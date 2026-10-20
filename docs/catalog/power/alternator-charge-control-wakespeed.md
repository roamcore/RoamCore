# Alternator charge control (Wakespeed / smart regulator)

**Support:** B (recipe)
**Install:** one-line

Shows you at a glance whether your alternator is charging the house battery while you drive, and turns charging off on its own when it would do more harm than good — so you wake up to a charged battery instead of a flat one.

## §1 What it does

- The dashboard surfaces a single "is the alternator allowed to charge right now?" tile that aggregates your chosen charging mode + whether the engine is running + your battery's state of charge + your battery's temperature + your current RoamCore mode + any regulator fault into one big YES / NO indicator.
- A "charging mode" selector lets you pick off / auto / boost / float / desulfation / stealth / protect_battery from the dashboard (advanced mode shows the per-vendor mode names; the default mode is auto).
- A "target voltage" tile shows the regulator's voltage setpoint (volts). When the battery is cold or hot, this number automatically lowers itself so the regulator doesn't over-charge or under-charge.
- A "charge current" tile shows how many amps the alternator is currently pushing into your house battery bank.
- A "temperature compensation active" tile tells you when the regulator's cold-battery / hot-battery protection curve is actively adjusting the target voltage.
- A "fault" tile warns you when the regulator reports an over-temp / over-voltage / communication-lost / BMS-lockout fault (when this is TRUE, the system forces charging OFF and pings your phone so you can investigate before something gets damaged).
- A "last trigger reason" tile tells you why the alternator was last enabled (manual / ignition_on / soc_low / battery_cold / boost / desulfation / stealth_suppressed / fault_blocked).
- A "manual override" button lets you force alternator charging ON for a configurable duration from the dashboard — useful when you know you need a top-off before tonight.

The system watches five safety interlocks at the same time and refuses to enable charging unless all five hold:

1. The engine is running (so the alternator is actually turning).
2. Your battery's state of charge is above your chosen protect-battery threshold (default 20 %).
3. Your battery's temperature is inside the safe range (cold cutoff default −10 °C, hot cutoff default +50 °C).
4. The current RoamCore mode isn't set to suppress the alternator (stealth + sleep only block charging if you've flagged the alternator as noisy).
5. The regulator isn't reporting a fault.

It also follows the broader RoamCore power patterns: when the inverter battery's state of charge drops below 60 %, the regulator automatically switches to boost charging until you hit 80 %; when the state of charge drops below 20 %, the system flips into a protect-battery mode that disables charging so you keep enough power for the fridge + lights + medical + comms.

## §2 Prerequisites

- **A charging source.** Pick ONE of:
  - A smart alternator regulator linked to a Victron / Renogy / REDARC / Sterling / Balmar / EP-Power DC-DC charger (the recommended path for vans with a DC-DC charger). The DC-DC charger exposes its enable/disable + voltage + current + temperature + fault state through its own integration.
  - A generic smart alternator regulator exposed over the messaging system by the vendor's bridge (Wakespeed WS500 + WS Link / Balmar MC-618 + Smartlink / Renogy Battery-to-Battery + BT-2 / REDARC BCDC + RedVision / Sterling regulated advanced alternator-to-battery charger + BMS Link / EP-Power B2B + EP Link / ARCO Zeus + Zeus app / an OEM CAN-j1939 regulator + a CAN-to-MQTT bridge such as a Signal K gateway on the boat's NMEA 2000 backbone).
  - A relay or GPIO switch on the alternator's field wire (the wire that tells the alternator's internal regulator when to charge). A Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano Switch or an ESPHome / Tasmota GPIO relay works. The wire connects through the relay; flipping the relay off tells the alternator to stop charging.
  - Just an ignition signal (read-only; no actual alternator control). You just want to know when the engine is running and let the existing dumb alternator do its thing.

- **A battery temperature probe.** A Z-Wave / Zigbee / 1-Wire / ESPHome analog-input probe attached to the house battery bank. The Victron's built-in temperature sensor works if you already have one.

- **An ignition signal.** Either a GPIO on an ESPHome node wired to the alternator's D+ wire with a voltage divider, or the existing signal that RoamCore already gets from your van's leveling + mode automations.

- **The Victron battery monitor + battery current reading.** The system reads your house battery's state of charge + current from your existing Victron setup. If you don't have a Victron system yet, see the Victron power monitoring recipe first.

- **The mode selector set up.** The system reads your current mode (home / away / stealth / sleep / off) from the RoamCore mode recipe so it can decide whether to suppress the alternator when you're trying to be quiet.

- **An always-on Home Assistant instance.** The canonical RoamCore setup.

## §3 Install

### §3.1 Option 1 (recommended) — DC-DC charger-linked regulator

1. **Pick your DC-DC charger.** If your alternator already charges through a Victron SmartSolar charger / BMV battery monitor / Cerbo GX, or a Renogy Battery-to-Battery charger, or a REDARC BCDC, or a Sterling regulated advanced alternator-to-battery charger, or a Balmar MC-618, or an EP-Power B2B — that path is the easiest one.
2. **Wire the DC-DC charger per the manufacturer's instructions.** Most DC-DC chargers need three wires: battery positive (from the house battery), alternator input (from the alternator's B+ terminal), and a thin ignition sense wire (from the vehicle's ignition).
3. **Pair the DC-DC charger with your home assistant.** If it's a Victron Cerbo GX, install the Victron integration from the app store for Home Assistant. If it's a Renogy / REDARC / Sterling / Balmar / EP-Power, install the messaging system integration and add the vendor's Bluetooth-to-MQTT bridge.
4. **Verify the upstream entities exist.** Open Settings → Devices & Services and confirm the DC-DC charger shows up as a device with a switch (charge enable) and several sensors (voltage, current, temperature) and a binary sensor (fault state).
5. **Set the charge mode to `auto`.** Open the RoamCore dashboard → Power → Alternator → Charge Mode → pick `auto` (the default; the automations take over from here).
6. **Turn on the engine and watch the dashboard.** The "is charging?" tile flips to YES, the "charge current" tile starts showing amps flowing into your batteries, and the "last trigger reason" tile shows "ignition_on".
7. **Wire the safety interlocks.** Follow the recipe's full howto for the temperature compensation + protect-battery mode + fault-block automations (these are the rules that prevent over-charge + fault damage + critical-load starvation).

### §3.2 Option 2 — Vendor messaging-system bridge (Wakespeed / Balmar / Sterling / Renogy / REDARC / EP-Power / ARCO)

1. **Install the regulator.** Wire the regulator to your alternator's field wire + battery sense + (if supported) CAN bus.
2. **Pair the regulator with the vendor's bridge.** Wakespeed WS Link / Sterling BMS Link / Balmar Smartlink / Renogy BT-2 / REDARC RedVision / EP-Power EP Link / ARCO Zeus app / Signal K gateway on a boat's NMEA 2000 backbone. Each one has its own pairing instructions in the box.
3. **Configure the bridge to publish over the messaging system.** Open the bridge's web UI → MQTT settings → set the topic prefix to e.g. `roamcore/regulator/`. Set the home assistant MQTT broker as the destination.
4. **Add the messaging system integration to home assistant.** Settings → Devices & Services → Add Integration → MQTT. Enter your broker credentials (or accept the auto-discovered broker).
5. **Verify the upstream entities.** Look for a switch (charge enable) + sensors (target voltage, charge current, battery temperature) + a binary sensor (fault state) + a number (voltage setpoint) + a select (charge mode).
6. **Set the charge mode to `auto`.** Same as Option 1.
7. **Turn on the engine and watch the dashboard.** Same as Option 1.

### §3.3 Option 3 — Relay or GPIO switch (the minimum-viable path)

This is the simplest path if you have no smart regulator and no messaging-system bridge — just a plain externally-regulated alternator whose field wire can be turned off.

1. **Pick the relay.** A Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano Switch or an ESPHome / Tasmota GPIO relay driven by an ESP32 / ESP8266 node.
2. **Wire the relay in series with the alternator's field excitation wire.** The wire goes: alternator field terminal → relay common → relay normally-open → regulator (or ignition feed, depending on your alternator). When the relay is open, no field excitation = alternator stops charging.
3. **Pair the relay with home assistant.** For a Shelly 1 / Shelly Plus 1: Settings → Devices & Services → Add Integration → Shelly. For an ESPHome / Tasmota node: same → Add Integration → ESPHome (or MQTT for Tasmota).
4. **Verify the switch entity.** Look for a switch.* or binary_switch.* entity representing the relay.
5. **Set the charge mode to `auto`.** Same as the other options. Note that with this path, the "target voltage" tile is hard-coded to your chosen nominal voltage (14.4 V for a 12 V system) — there's no smart regulator to negotiate with.
6. **Turn on the engine and watch the dashboard.** Same as the other options.

### §3.4 Option 4 — Read-only ignition-signal-only (just want to know)

If your alternator is dumb and you don't want to add any control hardware, this path gives you a single dashboard tile that tells you when the engine is running + when the system thinks the alternator *should* be charging.

1. **Skip the regulator / relay entirely.** Your dumb alternator stays dumb.
2. **Pick an ignition signal source.** The easiest option is to use the existing RoamCore engine-running signal from the leveling + mode recipes. Alternative: wire a GPIO on an ESPHome node to the alternator's D+ wire with a voltage divider.
3. **Set the charge mode to `auto`** (the only mode that does anything on this path).
4. **Turn on the engine and watch the dashboard.** The "is charging?" tile flips to YES as a *recommendation*. Your existing alternator continues doing whatever it does. The other tiles (target voltage, charge current, fault) are advisory-only on this path.

## §4 Recommended dashboard tile

- **Card type:** entities card under the Power section.
- **Entities:**
  - `binary_sensor.rc_power_alternator_charging_enabled` — the big YES / NO indicator (green when allowed, red when blocked).
  - `select.rc_power_alternator_charge_mode` — the mode selector.
  - `sensor.rc_power_alternator_target_voltage_v` — V (turns red and changes when temperature compensation lowers the value).
  - `sensor.rc_power_alternator_charge_current_a` — A.
  - `binary_sensor.rc_power_alternator_temp_compensation_active` — small dot; on when the temperature protection curve is active.
  - `binary_sensor.rc_power_alternator_fault` — small dot; red when there's a fault.
  - `sensor.rc_power_alternator_last_trigger_reason` — text explaining why the alternator is enabled right now.
  - `button.rc_power_alternator_manual_override` — the big "force charge for X minutes" button.

## §5 Troubleshooting

### §5.1 The "is charging?" tile never goes green

- The operator's upstream regulator / relay isn't connected to home assistant (Settings → Devices & Services → verify the integration is configured).
- The protect-battery mode is engaged (the battery's state of charge is below your threshold). Wait for solar / shore to recharge, OR press the manual override button.
- The fault tile is TRUE. Check the regulator's fault display and clear the fault before retrying.
- The mode is set to stealth or sleep and the alternator has been flagged as noisy. Either change mode, or press the manual override button.

### §5.2 The alternator keeps charging after the engine is off

- The engine-running signal is stuck. The leveling + mode recipes' engine-running tile should flip OFF when the engine stops; if it doesn't, check the leveling recipe's IMU + drive-state signal.

### §5.3 A fault fires on the very first start

- The field wire polarity is reversed. Many regulators are negative-ground only; check the polarity.
- The battery sense wire isn't connected. The regulator reads a phantom battery voltage and reports over-voltage.
- The CAN bus termination is wrong. Add a 120 Ω resistor at each end of the bus.

### §5.4 The protect-battery mode stays engaged even though the battery has plenty of charge

- The Victron battery state-of-charge reading is reporting stale data (the battery monitor hasn't received a fresh reading in over five minutes). Check the battery monitor's status.

### §5.5 The manual override button doesn't force the alternator on

- The fault tile is TRUE (the manual override is intentionally suppressed while a fault is active). Clear the fault first.
- The upstream switch entity isn't configured. Verify the relay integration shows up in Settings → Devices & Services.

### §5.6 The temperature compensation never kicks in

- The battery temperature probe isn't connected. Check the wiring.
- The probe is reading ambient air instead of the battery case. Attach it directly to one of the house battery's terminals.

### §5.7 The mode-aware suppression doesn't actually suppress

- The mode selector isn't set up (check Settings → Devices & Services → mode/automation-builder).
- The selected mode is actually `home` / `away`, not `stealth` / `sleep`.
- The alternator hasn't been flagged as noisy in the selected mode. Either flag it (input_boolean.rc_power_alternator_noisy_in_stealth or _in_sleep) or press the manual override button.

### §5.8 The fault tile stays TRUE even after the regulator reports the fault cleared

- The upstream fault entity is reporting `unknown` (the bridge or integration has lost contact with the regulator). Check the bridge's status.
- The upstream integration has a stale state bug. Restart the bridge / integration.

## §6 Useful links

- Recipe (the canonical full howto with all four paths + all six automations + the safety interlocks): [`../../connections/alternator-charge-control/docs/recipe.md`](../../connections/alternator-charge-control/docs/recipe.md)
- Connection overview (folder README): [`../../connections/alternator-charge-control/README.md`](../../connections/alternator-charge-control/README.md)
- Source manifest: [`../../connections/alternator-charge-control/connection.yml`](../../connections/alternator-charge-control/connection.yml)
- Manifest-honesty tests: [`../../connections/alternator-charge-control/tests/test_connection_yml.py`](../../connections/alternator-charge-control/tests/test_connection_yml.py)
- RoamCore entity naming: [`../../reference/rc-entity-naming.md`](../../reference/rc-entity-naming.md) (the `alternator` subsystem under the existing `power` subsystem was added by this slice)
- Victron recipe (the source of battery state-of-charge + battery current + battery temperature used by the safety interlocks): [`../../connections/victron/README.md`](../../connections/victron/README.md)
- Mode recipe (the source of the mode selector for the stealth / sleep suppression): [`../../connections/mode/README.md`](../../connections/mode/README.md)
- Leveling recipe (the source of the engine-running signal): [`../../connections/leveling/README.md`](../../connections/leveling/README.md)
