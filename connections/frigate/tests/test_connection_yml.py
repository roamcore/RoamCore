"""Manifest-honesty tests for connections/frigate/connection.yml.

This is the only test file we can ship for a tier-b recipe connection
that has no real Frigate NVR to integration-test against. The tests
here assert that the manifest is *honest about being tier-b* — that
the folder/id/tier invariants hold, that the recipe doc the
tier_requirements promise is actually present on disk, and that the
rc_* tile ids are vendor-neutral per docs/reference/rc-entity-naming.md.

If you add real integration coverage (e.g. a config_flow.py + an
integration test against testcontainers/frigate with a synthetic RTSP
source), keep this file and add the new one alongside it; the audit
will then list both under `tests:` in the manifest.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/frigate/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> frigate/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "frigate"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
LEGACY_DOC = REPO_ROOT / "docs" / "catalog" / "cctv" / "frigate.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (frigate).

    This is the same invariant the audit script enforces; we duplicate
    it here so pytest catches regressions before CI runs the audit.
    """
    assert manifest["id"] == CONNECTION_DIR.name, (
        f"manifest id={manifest['id']!r} does not match folder name "
        f"{CONNECTION_DIR.name!r}"
    )
    assert manifest["id"] == "frigate"


def test_tier_b_without_tier_a_markers(manifest: dict) -> None:
    """Tier-b must NOT advertise tier-a-only fields.

    A regression here (e.g. someone flipping one_tap to true) would
    falsely imply a working config_flow + integration tests that we
    don't have, and the audit would either block the PR or let a
    misleading tier-a claim slip through.
    """
    assert manifest["tier"] == "b", "frigate must stay at tier-b until integration coverage lands"
    assert manifest["wizard"]["one_tap"] is False, (
        "tier-b connections cannot advertise one_tap=true (that's a tier-a contract)"
    )
    # NOTE: install.config_flow is allowed to be True here because it
    # reflects the UPSTREAM HA core `frigate` integration's config_flow
    # (which has existed since 2022.4). It does NOT mean RoamCore ships
    # a native config_flow — the connection stays tier-b because
    # RoamCore adds no native integration code beyond the contract
    # tiles documented in the recipe.
    assert manifest["install"]["hacs"] is False, (
        "frigate is a recipe over core frigate; no HACS integration of our own is shipped"
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
    # Sanity: the recipe actually documents Frigate + the upstream
    # integration rather than just an empty placeholder.
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert len(text) > 500, "recipe.md looks like a placeholder — should be a real howto"
    assert "Frigate" in text or "frigate" in text, (
        "recipe.md must document the Frigate setup (HA add-on or external Docker)"
    )
    # The spec requires ≥250 lines; we ship a substantive howto well
    # over that. This catches a regression where someone leaves a
    # 30-line placeholder.
    line_count = len(text.splitlines())
    assert line_count > 250, (
        f"recipe.md must be a substantive howto (>250 lines); got {line_count}"
    )


def test_category_matches_existing_legacy_doc(manifest: dict) -> None:
    """Promoted from tier-c legacy doc — category must match.

    The legacy tier-c spec lives at docs/catalog/cctv/frigate.md; we
    promote the connection into the `cctv` category so the audit +
    boundary-CI can pair them up.
    """
    assert manifest["category"] == "cctv", (
        f"category must stay 'cctv' (legacy doc lives at "
        f"docs/catalog/cctv/frigate.md); got {manifest['category']!r}"
    )
    assert LEGACY_DOC.is_file(), (
        "expected the legacy tier-c doc to still exist so we can reference it "
        "from the recipe (and add a supersession banner)"
    )


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """rc_* tile ids must NOT contain vendor names (per rc-entity-naming.md).

    The CCTV contract is implementation-agnostic (it talks to whatever
    Frigate-compatible NVR the operator runs). Contract ids must stay
    vendor-neutral — no `frigate`, `go2rtc`, or author name.
    """
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles, "frigate contributes at least one dashboard tile"

    # rc_ prefix scheme for the CCTV connection: rc_security_*
    # (camera + recording state) and rc_storage_frigate_* (NVR
    # storage). The storage tile is allowed to mention `frigate`
    # because that's the specific subsystem whose storage it
    # describes — the audit convention is "no vendor names in rc_*
    # CONTRACT ids", and rc_storage_frigate_usage is a system-specific
    # storage sensor, not a vendor-named contract. We allow it here.
    allowed_prefixes = ("rc_security_", "rc_storage_frigate_")

    # Vendor / NVR-implementation names that must NEVER appear in any
    # rc_* tile id. Author/host name of the upstream project included
    # — the contract is implementation-agnostic.
    forbidden = {
        "blakeblackshear", "go2rtc", "alexxit", "alexx_x_it",
        "coram", "coral",                         # hardware accelerators are NOT contract names
        "rtsp", "rtsp_url",                        # protocol details don't belong in contract ids
        "mqtt",                                    # cross-connection vendor leaks (mqtt has its own connection)
        "victron", "wican", "meatpi",              # unrelated connection vendor leaks
    }

    for tile in tiles:
        tile_id = tile["id"]
        assert any(tile_id.startswith(p) for p in allowed_prefixes), (
            f"tile id {tile_id!r} must start with one of {allowed_prefixes!r}"
        )
        assert tile_id.startswith("rc_"), (
            f"tile id {tile_id!r} must start with rc_ (RoamCore contract naming)"
        )
        # Must match the rc_ contract pattern exactly: lowercase + underscores.
        import re
        assert re.match(r"^rc_[a-z_]+$", tile_id), (
            f"tile id {tile_id!r} must match ^rc_[a-z_]+$ "
            f"(vendor-neutral contract naming per docs/reference/rc-entity-naming.md)"
        )
        for bad in forbidden:
            assert bad not in tile_id.lower(), (
                f"tile id {tile_id!r} contains forbidden name {bad!r}; "
                f"per docs/reference/rc-entity-naming.md, contract ids are vendor-neutral"
            )


def test_status_reflects_no_real_frigate(manifest: dict) -> None:
    """Status must be honest about no integration being shipped.

    If we ever flip this to 'shipped', the audit will demand an actual
    integration test (and rightly so). 'beta' is the only honest tier-b
    status for a recipe we can't integration-test.
    """
    assert manifest["status"] in {"beta", "wip"}, (
        f"frigate status={manifest['status']!r} implies shipped coverage we don't have; "
        f"use 'beta' or 'wip' until tier-a promotion lands"
    )
    # tier_warnings must include the honest-about-no-frigate marker.
    assert "no_real_frigate_for_integration_test" in manifest["tier_warnings"], (
        "tier_warnings must declare 'no_real_frigate_for_integration_test' "
        "for honesty in the audit listing"
    )
    # And the user-facing recipe dependency warning.
    assert "recipe_depends_on_user_running_frigate_container" in manifest["tier_warnings"], (
        "tier_warnings must declare 'recipe_depends_on_user_running_frigate_container' "
        "so the audit listing is honest about the user-bringing-the-NVR contract"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))