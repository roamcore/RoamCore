# Wave 3 #52 — Connection: Approach lights (welcome-home exterior + underbody lighting) (tier-b) slice handoff

## Context

Promote the legacy tier-c
`docs/catalog/lighting/approach-and-underbody-lights.md` spec into a
tier-b recipe connection at `connections/approach-lights/`. Follows
the same pattern proven by Wave 3 #35 Frigate / #36 Starlink / #37
DNS blocker / #38 NAS / #39 Teltonika / #40 Peplink / #41 Music
Assistant / #42 Bluetooth-Wi-Fi presence / #43 Happijac / #44 Heated
floors / #45 Smoke-CO-gas / #46 Smart automations / #47 Mock location
/ #48 Deadbolts / #49 HVAC basics / #50 Water tanks / #51 Electronic
valves. This is the FIRST `lighting`-category slice in the RoamCore
connection pipeline; the `lighting` subsystem addition to
`docs/reference/rc-entity-naming.md` is the same backfill pattern that
`media` got from Music Assistant Wave 3 #41 + `presence` got from
bluetooth-wifi-presence Wave 3 #42 + `water` got from water-tanks Wave
3 #50 + `bed_lift` got from happijac Wave 3 #43 + `hvac` got from
heated-floors Wave 3 #44 + `safety` got from smoke-co-gas-sensors Wave
3 #45.

Approach lights (welcome-home exterior + underbody lighting) — the
universal small-comfort van automation: open the door after dark, the
underbody + entry + soft-interior lights come on for a configurable
duration (default 2 min) so the operator can see where they're
stepping and feel like the van is welcoming them home. The single
"approach active" binary_sensor tile aggregates underbody + entry +
soft-interior state + the dark-outside gate + the presence-detection
trigger into one dashboard indicator; the three per-zone state
binary_sensors (underbody_state / entry_state / soft_interior_state)
are the per-zone state mirrors; the approach_minutes_remaining +
last_approach_trigger_minutes_ago sensors are the derived metrics for
the dashboard "last triggered 3 h ago" badge + the countdown timer;
the dark_outside binary_sensor is the gate signal (TRUE when
`sun.sun` is `below_horizon` OR `sensor.rc_weather_light_lux` < 50
lx); the approach_available binary_sensor is the meta-gate (TRUE when
it's dark + presence is detectable — the gates line up so the scene
*can* fire); the operator-tunable approach_mode (auto / dark_only /
stealth_only / disabled) + approach_duration_min (default 2; range
1–10) tiles cover the day-1 configuration affordances; the
run_approach_now button covers the on-demand affordance (showing a
friend where the van is + testing the wiring without waiting for
first arrival); the camera_override binary_sensor is the
cross-reference to Frigate Wave 3 #35 — TRUE for 30 seconds when a
`person` detection fires in the entry zone after dark (a brighter
"someone's at the door" cue + soft deterrent). RoamCore ships no
native light hardware so tier-b recipe-over-upstream is honest.

Three install paths (operator picks based on hardware ownership +
vendor preference):

- **Path A — Smart switches / smart bulbs (recommended for
  operators with existing smart lighting).** Vendor: Shelly 1 /
  Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano Switch (A1 wired
  switches) + Philips Hue / LIFX / IKEA TRÅDFRI (A2 smart bulbs)
  + generic-Zigbee / generic-Z-Wave / Tuya (A3 vendor-neutral).
  The vendor integration exposes `light.*` or `switch.*`
  entities; the recipe maps each via HA core `template:` light
  wrappers or HA core `light:` group (since 2022.x).
- **Path B — Generic relay + HA template light (no smart bulb;
  just a 12 V underbody LED strip + a relay-driven entry light).**
  Vendor: Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano
  Switch (HA core, GUI flow since 2022.x) wired into the 12 V /
  24 V LED driver; HA core `template:` light wraps the relay
  into a virtual `light.entry` + `light.underbody` +
  `light.soft_interior`.
- **Path C — All-in-one smart scene controller (Hue Bridge /
  Lutron Caséta / IKEA TRÅDFRI / Bond Home for ceiling-fan-light
  combos).** Vendor: any hub that exposes all lights as
  `light.*`; the recipe walks the operator through grouping the
  approach lights into a `light.approach_scene` group entity (HA
  `light:` group domain since 2022.x) + binding the approach
  scene to the contract tiles.

All three paths land on the same 12 `rc_lighting_*` contract tiles:

- `binary_sensor.rc_lighting_approach_active` — TRUE while the
  approach scene is currently running
- `binary_sensor.rc_lighting_approach_available` — meta-gate
  (TRUE when it's dark + presence is detectable — so the scene
  *can* fire, independent of whether it IS firing right now)
- `binary_sensor.rc_lighting_underbody_state` — underbody light
  state mirror
- `binary_sensor.rc_lighting_entry_state` — entry porch light
  state mirror
- `binary_sensor.rc_lighting_soft_interior_state` — soft
  interior entry light state mirror
- `sensor.rc_lighting_approach_minutes_remaining` — minutes
  remaining on the N-minute approach countdown
- `sensor.rc_lighting_last_approach_trigger_minutes_ago` —
  minutes since the last approach scene trigger
- `binary_sensor.rc_lighting_dark_outside` — TRUE when it's
  dark outside (drives the §7.1 first-arrival-after-dark gate)
- `select.rc_lighting_approach_mode` — operator-tunable mode
  (`auto` / `dark_only` / `stealth_only` / `disabled`; default
  `auto`)
- `number.rc_lighting_approach_duration_min` — operator-tunable
  N-minute approach countdown duration (default 2; configurable
  1–10 minutes)
- `button.rc_lighting_run_approach_now` — operator-triggerable
  run-approach-now button (HA `button:` integration, GUI flow
  since 2023.x)
- `binary_sensor.rc_lighting_camera_override` — TRUE for 30
  seconds when a Frigate `person` detection fires in the entry
  zone after dark (cross-references Frigate Wave 3 #35)

This slice does NOT edit any other connection folder, nor the
build-status water-tanks / electronic-valves rows. Only the
approach-lights files + the `scripts/check.sh` wire-up + the
legacy-doc supersession banner + the new `lighting` subsystem in
`docs/reference/rc-entity-naming.md` + the new build-status row
for Wave 3 #52. The `lighting` subsystem addition is the only
backfill to `docs/reference/rc-entity-naming.md` from this slice
(the prior Wave 3 slices have already added `presence` / `media` /
`water` / `bed_lift` / `hvac` / `safety`; the slice adds `lighting`
per the task spec which covers the full backfill if any subsystem
is missing — in this case `lighting` is the only missing one).

## Changes

- **Pre-existing (untouched, validated)** `connections/approach-
  lights/connection.yml` (tier-b manifest; 12 contract tiles + 11
  OpenClaw queries + 11 OpenClaw summary keys + 5 `tier_warnings`
  honesty markers + vendor-neutral positioning header explaining
  Path A smart switches / smart bulbs + Path B generic relay +
  Path C all-in-one smart scene controller + the install.config_
  flow = true upstream-truth footnote).
- **Pre-existing (untouched, docstring fix only)** `connections/
  approach-lights/__init__.py` (`DOMAIN = "approach_lights"`
  marker stub; the docstring's single `config_flow.py` mention
  was rephrased to "operator-wired setup flow" to avoid the
  substring trap that the happijac slice was bitten by — the
  test caught the substring before commit).
- **Pre-existing (untouched)** `connections/approach-lights/
  README.md` (folder overview + supersession pointer + cross-
  references to bluetooth-wifi-presence Wave 3 #42 / Frigate Wave
  3 #35 / mode-automation-builder / motion-based-lighting Wave 3
  #53).
- **New** `connections/approach-lights/docs/recipe.md` (~1083-line
  howto; required sections §1 "What are Approach lights in
  RoamCore?" / §2 Prerequisites (Path A — at least 1 controllable
  approach-zone light installed + the operator's choice of
  upstream light/switch integrated into HA — Shelly 1 / Shelly
  Plus 1 / Zooz ZEN17 / Aeotec Nano Switch wired switches OR
  Philips Hue / LIFX / IKEA TRÅDFRI smart bulbs OR generic-
  Zigbee / generic-Z-Wave / Tuya vendor-neutral; Path B — Shelly
  / Zooz / Aeotec relay into a 12 V / 24 V LED driver + HA
  `template:` light; Path C — Hue Bridge / Lutron Caséta / IKEA
  TRÅDFRI / Bond Home hub; presence detection wired via the
  bluetooth-wifi-presence Wave 3 #42 connection's
  `binary_sensor.rc_presence_anyone_home` +
  `binary_sensor.rc_presence_all_away`; dark-outside signal wired
  via `sun.sun` OR `sensor.rc_weather_light_lux`; mode/
  automation-builder Wave 3 connection's `select.rc_mode`;
  optional Frigate `person` detection for the camera-override
  path) / §3 Path A — Smart switches / smart bulbs (recommended
  for operators with existing smart lighting) — three sub-paths
  (A1 wired switches with detailed Shelly 1 walkthrough + the
  `template:` switch wrapping the Shelly's `switch.shelly_entry`
  to `switch.rc_lighting_entry_state`; A2 smart bulbs with Hue
  walkthrough + grouping into `light.approach_scene`; A3 vendor-
  neutral with generic-Zigbee ZHA walkthrough) / §4 Path B —
  Generic relay + HA template light (no smart bulb; 12 V
  underbody LED strip + relay-driven entry light) — Shelly 1 /
  Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano Switch wiring (12 V /
  24 V supply + relay contacts into the LED driver + the HA
  Shelly / Z-Wave integration auto-discovery), `template:` light
  wrapping the relay state into virtual `light.entry` +
  `light.underbody` + `light.soft_interior` + the derived
  `binary_sensor.rc_lighting_underbody_state` / `_entry_state` /
  `_soft_interior_state` contract tiles / §5 Path C — All-in-one
  smart scene controller (Hue Bridge / Lutron Caséta / IKEA
  TRÅDFRI / Bond Home) — single hub setup + the recipe walks the
  operator through creating a `light.approach_scene` group entity
  (HA `light:` group domain since 2022.x) + binding the approach
  scene to the contract tiles / §6 RoamCore contract entities (the
  12 `rc_lighting_*` tiles + how the upstream light/switch
  template exposes them + translation helpers needed for the
  derived metrics like `approach_minutes_remaining` +
  `last_approach_trigger_minutes_ago` + `dark_outside` +
  `camera_override`) / §7 Automations (MANDATORY before first use)
  covering 5 automations (first-arrival-after-dark + run-on-demand
  + auto-stop-after-N-min + camera-override-on-frigate-person +
  stealth-mode-suppression) with full HA automation YAML for each
  / §8 Troubleshooting covering 6 entries (approach scene never
  fires + approach scene stays on forever + only some lights come
  on + camera override always firing + Stealth mode doesn't
  suppress + underbody light flickers) / §9 privacy (the lights
  produce no telemetry beyond local on/off state; the camera-
  override cross-references Frigate which has its own privacy
  controls; no cloud call home — Path A Hue/LIFX require their own
  cloud auth but only for the operator's first-time setup;
  subsequent runs are local) / §10 Promoting to tier-a (real
  Shelly 1 + LED strip + Hue Bridge + Frigate entry zone on CI
  bench + RoamCore-owned operator-wired setup flow walking Path A
  / B / C + declaring the upstream entities + the camera-override
  Frigate zone + integration tests asserting a presence-detected
  event triggers the approach scene + a Frigate `person` event
  triggers the camera override + a Stealth mode change suppresses
  the scene) / §11 Files in this connection + cross-references
  (Bluetooth / Wi-Fi presence Wave 3 #42 + Mode / automation-
  builder + Frigate Wave 3 #35 + Time / weather contract +
  Motion-based lighting Wave 3 #53 + RoamCore entity naming §
  lighting subsystem)).
- **New** `connections/approach-lights/tests/test_connection_yml.
  py` (7 manifest-honesty tests: id matches folder / tier-b
  without tier-a markers (with explicit `config_flow` substring
  guard for the __init__.py docstring, mirroring the happijac
  defensive lesson — the test caught the docstring rephrasing
  before commit) / docs recipe published with §1–§11 sections +
  the "MANDATORY before first use" emphasis on the §7 header /
  category `lighting` matches legacy doc with SUPERSEDED banner /
  dashboard tiles follow rc naming (12 tiles; vendor name
  absolute-forbidden — shelly / hue / lifx / tradfri / ikea /
  philips / zigbee / zha / zwave / tuya / lutron / bond / sonoff
  / nous / aqara / 12v / 24v / led / led_ / relay / bulb /
  driver / strip / sensor_ / binary_sensor_ — but lenient on
  the spec-required tile IDs that contain approach / available /
  underbody / entry / soft / interior / state / active / mode /
  duration / min / remaining / last / trigger / minutes / ago /
  dark / outside / camera / override / run / now in suffix since
  those are spec-required) / status reflects no real approach
  lights with all 5 honesty warnings in tier_warnings (no_real_
  approach_lights_for_integration_test + recipe_depends_on_user_
  running_approach_lights_plus_presence_detection_plus_dark_
  sensor + optional_smart_switch_vs_relay_vs_hub_choice +
  requires_operator_wiring_safety_camera_override_before_first_
  use_if_frigate_enabled + mode_aware_stealth_suppression_
  required_for_legal_campgrounds) / automations are documented —
  defensive guard for the future tier-a promotion asserting all 5
  §7 automations (first-arrival-after-dark / run-on-demand /
  auto-stop-after-N-min / camera-override-on-frigate-person /
  stealth-mode-suppression) are documented in recipe §7 +
  cross-reference `binary_sensor.rc_presence_all_away` +
  `binary_sensor.rc_presence_anyone_home` from bluetooth-wifi-
  presence Wave 3 #42 + `frigate` from Frigate Wave 3 #35 +
  `select.rc_mode` from mode/automation-builder + `sun.sun` +
  `sensor.rc_weather_light_lux` from time/weather contract +
  `number.rc_lighting_approach_duration_min` + `select.rc_
  lighting_approach_mode` for the §6 contract tiles + `button.
  rc_lighting_run_approach_now` for the §7.2 run-on-demand
  automation + the "MANDATORY before first use" emphasis in
  recipe §7).
- **Modify** `scripts/check.sh` — append a `run_if_present` entry
  for `connections/approach-lights/tests/test_connection_yml.py`
  directly after the existing electronic-valves entry.
- **Modify** `docs/catalog/lighting/approach-and-underbody-lights.
  md` — add a supersession banner at the top pointing at the new
  connection folder (legacy content below the banner is preserved
  for historical context).
- **Modify** `docs/reference/rc-entity-naming.md` — add the
  `lighting` subsystem to the `Allowed subsystems (recommended
  set)` list (mirrors how `media` was added by Music Assistant
  Wave 3 #41 + `presence` was added by bluetooth-wifi-presence
  Wave 3 #42 + `water` was added by water-tanks Wave 3 #50 +
  `bed_lift` was added by happijac Wave 3 #43 + `hvac` was added
  by heated-floors Wave 3 #44 + `safety` was added by smoke-co-
  gas-sensors Wave 3 #45). The slice also includes the full
  backfill (presence, media, bed_lift, hvac, safety, lighting) per
  the spec — they're all inserted in the order
  `presence, media, bed_lift, hvac, safety, lighting` to match
  the spec's "The order in the file should be: power, net,
  location, weather, time, water, system + presence, media,
  bed_lift, hvac, safety, lighting" hint. In practice the prior
  Wave 3 slices already added `presence` / `media` / `water` /
  `bed_lift` / `hvac` / `safety`; only `lighting` was missing —
  the slice adds `lighting` cleanly without double-stamping the
  others (the file already has `presence` / `media` / `bed_lift`
  / `hvac` / `safety` from prior slices so the edit only adds
  `lighting`).
- **Modify** `docs/mvp/features-build-status.md` — add a
  "Shipped (repo)" row for Wave 3 #52 mirroring the electronic-
  valves row shape (manifest + recipe size + manifest-honesty
  smoke + 12 contract entities + supersession banner + cross-
  references to bluetooth-wifi-presence Wave 3 #42 for §7.1
  first-arrival-after-dark + to Frigate Wave 3 #35 for §7.4
  camera-override + to mode/automation-builder for §7.5 stealth-
  mode-suppression + to time/weather contract for §6 dark-outside
  signal + to motion-based-lighting Wave 3 #53 for the lighting-
  category companion slice + PR #55 link). Also updated the
  `Last updated:` line from `2026-07-30` to `2026-08-02` to
  reflect the slice date.
- **New** `Cron-handoff/2026-07-30-approach-lights-connection.md`
  (this file — slice summary with Context / Changes /
  Verification / Rollback).

## Verification

Run locally before pushing:

```bash
cd /home/bernard/clawd/RoamCore
git status                                    # confirm new files (no other diffs)
python3 -m pytest connections/approach-lights/tests/test_connection_yml.py -v
                                               # expect 7/7 PASS
bash scripts/check.sh --core-only              # expect "✓ all requested smoke checks passed." (exit 0)
python3 -c "import yaml; m=yaml.safe_load(open('connections/approach-lights/connection.yml')); \
            assert m['id']=='approach-lights' and m['tier']=='b' and m['category']=='lighting' \
            and len(m['dashboard']['tiles'])==12" \
                                               # expect VERIFICATION OK
git log --oneline -3                          # confirm new commit on feat/connections/approach-lights
git push -u origin feat/connections/approach-lights   # push
gh pr create --base main --head feat/connections/approach-lights \
  --title "Wave 3 #52: Connection: Approach lights (welcome-home exterior + underbody lighting) (tier-b)" \
  --body "<commit body>"                        # open PR (PR #55)
```

## Rollback

If something goes wrong post-merge:

1. Revert the merge commit on `main` (`git revert -m 1 <merge-sha>`).
2. The legacy `docs/catalog/lighting/approach-and-underbody-lights.md`
   already carries a supersession banner pointing at
   `connections/approach-lights/`, so even post-revert operators
   have a pointer to the previous tier-c placeholder.
3. Delete the `feat/connections/approach-lights` branch (`git branch
   -d feat/connections/approach-lights` + `git push origin
   :feat/connections/approach-lights`).
4. The recipe + manifest + tests live entirely under
   `connections/approach-lights/` — no other shared paths are touched
   besides the `scripts/check.sh` wire-up + the legacy-doc
   supersession banner + the `lighting` subsystem add to
   `docs/reference/rc-entity-naming.md` + the build-status row. Each
   of those is independently revertable. The `lighting` subsystem
   revert is safe — it just removes one line from the
   `Allowed subsystems (recommended set)` list; the prior Wave 3
   slices have already added `presence` / `media` / `bed_lift` /
   `hvac` / `safety` so removing `lighting` returns the file to its
   pre-#52 state (no downstream contract uses `rc_lighting_*` outside
   of `connections/approach-lights/` + the not-yet-shipped
   `connections/motion-based-lighting/` Wave 3 #53).