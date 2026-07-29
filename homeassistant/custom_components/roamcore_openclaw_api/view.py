from __future__ import annotations

from datetime import timezone
from typing import Any

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .const import CONTRACT_VERSION

from aiohttp import web


def _state_or_none(hass: HomeAssistant, entity_id: str) -> str | None:
    st = hass.states.get(entity_id)
    if st is None:
        return None
    if st.state in ("unknown", "unavailable", "none", ""):
        return None
    return st.state


def _float_or_none(hass: HomeAssistant, entity_id: str) -> float | None:
    v = _state_or_none(hass, entity_id)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _bool_or_none(hass: HomeAssistant, entity_id: str) -> bool | None:
    st = hass.states.get(entity_id)
    if st is None:
        return None
    if st.state == "on":
        return True
    if st.state == "off":
        return False
    return None


def _attr_or_none(hass: HomeAssistant, entity_id: str, attr: str) -> Any:
    st = hass.states.get(entity_id)
    if st is None:
        return None
    return st.attributes.get(attr)


class RoamCoreOpenClawSummaryView(HomeAssistantView):
    """Return a stable summary of RoamCore contract entities for OpenClaw."""

    url = "/api/roamcore/openclaw/summary"
    name = "api:roamcore:openclaw:summary"
    def __init__(self, hass: HomeAssistant):
        self._hass = hass

    @property
    def requires_auth(self) -> bool:
        # Gate via helper so users can flip this without editing code.
        try:
            st = self._hass.states.get("input_boolean.rc_openclaw_api_requires_auth")
            return st is not None and st.state == "on"
        except Exception:
            return False

    def _enabled(self) -> bool:
        try:
            st = self._hass.states.get("input_boolean.rc_openclaw_api_enabled")
            # Default to enabled if helper is missing (back-compat).
            if st is None:
                return True
            return st.state == "on"
        except Exception:
            return True

    async def get(self, request):
        hass: HomeAssistant = request.app["hass"]

        # When disabled, return 404 so clients can treat it as "off".
        if not self._enabled():
            return web.json_response({"ok": False, "error": "disabled"}, status=404)

        # Entities used by the contract (prefer rc_* contract ids where they exist).
        # Power
        e_batt_soc = "sensor.rc_power_battery_soc"
        e_solar_w = "sensor.rc_power_solar_power"
        e_load_w = "sensor.rc_power_load_power"
        e_ac_in_w = "sensor.rc_power_ac_in_power"
        e_ac_out_w = "sensor.rc_power_ac_out_power"
        e_shore = "binary_sensor.rc_power_shore_connected"
        e_inv = "sensor.rc_power_inverter_status"

        # Power backend pairing health (already declared as rc_* contract
        # entities in homeassistant/packages/roamcore_victron_health.yaml).
        # These let OpenClaw answer "is Victron paired?" without scraping
        # the add-on.
        e_backend_connected = "binary_sensor.rc_system_power_backend_connected"
        e_backend_status = "sensor.rc_system_power_backend_status"
        e_backend_snapshot_state = "sensor.rc_system_power_backend_snapshot_state"
        e_backend_devices = "sensor.rc_system_power_backend_devices"
        e_backend_topics = "sensor.rc_system_power_backend_topics"

        # Map / location
        e_lat = "sensor.rc_location_lat"
        e_lon = "sensor.rc_location_lon"
        e_acc = "sensor.rc_location_accuracy_m"
        e_tile = "input_text.rc_map_tile_url"
        e_tile_online = "input_text.rc_map_tile_url_online"
        e_style = "input_text.rc_map_style_url"
        e_offline_max_zoom = "input_number.rc_map_offline_max_zoom"

        # Level
        e_pitch = "sensor.rc_system_level_pitch_deg"
        e_roll = "sensor.rc_system_level_roll_deg"
        e_level_ok = "binary_sensor.rc_system_level"
        e_level_status = "sensor.rc_system_level_status"
        e_level_hint = "sensor.rc_system_level_adjustment_hint"

        used_entities = [
            e_batt_soc,
            e_solar_w,
            e_load_w,
            e_ac_in_w,
            e_ac_out_w,
            e_shore,
            e_inv,
            e_backend_connected,
            e_backend_status,
            e_backend_snapshot_state,
            e_backend_devices,
            e_backend_topics,
            e_lat,
            e_lon,
            e_acc,
            e_tile,
            e_tile_online,
            e_style,
            e_offline_max_zoom,
            e_pitch,
            e_roll,
            e_level_ok,
            e_level_status,
            e_level_hint,
        ]

        # Include resolved entity names (nice for debugging consumers).
        ent_reg = er.async_get(hass)
        resolved: dict[str, dict[str, Any]] = {}
        for entity_id in used_entities:
            e = ent_reg.async_get(entity_id)
            resolved[entity_id] = {
                "exists": hass.states.get(entity_id) is not None,
                "name": _attr_or_none(hass, entity_id, "friendly_name"),
                "unique_id": getattr(e, "unique_id", None),
            }

        now = dt_util.utcnow()
        payload: dict[str, Any] = {
            "contract": {
                "name": "roamcore_openclaw_summary",
                "version": CONTRACT_VERSION,
            },
            "generated_at": now.replace(tzinfo=timezone.utc).isoformat(),
            "power": {
                "battery_soc_pct": _float_or_none(hass, e_batt_soc),
                "solar_power_w": _float_or_none(hass, e_solar_w),
                "load_power_w": _float_or_none(hass, e_load_w),
                "ac_in_power_w": _float_or_none(hass, e_ac_in_w),
                "ac_out_power_w": _float_or_none(hass, e_ac_out_w),
                "shore_connected": _bool_or_none(hass, e_shore),
                "inverter_status": _state_or_none(hass, e_inv),
            },
            # Power pairing status — lets OpenClaw answer "is Victron paired?"
            # and surface a one-line next action when it isn't.
            # See docs/guides/victron-connect-flow.md for the wizard flow.
            "pairing": {
                "victron_paired": _bool_or_none(hass, e_backend_connected),
                "backend_status": _state_or_none(hass, e_backend_status),
                "snapshot_state": _state_or_none(hass, e_backend_snapshot_state),
                "devices_count": _float_or_none(hass, e_backend_devices),
                "topics_count": _float_or_none(hass, e_backend_topics),
            },
            "map": {
                "lat": _float_or_none(hass, e_lat),
                "lon": _float_or_none(hass, e_lon),
                "accuracy_m": _float_or_none(hass, e_acc),
                "tile_url": _state_or_none(hass, e_tile),
                "tile_url_online": _state_or_none(hass, e_tile_online),
                "style_url": _state_or_none(hass, e_style),
                "offline_max_zoom": _float_or_none(hass, e_offline_max_zoom),
            },
            "level": {
                "pitch_deg": _float_or_none(hass, e_pitch),
                "roll_deg": _float_or_none(hass, e_roll),
                "is_level": _bool_or_none(hass, e_level_ok),
                "status": _state_or_none(hass, e_level_status),
                "hint": _state_or_none(hass, e_level_hint),
            },
            "debug": {
                "entities": resolved,
            },
        }

        return self.json(payload)


class RoamCoreOpenClawSkillView(HomeAssistantView):
    """Return copy/paste friendly agent config (legacy integration)."""

    url = "/api/roamcore/openclaw/skill"
    name = "api:roamcore:openclaw:skill"
    def __init__(self, hass: HomeAssistant):
        self._hass = hass

    @property
    def requires_auth(self) -> bool:
        try:
            st = self._hass.states.get("input_boolean.rc_openclaw_api_requires_auth")
            return st is not None and st.state == "on"
        except Exception:
            return False

    def _enabled(self) -> bool:
        try:
            st = self._hass.states.get("input_boolean.rc_openclaw_api_enabled")
            if st is None:
                return True
            return st.state == "on"
        except Exception:
            return True

    async def get(self, request):
        hass: HomeAssistant = request.app["hass"]

        if not self._enabled():
            return web.json_response({"ok": False, "error": "disabled"}, status=404)
        base = str(request.url).split("/api/roamcore/openclaw/skill", 1)[0]
        summary = f"{base}/api/roamcore/openclaw/summary"

        payload: dict[str, Any] = {
            "contract": {"name": "roamcore_openclaw_skill", "version": 1},
            "generated_at": dt_util.utcnow().replace(tzinfo=timezone.utc).isoformat(),
            "roamcore": {
                "openclaw_summary_url": summary,
                "requires_auth": bool(self.requires_auth),
                "summary_contract": {"name": "roamcore_openclaw_summary", "version": CONTRACT_VERSION},
            },
            "user_instructions": [
                "Copy openclaw_summary_url into your agent skill/config.",
                "If you expose Home Assistant beyond a trusted LAN, put it behind a VPN/proxy and enable auth.",
            ],
        }

        return self.json(payload)
