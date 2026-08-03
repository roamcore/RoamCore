"""RoamCore WiCAN Pro integration — main entry point.

Lifecycle:
  1. async_setup_entry: open the DB, build the HTTP client + coordinator,
     set up the sensor + binary_sensor platforms, register the timeseries
     HTTP views, schedule the background prune loop.
  2. async_unload_entry: tear down the coordinator, close the DB, deregister
     platforms + views.
"""

from __future__ import annotations

import logging
import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import WicanCoordinator, make_client
from .db import WicanDatabase, async_prune_loop
from .timeseries_view import async_register_views

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

# Track registered views per HA instance — re-registering on reload would
# raise from hass.http.register_view (it doesn't allow duplicates).
_views_registered = False


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the RoamCore WiCAN Pro integration from a config entry."""
    global _views_registered

    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    poll_interval = entry.options.get("poll_interval", entry.data.get("poll_interval", 5))
    retention_days = entry.options.get("retention_days", entry.data.get("retention_days", 90))

    # 1. Open the SQLite store at HA's config dir
    db_path = hass.config.path(".storage", "roamcore_wican.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    db = WicanDatabase(db_path, retention_days=retention_days)
    await hass.async_add_executor_job(db.open)

    # 2. Build the HTTP client + coordinator
    client = make_client(hass, host, port)
    coordinator = WicanCoordinator(
        hass,
        client,
        db,
        poll_interval=poll_interval,
        device_name=entry.data.get("device_name") or entry.title,
    )

    # 3. First refresh — verifies reachability + opens a DB session
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:  # noqa: BLE001
        await hass.async_add_executor_job(db.close)
        raise ConfigEntryNotReady(f"WiCAN Pro unreachable: {err}") from err

    # 4. Stash for the sensor platform
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # 5. Forward to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # 6. Register HTTP views (once per HA instance)
    if not _views_registered:
        async_register_views(hass)
        _views_registered = True

    # 7. Schedule the prune loop
    entry.async_on_unload(
        hass.async_create_background_task(
            async_prune_loop(db, interval_hours=24),
            name=f"{DOMAIN}_prune",
        )
    )

    # 8. Listen for options updates
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    _LOGGER.info(
        "WiCAN Pro integration set up: device=%s host=%s:%d poll=%ds retention=%dd",
        entry.title,
        host,
        port,
        poll_interval,
        retention_days,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: WicanCoordinator = hass.data[DOMAIN].get(entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and coordinator is not None:
        await coordinator.async_shutdown()
        await hass.async_add_executor_job(coordinator.db.close)
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
