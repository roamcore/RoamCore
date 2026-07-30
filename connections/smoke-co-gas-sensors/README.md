# Smoke / CO / gas sensors (lifesafety)

**Tier:** B (recipe)
**Category:** Safety
**Status:** beta

## What this connection is

Smoke / CO / propane-LPG / methane / natural-gas safety sensors — lifesafety detectors for vans — are the **lifesafety foundation** of every RoamCore install: early warning while sleeping, peace of mind when leaving pets inside (heat / CO risk), loud sirens + phone notifications on any alarm, mode-aware silencing for known false-positive sources (cooking smoke), the monthly test cycle to keep the operator confident the alarms actually work, and the cross-reference to the smart-automations connection for "if alarm → notify all devices + unlock deadbolts for emergency egress." The signal that drives all of those is a vendor-neutral "is anything dangerous happening right now?" layer that the rest of RoamCore can rely on — and that layer is what this connection provides.

RoamCore ships **no** native smoke / CO / gas safety controller. We RECIPE the well-understood combination of three upstream operator-side paths and a translation layer that maps each upstream `binary_sensor.*` (Path A Zigbee IAS Zone OR Path B Z-Wave Notification CC OR Path C ESPHome threshold-derived template) + upstream `sensor.*` (battery % per ZHA / zwave_js / ESPHome) + upstream `button.*` / `select.*` (silence / test / mode) into a vendor-neutral `rc_safety_*` contract layer. The three paths:

- **Path A — Zigbee via ZHA** (recommended for operators who already own a Zigbee coordinator). Pair a Zigbee smoke / CO / gas detector with ZHA; the auto-discovered `binary_sensor.smoke_*` / `binary_sensor.carbon_monoxide_*` / `binary_sensor.gas_*` entity_ids appear in HA. Some vendors expose only an IAS Zone `binary_sensor` for the alarm state, others expose a `sensor` for the battery separately. The recipe shows the recommended ZHA device signature overrides for vendors that don't ship clean signatures (Heiman / Develco / First Alert / X-Sense / etc.).

- **Path B — Z-Wave via zwave_js** (no Zigbee; Z-Wave coordinator). Pair a Z-Wave smoke / CO detector with zwave_js; the auto-discovered `binary_sensor.smoke_*` / `binary_sensor.carbon_monoxide_*` entity_ids appear in HA. Some Z-Wave detectors use the Notification CC to differentiate test vs alarm vs low-battery states.

- **Path C — DIY MQ-series analog gas sensor via ESPHome** (no Zigbee / Z-Wave; ESP32 + analog gas sensor on an ADC pin + relay-driven siren on a GPIO). The ESPHome integration in HA core since 2023.x exposes a `sensor.*` for the analog reading; a `binary_sensor.*` template derives the alarm state when the analog reading crosses the per-gas threshold (e.g. `binary_sensor.lpg_alarm: lambda: 'return id(mq9_reading).state > 400.0;'`). The recipe walks through the calibration routine (warm-up time + burn-in time + threshold tuning for the specific gas of interest) and the relay-driven siren GPIO.

All three paths land on the same vendor-neutral contract layer via `rc_safety_*` dashboard tiles:

- `binary_sensor.rc_safety_smoke_detected` — TRUE when any upstream smoke sensor reports smoke.
- `binary_sensor.rc_safety_co_detected` — TRUE when any upstream CO sensor reports CO.
- `binary_sensor.rc_safety_gas_detected` — TRUE when any upstream gas (LPG / propane / methane / natural gas) sensor reports gas above its alarm threshold.
- `binary_sensor.rc_safety_any_alarm_active` — aggregate: smoke OR co OR gas (single subscription point for downstream sirens + notifications).
- `binary_sensor.rc_safety_siren_active` — TRUE when the local siren is currently sounding.
- `binary_sensor.rc_safety_alarm_in_test_mode` — TRUE when the alarms are in test mode (silencing for testing — operator schedules a monthly test via `button.rc_safety_test_alarm`).
- `binary_sensor.rc_safety_low_battery_warning` — TRUE when any upstream sensor battery is below 20 % (combined with `sensor.rc_safety_lowest_battery_pct` the operator knows which sensor needs a battery swap).
- `binary_sensor.rc_safety_sensor_offline` — TRUE when any upstream sensor has not checked in within its expected heartbeat window (a silent safety sensor is the most dangerous kind).
- `sensor.rc_safety_lowest_battery_pct` — numeric battery percentage of the lowest-battery upstream sensor.
- `button.rc_safety_silence_alarm` — explicit "silence the siren + acknowledge the alarm" affordance (operator may want to silence when they have confirmed the alarm is a false positive, e.g. cooking smoke).
- `button.rc_safety_test_alarm` — explicit "run the test cycle" affordance (operator schedules a monthly test via a helper automation).
- `select.rc_safety_alarm_mode` — operator-tunable mode: `armed` (all alarms active; sirens fire on detection), `night_only` (only fire sirens + notifications when RoamCore mode is Sleep; avoids waking the neighbour when cooking in Morning / Afternoon), `silenced` (no sirens; only phone notifications — for known false-positive sources like a smoky stove), `disabled` (alarms tracked but not acted on; for service).

This fills the `safety` subsystem slot in `docs/reference/rc-entity-naming.md` — a forward-compatible addition that mirrors how `media` was added by the Music Assistant slice + how `presence` was backfilled alongside the bluetooth-wifi-presence slice + how `bed_lift` was added alongside the happijac slice + how `hvac` was added alongside the heated-floors slice.

RoamCore does **not** ship a smoke / CO / gas safety sensor, a relay-driven siren, an ESPHome controller, or any vendor-specific detector. The HA core `binary_sensor` + `mqtt` + `zha` + `zwave_js` + `esphome` integrations are the upstream truth; RoamCore layers a contract on top: the `rc_safety_*` dashboard tiles + the OpenClaw queries that bind to those contract entities ("is smoke detected?", "is CO detected?", "is gas detected?", "is any safety alarm active?", "silence safety alarm", "trigger safety siren", "is siren active?", "battery low — smoke alarm", "battery low — CO alarm", "is alarm in test mode?").

## Setup recipe (one-paragraph)

1. Decide which path fits your van: **Path A** — Zigbee via ZHA (you already own a Zigbee coordinator + a Zigbee smoke / CO / gas detector; the ZHA GUI flow pairs it); OR **Path B** — Z-Wave via zwave_js (you already own a Z-Wave coordinator + a Z-Wave smoke / CO detector; the zwave_js GUI flow pairs it); **Path C** — DIY MQ-series analog gas sensor via ESPHome (an ESP32 + an MQ-2 / MQ-3 / MQ-5 / MQ-7 / MQ-9 / MQ-135 analog gas sensor on an ADC pin + a relay-driven siren on a GPIO; the ESPHome integration exposes the analog reading + a threshold-derived binary_sensor template).
2. Wire the prerequisites FIRST (the recipe §2 walks through these — Path A needs the Zigbee coordinator + the Zigbee smoke / CO / gas detector paired via the ZHA GUI flow; Path B needs the Z-Wave coordinator + the Z-Wave smoke / CO detector paired via the zwave_js GUI flow; Path C needs the ESP32 + the analog gas sensor on an ADC pin + the relay-driven siren on a GPIO + the ESPHome integration exposing the analog reading). The operator MUST not skip the safety prerequisites — the `binary_sensor.rc_safety_sensor_offline` tile refuses to declare an alarm active until the upstream sensor has checked in within its expected heartbeat window.
3. Wire the upstream device. Path A: pair the Zigbee detector via ZHA; the upstream `binary_sensor.smoke_*` / `binary_sensor.carbon_monoxide_*` / `binary_sensor.gas_*` entities appear. Path B: pair the Z-Wave detector via zwave_js; the upstream `binary_sensor.smoke_*` / `binary_sensor.carbon_monoxide_*` entities appear. Path C: flash the ESPHome YAML to the ESP32; the upstream `sensor.mq9_reading` + `binary_sensor.lpg_alarm` entities appear.
4. Wire the HA core `template:` binary_sensor + template sensor + template button + template select that synthesizes the `rc_safety_*` contract tiles (recipe §3 / §4 / §5 walk through the template YAML for each path).
5. Create the `rc_safety_*` contract tiles (or import the recipe's `template:` helpers from the recipe §5 helper YAML). The recipe walks through synthesizing each `rc_safety_*` tile from the upstream `binary_sensor.*` + `sensor.*` + the mqtt `availability` topic + the operator-tunable mode select.
6. Verify the four §6 lifesafety interlocks (recipe walks through each): sensor-not-offline detection (any upstream sensor silent > its heartbeat window → `rc_safety_sensor_offline` flips TRUE), low-battery pre-warning (any sensor battery < 20 % → `rc_safety_low_battery_warning` flips TRUE; cross-reference `sensor.rc_safety_lowest_battery_pct`), any-alarm aggregate (`rc_safety_any_alarm_active` = smoke OR co OR gas), mode-aware lockout (when `select.rc_safety_alarm_mode` = `disabled`, sirens + notifications are suppressed).
7. Enable the recipe §7 automations: "loud siren + phone notification" on any alarm (the day-1 affordance), "auto-unlock deadbolts + flash all lights" on CO detection for emergency egress (cross-reference to deadbolts + approach-lights), "low-battery pre-warning" when any sensor < 20 % battery (Sunday-morning reminder), "sensor offline" detection via mqtt `last_seen` / `availability` topic (5–30 min heartbeat window), "monthly test cycle" via `button.rc_safety_test_alarm` (operator schedules via a helper automation that fires at 10am the first Sunday of each month and produces a 5-second siren burst + an audit event), "night-only mode" via `select.rc_safety_alarm_mode` set to `night_only` (sirens suppressed during cooking hours in Morning / Afternoon modes; full sirens in Sleep mode when a real alarm is most dangerous), "smart-cooking integration" via the smart-automations recipe when the hob is on + windows closed → auto-set mode to `silenced` for 30 min to avoid false-positive sirens.
8. Reload the RoamCore dashboard; the `rc_safety_*` contract tiles appear under the Safety section.

Full howto with copy-pasteable YAML for the helpers, automations, Path A / Path B / Path C wiring, the ESPHome `mq9` YAML + calibration routine + the threshold-derived `binary_sensor.lpg_alarm`, the relay-driven siren GPIO wiring, the four §6 lifesafety interlocks in full, mode-aware exceptions, and the tier-a promotion outline: see [`docs/recipe.md`](docs/recipe.md).

## Why tier-b, not tier-a

Tier-a requires a working RoamCore-owned `config_flow.py`, integration tests against a real smoke / CO / gas sensor + relay-driven siren bench on CI, and `wizard.one_tap: true`. We have no operator pin choice on the CI bench to integration-test against (no smoke / CO / gas sensor, no relay-driven siren, no ESPHome controller, no analog gas sensor). The operator's exact Path A vs Path B vs Path C choice + the analog pin / siren pin / threshold choice is a wiring decision that requires the operator's physical install context, and there's no canonical RoamCore-owned upstream HA integration that does what this connection recipes. So this connection is honestly beta-tier: the recipe is sound but we cannot claim one-tap automation. The [`tests/test_connection_yml.py`](tests/test_connection_yml.py) file asserts the manifest is honest about its tier — including the defensive `test_safety_interlocks_are_documented` assertion that guards the future tier-a promotion's hard-enforced lifesafety-interlock asserts — that's the only test we can ship today.

When a real smoke / CO / gas sensor + ESPHome + relay-driven siren bench lands (a bench with at least one Path A Zigbee detector OR one Path B Z-Wave detector OR one Path C ESP32 + analog gas sensor + a relay-driven siren simulator + the four §6 lifesafety interlock sources that the §10 promotion outline describes), this connection is the candidate to promote to tier-a: add a native `config_flow.py` that walks the operator through Path A vs Path B vs Path C + the sensor type / siren pin / battery alert threshold declaration, add an integration test that asserts the four §6 lifesafety interlocks (`rc_safety_sensor_offline`, `rc_safety_low_battery_warning`, `rc_safety_any_alarm_active`, the mode-aware `disabled` lockout) all flip to the expected state when wired to canned fixture responses, add a second integration test that asserts a sensor-trigger event (e.g. a simulated ZHA IAS Zone alarm) propagates to the right tile updates on `binary_sensor.rc_safety_smoke_detected` + `binary_sensor.rc_safety_any_alarm_active` within a defined latency budget, and flip `tier_requirements` to include `working_config_flow` + `integration_test_passes` + `no_manual_yaml_required` + `safety_interlocks_hard_enforced_in_roamcore_code`.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "smoke_co_gas"` marker for the audit.
- `docs/recipe.md` — the full howto (Path A Zigbee via ZHA wiring + the auto-discovered entity_ids + the recommended ZHA device signature overrides, Path B Z-Wave via zwave_js wiring + the Notification CC, Path C ESPHome MQ-series analog gas sensor YAML + the calibration routine + the threshold-derived binary_sensor template + the relay-driven siren GPIO, the four §6 lifesafety interlocks in full, seven §7 automations, eight §8 troubleshooting entries, privacy, tier-a promotion outline).
- `tests/test_connection_yml.py` — manifest honesty checks (including the `test_safety_interlocks_are_documented` defensive guard for the future tier-a promotion).

## See also

- Legacy catalog page (now superseded by the connection manifest):
  [`docs/catalog/safety/smoke-co-gas-sensors.md`](../../docs/catalog/safety/smoke-co-gas-sensors.md)
- Catalog category index: `docs/catalog/safety/index.md`
- MQTT connection (companion for the §6 + §7 sensor-offline cross-reference via `availability` topic for Path C ESPHome):
  `connections/mqtt/`
- Smart automations connection (companion for the §7 smart-cooking integration — when the hob is on + windows closed → auto-set mode to `silenced` for 30 min to avoid false-positive sirens):
  `connections/smart-automations/` *(slice pending)*
- Deadbolts connection (companion for the §7 "auto-unlock deadbolts + flash all lights" automation on CO detection for emergency egress):
  `connections/deadbolts/` *(slice pending)*
- Bluetooth / Wi-Fi presence connection (companion for the §7 monthly test cycle — fire the test alarm only when the operator is home, not when away):
  `connections/bluetooth-wifi-presence/`
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`
- OpenClaw JSON API (the contract `summary_keys` land here): `docs/reference/openclaw-json-api.md`
