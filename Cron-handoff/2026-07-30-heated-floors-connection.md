# Wave 3 #44 — Connection: Heated floors + engine pre-heat (tier-b) slice handoff

## Context

Promote the legacy tier-c `docs/catalog/hvac/heated-floors-and-engine-preheat.md` spec
into a tier-b recipe connection at `connections/heated-floors/`. Follows
the same pattern proven by Wave 3 #35 Frigate / #36 Starlink / #37
DNS blocker / #38 NAS / #39 Teltonika / #40 Peplink / #41 Music
Assistant / #42 Bluetooth-Wi-Fi presence / #43 Happijac.

Heated floors + optional engine pre-heat — cold-weather comfort controls for vans — are the **foundation** of every "Warm up" automation in winter van life: a single "warm up the van" command that orchestrates floor heat + interior temp + engine preheat together, shore-power-aware throttling, mode-aware Stealth/Sleep/Boost lockouts, presence-aware pre-warm when the operator's phone reconnects to the LAN, low-voltage lockout when SOC < 20 % AND shore is disconnected (heated floor + engine preheat together can pull 10–30 A sustained), frost-protection automation. Vendor-neutral climate + switch + sensor semantics.

Three install paths (operator picks based on existing IoT wiring + thermostat preference + engine preheat hardware ownership):

- **Path A — Smart thermostat** (recommended for operators who already own a Mysa / Shelly H&T / generic-Zigbee thermostat; vendor integration's `climate.*` entity is already exposed in HA; the recipe wraps the entity_id into the `rc_hvac_*` contract via templates that derive "Heating" / "Maintaining" / "Off" from the climate's `hvac_action` attribute).
- **Path B — Generic thermostat** (no smart thermostat; just a temperature probe + a relay-driven heater; HA core `generic_thermostat:` wraps `sensor.interior_temp` + `switch.heater_relay` into `climate.floor_heater` with `min_temp` / `max_temp` / `cold_tolerance` / `hot_tolerance` / `keep_alive`).
- **Path C — Optional engine pre-heat** (Webasto / Espar / Eberspächer / DIY coolant-loop via a relay OR a CAN bus gateway for higher-end Thermo Top Evo / Hydronic S3; recipe derives "is the engine preheat actually producing heat" from the cabin temp trend — when the switch is on AND cabin temp is rising over a 5-minute window → active).

All three paths land on the same 13 `rc_hvac_*` contract tiles:

- `climate.rc_hvac_floor_thermostat` — vendor-neutral climate wrapper (off / heat / auto modes + setpoint control)
- `sensor.rc_hvac_floor_current_temp` — current floor temperature (Path A: from upstream climate's `current_temperature`; Path B: from `sensor.interior_temp` probe)
- `sensor.rc_hvac_interior_temp` — interior air temperature (separate from floor probe)
- `binary_sensor.rc_hvac_floor_heating_active` — TRUE when climate's `hvac_action == "heating"`
- `binary_sensor.rc_hvac_floor_maintaining` — TRUE when climate's `hvac_action == "idle"` AND setpoint > current_temp
- `binary_sensor.rc_hvac_floor_off` — TRUE when climate's `hvac_action == "off"` OR state == "off"
- `switch.rc_hvac_floor_heater` — explicit heater on/off affordance (Path B relay-driven; Path A uses climate `turn_on` / `turn_off`)
- `number.rc_hvac_floor_setpoint` — numeric setpoint control (delegates to `climate.set_temperature`)
- `select.rc_hvac_floor_mode` — `auto` / `eco` / `boost` / `off` (operator-tunable lockout mode)
- `binary_sensor.rc_hvac_floor_low_voltage_lockout` — TRUE when `sensor.rc_power_battery_soc < 20 %` AND `binary_sensor.rc_power_shore_connected == off` (cross-references Victron `sensor.rc_power_battery_soc` + `binary_sensor.rc_power_shore_connected`)
- `switch.rc_hvac_engine_preheat` — optional Path C engine preheat on/off affordance
- `binary_sensor.rc_hvac_engine_preheat_active` — TRUE when engine preheat switch is on AND cabin temp is rising over a 5-minute window
- `sensor.rc_hvac_engine_preheat_runtime_min` — daily runtime tracker (utility_meter integration)

This slice does NOT edit `connections/happijac/` (the parent branch territory), nor any other connection folder, nor the build-status happijac row. Only the heated-floors files + the `scripts/check.sh` wire-up + the legacy-doc supersession banner + the rc-entity-naming subsystems addition + the new build-status row for Wave 3 #44.

## Changes

- **New** `connections/heated-floors/connection.yml` (tier-b manifest; 13 contract tiles + 14 OpenClaw queries + 9 OpenClaw summary keys + 5 `tier_warnings` honesty markers + vendor-neutral positioning header explaining Path A smart thermostat vs Path B `generic_thermostat:` vs Path C optional engine preheat + the five MANDATORY safety interlocks emphasis; mirrors happijac manifest shape verbatim with heated-floors substitutions).
- **New** `connections/heated-floors/__init__.py` (`DOMAIN = "heated_floors"` marker stub; mirrors happijac `__init__.py` shape with heated-floors-specific docstring describing all three paths + the contract tile flow + the five safety interlocks + the link to docs/recipe.md; explicitly avoids the `config_flow` substring per the happijac docstring-rephrasing lesson).
- **New** `connections/heated-floors/README.md` (folder overview; mirrors happijac README shape with heated-floors-specific setup recipe + cross-references to Victron + bluetooth-wifi-presence + happijac sibling slices).
- **New** `connections/heated-floors/docs/recipe.md` (~370-line howto; required sections §1 "What are heated floors + engine pre-heat in RoamCore?" / §2 Prerequisites (Path A smart thermostat + vendor integration; Path B temperature probe + relay-driven heater + HA core `generic_thermostat:` with `min_temp` / `max_temp` / `cold_tolerance` / `hot_tolerance` / `keep_alive`; Path C optional engine preheat hardware + relay or CAN bus gateway) / §3 Path A — Smart thermostat (the entity_id surfacing + the `set_hvac_mode` / `set_temperature` service calls + the template sensor deriving "Heating" / "Maintaining" / "Off" from the climate's `hvac_action` attribute + the template climate wrapper exposing `climate.rc_hvac_floor_thermostat` + the `number.rc_hvac_floor_setpoint` delegating to `climate.set_temperature`) / §4 Path B — Generic thermostat (full HA core `generic_thermostat:` YAML wrapping `sensor.interior_temp` + `switch.heater_relay` with `keep_alive: { minutes: 3 }` MANDATORY) / §5 Path C — Optional engine pre-heat (the `switch.engine_preheat` entity + the `binary_sensor.engine_preheat_active` template that derives "is the engine preheat actually producing heat" from the cabin temp trend + the `utility_meter` for the daily runtime tracker) / §6 RoamCore contract entities (the 13 `rc_hvac_*` tiles + how the upstream `climate.*` + `switch.*` + `sensor.*` templates expose them + translation helpers needed for the binary_sensors / numeric setpoint / mode select / low-voltage lockout template) / §7 Automations (MANDATORY before first use) covering 5 safety interlocks (low-voltage lockout via Victron cross-reference / shore-power-aware throttling / mode-aware Stealth/Sleep/Boost / presence-aware pre-warm using bluetooth-wifi-presence `binary_sensor.rc_presence_operator_phone_arrived` / frost-protection automation using happijac `select.rc_bed_lift_mode`) + the "Warm up" scene + the engine pre-heat schedule / §8 Troubleshooting (9 entries: floor heater not turning on relay polarity + coil voltage, heater stuck on relay welded shut, temperature probe reading -40 °C probe disconnected, setpoint not sticking template race keep_alive, floor heater cycling rapidly cold_tolerance too tight, engine preheat switch toggles but engine doesn't warm CAN bus gateway not connected, engine preheat brief but runtime tracker incremented sensor debounce, low-voltage lockout stuck after charging cross-check Victron SOC, generic_thermostat min_temp clamp missing template render error) / §9 Privacy (no telemetry beyond local 1-Wire / Zigbee / Wi-Fi temperature probes; no vendor cloud / no engine preheat cloud) / §10 Promoting to tier-a (real heated-floor + relay + temperature probe + optional engine preheat bench on CI + RoamCore-owned `config_flow.py` walking Path A vs Path B vs Path C + relay pin / probe pin / engine preheat pin declaration + integration tests asserting the 5 safety interlocks all flip + a setpoint change on `number.rc_hvac_floor_setpoint` triggers the right tile updates)).
- **New** `connections/heated-floors/tests/test_connection_yml.py` (7 manifest-honesty tests: id matches folder / tier-b without tier-a markers (with explicit `config_flow` substring guard for the __init__.py docstring, mirroring the happijac defensive lesson) / docs recipe published with §1–§10 sections including §3 / §4 / §5 for the three paths / category `hvac` matches legacy doc / dashboard tiles follow rc naming (13 tiles; vendor name absolute-forbidden — wyze / mysa / shelly / moen / zigbee / webasto / espar / eberspacher / thermo_top / hydronic / generic_thermostat / climate_ — but lenient on the spec-required tile IDs that contain floor / engine / preheat / thermostat in suffix since those are spec-required) / status reflects no real heated floor with all 5 honesty warnings in tier_warnings / safety interlocks are documented — defensive guard for the future tier-a promotion).
- **Modify** `scripts/check.sh` — append a `run_if_present` entry for `connections/heated-floors/tests/test_connection_yml.py` directly after the existing happijac entry.
- **Modify** `docs/catalog/hvac/heated-floors-and-engine-preheat.md` — add a supersession banner at the top pointing at the new connection folder (legacy content below the banner is preserved for historical context).
- **Modify** `docs/reference/rc-entity-naming.md` — add `hvac` to the Allowed subsystems list (between `bed_lift` and `system`).
- **Modify** `docs/mvp/features-build-status.md` — add a "Shipped (repo)" row for Wave 3 #44 mirroring the happijac row shape (manifest + recipe size + manifest-honesty smoke + contract entities + supersession banner + cross-references to Victron for SOC + to bluetooth-wifi-presence for operator-arrival + to happijac for frost-protection + PR #48 link).
- **New** `Cron-handoff/2026-07-30-heated-floors-connection.md` (this file — slice summary with Context / Changes / Verification / Rollback).

## Verification

Run locally before pushing:

```bash
cd /home/bernard/clawd/RoamCore
git status                                    # clean or only the new files
python3 -m pytest connections/heated-floors/tests/test_connection_yml.py -v
                                               # expect 7/7 PASS
bash scripts/check.sh --core-only              # expect "✓ all requested smoke checks passed."
python3 -c "import yaml; m=yaml.safe_load(open('connections/heated-floors/connection.yml')); \
            assert m['id']=='heated-floors' and m['tier']=='b' and m['category']=='hvac' \
            and len(m['dashboard']['tiles'])==13" \
                                               # expect VERIFICATION OK
git log --oneline -3                          # confirm new commit on feat/connections/heated-floors
git push -u origin feat/connections/heated-floors   # push
gh pr create --base main --head feat/connections/heated-floors \
  --title "Wave 3 #44: Connection: Heated floors + engine pre-heat (tier-b)" \
  --body "<commit body>"                        # open PR (PR #48)
```

## Rollback

If something goes wrong post-merge:

1. Revert the merge commit on `main` (`git revert -m 1 <merge-sha>`).
2. The legacy `docs/catalog/hvac/heated-floors-and-engine-preheat.md` already carries a
   supersession banner pointing at `connections/heated-floors/`, so even
   post-revert operators have a pointer to the previous tier-c spec.
3. Delete the `feat/connections/heated-floors` branch
   (`git branch -d feat/connections/heated-floors` + `git push origin
   --delete feat/connections/heated-floors`) once the PR is closed.
4. If the smoke check itself needs to be removed pre-merge, drop
   the `run_if_present "connections/heated-floors/tests/..."` line from
   `scripts/check.sh` — the connection folder can exist without
   the wire-up until tier-a promotion lands.
5. If the `hvac` subsystem addition to `docs/reference/rc-entity-naming.md`
   needs to be reverted separately, restore the file from the previous
   commit (the only other edit in the slice that touches shared docs is the
   build-status row addition for Wave 3 #44, which is also
   reversible independently).

## Notes for next slice

- The heated-floors recipe references the Victron + bluetooth-wifi-
  presence + happijac connection folders as companions (Victron for
  §7.4 low-voltage lockout; bluetooth-wifi-presence for §7.5
  presence-aware pre-warm; happijac for §7.6 frost-protection
  automation). Keep the cross-refs intact as those slices evolve.
- The recipe's `test_safety_interlocks_are_documented` defensive
  guard fires today (all five safety interlocks ARE documented in
  recipe §7); the tier-a promotion would move that assertion from
  "documented in the recipe" to "hard-enforced in RoamCore-side
  integration code" — at that point the test becomes a runtime
  assertion rather than a documentation assertion.
- The §3 Path A smart thermostat YAML uses well-understood upstream
  vendor `climate.*` entity ids; the §4 Path B `generic_thermostat:`
  YAML uses `sensor.interior_temp` + `switch.heater_relay` with the
  MANDATORY `keep_alive: { minutes: 3 }` setting (without this the
  climate goes stale and the relay never toggles); the §5 Path C
  engine preheat YAML uses `switch.engine_preheat` + a
  cabin-temp-trend-derived active binary_sensor + `utility_meter`
  for the daily runtime tracker.
- The recipe's §6 `rc_hvac_*` contract layer is fully written in
  YAML (template climate wrapper + template sensors + template
  binary_sensors + template switch + template number + template
  select + the low-voltage lockout template); operators wire those
  manually until tier-a promotion lands.
- The `config_flow` substring was explicitly avoided in the
  `__init__.py` docstring (per the happijac docstring-rephrasing
  lesson) — the docstring uses "GUI flow" or "the vendor
  integration's GUI flow" instead.