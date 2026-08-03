# Motion-based lighting (driving + arrival)

**Tier:** B (recipe)
**Category:** lighting
**Status:** beta

## What this connection is

Motion-based lighting (driving + arrival) — the umbrella for ignition-driven interior auto-off + ignition-driven soft-interior on stop + presence-driven arrival cue + motion-driven interior camping + mode-aware Stealth suppression — is the lighting-category complement to the approach-lights Wave 3 #52 welcome-home scene. The single "is ANY motion automation firing?" tile aggregates all the path-level automation states into one dashboard indicator; the "is motion lighting available?" tile is the meta-gate (TRUE when all the required upstream gates are satisfied AND mode is NOT stealth); the driving + dark-outside + presence mirrors are the per-gate tiles; the operator-tunable motion-mode (off / travel / camp / stealth / custom) + motion-duration-min (default 2; range 0.5–30) tiles cover the day-1 configuration affordances; the run-motion-now button covers the on-demand affordance (testing the wiring without waiting for an ignition / motion / arrival trigger); the last-trigger + 24h-count sensors are the derived metrics for the dashboard telemetry badge; the manual-override-active binary_sensor is the "automations don't fight manual control" gate (5-minute window after a manual `light.turn_on` / `light.turn_off`).

RoamCore ships **no** native motion sensor / ignition signal / presence / dark-outside bench. We RECIPE the well-understood combination of four upstream operator-side paths and a translation layer that maps the upstream `binary_sensor.motion_*` / `binary_sensor.engine_running` / `binary_sensor.rc_presence_*` / `select.rc_lighting_motion_mode` entities into a vendor-neutral `rc_lighting_*` contract layer. The four paths:

- **Path A — Motion sensor (PIR / mmWave / Frigate / generic).** Wired via the upstream `binary_sensor` domain (GUI flow since 2022.x) for the generic HA motion feed OR the upstream ZHA integration (GUI flow since 2022.x) for Zigbee motion sensors (Aqara RTCZCGQ11LM / Sonoff SNZB-03 / Tuya TY-ZT08) OR Zigbee2MQTT (GUI flow since 2022.x) for Zigbee2MQTT-bridged sensors OR ESPHome (GUI flow since 2023.x) for ESPHome-native mmWave radar (HLK-LD2410 / Tuya mmWave). The integration exposes `binary_sensor.motion_*` entities directly. Frigate Wave 3 #35 motion events cross-reference as `event.frigate_motion_<camera>` or the `binary_sensor.rc_cctv_motion_<camera>` template mirror.

- **Path B — Ignition / engine-running signal.** Wired via the Wican Pro Wave 3 #6 OBD-II reader's `binary_sensor.rc_obd_engine_running` (the canonical source — the recipe walks the operator through binding `engine_running: true` → interior `light.turn_off` for the §8.1 Travel auto-off safety feature) OR a 12 V D+ signal via ESPHome analog input on GPIO (e.g. GPIO34 ADC1_CH6 on an ESP32) with a `binary_sensor.engine_running` template OR the upstream `mqtt` integration (GUI flow since 2022.x) when the operator's van has an MQTT-published engine_running topic OR a manual `input_boolean.engine_running` that the operator toggles for benches without ignition wiring (the recipe recites the safety warning that forgetting to toggle off leaves interior lights on).

- **Path C — Presence detection (bluetooth-wifi-presence Wave 3 #42).** Wired via the upstream bluetooth-wifi-presence `binary_sensor.rc_presence_anyone_home` + `binary_sensor.rc_presence_all_away` + per-device `device_tracker.rc_presence_person_<name>` entities. The bluetooth-wifi-presence connection is its own tier-b recipe that owns the presence scanner wiring; motion-based-lighting depends on it for the §8.3 arrival-cue automation.

- **Path D — Mode-aware override (Travel / Camp / Stealth / Custom).** Wired via the operator-tunable `select.rc_lighting_motion_mode` (off / travel / camp / stealth / custom) + optional cross-reference to the mode/automation-builder Wave 2 #23 `select.rc_mode` for the higher-level Stealth / Sleep / Boost / Off integration. In Stealth mode, ALL motion lighting is suppressed (legal campgrounds). In Travel mode, interior auto-off is enforced (the §8.1 safety feature). In Camp mode, motion triggers soft interior + arrival cue + exterior arrival. In Custom mode, the operator picks which pillars are active via `select.rc_lighting_custom_pillars` (all / motion_only / ignition_only / presence_only / motion_and_presence).

All four paths land on the same vendor-neutral contract layer via 12 `rc_lighting_*` dashboard tiles.

## Setup recipe (one-paragraph)

1. Decide which paths fit your van: **Path A** — motion sensor via ZHA / Zigbee2MQTT / ESPHome / Frigate / generic HA binary_sensor (PIR / mmWave / Frigate); **Path B** — ignition signal via OBD-II (Wican Pro Wave 3 #6) / 12 V D+ signal via ESPHome / MQTT-published engine_running / manual `input_boolean.engine_running`; **Path C** — presence via the bluetooth-wifi-presence Wave 3 #42 connection; **Path D** — mode override via `select.rc_lighting_motion_mode` (off / travel / camp / stealth / custom).
2. Wire the prerequisites FIRST (the recipe §2 walks through these). The operator MUST wire at least one of the four upstream paths before this recipe can do anything. The motion-mode + motion-duration-min + dark-outside gate are mandatory for the §8 automations to work.
3. Wire the upstream entity. Path A: pair a motion sensor with HA (ZHA / Zigbee2MQTT / ESPHome / Frigate); Path B: configure OBD-II / ESPHome / MQTT / input_boolean fallback; Path C: ensure the bluetooth-wifi-presence connection is configured and `binary_sensor.rc_presence_anyone_home` + `binary_sensor.rc_presence_all_away` are wired; Path D: pick the motion-mode default (recommended: `camp` for most vans; `off` for legal campgrounds; `travel` for vans that frequently drive).
4. Wire the HA core `template:` (or HA core `entity` customize-domain alias) that maps the upstream entity to one of the 12 contract tiles (`rc_lighting_motion_available` / `rc_lighting_motion_active` / `rc_lighting_driving` / `rc_lighting_dark_outside` / `rc_lighting_presence_someone_home` / `rc_lighting_presence_all_away` / `rc_lighting_motion_mode` / `rc_lighting_motion_duration_min` / `rc_lighting_run_motion_now` / `rc_lighting_last_motion_trigger_minutes_ago` / `rc_lighting_motion_trigger_count_24h` / `rc_lighting_manual_override_active`).
5. Wire the dark-outside signal (`sun.sun` below-horizon OR `sensor.rc_weather_light_lux` < 50 lx) via HA core `template:` binary_sensor → `binary_sensor.rc_lighting_dark_outside`.
6. Verify the five §8 automations (travel-auto-off-interior-lights + stop-and-soft-interior + arrival-cue-exterior-and-soft-interior + motion-triggered-interior-camping + stealth-mode-suppression).
7. Reload the RoamCore dashboard.

Full howto: see [`docs/recipe.md`](docs/recipe.md).

## Why tier-b, not tier-a

Tier-a requires a working RoamCore-owned operator-wired setup flow, integration tests against a real motion + ignition + presence + dark-outside bench (a PIR sensor + a Wican Pro OBD-II + a bluetooth-wifi-presence setup + a `sun.sun` integration + a Frigate entry zone), and `wizard.one_tap: true`. We have no operator-side motion-lighting bench on the CI to integration-test against (the bench requires physical hardware: a PIR / mmWave motion sensor + an OBD-II reader + a bluetooth / Wi-Fi presence setup + a sun sensor + a Frigate CCTV setup, all wired together in a controlled environment). So this connection is honestly beta-tier: the recipe is sound but we cannot claim one-tap automation.

The original legacy catalog page (`docs/catalog/lighting/motion-based-lighting.md`) listed "Support tier: C" with no recipe + no contract + no automations — that placeholder is now superseded by this tier-b recipe connection.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "motion_lighting"` marker for the audit.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded): [`docs/catalog/lighting/motion-based-lighting.md`](../../docs/catalog/lighting/motion-based-lighting.md)
- Approach lights connection (lighting sibling — same subsystem; Wave 3 #52): `connections/approach-lights/`
- Bluetooth / Wi-Fi presence connection (the Path C presence source; Wave 3 #42): `connections/bluetooth-wifi-presence/`
- Wican Pro OBD-II connection (the Path B canonical ignition source; Wave 3 #6): `connections/wican-pro/`
- Frigate CCTV connection (the optional Path A motion source; Wave 3 #35): `connections/frigate/`
- Mode / automation-builder connection (the optional higher-level mode cross-reference; Wave 2 #23): `connections/mode-automation-builder/`
- Time / weather contract (the dark-outside signal; Wave 2 #14 + Wave 2 #15 + Wave 3 #55): `homeassistant/packages/roamcore_weather_time.yaml`
- HVAC basics connection (no relationship): `connections/hvac-basics/`
- Electronic valves connection (no relationship): `connections/electronic-valves/`
- Water tanks connection (no relationship): `connections/water-tanks/`
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`