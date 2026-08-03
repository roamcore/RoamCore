# HVAC basics — tier-b recipe connection

This is the full howto for the `connections/hvac-basics/` tier-b recipe
connection. It walks through wiring cabin heating/cooling on the van
(Path A — generic thermostat (any `climate.*` entity from HA core
integrations like `generic_thermostat`, `ecobee`, `nest`, `mitsubishi`,
`daikin`, etc.); Path B — diesel heater (Webasto / Eberspächer /
Chinese diesel / Vevor / Chinese planer-style) via the upstream
`esphome` + `binary_sensor` + `switch` recipe, or the `mqtt`
integration when the heater has an ESPHome-MQTT bridge; Path C —
rooftop AC (Furrion / Dometic / MaxxAir / Coleman) via IR-bridge
(Broadlink / MQTT-IR-Hub) + the upstream `switch` / `fan` / `select`
integration, or directly via the AC's own HA integration if it has
one; Path D — cabin ventilation (cabin fan / MaxxAir / Fan-Tastic Vent
/ roof-vent switches) via the HA core `fan` + `switch` + `select`
integration), mapping the upstream entities into the 11 `rc_hvac_*`
contract tiles, layering the four MANDATORY safety interlocks (frost
warning / over-temp warning / low-voltage lockout / mode-aware
lockouts) + the §8 automations, and promoting the connection to tier-a
when the bench fixture lands.

## §1 What is HVAC basics in RoamCore?

HVAC basics — cabin heating/cooling foundations for vans — is the
**umbrella** for thermostat + diesel heater + rooftop AC + cabin
ventilation control. It is positioned in RoamCore as:

- A **vendor-neutral** climate contract. The contract talks to whatever
  climate integration the operator already runs (Path A — generic
  thermostat via generic_thermostat / ecobee / nest / mitsubishi /
  daikin; Path B — diesel heater via esphome or mqtt; Path C —
  rooftop AC via broadlink IR-bridge or native vendor integration;
  Path D — cabin ventilation via HA core fan), not to any specific
  vendor's library.

- A **single "any HVAC device active?" aggregate** that surfaces
  heater + AC + fan + thermostat activity into one dashboard tile.
  The `binary_sensor.rc_hvac_heater_active` + `binary_sensor.rc_hvac_
  ac_active` tiles are the day-1 affordances; together with
  `binary_sensor.rc_hvac_frost_warning` + `binary_sensor.rc_hvac_
  over_temp_warning`, they give the operator a complete view of
  "is the cabin climate within safe bounds?" at a glance.

- A **safety-first** system. The `binary_sensor.rc_hvac_frost_warning`
  tile fires when `sensor.rc_hvac_outdoor_temperature` < 2 °C AND
  forces the cabin thermostat (`climate.rc_hvac_cabin_thermostat`)
  to maintain > 5 °C (the cabin MUST not drop below 5 °C — frozen
  pipes / condensation / battery damage below 0 °C). The
  `binary_sensor.rc_hvac_over_temp_warning` tile fires when
  `sensor.rc_hvac_cabin_temperature` > 35 °C + auto-turns on the
  AC + opens the cabin fan + sends a push notification (the
  operator + pets + electronics must not cook). The cross-reference
  to the bluetooth-wifi-presence connection is for the "pets left in
  van" escalation: when over-temp fires AND
  `binary_sensor.rc_presence_anyone_home` is FALSE, the alert
  escalates to high-priority + the dashboard highlights the
  over-temp tile in red.

- A **battery-aware** system. The diesel heater + rooftop AC
  together can pull 10–30 A sustained; below 30 % SOC that's
  enough to brown out the battery bank. The §7.3 low-voltage
  lockout (cross-reference to `sensor.rc_power_battery_soc` from
  the Victron `connections/victron/` connection) disables the
  diesel heater + AC when SOC < 30 % UNLESS shore power is
  connected (`binary_sensor.rc_power_shore_connected` TRUE).
  The operator can still manually turn on the cabin fan (Path D,
  < 1 A) in low-voltage mode.

- A **mode-aware** system. The `select.rc_hvac_mode` select
  controls the HVAC mode: `auto` (full auto-climate; heater / AC
  / fan based on the cabin thermostat), `heating` (heater only;
  AC off), `cooling` (AC only; heater off), `ventilation`
  (fan only; heater + AC off), `disabled` (reserved for service
  work; the operator can still manually control via the dashboard
  tiles). The mode-aware lockouts (Stealth / Sleep / Boost) layer
  on top: Stealth silent hours auto-lower the fan to `low`; Sleep
  mode turns the fan off + drops the heater/AC setpoints by 2 °C
  for eco mode; Boost disables ALL the mode-aware lockouts for
  service work / pre-trip packing.

- A **multi-mode-aware** system. The dashboard tile `select.rc_hvac_
  mode` exposes the operator's local override (`auto` / `heating` /
  `cooling` / `ventilation` / `disabled`) on top of the mode-aware
  defaults from `select.rc_mode` (the mode/automation-builder
  connection's mode select — away / stealth / sleep / boost).

## §2 Prerequisites

Path A — Generic thermostat (recommended when operator already has a
smart thermostat):

- The operator's existing smart thermostat (ecobee / nest /
  mitsubishi mini-split / daikin mini-split / any `climate.*`-
  exposing integration) configured per the vendor's instructions.
- For operators without a smart thermostat: a `sensor.<probe>` +
  a `switch.<heater_relay>` (1-Wire / Zigbee / Z-Wave temperature
  probe + a relay board driving the heater) + HA core
  `generic_thermostat` configured (its GUI flow walks through
  the configuration since 2022.x). The upstream `generic_
  thermostat` integration exposes `climate.<name>` entities
  directly via the HA core `climate` domain.

Path B — Diesel heater (Webasto / Eberspächer / Chinese diesel /
Vevor / Chinese planer-style):

- The operator's existing diesel heater installed per the
  manufacturer's instructions (most diesel heaters mount externally
  with a fuel line + combustion air intake + exhaust + a glow
  plug + a main blower + a combustion fan + a flame-sense wire).
- An ESP32 / ESP8266 board (ESPHome-compatible; ESP32 recommended
  for the extra GPIO + ADC channels) flashed with the ESPHome
  firmware, OR an ESPHome-MQTT bridge (a separate ESP32 running
  ESPHome that publishes the heater state over MQTT).
- The HA core `esphome` integration configured (its GUI flow
  walks through the device discovery since 2023.x); OR the HA
  core `mqtt` integration configured for the MQTT-bridged path.
- ESPHome YAML wiring exposes: `switch.glow_plug` (the heater's
  glow plug relay), `switch.main_blower` (the heater's main
  blower relay), `switch.combustion_fan` (the heater's
  combustion fan relay), `sensor.safety_thermistor` (the
  heater's safety thermistor in °C), `binary_sensor.flame_sense`
  (the flame-sense wire; TRUE when the heater detects flame).
- Alternative for heaters with an ESPHome-MQTT bridge: the
  upstream `mqtt` integration exposes the same set of entities
  (the ESPHome device publishes to MQTT topics that the `mqtt`
  integration subscribes to).

Path C — Rooftop AC (Furrion / Dometic / MaxxAir / Coleman):

- The operator's existing rooftop AC installed per the
  manufacturer's instructions (most rooftop ACs mount on the
  roof with a 110–230 VAC supply + a condensate drain + a
  remote-control IR receiver).
- An IR-bridge on the LAN (Broadlink RM Mini 3, Broadlink RM4
  Pro, or MQTT-IR-Hub via HACS). The IR-bridge learns the AC's
  remote codes and publishes them as switch / fan / select
  entities via the upstream `broadlink` integration (GUI flow
  since 2022.x) or the upstream `mqtt_ir_hub` integration
  (GUI flow since 2023.x).
- Alternative for AC units with a native HA integration (e.g.
  Furrion Chill with their own adapter): the upstream vendor
  integration exposes climate.* entities directly.

Path D — Cabin ventilation (cabin fan):

- The operator's existing cabin fan installed per the
  manufacturer's instructions (MaxxAir / Fan-Tastic Vent / roof-
  vent switch / cross-flow vent).
- The HA core `fan` integration configured (its GUI flow walks
  through the fan pairing since 2022.x). The fan integration
  exposes `fan.<name>` entities directly via the HA core `fan`
  domain.

Safety prerequisites (cross-references to other connections):

- The bluetooth-wifi-presence `connections/bluetooth-wifi-presence/`
  recipe's `binary_sensor.rc_presence_anyone_home` tile exists
  (required for the §7.2 over-temp warning's "pets left in van"
  escalation).
- The Victron `connections/victron/` recipe's `sensor.rc_power_
  battery_soc` + `binary_sensor.rc_power_shore_connected` tiles
  exist (required for the §7.3 low-voltage lockout).
- The mode/automation-builder `connections/mode-automation-builder/`
  recipe's `select.rc_mode` tile exists (required for the §7.4
  mode-aware lockouts: Stealth auto-lower fan + Sleep eco-mode
  + Boost disable-mode-aware-lockouts).
- The smart-automations `connections/smart-automations/` recipe's
  managed-marker convention is in place (the mode-aware
  automations can be wired as managed automations if the operator
  prefers).

No upstream vendor integration required beyond the climate /
esphome / mqtt / broadlink / fan integration. RoamCore ships
zero HVAC hardware.

## §3 Path A — Generic thermostat (recommended when operator already has a smart thermostat)

The `generic_thermostat` integration (HA core, GUI flow since
2022.x) is the recommended path for operators who don't already
have a smart thermostat but have a temperature probe + a relay-
driven heater. For operators who DO have a smart thermostat
(ecobee / nest / mitsubishi mini-split / daikin mini-split), the
vendor's own HA core integration exposes `climate.<name>` entities
directly — the wiring pattern is the same (the upstream
`climate.<name>` maps to the contract `climate.rc_hvac_cabin_
thermostat` via a HA core `template:` climate).

Step 1: choose the climate source.

```bash
# Option A.1 — HA core generic_thermostat (no smart thermostat;
# temperature probe + relay-driven heater):
#   In HA: Settings → Devices & Services → Add Integration →
#   Generic Thermostat. The GUI flow walks through:
#     - Temperature sensor (e.g. sensor.interior_temp)
#     - Heater switch (e.g. switch.heater_relay)
#     - min_temp / max_temp / cold_tolerance / hot_tolerance /
#       keep_alive settings
#   The upstream integration exposes climate.cabin_thermostat.

# Option A.2 — Vendor integration (smart thermostat already owned):
#   In HA: Settings → Devices & Services → Add Integration →
#   [Vendor name]. The GUI flow walks through the vendor's
#   onboarding. The upstream integration exposes climate.<name>
#   entities directly.
#   - ecobee: HA core `ecobee` integration (GUI flow since 2018.x)
#   - nest: HA core `nest` integration (GUI flow since 2022.x)
#   - mitsubishi: HACS `mitsubishi` Kumo Cloud integration OR
#     the local-API `mitsubishi_echonet` HACS integration
#   - daikin: HA core `daikin` integration (GUI flow since 2018.x)
```

Step 2: rename the climate entity to a stable entity_id.

```yaml
# homeassistant/packages/roamcore_hvac_thermostat.yaml
homeassistant:
  customize:
    climate.cabin_thermostat:
      friendly_name: "Cabin Thermostat"
      # The entity_id from generic_thermostat is stable across
      # reboots; no rename needed for the contract layer to find
      # it. For vendor integrations, the entity_id follows the
      # vendor's naming convention; rename via the HA core
      # `entity` customize-domain alias if the name is awkward.
```

Step 3: verify the climate surfaces as `climate.cabin_thermostat`
upstream.

```bash
# In HA Developer Tools → States, filter for `climate.cabin_thermostat`:
# Expect: climate.cabin_thermostat state=heat / cool / auto / off,
# attributes include current_temperature, target_temp_low,
# target_temp_high, hvac_action (heating / cooling / idle / off).
```

Step 4: wire the upstream `climate.cabin_thermostat` -> contract
`climate.rc_hvac_cabin_thermostat` mapping.

```yaml
template:
  - climate:
      - name: "rc_hvac_cabin_thermostat"
        # The template climate mirrors the upstream climate state.
        # When the operator changes the setpoint via the contract
        # tile (or the OpenClaw query "set cabin thermostat to
        # <temp>C"), HA fires climate.set_temperature service on
        # `climate.cabin_thermostat` (the upstream generic_
        # thermostat or vendor integration entity). When the
        # upstream climate changes (the operator adjusts the
        # vendor's own app, or a vendor-side automation fires),
        # the template climate mirrors the state.
        # The template climate only needs the state mirroring —
        # the upstream entity remains the source of truth for
        # the actual temperature control loop.
```

The recommended smart thermostats for vans (when the operator
already owns one):

| Vendor | Protocol | Notes |
|--------|----------|-------|
| **ecobee** | Wi-Fi (cloud-bridged) | Smart thermostat with remote sensors. |
| **nest** | Wi-Fi (cloud-bridged) | Smart thermostat with learning. |
| **Mitsubishi mini-split** | Kumo Cloud / local-API | Mini-split with HA integration. |
| **Daikin mini-split** | Wi-Fi (local-API) | Mini-split with HA core integration. |

## §4 Path B — Diesel heater (Webasto / Eberspächer / Chinese diesel)

Diesel heaters are the most common cabin heat source in van life
because they burn diesel directly (no propane tank + no inverter
draw), they heat the cabin air via a heat exchanger (no flame
inside the cabin), and they consume very little diesel (~0.5 L/hr
on low).

Step 1: flash ESPHome firmware on the ESP32 / ESP8266 that drives
the diesel heater.

```yaml
# esphome/diesel_heater.yaml
esphome:
  name: diesel-heater
  platform: ESP32
  board: esp32dev

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password
  ap:
    ssid: "Diesel-Heater Fallback"
    password: !secret ap_password

captive_portal:

logger:

api:
  encryption:
    key: !secret api_key

ota:
  - platform: esphome
    password: !secret ota_password

# Glow plug relay (drives the heater's glow plug; pre-heats the
# combustion chamber before ignition).
switch:
  - platform: gpio
    pin: GPIO25
    name: "Glow Plug"
    id: glow_plug
    icon: "mdi:fire"
    inverted: false

  # Main blower relay (drives the heater's main blower; pushes
  # air through the heat exchanger into the cabin).
  - platform: gpio
    pin: GPIO26
    name: "Main Blower"
    id: main_blower
    icon: "mdi:fan"
    inverted: false

  # Combustion fan relay (drives the heater's combustion fan;
  # mixes diesel + air in the combustion chamber).
  - platform: gpio
    pin: GPIO27
    name: "Combustion Fan"
    id: combustion_fan
    icon: "mdi:fan-chevron-up"
    inverted: false

# Safety thermistor (reads the heater's safety thermistor; if
# the temperature exceeds the safe limit, the heater MUST shut
# down — the relay cuts power to the heater).
sensor:
  - platform: thermistor
    sensor: !lambda "return 10000;"
    name: "Safety Thermistor"
    id: safety_thermistor
    unit_of_measurement: "°C"
    accuracy_decimals: 1
    filters:
      - throttle_average: 30s

# Flame sense wire (reads the heater's flame-sense wire; TRUE
# when the heater detects flame in the combustion chamber).
binary_sensor:
  - platform: gpio
    pin: GPIO34
    name: "Flame Sense"
    id: flame_sense
    icon: "mdi:fire"
    filters:
      - delayed_on: 2s
      - delayed_off: 5s

# Status LED + buzzer (the heater's local status indicators).
output:
  - platform: gpio
    pin: GPIO32
    id: status_led

  - platform: gpio
    pin: GPIO33
    id: buzzer

light:
  - platform: monochromatic
    name: "Status LED"
    output: status_led
    id: status_led_light
```

Step 2: pair the ESPHome device with HA.

```bash
# In HA: Settings → Devices & Services → Add Integration → ESPHome
# Click "Add". The GUI flow walks through device discovery + API
# key setup. After pairing, the heater's switch / sensor /
# binary_sensor entities appear in HA.
```

Step 3: verify the heater surfaces as `switch.glow_plug` etc.
upstream.

```bash
# In HA Developer Tools → States, filter for `switch.glow_plug`:
# Expect: switch.glow_plug state=off / on.
# Same for switch.main_blower, switch.combustion_fan,
# sensor.safety_thermistor, binary_sensor.flame_sense.
```

Step 4: wire the upstream entities -> contract `binary_sensor.
rc_hvac_heater_active` + the §7 safety interlocks mapping.

```yaml
# The heater is "active" when the combustion fan is on AND
# flame is detected. This is the canonical "is the diesel
# heater actually producing heat?" check — the combustion fan
# alone doesn't mean heat, and the flame sense alone doesn't
# mean the cabin is being heated.
template:
  - binary_sensor:
      - name: "rc_hvac_heater_active"
        state: >-
          {{ is_state('switch.combustion_fan', 'on')
             and is_state('binary_sensor.flame_sense', 'on') }}
        device_class: heat
```

Step 5: wire the heater control logic via the
`generic_thermostat` integration (Path A wiring + the heater
relay as the `switch.heater_relay` source).

The recommended diesel heaters for vans:

| Heater | Type | Power | Notes |
|--------|------|-------|-------|
| **Webasto Air Top 2000 STC** | Diesel | 2 kW | OEM-grade; expensive but reliable. |
| **Eberspächer Airtronic D2** | Diesel | 2 kW | OEM-grade; expensive but reliable. |
| **Chinese diesel (Vevor / Hcalory / LCD)** | Diesel | 2–5 kW | Budget; widely used in van conversions. |
| **Chinese planer-style (knock-off of Webasto)** | Diesel | 2–5 kW | Cheaper; variable quality. |

For the MQTT variant (heater has its own ESPHome-MQTT bridge
that publishes to MQTT topics): substitute the `mqtt:` switch /
sensor / binary_sensor YAML for the `switch:` / `sensor:` /
`binary_sensor:` YAML above; the contract wiring pattern is
identical.

## §5 Path C — Rooftop AC (Furrion / Dometic / MaxxAir / Coleman)

Rooftop ACs are the most common cabin cooling source in van life
because they don't require an inverter draw (most run on 110–230
VAC), they mount externally (no cabin real estate), and they
exhaust heat outside the cabin.

Step 1: pair the IR-bridge with HA + learn the AC's remote codes.

```bash
# Broadlink RM Mini 3 / RM4 Pro path:
# In HA: Settings → Devices & Services → Add Integration →
# Broadlink. The GUI flow walks through the device pairing
# (the device advertises itself via mDNS / UDP on the LAN).
# After pairing, use the Broadlink remote learn service to
# teach the bridge the AC's remote codes (power on, power off,
# mode cool, mode fan, mode heat, fan low, fan med, fan high,
# temp 16, temp 18, ..., temp 30).
# Save the learned codes as switch / fan / select entities via
# HA core `switch` + `fan` + `select` templates.

# MQTT-IR-Hub path:
# Install the mqtt_ir_hub HACS integration. Flash the IR
# bridge with the MQTT-IR-Hub firmware. The integration
# exposes switch / fan / select entities directly.
```

Step 2: rename the AC entities to stable entity_ids.

```yaml
# homeassistant/packages/roamcore_hvac_ac.yaml
homeassistant:
  customize:
    switch.rooftop_ac_power:
      friendly_name: "Rooftop AC Power"
    fan.rooftop_ac_fan:
      friendly_name: "Rooftop AC Fan"
    select.rooftop_ac_mode:
      friendly_name: "Rooftop AC Mode"
    select.rooftop_ac_fan_speed:
      friendly_name: "Rooftop AC Fan Speed"
    number.rooftop_ac_setpoint:
      friendly_name: "Rooftop AC Setpoint"
```

Step 3: verify the AC surfaces as `switch.rooftop_ac_power` etc.
upstream.

```bash
# In HA Developer Tools → States, filter for `switch.rooftop_ac_power`:
# Expect: switch.rooftop_ac_power state=off / on.
# Same for fan.rooftop_ac_fan, select.rooftop_ac_mode,
# select.rooftop_ac_fan_speed, number.rooftop_ac_setpoint.
```

Step 4: wire the upstream entities -> contract `binary_sensor.
rc_hvac_ac_active` + the §7 safety interlocks mapping.

```yaml
# The AC is "active" when power is on AND the mode is cool
# (or heat, depending on the AC's mode list). This is the
# canonical "is the rooftop AC actually running?" check.
template:
  - binary_sensor:
      - name: "rc_hvac_ac_active"
        state: >-
          {{ is_state('switch.rooftop_ac_power', 'on')
             and (is_state('select.rooftop_ac_mode', 'cool')
                  or is_state('select.rooftop_ac_mode', 'auto')) }}
        device_class: cold
```

Step 5: wire the AC setpoint via the upstream number entity OR
via a custom IR code service call.

The recommended rooftop ACs for vans:

| AC | Type | Power | Notes |
|----|------|-------|-------|
| **Furrion Chill** | Rooftop | 110–230 VAC | Premium; some models have native HA integration. |
| **Dometic Brisk II** | Rooftop | 110–230 VAC | Premium; widely available. |
| **MaxxAir MaxxFan** | Roof vent + fan | 12 VDC | Roof vent with built-in fan (not full AC). |
| **Coleman Mach** | Rooftop | 110–230 VAC | Premium; widely available. |

For native integrations (e.g. Furrion Chill with their own
adapter): the upstream vendor integration exposes climate.*
entities directly; map them to the contract via the same
`template:` climate pattern as Path A.

## §6 Path D — Ventilation (cabin fan)

Cabin ventilation is the often-overlooked "third mode" of HVAC
(heating + cooling + ventilation). On a hot-but-not-AC-day, or
when the AC is in eco mode, the cabin fan alone can keep the
cabin comfortable. On a cold-but-not-heater day, the cabin fan
distributes the heat from the Webasto / Chinese diesel without
running the heater at full power.

Step 1: pair the cabin fan with HA.

```bash
# Most cabin fans are simple 3-speed (low/med/high) or fully
# variable; the HA core `fan` integration handles both.
# In HA: Settings → Devices & Services → Add Integration →
# Fan. The GUI flow walks through:
#   - Fan entity selection (the fan's switch / fan entity)
#   - Speed selection (low / med / high / off; or fully variable)
```

Step 2: rename the fan entity to a stable entity_id.

```yaml
# homeassistant/packages/roamcore_hvac_fan.yaml
homeassistant:
  customize:
    fan.cabin_fan:
      friendly_name: "Cabin Fan"
```

Step 3: verify the fan surfaces as `fan.cabin_fan` upstream.

```bash
# In HA Developer Tools → States, filter for `fan.cabin_fan`:
# Expect: fan.cabin_fan state=off / on, percentage=0..100.
```

Step 4: wire the upstream `fan.cabin_fan` -> contract `fan.rc_hvac_
cabin_fan` mapping + the fan-speed select.

```yaml
# The contract fan mirrors the upstream fan state. The fan-speed
# select exposes the discrete speed choices (low / med / high /
# auto / off).
template:
  - fan:
      - name: "rc_hvac_cabin_fan"
        state: "{{ states('fan.cabin_fan') }}"
        percentage: "{{ state_attr('fan.cabin_fan', 'percentage') }}"

select:
  - platform: template
    selects:
      rc_hvac_fan_speed:
        options:
          - "off"
          - "low"
          - "med"
          - "high"
          - "auto"
        initial: "auto"
```

The recommended cabin fans for vans:

| Fan | Type | Power | Notes |
|-----|------|-------|-------|
| **MaxxAir MaxxFan** | Roof vent + 3-speed fan | 12 VDC | Premium; built-in rain sensor. |
| **Fan-Tastic Vent** | Roof vent + 3-speed fan | 12 VDC | Premium; reversible for intake/exhaust. |
| **Chinese roof vent** | Roof vent + 3-speed fan | 12 VDC | Budget; widely available. |
| **Sirocco II cabin fan** | In-cabin 3-speed fan | 12 VDC | Premium; in-cabin mounting. |

## §7 RoamCore contract entities

The 11 `rc_hvac_*` tiles + how the upstream `climate.*` / `switch.*`
/ `fan.*` / `sensor.*` templates expose them + translation helpers
needed.

The full tile set (per `connection.yml` `dashboard.tiles`):

- `climate.rc_hvac_cabin_thermostat` — cabin thermostat state
  (heat / cool / auto / off) + setpoint (target_temp_low /
  target_temp_high). The contract tile mirrors the upstream
  `climate.cabin_thermostat` (Path A generic_thermostat OR vendor
  integration).
- `sensor.rc_hvac_cabin_temperature` — cabin temperature in °C
  (the current temperature the thermostat is reading). The
  contract tile mirrors the upstream `sensor.<cabin_temp_probe>`
  (Path A temperature source).
- `sensor.rc_hvac_cabin_humidity` — cabin humidity in % (when
  the operator has a humidity sensor; not all thermostats
  expose this).
- `binary_sensor.rc_hvac_heater_active` — TRUE when the diesel
  heater (Path B) is actively producing heat (combustion fan
  on AND flame detected). The contract tile is a `template:`
  binary_sensor derived from the upstream `switch.combustion_fan`
  + `binary_sensor.flame_sense`.
- `binary_sensor.rc_hvac_ac_active` — TRUE when the rooftop AC
  (Path C) is actively cooling (power on AND mode is cool or
  auto). The contract tile is a `template:` binary_sensor
  derived from the upstream `switch.rooftop_ac_power` +
  `select.rooftop_ac_mode`.
- `fan.rc_hvac_cabin_fan` — cabin fan state (off / on) +
  percentage (0..100). The contract tile mirrors the upstream
  `fan.cabin_fan` (Path D fan integration).
- `select.rc_hvac_fan_speed` — fan speed select (off / low /
  med / high / auto). The contract tile is a `template:`
  select that maps the upstream `fan.cabin_fan.percentage` to
  the discrete speed choices.
- `sensor.rc_hvac_outdoor_temperature` — outdoor temperature in
  °C. The contract tile mirrors the upstream `sensor.<outdoor_
  temp>` (any outdoor temperature sensor; HA core `weather`
  integration exposes this via `weather.<home>.temperature`).
- `binary_sensor.rc_hvac_frost_warning` — TRUE when
  `sensor.rc_hvac_outdoor_temperature` < 2 °C AND
  `sensor.rc_hvac_cabin_temperature` < 5 °C (the cabin is at
  risk of dropping below freezing). The contract tile is a
  `template:` binary_sensor derived from the outdoor + cabin
  temperatures.
- `binary_sensor.rc_hvac_over_temp_warning` — TRUE when
  `sensor.rc_hvac_cabin_temperature` > 35 °C. The contract
  tile is a `template:` binary_sensor derived from the cabin
  temperature.
- `select.rc_hvac_mode` — HVAC mode select (auto / heating /
  cooling / ventilation / disabled). The contract tile is a
  `template:` select that controls the high-level HVAC mode.

The heater-active template:

```yaml
template:
  - binary_sensor:
      - name: "rc_hvac_heater_active"
        state: >-
          {{ is_state('switch.combustion_fan', 'on')
             and is_state('binary_sensor.flame_sense', 'on') }}
        device_class: heat
```

The AC-active template:

```yaml
template:
  - binary_sensor:
      - name: "rc_hvac_ac_active"
        state: >-
          {{ is_state('switch.rooftop_ac_power', 'on')
             and (is_state('select.rooftop_ac_mode', 'cool')
                  or is_state('select.rooftop_ac_mode', 'auto')) }}
        device_class: cold
```

The frost-warning template:

```yaml
template:
  - binary_sensor:
      - name: "rc_hvac_frost_warning"
        state: >-
          {{ (states('sensor.rc_hvac_outdoor_temperature') | float(99)) < 2
             and (states('sensor.rc_hvac_cabin_temperature') | float(99)) < 5 }}
        device_class: cold
```

The over-temp-warning template:

```yaml
template:
  - binary_sensor:
      - name: "rc_hvac_over_temp_warning"
        state: >-
          {{ (states('sensor.rc_hvac_cabin_temperature') | float(0)) > 35 }}
        device_class: heat
```

The HVAC-mode select:

```yaml
select:
  - platform: template
    selects:
      rc_hvac_mode:
        options:
          - "auto"
          - "heating"
          - "cooling"
          - "ventilation"
          - "disabled"
        initial: "auto"
```

## §8 Safety interlocks & automations (MANDATORY before first use)

Four safety interlocks to enable (the recipe ships the full YAML for
each):

1. **Frost warning** — when `sensor.rc_hvac_outdoor_temperature` <
   2 °C AND `sensor.rc_hvac_cabin_temperature` < 5 °C, fire
   `binary_sensor.rc_hvac_frost_warning` TRUE + force the cabin
   thermostat (`climate.rc_hvac_cabin_thermostat`) to maintain
   > 5 °C. This overrides the operator's setpoint if the operator
   has the thermostat set lower. The frost warning is critical in
   winter van life — frozen pipes / condensation / battery damage
   below 0 °C.

2. **Over-temp warning** — when `sensor.rc_hvac_cabin_temperature`
   > 35 °C, fire `binary_sensor.rc_hvac_over_temp_warning` TRUE +
   turn on the AC (`binary_sensor.rc_hvac_ac_active` TRUE) + open
   the cabin fan + send a push notification. The cross-reference to
   the bluetooth-wifi-presence connection is for the "pets left in
   van" scenario: when over-temp fires AND
   `binary_sensor.rc_presence_anyone_home` is FALSE, the alert
   escalates to high-priority + the dashboard highlights the
   over-temp tile in red. The operator + pets + electronics MUST
   not cook.

3. **Low-voltage lockout** — when `sensor.rc_power_battery_soc`
   < 30 % (from the Victron connection) AND
   `binary_sensor.rc_power_shore_connected` is FALSE, fire a
   low-voltage-lockout behavior: disable the diesel heater
   (Path B) AND the rooftop AC (Path C). The cabin fan (Path D)
   stays enabled because it draws < 1 A. The operator can still
   manually turn on the AC if shore power is connected (the
   `binary_sensor.rc_power_shore_connected` check). The cross-
   reference to the Victron connection is the same pattern that
   the heated-floors + Happijac bed lift connections use for their
   low-voltage lockout interlocks.

4. **Mode-aware lockouts (Stealth / Sleep / Boost)** —
   - Stealth silent hours auto-lower fan: when
     `select.rc_mode == stealth` (from the mode/automation-
     builder connection), force `select.rc_hvac_fan_speed` to
     `low` so the fan doesn't wake the campground neighbors.
   - Sleep mode fan-off + eco: when
     `select.rc_mode == sleep`, force `fan.rc_hvac_cabin_fan`
     to OFF + drop the heater setpoint by 2 °C + drop the AC
     setpoint by 2 °C for eco mode (the operator is asleep —
     full eco).
   - Boost disable-mode-aware-lockouts: when
     `select.rc_mode == boost`, disable ALL the above mode-aware
     lockouts (Stealth / Sleep) so the operator has full climate
     control during service work / pre-trip packing.
   - The `select.rc_hvac_mode` tile exposes the operator's local
     override (`auto` / `heating` / `cooling` / `ventilation` /
     `disabled`) on top of the mode-aware defaults.

## §9 Automations

Six automations to enable (the recipe ships the full YAML for each):

1. **Stealth auto-lower fan** — when `select.rc_mode == stealth`
   (from the mode/automation-builder connection), force
   `select.rc_hvac_fan_speed` to `low`. The cabin fan doesn't
   wake the campground neighbors during Stealth silent hours.

2. **Sleep eco-mode** — when `select.rc_mode == sleep`, force
   `fan.rc_hvac_cabin_fan` to OFF + drop the heater setpoint by
   2 °C + drop the AC setpoint by 2 °C. The operator is asleep —
   full eco mode to save battery.

3. **Boost disable-mode-aware-lockouts** — when
   `select.rc_mode == boost`, disable ALL the Stealth + Sleep
   mode-aware lockouts so the operator has full climate control
   during service work / pre-trip packing.

4. **Frost auto-heat** — when `binary_sensor.rc_hvac_frost_warning`
   is TRUE, force `climate.rc_hvac_cabin_thermostat` to maintain
   > 5 °C + fire a push notification. The cabin MUST not drop
   below 5 °C — frozen pipes / condensation / battery damage
   below 0 °C.

5. **Over-temp auto-cool + alert** — when
   `binary_sensor.rc_hvac_over_temp_warning` is TRUE, turn on the
   AC (`binary_sensor.rc_hvac_ac_active` TRUE) + open the cabin
   fan + send a push notification. If
   `binary_sensor.rc_presence_anyone_home` is FALSE (from the
   bluetooth-wifi-presence connection), the alert escalates to
   high-priority + the dashboard highlights the over-temp tile
   in red.

6. **Mode-aware morning pre-warm** — at 06:00 on weekday mornings
   (Monday-Friday), if `select.rc_mode == morning_routine` (a
   sub-mode the operator defines in the mode/automation-builder
   connection), force the cabin thermostat to 18 °C for 30
   minutes (pre-warm the cabin before the operator wakes up). The
   morning pre-warm is bounded to 30 minutes to avoid wasting
   battery if the operator doesn't actually wake up at 06:00.

The full automation YAML for each is in the recipe
`homeassistant/automations/rc_hvac_*.yaml` files (operator wires
these manually until tier-a promotion lands).

## §10 Troubleshooting

Eight troubleshooting entries:

1. **Thermostat not responding** — check the upstream
   `generic_thermostat` configuration (Path A). The temperature
   sensor must be a `sensor.*` entity (not a `binary_sensor.*`).
   The heater switch must be a `switch.*` entity. The
   `min_temp` / `max_temp` clamps must allow the operator's
   desired setpoint. For vendor integrations (ecobee / nest /
   mitsubishi / daikin), check the vendor's cloud status — most
   vendor integrations require cloud connectivity.

2. **Heater won't ignite** — glow plug pre-heat timeout. The
   heater's glow plug relay must be energized for 30–60 seconds
   before the combustion fan starts. If the ESPHome YAML doesn't
   have the pre-heat delay, the heater won't ignite reliably.
   Solution: add a `delay: 30s` between the glow plug on and
   the combustion fan on in the ESPHome automation.

3. **Heater shuts off after 30s** — flame-sense failure. The
   flame-sense wire must read TRUE within 30 seconds of the
   combustion fan starting. If the wire is disconnected or
   the combustion chamber is dirty, the heater's safety
   circuit cuts power. Solution: check the flame-sense wire
   connection + clean the combustion chamber + verify the
   `binary_sensor.flame_sense` entity is reading TRUE within
   30s of the combustion fan starting.

4. **AC doesn't respond to IR** — re-learn the IR codes on the
   bridge. The IR codes for the AC's remote are learned via the
   Broadlink / MQTT-IR-Hub's remote-learn service. If the AC
   doesn't respond to the learned codes, re-learn the codes
   (sometimes the first attempt captures noise). Solution: use
   the remote-learn service again, holding the AC's remote
   closer to the IR-bridge.

5. **Fan stuck on one speed** — wiring fault or relay stuck.
   The cabin fan's relay contacts can weld shut if the fan
   draws too much current. Solution: check the fan's current
   draw (should be < 5 A on high); if the relay is stuck,
   replace the relay.

6. **Frost warning stuck on** — cross-check outdoor sensor.
   The frost warning is TRUE when
   `sensor.rc_hvac_outdoor_temperature` < 2 °C AND
   `sensor.rc_hvac_cabin_temperature` < 5 °C. If the warning
   is stuck on, check the outdoor sensor's reading (some
   outdoor sensors report -40 °C when the probe is
   disconnected — the cabin temperature < 5 °C check would
   also fire). Solution: cross-check the outdoor sensor's
   reading in HA Developer Tools → States; if the reading is
   -40 °C, the probe is disconnected.

7. **Over-temp warning stuck on** — cross-check cabin sensor.
   The over-temp warning is TRUE when
   `sensor.rc_hvac_cabin_temperature` > 35 °C. If the warning
   is stuck on, check the cabin sensor's reading (some
   temperature sensors report 200 °C when the probe is
   shorted). Solution: cross-check the cabin sensor's reading
   in HA Developer Tools → States; if the reading is 200 °C,
   the probe is shorted.

8. **Low-voltage lockout stuck on after charging** — cross-check
   Victron SOC. The low-voltage lockout is TRUE when
   `sensor.rc_power_battery_soc` < 30 % AND
   `binary_sensor.rc_power_shore_connected` is FALSE. If the
   lockout is stuck on after charging, check the SOC reading
   (the SOC may be reading from a stale template cache).
   Solution: wait 5 minutes for the SOC template to re-evaluate;
   if the SOC reading is correct, the lockout should release
   when SOC >= 30 % AND shore is disconnected (the lockout
   releases automatically when shore power is connected).

## §11 Privacy

No telemetry. Everything is local. The climate / esphome / mqtt /
broadlink / fan integrations are local; no cloud call home. The HA
core `climate` + `fan` + `sensor` domains do not phone home.

Vendor integrations (ecobee / nest) MAY phone home to the
vendor's cloud — that's the operator's vendor choice; RoamCore
does not add any cloud integration. The contract entities
(`rc_hvac_*`) do not collect any operator data; they are pure
local-state tiles that surface the operator's choice + the
upstream entity state.

The push notification for the over-temp warning uses the
operator's existing HA Core push notification channel — that's
the operator's choice; RoamCore does not add any push
notification channel. The bluetooth-wifi-presence cross-
reference for the "pets left in van" escalation uses the
operator's existing presence detection — no additional
tracking is added.

## §12 Promoting to tier-a

What would need to happen to promote this connection from tier-b
to tier-a:

- A real HVAC bench on the CI rig: a thermostat + a heater +
  an AC + a fan + a temperature/humidity sensor + a relay
  board, all wired together in a controlled environment.
- A canonical RoamCore-owned `config_flow.py` that walks the
  operator through choosing Path A vs Path B vs Path C vs
  Path D + declaring the upstream entities (the climate.*
  entity for Path A; the switch.* + binary_sensor.* + sensor.*
  entities for Path B; the switch.* + fan.* + select.*
  entities for Path C; the fan.* entity for Path D) + mapping
  each upstream entity to the contract tile.
- Integration tests that assert a temperature change on
  `sensor.rc_hvac_cabin_temperature` triggers the right
  `binary_sensor.rc_hvac_frost_warning` /
  `binary_sensor.rc_hvac_over_temp_warning` updates + the
  §7 safety interlocks all fire when wired to canned fixture
  responses.
- Integration tests that assert the §7.3 low-voltage lockout
  disables the diesel heater + AC when
  `sensor.rc_power_battery_soc` < 30 % (cross-reference to the
  Victron `connections/victron/` recipe).
- Integration tests that assert the §7.4 mode-aware lockouts
  fire when `select.rc_mode` transitions to stealth / sleep /
  boost (cross-reference to the mode/automation-builder
  `connections/mode-automation-builder/` recipe).
- Integration tests that assert the §8.5 over-temp auto-cool
  + alert automation turns on the AC + opens the cabin fan +
  sends a push notification when
  `sensor.rc_hvac_cabin_temperature` > 35 °C.
- Flip `tier_requirements` to include `working_config_flow` +
  `integration_test_passes` + `no_manual_yaml_required` +
  `safety_automations_hard_enforced_in_roamcore_code`.

Until those ship, this connection is tier-b even though the
upstream climate / esphome / mqtt / broadlink / fan integrations
have their own GUI flows. The recipe is sound but we cannot
claim one-tap automation.
