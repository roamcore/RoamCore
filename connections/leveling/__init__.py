"""Leveling (vendor-neutral IMU + jacks + Bluetooth pads umbrella
for HA — phone IMU + permanent IMU board + levelling jacks +
Bluetooth pads, the operator picks ONE path) — tier-b recipe
connection.

Note on upstream wiring: tier-b connections don't ship a
RoamCore-owned operator-wired setup flow (a RoamCore
operator-wired wizard); instead, each path uses the upstream
integration's GUI flow (the HA core `sensor` integration +
the HA core `template:` sensor wrapper + the HA core
`template:` binary_sensor wrapper + the HA Companion app's
phone IMU + the ESPHome `mpu6050` / `mpu9250` / `bno055` /
`lsm6ds3` components + the HACS `mopeka` / `bno055` /
`esp32_imu` integrations + the well-known pneumatic /
hydraulic levelling jacks driven via relay all expose their
own operator-wired setup flow + GUI flow).

This module is a marker-only stub. Tier-b connections don't
ship native HA integration code; they publish a recipe
(docs/recipe.md) that walks the operator through installing
ONE OF the FOUR operator-pickable paths:

  - Path A — Phone IMU (recommended for most operators; no
    extra hardware). The HA Companion app on iOS / Android
    exposes the phone's built-in IMU (the accelerometer +
    gyroscope) as `sensor.<phone>_accelerometer` +
    `sensor.<phone>_gyroscope` +
    `sensor.<phone>_orientation` entities (since HA
    Companion iOS 2022.x / Android 2022.x). The operator
    picks a phone, mounts it face-up on the dashboard, and
    the RoamCore contract tiles publish from the phone's
    orientation. Path A is the default for any van that
    doesn't need a permanent IMU board.

  - Path B — Permanent IMU board (ESPHome + MPU-6050 /
    MPU-9250 / BNO055 / LSM6DS3). A $5-15 IMU breakout
    wired to a $5-10 ESP32 / ESP8266 board running the
    standard ESPHome `mpu6050` / `mpu9250` / `bno055` /
    `lsm6ds3` firmware (all in the upstream ESPHome
    codebase since 2022.x) + a USB-C cable to the head
    unit. Path B is the default for vans that want a
    permanent / reliable reading. Path B covers four sub-
    flavors:

    - Path B1 — ESPHome MPU-6050. The operator wires a
      $5 MPU-6050 IMU breakout to an ESP32 via I²C +
      flashes the upstream ESPHome `mpu6050` component
      firmware (the upstream ESPHome integration since
      2022.x exposes a GUI flow for the operator to add
      the ESPHome device + view the resulting `sensor.<
      board>_mpu6050_accel_x` +
      `sensor.<board>_mpu6050_accel_y` +
      `sensor.<board>_mpu6050_accel_z` entities).

    - Path B2 — ESPHome MPU-9250. The operator wires a
      $10 MPU-9250 IMU breakout to an ESP32 via I²C +
      flashes the upstream ESPHome `mpu9250` component
      firmware (the upstream ESPHome integration since
      2022.x exposes a GUI flow for the operator to add
      the ESPHome device + view the resulting `sensor.<
      board>_mpu9250_accel_x` +
      `sensor.<board>_mpu9250_accel_y` +
      `sensor.<board>_mpu9250_accel_z` entities).

    - Path B3 — ESPHome BNO055. The operator wires a
      $15 BNO055 IMU breakout to an ESP32 via I²C +
      flashes the upstream ESPHome `bno055` component
      firmware (the upstream ESPHome integration since
      2022.x exposes a GUI flow for the operator to add
      the ESPHome device + view the resulting `sensor.<
      board>_bno055_orientation_x` +
      `sensor.<board>_bno055_orientation_y` +
      `sensor.<board>_bno055_orientation_z` +
      `sensor.<board>_bno055_calibration` entities).

    - Path B4 — ESPHome LSM6DS3. The operator wires a
      $5 LSM6DS3 IMU breakout to an ESP32 via I²C +
      flashes the upstream ESPHome `lsm6ds3` component
      firmware (the upstream ESPHome integration since
      2022.x exposes a GUI flow for the operator to add
      the ESPHome device + view the resulting `sensor.<
      board>_lsm6ds3_accel_x` +
      `sensor.<board>_lsm6ds3_accel_y` +
      `sensor.<board>_lsm6ds3_accel_z` entities).

  - Path C — Levelling jacks (HWH / Lippert / Power Gear
    / Bigfoot via relay + manual control). The 4-point /
    6-point hydraulic levelling jacks wired through a
    $30-80 relay board (8-channel / 12-channel / 16-
    channel 5 V or 12 V relays) to the head unit. The
    operator presses a button, the relay turns on the
    pump, the jack extends. Path C covers three sub-
    flavors:

    - Path C1 — HWH via 8-channel relay + the HA core
      `template:` switch wrapper (since 2022.x — wraps
      any relay state into a virtual `switch.*` entity
      that exposes the standard `switch.toggle` +
      `switch.turn_on` + `switch.turn_off` service
      contract) for the pump + each of the 4 jacks.

    - Path C2 — Lippert via 12-channel relay + the HA
      core `template:` switch wrapper (since 2022.x —
      wraps any relay state into a virtual `switch.*`
      entity) for the pump + each of the 6 jacks.

    - Path C3 — Power Gear / Bigfoot via 16-channel
      relay + the HA core `template:` switch wrapper
      (since 2022.x — wraps any relay state into a
      virtual `switch.*` entity) for the pump + each
      of the 6 jacks + the optional slide-out room.

  - Path D — Bluetooth levelling pads (Mopeka / Lippert
    / TireMinder). The optional HACS `mopeka`
    integration (and the Lippert / TireMinder Bluetooth
    levelling pads) expose a `sensor.<pad>_pitch` +
    `sensor.<pad>_roll` entity over BLE. Path D covers
    three sub-flavors:

    - Path D1 — Mopeka. The operator installs the HACS
      `mopeka` integration (HACS — exposes a GUI flow
      for the operator to add a Mopeka BLE adapter +
      view the resulting `sensor.<pad>_pitch` +
      `sensor.<pad>_roll` entities) + wires the Mopeka
      BLE adapter + mounts the pads under each corner
      of the van.

    - Path D2 — Lippert. The operator installs the
      Lippert OneControl app + wires the Lippert
      Bluetooth adapter + mounts the pads under each
      corner of the van. The HA core `sensor`
      integration surfaces the upstream
      `sensor.<pad>_pitch` + `sensor.<pad>_roll`
      entities.

    - Path D3 — TireMinder. The operator installs the
      TireMinder app + wires the TireMinder Bluetooth
      adapter + mounts the pads under each corner of
      the van. The HA core `sensor` integration
      surfaces the upstream `sensor.<pad>_pitch` +
      `sensor.<pad>_roll` entities.

The umbrella publishes the resulting data via the upstream
HA core `sensor` integration (since 2022.x — has exposed
a `sensor.*` entity with `degrees` unit + `state_class:
measurement` + the `sensor.set_value` service + the
`sensor` domain) + the HA core `template:` sensor wrapper
(since 2022.x — wraps any upstream sensor state into a
derived `sensor.*` entity) + the HA core `template:`
binary_sensor wrapper (since 2022.x — wraps any upstream
sensor threshold into a derived `binary_sensor.*` entity)
+ the HA core `template:` switch wrapper (since 2022.x —
wraps any relay state into a virtual `switch.*` entity) +
the HA core `input_select` / `input_text` / `input_button`
/ `input_number` helper entities + the HA Companion app's
phone IMU (since 2022.x) + the ESPHome `mpu6050` /
`mpu9250` / `bno055` / `lsm6ds3` components (since 2022.x)
+ the HACS `mopeka` / `bno055` / `esp32_imu` integrations
(HACS) + the well-known pneumatic / hydraulic levelling
jacks driven via relay (the operator wires the relay
contacts to the head unit + the HA core `template:` switch
wrapper exposes the jack state), then publishes the
RoamCore leveling contract tiles on top (the 10 contract
entities documented in connection.yml — 1 sensor
pitch_degrees + 1 sensor roll_degrees + 1 sensor
max_tilt_degrees + 1 binary_sensor is_level + 1
binary_sensor is_close_to_level + 1 select mode + 1 sensor
last_calibrated_at + 1 button calibrate_now + 1 sensor
jack_status + 1 binary_sensor fridge_safe).

The audit + boundary CI can detect a `leveling/` folder that
claims to be a connection via the `DOMAIN` constant
exported here. The wizard reads the manifest + recipe at
runtime.

The real per-operator levelling affordance path is:

    Operator-side choice of ONE path (Path A — phone IMU
        via the HA Companion app on iOS / Android since
        2022.x; Path B — permanent IMU board via the
        ESPHome `mpu6050` / `mpu9250` / `bno055` /
        `lsm6ds3` components since 2022.x; Path C —
        levelling jacks via the HA core `template:`
        switch wrapper + relay; Path D — Bluetooth
        levelling pads via the HACS `mopeka` /
        `bno055` / `esp32_imu` integrations)
        -> upstream entity (HA core `sensor`
           integration's `sensor.<phone>_accelerometer`
           for Path A; the ESPHome integration's
           `sensor.<board>_mpu6050_accel_x` etc. for
           Path B; the HA core `switch.*` entity for
           Path C jack + pump control; the HACS
           `mopeka` integration's
           `sensor.<pad>_pitch` +
           `sensor.<pad>_roll` for Path D)
        -> RoamCore contract layer (HA core `template:`
           sensor + binary_sensor + select + the
           operator's `input_select` / `input_text` /
           `input_button` / `input_number` for the
           contract tiles + the `command_line`
           integration for the upstream reachability
           probe)
        -> dashboard tiles + OpenClaw queries
            ("are we level?",
             "what is the current pitch?",
             "what is the current roll?",
             "what is the max tilt?",
             "is the fridge safe to run?",
             "what is the leveling mode?",
             "when was the IMU last calibrated?",
             "calibrate the IMU now",
             "extend the levelling jacks",
             "is the sleep-mode warning active?")

    Safety interlocks (the recipe is the contract layer;
    the automation wrappers are documented in §8):
        -> The RoamCore auto-warn-when-out-of-level
           automation is the §8.1 automation that fires
           when the mode is `auto_warn` AND
           `sensor.rc_level_max_tilt_degrees > 1.5` for
           ≥ 30 s. The automation fires a persistent
           notification on the dashboard + (optionally)
           a Telegram message via the OpenClaw bridge.
        -> The RoamCore sleep-mode-warning automation is
           the §8.2 automation that fires when the mode
           is `auto_warn` AND `select.rc_mode` (from the
           mode/automation-builder Wave 2 #23 recipe) is
           in `sleep` mode AND
           `sensor.rc_level_max_tilt_degrees > 2.0`. The
           automation fires a critical notification on
           the bedroom tile + dims the cabin lights to
           red.
        -> The RoamCore fridge-safety-gate automation is
           the §8.3 automation that fires when the mode
           is `auto_warn` AND
           `binary_sensor.rc_level_fridge_safe`
           transitions from `true` to `false`. The
           automation fires an immediate notification
           warning the operator to turn off the fridge
           compressor (most compressor fridges tolerate
           ±3° but anything beyond that risks damage).
        -> The RoamCore auto-jack-extend automation is
           the §8.4 automation that fires when the mode
           is `auto_jack` AND the operator presses
           `button.rc_level_extend_jacks`. The automation
           fires the relay sequence to extend the 4 / 6
           jacks until
           `sensor.rc_level_max_tilt_degrees < 0.3` for
           ≥ 5 s, then stops the pump.
        -> The RoamCore calibration-reminder automation
           is the §8.5 automation that fires every 30
           days. The automation fires a notification
           reminding the operator to re-calibrate the
           IMU (the `button.rc_level_calibrate_now`
           button). The operator can dismiss the
           reminder.

    Cross-references:
        -> The HA core `sensor` integration is the
           canonical umbrella (since 2022.x — exposes
           the standard contract).
        -> The HA core `template:` sensor wrapper is
           the canonical pitch / roll / max_tilt
           derivation (since 2022.x).
        -> The HA core `template:` binary_sensor
           wrapper is the canonical is_level /
           is_close_to_level / fridge_safe derivation
           (since 2022.x).
        -> The HA core `template:` switch wrapper is
           the canonical Path C jack + pump control
           (since 2022.x).
        -> The HA Companion app on iOS / Android is
           the canonical Path A phone IMU source
           (since 2022.x).
        -> The ESPHome `mpu6050` / `mpu9250` /
           `bno055` / `lsm6ds3` components are the
           canonical Path B permanent IMU board
           firmware (since 2022.x).
        -> The HACS `mopeka` integration is the
           canonical Path D1 Mopeka Bluetooth pad
           integration (HACS).
        -> The HACS `bno055` integration is the
           canonical Path D2 Lippert Bluetooth pad
           integration (HACS).
        -> The HACS `esp32_imu` integration is the
           canonical Path D3 TireMinder Bluetooth pad
           integration (HACS).
        -> The HVAC basics Wave 3 #49 connection
           cross-references the cabin temperature
           sensor used by the §8.2 sleep-mode
           warning's cabin-light-dim behavior.
        -> The time-atomic Wave 3 #55 connection
           cross-references the time-of-day /
           sunrise-sunset primitives used by the §8.5
           calibration reminder.
        -> The mode/automation-builder recipe Wave 2
           #23 cross-references the `select.rc_mode`
           tile (the §8.2 sleep-mode warning's source
           of truth).
        -> The approach lights Wave 3 #52 connection
           cross-references the cabin lighting scene
           modified by the §8.2 sleep-mode warning.
        -> The fans Wave 3 #59 connection
           cross-references the §8.4 auto-jack
           extend's fan-off-on-tilt behavior.

See docs/recipe.md for the full howto (HA core `sensor`
integration install + HA core `template:` sensor wrapper
install + HA core `template:` binary_sensor wrapper
install + HA core `template:` switch wrapper install +
HA Companion app install + ESPHome `mpu6050` /
`mpu9250` / `bno055` / `lsm6ds3` component flash +
HACS `mopeka` / `bno055` / `esp32_imu` integration
install + Path A phone IMU wiring + Path B permanent IMU
board wiring (Path B1 ESPHome MPU-6050 + Path B2 ESPHome
MPU-9250 + Path B3 ESPHome BNO055 + Path B4 ESPHome
LSM6DS3) + Path C levelling jacks wiring (Path C1 HWH +
Path C2 Lippert + Path C3 Power Gear / Bigfoot) + Path D
Bluetooth pads wiring (Path D1 Mopeka + Path D2 Lippert +
Path D3 TireMinder) + the 10 `rc_level_*` contract tiles
+ the FIVE §8 MANDATORY automations + the 6 §9
troubleshooting entries + privacy + tier-a promotion
outline).
"""

DOMAIN = "leveling"