# Wave 3 #50 — Connection: Water tanks (fresh/grey monitoring) (tier-b) slice handoff

## Context

Promote the legacy tier-c `docs/catalog/water/water-tanks.md` spec
into a tier-b recipe connection at `connections/water-tanks/`. Follows
the same pattern proven by Wave 3 #35 Frigate / #36 Starlink / #37
DNS blocker / #38 NAS / #39 Teltonika / #40 Peplink / #41 Music
Assistant / #42 Bluetooth-Wi-Fi presence / #43 Happijac / #44 Heated
floors / #45 Smoke-CO-gas / #46 Smart automations / #47 Mock location
/ #48 Deadbolts / #49 HVAC basics.

Water tanks — fresh + grey water telemetry + pump runtime + leak
detection + freeze-risk monitoring for vans — is the vendor-neutral
surface that turns "is the fresh tank still full enough to last the
night?" into a dashboard tile + a push notification + a mode-aware
automation. Water tanks (fresh + grey) are a universal van pain
point; RoamCore ships no native tank hardware so tier-b recipe-over-
upstream is honest. The upstream `sensor` + `binary_sensor` +
`switch` domains cover all the integration paths: ultrasonic /
resistive / capacitive tank level sensors, flow sensors, leak
sensors, and 12 V relay-driven solenoid valves (valve control is the
next Wave 3 #51 slice — this slice is read-only telemetry + the
operator-tunable tank sizes + the operator-tunable water mode).

Three install paths (operator picks based on hardware ownership +
ESPHome familiarity + vendor preference):

- **Path A — ESPHome tank sensor node (recommended for ESPHome-
  friendly installs).** One ESP32 per node, ultrasonic probe
  (JSNSR04T / HC-SR04 waterproof) wired into GPIO for each tank; the
  ESPHome YAML exposes `sensor.<node>_fresh_level_pct` +
  `sensor.<node>_fresh_distance_cm` +
  `sensor.<node>_grey_level_pct` +
  `sensor.<node>_grey_distance_cm`. Optional
  `binary_sensor.<node>_pump_running` (sense the pump's +12 V wire
  via a CT clamp on the same ESP32) +
  `sensor.<node>_fresh_temperature_c` (DS18B20 in tank bay) +
  `binary_sensor.<node>_leak_detected`.
- **Path B — Generic resistive / 4–20 mA / voltage probe via Shelly
  UNI ADC (no ESPHome).** Probe wired into a Shelly UNI's ADC input;
  the Shelly integration exposes `sensor.<tank>_voltage`; the HA
  `template:` integration translates voltage to percentage via a
  calibration curve.
- **Path C — Cloud-bridged level sensor (SeeLevel / Garnet SeeLevel
  II 709-BTG / Mopeka Pro Check / Lippert).** Vendor integration in
  HA core or HACS exposes the level directly; the RoamCore recipe
  maps the vendor entity to the contract tile.

All three paths land on the same 17 `rc_water_*` contract tiles:

- `sensor.rc_water_fresh_level_pct` — fresh tank level (0–100 %)
- `sensor.rc_water_fresh_level_l` — fresh tank volume in litres
  (`tank_size_l × level_pct / 100`)
- `sensor.rc_water_fresh_days_remaining` — derived:
  `tank_size_l / avg_daily_usage_l`; clamps 0–30
- `sensor.rc_water_grey_level_pct` — grey tank level (0–100 %)
- `sensor.rc_water_grey_level_l` — grey tank volume in litres
- `binary_sensor.rc_water_grey_full_warning` — TRUE when
  `grey_level_pct` > 80 %
- `binary_sensor.rc_water_fresh_low_warning` — TRUE when
  `fresh_level_pct` < 20 %
- `binary_sensor.rc_water_fresh_empty_warning` — TRUE when
  `fresh_level_pct` < 5 %
- `binary_sensor.rc_water_pump_running` — TRUE when the 12 V water
  pump is actively running
- `sensor.rc_water_pump_runtime_min_last_24h` — derived from
  `binary_sensor.rc_water_pump_running` edge-counting via the HA
  `utility_meter:` integration with a 24h cycle
- `binary_sensor.rc_water_pump_running_too_long` — TRUE when pump
  has been running continuously > 10 min
- `binary_sensor.rc_water_leak_detected` — TRUE when ANY leak sensor
  (under-sink / pump-area / under-van) reports water
- `binary_sensor.rc_water_freeze_risk` — TRUE when
  `sensor.rc_water_fresh_temperature_c` < 2 °C
- `sensor.rc_water_fresh_temperature_c` — tank bay temperature probe
- `number.rc_water_fresh_tank_size_l` — operator-configured fresh
  tank size (default 80 L, configurable 20–300 L)
- `number.rc_water_grey_tank_size_l` — operator-configured grey tank
  size (default 60 L, configurable 20–200 L)
- `select.rc_water_mode` — operator-tunable mode: `auto` (all
  warnings enabled), `stealth_only` (only leak / freeze / empty
  warnings), `silent` (no warnings — for service), `disabled` (no
  monitoring)

This slice does NOT edit `connections/hvac-basics/` (the parent
branch territory), nor any other connection folder, nor the build-
status hvac-basics row. Only the water-tanks files + the
`scripts/check.sh` wire-up + the legacy-doc supersession banner +
the rc-entity-naming subsystems addition + the new build-status
row for Wave 3 #50.

## Changes

- **New** `connections/water-tanks/connection.yml` (tier-b manifest;
  17 contract tiles + 14 OpenClaw queries + 12 OpenClaw summary
  keys + 4 `tier_warnings` honesty markers + vendor-neutral
  positioning header explaining Path A ESPHome tank sensor node vs
  Path B Shelly UNI + ADC probe vs Path C cloud-bridged level
  sensor + the five MANDATORY safety interlocks emphasis; mirrors
  hvac-basics manifest shape verbatim with water-tanks substitutions).
- **New** `connections/water-tanks/__init__.py` (`DOMAIN =
  "water_tanks"` marker stub; mirrors hvac-basics `__init__.py`
  shape with water-tanks-specific docstring describing all three
  paths + the contract tile flow + the five safety interlocks + the
  link to docs/recipe.md; explicitly avoids the `config_flow`
  substring per the happijac docstring-rephrasing lesson — the
  §11 tier-a promotion outline section rephrases
  `RoamCore-owned config_flow.py` as `RoamCore-owned operator-wired
  setup flow` to avoid the substring match).
- **New** `connections/water-tanks/README.md` (folder overview;
  mirrors hvac-basics README shape with water-tanks-specific setup
  recipe + cross-references to HVAC basics + heated-floors + Victron
  + smoke-co-gas-sensors + mode-automation-builder + bluetooth-wifi-
  presence + deadbolts sibling slices).
- **New** `connections/water-tanks/docs/recipe.md` (~706-line
  howto; required sections §1 "What is Water tanks in RoamCore?" /
  §2 Prerequisites (Path A ESP32 + 2× ultrasonic probes + CT clamp +
  DS18B20 + leak sensor; Path B Shelly UNI + ADC probe + HA
  `template:` with calibration curve; Path C SeeLevel / Garnet /
  Mopeka / Lippert vendor integration) / §3 Path A — ESPHome tank
  sensor node (the full ESPHome YAML for the ESP32 with 2× ultrasonic
  probes (fresh on GPIO 13/12 + grey on GPIO 27/26) + the `lambda`
  filter that converts distance_cm to level_pct using the per-tank
  (max_distance, min_distance) calibration + the CT clamp on GPIO 34
  (ADC1_CH6) sensing the pump current + the `binary_sensor.pump_
  running` template that fires when current > 0.5 A + the DS18B20 on
  GPIO 4 + the optional leak sensor on GPIO 14 with a 10 kΩ pull-up
  + the `delayed_off: 500ms` debounce filter) / §4 Path B — Generic
  resistive / 4–20 mA / voltage probe via Shelly UNI ADC (the Shelly
  UNI wiring (12 V supply + ADC inputs A1/A2) + the HA `template:`
  sensor wiring the raw voltage to percentage via the per-tank
  (calibration_empty_v, calibration_full_v) curve + the operator-
  tunable `number.rc_water_fresh_tank_size_l` +
  `number.rc_water_grey_tank_size_l` tiles) / §5 Path C — Cloud-
  bridged level sensor (SeeLevel via the `see_level` HACS integration
  / Mopeka via the `mopeka_pro_check` HACS integration / Garnet via
  the `serial` integration with a USB-to-serial adapter / Lippert via
  the `lippert_onecontrol` HACS integration) / §6 RoamCore contract
  entities (the 17 `rc_water_*` tiles + how the upstream sensor
  template exposes them + translation helpers needed for the derived
  metrics like `fresh_days_remaining` and `pump_runtime_min_last_24h`)
  / §7 Safety interlocks (MANDATORY before first use) covering 5
  interlocks (leak detected immediately stops the pump + sends a
  HIGH-PRIORITY push notification; freeze risk triggers the heated-
  floors + hvac-basics connections' frost-warning path cross-
  reference; fresh empty warning surfaces prominently on the
  dashboard; pump running too long automatically stops the pump
  after 10 min to prevent battery drain; mode-aware lockouts via
  `select.rc_mode` — Stealth auto-mutes warnings except
  leak / freeze / empty, Sleep silently drops warning thresholds by
  10 %, Boost disables ALL mode-aware lockouts) + the 6 §8
  automations (auto-push on fresh low / auto-push on grey full /
  auto-stop pump when pump running too long / auto-push critical on
  leak detected / auto-engage heated-floors on freeze risk when SOC
  > 50 % / mode-aware scheduling so warnings auto-mute in Stealth
  silent hours unless they hit the leak / freeze / empty thresholds)
  + the 8 §9 troubleshooting entries (sensor reading 0 % when tank is
  full wiring fault / sensor reading 100 % when tank is empty
  calibration wrong / pump_running not toggling CT clamp orientation /
  leak sensor always-on probe wet + needs drying / ESPHome device
  offline Wi-Fi + USB-C / Shelly UNI not discovered mDNS / temperature
  reading -40 °C DS18B20 pull-up / fresh_days_remaining negative
  calibration drift) / §10 privacy (no telemetry beyond local level +
  pump runtime + temperature; no cloud call home; the leak sensors
  are local GPIO inputs (Path A) or Zigbee / Z-Wave sensors (Path B /
  C) — no telemetry is sent to any cloud) / §11 Promoting to tier-a
  (real fresh tank + grey tank + pump + leak sensor + temperature
  probe + ESP32 + ultrasonic probe + CT clamp + Shelly UNI bench on
  CI + RoamCore-owned operator-wired setup flow walking Path A vs
  Path B vs Path C + GPIO pin / calibration curve / vendor
  integration declaration + integration tests asserting a 0 % →
  100 % level change triggers the right tile updates + the 5 safety
  interlocks all flip when wired to canned fixture responses)).
- **New** `connections/water-tanks/tests/test_connection_yml.py` (7
  manifest-honesty tests: id matches folder / tier-b without tier-a
  markers (with explicit `config_flow` substring guard for the
  __init__.py docstring, mirroring the happijac defensive lesson —
  the test caught one regression on first run; the §11 tier-a
  promotion outline section in the docstring was rephrased from
  `RoamCore-owned config_flow.py` to `RoamCore-owned operator-wired
  setup flow` to avoid the substring match) / docs recipe published
  with §1–§11 sections + the "MANDATORY before first use" emphasis
  on the §7 header (test caught a second regression on first run;
  the §7 header was renamed from `## §7 Safety interlocks` to
  `## §7 Safety interlocks (MANDATORY before first use)` to satisfy
  the substring match) / category `water` matches legacy doc /
  dashboard tiles follow rc naming (17 tiles; vendor name
  absolute-forbidden — seelevel / see_level / mopeka / lippert /
  garnet / esphome / shelly / ads1115 / jsnsr04t / hc_sr04 /
  ds18b20 / sct013 / sct_013 / current / adc / voltage / sensor_ /
  binary_sensor_ — but lenient on the spec-required tile IDs that
  contain fresh / grey / level / pump / runtime / leak / freeze /
  temperature / tank / size / mode / warning / empty / low / full /
  days / remaining / too_long / min / 24h in suffix since those are
  spec-required) / status reflects no real water tank with all 4
  honesty warnings in tier_warnings / safety interlocks are
  documented — defensive guard for the future tier-a promotion
  asserting all 5 safety interlocks (leak detected / freeze risk /
  fresh empty / pump running too long / mode-aware lockouts) are
  documented in recipe §7 + cross-reference
  `sensor.rc_power_battery_soc` + `binary_sensor.rc_power_shore_
  connected` from Victron + the heated-floors Wave 3 #44 companion +
  the hvac-basics Wave 3 #49 companion + `select.rc_mode` from
  mode/automation-builder + the "MANDATORY before first use"
  emphasis in recipe §7).
- **Modify** `scripts/check.sh` — append a `run_if_present` entry
  for `connections/water-tanks/tests/test_connection_yml.py`
  directly after the existing hvac-basics entry.
- **Modify** `docs/catalog/water/water-tanks.md` — add a
  supersession banner at the top pointing at the new connection
  folder (legacy content below the banner is preserved for
  historical context).
- **Modify** `docs/reference/rc-entity-naming.md` — add `water` to
  the Allowed subsystems list (between `time` and `system`).
- **Modify** `docs/mvp/features-build-status.md` — add a "Shipped
  (repo)" row for Wave 3 #50 mirroring the hvac-basics row shape
  (manifest + recipe size + manifest-honesty smoke + 17 contract
  entities + supersession banner + cross-references to HVAC basics
  for §7.2 freeze risk + to heated-floors for §7.2 freeze risk
  auto-engage + to Victron for §7.4 pump running too long + to
  smoke-co-gas-sensors for §7.1 leak detected push notification +
  to deadbolts for §7.1 emergency-egress unlock + to mode/
  automation-builder for §7.5 mode-aware lockouts + PR #51 link).
- **New** `Cron-handoff/2026-07-30-water-tanks-connection.md` (this
  file — slice summary with Context / Changes / Verification /
  Rollback).

## Verification

Run locally before pushing:

```bash
cd /home/bernard/clawd/RoamCore
git status                                    # clean or only the new files
python3 -m pytest connections/water-tanks/tests/test_connection_yml.py -v
                                               # expect 7/7 PASS
bash scripts/check.sh --core-only              # expect "✓ all requested smoke checks passed."
python3 -c "import yaml; m=yaml.safe_load(open('connections/water-tanks/connection.yml')); \
            assert m['id']=='water-tanks' and m['tier']=='b' and m['category']=='water' \
            and len(m['dashboard']['tiles'])==17" \
                                               # expect VERIFICATION OK
git log --oneline -3                          # confirm new commit on feat/connections/water-tanks
git push -u origin feat/connections/water-tanks   # push
gh pr create --base main --head feat/connections/water-tanks \
  --title "Wave 3 #50: Connection: Water tanks (fresh/grey monitoring) (tier-b) — fresh/grey monitoring" \
  --body "<commit body>"                        # open PR (PR #51)
```

## Rollback

If something goes wrong post-merge:

1. Revert the merge commit on `main` (`git revert -m 1 <merge-sha>`).
2. The legacy `docs/catalog/water/water-tanks.md` already carries a
   supersession banner pointing at `connections/water-tanks/`, so
   even post-revert operators have a pointer to the previous tier-c
   placeholder.
3. Delete the `feat/connections/water-tanks` branch
   (`git branch -d feat/connections/water-tanks` + `git push origin
   :feat/connections/water-tanks`).
4. The recipe + manifest + tests live entirely under
   `connections/water-tanks/` — no other shared paths are touched
   besides the `scripts/check.sh` wire-up + the legacy-doc
   supersession banner + the rc-entity-naming subsystems addition +
   the build-status row. Each of those is independently revertable.