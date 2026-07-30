# Smoke / CO / gas safety sensors (van life safety monitoring)

**Tier:** B (recipe)
**Category:** Safety
**Status:** beta

## What this connection is

Smoke / CO / gas safety sensors — van life safety monitoring for vans — are the **foundation** of every "is it safe to sleep in the van?" question: a single "any alarm" tile that aggregates smoke detected + CO detected + gas detected into one dashboard indicator, the alarm silenced flag with operator-tunable duration (default 10 min), the sensor-offline warning when any safety sensor hasn't checked in within 30 min, the battery-low warning, the alarm mode select (`full` / `night_only` / `cooking_active` / `off`), the alarm test button, the alarm silence button, and the mode-aware `cooking_active` suppression that mutes non-CO alarms during active cooking.

RoamCore ships **no** native smoke detector, CO detector, or propane/LPG leak sensor. We RECIPE the well-understood combination of three upstream operator-side paths and a translation layer that maps each upstream `binary_sensor.*` + upstream `sensor.*` + upstream vendor integration choice into a vendor-neutral `rc_safety_*` contract layer. The three paths:

- **Path A — Smart detectors** (recommended for operators who already own a Nest Protect / First Alert Z-Wave / X-Sense Zigbee / Heiman Z-Wave / Zipato Zigbee). The vendor integration's `binary_sensor.*` (smoke detected / CO detected / gas detected) + `sensor.*` (smoke_ppm / co_ppm / gas_ppm) entities are already exposed in HA. The recipe shows the entity_id surfacing + a `template:` binary_sensor that aggregates multiple sensors of the same type via `is_state(...) or is_state(...)`.

- **Path B — Generic smoke/CO alarms** (basic Kidde / First Alert battery-only alarms do NOT have HA integration — they are standalone, non-networked detectors). Path B is the "minimum safety baseline" subsection that lists the recommended detectors (Kidde KN-COSM-IBA combo smoke+CO, Nest Protect, X-Sense SD11, First Alert Z-Wave).

- **Path C — Propane/LPG detectors** (Mopeka / Atemox / GasAlert / MQ-series via ESPHome). These are typically 4-20 mA analog sensors that need a Modbus bridge OR an analog-to-Zigbee bridge (e.g. Shelly UNI analog input + a 4-20 mA receiver OR an ESPHome ADC reading the analog voltage directly).

All three paths land on the same vendor-neutral contract layer via 13 `rc_safety_*` dashboard tiles.

## Setup recipe (one-paragraph)

1. Decide which path fits your van: **Path A** — Smart detectors (Nest Protect / First Alert Z-Wave / X-Sense Zigbee / Heiman Z-Wave / Zipato Zigbee); OR **Path B** — Basic smoke/CO alarms (Kidde / First Alert battery-only alarms — minimum safety baseline); **Path C** — Propane/LPG detectors (Mopeka / Atemox / GasAlert / MQ-series via a Modbus bridge or ESPHome ADC).
2. Wire the prerequisites FIRST (the recipe §2 walks through these). The operator MUST not skip the safety prerequisites.
3. Wire the upstream device. Path A: configure the vendor integration; Path B: install the basic alarm per local code; Path C: wire the analog input to the ESPHome ADC OR the Modbus bridge.
4. Wire the HA core `template:` binary_sensor + template sensors + template select + template buttons that synthesizes the `rc_safety_*` contract tiles.
5. Create the `rc_safety_*` contract tiles.
6. Verify the six safety automations (recipe §7 walks through each).
7. Enable the recipe §7 automations.
8. Reload the RoamCore dashboard.

Full howto: see [`docs/recipe.md`](docs/recipe.md).

## Why tier-b, not tier-a

Tier-a requires a working RoamCore-owned `config_flow.py`, integration tests against a real smoke + CO + propane sensor bench on CI, and `wizard.one_tap: true`. We have no operator detector placement on the CI bench to integration-test against. So this connection is honestly beta-tier: the recipe is sound but we cannot claim one-tap automation.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "smoke_co_gas_sensors"` marker for the audit.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded): [`docs/catalog/safety/smoke-co-gas-sensors.md`](../../docs/catalog/safety/smoke-co-gas-sensors.md)
- Smart Automations connection (companion for the §7 cooking-active mode-aware suppression): `connections/smart-automations/`
- Deadbolts connection (companion for the §7 smoke-detected emergency-egress unlock): `connections/deadbolts/`
- Bluetooth / Wi-Fi presence connection (companion for the §7 sensor-offline warning escalation): `connections/bluetooth-wifi-presence/`
- Mode / automation-builder connection (companion for the §7 `select.rc_safety_alarm_mode` mode-aware behavior): `connections/mode-automation-builder/`
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`
