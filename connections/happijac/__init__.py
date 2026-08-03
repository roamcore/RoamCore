"""Happijac bed lift (van bed up/down control) — tier-b recipe connection.

This module is a marker-only stub. Tier-b connections don't ship native
HA integration code; they publish a recipe (docs/recipe.md) that walks
the user through setting up bed lift control on the van (Path A —
ESPHome custom `cover:` component for ESPHome-friendly installs, OR
Path B — Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano Switch
pair + HA core `template:` cover for relay-friendly installs), and
exposes the resulting data via the upstream ESPHome or HA core
integrations, then publishes the RoamCore bed-lift contract tiles on
top (`rc_bed_lift_*` tiles: a `cover.rc_bed_lift_position` with
open/close/stop semantics + 2× `binary_sensor.rc_bed_lift_*_limit` +
a `binary_sensor.rc_bed_lift_moving` + a `sensor.rc_bed_lift_position_pct`
+ a `binary_sensor.rc_bed_lift_safety_ok` (limit-sanity aggregate:
false if both limits report true simultaneously — wiring fault) + 3×
`button.rc_bed_lift_*` (lift / lower / stop) + a
`binary_sensor.rc_bed_lift_obstruction_detected` + a
`binary_sensor.rc_bed_lift_low_voltage_lockout` + a
`select.rc_bed_lift_mode`).

The audit + boundary CI can detect a `happijac/` folder that claims
to be a connection via the `DOMAIN` constant exported here. The
wizard reads the manifest + recipe at runtime.

The real per-operator bed-lift affordance path is:

    Operator-side motor control source (Path A ESPHome custom `cover:`
        component handles the device-side GPIO + 2× outputs for the
        relay coils + 2× binary_sensor inputs for the limit
        microswitches + an optional ADC input for the CT-clamp
        current sensor + exposes cover.bed_lift upstream via
        the ESPHome integration's GUI flow
        since 2023.x;
        OR Path B Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano
        Switch pair auto-discovered by HA via the `shelly` integration
        since 2019.x, with 2× switch.shelly_*_relay entities exposed
        upstream; the operator wires the limit microswitches to either
        the Shelly dry-contact inputs OR separate GPIO-to-WiFi sensors)
        -> upstream cover.bed_lift (Path A) OR upstream switch.shelly_*
           _relay entities (Path B) + binary_sensor.shelly_*_dry_contact
           entities for limits
        -> RoamCore contract layer (HA core `template:` cover + template
           binary_sensors + template select that synthesizes the
           rc_bed_lift_* contract tiles from the upstream entities)
           (cover.rc_bed_lift_position,
            binary_sensor.rc_bed_lift_up_limit,
            binary_sensor.rc_bed_lift_down_limit,
            binary_sensor.rc_bed_lift_moving,                # derived from cover.rc_bed_lift_position state == opening/closing
            sensor.rc_bed_lift_position_pct,                # derived from cover.rc_bed_lift_position current_position
            binary_sensor.rc_bed_lift_safety_ok,            # NOR of (up_limit AND down_limit) — false on wiring fault
            button.rc_bed_lift_lift,                        # explicit "lift" button affordance for agent + automations
            button.rc_bed_lift_lower,                       # explicit "lower" button affordance
            button.rc_bed_lift_stop,                        # explicit "stop" button affordance
            binary_sensor.rc_bed_lift_obstruction_detected, # current-clamp based for Path A; motor-stall heuristic for Path B
            binary_sensor.rc_bed_lift_low_voltage_lockout,  # TRUE when sensor.rc_power_battery_soc < 20 % OR shore disconnected AND battery low (cross-references Victron connections/victron/ recipe)
            select.rc_bed_lift_mode)                        # auto | manual_only | disabled — operator-tunable lockout mode
        -> dashboard tiles + OpenClaw queries
            ("lift the bed", "lower the bed", "stop the bed",
             "what's the bed position?", "is the bed safe?",
             "is the bed moving?", "is the bed obstructed?",
             "is the bed low-voltage locked?", "set bed mode")

    Safety interlocks (MANDATORY before first use — operator must wire
    each one per the recipe §6):
        -> limit-switch sanity: binary_sensor.rc_bed_lift_safety_ok
           is FALSE whenever both up_limit AND down_limit report TRUE
           simultaneously (mechanically impossible — wiring fault;
           the cover template blocks any motion command until the
           wiring is fixed and the operator presses
           button.rc_bed_lift_stop + acknowledges)
        -> low-voltage lockout: binary_sensor.rc_bed_lift_low_voltage_
           lockout is TRUE whenever sensor.rc_power_battery_soc < 20 %
           (cross-references the Victron `connections/victron/`
           recipe; downstream MotionRequested commands are rejected
           until SOC recovers OR shore is reconnected)
        -> obstruction detection: binary_sensor.rc_bed_lift_obstruction_
           detected is TRUE whenever the CT-clamp current sensor (Path
           A) reads >5 A sustained for >2 s (motor is stalled against
           an obstruction) OR the motor-stall heuristic (Path B;
           upstream switch.shelly_*_relay current sensor reading >5 A
           sustained for >2 s with no limit-switch change in the
           expected direction) trips
        -> mode-aware lockouts: Stealth silent hours STOP any in-
           progress bed motion at the start of silent hours + suppress
           any auto-lift scheduling; Sleep mode locks the bed down
           overnight via a 23:00 auto-lower (only when mode is `auto`);
           Boost mode disables mode-aware lockouts for service work —
           the cover template accepts motion commands regardless of
           mode time of day

See docs/recipe.md for the full howto (Path A ESPHome YAML wiring for
the outputs / binary_sensors / cover + the HA-side template cover
that synthesizes the contract layer, Path B Shelly / Shelly Plus /
Zooz ZEN17 / Aeotec Nano Switch + HA template cover wiring + the
limit binary_sensor + the current_based_obstruction_detection block,
the four safety interlocks in full, six §7 automations: Stealth
auto-stop / Sleep lock-down / Boost disable-mode-aware-lockouts /
low-voltage lockout when SOC < 20 % / obstruction detected → stop +
alert / mode-aware scheduling, eight §8 troubleshooting entries
including "bed not moving" (relay polarity + coil voltage), "one
limit stuck" (replace microswitch), "both limits reporting true
simultaneously" (wiring fault), "bed moves up but not down" (NC/NO
mis-wire), "obstruction false-positive" (tune current threshold),
"low-voltage lockout stuck on after charging" (cross-check Victron
SOC), "Shelly not discovered" (mDNS / IGMP snooping on the LAN
switch), and "ESPHome device offline" (check Wi-Fi + USB-C power),
privacy, tier-a promotion outline).
"""

DOMAIN = "happijac"
