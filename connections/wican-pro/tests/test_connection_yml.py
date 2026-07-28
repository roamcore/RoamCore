"""Manifest-honesty tests for connections/wican-pro/connection.yml.

This is the only test file we can ship for a tier-b recipe connection
that has no real Wicann Pro device to integration-test against. The
tests here assert that the manifest is *honest about being tier-b* —
that the folder/id/tier invariants hold, and that the recipe doc the
tier_requirements promise is actually present on disk.

If you add real integration coverage (e.g. a config_flow.py + an
integration test against a mock WiCAN REST endpoint), keep this file
and add the new one alongside it; the audit will then list both under
`tests:` in the manifest.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/wican-pro/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> wican-pro/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "wican-pro"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
LEGACY_DOC = REPO_ROOT / "docs" / "catalog" / "vehicle-obd" / "wican-pro.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (wican-pro).

    This is the same invariant the audit script enforces; we duplicate
    it here so pytest catches regressions before CI runs the audit.
    """
    assert manifest["id"] == CONNECTION_DIR.name, (
        f"manifest id={manifest['id']!r} does not match folder name "
        f"{CONNECTION_DIR.name!r}"
    )
    assert manifest["id"] == "wican-pro"


def test_tier_b_without_tier_a_markers(manifest: dict) -> None:
    """Tier-b must NOT advertise tier-a-only fields.

    A regression here (e.g. someone flipping one_tap to true) would
    falsely imply a working config_flow + integration tests that we
    don't have, and the audit would either block the PR or let a
    misleading tier-a claim slip through.
    """
    assert manifest["tier"] == "b", "wican-pro must stay at tier-b until integration coverage lands"
    assert manifest["wizard"]["one_tap"] is False, (
        "tier-b connections cannot advertise one_tap=true (that's a tier-a contract)"
    )
    assert manifest["install"]["config_flow"] is False, (
        "tier-b connections cannot advertise config_flow=true (that's a tier-a contract)"
    )
    assert manifest["install"]["hacs"] is False, (
        "wican-pro is a recipe over core MQTT; HACS only applies if we ship a custom integration"
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
    # Sanity: the recipe actually documents the upstream integration
    # rather than just an empty placeholder.
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert len(text) > 500, "recipe.md looks like a placeholder — should be a real howto"
    assert "MQTT" in text or "ha-wican" in text, (
        "recipe.md must document at least one of the two documented setup paths"
    )


def test_category_matches_existing_legacy_doc(manifest: dict) -> None:
    """Promoted from tier-c legacy doc — category must match."""
    assert manifest["category"] == "vehicle-obd", (
        f"category must stay 'vehicle-obd' (legacy doc lives at "
        f"docs/catalog/vehicle-obd/wican-pro.md); got {manifest['category']!r}"
    )
    assert LEGACY_DOC.is_file(), (
        "expected the legacy tier-c doc to still exist so we can reference it "
        "from the recipe"
    )


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """rc_* tile ids must NOT contain vendor names (per rc-entity-naming.md)."""
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles, "wican-pro contributes at least one dashboard tile"
    forbidden = {"wican", "meatpi", "wican_pro", "wican-pro", "obdlink"}
    for tile in tiles:
        tile_id = tile["id"]
        assert tile_id.startswith("rc_"), f"tile id {tile_id!r} must start with rc_"
        for bad in forbidden:
            assert bad not in tile_id.lower(), (
                f"tile id {tile_id!r} contains vendor name {bad!r}; "
                f"per docs/reference/rc-entity-naming.md, contract ids are vendor-neutral"
            )


def test_status_reflects_no_real_device(manifest: dict) -> None:
    """Status must be honest about the integration not being shipped.

    If we ever flip this to 'shipped', the audit will demand an actual
    integration test (and rightly so). 'beta' is the only honest tier-b
    status for a recipe we can't integration-test.
    """
    assert manifest["status"] in {"beta", "wip"}, (
        f"wican-pro status={manifest['status']!r} implies shipped coverage we don't have; "
        f"use 'beta' or 'wip' until tier-a promotion lands"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))