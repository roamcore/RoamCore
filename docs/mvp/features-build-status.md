# RoamCore MVP — Features Build Status

Last updated: 2026-03-31

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

- Timezone geolocator (location-aware HA timezone) (tier-c recipe connection)
  - tier-c manifest: `connections/timezone-geolocator/connection.yml` (time category, recipe_published status; reuse-first recipe over upstream GeoLocator HACS integration by SmartyVan (https://github.com/SmartyVan/hass-geolocator) + a thin RoamCore automation wrapper; RoamCore does NOT maintain a custom timezone engine; `install.hacs: true` + `install.hacs_url: https://github.com/SmartyVan/hass-geolocator` is honest because the UPSTREAM HACS `geolocator` integration is the canonical timezone-update engine; Path A GPS source — Traccar Wave 3 #36 server `device_tracker.rc_location_van` OR HA Companion app `device_tracker.<phone>` OR Wican Pro Wave 3 #6 OBD-II's GPS feed OR generic `device_tracker.*` updating `zone.home`; Path B `homeassistant.set_location` service-call fallback for benches without a GPS tracker; Path C RoamCore automation wrapper — 15-min cadence default (recommended; conservative; `time_pattern minutes /15`) OR event-driven on `zone.home` changes (lower latency but requires reliable change-trigger) OR manual via `button.rc_time_zone_update_now`)
  - recipe: `connections/timezone-geolocator/docs/recipe.md` (~600+ line howto: HACS install of GeoLocator + the Path A1 Traccar GPS source + Path A2 HA Companion GPS source + Path A3 Wican Pro GPS source + Path A4 generic `device_tracker.*` GPS source + the `homeassistant.set_location` service-call binding pattern + the 15-min cadence automation + the event-driven automation + the manual-only option + the `select.rc_time_zone_update_cadence` (event_driven / 15_min / 60_min / manual) select; 8 `rc_time_zone_*` contract tiles (4 sensor + 2 binary_sensor + 1 select + 1 button — current timezone + offset-minutes + synced correctness gate + last-update-minutes-ago freshness + stale freshness gate + GPS-source + update-cadence select + update-now button); 1 MANDATORY §7 automation (Update timezone via `geolocator.update_location` on 15-min cadence default OR event-driven OR manual); 6 §8 troubleshooting entries (timezone never updates / `now()` still shows old timezone / stale always TRUE / current shows unknown / synced always FALSE / update-now button doesn't fire); §9 privacy (no telemetry beyond local zone + device_tracker + GeoLocator; no cloud call home; GeoLocator runs entirely on HA); §10 tier-b promotion outline (real timezone engine bench on CI (Traccar server + mock GPS feed + canned fixture responses + upstream GeoLocator) + RoamCore-owned config_flow.py walking Path A vs Path B vs Path C + integration tests asserting a GPS source update to `zone.home` triggers `geolocator.update_location` + a 15-min cadence tick triggers `geolocator.update_location` + `sensor.rc_time_zone_current` reflects the correct timezone + `binary_sensor.rc_time_zone_synced` is TRUE when system timezone matches GeoLocator's output + `binary_sensor.rc_time_zone_stale` is TRUE when last_update > 60 minutes + the `button.rc_time_zone_update_now` button forces a `geolocator.update_location` call within a defined latency budget + the cadence select correctly enables / disables the corresponding automation))
  - manifest-honesty smoke: `connections/timezone-geolocator/tests/test_connection_yml.py` (7/7 PASS via `bash scripts/check.sh --core-only` — includes the `test_tier_c_documents_reuse_first_strategy` defensive guard asserting tier=c + `wizard.one_tap=false` + `install.hacs=true` + `install.hacs_url` points at GeoLocator upstream + NO RoamCore-owned `config_flow.py` + DOMAIN=`timezone_geolocator` + the description explicitly documents the reuse-first strategy + the links.official list includes the GeoLocator upstream repo URL; the `test_automations_are_documented` defensive guard asserting the single §7 Update timezone automation is documented + 4 safety tiles wired (`sensor.rc_time_zone_current` + `binary_sensor.rc_time_zone_synced` + `binary_sensor.rc_time_zone_stale` + `button.rc_time_zone_update_now`) + cross-references to `geolocator.update_location` + `GeoLocator` + `zone.home` + `homeassistant.set_location` + `sensor.rc_time_zone` + `roamcore_weather_time.yaml`)
  - 8 contract entities all `rc_time_zone_*`: 4 sensor tiles (`sensor.rc_time_zone_current` / `sensor.rc_time_zone_offset_minutes` / `sensor.rc_time_zone_last_update_minutes_ago` / `sensor.rc_time_zone_gps_source`) + 2 binary_sensor tiles (`binary_sensor.rc_time_zone_synced` / `binary_sensor.rc_time_zone_stale`) + 1 select tile (`select.rc_time_zone_update_cadence`) + 1 button tile (`button.rc_time_zone_update_now`) (per docs/reference/rc-entity-naming.md §time subsystem — the `time` subsystem is OWNED by the existing `homeassistant/packages/roamcore_weather_time.yaml` + `sensor.rc_time_zone` override contract; this slice inherits the `rc_time_zone_*` prefix from the existing time helpers without backfilling, mirroring how hvac-basics Wave 3 #49 inherits the `rc_hvac_*` prefix from heated-floors Wave 3 #44 without backfilling)
  - vendor-neutrality strictly enforced: NO `traccar`, `ha_companion`, `wican`, `obd`, `12v`, `24v`, `esphome`, `esp32`, `mqtt`, `hass`, `ha_integration`, `hacs`, `geolocator`, `geo_locator`, `smartyvan`, `smarty_van`, `zone_`, `homeassistant`, `device_tracker`, `set_location`, `binary_sensor_`, `sensor_`, `switch`, `input_boolean`, `input_select`, `input_number`, `input_datetime`, `input_text` appears in any rc_* tile id BEYOND the `rc_time_zone_*` subsystem prefix (the spec-required tile IDs legitimately contain `current`, `offset`, `synced`, `last`, `update`, `minutes`, `ago`, `stale`, `gps`, `source`, `cadence`, `now` in the suffix to describe what the tile is for — these are the generic-noun tolerance list per spec; the forbidden substrings target the vendor-name / protocol-name / integration-name absolute-forbidden set only)
  - legacy tier-c catalog page (`docs/catalog/time/timezone-geolocator.md`) now carries a supersession banner pointing at the new connection folder
  - cross-reference to Traccar: §3 Path A1 GPS source uses the Traccar Wave 3 #36 server's `device_tracker.rc_location_van` entity (the canonical GPS source for the RoamCore map page; uses the always-on LTE backhaul so the GPS feed is reliable even when the operator's phone is asleep)
  - cross-reference to HA Companion app: §3 Path A2 GPS source uses the HA Companion app's `device_tracker.<phone_name>` entity (the operator-phone-based GPS source; battery-sensitive)
  - cross-reference to Wican Pro: §3 Path A3 GPS source uses the Wican Pro Wave 3 #6 OBD-II reader's GPS feed (always-on even when phone is asleep; the canonical GPS source for vans without a Traccar server)
  - cross-reference to Teltonika (optional): §3 Path A1 Traccar GPS source uses the Teltonika LTE connection for the always-on LTE backhaul (Wave 3 #39)
  - cross-reference to Time / weather contract: §6 the 8 `rc_time_zone_*` contract tiles cross-reference the existing `homeassistant/packages/roamcore_weather_time.yaml` + `sensor.rc_time_zone` override contract (the existing time helpers read `sensor.rc_time_zone_current` as the source of truth for the system timezone; this slice complements the existing time helpers by AUTOMATING the timezone update via GeoLocator, where the existing time helpers required manual override)
  - cross-reference to HVAC basics (no relationship): different subsystem
  - cross-reference to Motion-based lighting (no relationship): different subsystem
  - cross-reference to Approach lights (no relationship): different subsystem
  - PR #N

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
