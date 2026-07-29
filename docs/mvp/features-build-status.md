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

- RoamCore Wrapped — seamless USP flow (slice #21)
  - Demo seed generator: `homeassistant/tools/trip_wrapped/demo_seed.py` (stdlib-only, no outbound HTTP; map URL points at local tileserver `http://localhost:8000/...`).
  - HA wiring: `homeassistant/packages/roamcore_trip_wrapped.yaml`
    - new `input_boolean.rc_trip_wrapped_demo` (default ON)
    - new `input_boolean.rc_trip_wrapped_real` (default OFF)
    - shell_command `rc_trip_wrapped_demo_seed` + script `rc_trip_wrapped_demo_seed` + 2 automations (`rc_trip_wrapped_real_turns_off_demo`, `rc_trip_wrapped_demo_turns_on_seed`).
  - Custom-component service: `roamcore.trip_wrapped_demo` (declared in `homeassistant/custom_components/roamcore/services.yaml`, registered in `__init__.py`).
  - UI one-tap CTA in the Map → Trip Wrapped modal (`homeassistant/www/roamcore/roamcore-pages.js`): shown only when no `latest.json` exists; calls the new service.
  - Smoke check: `scripts/checks/trip-wrapped-seamless-smoke.sh` (wired into `scripts/check.sh --core-only`).
  - Files touched: `homeassistant/tools/trip_wrapped/demo_seed.py` (new), `homeassistant/packages/roamcore_trip_wrapped.yaml`, `homeassistant/custom_components/roamcore/services.yaml`, `homeassistant/custom_components/roamcore/__init__.py`, `homeassistant/www/roamcore/roamcore-pages.js`, `scripts/checks/trip-wrapped-seamless-smoke.sh` (new), `scripts/check.sh`, `docs/feature-checklist.md`, `docs/mvp/features-build-status.md`, `docs/howto/trip-wrapped.md` (new).
  - Smoke check: `bash scripts/checks/trip-wrapped-seamless-smoke.sh` ✓

- Amenities overlay — iOverlander-style, opt-in + privacy-respecting (slice #22)
  - Python helper: `homeassistant/tools/amenities/overpass_query.py` (stdlib-only; `urllib.request` deferred to `--query` path; `--dry-run` emits a deterministic fixture JSON).
  - HA wiring: `homeassistant/packages/roamcore_amenities.yaml`
    - `input_boolean.rc_amenities_overlay_enabled` (default OFF — opt-in)
    - `input_select.rc_amenities_categories` (default `water,laundry,campground,supermarket`)
    - `input_number.rc_amenities_radius_km` (default 5 km, range 0.5–50)
    - `input_text.rc_amenities_overpass_url` (default `https://overpass-api.de/api/interpreter`, annotated `# PRIVACY-OPTIN:`)
    - shell_command `rc_amenities_overpass_query` + `rc_amenities_clear` + scripts + 4 automations (toggle ON → refresh, OFF → clear, 30-min periodic, movement >1 km refresh).
  - Map UI: new `RcAmenitiesLayer` class + toggle button + category legend in `homeassistant/www/roamcore/roamcore-pages.js`. Fails safe: missing/malformed `latest.json` → console warning, basemap unaffected. Polls every 5 min while ON.
  - Smoke checks: `scripts/checks/amenities-overlay-smoke.sh` + `scripts/checks/amenities-overlay-privacy-smoke.sh` (both wired into `scripts/check.sh --core-only`).
  - Files touched: `homeassistant/tools/amenities/overpass_query.py` (new), `homeassistant/packages/roamcore_amenities.yaml` (new), `homeassistant/www/roamcore/roamcore-pages.js`, `scripts/checks/amenities-overlay-smoke.sh` (new), `scripts/checks/amenities-overlay-privacy-smoke.sh` (new), `scripts/check.sh`, `docs/feature-checklist.md`, `docs/catalog/map/amenities-overlay.md`, `docs/mvp/features-build-status.md`.
  - Smoke checks: `bash scripts/checks/amenities-overlay-smoke.sh` ✓ + `bash scripts/checks/amenities-overlay-privacy-smoke.sh` ✓

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
