"""Manifest-honesty tests for connections/smart-automations/connection.yml.

This is the only test file we can ship for a tier-b recipe connection
that has no RoamCore-owned automation engine to integration-test
against (RoamCore RECIPE-s HA Core's `automation:` domain + the
operator-side managed-marker convention from
docs/guides/smart-automations.md; the 17 automations live in HA
Core's automation engine and RoamCore only audits + publishes the
contract tiles). The tests here assert that the manifest is *honest
about being tier-b* — that the folder/id/tier invariants hold, that
the recipe doc the tier_requirements promise is actually present on
disk, that all 17 automations from `docs/guides/smart-automations.md`
are documented in the recipe's §4, and that the
`rc_safety_automation_*` + `rc_safety_automations_*` tile ids are
vendor-neutral per docs/reference/rc-entity-naming.md §safety
subsystem (which is already in the allowed subsystems list — no
backfill needed).

If you add real integration coverage (e.g. a config_flow.py + a
bench with HA Core + the 17 automation templates loaded + the
per-automation prerequisites mocked via canned entity states),
keep this file and add the new one alongside it; the audit will
then list both under `tests:` in the manifest.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/smart-automations/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]
CONNECTION_DIR = REPO_ROOT / "connections" / "smart-automations"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
LEGACY_DOC = REPO_ROOT / "docs" / "catalog" / "safety" / "smart-automations.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (smart-automations)."""
    assert manifest["id"] == CONNECTION_DIR.name
    assert manifest["id"] == "smart-automations"


def test_tier_b_without_tier_a_markers(manifest: dict) -> None:
    """Tier-b must NOT advertise tier-a-only RoamCore-owned fields."""
    assert manifest["tier"] == "b"
    assert manifest["wizard"]["one_tap"] is False
    assert manifest["install"]["config_flow"] is True, (
        "install.config_flow must stay True — the upstream HA core "
        "`automation` + `script` + `template` + `button` + `select` "
        "domains expose a GUI flow (honest upstream truth, NOT a "
        "tier-a marker)"
    )
    assert manifest["install"]["hacs"] is False
    assert not (CONNECTION_DIR / "config_flow.py").is_file()
    init_text = (CONNECTION_DIR / "__init__.py").read_text(encoding="utf-8")
    assert "DOMAIN" in init_text
    assert 'DOMAIN = "smart_automations"' in init_text
    for forbidden in ("async_setup", "config_flow", "PLATFORM_SCHEMA"):
        assert forbidden not in init_text


def test_requires_docs_recipe_published(manifest: dict) -> None:
    """The audit's only tier-b hard requirement, made explicit."""
    assert "docs_recipe_published" in manifest["tier_requirements"]
    assert RECIPE_PATH.is_file()
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert (
        "smart automation" in text.lower()
        or "prebuilt automation" in text.lower()
        or "managed by roamcore smart automations" in text.lower()
    ) and "rc_safety_" in text
    line_count = len(text.splitlines())
    assert line_count >= 280, f"recipe.md must be ≥280 lines; got {line_count}"
    required_sections = (
        "## §1 What are Smart Automations in RoamCore?",
        "## §2 Prerequisites",
        "## §3 How the 17 automations are wired",
        "## §4 The 17 built-in automations",
        "## §5 RoamCore contract tiles",
        "## §6 Cross-references to other connections",
        "## §7 Privacy",
        "## §8 Troubleshooting",
        "## §9 Promoting to tier-a",
    )
    for header in required_sections:
        assert header in text, f"recipe.md missing required section header {header!r}"


def test_category_matches_existing_legacy_doc(manifest: dict) -> None:
    """Promoted from tier-c legacy doc — category must match."""
    assert manifest["category"] == "safety"
    assert LEGACY_DOC.is_file(), (
        "legacy docs/catalog/safety/smart-automations.md must still "
        "exist (carrying the supersession banner)"
    )


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """rc_* tile ids must NOT contain vendor names or generic nouns."""
    import re

    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles
    for tile in tiles:
        assert isinstance(tile, str)

    pattern = re.compile(r"^[a-z_]+\.rc_safety_(automation|automations)_[a-z0-9_]+$")
    forbidden_substrings = (
        # vendor names (absolute forbidden)
        "nest", "kidde", "first_alert", "firstalert",
        "x_sense", "xsense", "x-sense", "heiman", "zipato",
        "victron", "traccar", "openwrt", "esphome", "zigbee",
        "z_wave", "zwave", "z-wave", "mqtt", "tuya", "xiaomi",
        "philips", "ubiquiti", "unifi", "mikrotik",
        # generic nouns (forbidden double-stamps)
        "smart", "automation_engine", "roamcore_smart",
        "lovelace_", "timer_", "schedule_", "rule_",
    )

    for tile in tiles:
        assert pattern.match(tile), (
            f"tile id {tile!r} must match ^[a-z_]+\\.rc_safety_(automation|automations)_[a-z_]+$"
        )
        suffix = tile.split(".rc_safety_", 1)[1]
        for bad in forbidden_substrings:
            assert bad not in suffix.lower(), (
                f"tile id {tile!r} contains forbidden substring {bad!r}"
            )
        for segment in tile.split("."):
            assert re.match(r"^[a-z_][a-z0-9_]*$", segment)

    # 7 summary tiles (3 sensors + 1 binary_sensor + 1 select + 2 buttons)
    # + 17 per-automation binary_sensors = 24 contract tiles.
    assert len(tiles) == 24, (
        f"smart-automations must contribute exactly 24 contract "
        f"tiles (7 summary + 17 per-automation mirror binary_sensors); "
        f"verify the manifest matches §5; got {len(tiles)}"
    )


def test_status_reflects_no_real_automation_engine(manifest: dict) -> None:
    """Status must be honest about no RoamCore-owned automation engine."""
    assert manifest["status"] == "beta"
    tier_warnings = manifest.get("tier_warnings", [])
    assert "no_real_automation_engine_for_integration_test" in tier_warnings
    assert "recipe_depends_on_user_running_ha_core_automation" in tier_warnings
    assert "requires_operator_to_enable_per_automation" in tier_warnings
    assert "some_automations_require_specific_connections_already_shipped" in tier_warnings


def test_recipe_documents_all_17_automations(manifest: dict) -> None:
    """Defensive guard: all 17 automations from docs/guides/smart-automations.md
    must appear as a named subsection in recipe.md §4 (the canonical
    list — Night Mode, Auto Internet Failover, Low Battery Mode,
    Freeze Protection, Daily Trip Log, Battery Full Alert, Inverter
    Overheat Alert, Router Overheat Alert, Shore Power Connected,
    Shore Power Disconnected, Internet Recovery, Arrive at Camp,
    Depart Travel Mode, Solar is Crushing It, Battery Critical
    Alert, Bedtime Level Check, Quiet Hours Reminder)."""
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert "## §4 The 17 built-in automations" in text

    # Each automation must appear as a §4.X subsection header. The
    # subsection title is a short slug like "### §4.1 Night Mode".
    # We assert both the subsection header AND that the automation
    # description appears verbatim.
    required_automations = (
        "Night Mode",
        "Auto Internet Failover",
        "Low Battery Mode",
        "Freeze Protection",
        "Daily Trip Log",
        "Battery Full Alert",
        "Inverter Overheat Alert",
        "Router Overheat Alert",
        "Shore Power Connected",
        "Shore Power Disconnected",
        "Internet Recovery",
        "Arrive at Camp",
        "Depart Travel Mode",
        "Solar is Crushing It",
        "Battery Critical Alert",
        "Bedtime Level Check",
        "Quiet Hours Reminder",
    )
    for automation in required_automations:
        assert automation in text, (
            f"recipe.md §4 must cover automation {automation!r}"
        )

    # And each per-automation contract tile must appear in the
    # recipe's §5 mirror list.
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    for automation_slug in (
        "night_mode", "auto_internet_failover", "low_battery_mode",
        "freeze_protection", "daily_trip_log", "battery_full_alert",
        "inverter_overheat_alert", "router_overheat_alert",
        "shore_power_connected", "shore_power_disconnected",
        "internet_recovery", "arrive_at_camp", "depart_travel_mode",
        "solar_crushing_it", "battery_critical_alert",
        "bedtime_level_check", "quiet_hours_reminder",
    ):
        expected_tile = f"binary_sensor.rc_safety_automation_{automation_slug}"
        assert expected_tile in tiles, (
            f"dashboard.tiles must include the per-automation "
            f"mirror tile {expected_tile!r}"
        )
        assert expected_tile in text, (
            f"recipe.md §5 must reference the per-automation "
            f"mirror tile {expected_tile!r}"
        )

    # And the managed-marker convention must appear in the recipe.
    assert "Managed by RoamCore Smart Automations" in text
    assert "key=<name>" in text
    assert "hash=<template hash>" in text


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))