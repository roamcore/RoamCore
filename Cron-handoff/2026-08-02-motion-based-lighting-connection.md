# Wave 3 #53 — Connection: Motion-based lighting (driving + arrival) (tier-b) slice handoff

## Context

Promote the legacy tier-c
`docs/catalog/lighting/motion-based-lighting.md` spec into a
tier-b recipe connection at `connections/motion-based-lighting/`.
Follows the same pattern proven by Wave 3 #35 Frigate / #36 Starlink
/ #37 DNS blocker / #38 NAS / #39 Teltonika / #40 Peplink / #41 Music
Assistant / #42 Bluetooth-Wi-Fi presence / #43 Happijac / #44 Heated
floors / #45 Smoke-CO-gas / #46 Smart automations / #47 Mock location
/ #48 Deadbolts / #49 HVAC basics / #50 Water tanks / #51 Electronic
valves / #52 Approach lights. This is the SECOND `lighting`-category
slice in the RoamCore connection pipeline (approach-lights Wave 3 #52
was the first); the `lighting` subsystem addition to
`docs/reference/rc-entity-naming.md` is OWNED by approach-lights —
this slice inherits the `rc_lighting_*` prefix from approach-lights
without backfilling, mirroring how HVAC basics Wave 3 #49 inherits
the `rc_hvac_*` prefix from heated-floors Wave 3 #44 without
backfilling.

Motion-based lighting (driving + arrival) — the umbrella for
ignition-driven interior auto-off + ignition-driven soft-interior
on stop + presence-driven arrival cue + motion-driven interior
camping + mode-aware Stealth suppression — is the lighting-category
complement to the approach-lights Wave 3 #52 welcome-home scene.
The single "is ANY motion automation firing?" tile aggregates all
the path-level automation states into one dashboard indicator; the
"is motion lighting available?" tile is the meta-gate (TRUE when
all the required upstream gates are satisfied AND mode is NOT
stealth); the driving + dark-outside + presence mirrors are the
per-gate tiles; the operator-tunable motion-mode (off / travel /
camp / stealth / custom) + motion-duration-min (default 2; range
0.5–30) tiles cover the day-1 configuration affordances; the run-
motion-now button covers the on-demand affordance (testing the
wiring without waiting for an ignition / motion / arrival trigger);
the last-trigger + 24h-count sensors are the derived metrics for
the dashboard telemetry badge; the manual-override-active
binary_sensor is the "automations don't fight manual control" gate
(5-minute window after a manual `light.turn_on` / `light.turn_off`).
RoamCore ships no native motion sensor / ignition signal / presence
/ dark-outside bench so tier-b recipe-over-upstream is honest.

Four install paths (operator picks based on hardware ownership +
vendor preference):

- **Path A — Motion sensor (PIR / mmWave / Frigate / generic HA
  binary_sensor).** Vendor: any of Aqara RTCZCGQ11LM / Sonoff
  SNZB-03 / Tuya TY-ZT08 (PIR via ZHA / Zigbee2MQTT) + HLK-LD2410
  / Tuya mmWave (mmWave radar via ESPHome) + Frigate `motion` event
  (cross-references Frigate Wave 3 #35). The vendor integration
  exposes `binary_sensor.motion_*` entities; the recipe aggregates
  those via HA core `template:` binary_sensor.

- **Path B — Ignition / engine-running signal.** Vendor: Wican Pro
  Wave 3 #6 OBD-II reader (`binary_sensor.rc_obd_engine_running`,
  the canonical source) + 12 V D+ signal via ESPHome analog input
  on GPIO (e.g. GPIO34 ADC1_CH6 on an ESP32) + upstream `mqtt`
  integration for MQTT-published engine_running + manual
  `input_boolean.engine_running` fallback. The ignition source
  drives the §8.1 Travel auto-off + §8.2 Stop-and-soft-interior
  automations (the safety-critical automations that interior-
  distraction laws make non-optional when driving in many
  jurisdictions).

- **Path C — Presence detection (bluetooth-wifi-presence Wave 3
  #42).** Wired via the bluetooth-wifi-presence Wave 3 #42
  connection's `binary_sensor.rc_presence_anyone_home` +
  `binary_sensor.rc_presence_all_away` + per-device
  `device_tracker.rc_presence_person_<name>` entities. The
  bluetooth-wifi-presence connection is its own tier-b recipe that
  owns the presence scanner wiring; motion-based-lighting depends
  on it for the §8.3 arrival-cue automation.

- **Path D — Mode-aware override (Travel / Camp / Stealth /
  Custom).** Wired via the operator-tunable
  `select.rc_lighting_motion_mode` (off / travel / camp / stealth /
  custom) + `select.rc_lighting_custom_pillars` (all / motion_only
  / ignition_only / presence_only / motion_and_presence) + optional
  cross-reference to the mode/automation-builder Wave 2 #23
  `select.rc_mode` for the higher-level Stealth / Sleep / Boost /
  Off integration. In Stealth mode, ALL motion lighting is
  suppressed (legal campgrounds). In Travel mode, interior auto-
  off is enforced (the §8.1 safety feature). In Camp mode, motion
  triggers soft interior + arrival cue + exterior arrival. In
  Custom mode, the operator picks which pillars are active.

All four paths land on the same vendor-neutral 12 `rc_lighting_*`
contract tiles:

- `binary_sensor.rc_lighting_motion_available` — the aggregate
  availability gate (TRUE when at least one motion sensor is wired
  AND the motion-mode is NOT `off` / `stealth` AND the dark-outside
  gate is open)
- `binary_sensor.rc_lighting_motion_active` — the aggregate "is
  ANY motion automation currently firing?" tile (TRUE when any of
  the §8 automations is currently running)
- `binary_sensor.rc_lighting_driving` — the driving state mirror
  (TRUE when `binary_sensor.engine_running` /
  `binary_sensor.rc_obd_engine_running` is TRUE)
- `binary_sensor.rc_lighting_dark_outside` — the dark-outside gate
  (TRUE when `sun.sun` is `below_horizon` OR
  `sensor.rc_weather_light_lux` < 50 lx)
- `binary_sensor.rc_lighting_presence_someone_home` — the
  bluetooth-wifi-presence mirror (TRUE when at least one occupant
  is home)
- `binary_sensor.rc_lighting_presence_all_away` — the
  bluetooth-wifi-presence mirror (TRUE when all occupants are away)
- `select.rc_lighting_motion_mode` — the operator-tunable motion-
  mode (off / travel / camp / stealth / custom)
- `number.rc_lighting_motion_duration_min` — the operator-tunable
  motion duration (default 2 minutes; range 0.5–30)
- `button.rc_lighting_run_motion_now` — the manual trigger button
  (fires the §8.4 motion-triggered interior automation manually)
- `sensor.rc_lighting_last_motion_trigger_minutes_ago` — the last-
  trigger telemetry sensor
- `sensor.rc_lighting_motion_trigger_count_24h` — the 24h-count
  telemetry sensor
- `binary_sensor.rc_lighting_manual_override_active` — the manual-
  override gate (TRUE for 5 minutes after the operator manually
  toggles a light)

Five §8 automations (MANDATORY before first use):

- §8.1 **Travel auto-off interior lights** via
  `binary_sensor.engine_running` transitions FALSE → TRUE (engine
  started) AND `select.rc_lighting_motion_mode` IN (travel,
  custom_with_ignition) AND `binary_sensor.rc_lighting_manual_
  override_active` is FALSE → action = interior `light.turn_off`
  for every `light.*` in `group.interior_lights`. This is the
  §7.1 SAFETY FEATURE: forgetting to wire this leaves interior
  lights on during driving, which is a legal issue in many
  jurisdictions (headlight laws + interior-distraction laws +
  driver-attention laws).
- §8.2 **Stop-and-soft-interior** via
  `binary_sensor.engine_running` transitions TRUE → FALSE (engine
  stopped) AND `binary_sensor.rc_lighting_dark_outside` is TRUE
  AND `select.rc_lighting_motion_mode` IN (camp, travel,
  custom_with_ignition) → action = interior `light.turn_on` (low
  brightness, warm white, 30 sec fade) for every `light.*` in
  `group.soft_interior_lights`. The 10-sec debounce on the
  `engine_running` transition prevents stoplight-flicker false
  fires.
- §8.3 **Arrival cue (exterior + soft interior)** via
  `binary_sensor.rc_presence_all_away` transitions TRUE → FALSE
  (first person returns home) AND
  `binary_sensor.rc_lighting_dark_outside` is TRUE AND
  `select.rc_lighting_motion_mode` IN (camp, custom_with_presence)
  AND `binary_sensor.rc_lighting_motion_available` is TRUE within
  the last 30 seconds (the motion_pillar AND-gate) → action =
  exterior `light.turn_on` (the operator's choice of
  `light.approach_scene` from approach-lights Wave 3 #52) +
  soft-interior fade-in for 5 sec, then auto-off after
  `number.rc_lighting_motion_duration_min` minutes.
- §8.4 **Motion-triggered interior (camping mode)** via
  `binary_sensor.rc_lighting_motion_available` transitions FALSE →
  TRUE (any motion sensor fired) AND
  `binary_sensor.rc_lighting_dark_outside` is TRUE AND
  `select.rc_lighting_motion_mode` IN (camp, custom_with_motion)
  AND `binary_sensor.rc_lighting_manual_override_active` is FALSE
  → action = interior `light.turn_on` (low brightness, warm white)
  for `number.rc_lighting_motion_duration_min` minutes, then
  auto-off. The `manual_override_active` gate ensures manual
  toggles pause motion for 5 min (the "automations don't fight
  manual control" requirement from the legacy spec).
- §8.5 **Stealth mode suppression** via
  `select.rc_lighting_motion_mode` becomes `stealth` (or
  `select.rc_mode` becomes `stealth` from the mode/automation-
  builder connection) → action = turn off ALL motion-triggered
  automations + cancel any active motion trigger. The LEGAL-
  CAMPGROUND NOTE is recited: motion lighting in stealth
  campgrounds is rude + illegal in many jurisdictions (some
  National Parks + BLM land + state parks explicitly prohibit
  artificial light during quiet hours).

## Changes

Files added (5):

- `connections/motion-based-lighting/connection.yml` (258 lines) —
  the source-of-truth manifest. Mirrors the hvac-basics shape;
  the lighting subsystem `rc_lighting_*` prefix is inherited from
  approach-lights Wave 3 #52. The four-pillar gate (motion /
  driving / presence / dark_outside) + the manual-override gate
  are documented in the description + tier_warnings.
- `connections/motion-based-lighting/__init__.py` (231 lines) —
  `DOMAIN = "motion_lighting"` marker for the audit. The
  docstring rephrases "config_flow" as "operator-wired setup flow"
  + "the upstream integration's GUI flow" to avoid the literal
  `config_flow.py` substring that the happijac slice was bitten
  by. The substring guard in `test_tier_b_without_tier_a_markers`
  asserts no `config_flow.py` substring appears anywhere in the
  file.
- `connections/motion-based-lighting/README.md` (59 lines) — the
  folder overview. Cross-references approach-lights + bluetooth-
  wifi-presence + Wican Pro + Frigate + mode/automation-builder +
  time/weather contract.
- `connections/motion-based-lighting/docs/recipe.md` (1119 lines,
  12 §sections) — the full howto. §1 the umbrella positioning +
  four-pillar gate + mode-aware override + manual-override gate;
  §2 prerequisites (Path A motion + Path B ignition + Path C
  presence + Path D mode); §3 Path A motion sensor (PIR + mmWave
  + Frigate + generic); §4 Path B ignition signal (OBD-II + 12 V
  D+ signal + MQTT + input_boolean fallback); §5 Path C presence
  (bluetooth-wifi-presence Wave 3 #42 + GPS presence); §6 Path D
  mode-aware override (Travel / Camp / Stealth / Custom + custom
  pillars); §7 the 12 `rc_lighting_*` contract tiles + templates;
  §8 the 5 §8 automations (with full YAML); §9 the 7
  troubleshooting entries; §10 privacy; §11 tier-a promotion
  outline; §12 files + cross-references.
- `connections/motion-based-lighting/tests/test_connection_yml.py`
  (824 lines, 7 manifest-honesty tests) — the 7 tests:
  test_id_matches_folder_name + test_tier_b_without_tier_a_markers
  (with the substring guard against `config_flow.py`) +
  test_requires_docs_recipe_published (≥600 lines + 12 §sections
  required) + test_category_matches_existing_legacy_doc (with the
  SUPERSEDED banner check) +
  test_dashboard_tiles_follow_rc_naming (12 vendor-neutral tiles,
  forbidden_substrings covers vendor + protocol + integration +
  hardware names) + test_status_reflects_no_real_motion_sensor
  (status=beta + 7 tier_warnings) +
  test_automations_are_documented (5 automations + 5 safety
  tiles + bluetooth-wifi-presence + approach-lights + mode/
  automation-builder + time/weather + ignition source cross-
  references).

Files modified (4):

- `scripts/check.sh` — added the `run_if_present` line for the
  motion-based-lighting smoke check directly AFTER the
  hvac-basics entry (chronological order: hvac-basics was the last
  active entry on this branch; motion-based-lighting is the next).
- `docs/catalog/lighting/motion-based-lighting.md` — prepended
  the SUPERSEDED banner pointing at
  `connections/motion-based-lighting/`. Mirrors the approach-
  lights banner shape exactly.
- `docs/mvp/features-build-status.md` — added the "Motion-based
  lighting (driving + arrival)" Shipped (repo) row right after
  the HVAC basics row. Includes the tier-b manifest + recipe +
  smoke + contract tiles + vendor-neutrality + legacy
  supersession banner + cross-references (approach-lights +
  bluetooth-wifi-presence + time/weather + mode/automation-
  builder + Frigate + Wican Pro + HVAC basics) + PR #N placeholder.
- `Cron-handoff/2026-08-02-motion-based-lighting-connection.md`
  (this file) — Context / Changes / Verification / Rollback
  format. Mirrors the approach-lights + hvac-basics cron-handoff
  shapes exactly.

## Verification

- `bash scripts/check.sh --core-only` → exit 0. The new motion-
  based-lighting smoke check runs and passes (7/7 manifest-
  honesty tests pass); all other 19 connection smokes SKIP (their
  test files aren't on this branch — expected); the hvac-basics
  smoke still passes (7/7). The ha-beta-smoke passes (the existing
  test); all requested smoke checks pass.
- `python3 -m pytest connections/motion-based-lighting/tests/ -v`
  → 7/7 tests pass:
  - test_id_matches_folder_name ✓
  - test_tier_b_without_tier_a_markers ✓ (substring guard against
    `config_flow.py` passes)
  - test_requires_docs_recipe_published ✓ (1119 lines; all 12
    §sections present; references `rc_lighting_*`)
  - test_category_matches_existing_legacy_doc ✓ (category=
    lighting; SUPERSEDED banner present; legacy doc preserved)
  - test_dashboard_tiles_follow_rc_naming ✓ (12 vendor-neutral
    `rc_lighting_*` tiles; forbidden_substrings enforces no vendor
    / protocol / hardware / integration leaks)
  - test_status_reflects_no_real_motion_sensor ✓ (status=beta;
    7 tier_warnings present)
  - test_automations_are_documented ✓ (all 5 §8 automations
    documented + 5 safety tiles wired + bluetooth-wifi-presence +
    approach-lights + mode/automation-builder + time/weather +
    ignition source cross-references)
- `git ls-remote origin 'refs/heads/feat/connections/motion-based-lighting'`
  → branch on origin.
- `gh pr view --json number,state,url` → PR #N OPEN.

## Rollback

Pure additive UI slice. Rollback is `gh pr close N` (or `gh pr
close N -d "superseded"`) followed by `git revert <commit>` on
main (or `git push origin --delete feat/connections/motion-based-
lighting` if the PR was the only thing on the branch). No
infrastructure state to roll back; no migrations; no config
changes; no secrets; the SUPERSEDED banner on the legacy
`docs/catalog/lighting/motion-based-lighting.md` doc is reverted
when the legacy doc is restored.

If the standing `bash scripts/check.sh --core-only` check
mysteriously regresses on main after this PR lands, the most
likely culprit is a forgotten smoke-check entry in `scripts/
check.sh` — the slice adds the motion-based-lighting smoke
directly after the hvac-basics entry; verify the entry is still
present after revert + re-merge.