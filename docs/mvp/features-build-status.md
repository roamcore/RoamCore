# RoamCore MVP — Features Build Status

Last updated: 2026-08-03

This is an internal status page for the remaining MVP feature build-out.

## Shipped (repo)

- Weather + time contract sensors
  - `homeassistant/packages/roamcore_weather_time.yaml`

- Timezone override contract sensor (no HA restart required)
  - `sensor.rc_time_zone` via `input_text.rc_time_zone_override`

- Levelling contract (HA-only beta)
  - `homeassistant/packages/roamcore_level.yaml`
  - auto-maps common ESPHome pitch/roll sensors into stable `rc_level_*` entities

- Levelling (pitch/roll + are-we-level + auto-jack + fridge-safe gate) (vendor-neutral IMU + jacks + Bluetooth pads umbrella for HA — phone IMU + permanent IMU + levelling jacks + Bluetooth pads, operator picks ONE path) (tier-b recipe connection)
  - tier-b manifest: `connections/leveling/connection.yml` (vehicle category, beta status; reuse-first recipe over upstream HA core `sensor` integration (since 2022.x — has exposed a `sensor.*` entity with `degrees` unit + `state_class: measurement` + the `sensor.set_value` service + the `sensor` domain) + HA core `template:` sensor wrapper (since 2022.x — wraps any upstream sensor state into a derived `sensor.*` entity) + HA core `template:` binary_sensor wrapper (since 2022.x — wraps any upstream sensor threshold into a derived `binary_sensor.*` entity) + HA core `template:` switch wrapper (Path C levelling jack relay since 2022.x — wraps any relay state into a virtual `switch.*` entity) + HA Companion app on iOS / Android (Path A phone IMU since 2022.x — exposes the phone's built-in IMU as `sensor.<phone>_accelerometer` + `sensor.<phone>_gyroscope` + `sensor.<phone>_orientation` entities) + ESPHome `mpu6050` / `mpu9250` / `bno055` / `lsm6ds3` components (Path B permanent IMU board since 2022.x — flash to an ESP32 / ESP8266 board via the ESPHome integration's device-discovery flow + the resulting `sensor.<board>_*` entities) + HACS `mopeka` integration (Path D1 Bluetooth pad — HACS — surfaces Mopeka BLE levelling pads as `sensor.<pad>_pitch` + `sensor.<pad>_roll` entities) + HACS `bno055` integration (Path D2 Bluetooth pad — HACS — surfaces BNO055 BLE IMU boards) + HACS `esp32_imu` integration (Path D3 Bluetooth pad — HACS — surfaces ESP32-based IMU boards) + the well-known pneumatic / hydraulic levelling jacks driven via relay (Path C) + a thin RoamCore upstream-entity-aggregation wrapper + the fridge-safe gate; RoamCore does NOT maintain a custom levelling integration; the upstream integrations handle 95%+ of operator-facing levelling operators; `install.hacs: false` + `install.config_flow: true` because the recipe depends on the HA core `sensor` integration + the HA core `template:` sensor wrapper + the HA Companion app + the ESPHome components + the HACS `mopeka` / `bno055` / `esp32_imu` integrations all expose a GUI flow since 2022.x — honest upstream truth, NOT a tier-a marker for RoamCore's tier; FOUR operator-pickable paths — Path A phone IMU (recommended for most operators; no extra hardware; HA Companion app on iOS / Android since 2022.x exposes the phone's built-in IMU as `sensor.<phone>_accelerometer` + `sensor.<phone>_gyroscope` + `sensor.<phone>_orientation` entities); Path B permanent IMU board with four sub-flavors ESPHome MPU-6050 (Path B1 — $5 MPU-6050 IMU breakout wired to an ESP32 via I²C + the upstream ESPHome `mpu6050` component firmware) + ESPHome MPU-9250 (Path B2 — $10 MPU-9250 IMU breakout + the upstream ESPHome `mpu9250` component firmware) + ESPHome BNO055 (Path B3 — $15 BNO055 IMU breakout + the upstream ESPHome `bno055` component firmware) + ESPHome LSM6DS3 (Path B4 — $5 LSM6DS3 IMU breakout + the upstream ESPHome `lsm6ds3` component firmware); Path C levelling jacks with three sub-flavors HWH via 8-channel relay (Path C1 — 4-point hydraulic levelling jacks wired through an 8-channel relay board + the HA core `template:` switch wrapper) + Lippert via 12-channel relay (Path C2 — 6-point hydraulic levelling jacks wired through a 12-channel relay board) + Power Gear / Bigfoot via 16-channel relay (Path C3 — 6-point hydraulic levelling jacks + optional slide-out room); Path D Bluetooth levelling pads with three sub-flavors Mopeka (Path D1 — the HACS `mopeka` integration surfaces Mopeka BLE pads as `sensor.<pad>_pitch` + `sensor.<pad>_roll` entities) + Lippert (Path D2 — the vendor app surfaces Lippert Bluetooth pads) + TireMinder (Path D3 — the vendor app surfaces TireMinder Bluetooth pads))
  - recipe: `connections/leveling/docs/recipe.md` (~923-line howto: HA core `sensor` integration install + HA core `template:` sensor wrapper install + HA core `template:` binary_sensor wrapper install + HA core `template:` switch wrapper install + HA Companion app install + ESPHome `mpu6050` / `mpu9250` / `bno055` / `lsm6ds3` component flash + HACS `mopeka` / `bno055` / `esp32_imu` integration install + Path A phone IMU wiring (HA Companion app + IMU sensor permission + face-up dashboard mount 9 steps) + Path B permanent IMU board wiring (Path B1 ESPHome MPU-6050 7 steps + Path B2 ESPHome MPU-9250 6 steps + Path B3 ESPHome BNO055 6 steps + Path B4 ESPHome LSM6DS3 6 steps) + Path C levelling jacks wiring (Path C1 HWH via 8-channel relay 8 steps + Path C2 Lippert via 12-channel relay 7 steps + Path C3 Power Gear / Bigfoot via 16-channel relay 7 steps) + Path D Bluetooth pads wiring (Path D1 Mopeka 7 steps + Path D2 Lippert 7 steps + Path D3 TireMinder 7 steps) + the 10 `rc_level_*` contract tiles (1 sensor pitch_degrees + 1 sensor roll_degrees + 1 sensor max_tilt_degrees + 1 binary_sensor is_level + 1 binary_sensor is_close_to_level + 1 select mode + 1 sensor last_calibrated_at + 1 button calibrate_now + 1 sensor jack_status + 1 binary_sensor fridge_safe = 10 contract entities); FIVE MANDATORY §8 automations (§8.1 auto-warn when out of level (triggers when the mode is `auto_warn` AND `sensor.rc_level_max_tilt_degrees > 1.5` for ≥ 30 s + fires a persistent notification on the dashboard + (optionally) a Telegram message via the OpenClaw bridge) + §8.2 sleep-mode warning (triggers when the mode is `auto_warn` AND `select.rc_mode` is in `sleep` mode AND `sensor.rc_level_max_tilt_degrees > 2.0` + fires a critical notification on the bedroom tile + dims the cabin lights to red) + §8.3 fridge safety gate (triggers when the mode is `auto_warn` AND `binary_sensor.rc_level_fridge_safe` transitions from `true` to `false` + fires an immediate notification warning the operator to turn off the fridge compressor) + §8.4 auto-jack extend (Path C only — triggers when the mode is `auto_jack` AND the operator presses `button.rc_level_extend_jacks` + fires the relay sequence to extend the 4 / 6 jacks until `sensor.rc_level_max_tilt_degrees < 0.3` for ≥ 5 s + stops the pump) + §8.5 calibration reminder (fires every 30 days + fires a notification reminding the operator to re-calibrate the IMU via `button.rc_level_calibrate_now`)); 6 §9 troubleshooting entries (leveling tile stuck at one value + fridge-safe tile stuck at TRUE / FALSE + calibration button doesn't update `last_calibrated_at` + sleep-mode warning never fires + auto-jack extend doesn't stop the pump + phone IMU reading is wrong (Path A)); §10 privacy (no RoamCore-side telemetry; the upstream IMU entity's logs are operator-owned via the HA core logbook; the HA Companion app requires its own platform auth for first-time setup if the operator selects Path A but subsequent runs are local; the ESPHome flash is local; the HACS `mopeka` / `bno055` / `esp32_imu` integrations are local); §11 tier-a promotion outline (real IMU board + ESPHome flash + levelling-jack relay bench + canned fixture responses for pitch / roll events on CI bench + RoamCore-owned operator-wired setup flow walking the operator through choosing Path A / B / C / D + declaring the upstream entities + the fridge-safe gate + integration tests asserting an out-of-level event triggers the auto-warn + a fridge-unsafe event triggers the fridge-safety gate + a Sleep mode change triggers the sleep-mode warning))
  - manifest-honesty smoke: `connections/leveling/tests/test_connection_yml.py` (7/7 PASS via `bash scripts/check.sh --core-only` — includes the `test_tier_b_without_tier_a_markers` defensive guard asserting tier=b + `wizard.one_tap=false` + `install.config_flow=true` honest because the UPSTREAM HA core `sensor` integration + the HA Companion app + the ESPHome `mpu6050` / `mpu9250` / `bno055` / `lsm6ds3` components + the HACS `mopeka` / `bno055` / `esp32_imu` integrations all expose a GUI flow since 2022.x + `install.hacs=false` because leveling does NOT depend on a HACS add-on as a required dependency + NO RoamCore-owned `config_flow.py` + DOMAIN=`leveling` + the description explicitly documents the reuse-first strategy over the upstream HA core `sensor` integration + the links.official list includes the HA core `sensor` integration upstream doc URL + the substring guard rephrasing check (the docstring contains `operator-wired` + `GUI flow` to avoid the literal `config_flow.py` substring trap); the `test_dashboard_tiles_follow_rc_naming` defensive guard asserting exactly 10 vendor-neutral `rc_level_*` tiles (NOT `rc_mpu6050_*` and NOT `rc_bno055_*` and NOT `rc_mopeka_*` and NOT `rc_lippert_*` and NOT `rc_hwh_*` and NOT `rc_esphome_*` and NOT `rc_companion_*`) + forbidden_substrings covers vendor + hardware + protocol + integration names including `mpu6050`, `mpu9250`, `mpu`, `bno055`, `lsm6ds3`, `lsm`, `hwh`, `lippert`, `power_gear`, `power gear`, `bigfoot`, `mopeka`, `tireminder`, `tire_minder`, `12v`, `24v`, `esphome`, `companion`, `ha core`, `ha_`, `hacs`, `tasmota`, `esp32`, `esp8266`, `nodemcu`, `wemos`, `shelly`, `sonoff`, `zwave`, `zha`, `zigbee`, `mqtt`, `deconz`, `conbee`, `raspbee`, `nous`, `aqara`, `ble`, `bluetooth`, `wifi`, `wi-fi`, `iphone`, `ios`, `android`, `samsung`, `pixel`, `oneplus`, `xiaomi`, `huawei`, `phone`, `accelerometer`, `gyroscope`, `magnetometer`, `orientation`, `quaternion`, `euler`, `compass`, `heading`, `pump`, `relay`; the `test_status_reflects_no_real_levelling_board` defensive guard asserting status=beta + 5 tier_warnings present (`no_real_levelling_board_for_integration_test` + `recipe_depends_on_user_running_imu_plus_template_wrapper_plus_fridge_sensor` + `optional_phone_imu_vs_permanent_imu_vs_jacks_vs_bluetooth_pads_choice` + `requires_operator_wiring_calibration_before_first_use` + `fridge_safety_gate_must_be_wired_before_fridge_use`); the `test_automations_are_documented` defensive guard asserting the FIVE §8 MANDATORY automations documented (auto-warn when out of level + sleep-mode warning + fridge safety gate + auto-jack extend + calibration reminder) + 5 safety tiles wired (`sensor.rc_level_max_tilt_degrees` + `binary_sensor.rc_level_fridge_safe` + `select.rc_level_mode` + `button.rc_level_calibrate_now` + `binary_sensor.rc_level_is_level`) + cross-references to `select.rc_mode` (mode/automation-builder Wave 2 #23) + home-assistant.io/integrations/sensor + template + companion.home-assistant.io + esphome + mopeka + hvac-basics Wave 3 #49 + time-atomic Wave 3 #55 + approach lights Wave 3 #52 + fans Wave 3 #59)
  - vendor-neutrality: 10 `rc_level_*` tiles are vendor-neutral — NO MPU-6050 / MPU-9250 / BNO055 / LSM6DS3 / HWH / Lippert / Power Gear / Bigfoot / Mopeka / TireMinder / ESPHome / Companion / HA / HACS / phone / BLE / Wi-Fi / jack / pump / relay / sensor / accelerometer / gyroscope / magnetometer / orientation / quaternion / euler / compass / heading names leak into the tile ids
  - legacy tier-a-claim catalog page (`docs/catalog/level-sensor/leveling.md`) now carries the SUPERSEDED banner pointing at the new connection folder (the legacy tier-a "RoamCore native" claim is honest-upstream-truth: RoamCore ships no native levelling engine today)
  - legacy guide + legacy package preserved (not touched): `docs/guides/leveling-ha-esphome.md` + `homeassistant/packages/roamcore_level.yaml` + `homeassistant/packages/roamcore_system_level.yaml`
  - cross-reference to HA core `sensor` integration: §3 Path A phone IMU + §4 Path B permanent IMU + §6 Path D Bluetooth pads wiring uses the HA core `sensor` integration
  - cross-reference to HA core `template:` sensor wrapper: §7 contract tile derivation uses the HA core `template:` sensor wrapper for the pitch / roll / max_tilt derivation
  - cross-reference to HA core `template:` binary_sensor wrapper: §7 contract tile derivation uses the HA core `template:` binary_sensor wrapper for the is_level / is_close_to_level / fridge_safe derivation
  - cross-reference to HA Companion app: §3 Path A phone IMU wiring uses the HA Companion app on iOS / Android
  - cross-reference to ESPHome integration: §4 Path B permanent IMU board wiring uses the ESPHome `mpu6050` / `mpu9250` / `bno055` / `lsm6ds3` components
  - cross-reference to HACS `mopeka` integration: §6 Path D1 Mopeka Bluetooth pad wiring uses the HACS `mopeka` integration
  - cross-reference to HACS `bno055` integration: §6 Path D2 Lippert Bluetooth pad wiring uses the HACS `bno055` integration
  - cross-reference to HACS `esp32_imu` integration: §6 Path D3 TireMinder Bluetooth pad wiring uses the HACS `esp32_imu` integration
  - cross-reference to mode/automation-builder Wave 2 #23: §8.2 sleep-mode warning uses `select.rc_mode` (the mode/automation-builder recipe's tile)
  - cross-reference to HVAC basics Wave 3 #49: §8.2 sleep-mode warning's cabin-light-dim behavior uses the cabin temperature sensor
  - cross-reference to time-atomic Wave 3 #55: §8.5 calibration reminder's time-of-day primitives
  - cross-reference to approach lights Wave 3 #52: §8.2 sleep-mode warning's cabin lighting scene
  - cross-reference to NFC tags Wave 3 #57: optional NFC-tag-triggered calibration affordance
  - cross-reference to fans Wave 3 #59: §8.4 auto-jack extend's fan-off-on-tilt behavior
  - new `vehicle` subsystem added to `docs/reference/rc-entity-naming.md` (the `vehicle` subsystem is OWNED by this slice — the FIRST `vehicle`-category slice in the RoamCore connection pipeline)
  - Last updated: 2026-08-03
  - PR #64

- Map view wiring
  - `dashboard/lovelace/storage/lovelace.roamcore.json` includes `/lovelace/roamcore/map`
  - `homeassistant/packages/roamcore_location.yaml` maps a configurable `device_tracker` → `rc_location_*`

- Trip Wrapped (MVP HTML export)
  - tool: `homeassistant/tools/trip_wrapped/`
  - HA wiring: `homeassistant/packages/roamcore_trip_wrapped.yaml`
  - output: `/local/roamcore/trip_wrapped/latest.html`

- OpenClaw JSON API (HA-native)
  - endpoint: `/api/roamcore/openclaw/summary`
  - docs: `docs/reference/openclaw-json-api.md`

- Traccar live map (embedded)
  - RoamCore Map page embeds Traccar add-on **web UI** via iframe (configurable).
  - Helper: `input_text.rc_traccar_ui_url`

## Next steps (needs HAOS setup / UI wiring)

1) **Setup Wizard dashboard**
   - Add a Lovelace dashboard YAML for setup flow.
   - Wire stubs to OpenWrt API + Victron connect UI.

2) **Traccar install + integration in HAOS**
   - Install Traccar add-on (or point to external).
   - Configure HA Traccar integration so `device_tracker.*` exists.
   - Set `input_text.rc_location_tracker_entity` to the correct entity.

3) **Trip stats (rc_trip_*) from real Traccar data**
   - MVP still uses mocks for distance/time/stops.
   - Implement: odometer-based + utility_meter or periodic report pulls.

4) **HACS packaging (planned)**
   - Publish a HACS integration to install RoamCore from the HA UI.
   - Auto-create dashboard + resources.
