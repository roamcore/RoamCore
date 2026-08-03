# Electronic valves + auto tank switching — tier-b recipe connection

This is the full howto for the `connections/electronic-valves/` tier-b
recipe connection. It walks through wiring fresh-inlet / grey-drain /
aux-tank valve control on the van (Path A — ESPHome valve node + 12 V
/ 24 V electrically-actuated valves + safe drivers per valve + valve-
position feedback (limit switch or current sense); the ESPHome YAML
exposes `switch.<node>_valve_fresh_inlet` +
`switch.<node>_valve_grey_drain` +
`switch.<node>_valve_aux_tank` + the
`binary_sensor.<node>_valve_*_position` feedback; Path B — generic
relay (Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano Switch)
wired into the 12 V / 24 V valve coils + HA core `template:` valve or
`switch:` template + valve-position feedback binary_sensor), mapping
the upstream entities into the 17 `rc_water_valve_*` contract tiles,
layering the six MANDATORY safety interlocks (leak detected / freeze
risk / low-voltage lockout / auto-close grey / mode-aware lockouts /
valve stuck-open detector) + the §8 automations, and promoting the
connection to tier-a when the bench fixture lands.

## §1 What is Electronic valves + auto tank switching in RoamCore?

Electronic valves + auto tank switching — fresh-inlet / grey-drain /
aux-tank valve control + auto tank switching between primary and aux
tanks — is positioned in RoamCore as:

- A **vendor-neutral** valve contract. The contract talks to
  whatever valve integration the operator already runs (Path A —
  ESPHome valve node + 12 V / 24 V electrically-actuated valves +
  safe drivers; Path B — generic relay + HA template valve), not to
  any specific vendor's library.

- A **single "are the valves within safe bounds?" aggregate** that
  surfaces fresh inlet state + grey drain state + aux tank state +
  valve-position feedback + any-moving + auto-tank-switch-active +
  leak-detected-lockout + freeze-risk-lockout + low-voltage-lockout
  into one dashboard tile. The
  `binary_sensor.rc_water_valve_leak_detected_lockout` +
  `binary_sensor.rc_water_valve_freeze_risk_lockout` +
  `binary_sensor.rc_water_valve_low_voltage_lockout` tiles are the
  van-killer scenario locks; together with
  `binary_sensor.rc_water_valve_any_moving` +
  `binary_sensor.rc_water_valve_auto_tank_switch_active`, they
  give the operator a complete view of "are the valves within safe
  bounds?" at a glance.

- A **safety-first** system. The
  `binary_sensor.rc_water_valve_leak_detected_lockout` tile fires
  when ANY leak sensor (under-sink / pump-area / under-van)
  reports water + closes fresh inlet (so the leak isn't
  continuously fed from the fresh tank) + opens grey drain (so
  the leak drips onto the floor / ground rather than pooling in
  the grey tank which then overflows onto the road). The
  `binary_sensor.rc_water_valve_freeze_risk_lockout` tile fires
  when `sensor.rc_water_fresh_temperature_c` < 2 °C + closes ALL
  valves (frozen valve + frozen pipe + frozen fresh tank =
  cracked tank + burst pipes + valve body splits = van-killer).

- A **battery-aware** system. The valve coils pull 0.5–2 A
  sustained during the switching pulse; below 20 % SOC that's
  enough to keep the battery bank from recovering overnight.
  The `binary_sensor.rc_water_valve_low_voltage_lockout` tile
  fires when `sensor.rc_power_battery_soc` <
  `number.rc_water_valve_low_voltage_lockout_soc_pct` (default
  20 %) AND `binary_sensor.rc_power_shore_connected` == FALSE
  + disables all valve opens (the operator can still manually
  close valves for emergency shutdown). The cross-reference to
  the Victron connection is the same pattern that the heated-
  floors + hvac-basics + happijac + water-tanks connections
  use for their low-voltage lockout interlocks.

- A **mode-aware** system. The `select.rc_water_valve_mode`
  select controls the valve monitoring mode: `auto` (auto tank
  switching + all warnings enabled), `manual_only` (auto tank
  switching disabled + manual valve control only), `stealth_only`
  (auto tank switching + only leak / freeze / low-voltage
  warnings; mute the daytime-noise auto-switch notifications),
  `silent` (auto tank switching disabled + no warnings — reserved
  for service work), `disabled` (no monitoring at all — reserved
  for when the operator has intentionally drained the tanks for
  winterization). The mode-aware lockouts (Stealth / Sleep /
  Boost) layer on top: Stealth silent hours auto-mute the auto-
  switch notifications; Sleep mode additionally drops the
  operator-tunable warning thresholds by 10 %; Boost disables ALL
  the mode-aware lockouts for service work / pre-trip packing.

- A **multi-mode-aware** system. The dashboard tile
  `select.rc_water_valve_mode` exposes the operator's local
  override (`auto` / `manual_only` / `stealth_only` / `silent` /
  `disabled`) on top of the mode-aware defaults from
  `select.rc_mode` (the mode/automation-builder connection's mode
  select — away / stealth / sleep / boost).

## §2 Prerequisites

Path A — ESPHome valve node (recommended for ESPHome-friendly
installs):

- One ESP32 per node (e.g. ESP32-DevKitC-V4 / ESP32-S3-DevKitC-1 /
  Wemos D1 Mini ESP32) flashed with ESPHome firmware.
- Three electrically-actuated 12 V / 24 V valves per van (one each
  for fresh inlet, grey drain, aux tank switching). Common
  choices: latching solenoid valve (bistable — power only to
  switch state, lower current draw, good for battery-powered
  vans); motorized ball valve (continuous power to actuate,
  position feedback typically built-in); proportional valve
  (continuous power + proportional control for variable flow
  rate). The recipe defaults to latching solenoid for battery
  efficiency.
- One safe driver per valve: a relay module (1-channel relay
  module for latching solenoids — pulse HIGH for 100 ms to
  switch state, pulse LOW to switch back); a MOSFET H-bridge
  (for motorized ball valves — needs both forward and reverse
  current); a BTS7960 43 A H-bridge driver (for high-current
  motorized ball valves); an IBOM (intelligent brushless output
  module — for proportional valves).
- One valve-position feedback per valve (for the
  `binary_sensor.<node>_valve_*_position` entity). Two common
  choices: a limit switch (mechanical microswitch on the valve
  body — TRUE when valve is in the open position); a current
  sense (CT clamp on the valve coil wire — TRUE when valve is
  actively switching). The limit switch is more reliable but
  adds wiring complexity; the current sense is simpler but can
  false-positive on power-supply noise.
- Optional DS18B20 temperature probe (in the tank bay) wired
  into GPIO 4 with a 4.7 kΩ pull-up resistor to 3.3 V (for the
  §7.2 freeze-risk safety interlock — shares the same probe
  used by the water-tanks Wave 3 #50 recipe).
- Optional leak sensor probe (e.g. a water-level-detection
  sensor with exposed contacts) wired into GPIO 14 with a
  10 kΩ pull-up resistor to 3.3 V (for the §7.1 leak-detected
  safety interlock — shares the same probe used by the water-
  tanks Wave 3 #50 recipe).
- The upstream `esphome` integration configured in HA (GUI flow
  since 2023.x) — ESPHome auto-discovers ESP32 nodes on the LAN
  via mDNS.

Path B — Generic relay + HA template valve (no ESPHome):

- Three relays (one per valve). Common choices: Shelly 1
  (single-channel relay, 12 V or 24 V power, dry contacts);
  Shelly Plus 1 (newer version with Bluetooth + improved Wi-Fi);
  Zooz ZEN17 (Z-Wave relay, 12 V or 24 V power); Aeotec Nano
  Switch (Z-Wave relay, 12 V or 24 V power). The relay contacts
  are wired into the 12 V / 24 V valve coils (the relay provides
  the switching pulse for the valve coil).
- For motorized ball valves: a DPDT relay (double-pole double-
  throw) or two SPST relays to provide both forward and reverse
  current (most motorized ball valves need both directions to
  open and close).
- One valve-position feedback per valve (the operator can use
  the relay's "switch state" as a proxy for "valve state" but
  that's not the same as "valve position" — for the position
  feedback, the operator still wires a limit switch or current
  sense separately; for latching solenoids without position
  feedback, the operator may skip the position binary_sensor
  and rely solely on the valve-state switch).
- The upstream `shelly` / `zooz` / `aeotec` integration
  configured in HA (GUI flow since 2022.x).
- The HA `template:` integration (HA core) — for the contract
  tile synthesis + the derived aggregates (`any_moving`,
  `auto_tank_switch_active`, `leak_detected_lockout`,
  `freeze_risk_lockout`, `low_voltage_lockout`).

Common to both paths:

- The HA `template:` integration (HA core) — for the contract
  tile synthesis + the derived aggregates + the auto-close-grey
  timer.
- The HA `timer:` integration (HA core) — for the auto-close-
  grey N-minutes timer.
- The HA `input_boolean:` integration (HA core, GUI flow since
  2022.x) — for the §8.1 / §8.2 / §8.3 / §8.4 / §8.5
  automation input booleans.
- The HA `input_select:` integration (HA core, GUI flow since
  2022.x) — for the operator-tunable
  `select.rc_water_valve_active_tank` +
  `select.rc_water_valve_mode` tiles.
- The HA `input_number:` integration (HA core, GUI flow since
  2022.x) — for the operator-tunable
  `number.rc_water_valve_auto_close_grey_min` +
  `number.rc_water_valve_low_voltage_lockout_soc_pct` tiles.
- The HA `button:` integration (HA core, GUI flow since
  2023.x) — for the `button.rc_water_valve_open_all` +
  `button.rc_water_valve_close_all` emergency buttons.
- The water-tanks Wave 3 #50 connection installed and configured
  — for the §6 auto tank switching source signals
  (`sensor.rc_water_fresh_level_pct` +
  `sensor.rc_water_grey_level_pct`) + the §7.1 / §7.2 safety
  interlock cross-references (`binary_sensor.rc_water_leak_
  detected` + `binary_sensor.rc_water_freeze_risk` +
  `sensor.rc_water_fresh_temperature_c`).
- The Victron connection installed and configured — for the
  §7.3 low-voltage lockout safety interlock
  (`sensor.rc_power_battery_soc` +
  `binary_sensor.rc_power_shore_connected`).
- The mode/automation-builder connection installed and
  configured — for the §7.5 / §8.7 mode-aware lockouts +
  scheduling (`select.rc_mode`).

## §3 Path A — ESPHome valve node (recommended for ESPHome-friendly installs)

The full ESPHome YAML for an ESP32 with 3× 12 V / 24 V
electrically-actuated valves (one each for fresh inlet, grey drain,
aux tank switching) + a relay module per valve + a limit switch per
valve for valve-position feedback + (optional) a DS18B20 temperature
probe in the tank bay + (optional) a leak sensor probe wired into a
GPIO. The ESPHome YAML exposes:

- `switch.<node>_valve_fresh_inlet` — fresh inlet valve control
- `switch.<node>_valve_grey_drain` — grey drain valve control
- `switch.<node>_valve_aux_tank` — aux tank switching valve control
- `binary_sensor.<node>_valve_fresh_inlet_position` — fresh inlet
  valve position (limit switch or current sense)
- `binary_sensor.<node>_valve_grey_drain_position` — grey drain
  valve position
- `binary_sensor.<node>_valve_aux_tank_position` — aux tank
  valve position
- `sensor.<node>_fresh_temperature_c` — tank bay temperature
  probe (°C) — shared with the water-tanks Wave 3 #50 recipe
- `binary_sensor.<node>_leak_detected` — TRUE when the leak
  sensor reports water — shared with the water-tanks Wave 3 #50
  recipe

The full ESPHome YAML:

```yaml
esphome:
  name: van-water-valves
  platform: ESP32
  board: esp32-devkitc-v4

# Wireless + logger + web + api config omitted for brevity (see
# ESPHome's standard ESP32 base config).

# 1-channel relay module per valve — GPIO 13 (fresh inlet),
# GPIO 27 (grey drain), GPIO 32 (aux tank switching).
switch:
  - platform: gpio
    name: "Valve Fresh Inlet"
    pin:
      number: GPIO13
      mode: OUTPUT
    id: valve_fresh_inlet
    icon: "mdi:water-pump"

  - platform: gpio
    name: "Valve Grey Drain"
    pin:
      number: GPIO27
      mode: OUTPUT
    id: valve_grey_drain
    icon: "mdi:water-pump-off"

  - platform: gpio
    name: "Valve Aux Tank"
    pin:
      number: GPIO32
      mode: OUTPUT
    id: valve_aux_tank
    icon: "mdi:water-pump"

# Limit switch on each valve body for position feedback — GPIO
# 14 (fresh inlet), GPIO 26 (grey drain), GPIO 33 (aux tank).
# Mechanical microswitch on the valve body — TRUE when the
# valve is in the open position.
binary_sensor:
  - platform: gpio
    pin:
      number: GPIO14
      mode: INPUT_PULLUP
    name: "Valve Fresh Inlet Position"
    filters:
      - delayed_off: 500ms  # debounce

  - platform: gpio
    pin:
      number: GPIO26
      mode: INPUT_PULLUP
    name: "Valve Grey Drain Position"
    filters:
      - delayed_off: 500ms

  - platform: gpio
    pin:
      number: GPIO33
      mode: INPUT_PULLUP
    name: "Valve Aux Tank Position"
    filters:
      - delayed_off: 500ms

  # DS18B20 temperature probe in tank bay (shared with water-
  # tanks Wave 3 #50 recipe).
  - platform: gpio
    pin:
      number: GPIO4
      mode: INPUT_PULLUP
    name: "Leak Detected"
    filters:
      - delayed_off: 500ms  # debounce

# DS18B20 temperature probe in tank bay (shared with water-
# tanks Wave 3 #50 recipe).
sensor:
  - platform: dallas_temp
    address: 0x1234567890ABCDEF  # your probe's address
    name: "Tank Bay Temperature (°C)"
    update_interval: 60s
```

The full wiring of the upstream entities into the 17 contract
tiles is via HA core `template:` — see §6 below.

## §4 Path B — Generic relay + HA template valve (no ESPHome)

The Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano Switch wiring
(12 V / 24 V supply + relay contacts into the valve coils):

1. Power the relay via the van's 12 V / 24 V distribution. For
   Shelly 1 / Shelly Plus 1: 12 V DC (or 24 V DC for the 24 V
   variant) on the `+12V` / `GND` (or `+24V` / `GND`)
   terminals. For Zooz ZEN17 / Aeotec Nano Switch: 12 V DC (or
   24 V DC for the 24 V variant) on the appropriate terminals.
2. Wire the relay's switched output to the valve coil. For a
   latching solenoid: the relay's COM terminal connects to the
   valve coil's +V terminal; the relay's NO (normally-open)
   terminal connects to the valve coil's -V terminal; the
   relay is pulsed for 100 ms to switch state. For a motorized
   ball valve: a DPDT relay (or two SPST relays) provides both
   forward and reverse current; consult the valve's wiring
   diagram for the specific terminal layout.
3. Configure the relay via its web UI (mDNS auto-discovery on
   the LAN for Shelly; Z-Wave interview for Zooz / Aeotec). The
   Shelly integration in HA exposes `switch.shelly_valve_fresh_
   inlet` (or similar); the Z-Wave JS integration in HA exposes
   `switch.zooz_valve_fresh_inlet` (or similar).
4. For valve-position feedback: wire a limit switch on the
   valve body to a separate GPIO (ESPHome node) OR a Zigbee /
   Z-Wave contact sensor. The position feedback is then exposed
   as `binary_sensor.<position_sensor>` and mapped via HA core
   `template:` to `binary_sensor.rc_water_valve_fresh_inlet_
   position` (etc.). For latching solenoids without separate
   position feedback: the operator may skip the position
   binary_sensor and rely solely on the valve-state switch
   (the recipe's `binary_sensor.rc_water_valve_<role>_position`
   tile would then mirror the `switch.rc_water_valve_<role>_
   state` tile directly).

The HA `template:` switch wiring the relay state to the
contract tile:

```yaml
template:
  - switch:
      - name: "RC Water Valve Fresh Inlet State"
        unique_id: rc_water_valve_fresh_inlet_state
        turn_on:
          - switch.turn_on: switch.shelly_valve_fresh_inlet
        turn_off:
          - switch.turn_off: switch.shelly_valve_fresh_inlet

      - name: "RC Water Valve Grey Drain State"
        unique_id: rc_water_valve_grey_drain_state
        turn_on:
          - switch.turn_on: switch.shelly_valve_grey_drain
        turn_off:
          - switch.turn_off: switch.shelly_valve_grey_drain

      - name: "RC Water Valve Aux Tank State"
        unique_id: rc_water_valve_aux_tank_state
        turn_on:
          - switch.turn_on: switch.shelly_valve_aux_tank
        turn_off:
          - switch.turn_off: switch.shelly_valve_aux_tank
```

## §5 Path A vs Path B — operator's choice

Path A (ESPHome valve node) is the recommended path for
ESPHome-friendly installs because:

- The ESPHome YAML is declarative + version-controlled + has
  built-in watchdog timers for the relay outputs (if the
  ESP32 crashes, the relay state is reset to a known safe
  default — typically OFF for all valves).
- The valve-position feedback GPIO is wired directly into the
  same ESP32 that drives the valve coil (single point of
  wiring + single point of failure).
- The `binary_sensor.<node>_valve_*_position` entities are
  exposed directly by the ESPHome integration (no separate
  HA `template:` translation needed).

Path B (generic relay + HA template valve) is recommended when:

- The operator already owns a Shelly / Zooz / Aeotec relay and
  doesn't want to flash ESPHome.
- The operator wants the relay's existing GUI flow (Shelly's
  web UI, Z-Wave JS interview) for configuration.
- The valve-position feedback is already wired to a separate
  ESPHome node (used for the water-tanks Wave 3 #50 recipe's
  tank-level sensors) and the operator wants to share that
  ESPHome node's feedback GPIO for the valve-position
  feedback.

Both paths land on the same vendor-neutral contract layer via
the 17 `rc_water_valve_*` dashboard tiles.

## §6 RoamCore contract entities

The 17 `rc_water_valve_*` contract tiles + how the upstream
switch / valve template exposes them + translation helpers
needed for the derived aggregates:

- `switch.rc_water_valve_fresh_inlet_state` — fresh inlet
  valve control (operator-tunable open / closed). Path A:
  maps directly from `switch.<node>_valve_fresh_inlet`. Path
  B: maps from the HA `template:` switch that wraps the
  Shelly / Zooz / Aeotec relay.
- `switch.rc_water_valve_grey_drain_state` — grey drain
  valve control. Same pattern as fresh inlet.
- `switch.rc_water_valve_aux_tank_state` — aux tank switching
  valve control. Same pattern as fresh inlet.
- `binary_sensor.rc_water_valve_fresh_inlet_position` —
  fresh inlet valve position (TRUE = open). Path A: maps
  from `binary_sensor.<node>_valve_fresh_inlet_position`.
  Path B: maps from the limit switch / current sense
  binary_sensor.
- `binary_sensor.rc_water_valve_grey_drain_position` —
  grey drain valve position.
- `binary_sensor.rc_water_valve_aux_tank_position` — aux
  tank valve position.
- `binary_sensor.rc_water_valve_any_moving` — TRUE when at
  least one valve is currently in motion (a valve is
  transitioning between states). Derived via HA `template:`
  binary_sensor that ORs the position binary_sensor's
  "currently transitioning" state (the position binary_sensor
  is TRUE if the valve is in the open position AND the switch
  state was recently toggled; the "moving" aggregate combines
  these per-valve signals into a single "any valve is
  moving" tile). Also catches the §7.6 stuck-open detector
  (the valve is reported as open but the switch state is
  expected closed for > 5 min — the tile stays TRUE until the
  operator manually resets).
- `binary_sensor.rc_water_valve_auto_tank_switch_active` —
  TRUE when auto tank switching is currently engaged
  (`select.rc_water_valve_active_tank == auto` AND
  `select.rc_water_valve_mode == auto`). Derived via HA
  `template:` binary_sensor.
- `binary_sensor.rc_water_valve_leak_detected_lockout` —
  TRUE when the leak-detected safety interlock is currently
  holding all valves closed (cross-reference
  `binary_sensor.rc_water_leak_detected` from the water-tanks
  Wave 3 #50 recipe). Derived via HA `template:` binary_sensor.
- `binary_sensor.rc_water_valve_freeze_risk_lockout` — TRUE
  when the freeze-risk safety interlock is currently holding
  all valves closed (cross-reference
  `binary_sensor.rc_water_freeze_risk` from the water-tanks
  Wave 3 #50 recipe). Derived via HA `template:` binary_sensor.
- `select.rc_water_valve_active_tank` — operator-tunable
  active tank (`auto` / `primary` / `aux`). Default `auto`.
- `select.rc_water_valve_mode` — operator-tunable mode
  (`auto` / `manual_only` / `stealth_only` / `silent` /
  `disabled`). Default `auto`.
- `number.rc_water_valve_auto_close_grey_min` — operator-
  tunable auto-close-grey-minutes (default 15 min,
  configurable 5–60 min).
- `number.rc_water_valve_low_voltage_lockout_soc_pct` —
  operator-tunable low-voltage lockout SOC threshold
  (default 20 %, configurable 10–50 %).
- `binary_sensor.rc_water_valve_low_voltage_lockout` — TRUE
  when `sensor.rc_power_battery_soc` <
  `number.rc_water_valve_low_voltage_lockout_soc_pct` AND
  `binary_sensor.rc_power_shore_connected` == FALSE. Derived
  via HA `template:` binary_sensor.
- `button.rc_water_valve_open_all` — emergency open all
  valves button (gated by the §7 safety interlock override —
  if any safety interlock is engaged, the operator must first
  clear the interlock before the button will open all valves;
  the button does not bypass the §7.1 leak-detected lockout
  because opening valves during a leak would dump water onto
  the floor).
- `button.rc_water_valve_close_all` — emergency close all
  valves button (always allowed; this is the panic-stop).

## §7 Safety interlocks (MANDATORY before first use)

Six MANDATORY safety interlocks (operator MUST wire each one
before first use):

1. **Leak detected** — when ANY leak sensor (under-sink /
   pump-area / under-van) reports water, fire
   `binary_sensor.rc_water_valve_leak_detected_lockout` TRUE
   + close fresh inlet (so the leak isn't continuously fed
   from the fresh tank) + open grey drain (so the leak drips
   onto the floor / ground rather than pooling in the grey
   tank which then overflows onto the road). The cross-
   reference to `binary_sensor.rc_water_leak_detected` from
   the water-tanks Wave 3 #50 recipe is the same pattern.
   The cross-reference to the smoke-co-gas-sensors
   `connections/smoke-co-gas-sensors/` connection's §7.x
   pattern (loud siren + phone notification on any alarm)
   applies to the leak detected push notification escalation.

2. **Freeze risk** — when
   `sensor.rc_water_fresh_temperature_c` < 2 °C (cross-
   reference from the water-tanks Wave 3 #50 recipe), fire
   `binary_sensor.rc_water_valve_freeze_risk_lockout` TRUE +
   close ALL valves (frozen valve + frozen pipe + frozen
   fresh tank = cracked tank + burst pipes + valve body
   splits = van-killer). The cross-reference to the heated-
   floors `connections/heated-floors/` recipe §7.5 frost-
   protection automation + the hvac-basics
   `connections/hvac-basics/` recipe §7.1 frost-warning is
   the same pattern. The water-valves freeze_risk_lockout
   tile is the fourth pillar of the cold-weather safety
   story (frozen fresh water tank + frozen pipes + frozen
   valve body = cracked tank + burst pipes + valve body
   splits + no drinking water + no shower water).

3. **Low-voltage lockout** — don't open valves when
   `sensor.rc_power_battery_soc` <
   `number.rc_water_valve_low_voltage_lockout_soc_pct`
   (default 20 %) AND `binary_sensor.rc_power_shore_
   connected` == FALSE. The valve coils pull 0.5–2 A
   sustained during the switching pulse; below 20 % SOC
   that's enough to keep the battery bank from recovering
   overnight. Fire
   `binary_sensor.rc_water_valve_low_voltage_lockout` TRUE
   + disable all valve opens (the operator can still manually
   close valves for emergency shutdown via the
   `button.rc_water_valve_close_all` button). The cross-
   reference to the Victron `connections/victron/`
   connection's `sensor.rc_power_battery_soc` +
   `binary_sensor.rc_power_shore_connected` is the same
   pattern that the heated-floors + hvac-basics + happijac
   + water-tanks connections use for their low-voltage
   lockout interlocks.

4. **Auto-close grey drain** — close the grey drain valve N
   minutes (operator-tunable via
   `number.rc_water_valve_auto_close_grey_min`, default 15
   min) after open. Grey drain left open = grey tank
   overflows + grey sloshes onto the road while driving =
   bad. The operator-tunable threshold covers operator
   preferences (some operators want 5 min for quick fills,
   some want 30 min for slow drains; the recipe defaults to
   15 min). Use the HA `timer:` integration with a 15-min
   countdown that fires on the
   `switch.rc_water_valve_grey_drain_state` transition to
   ON; the timer fires a `switch.turn_off` to the grey drain
   valve.

5. **Mode-aware lockouts (Stealth / Sleep / Boost)** —
   - Stealth silent hours auto-mute warnings: when
     `select.rc_mode == stealth` (from the mode/automation-
     builder connection), mute the
     `binary_sensor.rc_water_valve_auto_tank_switch_active`
     notification (daytime-noise warning — the operator is
     asleep / not interacting with the van). The
     `binary_sensor.rc_water_valve_leak_detected_lockout` +
     `binary_sensor.rc_water_valve_freeze_risk_lockout` +
     `binary_sensor.rc_water_valve_low_voltage_lockout`
     tiles ALWAYS fire (van-life-or-death warnings — they
     bypass mode-aware suppression).
   - Sleep mode silent: when `select.rc_mode == sleep`,
     additionally mute ALL non-van-life-or-death warnings +
     drop the operator-tunable warning thresholds by 10 %.
   - Boost disable-mode-aware-lockouts: when
     `select.rc_mode == boost`, disable ALL the above mode-
     aware lockouts so the operator has full valve monitoring
     during service work / pre-trip packing.
   - The dashboard tile `select.rc_water_valve_mode` exposes
     the operator's local override (`auto` / `manual_only` /
     `stealth_only` / `silent` / `disabled`) on top of the
     mode-aware defaults.

6. **Valve stuck-open detector** — when the valve
   binary_sensor reports `valve_position == open` but the
   expected_position is `closed` for > 5 min, fire
   `binary_sensor.rc_water_valve_any_moving` TRUE
   (sustained-TRUE flag) + send a push notification. A
   stuck valve is bad in any direction — a stuck-open grey
   drain dumps grey onto the road; a stuck-closed fresh
   inlet means no water at the faucet. The recipe §8.6 +
   §7.6 walks through the operator's options (manual
   override via the dashboard tile + replace the valve if
   the issue persists).

## §8 Automations

Seven MANDATORY automations:

1. **Auto-switch-to-aux-tank when fresh < 5 %** — when
   `sensor.rc_water_fresh_level_pct` < 5 % (from the water-
   tanks Wave 3 #50 recipe) AND
   `select.rc_water_valve_active_tank` == `auto` AND
   `binary_sensor.rc_water_valve_freeze_risk_lockout` ==
   FALSE AND
   `binary_sensor.rc_water_valve_leak_detected_lockout` ==
   FALSE AND
   `binary_sensor.rc_water_valve_low_voltage_lockout` ==
   FALSE, fire a `switch.turn_on` to
   `switch.rc_water_valve_aux_tank_state` (open the aux tank
   valve) + send a push notification (the operator needs to
   plan to refill the fresh tank within the next 12 hours).

2. **Auto-switch-back-to-primary when aux < 5 %** — when
   `sensor.rc_water_fresh_level_pct` > 20 % (fresh has been
   refilled) AND
   `select.rc_water_valve_active_tank` == `auto`, fire a
   `switch.turn_off` to
   `switch.rc_water_valve_aux_tank_state` (close the aux
   tank valve) + send a push notification (the operator has
   refilled the fresh tank + the system has auto-switched
   back to primary).

3. **Auto-close-grey-after-N-min** — when
   `switch.rc_water_valve_grey_drain_state` transitions to
   ON, start a HA `timer:` countdown with
   `number.rc_water_valve_auto_close_grey_min` minutes
   (default 15). When the timer fires, send a
   `switch.turn_off` to
   `switch.rc_water_valve_grey_drain_state` (close the grey
   drain valve) + send a push notification if the operator
   hasn't manually opened another valve since (so the
   operator knows the auto-close fired).

4. **Leak-detected-close-fresh-open-grey** — when
   `binary_sensor.rc_water_leak_detected` (from the water-
   tanks Wave 3 #50 recipe) transitions to TRUE, fire a
   `switch.turn_off` to
   `switch.rc_water_valve_fresh_inlet_state` (close fresh
   inlet) + fire a `switch.turn_on` to
   `switch.rc_water_valve_grey_drain_state` (open grey
   drain) + send a HIGH-PRIORITY push notification. The
   cross-reference to the smoke-co-gas-sensors
   `connections/smoke-co-gas-sensors/` recipe's §7.1 "loud
   siren + phone notification" is the same pattern.

5. **Freeze-risk-close-all** — when
   `binary_sensor.rc_water_freeze_risk` (from the water-
   tanks Wave 3 #50 recipe) transitions to TRUE, fire a
   `switch.turn_off` to all three valve state switches +
   send a HIGH-PRIORITY push notification. The cross-
   reference to the heated-floors
   `connections/heated-floors/` recipe §7.5 frost-
   protection automation + the hvac-basics
   `connections/hvac-basics/` recipe §7.1 frost-warning is
   the same pattern.

6. **Low-voltage-lockout** — when
   `binary_sensor.rc_water_valve_low_voltage_lockout`
   transitions to TRUE, fire a `switch.turn_off` to any
   currently-open valve state switches (close any open
   valves to save battery current) + send a HIGH-PRIORITY
   push notification (the operator needs to find shore power
   before the battery bank dies completely). The cross-
   reference to the Victron `connections/victron/` recipe is
   the same pattern that the heated-floors + hvac-basics +
   happijac + water-tanks connections use for their low-
   voltage lockout interlocks.

7. **Mode-aware scheduling** — when
   `select.rc_water_valve_mode == stealth_only`, mute the
   `binary_sensor.rc_water_valve_auto_tank_switch_active`
   notification. When
   `select.rc_water_valve_mode == silent`, mute ALL warnings
   except
   `binary_sensor.rc_water_valve_leak_detected_lockout` +
   `binary_sensor.rc_water_valve_freeze_risk_lockout` +
   `binary_sensor.rc_water_valve_low_voltage_lockout`. When
   `select.rc_water_valve_mode == disabled`, disable ALL
   monitoring (the operator has intentionally drained the
   tanks). The `auto` mode enables all warnings + auto tank
   switching; the `manual_only` mode disables auto tank
   switching but keeps all warnings.

The full automation YAML for each is in the recipe
`homeassistant/automations/rc_water_valve_*.yaml` files
(operator wires these manually until tier-a promotion lands).

## §9 Troubleshooting

Eight troubleshooting entries:

1. **Valve not responding** — coil polarity wrong or driver
   voltage wrong or wiring fault. For Path A: check the relay
   module's wiring (the relay's COM terminal connects to the
   valve coil's +V terminal; the relay's NO terminal connects
   to the valve coil's -V terminal). For Path B: check the
   Shelly / Zooz / Aeotec relay's wiring (similar to Path A).
   Solution: verify the relay's switched output is reaching
   the valve coil with a multimeter; reverse the wiring if
   the polarity is wrong.

2. **Valve stuck-open** — mechanical obstruction or lime
   buildup or replace valve. The valve-position binary_sensor
   reports `position == open` but the switch state has been
   turned OFF for > 5 min (the §7.6 stuck-open detector
   triggers). Solution: manually close the valve via the
   dashboard tile (the operator can override the
   §7.6 stuck-open detector flag); if the issue persists,
   check for lime buildup in the valve body (common in vans
   with hard water) + replace the valve if the buildup can't
   be cleared.

3. **Auto-switch keeps toggling** — threshold hysteresis too
   tight. The auto-switch-to-aux-tank fires when fresh < 5 %,
   but the auto-switch-back-to-primary fires when fresh > 20
   %. If the fresh tank is hovering around 5 % (e.g. the
   operator is running a shower while the aux tank valve is
   open), the system may toggle back and forth rapidly.
   Solution: increase the hysteresis to fresh < 3 % for aux +
   fresh > 25 % for primary (or whatever values match the
   operator's usage pattern).

4. **Freeze lockout stuck on after charging** — cross-check
   Victron SOC. The §7.2 freeze-risk lockout fires when
   `sensor.rc_water_fresh_temperature_c` < 2 °C; the lockout
   does NOT auto-release when the temperature rises above 2
   °C — the operator must manually clear the lockout via the
   dashboard tile. Solution: verify the temperature probe is
   reading correctly (cross-check the Victron `connections/
   victron/` recipe's battery temperature sensor); if the
   probe is correct, manually clear the lockout via the
   dashboard tile.

5. **Shelly not discovered** — mDNS / IGMP snooping on the
   LAN switch. For Path B: the Shelly 1 / Shelly Plus 1 uses
   mDNS for auto-discovery; some managed switches have IGMP
   snooping enabled which blocks mDNS multicast. Solution:
   enable mDNS reflector on the LAN switch OR manually add
   the Shelly via the Shelly integration's "Add device by IP"
   flow.

6. **ESPHome device offline** — check Wi-Fi + USB-C power.
   For Path A: the ESP32 must have stable 5 V via USB-C (not
   the van's 12 V / 24 V distribution without a regulator).
   Solution: check the USB-C cable + the Wi-Fi signal
   strength. For Path B: the Shelly / Zooz / Aeotec relay
   must have stable 12 V / 24 V supply. Solution: check the
   12 V / 24 V fuse + the relay's status LED.

7. **Leak lockout won't release** — must clear the leak
   first + manual override. The §7.1 leak-detected lockout
   fires when
   `binary_sensor.rc_water_leak_detected` (from the water-
   tanks Wave 3 #50 recipe) transitions to TRUE; the lockout
   does NOT auto-release when the leak sensor dries out — the
   operator must manually clear the lockout via the dashboard
   tile AFTER addressing the leak (drying the leak sensor +
   fixing the source of the leak). Solution: dry the leak
   sensor thoroughly + fix the leak source + manually clear
   the lockout via the dashboard tile.

8. **Grey valve auto-close not firing** — auto-close-grey-min
   set too high. The
   `number.rc_water_valve_auto_close_grey_min` timer fires
   after the configured minutes; if the operator has set the
   timer to 60 min (the maximum), the grey valve stays open
   for 60 min after opening. Solution: reduce
   `number.rc_water_valve_auto_close_grey_min` to 15 min
   (the default) or whatever value matches the operator's
   grey tank capacity + usage pattern.

## §10 Privacy

No telemetry. Everything is local. The esphome / shelly / zooz /
aeotec / template integrations are local; no cloud call home.

The valve state + valve position feedback produce no telemetry
beyond the local relay state. The safety interlocks are local —
no telemetry is sent to any cloud.

The push notification for the leak detected + freeze risk +
low-voltage lockout + valve stuck-open warnings uses the
operator's existing HA Core push notification channel — that's
the operator's choice; RoamCore does not add any push
notification channel. The bluetooth-wifi-presence cross-
reference for the leak detected push notification escalation
uses the operator's existing presence detection — no additional
tracking is added.

## §11 Promoting to tier-a

What would need to happen to promote this connection from
tier-b to tier-a:

- A real electronic valve bench on the CI rig: a 12 V / 24 V
  electrically-actuated valve + a safe driver + an ESP32 +
  a relay + a tank-level sensor, all wired together in a
  controlled environment + a way to simulate the leak /
  freeze / low-voltage trigger conditions.
- A canonical RoamCore-owned `config_flow.py` that walks the
  operator through choosing Path A vs Path B + declaring the
  valve GPIO pins + the valve coil polarity + (for motorized
  ball valves) the DPDT relay configuration.
- Integration tests that assert a 0 % → 100 % level change
  on the upstream tank-level sensor triggers the right
  `binary_sensor.rc_water_valve_auto_tank_switch_active`
  transition + the right auto-switch-to-aux-tank automation
  fires.
- Integration tests that assert the §7.1 leak detected
  automation closes fresh inlet + opens grey drain + sends a
  high-priority push when the leak sensor is triggered.
- Integration tests that assert the §7.2 freeze risk
  automation closes all valves when
  `sensor.rc_water_fresh_temperature_c` < 2 °C.
- Integration tests that assert the §7.3 low-voltage lockout
  automation closes any open valves when
  `sensor.rc_power_battery_soc` < threshold AND shore
  disconnected.
- Integration tests that assert the §7.4 auto-close-grey
  automation closes the grey drain valve after the
  configured minutes.
- Flip `tier_requirements` to include `working_config_flow` +
  `integration_test_passes` + `no_manual_yaml_required` +
  `safety_automations_hard_enforced_in_roamcore_code`.

Until those ship, this connection is tier-b even though the
upstream esphome / shelly / template integrations have their
own GUI flows. The recipe is sound but we cannot claim one-
tap automation.