# OpenClaw JSON API (MVP)

RoamCore exposes a small, stable JSON endpoint intended to be consumed by **OpenClaw**.

This is a thin HA-native wrapper around the existing **`rc_*` contract entities**.

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

Current MVP implementation sets `requires_auth = false` to keep OpenClaw simple on an isolated LAN.

If you expose Home Assistant beyond a trusted network, you should:

1. Put HA behind a VPN / reverse proxy with auth, and/or
2. Change the view to `requires_auth = True` and use a Long-Lived Access Token.

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
2. Force upstream entities to `unknown/unavailable` (or disable a source integration) and confirm the API returns `null` for those fields (no exceptions / stack traces).
3. Confirm the output fields and types remain stable while vendor entities change (the entire point of the `rc_*` contract layer).
