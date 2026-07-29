# RoamCore MVP — Features Build Status

Last updated: 2026-07-29

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

- Traccar install + integration in HAOS (Wave 2 #17)
  - `homeassistant/packages/roamcore_location.yaml`
    - auto-fill automation `automation.rc_location_autofill_tracker_entity`
      runs on `homeassistant_started` + every `entity_registry_updated` to
      write the first `device_tracker.traccar_*` entity_id into
      `input_text.rc_location_tracker_entity`.
  - `docs/setup/traccar.md` §"Step 1: Configure the Home Assistant Traccar
    integration" walks users through the built-in `traccar_server`
    integration (no HACS) and both the auto-fill (Path A) and manual
    `input_text.set_value` (Path B) wiring paths.
  - `scripts/install/ha/install.sh` exposes `--with-traccar` to print the
    integration setup steps + soft-verify via `ha integrations list`.
  - `homeassistant/configuration_addon.yaml` ships a commented-out
    `device_tracker:` → `platform: traccar` YAML pre-stage block for
    advanced users (default-off, HACS-first principle preserved).
  - `scripts/checks/traccar-integration-smoke.sh` (Wave 2 #17 smoke),
    wired into `scripts/check.sh`.

## Next steps (needs HAOS setup / UI wiring)

1) **Setup Wizard dashboard**
   - Add a Lovelace dashboard YAML for setup flow.
   - Wire stubs to OpenWrt API + Victron connect UI.

2) **Trip stats (rc_trip_*) from real Traccar data**
   - MVP still uses mocks for distance/time/stops.
   - Implement: odometer-based + utility_meter or periodic report pulls.

3) **HACS packaging (planned)**
   - Publish a HACS integration to install RoamCore from the HA UI.
   - Auto-create dashboard + resources.
