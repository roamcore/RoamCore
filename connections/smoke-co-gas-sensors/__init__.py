"""Smoke / CO / gas safety sensors (van life safety monitoring) — tier-b recipe connection.

This module is a marker-only stub. Tier-b connections don't ship native
HA integration code; they publish a recipe (docs/recipe.md) that walks
the user through setting up smoke / CO / gas safety monitoring on the
van (Path A — smart detectors that already expose `binary_sensor.*` +
`sensor.*` entities in HA via their vendor integration; Path B —
basic Kidde / First Alert battery-only alarms with no HA integration
as the minimum safety baseline; Path C — propane/LPG detectors via a
Modbus bridge or ESPHome analog input), and exposes the resulting
data via the upstream vendor integration or HA core integrations,
then publishes the RoamCore safety contract tiles on top
(`rc_safety_*` tiles: the 13 contract entities documented in
connection.yml).

The audit + boundary CI can detect a `smoke-co-gas-sensors/` folder
that claims to be a connection via the `DOMAIN` constant exported
here. The wizard reads the manifest + recipe at runtime.

The real per-operator safety monitoring affordance path is:

    Operator-side smoke / CO / gas detector source (Path A — smart
        detectors Nest Protect / First Alert Z-Wave / X-Sense Zigbee
        / Heiman Z-Wave / Zipato Zigbee; the vendor integration
        exposes the upstream `binary_sensor.*` + `sensor.*` entities
        via its own GUI flow on first run; OR Path B — basic Kidde /
        First Alert battery-only alarm with NO HA integration; OR
        Path C — propane/LPG detector via a Modbus bridge or ESPHome
        analog input)
        -> upstream binary_sensor.* (Path A smart detector
           integration) OR no upstream entity (Path B basic alarm)
           OR upstream binary_sensor.* (Path C ESPHome analog input)
        -> RoamCore contract layer (HA core `template:` binary_sensor
           + template sensors + template select + template buttons
           that synthesizes the rc_safety_* contract tiles from the
           upstream entities)
        -> dashboard tiles + OpenClaw queries

    Safety interlocks (MANDATORY before first use — operator must wire
    each one per the recipe §7):
        -> smoke detected: emergency-egress unlock + siren + lights
           + push notification (cross-references the upcoming
           deadbolts connection for the emergency-egress unlock)
        -> CO detected: cut propane solenoid + open roof vents +
           turn off HVAC + push notification
        -> gas leak detected: cut propane solenoid + open roof vents
           + turn off HVAC + push notification
        -> sensor offline (no check-in for >30 min): push notification
        -> sensor battery low: push notification
        -> alarm silenced: auto-resume after operator-set duration
           (default 10 minutes)

See docs/recipe.md for the full howto.
"""

DOMAIN = "smoke_co_gas_sensors"
