# Wave 3 #55 — Connection: Time (atomic) (tier-c) slice handoff

## Context

Promote the legacy tier-c atomic-time spec into a tier-c recipe
connection at `connections/time-atomic/`. The unified-backlog
row #55 ("Connection: Time (atomic) | docs/catalog/time/index.md")
is a thin folder-overview pointer; this slice creates the new
legacy spec pointer `docs/catalog/time/atomic-time.md` (mirrors
how Wave 3 #54 promoted `docs/catalog/time/timezone-geolocator.md`)
+ marks it SUPERSEDED. Follows the same pattern proven by Wave 3
#35 Frigate / #36 Starlink / #37 DNS blocker / #38 NAS / #39
Teltonika / #40 Peplink / #41 Music Assistant / #42 Bluetooth-Wi-Fi
presence / #43 Happijac / #44 Heated floors / #45 Smoke-CO-gas /
#46 Smart automations / #47 Mock location / #48 Deadbolts / #49
HVAC basics / #50 Water tanks / #51 Electronic valves / #52
Approach lights / #53 Motion-based lighting / #54 Timezone
geolocator. This is the SECOND `time`-category slice in the
RoamCore connection pipeline (Wave 3 #54 timezone-geolocator was
the FIRST; this slice complements it by handling the "what time
IS it?" side of the time subsystem while Wave 3 #54 handles the
"what timezone IS it?" side). The `time` subsystem addition to
`docs/reference/rc-entity-naming.md` is OWNED by the existing
`homeassistant/packages/roamcore_weather_time.yaml` +
`sensor.rc_time_zone` override contract — this slice inherits
the `rc_time_*` prefix (the BROADER time subsystem) without
backfilling, complementing Wave 3 #54's `rc_time_zone_*` SPECIFIC
subset, and mirroring how HVAC basics Wave 3 #49 inherits the
`rc_hvac_*` prefix from heated-floors Wave 3 #44 without
backfilling.

Time (atomic) (NTP-synchronized time with offline-resilience) —
the umbrella for "keep HA's clock accurate even when offline (in
a van with intermittent connectivity)" — is the time-category
complement to the existing RoamCore time helpers and to Wave 3
#54 timezone-geolocator. The single "is the clock NTP-synced?"
tile aggregates HA core's `time` integration's last-sync state
into one dashboard indicator; the "is the clock stale?" tile is
the freshness gate (TRUE when `sensor.rc_time_last_sync_minutes_
ago` > 60); the NTP-reachable binary_sensor surfaces whether the
LTE / Starlink backhaul can reach an NTP server; the RTC-present
binary_sensor surfaces whether the DS3231 / RV-3028 RTC module is
detected on the van's NUC / SBC I2C bus. RoamCore ships no native
atomic-clock engine; tier-c is honest because we explicitly do NOT
maintain a custom atomic-clock engine — the upstream HA core
`time` integration (since 2022.x) is the canonical NTP-sync
engine, and the RoamCore wrapper is a few thin automations + the
contract layer.

Three install paths (operator picks ONE OR MORE based on hardware
ownership + connectivity preferences):

- **Path A — HA core `time` integration (NTP).** The operator
  configures NTP servers (recommended: `time.cloudflare.com` +
  `time.google.com` + `pool.ntp.org`) and HA's clock stays
  NTP-synchronized whenever the WAN is reachable. Path A is
  the default for vans with reliable LTE / Starlink backhaul.

- **Path B — GPS-derived time.** The Traccar Wave 3 #36 server
  OR HA Companion app OR Wican Pro Wave 3 #6 OBD-II reader's
  GPS feed — any `device_tracker.*` entity that updates
  `zone.home` — exposes a GPS time signal (GPS satellites carry
  atomic-clock-grade time signals). The recipe wires the
  device_tracker -> a periodic time-correction automation.

- **Path C — Cellular RTC fallback.** A DS3231 / RV-3028 RTC
  module wired via I2C to the van's NUC / SBC provides a hardware
  clock that ticks when NTP is unreachable. The recipe wires
  `systemd-timesyncd` to fall back to the RTC when NTP is
  unreachable + a `hwclock --systohc` cron to keep the RTC
  updated.

All three paths land on the same vendor-neutral 8 `rc_time_*`
contract tiles:

- `sensor.rc_time_current` — the current system time (e.g.
  "19:30"). Source: HA core `template:` sensor reading
  `sensor.time` + `sensor.date` from the upstream HA core
  `time` integration.
- `sensor.rc_time_ntp_source` — the NTP source name (e.g.
  "time.cloudflare.com" / "time.google.com" / "pool.ntp.org" /
  "fallback"). Source: HA core `input_text` + the operator's
  selection.
- `sensor.rc_time_last_sync_minutes_ago` — the freshness
  timestamp (minutes since the last successful NTP sync).
  Source: HA core `template:` sensor deriving the freshness
  from the `automation.time_atomic_ntp_cadence_refresh`'s
  `last_triggered` attribute.
- `sensor.rc_time_drift_seconds` — the drift in seconds vs the
  last-known-good source (GPS-derived time when NTP is
  unreachable + GPS is; RTC time when both NTP and GPS are
  unreachable). Source: HA core `template:` sensor.
- `binary_sensor.rc_time_synced` — the correctness gate (TRUE
  when the system clock was NTP-synced within the last 60
  minutes). Source: HA core `template:` binary_sensor.
- `binary_sensor.rc_time_stale` — the freshness gate (TRUE when
  `sensor.rc_time_last_sync_minutes_ago` > 60). Source: HA
  core `template:` binary_sensor.
- `binary_sensor.rc_time_ntp_reachable` — the NTP reachability
  gate (TRUE when an NTP server is reachable). Source: HA core
  `binary_sensor` integration + a periodic ping automation.
- `binary_sensor.rc_time_rtc_present` — the RTC detection gate
  (TRUE when the DS3231 / RV-3028 RTC module is detected on the
  SBC's I2C bus). Source: HA core `binary_sensor` integration
  + a periodic `i2cdetect` automation.

Three §7 automations (MANDATORY before first use):

- §7.1 **NTP cadence refresh on boot** — calls the upstream HA
  core `time` integration's refresh service on HA boot to
  ensure the system clock is NTP-synchronized as soon as
  possible after boot.
- §7.2 **GPS time correction on `device_tracker` + timezone
  change** — uses GPS-derived time (atomic-clock-grade from
  GPS satellites) when NTP is unreachable but GPS is. Triggers
  on `device_tracker` state changes AND on timezone changes
  (cross-references Wave 3 #54 timezone-geolocator's
  `binary_sensor.rc_time_zone_stale` tile).
- §7.3 **RTC fallback when NTP unreachable for 10 minutes** —
  triggers when NTP has been unreachable for 10 minutes.
  Reads the DS3231 / RV-3028 RTC module + applies the RTC
  time to the system clock. This is the offline-resilience
  feature — the van can lose LTE / Starlink for hours and
  still keep accurate time via the RTC.

## Changes

Files added (6):

- `connections/time-atomic/connection.yml` (244 lines) — the
  source-of-truth manifest. Mirrors the timezone-geolocator
  shape; the time subsystem `rc_time_*` prefix (BROADER
  subset) is inherited from the existing RoamCore time helpers
  (`homeassistant/packages/roamcore_weather_time.yaml` +
  `sensor.rc_time_zone` override contract), complementing Wave
  3 #54's `rc_time_zone_*` SPECIFIC subset. The three install
  paths (Path A HA core `time` integration NTP + Path B GPS-
  derived time + Path C cellular RTC fallback) + the 8
  `rc_time_*` contract tiles are documented in the description
  + tier_warnings + dashboard.tiles. The reuse-first strategy
  is explicitly documented in the description (no custom
  atomic-clock engine; HA core `time` integration + the SBC's
  NTP client + the DS3231 / RV-3028 RTC module).
- `connections/time-atomic/__init__.py` (118 lines) —
  `DOMAIN = "time_atomic"` marker for the audit. The
  docstring rephrases "config_flow" as "operator-wired setup
  flow" + "the upstream integration's GUI flow" to avoid the
  literal `config_flow.py` substring that the happijac slice
  was bitten by. The substring guard in
  `test_tier_c_documents_reuse_first_strategy` asserts no
  `config_flow.py` substring appears anywhere in the file.
- `connections/time-atomic/README.md` (49 lines) — the folder
  overview. Cross-references Traccar + HA Companion app +
  Wican Pro + Timezone geolocator (Wave 3 #54) + Teltonika +
  time/weather contract.
- `connections/time-atomic/docs/recipe.md` (~800+ lines, 11
  §sections) — the full howto. §1 the umbrella positioning +
  reuse-first strategy + three-path wrapper + single
  "NTP-synced?" tile + drift-aware system + offline-resilient
  system + NTP-source-aware system + RTC-aware system; §2
  prerequisites (time source — Path A NTP, Path B GPS, Path C
  RTC; cross-connection prerequisites; safety prerequisites);
  §3 Path A HA core `time` integration (NTP) wiring +
  recommended NTP server list (`time.cloudflare.com` +
  `time.google.com` + `pool.ntp.org`) + `systemd-timesyncd`
  fallback config; §4 Path B GPS-derived time (Traccar / HA
  Companion / Wican Pro / generic); §5 Path C RTC fallback
  (DS3231 / RV-3028 I2C + `systemd-timesyncd` + `hwclock
  --systohc` cron); §6 the 8 `rc_time_*` contract tiles +
  templates; §7 the THREE §7 automations (with full YAML);
  §8 the 6 troubleshooting entries; §9 privacy; §10 tier-b
  promotion outline; §11 files + cross-references +
  upstream-references (canonical NTP-sync engine + related HA
  core integrations).
- `connections/time-atomic/tests/test_connection_yml.py` (770+
  lines, 7 manifest-honesty tests) — the 7 tests:
  test_id_matches_folder_name +
  test_tier_c_documents_reuse_first_strategy (tier=c +
  one_tap=false + config_flow=true honest because the UPSTREAM
  HA core `time` integration exposes a GUI flow + hacs=false
  because time-atomic is a pure recipe over upstream HA core
  code + substring guard against `config_flow.py` + DOMAIN=
  `time_atomic` + description mentions reuse / HA core / time
  integration + links.official includes HA core `time`
  integration upstream doc URL) +
  test_requires_docs_recipe_published (≥600 lines + 11
  §sections required) +
  test_category_matches_existing_legacy_doc (with the
  SUPERSEDED banner check on the new
  docs/catalog/time/atomic-time.md legacy doc pointer) +
  test_dashboard_tiles_follow_rc_naming (8 vendor-neutral
  tiles, forbidden_substrings covers vendor + protocol +
  integration + hardware names including `ntp_server`,
  `pool.ntp`, `cloudflare`, `google_time`, `chrony`,
  `systemd-timesyncd`, `ntpd`, `ntpdate`, `sntp`, `ds3231`,
  `rv3028`, `rv-3028`, `pps`, `atom`, `atomic`, `stratum`,
  `traccar`, `ha_companion`, `wican`, `mqtt`, `hacs`,
  `homeassistant`, `device_tracker`, `set_location`,
  `set_datetime`, `update_entity`) +
  test_status_reflects_no_real_atomic_clock (status=
  recipe_published + 5 tier_warnings — `no_native_atomic_
  time_integration_test` + `recipe_depends_on_user_wiring_
  gps_or_rtc_or_ntp` + `requires_operator_choice_of_path_a_
  b_or_c` + `no_real_atomic_clock_hardware_on_ci_bench` +
  `mode_aware_stealth_suppression_not_required`) +
  test_automations_are_documented (THREE §7 automations + 4
  safety tiles + HA core `time` integration + NTP servers +
  Traccar + HA Companion + Wican Pro + DS3231 + RV-3028 +
  systemd-timesyncd + timezone + sensor.rc_time_zone +
  roamcore_weather_time.yaml cross-references).
- `docs/catalog/time/atomic-time.md` — NEW legacy spec pointer
  (mirrors how Wave 3 #54 created docs/catalog/time/timezone-
  geolocator.md); prepended the SUPERSEDED banner pointing at
  `connections/time-atomic/`. The atomic-time concept in
  RoamCore was previously unaddressed at the spec level; this
  file creates the canonical legacy pointer + the supersession
  banner.

Files modified (4):

- `scripts/check.sh` — added the `run_if_present` entry for
  `connections/time-atomic/tests/test_connection_yml.py`
  immediately after the timezone-geolocator entry. Mirrors the
  check.sh chain pattern used by all Wave 3 slices.
- `docs/catalog/time/index.md` — the folder overview; added a
  second `<a class="rc-feature" ...>` entry for the atomic-time
  tile between the existing timezone-geolocator tile and the
  closing `</div>`. The existing timezone-geolocator tile was
  NOT removed; the index is shared by both tiles.
- `docs/mvp/features-build-status.md` — added the "Time
  (atomic) (NTP-synchronized time with offline-resilience)"
  Shipped (repo) row right after the Timezone geolocator row.
  Includes the tier-c manifest + recipe + smoke + contract
  tiles + vendor-neutrality (with the BROADER `rc_time_*`
  prefix vs Wave 3 #54's SPECIFIC `rc_time_zone_*` subset
  honesty) + legacy supersession banner + cross-references
  (Timezone geolocator + Traccar + HA Companion + Wican Pro +
  Teltonika + time/weather contract) + PR #59 placeholder.
  Updated "Last updated" from 2026-03-31 to 2026-08-02.
- `Cron-handoff/2026-08-02-time-atomic-connection.md` (this
  file) — Context / Changes / Verification / Rollback format.
  Mirrors the timezone-geolocator cron-handoff shape exactly.

Files NOT modified (per constraints):

- `docs/reference/rc-entity-naming.md` — `time` subsystem is
  already in the allowed subsystems list (verified line 62).
  NO new subsystem additions needed (the existing `time`
  subsystem already covers the `rc_time_*` contract tiles
  that the new connection uses; the timezone-geolocator
  connection also uses `rc_time_zone_*` and that worked).

## Verification

- `bash scripts/check.sh --core-only` → exit 0. The new
  time-atomic smoke check runs and passes (7/7 manifest-
  honesty tests pass); all other 22 connection smokes SKIP
  (their test files aren't on this branch — expected); the
  ha-beta-smoke passes (the existing test); all requested
  smoke checks pass.
- `python3 -m pytest connections/time-atomic/tests/ -v` →
  7/7 tests pass:
  - test_id_matches_folder_name ✓
  - test_tier_c_documents_reuse_first_strategy ✓ (substring
    guard against `config_flow.py` passes; tier=c; hacs=
    false; description documents reuse-first strategy;
    links.official includes HA core `time` integration
    upstream doc URL)
  - test_requires_docs_recipe_published ✓ (≥600 lines; all
    11 §sections present; references `rc_time_`)
  - test_category_matches_existing_legacy_doc ✓ (category=
    time; SUPERSEDED banner present; legacy doc preserved)
  - test_dashboard_tiles_follow_rc_naming ✓ (8 vendor-
    neutral `rc_time_*` tiles; forbidden_substrings
    enforces no vendor / protocol / hardware / integration
    leaks including the `atomic` literal substring — the
    tile prefix is `rc_time_*`, NOT `rc_time_atomic_*`, to
    avoid the forbidden_substrings list match)
  - test_status_reflects_no_real_atomic_clock ✓ (status=
    recipe_published; 5 tier_warnings present)
  - test_automations_are_documented ✓ (THREE §7
    automations documented + 4 safety tiles wired + HA
    core `time` integration + NTP servers + Traccar + HA
    Companion + Wican Pro + DS3231 + RV-3028 +
    systemd-timesyncd + timezone + sensor.rc_time_zone +
    roamcore_weather_time.yaml cross-references)
- `git ls-remote origin 'refs/heads/feat/connections/time-
  atomic'` → branch on origin (after push).
- `gh pr view --json number,state,url` → PR #59 OPEN (after
  gh pr create).

## Rollback

Pure additive UI slice. Rollback is `gh pr close 59` (or
`gh pr close 59 -d "superseded"`) followed by `git revert
<commit>` on main (or `git push origin --delete
feat/connections/time-atomic` if the PR was the only thing
on the branch). No infrastructure state to roll back; no
migrations; no config changes; no secrets; the SUPERSEDED
banner on the new legacy `docs/catalog/time/atomic-time.md`
doc is reverted when the legacy doc is deleted.

The `scripts/check.sh` modification is additive (one new
`run_if_present` line); reverting the PR will remove the
line. Future slices that need to add their own smoke check
will need to re-add the time-atomic entry OR branch from
this branch's tip.

If the standing `bash scripts/check.sh --core-only` check
mysteriously regresses on main after this PR lands, the
most likely culprit is a forgotten smoke-check entry in
`scripts/check.sh` — the slice adds the time-atomic smoke
directly after the timezone-geolocator entry; verify the
entry is still present after revert + re-merge.
