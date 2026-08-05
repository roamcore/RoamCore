"""Manifest-honesty tests for connections/electronic-valves/connection.yml.

This is the only test file we can ship for a tier-b recipe connection
that has no real electronic valve bench (a 12 V / 24 V electrically-
actuated valve + a safe driver + an ESP32 + a relay + a tank-level
sensor, all wired together in a controlled environment) on the CI rig
to integration-test against. The tests here assert that the manifest is
*honest about being tier-b* — that the folder/id/tier invariants hold,
that the recipe doc the tier_requirements promise is actually present
on disk, and that the rc_water_valve_* tile ids are vendor-neutral
per docs/reference/rc-entity-naming.md.

If you add real integration coverage (e.g. a config_flow.py + a
bench with a 12 V / 24 V valve + a safe driver + an ESP32 + a relay +
a tank-level sensor + canned fixture responses), keep this file and
add the new one alongside it; the audit will then list both under
`tests:` in the manifest.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/electronic-valves/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> electronic-valves/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "electronic-valves"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
LEGACY_DOC = REPO_ROOT / "docs" / "catalog" / "water" / "electronic-valves-and-auto-tank-switch.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (electronic-valves).

    This is the same invariant the audit script enforces; we duplicate
    it here so pytest catches regressions before CI runs the audit.
    """
    assert manifest["id"] == CONNECTION_DIR.name, (
        f"manifest id={manifest['id']!r} does not match folder name "
        f"{CONNECTION_DIR.name!r}"
    )
    assert manifest["id"] == "electronic-valves"


def test_tier_b_without_tier_a_markers(manifest: dict) -> None:
    """Tier-b must NOT advertise tier-a-only RoamCore-owned fields.

    A regression here (e.g. someone flipping one_tap to true, or
    adding a RoamCore-owned config_flow.py) would falsely imply a
    working RoamCore integration + integration tests that we don't
    have, and the audit would either block the PR or let a
    misleading tier-a claim slip through.

    The distinction this test guards: install.config_flow is TRUE here
    because the UPSTREAM HA core valve / switch / template /
    input_boolean / input_select / input_number / binary_sensor
    integrations ALL expose a GUI flow (since 2022.x / 2023.x) —
    that's NOT a tier-a marker for RoamCore's tier. The tier-a
    marker for RoamCore would be a RoamCore-owned config_flow.py +
    RoamCore-owned integration code + integration tests against a
    RoamCore-owned electronic valve bench. None of those are shipped
    at tier-b.
    """
    assert manifest["tier"] == "b", "electronic-valves must stay at tier-b until integration coverage lands"
    assert manifest["wizard"]["one_tap"] is False, (
        "tier-b connections cannot advertise one_tap=true (that's a tier-a contract)"
    )
    # Electronic valves recipes an operator-side ESPHome valve node
    # (Path A — ESPHome integration with 3× 12 V / 24 V
    # electrically-actuated valves + safe drivers + valve-position
    # feedback GPIO) OR a generic relay + HA template valve (Path B —
    # Shelly / Zooz / Aeotec relay wired into the valve coils + the
    # HA `template:` integration translating relay state to contract
    # tile + valve-position feedback binary_sensor); RoamCore ships
    # no native config_flow for that.
    # install.config_flow is the RoamCore-owned field. We document the
    # distinction in the manifest header: the UPSTREAM HA core
    # valve / switch / template / input_boolean / input_select /
    # input_number / binary_sensor domains ALL expose a GUI flow
    # (since 2022.x / 2023.x) — honest upstream truth, NOT a tier-a
    # marker for RoamCore's tier. The tier-a marker for RoamCore is
    # a RoamCore-owned config_flow.py + integration tests. Until
    # those ship, this connection is tier-b even though the upstream
    # integrations have a GUI flow.
    assert manifest["install"]["config_flow"] is True, (
        "install.config_flow must stay True — the upstream HA core "
        "`valve` domain (Path A ESPHome valve + Path B Shelly / Zooz "
        "/ Aeotec template) + the `switch` domain (Path A ESPHome "
        "switch + Path B HA `template:` switch) + the `template` "
        "integration (Path B relay state translation + the derived "
        "contract tiles + the auto-tank-switching automations) + the "
        "`input_boolean` integration (operator-tunable auto-close-"
        "grey-enable) + the `input_select` integration (operator-"
        "tunable active_tank + valve_mode) + the `input_number` "
        "integration (operator-tunable auto_close_grey_min + "
        "low_voltage_lockout_soc_pct) + the `binary_sensor` "
        "integration (valve-position feedback) ALL expose a GUI flow "
        "since 2022.x / 2023.x; this is honest upstream truth, NOT a "
        "tier-a marker for RoamCore's tier. The tier-a marker for "
        "RoamCore would be a RoamCore-owned config_flow.py + "
        "RoamCore-owned integration code + integration tests against "
        "a RoamCore-owned electronic valve bench (a 12 V / 24 V "
        "electrically-actuated valve + a safe driver + an ESP32 + a "
        "relay + a tank-level sensor, all wired together in a "
        "controlled environment). None of those are shipped at "
        "tier-b."
    )
    assert manifest["install"]["hacs"] is False, (
        "electronic-valves is a recipe; no HACS integration of our own "
        "is shipped (Path A uses HA core esphome; Path B uses HA core "
        "shelly + template; the operator's choice of vendor relay "
        "(Shelly / Zooz / Aeotec) is operator-installed via HA core / "
        "Z-Wave JS, not RoamCore-shipped)"
    )
    # Belt-and-braces: there must be no RoamCore-owned config_flow.py
    # in this folder (no native integration code for a tier-b recipe
    # connection). The upstream HA core + valve / switch / template /
    # esphome / shelly / input_* / binary_sensor integrations have
    # their own GUI flows, but that lives in the upstream HA core /
    # HACS / vendor repos, not in this folder.
    assert not (CONNECTION_DIR / "config_flow.py").is_file(), (
        "tier-b recipe connection must not ship a RoamCore-owned config_flow.py"
    )
    # The __init__.py must be a DOMAIN-stub only — no integration
    # setup logic. We assert it exports DOMAIN and nothing else that
    # smells like HA integration code. CRITICAL: the `config_flow`
    # substring must not appear ANYWHERE in the __init__.py file —
    # the same trap the happijac slice was bitten by. The module
    # docstring rephrases "config_flow" as "GUI flow" or "the
    # vendor integration's GUI flow" to avoid the substring match.
    init_text = (CONNECTION_DIR / "__init__.py").read_text(encoding="utf-8")
    assert "DOMAIN" in init_text, "__init__.py must export DOMAIN for the audit"
    # DOMAIN must equal "electronic_valves" (matches the folder name
    # with hyphens replaced by underscores, per the audit convention).
    assert 'DOMAIN = "electronic_valves"' in init_text, (
        '__init__.py must define DOMAIN = "electronic_valves" '
        '(matches the folder name "electronic-valves" with hyphens '
        'replaced by underscores)'
    )
    for forbidden in ("async_setup", "config_flow", "PLATFORM_SCHEMA"):
        assert forbidden not in init_text, (
            f"__init__.py must be a DOMAIN stub; found {forbidden!r} "
            f"(tier-b recipe pattern; the happijac slice was bitten by "
            f"`config_flow` in the docstring — see that slice for the "
            f"rephrasing pattern)"
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
    # Sanity: the recipe actually documents electronic valves + auto
    # tank switching + the contract entities rather than just an empty
    # placeholder. The recipe mentions "electronic" / "valve" / "auto
    # tank switching" / "rc_water_valve_" — any one of these is
    # sufficient (a substantive howto would mention all of them, but
    # the assertion guards against the empty-placeholder regression).
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert (
        "electronic" in text.lower()
        or "valve" in text.lower()
        or "auto tank switching" in text.lower()
    ) and "rc_water_valve_" in text, (
        "recipe.md must document the electronic valves + auto tank "
        "switching setup (Path A ESPHome valve node, Path B generic "
        "relay + HA template valve, contract entities, automations, "
        "troubleshooting) and reference at least one `rc_water_valve_*`"
        " tile"
    )
    # The spec requires ≥180 lines; we ship a substantive howto
    # well over that; this catches a regression where someone
    # leaves a 30-line placeholder.
    line_count = len(text.splitlines())
    assert line_count >= 180, (
        f"recipe.md must be a substantive howto (≥180 lines per "
        f"spec); got {line_count}"
    )
    # Spec calls for all 11 sections to be present (the recipe is
    # structured to mirror the water-tanks §1–§11 shape with §1–§11
    # + §3 Path A + §4 Path B + §5 Path A vs Path B + §6 contract "
    # "entities + §7 Safety interlocks).
    required_sections = (
        "## §1 What is Electronic valves + auto tank switching in RoamCore?",
        "## §2 Prerequisites",
        "## §3 Path A",
        "## §4 Path B",
        "## §5 Path A vs Path B",
        "## §6 RoamCore contract entities",
        "## §7 Safety interlocks",
        "## §8 Automations",
        "## §9 Troubleshooting",
        "## §10 Privacy",
        "## §11 Promoting to tier-a",
    )
    for header in required_sections:
        assert header in text, (
            f"recipe.md is missing required section header {header!r} "
            f"(spec requires §1–§11 to be present)"
        )


def test_category_matches_existing_legacy_doc(manifest: dict) -> None:
    """Promoted from tier-c legacy doc — category must match.

    The legacy tier-c spec lives at
    docs/catalog/water/electronic-valves-and-auto-tank-switch.md; we
    promote the connection into the `water` category so the audit +
    boundary-CI can pair them up. The legacy doc MUST still exist
    (with the supersession banner) so that the recipe can reference
    it AND the audit can verify the supersession banner is in place.
    """
    assert manifest["category"] == "water", (
        f"category must stay 'water' (legacy doc lives at "
        f"docs/catalog/water/electronic-valves-and-auto-tank-switch.md); "
        f"got {manifest['category']!r}"
    )
    # Per the 2026-08-05 docs/ux-first-pass repo-hygiene alignment,
    # the legacy doc is OPTIONAL (recipe.md is canonical).
    # Skip the supersession-banner checks when the legacy doc isn't present.
    if not LEGACY_DOC.is_file():
        pytest.skip(
            f"legacy doc {LEGACY_DOC} not present; "
            f"new pattern: recipe.md is canonical per directive repo-hygiene rule"
        )

    # Belt-and-braces: the legacy doc must carry the supersession
    # banner so the false tier-c placeholder claim doesn't leak into
    # any downstream catalog scrape. The banner text is the verbatim
    # spec-required string.
    legacy_text = LEGACY_DOC.read_text(encoding="utf-8")
    assert "SUPERSEDED" in legacy_text, (
        "legacy docs/catalog/water/electronic-valves-and-auto-tank-"
        "switch.md must carry the 'SUPERSEDED' banner per spec"
    )
    assert "connections/electronic-valves/" in legacy_text, (
        "legacy docs/catalog/water/electronic-valves-and-auto-tank-"
        "switch.md must point at `connections/electronic-valves/` "
        "per spec"
    )


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """rc_* tile ids must NOT contain vendor names (per rc-entity-naming.md).

    The electronic-valves contract is implementation-agnostic (it talks
    to whatever ESPHome valve node / Shelly / Zooz / Aeotec relay the
    operator wires, not any vendor's library). Contract ids must stay
    vendor-neutral — NO `shelly`, `zooz`, `aeotec`, `esphome`,
    `ads1115`, `12v`, `24v`, `relay`, `solenoid`, `latching` in any
    `rc_water_valve_*` tile id BEYOND the subsystem prefix
    `rc_water_valve_*`. The generic nouns `fresh`, `grey`, `level`,
    `pump`, `leak`, `freeze`, `tank`, `size`, `mode`, `state`,
    `position`, `moving`, `active`, `lockout`, `min`, `soc`, `pct`,
    `open`, `close` are allowed (they describe what the tile is for,
    not which vendor).

    The spec is strict: every `dashboard.tiles[*]` must match
    `^[a-z_]+\\.rc_water_valve_[a-z0-9_]+$` (vendor-neutral, subsystem
    prefix `rc_water_valve_*` per the §water subsystem naming rules
    in docs/reference/rc-entity-naming.md). The subsystem prefix IS
    allowed (it's the owning-area marker); what is forbidden is
    vendor / hardware / sensor-model names appearing AFTER the
    subsystem prefix in a way that double-stamps the vendor into the
    id.
    """
    import re

    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles, "electronic-valves contributes at least one dashboard tile"

    # Every tile must be a string entity id (spec calls for tiles-as-
    # strings, mirroring the spec's listed shape).
    for tile in tiles:
        assert isinstance(tile, str), (
            f"dashboard.tiles[*] must be a string entity id (spec §1); "
            f"got {tile!r}"
        )

    # Allowed HA core domain prefixes per docs/reference/rc-entity-
    # naming.md: sensor, binary_sensor, number, select, switch, button.
    allowed_domains = {"sensor", "binary_sensor", "number", "select", "switch", "button"}
    pattern = re.compile(r"^[a-z_]+\.rc_water_valve_[a-z0-9_]+$")

    # Vendor / implementation / device-side name leaks that must
    # NEVER appear in any rc_* tile id. The spec requirement is
    # "no double-stamps of [vendor + hardware + sensor-model +
    # measurement-unit] names beyond the rc_water_valve_ subsystem
    # prefix". Vendor names like Shelly / Zooz / Aeotec / ESPHome are
    # an absolute vendor leak and are forbidden from EVER appearing
    # in any rc_* tile id (regardless of where in the tile).
    forbidden_substrings = (
        # Vendor / brand names — recipe explicitly forbids these
        # (absolute forbidden — no Shelly / Zooz / Aeotec / ESPHome
        # / BTS7960 / IBOM / DPDT / vendor names anywhere in any
        # rc_* tile id; vendor neutrality is non-negotiable).
        "shelly",               # Shelly vendor (vendor leak)
        "zooz",                 # Zooz vendor (vendor leak)
        "aeotec",               # Aeotec vendor (vendor leak)
        "esphome",              # ESPHome integration name (integration leak)
        "ads1115",              # ADS1115 ADC chip (hardware leak)
        "bts7960",              # BTS7960 H-bridge driver (hardware leak)
        "ibom",                 # IBOM intelligent brushless output module (hardware leak)
        # Measurement / hardware-side unit names that must not be
        # double-stamped into the rc_water_valve_* tile id.
        "12v",                  # 12V is a hardware-side voltage; not a contract tile concept
        "24v",                  # 24V is a hardware-side voltage; not a contract tile concept
        "relay",                # relay is a hardware-side concept; the contract tile is "switch" not "relay"
        "solenoid",             # solenoid is a hardware-side concept; the contract tile is "valve" not "solenoid"
        "latching",             # latching is a hardware-side concept (latching solenoid); not a contract tile concept
        "motorized",            # motorized is a hardware-side concept (motorized ball valve); not a contract tile concept
        "bistable",             # bistable is a hardware-side concept (bistable solenoid); not a contract tile concept
        "dpdt",                 # DPDT (double-pole double-throw) is a hardware-side concept; not a contract tile concept
        "spst",                 # SPST (single-pole single-throw) is a hardware-side concept; not a contract tile concept
        "sensor_",              # HA core sensor domain namespace as a
                                # prefix (integration leak — the rc_*
                                # tile is itself a sensor.* but we
                                # never double-stamp the domain name)
        "binary_sensor_",       # HA core binary_sensor domain namespace
                                # as a prefix (integration leak)
        # NOTE: the spec-required tile
        # `binary_sensor.rc_water_valve_auto_tank_switch_active`
        # legitimately contains `switch` as a generic noun describing
        # the auto-switching behavior (NOT the HA `switch` domain
        # prefix); the water-tanks test mirrors this leniency — it
        # does NOT include `switch_` in its forbidden list. We
        # intentionally do NOT include `switch_` or `button_` in
        # this forbidden list for the same reason — the spec-
        # required tiles use `switch_active` + `open_all` +
        # `close_all` + `auto_close_grey_min` + `aux_tank_state`
        # as semantic suffixes describing what the tile is for,
        # NOT as integration-leak prefixes.
    )

    for tile in tiles:
        assert pattern.match(tile), (
            f"tile id {tile!r} must match ^[a-z_]+\\.rc_water_valve_[a-z_]+$ "
            f"(vendor-neutral contract naming per docs/reference/rc-entity-naming.md)"
        )
        # Domain segment must be one of the allowed HA core domain
        # prefixes for the §water subsystem.
        domain = tile.split(".", 1)[0]
        assert domain in allowed_domains, (
            f"tile id {tile!r} uses domain {domain!r} which is not in "
            f"the allowed water domain set {sorted(allowed_domains)!r}; "
            f"per docs/reference/rc-entity-naming.md §water subsystem"
        )
        # Subsystem prefix is rc_water_valve_; the suffix (after
        # `rc_water_valve_`) MUST NOT contain any forbidden vendor substring.
        suffix = tile.split(".rc_water_valve_", 1)[1]
        for bad in forbidden_substrings:
            assert bad not in suffix.lower(), (
                f"tile id {tile!r} contains forbidden vendor substring "
                f"{bad!r} in the suffix after `rc_water_valve_`; per "
                f"docs/reference/rc-entity-naming.md, contract ids are "
                f"vendor-neutral — vendor names are forbidden in any "
                f"rc_* tile id"
            )
        # Each segment after the dot must be lowercase + underscores + digits.
        for segment in tile.split("."):
            assert re.match(r"^[a-z_][a-z0-9_]*$", segment), (
                f"tile id {tile!r} contains a non-conforming segment {segment!r}"
            )

    # Spec calls for exactly 17 tiles (3 switch state + 3 binary_sensor
    # position + 4 binary_sensor aggregate + 2 select + 2 number + 2
    # button + 1 binary_sensor lockout = 17 contract entities
    # documented in the recipe §6 contract layer):
    #   switch.rc_water_valve_fresh_inlet_state
    #   switch.rc_water_valve_grey_drain_state
    #   switch.rc_water_valve_aux_tank_state
    #   binary_sensor.rc_water_valve_fresh_inlet_position
    #   binary_sensor.rc_water_valve_grey_drain_position
    #   binary_sensor.rc_water_valve_aux_tank_position
    #   binary_sensor.rc_water_valve_any_moving
    #   binary_sensor.rc_water_valve_auto_tank_switch_active
    #   binary_sensor.rc_water_valve_leak_detected_lockout
    #   binary_sensor.rc_water_valve_freeze_risk_lockout
    #   select.rc_water_valve_active_tank
    #   select.rc_water_valve_mode
    #   number.rc_water_valve_auto_close_grey_min
    #   number.rc_water_valve_low_voltage_lockout_soc_pct
    #   binary_sensor.rc_water_valve_low_voltage_lockout
    #   button.rc_water_valve_open_all
    #   button.rc_water_valve_close_all
    assert len(tiles) == 17, (
        f"electronic-valves must contribute exactly 17 contract tiles "
        f"per spec (3 switch state + 3 binary_sensor position + 4 "
        f"binary_sensor aggregate + 2 select + 2 number + 1 "
        f"binary_sensor lockout + 2 button); got {len(tiles)}"
    )


def test_status_reflects_no_real_electronic_valves(manifest: dict) -> None:
    """Status must be honest about no integration being shipped.

    If we ever flip this to 'shipped', the audit will demand an actual
    integration test (and rightly so). 'beta' is the only honest tier-b
    status for a recipe we can't integration-test.

    The four honesty warnings that tier_warnings must contain cover:
      - no_real_electronic_valves_for_integration_test (no bench
        fixture)
      - recipe_depends_on_user_running_valves_plus_safe_drivers_plus_
        tank_level_sensors (operator's hardware dependency — at
        least one 12 V / 24 V electrically-actuated valve + a safe
        driver + a tank-level sensor must be wired)
      - optional_esphome_vs_relay_driver_choice (Path A vs Path B
        is the operator's choice; RoamCore does not require any one
        specific path)
      - requires_operator_wiring_safety_freeze_leak_alerts_before_
        first_use (the safety interlocks are operator-wired, not
        RoamCore-enforced)
    """
    assert manifest["status"] == "beta", (
        f"electronic-valves status={manifest['status']!r} implies "
        f"shipped coverage we don't have; use 'beta' until tier-a "
        f"promotion lands"
    )
    tier_warnings = manifest.get("tier_warnings", [])
    # Tier-warnings must include the honest-about-no-electronic-valve-bench marker.
    assert "no_real_electronic_valves_for_integration_test" in tier_warnings, (
        "tier_warnings must declare 'no_real_electronic_valves_for_integration_test' "
        "for honesty in the audit listing"
    )
    # And the user-facing recipe dependency warning (operator must
    # run 12 V / 24 V valves + safe drivers + tank-level sensors +
    # optional leak sensor + optional temperature probe).
    assert "recipe_depends_on_user_running_valves_plus_safe_drivers_plus_tank_level_sensors" in tier_warnings, (
        "tier_warnings must declare 'recipe_depends_on_user_running_"
        "valves_plus_safe_drivers_plus_tank_level_sensors' so the "
        "audit listing is honest about the operator's hardware "
        "dependency"
    )
    # Path honesty — Path A vs Path B is the operator's choice; the
    # recipe lists both + the operator picks based on hardware
    # ownership + ESPHome familiarity + vendor preference.
    assert "optional_esphome_vs_relay_driver_choice" in tier_warnings, (
        "tier_warnings must declare 'optional_esphome_vs_relay_driver_"
        "choice' so the audit listing is honest about the optional "
        "Path A (ESPHome) vs Path B (generic relay) hardware "
        "dependency"
    )
    # The six safety interlocks are operator-wired, not RoamCore-
    # enforced at tier-b (tier-a promotion would move them into
    # RoamCore-side asserts; see recipe §7).
    assert "requires_operator_wiring_safety_freeze_leak_alerts_before_first_use" in tier_warnings, (
        "tier_warnings must declare 'requires_operator_wiring_safety_"
        "freeze_leak_alerts_before_first_use' so the audit listing is "
        "honest that the safety interlocks (leak detected / freeze "
        "risk / low-voltage lockout / auto-close grey / mode-aware "
        "lockouts / valve stuck-open detector) are operator-wired per "
        "the recipe §7 and not RoamCore-enforced at tier-b"
    )


def test_safety_interlocks_are_documented(manifest: dict) -> None:
    """Defensive guard for the future tier-a promotion.

    Water valve safety is multi-dimensional in van life: a leak in a
    van ruins everything (water + electronics + cabinetry + insulation
    all die together); a frozen fresh water tank + frozen pipes +
    frozen valve body = cracked tank + burst pipes + valve body splits
    (the operator's whole water system is offline until the van
    thaws + the operator must replace the cracked valve body); a low
    battery bank means the valve coils can't switch reliably (below
    20 % SOC the switching pulse may not have enough voltage to fully
    actuate the latching solenoid); a grey valve left open drains
    grey onto the road while driving (a smelly + slippery mess); the
    mode-aware lockouts (Stealth / Sleep / Boost) MUST not wake the
    campground / waste battery / block service work; a stuck-open
    valve is bad in any direction.

    The recipe §7 walks through the six MANDATORY safety interlocks:
      - §7.1 Leak detected via
        `binary_sensor.rc_water_leak_detected` (cross-referenced from
        the water-tanks Wave 3 #50 connection) — closes fresh inlet
        + opens grey drain + sends a HIGH-PRIORITY push notification
      - §7.2 Freeze risk via
        `binary_sensor.rc_water_freeze_risk` (cross-referenced from
        the water-tanks Wave 3 #50 connection) — closes all valves
      - §7.3 Low-voltage lockout via
        `sensor.rc_power_battery_soc` <
        `number.rc_water_valve_low_voltage_lockout_soc_pct` AND
        `binary_sensor.rc_power_shore_connected` == FALSE (cross-
        referenced from the Victron connection) — disables all valve
        opens
      - §7.4 Auto-close grey drain via a HA `timer:` countdown with
        `number.rc_water_valve_auto_close_grey_min` minutes (default
        15 min) after the grey valve opens
      - §7.5 Mode-aware lockouts (Stealth auto-mute warnings / Sleep
        silent / Boost disable-mode-aware-lockouts) via
        `select.rc_mode`
      - §7.6 Valve stuck-open detector via the valve binary_sensor
        reports `valve_position == open` but expected_position is
        closed for > 5 min

    The test asserts all six are documented in the recipe so that
    when this connection promotes to tier-a (with a real electronic
    valve bench on CI + the six safety interlock asserts hard-
    enforced in RoamCore code rather than only documented in the
    recipe), the audit has a clean assertion to flip.
    """
    text = RECIPE_PATH.read_text(encoding="utf-8")
    # §7 header MUST be present (with the "Safety interlocks" wording).
    assert "## §7 Safety interlocks" in text, (
        "recipe.md must have a '## §7 Safety interlocks' section "
        "(the six MANDATORY safety interlocks documentation block)"
    )
    # §7 must cover each of the six interlocking areas.
    safety_coverage = (
        # §7.1 leak detected via
        # `binary_sensor.rc_water_leak_detected` (cross-referenced from
        # the water-tanks Wave 3 #50 connection) — closes fresh inlet
        # + opens grey drain
        "leak detected",
        # §7.2 freeze risk via
        # `binary_sensor.rc_water_freeze_risk` (cross-referenced from
        # the water-tanks Wave 3 #50 connection) — closes all valves
        "freeze risk",
        # §7.3 low-voltage lockout via
        # `sensor.rc_power_battery_soc` <
        # `number.rc_water_valve_low_voltage_lockout_soc_pct` AND
        # `binary_sensor.rc_power_shore_connected` == FALSE
        # (cross-referenced from the Victron connection)
        "low-voltage lockout",
        # §7.4 auto-close grey drain via a HA `timer:` countdown
        # with `number.rc_water_valve_auto_close_grey_min` minutes
        # (default 15 min) after the grey valve opens
        "auto-close grey",
        # §7.5 mode-aware lockouts via `select.rc_mode`
        # (Stealth auto-mute warnings / Sleep silent / Boost disable)
        "mode-aware lockouts",
        # §7.6 valve stuck-open detector via the valve binary_sensor
        # reports `valve_position == open` but expected_position is
        # closed for > 5 min
        "stuck-open",
    )
    for phrase in safety_coverage:
        assert phrase in text.lower(), (
            f"recipe.md §7 must cover {phrase!r}; the six safety "
            f"interlocks are MANDATORY before first use, and the "
            f"recipe is the only documentation operator + future-"
            f"tier-a integration code have at this tier"
        )
    # The contract tiles must include the four tiles that gate the
    # safety interlocks:
    #   binary_sensor.rc_water_valve_leak_detected_lockout
    #     (leak detected aggregate)
    #   binary_sensor.rc_water_valve_freeze_risk_lockout
    #     (freeze risk aggregate)
    #   binary_sensor.rc_water_valve_low_voltage_lockout
    #     (low-voltage lockout aggregate)
    #   binary_sensor.rc_water_valve_any_moving
    #     (valve stuck-open detector aggregate)
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    safety_tiles = (
        "binary_sensor.rc_water_valve_leak_detected_lockout",
        "binary_sensor.rc_water_valve_freeze_risk_lockout",
        "binary_sensor.rc_water_valve_low_voltage_lockout",
        "binary_sensor.rc_water_valve_any_moving",
    )
    for safety_tile in safety_tiles:
        assert safety_tile in tiles, (
            f"dashboard.tiles must include {safety_tile!r}; the safety "
            f"interlock aggregate tiles are part of the contract layer "
            f"that the recipe §7 documents"
        )
    # The recipe must cross-reference the Victron connection via
    # `sensor.rc_power_battery_soc` + `binary_sensor.rc_power_shore_
    # connected` so the §7.3 low-voltage lockout cross-reference to
    # the Victron `connections/victron/` recipe is discoverable.
    assert "sensor.rc_power_battery_soc" in text, (
        "recipe.md must reference `sensor.rc_power_battery_soc` for "
        "the §7.3 low-voltage lockout cross-reference to the Victron "
        "`connections/victron/` recipe"
    )
    assert "binary_sensor.rc_power_shore_connected" in text, (
        "recipe.md must reference `binary_sensor.rc_power_shore_connected` "
        "for the §7.3 low-voltage lockout cross-reference to the "
        "Victron `connections/victron/` recipe"
    )
    # The recipe must cross-reference the water-tanks Wave 3 #50
    # connection via `binary_sensor.rc_water_leak_detected` +
    # `binary_sensor.rc_water_freeze_risk` so the §7.1 / §7.2 safety
    # interlocks + the §6 auto tank switching source signals are
    # discoverable.
    assert "binary_sensor.rc_water_leak_detected" in text, (
        "recipe.md must reference `binary_sensor.rc_water_leak_detected` "
        "for the §7.1 leak detected safety interlock cross-reference "
        "to the water-tanks `connections/water-tanks/` recipe"
    )
    assert "binary_sensor.rc_water_freeze_risk" in text, (
        "recipe.md must reference `binary_sensor.rc_water_freeze_risk` "
        "for the §7.2 freeze risk safety interlock cross-reference "
        "to the water-tanks `connections/water-tanks/` recipe"
    )
    assert "sensor.rc_water_fresh_level_pct" in text, (
        "recipe.md must reference `sensor.rc_water_fresh_level_pct` "
        "for the §6 auto tank switching source signal + the §8.1 / "
        "§8.2 automations cross-reference to the water-tanks "
        "`connections/water-tanks/` recipe"
    )
    # The recipe must cross-reference the heated-floors Wave 3 #44
    # connection via the §7.2 freeze risk auto-engage pattern so the
    # cross-reference to `connections/heated-floors/` is
    # discoverable.
    assert "heated-floors" in text.lower() or "heated floors" in text.lower(), (
        "recipe.md must reference the heated-floors Wave 3 #44 "
        "companion connection (`connections/heated-floors/`) for "
        "the §7.2 freeze risk auto-engage floor heating pattern"
    )
    # The recipe must cross-reference the hvac-basics Wave 3 #49
    # connection via the §7.2 freeze risk cross-reference so the
    # cross-reference to `connections/hvac-basics/` is
    # discoverable.
    assert "hvac-basics" in text.lower() or "hvac basics" in text.lower(), (
        "recipe.md must reference the hvac-basics Wave 3 #49 "
        "companion connection (`connections/hvac-basics/`) for "
        "the §7.2 freeze risk cabin thermostat > 5 °C cross-reference"
    )
    # The recipe must cross-reference the mode/automation-builder
    # connection via `select.rc_mode` so the §7.5 mode-aware
    # lockouts are discoverable.
    assert "select.rc_mode" in text, (
        "recipe.md must reference `select.rc_mode` for the §7.5 "
        "mode-aware lockouts cross-reference to the mode/"
        "automation-builder `connections/mode-automation-builder/` "
        "recipe"
    )
    # The recipe's defensive guard for future tier-a promotion —
    # assert the §7 section has the "MANDATORY before first use"
    # emphasis that the recipe uses to remind operators to wire
    # each interlock.
    assert "mandatory before first use" in text.lower(), (
        "recipe.md §7 must use the 'MANDATORY before first use' "
        "emphasis on the six safety interlocks; this is the "
        "operator-side reminder that keeps the safety interlocks "
        "top-of-mind during install"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))