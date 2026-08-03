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

- Peplink (multi-WAN router for van internet) (tier-b connection manifest)
  - tier-b manifest: `connections/peplink/connection.yml` (networking category, beta status; covers HA core `snmp` Path A for single-router operators + Peplink InControl 2 REST API via the community HACS `hass-incontrol2` integration Path B for fleet operators)
  - recipe: `connections/peplink/docs/recipe.md` (~870-line howto: Path A SNMP wiring + Path B InControl 2 wiring + force-failover affordance via Path A or Path B + WAN-priority `select` + mode-aware multi-WAN preference (cellular in Travel/Boost, Starlink in Home/Shore) + 4 automations + 8 troubleshooting entries + privacy + tier-a promotion outline)
  - manifest-honesty smoke: `connections/peplink/tests/test_connection_yml.py` (7/7 PASS via `bash scripts/check.sh --core-only`)
  - contract entities: `binary_sensor.rc_net_peplink_reachable`, `sensor.rc_net_peplink_wan1_state`, `sensor.rc_net_peplink_wan2_state`, `sensor.rc_net_peplink_active_wan`, `sensor.rc_net_peplink_wan_failover_count_24h`, `sensor.rc_net_peplink_wan_health_score`, `sensor.rc_net_peplink_uptime_hours`, `sensor.rc_net_peplink_public_ip`, `button.rc_net_peplink_refresh_now`, `button.rc_net_peplink_force_failover`, `select.rc_net_peplink_wan_priority` (all `rc_net_peplink_*` per docs/reference/rc-entity-naming.md §net subsystem)
  - legacy tier-c catalog page (`docs/catalog/networking/peplink.md`) now carries a supersession banner pointing at the new connection folder
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
