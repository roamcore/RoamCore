"""Motion-based lighting (driving + arrival) — tier-b recipe connection.

This module is a marker-only stub. Tier-b connections don't ship native
HA integration code; they publish a recipe (docs/recipe.md) that walks
the user through setting up motion-driven + ignition-driven + presence-
driven + dark-outside-driven lighting on the van (Path A — motion
sensor via ZHA / Zigbee2MQTT / ESPHome / Frigate / generic HA
binary_sensor motion feed, exposing `binary_sensor.motion_*` entities;
Path B — ignition / engine-running signal via OBD-II (Wican Pro Wave 3
#6) / 12 V D+ signal via ESPHome analog input / MQTT-published
engine_running topic / manual `input_boolean.engine_running` fallback
(for benches without ignition wiring), exposing
`binary_sensor.engine_running` or `binary_sensor.rc_obd_engine_running`
entities; Path C — presence detection via the bluetooth-wifi-presence
Wave 3 #42 connection's `binary_sensor.rc_presence_anyone_home` +
`binary_sensor.rc_presence_all_away` + per-device `device_tracker.*`
entities; Path D — mode-aware override via
`select.rc_lighting_motion_mode` (off / travel / camp / stealth /
custom) + optional cross-reference to the mode/automation-builder Wave
2 #23 `select.rc_mode` for the higher-level Stealth / Sleep / Boost /
Off integration), and exposes the resulting data via the upstream
binary_sensor / select / number / button / sensor integrations, then
publishes the RoamCore motion-lighting contract tiles on top
(`rc_lighting_*` tiles: the 12 contract entities documented in
connection.yml — 1 binary_sensor motion-available gate + 1 binary_sensor
motion-active aggregate + 1 binary_sensor driving state + 1
binary_sensor dark-outside gate + 2 binary_sensor presence mirrors +
1 select motion-mode + 1 number motion-duration-min + 1 button run-
motion-now + 2 sensor telemetry (last trigger + 24h count) + 1
binary_sensor manual-override-active gate).

The audit + boundary CI can detect a `motion-based-lighting/` folder
that claims to be a connection via the `DOMAIN` constant exported here.
The wizard reads the manifest + recipe at runtime.

The real per-operator motion-lighting affordance path is:

    Operator-side motion-lighting source (Path A — motion sensor via
        HA core `binary_sensor` domain for the PIR / mmWave / Frigate
        motion feed; HA core ZHA GUI flow since 2022.x for Zigbee
        motion sensors (Aqara / Sonoff / Tuya); Zigbee2MQTT GUI flow
        since 2022.x for Zigbee2MQTT-bridged motion sensors; ESPHome
        GUI flow since 2023.x for ESPHome-native mmWave radar
        (HLK-LD2410 / Tuya mmWave); Frigate Wave 3 #35 `event.frigate_
        motion_<camera>` event entity OR `binary_sensor.rc_cctv_motion_
        <camera>` template mirror; OR Path B — ignition signal via the
        Wican Pro Wave 3 #6 OBD-II reader's `binary_sensor.rc_obd_
        engine_running` (the canonical source) OR a 12 V D+ signal via
        ESPHome analog input on GPIO (e.g. GPIO34 ADC1_CH6 on an
        ESP32) with a `binary_sensor.engine_running` template OR the
        upstream `mqtt` integration when the operator's van has an
        MQTT-published engine_running topic (the upstream `mqtt`
        integration exposes a GUI flow since 2022.x) OR a manual
        `input_boolean.engine_running` that the operator toggles for
        benches without ignition wiring; OR Path C — presence via the
        bluetooth-wifi-presence Wave 3 #42 connection's
        `binary_sensor.rc_presence_anyone_home` + `binary_sensor.rc_
        presence_all_away` + per-device `device_tracker.rc_presence_
        person_alice` / `device_tracker.rc_presence_person_bob`
        entities (the bluetooth-wifi-presence connection is its own
        tier-b recipe that owns the presence scanner wiring); OR
        Path D — mode-aware override via the
        `select.rc_lighting_motion_mode` operator-tunable select
        (off / travel / camp / stealth / custom) + optional cross-
        reference to the mode/automation-builder Wave 2 #23
        `select.rc_mode` for the higher-level Stealth / Sleep / Boost
        / Off integration; the operator-wired setup is via HA core
        `template:` binary_sensor / select / number / button / sensor
        helpers)
        -> upstream entity (binary_sensor.motion_* for Path A;
           binary_sensor.engine_running / binary_sensor.rc_obd_engine_
           running for Path B; binary_sensor.rc_presence_anyone_home
           + binary_sensor.rc_presence_all_away + device_tracker.rc_
           presence_person_* for Path C; select.rc_lighting_motion_
           mode for Path D)
        -> RoamCore contract layer (HA core `template:` binary_sensor
           + select + number + button + sensor that maps the upstream
           entities into the 12 `rc_lighting_*` contract tiles —
           rc_lighting_motion_available + rc_lighting_motion_active +
           rc_lighting_driving + rc_lighting_dark_outside +
           rc_lighting_presence_someone_home + rc_lighting_presence_
           all_away + rc_lighting_motion_mode + rc_lighting_motion_
           duration_min + rc_lighting_run_motion_now +
           rc_lighting_last_motion_trigger_minutes_ago +
           rc_lighting_motion_trigger_count_24h +
           rc_lighting_manual_override_active)
        -> dashboard tiles + OpenClaw queries
            ("is anyone home?", "is it dark outside?", "is the
             vehicle moving?", "is motion lighting available?",
             "is any motion automation firing?", "set motion mode
             to off / travel / camp / stealth / custom", "run
             motion lighting now", "what was the last motion
             trigger?", "how many motion triggers in the last
             24h?", "is manual override active?")

    Safety interlocks (MANDATORY before first use — operator must
    wire each one per the recipe §8):
        -> Travel auto-off interior lights: when
           `binary_sensor.engine_running` (Path B ignition source)
           transitions FALSE -> TRUE (engine started) AND
           `select.rc_lighting_motion_mode` IN (travel, custom_with_
           ignition) AND `binary_sensor.rc_lighting_manual_override_
           active` is FALSE, fire interior `light.turn_off` for every
           `light.*` in the `group.interior_lights` group. This is
           the §7.1 SAFETY FEATURE: forgetting to wire this leaves
           interior lights on during driving, which is a legal issue
           in many jurisdictions (headlight laws + interior-
           distraction laws + driver-attention laws). The recipe
           recites the safety warning in §8.1.
        -> Stop-and-soft-interior: when
           `binary_sensor.engine_running` transitions TRUE -> FALSE
           (engine stopped) AND `binary_sensor.rc_lighting_dark_
           outside` is TRUE (sun below horizon OR light lux < 50) AND
           `select.rc_lighting_motion_mode` IN (camp, travel,
           custom_with_ignition), fire interior `light.turn_on` for
           the `group.soft_interior_lights` group (low brightness,
           warm white, 30 sec fade). The recipe recites the safety
           warning in §8.2 (driver shouldn't come home to a black
           cabin — soft-interior at low brightness is the compromise).
        -> Arrival cue (exterior + soft interior): when
           `binary_sensor.rc_presence_all_away` transitions TRUE ->
           FALSE (first person returns home) AND
           `binary_sensor.rc_lighting_dark_outside` is TRUE AND
           `select.rc_lighting_motion_mode` IN (camp,
           custom_with_presence), fire exterior `light.turn_on`
           (the operator's choice of `light.approach_scene` from the
           approach-lights Wave 3 #52 connection) + soft-interior
           fade-in for 5 sec, then auto-off after
           `number.rc_lighting_motion_duration_min` minutes. The
           motion_pillar is an AND-gate here: arrival cue only fires
           when a motion sensor ALSO fires within 30 seconds of the
           presence transition (the recipe explains why in §5.1).
        -> Motion-triggered interior (camping mode): when
           `binary_sensor.rc_lighting_motion_available` transitions
           FALSE -> TRUE (any motion sensor fired) AND
           `binary_sensor.rc_lighting_dark_outside` is TRUE AND
           `select.rc_lighting_motion_mode` IN (camp,
           custom_with_motion), fire interior `light.turn_on` (low
           brightness, warm white) for `number.rc_lighting_motion_
           duration_min` minutes, then auto-off. The
           `binary_sensor.rc_lighting_manual_override_active` gate
           ensures manual toggles pause motion for 5 min (the
           "automations don't fight manual control" requirement from
           the legacy spec). The recipe recites the safety warning
           in §8.4.
        -> Stealth mode suppression: when
           `select.rc_lighting_motion_mode` becomes `stealth` (or
           `select.rc_mode` becomes `stealth` from the mode/
           automation-builder connection), turn off ALL motion-
           triggered automations + cancel any active motion trigger.
           The recipe recites the LEGAL-CAMPGROUND NOTE in §8.5
           that motion lighting in stealth campgrounds is rude +
           illegal in many jurisdictions (some National Parks + BLM
           land + state parks explicitly prohibit artificial light
           during quiet hours).

    Cross-references:
        -> The `binary_sensor.rc_presence_anyone_home` +
           `binary_sensor.rc_presence_all_away` presence source comes
           from the bluetooth-wifi-presence Wave 3 #42 connection
           (cross-reference: `connections/bluetooth-wifi-presence/`).
           That connection is its own tier-b recipe that owns the
           presence scanner wiring (Path A `bluetooth_le_tracker` /
           Path B `nmap_device_tracker` / Path C `asuswrt` / `unifi`
           / `mikrotik`); motion-based-lighting depends on it for
           the §8.3 arrival-cue automation.
        -> The `light.approach_scene` for the §8.3 arrival-cue
           exterior lighting comes from the approach-lights Wave 3
           #52 connection (cross-reference:
           `connections/approach-lights/`). That connection is its
           own tier-b recipe that owns the lighting fixture wiring
           (Path A smart switches / smart bulbs / Path B generic
           relay + HA template light / Path C all-in-one hub); this
           slice assumes the operator already has the approach-lights
           contract wired so `light.approach_scene` (or equivalent)
           is available.
        -> The dark-outside signal comes from the time/weather
           contract (Wave 2 #14 + Wave 2 #15 + Wave 3 #55 atomic
           time) for `sensor.rc_weather_light_lux` OR the HA core
           `sun.sun` integration's below-horizon state (the
           `binary_sensor.rc_lighting_dark_outside` template gates on
           either source).
        -> The mode-aware override can cross-reference the mode/
           automation-builder Wave 2 #23 `select.rc_mode` for the
           higher-level Stealth / Sleep / Boost / Off integration;
           when `select.rc_mode` is `stealth`, motion lighting is
           suppressed; when `select.rc_mode` is `off`, motion
           lighting is fully disabled.
        -> The ignition source optionally cross-references the Wican
           Pro Wave 3 #6 OBD-II reader's
           `binary_sensor.rc_obd_engine_running`; alternatively, the
           upstream `mqtt` integration or ESPHome analog input can
           provide the ignition signal.
        -> The optional motion source can cross-reference the Frigate
           Wave 3 #35 entry-zone `motion` event (for vans with
           Frigate CCTV installed).

See docs/recipe.md for the full howto (Path A motion sensor via
ZHA / Zigbee2MQTT / ESPHome / Frigate / generic HA binary_sensor
with the HA core `binary_sensor` template wiring + the recommended
PIR / mmWave radar / Frigate combinations, Path B ignition signal
via OBD-II (Wican Pro Wave 3 #6) / 12 V D+ signal via ESPHome
analog input / MQTT-published engine_running topic / manual
`input_boolean.engine_running` fallback + the §8.1 travel-auto-off
+ §8.2 stop-and-soft-interior safety-critical automations, Path C
presence via bluetooth-wifi-presence Wave 3 #42's
`binary_sensor.rc_presence_anyone_home` +
`binary_sensor.rc_presence_all_away` + the §8.3 arrival-cue
automation, Path D mode-aware override via
`select.rc_lighting_motion_mode` (off / travel / camp / stealth /
custom) + the §8.5 stealth-mode-suppression automation, the five
§8 automations in full, the seven §9 troubleshooting entries
including "motion lighting never fires" (motion sensor not wired
/ dark sensor not wired / Stealth mode suppressing /
`binary_sensor.rc_lighting_motion_available` is FALSE because of a
missing upstream), "motion lighting stays on forever"
(`number.rc_lighting_motion_duration_min` set too high / the auto-
off automation missing), "Travel auto-off fires while parked at a
stoplight" (the ignition-source debounce is too short), "arrival
cue fires when the operator is just outside the wifi range" (the
presence debounce is too sensitive), "Stealth mode doesn't
suppress" (mode/automation-builder recipe not wired /
`select.rc_mode` tile missing / the `select.rc_lighting_motion_
mode` is set to a non-stealth value), "manual override is fighting
with motion" (the operator manually toggled a light within the
last 5 minutes, and the motion automation is honoring that — the
intended behavior), "motion lighting fires during the day"
(`binary_sensor.rc_lighting_dark_outside` is FALSE but the
automation doesn't gate on it), privacy, tier-a promotion outline).
"""

DOMAIN = "motion_lighting"