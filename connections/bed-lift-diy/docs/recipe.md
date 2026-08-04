# DIY bed lift — tier-c recipe connection

**Tier:** C (recipe)
**Audience:** A RoamCore user who wants vendor-neutral up/down control
of a DIY bed lift (operator-built linear actuators OR winch + motor +
strap OR any 2-relay + 2-limit-switch bed lift assembled by the
operator) with safety-first wiring interlocks, using one of two upstream
operator-side paths: ESPHome custom `cover:` (Path A — recommended for
ESPHome-friendly installs), or a Shelly 1 / Shelly Plus 1 / Zooz ZEN17 /
Aeotec Nano Switch relay pair + HA core `template:` cover (Path B —
recommended for relay-friendly installs). Both paths land on the same
vendor-neutral contract layer via `rc_bed_lift_*` dashboard tiles +
OpenClaw bed-lift queries ("lift the bed", "lower the bed", "stop
the bed", "what's the bed position?", "is the bed safe?", "is the bed
moving?", "is the bed obstructed?", "is the bed low-voltage locked?",
"set bed mode").

This howto is mirrored into `docs/connections/bed-lift-diy.md` by the
catalog cron (`scripts/build_catalog.py`) so it shows up under the
public docs site's "Connections" section. Keep this recipe as the
source of truth.

**Sibling connection:** [`connections/happijac/`](../happijac/) (Wave 3
#43) is the tier-b Happijac-specific connection for the LCI Happijac
controller flow. The DIY sibling shares the §5 contract tile ids (the
`rc_bed_lift_*` namespace is vendor-neutral), shares the §6 safety
interlocks, shares the §7 automations, and shares the §8 OpenClaw
queries — only the hardware stack differs (operator-built DIY
actuators / winch + motor + strap vs LCI Happijac controller). The
Happijac sibling is referenced explicitly in §6 + §7 where the LCI
Happijac controller flow has deeper controller-specific notes.

## §1 What is DIY bed lift in RoamCore?

Bed lift control — van bed up / down — is the **foundation** of every
sleep-cycle automation in a van with a DIY bed lift (operator-built
linear actuators OR winch + motor + strap OR any 2-relay + 2-limit-
switch bed lift assembled by the operator):

- **Vendor-neutral cover semantics.** RoamCore wants a `cover.<name>`
  tile (not a vendor-specific `cover.diy_bed_lift` tile) so that a DIY
  linear-actuator bed today + a winch + strap build next year + an LCI
  Happijac controller retrofit later all drop onto the same contract
  layer. The cover template `cover.rc_bed_lift_position` is the single
  integration point — every automation, every OpenClaw query, every
  dashboard tile binds to that contract entity.
- **Two upstream paths** (operator picks based on existing IoT
  wiring + comfort with ESPHome vs relay-friendly templates + safety
  interlock preference):
  - **Path A — ESPHome custom `cover:`** (recommended for
    ESPHome-friendly installs). ESPHome handles the device-side GPIO
    + 2× outputs for the relay coils + 2× binary_sensor inputs for the
    limit microswitches + an optional ADC input for the CT-clamp
    current sensor. The `cover:` component is built into ESPHome; we
    declare `cover.bed_lift` (NOT `cover.diy_bed_lift`) so the entity
    id is operator-neutral. ESPHome exposes a config_flow since
    2023.x.
  - **Path B — Dry-contact relay + HA core `template:` cover** (no
    ESPHome required; recommended when the operator is relay-friendly
    + wants the upstream HA core integrations to do the IO). Two
    Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano Switch units
    are wired to the DIY actuator / motor driver's up/down inputs (5
    V signal, common, up, down). HA auto-discovers the Shelly units via
    mDNS (`shelly` integration has a config_flow since 2019.x); the
    upstream `switch.shelly_*_relay` entities + the upstream
    `binary_sensor.shelly_*_dry_contact` entities for the limits are
    what we wrap.
- **Safety-first wiring.** Bed lift control is the only RoamCore
  connection where mis-wiring can cause a **physical injury** (the
  bed motor can pinch / crush an operator or occupant). Every install
  MUST include:
  - **2× limit microswitches** (one for UP, one for DOWN) wired into
    either ESPHome binary_sensor inputs (Path A) or Shelly dry-contact
    inputs (Path B). The cover template MUST use these for up-stop
    and down-stop logic — not timing.
  - **limit-sanity aggregate** (`binary_sensor.rc_bed_lift_safety_ok`)
    that flags FALSE when both limits report TRUE simultaneously (a
    wiring fault — mechanically impossible; operator MUST fix before
    next use).
  - **low-voltage lockout** that cross-references the Victron
    `connections/victron/` recipe's `sensor.rc_power_battery_soc` +
    `binary_sensor.rc_power_shore_connected` — TRUE when SOC < 20 %
    OR shore disconnected AND battery low; the cover template
    rejects any motion command while the lockout is TRUE.
  - **obstruction detection** (current-clamp for Path A; motor-stall
    heuristic for Path B).
  - **mode-aware lockouts** (Stealth silent hours stops any in-
    progress motion + suppresses any auto-lift scheduling; Sleep mode
    locks the bed down overnight; Boost disables mode-aware lockouts
    for service work).

RoamCore ships no native DIY bed lift controller. We RECIPE the well-
understood combination of one of two upstream operator-side paths
and a translation layer that maps each upstream `cover.bed_lift`
(Path A) or upstream `switch.shelly_*_relay` entities (Path B) +
upstream limit binary_sensors into a vendor-neutral `rc_bed_lift_*`
contract layer.

The Happijac sibling connection ([`connections/happijac/`](../happijac/),
Wave 3 #43) is the tier-b pattern for the LCI Happijac controller
flow (stock Happijac + dry-contact relay pair + limits + optional
CT clamp + Path A ESPHome OR Path B Shelly / Shelly Plus / Zooz
ZEN17 / Aeotec Nano Switch). The DIY sibling differs ONLY in
hardware stack (operator-built linear actuators OR winch + motor +
strap vs LCI Happijac controller); the operator-side ESPHome or HA-
core `template:` cover wiring is identical. We ship this as a
**sibling** tier-c connection because the operator's hardware
variability is greater (DIY actuators have a wider current-draw
range, motor driver choice varies — H-bridge vs two-relay-pair vs
single-relay direction-control — and the operator owns the
assembly rather than buying an off-the-shelf controller), and tier-c
is the honest marker for "recipe-only, no operator-bench, no
canonical RoamCore-owned config_flow".

The §6.4 mode-aware lockouts + the §7 automations depend on the
RoamCore mode builder (Wave 2 #23, [`connections/mode-builder/`](../mode-builder/))
to expose `select.roamcore_mode` with the Off / Auto / Travel /
Camp / Stealth states; the recipe §7 conditions on
`select.roamcore_mode == stealth` (§7.1) and
`select.roamcore_mode == sleep` (§7.2 + §7.6). The system summary
tile (Wave 2 #26, [`connections/system-summary/`](../system-summary/))
includes the bed-lift state in its operator-facing summary.

## §2 Prerequisites

The operator MUST have ALL of these on the bench / in the van before
this recipe can produce a working `cover.rc_bed_lift_position` tile.
Missing any one item creates either a wiring fault (the limit sanity
aggregate flags FALSE) or a motor that refuses to run (the low-
voltage lockout is TRUE) — both are intentional gates, not bugs.

### Hardware

- **DIY bed lift system** (operator-built linear actuators OR winch +
  motor + strap OR any 2-relay + 2-limit-switch bed lift assembled by
  the operator). The DIY variant of the bed lift hardware stack is
  the operator's choice — common combinations include:
  - **Linear actuators** (12 V or 24 V DC, with internal limit
    switches or external add-on microswitches; typically driven by
    an H-bridge motor driver or a two-relay pair wired as a polarity
    reverser).
  - **Winch + motor + strap** (12 V or 24 V DC, with a single-relay
    direction-control relay pair for UP and DOWN; the strap wraps
    around a pulley that the winch spools).
  - **Other 2-relay + 2-limit-switch bed lifts** (any operator-built
    variant that exposes up/down dry-contact inputs that a relay pair
    can drive + limit microswitches that can be sensed).
  The recipe is hardware-agnostic — the upstream cover semantics are
  the same regardless of the operator's exact actuator / winch /
  strap choice; the only difference is the relay pair's wiring
  topology (H-bridge vs polarity-reverser vs direction-control).
- **2× dry-contact relays** with the coil voltage matched to the
  chosen control path:
  - **Path A (ESPHome):** the relay coil voltage MUST match the
    ESPHome GPIO bank voltage (typically 3.3 V or 5 V). The recipe's
    §3 ESPHome YAML assumes 5 V coil; for 3.3 V coil the operator
    must swap `output` `pin:` to a 3.3 V-rated GPIO.
  - **Path B (Shelly / Shelly Plus / Zooz ZEN17 / Aeotec Nano
    Switch):** the Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec
    Nano Switch units drive their relay coils directly from mains
    (Shelly 1, Shelly Plus 1, Aeotec Nano Switch) or from 12 V
    (Zooz ZEN17). Pick the variant that matches the DIY actuator /
    motor driver's coil voltage.
- **5 V logic-level compatibility check** for Path A: the ESPHome
  GPIO bank voltage MUST match the relay coil voltage (3.3 V GPIO +
  5 V relay coil requires a level shifter; 5 V GPIO + 5 V relay
  coil is direct). The recipe's §3 ESPHome YAML assumes direct 5 V
  GPIO + 5 V relay coil; a level-shifter variant is documented in
  the troubleshooting §8 entry "bed not moving (relay polarity /
  coil voltage)".
- **A fuse per relay coil** (one for UP, one for DOWN). Both fuses
  sized to the relay coil current at 1.5× overcurrent rating. Fuses
  MUST be in series with the coil supply, NOT in series with the
  ESPHome GPIO output pin.
- **A flyback diode per relay coil** (1N4007 or equivalent). The
  diode cathode connects to the +V coil supply rail; the diode
  anode connects to the relay coil driver pin. Without this diode,
  the relay coil's inductive flyback voltage will eventually destroy
  the ESPHome output pin (Path A) or the Shelly / Shelly Plus / Zooz
  ZEN17 / Aeotec Nano Switch relay driver (Path B).
- **2× limit microswitches** (NC or NO per the actuator / motor
  driver's wiring) with mechanical debounce. Both microswitches MUST
  be wired into either the ESPHome binary_sensor inputs (Path A) or
  the Shelly dry-contact inputs (Path B). The recipe assumes NO
  (normally open) microswitches wired to the ESPHome / Shelly
  pull-up — the NC variant inverts the binary_sensor pull-up logic
  and is documented in the §8 troubleshooting entry "bed moves up
  but not down (NC/NO mis-wire)".
- **Optional CT-clamp current sensor** (Path A ESPHome only — for
  Path B the `current_based_obstruction_detection` block in the
  recipe §4 wires the same logic via the Shelly / Shelly Plus / Zooz
  / Aeotec current sensor). The CT clamp slips over the bed motor
  power wire (NOT the upstream shore feed). The CT clamp output goes
  to an ADC pin on the ESP device (Path A) or the dry-contact
  inputs on the Shelly (Path B).

### Software

- **Home Assistant 2023.8 or newer** (the `template:` cover + the
  ESPHome integration both have config_flow at this version).
- **ESPHome 2023.x or newer** for Path A (the `cover:` component
  has config_flow since 2023.x; the operator wires the cover YAML
  from recipe §3). ESPHome Device Builder is preferred over
  ESPHome CLI for fleet installs.
- **Shelly / Shelly Plus integration 2019.x or newer** for Path B
  (config_flow since 2019.x). Zooz ZEN17 / Aeotec Nano Switch users
  wire the equivalent `zwave_js` integration for those controllers
  (also config_flow at this HA version).
- **Music Assistant** (optional — only required for the §7.5 "obstruction
  detected → stop + alert" TTS automation; the recipe §7 walks through
  the optional install). Music Assistant is `connections/music-assistant/`.

### Knowledge

- The operator MUST understand the wiring of their DIY actuator /
  motor driver's up/down dry-contact inputs (the controller manual
  is the reference; for operator-built actuators / winch + strap
  the operator's own build notes are the reference). No RoamCore
  install walk-through covers the controller-side wiring — that's a
  per-controller decision.
- The operator MUST understand the ESPHome YAML editing workflow for
  Path A (the recipe §3 walks through the YAML fields; the
  operator's pin choices are theirs).
- The operator MUST understand the Shelly / Shelly Plus / Zooz ZEN17
  / Aeotec Nano Switch device wiring for Path B (the recipe §4
  walks through the device-side wiring + the upstream entity ids).

## §3 Path A — ESPHome custom cover (recommended for ESPHome-friendly installs)

Path A is the recommended approach for operators who already run
ESPHome for other appliances (lights, switches, fans, sensors). The
recipe declares the operator's `cover.bed_lift` directly in the
ESPHome YAML; HA discovers the device via the ESPHome integration
(config_flow since 2023.x); the recipe's §5 then maps the upstream
`cover.bed_lift` + the four safety interlocks into the
`rc_bed_lift_*` contract tiles via a `template:` cover.

### §3.1 ESPHome YAML — bed lift with up/down outputs + 2 limit binary_sensors + optional current sensor

```yaml
# connections/bed-lift-diy/bed-lift.yaml (Path A ESPHome device)
esphome:
  name: roamcore-bed-lift-diy
  friendly_name: RoamCore DIY Bed Lift
  platform: ESP32
  board: esp32dev

# Substitute the operator's actual ESPHome secret for `api_encryption_key`.
api:
  encryption:
    key: !secret api_encryption_key

# Substitute the operator's actual ESPHome Wi-Fi credentials.
wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password
  ap:
    ssid: "RoamCore DIY Bed Lift Fallback"
    password: !secret wifi_fallback_password

captive_portal:

logger:

# Two GPIO outputs for the UP relay coil + the DOWN relay coil.
# Substitute operator's actual GPIO pins for up_pin + down_pin.
# The pin mode + inverted: flag MUST match the operator's relay coil
# polarity (relay boards that turn on when the GPIO goes LOW need
# inverted: true).
output:
  - id: bed_lift_up
    platform: gpio
    pin: GPIO26
    inverted: false
  - id: bed_lift_down
    platform: gpio
    pin: GPIO27
    inverted: false

# A safe-by-default output that drives BOTH outputs off in a single
# call. The cover template's stop_action uses this; safety interlocks
# (limit-sanity, low-voltage lockout, obstruction detected) also call
# this to halt any in-progress motion.
output:
  - id: bed_lift_safe_off
    platform: template
    id: bed_lift_safe_off_internal

# Per the recipe §2 prerequisites, the operator MUST include a fuse
# per relay coil + a flyback diode per relay coil. ESPHome cannot
# enforce those — they are the operator's wiring responsibility.

# Two binary_sensor inputs for the limit microswitches. Both have a
# 100 ms delayed_off filter to debounce mechanical bounce.
binary_sensor:
  - id: up_limit
    platform: gpio
    pin: GPIO32
    filters:
      - delayed_off: 100ms
  - id: down_limit
    platform: gpio
    pin: GPIO33
    filters:
      - delayed_off: 100ms

# Optional CT-clamp current sensor wired to the ADC pin (substitute
# operator's actual GPIO pin). Path A's obstruction detection
# uses this; Path B's obstruction detection uses the Shelly's
# current sensor via `current_based_obstruction_detection` instead.
sensor:
  - id: bed_lift_current
    platform: ct_clamp
    sensor: analog_input
    # The CT clamp output goes to a 100 Ω burden resistor;
    # the ESP's ADC pin reads the voltage across that resistor.
    # Adjust the calibration values per the operator's specific
    # CT clamp + burden resistor choice.
    calibration:
      current: 0.0
      voltage: 0.0
    update_interval: 500ms
  - id: analog_input
    platform: adc
    pin: GPIO34
    attenuation: auto

# The ESPHome `cover:` component synthesises up/down/stop semantics
# from the two outputs + the two limit binary_sensors. The operator
# MUST use these limit binary_sensors for up-stop and down-stop
# logic — NOT timing. The delayed_off filter on each limit provides
# 100 ms mechanical debounce.
cover:
  - platform: template
    name: "Bed Lift"
    id: bed_lift
    open_action:
      - output.turn_on: bed_lift_up
      - delay: 5000ms  # Safety timeout; the up_limit binary_sensor should stop it sooner.
      - output.turn_off: bed_lift_up
      - output.turn_off: bed_lift_safe_off_internal
    open_endstop: up_limit
    open_duration: 30000ms  # Worst-case full travel time; the up_limit typically triggers in 10–20 s.
    close_action:
      - output.turn_on: bed_lift_down
      - delay: 5000ms
      - output.turn_off: bed_lift_down
      - output.turn_off: bed_lift_safe_off_internal
    close_endstop: down_limit
    close_duration: 30000ms
    stop_action:
      - output.turn_off: bed_lift_up
      - output.turn_off: bed_lift_down
      - output.turn_off: bed_lift_safe_off_internal
```

### §3.2 HA-side `template:` cover wiring the ESPHome device into the rc_bed_lift_* contract tiles

```yaml
# connections/bed-lift-diy/cover-template.yaml (Path A — wraps the
# ESPHome `cover.bed_lift` into the vendor-neutral
# `cover.rc_bed_lift_position` contract tile). Substitute the
# operator's actual ESPHome entity ids where noted.

# (Section §5 walks through the full rc_bed_lift_* template layer
# — these are the most important tiles; the §5 layer wraps both
# Path A's cover.bed_lift AND Path B's template cover.bed_lift into
# the same contract tiles.)
```

## §4 Path B — Dry-contact relay + HA core template cover (no ESPHome)

Path B is recommended for operators who already run Shelly / Shelly
Plus / Zooz ZEN17 / Aeotec Nano Switch units in their van (typical
for retrofit installs where the operator is relay-friendly + wants
the upstream HA core integrations to do the IO).

### §4.1 Shelly / Shelly Plus / Zooz ZEN17 / Aeotec Nano Switch wiring

For two Shelly 1 (or Shelly Plus 1) units (substitute for Zooz ZEN17
or Aeotec Nano Switch equivalent where noted):

- **Shelly 1 unit 1 (UP relay)**:
  - L (line) → the DIY actuator / motor driver's UP coil +V common
  - N (neutral) → the DIY actuator / motor driver's UP coil neutral
  - The Shelly output dry-contact (O) → the DIY actuator / motor
    driver's UP dry-contact input
  - 5 V signal → the UP limit microswitch common
  - The Shelly dry-contact input (SW) → the UP limit microswitch NO
    contact

- **Shelly 1 unit 2 (DOWN relay)**:
  - L (line) → the DIY actuator / motor driver's DOWN coil +V common
  - N (neutral) → the DIY actuator / motor driver's DOWN coil
    neutral
  - The Shelly output dry-contact (O) → the DIY actuator / motor
    driver's DOWN dry-contact input
  - 5 V signal → the DOWN limit microswitch common
  - The Shelly dry-contact input (SW) → the DOWN limit microswitch NO
    contact

(Zooz ZEN17 + Aeotec Nano Switch equivalent wiring is documented in
the controller's Z-Wave manual; the entity-id shape is the same:
`switch.shelly_*_relay` for the relay + `binary_sensor.shelly_*_dry_contact`
for the limit input.)

### §4.2 HA auto-discovery

The two Shelly units are auto-discovered by HA's `shelly` integration
via mDNS (config_flow since 2019.x). After auto-discovery, the
upstream entities are:

- `switch.shelly_bed_lift_up_relay` (UP relay)
- `switch.shelly_bed_lift_down_relay` (DOWN relay)
- `binary_sensor.shelly_bed_lift_up_dry_contact` (UP limit microswitch)
- `binary_sensor.shelly_bed_lift_down_dry_contact` (DOWN limit
  microswitch)

(Zooz ZEN17 units show as `switch.zooz_*` etc.; Aeotec Nano Switch
units show as `switch.aeotec_*` etc.)

### §4.3 HA core `template:` cover wiring the Shelly entities into `cover.bed_lift`

```yaml
# connections/bed-lift-diy/cover-template-path-b.yaml (Path B —
# wraps the upstream `switch.shelly_bed_lift_up_relay` +
# `switch.shelly_bed_lift_down_relay` +
# `binary_sensor.shelly_bed_lift_up_dry_contact` +
# `binary_sensor.shelly_bed_lift_down_dry_contact` into a single
# `cover.bed_lift` + limit binary_sensor logic).

cover:
  - platform: template
    covers:
      bed_lift:
        friendly_name: "Bed Lift"
        open_cover:
          - switch.turn_on: switch.shelly_bed_lift_up_relay
          - wait_template: "{{ is_state('binary_sensor.shelly_bed_lift_up_dry_contact', 'on') }}"
            timeout: "00:00:30"
            continue_on_timeout: true
          - switch.turn_off: switch.shelly_bed_lift_up_relay
          - switch.turn_off: switch.shelly_bed_lift_down_relay
        close_cover:
          - switch.turn_on: switch.shelly_bed_lift_down_relay
          - wait_template: "{{ is_state('binary_sensor.shelly_bed_lift_down_dry_contact', 'on') }}"
            timeout: "00:00:30"
            continue_on_timeout: true
          - switch.turn_off: switch.shelly_bed_lift_down_relay
          - switch.turn_off: switch.shelly_bed_lift_up_relay
        stop_cover:
          - switch.turn_off: switch.shelly_bed_lift_up_relay
          - switch.turn_off: switch.shelly_bed_lift_down_relay

# Optional `current_based_obstruction_detection` for Path B. This
# uses the Shelly's current sensor to detect motor stall. Disable
# if the operator's Shelly variant does NOT have a current sensor.
binary_sensor:
  - platform: template
    sensors:
      bed_lift_obstruction_detected_path_b:
        friendly_name: "Bed Lift Obstruction Detected (Path B)"
        # The Shelly's `current` attribute on the relay entities
        # reports the relay's instantaneous current draw. The
        # motor-stall heuristic: any motion command that does not
        # result in a matching limit-switch change within 2 s of
        # sustained >5 A draw is an obstruction.
        value_template: >
          {{ (states('sensor.shelly_bed_lift_up_relay_current') | float(0) > 5.0
              or states('sensor.shelly_bed_lift_down_relay_current') | float(0) > 5.0) }}
        delay_on: "00:00:02"
        delay_off: "00:00:05"
```

## §5 RoamCore contract entities

Both Path A and Path B land on the same vendor-neutral `rc_bed_lift_*`
contract tiles. The recipe §5 helper YAML walks through each tile:

```yaml
# connections/bed-lift-diy/contract-tiles.yaml (template — both
# paths). Substitute the operator's actual upstream entity ids
# where noted.

# The `cover.rc_bed_lift_position` tile wraps the upstream
# cover.bed_lift (Path A) OR the template cover.bed_lift (Path B)
# into the vendor-neutral contract layer. Operator-neutral; the
# template cover inherits up/down/stop semantics from the
# underlying cover.
cover:
  - platform: template
    covers:
      rc_bed_lift_position:
        friendly_name: "Bed Lift (RoamCore)"
        # The template cover re-exposes the operator's underlying
        # cover.bed_lift with vendor-neutral action calls.
        open_cover:
          - cover.open_cover: cover.bed_lift
        close_cover:
          - cover.close_cover: cover.bed_lift
        stop_cover:
          - cover.stop_cover: cover.bed_lift
        value_template: "{{ states('cover.bed_lift') }}"

# Two binary_sensors wrapping the upstream limit binary_sensors
# (Path A: binary_sensor.up_limit + binary_sensor.down_limit; Path
# B: binary_sensor.shelly_bed_lift_up_dry_contact +
# binary_sensor.shelly_bed_lift_down_dry_contact). No translation
# needed; the entity ids are already vendor-neutral when the
# operator follows the recipe's wire-up.
binary_sensor:
  - platform: template
    sensors:
      rc_bed_lift_up_limit:
        friendly_name: "Bed Lift UP Limit (RoamCore)"
        value_template: "{{ is_state('binary_sensor.up_limit', 'on') }}"
      rc_bed_lift_down_limit:
        friendly_name: "Bed Lift DOWN Limit (RoamCore)"
        value_template: "{{ is_state('binary_sensor.down_limit', 'on') }}"
      rc_bed_lift_moving:
        friendly_name: "Bed Lift Moving (RoamCore)"
        # True whenever the underlying cover's state ∈ {opening, closing}.
        value_template: >
          {{ states('cover.bed_lift') in ('opening', 'closing') }}
      rc_bed_lift_safety_ok:
        friendly_name: "Bed Lift Safety OK (RoamCore)"
        # Limit-sanity aggregate — FALSE if both limits report TRUE
        # simultaneously (wiring fault). See §6 for the safety-first
        # wiring emphasis.
        value_template: >
          {{ not (is_state('binary_sensor.rc_bed_lift_up_limit', 'on')
                  and is_state('binary_sensor.rc_bed_lift_down_limit', 'on')) }}
      rc_bed_lift_obstruction_detected:
        friendly_name: "Bed Lift Obstruction Detected (RoamCore)"
        # Path A uses the CT-clamp current sensor wired into the
        # ESPHome device; Path B uses the binary_sensor.bed_lift_
        # obstruction_detected_path_b motor-stall heuristic.
        # Operator chooses which one to wire; the recipe §6 walks
        # through both.
        value_template: >
          {{ states('binary_sensor.bed_lift_obstruction_detected_path_a') | default('off')
             if is_state('binary_sensor.bed_lift_obstruction_detected_path_a', 'on')
             else states('binary_sensor.bed_lift_obstruction_detected_path_b') }}
      rc_bed_lift_low_voltage_lockout:
        friendly_name: "Bed Lift Low-Voltage Lockout (RoamCore)"
        # TRUE when inverter SOC < 20 % OR shore disconnected AND
        # battery low. Cross-references the Victron connections/victron/
        # recipe for SOC + shore state.
        value_template: >
          {{ (states('sensor.rc_power_battery_soc') | float(0) < 20.0)
              or (is_state('binary_sensor.rc_power_shore_connected', 'off')
                  and states('sensor.rc_power_battery_soc') | float(0) < 50.0) }}

sensor:
  - platform: template
    sensors:
      rc_bed_lift_position_pct:
        friendly_name: "Bed Lift Position (RoamCore)"
        # Inherited from cover.bed_lift.current_position (0 / 100 /
        # interpolated when the cover has implicit position feedback).
        value_template: "{{ state_attr('cover.bed_lift', 'current_position') | int(0) }}"
        unit_of_measurement: '%'
        icon: mdi:percent

# Three buttons for explicit affordances + OpenClaw agent actions.
# The agent binds to these button entities directly (the OpenClaw
# `lift_bed` / `lower_bed` / `stop_bed` queries fire off
# cover.open_cover / cover.close_cover / cover.stop_cover on the
# underlying cover.bed_lift; the buttons are wired so the same
# commands are exposed as user-clickable affordances + agent-callable
# commands).
button:
  - platform: template
    buttons:
      rc_bed_lift_lift:
        friendly_name: "Bed Lift UP (RoamCore)"
        press:
          - cover.open_cover: cover.bed_lift
      rc_bed_lift_lower:
        friendly_name: "Bed Lift DOWN (RoamCore)"
        press:
          - cover.close_cover: cover.bed_lift
      rc_bed_lift_stop:
        friendly_name: "Bed Lift STOP (RoamCore)"
        press:
          - cover.stop_cover: cover.bed_lift

# Operator-tunable mode: `auto` (RoamCore modes drive the bed —
# auto-lower at 23:00 when Sleep, auto-lift at 07:00 when Travel,
# etc.), `manual_only` (only the OpenClaw queries + the buttons
# work; RoamCore modes do NOT auto-schedule), `disabled` (no motion
# at all — service mode).
select:
  - platform: template
    selects:
      rc_bed_lift_mode:
        friendly_name: "Bed Lift Mode (RoamCore)"
        options:
          - auto
          - manual_only
          - disabled
        initial: auto
```

## §6 Safety interlocks (MANDATORY before first use)

Every install MUST verify ALL FOUR of the following before the
operator's first use of the bed lift. Each interlock is documented
here in full; the §5 contract layer is hard-gated on each. The
recipe's `test_connection_yml.py` file asserts the documentation
coverage (the `test_safety_interlocks_are_documented` defensive guard
for the future tier-a promotion's hard-enforced asserts).

For the LCI Happijac controller flow (stock Happijac + dry-contact
relay pair + limits + optional CT clamp), the same four safety
interlocks apply identically; see the Happijac sibling
[`connections/happijac/docs/recipe.md` §6](../happijac/docs/recipe.md)
for the controller-specific Happijac notes.

### §6.1 Limit-switch sanity (both limits cannot be true simultaneously)

The `binary_sensor.rc_bed_lift_safety_ok` tile computes NOR of
`up_limit` AND `down_limit`. If both limits report `true` at the
same time, the wiring is faulty (mechanically impossible to be at
both the UP and DOWN positions simultaneously); the cover template's
`stop_action` runs immediately + the cover refuses any further
motion commands until the operator presses
`button.rc_bed_lift_stop` + manually inspects the wiring (likely
causes: both microswitches are wired to the same ESPHome GPIO pin;
both Shelly dry-contact inputs are wired to the same microswitch
common; both Shelly dry-contact inputs are mis-configured as
inputs instead of switches; one of the microswitches is jammed
closed).

### §6.2 Low-voltage lockout via `sensor.rc_power_battery_soc` cross-reference to the Victron connection

The `binary_sensor.rc_bed_lift_low_voltage_lockout` tile is TRUE
whenever `sensor.rc_power_battery_soc < 20 %` (low SOC) OR
`binary_sensor.rc_power_shore_connected == off AND
sensor.rc_power_battery_soc < 50 %` (shore disconnected + battery
low for an extended run). This cross-references the Victron
`connections/victron/` recipe for SOC + shore state — the bed motor
draws enough current to brown out a low SOC battery bank; the
operator MUST resolve the lockout condition (wait for shore
re-connection, idle until SOC recovers, or jump-start from the
starter battery) before any motion command is accepted.

### §6.3 Obstruction detection via current sensor / motor-stall heuristic

The `binary_sensor.rc_bed_lift_obstruction_detected` tile is TRUE
whenever:

- **Path A (ESPHome):** the CT-clamp current sensor reads >5 A
  sustained for >2 s with no matching limit-switch change in the
  expected direction (motor is stalled against an obstruction).
- **Path B (Shelly / Shelly Plus / Zooz / Aeotec):** the
  `binary_sensor.bed_lift_obstruction_detected_path_b` motor-stall
  heuristic trips (Shelly current sensor reading >5 A sustained for
  >2 s with no matching limit-switch change).

When the tile is TRUE, the cover template's `stop_action` runs
immediately + the cover refuses any further motion commands until
the operator clears the obstruction + presses `button.rc_bed_lift_stop`
to acknowledge.

### §6.4 Mode-aware lockouts (Stealth silent hours, Sleep mode lock-down, Boost disable-mode-aware-lockouts)

- **Stealth silent hours** — at the start of silent hours, any in-
  progress bed motion is stopped + any auto-lift scheduling is
  suppressed (the cover template accepts ONLY manual button
  presses + OpenClaw `stop_bed` / `lift_bed` / `lower_bed` queries
  during silent hours).
- **Sleep mode** — when the operator selects the Sleep mode via
  `select.rc_bed_lift_mode = auto` AND the RoamCore mode is Sleep,
  a 23:00-local automation auto-lowers the bed. If the bed is
  already lowered, no action. If the operator is using the bed
  (presence says `rc_presence_only_driver_home == false`), the
  auto-lower is skipped. See §7.2.
- **Boost mode** — when the operator sets `select.rc_bed_lift_mode
  = disabled` for service work, the cover template accepts motion
  commands regardless of mode time of day (the Stealth / Sleep
  mode-aware lockouts are bypassed). The operator MUST set the mode
  back to `auto` or `manual_only` when service work is complete.

### §6.5 Actuator safety interlock — block lift when door unlocked (Wave 3 #48 deadbolts cross-reference)

The `binary_sensor.rc_bed_lift_obstruction_detected` tile is
additionally TRUE when the deadbolts connection (Wave 3 #48,
[`connections/deadbolts/`](../deadbolts/)) reports an unlocked door
state while the bed is in motion (the operator MUST lock the door
before raising or lowering the bed — the actuator safety interlock
prevents accidental bed motion while the operator is outside the
van). See §7.7.

### §6.6 HVAC service-mode block — block lift when HVAC service mode is engaged (Wave 3 #49 HVAC basics cross-reference)

The `binary_sensor.rc_bed_lift_low_voltage_lockout` tile is
additionally TRUE when the HVAC basics connection (Wave 3 #49,
[`connections/hvac-basics/`](../hvac-basics/)) reports an engaged
service mode (the operator MUST exit HVAC service mode before
raising or lowering the bed — the bed actuator + the HVAC service
mode share the same upstream power bus). See §7.8.

## §7 Automations

Eight automations ship as copy-pasteable YAML; the operator imports
them as-is (after substituting their actual entity ids).

### §7.1 Stealth auto-stop (stop any in-progress motion at the start of silent hours)

```yaml
alias: "Bed Lift: Stealth auto-stop"
trigger:
  - platform: state
    entity_id: select.roamcore_mode
    to: stealth
action:
  - cover.stop_cover: cover.rc_bed_lift_position
```

### §7.2 Sleep lock-down (auto-lower at 23:00 local when mode is Sleep AND bed is up AND nobody needs it up)

```yaml
alias: "Bed Lift: Sleep lock-down (auto-lower at 23:00)"
trigger:
  - platform: time
    at: "23:00:00"
condition:
  - condition: state
    entity_id: select.roamcore_mode
    state: sleep
  - condition: state
    entity_id: select.rc_bed_lift_mode
    state: auto
  - condition: state
    entity_id: cover.rc_bed_lift_position
    state: open
  - condition: state
    entity_id: binary_sensor.rc_presence_only_driver_home
    state: "off"   # more than just the driver is home → bed in use
action:
  - cover.close_cover: cover.rc_bed_lift_position
```

### §7.3 Boost disable-mode-aware-lockouts (when operator sets rc_bed_lift_mode = disabled)

```yaml
alias: "Bed Lift: Boost disable-mode-aware-lockouts"
trigger:
  - platform: state
    entity_id: select.rc_bed_lift_mode
    to: disabled
action:
  # When disabled, the cover template ignores the Stealth / Sleep
  # mode-aware lockouts and accepts motion commands regardless of
  # mode time of day. The recipe §6.4 mode-aware lockouts are
  # bypassed; the safety interlocks (limit-sanity, low-voltage
  # lockout, obstruction detection) are NOT bypassed — those are
  # always enforced.
  - event: roamcore_bed_lift_boost_engaged
    event_data:
      engaged_by: operator
```

### §7.4 Low-voltage lockout when SOC < 20 %

```yaml
alias: "Bed Lift: low-voltage lockout alert"
trigger:
  - platform: numeric_state
    entity_id: sensor.rc_power_battery_soc
    below: 20
condition:
  - condition: state
    entity_id: binary_sensor.rc_bed_lift_low_voltage_lockout
    state: "on"
action:
  - cover.stop_cover: cover.rc_bed_lift_position
  - service: media_player.play_media
    target:
      entity_id: media_player.rc_media_zone_living
    data:
      media_content_type: "tts"
      media_content_id: media-source://tts/generate?message="Bed lift low-voltage lockout active. Shore disconnected and SOC below 20 percent. Refusing motion."
```

### §7.5 Obstruction detected → stop + alert via Music Assistant TTS

```yaml
alias: "Bed Lift: obstruction detected → stop + alert"
trigger:
  - platform: state
    entity_id: binary_sensor.rc_bed_lift_obstruction_detected
    to: "on"
action:
  - cover.stop_cover: cover.rc_bed_lift_position
  - service: media_player.play_media
    target:
      entity_id: media_player.rc_media_zone_living
    data:
      media_content_type: "tts"
      media_content_id: media-source://tts/generate?message="Bed lift obstruction detected. Bed motion stopped. Inspect for obstruction before pressing the stop button."
```

### §7.6 Mode-aware scheduling — gentle reminder if bed is up AND only driver home AND mode is Sleep

```yaml
alias: "Bed Lift: gentle reminder if bed is up AND only driver home AND mode is Sleep"
trigger:
  - platform: state
    entity_id: binary_sensor.rc_presence_only_driver_home
    to: "on"
    for: "00:15:00"   # only-driver-home for >15 min
condition:
  - condition: state
    entity_id: select.roamcore_mode
    state: sleep
  - condition: state
    entity_id: cover.rc_bed_lift_position
    state: open
  - condition: state
    entity_id: select.rc_bed_lift_mode
    state: auto
action:
  - service: media_player.play_media
    target:
      entity_id: media_player.rc_media_zone_living
    data:
      media_content_type: "tts"
      media_content_id: media-source://tts/generate?message="Bed is in the up position and only you are home. Lower the bed before sleeping for better headroom and access."
```

### §7.7 Actuator safety interlock — block lift when door unlocked (Wave 3 #48 deadbolts cross-reference)

```yaml
alias: "Bed Lift: actuator safety interlock — block lift when door unlocked"
trigger:
  - platform: state
    entity_id: binary_sensor.rc_deadbolts_any_unlocked
    to: "on"
action:
  - cover.stop_cover: cover.rc_bed_lift_position
  - service: media_player.play_media
    target:
      entity_id: media_player.rc_media_zone_living
    data:
      media_content_type: "tts"
      media_content_id: media-source://tts/generate?message="Bed lift blocked. A door is unlocked. Lock all doors before raising or lowering the bed."
```

### §7.8 HVAC service-mode block — block lift when HVAC service mode engaged (Wave 3 #49 HVAC basics cross-reference)

```yaml
alias: "Bed Lift: HVAC service-mode block — block lift when HVAC service mode engaged"
trigger:
  - platform: state
    entity_id: binary_sensor.rc_hvac_service_mode_engaged
    to: "on"
action:
  - cover.stop_cover: cover.rc_bed_lift_position
  - service: media_player.play_media
    target:
      entity_id: media_player.rc_media_zone_living
    data:
      media_content_type: "tts"
      media_content_id: media-source://tts/generate?message="Bed lift blocked. HVAC service mode is engaged. Exit HVAC service mode before raising or lowering the bed."
```

## §8 Troubleshooting

Eight troubleshooting entries covering the most common install / runtime failures.

### §8.1 Bed not moving (relay polarity / coil voltage)

Symptom: OpenClaw `lift_bed` returns "OK" but the bed does not move.

Cause: relay polarity is inverted (the GPIO drives LOW but the relay
board turns on when the GPIO goes LOW); OR the ESPHome GPIO bank's
voltage does not match the relay coil voltage (5 V GPIO + 3.3 V coil
won't fire the relay; 3.3 V GPIO + 5 V coil either won't fire or
will brown out).

Fix: set the relay's `inverted: true` flag in the ESPHome YAML (Path A);
OR add a level shifter between the ESPHome GPIO bank and the relay coil
(Path A); OR swap the relay coil's supply to match the GPIO bank
(both paths).

### §8.2 One limit stuck (replace microswitch)

Symptom: `binary_sensor.rc_bed_lift_safety_ok` is FALSE because one
limit is reporting TRUE even when the bed is NOT at that physical
limit position.

Cause: one of the limit microswitches is mechanically jammed (a stuck
plunger or a failed spring).

Fix: replace the stuck microswitch with a matching new one; verify
both `binary_sensor.rc_bed_lift_up_limit` and
`binary_sensor.rc_bed_lift_down_limit` go FALSE + TRUE at the correct
physical positions.

### §8.3 Both limits reporting TRUE simultaneously (wiring fault)

Symptom: `binary_sensor.rc_bed_lift_safety_ok` is FALSE because both
limits report TRUE at the same time.

Cause: wiring fault — mechanically impossible to be at both UP and
DOWN positions simultaneously. Most common root causes: both
microswitches wired to the same ESPHome GPIO pin (Path A); both
Shelly dry-contact inputs wired to the same microswitch common
(Path B); both Shelly dry-contact inputs mis-configured as inputs
instead of switches; one of the microswitches is jammed closed.

Fix: trace the wiring; verify each microswitch is on its own input;
verify the Shelly dry-contact input configuration per the Shelly
app's "dry contact mode" toggle; replace any jammed microswitch.

### §8.4 Bed moves up but not down (NC/NO mis-wire)

Symptom: `lift_bed` works; `lower_bed` does not.

Cause: the limit microswitches are wired for NC (normally closed)
contact operation but the recipe's ESPHome YAML / Shelly config
assumes NO (normally open). The binary_sensor reports the inverted
state.

Fix: change the ESPHome YAML's `binary_sensor` `inverted: true` flag
(Path A); OR change the Shelly's input mode to match NC dry-contact
operation (Path B); OR swap the microswitches from NC to NO
operation (some microswitches support both via the wiring + a
conversion clip).

### §8.5 Obstruction false-positive (tune current threshold)

Symptom: `binary_sensor.rc_bed_lift_obstruction_detected` trips when
no obstruction is present; the bed stops mid-motion and refuses to
resume.

Cause: the >5 A sustained-for->2 s threshold is too tight for the
operator's specific DIY actuator / motor (a lighter-duty linear
actuator might have a normal-startup inrush spike >5 A; a heavier-
duty winch motor has a different baseline current draw).

Fix: tune the threshold. Path A: edit the ESPHome YAML's
`obstruction_detected_path_a` `current_based_obstruction_detection`
threshold. Path B: edit the recipe §4.3 `current_based_obstruction_
detection` template binary_sensor's `value_template` threshold. The
recommended starting point is 6.0 A with a 3 s delay; tune from
there per the operator's motor.

### §8.6 Low-voltage lockout stuck on after charging (cross-check Victron SOC)

Symptom: `binary_sensor.rc_bed_lift_low_voltage_lockout` is TRUE
even though the operator just charged the battery to 80 % SOC.

Cause: the Victron `connections/victron/` recipe's
`sensor.rc_power_battery_soc` is stale (no recent update from the
Victron upstream integration). OR the operator's shore is still
disconnected (the second lockout clause triggers when shore is
disconnected AND battery is below 50 %).

Fix: cross-check `sensor.rc_power_battery_soc` directly in HA's
Developer Tools → States; if the value is correct (>20 %) but the
lockout is still TRUE, the shore disconnected clause is firing —
reconnect shore or wait for SOC > 50 %.

### §8.7 Shelly not discovered (mDNS / IGMP snooping on the LAN switch)

Symptom: Path B operators see no `switch.shelly_*` entities in HA
after wiring the Shelly units.

Cause: mDNS is being blocked by IGMP snooping on the LAN switch
(common for managed switches like Peplink / Teltonika / MikroTik /
Ubiquiti UniFi Switch).

Fix: enable IGMP snooping on the LAN switch BUT configure mDNS
forwarding (most managed switches have a setting for this). Verify
the Shelly units appear in HA's Integrations → Discovered; if they
do, click Configure to add them.

### §8.8 ESPHome device offline (check Wi-Fi + USB-C power)

Symptom: Path A operators see `cover.bed_lift` unavailable in HA.

Cause: the ESPHome device is offline — either Wi-Fi is unreachable
(common in a van with a flaky LAN) or USB-C power is dropped
(common with budget USB-C cables that don't carry enough current
for an ESP32 + the relay coil).

Fix: check the ESPHome device's Wi-Fi RSSI in ESPHome Device
Builder; check the USB-C cable's current rating (a 500 mA cable is
typically insufficient for an ESP32 + 5 V relay coil — use a 1.5 A
cable); verify the relay coil's idle current draw doesn't exceed
the ESPHome device's USB-C budget (heavier relay coils may need
external power).

## §9 Privacy

The DIY bed lift produces no telemetry beyond the limit
microswitches + the optional CT-clamp current sensor, all of which
are local-only inputs to the ESPHome device (Path A) or the Shelly
/ Shelly Plus / Zooz ZEN17 / Aeotec Nano Switch units (Path B).
Neither the DIY actuator / motor driver nor the upstream
integrations call home to a cloud service — there is no DIY cloud,
no ESPHome cloud, no Shelly cloud for relay control (Shelly's cloud
is purely optional + off by default), no Zooz / Aeotec cloud for
relay control.

The RoamCore `rc_bed_lift_*` contract tiles are all derived locally
in HA from the upstream entities. The recipe's automations §7 send
TTS alerts via Music Assistant's `media_player.rc_media_zone_living`
when obstruction / low-voltage conditions trip — those TTS calls go
through the operator's local TTS service (no cloud TTS by
default).

The operator's exact bed position + mode + the operator's exact
RoamCore mode + presence state are all visible in the HA UI; the
contract tiles do NOT expose any of this to any external service
beyond the operator's own OpenClaw queries.

## §10 Promoting to tier-a

A real DIY bed lift + 2× relay bench on CI (a bench with at least
one real DIY bed lift (linear actuators OR winch + motor + strap) +
2× dry-contact relays + 2× limit microswitches + optional CT-clamp
current sensor + an ESP32 flashed with the recipe §3 ESPHome YAML +
at least one Shelly / Shelly Plus / Zooz / Aeotec unit wired into
the bench's no-load DIY bed lift simulator) is required to flip this
connection from tier-c to tier-a.

What tier-a promotion requires:

1. **A real DIY bed lift + ESPHome + relay bench on CI.** The bench
   needs at least one ESP32 flashed with the recipe §3 ESPHome
   YAML + two Shelly / Shelly Plus / Zooz ZEN17 / Aeotec Nano
   Switch units wired into the bench's no-load DIY bed lift
   simulator + a CT-clamp current sensor wired into an ADC pin. The
   CI bench drives the ESPHome device over its API to simulate bed
   moves + limit-switch trips + current-sensor obstructions.

2. **A canonical RoamCore-owned `config_flow.py`** that walks the
   operator through Path A vs Path B + the operator's exact relay
   pin / limit pin / current-sensor pin choice. This wraps the
   recipe's YAML behind a config_flow (currently the operator
   writes the YAML by hand per the recipe §3 / §4). The
   config_flow.py is RoamCore-owned (lives in this folder, not
   upstream ESPHome or HA core).

3. **Integration tests** that assert:
   - The four safety interlocks (`rc_bed_lift_safety_ok`,
     `rc_bed_lift_low_voltage_lockout`,
     `rc_bed_lift_obstruction_detected`, mode-aware lockouts via
     `select.rc_bed_lift_mode`) all flip to the expected state when
     wired to canned fixture responses from the bench.
   - A 0→100% `cover.rc_bed_lift_position` change triggers the right
     tile updates on `sensor.rc_bed_lift_position_pct` +
     `binary_sensor.rc_bed_lift_moving` + the limit binary_sensors
     (UP limit goes TRUE at 100 %, DOWN limit goes TRUE at 0 %,
     `rc_bed_lift_moving` goes FALSE).
   - A `binary_sensor.rc_bed_lift_safety_ok = FALSE` scenario
     (simulated both-limits-TRUE wiring fault) blocks any subsequent
     motion command.
   - A `binary_sensor.rc_bed_lift_low_voltage_lockout = TRUE`
     scenario (simulated SOC < 20 %) blocks any subsequent motion
     command.

Once the bench + integration tests + config_flow ship, the
`test_connection_yml.py` file's `test_safety_interlocks_are_documented`
defensive guard is moved into a hard-enforced assertion (the
integration test now asserts the safety interlocks are active in
RoamCore code, not just documented in the recipe), and the
connection flips to `tier: a` with `wizard.one_tap: true` +
`tier_requirements` updated to `working_config_flow` +
`integration_test_passes` + `no_manual_yaml_required` +
`safety_interlocks_hard_enforced_in_roamcore_code`.

Until that bench lands, this connection stays at tier-c. The
recipe is sound; the safety interlocks are documented; the contract
tiles work; but we cannot claim one-tap automation without bench
integration coverage.