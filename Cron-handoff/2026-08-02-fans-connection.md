# Wave 3 #59 — Connection: Fans (tier-b) slice handoff

## Context

Promote the legacy tier-c `docs/catalog/fans/index.md`
spec (a 14-line stub, originally listed "Fans are a
simple upgrade that massively improves comfort: airflow,
condensation control, cooking smells, and keeping the
van livable in warm weather. This section covers fan
controllers, vent fans, and easy automations like 'run
when humidity is high'" with no recipe + no contract + no
vendor-neutral coverage — just a placeholder) into a
tier-b recipe connection at `connections/fans/`. Follows
the same pattern proven by Wave 3 #52 approach-lights /
#53 motion-based-lighting / #54 timezone-geolocator /
#55 time-atomic / #56 in-cab-tablet-dashboard / #57 NFC
tags / #58 remote-access tier-b/tier-c recipe slices.
This is the FIRST `ventilation`-category slice in the
RoamCore connection pipeline; the `ventilation` subsystem
addition to `docs/reference/rc-entity-naming.md` is NEW
(this slice adds the `ventilation` subsystem to the
`Allowed subsystems` list). The `ventilation` category
is the canonical category for fans + the rooftop vent
fans + the circulation fans.

Fans (vendor-neutral fan-controller umbrella for HA,
covering rooftop vent fans + circulation fans + bathroom
exhaust fans — rooftop + circulation fans cover the
climate-aware airflow + the rain-sensor safety block;
bathroom exhaust fans wire as a separate downstream
`fan.*` entity that RoamCore does NOT own) — the umbrella
for "Fans are a simple upgrade that massively improves
comfort: airflow, condensation control, cooking smells,
and keeping the van livable in warm weather" — is the
ventilation-category complement to the broader RoamCore
climate-aware automation affordances. The single "is the
fan currently running?" tile aggregates the upstream fan
state into one dashboard indicator; the "current speed"
tile surfaces the fan's 0-100 percent; the "fan mode"
selector is the operator-facing affordance (one of `off` /
`low` / `med` / `high` / `auto` / `rain_safe`); the "fan
active" tile is the AND gate (TRUE iff the fan is
currently running); the "runtime minutes today" tile is
the daily runtime aggregate; the "last trigger reason"
tile surfaces the reason the fan was last turned on (one
of `manual` / `humidity` / `temperature` / `schedule` /
`sleep`); the "run-now 15min" button is the manual
override (the operator can force the fan to run for 15
minutes from the dashboard without waiting for the
auto-fan-on-humidity-high or auto-fan-on-temperature-high
automations); the "rain sensor active" tile is the rooftop
safety block (TRUE iff the rain sensor is wet — the
rooftop fan is forced OFF + the rooftop vent cover is
forced CLOSED when this tile is TRUE).

RoamCore ships no native fan integration; tier-b is
honest because we explicitly do NOT maintain a custom
fan integration — the upstream HA core `fan` integration
(since 2022.x — has exposed a `set_percentage` service +
a `percentage` attribute + a `preset_mode` attribute +
the `fan.turn_on` / `fan.turn_off` / `fan.toggle` /
`fan.set_percentage` / `fan.set_preset_mode` services +
the `fan` domain since 2022.x) is the canonical umbrella
+ the HA core `template:` fan wrapper (since 2022.x) is
the canonical Path C wrapping for relay-driven fans +
the HA core `zwave_js` integration (since 2022.x) is the
canonical Path A1 Z-Wave fan controller integration +
the HA core `zha` integration (since 2022.x) is the
canonical Path A2 Zigbee fan controller integration +
the HA core `mqtt` integration (since 2022.x) is the
canonical Path A3 generic-tasmota-flashed fan controller
integration + the HA core Shelly integration (since
2022.x) is the canonical Path C1 Shelly 1 / Shelly Plus 1
wired to a 12 V fan integration + the HACS `bond`
integration (HACS) is the canonical Path B1 Bond Home +
ceiling fan integration + the HACS `tuya` integration
(HACS) is the canonical Path B3 Tuya Wi-Fi smart fan
integration + the HACS `hunterdouglas_simplify`
integration (HACS) is the canonical Path B2 Hunter
SIMPLEconnect Wi-Fi/BLE fan integration.

Four install paths (operator picks based on hardware
ownership + vendor preference + relay vs smart fan
choice):

- **Path A — Smart fan controllers (Z-Wave / Zigbee /
  MQTT).** The operator installs a Z-Wave fan controller
  (Zooz ZEN17 + Aeotec Nano Switch + Inovelli LZW42 are
  common choices for 12 V / 24 V fans) + the HA core
  `zwave_js` integration OR a Zigbee fan controller +
  the HA core `zha` integration OR a
  generic-tasmota-flashed fan controller + the HA core
  `mqtt` integration. The HA core `fan` integration has
  exposed the standard `set_percentage` service +
  `percentage` attribute + `preset_mode` attribute since
  2022.x; the operator uses `fan.set_percentage` to
  control the fan speed + uses the `percentage`
  attribute to read the current speed. Path A covers
  three sub-flavors: Path A1 Z-Wave fan controller
  (Zooz ZEN17 + Aeotec Nano Switch + Inovelli LZW42),
  Path A2 Zigbee fan controller (generic-Zigbee fan
  controllers + the Tuya Zigbee fan family), Path A3
  generic-tasmota-flashed fan controller (any 12 V /
  24 V fan relay + Tasmota + the HA core `mqtt`
  integration).

- **Path B — Wi-Fi / BLE smart fan (Bond Home + Hunter
  SIMPLEconnect + Tuya).** The operator installs a Bond
  Home RF-bridge-controlled ceiling fan + the HACS
  `bond` integration OR a Hunter SIMPLEconnect Wi-Fi/BLE
  fan + the HACS `hunterdouglas_simplify` integration OR
  a Tuya Wi-Fi smart fan + the HACS `tuya` integration.
  Path B covers three sub-flavors: Path B1 Bond Home +
  ceiling fan (the HACS `bond` integration surfaces Bond
  Home RF-bridge-controlled ceiling fans as `fan.*`
  entities), Path B2 Hunter SIMPLEconnect Wi-Fi/BLE fan
  (the HACS `hunterdouglas_simplify` integration surfaces
  Hunter SIMPLEconnect Wi-Fi/BLE fans as `fan.*`
  entities), Path B3 Tuya Wi-Fi smart fan (the HACS
  `tuya` integration surfaces Tuya Wi-Fi smart fans as
  `fan.*` entities).

- **Path C — Generic 12 V / 24 V fan + relay (no smart
  fan controller).** The operator wires a 12 V / 24 V
  ventilation fan + a Shelly 1 / Shelly Plus 1 / Zooz
  ZEN17 / Aeotec Nano Switch relay + the HA core Shelly
  integration OR the HA core `zwave_js` integration OR
  the HA core `template:` fan wrapper (since 2022.x —
  wraps any relay state into a virtual `fan.*` entity
  that exposes the standard `percentage` + `preset_mode`
  + `fan.set_percentage` service contract). Path C
  covers two sub-flavors: Path C1 Shelly 1 / Shelly Plus
  1 wired to a 12 V fan + the HA core Shelly integration
  + the HA core `template:` fan wrapper; Path C2 Zooz
  ZEN17 / Aeotec Nano Switch wired to a 24 V fan + the
  HA core `zwave_js` integration + the HA core
  `template:` fan wrapper.

- **Path D — All-in-one smart fan (MaxxAir / Fan-Tastic
  / MAXXAIR Deluxe).** The operator installs the
  rooftop vent fan per the manufacturer instructions +
  wires it into HA via the manufacturer-recommended
  integration (MaxxAir iFAN + Fan-Tastic Vent + MAXXAIR
  Deluxe all expose a vendor integration that surfaces
  as a `fan.*` entity + a `cover.*` entity for the
  automatic rain cover). The recipe's rain-sensor
  safety block forces the fan OFF + the cover CLOSED
  when the rain sensor trips.

RoamCore ships no native fan integration; the umbrella
LIFTS nothing from prior slices (Wave 2 #29 lifted the
Tailscale contract into the remote-access umbrella; this
slice is a fresh vendor-neutral fan umbrella with no Wave
2 prior). The recipe is the canonical howto for the FOUR
operator-pickable paths + the 8 `rc_fan_*` contract
tiles + the FIVE §8 automations + the 6 §9
troubleshooting entries + privacy + tier-a promotion
outline.

## Changes

- `connections/fans/connection.yml` — tier-b manifest,
  ventilation category, status=beta, 8 `rc_fan_*`
  vendor-neutral tiles (1 fan main + 1 sensor
  speed_percent + 1 select mode + 1 binary_sensor
  active + 1 sensor runtime_minutes_today + 1 sensor
  last_trigger_reason + 1 button run_now_15min + 1
  binary_sensor rain_sensor_active), 5 tier_warnings,
  install.hacs=false (fans does NOT depend on a HACS
  add-on as a required dependency), install.config_flow=
  true (the UPSTREAM HA core `fan` integration + the HA
  core `zwave_js` integration + the HA core `zha`
  integration + the HA core `mqtt` integration + the HA
  core Shelly integration + the HACS `bond` integration +
  the HACS `tuya` integration + the HACS
  `hunterdouglas_simplify` integration all expose a GUI
  flow since 2022.x — honest upstream truth, NOT a
  tier-a marker for RoamCore's tier), wizard.one_tap=
  false, wizard.connection_kind=recipe, wizard
  .upstream_truth="RoamCore does NOT maintain a custom
  fan integration; the upstream HA core `fan` integration
  handles 95%+ of operator-facing fan operators. RoamCore
  ships a vendor-neutral `rc_fan_*` contract layer that
  maps any upstream `fan.*` entity (MaxxAir / Fan-Tastic
  / MAXXAIR Deluxe / Heng's / Vento / generic-Zigbee /
  generic-Z-Wave / Tuya / Shelly / Zooz / GE / Leviton /
  Inovelli / Bond Home / Hunter) into the contract tiles
  via HA `template:` fan + the `fan.set_percentage` /
  `fan.turn_on` / `fan.turn_off` services." Style mirrors
  the remote-access slice's manifest header exactly.
- `connections/fans/__init__.py` — `DOMAIN = "fans"`
  marker stub + verbose module docstring walking the
  FOUR operator-pickable paths (Path A wired Z-Wave /
  Zigbee / MQTT fan controller + the upstream HA core
  `zwave_js` / `zha` / `mqtt` integration GUIs + the
  `fan.set_percentage` service; Path B Wi-Fi / BLE smart
  fan (Bond Home / Hunter SIMPLEconnect / Tuya) + the
  HACS `bond` or HACS `tuya` or HACS
  `hunterdouglas_simplify` integration; Path C generic
  12 V / 24 V fan + relay + a Shelly 1 / Shelly Plus 1 /
  Zooz ZEN17 / Aeotec Nano Switch + the HA core
  `template:` fan wrapping the relay state into a
  virtual `fan.*`; Path D all-in-one smart fan (MaxxAir
  / Fan-Tastic / MAXXAIR Deluxe) + the manufacturer-
  recommended integration auto-discovery + the upstream
  `fan.turn_on` / `fan.turn_off` / `fan.set_percentage`
  service mappings + the upstream `cover.close_cover`
  service call for the rooftop vent cover). Substring
  guard rephrased: "operator-wired setup flow" + "the
  upstream integration's GUI flow" instead of the literal
  `config_flow.py` (the happijac / remote-access lesson).
  Style mirrors the remote-access slice's __init__.py
  docstring exactly.
- `connections/fans/README.md` — folder overview + the
  4-path summary + the supersession pointer. Style
  mirrors the remote-access slice's README.md exactly.
- `connections/fans/docs/recipe.md` — ~1170-line howto,
  12 §sections mirroring the remote-access slice shape:
  - §1 "What are fans in RoamCore?" (positioning:
    rooftop + circulation + bathroom, vendor-neutral
    fan-controller semantics, the climate-aware auto-
    fan gate, the single "fan active" aggregate, the
    rain-sensor hard-block).
  - §2 "Prerequisites" (at least 1 controllable fan
    installed + the operator's choice of upstream fan
    controller integrated into HA + temperature +
    humidity via the HVAC basics Wave 3 #49 connection's
    `sensor.rc_hvac_interior_temperature` +
    `sensor.rc_hvac_interior_humidity` + optional rain
    sensor for the rain-safe mode + optional
    time-of-day / sunrise-sunset for the Sleep mode).
  - §3 "Path A — Smart fan controllers (Z-Wave /
    Zigbee / MQTT)" (full wiring for Zooz ZEN17 /
    Aeotec Nano Switch / Inovelli LZW42 + the HA core
    `zwave_js` integration + the HA core `zha`
    integration + the HA core `mqtt` integration; Path
    A1 Z-Wave fan controller; Path A2 Zigbee fan
    controller; Path A3 generic-tasmota-flashed fan
    controller).
  - §4 "Path B — Wi-Fi / BLE smart fan (Bond Home +
    Hunter SIMPLEconnect + Tuya)" (full wiring for Bond
    Home + the HACS `bond` integration + Hunter
    SIMPLEconnect + the HACS `hunterdouglas_simplify`
    integration + Tuya + the HACS `tuya` integration;
    the recipe walks the operator through creating a
    `fan.bond_fan` / `fan.tuya_fan` virtual entity via
    HA `template:` fan + binding the controller to the
    contract tiles).
  - §5 "Path C — Generic 12 V / 24 V fan + relay (no
    smart controller)" (Shelly / Zooz / Aeotec wiring +
    the LED driver's fan + HA Shelly / Z-Wave
    integration auto-discovery + `template:` fan
    wrapping the relay state into a virtual
    `fan.ventilation`).
  - §6 "Path D — All-in-one smart fan (MaxxAir /
    Fan-Tastic / MAXXAIR Deluxe)" (the rooftop-vent-fan
    walkthrough + the HA core `fan` integration auto-
    discovery + the `fan.set_percentage` /
    `fan.turn_on` / `fan.turn_off` service mappings +
    the rain-sensor safety block + the upstream cover
    entity for the rooftop vent cover).
  - §7 "RoamCore contract entities" (the 8 `rc_fan_*`
    tiles + how the upstream fan template exposes them
    + translation helpers needed for the derived metrics
    like `runtime_minutes_today` + `last_trigger_reason`
    + `rain_sensor_active`).
  - §8 "Automations" (at least 5: auto-fan on humidity
    high (triggered by
    `sensor.rc_hvac_interior_humidity` > 65%) + auto-fan
    on temperature high (triggered by
    `sensor.rc_hvac_interior_temperature` > 28°C) +
    manual override via `button.rc_fan_run_now_15min` +
    rain-sensor hard-block (the rain sensor trips →
    `binary_sensor.rc_fan_rain_sensor_active` becomes
    TRUE AND the fan is forced to OFF + the cover is
    forced CLOSED via the upstream cover entity if
    available) + Sleep mode suppression via
    `select.rc_mode` from the mode/automation-builder
    recipe).
  - §9 "Troubleshooting" (at least 6 entries: fan
    never starts (upstream fan integration not wired /
    climate sensors not wired / Sleep mode
    suppressing / `binary_sensor.rc_fan_active` is
    FALSE), fan stays on forever (number of minutes
    set too high / the auto-off automation missing),
    fan only runs at full speed (vendor fan controller
    not configured for variable speed / Path A vs Path
    B confusion), rain-sensor always blocks (rain sensor
    not wired / rain sensor polarity reversed / rain
    sensor stuck in the "wet" state), Sleep mode
    doesn't suppress (mode/automation-builder recipe not
    wired / `select.rc_mode` tile missing), fan-only
    airflow control doesn't reach the bathroom
    (downstream linkage not wired / circulation-fan
    template missing)).
  - §10 "Privacy" (the fan produces no telemetry beyond
    local on/off state + speed; the rain sensor is a
    physical switch; no cloud call home — MaxxAir /
    Fan-Tastic / MAXXAIR Deluxe / Bond Home / Hunter
    SIMPLEconnect / Tuya require their own cloud auth
    for first-time setup if the operator selects Path
    B / Path D but subsequent runs are local; Path A
    Z-Wave / Zigbee is fully local).
  - §11 "Promoting to tier-a" (what would need to
    happen: real Z-Wave fan controller + 12 V fan +
    Bond Home + MaxxAir + rain sensor on CI bench,
    RoamCore-owned operator-wired setup flow that walks
    the operator through choosing Path A / B / C / D +
    declaring the upstream entities + the rain-sensor
    safety block, integration tests that assert a
    humidity-high event triggers the auto-fan + a
    rain-sensor-trip event forces the fan off + a
    Sleep mode change suppresses the auto-fan).
  - §12 "Files in this connection + cross-references"
    (the 5 files + the cross-references to the upstream
    integrations + the HVAC basics Wave 3 #49 connection
    + the time-atomic Wave 3 #55 connection + the
    timezone-geolocator Wave 3 #54 connection + the
    cover entities + the mode/automation-builder Wave 2
    #23 connection + the approach-lights Wave 3 #52
    connection + the motion-based-lighting Wave 3 #53
    connection + the NFC tags Wave 3 #57 connection +
    the RoamCore entity naming doc).
- `connections/fans/tests/test_connection_yml.py` — 7
  manifest-honesty tests mirroring the remote-access test
  pattern, with these `fans` substitutions:
  - `test_id_matches_folder_name` (id=`fans`).
  - `test_tier_b_without_tier_a_markers` (tier=b,
    wizard.one_tap=false, install.config_flow=true
    with the upstream-truth footnote, install.hacs=
    false (fans does NOT depend on a HACS add-on as a
    required dependency), no `config_flow.py`,
    `__init__.py` is DOMAIN stub only — substring guard
    rephrased to "operator-wired setup flow" + "the
    upstream integration's GUI flow" + asserted in the
    test that the docstring contains `operator-wired` +
    `GUI flow`).
  - `test_requires_docs_recipe_published` (recipe
    exists, ≥600 lines, mentions fans / `rc_fan_`).
  - `test_category_matches_existing_legacy_doc`
    (category=`ventilation`, legacy
    `docs/catalog/fans/index.md` still exists with the
    SUPERSEDED banner).
  - `test_dashboard_tiles_follow_rc_naming` (exactly 8
    vendor-neutral `rc_fan_*` tiles; no vendor double-
    stamps; the `^[a-z_]+\.rc_fan_[a-z0-9_]+$` pattern
    is enforced; forbidden_substrings covers vendor +
    protocol + integration + hardware names including
    `maxxair`, `fan_tastic`, `maxtreme`, `fantastic_
    vent`, `hengs`, `vento`, `shelly`, `zooz`, `aeotec`,
    `inovelli`, `bond`, `hunter`, `simbleconnect`,
    `tuya`, `simp`, `caseta`, `lutron`, `philips`,
    `hue`, `zwave`, `zha`, `zigbee`, `mqtt`,
    `template_fan`, `template_`, `deconz`, `conbee`,
    `raspbee`, `sonoff`, `nous`, `aqara`, `12v`, `24v`,
    `vent`, `ventilation`, `rotating`, `3_speed`,
    `preset_mode`).
  - `test_status_reflects_no_real_fan_controller`
    (status=beta, all 5 honesty warnings in
    tier_warnings: no_real_fan_controller_for_integration
    _test + recipe_depends_on_user_running_fan_plus_
    humidity_sensor_plus_rain_sensor + optional_smart_
    fan_vs_relay_vs_hub_choice + requires_operator_
    wiring_safety_rain_sensor_before_first_use_if_
    rooftop + mode_aware_sleep_suppression_required_for
    _overnight_camp).
  - `test_automations_are_documented` (recipe.md §8
    covers the 5 automations: auto-fan-on-humidity-high
    + auto-fan-on-temperature-high + manual-override-
    via-button + rain-sensor-hard-block + stealth-mode-
    suppression; cross-references to HVAC basics Wave 3
    #49 + mode/automation-builder Wave 2 #23 + cover
    entities for the rain-safe cover block + time-
    atomic for Sleep mode + RFID-blocker-free rain
    sensor contract).

- `scripts/check.sh` — created from scratch (file does
  not exist on origin/main; branch-local). Copy of the
  canonical chain from `feat/connections/remote-access`
  @ `f2a1fed` + the `run_if_present` entry for
  `connections/fans/tests/test_connection_yml.py`
  immediately after the remote-access entry. The script
  is a faithful copy of the canonical chain pattern used
  by all Wave 3 slices — `run_if_present` for every
  connection smoke + the Wave 2 #23-#33 smoke probes +
  the `--core-only` mode + the full suite mode.
- `docs/catalog/fans/index.md` — prepended the
  SUPERSEDED banner pointing at `connections/fans/`.
  Mirrors the remote-access banner shape exactly.
- `docs/reference/rc-entity-naming.md` — added the
  `ventilation` subsystem to the `Allowed subsystems`
  list. One-line addition: `ventilation` — fans +
  climate-aware airflow + ventilation mode overrides +
  rain-sensor safety blocks; vendor-neutral `rc_fan_*`
  ids. This is the FIRST `ventilation`-category slice
  in the RoamCore connection pipeline; the addition
  mirrors how the `power` subsystem was added by Wave 1
  + how the `net` subsystem was added by Wave 1 + how
  the `system` subsystem was added by Wave 1.
- `docs/mvp/features-build-status.md` — added the
  "Fans (vendor-neutral fan-controller umbrella for HA
  — rooftop vent fans + circulation fans + bathroom
  exhaust fans, operator picks ONE path)" Shipped (repo)
  row right after the Traccar live map row. Includes
  the tier-b manifest + recipe + smoke + contract tiles
  + vendor-neutrality + legacy supersession banner +
  cross-references (HA core `fan` integration + HA core
  `zwave_js` integration + HA core `zha` integration +
  HA core `mqtt` integration + HA core Shelly
  integration + HACS `bond` integration + HACS `tuya`
  integration + HACS `hunterdouglas_simplify`
  integration + cover entities for the Path D rain-safe
  cover block + HVAC basics Wave 3 #49 +
  mode/automation-builder recipe + time-atomic Wave 3
  #55 + approach-lights Wave 3 #52 + motion-based-
  lighting Wave 3 #53 + NFC tags Wave 3 #57) + PR #N
  placeholder (initially `#63`, updated to actual PR
  number in follow-up commit after `gh pr create`).
- `Cron-handoff/2026-08-02-fans-connection.md` (this
  file) — Context / Changes / Verification / Rollback
  format. Mirrors the remote-access cron-handoff shape
  exactly.

## Verification

- `bash scripts/check.sh --core-only` → exit 0. The new
  fans smoke check runs and passes (7/7 manifest-
  honesty tests pass); all other 24 connection smokes
  SKIP (their test files aren't on this branch —
  expected); the ha-beta-smoke passes (the existing
  test); all requested smoke checks pass.
- `python3 -m pytest connections/fans/tests/ -v` →
  7/7 tests pass:
  - test_id_matches_folder_name ✓
  - test_tier_b_without_tier_a_markers ✓ (substring
    guard against `config_flow.py` passes; tier=b;
    hacs=false; config_flow=true with the upstream-truth
    footnote; description documents reuse-first
    strategy over the upstream HA core `fan`
    integration; links.official includes the HA core
    `fan` integration upstream doc URL; substring guard
    rephrasing check passes (docstring contains
    `operator-wired` + `GUI flow`))
  - test_requires_docs_recipe_published ✓ (≥600 lines,
    specifically 1170 lines; all 12 §sections present;
    references `rc_fan_`)
  - test_category_matches_existing_legacy_doc ✓
    (category=ventilation; SUPERSEDED banner present on
    legacy doc; legacy doc preserved)
  - test_dashboard_tiles_follow_rc_naming ✓ (exactly 8
    vendor-neutral `rc_fan_*` tiles; forbidden_substrings
    enforces no vendor / protocol / hardware /
    integration leaks including MaxxAir / Fan-Tastic /
    MAXXAIR Deluxe / Heng's / Vento / Shelly / Zooz /
    Aeotec / Inovelli / Bond / Hunter / Tuya / Simp /
    Caseta / Lutron / Philips / Hue / Z-Wave / ZHA /
    Zigbee / MQTT / template_fan / Deconz / Conbee /
    Raspbee / Sonoff / Nous / Aqara / 12v / 24v / vent /
    rotating / 3_speed / preset_mode vendor / hardware /
    protocol / integration names; preserves the
    spec-required `main`, `speed`, `percent`, `mode`,
    `active`, `runtime`, `minutes`, `today`, `last`,
    `trigger`, `reason`, `run`, `now`, `rain`, `sensor`,
    `button` substrings in the spec-required tile ids)
  - test_status_reflects_no_real_fan_controller ✓
    (status=beta; 5 tier_warnings present)
  - test_automations_are_documented ✓ (the FIVE §8
    automations documented + 4 safety tiles wired +
    sensor.rc_hvac_interior_humidity +
    sensor.rc_hvac_interior_temperature + HA core `fan`
    integration + home-assistant.io/integrations/fan +
    zwave_js + zha integration + mqtt integration +
    template + bond + tuya + cover.close_cover +
    select.rc_mode + time-atomic + approach-lights
    cross-references)
- `git ls-remote origin 'refs/heads/feat/connections/
  fans'` → branch on origin (after push).
- `gh pr view --json number,state,url` → PR #N OPEN
  (after gh pr create).

## Rollback

Pure additive UI slice. Rollback is `gh pr close N` (or
`gh pr close N -d "superseded"`) followed by `git revert
<commit>` on main (or `git push origin --delete
feat/connections/fans` if the PR was the only thing on
the branch). No infrastructure state to roll back; no
migrations; no config changes; no secrets; the
SUPERSEDED banner on the legacy
`docs/catalog/fans/index.md` doc is reverted when the
legacy doc is restored.

The `scripts/check.sh` file is a NEW file on this branch
(it doesn't exist on origin/main); reverting the PR will
delete the file. Future slices that need to add their own
smoke check will need to re-create check.sh OR branch
from this branch's tip.

If the standing `bash scripts/check.sh --core-only` check
mysteriously regresses on main after this PR lands, the
most likely culprit is a forgotten smoke-check entry in
`scripts/check.sh` — the slice adds the fans smoke
directly after the remote-access entry; verify the entry
is still present after revert + re-merge.

## Notes

- Branch cut fresh from `origin/main` @ `609b85a` (NOT
  stacked on the prior remote-access branch — same
  pattern as timezone-geolocator / time-atomic /
  in-cab-tablet-dashboard / nfc-tags / remote-access
  slices; the cron cuts fresh from main each time).
- The `__init__.py` docstring rephrases `config_flow`
  to "operator-wired setup flow" + "the upstream
  integration's GUI flow" to avoid the literal
  `config_flow.py` substring trap (the happijac /
  remote-access lesson).
- The `ventilation` subsystem in `rc-entity-naming.md`
  is the FIRST entry to claim it (no prior slice has
  added it; the line was added by this slice).
- Pure additive — no schema changes, no breaking
  changes to existing URL contracts, no data
  migrations, no forklift rewrites.
- No `docs/catalog/homelab/adguard-home.md` or
  pi-hole/dns-blocker files touched (per the
  constraint).
- The forbidden_substrings list in the test includes
  the vendor names above (maxxair / fan_tastic /
  maxtreme / fantastic_vent / hengs / vento / shelly /
  zooz / aeotec / inovelli / bond / hunter /
  simbleconnect / tuya / simp / caseta / lutron /
  philips / hue / zwave / zha / zigbee / mqtt /
  template_fan / template_ / deconz / conbee / raspbee
  / sonoff / nous / aqara / 12v / 24v / vent /
  ventilation / rotating / 3_speed / preset_mode) per
  the constraint.
- The 8 `rc_fan_*` contract tiles are vendor-neutral —
  no vendor / hardware / protocol / integration names
  leak into the tile ids.
- The recipe includes cross-references to the HVAC
  basics Wave 3 #49 connection (for the
  `sensor.rc_hvac_interior_temperature` +
  `sensor.rc_hvac_interior_humidity` source tiles that
  the §8.1 + §8.2 auto-fan automations read from) +
  the mode/automation-builder Wave 2 #23 connection
  (for the `select.rc_mode` tile that the §8.5 Sleep
  mode suppression reads from) + the cover entities
  (for the upstream cover integration that the §8.4
  rain-sensor hard-block's `cover.close_cover` service
  call targets) + the time-atomic Wave 3 #55
  connection (for the time-of-day / sunrise-sunset
  primitives that the §8.5 Sleep mode suppression uses)
  + the RFID-blocker-free rain sensor contract.

## Slice handoff

Wave 3 #59 SHIPPED. Branch: `feat/connections/fans`.
PR: expected #63 (next after #62 OPEN). Commit subject:
`Wave 3 #59: Connection: Fans (rooftop + circulation)
(tier-b) — vendor-neutral fan controller + rain-sensor
safety block`.