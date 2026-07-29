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

- Mode / automation builder (simple UI)
  - `homeassistant/packages/roamcore_mode.yaml` (extended) + `homeassistant/packages/roamcore_mode_builder.yaml`
  - `homeassistant/www/roamcore/roamcore-mode-builder.js` + mount in `roamcore-pages.js`
  - `docs/setup/mode-builder.md`
  - slice #23 (`feat/wave2-mode-automation-builder`)

- Automations builder via text/LLM/MCP (OpenClaw API v2 — apply bridge)
  - `homeassistant/custom_components/roamcore/automation_intents.py` extended with `set_helper` / `run_script` intents + `apply_intent()` allowlist-aware helper
  - `homeassistant/custom_components/roamcore/openclaw_view.py` adds `OpenClawAutomationApplyView` (`POST /api/roamcore/openclaw/automation/apply`)
  - `homeassistant/custom_components/roamcore/__init__.py` registers the view; execution delegates to the existing `roamcore.action_execute` service (kill switch + audit log already wired)
  - unit tests in `homeassistant/custom_components/roamcore/tests/test_automation_intents.py`
  - smoke check: `scripts/checks/openclaw-automation-smoke.sh`
  - slice #24 (`feat/wave2-openclaw-automation-apply`)

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

5) ~~Automations builder via text/LLM/MCP (OpenClaw API v2)~~
   - Shipped as slice #24 (`feat/wave2-openclaw-automation-apply`). See the “Shipped (repo)” section above.
