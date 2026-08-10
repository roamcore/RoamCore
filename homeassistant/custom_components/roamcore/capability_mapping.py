"""Vendor-entity → canonical-capability mapping layer (Phase 2 mapping layer).

Wave 9 #119b — the mapping layer sits between the vendor-specific entity
IDs published by integrations (Victron / Renogy / Starlink / Peplink /
Teltonika / generic sensors) and the canonical capability ids in
``connections/_schema/canonical_capabilities.json``.

The schema primitive (commit d5138ed, #119a) defined the canonical
contract; this slice is the translator. Downstream consumers
(dashboard generator #119c, verification framework #119d) read the
mapping this module produces — never the raw vendor entity IDs.

Design goals:
  - Pure stdlib + json (no Home Assistant imports — testable outside an
    HA install).
  - Returns a plain-English `reason` string on a `None` result so the
    caller can decide what to do (skip silently, log, surface a UI
    warning, …) without re-deriving the cause.
  - Naming rules follow ``docs/reference/rc-entity-naming.md``:
      * every canonical id starts with ``rc_``
      * no vendor names (victron, vt_, starlink, …) in any canonical id
  - Functions: ``load_mapping_rules``, ``map_entity_to_capability``,
    ``build_capability_map``, ``unmapped_entities``.

The ``FORBIDDEN_VENDOR_TOKENS`` tuple is re-declared here (rather than
imported from ``vehicle_model.py``) because this module must be
testable in isolation: importing across module boundaries couples two
schema pieces, and the canonical source is documented in the comment
below. If the upstream tuple ever changes, this tuple MUST be updated
in lockstep — the test suite guards both copies.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

# --- Public constants (exported so callers + tests don't hardcode) ---

# Confidence ranks used by ``map_entity_to_capability``. Exact match on a
# mapping rule outranks example_sources match, which outranks a fuzzy
# suffix match.
CONFIDENCE_EXACT_RULE: float = 1.0
CONFIDENCE_EXAMPLE_SOURCE: float = 0.9
CONFIDENCE_FUZZY_SUFFIX: float = 0.6

# A fuzzy match is considered "low confidence" — the dashboard
# generator may render it with a "low confidence" banner or skip it.
LOW_CONFIDENCE_THRESHOLD: float = 0.7

# Above this rank a result is treated as "confident" for inclusion in
# the canonical map produced by ``build_capability_map``.
CONFIDENCE_THRESHOLD: float = 0.7

# Vendor names that must NEVER appear in an ``rc_*`` canonical id.
# Canonical source: ``homeassistant/custom_components/roamcore/vehicle_model.py``
# (the schema validator). Re-declared here so this module can be
# imported in isolation; the test suite cross-checks both copies.
FORBIDDEN_VENDOR_TOKENS: tuple[str, ...] = (
    "victron",
    "vt_",
    "unifi",
    "ubnt",
    "starlink",
    "peplink",
    "teltonika",
    "frigate",
    "mqtt",
    "esphome",
    "homeassistant",
    "hass",
)

# Naming pattern for canonical ids. Mirrors the validator's pattern in
# ``vehicle_model.py`` — at least 2 lowercase tokens after the ``rc_``
# prefix.
_ID_PATTERN = re.compile(r"^rc_[a-z][a-z0-9]*(_[a-z][a-z0-9]*){1,}$")


# --- Public exceptions ---


class AmbiguousMappingError(ValueError):
    """Raised when a vendor entity matches multiple canonical capabilities
    with equal high confidence (≥ 0.9) and we cannot pick a winner.

    The exception carries the ``entity_id`` and the list of competing
    canonical ids so the caller can decide whether to flag the conflict
    in the UI, log it, or surface a setup-wizard warning.
    """


class MappingRuleError(ValueError):
    """Raised by ``load_mapping_rules`` when the rules file is malformed.
    Mirrors the "fail loudly at load time" pattern used by the schema
    validator — a typo in a mapping rule should never silently degrade
    auto-discovery.
    """


# --- Internal helpers ---


def _normalize(entity_id: str) -> str:
    """Lowercase + strip a vendor entity id for case-insensitive matching.

    Home Assistant entity IDs are conventionally lowercase but we don't
    rely on it; canonical mapping is case-insensitive.
    """
    return entity_id.strip().lower()


def _entity_suffix(entity_id: str) -> str:
    """Return the token after the first ``.`` underscore-segment.

    For ``sensor.vt_battery_soc_percent`` returns ``battery``.
    For ``sensor.battery_state`` returns ``battery``.
    For ``binary_sensor.vt_shore_connected`` returns ``shore``.

    Used by the fuzzy suffix match. Falls back to the whole entity id
    when no underscore exists (no sensible suffix to derive).
    """
    # Strip the domain prefix (``sensor.``, ``binary_sensor.``, …).
    if "." in entity_id:
        _, _, rest = entity_id.partition(".")
    else:
        rest = entity_id
    parts = rest.split("_")
    if len(parts) < 2:
        return rest
    # ``vt_battery_soc_percent`` → take the first token after the
    # vendor prefix (``vt_`` → ``battery``). For non-prefixed entities
    # the first token is the suffix.
    if parts[0] in {"vt", "dish", "pep", "rut", "ubnt"} and len(parts) >= 2:
        return parts[1]
    return parts[0]


def _validate_canonical_id(canonical_id: str) -> None:
    """Raise ``MappingRuleError`` if the canonical id violates rc-naming."""
    if not isinstance(canonical_id, str) or not canonical_id:
        raise MappingRuleError(
            f"canonical_id must be a non-empty string (got {canonical_id!r})"
        )
    if not canonical_id.startswith("rc_"):
        raise MappingRuleError(
            f"canonical_id {canonical_id!r} must start with the rc_ prefix"
        )
    if not _ID_PATTERN.match(canonical_id):
        raise MappingRuleError(
            f"canonical_id {canonical_id!r} does not match the rc-naming "
            "pattern rc_<subsystem>_<object>_<metric>"
        )
    lower = canonical_id.lower()
    for vendor in FORBIDDEN_VENDOR_TOKENS:
        if vendor in lower:
            raise MappingRuleError(
                f"canonical_id {canonical_id!r} contains forbidden vendor "
                f"token {vendor!r}"
            )


# --- Public API ---


def load_mapping_rules(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Read + JSON-parse the optional mapping rules file.

    The file shape is::

        {
          "rules": [
            {
              "vendor_entity_id_pattern": "sensor.vt_battery_soc_percent",
              "canonical_id": "rc_power_battery_soc"
            },
            ...
          ]
        }

    Returns the full document (so callers can introspect the rules
    list and any future top-level metadata).

    Raises:
        FileNotFoundError: when the path does not exist. Callers that
            treat the rules file as optional should ``try`` / ``except``
            and fall through to the schema's ``example_sources`` list.
        json.JSONDecodeError: when the file is not valid JSON.
        MappingRuleError: when the document shape is wrong (top-level
            is not a dict, has no ``rules`` key, a rule is missing one
            of the required keys, or the ``canonical_id`` violates
            rc-naming).
    """
    with open(path, "r", encoding="utf-8") as fp:
        doc = json.load(fp)

    if not isinstance(doc, dict):
        raise MappingRuleError(
            "mapping rules document must be a JSON object at the top level"
        )

    rules = doc.get("rules")
    if not isinstance(rules, list):
        raise MappingRuleError(
            "mapping rules document must contain a 'rules' list"
        )

    # Validate every rule at load time so the runtime mapper never sees
    # a malformed rule.
    for idx, rule in enumerate(rules):
        prefix = f"rules[{idx}]"
        if not isinstance(rule, dict):
            raise MappingRuleError(
                f"{prefix}: must be a JSON object"
            )
        pattern = rule.get("vendor_entity_id_pattern")
        canonical_id = rule.get("canonical_id")
        if not isinstance(pattern, str) or not pattern:
            raise MappingRuleError(
                f"{prefix}: missing or empty 'vendor_entity_id_pattern'"
            )
        if not isinstance(canonical_id, str) or not canonical_id:
            raise MappingRuleError(
                f"{prefix}: missing or empty 'canonical_id'"
            )
        _validate_canonical_id(canonical_id)

    return doc


def _index_example_sources(capabilities_doc: dict[str, Any]) -> dict[str, str]:
    """Build a `{vendor_entity_id: canonical_id}` lookup from the
    canonical schema's ``example_sources`` lists.

    Each entry maps a single vendor entity id (from a capability's
    ``example_sources`` array) to the canonical id of the capability
    it belongs to. The schema is data — multiple capabilities may
    legitimately reference the same example source — so when an entity
    is listed under more than one capability the LATER occurrence wins
    (deterministic by document order; ties resolved by first occurrence
    kept, subsequent duplicates ignored). In practice the shipped
    schema has no duplicates; the deterministic choice protects future
    editors from silent ambiguity.
    """
    index: dict[str, str] = {}
    for cap in capabilities_doc.get("capabilities") or []:
        if not isinstance(cap, dict):
            continue
        canonical_id = cap.get("id")
        if not isinstance(canonical_id, str) or not canonical_id:
            continue
        for source in cap.get("example_sources") or []:
            if not isinstance(source, str) or not source:
                continue
            key = _normalize(source)
            # First write wins — keeps the index deterministic.
            index.setdefault(key, canonical_id)
    return index


def map_entity_to_capability(
    entity_id: str,
    mapping_rules: dict[str, Any],
    capabilities_doc: dict[str, Any],
) -> tuple[str | None, dict[str, Any]]:
    """Map a single vendor entity id to a canonical capability id.

    Returns a ``(canonical_id, info)`` tuple:

      - ``canonical_id`` is the canonical id string when a confident
        mapping exists, or ``None`` when no mapping is found (with a
        ``reason`` string in ``info`` explaining why).
      - ``info`` is a dict with at least:
            * ``confidence`` (float in [0.0, 1.0])
            * ``low_confidence`` (bool, True when confidence is below
              ``LOW_CONFIDENCE_THRESHOLD``)
            * ``reason`` (plain-English string, always present)

    Confidence ranking:
      1. Exact match on a mapping rule's ``vendor_entity_id_pattern``
         (case-insensitive full-string match) → 1.0.
      2. Match on a canonical capability's ``example_sources`` entry
         (exact, case-insensitive) → 0.9.
      3. Fuzzy match on the suffix after the vendor prefix
         (``battery`` → any ``rc_power_battery_*``) → 0.6, flagged
         ``low_confidence=True``.

    Raises:
        AmbiguousMappingError: when two different rules match with
            equal confidence ≥ 0.9 and there is no deterministic way
            to pick a winner.

    The function never returns an ``rc_*`` id that violates rc-naming
    (the rules file is validated at load time and the example_sources
    index is built only from capabilities whose ``id`` is already
    validator-checked by ``vehicle_model.py``).
    """
    if not isinstance(entity_id, str) or not entity_id:
        raise ValueError(
            f"entity_id must be a non-empty string (got {entity_id!r})"
        )
    if not isinstance(capabilities_doc, dict):
        raise ValueError("capabilities_doc must be a JSON object (dict)")

    entity_norm = _normalize(entity_id)
    info: dict[str, Any] = {
        "confidence": 0.0,
        "low_confidence": True,
        "reason": "",
    }

    # --- 1. Exact rule match ---
    rule_hits: list[str] = []
    for rule in mapping_rules.get("rules") or []:
        if not isinstance(rule, dict):
            continue
        pattern = rule.get("vendor_entity_id_pattern")
        canonical_id = rule.get("canonical_id")
        if not isinstance(pattern, str) or not isinstance(canonical_id, str):
            continue
        if _normalize(pattern) == entity_norm:
            rule_hits.append(canonical_id)

    if rule_hits:
        unique = sorted(set(rule_hits))
        if len(unique) > 1:
            raise AmbiguousMappingError(
                f"entity_id {entity_id!r} matches multiple canonical ids "
                f"with equal confidence: {unique}"
            )
        info["confidence"] = CONFIDENCE_EXACT_RULE
        info["low_confidence"] = False
        info["reason"] = "exact match on mapping rule"
        return unique[0], info

    # --- 2. example_sources match ---
    example_index = _index_example_sources(capabilities_doc)
    if entity_norm in example_index:
        canonical_id = example_index[entity_norm]
        info["confidence"] = CONFIDENCE_EXAMPLE_SOURCE
        info["low_confidence"] = False
        info["reason"] = "matched the canonical schema's example_sources"
        return canonical_id, info

    # --- 3. Fuzzy suffix match ---
    suffix = _entity_suffix(entity_norm)
    fuzzy_hits: list[str] = []
    for cap in capabilities_doc.get("capabilities") or []:
        if not isinstance(cap, dict):
            continue
        canonical_id = cap.get("id")
        if not isinstance(canonical_id, str):
            continue
        # We match against the 2nd token of the canonical id
        # (``rc_<subsystem>_<object>_<metric>``), so a vendor entity
        # whose suffix is ``battery`` matches ``rc_power_battery_soc``
        # but not ``rc_water_fresh_level`` (whose second token is
        # ``water``).
        parts = canonical_id.split("_")
        if len(parts) >= 3 and parts[2] == suffix:
            fuzzy_hits.append(canonical_id)

    if fuzzy_hits:
        # Fuzzy matches are flagged low-confidence — the dashboard
        # generator may render them with a warning banner or skip
        # them. Multiple fuzzy hits are not an ambiguity error: the
        # confidence is so low that any of them is suspect, so we
        # surface them as None and report the candidates in reason so
        # the caller can decide whether to nudge the user toward
        # configuring an explicit rule.
        info["confidence"] = CONFIDENCE_FUZZY_SUFFIX
        info["low_confidence"] = True
        info["reason"] = (
            f"no exact match; fuzzy suffix {suffix!r} matches "
            f"{fuzzy_hits!r} but confidence is low"
        )
        info["candidates"] = sorted(set(fuzzy_hits))
        return None, info

    info["reason"] = f"no mapping rule, example_source, or fuzzy suffix hit for {entity_id!r}"
    return None, info


def build_capability_map(
    entities: dict[str, dict[str, Any]],
    mapping_rules: dict[str, Any],
    capabilities_doc: dict[str, Any],
) -> dict[str, str]:
    """Return ``{canonical_id: vendor_entity_id}`` for every vendor entity
    that mapped confidently (confidence ≥ ``CONFIDENCE_THRESHOLD``).

    The result is deterministic: when two vendor entities both map to
    the same canonical id (rare but legitimate — the mapping layer
    doesn't know which is "primary"), the alphabetical-first vendor
    entity id wins so the output is reproducible across runs.

    Entities whose mapping is low-confidence (fuzzy suffix match) or
    absent are silently dropped — use ``unmapped_entities`` to recover
    them.

    Ambiguous matches (≥ 2 rules with equal confidence ≥ 0.9) are
    caught here and raised as ``AmbiguousMappingError`` so a setup
    error never produces a silent winner.
    """
    if not isinstance(entities, dict):
        raise ValueError("entities must be a dict of {entity_id: attributes}")

    candidate: dict[str, str] = {}

    for entity_id in sorted(entities.keys()):
        canonical_id, info = map_entity_to_capability(
            entity_id, mapping_rules, capabilities_doc
        )
        if canonical_id is None:
            continue
        if info["confidence"] < CONFIDENCE_THRESHOLD:
            continue
        # Alphabetical tie-break: only overwrite when the new vendor
        # entity id sorts before the existing one.
        existing = candidate.get(canonical_id)
        if existing is None or entity_id < existing:
            candidate[canonical_id] = entity_id

    return candidate


def unmapped_entities(
    entities: dict[str, dict[str, Any]],
    mapping_rules: dict[str, Any],
    capabilities_doc: dict[str, Any],
) -> list[str]:
    """Return the vendor entity ids that did NOT map confidently.

    The returned list is sorted alphabetically for stable test output.
    Includes both "no mapping found at all" and "fuzzy low-confidence
    match only" — both cases deserve operator attention.
    """
    if not isinstance(entities, dict):
        raise ValueError("entities must be a dict of {entity_id: attributes}")

    canonical_map = build_capability_map(entities, mapping_rules, capabilities_doc)
    mapped_vendor_ids = set(canonical_map.values())

    leftover: list[str] = []
    for entity_id in sorted(entities.keys()):
        if entity_id in mapped_vendor_ids:
            continue
        leftover.append(entity_id)
    return leftover