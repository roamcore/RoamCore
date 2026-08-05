"""Manifest-honesty tests for connections/mock-location-and-tracks/connection.yml.

This is the FIRST tier-a connection slice in Wave 3 (all prior Wave 3
slices were tier-b recipe-over-upstream). The tests here assert that
the manifest is *honest about being tier-a* — that the folder/id/
tier invariants hold, that the recipe doc the tier_requirements
promise is actually present on disk with ≥10 §sections, that the
three YAML packages + the Python generator are present on disk, that
the `__init__.py` exports `DOMAIN = "mock_location"` and does NOT
contain a `config_flow` substring (tier-a DOES NOT use config_flow.py
because RoamCore owns the integration as a package — there is no
upstream vendor integration to wrap), that the 9 `rc_map_mock_*`
dashboard tiles are vendor-neutral per docs/reference/rc-entity-naming.md
§map subsystem (the `map` subsystem was added to the allowed
subsystems list alongside this slice), that the status reflects the
honest "no real GPS for integration test" tier_warnings, and that the
three mock YAML packages are wired into homeassistant/configuration.yaml
(via the `!include_dir_named packages` directive in
`homeassistant/configuration_addon.yaml`).

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/mock-location-and-tracks/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]
CONNECTION_DIR = REPO_ROOT / "connections" / "mock-location-and-tracks"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
LEGACY_DOC = REPO_ROOT / "docs" / "catalog" / "map" / "mock-location-and-tracks.md"

# Tier-a audit markers — these files MUST be present on disk because
# tier-a claims RoamCore owns all of the integration code natively.
MOCK_PACKAGES = (
    REPO_ROOT / "homeassistant" / "packages" / "roamcore_mock_track.yaml",
    REPO_ROOT / "homeassistant" / "packages" / "roamcore_mock_location_trail.yaml",
    REPO_ROOT / "homeassistant" / "packages" / "roamcore_dev_mocks.yaml",
)
PYTHON_GENERATOR = REPO_ROOT / "homeassistant" / "tools" / "mock_track" / "generate.py"

# The three mock packages are wired in via `!include_dir_named packages`
# in homeassistant/configuration_addon.yaml — so any file dropped under
# homeassistant/packages/ is automatically picked up. We verify the
# directive is present AND the three files exist on disk.
CONFIG_ADDON = REPO_ROOT / "homeassistant" / "configuration_addon.yaml"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (mock-location-and-tracks)."""
    assert manifest["id"] == CONNECTION_DIR.name
    assert manifest["id"] == "mock-location-and-tracks"


def test_tier_a_with_native_markers(manifest: dict) -> None:
    """Tier-a must advertise the native markers (NOT recipe)."""
    assert manifest["tier"] == "a", (
        "tier-a is REQUIRED for this slice — RoamCore owns the YAML "
        "packages + the Python generator natively and there is no "
        "external broker / device / vendor dependency"
    )
    assert manifest["wizard"]["connection_kind"] == "native", (
        "wizard.connection_kind must be 'native' (NOT 'recipe') — "
        "the tier-a audit convention established by this slice"
    )
    assert manifest["wizard"]["one_tap"] is True, (
        "wizard.one_tap must be True — the mock auto-runs on HA "
        "startup via automation.rc_mock_track_generate_on_startup "
        "(no operator setup required for the package to load)"
    )
    assert manifest["install"]["kind"] == "ha_package", (
        "install.kind must be 'ha_package' (NOT 'recipe-over-upstream') "
        "— the tier-a audit convention established by this slice"
    )
    assert manifest["install"]["config_flow"] is False, (
        "install.config_flow must be False — tier-a DOES NOT use "
        "config_flow.py because RoamCore owns the integration as a "
        "package (there is no upstream vendor integration to wrap)"
    )
    assert manifest["install"]["hacs"] is False

    # The three YAML packages must exist on disk in homeassistant/packages/.
    for pkg_path in MOCK_PACKAGES:
        assert pkg_path.is_file(), (
            f"required tier-a asset missing on disk: {pkg_path} — "
            f"tier-a claims RoamCore owns the YAML packages natively"
        )

    # The Python generator must exist on disk.
    assert PYTHON_GENERATOR.is_file(), (
        f"required tier-a asset missing on disk: {PYTHON_GENERATOR} — "
        f"tier-a claims RoamCore owns the Python generator natively"
    )

    # The install.packages manifest list must reference all three YAML files.
    install_packages = manifest["install"]["packages"]
    expected = {
        "homeassistant/packages/roamcore_mock_track.yaml",
        "homeassistant/packages/roamcore_mock_location_trail.yaml",
        "homeassistant/packages/roamcore_dev_mocks.yaml",
    }
    assert expected.issubset(set(install_packages)), (
        f"install.packages must reference all three mock YAML files; "
        f"got {install_packages!r}; missing {expected - set(install_packages)!r}"
    )

    # The Python generator is stdlib-only (no shapely import) — verify
    # that python_requirements is empty OR that it lists stdlib modules
    # that are already part of Python 3.11+.
    py_reqs = manifest["install"].get("python_requirements", [])
    assert isinstance(py_reqs, list)
    for req in py_reqs:
        # If a future slice adds shapely, the manifest should list
        # `shapely>=2.0` here — but for now, stdlib-only is the
        # honest truth.
        assert "shapely" not in req.lower(), (
            f"unexpected python_requirement {req!r} — the generator "
            f"is stdlib-only; if a future slice adds shapely, update "
            f"this test"
        )

    # __init__.py must export DOMAIN = "mock_location" and must NOT
    # contain a `config_flow` substring (tier-a DOES NOT use
    # config_flow.py).
    init_text = (CONNECTION_DIR / "__init__.py").read_text(encoding="utf-8")
    assert "DOMAIN" in init_text
    assert 'DOMAIN = "mock_location"' in init_text, (
        "__init__.py must export DOMAIN = \"mock_location\" — the "
        "audit convention uses the singular short name for the map "
        "category (not the full hyphen-separated folder name)"
    )
    assert "config_flow" not in init_text, (
        "__init__.py must NOT contain a `config_flow` substring — "
        "tier-a DOES NOT use config_flow.py because RoamCore owns "
        "the integration as a package"
    )
    # No config_flow.py at the folder root either.
    assert not (CONNECTION_DIR / "config_flow.py").is_file(), (
        "config_flow.py must NOT exist at the folder root — tier-a "
        "DOES NOT use config_flow.py because RoamCore owns the "
        "integration as a package"
    )


def test_requires_docs_recipe_published(manifest: dict) -> None:
    """The audit's tier-a hard requirements (docs + python + packages)."""
    assert "docs_recipe_published" in manifest["tier_requirements"]
    assert "python_generator_present" in manifest["tier_requirements"]
    assert "packages_present_in_homeassistant_yaml" in manifest["tier_requirements"]

    assert RECIPE_PATH.is_file(), (
        f"recipe.md must exist at {RECIPE_PATH} — tier-a requires "
        f"docs_recipe_published"
    )
    text = RECIPE_PATH.read_text(encoding="utf-8")
    line_count = len(text.splitlines())
    assert line_count >= 250, (
        f"recipe.md must be ≥250 lines per the slice spec; got {line_count}"
    )

    # Must have 11 §sections.
    import re
    section_headers = re.findall(r"^## §\d+ .+$", text, flags=re.MULTILINE)
    assert len(section_headers) >= 10, (
        f"recipe.md must have ≥10 §section headers; got {len(section_headers)}: "
        f"{section_headers!r}"
    )

    # Must cover the 6 built-in presets in §4.
    required_presets = (
        "uk_roadtrip",
        "us_west_coast",
        "alps_loop",
        "desert_southwest",
        "scandinavia_north",
        "custom",
    )
    for preset in required_presets:
        assert preset in text, (
            f"recipe.md §4 must cover preset {preset!r}"
        )

    # Must reference the 9 contract tiles.
    required_tiles = (
        "input_boolean.rc_map_mock_enabled",
        "input_text.rc_map_mock_location_trail",
        "input_select.rc_map_mock_preset",
        "input_number.rc_map_mock_points_per_leg",
        "input_number.rc_map_mock_jitter_m",
        "button.rc_map_mock_generate_now",
        "sensor.rc_map_mock_track_length_km",
        "sensor.rc_map_mock_track_point_count",
        "binary_sensor.rc_map_mock_track_fresh",
    )
    for tile in required_tiles:
        assert tile in text, (
            f"recipe.md must reference contract tile {tile!r}"
        )


def test_category_matches_existing_legacy_doc(manifest: dict) -> None:
    """Category must match the (now optional) legacy doc or the recipe.md.

    Per the 2026-08-05 docs/ux-first-pass repo-hygiene alignment, the
    legacy `docs/catalog/.../mock-location-and-tracks.md` is OPTIONAL
    (recipe.md is canonical). The legacy doc, when present, is the
    IKEA-style overview — it does NOT carry a 'Replaced by' banner
    anymore. We just verify the category matches and skip the
    supersession-banner check if the legacy doc isn't present.
    """
    assert manifest["category"] == "map"
    if not LEGACY_DOC.is_file():
        pytest.skip(
            f"legacy doc {LEGACY_DOC} not present; "
            f"new pattern: recipe.md is canonical per directive repo-hygiene rule"
        )


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """rc_* tile ids must NOT contain vendor names or generic nouns."""
    import re

    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles
    for tile in tiles:
        assert isinstance(tile, str)

    pattern = re.compile(r"^[a-z_]+\.rc_map_mock_[a-z0-9_]+$")
    forbidden_substrings = (
        # vendor names (absolute forbidden)
        "nest", "kidde", "first_alert", "firstalert",
        "x_sense", "xsense", "x-sense", "heiman", "zipato",
        "victron", "traccar", "openwrt", "esphome", "zigbee",
        "z_wave", "zwave", "z-wave", "mqtt", "tuya", "xiaomi",
        "philips", "ubiquiti", "unifi", "mikrotik",
        # preset names (forbidden — they are not vendor names but
        # they would couple the contract to specific synthetic routes)
        "uk_roadtrip", "us_west_coast", "alps_loop",
        "desert_southwest", "scandinavia_north",
        # format names (forbidden — they would couple the contract
        # to a specific polyline format)
        "polyline", "geojson", "shapely", "gpxtpx",
        # the old tier-b-style double-stamps would couple the contract
        # to the specific implementation; tier-a uses the
        # vendor-neutral `rc_map_mock_*` prefix
        "mock_location_and_tracks", "mock_track", "mock_trail",
    )

    for tile in tiles:
        assert pattern.match(tile), (
            f"tile id {tile!r} must match ^[a-z_]+\\.rc_map_mock_[a-z0-9_]+$"
        )
        suffix = tile.split(".rc_map_mock_", 1)[1]
        for bad in forbidden_substrings:
            assert bad not in suffix.lower(), (
                f"tile id {tile!r} contains forbidden substring {bad!r}"
            )
        for segment in tile.split("."):
            assert re.match(r"^[a-z_][a-z0-9_]*$", segment)

    # Exactly 9 contract tiles: 1 input_boolean + 1 input_text +
    # 1 input_select + 2 input_numbers + 1 button + 2 sensors +
    # 1 binary_sensor = 9.
    assert len(tiles) == 9, (
        f"mock-location-and-tracks must contribute exactly 9 "
        f"contract tiles; verify the manifest matches §5; got {len(tiles)}"
    )


def test_status_reflects_no_real_gps(manifest: dict) -> None:
    """Status must be honest about no real GPS for integration test."""
    assert manifest["status"] == "beta"
    tier_warnings = manifest.get("tier_warnings", [])
    assert "no_real_gps_for_integration_test" in tier_warnings
    assert "operator_must_opt_in_via_input_boolean" in tier_warnings
    assert "mock_does_not_replace_real_traccar" in tier_warnings
    assert "deterministic_preset_not_real_telemetry" in tier_warnings


def test_mock_packages_wired_into_homeassistant_yaml() -> None:
    """The three mock packages must be wired into homeassistant/configuration.yaml
    (via `!include_dir_named packages` in configuration_addon.yaml — so
    any file dropped under homeassistant/packages/ is automatically
    picked up)."""
    assert CONFIG_ADDON.is_file(), (
        f"homeassistant/configuration_addon.yaml must exist at "
        f"{CONFIG_ADDON} — it provides the `!include_dir_named "
        f"packages` directive that auto-includes all mock packages"
    )
    config_addon_text = CONFIG_ADDON.read_text(encoding="utf-8")
    assert "packages: !include_dir_named packages" in config_addon_text, (
        "homeassistant/configuration_addon.yaml must contain the "
        "`packages: !include_dir_named packages` directive that "
        "auto-includes the three mock YAML packages from "
        "homeassistant/packages/"
    )

    # And the three mock YAML files must exist on disk.
    for pkg_path in MOCK_PACKAGES:
        assert pkg_path.is_file(), (
            f"mock package {pkg_path.name} must exist on disk in "
            f"homeassistant/packages/ for the `!include_dir_named "
            f"packages` directive to pick it up"
        )

    # Sanity-check the package contents (each must define at least one
    # rc_* entity or one shell_command / script / automation).
    mock_track_text = MOCK_PACKAGES[0].read_text(encoding="utf-8")
    assert "shell_command" in mock_track_text
    assert "rc_mock_track_generate" in mock_track_text

    mock_trail_text = MOCK_PACKAGES[1].read_text(encoding="utf-8")
    assert "input_text" in mock_trail_text
    assert "rc_mock_location_trail" in mock_trail_text

    dev_mocks_text = MOCK_PACKAGES[2].read_text(encoding="utf-8")
    # The dev_mocks umbrella defines many input_* helpers — just
    # assert it has at least one rc_mock_* helper.
    assert "rc_mock_" in dev_mocks_text


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))