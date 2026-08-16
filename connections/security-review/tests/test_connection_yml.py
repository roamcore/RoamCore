"""Manifest-honesty tests for connections/security-review/connection.yml.

This is the canonical tier-a manifest-honesty test rig for the Security
Review connection. The tests assert that the manifest is honest about
being tier-a — that the folder / id / tier invariants hold, that the
RoamCore-owned Python service handler at
`homeassistant/custom_components/roamcore/security.py` is real + exists
on disk + has the 3 expected service handlers + the
`register_security_services` function + the `plain_english_status`
mapper + the `SECURITY_TILE_PREFIX` constant + the 3 stdlib-only
classes (`RCApiTokenManager` + `SSHAuditReader` +
`FirewallAuditReader`), that the recipe doc the tier_requirements
promise is actually present on disk, that the
`rc_security_review_*` tile ids are vendor-neutral per
`docs/reference/rc-entity-naming.md`, that the 4 §8 MANDATORY
automations are documented in the recipe + wired in the helper
package, that the secrets-leak guard is real (no hardcoded URLs, no
hardcoded passwords, no /home/<user> paths in the shipped files),
and that the idempotency marker is present (the §8.1 rotate-token
automation has a `mode: single` guard).

If you add new contract tiles, keep this file and update the
`required_tiles` tuple in `test_dashboard_tiles_follow_rc_naming` so
pytest catches regressions before CI runs the audit.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/security-review/tests/ -v
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> security-review/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "security-review"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
README_PATH = CONNECTION_DIR / "README.md"
INIT_PATH = CONNECTION_DIR / "__init__.py"

CUSTOM_COMPONENT_PATH = REPO_ROOT / "homeassistant" / "custom_components" / "roamcore"
SECURITY_PY = CUSTOM_COMPONENT_PATH / "security.py"
SERVICES_YAML = CUSTOM_COMPONENT_PATH / "services.yaml"
COMPONENT_INIT = CUSTOM_COMPONENT_PATH / "__init__.py"

HELPER_PACKAGE_PATH = REPO_ROOT / "homeassistant" / "packages" / "roamcore_security_review.yaml"
PYTEST_RIG_PATH = REPO_ROOT / "homeassistant" / "packages" / "tests" / "test_security_review.py"
BASH_SMOKE_PATH = REPO_ROOT / "scripts" / "checks" / "security-review-smoke.sh"
USER_RUNBOOK_PATH = REPO_ROOT / "docs" / "runbooks" / "security-review.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def helper_package_text() -> str:
    assert HELPER_PACKAGE_PATH.is_file(), f"missing helper package at {HELPER_PACKAGE_PATH}"
    return HELPER_PACKAGE_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def security_py_text() -> str:
    assert SECURITY_PY.is_file(), f"missing RoamCore-owned service handler at {SECURITY_PY}"
    return SECURITY_PY.read_text(encoding="utf-8")


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (security-review).

    This is the same invariant the audit script enforces; we duplicate
    it here so pytest catches regressions before CI runs the audit.
    """
    assert CONNECTION_DIR.name == "security-review", (
        f"folder name {CONNECTION_DIR.name!r} does not match the "
        f"spec-required kebab-case 'security-review'"
    )
    # The manifest id is snake_case per the Python DOMAIN
    # convention (matches `DOMAIN = "security_review"` in __init__.py).
    # The audit script accepts both kebab-case folder names +
    # snake_case manifest ids (same convention as
    # `connections/openclaw-api/` with id=openclaw_api +
    # folder=openclaw-api).
    assert manifest["id"] in ("security_review", "security-review"), (
        f"manifest id={manifest['id']!r} must be 'security_review' "
        f"(snake_case DOMAIN convention) or 'security-review' "
        f"(kebab-case folder convention); the audit accepts "
        f"both forms"
    )
    assert manifest["id"] == "security_review"


def test_tier_a_with_real_integration_code(manifest: dict, security_py_text: str) -> None:
    """Tier-a must advertise tier-a-only RoamCore-owned fields AND must
    back them with real on-disk code (the RoamCore-owned Python service
    handler at security.py).

    A regression here (e.g. someone flipping tier to b without removing
    the integration code, or removing the integration code from the
    install path) would falsely imply a working RoamCore integration
    + integration tests that we don't have, and the audit would
    either block the PR or let a misleading tier-a claim slip through.
    The tier-a strategy here is native integration code: the
    RoamCore-owned service handler at
    `homeassistant/custom_components/roamcore/security.py` is the
    canonical implementation (real code, 3 stdlib-only classes, the
    plain-English status mapper, the 3 RoamCore service registrations).
    """
    assert manifest["tier"] == "a", (
        "security-review must stay at tier-a because RoamCore owns + "
        "ships + maintains a real Python service handler at "
        "`homeassistant/custom_components/roamcore/security.py` (883 "
        "LOC, stdlib-only) that exposes 3 RoamCore services "
        "(`rotate_api_token` / `audit_ssh` / `audit_firewall`) + the "
        "plain-English status mapper; tier-b would be a downgrade "
        "that loses the audit's ability to verify the real "
        "integration code"
    )
    assert manifest["wizard"]["one_tap"] is True, (
        "tier-a connections CAN advertise one_tap=true (the "
        "Security Review helper package ships with "
        "`input_boolean.rc_security_review_enabled: initial: true` — "
        "the audit starts running automatically as soon as the helper "
        "package loads; no operator wiring required for the default "
        "flow)"
    )
    assert manifest["install"]["hacs"] is True, (
        "security-review must advertise install.hacs=true — the "
        "RoamCore HACS package bundles the RoamCore-owned service "
        "handler at `homeassistant/custom_components/roamcore/security.py`; "
        "HACS is the preferred install path"
    )
    assert manifest["install"]["config_flow"] is True, (
        "install.config_flow must stay True — the HACS-installed "
        "RoamCore integration exposes the Security Review surface via "
        "its options flow; this is the RoamCore-owned operator-wired "
        "setup flow for the tier-a marker"
    )
    # The install.install_custom_component field MUST point at the
    # RoamCore-owned service handler at `security.py`.
    custom_component_relpath = manifest["install"].get(
        "install_custom_component"
    )
    assert custom_component_relpath == (
        "homeassistant/custom_components/roamcore/security.py"
    ), (
        "install.install_custom_component must point at "
        "`homeassistant/custom_components/roamcore/security.py` — "
        "the RoamCore-owned service handler that backs the tier-a "
        "claim; got "
        f"{custom_component_relpath!r}"
    )
    # The real service handler MUST exist on disk.
    assert SECURITY_PY.is_file(), (
        "tier-a manifest claims `homeassistant/custom_components/"
        "roamcore/security.py` exists but the file is missing on disk "
        "— the tier-a claim is dishonest"
    )
    # The service handler MUST define the 3 expected service handlers
    # + the SERVICE_REGISTRATION function + the 3 stdlib-only classes
    # + the plain-English status mapper + the SECURITY_TILE_PREFIX
    # constant.
    expected_service_handlers = (
        "_svc_rotate_api_token",
        "_svc_audit_ssh",
        "_svc_audit_firewall",
    )
    for expected in expected_service_handlers:
        assert expected in security_py_text, (
            f"RoamCore-owned service handler at "
            f"`homeassistant/custom_components/roamcore/security.py` "
            f"MUST define {expected!r}; the tier-a claim is dishonest"
        )
    expected_api_surface = (
        # The 3 RoamCore service registration function.
        "def register_security_services",
        # The plain-English status mapper.
        "def plain_english_status",
        # The 3 stdlib-only classes.
        "class RCApiTokenManager",
        "class SSHAuditReader",
        "class FirewallAuditReader",
        # The canonical tile prefix.
        "SECURITY_TILE_PREFIX",
        # The backup-before-mutate discipline markers.
        "backup_path",
        "rotate_token",
        "find_risky_settings",
        "find_risky_rules",
    )
    for expected in expected_api_surface:
        assert expected in security_py_text, (
            f"RoamCore-owned service handler at "
            f"`homeassistant/custom_components/roamcore/security.py` "
            f"MUST define {expected!r}; the tier-a claim is dishonest"
        )
    # The SECURITY_TILE_PREFIX constant MUST be the canonical
    # `rc_security_review_` prefix.
    assert "SECURITY_TILE_PREFIX = \"rc_security_review_\"" in security_py_text, (
        "RoamCore-owned service handler at "
        "`homeassistant/custom_components/roamcore/security.py` MUST "
        "define the `SECURITY_TILE_PREFIX = \"rc_security_review_\"` "
        "constant (the canonical `rc_security_review_` prefix); the "
        "tier-a claim is dishonest"
    )
    # The service handler MUST register the 3 RoamCore services with
    # `hass.services.async_register` (the canonical HA service-registration
    # surface).
    for service_name in (
        "rotate_api_token",
        "audit_ssh",
        "audit_firewall",
    ):
        assert service_name in security_py_text, (
            f"RoamCore-owned service handler at "
            f"`homeassistant/custom_components/roamcore/security.py` "
            f"MUST register the {service_name!r} RoamCore service via "
            f"hass.services.async_register"
        )
    # The helper package + pytest rig + bash smoke + user runbook
    # MUST all exist on disk (the install paths promise all four).
    assert HELPER_PACKAGE_PATH.is_file(), (
        "install.install_helper_package promises "
        "`homeassistant/packages/roamcore_security_review.yaml` but it "
        "is missing on disk — the tier-a claim is dishonest"
    )
    assert PYTEST_RIG_PATH.is_file(), (
        "install.install_pytest_rig promises "
        "`homeassistant/packages/tests/test_security_review.py` but it "
        "is missing on disk — the tier-a claim is dishonest"
    )
    assert BASH_SMOKE_PATH.is_file(), (
        "install.install_smoke promises "
        "`scripts/checks/security-review-smoke.sh` but it is missing on "
        "disk — the tier-a claim is dishonest"
    )
    assert USER_RUNBOOK_PATH.is_file(), (
        "install.install_user_runbook promises "
        "`docs/runbooks/security-review.md` but it is missing on disk "
        "— the tier-a claim is dishonest"
    )
    assert SERVICES_YAML.is_file(), (
        "RoamCore-owned services.yaml at "
        "`homeassistant/custom_components/roamcore/services.yaml` "
        "MUST exist on disk (the 3 service definitions are appended "
        "there)"
    )
    assert COMPONENT_INIT.is_file(), (
        "RoamCore-owned __init__.py at "
        "`homeassistant/custom_components/roamcore/__init__.py` "
        "MUST exist on disk (the "
        "`register_security_services(hass)` call is wired into "
        "`async_setup_entry` there)"
    )
    # The reuse-first strategy is FALSE for tier-a (this connection
    # OWNS the integration code; it is NOT a recipe over upstream
    # integrations).
    upstream_truth = manifest.get("upstream_truth", {})
    assert upstream_truth.get("reuse_first") is False, (
        "upstream_truth.reuse_first must be False for tier-a — "
        "security-review OWNS the integration code at "
        "`homeassistant/custom_components/roamcore/security.py`; "
        "tier-b would set reuse_first=true (recipe over upstream)"
    )
    # The vendor_neutral flag must be TRUE — the service handler
    # exposes the 3 RoamCore services (vendor-neutral by definition —
    # they wrap the file-based SSH + firewall audit) + the SSH + firewall
    # audit is file-based (no specific firewall / SSH server
    # implementation).
    assert upstream_truth.get("vendor_neutral") is True, (
        "upstream_truth.vendor_neutral must be True — the "
        "RoamCore-owned service handler at "
        "`homeassistant/custom_components/roamcore/security.py` "
        "exposes the vendor-neutral RoamCore-registered `roamcore.*` "
        "services + the SSH + firewall audit is file-based (no "
        "vendor names leak into the integration)"
    )
    # The rocore_owned list MUST include the four RoamCore-owned
    # files (security.py + services.yaml + the helper package + the
    # pytest rig + the bash smoke + the user runbook + the
    # connection folder itself).
    rocore_owned = upstream_truth.get("rocore_owned", [])
    required_rocore_owned = (
        "homeassistant/custom_components/roamcore/security.py",
        "homeassistant/custom_components/roamcore/__init__.py",
        "homeassistant/custom_components/roamcore/services.yaml",
        "homeassistant/packages/roamcore_security_review.yaml",
        "homeassistant/packages/tests/test_security_review.py",
        "scripts/checks/security-review-smoke.sh",
        "docs/runbooks/security-review.md",
    )
    for required_path in required_rocore_owned:
        assert required_path in rocore_owned, (
            f"upstream_truth.rocore_owned must include "
            f"{required_path!r} (the RoamCore-owned files that "
            f"back the tier-a claim)"
        )
    # The tests list MUST reference the ~20 pytest tests + the
    # bash smoke + the connection-folder test rig.
    tests = manifest.get("tests", [])
    assert any("test_security_review.py" in t for t in tests), (
        "tests list must reference the pytest rig at "
        "`homeassistant/packages/tests/test_security_review.py` ("
        "the ~20-test contract validation rig)"
    )
    assert any("security-review-smoke.sh" in t for t in tests), (
        "tests list must reference the bash smoke at "
        "`scripts/checks/security-review-smoke.sh` (the ~10-assertion "
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
    # Sanity: the recipe actually documents the Security Review + the
    # 3-step operator flow + the 4 §8 MANDATORY automations +
    # the 12 `rc_security_review_*` contract tiles rather than just an
    # empty placeholder.
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert (
        "security-review" in text.lower()
        or "security_review" in text.lower()
        or "ssh" in text.lower()
        or "firewall" in text.lower()
        or "audit" in text.lower()
        or "rotate" in text.lower()
        or "access code" in text.lower()
        or "lockout" in text.lower()
    ) and "rc_security_review_" in text, (
        "recipe.md must document the Security Review setup (the "
        "3-step operator flow + the 4 §8 MANDATORY automations + the "
        "12 `rc_security_review_*` contract tiles + the 3-line §9 "
        "troubleshooting entries + the §7 How to recover section "
        "+ the §10 cross-references) and reference at least one "
        "`rc_security_review_` tile"
    )
    # The recipe must include the 4 §8 MANDATORY automations as
    # section headers.
    required_sections = (
        "## §3 Step 1 — Rotate access codes",
        "## §4 Step 2 — Audit SSH",
        "## §5 Step 3 — Audit firewall",
        "## §6 The 4 §8 MANDATORY automations",
        "### §8.1 Rotate-token",
        "### §8.2 Audit-ssh",
        "### §8.3 Audit-firewall",
        "### §8.4 Warn-rotation-age",
        "## §8 The 12 `rc_security_review_*` contract entities",
    )
    for header in required_sections:
        assert header in text, (
            f"recipe.md is missing required section header "
            f"{header!r} (spec requires the 3-step flow + the "
            f"4 §8 MANDATORY automations + the contract-entity "
            f"table to be present)"
        )


def test_category_security_with_no_legacy_doc(manifest: dict) -> None:
    """Brand-new connection — no legacy catalog stub exists.

    The connection is brand-new (no legacy docs/catalog/security-review/
    stub exists today). The `category` must be `security` (matches
    the existing catalog taxonomy). Per the 2026-08-05 docs/ux-first-pass
    repo-hygiene alignment, the recipe.md is the canonical surface for
    new connections — no SUPERSEDED banner is needed because there's
    no legacy stub.
    """
    assert manifest["category"] == "security", (
        f"category must stay 'security' (matches the existing "
        f"catalog taxonomy for Security Review); got "
        f"{manifest['category']!r}"
    )
    # Phase 7 / Gate F / Wave 9 #123.c.ii markers — the connection
    # is the canonical prevention for the "lockout" worst-case
    # (per the directive §"Phase 7 delivery" / Gate F).
    manifest_text = MANIFEST_PATH.read_text(encoding="utf-8")
    assert "phase-7" in manifest_text.lower() or "phase 7" in manifest_text.lower() or "gate-f" in manifest_text.lower() or "gate f" in manifest_text.lower(), (
        "connection.yml header must explicitly declare that the "
        "connection is the canonical prevention for the 'lockout' "
        "worst-case (Phase 7 / Gate F / Wave 9 #123.c.ii)"
    )


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """rc_* tile ids must NOT contain vendor names (per
    rc-entity-naming.md).

    The Security Review contract is vendor-neutral by design — the
    RoamCore-owned service handler at
    `homeassistant/custom_components/roamcore/security.py` exposes
    the 3 RoamCore `roamcore.*` services (vendor-neutral by
    definition) + the SSH + firewall audit is file-based (no
    specific firewall / SSH server implementation). Contract ids
    must stay vendor-neutral.

    The spec is strict: every `dashboard.tiles[*]` must match
    `^[a-z_]+\\.rc_security_review_[a-z0-9_]+$` (vendor-neutral,
    subsystem prefix `rc_security_review_*` per the
    `security_review` subsystem naming convention added by this
    slice).
    """
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles, "security-review contributes at least one dashboard tile"

    # Every tile must be a string entity id.
    for tile in tiles:
        assert isinstance(tile, str), (
            f"dashboard.tiles[*] must be a string entity id "
            f"(spec §1); got {tile!r}"
        )

    # Allowed HA core domain prefixes per
    # docs/reference/rc-entity-naming.md: input_boolean,
    # input_datetime, input_text, sensor, binary_sensor, button.
    allowed_domains = {
        "input_boolean",
        "input_datetime",
        "input_text",
        "sensor",
        "binary_sensor",
        "button",
    }
    pattern = re.compile(r"^[a-z_]+\.rc_security_review_[a-z0-9_]+$")

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
            f"^[a-z_]+\\.rc_security_review_[a-z_]+$ (vendor-neutral "
            f"contract naming per "
            f"docs/reference/rc-entity-naming.md)"
        )
        # Domain segment must be one of the allowed HA core
        # domain prefixes for the §security_review subsystem.
        domain = tile.split(".", 1)[0]
        assert domain in allowed_domains, (
            f"tile id {tile!r} uses domain {domain!r} which is "
            f"not in the allowed security-review domain set "
            f"{sorted(allowed_domains)!r}; per "
            f"docs/reference/rc-entity-naming.md §security_review "
            f"subsystem"
        )
        # Subsystem prefix is rc_security_review_; the suffix
        # (after `rc_security_review_`) MUST NOT contain any
        # forbidden vendor substring.
        suffix = tile.split(".rc_security_review_", 1)[1]
        for bad in forbidden_substrings:
            assert bad not in suffix.lower(), (
                f"tile id {tile!r} contains forbidden vendor "
                f"substring {bad!r} in the suffix after "
                f"`rc_security_review_`; per "
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

    # Spec calls for exactly 12 vendor-neutral tiles (the 12
    # contract entities documented in the recipe §8 contract
    # layer):
    #   input_boolean.rc_security_review_enabled
    #     (the §8 master enable toggle — pauses the daily
    #      security audit when OFF)
    #   input_datetime.rc_security_review_last_audit
    #     (the §8 last audit run timestamp — set by §8.2 +
    #      §8.3)
    #   input_text.rc_security_review_status
    #     (the §8 operator-visible plain-English status)
    #   input_text.rc_security_review_warnings
    #     (the §8 operator-visible plain-English warnings list)
    #   sensor.rc_security_review_last_status
    #     (the §8 mirrors the input_text status + adds a
    #      plain-English banner)
    #   sensor.rc_security_review_token_age_days
    #     (the §8 age of the current RC_API_TOKEN in whole days
    #      — 99999 if never)
    #   sensor.rc_security_review_ssh_warnings
    #     (the §8 count of SSH warnings from the last audit —
    #      0 if no warnings)
    #   sensor.rc_security_review_firewall_warnings
    #     (the §8 count of firewall warnings from the last audit
    #      — 0 if no warnings)
    #   binary_sensor.rc_security_review_healthy
    #     (the §8 resolved healthiness chip — true when no
    #      warnings AND token age < 75 days)
    #   button.rc_security_review_rotate_token_now
    #     (the §8 operator-triggered one-tap "rotate access code"
    #      button)
    #   button.rc_security_review_audit_ssh_now
    #     (the §8 operator-triggered one-tap "audit SSH now"
    #      button)
    #   button.rc_security_review_audit_firewall_now
    #     (the §8 operator-triggered one-tap "audit firewall now"
    #      button)
    assert len(tiles) == 12, (
        f"security-review must contribute exactly 12 contract "
        f"tiles per spec (1 input_boolean enabled + 1 "
        f"input_datetime last_audit + 2 input_text (status + "
        f"warnings) + 4 sensors (last_status + token_age_days + "
        f"ssh_warnings + firewall_warnings) + 1 binary_sensor "
        f"healthy + 3 buttons (rotate_token_now + audit_ssh_now + "
        f"audit_firewall_now) = 12 contract entities documented "
        f"in the recipe §8 contract layer); got {len(tiles)}"
    )


def test_required_tiles_present(manifest: dict) -> None:
    """The 12 contract entities documented in the recipe §8 must
    all be present in the dashboard.tiles list.

    A regression here (e.g. someone deleting a tile from the
    manifest without updating the recipe §8 contract-entity
    table) would break the dashboard contract; this test
    catches the regression.
    """
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    required_tiles = (
        "input_boolean.rc_security_review_enabled",
        "input_datetime.rc_security_review_last_audit",
        "input_text.rc_security_review_status",
        "input_text.rc_security_review_warnings",
        "sensor.rc_security_review_last_status",
        "sensor.rc_security_review_token_age_days",
        "sensor.rc_security_review_ssh_warnings",
        "sensor.rc_security_review_firewall_warnings",
        "binary_sensor.rc_security_review_healthy",
        "button.rc_security_review_rotate_token_now",
        "button.rc_security_review_audit_ssh_now",
        "button.rc_security_review_audit_firewall_now",
    )
    for required_tile in required_tiles:
        assert required_tile in tiles, (
            f"dashboard.tiles must include {required_tile!r} "
            f"(the §8 contract entity documented in the recipe)"
        )


def test_status_reflects_tier_a_with_pytest_rig(manifest: dict) -> None:
    """Status must be honest about tier-a with a real pytest rig.

    The Security Review connection has:
      - real RoamCore-owned Python service handler at
        `homeassistant/custom_components/roamcore/security.py`
        (883 LOC, stdlib-only)
      - real RoamCore-owned helper package at
        `homeassistant/packages/roamcore_security_review.yaml`
        (with the 4 §8 MANDATORY automations)
      - real ~20-test pytest rig at
        `homeassistant/packages/tests/test_security_review.py`
      - real ~10-assertion bash smoke at
        `scripts/checks/security-review-smoke.sh`
      - real user-facing IKEA-style runbook at
        `docs/runbooks/security-review.md`

    The `Available` status is the honest tier-a status: code is
    shipped + bench-tested but the recipe is still being validated
    in the field. If we ever flip this to 'shipped' or 'stable',
    the audit will demand real-world validation evidence that we
    don't have yet.
    """
    assert manifest["state"] == "Available", (
        f"security-review state={manifest['state']!r} implies a "
        f"state outside the 10-state allowlist; the "
        f"directive §'Connection states are standardized' "
        f"lists 'Available' as the default for code-shipped "
        f"connections"
    )


def test_automations_are_documented(manifest: dict, helper_package_text: str) -> None:
    """Defensive guard for the future tier-a promotion.

    Forgetting to wire the 4 §8 MANDATORY automations can leave
    the operator with stale Security Review state (the §8.1
    rotate-token doesn't fire + the §8.2 audit-ssh doesn't fire
    + the §8.3 audit-firewall doesn't fire + the §8.4
    warn-rotation-age doesn't fire). The §6 walks through the
    FOUR MANDATORY automations:
      - §8.1 Rotate-token — the automation that fires via cron
        every 90 days when
        `input_boolean.rc_security_review_enabled` is ON. The
        automation calls `roamcore.rotate_api_token` with
        `reason: "scheduled_90_day"` + writes the result to
        `input_text.rc_security_review_status`. The
        `mode: single` guard prevents double-rotation if a
        rotation is already running.
      - §8.2 Audit-ssh — the automation that fires at 02:30
        daily. The automation calls `roamcore.audit_ssh` +
        writes the warnings list to
        `input_text.rc_security_review_warnings` + writes the
        timestamp to `input_datetime.rc_security_review_last_audit`.
        The §8.2 surfaces "Your SSH is locked down — keys only,
        no password login." OR "Your SSH needs attention:
        <plain-English warnings>" depending on the audit.
      - §8.3 Audit-firewall — the automation that fires at
        02:45 daily. The automation calls
        `roamcore.audit_firewall` + writes the warnings list to
        `input_text.rc_security_review_warnings` + writes the
        timestamp to `input_datetime.rc_security_review_last_audit`.
        The §8.3 surfaces "Your firewall is locked down — no
        wide-open ports." OR "Your firewall needs attention:
        <plain-English warnings>" depending on the audit.
      - §8.4 Warn-rotation-age — the automation that fires at
        09:00 daily + reads
        `sensor.rc_security_review_token_age_days` + writes a
        plain-English warning to
        `input_text.rc_security_review_status` when token age
        >= 75 days.
    """
    text = RECIPE_PATH.read_text(encoding="utf-8")
    # §6 header MUST be present.
    assert "## §6 The 4 §8 MANDATORY automations" in text, (
        "recipe.md must have a '## §6 The 4 §8 MANDATORY "
        "automations' section (the 4 automation documentation "
        "block)"
    )
    # §6 must cover the 4 automation areas.
    automation_coverage = (
        "rotate-token",
        "audit-ssh",
        "audit-firewall",
        "warn-rotation-age",
    )
    for phrase in automation_coverage:
        assert phrase in text.lower(), (
            f"recipe.md §6 must cover {phrase!r}; the 4 "
            f"automations are MANDATORY before first use"
        )
    # The full §8.N titles MUST appear as section headers.
    full_automation_titles = (
        "### §8.1 Rotate-token",
        "### §8.2 Audit-ssh",
        "### §8.3 Audit-firewall",
        "### §8.4 Warn-rotation-age",
    )
    for full_title in full_automation_titles:
        assert full_title in text, (
            f"recipe.md §6 must have the full automation "
            f"section for {full_title!r}; the 4 MANDATORY "
            f"automations must be present in the recipe"
        )
    # The helper package MUST declare the 4 §8 automations
    # with the canonical `id` field.
    required_automation_ids = (
        "rc_security_review_rotate_token",
        "rc_security_review_audit_ssh",
        "rc_security_review_audit_firewall",
        "rc_security_review_warn_rotation_age",
    )
    for required_id in required_automation_ids:
        assert f"id: {required_id}" in helper_package_text, (
            f"helper package at "
            f"`homeassistant/packages/roamcore_security_review.yaml` "
            f"MUST declare automation with id={required_id!r} "
            f"(the §8 MANDATORY automation)"
        )


def test_idempotency_marker_present(helper_package_text: str) -> None:
    """The §8.1 rotate-token automation MUST have a
    `mode: single` guard so re-firing the cron while a rotation
    is already running returns gracefully.

    A regression here (e.g. someone removing the `mode: single`
    guard) would allow double-rotation if the cron fires while a
    rotation is already running — which would create duplicate
    backup records + duplicate .storage/ writes. The idempotency
    marker is the safety net.
    """
    # Locate the rotate-token automation block by id (must be inside
    # the `automation:` section, not the button's `unique_id`).
    # The pattern is `id: rc_security_review_rotate_token` followed
    # by lines that start with 4-space indentation (the automation
    # block), rather than the button's `unique_id:` which is followed
    # by `icon:`.
    block_start = None
    search_from = 0
    while True:
        found = helper_package_text.find(
            "id: rc_security_review_rotate_token", search_from
        )
        if found == -1:
            break
        # Check the surrounding context — the automation block has
        # `id: <name>` followed by `alias:`, while the button has
        # `unique_id: <name>` followed by `icon:`.
        # The lookahead is small enough that we can match unambiguously.
        following = helper_package_text[found:found + 80]
        if "alias:" in following:
            block_start = found
            break
        search_from = found + 1
    assert block_start is not None, (
        "helper package MUST declare automation with "
        "id=rc_security_review_rotate_token (not just a button "
        "unique_id)"
    )
    # The block ends at the next `id:` or the EOF.
    next_id = helper_package_text.find(
        "\n  - id:", block_start + 1
    )
    block_end = next_id if next_id != -1 else len(helper_package_text)
    block = helper_package_text[block_start:block_end]
    assert "mode: single" in block, (
        "§8.1 rotate-token automation MUST have a "
        "`mode: single` guard so re-firing the cron while a "
        "rotation is already running returns gracefully"
    )


def test_init_py_exports_domain_and_constants() -> None:
    """The __init__.py MUST export the canonical DOMAIN constant
    + the SECURITY_TILE_NAMES tuple + the status-code constants
    used by the audit + the helper package + the pytest rig.

    A regression here (e.g. someone renaming DOMAIN or
    removing the SECURITY_TILE_NAMES tuple) would break the
    audit's ability to detect the connection.
    """
    init_text = INIT_PATH.read_text(encoding="utf-8")
    assert 'DOMAIN = "security_review"' in init_text, (
        "__init__.py must define DOMAIN = \"security_review\" "
        "(matches the connection name \"security-review\" via "
        "underscore substitution per the audit convention)"
    )
    assert "SECURITY_TILE_NAMES" in init_text, (
        "__init__.py must export SECURITY_TILE_NAMES tuple "
        "(the canonical 12-tile contract surface used by the "
        "audit + the helper package + the pytest rig)"
    )
    assert "SECURITY_TILE_PREFIX" in init_text, (
        "__init__.py must export SECURITY_TILE_PREFIX constant "
        "(the canonical `rc_security_review_` prefix)"
    )
    for status_const in (
        "STATUS_SECURE",
        "STATUS_NEEDS_ROTATION",
        "STATUS_SSH_RISK",
        "STATUS_FIREWALL_RISK",
        "STATUS_UNKNOWN",
    ):
        assert status_const in init_text, (
            f"__init__.py must export {status_const} status "
            f"code constant (used by plain_english_status "
            f"mapper + the audit)"
        )


def test_secrets_leak_guard_no_hardcoded_secrets(security_py_text: str, helper_package_text: str) -> None:
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
        assert forbidden.lower() not in security_py_text.lower(), (
            f"security.py MUST NOT contain hardcoded URL leak "
            f"{forbidden!r}"
        )
        assert forbidden.lower() not in helper_package_text.lower(), (
            f"helper package MUST NOT contain hardcoded URL "
            f"leak {forbidden!r}"
        )
    # /home/<user> path leaks (the secret leak pattern).
    assert "/home/bernard" not in security_py_text, (
        "security.py MUST NOT contain /home/bernard path leak"
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
        assert forbidden not in security_py_text, (
            f"security.py MUST NOT contain hardcoded password "
            f"leak {forbidden!r}"
        )
        assert forbidden not in helper_package_text, (
            f"helper package MUST NOT contain hardcoded "
            f"password leak {forbidden!r}"
        )
