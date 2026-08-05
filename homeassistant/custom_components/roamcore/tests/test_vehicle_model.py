"""Tests for the canonical vehicle model schema + validator.

Phase 2 (Wave 9 #119) — the canonical vehicle model is the
foundational value of RoamCore: every connected device maps to a
canonical slot regardless of brand. The schema lives at
`connections/_schema/canonical_capabilities.json` and is enforced by
`homeassistant/custom_components/roamcore/vehicle_model.py`.

Naming follows `docs/reference/rc-entity-naming.md`:
  * `<domain>.rc_<subsystem>_<object>_<metric>`
  * the `rc_` prefix is mandatory
  * no vendor names (victron, unifi, starlink, …) in any contract id

Tests are pure stdlib — no Home Assistant imports — so they can run
in any CI rig that already runs the rest of the RoamCore test suite.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import sys

import pytest

# Load vehicle_model.py by absolute path so we don't depend on pytest's
# package-discovery machinery — pytest auto-imports the parent
# `homeassistant/custom_components/roamcore/__init__.py` when the test
# file lives inside that package, which requires the HA runtime.
# Loading by file path bypasses that import entirely.
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
_CC_DIR = os.path.join(_REPO_ROOT, "homeassistant", "custom_components", "roamcore")
_VM_PATH = os.path.join(_CC_DIR, "vehicle_model.py")

_spec = importlib.util.spec_from_file_location("roamcore_vehicle_model", _VM_PATH)
assert _spec is not None and _spec.loader is not None, "vehicle_model.py not loadable"
_vehicle_model = importlib.util.module_from_spec(_spec)
sys.modules["roamcore_vehicle_model"] = _vehicle_model
_spec.loader.exec_module(_vehicle_model)

DEFAULT_CAPABILITY_CATEGORIES = _vehicle_model.DEFAULT_CAPABILITY_CATEGORIES
FORBIDDEN_VENDOR_TOKENS = _vehicle_model.FORBIDDEN_VENDOR_TOKENS
VALID_DOMAINS = _vehicle_model.VALID_DOMAINS
VALID_KINDS = _vehicle_model.VALID_KINDS
find_capability = _vehicle_model.find_capability
get_capabilities_by_category = _vehicle_model.get_capabilities_by_category
load_capabilities = _vehicle_model.load_capabilities
validate_capabilities = _vehicle_model.validate_capabilities

SCHEMA_PATH = os.path.join(
    _REPO_ROOT, "connections", "_schema", "canonical_capabilities.json"
)


# --- Tiny helpers ---


def _minimal_valid_capability(idx: int = 0) -> dict:
    """A capability that satisfies every validator rule.

    `idx` keeps the id unique across the duplicates test below.
    """
    return {
        "id": f"rc_power_battery_soc_{idx}",
        "category": "power",
        "kind": "telemetry",
        "type": "sensor",
        "device_class": "battery",
        "unit": "%",
        "description": f"battery soc variant {idx}",
        "example_sources": [f"sensor.example_{idx}"],
    }


def _minimal_valid_doc(num_caps: int = 2) -> dict:
    """A document with `num_caps` minimal-valid capabilities across
    two categories so the 12-cap floor is intentionally *not* met."""
    caps = []
    for i in range(num_caps):
        caps.append(_minimal_valid_capability(i))
    # Add a second category entry so the doc has variety.
    if num_caps >= 2:
        caps[1] = {
            "id": "rc_lighting_interior_state_0",
            "category": "lighting",
            "kind": "control",
            "type": "switch",
            "description": "interior lights on/off",
            "example_sources": ["switch.cabin_main"],
        }
    return {
        "title": "test doc",
        "description": "test",
        "capability_categories": ["power", "lighting"],
        "capabilities": caps,
    }


_CATEGORY_TEMPLATES = [
    ("power", "sensor", "telemetry", "battery"),
    ("lighting", "switch", "control", None),
    ("climate", "sensor", "telemetry", "temperature"),
    ("water", "sensor", "telemetry", "battery"),
    ("position", "sensor", "telemetry", None),
    ("network", "binary_sensor", "telemetry", "connectivity"),
]


def _build_full_minimal_doc(num_caps: int = 12) -> dict:
    """Build a fully-valid document with N capabilities spread across
    the 6 default categories. Useful when a test needs a doc that
    passes the 12-cap floor.
    """
    categories = [c[0] for c in _CATEGORY_TEMPLATES]
    # Use a letter-only suffix so each token starts with a lowercase
    # letter and the rc-naming regex matches cleanly.
    LETTERS = "abcdefghijklmnopqrstuvwxyz"
    caps = []
    for i in range(num_caps):
        cat, domain, kind, _ = _CATEGORY_TEMPLATES[i % len(_CATEGORY_TEMPLATES)]
        suffix = LETTERS[i % 26] + (LETTERS[(i // 26) % 26] if i >= 26 else "")
        caps.append({
            "id": f"rc_{cat}_thing_{suffix}",
            "category": cat,
            "kind": kind,
            "type": domain,
            "description": f"{cat} thing {suffix}",
            "example_sources": [f"sensor.example_{suffix}"],
        })
    return {
        "title": "test doc",
        "description": "test",
        "capability_categories": categories,
        "capabilities": caps,
    }


# ===========================================================================
# load_capabilities
# ===========================================================================


def test_load_capabilities_parses_json():
    caps = load_capabilities(SCHEMA_PATH)
    assert isinstance(caps, dict)
    assert caps["title"] == "RoamCore Canonical Vehicle Model"
    assert "capabilities" in caps and isinstance(caps["capabilities"], list)
    assert len(caps["capabilities"]) >= 12


def test_load_capabilities_raises_on_missing_file(tmp_path):
    missing = tmp_path / "does-not-exist.json"
    with pytest.raises(FileNotFoundError):
        load_capabilities(missing)


def test_load_capabilities_raises_on_invalid_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{ this is : not, json")
    with pytest.raises(json.JSONDecodeError):
        load_capabilities(bad)


def test_load_capabilities_accepts_pathlib_path(tmp_path):
    src = tmp_path / "cap.json"
    src.write_text(json.dumps(_minimal_valid_doc()))
    # pathlib.Path should also work — not just strings.
    caps = load_capabilities(src)
    assert caps["title"] == "test doc"


# ===========================================================================
# validate_capabilities — accept paths
# ===========================================================================


def test_validate_capabilities_accepts_minimal_valid_caps():
    # 12 caps across 6 categories meets the floor and yields 0 errors.
    doc = _build_full_minimal_doc(num_caps=12)
    errs = validate_capabilities(doc)
    assert errs == []


def test_validate_capabilities_accepts_full_caps():
    # The shipped canonical document must validate cleanly.
    caps = load_capabilities(SCHEMA_PATH)
    errs = validate_capabilities(caps)
    assert errs == [], f"shipped schema failed validation: {errs}"


def test_validate_capabilities_flags_minimum_cap_count_when_below_threshold():
    doc = _minimal_valid_doc(num_caps=6)  # only 6, below the 12 floor
    errs = validate_capabilities(doc)
    assert any("at least 12 capabilities" in e for e in errs)


def test_capabilities_json_matches_validator_round_trip():
    """Re-parse the JSON and re-validate: must agree with the first run."""
    caps = load_capabilities(SCHEMA_PATH)
    errs_1 = validate_capabilities(caps)
    # Re-serialise + re-load, then re-validate. Same result.
    roundtrip = json.loads(json.dumps(caps))
    errs_2 = validate_capabilities(roundtrip)
    assert errs_1 == errs_2 == []


# ===========================================================================
# validate_capabilities — reject paths
# ===========================================================================


def test_validate_capabilities_rejects_unknown_category():
    doc = _minimal_valid_doc(num_caps=2)
    doc["capabilities"][0]["category"] = "magic"  # not in declared list
    errs = validate_capabilities(doc)
    assert any("category" in e and "magic" in e for e in errs)


def test_validate_capabilities_rejects_capability_id_without_rc_prefix():
    doc = _minimal_valid_doc(num_caps=2)
    doc["capabilities"][0]["id"] = "power_battery_soc_0"  # no rc_ prefix
    errs = validate_capabilities(doc)
    assert any("rc_ prefix" in e for e in errs)


def test_validate_capabilities_rejects_capability_id_with_victron_vendor_name():
    doc = _minimal_valid_doc(num_caps=2)
    doc["capabilities"][0]["id"] = "rc_power_victron_soc"
    errs = validate_capabilities(doc)
    assert any("victron" in e.lower() and "vendor token" in e for e in errs)


def test_validate_capabilities_rejects_capability_id_with_unifi_vendor_name():
    doc = _minimal_valid_doc(num_caps=2)
    doc["capabilities"][0]["id"] = "rc_network_unifi_wan_ip"
    errs = validate_capabilities(doc)
    assert any("unifi" in e.lower() for e in errs)


def test_validate_capabilities_rejects_capability_id_with_vt_prefix():
    """vt_* is the Victron vendor layer — must never leak into rc_*."""
    doc = _minimal_valid_doc(num_caps=2)
    doc["capabilities"][0]["id"] = "rc_power_vt_soc_0"
    errs = validate_capabilities(doc)
    assert any("vt_" in e for e in errs)


def test_validate_capabilities_accepts_capability_id_per_rc_naming_pattern():
    """Positive: every rc-naming style should be accepted."""
    for good_id in (
        "rc_power_battery_soc",
        "rc_location_lat",  # canonical 2-token-after-rc example
        "rc_network_internet_reachable",
    ):
        doc = _build_full_minimal_doc(num_caps=12)
        # Replace one cap with the good_id under the right category.
        target_cat = (
            "power" if "power" in good_id
            else "location" if "location" in good_id
            else "network"
        )
        if target_cat not in doc["capability_categories"]:
            doc["capability_categories"].append(target_cat)
        replaced = False
        for c in doc["capabilities"]:
            if c["category"] == target_cat and not replaced:
                c["id"] = good_id
                replaced = True
        if not replaced:
            doc["capabilities"].append({
                "id": good_id,
                "category": target_cat,
                "kind": "telemetry",
                "type": "sensor",
                "description": f"good id {good_id}",
                "example_sources": ["sensor.x"],
            })
        errs = validate_capabilities(doc)
        assert errs == [], f"{good_id!r} should validate: {errs}"


def test_validate_capabilities_rejects_capability_id_with_uppercase():
    doc = _minimal_valid_doc(num_caps=1)
    doc["capabilities"][0]["id"] = "rc_Power_Battery_Soc"
    errs = validate_capabilities(doc)
    assert any("rc-naming pattern" in e for e in errs)


def test_validate_capabilities_rejects_capability_id_with_single_token():
    doc = _minimal_valid_doc(num_caps=1)
    doc["capabilities"][0]["id"] = "rc_power"  # only 1 token after rc_
    errs = validate_capabilities(doc)
    assert any("rc-naming pattern" in e for e in errs)


def test_validate_capabilities_rejects_duplicate_capability_ids():
    doc = _build_full_minimal_doc(num_caps=12)
    doc["capabilities"][2]["id"] = doc["capabilities"][0]["id"]
    errs = validate_capabilities(doc)
    assert any("duplicate capability id" in e for e in errs)


def test_validate_capabilities_rejects_missing_kind():
    doc = _minimal_valid_doc(num_caps=1)
    del doc["capabilities"][0]["kind"]
    errs = validate_capabilities(doc)
    assert any(".kind" in e for e in errs)


def test_validate_capabilities_rejects_invalid_kind():
    doc = _minimal_valid_doc(num_caps=1)
    doc["capabilities"][0]["kind"] = "magic"
    errs = validate_capabilities(doc)
    assert any(".kind" in e for e in errs)


def test_validate_capabilities_rejects_invalid_type():
    doc = _minimal_valid_doc(num_caps=1)
    doc["capabilities"][0]["type"] = "weather"  # not an HA domain
    errs = validate_capabilities(doc)
    assert any(".type" in e for e in errs)


def test_validate_capabilities_rejects_empty_description():
    doc = _minimal_valid_doc(num_caps=1)
    doc["capabilities"][0]["description"] = "   "
    errs = validate_capabilities(doc)
    assert any(".description" in e for e in errs)


def test_validate_capabilities_rejects_missing_capability_categories():
    doc = _minimal_valid_doc(num_caps=1)
    del doc["capability_categories"]
    errs = validate_capabilities(doc)
    assert any("capability_categories" in e for e in errs)


def test_validate_capabilities_rejects_empty_capabilities_list():
    doc = _minimal_valid_doc(num_caps=0)
    errs = validate_capabilities(doc)
    assert any("capabilities" in e and "non-empty" in e for e in errs)


# ===========================================================================
# get_capabilities_by_category
# ===========================================================================


def test_get_capabilities_by_category():
    caps = load_capabilities(SCHEMA_PATH)
    power = get_capabilities_by_category(caps, "power")
    assert isinstance(power, list)
    assert len(power) >= 1
    assert all(c["category"] == "power" for c in power)
    # The shipped schema must include the headline power capability.
    assert any(c["id"] == "rc_power_battery_soc" for c in power)


def test_get_capabilities_by_category_returns_empty_for_unknown():
    caps = load_capabilities(SCHEMA_PATH)
    assert get_capabilities_by_category(caps, "unicorn") == []


def test_get_capabilities_by_category_returns_empty_when_capabilities_missing():
    doc = {"capability_categories": [], "capabilities": None}
    assert get_capabilities_by_category(doc, "power") == []


def test_get_capabilities_by_category_skips_non_dict_entries():
    doc = {
        "capability_categories": ["power"],
        "capabilities": [
            "not a dict",
            {"id": "rc_power_x_y", "category": "power", "kind": "telemetry",
             "type": "sensor", "description": "ok"},
        ],
    }
    out = get_capabilities_by_category(doc, "power")
    assert len(out) == 1
    assert out[0]["id"] == "rc_power_x_y"


# ===========================================================================
# find_capability
# ===========================================================================


def test_find_capability():
    caps = load_capabilities(SCHEMA_PATH)
    cap = find_capability(caps, "rc_power_battery_soc")
    assert cap is not None
    assert cap["category"] == "power"
    assert cap["kind"] == "telemetry"


def test_find_capability_returns_none_for_unknown():
    caps = load_capabilities(SCHEMA_PATH)
    assert find_capability(caps, "rc_does_not_exist") is None


def test_find_capability_returns_none_when_capabilities_missing():
    assert find_capability({}, "rc_anything") is None


# ===========================================================================
# Cross-cutting + exported constants
# ===========================================================================


def test_default_categories_are_six_and_unique():
    assert len(DEFAULT_CAPABILITY_CATEGORIES) == 6
    assert len(set(DEFAULT_CAPABILITY_CATEGORIES)) == 6
    assert set(DEFAULT_CAPABILITY_CATEGORIES) == {
        "power", "lighting", "climate", "water", "position", "network",
    }


def test_shipped_schema_uses_every_default_category():
    caps = load_capabilities(SCHEMA_PATH)
    seen = {c["category"] for c in caps["capabilities"]}
    assert set(DEFAULT_CAPABILITY_CATEGORIES).issubset(seen)


def test_shipped_schema_has_no_vendor_tokens_in_any_capability_id():
    """Hard Rule #2 from rc-entity-naming.md — guard with a sweep."""
    caps = load_capabilities(SCHEMA_PATH)
    for cap in caps["capabilities"]:
        lower = cap["id"].lower()
        for vendor in FORBIDDEN_VENDOR_TOKENS:
            assert vendor not in lower, (
                f"capability id {cap['id']!r} contains vendor token {vendor!r}"
            )


def test_shipped_schema_every_capability_passes_individual_id_pattern():
    import re
    pat = re.compile(r"^rc_[a-z][a-z0-9]*(_[a-z][a-z0-9]*){1,}$")
    caps = load_capabilities(SCHEMA_PATH)
    for cap in caps["capabilities"]:
        assert pat.match(cap["id"]), f"{cap['id']!r} does not match rc-naming"


def test_validator_aggregates_multiple_errors_at_once():
    """A bad document should report every problem in a single pass."""
    doc = {
        "title": 42,  # wrong type
        "capability_categories": "not a list",  # wrong type
        "capabilities": [
            {"id": "no_prefix", "category": "unknown", "kind": "magic",
             "type": "weather", "description": ""},
        ],
    }
    errs = validate_capabilities(doc)
    # At minimum we should see the top-level, the prefix, the kind,
    # the type, and the description flagged.
    joined = " | ".join(errs)
    assert "title" in joined
    assert "capability_categories" in joined
    assert "rc_ prefix" in joined
    assert ".kind" in joined
    assert ".type" in joined
    assert ".description" in joined


def test_validator_does_not_raise_on_non_dict_input():
    """The validator is total — it never raises, only returns errors."""
    errs = validate_capabilities("not a dict")  # type: ignore[arg-type]
    assert isinstance(errs, list)
    assert len(errs) >= 1


def test_validator_does_not_raise_on_capability_that_is_not_a_dict():
    doc = {
        "capability_categories": ["power"],
        "capabilities": ["not a dict", 42, None],
    }
    errs = validate_capabilities(doc)
    assert isinstance(errs, list)
    assert any("must be a JSON object" in e for e in errs)


def test_validator_handles_example_sources_wrong_type():
    doc = _minimal_valid_doc(num_caps=1)
    doc["capabilities"][0]["example_sources"] = "sensor.foo"
    errs = validate_capabilities(doc)
    assert any("example_sources" in e for e in errs)


def test_validator_handles_example_sources_with_empty_string():
    doc = _minimal_valid_doc(num_caps=1)
    doc["capabilities"][0]["example_sources"] = ["sensor.foo", ""]
    errs = validate_capabilities(doc)
    assert any("example_sources" in e for e in errs)


def test_validator_accepts_capability_without_example_sources():
    doc = _build_full_minimal_doc(num_caps=12)
    for c in doc["capabilities"]:
        c.pop("example_sources", None)
    errs = validate_capabilities(doc)
    assert errs == []


def test_validator_accepts_capability_without_device_class():
    """device_class is recommended but not required (lighting + water
    pump controls have no device_class in HA, for example)."""
    doc = _build_full_minimal_doc(num_caps=12)
    for c in doc["capabilities"]:
        c.pop("device_class", None)
    errs = validate_capabilities(doc)
    assert errs == []


def test_validator_accepts_capability_without_unit():
    """unit is optional for boolean / switch / select types."""
    doc = _build_full_minimal_doc(num_caps=12)
    for c in doc["capabilities"]:
        c.pop("unit", None)
    errs = validate_capabilities(doc)
    assert errs == []


def test_valid_domains_and_kinds_match_documented_allowlists():
    # Sanity: the validator exposes the right allowlists for callers.
    assert "sensor" in VALID_DOMAINS
    assert "binary_sensor" in VALID_DOMAINS
    assert "switch" in VALID_DOMAINS
    assert "telemetry" in VALID_KINDS
    assert "control" in VALID_KINDS
