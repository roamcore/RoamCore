"""Manifest-honesty tests for connections/map-dashboard/connection.yml.

Wave 9 #110: Map basemap lock-in (OSM default). This test suite asserts
that the RoamCore map package + the connection manifest declare
OpenStreetMap as the default basemap, with the standard tile URL
`https://tile.openstreetmap.org/{z}/{x}/{y}.png`, and that the OSM
default is reachable from the bench via a real HTTP probe.

The HTTP probe is the runtime check — a stubbed unit test isn't enough
(Bernard's doctrine: 'must not fail + super intuitive + critical
infrastructure'). We hit `tile.openstreetmap.org/2/1/1.png` (a real
OSM tile coordinate) and assert HTTP 200 + `image/png` content-type +
a valid PNG payload. This is the same tile-coord pair used in the
manual verification step the catalog doc describes.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/map-dashboard/tests/ -v
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]
CONNECTION_DIR = REPO_ROOT / "connections" / "map-dashboard"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
LEGACY_DOC = REPO_ROOT / "docs" / "catalog" / "map" / "map-dashboard.md"
MAP_PACKAGE = REPO_ROOT / "homeassistant" / "packages" / "roamcore_map.yaml"

# Wave 9 #110: default basemap is OpenStreetMap standard tiles.
# This is the single source of truth — the manifest + the package +
# the recipe must all agree.
EXPECTED_OSM_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"

# Real OSM tile probe — z=2, x=1, y=1 covers a known good tile
# (a chunk of central Europe / North Africa at zoom 2). If OSM ever
# drops this tile coord pair the test fails loudly with the URL
# printed, instead of silently green-lighting a dead tile server.
OSM_PROBE_URL = "https://tile.openstreetmap.org/2/1/1.png"
OSM_PROBE_TIMEOUT_S = 15
# PNG magic bytes — first 8 bytes of every PNG file.
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def map_package_text() -> str:
    assert MAP_PACKAGE.is_file(), (
        f"required map package missing on disk: {MAP_PACKAGE} — "
        f"tier-a claims RoamCore owns the map package natively"
    )
    return MAP_PACKAGE.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Pure unit tests — fast, no network.
# ---------------------------------------------------------------------------


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must be the short connection id (`map`).

    The historical manifest id is `map` (matches the HA core `map:`
    integration domain + the legacy catalog page slug); the folder
    name is `map-dashboard` because the connection umbrella bundles
    the map + dashboard + route + trip-overlay contract surface.
    """
    assert manifest["id"] == "map", (
        f"manifest `id` must be 'map' (the historical short id); "
        f"got {manifest['id']!r}"
    )
    # Folder is the umbrella bundle.
    assert CONNECTION_DIR.name == "map-dashboard"


def test_tier_a_with_recipe_markers(manifest: dict) -> None:
    """Tier-a must advertise the recipe-over-upstream markers."""
    assert manifest["tier"] == "a"
    assert manifest["wizard"]["connection_kind"] == "recipe"
    assert manifest["wizard"]["one_tap"] is False
    # install.packages must reference the three RoamCore-owned YAML files.
    install_packages = manifest["install"]["packages"]
    expected = {
        "homeassistant/packages/roamcore_map.yaml",
        "homeassistant/packages/roamcore_map_route.yaml",
        "homeassistant/packages/roamcore_location.yaml",
    }
    assert expected.issubset(set(install_packages)), (
        f"install.packages must reference all three map YAML files; "
        f"got {install_packages!r}; missing {expected - set(install_packages)!r}"
    )


def test_default_tile_url_is_osm(manifest: dict, map_package_text: str) -> None:
    """Wave 9 #110: the default basemap MUST be OpenStreetMap.

    Both the manifest `basemap_default_and_swap.default_tile_url` and
    the package `input_text.rc_map_tile_url.initial` must equal
    `https://tile.openstreetmap.org/{z}/{x}/{y}.png`.
    """
    swap = manifest.get("basemap_default_and_swap")
    assert swap is not None, (
        "manifest must declare a `basemap_default_and_swap` block "
        "(Wave 9 #110 basemap lock-in)"
    )
    assert swap["default_tile_url"] == EXPECTED_OSM_TILE_URL, (
        f"manifest basemap_default_and_swap.default_tile_url must be "
        f"{EXPECTED_OSM_TILE_URL!r}; got {swap.get('default_tile_url')!r}"
    )
    assert swap["default_provider"] == "openstreetmap", (
        f"manifest basemap_default_and_swap.default_provider must be "
        f"'openstreetmap'; got {swap.get('default_provider')!r}"
    )
    # Attribution string is mandatory per OSM tile usage policy.
    attribution = swap.get("default_attribution", "")
    assert "OpenStreetMap" in attribution, (
        f"manifest basemap_default_and_swap.default_attribution must "
        f"reference OpenStreetMap (OSM tile usage policy); got {attribution!r}"
    )

    # The package must declare the same default.
    # Look for `initial: "https://tile.openstreetmap.org/{z}/{x}/{y}.png"`
    # under `rc_map_tile_url`. Use a simple regex anchored on the helper
    # name to avoid false positives on `rc_map_tile_url_online`.
    pattern = re.compile(
        r"rc_map_tile_url:\s*\n(?:\s+[^\n]*\n)*?\s+initial:\s*\""
        + re.escape(EXPECTED_OSM_TILE_URL) + r"\"",
        re.MULTILINE,
    )
    assert pattern.search(map_package_text), (
        f"homeassistant/packages/roamcore_map.yaml must set "
        f"`input_text.rc_map_tile_url.initial` to {EXPECTED_OSM_TILE_URL!r}; "
        f"searched the package file and did not find the expected line."
    )

    # Anti-regression: the package must NOT default to the old
    # basemaps.cartocdn.com URL (that was the previous default before
    # Wave 9 #110 switched the basemap lock-in to OSM).
    assert "basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png" not in (
        s for s in re.findall(r'initial:\s*"([^"]+)"', map_package_text)
        if "tile" in s.lower()
    ), (
        "homeassistant/packages/roamcore_map.yaml must NOT keep the old "
        "Carto CDN default in `rc_map_tile_url.initial` after Wave 9 #110"
    )


def test_stadia_swap_example_present(manifest: dict) -> None:
    """Manifest must document the one-line Stadia swap (Wave 9 #110)."""
    swap = manifest["basemap_default_and_swap"]
    examples = swap.get("swap_examples", [])
    assert isinstance(examples, list) and examples, (
        "manifest basemap_default_and_swap.swap_examples must list "
        "at least one swap (Stadia, Carto, self-hosted)"
    )
    # Find the Stadia example.
    stadia = next(
        (e for e in examples if "stadia" in e.get("url_template", "").lower()),
        None,
    )
    assert stadia is not None, (
        "manifest basemap_default_and_swap.swap_examples must include a "
        "Stadia Maps example with the "
        "'https://tiles.stadia.com/{z}/{x}/{y}@2x?api_key=YOUR_KEY' "
        "URL template"
    )
    assert "docs.stadiamaps.com" in stadia.get("signup_url", ""), (
        "Stadia swap example must link to https://docs.stadiamaps.com/"
    )
    assert "YOUR_KEY" in stadia["url_template"], (
        "Stadia URL template must clearly mark the API key placeholder "
        "as `YOUR_KEY` so the operator knows to substitute their own"
    )


def test_fallback_behavior_documented(manifest: dict) -> None:
    """Manifest must document the graceful-degradation fallback."""
    fb = manifest["basemap_default_and_swap"].get("fallback_behavior", {})
    assert fb.get("on_tile_fetch_failure") == (
        "render_gray_basemap_with_last_known_pin_and_banner"
    ), (
        "manifest basemap_default_and_swap.fallback_behavior."
        "on_tile_fetch_failure must be "
        "'render_gray_basemap_with_last_known_pin_and_banner' — "
        "Bernard doctrine: graceful degradation, not crash"
    )
    banner = fb.get("error_banner_text", "")
    assert "Map tiles unavailable" in banner, (
        f"fallback_behavior.error_banner_text must contain "
        f"'Map tiles unavailable' (plain-English error); got {banner!r}"
    )
    assert "last-known location" in banner, (
        f"fallback_behavior.error_banner_text must mention "
        f"'last-known location' so the operator knows the pin is still "
        f"visible during fallback; got {banner!r}"
    )


def test_legacy_catalog_doc_is_5_step_ikea_without_offline_claim() -> None:
    """The user-facing catalog page is now 5-step IKEA with no
    `offline-tile-cache` mentions (Bernard: not fussed about offline)."""
    assert LEGACY_DOC.is_file(), (
        f"user-facing catalog doc must exist at {LEGACY_DOC}"
    )
    text = LEGACY_DOC.read_text(encoding="utf-8")
    # 5 numbered install steps.
    numbered = re.findall(r"^\d+\.\s+\*\*", text, flags=re.MULTILINE)
    assert len(numbered) >= 5, (
        f"catalog doc must be 5-step IKEA (≥5 numbered bold-led steps); "
        f"got {len(numbered)} numbered steps"
    )
    # No "offline-tile-cache" substring (the slice dropped the feature).
    assert "offline-tile-cache" not in text.lower(), (
        "catalog doc must NOT mention 'offline-tile-cache' — "
        "Wave 9 #110 dropped the offline-tile-cache feature"
    )
    # OSM default is the headline.
    assert "tile.openstreetmap.org" in text, (
        "catalog doc must show the OSM default tile URL"
    )


def test_recipe_documents_osm_default_and_swap() -> None:
    """recipe.md must document OSM as the default + the one-line swap."""
    assert RECIPE_PATH.is_file()
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert EXPECTED_OSM_TILE_URL in text, (
        f"recipe.md must reference the OSM default tile URL "
        f"{EXPECTED_OSM_TILE_URL!r}"
    )
    assert "Stadia" in text, (
        "recipe.md must document the Stadia swap example"
    )
    assert "https://docs.stadiamaps.com/" in text, (
        "recipe.md must link to https://docs.stadiamaps.com/"
    )


# ---------------------------------------------------------------------------
# Runtime check — real HTTP probe against tile.openstreetmap.org.
# Bernard's doctrine: verification is mandatory; a stubbed unit test
# isn't enough. If this probe fails the map view's graceful fallback
# (gray basemap + last-known pin + banner) is the contract surface.
# ---------------------------------------------------------------------------


def test_osm_default_tile_is_reachable_from_bench() -> None:
    """Probe tile.openstreetmap.org and assert HTTP 200 + image/png +
    a valid PNG payload. This is the runtime check that proves the OSM
    default is reachable from the bench — if it ever starts returning
    a 403/404/5xx the test fails loudly with the URL printed.
    """
    req = urllib.request.Request(
        OSM_PROBE_URL,
        headers={
            # OSM tile usage policy asks for a meaningful User-Agent.
            # We use the RoamCore repo URL so any abuse investigator
            # can trace the request to its source.
            "User-Agent": "RoamCore-basemap-probe/1.0 (+https://github.com/roamcore/RoamCore)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=OSM_PROBE_TIMEOUT_S) as resp:
            status = resp.status
            content_type = resp.headers.get("Content-Type", "")
            body = resp.read()
    except urllib.error.HTTPError as e:
        pytest.fail(
            f"OSM default tile fetch failed: HTTP {e.code} on {OSM_PROBE_URL} — "
            f"the RoamCore map view will fall back to a gray basemap with "
            f"the 'Map tiles unavailable' banner. Check your internet "
            f"connection or the upstream OSM tile-server status."
        )
    except urllib.error.URLError as e:
        pytest.fail(
            f"OSM default tile fetch failed: URL error {e.reason} on "
            f"{OSM_PROBE_URL} — no network from bench? The RoamCore map "
            f"view will fall back to a gray basemap with the 'Map tiles "
            f"unavailable' banner."
        )

    assert status == 200, (
        f"OSM default tile must return HTTP 200; got HTTP {status} on "
        f"{OSM_PROBE_URL}"
    )
    assert "image/png" in content_type.lower(), (
        f"OSM default tile must return Content-Type: image/png; got "
        f"{content_type!r} on {OSM_PROBE_URL}"
    )
    assert body.startswith(PNG_MAGIC), (
        f"OSM default tile body must start with the PNG magic bytes "
        f"{PNG_MAGIC!r}; got first 8 bytes = {body[:8]!r} on {OSM_PROBE_URL}"
    )
    assert len(body) > 100, (
        f"OSM default tile body must be a real PNG (non-trivial size); "
        f"got {len(body)} bytes on {OSM_PROBE_URL}"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))