# RoamCore dev mocks (Home Assistant)

RoamCore uses a **contract layer** of `rc_*` entities in Home Assistant.

During UI development (before vendor integrations are mapped), we provide editable **mock helpers** (e.g. `input_number.rc_mock_*`) and template sensors that expose stable contract entities (e.g. `sensor.rc_power_*`).

## Files

These live under the RoamCore repo and are meant to be copied into Home Assistant `packages/`:

- `homeassistant/packages/roamcore_dev_mocks.yaml`
  - Editable mock values: `input_number.rc_mock_*`, `input_text.rc_mock_*`, etc.
  - A calibration script: `script.rc_system_level_calibrate`
  - A template button: `button.rc_system_level_calibrate` (presses the script)

- `homeassistant/packages/roamcore_power.yaml`
- `homeassistant/packages/roamcore_net.yaml`
- `homeassistant/packages/roamcore_system_level.yaml`
- `homeassistant/packages/roamcore_location.yaml`

Frontends/dashboards should reference **only** the contract entities (the `rc_*` layer), never the mock helpers.

Naming convention reference:
- `RoamCore/docs/reference/rc-entity-naming.md`

## How it works

- UI reads: `sensor.rc_*`, `binary_sensor.rc_*`, `button.rc_*`
- Mock values live in: `input_number.rc_mock_*`, `input_text.rc_mock_*`, etc.
- Contract sensors are implemented with `template:` sensors that read from mock helpers (and later, can be switched to vendor entities).

## Common tasks

### Change a mock value

Use Home Assistant UI for Helpers:
- Settings → Devices & services → Helpers

Or edit the `initial:` values in `roamcore_dev_mocks.yaml` and restart Home Assistant.

### Extend the contract

When adding new UI fields:
1. Add a mock helper (`rc_mock_*`) in `roamcore_dev_mocks.yaml`
2. Add a new contract sensor (`sensor.rc_*`) in the appropriate package (`roamcore_power.yaml`, `roamcore_net.yaml`, etc.)
3. Update the UI to read only the contract sensor

## Notes / gotchas

- Home Assistant will often keep entity IDs in the entity registry once created. If you change `unique_id`/names later, you may need to clean up or rename entities in HA.
- Keep `rc_*` IDs vendor-agnostic. Do not put `victron`, `starlink`, etc. in `rc_*` entity_ids.
