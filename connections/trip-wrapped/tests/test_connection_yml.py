"""Manifest-honesty tests for the trip-wrapped connection.

These tests assert the `connection.yml` is honest about its tier +
requirements + scope. Mirrors the trip-local / wican-pro tier-a
connection test pattern; the test suite exists so a regression in
the manifest catches before CI runs the audit.

The 8 checks:
  - test_manifest_required_fields
  - test_id_matches_folder_name
  - test_tier_is_a
  - test_category_is_map
  - test_tier_a_means_recipe_wrapping_roamcore_owned_package_and_tooling
  - test_dashboard_tiles_follow_rc_naming
  - test_openclaw_queries_match_recipe_capabilities
  - test_links_include_required_official_and_cross_references
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> trip-wrapped/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "trip-wrapped"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
README_PATH = CONNECTION_DIR / "README.md"

EXISTING_TRIP_WRAPPED_PACKAGE = (
    REPO_ROOT / "homeassistant" / "packages" / "roamcore_trip_wrapped.yaml"
)
EXISTING_TRIP_WRAPPED_TOOLING = (
    REPO_ROOT / "homeassistant" / "tools" / "trip_wrapped"
)


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_manifest_required_fields(manifest: dict) -> None:
    """All required manifest fields are present."""
    for key in (
        "id",
        "name",
        "tier",
        "category",
        "status",
        "version",
        "description",
    ):
        assert manifest.get(key) is not None, (
            f"missing required field: {key}"
        )


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must match the folder name (trip-wrapped)."""
    folder_name = Path(__file__).resolve().parents[1].name
    assert folder_name == "trip-wrapped", (
        f"folder name {folder_name!r} does not match spec-required kebab-case 'trip-wrapped'"
    )
    assert manifest["id"] == "trip-wrapped", (
        f"manifest id={manifest['id']!r} must equal the folder name 'trip-wrapped'"
    )


def test_tier_is_a(manifest: dict) -> None:
    """This is a tier-a recipe connection wrapping a RoamCore-owned
    package + report-renderer tooling.

    Tier-a is honest because RoamCore owns + ships + maintains both
    the `homeassistant/packages/roamcore_trip_wrapped.yaml` package
    AND the report-renderer tooling under
    `homeassistant/tools/trip_wrapped/` — the package + the tooling
    ARE the tier-a surface. Downgrading to tier-b would require
    proving that the slice is NOT wrapping a RoamCore-owned
    surface (which it is).
    """
    assert manifest["tier"] == "a", (
        "trip-wrapped must stay at tier-a; downgrade requires proving "
        "the slice is NOT wrapping a RoamCore-owned package + tooling "
        "(which it is)"
    )


def test_category_is_map(manifest: dict) -> None:
    """This is a map-category connection (legacy catalog path was
    `docs/catalog/map/trip-wrapped.md`; the slice keeps the
    category: map placement)."""
    assert manifest["category"] == "map", (
        f"manifest category={manifest['category']!r} must equal 'map' "
        f"(the legacy catalog path was docs/catalog/map/trip-wrapped.md)"
    )


def test_tier_a_means_recipe_wrapping_roamcore_owned_package_and_tooling(
    manifest: dict,
) -> None:
    """Tier-a recipe connections wrapping a RoamCore-owned package
    + tooling MUST have install.ha_integration_domain == "" (no
    RoamCore-owned custom component is shipped at the connections/
    level — RoamCore owns the HA package + the tooling, not a
    Python integration under connections/) AND install.packages MUST
    reference `homeassistant/packages/roamcore_trip_wrapped.yaml`
    (the RoamCore-owned package this slice WRAPS).

    The existing package file MUST exist on disk (the tier-a
    claim depends on the package actually being shipped). The
    existing tooling directory MUST exist on disk (the tier-a
    claim depends on the report-renderer actually being shipped).
    """
    assert "install" in manifest, "manifest must declare install: section"
    assert manifest["install"]["ha_integration_domain"] == "", (
        "tier-a recipe wrapping a RoamCore-owned package + tooling "
        "must have install.ha_integration_domain == \"\" (no "
        "RoamCore-owned custom component is shipped at the "
        "connections/ level — RoamCore owns the HA package + the "
        "tooling)"
    )
    assert "homeassistant/packages/roamcore_trip_wrapped.yaml" in (
        manifest["install"]["packages"]
    ), (
        "install.packages MUST reference "
        "homeassistant/packages/roamcore_trip_wrapped.yaml "
        "(the RoamCore-owned package this slice WRAPS)"
    )
    assert EXISTING_TRIP_WRAPPED_PACKAGE.is_file(), (
        f"tier-a claim depends on the existing RoamCore-owned "
        f"package at {EXISTING_TRIP_WRAPPED_PACKAGE} being shipped; "
        f"file not found"
    )
    assert EXISTING_TRIP_WRAPPED_TOOLING.is_dir(), (
        f"tier-a claim depends on the existing RoamCore-owned "
        f"report-renderer tooling at {EXISTING_TRIP_WRAPPED_TOOLING} "
        f"being shipped; directory not found"
    )


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """All 3 dashboard tiles MUST start with `rc_trip_wrapped_` or
    `rc_traccar_ui_` per `docs/reference/rc-entity-naming.md` (the
    `trip` subsystem added by the trip-local Wave 3 #68 sibling
    slice).

    The naming rule forbids vendor names in any `rc_*` entity id —
    the forbidden vendor names for trip-wrapped are `spotify`,
    `apple_music`, `wrapped_attribution_chip`, `route_engine`,
    `cloud_recap`. Traccar IS the canonical source for the upstream
    trip-history data, so `rc_traccar_ui_reachable` is the explicit
    exception per Hard Rule #1: the vendor name IS the canonical
    product name; the data-source-prefix is allowed.
    """
    forbidden = {"spotify", "apple_music", "wrapped_attribution_chip",
                 "route_engine", "cloud_recap"}
    allowed_prefixes = ("rc_trip_wrapped_", "rc_traccar_ui_")
    tiles = manifest["dashboard"]["tiles"]
    assert len(tiles) == 3, (
        f"trip-wrapped must declare exactly 3 dashboard tiles "
        f"(latest_ready + latest_status + traccar_ui_reachable); "
        f"got {len(tiles)}"
    )
    for tile in tiles:
        # Tile is a full entity_id: '<domain>.<entity_id>'.
        # The contract surface is the `<entity_id>` portion, which
        # must use one of the allowed prefixes per the `trip`
        # subsystem added by the trip-local Wave 3 #68 sibling slice.
        entity_id = tile.split(".", 1)[-1]
        assert any(entity_id.startswith(prefix) for prefix in allowed_prefixes), (
            f"tile {tile!r} entity_id portion {entity_id!r} does not "
            f"start with any allowed prefix {allowed_prefixes!r} "
            f"(the `trip` subsystem prefix is `rc_trip_wrapped_`; "
            f"the data-source-prefix for Traccar (canonical upstream "
            f"trip-history source) is `rc_traccar_ui_`)"
        )
        for word in forbidden:
            assert word not in tile.lower(), (
                f"tile {tile!r} contains forbidden vendor name {word!r}"
            )


def test_openclaw_queries_match_recipe_capabilities(
    manifest: dict,
) -> None:
    """The openclaw.queries list must reflect what the recipe can
    answer (latest trip wrapped report + readiness + Traccar UI
    reachability + status + export status).

    The openclaw.summary_keys list must use the `trip_wrapped_` or
    `traccar_ui_` prefix per the `trip` subsystem convention
    added by the trip-local Wave 3 #68 sibling slice.
    """
    expected_queries = {
        "latest trip wrapped",
        "ready",
        "traccar ui",
        "status",
        "export status",
    }
    actual_queries = " ".join(
        manifest.get("openclaw", {}).get("queries", [])
    ).lower()
    for needle in expected_queries:
        assert needle.lower() in actual_queries, (
            f"openclaw.queries must include a query about {needle!r}"
        )

    expected_summary_prefixes = ("trip_wrapped_", "traccar_ui_")
    for key in manifest.get("openclaw", {}).get("summary_keys", []):
        assert any(
            key.startswith(prefix) for prefix in expected_summary_prefixes
        ), (
            f"summary_key {key!r} must start with one of "
            f"{expected_summary_prefixes!r}"
        )

    forbidden = {"spotify", "apple_music", "cloud_recap"}
    for q in manifest.get("openclaw", {}).get("queries", []):
        for word in forbidden:
            assert word not in q.lower(), (
                f"query {q!r} contains forbidden vendor name {word!r}"
            )


def test_links_include_required_official_and_cross_references(
    manifest: dict,
) -> None:
    """The manifest's links.official list MUST include the HA
    shell_command + input_text + input_number + command_line +
    script integration docs + the Traccar reports endpoint (the
    actual upstream surface).

    The manifest's links.cross_references list MUST include the
    sibling connections that the recipe references
    (trip-local Wave 3 #68 + map-dashboard Wave 3 #66 + traccar
    Wave 3 #12 + mode Wave 3 #61 + remote-access Wave 3 #58 +
    advanced-mode Wave 3 #63 + openclaw-api Wave 3 #64 + leveling
    Wave 3 #60).
    """
    required_official = {
        "shell_command",
        "input_text",
        "input_number",
        "command_line",
        "script",
        "traccar.org/reports",
    }
    official = " ".join(
        manifest.get("links", {}).get("official", [])
    ).lower()
    for needle in required_official:
        assert needle in official, (
            f"links.official must include the HA / Traccar {needle!r} "
            f"integration doc URL"
        )

    required_cross_refs = {
        "trip-local",
        "map-dashboard",
        "traccar",
        "mode",
        "remote-access",
        "advanced-mode",
        "openclaw-api",
        "leveling",
    }
    cross_refs = manifest.get("links", {}).get("cross_references", [])
    actual_cross_refs = " ".join(cross_refs).lower()
    for needle in required_cross_refs:
        assert needle in actual_cross_refs, (
            f"links.cross_references must include the {needle!r} "
            f"connection (sibling slice; the recipe documents "
            f"this cross-reference)"
        )


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))