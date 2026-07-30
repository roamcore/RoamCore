"""Water tanks (fresh/grey monitoring) — tier-b recipe connection.

This module is a marker-only stub. Tier-b connections don't ship native
HA integration code; they publish a recipe (docs/recipe.md) that walks
the user through setting up fresh + grey tank telemetry + pump runtime +
leak detection + freeze-risk monitoring on the van (Path A — ESPHome tank
sensor node per tank + per-pump CT clamp + optional DS18B20 temperature
probe in tank bay + optional leak sensor; Path B — generic resistive /
4–20 mA / voltage probe via a Shelly UNI ADC input + HA `template:`
sensor that translates voltage to percentage via a per-tank calibration
curve; Path C — cloud-bridged level sensor (SeeLevel / Garnet SeeLevel
II 709-BTG / Mopeka Pro Check / Lippert) via the vendor's own HA core
or HACS integration), and exposes the resulting data via the upstream
sensor / binary_sensor / switch / template integration, then publishes
the RoamCore water contract tiles on top (`rc_water_*` tiles: the 17
contract entities documented in connection.yml — 5 sensor telemetry
(fresh_level_pct / fresh_level_l / fresh_days_remaining / grey_level_pct
/ grey_level_l) + 7 binary_sensor warnings (grey_full_warning /
fresh_low_warning / fresh_empty_warning / pump_running /
pump_running_too_long / leak_detected / freeze_risk) + 1 temperature
sensor (fresh_temperature_c) + 2 number configuration tiles
(fresh_tank_size_l / grey_tank_size_l) + 1 mode select (water_mode:
auto / stealth_only / silent / disabled)).

The audit + boundary CI can detect a `water-tanks/` folder that claims
to be a connection via the `DOMAIN` constant exported here. The wizard
reads the manifest + recipe at runtime.

The real per-operator water tank affordance path is:

    Operator-side water tank source (Path A — ESPHome tank sensor node
        per tank + per-pump CT clamp + optional DS18B20 + optional
        leak sensor; the ESPHome integration exposes a GUI flow since
        2023.x; the ESPHome YAML exposes sensor.<node>_fresh_level_pct
        + sensor.<node>_fresh_distance_cm +
        sensor.<node>_grey_level_pct +
        sensor.<node>_grey_distance_cm + optional
        binary_sensor.<node>_pump_running + optional
        sensor.<node>_fresh_temperature_c + optional
        binary_sensor.<node>_leak_detected; OR Path B — generic
        resistive / 4–20 mA / voltage probe via a Shelly UNI ADC
        input + the Shelly integration exposes a GUI flow since
        2022.x + the HA `template:` integration translates voltage
        to percentage via a per-tank calibration curve; OR Path C —
        cloud-bridged level sensor (SeeLevel / Garnet SeeLevel II
        709-BTG / Mopeka Pro Check / Lippert) via the vendor's own
        HA core or HACS integration; vendor integrations expose a
        GUI flow since 2022.x / 2023.x depending on the vendor)
        -> upstream entity (sensor.<tank>_level_pct + sensor.<tank>
           _distance_cm for Path A; sensor.<tank>_voltage for Path B
           (then template'd to percentage); sensor.<vendor_entity>
           for Path C; + binary_sensor.* for pump_running / leak_
           detected / freeze_risk where applicable)
        -> RoamCore contract layer (HA core `template:` sensor /
           binary_sensor / number / select that maps the upstream
           entities into the 17 `rc_water_*` contract tiles —
           rc_water_fresh_level_pct + rc_water_fresh_level_l +
           rc_water_fresh_days_remaining + rc_water_grey_level_pct
           + rc_water_grey_level_l + rc_water_grey_full_warning +
           rc_water_fresh_low_warning + rc_water_fresh_empty_warning
           + rc_water_pump_running + rc_water_pump_runtime_min_last_
           24h + rc_water_pump_running_too_long + rc_water_leak_
           detected + rc_water_freeze_risk + rc_water_fresh_
           temperature_c + rc_water_fresh_tank_size_l +
           rc_water_grey_tank_size_l + rc_water_mode)
        -> dashboard tiles + OpenClaw queries
            ("fresh water level?", "grey water level?", "days of
             fresh water remaining?", "is fresh water low?",
             "is fresh water empty?", "is grey full?",
             "is the water pump running?", "how long has the pump
             been running?", "is there a leak?",
             "is there a freeze risk?", "set fresh tank size to
             <N> litres", "set grey tank size to <N> litres",
             "set water mode to auto/stealth_only/silent/disabled")

    Safety interlocks (MANDATORY before first use — operator must
    wire each one per the recipe §7):
        -> Leak detected: when ANY leak sensor (under-sink / pump-
           area / under-van) reports water, fire
           `binary_sensor.rc_water_leak_detected` TRUE + immediately
           stop the pump (the pump could be the cause of the leak
           or could keep pumping water onto the floor / into the
           van's electrical bay) + send a HIGH-PRIORITY push
           notification (leaks in a van ruin everything — water
           + electronics + cabinetry + insulation all die
           together; the operator MUST address the leak the moment
           it's detected).
        -> Freeze risk: when
           `sensor.rc_water_fresh_temperature_c` < 2 °C, fire
           `binary_sensor.rc_water_freeze_risk` TRUE + cross-
           reference the heated-floors + hvac-basics connections'
           frost-warning path (frozen fresh water tank + frozen
           pipes = cracked tank + burst pipes + no drinking water
           + no shower water + the operator's whole water system
           is offline until the van thaws). The heated-floors
           `connections/heated-floors/` recipe §7.5 frost-protection
           automation will engage gentle floor heating when the
           interior temp is < 5 °C; the hvac-basics
           `connections/hvac-basics/` recipe §7.1 frost-warning
           keeps the cabin thermostat > 5 °C; the water-tanks
           freeze_risk tile is the third pillar of the cold-
           weather safety story.
        -> Fresh empty warning: when
           `sensor.rc_water_fresh_level_pct` < 5 %, fire
           `binary_sensor.rc_water_fresh_empty_warning` TRUE +
           surface prominently on the dashboard (the operator
           MUST refill the fresh tank before the next shower /
           dish wash / toilet flush). This is the "ran out of
           water unexpectedly" tile that the legacy tier-c spec
           promised but never delivered.
        -> Pump running too long: when the pump has been running
           continuously > 10 min (typical usage: a shower is 5–8
           min; a dish-wash is 1–2 min; anything > 10 min is a
           stuck-open faucet or a stuck-relay), fire
           `binary_sensor.rc_water_pump_running_too_long` TRUE +
           automatically stop the pump (a stuck pump will drain
           the fresh tank onto the floor + drain the battery
           bank — both are van-killers). The operator can
           manually re-enable the pump from the dashboard.
        -> Mode-aware lockouts (Stealth / Sleep / Boost):
           - Stealth silent hours auto-mute warnings: when
             `select.rc_mode == stealth` (from the mode/automation-
             builder connection), mute the
             `binary_sensor.rc_water_grey_full_warning` +
             `binary_sensor.rc_water_fresh_low_warning` warnings
             (these are daytime-noise warnings — the operator is
             asleep / not interacting with the van). The
             `binary_sensor.rc_water_leak_detected` +
             `binary_sensor.rc_water_freeze_risk` +
             `binary_sensor.rc_water_fresh_empty_warning` warnings
             ALWAYS fire (these are van-life-or-death warnings —
             they bypass mode-aware suppression).
           - Sleep mode silent: when `select.rc_mode == sleep`,
             additionally mute ALL non-van-life-or-death warnings
             + drop the operator-tunable warning thresholds by
             10 % (the operator is asleep; we want a quieter
             dashboard).
           - Boost disable-mode-aware-lockouts: when
             `select.rc_mode == boost`, disable ALL the above
             mode-aware lockouts so the operator has full
             monitoring during service work / pre-trip packing.
           - The dashboard tile `select.rc_water_mode` exposes
             the operator's local override (`auto` /
             `stealth_only` / `silent` / `disabled`) on top of
             the mode-aware defaults. `auto` = all warnings
             enabled. `stealth_only` = only leak / freeze /
             empty warnings. `silent` = no warnings (reserved
             for service work). `disabled` = no monitoring
             at all (reserved for when the operator has
             intentionally drained the tanks for winterization).

See docs/recipe.md for the full howto (Path A ESPHome tank sensor node
with 2× HC-SR04 waterproof ultrasonic probes per tank + CT clamp on
the 12 V pump wire + DS18B20 temperature probe in tank bay + optional
leak sensor on a GPIO; the ESPHome YAML exposes sensor.<node>_fresh_
level_pct + sensor.<node>_fresh_distance_cm + sensor.<node>_grey_
level_pct + sensor.<node>_grey_distance_cm + binary_sensor.<node>_
pump_running + sensor.<node>_fresh_temperature_c + binary_sensor.
<node>_leak_detected; Path B Shelly UNI wiring + the per-tank
calibration curve for the voltage-to-percentage translation; Path C
SeeLevel via the HA `see_level` HACS integration / Mopeka via the
HA `mopeka_pro_check` HACS integration / Garnet via the `serial`
integration with a USB-to-serial adapter; the seventeen §6 contract
tiles + how the upstream sensor template exposes them + translation
helpers needed for the derived metrics like `fresh_days_remaining`
and `pump_runtime_min_last_24h`; the five §7 safety interlocks in
full (leak / freeze / fresh empty / pump running too long / mode-
aware lockouts); the six §8 automations including "auto-push when
fresh < 20 %" + "auto-push when grey > 80 %" + "auto-stop pump
when pump running too long" + "auto-push critical on leak detected"
+ "auto-engage heated-floors on freeze risk" + "mode-aware
scheduling so warnings auto-mute in Stealth silent hours unless
they hit the leak / freeze / empty thresholds"; the eight §9
troubleshooting entries including "sensor reading 0 % when tank is
full (wiring fault / empty-voltage calibration wrong)", "sensor
reading 100 % when tank is empty (full-voltage calibration wrong)",
"pump_running not toggling (CT clamp orientation / sense resistor
too small)", "leak sensor always-on (probe wet + needs drying +
salt bridge on the contacts)", "ESPHome device offline (check Wi-
Fi + USB-C power)", "Shelly UNI not discovered (mDNS / IGMP
snooping on the LAN switch)", "temperature reading -40 °C (DS18B20
wiring fault — check 4.7 kΩ pull-up)", "fresh_days_remaining
negative (calibration drift / tank-size misconfigured)"; §10
privacy (the water sensors produce no telemetry beyond level +
pump runtime; the leak sensors are local; no cloud call home);
§11 promoting to tier-a (real tank + ESPHome + Shelly UNI bench on
CI + RoamCore-owned operator-wired setup flow that walks the operator through
choosing Path A / B / C + declaring the tank sizes + (for Path A)
the GPIO pins + (for Path B) the calibration curve + (for Path C)
the vendor integration + integration tests that assert a 0 % →
100 % level change triggers the right tile updates)).
"""

DOMAIN = "water_tanks"