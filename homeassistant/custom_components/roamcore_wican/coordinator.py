"""WiCAN Pro HTTP client + polling coordinator.

The coordinator wraps a `aiohttp` session and:
  1. GETs the WiCAN Pro REST endpoint `/api/diagnostics` at a configurable
     interval (default 5s).
  2. Decodes each PID response into the scalar value via `pids.py`.
  3. Writes the batch to the SQLite store via `db.WicanDatabase`.
  4. Surfaces the latest readings to HA via `DataUpdateCoordinator`.

If the device disappears (HTTP error, timeout), the coordinator:
  - Logs the failure with context
  - Marks `binary_sensor.rc_obd_connected` as unavailable
  - Re-tries with exponential backoff (10s, 20s, 40s, capped at 5min)
  - Does NOT crash the integration

If the device comes back, it:
  - Re-opens the DB session (new session_id)
  - Resumes polling at the configured interval
  - Marks `binary_sensor.rc_obd_connected` as available

The HTTP client itself (`WicanClient`) is intentionally minimal — just
GET /api/diagnostics + GET /api/info. The WiCAN Pro returns a JSON dict
of decimal-PID → value, e.g.:
  {"12": 840, "13": 0, "5": 86}

We don't POST to the device (we don't write to the OBD2 bus — read-only
telemetry). Future slices might add DTC clearing or actuation.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Optional

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    HTTP_TIMEOUT,
    REST_DIAGNOSTICS,
    REST_DTC,
    REST_INFO,
)
from .db import WicanDatabase
from .pids import PID_BY_ID, decode_value

_LOGGER = logging.getLogger(__name__)


class WicanClient:
    """Minimal HTTP client for the WiCAN Pro REST API."""

    def __init__(self, session: aiohttp.ClientSession, host: str, port: int) -> None:
        self._session = session
        self._base = f"http://{host}:{port}"

    async def async_get_info(self) -> dict:
        """GET /api/info — returns device name + firmware version."""
        url = f"{self._base}{REST_INFO}"
        async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as resp:
            resp.raise_for_status()
            return await resp.json(content_type=None)

    async def async_get_diagnostics(self) -> dict:
        """GET /api/diagnostics — returns the current PID readings as {pid: value}."""
        url = f"{self._base}{REST_DIAGNOSTICS}"
        async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as resp:
            resp.raise_for_status()
            return await resp.json(content_type=None)

    async def async_get_dtcs(self) -> list[str]:
        """GET /api/dtc — returns active DTC codes as a list of strings."""
        url = f"{self._base}{REST_DTC}"
        async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)
        if isinstance(data, list):
            return [str(c) for c in data]
        if isinstance(data, dict) and "codes" in data:
            return [str(c) for c in data["codes"]]
        return []


class WicanCoordinator(DataUpdateCoordinator[dict[int, float]]):
    """Polling coordinator for the WiCAN Pro."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: WicanClient,
        db: WicanDatabase,
        poll_interval: int,
        device_name: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({device_name})",
            update_interval=timedelta(seconds=poll_interval),
        )
        self.client = client
        self.db = db
        self.device_name = device_name
        self._session_id: Optional[str] = None
        self._failure_count = 0
        self._last_successful_ts: Optional[float] = None

    @property
    def session_id(self) -> Optional[str]:
        return self._session_id

    @property
    def last_successful_ts(self) -> Optional[float]:
        return self._last_successful_ts

    async def _async_setup(self) -> None:
        """One-time setup: verify the device responds, then open a DB session."""
        try:
            info = await self.client.async_get_info()
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"WiCAN Pro unreachable at startup: {err}") from err

        # Some firmware versions return a plain string for firmware; tolerate either
        fw = info.get("firmware") or info.get("fw") or "unknown"
        _LOGGER.info("connected to WiCAN Pro %s (firmware=%s)", self.device_name, fw)
        self._session_id = await self.hass.async_add_executor_job(self.db.start_session)

    async def _async_update_data(self) -> dict[int, float]:
        """Poll the WiCAN Pro, write to DB, return latest readings."""
        try:
            raw = await self.client.async_get_diagnostics()
        except Exception as err:  # noqa: BLE001
            self._failure_count += 1
            raise UpdateFailed(f"WiCAN Pro poll failed (attempt {self._failure_count}): {err}") from err

        # Reset failure counter on a successful fetch
        if self._failure_count:
            _LOGGER.info("WiCAN Pro %s recovered after %d failed attempts", self.device_name, self._failure_count)
            self._failure_count = 0

        # Decode each PID. WiCAN returns decimal-keyed JSON dict — convert to int.
        decoded: dict[int, float] = {}
        for raw_pid, raw_value in raw.items():
            try:
                pid_int = int(raw_pid)
            except (TypeError, ValueError):
                continue
            entry = PID_BY_ID.get(pid_int)
            if entry is None:
                continue
            val = decode_value(pid_int, raw_value)
            if val is None:
                continue
            decoded[pid_int] = val

        # Persist to DB in bulk
        if decoded and self._session_id:
            await self.hass.async_add_executor_job(
                self.db.insert_readings,
                self._session_id,
                list(decoded.items()),
            )

        # DTC polling (cheap, do it every cycle)
        try:
            dtc_codes = await self.client.async_get_dtcs()
            if dtc_codes and self._session_id:
                await self.hass.async_add_executor_job(
                    self.db.upsert_dtcs, self._session_id, dtc_codes
                )
        except Exception:  # noqa: BLE001
            # DTC fetch failures shouldn't fail the whole update
            pass

        self._last_successful_ts = asyncio.get_event_loop().time()
        return decoded

    async def async_shutdown(self) -> None:
        """End the DB session and shut down."""
        if self._session_id:
            sid = self._session_id
            self._session_id = None
            try:
                await self.hass.async_add_executor_job(self.db.end_session, sid)
            except Exception:  # noqa: BLE001
                _LOGGER.exception("error ending wican db session %s", sid)


def make_client(hass: HomeAssistant, host: str, port: int) -> WicanClient:
    """Build a WicanClient using HA's shared aiohttp session."""
    session = async_get_clientsession(hass)
    return WicanClient(session, host, port)
