# HVAC basics (heating/cooling foundations)

**Tier:** B (recipe)
**Category:** hvac
**Status:** beta

## What this connection is

HVAC basics — cabin heating/cooling foundations for vans — is the **umbrella** for thermostat + diesel heater + rooftop AC + cabin ventilation control. The single "is ANY HVAC device active?" tile aggregates heater + AC + fan + thermostat state into one dashboard indicator, the cabin temperature + humidity sensors surface the cabin's current climate, the outdoor temperature sensor feeds the frost + over-temp safety warnings, the cabin thermostat + cabin fan + fan-speed select + HVAC-mode select cover the day-1 control affordances, and the six safety interlocks (frost warning / over-temp warning / low-voltage lockout / mode-aware lockouts) catch the extreme-temp + low-battery scenarios that are safety-relevant in van life.

RoamCore ships **no** native HVAC appliance. We RECIPE the well-understood combination of four upstream operator-side paths and a translation layer that maps the upstream `climate.*` / `switch.*` / `fan.*` / `sensor.*` / `select.*` entities into a vendor-neutral `rc_hvac_*` contract layer. The four paths:

- **Path A — Generic thermostat (recommended when operator already has a smart thermostat).** Vendor: `generic_thermostat` (HA core, GUI flow since 2022.x) — wraps a `sensor.<probe>` + a `switch.<heater_relay>` into a virtual `climate.<thermostat>`. Alternatives: `ecobee` (cloud-bridged smart thermostat), `nest` (cloud-bridged), `mitsubishi` (Kumo Cloud / local-API for Mitsubishi mini-splits), `daikin` (local-API for Daikin mini-splits), and any other HA core climate integration. The upstream integration exposes `climate.<name>` entities directly.

- **Path B — Diesel heater (Webasto / Eberspächer / Chinese diesel / Vevor / Chinese planer-style).** Wired via the upstream `esphome` integration (HA core + HACS, GUI flow since 2023.x) — the ESPHome YAML exposes the heater's glow plug + main blower + combustion fan as `switch.*` entities, the safety thermistor as `sensor.*`, and the flame-sense wire as `binary_sensor.*`. Alternative for heaters with an ESPHome-MQTT bridge: the upstream `mqtt` integration (GUI flow since 2022.x) which exposes the same set of entities.

- **Path C — Rooftop AC (Furrion / Dometic / MaxxAir / Coleman).** Wired via IR-bridge (`broadlink` HA core integration, GUI flow since 2022.x, OR `mqtt_ir_hub` HACS integration, GUI flow since 2023.x) — the IR-bridge learns the AC's remote codes and exposes AC power + mode + fan speed + temperature as `switch.*` + `fan.*` + `select.*` entities. Alternative for AC units with a native HA integration (e.g. Furrion Chill with their own adapter): the upstream vendor integration.

- **Path D — Cabin ventilation (cabin fan).** Wired via the HA core `fan` integration (GUI flow since 2022.x) — MaxxAir / Fan-Tastic Vent / roof-vent switches + cross-flow vent control. The fan integration exposes `fan.<name>` entities directly. Most van cabin fans are simple 3-speed (low/med/high) or fully variable; the `select.rc_hvac_fan_speed` tile handles the speed selection.

All four paths land on the same vendor-neutral contract layer via 11 `rc_hvac_*` dashboard tiles.

## Setup recipe (one-paragraph)

1. Decide which path fits your van: **Path A** — generic thermostat via generic_thermostat / ecobee / nest / mitsubishi / daikin (most common for vans with a smart thermostat); **Path B** — diesel heater via esphome or mqtt (Webasto / Eberspächer / Chinese diesel / Vevor); **Path C** — rooftop AC via IR-bridge (Broadlink / MQTT-IR-Hub) or native integration (Furrion / Dometic / MaxxAir / Coleman); **Path D** — cabin ventilation via HA core `fan` (MaxxAir / Fan-Tastic Vent / roof-vent).
2. Wire the prerequisites FIRST (the recipe §2 walks through these). The operator MUST not skip the upstream integration prerequisite (the recipe won't work if the climate / esphome / mqtt / broadlink / fan integration is not already configured).
3. Wire the upstream entity. Path A: configure the climate integration; Path B: flash the ESPHome firmware OR configure the MQTT bridge; Path C: learn the IR codes on the bridge; Path D: pair the fan.
4. Wire the HA core `template:` (or HA core `entity` customize-domain alias) that maps the upstream entity to one of the 11 contract tiles (`rc_hvac_cabin_thermostat` / `rc_hvac_cabin_temperature` / `rc_hvac_cabin_humidity` / `rc_hvac_heater_active` / `rc_hvac_ac_active` / `rc_hvac_cabin_fan` / `rc_hvac_fan_speed` / `rc_hvac_outdoor_temperature` / `rc_hvac_frost_warning` / `rc_hvac_over_temp_warning` / `rc_hvac_mode`).
5. Verify the four §7 safety interlocks (frost warning / over-temp warning / low-voltage lockout / mode-aware lockouts).
6. Enable the six §8 automations (Stealth auto-lower fan / Sleep eco-mode / Boost disable-mode-aware-lockouts / frost auto-heat / over-temp auto-cool + alert / mode-aware morning pre-warm).
7. Reload the RoamCore dashboard.

Full howto: see [`docs/recipe.md`](docs/recipe.md).

## Why tier-b, not tier-a

Tier-a requires a working RoamCore-owned `config_flow.py`, integration tests against a real HVAC bench (a thermostat + a heater + an AC + a fan), and `wizard.one_tap: true`. We have no operator-side HVAC bench on the CI to integration-test against (the bench requires physical hardware: a thermostat + a heater + an AC + a fan + a temperature/humidity sensor + a relay board, all wired together in a controlled environment). So this connection is honestly beta-tier: the recipe is sound but we cannot claim one-tap automation.

The original legacy catalog page (`docs/catalog/hvac/hvac-basics.md`) mis-claimed "Support tier: A (RoamCore native)" — that claim was aspirational and false. RoamCore does NOT ship a native HVAC appliance; this connection is tier-b and the supersession banner on the legacy page reflects that.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "hvac_basics"` marker for the audit.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded): [`docs/catalog/hvac/hvac-basics.md`](../../docs/catalog/hvac/hvac-basics.md)
- Heated floors + engine pre-heat connection (companion for the floor heat + engine pre-heat surface; Wave 3 #44): `connections/heated-floors/`
- Victron (power) connection (companion for the §7 low-voltage lockout — diesel heater + AC pull 10–30 A sustained): `connections/victron/`
- Mode / automation-builder connection (companion for the §7 mode-aware lockouts + the §8.1 Stealth / §8.2 Sleep / §8.3 Boost automations): `connections/mode-automation-builder/`
- Bluetooth / Wi-Fi presence connection (companion for the §7 over-temp warning "pets left in van" escalation): `connections/bluetooth-wifi-presence/`
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`
