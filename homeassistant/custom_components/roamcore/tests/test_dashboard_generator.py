"""Tests for the Lovelace YAML dashboard generator.

Phase 2 (Wave 9 #119c) — the dashboard generator consumes the
output of #119b's ``build_capability_map()`` and emits a Lovelace
YAML string. The module lives at
``homeassistant/custom_components/roamcore/dashboard_generator.py``
and is pure stdlib + json so the rig can run without the Home
Assistant runtime (mirrors ``test_vehicle_model.py``).

What the tests guard:

  * the output is a non-empty string,
  * the output parses as valid YAML (PyYAML is allowed ONLY in
    tests; the production module stays stdlib+json),
  * the output is deterministic (same inputs → byte-identical),
  * the output is vendor-neutral (no brand tokens outside
    ``entity:`` lines),
  * every canonical capability's ``description`` becomes the card
    name + title (vanlifer language, not the ``rc_*`` id),
  * device_class drives the icon (vendor-neutral mdi: prefix),
  * switches get a ``tap_action: toggle``,
  * buttons are NEVER surfaced on the auto-generated dashboard,
  * empty ``capability_map`` yields a placeholder document,
  * empty categories are HIDDEN (no empty section headers),
  * all three card styles (``compact``, ``full``, ``diagnostic``)
    render valid YAML with the right per-style additions.

The test rig follows the import-by-file-path pattern from
``test_vehicle_model.py`` so pytest does not pull in the HA
runtime when loading the parent package.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys

import pytest

# PyYAML is allowed ONLY in the test rig (production stays
# stdlib+json). Skip the parse-validity tests if it isn't
# installed in the smoke environment.
try:
    import yaml as _yaml  # noqa: F401
    _HAS_YAML = True
except ImportError:  # pragma: no cover - defensive
    _yaml = None
    _HAS_YAML = False

# Load dashboard_generator.py by absolute path so pytest doesn't
# pull in the parent roamcore package's __init__.py.
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
_CC_DIR = os.path.join(_REPO_ROOT, "homeassistant", "custom_components", "roamcore")
_DG_PATH = os.path.join(_CC_DIR, "dashboard_generator.py")

_spec = importlib.util.spec_from_file_location(
    "roamcore_dashboard_generator", _DG_PATH
)
assert _spec is not None and _spec.loader is not None, "dashboard_generator.py not loadable"
_dashboard_generator = importlib.util.module_from_spec(_spec)
sys.modules["roamcore_dashboard_generator"] = _dashboard_generator
_spec.loader.exec_module(_dashboard_generator)

CARD_STYLES = _dashboard_generator.CARD_STYLES
CATEGORY_TO_HEADING = _dashboard_generator.CATEGORY_TO_HEADING
DEFAULT_CARD_STYLE = _dashboard_generator.DEFAULT_CARD_STYLE
DEVICE_CLASS_TO_ICON = _dashboard_generator.DEVICE_CLASS_TO_ICON
EMPTY_OUTPUT_MARKER = _dashboard_generator.EMPTY_OUTPUT_MARKER
FORBIDDEN_VENDOR_TOKENS = _dashboard_generator.FORBIDDEN_VENDOR_TOKENS
SWITCH_DEFAULT_ICON = _dashboard_generator.SWITCH_DEFAULT_ICON
card_for_capability = _dashboard_generator.card_for_capability
generate_dashboard_yaml = _dashboard_generator.generate_dashboard_yaml
heading_for_category = _dashboard_generator.heading_for_category
icon_for_device_class = _dashboard_generator.icon_for_device_class

SCHEMA_PATH = os.path.join(
    _REPO_ROOT, "connections", "_schema", "canonical_capabilities.json"
)


# --- Tiny helpers ---


def _load_schema() -> dict:
    """Load the shipped canonical-capabilities document."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as fp:
        return json.load(fp)


def _minimal_doc(num_caps: int = 2) -> dict:
    """A tiny, fully-valid capabilities document for shape tests.

    Categories are spread across the 6 default categories so we can
    exercise per-category section ordering + heading rendering.
    """
    templates = [
        ("power", "sensor", "telemetry", "battery", "%", "battery percent"),
        ("power", "switch", "control", None, None, "battery toggle"),
        ("lighting", "switch", "control", None, None, "lights on/off"),
        ("climate", "sensor", "telemetry", "temperature", "°C", "indoor temp"),
        ("water", "sensor", "telemetry", "battery", "%", "fresh water level"),
        ("position", "sensor", "telemetry", "latitude", "°", "van latitude"),
        ("network", "binary_sensor", "telemetry", "connectivity", None, "internet ok"),
    ]
    capabilities = []
    for i in range(num_caps):
        cat, domain, kind, dev_class, unit, desc = templates[i % len(templates)]
        entry: dict = {
            "id": f"rc_{cat}_thing_{i}",
            "category": cat,
            "kind": kind,
            "type": domain,
            "description": f"{desc} {i}",
            "example_sources": [f"sensor.example_{i}"],
        }
        if dev_class is not None:
            entry["device_class"] = dev_class
        if unit is not None:
            entry["unit"] = unit
        capabilities.append(entry)
    return {
        "title": "test doc",
        "description": "test",
        "capability_categories": [
            "power", "lighting", "climate", "water", "position", "network",
        ],
        "capabilities": capabilities,
    }


def _yaml_load(text: str):
    """Parse YAML or skip if PyYAML isn't installed in the smoke env.

    PyYAML is allowed in tests only — the production module is
    stdlib+json. If PyYAML isn't available, parse-validity tests
    skip rather than fail so the rig still runs.
    """
    if not _HAS_YAML:
        pytest.skip("PyYAML not installed in smoke env; skipping parse check")
    return _yaml.safe_load(text)


def _yaml_lines(out: str) -> list[str]:
    """Return the rendered YAML split into lines for assertions."""
    return out.split("\n")


def _assert_vendor_neutral(out: str) -> None:
    """Assert the YAML contains no forbidden vendor tokens outside
    ``entity:`` lines (where the vendor entity id is allowed)."""
    forbidden = (
        "victron", "vt_", "unifi", "ubnt", "starlink",
        "dish_", "peplink", "teltonika", "rut_", "frigate",
        "mqtt", "esphome", "homeassistant", "hass",
    )
    for line in _yaml_lines(out):
        stripped = line.lstrip()
        # Vendor entity ids appear ONLY inside entity: lines.
        if stripped.startswith("- entity:") or stripped.startswith("entity:"):
            continue
        low = line.lower()
        for tok in forbidden:
            assert tok not in low, (
                f"forbidden vendor token {tok!r} leaked into non-entity line: "
                f"{line!r}"
            )


# ===========================================================================
# Public constants + helpers
# ===========================================================================


def test_card_styles_tuple_lists_supported_styles():
    assert CARD_STYLES == ("compact", "full", "diagnostic")


def test_default_card_style_is_compact():
    assert DEFAULT_CARD_STYLE == "compact"


def test_forbidden_vendor_tokens_match_documented_list():
    # Hard Rule #2 from rc-entity-naming.md.
    for tok in ("victron", "vt_", "unifi", "starlink", "peplink",
                "teltonika", "frigate", "mqtt"):
        assert tok in FORBIDDEN_VENDOR_TOKENS


def test_category_to_heading_uses_plain_english():
    """Headings must be vanlifer language, not machine ids."""
    assert CATEGORY_TO_HEADING["power"] == "Power"
    assert CATEGORY_TO_HEADING["lighting"] == "Lighting"
    assert CATEGORY_TO_HEADING["climate"] == "Climate"
    assert CATEGORY_TO_HEADING["water"] == "Water"
    assert CATEGORY_TO_HEADING["position"] == "Position"
    assert CATEGORY_TO_HEADING["network"] == "Network"


def test_heading_for_category_known_value():
    assert heading_for_category("power") == "Power"


def test_heading_for_category_unknown_value_falls_back_to_title_case():
    """Unknown categories still render something readable."""
    assert heading_for_category("magic_thing") == "Magic Thing"
    # Empty / non-string input is also defensive — never raise.
    assert isinstance(heading_for_category(""), str)


def test_icon_for_device_class_known_values():
    assert icon_for_device_class("battery") == "mdi:battery"
    assert icon_for_device_class("plug") == "mdi:power-plug"
    assert icon_for_device_class("connectivity") == "mdi:wifi"
    assert icon_for_device_class("temperature") == "mdi:thermometer"
    assert icon_for_device_class("power") == "mdi:solar-power"


def test_icon_for_device_class_unknown_returns_default():
    """Unknown device_class falls back to the default icon."""
    assert icon_for_device_class("unknown") == "mdi:gauge"


def test_icon_for_device_class_none_returns_default():
    """Missing device_class falls back to the default icon."""
    assert icon_for_device_class(None) == "mdi:gauge"


def test_all_known_device_classes_have_an_icon():
    """Every device_class in the shipped schema has an icon mapping."""
    schema = _load_schema()
    for cap in schema["capabilities"]:
        dc = cap.get("device_class")
        if dc is None:
            continue
        # The shipped schema uses well-known HA device_class values;
        # every one of them must have an icon mapping.
        assert dc in DEVICE_CLASS_TO_ICON, (
            f"device_class {dc!r} (capability {cap['id']!r}) has no icon "
            f"in DEVICE_CLASS_TO_ICON"
        )


def test_device_class_to_icons_all_use_mdi_prefix():
    """Icons must use the mdi: prefix — vendor-neutral Material Design Icons."""
    for dc, icon in DEVICE_CLASS_TO_ICON.items():
        assert icon.startswith("mdi:"), (
            f"icon for {dc!r} does not use the mdi: prefix: {icon!r}"
        )


def test_switch_default_icon_uses_mdi_prefix():
    """Switches use the standard mdi toggle-switch icon."""
    assert SWITCH_DEFAULT_ICON.startswith("mdi:")


# ===========================================================================
# card_for_capability — single-card shape
# ===========================================================================


def test_card_for_capability_sensor():
    cap = {
        "id": "rc_power_battery_soc",
        "category": "power",
        "kind": "telemetry",
        "type": "sensor",
        "device_class": "battery",
        "unit": "%",
        "description": "State of charge of the leisure battery.",
    }
    card = card_for_capability(cap, "sensor.vt_battery_soc_percent")
    assert card is not None
    assert card["type"] == "entities"
    assert card["title"] == "State of charge of the leisure battery."
    assert len(card["entities"]) == 1
    entity = card["entities"][0]
    assert entity["entity"] == "sensor.vt_battery_soc_percent"
    assert entity["name"] == "State of charge of the leisure battery."
    assert entity["icon"] == "mdi:battery"
    assert entity["unit"] == "%"
    # Sensors don't get a tap_action.
    assert "tap_action" not in entity


def test_card_for_capability_binary_sensor_uses_device_class_icon():
    cap = {
        "id": "rc_power_shore_connected",
        "category": "power",
        "kind": "telemetry",
        "type": "binary_sensor",
        "device_class": "plug",
        "description": "Whether the van is plugged into shore power.",
    }
    card = card_for_capability(cap, "binary_sensor.vt_shore_connected")
    entity = card["entities"][0]
    assert entity["icon"] == "mdi:power-plug"
    assert "tap_action" not in entity
    assert "unit" not in entity  # binary_sensor has no unit


def test_card_for_capability_switch_has_tap_action_toggle():
    cap = {
        "id": "rc_lighting_interior_state",
        "category": "lighting",
        "kind": "control",
        "type": "switch",
        "description": "On/off for the interior lights.",
    }
    card = card_for_capability(cap, "switch.cabin_main")
    entity = card["entities"][0]
    assert entity["tap_action"] == {"action": "toggle"}
    assert entity["entity"] == "switch.cabin_main"


def test_card_for_capability_button_returns_none():
    """Buttons are NOT shown on the auto-generated dashboard."""
    cap = {
        "id": "rc_power_thing",
        "category": "power",
        "kind": "control",
        "type": "button",
        "description": "A test button.",
    }
    assert card_for_capability(cap, "button.foo") is None


def test_card_for_capability_name_uses_description_not_id():
    """The card name comes from the description, NEVER from the id."""
    cap = {
        "id": "rc_power_internal_id_should_not_leak",
        "category": "power",
        "kind": "telemetry",
        "type": "sensor",
        "device_class": "battery",
        "unit": "%",
        "description": "Friendly plain-English label for the user.",
    }
    card = card_for_capability(cap, "sensor.vendor_thing")
    entity = card["entities"][0]
    assert "Friendly plain-English label" in entity["name"]
    # The canonical id must not leak into the rendered card name.
    assert "rc_power_internal_id_should_not_leak" not in entity["name"]
    assert card["title"] == entity["name"]


def test_card_for_capability_icon_uses_device_class_not_vendor():
    """The icon is derived from device_class, not from any vendor hint."""
    cap = {
        "id": "rc_power_battery_soc",
        "category": "power",
        "kind": "telemetry",
        "type": "sensor",
        "device_class": "battery",
        "description": "battery state",
    }
    card = card_for_capability(cap, "sensor.victron_special_soc")
    assert card["entities"][0]["icon"] == "mdi:battery"


def test_card_for_capability_compact_is_default_style():
    """card_style='compact' adds no secondary_info / diagnostic suffix."""
    cap = {
        "id": "rc_power_battery_soc", "category": "power", "kind": "telemetry",
        "type": "sensor", "device_class": "battery", "unit": "%",
        "description": "battery state",
    }
    card = card_for_capability(cap, "sensor.x", card_style="compact")
    entity = card["entities"][0]
    assert "secondary_info" not in entity
    assert "[" not in entity["name"]
    assert "[" not in card["title"]


def test_card_for_capability_full_adds_secondary_info_on_sensors():
    """card_style='full' adds secondary_info='last-changed' on sensors."""
    cap = {
        "id": "rc_power_battery_soc", "category": "power", "kind": "telemetry",
        "type": "sensor", "device_class": "battery", "unit": "%",
        "description": "battery state",
    }
    card = card_for_capability(cap, "sensor.x", card_style="full")
    entity = card["entities"][0]
    assert entity["secondary_info"] == "last-changed"


def test_card_for_capability_full_does_not_add_secondary_info_to_switches():
    """Switches don't get secondary_info in full mode."""
    cap = {
        "id": "rc_lighting_interior_state", "category": "lighting",
        "kind": "control", "type": "switch",
        "description": "lights on/off",
    }
    card = card_for_capability(cap, "switch.x", card_style="full")
    entity = card["entities"][0]
    assert "secondary_info" not in entity


def test_card_for_capability_diagnostic_surfaces_canonical_and_entity_ids():
    """card_style='diagnostic' surfaces both ids in the title + name."""
    cap = {
        "id": "rc_power_battery_soc", "category": "power", "kind": "telemetry",
        "type": "sensor", "device_class": "battery", "unit": "%",
        "description": "battery state",
    }
    card = card_for_capability(cap, "sensor.vt_battery", card_style="diagnostic")
    entity = card["entities"][0]
    # Diagnostic name carries BOTH the canonical id and the entity id.
    assert "rc_power_battery_soc" in entity["name"]
    assert "sensor.vt_battery" in entity["name"]
    # Diagnostic title carries the canonical id (grep-friendly).
    assert "rc_power_battery_soc" in card["title"]


def test_card_for_capability_rejects_unknown_card_style():
    cap = {
        "id": "rc_power_x", "category": "power", "kind": "telemetry",
        "type": "sensor", "device_class": "battery", "description": "x",
    }
    with pytest.raises(ValueError):
        card_for_capability(cap, "sensor.x", card_style="magic")


def test_card_for_capability_missing_description_falls_back_to_humanised_id():
    """Defensive: a capability without description still produces a card."""
    cap = {
        "id": "rc_power_battery_soc", "category": "power", "kind": "telemetry",
        "type": "sensor", "device_class": "battery",
    }
    card = card_for_capability(cap, "sensor.x")
    assert card is not None
    # Falls back to a humanised id.
    assert "power battery soc" in card["title"].lower()


def test_card_for_capability_skips_non_dict_input():
    """Defensive: non-dict capability is ignored (returns None)."""
    # Not exercised by the public API but guards future callers.
    assert card_for_capability(None, "sensor.x") is None  # type: ignore[arg-type]


# ===========================================================================
# generate_dashboard_yaml — top-level
# ===========================================================================


def test_generate_dashboard_yaml_returns_string():
    out = generate_dashboard_yaml({}, _minimal_doc())
    assert isinstance(out, str)


def test_generate_dashboard_yaml_empty_map_returns_placeholder():
    out = generate_dashboard_yaml({}, _minimal_doc())
    # The placeholder is valid YAML with a vertical-stack and an
    # empty cards list, plus a plain-English comment for the user.
    assert "vertical-stack" in out
    assert "cards: []" in out
    parsed = _yaml_load(out)
    assert parsed["vertical-stack"]["cards"] == []


def test_generate_dashboard_yaml_empty_map_uses_known_marker():
    out = generate_dashboard_yaml({}, _minimal_doc())
    # The marker constant is what the placeholder emits — this
    # guards against accidentally changing the user-facing string.
    assert EMPTY_OUTPUT_MARKER.strip() == out.strip()


def test_generate_dashboard_yaml_parses_as_yaml_for_real_inputs():
    """Real inputs produce YAML that PyYAML can re-parse."""
    cap_map = {
        "rc_power_thing_0": "sensor.example_0",
        "rc_lighting_thing_2": "switch.example_2",
    }
    out = generate_dashboard_yaml(cap_map, _minimal_doc(4))
    parsed = _yaml_load(out)
    assert "vertical-stack" in parsed
    assert isinstance(parsed["vertical-stack"]["cards"], list)
    assert len(parsed["vertical-stack"]["cards"]) >= 1


def test_generate_dashboard_yaml_single_sensor_capability():
    """A single sensor capability → one entities card with the right shape."""
    cap_map = {"rc_power_thing_0": "sensor.example_0"}
    out = generate_dashboard_yaml(cap_map, _minimal_doc(1))
    parsed = _yaml_load(out)
    # Walk into the section + the card.
    sections = parsed["vertical-stack"]["cards"]
    assert len(sections) == 1
    assert sections[0]["title"] == "Power"
    cards = sections[0]["cards"]
    assert len(cards) == 1
    assert cards[0]["type"] == "entities"
    entity = cards[0]["entities"][0]
    assert entity["entity"] == "sensor.example_0"
    assert entity["icon"] == "mdi:battery"
    assert entity["unit"] == "%"


def test_generate_dashboard_yaml_single_binary_sensor_uses_device_class_icon():
    """Plug binary_sensor → mdi:power-plug icon."""
    cap_map = {"rc_power_thing_0": "binary_sensor.example_0"}
    # Need a doc with a binary_sensor to exercise this branch.
    doc = {
        "title": "x", "description": "x",
        "capability_categories": ["power"],
        "capabilities": [{
            "id": "rc_power_thing_0", "category": "power", "kind": "telemetry",
            "type": "binary_sensor", "device_class": "plug",
            "description": "plug state",
        }],
    }
    out = generate_dashboard_yaml(cap_map, doc)
    parsed = _yaml_load(out)
    section = parsed["vertical-stack"]["cards"][0]
    entity = section["cards"][0]["entities"][0]
    assert entity["icon"] == "mdi:power-plug"


def test_generate_dashboard_yaml_single_switch_has_tap_action_toggle():
    """A switch capability renders tap_action: toggle."""
    cap_map = {"rc_power_thing_1": "switch.example_1"}
    out = generate_dashboard_yaml(cap_map, _minimal_doc(4))
    parsed = _yaml_load(out)
    # The switch lives in the power section.
    sections = parsed["vertical-stack"]["cards"]
    # Find the switch card across all sections.
    found_toggle = False
    for section in sections:
        for card in section.get("cards", []):
            for entity in card.get("entities", []):
                if entity.get("entity") == "switch.example_1":
                    assert entity.get("tap_action") == {"action": "toggle"}
                    found_toggle = True
    assert found_toggle, "switch card not found in any section"


def test_generate_dashboard_yaml_button_capability_is_not_in_output():
    """Buttons are HIDDEN from the auto-generated dashboard."""
    doc = {
        "title": "x", "description": "x",
        "capability_categories": ["power"],
        "capabilities": [{
            "id": "rc_power_button_test", "category": "power", "kind": "control",
            "type": "button", "description": "test button",
        }],
    }
    out = generate_dashboard_yaml(
        {"rc_power_button_test": "button.foo"}, doc
    )
    # The button must not appear anywhere in the rendered cards.
    assert "button.foo" not in out or "button_test" not in out
    # More precisely: the placeholder is emitted because the only
    # mapped capability was a button and got filtered out.
    assert "no capabilities mapped yet" in out


def test_generate_dashboard_yaml_multi_category_emits_per_category_sections():
    """Multi-category input produces one vertical-stack per populated category."""
    cap_map = {
        "rc_power_thing_0": "sensor.example_0",
        "rc_lighting_thing_2": "switch.example_2",
        "rc_network_thing_6": "binary_sensor.example_6",
    }
    out = generate_dashboard_yaml(cap_map, _minimal_doc(7))
    parsed = _yaml_load(out)
    titles = [s["title"] for s in parsed["vertical-stack"]["cards"]]
    assert "Power" in titles
    assert "Lighting" in titles
    assert "Network" in titles
    # Categories with no mapped capabilities are HIDDEN.
    assert "Climate" not in titles
    assert "Water" not in titles
    assert "Position" not in titles


def test_generate_dashboard_yaml_section_order_follows_capability_categories():
    """Sections appear in the order declared by capability_categories."""
    cap_map = {
        "rc_network_thing_6": "binary_sensor.example_6",
        "rc_power_thing_0": "sensor.example_0",
        "rc_lighting_thing_2": "switch.example_2",
    }
    out = generate_dashboard_yaml(cap_map, _minimal_doc(7))
    parsed = _yaml_load(out)
    titles = [s["title"] for s in parsed["vertical-stack"]["cards"]]
    # Power appears before Lighting, Lighting before Network in the
    # capability_categories list — sections follow that order.
    assert titles.index("Power") < titles.index("Lighting")
    assert titles.index("Lighting") < titles.index("Network")


def test_generate_dashboard_yaml_empty_categories_omitted():
    """Categories with zero mapped capabilities produce no section."""
    cap_map = {"rc_power_thing_0": "sensor.example_0"}
    out = generate_dashboard_yaml(cap_map, _minimal_doc(1))
    parsed = _yaml_load(out)
    titles = [s["title"] for s in parsed["vertical-stack"]["cards"]]
    assert titles == ["Power"]


def test_generate_dashboard_yaml_section_headings_are_plain_english():
    """Section headings are the plain-English CATEGORY_TO_HEADING values."""
    cap_map = {
        "rc_power_thing_0": "sensor.example_0",
        "rc_lighting_thing_2": "switch.example_2",
        "rc_climate_thing_3": "sensor.example_3",
    }
    out = generate_dashboard_yaml(cap_map, _minimal_doc(7))
    parsed = _yaml_load(out)
    titles = [s["title"] for s in parsed["vertical-stack"]["cards"]]
    assert titles == ["Power", "Lighting", "Climate"]


def test_generate_dashboard_yaml_card_name_uses_description_not_id():
    """The card name comes from the capability description, not the id."""
    cap_map = {"rc_power_internal_id_should_not_leak": "sensor.foo"}
    doc = {
        "title": "x", "description": "x",
        "capability_categories": ["power"],
        "capabilities": [{
            "id": "rc_power_internal_id_should_not_leak", "category": "power",
            "kind": "telemetry", "type": "sensor", "device_class": "battery",
            "description": "Friendly plain-English label for the user.",
        }],
    }
    out = generate_dashboard_yaml(cap_map, doc)
    # The canonical id must not appear in the rendered name/title.
    # (It is allowed inside entity: lines, but not in the card
    # name/title/icon.)
    for line in _yaml_lines(out):
        if line.lstrip().startswith("- entity:") or line.lstrip().startswith("entity:"):
            continue
        assert "rc_power_internal_id_should_not_leak" not in line, (
            f"canonical id leaked into non-entity line: {line!r}"
        )
    # The friendly description must appear.
    assert "Friendly plain-English label for the user." in out


def test_generate_dashboard_yaml_byte_identical_for_same_inputs():
    """Determinism: same inputs MUST produce byte-identical output."""
    cap_map = {
        "rc_power_thing_0": "sensor.example_0",
        "rc_lighting_thing_2": "switch.example_2",
    }
    out_1 = generate_dashboard_yaml(cap_map, _minimal_doc(4))
    out_2 = generate_dashboard_yaml(cap_map, _minimal_doc(4))
    out_3 = generate_dashboard_yaml(cap_map, _minimal_doc(4))
    assert out_1 == out_2 == out_3


def test_generate_dashboard_yaml_byte_identical_with_real_schema():
    """Determinism holds for the shipped schema + a non-trivial map."""
    schema = _load_schema()
    cap_map = {
        "rc_power_battery_soc": "sensor.vt_battery_soc_percent",
        "rc_power_battery_voltage": "sensor.vt_battery_voltage_v",
        "rc_power_shore_connected": "binary_sensor.vt_shore_connected",
        "rc_lighting_interior_state": "switch.cabin_main",
        "rc_network_internet_reachable": "binary_sensor.rc_net_internet_reachable",
    }
    out_1 = generate_dashboard_yaml(cap_map, schema)
    out_2 = generate_dashboard_yaml(cap_map, schema)
    assert out_1 == out_2


def test_generate_dashboard_yaml_output_is_vendor_neutral():
    """No brand tokens leak into card names, titles, icons, or headings."""
    schema = _load_schema()
    cap_map = {}
    for cap in schema["capabilities"]:
        if cap["type"] != "button":
            cap_map[cap["id"]] = cap["example_sources"][0]
    out = generate_dashboard_yaml(cap_map, schema)
    _assert_vendor_neutral(out)


def test_generate_dashboard_yaml_card_style_compact_is_one_line_per_card():
    """compact style emits the simplest possible card (no extras)."""
    cap_map = {"rc_power_thing_0": "sensor.example_0"}
    out = generate_dashboard_yaml(cap_map, _minimal_doc(1), card_style="compact")
    parsed = _yaml_load(out)
    entity = parsed["vertical-stack"]["cards"][0]["cards"][0]["entities"][0]
    assert "secondary_info" not in entity
    assert "[" not in entity["name"]


def test_generate_dashboard_yaml_card_style_full_adds_secondary_info():
    """full style adds secondary_info='last-changed' on sensors."""
    cap_map = {"rc_power_thing_0": "sensor.example_0"}
    out = generate_dashboard_yaml(cap_map, _minimal_doc(1), card_style="full")
    parsed = _yaml_load(out)
    entity = parsed["vertical-stack"]["cards"][0]["cards"][0]["entities"][0]
    assert entity["secondary_info"] == "last-changed"


def test_generate_dashboard_yaml_card_style_diagnostic_surfaces_ids():
    """diagnostic style surfaces both the canonical id and the entity id."""
    cap_map = {"rc_power_thing_0": "sensor.example_0"}
    out = generate_dashboard_yaml(cap_map, _minimal_doc(1), card_style="diagnostic")
    parsed = _yaml_load(out)
    section = parsed["vertical-stack"]["cards"][0]
    card = section["cards"][0]
    entity = card["entities"][0]
    assert "rc_power_thing_0" in entity["name"]
    assert "sensor.example_0" in entity["name"]
    assert "rc_power_thing_0" in card["title"]


def test_generate_dashboard_yaml_rejects_unknown_card_style():
    with pytest.raises(ValueError):
        generate_dashboard_yaml({}, _minimal_doc(), card_style="magic")


def test_generate_dashboard_yaml_handles_missing_capability_categories():
    """Defensive: a doc without capability_categories still works."""
    doc = {
        "title": "x", "description": "x",
        "capability_categories": None,
        "capabilities": [{
            "id": "rc_power_thing_0", "category": "power", "kind": "telemetry",
            "type": "sensor", "device_class": "battery", "description": "x",
        }],
    }
    # capability_categories is None → no sections → placeholder.
    out = generate_dashboard_yaml({"rc_power_thing_0": "sensor.x"}, doc)
    assert "no capabilities mapped yet" in out


def test_generate_dashboard_yaml_handles_non_dict_capabilities():
    """Defensive: non-dict entries in capabilities are silently skipped."""
    doc = {
        "title": "x", "description": "x",
        "capability_categories": ["power"],
        "capabilities": [
            "not a dict",
            {"id": "rc_power_thing_0", "category": "power", "kind": "telemetry",
             "type": "sensor", "device_class": "battery", "description": "x"},
        ],
    }
    out = generate_dashboard_yaml({"rc_power_thing_0": "sensor.x"}, doc)
    parsed = _yaml_load(out)
    assert len(parsed["vertical-stack"]["cards"]) == 1


def test_generate_dashboard_yaml_skips_capabilities_not_in_map():
    """Capabilities in the schema but absent from the map are skipped."""
    doc = _minimal_doc(4)
    cap_map = {"rc_power_thing_0": "sensor.example_0"}  # only one of four
    out = generate_dashboard_yaml(cap_map, doc)
    parsed = _yaml_load(out)
    # Power section has only one card.
    section = parsed["vertical-stack"]["cards"][0]
    assert len(section["cards"]) == 1


def test_generate_dashboard_yaml_consumes_shipped_schema_end_to_end():
    """End-to-end: render every non-button capability against the shipped schema."""
    schema = _load_schema()
    cap_map = {}
    for cap in schema["capabilities"]:
        if cap["type"] != "button":
            # Use the first example_source as the vendor entity id.
            cap_map[cap["id"]] = cap["example_sources"][0]
    for style in CARD_STYLES:
        out = generate_dashboard_yaml(cap_map, schema, card_style=style)
        parsed = _yaml_load(out)
        assert "vertical-stack" in parsed
        assert isinstance(parsed["vertical-stack"]["cards"], list)
        # Diagnostic mode intentionally surfaces vendor ids (it's
        # the Advanced mode escape hatch); the other styles must
        # stay vendor-neutral.
        if style != "diagnostic":
            _assert_vendor_neutral(out)


def test_generate_dashboard_yaml_empty_after_button_filter_returns_placeholder():
    """If every mapped capability is a button, the placeholder is emitted."""
    doc = {
        "title": "x", "description": "x",
        "capability_categories": ["power"],
        "capabilities": [{
            "id": "rc_power_button_a", "category": "power", "kind": "control",
            "type": "button", "description": "button a",
        }, {
            "id": "rc_power_button_b", "category": "power", "kind": "control",
            "type": "button", "description": "button b",
        }],
    }
    out = generate_dashboard_yaml(
        {"rc_power_button_a": "button.a", "rc_power_button_b": "button.b"},
        doc,
    )
    # Both buttons filtered → no sections → placeholder.
    assert "no capabilities mapped yet" in out
    parsed = _yaml_load(out)
    assert parsed["vertical-stack"]["cards"] == []


# ===========================================================================
# Vendor-neutral surface (extra guards)
# ===========================================================================


def test_rendered_yaml_does_not_mention_unmapped_vendor_entities_in_titles():
    """Card titles must not contain the vendor entity id (compact + full)."""
    cap_map = {"rc_power_thing_0": "sensor.victron_special_vendor_id"}
    doc = _minimal_doc(1)
    for style in ("compact", "full"):
        out = generate_dashboard_yaml(cap_map, doc, card_style=style)
        for line in _yaml_lines(out):
            stripped = line.lstrip()
            if stripped.startswith("- entity:") or stripped.startswith("entity:"):
                continue
            assert "victron_special_vendor_id" not in line, (
                f"vendor entity id leaked into non-entity line ({style}): "
                f"{line!r}"
            )


def test_rendered_yaml_icon_never_contains_vendor_token():
    """Icons must be mdi: prefixed and never contain a vendor token."""
    schema = _load_schema()
    cap_map = {}
    for cap in schema["capabilities"]:
        if cap["type"] != "button":
            cap_map[cap["id"]] = cap["example_sources"][0]
    out = generate_dashboard_yaml(cap_map, schema)
    for line in _yaml_lines(out):
        stripped = line.lstrip()
        if stripped.startswith("icon:"):
            icon = stripped.split(":", 1)[1].strip()
            assert icon.startswith("mdi:"), (
                f"icon is not mdi:-prefixed: {line!r}"
            )
            for tok in FORBIDDEN_VENDOR_TOKENS:
                assert tok not in icon.lower(), (
                    f"icon contains vendor token {tok!r}: {line!r}"
                )


def test_generate_dashboard_yaml_uses_section_type_vertical_stack():
    """Every section is a vertical-stack — the canonical Lovelace wrapper."""
    cap_map = {
        "rc_power_thing_0": "sensor.example_0",
        "rc_lighting_thing_2": "switch.example_2",
    }
    out = generate_dashboard_yaml(cap_map, _minimal_doc(4))
    parsed = _yaml_load(out)
    for section in parsed["vertical-stack"]["cards"]:
        assert section["type"] == "vertical-stack"
        assert "cards" in section
        for card in section["cards"]:
            assert card["type"] == "entities"


def test_generate_dashboard_yaml_entity_lines_use_dash_prefix():
    """Each entity inside an entities: card is a dash-prefixed list item."""
    cap_map = {"rc_power_thing_0": "sensor.example_0"}
    out = generate_dashboard_yaml(cap_map, _minimal_doc(1))
    # The YAML emitter uses "- entity: …" for each entity line.
    assert "- entity: sensor.example_0" in out
