"""Deadbolts (smart lock control for van doors) — tier-b recipe connection.

This module is a marker-only stub. Tier-b connections don't ship native
HA integration code; they publish a recipe (docs/recipe.md) that walks
the user through setting up smart deadbolt control on the van (Path A —
Z-Wave deadbolts (Schlage Encode Plus, Yale Assure 2, Kwikset Halo) via
the HA core `zwave_js` Z-Wave JS GUI flow; Path B — Zigbee deadbolts
(Aqara A100, Yale Assure 2 Zigbee) via the HA core `zha` Zigbee Home
Automation integration's GUI flow or `zigbee2mqtt` MQTT-bridged approach;
Path C — Matter/Thread deadbolts (Level Lock+, Yale Assure 2 Matter
variant) via the HA core `matter` integration's GUI flow + a Thread
border router on the LAN), and exposes the resulting data via the
upstream zwave_js / zha / matter integration, then publishes the
RoamCore lock contract tiles on top (`rc_safety_lock_*` tiles: the 12
contract entities documented in connection.yml — 3 individual lock
tiles for front_door / side_door / storage_compartment + 6 binary /
numeric aggregate tiles for any_unlocked / unlocked_count /
last_action_age_min / unexpected_unlock / co_egress_required /
low_voltage_lockout + a mode select + 2 action buttons).

The audit + boundary CI can detect a `deadbolts/` folder that claims
to be a connection via the `DOMAIN` constant exported here. The wizard
reads the manifest + recipe at runtime.

The real per-operator smart deadbolt affordance path is:

    Operator-side smart deadbolt source (Path A — Z-Wave deadbolts via
        the upstream `zwave_js` integration's GUI flow since 2022.x;
        the upstream zwave_js integration exposes lock.<name>
        entities directly via its lock domain; OR Path B — Zigbee
        deadbolts via the upstream `zha` integration's GUI flow or
        `zigbee2mqtt` MQTT-bridged approach; OR Path C — Matter/Thread
        deadbolts via the upstream `matter` integration's GUI flow +
        a Thread border router)
        -> upstream lock.<name> entity (the protocol integration
           exposes the lock state via the HA core `lock` domain —
           zwave_js for Path A; zha or zigbee2mqtt for Path B;
           matter for Path C)
        -> RoamCore contract layer (HA core `template:` lock OR HA
           core `entity` customize-domain alias that maps the
           upstream lock.<name> to one of the 3 contract lock tiles
           — rc_safety_lock_front_door / rc_safety_lock_side_door /
           rc_safety_lock_storage_compartment — plus template
           binary_sensors + template sensors + template select +
           template buttons that synthesize the rc_safety_lock_*
           contract tiles from the upstream entities)
        -> dashboard tiles + OpenClaw queries
            ("is the van locked?", "lock all", "unlock all",
             "unlock front door", "lock side door",
             "is the storage unlocked?", "is there an unexpected
              unlock?", "is CO egress required?",
             "is low-voltage lockout engaged?", "set lock mode")

    Safety interlocks (MANDATORY before first use — operator must
    wire each one per the recipe §7):
        -> Away auto-lock: when `select.rc_mode == away` (from the
           mode/automation-builder connection), fire `lock.lock` on
           all 3 contract lock tiles (front_door + side_door +
           storage_compartment)
        -> Sleep auto-lock + auto-relock: when `select.rc_mode ==
           sleep`, fire `lock.lock` on all 3 contract lock tiles at
           the operator-set bedtime; if any lock transitions back
           to `unlocked` during sleep, fire `lock.lock` again within
           60 seconds (auto-relock — the driver can't forget to
           lock the door at night)
        -> Unattended-unlock alarm: when any contract lock
           transitions to `unlocked` AND `binary_sensor.rc_presence_
           anyone_home` is FALSE (from the bluetooth-wifi-presence
           Wave 3 #42 connection) AND `select.rc_mode != away`, fire
           `binary_sensor.rc_safety_lock_unexpected_unlock` TRUE
           + send a push notification (someone is opening the van
           while the driver is away — investigate immediately)
        -> CO egress-required override: when `binary_sensor.rc_
           safety_co_detected` is TRUE (from the smoke-co-gas-sensors
           Wave 3 #45 connection), fire `binary_sensor.rc_safety_
           lock_co_egress_required` TRUE + fire `lock.unlock` on
           the egress-path lock tiles (front_door + side_door; the
           storage_compartment can stay locked — it's not on the
           egress path) + send a push notification. This overrides
           the Away / Sleep auto-lock state because the operator
           MUST be able to get OUT of the van even if the door was
           auto-locked at bedtime.
        -> Low-voltage lockout: when `sensor.rc_power_battery_soc`
           < 20% (from the Victron connection), fire
           `binary_sensor.rc_safety_lock_low_voltage_lockout` TRUE
           + disable auto-relock to save battery current (each
           lock/unlock cycle draws ~500 mA; in low-voltage mode we
           skip the auto-relock to preserve SOC for the rest of
           the van's systems). The operator can still manually
           lock / unlock via the dashboard tiles.
        -> Multi-door aggregate: `binary_sensor.rc_safety_lock_any_
           unlocked` is TRUE if ANY of the 3 contract lock tiles
           is in the `unlocked` state; `sensor.rc_safety_lock_
           unlocked_count` reports the integer count of unlocked
           doors. This gives a single "is the van fully secured?"
           dashboard indicator that covers vans with two doors +
           storage compartments.

See docs/recipe.md for the full howto (Path A Z-Wave JS pairing
instructions + recommended Z-Wave locks (Schlage Encode Plus, Yale
Assure 2, Kwikset Halo), Path B ZHA or Zigbee2MQTT pairing
instructions + recommended Zigbee locks (Aqara A100, Yale Assure 2
Zigbee), Path C Matter pairing instructions + Thread border router
prerequisite (OpenWrt VM, Apple HomePod mini, Nest Hub v2, or Aeotec
Border Router) + recommended Matter locks (Level Lock+, Yale Assure
2 Matter variant), the six §7 safety interlocks in full, six §8
troubleshooting entries including "lock not responding" (battery
low on the lock; Z-Wave / Zigbee mesh range; Matter Thread
reachability), "lock state stuck" (Z-Wave interview incomplete —
wake the lock manually and re-interview), "unexpected-unlock
false-positive" (presence detection lag — increase the home /
not_home grace period), "CO-egress doesn't fire" (smoke-co-gas-sensors
connection not installed yet), "low-voltage-lockout stuck on"
(Victron SOC recovering — wait 5 min), and "Z-Wave JS network down"
(USB stick unplugged — `dmesg | grep -i zwave` and reseat the
dongle), privacy, tier-a promotion outline).
"""

DOMAIN = "deadbolts"