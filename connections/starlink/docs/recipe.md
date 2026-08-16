# Starlink — tier-b recipe connection

**Tier:** B (recipe)
**Audience:** A RoamCore user who has a Starlink Gen-2 / Gen-3 / Mini
terminal and wants the sleep-timer + bring-back-up + signal-snapshot
story that powers the RoamCore `rc_net_starlink_*` contract tiles +
OpenClaw mobile-internet queries.

This is the developer / deeper-technician companion to the user-facing
doc at `docs/catalog/connectivity/starlink.md`. The user doc is the
5-step IKEA guide; this recipe covers the wiring details, the wizard
plumbing, the per-path schema, and the automations. **Read the user
doc first, then come here for the gory bits.**

The recipe mirrors the 3-path wizard that shipped in Wave 9 #108
(`connection.yml` → `wizard.setup_paths` + `connections/starlink/
__init__.py` → `apply_setup_path()` + `PATH_*` constants). The
wizard asks the user which topology they want and auto-wires the
chosen path.

## §0 — The 3 paths (wizard at a glance)

The wizard entry point is `apply_setup_path(hass, path_id,
user_input)` in `connections/starlink/__init__.py`. The valid
`path_id` values are the three constants exported from that module:

| Constant | Value | When to pick it |
|---|---|---|
| `PATH_STARLINK_MINI_ONLY` | `"starlink_mini_only"` | The Starlink Mini (or any single-box Starlink) IS your only router. No separate Wi-Fi router, no OpenWrt VM in the data path. Simplest setup. **This is the tier-a promotion candidate.** |
| `PATH_SEPARATE_ROUTER` | `"separate_router"` | You have a Gen-2/Gen-3 dish PLUS a separate third-party Wi-Fi router AND a smart plug behind the PSU (or behind the router). Legacy / most common path. |
| `PATH_VP2430_VM_ROUTER` | `"vp2430_vm_router"` | Your "router" is an OpenWrt VM inside the Proxmox box (VMID 100). RoamCore talks to the OpenWrt API for control. No smart plug needed. |

The full `describe_setup_paths()` radio-button metadata (label,
description, estimated_time, requires_inputs, requires_reboot) is in
`connections/starlink/__init__.py`. `connection.yml` carries the same
shape under `wizard.setup_paths` so the docs site can render the
choices without importing the Python module.

## What is Starlink in RoamCore?

Starlink (<https://www.starlink.com/>) is SpaceX's low-earth-orbit
satellite internet terminal. Gen-2 / Gen-3 hardware ships as a dish +
power supply + Wi-Fi router; Starlink Mini is a single flat box with
both dish and router. Idle draw is 20–40 W on Gen-2 and 30–60 W on
Gen-3 (with heating cycles), so leaving the dish on 24/7 drains a
van battery faster than most people expect. The community pattern is
to put a controllable smart plug behind the PSU and schedule it.

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
  on?" and "what's the signal %?" without you having to check the
  app.

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
audit-recommended config_flow can't be canonical for Paths B / C.
Path A is the closest we get to "one-tap" (just point RoamCore at
`http://192.168.100.1:80/` and you're done), but it's gated on a test
fixture landing. The promotion outline at the bottom of this recipe
describes exactly what needs to happen to flip Path A to tier-a.

## Prerequisites

Before starting the recipe, make sure you have:

- **A Starlink terminal.**
  - **Gen-2 / Gen-3:** dish + router + PSU. Path B (smart plug behind
    PSU or router) is the standard install.
  - **Starlink Mini:** single flat box, dish + router integrated.
    Path A (Mini as the only router) is the natural install.
  - **Gen-1:** the round "dishy" with the round router. Still works,
    but the signal tile will be grayed out — Gen-1 has no local HTTP
    API.
- **A controllable smart plug / relay / DC switch** (required for
  Path B; optional for Path A; not used by Path C). Anything HA can
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
- **Starlink's local HTTP API reachable from HA** (Path A and Path
  C's signal-stats wiring; Gen-2 / Gen-3 / Mini only): the router
  serves `http://192.168.100.1:80/api/console/dish-status.json` on
  the Starlink LAN. If your HA host is on a different VLAN, route
  the Starlink LAN to HA (or put HA on the Starlink LAN).
- **A spare 12 V / mains outlet** near where the Starlink PSU lives
  — the smart plug has to physically sit between the PSU and its
  power source.
- **For Path C:** an OpenWrt VM (VMID 100 on the VP2430) running
  RoamCore's networking recipe, plus the OpenWrt API URL + bearer
  token that RoamCore generated for it.
- **(Recommended) A UPS / battery monitor** — see "What wakes me up
  if Starlink goes down?" in §8.

## Path A — Starlink Mini only (tier-a promotion candidate)

The simplest path. The Starlink Mini's built-in Wi-Fi router IS your
LAN router; RoamCore just talks to the Mini's local API for signal
stats + reachability.

### §3.1 — Wire the Mini to your van's 12 V / mains

Plug the Starlink Mini into power, connect your laptop / phone to
its Wi-Fi network, confirm you have internet.

### §3.2 — Pick "Starlink Mini only" in the wizard

The RoamCore wizard renders a radio-button list (sourced from
`describe_setup_paths()`). Pick **"Starlink Mini as my only router"**
(`PATH_STARLINK_MINI_ONLY`). This path requires no user input — the
wizard writes:

- `input_text.rc_net_starlink_api_url = "http://192.168.100.1:80"`
- A REST sensor polling `dish-status.json` once per minute →
  `sensor.rc_net_starlink_signal_pct`
- Three template sensors:
  - `binary_sensor.rc_net_starlink_reachable`
    (green if the Mini answered within `STARLINK_REACH_TIMEOUT_S`,
    red otherwise).
  - `sensor.rc_net_starlink_signal_pct`
    (0–100 from `dish.snr_db`).
  - `sensor.rc_net_starlink_sleep_state`
    (always `awake` on Path A — there's no plug to flip; the
    Mini's built-in sleep is reachable via a separate API call
    that Path A doesn't yet invoke).

### §3.3 — Wizard verification

The wizard calls
`await _apply_path_starlink_mini_only(hass, user_input)` which does:

1. Writes the helper entities above (idempotent — re-running with
   the same input is a no-op).
2. Probes `http://192.168.100.1:80/api/console/dish-status.json`
   with **3 retries + exponential backoff**
   (`STARLINK_REACH_RETRIES = 3`,
   `STARLINK_REACH_BACKOFF_S = 1.0`, so 1s + 2s + 4s = 7s
   between attempts, 10s total budget).
3. On success: returns `{"reachable": True, "signal_pct": <0-100>,
   "generation": <2|3|"mini">}`.
4. On total failure: raises a plain-English
   `HomeAssistantError("We can't reach your Starlink router at
   http://192.168.100.1:80. Make sure the ethernet adapter is
   plugged in and your computer can reach the Starlink network.
   (Gen-2/Gen-3 only - Gen-1 has no local API.)")`. The wizard
   surfaces this as a toast and asks the user to check cabling.
5. Gen-1 detected: the wizard notes `generation = "gen1"` and
   gracefully degrades the signal tile to `unknown` (gray). All
   other tiles continue to work.

### §3.4 — Verify

1. Open the RoamCore dashboard → **Networking** section.
2. The `rc_net_starlink_*` tiles should be visible. `signal_pct`
   should fill in within 60 seconds.
3. If `reachable` is red but you have internet on the Mini's
   Wi-Fi, check §8 ("Troubleshooting").

### §3.5 — Auto-recover

If `binary_sensor.rc_net_starlink_reachable` flips to OFF (the Mini
stopped responding), Path A has no plug to fall back to. The
auto-recovery is: re-run the wizard step with the same answer
(`PATH_STARLINK_MINI_ONLY`). It's idempotent and will re-probe the
API. If the probe fails 3× in a row, the wizard surfaces the
plain-English unreachable error and asks the user to check
cabling / Wi-Fi association.

## Path B — Separate router (smart plug behind the PSU)

Identical install to the legacy recipe (this was the only path before
Wave 9 #108). Path B is for the common case: Gen-2 / Gen-3 dish +
separate Wi-Fi router + a smart plug behind the PSU (or behind the
router only).

### §4.1 — Wire the smart plug behind the router only

1. Unplug the router-side cable from the Starlink PSU (the cable
   that goes from the PSU's "router" port to the router's WAN
   port).
2. Plug a short extension / splitter into the PSU's router port if
   needed; route the existing router cable AND a new cable to the
   smart plug's input. Plug the smart plug's output into the
   router's WAN port.
3. Or — simpler — put the smart plug between the PSU's mains input
   and the wall (full PSU power cycle). The recipe works either
   way; the router-only variant just keeps the dish powered and
   gives faster wake times (~5 s vs ~90 s).

### §4.2 — Pair the smart plug with HA

Pick whichever integration matches your plug:

- **TP-Link Kasa** → HA → **Settings → Devices & Services → Add
  Integration → TP-Link Kasa Smart Home**. Sign in (or use the
  local-only path), pick the plug. The plug shows up as
  `switch.<name>_plug` (e.g. `switch.starlink_plug`).
- **Shelly** → HA → **Settings → Devices & Services → Add
  Integration → Shelly**. Add the device by IP or via the cloud;
  you get `switch.shelly_plug_relay` or similar.
- **Sonoff** (custom component / ESPHome) → follow the component's
  pairing flow. You get `switch.sonoff_<id>_relay` or
  `switch.<esphome_name>_relay`.
- **Zigbee** → HA → **Settings → Devices & Services → Zigbee Home
  Automation → Add Device**. Put the plug in pairing mode. You get
  `switch.<ieee>_plug` or whatever the integration renames it to.

Note the entity_id your plug ended up as — you need it in §4.3.

### §4.3 — Pick "I have a separate router" in the wizard

The wizard asks for **the entity_id of your smart plug**
(e.g. `switch.starlink_plug`). It calls
`await _apply_path_separate_router(hass, {"plug_entity_id": "switch.starlink_plug"})`,
which validates the plug entity is **exposed** AND **controllable**
(not hidden in **Settings → Devices & Services → Entities** AND not
a sensor — must be a `switch.*` that responds to turn_on / turn_off).

Validation errors (raised as plain-English `HomeAssistantError`):

- `ERROR_PLUG_NOT_EXPOSED = "We can't find the plug entity
  '{entity_id}' in Home Assistant. Make sure the smart plug
  integration is set up and the entity is exposed (not hidden in
  Settings -> Devices & Services -> Entities)."`
- `ERROR_PLUG_NOT_CONTROLLABLE = "The plug entity '{entity_id}'
  exists but isn't controllable (it might be a sensor, not a
  switch). Pick a switch.* entity that can be turned on and off."`

After validation, the wizard writes:

- `switch.rc_net_starlink_plug` (a `template` switch mapped to
  your plug entity — this indirection lets the recipe's
  automations refer to a vendor-neutral id).
- The full `rc_net_starlink_*` contract set (see §5).

### §4.4 — Optional signal-stats wiring (Gen-2/Gen-3 only)

The wizard will offer to wire the Starlink local API for the
`signal_pct` tile. Accept, and you get a REST sensor polling
`http://192.168.100.1:80/api/console/dish-status.json` once per
minute. See §6.2 for the YAML.

### §4.5 — Verify

1. Open the RoamCore dashboard → **Networking** section.
2. The `rc_net_starlink_*` tiles should be visible.
3. Tap the wake button. The plug should click ON within ~2
   seconds, the wake timer should start, and the sleep-state tile
   should show `awake` after the dish acquires a signal (~90 s for
   Gen-3, ~30 s for Gen-2).
4. Wait 30 minutes (or set the timer to 1 minute for the test).
   The plug should click OFF and the sleep-state tile should show
   `asleep`.

### §4.6 — Auto-recover (smart plug drops offline)

If the wizard's `switch.rc_net_starlink_plug` helper loses track of
the underlying plug entity (HA re-pair, integration restart), the
fallback is a manual REST API call:

1. Open **Developer Tools → Services** in HA.
2. Call `switch.toggle` on `switch.rc_net_starlink_plug`. If that
   works, the underlying plug is fine; the wizard's helper just
   needs re-running.
3. Re-run the wizard step with the same plug entity id. It's
   idempotent and will re-confirm the plug is exposed +
   controllable.

If `switch.toggle` does nothing, the underlying plug has lost Wi-Fi
or power. See §8 ("Troubleshooting") item 1.

## Path C — VM router inside the VP2430

For users running OpenWrt-in-Proxmox as their LAN router
(`connections/openwrt-controls` recipe + VMID 100 on the VP2430).
The "router" never powers down — the VM stays up; RoamCore toggles
an OpenWrt firewall rule to drop / un-drop Starlink traffic. Wake
is sub-second.

### §5.1 — Pick "VM router inside the VP2430" in the wizard

The wizard asks for **your OpenWrt API URL** (e.g.
`http://192.168.1.1/cgi-bin/api/`) AND **the bearer token**
RoamCore generated for the OpenWrt integration. The wizard calls
`await _apply_path_vp2430_vm_router(hass, {"openwrt_api_url":
"http://...", "openwrt_bearer_token": "..."})`, which validates
the API is reachable (3× retry with backoff).

Validation errors (raised as plain-English `HomeAssistantError`):

- `ERROR_OPENWRT_UNREACHABLE = "We can't reach the OpenWrt API at
  {url}. Check that the VM is running on the VP2430 (VMID 100)
  and the bearer token is correct."`

After validation, the wizard writes:

- `input_text.rc_net_starlink_openwrt_api_url` and
  `input_text.rc_net_starlink_openwrt_bearer_token` (the creds
  used by Path C's REST chain).
- A REST sensor chain through the OpenWrt API for WAN reachable /
  WAN IP.
- The Starlink local API for `signal_pct` (Path C also pulls
  signal stats from `dish-status.json` — the dish is still
  Gen-2/Gen-3 or Mini, just with a VM in front of it).

### §5.2 — Verify

1. Open the RoamCore dashboard → **Networking** section.
2. `reachable` should be green (the VM's API responded).
3. Tap **Wake for 30 min**. The OpenWrt firewall rule should
   remove within 1 second; internet should come back instantly
   (dish never went anywhere).

## §4 RoamCore contract entities

The full listing the wizard + dashboard + OpenClaw rely on. Path A
creates all of these except the smart-plug helper; Path B creates
all of them; Path C creates all of them except the smart-plug
helper (the OpenWrt API replaces it).

| Entity | Type | States | Source |
|---|---|---|---|
| `sensor.rc_net_starlink_sleep_state` | sensor | `awake \| asleep \| waking` | template over plug state + wake timer (Path B); always `awake` on Path A; OpenWrt firewall state on Path C |
| `switch.rc_net_starlink_allow_sleep` | switch | ON / OFF | `input_boolean` flag |
| `button.rc_net_starlink_wake_30_min` | button | (press) | HA timer + automation |
| `binary_sensor.rc_net_starlink_reachable` | binary_sensor | ON / OFF | HA last-seen check on plug (Path B) or API probe (Paths A/C) |
| `sensor.rc_net_starlink_signal_pct` | sensor | 0–100 | REST sensor to `dish-status.json` (Gen-2/Gen-3/Mini only; grayed out on Gen-1) |
| `input_datetime.rc_net_starlink_quiet_start` | input_datetime | time | user-set |
| `input_datetime.rc_net_starlink_quiet_end` | input_datetime | time | user-set |

All grayed-out / `unknown` fallback when the smart-plug is undefined
(no plug paired, or HA's plug integration is in error state).

### §6.1 — Copy-pasteable helper YAML

Drop into `homeassistant/packages/roamcore_starlink.yaml`:

```yaml
# RoamCore Starlink contract helpers (recipe §6.1).
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

### §6.2 — Signal-stats wiring (Gen-2/Gen-3 / Mini only)

Drop alongside §6.1 in the same package:

```yaml
rest:
  - resource_template: http://192.168.100.1:80/api/console/dish-status.json
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
`homeassistant/automations/roamcore_starlink_*.yaml`. Path B uses
all three; Path A uses none (no plug to flip); Path C uses the
break-sleep automation (§7.3) with the OpenWrt API in place of
the plug.

### §7.1 — Sleep during quiet hours

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

### §7.2 — Wake for 30 minutes on demand (button)

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

### §7.3 — Mode-aware break-sleep (lost WAN)

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

The 7 common failure modes (5 required by the spec, 2 bonus). See
also the user-facing doc at
`docs/catalog/connectivity/starlink.md` for the plain-English
version of the same list.

### 1. The smart plug is offline / unreachable (Path B)

- **What you see:** `binary_sensor.rc_net_starlink_reachable` is
  OFF; the **Wake for 30 min** button does nothing.
- **Why:** the plug lost Wi-Fi (inverter cycling, weak signal, ISP
  hiccup), or the integration in HA lost its pairing.
- **Fix:**
  1. Check the smart plug's LED. Off = no power to the plug.
     Blinking = lost Wi-Fi. Solid = OK.
  2. If it's blinking, power-cycle the plug (unplug 10 s, plug
     back in).
  3. If it's solid but HA can't see it, go to **Settings →
     Devices & Services**, find the plug's integration, click
     **⋯ → Reconfigure**.
  4. Last-resort fallback: manual REST call from **Developer
     Tools → Services** — `switch.toggle` on
     `switch.rc_net_starlink_plug`. If that works, the issue is
     the wizard's helper, not the plug.

### 2. Gen-1 router — signal tile is gray (all paths)

- **What you see:** every other tile works, but `signal_pct` is
  gray with `unavailable` underneath.
- **Why:** Gen-1 routers have no local HTTP API. RoamCore has no
  `dish-status.json` to query on a Gen-1. Hardware limitation,
  not a RoamCore bug.
- **Fix:** upgrade to Gen-2, Gen-3, or Starlink Mini (all expose
  `http://192.168.100.1:80/`). Everything else in RoamCore still
  works on Gen-1 — you just don't get the signal number.

### 3. The wizard step fails partway (all paths)

- **What you see:** the wizard accepts your inputs, then says
  "Couldn't save your setup" or similar.
- **Why:** usually Path B (no plug entity found) or Path C
  (OpenWrt API didn't answer). The wizard retries 3× with
  exponential backoff (`STARLINK_REACH_RETRIES = 3`,
  `STARLINK_REACH_BACKOFF_S = 1.0`, so 1s + 2s + 4s between
  attempts, ~10s total budget) before giving up.
- **Fix:**
  1. Re-read the error message — it tells you which piece is
     missing (e.g. "We can't reach your Starlink router at
     http://192.168.100.1:80. Make sure the ethernet adapter is
     plugged in and your computer can reach the Starlink
     network.").
  2. Fix the missing piece (plug the dish in, point HA at the
     right VLAN, paste the right bearer token).
  3. Re-run the wizard. It's idempotent — re-running with the
     same answers is safe and won't break anything you already
     wired.

### 4. Signal tile is gray on a Gen-2/Gen-3 / Mini (Path A, Path C)

- **What you see:** Gen-2 / Gen-3 / Mini hardware (you checked),
  but the signal_pct tile is still gray.
- **Why:** the HA host can't reach `http://192.168.100.1:80/` —
  usually a VLAN / firewall issue. Starlink's router serves the
  local API on its own subnet; if HA is on a different VLAN, the
  API isn't routable.
- **Fix:**
  1. From the HA host, run
     `curl http://192.168.100.1:80/api/console/dish-status.json`.
     Timeout = routing problem.
  2. Either move HA onto the Starlink LAN, or add a static route
     on your router to the Starlink subnet (`192.168.100.0/24`).
  3. Re-run the wizard. The signal tile should fill in within 60
     seconds.

### 5. Sleep state is stuck on "waking" or "asleep" (Path B)

- **What you see:** you pressed **Wake for 30 min**, the plug
  clicked on, but `rc_net_starlink_sleep_state` still says
  `waking` after 5 minutes. Or it says `asleep` even though the
  dish is clearly online (your laptop has internet).
- **Why:** the tile reads the plug's HA state + a 30-min wake
  timer. If the timer is misconfigured (paused, or its duration
  was edited) or the plug's state didn't propagate, the tile
  sticks.
- **Fix:**
  1. Open **Developer Tools → States** in HA. Look up
     `timer.rc_net_starlink_wake_30_min` and
     `switch.rc_net_starlink_plug`.
  2. If the timer says `paused`, click **Start**.
  3. If the plug says `off` but the dish is online, the wizard's
     helper is stale — re-run the wizard (it's idempotent).
  4. Last-resort: **Settings → Devices & Services → RoamCore →
     Reload**. That re-reads every helper from YAML.

### 6. (bonus) The dish takes a long time to wake (Path B)

- **What you see:** Wake for 30 min works, but internet doesn't
  come back for 60–90 seconds.
- **Why:** a full PSU power cycle reboots the dish AND the
  router. Dish boot + satellite acquisition + DHCP is ~60 s on
  Gen-2 and ~90 s on Gen-3.
- **Fix:** move the smart plug to be **router-only** (§4.1 step
  2). Dish stays pointed at the satellite; only the router
  reboots; wake is ~5 s.

### 7. (bonus) What wakes me up if Starlink goes down? (all paths)

If your **other** internet sources (LTE, campground Wi-Fi) are
all offline for 5 minutes, RoamCore automatically wakes Starlink
for 30 minutes so remote access keeps working — that's the
`rc_net_starlink_break_sleep_if_no_other_internet` automation
(§7.3). You don't need to configure anything. If you'd rather
not auto-wake on full disconnect, flip the
`switch.rc_net_starlink_allow_sleep` toggle OFF before leaving
the van.

## §7 Privacy

- **Local only.** No Starlink cloud API calls. No telemetry to
  RoamCore. No SSID, MAC, IP, or dish serial in any contract
  entity.
- **Signal stats** come from Starlink's local HTTP API
  (`http://192.168.100.1:80/...`), which serves the LAN only —
  no internet round-trip.
- **The smart-plug integration** uses whatever protocol your plug
  speaks (Kasa cloud, Shelly cloud, local Zigbee, local Modbus).
  RoamCore does not add any cloud dependency on top — if your
  plug uses a cloud, that's the plug's existing behavior, not
  RoamCore's.
- **No MAC / SSID / serial** is captured in any
  `rc_net_starlink_*` entity, OpenClaw summary key, or dashboard
  tile. The contract is intentionally vendor-neutral.

## §10 — Promotion to tier-a (outline)

When a real Starlink terminal lands on the bench (likely via
`testcontainers/grpc-starlink-dish` with a synthetic
`dish-status.json` fixture, or a recorded capture), **Path A
(`PATH_STARLINK_MINI_ONLY`)** is the candidate to promote to
tier-a:

1. Add a native `config_flow.py` (or a thin wrapper around the
   upstream Starlink community integration if one lands in core)
   that walks the operator through picking the Starlink Mini's
   Wi-Fi network + entering the local API credentials (or auto-
   detecting them via mDNS).
2. Add an integration test that asserts the `rc_net_starlink_*`
   contract entities appear after a synthetic `dish-status.json`
   payload, with the 3x-retry reachability probe passing.
3. Flip `tier_requirements` to include `working_config_flow` +
   `integration_test_passes` + `no_manual_yaml_required`.
4. Drop the `tier_warnings` entries that mention no-real-terminal
   / recipe-depends-on-user-smart-plug (for Path A specifically).
5. Flip Path A's `status` from `beta` to `shipped`.
6. Flip `wizard.one_tap` to `true` (or per-path: keep
   `one_tap: false` for the connection as a whole, but mark Path
   A as the tier-a subset).
7. Keep Path B (`PATH_SEPARATE_ROUTER`) and Path C
   (`PATH_VP2430_VM_ROUTER`) at tier-b — both depend on operator
   hardware (smart plug or OpenWrt VM) that we don't ship.

Until that fixture lands, this stays at tier-b (beta, recipe) —
the recipe is sound, the contract is honest, and we don't claim
one-tap coverage we don't have.
