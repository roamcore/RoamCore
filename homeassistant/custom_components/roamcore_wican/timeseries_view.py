"""HTTP view exposing the WiCAN Pro PID time-series as JSON.

Mounted at `/api/roamcore/wican/timeseries` via HA's HTTP component.
This is the read-only endpoint ML tools (or OpenClaw) can hit to query
historical PID data without needing direct SQLite access.

Endpoints:
  GET /api/roamcore/wican/timeseries/catalog
    -> {"pids": [{"pid": 12, "name": "rpm", "label": "Engine RPM", "unit": "rpm",
                   "reading_count": 1234, "latest_ts": 1234567890}, ...]}

  GET /api/roamcore/wican/timeseries?pid=12&from=1234560000&to=1234570000&limit=1000
    -> {"pid": 12, "name": "rpm", "unit": "rpm",
        "points": [{"ts": 1234567890, "value": 840.0}, ...]}

  GET /api/roamcore/wican/timeseries/stats
    -> {"total_readings": 12345, "session_count": 4, "active_dtcs": 0,
        "disk_bytes": 1234567, "retention_days": 90}

No write endpoints. No auth (assume local LAN; HA's `http` component is
the security boundary). The data is intentionally vendor-neutral (PID
identifiers are the SAE standard hex IDs, not WiCAN-internal ones).
"""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import web
from homeassistant.core import HomeAssistant
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers import config_entry_oauth2_flow

from .const import DOMAIN
from .coordinator import WicanCoordinator
from .db import WicanDatabase
from .pids import PID_BY_ID

_LOGGER = logging.getLogger(__name__)

BASE_URL = "/api/roamcore/wican/timeseries"


def _coordinators(hass: HomeAssistant) -> dict[str, tuple[WicanCoordinator, WicanDatabase]]:
    """Return {device_name: (coordinator, db)} for every active entry."""
    out: dict[str, tuple[WicanCoordinator, WicanDatabase]] = {}
    for entry_id, coordinator in hass.data.get(DOMAIN, {}).items():
        if isinstance(coordinator, WicanCoordinator):
            out[coordinator.device_name] = (coordinator, coordinator.db)
    return out


def _bad_request(message: str) -> web.Response:
    return web.json_response({"error": message}, status=400)


def _not_found(message: str) -> web.Response:
    return web.json_response({"error": message}, status=404)


class WicanTimeSeriesCatalogView(HomeAssistantView):
    """GET /api/roamcore/wican/timeseries/catalog."""

    name = "api:roamcore_wican:timeseries:catalog"
    url = f"{BASE_URL}/catalog"

    async def get(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        out: list[dict[str, Any]] = []
        for device_name, (coordinator, db) in _coordinators(hass).items():
            for pid, entry in PID_BY_ID.items():
                count = db.reading_count(pid)
                latest = db.latest_reading(pid)
                out.append(
                    {
                        "device_name": device_name,
                        "pid": pid,
                        "pid_hex": f"0x{pid:02X}",
                        "name": entry.name,
                        "label": entry.label,
                        "unit": entry.unit,
                        "reading_count": count,
                        "latest_ts": latest["ts"] if latest else None,
                        "latest_value": latest["value"] if latest else None,
                    }
                )
        return web.json_response({"pids": out})


class WicanTimeSeriesView(HomeAssistantView):
    """GET /api/roamcore/wican/timeseries — query readings."""

    name = "api:roamcore_wican:timeseries"
    url = BASE_URL

    async def get(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]

        # Parse query params
        try:
            pid = int(request.query.get("pid", ""))
        except (TypeError, ValueError):
            return _bad_request("missing or invalid 'pid' query param (integer OBD2 PID in decimal)")

        device_name = request.query.get("device")
        ts_from = request.query.get("from")
        ts_to = request.query.get("to")
        limit = int(request.query.get("limit", "1000"))

        if pid not in PID_BY_ID:
            return _bad_request(f"PID {pid} (0x{pid:02X}) not in supported PID table")

        ts_from_int = int(ts_from) if ts_from else None
        ts_to_int = int(ts_to) if ts_to else None

        coordinators = _coordinators(hass)
        if not coordinators:
            return _not_found("no WiCAN Pro is configured")

        # If a specific device is requested, filter
        if device_name:
            if device_name not in coordinators:
                return _not_found(f"device '{device_name}' not found")
            _, db = coordinators[device_name]
        else:
            # If only one device, default to it; otherwise require device=
            if len(coordinators) == 1:
                _, db = next(iter(coordinators.values()))
            else:
                return _bad_request("multiple devices configured; specify ?device=<name>")

        rows = db.query_readings(pid, ts_from_int, ts_to_int, limit)
        entry = PID_BY_ID[pid]
        return web.json_response(
            {
                "pid": pid,
                "pid_hex": f"0x{pid:02X}",
                "name": entry.name,
                "label": entry.label,
                "unit": entry.unit,
                "count": len(rows),
                "points": [{"ts": r["ts"], "value": r["value"]} for r in rows],
            }
        )


class WicanTimeSeriesStatsView(HomeAssistantView):
    """GET /api/roamcore/wican/timeseries/stats."""

    name = "api:roamcore_wican:timeseries:stats"
    url = f"{BASE_URL}/stats"

    async def get(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        coordinators = _coordinators(hass)
        if not coordinators:
            return _not_found("no WiCAN Pro is configured")

        result = {}
        for device_name, (_, db) in coordinators.items():
            result[device_name] = db.stats()
        return web.json_response({"devices": result})


def async_register_views(hass: HomeAssistant) -> None:
    """Register the timeseries HTTP views on HA's HTTP component."""
    hass.http.register_view(WicanTimeSeriesCatalogView())
    hass.http.register_view(WicanTimeSeriesView())
    hass.http.register_view(WicanTimeSeriesStatsView())
    _LOGGER.info("registered %s views", BASE_URL)
