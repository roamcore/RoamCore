"""Heated floors + engine pre-heat (cold-weather comfort) — tier-b recipe connection.

This module is a marker-only stub. Tier-b connections don't ship native
HA integration code; they publish a recipe (docs/recipe.md) that walks
the user through setting up heated-floor + optional engine pre-heat
control on the van (Path A — smart thermostat that already exposes a
`climate.*` entity in HA, OR Path B — HA core `generic_thermostat:`
wrapping a temperature probe + a relay-driven heater, OR Path C —
optional engine pre-heat via a relay or CAN bus gateway for Webasto /
Espar / Eberspächer / DIY coolant-loop heater), and exposes the
resulting data via the upstream vendor integration or HA core
integrations, then publishes the RoamCore HVAC contract tiles on top
(`rc_hvac_*` tiles: a `climate.rc_hvac_floor_thermostat` + a
`sensor.rc_hvac_floor_current_temp` + a `sensor.rc_hvac_interior_temp`
+ 3× `binary_sensor.rc_hvac_floor_*` (heating_active / maintaining /
off) + a `switch.rc_hvac_floor_heater` + a `number.rc_hvac_floor_setpoint`
+ a `select.rc_hvac_floor_mode` + a `binary_sensor.rc_hvac_floor_low_voltage_lockout`
+ a `switch.rc_hvac_engine_preheat` + a `binary_sensor.rc_hvac_engine_preheat_active`
+ a `sensor.rc_hvac_engine_preheat_runtime_min`).

The audit + boundary CI can detect a `heated-floors/` folder that
claims to be a connection via the `DOMAIN` constant exported here.
The wizard reads the manifest + recipe at runtime.

The real per-operator cold-weather comfort affordance path is:

    Operator-side heated floor source (Path A — smart thermostat
        (Mysa / Shelly H&T / generic-Zigbee thermostat); the vendor
        integration exposes the upstream `climate.floor_thermostat`
        entity via its own GUI flow on first run; OR Path B — HA core
        `generic_thermostat:` integration since 2022.x wraps a
        `sensor.interior_temp` + a `switch.heater_relay` (Shelly 1 /
        Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano Switch or a relay on
        ESPHome) into a virtual `climate.floor_heater`)
        -> upstream climate.floor_thermostat (Path A smart
           thermostat integration) OR upstream climate.floor_heater
           (Path B HA core generic_thermostat) + the upstream
           temperature sensors + the upstream switch.heater_relay
        -> RoamCore contract layer (HA core `template:` climate +
           template sensors + template binary_sensors + template
           switch + template number + template select that
           synthesizes the rc_hvac_* contract tiles from the
           upstream entities)
           (climate.rc_hvac_floor_thermostat,
            sensor.rc_hvac_floor_current_temp,                # current temperature reading from the climate's current_temperature attribute
            sensor.rc_hvac_interior_temp,                     # interior air probe (DS18B20 1-Wire / Zigbee / Shelly H&T)
            binary_sensor.rc_hvac_floor_heating_active,       # derived from climate's hvac_action == "heating"
            binary_sensor.rc_hvac_floor_maintaining,          # derived from climate's hvac_action == "idle" while setpoint > current_temp
            binary_sensor.rc_hvac_floor_off,                  # derived from climate's hvac_action == "off" OR state == "off"
            switch.rc_hvac_floor_heater,                      # explicit heater on/off affordance (Path B; Path A uses climate turn_on/turn_off)
            number.rc_hvac_floor_setpoint,                    # numeric setpoint control (delegates to climate.set_temperature)
            select.rc_hvac_floor_mode,                        # auto | eco | boost | off — operator-tunable mode
            binary_sensor.rc_hvac_floor_low_voltage_lockout,  # TRUE when sensor.rc_power_battery_soc < 20 % AND binary_sensor.rc_power_shore_connected == off (cross-references Victron connections/victron/ recipe)
            switch.rc_hvac_engine_preheat,                    # optional Path C — engine preheat on/off (Webasto / Espar / Eberspächer / DIY coolant-loop)
            binary_sensor.rc_hvac_engine_preheat_active,      # TRUE when switch.rc_hvac_engine_preheat is on AND cabin temp is rising over a 5-minute window
            sensor.rc_hvac_engine_preheat_runtime_min)        # daily runtime tracker (utility_meter integration)
        -> dashboard tiles + OpenClaw queries
            ("warm up the van", "set floor heat", "turn off
             floor heat", "floor temperature", "cabin
             temperature", "is floor heating?", "is floor
             maintaining?", "is floor off?", "is floor low-voltage
             locked?", "set floor mode", "start engine preheat",
             "stop engine preheat", "is engine preheat running?",
             "engine preheat runtime today")

    Safety interlocks (MANDATORY before first use — operator must wire
    each one per the recipe §7):
        -> low-voltage lockout: binary_sensor.rc_hvac_floor_low_
           voltage_lockout is TRUE whenever sensor.rc_power_battery_
           soc < 20 % (cross-references the Victron
           `connections/victron/` recipe) AND binary_sensor.rc_power_
           shore_connected == off; downstream HeatingRequested
           commands are rejected until SOC recovers OR shore is
           reconnected (the heated floor + engine preheat together
           can pull 10–30 A sustained)
        -> shore-power-aware throttling: when shore is connected
           (`binary_sensor.rc_power_shore_connected == on`), the
           floor can run aggressively at the operator's setpoint;
           when off shore + on battery, the floor setpoint is
           clamped to a lower value (e.g. 12 °C instead of 20 °C)
           to conserve power — this is enforced in the automation
           layer, not in the contract entities
        -> mode-aware lockouts: Stealth silent hours reduce floor
           heat to setpoint -3 °C; Sleep mode locks the floor to a
           min setpoint of 10 °C for frost protection; Boost mode
           disables mode-aware throttling for service work — the
           `select.rc_hvac_floor_mode` operator-tunable mode
           respects these as the default policy
        -> presence-aware pre-warm: when the operator's phone
           reconnects to the LAN (`binary_sensor.rc_presence_
           operator_phone_arrived` from the bluetooth-wifi-presence
           `connections/bluetooth-wifi-presence/` recipe) AND it's
           been >24h since the last warm-up, the automation starts
           the floor heat to the operator's preferred pre-warm
           setpoint (default 18 °C) so the cabin is comfortable
           when they arrive
        -> frost-protection automation: if mode is `auto` AND engine
           preheat is off AND interior temp < 5 °C → enable gentle
           floor heating for frost protection (cross-references the
           upcoming happijac `connections/happijac/` recipe's
           `select.rc_bed_lift_mode` for the mode signal)

See docs/recipe.md for the full howto (Path A smart thermostat wiring
+ the entity_id surfacing + the set_hvac_mode / set_temperature
service calls + the template sensor that derives "Heating" /
"Maintaining" / "Off" states from the climate's hvac_action
attribute, Path B HA core generic_thermostat: YAML wrapping a sensor
+ a switch with min_temp / max_temp / cold_tolerance / hot_tolerance
/ keep_alive, Path C optional engine pre-heat via a relay or CAN
bus gateway + the binary_sensor.engine_preheat_active template that
derives "is the engine preheat actually producing heat" from the
cabin temp trend, the five safety interlocks in full, six §7
automations: "Warm up" scene + shore-power-aware + mode-aware Stealth
/Sleep/Boost + low-voltage lockout when SOC < 20 % + presence-aware
pre-warm when operator phone reconnects + engine preheat schedule
auto-start at 06:30 weekdays when mode is Morning + ambient temp <
5 °C, eight §8 troubleshooting entries including "floor heater not
turning on" (relay polarity / coil voltage), "heater stuck on" (relay
welded shut — replace), "temperature probe reading -40 °C" (probe
disconnected), "setpoint not sticking" (template race; ensure
keep_alive is set), "floor heater cycling rapidly" (cold_tolerance
too tight), "engine preheat switch toggles but engine doesn't
actually warm" (CAN bus gateway not connected), "engine preheat brief
but heater runtime tracker still incremented" (sensor debounce),
"low-voltage lockout stuck on after charging" (cross-check Victron
SOC), and "generic_thermostat min_temp clamp missing" (template
render error), privacy, tier-a promotion outline).
"""

DOMAIN = "heated_floors"