# Electronic valves + auto tank switching

**Tier:** B (recipe)
**Category:** water
**Status:** beta

## What this connection is

Electronic valves + auto tank switching — fresh-inlet valve control + grey-drain valve control + aux-tank switching valve control + valve-position feedback + auto tank switching between primary and aux tanks + the §7 safety interlocks (leak detected / freeze risk / low-voltage lockout / auto-close grey / mode-aware lockouts / valve stuck-open detector) — is the vendor-neutral surface that turns "which tank am I drawing from right now?" + "is the grey valve about to overflow?" + "can I safely open a valve when the battery is low?" into a dashboard tile + a push notification + a mode-aware automation. The single "are the valves within safe bounds?" tile aggregates fresh inlet state + grey drain state + aux tank state + valve-position feedback + any-moving + auto-tank-switch-active + leak-detected-lockout + freeze-risk-lockout + low-voltage-lockout into one dashboard indicator, the three valve-state switches (fresh inlet / grey drain / aux tank) are the operator-tunable valve control affordances, the three valve-position binary_sensors are the position-feedback confirmations, the any-moving binary_sensor catches the stuck-valve / valve-in-motion scenario, the auto-tank-switch-active binary_sensor catches the auto-switching state, the leak-detected-lockout + freeze-risk-lockout + low-voltage-lockout binary_sensors catch the catastrophic van-killer scenarios, the operator-tunable auto-close-grey-minutes + low-voltage-lockout-SOC-pct + active-tank + valve-mode tiles cover the day-1 configuration affordances, and the open-all / close-all buttons cover the emergency affordances (panic-stop / operator-overridden unlock).

RoamCore ships **no** native valve hardware. We RECIPE the well-understood combination of two upstream operator-side paths and a translation layer that maps the upstream `switch.*` / `valve.*` / `binary_sensor.*` entities into a vendor-neutral `rc_water_valve_*` contract layer. The two paths:

- **Path A — ESPHome valve node (recommended for ESPHome-friendly installs).** Vendor: `esphome` (HA core, GUI flow since 2023.x) — one ESP32 per node, electrically-actuated 12 V / 24 V valves (latching solenoid / motorized ball / proportional) wired into GPIO + a safe driver (relay module / MOSFET H-bridge / BTS7960 43 A / IBOM / etc.) per valve; the ESPHome YAML exposes `switch.<node>_valve_fresh_inlet` + `switch.<node>_valve_grey_drain` + `switch.<node>_valve_aux_tank` + `binary_sensor.<node>_valve_fresh_inlet_position` + `binary_sensor.<node>_valve_grey_drain_position` + `binary_sensor.<node>_valve_aux_tank_position` (limit switch or current sense feedback). Optional `cover` / `valve` template for proportional valves.

- **Path B — Generic relay + HA template valve (no ESPHome).** Vendor: `shelly` / `zooz` / `aeotec` (HA core, GUI flow since 2022.x) — a Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano Switch wired into the 12 V / 24 V valve coils + HA core `template:` valve or `switch:` template + feedback binary_sensor for valve-position confirmation.

Both paths land on the same vendor-neutral contract layer via 17 `rc_water_valve_*` dashboard tiles.

## Setup recipe (one-paragraph)

1. Decide which path fits your van: **Path A** — ESPHome valve node + 12 V / 24 V electrically-actuated valves + safe drivers + valve-position feedback (most common for ESPHome-friendly installs); **Path B** — generic relay + HA template valve (most common when the operator already owns a Shelly / Zooz / Aeotec relay + doesn't want to flash ESPHome).
2. Wire the prerequisites FIRST (the recipe §2 walks through these). The operator MUST not skip the upstream integration prerequisite (the recipe won't work if the esphome / shelly / template integration is not already configured).
3. Wire the upstream entity. Path A: flash the ESPHome firmware onto the ESP32 + wire the 12 V / 24 V valve coils into the safe drivers + wire the valve-position feedback (limit switch or current sense) into GPIO; Path B: pair the Shelly / Zooz / Aeotec relay with the 12 V / 24 V valve coils + add the feedback binary_sensor (separate wiring).
4. Wire the HA core `template:` (or HA core `entity` customize-domain alias) that maps the upstream entity to one of the 17 contract tiles (`rc_water_valve_fresh_inlet_state` / `rc_water_valve_grey_drain_state` / `rc_water_valve_aux_tank_state` / `rc_water_valve_fresh_inlet_position` / `rc_water_valve_grey_drain_position` / `rc_water_valve_aux_tank_position` / `rc_water_valve_any_moving` / `rc_water_valve_auto_tank_switch_active` / `rc_water_valve_leak_detected_lockout` / `rc_water_valve_freeze_risk_lockout` / `rc_water_valve_active_tank` / `rc_water_valve_mode` / `rc_water_valve_auto_close_grey_min` / `rc_water_valve_low_voltage_lockout_soc_pct` / `rc_water_valve_low_voltage_lockout` / `rc_water_valve_open_all` / `rc_water_valve_close_all`).
5. Configure the operator-tunable thresholds (`number.rc_water_valve_auto_close_grey_min` default 15 min + `number.rc_water_valve_low_voltage_lockout_soc_pct` default 20 % + `select.rc_water_valve_active_tank` default auto + `select.rc_water_valve_mode` default auto).
6. Verify the six §7 safety interlocks (leak detected / freeze risk / low-voltage lockout / auto-close grey / mode-aware lockouts / valve stuck-open detector).
7. Enable the seven §8 automations (auto-switch-to-aux-tank when fresh < 5 % + auto-switch-back-to-primary when aux < 5 % + auto-close-grey-after-N-min + leak-detected-close-fresh-open-grey + freeze-risk-close-all + low-voltage-lockout + mode-aware scheduling).
8. Reload the RoamCore dashboard.

Full howto: see [`docs/recipe.md`](docs/recipe.md).

## Why tier-b, not tier-a

Tier-a requires a working RoamCore-owned `config_flow.py`, integration tests against a real electronic valve bench (a 12 V / 24 V electrically-actuated valve + a safe driver + an ESP32 + a relay + a tank-level sensor, all wired together in a controlled environment), and `wizard.one_tap: true`. We have no operator-side electronic valve bench on the CI to integration-test against (the bench requires physical hardware: a 12 V / 24 V electrically-actuated valve + a safe driver + an ESP32 + a relay + a tank-level sensor, all wired together in a controlled environment + a way to simulate the leak / freeze / low-voltage trigger conditions). So this connection is honestly beta-tier: the recipe is sound but we cannot claim one-tap automation.

The original legacy catalog page (the legacy spec) listed "Support tier: C" with no recipe + no contract + no automations — just a placeholder that said "Use electronically controlled valves to automate water routing". The supersession banner on the legacy page reflects that the connection has been promoted to tier-b.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "electronic_valves"` marker for the audit.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded): [the legacy spec](../../the legacy spec)
- Water tanks connection (companion for the §6 auto tank switching source signals + the §7.1 / §7.2 safety interlock cross-references — Wave 3 #50): `connections/water-tanks/`
- Victron (power) connection (companion for the §7.3 low-voltage lockout safety interlock — uses `sensor.rc_power_battery_soc` + `binary_sensor.rc_power_shore_connected`): `connections/victron/`
- Heated floors + engine pre-heat connection (companion for the §7.2 freeze risk pattern — Wave 3 #44): `connections/heated-floors/`
- HVAC basics connection (companion for the §7.2 freeze risk pattern — Wave 3 #49): `connections/hvac-basics/`
- Smoke / CO / gas sensors connection (companion for the §7.1 leak detected pattern — Wave 3 #45): `connections/smoke-co-gas-sensors/`
- Mode / automation-builder connection (companion for the §7.5 mode-aware lockouts + the §8.7 mode-aware scheduling automation): `connections/mode-automation-builder/`
- Bluetooth / Wi-Fi presence connection (companion for the §7.1 leak detected push notification escalation when the operator is home): `connections/bluetooth-wifi-presence/`
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`