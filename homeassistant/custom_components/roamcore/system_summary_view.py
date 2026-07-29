from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

# Contract version for /api/roamcore/system/summary.
# Bump ONLY on breaking schema changes. UI + agents rely on this number.
CONTRACT_NAME = "roamcore_system_summary"
CONTRACT_VERSION = 2

# Stable, frozen-ish set of required top-level keys (schema hint for UI + agents).
# This is intentionally a Python list (not a JSON Schema validator); we keep it
# boring so the contract is easy to embed in TypeScript/Go/Python consumers.
REQUIRED_KEYS = [
    "contract",
    "generated_at",
    "overall",
    "roamcore",
    "setup",
    "power_backend",
    "network",
    "diagnostics",
]


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_text(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


def _manifest_version() -> Optional[str]:
    """Return RoamCore HA component version from manifest.json (best-effort)."""

    try:
        here = os.path.dirname(__file__)
        p = os.path.join(here, "manifest.json")
        raw = _read_text(p)
        if not raw:
            return None
        obj = json.loads(raw)
        v = obj.get("version")
        return str(v) if v else None
    except Exception:
        return None


def _state_value(hass: HomeAssistant, entity_id: str) -> Optional[str]:
    """Return a stringified state for ``entity_id`` or ``None`` if missing/unknown.

    Truly silent: never raises. Missing/unknown/unavailable/empty all map to
    ``None`` so consumers can render "—" without needing a try/except.
    """
    try:
        st = hass.states.get(entity_id)
    except Exception:
        return None
    if st is None:
        return None
    v = st.state
    if v in ("unknown", "unavailable", "none", ""):
        return None
    return str(v)


def _state_bool(hass: HomeAssistant, entity_id: str) -> Optional[bool]:
    v = _state_value(hass, entity_id)
    if v is None:
        return None
    if v in ("on", "true", "True", "1"):
        return True
    if v in ("off", "false", "False", "0"):
        return False
    return None


def _summary_diagnostics(hass: HomeAssistant) -> dict[str, Any]:
    """Return a tiny trust-indicator dict.

    Shape:
        {
            "signals_total": <int>,
            "signals_ok": <int>,    # entities we could read as a usable value
            "signals_unknown": <int> # missing / unknown / unavailable / non-bool
        }

    Intentionally compact: we only count the boolean + scalar signals that
    already feed the overall status, so the diagnostic stays < 1 KB and stays
    deterministic.
    """
    # Keep this list in lock-step with the *primary* signals used below.
    bool_signals = [
        "binary_sensor.rc_setup_owner_ready",
        "binary_sensor.rc_setup_map_ready",
        "binary_sensor.rc_setup_trip_wrapped_ready",
        "binary_sensor.rc_setup_victron_ready",
        "binary_sensor.rc_system_power_backend_connected",
    ]
    value_signals = [
        "input_select.rc_setup_stage",
        "sensor.rc_system_power_backend_status",
        "sensor.rc_net_wan_status",
        "sensor.rc_net_wan_source",
    ]

    ok = 0
    unknown = 0
    for eid in bool_signals:
        if _state_bool(hass, eid) is None:
            unknown += 1
        else:
            ok += 1
    for eid in value_signals:
        if _state_value(hass, eid) is None:
            unknown += 1
        else:
            ok += 1

    total = ok + unknown
    return {
        "signals_total": total,
        "signals_ok": ok,
        "signals_unknown": unknown,
    }


class RoamcoreSystemSummaryView(HomeAssistantView):
    """Deterministic, user-facing system summary.

    Intent:
    - stable keys (good for UI + agents)
    - boring + consistent (avoid huge debug dumps)
    - best-effort (never break due to missing entities)
    - stable top-level key order (sorted alphabetically) so JSON consumers
      don't need to normalize before diffing.

    Contract version 2 adds:
    - ``diagnostics`` (signals_ok / signals_unknown) for the trust indicator
    - ``schema`` (frozen-ish required-key list)
    - sorted top-level keys (stable across requests)
    """

    url = "/api/roamcore/system/summary"
    name = "api:roamcore_system_summary"

    def __init__(self, hass: HomeAssistant):
        self._hass = hass

    async def get(self, request):
        hass = self._hass

        # Setup readiness
        setup = {
            "stage": _state_value(hass, "input_select.rc_setup_stage"),
            "owner_ready": _state_bool(hass, "binary_sensor.rc_setup_owner_ready"),
            "map_ready": _state_bool(hass, "binary_sensor.rc_setup_map_ready"),
            "trip_wrapped_ready": _state_bool(hass, "binary_sensor.rc_setup_trip_wrapped_ready"),
            "victron_ready": _state_bool(hass, "binary_sensor.rc_setup_victron_ready"),
        }
        ready_values = [
            setup.get("owner_ready"),
            setup.get("map_ready"),
            setup.get("trip_wrapped_ready"),
            setup.get("victron_ready"),
        ]
        setup_ready = all(v is True for v in ready_values)

        # Backend health
        power_backend = {
            "connected": _state_bool(hass, "binary_sensor.rc_system_power_backend_connected"),
            "status": _state_value(hass, "sensor.rc_system_power_backend_status"),
        }

        net = {
            "wan_status": _state_value(hass, "sensor.rc_net_wan_status"),
            "wan_source": _state_value(hass, "sensor.rc_net_wan_source"),
        }

        # Simple deterministic overall status.
        # Rules (unchanged from v1):
        # - error if any *_ready sensor is explicitly False
        # - warn if any *_ready sensor is unknown/unavailable
        # - ok if all *_ready sensors are True
        any_false = any(v is False for v in ready_values)
        any_unknown = any(v is None for v in ready_values)
        if any_false:
            overall = "error"
        elif any_unknown:
            overall = "warn"
        elif setup_ready:
            overall = "ok"
        else:
            overall = "warn"

        # NOTE: we keep this dict in logical (not alphabetic) order in source
        # for readability. The response body is serialized with ``sort_keys=True``
        # below so consumers see a stable alphabetic top-level layout.
        payload: dict[str, Any] = {
            "contract": {"name": CONTRACT_NAME, "version": CONTRACT_VERSION},
            "schema": {
                "type": "object",
                "required": list(REQUIRED_KEYS),
            },
            "generated_at": _iso_now(),
            "overall": overall,
            "roamcore": {
                "component_version": _manifest_version(),
            },
            "setup": {
                **setup,
                "ready": setup_ready,
            },
            "power_backend": power_backend,
            "network": net,
            "diagnostics": _summary_diagnostics(hass),
        }

        # Final response: deterministic, sorted keys at the top level.
        # (Nested dicts keep their natural order so sub-objects still read well
        # in logs and in the docs page.)
        #
        # We bypass ``self.json(payload)`` because HA's default JSON encoder
        # preserves insertion order — we need an explicitly-sorted body so
        # consumers see a stable alphabetic top-level layout request-to-request.
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return web.Response(
            text=body,
            status=200,
            content_type="application/json",
            charset="utf-8",
            headers={"Cache-Control": "no-store"},
        )