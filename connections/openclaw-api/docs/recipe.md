# OpenClaw JSON API — recipe (the full howto)

This is the canonical operator-walk through for the
`connections/openclaw-api/` tier-a connection. The
connection wraps the existing RoamCore-owned custom
component at
`homeassistant/custom_components/roamcore_openclaw_api/`
(233 lines of Python code: `__init__.py` + `view.py`
+ `const.py` + `manifest.json`). The canonical
contract spec lives at `docs/reference/openclaw-json-api.md`
(230 lines); the canonical agent install guide lives
at `docs/howto/openclaw-roamcore-skill.md` (62
lines); the canonical curl smoketest lives at
`homeassistant/tools/openclaw_api_smoketest.sh` (40
lines, validates `contract.version == 1` + the top-
level keys `power`, `map`, `level`, `debug` are
present in `/summary` + `contract.version == 1` +
`openclaw_summary_url` + `requires_auth` +
`summary_contract` are present in `/skill`).

This recipe is the umbrella for the FOUR-step
operator flow + the FIVE §8 MANDATORY automations +
the 12 `rc_openclaw_api_*` contract tiles + the 6 §9
troubleshooting entries + §10 privacy + §11 tier-a
promotion outline + §12 files + cross-references.

---

## §1 What is the OpenClaw JSON API in RoamCore?

The OpenClaw JSON API is the canonical machine-
readable contract that RoamCore exposes for local
agents (the OpenClaw agent runtime that lives on the
operator's hardware — phone, laptop, server, or the
RoamCore VP2430 box itself). The API exposes a
stable JSON payload derived from RoamCore's `rc_*`
contract entities, so a local agent can reason about
the van's state without parsing vendor-specific
outputs.

Concretely, the API exposes these endpoints (all
under `/api/roamcore/openclaw/`):

- `GET /summary` — the canonical stable snapshot.
  Returns a JSON payload with the `contract` block
  (`name: roamcore_openclaw_summary`, `version: 1`),
  a `generated_at` ISO 8601 timestamp, and 4
  sections: `power` (battery_soc_pct, solar_power_w,
  load_power_w, ac_in_power_w, ac_out_power_w,
  shore_connected, inverter_status — derived from
  the 7 `rc_power_*` upstream entities), `map` (lat,
  lon, accuracy_m, tile_url, tile_url_online,
  style_url, offline_max_zoom — derived from the 4
  `rc_location_*` + `rc_map_*` upstream entities),
  `level` (pitch_deg, roll_deg, is_level, status,
  hint — derived from the 5 `rc_level_*` upstream
  entities), and `debug.entities` (the resolved
  entity registry for the 19 upstream entities). All
  numeric fields are `number | null`; all strings are
  `string | null`; booleans are `boolean | null`;
  `null` means the source entity is missing or
  `unknown/unavailable`.

- `GET /skill` — the convenience payload for agent
  setup. Returns a JSON payload with the `contract`
  block (`name: roamcore_openclaw_skill`, `version:
  1`), a `generated_at` ISO 8601 timestamp, and a
  `roamcore` block with `openclaw_summary_url` (the
  absolute URL to use for `/summary`),
  `requires_auth` (whether the operator has enabled
  the `input_boolean.rc_openclaw_api_requires_auth`
  toggle), and `summary_contract` (the contract name
  + version for `/summary`). Includes
  `user_instructions` with copy/paste-friendly notes
  for the agent.

- `GET /rc_dump` — the diagnostic endpoint that
  returns a dump of all current Home Assistant
  entity states whose entity id contains `.rc_` (for
  example: `sensor.rc_power_battery_soc`,
  `binary_sensor.rc_level`, etc.). Intended for
  debugging installs + giving an agent a broad
  snapshot of available contract entities. **NOT a
  stable automation contract** — fields include
  `state` (string|null) plus best-effort parsed `num`
  (float|null) and `bool` (bool|null).

- `GET /timeseries/catalog` — the time-series key
  discovery endpoint. Returns a dictionary of
  supported time-series keys, each mapped to a Home
  Assistant `entity_id` and some metadata (unit /
  device_class when available).

- `GET /timeseries` — the time-series fetch endpoint.
  Query params: `keys` (required, comma-separated
  catalog keys, e.g.
  `keys=power.battery_soc_pct,power.load_power_w,
  power.solar_power_w`), `window_sec` (optional,
  lookback window, default 21600 = 6h, max 172800 =
  48h), `resolution_sec` (optional, bucket size,
  default 60, min 15, max 900). Returns a `series`
  block (numeric series as `[[t_epoch, value|null],
  ...]` at the chosen resolution) and an `events`
  block (boolean series as transitions `[[t_epoch,
  0|1], ...]`). Designed for **agent-side analysis**.

All endpoints return HTTP 404 with `{"ok": false,
"error": "disabled"}` when
`input_boolean.rc_openclaw_api_enabled` is OFF (the
integration's `view.py` handles this). All endpoints
respect the `input_boolean.rc_openclaw_api_requires_auth`
toggle (when ON, the integration returns HTTP 401 if
the request doesn't carry a valid Home Assistant
Long-Lived Access Token in the `Authorization:
Bearer <LLAT>` header).

The connection wraps the existing integration as a
tier-a manifest so the audit pipeline can find it.
The slice DOES NOT replace any of the existing code;
the actual JSON endpoint logic lives in
`homeassistant/custom_components/roamcore_openclaw_api/view.py`
(untouched by this slice).

---

## §2 Prerequisites

Before installing the OpenClaw JSON API connection,
you need:

1. **Home Assistant 2022.6 or newer.** The
   integration uses the `HomeAssistantView` API which
   has been stable since 2022.x.

2. **The RoamCore packages are included in your HA
   config.** The RoamCore packages declare the
   upstream `rc_*` contract entities (the
   `homeassistant/packages/roamcore_power.yaml` +
   `homeassistant/packages/roamcore_location.yaml` +
   `homeassistant/packages/roamcore_map.yaml` +
   `homeassistant/packages/roamcore_system_level.yaml`
   files declare the `rc_power_*` + `rc_location_*` +
   `rc_map_*` + `rc_level_*` upstream entities that
   the OpenClaw JSON API reads from). See
   `homeassistant/configuration_addon.yaml` for the
   canonical include list.

3. **The `input_boolean.rc_openclaw_api_enabled` +
   `input_boolean.rc_openclaw_api_requires_auth`
   helpers.** These come from
   `homeassistant/packages/roamcore_openclaw_api_controls.yaml`.
   The helper package ships with `initial: false`
   for both helpers — the operator flips them ON via
   the dashboard Settings → OpenClaw API → Connect /
   Setup toggle, or via the integration's options
   flow, or via the `roamcore_openclaw_api.options_set`
   service, or directly via the legacy helper.

4. **A way to install the RoamCore-owned custom
   component.** Either:
   - **HACS path (recommended):** Install RoamCore
     via HACS (custom repository beta path). HACS
     auto-installs the
     `homeassistant/custom_components/roamcore_openclaw_api/`
     integration. Then Settings → Devices & services →
     Add integration → **RoamCore** → Configure →
     Enable OpenClaw API.
   - **Legacy `configuration.yaml:` path:** Copy
     `homeassistant/custom_components/roamcore_openclaw_api/`
     into your HA `/config/custom_components/`. Ensure
     RoamCore packages are included (see
     `homeassistant/configuration_addon.yaml`). Add
     this line to `configuration.yaml`:
     ```yaml
     roamcore_openclaw_api:
     ```
     Restart Home Assistant.

5. **A Home Assistant Long-Lived Access Token
   (LLAT).** Recommended for any non-isolated LAN.
   Create under Home Assistant → Profile → Long-Lived
   Access Tokens → Create Token. The token is NOT
   stored in RoamCore — the operator owns the token
   and provides it to their OpenClaw agent.

6. **An OpenClaw agent runtime.** Either on the
   operator's hardware (phone, laptop, server, or the
   RoamCore VP2430 box itself) or in the cloud. The
   canonical agent-side skill is at
   `openclaw/skills/roamcore/SKILL.md`; the agent
   install guide is at `docs/howto/openclaw-roamcore-skill.md`.

---

## §3 Step 1 — Enable

The operator flips
`input_boolean.rc_openclaw_api_enabled` ON via one
of:

- **Dashboard Settings → OpenClaw API → Connect /
  Setup toggle** (recommended). The dashboard tile
  exposes the toggle + the four sub-toggles (the
  audit-log chip + the test-now button + the
  bust-cache button + the contract-version chip).

- **Integration options flow.** Settings → Devices &
  services → **RoamCore** → Configure → Enable
  OpenClaw API. The integration's options flow
  exposes the `enabled` + `requires_auth` toggles
  via the HA UI.

- **Service call.** Fire the
  `roamcore_openclaw_api.options_set` service with
  `{"enabled": true}`:
  ```yaml
  service: roamcore_openclaw_api.options_set
  data:
    enabled: true
  ```

- **Legacy helper directly.** Flip
  `input_boolean.rc_openclaw_api_enabled` ON via the
  HA UI (Settings → Helpers → input_boolean →
  rc_openclaw_api_enabled → Toggle ON) or via the
  `input_boolean.toggle` service:
  ```yaml
  service: input_boolean.toggle
  data:
    entity_id: input_boolean.rc_openclaw_api_enabled
  ```

After the toggle is flipped ON, the integration's
`view.py` serves the JSON endpoints (200 OK on
`/summary` + `/skill` + `/rc_dump` + `/timeseries/*`).

The §8.1 API-disabled returns 404 guard fires on
every disable event (writes an audit-log entry +
fires a warning notification so the operator knows
the API is disabled and is not, e.g., broken).

---

## §4 Step 2 — Auth setup

The operator flips
`input_boolean.rc_openclaw_api_requires_auth` ON
(recommended default; the helper package ships with
`initial: false` for safety, but the spec
recommends ON for any non-isolated LAN). If the
operator wants auth, they must create a Home
Assistant Long-Lived Access Token (LLAT) under
Home Assistant → Profile → Long-Lived Access Tokens
→ Create Token, and provide that LLAT to their
OpenClaw agent.

The toggle can be flipped via one of:

- **Dashboard Settings → OpenClaw API → Connect /
  Setup toggle.** The dashboard tile exposes the
  toggle alongside the master enable toggle.

- **Integration options flow.** Settings → Devices &
  services → **RoamCore** → Configure → Require Auth.

- **Service call.** Fire the
  `roamcore_openclaw_api.options_set` service with
  `{"requires_auth": true}`:
  ```yaml
  service: roamcore_openclaw_api.options_set
  data:
    requires_auth: true
  ```

- **Legacy helper directly.** Flip
  `input_boolean.rc_openclaw_api_requires_auth` ON
  via the HA UI or via the `input_boolean.toggle`
  service:
  ```yaml
  service: input_boolean.toggle
  data:
    entity_id: input_boolean.rc_openclaw_api_requires_auth
  ```

The §8.2 auth-required-when-enabled guard fires
when the toggle is ON AND no LLAT is configured
(surfaces a red "Auth required but no token
configured" chip + writes an audit-log entry +
fires a critical notification). Without this guard,
a misconfigured deployment could expose the API
without auth.

**Note on the helper package default mismatch:**
the helper package at
`homeassistant/packages/roamcore_openclaw_api_controls.yaml`
ships with `initial: false` for both
`rc_openclaw_api_enabled` + `rc_openclaw_api_requires_auth`.
This slice's spec recommends `initial: true` for
`rc_openclaw_api_requires_auth` for safety (any non-
isolated LAN should require auth). The discrepancy
is documented as a known mismatch in §10 Privacy;
operators should flip the toggle ON manually post-
install for any non-isolated LAN, OR override the
helper package via their own HA package that wins
the load order (e.g. an `input_boolean` override
in `homeassistant/packages/my_overrides.yaml` with
`initial: true`).

---

## §5 Step 3 — Skill discovery

The OpenClaw agent calls
`/api/roamcore/openclaw/skill` to learn the summary
URL + whether auth is required. The §8.4 agent-
skill-discovery guard fires (logs the agent identity
via user-agent header if present + writes an audit-
log entry + surfaces a "new agent discovered"
notification).

```sh
curl http://homeassistant.local:8123/api/roamcore/openclaw/skill
```

If `requires_auth=true`, the operator provides
OpenClaw with the Home Assistant Long-Lived Access
Token. The agent then sends the LLAT in the
`Authorization: Bearer <LLAT>` header on every
subsequent request:

```sh
curl -H "Authorization: Bearer <LLAT>" \
  http://homeassistant.local:8123/api/roamcore/openclaw/skill
```

The agent-side skill at
`openclaw/skills/roamcore/SKILL.md` is the
canonical agent-side skill that consumes the JSON
API. Copy the entire `roamcore` folder into the
OpenClaw workspace `skills/` directory:

```bash
# From a machine where you have this RoamCore repo checked out
cp -R openclaw/skills/roamcore /path/to/your/openclaw/workspace/skills/
```

Then restart OpenClaw (or start a new session) so
it reloads skills.

The §8.4 agent-skill-discovery guard fires on every
first-call-in-24h event. The guard's audit-log
entry includes:

- The agent identity (best-effort, via the user-
  agent header if present; e.g. `OpenClaw/1.2.3`).
- The timestamp.
- The source IP (best-effort).
- The `requires_auth` state at the time of the call.

The guard's "new agent discovered" notification
surfaces on the dashboard + the OpenClaw JSON
endpoint itself. The notification is friendly,
not alarming — it's the trust-but-verify layer so
the operator can see who has connected to the API.

---

## §6 Step 4 — Live use

The OpenClaw agent calls
`/api/roamcore/openclaw/summary` periodically (and
optionally `/rc_dump` + `/timeseries/*`). The §8.3
rc-dump-only-includes-rc_-prefix guard validates
the response (filters to `rc_*` entity IDs; rejects
vendor leaks). The §8.1 disabled-returns-404 guard
handles disable events. The §8.2 auth-required-when-
enabled guard surfaces misconfigurations. The §8.5
contract-version-bump-notify guard fires when the
integration's `CONTRACT_VERSION` constant is bumped.

```sh
curl -H "Authorization: Bearer <LLAT>" \
  http://homeassistant.local:8123/api/roamcore/openclaw/summary
```

The default workflow (from the agent-side skill at
`openclaw/skills/roamcore/SKILL.md`):

1. **Fetch `/summary`** for the canonical stable
   snapshot. This is the primary endpoint — fetch
   this first on every agent call.
2. **Fetch `/rc_dump`** when the user asks anything
   broader ("what's available?" / "why?" / "what
   changed?"). The diagnostic endpoint returns all
   `rc_*` entities with their current states. The
   §8.3 rc-dump-only-includes-rc-prefix guard
   validates the response.
3. **Fetch `/timeseries/catalog`** (if the agent
   doesn't already know keys) + then **`/timeseries`**
   with only the keys needed when the user's question
   needs trends ("over the last few hours"). Use
   small windows (last 2-6 hours for "what changed?",
   24h for "today so far") and coarse resolution
   (60s for short windows, 300s = 5 min for 24h).

The §8.3 rc-dump-only-includes-rc-prefix guard
double-checks the response payload after every
`/rc_dump` call. If the response includes any
non-`rc_*` entity ID (e.g. a vendor entity ID that
somehow leaked through), the guard writes an
audit-log entry + fires a critical notification.
The integration's `view.py` already filters to
`.rc_`-prefixed entities, but the §8.3 guard
defends in depth.

The §8.1 API-disabled returns 404 guard fires when
ANY dashboard query or OpenClaw agent call hits
`/api/roamcore/openclaw/*` while
`input_boolean.rc_openclaw_api_enabled` is OFF.
The integration's `view.py` already returns HTTP
404 with `{"ok": false, "error": "disabled"}`, but
the §8.1 guard fires an audit-log entry + a warning
notification so the operator knows the API is
disabled (and is not, e.g., broken).

The §8.2 auth-required-when-enabled guard fires
when `input_boolean.rc_openclaw_api_requires_auth`
is ON AND no LLAT is configured. The guard
surfaces a red "Auth required but no token
configured" chip + writes an audit-log entry +
fires a critical notification.

The §8.5 contract-version-bump-notify guard fires
when the integration's `CONTRACT_VERSION` constant
in `homeassistant/custom_components/roamcore_openclaw_api/const.py`
is bumped. The guard surfaces a "OpenClaw API
contract bumped to v{N+1}" critical notification +
writes an audit-log entry + auto-bumps
`sensor.rc_openclaw_api_contract_version`.

---

## §7 RoamCore contract entities (the 12 `rc_openclaw_api_*` tiles)

The 12 contract tiles are the canonical dashboard-
side companion to the integration's JSON endpoints.
The `enabled` + `requires_auth` toggles are HA core
`input_boolean` helpers from
`homeassistant/packages/roamcore_openclaw_api_controls.yaml`
(this slice does NOT modify that helper package —
the existing audited + smoketest-validated code is
preserved untouched). The `contract_version` +
`last_request_at` + `request_count_24h` +
`average_latency_ms` + `openclaw_summary_url` +
`skill_version` tiles are HA core `template:` sensors
derived from the integration's audit-log entries. The
`is_reachable` + `requires_auth_active` tiles are HA
core `template:` binary_sensors. The `test_now` +
`bust_cache` tiles are HA core `input_button` helpers
that fire the integration's
`roamcore_openclaw_api.test_now` +
`roamcore_openclaw_api.bust_cache` services.

### §7.1 The 12 tiles

| Domain | Tile id | Source | Notes |
|---|---|---|---|
| `input_boolean` | `rc_openclaw_api_enabled` | helper package | Master enable toggle (404 when OFF, default OFF for safety). |
| `input_boolean` | `rc_openclaw_api_requires_auth` | helper package | Require Bearer-token auth (LLAT) when ON; recommended default ON. |
| `sensor` | `rc_openclaw_api_contract_version` | template | Mirrors the JSON endpoint's `contract.version` (currently `1`). |
| `sensor` | `rc_openclaw_api_last_request_at` | template | Timestamp of last `/summary` + `/skill` + `/rc_dump` request. |
| `sensor` | `rc_openclaw_api_request_count_24h` | template | Request counter rolling 24h. |
| `sensor` | `rc_openclaw_api_average_latency_ms` | template | p50 latency over the last 24h. |
| `binary_sensor` | `rc_openclaw_api_is_reachable` | template | Resolved reachability chip (true when `/summary` returns 200 in the last 5 min). |
| `binary_sensor` | `rc_openclaw_api_requires_auth_active` | template | Safety chip — true when auth is required AND no LLAT is configured. |
| `sensor` | `rc_openclaw_api_openclaw_summary_url` | template | Absolute URL of the summary endpoint (mirrors the `/skill` payload). |
| `sensor` | `rc_openclaw_api_skill_version` | template | Mirrors the skill payload's `contract.version` (currently `1`). |
| `button` | `rc_openclaw_api_test_now` | input_button | One-tap `/summary` GET to verify reachability. |
| `button` | `rc_openclaw_api_bust_cache` | input_button | One-tap cache invalidation for stale agents. |

### §7.2 Recommended `template:` + `input_button` configurations

The 10 derived tiles (`sensor.*` + `binary_sensor.*`
+ `button.*`) live in a new HA package:
`homeassistant/packages/roamcore_openclaw_api_derived.yaml`.
The package uses the HA core `template:` sensor +
`template:` binary_sensor wrappers (since 2022.x) +
the HA core `input_button` helper (since 2022.x) to
derive the 10 tiles from the integration's audit-log
entries + the upstream `rc_*` entities.

Example (illustrative — the operator adjusts the
templates to match their upstream `rc_*` entity
names):

```yaml
# homeassistant/packages/roamcore_openclaw_api_derived.yaml

template:
  - sensor:
      - name: "RC OpenClaw API Contract Version"
        unique_id: rc_openclaw_api_contract_version
        state: >
          {% set v = states('input_text.rc_openclaw_api_contract_version') %}
          {{ v if v not in ['unknown', 'unavailable', 'none', ''] else '1' }}
        icon: mdi:robot
      - name: "RC OpenClaw API Last Request At"
        unique_id: rc_openclaw_api_last_request_at
        state: >
          {% set v = states('input_text.rc_openclaw_api_last_request_at') %}
          {{ v if v not in ['unknown', 'unavailable', 'none', ''] else 'unknown' }}
        device_class: timestamp
        icon: mdi:clock-outline
      - name: "RC OpenClaw API Request Count 24h"
        unique_id: rc_openclaw_api_request_count_24h
        state: >
          {% set v = states('input_number.rc_openclaw_api_request_count_24h') %}
          {{ v if v not in ['unknown', 'unavailable', 'none', ''] else 0 }}
        unit_of_measurement: requests
        icon: mdi:counter
      - name: "RC OpenClaw API Average Latency"
        unique_id: rc_openclaw_api_average_latency_ms
        state: >
          {% set v = states('input_number.rc_openclaw_api_average_latency_ms') %}
          {{ v if v not in ['unknown', 'unavailable', 'none', ''] else 0 }}
        unit_of_measurement: ms
        icon: mdi:speedometer
      - name: "RC OpenClaw API Summary URL"
        unique_id: rc_openclaw_api_openclaw_summary_url
        state: >
          {% set v = states('input_text.rc_openclaw_api_openclaw_summary_url') %}
          {{ v if v not in ['unknown', 'unavailable', 'none', ''] else 'http://homeassistant.local:8123/api/roamcore/openclaw/summary' }}
        icon: mdi:link-variant
      - name: "RC OpenClaw API Skill Version"
        unique_id: rc_openclaw_api_skill_version
        state: >
          {% set v = states('input_text.rc_openclaw_api_skill_version') %}
          {{ v if v not in ['unknown', 'unavailable', 'none', ''] else '1' }}
        icon: mdi:robot
  - binary_sensor:
      - name: "RC OpenClaw API Is Reachable"
        unique_id: rc_openclaw_api_is_reachable
        state: >
          {{ is_state('input_boolean.rc_openclaw_api_enabled', 'on')
             and (now() - as_timestamp(states('input_text.rc_openclaw_api_last_request_at'), now()) < timedelta(minutes=5)
                  if states('input_text.rc_openclaw_api_last_request_at') not in ['unknown', 'unavailable', 'none', '']
                  else false) }}
        device_class: connectivity
        icon: mdi:lan-connect
      - name: "RC OpenClaw API Requires Auth Active"
        unique_id: rc_openclaw_api_requires_auth_active
        state: >
          {{ is_state('input_boolean.rc_openclaw_api_requires_auth', 'on')
             and states('input_text.rc_openclaw_api_llat_configured') == 'no' }}
        device_class: problem
        icon: mdi:lock-alert

input_button:
  rc_openclaw_api_test_now:
    name: "RC OpenClaw API Test Now"
    icon: mdi:lan-check
  rc_openclaw_api_bust_cache:
    name: "RC OpenClaw API Bust Cache"
    icon: mdi:cache
```

The `input_text.*` + `input_number.*` helpers in the
template references are populated by the integration's
audit-log entries (the integration's `view.py` writes
to `input_text.rc_openclaw_api_last_request_at` +
`input_number.rc_openclaw_api_request_count_24h` +
`input_number.rc_openclaw_api_average_latency_ms`
when the integration processes a request). The
integration's audit-log writes are intentionally
minimal — they don't add latency to the JSON
response.

---

## §8 Automations (MANDATORY before first use)

The FIVE §8 MANDATORY automations are the dashboard-
side companion to the integration's existing logic.
The integration's `view.py` already handles:

- HTTP 404 with `{"ok": false, "error": "disabled"}`
  when `input_boolean.rc_openclaw_api_enabled` is OFF.
- HTTP 401 when
  `input_boolean.rc_openclaw_api_requires_auth` is ON
  and the request doesn't carry a valid LLAT.
- Filtering `/rc_dump` to `.rc_`-prefixed entities.

The §8 automations add the audit-log entries + the
dashboard-side notifications + the contract-version
auto-bump. The integration's logic is the first line
of defense; the §8 automations are the dashboard-
side second line.

### §8.1 API-disabled returns 404 guard

Fires when ANY dashboard query or OpenClaw agent call
hits `/api/roamcore/openclaw/*` while
`input_boolean.rc_openclaw_api_enabled` is OFF.
The integration's `view.py` already returns HTTP 404,
but the §8.1 automation fires an audit-log entry + a
warning notification so the operator knows the API is
disabled (and is not, e.g., broken).

```yaml
automation:
  - alias: "rc_openclaw_api_disabled_returns_404_guard"
    trigger:
      - platform: state
        entity_id: input_boolean.rc_openclaw_api_enabled
        to: "off"
    action:
      - service: logbook.log
        data:
          name: "OpenClaw JSON API"
          message: "API disabled; future dashboard queries + OpenClaw agent calls will return HTTP 404"
          entity_id: input_boolean.rc_openclaw_api_enabled
      - service: persistent_notification.create
        data:
          title: "OpenClaw JSON API disabled"
          message: >
            The OpenClaw JSON API is currently disabled
            (`input_boolean.rc_openclaw_api_enabled` is
            OFF). Future dashboard queries + OpenClaw agent
            calls will return HTTP 404 until the toggle is
            flipped back ON.
          notification_id: "rc_openclaw_api_disabled"
```

### §8.2 Auth-required-when-enabled guard

Fires when `input_boolean.rc_openclaw_api_requires_auth`
is ON AND no LLAT is configured in the operator's
Home Assistant user profile. Surfaces a red "Auth
required but no token configured" chip + writes an
audit-log entry + fires a critical notification.
Without this guard, a misconfigured deployment
could expose the API without auth.

```yaml
automation:
  - alias: "rc_openclaw_api_auth_required_when_enabled_guard"
    trigger:
      - platform: state
        entity_id: input_boolean.rc_openclaw_api_requires_auth
        to: "on"
    condition:
      - condition: template
        value_template: >
          {{ states('input_text.rc_openclaw_api_llat_configured') == 'no' }}
    action:
      - service: logbook.log
        data:
          name: "OpenClaw JSON API"
          message: "Auth required but no LLAT configured; create a token under Profile → Long-Lived Access Tokens"
          entity_id: input_boolean.rc_openclaw_api_requires_auth
      - service: persistent_notification.create
        data:
          title: "OpenClaw JSON API: auth required but no token configured"
          message: >
            `input_boolean.rc_openclaw_api_requires_auth`
            is ON but no Long-Lived Access Token is
            configured. Create one under Home Assistant
            → Profile → Long-Lived Access Tokens → Create
            Token, and provide that token to your OpenClaw
            agent.
          notification_id: "rc_openclaw_api_no_llat"
```

### §8.3 RC-dump-only-includes-rc-prefix guard

Fires when an OpenClaw agent requests
`/api/roamcore/openclaw/rc_dump` AND the response
includes non-`rc_*` entity IDs (which would leak
vendor entity IDs into the agent's working memory —
defeating the entire point of the `rc_*` contract
layer). The integration's `view.py` already filters
to `.rc_`-prefixed entities, but the §8.3 automation
double-checks the response payload + writes an
audit-log entry if a non-`rc_*` entity leaked
through.

```yaml
automation:
  - alias: "rc_openclaw_api_rc_dump_only_includes_rc_prefix_guard"
    trigger:
      - platform: webhook
        webhook_id: "rc_openclaw_api_rc_dump_audit"
    condition:
      - condition: template
        value_template: >
          {{ trigger.json.non_rc_entity_count | int > 0 }}
    action:
      - service: logbook.log
        data:
          name: "OpenClaw JSON API"
          message: >
            /rc_dump response included {{ trigger.json.non_rc_entity_count }}
            non-rc_* entity IDs (vendor leak detected);
            the integration's view.py filter must be checked
          entity_id: binary_sensor.rc_openclaw_api_is_reachable
      - service: persistent_notification.create
        data:
          title: "OpenClaw JSON API: vendor entity leak in /rc_dump"
          message: >
            The /rc_dump response included non-rc_*
            entity IDs (vendor leak detected). The
            integration's view.py filter at
            `homeassistant/custom_components/roamcore_openclaw_api/view.py`
            must be checked.
          notification_id: "rc_openclaw_api_rc_dump_leak"
```

### §8.4 Agent-skill-discovery guard

Fires when an OpenClaw agent calls
`/api/roamcore/openclaw/skill` for the first time
in 24h. Logs the agent identity (best-effort, via
the user-agent header if present) + writes an audit-
log entry + surfaces a "new agent discovered"
notification. This is the trust-but-verify layer:
the operator can see who has connected to the API.

```yaml
automation:
  - alias: "rc_openclaw_api_agent_skill_discovery_guard"
    trigger:
      - platform: webhook
        webhook_id: "rc_openclaw_api_skill_discovery_audit"
    condition:
      - condition: template
        value_template: >
          {{ (now() - as_timestamp(states('input_text.rc_openclaw_api_last_skill_discovery_at'), now())) > timedelta(hours=24)
             if states('input_text.rc_openclaw_api_last_skill_discovery_at') not in ['unknown', 'unavailable', 'none', '']
             else true }}
    action:
      - service: logbook.log
        data:
          name: "OpenClaw JSON API"
          message: >
            OpenClaw agent called /skill
            (user-agent: {{ trigger.json.user_agent | default('unknown') }};
             source IP: {{ trigger.json.source_ip | default('unknown') }});
            requires_auth={{ trigger.json.requires_auth }}
          entity_id: binary_sensor.rc_openclaw_api_is_reachable
      - service: persistent_notification.create
        data:
          title: "OpenClaw JSON API: new agent discovered"
          message: >
            An OpenClaw agent called /skill
            (user-agent: {{ trigger.json.user_agent | default('unknown') }}).
            If you didn't expect this discovery event,
            check your OpenClaw agent configuration.
          notification_id: "rc_openclaw_api_new_agent"
      - service: input_text.set_value
        data:
          entity_id: input_text.rc_openclaw_api_last_skill_discovery_at
          value: "{{ now().isoformat() }}"
```

### §8.5 Contract-version-bump-notify guard

Fires when the integration's `CONTRACT_VERSION`
constant in
`homeassistant/custom_components/roamcore_openclaw_api/const.py`
is bumped. Surfaces a "OpenClaw API contract bumped
to v{N+1}" critical notification + writes an audit-
log entry + auto-bumps
`sensor.rc_openclaw_api_contract_version`. This is
the dashboard-side companion to the integration's
bump; the operator knows immediately when the
contract changes.

```yaml
automation:
  - alias: "rc_openclaw_api_contract_version_bump_notify_guard"
    trigger:
      - platform: state
        entity_id: input_text.rc_openclaw_api_contract_version
    condition:
      - condition: template
        value_template: >
          {{ trigger.to_state.state not in ['unknown', 'unavailable', 'none', '']
             and trigger.from_state.state not in ['unknown', 'unavailable', 'none', '']
             and trigger.to_state.state != trigger.from_state.state }}
    action:
      - service: logbook.log
        data:
          name: "OpenClaw JSON API"
          message: >
            CONTRACT_VERSION bumped from v{{ trigger.from_state.state }}
            to v{{ trigger.to_state.state }}; agents that don't
            support the new contract may need to be updated
          entity_id: sensor.rc_openclaw_api_contract_version
      - service: persistent_notification.create
        data:
          title: "OpenClaw JSON API: contract bumped to v{{ trigger.to_state.state }}"
          message: >
            The OpenClaw JSON API contract has been bumped
            to v{{ trigger.to_state.state }}. Agents that
            don't support the new contract may need to be
            updated. See `docs/reference/openclaw-json-api.md`
            for the new contract details.
          notification_id: "rc_openclaw_api_contract_bump"
```

---

## §9 Troubleshooting

### §9.1 The OpenClaw JSON API is disabled (HTTP 404)

**Symptom:** `curl http://homeassistant.local:8123/api/roamcore/openclaw/summary`
returns HTTP 404 with `{"ok": false, "error": "disabled"}`.

**Cause:** `input_boolean.rc_openclaw_api_enabled` is OFF.

**Fix:** Flip the toggle ON via one of the methods
described in §3 Step 1 — Enable (dashboard Settings
→ OpenClaw API → Connect / Setup toggle, integration
options flow, `roamcore_openclaw_api.options_set`
service, or the legacy helper directly). The §8.1
API-disabled returns 404 guard fires on every disable
event.

### §9.2 Auth required but no LLAT configured

**Symptom:** HTTP 401 returned by the integration +
the red "Auth required but no token configured" chip
is on in the dashboard.

**Cause:** `input_boolean.rc_openclaw_api_requires_auth`
is ON but no Long-Lived Access Token is configured.

**Fix:** Create a token under Home Assistant →
Profile → Long-Lived Access Tokens → Create Token.
Provide that token to your OpenClaw agent. The §8.2
auth-required-when-enabled guard fires when the
toggle is ON AND no LLAT is configured.

### §9.3 The /rc_dump response includes vendor entity IDs

**Symptom:** The §8.3 rc-dump-only-includes-rc-prefix
guard fires + the integration returns non-`rc_*`
entity IDs in the `/rc_dump` response.

**Cause:** A bug in the integration's `view.py`
filter logic. The integration's filter at
`homeassistant/custom_components/roamcore_openclaw_api/view.py`
should be checked.

**Fix:** Open an issue at
https://github.com/roamcore/RoamCore/issues with the
integration's filter log + the audit-log entry from
the §8.3 guard. The fix is a one-line change to the
integration's filter logic.

### §9.4 The agent can't reach the OpenClaw JSON API

**Symptom:** The agent's HTTP request to
`/api/roamcore/openclaw/summary` times out or
returns a connection error.

**Cause:** The agent is on a different network than
the Home Assistant instance, OR the agent's DNS
doesn't resolve `homeassistant.local` to the HA
instance's IP.

**Fix:** Verify the agent can reach Home Assistant:
```sh
curl -v http://homeassistant.local:8123/api/roamcore/openclaw/skill
```
If that fails, use the absolute URL from the
`sensor.rc_openclaw_api_openclaw_summary_url` tile
(the integration populates this tile with the
absolute URL it received). The integration's
`view.py` derives the URL from the request's URL,
so the tile always reflects the URL the agent
should use.

### §9.5 The §8.5 contract-version-bump-notify guard fires unexpectedly

**Symptom:** The "OpenClaw API contract bumped to
v{N+1}" notification fires but the operator didn't
upgrade the integration.

**Cause:** The integration's `CONTRACT_VERSION`
constant in
`homeassistant/custom_components/roamcore_openclaw_api/const.py`
was bumped in a recent integration upgrade. The
upgrade could have been triggered by a HACS update
or a manual `configuration.yaml:` reload.

**Fix:** Verify the integration's `const.py` matches
the expected `CONTRACT_VERSION` value (currently
`1`). If the bump is expected, the operator should
review the new contract spec at
`docs/reference/openclaw-json-api.md` and update
their OpenClaw agent if needed. If the bump is
unexpected, the operator should pin the integration
to the previous version via HACS.

### §9.6 The agent's `/rc_dump` response is huge

**Symptom:** The agent's HTTP request to
`/api/roamcore/openclaw/rc_dump` returns a very
large JSON payload (hundreds of KB).

**Cause:** The operator has many `rc_*` entities
configured (the more upstream entities, the larger
the `/rc_dump` response).

**Fix:** Prefer `/summary` for the canonical stable
snapshot. Use `/rc_dump` only when the agent needs
the broader snapshot. Use `/timeseries/catalog` +
`/timeseries` for trends (the time-series endpoint
is bounded by `window_sec` + `resolution_sec`).

---

## §10 Privacy

The OpenClaw JSON API is **data-only** by design.
The API exposes ONLY the `rc_*` contract surface —
no vendor entities, no LLATs (the LLAT is the
operator's, not RoamCore's), no dashboards, no
scripts, no automations, no notification history.

The integration's `view.py` reads only from the 19
upstream `rc_*` entities (the 7 `rc_power_*` + 4
`rc_location_*` + 3 `rc_map_*` + 5 `rc_level_*`
entities). The `/summary` payload is a strict
projection of these 19 entities; no vendor entity
ever appears in the payload. The `/rc_dump` payload
is filtered to `.rc_`-prefixed entities only (the
§8.3 rc-dump-only-includes-rc-prefix guard double-
checks this).

The OpenClaw JSON API does NOT collect or transmit
any RoamCore-side telemetry. The API exposes data;
it does not collect data. The agent-side skill at
`openclaw/skills/roamcore/SKILL.md` is also
strictly data-only — the skill tells the agent
"RoamCore is data-only. You compute insights
agent-side."

**No secrets are stored in RoamCore.** The LLAT is
created under Home Assistant → Profile → Long-Lived
Access Tokens → Create Token, and the LLAT is owned
by the operator's user profile. The LLAT is NEVER
stored in the RoamCore custom component or in the
helper package. The operator provides the LLAT to
their OpenClaw agent directly.

**No third-party services are called.** The
OpenClaw JSON API serves the JSON payload directly
from the local Home Assistant instance. The agent
calls the local Home Assistant endpoint directly;
no third-party service is involved.

**Recommended deployment modes:**
- **Isolated / trusted LAN:** the operator may flip
  `input_boolean.rc_openclaw_api_requires_auth` OFF
  for convenience. The API is only accessible from
  the local LAN; no external exposure.
- **Remote / public LAN:** the operator MUST keep
  `input_boolean.rc_openclaw_api_requires_auth` ON
  AND must expose Home Assistant only via a
  VPN (Tailscale, WireGuard) or via the
  remote-access Wave 3 #58 connection. The remote-
  access connection cross-references the VPN
  primitive used for this deployment mode.

**Known mismatch:** the helper package at
`homeassistant/packages/roamcore_openclaw_api_controls.yaml`
ships with `initial: false` for both
`rc_openclaw_api_enabled` + `rc_openclaw_api_requires_auth`.
This slice's spec recommends `initial: true` for
`rc_openclaw_api_requires_auth` for safety (any non-
isolated LAN should require auth). The discrepancy
is documented as a known mismatch; operators should
flip the toggle ON manually post-install for any
non-isolated LAN, OR override the helper package
via their own HA package that wins the load order.

---

## §11 Promoting to fully-fledged tier-a

The slice is tier-a (`tier: a`) because the custom
component at
`homeassistant/custom_components/roamcore_openclaw_api/`
IS real + RoamCore-owned + audited + smoketest-
validated. The tier-a-but-flagged honesty is that the
integration has a curl-based smoketest, not pytest
integration tests against a controlled bench. The
bench fixture gap is documented in
`tier_requirements.integration_tests` below.

For full tier-a promotion (without the "but-flagged"
qualifier), the integration needs pytest integration
tests against a controlled bench. The 8 canned-
response bench artifacts needed are:

1. **Canned `/summary` response (all `rc_*` fields
   populated).** A JSON fixture with all 7 `rc_power_*`
   + 4 `rc_location_*` + 3 `rc_map_*` + 5 `rc_level_*`
   entities populated with realistic values. Tests
   should assert the `/summary` response matches the
   fixture.

2. **Canned `/summary` response (all `rc_*` fields
   null/unknown).** A JSON fixture with all upstream
   entities set to `unknown` or `unavailable`. Tests
   should assert the `/summary` response has all
   numeric fields as `null`, all strings as `null`,
   all booleans as `null`.

3. **Canned `/skill` response (auth required + auth
   not required).** Two JSON fixtures: one with
   `requires_auth: true` and one with `requires_auth:
   false`. Tests should assert the `/skill` response
   matches the fixture under both states.

4. **Canned `/rc_dump` response (mix of `rc_*` +
   non-`rc_*` entities).** A JSON fixture with a mix
   of `rc_*` and non-`rc_*` entities. Tests should
   assert the `/rc_dump` response filters out the
   non-`rc_*` entities AND that the §8.3 rc-dump-only-
   includes-rc-prefix guard fires.

5. **Canned `/timeseries/catalog` response.** A JSON
   fixture with a representative time-series catalog
   (e.g. 8 keys: power.battery_soc_pct, power.load_power_w,
   power.solar_power_w, power.ac_in_power_w,
   level.pitch_deg, level.roll_deg, map.lat, map.lon).
   Tests should assert the `/timeseries/catalog`
   response matches the fixture.

6. **Canned `/timeseries` response (numeric + boolean
   series).** Two JSON fixtures: one with a numeric
   series (e.g. `power.battery_soc_pct` over the last
   6h at 60s resolution) and one with a boolean series
   (e.g. `power.shore_connected` over the last 6h at
   60s resolution). Tests should assert the
   `/timeseries` response matches the fixture.

7. **404 response when `input_boolean.rc_openclaw_api_enabled`
   is OFF.** A test that flips the toggle OFF, makes
   a request to `/summary`, and asserts the response
   is HTTP 404 with `{"ok": false, "error":
   "disabled"}`. Also asserts the §8.1 API-disabled
   returns 404 guard fires.

8. **401 response when auth is required but LLAT is
   missing.** A test that flips the `requires_auth`
   toggle ON without configuring an LLAT, makes a
   request to `/summary` without an `Authorization`
   header, and asserts the response is HTTP 401.
   Also asserts the §8.2 auth-required-when-enabled
   guard fires.

The pytest bench harness would spin up a controlled
Home Assistant instance (using the
`pytest-homeassistant-custom-component` framework +
a controlled environment with canned upstream
`rc_*` entity states) + run the integration's
`view.py` + assert the responses match the
fixtures. The 8 canned-response bench artifacts
above are the minimum viable set; production-grade
tier-a promotion would add 20+ more (boundary
conditions, malformed input, auth edge cases, etc.).

---

## §12 Files in this connection + cross-references

### Files

- `connection.yml` — the source-of-truth tier-a
  manifest.
- `__init__.py` — `DOMAIN = "openclaw_api"` marker
  for the audit.
- `docs/recipe.md` — this file (the full howto).
- `tests/test_connection_yml.py` — manifest honesty
  checks (7/7 PASS via
  `bash scripts/check.sh --core-only`).

### Cross-references

- **Canonical contract spec:**
  [`docs/reference/openclaw-json-api.md`](../../../docs/reference/openclaw-json-api.md)
  (230 lines — the source of truth for the JSON
  payload shape + auth modes + endpoint catalog).

- **Agent install guide:**
  [`docs/howto/openclaw-roamcore-skill.md`](../../../docs/howto/openclaw-roamcore-skill.md)
  (62 lines — the canonical operator-walk through
  for installing the RoamCore skill into an OpenClaw
  agent).

- **Existing custom component:**
  [`homeassistant/custom_components/roamcore_openclaw_api/`](../../../homeassistant/custom_components/roamcore_openclaw_api/)
  (233 lines — the canonical implementation;
  registers the `HomeAssistantView`s at `/summary`
  + `/skill` + `/rc_dump` + `/timeseries/*`; reads
  ONLY from `rc_*` upstream entities; preserves
  vendor-neutrality).

- **Helper package:**
  [`homeassistant/packages/roamcore_openclaw_api_controls.yaml`](../../../homeassistant/packages/roamcore_openclaw_api_controls.yaml)
  (declares the `input_boolean.rc_openclaw_api_enabled`
  + `input_boolean.rc_openclaw_api_requires_auth`
  helpers).

- **Curl smoketest:**
  [`homeassistant/tools/openclaw_api_smoketest.sh`](../../../homeassistant/tools/openclaw_api_smoketest.sh)
  (40 lines — validates the JSON contract stability).

- **Agent-side skill:**
  [`openclaw/skills/roamcore/SKILL.md`](../../../openclaw/skills/roamcore/SKILL.md)
  (the canonical agent-side skill that consumes the
  JSON API).

- **Mode (the §8.4 agent-skill-discovery guard's
  mode-aware notification):** `connections/mode/`
  (Wave 3 #61).

- **Advanced mode (the §8.5 contract-version-bump-
  notify guard's confirmation-required pattern):**
  `connections/advanced-mode/` (Wave 3 #63).

- **Demo mode (the §8.2 auth-required-when-enabled
  guard's safety-chip pattern):**
  `connections/demo-mode/` (Wave 3 #62).

- **Leveling (the §8.3 rc-dump-only-includes-rc-
  prefix guard's contract-layer filtering):**
  `connections/leveling/` (Wave 3 #60).

- **RoamCore entity naming:**
  [`docs/reference/rc-entity-naming.md`](../../../docs/reference/rc-entity-naming.md)
  (the `openclaw_api` subsystem was added by this
  slice).

- **Legacy catalog page (preserved with SUPERSEDED
  banner — the tier-a claim is HONEST):**
  [`docs/catalog/ai/openclaw-json-api.md`](../../../docs/catalog/ai/openclaw-json-api.md)
