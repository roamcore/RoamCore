# Bluetooth / Wi-Fi presence — tier-b recipe connection

**Tier:** B (recipe)
**Audience:** A RoamCore user who wants to know who's home in the van (and
who's away) using one of three upstream operator-side paths: Bluetooth LE
tracking via HA core `bluetooth_le_tracker` (Path A), Wi-Fi presence via
HA core `nmap_device_tracker` or `ping` (Path B), or router-side
device_tracker via the matching HA core `asuswrt` / `unifi` / `mikrotik`
integration (Path C). All three paths land on the same vendor-neutral
contract layer via `rc_presence_*` dashboard tiles + OpenClaw presence
queries ("is anyone home?", "who is home?", "persons home count?",
"last arrival time?", "last departure time?", "is only driver home?",
"is everyone away?", "refresh presence now").

This howto is mirrored into `docs/connections/bluetooth-wifi-presence.md`
by the catalog cron (`scripts/build_catalog.py`) so it shows up under
the public docs site's "Connections" section. Keep this recipe as the
source of truth.

## §1 What is presence detection in RoamCore?

Presence detection — who is currently home in the van — is the
**foundation** of every occupied/away automation in RoamCore:

- **Per-person granularity** is optional but powerful. RoamCore wants
  to know "is anyone home?" (`binary_sensor.rc_presence_anyone_home`)
  for the inverter/pump-shutdown automation, but it also wants
  "is only the driver home?" (`binary_sensor.rc_presence_only_driver_home`)
  for the Stealth-silent-hours-dim-interior rule. The per-person
  `device_tracker.rc_presence_person_<name>` family lets the operator
  declare each tracked person individually.
- **Three upstream paths** (operator picks based on host OS +
  available hardware + existing router + per-person device mix):
  - **Path A — Bluetooth LE tracking** via HA core
    `bluetooth_le_tracker` (recommended for small vans with 1–2
    people where every phone is reliably discoverable on Bluetooth).
    YAML-only because the upstream integration is deprecated as of
    HA 2024.6 but still functional; the recipe recommends pairing a
    Bluetooth Low Energy beacon like a Nut find3 or Apple AirTag
    alongside the phone so the beacon remains discoverable while the
    phone screen is locked — solves the screensaver-sleep
    false-positive.
  - **Path B — Wi-Fi presence** via HA core `nmap_device_tracker`
    (config_flow since 2022.x) OR the `ping` binary_sensor
    alternative (Path B-alt; no nmap dependency but slower — 60 s
    poll). Recommended for fleet installs where each HA host can
    scan its own subnet.
  - **Path C — Router-side device_tracker** via the matching HA core
    integration (`asuswrt` for AsusWRT-Merlin routers, `unifi` for
    Ubiquiti UniFi gateways/controllers, `mikrotik` for MikroTik
    RouterOS routers). Recommended when the operator already uses
    one of those routers as the LAN gateway (the router is the
    source of truth — no ARP scanning needed).
- **The `rc_presence_*` contract layer** translates each upstream
  `device_tracker.<vendor>_<mac>` entity into a vendor-neutral
  `device_tracker.rc_presence_person_<name>` entity, then aggregates
  per-person presence into the `binary_sensor.rc_presence_anyone_home`,
  `binary_sensor.rc_presence_only_driver_home`, `binary_sensor.rc_presence_all_away`,
  `sensor.rc_presence_persons_home_count`,
  `sensor.rc_presence_last_arrival`,
  `sensor.rc_presence_last_departure`,
  `button.rc_presence_refresh_now`, and
  `select.rc_presence_occupied_threshold_minutes` tiles.
- **How it feeds mode-aware automations**: Stealth silent hours
  suppress the presence-driven lighting + inverter shutdown;
  Travel mode triggers approach lighting on first arrival; Boost
  mode relaxes the "only driver home → dim to 10 %" rule to 25 %;
  a power-aware automation alerts when shore is disconnected AND
  ≥2 people are home AND inverter SOC < 30 % (cross-references
  the Victron `connections/victron/` recipe for SOC + the Music
  Assistant `connections/music-assistant/` recipe for the TTS
  target).

RoamCore does **not** ship a Bluetooth adapter, a Wi-Fi scanner,
or a router integration. There is no canonical RoamCore-owned
upstream HA integration for "scan for who's home" — the operator's
Path A-vs-B-vs-C choice is host OS + available hardware + existing
router + per-person device mix driven, and the upstream HA core
integrations are the truth. So we publish a recipe that walks you
through the wiring, then layer a small contract on top: the
`rc_presence_*` dashboard tiles + the OpenClaw queries that bind
to those contract entities.

**Why tier-b:** RoamCore has no real Bluetooth adapters + Wi-Fi
routers + BLE beacons on the bench to integration-test against, no
native HA integration to point at, and the operator's per-person
device declaration + Path A-vs-B-vs-C choice is personal-taste +
hardware-driven — so the audit-recommended config_flow can't be
canonical here. The recipe is sound (it leans on the upstream HA
core integrations + the well-understood translation-into-`person`
pattern), but we cannot claim one-tap automation. The §10 promotion
outline describes exactly what needs to happen to flip this to
tier-a.

## §2 Prerequisites

Before starting the recipe, make sure you have:

- **Home Assistant 2023.8 or newer** (the upstream HA core
  `nmap_device_tracker` (Path B) + `asuswrt` / `unifi` / `mikrotik`
  (Path C) integrations have a config_flow since 2022.x; the
  upstream `bluetooth_le_tracker` (Path A) is YAML-only).
- **For Path A — Bluetooth LE tracking:** a Bluetooth adapter
  reachable from HA (built-in for most HAOS installs; for VM
  installs (VP2430 + HAOS VM, Proxmox + HA Container, etc.) you
  need either a USB Bluetooth dongle passed through to the HA
  VM/container OR an ESPHome Bluetooth proxy on the LAN).
- **For Path B — Wi-Fi presence via `nmap_device_tracker`:** the
  `nmap` binary installed on the HA host (`apt-get install nmap`
  on Debian-based HAOS, `apk add nmap` on Alpine-based HA
  Container) + the operator's LAN must permit ARP scans
  (most home routers do; some managed switches drop ARP probes
  — see §8 Troubleshooting). For Path B-alt via `ping`, no
  `nmap` dependency but slower (60 s poll).
- **For Path C — Router-side device_tracker:** a supported
  router integration + read-only API credentials:
  - `asuswrt` — AsusWRT-Merlin router + the router's admin
    username + password (recommend creating a dedicated
    read-only user).
  - `unifi` — Ubiquiti UniFi gateway or controller + the
    controller's local admin credentials (the integration
    auto-discovers the gateway if it's on the same LAN).
  - `mikrotik` — MikroTik RouterOS router + the router's
    API username + password (recommend creating a dedicated
    read-only API user with the `api` group).
- **For all paths:** at least one tracked device (a phone, a
  watch, a BLE beacon — the operator picks what to track per
  person) + the HA `person` integration (HA core; ships with
  HA; Settings → People → Add Person).
- **Hardware callouts (typical van install):** for Path A,
  most operators use a USB Bluetooth dongle (e.g. a
  Cambridge Silicon Radio CSR8510-based dongle, ~$10) +
  optionally one BLE beacon per tracked person (Nut find3
  ~$30 each, Apple AirTag ~$30 each, Tile Pro ~$35 each).
  For Path B, the HA host's built-in Wi-Fi adapter works for
  nmap scanning (nmap sends raw ARP packets; the operator's
  Wi-Fi adapter doesn't need to be associated with the LAN).
  For Path C, no extra hardware — the operator's existing
  router does the tracking.

## §3 Path A — Bluetooth LE tracking (recommended for small vans with 1–2 people)

The default install for RoamCore users on small vans with 1–2
people where every phone is reliably discoverable on Bluetooth.

### §3.1 — Verify HA can see the Bluetooth adapter

In HA → **Settings → Devices & Services → Add Integration →
Bluetooth**, HA will scan for available Bluetooth adapters. If
HA doesn't find an adapter:

1. For HAOS on bare metal: the built-in Bluetooth adapter should
   work out of the box.
2. For HAOS in a VM (Proxmox + HAOS VM): you need USB passthrough
   for the Bluetooth dongle. Add the USB device to the VM's
   hardware (Proxmox → VM → Hardware → Add → USB Device),
   then restart the VM.
3. For HA Container (Docker): the container needs
   `--privileged` + the Bluetooth dongle's device node
   passed through. See the HA Container Bluetooth docs.
4. **Recommended:** use an ESPHome Bluetooth proxy on the LAN
   (any ESP32 board flashed with ESPHome + the
   `esp32_ble_tracker` component + `bluetooth_proxy` component).
   The proxy advertises itself via mDNS on the LAN; HA
   auto-discovers it and uses it as a remote Bluetooth adapter.
   This is the cleanest path for VM/container installs.

### §3.2 — Add the `bluetooth_le_tracker` integration via YAML

The upstream `bluetooth_le_tracker` integration is YAML-only
(it's deprecated as of HA 2024.6 but still functional; no
config_flow because upstream has stopped investing in it). Add
to your `configuration.yaml`:

```yaml
device_tracker:
  - platform: bluetooth_le_tracker
    # Defaults: scan_interval=10, consider_home=0:00:30
    # (a device is considered "home" if seen in the last 30 s;
    # "away" if not seen for >30 s).
    # For vans where the BLE signal can be intermittent, consider
    # `consider_home: 0:03:00` (3 minutes) to reduce false-away.
    consider_home: 0:03:00
```

Restart HA. The integration will start scanning for Bluetooth
devices; each discoverable device shows up as a
`device_tracker.<device_name>_<mac_suffix>` entity in HA.

### §3.3 — Pair each person's phone

1. Make sure each person's phone has Bluetooth enabled +
   discoverable mode (most modern phones default to
   "non-discoverable" — the operator needs to flip the
   setting temporarily for the initial pairing, then flip
   it back. Android: Settings → Connections → Bluetooth →
   visibility timeout → set to "visible while settings is
   open" OR use a BLE beacon as the per-person tracker
   instead of the phone).
2. HA will discover the phone + create a `device_tracker.<phone_name>`
   entity. Note the entity id (Settings → Devices & Services
   → Device Tracker → `<device>` → Entity ID).
3. (Optional but recommended for screensaver-sleep) Pair a
   Bluetooth Low Energy beacon like a Nut find3 or Apple
   AirTag alongside the phone. The beacon remains
   discoverable even when the phone screen is locked +
   Bluetooth is in "low-energy" mode. HA discovers the
   beacon as a separate `device_tracker.<beacon_name>`
   entity. The recipe §7 "Bluetooth + Wi-Fi agreement rule"
   covers combining the two.

### §3.4 — Wire the `device_tracker.rc_presence_person_<name>` contract

For each tracked person, create a HA `person` entity via
Settings → People → Add Person, then attach the upstream
`device_tracker.<device>` entities to that person via the
person's `Device trackers` list (Person → Edit → Device
trackers → Add). HA computes the person's home/away state
as the OR of all attached device_tracker entities.

Then add a template device_tracker alias so the vendor-
neutral `rc_presence_person_<name>` contract tile mirrors
the HA `person.<name>` entity's state:

```yaml
template:
  - device_tracker:
      - name: Bluetooth / Wi-Fi presence — person alice (contract)
        unique_id: rc_presence_person_alice
        value_template: "{{ is_state('person.alice', 'home') }}"
        source_type: bluetooth_le
```

Repeat for each tracked person (`person.bob`,
`person.kid`, etc.).

### §3.5 — Verify

1. Open the RoamCore dashboard → **Presence** section.
2. The `device_tracker.rc_presence_person_<name>` tiles
   should be visible. Each one shows `home` when the
   attached upstream device_tracker entities are in the
   `home` state.
3. If the tiles never flip to `home`, check §8
   (Troubleshooting).

## §4 Path B — Wi-Fi presence via `nmap_device_tracker` or `ping` (recommended for fleet installs where each HA host can scan its own subnet)

The default install for RoamCore users on fleet installs where
each HA host can scan its own subnet (e.g. one HA instance per
van).

### §4.1 — Install `nmap` on the HA host

```bash
# HAOS (Debian-based):
sudo apt-get update && sudo apt-get install -y nmap

# HA Container (Alpine-based):
sudo apk add nmap

# HA Core on a generic Linux host:
# use your distro's package manager (apt, dnf, pacman, etc.)
```

Verify:

```bash
nmap --version
# Nmap version 7.80 (or newer)
```

### §4.2 — Add the `nmap_device_tracker` integration via config_flow

In HA → **Settings → Devices & Services → Add Integration →
Nmap Tracker**, with:

- **Host:** the IP or hostname of the host running nmap (default
  `localhost` — same as HA).
- **LAN CIDR:** the CIDR of the LAN you want to scan (e.g.
  `192.168.1.0/24`). HA will ARP-scan this subnet every 60 s
  by default.
- **Consider home:** how long a device must be seen before
  being marked `home` (default 180 s; for vans where the
  Wi-Fi signal can be intermittent, consider 300 s).

HA will scan the LAN and create one
`device_tracker.<vendor>_<mac>` entity per discovered device.

### §4.3 — Map each `device_tracker.<vendor>_<mac>` into the contract

For each tracked person, create a HA `person` entity via
Settings → People → Add Person, then attach the upstream
`device_tracker.<device>` entities to that person (same as
Path A §3.4).

For the rare case where the operator wants to skip the HA
`person` integration and map directly into the contract
tile, add a template device_tracker alias:

```yaml
template:
  - device_tracker:
      - name: Bluetooth / Wi-Fi presence — person alice (contract, nmap path)
        unique_id: rc_presence_person_alice_nmap
        value_template: "{{ is_state('device_tracker.alice_iphone_aa_bb_cc_dd_ee_ff', 'home') }}"
        source_type: router
```

(The `rc_presence_person_alice` contract tile then takes the
OR of all `rc_presence_person_alice*` template aliases via
the recipe §6 aggregation helpers.)

### §4.4 — Path B-alt: `ping` binary_sensor (no nmap dependency)

For hosts that cannot install `nmap` (Alpine-based HA
Container with read-only filesystem, etc.), use the HA core
`ping` binary_sensor:

```yaml
binary_sensor:
  - platform: ping
    host: 192.168.1.42          # Alice's phone LAN IP (recommend a static DHCP lease)
    name: "Ping Alice's phone"
    scan_interval: 60
```

Then wrap each `binary_sensor.ping_alices_phone` in a
template device_tracker:

```yaml
template:
  - device_tracker:
      - name: Bluetooth / Wi-Fi presence — person alice (contract, ping path)
        unique_id: rc_presence_person_alice_ping
        value_template: "{{ is_state('binary_sensor.ping_alices_phone', 'on') }}"
        source_type: router
```

Slower than nmap (60 s poll) but no nmap dependency.

### §4.5 — Verify

Same as Path A §3.5.

## §5 Path C — Router-side device_tracker (recommended when the operator already uses an AsusWRT / Ubiquiti UniFi / MikroTik router as the LAN gateway)

The cleanest path for operators who already use one of these
routers — the router is the source of truth (no ARP scanning
needed on the HA host).

### §5.1 — AsusWRT (`asuswrt` integration)

In HA → **Settings → Devices & Services → Add Integration →
AsusWRT**, with:

- **Host:** the AsusWRT-Merlin router's LAN IP (e.g.
  `192.168.1.1`).
- **Username + password:** the router's admin credentials
  (recommend creating a dedicated read-only user).

The integration queries the router's DHCP leases + ARP table
and exposes one `device_tracker.<device_name>` entity per
connected device.

### §5.2 — UniFi (`unifi` integration)

In HA → **Settings → Devices & Services → Add Integration →
Ubiquiti UniFi**, with:

- **Host:** the UniFi controller's LAN IP (typically the
  UniFi gateway's IP).
- **Username + password:** the controller's local admin
  credentials.
- **Port:** 8443 (default) OR 443 (for UniFi OS gateways).

The integration queries the controller's clients + ARP table
and exposes one `device_tracker.<device_name>` entity per
connected client.

### §5.3 — MikroTik (`mikrotik` integration)

In HA → **Settings → Devices & Services → Add Integration →
MikroTik**, with:

- **Host:** the RouterOS router's LAN IP (e.g. `192.168.1.1`).
- **Username + password:** the router's API credentials
  (recommend creating a dedicated read-only API user with
  the `api` group).

The integration queries the router's DHCP leases + ARP table
and exposes one `device_tracker.<device_name>` entity per
connected device.

### §5.4 — Map upstream entities into the contract

Same as Path B §4.3 — create a HA `person` entity per
tracked person, attach the upstream `device_tracker.<device>`
entities, then mirror the person's home/away state into the
`device_tracker.rc_presence_person_<name>` contract tile via
a template alias.

## §6 RoamCore contract entities

The full listing the wizard + dashboard + OpenClaw rely on:

| Entity | Type | States | Source |
|---|---|---|---|
| `device_tracker.rc_presence_person_alice` | device_tracker | `home` / `not_home` | template alias of HA `person.alice` |
| `device_tracker.rc_presence_person_bob` | device_tracker | `home` / `not_home` | template alias of HA `person.bob` |
| `binary_sensor.rc_presence_anyone_home` | binary_sensor | ON / OFF | template: any `rc_presence_person_*` state == `home` (or the stricter Bluetooth + Wi-Fi agreement rule, §7) |
| `binary_sensor.rc_presence_only_driver_home` | binary_sensor | ON / OFF | template: the operator-declared driver is `home` AND no other person is `home` |
| `sensor.rc_presence_persons_home_count` | sensor | int count | template: count of `rc_presence_person_*` entities currently `home` |
| `sensor.rc_presence_last_arrival` | sensor | timestamp | HA `history_stats` integration: last time `anyone_home` flipped `false` → `true` |
| `sensor.rc_presence_last_departure` | sensor | timestamp | HA `history_stats` integration: last time `anyone_home` flipped `true` → `false` |
| `binary_sensor.rc_presence_all_away` | binary_sensor | ON / OFF | inverse of `anyone_home`, debounced by `rc_presence_occupied_threshold_minutes` |
| `button.rc_presence_refresh_now` | button | (press) | calls `homeassistant.update_entity` on every `rc_presence_person_*` |
| `select.rc_presence_occupied_threshold_minutes` | select | int minutes | operator-tunable debounce window for `rc_presence_all_away` |

### §6.1 — Copy-pasteable helper YAML

Drop into `homeassistant/packages/roamcore_presence.yaml`:

```yaml
# RoamCore Presence contract helpers (recipe §6.1).
# All entities are vendor-neutral per docs/reference/rc-entity-naming.md.
# Replace `person.alice` / `person.bob` references with the actual
# person entity ids you created via Settings → People → Add Person.

input_select:
  rc_presence_driver_raw:
    name: Bluetooth / Wi-Fi presence — driver (contract, raw)
    options:
      - alice
      - bob
    icon: mdi:account-key

input_number:
  rc_presence_occupied_threshold_minutes_raw:
    name: Bluetooth / Wi-Fi presence — occupied threshold minutes (contract, raw)
    min: 1
    max: 60
    step: 1
    initial: 15
    icon: mdi:timer

select:
  - name: Bluetooth / Wi-Fi presence — occupied threshold minutes (contract)
    unique_id: rc_presence_occupied_threshold_minutes
    options:
      - "1"
      - "5"
      - "10"
      - "15"
      - "30"
      - "45"
      - "60"
    icon: mdi:timer

template:
  - binary_sensor:
      - name: Bluetooth / Wi-Fi presence — anyone home (contract)
        unique_id: rc_presence_anyone_home
        state: >
          {{ is_state('device_tracker.rc_presence_person_alice', 'home')
             or is_state('device_tracker.rc_presence_person_bob', 'home') }}
        device_class: presence
        icon: mdi:home-account
      - name: Bluetooth / Wi-Fi presence — only driver home (contract)
        unique_id: rc_presence_only_driver_home
        state: >
          {% set driver = states('select.rc_presence_driver_raw') %}
          {% if driver == 'alice' %}
            {{ is_state('device_tracker.rc_presence_person_alice', 'home')
               and not is_state('device_tracker.rc_presence_person_bob', 'home') }}
          {% elif driver == 'bob' %}
            {{ is_state('device_tracker.rc_presence_person_bob', 'home')
               and not is_state('device_tracker.rc_presence_person_alice', 'home') }}
          {% else %}
            off
          {% endif %}
        device_class: presence
        icon: mdi:account-key-outline
      - name: Bluetooth / Wi-Fi presence — all away (contract, debounced)
        unique_id: rc_presence_all_away
        state: >
          {% set threshold = states('select.rc_presence_occupied_threshold_minutes') | int(15) %}
          {% set anyone_home_for = now() - states.binary_sensor.rc_presence_anyone_home.last_changed %}
          {% if anyone_home_for.total_seconds() / 60 >= threshold %}
            on
          {% else %}
            off
          {% endif %}
        device_class: presence
        icon: mdi:home-outline
  - sensor:
      - name: Bluetooth / Wi-Fi presence — persons home count (contract)
        unique_id: rc_presence_persons_home_count
        state: >
          {{ states.device_tracker
             | selectattr('entity_id', 'match', 'device_tracker.rc_presence_person_')
             | selectattr('state', 'eq', 'home')
             | list | length }}
        icon: mdi:account-multiple
      - name: Bluetooth / Wi-Fi presence — last arrival (contract)
        unique_id: rc_presence_last_arrival
        state: "{{ state_attr('binary_sensor.rc_presence_anyone_home', 'last_changed') }}"
        icon: mdi:home-clock
      - name: Bluetooth / Wi-Fi presence — last departure (contract)
        unique_id: rc_presence_last_departure
        state: "{{ state_attr('binary_sensor.rc_presence_anyone_home', 'last_changed') }}"
        icon: mdi:home-clock-outline

button:
  - name: Bluetooth / Wi-Fi presence — refresh now (contract)
    unique_id: rc_presence_refresh_now
    icon: mdi:refresh
    # OpenClaw agent-action allowlist: this button is the target of
    # the `refresh_presence_now` query key.
    press:
      - service: homeassistant.update_entity
        target:
          entity_id:
            - device_tracker.rc_presence_person_alice
            - device_tracker.rc_presence_person_bob
            - binary_sensor.rc_presence_anyone_home
            - binary_sensor.rc_presence_only_driver_home
            - sensor.rc_presence_persons_home_count
```

## §7 Automations

Six sample automations, copy-pasteable into
`homeassistant/automations/roamcore_presence_*.yaml`. Every
automation below binds to the `rc_presence_anyone_home` tile
(or its complement `rc_presence_all_away`), so flipping the
single "anyone home" tile ON or OFF cascades through the
mode-aware occupied/away rules across the rest of RoamCore
(Stealth suppression, Travel approach lighting, Boost
driver-home-relaxed dim, inverter/pump shutdown on all-away,
power-aware occupancy alert):

### §7.1 — Stealth mode: suppress presence-based actions

```yaml
alias: Bluetooth / Wi-Fi presence — Stealth mode suppresses presence-driven actions
mode: single
trigger:
  - platform: state
    entity_id: input_select.rc_mode
    to: "stealth"
action:
  - service: persistent_notification.create
    data:
      title: RoamCore — Stealth presence: actions suppressed
      message: >-
        Stealth silent hours active; presence-based automations
        (approach lighting on arrival, inverter shutdown on all-away,
        TTS occupancy alerts) are suppressed for the duration of
        Stealth mode.
```

### §7.2 — Bluetooth + Wi-Fi agreement rule (legacy catalog spec §7)

```yaml
alias: Bluetooth / Wi-Fi presence — Bluetooth + Wi-Fi agreement (legacy §7)
mode: single
trigger:
  - platform: state
    entity_id:
      - device_tracker.rc_presence_person_alice
      - device_tracker.rc_presence_person_bob
    to: "home"
condition:
  # Requires BOTH a Bluetooth device_tracker AND a Wi-Fi device_tracker
  # in the `home` state for the SAME person within a 2-minute window.
  # Reduces false positives from iPhone screensaver sleep.
  - condition: template
    value_template: >
      {% set person = trigger.entity_id.split('_')[-1] %}
      {% set bt_entity = 'device_tracker.' ~ person ~ '_iphone_aa_bb_cc_dd_ee_ff' %}
      {% set wifi_entity = 'device_tracker.' ~ person ~ '_pixel_11_22_33_44_55_66' %}
      {% set now_ts = as_timestamp(now()) %}
      {% set bt_last = as_timestamp(states[bt_entity].last_changed) | default(0) %}
      {% set wifi_last = as_timestamp(states[wifi_entity].last_changed) | default(0) %}
      {{ (now_ts - bt_last) <= 120 and (now_ts - wifi_last) <= 120 }}
action:
  - service: persistent_notification.create
    data:
      title: RoamCore — Presence: Bluetooth + Wi-Fi agreement confirmed
      message: >-
        {{ trigger.entity_id }} confirmed home via BOTH Bluetooth and
        Wi-Fi within the 2-minute agreement window.
```

### §7.3 — Approach lighting on first arrival after dark

```yaml
alias: Bluetooth / Wi-Fi presence — Approach lighting on first arrival after dark
mode: single
trigger:
  - platform: state
    entity_id: binary_sensor.rc_presence_anyone_home
    from: "off"
    to: "on"
condition:
  - condition: state
    entity_id: input_select.rc_mode
    state:
      - travel
      - boost
      - home
  - condition: sun
    after: sunset
    after_offset: "-00:30:00"
action:
  - service: light.turn_on
    target:
      entity_id: light.rc_lighting_approach
    data:
      brightness_pct: 30
  - service: persistent_notification.create
    data:
      title: RoamCore — Presence: approach lighting on
      message: >-
        First person arrived home after dark; approach lighting at 30 %.
```

### §7.4 — Inverter/pump shutdown on all-away + shore disconnected + >15 min

```yaml
alias: Bluetooth / Wi-Fi presence — Inverter shutdown on all-away + shore disconnected
mode: single
trigger:
  - platform: state
    entity_id: binary_sensor.rc_presence_all_away
    to: "on"
    for: "00:15:00"
condition:
  - condition: state
    entity_id: binary_sensor.rc_power_shore_connected
    state: "off"
  - condition: state
    entity_id: input_select.rc_mode
    state:
      - home
      - travel
    # Stealth is allowed but typically not relevant (someone home to be in stealth).
action:
  - service: switch.turn_off
    target:
      entity_id:
        - switch.rc_power_inverter_idle
        - switch.rc_power_water_pump
  - service: persistent_notification.create
    data:
      title: RoamCore — Presence: inverter + pump shutdown on all-away
      message: >-
        Nobody home for 15+ minutes AND shore disconnected; inverter
        idle + water pump shut down to preserve battery.
```

### §7.5 — Only driver home: dim interior to 10 % after dark

```yaml
alias: Bluetooth / Wi-Fi presence — Only driver home: dim interior to 10%
mode: single
trigger:
  - platform: state
    entity_id: binary_sensor.rc_presence_only_driver_home
    to: "on"
condition:
  - condition: sun
    after: sunset
action:
  - service: light.turn_on
    target:
      entity_id:
        - light.rc_lighting_living
        - light.rc_lighting_bed
    data:
      brightness_pct: 10
  - service: persistent_notification.create
    data:
      title: RoamCore — Presence: only driver home, interior dim
      message: >-
        Only the driver is home after dark; interior lights dimmed
        to 10 % so as not to wake passengers.
```

### §7.6 — Power-aware occupancy alert (cross-references Music Assistant TTS + Victron SOC)

```yaml
alias: Bluetooth / Wi-Fi presence — Power-aware occupancy alert (TTS to living zone)
mode: single
trigger:
  - platform: numeric_state
    entity_id: sensor.rc_presence_persons_home_count
    above: 1
condition:
  - condition: numeric_state
    entity_id: sensor.rc_power_battery_soc
    below: 30
  - condition: state
    entity_id: binary_sensor.rc_power_shore_connected
    state: "off"
  - condition: state
    entity_id: input_select.rc_mode
    state:
      - home
      - travel
action:
  - service: tts.cloud_say
    target:
      entity_id: media_player.rc_media_zone_living
    data:
      message: >-
        Shore power disconnected and inverter battery below 30
        percent with {{ states('sensor.rc_presence_persons_home_count') }}
        people home. Consider conserving power.
  - service: persistent_notification.create
    data:
      title: RoamCore — Presence: power-aware occupancy alert
      message: >-
        Shore disconnected AND SOC {{ states('sensor.rc_power_battery_soc') }} %
        AND {{ states('sensor.rc_presence_persons_home_count') }} people home;
        TTS sent to the living zone.
```

## §8 Troubleshooting

1. **Bluetooth adapter not detected in HAOS VM (Path A).** USB
   passthrough required; ESPHome Bluetooth proxy recommended for
   non-USB builds (see §3.1).
2. **`nmap` not on PATH in HA Container (Path B).** Install with
   `apk add nmap` OR use the `ping` alternative (Path B-alt §4.4).
3. **MAC randomisation on modern phones breaks Wi-Fi tracking
   (Path B/C).** Modern phones randomise their MAC address on
   each Wi-Fi association for privacy. ARP scanning + DHCP
   lease tracking both see the random MAC, not the device's
   "real" MAC. Recommend per-phone static DHCP lease + use the
   DHCP-leases integration rather than ARP scanning, OR use a
   BLE beacon as the per-person tracker (Path A's recommendation).
4. **Router integration auth expired (Path C).** HA logs
   `401 Unauthorized` when the router integration's credentials
   expire; refresh the token in the integration's options
   (Settings → Devices & Services → `<integration>` → Options).
5. **`person` entity not picking up `device_tracker` (all paths).**
   HA requires the `person` entity to be created manually OR
   via the `person` integration; the device_tracker must be in
   the `person`'s `device_trackers` list (Person → Edit → Device
   trackers → Add). If the person entity's state never flips to
   `home`, check that the device_tracker is correctly attached.
6. **False-away when phone screen locks mid-evening (Path A).**
   This is Path A's screensaver-sleep failure mode; the phone's
   Bluetooth goes quiet when the screen is locked. Recommend
   pairing a BLE beacon (Nut find3 / Apple AirTag) alongside
   the phone so the beacon remains discoverable while the phone
   screen is locked (see §3.3).
7. **`nmap_device_tracker` returns no devices (Path B).** ARP
   scanning can be blocked by some managed switches (ARP
   inspection / DHCP snooping). Try switching to Path B-alt
   (`ping`) OR Path C (router-side) if your LAN has managed
   switches in the path.
8. **`binary_sensor.rc_presence_all_away` debounce stuck.** The
   debounce threshold (`select.rc_presence_occupied_threshold_minutes`)
   is too high; reduce it to 5 minutes for fleet installs where
   all-away periods are expected to be shorter.

## §9 Privacy

- **Presence data is sensitive.** `device_tracker` entities log
  historical locations; the upstream HA core integrations record
  every state change (typically with a default 10-day history
  retention). The recipe recommends turning off HA's default
  zone-tracking + history for `device_tracker.*` entities
  (Settings → Devices & Services → `<device>` → History → set
  to "No history"). The `rc_presence_*` contract tiles stay
  local.
- **No cloud sync.** None of the three upstream paths (Bluetooth
  LE tracking, Wi-Fi presence via nmap/ping, router-side
  device_tracker) phone home to a cloud service. All three are
  local-network only. The contract tiles (`rc_presence_*`)
  stay inside the HA instance.
- **The one exception** — AsusWRT / UniFi / MikroTik integrations
  may log to their respective vendor clouds if the operator
  enables that on the router itself (AsusWRT-Merlin has
  AiCloud, UniFi has cloud logging, MikroTik has The Dude).
  The recipe ships with all of these OFF by default; the
  operator can opt in on the router side if desired. RoamCore
  itself does not interact with any vendor cloud.
- **No MAC / serial / device-id captured by RoamCore.** The
  contract intentionally publishes only the high-level
  presence summary (per-person state, anyone-home, only-driver,
  persons-home-count, last-arrival, last-departure, all-away,
  refresh-now button, occupied-threshold select). The raw MAC
  addresses / serial numbers / device IDs of the upstream
  device_tracker entities stay on the HA instance and are not
  published to any external service.
- **No vendor / phone-model double-stamping.** No `bluetooth`,
  `bt`, `wifi`, `wlan`, `arp`, `nmap`, `ping`, `asuswrt`,
  `ubiquiti`, `unifi`, `mikrotik`, `iphone`, `android`,
  `pixel`, `galaxy` appears in any `rc_presence_*` entity,
  OpenClaw summary key, or dashboard tile beyond the subsystem
  prefix `rc_presence_*`. The contract is intentionally vendor-
  neutral per `docs/reference/rc-entity-naming.md`.

## §10 Promoting to tier-a

When a real Bluetooth + Wi-Fi bench lands (likely 2 BLE
devices + a Wi-Fi router + an ESPHome Bluetooth proxy —
exactly what the §2 prerequisites describe), this connection
is the candidate to promote to tier-a:

1. Add a native `config_flow.py` (or a thin wrapper around the
   upstream HA core integrations) that walks the operator
   through: choosing Path A vs Path B vs Path C + per-person
   device declaration (which person + which upstream
   device_tracker maps to that person) + declaring the driver
   for the `only_driver_home` helper + setting the initial
   `occupied_threshold_minutes`.
2. Add a RoamCore-owned bench fixture (a CI bench container
   with 2 simulated BLE devices + a Wi-Fi router mock that
   returns canned device_tracker responses).
3. Add an integration test that asserts the `rc_presence_*`
   contract entities appear after a synthetic
   `bluetooth_le_tracker` + `nmap_device_tracker` poll with
   canned fixture responses (Path A's YAML path AND Path B's
   config_flow path AND Path C's per-router config_flow path).
4. Flip `tier_requirements` to include `working_config_flow` +
   `integration_test_passes` + `no_manual_yaml_required`.
5. Drop `tier_warnings` entries that mention
   `no_real_presence_devices_for_integration_test` /
   `recipe_depends_on_user_declaring_persons_and_devices` /
   `bluetooth_vs_wifi_path_choice` /
   `false_positives_on_screensaver_sleep`.
6. Flip `status` from `beta` to `shipped`.
7. Keep `wizard.one_tap: false` because the operator's
   per-person device declaration + Path A-vs-B-vs-C choice is
   personal — even at tier-a, one-tap install is misleading
   if the per-person device declaration is a personal-taste
   choice. The wizard can pre-fill the upstream integration
   install but the per-person declaration is operator-driven.

Until then, this stays at tier-b (beta, recipe) — the recipe
is sound, the contract is honest, and we don't claim one-tap
coverage we don't have.