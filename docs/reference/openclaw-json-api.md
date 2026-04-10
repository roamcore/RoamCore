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
