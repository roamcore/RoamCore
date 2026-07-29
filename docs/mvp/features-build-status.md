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

- Trip tracking — fully local/private end-to-end by default (slice #20)
  - Privacy contract: `docs/feature-checklist.md` (Map / Trip section).
  - Toggle: `input_boolean.rc_trip_local_only` (default ON) +
    `input_text.rc_trip_opt_in_domains` in `homeassistant/packages/roamcore_trip_privacy.yaml`.
  - Pipeline defaults switched from public CDNs (`staticmap.openstreetmap.de`,
    `tile.openstreetmap.org`, `a.basemaps.cartocdn.com`) to the local
    RoamCore tileserver add-on (`http://localhost:8000/...`).
  - Non-loopback hosts must be in `privacy_allowlist.json` or annotated
    `# PRIVACY-OPTIN:` — enforced by
    `scripts/checks/trip-tracking-privacy-smoke.sh` (wired into
    `scripts/check.sh --core-only`).
  - Trip Wrapped HTML gets a privacy banner: "Generated locally · no data sent off-device".

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
