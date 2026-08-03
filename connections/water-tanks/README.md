# Water tanks (fresh/grey monitoring)

**Tier:** B (recipe)
**Category:** water
**Status:** beta

## What this connection is

Water tanks — fresh + grey water telemetry + pump runtime + leak detection + freeze-risk monitoring for vans — is the vendor-neutral surface that turns "is the fresh tank still full enough to last the night?" into a dashboard tile + a push notification + a mode-aware automation. The single "is the water system within safe bounds?" tile aggregates fresh level + grey level + pump running + leak detected + freeze risk into one dashboard indicator, the fresh + grey level sensors surface the current tank levels, the days-remaining sensor gives the operator a refill-planning forecast, the fresh + grey level-in-litres sensors convert percentage to litres using the operator-configured tank sizes, the three water-level warnings (fresh empty / fresh low / grey full) catch the "ran out / running out / tank is full and might overflow" scenarios, the pump running + pump running too long sensors catch the stuck-pump / stuck-faucet scenario, the leak detected + freeze risk sensors catch the catastrophic van-killer scenarios, and the operator-tunable tank sizes + water mode (auto / stealth_only / silent / disabled) cover the day-1 configuration affordances.

RoamCore ships **no** native tank sensor hardware. We RECIPE the well-understood combination of three upstream operator-side paths and a translation layer that maps the upstream `sensor.*` / `binary_sensor.*` / `switch.*` entities into a vendor-neutral `rc_water_*` contract layer. The three paths:

- **Path A — ESPHome tank sensor node (recommended for ESPHome-friendly installs).** Vendor: `esphome` (HA core, GUI flow since 2023.x) — one ESP32 per node, ultrasonic probe (JSNSR04T / HC-SR04 waterproof) wired into GPIO for each tank; the ESPHome YAML exposes `sensor.<node>_fresh_level_pct` + `sensor.<node>_fresh_distance_cm` + `sensor.<node>_grey_level_pct` + `sensor.<node>_grey_distance_cm`. Optional `binary_sensor.<node>_pump_running` (sense the pump's +12 V wire via a CT clamp on the same ESP32) + `sensor.<node>_fresh_temperature_c` (DS18B20 in tank bay) + `binary_sensor.<node>_leak_detected`.

- **Path B — Generic resistive / 4–20 mA / voltage probe via Shelly UNI ADC (no ESPHome).** Vendor: `shelly` (HA core, GUI flow since 2022.x) — probe wired into a Shelly UNI's ADC input; the Shelly integration exposes `sensor.<tank>_voltage`; the HA `template:` integration translates voltage to percentage via a calibration curve (operator configures `number.rc_water_fresh_tank_size_l` + the empty-voltage + full-voltage calibration points).

- **Path C — Cloud-bridged level sensor (SeeLevel / Garnet SeeLevel II 709-BTG / Mopeka Pro Check / Lippert).** Vendor integration in HA core or HACS (GUI flow since 2022.x / 2023.x depending on the vendor) — the vendor integration exposes the level directly; the RoamCore recipe maps the vendor entity to the contract tile via HA `template:`.

All three paths land on the same vendor-neutral contract layer via 17 `rc_water_*` dashboard tiles.

## Setup recipe (one-paragraph)

1. Decide which path fits your van: **Path A** — ESPHome tank sensor node per tank + per-pump CT clamp + optional DS18B20 + optional leak sensor (most common for ESPHome-friendly installs); **Path B** — Shelly UNI + ADC probe per tank + the operator's choice of resistive / 4–20 mA / voltage probe (most common when the operator already owns a Shelly UNI); **Path C** — cloud-bridged level sensor (SeeLevel / Garnet / Mopeka / Lippert) (most common for RVs with vendor-supplied tank sensors).
2. Wire the prerequisites FIRST (the recipe §2 walks through these). The operator MUST not skip the upstream integration prerequisite (the recipe won't work if the esphome / shelly / vendor integration is not already configured).
3. Wire the upstream entity. Path A: flash the ESPHome firmware onto the ESP32; Path B: pair the Shelly UNI with the tank probe; Path C: pair the vendor sensor with the vendor gateway / cloud.
4. Wire the HA core `template:` (or HA core `entity` customize-domain alias) that maps the upstream entity to one of the 17 contract tiles (`rc_water_fresh_level_pct` / `rc_water_fresh_level_l` / `rc_water_fresh_days_remaining` / `rc_water_grey_level_pct` / `rc_water_grey_level_l` / `rc_water_grey_full_warning` / `rc_water_fresh_low_warning` / `rc_water_fresh_empty_warning` / `rc_water_pump_running` / `rc_water_pump_runtime_min_last_24h` / `rc_water_pump_running_too_long` / `rc_water_leak_detected` / `rc_water_freeze_risk` / `rc_water_fresh_temperature_c` / `rc_water_fresh_tank_size_l` / `rc_water_grey_tank_size_l` / `rc_water_mode`).
5. Configure the operator-tunable tank sizes (`number.rc_water_fresh_tank_size_l` default 80 L + `number.rc_water_grey_tank_size_l` default 60 L) + (for Path B) the per-tank calibration curve (empty-voltage + full-voltage).
6. Verify the five §7 safety interlocks (leak detected / freeze risk / fresh empty warning / pump running too long / mode-aware lockouts).
7. Enable the six §8 automations (auto-push on fresh low / auto-push on grey full / auto-stop pump when pump running too long / auto-push critical on leak detected / auto-engage heated-floors on freeze risk / mode-aware scheduling).
8. Reload the RoamCore dashboard.

Full howto: see [`docs/recipe.md`](docs/recipe.md).

## Why tier-b, not tier-a

Tier-a requires a working RoamCore-owned `config_flow.py`, integration tests against a real water tank bench (a fresh tank + a grey tank + a pump + a leak sensor + a temperature probe + an ESPHome node + optionally a Shelly UNI + a vendor sensor), and `wizard.one_tap: true`. We have no operator-side water tank bench on the CI to integration-test against (the bench requires physical hardware: a fresh tank + a grey tank + a pump + a leak sensor + a temperature probe + an ESP32 + an ultrasonic probe + a CT clamp + optionally a Shelly UNI, all wired together in a controlled environment). So this connection is honestly beta-tier: the recipe is sound but we cannot claim one-tap automation.

The original legacy catalog page (the legacy spec) listed "Support tier: C (manual / varies)" with no recipe + no contract + no automations — just a placeholder that said "add your preferred sensors/integration, then wire the resulting entities into your dashboard". The supersession banner on the legacy page reflects that the connection has been promoted to tier-b.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "water_tanks"` marker for the audit.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded): [the legacy spec](../../the legacy spec)
- Heated floors + engine pre-heat connection (companion for the §7 freeze-risk safety interlock — engages floor heating on freeze_risk; Wave 3 #44): `connections/heated-floors/`
- HVAC basics connection (companion for the §7 freeze-risk safety interlock — keeps cabin thermostat > 5 °C; Wave 3 #49): `connections/hvac-basics/`
- Victron (power) connection (companion for the §7 freeze-risk / §7 pump-running-too-long safety interlocks — freeze risk + pump drain both pull battery): `connections/victron/`
- Smoke / CO / gas sensors connection (companion for the §7 leak-detected pattern — the leak-detected automation mirrors the CO-detected automation from this connection): `connections/smoke-co-gas-sensors/`
- Mode / automation-builder connection (companion for the §7 mode-aware lockouts + the §8.6 mode-aware scheduling automation): `connections/mode-automation-builder/`
- Bluetooth / Wi-Fi presence connection (companion for the §7 leak-detected push notification escalation when the operator is home): `connections/bluetooth-wifi-presence/`
- Deadbolts connection (companion for the §7 leak-detected emergency-egress unlock pattern — the operator must be able to get OUT of the van even if water is pooling near the door): `connections/deadbolts/`
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`