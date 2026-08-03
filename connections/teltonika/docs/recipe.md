# Teltonika — tier-b recipe connection

**Tier:** B (recipe)
**Audience:** A RoamCore user who has a Teltonika RUT-series LTE/5G
router on the van's LAN (RUT950 / RUT951 / RUTX11 / RUTX12 / RUTM50 /
etc.), wants the telemetry + reboot + monthly-data-reset story that
powers the RoamCore `rc_net_teltonika_*` contract tiles + OpenClaw
mobile-internet queries.

This howto is mirrored into `docs/connections/teltonika.md` by the
catalog cron (`scripts/build_catalog.py`) so it shows up under the
public docs site's "Connections" section. Keep this recipe as the
source of truth.

## What is Teltonika in RoamCore?

Teltonika Networks (<https://teltonika-networks.com/>) makes
rugged LTE/5G routers that are very popular in van life and remote
installations. The RUT-series hardware runs Teltonika's RutOS
firmware on top of OpenWrt, with a stable MIB-II + Teltonika-private
SNMP OID surface for monitoring, plus a documented REST / RMS / Web
UI API on newer firmware for direct programmatic control.

In RoamCore, Teltonika is the LTE/5G mobile-internet slice for vans
that already run a Teltonika router as their primary WAN:

- **Telemetry** (reachable, WAN state, signal strength, SIM state,
  LTE/5G mode, carrier, monthly data, uptime, public IP) sourced
  from SNMP (Path A) or the Teltonika REST / RMS API (Path B).
- **Reboot affordance** (one-tap "reboot teltonika") wired to either
  a controllable smart plug behind the router OR the Teltonika
  REST/RMS `reboot` API endpoint.
- **Mode-aware behavior** treats Teltonika as a fallback WAN for
  Travel mode (you may want Starlink or campground Wi-Fi first when
  moving), fails over to Starlink or shares with Peplink where
  relevant, and suppresses reboot during Stealth silent hours.
- **OpenClaw mobile-internet queries** ("is teltonika online?",
  "what's teltonika signal %?", "how much teltonika data this
  month?", "what carrier is teltonika on?", "reboot teltonika") bind
  to the contract entities. The corresponding OpenClaw query keys
  (used by the agent wiring) are: `is_teltonika_online`,
  `teltonika_signal_pct`, `teltonika_data_used_gb`,
  `teltonika_carrier`, `reboot_teltonika` — the recipe exposes a
  `button.rc_net_teltonika_reboot_now` for the `reboot_teltonika`
  agent-action allowlist so the OpenClaw wiring has a known-good
  button to call.

RoamCore does **not** ship a Teltonika router or a RoamCore-owned
native integration. There is no canonical RoamCore-owned upstream HA
integration for "talk to a Teltonika router as a mobile-internet
slice" — the operator's SNMP-vs-REST choice is firmware-driven, and
the underlying HA core `snmp` integration (or `rest` / `command_line`
for the REST/RMS path) is the upstream truth. So we publish a recipe
that walks you through the wiring, then layer a small contract on
top: the `rc_net_teltonika_*` dashboard tiles + the OpenClaw queries
that bind to those contract entities.

**Why tier-b:** RoamCore has no real Teltonika router on the bench to
integration-test against, no native HA integration to point at, and
the operator's SNMP-vs-REST choice is firmware-driven — so the
audit-recommended config_flow can't be canonical here. The recipe is
sound (it leans on HA's core `snmp` integration OR Teltonika's
documented REST/RMS API + the well-understood MIB-II + Teltonika-
private OIDs), but we cannot claim one-tap automation. The promotion
outline at the bottom of this recipe describes exactly what needs to
happen to flip this to tier-a.

**Two install paths (operator picks based on firmware):**

- **Path A — HA core SNMP integration** (recommended, supported on
  every Teltonika RUT firmware). The operator enables SNMP v2c (or
  v3) on the router (System → SNMP → Enable), gives HA the router
  IP + community string, and the recipe walks them through mapping
  the MIB-II + Teltonika-private OIDs into the `rc_net_teltonika_*`
  contract tiles via the recipe §4 helper YAML.
- **Path B — Teltonika REST / RMS / Web UI API** (alternative for
  newer firmware that exposes `http://<router>/cgi-bin/api/...` or
  the Teltonika RMS cloud API). The operator pulls JSON via HA's
  `rest` integration or `command_line` shell_command and the same §4
  helpers map fields into the contract tiles. The recipe ships a
  copy-pasteable REST-sensor block for the most common endpoints.

Both paths share the same §4 contract helpers and §5 automations.
The wizard asks the operator which path they wired; the contract
tiles are identical either way.

## Prerequisites

Before starting the recipe, make sure you have:

- **Teltonika RUT-series router on the van's LAN.** RUT950,
  RUT951, RUTX11, RUTX12, RUTM50, etc. all expose the same core
  MIB-II + Teltonika-private SNMP OID surface; firmware-specific
  OIDs may shift (see `tier_warnings: firmware_specific_oids_may_shift`
  in the manifest).
- **SNMP credentials OR REST/RMS API access** (your choice, depends
  on firmware — both are documented):
  - **For Path A (SNMP):** enable SNMP on the router (System →
    SNMP → Enable), set a community string (v2c) or v3 credentials.
    Note the community string + the router's LAN IP.
  - **For Path B (REST):** enable the REST API on the router
    (System → Web UI → API Access → Enable), or set up a Teltonika
    RMS account at <https://rms.teltonika-networks.com/> and note
    the RMS API credentials.
- **Network reachability** between HA and the Teltonika router (the
  same LAN, or a routed VLAN — most installs are LAN-local).
- **(Optional) A controllable smart plug** behind the router if you
  want the cheapest-possible reboot affordance without touching the
  Teltonika REST/RMS API (same pattern as Starlink's
  `switch.rc_net_starlink_plug`).

## Path A — HA core SNMP integration (recommended)

The default install for RoamCore users on any Teltonika RUT firmware.

### A.1 — Enable SNMP on the Teltonika router

1. Log into the router's Web UI (default `http://192.168.1.1/`, or
   whatever IP the router ended up at on your LAN).
2. Navigate to **System → SNMP**.
3. Enable SNMP. Pick SNMPv2c (default; easiest) or SNMPv3 (if you
   want auth + privacy).
4. For v2c: set the community string (default is `public` — change
   it to something not-public).
5. For v3: set the username, auth protocol (SHA), auth password,
   privacy protocol (AES), privacy password.
6. Note the community string / v3 credentials — you need them in A.2.

### A.2 — Add the SNMP integration in HA

In HA → **Settings → Devices & Services → Add Integration →
SNMP**, with:

- Host: `192.168.1.<router_lan_ip>` (the Teltonika's LAN IP).
- Port: `161` (default).
- Community string: `<your community string from A.1>`.
- Version: `2c` (or `3` + v3 credentials if you went v3).
- Timeout / retries: defaults are fine.

HA will create a handful of base SNMP sensors (system description,
uptime, contact, name, location) — these become the foundation for
the recipe §4 helpers.

### A.3 — Add Teltonika-private OID sensors

The Teltonika-private OIDs (signal strength, LTE/5G mode, carrier,
SIM state, data counters, etc.) need additional `snmp` sensors in
HA's `snmp` integration. The simplest path is a package YAML in
`homeassistant/packages/roamcore_teltonika_snmp.yaml` that the
operator loads via `homeassistant.packages:` in `configuration.yaml`:

```yaml
# RoamCore Teltonika SNMP package (recipe §A.3 / §4.1).
# Adjust OIDs to match your exact Teltonika model + firmware;
# consult https://wiki.teltonika-networks.com/view/SNMP for the
# canonical OID list per model.

snmp:
  - name: teltonika_router
    host: 192.168.1.<router_lan_ip>
    port: 161
    community: <your_community_string>
    version: 2c
    timeout: 10
    retries: 2
    baseoid: 1.3.6.1.4.1.48690     # Teltonika private enterprise OID root
    scan_interval: 30
    sensors:
      - name: "Teltonika signal strength (RSSI)"
        unique_id: teltonika_signal_rssi_dbm
        oid: 1.3.6.1.4.1.48690.10.10.10.0   # placeholder; replace with your model's OID
        unit_of_measurement: "dBm"
        device_class: signal_strength
        value_template: "{{ value | float(0) }}"
      - name: "Teltonika LTE mode"
        unique_id: teltonika_lte_mode_raw
        oid: 1.3.6.1.4.1.48690.10.10.20.0   # placeholder
        value_template: "{{ value }}"
      - name: "Teltonika carrier"
        unique_id: teltonika_carrier_raw
        oid: 1.3.6.1.4.1.48690.10.10.30.0   # placeholder
        value_template: "{{ value }}"
      - name: "Teltonika SIM state"
        unique_id: teltonika_sim_state_raw
        oid: 1.3.6.1.4.1.48690.10.10.40.0   # placeholder
        value_template: "{{ value }}"
      - name: "Teltonika WAN state"
        unique_id: teltonika_wan_state_raw
        oid: 1.3.6.1.4.1.4.1.48690.10.10.50.0  # placeholder
        value_template: "{{ value }}"
      - name: "Teltonika data used this month (bytes)"
        unique_id: teltonika_data_used_bytes
        oid: 1.3.6.1.4.1.48690.10.10.60.0   # placeholder
        unit_of_measurement: "B"
        value_template: "{{ value | int(0) }}"
      - name: "Teltonika public IP"
        unique_id: teltonika_public_ip_raw
        oid: 1.3.6.1.4.1.48690.10.10.70.0   # placeholder
        value_template: "{{ value }}"
```

**Important:** the OIDs above are placeholders. The actual OIDs per
Teltonika model + firmware are documented on
<https://wiki.teltonika-networks.com/view/SNMP> and
<https://wiki.teltonika-networks.com/view/Monitoring_via_SNMP>. The
recipe's job is to publish the *pattern*; the operator fills in
their exact OIDs. The `tier_warnings:
firmware_specific_oids_may_shift` flag in the manifest is the audit-
honest acknowledgement of this operator-side step.

### A.4 — Create the `rc_net_teltonika_*` contract tiles

In HA → **Helpers**, create the following (the recipe ships copy-
pastable YAML for these in §4.1 below):

- `binary_sensor.rc_net_teltonika_reachable` — template binary
  sensor reporting ON if the SNMP integration reports the router as
  up (HA's standard "entity is alive" check, scoped to the SNMP
  device tracker).
- `sensor.rc_net_teltonika_wan_state` — template sensor mapping
  the raw Teltonika WAN state to `connected | disconnected | connecting`.
- `sensor.rc_net_teltonika_signal_pct` — template sensor that takes
  the RSSI dBm and maps it to a 0–100 quality percentage.
- `sensor.rc_net_teltonika_lte_mode` — template sensor mapping the
  raw LTE mode integer to `LTE | 5G | 3G | 2G | unknown`.
- `sensor.rc_net_teltonika_carrier` — template sensor exposing the
  carrier name from the raw Teltonika OID.
- `sensor.rc_net_teltonika_data_used_gb` — template sensor that
  takes the monthly byte counter and converts it to GB.
- `sensor.rc_net_teltonika_uptime_hours` — template sensor
  exposing the SNMP uptime in hours.
- `sensor.rc_net_teltonika_public_ip` — template sensor exposing
  the router's WAN public IP.
- `switch.rc_net_teltonika_data_reset` — `input_boolean`-backed
  switch that resets the monthly-data counter (toggles an
  `input_boolean` the §5.4 automation listens to).
- `button.rc_net_teltonika_reboot_now` — one-tap reboot trigger.
- `button.rc_net_teltonika_refresh_signals` — force-poll the router
  (useful when the signal feels stale).

### A.5 — Wire the reboot affordance (Path A's plug option)

Same pattern as the Starlink slice:

1. Put a controllable smart plug / relay / DC switch behind the
   Teltonika router (between the wall / 12 V source and the router's
   power input).
2. Wire the plug into HA via your preferred integration (TP-Link /
   Shelly / Sonoff / Zigbee / Modbus / ...).
3. Create a template helper `switch.rc_net_teltonika_plug` pointing
   at the plug's HA switch entity.
4. The recipe §5.2 reboot automation toggles this plug.

Alternatively, if your Teltonika firmware exposes the REST reboot
endpoint, skip the plug and use Path B's REST reboot — see §B.5.

### A.6 — Enable the recipe §5 automations

The recipe ships four automations in §5.1 / §5.2 / §5.3 / §5.4:

- Mode-aware fallback-to-Starlink (when in Travel mode AND
  `binary_sensor.rc_net_teltonika_reachable` is OFF AND
  `binary_sensor.rc_net_starlink_reachable` is ON, log a notice).
- Reboot-on-no-internet (when `binary_sensor.rc_net_internet_reachable`
  is OFF for >5 min AND `binary_sensor.rc_net_teltonika_reachable`
  is ON, reboot Teltonika).
- Suppress-reboot-in-Stealth (when in Stealth mode, suppress the
  reboot automation).
- Monthly-data-counter reset (when `switch.rc_net_teltonika_data_reset`
  flips ON, reset the §A.4 helper that backs `sensor.rc_net_teltonika_data_used_gb`).

### A.7 — Verify

1. Open the RoamCore dashboard → **Networking** section.
2. The `rc_net_teltonika_*` tiles should be visible. If any are
   grayed out, check §6 (Troubleshooting).
3. Tap the refresh-signals button. The SNMP values should refresh
   within 30 s (the §A.3 scan_interval).
4. Tap the reboot button. The smart plug (or REST endpoint) should
   trigger within ~2 s, the router should reboot (~60 s typical),
   and the reachable tile should go OFF then ON again.

## Path B — Teltonika REST / RMS / Web UI API (alternative)

Identical contract + helpers as Path A; the only difference is how
the operator pulls telemetry from the router.

### B.1 — Enable the REST API on the Teltonika router

1. Log into the router's Web UI.
2. Navigate to **System → Web UI → API Access**.
3. Enable API Access. Set an API token (long, random).
4. Note the API token + the router's LAN IP.

For RMS (cloud polling), set up an account at
<https://rms.teltonika-networks.com/> and note the RMS API
credentials.

### B.2 — Add the `rest` integration in HA

In HA → **Settings → Devices & Services → Add Integration → REST**,
with:

- Resource / endpoint: `http://<router_lan_ip>/cgi-bin/api/...`
  (consult your model's Web UI API docs for the exact endpoint).
- Headers: `Authorization: Bearer <your_api_token>`.

Or, for RMS, the cloud API endpoint + RMS API key.

### B.3 — Map REST responses to the same contract helpers

Same as Path A — drop the recipe §4.1 helper YAML into the same
package, and replace the SNMP-sourced `value_template:` references
with the REST JSON path that corresponds to the same field. The
contract tiles stay identical; only the upstream sourcing changes.

### B.4 — Wire the reboot affordance (Path B's REST option)

The Teltonika REST API exposes a `/reboot` endpoint on most RUT-series
firmware. Wire it via HA's `rest_command`:

```yaml
rest_command:
  teltonika_reboot:
    url: "http://<router_lan_ip>/cgi-bin/api/reboot"
    method: POST
    headers:
      Authorization: "Bearer <your_api_token>"
      Content-Type: "application/json"
    payload: '{"reboot": true}'
```

The recipe §5.2 reboot automation calls `rest_command.teltonika_reboot`
instead of toggling `switch.rc_net_teltonika_plug` if you went REST
instead of the plug.

### B.5 — Verify

Same as Path A §A.7 — the contract tiles + the reboot button behave
identically.

## §4 RoamCore contract entities

The full listing the wizard + dashboard + OpenClaw rely on:

| Entity | Type | States | Source |
|---|---|---|---|
| `binary_sensor.rc_net_teltonika_reachable` | binary_sensor | ON / OFF | HA last-seen check on SNMP device tracker (Path A) or REST device tracker (Path B) |
| `sensor.rc_net_teltonika_wan_state` | sensor | `connected \| disconnected \| connecting` | template over SNMP/REST WAN state raw value |
| `sensor.rc_net_teltonika_signal_pct` | sensor | 0–100 | template over RSSI dBm → quality pct |
| `sensor.rc_net_teltonika_lte_mode` | sensor | `LTE \| 5G \| 3G \| 2G \| unknown` | template over LTE mode integer |
| `sensor.rc_net_teltonika_carrier` | sensor | string | template over carrier raw value |
| `sensor.rc_net_teltonika_data_used_gb` | sensor | float GB | template over monthly bytes counter |
| `sensor.rc_net_teltonika_uptime_hours` | sensor | float hours | template over SNMP uptime |
| `sensor.rc_net_teltonika_public_ip` | sensor | string (IP) | template over public IP raw value |
| `switch.rc_net_teltonika_data_reset` | switch | ON / OFF | `input_boolean` flag for monthly-data reset |
| `button.rc_net_teltonika_reboot_now` | button | (press) | calls `switch.turn_off switch.rc_net_teltonika_plug` (Path A plug) OR `rest_command.teltonika_reboot` (Path B REST) |
| `button.rc_net_teltonika_refresh_signals` | button | (press) | calls `homeassistant.update_entity` on all the SNMP/REST sensors |

All grayed-out / `unknown` fallback when the SNMP/REST integration
is in error state (router offline, community string wrong, v3
credentials wrong, REST token wrong, RMS rate-limited).

### §4.1 — Copy-pasteable helper YAML

Drop into `homeassistant/packages/roamcore_teltonika.yaml`:

```yaml
# RoamCore Teltonika contract helpers (recipe §4.1).
# All entities are vendor-neutral per docs/reference/rc-entity-naming.md.

input_boolean:
  rc_net_teltonika_data_reset:
    name: Teltonika monthly-data reset flag (contract)
    icon: mdi:sim

template:
  - binary_sensor:
      - name: Teltonika reachable (contract)
        unique_id: rc_net_teltonika_reachable
        state: >
          {{ states('sensor.teltonika_router_uptime') not in ['unknown', 'unavailable'] }}
        device_class: connectivity
        icon: mdi:signal-cellular-4g
  - sensor:
      - name: Teltonika WAN state (contract)
        unique_id: rc_net_teltonika_wan_state
        state: >
          {% set raw = states('sensor.teltonika_wan_state_raw') | default('unknown') %}
          {% if raw in ['1', 'connected', 'up'] %}
            connected
          {% elif raw in ['0', 'disconnected', 'down'] %}
            disconnected
          {% elif raw in ['2', 'connecting'] %}
            connecting
          {% else %}
            unknown
          {% endif %}
        icon: mdi:wan
      - name: Teltonika signal pct (contract)
        unique_id: rc_net_teltonika_signal_pct
        unit_of_measurement: "%"
        device_class: signal_strength
        state: >
          {% set rssi = states('sensor.teltonika_signal_rssi_dbm') | float(-113) %}
          {% set pct = ((max(-113, min(-51, rssi)) + 113) * 100 / 62) | round(0) %}
          {{ pct }}
        icon: mdi:signal-cellular-4g
      - name: Teltonika LTE mode (contract)
        unique_id: rc_net_teltonika_lte_mode
        state: >
          {% set raw = states('sensor.teltonika_lte_mode_raw') | default('0') | int(0) %}
          {% if raw == 13 %}5G
          {% elif raw == 7 %}LTE
          {% elif raw == 5 %}3G
          {% elif raw == 2 %}2G
          {% else %}unknown
          {% endif %}
        icon: mdi:signal-cellular-4g
      - name: Teltonika carrier (contract)
        unique_id: rc_net_teltonika_carrier
        state: "{{ states('sensor.teltonika_carrier_raw') | default('unknown') }}"
        icon: mdi:sim
      - name: Teltonika data used (contract, GB)
        unique_id: rc_net_teltonika_data_used_gb
        unit_of_measurement: "GB"
        state: >
          {{ (states('sensor.teltonika_data_used_bytes') | float(0) / 1073741824) | round(2) }}
        icon: mdi:sim
      - name: Teltonika uptime (contract, hours)
        unique_id: rc_net_teltonika_uptime_hours
        unit_of_measurement: "h"
        state: >
          {{ (states('sensor.teltonika_router_uptime') | float(0) / 3600) | round(2) }}
        icon: mdi:clock-outline
      - name: Teltonika public IP (contract)
        unique_id: rc_net_teltonika_public_ip
        state: "{{ states('sensor.teltonika_public_ip_raw') | default('unknown') }}"
        icon: mdi:ip

switch:
  - name: Teltonika monthly-data reset (contract)
    unique_id: rc_net_teltonika_data_reset
    icon: mdi:sim
    # Backed by an input_boolean under the hood — same input_boolean
    # that appears at the top of this package as
    # `input_boolean.rc_net_teltonika_data_reset`. The toggle writes
    # back to the input_boolean so the §5.4 automation can react.

button:
  - name: Reboot Teltonika (contract)
    unique_id: rc_net_teltonika_reboot_now
    icon: mdi:restart
    # The §5.2 automation listens for this press and either toggles
    # `switch.rc_net_teltonika_plug` (Path A's plug option) or calls
    # `rest_command.teltonika_reboot` (Path B's REST option).
    # OpenClaw agent-action allowlist: this button is the target of
    # the `reboot_teltonika` query key.
  - name: Refresh Teltonika signals (contract)
    unique_id: rc_net_teltonika_refresh_signals
    icon: mdi:refresh
    press:
      - homeassistant.update_entity:
          entity_id:
            - sensor.teltonika_signal_rssi_dbm
            - sensor.teltonika_lte_mode_raw
            - sensor.teltonika_carrier_raw
            - sensor.teltonika_wan_state_raw
            - sensor.teltonika_data_used_bytes
            - sensor.teltonika_public_ip_raw
            - sensor.teltonika_router_uptime
```

(For Path A's plug option, also include the helper template switch
from the Starlink slice pattern:
`switch.rc_net_teltonika_plug` pointing at the operator's plug HA
entity. For Path B's REST option, the `rest_command.teltonika_reboot`
block from §B.4 above.)

## §5 Automations

Four sample automations, copy-pasteable into
`homeassistant/automations/roamcore_teltonika_*.yaml`:

### §5.1 — Mode-aware fallback-to-Starlink (Travel mode)

```yaml
alias: Teltonika — fallback notice when WAN lost in Travel
mode: single
trigger:
  - platform: state
    entity_id: binary_sensor.rc_net_teltonika_reachable
    to: "off"
    for: "00:02:00"
condition:
  - condition: state
    entity_id: input_select.rc_mode
    state: "travel"
  - condition: state
    entity_id: binary_sensor.rc_net_starlink_reachable
    state: "on"
action:
  - service: persistent_notification.create
    data:
      title: RoamCore — Teltonika fallback to Starlink
      message: >-
        Teltonika unreachable for 2 min while in Travel mode;
        Starlink is up — falling back. Open the Networking section
        for status.
```

### §5.2 — Reboot on lost internet (one-tap or auto)

```yaml
alias: Teltonika — reboot on lost internet
mode: single
trigger:
  - platform: state
    entity_id: button.rc_net_teltonika_reboot_now
    to: "pressed"
  - platform: state
    entity_id: binary_sensor.rc_net_internet_reachable
    to: "off"
    for: "00:05:00"
condition:
  - condition: state
    entity_id: binary_sensor.rc_net_teltonika_reachable
    state: "on"
  - condition: not
    conditions:
      - condition: state
        entity_id: input_select.rc_mode
        state: "stealth"
action:
  # Path A (plug option): toggle the plug
  - choose:
      - conditions:
          - condition: template
            value_template: >
              {{ states('switch.rc_net_teltonika_plug') not in ['unknown', 'unavailable'] }}
        sequence:
          - service: switch.turn_off
            target:
              entity_id: switch.rc_net_teltonika_plug
          - delay: "00:00:05"
          - service: switch.turn_on
            target:
              entity_id: switch.rc_net_teltonika_plug
  # Path B (REST option): call the REST command
  - choose:
      - conditions:
          - condition: template
            value_template: >
              {{ states('switch.rc_net_teltonika_plug') in ['unknown', 'unavailable'] }}
        sequence:
          - service: rest_command.teltonika_reboot
```

### §5.3 — Suppress reboot in Stealth

This condition is inline in §5.2 (see the `condition: not ... state:
stealth` block). If you want a clearer separation, drop the inline
condition and split into two automations: one that fires only in
non-Stealth modes, one that fires only on explicit button press and
ignores mode. The recipe ships the combined version for brevity.

### §5.4 — Monthly-data-counter reset

```yaml
alias: Teltonika — reset monthly-data counter
mode: single
trigger:
  - platform: state
    entity_id: input_boolean.rc_net_teltonika_data_reset
    to: "on"
action:
  # Reset the underlying byte-counter sensor so the GB contract
  # value drops back to ~0 on the next poll.
  - service: homeassistant.update_entity
    target:
      entity_id: sensor.teltonika_data_used_bytes
  - service: input_boolean.turn_off
    target:
      entity_id: input_boolean.rc_net_teltonika_data_reset
  - service: persistent_notification.create
    data:
      title: RoamCore — Teltonika monthly-data reset
      message: >-
        Monthly data counter reset for Teltonika. The
        `sensor.rc_net_teltonika_data_used_gb` tile will reflect
        the reset on the next poll (~30 s for SNMP, immediate for
        REST).
```

## §6 Troubleshooting

- **All Teltonika tiles grayed out.** The SNMP/REST integration
  cannot reach the router. Check: is the router powered? Is the LAN
  reachable from HA? Is the SNMP community string / REST API token
  correct? Open HA → **Developer Tools → Template** against
  `states('sensor.teltonika_router_uptime')` — if `unknown`, the
  integration has lost the device.
- **`rc_net_teltonika_signal_pct` stuck at 0.** The RSSI OID is
  wrong for your firmware. Consult
  <https://wiki.teltonika-networks.com/view/SNMP> for your model's
  exact OID; substitute in `§A.3` and re-test.
- **`rc_net_teltonika_lte_mode` shows `unknown`.** The LTE-mode OID
  integer-to-string mapping in `§4.1` doesn't match your firmware's
  encoding. Run `snmpwalk -v2c -c <community> <router_ip>
  1.3.6.1.4.1.48690.10.10.20.0` and update the integer mapping.
- **Monthly data counter drifts.** The §B SNMP byte counter is a
  cumulative counter on the router; if the router reboots or the
  SIM is swapped, the counter resets to 0 (which would make
  `rc_net_teltonika_data_used_gb` look like data went negative). The
  recipe's §5.4 monthly-data-reset automation handles the
  end-of-month case; for the reboot case, add an automation that
  detects the counter dropping and resets `input_boolean.rc_net_teltonika_data_reset`
  accordingly.
- **Reboot doesn't trigger.** If you're on Path A's plug option,
  verify the plug's HA entity is alive; if you're on Path B's REST
  option, verify the API token and the `/cgi-bin/api/reboot`
  endpoint on your firmware (some RUT-series firmware uses
  `/api/reboot` instead).
- **Stealth mode blocks the auto-reboot.** That's intentional — Stealth
  silent hours mean "don't wake the van up at 3 AM". To force a
  reboot while in Stealth, press `button.rc_net_teltonika_reboot_now`
  manually — the §5.2 automation honors explicit button presses
  regardless of mode.
- **RMS rate-limited.** Teltonika's cloud RMS API has rate limits.
  If you wired Path B via RMS and you're hitting limits, switch to
  the local REST API instead, or bump `scan_interval` on the REST
  sensors from 30 s to 5 min.

## §7 Privacy

- **Local-first.** Path A (SNMP) is fully local — the MIB-II +
  Teltonika-private OIDs are served on the LAN only (UDP/161).
  Path B (REST) is also local if you use the router's local REST
  API; if you choose the RMS cloud API instead, telemetry rides
  through Teltonika's cloud, which is the operator's existing
  relationship with Teltonika (RoamCore adds no cloud dependency on
  top of the operator's existing RMS usage).
- **No MAC / serial / IMSI / phone number captured.** The contract
  intentionally publishes only the high-level telemetry (signal,
  WAN state, LTE mode, carrier *name*, data used, uptime, public
  IP). The raw IMEI / IMSI / serial numbers stay on the router and
  are not pulled into HA by the recipe.
- **Public IP** (`sensor.rc_net_teltonika_public_ip`) is the
  Teltonika router's WAN IP as seen by the operator's carrier. This
  is the same IP the operator already has via the Teltonika Web
  UI; the recipe surfaces it for OpenClaw queries but does not
  publish it to any external service.
- **The smart-plug integration** (Path A's plug option) uses whatever
  protocol your plug speaks (Kasa cloud, Shelly cloud, local Zigbee,
  local Modbus). RoamCore does not add any cloud dependency on top
  — if your plug uses a cloud, that's the plug's existing behavior,
  not RoamCore's.
- **No vendor double-stamping.** No `teltonika`, `rut`, `rutx`,
  `rutm`, `rms`, `snmp`, or other vendor name appears in any
  `rc_net_teltonika_*` entity, OpenClaw summary key, or dashboard
  tile beyond the subsystem prefix `rc_net_teltonika_*`. The
  contract is intentionally vendor-neutral per
  `docs/reference/rc-entity-naming.md`.

## Promotion to tier-a (outline)

When a real Teltonika router lands on the bench (likely via
`testcontainers/snmp-sim` with a synthetic MIB-II + Teltonika-private-
OID fixture, or a recorded SNMP capture), this connection is the
candidate to promote to tier-a:

1. Add a native `config_flow.py` (or a thin wrapper around the
   upstream HA `snmp` integration if a community "Teltonika" wrapper
   lands in core) that walks the operator through enabling SNMP +
   entering the community string + selecting the firmware profile.
2. Add an integration test that asserts the `rc_net_teltonika_*`
   contract entities appear after a synthetic SNMP-poll with a
   canned MIB-II + Teltonika-private-OID response.
3. Flip `tier_requirements` to include `working_config_flow` +
   `integration_test_passes` + `no_manual_yaml_required`.
4. Drop `tier_warnings` entries that mention no-real-router /
   recipe-depends-on-user / firmware-specific-oids-may-shift.
5. Flip `status` from `beta` to `shipped`.
6. Flip `wizard.one_tap` to `true`.

Until then, this stays at tier-b (beta, recipe) — the recipe is
sound, the contract is honest, and we don't claim one-tap coverage
we don't have.