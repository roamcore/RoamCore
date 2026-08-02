# Approach lights (welcome-home exterior + underbody lighting)

**Tier:** B (recipe)
**Category:** lighting
**Status:** beta

## What this connection is

Approach lights (welcome-home exterior + underbody lighting) is the universal small-comfort van automation: open the door after dark, the underbody + entry + soft-interior lights come on for a configurable duration (default 2 min) so you can see where you're stepping and feel like the van is welcoming you home. The single "approach active" binary_sensor tile aggregates underbody + entry + soft-interior state + the dark-outside gate + the presence-detection trigger into one dashboard indicator; the three per-zone state binary_sensors (underbody_state / entry_state / soft_interior_state) are the per-zone state mirrors; the approach_minutes_remaining + last_approach_trigger_minutes_ago sensors are the derived metrics for the dashboard "last triggered 3 h ago" badge + the countdown timer; the dark_outside binary_sensor is the gate signal (TRUE when `sun.sun` is `below_horizon` OR `sensor.rc_weather_light_lux` < 50 lx — the recipe documents the choice); the approach_available binary_sensor is the meta-gate (TRUE when it's dark + presence is detectable — the gates line up so the scene *can* fire); the operator-tunable approach_mode (auto / dark_only / stealth_only / disabled) + approach_duration_min (default 2; range 1–10) tiles cover the day-1 configuration affordances; the run_approach_now button covers the on-demand affordance (showing a friend where the van is + testing the wiring without waiting for first arrival); the camera_override binary_sensor is the cross-reference to Frigate Wave 3 #35 — TRUE for 30 seconds when a `person` detection fires in the entry zone after dark (a brighter "someone's at the door" cue + soft deterrent).

RoamCore ships **no** native light hardware. We RECIPE the well-understood combination of three upstream operator-side paths and a translation layer that maps the upstream `light.*` / `switch.*` entities into a vendor-neutral `rc_lighting_*` contract layer. The three paths:

- **Path A — Smart switches / smart bulbs (recommended for operators with existing smart lighting).** Vendor: any of Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano Switch (wired switches) + Philips Hue / LIFX / IKEA TRÅDFRI (smart bulbs) + generic-Zigbee / generic-Z-Wave / Tuya (vendor-neutral). The vendor integration exposes `light.*` or `switch.*` entities; the recipe maps each via HA core `template:` light wrappers or HA core `light:` group (since 2022.x).

- **Path B — Generic relay + HA template light (no smart bulb; just a 12 V underbody LED strip + a relay-driven entry light).** Vendor: `shelly` / `zooz` / `aeotec` (HA core, GUI flow since 2022.x) — a Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano Switch wired into the 12 V / 24 V LED driver; HA core `template:` light or `switch:` template wraps the relay into a virtual `light.entry` + `light.underbody` + `light.soft_interior`.

- **Path C — All-in-one smart scene controller (Hue Bridge / Lutron Caséta / IKEA TRÅDFRI / Bond Home for ceiling-fan-light combos).** Vendor: any hub that exposes all lights as `light.*`; the recipe walks the operator through grouping the approach lights into a `light.approach_scene` group entity (HA `light:` group domain since 2022.x) + binding the approach scene to the contract tiles.

All three paths land on the same vendor-neutral contract layer via 12 `rc_lighting_*` dashboard tiles.

## Setup recipe (one-paragraph)

1. Decide which path fits your van: **Path A** — smart switches / smart bulbs you already own (most common for operators with existing smart lighting); **Path B** — generic relay + HA template light (most common for operators with a 12 V / 24 V LED strip + a relay but no smart bulbs); **Path C** — all-in-one smart scene controller (most common when the operator already runs a Hue Bridge / Lutron Caséta / IKEA TRÅDFRI / Bond Home hub).
2. Wire the prerequisites FIRST (the recipe §2 walks through these). The operator MUST not skip the upstream integration prerequisite (the recipe won't work if the vendor's light/switch integration is not already configured in HA).
3. Wire the upstream entity. Path A: pair the Shelly / Hue / Zigbee / Z-Wave / Tuya device via its native integration; Path B: pair the Shelly / Zooz / Aeotec relay + wire the relay contacts into the LED driver + add a `template:` light wrapper; Path C: set up the Hue Bridge / Lutron hub / IKEA gateway / Bond Home + pair the bulbs + create the `light.approach_scene` group.
4. Wire the HA core `template:` (or HA core `light:` group domain since 2022.x) that maps the upstream entity to one of the 12 contract tiles (`rc_lighting_approach_active` / `rc_lighting_approach_available` / `rc_lighting_underbody_state` / `rc_lighting_entry_state` / `rc_lighting_soft_interior_state` / `rc_lighting_approach_minutes_remaining` / `rc_lighting_last_approach_trigger_minutes_ago` / `rc_lighting_dark_outside` / `rc_lighting_approach_mode` / `rc_lighting_approach_duration_min` / `rc_lighting_run_approach_now` / `rc_lighting_camera_override`).
5. Configure the operator-tunable thresholds (`select.rc_lighting_approach_mode` default `auto` + `number.rc_lighting_approach_duration_min` default 2 min, range 1–10).
6. Verify the bluetooth-wifi-presence Wave 3 #42 connection is installed and the `binary_sensor.rc_presence_anyone_home` + `binary_sensor.rc_presence_all_away` are wired (the first-arrival trigger depends on `rc_presence_all_away` transitioning TRUE → FALSE).
7. Verify the dark-outside signal is wired via `sun.sun` (simpler) OR `sensor.rc_weather_light_lux` (more accurate when there's bright streetlight pollution). The recipe documents the choice — `sun.sun` is the zero-config default; `sensor.rc_weather_light_lux` is recommended for urban environments with bright streetlight pollution.
8. Verify the mode/automation-builder connection's `select.rc_mode` is wired (the Stealth-mode-suppression automation depends on it).
9. Optionally wire the Frigate Wave 3 #35 entry-zone `person` detection for the camera-override soft-deterrent (skip this if Frigate is not installed — the camera-override contract tile will simply stay FALSE).
10. Enable the five §7 automations (first-arrival-after-dark + run-on-demand + auto-stop-after-N-min + camera-override-on-frigate-person + stealth-mode-suppression).
11. Reload the RoamCore dashboard.

Full howto: see [`docs/recipe.md`](docs/recipe.md).

## Why tier-b, not tier-a

Tier-a requires a working RoamCore-owned `config_flow.py`, integration tests against a real approach-light bench (a Shelly 1 + 12 V / 24 V LED strip + Hue Bridge + Frigate entry zone, all wired together in a controlled environment), and `wizard.one_tap: true`. We have no operator-side approach-light bench on the CI to integration-test against (the bench requires physical hardware: a Shelly 1 + LED strip + Hue Bridge + Frigate entry zone, all wired together in a controlled environment + a way to simulate the first-arrival / dark / Frigate `person` trigger conditions). So this connection is honestly beta-tier: the recipe is sound but we cannot claim one-tap automation.

The original legacy catalog page (`docs/catalog/lighting/approach-and-underbody-lights.md`) listed "Support tier: C" with no recipe + no contract + no automations — just a placeholder that said "Turn on exterior/underbody lights automatically when you approach the van after dark, so you can see where you're stepping and feel like the van is welcoming you home". The supersession banner on the legacy page reflects that the connection has been promoted to tier-b.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "approach_lights"` marker for the audit.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded): [`docs/catalog/lighting/approach-and-underbody-lights.md`](../../docs/catalog/lighting/approach-and-underbody-lights.md)
- Bluetooth / Wi-Fi presence connection (companion for the §7.1 first-arrival trigger — Wave 3 #42): `connections/bluetooth-wifi-presence/`
- Frigate connection (companion for the §7.4 camera-override soft-deterrent — Wave 3 #35): `connections/frigate/`
- Mode / automation-builder connection (companion for the §7.5 Stealth-mode-suppression automation): `connections/mode-automation-builder/`
- Time / weather contract (companion for the §6 dark-outside signal via `sun.sun` OR `sensor.rc_weather_light_lux`): `homeassistant/packages/roamcore_weather_time.yaml`
- Motion-based lighting connection (companion slice for the driving + ignition path — Wave 3 #53 — same `lighting` subsystem prefix; the `lighting` subsystem addition to `docs/reference/rc-entity-naming.md` lays the groundwork for both slices): `connections/motion-based-lighting/`
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`