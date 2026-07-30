"""Bluetooth / Wi-Fi presence (who's home?) — tier-b recipe connection.

This module is a marker-only stub. Tier-b connections don't ship native
HA integration code; they publish a recipe (docs/recipe.md) that walks
the user through setting up presence detection on the van (Path A — HA
core bluetooth_le_tracker for small vans with 1–2 people, OR Path B —
HA core nmap_device_tracker or ping for fleet installs, OR Path C —
router-side device_tracker via asuswrt / unifi / mikrotik when the
operator already uses one of those routers as the LAN gateway), and
exposes the resulting data via the upstream HA core integrations, then
publishes the RoamCore presence contract tiles on top (`rc_presence_*`
tiles: per-person `device_tracker` entities, a
`binary_sensor.rc_presence_anyone_home`, a
`binary_sensor.rc_presence_only_driver_home`, a
`sensor.rc_presence_persons_home_count`, a
`sensor.rc_presence_last_arrival`, a
`sensor.rc_presence_last_departure`, a
`binary_sensor.rc_presence_all_away`, a
`button.rc_presence_refresh_now`, and a
`select.rc_presence_occupied_threshold_minutes`).

The audit + boundary CI can detect a `bluetooth-wifi-presence/` folder
that claims to be a connection via the `DOMAIN` constant exported
here. The wizard reads the manifest + recipe at runtime.

The real per-person presence + anyone-home / only-driver / all-away
affordance path is:

    Operator-side presence source (Path A HA core bluetooth_le_tracker
        via YAML; OR Path B HA core nmap_device_tracker via the
        upstream integration's GUI flow OR ping binary_sensor as a
        Path B-alt; OR Path C router-side asuswrt / unifi / mikrotik
        device_tracker integration)
        -> upstream HA core device_tracker.* entities (per-tracked-
           device; looks like `device_tracker.alice_iphone`,
           `device_tracker.bob_pixel_7`, etc.)
        -> RoamCore contract layer (translation via HA `person`
           entity OR a template helper)
           (device_tracker.rc_presence_person_alice,
            device_tracker.rc_presence_person_bob,
            binary_sensor.rc_presence_anyone_home,           # OR of all rc_presence_person_*
            binary_sensor.rc_presence_only_driver_home,     # declared-driver-only
            sensor.rc_presence_persons_home_count,          # count of rc_presence_person_* == home
            sensor.rc_presence_last_arrival,                # last time anyone_home flipped false -> true
            sensor.rc_presence_last_departure,              # last time anyone_home flipped true -> false
            binary_sensor.rc_presence_all_away,             # inverse of anyone_home (with occupied_threshold_minutes debounce)
            button.rc_presence_refresh_now,                 # force a refresh on all rc_presence_person_*
            select.rc_presence_occupied_threshold_minutes)  # operator-tunable debounce window
        -> dashboard tiles + OpenClaw queries
            ("is anyone home?", "who is home?",
             "persons home count?", "last arrival time?",
             "last departure time?", "is only driver home?",
             "is everyone away?", "refresh presence now")

    Bluetooth + Wi-Fi agreement rule (legacy catalog spec §7,
    reduces iPhone screensaver-sleep false positives):
        -> binary_sensor.rc_presence_anyone_home is computed as
           `true` only when AT LEAST ONE person has BOTH a
           Bluetooth device_tracker AND a Wi-Fi device_tracker in
           the `home` state within a 2-minute window
        -> Falls back to the simple OR rule if only one upstream
           method is wired for a given person

See docs/recipe.md for the full howto (Path A bluetooth_le_tracker
YAML wiring + screensaver-sleep workaround via BLE beacon, Path B
nmap_device_tracker / ping wiring + per-device template helper YAML,
Path C asuswrt / unifi / mikrotik router-side wiring, HA `person`
entity OR template helper translation, mode-aware presence
automations that respect Stealth silent hours + Travel approach
lighting + Boost driver-home-relaxed + inverter-SOC power-aware
occupancy alert that cross-references the Music Assistant
`connections/music-assistant/` recipe for TTS + the Victron
`connections/victron/` recipe for SOC, troubleshooting,
privacy, tier-a promotion outline).
"""

DOMAIN = "bluetooth-wifi-presence"