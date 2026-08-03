# Deadbolts — tier-b recipe connection

This is the full howto for the `connections/deadbolts/` tier-b recipe
connection. It walks through wiring smart deadbolts on the van doors
(Path A — Z-Wave deadbolts (Schlage Encode Plus, Yale Assure 2,
Kwikset Halo) via the upstream zwave_js Z-Wave JS GUI flow since
2022.x; Path B — Zigbee deadbolts (Aqara A100, Yale Assure 2
Zigbee) via the upstream zha Zigbee Home Automation GUI flow or
zigbee2mqtt MQTT-bridged approach; Path C — Matter/Thread
deadbolts (Level Lock+, Yale Assure 2 Matter variant) via the
upstream matter integration's GUI flow + a Thread border router
on the LAN), mapping the upstream `lock.<name>` entities into the
`rc_safety_lock_*` contract tiles, layering the six MANDATORY
safety interlocks (Away auto-lock / Sleep auto-lock + auto-relock
/ unattended-unlock alarm / CO egress-required override / low-
voltage lockout / multi-door aggregate) + the §7 automations, and
promoting the connection to tier-a when the bench fixture lands.

## §1 What are Deadbolts in RoamCore?

Smart deadbolts — van door lock control for vans — are the **"did
I forget to lock the van?"** answer for every RoamCore operator.
They are positioned in RoamCore as:

- A **vendor-neutral** lock contract. The contract talks to whatever
  smart deadbolt integration the operator already runs (Path A —
  Z-Wave deadbolts via zwave_js; Path B — Zigbee deadbolts via zha
  or zigbee2mqtt; Path C — Matter/Thread deadbolts via matter), not
  to any specific vendor's library.

- A **single "any unlocked" tile** that aggregates front_door +
  side_door + storage_compartment lock state into one dashboard
  indicator. The `binary_sensor.rc_safety_lock_any_unlocked` tile
  is the day-1 affordance.

- A **safety-first** system. The `binary_sensor.rc_safety_lock_
  unexpected_unlock` tile fires when any lock transitions to
  `unlocked` while no presence is detected AND mode is not `away`
  — potential intruder alert. The `binary_sensor.rc_safety_lock_
  co_egress_required` tile fires when `binary_sensor.rc_safety_co_
  detected` (from the smoke-co-gas-sensors Wave 3 #45 connection)
  is TRUE — the operator MUST be able to get OUT of the van even
  if the door was auto-locked at bedtime.

- A **battery-aware** system. The `binary_sensor.rc_safety_lock_
  low_voltage_lockout` tile fires when `sensor.rc_power_battery_
  soc` < 20% (from the Victron connection) — auto-relock is
  disabled to save battery current (each lock/unlock cycle draws
  ~500 mA; in low-voltage mode we skip the auto-relock to preserve
  SOC for the rest of the van's systems).

- A **mode-aware** system. The `select.rc_safety_lock_mode` select
  controls the lock mode: `auto` (Away + Sleep auto-lock on),
  `manual_only` (no auto-lock), `disabled` (reserved for service
  work — the operator can still manually lock / unlock via the
  dashboard tiles).

- A **multi-door-aware** system. The `sensor.rc_safety_lock_
  unlocked_count` reports the integer count of unlocked doors; vans
  with two doors + a storage compartment get full coverage from
  the same 12 contract tiles.

## §2 Prerequisites

Path A — Z-Wave deadbolts (most common for locks):

- The operator's existing Z-Wave smart deadbolt (Schlage Encode
  Plus / Yale Assure 2 / Kwikset Halo / equivalent) installed per
  the manufacturer's instructions.
- A Z-Wave USB dongle on the HA host (e.g. Aeotec Z-Stick 7,
  Zooz ZST39, Silicon Labs UZB-7) — the zwave_js integration
  requires a USB coordinator.
- The HA core `zwave_js` integration configured (its GUI flow
  walks the operator through USB dongle path + network key setup
  since 2022.x).
- The zwave_js integration exposes `lock.<name>` entities in the
  upstream HA core `lock` domain.

Path B — Zigbee deadbolts:

- The operator's existing Zigbee smart deadbolt (Aqara A100 /
  Yale Assure 2 Zigbee / equivalent) installed per the
  manufacturer's instructions.
- A Zigbee coordinator on the HA host (e.g. ITead Zigbee 3.0
  USB Dongle, Tube ZB-GW04, Sonoff ZBDongle-P, or any other
  Zigbee Home Automation v1.2 coordinator).
- The HA core `zha` Zigbee Home Automation integration
  configured (its GUI flow walks the operator through the
  coordinator path since 2022.x) OR a `zigbee2mqtt` MQTT-bridged
  approach (slightly more complex setup but provides a richer
  device configuration UI).
- The zha or zigbee2mqtt integration exposes `lock.<name>`
  entities in the upstream HA core `lock` domain.

Path C — Matter/Thread deadbolts:

- The operator's existing Matter smart deadbolt (Level Lock+ /
  Yale Assure 2 Matter variant / equivalent) installed per the
  manufacturer's instructions.
- A **Thread border router** on the LAN. Acceptable options:
  - **OpenWrt VM** on the Proxmox host (recommended for RoamCore
    operators who already run the OpenWrt VM — adds Thread radio
    support to the existing VM).
  - **Apple HomePod mini** or **Apple TV 4K** (2nd gen or later)
    on the home network.
  - **Nest Hub v2** or **Nest Hub Max** on the home network.
  - **Aeotec Border Router** (USB or stand-alone) on the LAN.
- The HA core `matter` integration configured (its GUI flow
  walks the operator through the Matter fabric setup since
  2023.x).
- The matter integration exposes `lock.<name>` entities in the
  upstream HA core `lock` domain.

Safety prerequisites (cross-references to other connections):

- The bluetooth-wifi-presence `connections/bluetooth-wifi-presence/`
  recipe's `binary_sensor.rc_presence_anyone_home` tile exists
  (required for the §7.3 unattended-unlock alarm).
- The smoke-co-gas-sensors `connections/smoke-co-gas-sensors/`
  recipe's `binary_sensor.rc_safety_co_detected` tile exists
  (required for the §7.4 CO egress-required override).
- The Victron `connections/victron/` recipe's `sensor.rc_power_
  battery_soc` tile exists (required for the §7.5 low-voltage
  lockout).
- The Happijac `connections/happijac/` recipe's
  `binary_sensor.rc_bed_lift_low_voltage_lockout` tile exists
  (the battery-aware relock pattern is the same — Happijac and
  deadbolts share the same low-voltage lockout semantics from
  the Victron SOC signal).
- The mode/automation-builder `connections/mode-automation-builder/`
  recipe's `select.rc_mode` tile exists (required for the §7.1
  Away auto-lock + §7.2 Sleep auto-lock + auto-relock).
- The smart-automations `connections/smart-automations/` recipe's
  managed-marker convention is in place (the unattended-unlock
  alarm can be wired as one of the 17 managed automations if the
  operator prefers).

No upstream vendor integration required beyond the protocol
integration (zwave_js / zha / zigbee2mqtt / matter). RoamCore
ships zero lock hardware.

## §3 Path A — Z-Wave deadbolt (most common for locks)

Z-Wave is the most common protocol for locks because Z-Wave's
mesh networking + battery-friendly design + lock-vendor support
(Schlage / Yale / Kwikset all make Z-Wave variants) make it a
natural fit for battery-powered deadbolts.

Step 1: pair the Z-Wave lock with the zwave_js network.

```bash
# On the HA host, verify the Z-Wave USB dongle is recognized:
lsusb | grep -i zwave
# Expect: Silicon Labs Z-Wave dongle or Aeotec Z-Stick or similar

# In HA: Settings → Devices & Services → Add Integration → Z-Wave JS
# Click "Add". The GUI flow walks through:
#   - USB dongle path selection
#   - Network key setup (generate a fresh key, store in
#     configuration.yaml under zwave_js: network_key: ...)
#   - Home ID assignment
#   - Initial device interview
```

Step 2: include the Z-Wave deadbolt in the zwave_js network.

The lock vendor's instructions walk through the inclusion mode
(usually a button press on the lock + a button press on the
dongle, or a QR code / DSK for newer S2 security class locks).
After inclusion, the lock shows up in HA under
Settings → Devices & Services → Z-Wave JS → Nodes.

Step 3: rename the lock entity to a stable entity_id.

```yaml
# homeassistant/packages/roamcore_lock_zwave.yaml
homeassistant:
  customize:
    lock.zooz_zst39_schlage_encode_plus_front_door:
      friendly_name: "Front Door Lock (Z-Wave)"
      # The entity_id from zwave_js is stable across reboots; no
      # rename needed for the contract layer to find it.
```

Step 4: verify the lock surfaces as `lock.front_door` upstream.

```bash
# In HA Developer Tools → States, filter for `lock.front_door`:
# Expect: lock.front_door state=locked or unlocked, attributes
# include battery_level, node_id, manufacturer, model.
```

Step 5: wire the upstream `lock.front_door` -> contract
`lock.rc_safety_lock_front_door` mapping.

```yaml
template:
  - lock:
      - name: "rc_safety_lock_front_door"
        state: "{{ states('lock.front_door') }}"
        # The template lock mirrors the upstream lock state.
        # When the operator locks via the contract tile (or the
        # OpenClaw query `lock_all`), HA fires lock.lock service
        # on `lock.front_door` (the upstream zwave_js entity).
        # When the upstream lock changes (zwave_js interview /
        # physical button), the template lock mirrors the state.
```

The recommended Z-Wave locks for vans:

| Lock | Z-Wave | Battery | Notes |
|------|--------|---------|-------|
| **Schlage Encode Plus** | Z-Wave Plus | 4× AA | Wi-Fi + Z-Wave; HomeKit + Matter bridge. |
| **Yale Assure 2** | Z-Wave Plus | 4× AA | Touch-screen keypad; slim form factor. |
| **Kwikset Halo** | Z-Wave Plus | 4× AA | Touch-screen + traditional key. |

## §4 Path B — Zigbee deadbolt

Zigbee is the second-most-common protocol for locks. Aqara + Yale
both make Zigbee variants; the Zigbee protocol is more power-
hungry than Z-Wave but the Aqara A100 has a 1.5-year battery life.

Step 1: pair the Zigbee lock with the zha network.

```bash
# On the HA host, verify the Zigbee coordinator is recognized:
lsusb | grep -i zigbee
# Expect: ITead Zigbee 3.0 USB Dongle, Tube ZB-GW04, Sonoff
# ZBDongle-P, or similar

# In HA: Settings → Devices & Services → Add Integration → ZHA
# Click "Add". The GUI flow walks through:
#   - USB coordinator path selection
#   - Zigbee channel selection (default: channel 25 to avoid
#     interference with the Wi-Fi AP)
#   - Initial radio configuration
```

Step 2: include the Zigbee deadbolt in the zha network.

The lock vendor's instructions walk through the inclusion mode
(usually a button press on the lock + the zha "Add Device" button
in the HA UI). After inclusion, the lock shows up in HA under
Settings → Devices & Services → ZHA → Devices.

Step 3: rename the lock entity to a stable entity_id.

```yaml
# homeassistant/packages/roamcore_lock_zigbee.yaml
homeassistant:
  customize:
    lock.aqara_a100_side_door:
      friendly_name: "Side Door Lock (Zigbee)"
```

Step 4: verify the lock surfaces as `lock.side_door` upstream.

```bash
# In HA Developer Tools → States, filter for `lock.side_door`:
# Expect: lock.side_door state=locked or unlocked, attributes
# include battery_level, ieee, manufacturer, model.
```

Step 5: wire the upstream `lock.side_door` -> contract
`lock.rc_safety_lock_side_door` mapping.

```yaml
template:
  - lock:
      - name: "rc_safety_lock_side_door"
        state: "{{ states('lock.side_door') }}"
```

The recommended Zigbee locks for vans:

| Lock | Zigbee | Battery | Notes |
|------|--------|---------|-------|
| **Aqara A100** | Zigbee 3.0 | 4× AA | Budget Zigbee lock; 1.5-year battery. |
| **Yale Assure 2 Zigbee** | Zigbee 3.0 | 4× AA | Touch-screen keypad; slim form factor. |

## §5 Path C — Matter/Thread deadbolt

Matter is the newest lock protocol; it requires a Thread border
router on the LAN. Matter locks are typically more expensive than
Z-Wave or Zigbee locks but the multi-vendor interoperability +
local-only operation + no-cloud-required design is attractive for
operators who want a future-proof lock.

Step 1: ensure a Thread border router is on the LAN.

```bash
# OpenWrt VM (recommended for RoamCore operators):
ssh root@192.168.1.250
# opkg update && opkg install ot-rcp
# /etc/init.d/ot-rcp enable && /etc/init.d/ot-rcp start

# OR Apple HomePod mini / Apple TV 4K (2nd gen+):
# Confirm the device is on the home Wi-Fi and HomeKit is set up.

# OR Nest Hub v2 / Nest Hub Max:
# Confirm the device is on the home Wi-Fi and Google Home is
# set up.

# OR Aeotec Border Router (USB or stand-alone):
# Plug into the LAN; the device advertises itself via mDNS as
# a Thread border router.
```

Step 2: pair the Matter lock with the matter integration.

```bash
# In HA: Settings → Devices & Services → Add Integration → Matter
# Click "Add". The GUI flow walks through:
#   - Commissioning (scan the QR code on the lock OR enter the
#     11-digit setup code)
#   - Fabric setup (HA becomes a Matter commissioner)
#   - Initial device interview
```

Step 3: rename the lock entity to a stable entity_id.

```yaml
# homeassistant/packages/roamcore_lock_matter.yaml
homeassistant:
  customize:
    lock.level_lock_plus_storage_compartment:
      friendly_name: "Storage Compartment Lock (Matter)"
```

Step 4: verify the lock surfaces as `lock.storage_compartment` upstream.

```bash
# In HA Developer Tools → States, filter for `lock.storage_compartment`:
# Expect: lock.storage_compartment state=locked or unlocked,
# attributes include battery_level, node_id, vendor_id, product_id.
```

Step 5: wire the upstream `lock.storage_compartment` -> contract
`lock.rc_safety_lock_storage_compartment` mapping.

```yaml
template:
  - lock:
      - name: "rc_safety_lock_storage_compartment"
        state: "{{ states('lock.storage_compartment') }}"
```

The recommended Matter/Thread locks for vans:

| Lock | Matter | Thread | Battery | Notes |
|------|--------|--------|---------|-------|
| **Level Lock+** | Matter 1.2 | Thread | CR2 | Compact; fits in standard 2-1/8" bore. |
| **Yale Assure 2 Matter** | Matter 1.2 | Thread | 4× AA | Touch-screen keypad. |

## §6 RoamCore contract entities

The 12 `rc_safety_lock_*` tiles + how the upstream `lock.<name>`
templates expose them + translation helpers needed for the
binary_sensors / numeric aggregate sensors / mode select.

The full tile set (per `connection.yml` `dashboard.tiles`):

- `lock.rc_safety_lock_front_door` — front door lock state
  (locked / unlocked / locking / unlocking / opening / open).
- `lock.rc_safety_lock_side_door` — side door lock state.
- `lock.rc_safety_lock_storage_compartment` — storage
  compartment lock state.
- `binary_sensor.rc_safety_lock_any_unlocked` — TRUE if ANY of
  the 3 contract lock tiles is in the `unlocked` state.
- `sensor.rc_safety_lock_unlocked_count` — integer count of
  unlocked doors (0 / 1 / 2 / 3).
- `sensor.rc_safety_lock_last_action_age_min` — minutes since
  the last lock / unlock action across all 3 contract lock tiles
  (the operator can spot "the door has been unlocked for 6 hours
  while we're at the trail").
- `binary_sensor.rc_safety_lock_unexpected_unlock` — TRUE when
  any lock transitions to `unlocked` while no presence is detected
  AND mode is not `away`.
- `binary_sensor.rc_safety_lock_co_egress_required` — TRUE when
  `binary_sensor.rc_safety_co_detected` (from the smoke-co-gas-
  sensors Wave 3 #45 connection) is TRUE.
- `binary_sensor.rc_safety_lock_low_voltage_lockout` — TRUE when
  `sensor.rc_power_battery_soc` (from the Victron connection) <
  20%.
- `select.rc_safety_lock_mode` — `auto` / `manual_only` /
  `disabled`.
- `button.rc_safety_lock_lock_all` — lock all 3 contract lock
  tiles.
- `button.rc_safety_lock_unlock_all` — unlock all 3 contract
  lock tiles (front_door + side_door + storage_compartment).

The any-unlocked aggregate template:

```yaml
template:
  - binary_sensor:
      - name: "rc_safety_lock_any_unlocked"
        state: >-
          {{ is_state('lock.rc_safety_lock_front_door', 'unlocked')
             or is_state('lock.rc_safety_lock_side_door', 'unlocked')
             or is_state('lock.rc_safety_lock_storage_compartment', 'unlocked') }}
        device_class: lock

  - sensor:
      - name: "rc_safety_lock_unlocked_count"
        state: >-
          {{ ([
            is_state('lock.rc_safety_lock_front_door', 'unlocked') | int,
            is_state('lock.rc_safety_lock_side_door', 'unlocked') | int,
            is_state('lock.rc_safety_lock_storage_compartment', 'unlocked') | int
          ] | sum) }}
        unit_of_measurement: "doors"
        state_class: measurement

      - name: "rc_safety_lock_last_action_age_min"
        state: >-
          {{ (now() - (
            [
              state_attr('lock.rc_safety_lock_front_door', 'last_changed') | default(now(), true),
              state_attr('lock.rc_safety_lock_side_door', 'last_changed') | default(now(), true),
              state_attr('lock.rc_safety_lock_storage_compartment', 'last_changed') | default(now(), true)
            ] | max )).total_seconds() // 60 }}
        unit_of_measurement: "min"
        state_class: measurement
```

The mode select:

```yaml
select:
  - platform: template
    selects:
      rc_safety_lock_mode:
        options:
          - "auto"
          - "manual_only"
          - "disabled"
        initial: "auto"
```

The action buttons:

```yaml
button:
  - platform: template
    buttons:
      rc_safety_lock_lock_all:
        press:
          - service: lock.lock
            data:
              entity_id:
                - lock.rc_safety_lock_front_door
                - lock.rc_safety_lock_side_door
                - lock.rc_safety_lock_storage_compartment
      rc_safety_lock_unlock_all:
        press:
          - service: lock.unlock
            data:
              entity_id:
                - lock.rc_safety_lock_front_door
                - lock.rc_safety_lock_side_door
                - lock.rc_safety_lock_storage_compartment
```

## §7 Safety interlocks & automations (MANDATORY before first use)

Six safety interlocks to enable (the recipe ships the full YAML for
each):

1. **Away auto-lock via the mode connection** — when
   `select.rc_mode == away` (from the mode/automation-builder
   connection), fire `lock.lock` on all 3 contract lock tiles
   (front_door + side_door + storage_compartment). The operator
   leaves the van in Away mode and the doors auto-lock.

2. **Sleep auto-lock + auto-relock** — when `select.rc_mode ==
   sleep`, fire `lock.lock` on all 3 contract lock tiles at the
   operator-set bedtime (default 22:30); if any lock transitions
   back to `unlocked` during sleep, fire `lock.lock` again within
   60 seconds (auto-relock — the driver can't forget to lock the
   door at night). The auto-relock is bounded to 3 attempts per
   night to avoid battery drain on a malfunctioning lock.

3. **Unattended-unlock alarm** — when any contract lock
   transitions to `unlocked` AND `binary_sensor.rc_presence_anyone_
   home` is FALSE (from the bluetooth-wifi-presence Wave 3 #42
   connection) AND `select.rc_mode != away`, fire
   `binary_sensor.rc_safety_lock_unexpected_unlock` TRUE + send a
   push notification (someone is opening the van while the driver
   is away — investigate immediately). The cross-reference to the
   bluetooth-wifi-presence connection is critical: the
   unattended-unlock alarm is FALSE-positive prone if the operator
   just left and the presence detection hasn't caught up yet;
   the recipe §8 covers the "increase the home/not_home grace
   period" tuning tip.

4. **CO egress-required override** — when
   `binary_sensor.rc_safety_co_detected` is TRUE (from the
   smoke-co-gas-sensors Wave 3 #45 connection), fire
   `binary_sensor.rc_safety_lock_co_egress_required` TRUE + fire
   `lock.unlock` on the egress-path lock tiles (front_door +
   side_door; the storage_compartment can stay locked — it's not
   on the egress path) + send a push notification. This overrides
   the Away / Sleep auto-lock state because the operator MUST be
   able to get OUT of the van even if the door was auto-locked
   at bedtime. The CO egress-required override is the
   safety-critical interlock that distinguishes the deadbolts
   connection from a generic lock control widget.

5. **Low-voltage lockout** — when `sensor.rc_power_battery_soc`
   < 20% (from the Victron connection), fire
   `binary_sensor.rc_safety_lock_low_voltage_lockout` TRUE +
   disable auto-relock to save battery current (each lock/unlock
   cycle draws ~500 mA; in low-voltage mode we skip the auto-
   relock to preserve SOC for the rest of the van's systems).
   The operator can still manually lock / unlock via the
   dashboard tiles. The cross-reference to the Victron connection
   is the same pattern that the Happijac bed lift uses for its
   `binary_sensor.rc_bed_lift_low_voltage_lockout` interlock —
   both ride the same Victron SOC signal.

6. **Multi-door aggregate** — `binary_sensor.rc_safety_lock_any_
   unlocked` is TRUE if ANY of the 3 contract lock tiles is in
   the `unlocked` state; `sensor.rc_safety_lock_unlocked_count`
   reports the integer count of unlocked doors. This gives a
   single "is the van fully secured?" dashboard indicator that
   covers vans with two doors + storage compartments.

The full automation YAML for each interlock is in the recipe
`homeassistant/automations/rc_safety_lock_*.yaml` files (operator
wires these manually until tier-a promotion lands).

## §8 Troubleshooting

Six troubleshooting entries:

1. **Lock not responding** — the lock battery is dead; the
   Z-Wave / Zigbee mesh range is too far; the Matter Thread
   reachability is weak. Solution: replace the lock battery
   (most Z-Wave / Zigbee / Matter locks use 4× AA; check the
   vendor's manual for the specific battery type). If battery
   is fine, move the Z-Wave / Zigbee coordinator closer to the
   lock (or add a Z-Wave / Zigbee repeater); for Matter, move
   the Thread border router closer to the lock.

2. **Lock state stuck** — Z-Wave interview incomplete. Solution:
   wake the lock manually (usually a button press on the
   interior side) and re-interview the device via the zwave_js
   integration's "Re-interview" button. For Zigbee, re-configure
   the device via the zha integration's "Reconfigure" button.

3. **Unexpected-unlock false-positive** — presence detection
   lag. Solution: increase the home / not_home grace period
   on the bluetooth-wifi-presence `connections/bluetooth-wifi-
   presence/` recipe's `select.rc_presence_occupied_threshold_
   minutes` (default 5 min; raise to 10 min for vans where the
   operator's phone Bluetooth can be flaky near the van).

4. **CO-egress doesn't fire** — smoke-co-gas-sensors connection
   not installed yet. Solution: install the smoke-co-gas-sensors
   `connections/smoke-co-gas-sensors/` connection first
   (Wave 3 #45 slice). The deadbolts connection depends on
   `binary_sensor.rc_safety_co_detected` from the smoke-co-gas
   sensors; without it, the CO egress-required override
   automation has no signal to listen to.

5. **Low-voltage-lockout stuck on** — Victron SOC recovering.
   Solution: wait 5 minutes for the SOC template to re-evaluate;
   the lockout is `sensor.rc_power_battery_soc >= 20%` to
   release. If the SOC reading is bouncing around 20 % (e.g.
   solar charging briefly), the lockout can flicker — increase
   the template's hysteresis by adding `> 22%` instead of
   `> 20%` for the release threshold.

6. **Z-Wave JS network down** — USB stick unplugged. Solution:
   `dmesg | grep -i zwave` on the HA host to confirm the USB
   dongle is recognized; reseat the dongle; restart the
   zwave_js Docker container (or the zwave-js add-on if HAOS).

## §9 Privacy

No telemetry. Everything is local. The smart deadbolts are local
Z-Wave / Zigbee / Matter, no cloud call home. The HA core `lock`
domain does not phone home. The protocol integrations (zwave_js /
zha / matter) MAY phone home for firmware updates — that's the
operator's vendor choice; RoamCore does not add any cloud
integration.

The contract entities (`rc_safety_lock_*`) do not collect any
operator data; they are pure local-state tiles that surface the
operator's choice + the upstream lock state. The push notification
for the unattended-unlock alarm uses the operator's existing
HA Core push notification channel — that's the operator's choice;
RoamCore does not add any push notification channel.

## §10 Promoting to tier-a

What would need to happen to promote this connection from tier-b
to tier-a:

- A real Z-Wave / Zigbee / Matter smart deadbolt on the CI bench
  (the deadbolt requires physical hardware, battery installation,
  and a Z-Wave / Zigbee / Matter coordinator).
- A canonical RoamCore-owned `config_flow.py` that walks the
  operator through choosing Path A vs Path B vs Path C + naming
  each lock entity + mapping it to one of
  `rc_safety_lock_front_door` / `rc_safety_lock_side_door` /
  `rc_safety_lock_storage_compartment`.
- Integration tests that assert a state change from `locked` →
  `unlocked` triggers the right `binary_sensor.rc_safety_lock_any_
  unlocked` + `sensor.rc_safety_lock_unlocked_count` updates.
- Integration tests that assert the 6 safety interlocks (Away
  auto-lock / Sleep auto-lock + auto-relock / unattended-unlock
  alarm / CO egress-required override / low-voltage lockout /
  multi-door aggregate) all fire when wired to canned fixture
  responses.
- Integration tests that assert the CO egress-required override
  (the safety-critical interlock) auto-unlocks the front_door +
  side_door tiles when `binary_sensor.rc_safety_co_detected`
  flips TRUE.
- Flip `tier_requirements` to include `working_config_flow` +
  `integration_test_passes` + `no_manual_yaml_required` +
  `safety_automations_hard_enforced_in_roamcore_code`.

Until those ship, this connection is tier-b even though the
upstream zwave_js / zha / matter integrations have their own GUI
flows. The recipe is sound but we cannot claim one-tap automation.