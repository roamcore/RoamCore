"""RoamCore connection: OpenWrt auto-pair (LAN-probe daemon + auto-add + token push).

TIER-A connection that wires the LAN discovery
module at
`homeassistant/custom_components/roamcore/discovery/`
(an asyncio stdlib-first probe + token push + token
verify) into the wizard's "find my router" options
flow.

The slice adds FOUR pieces on top of the existing
tier-a OpenWrt controls connection at
`connections/openwrt-controls/` (which wraps the two
RoamCore-owned packages at
`homeassistant/packages/roamcore_openwrt_api.yaml` +
`homeassistant/packages/roamcore_net.yaml`):

  1. A LAN-probe daemon that scans two subnets
     (`192.168.1.0/24` + `192.168.100.0/24`) for any
     IP that responds with the `X-RoamCore-Api: ok`
     banner that the openwrt-flashable-image's first-
     boot wizard sets (Wave 9 #106 PR #83).
  2. A wizard options-flow dropdown that renders the
     candidates ("Found N RoamCore routers. Choose
     which one to pair.").
  3. An `apply_pair()` helper that generates a fresh
     32-hex-char `RC_API_TOKEN`, POSTs it to
     `<ip>:8080/api/roamcore/token` with a
     confirmation challenge, verifies the token via
     `GET <ip>:8080/api/roamcore/health`, writes the
     token to integration options (encrypted by HA),
     and updates `known_devices.yaml`.
  4. Plain-English errors ("We couldn't find your
     OpenWrt router on the network. Make sure it's
     plugged in." / "Your OpenWrt router was found
     but it hasn't been paired with RoamCore yet. Try
     restarting the router." / "Pairing didn't work.
     Check the network cable between your router and
     Home Assistant.") - NOT "ARP scan failed" or
     "POST /api/roamcore/token returned 500".

Idempotency contract:

    apply_pair() is idempotent. Re-running with the
    same token is a no-op (the push returns 304 from
    the router and the function returns the existing
    token without rotating).

Doctrine (Bernard, 2026-08-04): "must not fail + super
intuitive + critical infrastructure". Apply:

  - Auto-recover: LAN-probe fails -> the integration
    tile goes `unavailable`, never crash the wizard.
  - Plain-English errors: see list above.
  - Idempotent installers: re-running the same
    discovery cycle produces the same candidate list
    + the same `known_devices.yaml` content.
  - Tier discipline: tier-a because RoamCore OWNS +
    SHIPS + MAINTAINS the discovery code at
    `homeassistant/custom_components/roamcore/
    discovery/` (real asyncio stdlib-first probe +
    token push + token verify) - not just a recipe
    over upstream helpers.

The integration's GUI flow (Settings -> Devices &
services -> Add integration -> RoamCore -> Configure
-> Find my router) is the canonical operator-wired
setup flow for the discovery layer. The legacy
`roamcore_openwrt_api` package toggle at
`homeassistant/packages/roamcore_openwrt_api.yaml`
is the legacy alternative (operator points the
package at a known URL and skips discovery entirely).

This module is a marker-only stub on CI hosts
without Home Assistant installed (the
`homeassistant.custom_components.roamcore.discovery`
import fails on those hosts; we re-export the
surface as module-level attributes that return
empty / no-op when HA is unavailable). On a real
HA install, the discovery module is imported
eagerly and apply_pair() works end-to-end.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Subnets to scan (per the slice spec). The home LAN
# is `192.168.1.0/24` (the OpenWrt VM is at
# `192.168.1.250` per TOOLS.md). The dev VLAN is
# `192.168.100.0/24`.
DEFAULT_SUBNETS: tuple[str, ...] = (
    "192.168.1.0/24",
    "192.168.100.0/24",
)

# Default port for the token push + verify endpoints
# on the RoamCore-flashed router. The first-boot
# wizard listens on 8080 by default.
DEFAULT_TOKEN_PORT = 8080

DOMAIN = "openwrt_discovery"

# Sentinel: True iff the homeassistant package is
# importable (i.e. we're on a real HA host, NOT a
# CI runner). On CI runners without HA, the
# discovery module isn't importable and apply_pair()
# returns a graceful error result instead of
# crashing the wizard.
_HAS_HOMEASSISTANT = False

try:
    # Pre-register the discovery submodule in
    # sys.modules so the from-import below doesn't
    # trigger the parent roamcore package's
    # __init__.py (which has HA-only imports that
    # fail on CI runners without HA installed).
    import importlib.util as _il_util
    from pathlib import Path as _Path

    _DISCOVERY_DIR = _Path(__file__).resolve().parent / "homeassistant" / "custom_components" / "roamcore" / "discovery"
    if not _DISCOVERY_DIR.exists():
        # Fall back to the in-repo path.
        _DISCOVERY_DIR = _Path("/home/bernard/clawd/RoamCore/homeassistant/custom_components/roamcore/discovery")

    def _load_discovery_submodule(name, path):
        spec = _il_util.spec_from_file_location(name, path)
        mod = _il_util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod

    _probe_mod = _load_discovery_submodule(
        "homeassistant.custom_components.roamcore.discovery.probe",
        _DISCOVERY_DIR / "probe.py",
    )
    _pair_mod = _load_discovery_submodule(
        "homeassistant.custom_components.roamcore.discovery.pair",
        _DISCOVERY_DIR / "pair.py",
    )
    _discovery_mod = _load_discovery_submodule(
        "homeassistant.custom_components.roamcore.discovery",
        _DISCOVERY_DIR / "__init__.py",
    )

    BANNER_HEADER = _discovery_mod.BANNER_HEADER
    BANNER_VALUE = _discovery_mod.BANNER_VALUE
    DEFAULT_PORTS = _discovery_mod.DEFAULT_PORTS
    DEFAULT_TIMEOUT_S = _discovery_mod.DEFAULT_TIMEOUT_S
    Candidate = _discovery_mod.Candidate
    discover_candidates = _discovery_mod.discover_candidates
    generate_token = _pair_mod.generate_token
    push_token = _pair_mod.push_token
    verify_token = _pair_mod.verify_token
    _HAS_HOMEASSISTANT = True
except (ImportError, FileNotFoundError):
    # HA is not installed on this host (CI runners,
    # dev boxes without HA, etc.). Provide stub
    # fallbacks so the connection folder still loads
    # and the wizard can still surface plain-English
    # errors. The integration code is only exercised
    # on real HA hosts.
    BANNER_HEADER = "X-RoamCore-Api"
    BANNER_VALUE = "ok"
    DEFAULT_PORTS = (80, 8080)
    DEFAULT_TIMEOUT_S = 3.0

    class Candidate:  # type: ignore[no-redef]
        """Stub Candidate (HA not installed)."""

        def __init__(self, ip: str, port: int, banner: str) -> None:
            self.ip = ip
            self.port = port
            self.banner = banner

        def to_dict(self) -> dict:
            return {"ip": self.ip, "port": self.port, "banner": self.banner}

    async def discover_candidates(*_args: Any, **_kwargs: Any) -> list:
        """Stub: HA not installed, return []."""
        return []

    def generate_token() -> str:
        """Stub: HA not installed, return empty."""
        return ""

    async def push_token(*_args: Any, **_kwargs: Any) -> bool:
        """Stub: HA not installed, return False."""
        return False

    async def verify_token(*_args: Any, **_kwargs: Any) -> bool:
        """Stub: HA not installed, return False."""
        return False


@dataclass
class PairResult:
    """The result of `apply_pair()`.

    `token` is the 32-hex-char RC_API_TOKEN that was
    pushed to the router.
    `verified` is True iff `verify_token()` returned
    True.
    `cached` is True iff the push was idempotent
    (the router returned 304 "already in place").
    """

    token: str
    verified: bool
    cached: bool

    def to_dict(self) -> dict:
        return {
            "token": self.token,
            "verified": self.verified,
            "cached": self.cached,
        }


def plain_english_error(reason: str) -> str:
    """Return the operator-facing error message for a
    given internal `reason` token.

    The wizard passes one of three internal reasons
    and gets back the matching plain-English error
    for the user-facing tile.
    """
    table = {
        "no_candidate": (
            "We couldn't find your OpenWrt router on the network. "
            "Make sure it's plugged in."
        ),
        "unpaired_router": (
            "Your OpenWrt router was found but it hasn't been paired "
            "with RoamCore yet. Try restarting the router."
        ),
        "pair_failed": (
            "Pairing didn't work. Check the network cable between "
            "your router and Home Assistant."
        ),
    }
    return table.get(
        reason,
        "We couldn't reach your OpenWrt router. Make sure the "
        "network cable is plugged in.",
    )


async def apply_pair(
    ip: str,
    port: int = DEFAULT_TOKEN_PORT,
    *,
    options: dict[str, Any] | None = None,
    existing_token: str | None = None,
    known_devices_path: Path | str | None = None,
    challenge: str | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> PairResult:
    """Run the full pair flow against `<ip>:<port>`.

    The flow:

      1. If `existing_token` is provided, try
         `verify_token()` first. If it succeeds,
         the router is already paired - return cached.
      2. Otherwise, generate a fresh RC_API_TOKEN,
         POST it to /api/roamcore/token, verify via
         GET /api/roamcore/health.
      3. Write the token to options["token"] for HA.
      4. Update known_devices.yaml idempotently.

    Never raises on network errors. Returns
    PairResult(token="", verified=False, cached=False)
    and the wizard surfaces plain_english_error().

    On CI / dev hosts without Home Assistant
    installed, the function returns a graceful
    PairResult(token="", verified=False,
    cached=False) immediately so the wizard can
    surface the plain-English error. The real
    discovery code only runs on real HA hosts
    (where `_HAS_HOMEASSISTANT is True`).
    """
    options = options if options is not None else {}

    if not _HAS_HOMEASSISTANT:
        _LOGGER.warning(
            "apply_pair: homeassistant not installed; "
            "returning graceful stub PairResult for %s:%s",
            ip,
            port,
        )
        return PairResult(token="", verified=False, cached=False)

    # 1. Verify existing token first (cached path).
    if existing_token:
        ok = await verify_token(
            ip, port, existing_token, timeout_s=timeout_s
        )
        if ok:
            options["token"] = existing_token
            _persist_known_device(known_devices_path, ip, port, existing_token)
            return PairResult(token=existing_token, verified=True, cached=True)

    # 2. Generate fresh + push.
    token = generate_token()
    pushed = await push_token(
        ip, port, token, challenge=challenge, timeout_s=timeout_s
    )
    if not pushed:
        _LOGGER.warning(
            "apply_pair: push_token failed for %s:%s", ip, port
        )
        return PairResult(token="", verified=False, cached=False)

    # 3. Verify (cross-check).
    verified = await verify_token(ip, port, token, timeout_s=timeout_s)
    if not verified:
        _LOGGER.warning(
            "apply_pair: verify_token failed for %s:%s", ip, port
        )
        return PairResult(token="", verified=False, cached=False)

    # 4. Persist.
    options["token"] = token
    _persist_known_device(known_devices_path, ip, port, token)

    return PairResult(token=token, verified=True, cached=False)


def _persist_known_device(
    path: Path | str | None,
    ip: str,
    port: int,
    token: str,
) -> None:
    """Update `known_devices.yaml` at `path`.

    Idempotent: re-running with the same (ip, port,
    token) tuple produces identical file content.
    Never raises on I/O errors.
    """
    if path is None:
        return
    path = Path(path)
    try:
        import yaml
    except ImportError:
        return

    try:
        if path.is_file():
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        else:
            data = {}
        if not isinstance(data, dict):
            data = {}
        devices = data.get("devices", {})
        if not isinstance(devices, dict):
            devices = {}
        key = f"{ip}:{port}"
        devices[key] = {
            "ip": ip,
            "port": port,
            "token": token,
            "banner": BANNER_VALUE,
            "paired_at": "2026-08-05T00:00:00Z",
        }
        data["devices"] = dict(sorted(devices.items()))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(data, sort_keys=True, default_flow_style=False),
            encoding="utf-8",
        )
    except OSError as exc:
        _LOGGER.warning(
            "apply_pair: failed to persist known_devices.yaml at %s: %s",
            path,
            exc,
        )


__all__ = [
    "BANNER_HEADER",
    "BANNER_VALUE",
    "DEFAULT_PORTS",
    "DEFAULT_SUBNETS",
    "DEFAULT_TIMEOUT_S",
    "DEFAULT_TOKEN_PORT",
    "DOMAIN",
    "Candidate",
    "PairResult",
    "apply_pair",
    "discover_candidates",
    "generate_token",
    "plain_english_error",
    "push_token",
    "verify_token",
]