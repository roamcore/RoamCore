"""Tests for the capability mapping layer (Phase 2 / Wave 9 #119.b).

The mapping layer turns raw Home Assistant entity_ids into the
canonical RoamCore capability ids declared in
`connections/_schema/canonical_capabilities.json`. The rules live at
`connections/_schema/mapping_rules.json` and are consumed by the
pure-Python mapper at
`homeassistant/custom_components/roamcore/capability_mapper.py`.

Tests are pure stdlib — no Home Assistant imports — so they can run
in any CI rig that already runs the rest of the RoamCore test suite.
The same conftest.py trick (parent-package stubbing) used by
test_vehicle_model.py is in place, so the test file is collected
without dragging in the real `homeassistant.custom_components.roamcore`
package.

Doctrinal invariants verified here (Bernard 2026-08-04):
  * Auto-recover: unknown entity_ids resolve to None + the unmatched
    list (never a crash).
  * Idempotent: same input → same output, every time (1k-call sweep).
  * rc-naming: every rule's canonical_capability starts with `rc_`.
  * Cross-cutting: every rule targets a real canonical_capability id.
  * Conflict resolution: highest-weight rule wins; alphabetical
    tie-break.
  * Validation rejects broken rules (bad regex, weight out of range,
    typo in capability id).
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys

import pytest

# --- Load the module under test by absolute file path ---
#
# Pytest auto-imports the parent
# `homeassistant/custom_components/roamcore/__init__.py` when the test
# file lives inside that package, which requires the HA runtime.
# Loading by file path bypasses that import entirely. Same pattern as
# test_vehicle_model.py.

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
_CC_DIR = os.path.join(_REPO_ROOT, "homeassistant", "custom_components", "roamcore")
_CM_PATH = os.path.join(_CC_DIR, "capability_mapper.py")

_spec = importlib.util.spec_from_file_location(
    "roamcore_capability_mapper", _CM_PATH
)
assert _spec is not None and _spec.loader is not None, (
    "capability_mapper.py not loadable"
)
_capability_mapper = importlib.util.module_from_spec(_spec)
sys.modules["roamcore_capability_mapper"] = _capability_mapper
_spec.loader.exec_module(_capability_mapper)

apply_mapping_rules = _capability_mapper.apply_mapping_rules
load_capability_schema = _capability_mapper.load_capability_schema
load_mapping_rules = _capability_mapper.load_mapping_rules
map_entities = _capability_mapper.map_entities
resolve_entity_to_capability = _capability_mapper.resolve_entity_to_capability
validate_mapping_rules = _capability_mapper.validate_mapping_rules

MAPPING_RULES_PATH = os.path.join(
    _REPO_ROOT, "connections", "_schema", "mapping_rules.json"
)
SCHEMA_PATH = os.path.join(
    _REPO_ROOT, "connections", "_schema", "canonical_capabilities.json"
)


# --- Fixtures ---


@pytest.fixture(scope="module")
def rules_doc() -> dict:
    return load_mapping_rules(MAPPING_RULES_PATH)


@pytest.fixture(scope="module")
def schema_doc() -> dict:
    return load_capability_schema(SCHEMA_PATH)


@pytest.fixture(scope="module")
def valid_capability_ids(schema_doc: dict) -> set[str]:
    return {
        c["id"]
        for c in schema_doc["capabilities"]
        if isinstance(c, dict) and isinstance(c.get("id"), str)
    }


# A curated 50-entity real-world fixture covering every canonical
# category + the matching rules. Used by the "full real-world
# mapping" test below. Ordered so the first entity for each canonical
# capability is the one we expect to win (first-entity-wins +
# highest-weight tie-break).
REAL_WORLD_ENTITIES: list[str] = [
    # --- power (battery / solar / shore) ---
    "sensor.vt_battery_soc_percent",            # canonical: rc_power_battery_soc (weight 95, identity later in list at weight 100)
    "sensor.victron_smartshunt_battery_voltage", # canonical: rc_power_battery_voltage
    "sensor.vt_battery_current_a",              # canonical: rc_power_battery_current
    "sensor.vt_solar_power_w",                  # canonical: rc_power_solar_power
    "binary_sensor.vt_shore_connected",         # canonical: rc_power_shore_connected
    # --- lighting (interior + approach) ---
    "switch.cabin_main",                        # canonical: rc_lighting_interior_state
    "switch.porch_light",                       # canonical: rc_lighting_approach_state
    # --- climate (indoor temp + hvac) ---
    "sensor.indoor_temp",                       # canonical: rc_climate_indoor_temperature
    "switch.hvac_main",                         # canonical: rc_climate_hvac_state
    # --- water (fresh + pump) ---
    "sensor.fresh_water_tank_level",            # canonical: rc_water_fresh_level
    "switch.water_pump",                        # canonical: rc_water_pump_state
    # --- position (lat + lon) ---
    "device_tracker.vt_vehicle",                # canonical: rc_position_lat
    "sensor.vehicle_lon",                       # canonical: rc_position_lon
    # --- network (internet + wan ip) ---
    "binary_sensor.rc_net_internet_reachable",  # canonical: rc_network_internet_reachable
    "sensor.rc_net_wan_ip",                     # canonical: rc_network_wan_ip
    # --- self-mapping canonical tiles (would normally come last so they
    #     never win against a higher-priority vendor mapping) ---
    "sensor.rc_power_battery_soc",
    "sensor.rc_power_battery_voltage",
    "sensor.rc_power_battery_current",
    "sensor.rc_power_solar_power",
    "binary_sensor.rc_power_shore_connected",
    "switch.rc_lighting_interior_state",
    "switch.rc_lighting_approach_state",
    "sensor.rc_climate_indoor_temperature",
    "switch.rc_climate_hvac_state",
    "sensor.rc_water_fresh_level",
    "switch.rc_water_pump_state",
    "sensor.rc_position_lat",
    "sensor.rc_position_lon",
    "binary_sensor.rc_network_internet_reachable",
    "sensor.rc_network_wan_ip",
    # --- additional vendor variants (Renogy, generic) ---
    "sensor.renogy_ranger_battery_soc",         # canonical: rc_power_battery_soc (already taken by vt_battery_soc)
    "sensor.renogy_solar_power_w",              # canonical: rc_power_solar_power (already taken)
    "sensor.generic_battery_state_of_charge",   # canonical: rc_power_battery_soc (already taken)
    "sensor.generic_solar_panel_power",         # canonical: rc_power_solar_power (already taken)
    "binary_sensor.shore_power_connected",      # canonical: rc_power_shore_connected (already taken)
    "switch.cabin_lights_zone_2",               # canonical: rc_lighting_interior_state (already taken)
    "switch.awning_light_zone_a",               # canonical: rc_lighting_approach_state (already taken)
    "sensor.cabin_temperature",                 # canonical: rc_climate_indoor_temperature (already taken)
    "switch.webasto_heater",                    # canonical: rc_climate_hvac_state (already taken)
    "sensor.potable_water_tank",                # canonical: rc_water_fresh_level (already taken)
    "switch.shurflo_pump",                      # canonical: rc_water_pump_state (already taken)
    "sensor.gps_lat",                           # canonical: rc_position_lat (already taken)
    "sensor.gps_lon",                           # canonical: rc_position_lon (already taken)
    "binary_sensor.internet_reachable",         # canonical: rc_network_internet_reachable (already taken)
    "sensor.wan_ip",                            # canonical: rc_network_wan_ip (already taken)
    # --- 2 deliberately unmatched entities (auto-recover path) ---
    "sensor.weather_forecast",
    "binary_sensor.front_door_lock",
]


# --- Loaders ---


def test_load_mapping_rules_returns_expected_shape(rules_doc: dict) -> None:
    """The mapper rules file has the documented top-level shape."""
    assert isinstance(rules_doc, dict)
    assert rules_doc.get("title"), "rules file must have a title"
    assert isinstance(rules_doc.get("rules"), list)
    assert rules_doc["rules"], "rules list must be non-empty"
    # Every rule has the 4 mandatory keys.
    for rule in rules_doc["rules"]:
        for key in ("id", "source_pattern", "canonical_capability", "weight"):
            assert key in rule, f"rule missing required key {key!r}: {rule}"


def test_load_capability_schema_returns_expected_shape(schema_doc: dict) -> None:
    """The schema file is parseable and declares a capabilities list."""
    assert isinstance(schema_doc, dict)
    caps = schema_doc.get("capabilities")
    assert isinstance(caps, list) and caps, "schema.capabilities is empty"


# --- Validation (errors-as-strings) ---


def test_validate_mapping_rules_accepts_the_real_doc(
    rules_doc: dict, schema_doc: dict
) -> None:
    """The shipped mapping_rules.json passes its own validator."""
    errors = validate_mapping_rules(rules_doc, schema_doc)
    assert errors == [], f"unexpected validation errors: {errors[:3]}"


def test_validate_mapping_rules_rejects_unknown_capability(
    rules_doc: dict, schema_doc: dict
) -> None:
    """A typo in canonical_capability surfaces as a plain-English error."""
    bad = {
        "version": 1,
        "rules": [
            {
                "id": "bogus_capability",
                "source_pattern": "sensor\\.foo",
                "canonical_capability": "rc_power_typoed_capability",
                "weight": 50,
                "description": "should fail: cap not in schema",
            }
        ],
    }
    errors = validate_mapping_rules(bad, schema_doc)
    assert any("rc_power_typoed_capability" in e for e in errors), (
        f"expected the unknown-capability error, got: {errors}"
    )


def test_validate_mapping_rules_rejects_missing_rc_prefix(
    rules_doc: dict, schema_doc: dict
) -> None:
    """Any canonical_capability without the `rc_` prefix is rejected."""
    bad = {
        "version": 1,
        "rules": [
            {
                "id": "no_rc_prefix",
                "source_pattern": "sensor\\.foo",
                "canonical_capability": "power_battery_soc",  # missing rc_
                "weight": 50,
                "description": "should fail: missing rc_ prefix",
            }
        ],
    }
    errors = validate_mapping_rules(bad, schema_doc)
    assert any("rc_" in e and "prefix" in e for e in errors), (
        f"expected the missing-rc_ error, got: {errors}"
    )


def test_validate_mapping_rules_rejects_invalid_regex(
    rules_doc: dict, schema_doc: dict
) -> None:
    """An un-compilable regex is reported as a plain-English error."""
    bad = {
        "version": 1,
        "rules": [
            {
                "id": "bad_regex_rule",
                "source_pattern": "sensor\\.(unclosed",  # unbalanced group
                "canonical_capability": "rc_power_battery_soc",
                "weight": 50,
                "description": "should fail: bad regex",
            }
        ],
    }
    errors = validate_mapping_rules(bad, schema_doc)
    assert any("invalid regex" in e for e in errors), (
        f"expected the bad-regex error, got: {errors}"
    )


def test_validate_mapping_rules_rejects_weight_out_of_range(
    rules_doc: dict, schema_doc: dict
) -> None:
    """Weights must be integers in [0, 100]; out-of-range is rejected."""
    too_high = {
        "version": 1,
        "rules": [
            {
                "id": "weight_too_high",
                "source_pattern": "sensor\\.foo",
                "canonical_capability": "rc_power_battery_soc",
                "weight": 150,  # over the ceiling
                "description": "should fail: weight too high",
            }
        ],
    }
    too_low = {
        "version": 1,
        "rules": [
            {
                "id": "weight_negative",
                "source_pattern": "sensor\\.foo",
                "canonical_capability": "rc_power_battery_soc",
                "weight": -1,  # under the floor
                "description": "should fail: negative weight",
            }
        ],
    }
    for bad in (too_high, too_low):
        errors = validate_mapping_rules(bad, schema_doc)
        assert any("out of range" in e for e in errors), (
            f"expected the out-of-range error, got: {errors}"
        )


def test_validate_mapping_rules_rejects_duplicate_rule_ids(
    rules_doc: dict, schema_doc: dict
) -> None:
    """Duplicate rule ids are caught (silent overrides are a footgun)."""
    bad = {
        "version": 1,
        "rules": [
            {
                "id": "dup_rule",
                "source_pattern": "sensor\\.foo",
                "canonical_capability": "rc_power_battery_soc",
                "weight": 50,
                "description": "first",
            },
            {
                "id": "dup_rule",
                "source_pattern": "sensor\\.bar",
                "canonical_capability": "rc_power_battery_voltage",
                "weight": 50,
                "description": "second",
            },
        ],
    }
    errors = validate_mapping_rules(bad, schema_doc)
    assert any("duplicate rule id" in e for e in errors), (
        f"expected the duplicate-rule-id error, got: {errors}"
    )


def test_validate_mapping_rules_rejects_missing_required_keys(
    rules_doc: dict, schema_doc: dict
) -> None:
    """A rule missing any of id / source_pattern / canonical_capability /
    weight is rejected with a clear message."""
    bad = {
        "version": 1,
        "rules": [
            {
                # missing id + weight
                "source_pattern": "sensor\\.foo",
                "canonical_capability": "rc_power_battery_soc",
            }
        ],
    }
    errors = validate_mapping_rules(bad, schema_doc)
    assert any("missing required keys" in e for e in errors), (
        f"expected the missing-required-keys error, got: {errors}"
    )


# --- rc-naming cross-cutting guard ---


def test_every_rule_canonical_capability_starts_with_rc(
    rules_doc: dict,
) -> None:
    """Every rule's canonical_capability starts with `rc_`. This is the
    rc-entity-naming compliance check called out in the slice spec."""
    offenders = [
        r.get("id")
        for r in rules_doc["rules"]
        if not (isinstance(r.get("canonical_capability"), str)
                and r["canonical_capability"].startswith("rc_"))
    ]
    assert offenders == [], (
        f"rules whose canonical_capability is missing the rc_ prefix: "
        f"{offenders}"
    )


def test_every_rule_targets_a_real_canonical_capability(
    rules_doc: dict,
    valid_capability_ids: set[str],
) -> None:
    """Cross-cutting guard: every rule's canonical_capability exists in
    canonical_capabilities.json. Called out in the slice spec as a
    cross-cutting sweep test."""
    offenders = [
        (r.get("id"), r.get("canonical_capability"))
        for r in rules_doc["rules"]
        if r.get("canonical_capability") not in valid_capability_ids
    ]
    assert offenders == [], (
        f"rules whose canonical_capability is not in the schema: {offenders}"
    )


# --- Resolution ---


def test_resolve_victron_battery_voltage_returns_expected_capability(
    rules_doc: dict, schema_doc: dict
) -> None:
    """The slice-spec spot-check: a Victron voltage sensor resolves to
    rc_power_battery_voltage with confidence ≥ 0.7."""
    result = resolve_entity_to_capability(
        "sensor.victron_smartshunt_battery_voltage",
        rules=rules_doc,
        schema=schema_doc,
    )
    assert result is not None, "expected a match, got None"
    cap_id, rule_id, confidence = result
    assert cap_id == "rc_power_battery_voltage"
    assert isinstance(rule_id, str) and rule_id
    assert 0.7 <= confidence <= 1.0, f"confidence out of band: {confidence}"


def test_resolve_unknown_entity_returns_none(
    rules_doc: dict, schema_doc: dict
) -> None:
    """Auto-recover: unknown entity_id → None, never a crash."""
    result = resolve_entity_to_capability(
        "sensor.this_is_not_a_real_thing_xyz",
        rules=rules_doc,
        schema=schema_doc,
    )
    assert result is None


def test_resolve_empty_string_returns_none(
    rules_doc: dict, schema_doc: dict
) -> None:
    """Auto-recover: empty / non-string input → None, never a crash."""
    assert resolve_entity_to_capability("", rules=rules_doc, schema=schema_doc) is None
    assert resolve_entity_to_capability(None, rules=rules_doc, schema=schema_doc) is None  # type: ignore[arg-type]


def test_resolve_picks_highest_weight_on_conflict(
    rules_doc: dict, schema_doc: dict
) -> None:
    """When 2+ rules match, the highest-weight one wins. Build an
    in-memory rule pair that collides on the same entity_id, with
    different weights, and check the winner."""
    rules = {
        "version": 1,
        "rules": [
            {
                "id": "low_priority_match",
                "source_pattern": "sensor\\.conflict_test",
                "canonical_capability": "rc_power_battery_soc",
                "weight": 10,
                "description": "low priority",
            },
            {
                "id": "high_priority_match",
                "source_pattern": "sensor\\.conflict_test",
                "canonical_capability": "rc_power_battery_voltage",
                "weight": 90,
                "description": "high priority",
            },
        ],
    }
    cap_id, rule_id, confidence = resolve_entity_to_capability(
        "sensor.conflict_test", rules=rules, schema=schema_doc
    )
    assert cap_id == "rc_power_battery_voltage"
    assert rule_id == "high_priority_match"
    assert confidence == 0.9


def test_resolve_ties_break_alphabetically(
    rules_doc: dict, schema_doc: dict
) -> None:
    """When 2+ rules match with equal weight, the alphabetically-first
    rule_id wins. This is the determinism guarantee called out in the
    module docstring."""
    rules = {
        "version": 1,
        "rules": [
            {
                "id": "z_rule",
                "source_pattern": "sensor\\.tied_test",
                "canonical_capability": "rc_power_battery_soc",
                "weight": 50,
                "description": "z",
            },
            {
                "id": "a_rule",
                "source_pattern": "sensor\\.tied_test",
                "canonical_capability": "rc_power_battery_voltage",
                "weight": 50,
                "description": "a",
            },
        ],
    }
    cap_id, rule_id, _conf = resolve_entity_to_capability(
        "sensor.tied_test", rules=rules, schema=schema_doc
    )
    assert rule_id == "a_rule", (
        f"expected alphabetical tie-break to pick 'a_rule', got {rule_id!r}"
    )


# --- map_entities / apply_mapping_rules ---


def test_map_entities_handles_mixed_mapped_and_unmapped(
    rules_doc: dict, schema_doc: dict
) -> None:
    """map_entities returns capability_id for known + None for unknown.
    The unknown entries are the auto-recover path — they don't crash."""
    entities = [
        "sensor.victron_smartshunt_battery_voltage",
        "sensor.this_does_not_exist_xyz",
        "sensor.vt_battery_soc_percent",
    ]
    out = map_entities(entities, rules=rules_doc, schema=schema_doc)
    assert out["sensor.victron_smartshunt_battery_voltage"] == "rc_power_battery_voltage"
    assert out["sensor.vt_battery_soc_percent"] == "rc_power_battery_soc"
    assert out["sensor.this_does_not_exist_xyz"] is None


def test_apply_mapping_rules_returns_unmatched_list(
    rules_doc: dict, schema_doc: dict
) -> None:
    """apply_mapping_rules surfaces the unmatched entities separately so
    the dashboard can render a user-friendly fallback tile."""
    entities = [
        "sensor.victron_smartshunt_battery_voltage",  # mapped
        "sensor.totally_unknown_thing",                # unmatched
        "sensor.vt_battery_soc_percent",               # mapped
    ]
    mapping, unmatched = apply_mapping_rules(entities, rules_doc, schema_doc)
    assert mapping["sensor.victron_smartshunt_battery_voltage"] == "rc_power_battery_voltage"
    assert mapping["sensor.vt_battery_soc_percent"] == "rc_power_battery_soc"
    assert mapping["sensor.totally_unknown_thing"] is None
    assert "sensor.totally_unknown_thing" in unmatched
    # Mapped entities must not appear in the unmatched list.
    assert "sensor.victron_smartshunt_battery_voltage" not in unmatched
    assert "sensor.vt_battery_soc_percent" not in unmatched


def test_map_entities_first_entity_wins_per_capability(
    rules_doc: dict, schema_doc: dict
) -> None:
    """First-entity-wins per canonical capability is the dashboard
    contract: each tile gets one source, deterministic."""
    entities = [
        "sensor.first_entity_for_battery_soc",
        "sensor.second_entity_for_battery_soc",
    ]
    rules = {
        "version": 1,
        "rules": [
            {
                "id": "matcher",
                "source_pattern": "sensor\\.(first|second)_entity_for_battery_soc",
                "canonical_capability": "rc_power_battery_soc",
                "weight": 80,
                "description": "match both",
            }
        ],
    }
    out = map_entities(entities, rules=rules, schema=schema_doc)
    assert out["sensor.first_entity_for_battery_soc"] == "rc_power_battery_soc"
    assert out["sensor.second_entity_for_battery_soc"] is None


def test_full_real_world_50_entity_mapping_has_no_unmapped_required_caps(
    rules_doc: dict, schema_doc: dict
) -> None:
    """The slice-spec golden test: 50 sample entity_ids cover every
    canonical capability (15) and resolve to ≥ 15 unique capabilities
    with the deliberately-unmatched tail (2 weather / lock entries)
    landing in the unmatched list."""
    mapping, unmatched = apply_mapping_rules(
        REAL_WORLD_ENTITIES, rules_doc, schema_doc
    )
    # At least 15 distinct canonical capabilities were resolved
    # (one per declared capability).
    resolved_caps = {v for v in mapping.values() if v is not None}
    assert len(resolved_caps) >= 15, (
        f"expected ≥ 15 canonical capabilities resolved, got "
        f"{len(resolved_caps)}: {sorted(resolved_caps)}"
    )
    # Every canonical capability declared in the schema is represented.
    declared_caps = {
        c["id"]
        for c in schema_doc["capabilities"]
        if isinstance(c, dict)
    }
    missing_caps = declared_caps - resolved_caps
    assert missing_caps == set(), (
        f"canonical capabilities not represented in the mapping: "
        f"{sorted(missing_caps)}"
    )
    # The deliberately-unmatched entities land in the unmatched list.
    assert "sensor.weather_forecast" in unmatched
    assert "binary_sensor.front_door_lock" in unmatched
    # The matched ones do not.
    assert "sensor.vt_battery_soc_percent" not in unmatched
    assert "sensor.victron_smartshunt_battery_voltage" not in unmatched


# --- Idempotency ---


def test_idempotency_1000_calls_same_input_same_output(
    rules_doc: dict, schema_doc: dict
) -> None:
    """Idempotency: 1000 calls on the same input return identical output
    (no randomness, no clock-dependence, no caching surprises)."""
    sample = [
        "sensor.victron_smartshunt_battery_voltage",
        "sensor.vt_battery_soc_percent",
        "sensor.totally_made_up_thing",
        "switch.cabin_main",
    ]
    first = map_entities(sample, rules=rules_doc, schema=schema_doc)
    for i in range(1000):
        again = map_entities(sample, rules=rules_doc, schema=schema_doc)
        assert again == first, (
            f"non-idempotent on call {i}: {first!r} vs {again!r}"
        )


def test_resolver_purity_does_not_mutate_inputs(
    rules_doc: dict, schema_doc: dict
) -> None:
    """The resolver does not mutate its inputs (caller may reuse them)."""
    snapshot_rules = json.loads(json.dumps(rules_doc))
    snapshot_schema = json.loads(json.dumps(schema_doc))
    for eid in [
        "sensor.victron_smartshunt_battery_voltage",
        "sensor.vt_battery_soc_percent",
        "sensor.unknown_xyz",
    ]:
        resolve_entity_to_capability(eid, rules=rules_doc, schema=schema_doc)
    assert rules_doc == snapshot_rules, "rules_doc was mutated"
    assert schema_doc == snapshot_schema, "schema_doc was mutated"


# --- Cross-cutting structural guards ---


def test_every_rule_id_is_unique(rules_doc: dict) -> None:
    """Duplicate rule ids are a silent override footgun. Catch them."""
    ids = [r["id"] for r in rules_doc["rules"] if isinstance(r.get("id"), str)]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    assert duplicates == [], f"duplicate rule ids: {duplicates}"


def test_every_rule_pattern_compiles_as_valid_regex(rules_doc: dict) -> None:
    """The validation layer checks this — assert again on the raw doc
    so a regression in validate_mapping_rules shows up here too."""
    import re

    for r in rules_doc["rules"]:
        try:
            re.compile(r["source_pattern"])
        except re.error as exc:
            pytest.fail(
                f"rule {r.get('id')!r} has invalid regex: "
                f"{r.get('source_pattern')!r} ({exc})"
            )


def test_every_rule_weight_is_int_in_range(rules_doc: dict) -> None:
    """The validation layer checks this — assert again on the raw doc
    so a regression in validate_mapping_rules shows up here too."""
    for r in rules_doc["rules"]:
        w = r.get("weight")
        assert isinstance(w, int) and not isinstance(w, bool), (
            f"rule {r.get('id')!r} weight must be int, got {type(w).__name__}"
        )
        assert 0 <= w <= 100, (
            f"rule {r.get('id')!r} weight {w} out of [0, 100]"
        )


def test_minimum_rule_count_is_30(rules_doc: dict) -> None:
    """The slice spec asks for at least 30 rules spanning the listed
    categories. This is the structural floor guard."""
    rules = rules_doc["rules"]
    assert len(rules) >= 30, (
        f"need ≥ 30 rules for full Phase 2 coverage; found {len(rules)}"
    )


def test_rule_coverage_spans_all_six_categories(
    rules_doc: dict, schema_doc: dict
) -> None:
    """The slice spec asks the rules to span power / water / climate /
    lighting / position / network. Confirm every declared category in
    the schema is targeted by at least one rule."""
    declared_categories = {
        c["category"]
        for c in schema_doc["capabilities"]
        if isinstance(c, dict) and isinstance(c.get("category"), str)
    }
    # Reverse-lookup: capability_id → category.
    cap_to_cat = {
        c["id"]: c["category"]
        for c in schema_doc["capabilities"]
        if isinstance(c, dict)
    }
    targeted_categories = {
        cap_to_cat[r["canonical_capability"]]
        for r in rules_doc["rules"]
        if r.get("canonical_capability") in cap_to_cat
    }
    missing = declared_categories - targeted_categories
    assert missing == set(), (
        f"rules do not cover these declared categories: {sorted(missing)}"
    )


# --- Self-mapping + auto-recover combo ---


def test_self_mapping_canonical_tile_lands_in_its_own_capability(
    rules_doc: dict, schema_doc: dict
) -> None:
    """The self-mapping rules (rc_* → rc_*) let an already-canonical
    tile pass through unchanged. Important for template-entity flows
    where the canonical tile is the only source available."""
    result = resolve_entity_to_capability(
        "sensor.rc_power_battery_soc", rules=rules_doc, schema=schema_doc
    )
    assert result is not None
    cap_id, rule_id, confidence = result
    assert cap_id == "rc_power_battery_soc"
    assert rule_id == "roamcore_contract_power_soc"
    assert confidence == 1.0


def test_apply_mapping_rules_returns_list_not_dict_for_unmatched(
    rules_doc: dict, schema_doc: dict
) -> None:
    """The unmatched return is a plain list (callers iterate, never
    index by entity_id). This keeps the surface contract explicit."""
    mapping, unmatched = apply_mapping_rules(
        ["sensor.x_unknown_1", "sensor.y_unknown_2"],
        rules_doc,
        schema_doc,
    )
    assert isinstance(unmatched, list)
    assert all(isinstance(e, str) for e in unmatched)


# --- vehicle_model.py importability sanity ---


def test_mapper_does_not_crash_when_imported_alone(
    tmp_path, monkeypatch
) -> None:
    """The mapper must be importable as a standalone module without
    pulling in Home Assistant. (The vehicle_model loader uses the same
    file-path import trick.)"""
    spec = importlib.util.spec_from_file_location(
        "isolated_mapper_test",
        os.path.join(_CC_DIR, "capability_mapper.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # would raise ModuleNotFoundError on HA
    assert hasattr(mod, "resolve_entity_to_capability")
    assert hasattr(mod, "map_entities")
    assert hasattr(mod, "validate_mapping_rules")
