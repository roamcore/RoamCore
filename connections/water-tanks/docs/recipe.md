# Water tanks — tier-b recipe connection

This is the full howto for the `connections/water-tanks/` tier-b recipe
connection. It walks through wiring fresh + grey tank telemetry + pump
runtime + leak detection + freeze-risk monitoring on the van (Path A —
ESPHome tank sensor node per tank + per-pump CT clamp + optional
DS18B20 temperature probe in tank bay + optional leak sensor on a
GPIO; the ESPHome YAML exposes `sensor.<node>_fresh_level_pct` +
`sensor.<node>_fresh_distance_cm` + `sensor.<node>_grey_level_pct` +
`sensor.<node>_grey_distance_cm` + optional
`binary_sensor.<node>_pump_running` + optional
`sensor.<node>_fresh_temperature_c` + optional
`binary_sensor.<node>_leak_detected`; Path B — generic resistive /
4–20 mA / voltage probe via a Shelly UNI ADC input + the HA `template:`
integration translates voltage to percentage via a per-tank calibration
curve; Path C — cloud-bridged level sensor (SeeLevel / Garnet SeeLevel
II 709-BTG / Mopeka Pro Check / Lippert) via the vendor's own HA core
or HACS integration), mapping the upstream entities into the 17
`rc_water_*` contract tiles, layering the five MANDATORY safety
interlocks (leak detected / freeze risk / fresh empty / pump running
too long / mode-aware lockouts) + the §8 automations, and promoting the
connection to tier-a when the bench fixture lands.

## §1 What is Water tanks in RoamCore?

Water tanks — fresh + grey water telemetry + pump runtime + leak
detection + freeze-risk monitoring for vans — is positioned in
RoamCore as:

- A **vendor-neutral** water contract. The contract talks to whatever
  water integration the operator already runs (Path A — ESPHome tank
  sensor node per tank; Path B — Shelly UNI + ADC probe per tank;
  Path C — cloud-bridged level sensor via the vendor's own HA core or
  HACS integration), not to any specific vendor's library.

- A **single "is the water system within safe bounds?" aggregate**
  that surfaces fresh level + grey level + pump running + leak
  detected + freeze risk into one dashboard tile. The
  `binary_sensor.rc_water_fresh_low_warning` +
  `binary_sensor.rc_water_grey_full_warning` +
  `binary_sensor.rc_water_fresh_empty_warning` tiles are the
  day-1 affordances; together with
  `binary_sensor.rc_water_leak_detected` +
  `binary_sensor.rc_water_freeze_risk` +
  `binary_sensor.rc_water_pump_running_too_long`, they give the
  operator a complete view of "is the water system within safe
  bounds?" at a glance.

- A **safety-first** system. The
  `binary_sensor.rc_water_leak_detected` tile fires when ANY leak
  sensor (under-sink / pump-area / under-van) reports water +
  immediately stops the pump + sends a HIGH-PRIORITY push
  notification (leaks in a van ruin everything — water +
  electronics + cabinetry + insulation all die together; the
  operator MUST address the leak the moment it's detected). The
  `binary_sensor.rc_water_freeze_risk` tile fires when
  `sensor.rc_water_fresh_temperature_c` < 2 °C + cross-references
  the heated-floors + hvac-basics connections' frost-warning path
  (frozen fresh water tank + frozen pipes = cracked tank + burst
  pipes + no drinking water + no shower water + the operator's
  whole water system is offline until the van thaws).

- A **battery-aware** system. The water pump can pull 5–10 A
  sustained when running; below 30 % SOC that's enough to drain
  the battery bank over a single overnight pump cycle. The
  `binary_sensor.rc_water_pump_running_too_long` tile fires when
  the pump has been running continuously > 10 min (typical usage:
  a shower is 5–8 min; a dish-wash is 1–2 min; anything > 10 min is
  a stuck-open faucet or a stuck-relay) + automatically stops the
  pump (a stuck pump will drain the fresh tank onto the floor +
  drain the battery bank — both are van-killers). The cross-
  reference to the Victron connection is the same pattern that the
  heated-floors + hvac-basics + happijac connections use for their
  low-voltage lockout interlocks.

- A **mode-aware** system. The `select.rc_water_mode` select
  controls the water monitoring mode: `auto` (all warnings
  enabled), `stealth_only` (only leak / freeze / empty warnings;
  mute the daytime-noise warnings like fresh_low + grey_full),
  `silent` (no warnings at all — reserved for service work; the
  operator still gets leak / freeze / empty from the van-killer
  categories), `disabled` (no monitoring at all — reserved for
  when the operator has intentionally drained the tanks for
  winterization). The mode-aware lockouts (Stealth / Sleep /
  Boost) layer on top: Stealth silent hours auto-mute the
  fresh_low + grey_full warnings; Sleep mode additionally drops
  the operator-tunable warning thresholds by 10 %; Boost disables
  ALL the mode-aware lockouts for service work / pre-trip packing.

- A **multi-mode-aware** system. The dashboard tile
  `select.rc_water_mode` exposes the operator's local override
  (`auto` / `stealth_only` / `silent` / `disabled`) on top of
  the mode-aware defaults from `select.rc_mode` (the
  mode/automation-builder connection's mode select — away /
  stealth / sleep / boost).

## §2 Prerequisites

Path A — ESPHome tank sensor node (recommended for ESPHome-friendly
installs):

- One ESP32 per node (e.g. ESP32-DevKitC-V4 / ESP32-S3-DevKitC-1 / Wemos
  D1 Mini ESP32) flashed with ESPHome firmware.
- One ultrasonic probe per tank (JSNSR04T waterproof 2.5 m / HC-SR04
  waterproof 1 m) wired into GPIO — fresh tank on GPIO 13 (TRIG) +
  GPIO 12 (ECHO); grey tank on GPIO 27 (TRIG) + GPIO 26 (ECHO). The
  probe is mounted at the top of the tank pointing down; the
  `distance_cm` reading is the distance from the probe to the water
  surface (smaller = more full).
- One CT clamp on the 12 V water pump wire (e.g. SCT-013-030 30 A / 1 V
  output) wired into GPIO 34 (ADC1_CH6) — the CT clamp senses the
  current draw of the pump; the ESPHome ADC + a `binary_sensor.pump_
  running` template flags TRUE when the current draw > 0.5 A for >1s.
- Optional DS18B20 temperature probe (in the tank bay) wired into GPIO
  4 with a 4.7 kΩ pull-up resistor to 3.3 V.
- Optional leak sensor probe (e.g. a water-level-detection sensor with
  exposed contacts) wired into GPIO 14 with a 10 kΩ pull-up resistor
  to 3.3 V.
- The upstream `esphome` integration configured in HA (GUI flow since
  2023.x) — ESPHome auto-discovers ESP32 nodes on the LAN via mDNS.

Path B — Generic resistive / 4–20 mA / voltage probe via Shelly UNI ADC
(no ESPHome):

- One Shelly UNI per tank (Shelly UNI is a small DIN-rail-mountable
  module with 2× ADC inputs + 2× relay outputs + 1-Wire + dry contacts).
  Powered via 12 V supply (the van's 12 V distribution).
- One probe per tank — resistive (0–10 kΩ) / 4–20 mA current loop /
  0–10 V voltage — wired into the Shelly UNI's ADC input.
- The upstream `shelly` integration configured in HA (GUI flow since
  2022.x) — Shelly auto-discovers Shelly UNI devices on the LAN via
  mDNS.
- The HA `template:` integration (HA core, no GUI flow needed —
  operators configure the template YAML manually).

Path C — Cloud-bridged level sensor (SeeLevel / Garnet SeeLevel II
709-BTG / Mopeka Pro Check / Lippert):

- The vendor sensor + the vendor gateway (e.g. Mopeka Pro Check needs
  the Mopeka Bluetooth gateway; SeeLevel needs the SeeLevel gateway;
  Lippert needs the Lippert OneControl app).
- The vendor integration in HA core or HACS (GUI flow since 2022.x /
  2023.x depending on the vendor). For SeeLevel: the `see_level` HACS
  integration. For Mopeka: the `mopeka_pro_check` HACS integration. For
  Garnet: the `serial` integration with a USB-to-serial adapter. For
  Lippert: the `lippert_onecontrol` HACS integration.

Common to all three paths:

- The HA `template:` integration (HA core) — for the contract tile
  synthesis + the derived metrics (`fresh_days_remaining`,
  `pump_runtime_min_last_24h`).
- The HA `utility_meter:` integration (HA core) — for the
  `sensor.rc_water_pump_runtime_min_last_24h` daily runtime tracker.
- The HA `input_number:` integration (HA core, GUI flow since 2022.x) —
  for the operator-tunable `number.rc_water_fresh_tank_size_l` +
  `number.rc_water_grey_tank_size_l` tiles.
- The HA `input_select:` integration (HA core, GUI flow since 2022.x) —
  for the operator-tunable `select.rc_water_mode` tile.
- The HA `mqtt:` integration (HA core, GUI flow since 2022.x) — only
  needed for Path A if the operator wires the ESPHome + MQTT bridge
  variant (not common; ESPHome's native HA integration is preferred).

## §3 Path A — ESPHome tank sensor node (recommended for ESPHome-friendly installs)

The full ESPHome YAML for an ESP32 with 2× HC-SR04 waterproof
ultrasonic probes (one per tank) + a CT clamp on the 12 V pump wire +
a DS18B20 temperature probe in the tank bay + (optional) a leak
sensor probe wired into a GPIO. The ESPHome YAML exposes:

- `sensor.<node>_fresh_level_pct` — fresh tank level (0–100 %)
- `sensor.<node>_fresh_distance_cm` — fresh tank distance from probe
  to water surface (cm)
- `sensor.<node>_grey_level_pct` — grey tank level (0–100 %)
- `sensor.<node>_grey_distance_cm` — grey tank distance from probe to
  water surface (cm)
- `binary_sensor.<node>_pump_running` — TRUE when the 12 V pump is
  actively running
- `sensor.<node>_fresh_temperature_c` — tank bay temperature probe (°C)
- `binary_sensor.<node>_leak_detected` — TRUE when the leak sensor
  reports water

The full ESPHome YAML:

```yaml
esphome:
  name: van-water-tanks
  platform: ESP32
  board: esp32-devkitc-v4

# Wireless + logger + web + api config omitted for brevity (see
# ESPHome's standard ESP32 base config).

# Ultrasonic probes — fresh tank on GPIO 13/12; grey tank on GPIO 27/26.
ultrasonic:
  - name: "Fresh Tank Distance"
    trigger_pin: GPIO13
    echo_pin: GPIO12
    update_interval: 30s
    filters:
      - lambda: |-
          if (isnan(x)) return {};
          // Tank is 30 cm tall; probe mounted 5 cm above tank top.
          // distance_cm = distance from probe to water surface.
          // level_pct = ((max_distance - distance) / (max_distance -
          // min_distance)) * 100
          float max_distance = 35.0;  // empty: 35 cm from probe to bottom
          float min_distance = 5.0;   // full: 5 cm from probe to water surface
          float clamped = std::max(min_distance, std::min(max_distance, x));
          return ((max_distance - clamped) / (max_distance - min_distance)) * 100.0;
  - name: "Grey Tank Distance"
    trigger_pin: GPIO27
    echo_pin: GPIO26
    update_interval: 30s
    filters:
      - lambda: |-
          if (isnan(x)) return {};
          float max_distance = 30.0;
          float min_distance = 4.0;
          float clamped = std::max(min_distance, std::min(max_distance, x));
          return ((max_distance - clamped) / (max_distance - min_distance)) * 100.0;

# Distance sensors for the raw cm readings.
sensor:
  - platform: ultrasonic
    trigger_pin: GPIO13
    echo_pin: GPIO12
    name: "Fresh Tank Distance (cm)"
    update_interval: 30s
  - platform: ultrasonic
    trigger_pin: GPIO27
    echo_pin: GPIO26
    name: "Grey Tank Distance (cm)"
    update_interval: 30s

# CT clamp on the 12 V water pump wire.
  - platform: adc
    pin: GPIO34
    name: "Pump Current (A)"
    attenuation: auto
    update_interval: 5s
    filters:
      - multiply: 30.0  # SCT-013-030 is 30 A : 1 V

# DS18B20 temperature probe in tank bay.
  - platform: dallas_temp
    address: 0x1234567890ABCDEF  # your probe's address
    name: "Tank Bay Temperature (°C)"
    update_interval: 60s

binary_sensor:
  - platform: template
    name: "Pump Running"
    lambda: |-
      if (id(pump_current).state > 0.5) {
        return true;
      } else {
        return false;
      }

  - platform: gpio
    pin:
      number: GPIO14
      mode: INPUT_PULLUP
    name: "Leak Detected"
    filters:
      - delayed_off: 500ms  # debounce
```

The full wiring of the upstream entities into the 17 contract tiles
is via HA core `template:` — see §6 below.

## §4 Path B — Generic resistive / 4–20 mA / voltage probe via Shelly UNI ADC (no ESPHome)

The Shelly UNI wiring (12 V supply + ADC inputs):

1. Power the Shelly UNI via the van's 12 V distribution (the Shelly
   UNI accepts 12 V DC directly on its `+12V` + `GND` terminals).
2. Wire the resistive / 4–20 mA / voltage probe to the Shelly UNI's
   ADC input (`A1` for fresh tank; `A2` for grey tank). The probe's
   +V terminal connects to the Shelly UNI's `+12V` (for active
   probes) or to an external 5 V regulator (for low-voltage probes);
   the probe's signal terminal connects to `A1` / `A2`; the
   probe's GND terminal connects to the Shelly UNI's `GND`.
3. Configure the Shelly UNI's ADC mode via the Shelly web UI (mDNS
   auto-discovery on the LAN): set `A1` to `Voltage` for a 0–10 V
   probe; set `A1` to `Current` for a 4–20 mA probe; set `A1` to
   `Resistance` for a resistive probe. The Shelly integration in HA
   exposes `sensor.shelly_uni_a1_voltage` (or `_current` or
   `_resistance`).

The HA `template:` sensor wiring the raw voltage / current /
resistance to a percentage via a per-tank calibration curve:

```yaml
template:
  - sensor:
      - name: "Fresh Tank Level (pct)"
        unit_of_measurement: "%"
        state: >-
          {{
            (
              (states('sensor.shelly_uni_a1_voltage') | float(0) - 0.5) /
              (4.5 - 0.5)
            ) * 100 | round(1)
          }}
        attributes:
          calibration_empty_v: 0.5   # operator: empty tank voltage
          calibration_full_v: 4.5    # operator: full tank voltage
      - name: "Grey Tank Level (pct)"
        unit_of_measurement: "%"
        state: >-
          {{
            (
              (states('sensor.shelly_uni_a2_voltage') | float(0) - 0.6) /
              (4.6 - 0.6)
            ) * 100 | round(1)
          }}
        attributes:
          calibration_empty_v: 0.6
          calibration_full_v: 4.6
```

The operator MUST measure the empty-voltage (probe in an empty tank)
and the full-voltage (probe in a full tank) and configure the
`calibration_empty_v` + `calibration_full_v` attributes. The
`number.rc_water_fresh_tank_size_l` + `number.rc_water_grey_tank_size_l`
tiles cover the operator-tunable tank sizes (default 80 L for fresh,
default 60 L for grey).

## §5 Path C — Cloud-bridged level sensor (SeeLevel / Garnet / Mopeka / Lippert)

Path C is the most vendor-varied of the three paths — each vendor has
its own integration setup. The recipe walks through the four most
common vendors:

**SeeLevel** (SeeLevel International / Garnet SeeLevel II 709-BTG):
- The SeeLevel II 709-BTG is a 3-tank sensor with built-in Bluetooth
  LE. Pair the sensor with the SeeLevel gateway (a small Bluetooth
  receiver that bridges to the operator's phone / cloud).
- Install the `see_level` HACS integration (HACS → Integrations → Add
  → search "see_level"). The integration exposes
  `sensor.see_level_fresh_pct` + `sensor.see_level_grey_pct` +
  `sensor.see_level_black_pct` (RoamCore uses only the fresh + grey
  tiles).
- Map `sensor.see_level_fresh_pct` → `sensor.rc_water_fresh_level_pct`
  + `sensor.see_level_grey_pct` → `sensor.rc_water_grey_level_pct` via
  HA core `template:` (the vendor integration exposes percent
  directly; no calibration curve needed).

**Mopeka Pro Check** (Mopeka / Lippert LippertOne):
- The Mopeka Pro Check is a Bluetooth LE tank sensor that mounts on
  the bottom of an LPG / fresh / grey tank. Pair the sensor with the
  Mopeka gateway (a small Bluetooth receiver).
- Install the `mopeka_pro_check` HACS integration. The integration
  exposes `sensor.mopeka_pro_check_fresh_level_pct` (and similar for
  grey). Map via HA core `template:`.

**Garnet SeeLevel II 709-BTG** (Garnet Technologies):
- The Garnet SeeLevel II 709-BTG is a wired 3-tank sensor that
  outputs a resistance per tank level. Wire it to a USB-to-serial
  adapter (e.g. FTDI FT232R) → the HA `serial` integration.
- The `serial` integration exposes `sensor.garnet_fresh_level` +
  `sensor.garnet_grey_level` (raw resistance values; the operator
  MUST calibrate the resistance-to-percentage curve in the template).
- Map the resistance → percentage via HA core `template:` (similar
  to Path B's Shelly UNI pattern).

**Lippert OneControl**:
- The Lippert OneControl system is a Bluetooth LE / CAN-bus system
  that bundles several subsystems (tank level + slide-out + awning +
  lighting). Pair the OneControl gateway with HA via the
  `lippert_onecontrol` HACS integration. Map the tank-level entities
  via HA core `template:`.

The RoamCore contract mapping for each Path C vendor is identical:
map the vendor's `*_level_pct` entity to `sensor.rc_water_fresh_level_pct`
+ `sensor.rc_water_grey_level_pct` via HA core `template:`.

## §6 RoamCore contract entities

The 17 `rc_water_*` contract tiles + how the upstream sensor template
exposes them + translation helpers needed for the derived metrics:

- `sensor.rc_water_fresh_level_pct` — fresh tank level (0–100 %).
  Path A: maps directly from `sensor.<node>_fresh_level_pct`. Path B:
  maps from the calibrated `sensor.fresh_tank_level_pct` template.
  Path C: maps from the vendor's `*_fresh_level_pct` entity.
- `sensor.rc_water_fresh_level_l` — fresh tank volume in litres
  (`tank_size_l × level_pct / 100`). Derived via HA `template:`.
- `sensor.rc_water_fresh_days_remaining` — derived:
  `tank_size_l / avg_daily_usage_l`; clamps 0–30. The operator
  configures `avg_daily_usage_l` via `input_number.rc_water_avg_
  daily_usage_l` (default 20 L/day; configurable 5–100 L/day).
- `sensor.rc_water_grey_level_pct` — grey tank level (0–100 %).
  Same pattern as fresh.
- `sensor.rc_water_grey_level_l` — grey tank volume in litres
  (`tank_size_l × level_pct / 100`). Derived via HA `template:`.
- `binary_sensor.rc_water_grey_full_warning` — TRUE when
  `grey_level_pct` > 80 %.
- `binary_sensor.rc_water_fresh_low_warning` — TRUE when
  `fresh_level_pct` < 20 %.
- `binary_sensor.rc_water_fresh_empty_warning` — TRUE when
  `fresh_level_pct` < 5 %.
- `binary_sensor.rc_water_pump_running` — TRUE when the 12 V water
  pump is actively running. Path A: maps from
  `binary_sensor.<node>_pump_running`. Path B: derived from the
  Shelly UNI's relay state (the relay that powers the pump is on).
  Path C: most cloud-bridged sensors don't expose pump running —
  the operator wires a CT clamp on the pump wire as a separate
  Path A / Path B step.
- `sensor.rc_water_pump_runtime_min_last_24h` — derived from
  `binary_sensor.rc_water_pump_running` edge-counting. Use the HA
  `utility_meter:` integration with a 24h cycle + a `value_template:
  '{{ states("binary_sensor.rc_water_pump_running") | int }}'`
  pattern.
- `binary_sensor.rc_water_pump_running_too_long` — TRUE when pump
  has been running continuously > 10 min. Use HA `template:`
  binary_sensor with a `for: '00:10:00'` trigger.
- `binary_sensor.rc_water_leak_detected` — TRUE when ANY leak sensor
  (under-sink / pump-area / under-van) reports water. Path A: maps
  from `binary_sensor.<node>_leak_detected`. Path B + Path C: the
  operator wires a separate leak sensor (often a Zigbee / Z-Wave
  water leak sensor via the smoke-co-gas-sensors connection's
  §7.4 pattern).
- `binary_sensor.rc_water_freeze_risk` — TRUE when
  `sensor.rc_water_fresh_temperature_c` < 2 °C.
- `sensor.rc_water_fresh_temperature_c` — tank bay temperature probe.
- `number.rc_water_fresh_tank_size_l` — operator-configured fresh
  tank size (default 80 L, configurable 20–300 L).
- `number.rc_water_grey_tank_size_l` — operator-configured grey tank
  size (default 60 L, configurable 20–200 L).
- `select.rc_water_mode` — operator-tunable mode: `auto` (all warnings
  enabled), `stealth_only` (only leak / freeze / empty warnings),
  `silent` (no warnings — for service), `disabled` (no monitoring).

## §7 Safety interlocks (MANDATORY before first use)

Five MANDATORY safety interlocks (operator MUST wire each one before
first use):

1. **Leak detected** — when ANY leak sensor reports water, fire
   `binary_sensor.rc_water_leak_detected` TRUE + immediately stop
   the pump (the pump could be the cause of the leak or could keep
   pumping water onto the floor / into the van's electrical bay) +
   send a HIGH-PRIORITY push notification (leaks in a van ruin
   everything — water + electronics + cabinetry + insulation all
   die together; the operator MUST address the leak the moment
   it's detected). The cross-reference to the smoke-co-gas-sensors
   `connections/smoke-co-gas-sensors/` connection's §7.4 pattern
   (loud siren + phone notification on any alarm) is the same
   pattern this connection uses for the leak detected push
   notification.

2. **Freeze risk** — when `sensor.rc_water_fresh_temperature_c` <
   2 °C, fire `binary_sensor.rc_water_freeze_risk` TRUE + cross-
   reference the heated-floors `connections/heated-floors/` recipe
   §7.5 frost-protection automation + the hvac-basics
   `connections/hvac-basics/` recipe §7.1 frost-warning. The
   heated-floors frost-protection engages gentle floor heating
   when the interior temp is < 5 °C; the hvac-basics frost-
   warning keeps the cabin thermostat > 5 °C; the water-tanks
   freeze_risk tile is the third pillar of the cold-weather
   safety story (frozen fresh water tank + frozen pipes = cracked
   tank + burst pipes + no drinking water + no shower water).

3. **Fresh empty warning** — when `sensor.rc_water_fresh_level_pct`
   < 5 %, fire `binary_sensor.rc_water_fresh_empty_warning` TRUE
   + surface prominently on the dashboard (the operator MUST
   refill the fresh tank before the next shower / dish wash /
   toilet flush). This is the "ran out of water unexpectedly"
   tile that the legacy tier-c spec promised but never delivered.

4. **Pump running too long** — when the pump has been running
   continuously > 10 min (typical usage: a shower is 5–8 min; a
   dish-wash is 1–2 min; anything > 10 min is a stuck-open faucet
   or a stuck-relay), fire
   `binary_sensor.rc_water_pump_running_too_long` TRUE +
   automatically stop the pump (a stuck pump will drain the fresh
   tank onto the floor + drain the battery bank — both are van-
   killers). The cross-reference to the Victron
   `connections/victron/` connection's `sensor.rc_power_battery_soc`
   + `binary_sensor.rc_power_shore_connected` is the same pattern
   that the heated-floors + hvac-basics + happijac connections use
   for their low-voltage lockout interlocks.

5. **Mode-aware lockouts (Stealth / Sleep / Boost)** —
   - Stealth silent hours auto-mute warnings: when
     `select.rc_mode == stealth`, mute the
     `binary_sensor.rc_water_grey_full_warning` +
     `binary_sensor.rc_water_fresh_low_warning` warnings
     (daytime-noise warnings — the operator is asleep / not
     interacting with the van). The
     `binary_sensor.rc_water_leak_detected` +
     `binary_sensor.rc_water_freeze_risk` +
     `binary_sensor.rc_water_fresh_empty_warning` warnings
     ALWAYS fire (van-life-or-death warnings — bypass mode-
     aware suppression).
   - Sleep mode silent: when `select.rc_mode == sleep`,
     additionally mute ALL non-van-life-or-death warnings +
     drop the operator-tunable warning thresholds by 10 %.
   - Boost disable-mode-aware-lockouts: when
     `select.rc_mode == boost`, disable ALL the above mode-
     aware lockouts so the operator has full monitoring
     during service work / pre-trip packing.
   - The dashboard tile `select.rc_water_mode` exposes the
     operator's local override (`auto` / `stealth_only` /
     `silent` / `disabled`) on top of the mode-aware defaults.

## §8 Automations

Six MANDATORY automations:

1. **Auto-push on fresh low** — when
   `binary_sensor.rc_water_fresh_low_warning` transitions to
   TRUE, send a push notification (the operator needs to plan a
   refill stop within the next 12 hours). The cross-reference to
   the bluetooth-wifi-presence `connections/bluetooth-wifi-
   presence/` connection's `binary_sensor.rc_presence_anyone_
   home` is for the "operator is in the van" TTS escalation.

2. **Auto-push on grey full** — when
   `binary_sensor.rc_water_grey_full_warning` transitions to
   TRUE, send a push notification (the operator needs to plan a
   dump-station stop within the next 12 hours). Same
   bluetooth-wifi-presence cross-reference as §8.1.

3. **Auto-stop pump when pump running too long** — when
   `binary_sensor.rc_water_pump_running_too_long` transitions
   to TRUE, send a `switch.turn_off` to the pump's relay (this
   stops the pump from continuing to drain the tank + the
   battery) + send a push notification (the operator needs to
   investigate the stuck-open faucet / stuck-relay).

4. **Auto-push critical on leak detected** — when
   `binary_sensor.rc_water_leak_detected` transitions to TRUE,
   send a HIGH-PRIORITY push notification + trigger a loud siren
   (the operator MUST address the leak the moment it's
   detected). The cross-reference to the smoke-co-gas-sensors
   `connections/smoke-co-gas-sensors/` recipe's §7.1 "loud siren
   + phone notification" is the same pattern. The cross-
   reference to the deadbolts `connections/deadbolts/` recipe's
   §7.x emergency-egress unlock is for the "operator must be
   able to get OUT of the van even if water is pooling near
   the door" scenario.

5. **Auto-engage heated-floors on freeze risk** — when
   `binary_sensor.rc_water_freeze_risk` transitions to TRUE AND
   `sensor.rc_power_battery_soc` > 50 %, fire a
   `select.select_option` to `select.rc_hvac_floor_mode` =
   `auto` (the floor heating engages to keep the interior temp
   > 5 °C, which keeps the tank bay > 2 °C, which keeps the
   fresh tank + pipes from freezing). The cross-reference to
   the heated-floors `connections/heated-floors/` recipe's
   §7.5 frost-protection automation is the same pattern. The
   SOC > 50 % gate prevents the freeze-protection automation
   from draining the battery bank when off-grid.

6. **Mode-aware scheduling** — when `select.rc_water_mode ==
   stealth_only`, mute `binary_sensor.rc_water_grey_full_
   warning` + `binary_sensor.rc_water_fresh_low_warning`. When
   `select.rc_water_mode == silent`, mute ALL warnings except
   `binary_sensor.rc_water_leak_detected` +
   `binary_sensor.rc_water_freeze_risk` +
   `binary_sensor.rc_water_fresh_empty_warning`. When
   `select.rc_water_mode == disabled`, disable ALL monitoring
   (the operator has intentionally drained the tanks). The
   `auto` mode enables all warnings.

The full automation YAML for each is in the recipe
`homeassistant/automations/rc_water_*.yaml` files (operator wires
these manually until tier-a promotion lands).

## §9 Troubleshooting

Eight troubleshooting entries:

1. **Sensor reading 0 % when tank is full** — wiring fault or
   empty-voltage calibration wrong. For Path A: check the
   ultrasonic probe wiring (TRIG + ECHO on the right GPIOs;
   the probe must be mounted at the TOP of the tank pointing
   DOWN; the probe must NOT be submerged). For Path B: the
   `calibration_empty_v` attribute MUST match the actual
   empty-tank voltage (typically 0.5 V for a 0–5 V probe).
   Solution: measure the probe voltage with the tank empty +
   update `calibration_empty_v` in the template sensor.

2. **Sensor reading 100 % when tank is empty** — full-voltage
   calibration wrong. For Path A: check the ultrasonic probe
   wiring (TRIG + ECHO reversed; the probe's ECHO wire must be
   on the GPIO listed in the YAML). For Path B: the
   `calibration_full_v` attribute MUST match the actual full-
   tank voltage (typically 4.5 V for a 0–5 V probe). Solution:
   measure the probe voltage with the tank full + update
   `calibration_full_v` in the template sensor.

3. **Pump running not toggling** — CT clamp orientation wrong or
   sense resistor too small. For Path A: the CT clamp must be
   CLAMPED AROUND THE PUMP WIRE with the arrow pointing IN THE
   DIRECTION OF CURRENT FLOW (from +12 V battery to the pump).
   If the CT clamp is reversed, the current reading will be
   negative (or zero). Solution: flip the CT clamp on the wire.
   For Path B: the Shelly UNI's relay state must be wired to the
   pump's +12 V line (not the pump's ground). Solution: re-wire
   the Shelly UNI's relay in series with the pump's +12 V.

4. **Leak sensor always-on** — probe wet + needs drying + salt
   bridge on the contacts. The leak sensor's contacts form a
   salt bridge when they get wet + dry repeatedly. Solution:
   dry the probe thoroughly + clean the contacts with
   isopropyl alcohol + check the pull-up resistor is 10 kΩ
   (not 1 kΩ, which can cause false positives from noise).

5. **ESPHome device offline** — check Wi-Fi + USB-C power. For
   Path A: the ESP32 must have stable 5 V via USB-C (not the
   van's 12 V distribution without a regulator). Solution: check
   the USB-C cable + the Wi-Fi signal strength. For Path B: the
   Shelly UNI must have stable 12 V supply. Solution: check the
   12 V fuse + the Shelly UNI's status LED.

6. **Shelly UNI not discovered** — mDNS / IGMP snooping on the
   LAN switch. For Path B: the Shelly UNI uses mDNS for
   auto-discovery; some managed switches have IGMP snooping
   enabled which blocks mDNS multicast. Solution: enable mDNS
   reflector on the LAN switch OR manually add the Shelly UNI
   via the Shelly integration's "Add device by IP" flow.

7. **Temperature reading -40 °C** — DS18B20 wiring fault. For
   Path A: the DS18B20 requires a 4.7 kΩ pull-up resistor
   between DATA and +3.3 V. Solution: check the pull-up
   resistor is present + the DATA wire is on GPIO 4 + the
   GND wire is connected. A reading of -40 °C typically
   indicates an open circuit (the pull-up is missing).

8. **Fresh days remaining negative** — calibration drift or
   tank-size misconfigured. The
   `sensor.rc_water_fresh_days_remaining` formula is
   `tank_size_l / avg_daily_usage_l`. If the formula returns
   negative, either `tank_size_l` is 0 (operator mis-configured
   the tank size) or `avg_daily_usage_l` is undefined (operator
   didn't set the `input_number.rc_water_avg_daily_usage_l`
   helper). Solution: set `number.rc_water_fresh_tank_size_l` to
   the actual tank size (default 80 L) + set
   `input_number.rc_water_avg_daily_usage_l` to the operator's
   actual daily usage (default 20 L/day).

## §10 Privacy

No telemetry. Everything is local. The esphome / shelly / template
integrations are local; no cloud call home.

Vendor integrations (SeeLevel / Mopeka / Lippert) MAY phone home to
the vendor's cloud — that's the operator's vendor choice; RoamCore
does not add any cloud integration. The contract entities (`rc_water_*`)
do not collect any operator data; they are pure local-state tiles that
surface the operator's choice + the upstream entity state.

The push notification for the leak detected + freeze risk + pump
running too long warnings uses the operator's existing HA Core push
notification channel — that's the operator's choice; RoamCore does
not add any push notification channel. The bluetooth-wifi-presence
cross-reference for the leak detected push notification escalation
uses the operator's existing presence detection — no additional
tracking is added.

The water sensors produce no telemetry beyond level + pump runtime
+ temperature. The leak sensors are local GPIO inputs (Path A) or
Zigbee / Z-Wave sensors (Path B / C) — no telemetry is sent to any
cloud. The pump running CT clamp (Path A) is local — no telemetry
is sent to any cloud.

## §11 Promoting to tier-a

What would need to happen to promote this connection from tier-b
to tier-a:

- A real water tank bench on the CI rig: a fresh tank + a grey
  tank + a 12 V water pump + a leak sensor + a temperature probe
  + an ESP32 + an ultrasonic probe + a CT clamp + optionally a
  Shelly UNI, all wired together in a controlled environment.
- A canonical RoamCore-owned `config_flow.py` that walks the
  operator through choosing Path A vs Path B vs Path C + declaring
  the tank sizes + (for Path A) the GPIO pins + (for Path B) the
  calibration curve (empty-voltage + full-voltage) + (for Path C)
  the vendor integration.
- Integration tests that assert a 0 % → 100 % level change
  triggers the right `sensor.rc_water_fresh_level_pct` +
  `sensor.rc_water_fresh_level_l` updates + the
  `binary_sensor.rc_water_fresh_low_warning` /
  `binary_sensor.rc_water_fresh_empty_warning` transitions.
- Integration tests that assert the §7.1 leak detected
  automation stops the pump + sends a high-priority push when
  the leak sensor is triggered.
- Integration tests that assert the §7.2 freeze risk automation
  engages the heated-floors connection's frost-protection
  automation when `sensor.rc_water_fresh_temperature_c` < 2 °C.
- Integration tests that assert the §7.4 pump running too long
  automation stops the pump when the pump has been running
  continuously > 10 min.
- Flip `tier_requirements` to include `working_config_flow` +
  `integration_test_passes` + `no_manual_yaml_required` +
  `safety_automations_hard_enforced_in_roamcore_code`.

Until those ship, this connection is tier-b even though the
upstream esphome / shelly / template integrations have their
own GUI flows. The recipe is sound but we cannot claim one-tap
automation.