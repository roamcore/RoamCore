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

- Trip stats (rc_trip_*) from real Traccar data (Wave 2 #18)
  - `homeassistant/tools/trip_wrapped/traccar_trip_stats.py` — stdlib-only
    Python helper that polls the configured `device_tracker.traccar_*`
    entity on a rolling 5-minute cadence, computes haversine distance,
    drive time (speed > 0), segments, and stops (>=5 min stationary),
    and atomically writes a JSON state file under HA's
    `/config/.storage/`.
  - `homeassistant/packages/roamcore_trip_local.yaml` (extended):
    `shell_command.rc_trip_stats_poll` + `automation.rc_trip_stats_poll`
    (triggers: `homeassistant_started`, every 5 minutes, and on
    `entity_registry_updated` so a freshly-added tracker is picked up
    immediately) + six `command_line` sensors that read the JSON file:
    `rc_trip_stats_today_distance`, `rc_trip_stats_total_distance`,
    `rc_trip_stats_today_drive_time`, `rc_trip_stats_total_drive_time`,
    `rc_trip_stats_today_segments`, `rc_trip_stats_today_stops`.
  - `homeassistant/packages/roamcore_location.yaml` template sensors
    (`rc_trip_distance_today_mi`, `rc_trip_distance_total_mi`,
    `rc_trip_time_today`, `rc_trip_time_total`, `rc_trip_segments`,
    `rc_trip_stops`) now prefer the new `rc_trip_stats_*` sensors
    first, then `rc_trip_wrapped_*`, then `rc_trip_local_*`, then the
    existing mocks — preserving all previous behaviour when the live
    Traccar tracker is unavailable.
  - `docs/setup/traccar.md` §"Trip stats" documents the polling
    cadence and the local-only default.
  - `scripts/checks/trip-stats-traccar-smoke.sh` (Wave 2 #18 smoke),
    wired into `scripts/check.sh`.

## Next steps (needs HAOS setup / UI wiring)

1) **Setup Wizard dashboard**
   - Add a Lovelace dashboard YAML for setup flow.
   - Wire stubs to OpenWrt API + Victron connect UI.

2) **HACS packaging (planned)**
   - Publish a HACS integration to install RoamCore from the HA UI.
   - Auto-create dashboard + resources.
