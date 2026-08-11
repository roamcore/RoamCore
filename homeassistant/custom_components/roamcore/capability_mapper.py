"""Pure-Python capability mapper for the RoamCore canonical vehicle model.

Phase 2 (Wave 9 #119.b) — the capability mapping layer turns raw
Home Assistant entity_ids into the canonical RoamCore capability ids
defined in `connections/_schema/canonical_capabilities.json`. The
mapping is declarative (`connections/_schema/mapping_rules.json`) and
this module is the pure-Python engine that applies it.

Design goals (doctrine: must-not-fail + super-intuitive + critical
infrastructure, Bernard 2026-08-04):
  * Pure stdlib + json (NO Home Assistant runtime imports — keep this
    importable in tests outside an HA install, same as vehicle_model).
  * Idempotent: same input → same output, every time. No randomness,
    no network calls, no clock-dependence.
  * Auto-recover on unknown entity_ids: never crash the dashboard.
    Return None + log to a per-call log; callers surface a tile-readable
    string ("I couldn't figure out where this device belongs — check
    the setup wizard") instead of a stack trace.
  * Plain-English errors: validation errors are returned as a list of
    human-readable strings (empty list = valid), mirroring the
    vehicle_model.validate_capabilities contract.
  * Naming follows `docs/reference/rc-entity-naming.md`: the
    `canonical_capability` field must start with `rc_`.
  * Higher weight wins on conflicts, deterministic tie-break by
    rule_id (alphabetical).
  * Functions: load_mapping_rules, load_capability_schema,
    resolve_entity_to_capability, map_entities, apply_mapping_rules,
    validate_mapping_rules, _confidence_from_weight.

How matching works:
  * Every rule's `source_pattern` is a Python regex (NOT a glob).
    We use re.fullmatch against the entity_id (which is a plain
    ASCII string like "sensor.vt_battery_soc_percent").
  * On a single entity_id, every rule is tried in turn. Matching
    rules are collected, sorted by (-weight, rule_id), and the
    winner becomes the resolved capability. Confidence is computed
    as weight / 100 (so 0..1, mapped to 0.0..1.0 float).
  * If no rule matches, resolve returns None and the caller records
    the entity in the unmatched list. The dashboard surfaces a
    user-friendly fallback ("I couldn't figure out where this
    device belongs") for those.

Backwards compatibility with vehicle_model.py:
  * This module does NOT re-implement the canonical_capabilities
    validator. It imports `vehicle_model.load_capabilities` /
    `validate_capabilities` and uses the schema as the ground truth
    for `validate_mapping_rules` and `apply_mapping_rules`.
  * vehicle_model.py stays untouched (slice contract: minimal +
    additive only).
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Iterable

# --- Public constants (exported so callers + tests don't hardcode) ---

# Where the mapping rules file lives by default. Overridable per-call.
DEFAULT_MAPPING_RULES_PATH = "connections/_schema/mapping_rules.json"

# Weight floor / ceiling. weight ∈ [0, 100]; confidence = weight / 100.
WEIGHT_MIN: int = 0
WEIGHT_MAX: int = 100

# The rc_ prefix is mandatory for every canonical_capability reference.
# This duplicates vehicle_model.py's check on purpose — the mapper has
# to enforce it independently because the rule file is its own input.
_CONTRACT_PREFIX = "rc_"


# --- Loaders ---


def load_mapping_rules(
    path: str | os.PathLike[str] = DEFAULT_MAPPING_RULES_PATH,
) -> dict[str, Any]:
    """Read + JSON-parse the mapping rules file.

    Returns the full document (so callers can read `version` / `title`
    / `description` as well as the per-rule entries).

    Raises:
        FileNotFoundError: when `path` does not exist.
        json.JSONDecodeError: when the file is not valid JSON.
    """
    with open(path, "r", encoding="utf-8") as fp:
        return json.load(fp)


def load_capability_schema(
    path: str | os.PathLike[str] = "connections/_schema/canonical_capabilities.json",
) -> dict[str, Any]:
    """Load the canonical capabilities schema.

    Thin wrapper around `vehicle_model.load_capabilities` so callers
    that already imported the mapper don't have to import
    vehicle_model separately. The canonical_capabilities.json schema
    is the ground truth for `validate_mapping_rules`.

    Raises:
        FileNotFoundError: when `path` does not exist.
        json.JSONDecodeError: when the file is not valid JSON.
    """
    # Lazy import to keep `capability_mapper` importable without a
    # parent-package collision (the conftest patches the parent
    # `homeassistant.custom_components.roamcore` package; a top-level
    # `from .vehicle_model import load_capabilities` would crash on
    # collection). Loading by absolute path avoids the package
    # machinery entirely, exactly like test_vehicle_model.py does.
    import importlib.util

    _HERE = os.path.dirname(os.path.abspath(__file__))
    _VM_PATH = os.path.join(_HERE, "vehicle_model.py")
    _spec = importlib.util.spec_from_file_location(
        "roamcore_vehicle_model_lazy", _VM_PATH
    )
    if _spec is None or _spec.loader is None:
        raise ImportError(
            f"vehicle_model.py not loadable from {_VM_PATH!r}"
        )
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    return _mod.load_capabilities(path)


# --- Validation ---


def validate_mapping_rules(
    rules_doc: dict[str, Any],
    schema: dict[str, Any],
) -> list[str]:
    """Return a list of plain-English validation errors for the rules.

    Empty list means the rules doc is valid. Function is deliberately
    total (never raises) so callers can aggregate errors across many
    documents without try/except noise. Same contract as
    vehicle_model.validate_capabilities.

    Checks performed:
      1. Top-level shape (`rules` is a non-empty list, optional
         `version` is an int).
      2. Every rule has the 5 required keys (id, source_pattern,
         canonical_capability, weight, description).
      3. Every `canonical_capability` value exists in `schema`'s
         `capabilities` list (so a typo doesn't silently map into
         the void).
      4. Every `canonical_capability` starts with `rc_`.
      5. Every `weight` is an int in [0, 100].
      6. Every `source_pattern` compiles as a valid Python regex.
      7. Every `id` is unique (duplicate rule ids = silent override).
      8. Every `id` and `canonical_capability` is a non-empty string.
      9. `description` is a non-empty string when present.
    """
    errors: list[str] = []

    if not isinstance(rules_doc, dict):
        return ["top-level document must be a JSON object"]

    version = rules_doc.get("version")
    if version is not None and not isinstance(version, int):
        errors.append(
            f"'version' must be an integer when present (got {type(version).__name__})"
        )

    rules = rules_doc.get("rules")
    if not isinstance(rules, list) or not rules:
        errors.append("'rules' must be a non-empty list")
        return errors

    # Build the set of valid canonical_capability ids from the schema.
    capabilities = schema.get("capabilities") if isinstance(schema, dict) else None
    if not isinstance(capabilities, list) or not capabilities:
        errors.append(
            "schema has no 'capabilities' list — cannot validate rule targets"
        )
        valid_cap_ids: set[str] = set()
    else:
        valid_cap_ids = {
            c.get("id")
            for c in capabilities
            if isinstance(c, dict) and isinstance(c.get("id"), str)
        }

    seen_rule_ids: set[str] = set()
    required_keys = {
        "id",
        "source_pattern",
        "canonical_capability",
        "weight",
    }

    for idx, rule in enumerate(rules):
        prefix = f"rules[{idx}]"

        if not isinstance(rule, dict):
            errors.append(f"{prefix}: must be a JSON object")
            continue

        # Required keys.
        missing = required_keys - set(rule.keys())
        if missing:
            errors.append(
                f"{prefix}: missing required keys {sorted(missing)}"
            )
            # Continue with what we can check — partial validation is
            # better than swallowing the rest.

        # id.
        rule_id = rule.get("id")
        if not isinstance(rule_id, str) or not rule_id:
            errors.append(f"{prefix}.id: must be a non-empty string")
        elif rule_id in seen_rule_ids:
            errors.append(
                f"{prefix}.id ({rule_id!r}): duplicate rule id "
                "(every id must be unique)"
            )
        else:
            seen_rule_ids.add(rule_id)

        # source_pattern must be a compilable regex.
        source_pattern = rule.get("source_pattern")
        if not isinstance(source_pattern, str) or not source_pattern:
            errors.append(
                f"{prefix}.source_pattern: must be a non-empty string"
            )
        else:
            try:
                re.compile(source_pattern)
            except re.error as exc:
                errors.append(
                    f"{prefix}.source_pattern ({source_pattern!r}): "
                    f"invalid regex ({exc})"
                )

        # canonical_capability must be rc_-prefixed and present in schema.
        cap = rule.get("canonical_capability")
        if not isinstance(cap, str) or not cap:
            errors.append(
                f"{prefix}.canonical_capability: must be a non-empty string"
            )
        elif not cap.startswith(_CONTRACT_PREFIX):
            errors.append(
                f"{prefix}.canonical_capability ({cap!r}): must start "
                f"with the {(_CONTRACT_PREFIX + '_')!r} prefix (rc-naming "
                "contract — see docs/reference/rc-entity-naming.md)"
            )
        elif valid_cap_ids and cap not in valid_cap_ids:
            errors.append(
                f"{prefix}.canonical_capability ({cap!r}): not declared "
                "in canonical_capabilities.json (add it to the schema, "
                "or fix the typo)"
            )

        # weight must be an int in [0, 100].
        weight = rule.get("weight")
        if not isinstance(weight, int) or isinstance(weight, bool):
            errors.append(
                f"{prefix}.weight ({weight!r}): must be an integer in "
                f"[{WEIGHT_MIN}, {WEIGHT_MAX}]"
            )
        elif not (WEIGHT_MIN <= weight <= WEIGHT_MAX):
            errors.append(
                f"{prefix}.weight ({weight}): out of range "
                f"[{WEIGHT_MIN}, {WEIGHT_MAX}]"
            )

        # description (optional but, when present, must be a non-empty string).
        description = rule.get("description")
        if description is not None and (
            not isinstance(description, str) or not description.strip()
        ):
            errors.append(
                f"{prefix}.description: must be a non-empty string when present"
            )

    return errors


# --- Resolution ---


def _confidence_from_weight(weight: int) -> float:
    """Map a rule's weight (0..100) to a confidence score (0.0..1.0).

    The mapping is monotonic and total. Clamps out-of-range weights to
    [0.0, 1.0] so a malformed rule that slipped past validation still
    produces a sensible confidence score.
    """
    clamped = max(WEIGHT_MIN, min(WEIGHT_MAX, int(weight)))
    return clamped / float(WEIGHT_MAX)


def _compile_rules(
    rules_doc: dict[str, Any],
) -> list[tuple[dict[str, Any], re.Pattern[str]]]:
    """Internal: compile every rule's source_pattern once.

    Returns a list of (rule, compiled_regex) tuples in the rule's
    declared order. Patterns that fail to compile are skipped silently
    here — the caller is expected to run `validate_mapping_rules`
    first. We don't raise because the resolver must be total
    (auto-recover doctrine).
    """
    out: list[tuple[dict[str, Any], re.Pattern[str]]] = []
    rules = rules_doc.get("rules") if isinstance(rules_doc, dict) else None
    if not isinstance(rules, list):
        return out
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        pattern = rule.get("source_pattern")
        if not isinstance(pattern, str) or not pattern:
            continue
        try:
            compiled = re.compile(pattern)
        except re.error:
            continue
        out.append((rule, compiled))
    return out


def resolve_entity_to_capability(
    entity_id: str,
    *,
    rules: dict[str, Any] | None = None,
    schema: dict[str, Any] | None = None,
) -> tuple[str, str, float] | None:
    """Resolve a single entity_id to a canonical capability.

    Args:
        entity_id: The raw HA entity_id (e.g.
            "sensor.vt_battery_soc_percent").
        rules: Pre-loaded mapping rules doc (skips the file read).
            If None, the mapper does NOT auto-load the file — the
            test suite always passes an explicit `rules` so the
            resolver stays side-effect-free.
        schema: Unused on the hot path; accepted for API symmetry
            with `apply_mapping_rules`. Kept in the signature so
            callers don't have to branch.

    Returns:
        A (capability_id, matched_rule_id, confidence) tuple on a
        hit, or None when no rule matches.

    Determinism guarantee: on conflicts, the highest-weight rule
    wins. Ties are broken alphabetically by rule_id (stable).
    """
    if rules is None:
        return None
    if not isinstance(entity_id, str) or not entity_id:
        return None

    compiled = _compile_rules(rules)
    matches: list[tuple[int, str, str]] = []
    for rule, regex in compiled:
        if regex.fullmatch(entity_id):
            weight = rule.get("weight")
            if not isinstance(weight, int) or isinstance(weight, bool):
                continue
            cap = rule.get("canonical_capability")
            rid = rule.get("id")
            if not isinstance(cap, str) or not isinstance(rid, str):
                continue
            matches.append((weight, rid, cap))

    if not matches:
        return None

    # Highest weight first, then alphabetical rule_id for stability.
    matches.sort(key=lambda m: (-m[0], m[1]))
    winning_weight, winning_id, winning_cap = matches[0]
    return (winning_cap, winning_id, _confidence_from_weight(winning_weight))


def map_entities(
    entities: Iterable[str],
    *,
    rules: dict[str, Any] | None = None,
    schema: dict[str, Any] | None = None,
) -> dict[str, str | None]:
    """Map a collection of entity_ids to canonical capabilities.

    Returns a dict mapping `entity_id → capability_id | None`. The
    first entity that maps to a given canonical_capability wins
    (idempotent, deterministic — entities are processed in iteration
    order; the resolver picks the highest-weight rule per entity).

    Use this for "give me the dashboard layout" — every canonical
    capability gets exactly one source entity, picked deterministically.

    If you want the unmatched list too, call `apply_mapping_rules`
    directly.
    """
    if rules is None:
        rules = {}
    if schema is None:
        schema = {}

    out: dict[str, str | None] = {}
    seen_caps: set[str] = set()

    for entity_id in entities:
        if not isinstance(entity_id, str) or not entity_id:
            continue
        result = resolve_entity_to_capability(
            entity_id, rules=rules, schema=schema
        )
        if result is None:
            out[entity_id] = None
            continue
        cap_id, _rule_id, _conf = result
        # First entity wins for each canonical capability.
        if cap_id in seen_caps:
            out[entity_id] = None  # duplicate source — skip
            continue
        seen_caps.add(cap_id)
        out[entity_id] = cap_id

    return out


def apply_mapping_rules(
    raw_entities: Iterable[str],
    rules: dict[str, Any],
    schema: dict[str, Any],
) -> tuple[dict[str, str | None], list[str]]:
    """Apply mapping rules to a collection of raw entity_ids.

    Returns a tuple of:
      * mapping: entity_id → capability_id | None (deterministic,
        first-entity-wins per capability).
      * unmatched: list of entity_ids that no rule resolved.

    The caller is expected to display the unmatched list as a
    tile-readable string ("I couldn't figure out where this device
    belongs — check the setup wizard") rather than raise.
    """
    mapping = map_entities(raw_entities, rules=rules, schema=schema)
    unmatched = [eid for eid, cap in mapping.items() if cap is None]
    return mapping, unmatched
