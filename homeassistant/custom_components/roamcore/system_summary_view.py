from __future__ import annotations

import json
import os
from .contract_header import apply_contract_header
from datetime import datetime, timezone
from typing import Any, Optional

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant


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
    st = hass.states.get(entity_id)
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


class RoamcoreSystemSummaryView(HomeAssistantView):
    """Deterministic, user-facing system summary.

    Intent:
    - stable keys (good for UI + agents)
    - boring + consistent (avoid huge debug dumps)
    - best-effort (never break due to missing entities)
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
        setup_ready = all(v is True for k, v in setup.items() if k.endswith("_ready"))

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
        # Rules:
        # - error if setup not ready AND we have explicit False on any *_ready sensor
        # - warn if unknowns prevent readiness determination
        # - ok otherwise
        ready_values = [setup.get("owner_ready"), setup.get("map_ready"), setup.get("trip_wrapped_ready"), setup.get("victron_ready")]
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

        payload: dict[str, Any] = {
            "contract": {"name": "roamcore_system_summary", "version": 1},
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
        }

        return apply_contract_header(self.json(payload))
