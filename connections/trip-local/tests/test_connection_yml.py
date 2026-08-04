"""Manifest-honesty tests for the trip-local connection.

These tests assert the `connection.yml` is honest about its tier +
requirements + scope. Mirrors the wican-pro tier-a connection test
pattern; the test suite exists so a regression in the manifest
catches before CI runs the audit.

The 8 checks:
  - test_manifest_required_fields
  - test_id_matches_folder_name
  - test_tier_is_a
  - test_category_is_map
  - test_tier_a_means_recipe_wrapping_roamcore_owned_package
  - test_dashboard_tiles_follow_rc_naming
  - test_openclaw_queries_match_recipe_capabilities
  - test_links_include_required_official_and_cross_references
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> trip-local/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "trip-local"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
README_PATH = CONNECTION_DIR / "README.md"

EXISTING_TRIP_LOCAL_PACKAGE = (
    REPO_ROOT / "homeassistant" / "packages" / "roamcore_trip_local.yaml"
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
    """The manifest `id` must match the folder name (trip-local)."""
    folder_name = Path(__file__).resolve().parents[1].name
    assert folder_name == "trip-local", (
        f"folder name {folder_name!r} does not match spec-required kebab-case 'trip-local'"
    )
    assert manifest["id"] == "trip-local", (
        f"manifest id={manifest['id']!r} must equal the folder name 'trip-local'"
    )


def test_tier_is_a(manifest: dict) -> None:
    """This is a tier-a recipe connection wrapping a RoamCore-owned package.

    Tier-a is honest because RoamCore owns + ships + maintains the
    `homeassistant/packages/roamcore_trip_local.yaml` package — the
    package IS the tier-a surface. Downgrading to tier-b would
    require proving that the slice is NOT wrapping a RoamCore-owned
    surface (which it is).
    """
    assert manifest["tier"] == "a", (
        "trip-local must stay at tier-a; downgrade requires proving "
        "the slice is NOT wrapping a RoamCore-owned package (which it is)"
    )


def test_category_is_map(manifest: dict) -> None:
    """This is a map-category connection (legacy catalog path was
    `docs/catalog/map/trip-local.md`; the slice keeps the
    category: map placement)."""
    assert manifest["category"] == "map", (
        f"manifest category={manifest['category']!r} must equal 'map' "
        f"(the legacy catalog path was docs/catalog/map/trip-local.md)"
    )


def test_tier_a_means_recipe_wrapping_roamcore_owned_package(
    manifest: dict,
) -> None:
    """Tier-a recipe connections wrapping a RoamCore-owned package
    MUST have install.ha_integration_domain == "" (no RoamCore-owned
    custom component is shipped — RoamCore owns the HA package, not
    a Python integration) AND install.packages MUST reference
    `homeassistant/packages/roamcore_trip_local.yaml` (the
    RoamCore-owned package this slice WRAPS).

    The existing package file MUST exist on disk (the tier-a
    claim depends on the package actually being shipped).
    """
    assert "install" in manifest, "manifest must declare install: section"
    assert manifest["install"]["ha_integration_domain"] == "", (
        "tier-a recipe wrapping a RoamCore-owned package must have "
        "install.ha_integration_domain == \"\" (no RoamCore-owned "
        "custom component is shipped — RoamCore owns the HA package)"
    )
    assert "homeassistant/packages/roamcore_trip_local.yaml" in (
        manifest["install"]["packages"]
    ), (
        "install.packages MUST reference "
        "homeassistant/packages/roamcore_trip_local.yaml "
        "(the RoamCore-owned package this slice WRAPS)"
    )
    assert EXISTING_TRIP_LOCAL_PACKAGE.is_file(), (
        f"tier-a claim depends on the existing RoamCore-owned "
        f"package at {EXISTING_TRIP_LOCAL_PACKAGE} being shipped; "
        f"file not found"
    )


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """All 3 dashboard tiles MUST start with `rc_trip_local_today_`
    per `docs/reference/rc-entity-naming.md` (the `trip` subsystem
    added by this slice).

    The naming rule forbids vendor names in any `rc_*` entity id —
    the forbidden vendor names for trip-local are `traccar`,
    `owntracks`, `gpx`, `cloud_route`, `route_engine`.
    """
    forbidden = {"traccar", "owntracks", "gpx", "cloud_route", "route_engine"}
    expected_suffix = ".rc_trip_local_today_"
    expected_subsystem_suffix = "rc_trip_local_today_"
    tiles = manifest["dashboard"]["tiles"]
    assert len(tiles) == 3, (
        f"trip-local must declare exactly 3 dashboard tiles "
        f"(distance_mi + drive_time + stops); got {len(tiles)}"
    )
    for tile in tiles:
        # Tile is a full entity_id: '<domain>.<entity_id>'.
        # The contract surface is the `<entity_id>` portion, which
        # must use the `rc_trip_local_today_` prefix per the `trip`
        # subsystem added by this slice.
        assert expected_suffix in tile, (
            f"tile {tile!r} does not use the rc_trip_local_today_ "
            f"contract prefix"
        )
        # The entity_id portion (after the leading domain + dot)
        # must use the `rc_trip_local_today_` prefix.
        assert tile.split(".", 1)[-1].startswith(expected_subsystem_suffix), (
            f"tile {tile!r} entity_id portion does not start with "
            f"{expected_subsystem_suffix!r}"
        )
        for word in forbidden:
            assert word not in tile.lower(), (
                f"tile {tile!r} contains forbidden vendor name {word!r}"
            )


def test_openclaw_queries_match_recipe_capabilities(
    manifest: dict,
) -> None:
    """The openclaw.queries list must reflect what the recipe can
    answer (today's distance / drive_time / stops + the
    local-first trip summary).

    The openclaw.summary_keys list must use the `trip_local_today_`
    prefix per the `trip` subsystem convention added by this slice.
    """
    expected_queries = {
        "distance",
        "drive time",
        "stops",
        "local-first trip summary",
    }
    actual_queries = " ".join(
        manifest.get("openclaw", {}).get("queries", [])
    ).lower()
    for needle in expected_queries:
        assert needle.lower() in actual_queries, (
            f"openclaw.queries must include a query about {needle!r}"
        )

    expected_summary_prefix = "trip_local_today_"
    for key in manifest.get("openclaw", {}).get("summary_keys", []):
        assert key.startswith(expected_summary_prefix), (
            f"summary_key {key!r} must start with {expected_summary_prefix!r}"
        )

    forbidden = {"traccar", "owntracks", "gpx"}
    for q in manifest.get("openclaw", {}).get("queries", []):
        for word in forbidden:
            assert word not in q.lower(), (
                f"query {q!r} contains forbidden vendor name {word!r}"
            )


def test_links_include_required_official_and_cross_references(
    manifest: dict,
) -> None:
    """The manifest's links.official list MUST include the HA
    recorder + command_line + shell_command + input_text +
    automation integration docs (the actual upstream surface).

    The manifest's links.cross_references list MUST include the
    sibling connections that the recipe references
    (map-dashboard Wave 3 #66 + mode Wave 3 #61 +
    remote-access Wave 3 #58 + advanced-mode Wave 3 #63 +
    openclaw-api Wave 3 #64 + leveling Wave 3 #60).
    """
    required_official = {
        "recorder",
        "command_line",
        "shell_command",
        "input_text",
        "automation",
    }
    official = " ".join(
        manifest.get("links", {}).get("official", [])
    ).lower()
    for needle in required_official:
        assert needle in official, (
            f"links.official must include the HA {needle!r} "
            f"integration doc URL"
        )

    required_cross_refs = {
        "map-dashboard",
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