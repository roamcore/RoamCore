"""Smart automations (one-click enable / disable — 17 prebuilt van-life automations) — tier-b recipe connection.

This module is a marker-only stub. Tier-b connections don't ship native
HA integration code; they publish a recipe (docs/recipe.md) that walks
the user through setting up the 17 prebuilt automations on the van
using HA Core's native `automation:` domain + the operator-side
managed-marker convention (description starts with `Managed by
RoamCore Smart Automations v0.1`, contains `key=<name>`, contains
`hash=<template hash>` — see docs/guides/smart-automations.md), and
exposes the audit + contract tiles (`rc_safety_automations_*` +
`rc_safety_automation_<name>` binary_sensors) on top.

The audit + boundary CI can detect a `smart-automations/` folder that
claims to be a connection via the `DOMAIN` constant exported here.
The wizard reads the manifest + recipe at runtime.

The real per-operator 1-click enable/disable affordance path is:

    Operator chooses which of the 17 automations to enable from
    `RoamCore -> Settings -> Smart Automations`
        -> HA Core's `automation:` domain (the upstream integration
           exposes its own GUI flow on first run; the recipe does
           NOT add a tier-a wrapper around it)
        -> HA Core creates a standard HA automation with the
           RoamCore-managed marker in the description:
              `Managed by RoamCore Smart Automations v0.1`
              `key=<name>`
              `hash=<template hash>`
        -> HA Core's `template:` binary_sensor mirrors each managed
           automation's enable/disable state into the
           `binary_sensor.rc_safety_automation_<name>` contract tile
        -> HA Core's `template:` sensor aggregates the enabled count
           + the missing-dependencies count + the all-ready flag
        -> HA Core's `button:` + `select:` expose the
           enable-all-ready / disable-all / view-filter affordances
        -> HA Core's `input_boolean:` + `input_select:` provide the
           per-automation toggle surface that the upstream HA
           automations listen to for their enabled/disabled state
        -> 24 `rc_safety_automation_*` + `rc_safety_automations_*`
           dashboard tiles + 9 OpenClaw queries
           (`list smart automations`, `enable <name>`, `disable
           <name>`, `enable all ready smart automations`, `disable
           all smart automations`, `which smart automations are
           missing dependencies?`, `how many smart automations are
           enabled?`, `is <name> enabled?`, `what does <name> do?`)

    If the operator later edits the automation in HA (changing the
    triggers/actions), RoamCore stops updating its logic but still
    allows enable/disable. This is the documented behavior from
    docs/guides/smart-automations.md "Editing" section.

The 17 automations + their prerequisites (see docs/guides/smart-automations.md
for the canonical automation list):

    1. Night Mode (script.rc_mode_set_stealth, script.rc_mode_set_auto)
    2. Auto Internet Failover (sensor.rc_net_wan_status,
       script.rc_openwrt_prefer_auto)
    3. Low Battery Mode (sensor.rc_power_battery_soc,
       binary_sensor.rc_power_shore_connected,
       script.rc_mode_set_camp)
    4. Freeze Protection (sensor.rc_weather_temp_c)
    5. Daily Trip Log (sensor.rc_trip_distance_today_mi,
       sensor.rc_trip_time_today)
    6. Battery Full Alert (sensor.rc_power_battery_soc)
    7. Inverter Overheat Alert (sensor.rc_power_inverter_temperature)
    8. Router Overheat Alert (sensor.rc_router_temperature)
    9. Shore Power Connected (binary_sensor.rc_power_shore_connected)
    10. Shore Power Disconnected (binary_sensor.rc_power_shore_connected)
    11. Internet Recovery (binary_sensor.rc_net_internet_reachable,
        script.rc_openwrt_restart_network)
    12. Arrive at Camp (sensor.rc_location_speed, script.rc_mode_set_camp)
    13. Depart Travel Mode (sensor.rc_location_speed,
        script.rc_mode_set_travel)
    14. Solar is Crushing It (sensor.rc_power_solar_power)
    15. Battery Critical Alert (sensor.rc_power_battery_soc)
    16. Bedtime Level Check (binary_sensor.rc_level, sensor.rc_level_status)
    17. Quiet Hours Reminder (input_select.rc_mode,
        script.rc_mode_set_stealth)

See docs/recipe.md for the full howto.
"""

DOMAIN = "smart_automations"