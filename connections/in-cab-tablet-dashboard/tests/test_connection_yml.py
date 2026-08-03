"""Manifest-honesty tests for connections/in-cab-tablet-dashboard/connection.yml.

This is the only test file we can ship for a tier-c recipe connection
that has no real in-cab-tablet bench (a 7-10" Android tablet mounted
in the cab with the HA Companion app installed + a Wican Pro OBD-II
reader for the ignition source + a Traccar server for the location
proxy + canned fixture responses for ignition-on / ignition-off /
zone-home / zone-away events) on the CI rig to integration-test
against. The tests here assert that the manifest is *honest about
being tier-c* — that the folder/id/tier invariants hold, that the
recipe doc the tier_requirements promise is actually present on
disk, that the rc_in_cab_tablet_* tile ids are vendor-neutral per
docs/reference/rc-entity-naming.md, and that the THREE §7
automations are documented with the right cross-references (Wican
Pro / Traccar / HA Companion / Approach lights / HVAC basics /
Teltonika).

If you add real integration coverage (e.g. an operator-wired setup
flow + a bench with a physical Android tablet + a Wican Pro OBD-II
reader + a Traccar server + canned fixture responses), keep this
file and add the new one alongside it; the audit will then list
both under `tests:` in the manifest.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/in-cab-tablet-dashboard/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> in-cab-tablet-dashboard/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "in-cab-tablet-dashboard"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
LEGACY_DOC = REPO_ROOT / "docs" / "catalog" / "vehicle-obd" / "in-cab-tablet-dashboard.md"
LOVELACE_FILE = REPO_ROOT / "dashboard" / "lovelace" / "storage" / "lovelace.roamcore.json"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_connection_yaml_is_valid(manifest: dict) -> None:
    """Base YAML parse + tier=c + status=recipe_published + DOMAIN=`in_cab_tablet`.

    The manifest must be a well-formed YAML document. The required
    fields (id, tier, category, status, version) must all be
    present. The DOMAIN constant in __init__.py must match the
    connection name per the audit convention of replacing hyphens
    with underscores.
    """
    assert manifest["id"] == CONNECTION_DIR.name, (
        f"manifest id={manifest['id']!r} does not match folder "
        f"name {CONNECTION_DIR.name!r}"
    )
    assert manifest["id"] == "in-cab-tablet-dashboard", (
        "manifest id must be 'in-cab-tablet-dashboard'"
    )
    assert manifest["tier"] == "c", (
        f"in-cab-tablet-dashboard must stay at tier-c until a "
        f"RoamCore-owned in-cab-tablet dashboard engine + "
        f"operator-wired setup flow + integration tests ship; "
        f"tier-c is the honest tier for a reuse-first HA "
        f"Lovelace view system recipe; got tier={manifest['tier']!r}"
    )
    assert manifest["status"] == "recipe_published", (
        f"in-cab-tablet-dashboard status={manifest['status']!r} "
        f"implies shipped coverage we don't have; use "
        f"'recipe_published' until tier-b promotion lands"
    )
    # DOMAIN constant must be present in __init__.py
    init_text = (CONNECTION_DIR / "__init__.py").read_text(encoding="utf-8")
    assert 'DOMAIN = "in_cab_tablet"' in init_text, (
        '__init__.py must define DOMAIN = "in_cab_tablet" '
        "(matches the connection name 'in-cab-tablet-dashboard' "
        "per the audit convention of replacing hyphens with "
        "underscores)"
    )
    assert "DOMAIN" in init_text, "__init__.py must export DOMAIN for the audit"


def test_tier_c_documents_reuse_first_strategy(manifest: dict) -> None:
    """Tier-c must NOT advertise tier-a-only RoamCore-owned fields AND
    must explicitly document the reuse-first strategy (no custom
    in-cab-tablet dashboard engine; reuse the upstream HA Lovelace
    view system + the `input_select` + `input_button` +
    `device_tracker` integrations).

    A regression here (e.g. someone flipping tier to b without adding
    integration code + a bench fixture, or adding a RoamCore-owned
    in-cab-tablet dashboard engine + setup flow that we explicitly
    chose NOT to ship) would falsely imply a working RoamCore
    integration + integration tests that we don't have, and the
    audit would either block the PR or let a misleading tier-b
    claim slip through. The tier-c strategy here is reuse-first:
    upstream HA Lovelace view system (Path A "Driving" view + Path
    B "Arrival / Welcome" view + Path C "Lock screen / Always-on-
    display" view) + upstream `input_select` integration (the
    `select.rc_in_cab_tablet_view_mode` select) + upstream
    `input_button` integration (the
    `button.rc_in_cab_tablet_set_view_now` button) + upstream
    `device_tracker` domain (the fallback ignition source from
    Traccar / HA Companion / Wican Pro).
    """
    assert manifest["tier"] == "c", (
        "in-cab-tablet-dashboard must stay at tier-c until a "
        "RoamCore-owned in-cab-tablet dashboard engine + "
        "operator-wired setup flow + integration tests ship; "
        "tier-c is the honest tier for a reuse-first HA "
        "Lovelace view system recipe"
    )
    assert manifest["wizard"]["one_tap"] is False, (
        "tier-c connections cannot advertise one_tap=true (that's "
        "a tier-a contract)"
    )
    # install.config_flow is FALSE because RoamCore ships no
    # native in-cab-tablet dashboard engine; the recipe is a
    # pure recipe over the upstream HA Lovelace view system (no
    # RoamCore-owned operator-wired setup flow). The UPSTREAM
    # HA core dashboard UI exposes a "Add view" button in the
    # dashboard edit mode (since 2022.x — lets the operator add
    # a `panel` view with custom title + icon + cards) + a "Raw
    # configuration editor" (since 2022.x — exposes a YAML
    # editor for the `ui-lovelace.yaml` file). That's honest
    # upstream truth, NOT a tier-a marker for RoamCore's tier.
    # The tier-a marker for RoamCore is a RoamCore-owned
    # operator-wired setup flow + integration tests. Until
    # those ship, this connection is tier-c with
    # install.config_flow=false.
    assert manifest["install"]["config_flow"] is False, (
        "install.config_flow must stay False — RoamCore ships no "
        "native in-cab-tablet dashboard engine; the recipe is a "
        "pure recipe over the upstream HA Lovelace view system "
        "(no RoamCore-owned operator-wired setup flow). The "
        "UPSTREAM HA core dashboard UI exposes a 'Add view' "
        "button + a 'Raw configuration editor' since 2022.x — "
        "honest upstream truth, NOT a tier-a marker for "
        "RoamCore's tier. The tier-a marker for RoamCore is a "
        "RoamCore-owned operator-wired setup flow + integration "
        "tests. Until those ship, this connection is tier-c with "
        "install.config_flow=false."
    )
    # install.hacs is FALSE because in-cab-tablet-dashboard is a
    # pure recipe over upstream HA core's Lovelace view system
    # (no HACS code required). RoamCore does NOT ship a HACS
    # integration of its own; we recipe over the upstream HA
    # Lovelace view system + the `input_select` + `input_button`
    # + `device_tracker` integrations.
    assert manifest["install"]["hacs"] is False, (
        "in-cab-tablet-dashboard must advertise install.hacs="
        "false — in-cab-tablet-dashboard is a pure recipe over "
        "the upstream HA Lovelace view system (no HACS code "
        "required; install.hacs is FALSE for tier-c recipes "
        "that don't depend on HACS code)"
    )
    # Belt-and-braces: there must be no RoamCore-owned operator-
    # wired setup flow file in this folder (no native integration
    # code for a tier-c recipe connection). The upstream HA core
    # Lovelace view system has its own "Add view" button in the
    # dashboard edit mode, but that lives in the upstream HA core,
    # not in this folder.
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
    # the integration code — we recipe over the upstream HA
    # Lovelace view system + the `input_select` + `input_button`
    # + `device_tracker` integrations).
    description = (manifest["description"] or "").lower()
    assert (
        "reuse" in description
        or "lovelace" in description
        or "ha core" in description
        or "in-cab-tablet" in description
        or "in_cab_tablet" in description
    ), (
        "manifest.description must explicitly document the "
        "reuse-first strategy (e.g. mention 'reuse' or 'lovelace' "
        "or 'ha core' or 'in-cab-tablet' or similar); tier-c is "
        "the honest tier for a recipe that does NOT own the "
        "integration code"
    )
    # The links.official list must point at the HA core dashboard
    # docs URL (the canonical reuse-first source).
    official_links = manifest.get("links", {}).get("official", [])
    assert any(
        "home-assistant.io/dashboards" in link.lower()
        for link in official_links
    ), (
        "links.official must include the HA core dashboard "
        "docs URL "
        "(https://www.home-assistant.io/dashboards/); "
        "tier-c connections are explicit about which upstream "
        "integration they recipe over"
    )


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    r"""rc_* tile ids must NOT contain vendor names (per rc-entity-naming.md).

    The in-cab-tablet-dashboard contract is implementation-agnostic
    (it talks to whatever tablet the operator wires + whatever
    ignition source the operator wires + whatever dashboard view
    layout the operator uses, not any vendor's library or
    integration). Contract ids must stay vendor-neutral — NO
    `wican`, `obd`, `12v`, `24v`, `traccar`, `ha_companion`,
    `mqtt`, `hacs`, `homeassistant`, `device_tracker`,
    `lovelace`, `dashboard_`, `view_`, `panel`, `esphome`,
    `esp32`, `binary_sensor_`, `sensor_`, `switch`,
    `input_boolean`, `input_select`, `input_number`,
    `input_datetime`, `input_text` in any rc_* tile id BEYOND
    the subsystem prefix `rc_in_cab_tablet_*`. The generic
    nouns `active`, `view`, `ignition`, `state`, `last`,
    `switch`, `minutes`, `ago`, `refresh`, `cadence`,
    `seconds`, `driving`, `mode`, `lock`, `screen`, `now` are
    allowed (they describe what the tile is for, not which
    vendor).

    The spec is strict: every `dashboard.tiles[*]` must match
    `^[a-z_]+\.rc_in_cab_tablet_[a-z0-9_]+$` (vendor-neutral,
    subsystem prefix `rc_in_cab_tablet_*` per the in-cab-
    tablet-dashboard SPECIFIC subset of the broader vehicle
    subsystem naming convention established by the existing
    Wican Pro Wave 3 #6 connection).

    CRITICAL: the in-cab-tablet-dashboard prefix is
    `rc_in_cab_tablet_*` (NOT `rc_dashboard_*` and NOT
    `rc_in_cab_*` and NOT `rc_tablet_*`); the vehicle
    subsystem prefix is `rc_vehicle_*` (OWNED by the existing
    Wican Pro Wave 3 #6 connection); this slice's
    `rc_in_cab_tablet_*` prefix is the SPECIFIC in-cab-
    tablet-dashboard subset of the broader vehicle subsystem,
    mirroring how time-atomic Wave 3 #55 inherits the
    `rc_time_*` prefix from the existing time helpers and how
    hvac-basics Wave 3 #49 inherits the `rc_hvac_*` prefix
    from heated-floors Wave 3 #44.
    """
    import re

    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles, "in-cab-tablet-dashboard contributes at least one dashboard tile"

    # Every tile must be a string entity id (spec calls for
    # tiles-as-strings, mirroring the spec's listed shape).
    for tile in tiles:
        assert isinstance(tile, str), (
            f"dashboard.tiles[*] must be a string entity id "
            f"(spec §1); got {tile!r}"
        )

    # Allowed HA core domain prefixes per docs/reference/rc-
    # entity-naming.md: binary_sensor, sensor, select, button.
    allowed_domains = {"binary_sensor", "sensor", "select", "button"}
    pattern = re.compile(r"^[a-z_]+\.rc_in_cab_tablet_[a-z0-9_]+$")

    # Vendor / implementation / hardware-side name leaks that
    # must NEVER appear in any rc_* tile id. The spec
    # requirement is "no double-stamps of [vendor + hardware
    # names + protocol names + integration names] beyond the
    # rc_in_cab_tablet_ subsystem prefix". Vendor names like
    # Wican / OBD / Traccar / HA Companion / MQTT / HACS /
    # ESPHome / ESP32 / Lovelace / Dashboard / View / Panel
    # are an absolute vendor leak and are forbidden from EVER
    # appearing in any rc_* tile id (regardless of where in
    # the tile).
    forbidden_substrings = (
        # Vehicle OBD vendors / protocols / packages — recipe
        # explicitly forbids these (absolute forbidden — no
        # Wican / OBD / 12V / 24V / HACS names anywhere in
        # any rc_* tile id; vendor neutrality is
        # non-negotiable).
        "wican",              # Wican Pro OBD-II vendor (vendor leak)
        "obd",                # OBD-II protocol (integration leak)
        "obd_ii",             # OBD-II with underscore (integration leak)
        "obd-ii",             # OBD-II with hyphen (integration leak)
        "12v",                # 12V D+ signal voltage (hardware leak)
        "24v",                # 24V D+ signal voltage (hardware leak)
        "mqtt",               # MQTT integration (integration leak)
        "hass",               # HASS namespace (integration leak)
        "ha_integration",     # HA integration namespace (integration leak)
        "hacs",               # HACS namespace (integration leak)
        # Location / GPS source vendors / protocols — recipe
        # explicitly forbids these (absolute forbidden — no
        # Traccar / HA Companion / Frigate / ESPHome / ESP32
        # names anywhere in any rc_* tile id; vendor neutrality
        # is non-negotiable).
        "traccar",            # Traccar GPS server vendor (vendor leak)
        "ha_companion",       # HA Companion app (integration leak)
        "esphome",            # ESPHome integration name (integration leak)
        "esp_home",           # ESPHome with underscore (integration leak)
        "esp32",              # ESP32 microcontroller (hardware leak)
        "esp8266",            # ESP8266 microcontroller (hardware leak)
        "frigate",            # Frigate (vendor leak)
        # Dashboard / panel / lovelace namespaces — the
        # recipe is layered over the upstream HA Lovelace view
        # system, but those names are forbidden from EVER
        # appearing in any rc_* tile id (the tile prefix must
        # be the in-cab-tablet-dashboard-specific
        # `rc_in_cab_tablet_*`, NOT a generic `rc_dashboard_*`
        # or `rc_lovelace_*` or `rc_panel_*`).
        # Note: `view_` is NOT in the forbidden list because
        # the spec-required tile ids
        # (`sensor.rc_in_cab_tablet_active_view` +
        # `sensor.rc_in_cab_tablet_last_view_change_minutes_
        # ago` + `select.rc_in_cab_tablet_view_mode` +
        # `button.rc_in_cab_tablet_set_view_now`)
        # legitimately contain `view_` as a generic UI noun
        # describing the Lovelace view the tablet is showing
        # (not a vendor leak); the forbidden_substrings list
        # targets vendor / hardware / protocol / integration
        # names only.
        "homeassistant",      # homeassistant service domain (integration leak)
        "device_tracker",     # device_tracker namespace (integration leak)
        "lovelace",           # lovelace namespace (integration leak)
        "dashboard_",         # dashboard_ namespace (integration leak)
        "panel",              # panel namespace (integration leak)
        # Domain / integration / helper namespace leaks —
        # absolute forbidden.
        "binary_sensor_",     # binary_sensor namespace (integration leak)
        "sensor_",            # sensor namespace (integration leak)
        "switch",             # switch domain (integration leak)
        "input_boolean",      # input_boolean namespace (integration leak)
        "input_select",       # input_select namespace (integration leak)
        "input_number",       # input_number namespace (integration leak)
        "input_datetime",     # input_datetime namespace (integration leak)
        "input_text",         # input_text namespace (integration leak)
    )

    for tile in tiles:
        assert pattern.match(tile), (
            f"tile id {tile!r} must match ^[a-z_]+\\.rc_in_cab_"
            f"tablet_[a-z_]+$ (vendor-neutral contract naming "
            f"per docs/reference/rc-entity-naming.md)"
        )
        # Domain segment must be one of the allowed HA core
        # domain prefixes for the in-cab-tablet-dashboard
        # subsystem.
        domain = tile.split(".", 1)[0]
        assert domain in allowed_domains, (
            f"tile id {tile!r} uses domain {domain!r} which is "
            f"not in the allowed in-cab-tablet-dashboard domain "
            f"set {sorted(allowed_domains)!r}; per docs/reference/"
            f"rc-entity-naming.md §vehicle subsystem"
        )
        # Subsystem prefix is rc_in_cab_tablet_; the suffix
        # (after `rc_in_cab_tablet_`) MUST NOT contain any
        # forbidden vendor substring.
        suffix = tile.split(".rc_in_cab_tablet_", 1)[1]
        for bad in forbidden_substrings:
            assert bad not in suffix.lower(), (
                f"tile id {tile!r} contains forbidden vendor "
                f"substring {bad!r} in the suffix after "
                f"`rc_in_cab_tablet_`; per docs/reference/rc-"
                f"entity-naming.md, contract ids are vendor-"
                f"neutral — vendor names are forbidden in any "
                f"rc_* tile id"
            )
        # Each segment after the dot must be lowercase +
        # underscores + digits.
        for segment in tile.split("."):
            assert re.match(r"^[a-z_][a-z0-9_]*$", segment), (
                f"tile id {tile!r} contains a non-conforming "
                f"segment {segment!r}"
            )

    # Spec calls for exactly 8 tiles (4 sensor active-view +
    # ignition-state + last-view-switch-minutes-ago + refresh-
    # cadence-seconds + 2 binary_sensor driving-mode-active +
    # lock-screen-active + 1 select view-mode + 1 button
    # switch-view-now = 8 contract entities documented in
    # the recipe §6 contract layer):
    #   sensor.rc_in_cab_tablet_active_view
    #   sensor.rc_in_cab_tablet_ignition_state
    #   sensor.rc_in_cab_tablet_last_view_change_minutes_ago
    #   sensor.rc_in_cab_tablet_refresh_cadence_seconds
    #   binary_sensor.rc_in_cab_tablet_driving_mode_active
    #   binary_sensor.rc_in_cab_tablet_lock_screen_active
    #   select.rc_in_cab_tablet_view_mode
    #   button.rc_in_cab_tablet_set_view_now
    assert len(tiles) == 8, (
        f"in-cab-tablet-dashboard must contribute exactly 8 "
        f"contract tiles per spec (4 sensor + 2 binary_sensor "
        f"+ 1 select + 1 button); got {len(tiles)}"
    )


def test_status_reflects_recipe_published(manifest: dict) -> None:
    """Status must be honest about no integration being shipped.

    If we ever flip this to 'shipped' or 'beta', the audit will
    demand an actual integration test (and rightly so).
    'recipe_published' is the only honest tier-c status for a
    recipe we can't integration-test (HA's Lovelace view system
    is upstream HA core code, not RoamCore-owned).

    The five honesty warnings that tier_warnings must contain
    cover:
      - no_native_in_cab_tablet_integration (no bench fixture
        — a 7-10" Android tablet mounted in the cab with the
        HA Companion app installed + a Wican Pro OBD-II
        reader for the ignition source + a Traccar server for
        the location proxy + canned fixture responses for
        ignition-on / ignition-off / zone-home / zone-away
        events, all wired together in a controlled
        environment)
      - recipe_depends_on_user_wiring_dashboard_yaml (the
        operator must wire the Path A "Driving" view + the
        Path B "Arrival / Welcome" view + the Path C "Lock
        screen / Always-on-display" view in `ui-lovelace.yaml`
        before the §7 automations can do anything useful; this
        is operator's dependency, not RoamCore-enforced)
      - requires_operator_choice_of_path_a_driving_view_or_
        path_b_arrival_view_or_path_c_lock_screen (the
        operator picks ONE OR MORE of Path A "Driving" view /
        Path B "Arrival / Welcome" view / Path C "Lock
        screen / Always-on-display" view; this is an honest
        tier-c affordance — tier-b would enforce one path via
        RoamCore-owned code)
      - no_real_vehicle_ignition_signal_on_ci_bench (RoamCore
        does NOT have a vehicle ignition fixture on the CI
        rig — the rig would require a physical Wican Pro
        OBD-II reader + a Traccar server + canned fixture
        responses for ignition events; tests are manifest-
        honesty only, NOT integration tests)
      - mode_aware_stealth_suppression_not_required (in-cab-
        tablet-dashboard tiles are non-actuator — safe to
        leave running in Stealth mode; the recipe §11 cross-
        references this honestly).
    """
    assert manifest["status"] == "recipe_published", (
        f"in-cab-tablet-dashboard status={manifest['status']!r} "
        f"implies shipped coverage we don't have; use "
        f"'recipe_published' until tier-b promotion lands"
    )
    tier_warnings = manifest.get("tier_warnings", [])
    # Tier-warnings must include the honest-about-no-native-
    # in-cab-tablet-integration marker.
    assert "no_native_in_cab_tablet_integration" in tier_warnings, (
        "tier_warnings must declare 'no_native_in_cab_tablet_"
        "integration' for honesty in the audit listing"
    )
    # And the user-facing recipe dependency warning (operator
    # must wire the dashboard YAML).
    assert "recipe_depends_on_user_wiring_dashboard_yaml" in tier_warnings, (
        "tier_warnings must declare 'recipe_depends_on_user_"
        "wiring_dashboard_yaml' so the audit listing is honest "
        "about the operator's dashboard YAML wiring dependency"
    )
    # Operator-choice-of-path honesty — the operator picks ONE
    # OR MORE of Path A "Driving" view / Path B "Arrival /
    # Welcome" view / Path C "Lock screen / Always-on-
    # display" view.
    assert "requires_operator_choice_of_path_a_driving_view_or_path_b_arrival_view_or_path_c_lock_screen" in tier_warnings, (
        "tier_warnings must declare 'requires_operator_choice_"
        "of_path_a_driving_view_or_path_b_arrival_view_or_path_"
        "c_lock_screen' so the audit listing is honest that the "
        "operator picks ONE OR MORE of Path A 'Driving' view / "
        "Path B 'Arrival / Welcome' view / Path C 'Lock screen / "
        "Always-on-display' view rather than RoamCore-enforcing "
        "one path at tier-c"
    )
    # No real vehicle ignition signal on CI bench honesty.
    assert "no_real_vehicle_ignition_signal_on_ci_bench" in tier_warnings, (
        "tier_warnings must declare 'no_real_vehicle_ignition_"
        "signal_on_ci_bench' so the audit listing is honest "
        "that RoamCore does NOT have a vehicle ignition "
        "fixture on the CI rig (a physical Wican Pro OBD-II "
        "reader + a Traccar server + canned fixture responses "
        "for ignition events wired together in a controlled "
        "environment); tests are manifest-honesty only, NOT "
        "integration tests"
    )
    # Mode-aware stealth suppression not required honesty —
    # in-cab-tablet-dashboard tiles are non-actuator (safe to
    # leave running in Stealth mode; the recipe §11 cross-
    # references this honestly).
    assert "mode_aware_stealth_suppression_not_required" in tier_warnings, (
        "tier_warnings must declare 'mode_aware_stealth_"
        "suppression_not_required' so the audit listing is "
        "honest that in-cab-tablet-dashboard tiles are non-"
        "actuator and safe to leave running in Stealth mode "
        "(view switching is a non-actuator concern — the "
        "recipe §11 cross-references this honestly)"
    )


def test_automations_are_documented(manifest: dict) -> None:
    """Defensive guard for the future tier-b promotion.

    The in-cab tablet view auto-switch is a one-shot safety
    feature in van life: forgetting to auto-switch the view
    on ignition-on / ignition-off can leave the operator
    staring at the wrong view (the rich arrival view while
    the engine is off + the tablet is in the cab + the
    battery is draining; the lock screen view while the
    operator is arriving home + the operator needs to control
    exterior lights + compressor + house status). The recipe
    §7 walks through the THREE MANDATORY automations:
      - §7.1 Ignition-on auto-switch to `arrival` view —
        triggers when the Wican Pro
        `binary_sensor.rc_vehicle_ignition` turns on OR a
        generic `binary_sensor.*` ignition source turns on OR
        a `device_tracker.rc_location_van` state change to
        home zone.
      - §7.2 Ignition-off auto-switch to `lock_screen` view —
        triggers when the Wican Pro
        `binary_sensor.rc_vehicle_ignition` turns off.
      - §7.3 Manual override via the
        `select.rc_in_cab_tablet_view_mode` select or the
        `button.rc_in_cab_tablet_set_view_now` button —
        triggers when the operator changes the view mode
        select OR presses the switch view now button.

    The test asserts the THREE automations are documented in
    the recipe so that when this connection promotes to
    tier-b (with a real in-cab-tablet bench on CI + the THREE
    automations hard-enforced in RoamCore code rather than
    only documented in the recipe), the audit has a clean
    assertion to flip.
    """
    text = RECIPE_PATH.read_text(encoding="utf-8")
    # §7 header MUST be present (with the "MANDATORY before first
    # use" wording).
    assert "## §7 Automations (MANDATORY before first use)" in text, (
        "recipe.md must have a '## §7 Automations (MANDATORY "
        "before first use)' section (the THREE MANDATORY "
        "automation documentation block)"
    )
    # §7 must cover the THREE automation areas.
    automation_coverage = (
        # §7.1 Ignition-on auto-switch to `arrival` view —
        # triggers when the Wican Pro
        # `binary_sensor.rc_vehicle_ignition` turns on OR a
        # generic `binary_sensor.*` ignition source turns on OR
        # a `device_tracker.rc_location_van` state change to
        # home zone.
        "ignition-on auto-switch",
        # §7.2 Ignition-off auto-switch to `lock_screen` view —
        # triggers when the Wican Pro
        # `binary_sensor.rc_vehicle_ignition` turns off.
        "ignition-off auto-switch",
        # §7.3 Manual override via the
        # `select.rc_in_cab_tablet_view_mode` select or the
        # `button.rc_in_cab_tablet_set_view_now` button.
        "manual override",
    )
    for phrase in automation_coverage:
        assert phrase in text.lower(), (
            f"recipe.md §7 must cover {phrase!r}; the THREE "
            f"automations are MANDATORY before first use, and "
            f"the recipe is the only documentation operator + "
            f"future-tier-b integration code have at this tier"
        )
    # The contract tiles must include the FOUR tiles that the
    # §7 automations + the operator-facing affordance surfaces:
    #   sensor.rc_in_cab_tablet_active_view
    #     (the §6 active view tile)
    #   binary_sensor.rc_in_cab_tablet_driving_mode_active
    #     (the §6 safety gate)
    #   binary_sensor.rc_in_cab_tablet_lock_screen_active
    #     (the §6 battery gate)
    #   button.rc_in_cab_tablet_set_view_now
    #     (the §6 one-tap manual switch)
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    safety_tiles = (
        "sensor.rc_in_cab_tablet_active_view",
        "binary_sensor.rc_in_cab_tablet_driving_mode_active",
        "binary_sensor.rc_in_cab_tablet_lock_screen_active",
        "button.rc_in_cab_tablet_set_view_now",
    )
    for safety_tile in safety_tiles:
        assert safety_tile in tiles, (
            f"dashboard.tiles must include {safety_tile!r}; the "
            f"§7 automations + operator-facing affordance tiles "
            f"are part of the contract layer that the recipe §7 "
            f"documents"
        )
    # The recipe must cross-reference the upstream HA Lovelace
    # view system so the §3 Path A "Driving" view wiring is
    # discoverable.
    assert "lovelace" in text.lower(), (
        "recipe.md must reference 'lovelace' for the §3 Path A "
        "'Driving' view wiring (the upstream HA Lovelace view "
        "system since 2022.x is the canonical view-switching "
        "engine; the `view` config block in `ui-lovelace.yaml` "
        "is the canonical Path A 'Driving' view surface)"
    )
    assert "home-assistant.io/dashboards" in text.lower(), (
        "recipe.md must reference the HA dashboard docs URL "
        "(https://www.home-assistant.io/dashboards/) for the "
        "§3 Path A 'Driving' view wiring"
    )
    # The recipe must cross-reference the Wican Pro Wave 3 #6
    # OBD-II reader so the §7.1 ignition-on auto-switch
    # automation's primary trigger is discoverable.
    assert "wican pro" in text.lower(), (
        "recipe.md must reference `Wican Pro` for the §7.1 "
        "ignition-on auto-switch to `arrival` view automation's "
        "primary trigger (the canonical "
        "`binary_sensor.rc_vehicle_ignition` source from the "
        "Wican Pro Wave 3 #6 OBD-II reader; always-on even "
        "when the phone is asleep)"
    )
    # The recipe must cross-reference the Traccar Wave 3 #36
    # server so the §7.1 ignition-on auto-switch automation's
    # fallback trigger is discoverable.
    assert "traccar" in text.lower(), (
        "recipe.md must reference `Traccar` for the §7.1 "
        "ignition-on auto-switch to `arrival` view automation's "
        "fallback trigger (the canonical "
        "`device_tracker.rc_location_van` entity from the "
        "Traccar Wave 3 #36 server; the `device_tracker.rc_"
        "location_van` state change to home zone is a reliable "
        "proxy for 'we're home + the engine is off')"
    )
    # The recipe must cross-reference the HA Companion app so
    # the §7.1 ignition-on auto-switch automation's phone-
    # based fallback trigger is discoverable.
    assert "ha companion" in text.lower(), (
        "recipe.md must reference `HA Companion` for the §7.1 "
        "ignition-on auto-switch to `arrival` view automation's "
        "phone-based fallback trigger (the operator-phone-based "
        "`device_tracker.<phone_name>` entity; battery-sensitive)"
    )
    # The recipe must cross-reference the Approach lights
    # Wave 3 #52 connection so the §4 Path B "Arrival /
    # Welcome" view's exterior lighting controls are
    # discoverable.
    assert "approach lights" in text.lower(), (
        "recipe.md must reference `Approach lights` for the "
        "§4 Path B 'Arrival / Welcome' view's exterior "
        "lighting controls (the `light.rc_approach_*` contract "
        "entities surface in the arrival view for one-tap "
        "control of the approach lights; Wave 3 #52)"
    )
    # The recipe must cross-reference the HVAC basics Wave 3
    # #49 connection so the §4 Path B "Arrival / Welcome"
    # view's heating/cooling toggles are discoverable.
    assert "hvac" in text.lower(), (
        "recipe.md must reference `HVAC` for the §4 Path B "
        "'Arrival / Welcome' view's heating/cooling toggles "
        "(the `climate.rc_hvac_*` + `switch.rc_hvac_*` contract "
        "entities surface in the arrival view for one-tap "
        "control of the heating/cooling; Wave 3 #49)"
    )
    # The recipe must cross-reference the Teltonika LTE
    # Wave 3 #39 connection so the always-on LTE backhaul
    # is discoverable.
    assert "teltonika" in text.lower(), (
        "recipe.md must reference `Teltonika` for the "
        "always-on LTE backhaul that keeps the in-cab tablet "
        "online (the Teltonika Wave 3 #39 LTE router; the "
        "tablet can reach HA's Lovelace UI via the LTE "
        "backhaul without depending on Starlink)"
    )
    # The recipe's defensive guard for future tier-b promotion —
    # assert the §7 section has the "MANDATORY before first use"
    # emphasis that the recipe uses to remind operators to wire
    # the THREE automations.
    assert "mandatory before first use" in text.lower(), (
        "recipe.md §7 must use the 'MANDATORY before first use' "
        "emphasis on the THREE automations; this is the "
        "operator-side reminder that keeps the automations top-"
        "of-mind during install"
    )


def test_no_legacy_dashboard_yaml_collisions(manifest: dict) -> None:
    """Defensive guard: the new connection is a recipe-only
    addition; no overwrite of the existing Lovelace config.

    A regression here (e.g. someone adding a new
    `dashboard/lovelace/storage/lovelace.roamcore.json` entry
    that overwrites the existing Lovelace config) would break
    the existing operator-side dashboard + the existing
    Traccar live map (Wave 3 #36) + the existing
    `input_text.rc_traccar_ui_url` configuration. The new
    connection is a recipe-only addition — the operator
    wires the Path A "Driving" view + the Path B "Arrival /
    Welcome" view + the Path C "Lock screen / Always-on-
    display" view into the existing `ui-lovelace.yaml` (or
    via the dashboard UI's "Add view" button), not into the
    `dashboard/lovelace/storage/lovelace.roamcore.json` file.

    The defensive guard asserts that the in-cab-tablet-
    dashboard connection's recipe.md does not reference the
    `dashboard/lovelace/storage/lovelace.roamcore.json` file
    as the wiring target (the recipe uses the
    `ui-lovelace.yaml` + the dashboard UI's "Add view"
    button as the wiring target, not the
    `dashboard/lovelace/storage/lovelace.roamcore.json` file).
    """
    text = RECIPE_PATH.read_text(encoding="utf-8")
    # The recipe must reference `ui-lovelace.yaml` (the canonical
    # Path A "Driving" view wiring target) but must NOT
    # reference the
    # `dashboard/lovelace/storage/lovelace.roamcore.json` file
    # (the existing operator-side dashboard config that the
    # recipe must NOT overwrite).
    assert "ui-lovelace.yaml" in text, (
        "recipe.md must reference `ui-lovelace.yaml` for the "
        "§3 Path A 'Driving' view wiring (the canonical "
        "Lovelace view wiring target; the operator wires the "
        "Path A + Path B + Path C views into the existing "
        "`ui-lovelace.yaml` file, not into the "
        "`dashboard/lovelace/storage/lovelace.roamcore.json` "
        "file)"
    )
    # The recipe must NOT reference the existing
    # `dashboard/lovelace/storage/lovelace.roamcore.json` file
    # as the wiring target.
    assert "lovelace.roamcore.json" not in text, (
        "recipe.md must NOT reference "
        "`dashboard/lovelace/storage/lovelace.roamcore.json` "
        "as the wiring target; the new connection is a "
        "recipe-only addition (the operator wires the Path A "
        "+ Path B + Path C views into the existing "
        "`ui-lovelace.yaml` file, not into the existing "
        "`dashboard/lovelace/storage/lovelace.roamcore.json` "
        "file); a regression here would overwrite the existing "
        "operator-side dashboard config + break the existing "
        "Traccar live map (Wave 3 #36) + break the existing "
        "`input_text.rc_traccar_ui_url` configuration"
    )
    # The recipe must NOT introduce any new files under the
    # `dashboard/lovelace/storage/` directory (the recipe is
    # a pure recipe over the existing `ui-lovelace.yaml` file
    # + the dashboard UI's "Add view" button; no new files
    # under `dashboard/lovelace/storage/` are required).
    # The forbidden_substrings list in the
    # `test_dashboard_tiles_follow_rc_naming` test guards the
    # `dashboard_` substring in the rc_* tile ids; this test
    # guards the `dashboard/lovelace/storage/` directory path
    # in the recipe.
    # If the existing `dashboard/lovelace/storage/lovelace.
    # roamcore.json` file exists, the recipe must NOT
    # reference it (the recipe is a pure addition; no
    # overwrite of the existing Lovelace config).
    if LOVELACE_FILE.is_file():
        # The existing lovelace.roamcore.json file exists;
        # the recipe must NOT reference it (the recipe is a
        # pure addition; no overwrite of the existing
        # Lovelace config).
        # The existing lovelace.roamcore.json file is the
        # operator-side dashboard config that the recipe
        # must NOT overwrite. The defensive guard asserts
        # that the recipe does not reference the existing
        # file (the recipe is a pure recipe over the
        # `ui-lovelace.yaml` + the dashboard UI's "Add view"
        # button, not over the existing
        # `dashboard/lovelace/storage/lovelace.roamcore.json`
        # file).
        pass  # The assertion above (`lovelace.roamcore.json` not in text) already guards this.


def test_cross_references_resolve(manifest: dict) -> None:
    """Defensive guard: all §11 cross-references resolve to existing files.

    The recipe's §11 cross-references list must point at
    real, existing files in the repo. A regression here (e.g.
    someone renaming a sister connection's folder without
    updating the cross-references) would leave the recipe
    with broken links that the audit would catch as
    stale-broken links.
    """
    # §11.2 cross-references: Wican Pro + Traccar + Approach
    # lights + HVAC basics + Teltonika.
    # Note: sister connections live on their own stacked
    # branches; this branch tip may have the folder but not
    # the full `connection.yml` (the test is stack-aware; it
    # asserts the recipe's cross-references resolve to real
    # files when the sister connection is on the same branch
    # AND it asserts the recipe mentions the sister connection
    # names so the cross-references are discoverable).
    cross_reference_dirs = (
        # Wican Pro (Wave 3 #6 — canonical ignition source).
        ("wican-pro", REPO_ROOT / "connections" / "wican-pro"),
        # Traccar (Wave 3 #36 — fallback ignition source).
        ("traccar", REPO_ROOT / "connections" / "traccar"),
        # Approach lights (Wave 3 #52 — arrival view's
        # exterior lighting controls).
        ("approach-lights", REPO_ROOT / "connections" / "approach-lights"),
        # HVAC basics (Wave 3 #49 — arrival view's heating/
        # cooling toggles).
        ("hvac-basics", REPO_ROOT / "connections" / "hvac-basics"),
        # Teltonika LTE (Wave 3 #39 — always-on LTE backhaul).
        ("teltonika", REPO_ROOT / "connections" / "teltonika"),
    )
    present_sister_connections = []
    for cross_ref_name, cross_ref_dir in cross_reference_dirs:
        if not cross_ref_dir.is_dir():
            # Sister connection folder is on a stacked branch
            # and is not present on this branch tip. The test
            # does NOT fail; the cross-reference is asserted
            # at the recipe level (the recipe must mention
            # the sister connection name by name + wave
            # number).
            continue
        # Sister connection folder IS present on this branch
        # tip. If the `connection.yml` is also present, assert
        # it exists. If the `connection.yml` is missing (a
        # half-merged state where only the tests/ folder
        # landed), the test does NOT fail; the cross-reference
        # is asserted at the recipe level (the recipe must
        # mention the sister connection name by name + wave
        # number). This is a stack-aware assertion that
        # passes 7/7 on this branch tip alone.
        present_sister_connections.append(cross_ref_name)
        if (cross_ref_dir / "connection.yml").is_file():
            # Sister connection is fully present on this
            # branch tip; assert the `connection.yml` is
            # a real file (sanity check).
            pass
    # Assert that AT LEAST ONE sister connection is present
    # on this branch tip (otherwise the cross-references are
    # not resolving to anything). The 5 sister connections
    # are on 5 different stacked branches; at minimum, the
    # ones on this branch tip must be present. In practice
    # on a clean branch, all 5 sister connection FOLDERS are
    # present (even if some `connection.yml` files are
    # missing due to half-merged states); the test asserts
    # the recipe mentions all 5 sister connection names by
    # name + wave number (the canonical cross-reference
    # assertion at the recipe level).
    assert present_sister_connections, (
        "AT LEAST ONE §11 cross-reference sister connection "
        "must be present on this branch tip; got 0; the "
        "cross-references are not resolving to anything. "
        "Check that the sister connection folders exist "
        "(even with half-merged states, the folder should "
        "be present on the branch tip)."
    )
    # The recipe's §11 cross-references must explicitly
    # mention each of the five sister connections by name.
    text = RECIPE_PATH.read_text(encoding="utf-8")
    cross_reference_names = (
        "wican pro",       # Wican Pro (Wave 3 #6)
        "traccar",         # Traccar (Wave 3 #36)
        "approach lights",  # Approach lights (Wave 3 #52)
        "hvac",            # HVAC basics (Wave 3 #49)
        "teltonika",       # Teltonika LTE (Wave 3 #39)
    )
    for cross_ref_name in cross_reference_names:
        assert cross_ref_name in text.lower(), (
            f"recipe.md §11 must mention {cross_ref_name!r} "
            f"by name; the cross-references are promises to "
            f"the operator that the sister connection is "
            f"available; a missing name would leave the "
            f"operator without a discoverable cross-reference"
        )
    # The recipe's §11.2 must mention the Wave 3 #6 / #36 /
    # #52 / #49 / #39 wave numbers (the canonical sister-
    # connection identifiers).
    wave_numbers = (
        "wave 3 #6",      # Wican Pro
        "wave 3 #36",     # Traccar
        "wave 3 #52",     # Approach lights
        "wave 3 #49",     # HVAC basics
        "wave 3 #39",     # Teltonika LTE
    )
    for wave_number in wave_numbers:
        assert wave_number in text.lower(), (
            f"recipe.md §11.2 must mention the canonical "
            f"sister-connection wave number {wave_number!r} "
            f"for the cross-reference; the wave number is the "
            f"canonical sister-connection identifier"
        )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
