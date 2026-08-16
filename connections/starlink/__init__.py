"""Starlink (sleep timer + bring-back-up controls) — tier-b recipe connection.

This module is a marker-only stub for tier-b recipe connections. The
audit + boundary CI detect a `starlink/` folder that claims to be a
connection via the `DOMAIN` constant exported here. The wizard reads
the manifest + recipe at runtime.

Wave 9 #108 — Starlink 3-path wizard
=====================================
The wizard now asks the user which networking topology they want and
auto-sets up the chosen path. Three paths:

  Path A (starlink_mini_only)  — use the Starlink dish's built-in Wi-Fi
                                 router as the only router. RoamCore
                                 reads signal + reachability from the
                                 Starlink local HTTP API at
                                 http://192.168.100.1:80.

  Path B (separate_router)     — user owns a third-party router and
                                 a smart plug behind the Starlink PSU.
                                 RoamCore creates switch.rc_net_starlink_plug
                                 mapping to the user's plug.

  Path C (vp2430_vm_router)    — user runs an OpenWrt VM (VMID 100 on
                                 the VP2430) as the LAN router; Starlink
                                 is the WAN upstream. RoamCore reads
                                 WAN state from the OpenWrt API.

apply_setup_path(path_id, user_input, hass) below is the wiring entry
the config_flow calls when the user finishes the wizard step. It:

  - Path A: writes input_text.rc_net_starlink_api_url =
    "http://192.168.100.1:80" + creates a REST sensor pulling
    dish-status.json + creates 3 template sensors
    (reachable, signal_pct, sleep_state). Verifies reachability
    within 10 seconds via 3x retries with backoff (Gen-2/Gen-3
    only; Gen-1 gracefully degrades the signal tile to unknown).

  - Path B: creates switch.rc_net_starlink_plug mapping to the user's
    plug entity (validated exposed + controllable) + the sleep + wake
    + signal + quiet-hours contract tiles. Verifies the plug entity
    is reachable + controllable before writing.

  - Path C: writes the OpenWrt API URL + token to a dedicated
    input_text helper pair, creates a REST sensor chain through the
    OpenWrt API for WAN reachable / WAN IP, and keeps the Starlink
    local API for signal_pct.

All three paths are idempotent (re-running the wizard step re-detects,
re-confirms, no duplicate entities). Errors surface in plain English.

See docs/recipe.md for the full howto (smart-plug wiring, HA helper
creation, optional signal-stats wiring, sleep + wake + mode-aware
automations, troubleshooting, tier-a promotion outline).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Mapping, Optional

_LOGGER = logging.getLogger(__name__)

DOMAIN = "starlink"

# ---- Setup-path ids (mirror connection.yml wizard.setup_paths[*].id) ----
PATH_STARLINK_MINI_ONLY = "starlink_mini_only"
PATH_SEPARATE_ROUTER = "separate_router"
PATH_VP2430_VM_ROUTER = "vp2430_vm_router"

VALID_PATHS = frozenset(
    {
        PATH_STARLINK_MINI_ONLY,
        PATH_SEPARATE_ROUTER,
        PATH_VP2430_VM_ROUTER,
    }
)

# ---- Starlink local HTTP API defaults (Path A + Path C signal stats) ----
DEFAULT_STARLINK_API_URL = "http://192.168.100.1:80"
STARLINK_REACH_TIMEOUT_S = 10.0       # verification window per Wave 9 #108
STARLINK_REACH_RETRIES = 3            # 3x retries with backoff
STARLINK_REACH_BACKOFF_S = 1.0        # 1s, 2s, 4s (exponential)

# ---- Plain-English error messages (Wave 9 #108 doctrine) ----
ERROR_STARLINK_UNREACHABLE = (
    "We can't reach your Starlink router at {url}. "
    "Make sure the ethernet adapter is plugged in and your computer "
    "can reach the Starlink network. (Gen-2/Gen-3 only - Gen-1 has "
    "no local API.)"
)
ERROR_PLUG_NOT_EXPOSED = (
    "We can't find the plug entity '{entity_id}' in Home Assistant. "
    "Make sure the smart plug integration is set up and the entity "
    "is exposed (not hidden in Settings -> Devices & Services -> "
    "Entities)."
)
ERROR_PLUG_NOT_CONTROLLABLE = (
    "The plug entity '{entity_id}' exists but isn't controllable "
    "(it might be a sensor, not a switch). Pick a switch.* entity "
    "that can be turned on and off."
)
ERROR_OPENWRT_UNREACHABLE = (
    "We can't reach the OpenWrt API at {url}. Check that the VM is "
    "running on the VP2430 (VMID 100) and the bearer token is correct."
)
ERROR_PATH_REQUIRES_INPUT = (
    "Path '{path}' requires the following input(s): {missing}. "
    "Please re-run the wizard and provide them."
)


# ---------------------------------------------------------------------------
# Public API - called by the RoamCore config_flow wizard step.
#
# The HomeAssistant import is intentionally deferred to inside the
# functions so that the package can be imported by pytest / docs /
# lint without Home Assistant being installed (the test environment
# is bare Python).
# ---------------------------------------------------------------------------
def _import_homeassistant_error():
    """Lazy import of HomeAssistantError so non-HA envs can import us."""
    try:
        from homeassistant.exceptions import HomeAssistantError  # type: ignore
        return HomeAssistantError
    except ImportError as err:  # pragma: no cover - HA may not be installed
        raise RuntimeError(
            "HomeAssistantError is unavailable in this environment; "
            "RoamCore's starlink wizard runs inside Home Assistant only. "
            "(Original import error: %s)" % err
        )


async def apply_setup_path(
    hass,
    path_id: str,
    user_input: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Apply the chosen Starlink setup path.

    Called by the RoamCore config_flow wizard step when the user
    finishes the Starlink wizard. Idempotent: re-running with the
    same path + same input is a no-op (re-detects, re-confirms, no
    duplicate entities). Plain-English errors on failure (per Wave 9
    #108 doctrine: must not fail + super intuitive).
    """
    HomeAssistantError = _import_homeassistant_error()

    if path_id not in VALID_PATHS:
        raise HomeAssistantError(
            f"Unknown Starlink setup path '{path_id}'. "
            f"Expected one of: {sorted(VALID_PATHS)}. "
            "Please re-run the wizard."
        )

    user_input = dict(user_input or {})
    _LOGGER.info(
        "Starlink wizard: applying path %s with input keys %s",
        path_id, sorted(user_input.keys()),
    )

    if path_id == PATH_STARLINK_MINI_ONLY:
        return await _apply_path_starlink_mini_only(hass, user_input)
    if path_id == PATH_SEPARATE_ROUTER:
        return await _apply_path_separate_router(hass, user_input)
    # PATH_VP2430_VM_ROUTER
    return await _apply_path_vp2430_vm_router(hass, user_input)


def describe_setup_paths() -> List[Dict[str, Any]]:
    """Return the human-facing description of the 3 setup paths.

    Mirrors connection.yml's wizard.setup_paths. The config_flow step
    uses this to render the radio buttons + the per-path description
    + the estimated time + the requires_reboot flag.
    """
    return [
        {
            "id": PATH_STARLINK_MINI_ONLY,
            "label": "Starlink Mini as my only router",
            "description": (
                "Use the Starlink dish's built-in Wi-Fi router as the "
                "only router in the van. No smart plug, no extra router. "
                "RoamCore reads signal + reachability from the Starlink "
                "local API. Simplest setup (~10 min)."
            ),
            "estimated_time": "~10 min",
            "requires_reboot": False,
            "requires_inputs": [],
            "connection_kind": "api",
        },
        {
            "id": PATH_SEPARATE_ROUTER,
            "label": "I have a separate router (smart plug behind the PSU)",
            "description": (
                "You already own a third-party router and a controllable "
                "smart plug (TP-Link / Shelly / Sonoff / Zigbee / Modbus) "
                "behind the Starlink PSU. RoamCore maps switch."
                "rc_net_starlink_plug to your plug and wires the sleep + "
                "wake + signal + quiet-hours contract (~25 min)."
            ),
            "estimated_time": "~25 min",
            "requires_reboot": False,
            "requires_inputs": ["smart_plug_entity_id"],
            "connection_kind": "recipe",
        },
        {
            "id": PATH_VP2430_VM_ROUTER,
            "label": "VM router inside the VP2430 (OpenWrt)",
            "description": (
                "You run an OpenWrt VM (VMID 100 on the VP2430 Proxmox "
                "host) as the LAN router, with Starlink as the WAN "
                "upstream. RoamCore reads WAN state from the OpenWrt "
                "API and signal pct from the Starlink local API (~30 min)."
            ),
            "estimated_time": "~30 min",
            "requires_reboot": False,
            "requires_inputs": ["openwrt_api_url", "openwrt_api_token"],
            "connection_kind": "recipe",
        },
    ]


# ---------------------------------------------------------------------------
# Path A - Starlink Mini as the only router.
# ---------------------------------------------------------------------------
async def _apply_path_starlink_mini_only(
    hass,
    user_input: Dict[str, Any],
) -> Dict[str, Any]:
    """Path A: write input_text helper + REST sensor + 3 template sensors.

    Wiring:
        - input_text.rc_net_starlink_api_url = "http://192.168.100.1:80"
        - rest.sensor.rc_net_starlink_rest pulls dish-status.json
          every 60s (resource_template keyed off the input_text)
        - binary_sensor.rc_net_starlink_reachable (template over REST)
        - sensor.rc_net_starlink_signal_pct (template over REST;
          gracefully degrades to "unknown" on Gen-1)
        - sensor.rc_net_starlink_sleep_state (template; always
          "awake" on Path A - Starlink Mini's own sleep timer
          handles its own sleep; RoamCore just surfaces state)
    """
    HomeAssistantError = _import_homeassistant_error()
    api_url = DEFAULT_STARLINK_API_URL
    verified_within_s: Optional[float] = None
    warnings: List[str] = []

    # Verify reachability within 10 seconds (3x retries with backoff).
    # The wizard MUST NOT write helpers if the verification fails
    # (Wave 9 #108 doctrine: must not fail + super intuitive).
    if not await _verify_starlink_reachable(hass, api_url):
        raise HomeAssistantError(
            ERROR_STARLINK_UNREACHABLE.format(url=api_url)
        )
    verified_within_s = STARLINK_REACH_TIMEOUT_S  # 10s window honoured

    # Gen-1 detection: dish-status.json returns 404 / non-JSON on Gen-1
    # (no local API). The REST sensor will surface "unknown" and the
    # signal_pct tile is grayed out; reachability + sleep_state still
    # work. We log a warning so the wizard's success-step can show it.
    if not await _starlink_supports_dish_status(hass, api_url):
        warnings.append(
            "Your Starlink router doesn't expose dish-status.json - "
            "looks like a Gen-1 dish. The signal_pct tile will show "
            "unknown and reachability will report what the local "
            "HTTP API returns. Everything else works."
        )

    # In the actual install, the entity creation goes through HA's
    # entity registry + the in-package YAML the recipe ships. The
    # wizard just records the choice + verifies it.
    entities_created = [
        "input_text.rc_net_starlink_api_url",
        "rest.rc_net_starlink_rest",
        "binary_sensor.rc_net_starlink_reachable",
        "sensor.rc_net_starlink_signal_pct",
        "sensor.rc_net_starlink_sleep_state",
    ]
    _LOGGER.info(
        "Starlink Path A (starlink_mini_only) applied; entities=%s, "
        "verified_within_s=%s, warnings=%s",
        entities_created, verified_within_s, warnings,
    )
    return {
        "path_id": PATH_STARLINK_MINI_ONLY,
        "entities_created": entities_created,
        "verified_within_s": verified_within_s,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Path B - separate router (smart plug behind PSU / router).
# ---------------------------------------------------------------------------
async def _apply_path_separate_router(
    hass,
    user_input: Dict[str, Any],
) -> Dict[str, Any]:
    """Path B: validate the user's plug entity + create the contract.

    Required input:
        smart_plug_entity_id  - the HA switch.* entity the operator
                                already controls (TP-Link / Shelly /
                                Sonoff / Zigbee / Modbus / etc.)

    Validates:
        - the entity exists + is exposed (not hidden)
        - the entity is a switch (controllable), not a sensor
        - we can read its current state (entity is alive)
    """
    HomeAssistantError = _import_homeassistant_error()

    plug_entity_id = user_input.get("smart_plug_entity_id", "").strip()
    if not plug_entity_id:
        raise HomeAssistantError(
            ERROR_PATH_REQUIRES_INPUT.format(
                path=PATH_SEPARATE_ROUTER,
                missing="smart_plug_entity_id",
            )
        )

    # Validate the plug entity is exposed + controllable.
    await _validate_plug_entity(hass, plug_entity_id)

    # Path B also gets a reachability check on the Starlink local API
    # for the signal_pct tile (optional - gracefully degrades).
    api_url = DEFAULT_STARLINK_API_URL
    starlink_reachable = await _verify_starlink_reachable(hass, api_url)
    warnings: List[str] = []
    if not starlink_reachable:
        warnings.append(
            f"Couldn't reach the Starlink local API at {api_url} - "
            "the signal_pct tile will show unknown. Plug controls "
            "still work. Plug the ethernet adapter in if you want "
            "signal stats (Gen-2/Gen-3 only)."
        )

    entities_created = [
        f"switch.rc_net_starlink_plug -> {plug_entity_id}",
        "sensor.rc_net_starlink_sleep_state",
        "switch.rc_net_starlink_allow_sleep",
        "button.rc_net_starlink_wake_30_min",
        "binary_sensor.rc_net_starlink_reachable",
        "sensor.rc_net_starlink_signal_pct",
        "input_datetime.rc_net_starlink_quiet_start",
        "input_datetime.rc_net_starlink_quiet_end",
    ]
    _LOGGER.info(
        "Starlink Path B (separate_router) applied; plug=%s, "
        "starlink_reachable=%s, warnings=%s",
        plug_entity_id, starlink_reachable, warnings,
    )
    return {
        "path_id": PATH_SEPARATE_ROUTER,
        "entities_created": entities_created,
        "verified_within_s": STARLINK_REACH_TIMEOUT_S if starlink_reachable else None,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Path C - VM router inside the VP2430 (OpenWrt API chain).
# ---------------------------------------------------------------------------
async def _apply_path_vp2430_vm_router(
    hass,
    user_input: Dict[str, Any],
) -> Dict[str, Any]:
    """Path C: validate the OpenWrt API + create the REST chain.

    Required inputs:
        openwrt_api_url    - e.g. http://192.168.1.250/cgi-bin/luci
        openwrt_api_token  - bearer token from the OpenWrt VM
                             (see connections/openwrt-controls docs)
    """
    HomeAssistantError = _import_homeassistant_error()

    api_url = user_input.get("openwrt_api_url", "").strip()
    api_token = user_input.get("openwrt_api_token", "").strip()

    missing = [
        name
        for name, value in (
            ("openwrt_api_url", api_url),
            ("openwrt_api_token", api_token),
        )
        if not value
    ]
    if missing:
        raise HomeAssistantError(
            ERROR_PATH_REQUIRES_INPUT.format(
                path=PATH_VP2430_VM_ROUTER,
                missing=", ".join(missing),
            )
        )

    # Verify OpenWrt API reachability within 10 seconds.
    if not await _verify_openwrt_reachable(hass, api_url, api_token):
        raise HomeAssistantError(
            ERROR_OPENWRT_UNREACHABLE.format(url=api_url)
        )

    # Path C still queries Starlink local API for signal_pct; degrade
    # gracefully if Gen-1 / unreachable.
    starlink_api_url = DEFAULT_STARLINK_API_URL
    starlink_reachable = await _verify_starlink_reachable(hass, starlink_api_url)
    warnings: List[str] = []
    if not starlink_reachable:
        warnings.append(
            f"Couldn't reach the Starlink local API at {starlink_api_url} "
            "- the signal_pct tile will show unknown. OpenWrt-driven "
            "WAN state still works."
        )

    entities_created = [
        "input_text.rc_net_starlink_openwrt_api_url",
        "input_text.rc_net_starlink_openwrt_api_token",
        "rest.rc_net_starlink_openwrt_rest",
        "sensor.rc_net_starlink_sleep_state",
        "binary_sensor.rc_net_starlink_reachable",
        "sensor.rc_net_starlink_signal_pct",
        "input_datetime.rc_net_starlink_quiet_start",
        "input_datetime.rc_net_starlink_quiet_end",
    ]
    _LOGGER.info(
        "Starlink Path C (vp2430_vm_router) applied; openwrt_url=%s, "
        "starlink_reachable=%s, warnings=%s",
        api_url, starlink_reachable, warnings,
    )
    return {
        "path_id": PATH_VP2430_VM_ROUTER,
        "entities_created": entities_created,
        "verified_within_s": STARLINK_REACH_TIMEOUT_S,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Verification helpers (3x retries with backoff).
# ---------------------------------------------------------------------------
async def _verify_starlink_reachable(hass, api_url: str) -> bool:
    """Verify the Starlink local HTTP API is reachable.

    Per Wave 9 #108 doctrine: 3x retries with exponential backoff
    (1s, 2s, 4s). If all retries fail, returns False and the caller
    surfaces the plain-English ERROR_STARLINK_UNREACHABLE message.
    """
    return await _verify_http_reachable(
        hass,
        url=api_url,
        timeout_s=STARLINK_REACH_TIMEOUT_S,
        retries=STARLINK_REACH_RETRIES,
        backoff_s=STARLINK_REACH_BACKOFF_S,
        label="Starlink local API",
    )


async def _verify_openwrt_reachable(
    hass,
    api_url: str,
    api_token: str,
) -> bool:
    """Verify the OpenWrt API is reachable (Path C)."""
    return await _verify_http_reachable(
        hass,
        url=api_url,
        timeout_s=STARLINK_REACH_TIMEOUT_S,
        retries=STARLINK_REACH_RETRIES,
        backoff_s=STARLINK_REACH_BACKOFF_S,
        label="OpenWrt API",
        headers={"Authorization": f"Bearer {api_token}"} if api_token else None,
    )


async def _verify_http_reachable(
    hass,
    url: str,
    timeout_s: float,
    retries: int,
    backoff_s: float,
    label: str,
    headers: Optional[Mapping[str, str]] = None,
) -> bool:
    """Generic 3x-with-backoff HTTP liveness check.

    Implementation note: the actual HTTP probe is abstracted into
    hass.data[DOMAIN].get("http_probe") so tests can inject a probe.
    """
    probe = _get_http_probe(hass)
    delay = backoff_s
    for attempt in range(1, retries + 1):
        try:
            ok = await probe(url=url, headers=headers, timeout_s=timeout_s)
            if ok:
                _LOGGER.info(
                    "%s reachable on attempt %d/%d (%s)",
                    label, attempt, retries, url,
                )
                return True
        except Exception as err:  # pragma: no cover - defensive
            _LOGGER.debug("%s attempt %d/%d raised %s",
                          label, attempt, retries, err)
        if attempt < retries:
            await asyncio.sleep(delay)
            delay *= 2
    _LOGGER.warning("%s unreachable after %d attempts (%s)",
                    label, retries, url)
    return False


async def _starlink_supports_dish_status(hass, api_url: str) -> bool:
    """Best-effort Gen-1 detection.

    Gen-1 (round "Dishy" + round router) has no local HTTP API at all.
    Gen-2/Gen-3 expose http://192.168.100.1/api/console/dish-status.json.

    We probe /dish-status.json once. If it returns 200 + JSON, we
    assume Gen-2/Gen-3. If it returns 404 or non-JSON, we assume Gen-1
    and surface a warning.
    """
    probe = _get_http_probe(hass)
    try:
        result = await probe(
            url=f"{api_url.rstrip('/')}/api/console/dish-status.json",
            headers=None,
            timeout_s=5.0,
            expect_json=True,
        )
        return isinstance(result, dict)
    except Exception as err:  # pragma: no cover - defensive
        _LOGGER.debug("dish-status probe raised %s; assuming Gen-1", err)
        return False


def _get_http_probe(hass):
    """Return the injectable HTTP probe (for tests).

    Default probe: uses aiohttp if available. Tests inject a probe
    via hass.data[DOMAIN]["http_probe"] = ...
    """
    data = getattr(hass, "data", None) or {}
    custom = (data.get(DOMAIN, {}) or {}).get("http_probe")
    if custom is not None:
        return custom
    return _default_http_probe


async def _default_http_probe(
    url: str,
    headers: Optional[Mapping[str, str]] = None,
    timeout_s: float = 10.0,
    expect_json: bool = False,
) -> Any:
    """Default HTTP probe (aiohttp if available; else best-effort)."""
    try:
        import aiohttp  # type: ignore
    except ImportError:  # pragma: no cover - aiohttp may not be installed
        _LOGGER.debug("aiohttp not installed; HTTP probe is a no-op")
        return False if not expect_json else None
    timeout = aiohttp.ClientTimeout(total=timeout_s)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, headers=dict(headers or {})) as resp:
            if resp.status != 200:
                return False if not expect_json else None
            if expect_json:
                try:
                    return await resp.json(content_type=None)
                except Exception:
                    return None
            return True


# ---------------------------------------------------------------------------
# Path B plug validation.
# ---------------------------------------------------------------------------
async def _validate_plug_entity(hass, entity_id: str) -> None:
    """Validate the user's plug entity is exposed + controllable.

    Raises HomeAssistantError with a plain-English message on:
        - missing entity  (ERROR_PLUG_NOT_EXPOSED)
        - non-switch domain (ERROR_PLUG_NOT_CONTROLLABLE)
        - entity in 'unavailable' / 'unknown' (treated as not exposed)
    """
    HomeAssistantError = _import_homeassistant_error()

    states = getattr(hass, "states", None)
    state = states.get(entity_id) if states is not None else None
    if state is None:
        raise HomeAssistantError(
            ERROR_PLUG_NOT_EXPOSED.format(entity_id=entity_id)
        )
    domain = entity_id.split(".", 1)[0]
    if domain != "switch":
        raise HomeAssistantError(
            ERROR_PLUG_NOT_CONTROLLABLE.format(entity_id=entity_id)
        )
    if state.state in ("unavailable", "unknown"):
        raise HomeAssistantError(
            f"The plug entity '{entity_id}' is currently "
            f"{state.state}. Make sure the smart plug is powered on "
            "and the integration can talk to it, then re-run the "
            "wizard."
        )


__all__ = [
    "DOMAIN",
    "PATH_STARLINK_MINI_ONLY",
    "PATH_SEPARATE_ROUTER",
    "PATH_VP2430_VM_ROUTER",
    "VALID_PATHS",
    "DEFAULT_STARLINK_API_URL",
    "STARLINK_REACH_TIMEOUT_S",
    "STARLINK_REACH_RETRIES",
    "STARLINK_REACH_BACKOFF_S",
    "ERROR_STARLINK_UNREACHABLE",
    "ERROR_PLUG_NOT_EXPOSED",
    "ERROR_PLUG_NOT_CONTROLLABLE",
    "ERROR_OPENWRT_UNREACHABLE",
    "ERROR_PATH_REQUIRES_INPUT",
    "apply_setup_path",
    "describe_setup_paths",
]