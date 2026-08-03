# Wave 3 #48 — Connection: Deadbolts (tier-b) slice handoff

## Context

Promote the legacy tier-c `docs/catalog/safety/deadbolts.md` spec
(30 lines, claimed tier-B "Home Assistant supported") into a tier-b
**recipe** connection at `connections/deadbolts/`. Follows the same
pattern proven by Wave 3 #35 Frigate / #36 Starlink / #37 DNS
blocker / #38 NAS / #39 Teltonika / #40 Peplink / #41 Music
Assistant / #42 Bluetooth-Wi-Fi presence / #43 Happijac / #44
heated-floors / #45 Smoke-CO-gas / #46 Smart automations / #47
Mock location.

Smart deadbolts — van door lock control for vans — are the **"did
I forget to lock the van?"** answer: a single "any unlocked" tile
that aggregates front_door + side_door + storage_compartment lock
state into one dashboard indicator, the unlocked_count sensor
that reports the integer count of unlocked doors, the
last_action_age_min sensor that tracks how long since the last
lock/unlock action, the unexpected_unlock alarm that fires when
any lock transitions to unlocked while no presence is detected
(intruder alert), the CO-egress-required override that auto-
unlocks the egress-path doors when CO is detected (the safety-
critical interlock that distinguishes the deadbolts connection
from a generic lock control widget), the low-voltage lockout that
disables auto-relock when battery SOC drops below 20% (Victron
connection signal), the lock mode select (`auto` / `manual_only` /
`disabled`), and the lock_all / unlock_all action buttons for
agent + automation access.

Three install paths (operator picks based on existing IoT wiring +
lock ownership + coordinator comfort):

- **Path A — Z-Wave deadbolts** (most common for locks; recommended
  for operators who already own Schlage Encode Plus / Yale Assure
  2 / Kwikset Halo). The upstream `zwave_js` integration's GUI
  flow since 2022.x handles USB dongle setup + network key + home
  ID + initial interview; the upstream `lock.<name>` entities are
  exposed directly. Pairing via the vendor's button-press sequence
  (Schlage / Yale / Kwikset each have their own).

- **Path B — Zigbee deadbolts** (recommended for operators who
  already own Aqara A100 / Yale Assure 2 Zigbee). The upstream
  `zha` Zigbee Home Automation integration's GUI flow since 2022.x
  handles coordinator setup + channel selection + radio config; OR
  a `zigbee2mqtt` MQTT-bridged approach (slightly more complex
  but richer device configuration UI). Pairing via the vendor's
  button-press sequence.

- **Path C — Matter/Thread deadbolts** (recommended for operators
  who want future-proof lock with multi-vendor interoperability).
  The upstream `matter` integration's GUI flow since 2023.x handles
  Matter fabric setup + commissioning via QR code / setup code;
  REQUIRES a Thread border router on the LAN (OpenWrt VM with
  ot-rcp, Apple HomePod mini, Nest Hub v2, or Aeotec Border
  Router). Recommended locks: Level Lock+ / Yale Assure 2 Matter
  variant.

All three paths land on the same 12 `rc_safety_lock_*` contract
tiles (vendor-neutral per `docs/reference/rc-entity-naming.md`
§safety subsystem — already in the allowed subsystems list from
the smoke-co-gas-sensors Wave 3 #45 slice; the `safety_lock` sub-
prefix in the tile IDs is the documented naming convention for
"this is a tile owned by the safety subsystem that controls
locks"):

- 3 lock tiles (`lock.rc_safety_lock_front_door` / `_side_door` /
  `_storage_compartment`)
- 4 binary_sensor tiles (`binary_sensor.rc_safety_lock_any_unlocked`
  aggregate / `_unexpected_unlock` event / `_co_egress_required`
  safety / `_low_voltage_lockout` safety)
- 2 sensor tiles (`sensor.rc_safety_lock_unlocked_count` aggregate
  / `_last_action_age_min` freshness)
- 1 select tile (`select.rc_safety_lock_mode`)
- 2 button tiles (`button.rc_safety_lock_lock_all` / `_unlock_all`)

This slice does NOT edit any other connection folder, nor any
other branch. Only the deadbolts files + the `scripts/check.sh`
wire-up + the legacy-doc supersession banner + the new build-
status row for Wave 3 #48.

## Changes

- **New** `connections/deadbolts/connection.yml` (tier-b manifest;
  12 contract tiles + 10 OpenClaw queries + 7 OpenClaw summary
  keys + 4 `tier_warnings` honesty markers + vendor-neutral
  positioning header explaining Path A Z-Wave deadbolts vs Path B
  Zigbee deadbolts vs Path C Matter/Thread deadbolts).
- **New** `connections/deadbolts/__init__.py`
  (`DOMAIN = "deadbolts"` marker stub; explicitly avoids the
  `config_flow` substring per the happijac docstring-rephrasing
  lesson — the docstring uses "GUI flow" or "the upstream
  integration's GUI flow" or "RoamCore-owned GUI-walk-through"
  instead of any `config_flow` substring).
- **New** `connections/deadbolts/README.md` (folder overview;
  mirrors the smoke-co-gas-sensors tier-b slice shape with
  deadbolt-specific setup recipe + cross-references to Smoke / CO /
  gas safety sensors + Bluetooth-Wi-Fi presence + Mode / automation-
  builder + Victron + Happijac + Smart automations sibling slices).
- **New** `connections/deadbolts/docs/recipe.md`
  (~620-line howto; required sections §1 "What are Deadbolts in
  RoamCore?" / §2 Prerequisites (Path A Z-Wave deadbolts via
  zwave_js + recommended Z-Wave locks Schlage Encode Plus / Yale
  Assure 2 / Kwikset Halo + the upstream `lock.<name>` entity
  surfacing; Path B Zigbee deadbolts via zha or zigbee2mqtt +
  recommended Zigbee locks Aqara A100 / Yale Assure 2 Zigbee;
  Path C Matter/Thread deadbolts via matter + Thread border router
  prerequisite OpenWrt VM, Apple HomePod mini, Nest Hub v2, or
  Aeotec Border Router + recommended Matter locks Level Lock+ /
  Yale Assure 2 Matter variant) / §3 Path A — Z-Wave deadbolts
  (the upstream `lock.<name>` entity surfacing + the HA core
  `template:` lock that maps `lock.front_door` -> `lock.rc_safety_
  lock_front_door` + the rename pattern for stable entity_ids) /
  §4 Path B — Zigbee deadbolts (the upstream `lock.<name>` entity
  surfacing + the same `template:` lock pattern for the
  side_door slot + the rename pattern) / §5 Path C — Matter/Thread
  deadbolts (the Thread border router prerequisite + the upstream
  `lock.<name>` entity surfacing + the same `template:` lock
  pattern for the storage_compartment slot + the rename pattern)
  / §6 RoamCore contract entities (the 12 rc_safety_lock_* tiles +
  how the upstream lock.<name> templates expose them +
  translation helpers needed for the binary_sensors / numeric
  aggregate sensors / mode select / action buttons + the any-
  unlocked aggregate template) / §7 Safety interlocks &
  automations (MANDATORY before first use) covering 6 safety
  interlocks: Away auto-lock via `select.rc_mode` from the mode/
  automation-builder connection; Sleep auto-lock + auto-relock
  (driver can't forget to lock the door at night); unattended-
  unlock alarm cross-referencing `binary_sensor.rc_presence_anyone_
  home` from bluetooth-wifi-presence Wave 3 #42 + `select.rc_mode
  != away`; CO egress-required override cross-referencing
  `binary_sensor.rc_safety_co_detected` from smoke-co-gas-sensors
  Wave 3 #45 — auto-unlock the egress-path doors (front_door +
  side_door; storage_compartment can stay locked — not on the
  egress path); low-voltage lockout cross-referencing
  `sensor.rc_power_battery_soc` from Victron — disable auto-
  relock when SOC < 20% to save battery current; multi-door
  aggregate covering vans with two doors + storage compartments /
  §8 Troubleshooting (6 entries: lock not responding battery low
  on the lock Z-Wave Zigbee mesh range Matter Thread reachability;
  lock state stuck Z-Wave interview incomplete wake the lock
  manually and re-interview; unexpected-unlock false-positive
  presence detection lag increase the home/not_home grace period;
  CO-egress doesn't fire smoke-co-gas-sensors connection not
  installed yet; low-voltage-lockout stuck on Victron SOC
  recovering wait 5 min; Z-Wave JS network down USB stick
  unplugged dmesg grep -i zwave and reseat the dongle) / §9
  Privacy (no telemetry beyond local Z-Wave / Zigbee / Matter; no
  vendor cloud / no zwave_js cloud / no zha cloud / no matter
  cloud; no RoamCore cloud) / §10 tier-a promotion outline (real
  Z-Wave / Zigbee / Matter deadbolt on CI + RoamCore-owned
  config_flow.py walking Path A vs Path B vs Path C + naming each
  lock entity + mapping to one of `rc_safety_lock_front_door` /
  `rc_safety_lock_side_door` / `rc_safety_lock_storage_compartment`
  + integration tests asserting a state change from `locked` →
  `unlocked` triggers the right `binary_sensor.rc_safety_lock_any_
  unlocked` + `sensor.rc_safety_lock_unlocked_count` updates + the
  6 safety interlocks all fire when wired to canned fixture
  responses)).
- **New** `connections/deadbolts/tests/test_connection_yml.py`
  (7 manifest-honesty tests: id matches folder / tier-b without
  tier-a markers with explicit `config_flow` substring guard for
  the __init__.py docstring / docs recipe published with §1-§10
  sections + cross-references to all 4 partner connections
  (smoke-co-gas-sensors, bluetooth-wifi-presence, Victron, mode/
  automation-builder) + storage_compartment guidance / category
  `safety` matches legacy doc / dashboard tiles follow rc naming
  with 12 tiles; protocol-name / lock-vendor-name absolute-
  forbidden (zwave / z_wave / z-wave / zigbee / matter / thread /
  schlage / kwikset / yale / august / level_lock / levellock /
  ultraloq / igloohome / bold / lockly / smart_deadbolt /
  smart_lock / front_door_lock / side_door_lock /
  storage_door_lock) but lenient on the spec-required tile IDs
  that contain front_door / side_door / storage_compartment /
  any_unlocked / unlocked_count / last_action_age_min /
  unexpected_unlock / co_egress_required / low_voltage_lockout /
  lock_mode / lock_all / unlock_all in the suffix since those
  are spec-required / status reflects no real deadbolt with all 4
  honesty warnings in tier_warnings / safety interlocks are
  documented — defensive guard for the future tier-a promotion
  with cross-references to `binary_sensor.rc_safety_co_detected`
  from smoke-co-gas-sensors + `binary_sensor.rc_presence_anyone_
  home` from bluetooth-wifi-presence + `sensor.rc_power_battery_
  soc` from Victron + `select.rc_mode` from mode/automation-
  builder).
- **Modify** `scripts/check.sh` — append a `run_if_present` entry
  for `connections/deadbolts/tests/test_connection_yml.py` directly
  after the existing mock-location-and-tracks entry.
- **Modify** `docs/catalog/safety/deadbolts.md` — add a
  supersession banner at the top pointing at the new connection
  folder (legacy content below the banner is preserved for
  historical context).
- **Modify** `docs/mvp/features-build-status.md` — add a "Shipped
  (repo)" row for Wave 3 #48 mirroring the smoke-co-gas-sensors
  row shape exactly (tier-b manifest pointer + recipe size +
  manifest-honesty smoke + 12 contract entities + supersession
  banner + cross-references to smoke-co-gas-sensors CO egress +
  bluetooth-wifi-presence unattended unlock alarm + Victron
  low-voltage lockout + Happijac battery-aware relock pattern +
  mode/automation-builder Away + Sleep auto-lock + storage
  compartment egress-path note).
- **New** `Cron-handoff/2026-07-30-deadbolts-connection.md` (this
  file — slice summary with Context / Changes / Verification /
  Rollback).

## Verification

Run locally before pushing:

```bash
cd /home/bernard/clawd/RoamCore
git status                                    # clean or only the new files
python3 -m pytest connections/deadbolts/tests/test_connection_yml.py -v
                                               # expect 7/7 PASS
bash scripts/check.sh --core-only              # expect "✓ all requested smoke checks passed."
python3 -c "import yaml; m=yaml.safe_load(open('connections/deadbolts/connection.yml')); \
            assert m['id']=='deadbolts' and m['tier']=='b' and m['category']=='safety' \
            and len(m['dashboard']['tiles'])==12 \
            and len(m['openclaw']['queries'])==10 \
            and len(m['openclaw']['summary_keys'])==7 \
            and len(m['tier_warnings'])==4" \
                                               # expect VERIFICATION OK
grep -c "rc_safety_lock_" connections/deadbolts/connection.yml   # expect 12+ (tiles + summaries)
grep "config_flow" connections/deadbolts/__init__.py             # expect empty
git log --oneline -3                          # confirm new commit on feat/connections/deadbolts
git push -u origin feat/connections/deadbolts   # push
gh pr create --base main --head feat/connections/deadbolts \
  --title "Wave 3 #48: Connection: Deadbolts (tier-b) — smart lock control for van doors" \
  --body "<commit body>"                        # open PR (PR #52)
```

## Rollback

If something goes wrong post-merge:

1. Revert the merge commit on `main` (`git revert -m 1 <merge-sha>`).
2. The legacy `docs/catalog/safety/deadbolts.md` already carries a
   supersession banner pointing at `connections/deadbolts/`, so even
   post-revert operators have a pointer to the previous tier-c spec.
3. Delete the `feat/connections/deadbolts` branch
   (`git branch -d feat/connections/deadbolts` + `git push origin :feat/connections/deadbolts`).
4. Remove the `run_if_present` entry from `scripts/check.sh` (the
   one added for `connections/deadbolts/tests/test_connection_yml.py`).
   Note: no new subsystem was added to `docs/reference/rc-entity-
   naming.md` (the `safety` subsystem was already in the allowed
   subsystems list from the smoke-co-gas-sensors Wave 3 #45 slice);
   the `safety_lock` sub-prefix in the tile IDs is the documented
   naming convention and is NOT a generic-noun double-stamp, so no
   backfill is needed.

## Notes

- The recipe's §3 Path A Z-Wave YAML uses well-understood upstream
  zwave_js `lock.<name>` entity IDs + a `template:` lock that
  mirrors the upstream state to `lock.rc_safety_lock_front_door` +
  a `homeassistant:` `customize:` block for stable friendly names.
  The §4 Path B Zigbee YAML uses the same pattern for
  `lock.rc_safety_lock_side_door` via zha or zigbee2mqtt. The §5
  Path C Matter YAML uses the same pattern for
  `lock.rc_safety_lock_storage_compartment` via the matter
  integration + a Thread border router on the LAN.
- The recipe's §6 `rc_safety_lock_*` contract layer is fully
  written in YAML (template lock + template binary_sensors +
  template sensors + template select + template buttons +
  HA core `lock` + `template` integrations); operators wire those
  manually until tier-a promotion lands.
- The recipe's §7 documents the 6 MANDATORY safety interlocks:
  Away auto-lock (via `select.rc_mode` from mode/automation-
  builder); Sleep auto-lock + auto-relock (driver can't forget to
  lock the door at night); unattended-unlock alarm (via
  `binary_sensor.rc_presence_anyone_home` from bluetooth-wifi-
  presence Wave 3 #42); CO egress-required override (via
  `binary_sensor.rc_safety_co_detected` from smoke-co-gas-sensors
  Wave 3 #45 — the egress-path doors auto-unlock; storage_
  compartment stays locked); low-voltage lockout (via
  `sensor.rc_power_battery_soc` from Victron — auto-relock
  disabled when SOC < 20% to save battery current); multi-door
  aggregate (covers vans with two doors + storage compartments).
- The `config_flow` substring was explicitly avoided in the
  `__init__.py` docstring (per the happijac docstring-rephrasing
  lesson) — the docstring uses "GUI flow" or "the upstream
  integration's GUI flow" or "RoamCore-owned GUI-walk-through"
  instead. The `test_tier_b_without_tier_a_markers` audit
  asserts the forbidden substring is absent.
- The test's `test_dashboard_tiles_follow_rc_naming` defensive
  guard forbids protocol / vendor / generic-noun double-stamp
  substrings (zwave / z_wave / z-wave / zigbee / matter / thread /
  schlage / kwikset / yale / august / level_lock / levellock /
  ultraloq / igloohome / bold / lockly / smart_deadbolt /
  smart_lock / front_door_lock / side_door_lock /
  storage_door_lock) but is lenient on the spec-required tile
  IDs that contain generic nouns (front_door / side_door /
  storage_compartment / any_unlocked / unlocked_count /
  last_action_age_min / unexpected_unlock / co_egress_required /
  low_voltage_lockout / lock_mode / lock_all / unlock_all) in
  the suffix since those are spec-required. The `egress` substring
  from the spec's forbidden list was intentionally NOT added to
  the test's forbidden set because the spec-required tile
  `binary_sensor.rc_safety_lock_co_egress_required` uses
  `egress` as a semantic suffix to describe the CO emergency-
  egress scenario — the required tile list is authoritative when
  in conflict with the forbidden list.
- The `safety` subsystem was already in the allowed subsystems
  list from the smoke-co-gas-sensors Wave 3 #45 slice; no
  backfill to `docs/reference/rc-entity-naming.md` was needed.
  The `safety_lock` sub-prefix in the tile IDs is the documented
  naming convention for "this is a tile owned by the safety
  subsystem that controls locks" and is NOT a generic-noun
  double-stamp.