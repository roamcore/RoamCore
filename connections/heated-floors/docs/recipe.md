# Heated floors + engine pre-heat — tier-b recipe connection

This is the full howto for the `connections/heated-floors/` tier-b
recipe connection. It walks through wiring a heated floor (Path A —
smart thermostat, OR Path B — HA core `generic_thermostat:` wrapping a
temperature probe + a relay-driven heater) + optional engine pre-heat
(Path C — Webasto / Espar / Eberspächer / DIY coolant-loop via a
relay or CAN bus gateway) on the van, mapping the device-side
temperature probes + relay + optional engine preheat into the
`rc_hvac_*` contract tiles, layering the five MANDATORY safety
interlocks (low-voltage lockout via `sensor.rc_power_battery_soc` +
shore-power-aware throttling + mode-aware Stealth/Sleep/Boost
lockouts + presence-aware pre-warm + frost-protection automation) +
the §7 automations, and promoting the connection to tier-a when the
bench fixture lands.

## §1 What are heated floors + engine pre-heat in RoamCore?

Heated floors + optional engine pre-heat — cold-weather comfort controls for vans — are the **foundation** of every "Warm up" automation in winter van life. They are positioned in RoamCore as:

- A **vendor-neutral** climate + switch + sensor contract. The contract talks to whatever smart thermostat integration the operator already runs (Path A — Mysa / Shelly H&T / generic-Zigbee), or to whatever relay-driven heater + temperature probe the operator wires for HA core `generic_thermostat:` (Path B), or to whatever engine pre-heat relay or CAN bus gateway the operator wires for the optional engine pre-heat (Path C — Webasto / Espar / Eberspächer / DIY coolant-loop). The contract IDs are `rc_hvac_*` — they don't care which vendor or hardware path the operator picked.

- A **single "Warm up" scene** that orchestrates floor heat + interior temp + engine pre-heat into one command. The "Warm up" scene is the day-1 affordance: operator says "warm up the van" (OpenClaw query `warm_up_van`), and the floor heat + engine pre-heat start in concert, with the `binary_sensor.rc_hvac_floor_low_voltage_lockout` pre-check gating the whole thing.

- A **shore-power-aware** system. When shore is connected (`binary_sensor.rc_power_shore_connected == on`), the floor can run aggressively at the operator's setpoint; when off shore + on battery, the floor setpoint is clamped to a lower value (e.g. 12 °C instead of 20 °C) to conserve power. The cross-reference is to the Victron `connections/victron/` recipe's `binary_sensor.rc_power_shore_connected`.

- A **mode-aware** system. RoamCore modes (Stealth / Sleep / Boost) drive default policy: Stealth silent hours reduce floor heat to setpoint -3 °C; Sleep mode locks the floor to a min setpoint of 10 °C for frost protection; Boost mode disables mode-aware throttling for service work. The operator can override via the `select.rc_hvac_floor_mode`.

- A **presence-aware** system. When the operator's phone reconnects to the LAN AND it's been >24h since the last warm-up, the automation starts the floor heat to the operator's preferred pre-warm setpoint (default 18 °C) so the cabin is comfortable when they arrive. The cross-reference is to the bluetooth-wifi-presence `connections/bluetooth-wifi-presence/` recipe's `binary_sensor.rc_presence_operator_phone_arrived`.

- A **safety-first** system. The low-voltage lockout refuses to start the floor + engine pre-heat when inverter SOC < 20 % AND shore is disconnected (heated floor + engine pre-heat together can pull 10–30 A sustained). The frost-protection automation cross-references the upcoming happijac `connections/happijac/` recipe's `select.rc_bed_lift_mode` for the mode signal.

RoamCore does **not** ship a heated floor, a thermostat, a temperature probe, an engine pre-heat, or any vendor-specific controller. The recipe is the install: the operator picks Path A / Path B / Path C, wires the hardware, follows the YAML, and ends up with the `rc_hvac_*` contract tiles + the OpenClaw queries that bind to them.

## §2 Prerequisites

Path A — Smart thermostat:

- The operator's existing smart thermostat (Mysa / Shelly H&T / generic-Zigbee thermostat) installed in the van and powered up.
- The vendor's HA integration configured (each vendor has its own GUI flow; the recipe assumes the upstream `climate.*` entity already appears in HA).
- The vendor integration's `climate.*` entity ID — the recipe surfaces the entity ID + wraps it into the `rc_hvac_*` contract via templates.

Path B — Generic thermostat (no smart thermostat; relay-driven heater + temperature probe):

- A relay-driven heater (the heated floor element itself draws 5–15 A sustained depending on wattage; the relay must be rated for the load — Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano Switch or a relay on ESPHome for solid-state switching).
- A 5 V logic-level compatible relay coil (the heater's control board may be 12 V or 24 V; ensure the relay coil voltage matches).
- A fuse per relay per the upstream relay's spec (typically a 15 A or 20 A fuse for a 1500–2000 W heated floor at 120 V).
- A flyback diode per relay coil (only if the relay is a mechanical relay; solid-state relays don't need a flyback diode).
- A temperature probe (DS18B20 1-Wire / Zigbee / Shelly H&T / etc.) wired to an ESPHome device OR a Wi-Fi temperature sensor. The probe must be located in the cabin air (NOT under the floor — the floor probe is optional).
- An optional floor probe (DS18B20 1-Wire attached under the floor covering) for floor-temperature feedback.
- HA core `generic_thermostat:` integration (HA core since 2022.x; config_flow since 2022.x).

Path C — Optional engine pre-heat:

- Engine pre-heat hardware installed (Webasto Thermo Top Evo / Thermo Top Pro / Espar D2 / D4 / D5 / Eberspächer Hydronic S3 / DIY coolant-loop heater).
- A relay to switch the engine pre-heat on/off (Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano Switch or a relay on ESPHome). The relay's coil voltage must match the engine pre-heat's control input (typically 12 V).
- OR a CAN bus gateway for the higher-end Thermo Top Evo / Hydronic S3 (the gateway exposes the heater as a `climate.*` entity OR a `switch.*` entity depending on the gateway vendor).
- A temperature probe in the cabin air to derive `binary_sensor.rc_hvac_engine_preheat_active` from the cabin temp trend (when the engine preheat is on AND cabin temp is rising over a 5-minute window → active).

Safety prerequisites (operator MUST wire these before first use; the recipe §7 walks through each):

- The Victron `connections/victron/` recipe's `sensor.rc_power_battery_soc` + `binary_sensor.rc_power_shore_connected` tiles exist (the low-voltage lockout cross-references them).
- The bluetooth-wifi-presence `connections/bluetooth-wifi-presence/` recipe's `binary_sensor.rc_presence_operator_phone_arrived` tile exists (the presence-aware pre-warm automation cross-references it).
- The operator's interior air temperature probe is wired AND reporting sane values (typical 15–25 °C; a -40 °C reading means the probe is disconnected — see §8 troubleshooting).

## §3 Path A — Smart thermostat (recommended for operators who already own a Mysa / Shelly H&T / generic-Zigbee thermostat)

The vendor integration's `climate.*` entity is already exposed in HA. The recipe surfaces the entity ID + wraps it into the `rc_hvac_*` contract via templates.

```yaml
# Path A — wrap the upstream vendor thermostat's climate entity into the
# rc_hvac_* contract. Substitute the operator's actual vendor
# climate.* entity id where noted.
#
# Climate-domain integrations expose `hvac_action` (the climate's current
# action attribute) since 2022.x; "heating" / "idle" / "off" are the three
# canonical values. We derive the three state binary_sensors from this
# attribute.

template:
  - sensor:
      # Floor current temperature — read from the upstream climate's
      # current_temperature attribute. This is the "what does the
      # thermostat think the floor temp is right now?" reading.
      - name: "rc_hvac_floor_current_temp"
        state: "{{ state_attr('climate.mysa_floor_thermostat', 'current_temperature') }}"
        unit_of_measurement: "°C"
        device_class: temperature
        state_class: measurement

  - binary_sensor:
      # Floor heating active — TRUE when the upstream climate is actively
      # heating (hvac_action == "heating"). The state machine: "heating" /
      # "idle" (when setpoint > current_temp) / "off".
      - name: "rc_hvac_floor_heating_active"
        state: "{{ state_attr('climate.mysa_floor_thermostat', 'hvac_action') == 'heating' }}"
        device_class: heat

      # Floor maintaining — TRUE when the upstream climate is idle (heater
      # is off) BUT the setpoint > current_temp (the floor is warm enough
      # to maintain at the setpoint; the heater cycles on/off as needed).
      - name: "rc_hvac_floor_maintaining"
        state: >-
          {{ state_attr('climate.mysa_floor_thermostat', 'hvac_action') == 'idle'
             and state_attr('climate.mysa_floor_thermostat', 'temperature') >
                 state_attr('climate.mysa_floor_thermostat', 'current_temperature') }}
        device_class: heat

      # Floor off — TRUE when the climate is off (hvac_action == "off" OR
      # hvac_mode == "off").
      - name: "rc_hvac_floor_off"
        state: >-
          {{ state_attr('climate.mysa_floor_thermostat', 'hvac_action') == 'off'
             or states('climate.mysa_floor_thermostat') == 'off' }}
        device_class: heat
```

The upstream `climate.mysa_floor_thermostat` (or whatever vendor's climate entity ID) is exposed directly as `climate.rc_hvac_floor_thermostat` via a template climate:

```yaml
template:
  - climate:
      # rc_hvac_floor_thermostat — vendor-neutral wrapper around the
      # upstream climate. The set_temperature service call delegates
      # directly to the upstream climate.set_temperature.
      rc_hvac_floor_thermostat:
        friendly_name: "RC Floor thermostat"
        value_template: "{{ states('climate.mysa_floor_thermostat') }}"
        modes:
          - "off"
          - "heat"
          - "auto"
        mode_template: "{{ states('climate.mysa_floor_thermostat') }}"
        temperature_template: "{{ state_attr('climate.mysa_floor_thermostat', 'current_temperature') }}"
        set_temperature:
          - service: climate.set_temperature
            data:
              entity_id: climate.mysa_floor_thermostat
              temperature: "{{ temperature }}"
        set_mode:
          - service: climate.set_hvac_mode
            data:
              entity_id: climate.mysa_floor_thermostat
              hvac_mode: "{{ mode }}"
```

The `number.rc_hvac_floor_setpoint` tile delegates to `climate.set_temperature`:

```yaml
template:
  - number:
      - name: "rc_hvac_floor_setpoint"
        min_value: 5
        max_value: 30
        step: 0.5
        unit_of_measurement: "°C"
        device_class: temperature
        state: "{{ state_attr('climate.mysa_floor_thermostat', 'temperature') }}"
        set_value:
          - service: climate.set_temperature
            data:
              entity_id: climate.mysa_floor_thermostat
              temperature: "{{ value }}"
```

## §4 Path B — Generic thermostat (no smart thermostat; just a temperature probe + a relay-driven heater)

Full HA core `generic_thermostat:` YAML wiring a `sensor.interior_temp` (a probe) + a `switch.heater_relay` (Shelly / Shelly Plus / Zooz / Aeotec dry-contact or a relay on ESPHome) into a virtual `climate.floor_heater`. Includes the `min_temp` / `max_temp` / `cold_tolerance` / `hot_tolerance` / `keep_alive` settings.

```yaml
# connections/heated-floors/generic-thermostat.yaml
#
# Path B — HA core `generic_thermostat:` wrapping a temperature probe +
# a relay-driven heater. Substitute the operator's actual entity ids
# where noted.
#
# Prerequisites:
#   - sensor.interior_temp is wired + reporting sane values (15–25 °C
#     typical; -40 °C means the probe is disconnected)
#   - switch.heater_relay is wired + the upstream relay integration
#     (Shelly / Shelly Plus / Zooz ZEN17 / Aeotec Nano Switch / ESPHome)
#     has its own GUI flow configured
#
# Note on keep_alive: this is MANDATORY. Without `keep_alive`, the
# climate goes stale after a few minutes and stops issuing on/off
# commands to the relay; the operator will see the setpoint stick but
# the relay never toggle. See §8 troubleshooting.

climate:
  - platform: generic_thermostat
    name: Floor heater
    heater: switch.heater_relay               # the relay-driven heater (Shelly / ESPHome / etc.)
    target_sensor: sensor.interior_temp        # the interior air probe (NOT the floor probe)
    min_temp: 5                                # min setpoint (clamped to prevent frost-damage cycles below 5 °C)
    max_temp: 30                               # max setpoint (above 30 °C the floor is uncomfortably hot)
    cold_tolerance: 0.5                        # the climate turns on the heater when temp is 0.5 °C below setpoint
    hot_tolerance: 0.5                         # the climate turns off the heater when temp is 0.5 °C above setpoint
    keep_alive:                                # MANDATORY — without this the climate goes stale
      minutes: 3
    initial_hvac_mode: "off"                   # start off; operator enables via select.rc_hvac_floor_mode or the climate turn_on service
    away_temp: 12                              # eco/away setpoint when off-shore
    precision: 0.1                             # setpoint precision (0.5 °C is too coarse for a floor)
```

The `climate.floor_heater` upstream entity is exposed directly as `climate.rc_hvac_floor_thermostat` via the same template climate wrapper from §3 (substitute `climate.floor_heater` for `climate.mysa_floor_thermostat`).

## §5 Path C — Optional engine pre-heat

Webasto / Espar / Eberspächer / DIY coolant-loop via a relay OR a CAN bus gateway. The recipe shows the `switch.engine_preheat` entity + a `binary_sensor.engine_preheat_active` template that derives "is the engine preheat actually producing heat" from the cabin temp trend — when the switch is on AND cabin temp is rising over a 5-minute window → active.

```yaml
# connections/heated-floors/engine-preheat.yaml
#
# Path C — optional engine pre-heat. The relay (Shelly / Shelly Plus /
# Zooz ZEN17 / Aeotec Nano Switch or a relay on ESPHome) drives the
# engine pre-heat control input. For higher-end Webasto Thermo Top
# Evo / Eberspächer Hydronic S3, a CAN bus gateway exposes the heater
# as a `climate.*` entity directly; substitute the gateway's entity id.
#
# The binary_sensor.rc_hvac_engine_preheat_active template derives
# "is the engine preheat actually producing heat" from the cabin temp
# trend: when the switch is on AND cabin temp is rising over a
# 5-minute window → active. This catches the case where the relay
# toggles but the engine pre-heat doesn't actually fire (e.g. out of
# fuel, CAN bus gateway disconnected, ignition wire not connected).

switch:
  - platform: template
    switches:
      rc_hvac_engine_preheat:
        friendly_name: "RC Engine preheat"
        value_template: "{{ is_state('switch.engine_preheat', 'on') }}"
        turn_on:
          - service: switch.turn_on
            data:
              entity_id: switch.engine_preheat
        turn_off:
          - service: switch.turn_off
            data:
              entity_id: switch.engine_preheat

template:
  - binary_sensor:
      - name: "rc_hvac_engine_preheat_active"
        state: >-
          {{ is_state('switch.engine_preheat', 'on')
             and (states('sensor.rc_hvac_interior_temp') | float(0)
                  > (state_attr('sensor.rc_hvac_interior_temp', 'last_5min_avg') | float(0))) }}
        device_class: heat
```

The `sensor.rc_hvac_engine_preheat_runtime_min` daily runtime tracker is implemented via utility_meter:

```yaml
utility_meter:
  engine_preheat_runtime:
    source: switch.engine_preheat
    cycle: daily
    name: "rc_hvac_engine_preheat_runtime_min"
    unit_of_measurement: "min"
```

## §6 RoamCore contract entities

The 13 `rc_hvac_*` tiles + how the upstream `climate.*` + `switch.*` + `sensor.*` templates expose them + translation helpers needed for the binary_sensors / numeric setpoint.

The full tile set (per `connection.yml` `dashboard.tiles`):

- `climate.rc_hvac_floor_thermostat` — vendor-neutral climate wrapper (Path A: wraps the upstream vendor `climate.*`; Path B: exposes the upstream `climate.floor_heater` directly; Path C: N/A — engine preheat is a switch, not a climate).
- `sensor.rc_hvac_floor_current_temp` — current floor temperature (Path A: from upstream climate's `current_temperature`; Path B: from the `sensor.interior_temp` probe; Path C: N/A).
- `sensor.rc_hvac_interior_temp` — interior air temperature (separate from floor; cross-references the temperature probe from Path A OR Path B).
- `binary_sensor.rc_hvac_floor_heating_active` — TRUE when the climate's `hvac_action == "heating"`.
- `binary_sensor.rc_hvac_floor_maintaining` — TRUE when the climate's `hvac_action == "idle"` AND setpoint > current_temp.
- `binary_sensor.rc_hvac_floor_off` — TRUE when the climate's `hvac_action == "off"` OR state == "off".
- `switch.rc_hvac_floor_heater` — explicit heater on/off affordance (Path B relay-driven; Path A uses climate `turn_on` / `turn_off`).
- `number.rc_hvac_floor_setpoint` — numeric setpoint control (delegates to `climate.set_temperature`).
- `select.rc_hvac_floor_mode` — `auto` / `eco` / `boost` / `off`.
- `binary_sensor.rc_hvac_floor_low_voltage_lockout` — TRUE when `sensor.rc_power_battery_soc < 20 %` AND `binary_sensor.rc_power_shore_connected == off` (cross-references the Victron `connections/victron/` recipe).
- `switch.rc_hvac_engine_preheat` — optional Path C engine preheat on/off affordance.
- `binary_sensor.rc_hvac_engine_preheat_active` — TRUE when engine preheat switch is on AND cabin temp is rising over a 5-minute window.
- `sensor.rc_hvac_engine_preheat_runtime_min` — daily runtime tracker.

The low-voltage lockout template:

```yaml
template:
  - binary_sensor:
      - name: "rc_hvac_floor_low_voltage_lockout"
        state: >-
          {{ states('sensor.rc_power_battery_soc') | float(100) < 20
             and is_state('binary_sensor.rc_power_shore_connected', 'off') }}
        device_class: problem
```

The mode select:

```yaml
select:
  - platform: template
    selects:
      rc_hvac_floor_mode:
        options:
          - "auto"
          - "eco"
          - "boost"
          - "off"
        initial: "auto"
```

## §7 Automations (MANDATORY before first use — operator must wire each one)

Six automations to enable (the recipe ships the full YAML for each):

1. **"Warm up" scene** — orchestrates floor heat + interior temp + engine pre-heat into one command. The scene starts the floor heat + engine pre-heat in concert, with the `binary_sensor.rc_hvac_floor_low_voltage_lockout` pre-check gating the whole thing. If the low-voltage lockout is TRUE, the scene sends an alert via Music Assistant TTS (`media_player.rc_media_zone_living`) and refuses to start.

2. **Shore-power-aware throttling** — when shore is connected (`binary_sensor.rc_power_shore_connected == on`), the floor can run at the operator's setpoint; when off shore + on battery, the floor setpoint is clamped to a lower value (e.g. 12 °C instead of 20 °C) to conserve power. The automation sets `number.rc_hvac_floor_setpoint` based on the shore-connection state.

3. **Mode-aware (Stealth / Sleep / Boost)** — Stealth silent hours reduce floor heat to setpoint -3 °C; Sleep mode locks the floor to a min setpoint of 10 °C for frost protection; Boost mode disables mode-aware throttling for service work. The automation reads the RoamCore mode (`select.rc_system_mode` — assumed upstream) and adjusts the floor setpoint accordingly.

4. **Low-voltage lockout when SOC < 20 %** — refuses to start the floor + engine pre-heat when inverter SOC < 20 % AND shore is disconnected. The automation flips `binary_sensor.rc_hvac_floor_low_voltage_lockout` to TRUE; downstream HeatingRequested + EnginePreheat commands are rejected while the tile is TRUE.

5. **Presence-aware pre-warm** — when the operator's phone reconnects to the LAN AND it's been >24h since the last warm-up, the automation starts the floor heat to the operator's preferred pre-warm setpoint (default 18 °C) so the cabin is comfortable when they arrive. The cross-reference is to the bluetooth-wifi-presence `connections/bluetooth-wifi-presence/` recipe's `binary_sensor.rc_presence_operator_phone_arrived`.

6. **Engine pre-heat schedule** — auto-start at 06:30 weekdays when mode is `Morning` AND ambient temp < 5 °C. The automation triggers `switch.rc_hvac_engine_preheat` for 30 min; the `sensor.rc_hvac_engine_preheat_runtime_min` tracks the daily runtime.

Frost-protection automation (the cross-reference to the upcoming happijac slice): if mode is `auto` AND engine preheat is off AND interior temp < 5 °C → enable gentle floor heating for frost protection (cross-references the upcoming happijac `connections/happijac/` recipe's `select.rc_bed_lift_mode` for the mode signal).

## §8 Troubleshooting

Eight troubleshooting entries:

1. **Floor heater not turning on** — check the relay polarity (`switch.heater_relay` shows `on` but the heater doesn't fire → relay coil voltage mismatch OR relay is wired backwards). Verify the relay's coil voltage matches the heater's control board (12 V is typical; some heaters are 24 V). Verify the relay is rated for the heater's load (15 A or 20 A typical for a 1500–2000 W heated floor at 120 V).

2. **Heater stuck on** — the relay has welded shut (mechanical relay contacts have welded due to over-current or inductive load switching). Replace the relay with one rated for the load + add a flyback diode if not already present. Solid-state relays are less prone to welding but have their own failure modes.

3. **Temperature probe reading -40 °C** — the probe is disconnected (DS18B20 reads -40 °C when the 1-Wire bus is shorted or open). Check the probe wiring + the ESPHome device's 1-Wire bus configuration. A reading of -40 °C for an extended period will block `climate.floor_heater` from operating (the `generic_thermostat:` integration refuses to turn on the heater when the target sensor reads below `min_temp`).

4. **Setpoint not sticking** — template race; ensure `keep_alive` is set in `generic_thermostat:`. Without `keep_alive`, the climate goes stale after a few minutes and stops issuing on/off commands to the relay. The operator will see the setpoint stick in HA but the relay never toggle. Add `keep_alive: { minutes: 3 }` to the `generic_thermostat:` block.

5. **Floor heater cycling rapidly** — `cold_tolerance` too tight (the climate turns on the heater when temp is 0.1 °C below setpoint and turns off when 0.1 °C above; with a slow-responding floor this causes rapid cycling). Increase `cold_tolerance` to 0.5 °C and `hot_tolerance` to 0.5 °C.

6. **Engine preheat switch toggles but engine doesn't actually warm** — the CAN bus gateway is not connected (for higher-end Webasto Thermo Top Evo / Eberspächer Hydronic S3 setups that use a CAN bus gateway). Check the gateway's CAN bus wiring + the gateway's HA integration status. The `binary_sensor.rc_hvac_engine_preheat_active` template will report `false` even though the switch is `on`, because the cabin temp isn't rising.

7. **Engine preheat brief but heater runtime tracker still incremented** — sensor debounce issue; the `utility_meter` integration counts the cumulative on-time of the switch in seconds, but if the switch flickers (due to a loose relay contact), the runtime will be over-counted. Add a `delay_on: 2` filter to the upstream switch entity to debounce.

8. **Low-voltage lockout stuck on after charging** — the Victron `sensor.rc_power_battery_soc` hasn't refreshed yet (the SOC tile updates every 30 s; after a charging cycle the SOC takes a few minutes to settle). Cross-check the Victron SOC directly in the Victron integration's UI; if it's > 20 %, force-refresh the `sensor.rc_power_battery_soc` entity via Developer Tools → States → Refresh.

9. **`generic_thermostat` `min_temp` clamp missing** — template render error; if `min_temp` is below the target sensor's actual reading range, the climate will throw a template render error when the setpoint goes outside the sensor's range. Set `min_temp` to 5 °C (the typical minimum for a floor heating element) and `max_temp` to 30 °C (the typical maximum for a comfortable floor).

## §9 Privacy

No telemetry. Everything is local. The temperature probes (DS18B20 1-Wire / Zigbee / Shelly H&T / vendor thermostat's internal sensor) are local 1-Wire / Zigbee / Wi-Fi, no cloud call home. The HA core `generic_thermostat` integration does not phone home. The climate-domain vendor integrations (Mysa / Shelly H&T / generic-Zigbee) MAY phone home for firmware updates — that's the operator's vendor choice; RoamCore does not add any cloud integration. The relay integrations (Shelly / Shelly Plus / Zooz / Aeotec) MAY phone home for firmware updates — same operator choice. The engine pre-heat relay (Shelly / ESPHome / CAN bus gateway) is local; the engine pre-heat hardware itself (Webasto / Espar / Eberspächer) is not networked.

The contract entities (`rc_hvac_*`) do not collect any operator data; they are pure local-state tiles that surface the operator's choice + the upstream sensor readings.

## §10 Promoting to tier-a

What would need to happen to promote this connection from tier-b to tier-a:

- A real heated-floor + relay + temperature probe + optional engine preheat bench on CI. The bench needs at least one Path A smart thermostat OR one Path B relay-driven heater + temperature probe + a Path C engine preheat simulator. The bench must wire all five safety interlock sources (Victron SOC + shore-connection, bluetooth-wifi-presence, RoamCore mode, interior temp probe, etc.) so the integration tests can assert each one flips to the expected state.

- A canonical RoamCore-owned `config_flow.py` that walks the operator through choosing Path A vs Path B vs Path C + declaring the relay pin / probe pin / optional engine preheat pin. The config_flow should also collect the operator's preferred pre-warm setpoint + the shore-power-aware clamp value + the mode-aware (Stealth / Sleep / Boost) throttling values.

- Integration tests that assert a setpoint change on `number.rc_hvac_floor_setpoint` triggers the right tile updates on `climate.rc_hvac_floor_thermostat` + the 3× state binary_sensors (`heating_active` / `maintaining` / `off`).

- Integration tests that assert the five safety interlocks all flip to the expected state when wired to canned fixture responses (low-voltage lockout when SOC < 20 %, shore-power-aware throttling when shore toggles, mode-aware lockouts when RoamCore mode toggles, presence-aware pre-warm when operator phone arrives, frost-protection automation when interior temp drops below 5 °C).

- Flip `tier_requirements` to include `working_config_flow` + `integration_test_passes` + `no_manual_yaml_required` + `safety_interlocks_hard_enforced_in_roamcore_code`.

Until those ship, this connection is tier-b even though the upstream `generic_thermostat` + climate-domain vendor integrations have their own GUI flows. The recipe is sound but we cannot claim one-tap automation.