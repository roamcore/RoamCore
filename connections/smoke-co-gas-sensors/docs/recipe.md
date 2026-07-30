# Smoke / CO / gas sensors — tier-b recipe connection

This is the full howto for the `connections/smoke-co-gas-sensors/`
tier-b recipe connection. It walks through wiring a smoke / CO / gas
safety sensor (Path A — Zigbee via ZHA, OR Path B — Z-Wave via
zwave_js, OR Path C — DIY MQ-series analog gas sensor via ESPHome +
a relay-driven siren on a GPIO) on the van, mapping the device-side
smoke / CO / gas signals + battery % + optional siren into the
`rc_safety_*` contract tiles, layering the four MANDATORY §6
lifesafety interlocks (sensor-not-offline detection / low-battery
pre-warning / any-alarm aggregate / mode-aware lockout when
`alarm_mode=disabled` suppresses notifications) + the seven §7
automations, and promoting the connection to tier-a when the bench
fixture lands.

## §1 What are smoke / CO / gas sensors in RoamCore?

Smoke / carbon-monoxide / propane-LPG / methane / natural-gas safety sensors — lifesafety detectors for vans — are the **lifesafety foundation** of every RoamCore install. They are positioned in RoamCore as:

- A **vendor-neutral** binary_sensor + sensor + button + select contract. The contract talks to whatever Zigbee smoke / CO / gas detector the operator already runs via ZHA (Path A), or to whatever Z-Wave smoke / CO detector the operator runs via zwave_js (Path B), or to whatever DIY MQ-series analog gas sensor + relay-driven siren the operator wires via ESPHome (Path C). The contract IDs are `rc_safety_*` — they don't care which path or vendor or analog sensor the operator picked.

- A **single "any alarm" subscription point**. The `binary_sensor.rc_safety_any_alarm_active` tile aggregates smoke + CO + gas into a single entity; downstream automations (loud siren + phone notification, smart-cooking-aware silencing, deadbolt auto-unlock + emergency egress) subscribe to that one contract entity rather than racing three separate `binary_sensor.smoke_*` / `binary_sensor.carbon_monoxide_*` / `binary_sensor.gas_*` upstream entities from different paths.

- A **cross-reference to the smart-automations connection** for "if alarm → notify all devices + unlock deadbolts + flash all lights for emergency egress". The smart-automations connection is a separate slice; this slice's recipe §7 documents the cross-reference so future automations can subscribe to `binary_sensor.rc_safety_any_alarm_active` (and specifically to `binary_sensor.rc_safety_co_detected` for the deadbolt-unlock branch — CO detectors should auto-unlock so an unconscious operator can be reached).

- A **mode-aware** system. RoamCore modes (Stealth / Sleep / Boost) + the operator-tunable `select.rc_safety_alarm_mode` (armed / night_only / silenced / disabled) drive the default policy: `armed` fires sirens + notifications on any alarm; `night_only` only fires sirens when RoamCore mode is Sleep (avoids waking the neighbour when cooking in Morning / Afternoon); `silenced` fires phone notifications but no siren (for known false-positive sources like a smoky stove); `disabled` tracks alarms but suppresses all sirens + notifications (for service windows only).

- A **sensor-offline-aware** system. A silent safety sensor is the most dangerous kind — if your smoke / CO / gas sensor battery dies overnight AND the sensor doesn't publish an `availability` topic, you might not know until it's too late. The `binary_sensor.rc_safety_sensor_offline` tile flips TRUE whenever any upstream sensor has not checked in within its expected heartbeat window (5–30 minutes for battery-powered Zigbee / Z-Wave sensors; ESPHome sensors publish `availability` via mqtt / native API). Cross-references the mqtt `connections/mqtt/` recipe's `availability` topic pattern.

- A **lifesafety-first** system. The four §6 MANDATORY interlocks (sensor-not-offline / low-battery / any-alarm aggregate / mode-aware lockout) are operator-wired, not RoamCore-enforced at tier-b; the recipe §7 walks through each interlock + each recommended automation with full YAML examples.

RoamCore does **not** ship a smoke / CO / gas safety sensor, a relay-driven siren, an ESPHome controller, or an analog gas sensor. The recipe is the install: the operator picks Path A / Path B / Path C, wires the hardware, follows the YAML, and ends up with the `rc_safety_*` contract tiles + the OpenClaw queries that bind to them.

## §2 Prerequisites

Path A — Zigbee via ZHA:

- A Zigbee coordinator (the operator's existing Zigbee stick — Sonoff Zigbee 3.0 USB Dongle Plus / Tube ZB / etc.).
- A Zigbee smoke detector (the Heiman / Develco / X-Sense / First Alert / Kidde / etc. Zigbee smoke detector the operator owns; the Zigbee IAS Zone cluster exposes the alarm state).
- A Zigbee CO detector (the operator's existing Zigbee CO detector; the Zigbee IAS Zone cluster exposes the CO state separately from the smoke state).
- An optional Zigbee gas detector (LPG / propane / methane / natural-gas; the Zigbee IAS Zone cluster exposes the gas state).
- The ZHA integration in HA core since 2020.x (GUI flow since 2022.x; the ZHA integration handles device signature overrides for vendors that don't ship clean signatures).
- The operator's Zigbee smoke / CO / gas detectors must be paired via the ZHA GUI flow (Settings → Devices & Services → ZHA → Add Device); the upstream `binary_sensor.smoke_*` / `binary_sensor.carbon_monoxide_*` / `binary_sensor.gas_*` entity IDs appear after pairing.

Path B — Z-Wave via zwave_js:

- A Z-Wave controller (the operator's existing Z-Wave 500 / 700 series stick — Aeotec Z-Stick 7 / Zooz ZST39 / etc.).
- A Z-Wave smoke detector (the First Alert / Kidde / etc. Z-Wave smoke detector the operator owns; the Z-Wave Notification CC exposes the alarm state).
- An optional Z-Wave CO detector (the operator's existing Z-Wave CO detector; the Notification CC differentiates test vs alarm vs low-battery states).
- The zwave_js integration in HA core since 2020.x (GUI flow since 2022.x; the zwave_js integration handles device interview + Notification CC).
- The operator's Z-Wave smoke / CO detector must be paired via the zwave_js GUI flow (Settings → Devices & Services → Z-Wave JS → Add Device); the upstream `binary_sensor.smoke_*` / `binary_sensor.carbon_monoxide_*` entity IDs appear after pairing.

Path C — DIY MQ-series analog gas sensor via ESPHome:

- An ESP32 (ESP32-WROOM-32 / ESP32-S3 / ESP32-C3 — any variant with at least one ADC1 channel + one GPIO output).
- An analog gas sensor (MQ-2 / MQ-3 / MQ-5 / MQ-7 / MQ-9 / MQ-135; different sensors detect different gases — MQ-2 detects LPG + propane + methane + smoke; MQ-7 detects CO; MQ-135 detects benzene + alcohol + smoke; MQ-9 detects LPG + CO + methane). The recipe uses MQ-9 (the broadest detector) in §5; operators using a different MQ-series sensor should adapt the calibration routine and the threshold values.
- A 10 kΩ potentiometer (for the analog sensor's voltage divider — the sensor's analog output needs to be scaled into the ESP32's 0–3.3 V ADC range).
- A relay-driven siren (a 5 V logic-level compatible relay + a 12 V siren / buzzer; the relay coil voltage must match the siren's control input; place the siren in the cabin at a level where it will wake a sleeping operator).
- A 12 V → 5 V buck converter (the ESP32 + the sensor + the relay typically run off the van's 12 V rail; the buck converter scales down for the ESP32's 3.3 V via its onboard regulator).
- A fuse per relay per the upstream relay's spec (typically a 2–5 A fuse for a 12 V siren).
- A flyback diode per relay coil (only if the relay is a mechanical relay; solid-state relays don't need a flyback diode).
- A ferrite choke + bulk capacitor on the 12 V rail (the van's engine alternator creates electrical noise that can crash the ESP32 / cause false sensor reads).
- The ESPHome integration in HA core since 2023.x (GUI flow since 2023.x; the ESPHome integration handles native API + the device-side YAML).
- The ESPHome YAML flashed to the ESP32 exposing the analog reading as `sensor.mq9_reading` + the threshold-derived `binary_sensor.lpg_alarm` template (recipe §5 walks through the YAML).
- HA core `binary_sensor:` + `mqtt:` + `template:` integrations (HA core since 2022.x; GUI flow since 2022.x; the `template` integration exposes the contract tile synthesis).
- The operator's operator phone configured for the phone-notification integration (Companion app for iOS / Android; the recipe §7 automation's `notify` action targets the operator's phone).

Safety prerequisites (operator MUST wire these before first use; the recipe §6 walks through each):

- A **battery + battery charger** wired to the operator's relay-driven siren (the siren must be powered even when the van is parked; a small 12 V SLA battery + a trickle charger is the typical install).
- A **manual test cycle** executed by the operator before relying on the system for sleep (the recipe §6 documents the MANDATORY monthly test cycle via `button.rc_safety_test_alarm`).
- An **operator phone configured** for the phone-notification integration (the recipe §7 "loud siren + phone notification" automation needs a notification target).
- A **smart-cooking awareness** wired via the smart-automations connection (when the hob is on + windows closed → auto-set mode to `silenced` for 30 min to avoid false-positive sirens; the slice ships as a separate connection).

## §3 Path A — Zigbee via ZHA

The ZHA integration in HA core since 2020.x exposes a GUI flow since 2022.x. The recipe walks through pairing a Zigbee smoke / CO / gas detector with ZHA, the auto-discovered `binary_sensor.smoke_*` / `binary_sensor.carbon_monoxide_*` / `binary_sensor.gas_*` entity IDs, the device-specific quirks (some Zigbee smoke detectors expose only an IAS Zone `binary_sensor` for the alarm state, others expose a `sensor` for the battery separately), and the recommended ZHA device signature overrides for vendors that don't ship clean signatures.

### §3.1 Pair the Zigbee detector with ZHA

Steps:

1. Install the ZHA integration if not already configured (Settings → Devices & Services → ZHA → Add Integration → follow the wizard to select the Zigbee coordinator).
2. Put the Zigbee smoke / CO / gas detector into pairing mode (typically hold the button on the detector until the LED flashes rapidly — see the operator's detector manual).
3. In ZHA, click "Add Device" — ZHA scans for nearby Zigbee devices; the detector appears within 10–30 seconds.
4. ZHA interviews the device and reports the entity IDs (e.g. `binary_sensor.heiman_smoke_detector_smoke` for an Heiman smoke detector).
5. Verify the entity IDs appear under Developer Tools → States → filter `binary_sensor.smoke_` (or `binary_sensor.carbon_monoxide_` for CO detectors / `binary_sensor.gas_` for gas detectors).

### §3.2 ZHA device signature overrides

Some vendor Zigbee detectors don't ship clean ZHA signatures (the Heiman / Develco / X-Sense / First Alert / Kidde / etc. ecosystem is notorious for this). When the auto-discovered entity IDs are wrong / mis-named / missing the battery sensor, you can override the ZHA device signature:

1. In HA core, enable the ZHA "quirks" override pattern (`zhaquirks` package).
2. Locate the vendor's ZHA quirk (e.g. `zhaquirks.heiman.smoke` for Heiman smoke detectors) and add it to `custom_zha_quirks/` if not already in the upstream `zhaquirks` library.
3. Restart HA core; ZHA re-interviews the device with the new quirk; the entity IDs come up cleanly.

### §3.3 The upstream entities (Path A)

After pairing with ZHA, the upstream entities look like:

- `binary_sensor.heiman_smoke_detector_smoke` — IAS Zone `binary_sensor` for the smoke alarm state (TRUE when smoke detected).
- `binary_sensor.heiman_smoke_detector_battery_low` — IAS Zone `binary_sensor` for the low-battery state.
- `sensor.heiman_smoke_detector_battery` — numeric battery percentage.
- (For CO detectors) `binary_sensor.heiman_carbon_monoxide_detector_carbon_monoxide` — IAS Zone `binary_sensor` for the CO state.
- (For gas detectors) `binary_sensor.heiman_gas_detector_gas` — IAS Zone `binary_sensor` for the gas state.

The exact entity IDs depend on the vendor; the recipe §6 walks through mapping each upstream `binary_sensor.*` + `sensor.*` to the `rc_safety_*` contract tiles via a `template:` binary_sensor + template sensor wrapper.

## §4 Path B — Z-Wave via zwave_js

The zwave_js integration in HA core since 2020.x exposes a GUI flow since 2022.x. The recipe walks through pairing a Z-Wave smoke / CO detector with zwave_js, the auto-discovered `binary_sensor.*` entity IDs, the Notification CC that some Z-Wave detectors use to differentiate test vs alarm vs low-battery states.

### §4.1 Pair the Z-Wave detector with zwave_js

Steps:

1. Install the zwave_js integration if not already configured (Settings → Devices & Services → Z-Wave JS → Add Integration → follow the wizard to select the Z-Wave controller path; the add-on is the standard install).
2. Put the Z-Wave smoke / CO detector into inclusion mode (typically press the button on the detector three times within 1.5 seconds; see the operator's detector manual).
3. In zwave_js, click "Add Device" — zwave_js scans for nearby Z-Wave devices; the detector appears within 30–60 seconds.
4. zwave_js interviews the device and reports the entity IDs (e.g. `binary_sensor.first_alert_smoke_detector_smoke_alarm` for a First Alert Z-Wave smoke detector).
5. Verify the entity IDs appear under Developer Tools → States → filter `binary_sensor.smoke_` (or `binary_sensor.carbon_monoxide_`).

### §4.2 Notification CC (test vs alarm vs low-battery)

Some Z-Wave detectors use the Notification CC (Command Class 0x71) to send three distinct notifications:

- `NOTIFICATION_EVENT_SMOKE_ALARM` — fire alarm.
- `NOTIFICATION_EVENT_SMOKE_TEST` — the operator pressed the test button on the detector.
- `NOTIFICATION_EVENT_BATTERY_LOW` — battery is low.

zwave_js exposes these as three separate `binary_sensor.*` entities (one per notification type); the recipe §6 walks through translating these into the `rc_safety_*` contract tiles (`binary_sensor.rc_safety_smoke_detected` aggregates all upstream smoke entities; `binary_sensor.rc_safety_alarm_in_test_mode` aggregates all upstream test entities).

### §4.3 Z-Wave controller home ID backup (recovery note)

If the van's main battery dies AND the Z-Wave controller loses power, the controller's "home ID" (the Z-Wave network identifier) is volatile — on reboot the controller may forget which devices belong to the network. To prevent this:

1. Back up the Z-Wave network after each device add (zwave_js GUI flow → "Backup Network").
2. Store the backup file in the RoamCore config (`config/zwavejs/`) so it survives HA core upgrades.
3. On reboot, zwave_js asks whether to restore from the backup — accept the prompt.

If you skip this, see §8 for the "zwave_js unpair after van power-cycle" troubleshooting entry.

## §5 Path C — DIY MQ-series gas sensor via ESPHome

The ESPHome integration in HA core since 2023.x exposes a GUI flow since 2023.x. The recipe walks through the full ESPHome YAML for an `mq9` (or `mq2` / `mq3` / `mq5` / `mq7` / `mq135`) `sensor:` exposed via the ESPHome integration, the calibration routine for the analog sensor (warm-up time + burn-in time + threshold tuning for the specific gas of interest), a `binary_sensor:` template that derives the alarm state from the analog reading crossing the threshold (e.g. `binary_sensor.lpg_alarm: lambda: 'return id(mq9_reading).state > 400.0;'`), and the audible siren (a buzzer on a GPIO pin).

### §5.1 ESPHome YAML — MQ-9 sensor + relay-driven siren

Here's the full ESPHome YAML for an MQ-9 sensor on GPIO 34 (ADC1_CH6; ESP32's ADC2 pins can interfere with Wi-Fi) + a relay-driven siren on GPIO 26 + an onboard blue LED for local fault indication:

```yaml
esphome:
  name: van-safety-sensors
  friendly_name: "Van safety sensors (MQ-9 + siren)"

esp32:
  board: esp32dev
  framework:
    type: arduino

logger:
api:
  encryption:
    key: !secret api_encryption_key
ota:
  - platform: esphome
    password: !secret ota_password

# Wi-Fi (replace with the operator's LAN credentials)
wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password
  ap:
    ssid: "Van safety sensors fallback"
    password: !secret fallback_password

captive_portal:

# MQTT for the §6 sensor-offline detection (cross-references
# connections/mqtt/ — the recipe §7 automation uses the
# `availability` topic for the rc_safety_sensor_offline tile).
mqtt:
  broker: !secret mqtt_broker
  username: !secret mqtt_username
  password: !secret mqtt_password
  topic_prefix: "van/safety_sensors"
  birth_message:
    topic: "van/safety_sensors/availability"
    payload: "online"
    retain: true
  will_message:
    topic: "van/safety_sensors/availability"
    payload: "offline"
    retain: true

# Analog gas sensor (MQ-9 detects LPG + CO + methane — broadest
# detector; operators using MQ-2 / MQ-3 / MQ-5 / MQ-7 / MQ-135
# should adapt the calibration routine + the threshold values).
sensor:
  - platform: adc
    pin: GPIO34   # ADC1_CH6 — safe for Wi-Fi co-existence
    attenuation: auto
    name: "MQ-9 analog reading"
    id: mq9_reading
    unit_of_measurement: "ppm"
    accuracy_decimals: 0
    update_interval: 5s

  - platform: template
    name: "MQ-9 LPG alarm threshold"
    id: mq9_lpg_threshold
    unit_of_measurement: "ppm"
    accuracy_decimals: 0
    update_interval: never
    lambda: 'return 400.0;'

# Threshold-derived binary sensor
binary_sensor:
  - platform: template
    name: "LPG alarm"
    device_class: gas
    id: lpg_alarm
    lambda: 'return id(mq9_reading).state > id(mq9_lpg_threshold).state;'

# Relay-driven siren on GPIO 26
output:
  - platform: gpio
    pin: GPIO26
    id: siren_output

switch:
  - platform: output
    name: "Cabin siren"
    id: cabin_siren
    output: siren_output
```

### §5.2 Calibration routine

MQ-series analog gas sensors require a burn-in period BEFORE reliable readings — out of the box, the sensor's analog reading drifts for 24–48 hours of continuous power. The recipe walks through the burn-in:

1. Power the sensor from a clean 5 V supply (NOT the van's 12 V rail directly).
2. Let the sensor warm up for 24–48 hours in clean air (no LPG / CO / methane present).
3. After warm-up, the analog reading settles to a baseline (typically 80–120 ppm in clean air for an MQ-9; other MQ sensors have different baselines — see the sensor datasheet).
4. Expose the sensor to a known concentration of the target gas (e.g. a controlled LPG leak from a lighter / a controlled CO source from a car exhaust in a ventilated space) — the analog reading rises to a known value.
5. Tune `mq9_lpg_threshold` (in the YAML above) so the threshold is between the baseline and the alarm level.

For vans with intermittent power (the battery goes flat when parked for weeks), the operator should either:

- Leave the sensor powered 24/7 (a small 12 V SLA battery + a trickle charger, like the relay-driven siren).
- OR accept that the first 24–48 hours after a power-up are unreliable and use a `binary_sensor` template that suppresses alarms during the burn-in window (a `time_based_filter` against `id(mq9_reading).state` only when `millis() > 48 * 3600 * 1000` after boot).

### §5.3 Path C upstream entities

After flashing the ESPHome YAML, the upstream entities look like:

- `sensor.van_safety_sensors_mq_9_analog_reading` — the analog reading (typical range 80–120 ppm in clean air; rises to 400+ ppm on LPG / propane / methane detection).
- `binary_sensor.van_safety_sensors_lpg_alarm` — the threshold-derived alarm state (device_class `gas`).
- `switch.van_safety_sensors_cabin_siren` — the relay-driven siren on/off affordance.
- The MQTT `availability` topic (`van/safety_sensors/availability` = `online` / `offline`) — the sensor publishes this for the `binary_sensor.rc_safety_sensor_offline` cross-reference.

The recipe §6 walks through mapping each upstream entity into the `rc_safety_*` contract tiles via HA core `template:` binary_sensor + template sensor + template button + template select wrappers.

### §5.4 Per-gas thresholds cheat sheet

Different MQ-series sensors detect different gases; here are the practical threshold settings (these are starting points — operators MUST verify in their specific environment):

| Sensor | Detects | Clean-air baseline | LPG alarm threshold | CO alarm threshold | Methane alarm threshold |
|---|---|---|---|---|---|
| MQ-2 | LPG + propane + methane + smoke | ~100 ppm | 400 ppm | n/a | 500 ppm |
| MQ-3 | Alcohol + ethanol + benzene | ~120 ppm | n/a | n/a | n/a |
| MQ-5 | LPG + natural gas + propane | ~100 ppm | 400 ppm | n/a | 500 ppm |
| MQ-7 | CO (carbon monoxide) | ~80 ppm | n/a | 200 ppm | n/a |
| MQ-9 | LPG + CO + methane | ~100 ppm | 400 ppm | 200 ppm | 500 ppm |
| MQ-135 | Benzene + alcohol + smoke + NH3 + CO2 | ~100 ppm | n/a | 200 ppm | n/a |

(These are starting thresholds only; verify in your specific environment. The recipe §5.2 calibration routine walks through the verification step.)

## §6 RoamCore contract entities

The 12 `rc_safety_*` contract tiles are synthesised from the upstream `binary_sensor.*` (Path A Zigbee IAS Zone OR Path B Z-Wave Notification CC OR Path C ESPHome threshold-derived template) + the upstream `sensor.*` (battery % per ZHA / zwave_js / ESPHome) + the upstream `switch.*` (Path C relay-driven siren) + the mqtt `availability` topic (Path C) via HA core `template:` binary_sensor + template sensor + template button + template select wrappers.

### §6.1 The 12 `rc_safety_*` contract tiles

The `dashboard.tiles` block of `connection.yml` lists the full set. Each tile is documented below:

- `binary_sensor.rc_safety_smoke_detected` — TRUE when any upstream smoke sensor (`binary_sensor.smoke_*` per Path A / `binary_sensor.smoke_alarm` per Path B / the threshold-derived alarm per Path C) reports smoke. Implementation: a `template:` binary_sensor OR'ing all upstream smoke entities.
- `binary_sensor.rc_safety_co_detected` — TRUE when any upstream CO sensor reports CO.
- `binary_sensor.rc_safety_gas_detected` — TRUE when any upstream gas sensor reports LPG / propane / methane / natural gas above threshold.
- `binary_sensor.rc_safety_any_alarm_active` — aggregate: smoke OR co OR gas. Implementation: a `template:` binary_sensor OR'ing the three above.
- `binary_sensor.rc_safety_siren_active` — TRUE when the local siren is currently sounding. Implementation: a `template:` binary_sensor mirrored from the `switch.rc_safety_siren`'s state (or directly from `switch.van_safety_sensors_cabin_siren` if the operator uses the upstream siren entity).
- `binary_sensor.rc_safety_alarm_in_test_mode` — TRUE when the alarms are in test mode. Implementation: a `template:` binary_sensor driven by a `input_boolean.rc_safety_test_mode_active` helper.
- `binary_sensor.rc_safety_low_battery_warning` — TRUE when any sensor battery < 20 %. Implementation: a `template:` binary_sensor aggregating `< 20` from each upstream `sensor.*_battery` entity.
- `binary_sensor.rc_safety_sensor_offline` — TRUE when any upstream sensor has not checked in within its expected heartbeat window. Implementation: a `template:` binary_sensor driven by a `time_based_filter` against the upstream `last_seen` (ZHA / zwave_js) or `availability` topic (mqtt for Path C).
- `sensor.rc_safety_lowest_battery_pct` — numeric battery % of the lowest-battery sensor. Implementation: a `template:` sensor with `min([...])` across all upstream battery entities.
- `button.rc_safety_silence_alarm` — explicit "silence the siren + acknowledge the alarm" affordance. Implementation: a `script:` that turns off the siren + sets `input_boolean.rc_safety_alarm_acknowledged` TRUE + emits an audit event.
- `button.rc_safety_test_alarm` — explicit "run the test cycle" affordance. Implementation: a `script:` that turns on the siren for 5 seconds + emits an audit event + sets `input_boolean.rc_safety_test_mode_active` for the duration.
- `select.rc_safety_alarm_mode` — operator-tunable: `armed` / `night_only` / `silenced` / `disabled`. Implementation: a `input_select` consumed by the §7 automations.

### §6.2 The four MANDATORY §6 lifesafety interlocks

These four interlocks are MANDATORY before first use (operator must wire each per the recipe §7 automations):

1. **Sensor-not-offline detection.** When any upstream sensor has not checked in within its expected heartbeat window, `binary_sensor.rc_safety_sensor_offline` flips TRUE and the operator is alerted (a silent safety sensor is the most dangerous kind). Implementation: a `template:` binary_sensor with a `time_based_filter` OR an mqtt `availability`-aware sensor for Path C. The recipe §7 automation sends a phone notification immediately when the tile flips TRUE; cross-references the mqtt `connections/mqtt/` recipe's `availability` topic pattern.

2. **Low-battery pre-warning.** When any sensor battery is below 20 %, `binary_sensor.rc_safety_low_battery_warning` flips TRUE; the Sunday-morning reminder automation warns the operator which sensor needs a battery swap. Implementation: a `template:` binary_sensor with `value_template: "{{ states('sensor.rc_safety_lowest_battery_pct') | float(100) < 20 }}"` (which sensors are low is detail exposed via `sensor.rc_safety_lowest_battery_pct` + a per-sensor helper list).

3. **Any-alarm aggregate.** `binary_sensor.rc_safety_any_alarm_active` aggregates smoke + CO + gas into a single tile so downstream automations (sirens + phone notifications + smart-cooking-aware silencing) can subscribe to one contract entity. Implementation: a `template:` binary_sensor OR'ing `rc_safety_smoke_detected` + `rc_safety_co_detected` + `rc_safety_gas_detected`.

4. **Mode-aware lockout.** When the operator selects `disabled` on `select.rc_safety_alarm_mode`, all sirens + notifications are suppressed; the operator MUST use this mode only for service windows. Implementation: a guard clause in each §7 automation that checks the mode select before acting. (When the mode is `silenced`, sirens are suppressed but phone notifications fire; when the mode is `night_only`, sirens + notifications fire only when RoamCore mode is Sleep; when the mode is `armed`, full sirens + notifications fire at all times.)

### §6.3 The contract-tile synthesis templates

The HA core `template:` YAML for synthesising the contract tiles is below (operator fills in the upstream entity IDs for their Path A / Path B / Path C choice):

```yaml
# rc_safety_smoke_detected
binary_sensor:
  - platform: template
    name: "Safety: smoke detected"
    device_class: smoke
    unique_id: rc_safety_smoke_detected
    value_template: >-
      {{ is_state('binary_sensor.smoke_alarm', 'on')
         or is_state('binary_sensor.first_alert_smoke_detector_smoke_alarm', 'on')
         or is_state('binary_sensor.van_safety_sensors_lpg_alarm', 'on') }}

  # ... similar for co_detected + gas_detected ...

  # rc_safety_any_alarm_active
  - platform: template
    name: "Safety: any alarm active"
    device_class: safety
    unique_id: rc_safety_any_alarm_active
    value_template: >-
      {{ is_state('binary_sensor.rc_safety_smoke_detected', 'on')
         or is_state('binary_sensor.rc_safety_co_detected', 'on')
         or is_state('binary_sensor.rc_safety_gas_detected', 'on') }}

  # ... similar for siren_active + alarm_in_test_mode + sensor_offline ...

  # rc_safety_low_battery_warning
  - platform: template
    name: "Safety: low battery warning"
    device_class: battery
    unique_id: rc_safety_low_battery_warning
    value_template: >-
      {{ states('sensor.rc_safety_lowest_battery_pct') | float(100) < 20 }}

sensor:
  # rc_safety_lowest_battery_pct
  - platform: template
    name: "Safety: lowest battery %"
    device_class: battery
    unit_of_measurement: "%"
    unique_id: rc_safety_lowest_battery_pct
    value_template: >-
      {{ [ states('binary_sensor.heiman_smoke_detector_battery_low') | default('off'),
            states('binary_sensor.first_alert_smoke_detector_battery_low') | default('off'),
            states('sensor.van_safety_sensors_mq_9_analog_reading') | default('off') ] | min }}

  # ... silence_alarm + test_alarm are button entities (see below) ...

select:
  # rc_safety_alarm_mode
  - platform: input_select
    name: "Safety: alarm mode"
    options:
      - armed
      - night_only
      - silenced
      - disabled
    initial: armed
```

(Operator adapts the `value_template:` for their exact upstream entity IDs; the cross-references to the upstream `binary_sensor.*` + `sensor.*` change per path choice.)

## §7 Automations

Seven automations, each documented below with copy-pasteable YAML. All automations are MANDATORY before first use (the operator wires each one per the §6 interlock description).

### §7.1 "Loud siren + phone notification" on any alarm

When `binary_sensor.rc_safety_any_alarm_active` flips TRUE, fire the siren AND send a phone notification:

```yaml
automation:
  - alias: "Safety: loud siren + phone notification on any alarm"
    trigger:
      - platform: state
        entity_id: binary_sensor.rc_safety_any_alarm_active
        to: "on"
    condition:
      - condition: template
        value_template: "{{ not is_state('select.rc_safety_alarm_mode', 'disabled') }}"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.rc_safety_siren    # mirror of the upstream switch.van_safety_sensors_cabin_siren
      - service: notify.notify
        data:
          title: "⚠️ VAN SAFETY ALARM"
          message: >-
            {{ trigger.from_state.attributes.friendly_name | default('Smoke/CO/gas sensor') }} is reporting an alarm.
            Type: {{ trigger.to_state.attributes.safety_type | default('unknown') }}.
            Silence: button.rc_safety_silence_alarm.
            Mode: select.rc_safety_alarm_mode.
```

The `condition` clause is the §6.4 mode-aware lockout — `disabled` suppresses both the siren AND the notification; `silenced` would be a variant that suppresses only the siren (operator configures the exact behaviour for `silenced` per their preference — typically fire the phone notification but skip the siren).

### §7.2 "Auto-unlock deadbolts + flash all lights" on CO detection for emergency egress

When `binary_sensor.rc_safety_co_detected` flips TRUE, auto-unlock the deadbolts (cross-reference to the upcoming `connections/deadbolts/` recipe) + flash all interior lights (cross-reference to the upcoming approach-lights / flash all interior lights recipe; this slice documents the cross-reference so future automations can subscribe to `binary_sensor.rc_safety_co_detected` for emergency egress; the recipe references "approach-lights" + "flash all interior lights" both as the cross-reference target) so an unconscious operator can be reached:

```yaml
automation:
  - alias: "Safety: auto-unlock deadbolts + flash all lights on CO"
    trigger:
      - platform: state
        entity_id: binary_sensor.rc_safety_co_detected
        to: "on"
    condition:
      - condition: template
        value_template: "{{ not is_state('select.rc_safety_alarm_mode', 'disabled') }}"
    action:
      - service: lock.unlock
        target:
          entity_id: lock.rc_deadbolt_main        # cross-refs upcoming connections/deadbolts/
      - service: light.turn_on
        target:
          entity_id: all
        data:
          flash: long
```

(The cross-reference to `lock.rc_deadbolt_main` is a future slice; the recipe documents the cross-reference so future automations can subscribe to the `rc_safety_co_detected` contract entity. The "flash all interior lights" branch references the future approach-lights recipe.)

### §7.3 "Low-battery pre-warning" on Sunday morning

When `binary_sensor.rc_safety_low_battery_warning` flips TRUE, send a reminder every Sunday at 09:00:

```yaml
automation:
  - alias: "Safety: low-battery pre-warning (Sunday reminder)"
    trigger:
      - platform: time
        at: "09:00:00"
    condition:
      - condition: state
        entity_id: binary_sensor.rc_safety_low_battery_warning
        state: "on"
    action:
      - service: notify.notify
        data:
          title: "🔋 VAN SAFETY: low battery"
          message: >-
            One or more safety sensors has battery < 20 %.
            Lowest: {{ states('sensor.rc_safety_lowest_battery_pct') }} %.
            Swap batteries this week.
```

### §7.4 "Sensor offline" detection (5–30 min heartbeat window)

When `binary_sensor.rc_safety_sensor_offline` flips TRUE, send an immediate phone notification (a silent safety sensor is the most dangerous kind):

```yaml
automation:
  - alias: "Safety: sensor offline detection"
    trigger:
      - platform: state
        entity_id: binary_sensor.rc_safety_sensor_offline
        to: "on"
    action:
      - service: notify.notify
        data:
          title: "🔇 VAN SAFETY: sensor offline"
          message: >-
            One or more safety sensors has not checked in within its heartbeat window.
            Check the sensor + the batteries + the mqtt broker for Path C.
```

The `sensor_offline` binary_sensor is synthesised from the upstream entities' `last_seen` attribute (ZHA / zwave_js) OR the mqtt `availability` topic for Path C; the recipe §6.2 documents the synthesis.

### §7.5 "Monthly test cycle" via `button.rc_safety_test_alarm`

The operator schedules a monthly test via a helper automation that fires at 10am the first Sunday of each month and produces a 5-second siren burst + an audit event:

```yaml
automation:
  - alias: "Safety: monthly test cycle (10am first Sunday)"
    trigger:
      - platform: time
        at: "10:00:00"
    condition:
      - condition: template
        value_template: "{{ now().weekday() == 6 and now().day <= 7 }}"
    action:
      - service: button.press
        target:
          entity_id: button.rc_safety_test_alarm
```

(Operator adds the audit-event emission inside the script bound to `button.rc_safety_test_alarm` per their audit integration choice; the recipe cross-references `connections/smart-automations/` for the audit-event pattern.)

### §7.6 "Night-only mode" via `select.rc_safety_alarm_mode`

When `select.rc_safety_alarm_mode` is `night_only`, sirens + notifications fire only when RoamCore mode is Sleep — this is enforced in the §7.1 automation's condition:

```yaml
automation:
  - alias: "Safety: night-only mode gate"
    trigger:
      - platform: state
        entity_id: binary_sensor.rc_safety_any_alarm_active
        to: "on"
    condition:
      - condition: template
        value_template: >-
          {{ is_state('select.rc_safety_alarm_mode', 'armed')
             or (is_state('select.rc_safety_alarm_mode', 'night_only')
                 and is_state('select.rc_mode', 'Sleep')) }}
    action:
      # ... the loud siren + phone notification (see §7.1) ...
```

The condition clause is the §6.4 mode-aware lockout + the night-only gate: when mode is `night_only` AND RoamCore mode is NOT Sleep, the automation does NOT fire (avoids waking the neighbour when cooking in Morning / Afternoon).

### §7.7 "Smart-cooking integration" via the smart-automations recipe

When the hob is on + windows closed → auto-set `select.rc_safety_alarm_mode` to `silenced` for 30 min to avoid false-positive sirens; cross-references the upcoming `connections/smart-automations/` recipe:

```yaml
automation:
  - alias: "Safety: smart-cooking integration (hob on + windows closed)"
    trigger:
      - platform: state
        entity_id: binary_sensor.rc_kitchen_hob_active    # cross-refs connections/smart-automations/
        to: "on"
    condition:
      - condition: state
        entity_id: binary_sensor.rc_window_main_closed   # cross-refs connections/windows/
        state: "on"
    action:
      - service: select.select_option
        target:
          entity_id: select.rc_safety_alarm_mode
        data:
          option: silenced
      - delay: "00:30:00"
      - service: select.select_option
        target:
          entity_id: select.rc_safety_alarm_mode
        data:
          option: armed
```

(The cross-references to `binary_sensor.rc_kitchen_hob_active` + `binary_sensor.rc_window_main_closed` are future slices; the recipe documents the cross-reference so future automations can subscribe to the contract entities.)

## §8 Troubleshooting

Eight troubleshooting entries:

- **ZHA pair failing (Zigbee channel conflict with the van Wi-Fi AP).** ZHA defaults to Zigbee channel 11; if the van's Wi-Fi AP is also using channel 11, the Zigbee radio experiences interference. Fix: change the ZHA channel to 15 (or 20 / 25) via ZHA GUI flow → Settings → Zigbee Network → Change Channel.
- **zwave_js unpair after van power-cycle (Z-Wave needs the controller home ID backup).** If the Z-Wave controller loses power, the controller's home ID is volatile; on reboot the controller may forget which devices belong to the network. Fix: back up the Z-Wave network after each device add (zwave_js GUI flow → "Backup Network"); on reboot, zwave_js asks whether to restore from the backup — accept the prompt.
- **ESPHome MQ sensor reading zero (wrong ADC pin; check `input: true`).** ESP32's ADC2 pins (GPIO 0, 2, 4, 12–15, 25–27) conflict with Wi-Fi; if the MQ sensor is wired to an ADC2 pin, the analog reading reads zero when Wi-Fi is active. Fix: rewire to an ADC1 pin (GPIO 32, 33, 34, 35, 36, 37, 38, 39). Verify with `id(mq9_reading).state > 0` in the ESPHome logs.
- **ESPHome MQ sensor reading saturated at 4095 (wrong voltage divider).** ESP32's ADC reads 0–4095 for 0–3.3 V; if the MQ sensor's analog output exceeds 3.3 V (because the voltage divider's resistor values are mis-sized), the ADC saturates at 4095. Fix: recalibrate the resistor ladder for the sensor's max reading — typically a 10 kΩ + 10 kΩ divider for an MQ-9 reading 0–1000 ppm; verify with `id(mq9_reading).state < 4095` in the ESPHome logs.
- **Siren not firing (relay polarity; swap the buzzer leads).** If the relay is wired backwards (the relay closes on LOW instead of HIGH, or vice versa), the siren never fires. Fix: swap the buzzer leads OR change the relay's `inverted: true` flag in the ESPHome YAML.
- **Sensor going offline when the van engine runs (alternator noise on the 12 V rail).** The van's alternator creates electrical noise that can crash the ESP32 / cause false sensor reads / drop the Wi-Fi connection. Fix: add a ferrite choke on the 12 V supply line near the ESP32 + a 1000 µF bulk capacitor across the ESP32's VIN/GND pins.
- **Low-battery warning stuck after battery swap (ZHA device signature cache; re-interview the device).** After replacing the battery in a Zigbee smoke detector, ZHA may not update the `sensor.*_battery` entity to the new battery's voltage. Fix: re-interview the device (ZHA GUI flow → Devices & Services → ZHA → the device → "Re-interview"); ZHA re-reads the device's battery and updates the entity.
- **False-positive smoke when cooking (open a window first, or use `select.rc_safety_alarm_mode = silenced`).** Smoke detectors near the kitchen can false-positive during normal cooking. Fix: open a window before cooking, OR set `select.rc_safety_alarm_mode` to `silenced` during known-cooking windows (the §7.7 smart-cooking integration automation does this automatically when the hob is on + windows closed).

## §9 Privacy

No telemetry. Everything is local: the upstream `binary_sensor.*` (Path A ZHA OR Path B zwave_js OR Path C ESPHome) → HA core `binary_sensor` + `mqtt` + `template` integrations → `rc_safety_*` contract tiles. The sirens + notifications go through HA core's local `switch` + `notify` integrations; no cloud traffic beyond the operator's notification target (Companion app for iOS / Android → Apple Push Notification Service / Firebase Cloud Messaging, which is the operator's existing phone-notification path). No vendor cloud (no Heiman cloud, no First Alert cloud, no Kidde cloud, no ESPHome cloud, no MQTT broker cloud); no third-party analytics; no RoamCore-side telemetry. The operator can audit the system by inspecting the upstream HA core Developer Tools + the `template:` binary_sensors / sensors in the HA core configuration.

## §10 Promoting to tier-a

To promote `connections/smoke-co-gas-sensors/` from tier-b to tier-a, the following is needed:

1. **A real smoke / CO / gas sensor + ESPHome + relay-driven siren bench on CI.** This means a physical (or simulator-emulated) ZHA-coordinator + Zigbee smoke / CO / gas detector OR a zwave_js-coordinator + Z-Wave smoke / CO detector OR an ESP32 + analog gas sensor + relay + siren — wired to a canned fixture source that simulates smoke / CO / gas events on demand.
2. **A canonical RoamCore-owned `config_flow.py`** that walks the operator through choosing Path A vs Path B vs Path C + declaring the sensor type (smoke / CO / gas) / siren pin / battery alert threshold. Lives in the `connections/smoke-co-gas-sensors/` folder as `config_flow.py` + `const.py` + `__init__.py` with a real `async_setup_entry` setup function.
3. **Integration tests** that assert:
   - The four §6 lifesafety interlocks (`rc_safety_sensor_offline`, `rc_safety_low_battery_warning`, `rc_safety_any_alarm_active`, the mode-aware `disabled` lockout) all flip to the expected state when wired to canned fixture responses.
   - A simulated smoke trigger (e.g. a ZHA IAS Zone alarm fired by the canned fixture) propagates to the right tile updates on `binary_sensor.rc_safety_smoke_detected` + `binary_sensor.rc_safety_any_alarm_active` within a defined latency budget (e.g. < 2 s from sensor-trigger to tile-flip).
   - A simulated Z-Wave Notification CC test trigger propagates to `binary_sensor.rc_safety_alarm_in_test_mode` within the same latency budget.
   - A simulated ESPHome analog-gas-reading crossing the threshold propagates to `binary_sensor.rc_safety_gas_detected` + `binary_sensor.rc_safety_any_alarm_active`.
   - A simulated mqtt `availability` topic flip to `offline` propagates to `binary_sensor.rc_safety_sensor_offline`.
4. **Flip `tier_requirements` to include `working_config_flow` + `integration_test_passes` + `no_manual_yaml_required` + `safety_interlocks_hard_enforced_in_roamcore_code`.**
5. **Update the manifest header** to remove the tier-b honesty paragraph + replace with tier-a's certification paragraph.
