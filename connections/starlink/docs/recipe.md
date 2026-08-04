# Starlink — tier-b recipe connection

**Tier:** B (recipe; Path A `starlink_mini_only` is the tier-a
promotion candidate)
**Audience:** A RoamCore user who has a Starlink Gen-2 / Gen-3
terminal (or the round "Dishy" Gen-1 with limitations) and wants
RoamCore to handle the sleep-timer + bring-back-up + signal-snapshot
story that powers the `rc_net_starlink_*` contract tiles + OpenClaw
mobile-internet queries.

This howto is mirrored into `docs/connections/starlink.md` by the
catalog cron (`scripts/build_catalog.py`) so it shows up under the
public docs site's "Connections" section. Keep this recipe as the
source of truth.

## Choose your setup

The RoamCore setup wizard asks ONE question first: **how do you want
to use Starlink in the van?** Three answers, three different install
paths. Pick the one that matches your van.

| Path | When to pick it | Time | Needs |
|---|---|---|---|
| **A - `starlink_mini_only`** | You use the Starlink dish's built-in Wi-Fi router as the only router in the van. No separate router, no VM in the data path. | ~10 min | Nothing (RoamCore auto-detects the Starlink local API at `192.168.100.1`) |
| **B - `separate_router`** | You have your own router (Peplink / GL.iNet / TP-Link / etc.) and a controllable smart plug behind the Starlink PSU (or behind the router only). | ~25 min | The `switch.*` entity ID of your smart plug |
| **C - `vp2430_vm_router`** | You run an OpenWrt VM (VMID 100 on the VP2430 Proxmox host) as the LAN router, with Starlink as the WAN upstream. | ~30 min | OpenWrt API URL + bearer token (see `connections/openwrt-controls`) |

### Decision tree

```
Are you using the Starlink router as the only Wi-Fi in the van?
+- YES  -> Path A (starlink_mini_only)  -> see "Path A" below
+- NO
    +- Do you have a third-party router?     -> Path B (separate_router)  -> see "Path B" below
    +- Do you run a VM router in the VP2430? -> Path C (vp2430_vm_router) -> see "Path C" below
```

> All three paths are **idempotent** - re-running the wizard step
> is safe (re-detects, re-confirms, no duplicate entities).
>
> All three paths give you the **`rc_net_starlink_*` contract tiles**
> RoamCore is known for: sleep state, allow-sleep toggle, one-tap
> wake-for-30-min button, reachability, signal %, quiet-hours window.

## What is Starlink in RoamCore?

Starlink (<https://www.starlink.com/>) is SpaceX's low-earth-orbit
satellite internet terminal. The Gen-2 / Gen-3 hardware ships as a
dish + power supply + Wi-Fi router. Power draw is non-trivial at idle
(20-40 W on Gen-2; 30-60 W on Gen-3 with heating cycles), so leaving
the dish on 24/7 drains a van battery faster than most people expect.

In RoamCore, Starlink is the long-range mobile-internet slice for vans
that go off-grid:

- **Sleep timer** powers the dish down during quiet hours (or under
  Stealth mode) to save battery.
- **Wake on demand** is a one-tap "wake for 30 minutes" affordance for
  remote access, video calls, or streaming when the rest of the
  internet is congested.
- **Mode-aware behavior** skips sleep while Travel mode (you may need
  remote access mid-drive) and respects Stealth silent hours.
- **Reachability + signal snapshot** lets OpenClaw answer "is starlink
  on?" and "what's the signal %?" without you having to check the app.

RoamCore does **not** ship a Starlink terminal of its own. There is no
canonical upstream HA integration for the operator-side power-cycle
path that Path B recipes (the operator's plug choice is unconstrained
- TP-Link / Shelly / Sonoff / Zigbee / Modbus / a mechanical relay / a
DC switch with a Tail / ...). So we publish recipes that walk you
through the wiring, then layer a small contract on top: the
`rc_net_starlink_*` dashboard tiles + the OpenClaw queries ("is
starlink on?", "wake starlink for 30 minutes", "what's the signal?")
that bind to those contract entities.

**Why tier-b:** RoamCore has no real Starlink terminal on the bench to
integration-test against, no native HA integration to point at, and
the operator's smart-plug choice is unconstrained - so the
audit-recommended config_flow can't be canonical here. **Path A
(`starlink_mini_only`) is the tier-a promotion candidate** because it
doesn't depend on any operator wiring - RoamCore can ship the contract
entities directly from the Starlink local HTTP API. The promotion
outline at the bottom of this recipe describes exactly what needs to
happen to flip this to tier-a.

## Prerequisites

Before starting the recipe, make sure you have:

- **Starlink Gen-2 or Gen-3 terminal** (Path A and Path C's signal
  stats; works on Gen-1 too but with a warning that dish-status.json
  is unreachable).
- **A controllable smart plug / relay / DC switch** (Path B only).
  Anything HA can switch works. Common choices:
  - **TP-Link Kasa** (Wi-Fi plug, easiest; HA core `tplink` integration
    ships in 2023.3).
  - **Shelly Plug-S / Plug-US** (Wi-Fi, REST/MQTT-native; HA core
    `shelly` integration since 2022.2).
  - **Sonoff POW / S31** (Wi-Fi, flashed with ESPHome or via the
    `sonoff` custom-component).
  - **Zigbee smart plug** (Aqara / Innr / Nous / IKEA - pick one
    that the Zigbee Home Automation integration in HA can pair).
  - **Modbus DC switch** (for 12 V direct-from-battery installs).
- **Starlink's local HTTP API reachable from HA** (Path A and Path C's
  signal-stats wiring; Gen-2/Gen-3 only): the router serves
  `http://192.168.100.1/` on the Starlink LAN. If your HA host is on
  a different VLAN, route the Starlink LAN to HA (or put HA on the
  Starlink LAN).
- **A spare 12 V / mains outlet** near where the Starlink PSU lives
  (Path B only - the smart plug has to physically sit between the
  PSU and its power source).
- **(Path C only) OpenWrt VM running on the VP2430** (VMID 100). See
  `connections/openwrt-controls` for the upstream integration.
- **(Recommended) A UPS / battery monitor** - see "What wakes me up
  if Starlink goes down?" in the Troubleshooting section.

## Path A - Starlink Mini as the only router (`starlink_mini_only`)

The simplest setup: use the Starlink dish's built-in Wi-Fi router as
the only router in the van. No smart plug, no extra router. RoamCore
reads signal + reachability directly from the Starlink local HTTP API
at `http://192.168.100.1:80`. This is the tier-a promotion candidate.

### A.1 - Plug in the Starlink ethernet adapter

The Starlink local API is reachable over the dish's ethernet port.
Plug the official Starlink ethernet adapter into the dish (if not
already) and connect the dish to power. Wait for the dish to come
online (status light on the router goes solid white).

### A.2 - Run the RoamCore setup wizard

In HA -> **Settings -> Devices & Services -> RoamCore -> Configure ->
Starlink**, pick **"Starlink Mini as my only router"**.

The wizard will:

1. Hit `http://192.168.100.1:80/` with **3 retries and backoff** to
   verify reachability within **10 seconds**.
2. If reachable, write `input_text.rc_net_starlink_api_url =
   http://192.168.100.1:80` to HA.
3. Create a REST sensor pulling `dish-status.json` once per minute
   (resource_template keyed off the input_text, so you can change the
   URL without code).
4. Create 3 template sensors:
   - `binary_sensor.rc_net_starlink_reachable`
   - `sensor.rc_net_starlink_signal_pct`
   - `sensor.rc_net_starlink_sleep_state`
5. Surface a **Gen-1 warning** if `dish-status.json` returns 404 (the
   signal tile will show `unknown`; reachability still works).

### A.3 - Verify

1. Open the RoamCore dashboard -> **Networking** section.
2. The `rc_net_starlink_*` tiles should be visible. If any are
   grayed out, check the Troubleshooting section.
3. `binary_sensor.rc_net_starlink_reachable` should flip ON within
   ~2 seconds (the REST sensor updates every minute; the binary
   sensor surfaces "ON if last read was within 60 s").

### A.4 - Errors and what to do

- **"We can't reach your Starlink router at http://192.168.100.1:80"**
  - the wizard retried 3x with backoff and never got a response.
  Make sure the ethernet adapter is plugged in, the dish is online
  (solid white status light), and your computer can reach the
  Starlink network. Gen-1 (round "Dishy") has no local API at all -
  Path A still works for reachability, but the signal tile shows
  unknown.
- **Gen-1 detected** - the wizard detected the router doesn't
  expose `dish-status.json`. The signal_pct tile will show unknown;
  reachability still works. Everything else (OpenClaw queries,
  quiet-hours, mode-aware behavior) works fine.

## Path B - Separate router (smart plug behind PSU / router)

The legacy RoamCore recipe path: you own a third-party router and a
controllable smart plug behind the Starlink PSU (or behind the
router only). RoamCore maps `switch.rc_net_starlink_plug` to your
plug and wires the sleep + wake + signal + quiet-hours contract.

### B.1 - Wire the smart plug behind the PSU or the router only

You have two options:

- **Router-only power cycle** (recommended for the gentlest sleep):
  power-cycle only the router, leaving the dish itself connected.
  The dish stows; the router doesn't waste 5 W on idle DHCP; power-up
  is ~5 seconds.
- **Full PSU power cycle** (for the deepest sleep): power-cycle the
  entire PSU. Dish + router are fully off; power-up is ~90 seconds
  (dish boot + satellite acquisition + DHCP).

### B.2 - Pair the smart plug with HA

Pick whichever integration matches your plug:

- **TP-Link Kasa** -> HA -> **Settings -> Devices & Services -> Add
  Integration -> TP-Link Kasa Smart Home**. Sign in (or use the
  local-only path), pick the plug. The plug shows up as
  `switch.<name>_plug` (e.g. `switch.starlink_plug`).
- **Shelly** -> HA -> **Settings -> Devices & Services -> Add
  Integration -> Shelly**. Add the device by IP or via the cloud; you
  get `switch.shelly_plug_relay` or similar.
- **Sonoff** (custom component / ESPHome) -> follow the component's
  pairing flow.
- **Zigbee** -> HA -> **Settings -> Devices & Services -> Zigbee Home
  Automation -> Add Device**. Put the plug in pairing mode.

Note the `entity_id` your plug ended up as - you need it in B.3.

### B.3 - Run the RoamCore setup wizard

In HA -> **Settings -> Devices & Services -> RoamCore -> Configure ->
Starlink**, pick **"I have a separate router"**.

The wizard will:

1. Ask for your plug's `entity_id` (e.g. `switch.kasa_plug`).
2. Validate the plug entity is **exposed + controllable** (HA
   states registry says `switch.*` and current state is `on` / `off`,
   not `unavailable`).
3. Verify the Starlink local API is reachable for the signal_pct
   tile (gracefully degrades to unknown if unreachable).
4. Create `switch.rc_net_starlink_plug` (a template helper that maps
   to your plug), plus the rest of the `rc_net_starlink_*` contract.

### B.4 - Create the rest of the `rc_net_starlink_*` contract

In HA -> **Helpers**, create the following (the recipe ships copy-
pastable YAML for these in the contract section below):

- `input_boolean.rc_net_starlink_allow_sleep` - ON means the sleep
  timer is armed; OFF means always-on.
- `input_datetime.rc_net_starlink_quiet_start` / `_quiet_end` - the
  quiet-hours window the sleep timer honors.
- `sensor.rc_net_starlink_sleep_state` - template sensor reporting
  `awake | asleep | waking`, sourced from the plug state + a
  `timer.rc_net_starlink_wake_30_min` and the `input_boolean`.
- `button.rc_net_starlink_wake_30_min` - button that starts the
  30-minute wake timer.
- `binary_sensor.rc_net_starlink_reachable` - template sensor
  reporting ON if the plug state has been confirmed in the last
  60 seconds.
- `sensor.rc_net_starlink_signal_pct` - REST sensor pulling
  `http://192.168.100.1/api/console/dish-status.json` once per minute.

### B.5 - Enable the automations

The recipe ships three automations:

- Sleep-during-quiet-hours (when `allow_sleep` ON and inside the
  quiet-hours window and not in Travel mode).
- Wake-for-30-min-on-demand (button press -> plug ON for 30 min, then
  back to whatever the sleep timer says).
- Mode-aware-exception (skip sleep in Travel mode unless
  `binary_sensor.rc_power_alternator_charging` is ON; break sleep
  if `binary_sensor.rc_net_internet_reachable` is OFF for >5 min).

### B.6 - Verify

1. Open the RoamCore dashboard -> **Networking** section.
2. The `rc_net_starlink_*` tiles should be visible.
3. Tap the wake button. The plug should click ON within ~2 seconds,
   the wake timer should start, and the sleep-state tile should
   show `awake` after the dish acquires a signal (~90 s for Gen-3,
   ~30 s for Gen-2).

## Path C - VM router inside the VP2430 (`vp2430_vm_router`)

You're running an OpenWrt VM (VMID 100 on the VP2430 Proxmox host) as
the LAN router, with Starlink as the WAN upstream. RoamCore reads WAN
state + signal from the OpenWrt API (not a smart plug) - see
`connections/openwrt-controls` for the upstream contract.

### C.1 - Generate an OpenWrt API bearer token

On the OpenWrt VM (see `connections/openwrt-controls` docs), generate
a bearer token with read access to:

- `/cgi-bin/luci/admin/status` (WAN state)
- `/cgi-bin/luci/admin/network/wan` (WAN IP / interface)

The token goes into the wizard in step C.3 (and is stored in your
Home Assistant user secrets, not in the RoamCore repo).

### C.2 - Confirm Starlink is the WAN upstream

The OpenWrt VM's WAN interface should be configured to use Starlink
as the upstream (the Starlink dish's ethernet adapter feeds into the
OpenWrt VM's WAN port). If the dish is in bypass / router-only mode,
the OpenWrt VM picks up a DHCP lease from the Starlink router.

### C.3 - Run the RoamCore setup wizard

In HA -> **Settings -> Devices & Services -> RoamCore -> Configure ->
Starlink**, pick **"VM router inside the VP2430"**.

The wizard will:

1. Ask for your OpenWrt API URL (e.g.
   `http://192.168.1.250/cgi-bin/luci`) and bearer token.
2. Verify the OpenWrt API is reachable within 10 seconds (3x retries
   with backoff).
3. Write 2 `input_text` helpers:
   - `input_text.rc_net_starlink_openwrt_api_url`
   - `input_text.rc_net_starlink_openwrt_api_token`
4. Create a REST sensor chain through the OpenWrt API for WAN
   reachable / WAN IP / WAN interface state.
5. Verify the Starlink local API is reachable for the signal_pct
   tile (gracefully degrades to unknown if unreachable).
6. Create the rest of the `rc_net_starlink_*` contract:
   - `sensor.rc_net_starlink_sleep_state` (sourced from OpenWrt WAN
     state, not a smart plug)
   - `binary_sensor.rc_net_starlink_reachable` (sourced from OpenWrt
     WAN reachable)
   - `sensor.rc_net_starlink_signal_pct` (still from Starlink local
     API at `192.168.100.1`)
   - `input_datetime.rc_net_starlink_quiet_start` / `_quiet_end`

### C.4 - Verify

1. Open the RoamCore dashboard -> **Networking** section.
2. The `rc_net_starlink_*` tiles should be visible.
3. `binary_sensor.rc_net_starlink_reachable` should track the
   OpenWrt-reported WAN state within ~2 seconds.

### C.5 - Errors and what to do

- **"We can't reach the OpenWrt API at http://..."** - the wizard
  retried 3x with backoff and never got a response. Check that the
  VM is running on the VP2430 (`qm guest list` for VMID 100) and
  the bearer token is correct.
- **OpenWrt API returns 401** - the bearer token is wrong or
  expired. Re-generate it in step C.1.
- **Starlink local API unreachable** - the signal_pct tile will show
  unknown. OpenWrt-driven WAN state still works. Plug the ethernet
  adapter in if you want signal stats (Gen-2/Gen-3 only).

## §4 RoamCore contract entities

The full listing the wizard + dashboard + OpenClaw rely on:

| Entity | Type | States | Source |
|---|---|---|---|
| `sensor.rc_net_starlink_sleep_state` | sensor | `awake \| asleep \| waking` | template over plug state (Path B) / OpenWrt WAN state (Path C) / always-awake (Path A) + wake timer |
| `switch.rc_net_starlink_allow_sleep` | switch | ON / OFF | `input_boolean` flag |
| `button.rc_net_starlink_wake_30_min` | button | (press) | HA timer + automation |
| `binary_sensor.rc_net_starlink_reachable` | binary_sensor | ON / OFF | Path A: REST to `192.168.100.1`; Path B: HA last-seen check on plug entity; Path C: OpenWrt WAN reachable |
| `sensor.rc_net_starlink_signal_pct` | sensor | 0-100 | REST sensor to `dish-status.json` (all 3 paths) |
| `input_datetime.rc_net_starlink_quiet_start` | input_datetime | time | user-set |
| `input_datetime.rc_net_starlink_quiet_end` | input_datetime | time | user-set |

All grayed-out / `unknown` fallback when the smart-plug is undefined
(no plug paired, or HA's plug integration is in error state). Path A
fills in `binary_sensor.rc_net_starlink_reachable` from the Starlink
local API liveness check (HA's REST resource_template to
`192.168.100.1`).

### Copy-pasteable helper YAML (Path A + Path C)

Drop into `homeassistant/packages/roamcore_starlink.yaml`:

```yaml
# RoamCore Starlink contract helpers.
# All entities are vendor-neutral per docs/reference/rc-entity-naming.md.

input_text:
  # Path A only - Starlink Mini as the only router. The REST
  # resource_template below reads from this helper so the user can
  # change the URL without touching code.
  rc_net_starlink_api_url:
    name: Starlink local API URL (contract)
    initial: "http://192.168.100.1:80"
    icon: mdi:satellite-variant

  # Path C only - VM router inside the VP2430. Stores the OpenWrt
  # API URL + bearer token so the REST chain below can be rebuilt
  # without touching the YAML.
  rc_net_starlink_openwrt_api_url:
    name: Starlink -> OpenWrt API URL (contract)
    initial: ""
    icon: mdi:router-wireless
  rc_net_starlink_openwrt_api_token:
    name: Starlink -> OpenWrt API token (contract)
    initial: ""
    icon: mdi:key-variant

input_boolean:
  rc_net_starlink_allow_sleep:
    name: Starlink allowed to sleep
    icon: mdi:satellite-variant

input_datetime:
  rc_net_starlink_quiet_start:
    name: Starlink quiet hours start
    has_time: true
    icon: mdi:weather-night
  rc_net_starlink_quiet_end:
    name: Starlink quiet hours end
    has_time: true
    icon: mdi:weather-sunset

timer:
  rc_net_starlink_wake_30_min:
    name: Starlink wake window
    duration: "00:30:00"
    icon: mdi:satellite-uplink

template:
  - binary_sensor:
      - name: Starlink reachable (contract)
        unique_id: rc_net_starlink_reachable
        state: >
          {{ states('switch.rc_net_starlink_plug') not in ['unknown', 'unavailable'] }}
        device_class: connectivity
        icon: mdi:satellite-variant
  - sensor:
      - name: Starlink sleep state (contract)
        unique_id: rc_net_starlink_sleep_state
        state: >
          {% if is_state('switch.rc_net_starlink_plug', 'on') %}
            {% if states('timer.rc_net_starlink_wake_30_min') == 'active' %}
              waking
            {% else %}
              awake
            {% endif %}
          {% else %}
            asleep
          {% endif %}
        icon: mdi:satellite-variant

button:
  - name: Wake Starlink for 30 minutes
    unique_id: rc_net_starlink_wake_30_min
    icon: mdi:satellite-uplink
```

### Signal-stats wiring (Gen-2/Gen-3 only)

Drop alongside the helper YAML in the same package:

```yaml
rest:
  # Path A - pulls dish-status.json from the Starlink local API.
  # resource_template reads the URL from the input_text helper so
  # the user can change it without touching YAML.
  - resource_template: "{{ states('input_text.rc_net_starlink_api_url') }}/api/console/dish-status.json"
    scan_interval: 60
    sensor:
      - name: Starlink REST (contract)
        unique_id: rc_net_starlink_rest
        device_class: connectivity
        state: >
          {% if value_json is mapping %}
            ok
          {% else %}
            unavailable
          {% endif %}
        icon: mdi:satellite-variant

  # Shared signal_pct sensor (all 3 paths).
  - resource_template: "http://192.168.100.1/api/console/dish-status.json"
    scan_interval: 60
    sensor:
      - name: Starlink signal pct (contract)
        unique_id: rc_net_starlink_signal_pct
        unit_of_measurement: "%"
        device_class: signal_strength
        state: >
          {% set v = value_json.get('dish', {}).get('snr_db', 0) | float(0) %}
          {% set pct = (max(0, min(100, (v + 3) * 25)) ) | round(0) %}
          {{ pct }}
        icon: mdi:satellite-variant
```

## §5 Automations

Three sample automations, copy-pasteable into
`homeassistant/automations/roamcore_starlink_*.yaml`:

### §5.1 - Sleep during quiet hours

```yaml
alias: Starlink - sleep during quiet hours
mode: single
trigger:
  - platform: time
    at: input_datetime.rc_net_starlink_quiet_start
condition:
  - condition: state
    entity_id: input_boolean.rc_net_starlink_allow_sleep
    state: "on"
  - condition: template
    value_template: >
      {{ not is_state('input_select.rc_mode', 'travel')
         or is_state('binary_sensor.rc_power_alternator_charging', 'on') }}
action:
  - service: switch.turn_off
    target:
      entity_id: switch.rc_net_starlink_plug
```

### §5.2 - Wake for 30 minutes on demand (button)

```yaml
alias: Starlink - wake for 30 minutes
mode: single
trigger:
  - platform: state
    entity_id: button.rc_net_starlink_wake_30_min
action:
  - service: switch.turn_on
    target:
      entity_id: switch.rc_net_starlink_plug
  - service: timer.start
    target:
      entity_id: timer.rc_net_starlink_wake_30_min
```

### §5.3 - Mode-aware break-sleep (lost WAN)

```yaml
alias: Starlink - break sleep if no other internet
mode: single
trigger:
  - platform: state
    entity_id: binary_sensor.rc_net_internet_reachable
    to: "off"
    for: "00:05:00"
condition:
  - condition: state
    entity_id: input_boolean.rc_net_starlink_allow_sleep
    state: "on"
action:
  - service: switch.turn_on
    target:
      entity_id: switch.rc_net_starlink_plug
  - service: timer.start
    target:
      entity_id: timer.rc_net_starlink_wake_30_min
  - service: persistent_notification.create
    data:
      title: RoamCore - Starlink woke up
      message: >-
        No other internet reachable for 5 min; woke Starlink for
        30 min so remote access keeps working.
```

## §6 Troubleshooting

- **Wizard says "We can't reach your Starlink router at 192.168.100.1".**
  The wizard retried 3x with backoff (1s, 2s, 4s) and never got a
  response. Make sure:
  - The ethernet adapter is plugged in (Path A and Path C).
  - The dish is online (solid white status light).
  - Your computer can reach the Starlink network (`ping
    192.168.100.1` from your laptop on the Starlink LAN).
  - On Gen-1 (round "Dishy"), the local API doesn't exist; the
    signal tile will be grayed out but reachability still works for
    Path A. For Paths B / C, the plug / OpenWrt chain still works
    even on Gen-1.
- **Starlink not coming back up after wake.** The dish takes 30-90 s
  to acquire a satellite after a full PSU power cycle (Path B). If
  it never comes up, check: is the dish's view of the sky
  obstructed? Is the dish in stow mode (Gen-3 detects motion +
  parking and stows automatically)? Is the smart-plug actually
  passing current (cheap plugs can fail intermittently under
  inductive load - swap to a different plug)?
- **`rc_net_starlink_reachable` stays OFF.** The plug's underlying
  HA entity is in `unavailable` (Path B) - the plug integration
  lost its pairing. Re-pair the plug in the integration's settings.
  For Path A, the REST resource_template is failing - check the
  input_text helper's URL. For Path C, check the OpenWrt API URL +
  bearer token.
- **Wizard says "The plug entity 'switch.foo' is currently
  unavailable"**. The plug is paired but the integration can't talk
  to it right now. Make sure the plug is powered on and the
  integration can reach it (Wi-Fi / Zigbee / Modbus link), then
  re-run the wizard.
- **Wizard says "We can't find the plug entity 'switch.foo' in
  Home Assistant"**. The entity id is wrong. Go to **Settings ->
  Devices & Services -> Entities** and find the correct entity id
  for your plug.
- **Wizard says "The plug entity 'binary_sensor.bar' exists but
  isn't controllable"**. You picked a sensor, not a switch. Pick
  a `switch.*` entity.
- **Wizard says "We can't reach the OpenWrt API at http://..."**
  (Path C). Check that the OpenWrt VM is running on the VP2430
  (VMID 100, `qm guest list` on the Proxmox host) and the bearer
  token is correct.
- **Signal pct stuck at 0.** Starlink's local HTTP API may be
  blocked (firewall, VLAN routing), or the JSON schema changed in
  a firmware update (Gen-3 firmware 2024+ added new fields). Check
  HA -> **Developer Tools -> Template** against the same REST URL and
  inspect the JSON; substitute the working field name.
- **Automation fires in Travel mode.** Travel mode should
  suppress sleep *unless* alternator charging is active. Verify
  `input_select.rc_mode` is in the `travel` state, and verify
  `binary_sensor.rc_power_alternator_charging` is reporting
  sensibly.
- **Plug integration drops during inverter switching.** Some Wi-Fi
  plugs drop their connection when the inverter cycles. Add a
  reboot automation for the plug on inverter-switch events, or
  prefer a wired (Modbus / Zigbee / Z-Wave) plug over Wi-Fi.
- **What wakes me up if Starlink goes down?** The "break sleep"
  automation is the last-line-of-defense automation: if no other
  internet is reachable for 5 min, wake Starlink for 30 min. That's
  the contract layer's answer to "remote access must keep working".
  If you'd rather not auto-wake on full disconnect, flip the
  `allow_sleep` toggle OFF before leaving the van.

## §7 Privacy

- **Local only.** No Starlink cloud API calls. No telemetry to
  RoamCore. No SSID, MAC, IP, or dish serial in any contract
  entity.
- **Signal stats** come from Starlink's local HTTP API
  (`http://192.168.100.1/...`), which serves the LAN only - no
  internet round-trip.
- **The smart-plug integration** uses whatever protocol your plug
  speaks (Kasa cloud, Shelly cloud, local Zigbee, local Modbus).
  RoamCore does not add any cloud dependency on top - if your
  plug uses a cloud, that's the plug's existing behavior, not
  RoamCore's.
- **The OpenWrt API token** (Path C) is stored in your Home Assistant
  user secrets, not in the RoamCore repo. It never leaves your
  LAN.
- **No MAC / SSID / serial** is captured in any `rc_net_starlink_*`
  entity, OpenClaw summary key, or dashboard tile. The contract is
  intentionally vendor-neutral.

## Promotion to tier-a (outline)

When a real Starlink terminal lands on the bench (likely via
`testcontainers/grpc-starlink-dish` with a synthetic
`dish-status.json` fixture, or a recorded capture), this connection
is the candidate to promote to tier-a:

1. Add a native `config_flow.py` (or a thin wrapper around the
   upstream Starlink community integration if one lands in core) that
   walks the operator through picking the smart-plug integration +
   creating the `switch.rc_net_starlink_plug` helper. The Path A
   (`starlink_mini_only`) wizard already shipped in Wave 9 #108 is
   the seed - it just needs an integration test against a real
   Starlink local API or recorded `dish-status.json` fixture.
2. Add an integration test that asserts the `rc_net_starlink_*`
   contract entities appear after a synthetic plug-toggle + a
   synthetic `dish-status.json` payload.
3. Flip `tier_requirements` to include `working_config_flow` +
   `integration_test_passes` + `no_manual_yaml_required`.
4. Drop `tier_warnings` entries that mention no-real-terminal /
   recipe-depends-on-user-smart-plug.
5. Flip `status` from `beta` to `shipped`.
6. Flip `wizard.one_tap` to `true`.

Until then, this stays at tier-b (beta, recipe) - the recipe is
sound, the contract is honest, and we don't claim one-tap coverage
we don't have.