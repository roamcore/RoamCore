# Bluetooth / Wi-Fi presence (who's home?)

**Tier:** B (recipe)
**Category:** Presence
**Status:** beta

## What this connection is

Presence detection — who is currently home in the van — is the **foundation** of every occupied/away automation in RoamCore: shut down inverter + pump when nobody is home, turn on approach lighting when the first person returns after dark, suppress Stealth-silent-hours actions when only the driver is present, alert when shore is disconnected AND ≥2 people are home AND inverter SOC is low. The signal that drives all of those is a vendor-neutral "who's home?" layer that the rest of RoamCore can rely on — and that layer is what this connection provides.

RoamCore ships **no** native presence scanner. We RECIPE the well-understood combination of one of three upstream operator-side device-tracking paths and a translation layer that maps each upstream `device_tracker.<vendor>_<mac>` entity into a vendor-neutral `rc_presence_person_*` contract tile. The three paths:

- **Path A — Bluetooth LE tracking** via HA core `bluetooth_le_tracker` (recommended for small vans with 1–2 people where every phone is reliably discoverable on Bluetooth; YAML-only because the upstream integration is deprecated as of HA 2024.6 but still functional; the recipe recommends pairing a Bluetooth Low Energy beacon like a Nut find3 or Apple AirTag alongside the phone so the beacon remains discoverable while the phone screen is locked — solves the screensaver-sleep false-positive).
- **Path B — Wi-Fi presence** via HA core `nmap_device_tracker` (config_flow since 2022.x) OR the `ping` binary_sensor alternative (Path B-alt; no nmap dependency but slower — 60 s poll). Recommended for fleet installs where each HA host can scan its own subnet.
- **Path C — Router-side device_tracker** via the matching HA core integration (`asuswrt` for AsusWRT-Merlin routers, `unifi` for Ubiquiti UniFi gateways/controllers, `mikrotik` for MikroTik RouterOS routers). Recommended when the operator already uses one of those routers as the LAN gateway (the router is the source of truth — no ARP scanning needed).

All three paths land on the same vendor-neutral contract layer via `rc_presence_*` dashboard tiles:

- `device_tracker.rc_presence_person_alice` / `..._bob` — vendor-neutral per-person device_tracker aliases.
- `binary_sensor.rc_presence_anyone_home` — OR of all `rc_presence_person_*` entities being `home` (or the stricter Bluetooth + Wi-Fi agreement rule from the legacy catalog spec §7).
- `binary_sensor.rc_presence_only_driver_home` — true only when the operator-declared driver is the only person home.
- `sensor.rc_presence_persons_home_count` — count of `rc_presence_person_*` entities currently `home`.
- `sensor.rc_presence_last_arrival` — last time `anyone_home` flipped `false` → `true`.
- `sensor.rc_presence_last_departure` — last time `anyone_home` flipped `true` → `false`.
- `binary_sensor.rc_presence_all_away` — inverse of `anyone_home`, with a `rc_presence_occupied_threshold_minutes` debounce so a brief "everyone away" blip doesn't trigger the inverter-shutdown automation.
- `button.rc_presence_refresh_now` — force a refresh on all `rc_presence_person_*` contract tiles.
- `select.rc_presence_occupied_threshold_minutes` — operator-tunable debounce window.

This fills the `presence` subsystem slot in `docs/reference/rc-entity-naming.md` — a forward-compatible addition that mirrors how `media` was added by the Music Assistant slice.

RoamCore does **not** ship a Bluetooth adapter, a Wi-Fi scanner, or a router integration. The HA core integrations are the upstream truth; RoamCore layers a contract on top: the `rc_presence_*` dashboard tiles + the OpenClaw queries that bind to those contract entities ("is anyone home?", "who is home?", "persons home count?", "last arrival time?", "last departure time?", "is only driver home?", "is everyone away?", "refresh presence now").

## Setup recipe (one-paragraph)

1. Decide which path fits your van: **Path A** — Bluetooth LE tracking (small vans with 1–2 people; needs a Bluetooth adapter reachable from HA; pairs each phone + recommends a BLE beacon alongside the phone to handle screensaver-sleep); OR **Path B** — Wi-Fi presence via `nmap_device_tracker` (config_flow; needs `nmap` installed on the HA host + the operator's LAN must permit ARP scans) or `ping` (no nmap dependency but slower); OR **Path C** — Router-side device_tracker (`asuswrt` / `unifi` / `mikrotik`; cleanest when the operator already uses one of those routers).
2. Wire the upstream HA core integration for your chosen path. Path A goes via YAML (the upstream `bluetooth_le_tracker` integration is YAML-only). Path B and Path C go via the integration's config_flow. The recipe walks through each.
3. Declare each tracked person via the HA `person` integration (Settings → People → Add Person). For each person, add the upstream `device_tracker.<vendor>_<mac>` entities that map to them (a phone, a watch, a BLE beacon).
4. Create the `rc_presence_*` contract tiles (or import the recipe's `template` + `binary_sensor` + `sensor` + `button` + `select` helpers from the recipe §4 helper YAML). The recipe walks through translating each HA `person` entity's `state == 'home'` into the `device_tracker.rc_presence_person_*` family.
5. Create the aggregation helpers (`binary_sensor.rc_presence_anyone_home`, `binary_sensor.rc_presence_only_driver_home`, `binary_sensor.rc_presence_all_away`, `sensor.rc_presence_persons_home_count`, `sensor.rc_presence_last_arrival`, `sensor.rc_presence_last_departure`).
6. (Optional) Wire the Bluetooth + Wi-Fi agreement rule from legacy spec §7 — requires both a Bluetooth device_tracker AND a Wi-Fi device_tracker in the `home` state within a 2-minute window for `rc_presence_anyone_home` to be `true`. Reduces iPhone screensaver-sleep false positives.
7. Enable the recipe §7 automations (Stealth mode suppression, approach lighting on first arrival after dark, inverter/pump shutdown on all-away + shore disconnected + >15 min, only-driver-home dim interior to 10 % after dark, power-aware occupancy alert that cross-references the Music Assistant recipe for TTS + the Victron recipe for SOC).
8. Reload the RoamCore dashboard; the `rc_presence_*` contract tiles appear under the Presence section.

Full howto with copy-pasteable YAML for the helpers, automations, Path A/B/C wiring, HA `person` entity wiring, mode-aware exceptions, and the tier-a promotion outline: see [`docs/recipe.md`](docs/recipe.md).

## Why tier-b, not tier-a

Tier-a requires a working RoamCore-owned `config_flow.py`, integration tests against real Bluetooth adapters + Wi-Fi routers + BLE beacons on CI, and `wizard.one_tap: true`. We have no per-person device declaration on the CI bench to integration-test against, the operator's exact Path A-vs-B-vs-C choice + per-person device mix is a personal-taste choice, and there's no canonical RoamCore-owned upstream HA integration that does what this connection recipes. So this connection is honestly beta-tier: the recipe is sound but we cannot claim one-tap automation. The [`tests/test_connection_yml.py`](tests/test_connection_yml.py) file asserts the manifest is honest about its tier — that's the only test we can ship today.

When a real Bluetooth + Wi-Fi bench lands (likely 2 BLE devices + a Wi-Fi router + an ESPHome Bluetooth proxy — exactly what the §10 promotion outline describes), this connection is the candidate to promote to tier-a: add a native `config_flow.py` that wraps the RoamCore-specific presence contract (with per-person device declaration), add an integration test that asserts the `rc_presence_*` contract entities appear after a synthetic `bluetooth_le_tracker` + `nmap_device_tracker` poll with canned fixture responses, and flip `tier_requirements` to include `working_config_flow` + `integration_test_passes` + `no_manual_yaml_required`.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "bluetooth-wifi-presence"` marker for the audit.
- `docs/recipe.md` — the full howto (Path A bluetooth_le_tracker YAML wiring + screensaver-sleep workaround via BLE beacon, Path B nmap_device_tracker / ping wiring + per-device template helper YAML, Path C asuswrt / unifi / mikrotik router-side wiring, HA `person` entity OR template helper translation, mode-aware presence automations that respect Stealth silent hours + Travel approach lighting + Boost driver-home-relaxed + inverter-SOC power-aware occupancy alert that cross-references the Music Assistant `connections/music-assistant/` recipe for TTS + the Victron `connections/victron/` recipe for SOC, troubleshooting, privacy, tier-a promotion outline).
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded by the connection manifest):
  [the legacy spec](../../the legacy spec)
- Catalog category index: the legacy spec
- Music Assistant connection (companion for the §7 "Power-aware occupancy alert" TTS automation — the TTS target is `media_player.rc_media_zone_living`):
  `connections/music-assistant/`
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`
- OpenClaw JSON API (the contract `summary_keys` land here): `docs/reference/openclaw-json-api.md`