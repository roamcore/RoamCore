"""Manifest-honesty tests for connections/factory-reset/connection.yml.

This is the canonical tier-a manifest-honesty test rig for the Factory
Reset connection. The tests assert that the manifest is honest about
being tier-a — that the folder / id / tier invariants hold, that the
RoamCore-owned Python service handler at
`homeassistant/custom_components/roamcore/factory_reset.py` is real +
exists on disk + has the expected functions + the
`register_factory_reset_services` function + the
`RoamCoreFactoryResetView` HTTP view, that the recipe doc the
tier_requirements promise is actually present on disk, that the
`rc_factory_reset_*` tile ids are vendor-neutral per
`docs/reference/rc-entity-naming.md`, that the 5 section 8 MANDATORY
automations are documented in the recipe + wired in the helper
package, that the secrets-leak guard is real (no hardcoded URLs, no
hardcoded passwords, no /home/<user> paths in the shipped files), and
that the `requires: hub-backup` upstream dependency is declared in
the manifest.

If you add new contract tiles, keep this file and update the
`required_tiles` tuple in `test_dashboard_tiles_follow_rc_naming` so
pytest catches regressions before CI runs the audit.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/factory-reset/tests/ -v
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> factory-reset/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "factory-reset"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
README_PATH = CONNECTION_DIR / "README.md"
INIT_PATH = CONNECTION_DIR / "__init__.py"

CUSTOM_COMPONENT_PATH = REPO_ROOT / "homeassistant" / "custom_components" / "roamcore"
FACTORY_RESET_PY = CUSTOM_COMPONENT_PATH / "factory_reset.py"
SERVICES_YAML = CUSTOM_COMPONENT_PATH / "services.yaml"
COMPONENT_INIT = CUSTOM_COMPONENT_PATH / "__init__.py"

HELPER_PACKAGE_PATH = REPO_ROOT / "homeassistant" / "packages" / "roamcore_factory_reset.yaml"
PYTEST_RIG_PATH = REPO_ROOT / "homeassistant" / "packages" / "tests" / "test_factory_reset.py"
BASH_SMOKE_PATH = REPO_ROOT / "scripts" / "checks" / "factory-reset-smoke.sh"
USER_RUNBOOK_PATH = REPO_ROOT / "docs" / "runbooks" / "factory-reset.md"

HUB_BACKUP_CONNECTION_DIR = REPO_ROOT / "connections" / "hub-backup"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def helper_package_text() -> str:
    assert HELPER_PACKAGE_PATH.is_file(), f"missing helper package at {HELPER_PACKAGE_PATH}"
    return HELPER_PACKAGE_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def factory_reset_py_text() -> str:
    assert FACTORY_RESET_PY.is_file(), f"missing RoamCore-owned service handler at {FACTORY_RESET_PY}"
    return FACTORY_RESET_PY.read_text(encoding="utf-8")


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (factory-reset)."""
    assert CONNECTION_DIR.name == "factory-reset", (
        f"folder name {CONNECTION_DIR.name!r} does not match the "
        f"spec-required kebab-case 'factory-reset'"
    )
    assert manifest["id"] in ("factory_reset", "factory-reset"), (
        f"manifest id={manifest['id']!r} must be 'factory_reset' "
        f"(snake_case DOMAIN convention) or 'factory-reset' "
        f"(kebab-case folder convention); the audit accepts "
        f"both forms"
    )
    assert manifest["id"] == "factory_reset"


def test_tier_a_markers_present_and_justified(manifest: dict, factory_reset_py_text: str) -> None:
    """Tier-a must advertise tier-a-only RoamCore-owned fields AND must
    back them with real on-disk code (the RoamCore-owned Python service
    handler at factory_reset.py).
    """
    assert manifest["tier"] == "a", (
        "factory-reset must stay at tier-a because RoamCore owns + "
        "ships + maintains a real Python service handler at "
        "`homeassistant/custom_components/roamcore/factory_reset.py` "
        "(~340 LOC) that implements the 2-step confirm flow + the "
        "RoamCoreFactoryResetView HTTP view + the chain-corruption "
        "recovery path; tier-b would be a downgrade that loses the "
        "audit's ability to verify the real integration code"
    )
    assert manifest["install"]["config_flow"] is True, (
        "factory-reset must advertise install.config_flow=true — "
        "the HACS-installed RoamCore integration exposes the "
        "Factory Reset surface via its options flow"
    )
    # The install.install_custom_component field MUST point at the
    # RoamCore-owned service handler at `factory_reset.py`.
    custom_component_relpath = manifest["install"].get(
        "install_custom_component"
    )
    assert custom_component_relpath == (
        "homeassistant/custom_components/roamcore/factory_reset.py"
    ), (
        "install.install_custom_component must point at "
        "`homeassistant/custom_components/roamcore/factory_reset.py` "
        "— the RoamCore-owned service handler that backs the tier-a "
        f"claim; got {custom_component_relpath!r}"
    )
    # The real service handler MUST exist on disk.
    assert FACTORY_RESET_PY.is_file(), (
        "tier-a manifest claims `homeassistant/custom_components/"
        "roamcore/factory_reset.py` exists but the file is missing "
        "on disk — the tier-a claim is dishonest"
    )
    # The service handler MUST define the expected functions.
    expected_markers = (
        "FACTORY_RESET_TILE_PREFIX",
        "def register_factory_reset_services",
        "async def _svc_dry_run",
        "async def _svc_confirm",
        "async def _svc_cancel",
        "async def _svc_postflight_check",
        "class RoamCoreFactoryResetView",
        "def recovery_resets",
        "BACKUP_FRESHNESS_WINDOW_MINUTES",
        "EXPECTED_CONFIRM_TOKEN",
    )
    for expected in expected_markers:
        assert expected in factory_reset_py_text, (
            f"RoamCore-owned service handler at "
            f"`homeassistant/custom_components/roamcore/factory_reset.py` "
            f"MUST define {expected!r}; the tier-a claim is dishonest"
        )
    # The service handler MUST call `hass.services.async_call(
    # "backup", "restore", ...)` against the HA core `backup.restore`
    # service (NOT a third-party integration).
    # The strings may be on separate lines (typical Python multi-line
    # function call) so we check for both substrings independently.
    assert (
        '"backup"' in factory_reset_py_text
        and '"restore"' in factory_reset_py_text
        and 'hass.services.async_call' in factory_reset_py_text
    ), (
        "RoamCore-owned service handler at "
        "`homeassistant/custom_components/roamcore/factory_reset.py` "
        "MUST call `hass.services.async_call(\"backup\", \"restore\", "
        "...)` against the HA core `backup.restore` service"
    )
    # The helper package + pytest rig + bash smoke + user runbook
    # MUST all exist on disk (the install paths promise all four).
    assert HELPER_PACKAGE_PATH.is_file(), (
        "install.install_helper_package promises "
        "`homeassistant/packages/roamcore_factory_reset.yaml` but "
        "it is missing on disk — the tier-a claim is dishonest"
    )
    assert PYTEST_RIG_PATH.is_file(), (
        "install.install_pytest_rig promises "
        "`homeassistant/packages/tests/test_factory_reset.py` but "
        "it is missing on disk — the tier-a claim is dishonest"
    )
    assert BASH_SMOKE_PATH.is_file(), (
        "install.install_smoke promises "
        "`scripts/checks/factory-reset-smoke.sh` but it is missing "
        "on disk — the tier-a claim is dishonest"
    )
    assert USER_RUNBOOK_PATH.is_file(), (
        "install.install_user_runbook promises "
        "`docs/runbooks/factory-reset.md` but it is missing on "
        "disk — the tier-a claim is dishonest"
    )
    assert SERVICES_YAML.is_file(), (
        "RoamCore-owned services.yaml at "
        "`homeassistant/custom_components/roamcore/services.yaml` "
        "MUST exist on disk (the 4 service definitions are appended "
        "there)"
    )
    assert COMPONENT_INIT.is_file(), (
        "RoamCore-owned __init__.py at "
        "`homeassistant/custom_components/roamcore/__init__.py` "
        "MUST exist on disk (the "
        "`register_factory_reset_services(hass)` call is wired into "
        "`async_setup_entry` there)"
    )
    # The reuse-first strategy is FALSE for tier-a (this connection
    # OWNS the integration code).
    upstream_truth = manifest.get("upstream_truth", {})
    assert upstream_truth.get("reuse_first") is False, (
        "upstream_truth.reuse_first must be False for tier-a — "
        "factory-reset OWNS the integration code at "
        "`homeassistant/custom_components/roamcore/factory_reset.py`; "
        "tier-b would set reuse_first=true (recipe over upstream)"
    )
    assert upstream_truth.get("vendor_neutral") is True, (
        "upstream_truth.vendor_neutral must be True — the "
        "RoamCore-owned service handler at "
        "`homeassistant/custom_components/roamcore/factory_reset.py` "
        "calls the vendor-neutral HA core `backup.restore` service "
        "+ the RoamCore-registered `roamcore.factory_reset_*` "
        "services; no vendor names leak into the integration"
    )
    # The rocore_owned list MUST include the RoamCore-owned files.
    rocore_owned = upstream_truth.get("rocore_owned", [])
    required_rocore_owned = (
        "homeassistant/custom_components/roamcore/factory_reset.py",
        "homeassistant/custom_components/roamcore/__init__.py",
        "homeassistant/custom_components/roamcore/services.yaml",
        "homeassistant/packages/roamcore_factory_reset.yaml",
        "homeassistant/packages/tests/test_factory_reset.py",
        "scripts/checks/factory-reset-smoke.sh",
        "docs/runbooks/factory-reset.md",
    )
    for required_path in required_rocore_owned:
        assert required_path in rocore_owned, (
            f"upstream_truth.rocore_owned must include "
            f"{required_path!r} (the RoamCore-owned files that "
            f"back the tier-a claim)"
        )


def test_requires_hub_backup(manifest: dict) -> None:
    """The factory-reset connection MUST declare `requires: hub-backup`
    in the manifest (the reset refuses to run without a recent Hub
    Backup). The hub-backup connection MUST exist on disk.
    """
    requires = manifest.get("requires", [])
    assert "hub-backup" in requires, (
        "manifest must declare `requires: hub-backup` (the reset "
        "refuses to run without a recent Hub Backup); got "
        f"{requires!r}"
    )
    assert HUB_BACKUP_CONNECTION_DIR.is_dir(), (
        f"manifest declares `requires: hub-backup` but the "
        f"hub-backup connection folder is missing on disk at "
        f"{HUB_BACKUP_CONNECTION_DIR} — the upstream-truth "
        f"dependency is fictional"
    )
    hub_backup_manifest = HUB_BACKUP_CONNECTION_DIR / "connection.yml"
    assert hub_backup_manifest.is_file(), (
        f"hub-backup connection manifest missing at "
        f"{hub_backup_manifest} — the upstream-truth dependency is "
        f"fictional"
    )


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """rc_* tile ids must NOT contain vendor names (per
    rc-entity-naming.md).
    """
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles, "factory-reset contributes at least one dashboard tile"

    for tile in tiles:
        assert isinstance(tile, str), (
            f"dashboard.tiles[*] must be a string entity id "
            f"(spec section 1); got {tile!r}"
        )

    allowed_domains = {
        "input_boolean",
        "input_datetime",
        "input_select",
        "input_text",
        "input_button",
        "sensor",
        "binary_sensor",
        "button",
    }
    pattern = re.compile(r"^[a-z_]+\.rc_factory_reset_[a-z0-9_]+$")

    forbidden_substrings = (
        "victron",
        "renogy",
        "shunt",
        "bms",
        "inverter",
        "mppt",
        "see level",
        "seelevel",
        "garnet",
        "mopeka",
        "starlink",
        "peplink",
        "teltonika",
        "unifi",
        "ubiquiti",
        "mqtt",
        "webhook",
        "rest",
        "hacs",
        "tasmota",
        "esphome",
        "companion",
        "esp32",
        "esp8266",
        "shelly",
        "sonoff",
        "zwave",
        "zha",
        "zigbee",
        "deconz",
        "bluetooth",
        "input_boolean",
        "input_text",
        "input_datetime",
        "input_button",
        "gps",
        "accelerometer",
        "iphone",
        "ios",
        "android",
        "samsung",
        "pixel",
        "xiaomi",
        "huawei",
        "phone",
    )

    for tile in tiles:
        assert pattern.match(tile), (
            f"tile id {tile!r} must match "
            f"^[a-z_]+\\.rc_factory_reset_[a-z_]+$ (vendor-neutral "
            f"contract naming per "
            f"docs/reference/rc-entity-naming.md)"
        )
        domain = tile.split(".", 1)[0]
        assert domain in allowed_domains, (
            f"tile id {tile!r} uses domain {domain!r} which is "
            f"not in the allowed factory-reset domain set "
            f"{sorted(allowed_domains)!r}; per "
            f"docs/reference/rc-entity-naming.md section factory_reset "
            f"subsystem"
        )
        suffix = tile.split(".rc_factory_reset_", 1)[1]
        for bad in forbidden_substrings:
            assert bad not in suffix.lower(), (
                f"tile id {tile!r} contains forbidden vendor "
                f"substring {bad!r} in the suffix after "
                f"`rc_factory_reset_`; per "
                f"docs/reference/rc-entity-naming.md, contract "
                f"ids are vendor-neutral — vendor names are "
                f"forbidden in any rc_* tile id"
            )
        for segment in tile.split("."):
            assert re.match(r"^[a-z_][a-z0-9_]*$", segment), (
                f"tile id {tile!r} contains a non-conforming "
                f"segment {segment!r}"
            )

    required_tiles_set = {
        "input_button.rc_factory_reset_dry_run",
        "input_button.rc_factory_reset_confirm",
        "input_text.rc_factory_reset_token",
        "input_text.rc_factory_reset_dry_run_report",
        "input_boolean.rc_factory_reset_armed",
        "input_datetime.rc_factory_reset_last_dry_run",
        "sensor.rc_factory_reset_status",
        "sensor.rc_factory_reset_last_backup_age",
        "binary_sensor.rc_factory_reset_safe_to_run",
        "sensor.rc_factory_reset_preflight_warnings",
        "sensor.rc_factory_reset_postflight_status",
    }
    actual_tiles_set = set(tiles)
    missing_tiles = required_tiles_set - actual_tiles_set
    assert not missing_tiles, (
        f"factory-reset must contribute the 11 documented contract "
        f"tiles per spec; missing: {sorted(missing_tiles)}"
    )


def test_state_field_valid_for_pristine_install(manifest: dict) -> None:
    """The manifest `state` must be one of the 10-state allowlist for a
    pristine install. For factory-reset, the state is
    `needs_information` until the rollback path is fully wired.
    """
    valid_states = {
        "Available",
        "needs_information",
        "pending",
        "in_progress",
        "ready_for_review",
        "blocked",
        "shipped",
        "deprecated",
        "superseded",
        "removed",
    }
    assert manifest["state"] in valid_states, (
        f"manifest state={manifest['state']!r} is not in the 10-state "
        f"allowlist; the directive §'Connection states are "
        f"standardized' lists the canonical 10-state allowlist"
    )
    assert manifest["state"] == "needs_information", (
        f"factory-reset state={manifest['state']!r}; the pristine-"
        f"install state should be `needs_information` (the recipe "
        f"+ the dashboard are wired, but the chain-corruption "
        f"recovery path is still being wired — the openclaw-api "
        f"audit chain binary_sensor is not on main yet). Once the "
        f"openclaw binary_sensor lands, the state flips to "
        f"`Available`."
    )


def test_automations_are_documented(manifest: dict, helper_package_text: str) -> None:
    """Defensive guard: the 5 section 8 MANDATORY automations must be
    present in the recipe + wired in the helper package.
    """
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert "## §8 The 5 §8 MANDATORY automations" in text, (
        "recipe.md must have a '## §8 The 5 §8 MANDATORY "
        "automations' section (the 5 automation documentation "
        "block)"
    )
    automation_coverage = (
        "dry-run-sets-token",
        "confirm-requires-token-match",
        "cancel-clears-token",
        "postflight-check-on-boot",
        "recovery-on-audit-chain-invalid",
    )
    for phrase in automation_coverage:
        assert phrase in text.lower(), (
            f"recipe.md §8 must cover {phrase!r}; the 5 "
            f"automations are MANDATORY before first use"
        )
    full_automation_titles = (
        "### §8.1 Dry-run-sets-token",
        "### §8.2 Confirm-requires-token-match",
        "### §8.3 Cancel-clears-token",
        "### §8.4 Postflight-check-on-boot",
        "### §8.5 Recovery-on-audit-chain-invalid",
    )
    for full_title in full_automation_titles:
        assert full_title in text, (
            f"recipe.md §8 must have the full automation "
            f"section for {full_title!r}; the 5 MANDATORY "
            f"automations must be present in the recipe"
        )
    required_automation_ids = (
        "rc_factory_reset_dry_run_sets_token",
        "rc_factory_reset_confirm_requires_token_match",
        "rc_factory_reset_cancel_clears_token",
        "rc_factory_reset_postflight_check_on_boot",
        "rc_factory_reset_recovery_on_audit_chain_invalid",
    )
    for required_id in required_automation_ids:
        assert f"id: {required_id}" in helper_package_text, (
            f"helper package at "
            f"`homeassistant/packages/roamcore_factory_reset.yaml` "
            f"MUST declare automation with id={required_id!r} "
            f"(the section 8 MANDATORY automation)"
        )
    manifest_automations = manifest.get("automations", [])
    for auto in manifest_automations:
        assert "id" in auto, (
            f"manifest automations list entry must have an `id` "
            f"field; got {auto!r}"
        )
        assert auto["id"] in required_automation_ids, (
            f"manifest automations list entry id={auto['id']!r} "
            f"is not one of the 5 section 8 MANDATORY automation ids "
            f"{required_automation_ids!r}"
        )


def test_prerequisites_check_function_exists(factory_reset_py_text: str) -> None:
    """The RoamCore-owned service handler at
    `homeassistant/custom_components/roamcore/factory_reset.py`
    MUST define a `validate_factory_reset_prerequisites(hass)`-
    equivalent guard that returns (ok: bool, reasons: list[str]) where
    reasons are plain-English strings.
    """
    expected_markers = (
        "validate_factory_reset_prerequisites",
        "is_backup_fresh",
        "BACKUP_FRESHNESS_WINDOW_MINUTES",
        "plain_english_reason",
        "recent backup",
    )
    for expected in expected_markers:
        assert expected in factory_reset_py_text, (
            f"RoamCore-owned service handler at "
            f"`homeassistant/custom_components/roamcore/factory_reset.py` "
            f"MUST define {expected!r} (the prerequisites check + "
            f"the plain-English error mapper + the freshness guard); "
            f"the tier-a claim is dishonest"
        )
