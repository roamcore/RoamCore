"""Teltonika (LTE/5G router for vans) — tier-b recipe connection.

This module is a marker-only stub. Tier-b connections don't ship native
HA integration code; they publish a recipe (docs/recipe.md) that walks
the user through setting up a Teltonika RUT-series LTE/5G router on
the van's LAN, enabling SNMP (System → SNMP → Enable) or the REST /
RMS API on the router's firmware, exposing the resulting data via
HA's core `snmp` integration (or `rest` / `command_line` for the
REST/RMS path), and publishing the RoamCore mobile-internet contract
tiles on top (`rc_net_teltonika_*` tiles + a one-tap reboot button +
a monthly-data-reset switch).

The audit + boundary CI can detect a `teltonika/` folder that claims
to be a connection via the `DOMAIN` constant exported here. The
wizard reads the manifest + recipe at runtime.

The real telemetry + reboot path is:

    Operator-side Teltonika RUT router
        -> enable SNMP (Path A, recommended on every firmware) OR
           REST/RMS API (Path B, newer firmware)
        -> HA core `snmp` integration (Path A) OR
           HA `rest` / `command_line` integration (Path B)
        -> HA sensors (SNMP / REST sensor entities)
        -> RoamCore contract layer
           (rc_net_teltonika_reachable,
            rc_net_teltonika_wan_state,
            rc_net_teltonika_signal_pct,
            rc_net_teltonika_lte_mode,
            rc_net_teltonika_carrier,
            rc_net_teltonika_data_used_gb,
            rc_net_teltonika_uptime_hours,
            rc_net_teltonika_public_ip,
            rc_net_teltonika_data_reset,
            rc_net_teltonika_reboot_now,
            rc_net_teltonika_refresh_signals)
        -> dashboard tiles + OpenClaw queries
            ("is teltonika online?", "what's the signal?",
             "how much data this month?", "reboot teltonika")

    Reboot affordance (operator's choice):
        -> controllable smart plug behind the router (Path A's
           optional plug affordance, same pattern as Starlink's
           `switch.rc_net_starlink_plug`), OR
        -> Teltonika REST/RMS `reboot` API endpoint wired into a
           `button` helper + the recipe §5 automation
        -> contract tile: button.rc_net_teltonika_reboot_now

See docs/recipe.md for the full howto (SNMP wiring, REST/RMS wiring,
HA helpers, optional smart-plug or REST-reboot wiring, mode-aware
automations, troubleshooting, tier-a promotion outline).
"""

DOMAIN = "teltonika"