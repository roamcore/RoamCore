# Heated floors + engine pre-heat (cold-weather comfort)

**Tier:** B (recipe)
**Category:** HVAC
**Status:** beta

## What this connection is

Heated floors + optional engine pre-heat — cold-weather comfort controls for vans — are the **foundation** of every "Warm up" automation in winter van life: pre-warm the cabin when the operator's phone reconnects to the LAN and it's been >24h since the last warm-up, start the engine pre-heat 30 min before the morning commute when ambient temp < 5 °C, throttle the floor heat to setpoint -3 °C during Stealth silent hours, lock the floor to a min setpoint of 10 °C in Sleep mode for frost protection, refuse to start the floor + engine preheat when inverter SOC < 20 % AND shore is disconnected (heated floor + engine preheat together can pull 10–30 A sustained), and surface a single "warm up the van" command that orchestrates floor heat + interior temp + engine preheat together. The signal that drives all of those is a vendor-neutral "what's the cabin doing right now?" layer that the rest of RoamCore can rely on — and that layer is what this connection provides.

RoamCore ships **no** native heated-floor controller or engine pre-heat controller. We RECIPE the well-understood combination of three upstream operator-side paths and a translation layer that maps each upstream `climate.*` (Path A smart thermostat OR Path B HA core `generic_thermostat:`) + upstream `switch.*` (Path B relay OR Path C engine preheat relay) + upstream `sensor.*` (temperature probes) into a vendor-neutral `rc_hvac_*` contract layer. The three paths:

- **Path A — Smart thermostat** (recommended for operators who already own a Mysa / Shelly H&T / generic-Zigbee thermostat). The vendor integration's `climate.*` entity is already exposed in HA (the vendor's own GUI flow varies by vendor). The recipe shows the entity_id surfacing + the `set_hvac_mode` / `set_temperature` service calls + a `template:` sensor that derives the "Heating" / "Maintaining" / "Off" states from the climate's `hvac_action` attribute (which is the canonical HA climate attribute exposed by all climate-domain integrations since 2022.x).

- **Path B — Generic thermostat** (no smart thermostat; just a temperature probe + a relay-driven heater). HA core `generic_thermostat:` wraps a `sensor.interior_temp` (DS18B20 1-Wire / Zigbee / Shelly H&T / etc.) + a `switch.heater_relay` (Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano Switch or a relay on ESPHome) into a virtual `climate.floor_heater`. Includes the `min_temp` / `max_temp` / `cold_tolerance` / `hot_tolerance` / `keep_alive` settings. `generic_thermostat` exposes a GUI flow since 2022.x.

- **Path C — Optional engine pre-heat** (Webasto / Espar / Eberspächer / DIY coolant-loop heater). The heater is wired through a relay (Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano Switch or a relay on ESPHome) OR through a CAN bus gateway for the higher-end Thermo Top Evo / Hydronic S3 (the gateway exposes the heater as a `climate.*` entity OR a `switch.*` entity depending on the gateway vendor). The recipe shows the `switch.engine_preheat` entity + a `binary_sensor.engine_preheat_active` template that derives "is the engine preheat actually producing heat" from the cabin temp trend — when the switch is on AND cabin temp is rising over a 5-minute window → active.

All three paths land on the same vendor-neutral contract layer via `rc_hvac_*` dashboard tiles:

- `climate.rc_hvac_floor_thermostat` — vendor-neutral climate entity (off / heat / auto modes + setpoint control).
- `sensor.rc_hvac_floor_current_temp` — current temperature reading from the climate's `current_temperature` attribute.
- `sensor.rc_hvac_interior_temp` — interior air probe (DS18B20 1-Wire / Zigbee / Shelly H&T — separate from the floor probe).
- `binary_sensor.rc_hvac_floor_heating_active` — TRUE when the climate's `hvac_action == "heating"`.
- `binary_sensor.rc_hvac_floor_maintaining` — TRUE when the climate's `hvac_action == "idle"` while setpoint > current_temp (floor is warm enough; heater is off; maintaining the temp).
- `binary_sensor.rc_hvac_floor_off` — TRUE when the climate's `hvac_action == "off"` OR state == "off".
- `switch.rc_hvac_floor_heater` — explicit heater on/off affordance (Path B relay-driven; Path A uses climate `turn_on` / `turn_off`).
- `number.rc_hvac_floor_setpoint` — numeric setpoint control (delegates to `climate.set_temperature` service call).
- `select.rc_hvac_floor_mode` — `auto` (RoamCore modes drive the floor heat + low-voltage lockout + shore-power-aware throttling), `eco` (lower setpoint when off-shore), `boost` (disable mode-aware throttling for service work), `off` (no heat at all — frost protection only).
- `binary_sensor.rc_hvac_floor_low_voltage_lockout` — TRUE when inverter SOC < 20 % (cross-references `sensor.rc_power_battery_soc` from the Victron `connections/victron/` recipe) AND `binary_sensor.rc_power_shore_connected == off`. The `low_voltage_lockout` tile gates the heater + engine preheat on/off commands (any heat request is rejected while the tile is TRUE; the operator can acknowledge the lockout via a mode override).
- `switch.rc_hvac_engine_preheat` — optional Path C engine preheat on/off affordance (Webasto / Espar / Eberspächer / DIY coolant-loop).
- `binary_sensor.rc_hvac_engine_preheat_active` — TRUE when the engine preheat switch is on AND cabin temp is rising over a 5-minute window (derives "is the engine preheat actually producing heat" from the cabin temp trend).
- `sensor.rc_hvac_engine_preheat_runtime_min` — daily runtime tracker (utility_meter integration on top of the engine preheat switch).

This fills the `hvac` subsystem slot in `docs/reference/rc-entity-naming.md` — a forward-compatible addition that mirrors how `media` was added by the Music Assistant slice + how `presence` was backfilled alongside the bluetooth-wifi-presence slice + how `bed_lift` was added alongside the happijac slice.

RoamCore does **not** ship a heated floor, a thermostat, a temperature probe, an engine preheat, or any vendor-specific controller. The HA core `generic_thermostat` + the operator's choice of climate-domain vendor integration (Path A) or HA core `generic_thermostat` (Path B) + the upstream `switch.*` relay (Path C) are the upstream truth; RoamCore layers a contract on top: the `rc_hvac_*` dashboard tiles + the OpenClaw queries that bind to those contract entities ("warm up the van", "set floor heat", "turn off floor heat", "floor temperature", "cabin temperature", "is floor heating?", "is floor maintaining?", "is floor off?", "is floor low-voltage locked?", "set floor mode", "start engine preheat", "stop engine preheat", "is engine preheat running?", "engine preheat runtime today").

## Setup recipe (one-paragraph)

1. Decide which path fits your van: **Path A** — Smart thermostat (you already own a Mysa / Shelly H&T / generic-Zigbee thermostat that exposes a `climate.*` entity in HA); OR **Path B** — Generic thermostat (no smart thermostat; you have a temperature probe + a relay-driven heater + HA core `generic_thermostat:`); **Path C** — Optional engine pre-heat (Webasto / Espar / Eberspächer / DIY coolant-loop via a relay or CAN bus gateway; Path C is optional and additive to A or B).
2. Wire the prerequisites FIRST (the recipe §2 walks through these — Path A needs the smart thermostat + the vendor integration configured; Path B needs the temperature probe (interior air minimum + optional floor probe) + the relay-driven heater + the HA core `generic_thermostat:` YAML with `min_temp` / `max_temp` / `cold_tolerance` / `hot_tolerance` / `keep_alive` settings; Path C needs the engine preheat hardware + the relay or CAN bus gateway). The operator MUST not skip the safety prerequisites — the `low_voltage_lockout` tile refuses heat + engine preheat on/off commands until the cross-references to Victron are wired.
3. Wire the upstream device. Path A: configure the vendor integration; the upstream `climate.floor_thermostat` entity appears. Path B: wire the relay to the heater + the temperature probe + the `generic_thermostat:` YAML; the upstream `climate.floor_heater` entity appears. Path C: wire the relay to the engine preheat; the upstream `switch.engine_preheat` entity appears.
4. Wire the HA core `template:` climate wrapper + template sensors + template binary_sensors + template switch + template number + template select that synthesizes the `rc_hvac_*` contract tiles (recipe §3 / §4 / §5 walk through the template YAML for each path).
5. Create the `rc_hvac_*` contract tiles (or import the recipe's `template:` helpers from the recipe §5 helper YAML). The recipe walks through synthesizing each `rc_hvac_*` tile from the upstream `climate.*` + `switch.*` + `sensor.*` + the inverter SOC + shore-connection tiles from the Victron recipe.
6. Verify the five safety interlocks (recipe §7 walks through each): low-voltage lockout (`rc_hvac_floor_low_voltage_lockout`), shore-power-aware throttling, mode-aware Stealth/Sleep/Boost lockouts, presence-aware pre-warm when operator phone reconnects, frost-protection automation (the `select.rc_hvac_floor_mode` operator-tunable overrides; RoamCore modes drive the `auto` lane).
7. Enable the recipe §7 automations ("Warm up" scene (Heating + Maintaining + Off state machine + low-voltage lockout pre-check), shore-power-aware (heat aggressively when on shore, conserve when off), mode-aware (Stealth silent hours → reduce floor heat to setpoint -3 °C, Sleep mode → min setpoint = 10 °C, Boost mode disables Stealth/Sleep throttling for service), low-voltage lockout when SOC < 20 %, presence-aware pre-warm when operator's phone reconnects to the LAN + it's been >24h since the last warm-up, engine pre-heat schedule (auto-start at 06:30 weekdays when mode is Morning + ambient temp < 5 °C)).
8. Reload the RoamCore dashboard; the `rc_hvac_*` contract tiles appear under the HVAC section.

Full howto with copy-pasteable YAML for the helpers, automations, Path A / Path B / Path C wiring, the `generic_thermostat` YAML, the engine preheat CAN bus gateway wiring, the five safety interlocks in full, mode-aware exceptions, and the tier-a promotion outline: see [`docs/recipe.md`](docs/recipe.md).

## Why tier-b, not tier-a

Tier-a requires a working RoamCore-owned `config_flow.py`, integration tests against a real heated-floor + relay + temperature probe + optional engine preheat bench on CI, and `wizard.one_tap: true`. We have no operator pin choice on the CI bench to integration-test against (no heated floor, no thermostat, no relay, no temperature probe, no engine preheat, no CAN bus gateway). The operator's exact Path A vs Path B vs Path C choice + the relay pin / probe pin / engine preheat pin choice is a wiring decision that requires the operator's physical install context, and there's no canonical RoamCore-owned upstream HA integration that does what this connection recipes. So this connection is honestly beta-tier: the recipe is sound but we cannot claim one-tap automation. The [`tests/test_connection_yml.py`](tests/test_connection_yml.py) file asserts the manifest is honest about its tier — including the defensive `test_safety_interlocks_are_documented` assertion that guards the future tier-a promotion's hard-enforced safety interlock asserts — that's the only test we can ship today.

When a real heated-floor + relay + temperature probe + optional engine preheat bench lands (a bench with at least one Path A smart thermostat OR one Path B relay-driven heater + temperature probe + a Path C engine preheat simulator + the five safety interlock sources that the §10 promotion outline describes), this connection is the candidate to promote to tier-a: add a native `config_flow.py` that walks the operator through Path A vs Path B vs Path C + relay pin / probe pin / engine preheat pin declaration, add an integration test that asserts the five safety interlocks (`rc_hvac_floor_low_voltage_lockout`, shore-power-aware throttling, mode-aware lockouts, presence-aware pre-warm, frost-protection automation) all flip to the expected state when wired to canned fixture responses, add a second integration test that asserts a setpoint change on `number.rc_hvac_floor_setpoint` triggers the right tile updates on `climate.rc_hvac_floor_thermostat` + the 3× state binary_sensors, and flip `tier_requirements` to include `working_config_flow` + `integration_test_passes` + `no_manual_yaml_required` + `safety_interlocks_hard_enforced_in_roamcore_code`.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "heated_floors"` marker for the audit.
- `docs/recipe.md` — the full howto (Path A smart thermostat wiring + the entity_id surfacing + the set_hvac_mode / set_temperature service calls + the template sensor that derives "Heating" / "Maintaining" / "Off" states from the climate's hvac_action attribute, Path B HA core generic_thermostat: YAML wrapping a sensor + a switch with min_temp / max_temp / cold_tolerance / hot_tolerance / keep_alive, Path C optional engine pre-heat via a relay or CAN bus gateway + the binary_sensor.engine_preheat_active template that derives "is the engine preheat actually producing heat" from the cabin temp trend, the five safety interlocks in full, six §7 automations, eight §8 troubleshooting entries, privacy, tier-a promotion outline).
- `tests/test_connection_yml.py` — manifest honesty checks (including the `test_safety_interlocks_are_documented` defensive guard for the future tier-a promotion).

## See also

- Legacy catalog page (now superseded by the connection manifest):
  [the legacy spec](../../the legacy spec)
- Catalog category index: the legacy spec
- Victron connection (companion for the §7 low-voltage lockout cross-reference to `sensor.rc_power_battery_soc` + `binary_sensor.rc_power_shore_connected`):
  `connections/victron/`
- Bluetooth / Wi-Fi presence connection (companion for the §7 "presence-aware pre-warm when operator's phone reconnects to the LAN" automation — uses the `rc_presence_*` contract tiles for the presence signal):
  `connections/bluetooth-wifi-presence/`
- Happijac connection (companion for the §7 frost-protection automation — if mode is `auto` AND engine preheat is off AND interior temp < 5 °C → enable gentle floor heating for frost protection; uses the `select.rc_bed_lift_mode` for the mode signal):
  `connections/happijac/`
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`
- OpenClaw JSON API (the contract `summary_keys` land here): `docs/reference/openclaw-json-api.md`