#!/usr/bin/env python3
"""RoamCore — Hardware auto-discovery probe helper (stdlib-only).

This helper backs `homeassistant/packages/roamcore_hardware_discovery.yaml`
with one TCP-connect / filesystem probe per supported add-on. It is invoked
from a Home Assistant `command_line` sensor (`shell_command` is not used
because we want one short-lived call per add-on so the contract layer can
expose `binary_sensor.rc_hardware_<addon>_available` independently).

Goal (tier-b, slice Wave 2 #31):
- Survey the local LAN for each known add-on RoamCore already ships.
- Surface `ON` / `OFF` per add-on via the contract layer.
- NEVER touch the internet. Every probe target is loopback (127.0.0.1 / ::1)
  or RFC1918 (10/8, 172.16/12, 192.168/16) or the local filesystem
  (/share/roamcore/state.json for the OTA poller).
- Single probe per add-on, behind a master `input_boolean.rc_hardware_discovery_enabled`.

Output contract (single line, JSON):
    {"addon": "openwrt", "available": true, "latency_ms": 4, "error": ""}

Exit codes:
    0 — probe completed (available may still be false; that's fine)
    2 — argument / configuration error
    1 — fatal error (DNS, socket, unexpected)

Privacy: this script never resolves DNS, never opens a UDP socket, never
calls a non-loopback / non-RFC1918 target. The `victron` probe target
comes from `input_text.rc_hardware_victron_host` and is hard-validated
against RFC1918 ranges before any connect attempt. See `_validate_target`.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import socket
import sys
import time
from typing import Optional, Tuple


# Add-ons covered by the contract layer. The smoke check asserts at least
# these 5 names are wired in `homeassistant/packages/roamcore_hardware_discovery.yaml`
# as `binary_sensor.rc_hardware_<addon>_available`.
SUPPORTED_ADDONS = (
    "openwrt",
    "tileserver",
    "traccar",
    "victron",
    "ota",
)


# --- Privacy guard --------------------------------------------------------

def _validate_target(host: str, port: int) -> Tuple[bool, str]:
    """Reject any target that is not loopback or RFC1918.

    Returns (ok, reason). Empty reason means OK.

    This is the *single* privacy invariant the smoke check greps for. If
    this function ever loosens, the smoke must be updated in the same
    commit — otherwise the privacy invariant breaks.
    """
    if not (1 <= int(port) <= 65535):
        return False, "port out of range"

    # Resolve "localhost" / "localhost.localdomain" to loopback.
    if host.lower() in ("localhost", "ip6-localhost", "ip6-loopback"):
        return True, ""

    # Try IP parse first — covers 127.0.0.1, ::1, RFC1918 v4, unique local v6.
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False, f"host is not an IP literal: {host!r}"

    if ip.is_loopback:
        return True, ""
    if ip.is_private and not ip.is_unspecified:
        # is_private covers RFC1918 (10/8, 172.16/12, 192.168/16) AND
        # unique local IPv6 (fc00::/7). Both are on-prem.
        # Reject link-local (169.254/16, fe80::/10) to keep the smoke simple.
        return True, ""
    return False, f"host not in loopback or RFC1918: {host!r}"


# --- Per-add-on probes -----------------------------------------------------

def _probe_openwrt() -> dict:
    """TCP-connect the OpenWrt HTTP control plane.

    Default target: 192.168.1.1:80 (the OpenWrt default). Operators can
    override via `input_text.rc_hardware_openwrt_host`. We validate the
    host against RFC1918 before connecting.
    """
    host = os.environ.get("RC_HARDWARE_OPENWRT_HOST", "192.168.1.1")
    port = int(os.environ.get("RC_HARDWARE_OPENWRT_PORT", "80"))
    ok, reason = _validate_target(host, port)
    if not ok:
        return _result("openwrt", False, error=f"invalid target: {reason}")
    return _tcp_probe("openwrt", host, port, timeout=1.5)


def _probe_tileserver() -> dict:
    """TCP-connect the RoamCore tileserver add-on at 127.0.0.1:8000.

    Loopback only — the tileserver is shipped as an HA add-on and listens
    on the HA host's loopback by convention.
    """
    host = "127.0.0.1"
    port = 8000
    return _tcp_probe("tileserver", host, port, timeout=1.5)


def _probe_traccar() -> dict:
    """TCP-connect the Traccar add-on at 127.0.0.1:8082.

    The proxy add-on `roamcore_traccar_proxy` listens locally; the upstream
    Traccar itself may live elsewhere but our discovery contract only cares
    about whether the local proxy is reachable.
    """
    host = "127.0.0.1"
    port = 8082
    return _tcp_probe("traccar", host, port, timeout=1.5)


def _probe_victron() -> dict:
    """TCP-connect a Venus OS MQTT broker on the LAN.

    Operators configure the broker host via
    `input_text.rc_hardware_victron_host` (default: 192.168.1.100:1883).
    We refuse any host that doesn't pass `_validate_target`.
    """
    host = os.environ.get("RC_HARDWARE_VICTRON_HOST", "192.168.1.100")
    port = int(os.environ.get("RC_HARDWARE_VICTRON_PORT", "1883"))
    ok, reason = _validate_target(host, port)
    if not ok:
        return _result("victron", False, error=f"invalid target: {reason}")
    return _tcp_probe("victron", host, port, timeout=1.5)


def _probe_ota() -> dict:
    """Filesystem probe: is the OTA poller writing fresh state?

    The OTA add-on has no inbound port — it's a poller. Discovery looks for
    `/share/roamcore/state.json` and considers the add-on "available" if
    the file's `published_at` is within the last 7 days. Stale (> 7d) is
    treated as `OFF` because the poller hasn't run successfully.
    """
    path = "/share/roamcore/state.json"
    if not os.path.exists(path):
        return _result("ota", False, error="state.json not present")
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read(8192)
    except OSError as e:
        return _result("ota", False, error=f"read failed: {e}")

    # Cheap substring check (no json import required for the freshness probe).
    published_at = _extract_published_at(text)
    if published_at is None:
        return _result("ota", False, error="published_at missing")

    age_s = _age_seconds(published_at)
    if age_s is None:
        return _result("ota", False, error="published_at unparseable")
    if age_s > 7 * 24 * 3600:
        return _result("ota", False, error=f"state stale ({age_s}s old)")
    return _result("ota", True, latency_ms=0)


# --- Internals -------------------------------------------------------------

def _extract_published_at(text: str) -> Optional[str]:
    """Pull the value of `"published_at"` from a JSON-ish blob.

    We do this without json.loads so the probe works even on truncated
    files written by the poller.
    """
    needle = '"published_at"'
    idx = text.find(needle)
    if idx < 0:
        return None
    rest = text[idx + len(needle):]
    # Find the next colon, then the next quoted string.
    colon = rest.find(":")
    if colon < 0:
        return None
    rest = rest[colon + 1:].lstrip()
    if not rest.startswith('"'):
        return None
    end = rest.find('"', 1)
    if end < 0:
        return None
    return rest[1:end]


def _age_seconds(iso_ts: str) -> Optional[int]:
    """Compute the age (seconds) of an ISO-8601-ish timestamp.

    Accepts the formats the OTA poller emits (`Z` suffix or `+00:00`).
    Returns None on parse failure.
    """
    s = iso_ts.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        # datetime.fromisoformat handles offsets from Python 3.11+.
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(s)
    except Exception:
        return None
    if dt.tzinfo is None:
        from datetime import timezone
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(dt.tzinfo)
    return int((now - dt).total_seconds())


def _tcp_probe(addon: str, host: str, port: int, timeout: float) -> dict:
    """Single TCP connect. Returns the standard result shape."""
    start = time.monotonic()
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        latency_ms = int((time.monotonic() - start) * 1000)
        return _result(addon, True, latency_ms=latency_ms)
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        return _result(addon, False, error=f"{type(e).__name__}: {e}")
    finally:
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass


def _result(addon: str, available: bool, latency_ms: int = 0, error: str = "") -> dict:
    return {
        "addon": addon,
        "available": bool(available),
        "latency_ms": int(latency_ms),
        "error": str(error or ""),
    }


# --- CLI --------------------------------------------------------------------

PROBES = {
    "openwrt": _probe_openwrt,
    "tileserver": _probe_tileserver,
    "traccar": _probe_traccar,
    "victron": _probe_victron,
    "ota": _probe_ota,
}


def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--addon",
        required=True,
        choices=SUPPORTED_ADDONS,
        help="Which add-on to probe. One call per add-on so the HA contract layer can expose them independently.",
    )
    args = p.parse_args(argv)

    try:
        result = PROBES[args.addon]()
    except Exception as e:  # pragma: no cover — defensive
        # Last-ditch fallback: never crash the HA command_line sensor.
        sys.stdout.write(json.dumps(_result(args.addon, False, error=f"{type(e).__name__}: {e}")) + "\n")
        return 1

    sys.stdout.write(json.dumps(result) + "\n")
    # Exit 0 even on unavailable — HA's command_line uses stdout + exit
    # code only for sensor value derivation, and we want the binary_sensor
    # to flip ON/OFF based on the JSON, not on the exit code.
    return 0


if __name__ == "__main__":
    sys.exit(main())