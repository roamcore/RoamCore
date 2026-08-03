"""Config flow for the RoamCore WiCAN Pro integration.

Discovery paths (in priority order):
  1. mDNS zeroconf — HA's zeroconf integration picks up `_wican._tcp.local.`
     announcements; this flow presents a confirmation step.
  2. MQTT discovery — if the operator's MQTT broker carries `homeassistant/.../config`
     messages for this device, HA picks those up too.
  3. Manual IP / hostname — the operator types the WiCAN Pro's IP directly.

All three paths converge on the same configuration form: host + port +
poll interval + retention days. The form is pre-filled from the
discovery source where possible.
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DEFAULT_POLL_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_RETENTION_DAYS,
    DOMAIN,
    HTTP_TIMEOUT,
    MAX_POLL_INTERVAL,
    MAX_RETENTION_DAYS,
    MIN_POLL_INTERVAL,
    MIN_RETENTION_DAYS,
    REST_INFO,
)
from .discovery import (
    DiscoveredWican,
    MDNS_SERVICE_TYPE,
    is_valid_wican_host,
    parse_mdns_service_name,
)

_LOGGER = logging.getLogger(__name__)


USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_HOST, default=""): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.All(int, vol.Range(min=1, max=65535)),
        vol.Optional("poll_interval", default=DEFAULT_POLL_INTERVAL): vol.All(
            int, vol.Range(min=MIN_POLL_INTERVAL, max=MAX_POLL_INTERVAL)
        ),
        vol.Optional("retention_days", default=DEFAULT_RETENTION_DAYS): vol.All(
            int, vol.Range(min=MIN_RETENTION_DAYS, max=MAX_RETENTION_DAYS)
        ),
    }
)


async def _async_validate_connection(hass, host: str, port: int) -> dict:
    """Probe the WiCAN Pro's /api/info to validate reachability.

    Returns the parsed JSON info dict on success. Raises on failure.
    """
    session = async_get_clientsession(hass)
    url = f"http://{host}:{port}{REST_INFO}"
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as resp:
        resp.raise_for_status()
        return await resp.json(content_type=None)


class WicanConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the RoamCore WiCAN Pro."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered: DiscoveredWican | None = None
        self._discovered_host: str | None = None
        self._discovered_info: dict | None = None

    # --- mDNS discovery hook ---
    async def async_step_zeroconf(self, discovery_info) -> ConfigFlowResult:
        """Handle mDNS discovery from HA's zeroconf integration."""
        service_name = getattr(discovery_info, "name", "") or ""
        parsed = parse_mdns_service_name(service_name)
        if parsed is None:
            return self.async_abort(reason="not_wican")

        host = getattr(discovery_info, "host", None) or getattr(discovery_info, "ip_address", None)
        port = getattr(discovery_info, "port", DEFAULT_PORT)
        properties = getattr(discovery_info, "properties", {}) or {}

        # Update with the actual discovered host + firmware
        self._discovered = DiscoveredWican(
            name=parsed.name,
            host=host or "",
            port=port,
            firmware_version=properties.get("fw"),
            serial=properties.get("sn"),
            discovery_source="mdns",
        )
        self._discovered_host = host

        # Set unique id by MAC (last-6 of name) so re-discovery doesn't create dupes
        await self.async_set_unique_id(parsed.name)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host, CONF_PORT: port})

        # Don't show the form yet — show a confirmation step
        self.context["title_placeholders"] = {"name": parsed.name}
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(self, user_input=None) -> ConfigFlowResult:
        """Confirm a discovered WiCAN Pro."""
        if user_input is not None:
            assert self._discovered is not None
            data = {
                CONF_HOST: self._discovered.host,
                CONF_PORT: self._discovered.port,
                "poll_interval": DEFAULT_POLL_INTERVAL,
                "retention_days": DEFAULT_RETENTION_DAYS,
                "device_name": self._discovered.name,
                "device_serial": self._discovered.serial,
                "discovery_source": self._discovered.discovery_source,
            }
            return self.async_create_entry(title=self._discovered.name, data=data)

        assert self._discovered is not None
        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={
                "name": self._discovered.name,
                "host": self._discovered.host or "(unknown)",
                "firmware": self._discovered.firmware_version or "unknown",
            },
        )

    # --- User-initiated manual flow ---
    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        """Handle the manual setup (operator types IP)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = (user_input.get(CONF_HOST) or "").strip()
            port = user_input.get(CONF_PORT, DEFAULT_PORT)

            if not host:
                errors["base"] = "no_device"
            elif not is_valid_wican_host(host):
                errors[CONF_HOST] = "invalid_host"
            else:
                try:
                    info = await _async_validate_connection(self.hass, host, port)
                except aiohttp.ClientResponseError as err:
                    _LOGGER.warning("WiCAN Pro HTTP error at %s:%d: %s", host, port, err)
                    errors["base"] = "cannot_connect"
                except (aiohttp.ClientError, TimeoutError) as err:
                    _LOGGER.warning("WiCAN Pro connection failed at %s:%d: %s", host, port, err)
                    errors["base"] = "cannot_connect"
                except Exception as err:  # noqa: BLE001
                    _LOGGER.exception("Unexpected error probing WiCAN Pro")
                    errors["base"] = "cannot_connect"
                else:
                    # Use the device name from /api/info if available, else fall back to host
                    device_name = (
                        info.get("name")
                        or info.get("device_name")
                        or info.get("hostname")
                        or host
                    )
                    # Unique id by serial if available, else by host
                    unique_id = info.get("sn") or info.get("serial") or host
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=str(device_name),
                        data={
                            CONF_HOST: host,
                            CONF_PORT: port,
                            "poll_interval": user_input.get("poll_interval", DEFAULT_POLL_INTERVAL),
                            "retention_days": user_input.get("retention_days", DEFAULT_RETENTION_DAYS),
                            "device_name": str(device_name),
                            "device_serial": info.get("sn") or info.get("serial"),
                            "discovery_source": "manual",
                        },
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=USER_DATA_SCHEMA,
            errors=errors,
        )

    # --- MQTT discovery hook ---
    async def async_step_mqtt(self, discovery_info) -> ConfigFlowResult:
        """Handle MQTT discovery (WiCAN Pro publishing to the operator's broker)."""
        # Discovery payload format:
        #   {"name": "WiCAN-XXXXXX", "host": "192.168.1.x", "port": 80,
        #    "serial": "...", "firmware": "..."}
        payload = discovery_info
        device_name = payload.get("name", "WiCAN")
        host = payload.get("host")
        port = payload.get("port", DEFAULT_PORT)
        if not host or not is_valid_wican_host(host):
            return self.async_abort(reason="not_wican")

        unique_id = payload.get("serial") or device_name
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host, CONF_PORT: port})

        self._discovered = DiscoveredWican(
            name=device_name,
            host=host,
            port=port,
            firmware_version=payload.get("firmware"),
            serial=payload.get("serial"),
            discovery_source="mqtt",
        )
        self.context["title_placeholders"] = {"name": device_name}
        return await self.async_step_discovery_confirm()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return WicanOptionsFlow(config_entry)


class WicanOptionsFlow(OptionsFlow):
    """Options flow — change poll interval + retention days after setup."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "poll_interval",
                        default=self.config_entry.options.get(
                            "poll_interval",
                            self.config_entry.data.get("poll_interval", DEFAULT_POLL_INTERVAL),
                        ),
                    ): vol.All(int, vol.Range(min=MIN_POLL_INTERVAL, max=MAX_POLL_INTERVAL)),
                    vol.Optional(
                        "retention_days",
                        default=self.config_entry.options.get(
                            "retention_days",
                            self.config_entry.data.get("retention_days", DEFAULT_RETENTION_DAYS),
                        ),
                    ): vol.All(int, vol.Range(min=MIN_RETENTION_DAYS, max=MAX_RETENTION_DAYS)),
                }
            ),
        )
