# RoamCore Dashboard (Dev Baseline)

This guide documents the current RoamCore dashboard baseline inside Home Assistant.

## Goal
Provide an initial dashboard that matches the RoamCore v0 design language while remaining tied to the RoamCore `rc_*` contract entities.

## Contract entities
Dashboards should reference only the RoamCore contract entities (see naming convention):
- `docs/reference/rc-entity-naming.md`

The v0 dashboard custom card currently reads:
- Power: `sensor.rc_power_battery_soc`, `sensor.rc_power_solar_power`, `sensor.rc_power_load_power`, `binary_sensor.rc_power_shore_connected`, `sensor.rc_power_inverter_status`
- Network: `sensor.rc_net_wan_status`, `sensor.rc_net_wan_source`, `sensor.rc_net_download`, `sensor.rc_net_upload`, `sensor.rc_net_ping`
- Level: `sensor.rc_system_level_pitch_deg`, `sensor.rc_system_level_roll_deg`

## Implementation (HAOS)
### Custom card JS
- File path on HA: `/config/www/roamcore/roamcore-dashboard.js`
- Served at: `/local/roamcore/roamcore-dashboard.js`

A copy is kept in this repo at:
- `dashboard/lovelace/custom-cards/roamcore-dashboard.js`

### Lovelace dashboard config
The RoamCore dashboard is stored-mode Lovelace.
A snapshot copy of the storage JSON is kept at:
- `dashboard/lovelace/storage/lovelace.roamcore.json`

### Resource registration
Home Assistant must register the JS resource as a Lovelace resource:
- URL: `/local/roamcore/roamcore-dashboard.js`
- Type: `module`

(Exact storage key/file name may vary by HA version. In this environment we used `.storage/lovelace_resources`.)

## Dev mocks (temporary)
During development, we use mock helpers to populate the `rc_*` entities when real sources are not connected.

- All mock inputs live in a single HA packages file so it is easy to delete later.
- The contract translation packages should fall back to mocks only when vendor entities are missing.

## Status
This is a baseline intended for iterative polish.
