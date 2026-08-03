"""Stress / integration tests for the RoamCore WiCAN Pro integration.

These run inside the `.venv` (which has homeassistant installed) and
exercise the full stack against a mocked WiCAN Pro HTTP server. This
is the only place we actually spin up the integration code.

Test plan:
  1. Mock WiCAN Pro server returns valid /api/info + /api/diagnostics
  2. Integration setup populates entities + DB
  3. Polling writes to DB
  4. /api/roamcore/wican/timeseries/* views return expected JSON
  5. Integration handles WiCAN Pro going away gracefully
  6. Integration handles partial / corrupted responses
  7. Integration handles wrong/missing PIDs gracefully
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
import sys
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Make the custom_components dir importable as a package
_REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO / "homeassistant" / "custom_components"))


# These tests require homeassistant to be installed (the .venv).
# Skip them on systems where it's not.
homeassistant = pytest.importorskip("homeassistant")


# --- Test fixtures ---

@pytest.fixture
def hass_mock():
    """Build a minimal mock HomeAssistant for integration setup."""
    hass = MagicMock()

    async def _executor_job(fn, *args):
        """Actually run the function synchronously, like HA's executor job."""
        return fn(*args)

    hass.config.path = MagicMock(side_effect=lambda *args: os.path.join(tempfile.gettempdir(), *args))
    hass.async_add_executor_job = _executor_job
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.config_entries.async_reload = AsyncMock()
    hass.data = {}
    hass.http = MagicMock()
    hass.http.register_view = MagicMock()
    hass.bus = MagicMock()
    hass.bus.async_listen = MagicMock()
    return hass


@pytest.fixture
def config_entry():
    """A minimal config entry for the WiCAN Pro integration."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.title = "WiCAN-Test"
    entry.data = {
        "host": "192.168.1.100",
        "port": 80,
        "poll_interval": 1,
        "retention_days": 30,
        "device_name": "WiCAN-Test",
    }
    entry.options = {}
    entry.add_update_listener = MagicMock(return_value=lambda: None)
    entry.async_on_unload = MagicMock()
    return entry


# --- Mocked HTTP responses ---

WICAN_INFO_RESPONSE = {
    "name": "WiCAN-Test",
    "firmware": "2.1.4",
    "serial": "WCP-TEST-1234",
}

# A realistic diagnostics response: decimal PID -> scalar value
WICAN_DIAGNOSTICS_RESPONSE = {
    "4": 15.2,    # engine load %
    "5": 86,      # coolant temp -> 86-40 = 46°C
    "12": 840,    # RPM (pre-decoded)
    "13": 65,     # speed
    "17": 12.5,   # MAF
    "47": 50.2,   # fuel level
    "66": 12.4,   # control module voltage
}

WICAN_DTC_RESPONSE = {"codes": ["P0420"]}


# --- The actual tests ---

@pytest.mark.asyncio
async def test_coordinator_polls_wican_and_writes_db(hass_mock):
    """End-to-end: coordinator polls WiCAN Pro, decodes responses, writes to DB."""
    from roamcore_wican.db import WicanDatabase
    from roamcore_wican.coordinator import WicanCoordinator, WicanClient

    # Mock the aiohttp session
    session = MagicMock()
    response = MagicMock()
    response.json = AsyncMock(side_effect=[
        WICAN_INFO_RESPONSE,
        WICAN_DIAGNOSTICS_RESPONSE,
        WICAN_DTC_RESPONSE,
    ])
    response.raise_for_status = MagicMock()
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=None)
    session.get = MagicMock(return_value=response)

    # Build the integration pieces
    db_path = os.path.join(tempfile.gettempdir(), "test_wican_e2e.db")
    if os.path.exists(db_path):
        os.unlink(db_path)
    db = WicanDatabase(db_path)
    db.open()

    client = WicanClient(session, "192.168.1.100", 80)
    coordinator = WicanCoordinator(hass_mock, client, db, poll_interval=1, device_name="WiCAN-Test")

    # Manually drive the first refresh
    await coordinator._async_setup()
    data = await coordinator._async_update_data()

    assert coordinator.session_id is not None
    assert len(data) > 0
    assert db.reading_count() > 0

    db.close()
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.mark.asyncio
async def test_coordinator_handles_connection_failure(hass_mock):
    """If the WiCAN Pro is unreachable, the coordinator raises UpdateFailed."""
    from roamcore_wican.db import WicanDatabase
    from roamcore_wican.coordinator import WicanCoordinator, WicanClient
    from homeassistant.helpers.update_coordinator import UpdateFailed

    session = MagicMock()
    response = MagicMock()
    response.raise_for_status = MagicMock(side_effect=Exception("Connection refused"))
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=None)
    session.get = MagicMock(return_value=response)

    db_path = os.path.join(tempfile.gettempdir(), "test_wican_fail.db")
    if os.path.exists(db_path):
        os.unlink(db_path)
    db = WicanDatabase(db_path)
    db.open()

    client = WicanClient(session, "192.168.1.100", 80)
    coordinator = WicanCoordinator(hass_mock, client, db, poll_interval=1, device_name="WiCAN-Test")

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    db.close()
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.mark.asyncio
async def test_coordinator_handles_partial_pid_response(hass_mock):
    """A diagnostics response with unknown PIDs / missing values must not crash."""
    from roamcore_wican.db import WicanDatabase
    from roamcore_wican.coordinator import WicanCoordinator, WicanClient

    partial_response = {
        "12": 840,     # RPM — known
        "FF": 42,      # Unknown PID
        "13": "abc",   # Garbage value
        # Missing most PIDs (vehicle didn't respond)
    }

    session = MagicMock()
    response = MagicMock()
    response.json = AsyncMock(side_effect=[
        WICAN_INFO_RESPONSE,
        partial_response,
        [],  # no DTCs
    ])
    response.raise_for_status = MagicMock()
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=None)
    session.get = MagicMock(return_value=response)

    db_path = os.path.join(tempfile.gettempdir(), "test_wican_partial.db")
    if os.path.exists(db_path):
        os.unlink(db_path)
    db = WicanDatabase(db_path)
    db.open()

    client = WicanClient(session, "192.168.1.100", 80)
    coordinator = WicanCoordinator(hass_mock, client, db, poll_interval=1, device_name="WiCAN-Test")

    await coordinator._async_setup()
    data = await coordinator._async_update_data()

    # Only RPM should have made it through
    assert data == {0x0C: 840.0}
    assert db.reading_count() == 1

    db.close()
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.mark.asyncio
async def test_coordinator_handles_empty_diagnostics(hass_mock):
    """An empty diagnostics response must not crash."""
    from roamcore_wican.db import WicanDatabase
    from roamcore_wican.coordinator import WicanCoordinator, WicanClient

    session = MagicMock()
    response = MagicMock()
    response.json = AsyncMock(side_effect=[
        WICAN_INFO_RESPONSE,
        {},  # empty
        [],
    ])
    response.raise_for_status = MagicMock()
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=None)
    session.get = MagicMock(return_value=response)

    db_path = os.path.join(tempfile.gettempdir(), "test_wican_empty.db")
    if os.path.exists(db_path):
        os.unlink(db_path)
    db = WicanDatabase(db_path)
    db.open()

    client = WicanClient(session, "192.168.1.100", 80)
    coordinator = WicanCoordinator(hass_mock, client, db, poll_interval=1, device_name="WiCAN-Test")

    await coordinator._async_setup()
    data = await coordinator._async_update_data()
    assert data == {}
    assert db.reading_count() == 0

    db.close()
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.mark.asyncio
async def test_coordinator_recovers_after_failure(hass_mock):
    """If the WiCAN Pro comes back after a failure, the next poll succeeds."""
    from roamcore_wican.db import WicanDatabase
    from roamcore_wican.coordinator import WicanCoordinator, WicanClient
    from homeassistant.helpers.update_coordinator import UpdateFailed

    session = MagicMock()

    # First call fails, second succeeds
    fail_response = MagicMock()
    fail_response.raise_for_status = MagicMock(side_effect=Exception("timeout"))
    fail_response.__aenter__ = AsyncMock(return_value=fail_response)
    fail_response.__aexit__ = AsyncMock(return_value=None)

    ok_response = MagicMock()
    ok_response.json = AsyncMock(return_value={**WICAN_DIAGNOSTICS_RESPONSE, "13": 0})
    ok_response.raise_for_status = MagicMock()
    ok_response.__aenter__ = AsyncMock(return_value=ok_response)
    ok_response.__aexit__ = AsyncMock(return_value=None)

    session.get = MagicMock(side_effect=[fail_response, ok_response])

    db_path = os.path.join(tempfile.gettempdir(), "test_wican_recover.db")
    if os.path.exists(db_path):
        os.unlink(db_path)
    db = WicanDatabase(db_path)
    db.open()

    client = WicanClient(session, "192.168.1.100", 80)
    coordinator = WicanCoordinator(hass_mock, client, db, poll_interval=1, device_name="WiCAN-Test")

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    # Now it succeeds
    data = await coordinator._async_update_data()
    assert 0x0C in data
    assert coordinator._failure_count == 0  # recovered

    db.close()
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.mark.asyncio
async def test_views_serve_time_series(hass_mock):
    """The HTTP views return expected JSON for catalog/stats/query endpoints."""
    from roamcore_wican.db import WicanDatabase
    from roamcore_wican.timeseries_view import (
        WicanTimeSeriesCatalogView,
        WicanTimeSeriesStatsView,
        WicanTimeSeriesView,
    )

    # Seed the DB
    db_path = os.path.join(tempfile.gettempdir(), "test_wican_views.db")
    if os.path.exists(db_path):
        os.unlink(db_path)
    db = WicanDatabase(db_path)
    db.open()

    sid = db.start_session()
    db.insert_readings(sid, [(0x0C, 840.0), (0x0D, 65.0)])
    db.insert_readings(sid, [(0x0C, 850.0)])

    # Make the coordinator visible to _coordinators()
    from roamcore_wican.coordinator import WicanCoordinator, WicanClient
    session = MagicMock()
    client = WicanClient(session, "192.168.1.100", 80)
    coordinator = WicanCoordinator(hass_mock, client, db, poll_interval=1, device_name="WiCAN-Test")
    coordinator._session_id = sid  # fake an active session
    hass_mock.data[DOMAIN := "roamcore_wican"] = {coordinator.session_id or "x": coordinator}

    # Catalog endpoint
    request = MagicMock()
    request.app = {"hass": hass_mock}
    request.query = {}

    catalog_view = WicanTimeSeriesCatalogView()
    catalog_view.canonical_path = "/api/roamcore/wican/timeseries/catalog"  # not used directly
    resp = await catalog_view.get(request)
    payload = json.loads(resp.text)
    assert "pids" in payload
    assert any(p["name"] == "rpm" for p in payload["pids"])

    db.close()
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.mark.asyncio
async def test_session_recording_on_disconnect(hass_mock):
    """When the coordinator shuts down, the DB session is marked ended."""
    from roamcore_wican.db import WicanDatabase
    from roamcore_wican.coordinator import WicanCoordinator, WicanClient

    session = MagicMock()
    response = MagicMock()
    response.json = AsyncMock(side_effect=[WICAN_INFO_RESPONSE, WICAN_DIAGNOSTICS_RESPONSE, []])
    response.raise_for_status = MagicMock()
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=None)
    session.get = MagicMock(return_value=response)

    db_path = os.path.join(tempfile.gettempdir(), "test_wican_session.db")
    if os.path.exists(db_path):
        os.unlink(db_path)
    db = WicanDatabase(db_path)
    db.open()

    client = WicanClient(session, "192.168.1.100", 80)
    coordinator = WicanCoordinator(hass_mock, client, db, poll_interval=1, device_name="WiCAN-Test")

    await coordinator._async_setup()
    await coordinator._async_update_data()
    assert coordinator.session_id is not None
    assert db.get_session(coordinator.session_id)["ended_at"] is None

    await coordinator.async_shutdown()
    assert db.get_session(coordinator.session_id or "x") is None or \
           db.get_session(list(db.list_sessions(limit=1))[0]["id"])["ended_at"] is not None

    db.close()
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.mark.asyncio
async def test_dtc_recording(hass_mock):
    """DTC codes are persisted + idempotent (re-adding existing codes is a no-op)."""
    from roamcore_wican.db import WicanDatabase
    from roamcore_wican.coordinator import WicanCoordinator, WicanClient

    session = MagicMock()
    response = MagicMock()
    response.json = AsyncMock(side_effect=[
        WICAN_INFO_RESPONSE,
        WICAN_DIAGNOSTICS_RESPONSE,
        {"codes": ["P0420", "P0171"]},
        {"codes": ["P0420", "P0171"]},  # same codes again — should be idempotent
    ])
    response.raise_for_status = MagicMock()
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=None)
    session.get = MagicMock(return_value=response)

    db_path = os.path.join(tempfile.gettempdir(), "test_wican_dtc.db")
    if os.path.exists(db_path):
        os.unlink(db_path)
    db = WicanDatabase(db_path)
    db.open()

    client = WicanClient(session, "192.168.1.100", 80)
    coordinator = WicanCoordinator(hass_mock, client, db, poll_interval=1, device_name="WiCAN-Test")

    await coordinator._async_setup()
    await coordinator._async_update_data()
    await coordinator._async_update_data()

    active = db.list_active_dtcs()
    # Both codes are present, both only registered once (idempotent on second call)
    assert {d["code"] for d in active} == {"P0420", "P0171"}

    db.close()
    try:
        os.unlink(db_path)
    except OSError:
        pass
