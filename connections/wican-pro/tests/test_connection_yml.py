"""Manifest honesty tests for the wican-pro connection.

These tests assert the `connection.yml` is honest about its tier +
requirements + scope. Mirrors the audit script's checks; the test
suite exists so a regression in the manifest catches before CI.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


@pytest.fixture(scope="module")
def manifest() -> dict:
    path = Path(__file__).resolve().parents[1] / "connection.yml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_manifest_required_fields(manifest):
    for key in ("id", "name", "tier", "category", "status", "version", "description"):
        assert manifest.get(key) is not None, f"missing required field: {key}"


def test_id_matches_folder_name(manifest):
    folder_name = Path(__file__).resolve().parents[1].name
    assert manifest["id"] == folder_name, (
        f"manifest id={manifest['id']!r} does not match folder name {folder_name!r}"
    )


def test_tier_is_a(manifest):
    """This is a tier-a native integration — RoamCore ships the custom component."""
    assert manifest["tier"] == "a", (
        "wican-pro must stay at tier-a; downgrade requires proving the slice is "
        "actually a recipe wrapping an upstream HA integration (which it isn't)"
    )


def test_category_is_connectivity(manifest):
    assert manifest["category"] == "connectivity"


def test_tier_a_means_native_custom_component(manifest):
    """Tier-a connections must declare the custom component path."""
    assert "install" in manifest
    assert manifest["install"]["ha_integration_domain"] == "roamcore_wican"
    assert manifest["install"]["config_flow"] is True


def test_custom_references_point_at_real_files(manifest):
    repo_root = Path(__file__).resolve().parents[3]
    for ref in manifest.get("links", {}).get("custom_references", []):
        full = repo_root / ref
        assert full.is_file(), f"custom reference {ref!r} does not exist at {full}"


def test_cross_references_point_at_real_dirs(manifest):
    conn_root = Path(__file__).resolve().parents[1]  # wican-pro/ directory
    for ref in manifest.get("links", {}).get("cross_references", []):
        full = (conn_root / ref).resolve()
        assert full.is_dir(), f"cross reference {ref!r} does not exist at {full}"


def test_no_vendor_names_in_dashboard_tiles(manifest):
    """The naming rule forbids vendor names in any rc_obd_* entity id."""
    forbidden = {"wican", "custic", "elm327", "obdlink", "viecar"}
    for tile in manifest["dashboard"]["tiles"]:
        for word in forbidden:
            assert word not in tile.lower(), f"tile {tile!r} contains vendor name {word!r}"


def test_dashboard_tiles_use_rc_obd_prefix(manifest):
    for tile in manifest["dashboard"]["tiles"]:
        assert "rc_obd_" in tile, f"tile {tile!r} does not use rc_obd_ prefix"


def test_openclaw_queries_no_vendor_names(manifest):
    forbidden = {"wican", "custic", "elm327"}
    for q in manifest.get("openclaw", {}).get("queries", []):
        for word in forbidden:
            assert word not in q.lower(), f"query {q!r} contains vendor name {word!r}"


def test_openclaw_summary_keys_use_obd_prefix(manifest):
    for key in manifest.get("openclaw", {}).get("summary_keys", []):
        assert key.startswith("obd_"), f"summary_key {key!r} should start with obd_"


def test_tests_match_actual_test_files(manifest):
    conn_root = Path(__file__).resolve().parents[1]  # wican-pro/ directory
    for t in manifest.get("tests", []):
        full = (conn_root / t).resolve()
        assert full.is_file(), f"declared test {t!r} does not exist at {full}"


def test_tier_warnings_acknowledged(manifest):
    """Tier-a connections should declare the bench-test gap honestly."""
    warnings = manifest.get("tier_warnings", [])
    assert any("pytest" in w.lower() for w in warnings), (
        "tier-a connections should disclose the absence of pytest integration tests"
    )


def test_one_tap_and_auto_discover(manifest):
    """The wizard must declare one-tap + auto-discover for plug-and-play."""
    wiz = manifest.get("wizard", {})
    assert wiz.get("one_tap") is True
    assert wiz.get("auto_discover") is True
