"""Peplink (multi-WAN router for van internet) — tier-b recipe connection.

This module is a marker-only stub. Tier-b connections don't ship native
HA integration code; they publish a recipe (docs/recipe.md) that walks
the user through setting up a Peplink Balance / MAX / EP-series
multi-WAN router on the van's LAN, enabling SNMP (System → SNMP →
Enable) for Path A or installing the HACS `hass-incontrol2`
community integration + InControl 2 API key for Path B, exposing
the resulting data via HA's core `snmp` integration (Path A) or the
HACS `hass-incontrol2` integration (Path B), and publishing the
RoamCore multi-WAN contract tiles on top (`rc_net_peplink_*` tiles
+ a one-tap refresh button + a one-tap force-failover button + a
WAN-priority `select`).

The audit + boundary CI can detect a `peplink/` folder that claims
to be a connection via the `DOMAIN` constant exported here. The
wizard reads the manifest + recipe at runtime.

The real telemetry + force-failover path is:

    Operator-side Peplink Balance / MAX / EP router
        -> enable SNMP (Path A, recommended for single-router
           operators on any SNMP-enabled Peplink firmware) OR
           install the HACS `hass-incontrol2` integration +
           InControl 2 API key (Path B, recommended for fleet
           operators managing >1 Peplink device)
        -> HA core `snmp` integration (Path A) OR
           HA HACS `hass-incontrol2` integration (Path B)
        -> HA sensors (SNMP / InControl 2 entities)
        -> RoamCore contract layer
           (binary_sensor.rc_net_peplink_reachable,
            sensor.rc_net_peplink_wan1_state,
            sensor.rc_net_peplink_wan2_state,
            sensor.rc_net_peplink_active_wan,
            sensor.rc_net_peplink_wan_failover_count_24h,
            sensor.rc_net_peplink_wan_health_score,
            sensor.rc_net_peplink_uptime_hours,
            sensor.rc_net_peplink_public_ip,
            button.rc_net_peplink_refresh_now,
            button.rc_net_peplink_force_failover,
            select.rc_net_peplink_wan_priority)
        -> dashboard tiles + OpenClaw queries
            ("is peplink online?", "what's peplink's active WAN?",
             "how many peplink failovers in the last 24h?",
             "what's peplink's load-balance health?",
             "what's peplink's public IP?",
             "force a peplink failover",
             "refresh peplink telemetry")

    Force-failover affordance (operator's choice of path):
        -> Peplink REST/SNMP-triggered WAN-swap endpoint (Path A's
           native option, same pattern as Starlink's
           `button.rc_net_starlink_sleep_now`), OR
        -> InControl 2 fleet-action endpoint (Path B, for fleet
           operators)
        -> contract tile: button.rc_net_peplink_force_failover

See docs/recipe.md for the full howto (SNMP wiring, InControl 2
wiring, HA helpers, force-failover wiring, mode-aware
multi-WAN automations that prefer cellular in Travel/Boost and
Starlink in Home/Shore, troubleshooting, tier-a promotion outline).
"""

DOMAIN = "peplink"