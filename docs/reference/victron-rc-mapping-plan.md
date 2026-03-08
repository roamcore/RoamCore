# Victron → RoamCore mapping plan (vt_* → rc_*)

This document describes the intended mapping between:

- **Vendor layer (Victron ingest):** `vt_*` entities published via MQTT Discovery
- **RoamCore contract layer:** `rc_*` entities consumed by RoamCore UI/automations

Entity naming must follow:
- `RoamCore/docs/reference/rc-entity-naming.md`

## Goals

1. Keep `vt_*` **vendor-specific** and stable (directly reflects Victron/Venus data model).
2. Keep `rc_*` **product/contract** oriented (what the RoamCore UI expects).
3. Keep the mapping layer **thin and swappable**:
   - If the data source changes (real GX vs dev mock, different integration), we only update the mapping.

## Current vt_* signals (MVP)

Published by `homeassistant/addons/roamcore-victron-auto`:

- `sensor.vt_battery_voltage_v`
- `sensor.vt_battery_current_a`
- `sensor.vt_battery_power_w`
- `sensor.vt_battery_soc_percent`
- `sensor.vt_solar_power_w`
- `sensor.vt_dc_load_power_w`
- `sensor.vt_ac_in_power_w`
- `sensor.vt_ac_out_power_w`
- `binary_sensor.vt_shore_connected`

## rc_* contract entities (initial)

Mirrored via Home Assistant templates in:
- `homeassistant/packages/roamcore_victron_map.yaml`

| rc_* | Type | Source vt_* |
|---|---|---|
| `sensor.rc_power_battery_soc` | sensor | `sensor.vt_battery_soc_percent` |
| `sensor.rc_power_battery_voltage` | sensor | `sensor.vt_battery_voltage_v` |
| `sensor.rc_power_battery_current` | sensor | `sensor.vt_battery_current_a` |
| `sensor.rc_power_solar_power` | sensor | `sensor.vt_solar_power_w` |
| `sensor.rc_power_load_power` | sensor | `sensor.vt_dc_load_power_w` |
| `sensor.rc_power_ac_in_power` | sensor | `sensor.vt_ac_in_power_w` |
| `sensor.rc_power_ac_out_power` | sensor | `sensor.vt_ac_out_power_w` |
| `binary_sensor.rc_power_shore_connected` | binary_sensor | `binary_sensor.vt_shore_connected` |

## Next expansions

- Add charger/inverter/bus voltage/current detail signals as needed.
- Introduce a battery “mode/state” rc entity (charging/discharging/idle) derived from `vt_battery_power_w`.
- Add multi-instance device list diagnostic entity (already tracked by the add-on).

