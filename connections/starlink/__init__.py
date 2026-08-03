"""Starlink (sleep timer + bring-back-up controls) — tier-b recipe connection.

This module is a marker-only stub. Tier-b connections don't ship native
HA integration code; they publish a recipe (docs/recipe.md) that walks
the user through setting up an operator-side controllable smart plug
behind the Starlink PSU (or behind the router only), exposing it to HA
via whatever plug-integration the operator already uses (TP-Link /
Shelly / Sonoff / Zigbee / Modbus / ...), and telling the wizard how to
publish the RoamCore mobile-internet contract entities on top
(`rc_net_starlink_*` tiles + a one-tap wake-for-30-min button + a
quiet-hours window for automated sleep).

The audit + boundary CI can detect a `starlink/` folder that claims to
be a connection via the `DOMAIN` constant exported here. The wizard
reads the manifest + recipe at runtime.

The real sleep / wake / signal path is:

    Operator-side smart plug (TP-Link / Shelly / Sonoff / Zigbee / ...)
        -> plug integration in HA (any of the upstream integrations)
        -> HA switch entity (helper: switch.rc_net_starlink_plug)
        -> RoamCore contract layer (rc_net_starlink_sleep_state,
           rc_net_starlink_allow_sleep, rc_net_starlink_wake_30_min,
           rc_net_starlink_reachable, rc_net_starlink_signal_pct,
           rc_net_starlink_quiet_start, rc_net_starlink_quiet_end)
        -> dashboard tiles + OpenClaw queries

    Starlink local HTTP API (Gen-2/Gen-3 only)
        -> GET http://192.168.100.1/api/console/dish-status.json
        -> contract signal snapshot (sensor.rc_net_starlink_signal_pct)

See docs/recipe.md for the full howto (smart-plug wiring, HA helper
creation, optional signal-stats wiring, sleep + wake + mode-aware
automations, troubleshooting, tier-a promotion outline).
"""

DOMAIN = "starlink"