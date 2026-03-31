"""RoamCore OpenClaw JSON API.

This integration exposes a small, stable JSON endpoint intended for OpenClaw.

Endpoint (GET): /api/roamcore/openclaw/summary
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .view import RoamCoreOpenClawSummaryView


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration from configuration.yaml."""
    if DOMAIN not in config:
        return True

    hass.http.register_view(RoamCoreOpenClawSummaryView())
    return True

