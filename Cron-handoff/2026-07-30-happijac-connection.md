# Wave 3 #43 — Connection: Happijac bed lift (tier-b) slice handoff

## Context

Promote the legacy tier-c `docs/catalog/bed-lift/happijac.md` spec
into a tier-b recipe connection at `connections/happijac/`. Follows
the same pattern proven by Wave 3 #35 Frigate / #36 Starlink / #37
DNS blocker / #38 NAS / #39 Teltonika / #40 Peplink / #41 Music
Assistant / #42 Bluetooth-Wi-Fi presence.

Bed lift control — van bed up / down — is the **foundation** of every
sleep-cycle automation in a van with a Happijac (or any 2-relay +
2-limit-switch bed lift: LCI Happijac, DIY linear actuators, winch +
strap, etc.). Bed lift control is the ONLY RoamCore connection where
mis-wiring can cause a physical injury (the bed motor can pinch /
crush an operator or occupant), so the recipe documents the four
MANDATORY safety interlocks (limit-sanity aggregate / low-voltage
lockout via `sensor.rc_power_battery_soc` cross-reference to the
Victron connection / current-based obstruction detection / mode-
aware Stealth + Sleep + Boost lockouts) with the
`test_safety_interlocks_are_documented` defensive guard for the
future tier-a promotion's hard-enforced asserts.

Two install paths (operator picks based on existing IoT wiring +
comfort with ESPHome vs relay-friendly templates):

- **Path A — ESPHome custom cover** (ESPHome-friendly installs;
  ESP32 + 2× GPIO outputs for the relay coils + 2× binary_sensor
  limit inputs with `delayed_off: 100ms` filter + optional CT-clamp
  current sensor on an ADC pin for obstruction detection; ESPHome
  exposes a config_flow since 2023.x).
- **Path B — Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano
  Switch relay pair + HA core `template:` cover** (relay-friendly;
  no ESPHome required; HA's `shelly` integration auto-discovers via
  mDNS with config_flow since 2019.x; the upstream `switch.shelly_*_relay`
  + `binary_sensor.shelly_*_dry_contact` entities get wrapped into
  the same `cover.bed_lift` contract + a
  `current_based_obstruction_detection` template binary_sensor).

Both paths land on the same 12 `rc_bed_lift_*` contract tiles:

- `cover.rc_bed_lift_position` — open/close/stop with position reporting
- `binary_sensor.rc_bed_lift_up_limit` / `..._down_limit` — limit microswitch binary_sensors
- `binary_sensor.rc_bed_lift_moving` — derived from cover state ∈ {opening, closing}
- `sensor.rc_bed_lift_position_pct` — `cover.current_position` (0/100/interpolated)
- `binary_sensor.rc_bed_lift_safety_ok` — limit-sanity aggregate (NOR of `up_limit` AND `down_limit`; FALSE on wiring fault)
- `button.rc_bed_lift_lift` / `..._lower` / `..._stop` — explicit button affordances for agent + automations
- `binary_sensor.rc_bed_lift_obstruction_detected` — TRUE when CT-clamp current sensor (Path A) OR motor-stall heuristic (Path B) detects stalled motor against obstruction
- `binary_sensor.rc_bed_lift_low_voltage_lockout` — TRUE when SOC < 20 % OR shore disconnected AND battery low (cross-references Victron `sensor.rc_power_battery_soc` + `binary_sensor.rc_power_shore_connected`)
- `select.rc_bed_lift_mode` — `auto` / `manual_only` / `disabled` (operator-tunable lockout mode)

This slice does NOT edit `connections/bluetooth-wifi-presence/` (the
parent branch territory), nor any other connection folder, nor the
build-status bluetooth-wifi-presence row. Only the Happijac files +
the `scripts/check.sh` wire-up + the legacy-doc supersession banner
+ the rc-entity-naming subsystems addition + the new build-status
row for Wave 3 #43.

## Changes

- **New** `connections/happijac/connection.yml` (tier-b manifest; 12
  contract tiles + 9 OpenClaw queries + 6 OpenClaw summary keys +
  4 `tier_warnings` honesty markers + vendor-neutral positioning
  header explaining Path A ESPHome vs Path B Shelly/template + the
  four MANDATORY safety interlocks emphasis; mirrors
  bluetooth-wifi-presence manifest shape verbatim with happijac
  substitutions).
- **New** `connections/happijac/__init__.py` (`DOMAIN = "happijac"`
  marker stub; mirrors bluetooth-wifi-presence `__init__.py` shape
  with happijac-specific docstring describing both paths + the
  contract tile flow + the four safety interlocks + the link to
  docs/recipe.md).
- **New** `connections/happijac/README.md` (folder overview; mirrors
  bluetooth-wifi-presence README shape with happijac-specific setup
  recipe + cross-references to Victron + Music Assistant +
  bluetooth-wifi-presence sibling slices).
- **New** `connections/happijac/docs/recipe.md` (~360-line howto;
  required sections §1 "What is Happijac in RoamCore?" / §2
  Prerequisites (Happijac + 2× dry-contact relays + 2× limit
  microswitches + ESPHome device for Path A OR Shelly / Shelly
  Plus / Zooz ZEN17 / Aeotec Nano Switch pair for Path B + 5 V
  logic-level compatibility check + fuse per relay + flyback
  diode per relay coil) / §3 Path A — ESPHome custom cover
  (full YAML with output `bed_lift_up` + output `bed_lift_down` +
  binary_sensor `up_limit` with `delayed_off: 100ms` filter +
  binary_sensor `down_limit` with `delayed_off: 100ms` filter +
  sensor `bed_lift_current` (optional CT clamp) + cover `bed_lift`
  with `open_action` + `close_action` + `stop_action` + open_endstop
  `up_limit` + close_endstop `down_limit`) / §4 Path B — Shelly /
  template cover (5 V signal, common, up, down wiring per Shelly
  unit + HA `shelly` integration auto-discovery via mDNS since
  2019.x + template cover wiring two Shelly switches + limits +
  optional `current_based_obstruction_detection` block) / §5
  RoamCore contract entities (the 12 `rc_bed_lift_*` tiles + how
  the cover template exposes them + translation helpers needed
  for binary_sensors / numeric position / mode select) / §6
  Safety interlocks (MANDATORY before first use) covering limit-
  switch sanity + low-voltage lockout via Victron cross-reference
  + obstruction detection + mode-aware Stealth/Sleep/Boost
  lockouts / §7 Automations (Stealth auto-stop / Sleep lock-down
  23:00 auto-lower / Boost disable-mode-aware-lockouts / low-
  voltage lockout when SOC < 20 % with MA TTS / obstruction
  detected → stop + alert with MA TTS / mode-aware gentle
  reminder when only-driver-home for >15 min using bluetooth-wifi-
  presence `binary_sensor.rc_presence_only_driver_home`) / §8
  Troubleshooting (8 entries: bed not moving relay polarity /
  coil voltage, one limit stuck replace microswitch, both limits
  TRUE wiring fault, bed moves up but not down NC/NO mis-wire,
  obstruction false-positive tune current threshold, low-voltage
  lockout stuck after charging cross-check Victron, Shelly not
  discovered mDNS IGMP snooping, ESPHome device offline check
  Wi-Fi + USB-C power) / §9 Privacy (no telemetry beyond
  position; local-only limit microswitches + CT clamp; no Happijac
  cloud / no ESPHome cloud / no Shelly cloud / no Zooz / Aeotec
  cloud) / §10 Promoting to tier-a (real Happijac + ESPHome +
  relay bench on CI + RoamCore-owned `config_flow.py` walking
  Path A vs Path B + relay pin / limit pin / current-sensor pin
  declaration + integration tests asserting the 4 safety
  interlocks all flip + a 0→100% `cover.rc_bed_lift_position`
  change triggers the right tile updates)).
- **New** `connections/happijac/tests/test_connection_yml.py` (7
  manifest-honesty tests: id matches folder / tier-b without
  tier-a markers / docs recipe published with §1–§10 sections /
  category `bed_lift` matches legacy doc / dashboard tiles follow
  rc naming (12 tiles; vendor name strict + generic-noun lenient
  on the spec-required tile IDs that contain bed/lift in suffix)
  / status reflects no real happijac with all 4 honesty warnings
  in tier_warnings / safety interlocks are documented — defensive
  guard for the future tier-a promotion).
- **Modify** `scripts/check.sh` — append a `run_if_present` entry
  for `connections/happijac/tests/test_connection_yml.py` directly
  after the existing bluetooth-wifi-presence entry.
- **Modify** `docs/catalog/bed-lift/happijac.md` — add a
  supersession banner at the top pointing at the new connection
  folder (legacy content below the banner is preserved for
  historical context).
- **Modify** `docs/reference/rc-entity-naming.md` — add `bed_lift`
  AND backfill `presence` to the Allowed subsystems list (Wave 3
  #42 promised `presence` in a code comment but it never landed;
  this slice adds it alongside the new `bed_lift` addition).
- **Modify** `docs/mvp/features-build-status.md` — add a "Shipped
  (repo)" row for Wave 3 #43 mirroring the bluetooth-wifi-presence
  row shape (manifest + recipe size + manifest-honesty smoke +
  contract entities + supersession banner + cross-references to
  Victron for SOC + to bluetooth-wifi-presence for the only-
  driver-home gentle reminder automation + PR #47 link).
- **New** `Cron-handoff/2026-07-30-happijac-connection.md` (this
  file — slice summary with Context / Changes / Verification /
  Rollback).

## Verification

Run locally before pushing:

```bash
cd /home/bernard/clawd/RoamCore
git status                                    # clean or only the new files
python3 -m pytest connections/happijac/tests/test_connection_yml.py -v
                                               # expect 7/7 PASS
bash scripts/check.sh --core-only              # expect "✓ all requested smoke checks passed."
python3 -c "import yaml; m=yaml.safe_load(open('connections/happijac/connection.yml')); \
            assert m['id']=='happijac' and m['tier']=='b' and m['category']=='bed_lift' \
            and all('happijac' not in t.lower().replace('happijac','__strip__') for t in m['dashboard']['tiles'])" \
                                               # expect VERIFICATION OK
git log --oneline -3                          # confirm new commit on feat/connections/happijac
git push -u origin feat/connections/happijac   # push
gh pr create --base main --head feat/connections/happijac \
  --title "Wave 3 #43: Connection: Happijac bed lift (tier-b) — van bed up/down control" \
  --body "<commit body>"                        # open PR (PR #47)
```

## Rollback

If something goes wrong post-merge:

1. Revert the merge commit on `main` (`git revert -m 1 <merge-sha>`).
2. The legacy `docs/catalog/bed-lift/happijac.md` already carries a
   supersession banner pointing at `connections/happijac/`, so even
   post-revert operators have a pointer to the previous tier-c spec.
3. Delete the `feat/connections/happijac` branch
   (`git branch -d feat/connections/happijac` + `git push origin
   --delete feat/connections/happijac`) once the PR is closed.
4. If the smoke check itself needs to be removed pre-merge, drop
   the `run_if_present "connections/happijac/tests/..."` line from
   `scripts/check.sh` — the connection folder can exist without
   the wire-up until tier-a promotion lands.
5. If the `bed_lift` / `presence` subsystem addition to
   `docs/reference/rc-entity-naming.md` needs to be reverted
   separately, restore the file from the previous commit (the only
   other edit in the slice that touches shared docs is the
   build-status row addition for Wave 3 #43, which is also
   reversible independently).

## Notes for next slice

- The Happijac recipe references the Victron + Music Assistant +
  bluetooth-wifi-presence connection folders as companions
  (Victron for §6.2 low-voltage lockout; Music Assistant for §7.5
  obstruction detected → stop + alert TTS; bluetooth-wifi-presence
  for §7.6 only-driver-home gentle reminder). Keep the cross-refs
  intact as those slices evolve.
- The recipe's `test_safety_interlocks_are_documented` defensive
  guard fires today (all four safety interlocks ARE documented in
  recipe §6); the tier-a promotion would move that assertion from
  "documented in the recipe" to "hard-enforced in RoamCore-side
  integration code" — at that point the test becomes a runtime
  assertion rather than a documentation assertion.
- The §3 ESPHome YAML is operator-portable (the operator's exact
  pin / fuse / flyback-diode choices are theirs); the §4 Shelly
  template cover YAML uses well-understood upstream `switch.shelly_*
  _relay` + `binary_sensor.shelly_*_dry_contact` entity ids.
- The recipe's §5 `rc_bed_lift_*` contract layer is fully written
  in YAML (template cover + template binary_sensor + template
  sensor + button + select); operators wire those manually until
  tier-a promotion lands.
