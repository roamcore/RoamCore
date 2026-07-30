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

- Starlink (tier-b connection manifest)
  - tier-b manifest: `connections/starlink/connection.yml` (networking category, beta status)
  - recipe: `connections/starlink/docs/recipe.md` (~450-line howto: Path A router-only power cycle + Path B full PSU power cycle + smart-plug wiring + REST signal-stats + 3 automations + 6 troubleshooting entries + tier-a promotion outline)
  - manifest-honesty smoke: `connections/starlink/tests/test_connection_yml.py` (6/6 PASS via `bash scripts/check.sh --core-only`)
  - contract entities: `rc_net_starlink_sleep_state`, `rc_net_starlink_allow_sleep`, `rc_net_starlink_wake_30_min`, `rc_net_starlink_reachable`, `rc_net_starlink_signal_pct`, `rc_net_starlink_quiet_start`, `rc_net_starlink_quiet_end` (all `rc_net_starlink_*` per docs/reference/rc-entity-naming.md §net subsystem)
  - legacy tier-c catalog page (`docs/catalog/networking/starlink-sleep-timer.md`) now carries a supersession banner pointing at the new connection folder

- Pi-hole / AdGuard Home (tier-b connection manifest)
  - tier-b manifest: `connections/dns-blocker/connection.yml` (networking category, beta status; covers both Pi-hole + AdGuard Home as Path A + Path B in one slice)
  - recipe: `connections/dns-blocker/docs/recipe.md` (~700-line howto: Path A Pi-hole + Path B AdGuard Home + rc_net_dns_* contract wiring + OpenWrt DHCP-options cross-reference + 3 automations + 6 troubleshooting entries + tier-a promotion outline)
  - manifest-honesty smoke: `connections/dns-blocker/tests/test_connection_yml.py` (6/6 PASS via `bash scripts/check.sh --core-only`)
  - contract entities: `rc_net_dns_blocked_today`, `rc_net_dns_blocked_pct`, `rc_net_dns_blocker_reachable`, `rc_net_dns_queries_total`, `rc_net_dns_blocker_enabled`, `rc_net_dns_resolver_status`, `rc_net_dns_gravity_updated` (all `rc_net_dns_*` per docs/reference/rc-entity-naming.md §net subsystem)
  - legacy tier-c catalog pages (`docs/catalog/homelab/pi-hole.md` + `docs/catalog/homelab/adguard-home.md`) now carry supersession banners pointing at the new connection folder

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
