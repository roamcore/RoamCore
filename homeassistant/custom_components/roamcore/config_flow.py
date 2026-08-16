from __future__ import annotations

import logging
from typing import Any, Dict

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    CONF_OPENCLAW_API_ENABLED,
    CONF_OPENCLAW_API_REQUIRES_AUTH,
    CONF_TRACCAR_USER_TOKEN,
    CONF_IOVERLANDER_API_KEY,
    CONF_AUTO_PROVISION_ASSETS,
    DEFAULT_AUTO_PROVISION_ASSETS,
    CONF_PROVISION_REF,
    DEFAULT_PROVISION_REF,
    DEFAULT_OPENCLAW_API_ENABLED,
    DEFAULT_OPENCLAW_API_REQUIRES_AUTH,
)

_LOGGER = logging.getLogger(__name__)

# Wave 9 #108 — Starlink 3-path wizard constants.
# Imported lazily inside the Starlink step so the module can be
# imported without the connections/starlink package being installed
# (the wizard is gated on the connection folder being present).
CONF_STARLINK_PATH = "starlink_path"
CONF_STARLINK_PLUG_ENTITY_ID = "smart_plug_entity_id"
CONF_STARLINK_OPENWRT_API_URL = "openwrt_api_url"
CONF_STARLINK_OPENWRT_API_TOKEN = "openwrt_api_token"


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

    # ------------------------------------------------------------------
    # Wave 9 #108 — Starlink 3-path wizard step.
    #
    # The wizard shows 3 radio buttons (one per setup path); the user
    # picks one; we render a path-specific follow-up form (Path A
    # needs no input; Path B needs the smart plug entity id; Path C
    # needs the OpenWrt API URL + token). On submit we call
    # connections.starlink.apply_setup_path() which verifies the
    # target is reachable (3x retries with backoff) and writes the
    # right helpers + REST sensors + template sensors.
    #
    # Re-running the step is safe (apply_setup_path is idempotent).
    # ------------------------------------------------------------------
    async def async_step_starlink(self, user_input=None):
        """Wave 9 #108 — Starlink 3-path wizard step.

        Step 1: show the 3 setup_paths as radio buttons. User picks
                one. We render the path-specific follow-up form.
        Step 2: collect path-specific input + call apply_setup_path.
                We surface plain-English errors as the form's `errors`
                dict (no exceptions bubble up to the HA UI).
        """
        # Lazy import the starlink wiring module — only loaded when
        # the user actually invokes the Starlink wizard step.
        try:
            import sys
            import os
            # The connections/starlink folder is a sibling of the
            # RoamCore custom_component. We add it to sys.path so
            # `import starlink` (which is the package the wizard
            # uses) works in both dev and HA Container contexts.
            _starlink_pkg = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                "connections",
                "starlink",
            )
            if os.path.isdir(_starlink_pkg) and _starlink_pkg not in sys.path:
                sys.path.insert(0, _starlink_pkg)
            import starlink  # noqa: WPS433 - lazy import by design
        except (ImportError, OSError) as err:
            _LOGGER.warning(
                "Starlink wizard: cannot import connections/starlink (%s). "
                "Is the connections/ folder present in the repo?",
                err,
            )
            return self.async_abort(
                reason="starlink_connection_unavailable",
                description_placeholders={
                    "error": (
                        "RoamCore can't find the Starlink connection "
                        "(connections/starlink/). Make sure the RoamCore "
                        "repo is checked out alongside the custom_component."
                    ),
                },
            )

        paths = starlink.describe_setup_paths()

        if user_input is None:
            # Step 1: render the radio-button form.
            return self.async_show_form(
                step_id="starlink",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_STARLINK_PATH): vol.In(
                            [p["id"] for p in paths]
                        ),
                    }
                ),
                description_placeholders={
                    "options": "\n".join(
                        f"- **{p['label']}** ({p['estimated_time']}): "
                        f"{p['description']}"
                        for p in paths
                    ),
                },
            )

        # Step 2: path-specific follow-up form. The first submission
        # only carries CONF_STARLINK_PATH; we re-render with the
        # path-specific fields + a marker that CONF_STARLINK_PATH was
        # already chosen. We use a sentinel so the user can navigate
        # back without re-picking the path.
        chosen_path = user_input.get(CONF_STARLINK_PATH)
        if not chosen_path or chosen_path not in starlink.VALID_PATHS:
            return self.async_show_form(
                step_id="starlink",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_STARLINK_PATH): vol.In(
                            [p["id"] for p in paths]
                        ),
                    }
                ),
                errors={"base": "invalid_path"},
                description_placeholders={
                    "options": "\n".join(
                        f"- **{p['label']}** ({p['estimated_time']}): "
                        f"{p['description']}"
                        for p in paths
                    ),
                },
            )

        # If the user hasn't supplied the path-specific inputs yet,
        # show the follow-up form.
        if chosen_path == starlink.PATH_STARLINK_MINI_ONLY:
            # Path A needs no inputs — submit immediately.
            return await self._apply_starlink_path(starlink, chosen_path, {})
        if chosen_path == starlink.PATH_SEPARATE_ROUTER:
            if CONF_STARLINK_PLUG_ENTITY_ID not in user_input:
                return self.async_show_form(
                    step_id="starlink",
                    data_schema=vol.Schema(
                        {
                            vol.Required(CONF_STARLINK_PATH, default=chosen_path): str,
                            vol.Required(CONF_STARLINK_PLUG_ENTITY_ID): str,
                        }
                    ),
                    description_placeholders={
                        "options": "Path B (separate router) — enter the "
                        "HA switch.* entity ID of your smart plug "
                        "(e.g. switch.kasa_plug).",
                    },
                )
            return await self._apply_starlink_path(
                starlink,
                chosen_path,
                {
                    CONF_STARLINK_PLUG_ENTITY_ID: user_input[
                        CONF_STARLINK_PLUG_ENTITY_ID
                    ],
                },
            )
        # PATH_VP2430_VM_ROUTER
        if (
            CONF_STARLINK_OPENWRT_API_URL not in user_input
            or CONF_STARLINK_OPENWRT_API_TOKEN not in user_input
        ):
            return self.async_show_form(
                step_id="starlink",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_STARLINK_PATH, default=chosen_path): str,
                        vol.Required(CONF_STARLINK_OPENWRT_API_URL): str,
                        vol.Required(CONF_STARLINK_OPENWRT_API_TOKEN): str,
                    }
                ),
                description_placeholders={
                    "options": (
                        "Path C (VM router inside the VP2430) — enter the "
                        "OpenWrt API URL (e.g. http://192.168.1.250/cgi-bin/luci) "
                        "and bearer token from the OpenWrt VM. See "
                        "connections/openwrt-controls for how to generate the token."
                    ),
                },
            )
        return await self._apply_starlink_path(
            starlink,
            chosen_path,
            {
                CONF_STARLINK_OPENWRT_API_URL: user_input[
                    CONF_STARLINK_OPENWRT_API_URL
                ],
                CONF_STARLINK_OPENWRT_API_TOKEN: user_input[
                    CONF_STARLINK_OPENWRT_API_TOKEN
                ],
            },
        )

    async def _apply_starlink_path(
        self,
        starlink_module: Any,
        path_id: str,
        user_input: Dict[str, Any],
    ) -> Any:
        """Apply the chosen Starlink setup path.

        Translates the wizard's path-id + user_input into the
        kwargs starlink.apply_setup_path expects, calls it, and
        either aborts with the plain-English error (if the apply
        failed) or creates an entry recording the choice.
        """
        # Map wizard kwargs to starlink-module kwargs.
        kwargs: Dict[str, Any] = {}
        if path_id == starlink_module.PATH_SEPARATE_ROUTER:
            kwargs["smart_plug_entity_id"] = user_input[
                CONF_STARLINK_PLUG_ENTITY_ID
            ]
        elif path_id == starlink_module.PATH_VP2430_VM_ROUTER:
            kwargs["openwrt_api_url"] = user_input[
                CONF_STARLINK_OPENWRT_API_URL
            ]
            kwargs["openwrt_api_token"] = user_input[
                CONF_STARLINK_OPENWRT_API_TOKEN
            ]
        # Path A has no extra inputs.

        try:
            result = await starlink_module.apply_setup_path(
                self.hass,
                path_id,
                kwargs,
            )
        except Exception as err:  # noqa: BLE001 - we surface ALL errors
            # apply_setup_path raises HomeAssistantError with
            # plain-English messages. We surface them as form errors
            # (never as exceptions to the HA UI).
            _LOGGER.warning("Starlink wizard apply_setup_path failed: %s", err)
            return self.async_show_form(
                step_id="starlink",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_STARLINK_PATH, default=path_id): str,
                    }
                ),
                errors={"base": "starlink_apply_failed"},
                description_placeholders={
                    "options": (
                        f"The wizard couldn't apply Path "
                        f"{path_id!r}: {err}. Please check the "
                        f"connection and re-run the wizard."
                    ),
                },
            )

        # Success — record the choice in the config entry options.
        # We don't create a NEW config entry; the RoamCore config
        # entry already exists. We attach the wizard's choice to
        # its options so downstream code (the in-package YAML +
        # the connections/starlink/__init__.py helpers) can read it
        # on the next reload.
        return self.async_create_entry(
            title=f"Starlink: {path_id}",
            data={},
            options={
                "starlink_path": result["path_id"],
                "starlink_entities_created": result["entities_created"],
                "starlink_verified_within_s": result.get(
                    "verified_within_s"
                ),
                "starlink_warnings": result.get("warnings", []),
            },
        )


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

                        # Optional integrations / API keys
                        # NOTE: stored in the config entry options, not in YAML.
                        # Prefer this over putting secrets in Lovelace helpers.
                        vol.Optional(
                            CONF_TRACCAR_USER_TOKEN,
                            default=opts.get(CONF_TRACCAR_USER_TOKEN, ""),
                        ): str,
                        vol.Optional(
                            CONF_IOVERLANDER_API_KEY,
                            default=opts.get(CONF_IOVERLANDER_API_KEY, ""),
                        ): str,

                        # HACS-first provisioning
                        vol.Optional(
                            CONF_AUTO_PROVISION_ASSETS,
                            default=opts.get(CONF_AUTO_PROVISION_ASSETS, DEFAULT_AUTO_PROVISION_ASSETS),
                        ): bool,
                        vol.Optional(
                            CONF_PROVISION_REF,
                            default=opts.get(CONF_PROVISION_REF, DEFAULT_PROVISION_REF),
                        ): str,
                    }
                ),
            )

        return self.async_create_entry(title="", data=user_input)
