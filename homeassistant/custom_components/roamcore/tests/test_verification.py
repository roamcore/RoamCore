"""Tests for the RoamCore post-install verification framework.

Wave 9 #119d — Phase 2 canonical vehicle model VERIFICATION FRAMEWORK.

This rig proves the pure-Python contract is sound by running it
against the shipped canonical capabilities schema plus a battery of
mock-data scenarios (every 5-check pass + every 5-check fail + the
aggregation helpers + the cross-cutting anti-slop guards).

Pure stdlib + pytest. No Home Assistant imports — the rig tests the
framework in isolation, exactly like the directive requires
("successful install != working connection" + "values plausible,
data updates, device reconnects after restart").

Naming follows ``docs/reference/rc-entity-naming.md``:
  * canonical capability ids start with ``rc_``
  * no vendor names (victron, unifi, starlink, …) anywhere
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import time

import pytest

# --- Load verification.py + vehicle_model.py by absolute file path so we
# don't depend on pytest's package-discovery machinery — pytest auto-
# imports the parent `homeassistant/custom_components/roamcore/__init__.py`
# when the test file lives inside that package, which requires the HA
# runtime. Loading by file path bypasses that import entirely. Mirrors
# the pattern in `test_vehicle_model.py` and the sibling slice
# `test_capability_mapping.py`. ---

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
_CC_DIR = os.path.join(_REPO_ROOT, "homeassistant", "custom_components", "roamcore")
_VM_PATH = os.path.join(_CC_DIR, "vehicle_model.py")
_VF_PATH = os.path.join(_CC_DIR, "verification.py")


def _load_by_path(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, f"{path} not loadable"
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_vehicle_model = _load_by_path("roamcore_vehicle_model_for_verification_tests", _VM_PATH)
_verification = _load_by_path("roamcore_verification", _VF_PATH)

# Convenience re-exports so the tests below read like English.
VerificationTarget = _verification.VerificationTarget
VerificationResult = _verification.VerificationResult
verify_connection = _verification.verify_connection
verify_capability_map = _verification.verify_capability_map
assert_rc_prefix = _verification.assert_rc_prefix
assert_no_vendor_tokens = _verification.assert_no_vendor_tokens
CHECK_ORDER = _verification.CHECK_ORDER
DEFAULT_FRESHNESS_SECONDS = _verification.DEFAULT_FRESHNESS_SECONDS
DEFAULT_MAX_JUMP_FRACTION = _verification.DEFAULT_MAX_JUMP_FRACTION
DEFAULT_MIN_SECONDS_BETWEEN_JUMPS = _verification.DEFAULT_MIN_SECONDS_BETWEEN_JUMPS

FORBIDDEN_VENDOR_TOKENS = _vehicle_model.FORBIDDEN_VENDOR_TOKENS
load_capabilities = _vehicle_model.load_capabilities
find_capability = _vehicle_model.find_capability

SCHEMA_PATH = os.path.join(
    _REPO_ROOT, "connections", "_schema", "canonical_capabilities.json"
)


# --- Tiny helpers -----------------------------------------------------------


def _now() -> float:
    """Wall clock for tests that don't need determinism."""
    return time.time()


def _fixed_now() -> float:
    """A stable reference point for deterministic timestamp math.

    Useful when the test is comparing two samples whose relative
    spacing matters (e.g. data_plausible jumps). For `recent_update`
    we use wall-clock time because the framework compares samples
    against `time.time()` internally — so a "fixed" sample in the
    past is always stale relative to wall clock.
    """
    return 1_700_000_000.0  # 2023-11-14 22:13:20 UTC, easy to recognise


def _fresh_samples(values, base_ts=None, step=10):
    """Build a sample_history of `(timestamp, value)` tuples, fresh enough
    to pass `recent_update` (within the 60s window).

    Defaults `base_ts` to wall-clock NOW so `recent_update` sees the
    samples as fresh. Pass `base_ts=_fixed_now()` explicitly only when
    testing `data_plausible` (where the relative spacing matters).
    """
    if base_ts is None:
        base_ts = _now()
    return [(base_ts - (len(values) - i) * step, float(v)) for i, v in enumerate(values)]


def _stale_samples(values, base_ts=None, step=600):
    """Build a sample_history that's too old to pass `recent_update`."""
    if base_ts is None:
        base_ts = _now()
    return [(base_ts - (len(values) - i) * step, float(v)) for i, v in enumerate(values)]


# Schema (loaded once, shared across all tests).
_SCHEMA: dict | None = None


def _schema() -> dict:
    global _SCHEMA
    if _SCHEMA is None:
        _SCHEMA = load_capabilities(SCHEMA_PATH)
    return _SCHEMA


# --- Operator→vanlifer anti-slop guard --------------------------------------

# Forbidden operator-speak tokens (per the operator→vanlifer translation
# table). Every `reason` + `recovery_hint` string in the framework is
# scanned against this set; if any forbidden token appears, the
# framework is failing its own contract.
_FORBIDDEN_OPERATOR_TOKENS: tuple[str, ...] = (
    "entity",
    "integration",
    "capability discovery",
    "hacs",
    "lovelace",
    "dashboard tile",
    "automation",
    "script",
    "scene",
    "service call",
    "mdns",
    "zeroconf",
    "mqtt",
    "tailscale",
    "failover",
    "api key",
    "token",
)


def _is_vanlifery(s: str | None) -> bool:
    """True when `s` contains no forbidden operator-speak tokens.

    Word-boundary match is intentionally loose: a single forbidden
    substring anywhere in the string flags it. Plain-English target.
    """
    if not isinstance(s, str) or not s:
        return True
    lower = s.lower()
    return all(tok not in lower for tok in _FORBIDDEN_OPERATOR_TOKENS)


# ===========================================================================
# Module surface / dataclass shape
# ===========================================================================


def test_module_exposes_expected_public_api():
    """The public surface documented in the docstring is what we ship."""
    for name in (
        "VerificationTarget",
        "VerificationResult",
        "verify_connection",
        "verify_capability_map",
        "assert_rc_prefix",
        "assert_no_vendor_tokens",
        "CHECK_ORDER",
    ):
        assert hasattr(_verification, name), f"missing export: {name}"


def test_check_order_is_five_canonical_names_in_stable_order():
    """Stable order matters — tests assert "first failing check wins"."""
    assert CHECK_ORDER == (
        "value_in_range",
        "recent_update",
        "data_plausible",
        "restart_resilience",
        "vendor_match",
    )


def test_default_freshness_window_is_60_seconds():
    assert DEFAULT_FRESHNESS_SECONDS == 60.0


def test_default_jump_fraction_and_window_are_sane():
    assert 0.0 < DEFAULT_MAX_JUMP_FRACTION <= 1.0
    assert DEFAULT_MIN_SECONDS_BETWEEN_JUMPS > 0.0


def test_verification_target_dataclass_is_frozen():
    """Frozen dataclass: callers can't mutate after construction (audit trail)."""
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=[(_fixed_now(), 80.0)],
    )
    with pytest.raises((AttributeError, Exception)):
        target.capability_id = "rc_power_battery_soc_renamed"  # type: ignore[misc]


def test_verification_result_dataclass_is_frozen():
    result = VerificationResult(
        ok=True, reason="ok", recovery_hint=None, checks_run=[]
    )
    with pytest.raises((AttributeError, Exception)):
        result.ok = False  # type: ignore[misc]


def test_verification_result_defaults_checks_run_to_empty_list():
    """`checks_run` defaults to [] — dataclass field default."""
    result = VerificationResult(ok=True, reason="ok", recovery_hint=None)
    assert result.checks_run == []


# ===========================================================================
# value_in_range
# ===========================================================================


def test_value_in_range_passes_for_in_range_sample():
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=_fresh_samples([80.0, 81.0, 82.0]),
    )
    res = verify_connection(target, _schema())
    assert res.ok is True


def test_value_in_range_fails_for_out_of_range_sample_with_plain_english_reason():
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=_fresh_samples([150.0]),  # way over 100%
    )
    res = verify_connection(target, _schema())
    assert res.ok is False
    assert "outside the expected range" in res.reason
    assert "0 to 100" in res.reason
    assert res.recovery_hint is not None
    assert _is_vanlifery(res.reason)
    assert _is_vanlifery(res.recovery_hint)


def test_value_in_range_fails_for_negative_battery():
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=_fresh_samples([-5.0]),
    )
    res = verify_connection(target, _schema())
    assert res.ok is False
    assert "outside the expected range" in res.reason


def test_value_in_range_passes_when_no_range_supplied_or_derivable():
    """Lighting switch has no unit + no device_class → no range → skip."""
    target = VerificationTarget(
        capability_id="rc_lighting_interior_state",
        entity_id="switch.cabin_main",
        sample_history=_fresh_samples([1.0]),  # value doesn't matter
    )
    res = verify_connection(target, _schema())
    assert res.ok is True
    # value_in_range was skipped (not in checks_run).
    assert "value_in_range" not in res.checks_run


def test_value_in_range_fails_for_non_numeric_sample():
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=[(time.time(), "eighty")],
    )
    res = verify_connection(target, _schema())
    assert res.ok is False
    assert "isn't a number" in res.reason
    assert _is_vanlifery(res.reason)


def test_value_in_range_respects_explicit_expected_range_override():
    """Explicit range overrides the derived range."""
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=_fresh_samples([80.0]),
        expected_range=(70.0, 90.0),
    )
    res = verify_connection(target, _schema())
    assert res.ok is True

    target2 = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=_fresh_samples([80.0]),
        expected_range=(85.0, 100.0),  # 80 fails
    )
    res2 = verify_connection(target2, _schema())
    assert res2.ok is False
    assert "outside the expected range" in res2.reason


# ===========================================================================
# recent_update
# ===========================================================================


def test_recent_update_passes_when_sample_within_window():
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=[(_now() - 10, 80.0)],
    )
    res = verify_connection(target, _schema())
    assert res.ok is True


def test_recent_update_fails_when_oldest_sample_is_stale():
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=_stale_samples([80.0]),
    )
    res = verify_connection(target, _schema())
    assert res.ok is False
    assert "no fresh data in the last 60 seconds" in res.reason
    assert "device might have stopped sending" in res.reason
    assert res.recovery_hint is not None
    assert _is_vanlifery(res.reason)
    assert _is_vanlifery(res.recovery_hint)


def test_recent_update_fails_when_no_samples_at_all():
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=[],
    )
    res = verify_connection(target, _schema())
    assert res.ok is False
    assert "no data has arrived" in res.reason
    assert res.recovery_hint is not None
    assert _is_vanlifery(res.reason)


def test_recent_update_uses_freshest_sample_not_oldest():
    """Even one stale sample + one fresh sample must pass."""
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=[
            (_now() - 1000, 80.0),
            (_now() - 5, 81.0),  # fresh
        ],
    )
    res = verify_connection(target, _schema())
    assert res.ok is True


# ===========================================================================
# data_plausible
# ===========================================================================


def test_data_plausible_passes_for_smooth_history():
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=_fresh_samples([80.0, 80.5, 81.0, 81.5, 82.0], step=1),
    )
    res = verify_connection(target, _schema())
    assert res.ok is True


def test_data_plausible_passes_for_one_percent_step_in_one_second():
    """A 1% step in 1 second is plausible battery behaviour."""
    base = _now()
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=[(base, 80.0), (base + 1, 81.0)],
    )
    res = verify_connection(target, _schema())
    assert res.ok is True


def test_data_plausible_fails_for_zero_to_hundred_jump_in_one_second():
    """A 100% jump in 1 second is implausible for any battery chemistry."""
    base = _now()
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=[(base, 0.0), (base + 1, 100.0)],
    )
    res = verify_connection(target, _schema())
    assert res.ok is False
    assert "impossible jump" in res.reason
    assert res.recovery_hint is not None
    assert _is_vanlifery(res.reason)
    assert _is_vanlifery(res.recovery_hint)


def test_data_plausible_passes_when_jump_is_slow_enough():
    """A 100% jump over 10 minutes is plausible (full charge cycle)."""
    base = _now()
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=[
            (base, 0.0),
            (base + 600, 100.0),  # 600 seconds = 10 minutes
        ],
    )
    res = verify_connection(target, _schema())
    assert res.ok is True


def test_data_plausible_passes_when_only_one_sample():
    """Single sample → no comparison possible → skip."""
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=_fresh_samples([80.0]),
    )
    res = verify_connection(target, _schema())
    assert res.ok is True
    assert "data_plausible" not in res.checks_run


def test_data_plausible_fails_for_non_numeric_value_in_history():
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=[(_now(), 80.0), (_now() + 1, "eighty")],
    )
    res = verify_connection(target, _schema())
    assert res.ok is False
    assert "isn't a number" in res.reason


# ===========================================================================
# restart_resilience
# ===========================================================================


def test_restart_resilience_passes_with_zero_restarts_no_disconnect():
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=_fresh_samples([80.0]),
        connection_metadata={"restart_count": 0},
    )
    res = verify_connection(target, _schema())
    assert res.ok is True


def test_restart_resilience_passes_when_samples_arrive_after_disconnect():
    now = _now()
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        # Two samples: a recent one (fresh, after the disconnect) and
        # an older one (before the disconnect). The recent one
        # satisfies recent_update AND the post-disconnect check.
        sample_history=[
            (now - 300, 80.0),
            (now - 5, 81.0),  # fresh + AFTER the disconnect
        ],
        connection_metadata={
            "restart_count": 1,
            "last_disconnect_at": now - 200,  # between the two samples
        },
    )
    res = verify_connection(target, _schema())
    assert res.ok is True


def test_restart_resilience_fails_when_no_samples_after_disconnect():
    """Device restarted, samples exist BEFORE but NOT AFTER the disconnect."""
    now = _now()
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        # Only one sample, 30s ago (still fresh for recent_update).
        # But the disconnect happened 1s ago, AFTER the sample arrived.
        sample_history=[(now - 30, 80.0)],
        connection_metadata={
            "restart_count": 1,
            "last_disconnect_at": now - 1,  # 1 second ago, after the sample
        },
    )
    res = verify_connection(target, _schema())
    assert res.ok is False
    assert "didn't come back after the last restart" in res.reason
    assert res.recovery_hint is not None
    assert _is_vanlifery(res.reason)
    assert _is_vanlifery(res.recovery_hint)


def test_restart_resilience_fails_for_negative_restart_count():
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=_fresh_samples([80.0]),
        connection_metadata={"restart_count": -1},
    )
    res = verify_connection(target, _schema())
    assert res.ok is False
    assert "restart counter" in res.reason


def test_restart_resilience_fails_for_non_int_restart_count():
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=_fresh_samples([80.0]),
        connection_metadata={"restart_count": "two"},
    )
    res = verify_connection(target, _schema())
    assert res.ok is False


def test_restart_resilience_passes_when_connection_metadata_is_none():
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=_fresh_samples([80.0]),
        connection_metadata=None,
    )
    res = verify_connection(target, _schema())
    assert res.ok is True


# ===========================================================================
# vendor_match
# ===========================================================================


def test_vendor_match_passes_for_example_source_family():
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",  # vt_ matches
        sample_history=_fresh_samples([80.0]),
    )
    res = verify_connection(target, _schema())
    assert res.ok is True


def test_vendor_match_passes_for_alternative_example_source():
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.battery_state",  # "battery" matches
        sample_history=_fresh_samples([80.0]),
    )
    res = verify_connection(target, _schema())
    assert res.ok is True


def test_vendor_match_fails_for_unrelated_entity_id():
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.unifi_random_thing",  # no vt_, no battery
        sample_history=_fresh_samples([80.0]),
    )
    res = verify_connection(target, _schema())
    assert res.ok is False
    assert "doesn't look like the kind of device" in res.reason
    assert res.recovery_hint is not None
    assert _is_vanlifery(res.reason)
    assert _is_vanlifery(res.recovery_hint)


def test_vendor_match_skips_when_capability_has_no_examples():
    """Defensive: a capability with no example_sources → skip the check.

    The shipped schema always supplies example_sources, so we can't
    test this against the real schema. Build a tiny ad-hoc schema
    inline for this test only.
    """
    ad_hoc_schema = {
        "title": "test",
        "capability_categories": ["lighting"],
        "capabilities": [
            {
                "id": "rc_lighting_interior_state",
                "category": "lighting",
                "kind": "control",
                "type": "switch",
                "description": "interior lights on/off",
                # No example_sources field.
            }
        ],
    }
    target = VerificationTarget(
        capability_id="rc_lighting_interior_state",
        entity_id="switch.something_completely_different",
        sample_history=_fresh_samples([1.0]),
    )
    res = verify_connection(target, ad_hoc_schema)
    assert res.ok is True
    # vendor_match was skipped (no examples → no expectation).
    assert "vendor_match" not in res.checks_run


# ===========================================================================
# Aggregation (verify_connection top-level)
# ===========================================================================


def test_verify_connection_all_pass_returns_ok_with_five_checks_run():
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=_fresh_samples([80.0, 80.5, 81.0], step=1),
        connection_metadata={"restart_count": 0},
    )
    res = verify_connection(target, _schema())
    assert res.ok is True
    assert res.reason == "Verified — your device is sending fresh, plausible data"
    assert res.recovery_hint is None
    assert res.checks_run == list(CHECK_ORDER)


def test_verify_connection_first_failing_check_wins_for_aggregation():
    """Multiple failures → first-check-in-CHECK_ORDER wins the reason."""
    now = _now()
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.unifi_random_thing",  # vendor_match would fail
        sample_history=[(now - 5, 200.0)],  # fresh + out-of-range: value_in_range wins
        connection_metadata={"restart_count": -1},
    )
    res = verify_connection(target, _schema())
    assert res.ok is False
    # value_in_range runs first → its reason wins.
    assert "outside the expected range" in res.reason
    assert "value_in_range" in res.checks_run
    # Subsequent checks should NOT be listed in checks_run because we
    # short-circuited on the first failure.
    assert "recent_update" not in res.checks_run
    assert "data_plausible" not in res.checks_run
    assert "restart_resilience" not in res.checks_run
    assert "vendor_match" not in res.checks_run


def test_verify_connection_unknown_capability_id_runs_subset():
    """Capability id not in schema → vendor_match skips, others run."""
    target = VerificationTarget(
        capability_id="rc_does_not_exist",
        entity_id="sensor.anything",
        sample_history=_fresh_samples([80.0]),
    )
    res = verify_connection(target, _schema())
    assert res.ok is True


# ===========================================================================
# verify_capability_map (the batch helper)
# ===========================================================================


def _five_capability_mock_van():
    """A small mock van setup with 5 canonical capabilities, all fresh + plausible."""
    now = _now()
    cap_map = {
        "rc_power_battery_soc": "sensor.vt_battery_soc_percent",
        "rc_power_battery_voltage": "sensor.vt_battery_voltage_v",
        "rc_power_solar_power": "sensor.vt_solar_power_w",
        "rc_climate_indoor_temperature": "sensor.indoor_temp",
        "rc_water_fresh_level": "sensor.fresh_water_tank_level",
    }
    histories = {
        "rc_power_battery_soc": _fresh_samples([80.0, 80.5], base_ts=now),
        "rc_power_battery_voltage": _fresh_samples([12.8, 12.9], base_ts=now),
        "rc_power_solar_power": _fresh_samples([120.0, 122.0], base_ts=now),
        "rc_climate_indoor_temperature": _fresh_samples([20.0, 20.5], base_ts=now),
        "rc_water_fresh_level": _fresh_samples([75.0, 75.5], base_ts=now),
    }
    return cap_map, histories


def test_verify_capability_map_all_pass_returns_five_ok_results():
    cap_map, histories = _five_capability_mock_van()
    results = verify_capability_map(cap_map, histories, _schema())
    assert set(results.keys()) == set(cap_map.keys())
    assert len(results) == 5
    assert all(r.ok for r in results.values()), (
        f"expected all OK, got: {[(k, r.reason) for k, r in results.items()]}"
    )


def test_verify_capability_map_with_one_stale_marks_only_that_one_failed():
    cap_map, histories = _five_capability_mock_van()
    # Make the solar history stale.
    histories["rc_power_solar_power"] = _stale_samples([120.0])
    results = verify_capability_map(cap_map, histories, _schema())
    assert len(results) == 5
    assert results["rc_power_solar_power"].ok is False
    assert "no fresh data" in results["rc_power_solar_power"].reason
    # The other 4 should still pass.
    for cap_id, res in results.items():
        if cap_id == "rc_power_solar_power":
            continue
        assert res.ok is True, f"{cap_id} should have passed: {res.reason}"


def test_verify_capability_map_with_connection_metadata_applies_restart_check():
    cap_map, histories = _five_capability_mock_van()
    # Pretend the voltage sensor has restarted and not come back.
    now = _now()
    histories["rc_power_battery_voltage"] = [(now - 30, 12.8)]
    meta = {
        "rc_power_battery_voltage": {
            "restart_count": 1,
            "last_disconnect_at": now - 1,  # 1 second ago, AFTER the sample
        }
    }
    results = verify_capability_map(cap_map, histories, _schema(), meta)
    assert results["rc_power_battery_voltage"].ok is False
    assert "didn't come back after the last restart" in (
        results["rc_power_battery_voltage"].reason
    )


def test_verify_capability_map_does_not_raise_on_missing_history():
    cap_map, _ = _five_capability_mock_van()
    # Pass empty histories dict — should produce ok=False for every entry.
    results = verify_capability_map(cap_map, {}, _schema())
    assert len(results) == 5
    for res in results.values():
        assert res.ok is False
        assert res.reason  # has a plain-English reason


def test_verify_capability_map_does_not_mutate_inputs():
    cap_map, histories = _five_capability_mock_van()
    meta = {
        "rc_power_battery_soc": {"restart_count": 0},
    }
    cap_map_snapshot = dict(cap_map)
    histories_snapshot = {k: list(v) for k, v in histories.items()}
    verify_capability_map(cap_map, histories, _schema(), meta)
    assert cap_map == cap_map_snapshot
    assert histories == histories_snapshot


def test_verify_capability_map_raises_typeerror_on_bad_inputs():
    with pytest.raises(TypeError):
        verify_capability_map("not a dict", {}, _schema())  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        verify_capability_map({}, "not a dict", _schema())  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        verify_capability_map({}, {}, "not a dict")  # type: ignore[arg-type]


# ===========================================================================
# rc-entity-naming belt-and-braces guards
# ===========================================================================


def test_assert_rc_prefix_accepts_canonical_ids():
    assert_rc_prefix("rc_power_battery_soc")
    assert_rc_prefix("rc_network_internet_reachable")


def test_assert_rc_prefix_rejects_non_rc_ids():
    for bad in ("power_battery_soc", "rc", "Rcpower", "", "rc_"):
        with pytest.raises(ValueError):
            assert_rc_prefix(bad)


def test_assert_no_vendor_tokens_accepts_clean_ids():
    for good in ("rc_power_battery_soc", "rc_network_internet_reachable", "rc_lighting_interior_state"):
        assert_no_vendor_tokens(good)


def test_assert_no_vendor_tokens_rejects_known_vendors():
    for bad in (
        "rc_power_victron_soc",
        "rc_net_unifi_wan",
        "rc_net_starlink_status",
        "rc_lighting_esphome_switch",
    ):
        with pytest.raises(ValueError):
            assert_no_vendor_tokens(bad)


def test_assert_no_vendor_tokens_uses_vehicle_model_allowlist():
    """Guard against drift between verification.py and vehicle_model.py."""
    forbidden = _verification._load_vehicle_model_allowlist()
    assert forbidden == FORBIDDEN_VENDOR_TOKENS


# ===========================================================================
# Cross-cutting anti-slop: scan every reason / recovery_hint produced by
# the framework for forbidden operator-speak. This is the user-facing
# contract enforcement — the reason and recovery_hint are what the
# vanlifer sees, so they must pass the operator→vanlifer table.
# ===========================================================================


def test_anti_slop_scan_all_framework_strings_pass_translation_table():
    """Run a battery of representative scenarios, collect every reason +
    recovery_hint string the framework produces, and assert none
    contain forbidden operator jargon.
    """
    now = _now()
    base_target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=_fresh_samples([80.0]),
    )

    scenarios = [
        ("baseline_pass", base_target),
        ("range_fail", VerificationTarget(
            capability_id="rc_power_battery_soc",
            entity_id="sensor.vt_battery_soc_percent",
            sample_history=_fresh_samples([150.0]),
        )),
        ("stale_fail", VerificationTarget(
            capability_id="rc_power_battery_soc",
            entity_id="sensor.vt_battery_soc_percent",
            sample_history=_stale_samples([80.0]),
        )),
        ("no_data_fail", VerificationTarget(
            capability_id="rc_power_battery_soc",
            entity_id="sensor.vt_battery_soc_percent",
            sample_history=[],
        )),
        ("jump_fail", VerificationTarget(
            capability_id="rc_power_battery_soc",
            entity_id="sensor.vt_battery_soc_percent",
            sample_history=[(now, 0.0), (now + 1, 100.0)],
        )),
        ("restart_fail", VerificationTarget(
            capability_id="rc_power_battery_soc",
            entity_id="sensor.vt_battery_soc_percent",
            sample_history=[(now - 30, 80.0)],  # fresh, but before disconnect
            connection_metadata={"restart_count": 1, "last_disconnect_at": now - 1},
        )),
        ("vendor_fail", VerificationTarget(
            capability_id="rc_power_battery_soc",
            entity_id="sensor.unifi_random_thing",
            sample_history=_fresh_samples([80.0]),
        )),
    ]

    for name, target in scenarios:
        res = verify_connection(target, _schema())
        assert _is_vanlifery(res.reason), (
            f"scenario {name}: reason contains forbidden jargon: {res.reason!r}"
        )
        assert _is_vanlifery(res.recovery_hint), (
            f"scenario {name}: recovery_hint contains forbidden jargon: "
            f"{res.recovery_hint!r}"
        )


def test_anti_slop_no_module_level_strings_contain_forbidden_tokens():
    """Module docstring + comments may contain jargon (we explain our
    work), but the user-facing public strings — every `reason` and
    every `recovery_hint` — must not. We scan the source for short
    string literals that look like user-facing messages (i.e. start
    with "your " or "no " or "the " or "check " — typical
    sentence-starters for `reason` + `recovery_hint`).
    """
    with open(_VF_PATH, "r", encoding="utf-8") as fp:
        source = fp.read()

    # Pull out string literals (single + triple quoted).
    string_lits: list[str] = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', source)
    string_lits += re.findall(r"'([^'\\]*(?:\\.[^'\\]*)*)'", source)

    # Filter to strings that are user-facing: short, start with a
    # plain-English sentence-starter, and look like a typical
    # `reason` or `recovery_hint` (NOT module docstrings).
    user_facing = []
    for s in string_lits:
        if not s or len(s) > 250:
            # Cap on length excludes module-docstring prose.
            continue
        low = s.lower()
        looks_like_sentence = (
            low.startswith("your ")
            or low.startswith("no ")
            or low.startswith("the ")
            or low.startswith("check ")
            or low.startswith("power-cycle")
            or low.startswith("verified")
        )
        if looks_like_sentence:
            user_facing.append(s)

    for s in user_facing:
        low = s.lower()
        for tok in _FORBIDDEN_OPERATOR_TOKENS:
            assert tok not in low, (
                f"user-facing string contains forbidden operator-speak "
                f"{tok!r}: {s!r}"
            )


# ===========================================================================
# Plain-English shape: every reason string is one clause + starts naturally
# ===========================================================================


def test_reason_strings_start_with_a_verb_or_natural_phrase():
    """A vanlifer-friendly reason starts with a verb ("your device sent")
    or with a clear noun phrase ("no fresh data…"). It does NOT start
    with a code path, an entity_id, or a backtick.
    """
    now = _now()
    targets = [
        # value_in_range fail
        VerificationTarget(
            capability_id="rc_power_battery_soc",
            entity_id="sensor.vt_battery_soc_percent",
            sample_history=_fresh_samples([150.0]),
        ),
        # recent_update fail
        VerificationTarget(
            capability_id="rc_power_battery_soc",
            entity_id="sensor.vt_battery_soc_percent",
            sample_history=_stale_samples([80.0]),
        ),
        # data_plausible fail
        VerificationTarget(
            capability_id="rc_power_battery_soc",
            entity_id="sensor.vt_battery_soc_percent",
            sample_history=[(now, 0.0), (now + 1, 100.0)],
        ),
        # restart_resilience fail
        VerificationTarget(
            capability_id="rc_power_battery_soc",
            entity_id="sensor.vt_battery_soc_percent",
            sample_history=[(now - 30, 80.0)],
            connection_metadata={"restart_count": 1, "last_disconnect_at": now - 1},
        ),
        # vendor_match fail
        VerificationTarget(
            capability_id="rc_power_battery_soc",
            entity_id="sensor.unifi_random_thing",
            sample_history=_fresh_samples([80.0]),
        ),
    ]
    for t in targets:
        res = verify_connection(t, _schema())
        assert res.ok is False
        # Must not start with a backtick, dot, or entity-id-y token.
        assert not res.reason.startswith("`"), res.reason
        assert not res.reason.startswith("."), res.reason
        assert "sensor." not in res.reason.split(" ")[0], res.reason
        # Must be a single sentence (no more than one period-terminated clause).
        assert res.reason.count(".") <= 2, res.reason


def test_recovery_hint_strings_are_short_and_actionable():
    """Recovery hints should be short plain-English instructions."""
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=_stale_samples([80.0]),
    )
    res = verify_connection(target, _schema())
    assert res.recovery_hint is not None
    # 30 words or fewer — short enough for a notification.
    assert len(res.recovery_hint.split()) <= 30, res.recovery_hint
    # Doesn't lead with "run " or "execute " (operator-speak for actions).
    assert not res.recovery_hint.lower().startswith("run "), res.recovery_hint
    assert not res.recovery_hint.lower().startswith("execute "), res.recovery_hint


# ===========================================================================
# Idempotency: verify_connection + verify_capability_map can run repeatedly
# without drift.
# ===========================================================================


def test_verify_connection_is_idempotent():
    """Running the same verification 100x must produce identical output."""
    target = VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=_fresh_samples([80.0, 81.0], step=1),
    )
    first = verify_connection(target, _schema())
    for _ in range(100):
        again = verify_connection(target, _schema())
        assert again.ok == first.ok
        assert again.reason == first.reason
        assert again.recovery_hint == first.recovery_hint
        assert again.checks_run == first.checks_run
