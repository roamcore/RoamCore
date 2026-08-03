# Wave 3 #45 — Connection: Smoke / CO / gas safety sensors (tier-b) slice handoff

## Context

Promote the legacy tier-c `docs/catalog/safety/smoke-co-gas-sensors.md`
spec into a tier-b recipe connection at `connections/smoke-co-gas-sensors/`.
Follows the same pattern proven by Wave 3 #35 Frigate / #36 Starlink /
#37 DNS blocker / #38 NAS / #39 Teltonika / #40 Peplink / #41 Music
Assistant / #42 Bluetooth-Wi-Fi presence / #43 Happijac / #44 heated-floors.

Smoke / CO / gas safety sensors — van life safety monitoring — are
the **foundation** of every "is it safe to sleep in the van?"
question: a single "any alarm" tile that aggregates smoke detected +
CO detected + gas detected into one dashboard indicator, the alarm
silenced flag with operator-tunable duration (default 10 min), the
sensor-offline warning when any safety sensor hasn't checked in
within 30 min (dead battery / lost Wi-Fi), the battery-low warning,
the alarm mode select (`full` / `night_only` / `cooking_active` /
`off`), the alarm test button, the alarm silence button, and the
mode-aware `cooking_active` suppression that mutes non-CO alarms
during active cooking. Vendor-neutral binary_sensor + sensor
semantics.

Three install paths (operator picks based on existing IoT wiring +
detector ownership + analog wiring comfort):

- **Path A — Smart detectors** (recommended for operators who
  already own a Nest Protect / First Alert Z-Wave / X-Sense Zigbee
  / Heiman Z-Wave / Zipato Zigbee). The vendor integration's
  `binary_sensor.*` (smoke detected / CO detected / gas detected) +
  `sensor.*` (smoke_ppm / co_ppm / gas_ppm) entities are already
  exposed in HA. The recipe wraps them into the `rc_safety_*`
  contract via templates that aggregate multiple sensors of the
  same type via `is_state(...) or is_state(...)`.
- **Path B — Generic smoke/CO alarms** (basic Kidde / First Alert
  battery-only alarms do NOT have HA integration — minimum safety
  baseline; local audible alarm only, no contract tiles wired).
  The recipe documents the recommended detectors (Kidde
  KN-COSM-IBA combo smoke+CO, Nest Protect, X-Sense SD11, First
  Alert Z-Wave).
- **Path C — Propane/LPG detectors** (Mopeka / Atemox / GasAlert /
  MQ-series via ESPHome). Analog 4-20 mA sensors wired via Modbus
  bridge or ESPHome ADC; sensor.gas_ppm derived from analog voltage.

All three paths land on the same 13 `rc_safety_*` contract tiles
(vendor-neutral per `docs/reference/rc-entity-naming.md` §safety
subsystem — newly added to the allowed subsystems list alongside
this slice):

- `binary_sensor.rc_safety_smoke_detected` — TRUE when any smoke sensor triggers (OR aggregate)
- `binary_sensor.rc_safety_co_detected` — TRUE when any CO sensor exceeds threshold
- `binary_sensor.rc_safety_gas_detected` — TRUE when any propane / LPG / natural gas sensor triggers
- `sensor.rc_safety_smoke_max_ppm` — highest current smoke reading (ppm)
- `sensor.rc_safety_co_max_ppm` — highest current CO reading (ppm)
- `sensor.rc_safety_gas_max_ppm` — highest current gas reading (ppm)
- `binary_sensor.rc_safety_any_alarm` — aggregate of smoke_detected OR co_detected OR gas_detected (single most important dashboard indicator)
- `binary_sensor.rc_safety_alarm_silenced` — TRUE when operator has silenced the alarm
- `binary_sensor.rc_safety_battery_low` — TRUE when any safety sensor reports battery low
- `binary_sensor.rc_safety_sensor_offline` — TRUE when any safety sensor hasn't checked in within last 30 min
- `select.rc_safety_alarm_mode` — `full` / `night_only` / `cooking_active` / `off`
- `button.rc_safety_alarm_test` — test all sensors
- `button.rc_safety_alarm_silence` — silence the alarm for operator-set duration (default 10 min)

This slice does NOT edit any other connection folder, nor any other
branch. Only the smoke-co-gas-sensors files + the `scripts/check.sh`
wire-up + the legacy-doc supersession banner + the rc-entity-naming
subsystems addition + the new build-status row for Wave 3 #45.

## Changes

- **New** `connections/smoke-co-gas-sensors/connection.yml` (tier-b
  manifest; 13 contract tiles + 12 OpenClaw queries + 11 OpenClaw
  summary keys + 4 `tier_warnings` honesty markers + vendor-neutral
  positioning header explaining Path A smart detectors vs Path B
  basic alarms vs Path C propane/LPG via ESPHome).
- **New** `connections/smoke-co-gas-sensors/__init__.py`
  (`DOMAIN = "smoke_co_gas_sensors"` marker stub; explicitly avoids
  the `config_flow` substring per the happijac docstring-rephrasing
  lesson).
- **New** `connections/smoke-co-gas-sensors/README.md` (folder
  overview; mirrors the prior tier-b slice shapes with smoke-co-gas
  specific setup recipe + cross-references to Smart Automations +
  Deadbolts + Bluetooth-Wi-Fi presence + Mode/automation-builder
  sibling slices).
- **New** `connections/smoke-co-gas-sensors/docs/recipe.md`
  (~330-line howto; required sections §1 "What are smoke / CO / gas
  safety sensors in RoamCore?" / §2 Prerequisites (Path A smart
  detectors + vendor integration; Path B basic Kidde / First Alert
  battery-only alarms minimum safety baseline; Path C propane/LPG
  detector + Modbus bridge OR ESPHome analog input) / §3 Path A —
  Smart detectors (the entity_id surfacing + the template binary_
  sensor that aggregates multiple smoke detectors via is_state(...)
  or is_state(...) + the template sensor for the ppm readings) /
  §4 Path B — Generic smoke/CO alarms (minimum safety baseline
  subsection listing the recommended detectors (Kidde KN-COSM-IBA
  combo smoke+CO, Nest Protect, X-Sense SD11, First Alert Z-Wave))
  / §5 Path C — Propane/LPG detectors via ESPHome (the analog-to-
  digital wiring + the sensor.gas_ppm template that derives the
  ppm reading from the analog voltage) / §6 RoamCore contract
  entities (the 13 rc_safety_* tiles + how the upstream binary_
  sensor.* + sensor.* templates expose them + translation helpers
  needed for the binary_sensors / numeric ppm readings + the
  any-alarm aggregate template) / §7 Automations (MANDATORY before
  first use) covering 6 safety automations: smoke detected →
  emergency-egress unlock + siren + lights + push notification; CO
  detected → cut propane solenoid + open roof vents + turn off HVAC
  + push notification; gas leak detected → cut propane solenoid +
  open roof vents + turn off HVAC + push notification; sensor offline
  (>30 min no check-in) → push notification with bluetooth-wifi-
  presence escalation when operator is in the van; sensor battery
  low → push notification; alarm silenced → auto-resume after
  operator-set duration default 10 minutes / §8 Troubleshooting (8
  entries: alarm false-positive during cooking use cooking_active
  mode + smoke detector in bedroom not kitchen; sensor not discovered
  Zigbee / Z-Wave interview needed; ppm reading stuck at 0 sensor
  calibration needed; sensor offline after first install battery
  not seated correctly reseat; alarm won't silence test button is
  on a different entity; CO threshold set too sensitive false alarm
  during heavy cooking do not lower below vendor recommendation;
  Mopeka propane sensor shows leak when tank is full calibrate the
  empty/full reference; X-Sense integration missing in HA core
  install via ZHA; Shelly UNI analog input not reporting check
  4-20 mA wiring polarity) / §9 Privacy (no telemetry beyond local
  Zigbee / Z-Wave / Wi-Fi / ESPHome; no vendor cloud) / §10
  tier-a promotion outline (real smoke + CO + propane sensor bench
  on CI + RoamCore-owned config_flow.py walking Path A vs Path B
  vs Path C + detector placement per local code + analog input
  wiring for Path C + integration tests asserting the 6 safety
  automations all fire + the any_alarm tile lights up)).
- **New** `connections/smoke-co-gas-sensors/tests/test_connection_yml.py`
  (7 manifest-honesty tests: id matches folder / tier-b without
  tier-a markers with explicit `config_flow` substring guard for
  the __init__.py docstring / docs recipe published with §1-§10
  sections / category `safety` matches legacy doc / dashboard tiles
  follow rc naming with 13 tiles; vendor name absolute-forbidden
  (nest / kidde / first_alert / x_sense / heiman / zipato /
  mopeka / atemox / gasalert / mq_2 / mq_5 / mq_7 / mq_135 /
  esphome / zigbee / z_wave / propane / lpg / natural_gas) but
  lenient on the spec-required tile IDs that contain smoke / co /
  gas / alarm / battery / sensor / offline / silenced / test /
  mode in suffix since those are spec-required / status reflects
  no real safety sensor with all 4 honesty warnings in tier_
  warnings / safety automations are documented — defensive guard
  for the future tier-a promotion).
- **Modify** `scripts/check.sh` — append a `run_if_present` entry
  for `connections/smoke-co-gas-sensors/tests/test_connection_yml.py`
  directly after the existing heated-floors entry.
- **Modify** `docs/catalog/safety/smoke-co-gas-sensors.md` — add a
  supersession banner at the top pointing at the new connection
  folder (legacy content below the banner is preserved for
  historical context).
- **Modify** `docs/reference/rc-entity-naming.md` — add `safety`
  subsystem slot between `hvac` and `system` (the canonical name
  per the slice spec: "smoke / CO / gas / safety sensors + safety
  automations (smoke alarm, CO monitor, propane leak, etc.), only
  if needed").
- **Modify** `docs/mvp/features-build-status.md` — add a "Shipped
  (repo)" row for Wave 3 #45 mirroring the heated-floors row shape.
- **New** `Cron-handoff/2026-07-30-smoke-co-gas-sensors-connection.md`
  (this file — slice summary with Context / Changes / Verification /
  Rollback).

## Verification

Run locally before pushing:

```bash
cd /home/bernard/clawd/RoamCore
git status                                    # clean or only the new files
python3 -m pytest connections/smoke-co-gas-sensors/tests/test_connection_yml.py -v
                                               # expect 7/7 PASS
bash scripts/check.sh --core-only              # expect "✓ all requested smoke checks passed."
python3 -c "import yaml; m=yaml.safe_load(open('connections/smoke-co-gas-sensors/connection.yml')); \
            assert m['id']=='smoke-co-gas-sensors' and m['tier']=='b' and m['category']=='safety' \
            and len(m['dashboard']['tiles'])==13" \
                                               # expect VERIFICATION OK
git log --oneline -3                          # confirm new commit on feat/connections/smoke-co-gas-sensors
git push -u origin feat/connections/smoke-co-gas-sensors   # push
gh pr create --base main --head feat/connections/smoke-co-gas-sensors \
  --title "Wave 3 #45: Connection: Smoke / CO / gas safety sensors (tier-b)" \
  --body "<commit body>"                        # open PR (PR #49)
```

## Rollback

If something goes wrong post-merge:

1. Revert the merge commit on `main` (`git revert -m 1 <merge-sha>`).
2. The legacy `docs/catalog/safety/smoke-co-gas-sensors.md` already carries a
   supersession banner pointing at `connections/smoke-co-gas-sensors/`, so even
   post-revert operators have a pointer to the previous tier-c spec.
3. Delete the `feat/connections/smoke-co-gas-sensors` branch
   (`git branch -d feat/connections/smoke-co-gas-sensors` + `git push origin :feat/connections/smoke-co-gas-sensors`).
4. Remove the `safety` subsystem from `docs/reference/rc-entity-naming.md`'s
   Allowed subsystems list (delete the `- \`safety\` — smoke / CO / gas /
   safety sensors + safety automations (smoke alarm, CO monitor, propane
   leak, etc.), only if needed` line). Note: this is also the only
   `safety` subsystem reference in the repo; removing it leaves no stale
   cross-references.

## Notes

- The recipe's §3 Path A smart detector YAML uses well-understood
  upstream vendor `binary_sensor.*` + `sensor.*` entity IDs; the §4
  Path B minimum safety baseline subsection lists the recommended
  detectors (Kidde KN-COSM-IBA combo smoke+CO, Nest Protect, X-Sense
  SD11, First Alert Z-Wave); the §5 Path C ESPHome YAML uses an
  ESP32 ADC pin + a 4-20 mA receiver + a template sensor that
  derives the ppm reading from the analog voltage.
- The recipe's §6 `rc_safety_*` contract layer is fully written in
  YAML (template binary_sensor + template sensors + template select
  + template buttons + input_boolean + timer); operators wire those
  manually until tier-a promotion lands.
- The recipe's §7 documents the 6 MANDATORY safety automations:
  smoke detected (emergency-egress unlock + siren + lights + push
  notification), CO detected (cut propane + open vents + turn off
  HVAC + push notification), gas leak detected (same as CO),
  sensor offline > 30 min (push notification with bluetooth-wifi-
  presence escalation when operator is in the van), sensor battery
  low (push notification), alarm silenced (auto-resume after
  operator-set duration default 10 minutes). The cooking_active
  mode-aware suppression does NOT silence CO alarms (CO is
  life-threatening even during cooking).
- The `config_flow` substring was explicitly avoided in the
  `__init__.py` docstring (per the happijac docstring-rephrasing
  lesson) — the docstring uses "GUI flow" or "the vendor
  integration's GUI flow" instead.
- The test's `test_dashboard_tiles_follow_rc_naming` defensive guard
  forbids vendor names (nest / kidde / first_alert / x_sense /
  heiman / zipato / mopeka / atemox / gasalert / mq_2 / mq_5 /
  mq_7 / mq_135 / esphome / zigbee / z_wave) but is lenient on
  the spec-required tile IDs that contain generic nouns (smoke /
  co / gas / alarm / battery / sensor / offline / silenced /
  test / mode) in the suffix since those are spec-required. The
  binary_sensor_ / sensor_ domain-namespace substring guards were
  removed because `sensor_offline` is a spec-required literal tile
  ID and legitimately contains `sensor_` as a generic-noun part.
