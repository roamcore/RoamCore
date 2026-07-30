"""HVAC basics (heating/cooling foundations) — tier-b recipe connection.

This module is a marker-only stub. Tier-b connections don't ship native
HA integration code; they publish a recipe (docs/recipe.md) that walks
the user through setting up cabin heating/cooling on the van (Path A —
generic thermostat (any `climate.*` entity from HA core integrations like
`generic_thermostat`, `ecobee`, `nest`, `mitsubishi`, `daikin`, etc.);
Path B — diesel heater (Webasto / Eberspächer / Chinese diesel / Vevor
/ Chinese planer-style) via the upstream `esphome` + `binary_sensor`
+ `switch` recipe, or the `mqtt` integration when the heater has an
ESPHome-MQTT bridge; Path C — rooftop AC (Furrion / Dometic / MaxxAir /
Coleman) via IR-bridge (Broadlink / MQTT-IR-Hub) + the upstream `switch`
/ `fan` / `select` integration, or directly via the AC's own HA
integration if it has one; Path D — cabin ventilation (cabin fan /
MaxxAir / Fan-Tastic Vent / roof-vent switches) via the HA core `fan`
+ `switch` + `select` integration), and exposes the resulting data via
the upstream climate / switch / fan / sensor integration, then
publishes the RoamCore HVAC contract tiles on top (`rc_hvac_*` tiles:
the 11 contract entities documented in connection.yml — 1 climate
thermostat + 2 sensor telemetry + 2 binary_sensor activity flags + 1
fan + 1 select for fan speed + 1 outdoor sensor + 2 binary_sensor
safety flags (frost_warning + over_temp_warning) + 1 mode select).

The audit + boundary CI can detect a `hvac-basics/` folder that claims
to be a connection via the `DOMAIN` constant exported here. The wizard
reads the manifest + recipe at runtime.

The real per-operator HVAC affordance path is:

    Operator-side HVAC source (Path A — generic thermostat via any
        HA core climate integration; HA core generic_thermostat
        exposes a GUI flow since 2022.x; the operator's choice of
        climate-domain vendor integration (ecobee / nest / mitsubishi
        / daikin) also exposes a GUI flow; the upstream integration
        exposes climate.<name> entities directly; OR Path B — diesel
        heater via the upstream `esphome` integration (ESPHome exposes
        a GUI flow since 2023.x) OR the upstream `mqtt` integration
        when the heater has an ESPHome-MQTT bridge; the diesel
        heater wiring exposes switch.* + binary_sensor.* + sensor.*
        entities via HA core switch / binary_sensor / sensor
        domains; OR Path C — rooftop AC via the IR-bridge
        (Broadlink RM Mini 3 / MQTT-IR-Hub) + the upstream `switch`
        / `fan` / `select` integration; Broadlink exposes a GUI flow
        since 2022.x; MQTT-IR-Hub exposes a GUI flow since 2023.x;
        OR Path D — cabin ventilation via the HA core `fan` +
        `switch` + `select` integration; the fan integration exposes
        a GUI flow since 2022.x)
        -> upstream entity (climate.<name> for Path A; switch.* +
           binary_sensor.* + sensor.* for Path B; switch.* + fan.* +
           select.* for Path C; fan.* + switch.* for Path D)
        -> RoamCore contract layer (HA core `template:` climate /
           binary_sensor / sensor / fan / select that maps the
           upstream entities into the 11 `rc_hvac_*` contract tiles —
           rc_hvac_cabin_thermostat + rc_hvac_cabin_temperature +
           rc_hvac_cabin_humidity + rc_hvac_heater_active +
           rc_hvac_ac_active + rc_hvac_cabin_fan + rc_hvac_fan_speed
           + rc_hvac_outdoor_temperature + rc_hvac_frost_warning +
           rc_hvac_over_temp_warning + rc_hvac_mode)
        -> dashboard tiles + OpenClaw queries
            ("what is the cabin temperature?", "is the heater on?",
             "is the AC on?", "set cabin thermostat to <temp>C",
             "set cabin thermostat to heat/cool/auto/off",
             "set cabin fan speed to low/med/high/auto/off",
             "is frost warning active?", "is over-temp warning
              active?", "set HVAC mode to auto/heating/cooling/
              ventilation/disabled")

    Safety interlocks (MANDATORY before first use — operator must
    wire each one per the recipe §7):
        -> Frost warning: when `sensor.rc_hvac_outdoor_temperature`
           < 2 °C, fire `binary_sensor.rc_hvac_frost_warning` TRUE +
           force the cabin thermostat to maintain
           `climate.rc_hvac_cabin_thermostat` > 5 °C (the cabin MUST
           not drop below 5 °C — frozen pipes / condensation /
           battery damage below 0 °C). This overrides the operator's
           setpoint if the operator has the thermostat set lower.
        -> Over-temp warning: when `sensor.rc_hvac_cabin_temperature`
           > 35 °C, fire `binary_sensor.rc_hvac_over_temp_warning`
           TRUE + turn on the AC (`binary_sensor.rc_hvac_ac_active`
           TRUE) + open the cabin fan + send a push notification
           (the operator + pets + electronics must not cook). The
           cross-reference to the bluetooth-wifi-presence connection
           is for the "pets left in van" scenario — if
           `binary_sensor.rc_presence_anyone_home` is FALSE AND the
           cabin temp is > 35 °C, the over-temp alert escalates to
           a high-priority push + the dashboard highlights the
           over-temp tile in red.
        -> Low-voltage lockout: when `sensor.rc_power_battery_soc`
           < 30 % (from the Victron connection), fire
           `binary_sensor.rc_hvac_low_voltage_lockout`-equivalent
           behavior — disable the diesel heater (Path B) unless
           `binary_sensor.rc_power_shore_connected` is TRUE; the AC
           (Path C) is also disabled because both pull 10–30 A
           sustained which would brown out the battery bank below
           30 % SOC. The operator can still manually turn on the
           cabin fan (Path D) which is < 1 A. The cross-reference to
           the Victron connection is the same pattern that the
           heated-floors + Happijac bed lift connections use for
           their low-voltage lockout interlocks.
        -> Mode-aware lockouts (Stealth / Sleep / Boost):
           - Stealth silent hours auto-lower fan: when
             `select.rc_mode == stealth` (from the mode/automation-
             builder connection), force the cabin fan
             (`select.rc_hvac_fan_speed`) to `low` so the fan
             doesn't wake the campground neighbors.
           - Sleep mode fan-off + eco: when
             `select.rc_mode == sleep`, force the cabin fan OFF
             (`fan.rc_hvac_cabin_fan` to OFF) + drop the AC setpoint
             by 2 °C + drop the heater setpoint by 2 °C for eco
             mode (the operator is asleep — full eco).
           - Boost disable-mode-aware-lockouts: when
             `select.rc_mode == boost`, disable ALL the above
             mode-aware lockouts (Stealth / Sleep) so the operator
             has full climate control during service work / pre-trip
             packing.
           - The dashboard tile `select.rc_hvac_mode` exposes the
             operator's local override (`auto` / `heating` /
             `cooling` / `ventilation` / `disabled`) on top of the
             mode-aware defaults.

See docs/recipe.md for the full howto (Path A generic thermostat via
generic_thermostat / ecobee / nest / mitsubishi / daikin with the
HA core climate domain wiring + the recommended generic thermostat
pairing instructions, Path B diesel heater via ESPHome YAML for the
glow plug + main blower + combustion fan + safety thermistor +
flame-sense binary_sensor + the MQTT variant when the heater has
an ESPHome-MQTT bridge, Path C rooftop AC via IR-bridge (Broadlink
RM Mini 3 / MQTT-IR-Hub) + switch + fan + select wiring for AC power
+ mode + fan speed + temperature + the native Furrion / Dometic
integration paths where available, Path D cabin ventilation via
MaxxAir / Fan-Tastic Vent + roof-vent switches + cross-flow vent
control, the four §7 safety interlocks in full, the six §8
automations including the "Stealth auto-lower fan" + "Sleep eco-
mode" + "Boost disable-mode-aware-lockouts" + "frost auto-heat" +
"over-temp auto-cool + alert" + "mode-aware scheduling for morning
pre-warm" + six §9 troubleshooting entries including "thermostat
not responding" (check generic_thermostat config), "heater won't
ignite" (glow plug pre-heat timeout), "heater shuts off after 30s"
(flame-sense failure), "AC doesn't respond to IR" (re-learn IR
codes on the bridge), "fan stuck on one speed" (wiring fault /
relay stuck), "frost warning stuck on" (cross-check outdoor
sensor), "over-temp warning stuck on" (cross-check cabin sensor),
"low-voltage lockout stuck on after charging" (cross-check Victron
SOC), privacy, tier-a promotion outline).
"""

DOMAIN = "hvac_basics"
