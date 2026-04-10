"""RoamCore OpenClaw JSON API.

This integration exposes a small, stable JSON endpoint intended for OpenClaw.

Endpoint (GET): /api/roamcore/openclaw/summary
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .view import RoamCoreOpenClawSummaryView, RoamCoreOpenClawSkillView


def _is_on(hass: HomeAssistant, entity_id: str) -> bool:
    try:
        st = hass.states.get(entity_id)
        return st is not None and st.state == "on"
    except Exception:
        return False


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration from configuration.yaml."""
    if DOMAIN not in config:
        return True

    # Views are always registered, but can be gated via input_booleans.
    # This makes it possible to toggle enable/auth without restarts.
    hass.http.register_view(RoamCoreOpenClawSummaryView(hass))
    hass.http.register_view(RoamCoreOpenClawSkillView(hass))

    async def _svc_options_set(call):
        data = call.data or {}
        enabled = data.get("enabled", None)
        requires_auth = data.get("requires_auth", None)

        # We store state in helpers so it persists + is user-visible.
        if enabled is not None:
            await hass.services.async_call(
                "input_boolean",
                "turn_on" if bool(enabled) else "turn_off",
                {"entity_id": "input_boolean.rc_openclaw_api_enabled"},
                blocking=True,
            )
        if requires_auth is not None:
            await hass.services.async_call(
                "input_boolean",
                "turn_on" if bool(requires_auth) else "turn_off",
                {"entity_id": "input_boolean.rc_openclaw_api_requires_auth"},
                blocking=True,
            )

    hass.services.async_register(
        DOMAIN,
        "options_set",
        _svc_options_set,
        schema=None,
    )
    return True
