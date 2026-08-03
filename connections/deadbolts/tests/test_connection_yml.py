"""Manifest-honesty tests for connections/deadbolts/connection.yml.

This is the only test file we can ship for a tier-b recipe connection
that has no real smart deadbolt (Z-Wave / Zigbee / Matter) on the CI
bench to integration-test against. The tests here assert that the
manifest is *honest about being tier-b* — that the folder/id/tier
invariants hold, that the recipe doc the tier_requirements promise
is actually present on disk, and that the rc_safety_lock_* tile ids
are vendor-neutral per docs/reference/rc-entity-naming.md.

If you add real integration coverage (e.g. a config_flow.py + a
bench with a Z-Wave / Zigbee / Matter deadbolt + canned fixture
responses), keep this file and add the new one alongside it; the
audit will then list both under `tests:` in the manifest.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/deadbolts/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]
CONNECTION_DIR = REPO_ROOT / "connections" / "deadbolts"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (deadbolts)."""
    assert manifest["id"] == CONNECTION_DIR.name
    assert manifest["id"] == "deadbolts"


def test_tier_b_without_tier_a_markers(manifest: dict) -> None:
    """Tier-b must NOT advertise tier-a-only RoamCore-owned fields."""
    assert manifest["tier"] == "b"
    assert manifest["wizard"]["one_tap"] is False
    assert manifest["install"]["config_flow"] is True, (
        "install.config_flow must stay True — the upstream HA core "
        "`zwave_js` (Path A) + `zha` (Path B) + `matter` (Path C) "
        "integrations ALL expose a GUI flow since 2022.x / 2023.x; "
        "this is honest upstream truth, NOT a tier-a marker for "
        "RoamCore's tier. The tier-a marker for RoamCore would be "
        "a RoamCore-owned `config_flow.py` + RoamCore-owned "
        "integration code + integration tests against a "
        "RoamCore-owned deadbolt bench. None of those are shipped "
        "at tier-b."
    )
    assert manifest["install"]["hacs"] is False
    assert not (CONNECTION_DIR / "config_flow.py").is_file()
    init_text = (CONNECTION_DIR / "__init__.py").read_text(encoding="utf-8")
    assert "DOMAIN" in init_text
    assert 'DOMAIN = "deadbolts"' in init_text
    for forbidden in ("async_setup", "config_flow", "PLATFORM_SCHEMA"):
        assert forbidden not in init_text, (
            f"__init__.py must be a DOMAIN stub; found {forbidden!r} "
            f"(tier-b recipe pattern)"
        )


def test_requires_docs_recipe_published(manifest: dict) -> None:
    """The audit's only tier-b hard requirement, made explicit."""
    assert "docs_recipe_published" in manifest["tier_requirements"]
    assert RECIPE_PATH.is_file()
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert (
        "deadbolts" in text.lower()
        or "smart lock" in text.lower()
        or "smart deadbolt" in text.lower()
    ) and "rc_safety_lock_" in text, (
        "recipe.md must document the deadbolt setup (Path A Z-Wave, "
        "Path B Zigbee, Path C Matter, contract entities, "
        "automations, troubleshooting) and reference at least one "
        "`rc_safety_lock_*` tile"
    )
    line_count = len(text.splitlines())
    assert line_count >= 280, (
        f"recipe.md must be a substantive howto (≥280 lines per "
        f"spec); got {line_count}"
    )
    required_sections = (
        "## §1 What are Deadbolts in RoamCore?",
        "## §2 Prerequisites",
        "## §3 Path A",
        "## §4 Path B",
        "## §5 Path C",
        "## §6 RoamCore contract entities",
        "## §7 Safety interlocks",
        "## §8 Troubleshooting",
        "## §9 Privacy",
        "## §10 Promoting to tier-a",
    )
    for header in required_sections:
        assert header in text, (
            f"recipe.md is missing required section header {header!r}"
        )


def test_category_matches_existing_legacy_doc(manifest: dict) -> None:
    """Sanity: category is set (legacy-doc pairing no longer enforced)."""
    assert manifest["category"], "category must be set"


def test_status_reflects_no_real_deadbolt(manifest: dict) -> None:
    """Status must be honest about no integration being shipped."""
    assert manifest["status"] == "beta"
    tier_warnings = manifest.get("tier_warnings", [])
    assert "no_real_deadbolt_for_integration_test" in tier_warnings, (
        "tier_warnings must declare 'no_real_deadbolt_for_integration_test' "
        "for honesty in the audit listing"
    )
    assert (
        "recipe_depends_on_user_running_zwave_or_zigbee_or_matter_lock_plus_protocol_integration"
        in tier_warnings
    ), (
        "tier_warnings must declare "
        "'recipe_depends_on_user_running_zwave_or_zigbee_or_matter_"
        "lock_plus_protocol_integration' so the audit listing is "
        "honest about the operator's hardware + protocol-integration "
        "dependency"
    )
    assert (
        "requires_zwave_js_or_zha_or_matter_integration_already_configured"
        in tier_warnings
    ), (
        "tier_warnings must declare "
        "'requires_zwave_js_or_zha_or_matter_integration_already_"
        "configured' so the audit listing is honest that the recipe "
        "depends on the operator already running the upstream "
        "protocol integration"
    )
    assert "requires_thread_border_router_for_path_c" in tier_warnings, (
        "tier_warnings must declare "
        "'requires_thread_border_router_for_path_c' so the audit "
        "listing is honest about the Path C Thread border router "
        "prerequisite"
    )


def test_safety_interlocks_are_documented(manifest: dict) -> None:
    """Defensive guard for the future tier-a promotion.

    Smart deadbolt control is a safety-relevant surface in the
    van (the operator MUST be able to get OUT of the van even if
    the door was auto-locked at bedtime, AND unexpected unlocks
    while no one is home are an intruder alert). The recipe §7
    walks through the 6 MANDATORY safety interlocks:
      - §7.1 Away auto-lock via `select.rc_mode`
      - §7.2 Sleep auto-lock + auto-relock
      - §7.3 Unattended-unlock alarm (cross-references
        bluetooth-wifi-presence Wave 3 #42 via
        `binary_sensor.rc_presence_anyone_home`)
      - §7.4 CO egress-required override (cross-references
        smoke-co-gas-sensors Wave 3 #45 via
        `binary_sensor.rc_safety_co_detected`)
      - §7.5 Low-voltage lockout (cross-references Victron via
        `sensor.rc_power_battery_soc`)
      - §7.6 Multi-door aggregate

    The test asserts all six are documented in the recipe so that
    when this connection promotes to tier-a (with a real Z-Wave /
    Zigbee / Matter deadbolt on CI + the 6 safety interlock asserts
    hard-enforced in RoamCore code rather than only documented in
    the recipe), the audit has a clean assertion to flip.
    """
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert "## §7 Safety interlocks" in text, (
        "recipe.md must have a '## §7 Safety interlocks' section "
        "(the 6 MANDATORY safety interlocks documentation block)"
    )
    safety_coverage = (
        "away auto-lock",
        "sleep auto-lock",
        "auto-relock",
        "unattended-unlock alarm",
        "co egress-required",
        "low-voltage lockout",
        "multi-door aggregate",
    )
    for phrase in safety_coverage:
        assert phrase in text.lower(), (
            f"recipe.md §7 must cover {phrase!r}; the six safety "
            f"interlocks are MANDATORY before first use, and the "
            f"recipe is the only documentation operator + future-"
            f"tier-a integration code have at this tier"
        )
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    safety_tiles = (
        "binary_sensor.rc_safety_lock_any_unlocked",
        "binary_sensor.rc_safety_lock_unexpected_unlock",
        "binary_sensor.rc_safety_lock_co_egress_required",
        "binary_sensor.rc_safety_lock_low_voltage_lockout",
    )
    for safety_tile in safety_tiles:
        assert safety_tile in tiles, (
            f"dashboard.tiles must include {safety_tile!r}; the "
            f"safety interlock aggregate tiles are part of the "
            f"contract layer that the recipe §7 documents"
        )
    # The recipe must cross-reference the smoke-co-gas-sensors
    # Wave 3 #45 connection via `binary_sensor.rc_safety_co_detected`
    # so the §7.4 CO egress-required override is discoverable.
    assert "binary_sensor.rc_safety_co_detected" in text, (
        "recipe.md must reference `binary_sensor.rc_safety_co_detected` "
        "for the §7.4 CO egress-required override cross-reference to "
        "the smoke-co-gas-sensors `connections/smoke-co-gas-sensors/` "
        "recipe"
    )
    # The recipe must cross-reference the bluetooth-wifi-presence
    # Wave 3 #42 connection via `binary_sensor.rc_presence_anyone_home`
    # so the §7.3 unattended-unlock alarm is discoverable.
    assert "binary_sensor.rc_presence_anyone_home" in text, (
        "recipe.md must reference `binary_sensor.rc_presence_anyone_home` "
        "for the §7.3 unattended-unlock alarm cross-reference to "
        "the bluetooth-wifi-presence `connections/bluetooth-wifi-"
        "presence/` recipe"
    )
    # The recipe must cross-reference the Victron connection via
    # `sensor.rc_power_battery_soc` so the §7.5 low-voltage lockout
    # is discoverable.
    assert "sensor.rc_power_battery_soc" in text, (
        "recipe.md must reference `sensor.rc_power_battery_soc` for "
        "the §7.5 low-voltage lockout cross-reference to the Victron "
        "`connections/victron/` recipe"
    )
    # The recipe must cross-reference the mode/automation-builder
    # connection via `select.rc_mode` so the §7.1 + §7.2 mode-aware
    # auto-lock is discoverable.
    assert "select.rc_mode" in text, (
        "recipe.md must reference `select.rc_mode` for the §7.1 Away "
        "auto-lock + §7.2 Sleep auto-lock cross-reference to the mode/"
        "automation-builder `connections/mode-automation-builder/` recipe"
    )
    # The recipe must reference the storage compartment tile so the
    # §7.4 CO egress-required override's "storage compartment can
    # stay locked — it's not on the egress path" guidance is
    # discoverable.
    assert "storage_compartment" in text, (
        "recipe.md must reference `storage_compartment` for the §7.4 "
        "CO egress-required override's egress-path guidance"
    )
    # The recipe must use the 'MANDATORY before first use' emphasis.
    assert "mandatory before first use" in text.lower(), (
        "recipe.md §7 must use the 'MANDATORY before first use' "
        "emphasis on the six safety interlocks; this is the "
        "operator-side reminder that keeps the safety interlocks "
        "top-of-mind during install"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))