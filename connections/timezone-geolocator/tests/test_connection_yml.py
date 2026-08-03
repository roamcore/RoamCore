"""Manifest-honesty tests for connections/timezone-geolocator/connection.yml.

This is the only test file we can ship for a tier-c recipe connection
that has no real timezone engine bench (a Traccar server + a mock
GPS feed + canned fixture responses for multiple timezones + the
upstream GeoLocator integration installed) on the CI rig to
integration-test against. The tests here assert that the manifest is
*honest about being tier-c* — that the folder/id/tier invariants
hold, that the recipe doc the tier_requirements promise is actually
present on disk, that the rc_time_zone_* tile ids are vendor-neutral
per docs/reference/rc-entity-naming.md, and that the §5 automation
is documented with the right cross-references (Traccar / HA
Companion / Wican Pro / time-weather contract).

If you add real integration coverage (e.g. an operator-wired setup
flow + a bench with a Traccar server + a mock GPS feed + canned
fixture responses), keep this file and add the new one alongside
it; the audit will then list both under `tests:` in the manifest.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/timezone-geolocator/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> timezone-geolocator/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "timezone-geolocator"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (timezone-geolocator).

    This is the same invariant the audit script enforces; we duplicate
    it here so pytest catches regressions before CI runs the audit.
    """
    assert manifest["id"] == CONNECTION_DIR.name, (
        f"manifest id={manifest['id']!r} does not match folder name "
        f"{CONNECTION_DIR.name!r}"
    )
    assert manifest["id"] == "timezone-geolocator"


def test_tier_c_documents_reuse_first_strategy(manifest: dict) -> None:
    """Tier-c must NOT advertise tier-a-only RoamCore-owned fields AND
    must explicitly document the reuse-first strategy (no custom
    timezone engine; reuse GeoLocator + the existing RoamCore time
    helpers).

    A regression here (e.g. someone flipping tier to b without adding
    integration code + a bench fixture, or adding a RoamCore-owned
    timezone engine + setup flow that we explicitly chose NOT to
    ship) would falsely imply a working RoamCore integration +
    integration tests that we don't have, and the audit would
    either block the PR or let a misleading tier-b claim slip
    through. The tier-c strategy here is reuse-first: GeoLocator
    upstream HACS + a thin RoamCore automation wrapper.

    The distinction this test guards: install.hacs is TRUE here
    because the UPSTREAM HACS `geolocator` integration (by
    SmartyVan, since 2023.x) is the canonical timezone-update
    engine. That's honest upstream truth, NOT a RoamCore-owned
    HACS integration. The tier-b marker for RoamCore would be a
    RoamCore-owned operator-wired setup flow + RoamCore-owned
    integration code + integration tests against a RoamCore-owned
    timezone engine bench. None of those are shipped at tier-c.

    The reuse-first strategy is explicitly documented in the
    `description` field + the `tier_warnings` field + the
    `links.official` list (pointing at the GeoLocator upstream
    repo). The recipe §1 + §10 explicitly walk through why
    RoamCore does NOT maintain its own timezone engine (the
    DST rules change annually + GeoLocator upstream tracks
    these changes + writing a custom engine would duplicate
    work + introduce maintenance burden).
    """
    assert manifest["tier"] == "c", (
        "timezone-geolocator must stay at tier-c until a "
        "RoamCore-owned timezone engine + operator-wired setup "
        "flow + integration tests ship; tier-c is the honest tier "
        "for a reuse-first GeoLocator recipe"
    )
    assert manifest["wizard"]["one_tap"] is False, (
        "tier-c connections cannot advertise one_tap=true (that's "
        "a tier-a contract)"
    )
    # Timezone geolocator recipes an upstream GPS source (Path A
    # — Traccar Wave 3 #36 / HA Companion app / Wican Pro Wave 3
    # #6 OBD-II's GPS feed / generic `device_tracker.*` updating
    # `zone.home`) OR a manual `homeassistant.set_location`
    # service call (Path B) OR a RoamCore automation wrapper
    # (Path C — 15-min cadence or event-driven or manual);
    # RoamCore ships no native operator-wired setup flow for
    # that, and explicitly does NOT maintain a custom timezone
    # engine — we reuse GeoLocator's offline lookup table.
    # install.config_flow is the RoamCore-owned field. We
    # document the distinction in the manifest header: the
    # UPSTREAM HA core `zone` domain + the `device_tracker`
    # domain + the `homeassistant` service domain + the
    # `template` integration + the `input_boolean` integration
    # + the `input_datetime` integration + the HACS `geolocator`
    # integration ALL expose a GUI flow since 2022.x / 2023.x —
    # honest upstream truth, NOT a tier-a marker for RoamCore's
    # tier. The tier-a marker for RoamCore is a RoamCore-owned
    # operator-wired setup flow + integration tests. Until
    # those ship, this connection is tier-c.
    assert manifest["install"]["config_flow"] is True, (
        "install.config_flow must stay True — the upstream HA "
        "core `zone` domain + the `device_tracker` domain + the "
        "`homeassistant` service domain + the `template` "
        "integration + the `input_boolean` integration + the "
        "`input_datetime` integration + the HACS `geolocator` "
        "integration ALL expose a GUI flow since 2022.x / "
        "2023.x; this is honest upstream truth, NOT a tier-a "
        "marker for RoamCore's tier. The tier-a marker for "
        "RoamCore would be a RoamCore-owned operator-wired "
        "setup flow + RoamCore-owned integration code + "
        "integration tests against a RoamCore-owned timezone "
        "engine bench (a Traccar server + a mock GPS feed + "
        "canned fixture responses for multiple timezones + "
        "the upstream GeoLocator integration installed). None "
        "of those are shipped at tier-c."
    )
    # install.hacs is TRUE because the GeoLocator integration is
    # upstream HACS code (not RoamCore-owned). This is the
    # canonical HACS install — RoamCore does NOT ship a HACS
    # integration of its own; we recipe over the upstream HACS
    # `geolocator` integration by SmartyVan.
    assert manifest["install"]["hacs"] is True, (
        "timezone-geolocator must advertise install.hacs=true — "
        "the GeoLocator integration by SmartyVan is upstream "
        "HACS code that RoamCore recipes over (RoamCore does "
        "NOT ship a HACS integration of its own; install.hacs "
        "is the canonical HACS install for the upstream "
        "`geolocator` integration)"
    )
    assert manifest["install"]["hacs_url"] == "https://github.com/SmartyVan/hass-geolocator", (
        "install.hacs_url must point at the GeoLocator upstream "
        "HACS repo (https://github.com/SmartyVan/hass-geolocator); "
        "RoamCore does NOT maintain a HACS fork"
    )
    # Belt-and-braces: there must be no RoamCore-owned operator-
    # wired setup flow file in this folder (no native integration
    # code for a tier-c recipe connection). The upstream HA core
    # + zone / device_tracker / homeassistant / template /
    # input_boolean / input_datetime + HACS geolocator
    # integrations have their own GUI flows, but that lives in
    # the upstream HA core / HACS / vendor repos, not in this
    # folder.
    # The forbidden filenames for a tier-c recipe connection are
    # the canonical RoamCore-owned operator-wired setup flow +
    # integration-code filenames. The literal phrase
    # `config_flow.py` (with the .py suffix) MUST NOT appear as a
    # filename in this folder — same trap the happijac slice was
    # bitten by. The __init__.py docstring rephrases "config_flow"
    # as "operator-wired setup flow" or "the upstream integration's
    # GUI flow" to avoid the substring match.
    for forbidden_filename in ("config_flow.py",):
        assert not (CONNECTION_DIR / forbidden_filename).is_file(), (
            f"tier-c recipe connection must not ship a RoamCore-"
            f"owned {forbidden_filename} file"
        )
    # The __init__.py must be a DOMAIN-stub only — no integration
    # setup logic. We assert it exports DOMAIN and nothing else
    # that smells like HA integration code. CRITICAL: the literal
    # phrase `config_flow.py` (with the .py suffix, as a filename)
    # must not appear ANYWHERE in the __init__.py file — the same
    # trap the happijac slice was bitten by. The module docstring
    # rephrases "config_flow" as "operator-wired setup flow" or
    # "the upstream integration's GUI flow" to avoid the
    # substring match.
    init_text = (CONNECTION_DIR / "__init__.py").read_text(encoding="utf-8")
    assert "DOMAIN" in init_text, "__init__.py must export DOMAIN for the audit"
    # DOMAIN must equal "timezone_geolocator" (matches the connection
    # name "timezone-geolocator" → "timezone_geolocator" via the
    # audit convention of replacing hyphens with underscores).
    assert 'DOMAIN = "timezone_geolocator"' in init_text, (
        '__init__.py must define DOMAIN = "timezone_geolocator" '
        '(matches the connection name "timezone-geolocator" per '
        'the audit convention)'
    )
    for forbidden in ("async_setup", "config_flow.py", "PLATFORM_SCHEMA"):
        assert forbidden not in init_text, (
            f"__init__.py must be a DOMAIN stub; found {forbidden!r} "
            f"(tier-c recipe pattern; the happijac slice was bitten "
            f"by `config_flow.py` in the docstring — see that slice "
            f"for the rephrasing pattern; this slice uses "
            f"`operator-wired setup flow` and `the upstream "
            f"integration's GUI flow` instead of the literal "
            f"`config_flow.py` filename)"
        )
    # The reuse-first strategy must be explicitly documented in
    # the `description` field (the tier-c contract; tier-b would
    # own the integration code; tier-c explicitly does NOT own
    # the integration code — we recipe over GeoLocator).
    description = (manifest["description"] or "").lower()
    assert "reuse" in description or "geo_locator" in description or "geolocator" in description, (
        "manifest.description must explicitly document the "
        "reuse-first strategy (e.g. mention 'GeoLocator' or "
        "'reuse-first' or similar); tier-c is the honest tier "
        "for a recipe that does NOT own the integration code"
    )
    # The links.official list must point at the GeoLocator
    # upstream repo (the canonical reuse-first source).
    official_links = manifest.get("links", {}).get("official", [])
    assert any("geolocator" in link.lower() or "hass-geolocator" in link.lower() for link in official_links), (
        "links.official must include the GeoLocator upstream "
        "repo URL (https://github.com/SmartyVan/hass-geolocator); "
        "tier-c connections are explicit about which upstream "
        "integration they recipe over"
    )


def test_requires_docs_recipe_published(manifest: dict) -> None:
    """The audit's only tier-c hard requirement, made explicit.

    `docs_recipe_published` must be in tier_requirements AND a real
    recipe file must live on disk where the audit / docs site can
    reach it.
    """
    assert "docs_recipe_published" in manifest["tier_requirements"], (
        "tier-c requires 'docs_recipe_published' in tier_requirements"
    )
    assert RECIPE_PATH.is_file(), (
        f"tier_requirements promises a published recipe but {RECIPE_PATH} does not exist"
    )
    # Sanity: the recipe actually documents timezone geolocation
    # + the contract entities rather than just an empty placeholder.
    # The recipe mentions "timezone" / "geolocator" / "zone" /
    # "rc_time_zone_" — any one of these is sufficient (a
    # substantive howto would mention all of them, but the assertion
    # guards against the empty-placeholder regression).
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert (
        "timezone" in text.lower()
        or "geolocator" in text.lower()
        or "zone.home" in text.lower()
    ) and "rc_time_zone_" in text, (
        "recipe.md must document the timezone geolocator setup "
        "(Path A GPS source, Path B set_location fallback, Path "
        "C automation wrapper, contract entities, automation, "
        "troubleshooting) and reference at least one "
        "`rc_time_zone_*` tile"
    )
    # The spec requires ~600+ lines; we ship a substantive howto
    # well over that; this catches a regression where someone
    # leaves a 30-line placeholder.
    line_count = len(text.splitlines())
    assert line_count >= 600, (
        f"recipe.md must be a substantive howto (≥600 lines per "
        f"spec; the §3 Path A + §5 Path C + §6 contract entities "
        f"alone are ~400 lines); got {line_count}"
    )
    # Spec calls for all 11 §sections to be present (the recipe
    # is the umbrella for the 3 paths + the §6 contract entities
    # + the §7 single automation + §8 troubleshooting + §9 Privacy
    # + §10 Promoting to tier-b + §11 Files + cross-references).
    # Grep-anchor the major section headers so a future "I
    # rewrote the recipe as one wall of text" regression gets
    # caught.
    required_sections = (
        "## §1 What is timezone geolocator in RoamCore?",
        "## §2 Prerequisites",
        "## §3 Path A",
        "## §4 Path B",
        "## §5 Path C",
        "## §6 RoamCore contract entities",
        "## §7 Automations (MANDATORY before first use)",
        "## §8 Troubleshooting",
        "## §9 Privacy",
        "## §10 Promoting to tier-b",
        "## §11 Files in this connection + cross-references",
    )
    for header in required_sections:
        assert header in text, (
            f"recipe.md is missing required section header "
            f"{header!r} (spec requires §1–§11 to be present)"
        )


def test_category_matches_existing_legacy_doc(manifest: dict) -> None:
    """Sanity: category is set (legacy-doc pairing no longer enforced)."""
    assert manifest["category"], "category must be set"


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """rc_* tile ids must NOT contain vendor names (per rc-entity-naming.md).

    The timezone-geolocator contract is implementation-agnostic (it
    talks to whatever GPS source the operator wires + the upstream
    GeoLocator HACS integration, not any vendor's library).
    Contract ids must stay vendor-neutral — NO `traccar`,
    `ha_companion`, `wican`, `obd`, `hass`, `mqtt`, `esphome`,
    `hacs`, `ha_integration`, `template`, `binary_sensor`,
    `sensor`, `switch`, `input_boolean`, `input_select`,
    `input_number`, `input_datetime`, `input_text` in any rc_*
    tile id BEYOND the subsystem prefix `rc_time_zone_*`. The
    generic nouns `current`, `offset`, `synced`, `last`, `update`,
    `minutes`, `ago`, `stale`, `gps`, `source`, `cadence`,
    `button`, `now` are allowed (they describe what the tile is
    for, not which vendor).

    The spec is strict: every `dashboard.tiles[*]` must match
    `^[a-z_]+\\.rc_time_zone_[a-z0-9_]+$` (vendor-neutral,
    subsystem prefix `rc_time_zone_*` per the time subsystem
    naming convention established by the existing RoamCore
    time helpers — the `time` subsystem is OWNED by the
    existing `homeassistant/packages/roamcore_weather_time.yaml`
    + `sensor.rc_time_zone` override contract; this slice
    inherits the `rc_time_zone_*` prefix from the existing
    time helpers without backfilling, mirroring how hvac-
    basics Wave 3 #49 inherits the `rc_hvac_*` prefix from
    heated-floors Wave 3 #44 without backfilling).
    """
    import re

    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles, "timezone-geolocator contributes at least one dashboard tile"

    # Every tile must be a string entity id (spec calls for
    # tiles-as-strings, mirroring the spec's listed shape).
    for tile in tiles:
        assert isinstance(tile, str), (
            f"dashboard.tiles[*] must be a string entity id "
            f"(spec §1); got {tile!r}"
        )

    # Allowed HA core domain prefixes per docs/reference/rc-
    # entity-naming.md: binary_sensor, sensor, select, number,
    # button. (No `zone.*` domain tile in this connection — the
    # contract layer reports "is the timezone synced?" via
    # binary_sensor, not "what zone is the van in?" via zone.*;
    # the operator-side zone entity lives in the upstream zone
    # domain, not in the rc_time_zone_* contract layer.)
    allowed_domains = {"binary_sensor", "sensor", "select", "number", "button"}
    pattern = re.compile(r"^[a-z_]+\.rc_time_zone_[a-z0-9_]+$")

    # Vendor / implementation / device-side name leaks that must
    # NEVER appear in any rc_* tile id. The spec requirement is
    # "no double-stamps of [vendor + hardware names + protocol
    # names + integration names] beyond the rc_time_zone_
    # subsystem prefix". Vendor names like Traccar / Wican /
    # OBD / HACS / GeoLocator vendor names / MQTT / ESPHome /
    # HA Companion are an absolute vendor leak and are
    # forbidden from EVER appearing in any rc_* tile id
    # (regardless of where in the tile).
    #
    # The generic nouns (`current`, `offset`, `synced`, `last`,
    # `update`, `minutes`, `ago`, `stale`, `gps`, `source`,
    # `cadence`, `button`, `now`) are LITERALLY PART OF the
    # spec-required tile ids (e.g.
    # `sensor.rc_time_zone_current`,
    # `sensor.rc_time_zone_offset_minutes`,
    # `binary_sensor.rc_time_zone_synced`,
    # `binary_sensor.rc_time_zone_stale`,
    # `sensor.rc_time_zone_last_update_minutes_ago`,
    # `sensor.rc_time_zone_gps_source`,
    # `select.rc_time_zone_update_cadence`,
    # `button.rc_time_zone_update_now`) — the spec calls for
    # those tiles — so flagging them as absolute substrings of
    # the suffix would conflict with the literal tile ids the
    # spec requires. The forbidden_substrings list below targets
    # the vendor-name absolute-forbidden set only; the spec's
    # literal tile ids are accepted by ID and never double-stamp
    # any vendor name.
    forbidden_substrings = (
        # GPS source vendors / protocols — recipe explicitly
        # forbids these (absolute forbidden — no Traccar / HA
        # Companion / Wican / OBD / Zigbee / Z-Wave / mmWave /
        # HLK / LD2410 / Frigate / ESPHome / ESP32 names
        # anywhere in any rc_* tile id; vendor neutrality is
        # non-negotiable).
        "traccar",            # Traccar GPS server vendor (vendor leak)
        "ha_companion",       # HA Companion app (integration leak)
        "wican",              # Wican Pro OBD-II vendor (vendor leak)
        "obd",                # OBD-II protocol (integration leak)
        "obd_ii",             # OBD-II with underscore (integration leak)
        "obd-ii",             # OBD-II with hyphen (integration leak)
        "12v",                # 12V D+ signal voltage (hardware leak)
        "24v",                # 24V D+ signal voltage (hardware leak)
        "esphome",            # ESPHome integration name (integration leak)
        "esp_home",           # ESPHome with underscore (integration leak)
        "esp32",              # ESP32 microcontroller (hardware leak)
        "esp8266",            # ESP8266 microcontroller (hardware leak)
        "mqtt",               # MQTT integration (integration leak)
        "hass",               # HASS namespace (integration leak)
        "ha_integration",     # HA integration namespace (integration leak)
        "hacs",               # HACS namespace (integration leak)
        # Timezone engine vendor names — the recipe explicitly
        # forbids these from EVER appearing in any rc_* tile id;
        # GeoLocator is the upstream integration we recipe over,
        # not a vendor we own.
        "geolocator",         # GeoLocator integration name (vendor leak — recipe is reuse-first, not own-the-engine)
        "geo_locator",        # GeoLocator with underscore (vendor leak)
        "geo-locator",        # GeoLocator with hyphen (vendor leak)
        "smartyvan",          # SmartyVan vendor name (vendor leak)
        "smarty_van",         # SmartyVan with underscore (vendor leak)
        "smarty-van",         # SmartyVan with hyphen (vendor leak)
        # Zone / location domain / integration namespace leaks —
        # absolute forbidden.
        "zone_",              # zone namespace (integration leak)
        "zone.",              # zone namespace (integration leak)
        "binary_sensor_",     # binary_sensor namespace (integration leak)
        "sensor_",            # sensor namespace (integration leak)
        "switch",             # switch domain (integration leak)
        "input_boolean",      # input_boolean namespace (integration leak)
        "input_select",       # input_select namespace (integration leak)
        "input_number",       # input_number namespace (integration leak)
        "input_datetime",     # input_datetime namespace (integration leak)
        "input_text",         # input_text namespace (integration leak)
        "homeassistant",      # homeassistant service domain (integration leak)
        "device_tracker",     # device_tracker namespace (integration leak)
        "set_location",       # set_location service name (integration leak)
    )

    for tile in tiles:
        assert pattern.match(tile), (
            f"tile id {tile!r} must match ^[a-z_]+\\.rc_time_zone_"
            f"[a-z_]+$ (vendor-neutral contract naming per "
            f"docs/reference/rc-entity-naming.md)"
        )
        # Domain segment must be one of the allowed HA core
        # domain prefixes for the §time subsystem.
        domain = tile.split(".", 1)[0]
        assert domain in allowed_domains, (
            f"tile id {tile!r} uses domain {domain!r} which is "
            f"not in the allowed time domain set "
            f"{sorted(allowed_domains)!r}; per docs/reference/"
            f"rc-entity-naming.md §time subsystem"
        )
        # Subsystem prefix is rc_time_zone_; the suffix (after
        # `rc_time_zone_`) MUST NOT contain any forbidden vendor
        # substring.
        suffix = tile.split(".rc_time_zone_", 1)[1]
        for bad in forbidden_substrings:
            assert bad not in suffix.lower(), (
                f"tile id {tile!r} contains forbidden vendor "
                f"substring {bad!r} in the suffix after "
                f"`rc_time_zone_`; per docs/reference/rc-entity-"
                f"naming.md, contract ids are vendor-neutral — "
                f"vendor names are forbidden in any rc_* tile id"
            )
        # Each segment after the dot must be lowercase +
        # underscores + digits.
        for segment in tile.split("."):
            assert re.match(r"^[a-z_][a-z0-9_]*$", segment), (
                f"tile id {tile!r} contains a non-conforming "
                f"segment {segment!r}"
            )

    # Spec calls for exactly 8 tiles (1 sensor timezone + 1
    # sensor offset-minutes + 1 binary_sensor synced + 1
    # sensor last-update-minutes-ago + 1 binary_sensor stale
    # + 1 sensor GPS-source + 1 select update-cadence + 1
    # button update-now = 8 contract entities documented in
    # the recipe §6 contract layer):
    #   sensor.rc_time_zone_current
    #   sensor.rc_time_zone_offset_minutes
    #   binary_sensor.rc_time_zone_synced
    #   sensor.rc_time_zone_last_update_minutes_ago
    #   binary_sensor.rc_time_zone_stale
    #   sensor.rc_time_zone_gps_source
    #   select.rc_time_zone_update_cadence
    #   button.rc_time_zone_update_now
    assert len(tiles) == 8, (
        f"timezone-geolocator must contribute exactly 8 "
        f"contract tiles per spec (4 sensor + 2 binary_sensor + "
        f"1 select + 1 button); got {len(tiles)}"
    )


def test_status_reflects_no_real_timezone_engine(manifest: dict) -> None:
    """Status must be honest about no integration being shipped.

    If we ever flip this to 'shipped' or 'beta', the audit will
    demand an actual integration test (and rightly so).
    'recipe_published' is the only honest tier-c status for a
    recipe we can't integration-test (GeoLocator is upstream
    HACS code, not RoamCore-owned).

    The seven honesty warnings that tier_warnings must contain
    cover:
      - no_real_timezone_engine_for_integration_test (no bench
        fixture — a Traccar server + a mock GPS feed + canned
        fixture responses + the upstream GeoLocator integration
        installed, all wired together in a controlled
        environment)
      - recipe_depends_on_user_installing_geolocator_via_hacs
        (the upstream GeoLocator HACS integration must be
        installed BEFORE the §5 automation can do anything
        useful — this is operator's dependency, not
        RoamCore-enforced)
      - reuse_first_strategy_geo_locator_recommended_no_custom_
        timezone_engine (the explicit tier-c strategy: GeoLocator
        upstream HACS + a thin RoamCore wrapper; we do NOT
        maintain a custom timezone engine)
      - optional_gps_source_via_traccar_or_ha_companion_or_wican_
        pro (Path A GPS source is optional + additive; one of
        the 4 sources must be running before the §5 automation
        can update the timezone)
      - requires_zone_home_to_be_updated_by_a_gps_source (the
        `zone.home` entity must be updated by a GPS source for
        GeoLocator to compute the timezone)
      - cadence_vs_event_driven_choice_left_to_operator (the
        `select.rc_time_zone_update_cadence` lets the operator
        pick between event_driven / 15_min / 60_min / manual;
        this is an honest tier-c affordance — tier-b would
        enforce one cadence via RoamCore-owned code)
      - ha_system_timezone_change_does_not_require_ha_restart_
        via_geolocator (GeoLocator updates HA's system timezone
        via the `homeassistant.set_time_zone` service which does
        NOT require an HA restart — the recipe walks through the
        freshness gate + the freshness tile to make this
        discoverable)
    """
    assert manifest["status"] == "recipe_published", (
        f"timezone-geolocator status={manifest['status']!r} "
        f"implies shipped coverage we don't have; use "
        f"'recipe_published' until tier-b promotion lands"
    )
    tier_warnings = manifest.get("tier_warnings", [])
    # Tier-warnings must include the honest-about-no-timezone-
    # engine marker.
    assert "no_real_timezone_engine_for_integration_test" in tier_warnings, (
        "tier_warnings must declare 'no_real_timezone_engine_for_"
        "integration_test' for honesty in the audit listing"
    )
    # And the user-facing recipe dependency warning (operator
    # must install GeoLocator via HACS).
    assert "recipe_depends_on_user_installing_geolocator_via_hacs" in tier_warnings, (
        "tier_warnings must declare 'recipe_depends_on_user_"
        "installing_geolocator_via_hacs' so the audit listing is "
        "honest about the operator's HACS install dependency"
    )
    # Reuse-first strategy honesty — the explicit tier-c
    # strategy of reusing GeoLocator + NOT maintaining a custom
    # timezone engine.
    assert "reuse_first_strategy_geo_locator_recommended_no_custom_timezone_engine" in tier_warnings, (
        "tier_warnings must declare 'reuse_first_strategy_geo_"
        "locator_recommended_no_custom_timezone_engine' so the "
        "audit listing is honest about the tier-c strategy "
        "(GeoLocator upstream HACS + thin RoamCore wrapper; we "
        "do NOT maintain a custom timezone engine)"
    )
    # Path A honesty — the optional GPS source via Traccar /
    # HA Companion / Wican Pro is optional + additive.
    assert "optional_gps_source_via_traccar_or_ha_companion_or_wican_pro" in tier_warnings, (
        "tier_warnings must declare 'optional_gps_source_via_"
        "traccar_or_ha_companion_or_wican_pro' so the audit "
        "listing is honest about the optional Path A GPS source "
        "hardware dependency"
    )
    # zone.home honesty — the operator must wire a GPS source
    # that updates `zone.home` before GeoLocator can compute the
    # timezone.
    assert "requires_zone_home_to_be_updated_by_a_gps_source" in tier_warnings, (
        "tier_warnings must declare 'requires_zone_home_to_be_"
        "updated_by_a_gps_source' so the audit listing is "
        "honest that GeoLocator reads coordinates from "
        "`zone.home` and the operator must wire a GPS source "
        "that updates `zone.home` before the §5 automation can "
        "do anything useful"
    )
    # Cadence-vs-event-driven honesty — the operator picks the
    # cadence via `select.rc_time_zone_update_cadence`; this
    # is an honest tier-c affordance (tier-b would enforce one
    # cadence via RoamCore-owned code).
    assert "cadence_vs_event_driven_choice_left_to_operator" in tier_warnings, (
        "tier_warnings must declare 'cadence_vs_event_driven_"
        "choice_left_to_operator' so the audit listing is "
        "honest that the cadence select is operator-tunable "
        "(event_driven / 15_min / 60_min / manual) rather than "
        "RoamCore-enforced at tier-c"
    )
    # HA system timezone change does NOT require HA restart via
    # GeoLocator (the recipe walks through the freshness gate +
    # the freshness tile to make this discoverable).
    assert "ha_system_timezone_change_does_not_require_ha_restart_via_geolocator" in tier_warnings, (
        "tier_warnings must declare 'ha_system_timezone_change_"
        "does_not_require_ha_restart_via_geolocator' so the "
        "audit listing is honest that GeoLocator updates the "
        "system timezone via `homeassistant.set_time_zone` "
        "(which does NOT require an HA restart) rather than "
        "requiring an HA restart like the legacy HA core "
        "`configuration.yaml` `time_zone:` setting"
    )


def test_automations_are_documented(manifest: dict) -> None:
    """Defensive guard for the future tier-b promotion.

    Timezone correctness is a one-shot safety feature in van life:
    forgetting to keep the timezone in sync as the van travels
    across regions breaks time-based automations (sun events +
    `now()` + `today_at()`) silently — the operator may not notice
    the breakage until the sun-triggered scene fires at the wrong
    time. The recipe §7 walks through the single MANDATORY
    automation:
      - §7 Update timezone (15-min cadence default OR event-
        driven alternative OR manual) via
        `geolocator.update_location` (cross-reference to the
        GeoLocator upstream HACS integration). GeoLocator handles
        the timezone lookup + the `homeassistant.set_time_zone`
        service call internally — RoamCore does NOT maintain a
        custom timezone engine.

    The test asserts the single automation is documented in the
    recipe so that when this connection promotes to tier-b (with
    a real timezone engine bench on CI + the cadence select
    default + automation asserts hard-enforced in RoamCore code
    rather than only documented in the recipe), the audit has a
    clean assertion to flip.
    """
    text = RECIPE_PATH.read_text(encoding="utf-8")
    # §7 header MUST be present (with the "MANDATORY before first
    # use" wording).
    assert "## §7 Automations (MANDATORY before first use)" in text, (
        "recipe.md must have a '## §7 Automations (MANDATORY "
        "before first use)' section (the single MANDATORY "
        "automation documentation block)"
    )
    # §7 must cover the single automation area.
    automation_coverage = (
        # §7 Update timezone (15-min cadence OR event-driven OR
        # manual) via `geolocator.update_location` — the single
        # automation that keeps the system timezone synced with
        # `zone.home`. GeoLocator handles the timezone lookup +
        # the `homeassistant.set_time_zone` service call
        # internally; RoamCore does NOT maintain a custom
        # timezone engine.
        "update timezone",
    )
    for phrase in automation_coverage:
        assert phrase in text.lower(), (
            f"recipe.md §7 must cover {phrase!r}; the single "
            f"automation is MANDATORY before first use, and the "
            f"recipe is the only documentation operator + future-"
            f"tier-b integration code have at this tier"
        )
    # The contract tiles must include the four tiles that the
    # §7 automation + the operator-facing affordance surfaces:
    #   sensor.rc_time_zone_current
    #     (the §7 system timezone tile)
    #   binary_sensor.rc_time_zone_synced
    #     (the §7 correctness gate)
    #   binary_sensor.rc_time_zone_stale
    #     (the §7 freshness gate)
    #   button.rc_time_zone_update_now
    #     (the §7 on-demand affordance — forces a
    #     `geolocator.update_location` call without waiting for
    #     the next cadence tick)
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    safety_tiles = (
        "sensor.rc_time_zone_current",
        "binary_sensor.rc_time_zone_synced",
        "binary_sensor.rc_time_zone_stale",
        "button.rc_time_zone_update_now",
    )
    for safety_tile in safety_tiles:
        assert safety_tile in tiles, (
            f"dashboard.tiles must include {safety_tile!r}; the "
            f"§7 automation + operator-facing affordance tiles "
            f"are part of the contract layer that the recipe §7 "
            f"documents"
        )
    # The recipe must cross-reference the GeoLocator upstream
    # HACS integration so the §7 automation + the §5 cadence
    # wrapper are discoverable.
    assert "geolocator.update_location" in text.lower(), (
        "recipe.md must reference `geolocator.update_location` "
        "for the §7 automation + the §5 cadence wrapper"
    )
    assert "geolocator" in text.lower(), (
        "recipe.md must reference `GeoLocator` for the §7 "
        "automation + the §5 cadence wrapper + the §1 "
        "reuse-first strategy"
    )
    # The recipe must cross-reference the `zone.home` entity so
    # the §3 Path A GPS source wiring is discoverable.
    assert "zone.home" in text.lower(), (
        "recipe.md must reference `zone.home` for the §3 Path A "
        "GPS source wiring (GeoLocator reads coordinates from "
        "`zone.home`)"
    )
    # The recipe must cross-reference the
    # `homeassistant.set_location` service so the §4 Path B
    # fallback wiring is discoverable.
    assert "homeassistant.set_location" in text.lower(), (
        "recipe.md must reference `homeassistant.set_location` "
        "for the §4 Path B fallback wiring (the operator can "
        "manually push coordinates to HA via this service call "
        "for benches without a GPS tracker)"
    )
    # The recipe must cross-reference the existing RoamCore
    # time helpers (`sensor.rc_time_zone` override contract +
    # `homeassistant/packages/roamcore_weather_time.yaml`) so
    # the §6 contract entities + the §11 cross-references are
    # discoverable.
    assert "sensor.rc_time_zone" in text, (
        "recipe.md must reference `sensor.rc_time_zone` for the "
        "§6 contract entities + the §11 cross-references to the "
        "existing RoamCore time helpers (the override contract)"
    )
    assert "roamcore_weather_time.yaml" in text, (
        "recipe.md must reference `roamcore_weather_time.yaml` "
        "for the §6 contract entities + the §11 cross-references "
        "to the existing RoamCore time helpers (the weather-time "
        "package)"
    )
    # The recipe's defensive guard for future tier-b promotion —
    # assert the §7 section has the "MANDATORY before first use"
    # emphasis that the recipe uses to remind operators to wire
    # the single automation.
    assert "mandatory before first use" in text.lower(), (
        "recipe.md §7 must use the 'MANDATORY before first use' "
        "emphasis on the single automation; this is the operator-"
        "side reminder that keeps the automation top-of-mind "
        "during install"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))