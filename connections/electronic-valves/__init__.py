"""Electronic valves + auto tank switching — tier-b recipe connection.

This module is a marker-only stub. Tier-b connections don't ship native
HA integration code; they publish a recipe (docs/recipe.md) that walks
the user through setting up fresh-inlet / grey-drain / aux-tank valve
control on the van (Path A — ESPHome valve node + 12 V / 24 V
electrically-actuated valves (latching solenoid / motorized ball /
proportional) wired into GPIO + a safe driver (relay module / MOSFET
H-bridge / BTS7960 43 A / IBOM / etc.) per valve + valve-position
feedback (limit switch or current sense); the ESPHome YAML exposes
`switch.<node>_valve_fresh_inlet` +
`switch.<node>_valve_grey_drain` +
`switch.<node>_valve_aux_tank` + the
`binary_sensor.<node>_valve_*_position` feedback; OR Path B — generic
relay (Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano Switch)
wired into the 12 V / 24 V valve coils + HA core `template:` valve or
`switch:` template + valve-position feedback binary_sensor), and
exposes the resulting data via the upstream switch / valve / template
integration, then publishes the RoamCore water valve contract tiles
on top (`rc_water_valve_*` tiles: the 17 contract entities documented
in connection.yml — 3 switch state tiles (fresh_inlet_state /
grey_drain_state / aux_tank_state) + 3 binary_sensor position tiles
(fresh_inlet_position / grey_drain_position / aux_tank_position) +
5 binary_sensor aggregate tiles (any_moving /
auto_tank_switch_active / leak_detected_lockout /
freeze_risk_lockout / low_voltage_lockout) + 2 select tiles
(active_tank: auto / primary / aux; mode: auto / manual_only /
stealth_only / silent / disabled) + 2 number configuration tiles
(auto_close_grey_min / low_voltage_lockout_soc_pct) + 2 button tiles
(open_all / close_all) + 1 binary_sensor lockout aggregate).

The audit + boundary CI can detect a `electronic-valves/` folder
that claims to be a connection via the `DOMAIN` constant exported
here. The wizard reads the manifest + recipe at runtime.

The real per-operator electronic valve affordance path is:

    Operator-side electronic valve source (Path A — ESPHome valve
        node + 12 V / 24 V electrically-actuated valves + safe
        drivers per valve + valve-position feedback (limit switch
        or current sense); the ESPHome integration exposes a GUI
        flow since 2023.x; the ESPHome YAML exposes
        switch.<node>_valve_fresh_inlet +
        switch.<node>_valve_grey_drain +
        switch.<node>_valve_aux_tank +
        binary_sensor.<node>_valve_*_position; OR Path B — generic
        relay (Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano
        Switch) wired into the 12 V / 24 V valve coils + the Shelly
        integration exposes a GUI flow since 2022.x + the HA
        `template:` integration translates the relay state into a
        valve / switch template + valve-position feedback
        binary_sensor)
        -> upstream entity (switch.<valve>_<role> for the operator's
           valve entity; binary_sensor.<valve>_<role>_position for
           the valve-position feedback; valve.<valve>_<role> for
           proportional valves (Path A `valve` component or Path B
           HA `template:` valve))
        -> RoamCore contract layer (HA core `template:` switch /
           binary_sensor / select / number / button that maps the
           upstream entities into the 17 `rc_water_valve_*`
           contract tiles — rc_water_valve_fresh_inlet_state +
           rc_water_valve_grey_drain_state +
           rc_water_valve_aux_tank_state +
           rc_water_valve_fresh_inlet_position +
           rc_water_valve_grey_drain_position +
           rc_water_valve_aux_tank_position +
           rc_water_valve_any_moving +
           rc_water_valve_auto_tank_switch_active +
           rc_water_valve_leak_detected_lockout +
           rc_water_valve_freeze_risk_lockout +
           rc_water_valve_active_tank +
           rc_water_valve_mode +
           rc_water_valve_auto_close_grey_min +
           rc_water_valve_low_voltage_lockout_soc_pct +
           rc_water_valve_low_voltage_lockout +
           rc_water_valve_open_all +
           rc_water_valve_close_all)
        -> dashboard tiles + OpenClaw queries
            ("open fresh inlet", "close grey drain",
             "switch to aux tank", "auto tank switching on/off",
             "what valves are open?", "is auto-close grey enabled?",
             "freeze risk — close all valves",
             "leak detected — close all valves",
             "are valves locked out by low voltage?",
             "set auto-close grey to 15 minutes")

    Safety interlocks (MANDATORY before first use — operator must
    wire each one per the recipe §7):
        -> Leak detected: when ANY leak sensor reports water,
           close fresh inlet (so the leak isn't continuously fed
           from the fresh tank) + open grey drain (so the leak
           drips onto the floor / ground rather than pooling in
           the grey tank which then overflows onto the road).
           Cross-reference `binary_sensor.rc_water_leak_detected`
           from the water-tanks Wave 3 #50 connection.
        -> Freeze risk: when
           `sensor.rc_water_fresh_temperature_c` < 2 °C, fire
           `binary_sensor.rc_water_freeze_risk` TRUE + close ALL
           valves (frozen valve + frozen pipe + frozen fresh tank
           = cracked tank + burst pipes + valve body splits =
           van-killer). Cross-reference
           `binary_sensor.rc_water_freeze_risk` from the water-
           tanks Wave 3 #50 connection.
        -> Low-voltage lockout: don't open valves when
           `sensor.rc_power_battery_soc` <
           `number.rc_water_valve_low_voltage_lockout_soc_pct`
           AND `binary_sensor.rc_power_shore_connected` == FALSE.
           The valve coils pull 0.5–2 A sustained during the
           switching pulse; below 20 % SOC that's enough to keep
           the battery bank from recovering overnight. Cross-
           reference the Victron
           `connections/victron/` connection's
           `sensor.rc_power_battery_soc` +
           `binary_sensor.rc_power_shore_connected` (the same
           pattern that the heated-floors + hvac-basics +
           happijac + water-tanks connections use for their low-
           voltage lockout interlocks).
        -> Auto-close grey drain: close the grey drain valve N
           minutes (operator-tunable via
           `number.rc_water_valve_auto_close_grey_min`, default
           15 min) after open. Grey drain left open = grey tank
           overflows + grey sloshes onto the road while driving =
           bad. The operator-tunable threshold covers operator
           preferences (some operators want 5 min, some want 30
           min — the recipe defaults to 15 min).
        -> Mode-aware lockouts (Stealth / Sleep / Boost):
           - Stealth silent hours auto-mute warnings: when
             `select.rc_mode == stealth` (from the mode/
             automation-builder connection), mute the
             `binary_sensor.rc_water_valve_auto_tank_switch_
             active` + the auto-switch notification (daytime-
             noise warnings — the operator is asleep / not
             interacting with the van). The
             `binary_sensor.rc_water_valve_leak_detected_lockout`
             + `binary_sensor.rc_water_valve_freeze_risk_lockout`
             tiles ALWAYS fire (van-life-or-death warnings —
             they bypass mode-aware suppression).
           - Sleep mode silent: when `select.rc_mode == sleep`,
             additionally mute ALL non-van-life-or-death
             warnings + drop the operator-tunable warning
             thresholds by 10 %.
           - Boost disable-mode-aware-lockouts: when
             `select.rc_mode == boost`, disable ALL the above
             mode-aware lockouts so the operator has full valve
             monitoring during service work / pre-trip packing.
           - The dashboard tile `select.rc_water_valve_mode`
             exposes the operator's local override (`auto` /
             `manual_only` / `stealth_only` / `silent` /
             `disabled`) on top of the mode-aware defaults.
             `auto` = auto tank switching + all warnings enabled.
             `manual_only` = auto tank switching disabled +
             manual valve control only. `stealth_only` = auto
             tank switching + only leak / freeze / low-voltage
             warnings. `silent` = auto tank switching disabled +
             no warnings — reserved for service work. `disabled`
             = no monitoring at all — reserved for when the
             operator has intentionally drained the tanks for
             winterization.
        -> Valve stuck-open detector: when the valve binary_sensor
           reports `valve_position == open` but the
           `expected_position == closed` for > 5 min, fire
           `binary_sensor.rc_water_valve_any_moving` (stuck
           valve = bad in any direction — a stuck-open grey
           drain dumps grey onto the road; a stuck-closed
           fresh inlet means no water at the faucet). The
           recipe §8.6 + §7.6 walks through the operator's
           options (manual override via the dashboard tile +
           replace the valve if the issue persists).

See docs/recipe.md for the full howto (Path A ESPHome valve node
with 12 V / 24 V electrically-actuated valves + safe drivers +
valve-position feedback GPIO; the ESPHome YAML exposes
switch.<node>_valve_fresh_inlet +
switch.<node>_valve_grey_drain +
switch.<node>_valve_aux_tank +
binary_sensor.<node>_valve_*_position; Path B Shelly 1 / Shelly
Plus 1 / Zooz ZEN17 / Aeotec Nano Switch wired into the 12 V /
24 V valve coils + HA core `template:` valve or `switch:` template
+ valve-position feedback binary_sensor; the eighteen §6 contract
tiles + how the upstream switch / valve template exposes them +
translation helpers needed for the derived aggregates like
`any_moving` + `auto_tank_switch_active` + `leak_detected_lockout`
+ `freeze_risk_lockout` + `low_voltage_lockout`; the six §7 safety
interlocks in full (leak detected closes fresh inlet + opens grey
drain; freeze risk closes all valves; low-voltage lockout disables
valve opens when SOC < threshold AND shore disconnected; auto-close
grey drain N minutes after open; mode-aware lockouts via
`select.rc_mode`; valve stuck-open detector); the seven §8
automations including "auto-switch-to-aux-tank when fresh < 5 %"
+ "auto-switch-back-to-primary when aux < 5 %" + "auto-close-grey-
after-N-min" + "leak-detected-close-fresh-open-grey" + "freeze-risk-
close-all" + "low-voltage-lockout" + "mode-aware scheduling so
warnings auto-mute in Stealth silent hours unless they hit the
leak / freeze / low-voltage thresholds"; the eight §9
troubleshooting entries including "valve not responding (coil
polarity / driver voltage / wiring fault)", "valve stuck-open
(mechanical obstruction / lime buildup / replace valve)",
"auto-switch keeps toggling (threshold hysteresis too tight)",
"freeze lockout stuck on after charging (cross-check Victron SOC)",
"Shelly not discovered (mDNS / IGMP snooping)", "ESPHome device
offline", "leak lockout won't release (must clear the leak first
+ manual override)", "grey valve auto-close not firing
(number.rc_water_valve_auto_close_grey_min set too high)"; §10
privacy (the electronic valves produce no telemetry beyond valve
state + valve position feedback; the safety interlocks are local;
no cloud call home); §11 promoting to tier-a (real 12 V / 24 V
valve + safe driver + ESP32 + relay + tank-level sensor bench on
CI + RoamCore-owned operator-wired setup flow that walks the
operator through choosing Path A vs Path B + declaring the valve
GPIO pins + the valve coil polarity + integration tests that
assert a 0 % → 100 % level change triggers the right auto-tank-
switch + the six safety interlocks all flip)).
"""

DOMAIN = "electronic_valves"