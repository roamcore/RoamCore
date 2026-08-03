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

- Agent actions allowlist (safety gateway for agent-driven RoamCore actions)
  - Connection: [`connections/agent-actions-allowlist/`](../../connections/agent-actions-allowlist/) (Wave 3 #65, PR #69)
  - Tier-b recipe connection over upstream HA core `input_boolean` + `input_text` + `input_number` + `input_select` + `input_datetime` + `input_button` + `script` helpers (since 2022.x) + HA core `template:` sensor wrapper (since 2022.x) + HA core `logbook` integration (since 2022.x) + the upstream `script:` integration (since 2022.x). The single `input_boolean.rc_agent_actions_enabled` kill switch is already shipped in `homeassistant/packages/roamcore_agent_actions.yaml` and is preserved verbatim by this slice.
  - 11 vendor-neutral `rc_agent_actions_*` contract tiles (the kill switch + the policy path + the require-confirmation toggle + the default-duration picker + the session expiry timestamp + the seconds-until-expiry + the last-action-id + last-action-at + the last-action-result + the is-blocked-by-kill-switch + the disable-now button) — no Victron / SeeLevel / Garnet / Mopeka / Renogy / Starlink / Peplink / Teltonika / Unifi / Ubiquiti / OpenAI / Anthropic / Claude / GPT / ChatGPT / LLM / MQTT / webhook / REST / API / HTTP / HTTPS / ESPHome / Companion / phone / GPS / accelerometer / iPhone / iOS / Android / Samsung / Pixel / OnePlus / Xiaomi / Huawei / input_boolean / input_text / input_number / input_select / input_datetime / input_button / script / template / logbook / Z-Wave / Zigbee / ZHA / Deconz / Tasmota / Shelly / Sonoff / ESP32 / ESP8266 / Wi-Fi / BLE / Bluetooth names leak into the tile ids.
  - 5 §8 MANDATORY automations (kill-switch-blocks-everything guard + session-timeout guard + audit-log entry + require-confirmation guard + outside-allowlist deny-by-default guard).
  - Legacy catalog doc [`docs/catalog/ai/agent-actions-allowlist.md`](../catalog/ai/agent-actions-allowlist.md) now superseded (the SUPERSEDED banner is appended at the end of the doc).
  - Cross-references: time-atomic Wave 3 #55 + remote-access Wave 3 #58 + approach lights Wave 3 #52 + fans Wave 3 #59 + leveling Wave 3 #60 + mode Wave 3 #61 + demo-mode Wave 3 #62 + advanced-mode Wave 3 #63 + openclaw-api Wave 3 #64.
  - Verification: `bash scripts/check.sh --core-only` exit 0 + 7/7 pytest PASS + PR #69 OPEN against `main`.

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
