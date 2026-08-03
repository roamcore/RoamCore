"""Fans (vendor-neutral fan-controller umbrella for HA — rooftop vent
fans + circulation fans + bathroom exhaust fans, the operator picks
ONE path) — tier-b recipe connection.

Note on upstream wiring: tier-b connections don't ship a RoamCore-
owned operator-wired setup flow (a RoamCore `config_flow`-style
wizard); instead, each path uses the upstream integration's GUI
flow (the HA core `fan` integration + the HA core `zwave_js`
integration + the HA core `zha` integration + the HA core `mqtt`
integration + the HACS `bond` integration + the HACS `tuya`
integration + the HACS `hunterdouglas_simplify` integration +
the HA core Shelly integration all expose their own operator-
wired setup flow + GUI flow).

This module is a marker-only stub. Tier-b connections don't ship
native HA integration code; they publish a recipe
(docs/recipe.md) that walks the operator through installing ONE OF
the FOUR operator-pickable fan-controller paths:

  - Path A — Smart fan controllers (Z-Wave / Zigbee / MQTT fan
    controllers wired to 12 V / 24 V fans + the HA core
    `zwave_js` integration OR the HA core `zha` integration
    OR the HA core `mqtt` integration). Path A covers three
    sub-flavors:

    - Path A1 — Z-Wave fan controller. The operator installs
      a Z-Wave fan controller (Zooz ZEN17 + Aeotec Nano
      Switch + Inovelli LZW42 are common choices for 12 V /
      24 V fans) + the HA core `zwave_js` integration
      (since 2022.x — exposes a GUI flow for the operator
      to add the Z-Wave fan controller to the HA server's
      Z-Wave network + view the resulting `binary_switch.*`
      OR `fan.*` entity from the operator's Z-Wave network).
      The HA core `fan` integration has exposed a
      `set_percentage` service + a `percentage` attribute +
      a `preset_mode` attribute since 2022.x; the operator
      uses `fan.set_percentage` to control the fan speed +
      uses the `percentage` attribute to read the current
      speed.

    - Path A2 — Zigbee fan controller. The operator installs
      a Zigbee fan controller (generic-Zigbee fan
      controllers + the Tuya Zigbee fan family are common
      choices) + the HA core `zha` integration (since
      2022.x — exposes a GUI flow for the operator to add
      the Zigbee fan controller to the HA server's Zigbee
      network + view the resulting `fan.*` entity from the
      operator's Zigbee network). The HA core `fan`
      integration exposes the standard contract.

    - Path A3 — Generic-tasmota-flashed fan controller. The
      operator flashes Tasmota onto any 12 V / 24 V fan
      relay + the HA core `mqtt` integration (since
      2022.x — exposes a GUI flow for the operator to
      configure the Tasmota-flashed relay's MQTT topic) +
      the resulting `fan.*` entity from the MQTT topic.
      The HA core `fan` integration exposes the standard
      contract.

  - Path B — Wi-Fi / BLE smart fan (Bond Home + Hunter
    SIMPLEconnect + Tuya + the HACS `bond` integration +
    the HACS `tuya` integration + the HACS
    `hunterdouglas_simplify` integration). Path B covers
    three sub-flavors:

    - Path B1 — Bond Home RF-bridge + ceiling fan. The
      operator pairs the Bond Home hub to the
      RF-bridge-controlled ceiling fan (the operator's
      existing ceiling fan may already have a Bond Home
      RF-bridge controller retrofitted; the operator
      follows the Bond Home pairing instructions + adds
      the fan via the Bond Home app + installs the HACS
      `bond` integration (HACS — exposes a GUI flow for
      the operator to add the Bond Home hub to HA + view
      the resulting `fan.*` entity)). The HA core `fan`
      integration exposes the standard contract.

    - Path B2 — Hunter SIMPLEconnect (HunterDouglas
      SIMPLIFY) Wi-Fi/BLE fan. The operator installs the
      Hunter SIMPLEconnect app + pairs the fan + installs
      the HACS `hunterdouglas_simplify` integration (HACS
      — exposes a GUI flow for the operator to add the
      Hunter SIMPLEconnect fan to HA + view the resulting
      `fan.*` entity). The HA core `fan` integration
      exposes the standard contract.

    - Path B3 — Tuya Wi-Fi smart fan. The operator
      installs the Tuya Smart / Smart Life app + pairs
      the fan + installs the HACS `tuya` integration
      (HACS — exposes a GUI flow for the operator to add
      the Tuya Wi-Fi smart fan to HA + view the
      resulting `fan.*` entity). The HA core `fan`
      integration exposes the standard contract.

  - Path C — Generic 12 V / 24 V fan + relay (no smart
    fan controller — the operator wires a 12 V / 24 V
    ventilation fan + a Shelly 1 / Zooz ZEN17 / Aeotec
    Nano Switch relay + the HA core Shelly integration
    OR the HA core `zwave_js` integration OR the HA core
    `template:` fan wrapping the relay state into a
    virtual `fan.ventilation` entity that exposes the
    standard `percentage` + `preset_mode` + the
    `fan.set_percentage` service contract). Path C
    covers two sub-flavors:

    - Path C1 — Shelly 1 / Shelly Plus 1 wired to a 12 V
      fan + the HA core Shelly integration (since 2022.x
      — exposes a GUI flow for the operator to add the
      Shelly 1 / Shelly Plus 1 to HA + view the resulting
      `binary_switch.*` entity). The operator creates a
      `template:` fan wrapping the relay state into a
      virtual `fan.ventilation` entity that exposes the
      standard contract.

    - Path C2 — Zooz ZEN17 / Aeotec Nano Switch wired to
      a 24 V fan + the HA core `zwave_js` integration +
      the HA core `template:` fan wrapping the relay
      state into a virtual `fan.*` entity. The HA core
      `fan` integration exposes the standard contract.

  - Path D — All-in-one smart fan (MaxxAir / Fan-Tastic
    / MAXXAIR Deluxe rooftop vent fan + the HA core
    `fan` integration auto-discovery + the
    `fan.turn_on` / `fan.turn_off` / `fan.set_percentage`
    service mappings + the rain-sensor safety block +
    the upstream cover entity for the rooftop vent
    cover). The operator installs the rooftop vent fan
    per the manufacturer instructions + wires it into
    HA via the manufacturer-recommended integration
    (MaxxAir iFAN + Fan-Tastic Vent + MAXXAIR Deluxe all
    expose a vendor integration that surfaces as a
    `fan.*` entity + a `cover.*` entity for the
    automatic rain cover) + the recipe's rain-sensor
    safety block forces the fan OFF + the cover CLOSED
    when the rain sensor trips.

The umbrella publishes the resulting data via the upstream
HA core `fan` integration (since 2022.x — has exposed a
`set_percentage` service + a `percentage` attribute + a
`preset_mode` attribute + the `fan.turn_on` / `fan.turn_off`
/ `fan.toggle` / `fan.set_percentage` / `fan.set_preset_mode`
services + the `fan` domain since 2022.x) + the HA core
`template:` fan wrapper (since 2022.x — wraps any relay
state or upstream `fan.*` entity into a virtual `fan.*`
entity that exposes the standard `percentage` +
`preset_mode` + `fan.set_percentage` service contract) +
the HA core `zwave_js` integration (since 2022.x —
surfaces Z-Wave fan controllers like the Zooz ZEN17 +
Aeotec Nano Switch + Inovelli LZW42 as `fan.*` entities) +
the HA core `zha` integration (since 2022.x — surfaces
Zigbee fan controllers like generic-Zigbee fan
controllers + the Tuya Zigbee fan family as `fan.*`
entities) + the HACS `bond` integration (HACS — surfaces
Bond Home RF-bridge-controlled ceiling fans + Hunter
SIMPLEconnect fans as `fan.*` entities) + the HACS `tuya`
integration (HACS — surfaces Tuya Wi-Fi smart fans as
`fan.*` entities) + the HA core `mqtt` integration (since
2022.x — surfaces MQTT-driven fan controllers +
Tasmota-flashed fan controllers as `fan.*` entities), then
publishes the RoamCore fan contract tiles on top (the 8
contract entities documented in connection.yml — 1 fan
main + 1 sensor speed_percent + 1 select mode + 1
binary_sensor active + 1 sensor runtime_minutes_today +
1 sensor last_trigger_reason + 1 button run_now_15min +
1 binary_sensor rain_sensor_active).

The audit + boundary CI can detect a `fans/` folder that
claims to be a connection via the `DOMAIN` constant
exported here. The wizard reads the manifest + recipe at
runtime.

The real per-operator fan-controller affordance path is:

    Operator-side choice of ONE path (Path A — Z-Wave /
        Zigbee / MQTT fan controller via the HA core
        `zwave_js` integration OR the HA core `zha`
        integration OR the HA core `mqtt` integration; Path
        B — Wi-Fi / BLE smart fan via the HACS `bond`
        integration OR the HACS `tuya` integration OR the
        HACS `hunterdouglas_simplify` integration; Path C
        — generic 12 V / 24 V fan + relay via the HA
        core Shelly integration OR the HA core
        `zwave_js` integration + the HA core `template:`
        fan wrapper; Path D — all-in-one smart fan via
        the upstream manufacturer-recommended
        integration)
        -> upstream entity (HA core `fan` integration's
           `fan.*` entity for Path A / Path B / Path D;
           the HA core `template:` fan wrapper's
           `fan.ventilation` entity for Path C; the HA
           core `cover.*` entity for the rooftop vent
           cover in Path D; the upstream physical rain
           sensor's `binary_sensor.*` entity for the
           §8.4 rain-sensor hard-block)
        -> RoamCore contract layer (HA core `template:`
           sensor + binary_sensor + select + the
           operator's `input_boolean` / `input_text` /
           `input_select` / `input_button` / `input_number`
           for the contract tiles + the `command_line`
           integration for the upstream reachability
           probe)
        -> dashboard tiles + OpenClaw queries
            ("is the fan currently running?",
             "what speed is the fan at?",
             "what mode is the fan in?",
             "is the rain sensor blocking the fan?",
             "how long has the fan been running today?",
             "why was the fan last turned on?",
             "run the fan for 15 minutes now",
             "force the fan off because of rain")

    Safety interlocks (the recipe is the contract layer;
    the automation wrappers are documented in §8):
        -> The RoamCore auto-fan-on-humidity-high
           automation is the §8.1 automation that fires
           when `sensor.rc_hvac_interior_humidity` (from
           the HVAC basics Wave 3 #49 connection) rises
           above 65% AND the fan is not in `rain_safe`
           mode. The automation sets
           `select.rc_fan_mode` to `auto` + writes
           `sensor.rc_fan_last_trigger_reason = humidity`
           + calls the upstream `fan.turn_on` service
           with `percentage: 50` (med speed).
        -> The RoamCore auto-fan-on-temperature-high
           automation is the §8.2 automation that fires
           when `sensor.rc_hvac_interior_temperature`
           (from the HVAC basics Wave 3 #49 connection)
           rises above 28°C AND the fan is not in
           `rain_safe` mode. The automation sets
           `select.rc_fan_mode` to `auto` + writes
           `sensor.rc_fan_last_trigger_reason =
           temperature` + calls the upstream
           `fan.turn_on` service with `percentage: 75`
           (high speed).
        -> The RoamCore manual-override-via-button
           automation is the §8.3 automation that fires
           when the operator presses
           `button.rc_fan_run_now_15min`. The automation
           writes `sensor.rc_fan_last_trigger_reason =
           manual` + calls the upstream `fan.turn_on`
           service with `percentage: 50` (med speed) +
           fires a 15-minute timer that calls
           `fan.turn_off` after 15 minutes.
        -> The RoamCore rain-sensor-hard-block automation
           is the §8.4 automation that fires when
           `binary_sensor.rc_fan_rain_sensor_active`
           flips to TRUE. The automation calls
           `fan.turn_off` on the chosen upstream fan
           entity + calls `cover.close_cover` on the
           upstream cover entity if the operator has a
           rooftop vent with a cover (Path D — MaxxAir /
           Fan-Tastic / MAXXAIR Deluxe all expose an
           upstream `cover.*` entity for the automatic
           rain cover) + writes `select.rc_fan_mode =
           rain_safe` + notifies the operator's phone
           (via the HA Companion app) saying "Rain
           detected — fan forced OFF + cover forced
           CLOSED".
        -> The RoamCore Sleep-mode suppression automation
           is the §8.5 automation that SUPPRESSES the
           §8.1 + §8.2 auto-fan automations when
           `select.rc_mode` is in `sleep` mode (overnight
           camp where the fan noise is unwanted; the
           operator can still trigger the manual override
           via `button.rc_fan_run_now_15min`). The recipe
           §12 cross-references the mode/automation-
           builder recipe (Wave 2 #23) for the
           `select.rc_mode` tile.

    Cross-references:
        -> The HA core `fan` integration is the canonical
           umbrella (since 2022.x — exposes the standard
           contract).
        -> The HA core `template:` fan wrapper is the
           canonical Path C wrapping for relay-driven
           fans (since 2022.x).
        -> The HA core `zwave_js` integration is the
           canonical Path A1 Z-Wave fan controller
           integration (since 2022.x).
        -> The HA core `zha` integration is the canonical
           Path A2 Zigbee fan controller integration
           (since 2022.x).
        -> The HA core `mqtt` integration is the canonical
           Path A3 generic-tasmota-flashed fan
           controller integration (since 2022.x).
        -> The HACS `bond` integration is the canonical
           Path B1 Bond Home RF-bridge + ceiling fan
           integration (HACS).
        -> The HACS `tuya` integration is the canonical
           Path B3 Tuya Wi-Fi smart fan integration
           (HACS).
        -> The HACS `hunterdouglas_simplify` integration
           is the canonical Path B2 Hunter SIMPLEconnect
           Wi-Fi/BLE fan integration (HACS).
        -> The HVAC basics Wave 3 #49 connection
           cross-references the
           `sensor.rc_hvac_interior_temperature` +
           `sensor.rc_hvac_interior_humidity` tiles
           that the §8.1 + §8.2 auto-fan automations
           read from.
        -> The time-atomic Wave 3 #55 connection
           cross-references the time-of-day / sunrise-
           sunset primitives used by the §8 Sleep mode
           suppression.
        -> The mode/automation-builder recipe Wave 2 #23
           cross-references the `select.rc_mode` tile
           (the Sleep-mode suppression source of truth).
        -> The cover entities (the upstream cover
           integration for Path D rooftop vent covers)
           cross-reference the §8.4 rain-sensor hard-
           block cover-close service call.

See docs/recipe.md for the full howto (HA core `fan`
integration install + HA core `template:` fan wrapper +
HA core `zwave_js` integration + HA core `zha`
integration + HA core `mqtt` integration + HACS `bond`
integration + HACS `tuya` integration + HACS
`hunterdouglas_simplify` integration + Path A Z-Wave /
Zigbee / MQTT fan controller wiring + Path B Wi-Fi / BLE
smart fan wiring + Path C generic 12 V / 24 V fan + relay
wiring + Path D all-in-one smart fan wiring + the 8
`rc_fan_*` contract tiles + the FIVE §8 automations +
the 6 §9 troubleshooting entries + privacy + tier-a
promotion outline).
"""

DOMAIN = "fans"