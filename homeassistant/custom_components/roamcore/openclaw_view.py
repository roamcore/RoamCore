from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.components.http import HomeAssistantView

from .const import (
    DOMAIN,
    CONF_OPENCLAW_API_REQUIRES_AUTH,
    DEFAULT_OPENCLAW_API_REQUIRES_AUTH,
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state_value(hass: HomeAssistant, entity_id: str) -> Optional[str]:
    st = hass.states.get(entity_id)
    if st is None:
        return None
    v = st.state
    if v in ("unknown", "unavailable", "none", ""):
        return None
    return v


def _state_float(hass: HomeAssistant, entity_id: str) -> Optional[float]:
    v = _state_value(hass, entity_id)
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def _state_bool(hass: HomeAssistant, entity_id: str) -> Optional[bool]:
    v = _state_value(hass, entity_id)
    if v is None:
        return None
    if v in ("on", "true", "True", "1"):
        return True
    if v in ("off", "false", "False", "0"):
        return False
    return None


class OpenClawSummaryView(HomeAssistantView):
    url = "/api/roamcore/openclaw/summary"
    name = "api:roamcore_openclaw_summary"

    def __init__(self, hass: HomeAssistant, entry_id: str):
        self._hass = hass
        self._entry_id = entry_id

    @property
    def requires_auth(self) -> bool:
        entry: Optional[ConfigEntry] = self._hass.config_entries.async_get_entry(self._entry_id)
        if not entry:
            return DEFAULT_OPENCLAW_API_REQUIRES_AUTH
        return bool(entry.options.get(CONF_OPENCLAW_API_REQUIRES_AUTH, DEFAULT_OPENCLAW_API_REQUIRES_AUTH))

    async def get(self, request):
        hass = self._hass

        # Contract sources (rc_* only)
        src = {
            "power": {
                "battery_soc_pct": "sensor.rc_power_battery_soc",
                "solar_power_w": "sensor.rc_power_solar_power",
                "load_power_w": "sensor.rc_power_load_power",
                "ac_in_power_w": "sensor.rc_power_ac_in_power",
                "ac_out_power_w": "sensor.rc_power_ac_out_power",
                "shore_connected": "binary_sensor.rc_power_shore_connected",
                "inverter_status": "sensor.rc_power_inverter_status",
            },
            "level": {
                "pitch_deg": "sensor.rc_level_pitch_deg",
                "roll_deg": "sensor.rc_level_roll_deg",
                "is_level": "binary_sensor.rc_level",
                "status": "sensor.rc_level_status",
                "hint": "sensor.rc_level_adjustment_hint",
            },
            "map": {
                "lat": "sensor.rc_location_lat",
                "lon": "sensor.rc_location_lon",
                "accuracy_m": "sensor.rc_location_accuracy_m",
                "style_url": "input_text.rc_map_style_url",
                "tile_url": "input_text.rc_map_tile_url",
                "tile_url_online": "input_text.rc_map_tile_url_online",
                "offline_max_zoom": "input_number.rc_map_offline_max_zoom",
            },
        }

        payload: dict[str, Any] = {
            "contract": {"name": "roamcore_openclaw_summary", "version": 1},
            "generated_at": _iso_now(),
            "power": {
                "battery_soc_pct": _state_float(hass, src["power"]["battery_soc_pct"]),
                "solar_power_w": _state_float(hass, src["power"]["solar_power_w"]),
                "load_power_w": _state_float(hass, src["power"]["load_power_w"]),
                "ac_in_power_w": _state_float(hass, src["power"]["ac_in_power_w"]),
                "ac_out_power_w": _state_float(hass, src["power"]["ac_out_power_w"]),
                "shore_connected": _state_bool(hass, src["power"]["shore_connected"]),
                "inverter_status": _state_value(hass, src["power"]["inverter_status"]),
            },
            "map": {
                "lat": _state_float(hass, src["map"]["lat"]),
                "lon": _state_float(hass, src["map"]["lon"]),
                "accuracy_m": _state_float(hass, src["map"]["accuracy_m"]),
                "style_url": _state_value(hass, src["map"]["style_url"]),
                "tile_url": _state_value(hass, src["map"]["tile_url"]),
                "tile_url_online": _state_value(hass, src["map"]["tile_url_online"]),
                "offline_max_zoom": _state_float(hass, src["map"]["offline_max_zoom"]),
            },
            "level": {
                "pitch_deg": _state_float(hass, src["level"]["pitch_deg"]),
                "roll_deg": _state_float(hass, src["level"]["roll_deg"]),
                "is_level": _state_bool(hass, src["level"]["is_level"]),
                "status": _state_value(hass, src["level"]["status"]),
                "hint": _state_value(hass, src["level"]["hint"]),
            },
        }

        # Debug block: entity existence + availability (helps fix install/mapping)
        reg = async_get_entity_registry(hass)
        debug_entities: dict[str, Any] = {}
        for group, mapping in src.items():
            for key, eid in mapping.items():
                st = hass.states.get(eid)
                debug_entities[f"{group}.{key}"] = {
                    "entity_id": eid,
                    "exists": st is not None,
                    "state": None if st is None else st.state,
                    "registry": eid in reg.entities,
                }

        payload["debug"] = {"entities": debug_entities}

        return self.json(payload)

