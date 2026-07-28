# Time entities (clock + timezone contract)

**Support tier:** B (Home Assistant supported)

## What this is
A curated list of time + timezone primitives that automations can rely on. RoamCore exposes a small contract surface (`rc_time_*`) so dashboards and automations stay stable even when the underlying timezone source changes.

## Why it’s useful in a van
- Travel across timezones without breaking "local time" automations
- Coordinate wake-up, quiet-hours, and bedtime routines to *local* time
- Provide agents with a single deterministic clock snapshot

## Extra hardware required
- None

## Install / best next step
- Set the RoamCore helper to either an explicit IANA timezone (overriding HA's config) or leave it blank to follow HA.
- RoamCore helper: `input_text.rc_time_zone_override`
- HA package: `homeassistant/packages/roamcore_weather_time.yaml`

## Contract entities

These are the **RoamCore contract entities** the rest of the system reads from. They are stable even when you change the underlying timezone source.

| Entity | What it is | Source |
|---|---|---|
| `sensor.rc_time_local` | Local time formatted as `YYYY-MM-DD HH:MM` (legacy MVP) | `now()` |
| `sensor.rc_time_zone` | Resolved IANA timezone name (legacy MVP) | `input_text.rc_time_zone_override` → `UTC` |
| `sensor.rc_time_now_iso` | Local time as ISO-8601 (device_class: `timestamp`) | `now().isoformat()` |
| `sensor.rc_time_utc_offset_minutes` | UTC offset in minutes (positive = ahead of UTC) | `now().utcoffset()` |
| `binary_sensor.rc_time_is_dst` | `on` / `off` / `unknown` — is local time in DST right now? | `now().dst()` |
| `sensor.rc_time_source` | Canonical source enum: `override` \| `ha_config` \| `browser` \| `unknown` | `input_text.rc_time_zone_override` → `ha_config` |
| `sensor.rc_time_status` | Canonical sync status enum: `ok` \| `no_override` \| `invalid_override` \| `ha_unconfigured` \| `unknown` | derived from the chain above |

**Every entity returns `unavailable` (sensors) or `unknown` (binary_sensors) when sources are missing** — the dashboard and automations never crash. Each entity also exposes a `reason` attribute so the UI can show the user a friendly explanation.

### Canonical enums (must remain stable)

```
RC_TIMEZONE_SOURCES = ("override", "ha_config", "browser", "unknown")
RC_TIME_STATUSES    = ("ok", "no_override", "invalid_override", "ha_unconfigured", "unknown")
```

## Configuration (user-facing)

In **Settings → Devices & Services → Helpers → RoamCore** (or directly in `helpers.yaml`):

- **`input_text.rc_time_zone_override`** *(optional)* — manual timezone override (IANA name). Leave blank to use HA's configured timezone (`config.time_zone`). Common values: `Europe/London`, `America/New_York`, `Asia/Tokyo`.

The fallback chain is:

1. `input_text.rc_time_zone_override` (if non-empty + valid IANA name)
2. HA's configured timezone (`now().astimezone().tzinfo`)
3. `unavailable` / `unknown` (never crashes)

## OpenClaw JSON API

RoamCore exposes a read-only time endpoint at
`GET /api/roamcore/openclaw/time`. It returns a deterministic JSON
shape derived from the contract entities:

```json
{
  "contract": { "name": "roamcore_openclaw_time", "version": 1 },
  "time": {
    "now_iso": "2026-07-28T23:00:00+00:00",
    "timezone": "Europe/London",
    "source": "ha_config",
    "utc_offset_minutes": 60,
    "is_dst": true,
    "status": "ok",
    "reason": "ok"
  }
}
```

All fields are nullable. `status` is one of the canonical enum values; `source` is one of the canonical source enum values; `reason` mirrors `status` so older clients can keep working. Auth follows the same rules as the other OpenClaw endpoints (toggle via the RoamCore integration options or `input_boolean.rc_openclaw_api_enabled`).

## Implementation

- Pure-Python helpers (testable without a live HA):
  `homeassistant/roamcore_time_primitives.py`
- View: `homeassistant/custom_components/roamcore/openclaw_view.py`
  → `OpenClawTimeView`

## Links
- Naming convention: `docs/reference/rc-entity-naming.md`
- Lovelace card: `dashboard/lovelace/time-card.yaml`
- Package: `homeassistant/packages/roamcore_weather_time.yaml`
- Tests: `homeassistant/tools/roamcore_time/tests/`
