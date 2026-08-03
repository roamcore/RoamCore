# Fans (vendor-neutral fan-controller umbrella for HA — rooftop vent fans + circulation fans + bathroom exhaust fans, operator picks ONE path)

**Tier:** B (recipe)
**Category:** ventilation
**Status:** beta

## What this connection is

Fans (vendor-neutral fan-controller umbrella for HA, covering rooftop vent fans + circulation fans + bathroom exhaust fans — rooftop + circulation fans cover the climate-aware airflow + the rain-sensor safety block; bathroom exhaust fans wire as a separate downstream `fan.*` entity that RoamCore does NOT own) — the umbrella for "Fans are a simple upgrade that massively improves comfort: airflow, condensation control, cooking smells, and keeping the van livable in warm weather" — is the ventilation-category complement to the broader RoamCore climate-aware automation affordances. The single "is the fan currently running?" tile aggregates the upstream fan state into one dashboard indicator; the "current speed" tile surfaces the fan's 0-100 percent; the "fan mode" selector is the operator-facing affordance (one of `off` / `low` / `med` / `high` / `auto` / `rain_safe`); the "fan active" tile is the AND gate (TRUE iff the fan is currently running); the "runtime minutes today" tile is the daily runtime aggregate; the "last trigger reason" tile surfaces the reason the fan was last turned on (one of `manual` / `humidity` / `temperature` / `schedule` / `sleep`); the "run-now 15min" button is the manual override (the operator can force the fan to run for 15 minutes from the dashboard without waiting for the auto-fan-on-humidity-high or auto-fan-on-temperature-high automations); the "rain sensor active" tile is the rooftop safety block (TRUE iff the rain sensor is wet — the rooftop fan is forced OFF + the rooftop vent cover is forced CLOSED when this tile is TRUE).

RoamCore ships **no** native fan integration. We RECIPE the well-understood upstream HA core `fan` integration (since 2022.x — has exposed a `set_percentage` service + a `percentage` attribute + a `preset_mode` attribute + the `fan.turn_on` / `fan.turn_off` / `fan.toggle` / `fan.set_percentage` / `fan.set_preset_mode` services + the `fan` domain since 2022.x) + the HA core `template:` fan wrapper (since 2022.x — wraps any relay state or upstream `fan.*` entity into a virtual `fan.*` entity that exposes the standard `percentage` + `preset_mode` + the `fan.set_percentage` service contract) + the HA core `zwave_js` integration (since 2022.x — surfaces Z-Wave fan controllers like the Zooz ZEN17 + Aeotec Nano Switch + Inovelli LZW42 as `fan.*` entities) + the HA core `zha` integration (since 2022.x — surfaces Zigbee fan controllers like generic-Zigbee fan controllers + the Tuya Zigbee fan family as `fan.*` entities) + the HACS `bond` integration (HACS — surfaces Bond Home RF-bridge-controlled ceiling fans + Hunter SIMPLEconnect fans as `fan.*` entities) + the HACS `tuya` integration (HACS — surfaces Tuya Wi-Fi smart fans as `fan.*` entities) + the HA core `mqtt` integration (since 2022.x — surfaces MQTT-driven fan controllers + Tasmota-flashed fan controllers as `fan.*` entities). The 8 `rc_fan_*` contract tiles are the vendor-neutral layer the dashboard + OpenClaw queries use; the actual fan-controller path is provided by the upstream HA core `fan` integration + the HA core `template:` fan wrapper + the HA core `zwave_js` integration + the HA core `zha` integration + the HA core `mqtt` integration + the HACS `bond` integration + the HACS `tuya` integration + the HACS `hunterdouglas_simplify` integration + the HA core Shelly integration (RoamCore does NOT fork any of these).

## The 4 operator-pickable paths

- **Path A — Smart fan controllers (Z-Wave / Zigbee / MQTT).** Default for operators with existing Z-Wave / Zigbee / MQTT infrastructure + 12 V / 24 V fans wired to fan controllers. Path A1 — Z-Wave fan controller (Zooz ZEN17 + Aeotec Nano Switch + Inovelli LZW42 + the HA core `zwave_js` integration). Path A2 — Zigbee fan controller (generic-Zigbee fan controllers + the HA core `zha` integration). Path A3 — Generic-tasmota-flashed fan controller (any 12 V / 24 V fan relay + Tasmota + the HA core `mqtt` integration).

- **Path B — Wi-Fi / BLE smart fan (Bond Home / Hunter SIMPLEconnect + Tuya).** Default for operators with Wi-Fi / BLE smart fans (Bond Home RF-bridge-controlled ceiling fans + Hunter SIMPLEconnect Wi-Fi/BLE fans + Tuya Wi-Fi smart fans). Path B1 — Bond Home RF-bridge + ceiling fan (the HACS `bond` integration). Path B2 — Hunter SIMPLEconnect Wi-Fi/BLE fan (the HACS `hunterdouglas_simplify` integration). Path B3 — Tuya Wi-Fi smart fan (the HACS `tuya` integration).

- **Path C — Generic 12 V / 24 V fan + relay (no smart fan controller).** Default for operators with a basic 12 V / 24 V ventilation fan + a relay (Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano Switch) + the HA core Shelly integration OR the HA core `zwave_js` integration + the HA core `template:` fan wrapper that creates a virtual `fan.ventilation` entity.

- **Path D — All-in-one smart fan (MaxxAir / Fan-Tastic / MAXXAIR Deluxe).** Default for operators with a MaxxAir / Fan-Tastic / MAXXAIR Deluxe rooftop vent fan (the manufacturer-recommended integration surfaces the fan as a `fan.*` entity + the rooftop vent cover as a `cover.*` entity). The rain-sensor safety block forces the fan OFF + the cover CLOSED when the rain sensor trips.

## Setup recipe (one-paragraph)

1. Have at least 1 controllable fan installed (rooftop vent fan + circulation fan + bathroom exhaust fan).
2. Pick ONE of the four fan-controller paths (Path A / Path B / Path C / Path D).
3. Set up the chosen path:
   - **Path A — Smart fan controllers:** install the HA core `zwave_js` integration OR the HA core `zha` integration OR the HA core `mqtt` integration + wire the fan controller into HA + verify the upstream `fan.*` entity exists.
   - **Path B — Wi-Fi / BLE smart fan:** install the HACS `bond` integration OR the HACS `tuya` integration OR the HACS `hunterdouglas_simplify` integration + wire the smart fan into HA + verify the upstream `fan.*` entity exists.
   - **Path C — Generic 12 V / 24 V fan + relay:** install the HA core Shelly integration OR the HA core `zwave_js` integration + wire the relay into HA + create a `template:` fan wrapping the relay state into a virtual `fan.ventilation` entity.
   - **Path D — All-in-one smart fan:** install the rooftop vent fan per the manufacturer instructions + wire it into HA via the manufacturer-recommended integration + verify the upstream `fan.*` entity + the upstream `cover.*` entity exist.
4. Configure temperature + humidity via the HVAC basics Wave 3 #49 connection's `sensor.rc_hvac_interior_temperature` + `sensor.rc_hvac_interior_humidity` (REQUIRED — the §8.1 + §8.2 auto-fan automations read from these tiles).
5. Configure the optional rain sensor for the rooftop rain-safe mode (REQUIRED for Path D rooftop vent fans; OPTIONAL for Path A / Path B / Path C — the §8.4 rain-sensor hard-block automation reads from `binary_sensor.rc_fan_rain_sensor_active`).
6. Configure optional time-of-day / sunrise-sunset for the Sleep mode suppression via the time-atomic Wave 3 #55 connection.
7. Configure the operator-facing `fan.rc_fan_main` contract tile to point at the operator's chosen upstream `fan.*` entity.
8. Configure `select.rc_fan_mode` to the operator's chosen starting mode (default `auto`).
9. Wire the FIVE §8 automations (auto-fan on humidity high + auto-fan on temperature high + manual override via `button.rc_fan_run_now_15min` + rain-sensor hard-block + Sleep mode suppression via `select.rc_mode`).
10. Verify: check `binary_sensor.rc_fan_active` reflects the upstream fan state + check `sensor.rc_fan_speed_percent` reflects the upstream `percentage` attribute + trigger `button.rc_fan_run_now_15min` + verify the fan runs for 15 minutes.

Full howto: see [`docs/recipe.md`](docs/recipe.md).

## Why tier-b, not tier-a

Tier-a would require a RoamCore-owned fan engine + integration code + integration tests against a real fan bench (a controlled environment with a Z-Wave fan controller + a 12 V fan + a Bond Home + a MaxxAir + a rain sensor + canned fixture responses for humidity/temperature/rain events — all wired together in a controlled environment). We have no operator-side fan bench on the CI to integration-test against (the bench requires the operator's chosen upstream fan controller + a 12 V / 24 V fan + a humidity sensor + a temperature sensor + a rain sensor + canned fixture responses for humidity/temperature/rain events — all wired together in a controlled environment). Tier-b is the honest tier: MaxxAir / Fan-Tastic / MAXXAIR Deluxe / Bond Home / Hunter SIMPLEconnect / Tuya / Z-Wave / Zigbee / Shelly / Zooz / Aeotec / Inovelli are all upstream / vendor / HACS code (not RoamCore-owned); the RoamCore wrapper is a thin upstream-entity-aggregation layer + the contract layer + the rain-sensor safety block. The recipe is sound but we cannot claim one-tap automation.

The legacy catalog page (the legacy spec — 14-line tier-c stub, originally listed "Fans are a simple upgrade that massively improves comfort: airflow, condensation control, cooking smells, and keeping the van livable in warm weather. This section covers fan controllers, vent fans, and easy automations like 'run when humidity is high'" with no recipe + no contract + no vendor-neutral coverage — just a placeholder) is now superseded by this tier-b recipe connection.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "fans"` marker for the audit.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded by this slice): [the legacy spec](../../the legacy spec)
- HA core `fan` integration (the canonical umbrella): https://www.home-assistant.io/integrations/fan/
- HA core `zwave_js` integration (Path A1 Z-Wave fan controllers): https://www.home-assistant.io/integrations/zwave_js/
- HA core `zha` integration (Path A2 Zigbee fan controllers): https://www.home-assistant.io/integrations/zha/
- HA core `mqtt` integration (Path A3 generic-tasmota-flashed fan controllers): https://www.home-assistant.io/integrations/mqtt/
- HA core Shelly integration (Path C1 relay-driven fans): https://www.home-assistant.io/integrations/shelly/
- HA core `template:` fan wrapper (Path C2 relay-state-to-virtual-fan): https://www.home-assistant.io/integrations/template/
- HACS `bond` integration (Path B1 Bond Home + ceiling fans): https://hacs.xyz/docs/integrations/active
- HACS `tuya` integration (Path B3 Tuya Wi-Fi smart fans): https://hacs.xyz/docs/integrations/active
- HACS `hunterdouglas_simplify` integration (Path B2 Hunter SIMPLEconnect fans): https://hacs.xyz/docs/integrations/active
- HVAC basics (the `sensor.rc_hvac_interior_temperature` + `sensor.rc_hvac_interior_humidity` tiles for the §8.1 + §8.2 auto-fan automations): `connections/hvac-basics/` (Wave 3 #49)
- Time-atomic (the time-of-day / sunrise-sunset primitives for the §8 Sleep mode suppression): `connections/time-atomic/` (Wave 3 #55)
- Mode/automation-builder (the `select.rc_mode` tile source of truth for the §8.5 Sleep-mode suppression): `connections/smart-automations/` (Wave 2 #23)
- Approach lights (the canonical ON-LAN-only lighting scene that mirrors the Sleep-mode pattern): `connections/approach-lights/` (Wave 3 #52)
- NFC tags (the optional "tag-trigger-manual-override" affordance that uses NFC scan events to trigger `button.rc_fan_run_now_15min`): `connections/nfc-tags/` (Wave 3 #57)
- RoamCore entity naming: `docs/reference/rc-entity-naming.md` (the `ventilation` subsystem was added by this slice)