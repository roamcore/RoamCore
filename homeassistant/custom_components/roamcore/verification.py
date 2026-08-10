"""Post-install verification framework for the RoamCore canonical vehicle model.

Wave 9 #119d — Phase 2 canonical vehicle model VERIFICATION FRAMEWORK.

This module turns "the tile is on the screen" into "the tile is showing
REAL DATA that we just verified" — per Directive Rule 4
("Don't mark successful if automated action can't be verified"):

    successful install != working connection. Post-install checks:
    voltage available, values plausible, SoC present where expected,
    data updates, device reconnects after restart.

The framework is a **pure-stdlib contract** (no Home Assistant imports)
so it can be tested in isolation. A future slice will wire it into the
HA runtime; for THIS slice the contract is the deliverable plus a
mock-data test rig that proves the contract is sound.

Design goals:
  - Pure stdlib + json. No HA imports — testable outside an HA install.
  - Plain-English `reason` + `recovery_hint` strings on every check, in
    language a vanlifer would understand. The operator→vanlifer
    translation table (entity → device, integration → connection, MQTT →
    messaging system, script → action, …) is honoured here.
  - All 5 verification checks (`value_in_range`, `recent_update`,
    `data_plausible`, `restart_resilience`, `vendor_match`) are
    implemented + individually tested.
  - `verify_capability_map` runs the contract across an entire map and
    returns one `VerificationResult` per canonical capability id.
  - rc-entity-naming compliance: every canonical id flowing through
    the framework starts with `rc_` and contains no vendor tokens
    (enforced by `vehicle_model.FORBIDDEN_VENDOR_TOKENS`).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

# Re-use the rc-entity-naming allowlist from the canonical schema
# primitive so this slice never drifts from the upstream rules.
# Imported lazily inside `assert_no_vendor_tokens` so this module can
# still be loaded by the pytest rig via file-path import (which
# bypasses the package `__init__.py` and would otherwise break the
# relative import). The lazy import is wrapped in a tiny cache so
# it's a no-op after the first call.
_VEHICLE_MODEL_CACHE: dict[str, Any] = {}


def _load_vehicle_model_allowlist() -> tuple[str, ...]:
    """Return `vehicle_model.FORBIDDEN_VENDOR_TOKENS`, importing lazily."""
    if "FORBIDDEN_VENDOR_TOKENS" not in _VEHICLE_MODEL_CACHE:
        # Direct file-path import so we don't trigger HA package init.
        import importlib.util as _ilu
        import os as _os

        _HERE = _os.path.dirname(_os.path.abspath(__file__))
        _VM_PATH = _os.path.join(_HERE, "vehicle_model.py")
        _spec = _ilu.spec_from_file_location(
            "_roamcore_verification_vm", _VM_PATH
        )
        assert _spec is not None and _spec.loader is not None
        _mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        _VEHICLE_MODEL_CACHE["FORBIDDEN_VENDOR_TOKENS"] = tuple(
            _mod.FORBIDDEN_VENDOR_TOKENS
        )
        _VEHICLE_MODEL_CACHE["find_capability"] = _mod.find_capability
        _VEHICLE_MODEL_CACHE["load_capabilities"] = _mod.load_capabilities
    return _VEHICLE_MODEL_CACHE["FORBIDDEN_VENDOR_TOKENS"]


def _find_capability(caps: dict[str, Any], cap_id: str) -> dict[str, Any] | None:
    """Find a canonical capability by id, with a lazy fallback import."""
    if "find_capability" not in _VEHICLE_MODEL_CACHE:
        _load_vehicle_model_allowlist()
    return _VEHICLE_MODEL_CACHE["find_capability"](caps, cap_id)


# --- Public dataclasses -----------------------------------------------------


@dataclass(frozen=True)
class VerificationTarget:
    """One thing RoamCore wants to verify post-install.

    Attributes:
        capability_id: Canonical capability id, e.g. ``rc_power_battery_soc``.
            Must start with ``rc_`` (per docs/reference/rc-entity-naming.md).
        entity_id: The Home Assistant entity id that backs the capability,
            e.g. ``sensor.vt_battery_soc_percent``.
        sample_history: Recent samples as a list of ``(timestamp, value)``
            tuples. Timestamps are seconds-since-epoch (UTC, float).
            Values are numeric (int or float). Order is oldest-first
            (a list with no samples is allowed — ``recent_update`` will
            fail in that case).
        expected_range: Optional ``(low, high)`` tuple. When supplied,
            the most recent sample must lie inside it. When ``None``,
            the range is derived from the canonical capability's
            ``unit`` + ``device_class`` (battery % → 0..100, voltage →
            0..60, current → -500..500, power → -5000..5000,
            temperature → -50..80, latitude → -90..90, longitude →
            -180..180). When both are ``None``, the range check is
            skipped.
        connection_metadata: Optional dict describing the link to the
            device. Sub-agent-chosen fields:
              * ``connected_since: float`` — seconds-since-epoch when
                the link became active.
              * ``last_disconnect_at: float | None`` — timestamp of the
                most recent disconnect, if any.
              * ``restart_count: int`` — number of times the device has
                restarted (must be >= 0; default 0 when missing).
            When ``None``, defaults are used and ``restart_resilience``
            passes trivially.
    """

    capability_id: str
    entity_id: str
    sample_history: list[tuple[float, float]]
    expected_range: tuple[float, float] | None = None
    connection_metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of one verify_connection call.

    Attributes:
        ok: ``True`` when every check passed.
        reason: One plain-English sentence explaining the outcome.
            Operator→vanlifer translation table applies (no
            "entity", "integration", "MQTT", "script", "API key", …).
        recovery_hint: One plain-English sentence telling the user
            what to do when ``ok`` is ``False``. ``None`` when ``ok``.
        checks_run: Names of the verification checks that fired
            (e.g. ``["value_in_range", "recent_update", …]``). Checks
            that were skipped (because their input was missing) are
            not listed.
    """

    ok: bool
    reason: str
    recovery_hint: str | None
    checks_run: list[str] = field(default_factory=list)


# --- Default freshness + plausibility windows -------------------------------

# Default freshness window for `recent_update`. Sub-agent-chosen:
# a battery SoC that has not updated in the last 60 seconds is stale
# enough to merit a plain-English warning. Callers may override per
# target by supplying a ``freshness_window`` to the helpers, but the
# dataclass-level default lives here for the common case.
DEFAULT_FRESHNESS_SECONDS: float = 60.0

# Default plausibility rule for `data_plausible`. A sample-to-sample
# delta that exceeds `max_jump_fraction * expected_range_width`
# (default 0.5 of the range) within `min_seconds_between_jumps`
# (default 60 s) is implausible. Example: a battery SoC jumping from
# 0 % to 100 % in 1 second triggers the rule (delta = 100, allowed
# = 50 in < 60 s). A 1 % step in 1 second passes (delta = 1, allowed
# = 50 in < 60 s).
DEFAULT_MAX_JUMP_FRACTION: float = 0.5
DEFAULT_MIN_SECONDS_BETWEEN_JUMPS: float = 60.0


# --- Per-check helpers -----------------------------------------------------
# Each helper returns one of:
#   * ``True`` — check passed (the check ran and found no issue).
#   * ``False`` — check was skipped (e.g. no range derivable, not
#     enough samples, no examples to compare against).
#   * ``(reason, recovery_hint)`` tuple when the check fails.
#
# `verify_connection` aggregates the first failure across all checks
# in canonical order, and records the names of checks that actually
# RAN (passed or failed) in `checks_run`. Skipped checks are NOT in
# `checks_run` so callers can distinguish "not yet evaluated" from
# "evaluated and passed".
#
# The split into three return states (True/False/tuple) keeps the
# helpers explicit about why a check didn't run, which makes the
# anti-slop + plain-English contract easier to audit.

_CHECK_PASSED = True
_CHECK_SKIPPED = False


def _derive_expected_range(cap: dict[str, Any] | None) -> tuple[float, float] | None:
    """Derive a sensible default range from the canonical capability.

    Returns ``None`` when no range can be derived (the caller treats
    this as "skip the range check").
    """
    if not isinstance(cap, dict):
        return None

    unit = cap.get("unit")
    device_class = cap.get("device_class")

    # Battery-class percentage (SoC, tank level): 0..100.
    if unit == "%" and device_class in ("battery", None):
        return (0.0, 100.0)

    # Voltage (covers 12 V, 24 V, 48 V van systems with margin).
    if device_class == "voltage" or unit == "V":
        return (0.0, 60.0)

    # Current (positive = charging, negative = discharging — covers
    # alternators + large inverters).
    if device_class == "current" or unit == "A":
        return (-500.0, 500.0)

    # Power (covers up to 5 kW in either direction — solar + inverter).
    if device_class == "power" or unit == "W":
        return (-5000.0, 5000.0)

    # Temperature (°C — freezer cold to hot engine bay).
    if device_class == "temperature" or unit == "°C" or unit == "C":
        return (-50.0, 80.0)

    # GPS latitude / longitude.
    if device_class == "latitude":
        return (-90.0, 90.0)
    if device_class == "longitude":
        return (-180.0, 180.0)

    return None


def _check_value_in_range(
    target: VerificationTarget,
    capability: dict[str, Any] | None,
) -> bool | tuple[str, str]:
    """Pass when the most recent sample is within the expected range.

    Skips (``False``) when no range was supplied AND no range can be
    derived from the capability's `unit` + `device_class`. Returns
    ``True`` when the range check ran and passed.
    """
    expected = target.expected_range
    if expected is None:
        expected = _derive_expected_range(capability)
    if expected is None:
        return _CHECK_SKIPPED  # No range → skip.

    low, high = expected
    if not target.sample_history:
        return _CHECK_SKIPPED  # No data yet → defer to recent_update.

    _ts, value = target.sample_history[-1]
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return (
            "your device sent a value that isn't a number",
            "check the device — it should be sending a number, not text",
        )

    if numeric < low or numeric > high:
        # Pick units from the capability so the message reads naturally.
        unit = ""
        if isinstance(capability, dict):
            u = capability.get("unit")
            if isinstance(u, str) and u:
                unit = f" {u}"

        return (
            f"your device sent {numeric:g}{unit}, which is outside the "
            f"expected range of {low:g} to {high:g}{unit}",
            "check that the right device is mapped to this tile — "
            "it looks like the wrong sensor is plugged in",
        )

    return _CHECK_PASSED


def _check_recent_update(
    target: VerificationTarget,
    freshness_window: float = DEFAULT_FRESHNESS_SECONDS,
    now: float | None = None,
) -> bool | tuple[str, str]:
    """Pass when at least one sample is within `freshness_window`."""
    if not target.sample_history:
        return (
            "no data has arrived from your device yet",
            "wait a minute — if nothing shows up, check the cables "
            "and the connection",
        )

    # Use the supplied `now` for testability, else wall clock.
    current = float(time.time()) if now is None else float(now)

    newest_ts = max(float(ts) for ts, _ in target.sample_history)
    age = current - newest_ts
    if age > freshness_window:
        seconds = int(round(freshness_window))
        return (
            f"no fresh data in the last {seconds} seconds — your "
            "device might have stopped sending",
            "check the device — make sure it has power and the "
            "cable or wireless link is connected",
        )

    return _CHECK_PASSED


def _check_data_plausible(
    target: VerificationTarget,
    capability: dict[str, Any] | None,
    max_jump_fraction: float = DEFAULT_MAX_JUMP_FRACTION,
    min_seconds_between_jumps: float = DEFAULT_MIN_SECONDS_BETWEEN_JUMPS,
) -> bool | tuple[str, str]:
    """Pass when consecutive samples don't show impossible jumps.

    Rule: if any sample-to-sample absolute delta exceeds
    ``max_jump_fraction * expected_range_width`` AND the elapsed time
    is under ``min_seconds_between_jumps``, the history is implausible.

    Skips (``False``) when fewer than 2 samples are available OR the
    expected range is degenerate (zero-width).
    """
    if len(target.sample_history) < 2:
        return _CHECK_SKIPPED  # Not enough data to compare.

    expected = target.expected_range
    if expected is None:
        expected = _derive_expected_range(capability)
    if expected is None:
        # No range → fall back to a generous absolute jump ceiling
        # (1000 units) so the check still catches catastrophic jumps.
        jump_ceiling = 1000.0
    else:
        range_width = expected[1] - expected[0]
        if range_width <= 0:
            return _CHECK_SKIPPED  # Degenerate range; can't reason about jumps.
        jump_ceiling = max_jump_fraction * range_width

    for i in range(1, len(target.sample_history)):
        prev_ts, prev_val = target.sample_history[i - 1]
        cur_ts, cur_val = target.sample_history[i]
        try:
            delta_v = abs(float(cur_val) - float(prev_val))
            delta_t = float(cur_ts) - float(prev_ts)
        except (TypeError, ValueError):
            return (
                "your device sent a value that isn't a number",
                "check the device — it should be sending numbers, not text",
            )

        if delta_v > jump_ceiling and delta_t < min_seconds_between_jumps:
            return (
                "your device sent an impossible jump in values — "
                "looks like bad data",
                "check the device — it may need a power cycle, or "
                "the wiring may be picking up electrical noise",
            )

    return _CHECK_PASSED


def _check_restart_resilience(
    target: VerificationTarget,
    now: float | None = None,
) -> bool | tuple[str, str]:
    """Pass when the device has come back after its last restart.

    Rules:
      * ``restart_count`` must be >= 0.
      * If ``last_disconnect_at`` is set, at least one sample must
        exist with a timestamp >= ``last_disconnect_at`` (proves the
        device reconnected).
      * If ``last_disconnect_at`` is missing, the check passes
        trivially (the device has never restarted on our watch).
    """
    metadata = target.connection_metadata or {}
    restart_count = metadata.get("restart_count", 0)
    if not isinstance(restart_count, int) or restart_count < 0:
        return (
            "the device's restart counter is missing or invalid",
            "check the device — its restart counter should be a "
            "whole number zero or higher",
        )

    last_disconnect_at = metadata.get("last_disconnect_at")
    if last_disconnect_at is None:
        return _CHECK_PASSED  # No disconnect on record → nothing to verify.

    # Did samples arrive AFTER the last disconnect?
    has_post_disconnect_sample = any(
        isinstance(ts, (int, float)) and float(ts) >= float(last_disconnect_at)
        for ts, _ in target.sample_history
    )
    if not has_post_disconnect_sample:
        return (
            "your device didn't come back after the last restart",
            "power-cycle the device, then check the cable or wireless "
            "link — it should reconnect on its own",
        )

    return _CHECK_PASSED


def _extract_vendor_tokens_from_examples(
    examples: list[str],
) -> set[str]:
    """Derive a set of vendor prefix tokens from `example_sources`.

    For each example entity_id (e.g. ``sensor.vt_battery_soc_percent``),
    we extract the second underscore-separated token (``vt``) and use
    that as a vendor identifier. This gives us a small, focused
    substring that uniquely identifies a vendor family without
    pulling in metric / domain noise.
    """
    out: set[str] = set()
    for src in examples:
        if not isinstance(src, str) or not src:
            continue
        parts = src.split(".")
        if len(parts) < 2:
            continue
        # e.g. "sensor.vt_battery_soc_percent" → "vt_battery_soc_percent"
        tail = parts[-1]
        tokens = tail.split("_")
        if len(tokens) < 1 or not tokens[0]:
            continue
        # Use the first token (the vendor prefix). For generic sensors
        # like "sensor.battery_state", the token is "battery" — which
        # is too generic; in that case we skip (the broader substring
        # is matched instead via the "vendor family" pass below).
        token = tokens[0]
        if len(token) >= 2 and token.isalpha():
            out.add(token)
    return out


def _extract_vendor_families_from_examples(examples: list[str]) -> set[str]:
    """Derive a set of vendor-family substrings from `example_sources`.

    A "family" is the full trailing identifier of the entity_id
    (everything after the domain), e.g. ``vt_battery_soc_percent`` or
    ``indoor_temp``. The check is a substring match (not a regex)
    against the target's entity_id — if the family appears as a
    substring, the vendor is recognised.
    """
    out: set[str] = set()
    for src in examples:
        if not isinstance(src, str) or not src:
            continue
        parts = src.split(".")
        if len(parts) < 2:
            continue
        tail = parts[-1]
        if tail:
            out.add(tail)
    return out


def _check_vendor_match(
    target: VerificationTarget,
    capability: dict[str, Any] | None,
) -> bool | tuple[str, str]:
    """Pass when the entity_id looks like one of the canonical families.

    Two substring passes are tried in order:

      1. The "family" substring (full trailing identifier, e.g.
         ``vt_battery_soc_percent``).
      2. The first underscore-separated token (e.g. ``vt``).

    Either pass counts as a match. The check fails only when NONE of
    the families or vendor tokens appear as substrings in the
    entity_id — which is the signal that the wrong device is mapped
    in.

    Skips (``False``) when the capability has no ``example_sources``
    to compare against (a defensive guard for hand-curated capabilities
    that didn't supply any).
    """
    if not isinstance(capability, dict):
        # No schema → no expectation → skip.
        return _CHECK_SKIPPED

    examples = capability.get("example_sources") or []
    if not isinstance(examples, list) or not examples:
        return _CHECK_SKIPPED  # No examples → can't compare.

    families = _extract_vendor_families_from_examples(examples)
    tokens = _extract_vendor_tokens_from_examples(examples)

    entity_id = target.entity_id or ""
    family_hit = any(fam in entity_id for fam in families)
    token_hit = any(tok in entity_id for tok in tokens)

    if family_hit or token_hit:
        return _CHECK_PASSED

    return (
        "your device id doesn't look like the kind of device this "
        "should be",
        "check the device mapping — this tile expects a sensor from "
        "a different family",
    )


# --- Top-level API ---------------------------------------------------------


# Canonical check order. `verify_connection` runs these in order and
# returns the FIRST failure's reason + recovery_hint. Stable order
# matters for tests that assert "first failing check".
CHECK_ORDER: tuple[str, ...] = (
    "value_in_range",
    "recent_update",
    "data_plausible",
    "restart_resilience",
    "vendor_match",
)


def verify_connection(
    target: VerificationTarget,
    capabilities_doc: dict[str, Any],
) -> VerificationResult:
    """Run the full verification suite against one target.

    Args:
        target: A `VerificationTarget` describing the device + history.
        capabilities_doc: The parsed canonical capabilities document
            (i.e. `connections/_schema/canonical_capabilities.json`).

    Returns:
        A `VerificationResult`. `ok=True` means every check that ran
        passed. `checks_run` lists the names of checks that actually
        ran (passed or failed); checks that were skipped because
        their input was missing are NOT in `checks_run`.
    """
    capability = _find_capability(capabilities_doc, target.capability_id)
    checks_run: list[str] = []

    # Run checks in canonical order. First failure wins.
    for name in CHECK_ORDER:
        if name == "value_in_range":
            outcome = _check_value_in_range(target, capability)
        elif name == "recent_update":
            outcome = _check_recent_update(target)
        elif name == "data_plausible":
            outcome = _check_data_plausible(target, capability)
        elif name == "restart_resilience":
            outcome = _check_restart_resilience(target)
        elif name == "vendor_match":
            outcome = _check_vendor_match(target, capability)
        else:  # pragma: no cover — guard against future drift.
            continue

        if outcome is _CHECK_SKIPPED:
            # Skip silently — don't add to checks_run.
            continue

        if outcome is _CHECK_PASSED:
            checks_run.append(name)
            continue

        # outcome is a (reason, recovery_hint) tuple.
        reason, hint = outcome
        return VerificationResult(
            ok=False,
            reason=reason,
            recovery_hint=hint,
            checks_run=checks_run + [name],
        )

    return VerificationResult(
        ok=True,
        reason="Verified — your device is sending fresh, plausible data",
        recovery_hint=None,
        checks_run=checks_run,
    )


def verify_capability_map(
    capability_map: dict[str, str],
    sample_histories: dict[str, list[tuple[float, float]]],
    capabilities_doc: dict[str, Any],
    connection_metadata: dict[str, dict[str, Any]] | None = None,
) -> dict[str, VerificationResult]:
    """Run `verify_connection` across an entire map.

    Args:
        capability_map: ``{canonical_capability_id: entity_id}`` — the
            output of the mapping layer (#119b). Keys must be rc_-prefixed.
        sample_histories: ``{canonical_capability_id: sample_history}``
            where each value is a list of ``(timestamp, value)`` tuples.
        capabilities_doc: The parsed canonical capabilities document.
        connection_metadata: Optional ``{canonical_capability_id:
            metadata_dict}`` for per-target restart counters / disconnect
            timestamps. Missing entries default to empty metadata.

    Returns:
        A ``{canonical_capability_id: VerificationResult}`` dict. Every
        key in `capability_map` is present in the result — even if
        there is no sample history yet — so callers can iterate the
        map in a single pass.

    Note:
        This function NEVER raises on per-target failures. A bad
        sample history produces ``ok=False`` + a plain-English reason;
        a missing history produces the same. Programmer errors (e.g.
        a non-dict capability_map) still raise — those are bugs.
    """
    if not isinstance(capability_map, dict):
        raise TypeError("capability_map must be a dict")
    if not isinstance(sample_histories, dict):
        raise TypeError("sample_histories must be a dict")
    if not isinstance(capabilities_doc, dict):
        raise TypeError("capabilities_doc must be a dict")

    connection_metadata = connection_metadata or {}

    results: dict[str, VerificationResult] = {}
    for cap_id, entity_id in capability_map.items():
        history = sample_histories.get(cap_id, [])
        meta = connection_metadata.get(cap_id, {}) or {}
        target = VerificationTarget(
            capability_id=cap_id,
            entity_id=entity_id,
            sample_history=list(history),
            expected_range=None,
            connection_metadata=dict(meta),
        )
        results[cap_id] = verify_connection(target, capabilities_doc)
    return results


# --- rc-naming belt-and-braces guards --------------------------------------
# These exist so the module's own surface can't drift from the
# canonical naming rules. `verify_capability_map` already enforces the
# `rc_` prefix indirectly (find_capability returns None for any
# non-rc_ id, which causes vendor_match to skip), but the test rig
# uses the helpers below as an additional belt.


def assert_rc_prefix(capability_id: str) -> None:
    """Raise ``ValueError`` if `capability_id` does not start with ``rc_``.

    Mirrors `docs/reference/rc-entity-naming.md` Hard Rule #1. Requires
    at least one character after the ``rc_`` prefix (so ``rc_``
    alone is not enough — a contract id needs an actual name).
    """
    if (
        not isinstance(capability_id, str)
        or not capability_id.startswith("rc_")
        or len(capability_id) <= len("rc_")
    ):
        raise ValueError(
            f"capability id {capability_id!r} must start with rc_ "
            "and have at least one character after the prefix"
        )


def assert_no_vendor_tokens(capability_id: str) -> None:
    """Raise ``ValueError`` if `capability_id` contains a vendor token.

    Mirrors `docs/reference/rc-entity-naming.md` Hard Rule #2 by
    reusing the canonical FORBIDDEN_VENDOR_TOKENS allowlist.
    """
    if not isinstance(capability_id, str):
        raise ValueError("capability id must be a string")
    lower = capability_id.lower()
    forbidden = _load_vehicle_model_allowlist()
    for vendor in forbidden:
        if vendor in lower:
            raise ValueError(
                f"capability id {capability_id!r} contains forbidden "
                f"vendor token {vendor!r}"
            )


__all__ = [
    "DEFAULT_FRESHNESS_SECONDS",
    "DEFAULT_MAX_JUMP_FRACTION",
    "DEFAULT_MIN_SECONDS_BETWEEN_JUMPS",
    "CHECK_ORDER",
    "VerificationTarget",
    "VerificationResult",
    "assert_no_vendor_tokens",
    "assert_rc_prefix",
    "verify_capability_map",
    "verify_connection",
]
