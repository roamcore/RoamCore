"""Pure-function helpers for the RoamCore weather contract.

These helpers are intentionally **HA-free** (no HomeAssistantView, no
ConfigEntry, no global state) so they can be unit-tested without a live
HA install.

Reference: docs/reference/rc-entity-naming.md
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

# Canonical forecast-condition enum. Must match the docs/catalog/weather
# contract. Automations should branch on these strings only.
RC_FORECAST_CONDITIONS: tuple[str, ...] = (
    "clear",
    "cloudy",
    "rain",
    "snow",
    "storm",
    "fog",
    "unknown",
)

# Raw HA weather states → canonical enum mapping.
# Lower-cased, covers the Met.no / OpenWeatherMap / NWS state strings that
# HA's weather integrations emit (HA itself does not normalize).
_RAW_TO_CANONICAL: dict[str, str] = {
    # clear
    "sunny": "clear",
    "clear": "clear",
    "clear-night": "clear",
    # cloudy
    "partlycloudy": "cloudy",
    "partly-cloudy": "cloudy",
    "mostlycloudy": "cloudy",
    "mostly-cloudy": "cloudy",
    "cloudy": "cloudy",
    "overcast": "cloudy",
    # rain
    "rainy": "rain",
    "rain": "rain",
    "pouring": "rain",
    "drizzle": "rain",
    "showers": "rain",
    "light-rain": "rain",
    "heavy-rain": "rain",
    # snow
    "snowy": "snow",
    "snow": "snow",
    "snowy-rainy": "snow",
    "snow-rainy": "snow",
    "hail": "snow",
    "sleet": "snow",
    "light-snow": "snow",
    "heavy-snow": "snow",
    # storm
    "lightning": "storm",
    "lightning-rainy": "storm",
    "thunderstorm": "storm",
    "storm": "storm",
    "hurricane": "storm",
    "tropical-storm": "storm",
    # fog
    "fog": "fog",
    "foggy": "fog",
    "haze": "fog",
    "mist": "fog",
    "smoke": "fog",
    "dust": "fog",
    # wind is treated as "cloudy" (no dedicated enum) — surface
    # wind explicitly via `rc_weather_forecast_*` if added later.
    "windy": "cloudy",
    "wind": "cloudy",
    # exceptional / unknown
    "exceptional": "unknown",
}


def map_forecast_condition(raw: Any) -> str:
    """Map a raw HA weather state string to the RC canonical enum.

    Never raises; never returns a value outside `RC_FORECAST_CONDITIONS`.
    """
    if raw is None:
        return "unknown"
    s = str(raw).strip().lower()
    if not s or s in ("unknown", "unavailable", "none"):
        return "unknown"
    return _RAW_TO_CANONICAL.get(s, "unknown")


def safe_float(v: Any) -> Optional[float]:
    """Best-effort float parse. Returns None on any failure."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f


def safe_bool(v: Any) -> Optional[bool]:
    """Best-effort bool parse for HA state strings."""
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in ("on", "true", "1", "yes"):
        return True
    if s in ("off", "false", "0", "no"):
        return False
    return None


def forecast_high_low_24h(forecast: Optional[Iterable[dict[str, Any]]]) -> tuple[Optional[float], Optional[float]]:
    """Extract (high, low) temperatures from an HA weather forecast list.

    HA's `weather.*` integrations expose a `forecast` attribute as a list of
    dicts. Each dict may include `temperature`, `datetime`, etc. We pull
    temperatures over the next 24h (HA's forecast is typically hourly or
    3-hourly, so we take the first 24 hours if datetimes are present,
    otherwise we use the first 8 entries as a sensible default window).

    Returns `(high, low)` as floats, or `(None, None)` if no usable data.
    """
    if not forecast:
        return (None, None)

    # Convert to a list so we can iterate twice if needed.
    items: list[dict[str, Any]] = []
    for entry in forecast:
        if isinstance(entry, dict):
            items.append(entry)

    if not items:
        return (None, None)

    # Best-effort: filter to the next 24h if we can parse datetimes.
    from datetime import datetime as _dt, timezone as _tz

    selected: list[dict[str, Any]] = []
    horizon_hits = 0
    for entry in items:
        ts_raw = entry.get("datetime")
        if ts_raw is None:
            selected.append(entry)
            continue
        try:
            ts = _dt.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=_tz.utc)
            now = _dt.now(_tz.utc)
            delta = (ts - now).total_seconds()
            if 0 <= delta <= 24 * 3600:
                selected.append(entry)
                horizon_hits += 1
        except Exception:
            selected.append(entry)

    if horizon_hits > 0:
        chosen = selected
    else:
        # Fallback: use first 8 entries (~24h for 3-hourly data).
        chosen = items[:8]

    temps: list[float] = []
    for entry in chosen:
        t = entry.get("temperature")
        f = safe_float(t)
        if f is not None:
            temps.append(f)

    if not temps:
        return (None, None)
    return (max(temps), min(temps))


def precipitation_expected_2h(forecast: Optional[Iterable[dict[str, Any]]]) -> Optional[bool]:
    """Return True/False if precipitation is expected in the next 2h.

    Considers both `precipitation` (mm) and `precipitation_probability` (%)
    fields. Returns None when no forecast is available or no signal can be
    derived — caller should map that to "unknown" for a binary sensor.
    """
    if not forecast:
        return None

    from datetime import datetime as _dt, timezone as _tz

    horizon_seconds = 2 * 3600
    now = _dt.now(_tz.utc)

    precip_seen = False
    precip_amount = 0.0
    precip_prob_seen = False
    precip_prob_max = 0.0

    for entry in forecast:
        if not isinstance(entry, dict):
            continue
        # Window check
        ts_raw = entry.get("datetime")
        if ts_raw is not None:
            try:
                ts = _dt.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=_tz.utc)
                delta = (ts - now).total_seconds()
                if not (0 <= delta <= horizon_seconds):
                    continue
            except Exception:
                pass  # fall through to a value-only check

        p = safe_float(entry.get("precipitation"))
        if p is not None:
            precip_seen = True
            precip_amount = max(precip_amount, p)

        pp = safe_float(entry.get("precipitation_probability"))
        if pp is not None:
            precip_prob_seen = True
            precip_prob_max = max(precip_prob_max, pp)

    if not precip_seen and not precip_prob_seen:
        return None
    if precip_amount > 0:
        return True
    if precip_prob_max > 30:
        return True
    return False


def normalize_weather_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize a weather payload dict for JSON exposure.

    Coerces nullable values to a stable shape: numbers become float|None,
    booleans become bool|None, and condition strings become canonical
    enum values. Unknown keys are preserved as-is.

    This is the single function exercised by the OpenClaw endpoint
    controller logic and is the primary target for unit tests.
    """
    out: dict[str, Any] = {}

    if "outdoor_temperature_c" in payload:
        out["outdoor_temperature_c"] = safe_float(payload.get("outdoor_temperature_c"))

    if "outdoor_humidity_pct" in payload:
        out["outdoor_humidity_pct"] = safe_float(payload.get("outdoor_humidity_pct"))

    if "forecast_condition" in payload:
        out["forecast_condition"] = map_forecast_condition(payload.get("forecast_condition"))

    if "forecast_high_temp_24h_c" in payload:
        out["forecast_high_temp_24h_c"] = safe_float(payload.get("forecast_high_temp_24h_c"))

    if "forecast_low_temp_24h_c" in payload:
        out["forecast_low_temp_24h_c"] = safe_float(payload.get("forecast_low_temp_24h_c"))

    if "precipitation_expected_2h" in payload:
        out["precipitation_expected_2h"] = safe_bool(payload.get("precipitation_expected_2h"))

    if "sun_next_event" in payload:
        out["sun_next_event"] = payload.get("sun_next_event") or None

    if "weather_entity_id" in payload:
        out["weather_entity_id"] = payload.get("weather_entity_id") or None

    if "reason" in payload:
        out["reason"] = str(payload.get("reason") or "unknown")

    # Preserve any extra keys (forward-compat).
    for k, v in payload.items():
        if k not in out:
            out[k] = v

    return out