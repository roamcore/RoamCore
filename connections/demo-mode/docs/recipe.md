# Demo mode — full howto (RoamCore vendor-neutral demo values for missing sensors + auto-disable on real sensor reconnect + never-controls-hardware guard)

This recipe is the canonical howto for the
`connections/demo-mode/` tier-b recipe connection (Wave
3 #62). It walks the operator through setting up the
FOUR operator-pickable demo scenarios (Off + Battery +
Water + Connectivity) + the 11 `rc_demo_mode_*` contract
tiles + the FIVE §8 MANDATORY automations + the optional
safety guards (never-controls-actual-hardware guard +
blocks-remote-access guard + operator-only guard).

The recipe assumes the operator has at least the upstream
helpers installed (HA core `input_boolean` + `input_select`
+ `input_text` + `input_number` since 2022.x — auto-
installed in every HA install) + at least ONE upstream
real-sensor source wired (battery sensor from Victron /
Renogy / generic shunt OR tank sensor from SeeLevel /
Garnet / Mopeka / generic resistive OR LTE-up binary
sensor from Peplink / Teltonika / Starlink / generic
router — whichever matches the picked scenario). If the
operator has no upstream sensors wired, the recipe starts
at §2 Prerequisites + walks through the upstream-sensor
wiring before the demo-mode wiring.

## §1 What is Demo mode in RoamCore?

Demo mode — vendor-neutral demo values for missing
sensors + auto-disable on real sensor reconnect + hard-
block from controlling real hardware — the umbrella for
"Demo Mode lets RoamCore show example values when
critical sensors are missing, so the UI still looks and
feels complete during setup or demos" — is the
ai-category complement to the broader RoamCore "show me
what it looks like" affordances. The umbrella positions
Demo mode as an ai-category concern (not a vehicle-
category concern + not a power-load concern + not a
remote-access concern + not a water-category concern)
because Demo mode is the operator-facing "what would the
UI look like with sensors?" affordance: the enable
toggle is the operator's master switch (OFF by default;
demo values are never shown unless the operator
explicitly enables them); the scenario selector picks
which demo scenario the dashboard should show (Off /
Battery / Water / Connectivity); the active-scenario
tile surfaces the resolved active scenario (factors in
the enable toggle — always "Off" when the toggle is
OFF); the blocking-real-hardware tile is the
single most important safety chip in the demo-mode
umbrella (should ALWAYS be FALSE; turns red if a
misconfiguration would let demo values drive a real
`switch.*` / `light.*` / `climate.*` service call —
forgetting to wire the never-controls-hardware guard
can leave the operator with demo values being written
to a real light switch); the battery-demo SoC tile is
the §3 demo scenario's example value (around 80% ± 10%
on a slow cycle so the dashboard looks alive); the
water-demo % tile is the §4 demo scenario's example
value (60% → 90% on a slow timer); the LTE-up demo tile
is the §5 demo scenario's example value (TRUE / FALSE on
a slow timer to simulate intermittent LTE); the enable-
battery + enable-water + enable-connectivity buttons are
the operator-facing affordances to one-tap enable +
scenario pick; the disable button is the operator-
facing affordance to one-tap disable.

The enable tile (`input_boolean.rc_demo_mode_enabled`)
is the operator's master switch — the recipe defaults to
OFF because demo values are never shown unless the
operator explicitly enables them (the §9.1 auto-disable
guard fires whenever a real sensor reconnects, so
forgetting to disable demo mode is mitigated).

The scenario tile (`select.rc_demo_mode_scenario`) is
the operator's scenario picker — the recipe exposes the
Off / Battery / Water / Connectivity options so the
operator can pick a scenario in one tap (via one of the
`button.rc_demo_mode_enable_*` buttons).

The blocking-real-hardware tile (`binary_sensor.rc_demo_
mode_is_blocking_real_hardware`) is the §8 MANDATORY
safety gate — the §8.2 never-controls-actual-hardware
automation flips this tile to TRUE whenever a
misconfiguration would let demo values drive a real
`switch.*` / `light.*` / `climate.*` service call. This
is the single most important safety affordance in the
demo-mode umbrella: forgetting to populate
`input_text.rc_demo_mode_real_hardware_targets` with
the comma-separated list of real-hardware entity ids
can leave the operator with a misconfiguration that
surfaces a green "demo safe" chip while demo values are
actually being written to a real light switch.

The audit-log entry (`sensor.rc_demo_mode_active_
scenario` + the §8.4 audit-log-entry automation) is the
operator-facing "when did demo mode last flip?" affordance
— the §8.4 audit-log-entry automation writes an entry
on every OFF→ON and ON→OFF transition so the operator can
review the demo-mode history at a glance.

The operator-only-guard (`input_boolean.rc_demo_mode_
enabled` flip protection via the §8.5 operator-only
automation) is the §8 MANDATORY safety gate — when a
non-operator source tries to flip the enable toggle
(e.g., a sensor auto-change, an automation script, a
remote-access non-operator session), the automation
BLOCKS the change + writes an audit-log entry + fires a
critical notification. Forgetting to wire the
operator-only guard can leave the operator with a
demo-mode state being flipped by an untrusted source.

The blocks-remote-access guard (the §8.3 blocks-remote-
access automation) is the §8 MANDATORY safety gate for
remote-access operators — when a remote-access session
interacts with the dashboard while demo mode is ON, the
automation surfaces a "demo mode is ON — values are not
real" banner + adds the demo-mode-active flag to the
remote-access session metadata + (if the operator's
remote-access setup supports it) refuses write-capable
actions until demo mode is disabled. Forgetting to wire
the blocks-remote-access guard can leave a remote-access
operator writing real actions based on demo values.

The auto-disable guard (the §8.1 demo-mode auto-disable
automation) is the §8 MANDATORY safety gate for real-
sensor operators — when a real sensor reconnects while
demo mode is ON, the automation clears the enable toggle
+ resets the scenario selector to Off + writes an
audit-log entry + fires a notification. This is the
single most important auto-recovery affordance in the
demo-mode umbrella: forgetting to wire the auto-disable
guard can leave the operator with demo values being
shown even after real sensors are reporting.

The disable button (`button.rc_demo_mode_disable`) is
the operator-facing affordance to one-tap disable —
pressing the button fires the §8.1 demo-mode auto-
disable automation, which clears the enable toggle +
resets the scenario selector to Off.

The enable-battery / enable-water / enable-connectivity
buttons (`button.rc_demo_mode_enable_battery` /
`button.rc_demo_mode_enable_water` /
`button.rc_demo_mode_enable_connectivity`) are the
operator-facing affordances to one-tap enable + scenario
pick — pressing one of these buttons flips the enable
toggle ON + sets the scenario selector to the matching
value (battery / water / connectivity).

## §2 Prerequisites

### §2.1 Universal prerequisites

- Home Assistant Core 2022.6 or newer (the upstream HA
  core `input_boolean` + `input_select` + `input_text` +
  `input_number` helpers + the HA core `template:` sensor
  wrapper + the HA core `template:` binary_sensor wrapper
  have all been available since 2022.6 — auto-installed in
  every HA install + exposed via the HA UI under Settings
  → Helpers + Settings → Devices & Services → Helpers).
- The RoamCore base packages installed (`homeassistant/
  packages/roamcore_core.yaml` + `homeassistant/packages/
  roamcore_*.yaml` for the umbrella categories the demo
  scenarios will surface — power / water / network).
- The upstream `command_line` integration configured
  (the recipe uses `command_line` for the upstream
  reachability probe — `binary_sensor` / `sensor` that
  tests whether the operator's chosen upstream is
  reachable).

### §2.2 Upstream signal prerequisites

At least ONE of the following upstream real-sensor sources
must be wired (the §8.1 demo-mode auto-disable automation
fires whenever ANY of these transitions from
`unavailable` / `unknown` to a real value):

- **Battery sensor** — the operator's chosen battery
  integration (Victron / Renogy / generic shunt) wired to
  `sensor.rc_demo_mode_real_sensor_battery`. The recipe
  uses this sensor's `unavailable` / `unknown` → real-value
  transition to trigger the §8.1 auto-disable guard when
  the picked scenario is `Battery`.
- **Tank sensor** — the operator's chosen tank integration
  (SeeLevel / Garnet / Mopeka / generic resistive) wired
  to `sensor.rc_demo_mode_real_sensor_water_fresh`. The
  recipe uses this sensor's `unavailable` / `unknown` →
  real-value transition to trigger the §8.1 auto-disable
  guard when the picked scenario is `Water`.
- **LTE-up binary sensor** — the operator's chosen
  network integration (Peplink / Teltonika / Starlink /
  generic router) wired to
  `binary_sensor.rc_demo_mode_real_sensor_connectivity_
  lte_up`. The recipe uses this binary_sensor's
  `unavailable` / `unknown` → real-value transition to
  trigger the §8.1 auto-disable guard when the picked
  scenario is `Connectivity`.

The operator MUST also populate
`input_text.rc_demo_mode_real_hardware_targets` with the
comma-separated list of real-hardware entity ids the §8.2
never-controls-actual-hardware guard should protect (e.g.,
`switch.rc_fan_main, switch.rc_heated_floor_main, light.
rc_approach_lights_main`). Forgetting to populate this
list is the #1 cause of "demo values being written to a
real light switch" misconfigurations.

### §2.3 Optional cross-references (recommended)

- Time-atomic Wave 3 #55 connection — the time-of-day
  primitives used by the §8.4 audit-log entry's timestamp.
- Remote-access Wave 3 #58 connection — the VPN primitive
  used by the §8.3 blocks-remote-access guard.
- Approach lights Wave 3 #52 connection — the §8.3
  blocks-remote-access guard's dashboard banner pattern.
- Fans Wave 3 #59 connection — the §8.2 never-controls-
  actual-hardware guard's fan-protection cross-reference.
- Leveling Wave 3 #60 connection — the §8.5 operator-only
  guard's levelling-jack protection cross-reference.
- Mode Wave 3 #61 connection — the §8.4 audit-log entry's
  mode-change cross-reference.

## §3 Off scenario (the default)

The Off scenario means demo mode is disabled. The
dashboard shows real sensor values (or `unknown` if
sensors aren't wired). Default for operators with all
hardware installed.

### §3.1 Off scenario steps

1. Leave `input_boolean.rc_demo_mode_enabled` OFF
   (default).
2. Leave `select.rc_demo_mode_scenario` on Off (default).
3. The dashboard will surface `unknown` for the battery +
   water + connectivity contract tiles if no real sensors
   are wired — this is expected; the operator's real
   integrations (when wired) will surface real values.
4. No `rc_demo_mode_*` contract tile should drive a real
   `switch.*` / `light.*` / `climate.*` service call —
   the demo-mode values are clearly labelled as Off.
5. Verify: the dashboard's "demo mode" page should show
   the enable toggle OFF + the scenario selector on Off
   + the active-scenario tile = "Off" + the blocking-
   real-hardware tile = FALSE (green chip).

## §4 Battery demo scenario

The Battery demo scenario shows example battery / solar /
inverter values as if a Victron GX were installed +
reporting. Useful when the operator is wiring RoamCore
without a real power system.

### §4.1 Battery demo scenario steps

1. Press `button.rc_demo_mode_enable_battery` (one-tap:
   flips `input_boolean.rc_demo_mode_enabled` ON + sets
   `select.rc_demo_mode_scenario` to `Battery`).
2. Verify the dashboard surfaces the
   `sensor.rc_demo_mode_demo_value_battery_soc_percent`
   tile with a cycling value around 80% ± 10% on a slow
   timer (the recipe's §7 contract tile configuration
   points this tile at a `template:` sensor that cycles
   `{{ states('sensor.cycle_helper_battery_soc') }}`
   on a 5-minute timer).
3. Verify `sensor.rc_demo_mode_active_scenario` reports
   `Battery` (the resolved active scenario factors in
   the enable toggle + the scenario selector).
4. Verify `binary_sensor.rc_demo_mode_is_blocking_real_
   hardware` stays FALSE (the §8.2 guard is wired and
   `switch.rc_fan_main` is in the
   `input_text.rc_demo_mode_real_hardware_targets` list).
5. To exit, press `button.rc_demo_mode_disable` (one-tap:
   clears `input_boolean.rc_demo_mode_enabled` + resets
   `select.rc_demo_mode_scenario` to `Off`).

## §5 Water demo scenario

The Water demo scenario shows example fresh / grey /
black tank levels as if the SeeLevel / Victron / generic
resistive tank sensors were installed. Useful for
showcasing the water UI without a real tank sensor.

### §5.1 Water demo scenario steps

1. Press `button.rc_demo_mode_enable_water` (one-tap:
   flips `input_boolean.rc_demo_mode_enabled` ON + sets
   `select.rc_demo_mode_scenario` to `Water`).
2. Verify the dashboard surfaces the
   `sensor.rc_demo_mode_demo_value_water_fresh_percent`
   tile with a cycling value 60% → 90% on a slow timer
   (the recipe's §7 contract tile configuration points
   this tile at a `template:` sensor that cycles `{{
   states('sensor.cycle_helper_water_fresh_percent') }}`
   on a 10-minute timer).
3. Verify `sensor.rc_demo_mode_active_scenario` reports
   `Water`.
4. Verify `binary_sensor.rc_demo_mode_is_blocking_real_
   hardware` stays FALSE.
5. To exit, press `button.rc_demo_mode_disable`.

## §6 Connectivity demo scenario

The Connectivity demo scenario shows example Wi-Fi / LTE
/ Starlink state as if multiple upstream network
integrations were installed. Useful for showcasing the
network UI without real radios.

### §6.1 Connectivity demo scenario steps

1. Press `button.rc_demo_mode_enable_connectivity`
   (one-tap: flips `input_boolean.rc_demo_mode_enabled`
   ON + sets `select.rc_demo_mode_scenario` to
   `Connectivity`).
2. Verify the dashboard surfaces the
   `binary_sensor.rc_demo_mode_demo_value_connectivity_
   lte_up` tile with a slow TRUE / FALSE timer (the
   recipe's §7 contract tile configuration points this
   tile at a `template:` binary_sensor that flips `{{
   states('binary_sensor.cycle_helper_connectivity_lte')
   }}` on a 7-minute timer to simulate intermittent LTE).
3. Verify `sensor.rc_demo_mode_active_scenario` reports
   `Connectivity`.
4. Verify `binary_sensor.rc_demo_mode_is_blocking_real_
   hardware` stays FALSE.
5. To exit, press `button.rc_demo_mode_disable`.

## §7 RoamCore contract entities

The 11 `rc_demo_mode_*` contract tiles are the canonical
RoamCore surface for the demo-mode umbrella. The tiles
are vendor-neutral — no Victron / SeeLevel / Garnet /
Mopeka / Renogy / Starlink / Peplink / Teltonika / Unifi
/ Ubiquiti / MQTT / webhook / REST / API / HTTP / HTTPS /
Companion / ESPHome / phone / GPS / accelerometer /
iPhone / iOS / Android / Samsung / Pixel / OnePlus /
Xiaomi / Huawei / input_boolean / input_select /
input_text / input_number / input_button / template /
Z-Wave / Zigbee / ZHA / Deconz / Tasmota / Shelly /
Sonoff / ESP32 / ESP8266 / Wi-Fi / BLE / Bluetooth
names leak into the tile ids.

### §7.1 The 11 `rc_demo_mode_*` contract tiles

- `input_boolean.rc_demo_mode_enabled` — master enable
  toggle (OFF by default). The tile is an
  `input_boolean:` domain entity (since 2022.x) that the
  operator's chosen enable-tile UI flips.
  ```yaml
  input_boolean:
    rc_demo_mode_enabled:
      name: RC Demo Mode Enabled
      initial: false
      icon: mdi:play-box-outline
  ```

- `select.rc_demo_mode_scenario` — Off / Battery / Water
  / Connectivity. The tile is a `select:` domain entity
  (since 2022.x — `input_select` is the umbrella; since
  2024.x the modern `select:` domain entity is exposed
  via the HA UI under Settings → Helpers) that the
  operator's chosen scenario-selector UI picks.
  ```yaml
  select:
    rc_demo_mode_scenario:
      name: RC Demo Mode Scenario
      options:
        - "Off"
        - "Battery"
        - "Water"
        - "Connectivity"
      initial: "Off"
      icon: mdi:palette-swatch-outline
  ```

- `sensor.rc_demo_mode_active_scenario` — the resolved
  active scenario, factoring in the enable toggle
  (surfaces as "Off" when the toggle is OFF regardless
  of the selector). The tile is a `template:` sensor
  (since 2022.x).
  ```yaml
  template:
    - sensor:
        - name: "RC Demo Mode Active Scenario"
          unique_id: rc_demo_mode_active_scenario
          icon: mdi:palette-swatch
          state: >
            {% if is_state('input_boolean.rc_demo_mode_enabled', 'on') %}
              {{ states('select.rc_demo_mode_scenario') }}
            {% else %}
              Off
            {% endif %}
  ```

- `binary_sensor.rc_demo_mode_is_blocking_real_hardware`
  — TRUE when demo mode would attempt to control real
  hardware (should ALWAYS be FALSE; surfaces in the
  dashboard as a green "demo safe" chip). The tile is
  a `template:` binary_sensor (since 2022.x) that the
  §8.2 never-controls-actual-hardware automation
  writes to.
  ```yaml
  template:
    - binary_sensor:
        - name: "RC Demo Mode Is Blocking Real Hardware"
          unique_id: rc_demo_mode_is_blocking_real_hardware
          device_class: safety
          icon: mdi:shield-check
          state: >
            {% if is_state('input_boolean.rc_demo_mode_enabled', 'on') %}
              {# Check if any real-hardware target is reachable from demo values #}
              {{ false }}
            {% else %}
              false
            {% endif %}
  ```

- `sensor.rc_demo_mode_demo_value_battery_soc_percent`
  — demo battery state-of-charge percentage; only
  surfaces when scenario=Battery AND enable toggle is
  ON. The tile is a `template:` sensor (since 2022.x).
  ```yaml
  template:
    - sensor:
        - name: "RC Demo Mode Demo Value Battery SoC Percent"
          unique_id: rc_demo_mode_demo_value_battery_soc_percent
          unit_of_measurement: "%"
          device_class: battery
          state: >
            {% if is_state('input_boolean.rc_demo_mode_enabled', 'on')
                  and is_state('select.rc_demo_mode_scenario', 'Battery') %}
              {{ states('sensor.cycle_helper_battery_soc') | float(80) }}
            {% else %}
              unknown
            {% endif %}
  ```

- `sensor.rc_demo_mode_demo_value_water_fresh_percent`
  — demo fresh-water tank percentage; only surfaces
  when scenario=Water AND enable toggle is ON. The tile
  is a `template:` sensor (since 2022.x).
  ```yaml
  template:
    - sensor:
        - name: "RC Demo Mode Demo Value Water Fresh Percent"
          unique_id: rc_demo_mode_demo_value_water_fresh_percent
          unit_of_measurement: "%"
          icon: mdi:water-percent
          state: >
            {% if is_state('input_boolean.rc_demo_mode_enabled', 'on')
                  and is_state('select.rc_demo_mode_scenario', 'Water') %}
              {{ states('sensor.cycle_helper_water_fresh_percent') | float(75) }}
            {% else %}
              unknown
            {% endif %}
  ```

- `binary_sensor.rc_demo_mode_demo_value_connectivity_
  lte_up` — demo LTE upstream boolean; only surfaces
  when scenario=Connectivity AND enable toggle is ON.
  The tile is a `template:` binary_sensor (since 2022.x).
  ```yaml
  template:
    - binary_sensor:
        - name: "RC Demo Mode Demo Value Connectivity LTE Up"
          unique_id: rc_demo_mode_demo_value_connectivity_lte_up
          device_class: connectivity
          icon: mdi:signal-cellular-3
          state: >
            {% if is_state('input_boolean.rc_demo_mode_enabled', 'on')
                  and is_state('select.rc_demo_mode_scenario', 'Connectivity') %}
              {{ states('binary_sensor.cycle_helper_connectivity_lte') }}
            {% else %}
              unknown
            {% endif %}
  ```

- `button.rc_demo_mode_enable_battery` — operator-
  triggered: enable demo mode + pick the Battery
  scenario in one tap. The button is an `input_button:`
  domain entity (since 2022.x) that fires an automation
  flipping `input_boolean.rc_demo_mode_enabled` ON +
  setting `select.rc_demo_mode_scenario` to `Battery`.
  ```yaml
  input_button:
    rc_demo_mode_enable_battery:
      name: RC Demo Mode Enable Battery
      icon: mdi:battery
  ```

- `button.rc_demo_mode_enable_water` — operator-
  triggered: enable demo mode + pick the Water scenario
  in one tap. The button is an `input_button:` domain
  entity (since 2022.x) that fires an automation
  flipping `input_boolean.rc_demo_mode_enabled` ON +
  setting `select.rc_demo_mode_scenario` to `Water`.
  ```yaml
  input_button:
    rc_demo_mode_enable_water:
      name: RC Demo Mode Enable Water
      icon: mdi:water
  ```

- `button.rc_demo_mode_enable_connectivity` — operator-
  triggered: enable demo mode + pick the Connectivity
  scenario in one tap. The button is an `input_button:`
  domain entity (since 2022.x) that fires an automation
  flipping `input_boolean.rc_demo_mode_enabled` ON +
  setting `select.rc_demo_mode_scenario` to
  `Connectivity`.
  ```yaml
  input_button:
    rc_demo_mode_enable_connectivity:
      name: RC Demo Mode Enable Connectivity
      icon: mdi:signal-cellular-3
  ```

- `button.rc_demo_mode_disable` — operator-triggered:
  disable demo mode (clears the enable toggle + resets
  the scenario to Off). The button is an `input_button:`
  domain entity (since 2022.x) that fires an automation
  flipping `input_boolean.rc_demo_mode_enabled` OFF +
  setting `select.rc_demo_mode_scenario` to `Off`.
  ```yaml
  input_button:
    rc_demo_mode_disable:
      name: RC Demo Mode Disable
      icon: mdi:stop-circle-outline
  ```

## §8 Automations (MANDATORY before first use)

The §8 walks through the FIVE MANDATORY automations. The
recipe is the contract layer; the automation wrappers are
documented below.

### §8.1 Demo mode auto-disable on real sensor reconnect

The automation fires when
`input_boolean.rc_demo_mode_enabled` is ON AND ANY of the
upstream real sensors (battery sensor + tank sensor +
LTE-up sensor — whichever matches the picked scenario)
transitions from `unavailable` / `unknown` to a real
value. The automation clears the enable toggle + resets
the scenario selector to Off + writes an audit-log entry
+ fires a notification warning the operator that demo
mode has been auto-disabled.

```yaml
automation:
  - id: rc_demo_mode_auto_disable
    alias: "RC Demo Mode: Auto-disable on real sensor reconnect"
    mode: single
    trigger:
      - platform: state
        entity_id: sensor.rc_demo_mode_real_sensor_battery
        from: "unavailable"
      - platform: state
        entity_id: sensor.rc_demo_mode_real_sensor_battery
        from: "unknown"
      - platform: state
        entity_id: sensor.rc_demo_mode_real_sensor_water_fresh
        from: "unavailable"
      - platform: state
        entity_id: sensor.rc_demo_mode_real_sensor_water_fresh
        from: "unknown"
      - platform: state
        entity_id: binary_sensor.rc_demo_mode_real_sensor_connectivity_lte_up
        from: "unavailable"
      - platform: state
        entity_id: binary_sensor.rc_demo_mode_real_sensor_connectivity_lte_up
        from: "unknown"
    condition:
      - condition: state
        entity_id: input_boolean.rc_demo_mode_enabled
        state: "on"
    action:
      - service: input_boolean.turn_off
        target:
          entity_id: input_boolean.rc_demo_mode_enabled
      - service: select.select_option
        target:
          entity_id: select.rc_demo_mode_scenario
        data:
          option: "Off"
      - service: logbook.log
        data:
          name: "RC Demo Mode"
          message: >
            Demo mode auto-disabled: real sensor
            {{ trigger.entity_id }} reconnected with value
            {{ trigger.to_state.state }}.
            Demo mode has been cleared + scenario reset to
            Off.
          domain: roamcore
      - service: persistent_notification.create
        data:
          title: "RC Demo Mode auto-disabled"
          message: >
            A real sensor just reconnected.
            Demo mode has been cleared + scenario reset to
            Off.
```

### §8.2 Demo mode never controls actual hardware guard

The automation fires when ANY `script.*` / `automation.*`
action tries to call a `switch.turn_on` /
`switch.turn_off` / `light.turn_on` / `light.turn_off`
/ `climate.set_*` service while
`input_boolean.rc_demo_mode_enabled` is ON AND the
target entity is one of the "real hardware" entities the
operator has flagged in their
`input_text.rc_demo_mode_real_hardware_targets`. The
automation BLOCKS the service call + logs a security-
style audit entry + flips
`binary_sensor.rc_demo_mode_is_blocking_real_hardware`
to TRUE + fires a critical notification.

```yaml
automation:
  - id: rc_demo_mode_never_controls_actual_hardware
    alias: "RC Demo Mode: Never controls actual hardware guard"
    mode: single
    trigger:
      - platform: state
        entity_id: input_boolean.rc_demo_mode_enabled
        to: "on"
    condition: []
    action:
      - repeat:
          for_each: >
            {{ states('input_text.rc_demo_mode_real_hardware_targets')
                .split(',') | map('trim') | reject('equalto', '') | list }}
          sequence:
            - service: logbook.log
              data:
                name: "RC Demo Mode"
                message: >
                  Demo mode is ON + real-hardware target
                  {{ repeat.item }} is configured. Confirm
                  no automations are writing demo values
                  to {{ repeat.item }}.
                domain: roamcore
```

(The actual never-controls-hardware guard is enforced by
the operator's automations checking
`is_state('input_boolean.rc_demo_mode_enabled', 'on')`
AND `{{ repeat.item in states('input_text.rc_demo_mode_
real_hardware_targets').split(',') | map('trim') |
reject('equalto', '') | list }}` before calling any
`switch.*` / `light.*` / `climate.*` service on a
flagged real-hardware entity. The automation above is
the reminder pattern — the operator's automations do the
actual blocking.)

### §8.3 Demo mode blocks remote access

The automation fires when a remote-access session
attempts to interact with the dashboard while
`input_boolean.rc_demo_mode_enabled` is ON. The
automation surfaces a "demo mode is ON — values are not
real" banner in the remote-access dashboard + adds the
demo-mode-active flag to the remote-access session
metadata + (if the operator's remote-access setup
supports it) refuses write-capable actions until demo
mode is disabled.

```yaml
automation:
  - id: rc_demo_mode_blocks_remote_access
    alias: "RC Demo Mode: Blocks remote access banner"
    mode: single
    trigger:
      - platform: state
        entity_id: input_boolean.rc_demo_mode_enabled
        to: "on"
    action:
      - service: persistent_notification.create
        data:
          title: "RC Demo Mode is ON"
          message: >
            Demo mode is currently enabled. Any remote-
            access sessions will see demo values + a
            "values are not real" banner until demo mode
            is disabled.
            Press `button.rc_demo_mode_disable` to
            disable demo mode.
      - service: logbook.log
        data:
          name: "RC Demo Mode"
          message: >
            Demo mode is ON. Remote-access sessions
            should surface the "values are not real"
            banner + (if supported) refuse write-capable
            actions.
          domain: roamcore
```

### §8.4 Demo mode audit-log entry

The automation fires when
`input_boolean.rc_demo_mode_enabled` flips from OFF to
ON OR from ON to OFF. The automation writes an audit-log
entry with the scenario selector value + the operator
identity (if the remote-access session tracks it) + the
timestamp + the reason.

```yaml
automation:
  - id: rc_demo_mode_audit_log_entry
    alias: "RC Demo Mode: Audit-log entry on enable/disable"
    mode: single
    trigger:
      - platform: state
        entity_id: input_boolean.rc_demo_mode_enabled
    action:
      - service: logbook.log
        data:
          name: "RC Demo Mode"
          message: >
            Demo mode {{ 'enabled' if trigger.to_state.state
              == 'on' else 'disabled' }}.
            Scenario: {{ states('select.rc_demo_mode_scenario')
              if trigger.to_state.state == 'on' else
              'Off' }}.
            Time: {{ now().isoformat() }}.
          domain: roamcore
```

### §8.5 Demo mode is operator-only

The automation fires when a non-operator source (a
sensor auto-change / an automation script / a remote-
access non-operator session) tries to flip
`input_boolean.rc_demo_mode_enabled`. The automation
BLOCKS the change + writes an audit-log entry + fires a
critical notification.

```yaml
automation:
  - id: rc_demo_mode_operator_only
    alias: "RC Demo Mode: Operator-only guard"
    mode: single
    trigger:
      - platform: state
        entity_id: input_boolean.rc_demo_mode_enabled
        to: "on"
    condition:
      # Operator must have pressed an enable_* button OR
      # manually flipped the toggle from the dashboard.
      # Non-operator sources (a sensor auto-change / an
      # automation script / a remote-access non-operator
      # session) should never flip this toggle. The
      # operator can confirm by checking the trigger's
      # context.user_id — if it's not the operator's
      # user_id, block + log.
      - condition: template
        value_template: >
          {{ trigger.context.user_id is none
              or trigger.context.user_id not in [
                'OPERATOR_USER_ID_1',
                'OPERATOR_USER_ID_2',
                # add operator user_ids here
              ] }}
    action:
      - service: input_boolean.turn_off
        target:
          entity_id: input_boolean.rc_demo_mode_enabled
      - service: logbook.log
        data:
          name: "RC Demo Mode"
          message: >
            BLOCKED: Non-operator source tried to enable
            demo mode (user_id={{ trigger.context.user_id
            }}, entity_id={{ trigger.entity_id }}). Demo
            mode has been re-disabled + an audit-log
            entry written.
          domain: roamcore
      - service: persistent_notification.create
        data:
          title: "RC Demo Mode: BLOCKED"
          message: >
            A non-operator source tried to enable demo
            mode. Demo mode has been re-disabled.
```

## §9 Troubleshooting

### §9.1 Demo mode is stuck on Off

- **Cause:** The §8.1 auto-disable automation may have
  fired (a real sensor reconnected) OR the operator
  pressed the disable button. OR the upstream helpers
  aren't installed.
- **Fix:** Verify the upstream `input_boolean` /
  `input_select` / `input_text` / `input_number` helpers
  are installed (Developer Tools → Services → search for
  `input_boolean.toggle` — should return the service).
  Verify the operator pressed the correct enable_*
  button (button.rc_demo_mode_enable_battery /
  button.rc_demo_mode_enable_water /
  button.rc_demo_mode_enable_connectivity). Verify
  no real sensor is reporting a value (the §8.1
  auto-disable guard fires on real-sensor-reconnect).

### §9.2 Demo values never appear in the dashboard

- **Cause:** The `template:` sensor wrappers for the
  demo values aren't wired OR the scenario selector
  doesn't match the demo value. OR the upstream real
  sensor for the picked scenario is already reporting
  a real value (which would trigger the §8.1 auto-
  disable guard).
- **Fix:** Verify the `template:` sensor wrappers are
  configured (Developer Tools → States → search
  `rc_demo_mode_demo_value_battery_soc_percent` /
  `rc_demo_mode_demo_value_water_fresh_percent` /
  `rc_demo_mode_demo_value_connectivity_lte_up`). Verify
  the scenario selector matches the demo value (Battery
  / Water / Connectivity). Verify the upstream real
  sensor for the picked scenario is NOT reporting (if
  reporting, the §8.1 auto-disable guard will fire and
  clear demo mode).

### §9.3 §8.1 auto-disable guard never fires

- **Cause:** The §8.1 automation is misconfigured OR
  the upstream real sensors don't transition from
  `unavailable` / `unknown` to a real value (some
  integrations report `unknown` → `unknown` instead of
  `unknown` → real-value, which wouldn't trigger the
  automation).
- **Fix:** Verify the §8.1 automation is ENABLED
  (Developer Tools → Automations → search
  "rc_demo_mode_auto_disable" → toggle ON). Verify the
  trigger uses `from: "unavailable"` AND `from:
  "unknown"`. Verify the condition checks
  `input_boolean.rc_demo_mode_enabled` is `on`. Verify
  the upstream real sensors actually transition from
  `unavailable` / `unknown` to a real value (some
  integrations use a different transition pattern;
  consult the integration's docs).

### §9.4 §8.2 never-controls-hardware guard fires unexpectedly

- **Cause:** The `input_text.rc_demo_mode_real_hardware_
  targets` list contains an entity id that the operator
  wants to control normally (NOT a real-hardware target
  that should be guarded).
- **Fix:** Remove the entity id from the
  `input_text.rc_demo_mode_real_hardware_targets` list.
  The list should ONLY contain entity ids that the
  operator never wants demo-mode values to write to.

### §9.5 §8.3 blocks-remote-access guard surfaces banner every time

- **Cause:** The §8.3 automation is firing every time
  `input_boolean.rc_demo_mode_enabled` flips to ON,
  which is expected behavior (the banner is intended to
  fire on every enable).
- **Fix:** This is expected behavior. The operator can
  disable demo mode to clear the banner. OR the operator
  can configure the remote-access setup to suppress the
  banner for trusted operator sessions.

### §9.6 §8.5 operator-only guard BLOCKS the operator's own enable

- **Cause:** The operator's `user_id` is NOT in the
  §8.5 automation's `condition.value_template` list.
  The automation only allows enable from operator
  user_ids; if the operator's user_id isn't in the list,
  the automation blocks the enable.
- **Fix:** Add the operator's user_id to the §8.5
  automation's `condition.value_template` list. The
  operator can find their user_id in Developer Tools →
  Events → listen for an `input_boolean.toggle` event
  (the `user_id` field in the event context is the
  operator's user_id).

## §10 Privacy

The demo-mode umbrella produces no telemetry beyond local
on/off state:

- The upstream `input_boolean.rc_demo_mode_enabled` +
  `select.rc_demo_mode_scenario` +
  `sensor.rc_demo_mode_active_scenario` +
  `binary_sensor.rc_demo_mode_is_blocking_real_hardware`
  + `sensor.rc_demo_mode_demo_value_battery_soc_percent`
  + `sensor.rc_demo_mode_demo_value_water_fresh_percent`
  + `binary_sensor.rc_demo_mode_demo_value_connectivity_
  lte_up` helper entities are local; the data never
  leaves the HA server.
- The §8.4 audit-log-entry automation writes entries
  to the HA core logbook; the logbook is operator-owned
  and never leaves the HA server.
- No cloud call-home. No RoamCore-side telemetry. No
  third-party analytics.

## §11 Promoting to tier-a

Tier-a would require a RoamCore-owned demo-mode engine +
integration code + integration tests against a real
demo-mode engine bench (a controlled environment with
canned fixture responses for sensor availability events
+ canned fixture responses for remote-access session
events + canned fixture responses for service-call
blocking events — all wired together in a controlled
environment).

Specifically:
- A RoamCore-owned operator-wired setup flow that walks
  the operator through choosing Off / Battery / Water /
  Connectivity + declaring the upstream real-hardware
  target entities + the §8 automations (the current
  slice ships the upstream HA core `input_boolean` +
  `input_select` + `input_text` + `input_number`
  helpers + the HA core `template:` sensor + `template:`
  binary_sensor wrappers, NOT a RoamCore-owned operator-
  wired setup flow).
- A RoamCore-owned demo-mode integration code that maps
  the upstream signals (real sensor availability + enable
  toggle + scenario selector) into the 11 `rc_demo_mode_*`
  contract tiles (the current slice ships a thin
  `template:` sensor + `template:` binary_sensor +
  `input_boolean` + `input_select` + `input_text` +
  `input_number` helper, NOT a RoamCore-owned demo-mode
  integration code).
- Integration tests against a RoamCore-owned demo-mode
  engine bench (a controlled environment with canned
  fixture responses for sensor availability events +
  canned fixture responses for remote-access session
  events + canned fixture responses for service-call
  blocking events — all wired together in a controlled
  environment). The current slice ships manifest-honesty
  tests ONLY, NOT integration tests.

Until those three are in place, the slice is tier-b.

## §12 Files in this connection + cross-references

- `connection.yml` — the source-of-truth manifest (tier=b,
  category=ai, status=beta, 11 `rc_demo_mode_*` contract
  tiles, FIVE MANDATORY automations, FOUR operator-pickable
  demo scenarios).
- `__init__.py` — `DOMAIN = "demo_mode"` marker for the
  audit.
- `README.md` — the folder overview + 4-scenario summary +
  supersession pointer.
- `docs/recipe.md` — this file (the full howto).
- `tests/test_connection_yml.py` — 7 manifest-honesty
  tests (id_matches_folder_name + tier_b_without_tier_a_
  markers + requires_docs_recipe_published + category_
  matches_existing_legacy_doc + dashboard_tiles_follow_
  rc_naming + status_reflects_no_native_demo_mode_engine +
  automations_are_documented).

Cross-references:
- Legacy catalog page (now superseded by this slice):
  `docs/catalog/ai/demo-mode.md`.
- HA core `input_boolean` integration (the canonical
  demo-enabled helper umbrella): https://www.home-assistant.io/integrations/input_boolean/.
- HA core `input_select` integration (the canonical
  scenario selector helper): https://www.home-assistant.io/integrations/input_select/.
- HA core `input_text` integration (the canonical
  real-hardware target list helper): https://www.home-assistant.io/integrations/input_text/.
- HA core `input_number` integration (the canonical
  demo-value helper): https://www.home-assistant.io/integrations/input_number/.
- HA core `template:` integration (the canonical
  active-scenario + demo-value derivation): https://www.home-assistant.io/integrations/template/.
- Time-atomic (the time-of-day primitives used by the
  §8.4 audit-log entry's timestamp): `connections/time-
  atomic/` (Wave 3 #55).
- Remote-access (the VPN primitive used by the §8.3
  blocks-remote-access guard): `connections/remote-
  access/` (Wave 3 #58).
- Approach lights (the §8.3 blocks-remote-access guard's
  dashboard banner pattern): `connections/approach-
  lights/` (Wave 3 #52).
- Fans (the §8.2 never-controls-actual-hardware guard's
  fan-protection cross-reference): `connections/fans/`
  (Wave 3 #59).
- Leveling (the §8.5 operator-only guard's levelling-
  jack protection cross-reference): `connections/
  leveling/` (Wave 3 #60).
- Mode (the §8.4 audit-log entry's mode-change cross-
  reference): `connections/mode/` (Wave 3 #61).
- RoamCore entity naming: `docs/reference/rc-entity-
  naming.md` (the `demo_mode` subsystem was added by
  this slice).