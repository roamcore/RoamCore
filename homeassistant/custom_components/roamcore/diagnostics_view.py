from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from .const import (
    DOMAIN,
    CONF_CONTRACT_VERSION,
    CONF_OPENCLAW_API_ENABLED,
    CONF_OPENCLAW_API_REQUIRES_AUTH,
    CONF_AUTO_PROVISION_ASSETS,
    CONF_PROVISION_REF,
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_text(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


def _parse_kv(text: Optional[str]) -> dict[str, str]:
    """Parse key=value lines (best-effort)."""
    out: dict[str, str] = {}
    if not text:
        return out
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        if "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        k = k.strip()
        v = v.strip()
        if k:
            out[k] = v
    return out


def _manifest_version() -> Optional[str]:
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


def _state_snapshot(hass: HomeAssistant, entity_id: str) -> dict[str, Any]:
    st = hass.states.get(entity_id)
    if st is None:
        return {
            "entity_id": entity_id,
            "exists": False,
            "state": None,
            "attributes": {},
            "last_changed": None,
            "last_updated": None,
        }

    return {
        "entity_id": entity_id,
        "exists": True,
        "state": st.state,
        # Keep attributes because they often contain units + device_class.
        # This is still safe: HA state attributes should not contain secrets.
        "attributes": dict(getattr(st, "attributes", {}) or {}),
        "last_changed": getattr(st, "last_changed", None).isoformat() if getattr(st, "last_changed", None) else None,
        "last_updated": getattr(st, "last_updated", None).isoformat() if getattr(st, "last_updated", None) else None,
    }


KEY_ENTITIES: list[str] = [
    # Setup wizard
    "input_select.rc_setup_stage",
    "sensor.rc_setup_progress",
    "binary_sensor.rc_setup_owner_ready",
    "binary_sensor.rc_setup_map_ready",
    "binary_sensor.rc_setup_trip_wrapped_ready",
    "binary_sensor.rc_setup_victron_ready",
    # Victron health
    "binary_sensor.rc_system_power_backend_connected",
    "sensor.rc_system_power_backend_status",
    "sensor.rc_system_power_backend_snapshot_state",
    "sensor.rc_system_power_backend_devices",
    "sensor.rc_system_power_backend_topics",
    # Dashboard essentials
    "sensor.rc_power_battery_soc",
    "sensor.rc_power_solar_power",
    "sensor.rc_power_load_power",
    "binary_sensor.rc_power_shore_connected",
    "sensor.rc_power_inverter_status",
    "sensor.rc_net_wan_status",
    "sensor.rc_net_wan_source",
    "sensor.rc_net_ping",
    "sensor.rc_net_download",
    "sensor.rc_net_upload",
    # Location
    "sensor.rc_location_lat",
    "sensor.rc_location_lon",
    "sensor.rc_map_location",
    "sensor.rc_trip_distance_today_mi",
    "sensor.rc_trip_distance_total_mi",
    # Level (support both naming variants)
    "sensor.rc_system_level_pitch_deg",
    "sensor.rc_system_level_roll_deg",
    "sensor.rc_level_pitch_deg",
    "sensor.rc_level_roll_deg",
]


class RoamcoreDiagnosticsView(HomeAssistantView):
    """Diagnostics endpoint for the RoamCore UI.

    Intended for support and bring-up.
    """

    url = "/api/roamcore/diagnostics"
    name = "api:roamcore_diagnostics"

    def __init__(self, hass: HomeAssistant, entry_id: str):
        self._hass = hass
        self._entry_id = entry_id

    async def get(self, request):
        hass = self._hass

        q = request.query
        include_rc_dump = str(q.get("include_rc_dump") or "").lower() in ("1", "true", "yes", "on")

        entry: Optional[ConfigEntry] = hass.config_entries.async_get_entry(self._entry_id)
        options = dict(entry.options) if entry else {}

        safe_option_keys = [
            CONF_CONTRACT_VERSION,
            CONF_OPENCLAW_API_ENABLED,
            CONF_OPENCLAW_API_REQUIRES_AUTH,
            CONF_AUTO_PROVISION_ASSETS,
            CONF_PROVISION_REF,
        ]
        safe_options = {k: options.get(k) for k in safe_option_keys if k in options}

        install_info_path = hass.config.path(".roamcore", "install-info.txt")
        provision_marker_path = hass.config.path(".roamcore", "provisioned.marker")

        install_info = await hass.async_add_executor_job(lambda: _read_text(install_info_path))
        provision_marker = await hass.async_add_executor_job(lambda: _read_text(provision_marker_path))

        # Absolute links are nicer for copy/paste support.
        base = str(request.url).split("/api/roamcore/diagnostics", 1)[0]

        reg = async_get_entity_registry(hass)
        key_entity_snapshots = []
        for eid in KEY_ENTITIES:
            snap = _state_snapshot(hass, eid)
            snap["registry"] = eid in reg.entities
            key_entity_snapshots.append(snap)

        payload: dict[str, Any] = {
            "contract": {"name": "roamcore_diagnostics", "version": 1},
            "generated_at": _iso_now(),
            "hass": {
                "version": getattr(hass.config, "version", None),
                "timezone": getattr(hass.config, "time_zone", None),
            },
            "roamcore": {
                "domain": DOMAIN,
                "component_version": _manifest_version(),
                "config_entry": {
                    "entry_id": entry.entry_id if entry else None,
                    "title": entry.title if entry else None,
                    "options": safe_options,
                },
            },
            "install": {
                "install_info": {
                    "path": "/config/.roamcore/install-info.txt",
                    "exists": install_info is not None,
                    "raw": install_info,
                    "parsed": _parse_kv(install_info),
                },
                "provisioned_marker": {
                    "path": "/config/.roamcore/provisioned.marker",
                    "exists": provision_marker is not None,
                    "raw": provision_marker,
                    "parsed": _parse_kv(provision_marker),
                },
            },
            "entities": {
                "key": key_entity_snapshots,
            },
            "endpoints": {
                "base_url": base,
                "diagnostics": f"{base}/api/roamcore/diagnostics",
                "openclaw_summary": f"{base}/api/roamcore/openclaw/summary",
                "openclaw_skill": f"{base}/api/roamcore/openclaw/skill",
                "openclaw_rc_dump": f"{base}/api/roamcore/openclaw/rc_dump",
                "openclaw_timeseries_catalog": f"{base}/api/roamcore/openclaw/timeseries/catalog",
                "openclaw_timeseries": f"{base}/api/roamcore/openclaw/timeseries",
            },
        }

        if include_rc_dump:
            out: dict[str, Any] = {}
            for st in hass.states.async_all():
                try:
                    eid = str(getattr(st, "entity_id", ""))
                    if not eid or ".rc_" not in eid:
                        continue
                    out[eid] = {
                        "state": st.state,
                        "attributes": dict(getattr(st, "attributes", {}) or {}),
                        "last_changed": getattr(st, "last_changed", None).isoformat() if getattr(st, "last_changed", None) else None,
                        "last_updated": getattr(st, "last_updated", None).isoformat() if getattr(st, "last_updated", None) else None,
                        "registry": eid in reg.entities,
                    }
                except Exception:
                    continue
            payload["entities"]["rc_dump"] = {
                "count": len(out),
                "entities": out,
            }

        return self.json(payload)

