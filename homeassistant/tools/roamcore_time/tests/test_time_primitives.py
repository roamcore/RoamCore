"""Unit tests for RoamCore time primitives.

Pure-Python tests — no Home Assistant runtime required.
Run with:
    python -m unittest discover -s homeassistant/tools/roamcore_time/tests
or:
    python -m pytest homeassistant/tools/roamcore_time/tests/
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(__file__)
# time_primitives lives at homeassistant/roamcore_time_primitives.py
# (top of the HA tree, NOT inside the custom_components/roamcore package)
# so it can be imported + tested without triggering the parent package's
# HA-dependent __init__.py.
MODULE_PATH = os.path.abspath(
    os.path.join(HERE, "..", "..", "..", "roamcore_time_primitives.py")
)


def _load_time_primitives():
    """Load `time_primitives.py` directly, bypassing the parent package's
    `__init__.py` (which imports `homeassistant.*` and would crash without
    the full HA runtime installed).
    """
    spec = importlib.util.spec_from_file_location(
        "rc_time_primitives", MODULE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Inject into sys.modules so any subsequent `import` finds it.
tp = _load_time_primitives()
sys.modules.setdefault("rc_time_primitives", tp)

RC_TIMEZONE_SOURCES = tp.RC_TIMEZONE_SOURCES
RC_TIME_STATUSES = tp.RC_TIME_STATUSES
is_valid_iana_name = tp.is_valid_iana_name
resolve_timezone = tp.resolve_timezone
safe_isoformat = tp.safe_isoformat
normalize_time_payload = tp.normalize_time_payload


class TestCanonicalEnums(unittest.TestCase):
    """The canonical enums are the contract surface — these cases are the contract."""

    def test_sources_enum_is_stable(self):
        # Order matters for documentation — keep this tuple unchanged
        # unless the doc and dashboards are updated together.
        self.assertEqual(
            RC_TIMEZONE_SOURCES,
            ("override", "ha_config", "browser", "unknown"),
        )

    def test_statuses_enum_is_stable(self):
        self.assertEqual(
            RC_TIME_STATUSES,
            ("ok", "no_override", "invalid_override", "ha_unconfigured", "unknown"),
        )


class TestIsValidIanaName(unittest.TestCase):
    def test_canonical_names_valid(self):
        for name in (
            "UTC",
            "Etc/UTC",
            "Europe/London",
            "America/New_York",
            "Asia/Tokyo",
            "Australia/Sydney",
        ):
            self.assertTrue(is_valid_iana_name(name), msg=name)

    def test_case_is_sensitive(self):
        # zoneinfo is case-sensitive — we mirror that behavior.
        self.assertFalse(is_valid_iana_name("EUROPE/LONDON"))
        self.assertFalse(is_valid_iana_name("europe/london"))
        self.assertTrue(is_valid_iana_name("Europe/London"))

    def test_empty_and_none_are_invalid(self):
        for v in (None, "", "   ", 0, False, []):
            self.assertFalse(is_valid_iana_name(v), msg=repr(v))

    def test_garbage_is_invalid(self):
        for v in ("Not/A/Zone", "FooBar", "12345", "Europe/Atlantis"):
            self.assertFalse(is_valid_iana_name(v), msg=v)

    def test_non_string_is_invalid(self):
        # Never crashes.
        for v in (123, 1.5, ["Europe/London"], {"name": "Europe/London"}, object()):
            self.assertFalse(is_valid_iana_name(v), msg=repr(v))


class TestResolveTimezone(unittest.TestCase):
    """The fallback chain is the contract."""

    def test_override_valid_used_first(self):
        self.assertEqual(
            resolve_timezone("Europe/London", "America/New_York"),
            ("Europe/London", "override"),
        )

    def test_override_empty_falls_through_to_ha_config(self):
        self.assertEqual(
            resolve_timezone("", "America/New_York"),
            ("America/New_York", "ha_config"),
        )

    def test_override_none_falls_through_to_ha_config(self):
        self.assertEqual(
            resolve_timezone(None, "America/New_York"),
            ("America/New_York", "ha_config"),
        )

    def test_override_whitespace_falls_through_to_ha_config(self):
        self.assertEqual(
            resolve_timezone("   ", "America/New_York"),
            ("America/New_York", "ha_config"),
        )

    def test_override_invalid_falls_back_to_ha_config_with_invalid_source(self):
        # User wrote garbage — we surface that via the source so the UI
        # can explain what went wrong.
        self.assertEqual(
            resolve_timezone("Not/A/Zone", "America/New_York"),
            ("America/New_York", "invalid_override"),
        )

    def test_override_invalid_and_ha_unconfigured(self):
        # Both unusable — we still return a meaningful source for the
        # status sensor to surface.
        self.assertEqual(
            resolve_timezone("Not/A/Zone", None),
            (None, "invalid_override"),
        )

    def test_override_invalid_and_ha_empty(self):
        self.assertEqual(
            resolve_timezone("FOO/BAR", ""),
            (None, "invalid_override"),
        )

    def test_ha_config_set_without_override(self):
        self.assertEqual(
            resolve_timezone(None, "UTC"),
            ("UTC", "ha_config"),
        )

    def test_ha_config_set_but_invalid(self):
        # Treat invalid ha_config as "not provided" — never crashes.
        self.assertEqual(
            resolve_timezone(None, "Not/A/Zone"),
            (None, "unknown"),
        )

    def test_ha_config_empty_returns_unknown(self):
        self.assertEqual(
            resolve_timezone(None, None),
            (None, "unknown"),
        )
        self.assertEqual(
            resolve_timezone(None, ""),
            (None, "unknown"),
        )

    def test_both_empty_returns_unknown(self):
        self.assertEqual(
            resolve_timezone("", ""),
            (None, "unknown"),
        )

    def test_override_strips_whitespace(self):
        self.assertEqual(
            resolve_timezone("  Europe/London  ", "America/New_York"),
            ("Europe/London", "override"),
        )

    def test_non_string_override_does_not_crash(self):
        # Never raises on weird input. A non-empty-but-invalid override
        # (any value that coerces to a non-empty stripped string that
        # isn't a valid IANA name) is treated as `invalid_override` per
        # the contract; the resolved tz still falls back to ha_config.
        for v in (123, 1.5, [], {}, object()):
            result = resolve_timezone(v, "UTC")
            self.assertIsInstance(result, tuple)
            self.assertEqual(result, ("UTC", "invalid_override"))

        # Truly empty inputs (None / empty string) are treated as
        # "no override" and fall through to ha_config cleanly.
        for v in (None, ""):
            result = resolve_timezone(v, "UTC")
            self.assertEqual(result, ("UTC", "ha_config"), msg=repr(v))

    def test_non_string_ha_config_does_not_crash(self):
        # ha_config path is only consulted when override is empty/None;
        # if ha_config is unparseable it must not crash — we fall back
        # to (None, "unknown").
        result = resolve_timezone(None, [])
        self.assertEqual(result, (None, "unknown"))

        result = resolve_timezone(None, object())
        self.assertEqual(result, (None, "unknown"))

    def test_non_string_override_with_valid_string_override(self):
        # When the user supplied a valid override, weird ha_config input
        # must not be inspected at all — we never reach the ha_config
        # branch.
        result = resolve_timezone("Europe/London", object())
        self.assertEqual(result, ("Europe/London", "override"))

    def test_override_takes_priority_even_when_ha_unset(self):
        self.assertEqual(
            resolve_timezone("Europe/London", None),
            ("Europe/London", "override"),
        )

    def test_override_takes_priority_even_when_ha_empty(self):
        self.assertEqual(
            resolve_timezone("Europe/London", ""),
            ("Europe/London", "override"),
        )


class TestSafeIsoformat(unittest.TestCase):
    def test_none_returns_none(self):
        self.assertIsNone(safe_isoformat(None))

    def test_aware_datetime_preserves_offset(self):
        dt = datetime(2026, 7, 28, 12, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(safe_isoformat(dt), "2026-07-28T12:00:00+00:00")

    def test_aware_datetime_non_utc_offset(self):
        # Build a fixed +02:00 offset without depending on zoneinfo.
        dt = datetime(2026, 7, 28, 14, 0, 0, tzinfo=timezone(timedelta(hours=2)))
        self.assertEqual(safe_isoformat(dt), "2026-07-28T14:00:00+02:00")

    def test_naive_datetime_treated_as_utc(self):
        dt = datetime(2026, 7, 28, 12, 0, 0)
        # Naive datetimes are forced to UTC so we always emit an offset.
        self.assertEqual(safe_isoformat(dt), "2026-07-28T12:00:00+00:00")

    def test_non_datetime_returns_none(self):
        for v in ("2026-07-28", 12345, 1.5, [], {}, object(), True):
            self.assertIsNone(safe_isoformat(v), msg=repr(v))


class TestNormalizeTimePayload(unittest.TestCase):
    """`normalize_time_payload` is the primary target — the contract layer."""

    def test_canonical_enums_are_stable(self):
        # The enums must match the values the YAML template emits so the
        # JSON API never diverges from the sensor layer.
        self.assertEqual(
            RC_TIMEZONE_SOURCES,
            ("override", "ha_config", "browser", "unknown"),
        )
        self.assertEqual(
            RC_TIME_STATUSES,
            ("ok", "no_override", "invalid_override", "ha_unconfigured", "unknown"),
        )

    def test_basic_payload(self):
        raw = {
            "now_iso": "2026-07-28T23:00:00+00:00",
            "timezone": "Europe/London",
            "source": "override",
            "utc_offset_minutes": 60,
            "is_dst": True,
            "status": "ok",
            "reason": "ok",
        }
        out = normalize_time_payload(raw)
        self.assertEqual(out["now_iso"], "2026-07-28T23:00:00+00:00")
        self.assertEqual(out["timezone"], "Europe/London")
        self.assertEqual(out["source"], "override")
        self.assertEqual(out["utc_offset_minutes"], 60)
        self.assertIs(out["is_dst"], True)
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["reason"], "ok")

    def test_aware_datetime_now_iso_is_emitted(self):
        dt = datetime(2026, 7, 28, 23, 0, 0, tzinfo=timezone.utc)
        out = normalize_time_payload({"now_iso": dt, "reason": "ok"})
        self.assertEqual(out["now_iso"], "2026-07-28T23:00:00+00:00")

    def test_invalid_timezone_becomes_none(self):
        out = normalize_time_payload({"timezone": "Not/A/Zone"})
        self.assertIsNone(out["timezone"])

    def test_invalid_source_becomes_unknown(self):
        out = normalize_time_payload({"source": "martian"})
        self.assertEqual(out["source"], "unknown")

    def test_invalid_status_becomes_unknown(self):
        out = normalize_time_payload({"status": "banana"})
        self.assertEqual(out["status"], "unknown")

    def test_source_coercion_case_insensitive(self):
        # Allow HA-style state strings ("Override", "OVERRIDE") to map.
        out = normalize_time_payload({"source": "Override"})
        self.assertEqual(out["source"], "override")
        out = normalize_time_payload({"source": "HA_CONFIG"})
        self.assertEqual(out["source"], "ha_config")

    def test_status_coercion_case_insensitive(self):
        out = normalize_time_payload({"status": "OK"})
        self.assertEqual(out["status"], "ok")

    def test_null_and_unavailable_become_none_or_unknown(self):
        raw = {
            "now_iso": None,
            "timezone": None,
            "source": None,
            "utc_offset_minutes": None,
            "is_dst": None,
            "status": None,
            "reason": None,
        }
        out = normalize_time_payload(raw)
        self.assertIsNone(out["now_iso"])
        self.assertIsNone(out["timezone"])
        self.assertEqual(out["source"], "unknown")
        self.assertIsNone(out["utc_offset_minutes"])
        self.assertIsNone(out["is_dst"])
        self.assertEqual(out["status"], "unknown")
        self.assertEqual(out["reason"], "unknown")

    def test_empty_strings_become_none_or_unknown(self):
        raw = {
            "now_iso": "",
            "timezone": "",
            "source": "",
            "utc_offset_minutes": "",
            "is_dst": "",
            "status": "",
            "reason": "",
        }
        out = normalize_time_payload(raw)
        self.assertIsNone(out["now_iso"])
        self.assertIsNone(out["timezone"])
        self.assertEqual(out["source"], "unknown")
        self.assertIsNone(out["utc_offset_minutes"])
        self.assertIsNone(out["is_dst"])
        self.assertEqual(out["status"], "unknown")
        self.assertEqual(out["reason"], "unknown")

    def test_utc_offset_string_becomes_int(self):
        out = normalize_time_payload({"utc_offset_minutes": "60"})
        self.assertEqual(out["utc_offset_minutes"], 60)

    def test_utc_offset_float_string_becomes_int(self):
        out = normalize_time_payload({"utc_offset_minutes": "60.0"})
        self.assertEqual(out["utc_offset_minutes"], 60)

    def test_utc_offset_negative(self):
        out = normalize_time_payload({"utc_offset_minutes": -300})
        self.assertEqual(out["utc_offset_minutes"], -300)

    def test_utc_offset_garbage_becomes_none(self):
        out = normalize_time_payload({"utc_offset_minutes": "not-a-number"})
        self.assertIsNone(out["utc_offset_minutes"])

    def test_is_dst_string_parsing(self):
        for raw, expected in (
            ("on", True),
            ("off", False),
            ("true", True),
            ("false", False),
            ("yes", True),
            ("no", False),
        ):
            out = normalize_time_payload({"is_dst": raw})
            self.assertIs(out["is_dst"], expected, msg=f"{raw} -> {out['is_dst']}")

    def test_is_dst_unknown_string_becomes_none(self):
        out = normalize_time_payload({"is_dst": "maybe"})
        self.assertIsNone(out["is_dst"])

    def test_extra_keys_preserved(self):
        out = normalize_time_payload(
            {"reason": "ok", "future_field": 42, "source": "override"}
        )
        self.assertIn("future_field", out)
        self.assertEqual(out["future_field"], 42)
        self.assertEqual(out["source"], "override")

    def test_partial_payload(self):
        out = normalize_time_payload({"timezone": "UTC"})
        self.assertEqual(out["timezone"], "UTC")
        self.assertNotIn("source", out)
        self.assertNotIn("status", out)

    def test_empty_payload(self):
        out = normalize_time_payload({})
        self.assertEqual(out, {})

    def test_garbage_inputs_do_not_raise(self):
        # The contract is "never crash the API".
        out = normalize_time_payload(
            {
                "now_iso": object(),
                "timezone": 12345,
                "source": ["override"],
                "utc_offset_minutes": object(),
                "is_dst": "maybe",
                "status": {"foo": "bar"},
                "reason": None,
            }
        )
        # now_iso: object() → not a datetime → None
        self.assertIsNone(out["now_iso"])
        # timezone: 12345 → not a valid IANA name → None
        self.assertIsNone(out["timezone"])
        # source: list → str() → "['override']" → not in enum → "unknown"
        self.assertEqual(out["source"], "unknown")
        # utc_offset_minutes: object() → float() raises → None
        self.assertIsNone(out["utc_offset_minutes"])
        # is_dst: "maybe" → not in parse set → None
        self.assertIsNone(out["is_dst"])
        # status: dict → str() → not in enum → "unknown"
        self.assertEqual(out["status"], "unknown")
        # reason: None → "unknown"
        self.assertEqual(out["reason"], "unknown")


class TestRoundTripRealistic(unittest.TestCase):
    """Build a realistic payload and assert normalization is idempotent."""

    def _build(self):
        return {
            "now_iso": "2026-07-28T23:00:00+01:00",
            "timezone": "Europe/London",
            "source": "override",
            "utc_offset_minutes": 60,
            "is_dst": True,
            "status": "ok",
            "reason": "ok",
        }

    def test_normalize_is_idempotent(self):
        once = normalize_time_payload(self._build())
        twice = normalize_time_payload(once)
        self.assertEqual(once, twice)

    def test_round_trip_through_json(self):
        out = normalize_time_payload(self._build())
        encoded = json.dumps(out)
        decoded = json.loads(encoded)
        # Re-normalizing the decoded payload must produce the same shape.
        again = normalize_time_payload(decoded)
        self.assertEqual(out, again)

    def test_json_shape_is_what_an_agent_would_consume(self):
        out = normalize_time_payload(self._build())
        encoded = json.dumps(out)
        # All top-level keys must be present.
        for key in (
            "now_iso",
            "timezone",
            "source",
            "utc_offset_minutes",
            "is_dst",
            "status",
            "reason",
        ):
            self.assertIn(f'"{key}"', encoded, msg=f"missing key in JSON: {key}")


class TestEndToEndJSONShape(unittest.TestCase):
    """Sanity-check that the JSON shape an agent would see matches the brief.

    Brief acceptance criteria (#15):
      - now_iso: ISO-8601 string|null
      - timezone: IANA string|null
      - source: canonical enum string
      - utc_offset_minutes: int|null
      - is_dst: bool|null
      - status: canonical enum string
      - reason: string
    """

    def test_full_snapshot_is_json_serializable(self):
        raw = {
            "now_iso": "2026-07-28T23:00:00+01:00",
            "timezone": "Europe/London",
            "source": "override",
            "utc_offset_minutes": 60,
            "is_dst": True,
            "status": "ok",
            "reason": "ok",
        }
        out = normalize_time_payload(raw)
        encoded = json.dumps(out)
        self.assertIn('"now_iso": "2026-07-28T23:00:00+01:00"', encoded)
        self.assertIn('"timezone": "Europe/London"', encoded)
        self.assertIn('"source": "override"', encoded)
        self.assertIn('"utc_offset_minutes": 60', encoded)
        self.assertIn('"is_dst": true', encoded)
        self.assertIn('"status": "ok"', encoded)
        self.assertIn('"reason": "ok"', encoded)

    def test_degraded_snapshot_serializes_cleanly(self):
        raw = {
            "now_iso": None,
            "timezone": None,
            "source": None,
            "utc_offset_minutes": None,
            "is_dst": None,
            "status": None,
            "reason": "ha_unconfigured",
        }
        out = normalize_time_payload(raw)
        encoded = json.dumps(out)
        decoded = json.loads(encoded)
        self.assertIsNone(decoded["now_iso"])
        self.assertIsNone(decoded["timezone"])
        self.assertEqual(decoded["source"], "unknown")
        self.assertIsNone(decoded["utc_offset_minutes"])
        self.assertIsNone(decoded["is_dst"])
        self.assertEqual(decoded["status"], "unknown")
        self.assertEqual(decoded["reason"], "ha_unconfigured")


if __name__ == "__main__":
    unittest.main()
