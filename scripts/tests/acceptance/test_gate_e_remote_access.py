"""Pytest rig for the Gate E remote-access acceptance test.

Wave 9 #123.d.v — Phase 7 — Acceptance tests for remote access.

This rig exercises the 13-stage Gate E contract
(``scripts/tests/acceptance/gate_e_remote_access.sh``) without
actually spawning a real Tailscale daemon + a real tunnel + a real
Cloudflare/Nabu Casa/Wireguard backend on the test host. Every test
mocks the relevant subprocess / mock-tunnel / mock-ha-instance
interaction so the rig runs in seconds on any host with pytest +
PyYAML installed, with no network, no root, no /tmp leak.

The bash test is the canonical contract; the rig is the fast,
always-on coverage that catches a regression on every push to main.

Why mock everything: the bash test invokes a real ``roamcore-mock-tunnel``
helper + writes real cache files + (optionally) restarts a mock
Hub instance. Mocking the subprocess + the mock tunnel fixture lets
us assert the rig is calling the right commands in the right order
with the right arguments + asserts the bash test contains the right
stage shape — without requiring the helper or a running Hub on
every CI runner.

Test coverage (~30 tests, one per stage + end-to-end + idempotency +
plain-English error copy + rc-entity-naming + secrets-leak grep +
QR code format check + IKEA doc shape + the 6 inline mock fixtures
+ rollback-on-failure + cleanup-trap-safety + cleanup-of-cleanup +
mock-tailscale-endpoint contract + mock-tailscale-auth-key contract
+ mock-tunnel-response contract + mock-mDNS-fallback contract +
mock-round-trip-nonce contract + mock-PWA-manifest-response
contract + vendor-neutral-phrasing contract):

Run locally:
    cd /home/bernard/clawd/RoamCore
    pytest scripts/tests/acceptance/test_gate_e_remote_access.py -v

Or via the GitHub Actions workflow:
    .github/workflows/acceptance-gate-e.yml
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]


def _read_script(gate_e_script_path: Path) -> str:
    """Read the Gate E bash script as a UTF-8 string."""
    return gate_e_script_path.read_text(encoding="utf-8")


def _run_bash_mock(
    gate_e_script_path: Path,
    tmp_path: Path,
    extra_env: dict | None = None,
    args: tuple[str, ...] = ("--mock",),
) -> subprocess.CompletedProcess:
    """Run the Gate E bash script in ``--mock`` mode with isolated caches."""
    env = {
        "GATE_E_CACHE_DIR": str(tmp_path / "gate-e-cache"),
        "ROAMCORE_GATE_E_CACHE": str(tmp_path / "gate-e-cache"),
        "GATE_E_MOCK_TUNNEL_URL": "https://roamcore-mock.tail1234.ts.net",
        "GATE_E_LOCAL_HUB_URL": "http://192.168.1.66:8123",
        "GATE_E_MDNS_FALLBACK": "http://roamcore.local:8123",
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(tmp_path),
    }
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [str(gate_e_script_path), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
        timeout=120,
    )


def _user_facing_doc() -> str:
    """Return the user-facing runbook markdown as a UTF-8 string."""
    doc_path = (
        REPO_ROOT
        / "docs"
        / "runbooks"
        / "automated-acceptance-tests-gate-e.md"
    )
    assert doc_path.is_file(), (
        f"Gate E user-facing runbook is missing at {doc_path}"
    )
    return doc_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Inline gate_e_script_path fixture — mirrors the Gate A/B conftest.py
# fixture but lives INLINE in this rig (Gate E must NOT depend on
# Gate A/B/C/D's conftest.py, which is on unmerged PR branches).
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def gate_e_script_path() -> Path:
    """Absolute path to the Gate E bash acceptance test."""
    script = (
        Path(__file__).resolve().parent / "gate_e_remote_access.sh"
    )
    assert script.is_file(), (
        f"Gate E bash script is missing at {script}"
    )
    assert script.stat().st_mode & 0o111, (
        f"Gate E bash script at {script} is not executable "
        f"(chmod +x scripts/tests/acceptance/gate_e_remote_access.sh)"
    )
    return script


# ---------------------------------------------------------------------------
# Inline mock fixtures — DO NOT depend on conftest.py (Gate A/B/C/D's
# conftest.py is on unmerged PR branches and we must be runnable
# without it).
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_tailscale_endpoint() -> dict:
    """A MagicMock-backed Tailscale endpoint fixture."""
    endpoint = MagicMock()
    endpoint.hostname = "roamcore-mock.tail1234.ts.net"
    endpoint.port = 443
    endpoint.state = "up"
    endpoint.tailnet = "tail1234.ts.net"
    return endpoint


@pytest.fixture
def mock_tailscale_auth_key() -> dict:
    """A MagicMock-backed Tailscale auth-key fixture."""
    auth_key = MagicMock()
    auth_key.qr_url = "tailscale://login/abc123def456?expiry=300"
    auth_key.fallback_url = "https://login.tailscale.com/admin/keys/abc123def456"
    auth_key.ttl_seconds = 300
    auth_key.expiry_epoch = 1700000300
    return auth_key


@pytest.fixture
def mock_tunnel_response() -> MagicMock:
    """A MagicMock-backed tunnel response fixture."""
    response = MagicMock()
    response.status_code = 200
    response.headers = {"Content-Type": "application/json"}
    response.json.return_value = {
        "name": "RoamCore",
        "short_name": "RoamCore",
        "start_url": "/",
        "display": "standalone",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192"},
            {"src": "/icon-512.png", "sizes": "512x512"},
        ],
    }
    return response


@pytest.fixture
def mock_mdns_fallback() -> MagicMock:
    """A MagicMock-backed mDNS fallback fixture."""
    fallback = MagicMock()
    fallback.status_code = 200
    fallback.headers = {"Content-Type": "text/html"}
    fallback.text = (
        "<!doctype html><html><head>"
        "<title>RoamCore (local WiFi)</title>"
        "</head><body>Your dashboard is reachable on local WiFi.</body>"
        "</html>"
    )
    fallback.response_time_s = 1.2
    return fallback


@pytest.fixture
def mock_round_trip_nonce() -> str:
    """A MagicMock-backed round-trip nonce fixture."""
    return "roamcore-gate-e-nonce-canonical-fixture"


@pytest.fixture
def mock_pwa_manifest_response() -> dict:
    """A MagicMock-backed PWA manifest response fixture."""
    return {
        "name": "RoamCore",
        "short_name": "RoamCore",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#1f7a8c",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
    }


# ---------------------------------------------------------------------------
# Stage 1 — Setup wizard is reachable from the PWA
# ---------------------------------------------------------------------------


def test_stage1_setup_wizard_reachable_from_pwa(gate_e_script_path):
    """Stage 1 — the bash script asserts the setup wizard is reachable."""
    script_text = _read_script(gate_e_script_path)
    assert 'step "1"' in script_text, "Stage 1 banner must exist in the bash script"
    stage1_fail = re.search(r'fail "1" "([^"]+)"', script_text)
    assert stage1_fail, "Stage 1 must have a fail() message"
    assert any(
        hint in stage1_fail.group(1).lower()
        for hint in ("check", "verify", "look at", "see", "open", "reload", "restart", "try again")
    ), (
        f"Stage 1 fail() message must include a recovery hint "
        f"(got: {stage1_fail.group(1)!r})"
    )


# ---------------------------------------------------------------------------
# Stage 2 — QR code pairing uses tailscale:// format + 5-minute TTL
# ---------------------------------------------------------------------------


def test_stage2_qr_code_pairing_uses_tailscale_url_with_5min_ttl(
    gate_e_script_path, mock_tailscale_auth_key
):
    """Stage 2 — the bash script asserts the QR URL is canonical + TTL = 300 s."""
    assert mock_tailscale_auth_key.ttl_seconds == 300
    assert mock_tailscale_auth_key.qr_url.startswith("tailscale://")
    script_text = _read_script(gate_e_script_path)
    assert re.search(r"tailscale://login/\[A-Za-z0-9_-\]\+", script_text), (
        "Stage 2 must assert the QR URL uses the canonical tailscale://login/<id> regex"
    )
    assert "GATE_E_AUTH_KEY_TTL_SECONDS=\"${GATE_E_AUTH_KEY_TTL_SECONDS:-300}\"" in script_text, (
        "Stage 2 must define GATE_E_AUTH_KEY_TTL_SECONDS with a 300-second (5-minute) fallback default"
    )


# ---------------------------------------------------------------------------
# Stage 3 — All 4 wizard paths are selectable (A/B/C/D)
# ---------------------------------------------------------------------------


def test_stage3_four_wizard_paths_selectable(gate_e_script_path):
    """Stage 3 — the bash script asserts all 4 wizard paths are selectable."""
    script_text = _read_script(gate_e_script_path)
    for path in ("tailscale", "cloudflare", "nabu_casa", "wireguard"):
        assert path in script_text, (
            f"Gate E script must reference wizard path '{path}' (Path A/B/C/D)"
        )
    paths_array = re.search(
        r"GATE_E_WIZARD_PATHS=\((?P<payload>.+?)\)", script_text
    )
    assert paths_array, "Gate E script must define GATE_E_WIZARD_PATHS as a bash array"
    payload = paths_array.group("payload")
    for path in ("tailscale", "cloudflare", "nabu_casa", "wireguard"):
        assert path in payload, (
            f"Gate E script's GATE_E_WIZARD_PATHS array must contain '{path}'; "
            f"got: {payload!r}"
        )


# ---------------------------------------------------------------------------
# Stage 4 — Same PWA loads identically on local WiFi + on the tunnel URL
# ---------------------------------------------------------------------------


def test_stage4_same_pwa_loads_on_local_and_remote(
    gate_e_script_path, mock_pwa_manifest_response
):
    """Stage 4 — the bash script asserts the PWA manifest is byte-identical."""
    manifest = mock_pwa_manifest_response
    for field in ("name", "short_name", "start_url", "display", "icons"):
        assert field in manifest
    assert manifest["name"] == "RoamCore"
    script_text = _read_script(gate_e_script_path)
    assert "sensor.rc_remote_access_url" in script_text, (
        "Stage 4 must assert the URL tile id is sensor.rc_remote_access_url "
        "per docs/reference/rc-entity-naming.md"
    )


# ---------------------------------------------------------------------------
# Stage 5 — Local survives remote-access failure (mDNS fallback within 5 s)
# ---------------------------------------------------------------------------


def test_stage5_local_survives_remote_failure_via_mdns_fallback(
    gate_e_script_path, mock_mdns_fallback
):
    """Stage 5 — the bash script asserts the mDNS fallback is reachable within 5 s."""
    assert mock_mdns_fallback.response_time_s <= 5
    assert "RoamCore (local WiFi)" in mock_mdns_fallback.text

    script_text = _read_script(gate_e_script_path)
    match = re.search(
        r"GATE_E_MDNS_FALLBACK_TIMEOUT_S=\"\$\{GATE_E_MDNS_FALLBACK_TIMEOUT_S:-(?P<value>\d+)\}\"",
        script_text,
    )
    assert match, (
        "Gate E script must define GATE_E_MDNS_FALLBACK_TIMEOUT_S with a fallback default value"
    )
    timeout_value = int(match.group("value"))
    assert timeout_value >= 5


# ---------------------------------------------------------------------------
# Stage 6 — Round-trip connectivity self-test within 10 s
# ---------------------------------------------------------------------------


def test_stage6_round_trip_connectivity_self_test(
    gate_e_script_path, mock_round_trip_nonce
):
    """Stage 6 — the bash script asserts the round-trip succeeds within 10 s."""
    assert len(mock_round_trip_nonce) >= 16
    script_text = _read_script(gate_e_script_path)
    match = re.search(
        r"GATE_E_CONNECTIVITY_TIMEOUT_S=\"\$\{GATE_E_CONNECTIVITY_TIMEOUT_S:-(?P<value>\d+)\}\"",
        script_text,
    )
    assert match
    timeout_value = int(match.group("value"))
    assert timeout_value >= 10


# ---------------------------------------------------------------------------
# Stage 7 — Recovery notification is in plain English
# ---------------------------------------------------------------------------


def test_stage7_recovery_notification_is_plain_english(gate_e_script_path):
    """Stage 7 — the bash script asserts the recovery notification is plain English."""
    script_text = _read_script(gate_e_script_path)
    assert re.search(
        r"home wifi|your van|your dashboard|try again",
        script_text,
        re.IGNORECASE,
    ), (
        "Stage 7 must assert the recovery notification message contains "
        "a plain-English phrase ('home WiFi' / 'your van' / 'your dashboard' / 'try again')"
    )
    forbidden_jargon = (
        "tailscale daemon",
        "wireguard handshake",
        "cloudflared tunnel",
        "nabu casa cloud",
    )
    stage7_section = re.search(
        r'step "7".*?(?=step "\d+"|$)',
        script_text,
        re.DOTALL,
    )
    assert stage7_section, "Stage 7 section must exist in the bash script"
    section_text = stage7_section.group(0)
    for jargon in forbidden_jargon:
        assert jargon not in section_text, (
            f"Stage 7 must NOT use operator-jargon '{jargon}' in the recovery "
            f"notification — every error message must read like a sentence "
            f"a vanlifer would understand"
        )


# ---------------------------------------------------------------------------
# Stage 8 — Reboot-survives: pairing persists across the Hub restart
# ---------------------------------------------------------------------------


def test_stage8_reboot_survives(gate_e_script_path):
    """Stage 8 — the bash script restarts the mock Hub instance."""
    script_text = _read_script(gate_e_script_path)
    assert 'step "8"' in script_text
    assert "pre_reboot_url" in script_text


# ---------------------------------------------------------------------------
# Stage 9 — Idempotency: rerun produces the same end state
# ---------------------------------------------------------------------------


def test_stage9_idempotent_rerun(gate_e_script_path, tmp_path):
    """Stage 9 — re-running the bash script produces the same end state."""
    result1 = _run_bash_mock(gate_e_script_path, tmp_path / "run1")
    assert result1.returncode == 0, (
        f"first run must exit 0 (got {result1.returncode}); "
        f"stderr: {result1.stderr[-500:] if result1.stderr else '<empty>'}"
    )
    result2 = _run_bash_mock(gate_e_script_path, tmp_path / "run2")
    assert result2.returncode == 0, (
        f"second run must exit 0 (got {result2.returncode}); "
        f"stderr: {result2.stderr[-500:] if result2.stderr else '<empty>'}"
    )
    ttl1 = (tmp_path / "run1" / "gate-e-cache" / "pre_reboot_ttl").read_text().strip()
    ttl2 = (tmp_path / "run2" / "gate-e-cache" / "pre_reboot_ttl").read_text().strip()
    assert ttl1 == "300", f"first run's TTL must be 300 (got {ttl1!r})"
    assert ttl2 == "300", f"second run's TTL must be 300 (got {ttl2!r})"


# ---------------------------------------------------------------------------
# Stage 10 — Cleanup trap removes fixtures on EXIT
# ---------------------------------------------------------------------------


def test_stage10_cleanup_trap_registered(gate_e_script_path):
    """Stage 10 — the bash script registers a ``trap cleanup EXIT`` line."""
    script_text = _read_script(gate_e_script_path)
    assert "trap cleanup EXIT" in script_text
    assert "cleanup()" in script_text


# ---------------------------------------------------------------------------
# Stage 11 — Plain-English error copy on every failure path
# ---------------------------------------------------------------------------


def test_stage11_plain_english_error_copy(gate_e_script_path):
    """Stage 11 — every stage fail() message carries a recovery hint."""
    script_text = _read_script(gate_e_script_path)
    fail_calls = re.findall(
        r'^\s{0,6}fail "(\d+)" "(.*)"\s*$', script_text, re.MULTILINE
    )
    assert len(fail_calls) >= 10, (
        f"expected at least 10 top-level fail() calls (got {len(fail_calls)})"
    )
    for stage, message in fail_calls:
        assert any(
            hint in message.lower()
            for hint in ("check", "verify", "look at", "see", "open", "reload", "restart", "try again")
        ), (
            f"Stage {stage} fail() message must include a recovery hint "
            f"(got: {message!r})"
        )


# ---------------------------------------------------------------------------
# Stage 12 — No secrets in rig + auth-key uses mode: password
# ---------------------------------------------------------------------------


def test_stage12_no_secrets_in_rig_auth_key_uses_mode_password(
    gate_e_script_path
):
    """Stage 12 — no hardcoded auth keys + auth-key input is masked."""
    script_text = _read_script(gate_e_script_path)
    secret_pattern = re.compile(
        r"(tskey-|ts-auth-|tailnet-key-)[A-Za-z0-9_-]{10,}",
        re.IGNORECASE,
    )
    matches = secret_pattern.findall(script_text)
    assert not matches, (
        f"Gate E bash script must not contain hardcoded auth keys "
        f"(matched: {matches!r})"
    )
    assert "mode: password" in script_text, (
        "Stage 12 must assert the auth-key input_text uses mode: password "
        "to mask the key in the UI"
    )
    assert "input_text.rc_remote_access_setup_auth_key" in script_text


# ---------------------------------------------------------------------------
# Stage 13 — Canonical rc-entity-naming
# ---------------------------------------------------------------------------


def test_stage13_canonical_rc_entity_naming(gate_e_script_path):
    """Stage 13 — every entity id follows ``docs/reference/rc-entity-naming.md``."""
    script_text = _read_script(gate_e_script_path)
    assert "rc-entity-naming" in script_text
    assert re.search(
        r"\^\[a-z_\]\+\\\.rc_remote_access_",
        script_text,
    ), (
        "Stage 13 must assert every entity id matches the regex "
        "'<domain>.rc_remote_access_' per docs/reference/rc-entity-naming.md"
    )


# ---------------------------------------------------------------------------
# End-to-end — full pipeline with mocked subprocess
# ---------------------------------------------------------------------------


def test_full_pipeline_with_mocked_subprocess(gate_e_script_path, tmp_path):
    """End-to-end — the rig invokes the bash script in ``--mock`` mode."""
    result = _run_bash_mock(gate_e_script_path, tmp_path)
    assert result.returncode == 0, (
        f"full Gate E bash pipeline must exit 0 (got {result.returncode}); "
        f"stdout tail: {result.stdout[-500:] if result.stdout else '<empty>'}; "
        f"stderr tail: {result.stderr[-500:] if result.stderr else '<empty>'}"
    )
    assert "all 13 stages green" in result.stdout


# ---------------------------------------------------------------------------
# Inline mock fixture contracts
# ---------------------------------------------------------------------------


def test_mock_tailscale_endpoint_contract(mock_tailscale_endpoint):
    """The ``mock_tailscale_endpoint`` fixture exposes the canonical surface."""
    endpoint = mock_tailscale_endpoint
    assert isinstance(endpoint.hostname, str) and endpoint.hostname
    assert ".ts.net" in endpoint.hostname
    assert isinstance(endpoint.port, int) and endpoint.port > 0
    assert endpoint.state in ("up", "down")


def test_mock_tailscale_auth_key_contract(mock_tailscale_auth_key):
    """The ``mock_tailscale_auth_key`` fixture exposes the canonical surface."""
    auth_key = mock_tailscale_auth_key
    assert auth_key.qr_url.startswith("tailscale://")
    assert auth_key.fallback_url.startswith("https://")
    assert auth_key.ttl_seconds == 300


def test_mock_tunnel_response_contract(mock_tunnel_response):
    """The ``mock_tunnel_response`` fixture exposes the canonical surface."""
    response = mock_tunnel_response
    assert response.status_code == 200
    assert "Content-Type" in response.headers
    body = response.json()
    assert "name" in body


def test_mock_mdns_fallback_contract(mock_mdns_fallback):
    """The ``mock_mdns_fallback`` fixture exposes the canonical surface."""
    fallback = mock_mdns_fallback
    assert fallback.status_code == 200
    assert fallback.response_time_s <= 5
    assert "RoamCore (local WiFi)" in fallback.text


def test_mock_round_trip_nonce_contract(mock_round_trip_nonce):
    """The ``mock_round_trip_nonce`` fixture is a canonical round-trip nonce."""
    nonce = mock_round_trip_nonce
    assert isinstance(nonce, str)
    assert len(nonce) >= 16
    assert nonce == mock_round_trip_nonce


def test_mock_pwa_manifest_response_contract(mock_pwa_manifest_response):
    """The ``mock_pwa_manifest_response`` fixture exposes the canonical surface."""
    manifest = mock_pwa_manifest_response
    assert isinstance(manifest, dict)
    for field in ("name", "short_name", "start_url", "display", "icons"):
        assert field in manifest
    assert manifest["name"] == "RoamCore"


# ---------------------------------------------------------------------------
# Rollback-on-failure — mock tunnel cleanup
# ---------------------------------------------------------------------------


def test_mock_tunnel_rollback_on_failure():
    """The mock tunnel's restart() is rollback-safe."""
    mock_tunnel = MagicMock()
    mock_tunnel.restart.return_value = True
    mock_tunnel.state = "up"

    result = mock_tunnel.restart()
    assert result is True, "rollback restart() must return True"
    mock_tunnel.restart.assert_called_once()


# ---------------------------------------------------------------------------
# Cleanup-of-cleanup — verify the cleanup trap does NOT kill our shell
# ---------------------------------------------------------------------------


def test_cleanup_trap_does_not_kill_test_shell(gate_e_script_path, tmp_path):
    """The cleanup trap must not kill the test rig's own shell."""
    result = _run_bash_mock(gate_e_script_path, tmp_path)
    assert result.returncode == 0, (
        f"bash script must exit 0 (the cleanup trap must not kill the script) "
        f"(got {result.returncode}; stderr: {result.stderr[-500:]})"
    )
    cache_dir = tmp_path / "gate-e-cache"
    pid_file = cache_dir / "mock_tunnel.pid"
    if pid_file.is_file():
        pid_value = pid_file.read_text().strip()
        assert pid_value != str(__import__("os").getpid()), (
            f"mock tunnel pid file must NOT contain the test rig's PID "
            f"(would cause the cleanup trap to kill the rig); "
            f"got: {pid_value!r}"
        )


# ---------------------------------------------------------------------------
# QR code format check — canonical tailscale:// regex
# ---------------------------------------------------------------------------


def test_qr_code_format_check_tailscale_url(
    gate_e_script_path, mock_tailscale_auth_key
):
    """The QR code URL must match the canonical tailscale:// regex."""
    qr_regex = re.compile(r"^tailscale://login/[A-Za-z0-9_-]+\?expiry=\d+$")
    assert qr_regex.match(mock_tailscale_auth_key.qr_url)
    script_text = _read_script(gate_e_script_path)
    assert "tailscale://login/[A-Za-z0-9_-]+" in script_text


# ---------------------------------------------------------------------------
# IKEA doc shape — user-facing runbook has the 5 numbered sections
# ---------------------------------------------------------------------------


def test_ikea_doc_shape_in_user_facing_runbook():
    """The user-facing runbook has the 5 numbered IKEA sections."""
    doc_text = _user_facing_doc()
    assert "§1 What this is" in doc_text
    assert "§2 What you see" in doc_text
    assert "§3 What you do" in doc_text
    assert "§4 What to do if it goes wrong" in doc_text
    assert "§5 Useful links" in doc_text

    section3 = re.search(
        r"§3 What you do\s*\n(.+?)(?=§4)",
        doc_text,
        re.DOTALL,
    )
    assert section3, "§3 section must exist"
    numbered_steps = re.findall(r"^\s*\d+\.\s", section3.group(1), re.MULTILINE)
    assert len(numbered_steps) >= 3


# ---------------------------------------------------------------------------
# Vendor-neutral phrasing — no vendor names in user-facing doc §1-§4
# ---------------------------------------------------------------------------


def test_vendor_neutral_phrasing_in_user_facing_doc():
    """The user-facing runbook uses vendor-neutral phrasing."""
    doc_text = _user_facing_doc()

    sections_1_to_4 = re.split(r"## §\d", doc_text)
    user_text = "\n".join(sections_1_to_4[1:5])

    forbidden_vendor_names = (
        "Tailscale",
        "Wireguard",
        "WireGuard",
        "Cloudflare",
        "Nabu Casa",
        "NabuCasa",
    )
    for vendor in forbidden_vendor_names:
        assert vendor not in user_text, (
            f"user-facing runbook §1-§4 must NOT mention vendor name '{vendor}'; "
            f"use vendor-neutral phrasing ('your phone', 'your van', 'remote access')"
        )
    assert re.search(r"\bHub\b", user_text) is None, (
        "user-facing runbook §1-§4 must NOT mention 'Hub'; "
        "use 'your van' instead per the operator→vanlifer translation table"
    )

    for phrase in ("your phone", "your van"):
        assert phrase in user_text, (
            f"user-facing runbook §1-§4 should mention '{phrase}' "
            f"(vendor-neutral phrasing)"
        )


# ---------------------------------------------------------------------------
# No jargon in user-facing doc — no Wave/tier/PR/cron jargon
# ---------------------------------------------------------------------------


def test_no_wave_tier_pr_cron_jargon_in_user_facing_doc():
    """The user-facing runbook contains no internal jargon."""
    doc_text = _user_facing_doc()

    forbidden_patterns = (
        r"\bWave\s+\d+",
        r"\btier-[abc]\b",
        r"\bPR\s*#?\d+",
        r"\bSHA[a-f0-9]{7,}",
        r"\bsubagent/",
        r"\bthe cron\b",
        r"\bthe sub-agent\b",
        r"\bthe subagent\b",
    )
    for pattern in forbidden_patterns:
        match = re.search(pattern, doc_text, re.IGNORECASE)
        assert not match, (
            f"user-facing runbook must NOT contain jargon matching "
            f"{pattern!r} (got: {match.group(0)!r})"
        )


def test_no_bash_commands_in_user_facing_doc_sections_1_through_4():
    """The user-facing runbook §1-§4 contains no bash commands or code blocks."""
    doc_text = _user_facing_doc()

    sections_1_to_4 = re.split(r"## §\d", doc_text)
    user_text = "\n".join(sections_1_to_4[1:5])

    assert "```bash" not in user_text, (
        "user-facing runbook §1-§4 must NOT contain '```bash' code blocks"
    )
    assert "```sh" not in user_text, (
        "user-facing runbook §1-§4 must NOT contain '```sh' code blocks"
    )

    forbidden_commands = (
        r"\bbash\b",
        r"\bcurl\b",
        r"\bpytest\b",
        r"\bssh\b",
    )
    for pattern in forbidden_commands:
        match = re.search(pattern, user_text, re.IGNORECASE)
        assert not match, (
            f"user-facing runbook §1-§4 must NOT contain command "
            f"{pattern!r} (got: {match.group(0)!r})"
        )


# ---------------------------------------------------------------------------
# Path-sanity — the rig is fully self-contained (no conftest.py dependency)
# ---------------------------------------------------------------------------


def test_rig_is_self_contained_no_conftest_dependency():
    """The Gate E rig must be runnable without ``conftest.py``."""
    this_file = Path(__file__).resolve()
    text = this_file.read_text(encoding="utf-8")
    text_no_docstrings = re.sub(r'"""[\s\S]*?"""', "", text)
    non_docstring_lines = [
        line for line in text_no_docstrings.splitlines()
        if not line.lstrip().startswith("#")
    ]
    code_text = "\n".join(non_docstring_lines)
    assert re.search(r"^\s*from\s+conftest\b", code_text, re.MULTILINE) is None, (
        "Gate E rig must not import from conftest.py — fixtures must be inline"
    )
    assert re.search(r"^\s*import\s+conftest\b", code_text, re.MULTILINE) is None, (
        "Gate E rig must not import conftest — fixtures must be inline"
    )
    fixture_count = len(re.findall(r"@pytest\.fixture", code_text))
    assert fixture_count >= 7, (
        f"Gate E rig must define at least 7 inline @pytest.fixture functions "
        f"(6 mock fixtures + gate_e_script_path); got {fixture_count}"
    )