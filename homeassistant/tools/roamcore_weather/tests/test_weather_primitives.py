"""Unit tests for RoamCore weather primitives.

Pure-Python tests — no Home Assistant runtime required.
Run with:
    python -m unittest discover -s homeassistant/tools/roamcore_weather/tests
or:
    python -m pytest homeassistant/tools/roamcore_weather/tests/
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types
import unittest

HERE = os.path.dirname(__file__)
# weather_primitives lives at homeassistant/roamcore_weather_primitives.py
# (top of the HA tree, NOT inside the custom_components/roamcore package)
# so it can be imported + tested without triggering the parent package's
# HA-dependent __init__.py.
MODULE_PATH = os.path.abspath(
    os.path.join(HERE, "..", "..", "..", "roamcore_weather_primitives.py")
)


def _load_weather_primitives():
    """Load `weather_primitives.py` directly, bypassing the parent package's
    `__init__.py` (which imports `homeassistant.*` and would crash without
    the full HA runtime installed).
    """
    spec = importlib.util.spec_from_file_location(
        "rc_weather_primitives", MODULE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Inject into sys.modules so any subsequent `import` finds it.
wp = _load_weather_primitives()
sys.modules.setdefault("rc_weather_primitives", wp)

RC_FORECAST_CONDITIONS = wp.RC_FORECAST_CONDITIONS
forecast_high_low_24h = wp.forecast_high_low_24h
map_forecast_condition = wp.map_forecast_condition
normalize_weather_payload = wp.normalize_weather_payload
precipitation_expected_2h = wp.precipitation_expected_2h
safe_bool = wp.safe_bool
safe_float = wp.safe_float


class TestMapForecastCondition(unittest.TestCase):
    """The canonical enum is the contract surface — these cases are the contract."""

    def test_canonical_values_are_stable(self):
        # The order matters for documentation — keep this tuple unchanged
        # unless the doc and dashboards are updated together.
        self.assertEqual(
            RC_FORECAST_CONDITIONS,
            ("clear", "cloudy", "rain", "snow", "storm", "fog", "unknown"),
        )

    def test_clear_variants(self):
        for raw in ("sunny", "clear", "clear-night"):
            self.assertEqual(map_forecast_condition(raw), "clear", msg=raw)

    def test_cloudy_variants(self):
        for raw in (
            "partlycloudy",
            "partly-cloudy",
            "mostlycloudy",
            "mostly-cloudy",
            "cloudy",
            "overcast",
        ):
            self.assertEqual(map_forecast_condition(raw), "cloudy", msg=raw)

    def test_rain_variants(self):
        for raw in (
            "rainy",
            "rain",
            "pouring",
            "drizzle",
            "showers",
            "light-rain",
            "heavy-rain",
        ):
            self.assertEqual(map_forecast_condition(raw), "rain", msg=raw)

    def test_snow_variants(self):
        for raw in ("snowy", "snow", "hail", "sleet", "light-snow", "heavy-snow"):
            self.assertEqual(map_forecast_condition(raw), "snow", msg=raw)

    def test_storm_variants(self):
        for raw in (
            "lightning",
            "lightning-rainy",
            "thunderstorm",
            "storm",
            "hurricane",
            "tropical-storm",
        ):
            self.assertEqual(map_forecast_condition(raw), "storm", msg=raw)

    def test_fog_variants(self):
        for raw in ("fog", "foggy", "haze", "mist", "smoke", "dust"):
            self.assertEqual(map_forecast_condition(raw), "fog", msg=raw)

    def test_wind_is_cloudy(self):
        # Wind has no dedicated enum slot; map to cloudy.
        self.assertEqual(map_forecast_condition("windy"), "cloudy")
        self.assertEqual(map_forecast_condition("wind"), "cloudy")

    def test_exceptional_is_unknown(self):
        self.assertEqual(map_forecast_condition("exceptional"), "unknown")

    def test_none_and_empty(self):
        self.assertEqual(map_forecast_condition(None), "unknown")
        self.assertEqual(map_forecast_condition(""), "unknown")
        self.assertEqual(map_forecast_condition("   "), "unknown")

    def test_unavailable_inputs(self):
        # These come straight from HA when the source is missing.
        self.assertEqual(map_forecast_condition("unknown"), "unknown")
        self.assertEqual(map_forecast_condition("unavailable"), "unknown")
        self.assertEqual(map_forecast_condition("none"), "unknown")

    def test_unknown_strings_map_to_unknown(self):
        self.assertEqual(map_forecast_condition("alien-weather"), "unknown")
        self.assertEqual(map_forecast_condition("42"), "unknown")

    def test_is_case_insensitive(self):
        self.assertEqual(map_forecast_condition("SUNNY"), "clear")
        self.assertEqual(map_forecast_condition("Clear"), "clear")
        self.assertEqual(map_forecast_condition("  Rain  "), "rain")

    def test_non_string_inputs(self):
        # HA sometimes returns ints/floats via state — never crash.
        self.assertEqual(map_forecast_condition(0), "unknown")
        self.assertEqual(map_forecast_condition(1.5), "unknown")


class TestSafeFloat(unittest.TestCase):
    def test_parses_valid_numbers(self):
        self.assertEqual(safe_float("12.5"), 12.5)
        self.assertEqual(safe_float("-3"), -3.0)
        self.assertEqual(safe_float(42), 42.0)

    def test_returns_none_for_invalid(self):
        self.assertIsNone(safe_float(None))
        self.assertIsNone(safe_float(""))
        self.assertIsNone(safe_float("not-a-number"))
        self.assertIsNone(safe_float("12.5abc"))


class TestSafeBool(unittest.TestCase):
    def test_truthy(self):
        for v in ("on", "true", "1", "yes", "ON", "True", "YES"):
            self.assertIs(safe_bool(v), True, msg=v)

    def test_falsy(self):
        for v in ("off", "false", "0", "no", "OFF", "False", "NO"):
            self.assertIs(safe_bool(v), False, msg=v)

    def test_unknown(self):
        self.assertIsNone(safe_bool(None))
        self.assertIsNone(safe_bool(""))
        self.assertIsNone(safe_bool("maybe"))
        self.assertIsNone(safe_bool("onish"))


class TestForecastHighLow24h(unittest.TestCase):
    def test_no_forecast(self):
        self.assertEqual(forecast_high_low_24h(None), (None, None))
        self.assertEqual(forecast_high_low_24h([]), (None, None))

    def test_simple_temperatures(self):
        # When no datetimes are present, the function uses first 8 entries
        # as the 24h window.
        fc = [{"temperature": 10}, {"temperature": 5}, {"temperature": 15}]
        self.assertEqual(forecast_high_low_24h(fc), (15.0, 5.0))

    def test_ignores_missing_temperatures(self):
        fc = [{"temperature": 10}, {"datetime": "2026-01-01T00:00:00Z"}]
        self.assertEqual(forecast_high_low_24h(fc), (10.0, 10.0))

    def test_handles_string_temperatures(self):
        fc = [{"temperature": "10"}, {"temperature": "5"}]
        self.assertEqual(forecast_high_low_24h(fc), (10.0, 5.0))

    def test_filters_to_24h_when_datetimes_present(self):
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        fc = [
            {"temperature": 100, "datetime": (now - timedelta(hours=1)).isoformat()},
            {"temperature": 12, "datetime": (now + timedelta(hours=1)).isoformat()},
            {"temperature": 8, "datetime": (now + timedelta(hours=23)).isoformat()},
            {"temperature": -50, "datetime": (now + timedelta(hours=48)).isoformat()},
        ]
        high, low = forecast_high_low_24h(fc)
        # The first entry is in the past (delta < 0) so filtered out.
        # High should be 12, low should be 8.
        self.assertEqual(high, 12.0)
        self.assertEqual(low, 8.0)

    def test_non_dict_entries_are_ignored(self):
        fc = [{"temperature": 5}, "string", None, {"temperature": 10}]
        self.assertEqual(forecast_high_low_24h(fc), (10.0, 5.0))

    def test_all_invalid_returns_none(self):
        fc = [{"temperature": "bad"}, {"temperature": None}]
        self.assertEqual(forecast_high_low_24h(fc), (None, None))


class TestPrecipitationExpected2h(unittest.TestCase):
    def test_no_forecast(self):
        self.assertIsNone(precipitation_expected_2h(None))
        self.assertIsNone(precipitation_expected_2h([]))

    def test_amount_positive_returns_true(self):
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        fc = [
            {
                "datetime": (now + timedelta(hours=1)).isoformat(),
                "precipitation": 0.5,
            }
        ]
        self.assertIs(precipitation_expected_2h(fc), True)

    def test_probability_above_threshold(self):
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        fc = [
            {
                "datetime": (now + timedelta(hours=1)).isoformat(),
                "precipitation_probability": 80,
            }
        ]
        self.assertIs(precipitation_expected_2h(fc), True)

    def test_probability_below_threshold(self):
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        fc = [
            {
                "datetime": (now + timedelta(hours=1)).isoformat(),
                "precipitation_probability": 20,
            }
        ]
        self.assertIs(precipitation_expected_2h(fc), False)

    def test_no_precipitation_data_returns_none(self):
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        fc = [
            {
                "datetime": (now + timedelta(hours=1)).isoformat(),
                "temperature": 12,
            }
        ]
        self.assertIsNone(precipitation_expected_2h(fc))

    def test_outside_2h_window_ignored(self):
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        fc = [
            {
                "datetime": (now + timedelta(hours=3)).isoformat(),
                "precipitation": 5.0,
            }
        ]
        # No entries within 2h, no precip data → None.
        self.assertIsNone(precipitation_expected_2h(fc))


class TestNormalizeWeatherPayload(unittest.TestCase):
    def test_basic_payload(self):
        raw = {
            "outdoor_temperature_c": 12.4,
            "outdoor_humidity_pct": 75,
            "forecast_condition": "rainy",
            "forecast_high_temp_24h_c": 18.0,
            "forecast_low_temp_24h_c": 7.0,
            "precipitation_expected_2h": "on",
            "sun_next_event": "2026-01-02T16:00:00+00:00",
            "weather_entity_id": "weather.home",
            "reason": "ok",
        }
        out = normalize_weather_payload(raw)
        self.assertEqual(out["outdoor_temperature_c"], 12.4)
        self.assertEqual(out["outdoor_humidity_pct"], 75.0)
        self.assertEqual(out["forecast_condition"], "rain")
        self.assertEqual(out["forecast_high_temp_24h_c"], 18.0)
        self.assertEqual(out["forecast_low_temp_24h_c"], 7.0)
        self.assertIs(out["precipitation_expected_2h"], True)
        self.assertEqual(out["sun_next_event"], "2026-01-02T16:00:00+00:00")
        self.assertEqual(out["weather_entity_id"], "weather.home")
        self.assertEqual(out["reason"], "ok")

    def test_null_and_unavailable_become_none_or_unknown(self):
        raw = {
            "outdoor_temperature_c": None,
            "outdoor_humidity_pct": "unavailable",
            "forecast_condition": "unavailable",
            "forecast_high_temp_24h_c": None,
            "forecast_low_temp_24h_c": None,
            "precipitation_expected_2h": "unknown",
            "sun_next_event": None,
            "weather_entity_id": "",
            "reason": "no_weather_integration",
        }
        out = normalize_weather_payload(raw)
        self.assertIsNone(out["outdoor_temperature_c"])
        self.assertIsNone(out["outdoor_humidity_pct"])
        # "unavailable" maps to canonical "unknown"
        self.assertEqual(out["forecast_condition"], "unknown")
        self.assertIsNone(out["forecast_high_temp_24h_c"])
        self.assertIsNone(out["forecast_low_temp_24h_c"])
        self.assertIsNone(out["precipitation_expected_2h"])
        self.assertIsNone(out["sun_next_event"])
        self.assertIsNone(out["weather_entity_id"])
        self.assertEqual(out["reason"], "no_weather_integration")

    def test_extra_keys_preserved(self):
        out = normalize_weather_payload(
            {"reason": "ok", "future_field": 42, "forecast_condition": "sunny"}
        )
        self.assertIn("future_field", out)
        self.assertEqual(out["future_field"], 42)
        self.assertEqual(out["forecast_condition"], "clear")

    def test_partial_payload(self):
        # Only some fields present — that's fine.
        out = normalize_weather_payload({"outdoor_temperature_c": 12.0})
        self.assertEqual(out["outdoor_temperature_c"], 12.0)
        self.assertNotIn("outdoor_humidity_pct", out)

    def test_empty_payload(self):
        out = normalize_weather_payload({})
        self.assertEqual(out, {})

    def test_garbage_inputs_do_not_raise(self):
        # The contract is "never crash the API". Verify.
        out = normalize_weather_payload(
            {
                "outdoor_temperature_c": object(),
                "forecast_condition": ["rain"],
                "precipitation_expected_2h": 42,
            }
        )
        self.assertIsNone(out["outdoor_temperature_c"])
        # list → str() → "['rain']" → unknown
        self.assertEqual(out["forecast_condition"], "unknown")
        # 42 → safe_bool → None
        self.assertIsNone(out["precipitation_expected_2h"])


class TestEndToEndJSONShape(unittest.TestCase):
    """Sanity-check that the JSON shape an agent would see matches the brief.

    Brief acceptance criteria (#14):
      - outdoor temp: float|null
      - forecast condition: canonical enum string
      - precip expected 2h: bool|null
    """

    def test_full_weather_snapshot_is_json_serializable(self):
        import json

        raw = {
            "outdoor_temperature_c": 12.4,
            "outdoor_humidity_pct": 75.0,
            "forecast_condition": "partly-cloudy",
            "forecast_high_temp_24h_c": 18.0,
            "forecast_low_temp_24h_c": 7.0,
            "precipitation_expected_2h": False,
            "sun_next_event": "2026-01-02T16:00:00+00:00",
            "weather_entity_id": "weather.home",
            "reason": "ok",
        }
        out = normalize_weather_payload(raw)
        encoded = json.dumps(out)
        self.assertIn('"outdoor_temperature_c": 12.4', encoded)
        self.assertIn('"forecast_condition": "cloudy"', encoded)  # partly-cloudy → cloudy
        self.assertIn('"precipitation_expected_2h": false', encoded)

    def test_degraded_snapshot_serializes_cleanly(self):
        import json

        raw = {
            "outdoor_temperature_c": None,
            "forecast_condition": None,
            "precipitation_expected_2h": None,
            "weather_entity_id": "",
            "reason": "no_weather_integration",
        }
        out = normalize_weather_payload(raw)
        # Must round-trip through JSON without errors and without surfacing
        # raw HA "unknown"/"unavailable" strings.
        encoded = json.dumps(out)
        decoded = json.loads(encoded)
        self.assertIsNone(decoded["outdoor_temperature_c"])
        self.assertEqual(decoded["forecast_condition"], "unknown")
        self.assertIsNone(decoded["precipitation_expected_2h"])
        self.assertEqual(decoded["reason"], "no_weather_integration")


if __name__ == "__main__":
    unittest.main()