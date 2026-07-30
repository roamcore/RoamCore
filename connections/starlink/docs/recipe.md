# Starlink — tier-b recipe connection

**Tier:** B (recipe)
**Audience:** A RoamCore user who has a Starlink Gen-2 or Gen-3
terminal, a controllable smart plug / relay / DC switch behind the
Starlink PSU (or router-only power), and wants the sleep-timer +
bring-back-up + signal-snapshot story that powers the RoamCore
`rc_net_starlink_*` contract tiles + OpenClaw mobile-internet queries.

This howto is mirrored into `docs/connections/starlink.md` by the
catalog cron (`scripts/build_catalog.py`) so it shows up under the
public docs site's "Connections" section. Keep this recipe as the
source of truth.

## What is Starlink in RoamCore?

Starlink (<https://www.starlink.com/>) is SpaceX's low-earth-orbit
satellite internet terminal. The Gen-2 / Gen-3 hardware ships as a
dish + power supply + Wi-Fi router. Power draw is non-trivial at idle
(20–40 W on Gen-2; 30–60 W on Gen-3 with heating cycles), so leaving
the dish on 24/7 drains a van battery faster than most people expect.
The community pattern is to put a controllable smart plug behind the
PSU and schedule it.

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
path that this connection recipes (the operator's plug choice is
unconstrained — TP-Link / Shelly / Sonoff / Zigbee / Modbus / a
mechanical relay / a DC switch with a Tail / ...). So we publish a
recipe that walks you through the wiring, then layer a small contract
on top: the `rc_net_starlink_*` dashboard tiles + the OpenClaw queries
("is starlink on?", "wake starlink for 30 minutes", "what's the
signal?") that bind to those contract entities.

**Why tier-b:** RoamCore has no real Starlink terminal on the bench to
integration-test against, no native HA integration to point at, and
the operator's smart-plug choice is unconstrained — so the
audit-recommended config_flow can't be canonical here. The recipe is
sound (it leans on whichever plug integration the operator already
uses + Starlink's well-understood local HTTP API), but we cannot claim
one-tap automation. The promotion outline at the bottom of this recipe
describes exactly what needs to happen to flip this to tier-a.

**Two install paths:**

- **Path A — Router-only power cycle** (recommended for the gentlest
  sleep): power-cycle only the router, leaving the dish itself
  connected. The dish stows; the router doesn't waste 5 W on idle
  DHCP; power-up is ~5 seconds.
- **Path B — Full PSU power cycle** (for the deepest sleep): power-
  cycle the entire PSU. Dish + router are fully off; power-up is
  ~90 seconds (dish boot + satellite acquisition + DHCP).

## Prerequisites

Before starting the recipe, make sure you have:

- **Starlink Gen-2 or Gen-3 terminal.** Gen-1 (the round "dishy"
  with the round router) has no local HTTP API — the signal tile
  will be grayed out and the rest of the recipe still works.
- **A controllable smart plug / relay / DC switch.** Anything HA can
  switch works. Common choices:
  - **TP-Link Kasa** (Wi-Fi plug, easiest; HA core `tplink` integration
    ships in 2023.3).
  - **Shelly Plug-S / Plug-US** (Wi-Fi, REST/MQTT-native; HA core
    `shelly` integration since 2022.2).
  - **Sonoff POW / S31** (Wi-Fi, flashed with ESPHome or via the
    `sonoff` custom-component).
  - **Zigbee smart plug** (Aqara / Innr / Nous / IKEA — pick one
    that the Zigbee Home Automation integration in HA can pair).
  - **Modbus DC switch** (for 12 V direct-from-battery installs — a
    smart DC switch with a Modbus interface; talk to your installer).
- **Starlink's local HTTP API reachable from HA** (Path A and Path B's
  signal-stats wiring; Gen-2/Gen-3 only): the router serves
  `http://192.168.100.1/api/console/dish-status.json` on the Starlink
  LAN. If your HA host is on a different VLAN, route the Starlink LAN
  to HA (or put HA on the Starlink LAN).
- **A spare 12 V / mains outlet** near where the Starlink PSU lives
  — the smart plug has to physically sit between the PSU and its
  power source.
- **(Recommended) A UPS / battery monitor** — see "What wakes me up
  if Starlink goes down?" in §6.

## Path A — Router-only power cycle (recommended)

The default install for RoamCore users who want the gentlest sleep.

### A.1 — Wire the smart plug behind the router only

1. Unplug the router-side cable from the Starlink PSU (the cable that
   goes from the PSU's "router" port to the router's WAN port).
2. Plug a short extension / splitter into the PSU's router port if
   needed; route the existing router cable AND a new cable to the
   smart plug's input. Plug the smart plug's output into the
   router's WAN port.
3. Or — simpler — put the smart plug between the PSU's mains input
   and the wall (full PSU power cycle, Path B below). The recipe
   works either way; Path A just keeps the dish powered and gives
   faster wake times.

### A.2 — Pair the smart plug with HA

Pick whichever integration matches your plug:

- **TP-Link Kasa** → HA → **Settings → Devices & Services → Add
  Integration → TP-Link Kasa Smart Home**. Sign in (or use the
  local-only path), pick the plug. The plug shows up as
  `switch.<name>_plug` (e.g. `switch.starlink_plug`).
- **Shelly** → HA → **Settings → Devices & Services → Add
  Integration → Shelly**. Add the device by IP or via the cloud; you
  get `switch.shelly_plug_relay` or similar.
- **Sonoff** (custom component / ESPHome) → follow the component's
  pairing flow. You get `switch.sonoff_<id>_relay` or
  `switch.<esphome_name>_relay`.
- **Zigbee** → HA → **Settings → Devices & Services → Zigbee Home
  Automation → Add Device**. Put the plug in pairing mode. You get
  `switch.<ieee>_plug` or whatever the integration renames it to.

Note the entity_id your plug ended up as — you need it in A.3.

### A.3 — Create the helper `switch.rc_net_starlink_plug`

In HA → **Settings → Devices & Services → Helpers → Create Helper →
Template → Switch**, with:

- Entity: `switch.<your_plug_entity_id>` (from A.2)
- Name: `Starlink plug (contract)`
- Icon: `mdi:satellite-variant`

This indirection lets the recipe's automations refer to
`switch.rc_net_starlink_plug` without depending on which plug
integration you used — if you swap plugs later, you only update the
template helper.

### A.4 — Create the rest of the `rc_net_starlink_*` contract

In HA → **Helpers**, create the following (the recipe ships copy-
pastable YAML for these in §4.1 below):

- `input_boolean.rc_net_starlink_allow_sleep` — ON means the sleep
  timer is armed; OFF means always-on.
- `input_datetime.rc_net_starlink_quiet_start` / `_quiet_end` — the
  quiet-hours window the sleep timer honors.
- `sensor.rc_net_starlink_sleep_state` — template sensor reporting
  `awake | asleep | waking`, sourced from the plug state + a
  `timer.rc_net_starlink_wake_30_min` and the `input_boolean`.
- `button.rc_net_starlink_wake_30_min` — button that starts the
  30-minute wake timer.
- `binary_sensor.rc_net_starlink_reachable` — template sensor
  reporting ON if the plug state has been confirmed in the last
  60 seconds (HA's standard "entity is alive" check).
- `sensor.rc_net_starlink_signal_pct` — REST sensor pulling
  `http://192.168.100.1/api/console/dish-status.json` once per minute
  and returning the `pop_ping_drop_rate` / `snr` / `obstruction_perc`
  snapshot as a 0–100 number (recipe §4.2).

### A.5 — Enable the recipe §5 automations

The recipe ships three automations in §5.1 / §5.2 / §5.3:

- Sleep-during-quiet-hours (when `allow_sleep` ON and inside the
  quiet-hours window and not in Travel mode and not in Stealth-only).
- Wake-for-30-min-on-demand (button press → plug ON for 30 min, then
  back to whatever the sleep timer says).
- Mode-aware-exception (skip sleep in Travel mode unless
  `binary_sensor.rc_power_alternator_charging` is ON; break sleep
  if `binary_sensor.rc_net_internet_reachable` is OFF for >5 min
  — someone else lost their internet, you don't have any either).

### A.6 — Verify

1. Open the RoamCore dashboard → **Networking** section.
2. The `rc_net_starlink_*` tiles should be visible. If any are
   grayed out, check §6 (Troubleshooting).
3. Tap the wake button. The plug should click ON within ~2 seconds,
   the wake timer should start, and the sleep-state tile should
   show `awake` after the dish acquires a signal (~90 s for Gen-3,
   ~30 s for Gen-2).
4. Wait 30 minutes (or set the timer to 1 minute for the test).
   The plug should click OFF and the sleep-state tile should show
   `asleep`.

## Path B — Full PSU power cycle

Identical to Path A except the smart plug sits between the wall /
12 V source and the PSU's mains input. Dish + router are fully off
during sleep; wake takes ~90 seconds (dish boot + satellite
acquisition + DHCP). Use this if you want the deepest possible
sleep — 0 W draw during the off period — and don't mind the longer
wake latency.

Everything else is the same. The recipe §5 automations don't care
which path you wired; they just toggle `switch.rc_net_starlink_plug`.

## §4 RoamCore contract entities

The full listing the wizard + dashboard + OpenClaw rely on:

| Entity | Type | States | Source |
|---|---|---|---|
| `sensor.rc_net_starlink_sleep_state` | sensor | `awake \| asleep \| waking` | template over plug state + wake timer |
| `switch.rc_net_starlink_allow_sleep` | switch | ON / OFF | `input_boolean` flag |
| `button.rc_net_starlink_wake_30_min` | button | (press) | HA timer + automation |
| `binary_sensor.rc_net_starlink_reachable` | binary_sensor | ON / OFF | HA last-seen check on plug entity |
| `sensor.rc_net_starlink_signal_pct` | sensor | 0–100 | REST sensor to `dish-status.json` |
| `input_datetime.rc_net_starlink_quiet_start` | input_datetime | time | user-set |
| `input_datetime.rc_net_starlink_quiet_end` | input_datetime | time | user-set |

All grayed-out / `unknown` fallback when the smart-plug is undefined
(no plug paired, or HA's plug integration is in error state).

### §4.1 — Copy-pasteable helper YAML

Drop into `homeassistant/packages/roamcore_starlink.yaml`:

```yaml
# RoamCore Starlink contract helpers (recipe §4.1).
# All entities are vendor-neutral per docs/reference/rc-entity-naming.md.

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

### §4.2 — Signal-stats wiring (Gen-2/Gen-3 only)

Drop alongside §4.1 in the same package:

```yaml
rest:
  - resource_template: http://192.168.100.1/api/console/dish-status.json
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

(`dish-status.json` schema varies by firmware; `snr_db` is the
most stable signal-quality proxy across versions. If your firmware
returns a different field, substitute and re-test.)

## §5 Automations

Three sample automations, copy-pasteable into
`homeassistant/automations/roamcore_starlink_*.yaml`:

### §5.1 — Sleep during quiet hours

```yaml
alias: Starlink — sleep during quiet hours
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

### §5.2 — Wake for 30 minutes on demand (button)

```yaml
alias: Starlink — wake for 30 minutes
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

### §5.3 — Mode-aware break-sleep (lost WAN)

```yaml
alias: Starlink — break sleep if no other internet
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
      title: RoamCore — Starlink woke up
      message: >-
        No other internet reachable for 5 min; woke Starlink for
        30 min so remote access keeps working.
```

## §6 Troubleshooting

- **Starlink not coming back up after wake.** The dish takes 30–90 s
  to acquire a satellite after a full PSU power cycle (Path B). If
  it never comes up, check: is the dish's view of the sky
  obstructed? Is the dish in stow mode (Gen-3 detects motion +
  parking and stows automatically)? Is the smart-plug actually
  passing current (cheap plugs can fail intermittently under
  inductive load — swap to a different plug)?
- **`rc_net_starlink_reachable` stays OFF.** The plug's underlying
  HA entity is in `unavailable` — the plug integration lost its
  pairing. Re-pair the plug in the integration's settings.
- **Signal pct stuck at 0.** Starlink's local HTTP API may be
  blocked (firewall, VLAN routing), or the JSON schema changed in
  a firmware update (Gen-3 firmware 2024+ added new fields). Check
  HA → **Developer Tools → Template** against the same REST URL and
  inspect the JSON; substitute the working field name.
- **Automation fires in Travel mode.** Travel mode should
  suppress sleep *unless* alternator charging is active. Verify
  `input_select.rc_mode` is in the `travel` state, and verify
  `binary_sensor.rc_power_alternator_charging` is reporting
  sensibly. (If you don't have a Victron / alternator monitor yet,
  set the Travel condition to `false` and rely on the user toggle.)
- **Plug integration drops during inverter switching.** Some Wi-Fi
  plugs drop their connection when the inverter cycles. Add a
  reboot automation for the plug on inverter-switch events, or
  prefer a wired (Modbus / Zigbee / Z-Wave) plug over Wi-Fi.
- **What wakes me up if Starlink goes down?** §5.3 is the
  last-line-of-defense automation: if no other internet is reachable
  for 5 min, wake Starlink for 30 min. That's the contract layer's
  answer to "remote access must keep working". If you'd rather
  not auto-wake on full disconnect, flip the `allow_sleep` toggle
  OFF before leaving the van.

## §7 Privacy

- **Local only.** No Starlink cloud API calls. No telemetry to
  RoamCore. No SSID, MAC, IP, or dish serial in any contract
  entity.
- **Signal stats** come from Starlink's local HTTP API
  (`http://192.168.100.1/...`), which serves the LAN only — no
  internet round-trip.
- **The smart-plug integration** uses whatever protocol your plug
  speaks (Kasa cloud, Shelly cloud, local Zigbee, local Modbus).
  RoamCore does not add any cloud dependency on top — if your
  plug uses a cloud, that's the plug's existing behavior, not
  RoamCore's.
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
   creating the `switch.rc_net_starlink_plug` helper.
2. Add an integration test that asserts the `rc_net_starlink_*`
   contract entities appear after a synthetic plug-toggle + a
   synthetic `dish-status.json` payload.
3. Flip `tier_requirements` to include `working_config_flow` +
   `integration_test_passes` + `no_manual_yaml_required`.
4. Drop `tier_warnings` entries that mention no-real-terminal /
   recipe-depends-on-user-smart-plug.
5. Flip `status` from `beta` to `shipped`.
6. Flip `wizard.one_tap` to `true`.

Until then, this stays at tier-b (beta, recipe) — the recipe is
sound, the contract is honest, and we don't claim one-tap coverage
we don't have.