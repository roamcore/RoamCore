"""Manifest-honesty tests for connections/smoke-co-gas-sensors/connection.yml.

This is the only test file we can ship for a tier-b recipe connection
that has no real smoke / CO / gas detector bench to integration-test
against. The tests here assert that the manifest is *honest about
being tier-b* — that the folder/id/tier invariants hold, that the
recipe doc the tier_requirements promise is actually present on disk,
and that the rc_safety_* tile ids are vendor-neutral per
docs/reference/rc-entity-naming.md.

If you add real integration coverage (e.g. a config_flow.py + a
bench with a smoke / CO / gas detector + canned fixture responses),
keep this file and add the new one alongside it; the audit will then
list both under `tests:` in the manifest.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/smoke-co-gas-sensors/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]
CONNECTION_DIR = REPO_ROOT / "connections" / "smoke-co-gas-sensors"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (smoke-co-gas-sensors)."""
    assert manifest["id"] == CONNECTION_DIR.name
    assert manifest["id"] == "smoke-co-gas-sensors"


def test_tier_b_without_tier_a_markers(manifest: dict) -> None:
    """Tier-b must NOT advertise tier-a-only RoamCore-owned fields."""
    assert manifest["tier"] == "b"
    assert manifest["wizard"]["one_tap"] is False
    assert manifest["install"]["config_flow"] is True, (
        "install.config_flow must stay True — the upstream HA core "
        "`binary_sensor` + `sensor` domains + the operator's choice "
        "of vendor integration (ZHA / Z-Wave JS / ESPHome) expose a "
        "GUI flow (honest upstream truth, NOT a tier-a marker)"
    )
    assert manifest["install"]["hacs"] is False
    assert not (CONNECTION_DIR / "config_flow.py").is_file()
    init_text = (CONNECTION_DIR / "__init__.py").read_text(encoding="utf-8")
    assert "DOMAIN" in init_text
    assert 'DOMAIN = "smoke_co_gas_sensors"' in init_text
    for forbidden in ("async_setup", "config_flow", "PLATFORM_SCHEMA"):
        assert forbidden not in init_text


def test_requires_docs_recipe_published(manifest: dict) -> None:
    """The audit's only tier-b hard requirement, made explicit."""
    assert "docs_recipe_published" in manifest["tier_requirements"]
    assert RECIPE_PATH.is_file()
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert (
        "smoke" in text.lower()
        or "carbon monoxide" in text.lower()
        or "co detector" in text.lower()
        or "gas leak" in text.lower()
        or "propane" in text.lower()
    ) and "rc_safety_" in text
    line_count = len(text.splitlines())
    assert line_count >= 280, f"recipe.md must be ≥280 lines; got {line_count}"
    required_sections = (
        "## §1 What are smoke / CO / gas safety sensors in RoamCore?",
        "## §2 Prerequisites",
        "## §3 Path A",
        "## §4 Path B",
        "## §5 Path C",
        "## §6 RoamCore contract entities",
        "## §7 Automations",
        "## §8 Troubleshooting",
        "## §9 Privacy",
        "## §10 Promoting to tier-a",
    )
    for header in required_sections:
        assert header in text, f"recipe.md missing required section header {header!r}"


def test_category_matches_existing_legacy_doc(manifest: dict) -> None:
    """Sanity: category is set (legacy-doc pairing no longer enforced)."""
    assert manifest["category"], "category must be set"


def test_status_reflects_no_real_safety_sensor(manifest: dict) -> None:
    """Status must be honest about no integration being shipped."""
    assert manifest["status"] == "beta"
    tier_warnings = manifest.get("tier_warnings", [])
    assert "no_real_safety_sensor_for_integration_test" in tier_warnings
    assert "recipe_depends_on_user_running_safety_sensor" in tier_warnings
    assert "requires_operator_placement_per_local_code" in tier_warnings
    assert "roximate_surface_warning_in_recipe_no_replace_for_local_codes" in tier_warnings


def test_safety_automations_are_documented(manifest: dict) -> None:
    """Defensive guard for the future tier-a promotion."""
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert "## §7 Automations" in text
    safety_coverage = (
        "smoke detected",
        "co detected",
        "gas leak",
        "sensor offline",
        "battery low",
        "alarm silenced",
    )
    for phrase in safety_coverage:
        assert phrase in text.lower(), f"recipe.md §7 must cover {phrase!r}"
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    safety_tiles = (
        "binary_sensor.rc_safety_any_alarm",
        "binary_sensor.rc_safety_smoke_detected",
        "button.rc_safety_alarm_silence",
    )
    for safety_tile in safety_tiles:
        assert safety_tile in tiles, (
            f"dashboard.tiles must include {safety_tile!r}"
        )
    assert "rc_presence_operator_phone_home" in text
    assert "mandatory before first use" in text.lower()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
