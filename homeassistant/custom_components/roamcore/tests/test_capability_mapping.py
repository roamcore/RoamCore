"""Tests for the canonical vehicle model mapping layer (Wave 9 #119b).

Phase 2 (Wave 9 #119) — the canonical vehicle model is the foundational
abstraction that every Phase 2 piece builds on. The schema primitive
(commit d5138ed, #119a) defined the canonical contract in
``connections/_schema/canonical_capabilities.json``. This slice is the
mapping layer (#119b): given a vendor entity id, return the canonical
capability id it should map to.

Naming follows ``docs/reference/rc-entity-naming.md``:
  * every canonical id starts with ``rc_``
  * no vendor names (victron, unifi, starlink, …) in any contract id

Tests are pure stdlib — no Home Assistant imports — so they can run in
any CI rig that already runs the rest of the RoamCore test suite.

The test module imports ``capability_mapping.py`` by absolute file
path (mirroring ``test_vehicle_model.py``) so pytest does not
auto-import the parent ``roamcore`` package, which requires the HA
runtime.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys

import pytest

# ---------------------------------------------------------------------------
# Import the module under test by absolute file path.
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
_CC_DIR = os.path.join(_REPO_ROOT, "homeassistant", "custom_components", "roamcore")
_CM_PATH = os.path.join(_CC_DIR, "capability_mapping.py")

_spec = importlib.util.spec_from_file_location(
    "roamcore_capability_mapping", _CM_PATH
)
assert _spec is not None and _spec.loader is not None, (
    "capability_mapping.py not loadable"
)
_capability_mapping = importlib.util.module_from_spec(_spec)
sys.modules["roamcore_capability_mapping"] = _capability_mapping
_spec.loader.exec_module(_capability_mapping)

CONFIDENCE_EXACT_RULE = _capability_mapping.CONFIDENCE_EXACT_RULE
CONFIDENCE_EXAMPLE_SOURCE = _capability_mapping.CONFIDENCE_EXAMPLE_SOURCE
CONFIDENCE_FUZZY_SUFFIX = _capability_mapping.CONFIDENCE_FUZZY_SUFFIX
CONFIDENCE_THRESHOLD = _capability_mapping.CONFIDENCE_THRESHOLD
LOW_CONFIDENCE_THRESHOLD = _capability_mapping.LOW_CONFIDENCE_THRESHOLD
FORBIDDEN_VENDOR_TOKENS = _capability_mapping.FORBIDDEN_VENDOR_TOKENS
AmbiguousMappingError = _capability_mapping.AmbiguousMappingError
MappingRuleError = _capability_mapping.MappingRuleError
build_capability_map = _capability_mapping.build_capability_map
load_mapping_rules = _capability_mapping.load_mapping_rules
map_entity_to_capability = _capability_mapping.map_entity_to_capability
unmapped_entities = _capability_mapping.unmapped_entities

SCHEMA_PATH = os.path.join(
    _REPO_ROOT, "connections", "_schema", "canonical_capabilities.json"
)
RULES_PATH = os.path.join(
    _REPO_ROOT, "connections", "_schema", "capability_mapping_rules.json"
)

# A canonical "shipped rules" doc that exercises the documented
# vendors + the generic-fallback patterns. Reused by many tests.
_SHIPPED_RULES_DOC: dict = {
    "rules": [
        # Victron
        {"vendor_entity_id_pattern": "sensor.vt_battery_soc_percent",
         "canonical_id": "rc_power_battery_soc"},
        {"vendor_entity_id_pattern": "sensor.vt_battery_voltage_v",
         "canonical_id": "rc_power_battery_voltage"},
        {"vendor_entity_id_pattern": "sensor.vt_battery_current_a",
         "canonical_id": "rc_power_battery_current"},
        {"vendor_entity_id_pattern": "sensor.vt_solar_power_w",
         "canonical_id": "rc_power_solar_power"},
        {"vendor_entity_id_pattern": "binary_sensor.vt_shore_connected",
         "canonical_id": "rc_power_shore_connected"},
        # Starlink
        {"vendor_entity_id_pattern": "sensor.dish_signal_quality",
         "canonical_id": "rc_network_internet_reachable"},
        # Peplink
        {"vendor_entity_id_pattern": "sensor.pep_wan_ip",
         "canonical_id": "rc_network_wan_ip"},
        # Teltonika
        {"vendor_entity_id_pattern": "sensor.rut_signal_strength",
         "canonical_id": "rc_network_internet_reachable"},
        # Generic
        {"vendor_entity_id_pattern": "switch.cabin_main",
         "canonical_id": "rc_lighting_interior_state"},
        {"vendor_entity_id_pattern": "switch.porch_light",
         "canonical_id": "rc_lighting_approach_state"},
        {"vendor_entity_id_pattern": "sensor.indoor_temp",
         "canonical_id": "rc_climate_indoor_temperature"},
        {"vendor_entity_id_pattern": "switch.hvac_main",
         "canonical_id": "rc_climate_hvac_state"},
        {"vendor_entity_id_pattern": "sensor.fresh_water_tank_level",
         "canonical_id": "rc_water_fresh_level"},
        {"vendor_entity_id_pattern": "switch.water_pump",
         "canonical_id": "rc_water_pump_state"},
    ],
}


def _caps_doc() -> dict:
    """Load the shipped canonical schema once per call."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as fp:
        return json.load(fp)


def _write_rules(tmp_path, doc: dict) -> str:
    p = tmp_path / "capability_mapping_rules.json"
    p.write_text(json.dumps(doc))
    return str(p)


# ===========================================================================
# load_mapping_rules — accept paths
# ===========================================================================


def test_load_mapping_rules_parses_shipped_default(tmp_path):
    """If the rules file is shipped on disk, ``load_mapping_rules`` parses it.
    If the file is absent (development fork) the test still documents the
    contract — re-creating the shipped doc on the fly into a tmp_path.
    """
    if os.path.exists(RULES_PATH):
        doc = load_mapping_rules(RULES_PATH)
        assert isinstance(doc, dict)
        assert "rules" in doc and isinstance(doc["rules"], list)
        assert len(doc["rules"]) >= 1
    else:
        # Shipped rules file absent — write the well-known defaults into
        # tmp_path and re-load from disk to exercise the parser end-to-end.
        path = _write_rules(tmp_path, _SHIPPED_RULES_DOC)
        doc = load_mapping_rules(path)
        assert isinstance(doc, dict)
        assert "rules" in doc and isinstance(doc["rules"], list)
        assert len(doc["rules"]) == len(_SHIPPED_RULES_DOC["rules"])


def test_load_mapping_rules_parses_valid_json(tmp_path):
    path = _write_rules(tmp_path, _SHIPPED_RULES_DOC)
    doc = load_mapping_rules(path)
    assert "rules" in doc
    assert len(doc["rules"]) == len(_SHIPPED_RULES_DOC["rules"])


def test_load_mapping_rules_raises_on_missing_file(tmp_path):
    missing = tmp_path / "does-not-exist.json"
    with pytest.raises(FileNotFoundError):
        load_mapping_rules(missing)


def test_load_mapping_rules_raises_on_invalid_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{ this is : not, json")
    with pytest.raises(json.JSONDecodeError):
        load_mapping_rules(bad)


def test_load_mapping_rules_rejects_non_dict_top_level(tmp_path):
    p = tmp_path / "rules.json"
    p.write_text(json.dumps(["not", "a", "dict"]))
    with pytest.raises(MappingRuleError):
        load_mapping_rules(p)


def test_load_mapping_rules_rejects_missing_rules_key(tmp_path):
    p = tmp_path / "rules.json"
    p.write_text(json.dumps({"not_rules": []}))
    with pytest.raises(MappingRuleError):
        load_mapping_rules(p)


def test_load_mapping_rules_rejects_rule_without_vendor_pattern(tmp_path):
    p = tmp_path / "rules.json"
    p.write_text(json.dumps({"rules": [{"canonical_id": "rc_power_battery_soc"}]}))
    with pytest.raises(MappingRuleError):
        load_mapping_rules(p)


def test_load_mapping_rules_rejects_rule_without_canonical_id(tmp_path):
    p = tmp_path / "rules.json"
    p.write_text(
        json.dumps({"rules": [{"vendor_entity_id_pattern": "sensor.x"}]})
    )
    with pytest.raises(MappingRuleError):
        load_mapping_rules(p)


def test_load_mapping_rules_rejects_rule_with_non_dict_entry(tmp_path):
    p = tmp_path / "rules.json"
    p.write_text(
        json.dumps(
            {"rules": ["not a dict", {"vendor_entity_id_pattern": "sensor.x",
                                       "canonical_id": "rc_power_battery_soc"}]}
        )
    )
    with pytest.raises(MappingRuleError):
        load_mapping_rules(p)


# ===========================================================================
# load_mapping_rules — reject rc-naming violations
# ===========================================================================


def test_load_mapping_rules_rejects_canonical_id_without_rc_prefix(tmp_path):
    p = tmp_path / "rules.json"
    p.write_text(
        json.dumps(
            {"rules": [{"vendor_entity_id_pattern": "sensor.x",
                        "canonical_id": "power_battery_soc"}]}
        )
    )
    with pytest.raises(MappingRuleError):
        load_mapping_rules(p)


def test_load_mapping_rules_rejects_canonical_id_with_victron_token(tmp_path):
    p = tmp_path / "rules.json"
    p.write_text(
        json.dumps(
            {"rules": [{"vendor_entity_id_pattern": "sensor.x",
                        "canonical_id": "rc_power_victron_soc"}]}
        )
    )
    with pytest.raises(MappingRuleError):
        load_mapping_rules(p)


def test_load_mapping_rules_rejects_canonical_id_with_vt_prefix(tmp_path):
    p = tmp_path / "rules.json"
    p.write_text(
        json.dumps(
            {"rules": [{"vendor_entity_id_pattern": "sensor.x",
                        "canonical_id": "rc_power_vt_soc_0"}]}
        )
    )
    with pytest.raises(MappingRuleError):
        load_mapping_rules(p)


def test_load_mapping_rules_rejects_canonical_id_with_starlink_token(tmp_path):
    p = tmp_path / "rules.json"
    p.write_text(
        json.dumps(
            {"rules": [{"vendor_entity_id_pattern": "sensor.x",
                        "canonical_id": "rc_network_starlink_signal"}]}
        )
    )
    with pytest.raises(MappingRuleError):
        load_mapping_rules(p)


def test_load_mapping_rules_rejects_canonical_id_with_uppercase(tmp_path):
    p = tmp_path / "rules.json"
    p.write_text(
        json.dumps(
            {"rules": [{"vendor_entity_id_pattern": "sensor.x",
                        "canonical_id": "rc_Power_Battery_Soc"}]}
        )
    )
    with pytest.raises(MappingRuleError):
        load_mapping_rules(p)


# ===========================================================================
# map_entity_to_capability — exact rule matches (positive cases)
# ===========================================================================


def test_map_entity_exact_match_victron_soc():
    caps = _caps_doc()
    cid, info = map_entity_to_capability(
        "sensor.vt_battery_soc_percent", _SHIPPED_RULES_DOC, caps
    )
    assert cid == "rc_power_battery_soc"
    assert info["confidence"] == CONFIDENCE_EXACT_RULE
    assert info["low_confidence"] is False


def test_map_entity_exact_match_victron_voltage():
    caps = _caps_doc()
    cid, _ = map_entity_to_capability(
        "sensor.vt_battery_voltage_v", _SHIPPED_RULES_DOC, caps
    )
    assert cid == "rc_power_battery_voltage"


def test_map_entity_exact_match_victron_current():
    caps = _caps_doc()
    cid, _ = map_entity_to_capability(
        "sensor.vt_battery_current_a", _SHIPPED_RULES_DOC, caps
    )
    assert cid == "rc_power_battery_current"


def test_map_entity_exact_match_victron_solar():
    caps = _caps_doc()
    cid, _ = map_entity_to_capability(
        "sensor.vt_solar_power_w", _SHIPPED_RULES_DOC, caps
    )
    assert cid == "rc_power_solar_power"


def test_map_entity_exact_match_victron_shore():
    caps = _caps_doc()
    cid, _ = map_entity_to_capability(
        "binary_sensor.vt_shore_connected", _SHIPPED_RULES_DOC, caps
    )
    assert cid == "rc_power_shore_connected"


def test_map_entity_exact_match_starlink():
    caps = _caps_doc()
    cid, _ = map_entity_to_capability(
        "sensor.dish_signal_quality", _SHIPPED_RULES_DOC, caps
    )
    assert cid == "rc_network_internet_reachable"


def test_map_entity_exact_match_peplink():
    caps = _caps_doc()
    cid, _ = map_entity_to_capability(
        "sensor.pep_wan_ip", _SHIPPED_RULES_DOC, caps
    )
    assert cid == "rc_network_wan_ip"


def test_map_entity_exact_match_teltonika():
    caps = _caps_doc()
    cid, _ = map_entity_to_capability(
        "sensor.rut_signal_strength", _SHIPPED_RULES_DOC, caps
    )
    assert cid == "rc_network_internet_reachable"


def test_map_entity_exact_match_generic_cabin_lights():
    caps = _caps_doc()
    cid, _ = map_entity_to_capability(
        "switch.cabin_main", _SHIPPED_RULES_DOC, caps
    )
    assert cid == "rc_lighting_interior_state"


def test_map_entity_exact_match_generic_porch_lights():
    caps = _caps_doc()
    cid, _ = map_entity_to_capability(
        "switch.porch_light", _SHIPPED_RULES_DOC, caps
    )
    assert cid == "rc_lighting_approach_state"


def test_map_entity_exact_match_generic_indoor_temp():
    caps = _caps_doc()
    cid, _ = map_entity_to_capability(
        "sensor.indoor_temp", _SHIPPED_RULES_DOC, caps
    )
    assert cid == "rc_climate_indoor_temperature"


def test_map_entity_exact_match_generic_fresh_water():
    caps = _caps_doc()
    cid, _ = map_entity_to_capability(
        "sensor.fresh_water_tank_level", _SHIPPED_RULES_DOC, caps
    )
    assert cid == "rc_water_fresh_level"


def test_map_entity_exact_match_is_case_insensitive():
    """HA entity IDs are lowercase by convention but a stray uppercase
    must not silently fail to map."""
    caps = _caps_doc()
    cid, _ = map_entity_to_capability(
        "SENSOR.VT_BATTERY_SOC_PERCENT", _SHIPPED_RULES_DOC, caps
    )
    assert cid == "rc_power_battery_soc"


# ===========================================================================
# map_entity_to_capability — example_sources match
# ===========================================================================


def test_map_entity_example_sources_match_returns_canonical_with_0_9_confidence():
    """``sensor.battery_state`` is listed in the shipped schema's
    example_sources for ``rc_power_battery_soc``. No explicit rule
    covers it, so the result must come from the example_sources index
    with confidence 0.9."""
    caps = _caps_doc()
    cid, info = map_entity_to_capability(
        "sensor.battery_state", _SHIPPED_RULES_DOC, caps
    )
    assert cid == "rc_power_battery_soc"
    assert info["confidence"] == CONFIDENCE_EXAMPLE_SOURCE
    assert info["low_confidence"] is False
    assert "example_sources" in info["reason"]


def test_map_entity_example_sources_match_awning_light():
    """``switch.awning_light`` is in the schema's example_sources for
    ``rc_lighting_approach_state``."""
    caps = _caps_doc()
    cid, info = map_entity_to_capability(
        "switch.awning_light", _SHIPPED_RULES_DOC, caps
    )
    assert cid == "rc_lighting_approach_state"
    assert info["confidence"] == CONFIDENCE_EXAMPLE_SOURCE


def test_map_entity_no_explicit_rule_uses_schema_example_sources():
    """Without any rules file (empty rules doc), the schema's
    example_sources still drives mapping."""
    caps = _caps_doc()
    empty_rules = {"rules": []}
    cid, info = map_entity_to_capability(
        "sensor.battery_state", empty_rules, caps
    )
    assert cid == "rc_power_battery_soc"
    assert info["confidence"] == CONFIDENCE_EXAMPLE_SOURCE


# ===========================================================================
# map_entity_to_capability — fuzzy suffix match
# ===========================================================================


def test_map_entity_fuzzy_suffix_returns_none_with_low_confidence():
    """A vendor entity whose suffix token matches the canonical id's
    object token but has no explicit rule and is not in example_sources
    must produce ``None`` with low_confidence=True so the dashboard
    generator can choose to skip or warn.

    ``sensor.battery_health_gauge`` has suffix ``battery`` (first token
    after the domain prefix) and is NOT in any example_sources list, so
    it falls through to fuzzy matching."""
    caps = _caps_doc()
    cid, info = map_entity_to_capability(
        "sensor.battery_health_gauge", _SHIPPED_RULES_DOC, caps
    )
    assert cid is None
    assert info["confidence"] == CONFIDENCE_FUZZY_SUFFIX
    assert info["low_confidence"] is True
    assert "candidates" in info


def test_map_entity_fuzzy_suffix_lists_candidates():
    """The candidates field lists the canonical ids whose object token
    matched the vendor suffix — useful for the setup wizard to nudge
    the user toward configuring an explicit rule."""
    caps = _caps_doc()
    _, info = map_entity_to_capability(
        "sensor.battery_health_gauge", _SHIPPED_RULES_DOC, caps
    )
    assert isinstance(info["candidates"], list)
    # All candidates are rc_power_battery_* capabilities.
    assert all(c.startswith("rc_power_battery_") for c in info["candidates"])


def test_map_entity_fully_unknown_returns_none():
    """An entity id with no rule, no example_source, and no fuzzy hit
    returns None with a reason that names the entity."""
    caps = _caps_doc()
    cid, info = map_entity_to_capability(
        "sensor.weird_unicorn_gauge", _SHIPPED_RULES_DOC, caps
    )
    assert cid is None
    assert info["confidence"] == 0.0
    assert info["low_confidence"] is True
    assert "no mapping" in info["reason"]


# ===========================================================================
# map_entity_to_capability — ambiguous match
# ===========================================================================


def test_map_entity_ambiguous_two_rules_equal_confidence_raises():
    """Two rules that both match the same entity id with equal exact-rule
    confidence must raise ``AmbiguousMappingError`` — silent winners are
    a setup-wizard footgun."""
    caps = _caps_doc()
    rules = {
        "rules": [
            {"vendor_entity_id_pattern": "sensor.dual_watch",
             "canonical_id": "rc_power_battery_soc"},
            {"vendor_entity_id_pattern": "sensor.dual_watch",
             "canonical_id": "rc_power_solar_power"},
        ]
    }
    with pytest.raises(AmbiguousMappingError):
        map_entity_to_capability("sensor.dual_watch", rules, caps)


def test_ambiguous_mapping_error_carries_entity_and_candidates():
    caps = _caps_doc()
    rules = {
        "rules": [
            {"vendor_entity_id_pattern": "sensor.dual_watch",
             "canonical_id": "rc_power_battery_soc"},
            {"vendor_entity_id_pattern": "sensor.dual_watch",
             "canonical_id": "rc_power_solar_power"},
        ]
    }
    try:
        map_entity_to_capability("sensor.dual_watch", rules, caps)
    except AmbiguousMappingError as exc:
        msg = str(exc)
        assert "sensor.dual_watch" in msg
        assert "rc_power_battery_soc" in msg
        assert "rc_power_solar_power" in msg


def test_map_entity_rule_match_outranks_example_sources():
    """If an entity matches BOTH a rule AND an example_source from a
    different capability, the rule wins (confidence 1.0 vs 0.9)."""
    caps = _caps_doc()
    rules = {
        "rules": [
            {"vendor_entity_id_pattern": "sensor.battery_state",
             "canonical_id": "rc_power_battery_voltage"},
        ]
    }
    cid, info = map_entity_to_capability(
        "sensor.battery_state", rules, caps
    )
    assert cid == "rc_power_battery_voltage"
    assert info["confidence"] == CONFIDENCE_EXACT_RULE


# ===========================================================================
# map_entity_to_capability — input validation
# ===========================================================================


def test_map_entity_rejects_empty_entity_id():
    with pytest.raises(ValueError):
        map_entity_to_capability("", _SHIPPED_RULES_DOC, _caps_doc())


def test_map_entity_rejects_non_dict_capabilities_doc():
    with pytest.raises(ValueError):
        map_entity_to_capability("sensor.x", _SHIPPED_RULES_DOC, "not a dict")  # type: ignore[arg-type]


def test_map_entity_tolerates_missing_rules_key():
    """A rules doc without 'rules' key behaves like an empty rules doc."""
    caps = _caps_doc()
    cid, info = map_entity_to_capability(
        "sensor.battery_state", {}, caps
    )
    # Falls through to example_sources match.
    assert cid == "rc_power_battery_soc"
    assert info["confidence"] == CONFIDENCE_EXAMPLE_SOURCE


def test_map_entity_tolerates_non_dict_rule_entries():
    """Garbage in the rules list (e.g. strings) is skipped, not crashed."""
    caps = _caps_doc()
    rules = {"rules": ["not a dict", 42, None,
                       {"vendor_entity_id_pattern": "sensor.vt_battery_soc_percent",
                        "canonical_id": "rc_power_battery_soc"}]}
    cid, info = map_entity_to_capability(
        "sensor.vt_battery_soc_percent", rules, caps
    )
    assert cid == "rc_power_battery_soc"
    assert info["confidence"] == CONFIDENCE_EXACT_RULE


# ===========================================================================
# build_capability_map
# ===========================================================================


def test_build_capability_map_returns_confident_subset_only():
    """Low-confidence fuzzy hits are NOT included in the canonical map."""
    caps = _caps_doc()
    entities = {
        "sensor.vt_battery_soc_percent": {},                # exact → in
        "sensor.battery_health_gauge": {},                  # fuzzy → out
        "sensor.battery_state": {},                          # example_sources → in
        "sensor.weird_unicorn_gauge": {},                    # nothing → out
        "switch.cabin_main": {},                             # exact → in
    }
    result = build_capability_map(entities, _SHIPPED_RULES_DOC, caps)
    assert "rc_power_battery_soc" in result
    assert "rc_lighting_interior_state" in result
    # The fuzzy hit must NOT have polluted any canonical slot.
    for vendor_id in result.values():
        assert vendor_id != "sensor.battery_health_gauge"


def test_build_capability_map_returns_deterministic_tie_break_alphabetical():
    """Two vendor entities both mapping to ``rc_power_battery_soc``
    via exact rules (confidence 1.0 each) — the alphabetical-first
    vendor id wins so output is reproducible across runs."""
    caps = _caps_doc()
    entities = {
        "sensor.zzz_vendor_battery_soc": {},   # rule → rc_power_battery_soc
        "sensor.aaa_vendor_battery_soc": {},   # rule → rc_power_battery_soc
    }
    rules = {
        "rules": [
            {"vendor_entity_id_pattern": "sensor.zzz_vendor_battery_soc",
             "canonical_id": "rc_power_battery_soc"},
            {"vendor_entity_id_pattern": "sensor.aaa_vendor_battery_soc",
             "canonical_id": "rc_power_battery_soc"},
        ]
    }
    result = build_capability_map(entities, rules, caps)
    # Both entities map with confidence 1.0 to the same canonical id.
    # The alphabetical-first vendor id (``sensor.aaa_vendor_battery_soc``)
    # must win so the dashboard generator is deterministic.
    assert result.get("rc_power_battery_soc") == "sensor.aaa_vendor_battery_soc"


def test_build_capability_map_does_not_duplicate_canonical_ids():
    """The returned dict is keyed by canonical id — no canonical id can
    appear twice (Python dicts can't have duplicate keys, but the
    test guards the intent)."""
    caps = _caps_doc()
    entities = {
        "sensor.vt_battery_soc_percent": {},
        "sensor.battery_state": {},
        "switch.cabin_main": {},
    }
    result = build_capability_map(entities, _SHIPPED_RULES_DOC, caps)
    keys = list(result.keys())
    assert len(keys) == len(set(keys))


def test_build_capability_map_rejects_non_dict_entities():
    with pytest.raises(ValueError):
        build_capability_map([], _SHIPPED_RULES_DOC, _caps_doc())  # type: ignore[arg-type]


def test_unmapped_entities_returns_leftovers_sorted():
    caps = _caps_doc()
    entities = {
        "sensor.zzz_unknown_thing": {},
        "sensor.aaa_unknown_thing": {},
        "sensor.vt_battery_soc_percent": {},  # maps → excluded from leftovers
    }
    leftover = unmapped_entities(entities, _SHIPPED_RULES_DOC, caps)
    assert leftover == [
        "sensor.aaa_unknown_thing",
        "sensor.zzz_unknown_thing",
    ]


def test_unmapped_entities_includes_low_confidence_fuzzy_hits():
    """A fuzzy-match-only entity must show up in ``unmapped_entities``
    so the setup wizard can offer the user an explicit rule."""
    caps = _caps_doc()
    entities = {
        "sensor.battery_health_gauge": {},      # fuzzy only → unmapped
        "sensor.vt_battery_soc_percent": {},   # exact → mapped
    }
    leftover = unmapped_entities(entities, _SHIPPED_RULES_DOC, caps)
    assert "sensor.battery_health_gauge" in leftover
    assert "sensor.vt_battery_soc_percent" not in leftover


# ===========================================================================
# End-to-end: a mock van setup
# ===========================================================================


def test_end_to_end_typical_van_setup_covers_six_categories():
    """A realistic van setup — Victron battery + Renogy solar + Starlink
    + generic lights + water + GPS — must produce a canonical map that
    covers all 6 default capability categories."""
    caps = _caps_doc()
    rules = _SHIPPED_RULES_DOC
    # Note: some categories (climate, position) need extra rules not in
    # the shipped doc — append them so the e2e test exercises every
    # default category.
    extra = {
        "rules": rules["rules"] + [
            {"vendor_entity_id_pattern": "sensor.indoor_temp_2",
             "canonical_id": "rc_climate_indoor_temperature"},
            {"vendor_entity_id_pattern": "device_tracker.vt_vehicle",
             "canonical_id": "rc_position_lat"},
            {"vendor_entity_id_pattern": "sensor.vehicle_lon",
             "canonical_id": "rc_position_lon"},
        ]
    }
    entities = {
        # power
        "sensor.vt_battery_soc_percent": {},
        "sensor.vt_battery_voltage_v": {},
        "sensor.vt_battery_current_a": {},
        "sensor.vt_solar_power_w": {},
        "binary_sensor.vt_shore_connected": {},
        # lighting
        "switch.cabin_main": {},
        "switch.porch_light": {},
        # climate
        "sensor.indoor_temp_2": {},
        # water
        "sensor.fresh_water_tank_level": {},
        "switch.water_pump": {},
        # position
        "device_tracker.vt_vehicle": {},
        "sensor.vehicle_lon": {},
        # network
        "sensor.dish_signal_quality": {},
        "sensor.pep_wan_ip": {},
    }
    result = build_capability_map(entities, extra, caps)
    seen_categories = {
        next(c["category"] for c in caps["capabilities"] if c["id"] == cid)
        for cid in result.keys()
    }
    assert seen_categories == {
        "power", "lighting", "climate", "water", "position", "network"
    }


def test_end_to_end_canonical_map_has_no_vendor_token_in_keys():
    """Cross-cutting guard: every key in the produced map is an
    ``rc_*`` id with no vendor name — proves the rc-naming rule is
    honoured end-to-end, not just at rule-load time."""
    caps = _caps_doc()
    entities = {
        "sensor.vt_battery_soc_percent": {},
        "sensor.vt_solar_power_w": {},
        "binary_sensor.vt_shore_connected": {},
        "sensor.dish_signal_quality": {},
        "sensor.pep_wan_ip": {},
        "sensor.rut_signal_strength": {},
        "switch.cabin_main": {},
        "sensor.indoor_temp": {},
        "sensor.fresh_water_tank_level": {},
    }
    result = build_capability_map(entities, _SHIPPED_RULES_DOC, caps)
    assert result, "expected non-empty canonical map"
    for cid in result.keys():
        assert cid.startswith("rc_")
        lower = cid.lower()
        for vendor in FORBIDDEN_VENDOR_TOKENS:
            assert vendor not in lower, (
                f"canonical id {cid!r} contains forbidden vendor token "
                f"{vendor!r}"
            )


def test_end_to_end_unmapped_leftovers_are_alphabetical():
    caps = _caps_doc()
    entities = {
        "sensor.zzz_unknown": {},
        "sensor.aaa_unknown": {},
        "sensor.vt_battery_soc_percent": {},
    }
    result = build_capability_map(entities, _SHIPPED_RULES_DOC, caps)
    leftovers = unmapped_entities(entities, _SHIPPED_RULES_DOC, caps)
    assert leftovers == sorted(leftovers)


# ===========================================================================
# Exported constants + parity with vehicle_model.py
# ===========================================================================


def test_forbidden_vendor_tokens_match_vehicle_model_pattern():
    """The mapping layer's forbidden vendor tokens MUST contain every
    well-known vendor name — guards against typos at re-declaration."""
    expected = {
        "victron", "vt_", "unifi", "ubnt", "starlink", "peplink",
        "teltonika", "frigate", "mqtt", "esphome", "homeassistant", "hass",
    }
    assert set(FORBIDDEN_VENDOR_TOKENS) == expected


def test_confidence_thresholds_are_ordered():
    assert CONFIDENCE_EXACT_RULE > CONFIDENCE_EXAMPLE_SOURCE > CONFIDENCE_FUZZY_SUFFIX
    assert LOW_CONFIDENCE_THRESHOLD < CONFIDENCE_EXAMPLE_SOURCE
    assert CONFIDENCE_THRESHOLD >= LOW_CONFIDENCE_THRESHOLD


def test_constants_are_exported_at_module_level():
    """Public constants are accessible via attribute access — guards
    against accidentally renaming them."""
    for name in (
        "CONFIDENCE_EXACT_RULE",
        "CONFIDENCE_EXAMPLE_SOURCE",
        "CONFIDENCE_FUZZY_SUFFIX",
        "CONFIDENCE_THRESHOLD",
        "LOW_CONFIDENCE_THRESHOLD",
        "FORBIDDEN_VENDOR_TOKENS",
    ):
        assert hasattr(_capability_mapping, name), f"missing export: {name}"


# ===========================================================================
# Sanity: the shipped canonical schema passes every rc-naming rule.
# ===========================================================================


def test_shipped_schema_has_no_vendor_token_in_canonical_ids():
    """Same shape as the validator's cross-cutting sweep — confirms
    the canonical map (which the mapping layer produces) can only ever
    reference contract ids that already pass the rc-naming rule."""
    caps = _caps_doc()
    for cap in caps["capabilities"]:
        lower = cap["id"].lower()
        for vendor in FORBIDDEN_VENDOR_TOKENS:
            assert vendor not in lower, (
                f"shipped canonical id {cap['id']!r} contains vendor token "
                f"{vendor!r}"
            )