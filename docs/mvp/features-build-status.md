# RoamCore MVP — Features Build Status

Last updated: 2026-08-02

This is an internal status page for the remaining MVP feature build-out.

## Shipped (repo)

- Weather + time contract sensors
  - `homeassistant/packages/roamcore_weather_time.yaml`

- Timezone override contract sensor (no HA restart required)
  - `sensor.rc_time_zone` via `input_text.rc_time_zone_override`

- Levelling contract (HA-only beta)
  - `homeassistant/packages/roamcore_level.yaml`
  - auto-maps common ESPHome pitch/roll sensors into stable `rc_level_*` entities

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

- In-cab tablet dashboard (driving / arrival / lock-screen Lovelace views with ignition-aware auto-switch) (tier-c recipe connection)
  - tier-c manifest: `connections/in-cab-tablet-dashboard/connection.yml` (vehicle_obd category, recipe_published status; reuse-first recipe over upstream HA Lovelace view system (a `view` config block in `ui-lovelace.yaml` / a panel view via the dashboard UI's "Add view" button / the `lovelace:` config block under `dashboard:` HA core UI configuration) + a thin RoamCore automation wrapper; RoamCore does NOT maintain a custom in-cab-tablet dashboard engine; `install.hacs: false` + `install.config_flow: false` because the recipe is a pure recipe over upstream HA Lovelace view system code (no HACS code required + no RoamCore-owned operator-wired setup flow); the UPSTREAM HA core dashboard UI exposes a "Add view" button in the dashboard edit mode (since 2022.x — lets the operator add a `panel` view with custom title + icon + cards) + a "Raw configuration editor" (since 2022.x — exposes a YAML editor for the `ui-lovelace.yaml` file); THREE operator-pickable paths — Path A "Driving" view (Lovelace view YAML with view type `panel`, view icon `mdi:car`, view title `Driving`, big-button tile layout, only safe interactions (toggle exterior lights + toggle compressor + mute the cabin)); Path B "Arrival / Welcome" view (ignition-triggered view switch via an automation that watches the OBD-II `binary_sensor.rc_vehicle_ignition` from Wican Pro Wave 3 #6 OR a generic `binary_sensor.*` ignition source OR a `device_tracker.rc_location_van` state change to home zone; the arrival view shows exterior lighting + compressor + house status); Path C "Lock screen / Always-on-display" view (battery-friendly low-power dashboard showing critical house status + key vehicle stats, refreshes every 60s, dimmed colors, minimal true/false states))
  - recipe: `connections/in-cab-tablet-dashboard/docs/recipe.md` (~1300+ line howto: HA Lovelace view install + Path A "Driving" view wiring (the `view` config block in `ui-lovelace.yaml` with view type `panel` + view icon `mdi:car` + view title `Driving` + big-button tile layout + only safe interactions) + Path B "Arrival / Welcome" view wiring (the `view` config block in `ui-lovelace.yaml` with view type `panel` + view icon `mdi:home-outline` + view title `Arrival` + rich tile layout for exterior lighting + compressor + house status) + the §7.1 ignition-on auto-switch to `arrival` view automation + Path C "Lock screen / Always-on-display" view wiring (battery-friendly low-power dashboard showing critical house status + key vehicle stats, refreshes every 60s, dimmed colors, minimal true/false states) + the §7.2 ignition-off auto-switch to `lock_screen` view automation + the §7.3 manual override automation + the 8 `rc_in_cab_tablet_*` contract tiles (4 sensor + 2 binary_sensor + 1 select + 1 button — active view + ignition state + last view change minutes ago + refresh cadence seconds + driving mode active + lock screen active + view mode + set view now); 3 MANDATORY §7 automations (ignition-on auto-switch to `arrival` view + ignition-off auto-switch to `lock_screen` view + manual override via select or button); 6 §8 troubleshooting entries (view never auto-switches / driving view not safe while moving / always-on display drains battery / Wican Pro ignition not detected / lock screen view not dimmed enough / manual override doesn't stick); §9 privacy (no telemetry beyond local Lovelace view state + ignition source + view mode select; all processing is local to the HA instance; no cloud call home); §10 tier-b promotion outline (real in-cab tablet bench on CI + RoamCore-owned config_flow.py walking Path A vs Path B vs Path C + integration tests asserting ignition-on triggers the §7.1 automation + ignition-off triggers the §7.2 automation + manual select change triggers the §7.3 automation + the contract tiles reflect the current view state))
  - manifest-honesty smoke: `connections/in-cab-tablet-dashboard/tests/test_connection_yml.py` (7/7 PASS via `bash scripts/check.sh --core-only` — includes the `test_tier_c_documents_reuse_first_strategy` defensive guard asserting tier=c + `wizard.one_tap=false` + `install.config_flow=false` honest because RoamCore ships no native in-cab-tablet dashboard engine + `install.hacs=false` because in-cab-tablet-dashboard is a pure recipe over upstream HA Lovelace view system code + NO RoamCore-owned `config_flow.py` + DOMAIN=`in_cab_tablet` + the description explicitly documents the reuse-first strategy over the upstream HA Lovelace view system + the links.official list includes the HA dashboard docs URL; the `test_dashboard_tiles_follow_rc_naming` defensive guard asserting 8 vendor-neutral `rc_in_cab_tablet_*` tiles (NOT `rc_dashboard_*` and NOT `rc_in_cab_*` and NOT `rc_tablet_*` — the in-cab-tablet-dashboard prefix is the SPECIFIC in-cab-tablet-dashboard subset of the broader vehicle subsystem, mirroring how time-atomic Wave 3 #55 inherits the `rc_time_*` prefix from the existing time helpers) + forbidden_substrings covers vendor + hardware + protocol + integration names including `wican`, `obd`, `12v`, `24v`, `mqtt`, `hacs`, `homeassistant`, `device_tracker`, `lovelace`, `dashboard_`, `panel`, `traccar`, `ha_companion`, `esphome`, `esp32`, `frigate`, `binary_sensor_`, `sensor_`, `switch`, `input_boolean`, `input_select`, `input_number`, `input_datetime`, `input_text`; the `test_status_reflects_recipe_published` defensive guard asserting status=recipe_published + 5 tier_warnings present (`no_native_in_cab_tablet_integration` + `recipe_depends_on_user_wiring_dashboard_yaml` + `requires_operator_choice_of_path_a_driving_view_or_path_b_arrival_view_or_path_c_lock_screen` + `no_real_vehicle_ignition_signal_on_ci_bench` + `mode_aware_stealth_suppression_not_required`); the `test_automations_are_documented` defensive guard asserting the THREE §7 automations documented (ignition-on auto-switch + ignition-off auto-switch + manual override) + 4 safety tiles wired (`sensor.rc_in_cab_tablet_active_view` + `binary_sensor.rc_in_cab_tablet_driving_mode_active` + `binary_sensor.rc_in_cab_tablet_lock_screen_active` + `button.rc_in_cab_tablet_set_view_now`) + cross-references to Wican Pro + Traccar + HA Companion + Approach lights + HVAC basics + Teltonika; the `test_no_legacy_dashboard_yaml_collisions` defensive guard asserting no collision with the existing dashboard YAML files; the `test_cross_references_resolve` defensive guard asserting all §11 cross-references resolve to existing files)
  - 8 contract entities all `rc_in_cab_tablet_*`: 4 sensor tiles (`sensor.rc_in_cab_tablet_active_view` / `sensor.rc_in_cab_tablet_ignition_state` / `sensor.rc_in_cab_tablet_last_view_change_minutes_ago` / `sensor.rc_in_cab_tablet_refresh_cadence_seconds`) + 2 binary_sensor tiles (`binary_sensor.rc_in_cab_tablet_driving_mode_active` / `binary_sensor.rc_in_cab_tablet_lock_screen_active`) + 1 select tile (`select.rc_in_cab_tablet_view_mode`) + 1 button tile (`button.rc_in_cab_tablet_set_view_now`) (per docs/reference/rc-entity-naming.md §vehicle subsystem — the `vehicle` subsystem is OWNED by the existing Wican Pro Wave 3 #6 connection; this slice inherits the `rc_vehicle_*` prefix from the existing Wican Pro entities and extends it with the `rc_in_cab_tablet_*` SPECIFIC subset for the dashboard view state, mirroring how time-atomic Wave 3 #55 inherits the `rc_time_*` prefix from the existing time helpers and how hvac-basics Wave 3 #49 inherits the `rc_hvac_*` prefix from heated-floors Wave 3 #44; this slice's `rc_in_cab_tablet_*` prefix is the SPECIFIC in-cab-tablet-dashboard subset of the broader vehicle subsystem, complementing Wican Pro Wave 3 #6's BROADER `rc_vehicle_*` prefix — both prefixes coexist in the same vehicle subsystem)
  - vendor-neutrality strictly enforced: NO `wican`, `obd`, `12v`, `24v`, `mqtt`, `hass`, `ha_integration`, `hacs`, `traccar`, `ha_companion`, `esphome`, `esp32`, `frigate`, `homeassistant`, `device_tracker`, `lovelace`, `dashboard_`, `panel`, `binary_sensor_`, `sensor_`, `switch`, `input_boolean`, `input_select`, `input_number`, `input_datetime`, `input_text` appears in any rc_* tile id BEYOND the `rc_in_cab_tablet_*` subsystem prefix (the spec-required tile IDs legitimately contain `active`, `view`, `ignition`, `state`, `last`, `change`, `minutes`, `ago`, `refresh`, `cadence`, `seconds`, `driving`, `mode`, `lock`, `screen`, `now` in the suffix to describe what the tile is for — these are the generic-noun tolerance list per spec; the forbidden substrings target the vendor-name / hardware-name / protocol-name / integration-name absolute-forbidden set only; the tile prefix is `rc_in_cab_tablet_*` — NOT `rc_dashboard_*` and NOT `rc_in_cab_*` and NOT `rc_tablet_*` — to avoid the literal substring `dashboard_` (which would conflict with the forbidden_substrings list) in the tile prefix; the `switch` HA core domain is also forbidden so the button tile uses `set_view_now` instead of `switch_view_now`; the `view_` UI noun is a generic English word and is NOT in the forbidden_substrings list because the spec-required tile IDs use it)
  - legacy tier-c catalog page (`docs/catalog/vehicle-obd/in-cab-tablet-dashboard.md`) now carries a supersession banner pointing at the new connection folder
  - cross-reference to Wican Pro: §7.1 ignition-on auto-switch to `arrival` view automation uses the Wican Pro Wave 3 #6 `binary_sensor.rc_vehicle_ignition` as the canonical ignition source (OBD-II-derived ignition signal that's reliable even when the phone is asleep)
  - cross-reference to Traccar: §7.1 ignition-on auto-switch automation's fallback trigger uses the Traccar Wave 3 #36 server's `device_tracker.rc_location_van` state change to home zone (the canonical location proxy; the `device_tracker.rc_location_van` state change to home zone is a reliable proxy for "we're home + the engine is off")
  - cross-reference to HA Companion app: §7.1 ignition-on auto-switch automation's phone-based fallback trigger uses the HA Companion app's `device_tracker.<phone_name>` entity (the operator-phone-based location source; battery-sensitive)
  - cross-reference to Approach lights: §4 Path B "Arrival / Welcome" view's exterior lighting controls surface the Approach lights Wave 3 #52 contract entities (`light.rc_approach_left` + `light.rc_approach_right` + `light.rc_approach_underbody`) for one-tap control of the approach lights on arrival
  - cross-reference to HVAC basics: §4 Path B "Arrival / Welcome" view's heating/cooling toggles surface the HVAC basics Wave 3 #49 contract entities (`climate.rc_hvac_*` + `switch.rc_hvac_*`) for one-tap control of the heating/cooling on arrival
  - cross-reference to Teltonika (optional): the in-cab tablet reaches HA's Lovelace UI over the always-on LTE backhaul via the Teltonika Wave 3 #39 LTE router (the tablet can reach HA's Lovelace UI via the LTE backhaul without depending on Starlink)
  - cross-reference to Vehicle subsystem: §6 the 8 `rc_in_cab_tablet_*` contract tiles inherit the `rc_vehicle_*` prefix from the existing Wican Pro Wave 3 #6 entities and extend it with the `rc_in_cab_tablet_*` SPECIFIC subset (the vehicle subsystem is OWNED by the existing Wican Pro Wave 3 #6 connection; this slice complements the existing Wican Pro entities by AUTOMATING the dashboard view state via Path A + Path B + Path C, where the existing Wican Pro entities publish the OBD-II telemetry + the ignition signal)
  - cross-reference to Timezone geolocator (no relationship): different subsystem
  - cross-reference to Motion-based lighting (no relationship): different subsystem
  - cross-reference to Time (atomic) (no relationship): different subsystem
  - PR #60

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
