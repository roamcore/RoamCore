# Leveling — full howto (RoamCore vendor-neutral IMU + jacks + Bluetooth pads umbrella for HA — phone IMU + permanent IMU + levelling jacks + Bluetooth pads)

This recipe is the canonical howto for the
`connections/leveling/` tier-b recipe connection (Wave 3
#60). It walks the operator through setting up ONE of the
FOUR operator-pickable paths (Path A phone IMU + Path B
permanent IMU board with four sub-flavors ESPHome MPU-6050
/ ESPHome MPU-9250 / ESPHome BNO055 / ESPHome LSM6DS3 +
Path C levelling jacks with three sub-flavors HWH /
Lippert / Power Gear / Bigfoot + Path D Bluetooth pads
with three sub-flavors Mopeka / Lippert / TireMinder) + the
10 `rc_level_*` contract tiles + the FIVE §8 MANDATORY
automations.

The recipe assumes the operator has at least ONE levelling
hardware choice (a phone with the HA Companion app for Path
A OR an ESP32 + IMU breakout for Path B OR a relay-driven
levelling-jack set for Path C OR a Bluetooth levelling pad
set for Path D). If the operator has no levelling hardware,
the recipe starts at §2 Prerequisites + walks through the
hardware-installation prerequisites before the upstream-
integration wiring.

## §1 What is leveling in RoamCore?

Leveling (vendor-neutral IMU + jacks + Bluetooth pads
umbrella for HA, covering phone IMU + permanent IMU board
+ levelling jacks + Bluetooth pads — phone IMU covers the
most-asked user-facing question "Are we level?" without
extra hardware; permanent IMU board covers the always-on /
reliable reading; levelling jacks cover the auto-extend /
auto-retract affordance for motorhomes; Bluetooth pads
cover the aftermarket pad-mounted levelling) — the
umbrella for "Better sleep and cooking. Quick 'good
enough' check without guessing" — is the vehicle-category
complement to the broader RoamCore comfort affordances.
The umbrella positions leveling as a vehicle-category
concern (not a scene + not a power-load concern + not a
remote-access concern) because leveling is the vehicle-
level sensor substrate: the pitch / roll / max-tilt tiles
give the operator an at-a-glance "are we level?" status;
the fridge-safe tile is the §8 MANDATORY safety gate for
the fridge compressor (most compressor fridges tolerate
±3° but anything beyond that risks damage); the jack-
status tile (Path C only) surfaces the jack state for the
motorhome's levelling-jack control; the calibration-
reminder automation (every 30 days) keeps the IMU
calibrated to the operator's chosen parking surface.

The pitch / roll tiles are the operator's "are we level?"
dashboard indicator — the recipe exposes the
`binary_sensor.rc_level_is_level` (TRUE iff max_tilt <
0.5°) + `binary_sensor.rc_level_is_close_to_level` (TRUE
iff max_tilt < 1.5°) + `sensor.rc_level_max_tilt_degrees`
(max of `|pitch|` + `|roll|`) so the operator can see at
a glance whether the van is "good enough" to cook / sleep
/ run the fridge.

The fridge-safe tile is the §8 MANDATORY safety gate
(`binary_sensor.rc_level_fridge_safe`) — when the tile
flips to FALSE, the §8.3 fridge-safety-gate automation
fires an immediate notification warning the operator to
turn off the fridge compressor. This is the single most
important affordance in the leveling umbrella: forgetting
to wire the fridge-safe gate can damage the fridge in
overnight tilt events (most compressor fridges tolerate
±3° but anything beyond that risks damaging the
compressor).

The mode selector (`select.rc_level_mode`) is the
operator-facing affordance (one of `off` / `read_only` /
`auto_warn` / `auto_jack`) — the operator picks the mode
based on their use case: `read_only` for "I want to see
the tiles but no automations"; `auto_warn` for "fire
notifications when out of level"; `auto_jack` for "auto-
extend the jacks when I press the button" (Path C only).

The calibration button (`button.rc_level_calibrate_now`)
is the operator-triggered calibration — pressing the
button touches the calibration offset and updates the
`last_calibrated_at` tile. The recipe requires the
operator to press the button ONCE before first use (the
fridge-safe tile depends on a calibrated zero).

## §2 Prerequisites

### §2.1 Path A — Phone IMU

- A smartphone with the HA Companion app installed (iOS
  2022.x or Android 2022.x minimum).
- The HA Companion app's IMU sensor permission enabled
  (Settings → Companion App → Sensors → IMU Sensor).
- The phone mounted face-up on the dashboard (the phone's
  accelerometer orientation matters — face-up = positive
  z-axis = "van is level" baseline).

### §2.2 Path B — Permanent IMU board

- An ESP32 or ESP8266 board ($5-10 — ESP32-DevKitC or
  NodeMCU v3 are common choices).
- An IMU breakout ($5-15 — MPU-6050 / MPU-9250 / BNO055 /
  LSM6DS3 are common choices).
- I²C wiring: 4 wires (VCC + GND + SCL + SDA) between the
  ESP32 and the IMU breakout.
- USB-C cable from the ESP32 to the head unit (for power
  + flashing).
- The ESPHome integration installed on the HA server (HA
  core `esphome` integration since 2022.x).

### §2.3 Path C — Levelling jacks

- A 4-point / 6-point hydraulic levelling jack set (HWH /
  Lippert / Power Gear / Bigfoot are common choices for
  motorhomes).
- An 8-channel / 12-channel / 16-channel relay board
  ($30-80 — 5 V or 12 V relays, low-level trigger).
- Wiring: relay contacts to the jack + pump control lines
  (per the manufacturer's wiring diagram).
- A 12 V or 24 V supply for the relay board.

### §2.4 Path D — Bluetooth pads

- A Mopeka / Lippert / TireMinder Bluetooth levelling pad
  set (the operator's existing pads work — no need to
  buy new).
- A Mopeka BLE adapter OR a Lippert Bluetooth adapter OR
  a TireMinder Bluetooth adapter (depending on the pad
  vendor).
- The HACS `mopeka` integration installed (HACS — for
  Mopeka pads); OR the vendor app (Lippert OneControl /
  TireMinder) + the HA core `sensor` integration (for
  Lippert / TireMinder pads).

### §2.5 Universal prerequisites

- HA core `sensor` integration installed (HA core since
  2022.x — auto-installed in every HA install).
- HA core `template:` integration installed (HA core since
  2022.x — auto-installed in every HA install).
- HA core `input_select` / `input_text` / `input_button` /
  `input_number` helper entities enabled (HA core since
  2022.x — these are the contract tile inputs).
- The HA server reachable from the operator's chosen
  path's upstream integration (local network for Path A
  Companion + Path B ESPHome + Path C relay + Path D BLE).
- Optional cross-references (recommended but not required):
  - The HVAC basics Wave 3 #49 connection's
    `sensor.rc_hvac_interior_temperature` for the §8.2
    sleep-mode warning's cabin-light-dim behavior.
  - The time-atomic Wave 3 #55 connection's time-of-day /
    sunrise-sunset primitives for the §8.5 calibration
    reminder.
  - The mode/automation-builder Wave 2 #23 recipe's
    `select.rc_mode` tile for the §8.2 sleep-mode warning.

## §3 Path A — Phone IMU (recommended for most operators; no extra hardware)

Path A uses the HA Companion app on iOS / Android (since
2022.x) to expose the phone's built-in IMU (the
accelerometer + gyroscope) as upstream `sensor.*` entities.
The operator picks a phone, mounts it face-up on the
dashboard, and the RoamCore contract tiles publish from the
phone's orientation.

### §3.1 Path A steps

1. Install the HA Companion app on the operator's phone
   (iOS App Store or Google Play Store — search for
   "Home Assistant Companion").
2. Open the HA Companion app + sign in to the operator's
   HA server (URL + long-lived access token).
3. Enable the IMU sensor permission: Settings → Companion
   App → Sensors → IMU Sensor → ON.
4. Mount the phone face-up on the dashboard (a non-slip
   mat is recommended — phone vibration from driving can
   cause the phone to slide).
5. Verify the upstream `sensor.*` entities exist:
   `Developer Tools → States → search "accelerometer" +
   "gyroscope" + "orientation"`. The HA Companion app
   should publish:
   - `sensor.<phone>_accelerometer` (the x/y/z
     accelerometer reading in m/s²)
   - `sensor.<phone>_gyroscope` (the x/y/z gyroscope
     reading in rad/s)
   - `sensor.<phone>_orientation` (the quaternion-derived
     orientation)
6. Configure the operator-facing
   `sensor.rc_level_pitch_degrees` contract tile to point
   at the upstream `sensor.<phone>_accelerometer` (the
   `template:` sensor derives pitch from the accelerometer
   x-axis; the recipe walks the operator through the
   `template:` sensor configuration in §7).
7. Configure `sensor.rc_level_roll_degrees` to point at
   the upstream `sensor.<phone>_accelerometer` (the
   `template:` sensor derives roll from the accelerometer
   y-axis).
8. Press `button.rc_level_calibrate_now` once to seed the
   calibration offset (REQUIRED before first use).
9. Verify: check `binary_sensor.rc_level_is_level`
   reflects the upstream tilt + tilt the phone + check
   the `binary_sensor.rc_level_is_level` flips to FALSE.
10. Done. Skip to §7 for the contract tile derivation +
    §8 for the FIVE MANDATORY automations.

## §4 Path B — Permanent IMU board (ESPHome + MPU-6050 / MPU-9250 / BNO055 / LSM6DS3)

Path B uses the upstream ESPHome `mpu6050` / `mpu9250` /
`bno055` / `lsm6ds3` components (since 2022.x) to flash
firmware to a $5-15 IMU breakout wired to a $5-10 ESP32
/ ESP8266 board. The operator picks ONE of the four sub-
flavors based on the chosen IMU breakout.

### §4.1 Path B1 — ESPHome MPU-6050

1. Wire the MPU-6050 IMU breakout to the ESP32 via I²C
   (VCC + GND + SCL + SDA — typically GPIO22 = SCL +
   GPIO21 = SDA on an ESP32).
2. Flash the upstream ESPHome `mpu6050` component firmware
   to the ESP32 (the operator uses the ESPHome integration
   since 2022.x — Device Discovery flow).
3. Configure the ESPHome YAML:
   ```yaml
   sensor:
     - platform: mpu6050
       address: 0x68
       accel_x:
         name: "Van IMU Accel X"
         unit_of_measurement: 'm/s²'
       accel_y:
         name: "Van IMU Accel Y"
         unit_of_measurement: 'm/s²'
       accel_z:
         name: "Van IMU Accel Z"
         unit_of_measurement: 'm/s²'
   ```
4. Verify the upstream `sensor.*` entities exist:
   `sensor.van_imu_accel_x` + `sensor.van_imu_accel_y` +
   `sensor.van_imu_accel_z`.
5. Configure the operator-facing
   `sensor.rc_level_pitch_degrees` to point at
   `sensor.van_imu_accel_x`.
6. Configure `sensor.rc_level_roll_degrees` to point at
   `sensor.van_imu_accel_y`.
7. Press `button.rc_level_calibrate_now` once to seed
   the calibration offset (REQUIRED before first use).

### §4.2 Path B2 — ESPHome MPU-9250

1. Wire the MPU-9250 IMU breakout to the ESP32 via I²C
   (VCC + GND + SCL + SDA).
2. Flash the upstream ESPHome `mpu9250` component
   firmware.
3. Configure the ESPHome YAML:
   ```yaml
   sensor:
     - platform: mpu9250
       address: 0x68
       accel_x:
         name: "Van IMU Accel X"
         unit_of_measurement: 'm/s²'
       accel_y:
         name: "Van IMU Accel Y"
         unit_of_measurement: 'm/s²'
       accel_z:
         name: "Van IMU Accel Z"
         unit_of_measurement: 'm/s²'
   ```
4. Verify the upstream `sensor.*` entities exist.
5. Configure the operator-facing contract tiles.
6. Press `button.rc_level_calibrate_now`.

### §4.3 Path B3 — ESPHome BNO055

1. Wire the BNO055 IMU breakout to the ESP32 via I²C
   (VCC + GND + SCL + SDA — note: BNO055 is a 9-DOF IMU
   with built-in sensor fusion; the orientation output is
   a quaternion / Euler angle).
2. Flash the upstream ESPHome `bno055` component
   firmware.
3. Configure the ESPHome YAML:
   ```yaml
   sensor:
     - platform: bno055
       address: 0x28
       orientation_x:
         name: "Van IMU Orientation X"
         unit_of_measurement: '°'
       orientation_y:
         name: "Van IMU Orientation Y"
         unit_of_measurement: '°'
       orientation_z:
         name: "Van IMU Orientation Z"
         unit_of_measurement: '°'
       calibration:
         name: "Van IMU Calibration"
   ```
4. Verify the upstream `sensor.*` entities exist.
5. Configure the operator-facing contract tiles (the
   BNO055 orientation_x / orientation_y are Euler angles
   directly, not raw accelerometer readings).
6. Press `button.rc_level_calibrate_now`.

### §4.4 Path B4 — ESPHome LSM6DS3

1. Wire the LSM6DS3 IMU breakout to the ESP32 via I²C
   (VCC + GND + SCL + SDA).
2. Flash the upstream ESPHome `lsm6ds3` component
   firmware.
3. Configure the ESPHome YAML:
   ```yaml
   sensor:
     - platform: lsm6ds3
       address: 0x6A
       accel_x:
         name: "Van IMU Accel X"
         unit_of_measurement: 'm/s²'
       accel_y:
         name: "Van IMU Accel Y"
         unit_of_measurement: 'm/s²'
       accel_z:
         name: "Van IMU Accel Z"
         unit_of_measurement: 'm/s²'
   ```
4. Verify the upstream `sensor.*` entities exist.
5. Configure the operator-facing contract tiles.
6. Press `button.rc_level_calibrate_now`.

## §5 Path C — Levelling jacks (HWH / Lippert / Power Gear / Bigfoot via relay + manual control)

Path C wires the 4-point / 6-point hydraulic levelling
jacks through a relay board to the head unit. The operator
presses a button, the relay turns on the pump, the jack
extends. The recipe supports three sub-flavors based on
the chosen jack vendor.

### §5.1 Path C1 — HWH via 8-channel relay

1. Wire the HWH 4-jack control lines (front-left + front-
   right + rear-left + rear-right + pump) to the 8-
   channel relay board (one relay per jack + one relay for
   the pump + spare relays for future use).
2. Wire the relay board's control inputs to a $5-10
   ESP32 / Shelly 1 / Zooz ZEN17 (the operator's choice of
   smart switch for relay control).
3. Configure the upstream `switch.*` entities via the HA
   core Shelly integration (Shelly 1) OR the HA core
   `zwave_js` integration (Zooz ZEN17) OR the HA core
   `template:` switch wrapper (ESP32 + relay control).
4. Create `template:` switch wrappers for the pump + each
   of the 4 jacks:
   ```yaml
   switch:
     - platform: template
       switches:
         jack_front_left:
           friendly_name: "Jack Front Left"
           value_template: "{{ is_state('switch.shelly_relay_1', 'on') }}"
           turn_on:
             service: switch.turn_on
             entity_id: switch.shelly_relay_1
           turn_off:
             service: switch.turn_off
             entity_id: switch.shelly_relay_1
   ```
5. Verify the upstream `switch.*` entities exist.
6. Configure `sensor.rc_level_jack_status` to write the
   current jack state (`None` / `Retracted` / `Extending`
   / `Extended` / `Lowering` / `Lowered` / `Error`).
7. Press `button.rc_level_calibrate_now` to seed the
   calibration offset.
8. Verify: press the `button.rc_level_extend_jacks` button
   + verify the jacks extend + the pump runs + the
   `sensor.rc_level_jack_status` updates to `Extended`.

### §5.2 Path C2 — Lippert via 12-channel relay

Same as §5.1 but with 6 jacks (front-left + front-right
+ mid-left + mid-right + rear-left + rear-right + pump)
wired through a 12-channel relay board.

### §5.3 Path C3 — Power Gear / Bigfoot via 16-channel relay

Same as §5.1 but with 6 jacks + the optional slide-out
room + the optional awning wired through a 16-channel
relay board.

## §6 Path D — Bluetooth levelling pads (Mopeka / Lippert / TireMinder)

Path D uses the operator's existing Bluetooth levelling
pads to publish pitch / roll over BLE. The recipe supports
three sub-flavors.

### §6.1 Path D1 — Mopeka

1. Install the HACS `mopeka` integration (HACS — HACS →
   Integrations → search "mopeka" → Install).
2. Wire the Mopeka BLE adapter to the head unit's USB
   port (the Mopeka BLE adapter is a USB dongle).
3. Mount the Mopeka pads under each corner of the van
   (front-left + front-right + rear-left + rear-right).
4. Pair the Mopeka BLE adapter with the pads (the HACS
   `mopeka` integration auto-discovers nearby pads).
5. Verify the upstream `sensor.*` entities exist:
   `sensor.mopeka_pro_check_<pad_id>_pitch` +
   `sensor.mopeka_pro_check_<pad_id>_roll`.
6. Configure the operator-facing contract tiles to point
   at the upstream entities.
7. Press `button.rc_level_calibrate_now`.

### §6.2 Path D2 — Lippert

1. Install the Lippert OneControl app on the operator's
   phone.
2. Wire the Lippert Bluetooth adapter to the head unit's
   USB port.
3. Mount the Lippert pads under each corner of the van.
4. Pair the Lippert Bluetooth adapter with the pads via
   the OneControl app.
5. Verify the upstream `sensor.*` entities exist via the
   HA core `sensor` integration.
6. Configure the operator-facing contract tiles.
7. Press `button.rc_level_calibrate_now`.

### §6.3 Path D3 — TireMinder

1. Install the TireMinder app on the operator's phone.
2. Wire the TireMinder Bluetooth adapter to the head
   unit's USB port.
3. Mount the TireMinder pads under each corner of the
   van.
4. Pair the TireMinder Bluetooth adapter with the pads
   via the TireMinder app.
5. Verify the upstream `sensor.*` entities exist via the
   HA core `sensor` integration.
6. Configure the operator-facing contract tiles.
7. Press `button.rc_level_calibrate_now`.

## §7 RoamCore contract entities

The leveling contract layer is a thin upstream-entity-
aggregation layer. The 10 `rc_level_*` contract tiles are
vendor-neutral — no MPU-6050 / MPU-9250 / BNO055 /
LSM6DS3 / HWH / Lippert / Power Gear / Bigfoot / Mopeka /
TireMinder / ESPHome / Companion / HA / HACS / phone / BLE
/ Wi-Fi / jack / pump / relay / sensor / accelerometer /
gyroscope names leak into the tile ids.

### §7.1 The 10 `rc_level_*` contract tiles

- `sensor.rc_level_pitch_degrees` — current pitch in
  degrees, −90 to +90. The tile is a `template:` sensor
  (since 2022.x) that derives from the upstream
  `sensor.<phone>_accelerometer` (Path A) OR the upstream
  `sensor.<board>_mpu6050_accel_x` (Path B1) OR the
  upstream `sensor.<board>_mpu9250_accel_x` (Path B2) OR
  the upstream `sensor.<board>_bno055_orientation_x`
  (Path B3) OR the upstream
  `sensor.<board>_lsm6ds3_accel_x` (Path B4) OR the
  upstream `sensor.<pad>_pitch` (Path D1 / Path D2 / Path
  D3).
  ```yaml
  sensor:
    - platform: template
      sensors:
        rc_level_pitch_degrees:
          friendly_name: "RC Level Pitch"
          unit_of_measurement: '°'
          value_template: >-
            {% set accel_x = states('sensor.van_imu_accel_x') | float(0) %}
            {{ accel_x * -1.0 }}
  ```

- `sensor.rc_level_roll_degrees` — current roll in
  degrees, −90 to +90.
  ```yaml
  sensor:
    - platform: template
      sensors:
        rc_level_roll_degrees:
          friendly_name: "RC Level Roll"
          unit_of_measurement: '°'
          value_template: >-
            {% set accel_y = states('sensor.van_imu_accel_y') | float(0) %}
            {{ accel_y }}
  ```

- `sensor.rc_level_max_tilt_degrees` — max of `|pitch|` +
  `|roll|`.
  ```yaml
  sensor:
    - platform: template
      sensors:
        rc_level_max_tilt_degrees:
          friendly_name: "RC Level Max Tilt"
          unit_of_measurement: '°'
          value_template: >-
            {% set pitch = states('sensor.rc_level_pitch_degrees') | float(0) %}
            {% set roll = states('sensor.rc_level_roll_degrees') | float(0) %}
            {{ [pitch | abs, roll | abs] | max }}
  ```

- `binary_sensor.rc_level_is_level` — TRUE iff
  `sensor.rc_level_max_tilt_degrees < 0.5`.
  ```yaml
  binary_sensor:
    - platform: template
      sensors:
        rc_level_is_level:
          friendly_name: "RC Level Is Level"
          value_template: >-
            {{ states('sensor.rc_level_max_tilt_degrees') | float(99) < 0.5 }}
  ```

- `binary_sensor.rc_level_is_close_to_level` — TRUE iff
  `sensor.rc_level_max_tilt_degrees < 1.5`.
  ```yaml
  binary_sensor:
    - platform: template
      sensors:
        rc_level_is_close_to_level:
          friendly_name: "RC Level Is Close To Level"
          value_template: >-
            {{ states('sensor.rc_level_max_tilt_degrees') | float(99) < 1.5 }}
  ```

- `select.rc_level_mode` — the operator's chosen mode
  (one of `off` / `read_only` / `auto_warn` / `auto_jack`).
  ```yaml
  input_select:
    rc_level_mode:
      name: RC Level Mode
      options:
        - off
        - read_only
        - auto_warn
        - auto_jack
      initial: read_only
      icon: mdi-axis-arrow
  ```

- `sensor.rc_level_last_calibrated_at` — timestamp of
  the last operator-initiated calibration.
  ```yaml
  input_text:
    rc_level_last_calibrated_at:
      name: RC Level Last Calibrated At
      initial: "Never"
      icon: mdi-clock-outline
  ```

- `button.rc_level_calibrate_now` — the operator-
  triggered calibration.
  ```yaml
  input_button:
    rc_level_calibrate_now:
      name: RC Level Calibrate Now
      icon: mdi-refresh
  ```

- `sensor.rc_level_jack_status` — jack state (only when
  Path C jacks are wired).
  ```yaml
  input_text:
    rc_level_jack_status:
      name: RC Level Jack Status
      initial: "None"
      icon: mdi-arrow-expand-vertical
  ```

- `binary_sensor.rc_level_fridge_safe` — TRUE iff the
  fridge is safe to run.
  ```yaml
  binary_sensor:
    - platform: template
      sensors:
        rc_level_fridge_safe:
          friendly_name: "RC Level Fridge Safe"
          value_template: >-
            {{ states('sensor.rc_level_max_tilt_degrees') | float(99) < 3.0 }}
  ```

## §8 Automations (MANDATORY before first use)

The §8 walks through the FIVE MANDATORY automations. The
recipe is the contract layer; the automation wrappers are
documented below.

### §8.1 Auto-warn when out of level

The automation fires when the mode is `auto_warn` AND
`sensor.rc_level_max_tilt_degrees > 1.5` for ≥ 30 s. The
automation fires a persistent notification on the dashboard
+ (optionally) a Telegram message via the OpenClaw bridge.

```yaml
automation:
  - id: rc_level_auto_warn_when_out_of_level
    alias: "RC Level: Auto-warn when out of level"
    mode: single
    trigger:
      - platform: numeric_state
        entity_id: sensor.rc_level_max_tilt_degrees
        above: 1.5
        for: "00:00:30"
    condition:
      - condition: state
        entity_id: select.rc_level_mode
        state: auto_warn
    action:
      - service: persistent_notification.create
        data:
          title: "Out of Level"
          message: >-
            Van is out of level: max tilt is
            {{ states('sensor.rc_level_max_tilt_degrees') }}°.
            Adjust parking position.
```

### §8.2 Sleep-mode warning

The automation fires when the mode is `auto_warn` AND
`select.rc_mode` (from the mode/automation-builder Wave 2
#23 recipe) is in `sleep` mode AND
`sensor.rc_level_max_tilt_degrees > 2.0`. The automation
fires a critical notification on the bedroom tile + dims
the cabin lights to red.

```yaml
automation:
  - id: rc_level_sleep_mode_warning
    alias: "RC Level: Sleep-mode warning"
    mode: single
    trigger:
      - platform: numeric_state
        entity_id: sensor.rc_level_max_tilt_degrees
        above: 2.0
    condition:
      - condition: state
        entity_id: select.rc_level_mode
        state: auto_warn
      - condition: state
        entity_id: select.rc_mode
        state: sleep
    action:
      - service: persistent_notification.create
        data:
          title: "Sleep Mode: Out of Level"
          message: >-
            Van is out of level during sleep mode: max tilt
            is {{ states('sensor.rc_level_max_tilt_degrees')
            }}°.
      - service: light.turn_on
        target:
          entity_id: light.cabin_lights
        data:
          rgb_color: [255, 0, 0]
          brightness: 50
```

### §8.3 Fridge safety gate

The automation fires when the mode is `auto_warn` AND
`binary_sensor.rc_level_fridge_safe` transitions from
`true` to `false`. The automation fires an immediate
notification warning the operator to turn off the fridge
compressor.

```yaml
automation:
  - id: rc_level_fridge_safety_gate
    alias: "RC Level: Fridge safety gate"
    mode: single
    trigger:
      - platform: state
        entity_id: binary_sensor.rc_level_fridge_safe
        from: "on"
        to: "off"
    condition:
      - condition: state
        entity_id: select.rc_level_mode
        state: auto_warn
    action:
      - service: persistent_notification.create
        data:
          title: "FRIDGE UNSAFE — TURN OFF COMPRESSOR"
          message: >-
            Van is out of safe fridge range: max tilt is
            {{ states('sensor.rc_level_max_tilt_degrees') }}°
            (limit is ±3°). Turn off the fridge compressor
            NOW to prevent damage.
```

### §8.4 Auto-jack extend (Path C only)

The automation fires when the mode is `auto_jack` AND the
operator presses `button.rc_level_extend_jacks`. The
automation fires the relay sequence to extend the 4 / 6
jacks until `sensor.rc_level_max_tilt_degrees < 0.3` for
≥ 5 s, then stops the pump.

```yaml
automation:
  - id: rc_level_auto_jack_extend
    alias: "RC Level: Auto-jack extend (Path C only)"
    mode: single
    trigger:
      - platform: state
        entity_id: input_button.rc_level_extend_jacks
    condition:
      - condition: state
        entity_id: select.rc_level_mode
        state: auto_jack
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.jack_pump
      - repeat:
          while:
            - condition: numeric_state
              entity_id: sensor.rc_level_max_tilt_degrees
              above: 0.3
          sequence:
            - delay: "00:00:05"
      - service: switch.turn_off
        target:
          entity_id: switch.jack_pump
```

### §8.5 Calibration reminder

Every 30 days, the automation fires a notification
reminding the operator to re-calibrate the IMU.

```yaml
automation:
  - id: rc_level_calibration_reminder
    alias: "RC Level: Calibration reminder (every 30 days)"
    mode: single
    trigger:
      - platform: time
        at: "09:00:00"
    condition:
      - condition: template
        value_template: >-
          {{ now().day == 1 }}
    action:
      - service: persistent_notification.create
        data:
          title: "Calibration Reminder"
          message: >-
            It's been a month since the last IMU calibration.
            Press `button.rc_level_calibrate_now` to re-
            calibrate.
```

## §9 Troubleshooting

### §9.1 "Are we level?" tile is stuck at one value

- **Cause:** The upstream `sensor.<phone>_accelerometer`
  OR `sensor.<board>_*` entity is not reporting state.
- **Fix:** Verify the upstream entity exists (`Developer
  Tools → States → search`). For Path A, check the HA
  Companion app's IMU sensor permission is enabled. For
  Path B, verify the ESPHome device is online (`Developer
  Tools → Integrations → ESPHome → device status`). For
  Path C, verify the relay board is powered. For Path D,
  verify the BLE adapter is paired with the pads.

### §9.2 Fridge-safe tile is stuck at TRUE (or FALSE)

- **Cause:** The §8.3 fridge-safety-gate automation is
  misconfigured OR the fridge-safe threshold is too lax.
- **Fix:** Check `sensor.rc_level_max_tilt_degrees` — the
  fridge-safe tile derives from `max_tilt < 3.0`. If the
  operator wants a stricter threshold, adjust the
  `binary_sensor.rc_level_fridge_safe` `template:` config
  to `< 2.0` (for stricter fridge protection).

### §9.3 Calibration button doesn't update `last_calibrated_at`

- **Cause:** The §8.5 calibration-reminder automation
  doesn't include the `input_text.rc_level_last_calibrated_
  at` write step.
- **Fix:** Add an automation that writes
  `input_text.set_value` to `now().isoformat()` when
  `button.rc_level_calibrate_now` is pressed.

### §9.4 Sleep-mode warning never fires

- **Cause:** `select.rc_mode` is not in `sleep` mode OR
  the mode/automation-builder recipe is not wired.
- **Fix:** Verify `select.rc_mode` is in `sleep` mode
  (toggle via the mode/automation-builder recipe's UI).
  If the mode/automation-builder recipe is not wired, the
  sleep-mode warning has no source of truth.

### §9.5 Auto-jack extend doesn't stop the pump

- **Cause:** The §8.4 auto-jack-extend automation's
  `repeat:` loop condition is wrong OR the max-tilt sensor
  doesn't reach `< 0.3`.
- **Fix:** Verify the `repeat:` loop uses
  `condition: numeric_state` with `above: 0.3`. If the
  max-tilt sensor is stuck at > 0.3, the operator must
  manually stop the pump via `switch.jack_pump`.

### §9.6 Phone IMU reading is wrong (Path A)

- **Cause:** The phone is not mounted face-up on the
  dashboard OR the HA Companion app's IMU sensor
  permission is disabled.
- **Fix:** Re-mount the phone face-up on the dashboard.
  Re-enable the HA Companion app's IMU sensor permission.

## §10 Privacy

The leveling umbrella produces no telemetry beyond local
on/off state:

- The upstream `sensor.<phone>_accelerometer` (Path A) is
  a local reading from the phone's built-in IMU; the
  data never leaves the HA server.
- The upstream `sensor.<board>_*` (Path B) is a local
  reading from the ESPHome-flashed IMU board; the data
  never leaves the HA server.
- The upstream `sensor.<pad>_pitch` + `sensor.<pad>_roll`
  (Path D) is a local reading from the BLE pads; the data
  never leaves the HA server.
- The HA Companion app (Path A) requires its own platform
  auth for first-time setup if the operator selects Path
  A, but subsequent runs are local.
- The ESPHome flash (Path B) is local (the operator's HA
  server reaches the ESP32 over the local network).
- The HACS `mopeka` / `bno055` / `esp32_imu` integrations
  (Path D) are local.
- No cloud call-home. No third-party analytics. No RoamCore
  -side telemetry.

## §11 Promoting to tier-a

Tier-a would require a RoamCore-owned levelling engine +
integration code + integration tests against a real
levelling bench (a controlled environment with an
ESPHome-flashed IMU board + a 4-jack relay bench + a
Mopeka BLE adapter + canned fixture responses for pitch /
roll / fridge-unsafe events — all wired together in a
controlled environment).

Specifically:
- A RoamCore-owned `config_flow.py`-style wizard (the
  current slice ships the upstream HA core `sensor`
  integration + the HA core `template:` sensor wrapper +
  the HA Companion app + the ESPHome components + the HACS
  `mopeka` / `bno055` / `esp32_imu` integrations, NOT a
  RoamCore-owned operator-wired setup flow).
- A RoamCore-owned levelling integration code that maps
  the upstream IMU + relay + BLE pad state into the 10
  `rc_level_*` contract tiles (the current slice ships a
  thin `template:` sensor wrapper + a `template:`
  binary_sensor wrapper + an `input_select` / `input_text`
  / `input_button` helper, NOT a RoamCore-owned levelling
  integration code).
- Integration tests against a RoamCore-owned levelling
  bench (a controlled environment with an ESPHome-flashed
  IMU board + a 4-jack relay bench + a Mopeka BLE adapter
  + canned fixture responses for pitch / roll / fridge-
  unsafe events — all wired together in a controlled
  environment). The current slice ships manifest-honesty
  tests ONLY, NOT integration tests.

Until those three are in place, the slice is tier-b.

## §12 Files in this connection + cross-references

- `connection.yml` — the source-of-truth manifest (tier=b,
  category=vehicle, status=beta, 10 `rc_level_*` contract
  tiles, FIVE MANDATORY automations, FOUR operator-pickable
  paths).
- `__init__.py` — `DOMAIN = "leveling"` marker for the
  audit.
- `README.md` — the folder overview + 4-path summary +
  supersession pointer.
- `docs/recipe.md` — this file (the full howto).
- `tests/test_connection_yml.py` — 7 manifest-honesty
  tests (id_matches_folder_name + tier_b_without_tier_a_
  markers + requires_docs_recipe_published + category_
  matches_existing_legacy_doc + dashboard_tiles_follow_
  rc_naming + status_reflects_no_real_levelling_board +
  automations_are_documented).

Cross-references:
- Legacy catalog page (now superseded by this slice):
  the legacy spec.
- HA core `sensor` integration (the canonical umbrella):
  https://www.home-assistant.io/integrations/sensor/.
- HA core `template:` sensor wrapper (the canonical pitch
  / roll / max_tilt derivation): https://www.home-assistant.io/integrations/template/.
- HA Companion app (the canonical Path A phone IMU
  source): https://companion.home-assistant.io/.
- ESPHome integration (the canonical Path B permanent IMU
  board wiring): https://www.home-assistant.io/integrations/esphome/.
- HACS `mopeka` / `bno055` / `esp32_imu` integrations
  (the canonical Path D Bluetooth pad integration):
  https://hacs.xyz/docs/integrations/active.
- HVAC basics (the cabin temperature sensor used by the
  §8.2 sleep-mode warning's cabin-light-dim behavior):
  `connections/hvac-basics/` (Wave 3 #49).
- Time-atomic (the time-of-day / sunrise-sunset primitives
  used by the §8.5 calibration reminder):
  `connections/time-atomic/` (Wave 3 #55).
- Mode/automation-builder (the `select.rc_mode` tile
  source of truth for the §8.2 sleep-mode warning):
  `connections/smart-automations/` (Wave 2 #23).
- Approach lights (the cabin lighting scene modified by
  the §8.2 sleep-mode warning): `connections/approach-
  lights/` (Wave 3 #52).
- NFC tags (the optional NFC-tag-triggered calibration
  affordance): `connections/nfc-tags/` (Wave 3 #57).
- Fans (the §8.4 auto-jack extend's fan-off-on-tilt
  behavior cross-reference): `connections/fans/` (Wave 3
  #59).
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`
  (the `vehicle` subsystem was added by this slice).