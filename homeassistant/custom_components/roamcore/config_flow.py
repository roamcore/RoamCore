from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    CONF_OPENCLAW_API_ENABLED,
    CONF_OPENCLAW_API_REQUIRES_AUTH,
    DEFAULT_OPENCLAW_API_ENABLED,
    DEFAULT_OPENCLAW_API_REQUIRES_AUTH,
)


class RoamCoreConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        # Single instance (for beta)
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            CONF_OPENCLAW_API_ENABLED,
                            default=DEFAULT_OPENCLAW_API_ENABLED,
                        ): bool,
                        vol.Optional(
                            CONF_OPENCLAW_API_REQUIRES_AUTH,
                            default=DEFAULT_OPENCLAW_API_REQUIRES_AUTH,
                        ): bool,
                    }
                ),
            )

        return self.async_create_entry(title="RoamCore", data={}, options=user_input)


async def async_get_options_flow(config_entry):
    return RoamCoreOptionsFlowHandler(config_entry)


class RoamCoreOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is None:
            opts = self.config_entry.options
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            CONF_OPENCLAW_API_ENABLED,
                            default=opts.get(CONF_OPENCLAW_API_ENABLED, DEFAULT_OPENCLAW_API_ENABLED),
                        ): bool,
                        vol.Optional(
                            CONF_OPENCLAW_API_REQUIRES_AUTH,
                            default=opts.get(
                                CONF_OPENCLAW_API_REQUIRES_AUTH,
                                DEFAULT_OPENCLAW_API_REQUIRES_AUTH,
                            ),
                        ): bool,
                    }
                ),
            )

        return self.async_create_entry(title="", data=user_input)

