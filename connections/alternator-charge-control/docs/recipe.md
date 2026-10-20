# Alternator charge control — full howto (RoamCore vendor-neutral alternator charge umbrella for HA — Wakespeed / smart regulator / field relay / read-only)

This recipe is the canonical howto for the
`connections/alternator-charge-control/` tier-b recipe
connection (backlog row #307 — promoted from the legacy
tier-c stub
`docs/catalog/power/alternator-charge-control-wakespeed.md`).
It walks the operator through setting up ONE of the FOUR
operator-pickable alternator charge paths (Path A DC-DC-
charger-linked regulator + Path B vendor-MQTT-bridged smart
regulator + Path C relay / GPIO switch on the alternator
field wire + Path D read-only ignition-signal-only + no
control) + the 8 `rc_power_alternator_*` contract tiles +
the SIX §8 automations.

The recipe assumes the operator has at least 1 charging
source (an alternator-side regulator OR a relay / GPIO
switch on the field wire OR a read-only ignition signal) +
the operator's choice of upstream integration wired into
HA. If the operator has no alternator-side regulator OR no
field relay, the recipe starts at §2 Prerequisites + walks
through the alternator-side install prerequisites before
the path wiring.

## §1 What is alternator charge control in RoamCore?

Alternator charge control — vendor-neutral umbrella for
Wakespeed / Balmar / Sterling / Renogy / REDARC / EP-Power
/ ARCO / OEM smart alternator regulators — is the canonical
"should the alternator be charging the house battery right
now + is it actually charging + did anything go wrong"
answer for vans. The umbrella positions alternator charge
control as a power-category concern (not a scene + not a
fridge-load concern + not a remote-access concern) because
the alternator is the primary charging source for vans with
no solar or limited solar — the umbrella surfaces the
alternator's state + safety interlocks (fault / temperature
/ SOC / mode) as the canonical contract layer that the
rest of RoamCore's power-side automations can rely on.

The umbrella publishes the 8 `rc_power_alternator_*`
contract tiles (vendor-neutral — no Wakespeed / Balmar /
Sterling / Renogy / REDARC / EP-Power / ARCO / OEM /
regulator / B2B / BCDC / MC-618 / WS500 / WS Link /
Smartlink / BT-2 / RedVision / EP Link / BMS Link / Zeus
/ NMEA 2000 / CAN / CANbus / J1939 / LIN / D+ / Vsense /
12V / 24V / lithium / LiFePO4 / AGM / flooded / gel names
leak into the tile ids). The tiles are:

- `binary_sensor.rc_power_alternator_charging_enabled` —
  the AND gate (TRUE iff the alternator is allowed to
  charge right now — combines `select.rc_power_alternator_
  charge_mode` != off + ignition on + battery SOC >
  threshold + temperature within range + `select.rc_mode`
  not suppressed + fault clear). The tile is a `template:`
  binary_sensor (since 2022.x) that derives from the
  upstream switch + sensor + binary_sensor family. The
  tile is the operator-facing "is the alternator allowed
  to charge?" indicator; the §8.1 ignition-on enable +
  §8.2 SOC-low boost + §8.5 protect_battery mode + §8.6
  fault-block automations read from + write to this tile.

- `select.rc_power_alternator_charge_mode` — the
  operator's chosen charge mode (one of `off` / `auto` /
  `boost` / `float` / `desulfation` / `stealth` /
  `protect_battery`). The tile is a `select:` domain
  entity (since 2022.x) that maps to the upstream `switch.*`
  enable/disable + the upstream `select.*` mode (if the
  vendor exposes one) + the temperature-compensation
  override (for cold / hot batteries). The tile is the
  operator-facing "what mode is the alternator in?"
  affordance; the §8.1 / §8.2 / §8.3 / §8.4 / §8.5 / §8.6
  automations read from this tile before calling the
  upstream services.

- `sensor.rc_power_alternator_target_voltage_v` — the
  regulator's voltage setpoint (V; the temperature-
  compensation may have lowered it from the operator's
  chosen nominal voltage). The tile is a `template:`
  sensor (since 2022.x) that derives from the upstream
  `sensor.*` target_voltage entity (when present) + the
  operator's chosen nominal voltage setpoint (an
  `input_number.rc_power_alternator_target_voltage_nominal_v`,
  default 14.4 V for a 12 V system or 28.8 V for a 24 V
  system) + the temperature-compensation curve. The tile
  is the operator-facing "what voltage is the regulator
  targeting?" indicator; the §8.3 battery-cold temperature
  compensation automation lowers this value.

- `sensor.rc_power_alternator_charge_current_a` — the
  current accepted by the house battery bank during
  alternator charging (A). The tile is a `template:`
  sensor (since 2022.x) that derives from the upstream
  regulator's current-sense input (`sensor.alt_charge_
  current_a` for Path B / the regulator's `sensor.*`
  family) OR the Victron `sensor.rc_power_battery_current_a`
  for Path C (the field-relay path has no regulator-side
  current sensor; the charge current is the battery-side
  current). The tile is the operator-facing "how much
  current is the alternator pushing into the house bank?"
  indicator; the §8.1 ignition-on enable + §8.2 SOC-low
  boost automations cross-reference this tile when
  deciding whether to enable / boost charging.

- `binary_sensor.rc_power_alternator_temp_compensation_active`
  — the cold / hot battery gate (TRUE iff the temperature
  probe reads cold (< 0°C) OR hot (> 45°C) AND the
  regulator's temperature-compensation curve is actively
  lowering the target voltage). The tile is a `template:`
  binary_sensor (since 2022.x) that derives from the
  upstream temperature probe (`sensor.battery_temp_c` for
  Path A / Path B / Path C / Path D) + the operator's
  chosen nominal temperature (default 25°C) + the
  temperature-compensation curve (-3 mV/°C/cell for lead-
  acid; -5 mV/°C/cell for LiFePO4 — the operator picks
  one). The tile is the operator-facing "is the
  regulator's temperature-compensation curve actively
  lowering the target voltage?" indicator; the §8.3
  battery-cold temperature-compensation automation reads
  from this tile.

- `binary_sensor.rc_power_alternator_fault` — the
  regulator's fault trip gate (TRUE iff the regulator
  reports over-temp / over-voltage / communication lost /
  BMS lockout). The tile is a `template:` binary_sensor
  (since 2022.x) that derives from the upstream regulator's
  fault state (`binary_sensor.alt_fault` for Path A / Path
  B / Path C / Path D). The tile is the operator-facing
  "is the regulator faulting?" indicator; the §8.6
  fault-block automation reads from this tile + calls
  the upstream `switch.turn_off` service when the regulator
  reports a fault.

- `sensor.rc_power_alternator_last_trigger_reason` —
  the reason the alternator was last enabled (one of
  `manual` / `ignition_on` / `soc_low` / `battery_cold`
  / `boost` / `desulfation` / `stealth_suppressed` /
  `fault_blocked`). The tile is an `input_text:`
  domain entity (since 2022.x) that the operator's
  automations write to before calling the
  `switch.turn_on` service. The tile is the
  operator-facing "why was the alternator last enabled?"
  indicator.

- `button.rc_power_alternator_manual_override` — the
  manual override (the operator can force alternator
  charging ON for a configurable duration from the
  dashboard, regardless of the auto-policy). The button
  is an `input_button:` domain entity (since 2022.x) that
  fires a configurable-duration `switch.turn_on` +
  a timer to call `switch.turn_off` after the operator's
  chosen duration. The tile is the operator-facing "force
  the alternator to charge now" affordance; the §8.7
  manual override automation handles the timer.

The 8 contract tiles are vendor-neutral — no vendor /
hardware / protocol / integration names leak into the tile
ids. The umbrella uses the `rc_power_alternator_*` prefix
because `alternator` is the canonical vendor-neutral
alternator subsystem (the umbrella for the FOUR operator-
pickable paths); the `alternator` subsystem under the
existing `power` subsystem was added to
`docs/reference/rc-entity-naming.md` by this slice.

## §2 Prerequisites

Before installing the alternator charge control
connection, the operator needs:

- **At least 1 charging source installed.** The operator
  needs at least 1 of:
  - **Smart alternator regulator linked to a Victron /
    Renogy / REDARC / Sterling / Balmar / EP-Power DC-DC
    charger** — Path A. The DC-DC charger exposes the
    upstream `switch.*` (charge enable) + `sensor.*`
    (voltage + current + temperature) + `binary_sensor.*`
    (fault state) entities via the vendor's integration
    (the `victron` integration for Path A1; the `mqtt`
    integration for Path A2).
  - **Generic smart alternator regulator exposed over MQTT
    by the vendor's bridge** — Path B. The regulator
    (Wakespeed WS500 / Balmar MC-618 / Sterling
    Regulated Advanced Alternator-to-Battery charger /
    Renogy Battery-to-Battery / REDARC BCDC / EP-Power
    B2B / ARCO Zeus / OEM CAN-j1939 regulator) ships
    with a Bluetooth / Wi-Fi / CAN bridge (Wakespeed's
    WS Link / Sterling's BMS Link / Balmar's Smartlink /
    Renogy's BT-2 / REDARC's RedVision / EP-Power's
    EP Link / a Signal K gateway on the boat's NMEA
    2000 backbone). The bridge exposes the regulator's
    enable/disable + target voltage + charge current +
    battery temperature + fault state as a `switch.*` +
    `sensor.*` + `binary_sensor.*` + `number.*` +
    `select.*` family via the HA core `mqtt` integration.
  - **A relay / GPIO switch on the alternator field wire**
    — Path C. The relay (Shelly 1 / Shelly Plus 1 / Zooz
    ZEN17 / Aeotec Nano Switch OR a GPIO relay driven by
    an ESPHome / Tasmota node) is wired to the
    alternator's field excitation wire. Turning the relay
    off interrupts the alternator's field excitation + the
    alternator stops charging. The relay surfaces as a
    `binary_switch.*` (Shelly) OR `switch.*` (ESPHome /
    Tasmota) entity.
  - **A read-only ignition signal** — Path D. The
    operator doesn't want to control the alternator at
    all — just knows when the engine is running via
    `binary_sensor.rc_vehicle_engine_running` from the
    leveling / mode connection slices OR a GPIO on an
    ESPHome node + a voltage divider on the alternator's
    D+ / IGN wire.

- **The operator's choice of upstream integration wired
  into HA.** The operator needs at least 1 of:
  - **HA core `mqtt` integration** (since 2022.x) —
    the canonical Path A2 + Path B integrator. Exposes a
    GUI flow for the operator to configure the
    regulator's / DC-DC charger's / vendor bridge's
    MQTT topic.
  - **HA core Shelly integration** (since 2022.x) —
    the canonical Path C1 relay integrator. Exposes a
    GUI flow for the operator to add the Shelly 1 /
    Shelly Plus 1 to HA + view the resulting
    `binary_switch.*` entity.
  - **HA core `victron` integration** (since 2022.x) —
    the canonical Path A1 DC-DC-charger-integrated-
    with-Victron integrator. Exposes a GUI flow for the
    operator to add the Victron Cerbo GX to HA + view
    the resulting `switch.*` + `sensor.*` + `binary_
    sensor.*` entities on the DC-DC charger.
  - **HA core `template:` switch + sensor +
    binary_sensor wrappers** (since 2022.x) — the
    canonical contract-layer wrapping. Wraps any
    upstream `switch.*` + `sensor.*` + `binary_sensor.*`
    entities into derived entities that expose the
    standard contract.
  - **HA core `input_boolean` + `input_text` +
    `input_number` + `input_select` + `input_button`
    helpers** (since 2022.x) — the canonical operator-
    facing affordances. Used for the
    `select.rc_power_alternator_charge_mode` +
    `button.rc_power_alternator_manual_override` +
    `sensor.rc_power_alternator_last_trigger_reason`
    tiles.

- **An ignition signal** — REQUIRED for §8.1 ignition-
  on enable. The operator needs:
  - `binary_sensor.rc_vehicle_engine_running` from the
    leveling / mode connection slices (preferred — the
    mode connection exposes this tile via `binary_sensor
    .rc_mode_engine_running` cross-referencing the
    leveling connection's IMU + drive-state signal).
  - OR a GPIO on an ESPHome node + a voltage divider
    on the alternator's D+ / IGN wire + an ESPHome
    analog input (`binary_sensor.alt_engine_running`).
  - OR the operator's Victron `binary_sensor.rc_power_
    engine_running` if the operator's Cerbo GX is wired
    to the engine's ignition.

- **A battery temperature probe** — REQUIRED for §8.3
  battery-cold temperature-compensation. The operator
  needs:
  - A Z-Wave / Zigbee / 1-Wire / ESPHome analog-input
    temperature probe attached to the house battery
    bank (a common choice: a DS18B20 1-Wire probe with
    a Shelly 1 / Shelly Plus 1 Uni / Shelly Plus AddOn
    + a 4.7 kΩ pullup resistor; a Zigbee temperature
    probe from the Aqara / Sonoff / Nous families; an
    ESP32 with a thermistor + ESPHome firmware).
  - OR the operator's Victron `sensor.rc_power_battery_
    temperature_c` if the operator's Cerbo GX has a
    battery temperature probe attached.

- **Victron battery SOC + battery current from the
  Victron `connections/victron/` recipe** —
  REQUIRED for §8.2 SOC-low boost + §8.5 protect_battery
  mode. The operator needs:
  - `sensor.rc_power_battery_soc` — the SOC percentage
    from the Victron battery monitor.
  - `sensor.rc_power_battery_current_a` — the current
    flowing into / out of the house battery bank
    (used for §8.1 ignition-on enable's confirmation
    that charging is actually flowing).

- **`select.rc_mode` from the mode `connections/mode/`
  recipe** — REQUIRED for §8.4 mode-aware Stealth /
  Sleep suppressions. The operator needs:
  - The mode connection's `select.rc_mode` tile set
    to one of `home` / `away` / `stealth` / `sleep` /
    `off` (the operator's chosen mode drives the §8.4
    Stealth / Sleep suppressions).

- **A `binary_sensor.rc_vehicle_engine_running` from
  the leveling / mode connection slices** — REQUIRED for
  §8.1 ignition-on enable. The operator needs:
  - The leveling connection's IMU-based pitch / roll /
    drive-state signal (derives "is the engine running"
    from the IMU + vibration + GPS speed + alternator
    field voltage).
  - OR the mode connection's `binary_sensor.rc_mode_
    engine_running` cross-reference.

- **An always-on HA instance** (the RoamCore canonical
  setup).

## §3 Path A — DC-DC-charger-linked regulator

Path A covers TWO sub-flavors: Path A1 Victron Cerbo GX +
DC-DC charger via the `victron` integration, Path A2
Renogy / REDARC / EP-Power / Sterling / Balmar DC-DC
charger via the `mqtt` integration. The operator picks
ONE sub-flavor based on the operator's existing DC-DC
charger + integration wiring.

### §3.1 Path A1 — Victron Cerbo GX + DC-DC charger

1. **Install the Victron Cerbo GX hardware.** The
   operator installs the chosen Cerbo GX (Cerbo GX MK2
   is current; the older Cerbo GX is still supported)
   per the manufacturer instructions. The Cerbo GX
   connects to the DC-DC charger via the Victron
   VE.Can / VE.Bus network.

2. **Pair the DC-DC charger with the Cerbo GX.** The
   operator follows the Victron pairing instructions to
   add the DC-DC charger to the Cerbo GX's device list.
   The DC-DC charger exposes its enable/disable +
   target voltage + charge current + battery
   temperature + fault state via the Cerbo GX's
   `switch.*` + `sensor.*` + `binary_sensor.*` family.

3. **Install the HA core `victron` integration.** The
   operator uses the HA core `victron` integration's
   GUI flow (since 2022.x — exposes a GUI flow for the
   operator to add the Cerbo GX to HA + view the
   resulting entities). The operator opens Settings →
   Devices & Services → Victron → Configure → enters
   the Cerbo GX's IP address + Modbus TCP credentials
   → verifies the DC-DC charger appears as a device.

4. **Verify the upstream `switch.*` + `sensor.*` +
   `binary_sensor.*` entities exist.** The `victron`
   integration surfaces the DC-DC charger as a
   `switch.*` entity (charge enable) + a `sensor.*`
   entity (target voltage + charge current + battery
   temperature) + a `binary_sensor.*` entity (fault
   state). The umbrella §7 walks through the
   `template:` wrappers that synthesize the
   `rc_power_alternator_*` contract tiles.

5. **Configure the operator-facing
   `binary_sensor.rc_power_alternator_charging_enabled`
   contract tile.** The operator creates a `template:`
   binary_sensor (since 2022.x) that ANDs the upstream
   `switch.*` (charge enable) + ignition on + battery
   SOC > threshold + temperature within range + mode
   not suppressed + fault clear. The recipe §7 walks
   through the template wiring.

6. **Configure `select.rc_power_alternator_charge_mode`
   to `auto`.** The operator sets the charge mode to
   `auto` (the default starting mode; the §8.1 + §8.2
   automations take over from here).

7. **Wire the SIX §8 automations** (ignition-on
   enable + SOC-low boost + battery-cold temperature-
   compensation + mode-aware Stealth / Sleep
   suppressions + protect_battery mode + fault-block).

8. **Verify the alternator charges when the engine
   starts.** The operator turns on the engine + the
   §8.1 ignition-on enable automation fires + the
   `binary_sensor.rc_power_alternator_charging_enabled`
   flips to TRUE + the operator verifies
   `sensor.rc_power_alternator_charge_current_a`
   reflects the upstream `sensor.*` charge_current.

### §3.2 Path A2 — Renogy / REDARC / EP-Power / Sterling / Balmar DC-DC charger via `mqtt`

1. **Pair the DC-DC charger with the vendor's
   Bluetooth-to-MQTT bridge.** The operator follows
   the vendor's pairing instructions (Renogy BT-2 /
   REDARC RedVision / EP-Power EP Link / Sterling BMS
   Link / Balmar Smartlink).

2. **Install the HA core `mqtt` integration.** The
   operator uses the HA core `mqtt` integration's GUI
   flow (since 2022.x — exposes a GUI flow for the
   operator to add the bridge's MQTT broker credentials
   + topics to HA). The operator enters the bridge's
   MQTT broker address + port + credentials + the
   topic prefix (default `roamcore/dc_dc_charger/`
   for Renogy; `roamcore/redvision/` for REDARC; etc.)
   → verifies the upstream `switch.*` + `sensor.*` +
   `binary_sensor.*` entities appear.

3. **Verify the upstream `switch.*` + `sensor.*` +
   `binary_sensor.*` entities exist.** The bridge
   surfaces the DC-DC charger as a `switch.*` entity
   (charge enable) + a `sensor.*` entity (target
   voltage + charge current + battery temperature) +
   a `binary_sensor.*` entity (fault state).

4. **Configure the operator-facing contract tiles**
   (same as Path A1 §3.1 steps 5–8).

5. **Verify the alternator charges when the engine
   starts** (same as Path A1).

## §4 Path B — Vendor MQTT bridge (Wakespeed WS500 / Balmar MC-618 / Sterling / Renogy / REDARC / EP-Power / ARCO)

Path B is the canonical "use the upstream vendor's MQTT
bridge" path for operators whose regulator ships with a
Bluetooth / Wi-Fi / CAN-to-MQTT bridge.

### §4.1 Pairing the regulator with the vendor's bridge

1. **Install the regulator hardware.** The operator
   installs the chosen regulator (Wakespeed WS500 /
   Balmar MC-618 / Sterling Regulated Advanced
   Alternator-to-Battery charger / Renogy Battery-to-
   Battery / REDARC BCDC / EP-Power B2B / ARCO Zeus /
   OEM CAN-j1939 regulator) per the manufacturer
   instructions. The regulator is wired into the
   alternator's field wire + the alternator's B+ /
   battery-sense wire + the house battery bank + the
   vehicle's CAN bus (if the regulator supports CAN).

2. **Pair the regulator with the vendor's bridge.**
   The operator follows the vendor's pairing
   instructions to pair the regulator with the bridge
   (Wakespeed's WS Link / Sterling's BMS Link /
   Balmar's Smartlink / Renogy's BT-2 / REDARC's
   RedVision / EP-Power's EP Link / ARCO's Zeus app
   / a Signal K gateway on the boat's NMEA 2000
   backbone).

3. **Configure the bridge's MQTT bridge.** The
   operator opens the bridge's web UI (Wakespeed's WS
   Link web UI / Renogy BT-2 web UI / REDARC
   RedVision app / etc.) → Configures the bridge to
   publish the regulator's enable/disable + target
   voltage + charge current + battery temperature +
   fault state as MQTT topics on a local MQTT broker
   (Mosquitto OR the HA add-on Mosquitto broker).

### §4.2 Wiring the regulator's MQTT topics into HA

1. **Install the HA core `mqtt` integration** (if
   not already installed for other reasons). The
   operator uses the HA core `mqtt` integration's GUI
   flow (since 2022.x).

2. **Configure the bridge's MQTT topics in HA.** The
   operator opens Settings → Devices & Services →
   MQTT → Configure → enters the MQTT broker's
   credentials + the topic prefix. The integration
   auto-discovers the regulator as a `switch.*` +
   `sensor.*` + `binary_sensor.*` + `number.*` +
   `select.*` family.

3. **Verify the upstream entities exist.** The HA core
   `mqtt` integration surfaces the regulator as a
   `switch.*` entity (charge enable, e.g.
   `switch.wakespeed_charge_enable`) + a `sensor.*`
   entity (target voltage, e.g. `sensor.wakespeed_
   target_voltage_v`) + a `sensor.*` entity (charge
   current, e.g. `sensor.wakespeed_charge_current_a`)
   + a `sensor.*` entity (battery temperature, e.g.
   `sensor.wakespeed_battery_temp_c`) + a
   `binary_sensor.*` entity (fault state, e.g.
   `binary_sensor.wakespeed_fault`). The exact
   entity ids vary by vendor — the recipe §7 walks
   through the template wrappers that rename them to
   the `rc_power_alternator_*` contract layer.

4. **Configure the operator-facing contract tiles**
   (same as Path A1 §3.1 steps 5–8).

5. **Verify the alternator charges when the engine
   starts** (same as Path A1).

## §5 Path C — Relay / GPIO switch on the alternator field wire

Path C covers TWO sub-flavors: Path C1 Shelly 1 / Shelly
Plus 1 wired to the alternator's field excitation wire,
Path C2 ESPHome / Tasmota GPIO relay driven by an ESP32 /
ESP8266 node + the upstream ESPHome / Tasmota integration.

### §5.1 Path C1 — Shelly 1 / Shelly Plus 1 wired to the alternator's field wire

1. **Install the Shelly 1 / Shelly Plus 1 hardware.**
   The operator installs the Shelly 1 / Shelly Plus 1
   relay per the manufacturer instructions. The relay
   is wired in series with the alternator's field
   excitation wire (the operator's alternator's
   internal regulator is bypassed OR the operator's
   alternator is externally regulated; the field wire
   is the alternator's input from the ignition
   switch + the alternator's internal regulator).

2. **Add the Shelly 1 / Shelly Plus 1 to the HA
   server.** The operator uses the HA core Shelly
   integration's GUI flow (since 2022.x). The Shelly
   surfaces as a `binary_switch.*` entity.

3. **Create a `template:` switch wrapping the relay
   state into a virtual `switch.*` entity.** The
   operator creates a `template:` switch (since
   2022.x) that wraps the upstream `binary_switch.*`
   into a virtual `switch.*` entity with the standard
   contract.

4. **Verify the upstream `switch.*` entity exists.**
   The `template:` switch surfaces as a `switch.*`
   entity (e.g. `switch.alt_field_relay`).

5. **Configure the operator-facing contract tiles**
   (same as Path A1 §3.1 steps 5–8). Note: Path C
   has no upstream target_voltage sensor — the
   `sensor.rc_power_alternator_target_voltage_v`
   tile is hard-coded to the operator's chosen
   nominal voltage setpoint.

6. **Wire the SIX §8 automations** (same as Path A1).
   Note: Path C has no upstream fault sensor —
   `binary_sensor.rc_power_alternator_fault` is
   derived from the upstream `binary_sensor` (if
   any) + a derived fault (e.g. upstream
   `sensor.rc_power_battery_voltage_v` > 16 V for
   > 30 seconds suggests the regulator is over-
   charging).

7. **Verify the alternator charges when the engine
   starts.** The operator turns on the engine + the
   §8.1 ignition-on enable automation fires + the
   `binary_sensor.rc_power_alternator_charging_
   enabled` flips to TRUE + verifies the relay is
   closed + verifies
   `sensor.rc_power_alternator_charge_current_a`
   reflects the Victron
   `sensor.rc_power_battery_current_a`.

### §5.2 Path C2 — ESPHome / Tasmota GPIO relay driven by an ESP32 / ESP8266

1. **Flash the ESP32 / ESP8266 with ESPHome / Tasmota.**
   The operator flashes the ESPHome / Tasmota firmware
   onto the ESP32 / ESP8266 per the upstream instructions
   (https://esphome.io/ for ESPHome;
   https://tasmota.github.io/docs/ for Tasmota).

2. **Configure the GPIO pin for the relay output.** The
   operator configures the GPIO pin in the ESPHome /
   Tasmota firmware (Pin 12 is a common choice on
   ESP32; Pin 5 / Pin 12 / Pin 13 on ESP8266). The
   relay is wired between the GPIO pin and ground.

3. **Wire the relay to the alternator's field
   excitation wire.** The operator wires the relay in
   series with the alternator's field excitation wire
   (same as Path C1).

4. **Add the ESP32 / ESP8266 to HA.** The operator
   uses the ESPHome integration's GUI flow (since
   2022.x — surfaces as a `switch.*` entity) OR the
   HA core `mqtt` integration (since 2022.x — for
   Tasmota-flashed devices).

5. **Configure the operator-facing contract tiles**
   (same as Path C1 §5.1 steps 5–6).

6. **Verify the alternator charges when the engine
   starts** (same as Path C1).

## §6 Path D — Read-only ignition-signal-only + no control

Path D is the canonical "I just want to know when the
engine is running; I don't want to control the alternator"
path. The umbrella surfaces a single "should we be
charging now?" advisory tile (`binary_sensor.rc_power_
alternator_charging_enabled` derived from ignition on +
battery SOC > threshold + temperature within range +
mode not suppressed + operator's chosen charge_mode)
without any `switch.*` + `sensor.*` upstream entities
other than the ignition signal.

### §6.1 Wiring the ignition signal

1. **Pair the ignition signal source.** The operator
   uses an upstream `binary_sensor.rc_vehicle_engine_
   running` from the leveling / mode connection
   slices (preferred — the mode connection exposes
   this tile). Alternatively, the operator wires a
   GPIO on an ESPHome node + a voltage divider on the
   alternator's D+ / IGN wire + an ESPHome analog
   input (`binary_sensor.alt_engine_running`).

2. **Configure `select.rc_power_alternator_charge_mode`
   to `auto`.** The operator sets the charge mode to
   `auto` (Path D only supports `auto` / `off`; the
   other modes require a regulator that Path D doesn't
   have).

3. **Wire the SIX §8 automations.** Path D doesn't
   call any upstream switch.turn_off / switch.turn_on
   services — the `binary_sensor.rc_power_alternator_
   charging_enabled` tile is purely advisory (the
   operator's van has no regulator + no relay to
   control). The §8 automations still fire + write
   to `sensor.rc_power_alternator_last_trigger_reason`
   + the operator sees the advisory in the dashboard.

4. **Verify the advisory tile fires when the engine
   starts.** The operator turns on the engine + the
   §8.1 ignition-on enable automation fires + the
   `binary_sensor.rc_power_alternator_charging_
   enabled` flips to TRUE + verifies the operator's
   Victron `sensor.rc_power_battery_current_a`
   shows positive current flowing into the house
   battery bank (the alternator is charging; the
   §8 automation is just logging the fact).

## §7 RoamCore contract entities

The 8 `rc_power_alternator_*` contract tiles are vendor-
neutral — no vendor / hardware / protocol / integration
names leak into the tile ids. The umbrella uses the
`rc_power_alternator_*` prefix because `alternator` is
the canonical vendor-neutral alternator subsystem (the
umbrella for the FOUR operator-pickable paths); the
`alternator` subsystem under the existing `power`
subsystem was added to `docs/reference/rc-entity-
naming.md` by this slice.

The contract tiles + how the upstream vendor + HA core
+ relay integration template exposes them:

- `binary_sensor.rc_power_alternator_charging_enabled` —
  the AND gate (TRUE iff the alternator is allowed to
  charge right now). The tile is a `template:`
  binary_sensor (since 2022.x) that ANDs:

      is_charging_enabled =
          states('select.rc_power_alternator_charge_mode')
              not in ('off', 'stealth', 'protect_battery')
          and is_state('binary_sensor.rc_vehicle_engine_running', 'on')
          and (states('sensor.rc_power_battery_soc') | float(0)) > 30
          and (states('sensor.alt_battery_temp_c') | float(25)) > -10
          and (states('sensor.alt_battery_temp_c') | float(25)) < 50
          and is_state('select.rc_mode', 'home')
          and is_state('binary_sensor.rc_power_alternator_fault', 'off')

  The thresholds (30 % SOC, -10 °C cold cutoff, 50 °C
  hot cutoff) are the operator's chosen defaults; the
  recipe §12 walks through adjusting them via
  `input_number.rc_power_alternator_soc_threshold`
  (default 30 %) +
  `input_number.rc_power_alternator_temp_cold_cutoff`
  (default -10 °C) +
  `input_number.rc_power_alternator_temp_hot_cutoff`
  (default 50 °C).

- `select.rc_power_alternator_charge_mode` — the
  operator's chosen charge mode (one of `off` / `auto`
  / `boost` / `float` / `desulfation` / `stealth` /
  `protect_battery`). The tile is a `select:` domain
  entity (since 2022.x). The translation helper is the
  operator's `input_select.rc_power_alternator_charge_
  mode` (since 2022.x — exposes a GUI flow for the
  operator to pick the charge mode from the HA UI
  under Settings → Helpers).

- `sensor.rc_power_alternator_target_voltage_v` — the
  regulator's voltage setpoint (V; the temperature-
  compensation may have lowered it from the operator's
  chosen nominal voltage). The tile is a `template:`
  sensor (since 2022.x) that derives from the upstream
  regulator's target_voltage entity (when present) OR
  the operator's `input_number.rc_power_alternator_
  target_voltage_nominal_v` (default 14.4 V for a 12 V
  system or 28.8 V for a 24 V system) + the
  temperature-compensation curve.

- `sensor.rc_power_alternator_charge_current_a` — the
  current accepted by the house battery bank during
  alternator charging (A). The tile is a `template:`
  sensor (since 2022.x) that derives from the upstream
  regulator's current-sense input (Path A / Path B) OR
  the Victron `sensor.rc_power_battery_current_a` for
  Path C / Path D.

- `binary_sensor.rc_power_alternator_temp_compensation_
  active` — the cold / hot battery gate (TRUE iff the
  temperature probe reads cold (< 0°C) OR hot (> 45°C)
  AND the regulator's temperature-compensation curve
  is actively lowering the target voltage). The tile
  is a `template:` binary_sensor (since 2022.x).

- `binary_sensor.rc_power_alternator_fault` — the
  regulator's fault trip gate (TRUE iff the regulator
  reports over-temp / over-voltage / communication
  lost / BMS lockout). The tile is a `template:`
  binary_sensor (since 2022.x) that derives from the
  upstream regulator's fault state.

- `sensor.rc_power_alternator_last_trigger_reason` —
  the reason the alternator was last enabled (one of
  `manual` / `ignition_on` / `soc_low` / `battery_cold`
  / `boost` / `desulfation` / `stealth_suppressed` /
  `fault_blocked`). The tile is an `input_text:`
  domain entity (since 2022.x) that the operator's
  automations write to before calling the
  `switch.turn_on` service.

- `button.rc_power_alternator_manual_override` — the
  manual override (the operator can force alternator
  charging ON for a configurable duration from the
  dashboard). The button is an `input_button:` domain
  entity (since 2022.x) that fires a configurable-
  duration `switch.turn_on` + a timer to call
  `switch.turn_off` after the operator's chosen
  duration.

The translation helpers needed for the contract tiles
include:

- The `template:` switch + sensor + binary_sensor +
  select + number wrappers (since 2022.x) for the
  contract layer.
- The `input_boolean` + `input_text` + `input_number` +
  `input_select` + `input_button` helpers (since
  2022.x) for the operator-facing affordances +
  the operator's chosen thresholds.

## §8 Automations

The SIX §8 automations are documented below. The
automations are the canonical wiring that makes the
recipe work end-to-end. The recipe walks through each
automation + the contract tiles each automation reads +
the services each automation calls.

### §8.1 Ignition-on enable

The automation fires when
`binary_sensor.rc_vehicle_engine_running` flips to TRUE
AND the battery SOC is below the operator's chosen
threshold (default 95 %). The automation enables
alternator charging via the upstream `switch.turn_on`
service + sets `select.rc_power_alternator_charge_mode`
to `auto` + writes `sensor.rc_power_alternator_last_
trigger_reason = ignition_on`.

Trigger: `binary_sensor.rc_vehicle_engine_running`
flips to `on`
Condition:
`sensor.rc_power_battery_soc < 95`
Action:
```yaml
action: switch.turn_on
target:
  entity_id: switch.alt_field_relay  # Path A / Path B / Path C
- action: select.select_option
target:
  entity_id: select.rc_power_alternator_charge_mode
data:
  option: auto
- action: input_text.set_value
target:
  entity_id: sensor.rc_power_alternator_last_trigger_reason
data:
  value: ignition_on
```

For Path A / Path B (regulator-equipped), the upstream
`switch.*` turn_on call also writes the regulator's
target_voltage to the operator's chosen nominal voltage
via the regulator's `number.set_value` service.

For Path C (relay-only), the upstream `switch.*` turn_on
call closes the relay + the alternator's field
excitation is connected + the alternator charges.

For Path D (read-only), the automation does NOT call any
upstream switch.turn_on — it just writes
`sensor.rc_power_alternator_last_trigger_reason` to log
the advisory.

### §8.2 SOC-low boost

The automation fires when
`sensor.rc_power_battery_soc` falls below the operator's
chosen threshold (default 60 %) AND the engine is
running. The automation enables boost charging via the
upstream regulator's `select.*` mode set to `boost` OR
sets `select.rc_power_alternator_charge_mode` to `boost`
+ writes `sensor.rc_power_alternator_last_trigger_reason
= boost`.

Trigger: `sensor.rc_power_battery_soc < 60`
Condition:
`binary_sensor.rc_vehicle_engine_running == on`
Action:
```yaml
action: select.select_option
target:
  entity_id: select.rc_power_alternator_charge_mode
data:
  option: boost
- action: input_text.set_value
target:
  entity_id: sensor.rc_power_alternator_last_trigger_reason
data:
  value: boost
```

The boost mode raises the regulator's target_voltage
(default 14.8 V for a 12 V system) until SOC > 80 %.

### §8.3 Battery-cold temperature-compensation

The automation fires when the battery temperature probe
reads cold (< 0°C) OR hot (> 45°C). The automation lowers
the regulator's target_voltage via the upstream
`number.set_value` service + sets
`binary_sensor.rc_power_alternator_temp_compensation_
active` to TRUE + writes
`sensor.rc_power_alternator_last_trigger_reason =
battery_cold` (or `battery_hot`).

Trigger: `sensor.alt_battery_temp_c < 0` OR
`sensor.alt_battery_temp_c > 45`
Action:
```yaml
action: number.set_value
target:
  entity_id: number.alt_target_voltage_v
data:
  value: >-
    {{ states('input_number.rc_power_alternator_target_
             voltage_nominal_v') | float
       - 0.003 * (25 - (states('sensor.alt_battery_
              temp_c') | float))
    }}
- action: input_text.set_value
target:
  entity_id: sensor.rc_power_alternator_last_trigger_reason
data:
  value: battery_cold
```

The temperature-compensation curve uses the standard
-3 mV/°C/cell (lead-acid) or -5 mV/°C/cell (LiFePO4)
slope — the operator picks one via
`input_select.rc_power_alternator_temp_compensation_
curve`.

### §8.4 Mode-aware Stealth / Sleep suppressions

The automation SUPPRESSES charging when
`select.rc_mode` is in `stealth` OR `sleep` mode AND the
operator has flagged the alternator as noisy (the
operator's `input_boolean.rc_power_alternator_noisy_in_
stealth` + `input_boolean.rc_power_alternator_noisy_in_
sleep`). The suppression is implemented as a CONDITION
on the §8.1 + §8.2 automations.

Condition on §8.1 + §8.2:
`(select.rc_mode not in ('stealth', 'sleep')) OR
(input_boolean.rc_power_alternator_noisy_in_X == off)`

The operator can still trigger the manual override via
`button.rc_power_alternator_manual_override` during
Stealth / Sleep mode (the §8.7 manual override is NOT
suppressed by mode).

### §8.5 Protect_battery mode

The automation fires when
`sensor.rc_power_battery_soc` falls below the operator's
chosen protect_battery threshold (default 20 %). The
automation disables charging via the upstream
`switch.turn_off` service + sets
`select.rc_power_alternator_charge_mode` to
`protect_battery` + writes
`sensor.rc_power_alternator_last_trigger_reason =
protect_battery`.

Trigger:
`sensor.rc_power_battery_soc < 20`
Action:
```yaml
action: switch.turn_off
target:
  entity_id: switch.alt_field_relay
- action: select.select_option
target:
  entity_id: select.rc_power_alternator_charge_mode
data:
  option: protect_battery
- action: input_text.set_value
target:
  entity_id: sensor.rc_power_alternator_last_trigger_reason
data:
  value: protect_battery
```

The §8.5 protect_battery mode mirrors the canonical
low-voltage lockout pattern from the heated-floors
`connections/heated-floors/` recipe's
`binary_sensor.rc_hvac_floor_low_voltage_lockout` —
when the inverter SOC falls below the threshold, the
alternator / floor heat refuses to start until SOC
recovers OR shore is reconnected (in the heated-floors
case; in this case, the operator can manually enable
the alternator via `button.rc_power_alternator_manual_
override` if the operator has a known full-charge
window via solar / shore).

### §8.6 Fault-block

The automation fires when
`binary_sensor.rc_power_alternator_fault` flips to TRUE
(the regulator reported over-temp / over-voltage /
communication lost / BMS lockout). The automation
forces charging OFF via the upstream `switch.turn_off`
service + sets `select.rc_power_alternator_charge_mode`
to `off` + notifies the operator's phone via the HA
Companion app + writes
`sensor.rc_power_alternator_last_trigger_reason =
fault_blocked`.

Trigger:
`binary_sensor.rc_power_alternator_fault` flips to `on`
Action:
```yaml
action: switch.turn_off
target:
  entity_id: switch.alt_field_relay
- action: select.select_option
target:
  entity_id: select.rc_power_alternator_charge_mode
data:
  option: off
- action: input_text.set_value
target:
  entity_id: sensor.rc_power_alternator_last_trigger_reason
data:
  value: fault_blocked
- action: notify.notify
data:
  message: "Alternator regulator fault — charging forced OFF"
```

The §8.6 fault-block mirrors the canonical "blocks on
fault" automation pattern from the deadbolts
`connections/deadbolts/` recipe's
`binary_sensor.rc_safety_lock_*` fault handling — when a
fault is reported, the regulator / lock refuses to act
until the fault is cleared.

### §8.7 Manual override via `button.rc_power_alternator_manual_override`

The button fires a configurable-duration `switch.turn_on`
+ a timer to call `switch.turn_off` after the operator's
chosen duration (default 60 min) + writes
`sensor.rc_power_alternator_last_trigger_reason =
manual`.

Trigger:
`button.rc_power_alternator_manual_override` pressed
Action:
```yaml
action: switch.turn_on
target:
  entity_id: switch.alt_field_relay
- delay: "01:00:00"  # operator-configurable duration
- action: switch.turn_off
target:
  entity_id: switch.alt_field_relay
- action: input_text.set_value
target:
  entity_id: sensor.rc_power_alternator_last_trigger_reason
data:
  value: manual
```

The manual override is useful when the operator knows
they need a top-off before tonight + the auto-policy
mode has charging OFF (e.g. the operator is in Stealth
mode + has the alternator flagged as noisy — the
operator can manually force a charging session for 60
minutes to top off before dark).

## §9 Troubleshooting

The EIGHT §9 troubleshooting entries cover the most
common issues operators hit when wiring the recipe.

### §9.1 Alternator never charges

**Symptom:** The operator turns on the engine + the
§8.1 ignition-on enable automation fires + the umbrella
indicates `binary_sensor.rc_power_alternator_charging_
enabled = TRUE` + but no current is flowing into the
house battery bank.

**Causes:**
- The upstream regulator / relay integration is not
  wired (the operator has not installed the HA core
  `mqtt` integration + the operator's chosen path's
  upstream integration). The operator checks Settings →
  Devices & Services → verifies the operator's chosen
  path's integration is configured + verifies the
  upstream `switch.*` entity exists.
- The operator's chosen path's upstream integration is
  wired but the upstream `switch.*` entity is not
  surfacing (the upstream integration is reporting
  `unknown` / `unavailable`). The operator checks the
  upstream integration's device page + verifies the
  `switch.*` entity has a numeric value (typically
  `on` / `off`).
- The §8.5 protect_battery mode is active (the
  operator's `sensor.rc_power_battery_soc` is below the
  operator's chosen threshold). The operator either
  waits for SOC to recover OR enables the §8.7 manual
  override.
- The §8.6 fault-block is active (the regulator
  reported a fault). The operator checks the
  regulator's fault log + verifies the fault has been
  cleared + resets the fault.
- The §8.4 mode-aware Stealth / Sleep suppression is
  active (the operator is in Stealth mode + has flagged
  the alternator as noisy). The operator either changes
  mode OR enables the §8.7 manual override.

### §9.2 Alternator charges forever

**Symptom:** The operator turns off the engine + the
alternator keeps charging (the regulator target_voltage
remains at the operator's chosen nominal voltage).

**Causes:**
- The §8.1 ignition-on enable automation's
  `binary_sensor.rc_vehicle_engine_running` source is
  stuck in the `on` state (the operator's leveling / mode
  connection's engine-running signal is reporting
  `on` after the engine is off — usually an IMU
  vibration false-positive). The operator checks the
  engine-running signal + verifies it flips to `off`
  when the engine is off.
- The operator's chosen path's upstream integration has
  a bug (the upstream integration does NOT respond to
  `switch.turn_off` service calls when the engine is off).
  The operator checks the upstream integration's device
  page + verifies the `switch.turn_off` service call
  works.

### §9.3 Alternator faults on first start

**Symptom:** The operator turns on the engine + the §8.1
ignition-on enable automation fires + the §8.6 fault-
block automation immediately fires + the operator's
phone receives a "Alternator regulator fault — charging
forced OFF" notification.

**Causes:**
- The regulator's field wire polarity is reversed (the
  operator's regulator is rated for negative-ground
  alternators + the operator's van is positive-ground OR
  vice-versa). The operator checks the regulator's
  polarity + reverses the field wire.
- The regulator's battery-sense wire is not connected
  (the regulator is reading a phantom battery voltage +
  reporting it as over-voltage). The operator checks the
  battery-sense wire + connects it to the house
  battery's B+ terminal.
- The regulator's CAN bus termination is incorrect (the
  regulator is reporting a CAN bus communication-lost
  fault). The operator checks the CAN bus termination
  resistors + adds a 120 Ω resistor at each end of the
  CAN bus if not already present.

### §9.4 Protect_battery mode stuck on

**Symptom:** The operator turns on the engine + the §8.5
protect_battery automation fires + the umbrella
disables charging + the operator's SOC is well above
the threshold.

**Causes:**
- The Victron `sensor.rc_power_battery_soc` is
  reporting stale data (the operator's battery monitor
  has not received a fresh SOC update in > 5 minutes).
  The operator checks the battery monitor's status +
  verifies the SOC is fresh (typically a refresh
  every 30 seconds).
- The Victron `sensor.rc_power_battery_soc` is wired
  to the wrong source (the operator's battery monitor
  is reporting the starter battery's SOC + the starter
  battery is at 100 % but the operator wired it to the
  house battery monitor). The operator checks the
  source entity + verifies it's the house battery
  monitor.

### §9.5 Manual override doesn't fire

**Symptom:** The operator presses
`button.rc_power_alternator_manual_override` + the
umbrella does NOT force charging ON.

**Causes:**
- The upstream `switch.alt_field_relay` entity is not
  wired (the operator's relay is not integrated into
  HA). The operator checks Settings → Devices &
  Services → verifies the upstream entity exists.
- The operator's chosen path's upstream integration has
  a bug (the upstream integration does NOT respond to
  `switch.turn_on` service calls from manual overrides).
  The operator checks the upstream integration's device
  page + verifies the `switch.turn_on` service call
  works.
- The §8.6 fault-block is active (the regulator is
  reporting a fault + the operator's manual override
  is being suppressed). The operator checks the fault
  state + clears the fault.

### §9.6 Temperature-compensation never fires

**Symptom:** The operator's battery temperature probe
reads cold (< 0°C) OR hot (> 45°C) but the §8.3
battery-cold temperature-compensation automation never
fires + `binary_sensor.rc_power_alternator_temp_
compensation_active` stays FALSE.

**Causes:**
- The battery temperature probe is not wired (the
  `binary_sensor.rc_power_alternator_temp_compensation_
  active` template binary_sensor is not derived from
  the upstream temperature probe's `sensor.*` entity).
  The operator checks the template binary_sensor's
  source + verifies the upstream `sensor.*` entity
  exists.
- The battery temperature probe's polarity is reversed
  (the probe is reading the ambient air + not the
  battery's internal temperature). The operator checks
  the probe's wiring + attaches it to the battery's
  case.

### §9.7 Mode-aware suppression doesn't suppress

**Symptom:** The operator sets `select.rc_mode` to
`stealth` OR `sleep` + the §8.1 + §8.2 automations
still fire + the alternator charges.

**Causes:**
- The mode `connections/mode/` recipe is not wired
  (the `select.rc_mode` tile does not exist). The
  operator checks Settings → Devices & Services →
  mode/automation-builder + verifies the tile exists.
- The §8.1 + §8.2 automations' CONDITION does NOT
  include the mode-aware Stealth / Sleep suppression
  (the condition is missing). The operator adds the
  condition to the §8.1 + §8.2 automations.
- The `select.rc_mode` tile is set to `home` / `away`
  (not `stealth` / `sleep`). The operator verifies the
  tile's state is `stealth` / `sleep`.
- The operator's `input_boolean.rc_power_alternator_
  noisy_in_stealth` (or `_in_sleep`) is OFF (the
  operator has NOT flagged the alternator as noisy in
  the chosen mode). The operator either flags the
  alternator as noisy OR enables the §8.7 manual
  override.

### §9.8 Fault-block never clears

**Symptom:** The §8.6 fault-block fires + the operator
clears the regulator's fault + the
`binary_sensor.rc_power_alternator_fault` tile stays
TRUE.

**Causes:**
- The upstream regulator's fault state is not wired (the
  `binary_sensor.rc_power_alternator_fault` template
  binary_sensor is not derived from the upstream
  regulator's `binary_sensor.*` entity). The operator
  checks the template binary_sensor's source + verifies
  the upstream `binary_sensor.*` entity exists.
- The upstream regulator's fault state is reporting
  `unknown` (the bridge / integration has lost contact
  with the regulator). The operator checks the bridge's
  status + verifies the bridge is online.
- The operator's chosen path's upstream integration has
  a bug (the upstream integration is stuck reporting
  the fault even after the fault is cleared). The
  operator restarts the bridge / integration.

## §10 Privacy

The umbrella does NOT collect any personally identifiable
information (PII) about the operator's alternator
wiring. The 8 `rc_power_alternator_*` contract tiles
are computed locally on the HA instance; the upstream
regulator / DC-DC charger / relay entity's logs are
operator-owned via the HA core logbook; no RoamCore-
side telemetry is sent.

The alternator-side control produces no telemetry
beyond local enable/disable + voltage + current + fault
state; the upstream integration's logs are operator-
owned via the HA core logbook.

- **Path A1 Victron Cerbo GX + DC-DC charger** is
  fully local (no cloud call home for the
  enable/disable + voltage + current + fault; the
  Cerbo GX communicates with HA over the local
  network via the `victron` integration).
- **Path A2 / Path B vendor MQTT bridge** may require
  vendor cloud auth for first-time setup (the operator
  pairs the regulator / DC-DC charger with the vendor's
  app + creates an account), but subsequent runs are
  local (the bridge publishes the regulator's state to
  the local MQTT broker + the HA core `mqtt`
  integration auto-discovers the entities).
- **Path C Shelly 1 / Shelly Plus 1 / ESPHome / Tasmota
  relay** is fully local (no cloud call home; the relay
  communicates with HA over Wi-Fi).
- **Path D read-only ignition-signal-only** is fully
  local (the upstream `binary_sensor.rc_vehicle_
  engine_running` is computed locally on the HA server
  via the leveling / mode connection's IMU + drive-
  state signal).

The alternator-side control produces no telemetry
beyond local enable/disable + voltage + current + fault
state; the ignition signal is local; no cloud call
home.

## §11 Promoting to tier-a

To promote the alternator charge control connection from
tier-b to tier-a, the following would need to happen:

1. **Real alternator regulator + battery + relay +
   temperature probe + ignition signal on CI bench.**
   RoamCore would need a CI bench with at least one of:
   - Path A — a Victron Cerbo GX + DC-DC charger + the
     HA core `victron` integration wired.
   - Path B — a Wakespeed WS500 / Balmar MC-618 /
     Sterling Regulated Advanced Alternator-to-Battery
     charger / Renogy Battery-to-Battery / REDARC BCDC
     / EP-Power B2B / ARCO Zeus regulator + a vendor
     MQTT bridge + the HA core `mqtt` integration
     wired.
   - Path C — a Shelly 1 / Shelly Plus 1 relay wired to
     an alternator field excitation wire + the HA core
     Shelly integration + the HA core `template:`
     wrappers wired.
   Plus a 12 V / 24 V house battery bank + a battery
   temperature probe + an ignition signal + canned
   fixture responses for ignition / SOC / temperature /
   fault events. The bench is the canonical
   "integration test" target for alternator charge
   control.

2. **RoamCore-owned operator-wired setup flow.** RoamCore
   would need a setup flow for the alternator charge
   control integration that walks the operator through
   choosing Path A vs Path B vs Path C vs Path D +
   declaring the MQTT topic / GPIO pin / CAN-bridge
   choice + ignition signal declaration + temperature-
   probe pin + the upstream fault state source + the
   upstream SOC + battery-current sources from
   `connections/victron/`. The setup flow is the
   canonical "operator-wired" affordance that
   distinguishes tier-b from tier-a.

3. **Integration tests asserting:**
   - The §8.1 ignition-on enable automation fires
     when `binary_sensor.rc_vehicle_engine_running`
     flips to `on` (a canned fixture response of
     `engine_running: on` triggers the automation +
     the automation calls `switch.turn_on` on the
     upstream `switch.*` entity when SOC < 95 %).
   - The §8.2 SOC-low boost automation fires when
     `sensor.rc_power_battery_soc` falls below 60 %
     (a canned fixture response of `soc: 50` triggers
     the automation + the automation sets
     `select.rc_power_alternator_charge_mode` to
     `boost`).
   - The §8.3 battery-cold temperature-compensation
     automation fires when the battery temperature
     probe reads cold (< 0°C) (a canned fixture
     response of `battery_temp_c: -5` triggers the
     automation + the automation lowers the regulator's
     target_voltage by the temperature-compensation
     curve).
   - The §8.4 mode-aware Stealth / Sleep suppressions
     suppress the §8.1 + §8.2 automations when
     `select.rc_mode` is in `stealth` OR `sleep` mode
     AND the operator has flagged the alternator as
     noisy (a canned fixture response of
     `mode: stealth` + `noisy_in_stealth: on` blocks
     the §8.1 + §8.2 automations).
   - The §8.5 protect_battery mode forces charging
     OFF when `sensor.rc_power_battery_soc` falls
     below 20 % (a canned fixture response of
     `soc: 15` triggers the automation + the
     automation calls `switch.turn_off` on the
     upstream `switch.*` entity).
   - The §8.6 fault-block fires when
     `binary_sensor.rc_power_alternator_fault` flips
     to `on` (a canned fixture response of
     `alt_fault: on` triggers the automation + the
     automation calls `switch.turn_off` on the
     upstream `switch.*` entity).
   - The §8.7 manual override via
     `button.rc_power_alternator_manual_override`
     fires a 60-minute `switch.turn_on` + a 60-minute
     timer calls `switch.turn_off` (a button press
     fires the automation + the automation calls
     `switch.turn_on` + a 60-minute timer calls
     `switch.turn_off`).
   - The contract tiles reflect the current state of
     the alternator charge setup (the operator's
     chosen `switch.*` entity + the upstream
     `sensor.*` (target_voltage + charge_current +
     battery_temp) + the upstream `binary_sensor.*`
     (fault state) + the ignition signal + the
     battery SOC from `sensor.rc_power_battery_soc`
     + the mode from `select.rc_mode`).

The tier-a promotion is BLOCKED on the real alternator
regulator + battery + relay + temperature probe +
ignition signal bench + a real Wakespeed / Balmar /
Sterling / Renogy / REDARC / EP-Power / ARCO regulator
(or a Victron Cerbo GX + DC-DC charger) on the bench;
until the bench fixture lands, the alternator charge
control connection is tier-b.

## §12 Files in this connection + cross-references

### Files

- `connections/alternator-charge-control/connection.yml`
  — the source-of-truth manifest.
- `connections/alternator-charge-control/__init__.py`
  — the `DOMAIN = "alternator-charge-control"` marker
  for the audit.
- `connections/alternator-charge-control/README.md`
  — the folder overview.
- `connections/alternator-charge-control/docs/recipe.md`
  — the full howto (this file).
- `connections/alternator-charge-control/tests/test_
  connection_yml.py` — the manifest honesty checks.

### Cross-references

- **HA core `mqtt` integration** (the canonical Path A2
  + Path B integrator; since 2022.x) —
  https://www.home-assistant.io/integrations/mqtt/
- **HA core Shelly integration** (the canonical Path C1
  relay integrator; since 2022.x) —
  https://www.home-assistant.io/integrations/shelly/
- **HA core `victron` integration** (the canonical Path
  A1 DC-DC-charger-integrated-with-Victron integrator;
  since 2022.x) —
  https://www.home-assistant.io/integrations/victron/
- **HA core `template:` switch + sensor +
  binary_sensor wrappers** (the canonical contract-
  layer wrapping; since 2022.x) —
  https://www.home-assistant.io/integrations/template/
- **HA core `input_boolean` + `input_text` +
  `input_number` + `input_select` + `input_button`
  helpers** (the canonical operator-facing affordances;
  since 2022.x) —
  https://www.home-assistant.io/integrations/input_boolean/
- **Victron connection** (the canonical source of
  `sensor.rc_power_battery_soc` +
  `sensor.rc_power_battery_current_a` +
  `sensor.rc_power_battery_temperature_c` for the
  §8.1 / §8.2 / §8.3 / §8.5 automations; the
  low-voltage lockout pattern mirrored in §8.5
  protect_battery mode) —
  `connections/victron/`
- **Mode / automation-builder connection** (the
  canonical source of `select.rc_mode` for the §8.4
  mode-aware Stealth / Sleep suppressions) —
  `connections/mode/`
- **Leveling / vehicle connection** (the canonical
  source of `binary_sensor.rc_vehicle_engine_running`
  for the §8.1 ignition-on enable) —
  `connections/leveling/`
- **Heated floors connection** (the canonical low-
  voltage lockout pattern mirrored in §8.5
  protect_battery mode when SOC < threshold) —
  `connections/heated-floors/`
- **Deadbolts connection** (the canonical "blocks on
  fault" automation pattern mirrored in §8.6 fault-
  block) —
  `connections/deadbolts/`
- **Fans connection** (the canonical mode-aware
  Stealth / Sleep suppression pattern mirrored in
  §8.4) —
  `connections/fans/`
- **RoamCore entity naming** —
  `docs/reference/rc-entity-naming.md` (the
  `alternator` subsystem under the existing `power`
  subsystem was added by this slice).
- **OpenClaw JSON API** (the contract `summary_keys`
  land here) —
  `docs/reference/openclaw-json-api.md`
- **HA core `switch` + `binary_sensor` + `sensor`
  integrations** (the canonical wrapper primitives
  for the contract layer; since 2022.x) —
  https://www.home-assistant.io/integrations/switch/
- **Wakespeed WS Link / Balmar Smartlink / Renogy
  BT-2 / REDARC RedVision / Sterling BMS Link /
  EP-Power EP Link / ARCO Zeus app** (Path B vendor
  MQTT bridges):
  - https://www.wakespeed.com/ (Wakespeed WS500 + WS Link)
  - https://balmar.net/ (Balmar MC-618 + Smartlink)
  - https://www.renogy.com/ (Renogy BT-2)
  - https://www.redarc.com.au/ (REDARC RedVision)
  - https://www.sterling-power.com/ (Sterling BMS Link)
  - https://www.ep-power.com/ (EP-Power EP Link)
  - https://www.arcomarine.com/ (ARCO Zeus)
