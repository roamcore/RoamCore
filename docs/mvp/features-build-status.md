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
- Bluetooth / Wi-Fi presence (who's home?) (tier-b connection manifest)
  - tier-b manifest: `connections/bluetooth-wifi-presence/connection.yml` (presence category, beta status; recipe-over-upstream — no RoamCore-owned presence scanner; `install.config_flow: true` is honest because HA core `nmap_device_tracker` (Path B) + `asuswrt` / `unifi` / `mikrotik` (Path C) integrations expose a config_flow since 2022.x; `bluetooth_le_tracker` Path A is YAML-only (deprecated upstream but still functional); no HACS integration of our own is shipped — Paths A/B/C all use existing HA core integrations)
  - recipe: `connections/bluetooth-wifi-presence/docs/recipe.md` (~260-line howto: Path A `bluetooth_le_tracker` YAML wiring + screensaver-sleep workaround via BLE beacon (Nut find3 / Apple AirTag) + Path B `nmap_device_tracker` / `ping` wiring + per-device template helper YAML + Path C `asuswrt` / `unifi` / `mikrotik` router-side wiring + HA `person` entity OR template helper translation into the contract layer + 10 `rc_presence_*` contract tiles + 6 automations (Stealth suppression / Bluetooth + Wi-Fi agreement rule (legacy catalog spec §7) / approach lighting on first arrival after dark / inverter+pump shutdown on all-away + shore disconnected + >15 min / only-driver-home dim interior to 10 % after dark / power-aware occupancy alert TTS to living zone) + 8 troubleshooting entries + privacy + tier-a promotion outline)
  - manifest-honesty smoke: `connections/bluetooth-wifi-presence/tests/test_connection_yml.py` (7/7 PASS via `bash scripts/check.sh --core-only`)
  - contract entities: `device_tracker.rc_presence_person_alice`, `device_tracker.rc_presence_person_bob`, `binary_sensor.rc_presence_anyone_home`, `binary_sensor.rc_presence_only_driver_home`, `sensor.rc_presence_persons_home_count`, `sensor.rc_presence_last_arrival`, `sensor.rc_presence_last_departure`, `binary_sensor.rc_presence_all_away`, `button.rc_presence_refresh_now`, `select.rc_presence_occupied_threshold_minutes` (all `rc_presence_*` per docs/reference/rc-entity-naming.md §presence subsystem — added to the allowed subsystems list alongside this slice, mirroring how `media` was added by the Music Assistant slice)
  - vendor-neutrality strictly enforced: NO `bluetooth`, `bt`, `wifi`, `wlan`, `arp`, `nmap`, `ping`, `asuswrt`, `ubiquiti`, `unifi`, `mikrotik`, `iphone`, `android`, `pixel`, `galaxy` appears in any tile id BEYOND the subsystem prefix `rc_presence_*`
  - legacy tier-c catalog page (`docs/catalog/presence/bluetooth-wifi-presence.md`) now carries a supersession banner pointing at the new connection folder
  - cross-reference to Music Assistant: the §7.6 "power-aware occupancy alert" automation sends TTS to `media_player.rc_media_zone_living` when shore is disconnected AND ≥2 people are home AND inverter SOC < 30 % — uses the Music Assistant `connections/music-assistant/` contract tile as the TTS target
  - cross-reference to Victron: the §7.4 inverter-shutdown automation + §7.6 power-aware alert both depend on `sensor.rc_power_battery_soc` + `binary_sensor.rc_power_shore_connected` — uses the Victron `connections/victron/` contract tiles as the power source
  - PR #N
- Happijac bed lift (van bed up/down control) (tier-b connection manifest)
  - tier-b manifest: `connections/happijac/connection.yml` (bed_lift category, beta status; HA core `cover` template Path A ESPHome-friendly + Path B relay-friendly; `install.config_flow: true` is honest because the UPSTREAM HA core `cover` template integration + ESPHome `cover:` component expose a config_flow since 2022.x / 2023.x respectively; no RoamCore-owned wrapper / no native integration code is shipped — both paths recipe over upstream ESPHome or HA core `template` cover + 2× dry-contact relays + 2× limit microswitches + optional CT-clamp current sensor)
  - recipe: `connections/happijac/docs/recipe.md` (~360-line howto: Path A ESPHome YAML wiring for the 2× outputs (UP + DOWN relay coils) + 2× binary_sensor limit inputs (up_limit + down_limit, both with `delayed_off: 100ms` filter) + optional ADC current sensor for obstruction detection + the ESPHome `cover:` component declaring `cover.bed_lift`; Path B Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano Switch pair + HA core `template:` cover wiring + the limit binary_sensor + the `current_based_obstruction_detection` block; 12 `rc_bed_lift_*` contract tiles (cover position + 2× limits + moving + position_pct + safety_ok + 3× button + obstruction_detected + low_voltage_lockout + mode select); 4 safety interlocks (limit-sanity aggregate / low-voltage lockout via `sensor.rc_power_battery_soc` from Victron / current-based obstruction detection / mode-aware lockouts Stealth + Sleep + Boost); 6 automations (Stealth auto-stop / Sleep 23:00 auto-lower / Boost disable-mode-aware-lockouts / low-voltage lockout when SOC < 20 % / obstruction detected → stop + alert via MA TTS / mode-aware gentle reminder when only-driver-home for >15 min); 8 troubleshooting entries (relay polarity / one limit stuck / both limits TRUE wiring fault / NC-NO mis-wire / obstruction false-positive tune current threshold / low-voltage lockout stuck after charging / Shelly not discovered mDNS IGMP / ESPHome device offline); §9 privacy (no telemetry beyond local limit microswitches + optional CT clamp; no Happijac cloud / no ESPHome cloud / no Shelly cloud / no Zooz / Aeotec cloud); §10 tier-a promotion outline (real Happijac + ESPHome + relay bench on CI + RoamCore-owned config_flow.py + integration tests asserting the 4 safety interlocks all flip + a 0→100% `cover.rc_bed_lift_position` change triggers the right tile updates))
  - manifest-honesty smoke: `connections/happijac/tests/test_connection_yml.py` (7/7 PASS via `bash scripts/check.sh --core-only` — includes the `test_safety_interlocks_are_documented` defensive guard for the future tier-a promotion's hard-enforced safety interlock asserts)
  - 12 contract entities all `rc_bed_lift_*`: `cover.rc_bed_lift_position`, `binary_sensor.rc_bed_lift_up_limit`, `binary_sensor.rc_bed_lift_down_limit`, `binary_sensor.rc_bed_lift_moving`, `sensor.rc_bed_lift_position_pct`, `binary_sensor.rc_bed_lift_safety_ok`, `button.rc_bed_lift_lift`, `button.rc_bed_lift_lower`, `button.rc_bed_lift_stop`, `binary_sensor.rc_bed_lift_obstruction_detected`, `binary_sensor.rc_bed_lift_low_voltage_lockout`, `select.rc_bed_lift_mode` (per docs/reference/rc-entity-naming.md §bed_lift subsystem — added to the allowed subsystems list alongside this slice, mirroring how `media` was added by the Music Assistant slice AND how `presence` was backfilled in the same edit since Wave 3 #42 promised it but didn't deliver)
  - vendor-neutrality strictly enforced: NO `happijac`, `happi`, `lc_`, `lci`, `bed`, `lift`, `actuator`, `esphome`, `shelly`, `zooz`, `aeotec`, `relay`, `cover_*`, `dry_contact` appears in any tile id BEYOND the `rc_bed_lift_*` subsystem prefix
  - legacy tier-c catalog page (`docs/catalog/bed-lift/happijac.md`) now carries a supersession banner pointing at the new connection folder
  - cross-reference to Victron: §6.2 safety interlock for low-voltage lockout uses `sensor.rc_power_battery_soc` + `binary_sensor.rc_power_shore_connected` from the Victron `connections/victron/` recipe
  - cross-reference to Bluetooth / Wi-Fi presence: §7.6 "if bed is in the up position AND presence says only-driver-home for >15 min AND mode is Sleep → gentle reminder to lower bed before sleeping" automation uses the bluetooth-wifi-presence `connections/bluetooth-wifi-presence/` contract tile (`binary_sensor.rc_presence_only_driver_home`) for the presence signal
  - PR #47

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
