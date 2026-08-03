# Leveling (vendor-neutral IMU + jacks + Bluetooth pads umbrella for HA — phone IMU + permanent IMU + levelling jacks + Bluetooth pads, operator picks ONE path)

**Tier:** B (recipe)
**Category:** vehicle
**Status:** beta

## What this connection is

Leveling (vendor-neutral IMU + jacks + Bluetooth pads umbrella for HA, covering phone IMU + permanent IMU board + levelling jacks + Bluetooth pads — phone IMU covers the most-asked user-facing question "Are we level?" without extra hardware; permanent IMU board covers the always-on / reliable reading; levelling jacks cover the auto-extend / auto-retract affordance for motorhomes; Bluetooth pads cover the aftermarket pad-mounted levelling) — the umbrella for "Better sleep and cooking. Quick 'good enough' check without guessing" — is the vehicle-category complement to the broader RoamCore comfort affordances. The single "are we level?" tile aggregates the upstream pitch / roll into one dashboard indicator; the "pitch" tile surfaces the current pitch in degrees; the "roll" tile surfaces the current roll in degrees; the "max tilt" tile is the max of `|pitch|` + `|roll|`; the "is level" tile is the strict level gate (TRUE iff max_tilt < 0.5°); the "is close to level" tile is the relaxed level gate (TRUE iff max_tilt < 1.5°); the "mode" selector is the operator-facing affordance (one of `off` / `read_only` / `auto_warn` / `auto_jack`); the "last calibrated at" tile surfaces the timestamp of the last operator-initiated calibration; the "calibrate now" button is the operator-triggered calibration (touches the calibration offset and updates last_calibrated_at); the "jack status" tile surfaces the jack state (only when Path C jacks are wired); the "fridge safe" tile is the §8 MANDATORY automation target (TRUE iff the fridge is safe to run).

RoamCore ships **no** native levelling engine. We RECIPE the well-understood upstream HA core `sensor` integration (since 2022.x — has exposed a `sensor.*` entity with `degrees` unit + `state_class: measurement` + the `sensor.set_value` service + the `sensor` domain since 2022.x) + the HA core `template:` sensor wrapper (since 2022.x — wraps any upstream sensor state into a derived `sensor.*` entity that exposes the standard `state` attribute) + the HA core `template:` binary_sensor wrapper (since 2022.x — wraps any upstream sensor threshold into a derived `binary_sensor.*` entity) + the HA core `template:` switch wrapper (since 2022.x — wraps any relay state into a virtual `switch.*` entity) + the HA Companion app on iOS / Android (since 2022.x — exposes the phone's built-in IMU as `sensor.<phone>_accelerometer` + `sensor.<phone>_gyroscope` + `sensor.<phone>_orientation` entities) + the ESPHome `mpu6050` / `mpu9250` / `bno055` / `lsm6ds3` components (since 2022.x — flash to an ESP32 / ESP8266 board via the ESPHome integration's device-discovery flow + the resulting `sensor.<board>_*` entities) + the HACS `mopeka` / `bno055` / `esp32_imu` integrations (HACS — surfaces Mopeka / Lippert / TireMinder BLE levelling pads + BNO055 BLE IMU boards + ESP32-based IMU boards as `sensor.*` entities). The 10 `rc_level_*` contract tiles are the vendor-neutral layer the dashboard + OpenClaw queries use; the actual levelling path is provided by the upstream HA core `sensor` integration + the HA core `template:` sensor wrapper + the HA core `template:` binary_sensor wrapper + the HA core `template:` switch wrapper + the HA Companion app + the ESPHome components + the HACS `mopeka` / `bno055` / `esp32_imu` integrations + the well-known pneumatic / hydraulic levelling jacks driven via relay (RoamCore does NOT fork any of these).

## The 4 operator-pickable paths

- **Path A — Phone IMU (recommended for most operators; no extra hardware).** Default for operators who already have a smartphone + don't want extra hardware. The HA Companion app on iOS / Android exposes the phone's built-in IMU (the accelerometer + gyroscope) as `sensor.<phone>_accelerometer` + `sensor.<phone>_gyroscope` + `sensor.<phone>_orientation` entities (since 2022.x). The operator picks a phone, mounts it face-up on the dashboard, and the RoamCore contract tiles publish from the phone's orientation.

- **Path B — Permanent IMU board (ESPHome + MPU-6050 / MPU-9250 / BNO055 / LSM6DS3).** Default for vans that want a permanent / reliable reading. Path B1 — ESPHome MPU-6050 ($5 IMU breakout wired to an ESP32 via I²C + the upstream ESPHome `mpu6050` component firmware). Path B2 — ESPHome MPU-9250 ($10 IMU breakout + the upstream ESPHome `mpu9250` component firmware). Path B3 — ESPHome BNO055 ($15 IMU breakout + the upstream ESPHome `bno055` component firmware). Path B4 — ESPHome LSM6DS3 ($5 IMU breakout + the upstream ESPHome `lsm6ds3` component firmware).

- **Path C — Levelling jacks (HWH / Lippert / Power Gear / Bigfoot via relay + manual control).** Default for motorhomes / Class A / Class C with factory jacks. The 4-point / 6-point hydraulic levelling jacks wired through an 8-channel / 12-channel / 16-channel relay board to the head unit. Path C1 — HWH via 8-channel relay + the HA core `template:` switch wrapper for the pump + each of the 4 jacks. Path C2 — Lippert via 12-channel relay + the HA core `template:` switch wrapper for the pump + each of the 6 jacks. Path C3 — Power Gear / Bigfoot via 16-channel relay + the HA core `template:` switch wrapper for the pump + each of the 6 jacks + the optional slide-out room.

- **Path D — Bluetooth levelling pads (Mopeka / Lippert / TireMinder).** Default for vans that already have the pads. The optional HACS `mopeka` integration (and the Lippert / TireMinder Bluetooth levelling pads) expose a `sensor.<pad>_pitch` + `sensor.<pad>_roll` entity over BLE. Path D1 — Mopeka (the HACS `mopeka` integration). Path D2 — Lippert (the HA core `sensor` integration via the vendor app). Path D3 — TireMinder (the HA core `sensor` integration via the vendor app).

## Setup recipe (one-paragraph)

1. Pick ONE of the four paths (Path A — phone IMU; Path B — permanent IMU board with four sub-flavors ESPHome MPU-6050 / ESPHome MPU-9250 / ESPHome BNO055 / ESPHome LSM6DS3; Path C — levelling jacks with three sub-flavors HWH / Lippert / Power Gear / Bigfoot; Path D — Bluetooth pads with three sub-flavors Mopeka / Lippert / TireMinder).
2. Set up the chosen path:
   - **Path A — Phone IMU:** install the HA Companion app on the operator's phone + enable the IMU sensor permission + mount the phone face-up on the dashboard + verify the upstream `sensor.<phone>_accelerometer` + `sensor.<phone>_gyroscope` + `sensor.<phone>_orientation` entities exist.
   - **Path B — Permanent IMU board:** wire the IMU breakout to the ESP32 via I²C + flash the upstream ESPHome `mpu6050` / `mpu9250` / `bno055` / `lsm6ds3` firmware to the ESP32 via the ESPHome integration's device-discovery flow + verify the upstream `sensor.<board>_*` entities exist.
   - **Path C — Levelling jacks:** wire the 8-channel / 12-channel / 16-channel relay board to the head unit + create `template:` switch wrappers for the pump + each of the 4 / 6 jacks.
   - **Path D — Bluetooth pads:** install the HACS `mopeka` integration OR the vendor app + wire the BLE adapter + mount the pads under each corner of the van + verify the upstream `sensor.<pad>_pitch` + `sensor.<pad>_roll` entities exist.
3. Configure the operator-facing `sensor.rc_level_pitch_degrees` + `sensor.rc_level_roll_degrees` contract tiles to point at the operator's chosen upstream `sensor.*` entities.
4. Configure `sensor.rc_level_max_tilt_degrees` + `binary_sensor.rc_level_is_level` + `binary_sensor.rc_level_is_close_to_level` + `binary_sensor.rc_level_fridge_safe` to derive from the upstream entities.
5. Configure `select.rc_level_mode` to the operator's chosen starting mode (default `read_only`).
6. Press `button.rc_level_calibrate_now` once to seed the calibration offset (REQUIRED before first use — the fridge-safe tile depends on a calibrated zero).
7. Wire the FIVE §8 MANDATORY automations (auto-warn when out of level + sleep-mode warning + fridge safety gate + auto-jack extend (Path C only) + calibration reminder).
8. Verify: check `binary_sensor.rc_level_is_level` reflects the upstream tilt + trigger `button.rc_level_calibrate_now` + verify `sensor.rc_level_last_calibrated_at` updates.

Full howto: see [`docs/recipe.md`](docs/recipe.md).

## Why tier-b, not tier-a

Tier-a would require a RoamCore-owned levelling engine + integration code + integration tests against a real levelling bench (a controlled environment with an ESPHome-flashed IMU board + a 4-jack relay bench + a Mopeka BLE adapter + canned fixture responses for pitch / roll / fridge-unsafe events — all wired together in a controlled environment). We have no operator-side levelling bench on the CI to integration-test against (the bench requires the operator's chosen upstream IMU + a 4-jack relay bench + a Bluetooth adapter + canned fixture responses for pitch / roll / fridge-unsafe events — all wired together in a controlled environment). Tier-b is the honest tier: MPU-6050 / MPU-9250 / BNO055 / LSM6DS3 / HWH / Lippert / Power Gear / Bigfoot / Mopeka / TireMinder / ESPHome / Companion / HA / HACS are all upstream / vendor / HACS / hardware code (not RoamCore-owned); the RoamCore wrapper is a thin upstream-entity-aggregation layer + the contract layer + the fridge-safe gate + the §8 MANDATORY automations. The recipe is sound but we cannot claim one-tap automation.

The legacy catalog page (the legacy spec — 18-line tier-a claim stub, originally listed "RoamCore defines a levelling contract (`rc_level_*`) and supports pitch/roll sensors so the dashboard can show an easy levelling status. Better sleep and cooking. Quick 'good enough' check without guessing. A pitch/roll sensor (often via ESPHome / accelerometer)" with no recipe + no contract + no automations + no install path — just a placeholder) is now superseded by this tier-b recipe connection. The legacy tier-a claim was aspirational (no native RoamCore levelling engine in the repo today); the picker is honest and ships the contract layer + the recipe + the §8 automations as tier-b.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "leveling"` marker for the audit.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded by this slice): [the legacy spec](../../the legacy spec)
- HA core `sensor` integration (the canonical umbrella): https://www.home-assistant.io/integrations/sensor/
- HA core `template:` sensor wrapper (the canonical pitch / roll / max_tilt derivation): https://www.home-assistant.io/integrations/template/
- HA Companion app (the canonical Path A phone IMU source): https://companion.home-assistant.io/
- ESPHome integration (the canonical Path B permanent IMU board wiring): https://www.home-assistant.io/integrations/esphome/
- HACS `mopeka` integration (the canonical Path D1 Mopeka BLE pad integration): https://hacs.xyz/docs/integrations/active
- HACS `bno055` integration (the canonical Path D2 Lippert BLE pad integration): https://hacs.xyz/docs/integrations/active
- HACS `esp32_imu` integration (the canonical Path D3 TireMinder BLE pad integration): https://hacs.xyz/docs/integrations/active
- HVAC basics (the cabin temperature sensor used by the §8.2 sleep-mode warning's cabin-light-dim behavior): `connections/hvac-basics/` (Wave 3 #49)
- Time-atomic (the time-of-day / sunrise-sunset primitives used by the §8.5 calibration reminder): `connections/time-atomic/` (Wave 3 #55)
- Mode/automation-builder (the `select.rc_mode` tile source of truth for the §8.2 sleep-mode warning): `connections/smart-automations/` (Wave 2 #23)
- Approach lights (the cabin lighting scene modified by the §8.2 sleep-mode warning): `connections/approach-lights/` (Wave 3 #52)
- NFC tags (the optional NFC-tag-triggered calibration affordance that uses NFC scan events to trigger `button.rc_level_calibrate_now`): `connections/nfc-tags/` (Wave 3 #57)
- Fans (the §8.4 auto-jack extend's fan-off-on-tilt behavior cross-reference): `connections/fans/` (Wave 3 #59)
- RoamCore entity naming: `docs/reference/rc-entity-naming.md` (the `vehicle` subsystem was added by this slice)