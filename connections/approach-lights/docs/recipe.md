# Approach lights (welcome-home exterior + underbody lighting) — tier-b recipe connection

This is the full howto for the `connections/approach-lights/` tier-b
recipe connection. It walks through wiring welcome-home exterior +
underbody + entry + soft-interior lighting on the van (Path A — Smart
switches / smart bulbs the operator already owns — Shelly 1 / Shelly
Plus 1 / Zooz ZEN17 / Aeotec Nano Switch (A1 wired switches) +
Philips Hue / LIFX / IKEA TRÅDFRI (A2 smart bulbs) + generic-Zigbee
/ generic-Z-Wave / Tuya (A3 vendor-neutral); the vendor integration
exposes `light.*` or `switch.*` entities; Path B — Generic relay +
HA template light (no smart bulb; just a 12 V underbody LED strip +
a relay-driven entry light). Shelly 1 / Shelly Plus 1 / Zooz ZEN17 /
Aeotec Nano Switch wired into the 12 V / 24 V LED driver + the HA
Shelly / Z-Wave integration auto-discovery; the HA `template:`
light wraps the relay state into virtual `light.entry` +
`light.underbody` + `light.soft_interior`; Path C — All-in-one smart
scene controller (Hue Bridge / Lutron Caséta / IKEA TRÅDFRI / Bond
Home for ceiling-fan-light combos). Single hub exposes all lights as
`light.*`; the recipe walks the operator through grouping the
approach lights into a `light.approach_scene` group entity (HA
`light:` group domain since 2022.x)), mapping the upstream entities
into the 12 `rc_lighting_*` contract tiles, layering the five
automations (first-arrival-after-dark / run-on-demand / auto-stop-
after-N-min / camera-override-on-frigate-person / stealth-mode-
suppression) + the §8 troubleshooting, and promoting the connection
to tier-a when the bench fixture lands.

## §1 What are Approach lights in RoamCore?

Approach lights (welcome-home exterior + underbody lighting) is
positioned in RoamCore as:

- A **vendor-neutral** light/switch contract. The contract talks to
  whatever upstream vendor's light/switch integration the operator
  already runs (Path A — smart switches / smart bulbs the operator
  already owns — Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano
  Switch (A1 wired switches) + Philips Hue / LIFX / IKEA TRÅDFRI
  (A2 smart bulbs) + generic-Zigbee / generic-Z-Wave / Tuya (A3
  vendor-neutral); Path B — generic relay + HA template light —
  Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano Switch wired
  into a 12 V / 24 V LED driver for the underbody strip + the
  entry porch light, with the HA `template:` light wrapping the
  relay state into virtual `light.entry` + `light.underbody` +
  `light.soft_interior`; Path C — all-in-one smart scene controller
  — Hue Bridge / Lutron Caséta / IKEA TRÅDFRI / Bond Home hub with
  all approach lights grouped into a `light.approach_scene` group
  entity (HA `light:` group domain since 2022.x)), not to any
  specific vendor's library.

- A **three-way gate** before the approach scene fires. The gate is:
  is it dark (`binary_sensor.rc_lighting_dark_outside` is TRUE,
  driven by `sun.sun` OR `sensor.rc_weather_light_lux`) + is
  someone arriving (`binary_sensor.rc_presence_all_away` from the
  bluetooth-wifi-presence Wave 3 #42 connection transitions TRUE
  → FALSE) + is mode != stealth (`select.rc_mode` from the mode/
  automation-builder Wave 3 connection is not `stealth`). All three
  must hold simultaneously for the first-arrival-after-dark
  automation to fire the approach scene. This is the universal
  small-comfort van automation: open the door after dark, the
  underbody + entry + soft-interior lights come on for a
  configurable duration (default 2 min) so the operator can see
  where they're stepping and feel like the van is welcoming them
  home.

- A **single "is the approach scene active?" aggregate** that
  surfaces underbody + entry + soft-interior state + the dark-
  outside gate + the presence trigger + the timer countdown into
  one dashboard tile:
  `binary_sensor.rc_lighting_approach_active` is TRUE while the
  approach scene is currently running (the operator-triggered
  automation fired, the N-minute countdown is in progress, and
  the operator has not manually cancelled). The
  `binary_sensor.rc_lighting_approach_available` tile is the meta-
  gate (TRUE when the gates line up — it's dark + presence is
  detectable — so the scene *can* fire, independent of whether it
  IS firing right now). The three per-zone state binary_sensors
  (`binary_sensor.rc_lighting_underbody_state` +
  `binary_sensor.rc_lighting_entry_state` +
  `binary_sensor.rc_lighting_soft_interior_state`) are the per-
  zone state mirrors.

- A **camera-override soft-deterrent** cross-referencing Frigate
  Wave 3 #35. When a Frigate `person` detection fires in the
  entry zone after dark, the
  `binary_sensor.rc_lighting_camera_override` tile goes TRUE for
  30 seconds (a brighter "someone's at the door" cue than the
  gentle approach scene; the brighter cue is also a soft
  deterrent). Cross-references the Frigate
  `connections/frigate/` connection's
  `binary_sensor.<camera>_<zone>_person_detected` entity (the
  operator wires this via HA `template:` binary_sensor if Frigate
  is installed; the camera-override contract tile stays FALSE if
  Frigate is not installed — the rest of the approach-lights
  system continues to work without Frigate).

- A **mode-aware** system. The
  `select.rc_lighting_approach_mode` tile controls the approach
  monitoring mode: `auto` (full automation — fires on first
  arrival after dark + auto-stops after N min), `dark_only` (only
  fires when `binary_sensor.rc_lighting_dark_outside` is TRUE
  via `sensor.rc_weather_light_lux`; useful for urban operators
  with bright streetlight pollution), `stealth_only` (only fires
  when `select.rc_mode` from the mode/automation-builder
  connection is NOT `stealth` — adds a second gate on top of the
  mode-aware suppression), `disabled` (no monitoring at all —
  reserved for when the operator has intentionally removed all
  approach lights for service work). The mode-aware lockouts
  (Stealth / Sleep / Boost) layer on top: Stealth silent hours
  auto-mute the approach scene (the §7.5 stealth-mode-suppression
  automation); Sleep mode additionally drops the operator-tunable
  approach duration threshold by 10 %; Boost disables ALL the
  mode-aware lockouts for service work / pre-trip packing.

- A **12-tile vendor-neutral contract layer**. The
  `dashboard.tiles` lists exactly 12 contract tiles (4
  binary_sensor active / available / per-zone state / camera-
  override (5 binary_sensors total: approach_active +
  approach_available + underbody_state + entry_state +
  soft_interior_state + dark_outside + camera_override = 7
  binary_sensors) + 2 sensor tiles (approach_minutes_remaining +
  last_approach_trigger_minutes_ago) + 1 select tile
  (approach_mode: auto / dark_only / stealth_only / disabled) +
  1 number configuration tile (approach_duration_min) + 1 button
  tile (run_approach_now) = 12 contract tiles). All 12 tiles are
  vendor-neutral `rc_lighting_*` ids per
  `docs/reference/rc-entity-naming.md` §lighting subsystem (NEW —
  added by this slice in `docs/reference/rc-entity-naming.md`,
  mirroring how `media` was added by Music Assistant Wave 3 #41
  + how `presence` was added by bluetooth-wifi-presence Wave 3
  #42 + how `water` was added by water-tanks Wave 3 #50 + how
  `bed_lift` was added by happijac Wave 3 #43 + how `hvac` was
  added by heated-floors Wave 3 #44 + how `safety` was added by
  smoke-co-gas-sensors Wave 3 #45).

## §2 Prerequisites

Path A — Smart switches / smart bulbs (recommended for operators with
existing smart lighting):

- At least one controllable approach-zone light installed (an
  underbody LED strip OR an entry porch light OR a soft-interior
  entry light).
- The operator's choice of upstream light/switch integrated into
  HA. Common choices:
  - **A1 — Wired switches**: Shelly 1 (single-channel relay, 12 V
    or 24 V power, dry contacts; HA core `shelly` integration, GUI
    flow since 2022.x); Shelly Plus 1 (newer version with
    Bluetooth + improved Wi-Fi; HA core `shelly` integration); Zooz
    ZEN17 (Z-Wave relay, 12 V or 24 V power; HA `zwave_js`
    integration); Aeotec Nano Switch (Z-Wave relay, 12 V or 24 V
    power; HA `zwave_js` integration).
  - **A2 — Smart bulbs**: Philips Hue (HA core `hue` integration,
    GUI flow since 2022.x — Hue Bridge required for the cloud
    discovery but the daily-operation path is local); LIFX (HA
    core `lifx` integration, GUI flow since 2022.x — local
    network, no cloud required); IKEA TRÅDFRI (HA core `tradfri`
    integration, GUI flow since 2022.x — TRADFRI gateway
    required).
  - **A3 — Vendor-neutral**: generic-Zigbee (HA core `zha`
    integration, GUI flow since 2022.x — Zigbee dongle required);
    generic-Z-Wave (HA `zwave_js` integration, GUI flow since
    2022.x — Z-Wave dongle required); Tuya (HA core `tuya`
    integration, GUI flow since 2022.x — Tuya cloud auth
    required for the operator's first-time setup; subsequent runs
    are local).
- The HA `template:` integration (HA core, GUI flow since
  2022.x) — for the contract tile synthesis (mapping the vendor
  `light.*` / `switch.*` entities into the 12 `rc_lighting_*`
  contract tiles).

Path B — Generic relay + HA template light (no smart bulb; just a
12 V underbody LED strip + a relay-driven entry light):

- One relay (one per zone). Common choices: Shelly 1 (single-
  channel relay, 12 V or 24 V power, dry contacts; HA core
  `shelly` integration, GUI flow since 2022.x); Shelly Plus 1
  (newer version with Bluetooth + improved Wi-Fi); Zooz ZEN17
  (Z-Wave relay, 12 V or 24 V power; HA `zwave_js` integration);
  Aeotec Nano Switch (Z-Wave relay, 12 V or 24 V power; HA
  `zwave_js` integration). The relay contacts are wired into the
  12 V / 24 V LED driver.
- One 12 V / 24 V LED driver per zone (a constant-voltage LED
  driver matched to the LED strip's voltage + current rating —
  common choices: a 12 V / 5 A Mean Well HLG driver for a 5 m
  underbody strip pulling ~3 A; a 24 V / 2 A driver for the
  entry porch light pulling ~1 A).
- One LED strip per zone (a 12 V / 24 V constant-voltage LED
  strip — common choices: a 5050 SMD white-warm LED strip for the
  underbody; a 2835 SMD white LED strip for the entry porch
  light; a 2216 SMD warm-white LED strip for the soft interior
  entry lighting).
- The HA `template:` integration (HA core, GUI flow since
  2022.x) — for the contract tile synthesis (mapping the relay
  state to virtual `light.entry` + `light.underbody` +
  `light.soft_interior` template lights).

Path C — All-in-one smart scene controller (Hue Bridge / Lutron
Caséta / IKEA TRÅDFRI / Bond Home for ceiling-fan-light combos):

- One hub. Common choices: Hue Bridge (HA core `hue` integration,
  GUI flow since 2022.x); Lutron Caséta Smart Bridge (HA `lutron`
  integration, GUI flow since 2022.x); IKEA TRÅDFRI gateway (HA
  core `tradfri` integration, GUI flow since 2022.x); Bond Home
  hub (HA `bond` integration, GUI flow since 2022.x).
- At least one compatible smart bulb per zone (a Hue White /
  Hue White and Color / Lutron Caséta in-wall dimmer / IKEA
  TRÅDFRI bulb / Bond-controlled ceiling-fan light).
- The HA `light:` group domain (HA core, GUI flow since 2022.x)
  — for the `light.approach_scene` group entity.

Common to all three paths:

- The HA `template:` integration (HA core, GUI flow since
  2022.x) — for the contract tile synthesis + the derived
  aggregates (approach_active + approach_available + per-zone
  state + camera_override + dark_outside + approach_minutes_
  remaining + last_approach_trigger_minutes_ago).
- The HA `timer:` integration (HA core, GUI flow since 2022.x)
  — for the approach N-minutes countdown timer + the camera-
  override 30-second auto-reset timer.
- The HA `input_boolean:` integration (HA core, GUI flow since
  2022.x) — for the §7.1 / §7.3 automation input booleans.
- The HA `input_select:` integration (HA core, GUI flow since
  2022.x) — for the operator-tunable
  `select.rc_lighting_approach_mode` tile.
- The HA `input_number:` integration (HA core, GUI flow since
  2022.x) — for the operator-tunable
  `number.rc_lighting_approach_duration_min` tile (default 2;
  range 1–10).
- The HA `button:` integration (HA core, GUI flow since
  2023.x) — for the `button.rc_lighting_run_approach_now`
  button.
- The HA `input_datetime:` integration (HA core, GUI flow since
  2022.x) — for the `last_approach_trigger_minutes_ago` derived
  metric (the timestamp is stored in `input_datetime.rc_lighting_
  last_approach_trigger_ts` and the minutes-ago is derived via HA
  `template:` sensor).
- The bluetooth-wifi-presence Wave 3 #42 connection installed
  and configured — for the §7.1 first-arrival-after-dark trigger
  `binary_sensor.rc_presence_all_away` (the approach scene fires
  on `rc_presence_all_away` transitioning TRUE → FALSE — the
  "nobody → someone home" edge) + the `binary_sensor.rc_presence_
  anyone_home` cross-check (the scene only fires when someone is
  actually home, not when the phone just briefly pinged the LAN).
- The dark-outside signal wired via `sun.sun` (HA core, GUI flow
  since 2022.x — the simpler default) OR
  `sensor.rc_weather_light_lux` (from the time/weather contract
  in `homeassistant/packages/roamcore_weather_time.yaml` — the
  more accurate choice for urban environments with bright
  streetlight pollution). The recipe documents the choice; the
  default is `sun.sun` for zero-config setups.
- The mode/automation-builder Wave 3 connection installed and
  configured — for the §7.5 stealth-mode-suppression automation
  (`select.rc_mode` from the mode/automation-builder connection
  must be wired).
- The Frigate Wave 3 #35 connection installed and configured
  (OPTIONAL — only required for the §7.4 camera-override-on-
  frigate-person automation) — for the
  `binary_sensor.<camera>_<zone>_person_detected` entity (the
  operator wires this via HA `template:` binary_sensor if Frigate
  is installed; the camera-override contract tile stays FALSE if
  Frigate is not installed). Skip this prerequisite if Frigate is
  not installed — the rest of the approach-lights system
  continues to work without Frigate.

## §3 Path A — Smart switches / smart bulbs (recommended for operators with existing smart lighting)

Path A splits into three sub-paths (A1 wired switches, A2 smart
bulbs, A3 vendor-neutral). Each shows entity_id surfacing + the
`light.turn_on` service call + a `template:` binary_sensor that
aggregates the vendor `light.*` entities into the `rc_lighting_*`
contract tiles.

### §3.1 Path A1 — Wired switches (Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano Switch)

Walk through the Shelly 1 example in detail. A Shelly 1 wired into
the entry porch light + a Shelly 1 wired into the underbody LED
strip + the HA `shelly` integration auto-discovery:

1. Power the Shelly via the van's 12 V distribution. Shelly 1:
   12 V DC (or 24 V DC for the 24 V variant) on the `+12V` /
   `GND` (or `+24V` / `GND`) terminals.
2. Wire the Shelly's switched output to the light. Entry porch
   light: the Shelly's COM terminal connects to the light's hot
   wire; the Shelly's NO (normally-open) terminal connects to
   the light's switched-hot wire; the light's neutral wire
   connects directly to the van's 12 V / 24 V neutral bus.
   Underbody LED strip: same pattern, but the Shelly's switched
   output drives the LED driver's input + terminal (the LED
   driver's - terminal connects to the van's 12 V / 24 V
   neutral bus).
3. Configure the Shelly via its web UI (mDNS auto-discovery on
   the LAN for Shelly). The `shelly` integration in HA exposes
   `switch.shelly_entry_porch` (or similar) +
   `switch.shelly_underbody` (or similar).
4. Wire the upstream entities into the contract tiles via HA
   core `template:`. The template switches wrap the Shelly's
   `switch.*` entities so they look like `light.*` entities to
   the rest of the system (the upstream `light.turn_on` service
   call works on `template:` switches via HA's
   `homeassistant.turn_on` service with a target):

```yaml
template:
  - switch:
      - name: "RC Lighting Entry State"
        unique_id: rc_lighting_entry_state
        turn_on:
          - switch.turn_on: switch.shelly_entry_porch
        turn_off:
          - switch.turn_off: switch.shelly_entry_porch

      - name: "RC Lighting Underbody State"
        unique_id: rc_lighting_underbody_state
        turn_on:
          - switch.turn_on: switch.shelly_underbody
        turn_off:
          - switch.turn_off: switch.shelly_underbody

      - name: "RC Lighting Soft Interior State"
        unique_id: rc_lighting_soft_interior_state
        turn_on:
          - switch.turn_on: switch.shelly_soft_interior
        turn_off:
          - switch.turn_off: switch.shelly_soft_interior
```

(The dashboard contract tile
`binary_sensor.rc_lighting_entry_state` mirrors the state of
`switch.rc_lighting_entry_state` via a separate `template:`
binary_sensor; the same pattern applies for `underbody_state` +
`soft_interior_state`).

The vendor's `light.turn_on` service call to the approach scene:

```yaml
service: light.turn_on
target:
  entity_id:
    - switch.rc_lighting_entry_state
    - switch.rc_lighting_underbody_state
    - switch.rc_lighting_soft_interior_state
```

### §3.2 Path A2 — Smart bulbs (Philips Hue / LIFX / IKEA TRÅDFRI)

Walk through the Hue example in detail. A Hue Bridge with three
Hue White bulbs (one each for entry porch, underbody, soft
interior) + the HA `hue` integration:

1. Set up the Hue Bridge via the Hue app (cloud auth required
   for the operator's first-time setup; subsequent runs are
   local).
2. Pair each Hue bulb with the Hue Bridge via the Hue app.
3. Configure the `hue` integration in HA (GUI flow since
   2022.x). The integration auto-discovers the Hue Bridge on
   the LAN via mDNS + exposes each bulb as a `light.*` entity:
   `light.hue_entry_porch` + `light.hue_underbody` +
   `light.hue_soft_interior`.
4. Group the three bulbs into a `light.approach_scene` group
   entity via the HA core `light:` group domain (GUI flow since
   2022.x; the operator creates the group in the Settings →
   Devices & Services → Helpers → Create Group → light group UI,
   and selects the three bulbs as members).

The HA core `template:` binary_sensor aggregating the vendor
`light.*` entities into the contract tile:

```yaml
template:
  - binary_sensor:
      - name: "RC Lighting Underbody State"
        unique_id: rc_lighting_underbody_state
        state: "{{ is_state('light.hue_underbody', 'on') }}"

      - name: "RC Lighting Entry State"
        unique_id: rc_lighting_entry_state
        state: "{{ is_state('light.hue_entry_porch', 'on') }}"

      - name: "RC Lighting Soft Interior State"
        unique_id: rc_lighting_soft_interior_state
        state: "{{ is_state('light.hue_soft_interior', 'on') }}"
```

The vendor's `light.turn_on` service call to the approach scene:

```yaml
service: light.turn_on
target:
  entity_id: light.approach_scene
data:
  brightness_pct: 60
```

### §3.3 Path A3 — Vendor-neutral (generic-Zigbee / generic-Z-Wave / Tuya)

Walk through the generic-Zigbee (ZHA) example in detail. A ZHA-
compatible Zigbee relay (a SONOFF ZBMINI or a Nous A1Z or similar)
wired into the entry porch light + an IKEA TRÅDFRI bulb paired
via ZHA for the underbody:

1. Plug the Zigbee dongle into the HA host (a SONOFF Zigbee 3.0
   USB Dongle Plus-ZBDongle-E or a Texas Instruments CC2652
   stick).
2. Configure the `zha` integration in HA (GUI flow since
   2022.x). The integration auto-discovers the Zigbee dongle
   on the USB bus.
3. Pair the Zigbee relay + the IKEA TRÅDFRI bulb via ZHA's
   "Add device" flow (the operator triggers pairing on the
   device + ZHA discovers it within 30 seconds).
4. The ZHA integration exposes the devices as `light.*` or
   `switch.*` entities: `switch.zha_entry_relay` +
   `light.zha_underbody_bulb`.
5. The template layer is identical to Path A1 + Path A2 above
   (the template wraps the `switch.*` / `light.*` entities into
   the `rc_lighting_*` contract tiles).

The vendor-neutrality comes from the fact that the recipe never
hardcodes a specific vendor's library — the operator wires
whatever Zigbee / Z-Wave / Tuya device they happen to own, and
the template layer maps it into the contract layer.

## §4 Path B — Generic relay + HA template light (no smart bulb; 12 V underbody LED strip + relay-driven entry light)

Walk through the Shelly 1 example in detail. A Shelly 1 wired
into a 12 V LED driver + a 12 V LED strip for the underbody +
the same pattern for the entry porch light:

1. Power the Shelly via the van's 12 V distribution. Shelly 1:
   12 V DC on the `+12V` / `GND` terminals.
2. Wire the Shelly's switched output to the LED driver's input.
   Underbody LED strip: the Shelly's COM terminal connects to
   the LED driver's + terminal; the Shelly's NO (normally-open)
   terminal connects to the LED driver's switched-+ terminal;
   the LED driver's - terminal connects directly to the van's
   12 V neutral bus. The LED strip's + and - wires connect to
   the LED driver's output + and - terminals.
3. Configure the Shelly via its web UI (mDNS auto-discovery on
   the LAN). The `shelly` integration in HA exposes
   `switch.shelly_underbody_relay` (or similar).
4. Wire the HA `template:` light wrapping the relay state into
   a virtual `light.underbody` template light (the template
   `light:` integration exposes the relay as a `light.*` entity
   that the rest of the system can call `light.turn_on` /
   `light.turn_off` on):

```yaml
template:
  - light:
      - name: "RC Lighting Underbody"
        unique_id: rc_lighting_underbody
        turn_on:
          - switch.turn_on: switch.shelly_underbody_relay
        turn_off:
          - switch.turn_off: switch.shelly_underbody_relay

      - name: "RC Lighting Entry"
        unique_id: rc_lighting_entry
        turn_on:
          - switch.turn_on: switch.shelly_entry_relay
        turn_off:
          - switch.turn_off: switch.shelly_entry_relay

      - name: "RC Lighting Soft Interior"
        unique_id: rc_lighting_soft_interior
        turn_on:
          - switch.turn_on: switch.shelly_soft_interior_relay
        turn_off:
          - switch.turn_off: switch.shelly_soft_interior_relay
```

(The `template:` light wraps the Shelly's `switch.*` entities
into virtual `light.*` entities; the same pattern applies for
`light.entry` + `light.soft_interior`. The vendor's
`light.turn_on` service call then works on the template lights
directly:)

```yaml
service: light.turn_on
target:
  entity_id:
    - light.rc_lighting_underbody
    - light.rc_lighting_entry
    - light.rc_lighting_soft_interior
```

The derived contract tiles (`binary_sensor.rc_lighting_underbody_
state` + `binary_sensor.rc_lighting_entry_state` +
`binary_sensor.rc_lighting_soft_interior_state`) are
`template:` binary_sensors that mirror the template light state:

```yaml
template:
  - binary_sensor:
      - name: "RC Lighting Underbody State"
        unique_id: rc_lighting_underbody_state
        state: "{{ is_state('light.rc_lighting_underbody', 'on') }}"

      - name: "RC Lighting Entry State"
        unique_id: rc_lighting_entry_state
        state: "{{ is_state('light.rc_lighting_entry', 'on') }}"

      - name: "RC Lighting Soft Interior State"
        unique_id: rc_lighting_soft_interior_state
        state: "{{ is_state('light.rc_lighting_soft_interior', 'on') }}"
```

## §5 Path C — All-in-one smart scene controller (Hue Bridge / Lutron Caséta / IKEA TRÅDFRI / Bond Home)

Walk through the Hue Bridge example in detail. A Hue Bridge with
three Hue White bulbs (one each for entry porch, underbody, soft
interior) + the HA `hue` integration + the HA `light:` group
domain:

1. Set up the Hue Bridge via the Hue app (cloud auth required
   for the operator's first-time setup; subsequent runs are
   local).
2. Pair each Hue bulb with the Hue Bridge via the Hue app.
3. Configure the `hue` integration in HA (GUI flow since
   2022.x). The integration auto-discovers the Hue Bridge on
   the LAN via mDNS + exposes each bulb as a `light.*` entity:
   `light.hue_entry_porch` + `light.hue_underbody` +
   `light.hue_soft_interior`.
4. Group the three bulbs into a `light.approach_scene` group
   entity via the HA core `light:` group domain (GUI flow since
   2022.x; the operator creates the group in the Settings →
   Devices & Services → Helpers → Create Group → light group UI,
   and selects the three bulbs as members). The group is
   exposed as a `light.*` entity: `light.approach_scene`.
5. Wire the upstream entity into the contract tile via a
   `template:` binary_sensor mirroring the scene state:

```yaml
template:
  - binary_sensor:
      - name: "RC Lighting Approach Active"
        unique_id: rc_lighting_approach_active
        state: "{{ is_state('light.approach_scene', 'on') }}"

      - name: "RC Lighting Underbody State"
        unique_id: rc_lighting_underbody_state
        state: "{{ is_state('light.hue_underbody', 'on') }}"

      - name: "RC Lighting Entry State"
        unique_id: rc_lighting_entry_state
        state: "{{ is_state('light.hue_entry_porch', 'on') }}"

      - name: "RC Lighting Soft Interior State"
        unique_id: rc_lighting_soft_interior_state
        state: "{{ is_state('light.hue_soft_interior', 'on') }}"
```

The vendor's `light.turn_on` service call to the approach scene:

```yaml
service: light.turn_on
target:
  entity_id: light.approach_scene
data:
  brightness_pct: 60
```

(The Path C pattern is identical to Path A2 — the Hue Bridge is
the hub; the only difference is that Path A2 covers the
non-hubbed bulb case + Path C covers the hubbed case where all
lights come from the same hub).

## §6 RoamCore contract entities

The 12 `rc_lighting_*` contract tiles + how the upstream light/
switch template exposes them + translation helpers needed for the
derived metrics like `approach_minutes_remaining` +
`last_approach_trigger_minutes_ago` + `dark_outside` +
`camera_override`:

- `binary_sensor.rc_lighting_approach_active` — TRUE while the
  approach scene is currently running (the operator-triggered
  automation fired + the N-minute countdown is in progress + the
  operator has not manually cancelled). Path A / B / C: derived
  via HA `template:` binary_sensor that ORs the upstream
  `light.<approach_scene>` state OR the three per-zone template
  light states (any of them ON means the approach scene is
  active). Auto-resets to FALSE when the §7.3 auto-stop-after-N-
  min automation fires.
- `binary_sensor.rc_lighting_approach_available` — meta-gate
  (TRUE when the gates line up — it's dark + presence is
  detectable — so the scene *can* fire, independent of whether
  it IS firing right now). Path A / B / C: derived via HA
  `template:` binary_sensor that ANDs
  `binary_sensor.rc_lighting_dark_outside` (it's dark) AND
  `binary_sensor.rc_presence_anyone_home` (presence detection
  is wired and reporting someone home) AND
  `select.rc_lighting_approach_mode != disabled` (the operator
  has not disabled the approach system).
- `binary_sensor.rc_lighting_underbody_state` — underbody light
  state mirror (TRUE when the underbody light is currently ON).
  Path A / B / C: derived via HA `template:` binary_sensor that
  mirrors the upstream `light.<underbody>` or
  `switch.<underbody_relay>` state.
- `binary_sensor.rc_lighting_entry_state` — entry porch light
  state mirror (TRUE when the entry porch light is currently
  ON). Path A / B / C: same pattern as `underbody_state`.
- `binary_sensor.rc_lighting_soft_interior_state` — soft
  interior entry light state mirror (TRUE when the soft
  interior light is currently ON). Path A / B / C: same pattern
  as `underbody_state`.
- `sensor.rc_lighting_approach_minutes_remaining` — minutes
  remaining on the N-minute approach countdown (default 2; the
  tile reports 0 when no approach scene is active, reports the
  remaining minutes while the countdown is in progress, reports
  the configured duration when the countdown is restarted by the
  §7.2 run-on-demand button press). Path A / B / C: derived via
  HA `template:` sensor that reads the HA `timer:` integration's
  remaining-time attribute.
- `sensor.rc_lighting_last_approach_trigger_minutes_ago` —
  minutes since the last approach scene trigger (the dashboard
  "last triggered 3 h ago" badge). Path A / B / C: derived via
  HA `template:` sensor that reads the
  `input_datetime.rc_lighting_last_approach_trigger_ts` helper
  timestamp + computes the minutes-since via `now() -
  input_datetime.rc_lighting_last_approach_trigger_ts`.
- `binary_sensor.rc_lighting_dark_outside` — TRUE when it's
  dark outside (drives the §7.1 first-arrival-after-dark gate).
  Path A / B / C: derived via HA `template:` binary_sensor that
  ORs `sun.sun == below_horizon` (HA core `sun` integration,
  GUI flow since 2022.x — the simpler default) OR
  `sensor.rc_weather_light_lux < 50` (from the time/weather
  contract in `homeassistant/packages/roamcore_weather_time.yaml`
  — the more accurate choice for urban environments with bright
  streetlight pollution).
- `select.rc_lighting_approach_mode` — operator-tunable mode
  (`auto` / `dark_only` / `stealth_only` / `disabled`; default
  `auto`). `auto` enables full automation; `dark_only` requires
  `sensor.rc_weather_light_lux < 50` in addition to
  `sun.sun == below_horizon`; `stealth_only` requires
  `select.rc_mode != stealth` (the §7.5 stealth-mode-suppression
  automation is the second gate); `disabled` stops all approach
  monitoring (reserved for service work).
- `number.rc_lighting_approach_duration_min` — operator-tunable
  N-minute approach countdown duration (default 2; configurable
  1–10 minutes via HA `input_number:` integration, GUI flow
  since 2022.x).
- `button.rc_lighting_run_approach_now` — operator-triggerable
  run-approach-now button (HA `button:` integration, GUI flow
  since 2023.x). Pressing the button fires the §7.2 run-on-
  demand automation (same as the §7.1 first-arrival-after-dark
  trigger — useful for showing a friend where the van is + for
  testing the wiring without waiting for first arrival).
- `binary_sensor.rc_lighting_camera_override` — TRUE for 30
  seconds when a Frigate `person` detection fires in the entry
  zone after dark (a brighter "someone's at the door" cue than
  the gentle approach scene; the brighter cue is also a soft
  deterrent). Path A / B / C: derived via HA `template:`
  binary_sensor that ANDs the Frigate
  `binary_sensor.<camera>_<zone>_person_detected` (cross-
  reference Frigate Wave 3 #35) AND
  `binary_sensor.rc_lighting_dark_outside` (only fire after
  dark). Auto-resets to FALSE via a HA `timer:` integration
  30-second countdown.

## §7 Automations

Five MANDATORY automations (MANDATORY before first use; operator MUST wire each one before
first use):

1. **First-arrival-after-dark** — when
   `binary_sensor.rc_presence_all_away` (from the bluetooth-wifi-
   presence Wave 3 #42 connection) transitions TRUE → FALSE (the
   "nobody → someone home" edge — the operator just arrived home)
   AND `binary_sensor.rc_lighting_dark_outside` is TRUE (it's
   dark outside) AND `select.rc_lighting_approach_mode` !=
   `disabled` (the operator has not disabled the approach system)
   AND `select.rc_mode` (from the mode/automation-builder
   connection) != `stealth` (Stealth mode suppression per
   §7.5), fire the approach scene:

```yaml
automation:
  - alias: "RC Lighting: Approach scene on first arrival after dark"
    trigger:
      - platform: state
        entity_id: binary_sensor.rc_presence_all_away
        from: "on"
        to: "off"
    condition:
      - condition: state
        entity_id: binary_sensor.rc_lighting_dark_outside
        state: "on"
      - condition: not
        conditions:
          - condition: state
            entity_id: select.rc_lighting_approach_mode
            state: "disabled"
      - condition: not
        conditions:
          - condition: state
            entity_id: select.rc_mode
            state: "stealth"
    action:
      - service: input_datetime.set_datetime
        target:
          entity_id: input_datetime.rc_lighting_last_approach_trigger_ts
        data:
          datetime: "{{ now() }}"
      - service: light.turn_on
        target:
          entity_id:
            - switch.rc_lighting_entry_state
            - switch.rc_lighting_underbody_state
            - switch.rc_lighting_soft_interior_state
        data:
          brightness_pct: 60
      - service: timer.start
        target:
          entity_id: timer.rc_lighting_approach_duration
        data:
          duration: "{{ states('number.rc_lighting_approach_duration_min') | int(2) * 60 }}"
```

2. **Run-on-demand** — when
   `button.rc_lighting_run_approach_now` is pressed (HA
   `button:` integration, GUI flow since 2023.x), fire the same
   approach scene + the same N-minute countdown (useful for
   showing a friend where the van is + for testing the wiring
   without waiting for first arrival):

```yaml
automation:
  - alias: "RC Lighting: Run approach scene on demand"
    trigger:
      - platform: state
        entity_id: button.rc_lighting_run_approach_now
    action:
      - service: input_datetime.set_datetime
        target:
          entity_id: input_datetime.rc_lighting_last_approach_trigger_ts
        data:
          datetime: "{{ now() }}"
      - service: light.turn_on
        target:
          entity_id:
            - switch.rc_lighting_entry_state
            - switch.rc_lighting_underbody_state
            - switch.rc_lighting_soft_interior_state
        data:
          brightness_pct: 60
      - service: timer.start
        target:
          entity_id: timer.rc_lighting_approach_duration
        data:
          duration: "{{ states('number.rc_lighting_approach_duration_min') | int(2) * 60 }}"
```

3. **Auto-stop-after-N-min** — when the HA `timer:` N-minute
   countdown fires (the countdown was started by the §7.1
   first-arrival-after-dark automation OR the §7.2 run-on-demand
   button press), fire `light.turn_off` for each of the approach
   lights + update the timestamp:

```yaml
automation:
  - alias: "RC Lighting: Auto-stop approach scene after N minutes"
    trigger:
      - platform: event
        event_type: timer.finished
        event_data:
          entity_id: timer.rc_lighting_approach_duration
    action:
      - service: light.turn_off
        target:
          entity_id:
            - switch.rc_lighting_entry_state
            - switch.rc_lighting_underbody_state
            - switch.rc_lighting_soft_interior_state
```

4. **Camera-override-on-frigate-person** — when a Frigate
   `person` detection fires in the entry zone (cross-references
   Frigate Wave 3 #35) AND
   `binary_sensor.rc_lighting_dark_outside` is TRUE (only fire
   after dark — a daytime `person` detection is normal traffic),
   fire `binary_sensor.rc_lighting_camera_override` TRUE for
   30 seconds + set the underbody lights to full brightness
   (the operator wants a brighter "someone's at the door" cue
   than the gentle approach scene; the brighter cue is also a
   soft deterrent):

```yaml
automation:
  - alias: "RC Lighting: Camera-override bright cue on Frigate person"
    trigger:
      - platform: state
        entity_id: binary_sensor.<camera>_<zone>_person_detected
        to: "on"
    condition:
      - condition: state
        entity_id: binary_sensor.rc_lighting_dark_outside
        state: "on"
    action:
      - service: light.turn_on
        target:
          entity_id:
            - switch.rc_lighting_underbody_state
            - switch.rc_lighting_entry_state
        data:
          brightness_pct: 100
      - service: timer.start
        target:
          entity_id: timer.rc_lighting_camera_override
        data:
          duration: 30
      - service: notify.notify
        data:
          title: "Camera override: person at entry"
          message: "Frigate detected a person in the entry zone; approach lights at 100% for 30 seconds."
```

(The Frigate `binary_sensor.<camera>_<zone>_person_detected`
entity is wired via HA `template:` binary_sensor if Frigate is
installed; the camera-override contract tile stays FALSE if
Frigate is not installed — the rest of the approach-lights
system continues to work without Frigate).

5. **Stealth-mode-suppression** — when
   `select.rc_mode` (from the mode/automation-builder
   connection) == `stealth`, suppress ALL approach lighting
   (don't fire the §7.1 first-arrival-after-dark automation). At
   a quiet campground after dark, the gentle approach lights
   can be enough to make neighbors think someone is up + wanting
   to chat — Stealth mode mutes the approach scene entirely so
   the operator can come home late without waking the campground.
   The camera-override cross-reference still fires (the camera-
   override is a safety-relevant deterrent; Stealth mode does
   NOT mute safety-relevant cues):

```yaml
automation:
  - alias: "RC Lighting: Stealth mode suppresses approach scene"
    trigger:
      - platform: state
        entity_id: select.rc_mode
        to: "stealth"
    action:
      - service: light.turn_off
        target:
          entity_id:
            - switch.rc_lighting_entry_state
            - switch.rc_lighting_underbody_state
            - switch.rc_lighting_soft_interior_state
      - service: timer.cancel
        target:
          entity_id: timer.rc_lighting_approach_duration
```

(The suppression is enforced via the §7.1 first-arrival-after-
dark automation's `condition: select.rc_mode != stealth` check
— the automation simply does NOT fire while Stealth mode is
active. The automation above is the cleanup path: when Stealth
mode is engaged, kill any in-progress approach scene).

The full automation YAML for each is in the recipe
`homeassistant/automations/rc_lighting_*.yaml` files (operator
wires these manually until tier-a promotion lands).

## §8 Troubleshooting

Six troubleshooting entries:

1. **Approach scene never fires** — presence detection not wired
   / dark sensor not wired / Stealth mode suppressing /
   `binary_sensor.rc_lighting_approach_available` is FALSE. The
   §7.1 first-arrival-after-dark automation has FOUR conditions
   that must ALL hold simultaneously: (a)
   `binary_sensor.rc_presence_all_away` transitions TRUE →
   FALSE (the bluetooth-wifi-presence Wave 3 #42 connection
   must be installed + the presence detection must be
   reporting); (b) `binary_sensor.rc_lighting_dark_outside` is
   TRUE (the dark-outside signal must be wired via `sun.sun` OR
   `sensor.rc_weather_light_lux`); (c)
   `select.rc_lighting_approach_mode != disabled`; (d)
   `select.rc_mode != stealth` (the mode/automation-builder
   recipe must be wired). Solution: check each of the four
   conditions in the dashboard — if any is FALSE, the
   automation will not fire. The
   `binary_sensor.rc_lighting_approach_available` tile is a
   meta-gate that surfaces conditions (a) + (b) + (c) — if
   it's FALSE, one of those three is the issue.

2. **Approach scene stays on forever** — the
   `number.rc_lighting_approach_duration_min` is set too high
   OR the §7.3 auto-stop-after-N-min automation is missing. The
   HA `timer:` integration fires after the configured minutes;
   if the operator has set `number.rc_lighting_approach_duration_
   min` to 10 min (the maximum), the approach scene stays on
   for 10 minutes after triggering. If the §7.3 automation is
   not wired, the timer fires but nothing happens — the lights
   stay on until the operator manually turns them off.
   Solution: check the `number.rc_lighting_approach_duration_
   min` value (default 2); check that the §7.3 automation is
   wired + the timer entity ID matches; check that the timer
   is firing (look for the `timer.finished` event in the HA
   developer tools).

3. **Only some lights come on** — vendor group not configured /
   Path A vs Path B confusion. If the operator wired Path C
   (Hue Bridge + `light.approach_scene` group) but the Hue
   app's group membership is incomplete (e.g. they added the
   entry + underbody bulbs but forgot the soft interior bulb),
   the soft interior light stays off when the approach scene
   fires. If the operator wired Path A (Shelly / Hue / Zigbee
   individual entities) but the §7.1 automation only targets
   the entry + underbody switches (forgetting the soft interior
   switch), the soft interior light stays off. Solution: verify
   the group membership in the Hue app (Path C) OR verify the
   §7.1 automation's `target.entity_id` list (Path A / B).

4. **Camera override always firing** — Frigate zone too
   sensitive / motion-trigger vs person-trigger. If the Frigate
   entry zone is too sensitive (e.g. it triggers on every
   shadow movement from a tree), the camera-override fires
   constantly throughout the day + night. If the Frigate
   trigger is `motion` (not `person`), the override fires on
   every motion event (a passing car, a cat, a shadow), not just
   on `person` detections. Solution: tighten the Frigate entry
   zone (smaller bounding box); switch the Frigate trigger
   from `motion` to `person` (the recipe's
   `binary_sensor.<camera>_<zone>_person_detected` template
   binary_sensor only fires on `person` classifications, not on
   raw motion).

5. **Stealth mode doesn't suppress** — mode/automation-builder
   recipe not wired / `select.rc_mode` tile missing. The §7.5
   stealth-mode-suppression automation depends on
   `select.rc_mode` from the mode/automation-builder
   connection. If that connection is not installed + the
   `select.rc_mode` tile is missing, the §7.1 first-arrival-
   after-dark automation's `condition: select.rc_mode !=
   stealth` check is always TRUE (the missing entity defaults
   to "unknown" / "unavailable", not "stealth"), so Stealth
   mode does not actually suppress the approach scene.
   Solution: install the mode/automation-builder recipe + wire
   the `select.rc_mode` tile.

6. **Underbody light flickers** — 12 V supply undersized for the
   LED strip current / relay contact bounce (no flyback diode).
   The underbody LED strip pulls ~3 A at 12 V; if the van's 12
   V distribution is undersized (a 2 A fuse on a circuit that's
   pulling 3 A peaks), the voltage sags + the LED strip
   flickers. If the relay driving the LED strip has contact
   bounce (a low-quality relay that doesn't make a clean
   contact), the LED strip flickers. Solution: verify the 12 V
   distribution's fuse rating (use a 5 A fuse for a 5 m
   underbody strip pulling ~3 A sustained); replace the relay
   with a higher-quality one OR add a flyback diode across the
   relay coil (a 1N4007 diode in reverse-bias across the relay
   coil terminals absorbs the back-EMF when the relay coil
   de-energizes).

## §9 Privacy

No telemetry beyond local on/off state. Everything is local. The
upstream `shelly` / `hue` / `lifx` / `tradfri` / `zha` / `zwave_
js` / `tuya` / `lutron` / `bond` / `template` integrations are
local; no cloud call home from RoamCore.

The lights produce no telemetry beyond the local on/off state
(the upstream integration reports each light's `state` attribute
— on/off — which the `template:` binary_sensor mirrors into the
`rc_lighting_*` contract tiles).

The camera-override cross-references Frigate which has its own
privacy controls (the Frigate `binary_sensor.<camera>_<zone>_
person_detected` entity is derived from local Frigate inference
on the operator's local camera feeds; Frigate does NOT send any
video to the cloud). The push notification for the camera-
override uses the operator's existing HA Core push notification
channel — that's the operator's choice; RoamCore does not add
any push notification channel.

Path A Hue / LIFX require their own cloud auth (Hue) but only
for the operator's first-time setup; subsequent runs are local
(the Hue Bridge runs a local API for daily operation; the cloud
auth is only needed for the Hue app's remote access). LIFX is
fully local (no cloud required for daily operation).

The bluetooth-wifi-presence Wave 3 #42 cross-reference for the
§7.1 first-arrival-after-dark trigger uses the operator's
existing presence detection (the operator's phone's Bluetooth
MAC + Wi-Fi association); no additional tracking is added by
RoamCore.

## §10 Promoting to tier-a

What would need to happen to promote this connection from
tier-b to tier-a:

- A real approach-light bench on the CI rig: a Shelly 1 + a 12 V
  LED strip + a Hue Bridge + a Frigate entry zone, all wired
  together in a controlled environment + a way to simulate the
  first-arrival / dark / Frigate `person` trigger conditions.
- A canonical RoamCore-owned `config_flow.py` that walks the
  operator through choosing Path A / B / C + declaring the
  upstream entities + the camera-override Frigate zone + the
  dark-outside signal choice (`sun.sun` vs
  `sensor.rc_weather_light_lux`) + the operator-tunable
  thresholds (`number.rc_lighting_approach_duration_min` default
  2; range 1–10) + the `select.rc_lighting_approach_mode` (auto /
  dark_only / stealth_only / disabled).
- Integration tests that assert a presence-detected event (a
  canned fixture response simulating
  `binary_sensor.rc_presence_all_away` transitioning TRUE →
  FALSE AND `binary_sensor.rc_lighting_dark_outside` TRUE)
  triggers the approach scene + starts the N-minute countdown.
- Integration tests that assert a Frigate `person` event (a
  canned fixture response simulating
  `binary_sensor.<camera>_<zone>_person_detected` transitioning
  to TRUE) triggers the camera override + sets the underbody
  lights to full brightness + starts the 30-second countdown.
- Integration tests that assert a Stealth mode change (a canned
  fixture response simulating `select.rc_mode` transitioning to
  `stealth`) suppresses the §7.1 first-arrival-after-dark
  automation + kills any in-progress approach scene.
- Integration tests that assert the §7.3 auto-stop-after-N-min
  automation fires the `light.turn_off` after the configured
  minutes.
- Flip `tier_requirements` to include `working_config_flow` +
  `integration_test_passes` + `no_manual_yaml_required` +
  `safety_automations_hard_enforced_in_roamcore_code`.

Until those ship, this connection is tier-b even though the
upstream shelly / hue / lifx / tradfri / zha / zwave_js / tuya
/ lutron / bond / template / input_boolean / input_select /
input_number / input_datetime / binary_sensor / button / timer
integrations have their own GUI flows. The recipe is sound but
we cannot claim one-tap automation.

## §11 Files in this connection + cross-references

### Files in this connection

- `connection.yml` — the source-of-truth manifest (12
  `rc_lighting_*` contract tiles + 11 OpenClaw queries + 11
  OpenClaw summary keys + 5 `tier_warnings` honesty markers +
  vendor-neutral positioning header explaining Path A smart
  switches / smart bulbs + Path B generic relay + Path C all-in-
  one smart scene controller + the install.config_flow = true
  upstream-truth footnote; mirrors electronic-valves manifest
  shape verbatim with approach-lights substitutions).
- `__init__.py` — `DOMAIN = "approach_lights"` marker stub.
- `README.md` — folder overview + supersession pointer.
- `docs/recipe.md` — this file (the full howto).
- `tests/test_connection_yml.py` — manifest honesty checks.

### Cross-references

- **Bluetooth / Wi-Fi presence Wave 3 #42** — the §7.1 first-
  arrival-after-dark trigger depends on
  `binary_sensor.rc_presence_all_away` (the "nobody → someone
  home" edge) +
  `binary_sensor.rc_presence_anyone_home` (cross-check).
  Connection: `connections/bluetooth-wifi-presence/`.
- **Mode / automation-builder** — the §7.5 stealth-mode-
  suppression automation depends on `select.rc_mode` (Stealth
  mode from the mode/automation-builder connection). Connection:
  `connections/mode-automation-builder/`.
- **Frigate Wave 3 #35** — the §7.4 camera-override-on-frigate-
  person automation depends on
  `binary_sensor.<camera>_<zone>_person_detected` (the Frigate
  `person` classification entity, wired via HA `template:`
  binary_sensor). Connection: `connections/frigate/`.
- **Time / weather contract** — the §6 dark-outside signal is
  wired via `sun.sun` (HA core, GUI flow since 2022.x — the
  simpler default) OR `sensor.rc_weather_light_lux` (from
  `homeassistant/packages/roamcore_weather_time.yaml` — the
  more accurate choice for urban environments with bright
  streetlight pollution).
- **Motion-based lighting Wave 3 #53** — companion slice for
  the driving + ignition path; same `lighting` subsystem
  prefix. The `lighting` subsystem addition to
  `docs/reference/rc-entity-naming.md` (made by this slice)
  lays the groundwork for both slices. Connection:
  `connections/motion-based-lighting/`.
- **RoamCore entity naming** — `docs/reference/rc-entity-naming.
  md` §lighting subsystem (NEW — added by this slice).