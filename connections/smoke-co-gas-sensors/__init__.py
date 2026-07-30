"""Smoke / CO / gas sensors (lifesafety for vans) — tier-b recipe connection.

This module is a marker-only stub. Tier-b connections don't ship native
HA integration code; they publish a recipe (docs/recipe.md) that walks
the user through setting up smoke / CO / propane-LPG / methane /
natural-gas safety sensors on the van (Path A — Zigbee smoke / CO /
gas detector via the ZHA GUI flow, OR Path B — Z-Wave smoke / CO
detector via the zwave_js GUI flow, OR Path C — DIY MQ-series analog
gas sensor via ESPHome + a relay-driven siren on a GPIO), and
exposes the resulting data via the upstream ZHA / zwave_js /
ESPHome integration OR HA core binary_sensor / mqtt / template
integrations, then publishes the RoamCore safety contract tiles on
top (`rc_safety_*` tiles: 8 binary_sensor + 1 sensor + 2 button +
1 select — see the `dashboard.tiles` block of connection.yml for the
full list).

The audit + boundary CI can detect a `smoke-co-gas-sensors/` folder
that claims to be a connection via the `DOMAIN` constant exported
here. The wizard reads the manifest + recipe at runtime.

The real per-operator smoke / CO / gas sensor affordance path is:

    Operator-side sensor source (Path A — Zigbee smoke / CO / gas
        detector via ZHA; the vendor's integration exposes the
        upstream `binary_sensor.smoke_*` / `binary_sensor.carbon_
        monoxide_*` / `binary_sensor.gas_*` entity via ZHA's own
        GUI flow on first run; OR Path B — Z-Wave smoke / CO
        detector via zwave_js; the zwave_js integration since
        2020.x exposes the upstream `binary_sensor.smoke_*` /
        `binary_sensor.carbon_monoxide_*` entity via the
        zwave_js GUI flow; some vendors use the Notification CC
        to differentiate test vs alarm vs low-battery states;
        OR Path C — DIY MQ-series analog gas sensor via ESPHome;
        the ESPHome integration since 2023.x exposes the analog
        reading via `sensor.*` + the threshold-derived `binary_
        sensor.*` entity)
        -> upstream binary_sensor.smoke_* / binary_sensor.carbon_
           monoxide_* / binary_sensor.gas_* (Path A ZHA OR Path B
           zwave_js) OR upstream sensor.mq9_reading + the
           ESPHome-derived binary_sensor.lpg_alarm (Path C)
        -> RoamCore contract layer (HA core `template:` binary_
           sensor + template sensor + template button + template
           select that synthesizes the rc_safety_* contract
           tiles from the upstream entities)
           (binary_sensor.rc_safety_smoke_detected,       # TRUE when any upstream smoke sensor reports smoke
            binary_sensor.rc_safety_co_detected,          # TRUE when any upstream CO sensor reports CO
            binary_sensor.rc_safety_gas_detected,         # TRUE when any upstream gas sensor reports gas above alarm threshold
            binary_sensor.rc_safety_any_alarm_active,     # aggregate: smoke OR co OR gas
            binary_sensor.rc_safety_siren_active,         # TRUE when the local siren is currently sounding
            binary_sensor.rc_safety_alarm_in_test_mode,   # TRUE when alarms are in test mode (silencing for testing)
            binary_sensor.rc_safety_low_battery_warning,  # TRUE when any sensor battery < 20 %
            binary_sensor.rc_safety_sensor_offline,       # TRUE when any upstream sensor has not checked in within its heartbeat window
            sensor.rc_safety_lowest_battery_pct,          # numeric battery % of the lowest-battery upstream sensor
            button.rc_safety_silence_alarm,               # explicit "silence the siren + acknowledge the alarm" affordance
            button.rc_safety_test_alarm,                  # explicit "run the test cycle" affordance
            select.rc_safety_alarm_mode)                  # operator-tunable: armed | night_only | silenced | disabled
        -> dashboard tiles + OpenClaw queries
            ("is smoke detected?", "is CO detected?", "is gas
             detected?", "is any safety alarm active?",
             "silence safety alarm", "trigger safety siren",
             "is siren active?", "battery low — smoke alarm",
             "battery low — CO alarm", "is alarm in test mode?")

    Lifesafety interlocks (MANDATORY before first use — operator
    must wire each one per the recipe §6):
        -> sensor-not-offline detection: when any upstream sensor
           has not checked in within its expected heartbeat
           window (5–30 minutes for battery-powered Zigbee / Z-
           Wave sensors; ESPHome sensors publish `availability`
           via mqtt / native API), binary_sensor.rc_safety_
           sensor_offline flips TRUE and the operator is
           alerted (a silent safety sensor is the most
           dangerous kind)
        -> low-battery pre-warning: when any sensor battery is
           below 20 %, binary_sensor.rc_safety_low_battery_
           warning flips TRUE; the Sunday-morning reminder
           automation warns the operator which sensor needs a
           battery swap
        -> any-alarm aggregate: binary_sensor.rc_safety_any_
           alarm_active aggregates smoke + CO + gas into a
           single tile so downstream automations (sirens +
           phone notifications + smart-cooking-aware silencing)
           can subscribe to one contract entity
        -> mode-aware lockout: when the operator selects
           `disabled` on select.rc_safety_alarm_mode, all
           sirens + notifications are suppressed; the operator
           MUST use this mode only for service windows

See docs/recipe.md for the full howto (Path A Zigbee via ZHA wiring
+ the auto-discovered binary_sensor.smoke_* / binary_sensor.carbon_
monoxide_* / binary_sensor.gas_* entity_ids + the recommended ZHA
device signature overrides for vendors that don't ship clean
signatures + Path B Z-Wave via zwave_js wiring + the Notification CC
that some vendors use to differentiate test vs alarm vs low-battery
states + Path C ESPHome MQ-series analog gas sensor YAML with the
sensor: calibration routine for the analog sensor (warm-up time +
burn-in time + threshold tuning for the specific gas of interest)
+ the binary_sensor template that derives the alarm state from the
analog reading crossing the threshold + the relay-driven siren on a
GPIO, the four §6 lifesafety interlocks in full, seven §7
automations: "loud siren + phone notification" on any alarm +
"auto-unlock deadbolts + flash all lights" on CO detection for
emergency egress + "low-battery pre-warning" when any sensor < 20 %
battery + "sensor offline" detection via mqtt last_seen /
availability topic + "monthly test cycle" via
button.rc_safety_test_alarm + "night-only mode" via
select.rc_safety_alarm_mode set to night_only + "smart-cooking
integration" via the smart-automations recipe, eight §8
troubleshooting entries including "ZHA pair failing" (Zigbee channel
conflict with the van Wi-Fi AP) + "zwave_js unpair after van power-
cycle" (Z-Wave needs the controller home ID backup) + "ESPHome MQ
sensor reading zero" (wrong ADC pin; check input: true) + "ESPHome
MQ sensor reading saturated at 4095" (wrong voltage divider) +
"siren not firing" (relay polarity; swap the buzzer leads) +
"sensor going offline when the van engine runs" (alternator noise on
the 12 V rail; add a ferrite choke + bulk capacitor) + "low-battery
warning stuck after battery swap" (ZHA device signature cache; re-
interview the device) + "false-positive smoke when cooking" (open a
window first, or use select.rc_safety_alarm_mode = silenced during
known-cooking windows), privacy, tier-a promotion outline).
"""

DOMAIN = "smoke_co_gas"
