# Levelling (HA-only beta) with ESPHome IMU

This guide describes the RoamCore **HA-only beta** levelling implementation.

## What you get (contract entities)
The RoamCore UI/automations should reference **only** the contract entities below:

- `sensor.rc_level_pitch_deg` — corrected pitch (degrees)
- `sensor.rc_level_roll_deg` — corrected roll (degrees)
- `sensor.rc_level_pitch_raw_deg` — raw pitch from IMU (degrees)
- `sensor.rc_level_roll_raw_deg` — raw roll from IMU (degrees)
- `binary_sensor.rc_level` — `on` when within tolerance
- `sensor.rc_level_status` — `level | close | adjust`
- `sensor.rc_level_adjustment_hint` — human-readable hint
- `button.rc_level_calibrate` — stores current raw values as offsets
- `input_number.rc_level_pitch_offset_deg` / `input_number.rc_level_roll_offset_deg` — calibration offsets

Naming convention reference:
- `docs/reference/rc-entity-naming.md`

## How the mapping works (auto-detect)
The HA package `homeassistant/packages/roamcore_level.yaml` **auto-detects** an upstream ESPHome entity for pitch/roll by scanning a list of common `sensor.*` entity_ids (e.g. `sensor.pitch`, `sensor.imu_pitch_deg`, `sensor.tilt_roll_deg`, etc.).

You can see what it selected here:
- `sensor.rc_level_pitch_source`
- `sensor.rc_level_roll_source`

If nothing matches, the contract entities will be `unknown`/`unavailable`.

### Recommended ESPHome entity naming
To make auto-detection work reliably, publish **degrees** as one of:
- `sensor.pitch_deg` and `sensor.roll_deg` (simple)
- or `sensor.imu_pitch_deg` and `sensor.imu_roll_deg`

## Calibration flow (HA-native)
1. Place the vehicle/trailer/platform in the desired *"level"* reference position.
2. Wait for the raw pitch/roll to settle.
3. Press: `button.rc_level_calibrate`
4. This stores the current raw pitch/roll into:
   - `input_number.rc_level_pitch_offset_deg`
   - `input_number.rc_level_roll_offset_deg`
5. The corrected sensors are computed as:
   - `rc_level_pitch_deg = rc_level_pitch_raw_deg - rc_level_pitch_offset_deg`
   - `rc_level_roll_deg = rc_level_roll_raw_deg - rc_level_roll_offset_deg`

You can also manually tweak the offsets in HA if needed.

## Home Assistant setup
### 1) Enable packages (if not already)
Your HA `configuration.yaml` needs packages enabled, e.g.:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

### 2) Add the RoamCore levelling package
This repo provides:

- `homeassistant/packages/roamcore_level.yaml`

Copy it into your HA `packages/` directory (or symlink it, depending on your deployment) and restart Home Assistant.

## Reference ESPHome config (MPU6050)
This example publishes `sensor.pitch_deg` and `sensor.roll_deg` using an MPU6050.

> Notes:
> - Wiring and I2C pins vary per board.
> - This is a reference snippet; adapt pins, Wi‑Fi/API, and board settings.

```yaml
esphome:
  name: rc-imu
  friendly_name: RC IMU

esp32:
  board: esp32dev
  framework:
    type: arduino

# --- Connectivity (fill in for your environment) ---
logger:
api:
ota:

i2c:
  sda: 21
  scl: 22
  scan: true

mpu6050:
  address: 0x68
  update_interval: 200ms

sensor:
  # Raw accelerometer (m/s^2)
  - platform: mpu6050
    accel_x:
      name: "Accel X"
      id: accel_x
    accel_y:
      name: "Accel Y"
      id: accel_y
    accel_z:
      name: "Accel Z"
      id: accel_z

  # Compute pitch/roll from gravity vector.
  # Convention used here:
  # - roll: rotation around X axis
  # - pitch: rotation around Y axis
  - platform: template
    name: "Pitch"
    id: pitch_deg
    unit_of_measurement: "°"
    device_class: "angle"
    state_class: "measurement"
    update_interval: 200ms
    lambda: |-
      const float ax = id(accel_x).state;
      const float ay = id(accel_y).state;
      const float az = id(accel_z).state;
      // pitch = atan2(-ax, sqrt(ay^2 + az^2))
      return atan2f(-ax, sqrtf(ay*ay + az*az)) * 180.0f / (float) M_PI;

  - platform: template
    name: "Roll"
    id: roll_deg
    unit_of_measurement: "°"
    device_class: "angle"
    state_class: "measurement"
    update_interval: 200ms
    lambda: |-
      const float ax = id(accel_x).state;
      const float ay = id(accel_y).state;
      const float az = id(accel_z).state;
      // roll = atan2(ay, az)
      return atan2f(ay, az) * 180.0f / (float) M_PI;

  # Optional: publish with contract-friendly entity_ids (helps the auto-detector).
  # In Home Assistant these become sensor.pitch and sensor.roll by default.
  # If you prefer explicit names, set:
  #   name: "Pitch Deg"  -> sensor.pitch_deg
  #   name: "Roll Deg"   -> sensor.roll_deg
```

### BNO085/BNO08x note
BNO08x sensors can provide fused orientation that is often more stable than raw-accelerometer-only pitch/roll. If you use BNO08x, publish pitch/roll as `sensor.pitch_deg` + `sensor.roll_deg` (or `sensor.imu_pitch_deg`/`sensor.imu_roll_deg`) so the RoamCore mapping layer finds them.

## Troubleshooting
- **`rc_level_*` is `unknown`:** check `sensor.rc_level_pitch_source` / `sensor.rc_level_roll_source`.
- **Pitch/roll look swapped or inverted:** IMU axis conventions depend on mounting orientation. Adjust the ESPHome template math or swap axes.
- **Noisy readings:** increase `update_interval`, add a moving average filter in ESPHome, or use an IMU that provides fused orientation.
