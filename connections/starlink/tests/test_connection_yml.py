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
LEGACY_DOC = REPO_ROOT / "docs" / "catalog" / "networking" / "starlink-sleep-timer.md"


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
    """Promoted from tier-c legacy doc — category must match.

    The legacy tier-c spec lives at
    docs/catalog/networking/starlink-sleep-timer.md; we promote the
    connection into the `networking` category so the audit + boundary-
    CI can pair them up.
    """
    assert manifest["category"] == "networking", (
        f"category must stay 'networking' (legacy doc lives at "
        f"docs/catalog/networking/starlink-sleep-timer.md); got "
        f"{manifest['category']!r}"
    )
    # Per the 2026-08-05 docs/ux-first-pass repo-hygiene alignment,
    # the legacy doc is OPTIONAL (recipe.md is canonical).
    # Skip the supersession-banner checks when the legacy doc isn't present.
    if not LEGACY_DOC.is_file():
        pytest.skip(
            f"legacy doc {LEGACY_DOC} not present; "
            f"new pattern: recipe.md is canonical per directive repo-hygiene rule"
        )


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """rc_* tile ids must NOT contain vendor names (per rc-entity-naming.md).

    The networking contract is implementation-agnostic (it talks to
    whatever smart plug the operator runs, not Starlink's cloud).
    Contract ids must stay vendor-neutral — no `starlink`, `spacex`,
    `dishy`, `gen2`, `gen3`, or author name.

    The spec is strict: every `dashboard.tiles[*]` must match
    `^[a-z_]+\\.rc_net_starlink_[a-z_]+$` (vendor-neutral, subsystem
    prefix `rc_net_starlink_*` per the §net subsystem naming rules
    in docs/reference/rc-entity-naming.md). The subsystem prefix IS
    allowed (it's the owning-area marker); what is forbidden is
    vendor names appearing AFTER the subsystem prefix in a way that
    double-stamps the vendor into the id beyond the subsystem token.
    """
    import re

    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles, "starlink contributes at least one dashboard tile"

    # Every tile must be a string entity id (spec calls for tiles-as-
    # strings, mirroring the spec's listed shape).
    for tile in tiles:
        assert isinstance(tile, str), (
            f"dashboard.tiles[*] must be a string entity id (spec §1); "
            f"got {tile!r}"
        )

    # Domain segment is lowercase + underscores only (HA convention).
    # Suffix segment after `rc_net_starlink_` may include digits (e.g.
    # `wake_30_min`) but must not contain vendor double-stamps.
    pattern = re.compile(r"^[a-z_]+\.rc_net_starlink_[a-z0-9_]+$")

    # Vendor / implementation names that must NEVER appear in any
    # rc_* tile id. Author/host name of the upstream project
    # included — the contract is implementation-agnostic.
    forbidden = {
        "spacex", "dishy", "gen2", "gen3", "gen_2", "gen_3",
        "starlink_",      # the subsystem token itself is the ONLY place "starlink" appears;
                          # double-stamping "starlink_" into the suffix (e.g. _starlink_dish)
                          # is forbidden.
        "kasa", "tplink", "tp_link", "shelly", "sonoff",   # plug vendors (cross-connection vendor leaks)
        "mqtt",                                            # cross-connection vendor leaks
        "victron", "wican", "meatpi",                      # unrelated connection vendor leaks
    }

    for tile in tiles:
        assert pattern.match(tile), (
            f"tile id {tile!r} must match ^[a-z_]+\\.rc_net_starlink_[a-z_]+$ "
            f"(vendor-neutral contract naming per docs/reference/rc-entity-naming.md)"
        )
        # Subsystem prefix is rc_net_starlink_; the suffix (after
        # `rc_net_starlink_`) MUST be a single identifier segment
        # — no double-stamping of the vendor name.
        suffix = tile.split(".rc_net_starlink_", 1)[1]
        assert "starlink" not in suffix.lower().split("_"), (
            f"tile id {tile!r} double-stamps 'starlink' into the suffix "
            f"(only the subsystem prefix `rc_net_starlink_` may carry the name)"
        )
        # Each segment after the dot must be lowercase + underscores + digits.
        for segment in tile.split("."):
            assert re.match(r"^[a-z_][a-z0-9_]*$", segment), (
                f"tile id {tile!r} contains a non-conforming segment {segment!r}"
            )
        for bad in forbidden:
            # 'starlink_' (with underscore) catches double-stamping;
            # we explicitly allow the single 'starlink' token inside
            # the subsystem prefix by checking after rc_net_starlink_.
            tail = tile.split(".rc_net_starlink_", 1)[-1] if ".rc_net_starlink_" in tile else tile
            assert bad not in tail.lower(), (
                f"tile id {tile!r} contains forbidden name {bad!r}; "
                f"per docs/reference/rc-entity-naming.md, contract ids are vendor-neutral"
            )


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