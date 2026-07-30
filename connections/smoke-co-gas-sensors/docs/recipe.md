# Smoke / CO / gas safety sensors — tier-b recipe connection

This is the full howto for the `connections/smoke-co-gas-sensors/`
tier-b recipe connection. It walks through wiring smoke detectors
(Path A — smart detectors that already expose `binary_sensor.*` +
`sensor.*` entities in HA via their vendor integration, OR Path B —
basic Kidde / First Alert battery-only alarms with no HA integration
as the minimum safety baseline) + CO detectors (Path A or Path B) +
propane/LPG detectors (Path C — Mopeka / Atemox / GasAlert / MQ-
series via a Modbus bridge or ESPHome analog input) on the van,
mapping the device-side smoke / CO / gas detector outputs + analog
inputs into the `rc_safety_*` contract tiles, layering the six
MANDATORY safety automations (smoke detected → emergency-egress
unlock; CO detected → cut propane + open vents; gas leak detected →
cut propane + open vents; sensor offline > 30 min → push
notification; sensor battery low → push notification; alarm silenced
→ auto-resume after operator-set duration) + the §7 automations, and
promoting the connection to tier-a when the bench fixture lands.

## §1 What are smoke / CO / gas safety sensors in RoamCore?

Smoke / CO / gas safety sensors — van life safety monitoring for vans — are the **foundation** of every "is it safe to sleep in the van?" question. They are positioned in RoamCore as:

- A **vendor-neutral** binary_sensor + sensor contract. The contract talks to whatever smart detector integration the operator already runs (Path A — Nest Protect / First Alert Z-Wave / X-Sense Zigbee / Heiman Z-Wave / Zipato Zigbee), or to whatever basic Kidde / First Alert battery-only alarm the operator wires (Path B — minimum safety baseline; no HA integration), or to whatever propane/LPG detector the operator wires via a Modbus bridge or ESPHome analog input (Path C — Mopeka / Atemox / GasAlert / MQ-series).

- A **single "any alarm" tile** that aggregates smoke detected + CO detected + gas detected into one dashboard indicator. The `binary_sensor.rc_safety_any_alarm` tile is the day-1 affordance.

- A **mode-aware** system. The `select.rc_safety_alarm_mode` operator-tunable mode controls the alarm mode: `full` (every alarm triggers a siren), `night_only` (non-CO silenced during the day), `cooking_active` (30-min suppression), `off` (reserved for service work).

- A **safety-first** system. The `binary_sensor.rc_safety_sensor_offline` tile fires when any safety sensor hasn't checked in within 30 minutes — a dead battery or lost Wi-Fi means the operator has NO safety coverage and MUST address immediately.

- A **placement-aware** system. The operator MUST place detectors per local code: smoke detector in the bedroom (NOT the kitchen), CO detector within 10 ft of every sleeping area, propane/LPG detector near the propane system.

## §2 Prerequisites

Path A — Smart detectors (recommended):

- The operator's existing smart detectors (Nest Protect / First Alert Z-Wave / X-Sense Zigbee / Heiman Z-Wave / Zipato Zigbee) installed per local code.
- The vendor's HA integration configured (ZHA / Z-Wave JS / vendor first-party integration).
- The vendor integration's `binary_sensor.*` entity IDs + `sensor.*` entity IDs.

Path B — Generic smoke/CO alarms (basic, no smart features):

- The operator's basic Kidde / First Alert battery-only alarms installed per local code.
- These detectors do NOT have HA integration. Path B is the **minimum safety baseline**.

Path C — Propane/LPG detectors:

- The operator's propane/LPG detector (Mopeka / Atemox / GasAlert / MQ-2 / MQ-5 / MQ-7 / MQ-135) installed near the propane system.
- A Modbus bridge OR an ESPHome device with an ADC (ESP32 / ESP8266 ADC pin).

Safety prerequisites:

- The smart-automations `connections/smart-automations/` recipe's mode signal is wired.
- The upcoming deadbolts `connections/deadbolts/` recipe's `lock.deadbolt_emergency_unlock` switch exists.
- The bluetooth-wifi-presence `connections/bluetooth-wifi-presence/` recipe's `binary_sensor.rc_presence_operator_phone_home` tile exists.
- The operator's detectors are placed per local code.

## §3 Path A — Smart detectors (recommended: Nest Protect / First Alert Z-Wave / X-Sense Zigbee / Heiman Z-Wave)

The vendor integration's `binary_sensor.*` (smoke detected / CO detected / gas detected) + `sensor.*` (smoke_ppm / co_ppm / gas_ppm) entities are already exposed in HA. The recipe surfaces the entity IDs + wraps them into the `rc_safety_*` contract via templates.

```yaml
template:
  - binary_sensor:
      - name: "rc_safety_smoke_detected"
        state: >-
          {{ is_state('binary_sensor.nest_protect_bedroom_smoke', 'on')
             or is_state('binary_sensor.nest_protect_cab_smoke', 'on')
             or is_state('binary_sensor.first_alert_zwave_smoke', 'on') }}
        device_class: smoke

      - name: "rc_safety_co_detected"
        state: >-
          {{ is_state('binary_sensor.nest_protect_bedroom_co', 'on')
             or is_state('binary_sensor.nest_protect_cab_co', 'on')
             or is_state('binary_sensor.first_alert_zwave_co', 'on') }}
        device_class: carbon_monoxide

      - name: "rc_safety_gas_detected"
        state: >-
          {{ is_state('binary_sensor.zipato_gas_leak', 'on')
             or is_state('binary_sensor.esphome_propane_detected', 'on') }}
        device_class: gas

      - name: "rc_safety_any_alarm"
        state: >-
          {{ is_state('binary_sensor.rc_safety_smoke_detected', 'on')
             or is_state('binary_sensor.rc_safety_co_detected', 'on')
             or is_state('binary_sensor.rc_safety_gas_detected', 'on') }}
        device_class: safety

      - name: "rc_safety_alarm_silenced"
        state: "{{ is_state('input_boolean.rc_safety_alarm_silenced', 'on') }}"
        device_class: safety

      - name: "rc_safety_battery_low"
        state: >-
          {{ is_state('binary_sensor.nest_protect_bedroom_battery_low', 'on')
             or is_state('binary_sensor.nest_protect_cab_battery_low', 'on')
             or is_state('binary_sensor.first_alert_zwave_battery_low', 'on')
             or is_state('binary_sensor.zipato_gas_battery_low', 'on') }}
        device_class: battery

      - name: "rc_safety_sensor_offline"
        state: >-
          {{ (now() - state_attr('binary_sensor.nest_protect_bedroom_smoke', 'last_seen') | default(now(), true)).total_seconds() > 1800
             or (now() - state_attr('binary_sensor.nest_protect_cab_smoke', 'last_seen') | default(now(), true)).total_seconds() > 1800
             or (now() - state_attr('binary_sensor.first_alert_zwave_smoke', 'last_seen') | default(now(), true)).total_seconds() > 1800 }}
        device_class: safety

  - sensor:
      - name: "rc_safety_smoke_max_ppm"
        state: >-
          {{ [
            states('sensor.nest_protect_bedroom_smoke_ppm') | float(0),
            states('sensor.nest_protect_cab_smoke_ppm') | float(0),
            states('sensor.first_alert_zwave_smoke_ppm') | float(0)
          ] | max }}
        unit_of_measurement: "ppm"
        device_class: smoke
        state_class: measurement

      - name: "rc_safety_co_max_ppm"
        state: >-
          {{ [
            states('sensor.nest_protect_bedroom_co_ppm') | float(0),
            states('sensor.nest_protect_cab_co_ppm') | float(0),
            states('sensor.first_alert_zwave_co_ppm') | float(0)
          ] | max }}
        unit_of_measurement: "ppm"
        device_class: carbon_monoxide
        state_class: measurement

      - name: "rc_safety_gas_max_ppm"
        state: >-
          {{ [
            states('sensor.zipato_gas_ppm') | float(0),
            states('sensor.esphome_propane_ppm') | float(0)
          ] | max }}
        unit_of_measurement: "ppm"
        device_class: gas
        state_class: measurement
```

The mode select:

```yaml
select:
  - platform: template
    selects:
      rc_safety_alarm_mode:
        options:
          - "full"
          - "night_only"
          - "cooking_active"
          - "off"
        initial: "full"
```

The alarm test + silence buttons:

```yaml
button:
  - platform: template
    buttons:
      rc_safety_alarm_test:
        press:
          - service: homeassistant.test_alarm
      rc_safety_alarm_silence:
        press:
          - service: input_boolean.turn_on
            data:
              entity_id: input_boolean.rc_safety_alarm_silenced
          - service: timer.start
            data:
              entity_id: timer.rc_safety_alarm_silence

input_boolean:
  rc_safety_alarm_silenced:

timer:
  rc_safety_alarm_silence:
    duration: "00:10:00"
    restore: true
```

## §4 Path B — Generic smoke/CO alarms (basic, no smart features)

Basic Kidde / First Alert battery-only alarms do NOT have HA integration. Path B is the **minimum safety baseline** subsection that lists the recommended detectors.

### Minimum safety baseline — recommended detectors

| Detector | Smoke | CO | Gas | HA integration | Notes |
|----------|-------|-----|-----|----------------|-------|
| **Kidde KN-COSM-IBA** (combo smoke+CO) | ✅ | ✅ | ❌ | ❌ (basic) | The minimum safety combo alarm. Battery-only. |
| **Nest Protect** (2nd gen) | ✅ | ✅ | ❌ | ✅ (Nest integration) | The recommended smart detector. |
| **X-Sense SD11** (Zigbee) | ✅ | ❌ | ❌ | ✅ (ZHA) | Budget smart smoke detector. |
| **First Alert Z-Wave** (ZCOMBO) | ✅ | ✅ | ❌ | ✅ (Z-Wave JS) | Z-Wave combo smoke + CO detector. |

The operator installs a Kidde KN-COSM-IBA (combo smoke+CO) in the bedroom area (NOT the kitchen) + the cab per local code. The detector has a local audible alarm. The operator MUST upgrade to a smart detector (Path A) to get HA integration + the contract tiles.

## §5 Path C — Propane/LPG detectors (Mopeka / Atemox / GasAlert / MQ-series via ESPHome)

Propane/LPG detectors are typically 4-20 mA analog sensors that need a Modbus bridge OR an analog-to-Zigbee bridge (e.g. Shelly UNI analog input + a 4-20 mA receiver OR an ESPHome ADC reading the analog voltage directly).

```yaml
esphome:
  name: propane-sensor
  platform: ESP32
  board: esp32dev

sensor:
  - platform: adc
    pin: GPIO34
    name: "Propane ADC Voltage"
    attenuation: auto
    update_interval: 30s
    filters:
      - multiply: 3.3
    unit_of_measurement: "V"
    accuracy_decimals: 3

template:
  - sensor:
      - name: "esphome_propane_ppm"
        state: >-
          {{ (states('sensor.propane_adc_voltage') | float(0) * 1500) | int }}
        unit_of_measurement: "ppm"
        device_class: gas
        state_class: measurement

      - name: "esphome_propane_detected"
        state: "{{ states('sensor.esphome_propane_ppm') | float(0) > 5000 }}"
        device_class: gas
```

## §6 RoamCore contract entities

The 13 `rc_safety_*` tiles + how the upstream `binary_sensor.*` + `sensor.*` templates expose them + translation helpers needed for the binary_sensors / numeric ppm readings.

The full tile set (per `connection.yml` `dashboard.tiles`):

- `binary_sensor.rc_safety_smoke_detected` — TRUE when any smoke sensor triggers (OR-aggregate).
- `binary_sensor.rc_safety_co_detected` — TRUE when any CO sensor exceeds threshold.
- `binary_sensor.rc_safety_gas_detected` — TRUE when any propane / LPG / natural gas sensor triggers.
- `sensor.rc_safety_smoke_max_ppm` — highest current smoke reading across all smoke sensors (ppm).
- `sensor.rc_safety_co_max_ppm` — highest current CO reading (ppm).
- `sensor.rc_safety_gas_max_ppm` — highest current gas reading (ppm).
- `binary_sensor.rc_safety_any_alarm` — aggregate of `smoke_detected OR co_detected OR gas_detected`.
- `binary_sensor.rc_safety_alarm_silenced` — TRUE when operator has silenced the alarm.
- `binary_sensor.rc_safety_battery_low` — TRUE when any safety sensor reports battery low.
- `binary_sensor.rc_safety_sensor_offline` — TRUE when any safety sensor hasn't checked in within last 30 minutes.
- `select.rc_safety_alarm_mode` — `full` / `night_only` / `cooking_active` / `off`.
- `button.rc_safety_alarm_test` — test all sensors.
- `button.rc_safety_alarm_silence` — silence the alarm for operator-set duration.

The any-alarm aggregate template:

```yaml
template:
  - binary_sensor:
      - name: "rc_safety_any_alarm"
        state: >-
          {{ is_state('binary_sensor.rc_safety_smoke_detected', 'on')
             or is_state('binary_sensor.rc_safety_co_detected', 'on')
             or is_state('binary_sensor.rc_safety_gas_detected', 'on') }}
        device_class: safety
```

## §7 Automations (MANDATORY before first use — operator must wire each one)

Six automations to enable (the recipe ships the full YAML for each):

1. **Smoke detected → emergency-egress unlock + siren + lights + push notification** — when `binary_sensor.rc_safety_smoke_detected` flips TRUE, fire `switch.turn_on` on the upcoming deadbolts `connections/deadbolts/` recipe's `lock.deadbolt_emergency_unlock` switch (emergency-egress unlock), fire `homeassistant.turn_on` on all lights, fire `notify.notify` (push notification to operator's phone), and sound the alarm via the operator's chosen alarm service.

2. **CO detected → cut propane solenoid + open roof vents + turn off HVAC + push notification** — when `binary_sensor.rc_safety_co_detected` flips TRUE, fire `switch.turn_off` on the propane solenoid, fire `cover.open_cover` on the roof vents, fire `climate.turn_off` on the HVAC, and fire `notify.notify`.

3. **Gas leak detected → cut propane solenoid + open roof vents + turn off HVAC + push notification** — same as CO detected, but triggered by `binary_sensor.rc_safety_gas_detected`.

4. **Sensor offline (no check-in for >30 min) → push notification** — when `binary_sensor.rc_safety_sensor_offline` flips TRUE, fire `notify.notify` (push notification to operator's phone). The cross-reference is to the bluetooth-wifi-presence `connections/bluetooth-wifi-presence/` recipe's `binary_sensor.rc_presence_operator_phone_home` — when the operator is in the van AND the sensor is offline, the notification escalates.

5. **Sensor battery low → push notification** — when `binary_sensor.rc_safety_battery_low` flips TRUE, fire `notify.notify` (replace battery before it dies).

6. **Alarm silenced → auto-resume after operator-set duration** — when `timer.rc_safety_alarm_silence` finishes, fire `input_boolean.turn_off` on `input_boolean.rc_safety_alarm_silenced` (the `binary_sensor.rc_safety_alarm_silenced` tile flips FALSE; the alarm auto-resumes). The default 10-min silence is operator-tunable.

Cooking-active mode-aware suppression: when `select.rc_safety_alarm_mode == cooking_active`, non-CO alarms are silenced for 30 minutes. CO alarms are NEVER silenced.

## §8 Troubleshooting

Eight troubleshooting entries:

1. **Alarm false-positive during cooking** — the smoke detector is in the kitchen area, not the bedroom. Solution: move the smoke detector to the bedroom (NOT the kitchen). Secondary defense: use `cooking_active` mode-aware suppression. CO alarms are NEVER silenced by `cooking_active`.

2. **Sensor not discovered** — Zigbee / Z-Wave interview needed. Solution: trigger a manual interview via the ZHA / Z-Wave JS integration.

3. **ppm reading stuck at 0** — sensor calibration needed. Solution: for the MQ-series sensors in Path C, calibrate the sensor against a known gas concentration.

4. **Sensor offline after first install** — battery not seated correctly. Solution: open the sensor + reseat the battery.

5. **Alarm won't silence** — the test button is on a different entity. Solution: the `button.rc_safety_alarm_test` button tests all sensors; it does NOT silence the alarm. To silence the alarm, use the `button.rc_safety_alarm_silence` button.

6. **CO threshold set too sensitive** — false alarm during heavy cooking. Solution: the operator MUST NOT lower the threshold below the vendor's recommended setting.

7. **Mopeka propane sensor shows "leak" when tank is full** — calibrate the empty/full reference. Solution: recalibrate the sensor's empty/full reference via the Mopeka app.

8. **X-Sense integration missing in HA core** — install via HACS. Solution: the X-Sense Zigbee smoke detector integrates with HA via ZHA — no HACS needed.

9. **Shelly UNI analog input not reporting** — check 4-20 mA wiring polarity. Solution: the Shelly UNI analog input has a + and - terminal for the 4-20 mA loop. If the wiring is reversed, reverse the wiring.

## §9 Privacy

No telemetry. Everything is local. The smoke / CO / gas detectors are local Zigbee / Z-Wave / Wi-Fi / ESPHome, no cloud call home. The HA core `binary_sensor` + `sensor` domains do not phone home. The vendor integrations MAY phone home for firmware updates — that's the operator's vendor choice; RoamCore does not add any cloud integration.

The contract entities (`rc_safety_*`) do not collect any operator data; they are pure local-state tiles that surface the operator's choice + the upstream sensor readings.

## §10 Promoting to tier-a

What would need to happen to promote this connection from tier-b to tier-a:

- A real smoke + CO + propane sensor bench on CI.
- A canonical RoamCore-owned `config_flow.py` that walks the operator through choosing Path A vs Path B vs Path C + declaring the detector placement per local code + the analog input wiring for Path C.
- Integration tests that assert a smoke trigger on the upstream `binary_sensor.*` fires the right automation (emergency-egress unlock + siren + lights + push notification) + the dashboard `any_alarm` tile lights up.
- Integration tests that assert the six safety automations (smoke / CO / gas / offline / battery-low / alarm-silence auto-resume) all fire when wired to canned fixture responses.
- Flip `tier_requirements` to include `working_config_flow` + `integration_test_passes` + `no_manual_yaml_required` + `safety_automations_hard_enforced_in_roamcore_code`.

Until those ship, this connection is tier-b even though the upstream `binary_sensor` + `sensor` domains + the operator's choice of vendor integration have their own GUI flows. The recipe is sound but we cannot claim one-tap automation.
