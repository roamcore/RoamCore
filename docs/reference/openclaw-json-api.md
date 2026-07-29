# OpenClaw JSON API (MVP)

RoamCore exposes a small, stable JSON endpoint intended to be consumed by **OpenClaw**.

This is a thin HA-native wrapper around the existing **`rc_*` contract entities**.

## Why this matters (what it unlocks)

Dashboards are great for glanceable status — but they still force *you* to translate data into decisions.

The OpenClaw API turns RoamCore into something different: a **machine-readable contract** that a local agent can use to reason about your van.
Once connected to an OpenClaw-based agent (eventually something we can ship locally on RoamCore hardware like the VP2430), you can interact with your van in natural language:

- “Are we good to run the kettle right now?”
- “What’s draining the battery?”
- “How much solar did we get today?”
- “Are we level enough to sleep?”
- “Where did we stop last night and how long did we drive?”

Because the API is derived from stable `rc_*` entities, this stays consistent even as you change hardware or vendors behind the scenes.
This is the logical next step after consolidating everything into one clean dashboard: **a conversational interface for your system**.

## Endpoint

- **GET** `/api/roamcore/openclaw/summary`
- Returned `Content-Type`: `application/json`

## Convenience endpoint (agent setup)

- **GET** `/api/roamcore/openclaw/skill`

This returns a copy/paste-friendly payload that includes:
- the full URL to the summary endpoint
- whether auth is required
- the summary contract name/version

### Auth

RoamCore supports two modes:

1) **Require auth (recommended)** — OpenClaw must send a Home Assistant **Long‑Lived Access Token**:

```http
Authorization: Bearer <LLAT>
```

2) **No auth** — intended only for isolated/trusted LANs.

You can toggle this from the RoamCore dashboard:

- **Settings → OpenClaw API → Connect / Setup**

Or via Home Assistant integration options for **RoamCore**.

## Diagnostic endpoint (rc dump)

- **GET** `/api/roamcore/openclaw/rc_dump`

This returns a dump of all current Home Assistant entity states whose entity id contains `.rc_` (for example: `sensor.rc_power_battery_soc`, `binary_sensor.rc_level`, etc.).

Intended use:
- debugging installs
- quickly seeing “what rc_* entities exist right now?”
- giving an agent a broad snapshot of available contract entities

Notes:
- This is **not** meant to be a stable automation contract.
- Fields include `state` (string|null) plus best-effort parsed `num` (float|null) and `bool` (bool|null).

## Time series (compact, agent-requested)

Time series data is extremely useful for good “wow moment” insights, but raw Home Assistant history is too large.

RoamCore provides a **bounded**, **downsampled** time-series endpoint where the agent requests only the keys it needs.

### Catalog (discover what’s available)

- **GET** `/api/roamcore/openclaw/timeseries/catalog`

Returns a dictionary of supported time-series keys, each mapped to a Home Assistant `entity_id` and some metadata (unit/device_class when available).

### Time series fetch

- **GET** `/api/roamcore/openclaw/timeseries`

Query params:
- `keys` (required): comma-separated catalog keys
  - example: `keys=power.battery_soc_pct,power.load_power_w,power.solar_power_w`
- `window_sec` (optional): lookback window (default 21600 = 6h, max 172800 = 48h)
- `resolution_sec` (optional): bucket size (default 60, min 15, max 900)

Response:
- `series`: numeric series as `[[t_epoch, value|null], ...]` at the chosen resolution
- `events`: boolean series as transitions `[[t_epoch, 0|1], ...]`

Notes:
- This endpoint is designed for **agent-side analysis**.
- Keep requests small: fetch only the keys you need.

## Contract

Top-level fields:

```json
{
  "contract": { "name": "roamcore_openclaw_summary", "version": 1 },
  "generated_at": "2026-01-01T00:00:00+00:00",
  "power": { /* ... */ },
  "map": { /* ... */ },
  "mode": { /* ... */ },
  "level": { /* ... */ },
  "debug": { "entities": { /* ... */ } }
}
```

Notes:

- All numeric fields are `number | null`.
- All strings are `string | null`.
- Booleans are `boolean | null`.
- `null` means the source entity is missing or `unknown/unavailable`.

### `power`

Derived from RoamCore contract entities in `homeassistant/packages/roamcore_power.yaml`.

Fields:

- `battery_soc_pct`
- `solar_power_w`
- `load_power_w`
- `ac_in_power_w`
- `ac_out_power_w`
- `shore_connected`
- `inverter_status`

### `map`

Derived from:

- `homeassistant/packages/roamcore_location.yaml`
- `homeassistant/packages/roamcore_map.yaml`

Fields:

- `lat`
- `lon`
- `accuracy_m`
- `tile_url`
- `tile_url_online`
- `style_url`
- `offline_max_zoom`

### `level`

Derived from `homeassistant/packages/roamcore_system_level.yaml`.

Fields:

- `pitch_deg`
- `roll_deg`
- `is_level`
- `status`
- `hint`

### `mode`

Derived from `homeassistant/packages/roamcore_mode.yaml`.

Fields:

- `selected` (current value of `input_select.rc_mode`)
- `current` (value of `sensor.rc_mode_current`; currently mirrors `selected`)

## Implementation

Home Assistant custom integration:

- Preferred (HACS): `homeassistant/custom_components/roamcore/`
- Legacy (pre-HACS): `homeassistant/custom_components/roamcore_openclaw_api/`

The integration registers a `HomeAssistantView` and reads `rc_*` entity states from HA.

## Setup steps

### HACS path (recommended)

1. Install RoamCore via HACS (custom repository beta path).
2. Add the integration: Settings → Devices & services → Add integration → **RoamCore**.
3. Restart Home Assistant.
4. Confirm:

```sh
curl http://HOME_ASSISTANT:8123/api/roamcore/openclaw/summary
curl http://HOME_ASSISTANT:8123/api/roamcore/openclaw/skill
```

### Enable/disable (dashboard)

The RoamCore dashboard provides a simple toggle:

- **Settings → OpenClaw API**

When disabled, the OpenClaw endpoints return **HTTP 404**.

### Manual / legacy path

1. Copy `homeassistant/custom_components/roamcore_openclaw_api/` into your HA `/config/custom_components/`.
2. Ensure RoamCore packages are included (see `homeassistant/configuration_addon.yaml`).
3. Add this line to `configuration.yaml`:

```yaml
roamcore_openclaw_api:
```

4. Restart Home Assistant.
5. Confirm:

```sh
curl http://HOME_ASSISTANT:8123/api/roamcore/openclaw/summary
```

## Testing (MVP)

Recommended smoke tests:

1. Verify the endpoint returns HTTP 200 and valid JSON.
   - `homeassistant/tools/openclaw_api_smoketest.sh`
2. Force upstream entities to `unknown/unavailable` (or disable a source integration) and confirm the API returns `null` for those fields (no exceptions / stack traces).
3. Confirm the output fields and types remain stable while vendor entities change (the entire point of the `rc_*` contract layer).

## Automation apply endpoint (slice #24)

OpenClaw agents can drive a small, allowlisted slice of RoamCore state via a single apply endpoint. Everything goes through the existing `roamcore.action_execute` service so the global kill switch (`input_boolean.rc_agent_actions_enabled`) and audit log (`/config/.roamcore/agent_action_log.jsonl`) stay in one place.

### Endpoint

- **POST** `/api/roamcore/openclaw/automation/apply`
- Same auth rules as the other OpenClaw endpoints (Long-Lived Access Token when `requires_auth=true`).

### Request shape

Accepts either `{ "intent": { ... } }` or the bare intent itself. The intent body is the same shape the validate endpoint already accepts:

```json
{ "type": "set_helper", "params": { "entity_id": "input_text.rc_map_style_url", "value": "https://..." } }
```

### Supported intent types

| `type`         | Required params                                         | Notes                                                                                  |
| -------------- | ------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| `set_mode`     | `mode: string` (`auto` / `travel` / `camp` / `stealth` / `off`) | Sets `input_select.rc_mode`. Requires a `set_helper:input_select.rc_mode` allowlist entry. |
| `apply_mode`   | _(none)_                                                | Runs `script.rc_mode_apply` if allowlisted.                                            |
| `set_helper`   | `entity_id: string`, `value: string|number|boolean`      | `entity_id` must start with `input_` (text/number/select/boolean helpers only).        |
| `run_script`   | `entity_id: string`                                     | `entity_id` must start with `script.rc_`.                                              |

### Response shape

On success:

```json
{
  "ok": true,
  "contract": { "name": "roamcore_automation_intents", "version": 2 },
  "generated_at": "2026-07-29T...",
  "action_id": "set_helper:input_text.rc_map_style_url",
  "intent": { "type": "set_helper", "params": { ... } },
  "executor_result": { "ok": true }
}
```

On failure (validation, allowlist, kill switch, or executor error):

```json
{
  "ok": false,
  "error": "action_not_allowlisted",
  "contract": { ... },
  "generated_at": "..."
}
```

### Allowlist contract

The endpoint reads `/config/.roamcore/agent_allowlist.yaml` (the same file `roamcore.action_execute` reads). Each `actions[]` entry must have `kind` (`set_helper` or `run_script`) and `target.entity_id`. An intent is allowed only when some allowlisted action of the right kind targets the same `entity_id`. Example:

```yaml
version: 1
actions:
  - id: set_helper:input_select.rc_mode
    kind: set_helper
    target:
      entity_id: input_select.rc_mode
    constraints:
      enum: [auto, travel, camp, stealth, off]
  - id: run_script:script.rc_mode_apply
    kind: run_script
    target:
      entity_id: script.rc_mode_apply
```

### Kill switch

Global: `input_boolean.rc_agent_actions_enabled` must be **on**. The endpoint never executes an action when the kill switch is off, and the executor writes a denial record to the audit log either way.

### Audit log

Every apply call is written to `/config/.roamcore/agent_action_log.jsonl` by the existing `roamcore.action_execute` service. Each line contains `ts`, `action_id`, `reason="openclaw_automation_apply"`, `args`, and `result`. No secrets should ever appear in the args (the endpoint does not pass tokens through).

### Schema discovery

`GET /api/roamcore/openclaw/automation/intents` returns the current `SUPPORTED_INTENTS` map and the contract version. Treat it as the single source of truth for which intent types the running build accepts.
