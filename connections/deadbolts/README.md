# Deadbolts (smart lock control for van doors)

**Tier:** B (recipe)
**Category:** Safety
**Status:** beta

## What this connection is

Smart deadbolts — van door lock control for vans — are the **"did I forget to lock the van?"** answer: a single "any unlocked" tile that aggregates front_door + side_door + storage_compartment lock state into one dashboard indicator, the unlocked_count sensor that reports the integer count of unlocked doors, the last_action_age_min sensor that tracks how long it's been since the last lock/unlock action (so the operator can spot "the door has been unlocked for 6 hours while we're at the trail"), the unexpected_unlock alarm that fires when any lock transitions to unlocked while no one is home (potential intruder alert), the CO-egress-required override that auto-unlocks the egress-path doors when CO is detected in the van (smoke-co-gas-sensors Wave 3 #45 integration fires this), the low-voltage lockout that disables auto-relock when the battery SOC drops below 20 % (Victron connection signal), the lock mode select (`auto` / `manual_only` / `disabled`), and the lock_all / unlock_all action buttons for agent + automation access.

RoamCore ships **no** native smart deadbolt. We RECIPE the well-understood combination of three upstream operator-side paths and a translation layer that maps each upstream `lock.<name>` (from zwave_js / zha / matter) into a vendor-neutral `rc_safety_lock_*` contract layer. The three paths:

- **Path A — Z-Wave deadbolts** (most common for locks). Recommended models: Schlage Encode Plus, Yale Assure 2, Kwikset Halo. Wired via the upstream `zwave_js` integration (HA core `zwave_js` since 2022.x; USB Z-Wave dongle required). The upstream integration exposes `lock.<name>` entities directly.

- **Path B — Zigbee deadbolts**. Recommended models: Aqara A100, Yale Assure 2 Zigbee. Wired via the upstream `zha` Zigbee Home Automation integration (HA core `zha` since 2022.x; Zigbee coordinator required) OR `zigbee2mqtt` MQTT-bridged approach. The upstream integration exposes `lock.<name>` entities directly.

- **Path C — Matter/Thread deadbolts**. Recommended models: Level Lock+, Yale Assure 2 Matter variant. Wired via the upstream `matter` integration (HA core `matter` since 2023.x; requires a Thread border router on the LAN — OpenWrt VM, Apple HomePod mini, Nest Hub v2, or Aeotec Border Router). The upstream integration exposes `lock.<name>` entities directly.

All three paths land on the same vendor-neutral contract layer via 12 `rc_safety_lock_*` dashboard tiles (3 individual lock tiles for the 3 door slots + 6 aggregate / interlock binary_sensors + sensors + a mode select + 2 action buttons).

## Setup recipe (one-paragraph)

1. Decide which path fits your van: **Path A** — Z-Wave deadbolts via zwave_js (most common for locks; Schlage Encode Plus / Yale Assure 2 / Kwikset Halo); **Path B** — Zigbee deadbolts via zha or zigbee2mqtt (Aqara A100 / Yale Assure 2 Zigbee); **Path C** — Matter/Thread deadbolts via the matter integration (Level Lock+ / Yale Assure 2 Matter variant) + a Thread border router on the LAN.
2. Wire the prerequisites FIRST (the recipe §2 walks through these). The operator MUST not skip the upstream protocol integration prerequisite (the recipe won't work if zwave_js / zha / matter is not already configured).
3. Wire the upstream lock. Path A: pair the Z-Wave lock via the zwave_js GUI flow; Path B: pair the Zigbee lock via zha or zigbee2mqtt; Path C: pair the Matter lock via the matter GUI flow + the Thread border router.
4. Wire the HA core `template:` locks (or HA core `entity` customize-domain alias) that maps the upstream `lock.<name>` to one of the 3 contract lock tiles (`rc_safety_lock_front_door` / `rc_safety_lock_side_door` / `rc_safety_lock_storage_compartment`).
5. Wire the `template:` binary_sensors + sensors + select + buttons that synthesize the remaining 9 contract tiles.
6. Verify the 6 §7 safety interlocks (Away auto-lock / Sleep auto-lock + auto-relock / unattended-unlock alarm / CO egress-required override / low-voltage lockout / multi-door aggregate).
7. Enable the 6 §7 safety automations.
8. Reload the RoamCore dashboard.

Full howto: see [`docs/recipe.md`](docs/recipe.md).

## Why tier-b, not tier-a

Tier-a requires a working RoamCore-owned `config_flow.py`, integration tests against a real smart deadbolt on the CI bench, and `wizard.one_tap: true`. We have no operator-side smart deadbolt on the CI bench to integration-test against (the deadbolt requires physical hardware, battery installation, and a Z-Wave / Zigbee / Matter coordinator). So this connection is honestly beta-tier: the recipe is sound but we cannot claim one-tap automation.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "deadbolts"` marker for the audit.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded): [`docs/catalog/safety/deadbolts.md`](../../docs/catalog/safety/deadbolts.md)
- Smoke / CO / gas safety sensors connection (companion for the §7 CO egress-required override): `connections/smoke-co-gas-sensors/`
- Bluetooth / Wi-Fi presence connection (companion for the §7 unattended-unlock alarm): `connections/bluetooth-wifi-presence/`
- Mode / automation-builder connection (companion for the §7 Away + Sleep mode-aware auto-lock): `connections/mode-automation-builder/`
- Victron (power) connection (companion for the §7 low-voltage lockout): `connections/victron/`
- Happijac bed lift connection (companion for the §7 battery-aware relock pattern): `connections/happijac/`
- Smart automations connection (companion for the §7 mode-aware lock scheduling): `connections/smart-automations/`
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`