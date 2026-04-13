from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.components.http import HomeAssistantView
from homeassistant.components.recorder import history
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_OPENCLAW_API_ENABLED,
    DEFAULT_OPENCLAW_API_ENABLED,
    CONF_OPENCLAW_API_REQUIRES_AUTH,
    DEFAULT_OPENCLAW_API_REQUIRES_AUTH,
)

from aiohttp import web

from .automation_intents import INTENT_CONTRACT, SUPPORTED_INTENTS, validate_intent


def _openclaw_enabled(hass: HomeAssistant, entry_id: str) -> bool:
    try:
        entry: Optional[ConfigEntry] = hass.config_entries.async_get_entry(entry_id)
        if not entry:
            return bool(DEFAULT_OPENCLAW_API_ENABLED)
        return bool(entry.options.get(CONF_OPENCLAW_API_ENABLED, DEFAULT_OPENCLAW_API_ENABLED))
    except Exception:
        return bool(DEFAULT_OPENCLAW_API_ENABLED)


def _mark_openclaw_last_seen(hass: HomeAssistant, entry_id: str, endpoint: str) -> None:
    """Best-effort onboarding signal: record when an OpenClaw endpoint was hit."""

    try:
        per_entry = hass.data.setdefault(DOMAIN, {}).setdefault(entry_id, {})
        per_entry["openclaw_last_seen"] = {
            "ts": dt_util.utcnow(),
            "endpoint": str(endpoint or ""),
        }
        ent = per_entry.get("openclaw_last_seen_entity")
        if ent is not None and hasattr(ent, "async_mark_seen"):
            ent.async_mark_seen(endpoint)
    except Exception:
        # Never break API responses.
        return


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_num(v: Optional[str]) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def _parse_bool(v: Optional[str]) -> Optional[bool]:
    if v is None:
        return None
    if v in ("on", "true", "True", "1"):
        return True
    if v in ("off", "false", "False", "0"):
        return False
    return None


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

        # Option-gated: return 404 when disabled so it's safe to leave this
        # integration installed but keep the API off by default.
        if not _openclaw_enabled(hass, self._entry_id):
            return web.Response(status=404)

        _mark_openclaw_last_seen(hass, self._entry_id, "summary")

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
            "agent_actions": {
                "enabled": _state_bool(hass, "input_boolean.rc_agent_actions_enabled"),
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


class OpenClawSkillView(HomeAssistantView):
    """Convenience endpoint to help users configure an agent quickly."""

    url = "/api/roamcore/openclaw/skill"
    name = "api:roamcore_openclaw_skill"

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
        if not _openclaw_enabled(self._hass, self._entry_id):
            return web.Response(status=404)

        base = str(request.url).split("/api/roamcore/openclaw/skill", 1)[0]
        summary = f"{base}/api/roamcore/openclaw/summary"
        payload: dict[str, Any] = {
            "contract": {"name": "roamcore_openclaw_skill", "version": 1},
            "generated_at": _iso_now(),
            "roamcore": {
                "openclaw_summary_url": summary,
                "requires_auth": bool(self.requires_auth),
                "summary_contract": {"name": "roamcore_openclaw_summary", "version": 1},
            },
            "user_instructions": [
                "Copy the openclaw_summary_url into your agent skill/config.",
                "If requires_auth=true, configure your agent to send a Home Assistant Long-Lived Access Token as a Bearer token.",
            ],
        }
        return self.json(payload)


class OpenClawRcDumpView(HomeAssistantView):
    """Diagnostic endpoint: dump all rc_* entity states.

    This is intentionally *not* a stable contract for downstream automation.
    It's meant for debugging and to help agent skills introspect what's available.
    """

    url = "/api/roamcore/openclaw/rc_dump"
    name = "api:roamcore_openclaw_rc_dump"

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
        if not _openclaw_enabled(self._hass, self._entry_id):
            return web.Response(status=404)

        _mark_openclaw_last_seen(self._hass, self._entry_id, "rc_dump")
        hass = self._hass
        reg = async_get_entity_registry(hass)

        out: dict[str, Any] = {}
        for st in hass.states.async_all():
            try:
                eid = str(getattr(st, "entity_id", ""))
                if not eid:
                    continue
                # include all domains, but only rc_ object_id
                if ".rc_" not in eid:
                    continue

                raw = st.state
                v = None if raw in ("unknown", "unavailable", "none", "") else raw

                out[eid] = {
                    "state": v,
                    "num": _parse_num(v),
                    "bool": _parse_bool(v),
                    "attributes": dict(getattr(st, "attributes", {}) or {}),
                    "last_changed": getattr(st, "last_changed", None).isoformat() if getattr(st, "last_changed", None) else None,
                    "last_updated": getattr(st, "last_updated", None).isoformat() if getattr(st, "last_updated", None) else None,
                    "registry": eid in reg.entities,
                }
            except Exception:
                continue

        payload: dict[str, Any] = {
            "contract": {"name": "roamcore_openclaw_rc_dump", "version": 1},
            "generated_at": _iso_now(),
            "count": len(out),
            "entities": out,
        }
        return self.json(payload)


# A curated set of time-series keys for agent-friendly analysis.
# We keep this intentionally small and stable to avoid massive payloads.
TIMESERIES_CATALOG: dict[str, dict[str, Any]] = {
    # Power
    "power.battery_soc_pct": {"entity_id": "sensor.rc_power_battery_soc", "kind": "number"},
    "power.solar_power_w": {"entity_id": "sensor.rc_power_solar_power", "kind": "number"},
    "power.load_power_w": {"entity_id": "sensor.rc_power_load_power", "kind": "number"},
    "power.ac_in_power_w": {"entity_id": "sensor.rc_power_ac_in_power", "kind": "number"},
    "power.ac_out_power_w": {"entity_id": "sensor.rc_power_ac_out_power", "kind": "number"},
    "power.shore_connected": {"entity_id": "binary_sensor.rc_power_shore_connected", "kind": "bool"},
    # Level
    "level.pitch_deg": {"entity_id": "sensor.rc_level_pitch_deg", "kind": "number"},
    "level.roll_deg": {"entity_id": "sensor.rc_level_roll_deg", "kind": "number"},
    "level.is_level": {"entity_id": "binary_sensor.rc_level", "kind": "bool"},
    # Map
    "map.lat": {"entity_id": "sensor.rc_location_lat", "kind": "number"},
    "map.lon": {"entity_id": "sensor.rc_location_lon", "kind": "number"},
    "map.accuracy_m": {"entity_id": "sensor.rc_location_accuracy_m", "kind": "number"},
}


class OpenClawTimeSeriesCatalogView(HomeAssistantView):
    """Discoverable list of supported time-series keys.

    The agent should call this first, then request only what it needs.
    """

    url = "/api/roamcore/openclaw/timeseries/catalog"
    name = "api:roamcore_openclaw_timeseries_catalog"

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
        if not _openclaw_enabled(self._hass, self._entry_id):
            return web.Response(status=404)

        _mark_openclaw_last_seen(self._hass, self._entry_id, "timeseries_catalog")
        hass = self._hass
        items: dict[str, Any] = {}
        for key, meta in TIMESERIES_CATALOG.items():
            eid = str(meta.get("entity_id"))
            st = hass.states.get(eid)
            attrs = dict(getattr(st, "attributes", {}) or {}) if st else {}
            items[key] = {
                "entity_id": eid,
                "kind": meta.get("kind"),
                "unit": attrs.get("unit_of_measurement"),
                "device_class": attrs.get("device_class"),
                "state_class": attrs.get("state_class"),
            }

        payload: dict[str, Any] = {
            "contract": {"name": "roamcore_openclaw_timeseries_catalog", "version": 1},
            "generated_at": _iso_now(),
            "count": len(items),
            "keys": items,
        }
        return self.json(payload)


class OpenClawTimeSeriesView(HomeAssistantView):
    """Compact, bounded time-series endpoint for agent analysis.

    Query params:
    - keys: comma-separated list of catalog keys (preferred)
    - window_sec: lookback window (default 21600=6h, max 172800=48h)
    - resolution_sec: bucket size (default 60, min 15, max 900)

    Output:
    - numeric series as [[t_epoch, value|null], ...]
    - bool series as event transitions [[t_epoch, 0|1], ...]
    """

    url = "/api/roamcore/openclaw/timeseries"
    name = "api:roamcore_openclaw_timeseries"

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
        if not _openclaw_enabled(self._hass, self._entry_id):
            return web.Response(status=404)

        _mark_openclaw_last_seen(self._hass, self._entry_id, "timeseries")
        hass = self._hass
        q = request.query
        raw_keys = str(q.get("keys") or "").strip()
        keys = [k.strip() for k in raw_keys.split(",") if k.strip()]

        # Defaults + bounds
        try:
            window_sec = int(q.get("window_sec") or 21600)
        except Exception:
            window_sec = 21600
        window_sec = max(900, min(window_sec, 172800))

        try:
            resolution_sec = int(q.get("resolution_sec") or 60)
        except Exception:
            resolution_sec = 60
        resolution_sec = max(15, min(resolution_sec, 900))

        if not keys:
            return self.json(
                {
                    "ok": False,
                    "error": "no_keys",
                    "hint": "Pass ?keys=power.battery_soc_pct,power.load_power_w ... See /api/roamcore/openclaw/timeseries/catalog",
                }
            )

        # Resolve to entity_ids and partition by kind
        resolved: list[tuple[str, str, str]] = []  # (key, eid, kind)
        unknown: list[str] = []
        for k in keys:
            meta = TIMESERIES_CATALOG.get(k)
            if not meta:
                unknown.append(k)
                continue
            resolved.append((k, str(meta.get("entity_id")), str(meta.get("kind"))))

        now = dt_util.utcnow()
        start = now - timedelta(seconds=window_sec)

        entity_ids = [eid for _, eid, _ in resolved]

        def _fetch():
            # significant_only=False: numeric sensors often update monotonically
            return history.get_significant_states(
                hass,
                start,
                now,
                entity_ids,
                include_start_time_state=True,
                significant_changes_only=False,
            )

        hist = await hass.async_add_executor_job(_fetch)

        series: dict[str, Any] = {}
        events: dict[str, Any] = {}

        # Hard cap total points to avoid massive payloads
        max_points = 2000
        bucket_count = int(window_sec // resolution_sec) + 1
        if bucket_count * max(1, len(resolved)) > max_points * 5:
            # if request is too large, force a coarser resolution
            resolution_sec = max(resolution_sec, int(window_sec // max_points) + 1)
            resolution_sec = min(resolution_sec, 900)
            bucket_count = int(window_sec // resolution_sec) + 1

        # Align buckets to resolution
        start_epoch = int(start.timestamp())
        start_epoch = start_epoch - (start_epoch % resolution_sec)

        for key, eid, kind in resolved:
            states = hist.get(eid) or []
            # Convert to (t_epoch, v_str)
            points: list[tuple[int, Optional[str]]] = []
            for st in states:
                try:
                    t = getattr(st, "last_updated", None) or getattr(st, "last_changed", None)
                    if not t:
                        continue
                    te = int(dt_util.as_utc(t).timestamp())
                    raw = st.state
                    v = None if raw in ("unknown", "unavailable", "none", "") else raw
                    points.append((te, v))
                except Exception:
                    continue
            points.sort(key=lambda x: x[0])

            if kind == "bool":
                # Emit only transitions (0/1) within window
                ev: list[list[int | int]] = []
                last: Optional[bool] = None
                for te, v in points:
                    b = _parse_bool(v)
                    if b is None:
                        continue
                    if last is None or b != last:
                        ev.append([te, 1 if b else 0])
                        last = b
                events[key] = ev
                continue

            # Numeric bucket series
            # Fill-forward last known value; emit null if no value seen yet.
            vals: list[list[Any]] = []
            last_num: Optional[float] = None
            idx = 0
            for i in range(bucket_count):
                bt = start_epoch + i * resolution_sec
                # advance through points up to this bucket
                while idx < len(points) and points[idx][0] <= bt:
                    last_num = _parse_num(points[idx][1])
                    idx += 1
                vals.append([bt, last_num])
            series[key] = vals

        payload: dict[str, Any] = {
            "contract": {"name": "roamcore_openclaw_timeseries", "version": 1},
            "generated_at": _iso_now(),
            "window_sec": window_sec,
            "resolution_sec": resolution_sec,
            "unknown_keys": unknown,
            "series": series,
            "events": events,
        }
        return self.json(payload)


class OpenClawAutomationIntentsView(HomeAssistantView):
    """Read-only automation intent schema + validator.

    This endpoint is intentionally non-destructive.
    """

    url = "/api/roamcore/openclaw/automation/intents"
    name = "api:roamcore_openclaw_automation_intents"

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
        if not _openclaw_enabled(self._hass, self._entry_id):
            return web.Response(status=404)

        _mark_openclaw_last_seen(self._hass, self._entry_id, "automation_intents")
        return self.json(
            {
                "contract": INTENT_CONTRACT,
                "generated_at": _iso_now(),
                "supported_intents": SUPPORTED_INTENTS,
                "validate": {
                    "method": "POST",
                    "url": "/api/roamcore/openclaw/automation/validate",
                    "payload_shape": {"type": "<intent_type>", "params": {}},
                },
            }
        )

    async def post(self, request):
        """Validate a JSON payload.

        Accepts either:
        - {"type": ..., "params": ...}
        - {"intent": {"type": ..., "params": ...}}
        """

        if not _openclaw_enabled(self._hass, self._entry_id):
            return web.Response(status=404)

        _mark_openclaw_last_seen(self._hass, self._entry_id, "automation_validate")

        try:
            data = await request.json()
        except Exception:
            return self.json({"ok": False, "error": "invalid_json"})

        intent = data.get("intent") if isinstance(data, dict) else None
        if intent is None:
            intent = data

        res = validate_intent(intent)
        return self.json({"contract": INTENT_CONTRACT, "generated_at": _iso_now(), **res.to_dict()})


class OpenClawAutomationValidateView(OpenClawAutomationIntentsView):
    """Alias endpoint to keep URLs semantically clean."""

    url = "/api/roamcore/openclaw/automation/validate"
    name = "api:roamcore_openclaw_automation_validate"

    async def get(self, request):
        # Redirect-ish hint (we don't want to deal with actual redirects in some clients)
        return self.json(
            {
                "ok": False,
                "error": "use_post",
                "hint": "POST JSON to this endpoint, or GET /api/roamcore/openclaw/automation/intents for schema.",
            }
        )
