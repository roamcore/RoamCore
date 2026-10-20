"""Alternator charge control (Wakespeed / smart regulator — vendor-
neutral alternator charge umbrella for HA — rooftop vent fans /
circulation fans / bathroom exhaust fans sit OUTSIDE this slice; the
alternator-side regulator control lives here) — tier-b recipe
connection.

Note on upstream wiring: tier-b connections don't ship a RoamCore-
owned operator-wired setup flow (a RoamCore `config_flow`-style
wizard); instead, each path uses the upstream integration's GUI
flow (the HA core `mqtt` integration + the HA core Shelly
integration + the HA core `victron` integration + the HA core
`template:` switch + sensor + binary_sensor wrappers + the HA core
`input_boolean` + `input_text` + `input_number` + `input_select` +
`input_button` helpers + the upstream vendor integrations (Wakespeed
Link + Balmar Smartlink + Renogy BT-2 + REDARC RedVision + Sterling
BMS Link + EP-Power EP Link + ARCO Zeus app) all expose their own
operator-wired setup flow + GUI flow).

This module is a marker-only stub. Tier-b connections don't ship
native HA integration code; they publish a recipe
(docs/recipe.md) that walks the operator through installing ONE OF
the FOUR operator-pickable alternator charge paths:

  - Path A — Smart alternator regulator linked to a Victron /
    Renogy / REDARC / Sterling / Balmar / EP-Power DC-DC charger
    with its own regulator control (the recommended path for
    operators whose alternators already charge through a DC-DC
    charger). Path A covers two sub-flavors:

    - Path A1 — Victron Cerbo GX + DC-DC charger via the HA core
      `victron` integration (the canonical Victron integration
      since 2022.x — exposes a GUI flow for the operator to add
      the Cerbo GX to HA + view the resulting `switch.*` (charge
      enable) + `sensor.*` (voltage + current + temperature +
      fault) on the DC-DC charger; the recipe wires the upstream
      entities through a `template:` switch + `template:` sensor +
      `template:` binary_sensor wrapper into the
      `rc_power_alternator_*` contract tiles).

    - Path A2 — Renogy / REDARC / EP-Power / Sterling / Balmar DC-DC
      charger via the HA core `mqtt` integration (since 2022.x —
      exposes a GUI flow for the operator to add the vendor's
      Bluetooth-to-MQTT bridge topic to HA + view the resulting
      `switch.*` + `sensor.*` + `binary_sensor.*` entities). The
      vendor may also expose a `number.*` for the target voltage
      setpoint + a `select.*` for the charge mode (off / auto /
      boost / float / desulfation) — the recipe walks through
      wiring those too.

  - Path B — Generic smart alternator regulator exposed over MQTT
    by the vendor's bridge (Wakespeed WS500 / Balmar MC-618 /
    Sterling Regulated Advanced Alternator-to-Battery charger /
    Renogy Battery-to-Battery / REDARC BCDC / EP-Power B2B / ARCO
    Zeus / OEM alternator regulator with a CAN-to-MQTT bridge
    such as Wakespeed's WS Link / Sterling's BMS Link / Balmar's
    Smartlink / Renogy's BT-2 / REDARC's RedVision / EP-Power's
    EP Link / a Signal K gateway on the boat's NMEA 2000 backbone).
    Path B is the canonical "use the upstream vendor's MQTT
    bridge" path for operators whose regulator ships with a
    Bluetooth / Wi-Fi / CAN bridge. The HA core `mqtt`
    integration (since 2022.x — exposes a GUI flow for the
    operator to configure the regulator's MQTT topic in HA)
    surfaces the regulator's enable/disable + target voltage +
    charge current + battery temperature + fault state as a
    `switch.*` + `sensor.*` + `binary_sensor.*` + `number.*` +
    `select.*` family of upstream entities.

  - Path C — Relay / GPIO switch between the alternator field
    wire and a plain smart charger (the minimum-viable path for
    operators with no smart regulator + no MQTT bridge — a plain
    externally-regulated alternator whose field excitation wire
    can be turned off). Path C covers two sub-flavors:

    - Path C1 — Shelly 1 / Shelly Plus 1 wired to the alternator's
      field excitation wire + the HA core Shelly integration
      (since 2022.x — exposes a GUI flow for the operator to add
      the Shelly 1 / Shelly Plus 1 to HA + view the resulting
      `binary_switch.*` entity). The operator creates a `template:`
      switch wrapping the relay state into a virtual
      `switch.*` entity + a `template:` sensor for charge current
      derived from `sensor.rc_power_battery_current_a` (from the
      Victron `connections/victron/` recipe).

    - Path C2 — ESPHome / Tasmota GPIO relay driven by an ESP32 /
      ESP8266 node connected to the alternator's field excitation
      wire + flashed with ESPHome / Tasmota + the upstream
      integration (the ESPHome integration since 2022.x surfaces
      the relay as a `switch.alternator_field` entity OR the HA
      core `mqtt` integration surfaces the Tasmota-flashed relay
      as a `switch.*` entity).

  - Path D — Read-only ignition-signal-only + no control (the
    alternator is dumb / the operator does NOT want to control
    the alternator at all — just knows when the engine is running
    via `binary_sensor.rc_vehicle_engine_running` from the
    vehicle-related connection slices + surfaces a single "should
    we be charging now?" advisory tile). The operator may use
    Path D as a stepping stone to Path A / Path B / Path C later.
    Path D requires only the ignition signal — the upstream entity
    is `binary_sensor.rc_vehicle_engine_running` (from the
    leveling or mode connection) OR a GPIO on an ESPHome node +
    a voltage divider on the alternator's D+ / IGN wire.

The umbrella publishes the resulting data via the upstream HA core
`mqtt` integration (since 2022.x — has exposed a GUI flow for the
operator to configure a vendor-bridged regulator's MQTT topic) +
the HA core Shelly integration (since 2022.x — has exposed a GUI
flow for the operator to add a Shelly 1 / Shelly Plus 1 to HA) +
the HA core `victron` integration (since 2022.x — has exposed a
GUI flow for the operator to add a Victron Cerbo GX to HA) + the
HA core `template:` switch + `template:` sensor + `template:`
binary_sensor wrappers (since 2022.x — wraps any upstream `switch.*`
+ `sensor.*` + `binary_sensor.*` entities into derived entities
that expose the standard contract) + the HA core `input_boolean` +
`input_text` + `input_number` + `input_select` + `input_button`
helpers (since 2022.x — for the operator-facing affordances), then
publishes the RoamCore alternator contract tiles on top (the 8
contract entities documented in connection.yml — 1 binary_sensor
charging_enabled + 1 select charge_mode + 1 sensor target_voltage_v
+ 1 sensor charge_current_a + 1 binary_sensor
temp_compensation_active + 1 binary_sensor fault + 1 sensor
last_trigger_reason + 1 button manual_override).

The audit + boundary CI can detect a `alternator-charge-control/`
folder that claims to be a connection via the `DOMAIN` constant
exported here. The wizard reads the manifest + recipe at runtime.

The real per-operator alternator-side charge affordance path is:

    Operator-side choice of ONE path (Path A — DC-DC-charger-
        linked regulator via the HA core `victron` integration
        OR the HA core `mqtt` integration; Path B — vendor-
        bridged smart regulator over the HA core `mqtt`
        integration; Path C — relay / GPIO switch via the HA
        core Shelly integration OR an ESPHome / Tasmota GPIO
        node; Path D — read-only ignition-signal-only + no
        control via upstream `binary_sensor.rc_vehicle_engine_
        running`)
        -> upstream entity (HA core `mqtt` integration's
           `switch.*` + `sensor.*` + `binary_sensor.*` for
           Path A2 / Path B; the HA core `victron` integration's
           `switch.*` + `sensor.*` + `binary_sensor.*` for
           Path A1; the HA core Shelly integration's
           `binary_switch.*` for Path C1; the upstream GPIO
           `binary_sensor.*` for Path D)
        -> RoamCore contract layer (HA core `template:` switch
           + sensor + binary_sensor + the operator's
           `input_boolean` / `input_text` / `input_number` /
           `input_select` / `input_button` for the contract tiles
           + the upstream `command_line` integration for the
           upstream reachability probe)
           -> dashboard tiles + OpenClaw queries
              ("is the alternator charging?", "alternator charge
               mode", "alternator target voltage", "alternator
               charge current", "is the alternator temperature-
               compensating?", "is the alternator faulting?",
               "alternator last trigger reason", "alternator
               manual override")

Safety interlocks (MANDATORY before first use — operator must wire
each one per the recipe §8):
    -> ignition-on charge enable: the §8.1 ignition-on
       automation enables charging when `binary_sensor.rc_
       vehicle_engine_running` is TRUE AND the operator's
       chosen charge_mode allows it (`select.rc_power_
       alternator_charge_mode` is `auto` / `boost` / `float` /
       `desulfation`)
    -> SOC-low boost: the §8.2 SOC-low boost automation enables
       boost charging when `sensor.rc_power_battery_soc` (from
       the Victron `connections/victron/` recipe) falls below
       the operator's chosen threshold (default 60 %) — boost
       runs while the alternator is on + the engine is running
    -> battery-cold temperature-compensation: the §8.3
       temperature-compensation automation lowers the
       regulator's target voltage setpoint when the battery
       temperature probe reads cold (< 0°C) OR hot (> 45°C) —
       the `binary_sensor.rc_power_alternator_temp_
       compensation_active` tile flips to TRUE
    -> mode-aware Stealth / Sleep suppressions: the §8.4 mode-
       aware Stealth / Sleep suppressions block charging when
       `select.rc_mode` (from the `connections/mode/` recipe)
       is `stealth` AND the operator has flagged the
       alternator as noisy (the operator's `input_boolean.rc_
       power_alternator_noisy_in_stealth`); the same path
       applies to `sleep` mode
    -> protect_battery mode: the §8.5 protect_battery mode
       disables charging when `sensor.rc_power_battery_soc` is
       below the operator's chosen protect_battery threshold
       (default 20 %) — preserves the battery for critical
       loads
    -> fault-block: the §8.6 fault-block automation forces
       charging OFF when `binary_sensor.rc_power_alternator_
       fault` is TRUE (the regulator reported over-temp /
       over-voltage / communication lost / BMS lockout) +
       notifies the operator's phone via the HA Companion app +
       writes `sensor.rc_power_alternator_last_trigger_reason =
       fault_blocked`

Cross-references (the §8 automations read from these tiles in
upstream connections):
    -> Victron (the source of `sensor.rc_power_battery_soc` +
       `sensor.rc_power_battery_current_a` + `sensor.rc_power_
       battery_temperature_c` for the §8.1 / §8.2 / §8.3 / §8.5
       automations): `connections/victron/`
    -> mode/automation-builder (the source of `select.rc_mode`
       for the §8.4 mode-aware Stealth / Sleep suppressions):
       `connections/mode/`
    -> leveling (the source of `binary_sensor.rc_vehicle_
       engine_running` for the §8.1 ignition-on enable):
       `connections/leveling/`
    -> heated floors (the canonical low-voltage lockout pattern
       mirrored in §8.5 protect_battery mode when SOC <
       threshold):
       `connections/heated-floors/`
    -> deadbolts (the canonical "blocks on fault" automation
       pattern mirrored in §8.6 fault-block): `connections/
       deadbolts/`
    -> fans (the canonical mode-aware Stealth / Sleep
       suppression pattern mirrored in §8.4): `connections/
       fans/`

See docs/recipe.md for the full howto (Path A DC-DC-charger-linked
regulator wiring + Path B vendor-MQTT-bridged regulator wiring +
Path C field-relay wiring + Path D read-only ignition-signal-only,
eight §8 automations in full, eight §9 troubleshooting entries,
privacy, tier-a promotion outline).
"""

DOMAIN = "alternator-charge-control"
