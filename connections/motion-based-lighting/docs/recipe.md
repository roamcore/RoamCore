# Motion-based lighting — tier-b recipe connection

This is the full howto for the `connections/motion-based-lighting/`
tier-b recipe connection. It walks through wiring motion-driven +
ignition-driven + presence-driven + dark-outside-driven lighting on
the van (Path A — motion sensor via ZHA / Zigbee2MQTT / ESPHome /
Frigate / generic HA binary_sensor motion feed (PIR / mmWave radar /
Frigate `motion` event); Path B — ignition signal via OBD-II
(Wican Pro Wave 3 #6) / 12 V D+ signal via ESPHome analog input /
MQTT-published engine_running / manual `input_boolean.engine_running`
fallback; Path C — presence via the bluetooth-wifi-presence Wave 3
#42 connection's `binary_sensor.rc_presence_anyone_home` +
`binary_sensor.rc_presence_all_away`; Path D — mode-aware override
via `select.rc_lighting_motion_mode` (off / travel / camp / stealth /
custom) + optional cross-reference to the mode/automation-builder
Wave 2 #23 `select.rc_mode`), mapping the upstream entities into the
12 `rc_lighting_*` contract tiles, layering the four MANDATORY
safety interlocks (manual-override gate + dark-outside gate +
mode-aware Stealth suppression + travel-mode interior auto-off as a
safety feature) + the five §8 automations (travel-auto-off-interior-
lights + stop-and-soft-interior + arrival-cue-exterior-and-soft-
interior + motion-triggered-interior-camping + stealth-mode-
suppression), and promoting the connection to tier-a when the bench
fixture lands.

## §1 What is motion-based lighting in RoamCore?

Motion-based lighting (driving + arrival) — the umbrella for
ignition-driven interior auto-off + ignition-driven soft-interior
on stop + presence-driven arrival cue + motion-driven interior
camping + mode-aware Stealth suppression — is positioned in
RoamCore as:

- A **vendor-neutral** motion + ignition + presence + dark-outside
  contract. The contract talks to whatever motion sensor + ignition
  signal + presence setup + dark-outside sensor the operator wires
  (Path A motion sensor via ZHA / Zigbee2MQTT / ESPHome / Frigate /
  generic HA binary_sensor; Path B ignition signal via OBD-II / 12 V
  D+ signal / MQTT / input_boolean fallback; Path C presence via
  bluetooth-wifi-presence Wave 3 #42; Path D mode-aware override
  via `select.rc_lighting_motion_mode`), not to any specific
  vendor's library.

- A **single "any motion automation firing?" aggregate** that
  surfaces the path-level automation states into one dashboard
  tile. The `binary_sensor.rc_lighting_motion_active` tile is the
  day-1 aggregate (TRUE when any motion / ignition / presence
  automation is currently firing); together with
  `binary_sensor.rc_lighting_motion_available` (the meta-gate — TRUE
  when all required upstream gates are satisfied AND mode is NOT
  stealth), they give the operator a complete view of "is motion
  lighting ready to fire?" + "is motion lighting firing right now?"
  at a glance.

- A **four-pillar gate** for each automation. Each of the five §8
  automations specifies which pillars it requires:
    - Pillar 1: `binary_sensor.rc_lighting_motion_available` — TRUE
      when at least one motion sensor is wired AND the
      motion-mode is not `off` AND the dark-outside gate is open.
    - Pillar 2: `binary_sensor.rc_lighting_driving` — TRUE when
      `binary_sensor.engine_running` (or
      `binary_sensor.rc_obd_engine_running`) is TRUE.
    - Pillar 3: `binary_sensor.rc_lighting_presence_someone_home` /
      `binary_sensor.rc_lighting_presence_all_away` — the
      bluetooth-wifi-presence mirrors.
    - Pillar 4: `binary_sensor.rc_lighting_dark_outside` — TRUE
      when `sun.sun` is `below_horizon` OR
      `sensor.rc_weather_light_lux` < 50 lx.

  Each automation in §8 specifies which pillars it AND-gates on.
  The §8.1 Travel auto-off gates on Pillar 2 (driving) + manual-
  override gate. The §8.2 Stop-and-soft-interior gates on Pillar 2
  (driving transitioning FALSE) + Pillar 4 (dark outside). The §8.3
  Arrival cue gates on Pillar 3 (presence transition TRUE → FALSE)
  + Pillar 4 (dark outside). The §8.4 Motion-triggered interior
  gates on Pillar 1 (motion available) + Pillar 4 (dark outside).
  The §8.5 Stealth suppression gates on `select.rc_lighting_motion_
  mode == stealth`.

- A **mode-aware** system. The `select.rc_lighting_motion_mode`
  select controls the motion-mode:
    - `off` — motion lighting is fully disabled (operator is doing
      service work; the operator can still manually toggle lights
      via the dashboard tiles).
    - `travel` — interior auto-off is enforced (§8.1) + stop-and-
      soft-interior (§8.2) are active; motion-triggered interior
      (§8.4) is suppressed.
    - `camp` — motion-triggered interior (§8.4) + arrival cue (§8.3)
      are active; travel auto-off (§8.1) is suppressed.
    - `stealth` — ALL motion lighting is suppressed (§8.5). Legal
      campgrounds / National Parks / BLM land / state parks
      prohibit artificial light during quiet hours — the Stealth
      mode is the safety + legal setting for camped vans.
    - `custom` — the operator picks which pillars are active via
      `select.rc_lighting_custom_pillars` (all / motion_only /
      ignition_only / presence_only / motion_and_presence).

  The mode-aware lockouts layer on top: when `select.rc_mode`
  (from the mode/automation-builder Wave 2 #23 connection) is set
  to `stealth`, motion lighting is suppressed (the mode/
  automation-builder's higher-level Stealth overrides the motion-
  mode override). When `select.rc_mode` is `off`, motion lighting
  is fully disabled.

- A **manual-override-aware** system. The
  `binary_sensor.rc_lighting_manual_override_active` is TRUE for 5
  minutes after the operator manually toggles a light via
  `light.turn_on` or `light.turn_off`. During that 5-minute window,
  the §8.4 motion-triggered interior automation is suppressed
  (the "automations don't fight manual control" requirement from
  the legacy spec). The window is operator-tunable via
  `number.rc_lighting_manual_override_min` (default 5 minutes;
  range 1–30).

- A **safety-first** system. The §8.1 Travel auto-off is a SAFETY
  FEATURE: forgetting to wire it leaves interior lights on during
  driving, which is a legal issue in many jurisdictions (headlight
  laws + interior-distraction laws + driver-attention laws). The
  §8.5 Stealth suppression is a SAFETY + LEGAL FEATURE: motion
  lighting in stealth campgrounds is rude + illegal in many
  jurisdictions. The §8.3 Arrival cue includes a motion_pillar
  AND-gate (arrival cue only fires when a motion sensor ALSO fires
  within 30 seconds of the presence transition — the recipe
  explains why in §5.1: prevents wifi-range false positives from
  waking the operator when a neighbor's wifi just briefly drops).

- A **telemetry-aware** system. The
  `sensor.rc_lighting_last_motion_trigger_minutes_ago` +
  `sensor.rc_lighting_motion_trigger_count_24h` tiles surface the
  motion-automation telemetry (last trigger timestamp + 24-hour
  trigger count) for the dashboard badges. The telemetry is
  derived from the automation trace (`automation.motion_lighting_*
  .last_triggered` attribute) — no extra sensors required.

- A **multi-mode-aware** system. The dashboard tile
  `select.rc_lighting_motion_mode` exposes the operator's local
  override (off / travel / camp / stealth / custom) on top of the
  mode-aware defaults from `select.rc_mode` (the mode/automation-
  builder connection's mode select — away / stealth / sleep /
  boost / off). The recipe §6 walks through both.

## §2 Prerequisites

Path A — Motion sensor (PIR / mmWave / Frigate / generic HA
binary_sensor):

- At least one of the following motion sources configured:
    - PIR sensor (`binary_sensor.motion_*`) wired via ZHA / Zigbee2MQTT
      / ESPHome / generic HA `binary_sensor` (Aqara RTCZCGQ11LM /
      Sonoff SNZB-03 / Tuya TY-ZT08 / generic-Zigbee motion sensor).
    - mmWave radar sensor (HLK-LD2410 / Tuya mmWave) via ESPHome
      (the mmWave radar distinguishes motion from presence — useful
      for the "is anyone inside" path that triggers the arrival
      cue).
    - Frigate `motion` event (cross-references Frigate Wave 3 #35)
      wired via `event.frigate_motion_<camera>` if Frigate is
      enabled, OR via `binary_sensor.rc_cctv_motion_<camera>` if
      the Frigate-connection tiles are wired.
    - Generic HA `binary_sensor` motion feed (anything matching
      `binary_sensor.motion_*`) — the recipe walks the operator
      through picking which binary_sensors to aggregate into
      `binary_sensor.rc_lighting_motion_available`.
- The HA core `binary_sensor` domain (GUI flow since 2022.x) OR
  ZHA (GUI flow since 2022.x) OR Zigbee2MQTT (GUI flow since
  2022.x) OR ESPHome (GUI flow since 2023.x) OR Frigate (GUI flow
  since 2022.x) integration configured.

Path B — Ignition / engine-running signal:

- At least one of the following ignition sources configured:
    - OBD-II reader (Wican Pro Wave 3 #6) with
      `binary_sensor.rc_obd_engine_running` wired. The recipe
      walks the operator through binding `engine_running: true` →
      interior `light.turn_off` (the §8.1 Travel auto-off safety
      feature).
    - 12 V D+ signal via ADC + ESPHome (the recipe walks the
      operator through adding an ESPHome ADC sensor on GPIO (e.g.
      GPIO34 ADC1_CH6 on an ESP32) + a `binary_sensor.engine_
      running` template).
    - Upstream `mqtt` ignition topic (if the operator's van has an
      MQTT-published engine_running) — the recipe walks the
      operator through subscribing to the topic + creating the
      `binary_sensor.engine_running`.
    - Fallback `input_boolean.engine_running` that the operator
      toggles manually (for benches without ignition wiring) —
      RECITE the safety warning that forgetting to toggle off
      leaves interior lights on.
- The upstream `mqtt` (GUI flow since 2022.x) OR ESPHome (GUI
  flow since 2023.x) OR Wican Pro (Wave 3 #6) integration
  configured.

Path C — Presence detection (bluetooth-wifi-presence Wave 3 #42):

- The bluetooth-wifi-presence Wave 3 #42 connection's
  `binary_sensor.rc_presence_anyone_home` +
  `binary_sensor.rc_presence_all_away` wired. The bluetooth-wifi-
  presence connection is its own tier-b recipe that owns the
  presence scanner wiring (Path A `bluetooth_le_tracker` / Path B
  `nmap_device_tracker` / Path C `asuswrt` / `unifi` / `mikrotik`);
  motion-based-lighting depends on it for the §8.3 arrival-cue
  automation.

Path D — Mode-aware override:

- `select.rc_lighting_motion_mode` (off / travel / camp / stealth /
  custom) is the operator-tunable select for the motion-mode. The
  HA core `input_select` integration (GUI flow since 2022.x)
  provides the select widget.
- Optional but recommended: `select.rc_mode` from the mode/
  automation-builder Wave 2 #23 connection for the higher-level
  Stealth / Sleep / Boost / Off integration.

Cross-connection prerequisites:

- The approach-lights Wave 3 #52 connection's `light.approach_scene`
  group wired (for the §8.3 arrival-cue exterior lighting — the
  arrival cue fades in the approach scene + the soft interior,
  similar to approach-lights but only when motion-validated).
- The time/weather contract (Wave 2 #14 + Wave 2 #15 + Wave 3 #55
  atomic time) for `sensor.rc_weather_light_lux` OR the HA core
  `sun.sun` integration's below-horizon state (the
  `binary_sensor.rc_lighting_dark_outside` template gates on
  either source).

Safety prerequisites (cross-references to other connections):

- The bluetooth-wifi-presence Wave 3 #42 connection's
  `binary_sensor.rc_presence_anyone_home` +
  `binary_sensor.rc_presence_all_away` tiles exist (required for
  the §8.3 arrival-cue automation).
- The approach-lights Wave 3 #52 connection's
  `light.approach_scene` group exists (required for the §8.3
  arrival-cue exterior lighting).
- The mode/automation-builder Wave 2 #23 recipe's
  `select.rc_mode` tile exists (required for the §6 mode-aware
  override higher-level integration).
- The Frigate Wave 3 #35 recipe's `binary_sensor.rc_cctv_motion_<
  camera>` tiles exist (optional — for vans with Frigate CCTV
  installed and using Frigate as the motion source).
- The Wican Pro Wave 3 #6 OBD-II reader's
  `binary_sensor.rc_obd_engine_running` tile exists (optional —
  the canonical ignition source).

No upstream vendor integration required beyond the binary_sensor /
mqtt / sun / template / input_select / input_boolean integrations.
RoamCore ships zero motion-lighting hardware.

## §3 Path A — Motion sensor (PIR / mmWave / Frigate / generic)

Path A1 — Wired motion sensors (Aqara / Sonoff / Tuya PIR via
Zigbee2MQTT or ZHA):

```bash
# In HA: Settings → Devices & Services → Add Integration →
# Zigbee Home Automation (ZHA) OR Zigbee2MQTT (depending on
# which Zigbee hub the operator has). The GUI flow walks through
# device pairing.
#
# For ZHA: pair the motion sensor with the ZHA radio (the
# sensor advertises itself on the Zigbee network; ZHA
# auto-discovers + creates a `binary_sensor.motion_<sensor>`
# entity in the binary_sensor domain).
#
# For Zigbee2MQTT: the sensor publishes to the
# `zigbee2mqtt/<sensor>` MQTT topic; the Zigbee2MQTT integration
# creates a `binary_sensor.motion_<sensor>` entity.
```

Path A2 — mmWave radar sensors (HLK-LD2410 / Tuya mmWave):

```bash
# Wire the mmWave radar via ESPHome (the mmWave radar
# distinguishes motion from presence — useful for the "is
# anyone inside" path that triggers the arrival cue).
#
# ESPHome YAML (snippet):
#   uart:
#     rx_pin: GPIO16
#     tx_pin: GPIO17
#     baud_rate: 256000
#   ld2410:
#   binary_sensor:
#     - platform: ld2410
#       has_target:
#         name: "mmWave Presence"
#       has_moving_target:
#         name: "mmWave Motion"
#       still_distance:
#         name: "mmWave Still Distance"
#       moving_distance:
#         name: "mmWave Moving Distance"
```

Path A3 — Frigate `motion` event (cross-references Frigate Wave 3
#35):

```bash
# If Frigate is installed and configured, the Frigate integration
# creates `event.frigate_motion_<camera>` event entities + motion
# binary_sensor entities for each camera.
#
# Cross-reference the Frigate connection's `binary_sensor.rc_cctv_
# motion_<camera>` tiles (Wave 3 #35) — those are the contract
# layer mirrors of the raw Frigate motion events.
```

Path A4 — Generic HA `binary_sensor` motion feed:

```bash
# Anything matching `binary_sensor.motion_*` can be aggregated
# into `binary_sensor.rc_lighting_motion_available`. The recipe
# walks the operator through picking which binary_sensors to
# include in the aggregation.
```

The motion-available template:

```yaml
template:
  - binary_sensor:
      - name: "rc_lighting_motion_available"
        # Aggregate multiple motion sources into the
        # motion_available gate. The gate is TRUE when ANY of
        # the upstream motion sources is TRUE AND the motion-mode
        # is NOT `off` AND the motion-mode is NOT `stealth`.
        state: >-
          {{ is_state('select.rc_lighting_motion_mode', 'off')
             or is_state('select.rc_lighting_motion_mode', 'stealth')
             and false
             or (states('binary_sensor.motion_entry') == 'on'
                 or states('binary_sensor.motion_cabin') == 'on'
                 or states('binary_sensor.motion_porch') == 'on')
             and not is_state('select.rc_lighting_motion_mode', 'off')
             and not is_state('select.rc_lighting_motion_mode', 'stealth') }}
        device_class: motion
```

The motion-active template:

```yaml
template:
  - binary_sensor:
      - name: "rc_lighting_motion_active"
        # The aggregate "is ANY motion automation currently
        # firing?" tile. TRUE when any of the §8 automations is
        # currently running. The recipe walks the operator
        # through wiring the aggregate via the automation trace
        # (each automation sets a `input_boolean.motion_lighting_
        # <automation>_active` flag when it fires; the template
        # ORs them).
        state: >-
          {{ is_state('input_boolean.motion_lighting_travel_auto_off_active', 'on')
             or is_state('input_boolean.motion_lighting_stop_soft_interior_active', 'on')
             or is_state('input_boolean.motion_lighting_arrival_cue_active', 'on')
             or is_state('input_boolean.motion_lighting_motion_triggered_interior_active', 'on') }}
        device_class: light
```

The recommended motion sensors for vans:

| Sensor | Type | Wiring | Notes |
|--------|------|--------|-------|
| **Aqara RTCZCGQ11LM** | PIR + light + temp | ZHA / Zigbee2MQTT | Budget; widely available. |
| **Sonoff SNZB-03** | PIR | ZHA / Zigbee2MQTT | Budget; widely available. |
| **Tuya TY-ZT08** | PIR + Zigbee | ZHA / Zigbee2MQTT | Budget; widely available. |
| **HLK-LD2410** | mmWave radar | ESPHome UART | Distinguishes motion from presence. |
| **Tuya mmWave** | mmWave radar | ESPHome / Tuya cloud | Distinguishes motion from presence. |
| **Frigate `motion`** | Camera motion event | Frigate Wave 3 #35 | Camera-side motion; cross-references CCTV. |

## §4 Path B — Ignition signal (interior auto-off + soft-interior on stop)

Path B1 — OBD-II reader (Wican Pro Wave 3 #6):

```bash
# The Wican Pro Wave 3 #6 OBD-II reader is the canonical
# ignition source. The Wican Pro connection's
# `binary_sensor.rc_obd_engine_running` is wired via the
# upstream Wican Pro integration (GUI flow since 2023.x) OR
# via the upstream `obd` integration (GUI flow since 2023.x)
# OR via the upstream `mqtt` integration if the Wican Pro
# publishes via MQTT.
#
# The recipe walks the operator through binding
# `engine_running: true` -> interior `light.turn_off` (the §8.1
# Travel auto-off safety feature).
```

Path B2 — 12 V D+ signal via ADC + ESPHome:

```bash
# The 12 V D+ signal from the van's alternator (or ignition
# switch) is wired via a voltage divider (12 V -> 3.3 V for the
# ESP32 ADC) to an ESPHome analog input.
#
# ESPHome YAML (snippet):
#   sensor:
#     - platform: adc
#       pin: GPIO34
#       name: "Ignition D+ Voltage"
#       attenuation: auto
#       filters:
#         - throttle_average: 5s
#   binary_sensor:
#     - platform: template
#       sensors:
#         engine_running:
#           name: "Engine Running"
#           device_class: running
#           # 12 V D+ signal is HIGH when the engine is running
#           # (alternator charging); LOW when the engine is off.
#           value_template: >-
#             {{ states('sensor.ignition_d_plus_voltage') | float(0) > 6.0 }}
```

Path B3 — Upstream `mqtt` ignition topic:

```bash
# If the operator's van has an MQTT-published engine_running
# topic (e.g. via a separate ESP32 + relay + MQTT bridge), the
# upstream `mqtt` integration (GUI flow since 2022.x) subscribes
# to the topic and creates the `binary_sensor.engine_running`
# entity.
#
# Example MQTT subscription:
#   binary_sensor:
#     - platform: mqtt
#       name: "Engine Running"
#       state_topic: "van/engine/running"
#       payload_on: "true"
#       payload_off: "false"
#       device_class: running
```

Path B4 — Fallback `input_boolean.engine_running`:

```bash
# For benches without ignition wiring, the operator toggles
# `input_boolean.engine_running` manually. RECITE the safety
# warning that forgetting to toggle off leaves interior lights
# on (the §8.1 Travel auto-off is bypassed if
# `binary_sensor.engine_running` is stuck ON).
#
# The HA core `input_boolean` integration (GUI flow since
# 2022.x) provides the toggle widget.
```

The driving template:

```yaml
template:
  - binary_sensor:
      - name: "rc_lighting_driving"
        # TRUE when the vehicle is moving per ignition / speed.
        # The canonical source is the Wican Pro OBD-II
        # `binary_sensor.rc_obd_engine_running`. The recipe
        # accepts any upstream binary_sensor that surfaces
        # engine state (Path B1 OBD-II / Path B2 ESPHome D+ /
        # Path B3 MQTT / Path B4 input_boolean fallback).
        state: >-
          {{ is_state('binary_sensor.engine_running', 'on')
             or is_state('binary_sensor.rc_obd_engine_running', 'on') }}
        device_class: moving
```

The recommended ignition sources for vans:

| Source | Type | Wiring | Notes |
|--------|------|--------|-------|
| **Wican Pro OBD-II** | OBD-II CAN bus | Wican Pro Wave 3 #6 | Canonical; engine RPM + speed + D+. |
| **12 V D+ signal** | Alternator D+ | ESPHome ADC + voltage divider | Budget; analog only. |
| **MQTT engine_running** | MQTT topic | `mqtt` integration | Custom wiring; broker required. |
| **Input boolean** | Manual toggle | `input_boolean` integration | Bench fallback; operator-wired. |

## §5 Path C — Presence (arrival cue)

Path C1 — bluetooth-wifi-presence Wave 3 #42:

```yaml
# The bluetooth-wifi-presence Wave 3 #42 connection is its
# own tier-b recipe that owns the presence scanner wiring
# (Path A `bluetooth_le_tracker` / Path B `nmap_device_tracker`
# / Path C `asuswrt` / `unifi` / `mikrotik`). The
# motion-based-lighting connection depends on its contract
# tiles:
#   - binary_sensor.rc_presence_anyone_home
#     (TRUE when at least one occupant is home)
#   - binary_sensor.rc_presence_all_away
#     (TRUE when all occupants are away)
#   - device_tracker.rc_presence_person_<name>
#     (per-device tracker)
#
# The §8.3 arrival-cue automation uses the all_away -> not_
# all_away transition as the trigger (the "first person
# returns home" event).
```

Path C2 — GPS presence (device_tracker returning home):

```bash
# For vans with GPS-tracked devices (Traccar Wave 3 #36 or
# HA core `device_tracker` integration), the operator wires a
# `device_tracker` for each occupant; the recipe walks the
# operator through the `proximity:` home zone aggregation.
#
# The recipe recommends the bluetooth-wifi-presence connection
# as the primary presence source (Path C1) — it's lower-power
# + lower-latency than GPS + works indoors.
```

The presence mirrors:

```yaml
template:
  - binary_sensor:
      - name: "rc_lighting_presence_someone_home"
        # Mirror of bluetooth-wifi-presence
        # `binary_sensor.rc_presence_anyone_home`.
        state: "{{ is_state('binary_sensor.rc_presence_anyone_home', 'on') }}"
        device_class: presence

      - name: "rc_lighting_presence_all_away"
        # Mirror of bluetooth-wifi-presence
        # `binary_sensor.rc_presence_all_away`.
        state: "{{ is_state('binary_sensor.rc_presence_all_away', 'on') }}"
        device_class: presence
```

The motion_pillar AND-gate (the recipe explains why):

```yaml
# The §8.3 arrival-cue automation only fires when a motion
# sensor ALSO fires within 30 seconds of the presence
# transition. The motion_pillar AND-gate prevents wifi-range
# false positives from waking the operator when a neighbor's
# wifi just briefly drops (the operator IS home but the wifi
# presence temporarily reports all_away).
#
# The motion_pillar is checked via:
#   {{ is_state('binary_sensor.rc_lighting_motion_available', 'on') }}
# combined with the presence transition (TRUE -> FALSE on
# all_away) AND the dark_outside gate.
```

## §6 Path D — Mode-aware override (Travel / Camp / Stealth / Custom)

```yaml
select:
  - platform: template
    selects:
      rc_lighting_motion_mode:
        # The operator-tunable motion-mode. Determines which
        # §8 automations are active. The cross-reference to
        # the mode/automation-builder Wave 2 #23
        # `select.rc_mode` is OPTIONAL but recommended.
        options:
          - "off"
          - "travel"
          - "camp"
          - "stealth"
          - "custom"
        initial: "camp"

  - platform: template
    selects:
      rc_lighting_custom_pillars:
        # For Custom mode: which pillars are active.
        options:
          - "all"
          - "motion_only"
          - "ignition_only"
          - "presence_only"
          - "motion_and_presence"
        initial: "all"
```

The mode cross-reference to mode/automation-builder:

```yaml
# Optional: when `select.rc_mode` (from the mode/automation-
# builder Wave 2 #23 connection) is set to `stealth`, motion
# lighting is suppressed (the mode/automation-builder's higher-
# level Stealth overrides the motion-mode override). When
# `select.rc_mode` is `off`, motion lighting is fully disabled.
#
# The recipe recommends wiring the `select.rc_mode` -> motion-
# mode override via a HA core `automation:` that listens to
# `select.rc_mode` transitions and updates
# `select.rc_lighting_motion_mode` accordingly.
```

The manual-override gate:

```yaml
template:
  - binary_sensor:
      - name: "rc_lighting_manual_override_active"
        # TRUE for 5 minutes after the operator manually
        # toggles a light. The window is operator-tunable
        # via `number.rc_lighting_manual_override_min`
        # (default 5; range 1–30).
        state: >-
          {{ (now() - state_attr('automation.motion_lighting_
             manual_override_timer', 'last_triggered')) <
             timedelta(minutes=states('number.rc_lighting_
             manual_override_min') | int(5))
             if state_attr('automation.motion_lighting_
             manual_override_timer', 'last_triggered')
             else false }}
        device_class: occupancy
```

## §7 RoamCore contract entities

The 12 `rc_lighting_*` tiles + how the upstream Path A / B / C / D
templates expose them + translation helpers needed for derived
metrics (`last_motion_trigger_minutes_ago`, `motion_trigger_count_24h`,
`manual_override_active`).

The full tile set (per `connection.yml` `dashboard.tiles`):

- `binary_sensor.rc_lighting_motion_available` — the aggregate
  availability gate (TRUE when at least one motion sensor is wired
  AND the motion-mode is NOT `off` / `stealth` AND the dark-outside
  gate is open).
- `binary_sensor.rc_lighting_motion_active` — the aggregate "is
  ANY motion automation currently firing?" tile (TRUE when any of
  the §8 automations is currently running).
- `binary_sensor.rc_lighting_driving` — the driving state mirror
  (TRUE when `binary_sensor.engine_running` /
  `binary_sensor.rc_obd_engine_running` is TRUE).
- `binary_sensor.rc_lighting_dark_outside` — the dark-outside gate
  (TRUE when `sun.sun` is `below_horizon` OR
  `sensor.rc_weather_light_lux` < 50 lx).
- `binary_sensor.rc_lighting_presence_someone_home` — the
  bluetooth-wifi-presence mirror (TRUE when at least one occupant
  is home).
- `binary_sensor.rc_lighting_presence_all_away` — the
  bluetooth-wifi-presence mirror (TRUE when all occupants are
  away).
- `select.rc_lighting_motion_mode` — the operator-tunable motion-
  mode (off / travel / camp / stealth / custom).
- `number.rc_lighting_motion_duration_min` — the operator-tunable
  motion duration (default 2 minutes; range 0.5–30).
- `button.rc_lighting_run_motion_now` — the manual trigger button
  (fires the §8.4 motion-triggered interior automation manually).
- `sensor.rc_lighting_last_motion_trigger_minutes_ago` — the
  last-trigger telemetry sensor (minutes since the last motion
  automation fired).
- `sensor.rc_lighting_motion_trigger_count_24h` — the 24h-count
  telemetry sensor (count of motion automation fires in the last
  24 hours).
- `binary_sensor.rc_lighting_manual_override_active` — the manual-
  override gate (TRUE for 5 minutes after the operator manually
  toggles a light).

The dark-outside template:

```yaml
template:
  - binary_sensor:
      - name: "rc_lighting_dark_outside"
        # The dark-outside gate. TRUE when `sun.sun` is
        # below_horizon OR `sensor.rc_weather_light_lux` < 50 lx.
        # The recipe walks the operator through picking
        # between `sun.sun` (simpler) OR
        # `sensor.rc_weather_light_lux` (more accurate when
        # there's bright streetlight pollution).
        state: >-
          {{ is_state('sun.sun', 'below_horizon')
             or (states('sensor.rc_weather_light_lux') | float(9999)) < 50 }}
        device_class: light
```

The last-trigger + 24h-count sensors:

```yaml
template:
  - sensor:
      - name: "rc_lighting_last_motion_trigger_minutes_ago"
        # Minutes since the last motion automation fired.
        # Derived from the `automation.motion_lighting_*`
        # trace's `last_triggered` attribute.
        state: >-
          {{ (now() - state_attr('automation.motion_lighting_
             motion_triggered_interior', 'last_triggered')).total_
             seconds() / 60
             if state_attr('automation.motion_lighting_motion_
             triggered_interior', 'last_triggered')
             else 9999 }}
        unit_of_measurement: "min"

      - name: "rc_lighting_motion_trigger_count_24h"
        # Count of motion automation fires in the last 24 hours.
        # Derived from the `sensor.rc_lighting_motion_trigger_
        # count_24h` counter template that the §8 automations
        # increment on each fire.
        state: "{{ states('sensor.motion_lighting_trigger_count_24h') | int(0) }}"
        unit_of_measurement: "fires"
```

The button:

```yaml
button:
  - platform: template
    buttons:
      rc_lighting_run_motion_now:
        name: "Run motion lighting now"
        # Fires the §8.4 motion-triggered interior automation
        # manually. Useful for testing the wiring without
        # waiting for an ignition / motion / arrival trigger.
        press:
          - service: automation.trigger
            entity_id: automation.motion_lighting_motion_triggered_interior
```

## §8 Automations (MANDATORY before first use)

Five mode-aware automations to enable (the recipe ships the full
YAML for each):

1. **Travel auto-off interior lights** — when
   `binary_sensor.engine_running` (Path B ignition source)
   transitions FALSE → TRUE (engine started) AND
   `select.rc_lighting_motion_mode` IN (travel, custom_with_
   ignition) AND `binary_sensor.rc_lighting_manual_override_active`
   is FALSE → action = interior `light.turn_off` for every
   `light.*` in the `group.interior_lights` group. RECITE the
   safety warning that forgetting to wire this leaves interior
   lights on during driving (which is a legal issue in many
   jurisdictions — headlight laws + interior-distraction laws +
   driver-attention laws).

   ```yaml
   automation:
     - alias: "Motion lighting: Travel auto-off interior lights"
       id: motion_lighting_travel_auto_off
       mode: single
       trigger:
         - platform: state
           entity_id: binary_sensor.engine_running
           from: "off"
           to: "on"
         - platform: state
           entity_id: binary_sensor.rc_obd_engine_running
           from: "off"
           to: "on"
       condition:
         - condition: template
           value_template: >-
             {{ 'travel' in states('select.rc_lighting_motion_mode')
                or 'custom_with_ignition' in
                states('select.rc_lighting_motion_mode') }}
         - condition: state
           entity_id: binary_sensor.rc_lighting_manual_override_active
           state: "off"
       action:
         - service: light.turn_off
           target:
             entity_id: light.interior_lights
   ```

2. **Stop-and-soft-interior** — when
   `binary_sensor.engine_running` transitions TRUE → FALSE (engine
   stopped) AND `binary_sensor.rc_lighting_dark_outside` is TRUE
   AND `select.rc_lighting_motion_mode` IN (camp, travel,
   custom_with_ignition) → action = interior `light.turn_on` (low
   brightness, warm white, 30 sec fade) for every `light.*` in
   `group.soft_interior_lights`.

   ```yaml
   automation:
     - alias: "Motion lighting: Stop-and-soft-interior"
       id: motion_lighting_stop_soft_interior
       mode: single
       trigger:
         - platform: state
           entity_id: binary_sensor.engine_running
           from: "on"
           to: "off"
           for: "00:00:10"  # 10-sec debounce; prevents
                             # stoplight-flicker false fires.
         - platform: state
           entity_id: binary_sensor.rc_obd_engine_running
           from: "on"
           to: "off"
           for: "00:00:10"
       condition:
         - condition: state
           entity_id: binary_sensor.rc_lighting_dark_outside
           state: "on"
         - condition: template
           value_template: >-
             {{ 'camp' in states('select.rc_lighting_motion_mode')
                or 'travel' in states('select.rc_lighting_motion_mode')
                or 'custom_with_ignition' in
                states('select.rc_lighting_motion_mode') }}
       action:
         - service: light.turn_on
           target:
             entity_id: light.soft_interior_lights
           data:
             brightness: 64  # ~25%; low brightness for soft cue
             color_temp_kelvin: 2700  # warm white
             transition: 30  # 30-sec fade-in
   ```

3. **Arrival cue (exterior + soft interior)** — when
   `binary_sensor.rc_presence_all_away` transitions TRUE → FALSE
   (first person returns home) AND
   `binary_sensor.rc_lighting_dark_outside` is TRUE AND
   `select.rc_lighting_motion_mode` IN (camp, custom_with_
   presence) AND `binary_sensor.rc_lighting_motion_available`
   is TRUE within the last 30 seconds → action = exterior
   `light.turn_on` (the operator's choice of `light.approach_scene`
   from approach-lights Wave 3 #52) + soft-interior fade-in for
   5 sec, then auto-off after `number.rc_lighting_motion_duration_
   min` minutes.

   ```yaml
   automation:
     - alias: "Motion lighting: Arrival cue (exterior + soft interior)"
       id: motion_lighting_arrival_cue
       mode: single
       trigger:
         - platform: state
           entity_id: binary_sensor.rc_lighting_presence_all_away
           from: "on"
           to: "off"
           for: "00:00:30"  # 30-sec debounce; prevents wifi-
                             # range false positives.
       condition:
         - condition: state
           entity_id: binary_sensor.rc_lighting_dark_outside
           state: "on"
         - condition: template
           value_template: >-
             {{ 'camp' in states('select.rc_lighting_motion_mode')
                or 'custom_with_presence' in
                states('select.rc_lighting_motion_mode') }}
         - condition: template
           # motion_pillar AND-gate: the motion sensor must
           # have fired within the last 30 seconds of the
           # presence transition (prevents wifi-range false
           # positives from waking the operator).
           value_template: >-
             {{ (now() - state_attr('automation.motion_lighting_
                motion_triggered_interior', 'last_triggered'))
                < timedelta(seconds=30)
                if state_attr('automation.motion_lighting_motion_
                triggered_interior', 'last_triggered')
                else false }}
       action:
         - service: light.turn_on
           target:
             entity_id: light.approach_scene
           data:
             brightness: 128
             color_temp_kelvin: 2700
             transition: 5
         - service: light.turn_on
           target:
             entity_id: light.soft_interior_lights
           data:
             brightness: 64
             color_temp_kelvin: 2700
             transition: 5
         - delay: >-
             {{ states('number.rc_lighting_motion_duration_min')
                | int(2) * 60 }}
         - service: light.turn_off
           target:
             entity_id:
               - light.approach_scene
               - light.soft_interior_lights
   ```

4. **Motion-triggered interior (camping mode)** — when
   `binary_sensor.rc_lighting_motion_available` transitions FALSE
   → TRUE (any motion sensor fired) AND
   `binary_sensor.rc_lighting_dark_outside` is TRUE AND
   `select.rc_lighting_motion_mode` IN (camp, custom_with_motion)
   AND `binary_sensor.rc_lighting_manual_override_active` is FALSE
   → action = interior `light.turn_on` (low brightness, warm
   white) for `number.rc_lighting_motion_duration_min` minutes,
   then auto-off. The `manual_override_active` gate ensures
   manual toggles pause motion for 5 min.

   ```yaml
   automation:
     - alias: "Motion lighting: Motion-triggered interior (camping mode)"
       id: motion_lighting_motion_triggered_interior
       mode: restart
       trigger:
         - platform: state
           entity_id: binary_sensor.rc_lighting_motion_available
           from: "off"
           to: "on"
       condition:
         - condition: state
           entity_id: binary_sensor.rc_lighting_dark_outside
           state: "on"
         - condition: template
           value_template: >-
             {{ 'camp' in states('select.rc_lighting_motion_mode')
                or 'custom_with_motion' in
                states('select.rc_lighting_motion_mode') }}
         - condition: state
           entity_id: binary_sensor.rc_lighting_manual_override_active
           state: "off"
       action:
         - service: light.turn_on
           target:
             entity_id: light.interior_lights
           data:
             brightness: 96  # ~38%; low brightness for camping
             color_temp_kelvin: 2700
             transition: 2
         - delay: >-
             {{ states('number.rc_lighting_motion_duration_min')
                | int(2) * 60 }}
         - service: light.turn_off
           target:
             entity_id: light.interior_lights
           data:
             transition: 5
   ```

5. **Stealth mode suppression** — when
   `select.rc_lighting_motion_mode` becomes `stealth` (or
   `select.rc_mode` becomes `stealth` from the mode/automation-
   builder connection) → action = turn off ALL motion-triggered
   automations + cancel any active motion trigger. RECITE the
   LEGAL-CAMPGROUND NOTE that motion lighting in stealth
   campgrounds is rude + illegal in many jurisdictions (some
   National Parks + BLM land + state parks explicitly prohibit
   artificial light during quiet hours).

   ```yaml
   automation:
     - alias: "Motion lighting: Stealth mode suppression"
       id: motion_lighting_stealth_suppression
       mode: single
       trigger:
         - platform: state
           entity_id: select.rc_lighting_motion_mode
           to: "stealth"
         - platform: state
           entity_id: select.rc_mode
           to: "stealth"
       action:
         - service: automation.turn_off
           target:
             entity_id:
               - automation.motion_lighting_travel_auto_off
               - automation.motion_lighting_stop_soft_interior
               - automation.motion_lighting_arrival_cue
               - automation.motion_lighting_motion_triggered_interior
         - service: light.turn_off
           target:
             entity_id:
               - light.interior_lights
               - light.approach_scene
               - light.soft_interior_lights
   ```

## §9 Troubleshooting

Seven troubleshooting entries:

1. **Motion lighting never fires** — motion sensor not wired /
   dark sensor not wired / Stealth mode suppressing /
   `binary_sensor.rc_lighting_motion_available` is FALSE because
   of a missing upstream. Check the `binary_sensor.rc_lighting_
   motion_available` template's upstream sources in HA Developer
   Tools → States.

2. **Motion lighting stays on forever** —
   `number.rc_lighting_motion_duration_min` set too high / the
   §8.4 motion-triggered interior automation's auto-off action
   missing. Check the automation YAML in HA Settings →
   Automations & Scenes.

3. **Travel auto-off fires while parked at a stoplight** — the
   ignition-source debounce is too short. The §8.2 stop-and-soft-
   interior automation recommends a 10-sec debounce on the
   `engine_running` transition. If the operator's ignition source
   flickers (e.g. weak battery at the stoplight), increase the
   debounce to 15–30 sec.

4. **Arrival cue fires when the operator is just outside the wifi
   range** — `binary_sensor.rc_presence_all_away` is too
   sensitive. The §8.3 arrival-cue automation recommends a 30-sec
   debounce on the presence transition. If the operator's wifi
   presence flickers when they walk past the van with their phone
   in their pocket, increase the debounce to 60–120 sec.

5. **Stealth mode doesn't suppress** — mode/automation-builder
   recipe not wired / `select.rc_mode` tile missing / the
   `select.rc_lighting_motion_mode` is set to a non-stealth value.
   The recipe walks through both. Check the §8.5 stealth-mode-
   suppression automation's triggers in HA Settings →
   Automations & Scenes.

6. **Manual override is fighting with motion** — the operator
   manually toggled a light within the last 5 minutes, and the
   §8.4 motion-triggered interior automation is honoring that
   (the intended behavior). The recipe walks through shortening
   or extending the `manual_override_active` window via
   `number.rc_lighting_manual_override_min` (default 5).

7. **Motion lighting fires during the day** —
   `binary_sensor.rc_lighting_dark_outside` is FALSE but the
   automation doesn't gate on it. Walk through adding the dark-
   outside gate to the automation's `condition:` block.

## §10 Privacy

The lights produce no telemetry beyond local on/off state. The
motion sensors produce no telemetry beyond local motion-events
(binary_sensor). The presence source (bluetooth-wifi-presence
Wave 3 #42) has its own privacy controls. The ignition source
(OBD-II / D+ signal / MQTT / input_boolean) has its own privacy
controls.

No cloud call home. Path A motion sensors (Aqara / Sonoff / Tuya)
require their own hub (Zigbee2MQTT / ZHA / Tuya cloud) for the
operator's first-time setup; subsequent runs are local. Path B
ignition sources (OBD-II / ESPHome / MQTT) are local; no cloud
round-trip.

The mode-aware override (Stealth suppression) is local + private
— no cloud round-trip. The push notification for the manual-
override timer uses the operator's existing HA Core push
notification channel — that's the operator's choice; RoamCore
does not add any push notification channel.

No telemetry shared with RoamCore or any third party.

## §11 Promoting to tier-a

What would need to happen to promote this connection from tier-b
to tier-a:

- A real motion + ignition + presence + dark-outside bench on the
  CI rig: a PIR sensor (Aqara RTCZCGQ11LM via ZHA) + an OBD-II
  reader (Wican Pro Wave 3 #6) + a bluetooth-wifi-presence setup
  (Nmap device tracker on a Pi) + a `sun.sun` integration + a
  Frigate entry zone, all wired together in a controlled
  environment.
- A canonical RoamCore-owned operator-wired setup flow that walks
  the operator through choosing Path A / B / C / D + declaring
  the upstream entities (the motion binary_sensors for Path A;
  the engine_running binary_sensor for Path B; the presence
  binary_sensors for Path C; the motion-mode default for Path D)
  + mapping each upstream entity to the contract tile.
- Integration tests that assert:
    - a motion sensor event triggers
      `binary_sensor.rc_lighting_motion_available` (and the
      dependent §8.4 motion-triggered interior automation)
    - an ignition event (engine_running TRUE) triggers the §8.1
      Travel auto-off interior lights (when motion-mode is travel)
    - an ignition-off event (engine_running FALSE) triggers the
      §8.2 Stop-and-soft-interior (when dark_outside is TRUE)
    - a presence transition from all_away to someone_home
      triggers the §8.3 arrival cue (when dark_outside is TRUE
      AND a motion sensor fired within 30 sec)
    - a motion sensor event in Camp mode triggers the §8.4
      Motion-triggered interior (when dark_outside is TRUE)
    - a Stealth mode change suppresses all motion-triggered
      automations (§8.5)
    - a manual light toggle pauses motion automation for 5
      minutes (the `binary_sensor.rc_lighting_manual_override_
      active` gate).
- The RoamCore-owned `__init__.py` actually wires the 4 paths at
  HA startup (instead of being a tier-b recipe stub).

Until those ship, this connection is tier-b even though the
upstream binary_sensor / mqtt / sun / template / input_select /
input_boolean integrations have their own GUI flows. The recipe
is sound but we cannot claim one-tap automation.

## §12 Files in this connection + cross-references

Files in this connection:

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "motion_lighting"` marker for the
  audit.
- `docs/recipe.md` — the full howto (this file).
- `tests/test_connection_yml.py` — manifest honesty checks.

Cross-references:

- **Approach lights** (Wave 3 #52 — the lighting sibling): the
  §8.3 arrival-cue exterior lighting uses the approach-lights
  `light.approach_scene` group entity.
- **Bluetooth / Wi-Fi presence** (Wave 3 #42 — the Path C
  presence source): the §8.3 arrival-cue trigger depends on
  `binary_sensor.rc_presence_anyone_home` +
  `binary_sensor.rc_presence_all_away`.
- **Time / weather contract** (Wave 2 #14 + Wave 2 #15 + Wave 3
  #55): the dark-outside signal uses `sensor.rc_weather_light_
  lux` OR `sun.sun`.
- **Mode / automation-builder** (Wave 2 #23 — the higher-level
  mode): when `select.rc_mode` is `stealth`, motion lighting is
  suppressed (the mode/automation-builder's higher-level Stealth
  overrides the motion-mode override).
- **Frigate** (Wave 3 #35 — the optional motion source): the
  §3 Path A3 Frigate motion event cross-references Frigate for
  vans with Frigate CCTV installed.
- **Wican Pro** (Wave 3 #6 — the optional ignition source): the
  §4 Path B1 OBD-II reader cross-references Wican Pro for the
  canonical ignition source.
- **HVAC basics** (Wave 3 #49 — no relationship): different
  subsystem.
- **Electronic valves** (Wave 3 #51 — no relationship):
  different subsystem.
- **Water tanks** (Wave 3 #50 — no relationship): different
  subsystem.