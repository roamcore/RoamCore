# RoamCore MVP — Features Build Status

Last updated: 2026-07-29

This is an internal status page for the remaining MVP feature build-out.

## Shipped (repo)

- OTA updates (GitHub channel + rollback-aware) — Wave 2 #30 (slice shipped)
  - Add-on: `homeassistant/addons/roamcore_ota/` (poller + 3-snapshot history at `/share/roamcore/snapshots/`)
  - Contract package: `homeassistant/packages/roamcore_ota.yaml` (sensors + helpers + auto-apply scheduler at 03:00 local)
  - Wizard snippet: `homeassistant/packages/roamcore_setup_wizard_ota.yaml` (paste-this-card for the OTA stage)
  - Setup doc: `docs/setup/ota.md`
  - Architecture doc: `docs/architecture/ota-channel.md`
  - Smoke check: `scripts/checks/ota-smoke.sh` wired into `scripts/check.sh --core-only`
  - Privacy: only outbound traffic is `api.github.com` over HTTPS (no telemetry)

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

- RoamCore Labs (share setups/dashboards) — Wave 2 #32 (slice shipped)
  - Contract layer: `homeassistant/packages/roamcore_labs.yaml` (8 contract entities)
  - Wizard snippet: `homeassistant/packages/roamcore_setup_wizard_labs.yaml`
  - Services: `roamcore.labs_export_setup` + `roamcore.labs_import_setup`
  - CLI mirrors: `homeassistant/tools/labs/{export_setup,import_setup}.py` (stdlib-only)
  - Smoke: `scripts/checks/labs-smoke.sh` (privacy invariant wired into `scripts/check.sh --core-only`)

- Gamification (opt-in streak + trophy subsystem) — Wave 2 #33 (slice shipped; tier-c, opt-in, local-only)
  - Contract layer: `homeassistant/packages/roamcore_gamification.yaml` (19 contract entities)
  - Wizard snippet: `homeassistant/packages/roamcore_setup_wizard_gamification.yaml`
  - Service: `roamcore.gamification_acknowledge_trophy` (registered in `homeassistant/custom_components/roamcore/services.yaml`)
  - CLI mirror: `homeassistant/tools/gamification/trophy_state.py` (stdlib-only)
  - Smoke: `scripts/checks/gamification-smoke.sh` (privacy invariant wired into `scripts/check.sh --core-only`)

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
