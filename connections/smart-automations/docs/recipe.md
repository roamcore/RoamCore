# Smart Automations — tier-b recipe connection

This is the full howto for the `connections/smart-automations/` tier-b
recipe connection. It walks through the 17 prebuilt RoamCore
automations (the canonical list lives at
[`docs/guides/smart-automations.md`](../../../docs/guides/smart-automations.md)
and is mirrored here with the per-automation prerequisite wiring +
the managed-marker audit + the contract-tile synthesis), explains
how RoamCore creates each automation in HA Core's `automation:`
domain with the `Managed by RoamCore Smart Automations v0.1` +
`key=<name>` + `hash=<template hash>` marker in the description,
documents the 25 `rc_safety_*` contract tiles (24
`rc_safety_automation_*` + `rc_safety_automations_*` summary tiles),
and outlines the §9 tier-a promotion path (a RoamCore-owned
automation engine + `config_flow.py` for the RoamCore UI "Smart
Automations" page + integration tests that assert enabling /
disabling a managed automation works via the HA Core API + the
managed-marker invariants hold).

## §1 What are Smart Automations in RoamCore?

Smart Automations are the **day-to-day convenience layer** of a
RoamCore van: 17 prebuilt Home Assistant automations positioned as:

- **17 prebuilt automations** — the full list is at `docs/guides/smart-automations.md` and mirrored in §4 below. They cover mode-aware transitions, power-aware responses, safety alerts, trip accounting, connectivity resilience, and bedtime reminders.

- **1-click enable / disable** — the operator enables each automation independently from `RoamCore → Settings → Smart Automations`. The enable-all-ready + disable-all buttons at the top of the page handle bulk operations; the per-automation `binary_sensor.rc_safety_automation_<name>` mirror tile shows whether each automation is enabled.

- **Safe + predictable** — each automation has well-defined prerequisites (the recipe §2 + §4 lists them per automation); the managed-marker audit (`Managed by RoamCore Smart Automations v0.1` + `key=<name>` + `hash=<template hash>`) detects if the operator has edited the automation and stops RoamCore from overwriting the operator's changes.

- **Fully native HA automations** — every automation lives in HA Core's `automation:` domain. The operator can open HA → Settings → Automations and edit them in place. RoamCore adds an audit + a contract-tile synthesis on top; it does not hide any automation logic.

- **Transparent** — no hidden automation engine. The recipe publishes the YAML for every automation; the operator can copy-paste any automation into their own `packages/` folder if they prefer not to use the RoamCore-managed enable/disable flow.

- **The managed-marker convention** — every RoamCore-installed automation has a description that starts with the literal string `Managed by RoamCore Smart Automations v0.1` + a `key=<name>` line + a `hash=<template hash>` line. The `template:` binary_sensor audit (recipe §3) reads each automation's description and mirrors its enable/disable state into the `binary_sensor.rc_safety_automation_<name>` contract tile. If the operator edits the description and loses the marker, RoamCore stops updating the logic but still allows enable/disable — the documented behavior from `docs/guides/smart-automations.md` "Editing" section.

## §2 Prerequisites

The operator MUST wire the upstream prerequisites BEFORE the 17
automations can fire. Each automation lists its prerequisites in §4
below; here is the consolidated list:

**HA Core:** 2023.8 or newer (the upstream `automation:` + `template:` + `button:` + `select:` domains expose a GUI config_flow since 2023.x; older HA versions will fail to load the `template:` binary_sensor audit).

**Per-automation prerequisites (from `docs/guides/smart-automations.md`):**

- `sensor.rc_power_battery_soc` + `binary_sensor.rc_power_shore_connected` (from the upcoming Victron `connections/victron/` recipe) — required for Low Battery Mode + Shore Power Connected + Shore Power Disconnected + Battery Full Alert + Battery Critical Alert.
- `script.rc_mode_set_stealth` + `script.rc_mode_set_auto` (from the upcoming mode/automation-builder `connections/mode-automation-builder/` recipe) — required for Night Mode.
- `script.rc_mode_set_camp` (from the mode/automation-builder recipe) — required for Low Battery Mode + Arrive at Camp.
- `script.rc_mode_set_travel` (from the mode/automation-builder recipe) — required for Depart Travel Mode.
- `sensor.rc_net_wan_status` + `binary_sensor.rc_net_internet_reachable` (from the upcoming Net `connections/net/` recipe) — required for Auto Internet Failover + Internet Recovery.
- `script.rc_openwrt_prefer_auto` (from the upcoming OpenWrt controls `connections/openwrt-controls/` recipe) — required for Auto Internet Failover.
- `script.rc_openwrt_restart_network` (from the OpenWrt controls recipe) — required for Internet Recovery.
- `sensor.rc_weather_temp_c` (from the Weather + time contract `homeassistant/packages/roamcore_weather_time.yaml`) — required for Freeze Protection.
- `sensor.rc_trip_distance_today_mi` + `sensor.rc_trip_time_today` (from the upcoming Traccar `connections/traccar/` recipe) — required for Daily Trip Log.
- `sensor.rc_power_inverter_temperature` (from the Victron recipe) — required for Inverter Overheat Alert.
- `sensor.rc_router_temperature` (from the OpenWrt controls recipe) — required for Router Overheat Alert.
- `sensor.rc_power_solar_power` (from the Victron recipe) — required for Solar is Crushing It.
- `sensor.rc_location_speed` (from the Traccar recipe) — required for Arrive at Camp + Depart Travel Mode.
- `binary_sensor.rc_level` + `sensor.rc_level_status` (from `homeassistant/packages/roamcore_level.yaml` + the upcoming leveling `connections/leveling/` recipe) — required for Bedtime Level Check.
- `input_select.rc_mode` (from the mode/automation-builder recipe) — required for Quiet Hours Reminder.

**Operator prerequisites:**

- The operator has HA Core 2023.8+ running.
- The operator has accepted the "Editing" caveat from `docs/guides/smart-automations.md` — RoamCore stops updating the logic if the operator edits an automation; only the enable/disable state is managed from that point forward.
- The operator has decided which of the 17 automations fit their van. The recipe §4 documents every automation; the operator is NOT required to enable all 17.

## §3 How the 17 automations are wired

RoamCore creates each automation via the HA Core config API. The
managed-marker convention is the audit backbone:

```yaml
# Managed by RoamCore Smart Automations v0.1
# key=<name>
# hash=<template hash>
# Do not edit above this line if you want RoamCore to keep this
# automation in sync. Editing below this line is fine; RoamCore
# will keep the enable/disable state managed but will stop
# updating the triggers / conditions / actions.

alias: "RoamCore - Night Mode"
description: |
  Managed by RoamCore Smart Automations v0.1
  key=night_mode
  hash=<template hash>

  At 23:00 sets RoamCore Mode to Stealth; at 07:00 sets it back to
  Auto. Requires script.rc_mode_set_stealth + script.rc_mode_set_auto.

trigger:
  - platform: time
    at: "23:00:00"
    id: "to_stealth"
  - platform: time
    at: "07:00:00"
    id: "to_auto"

condition: []

action:
  - choose:
      - conditions:
          - condition: trigger
            id: "to_stealth"
        sequence:
          - service: script.rc_mode_set_stealth
      - conditions:
          - condition: trigger
            id: "to_auto"
        sequence:
          - service: script.rc_mode_set_auto

mode: single
```

The audit `template:` binary_sensor that mirrors the automation's
enable/disable state into the contract layer:

```yaml
template:
  - binary_sensor:
      - name: "rc_safety_automation_night_mode"
        state: >-
          {{ is_state('automation.roamcore_night_mode', 'on') }}
        device_class: safety
        unique_id: rc_safety_automation_night_mode

      # ... and so on for all 17 automations, one template binary_sensor
      # per automation ...
```

The summary tiles:

```yaml
template:
  - sensor:
      - name: "rc_safety_automations_enabled_count"
        state: >-
          {{ states.binary_sensor
             | selectattr('attributes.device_class', 'defined')
             | selectattr('entity_id', 'match', 'binary_sensor.rc_safety_automation_*')
             | selectattr('state', 'eq', 'on')
             | list | length }}
        unit_of_measurement: "automations"

      - name: "rc_safety_automations_total_count"
        state: "{{ 17 }}"

      - name: "rc_safety_automations_missing_count"
        state: >-
          {{ states.binary_sensor
             | selectattr('entity_id', 'match', 'binary_sensor.rc_safety_automation_*')
             | selectattr('attributes.missing_dependencies', 'defined')
             | selectattr('attributes.missing_dependencies', 'ne', [])
             | list | length }}
        unit_of_measurement: "automations"

  - binary_sensor:
      - name: "rc_safety_automations_all_ready"
        state: >-
          {{ states('sensor.rc_safety_automations_missing_count') | int(0) == 0 }}
        device_class: safety

  - select:
      - name: "rc_safety_automations_view"
        options:
          - "all"
          - "enabled"
          - "missing"
          - "disabled"
        initial: "all"

  - button:
      - name: "rc_safety_automations_enable_all_ready"
        press:
          - service: automation.turn_on
            target:
              entity_id: >-
                {{ state_attr('sensor.rc_safety_automations_ready_list', 'entity_ids') }}

      - name: "rc_safety_automations_disable_all"
        press:
          - service: automation.turn_off
            target:
              entity_id: >-
                {{ state_attr('sensor.rc_safety_automations_all_list', 'entity_ids') }}
```

What happens when the operator edits one:

- If the operator edits the **triggers / conditions / actions** below the managed-marker comment block, RoamCore stops updating the logic but the enable/disable flow keeps working. The `binary_sensor.rc_safety_automation_<name>` mirror tile continues to track the HA automation's enable/disable state correctly because it reads `is_state('automation.roamcore_<name>', 'on')` which is independent of the trigger/action content.
- If the operator edits the **description** above the managed-marker comment block, RoamCore stops auditing the automation. The contract tile may go stale. Fix: re-enable the automation from the RoamCore UI which will re-create the marker.

## §4 The 17 built-in automations

The full canonical list lives at
[`docs/guides/smart-automations.md`](../../../docs/guides/smart-automations.md);
this section mirrors each automation with the RoamCore contract-tile
mapping + the prerequisite wiring + the managed-marker hash.

### §4.1 Night Mode (23:00 → Stealth; 07:00 → Auto)

- **Trigger:** time at 23:00 (to Stealth); time at 07:00 (to Auto).
- **Action:** calls `script.rc_mode_set_stealth` at 23:00; calls `script.rc_mode_set_auto` at 07:00.
- **Prerequisites:** `script.rc_mode_set_stealth` + `script.rc_mode_set_auto` (from the mode/automation-builder recipe).
- **Contract tile:** `binary_sensor.rc_safety_automation_night_mode`.

### §4.2 Auto Internet Failover (WAN bad for 2 min → prefer_auto)

- **Trigger:** `sensor.rc_net_wan_status == 'bad'` for 2 minutes.
- **Action:** calls `script.rc_openwrt_prefer_auto`.
- **Prerequisites:** `sensor.rc_net_wan_status` (from the Net recipe) + `script.rc_openwrt_prefer_auto` (from the OpenWrt controls recipe).
- **Contract tile:** `binary_sensor.rc_safety_automation_auto_internet_failover`.

### §4.3 Low Battery Mode (SOC < 20% for 10 min AND shore disconnected → Camp)

- **Trigger:** `sensor.rc_power_battery_soc < 20` for 10 minutes AND `binary_sensor.rc_power_shore_connected == 'off'`.
- **Action:** calls `script.rc_mode_set_camp`.
- **Prerequisites:** `sensor.rc_power_battery_soc` + `binary_sensor.rc_power_shore_connected` (from the Victron recipe) + `script.rc_mode_set_camp` (from the mode/automation-builder recipe).
- **Contract tile:** `binary_sensor.rc_safety_automation_low_battery_mode`.

### §4.4 Freeze Protection (temp < 2°C for 10 min → notification)

- **Trigger:** `sensor.rc_weather_temp_c < 2` for 10 minutes.
- **Action:** creates a persistent notification + writes a logbook entry.
- **Prerequisites:** `sensor.rc_weather_temp_c` (from `homeassistant/packages/roamcore_weather_time.yaml`).
- **Contract tile:** `binary_sensor.rc_safety_automation_freeze_protection`.

### §4.5 Daily Trip Log (23:59 → logbook entry)

- **Trigger:** time at 23:59.
- **Action:** writes a simple daily trip summary to the HA Logbook using `sensor.rc_trip_distance_today_mi` + `sensor.rc_trip_time_today`.
- **Prerequisites:** `sensor.rc_trip_distance_today_mi` + `sensor.rc_trip_time_today` (from the Traccar recipe).
- **Contract tile:** `binary_sensor.rc_safety_automation_daily_trip_log`.

### §4.6 Battery Full Alert (SOC > 95% for 15 min → notification)

- **Trigger:** `sensor.rc_power_battery_soc > 95` for 15 minutes.
- **Action:** creates a notification + writes a logbook entry.
- **Prerequisites:** `sensor.rc_power_battery_soc` (from the Victron recipe).
- **Contract tile:** `binary_sensor.rc_safety_automation_battery_full_alert`.

### §4.7 Inverter Overheat Alert (inverter temp > 75°C for 5 min → notification)

- **Trigger:** `sensor.rc_power_inverter_temperature > 75` for 5 minutes.
- **Action:** creates a notification + writes a logbook entry.
- **Prerequisites:** `sensor.rc_power_inverter_temperature` (from the Victron recipe).
- **Contract tile:** `binary_sensor.rc_safety_automation_inverter_overheat_alert`.

### §4.8 Router Overheat Alert (router temp > 70°C for 10 min → notification)

- **Trigger:** `sensor.rc_router_temperature > 70` for 10 minutes.
- **Action:** creates a notification + writes a logbook entry.
- **Prerequisites:** `sensor.rc_router_temperature` (from the OpenWrt controls recipe).
- **Contract tile:** `binary_sensor.rc_safety_automation_router_overheat_alert`.

### §4.9 Shore Power Connected (shore connects → notification)

- **Trigger:** `binary_sensor.rc_power_shore_connected` flips from `off` to `on`.
- **Action:** creates a notification + writes a logbook entry.
- **Prerequisites:** `binary_sensor.rc_power_shore_connected` (from the Victron recipe).
- **Contract tile:** `binary_sensor.rc_safety_automation_shore_power_connected`.

### §4.10 Shore Power Disconnected (shore disconnected for 1 min → notification)

- **Trigger:** `binary_sensor.rc_power_shore_connected == 'off'` for 1 minute.
- **Action:** creates a notification + writes a logbook entry.
- **Prerequisites:** `binary_sensor.rc_power_shore_connected` (from the Victron recipe).
- **Contract tile:** `binary_sensor.rc_safety_automation_shore_power_disconnected`.

### §4.11 Internet Recovery (internet unreachable for 2 min → restart network)

- **Trigger:** `binary_sensor.rc_net_internet_reachable == 'off'` for 2 minutes.
- **Action:** calls `script.rc_openwrt_restart_network`.
- **Prerequisites:** `binary_sensor.rc_net_internet_reachable` (from the Net recipe) + `script.rc_openwrt_restart_network` (from the OpenWrt controls recipe).
- **Contract tile:** `binary_sensor.rc_safety_automation_internet_recovery`.

### §4.12 Arrive at Camp (speed < 1 for 15 min AND 18:00-23:59 → Camp)

- **Trigger:** `sensor.rc_location_speed < 1` for 15 minutes AND time is between 18:00 and 23:59.
- **Action:** calls `script.rc_mode_set_camp`.
- **Prerequisites:** `sensor.rc_location_speed` (from the Traccar recipe) + `script.rc_mode_set_camp` (from the mode/automation-builder recipe).
- **Contract tile:** `binary_sensor.rc_safety_automation_arrive_at_camp`.

### §4.13 Depart Travel Mode (speed > 10 for 2 min → Travel)

- **Trigger:** `sensor.rc_location_speed > 10` for 2 minutes.
- **Action:** calls `script.rc_mode_set_travel`.
- **Prerequisites:** `sensor.rc_location_speed` (from the Traccar recipe) + `script.rc_mode_set_travel` (from the mode/automation-builder recipe).
- **Contract tile:** `binary_sensor.rc_safety_automation_depart_travel_mode`.

### §4.14 Solar is Crushing It (solar > 600W for 5 min → notification)

- **Trigger:** `sensor.rc_power_solar_power > 600` for 5 minutes.
- **Action:** creates a notification + writes a logbook entry.
- **Prerequisites:** `sensor.rc_power_solar_power` (from the Victron recipe).
- **Contract tile:** `binary_sensor.rc_safety_automation_solar_crushing_it`.

### §4.15 Battery Critical Alert (SOC < 10% for 5 min → notification)

- **Trigger:** `sensor.rc_power_battery_soc < 10` for 5 minutes.
- **Action:** creates a notification + writes a logbook entry.
- **Prerequisites:** `sensor.rc_power_battery_soc` (from the Victron recipe).
- **Contract tile:** `binary_sensor.rc_safety_automation_battery_critical_alert`.

### §4.16 Bedtime Level Check (22:00 + not level → reminder)

- **Trigger:** time at 22:00 AND `binary_sensor.rc_level == 'off'`.
- **Action:** creates a persistent notification + writes a logbook entry.
- **Prerequisites:** `binary_sensor.rc_level` + `sensor.rc_level_status` (from `homeassistant/packages/roamcore_level.yaml` + the leveling recipe).
- **Contract tile:** `binary_sensor.rc_safety_automation_bedtime_level_check`.

### §4.17 Quiet Hours Reminder (21:30 + mode != Stealth → reminder)

- **Trigger:** time at 21:30 AND `input_select.rc_mode != 'Stealth'`.
- **Action:** creates a persistent notification.
- **Prerequisites:** `input_select.rc_mode` + `script.rc_mode_set_stealth` (from the mode/automation-builder recipe).
- **Contract tile:** `binary_sensor.rc_safety_automation_quiet_hours_reminder`.

## §5 RoamCore contract tiles

The 25 `rc_safety_automation_*` + `rc_safety_automations_*` tiles + how the upstream HA automation enable-state binary_sensors expose them + translation helpers needed for the missing-dependency count + the enable-all-ready / disable-all buttons.

The full tile set (per `connection.yml` `dashboard.tiles`):

**Summary tiles (7):**

- `sensor.rc_safety_automations_enabled_count` — number of smart automations currently enabled (0–17).
- `sensor.rc_safety_automations_total_count` — total smart automations available (always 17).
- `sensor.rc_safety_automations_missing_count` — count of automations whose dependencies (scripts / entities) are not yet wired (e.g. Low Battery Mode's `script.rc_mode_set_camp` is missing → that automation is "missing").
- `binary_sensor.rc_safety_automations_all_ready` — TRUE when `missing_count == 0` (all 17 automations have their dependencies wired).
- `select.rc_safety_automations_view` — operator-tunable dashboard view: `all` / `enabled` / `missing` / `disabled`.
- `button.rc_safety_automations_enable_all_ready` — enable every automation whose dependencies are currently wired (one-tap).
- `button.rc_safety_automations_disable_all` — disable every automation (one-tap, for service).

**Per-automation mirror binary_sensors (17 — one per automation):**

- `binary_sensor.rc_safety_automation_night_mode`
- `binary_sensor.rc_safety_automation_auto_internet_failover`
- `binary_sensor.rc_safety_automation_low_battery_mode`
- `binary_sensor.rc_safety_automation_freeze_protection`
- `binary_sensor.rc_safety_automation_daily_trip_log`
- `binary_sensor.rc_safety_automation_battery_full_alert`
- `binary_sensor.rc_safety_automation_inverter_overheat_alert`
- `binary_sensor.rc_safety_automation_router_overheat_alert`
- `binary_sensor.rc_safety_automation_shore_power_connected`
- `binary_sensor.rc_safety_automation_shore_power_disconnected`
- `binary_sensor.rc_safety_automation_internet_recovery`
- `binary_sensor.rc_safety_automation_arrive_at_camp`
- `binary_sensor.rc_safety_automation_depart_travel_mode`
- `binary_sensor.rc_safety_automation_solar_crushing_it`
- `binary_sensor.rc_safety_automation_battery_critical_alert`
- `binary_sensor.rc_safety_automation_bedtime_level_check`
- `binary_sensor.rc_safety_automation_quiet_hours_reminder`

Each per-automation binary_sensor mirrors the corresponding `automation.roamcore_<name>` enable/disable state via a `template:` binary_sensor. The naming convention is `rc_safety_automation_<name>` because the suffix `_automation_<name>` is the documented naming convention for "this is the binary_sensor that mirrors the state of an automation by the same name" — the suffix is part of the tile id and is NOT a generic-noun double-stamp.

## §6 Cross-references to other connections

The 17 automations ride on top of these existing + upcoming
connections. The operator MUST wire the upstream connection's
contract tiles before the dependent automation can fire.

- **`connections/smoke-co-gas-sensors/`** (Wave 3 #45 — companion for the smart-cooking silence integration): the smoke-co-gas-sensors recipe's §7.7 automation can set `select.rc_safety_alarm_mode = silenced` for 30 minutes during active cooking; the smart-automations recipe mirrors the cooking-active state via the §17 Quiet Hours Reminder (21:30 + mode != Stealth → reminder) + the §1 Night Mode. CO alarms are NEVER silenced by the cooking-active path — CO is life-threatening even during cooking.
- **`connections/heated-floors/`** (Wave 3 #44 — companion for the §16 Bedtime Level Check prerequisite): the §16 Bedtime Level Check fires at 22:00 if `binary_sensor.rc_level == 'off'`. The heated-floors recipe's §1 cross-references the leveling recipe; the smart-automations recipe's §16 depends on the heated-floors recipe's §7.5 frost-protection automation (which uses `binary_sensor.rc_level`) for the level signal.
- **`connections/victron/`** (companion for §3 + §6 + §7 + §9 + §10 + §14 + §15): the §3 Low Battery Mode + §6 Battery Full Alert + §7 Inverter Overheat Alert + §9 Shore Power Connected + §10 Shore Power Disconnected + §14 Solar is Crushing It + §15 Battery Critical Alert all consume Victron's `sensor.rc_power_battery_soc` + `sensor.rc_power_inverter_temperature` + `sensor.rc_power_solar_power` + `binary_sensor.rc_power_shore_connected` contract tiles.
- **`connections/traccar/`** (companion for §5 + §12 + §13): the §5 Daily Trip Log + §12 Arrive at Camp + §13 Depart Travel Mode consume Traccar's `sensor.rc_trip_distance_today_mi` + `sensor.rc_trip_time_today` + `sensor.rc_location_speed` contract tiles.
- **`connections/leveling/`** (companion for §16): the §16 Bedtime Level Check consumes the leveling recipe's `binary_sensor.rc_level` + `sensor.rc_level_status` contract tiles.
- **`connections/openwrt-controls/`** (companion for §2 + §11): the §2 Auto Internet Failover + §11 Internet Recovery consume OpenWrt's `script.rc_openwrt_prefer_auto` + `script.rc_openwrt_restart_network` + `sensor.rc_router_temperature` contract tiles.
- **`connections/net/`** (companion for §2 + §11): the §2 Auto Internet Failover + §11 Internet Recovery consume Net's `sensor.rc_net_wan_status` + `binary_sensor.rc_net_internet_reachable` contract tiles.
- **`connections/mode-automation-builder/`** (companion for §1 + §12 + §13 + §17): the §1 Night Mode + §12 Arrive at Camp + §13 Depart Travel Mode + §17 Quiet Hours Reminder consume the mode-automation-builder's `input_select.rc_mode` + `script.rc_mode_set_stealth` + `script.rc_mode_set_auto` + `script.rc_mode_set_camp` + `script.rc_mode_set_travel` contract tiles.
- **`connections/bluetooth-wifi-presence/`** (Wave 3 #42 — companion for downstream notification escalation): the 17 automations' persistent notifications can be escalated (via the smoke-co-gas-sensors §7.4 pattern) when the operator is in the van AND a safety-relevant automation fires (e.g. Inverter Overheat Alert + operator at home → MA TTS to living zone + louder siren).

## §7 Privacy

All 17 automations are **local**. No cloud call home. The HA Core
`automation:` + `script:` + `template:` + `button:` + `select:`
domains are all local; no telemetry is sent off-van. The only
network call is the **HA Core push-notification** if the operator
has set one up via the upstream companion app (iOS / Android) — that
is the operator's choice; RoamCore does not add any cloud
integration.

The contract entities (`rc_safety_automation_*` +
`rc_safety_automations_*`) do not collect any operator data; they
are pure local-state tiles that surface the operator's choice + the
upstream sensor readings + the audit summary.

The managed-marker convention (`Managed by RoamCore Smart Automations
v0.1` + `key=<name>` + `hash=<template hash>`) is purely local — it
lives in each automation's `description` field inside HA Core; no
external service sees it.

## §8 Troubleshooting

Eight troubleshooting entries:

1. **Automation doesn't trigger** — the prerequisite entity isn't present yet because the parent connection hasn't been shipped OR the operator hasn't wired the upstream device yet. Solution: check `RoamCore → Settings → Smart Automations` for the per-automation "missing dependencies" indicator; the missing entity is listed in the per-automation detail view. Once the upstream connection ships and the entity is wired, the automation fires automatically.

2. **Automation runs but action fails** — the dependent script is missing (e.g. `script.rc_mode_set_camp` for Low Battery Mode). Solution: install the mode scripts via the upcoming Wave 2 #23 mode-automation-builder slice OR manually copy the scripts YAML from the mode-automation-builder recipe's `docs/recipe.md`.

3. **Managed-marker overwritten by user edit** — the operator edited the automation's `description` and lost the `Managed by RoamCore Smart Automations v0.1` + `key=<name>` + `hash=<template hash>` marker. RoamCore stops updating the logic but still allows enable/disable. This is the documented behavior from `docs/guides/smart-automations.md` "Editing" section. Solution: re-enable the automation from the RoamCore UI which will re-create the marker.

4. **Automation key collisions** — if two RoamCore-installed automations have the same `key=<name>`, the second one will fail to install. Solution: check `RoamCore → Settings → Smart Automations` for the duplicate; the missing-dependencies count will show 1 for the collided automation.

5. **Managed-marker not detected** — the operator edited the description and lost the marker. Solution: re-enable the automation from the RoamCore UI which will re-create the marker (this is the same as #3 — the audit detects the missing marker and the RoamCore UI offers a "Repair managed marker" action).

6. **Night Mode triggers at the wrong time** — timezone mismatch. Solution: ensure `sensor.rc_time_zone` is set correctly via the `input_text.rc_time_zone_override` helper (from `homeassistant/packages/roamcore_weather_time.yaml`); the time trigger respects the HA Core timezone setting.

7. **Low Battery Mode triggers on shore** — the `binary_sensor.rc_power_shore_connected` is bouncing. Solution: add a `for: 00:05:00` debounce on the shore-connected binary_sensor in the Victron recipe's `template:` binary_sensor (5-minute debounce matches the recipe's documented pattern for shore-power state changes).

8. **Bedtime Level Check fires every night even when level** — the `binary_sensor.rc_level` is stuck. Solution: re-calibrate the leveling sensor via the upcoming Wave 3 #60 leveling connection; the calibration routine resets the level binary_sensor to the actual van pitch + roll.

## §9 Promoting to tier-a

What would need to happen to promote this connection from tier-b to
tier-a:

1. **A RoamCore-owned automation engine** — currently RoamCore RECIPE-s HA Core's `automation:` domain. A tier-a promotion would add a RoamCore-owned wrapper that owns the enable/disable state machine + the managed-marker audit + the contract-tile synthesis in a single `config_flow.py`. The wrapper would still back the automations with HA Core's `automation:` domain (we don't re-implement the trigger engine), but the wrapper would own the audit invariants.

2. **A `config_flow.py` for the RoamCore UI "Smart Automations" page** that walks the operator through enabling each of the 17 automations one-by-one, surfacing the per-automation prerequisite wiring (Victron sensor present? Mode script present? Net sensor present? Traccar sensor present? etc.) + the managed-marker audit + the missing-dependencies count + the enable-all-ready / disable-all button affordances. The current UI is a dashboard card (the `rc_safety_automations_*` + `rc_safety_automation_*` tiles) + a set of OpenClaw queries — a tier-a promotion would add the `config_flow.py` GUI flow on top.

3. **Integration tests that assert enabling / disabling a managed automation works via the HA Core API** — currently the smoke test is a manifest-honesty check (`tests/test_connection_yml.py`); a tier-a promotion would add an integration test that uses the HA Core API to (a) create a managed automation via the wrapper, (b) verify the managed-marker audit invariants hold (description starts with `Managed by RoamCore Smart Automations v0.1`, contains `key=<name>`, contains `hash=<template hash>`), (c) enable the automation via the wrapper, (d) verify the `binary_sensor.rc_safety_automation_<name>` mirror tile flips to `on`, (e) disable the automation, (f) verify the mirror tile flips back to `off`.

4. **The bench fixture** — a CI bench with the upstream prerequisites wired (HA Core 2023.8+ + the 17 automation templates loaded + the per-automation prerequisites mocked via canned entity states). Without the bench fixture, the integration test cannot run on CI and the connection must stay tier-b.

When the above is in place, flip `tier: b` → `tier: a` in
`connection.yml`, remove the 4 `tier_warnings`, set
`wizard.one_tap: true`, and document the promotion in a Wave 4
follow-up slice.