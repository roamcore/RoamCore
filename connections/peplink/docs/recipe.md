# Peplink — tier-b recipe connection

**Tier:** B (recipe)
**Audience:** A RoamCore user who has a Peplink Balance / MAX / EP-series
multi-WAN router on the van's LAN (Balance One / Balance 20 / Balance 30
/ MAX 700 / EP 5 / etc.), wants the telemetry + force-failover +
WAN-priority story that powers the RoamCore `rc_net_peplink_*` contract
tiles + OpenClaw multi-WAN queries.

This howto is mirrored into `docs/connections/peplink.md` by the
catalog cron (`scripts/build_catalog.py`) so it shows up under the
public docs site's "Connections" section. Keep this recipe as the
source of truth.

## What is Peplink in RoamCore?

Peplink (<https://www.peplink.com/>) makes rugged multi-WAN routers
that are very popular in van life, marine installations, and remote
sites. The Balance / MAX / EP hardware runs Peplink's firmware on
top of a hardened Linux, with a stable MIB-II + Peplink-private
SNMP OID surface for monitoring (most Peplink units ship SNMP
enabled-or-enableable), plus a documented InControl 2 cloud REST API
at `https://api.ic.peplink.com/...` for fleet management via the
community `hass-incontrol2` HACS integration
(<https://github.com/sneelco/hass-incontrol2>).

In RoamCore, Peplink is the **multi-WAN glue** for vans that bond /
failover multiple WANs through a single Peplink router:

- **Telemetry** (reachable, WAN1 state, WAN2 state, active WAN, WAN
  failover count in last 24h, load-balance health score 0–100,
  uptime, public IP of the active WAN) sourced from SNMP (Path A)
  or the Peplink InControl 2 REST API (Path B).
- **Force-failover affordance** (one-tap "force peplink failover")
  wired to either the Peplink REST/SNMP-triggered WAN-swap endpoint
  (Path A's native option) OR the InControl 2 fleet-action endpoint
  (Path B).
- **WAN-priority select** (one-tap "wan1 first / wan2 first /
  load-balanced") wired to either the Peplink REST/SNMP-triggered
  WAN-priority setter (Path A) or the InControl 2 fleet-policy
  endpoint (Path B).
- **Mode-aware behavior** treats Peplink as the multi-WAN glue
  between Starlink + Teltonika + campground Wi-Fi: in Travel /
  Boost mode prefer cellular (Teltonika) first; in Home / Shore
  mode prefer Starlink first; Stealth silent hours suppress the
  force-failover trigger + any WAN-restart automations; alert when
  WAN failover count exceeds 3 in 24h.
- **OpenClaw multi-WAN queries** ("is peplink online?", "what's
  peplink's active WAN?", "how many peplink failovers in the last
  24h?", "what's peplink's load-balance health?", "what's peplink's
  public IP?", "force a peplink failover", "refresh peplink
  telemetry") bind to the contract entities. The corresponding
  OpenClaw query keys (used by the agent wiring) are:
  `is_peplink_online`, `peplink_active_wan`,
  `peplink_wan_failover_count_24h`, `peplink_wan_health_score`,
  `peplink_public_ip`, `force_peplink_failover`,
  `refresh_peplink_telemetry` — the recipe exposes a
  `button.rc_net_peplink_force_failover` for the
  `force_peplink_failover` agent-action allowlist so the OpenClaw
  wiring has a known-good button to call.

RoamCore does **not** ship a Peplink router or a RoamCore-owned
native integration. There is no canonical RoamCore-owned upstream HA
integration for "talk to a Peplink router as a multi-WAN slice" —
the operator's SNMP-vs-InControl2 choice is model + firmware +
fleet-size driven, and the underlying HA core `snmp` integration
(or the HACS `hass-incontrol2` community integration for Path B) is
the upstream truth. So we publish a recipe that walks you through the
wiring, then layer a small contract on top: the `rc_net_peplink_*`
dashboard tiles + the OpenClaw queries that bind to those contract
entities.

**Why tier-b:** RoamCore has no real Peplink router on the bench to
integration-test against, no native HA integration to point at, and
the operator's SNMP-vs-InControl2 choice is model + firmware +
fleet-size driven — so the audit-recommended config_flow can't be
canonical here. The recipe is sound (it leans on HA's core `snmp`
integration OR the HACS `hass-incontrol2` community integration +
the well-understood MIB-II + Peplink-private OIDs), but we cannot
claim one-tap automation. The promotion outline at the bottom of
this recipe describes exactly what needs to happen to flip this to
tier-a.

**Two install paths (operator picks based on firmware/model + fleet
size):**

- **Path A — HA core SNMP integration** (recommended for
  single-router operators with SNMP-enabled Peplink firmware —
  most Peplink units ship SNMP enabled-or-enableable, exposing
  MIB-II + Peplink-private OIDs for WAN state, signal strength per
  WAN, WAN priority, load-balance health, uptime, throughput, and
  public IP per WAN). The operator enables SNMP v2c (or v3) on
  the router (System → SNMP → Enable), gives HA the router IP +
  community string, and the recipe walks them through mapping the
  MIB-II + Peplink-private OIDs into the `rc_net_peplink_*`
  contract tiles via the recipe §4 helper YAML.
- **Path B — Peplink InControl 2 REST API via the community
  `hass-incontrol2` HACS integration** (recommended for operators
  managing >1 Peplink device — a fleet). The operator creates an
  InControl 2 API key at <https://ic.peplink.com/>, installs the
  HACS `hass-incontrol2` integration
  (<https://github.com/sneelco/hass-incontrol2>), and the recipe
  walks them through mapping the InControl 2 fleet entities into
  the same `rc_net_peplink_*` contract tiles.

Both paths land on the same `rc_net_peplink_*` contract tiles. The
wizard asks the operator which path they wired; the contract tiles
are identical either way.

## Prerequisites

Before starting the recipe, make sure you have:

- **Peplink Balance / MAX / EP-series router on the van's LAN.**
  Balance One, Balance 20, Balance 30, MAX 700, EP 5, etc. all
  expose the same core MIB-II + Peplink-private SNMP OID surface
  (firmware-specific OIDs may shift — see
  `tier_warnings: model_and_firmware_variation_across_peplink_line`
  in the manifest).
- **SNMP credentials OR InControl 2 API key** (your choice, depends
  on model + firmware + fleet size — both are documented):
  - **For Path A (SNMP):** enable SNMP on the router (System →
    SNMP → Enable), set a community string (v2c) or v3 credentials.
    Note the community string + the router's LAN IP.
  - **For Path B (InControl 2):** create an InControl 2 account at
    <https://ic.peplink.com/>, generate an API key, and register
    your Peplink fleet under that account. Note the API key + the
    organization ID.
- **Network reachability** between HA and the Peplink router (the
  same LAN, or a routed VLAN — most installs are LAN-local). Path
  B's InControl 2 cloud API requires outbound HTTPS from HA to
  `api.ic.peplink.com` — make sure your HA host can reach the
  internet.
- **(Optional) HACS installed** if you go Path B (the
  `hass-incontrol2` integration is a HACS integration, not core).

## Path A — HA core SNMP integration (recommended for single-router operators)

The default install for RoamCore users on any SNMP-enabled Peplink
firmware with a single Peplink router.

### A.1 — Enable SNMP on the Peplink router

1. Log into the router's Web UI (default `http://192.168.1.1/`, or
   whatever IP the router ended up at on your LAN).
2. Navigate to **System → SNMP** (or **Advanced → SNMP** on
   firmware variants).
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

- Host: `192.168.1.<router_lan_ip>` (the Peplink's LAN IP).
- Port: `161` (default).
- Community string: `<your community string from A.1>`.
- Version: `2c` (or `3` + v3 credentials if you went v3).
- Timeout / retries: defaults are fine.

HA will create a handful of base SNMP sensors (system description,
uptime, contact, name, location) — these become the foundation for
the recipe §4 helpers.

### A.3 — Add Peplink-private OID sensors

The Peplink-private OIDs (WAN1/WAN2 state, signal strength per WAN,
WAN priority, load-balance health, throughput, public IP per WAN)
need additional `snmp` sensors in HA's `snmp` integration. The
simplest path is a package YAML in
`homeassistant/packages/roamcore_peplink_snmp.yaml` that the
operator loads via `homeassistant.packages:` in `configuration.yaml`:

```yaml
# RoamCore Peplink SNMP package (recipe §A.3 / §4.1).
# Adjust OIDs to match your exact Peplink model + firmware;
# consult https://www.peplink.com/knowledgebase/ for the
# canonical OID list per model + firmware version.

snmp:
  - name: peplink_router
    host: 192.168.1.<router_lan_ip>
    port: 161
    community: <your_community_string>
    version: 2c
    timeout: 10
    retries: 2
    baseoid: 1.3.6.1.4.1.23695      # Peplink private enterprise OID root
    scan_interval: 30
    sensors:
      - name: "Peplink WAN1 state"
        unique_id: peplink_wan1_state_raw
        oid: 1.3.6.1.4.1.23695.2.1.1.0   # placeholder; replace with your model's OID
        value_template: "{{ value }}"
      - name: "Peplink WAN2 state"
        unique_id: peplink_wan2_state_raw
        oid: 1.3.6.1.4.1.23695.2.1.2.0   # placeholder
        value_template: "{{ value }}"
      - name: "Peplink active WAN"
        unique_id: peplink_active_wan_raw
        oid: 1.3.6.1.4.1.23695.2.1.3.0   # placeholder
        value_template: "{{ value }}"
      - name: "Peplink WAN failover count (last 24h)"
        unique_id: peplink_wan_failover_count_24h_raw
        oid: 1.3.6.1.4.1.23695.2.1.4.0   # placeholder
        value_template: "{{ value | int(0) }}"
      - name: "Peplink load-balance health"
        unique_id: peplink_wan_health_score_raw
        oid: 1.3.6.1.4.1.23695.2.1.5.0   # placeholder
        unit_of_measurement: "score"
        value_template: "{{ value | int(0) }}"
      - name: "Peplink public IP (active WAN)"
        unique_id: peplink_public_ip_raw
        oid: 1.3.6.1.4.1.23695.2.1.6.0   # placeholder
        value_template: "{{ value }}"
```

**Important:** the OIDs above are placeholders. The actual OIDs per
Peplink model + firmware are documented on
<https://www.peplink.com/knowledgebase/> and the Peplink MIB
downloads. The recipe's job is to publish the *pattern*; the
operator fills in their exact OIDs. The
`tier_warnings: model_and_firmware_variation_across_peplink_line`
flag in the manifest is the audit-honest acknowledgement of this
operator-side step.

### A.4 — Create the `rc_net_peplink_*` contract tiles

In HA → **Helpers**, create the following (the recipe ships copy-
pastable YAML for these in §4.1 below):

- `binary_sensor.rc_net_peplink_reachable` — template binary
  sensor reporting ON if the SNMP integration reports the router as
  up (HA's standard "entity is alive" check, scoped to the SNMP
  device tracker).
- `sensor.rc_net_peplink_wan1_state` — template sensor mapping
  the raw Peplink WAN1 state to `connected | disconnected | connecting`.
- `sensor.rc_net_peplink_wan2_state` — template sensor mapping
  the raw Peplink WAN2 state to `connected | disconnected | connecting`.
- `sensor.rc_net_peplink_active_wan` — template sensor exposing
  which WAN is currently active: `wan1 | wan2 | load-balanced`.
- `sensor.rc_net_peplink_wan_failover_count_24h` — template sensor
  exposing the failover count in the last 24h (driven by the
  InControl 2 / SNMP-reported counter).
- `sensor.rc_net_peplink_wan_health_score` — template sensor
  exposing the load-balance health score 0–100.
- `sensor.rc_net_peplink_uptime_hours` — template sensor exposing
  the SNMP uptime in hours.
- `sensor.rc_net_peplink_public_ip` — template sensor exposing
  the active WAN's public IP.
- `button.rc_net_peplink_refresh_now` — one-tap refresh trigger
  (force-poll the router for fresh telemetry).
- `button.rc_net_peplink_force_failover` — one-tap force-failover
  trigger (swap to the other WAN for testing or manual control).
- `select.rc_net_peplink_wan_priority` — operator chooses which
  WAN is preferred: `WAN1 first | WAN2 first | load-balanced`.

### A.5 — Wire the force-failover affordance (Path A's REST option)

Same pattern as the Starlink slice's sleep-timer wiring, adapted for
multi-WAN swap:

1. Confirm your Peplink firmware exposes a REST WAN-swap endpoint
   (most do — see <https://www.peplink.com/ic2-api-doc/> for the
   exact endpoint per firmware).
2. Wire it via HA's `rest_command`:

```yaml
rest_command:
  peplink_force_failover:
    url: "http://<router_lan_ip>/api/force_failover"
    method: POST
    headers:
      Authorization: "Bearer <your_api_token>"
      Content-Type: "application/json"
    payload: '{"action": "swap_wan"}'
```

3. Alternatively, if your Peplink firmware exposes the WAN-priority
   setter via REST, add a second `rest_command` for setting WAN
   priority (the recipe §5 automations call this on mode changes):

```yaml
rest_command:
  peplink_set_wan_priority:
    url: "http://<router_lan_ip>/api/wan_priority"
    method: POST
    headers:
      Authorization: "Bearer <your_api_token>"
      Content-Type: "application/json"
    payload: '{"priority": "{{ priority_value }}"}'
```

The recipe §5.2 force-failover automation calls
`rest_command.peplink_force_failover` (Path A's REST option) or the
InControl 2 fleet-action endpoint (Path B).

### A.6 — Enable the recipe §5 automations

The recipe ships four automations in §5.1 / §5.2 / §5.3 / §5.4:

- Mode-aware multi-WAN preference (when in Travel / Boost mode AND
  Teltonika is reachable, prefer cellular first; when in Home /
  Shore mode AND Starlink is reachable, prefer Starlink first —
  this feeds `select.rc_net_peplink_wan_priority` via
  `rest_command.peplink_set_wan_priority`).
- Force-failover button + auto-force-failover on WAN loss (when
  `button.rc_net_peplink_force_failover` is pressed OR the active
  WAN's state goes disconnected for >2 min, swap to the other WAN;
  suppress in Stealth silent hours).
- Daily WAN-failover-count reset (at midnight, reset the
  `sensor.rc_net_peplink_wan_failover_count_24h` counter so the
  24h window stays accurate).
- Alert when WAN failover count exceeds 3 in 24h (when
  `sensor.rc_net_peplink_wan_failover_count_24h` > 3, send a
  persistent_notification + optional Telegram alert via the
  `telegram_bot` integration).

### A.7 — Verify

1. Open the RoamCore dashboard → **Networking** section.
2. The `rc_net_peplink_*` tiles should be visible. If any are
   grayed out, check §7 (Troubleshooting).
3. Tap the refresh button. The SNMP values should refresh within
   30 s (the §A.3 scan_interval).
4. Tap the force-failover button. The Peplink router should swap
   to the other WAN within ~2 s, the active WAN tile should flip,
   and the load-balance health should briefly dip then recover.

## Path B — Peplink InControl 2 REST API (recommended for multi-device fleets)

Identical contract + helpers as Path A; the only difference is how
the operator pulls telemetry from the router (and which routers are
in scope — Path B handles a fleet).

### B.1 — Install the HACS `hass-incontrol2` integration

1. Install HACS on your HA instance if it isn't already (HACS is the
   Home Assistant Community Store — install via
   <https://hacs.xyz/docs/setup/download>).
2. In HA → **HACS → Integrations → Explore & Add Repositories**,
   search for `hass-incontrol2` (community integration by
   `@sneelco`).
3. Install `hass-incontrol2` and restart HA.

### B.2 — Create an InControl 2 API key

1. Log into <https://ic.peplink.com/>.
2. Navigate to **Settings → API Keys**.
3. Generate a new API key. Note the API key + the organization ID.

### B.3 — Add the InControl 2 integration in HA

In HA → **Settings → Devices & Services → Add Integration →
InControl 2** (after the HACS install in §B.1), with:

- API key: `<your_api_key_from_§B.2>`.
- Organization ID: `<your_org_id>`.

The integration will register your Peplink fleet under HA and
create entities per router (WAN state per WAN, signal strength per
WAN, WAN priority, load-balance health, uptime, throughput, public
IP per WAN, etc.).

### B.4 — Map InControl 2 entities to the same contract helpers

Same as Path A — drop the recipe §4.1 helper YAML into the same
package, and replace the SNMP-sourced `value_template:` references
with the InControl 2 entity references that correspond to the same
field (per-router entities look like
`binary_sensor.peplink_<router_name>_online`,
`sensor.peplink_<router_name>_wan_<n>_state`, etc.). The contract
tiles stay identical; only the upstream sourcing changes.

### B.5 — Wire the force-failover affordance (Path B's InControl 2 option)

The InControl 2 cloud REST API exposes a fleet-action endpoint that
triggers a WAN swap on a specific router in your fleet. Wire it via
HA's `rest_command`:

```yaml
rest_command:
  peplink_force_failover_ic2:
    url: "https://api.ic.peplink.com/v1/organization/{{ org_id }}/device/{{ device_id }}/action"
    method: POST
    headers:
      Authorization: "Bearer <your_api_key>"
      Content-Type: "application/json"
    payload: '{"action": "swap_wan"}'
```

The recipe §5.2 force-failover automation calls
`rest_command.peplink_force_failover_ic2` (Path B's InControl 2
option) instead of the local REST endpoint if you went Path B
instead of Path A.

### B.6 — Verify

Same as Path A §A.7 — the contract tiles + the force-failover
button behave identically. The only difference is the upstream
sourcing (cloud REST polling at InControl 2 cadence vs local SNMP
polling at your chosen scan_interval).

## §5 RoamCore contract entities

The full listing the wizard + dashboard + OpenClaw rely on:

| Entity | Type | States | Source |
|---|---|---|---|
| `binary_sensor.rc_net_peplink_reachable` | binary_sensor | ON / OFF | HA last-seen check on SNMP device tracker (Path A) or InControl 2 fleet device tracker (Path B) |
| `sensor.rc_net_peplink_wan1_state` | sensor | `connected \| disconnected \| connecting` | template over SNMP/InControl 2 WAN1 state raw value |
| `sensor.rc_net_peplink_wan2_state` | sensor | `connected \| disconnected \| connecting` | template over SNMP/InControl 2 WAN2 state raw value |
| `sensor.rc_net_peplink_active_wan` | sensor | `wan1 \| wan2 \| load-balanced` | template over SNMP/InControl 2 active WAN raw value |
| `sensor.rc_net_peplink_wan_failover_count_24h` | sensor | int count | template over SNMP/InControl 2 failover counter (reset at midnight by §5.3) |
| `sensor.rc_net_peplink_wan_health_score` | sensor | 0–100 | template over SNMP/InControl 2 load-balance health raw value |
| `sensor.rc_net_peplink_uptime_hours` | sensor | float hours | template over SNMP/InControl 2 uptime |
| `sensor.rc_net_peplink_public_ip` | sensor | string (IP) | template over active WAN's public IP raw value |
| `button.rc_net_peplink_refresh_now` | button | (press) | calls `homeassistant.update_entity` on all the SNMP/InControl 2 sensors |
| `button.rc_net_peplink_force_failover` | button | (press) | calls `rest_command.peplink_force_failover` (Path A) or `rest_command.peplink_force_failover_ic2` (Path B) |
| `select.rc_net_peplink_wan_priority` | select | `WAN1 first \| WAN2 first \| load-balanced` | operator choice; §5.1 automation listens + writes back to `rest_command.peplink_set_wan_priority` (Path A) or `rest_command.peplink_set_wan_priority_ic2` (Path B) |

All grayed-out / `unknown` fallback when the SNMP/InControl 2
integration is in error state (router offline, community string
wrong, v3 credentials wrong, InControl 2 API key revoked, InControl
2 rate-limited).

### §5.1 — Copy-pasteable helper YAML

Drop into `homeassistant/packages/roamcore_peplink.yaml`:

```yaml
# RoamCore Peplink contract helpers (recipe §5.1).
# All entities are vendor-neutral per docs/reference/rc-entity-naming.md.
# Replace `sensor.peplink_*_raw` references with the actual entity ids
# your integration exposes (Path A: the §A.3 package; Path B: the
# `hass-incontrol2` per-router entities).

input_number:
  rc_net_peplink_wan_failover_count_24h_baseline:
    name: Peplink WAN-failover-count baseline (contract)
    min: 0
    max: 999
    step: 1
    icon: mdi:swap-horizontal

template:
  - binary_sensor:
      - name: Peplink reachable (contract)
        unique_id: rc_net_peplink_reachable
        state: >
          {{ states('sensor.peplink_router_uptime') not in ['unknown', 'unavailable'] }}
        device_class: connectivity
        icon: mdi:router-wireless
  - sensor:
      - name: Peplink WAN1 state (contract)
        unique_id: rc_net_peplink_wan1_state
        state: >
          {% set raw = states('sensor.peplink_wan1_state_raw') | default('unknown') %}
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
      - name: Peplink WAN2 state (contract)
        unique_id: rc_net_peplink_wan2_state
        state: >
          {% set raw = states('sensor.peplink_wan2_state_raw') | default('unknown') %}
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
      - name: Peplink active WAN (contract)
        unique_id: rc_net_peplink_active_wan
        state: >
          {% set raw = states('sensor.peplink_active_wan_raw') | default('unknown') %}
          {% if raw in ['1', 'wan1'] %}
            wan1
          {% elif raw in ['2', 'wan2'] %}
            wan2
          {% elif raw in ['0', 'balanced', 'load_balanced'] %}
            load-balanced
          {% else %}
            unknown
          {% endif %}
        icon: mdi:swap-horizontal
      - name: Peplink WAN failover count 24h (contract)
        unique_id: rc_net_peplink_wan_failover_count_24h
        state: >
          {% set baseline = states('input_number.rc_net_peplink_wan_failover_count_24h_baseline') | float(0) %}
          {% set raw = states('sensor.peplink_wan_failover_count_24h_raw') | float(0) %}
          {{ max(0, raw - baseline) | int(0) }}
        icon: mdi:counter
      - name: Peplink load-balance health (contract)
        unique_id: rc_net_peplink_wan_health_score
        unit_of_measurement: "score"
        state: >
          {{ states('sensor.peplink_wan_health_score_raw') | int(0) }}
        icon: mdi:heart-pulse
      - name: Peplink uptime (contract, hours)
        unique_id: rc_net_peplink_uptime_hours
        unit_of_measurement: "h"
        state: >
          {{ (states('sensor.peplink_router_uptime') | float(0) / 3600) | round(2) }}
        icon: mdi:clock-outline
      - name: Peplink public IP (contract, active WAN)
        unique_id: rc_net_peplink_public_ip
        state: "{{ states('sensor.peplink_public_ip_raw') | default('unknown') }}"
        icon: mdi:ip

select:
  - name: Peplink WAN priority (contract)
    unique_id: rc_net_peplink_wan_priority
    options:
      - "WAN1 first"
      - "WAN2 first"
      - "load-balanced"
    icon: mdi:swap-horizontal

button:
  - name: Refresh Peplink telemetry (contract)
    unique_id: rc_net_peplink_refresh_now
    icon: mdi:refresh
    press:
      - homeassistant.update_entity:
          entity_id:
            - sensor.peplink_wan1_state_raw
            - sensor.peplink_wan2_state_raw
            - sensor.peplink_active_wan_raw
            - sensor.peplink_wan_failover_count_24h_raw
            - sensor.peplink_wan_health_score_raw
            - sensor.peplink_public_ip_raw
            - sensor.peplink_router_uptime
  - name: Force Peplink failover (contract)
    unique_id: rc_net_peplink_force_failover
    icon: mdi:swap-horizontal-bold
    # The §5.2 automation listens for this press and either calls
    # `rest_command.peplink_force_failover` (Path A's local REST
    # option) or `rest_command.peplink_force_failover_ic2` (Path B's
    # InControl 2 fleet-action endpoint).
    # OpenClaw agent-action allowlist: this button is the target of
    # the `force_peplink_failover` query key.
```

(For Path A's local REST option, also include the
`rest_command.peplink_force_failover` and
`rest_command.peplink_set_wan_priority` blocks from §A.5 above.
For Path B's InControl 2 option, include the
`rest_command.peplink_force_failover_ic2` block from §B.5 above.)

## §6 Automations

Four sample automations, copy-pasteable into
`homeassistant/automations/roamcore_peplink_*.yaml`:

### §6.1 — Mode-aware multi-WAN preference

```yaml
alias: Peplink — mode-aware WAN priority (cellular in Travel/Boost, Starlink in Home/Shore)
mode: single
trigger:
  - platform: state
    entity_id: input_select.rc_mode
condition:
  - condition: state
    entity_id: binary_sensor.rc_net_peplink_reachable
    state: "on"
action:
  - choose:
      # Travel / Boost mode: prefer cellular (Teltonika) first.
      - conditions:
          - condition: state
            entity_id: input_select.rc_mode
            state: "travel"
          - condition: state
            entity_id: binary_sensor.rc_net_teltonika_reachable
            state: "on"
        sequence:
          - service: select.select_option
            target:
              entity_id: select.rc_net_peplink_wan_priority
            data:
              option: "WAN1 first"   # operator convention: WAN1 = cellular (Teltonika)
      # Boost mode: same preference as Travel.
      - conditions:
          - condition: state
            entity_id: input_select.rc_mode
            state: "boost"
          - condition: state
            entity_id: binary_sensor.rc_net_teltonika_reachable
            state: "on"
        sequence:
          - service: select.select_option
            target:
              entity_id: select.rc_net_peplink_wan_priority
            data:
              option: "WAN1 first"
      # Home / Shore mode: prefer Starlink first (cheaper, faster when stationary).
      - conditions:
          - condition: state
            entity_id: input_select.rc_mode
            state: "home"
          - condition: state
            entity_id: binary_sensor.rc_net_starlink_reachable
            state: "on"
        sequence:
          - service: select.select_option
            target:
              entity_id: select.rc_net_peplink_wan_priority
            data:
              option: "WAN2 first"   # operator convention: WAN2 = Starlink
      # Shore mode: same preference as Home.
      - conditions:
          - condition: state
            entity_id: input_select.rc_mode
            state: "shore"
          - condition: state
            entity_id: binary_sensor.rc_net_starlink_reachable
            state: "on"
        sequence:
          - service: select.select_option
            target:
              entity_id: select.rc_net_peplink_wan_priority
            data:
              option: "WAN2 first"
```

### §6.2 — Force-failover button + auto-force-failover on WAN loss

```yaml
alias: Peplink — force failover (button or auto on WAN loss)
mode: single
trigger:
  - platform: state
    entity_id: button.rc_net_peplink_force_failover
    to: "pressed"
  - platform: state
    entity_id: sensor.rc_net_peplink_active_wan
    to: "wan1"
    for: "00:02:00"
  - platform: state
    entity_id: sensor.rc_net_peplink_wan1_state
    to: "disconnected"
    for: "00:02:00"
condition:
  # Stealth silent hours suppress the auto-failover path; explicit
  # button presses bypass the Stealth check.
  - condition: template
    value_template: >
      {{ trigger.entity_id == 'button.rc_net_peplink_force_failover'
         or states('input_select.rc_mode') != 'stealth' }}
  - condition: state
    entity_id: binary_sensor.rc_net_peplink_reachable
    state: "on"
action:
  # Path A (local REST option): call the local WAN-swap endpoint.
  - choose:
      - conditions:
          - condition: template
            value_template: >
              {{ states('rest_command.peplink_force_failover') not in ['unknown', 'unavailable'] }}
        sequence:
          - service: rest_command.peplink_force_failover
  # Path B (InControl 2 fleet-action option): call the cloud endpoint.
  - choose:
      - conditions:
          - condition: template
            value_template: >
              {{ states('rest_command.peplink_force_failover_ic2') not in ['unknown', 'unavailable'] }}
        sequence:
          - service: rest_command.peplink_force_failover_ic2
  - service: persistent_notification.create
    data:
      title: RoamCore — Peplink force-failover triggered
      message: >-
        Peplink force-failover triggered
        {% if trigger.entity_id == 'button.rc_net_peplink_force_failover' %}
          by explicit button press
        {% else %}
          by auto-detection (active WAN loss for 2 min)
        {% endif %}.
        Open the Networking section for status.
```

### §6.3 — Daily WAN-failover-count reset

```yaml
alias: Peplink — reset WAN-failover-count 24h baseline at midnight
mode: single
trigger:
  - platform: time
    at: "00:00:00"
action:
  - service: input_number.set_value
    target:
      entity_id: input_number.rc_net_peplink_wan_failover_count_24h_baseline
    data:
      value: >
        {{ states('sensor.peplink_wan_failover_count_24h_raw') | float(0) }}
  - service: persistent_notification.create
    data:
      title: RoamCore — Peplink WAN-failover-count 24h reset
      message: >-
        Midnight reset of the Peplink WAN-failover-count 24h
        baseline. The
        `sensor.rc_net_peplink_wan_failover_count_24h` tile now
        reports failovers in the rolling 24h window.
```

### §6.4 — Alert when WAN failover count exceeds 3 in 24h

```yaml
alias: Peplink — alert on excessive WAN failovers (>3 in 24h)
mode: single
trigger:
  - platform: numeric_state
    entity_id: sensor.rc_net_peplink_wan_failover_count_24h
    above: 3
action:
  - service: persistent_notification.create
    data:
      title: RoamCore — Peplink excessive WAN failovers
      message: >-
        Peplink has failover'd more than 3 times in the last 24h
        (currently
        {{ states('sensor.rc_net_peplink_wan_failover_count_24h') }}
        failovers). Investigate WAN stability — likely a flaky WAN
        or a Peplink health issue.
  # Optional: forward to Telegram if the operator has the
  # telegram_bot integration set up.
  - choose:
      - conditions:
          - condition: template
            value_template: >
              {{ states('telegram_bot') not in ['unknown', 'unavailable'] }}
        sequence:
          - service: telegram_bot.send_message
            data:
              message: >-
                RoamCore alert: Peplink excessive WAN failovers
                ({{ states('sensor.rc_net_peplink_wan_failover_count_24h') }}
                failovers in 24h). Investigate WAN stability.
```

## §7 Troubleshooting

- **All Peplink tiles grayed out.** The SNMP/InControl 2 integration
  cannot reach the router / fleet. Check: is the router powered? Is
  the LAN reachable from HA (Path A) or is the InControl 2 cloud
  reachable from HA (Path B)? Is the SNMP community string /
  InControl 2 API key correct? Open HA → **Developer Tools →
  Template** against `states('sensor.peplink_router_uptime')` (Path
  A) or `states('binary_sensor.peplink_<router>_online')` (Path
  B) — if `unknown`, the integration has lost the device.
- **SNMP community string mismatch.** Path A's most common setup
  error — the community string on the router (System → SNMP →
  Community) doesn't match what you entered in HA. Verify both
  sides match exactly (case-sensitive, no trailing whitespace).
  See `tier_warnings: recipe_depends_on_user_running_peplink` for
  the operator-side honesty framing.
- **InControl 2 API key revoked.** Path B's most common runtime
  error — the API key was revoked or rotated on the InControl 2
  web UI but HA still has the old one. Re-generate the key in
  InControl 2, update the `hass-incontrol2` integration config,
  and reload.
- **Peplink firmware update changes OID layout.** When the
  operator updates the Peplink firmware, the Peplink-private OID
  tree can shift (the canonical MIB-II surface stays stable, but
  the per-model enterprise OIDs for WAN state / load-balance
  health / public IP can move). Re-run `snmpwalk -v2c -c
  <community> <router_ip> 1.3.6.1.4.1.23695` against the new
  firmware, compare to your §A.3 OIDs, and update the package YAML.
  See `tier_warnings: model_and_firmware_variation_across_peplink_line`
  for the audit-honest framing of this drift.
- **WAN priority UI not reflecting in active WAN.** The
  `select.rc_net_peplink_wan_priority` UI tile may say "WAN1
  first" but `sensor.rc_net_peplink_active_wan` still shows
  "wan2". This is because the select updates the §5.1 mode-aware
  automation's `select.select_option` action — the actual WAN
  priority write to the Peplink is via
  `rest_command.peplink_set_wan_priority` (Path A) or the
  InControl 2 fleet-policy endpoint (Path B). If those are not
  wired, the UI state is local-only. Verify the rest_command is
  reachable from HA + the API token is valid.
- **Load-balance health shows 0 with one WAN disabled.** When the
  operator disables one WAN on the Peplink router directly
  (outside RoamCore), the load-balance health score drops to 0
  because there's nothing to balance. This is expected — but it
  will trigger the §6.4 alert because the system sees the
  load-balance health as "failed". Disable the §6.4 alert via the
  automation's `condition:` block if you regularly disable one
  WAN (e.g. for a long Starlink-only stretch on shore power).
- **Public IP not refreshing when WAN fails over.** The active
  WAN's public IP can lag behind a WAN swap because the
  §A.3 scan_interval is 30 s. If you need faster public-IP
  refreshes after a failover, drop the scan_interval to 10 s
  (cost: more frequent polling) or trigger a manual refresh via
  `button.rc_net_peplink_refresh_now` after a force-failover.
- **MIB tree private OID drift across firmware versions.** The
  Peplink MIB-II surface (system description, uptime, contact,
  name, location) is stable across the Balance / MAX / EP line —
  but the Peplink-private OIDs for WAN state / signal strength /
  WAN priority / load-balance health / public IP shift between
  firmware versions. This is the audit-honest reason this
  connection is tier-b rather than tier-a: without a real
  Peplink on the bench + per-firmware OID pinning, we cannot
  ship a one-tap config_flow that handles every firmware
  variant. The tier-a promotion outline at the bottom of this
  recipe describes exactly what needs to happen to fix this.

## §8 Privacy

- **Path A (SNMP) is fully local.** The MIB-II + Peplink-private
  OIDs are served on the LAN only (UDP/161). No telemetry rides
  outside the van's LAN.
- **Path B (InControl 2 REST API) rides through Peplink's cloud.**
  The `hass-incontrol2` HACS integration polls
  `https://api.ic.peplink.com/...` for fleet telemetry — this is
  the operator's existing relationship with Peplink (RoamCore adds
  no cloud dependency on top of the operator's existing InControl 2
  usage). The polling is HTTPS, API-key-authenticated, and
  in-band only (no extra side-channels). Operators who are
  uncomfortable with the cloud dependency should use Path A's
  local SNMP path instead.
- **No MAC / serial / device-id captured.** The contract
  intentionally publishes only the high-level multi-WAN telemetry
  (reachable, WAN state per WAN, active WAN, WAN failover count,
  load-balance health, uptime, public IP). The raw MAC addresses /
  serial numbers / device IDs stay on the Peplink router (and on
  the InControl 2 cloud, for Path B) and are not pulled into HA
  by the recipe.
- **Public IP** (`sensor.rc_net_peplink_public_ip`) is the
  active WAN's public IP as seen by the operator's carriers /
  Starlink. This is the same IP the operator already has via the
  Peplink Web UI; the recipe surfaces it for OpenClaw queries
  but does not publish it to any external service beyond what
  the underlying integration already does.
- **No vendor double-stamping.** No `peplink`, `pepwave`, `ic2`,
  `incontrol`, `mib`, `snmp`, `balance`, `max`, `ep`, `br`, or
  other vendor name appears in any `rc_net_peplink_*` entity,
  OpenClaw summary key, or dashboard tile beyond the subsystem
  prefix `rc_net_peplink_*`. The contract is intentionally
  vendor-neutral per `docs/reference/rc-entity-naming.md`.

## §9 Promoting to tier-a

When a real Peplink router lands on the bench (likely via
`testcontainers/snmp-sim` with a synthetic MIB-II + Peplink-private-
OID fixture, or a recorded SNMP capture from a Balance 20), this
connection is the candidate to promote to tier-a:

1. Add a native `config_flow.py` (or a thin wrapper around the
   upstream HA `snmp` integration if a community "Peplink" wrapper
   lands in core, OR a wrapper around the HACS `hass-incontrol2`
   integration for Path B) that walks the operator through
   enabling SNMP / InControl 2 + entering the credentials +
   selecting the firmware profile (per-firmware OID pinning so the
   MIB drift across the Peplink line is handled).
2. Add an integration test that asserts the `rc_net_peplink_*`
   contract entities appear after a synthetic SNMP-poll with a
   canned MIB-II + Peplink-private-OID response (Path A) AND after
   a synthetic InControl 2 fleet response (Path B).
3. Flip `install.config_flow` to `true` in the manifest.
4. Flip `tier_requirements` to include `working_config_flow` +
   `integration_test_passes` + `no_manual_yaml_required`.
5. Drop `tier_warnings` entries that mention
   `no_real_peplink_for_integration_test` /
   `recipe_depends_on_user_running_peplink` /
   `model_and_firmware_variation_across_peplink_line` /
   `snmp_or_incontrol2_path_choice`.
6. Flip `status` from `beta` to `shipped`.
7. Flip `wizard.one_tap` to `true`.

Until then, this stays at tier-b (beta, recipe) — the recipe is
sound, the contract is honest, and we don't claim one-tap coverage
we don't have.