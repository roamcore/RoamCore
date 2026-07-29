# Weather entities (forecast + alerts)

**Support tier:** B (Home Assistant supported)

## What this is
A curated list of weather integrations that pair well with van life (forecast, alerts, sunrise/sunset), plus guidance on wiring them into the RoamCore dashboard.

## Why it’s useful in a van
- Avoid unsafe conditions (wind, snow, heat)
- Plan travel days and energy usage

## Extra hardware required
- None (optional outdoor sensors improve accuracy)

## Install / best next step
- Start with Home Assistant’s weather integration of choice, then set the RoamCore helper to point at it.
- RoamCore helper: `input_text.rc_weather_entity_id`
- HA package: `homeassistant/packages/roamcore_weather_time.yaml`

## Contract entities

These are the **RoamCore contract entities** the rest of the system reads
from. They are stable even when you change the underlying weather
integration (Met.no → OpenWeatherMap → NWS).

| Entity | What it is | Source |
|---|---|---|
| `sensor.rc_weather_outdoor_temperature` | Current outdoor temperature (°C) | `input_text.rc_weather_outdoor_temperature_entity` (override) → weather entity attribute → `unavailable` |
| `sensor.rc_weather_outdoor_humidity` | Current outdoor humidity (%) | `input_text.rc_weather_outdoor_humidity_entity` (override) → weather entity attribute → `unavailable` |
| `sensor.rc_weather_forecast_condition` | Forecast condition, mapped to canonical enum (`clear` / `cloudy` / `rain` / `snow` / `storm` / `fog` / `unknown`) | Weather entity state, normalized |
| `sensor.rc_weather_forecast_high_temp_24h` | 24h forecast high (°C) | Derived from `weather.<id>.forecast` |
| `sensor.rc_weather_forecast_low_temp_24h` | 24h forecast low (°C) | Derived from `weather.<id>.forecast` |
| `binary_sensor.rc_weather_precipitation_expected_2h` | Rain expected within next 2h | Derived from `weather.<id>.forecast` |
| `sensor.rc_weather_sun_next_event` | Next sunrise / sunset (ISO timestamp + `kind` attribute) | `sun.sun` |

**Every entity returns `unavailable` (sensors) or `unknown` (binary
sensors) when no weather integration is configured** — the dashboard and
automations never crash. Each entity also exposes a `reason` attribute
(`no_weather_integration`, `weather_integration_unavailable`,
`no_forecast_data`, or `ok`) so the UI can show the user a friendly
explanation.

## Configuration (user-facing)

In **Settings → Devices & Services → Helpers → RoamCore** (or directly
in `helpers.yaml`):

- **`input_text.rc_weather_entity_id`** — weather entity id, default `weather.home`
  (Met.no via HA's built-in Weather integration). Set this if you use a
  different provider.
- **`input_text.rc_weather_outdoor_temperature_entity`** *(optional)* —
  override the outdoor-temperature source. Common values:
  `sensor.openweathermap_temperature`, `sensor.met_no_temperature`,
  `sensor.outdoor_temperature` (your own outdoor sensor). Leave blank to
  read the temperature attribute from the weather integration.
- **`input_text.rc_weather_outdoor_humidity_entity`** *(optional)* —
  same pattern for humidity.

## OpenClaw JSON API

RoamCore exposes a read-only weather endpoint at
`GET /api/roamcore/openclaw/weather`. It returns a deterministic JSON
shape derived from the contract entities:

```json
{
  "contract": { "name": "roamcore_openclaw_weather", "version": 1 },
  "weather": {
    "outdoor_temperature_c": 12.4,
    "outdoor_humidity_pct": 75.0,
    "forecast_condition": "cloudy",
    "forecast_high_temp_24h_c": 18.0,
    "forecast_low_temp_24h_c": 7.0,
    "precipitation_expected_2h": false,
    "sun_next_event": "2026-01-02T16:00:00+00:00",
    "weather_entity_id": "weather.home",
    "reason": "ok"
  }
}
```

All fields are nullable. `reason` is `ok` when a weather integration is
configured and reporting, or `no_weather_integration` /
`weather_integration_unavailable` otherwise. Auth follows the same rules
as the other OpenClaw endpoints (toggle via the RoamCore integration
options or `input_boolean.rc_openclaw_api_enabled`).

## Links
- Naming convention: `docs/reference/rc-entity-naming.md`
- Lovelace card: `dashboard/lovelace/weather-card.yaml`
- Package: `homeassistant/packages/roamcore_weather_time.yaml`
- Tests: `homeassistant/tools/roamcore_weather/tests/`
