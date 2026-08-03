# Fans — full howto (RoamCore vendor-neutral fan-controller umbrella for HA — rooftop vent fans + circulation fans + bathroom exhaust fans)

This recipe is the canonical howto for the
`connections/fans/` tier-b recipe connection (Wave 3
#59). It walks the operator through setting up ONE of the
FOUR operator-pickable fan-controller paths (Path A
Z-Wave / Zigbee / MQTT fan controllers + Path B Wi-Fi /
BLE smart fans via Bond Home + Hunter SIMPLEconnect + Tuya
+ Path C generic 12 V / 24 V fan + relay + Path D
all-in-one smart fan like MaxxAir / Fan-Tastic / MAXXAIR
Deluxe rooftop vent fan) + the 8 `rc_fan_*` contract
tiles + the FIVE §8 automations.

The recipe assumes the operator has at least 1
controllable fan installed (rooftop vent fan + circulation
fan + bathroom exhaust fan) + the operator's choice of
upstream fan controller integrated into HA. If the
operator has no fan installed, the recipe starts at §2
Prerequisites + walks through the fan-installation
prerequisites before the fan-controller wiring.

## §1 What are fans in RoamCore?

Fans (vendor-neutral fan-controller umbrella for HA,
covering rooftop vent fans + circulation fans + bathroom
exhaust fans — rooftop + circulation fans cover the
climate-aware airflow + the rain-sensor safety block;
bathroom exhaust fans wire as a separate downstream
`fan.*` entity that RoamCore does NOT own) — the umbrella
for "Fans are a simple upgrade that massively improves
comfort: airflow, condensation control, cooking smells,
and keeping the van livable in warm weather" — is the
ventilation-category complement to the broader RoamCore
climate-aware automation affordances. The umbrella
positions fans as a ventilation-category concern (not a
scene + not a power-load concern + not a remote-access
concern) because fans are the climate-aware airflow
substrate: the rooftop vent fan handles the moisture +
CO2 + cooking-smell + condensation load; the circulation
fan handles the bedroom/bathroom airflow; the bathroom
exhaust fan handles the shower/bath humidity. Each is a
separate `fan.*` entity on the HA server (the rooftop
vent fan + the circulation fan + the bathroom exhaust
fan are typically separate physical devices); the recipe
wires ALL of them into the umbrella.

The umbrella publishes the 8 `rc_fan_*` contract tiles
(vendor-neutral — no MaxxAir / Fan-Tastic / MAXXAIR
Deluxe / Heng's / Vento / generic-Zigbee /
generic-Z-Wave / Tuya / Shelly / Zooz / Aeotec / Inovelli
/ Bond Home / Hunter / Shelly names leak into the tile
ids). The tiles are:

- `fan.rc_fan_main` — the main fan, mapped via template
  fan from the upstream `fan.*` entities. The tile is an
  `input_select`-backed `fan:` domain entity (since
  2022.x) that selects between the operator's chosen
  upstream `fan.*` entity (one of `fan.maxxair_roof` /
  `fan.bond_fan` / `fan.tuya_fan` / `fan.ventilation` /
  `fan.zwave_fan_controller` / `fan.zigbee_fan_` etc.).
  The HA core `fan` integration has exposed the standard
  `set_percentage` service + `percentage` attribute +
  `preset_mode` attribute since 2022.x; the umbrella uses
  these standard services + attributes. The §8.1 + §8.2
  + §8.3 + §8.4 automations call the upstream
  `fan.turn_on` + `fan.set_percentage` + `fan.turn_off`
  services through this contract layer.
- `sensor.rc_fan_speed_percent` — the current fan speed
  as a 0-100 percent. The tile is a `template:` sensor
  (since 2022.x) that derives from the upstream `fan.*`
  entity's `percentage` attribute (the HA core `fan`
  integration has exposed a `percentage` attribute since
  2022.x). The tile is the operator-facing "what speed
  is the fan at?" indicator; the §8.1 + §8.2
  automations set the speed via the upstream
  `fan.set_percentage` service.
- `select.rc_fan_mode` — the operator's chosen fan mode
  (one of `off` / `low` / `med` / `high` / `auto` /
  `rain_safe`). The tile is a `select:` domain entity
  (since 2022.x) that maps to the upstream `fan.*`
  entity's `preset_mode` attribute (the HA core `fan`
  integration has exposed a `preset_mode` attribute since
  2022.x — values are vendor-defined, but `low` / `med` /
  `high` are the de-facto standard for 3-speed fans).
  The tile is the operator-facing "what mode is the fan
  in?" affordance; the §8.1 + §8.2 + §8.4 automations
  write to this tile before calling the upstream
  `fan.turn_on` / `fan.turn_off` services.
- `binary_sensor.rc_fan_active` — the AND gate (TRUE iff
  the fan is currently running). The tile is a
  `template:` binary_sensor (since 2022.x) that derives
  from the upstream `fan.*` entity's `state` attribute
  (the HA core `fan` integration has exposed `state` as
  `off` / `on` since 2022.x). The tile is the
  operator-facing "is the fan currently running?"
  indicator.
- `sensor.rc_fan_runtime_minutes_today` — the fan's
  runtime in minutes for today. The tile is a
  `template:` sensor (since 2022.x) that derives from
  the upstream `fan.*` entity's history (the HA core
  `statistics` integration OR the `history_stats:`
  platform since 2022.x aggregates the upstream `fan.*`
  entity's ON-time into a daily total). The tile is the
  operator-facing "how long has the fan been running
  today?" indicator.
- `sensor.rc_fan_last_trigger_reason` — the reason the
  fan was last turned on (one of `manual` / `humidity` /
  `temperature` / `schedule` / `sleep`). The tile is an
  `input_text:` domain entity (since 2022.x) that the
  operator's automations write to before calling the
  `fan.turn_on` service. The tile is the operator-facing
  "why was the fan last turned on?" indicator.
- `button.rc_fan_run_now_15min` — the manual override
  (the operator can force the fan to run for 15 minutes
  from the dashboard without waiting for the §8.1 + §8.2
  auto-fan-on-humidity-high / auto-fan-on-temperature-
  high automations). The button is an `input_button:`
  domain entity (since 2022.x) that fires a 15-minute
  `fan.turn_on` + a 15-minute timer to call
  `fan.turn_off` after 15 minutes. The tile is the
  operator-facing "run the fan for 15 minutes now"
  affordance; the §8.3 automation handles the timer.
- `binary_sensor.rc_fan_rain_sensor_active` — the
  rain-sensor trip gate (TRUE iff the rain sensor is wet
  — the rooftop fan is forced OFF + the rooftop vent
  cover is forced CLOSED when this tile is TRUE). The
  tile is a `template:` binary_sensor (since 2022.x)
  that derives from the operator's physical rain sensor
  (a Z-Wave / Zigbee / wired rain sensor OR a
  binary_sensor derived from the rooftop vent fan's
  built-in rain sensor if the operator has a MaxxAir /
  Fan-Tastic / MAXXAIR Deluxe with a built-in rain
  sensor). The tile is the operator-facing "is the rain
  sensor blocking the fan?" indicator; the §8.4
  rain-sensor hard-block automation reads from this tile
  + the cover entities for the Path D rooftop vent cover
  block.

The 8 contract tiles are vendor-neutral — no vendor /
hardware / protocol / integration names leak into the
tile ids. The umbrella uses the `rc_fan_*` prefix
because `ventilation` is the canonical vendor-neutral
fan subsystem (the umbrella for the FOUR operator-
pickable paths); the `ventilation` subsystem addition
to `docs/reference/rc-entity-naming.md` is the FIRST
`ventilation`-category slice in the RoamCore connection
pipeline.

## §2 Prerequisites

Before installing the fans connection, the operator
needs:

- **At least 1 controllable fan installed.** The
  operator needs at least 1 of:
  - **Rooftop vent fan** — MaxxAir iFAN / Fan-Tastic
    Vent / MAXXAIR Deluxe are common choices. Path D
    umbrella — exposes a `fan.*` entity + a `cover.*`
    entity for the automatic rain cover.
  - **Circulation fan** — a 12 V / 24 V circulation
    fan (Heng's / Vento / generic 12 V DC brushless fan)
    wired to a relay (Shelly 1 / Shelly Plus 1 / Zooz
    ZEN17 / Aeotec Nano Switch). Path C umbrella.
  - **Bathroom exhaust fan** — a 12 V / 24 V exhaust
    fan wired to a relay. Path C umbrella (separate
    from the rooftop vent fan).
  - **Wi-Fi / BLE smart fan** — Bond Home RF-bridge-
    controlled ceiling fan / Hunter SIMPLEconnect
    Wi-Fi/BLE fan / Tuya Wi-Fi smart fan. Path B
    umbrella.

- **The operator's choice of upstream fan controller
  integrated into HA.** The operator needs at least 1
  of:
  - **HA core `fan` integration** (since 2022.x) — the
    canonical umbrella. Exposes the standard
    `set_percentage` service + `percentage` attribute +
    `preset_mode` attribute + the `fan.turn_on` /
    `fan.turn_off` / `fan.toggle` / `fan.set_percentage`
    / `fan.set_preset_mode` services.
  - **HA core `template:` fan wrapper** (since 2022.x)
    — the canonical Path C wrapping for relay-driven
    fans. Wraps any relay state into a virtual `fan.*`
    entity.
  - **HA core `zwave_js` integration** (since 2022.x) —
    the canonical Path A1 Z-Wave fan controller
    integration.
  - **HA core `zha` integration** (since 2022.x) — the
    canonical Path A2 Zigbee fan controller integration.
  - **HA core `mqtt` integration** (since 2022.x) — the
    canonical Path A3 generic-tasmota-flashed fan
    controller integration.
  - **HA core Shelly integration** (since 2022.x) — the
    canonical Path C1 Shelly 1 / Shelly Plus 1 wired to
    a 12 V fan integration.
  - **HACS `bond` integration** (HACS) — the canonical
    Path B1 Bond Home RF-bridge + ceiling fan
    integration.
  - **HACS `tuya` integration** (HACS) — the canonical
    Path B3 Tuya Wi-Fi smart fan integration.
  - **HACS `hunterdouglas_simplify` integration** (HACS)
    — the canonical Path B2 Hunter SIMPLEconnect
    Wi-Fi/BLE fan integration.

- **Temperature + humidity via the HVAC basics Wave 3
  #49 connection.** REQUIRED — the §8.1 +
  auto-fan-on-humidity-high automation reads
  `sensor.rc_hvac_interior_humidity`; the §8.2
  auto-fan-on-temperature-high automation reads
  `sensor.rc_hvac_interior_temperature`. Both tiles are
  defined in the HVAC basics Wave 3 #49 connection's
  contract layer.

- **Optional rain sensor for the rain-safe mode.**
  REQUIRED for Path D rooftop vent fans (the rooftop
  fan is forced OFF + the rooftop vent cover is forced
  CLOSED when the rain sensor trips); OPTIONAL for
  Path A / Path B / Path C. The operator can use:
  - A Z-Wave / Zigbee rain sensor wired into the HA
    server (common choices: Z-Wave weather sensors with
    a rain-detect input; Zigbee rain sensors like the
    generic-Zigbee rain sensor family).
  - A wired rain sensor wired into a Shelly 1 / Shelly
    Plus 1 input (the Shelly's input state becomes a
    `binary_sensor.*` entity that the recipe's
    `template:` binary_sensor derives from).
  - The rooftop vent fan's built-in rain sensor (Path D
    only — MaxxAir / Fan-Tastic / MAXXAIR Deluxe all
    expose a built-in rain sensor that the upstream
    integration surfaces as a `binary_sensor.*` entity).

- **Optional time-of-day / sunrise-sunset for the Sleep
  mode suppression.** The §8.5 Sleep mode suppression
  automation cross-references the time-atomic Wave 3
  #55 connection's time-of-day + sunrise-sunset
  primitives for the operator's chosen overnight-camp
  schedule. The operator configures the time window
  (default 22:00–06:00 local time) where the §8.1 +
  §8.2 auto-fan automations are suppressed.

- **An always-on HA instance** (the RoamCore canonical
  setup).

## §3 Path A — Smart fan controllers (Z-Wave / Zigbee / MQTT)

Path A covers THREE sub-flavors: Path A1 Z-Wave fan
controller, Path A2 Zigbee fan controller, Path A3
generic-tasmota-flashed fan controller. The operator
picks ONE sub-flavor based on the operator's existing
Z-Wave / Zigbee / MQTT infrastructure.

### §3.1 Path A1 — Z-Wave fan controller (Zooz ZEN17 + Aeotec Nano Switch + Inovelli LZW42)

1. **Install the Z-Wave fan controller hardware.** The
   operator installs the chosen Z-Wave fan controller
   (Zooz ZEN17 + Aeotec Nano Switch + Inovelli LZW42
   are common choices for 12 V / 24 V fans) per the
   manufacturer instructions. The fan controller is
   wired to the 12 V / 24 V fan's power supply + the
   fan's speed control input (3-speed fans typically
   have a 3-position switch OR a variable-speed
   PWM/dimmer input; the fan controller's relay
   output(s) map to the fan's speed control input).
2. **Add the Z-Wave fan controller to the HA server's
   Z-Wave network.** The operator uses the HA core
   `zwave_js` integration's GUI flow (since 2022.x —
   exposes a GUI flow for the operator to add the
   Z-Wave fan controller to the HA server's Z-Wave
   network + view the resulting `binary_switch.*` OR
   `fan.*` entity from the operator's Z-Wave network).
   The operator opens Settings → Devices & Services →
   Z-Wave JS → Configure → Add Node → triggers the
   Z-Wave inclusion on the fan controller → waits for
   the inclusion to complete → verifies the fan
   controller appears as a device.
3. **Verify the upstream `fan.*` entity exists.** The
   HA core `fan` integration should auto-discover the
   fan controller as a `fan.*` entity (the upstream
   Z-Wave fan controller exposes the standard fan
   contract since 2022.x; the umbrella surfaces it as
   a `fan.*` entity with the `set_percentage` service +
   `percentage` attribute + `preset_mode` attribute).
   If the entity does not appear, the operator checks
   the Z-Wave inclusion log + the `zwave_js`
   integration's device page.
4. **Configure the operator-facing `fan.rc_fan_main`
   contract tile.** The operator creates an
   `input_select` helper (since 2022.x) that maps the
   umbrella to the upstream `fan.*` entity (e.g.
   `fan.zwave_fan_controller`). The recipe §7 walks
   through the `input_select` + `template:` fan
   wrapper mapping.
5. **Configure `select.rc_fan_mode` to `auto`.** The
   operator sets the fan mode to `auto` (the default
   starting mode; the §8.1 + §8.2 automations take
   over from here).
6. **Wire the §8.4 rain-sensor hard-block.** The
   operator wires the rain sensor (if installed) into
   `binary_sensor.rc_fan_rain_sensor_active`. The
   §8.4 automation reads from this tile + calls
   `fan.turn_off` on the upstream `fan.*` entity when
   the rain sensor trips. For Path A1, no
   `cover.close_cover` call is needed (Path A fans do
   not have an automatic rain cover; the rooftop
   vent cover is a Path D concern).
7. **Verify the fan runs.** The operator presses
   `button.rc_fan_run_now_15min` (the §8.3 manual
   override) + verifies the fan runs for 15 minutes +
   verifies `binary_sensor.rc_fan_active` flips to
   TRUE during the 15-minute window +
   `sensor.rc_fan_speed_percent` reflects the
   upstream `percentage` attribute.

### §3.2 Path A2 — Zigbee fan controller

1. **Install the Zigbee fan controller hardware.** The
   operator installs the chosen Zigbee fan controller
   (generic-Zigbee fan controllers + the Tuya Zigbee
   fan family are common choices) per the manufacturer
   instructions.
2. **Add the Zigbee fan controller to the HA server's
   Zigbee network.** The operator uses the HA core
   `zha` integration's GUI flow (since 2022.x — exposes
   a GUI flow for the operator to add the Zigbee fan
   controller to the HA server's Zigbee network + view
   the resulting `fan.*` entity from the operator's
   Zigbee network).
3. **Verify the upstream `fan.*` entity exists.** The
   HA core `fan` integration should auto-discover the
   fan controller as a `fan.*` entity with the standard
   contract.
4. **Configure the operator-facing `fan.rc_fan_main`
   contract tile** + `select.rc_fan_mode` to `auto`.
5. **Wire the §8.4 rain-sensor hard-block** (if a rain
   sensor is installed).
6. **Verify the fan runs** (same as Path A1).

### §3.3 Path A3 — Generic-tasmota-flashed fan controller

1. **Flash Tasmota onto the relay.** The operator
   flashes Tasmota onto any 12 V / 24 V fan relay per
   the Tasmota flashing instructions
   (https://tasmota.github.io/docs/Getting-Started/).
2. **Configure the MQTT topic.** The operator
   configures the Tasmota-flashed relay's MQTT topic
   in the Tasmota web UI (Configure → MQTT → Topic →
   `tasmota_fan_relay`). The operator's HA server's
   `mqtt` integration (since 2022.x — exposes a GUI
   flow for the operator to configure the MQTT topic)
   auto-discovers the relay + surfaces it as a
   `fan.*` entity.
3. **Verify the upstream `fan.*` entity exists.** The
   HA core `fan` integration should auto-discover the
   relay as a `fan.*` entity with the standard
   contract.
4. **Configure the operator-facing `fan.rc_fan_main`
   contract tile** + `select.rc_fan_mode` to `auto`.
5. **Wire the §8.4 rain-sensor hard-block** (if a rain
   sensor is installed).
6. **Verify the fan runs** (same as Path A1).

## §4 Path B — Wi-Fi / BLE smart fan (Bond Home + Hunter SIMPLEconnect + Tuya)

Path B covers THREE sub-flavors: Path B1 Bond Home +
ceiling fan, Path B2 Hunter SIMPLEconnect, Path B3 Tuya
Wi-Fi smart fan. The operator picks ONE sub-flavor based
on the operator's existing Wi-Fi / BLE smart fan
hardware.

### §4.1 Path B1 — Bond Home RF-bridge + ceiling fan

1. **Pair the Bond Home hub to the RF-bridge-controlled
   ceiling fan.** The operator follows the Bond Home
   pairing instructions
   (https://github.com/bondhomeio/bond): installs the
   Bond Home app + pairs the Bond Home hub to the
   operator's Wi-Fi network + pairs the
   RF-bridge-controlled ceiling fan via the Bond Home
   app's "Add Device" flow.
2. **Install the HACS `bond` integration.** The
   operator installs the HACS `bond` integration
   (HACS — exposes a GUI flow for the operator to add
   the Bond Home hub to HA + view the resulting
   `fan.*` entity).
3. **Verify the upstream `fan.*` entity exists.** The
   HACS `bond` integration surfaces the Bond Home
   ceiling fan as a `fan.*` entity with the standard
   `set_percentage` service + `percentage` attribute +
   `preset_mode` attribute.
4. **Configure the operator-facing `fan.rc_fan_main`
   contract tile** + `select.rc_fan_mode` to `auto`.
5. **Wire the §8.4 rain-sensor hard-block** (if a rain
   sensor is installed).
6. **Verify the fan runs** (same as Path A1).

### §4.2 Path B2 — Hunter SIMPLEconnect (HunterDouglas SIMPLIFY) Wi-Fi/BLE fan

1. **Pair the Hunter SIMPLEconnect fan.** The operator
   installs the Hunter SIMPLEconnect app + pairs the
   fan per the app's instructions.
2. **Install the HACS `hunterdouglas_simplify`
   integration.** The operator installs the HACS
   `hunterdouglas_simplify` integration (HACS —
   exposes a GUI flow for the operator to add the
   Hunter SIMPLEconnect fan to HA + view the resulting
   `fan.*` entity).
3. **Verify the upstream `fan.*` entity exists.** The
   HACS `hunterdouglas_simplify` integration surfaces
   the Hunter SIMPLEconnect fan as a `fan.*` entity
   with the standard contract.
4. **Configure the operator-facing `fan.rc_fan_main`
   contract tile** + `select.rc_fan_mode` to `auto`.
5. **Wire the §8.4 rain-sensor hard-block** (if a rain
   sensor is installed).
6. **Verify the fan runs** (same as Path A1).

### §4.3 Path B3 — Tuya Wi-Fi smart fan

1. **Pair the Tuya Wi-Fi smart fan.** The operator
   installs the Tuya Smart / Smart Life app + pairs
   the fan per the app's instructions.
2. **Install the HACS `tuya` integration.** The
   operator installs the HACS `tuya` integration
   (HACS — exposes a GUI flow for the operator to add
   the Tuya Wi-Fi smart fan to HA + view the
   resulting `fan.*` entity). The operator enters
   their Tuya Smart / Smart Life app credentials in
   the HACS `tuya` integration's GUI flow.
3. **Verify the upstream `fan.*` entity exists.** The
   HACS `tuya` integration surfaces the Tuya Wi-Fi
   smart fan as a `fan.*` entity with the standard
   contract.
4. **Configure the operator-facing `fan.rc_fan_main`
   contract tile** + `select.rc_fan_mode` to `auto`.
5. **Wire the §8.4 rain-sensor hard-block** (if a rain
   sensor is installed).
6. **Verify the fan runs** (same as Path A1).

## §5 Path C — Generic 12 V / 24 V fan + relay (no smart fan controller)

Path C covers TWO sub-flavors: Path C1 Shelly 1 / Shelly
Plus 1 wired to a 12 V fan, Path C2 Zooz ZEN17 / Aeotec
Nano Switch wired to a 24 V fan. The operator picks ONE
sub-flavor based on the operator's existing relay
hardware.

### §5.1 Path C1 — Shelly 1 / Shelly Plus 1 wired to a 12 V fan

1. **Install the Shelly 1 / Shelly Plus 1 hardware.**
   The operator installs the Shelly 1 / Shelly Plus 1
   relay per the manufacturer instructions. The relay
   is wired to the 12 V fan's power supply + the fan's
   on/off control input (binary fans have a simple
   on/off input; 3-speed fans have a 3-position switch
   OR a variable-speed PWM/dimmer input; the Shelly
   relay's output contacts map to the fan's on/off
   control input).
2. **Add the Shelly 1 / Shelly Plus 1 to the HA
   server.** The operator uses the HA core Shelly
   integration's GUI flow (since 2022.x — exposes a
   GUI flow for the operator to add the Shelly 1 /
   Shelly Plus 1 to HA + view the resulting
   `binary_switch.*` entity).
3. **Create a `template:` fan wrapping the relay state
   into a virtual `fan.ventilation` entity.** The
   operator creates a `template:` fan (since 2022.x)
   in `configuration.yaml` that wraps the upstream
   `binary_switch.*` entity into a virtual `fan.*`
   entity with the standard `percentage` attribute +
   `preset_mode` attribute + `set_percentage` service.
   The recipe §7 walks through the template fan
   configuration.
4. **Verify the upstream `fan.ventilation` entity
   exists.** The HA core `fan` integration surfaces
   the template fan as a `fan.*` entity with the
   standard contract.
5. **Configure the operator-facing `fan.rc_fan_main`
   contract tile** + `select.rc_fan_mode` to `auto`.
6. **Wire the §8.4 rain-sensor hard-block** (if a rain
   sensor is installed).
7. **Verify the fan runs** (same as Path A1).

### §5.2 Path C2 — Zooz ZEN17 / Aeotec Nano Switch wired to a 24 V fan

1. **Install the Zooz ZEN17 / Aeotec Nano Switch
   hardware.** The operator installs the relay per the
   manufacturer instructions. The relay is wired to
   the 24 V fan's power supply + the fan's on/off
   control input.
2. **Add the relay to the HA server's Z-Wave network.**
   The operator uses the HA core `zwave_js`
   integration's GUI flow to add the relay to the HA
   server's Z-Wave network.
3. **Create a `template:` fan wrapping the relay state
   into a virtual `fan.*` entity** (same as Path C1).
4. **Verify the upstream `fan.*` entity exists.**
5. **Configure the operator-facing `fan.rc_fan_main`
   contract tile** + `select.rc_fan_mode` to `auto`.
6. **Wire the §8.4 rain-sensor hard-block** (if a rain
   sensor is installed).
7. **Verify the fan runs** (same as Path A1).

## §6 Path D — All-in-one smart fan (MaxxAir / Fan-Tastic / MAXXAIR Deluxe)

Path D covers the rooftop vent fan walkthrough. The
operator installs the rooftop vent fan per the
manufacturer instructions + wires it into HA via the
manufacturer-recommended integration + verifies the
upstream `fan.*` entity + the upstream `cover.*` entity
exist.

### §6.1 Rooftop vent fan (MaxxAir iFAN / Fan-Tastic Vent / MAXXAIR Deluxe)

1. **Install the rooftop vent fan hardware.** The
   operator installs the chosen rooftop vent fan
   (MaxxAir iFAN / Fan-Tastic Vent / MAXXAIR Deluxe are
   common choices) per the manufacturer instructions.
   The rooftop vent fan has a built-in rain sensor +
   an automatic rain cover that closes when the rain
   sensor trips.
2. **Wire the rooftop vent fan into HA via the
   manufacturer-recommended integration.** The operator
   wires the rooftop vent fan into HA via the
   manufacturer-recommended integration (MaxxAir iFAN
   + Fan-Tastic Vent + MAXXAIR Deluxe all expose a
   vendor integration that surfaces as a `fan.*`
   entity + a `cover.*` entity for the automatic rain
   cover). The integration's GUI flow walks the
   operator through adding the rooftop vent fan to HA.
3. **Verify the upstream `fan.*` entity + the upstream
   `cover.*` entity exist.** The HA core `fan`
   integration surfaces the rooftop vent fan as a
   `fan.*` entity with the standard contract; the HA
   core `cover` integration surfaces the rooftop vent
   cover as a `cover.*` entity with the standard
   `close_cover` service.
4. **Configure the operator-facing `fan.rc_fan_main`
   contract tile** + `select.rc_fan_mode` to `auto`.
5. **Wire the §8.4 rain-sensor hard-block.** The
   operator wires the rain sensor (REQUIRED for Path
   D) into `binary_sensor.rc_fan_rain_sensor_active`.
   The §8.4 automation reads from this tile + calls
   `fan.turn_off` on the upstream `fan.*` entity +
   calls `cover.close_cover` on the upstream `cover.*`
   entity when the rain sensor trips.
6. **Verify the fan runs** + verify the cover closes
   when the rain sensor trips (the operator can use a
   spray bottle to test the rain sensor).

### §6.2 Path D rain-sensor safety block — the canonical rooftop vent fan use case

The Path D rain-sensor safety block is the canonical
rooftop vent fan use case. The operator's MaxxAir /
Fan-Tastic / MAXXAIR Deluxe has a built-in rain sensor
that closes the cover automatically; the umbrella's
§8.4 rain-sensor hard-block automation ADDS the
RoamCore-side safety block (forces the fan OFF + the
cover CLOSED via the HA core `cover.close_cover`
service) so the operator has a single source of truth
for the rain-sensor state on the HA server.

The umbrella's rain-sensor safety block is also wired
to the upstream cover entity (the HA core `cover`
integration surfaces the rooftop vent cover as a
`cover.*` entity with the standard `close_cover` +
`open_cover` services). The §8.4 automation calls
`cover.close_cover` on the upstream cover entity when
the rain sensor trips — this is the canonical
"close-the-cover-when-it-rains" affordance for the
rooftop vent fan.

## §7 RoamCore contract entities

The 8 `rc_fan_*` contract tiles are vendor-neutral — no
vendor / hardware / protocol / integration names leak
into the tile ids. The umbrella uses the `rc_fan_*`
prefix because `ventilation` is the canonical
vendor-neutral fan subsystem (the umbrella for the
FOUR operator-pickable paths); the `ventilation`
subsystem addition to `docs/reference/rc-entity-naming.md`
is the FIRST `ventilation`-category slice in the
RoamCore connection pipeline.

The contract tiles + how the upstream fan template
exposes them:

- `fan.rc_fan_main` — the main fan, mapped via template
  fan from the upstream `fan.*` entities. The tile is
  an `input_select`-backed `fan:` domain entity (since
  2022.x) that selects between the operator's chosen
  upstream `fan.*` entity (one of `fan.maxxair_roof` /
  `fan.bond_fan` / `fan.tuya_fan` / `fan.ventilation` /
  `fan.zwave_fan_controller` / `fan.zigbee_fan_` etc.).
  The translation helper is a `template:` fan (since
  2022.x) that wraps the operator's chosen upstream
  `fan.*` entity into the contract layer.

- `sensor.rc_fan_speed_percent` — the current fan
  speed as a 0-100 percent. The tile is a `template:`
  sensor (since 2022.x) that derives from the upstream
  `fan.*` entity's `percentage` attribute.

- `select.rc_fan_mode` — the operator's chosen fan mode
  (one of `off` / `low` / `med` / `high` / `auto` /
  `rain_safe`). The tile is a `select:` domain entity
  (since 2022.x) that maps to the upstream `fan.*`
  entity's `preset_mode` attribute.

- `binary_sensor.rc_fan_active` — the AND gate (TRUE iff
  the fan is currently running). The tile is a
  `template:` binary_sensor (since 2022.x) that derives
  from the upstream `fan.*` entity's `state` attribute
  (the HA core `fan` integration has exposed `state` as
  `off` / `on` since 2022.x).

- `sensor.rc_fan_runtime_minutes_today` — the fan's
  runtime in minutes for today. The tile is a
  `template:` sensor (since 2022.x) that derives from
  the upstream `fan.*` entity's history. The
  translation helper is the HA core `history_stats:`
  platform (since 2022.x) that aggregates the upstream
  `fan.*` entity's ON-time into a daily total.

- `sensor.rc_fan_last_trigger_reason` — the reason the
  fan was last turned on (one of `manual` / `humidity` /
  `temperature` / `schedule` / `sleep`). The tile is an
  `input_text:` domain entity (since 2022.x) that the
  operator's automations write to before calling the
  `fan.turn_on` service.

- `button.rc_fan_run_now_15min` — the manual override
  (the operator can force the fan to run for 15
  minutes from the dashboard without waiting for the
  §8.1 + §8.2 auto-fan-on-humidity-high /
  auto-fan-on-temperature-high automations). The
  button is an `input_button:` domain entity (since
  2022.x) that fires a 15-minute `fan.turn_on` + a
  15-minute timer to call `fan.turn_off` after 15
  minutes.

- `binary_sensor.rc_fan_rain_sensor_active` — the
  rain-sensor trip gate (TRUE iff the rain sensor is
  wet). The tile is a `template:` binary_sensor (since
  2022.x) that derives from the operator's physical
  rain sensor.

The translation helpers needed for the derived metrics
include:

- The `history_stats:` platform (since 2022.x) for the
  daily runtime aggregate.
- The `statistics:` integration (since 2022.x) for the
  upstream fan's mean / min / max speed over time.
- The `template:` sensor + binary_sensor + select +
  fan wrappers (since 2022.x) for the contract layer.
- The `input_text:` + `input_select:` + `input_button:`
  + `input_number:` helpers (since 2022.x) for the
  operator-facing affordances.

## §8 Automations

The FIVE §8 automations are documented below. The
automations are the canonical wiring that makes the
recipe work end-to-end. The recipe walks through each
automation + the contract tiles each automation reads +
the services each automation calls.

### §8.1 Auto-fan on humidity high

The automation fires when `sensor.rc_hvac_interior_
humidity` (from the HVAC basics Wave 3 #49 connection)
rises above 65% AND the fan is not in `rain_safe` mode.
The automation sets `select.rc_fan_mode` to `auto` +
writes `sensor.rc_fan_last_trigger_reason = humidity`
+ calls the upstream `fan.turn_on` service with
`percentage: 50` (med speed).

Trigger: `sensor.rc_hvac_interior_humidity > 65`
Condition: `select.rc_fan_mode != rain_safe`
Action:
```yaml
action: fan.turn_on
target:
  entity_id: fan.rc_fan_main
data:
  percentage: 50
```

The automation also writes
`sensor.rc_fan_last_trigger_reason = humidity` via
`input_text.set_value` service + sets
`select.rc_fan_mode = auto` via `select.select_option`
service.

### §8.2 Auto-fan on temperature high

The automation fires when
`sensor.rc_hvac_interior_temperature` (from the HVAC
basics Wave 3 #49 connection) rises above 28°C AND the
fan is not in `rain_safe` mode. The automation sets
`select.rc_fan_mode` to `auto` + writes
`sensor.rc_fan_last_trigger_reason = temperature` +
calls the upstream `fan.turn_on` service with
`percentage: 75` (high speed).

Trigger: `sensor.rc_hvac_interior_temperature > 28`
Condition: `select.rc_fan_mode != rain_safe`
Action:
```yaml
action: fan.turn_on
target:
  entity_id: fan.rc_fan_main
data:
  percentage: 75
```

The automation also writes
`sensor.rc_fan_last_trigger_reason = temperature` via
`input_text.set_value` service + sets
`select.rc_fan_mode = auto` via `select.select_option`
service.

### §8.3 Manual override via `button.rc_fan_run_now_15min`

The button fires a 15-minute `fan.turn_on` + a
15-minute timer to call `fan.turn_off` after 15 minutes
+ writes `sensor.rc_fan_last_trigger_reason = manual`.

Trigger: `button.rc_fan_run_now_15min` pressed
Action:
```yaml
action: fan.turn_on
target:
  entity_id: fan.rc_fan_main
data:
  percentage: 50
- delay: "00:15:00"
- action: fan.turn_off
target:
  entity_id: fan.rc_fan_main
```

The automation also writes
`sensor.rc_fan_last_trigger_reason = manual` via
`input_text.set_value` service.

### §8.4 Rain-sensor hard-block

The automation fires when
`binary_sensor.rc_fan_rain_sensor_active` flips to
TRUE. The automation calls `fan.turn_off` on the chosen
upstream fan entity + calls `cover.close_cover` on the
upstream cover entity if the operator has a rooftop
vent with a cover (Path D — MaxxAir / Fan-Tastic /
MAXXAIR Deluxe all expose an upstream `cover.*` entity
for the automatic rain cover) + writes
`select.rc_fan_mode = rain_safe` + notifies the
operator's phone (via the HA Companion app) saying
"Rain detected — fan forced OFF + cover forced CLOSED".

Trigger: `binary_sensor.rc_fan_rain_sensor_active`
flips to `on`
Action:
```yaml
action: fan.turn_off
target:
  entity_id: fan.rc_fan_main
- action: cover.close_cover
target:
  entity_id: cover.rc_fan_roof_cover  # Path D only
- action: select.select_option
target:
  entity_id: select.rc_fan_mode
data:
  option: rain_safe
- action: input_text.set_value
target:
  entity_id: sensor.rc_fan_last_trigger_reason
data:
  value: rain
- action: notify.notify
data:
  message: "Rain detected — fan forced OFF + cover forced CLOSED"
```

The cover entities cross-reference the upstream cover
integration for Path D rooftop vent covers; the
§8.4 automation's `cover.close_cover` call is a
Path D-specific affordance (Path A / Path B / Path C
fans do not have an automatic rain cover).

### §8.5 Sleep mode suppression via `select.rc_mode`

The automation SUPPRESSES the §8.1 + §8.2 auto-fan
automations when `select.rc_mode` is in `sleep` mode
(overnight camp where the fan noise is unwanted; the
operator can still trigger the manual override via
`button.rc_fan_run_now_15min`). The recipe §12
cross-references the mode/automation-builder recipe
(Wave 2 #23) for the `select.rc_mode` tile.

The suppression is implemented as a CONDITION on the
§8.1 + §8.2 automations:

Condition on §8.1 + §8.2: `select.rc_mode != sleep`

The operator can still trigger the fan during sleep mode
via `button.rc_fan_run_now_15min` (the §8.3 manual
override is NOT suppressed by sleep mode — only the
auto-fan automations are suppressed).

The recipe §12 cross-references the
mode/automation-builder recipe (Wave 2 #23) for the
`select.rc_mode` tile (the source of truth for the
`home` / `away` / `stealth` / `sleep` / `off` modes).

## §9 Troubleshooting

The 6 §9 troubleshooting entries cover the most common
issues operators hit when wiring the recipe:

### §9.1 Fan never starts

**Symptom:** The operator presses
`button.rc_fan_run_now_15min` (or the §8.1 + §8.2
auto-fan automations fire) but the fan does not start.

**Causes:**
- The upstream fan integration is not wired (the
  operator has not installed the HA core `fan`
  integration + the operator's chosen path's upstream
  integration). The operator checks Settings → Devices
  & Services → verify the operator's chosen path's
  integration is configured + verify the upstream
  `fan.*` entity exists.
- The operator's chosen path's upstream integration is
  wired but the upstream `fan.*` entity is not surfacing
  the standard contract (the upstream integration does
  not expose the `set_percentage` service + the
  `percentage` attribute + the `preset_mode`
  attribute). The operator checks the upstream
  integration's device page + verifies the `fan.*`
  entity has the standard contract attributes.
- The HVAC basics Wave 3 #49 connection's
  `sensor.rc_hvac_interior_temperature` +
  `sensor.rc_hvac_interior_humidity` tiles are not
  wired (the §8.1 + §8.2 auto-fan automations read
  from these tiles; if the tiles are not wired, the
  automations never fire). The operator checks
  Settings → Devices & Services → HVAC basics +
  verifies the tiles exist.
- The Sleep mode suppression is active (the operator is
  in `select.rc_mode = sleep` mode). The operator
  either changes `select.rc_mode` to `home` / `away` /
  `stealth` OR triggers the §8.3 manual override via
  `button.rc_fan_run_now_15min` (the §8.3 manual
  override is NOT suppressed by sleep mode).
- The `binary_sensor.rc_fan_active` tile is FALSE (the
  fan is NOT running). The operator checks the upstream
  `fan.*` entity's state + verifies the `state`
  attribute is `on`.

### §9.2 Fan stays on forever

**Symptom:** The operator presses
`button.rc_fan_run_now_15min` + the fan starts + the
fan does NOT turn off after 15 minutes.

**Causes:**
- The §8.3 manual override's 15-minute timer is
  misconfigured. The operator checks the §8.3
  automation's `delay: "00:15:00"` line + verifies the
  timer is correctly configured.
- The auto-off automation is missing (the §8.3 manual
  override relies on a 15-minute timer + the `fan.turn_
  off` service call after the timer; if the
  automation is missing, the fan stays on). The
  operator verifies the §8.3 automation is configured
  in `automations.yaml`.
- The operator's chosen path's upstream integration has
  a bug (the upstream integration does NOT respond to
  `fan.turn_off` service calls). The operator checks
  the upstream integration's device page + verifies the
  `fan.turn_off` service call works.

### §9.3 Fan only runs at full speed

**Symptom:** The operator presses
`button.rc_fan_run_now_15min` + the fan starts + the
fan only runs at full speed (the §8.1 + §8.2
automations set `percentage: 50` / `percentage: 75`
but the fan ignores the percentage + runs at 100%).

**Causes:**
- The vendor fan controller is NOT configured for
  variable speed (the fan controller is a simple
  on/off relay; the fan's motor speed is fixed at 100%
  on + 0% off). The operator either accepts the
  fixed-speed behavior OR replaces the fan controller
  with a variable-speed fan controller (Path A1 Z-Wave
  variable-speed fan controller OR Path A2 Zigbee
  variable-speed fan controller OR Path B1 Bond Home
  variable-speed ceiling fan).
- Path A vs Path B confusion (the operator wired a Path
  A simple on/off relay but expected Path B variable-
  speed ceiling fan behavior). The operator picks the
  correct path for the operator's hardware.
- The §8.1 + §8.2 automations set the percentage but
  the upstream fan's `percentage` attribute is not
  reflected (the upstream fan integration does NOT
  surface the `percentage` attribute). The operator
  checks the upstream fan's state attributes + verifies
  the `percentage` attribute is set correctly.

### §9.4 Rain-sensor always blocks

**Symptom:** The operator wired a rain sensor but the
fan never runs (the §8.4 rain-sensor hard-block
automation always fires + forces the fan OFF).

**Causes:**
- The rain sensor is not wired (the
  `binary_sensor.rc_fan_rain_sensor_active` template
  binary_sensor is not derived from the upstream rain
  sensor's `binary_sensor.*` entity). The operator
  checks the template binary_sensor's source + verifies
  the upstream `binary_sensor.*` entity exists.
- The rain sensor's polarity is reversed (the rain
  sensor's `binary_sensor.*` entity is `on` when the
  sensor is dry + `off` when the sensor is wet; the
  template binary_sensor should be `on` when the sensor
  is wet + `off` when the sensor is dry). The operator
  inverts the template binary_sensor's polarity.
- The rain sensor is stuck in the "wet" state (the
  rain sensor's wiring is shorted + the sensor reads
  "wet" even when it's dry). The operator checks the
  rain sensor's wiring + replaces the sensor if
  necessary.

### §9.5 Sleep mode doesn't suppress

**Symptom:** The operator sets `select.rc_mode` to
`sleep` + the §8.1 + §8.2 auto-fan automations still
fire + the fan runs overnight.

**Causes:**
- The mode/automation-builder recipe (Wave 2 #23) is
  not wired (the `select.rc_mode` tile does not
  exist). The operator checks Settings → Devices &
  Services → mode/automation-builder + verifies the
  tile exists.
- The §8.1 + §8.2 automations' CONDITION does NOT
  include `select.rc_mode != sleep` (the condition is
  missing). The operator adds the condition to the
  §8.1 + §8.2 automations.
- The `select.rc_mode` tile is set to `home` / `away` /
  `stealth` (not `sleep`). The operator verifies the
  tile's state is `sleep`.

### §9.6 Fan-only airflow control doesn't reach the bathroom

**Symptom:** The operator wires the rooftop vent fan
+ the circulation fan + the bathroom exhaust fan into
the umbrella + the umbrella's §8.1 + §8.2 + §8.3
automations control the rooftop vent fan + the
circulation fan but NOT the bathroom exhaust fan.

**Causes:**
- The bathroom exhaust fan is wired as a separate
  downstream `fan.*` entity (RoamCore does NOT own the
  bathroom exhaust fan; the operator must wire the
  bathroom exhaust fan into the umbrella manually via
  the operator's chosen path's upstream integration +
  configure the bathroom exhaust fan's automation
  separately).
- The downstream linkage is not wired (the operator's
  chosen path's upstream integration for the bathroom
  exhaust fan is not installed). The operator checks
  the bathroom exhaust fan's upstream integration +
  verifies the upstream `fan.*` entity exists.
- The circulation-fan template is missing (the operator
  has a single upstream `fan.*` entity that combines
  the rooftop vent fan + the circulation fan; the
  operator must create a separate `fan.*` entity for
  the circulation fan via the HA core `template:` fan
  wrapper).

## §10 Privacy

The umbrella does NOT collect any personally
identifiable information (PII) about the operator's fan
setup. The 8 `rc_fan_*` contract tiles are computed
locally on the HA instance; the upstream fan entity's
logs are operator-owned via the HA core logbook; no
RoamCore-side telemetry is sent.

The fan produces no telemetry beyond local on/off
state + speed; the rain sensor is a physical switch;
no cloud call home.

- **Path A Z-Wave / Zigbee / MQTT fan controllers** are
  fully local (no cloud call home; the fan controller
  communicates with the HA server over Z-Wave / Zigbee
  / MQTT).
- **Path B Bond Home / Hunter SIMPLEconnect / Tuya
  smart fans** require their own cloud auth for
  first-time setup (the operator pairs the fan with the
  vendor's app + creates an account), but subsequent
  runs are local (the HA server communicates with the
  fan via the HACS `bond` / `tuya` / `hunterdouglas_
  simplify` integrations over the local network + the
  cloud relay is only used for initial pairing).
- **Path C generic 12 V / 24 V fan + relay** is fully
  local (no cloud call home; the relay communicates
  with the HA server over Wi-Fi / Z-Wave).
- **Path D MaxxAir / Fan-Tastic / MAXXAIR Deluxe
  rooftop vent fan** requires the manufacturer-
  recommended integration's cloud auth for first-time
  setup (the operator pairs the fan with the
  manufacturer's app + creates an account), but
  subsequent runs are local (the HA server communicates
  with the fan over the local network + the cloud relay
  is only used for initial pairing).

The fan produces no telemetry beyond local on/off state
+ speed; the rain sensor is a physical switch; no cloud
call home.

## §11 Promoting to tier-a

To promote the fans connection from tier-b to tier-a,
the following would need to happen:

1. **Real Z-Wave fan controller + 12 V fan + Bond Home
   + MaxxAir + rain sensor on CI bench.** RoamCore would
   need a CI bench with a Z-Wave fan controller + a
   12 V fan + a Bond Home + a MaxxAir + a rain sensor +
   canned fixture responses for humidity / temperature /
   rain events. The bench is the canonical "integration
   test" target for fans.
2. **RoamCore-owned operator-wired setup flow.** RoamCore
   would need a setup flow for the fans integration that
   walks the operator through choosing Path A / B / C /
   D + declaring the upstream entities + the rain-sensor
   safety block. The setup flow is the canonical
   "operator-wired" affordance that distinguishes
   tier-b from tier-a.
3. **Integration tests asserting:**
   - The §8.1 auto-fan-on-humidity-high automation
     fires when `sensor.rc_hvac_interior_humidity`
     rises above 65% (a canned fixture response of
     `humidity: 70` triggers the automation + the
     automation calls `fan.turn_on` with `percentage:
     50` on the chosen upstream fan entity).
   - The §8.2 auto-fan-on-temperature-high automation
     fires when `sensor.rc_hvac_interior_temperature`
     rises above 28°C (a canned fixture response of
     `temperature: 30` triggers the automation + the
     automation calls `fan.turn_on` with `percentage:
     75` on the chosen upstream fan entity).
   - The §8.3 manual override via
     `button.rc_fan_run_now_15min` runs the fan for
     15 minutes (a button press fires the automation +
     the automation calls `fan.turn_on` with
     `percentage: 50` + a 15-minute timer calls
     `fan.turn_off`).
   - The §8.4 rain-sensor hard-block fires when the
     rain sensor trips (a canned fixture response of
     `rain_sensor: on` triggers the automation + the
     automation calls `fan.turn_off` on the chosen
     upstream fan entity + calls `cover.close_cover`
     on the upstream cover entity if Path D).
   - The §8.5 Sleep mode suppression suppresses the
     §8.1 + §8.2 auto-fan automations when
     `select.rc_mode` is in `sleep` mode (a canned
     fixture response of `mode: sleep` blocks the
     §8.1 + §8.2 automations).
   - The contract tiles reflect the current state of
     the fan setup (the operator's chosen upstream
     `fan.*` entity + the upstream `percentage`
     attribute + the upstream `preset_mode` attribute
     + the upstream `state` attribute + the rain
     sensor's `binary_sensor.*` entity).

The tier-a promotion is BLOCKED on the real Z-Wave fan
controller + 12 V fan + Bond Home + MaxxAir + rain
sensor bench; until the bench fixture lands, the fans
connection is tier-b.

## §12 Files in this connection + cross-references

### Files

- `connections/fans/connection.yml` — the source-of-
  truth manifest.
- `connections/fans/__init__.py` — the
  `DOMAIN = "fans"` marker for the audit.
- `connections/fans/README.md` — the folder overview.
- `connections/fans/docs/recipe.md` — the full howto
  (this file).
- `connections/fans/tests/test_connection_yml.py` —
  the manifest honesty checks.

### Cross-references

- **HA core `fan` integration** (the canonical umbrella;
  since 2022.x) —
  https://www.home-assistant.io/integrations/fan/
- **HA core `template:` fan wrapper** (the canonical
  Path C wrapping for relay-driven fans; since 2022.x)
  —
  https://www.home-assistant.io/integrations/template/
- **HA core `zwave_js` integration** (the canonical
  Path A1 Z-Wave fan controller integration; since
  2022.x) —
  https://www.home-assistant.io/integrations/zwave_js/
- **HA core `zha` integration** (the canonical Path A2
  Zigbee fan controller integration; since 2022.x) —
  https://www.home-assistant.io/integrations/zha/
- **HA core `mqtt` integration** (the canonical Path A3
  generic-tasmota-flashed fan controller integration;
  since 2022.x) —
  https://www.home-assistant.io/integrations/mqtt/
- **HA core Shelly integration** (the canonical Path C1
  Shelly 1 / Shelly Plus 1 wired to a 12 V fan
  integration; since 2022.x) —
  https://www.home-assistant.io/integrations/shelly/
- **HACS `bond` integration** (the canonical Path B1
  Bond Home RF-bridge + ceiling fan integration; HACS)
  — https://hacs.xyz/docs/integrations/active
- **HACS `tuya` integration** (the canonical Path B3
  Tuya Wi-Fi smart fan integration; HACS) —
  https://hacs.xyz/docs/integrations/active
- **HACS `hunterdouglas_simplify` integration** (the
  canonical Path B2 Hunter SIMPLEconnect Wi-Fi/BLE fan
  integration; HACS) —
  https://hacs.xyz/docs/integrations/active
- **HVAC basics** (the
  `sensor.rc_hvac_interior_temperature` +
  `sensor.rc_hvac_interior_humidity` tiles that the
  §8.1 + §8.2 auto-fan automations read from; Wave 3
  #49) — `connections/hvac-basics/`
- **Time-atomic** (the time-of-day / sunrise-sunset
  primitives used by the §8.5 Sleep mode suppression;
  Wave 3 #55) — `connections/time-atomic/`
- **Timezone geolocator** (the timezone primitive used
  by the §8.5 Sleep mode suppression's time-of-day
  schedule; Wave 3 #54) —
  `connections/timezone-geolocator/`
- **Cover entities** (the upstream cover integration
  for Path D rooftop vent covers; the §8.4 rain-sensor
  hard-block's `cover.close_cover` service call) —
  https://www.home-assistant.io/integrations/cover/
- **Mode/automation-builder recipe** (the
  `select.rc_mode` tile source of truth for the §8.5
  Sleep-mode suppression; Wave 2 #23) —
  `connections/smart-automations/`
- **Approach lights** (the canonical ON-LAN-only
  lighting scene that mirrors the Sleep-mode pattern;
  Wave 3 #52) — `connections/approach-lights/`
- **Motion-based lighting** (the canonical
  motion-triggered lighting pattern that mirrors the
  §8.1 humidity-triggered fan pattern; Wave 3 #53) —
  `connections/motion-based-lighting/`
- **NFC tags** (the optional "tag-trigger-manual-
  override" affordance that uses NFC scan events to
  trigger `button.rc_fan_run_now_15min`; Wave 3 #57)
  — `connections/nfc-tags/`
- **RoamCore entity naming** —
  `docs/reference/rc-entity-naming.md` (the
  `ventilation` subsystem was added by this slice)