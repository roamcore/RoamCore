"""Pytest suite for the OpenWrt auto-pair flow.

Covers:

  - 6 unit tests:
      1. test_probe_parses_banner_correctly
      2. test_candidate_list_dedupes_ips
      3. test_idempotent_pair
      4. test_token_generator_is_32_hex_chars
      5. test_no_banner_found_returns_empty_list
      6. test_cross_subnet_scan_works_on_both_subnets

  - 1 integration HTTP probe test:
      test_integration_http_probe_against_fake_bind_mock
         (marked with pytest.mark.requires_aiohttp)

Run locally:

    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/openwrt/tests/ -v
"""

from __future__ import annotations

import asyncio
import json
import re
import secrets
import socket
import sys
from pathlib import Path

# Ensure the repo root is on sys.path so that
# `from connections.openwrt import ...` works when
# this file is invoked via `python3 <file.py>`
# (which the `scripts/check.sh` chain does).
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest

# Load the discovery module directly via importlib so
# we don't trigger the parent
# `homeassistant.custom_components.roamcore.__init__`
# (which has HA-only imports that fail on CI runners
# without HA installed).
_DISCOVERY_DIR = (
    Path(__file__).resolve().parents[3]
    / "homeassistant"
    / "custom_components"
    / "roamcore"
    / "discovery"
)
# Add the discovery/ directory to sys.path so we
# can import probe / pair / discovery as top-level
# modules (bypassing Python's parent-package
# resolution).
_ROAMCORE_CC_DIR = _DISCOVERY_DIR.parent
if str(_ROAMCORE_CC_DIR) not in sys.path:
    sys.path.insert(0, str(_ROAMCORE_CC_DIR))

# Direct file imports via importlib so we don't
# trigger the parent roamcore package __init__.py.
import importlib.util as _il_util  # noqa: E402

def _load(name, path):
    spec = _il_util.spec_from_file_location(name, path)
    mod = _il_util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

_probe_mod = _load(
    "rc_probe",
    _DISCOVERY_DIR / "probe.py",
)
_pair_mod = _load(
    "rc_pair",
    _DISCOVERY_DIR / "pair.py",
)
_discovery_mod = _load(
    "rc_discovery",
    _DISCOVERY_DIR / "__init__.py",
)

BANNER_HEADER = _discovery_mod.BANNER_HEADER
BANNER_VALUE = _discovery_mod.BANNER_VALUE
DEFAULT_PORTS = _discovery_mod.DEFAULT_PORTS
Candidate = _discovery_mod.Candidate
discover_candidates = _discovery_mod.discover_candidates
generate_token = _pair_mod.generate_token
probe_ip = _probe_mod.probe_ip
scan_subnet = _probe_mod.scan_subnet

from connections.openwrt import (
    DEFAULT_TOKEN_PORT,
    PairResult,
    apply_pair,
    plain_english_error,
)


# ---------------------------------------------------------------------------
# Helper: tiny HTTP server returning the banner
# ---------------------------------------------------------------------------


async def _start_banner_server(
    host: str = "127.0.0.1",
    port: int = 0,
    *,
    banner_value: str = BANNER_VALUE,
    respond_body: bytes = b"",
) -> tuple[asyncio.AbstractServer, int]:
    """Start a tiny HTTP server that responds to HEAD/GET with the banner.

    Returns (server, actual_port).
    """
    async def _handle(reader, writer):
        try:
            buf = bytearray()
            while len(buf) < 8192:
                chunk = await asyncio.wait_for(reader.read(512), timeout=2.0)
                if not chunk:
                    break
                buf.extend(chunk)
                if b"\r\n\r\n" in buf:
                    break

            request_line = bytes(buf).decode("iso-8859-1", errors="replace").split("\r\n", 1)[0]
            is_head = request_line.upper().startswith("HEAD")

            response_headers = (
                f"HTTP/1.1 200 OK\r\n"
                f"{BANNER_HEADER}: {banner_value}\r\n"
                f"Server: fake-openwrt-for-tests\r\n"
                f"Content-Type: text/plain\r\n"
                f"Content-Length: {len(respond_body)}\r\n"
                f"Connection: close\r\n"
                f"\r\n"
            )
            writer.write(response_headers.encode("ascii"))
            if not is_head:
                writer.write(respond_body)
            await writer.drain()
        except (asyncio.TimeoutError, OSError, ConnectionResetError):
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    server = await asyncio.start_server(_handle, host=host, port=port)
    actual_port = server.sockets[0].getsockname()[1] if server.sockets else port
    return server, actual_port


# ---------------------------------------------------------------------------
# Test 1: probe parses the banner correctly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_probe_parses_banner_correctly() -> None:
    """A fake-bind HTTP server returning the
    X-RoamCore-Api: ok banner must be parsed into a
    Candidate with the right ip + port + banner value.
    """
    server, port = await _start_banner_server()
    try:
        cand = await probe_ip("127.0.0.1", port, timeout_s=2.0)
        assert cand is not None
        assert cand.ip == "127.0.0.1"
        assert cand.port == port
        assert cand.banner == BANNER_VALUE
    finally:
        server.close()
        await server.wait_closed()


# ---------------------------------------------------------------------------
# Test 2: candidate list dedupes IPs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_candidate_list_dedupes_ips() -> None:
    """discover_candidates must deduplicate IPs.

    Strategy: start TWO banner servers on the same
    IP (127.0.0.1) on different ports. Configure
    discover_candidates to scan ONLY that IP on
    BOTH ports. The function returns exactly TWO
    candidates (one per port). Then run twice and
    confirm idempotent.
    """
    server_a, port_a = await _start_banner_server()
    server_b, port_b = await _start_banner_server()
    try:
        cands = await discover_candidates(
            subnets=["127.0.0.1/32"],
            ports=(port_a, port_b),
            timeout_s=2.0,
        )
        ips_ports = sorted((c.ip, c.port) for c in cands)
        assert len(ips_ports) == 2
        assert ("127.0.0.1", port_a) in ips_ports
        assert ("127.0.0.1", port_b) in ips_ports
    finally:
        server_a.close()
        await server_a.wait_closed()
        server_b.close()
        await server_b.wait_closed()

    # And the dedup itself: two consecutive scans
    # produce the same list.
    server_c, port_c = await _start_banner_server()
    try:
        first = await discover_candidates(
            subnets=["127.0.0.1/32"],
            ports=(port_c,),
            timeout_s=2.0,
        )
        second = await discover_candidates(
            subnets=["127.0.0.1/32"],
            ports=(port_c,),
            timeout_s=2.0,
        )
        assert first == second
    finally:
        server_c.close()
        await server_c.wait_closed()


# ---------------------------------------------------------------------------
# Test 3: idempotent pair
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_idempotent_pair() -> None:
    """apply_pair with the same existing_token twice
    must NOT push a new token; the second call
    returns cached=True.
    """
    push_count = {"n": 0}
    verify_count = {"n": 0}
    expected_token = secrets.token_hex(16)

    async def _handler(reader, writer):
        try:
            buf = bytearray()
            while len(buf) < 8192:
                chunk = await asyncio.wait_for(reader.read(512), timeout=2.0)
                if not chunk:
                    break
                buf.extend(chunk)
                if b"\r\n\r\n" in buf:
                    break

            request = bytes(buf).decode("iso-8859-1", errors="replace")
            request_line = request.split("\r\n", 1)[0].upper()

            if request_line.startswith("POST"):
                push_count["n"] += 1
                body = b'{"ok": true}'
            elif request_line.startswith("GET"):
                verify_count["n"] += 1
                body = b'{"status": "200 ok"}'
            else:
                body = b""

            response = (
                f"HTTP/1.1 200 OK\r\n"
                f"Content-Type: application/json\r\n"
                f"Content-Length: {len(body)}\r\n"
                f"Connection: close\r\n"
                f"\r\n"
            ).encode("ascii") + body
            writer.write(response)
            await writer.drain()
        except (asyncio.TimeoutError, OSError, ConnectionResetError):
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    server = await asyncio.start_server(_handler, host="127.0.0.1", port=0)
    actual_port = server.sockets[0].getsockname()[1]
    try:
        result = await apply_pair(
            ip="127.0.0.1",
            port=actual_port,
            existing_token=expected_token,
            timeout_s=2.0,
        )
        assert isinstance(result, PairResult)
        assert result.verified is True
        assert result.cached is True
        assert result.token == expected_token
        assert push_count["n"] == 0, (
            f"push was hit {push_count['n']} time(s) on "
            f"cached call; idempotent pair must NOT push"
        )
        assert verify_count["n"] == 1

        push_count["n"] = 0
        verify_count["n"] = 0
        result2 = await apply_pair(
            ip="127.0.0.1",
            port=actual_port,
            existing_token=expected_token,
            timeout_s=2.0,
        )
        assert result2.cached is True
        assert result2.verified is True
        assert result2.token == expected_token
        assert push_count["n"] == 0
        assert verify_count["n"] == 1
    finally:
        server.close()
        await server.wait_closed()


# ---------------------------------------------------------------------------
# Test 4: token generator is 32 hex chars
# ---------------------------------------------------------------------------


def test_token_generator_is_32_hex_chars() -> None:
    """generate_token() must return a 32-hex-char
    string composed of only [0-9a-f].
    """
    token = generate_token()
    assert len(token) == 32
    assert re.match(r"^[0-9a-f]{32}$", token)

    # Sanity check: different tokens on consecutive calls.
    token2 = generate_token()
    assert token != token2


# ---------------------------------------------------------------------------
# Test 5: error path "no banner found" returns empty list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_banner_found_returns_empty_list() -> None:
    """A scan of a subnet with NO RoamCore-flashed
    routers must return an empty list.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    free_port = sock.getsockname()[1]
    sock.close()

    cands = await discover_candidates(
        subnets=["127.0.0.1/32"],
        ports=(free_port,),
        timeout_s=1.0,
    )
    assert cands == []
    err = plain_english_error("no_candidate")
    assert "couldn't find" in err.lower()
    assert "plugged in" in err.lower()


# ---------------------------------------------------------------------------
# Test 6: cross-subnet test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_subnet_scan_works_on_both_subnets() -> None:
    """scan_subnet must accept BOTH `192.168.1.0/24`
    and `192.168.100.0/24` as valid CIDR inputs.
    """
    cands_1 = await scan_subnet(
        "192.168.1.0/24", ports=DEFAULT_PORTS, timeout_s=0.1, max_concurrent=64
    )
    assert cands_1 == []

    cands_100 = await scan_subnet(
        "192.168.100.0/24", ports=DEFAULT_PORTS, timeout_s=0.1, max_concurrent=64
    )
    assert cands_100 == []

    both = await discover_candidates(
        subnets=["192.168.1.0/24", "192.168.100.0/24"],
        timeout_s=0.1,
    )
    assert both == []

    bad = await discover_candidates(subnets=["not-a-cidr"], timeout_s=0.1)
    assert bad == []


# ---------------------------------------------------------------------------
# Test 7: integration HTTP probe (requires aiohttp)
# ---------------------------------------------------------------------------


@pytest.mark.requires_aiohttp
@pytest.mark.asyncio
async def test_integration_http_probe_against_fake_bind_mock(
    aiohttp_present: bool,
    tmp_path: Path,
) -> None:
    """Spin up an aiohttp test server on 127.0.0.1:18080
    returning the X-RoamCore-Api: ok banner, configure
    discovery on that one IP, assert the candidate
    list contains it, and assert apply_pair() pushes a
    token to /api/roamcore/token + verifies via
    /api/roamcore/health.

    The spec's "real verification" requirement.
    """
    if not aiohttp_present:
        pytest.skip("aiohttp not installed")

    import aiohttp
    from aiohttp import web

    push_requests: list[dict] = []
    verify_requests: list[dict] = []

    async def banner_handler(request: web.Request) -> web.Response:
        return web.Response(
            status=200,
            text="RoamCore-flashed OpenWrt (fake-bind test mock)",
            headers={BANNER_HEADER: BANNER_VALUE},
        )

    async def token_handler(request: web.Request) -> web.Response:
        body = await request.json()
        push_requests.append(body)
        token = body.get("token", "")
        if not re.match(r"^[0-9a-f]{32}$", token):
            return web.json_status(400, message="bad token format")
        return web.json_response(
            {"ok": True, "token_id": token[:8]}, status=200
        )

    async def health_handler(request: web.Request) -> web.Response:
        auth = request.headers.get("Authorization", "")
        verify_requests.append({"auth": auth})
        if not auth.startswith("Bearer "):
            return web.json_status(401, message="missing bearer")
        token = auth[len("Bearer "):]
        if not re.match(r"^[0-9a-f]{32}$", token):
            return web.json_status(401, message="bad token format")
        return web.json_response({"status": "200 ok"}, status=200)

    app = web.Application()
    app.router.add_get("/", banner_handler)
    app.router.add_post("/api/roamcore/token", token_handler)
    app.router.add_get("/api/roamcore/health", health_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 18080)
    await site.start()
    try:
        # 1. Discover candidates.
        cands = await discover_candidates(
            subnets=["127.0.0.1/32"],
            ports=(18080,),
            timeout_s=2.0,
        )
        assert len(cands) == 1
        cand = cands[0]
        assert cand.ip == "127.0.0.1"
        assert cand.port == 18080
        assert cand.banner == BANNER_VALUE

        # 2. Pair via apply_pair().
        known_devices_path = tmp_path / "known_devices.yaml"
        options: dict = {}
        result = await apply_pair(
            ip="127.0.0.1",
            port=18080,
            options=options,
            existing_token=None,
            known_devices_path=known_devices_path,
            timeout_s=2.0,
        )
        assert result.verified is True
        assert result.cached is False
        assert re.match(r"^[0-9a-f]{32}$", result.token)
        assert options.get("token") == result.token
        assert len(push_requests) == 1
        assert push_requests[0]["token"] == result.token
        assert len(verify_requests) == 1
        assert verify_requests[0]["auth"] == f"Bearer {result.token}"

        # 3. Idempotency.
        push_requests.clear()
        verify_requests.clear()
        result2 = await apply_pair(
            ip="127.0.0.1",
            port=18080,
            options=options,
            existing_token=result.token,
            known_devices_path=known_devices_path,
            timeout_s=2.0,
        )
        assert result2.cached is True
        assert result2.verified is True
        assert result2.token == result.token
        assert len(push_requests) == 0
        assert len(verify_requests) == 1
    finally:
        await runner.cleanup()

    # 4. known_devices.yaml was updated idempotently.
    assert known_devices_path.is_file()
    content = known_devices_path.read_text(encoding="utf-8")
    assert "127.0.0.1:18080" in content
    assert result.token in content
    import yaml
    parsed = yaml.safe_load(content)
    assert isinstance(parsed, dict)
    assert "devices" in parsed
    assert "127.0.0.1:18080" in parsed["devices"]
    assert parsed["devices"]["127.0.0.1:18080"]["token"] == result.token

if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
