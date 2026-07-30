# Wave 3 #51 — Connection: Electronic valves + auto tank switching (tier-b) slice handoff

## Context

Promote the legacy tier-c `docs/catalog/water/electronic-valves-and-auto-tank-switch.md`
spec into a tier-b recipe connection at `connections/electronic-valves/`.
Follows the same pattern proven by Wave 3 #35 Frigate / #36 Starlink /
#37 DNS blocker / #38 NAS / #39 Teltonika / #40 Peplink / #41 Music
Assistant / #42 Bluetooth-Wi-Fi presence / #43 Happijac / #44 Heated
floors / #45 Smoke-CO-gas / #46 Smart automations / #47 Mock location /
#48 Deadbolts / #49 HVAC basics / #50 Water tanks.

Electronic valves + auto tank switching — fresh-inlet / grey-drain /
aux-tank valve control + auto tank switching between primary and aux
tanks + the six MANDATORY safety interlocks (leak detected / freeze
risk / low-voltage lockout / auto-close grey / mode-aware lockouts /
valve stuck-open detector) — is the vendor-neutral surface that turns
"which tank am I drawing from right now?" + "is the grey valve about
to overflow?" + "can I safely open a valve when the battery is low?"
into a dashboard tile + a push notification + a mode-aware automation.
RoamCore ships no native valve hardware so tier-b recipe-over-upstream
is honest. The upstream `valve` + `switch` + `template` + `esphome` +
`shelly` + `input_boolean` + `input_select` + `input_number` +
`binary_sensor` + `button` domains cover all the integration paths:
12 V / 24 V electrically-actuated valves (latching solenoid /
motorized ball / proportional), relay drivers (1-channel relay /
MOSFET H-bridge / BTS7960 43 A / IBOM), valve-position feedback
(limit switch or current sense), and the auto tank switching logic
that swaps between primary + aux tanks based on the water-tanks
Wave 3 #50 §6 fresh level sensors.

Two install paths (operator picks based on hardware ownership +
ESPHome familiarity + vendor preference):

- **Path A — ESPHome valve node (recommended for ESPHome-friendly
  installs).** One ESP32 per node, 3× 12 V / 24 V electrically-
  actuated valves (one each for fresh inlet, grey drain, aux tank
  switching) wired into GPIO + a safe driver (1-channel relay
  module for latching solenoids; MOSFET H-bridge for motorized
  ball valves; BTS7960 43 A H-bridge for high-current motorized
  ball valves; IBOM for proportional valves) per valve; the
  ESPHome YAML exposes `switch.<node>_valve_fresh_inlet` +
  `switch.<node>_valve_grey_drain` +
  `switch.<node>_valve_aux_tank` + the
  `binary_sensor.<node>_valve_*_position` feedback (limit
  switch or current sense).
- **Path B — Generic relay + HA template valve (no ESPHome).** A
  Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano Switch
  wired into the 12 V / 24 V valve coils + HA core `template:`
  valve or `switch:` template + valve-position feedback
  binary_sensor.

Both paths land on the same 17 `rc_water_valve_*` contract tiles:

- `switch.rc_water_valve_fresh_inlet_state` — fresh inlet
  valve control
- `switch.rc_water_valve_grey_drain_state` — grey drain valve
  control
- `switch.rc_water_valve_aux_tank_state` — aux tank switching
  valve control
- `binary_sensor.rc_water_valve_fresh_inlet_position` — fresh
  inlet valve position (limit switch or current sense)
- `binary_sensor.rc_water_valve_grey_drain_position` — grey
  drain valve position
- `binary_sensor.rc_water_valve_aux_tank_position` — aux tank
  valve position
- `binary_sensor.rc_water_valve_any_moving` — TRUE when at
  least one valve is currently in motion (also catches the
  §7.6 stuck-open detector)
- `binary_sensor.rc_water_valve_auto_tank_switch_active` —
  TRUE when auto tank switching is currently engaged
- `binary_sensor.rc_water_valve_leak_detected_lockout` — TRUE
  when the leak-detected safety interlock is currently holding
  all valves closed
- `binary_sensor.rc_water_valve_freeze_risk_lockout` — TRUE
  when the freeze-risk safety interlock is currently holding
  all valves closed
- `select.rc_water_valve_active_tank` — operator-tunable
  active tank (`auto` / `primary` / `aux`; default `auto`)
- `select.rc_water_valve_mode` — operator-tunable mode (`auto`
  / `manual_only` / `stealth_only` / `silent` / `disabled`;
  default `auto`)
- `number.rc_water_valve_auto_close_grey_min` — operator-
  tunable auto-close-grey-minutes (default 15 min,
  configurable 5–60 min)
- `number.rc_water_valve_low_voltage_lockout_soc_pct` —
  operator-tunable low-voltage lockout SOC threshold
  (default 20 %, configurable 10–50 %)
- `binary_sensor.rc_water_valve_low_voltage_lockout` — TRUE
  when SOC < threshold AND shore disconnected
- `button.rc_water_valve_open_all` — emergency open all
  valves button
- `button.rc_water_valve_close_all` — emergency close all
  valves button (panic-stop)

This slice does NOT edit `connections/water-tanks/` (the
parent branch territory), nor any other connection folder, nor
the build-status water-tanks row. Only the electronic-valves
files + the `scripts/check.sh` wire-up + the legacy-doc
supersession banner + the new build-status row for Wave 3 #51.
No `docs/reference/rc-entity-naming.md` changes needed — the
`water` subsystem is already in the allowed subsystems list
from the water-tanks Wave 3 #50 slice.

## Changes

- **New** `connections/electronic-valves/connection.yml`
  (tier-b manifest; 17 contract tiles + 15 OpenClaw queries +
  12 OpenClaw summary keys + 4 `tier_warnings` honesty
  markers + vendor-neutral positioning header explaining Path
  A ESPHome valve node + Path B generic relay + the six
  MANDATORY safety interlocks emphasis + the install.config_
  flow = true upstream-truth footnote; mirrors water-tanks
  manifest shape verbatim with electronic-valves substitutions
  + extends the existing `water` subsystem prefix
  (`rc_water_valve_*`) rather than introducing a new `valve`
  subsystem).
- **New** `connections/electronic-valves/__init__.py`
  (`DOMAIN = "electronic_valves"` marker stub; mirrors
  water-tanks `__init__.py` shape with electronic-valves-
  specific docstring describing both paths + the contract
  tile flow + the six safety interlocks + the link to
  docs/recipe.md; explicitly avoids the `config_flow`
  substring per the happijac docstring-rephrasing lesson).
- **New** `connections/electronic-valves/README.md` (folder
  overview; mirrors water-tanks README shape with electronic-
  valves-specific setup recipe + cross-references to water-
  tanks Wave 3 #50 + Victron + heated-floors Wave 3 #44 +
  hvac-basics Wave 3 #49 + smoke-co-gas-sensors Wave 3 #45 +
  mode/automation-builder + bluetooth-wifi-presence Wave 3 #42
  sibling slices).
- **New** `connections/electronic-valves/docs/recipe.md`
  (~822-line howto; required sections §1 "What is Electronic
  valves + auto tank switching in RoamCore?" / §2
  Prerequisites (Path A ESP32 + 3× 12 V / 24 V electrically-
  actuated valves + relay module per valve + valve-position
  feedback GPIO + optional DS18B20 + optional leak sensor;
  Path B Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano
  Switch + DPDT or 2× SPST relay for motorized ball valves +
  HA `template:` valve / switch + valve-position feedback
  binary_sensor + shared water-tanks Wave 3 #50 prerequisites
  + shared Victron prerequisites + shared mode/automation-
  builder prerequisites) / §3 Path A — ESPHome valve node
  (the full ESPHome YAML for the ESP32 with 3× valves (fresh
  inlet on GPIO 13 / grey drain on GPIO 27 / aux tank on
  GPIO 32) + 3× limit-switch position-feedback binary_sensors
  on GPIO 14 / 26 / 33 + the `delayed_off: 500ms` debounce
  filter + the shared DS18B20 + the shared leak sensor) /
  §4 Path B — Generic relay + HA template valve (the Shelly /
  Zooz / Aeotec wiring (12 V / 24 V supply + relay contacts
  into the valve coils) + the HA `template:` switch wiring
  the relay state to the contract tile + the valve-position
  feedback binary_sensor) / §5 Path A vs Path B — operator's
  choice (Path A recommended for ESPHome-friendly installs;
  Path B recommended when the operator already owns a Shelly /
  Zooz / Aeotec relay) / §6 RoamCore contract entities (the
  17 `rc_water_valve_*` tiles + how the upstream switch /
  valve template exposes them + translation helpers needed
  for the derived aggregates like `any_moving` +
  `auto_tank_switch_active` + `leak_detected_lockout` +
  `freeze_risk_lockout` + `low_voltage_lockout`) / §7 Safety
  interlocks (MANDATORY before first use) covering 6
  interlocks (leak detected closes fresh inlet + opens grey
  drain so the leak drips onto the floor rather than into
  the tank + cross-reference `binary_sensor.rc_water_leak_
  detected` from water-tanks Wave 3 #50; freeze risk closes
  all valves + cross-reference `binary_sensor.rc_water_freeze_
  risk` from water-tanks Wave 3 #50; low-voltage lockout
  disables valve opens when SOC < threshold AND shore
  disconnected + cross-reference `sensor.rc_power_battery_
  soc` + `binary_sensor.rc_power_shore_connected` from
  Victron; auto-close grey drain N minutes after open so the
  grey tank doesn't overflow + grey doesn't slosh onto the
  road while driving; mode-aware lockouts via `select.rc_mode`
  from mode/automation-builder — Stealth auto-mutes the
  auto-switch notification, Sleep silently drops warning
  thresholds by 10 %, Boost disables ALL mode-aware lockouts;
  valve stuck-open detector — valve binary_sensor reports
  `valve_position == open` but expected_position is closed
  for > 5 min) + the 7 §8 automations (auto-switch-to-aux-
  tank when fresh < 5 % + auto-switch-back-to-primary when
  fresh > 20 % + auto-close-grey-after-N-min + leak-detected-
  close-fresh-open-grey + freeze-risk-close-all + low-voltage-
  lockout + mode-aware scheduling) + the 8 §9 troubleshooting
  entries (valve not responding coil polarity / driver
  voltage / wiring fault + valve stuck-open mechanical
  obstruction / lime buildup / replace valve + auto-switch
  keeps toggling threshold hysteresis too tight + freeze
  lockout stuck on after charging cross-check Victron SOC +
  Shelly not discovered mDNS / IGMP snooping + ESPHome device
  offline + leak lockout won't release must clear the leak
  first + manual override + grey valve auto-close not firing
  number.rc_water_valve_auto_close_grey_min set too high) /
  §10 privacy (no telemetry beyond local valve state + valve
  position feedback; no vendor cloud / no ESPHome cloud / no
  Shelly cloud / no Zooz / Aeotec cloud) / §11 Promoting to
  tier-a (real 12 V / 24 V valve + safe driver + ESP32 +
  relay + tank-level sensor bench on CI + RoamCore-owned
  operator-wired setup flow walking Path A vs Path B + valve
  GPIO pins + valve coil polarity declaration + integration
  tests asserting a 0 % → 100 % level change triggers the
  right auto-tank-switch + the 6 safety interlocks all flip
  when wired to canned fixture responses)).
- **New** `connections/electronic-valves/tests/test_connection_
  yml.py` (7 manifest-honesty tests: id matches folder / tier-
  b without tier-a markers (with explicit `config_flow`
  substring guard for the __init__.py docstring, mirroring the
  happijac defensive lesson — the test caught no regressions
  in this slice because the docstring was authored from the
  start with the "GUI flow" / "vendor integration's GUI flow"
  rephrasing) / docs recipe published with §1–§11 sections +
  the "MANDATORY before first use" emphasis on the §7 header /
  category `water` matches legacy doc / dashboard tiles follow
  rc naming (17 tiles; vendor name absolute-forbidden —
  shelly / zooz / aeotec / esphome / ads1115 / bts7960 /
  ibom / 12v / 24v / relay / solenoid / latching / motorized
  / bistable / dpdt / spst / sensor_ / binary_sensor_ — but
  lenient on the spec-required tile IDs that contain fresh /
  grey / state / position / moving / active / lockout / min /
  soc / pct / open / close / mode / auto / tank / valve in
  suffix since those are spec-required + lenient on
  `auto_tank_switch_active` which legitimately contains
  `switch` as a generic noun describing the auto-switching
  behavior — mirroring the water-tanks Wave 3 #50 pattern of
  not including `switch_` in the forbidden list) / status
  reflects no real electronic valves with all 4 honesty
  warnings in tier_warnings / safety interlocks are
  documented — defensive guard for the future tier-a
  promotion asserting all 6 safety interlocks (leak detected
  / freeze risk / low-voltage lockout / auto-close grey /
  mode-aware lockouts / valve stuck-open detector) are
  documented in recipe §7 + cross-reference
  `sensor.rc_power_battery_soc` + `binary_sensor.rc_power_
  shore_connected` from Victron + `binary_sensor.rc_water_
  leak_detected` + `binary_sensor.rc_water_freeze_risk` +
  `sensor.rc_water_fresh_level_pct` from water-tanks Wave 3
  #50 + the heated-floors Wave 3 #44 companion + the hvac-
  basics Wave 3 #49 companion + `select.rc_mode` from mode/
  automation-builder + the "MANDATORY before first use"
  emphasis in recipe §7).
- **Modify** `scripts/check.sh` — append a `run_if_present`
  entry for `connections/electronic-valves/tests/test_
  connection_yml.py` directly after the existing water-tanks
  entry (line 117 area).
- **Modify** `docs/catalog/water/electronic-valves-and-auto-
  tank-switch.md` — add a supersession banner at the top
  pointing at the new connection folder (legacy content below
  the banner is preserved for historical context).
- **Modify** `docs/mvp/features-build-status.md` — add a
  "Shipped (repo)" row for Wave 3 #51 mirroring the water-
  tanks row shape (manifest + recipe size + manifest-honesty
  smoke + 17 contract entities + supersession banner + cross-
  references to water-tanks Wave 3 #50 for §6 auto tank
  switching source signals + to Victron for §7.3 low-voltage
  lockout + to heated-floors Wave 3 #44 for §7.2 freeze risk
  cross-reference + to hvac-basics Wave 3 #49 for §7.2 freeze
  risk cross-reference + to smoke-co-gas-sensors Wave 3 #45
  for §7.1 leak detected push notification + to mode/
  automation-builder for §7.5 mode-aware lockouts + PR #54
  link). Also updated the `Last updated:` line from
  `2026-03-31` to `2026-07-30` to reflect the slice date.
- **New** `Cron-handoff/2026-07-30-electronic-valves-
  connection.md` (this file — slice summary with Context /
  Changes / Verification / Rollback).

## Verification

Run locally before pushing:

```bash
cd /home/bernard/clawd/RoamCore
git status                                    # confirm new files (no other diffs)
python3 -m pytest connections/electronic-valves/tests/test_connection_yml.py -v
                                               # expect 7/7 PASS
bash scripts/check.sh --core-only              # expect "✓ all requested smoke checks passed." (exit 0)
python3 -c "import yaml; m=yaml.safe_load(open('connections/electronic-valves/connection.yml')); \
            assert m['id']=='electronic-valves' and m['tier']=='b' and m['category']=='water' \
            and len(m['dashboard']['tiles'])==17" \
                                               # expect VERIFICATION OK
git log --oneline -3                          # confirm new commit on feat/connections/electronic-valves
git push -u origin feat/connections/electronic-valves   # push
gh pr create --base main --head feat/connections/electronic-valves \
  --title "Wave 3 #51: Connection: Electronic valves + auto tank switching (tier-b)" \
  --body "<commit body>"                        # open PR (PR #54)
```

## Rollback

If something goes wrong post-merge:

1. Revert the merge commit on `main` (`git revert -m 1 <merge-sha>`).
2. The legacy `docs/catalog/water/electronic-valves-and-auto-
   tank-switch.md` already carries a supersession banner pointing
   at `connections/electronic-valves/`, so even post-revert
   operators have a pointer to the previous tier-c placeholder.
3. Delete the `feat/connections/electronic-valves` branch
   (`git branch -d feat/connections/electronic-valves` + `git push
   origin :feat/connections/electronic-valves`).
4. The recipe + manifest + tests live entirely under
   `connections/electronic-valves/` — no other shared paths are
   touched besides the `scripts/check.sh` wire-up + the legacy-doc
   supersession banner + the build-status row. Each of those is
   independently revertable.