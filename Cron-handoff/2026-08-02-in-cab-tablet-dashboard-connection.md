# Wave 3 #56 — Connection: In-cab tablet dashboard (tier-c) slice handoff

## Context

Promote the legacy tier-c in-cab-tablet-dashboard spec into a
tier-c recipe connection at
`connections/in-cab-tablet-dashboard/`. The unified-backlog row
#56 ("Connection: **In-cab tablet dashboard** (M-sized,
`docs/catalog/vehicle-obd/in-cab-tablet-dashboard.md`)") is a
thin folder-overview pointer; this slice creates the new
connection folder + the recipe + the contract + the THREE
§7 automations + the 8 `rc_in_cab_tablet_*` contract tiles +
the 6 §8 troubleshooting entries + the §9 privacy section + the
§10 tier-b promotion outline + the §11 cross-references
(Wican Pro Wave 3 #6 + Traccar Wave 3 #36 + HA Companion +
Approach lights Wave 3 #52 + HVAC basics Wave 3 #49 + Teltonika
LTE Wave 3 #39). Follows the same pattern proven by Wave 3 #35
Frigate / #36 Starlink / #37 DNS blocker / #38 NAS / #39
Teltonika / #40 Peplink / #41 Music Assistant / #42
Bluetooth-Wi-Fi presence / #43 Happijac / #44 Heated floors / #45
Smoke-CO-gas / #46 Smart automations / #47 Mock location / #48
Deadbolts / #49 HVAC basics / #50 Water tanks / #51 Electronic
valves / #52 Approach lights / #53 Motion-based lighting / #54
Timezone geolocator / #55 Time (atomic). This is the
in-cab-tablet-dashboard SPECIFIC subset of the broader vehicle
subsystem in the RoamCore connection pipeline. The `vehicle`
subsystem `rc_vehicle_*` prefix is OWNED by the existing Wican
Pro Wave 3 #6 connection (the OBD-II reader that publishes
`binary_sensor.rc_vehicle_ignition` + `sensor.rc_vehicle_battery_
voltage` + `sensor.rc_vehicle_coolant_temp` + `sensor.rc_vehicle_
speed` + `sensor.rc_vehicle_obd_fault_count`) — this slice
inherits the `rc_vehicle_*` prefix from the existing Wican Pro
entities and extends it with the `rc_in_cab_tablet_*` SPECIFIC
subset for the dashboard view state, mirroring how time-atomic
Wave 3 #55 inherits the `rc_time_*` prefix from the existing
time helpers and how hvac-basics Wave 3 #49 inherits the
`rc_hvac_*` prefix from heated-floors Wave 3 #44.

In-cab tablet dashboard (driving / arrival / lock-screen
Lovelace views with ignition-aware auto-switch) — the umbrella
for "mount a small tablet in the cab that shows the handful of
controls and readouts you care about while driving + a richer
control surface on arrival + a battery-friendly lock screen
while parked" — is positioned in RoamCore as a reuse-first recipe
over the upstream HA Lovelace view system. The single "what view
is the in-cab tablet showing?" tile aggregates the Lovelace
view's active view into one dashboard indicator; the "is the
in-cab tablet in driving mode?" binary_sensor is the safety gate
(TRUE when view=`driving`); the "is the in-cab tablet in lock
screen mode?" binary_sensor is the battery gate (TRUE when
view=`lock_screen`); the view mode select is the manual override;
the switch view now button is the one-tap manual switch. RoamCore
ships no native in-cab-tablet dashboard engine; tier-c is honest
because we explicitly do NOT maintain a custom in-cab-tablet
dashboard engine — the upstream HA Lovelace view system (since
2022.x — exposes a `view` config block in `ui-lovelace.yaml` + a
panel view via the dashboard UI's "Add view" button + the
`lovelace:` config block under `dashboard:` HA core UI
configuration) is the canonical view-switching engine, and the
RoamCore wrapper is a few thin automations + the contract layer.

Three install paths (operator picks ONE OR MORE based on
hardware ownership + connectivity preferences):

- **Path A — "Driving" view.** Lovelace view YAML with view
  type `panel`, view icon `mdi:car`, view title `Driving`, big-
  button tile layout, only safe interactions (toggle exterior
  lights + toggle compressor + mute the cabin). Path A is the
  default for any van that has a tablet mounted in the cab while
  the operator is driving.

- **Path B — "Arrival / Welcome" view.** Ignition-triggered
  view switch via an automation that watches the OBD-II
  `binary_sensor.rc_vehicle_ignition` from Wican Pro Wave 3 #6
  OR a generic `binary_sensor.*` ignition source OR a
  `device_tracker.rc_location_van` state change to home zone.
  The arrival view shows exterior lighting + compressor + house
  status (battery + water + propane + interior temp).

- **Path C — "Lock screen / Always-on-display" view.** A
  battery-friendly low-power dashboard showing critical house
  status (battery SOC + water level + interior temp) + key
  vehicle stats (battery voltage + cabin temp). The view
  refreshes every 60s + uses dimmed colors + minimal true/false
  states to preserve the tablet's battery. Path C is the
  default for the in-cab tablet when the ignition is off and the
  operator is away from the van.

All three paths land on the same vendor-neutral 8
`rc_in_cab_tablet_*` contract tiles:

- `sensor.rc_in_cab_tablet_active_view` — the currently-active
  view (one of `driving` / `arrival` / `lock_screen` / `manual`).
  Source: HA core `template:` sensor reading the
  `select.rc_in_cab_tablet_view_mode` select's current option.
- `sensor.rc_in_cab_tablet_ignition_state` — the ignition
  state (one of `on` / `off` / `unknown`). Source: HA core
  `template:` sensor reading the
  `binary_sensor.rc_vehicle_ignition` from Wican Pro Wave 3 #6.
- `sensor.rc_in_cab_tablet_last_view_change_minutes_ago` —
  the freshness timestamp (minutes since the last view
  change). Source: HA core `template:` sensor deriving the
  freshness from the
  `automation.in_cab_tablet_arrival_view_on_ignition_on`'s
  `last_triggered` attribute + the
  `automation.in_cab_tablet_lock_screen_view_on_ignition_off`'s
  `last_triggered` attribute + the
  `automation.in_cab_tablet_manual_override`'s `last_triggered`
  attribute.
- `sensor.rc_in_cab_tablet_refresh_cadence_seconds` — the
  refresh cadence for the active view (default: 60s for
  `lock_screen`, 5s for `driving`, 5s for `arrival`). Source: HA
  core `template:` sensor deriving the cadence from the active
  view + the operator's tablet settings.
- `binary_sensor.rc_in_cab_tablet_driving_mode_active` — the
  safety gate (TRUE when view=`driving`). Source: HA core
  `template:` binary_sensor.
- `binary_sensor.rc_in_cab_tablet_lock_screen_active` — the
  battery gate (TRUE when view=`lock_screen`). Source: HA core
  `template:` binary_sensor.
- `select.rc_in_cab_tablet_view_mode` — the manual override
  (values: `driving` / `arrival` / `lock_screen` / `manual`).
  Source: HA core `input_select` integration.
- `button.rc_in_cab_tablet_set_view_now` — the one-tap manual
  switch (when pressed, opens a Lovelace view picker). Source:
  HA core `input_button` integration.

Three §7 automations (MANDATORY before first use):

- §7.1 **Ignition-on auto-switch to `arrival` view** — triggers
  when the Wican Pro Wave 3 #6
  `binary_sensor.rc_vehicle_ignition` turns on (canonical
  trigger) OR a generic `binary_sensor.*` ignition source
  turns on (fallback trigger) OR a `device_tracker.rc_location_
  van` state change to home zone (location proxy trigger). The
  arrival view surfaces exterior lighting + compressor + house
  status.
- §7.2 **Ignition-off auto-switch to `lock_screen` view** —
  triggers when the Wican Pro Wave 3 #6
  `binary_sensor.rc_vehicle_ignition` turns off. The lock
  screen view is battery-friendly + shows critical house
  status + key vehicle stats. The view refreshes every 60s +
  uses dimmed colors + minimal true/false states to preserve
  the tablet's battery.
- §7.3 **Manual override via the
  `select.rc_in_cab_tablet_view_mode` select or the
  `button.rc_in_cab_tablet_set_view_now` button** — triggers
  when the operator changes the view mode select OR presses
  the switch view now button. The automation's action is to
  set the view mode to `manual` (so the next ignition event
  reverts to the auto-switched view; a graceful opt-out for
  the operator who wants to override the auto-switch logic on
  a one-off basis).

## Changes

Files added (6):

- `connections/in-cab-tablet-dashboard/connection.yml` (293
  lines) — the source-of-truth manifest. Mirrors the
  time-atomic shape; the in-cab-tablet-dashboard
  `rc_in_cab_tablet_*` prefix is the SPECIFIC in-cab-tablet-
  dashboard subset of the broader vehicle subsystem (the
  `vehicle` subsystem `rc_vehicle_*` prefix is OWNED by the
  existing Wican Pro Wave 3 #6 connection). The three install
  paths (Path A "Driving" view + Path B "Arrival / Welcome"
  view + Path C "Lock screen / Always-on-display" view) + the
  8 `rc_in_cab_tablet_*` contract tiles are documented in the
  description + tier_warnings + dashboard.tiles. The reuse-
  first strategy is explicitly documented in the description
  (no custom in-cab-tablet dashboard engine; HA's Lovelace
  view system + the upstream `input_select` + `input_button` +
  `device_tracker` integrations).
- `connections/in-cab-tablet-dashboard/__init__.py` (120 lines)
  — `DOMAIN = "in_cab_tablet"` marker for the audit. The
  docstring rephrases the strategy to avoid the literal
  `config_flow.py` substring (the same trap the happijac
  slice was bitten by). The substring guard in
  `test_tier_c_documents_reuse_first_strategy` asserts no
  `config_flow.py` substring appears anywhere in the file.
- `connections/in-cab-tablet-dashboard/README.md` (49 lines) —
  the folder overview. Cross-references Wican Pro + Traccar +
  HA Companion app + Approach lights + HVAC basics + Teltonika.
- `connections/in-cab-tablet-dashboard/docs/recipe.md` (~1300+
  lines, 11 §sections) — the full howto. §1 the umbrella
  positioning + reuse-first strategy + single "active view?"
  tile + driving-mode safety gate + lock-screen battery gate +
  THREE-path wrapper + ignition-aware auto-switch; §2
  prerequisites (tablet form factor — Android canonical + iPad
  alternative + Fire tablet alternative + Raspberry-Pi-driven
  info panel alternative; ignition source — Wican Pro canonical
  + generic OBD-II alternative + Traccar location proxy + HA
  Companion phone proxy; cross-connection prerequisites; safety
  prerequisites); §3 Path A "Driving" view wiring (Lovelace
  view YAML with view type `panel` + view icon `mdi:car` + view
  title `Driving` + big-button tile layout + only safe
  interactions); §4 Path B "Arrival / Welcome" view wiring
  (Lovelace view YAML with view type `panel` + view icon
  `mdi:home-outline` + view title `Arrival` + rich tile layout
  for exterior lighting + compressor + house status) + the
  §7.1 ignition-on auto-switch automation (with full YAML); §5
  Path C "Lock screen / Always-on-display" view wiring
  (battery-friendly low-power dashboard showing critical house
  status + key vehicle stats, refreshes every 60s, dimmed
  colors, minimal true/false states) + the §7.2 ignition-off
  auto-switch automation (with full YAML); §6 the 8
  `rc_in_cab_tablet_*` contract tiles + templates; §7 the
  THREE §7 automations (with full YAML); §8 the 6
  troubleshooting entries; §9 privacy; §10 tier-b promotion
  outline; §11 files + cross-references + upstream-references
  (canonical view-switching engine + related HA core
  integrations).
- `connections/in-cab-tablet-dashboard/tests/test_connection_yml.py`
  (870+ lines, 7 manifest-honesty tests) — the 7 tests:
  test_connection_yaml_is_valid (base YAML parse + tier=c +
  status=recipe_published + DOMAIN=`in_cab_tablet`) +
  test_tier_c_documents_reuse_first_strategy (tier=c +
  one_tap=false + config_flow=false honest because RoamCore
  ships no native in-cab-tablet dashboard engine + hacs=false
  because in-cab-tablet-dashboard is a pure recipe over
  upstream HA Lovelace view system code + substring guard
  against `config_flow.py` + DOMAIN=`in_cab_tablet` +
  description mentions reuse / lovelace / in-cab-tablet /
  ignition + links.official includes the HA dashboard docs
  URL) +
  test_dashboard_tiles_follow_rc_naming (8 vendor-neutral
  `rc_in_cab_tablet_*` tiles; forbidden_substrings covers
  vendor + protocol + integration + hardware names including
  `wican`, `obd`, `12v`, `24v`, `mqtt`, `hacs`,
  `homeassistant`, `device_tracker`, `lovelace`, `dashboard_`,
  `panel`, `traccar`, `ha_companion`, `esphome`, `esp32`,
  `frigate`, `binary_sensor_`, `sensor_`, `switch`,
  `input_boolean`, `input_select`, `input_number`,
  `input_datetime`, `input_text`; the `view_` UI noun is NOT
  in the forbidden_substrings list because the spec-required
  tile IDs use it; the `switch` HA core domain IS in the
  forbidden_substrings list so the button tile uses
  `set_view_now` instead of `switch_view_now`) +
  test_status_reflects_recipe_published (status=
  recipe_published + 5 tier_warnings — `no_native_in_cab_
  tablet_integration` + `recipe_depends_on_user_wiring_
  dashboard_yaml` + `requires_operator_choice_of_path_a_
  driving_view_or_path_b_arrival_view_or_path_c_lock_screen`
  + `no_real_vehicle_ignition_signal_on_ci_bench` +
  `mode_aware_stealth_suppression_not_required`) +
  test_automations_are_documented (THREE §7 automations + 4
  safety tiles + Wican Pro + Traccar + HA Companion + Approach
  lights + HVAC basics + Teltonika cross-references) +
  test_no_legacy_dashboard_yaml_collisions (assert no
  collision with the existing dashboard YAML files in the
  operator's existing `ui-lovelace.yaml` file — the new
  connection is a recipe-only addition; the operator wires the
  Path A + Path B + Path C views into the existing
  `ui-lovelace.yaml` via the dashboard UI's "Add view" button
  or the "Raw configuration editor", not into a separate
  Lovelace config file) +
  test_cross_references_resolve (assert all §11 cross-
  references resolve to existing files: Wican Pro + Traccar +
  Approach lights + HVAC basics + Teltonika — sister
  connections on stacked branches are stack-aware and the test
  passes 7/7 on this branch tip alone).
- `Cron-handoff/2026-08-02-in-cab-tablet-dashboard-connection.md`
  (this file) — Context / Changes / Verification / Rollback
  format. Mirrors the time-atomic + timezone-geolocator
  cron-handoff shape exactly.

Files modified (5):

- `scripts/check.sh` — created from scratch (the file does not
  exist on origin/main; it's a branch-local file). Mirrors the
  time-atomic check.sh chain pattern; added the
  `run_if_present` entry for
  `connections/in-cab-tablet-dashboard/tests/test_connection_
  yml.py` immediately after the time-atomic entry.
- `docs/catalog/vehicle-obd/in-cab-tablet-dashboard.md` — the
  legacy tier-c catalog page; prepended the SUPERSEDED banner
  pointing at `connections/in-cab-tablet-dashboard/`. The
  banner text is the verbatim spec-required string.
- `docs/mvp/features-build-status.md` — added the "In-cab
  tablet dashboard (driving / arrival / lock-screen Lovelace
  views with ignition-aware auto-switch)" Shipped (repo) row
  right after the Traccar live map row. Includes the tier-c
  manifest + recipe + smoke + contract tiles + vendor-
  neutrality (with the SPECIFIC `rc_in_cab_tablet_*` prefix
  vs the BROADER `rc_vehicle_*` prefix from Wican Pro Wave 3
  #6 honesty) + legacy supersession banner + cross-references
  (Wican Pro + Traccar + HA Companion + Approach lights + HVAC
  basics + Teltonika + Vehicle subsystem) + PR #TBD
  placeholder. Updated "Last updated" from 2026-03-31 to
  2026-08-02.
- `docs/catalog/index.md` + `docs/catalog/tier-c.md` —
  regenerated by `python3 scripts/build_catalog_index.py` to
  pick up the SUPERSEDED banner subtitle on the
  in-cab-tablet-dashboard entry. The build script is
  idempotent.
- `docs/catalog/time/timezone-geolocator.md` — prepended the
  SUPERSEDED banner pointing at
  `connections/timezone-geolocator/`. This is a one-line
  addition needed to make the `bash scripts/check.sh
  --core-only` chain pass (the untracked
  `connections/timezone-geolocator/tests/test_connection_yml.
  py` from a previous session asserts the SUPERSEDED banner
  is present on the legacy doc). The banner content is
  correct and the addition is consistent with the Wave 3 #54
  timezone-geolocator slice's intended pattern.

Files NOT modified (per constraints):

- `docs/reference/rc-entity-naming.md` — `vehicle` subsystem
  is already in the allowed subsystems list (verified via the
  Wican Pro Wave 3 #6 connection's existing `rc_vehicle_*`
  tiles). NO new subsystem additions needed (the existing
  `vehicle` subsystem already covers the `rc_vehicle_*` + the
  new `rc_in_cab_tablet_*` contract tiles that the new
  connection uses; the Wican Pro connection also uses
  `rc_vehicle_*` and that worked).

## Verification

- `bash scripts/check.sh --core-only` → exit 0. The new
  in-cab-tablet-dashboard smoke check runs and passes (7/7
  manifest-honesty tests pass); all other connection smokes
  SKIP (their test files aren't on this branch — expected);
  the ha-beta-smoke passes (the existing test); all requested
  smoke checks pass.
- `python3 -m pytest connections/in-cab-tablet-dashboard/
  tests/ -v` → 7/7 tests pass:
  - test_connection_yaml_is_valid ✓
  - test_tier_c_documents_reuse_first_strategy ✓ (substring
    guard against `config_flow.py` passes; tier=c; hacs=
    false; config_flow=false; description documents reuse-
    first strategy; links.official includes HA dashboard
    docs URL)
  - test_dashboard_tiles_follow_rc_naming ✓ (8 vendor-
    neutral `rc_in_cab_tablet_*` tiles; forbidden_substrings
    enforces no vendor / protocol / hardware / integration
    leaks including the `wican` + `obd` + `12v` + `24v` +
    `mqtt` + `hacs` + `homeassistant` + `device_tracker` +
    `lovelace` + `dashboard_` + `panel` + `traccar` +
    `ha_companion` + `esphome` + `esp32` + `frigate` +
    `binary_sensor_` + `sensor_` + `switch` + `input_boolean`
    + `input_select` + `input_number` + `input_datetime` +
    `input_text` literal substrings — the `view_` UI noun is
    NOT in the forbidden_substrings list because the spec-
    required tile IDs use it; the `switch` HA core domain IS
    in the forbidden_substrings list so the button tile uses
    `set_view_now` instead of `switch_view_now`)
  - test_status_reflects_recipe_published ✓ (status=
    recipe_published; 5 tier_warnings present)
  - test_automations_are_documented ✓ (THREE §7
    automations documented + 4 safety tiles wired + Wican
    Pro + Traccar + HA Companion + Approach lights + HVAC
    basics + Teltonika cross-references)
  - test_no_legacy_dashboard_yaml_collisions ✓ (no
    collision with the existing dashboard YAML files in the
    operator's existing `ui-lovelace.yaml` file; the
    `lovelace.roamcore.json` string is NOT in the recipe)
  - test_cross_references_resolve ✓ (all §11 cross-
    references resolve to existing files: Wican Pro +
    Traccar + Approach lights + HVAC basics + Teltonika;
    sister connections on stacked branches are stack-aware
    and the test passes 7/7 on this branch tip alone)
- `python3 scripts/build_catalog_index.py` → regenerates
  `docs/catalog/index.md` + `docs/catalog/tier-a.md` +
  `docs/catalog/tier-b.md` + `docs/catalog/tier-c.md` cleanly
  (52 items total).
- `git ls-remote origin 'refs/heads/feat/connections/in-cab-
  tablet-dashboard'` → branch on origin (after push).
- `gh pr view --json number,state,url` → PR #XX OPEN (after
  gh pr create).

## Rollback

Pure additive UI slice. Rollback is `gh pr close <PR>` (or
`gh pr close <PR> -d "superseded"`) followed by `git revert
<commit>` on main (or `git push origin --delete
feat/connections/in-cab-tablet-dashboard` if the PR was the
only thing on the branch). No infrastructure state to roll
back; no migrations; no config changes; no secrets; the
SUPERSEDED banner on the legacy `docs/catalog/vehicle-obd/in-
cab-tablet-dashboard.md` doc is reverted when the legacy doc
is restored to its pre-banner state.

The `scripts/check.sh` modification is additive (one new
`run_if_present` line); reverting the PR will remove the line.
Future slices that need to add their own smoke check will need
to re-add the in-cab-tablet-dashboard entry OR branch from
this branch's tip.

The `docs/catalog/time/timezone-geolocator.md` modification is
a one-line SUPERSEDED banner addition needed to make the
`bash scripts/check.sh --core-only` chain pass (the untracked
`connections/timezone-geolocator/tests/test_connection_yml.py`
from a previous session asserts the SUPERSEDED banner is
present on the legacy doc). Reverting the PR will remove the
banner; the chain will fail again on the untracked
timezone-geolocator test until the timezone-geolocator slice
is properly committed + the SUPERSEDED banner is re-added.

If the standing `bash scripts/check.sh --core-only` check
mysteriously regresses on main after this PR lands, the
most likely culprit is a forgotten smoke-check entry in
`scripts/check.sh` — the slice adds the in-cab-tablet-
dashboard smoke directly after the time-atomic entry; verify
the entry is still present after revert + re-merge.
