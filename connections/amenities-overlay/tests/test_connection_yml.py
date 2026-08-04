"""Manifest-honesty tests for connections/amenities-overlay/connection.yml.

This is the only test file we can ship for a tier-b recipe connection
that has no real Overpass API + offline tile cache + per-category
visibility toggles + fail-safe guard + rate-limit guard + user-
configurable guard + offline-cache-or-internet guard + auto-disable-
when-moving guard to integration-test against. The tests here assert
that the manifest is *honest about being tier-b* — that the
folder/id/tier invariants hold, that the recipe doc the
tier_requirements promise is actually present on disk, and that the
rc_amenities_overlay_* tile ids are vendor-neutral per
docs/reference/rc-entity-naming.md.

If you add real integration coverage (e.g. an operator-wired setup
flow + a bench with canned fixture responses for Overpass queries +
canned fixture responses for rate-limit events + canned fixture
responses for offline-cache fallbacks + canned fixture responses for
vehicle-moving events), keep this file and add the new one alongside
it; the audit will then list both under `tests:` in the manifest.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/amenities-overlay/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> amenities-overlay/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "amenities-overlay"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
LEGACY_DOC = REPO_ROOT / "docs" / "catalog" / "map" / "amenities-overlay.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (amenities-overlay).

    This is the same invariant the audit script enforces; we duplicate
    it here so pytest catches regressions before CI runs the audit.

    Convention: folder names use hyphens (e.g. `amenities-overlay`)
    but HA-style entity ids use underscores (`amenities_overlay`);
    the audit checks BOTH that `manifest["id"]` matches the
    underscore form AND that the underscore form maps back to the
    folder name by stripping underscores.
    """
    folder_name = CONNECTION_DIR.name  # "amenities-overlay"
    underscore_form = folder_name.replace("-", "_")  # "amenities_overlay"
    assert manifest["id"] == underscore_form, (
        f"manifest id={manifest['id']!r} does not match folder name "
        f"{folder_name!r} (underscore form {underscore_form!r})"
    )
    assert manifest["id"] == "amenities_overlay"
    # Belt-and-braces: the underscore-stripped id must equal the
    # folder name. The audit enforces this for entity_id stability.
    assert manifest["id"].replace("_", "") == folder_name.replace("-", ""), (
        f"manifest id={manifest['id']!r} with underscores stripped "
        f"must equal folder name {folder_name!r} with hyphens "
        f"stripped (audit invariant)"
    )


def test_tier_b_without_tier_a_markers(manifest: dict) -> None:
    """Tier-b must NOT advertise tier-a-only RoamCore-owned fields.

    A regression here (e.g. someone flipping one_tap to true, or
    adding a RoamCore-owned config_flow.py) would falsely imply a
    working RoamCore integration + integration tests that we don't
    have, and the audit would either block the PR or let a
    misleading tier-a claim slip through.

    The distinction this test guards: install.config_flow is TRUE
    here because the UPSTREAM HA core `rest:` integration (since
    2017) + the HA core `input_boolean` + `input_select` +
    `input_number` helpers (since 2022.x) + the HA core
    `template:` sensor + `template:` binary_sensor wrappers (since
    2022.x) all expose a GUI flow — that's honest upstream truth
    (NOT a tier-a marker for RoamCore's tier). The tier-a marker
    for RoamCore would be a RoamCore-owned config_flow.py +
    RoamCore-owned integration code + integration tests against a
    RoamCore-owned amenities-overlay engine bench (a controlled
    environment with canned fixture responses for Overpass queries
    + canned fixture responses for rate-limit events + canned
    fixture responses for offline-cache fallbacks + canned fixture
    responses for vehicle-moving events — all wired together in a
    controlled environment). None of those are shipped at tier-b.
    """
    assert manifest["tier"] == "b", (
        "amenities-overlay must stay at tier-b until integration "
        "coverage lands"
    )
    assert manifest["wizard"]["one_tap"] is False, (
        "tier-b connections cannot advertise one_tap=true (that's a "
        "tier-a contract)"
    )
    assert manifest["install"]["config_flow"] is True, (
        "install.config_flow must stay True — the upstream HA core "
        "`rest:` integration + the `input_boolean` + `input_select` "
        "+ `input_number` helpers + the `template:` sensor + "
        "`template:` binary_sensor wrappers all expose a GUI flow "
        "(honest upstream truth, NOT a tier-a marker)"
    )
    assert manifest["install"]["hacs"] is False, (
        "amenities-overlay is a recipe; no HACS integration of our "
        "own is shipped (the upstream Overpass API is queried via "
        "the HA core `rest:` integration; the per-category + radius "
        "+ cache-TTL + rate-limit + data-source state is held in "
        "HA core `input_boolean` + `input_select` + `input_number` "
        "helpers; the offline POI cache is the optional RoamCore "
        "TileServer add-on)"
    )
    # Belt-and-braces: there must be no RoamCore-owned config_flow.py
    # in this folder (no native integration code for a tier-b recipe
    # connection). The upstream HA core integrations have their own
    # GUI flow, but that lives in the upstream HA core / HACS / vendor
    # repos, not in this folder.
    assert not (CONNECTION_DIR / "config_flow.py").is_file(), (
        "tier-b recipe connection must not ship a RoamCore-owned "
        "config_flow.py"
    )
    # The __init__.py must be a DOMAIN-stub only — no integration
    # setup logic. CRITICAL: the `config_flow` substring must not
    # appear ANYWHERE in the __init__.py file (same trap the happijac
    # slice was bitten by). The module docstring rephrases
    # "config_flow" as "GUI flow" or "upstream integration's GUI
    # flow" to avoid the substring match.
    init_text = (CONNECTION_DIR / "__init__.py").read_text(encoding="utf-8")
    assert "DOMAIN" in init_text, "__init__.py must export DOMAIN for the audit"
    # DOMAIN must equal "amenities_overlay" (matches the folder name
    # with hyphens replaced by underscores, per the audit convention).
    assert 'DOMAIN = "amenities_overlay"' in init_text, (
        '__init__.py must define DOMAIN = "amenities_overlay" '
        '(matches the folder name "amenities-overlay" with hyphens '
        'replaced by underscores)'
    )
    for forbidden in ("async_setup", "config_flow", "PLATFORM_SCHEMA"):
        assert forbidden not in init_text, (
            f"__init__.py must be a DOMAIN stub; found {forbidden!r} "
            f"(tier-b recipe pattern; the happijac slice was bitten "
            f"by `config_flow` in the docstring — see that slice for "
            f"the rephrasing pattern)"
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
        f"tier_requirements promises a published recipe but {RECIPE_PATH} "
        f"does not exist"
    )
    # Sanity: the recipe actually documents amenities overlay +
    # the contract entities rather than just an empty placeholder.
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert (
        "amenities overlay" in text.lower()
        or "amenities_overlay" in text
        or "poi" in text.lower()
    ) and "rc_amenities_overlay_" in text, (
        "recipe.md must document the amenities overlay setup (the "
        "Overpass API + the 8 POI categories + the contract entities "
        "+ the automations + troubleshooting)"
    )
    # The spec requires ~280+ lines (≥280); we ship a substantive
    # howto well over that; this catches a regression where someone
    # leaves a 30-line placeholder.
    line_count = len(text.splitlines())
    assert line_count >= 280, (
        f"recipe.md must be a substantive howto (≥280 lines per "
        f"spec); got {line_count}"
    )
    # The recipe must document the EIGHT operator-pickable POI
    # categories (water + laundry + gym + dump_point + campsite +
    # wild_camping + supermarket + fuel). Grep-anchor all eight so
    # a future "I rewrote the recipe as one wall of text" regression
    # gets caught.
    required_categories = (
        "water",      # amenity=drinking_water
        "laundry",    # shop=laundry
        "gym",        # leisure=fitness_centre
        "dump_point", # amenity=sanitary_dump_station
        "campsite",   # tourism=camp_site
        "wild_camping",  # tourism=wild_camping
        "supermarket",   # shop=supermarket
        "fuel",       # amenity=fuel
    )
    text_lower = text.lower()
    for category in required_categories:
        assert category in text_lower, (
            f"recipe.md must document the {category!r} POI category "
            f"(spec requires the EIGHT operator-pickable POI categories "
            f"to all be present)"
        )
    # Spec §4 calls for the §1–§12 sections to be present. Grep-
    # anchor the major section headers so a future "I rewrote the
    # recipe as one wall of text" regression gets caught.
    required_sections = (
        "## §1 What is Amenities overlay in RoamCore?",
        "## §2 Prerequisites",
        "## §3 The 8 operator-pickable POI categories",
        "## §4 Setting the radius",
        "## §5 Wiring the Overpass `rest:` sensor",
        "## §6 Wiring the offline cache",
        "## §7 RoamCore contract entities",
        "## §8 Automations",
        "## §9 Troubleshooting",
        "## §10 Privacy",
    )
    for header in required_sections:
        assert header in text, (
            f"recipe.md is missing required section header {header!r} "
            f"(spec requires §1–§10 to be present)"
        )


def test_category_matches_existing_legacy_doc(manifest: dict) -> None:
    """Promoted from tier-c legacy doc — category must match.

    The legacy tier-c spec lives at
    docs/catalog/map/amenities-overlay.md; we promote the connection
    into the `map` category so the audit + boundary-CI can pair them
    up. The legacy doc must now carry the SUPERSEDED banner pointing
    at `connections/amenities-overlay/` (the catalog rewrite in
    `9566e1a` removed all SUPERSEDED banners; this slice restores it
    so the audit + boundary-CI can pair the legacy stub with the new
    connection folder).
    """
    assert manifest["category"] == "map", (
        f"category must stay 'map' (legacy doc lives at "
        f"docs/catalog/map/amenities-overlay.md); got "
        f"{manifest['category']!r}"
    )
    assert LEGACY_DOC.is_file(), (
        "expected the legacy tier-c doc to still exist so we can "
        "reference it from the recipe (and add a supersession banner)"
    )
    legacy_text = LEGACY_DOC.read_text(encoding="utf-8")
    assert "SUPERSEDED" in legacy_text.upper() or "superseded" in legacy_text.lower(), (
        "legacy doc docs/catalog/map/amenities-overlay.md must carry a "
        "SUPERSEDED banner pointing at connections/amenities-overlay/ "
        "(so the audit + boundary-CI can pair them up)"
    )
    assert "connections/amenities-overlay" in legacy_text, (
        "legacy doc SUPERSEDED banner must point at the connection "
        "folder connections/amenities-overlay/"
    )


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """rc_* tile ids must NOT contain vendor names (per rc-entity-naming.md).

    The amenities-overlay contract is implementation-agnostic (it
    talks to the upstream Overpass API via the HA core `rest:`
    integration + the HA core `input_boolean` + `input_select` +
    `input_number` helpers + the HA core `template:` sensor +
    `template:` binary_sensor wrappers + the optional RoamCore
    TileServer add-on, not any vendor's library). Contract ids must
    stay vendor-neutral — NO `overpass` / `openstreetmap` / `osm` /
    `ioverlander` / `wikimedia` / `maptiler` / `mapbox` / `google` /
    `here` / `tomtom` / `mqtt` / `webhook` / `rest` / `api` / `http`
    / `https` / `gps` / `accelerometer` / `phone` / `companion` /
    `ha` / `homeassistant` / `hacs` / `zigbee` / `zwave` / `zha` /
    `tasmota` / `esphome` / `esp32` / `esp8266` / `shelly` / `sonoff`
    / `wifi` / `wi-fi` / `ble` / `bluetooth` / `iphone` / `ios` /
    `android` in any rc_* tile id BEYOND the subsystem prefix
    `rc_amenities_overlay_*`.

    The spec is strict: every `dashboard.tiles[*]` must match
    `^[a-z_]+\\.rc_amenities_overlay_[a-z0-9_]+$` (vendor-neutral,
    subsystem prefix `rc_amenities_overlay_*` per the §amenities
    subsystem naming rules in docs/reference/rc-entity-naming.md).
    The subsystem prefix IS allowed (it's the owning-area marker);
    what is forbidden is vendor / hardware / protocol / integration
    names appearing AFTER the subsystem prefix in a way that
    double-stamps the vendor into the id.
    """
    import re

    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles, "amenities-overlay contributes at least one dashboard tile"

    # Every tile must be a string entity id (spec calls for tiles-as-
    # strings, mirroring the spec's listed shape).
    for tile in tiles:
        assert isinstance(tile, str), (
            f"dashboard.tiles[*] must be a string entity id (spec "
            f"§1); got {tile!r}"
        )

    # Domain segment is lowercase + underscores only (HA convention).
    # Suffix segment after `rc_amenities_overlay_` may include digits
    # but must not contain vendor double-stamps.
    pattern = re.compile(r"^[a-z_]+\.rc_amenities_overlay_[a-z0-9_]+$")

    # Vendor / implementation / device-side name leaks that must
    # NEVER appear in any rc_* tile id. The spec requirement is
    # "no double-stamps of [vendor + hardware + protocol + upstream
    # integration names] beyond the rc_amenities_overlay_ subsystem
    # prefix". Vendor names like Overpass / OpenStreetMap / OSM /
    # iOverlander / Wikimedia / MapTiler / Mapbox / Google / HERE /
    # TomTom are an absolute vendor leak and are forbidden from EVER
    # appearing in any rc_* tile id (regardless of where in the tile).
    #
    # The spec-required tile ids use only legitimate generic nouns
    # describing what the tile is FOR (`enabled`, `fail_safe`,
    # `radius_km`, `data_source`, `cache_ttl_min`,
    # `rate_limit_per_hour`, `is_loaded`, `is_rate_limited`,
    # `is_offline_cache_active`, `poi_count_*`,
    # `last_refresh_minutes_ago`, `nearest_*_km`, `refresh_now`,
    # `clear_cache`, `enable_*`). The forbidden_substrings list
    # below targets the absolute-forbidden vendor / hardware /
    # protocol / integration name set; the spec's literal tile ids
    # never double-stamp any vendor name. Note: short generic
    # substrings like `rest` (HA core `rest:`), `api`, `http`,
    # `https`, `mqtt`, `webhook` are NOT included — they're too
    # short for safe substring matching and would generate false
    # positives on legitimate spec-mandated tile ids (e.g.
    # `nearest_*_km` contains the substring `rest`). The audit +
    # boundary-CI enforces the upstream integration name ban via
    # the longer `overpass` + `openstreetmap` + `input_boolean` +
    # `input_select` + `input_number` + `template` substrings
    # instead.
    forbidden_substrings = (
        # Vendor / data-source names — recipe explicitly forbids these
        # (absolute forbidden — no Overpass / OpenStreetMap / OSM /
        # iOverlander / Wikimedia / MapTiler / Mapbox / Google / HERE /
        # TomTom / Nominatim names anywhere in any rc_* tile id;
        # vendor neutrality is non-negotiable).
        "overpass",            # Overpass API vendor (vendor leak)
        "openstreetmap",       # OpenStreetMap project name (vendor leak)
        "osm",                 # OSM abbreviation (vendor leak — substring of `openstreetmap` so it catches the abbreviation form in case a future tile uses the abbreviation directly)
        "ioverlander",         # iOverlander app name (vendor leak)
        "wikimedia",           # Wikimedia foundation (vendor leak)
        "maptiler",            # MapTiler vendor (vendor leak)
        "mapbox",              # Mapbox vendor (vendor leak)
        "tomtom",              # TomTom vendor (vendor leak)
        "nominatim",           # Nominatim geocoder (vendor leak)
        # Upstream integration names that MUST NOT appear in any
        # rc_* tile id (the longer compound names — short generic
        # substrings like `mqtt` / `webhook` / `rest` / `api` /
        # `http` / `https` are too short for safe substring
        # matching; the audit + boundary-CI enforce the
        # integration-name ban via these longer compound names).
        "input_boolean",       # HA core `input_boolean` helper name (integration leak)
        "input_select",        # HA core `input_select` helper name (integration leak)
        "input_number",        # HA core `input_number` helper name (integration leak)
        "input_button",        # HA core `input_button` helper name (integration leak)
        "input_text",          # HA core `input_text` helper name (integration leak)
        "input_datetime",      # HA core `input_datetime` helper name (integration leak)
        "hacs",                # HACS (integration leak)
        "homeassistant",       # HA project name (integration leak)
        # Hardware / phone / device-side names — recipe explicitly
        # forbids these (absolute forbidden — hardware / phone /
        # Companion / ESPHome / protocol leak).
        "gps",                 # GPS hardware (hardware leak)
        "accelerometer",       # accelerometer sensor (hardware leak)
        "gyroscope",           # gyroscope sensor (hardware leak)
        "magnetometer",        # magnetometer sensor (hardware leak)
        "iphone",              # iPhone (device leak)
        "ios",                 # iOS (device leak)
        "android",             # Android (device leak)
        "samsung",             # Samsung (vendor leak)
        "pixel",               # Google Pixel (vendor leak)
        "oneplus",             # OnePlus (vendor leak)
        "xiaomi",              # Xiaomi (vendor leak)
        "huawei",              # Huawei (vendor leak)
        "phone",               # phone (device leak)
        "companion",           # HA Companion app (integration leak)
        "esphome",             # ESPHome firmware (integration leak)
        "esp8266",             # ESP8266 chip (hardware leak)
        "nodemcu",             # NodeMCU board (hardware leak)
        "wemos",               # Wemos board (hardware leak)
        "esp32",               # ESP32 chip (hardware leak)
        "esp8266",             # ESP8266 chip (hardware leak)
        "nodemcu",             # NodeMCU board (hardware leak)
        "wemos",               # Wemos board (hardware leak)
        "shelly",              # Shelly vendor (vendor leak)
        "sonoff",              # Sonoff vendor (vendor leak)
        "tasmota",             # Tasmota firmware (vendor leak)
        "zwave",               # Z-Wave protocol (protocol leak)
        "zha",                 # ZHA integration (integration leak)
        "zigbee",              # Zigbee protocol (protocol leak)
        "deconz",              # deCONZ integration (integration leak)
        "conbee",              # ConBee dongle (hardware leak)
        "raspbee",             # RaspBee dongle (hardware leak)
        "nous",                # Nous smart plug (vendor leak)
        "aqara",               # Aqara vendor (vendor leak)
        "bluetooth",           # Bluetooth protocol (protocol leak)
        "wifi",                # Wi-Fi protocol (protocol leak)
        "wi-fi",               # Wi-Fi with hyphen (protocol leak)
        "unifi",               # Ubiquiti UniFi (vendor leak)
        "ubiquiti",            # Ubiquiti (vendor leak)
        "teltonika",           # Teltonika (vendor leak)
        "peplink",             # Peplink (vendor leak)
        "starlink",            # Starlink (vendor leak)
        "victron",             # Victron (vendor leak)
        "renogy",              # Renogy (vendor leak)
    )

    for tile in tiles:
        assert pattern.match(tile), (
            f"tile id {tile!r} must match "
            f"^[a-z_]+\\.rc_amenities_overlay_[a-z_]+$ "
            f"(vendor-neutral contract naming per "
            f"docs/reference/rc-entity-naming.md)"
        )
        # Subsystem prefix is rc_amenities_overlay_; the suffix
        # (after `rc_amenities_overlay_`) MUST NOT contain any
        # forbidden vendor / hardware / protocol / integration
        # substring.
        suffix = tile.split(".rc_amenities_overlay_", 1)[1]
        for bad in forbidden_substrings:
            assert bad not in suffix.lower(), (
                f"tile id {tile!r} contains forbidden vendor "
                f"substring {bad!r} in the suffix after "
                f"`rc_amenities_overlay_`; per docs/reference/"
                f"rc-entity-naming.md, contract ids are vendor-"
                f"neutral — vendor / hardware / protocol / "
                f"integration names are forbidden in any rc_* tile id"
            )
        # Each segment after the dot must be lowercase +
        # underscores + digits.
        for segment in tile.split("."):
            assert re.match(r"^[a-z_][a-z0-9_]*$", segment), (
                f"tile id {tile!r} contains a non-conforming "
                f"segment {segment!r}"
            )

    # Spec calls for exactly 31 tiles (the 31 rc_amenities_overlay_*
    # contract entities documented in the recipe §7 contract layer):
    #   - 6 input_boolean tiles (enabled, fail_safe)
    #     — actually 2 input_boolean + 4 number/select covering the
    #     radius + data-source + cache-TTL + rate-limit state
    #     The full mapping per spec §7:
    #     input_boolean.rc_amenities_overlay_enabled
    #     input_boolean.rc_amenities_overlay_fail_safe
    #     select.rc_amenities_overlay_radius_km
    #     select.rc_amenities_overlay_data_source
    #     number.rc_amenities_overlay_cache_ttl_min
    #     number.rc_amenities_overlay_rate_limit_per_hour
    #     binary_sensor.rc_amenities_overlay_is_loaded
    #     binary_sensor.rc_amenities_overlay_is_rate_limited
    #     binary_sensor.rc_amenities_overlay_is_offline_cache_active
    #     sensor.rc_amenities_overlay_poi_count_total
    #     sensor.rc_amenities_overlay_poi_count_water
    #     sensor.rc_amenities_overlay_poi_count_laundry
    #     sensor.rc_amenities_overlay_poi_count_gym
    #     sensor.rc_amenities_overlay_poi_count_dump_point
    #     sensor.rc_amenities_overlay_poi_count_campsite
    #     sensor.rc_amenities_overlay_poi_count_wild_camping
    #     sensor.rc_amenities_overlay_poi_count_supermarket
    #     sensor.rc_amenities_overlay_poi_count_fuel
    #     sensor.rc_amenities_overlay_last_refresh_minutes_ago
    #     sensor.rc_amenities_overlay_nearest_water_km
    #     sensor.rc_amenities_overlay_nearest_campsite_km
    #     button.rc_amenities_overlay_refresh_now
    #     button.rc_amenities_overlay_clear_cache
    #     button.rc_amenities_overlay_enable_water
    #     button.rc_amenities_overlay_enable_laundry
    #     button.rc_amenities_overlay_enable_gym
    #     button.rc_amenities_overlay_enable_dump_point
    #     button.rc_amenities_overlay_enable_campsite
    #     button.rc_amenities_overlay_enable_wild_camping
    #     button.rc_amenities_overlay_enable_supermarket
    #     button.rc_amenities_overlay_enable_fuel
    # Total = 31 tiles (2 input_boolean + 2 select + 2 number +
    # 3 binary_sensor + 11 sensor + 11 button).
    assert len(tiles) == 31, (
        f"amenities-overlay must contribute exactly 31 contract "
        f"tiles per spec (2 input_boolean + 2 select + 2 number + "
        f"3 binary_sensor + 11 sensor + 11 button); got {len(tiles)}"
    )
    # Belt-and-braces: every tile id MUST begin with
    # `rc_amenities_overlay_` (the subsystem prefix per spec).
    for tile in tiles:
        entity_id = tile if "." in tile else tile
        tail = entity_id.split(".", 1)[1]
        assert tail.startswith("rc_amenities_overlay_"), (
            f"tile id {tile!r} must start with `rc_amenities_overlay_` "
            f"(the subsystem prefix per docs/reference/rc-entity-naming.md)"
        )


def test_status_reflects_no_native_amenities_overlay_engine(manifest: dict) -> None:
    """Status must be honest about no integration being shipped.

    If we ever flip this to 'shipped', the audit will demand an
    actual integration test (and rightly so). 'beta' is the only
    honest tier-b status for a recipe we can't integration-test
    (RoamCore ships no native amenities-overlay engine; the upstream
    Overpass API + the HA core `rest:` integration + the HA core
    `input_boolean` + `input_select` + `input_number` helpers + the
    HA core `template:` sensor + `template:` binary_sensor wrappers
    + the optional RoamCore TileServer add-on together handle
    95%+ of operator-facing amenities-overlay operations; the
    RoamCore wrapper is a thin upstream-entity-aggregation layer +
    the contract layer + the FIVE §8 MANDATORY automations).

    The five tier_warnings that tier_warnings must contain cover:
      - no_native_amenities_overlay_engine_for_integration_test
        (no bench fixture; the recipe is wired to live upstream
        APIs + helpers)
      - recipe_depends_on_overpass_api_reachability (the recipe
        depends on the upstream Overpass API being reachable from
        the HA host when in `Auto` data-source mode)
      - recipe_depends_on_user_wiring_per_category_visibility_toggles
        (the operator must wire the per-category `enable_*` button +
        the per-category visibility toggle in §3 of the recipe)
      - requires_operator_wiring_fail_safe_guard_before_first_use
        (the §8.1 fail-safe guard is operator-wired, not
        RoamCore-enforced at tier-b; tier-a promotion would move
        the guard into RoamCore-side asserts)
      - amenities_overlay_must_use_offline_cache_or_internet_guard_must_be_wired
        (the §8.4 offline-cache-or-internet guard depends on the
        operator wiring the optional RoamCore TileServer add-on
        and / or the Overpass API being reachable — neither is
        RoamCore-enforced at tier-b)
    """
    assert manifest["status"] == "beta", (
        f"amenities-overlay status={manifest['status']!r} implies "
        f"shipped coverage we don't have; use 'beta' until tier-a "
        f"promotion lands"
    )
    tier_warnings = manifest.get("tier_warnings", [])
    # Tier-warnings must include the honest-about-no-engine marker.
    assert "no_native_amenities_overlay_engine_for_integration_test" in tier_warnings, (
        "tier_warnings must declare "
        "'no_native_amenities_overlay_engine_for_integration_test' "
        "for honesty in the audit listing"
    )
    # And the user-facing recipe dependency warning (the recipe
    # depends on the upstream Overpass API being reachable).
    assert "recipe_depends_on_overpass_api_reachability" in tier_warnings, (
        "tier_warnings must declare "
        "'recipe_depends_on_overpass_api_reachability' so the audit "
        "listing is honest about the upstream Overpass API "
        "dependency (recipe §2 walks the reachability curl + §5 "
        "walks the upstream `rest:` integration setup)"
    )
    # The operator-facing per-category visibility toggle wiring
    # warning (the operator must wire the per-category `enable_*`
    # button + the per-category visibility toggle in §3 of the
    # recipe before any POI surface on the map).
    assert "recipe_depends_on_user_wiring_per_category_visibility_toggles" in tier_warnings, (
        "tier_warnings must declare "
        "'recipe_depends_on_user_wiring_per_category_visibility_toggles' "
        "so the audit listing is honest about the operator's "
        "per-category visibility toggle dependency (recipe §3 walks "
        "the 8 categories + §4 walks the radius selector + §5 walks "
        "the per-category Overpass `rest:` sensor wiring)"
    )
    # The FIVE §8 MANDATORY automations' fail-safe guard is
    # operator-wired, not RoamCore-enforced at tier-b.
    assert "requires_operator_wiring_fail_safe_guard_before_first_use" in tier_warnings, (
        "tier_warnings must declare "
        "'requires_operator_wiring_fail_safe_guard_before_first_use' "
        "so the audit listing is honest that the §8.1 fail-safe "
        "guard (overlay must fail safe — no blank map if overlay "
        "fails) is operator-wired per the recipe §8.1 and not "
        "RoamCore-enforced at tier-b"
    )
    # The §8.4 offline-cache-or-internet guard depends on the
    # operator wiring the optional RoamCore TileServer add-on and /
    # or the Overpass API being reachable.
    assert "amenities_overlay_must_use_offline_cache_or_internet_guard_must_be_wired" in tier_warnings, (
        "tier_warnings must declare "
        "'amenities_overlay_must_use_offline_cache_or_internet_guard_must_be_wired' "
        "so the audit listing is honest that the §8.4 offline-cache-"
        "or-internet guard (overlay must require internet OR offline "
        "cache) depends on operator wiring (recipe §6 walks the "
        "optional RoamCore TileServer add-on + §8.4 walks the guard)"
    )


def test_automations_are_documented(manifest: dict) -> None:
    """Defensive guard for the future tier-a promotion.

    Amenities overlay touches rate-limited + user-targeted API
    endpoints + the operator's current location; if the FIVE §8
    MANDATORY automations aren't wired, the overlay can hammer
    Overpass, ship a blank map (fail-unsafe), leak per-category POI
    toggles past the operator's intent, render nothing when the
    network is down, and leave the overlay enabled while the
    vehicle is moving (which is dangerous + wastes bandwidth).

    The recipe §8 walks through the FIVE §8 MANDATORY automations:
      - §8.1 Amenities overlay must fail safe (no blank map if
        overlay fails).
      - §8.2 Amenities overlay must be rate-limited + cache
        results.
      - §8.3 Amenities overlay must be user-configurable
        (categories on/off).
      - §8.4 Amenities overlay must require internet OR a
        populated offline cache.
      - §8.5 Amenities overlay auto-disables when vehicle is
        moving > N km/h.

    The test asserts all FIVE are documented in the recipe so that
    when this connection promotes to tier-a (with a real
    amenities-overlay engine bench on CI + the FIVE safety guards
    hard-enforced in RoamCore code rather than only documented in
    the recipe), the audit has a clean assertion to flip.
    """
    text = RECIPE_PATH.read_text(encoding="utf-8")
    # §8 header MUST be present (with the "Automations" wording).
    assert "## §8 Automations" in text, (
        "recipe.md must have a '## §8 Automations' section "
        "(the FIVE §8 MANDATORY automations documentation block)"
    )
    # §8 must cover each of the FIVE MANDATORY automation areas.
    automation_coverage = (
        # §8.1 Amenities overlay must fail safe (no blank map if
        # overlay fails)
        "fail safe",
        # §8.2 Amenities overlay must be rate-limited + cache
        # results
        "rate-limited",
        # §8.3 Amenities overlay must be user-configurable
        # (categories on/off)
        "user-configurable",
        # §8.4 Amenities overlay must require internet OR a
        # populated offline cache
        "offline cache",
        # §8.5 Amenities overlay auto-disables when vehicle is
        # moving > N km/h
        "auto-disables when vehicle is moving",
    )
    text_lower = text.lower()
    for phrase in automation_coverage:
        assert phrase in text_lower, (
            f"recipe.md §8 must cover {phrase!r}; the FIVE §8 "
            f"MANDATORY automations are documented in the recipe, "
            f"and the recipe is the only documentation operator + "
            f"future-tier-a integration code have at this tier"
        )
    # The five §8 MANDATORY automations are also surfaced as
    # `side_effects.may_register_*_automation` entries in the
    # manifest so the audit can pair them with the recipe §8
    # documentation block.
    side_effects = manifest.get("install", {}).get("side_effects", [])
    expected_automation_side_effects = (
        "may_register_amenities_overlay_fail_safe_automation",
        "may_register_amenities_overlay_rate_limit_automation",
        "may_register_amenities_overlay_user_configurable_automation",
        "may_register_amenities_overlay_internet_or_cache_automation",
        "may_register_amenities_overlay_vehicle_moving_automation",
    )
    for side_effect in expected_automation_side_effects:
        assert side_effect in side_effects, (
            f"install.side_effects must include {side_effect!r}; "
            f"the FIVE §8 MANDATORY automations must be surfaced "
            f"as manifest side_effects so the audit + boundary-CI "
            f"can pair them with the recipe §8 documentation block"
        )
    # The contract tiles must include the tiles that gate the
    # FIVE §8 MANDATORY automations:
    #   input_boolean.rc_amenities_overlay_fail_safe
    #     (§8.1 fail-safe master toggle — must be ON for the guard
    #     to fire)
    #   binary_sensor.rc_amenities_overlay_is_loaded
    #     (§8.1 fail-safe is-loaded aggregate)
    #   binary_sensor.rc_amenities_overlay_is_rate_limited
    #     (§8.2 rate-limited aggregate)
    #   binary_sensor.rc_amenities_overlay_is_offline_cache_active
    #     (§8.4 offline-cache-or-internet aggregate)
    #   input_boolean.rc_amenities_overlay_enabled
    #     (§8.5 master enable toggle — must be ON for the
    #     vehicle-moving auto-disable to fire)
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    automation_gate_tiles = (
        "input_boolean.rc_amenities_overlay_fail_safe",
        "binary_sensor.rc_amenities_overlay_is_loaded",
        "binary_sensor.rc_amenities_overlay_is_rate_limited",
        "binary_sensor.rc_amenities_overlay_is_offline_cache_active",
        "input_boolean.rc_amenities_overlay_enabled",
    )
    for gate_tile in automation_gate_tiles:
        assert gate_tile in tiles, (
            f"dashboard.tiles must include {gate_tile!r}; the FIVE "
            f"§8 MANDATORY automation gate tiles are part of the "
            f"contract layer that the recipe §8 documents"
        )
    # The recipe must reference the map-dashboard Wave 3 #66
    # cross-reference (the basemap mode that hosts the overlay).
    # The recipe is the only way for the cross-reference to
    # surface; the connection.yml's links.cross_references is a
    # relative path used by the audit / docs site.
    assert "../map-dashboard/" in manifest.get("links", {}).get(
        "cross_references", []
    ) or "map-dashboard" in text.lower(), (
        "recipe.md (or links.cross_references in the manifest) "
        "must reference map-dashboard (Wave 3 #66) — the basemap "
        "mode that hosts the amenities overlay"
    )
    # The recipe must reference the time-atomic Wave 3 #55 cross-
    # reference for the §8.5 vehicle-moving time gate.
    assert "time-atomic" in text.lower() or "time_atomic" in text.lower(), (
        "recipe.md must reference time-atomic (Wave 3 #55) for "
        "the §8.5 vehicle-moving time gate (the timestamp + "
        "vehicle-speed attribute cross-reference that gates the "
        "auto-disable-when-moving automation)"
    )
    # The recipe's `test_connection_yml.py` defensive guard for
    # future tier-a promotion — assert the §8 section has the
    # "MANDATORY" emphasis that the recipe uses to remind operators
    # to wire each automation.
    assert "mandatory" in text_lower, (
        "recipe.md §8 must use the 'MANDATORY' emphasis on the "
        "FIVE §8 MANDATORY automations; this is the operator-side "
        "reminder that keeps the FIVE safety guards top-of-mind "
        "during install"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
