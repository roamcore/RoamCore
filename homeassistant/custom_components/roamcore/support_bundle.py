from __future__ import annotations

import json
import os
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from .openclaw_view import TIMESERIES_CATALOG


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _read_text(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


def _copy_file(src: str, dest: str) -> bool:
    try:
        _ensure_dir(os.path.dirname(dest))
        with open(src, "rb") as rf, open(dest, "wb") as wf:
            wf.write(rf.read())
        return True
    except FileNotFoundError:
        return False


def _write_json(path: str, payload: Any) -> None:
    _ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")


def _zip_dir(src_dir: str, zip_path: str) -> None:
    """Create a zip containing all files under src_dir."""
    _ensure_dir(os.path.dirname(zip_path))
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for base, _, files in os.walk(src_dir):
            for fn in files:
                fp = os.path.join(base, fn)
                arc = os.path.relpath(fp, os.path.dirname(src_dir))
                zf.write(fp, arcname=arc)


@dataclass
class EntitySnapshot:
    entity_id: str
    state: Optional[str]
    attributes: dict[str, Any]
    last_changed: Optional[str]
    last_updated: Optional[str]


def _snapshot_entity(hass: HomeAssistant, entity_id: str, *, include_attributes: bool = True) -> EntitySnapshot:
    st = hass.states.get(entity_id)
    if st is None:
        return EntitySnapshot(
            entity_id=entity_id,
            state=None,
            attributes={},
            last_changed=None,
            last_updated=None,
        )

    raw = st.state
    v = None if raw in ("unknown", "unavailable", "none", "") else str(raw)
    attrs = dict(getattr(st, "attributes", {}) or {}) if include_attributes else {}
    lc = getattr(st, "last_changed", None)
    lu = getattr(st, "last_updated", None)

    return EntitySnapshot(
        entity_id=entity_id,
        state=v,
        attributes=attrs,
        last_changed=lc.isoformat() if lc else None,
        last_updated=lu.isoformat() if lu else None,
    )


async def export_support_bundle(hass: HomeAssistant, *, include_zip: bool = True) -> dict[str, Any]:
    """Export a RoamCore support bundle under /config/.roamcore/support/<timestamp>/.

    Bundle contents are best-effort and intentionally avoid secrets.

    Returns:
        {"dir": <dir>, "zip": <zip_or_none>}
    """

    ts = _ts()
    out_dir = hass.config.path(".roamcore", "support", ts)

    await hass.async_add_executor_job(lambda: _ensure_dir(out_dir))

    # Copy key RoamCore installer/provisioning state (if present)
    copied: dict[str, bool] = {}
    missing: list[str] = []

    def _copy(rel_src: str, dest_name: str) -> None:
        src = hass.config.path(rel_src)
        dest = os.path.join(out_dir, dest_name)
        ok = _copy_file(src, dest)
        copied[dest_name] = ok
        if not ok:
            missing.append(rel_src)

    await hass.async_add_executor_job(lambda: _copy(".roamcore/install-info.txt", "install-info.txt"))
    await hass.async_add_executor_job(lambda: _copy(".roamcore/manifest.txt", "manifest.txt"))
    await hass.async_add_executor_job(lambda: _copy(".roamcore/provisioned.marker", "provisioned.marker"))

    # Snapshot OpenClaw summary-like state (no HTTP required)
    summary_src = {
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

    reg = async_get_entity_registry(hass)

    def _value(entity_id: str) -> Optional[str]:
        s = hass.states.get(entity_id)
        if s is None:
            return None
        raw = s.state
        if raw in ("unknown", "unavailable", "none", ""):
            return None
        return str(raw)

    def _num(entity_id: str) -> Optional[float]:
        v = _value(entity_id)
        if v is None:
            return None
        try:
            return float(v)
        except Exception:
            return None

    def _bool(entity_id: str) -> Optional[bool]:
        v = _value(entity_id)
        if v is None:
            return None
        if v in ("on", "true", "True", "1"):
            return True
        if v in ("off", "false", "False", "0"):
            return False
        return None

    debug_entities: dict[str, Any] = {}
    for group, mapping in summary_src.items():
        for key, eid in mapping.items():
            st = hass.states.get(eid)
            debug_entities[f"{group}.{key}"] = {
                "entity_id": eid,
                "exists": st is not None,
                "state": None if st is None else st.state,
                "registry": eid in reg.entities,
            }

    openclaw_summary = {
        "contract": {"name": "roamcore_openclaw_summary", "version": 1},
        "generated_at": _iso_now(),
        "power": {
            "battery_soc_pct": _num(summary_src["power"]["battery_soc_pct"]),
            "solar_power_w": _num(summary_src["power"]["solar_power_w"]),
            "load_power_w": _num(summary_src["power"]["load_power_w"]),
            "ac_in_power_w": _num(summary_src["power"]["ac_in_power_w"]),
            "ac_out_power_w": _num(summary_src["power"]["ac_out_power_w"]),
            "shore_connected": _bool(summary_src["power"]["shore_connected"]),
            "inverter_status": _value(summary_src["power"]["inverter_status"]),
        },
        "map": {
            "lat": _num(summary_src["map"]["lat"]),
            "lon": _num(summary_src["map"]["lon"]),
            "accuracy_m": _num(summary_src["map"]["accuracy_m"]),
            "style_url": _value(summary_src["map"]["style_url"]),
            "tile_url": _value(summary_src["map"]["tile_url"]),
            "tile_url_online": _value(summary_src["map"]["tile_url_online"]),
            "offline_max_zoom": _num(summary_src["map"]["offline_max_zoom"]),
        },
        "level": {
            "pitch_deg": _num(summary_src["level"]["pitch_deg"]),
            "roll_deg": _num(summary_src["level"]["roll_deg"]),
            "is_level": _bool(summary_src["level"]["is_level"]),
            "status": _value(summary_src["level"]["status"]),
            "hint": _value(summary_src["level"]["hint"]),
        },
        "debug": {"entities": debug_entities},
    }

    # Snapshot OpenClaw time-series catalog-like payload
    catalog_items: dict[str, Any] = {}
    for key, meta in TIMESERIES_CATALOG.items():
        eid = str(meta.get("entity_id"))
        st = hass.states.get(eid)
        attrs = dict(getattr(st, "attributes", {}) or {}) if st else {}
        catalog_items[key] = {
            "entity_id": eid,
            "kind": meta.get("kind"),
            "unit": attrs.get("unit_of_measurement"),
            "device_class": attrs.get("device_class"),
            "state_class": attrs.get("state_class"),
        }

    openclaw_catalog = {
        "contract": {"name": "roamcore_openclaw_timeseries_catalog", "version": 1},
        "generated_at": _iso_now(),
        "count": len(catalog_items),
        "keys": catalog_items,
    }

    # Snapshot setup wizard progress states (avoid any secret fields)
    setup_entities = [
        "input_select.rc_setup_stage",
        "sensor.rc_setup_progress",
        "binary_sensor.rc_setup_owner_ready",
        "binary_sensor.rc_setup_map_ready",
        "binary_sensor.rc_setup_trip_wrapped_ready",
        "binary_sensor.rc_setup_victron_ready",
    ]

    setup_states = {eid: _snapshot_entity(hass, eid, include_attributes=True).__dict__ for eid in setup_entities}

    # Write files to disk
    await hass.async_add_executor_job(lambda: _write_json(os.path.join(out_dir, "openclaw-summary.json"), openclaw_summary))
    await hass.async_add_executor_job(
        lambda: _write_json(os.path.join(out_dir, "openclaw-timeseries-catalog.json"), openclaw_catalog)
    )
    await hass.async_add_executor_job(lambda: _write_json(os.path.join(out_dir, "setup-wizard-states.json"), setup_states))

    meta = {
        "generated_at": _iso_now(),
        "bundle_dir": out_dir,
        "copied": copied,
        "missing": missing,
    }
    await hass.async_add_executor_job(lambda: _write_json(os.path.join(out_dir, "bundle-meta.json"), meta))

    zip_out: Optional[str] = None
    if include_zip:
        try:
            zip_out = hass.config.path(".roamcore", "support", f"{ts}.zip")
            await hass.async_add_executor_job(lambda: _zip_dir(out_dir, zip_out))
        except Exception:
            zip_out = None

    return {"dir": out_dir, "zip": zip_out}
