# Plan: Levelling (HA-only beta) via ESPHome IMU

## Scope
Provide a stable RoamCore levelling contract in Home Assistant for the beta period **without** requiring a custom integration.

## Architecture
- **ESPHome node** publishes IMU-derived pitch/roll sensors (degrees) into Home Assistant.
- **Home Assistant package** implements the RoamCore contract (`rc_level_*`) as template entities.
- **Auto-mapping** picks the first available upstream sensor from a curated list of common ESPHome entity_id patterns.
- **Calibration** is HA-native: store offsets in helpers (`input_number`) and compute corrected values in templates.

## Contract entities (UI-facing)
- `sensor.rc_level_pitch_deg`
- `sensor.rc_level_roll_deg`
- `sensor.rc_level_pitch_raw_deg`
- `sensor.rc_level_roll_raw_deg`
- `sensor.rc_level_status` (`level|close|adjust`)
- `sensor.rc_level_adjustment_hint`
- `binary_sensor.rc_level`
- `button.rc_level_calibrate`
- `input_number.rc_level_pitch_offset_deg`, `input_number.rc_level_roll_offset_deg`

## Upstream naming recommendation (ESPHome)
Publish degrees as one of:
- `sensor.pitch_deg` + `sensor.roll_deg` (preferred)
- or `sensor.imu_pitch_deg` + `sensor.imu_roll_deg`

## Calibration UX
1. User levels the platform.
2. Press `RC Level Calibrate`.
3. Offsets are set to current raw values.
4. Corrected pitch/roll become ~0° when in the reference position.

## Future upgrades
- Replace auto-mapping list with a selectable source (`select.rc_level_source`) once multiple IMU nodes are common.
- Move the mapping logic into a RoamCore custom integration if/when more complex transforms are needed.
- Consider adding yaw/heading, stability metrics, and filtering at the ESPHome layer.
