from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    CONF_CONTRACT_VERSION,
    DEFAULT_CONTRACT_VERSION,
    CONF_OPENCLAW_API_ENABLED,
    DEFAULT_OPENCLAW_API_ENABLED,
)
from .openclaw_view import OpenClawSummaryView, OpenClawSkillView


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up RoamCore from YAML (deprecated; prefer config entry)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up RoamCore from a config entry."""

    # Ensure options defaults exist
    options = dict(entry.options)
    if CONF_CONTRACT_VERSION not in options:
        options[CONF_CONTRACT_VERSION] = DEFAULT_CONTRACT_VERSION
    if CONF_OPENCLAW_API_ENABLED not in options:
        options[CONF_OPENCLAW_API_ENABLED] = DEFAULT_OPENCLAW_API_ENABLED

    if options != dict(entry.options):
        hass.config_entries.async_update_entry(entry, options=options)

    # Register HTTP endpoints (OpenClaw summary)
    if options.get(CONF_OPENCLAW_API_ENABLED, DEFAULT_OPENCLAW_API_ENABLED):
        hass.http.register_view(OpenClawSummaryView(hass, entry.entry_id))
        hass.http.register_view(OpenClawSkillView(hass, entry.entry_id))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Home Assistant does not currently provide a stable public API to unregister
    # HTTP views. We leave the view registered for the life of the process.
    return True
