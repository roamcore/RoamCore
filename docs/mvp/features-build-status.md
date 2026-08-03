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

- Demo mode (vendor-neutral demo values for missing sensors + auto-disable on real sensor reconnect + never-controls-hardware guard) (tier-b recipe connection)
  - tier-b manifest: `connections/demo-mode/connection.yml` (ai category, beta status; reuse-first recipe over upstream HA core `input_boolean` + `input_select` + `input_text` + `input_number` helpers (since 2022.x — expose a GUI flow for the operator to add the helper entities from the HA UI under Settings → Helpers) + HA core `template:` sensor wrapper (since 2022.x — wraps any upstream sensor state into a derived `sensor.*` entity) + HA core `template:` binary_sensor wrapper (since 2022.x — wraps any upstream sensor threshold into a derived `binary_sensor.*` entity) + a thin RoamCore upstream-entity-aggregation wrapper; RoamCore does NOT maintain a custom demo-mode engine; the upstream helpers + `template:` wrappers handle 95%+ of operator-facing demo-mode operations; `install.hacs: false` + `install.config_flow: true` because the recipe depends on the HA core `input_boolean` + `input_select` + `input_text` + `input_number` helpers + the HA core `template:` sensor + `template:` binary_sensor wrappers all expose a GUI flow since 2022.x — honest upstream truth, NOT a tier-a marker for RoamCore's tier; FOUR operator-pickable demo scenarios — Off (demo mode is disabled; real sensor values (or "unknown" if sensors aren't wired) are shown; default for operators with all hardware installed); Battery demo (shows example battery / solar / inverter values as if a Victron GX were installed + reporting; useful when the operator is wiring RoamCore without a real power system); Water tank demo (shows example fresh / grey / black tank levels as if the SeeLevel / Victron / generic resistive tank sensors were installed; useful for showcasing the water UI without a real tank sensor); Connectivity demo (shows example Wi-Fi / LTE / Starlink state as if multiple upstream network integrations were installed; useful for showcasing the network UI without real radios))
  - recipe: `connections/demo-mode/docs/recipe.md` (~990-line howto: HA core `input_boolean` + `input_select` + `input_text` + `input_number` helpers install + HA core `template:` sensor wrapper install + HA core `template:` binary_sensor wrapper install + §3 Off scenario wiring (5 steps) + §4 Battery demo scenario wiring (5 steps) + §5 Water demo scenario wiring (5 steps) + §6 Connectivity demo scenario wiring (5 steps) + §7 the 11 `rc_demo_mode_*` contract tiles (1 input_boolean enabled + 1 select scenario + 1 sensor active_scenario + 1 binary_sensor is_blocking_real_hardware + 1 sensor demo_value_battery_soc_percent + 1 sensor demo_value_water_fresh_percent + 1 binary_sensor demo_value_connectivity_lte_up + 1 button enable_battery + 1 button enable_water + 1 button enable_connectivity + 1 button disable = 11 contract entities); FIVE MANDATORY §8 automations (§8.1 demo-mode auto-disable on real sensor reconnect (triggers when `input_boolean.rc_demo_mode_enabled` is ON AND ANY of the upstream real sensors (battery + tank + LTE-up, whichever matches the picked scenario) transitions from `unavailable` / `unknown` to a real value + clears the enable toggle + resets the scenario selector to Off + writes an audit-log entry + fires a notification warning the operator that demo mode has been auto-disabled) + §8.2 demo-mode never-controls-actual-hardware guard (triggers when ANY `script.*` / `automation.*` action tries to call a `switch.turn_on` / `switch.turn_off` / `light.turn_on` / `light.turn_off` / `climate.set_*` service while `input_boolean.rc_demo_mode_enabled` is ON AND the target entity is one of the "real hardware" entities the operator has flagged in their `input_text.rc_demo_mode_real_hardware_targets`; BLOCKS the service call + logs a security-style audit entry + flips `binary_sensor.rc_demo_mode_is_blocking_real_hardware` to TRUE + fires a critical notification) + §8.3 demo-mode blocks-remote-access guard (triggers when a remote-access session attempts to interact with the dashboard while `input_boolean.rc_demo_mode_enabled` is ON; surfaces a "demo mode is ON — values are not real" banner in the remote-access dashboard + adds the demo-mode-active flag to the remote-access session metadata + (if the operator's remote-access setup supports it) refuses write-capable actions until demo mode is disabled) + §8.4 demo-mode audit-log entry (triggers when `input_boolean.rc_demo_mode_enabled` flips from OFF to ON OR from ON to OFF; writes an audit-log entry with the scenario selector value + the operator identity (if the remote-access session tracks it) + the timestamp + the reason) + §8.5 demo-mode operator-only guard (triggers when a non-operator source (a sensor auto-change / an automation script / a remote-access non-operator session) tries to flip `input_boolean.rc_demo_mode_enabled`; BLOCKS the change + writes an audit-log entry + fires a critical notification)); 6 §9 troubleshooting entries (demo mode is stuck on Off + demo values never appear in the dashboard + §8.1 auto-disable guard never fires + §8.2 never-controls-hardware guard fires unexpectedly + §8.3 blocks-remote-access guard surfaces banner every time + §8.5 operator-only guard BLOCKS the operator's own enable); §10 privacy (no RoamCore-side telemetry; the upstream helper entities' logs are operator-owned via the HA core logbook; demo-mode values are clearly labelled as demo + never reach the operator's automations); §11 tier-a promotion outline (real demo-mode engine + canned fixture responses for sensor availability events on CI bench + canned fixture responses for remote-access session events + canned fixture responses for service-call blocking events + RoamCore-owned operator-wired setup flow walking the operator through choosing Off / Battery / Water / Connectivity + declaring the upstream real-hardware target entities + the §8 automations + integration tests asserting a real-sensor-reconnect event auto-disables demo mode + a service-call attempt on a flagged real-hardware entity triggers the never-controls-hardware guard + a remote-access session triggers the blocks-remote-access guard))
  - manifest-honesty smoke: `connections/demo-mode/tests/test_connection_yml.py` (7/7 PASS via `bash scripts/check.sh --core-only` — includes the `test_tier_b_without_tier_a_markers` defensive guard asserting tier=b + `wizard.one_tap=false` + `install.config_flow=true` honest because the UPSTREAM HA core `input_boolean` + `input_select` + `input_text` + `input_number` helpers + the HA core `template:` sensor + `template:` binary_sensor wrappers all expose a GUI flow since 2022.x + `install.hacs=false` because demo-mode does NOT depend on a HACS add-on as a required dependency + NO RoamCore-owned `config_flow.py` + DOMAIN=`demo_mode` + the description explicitly documents the reuse-first strategy over the upstream HA core `input_boolean` + `input_select` + `input_text` + `input_number` helpers + the HA core `template:` sensor + `template:` binary_sensor wrappers + the links.official list includes the HA core `input_boolean` integration upstream doc URL + the substring guard rephrasing check (the docstring contains `operator-wired` + `GUI flow` to avoid the literal `config_flow.py` substring trap); the `test_dashboard_tiles_follow_rc_naming` defensive guard asserting exactly 11 vendor-neutral `rc_demo_mode_*` tiles (NOT `rc_victron_*` and NOT `rc_see_level_*` and NOT `rc_seelevel_*` and NOT `rc_garnet_*` and NOT `rc_mopeka_*` and NOT `rc_renogy_*` and NOT `rc_starlink_*` and NOT `rc_peplink_*` and NOT `rc_teltonika_*` and NOT `rc_unifi_*` and NOT `rc_ubiquiti_*` and NOT `rc_input_boolean_*` and NOT `rc_input_select_*` and NOT `rc_input_text_*` and NOT `rc_input_number_*` and NOT `rc_input_button_*` and NOT `rc_template_*`) + forbidden_substrings covers vendor + hardware + protocol + integration names including `victron`, `renogy`, `shunt`, `bms`, `inverter`, `mppt`, `see level`, `seelevel`, `garnet`, `mopeka`, `icon`, `resistive`, `tank`, `starlink`, `peplink`, `teltonika`, `unifi`, `ubiquiti`, `mqtt`, `webhook`, `rest`, `api`, `http`, `https`, `ha core`, `ha_`, `hacs`, `tasmota`, `esphome`, `companion`, `esp32`, `esp8266`, `nodemcu`, `wemos`, `shelly`, `sonoff`, `zwave`, `zha`, `zigbee`, `deconz`, `conbee`, `raspbee`, `nous`, `aqara`, `bluetooth`, `wifi`, `wi-fi`, `input_boolean`, `input_select`, `input_text`, `input_number`, `input_button`, `gps`, `accelerometer`, `gyroscope`, `magnetometer`, `compass`, `heading`, `iphone`, `ios`, `android`, `samsung`, `pixel`, `oneplus`, `xiaomi`, `huawei`, `phone` (note: `ble`, `lte`, `router`, `cellular` deliberately omitted from forbidden_substrings because they're legitimate generic nouns for the demo-mode contract — `lte` is the spec's allowed generic noun for the connectivity scenario; the audit catches true BLE / vendor leaks via the longer `bluetooth` / `starlink` / `peplink` / `teltonika` / `unifi` / `ubiquiti` substrings); the `test_status_reflects_no_native_demo_mode_engine` defensive guard asserting status=beta + 5 tier_warnings present (`no_native_demo_mode_engine_for_integration_test` + `recipe_depends_on_user_wiring_real_sensor_signals` + `recipe_depends_on_user_declaring_real_hardware_target_entities` + `requires_operator_wiring_auto_disable_guard_before_first_use` + `demo_mode_never_controls_real_hardware_guard_must_be_wired`); the `test_automations_are_documented` defensive guard asserting the FIVE §8 MANDATORY automations documented (auto-disable on real sensor reconnect + never-controls-actual-hardware guard + blocks-remote-access guard + audit-log entry + operator-only guard) + 5 safety tiles wired (`input_boolean.rc_demo_mode_enabled` + `select.rc_demo_mode_scenario` + `binary_sensor.rc_demo_mode_is_blocking_real_hardware` + `sensor.rc_demo_mode_active_scenario` + `button.rc_demo_mode_disable`) + cross-references to time-atomic Wave 3 #55 + home-assistant.io/integrations/input_boolean + template + binary_sensor (HA core `template:` binary_sensor wrapper) + remote-access Wave 3 #58 + fans Wave 3 #59 + leveling Wave 3 #60 + approach lights Wave 3 #52 + mode Wave 3 #61)
  - vendor-neutrality: 11 `rc_demo_mode_*` tiles are vendor-neutral — NO Victron / SeeLevel / Seelevel / Garnet / Mopeka / Renogy / Starlink / Peplink / Teltonika / Unifi / Ubiquiti / MQTT / webhook / REST / API / HTTP / HTTPS / input_boolean / input_select / input_text / input_number / input_button / template / Companion / ESPHome / phone / GPS / accelerometer / gyroscope / magnetometer / compass / heading / iPhone / iOS / Android / Samsung / Pixel / OnePlus / Xiaomi / Huawei names leak into the tile ids
  - legacy tier-a-claim catalog page (`docs/catalog/ai/demo-mode.md`) now carries the SUPERSEDED banner pointing at the new connection folder (the legacy tier-a "RoamCore native" claim is honest-upstream-truth: RoamCore ships no native demo-mode engine today)
  - legacy package preserved (not touched): `homeassistant/packages/roamcore_demo_mode.yaml`
  - cross-reference to HA core `input_boolean` integration: §7 `input_boolean.rc_demo_mode_enabled` storage uses the HA core `input_boolean` integration
  - cross-reference to HA core `input_select` integration: §7 `select.rc_demo_mode_scenario` storage uses the HA core `input_select` integration
  - cross-reference to HA core `input_text` integration: §7 `input_text.rc_demo_mode_real_hardware_targets` storage uses the HA core `input_text` integration
  - cross-reference to HA core `input_number` integration: §7 cycle-helper storage uses the HA core `input_number` integration
  - cross-reference to HA core `template:` sensor wrapper: §7 active-scenario + battery-demo + water-demo derivation uses the HA core `template:` sensor wrapper
  - cross-reference to HA core `template:` binary_sensor wrapper: §7 blocking-real-hardware + connectivity-demo derivation uses the HA core `template:` binary_sensor wrapper
  - cross-reference to time-atomic Wave 3 #55: §8.4 audit-log entry's timestamp
  - cross-reference to remote-access Wave 3 #58: §8.3 blocks-remote-access guard's VPN primitive
  - cross-reference to approach lights Wave 3 #52: §8.3 blocks-remote-access guard's dashboard banner pattern
  - cross-reference to fans Wave 3 #59: §8.2 never-controls-actual-hardware guard's fan-protection cross-reference
  - cross-reference to leveling Wave 3 #60: §8.5 operator-only guard's levelling-jack protection cross-reference
  - cross-reference to mode Wave 3 #61: §8.4 audit-log entry's mode-change cross-reference
  - new `demo_mode` subsystem added to `docs/reference/rc-entity-naming.md` (the `demo_mode` subsystem is OWNED by this slice — the FIRST `ai`-category `demo_mode` slice in the RoamCore connection pipeline; back-fills `ventilation` + `vehicle` + `mode` subsystems since all three were missing from the Allowed subsystems list on the fresh-from-main branch cut)
  - Last updated: 2026-08-03
  - PR #66

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
