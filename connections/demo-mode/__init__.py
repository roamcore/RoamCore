"""Demo mode — vendor-neutral demo values for missing
sensors + auto-disable on real sensor reconnect + hard-
block from controlling real hardware — tier-b recipe
connection.

Note on upstream wiring: tier-b connections don't ship a
RoamCore-owned operator-wired setup flow (a RoamCore
operator-wired wizard); instead, each path uses the
upstream integration's GUI flow (the HA core
`input_boolean` + `input_select` + `input_text` +
`input_number` helpers + the HA core `template:` sensor
wrapper + the HA core `template:` binary_sensor wrapper
all expose their own operator-wired setup flow + GUI
flow).

This module is a marker-only stub. Tier-b connections
don't ship native HA integration code; they publish a
recipe (docs/recipe.md) that walks the operator through
installing the upstream helpers + wiring the FOUR
operator-pickable demo scenarios:

  - Off — demo mode is disabled. Real sensor values (or
    "unknown" if sensors aren't wired) are shown. Default
    for operators with all hardware installed.

  - Battery demo — shows example battery / solar /
    inverter values as if a Victron GX were installed +
    reporting. Useful when the operator is wiring
    RoamCore without a real power system. The §3 demo
    scenario walks the operator through pointing the
    `sensor.rc_demo_mode_demo_value_battery_soc_percent`
    contract tile at a `template:` sensor that returns a
    realistic cycling value around 80% ± 10% so the
    dashboard looks alive.

  - Water tank demo — shows example fresh / grey / black
    tank levels as if the SeeLevel / Victron / generic
    resistive tank sensors were installed. Useful for
    showcasing the water UI without a real tank sensor.
    The §4 demo scenario walks the operator through
    pointing the
    `sensor.rc_demo_mode_demo_value_water_fresh_percent`
    contract tile at a `template:` sensor that cycles
    60% → 90% on a slow timer.

  - Connectivity demo — shows example Wi-Fi / LTE /
    Starlink state as if multiple upstream network
    integrations were installed. Useful for showcasing
    the network UI without real radios. The §5 demo
    scenario walks the operator through pointing the
    `binary_sensor.rc_demo_mode_demo_value_connectivity_
    lte_up` contract tile at a `template:` binary_sensor
    that flips TRUE / FALSE on a slow timer to simulate
    intermittent LTE.

The umbrella publishes the resulting data via the
upstream HA core `input_boolean` + `input_select` +
`input_text` + `input_number` helper entities (since
2022.x — have exposed the standard `input_boolean.toggle`
+ `input_select.select_option` + `input_text.set_value`
+ `input_number.set_value` services + the
`input_boolean` / `select` / `sensor` / `binary_sensor`
/ `button` domain entities) + the HA core `template:`
sensor wrapper (since 2022.x — wraps any upstream sensor
state into a derived `sensor.*` entity) + the HA core
`template:` binary_sensor wrapper (since 2022.x — wraps
any upstream sensor threshold into a derived
`binary_sensor.*` entity), then publishes the RoamCore
demo-mode contract tiles on top (the 11 contract
entities documented in connection.yml — 1 input_boolean
demo_mode_enabled + 1 select demo_mode_scenario + 1
sensor demo_mode_active_scenario + 1 binary_sensor
demo_mode_is_blocking_real_hardware + 1 sensor
demo_value_battery_soc_percent + 1 sensor
demo_value_water_fresh_percent + 1 binary_sensor
demo_value_connectivity_lte_up + 1 button
enable_battery + 1 button enable_water + 1 button
enable_connectivity + 1 button disable = 11 contract
entities).

The audit + boundary CI can detect a `demo-mode/` folder
that claims to be a connection via the `DOMAIN` constant
exported here. The wizard reads the manifest + recipe at
runtime.

The real per-operator demo-mode affordance path is:

    Operator-side choice of one of the FOUR demo
        scenarios (Off / Battery / Water / Connectivity)
        -> upstream entities (the HA core
           `input_boolean.rc_demo_mode_enabled` for the
           master enable; the HA core
           `select.rc_demo_mode_scenario` for the
           scenario selector; the HA core
           `sensor.rc_demo_mode_active_scenario`
           `template:` sensor for the resolved active
           scenario; the HA core
           `binary_sensor.rc_demo_mode_is_blocking_real_
           hardware` for the safety chip; the HA core
           `sensor.rc_demo_mode_demo_value_battery_soc_
           percent` `template:` sensor for the demo
           battery SoC; the HA core
           `sensor.rc_demo_mode_demo_value_water_fresh_
           percent` `template:` sensor for the demo
           fresh-water %; the HA core
           `binary_sensor.rc_demo_mode_demo_value_
           connectivity_lte_up` `template:` binary_sensor
           for the demo LTE upstream boolean; the HA core
           `button.rc_demo_mode_enable_battery` /
           `button.rc_demo_mode_enable_water` /
           `button.rc_demo_mode_enable_connectivity` /
           `button.rc_demo_mode_disable` for the
           operator-triggered one-tap enable / disable
           affordances)
        -> upstream signals (the operator's chosen real
           battery sensor — Victron / Renogy / generic
           shunt; the operator's chosen real tank sensor
           — SeeLevel / Garnet / Mopeka / generic
           resistive; the operator's chosen real LTE-up
           binary sensor — Peplink / Teltonika / Starlink
           / generic router; the operator-declared real-
           hardware target entities in
           `input_text.rc_demo_mode_real_hardware_targets`
           for the §9.2 never-controls-hardware guard)
        -> RoamCore contract layer (HA core `template:`
           sensor + binary_sensor + select + the
           operator's `input_boolean` / `input_select` /
           `input_text` / `input_number` for the contract
           tiles + the `command_line` integration for the
           upstream reachability probe)
        -> dashboard tiles + OpenClaw queries
            ("is demo mode enabled?",
             "what demo scenario is active?",
             "is demo mode blocking real hardware?",
             "what is the demo battery SoC?",
             "what is the demo fresh-water percentage?",
             "is the demo LTE upstream up?",
             "enable battery demo",
             "enable water demo",
             "enable connectivity demo",
             "disable demo mode")

    Safety interlocks (the recipe is the contract layer;
    the automation wrappers are documented in §8):
        -> The RoamCore demo-mode auto-disable automation
           is the §9.1 automation that fires when
           `input_boolean.rc_demo_mode_enabled` is ON AND
           ANY of the upstream real sensors (battery
           sensor + tank sensor + LTE-up sensor —
           whichever matches the picked scenario)
           transitions from `unavailable` / `unknown` to
           a real value. The automation clears the enable
           toggle + resets the scenario selector to Off +
           writes an audit-log entry + fires a
           notification warning the operator that demo
           mode has been auto-disabled.
        -> The RoamCore never-controls-actual-hardware
           automation is the §9.2 automation that fires
           when ANY `script.*` / `automation.*` action
           tries to call a `switch.turn_on` /
           `switch.turn_off` / `light.turn_on` /
           `light.turn_off` / `climate.set_*` service
           while `input_boolean.rc_demo_mode_enabled` is
           ON AND the target entity is one of the "real
           hardware" entities the operator has flagged in
           their `input_text.rc_demo_mode_real_hardware_
           targets`. The automation BLOCKS the service
           call + logs a security-style audit entry +
           flips `binary_sensor.rc_demo_mode_is_blocking_
           real_hardware` to TRUE + fires a critical
           notification.
        -> The RoamCore blocks-remote-access automation
           is the §9.3 automation that fires when a
           remote-access session attempts to interact
           with the dashboard while
           `input_boolean.rc_demo_mode_enabled` is ON.
           The automation surfaces a "demo mode is ON —
           values are not real" banner in the remote-
           access dashboard + adds the demo-mode-active
           flag to the remote-access session metadata +
           (if the operator's remote-access setup supports
           it) refuses write-capable actions until demo
           mode is disabled.
        -> The RoamCore audit-log-entry automation is the
           §9.4 automation that fires when
           `input_boolean.rc_demo_mode_enabled` flips
           from OFF to ON OR from ON to OFF. The
           automation writes an audit-log entry with the
           scenario selector value + the operator
           identity (if the remote-access session tracks
           it) + the timestamp + the reason.
        -> The RoamCore operator-only-guard automation is
           the §9.5 automation that fires when a non-
           operator source (a sensor auto-change / an
           automation script / a remote-access non-
           operator session) tries to flip
           `input_boolean.rc_demo_mode_enabled`. The
           automation BLOCKS the change + writes an
           audit-log entry + fires a critical
           notification.

    Cross-references:
        -> The HA core `input_boolean` + `input_select`
           + `input_text` + `input_number` helper
           entities are the canonical umbrella (since
           2022.x — expose the standard contract).
        -> The HA core `template:` sensor wrapper is the
           canonical active-scenario + battery-demo +
           water-demo derivation (since 2022.x).
        -> The HA core `template:` binary_sensor wrapper
           is the canonical blocking-real-hardware +
           connectivity-demo derivation (since 2022.x).
        -> The time-atomic Wave 3 #55 connection cross-
           references the time-of-day primitives used by
           the §9.4 audit-log entry's timestamp.
        -> The remote-access Wave 3 #58 connection cross-
           references the VPN primitive used by the §9.3
           blocks-remote-access guard.
        -> The approach lights Wave 3 #52 connection
           cross-references the §9.3 blocks-remote-
           access guard's dashboard banner pattern.
        -> The fans Wave 3 #59 connection cross-
           references the §9.2 never-controls-actual-
           hardware guard's fan-protection cross-
           reference (the guard protects real fans from
           being toggled by demo-mode values).
        -> The leveling Wave 3 #60 connection cross-
           references the §9.5 operator-only-guard's
           levelling-jack protection cross-reference (the
           guard prevents a non-operator source from
           enabling demo mode while levelling jacks are
           active).
        -> The mode Wave 3 #61 connection cross-
           references the §9.4 audit-log entry's mode-
           change cross-reference (the guard surfaces
           demo-mode transitions on the mode-change
           notification timeline).

See docs/recipe.md for the full howto (HA core
`input_boolean` + `input_select` + `input_text` +
`input_number` helper install + HA core `template:`
sensor wrapper install + HA core `template:`
binary_sensor wrapper install + the FOUR operator-
pickable demo scenarios + the 11 `rc_demo_mode_*`
contract tiles + the FIVE §9 MANDATORY automations +
the 6 §10 troubleshooting entries + privacy + tier-a
promotion outline).
"""

DOMAIN = "demo_mode"