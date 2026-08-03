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

- Music Assistant (multi-room van audio) (tier-b connection manifest)
  - tier-b manifest: `connections/music-assistant/connection.yml` (media category, beta status; honest HACS-only install — `install.hacs: true` + `install.config_flow: true` because the UPSTREAM HACS `music_assistant` integration has a config_flow since 2023; HACS-only because HA core does NOT include Music Assistant; auto-discover via zeroconf on the LAN; covers Path A HA add-on for HAOS installs + Path B external MA server via `ghcr.io/music-assistant/server` for fleet installs + non-HAOS hosts)
  - recipe: `connections/music-assistant/docs/recipe.md` (~960-line howto: HACS install + Path A HA add-on wiring + Path B external MA server wiring + provider configuration (Spotify OAuth / Apple Music dev token / TuneIn / local-files mount / Chromecast / AirPlay / Sonos receivers) + per-zone `rc_media_zone_*` template media_player aliases + now-playing trio + library counts + `pause_all` / `resume_last` button affordances + 6 automations (Stealth auto-pause / Travel motion-resume / Boost zone-default-volume / inverter-SOC power-aware pause / TTS-zone-pinning / remember-last-played) + 8 troubleshooting entries + privacy + tier-a promotion outline)
  - manifest-honesty smoke: `connections/music-assistant/tests/test_connection_yml.py` (7/7 PASS via `bash scripts/check.sh --core-only`)
  - contract entities: `media_player.rc_media_zone_living`, `media_player.rc_media_zone_bed`, `media_player.rc_media_zone_outdoor`, `binary_sensor.rc_media_any_player_playing`, `sensor.rc_media_active_zone`, `sensor.rc_media_now_playing_title`, `sensor.rc_media_now_playing_artist`, `sensor.rc_media_now_playing_album`, `sensor.rc_media_library_artists_count`, `sensor.rc_media_library_albums_count`, `sensor.rc_media_library_tracks_count`, `button.rc_media_pause_all`, `button.rc_media_resume_last`, `select.rc_media_default_zone` (all `rc_media_*` per docs/reference/rc-entity-naming.md §media subsystem — added to the allowed subsystems list alongside this slice)
  - legacy tier-c catalog page (`docs/catalog/audio-media/music-assistant.md`) now carries a supersession banner pointing at the new connection folder
  - HACS-only install is honestly disclosed: MA is fetched from `music-assistant/hass-music-assistant` via HACS → Repositories → Add (HA core does NOT include Music Assistant)
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
