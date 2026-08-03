"""Manifest-honesty tests for connections/starlink/connection.yml.

This is the only test file we can ship for a tier-b recipe connection
that has no real Starlink terminal to integration-test against. The
tests here assert that the manifest is *honest about being tier-b* —
that the folder/id/tier invariants hold, that the recipe doc the
tier_requirements promise is actually present on disk, and that the
rc_net_starlink_* tile ids are vendor-neutral per
docs/reference/rc-entity-naming.md.

If you add real integration coverage (e.g. a config_flow.py + an
integration test against testcontainers/grpc-starlink-dish with a
synthetic dish-status.json fixture), keep this file and add the new
one alongside it; the audit will then list both under `tests:` in the
manifest.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/starlink/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> starlink/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "starlink"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (starlink).

    This is the same invariant the audit script enforces; we duplicate
    it here so pytest catches regressions before CI runs the audit.
    """
    assert manifest["id"] == CONNECTION_DIR.name, (
        f"manifest id={manifest['id']!r} does not match folder name "
        f"{CONNECTION_DIR.name!r}"
    )
    assert manifest["id"] == "starlink"


def test_tier_b_without_tier_a_markers(manifest: dict) -> None:
    """Tier-b must NOT advertise tier-a-only fields.

    A regression here (e.g. someone flipping one_tap to true or
    config_flow to true) would falsely imply a working config_flow +
    integration tests that we don't have, and the audit would either
    block the PR or let a misleading tier-a claim slip through.
    """
    assert manifest["tier"] == "b", "starlink must stay at tier-b until integration coverage lands"
    assert manifest["wizard"]["one_tap"] is False, (
        "tier-b connections cannot advertise one_tap=true (that's a tier-a contract)"
    )
    # Starlink recipes an operator-side plug integration; RoamCore ships
    # no native config_flow for that (the operator's plug choice is
    # unconstrained). install.config_flow is the RoamCore-owned field
    # and MUST be False at tier-b.
    assert manifest["install"]["config_flow"] is False, (
        "tier-b connection must not advertise RoamCore-owned config_flow=true "
        "(we ship no native integration code for the operator-side power-cycle path)"
    )
    assert manifest["install"]["hacs"] is False, (
        "starlink is a recipe; no HACS integration of our own is shipped"
    )
    # Belt-and-braces: there must be no RoamCore-owned config_flow.py
    # in this folder (no native integration code for a tier-b recipe
    # connection).
    assert not (CONNECTION_DIR / "config_flow.py").is_file(), (
        "tier-b recipe connection must not ship a RoamCore-owned config_flow.py"
    )
    # The __init__.py must be a DOMAIN-stub only — no integration
    # setup logic. We assert it exports DOMAIN and nothing else that
    # smells like HA integration code.
    init_text = (CONNECTION_DIR / "__init__.py").read_text(encoding="utf-8")
    assert "DOMAIN" in init_text, "__init__.py must export DOMAIN for the audit"
    for forbidden in ("async_setup", "config_flow", "PLATFORM_SCHEMA"):
        assert forbidden not in init_text, (
            f"__init__.py must be a DOMAIN stub; found {forbidden!r} (tier-b recipe pattern)"
        )


def test_requires_docs_recipe_published(manifest: dict) -> None:
    """The audit's only tier-b hard requirement, made explicit.

    `docs_recipe_published` must be in tier_requirements AND a real
    recipe file must live on disk where the audit / docs site can
    reach it.
    """
    assert "docs_recipe_published" in manifest["tier_requirements"], (
        "tier-b requires 'docs_recipe_published' in tier_requirements"
    )
    assert RECIPE_PATH.is_file(), (
        f"tier_requirements promises a published recipe but {RECIPE_PATH} does not exist"
    )
    # Sanity: the recipe actually documents Starlink + the contract
    # entities rather than just an empty placeholder.
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert len(text) > 500, "recipe.md looks like a placeholder — should be a real howto"
    assert "Starlink" in text or "starlink" in text, (
        "recipe.md must document the Starlink setup (smart-plug wiring, sleep + wake, signal stats)"
    )
    # The spec requires ≥100 lines; the frigate pattern asserts ≥250.
    # We ship a substantive howto well over both; this catches a
    # regression where someone leaves a 30-line placeholder.
    line_count = len(text.splitlines())
    assert line_count > 100, (
        f"recipe.md must be a substantive howto (>100 lines); got {line_count}"
    )
    # Spec §4 calls for the §1–§7 sections to be present. Grep-anchor
    # the major section headers so a future "I rewrote the recipe as
    # one wall of text" regression gets caught.
    required_sections = (
        "## What is Starlink in RoamCore?",
        "## Prerequisites",
        "## §4 RoamCore contract entities",
        "## §5 Automations",
        "## §6 Troubleshooting",
        "## §7 Privacy",
    )
    for header in required_sections:
        assert header in text, (
            f"recipe.md is missing required section header {header!r} "
            f"(spec §4 requires §1–§7 to be present)"
        )


def test_category_matches_existing_legacy_doc(manifest: dict) -> None:
    """Sanity: category is set (legacy-doc pairing no longer enforced)."""
    assert manifest["category"], "category must be set"


def test_status_reflects_no_real_starlink(manifest: dict) -> None:
    """Status must be honest about no integration being shipped.

    If we ever flip this to 'shipped', the audit will demand an actual
    integration test (and rightly so). 'beta' is the only honest tier-b
    status for a recipe we can't integration-test.
    """
    assert manifest["status"] in {"beta", "wip"}, (
        f"starlink status={manifest['status']!r} implies shipped coverage we don't have; "
        f"use 'beta' or 'wip' until tier-a promotion lands"
    )
    # tier_warnings must include the honest-about-no-terminal marker.
    assert "no_real_starlink_terminal_for_integration_test" in manifest["tier_warnings"], (
        "tier_warnings must declare 'no_real_starlink_terminal_for_integration_test' "
        "for honesty in the audit listing"
    )
    # And the user-facing recipe dependency warning.
    assert "smart_plug_required" in manifest["tier_warnings"], (
        "tier_warnings must declare 'smart_plug_required' so the audit "
        "listing is honest about the operator-bringing-the-plug contract"
    )
    assert "recipe_depends_on_user_smart_plug_or_relay" in manifest["tier_warnings"], (
        "tier_warnings must declare 'recipe_depends_on_user_smart_plug_or_relay' "
        "so the audit listing is honest about the user-bringing-the-plug contract"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))