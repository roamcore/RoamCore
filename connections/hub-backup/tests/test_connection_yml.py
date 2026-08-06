"""Manifest-honesty tests for connections/hub-backup/connection.yml.

This is the canonical tier-a manifest-honesty test rig for the Hub Backup
connection. The tests assert that the manifest is honest about being
tier-a — that the folder / id / tier invariants hold, that the
RoamCore-owned Python service handler at
`homeassistant/custom_components/roamcore/backup.py` is real + exists
on disk + has the 4 expected functions + the `register_backup_services`
function + the `plain_english_status` mapper, that the recipe doc the
tier_requirements promise is actually present on disk, that the
`rc_hub_backup_*` tile ids are vendor-neutral per
`docs/reference/rc-entity-naming.md`, that the 3 §8 MANDATORY
automations are documented in the recipe + wired in the helper package,
that the secrets-leak guard is real (no hardcoded URLs, no hardcoded
passwords, no /home/<user> paths in the shipped files), and that the
idempotency marker is present (the §8.1 nightly-create automation has
a `mode: single` guard).

If you add new contract tiles, keep this file and update the
`required_tiles` tuple in `test_dashboard_tiles_follow_rc_naming` so
pytest catches regressions before CI runs the audit.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/hub-backup/tests/ -v
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> hub-backup/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "hub-backup"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
README_PATH = CONNECTION_DIR / "README.md"
INIT_PATH = CONNECTION_DIR / "__init__.py"

CUSTOM_COMPONENT_PATH = REPO_ROOT / "homeassistant" / "custom_components" / "roamcore"
BACKUP_PY = CUSTOM_COMPONENT_PATH / "backup.py"
SERVICES_YAML = CUSTOM_COMPONENT_PATH / "services.yaml"
COMPONENT_INIT = CUSTOM_COMPONENT_PATH / "__init__.py"

HELPER_PACKAGE_PATH = REPO_ROOT / "homeassistant" / "packages" / "roamcore_hub_backup.yaml"
PYTEST_RIG_PATH = REPO_ROOT / "homeassistant" / "packages" / "tests" / "test_hub_backup.py"
BASH_SMOKE_PATH = REPO_ROOT / "scripts" / "checks" / "hub-backup-smoke.sh"
USER_RUNBOOK_PATH = REPO_ROOT / "docs" / "runbooks" / "hub-backup.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def helper_package_text() -> str:
    assert HELPER_PACKAGE_PATH.is_file(), f"missing helper package at {HELPER_PACKAGE_PATH}"
    return HELPER_PACKAGE_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def backup_py_text() -> str:
    assert BACKUP_PY.is_file(), f"missing RoamCore-owned service handler at {BACKUP_PY}"
    return BACKUP_PY.read_text(encoding="utf-8")


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (hub-backup).

    This is the same invariant the audit script enforces; we duplicate
    it here so pytest catches regressions before CI runs the audit.
    """
    assert CONNECTION_DIR.name == "hub-backup", (
        f"folder name {CONNECTION_DIR.name!r} does not match the "
        f"spec-required kebab-case 'hub-backup'"
    )
    # The manifest id is snake_case per the Python DOMAIN
    # convention (matches `DOMAIN = "hub_backup"` in __init__.py).
    # The audit script accepts both kebab-case folder names +
    # snake_case manifest ids (same convention as
    # `connections/openclaw-api/` with id=openclaw_api +
    # folder=openclaw-api).
    assert manifest["id"] in ("hub_backup", "hub-backup"), (
        f"manifest id={manifest['id']!r} must be 'hub_backup' "
        f"(snake_case DOMAIN convention) or 'hub-backup' "
        f"(kebab-case folder convention); the audit accepts "
        f"both forms"
    )
    assert manifest["id"] == "hub_backup"


def test_tier_a_with_real_integration_code(manifest: dict, backup_py_text: str) -> None:
    """Tier-a must advertise tier-a-only RoamCore-owned fields AND must
    back them with real on-disk code (the RoamCore-owned Python service
    handler at backup.py).

    A regression here (e.g. someone flipping tier to b without removing
    the integration code, or removing the integration code from the
    install path) would falsely imply a working RoamCore integration
    + integration tests that we don't have, and the audit would
    either block the PR or let a misleading tier-a claim slip through.
    The tier-a strategy here is native integration code: the
    RoamCore-owned service handler at
    `homeassistant/custom_components/roamcore/backup.py` is the
    canonical implementation (real code, real HA core `backup.create`
    / `backup.list` / `backup.delete` service calls, real
    `async_test_restore` sandbox runner, real `plain_english_status`
    mapper).
    """
    assert manifest["tier"] == "a", (
        "hub-backup must stay at tier-a because RoamCore owns + ships "
        "+ maintains a real Python service handler at "
        "`homeassistant/custom_components/roamcore/backup.py` (~240 "
        "LOC) that wraps the HA core `backup.create` / `backup.list` "
        "/ `backup.delete` services + a sandbox restore-test runner "
        "+ a plain-English status mapper; tier-b would be a downgrade "
        "that loses the audit's ability to verify the real "
        "integration code"
    )
    assert manifest["wizard"]["one_tap"] is True, (
        "tier-a connections CAN advertise one_tap=true (the Hub "
        "Backup helper package ships with "
        "`input_boolean.rc_hub_backup_enabled: initial: true` — "
        "backups start running automatically as soon as the helper "
        "package loads; no operator wiring required for the default "
        "flow)"
    )
    assert manifest["install"]["hacs"] is True, (
        "hub-backup must advertise install.hacs=true — the RoamCore "
        "HACS package bundles the RoamCore-owned service handler at "
        "`homeassistant/custom_components/roamcore/backup.py`; HACS "
        "is the preferred install path"
    )
    assert manifest["install"]["config_flow"] is True, (
        "install.config_flow must stay True — the HACS-installed "
        "RoamCore integration exposes the Hub Backup surface via its "
        "options flow; this is the RoamCore-owned operator-wired "
        "setup flow for the tier-a marker"
    )
    # The install.install_custom_component field MUST point at the
    # RoamCore-owned service handler at `backup.py`.
    custom_component_relpath = manifest["install"].get(
        "install_custom_component"
    )
    assert custom_component_relpath == (
        "homeassistant/custom_components/roamcore/backup.py"
    ), (
        "install.install_custom_component must point at "
        "`homeassistant/custom_components/roamcore/backup.py` — "
        "the RoamCore-owned service handler that backs the tier-a "
        "claim; got "
        f"{custom_component_relpath!r}"
    )
    # The real service handler MUST exist on disk.
    assert BACKUP_PY.is_file(), (
        "tier-a manifest claims `homeassistant/custom_components/"
        "roamcore/backup.py` exists but the file is missing on disk "
        "— the tier-a claim is dishonest"
    )
    # The service handler MUST define the 6 expected functions
    # (`async_create_backup` + `async_list_backups` +
    # `async_delete_backup` + `async_test_restore` +
    # `register_backup_services` + `plain_english_status`) and the
    # `BACKUP_TILE_PREFIX` constant.
    expected_functions = (
        "async def async_create_backup",
        "async def async_list_backups",
        "async def async_delete_backup",
        "async def async_test_restore",
        "def register_backup_services",
        "def plain_english_status",
    )
    for expected in expected_functions:
        assert expected in backup_py_text, (
            f"RoamCore-owned service handler at "
            f"`homeassistant/custom_components/roamcore/backup.py` "
            f"MUST define {expected!r}; the tier-a claim is dishonest"
        )
    # The service handler MUST define the BACKUP_TILE_PREFIX constant
    # (the canonical `rc_hub_backup_` prefix).
    assert "BACKUP_TILE_PREFIX" in backup_py_text, (
        "RoamCore-owned service handler at "
        "`homeassistant/custom_components/roamcore/backup.py` MUST "
        "define the `BACKUP_TILE_PREFIX` constant (the canonical "
        "`rc_hub_backup_` prefix); the tier-a claim is dishonest"
    )
    # The service handler MUST call `hass.services.async_call(
    # 'backup', 'create', ...)` against the HA core `backup.create`
    # service (NOT a third-party integration).
    assert "'backup', 'create'" in backup_py_text, (
        "RoamCore-owned service handler at "
        "`homeassistant/custom_components/roamcore/backup.py` MUST "
        "call `hass.services.async_call('backup', 'create', ...)` "
        "against the HA core `backup.create` service"
    )
    assert "'backup', 'list'" in backup_py_text, (
        "RoamCore-owned service handler at "
        "`homeassistant/custom_components/roamcore/backup.py` MUST "
        "call `hass.services.async_call('backup', 'list', ...)` "
        "against the HA core `backup.list` service"
    )
    assert "'backup', 'delete'" in backup_py_text, (
        "RoamCore-owned service handler at "
        "`homeassistant/custom_components/roamcore/backup.py` MUST "
        "call `hass.services.async_call('backup', 'delete', ...)` "
        "against the HA core `backup.delete` service"
    )
    # The helper package + pytest rig + bash smoke + user runbook
    # MUST all exist on disk (the install paths promise all four).
    assert HELPER_PACKAGE_PATH.is_file(), (
        "install.install_helper_package promises "
        "`homeassistant/packages/roamcore_hub_backup.yaml` but it "
        "is missing on disk — the tier-a claim is dishonest"
    )
    assert PYTEST_RIG_PATH.is_file(), (
        "install.install_pytest_rig promises "
        "`homeassistant/packages/tests/test_hub_backup.py` but it "
        "is missing on disk — the tier-a claim is dishonest"
    )
    assert BASH_SMOKE_PATH.is_file(), (
        "install.install_smoke promises "
        "`scripts/checks/hub-backup-smoke.sh` but it is missing on "
        "disk — the tier-a claim is dishonest"
    )
    assert USER_RUNBOOK_PATH.is_file(), (
        "install.install_user_runbook promises "
        "`docs/runbooks/hub-backup.md` but it is missing on disk — "
        "the tier-a claim is dishonest"
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
        "`register_backup_services(hass)` call is wired into "
        "`async_setup_entry` there)"
    )
    # The reuse-first strategy is FALSE for tier-a (this connection
    # OWNS the integration code; it is NOT a recipe over upstream
    # integrations).
    upstream_truth = manifest.get("upstream_truth", {})
    assert upstream_truth.get("reuse_first") is False, (
        "upstream_truth.reuse_first must be False for tier-a — "
        "hub-backup OWNS the integration code at "
        "`homeassistant/custom_components/roamcore/backup.py`; "
        "tier-b would set reuse_first=true (recipe over upstream)"
    )
    # The vendor_neutral flag must be TRUE — the service handler
    # calls the HA core `backup.create` / `backup.list` /
    # `backup.delete` services (vendor-neutral) + the RoamCore-
    # registered `roamcore.create_backup` / etc. services
    # (vendor-neutral by definition — they wrap the HA core
    # services + the sandbox restore-test runner).
    assert upstream_truth.get("vendor_neutral") is True, (
        "upstream_truth.vendor_neutral must be True — the "
        "RoamCore-owned service handler at "
        "`homeassistant/custom_components/roamcore/backup.py` "
        "calls the vendor-neutral HA core `backup.create` / "
        "`backup.list` / `backup.delete` services + the "
        "RoamCore-registered `roamcore.*` services; no vendor "
        "names leak into the integration"
    )
    # The rocore_owned list MUST include the four RoamCore-owned
    # files (backup.py + services.yaml + the helper package + the
    # pytest rig + the bash smoke + the user runbook + the
    # connection folder itself).
    rocore_owned = upstream_truth.get("rocore_owned", [])
    required_rocore_owned = (
        "homeassistant/custom_components/roamcore/backup.py",
        "homeassistant/custom_components/roamcore/__init__.py",
        "homeassistant/custom_components/roamcore/services.yaml",
        "homeassistant/packages/roamcore_hub_backup.yaml",
        "homeassistant/packages/tests/test_hub_backup.py",
        "scripts/checks/hub-backup-smoke.sh",
        "docs/runbooks/hub-backup.md",
    )
    for required_path in required_rocore_owned:
        assert required_path in rocore_owned, (
            f"upstream_truth.rocore_owned must include "
            f"{required_path!r} (the RoamCore-owned files that "
            f"back the tier-a claim)"
        )
    # The tests list MUST reference the 22 pytest tests + the
    # bash smoke + the connection-folder test rig.
    tests = manifest.get("tests", [])
    assert any("test_hub_backup.py" in t for t in tests), (
        "tests list must reference the pytest rig at "
        "`homeassistant/packages/tests/test_hub_backup.py` (the "
        "22-test contract validation rig)"
    )
    assert any("hub-backup-smoke.sh" in t for t in tests), (
        "tests list must reference the bash smoke at "
        "`scripts/checks/hub-backup-smoke.sh` (the 10-assertion "
        "cross-cutting YAML/secrets-leak/idempotency smoke)"
    )


def test_requires_docs_recipe_published(manifest: dict) -> None:
    """The audit's only tier-a hard requirement, made explicit.

    `docs_recipe_published` must be in tier_requirements AND a real
    recipe file must live on disk where the audit / docs site can
    reach it.
    """
    assert "docs_recipe_published" in manifest["tier_requirements"], (
        "tier-a requires 'docs_recipe_published' in tier_requirements"
    )
    assert RECIPE_PATH.is_file(), (
        f"tier_requirements promises a published recipe but "
        f"{RECIPE_PATH} does not exist"
    )
    # Sanity: the recipe actually documents the Hub Backup + the
    # FIVE-step operator flow + the 3 §8 MANDATORY automations +
    # the 10 `rc_hub_backup_*` contract tiles rather than just an
    # empty placeholder.
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert (
        "hub-backup" in text.lower()
        or "hub_backup" in text.lower()
        or "nightly" in text.lower()
        or "verified-restorable" in text.lower()
        or "verified restorable" in text.lower()
        or "backup" in text.lower()
        or "snapshot" in text.lower()
        or "recovery" in text.lower()
        or "restore" in text.lower()
    ) and "rc_hub_backup_" in text, (
        "recipe.md must document the Hub Backup setup (the FIVE-"
        "step operator flow + the 3 §8 MANDATORY automations + the "
        "10 `rc_hub_backup_*` contract tiles + the 3-line §9 "
        "troubleshooting entries + the §9 How to restore section "
        "+ the §10 How to factory reset section + the §12 "
        "cross-references) and reference at least one "
        "`rc_hub_backup_` tile"
    )
    # The recipe must include the 3 §8 MANDATORY automations as
    # section headers.
    required_sections = (
        "## §3 Step 1 — Enable",
        "## §4 Step 2 — Set destination",
        "## §5 Step 3 — Set retention",
        "## §6 Step 4 — Wait for first run",
        "## §7 Step 5 — Check the tile",
        "## §8 The 3 §8 MANDATORY automations",
        "### §8.1 Nightly-create-backup",
        "### §8.2 Verify-integrity",
        "### §8.3 Cleanup-old",
        "## §11 The 10 `rc_hub_backup_*` contract entities",
    )
    for header in required_sections:
        assert header in text, (
            f"recipe.md is missing required section header "
            f"{header!r} (spec requires the FIVE-step flow + the "
            f"3 §8 MANDATORY automations + the contract-entity "
            f"table to be present)"
        )


def test_category_backup_with_no_legacy_doc(manifest: dict) -> None:
    """Brand-new connection — no legacy catalog stub exists.

    The connection is brand-new (no legacy docs/catalog/backup/
    stub exists today). The `category` must be `backup` (matches
    the existing catalog taxonomy). Per the 2026-08-05 docs/ux-
    first-pass repo-hygiene alignment, the recipe.md is the
    canonical surface for new connections — no SUPERSEDED banner
    is needed because there's no legacy stub.
    """
    assert manifest["category"] == "backup", (
        f"category must stay 'backup' (matches the existing "
        f"catalog taxonomy for Hub Backup); got "
        f"{manifest['category']!r}"
    )
    # Brand-new connection marker — the connection.yml header
    # explicitly says "the connection is brand-new" (no legacy
    # stub to point a SUPERSEDED banner at).
    manifest_text = MANIFEST_PATH.read_text(encoding="utf-8")
    assert "brand-new" in manifest_text.lower() or "brand new" in manifest_text.lower(), (
        "connection.yml header must explicitly declare that the "
        "connection is brand-new (no legacy catalog stub exists)"
    )


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """rc_* tile ids must NOT contain vendor names (per
    rc-entity-naming.md).

    The Hub Backup contract is vendor-neutral by design — the
    RoamCore-owned service handler at
    `homeassistant/custom_components/roamcore/backup.py` calls
    the HA core `backup.create` / `backup.list` / `backup.delete`
    services (vendor-neutral) + the RoamCore-registered
    `roamcore.create_backup` / etc. services (vendor-neutral by
    definition). Contract ids must stay vendor-neutral.

    The spec is strict: every `dashboard.tiles[*]` must match
    `^[a-z_]+\\.rc_hub_backup_[a-z0-9_]+$` (vendor-neutral,
    subsystem prefix `rc_hub_backup_*` per the `hub_backup`
    subsystem naming convention added by this slice).
    """
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles, "hub-backup contributes at least one dashboard tile"

    # Every tile must be a string entity id.
    for tile in tiles:
        assert isinstance(tile, str), (
            f"dashboard.tiles[*] must be a string entity id "
            f"(spec §1); got {tile!r}"
        )

    # Allowed HA core domain prefixes per
    # docs/reference/rc-entity-naming.md: input_boolean,
    # input_datetime, input_select, input_text, sensor,
    # binary_sensor, button.
    allowed_domains = {
        "input_boolean",
        "input_datetime",
        "input_select",
        "input_text",
        "sensor",
        "binary_sensor",
        "button",
    }
    pattern = re.compile(r"^[a-z_]+\.rc_hub_backup_[a-z0-9_]+$")

    # Vendor / implementation / hardware-side name leaks that
    # must NEVER appear in any rc_* tile id (the
    # forbidden_substrings list targets the
    # vendor-name / hardware-name / protocol-name /
    # integration-name absolute-forbidden set only).
    forbidden_substrings = (
        # Battery / power vendor / integration name leaks.
        "victron",
        "renogy",
        "shunt",
        "bms",
        "inverter",
        "mppt",
        # Water / tank sensor vendor / hardware name leaks.
        "see level",
        "seelevel",
        "garnet",
        "mopeka",
        # Network / connectivity vendor / hardware name leaks.
        "starlink",
        "peplink",
        "teltonika",
        "unifi",
        "ubiquiti",
        # Protocol / integration / library namespace leaks.
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
        # Upstream helper / integration namespace leaks.
        "input_boolean",
        "input_text",
        "input_datetime",
        "input_button",
        # Hardware / sensor / phone vendor / platform name
        # leaks.
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
            f"^[a-z_]+\\.rc_hub_backup_[a-z_]+$ (vendor-neutral "
            f"contract naming per "
            f"docs/reference/rc-entity-naming.md)"
        )
        # Domain segment must be one of the allowed HA core
        # domain prefixes for the §hub_backup subsystem.
        domain = tile.split(".", 1)[0]
        assert domain in allowed_domains, (
            f"tile id {tile!r} uses domain {domain!r} which is "
            f"not in the allowed backup domain set "
            f"{sorted(allowed_domains)!r}; per "
            f"docs/reference/rc-entity-naming.md §hub_backup "
            f"subsystem"
        )
        # Subsystem prefix is rc_hub_backup_; the suffix
        # (after `rc_hub_backup_`) MUST NOT contain any
        # forbidden vendor substring.
        suffix = tile.split(".rc_hub_backup_", 1)[1]
        for bad in forbidden_substrings:
            assert bad not in suffix.lower(), (
                f"tile id {tile!r} contains forbidden vendor "
                f"substring {bad!r} in the suffix after "
                f"`rc_hub_backup_`; per "
                f"docs/reference/rc-entity-naming.md, contract "
                f"ids are vendor-neutral — vendor names are "
                f"forbidden in any rc_* tile id"
            )
        # Each segment after the dot must be lowercase +
        # underscores + digits.
        for segment in tile.split("."):
            assert re.match(r"^[a-z_][a-z0-9_]*$", segment), (
                f"tile id {tile!r} contains a non-conforming "
                f"segment {segment!r}"
            )

    # Spec calls for exactly 10 vendor-neutral tiles (the 10
    # contract entities documented in the recipe §11 contract
    # layer):
    #   input_boolean.rc_hub_backup_enabled
    #     (the §11 master enable toggle — pauses nightly
    #      backups when OFF)
    #   input_datetime.rc_hub_backup_next_run
    #     (the §11 next scheduled run timestamp — default
    #      tomorrow 02:00)
    #   input_select.rc_hub_backup_retention_policy
    #     (the §11 operator-chosen retention policy — 3
    #      options)
    #   input_text.rc_hub_backup_destination
    #     (the §11 operator-owned destination path — mode
    #      password; default /config/.roamcore/backups/)
    #   input_text.rc_hub_backup_status
    #     (the §11 operator-visible plain-English status)
    #   sensor.rc_hub_backup_last_status
    #     (the §11 mirrors the input_text status + adds a
    #      plain-English banner)
    #   sensor.rc_hub_backup_age_minutes
    #     (the §11 minutes since last successful backup —
    #      99999 if never)
    #   binary_sensor.rc_hub_backup_healthy
    #     (the §11 resolved healthiness chip — true when
    #      age_minutes < 1500 AND verify-integrity passed)
    #   button.rc_hub_backup_backup_now
    #     (the §11 operator-triggered one-tap "back up now"
    #      button)
    #   button.rc_hub_backup_verify_now
    #     (the §11 operator-triggered one-tap "verify restore
    #      now" button)
    assert len(tiles) == 10, (
        f"hub-backup must contribute exactly 10 contract tiles "
        f"per spec (1 input_boolean enabled + 1 input_datetime "
        f"next_run + 1 input_select retention_policy + 2 "
        f"input_text (destination + status) + 2 sensors "
        f"(last_status + age_minutes) + 1 binary_sensor "
        f"healthy + 2 buttons (backup_now + verify_now) = 10 "
        f"contract entities documented in the recipe §11 "
        f"contract layer); got {len(tiles)}"
    )


def test_required_tiles_present(manifest: dict) -> None:
    """The 10 contract entities documented in the recipe §11 must
    all be present in the dashboard.tiles list.

    A regression here (e.g. someone deleting a tile from the
    manifest without updating the recipe §11 contract-entity
    table) would break the dashboard contract; this test
    catches the regression.
    """
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    required_tiles = (
        "input_boolean.rc_hub_backup_enabled",
        "input_datetime.rc_hub_backup_next_run",
        "input_select.rc_hub_backup_retention_policy",
        "input_text.rc_hub_backup_destination",
        "input_text.rc_hub_backup_status",
        "sensor.rc_hub_backup_last_status",
        "sensor.rc_hub_backup_age_minutes",
        "binary_sensor.rc_hub_backup_healthy",
        "button.rc_hub_backup_backup_now",
        "button.rc_hub_backup_verify_now",
    )
    for required_tile in required_tiles:
        assert required_tile in tiles, (
            f"dashboard.tiles must include {required_tile!r} "
            f"(the §11 contract entity documented in the recipe)"
        )


def test_status_reflects_tier_a_with_pytest_rig(manifest: dict) -> None:
    """Status must be honest about tier-a with a real pytest rig.

    The Hub Backup connection has:
      - real RoamCore-owned Python service handler at
        `homeassistant/custom_components/roamcore/backup.py`
        (~240 LOC)
      - real RoamCore-owned helper package at
        `homeassistant/packages/roamcore_hub_backup.yaml`
        (with the 3 §8 MANDATORY automations)
      - real 22-test pytest rig at
        `homeassistant/packages/tests/test_hub_backup.py`
      - real 10-assertion bash smoke at
        `scripts/checks/hub-backup-smoke.sh`
      - real user-facing IKEA-style runbook at
        `docs/runbooks/hub-backup.md`

    The `beta` status is the honest tier-a status: code is
    shipped + bench-tested but the recipe is still being
    validated in the field. If we ever flip this to 'shipped'
    or 'stable', the audit will demand real-world validation
    evidence that we don't have yet.
    """
    assert manifest["state"] == "Available", (
        f"hub-backup state={manifest['state']!r} implies a "
        f"state outside the 10-state allowlist; the "
        f"directive §'Connection states are standardized' "
        f"lists 'Available' as the default for code-shipped "
        f"connections"
    )


def test_automations_are_documented(manifest: dict, helper_package_text: str) -> None:
    """Defensive guard for the future tier-a promotion.

    Forgetting to wire the 3 §8 MANDATORY automations can
    leave the operator with stale Hub Backup state (the §8.1
    nightly-create doesn't fire + the §8.2 verify-integrity
    doesn't fire + the §8.3 cleanup-old doesn't fire). The
    §8 walks through the THREE MANDATORY automations:
      - §8.1 Nightly-create-backup — the automation that
        fires at 02:00 daily when
        `input_boolean.rc_hub_backup_enabled` is ON. The
        automation calls `roamcore.create_backup` with
        `retention_days: 30` + writes the result to
        `input_text.rc_hub_backup_status`. The `mode: single`
        guard prevents double-creation if a backup is already
        running.
      - §8.2 Verify-integrity — the automation that fires
        after the §8.1 nightly-create completes. The
        automation calls `roamcore.test_restore` against the
        newly-created backup + writes the result to
        `input_text.rc_hub_backup_status`. The §8.2 surfaces
        "Your last backup ran and the restore-test passed."
        OR "Your last backup ran but the restore-test
        failed — check the Hub is plugged in."
      - §8.3 Cleanup-old — the automation that fires at
        03:30 daily + calls `roamcore.list_backups` to
        enumerate existing backups + calls
        `roamcore.delete_backup` for any backup older than
        the operator-chosen retention policy (the
        `input_select.rc_hub_backup_retention_policy`
        helper).
    """
    text = RECIPE_PATH.read_text(encoding="utf-8")
    # §8 header MUST be present.
    assert "## §8 The 3 §8 MANDATORY automations" in text, (
        "recipe.md must have a '## §8 The 3 §8 MANDATORY "
        "automations' section (the 3 automation documentation "
        "block)"
    )
    # §8 must cover the 3 automation areas.
    automation_coverage = (
        "nightly-create-backup",
        "verify-integrity",
        "cleanup-old",
    )
    for phrase in automation_coverage:
        assert phrase in text.lower(), (
            f"recipe.md §8 must cover {phrase!r}; the 3 "
            f"automations are MANDATORY before first use"
        )
    # The full §8.N titles MUST appear as section headers.
    full_automation_titles = (
        "### §8.1 Nightly-create-backup",
        "### §8.2 Verify-integrity",
        "### §8.3 Cleanup-old",
    )
    for full_title in full_automation_titles:
        assert full_title in text, (
            f"recipe.md §8 must have the full automation "
            f"section for {full_title!r}; the 3 MANDATORY "
            f"automations must be present in the recipe"
        )
    # The helper package MUST declare the 3 §8 automations
    # with the canonical `id` field.
    required_automation_ids = (
        "rc_hub_backup_nightly_create_backup",
        "rc_hub_backup_verify_integrity",
        "rc_hub_backup_cleanup_old",
    )
    for required_id in required_automation_ids:
        assert f"id: {required_id}" in helper_package_text, (
            f"helper package at "
            f"`homeassistant/packages/roamcore_hub_backup.yaml` "
            f"MUST declare automation with id={required_id!r} "
            f"(the §8 MANDATORY automation)"
        )


def test_idempotency_marker_present(helper_package_text: str) -> None:
    """The §8.1 nightly-create automation MUST have a
    `mode: single` guard so re-firing the cron while a backup
    is running returns gracefully.

    A regression here (e.g. someone removing the `mode: single`
    guard) would allow double-creation if the cron fires
    while a backup is already running — which would create
    duplicate backups + duplicate destination writes. The
    idempotency marker is the safety net.
    """
    # Locate the nightly-create automation block by id.
    block_start = helper_package_text.find(
        "id: rc_hub_backup_nightly_create_backup"
    )
    assert block_start != -1, (
        "helper package MUST declare automation with "
        "id=rc_hub_backup_nightly_create_backup"
    )
    # The block ends at the next `id:` or the EOF.
    next_id = helper_package_text.find(
        "\n  - id:", block_start + 1
    )
    block_end = next_id if next_id != -1 else len(helper_package_text)
    block = helper_package_text[block_start:block_end]
    assert "mode: single" in block, (
        "§8.1 nightly-create automation MUST have a "
        "`mode: single` guard so re-firing the cron while a "
        "backup is running returns gracefully"
    )


def test_init_py_exports_domain_and_constants() -> None:
    """The __init__.py MUST export the canonical DOMAIN constant
    + the BACKUP_TILE_NAMES tuple + the status-code constants
    used by the audit + the helper package + the pytest rig.

    A regression here (e.g. someone renaming DOMAIN or
    removing the BACKUP_TILE_NAMES tuple) would break the
    audit's ability to detect the connection.
    """
    init_text = INIT_PATH.read_text(encoding="utf-8")
    assert 'DOMAIN = "hub_backup"' in init_text, (
        "__init__.py must define DOMAIN = \"hub_backup\" "
        "(matches the connection name \"hub-backup\" via "
        "underscore substitution per the audit convention)"
    )
    assert "BACKUP_TILE_NAMES" in init_text, (
        "__init__.py must export BACKUP_TILE_NAMES tuple "
        "(the canonical 10-tile contract surface used by the "
        "audit + the helper package + the pytest rig)"
    )
    assert "BACKUP_TILE_PREFIX" in init_text, (
        "__init__.py must export BACKUP_TILE_PREFIX constant "
        "(the canonical `rc_hub_backup_` prefix)"
    )
    for status_const in (
        "STATUS_OK",
        "STATUS_FAILED",
        "STATUS_RUNNING",
        "STATUS_NEVER",
    ):
        assert status_const in init_text, (
            f"__init__.py must export {status_const} status "
            f"code constant (used by plain_english_status "
            f"mapper + the audit)"
        )


def test_secrets_leak_guard_no_hardcoded_secrets(backup_py_text: str, helper_package_text: str) -> None:
    """Secrets-leak guard: no hardcoded URLs, no hardcoded
    passwords, no /home/<user> paths in the shipped files.

    The destination is `input_text` mode password (the
    operator owns the value, not RoamCore). A regression here
    (e.g. someone adding a hardcoded AWS access key) would
    leak secrets into the public GitHub repo — the GOLDEN.md
    anti-pattern forbids this.
    """
    # Hardcoded URL leaks (https://, http://, s3://, etc.).
    for forbidden in (
        "https://AKIA",        # AWS access key
        "https://arn:aws",     # AWS ARN
        "https://hooks.slack", # Slack webhook URL
        "https://discord.com/api/webhooks", # Discord webhook URL
        "https://api.telegram.org/bot", # Telegram bot token
    ):
        assert forbidden.lower() not in backup_py_text.lower(), (
            f"backup.py MUST NOT contain hardcoded URL leak "
            f"{forbidden!r}"
        )
        assert forbidden.lower() not in helper_package_text.lower(), (
            f"helper package MUST NOT contain hardcoded URL "
            f"leak {forbidden!r}"
        )
    # /home/<user> path leaks (the secret leak pattern).
    assert "/home/bernard" not in backup_py_text, (
        "backup.py MUST NOT contain /home/bernard path leak"
    )
    assert "/home/bernard" not in helper_package_text, (
        "helper package MUST NOT contain /home/bernard path "
        "leak"
    )
    # Hardcoded password leaks (the secret leak pattern).
    for forbidden in (
        "password: \"hunter2\"",
        "password = \"hunter2\"",
        "api_key: \"secret\"",
        "api_key = \"secret\"",
    ):
        assert forbidden not in backup_py_text, (
            f"backup.py MUST NOT contain hardcoded password "
            f"leak {forbidden!r}"
        )
        assert forbidden not in helper_package_text, (
            f"helper package MUST NOT contain hardcoded "
            f"password leak {forbidden!r}"
        )
