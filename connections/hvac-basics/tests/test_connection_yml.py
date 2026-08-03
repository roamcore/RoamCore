"""Manifest-honesty tests for connections/hvac-basics/connection.yml.

This is the only test file we can ship for a tier-b recipe connection
that has no real HVAC bench (a thermostat + a heater + an AC + a fan +
a temperature/humidity sensor + a relay board) on the CI rig to
integration-test against. The tests here assert that the manifest is
*honest about being tier-b* — that the folder/id/tier invariants
hold, that the recipe doc the tier_requirements promise is actually
present on disk, and that the rc_hvac_* tile ids are vendor-neutral
per docs/reference/rc-entity-naming.md.

If you add real integration coverage (e.g. a config_flow.py + a
bench with a thermostat + a heater + an AC + a fan + canned fixture
responses), keep this file and add the new one alongside it; the
audit will then list both under `tests:` in the manifest.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/hvac-basics/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> hvac-basics/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "hvac-basics"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
LEGACY_DOC = REPO_ROOT / "docs" / "catalog" / "hvac" / "hvac-basics.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (hvac-basics).

    This is the same invariant the audit script enforces; we duplicate
    it here so pytest catches regressions before CI runs the audit.
    """
    assert manifest["id"] == CONNECTION_DIR.name, (
        f"manifest id={manifest['id']!r} does not match folder name "
        f"{CONNECTION_DIR.name!r}"
    )
    assert manifest["id"] == "hvac-basics"


def test_tier_b_without_tier_a_markers(manifest: dict) -> None:
    """Tier-b must NOT advertise tier-a-only RoamCore-owned fields.

    A regression here (e.g. someone flipping one_tap to true, or
    adding a RoamCore-owned config_flow.py) would falsely imply a
    working RoamCore integration + integration tests that we don't
    have, and the audit would either block the PR or let a
    misleading tier-a claim slip through.

    The distinction this test guards: install.config_flow is TRUE here
    because the UPSTREAM HA core climate / esphome / mqtt / broadlink /
    fan integrations all expose a GUI flow (since 2022.x / 2023.x) —
    that's NOT a tier-a marker for RoamCore's tier. The tier-a marker
    for RoamCore would be a RoamCore-owned `config_flow.py` +
    RoamCore-owned integration code + integration tests against a
    RoamCore-owned HVAC bench. None of those are shipped at tier-b.
    """
    assert manifest["tier"] == "b", "hvac-basics must stay at tier-b until integration coverage lands"
    assert manifest["wizard"]["one_tap"] is False, (
        "tier-b connections cannot advertise one_tap=true (that's a tier-a contract)"
    )
    # HVAC basics recipes an operator-side generic thermostat (Path A —
    # HA core generic_thermostat / ecobee / nest / mitsubishi / daikin
    # OR vendor integration's climate.* entity) OR a diesel heater
    # (Path B — ESPHome or MQTT bridge) OR a rooftop AC (Path C —
    # IR-bridge or native integration) OR a cabin fan (Path D — HA core
    # fan); RoamCore ships no native config_flow for that.
    # install.config_flow is the RoamCore-owned field. We document the
    # distinction in the manifest header: the UPSTREAM HA core climate
    # domain (generic_thermostat, ecobee, nest, mitsubishi, daikin) +
    # the ESPHome integration + the mqtt integration + the broadlink
    # integration + the fan integration ALL expose a GUI flow (since
    # 2022.x / 2023.x) — honest upstream truth, NOT a tier-a marker
    # for RoamCore's tier. The tier-a marker for RoamCore is a
    # RoamCore-owned config_flow.py + integration tests. Until those
    # ship, this connection is tier-b even though the upstream
    # integrations have a GUI flow.
    assert manifest["install"]["config_flow"] is True, (
        "install.config_flow must stay True — the upstream HA core "
        "`climate` domain (generic_thermostat / ecobee / nest / "
        "mitsubishi / daikin) + the `esphome` integration (Path B "
        "diesel heater) + the `mqtt` integration (MQTT-bridged "
        "heater) + the `broadlink` IR-bridge integration (Path C "
        "rooftop AC) + the `fan` integration (Path D cabin "
        "ventilation) ALL expose a GUI flow since 2022.x / 2023.x; "
        "this is honest upstream truth, NOT a tier-a marker for "
        "RoamCore's tier. The tier-a marker for RoamCore would be "
        "a RoamCore-owned `config_flow.py` + RoamCore-owned "
        "integration code + integration tests against a "
        "RoamCore-owned HVAC bench (a thermostat + a heater + an "
        "AC + a fan + a temperature/humidity sensor + a relay "
        "board, all wired together in a controlled environment). "
        "None of those are shipped at tier-b."
    )
    assert manifest["install"]["hacs"] is False, (
        "hvac-basics is a recipe; no HACS integration of our own is "
        "shipped (Path A uses generic_thermostat or vendor integration; "
        "Path B uses HA core esphome or mqtt; Path C uses HA core "
        "broadlink or HACS mqtt_ir_hub; Path D uses HA core fan)"
    )
    # Belt-and-braces: there must be no RoamCore-owned config_flow.py
    # in this folder (no native integration code for a tier-b recipe
    # connection). The upstream HA core + climate / esphome / mqtt /
    # broadlink / fan integrations have their own GUI flows, but that
    # lives in the upstream HA core / HACS / vendor repos, not in this
    # folder.
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
    # DOMAIN must equal "hvac_basics" (matches the folder name
    # with hyphens replaced by underscores, per the audit convention).
    assert 'DOMAIN = "hvac_basics"' in init_text, (
        '__init__.py must define DOMAIN = "hvac_basics" '
        '(matches the folder name "hvac-basics" with hyphens replaced by underscores)'
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
    # Sanity: the recipe actually documents HVAC basics + the contract
    # entities rather than just an empty placeholder. The recipe
    # mentions "hvac" / "climate" / "thermostat" / "rc_hvac_" — any
    # one of these is sufficient (a substantive howto would mention
    # all of them, but the assertion guards against the empty-
    # placeholder regression).
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert (
        "hvac" in text.lower()
        or "climate" in text.lower()
        or "thermostat" in text.lower()
    ) and "rc_hvac_" in text, (
        "recipe.md must document the HVAC basics setup (Path A "
        "generic thermostat, Path B diesel heater, Path C rooftop "
        "AC, Path D cabin ventilation, contract entities, "
        "automations, troubleshooting) and reference at least one "
        "`rc_hvac_*` tile"
    )
    # The spec requires ~280+ lines (≥280); we ship a substantive
    # howto well over that; this catches a regression where someone
    # leaves a 30-line placeholder.
    line_count = len(text.splitlines())
    assert line_count >= 280, (
        f"recipe.md must be a substantive howto (≥280 lines per "
        f"spec); got {line_count}"
    )
    # Spec calls for all 12 sections to be present (the recipe is the
    # umbrella for the 4 paths; the heated-floors companion has §1–§10;
    # the umbrella needs §1–§12 with the §11 Privacy + §12 Promoting
    # to tier-a sections included). Grep-anchor the major section
    # headers so a future "I rewrote the recipe as one wall of text"
    # regression gets caught.
    required_sections = (
        "## §1 What is HVAC basics in RoamCore?",
        "## §2 Prerequisites",
        "## §3 Path A",
        "## §4 Path B",
        "## §5 Path C",
        "## §6 Path D",
        "## §7 RoamCore contract entities",
        "## §8 Safety interlocks",
        "## §9 Automations",
        "## §10 Troubleshooting",
        "## §11 Privacy",
        "## §12 Promoting to tier-a",
    )
    for header in required_sections:
        assert header in text, (
            f"recipe.md is missing required section header {header!r} "
            f"(spec requires §1–§12 to be present)"
        )


def test_category_matches_existing_legacy_doc(manifest: dict) -> None:
    """Promoted from tier-c legacy doc — category must match.

    The legacy tier-c spec lives at
    docs/catalog/hvac/hvac-basics.md; we promote the connection into
    the `hvac` category so the audit + boundary-CI can pair them up.
    The legacy doc MUST still exist (with the supersession banner) so
    that the recipe can reference it AND the audit can verify the
    supersession banner is in place.
    """
    assert manifest["category"] == "hvac", (
        f"category must stay 'hvac' (legacy doc lives at "
        f"docs/catalog/hvac/hvac-basics.md); got {manifest['category']!r}"
    )
    assert LEGACY_DOC.is_file(), (
        "expected the legacy tier-c doc to still exist so we can "
        "reference it from the recipe (and add a supersession banner)"
    )
    # Belt-and-braces: the legacy doc must carry the supersession
    # banner so the false tier-a claim doesn't leak into any
    # downstream catalog scrape. The banner text is the verbatim
    # spec-required string.
    legacy_text = LEGACY_DOC.read_text(encoding="utf-8")
    assert "SUPERSEDED" in legacy_text, (
        "legacy docs/catalog/hvac/hvac-basics.md must carry the "
        "'SUPERSEDED' banner per spec"
    )
    assert "connections/hvac-basics/" in legacy_text, (
        "legacy docs/catalog/hvac/hvac-basics.md must point at "
        "`connections/hvac-basics/` per spec"
    )
    # The original false tier-a claim MUST be retracted (the
    # supersession banner replaces it).
    assert "Support tier: A" not in legacy_text or "retracted" in legacy_text.lower(), (
        "legacy docs/catalog/hvac/hvac-basics.md must retract the "
        "false 'Support tier: A' claim per spec (either remove the "
        "claim entirely OR carry the 'retracted' qualifier)"
    )


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """rc_* tile ids must NOT contain vendor names (per rc-entity-naming.md).

    The HVAC contract is implementation-agnostic (it talks to whatever
    generic thermostat / diesel heater ESPHome integration / IR-bridge
    AC / HA core fan the operator wires, not any vendor's library).
    Contract ids must stay vendor-neutral — NO `webasto`, `eberspaecher`,
    `eberspächer`, `furrion`, `dometic`, `maxxair`, `coleman`,
    `broadlink`, `generic_thermostat`, `ecobee`, `nest`, `mitsubishi`,
    `daikin` in any rc_* tile id BEYOND the subsystem prefix
    `rc_hvac_*`. The generic nouns `cabin`, `fan`, `heater`, `ac`,
    `cool`, `heat`, `temperature`, `humidity`, `outdoor`, `frost`,
    `over_temp`, `mode`, `speed`, `warning` are allowed (they describe
    what the tile is for, not which vendor).

    The spec is strict: every `dashboard.tiles[*]` must match
    `^[a-z_]+\\.rc_hvac_[a-z0-9_]+$` (vendor-neutral, subsystem
    prefix `rc_hvac_*` per the §hvac subsystem naming rules in
    docs/reference/rc-entity-naming.md). The subsystem prefix IS
    allowed (it's the owning-area marker); what is forbidden is
    vendor / hardware / climate-domain / generic_thermostat names
    appearing AFTER the subsystem prefix in a way that double-stamps
    the vendor into the id.
    """
    import re

    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles, "hvac-basics contributes at least one dashboard tile"

    # Every tile must be a string entity id (spec calls for tiles-as-
    # strings, mirroring the spec's listed shape).
    for tile in tiles:
        assert isinstance(tile, str), (
            f"dashboard.tiles[*] must be a string entity id (spec §1); "
            f"got {tile!r}"
        )

    # Allowed HA core domain prefixes per docs/reference/rc-entity-
    # naming.md: climate, sensor, binary_sensor, fan, select.
    # switch is NOT in this connection (the deadbolts connection uses
    # switch.* for the lock entities; HVAC basics uses fan.* for the
    # cabin fan + climate.* for the thermostat; the heater + AC
    # activity tiles are binary_sensor.* not switch.* because the
    # contract layer reports "is the device currently producing
    # heat/cold?" not "is the device currently switched on?").
    allowed_domains = {"climate", "sensor", "binary_sensor", "fan", "select"}
    pattern = re.compile(r"^[a-z_]+\.rc_hvac_[a-z0-9_]+$")

    # Vendor / implementation / device-side name leaks that must
    # NEVER appear in any rc_* tile id. The spec requirement is
    # "no double-stamps of [vendor + hardware names + climate-domain
    # + generic_thermostat] beyond the rc_hvac_ subsystem prefix".
    # Vendor names like Webasto / Eberspächer / Furrion / Dometic /
    # MaxxAir / Coleman / Broadlink / ecobee / nest / mitsubishi /
    # daikin are an absolute vendor leak and are forbidden from EVER
    # appearing in any rc_* tile id (regardless of where in the
    # tile).
    #
    # The generic nouns (`cabin`, `fan`, `heater`, `ac`, `cool`,
    # `heat`, `temperature`, `humidity`, `outdoor`, `frost`,
    # `over_temp`, `mode`, `speed`, `warning`) are LITERALLY PART OF
    # the spec-required tile ids (e.g.
    # `binary_sensor.rc_hvac_heater_active`,
    # `binary_sensor.rc_hvac_ac_active`,
    # `binary_sensor.rc_hvac_frost_warning`) — the spec calls for
    # those tiles — so flagging them as absolute substrings of the
    # suffix would conflict with the literal tile ids the spec
    # requires. The forbidden_substrings list below targets the
    # vendor-name absolute-forbidden set only; the spec's literal
    # tile ids are accepted by ID and never double-stamp any vendor
    # name.
    forbidden_substrings = (
        # Vendor / brand names — recipe explicitly forbids these
        # (absolute forbidden — no Webasto / Eberspächer / Furrion /
        # Dometic / MaxxAir / Coleman / Broadlink / generic_
        # thermostat / ecobee / nest / mitsubishi / daikin names
        # anywhere in any rc_* tile id; vendor neutrality is
        # non-negotiable).
        "webasto",              # Webasto diesel heater vendor (vendor leak)
        "eberspacher",          # Eberspächer diesel heater vendor (vendor leak)
        "eberspaecher",         # Eberspächer alternative spelling (vendor leak)
        "ebersp_acher",         # Eberspächer with non-ASCII umlaut — defensive (vendor leak)
        "furrion",              # Furrion rooftop AC vendor (vendor leak)
        "dometic",              # Dometic rooftop AC vendor (vendor leak)
        "maxxair",              # MaxxAir roof vent + AC vendor (vendor leak)
        "coleman",              # Coleman rooftop AC vendor (vendor leak)
        "broadlink",            # Broadlink IR-bridge vendor (vendor leak)
        "vevor",                # Vevor diesel heater vendor (vendor leak)
        "generic_thermostat",   # HA core generic_thermostat integration name (integration leak)
        "ecobee",               # ecobee vendor (vendor leak)
        "nest",                 # nest vendor (vendor leak)
        "mitsubishi",           # Mitsubishi mini-split vendor (vendor leak)
        "daikin",               # Daikin mini-split vendor (vendor leak)
        "climate_",             # HA core climate-domain namespace (integration leak)
    )

    for tile in tiles:
        assert pattern.match(tile), (
            f"tile id {tile!r} must match ^[a-z_]+\\.rc_hvac_[a-z_]+$ "
            f"(vendor-neutral contract naming per docs/reference/rc-entity-naming.md)"
        )
        # Domain segment must be one of the allowed HA core domain
        # prefixes for the §hvac subsystem.
        domain = tile.split(".", 1)[0]
        assert domain in allowed_domains, (
            f"tile id {tile!r} uses domain {domain!r} which is not in "
            f"the allowed HVAC domain set {sorted(allowed_domains)!r}; "
            f"per docs/reference/rc-entity-naming.md §hvac subsystem"
        )
        # Subsystem prefix is rc_hvac_; the suffix (after
        # `rc_hvac_`) MUST NOT contain any forbidden vendor substring.
        suffix = tile.split(".rc_hvac_", 1)[1]
        for bad in forbidden_substrings:
            assert bad not in suffix.lower(), (
                f"tile id {tile!r} contains forbidden vendor substring "
                f"{bad!r} in the suffix after `rc_hvac_`; per "
                f"docs/reference/rc-entity-naming.md, contract ids are "
                f"vendor-neutral — vendor names are forbidden in any "
                f"rc_* tile id"
            )
        # Each segment after the dot must be lowercase + underscores + digits.
        for segment in tile.split("."):
            assert re.match(r"^[a-z_][a-z0-9_]*$", segment), (
                f"tile id {tile!r} contains a non-conforming segment {segment!r}"
            )

    # Spec calls for exactly 11 tiles (1 climate + 2 sensor + 2
    # binary_sensor + 1 fan + 1 select + 1 sensor + 2 binary_sensor
    # + 1 select = 11 contract entities documented in the recipe §7
    # contract layer):
    #   climate.rc_hvac_cabin_thermostat
    #   sensor.rc_hvac_cabin_temperature
    #   sensor.rc_hvac_cabin_humidity
    #   binary_sensor.rc_hvac_heater_active
    #   binary_sensor.rc_hvac_ac_active
    #   fan.rc_hvac_cabin_fan
    #   select.rc_hvac_fan_speed
    #   sensor.rc_hvac_outdoor_temperature
    #   binary_sensor.rc_hvac_frost_warning
    #   binary_sensor.rc_hvac_over_temp_warning
    #   select.rc_hvac_mode
    assert len(tiles) == 11, (
        f"hvac-basics must contribute exactly 11 contract tiles per "
        f"spec (1 climate + 3 sensor + 4 binary_sensor + 1 fan + "
        f"2 select); got {len(tiles)}"
    )


def test_status_reflects_no_real_hvac(manifest: dict) -> None:
    """Status must be honest about no integration being shipped.

    If we ever flip this to 'shipped', the audit will demand an actual
    integration test (and rightly so). 'beta' is the only honest tier-b
    status for a recipe we can't integration-test.

    The six honesty warnings that tier_warnings must contain cover:
      - no_real_hvac_appliance_for_integration_test (no bench fixture)
      - recipe_depends_on_user_running_thermostat_and_or_heater_and_or_ac
        (operator's hardware dependency — at least one of the 4 paths
        must be running)
      - optional_diesel_heater_via_esphome_or_mqtt (Path B is optional)
      - optional_ac_via_ir_bridge_or_native_integration (Path C is optional)
      - requires_operator_wiring_safety_thermostats_before_first_use
        (the safety interlocks are operator-wired, not RoamCore-enforced)
      - frost_warning_and_over_temp_warning_depend_on_temperature_sensors
        (the frost + over-temp warnings depend on the temperature
        sensor wiring being correct)
    """
    assert manifest["status"] == "beta", (
        f"hvac-basics status={manifest['status']!r} implies shipped "
        f"coverage we don't have; use 'beta' until tier-a promotion "
        f"lands"
    )
    tier_warnings = manifest.get("tier_warnings", [])
    # Tier-warnings must include the honest-about-no-HVAC-appliance marker.
    assert "no_real_hvac_appliance_for_integration_test" in tier_warnings, (
        "tier_warnings must declare 'no_real_hvac_appliance_for_integration_test' "
        "for honesty in the audit listing"
    )
    # And the user-facing recipe dependency warning (operator must
    # run a thermostat AND/OR heater AND/OR AC).
    assert "recipe_depends_on_user_running_thermostat_and_or_heater_and_or_ac" in tier_warnings, (
        "tier_warnings must declare 'recipe_depends_on_user_running_thermostat_"
        "and_or_heater_and_or_ac' so the audit listing is honest about "
        "the operator's hardware dependency"
    )
    # Path B honesty — the optional diesel heater (Webasto / Eberspächer
    # / Chinese diesel / Vevor) via esphome or mqtt is optional + additive.
    assert "optional_diesel_heater_via_esphome_or_mqtt" in tier_warnings, (
        "tier_warnings must declare 'optional_diesel_heater_via_esphome_or_mqtt' "
        "so the audit listing is honest about the optional Path B "
        "diesel heater hardware dependency"
    )
    # Path C honesty — the optional rooftop AC (Furrion / Dometic /
    # MaxxAir / Coleman) via IR-bridge (Broadlink / MQTT-IR-Hub) or
    # native integration is optional + additive.
    assert "optional_ac_via_ir_bridge_or_native_integration" in tier_warnings, (
        "tier_warnings must declare 'optional_ac_via_ir_bridge_or_native_integration' "
        "so the audit listing is honest about the optional Path C "
        "rooftop AC hardware dependency"
    )
    # The four safety interlocks are operator-wired, not RoamCore-
    # enforced at tier-b (tier-a promotion would move them into
    # RoamCore-side asserts; see recipe §8).
    assert "requires_operator_wiring_safety_thermostats_before_first_use" in tier_warnings, (
        "tier_warnings must declare 'requires_operator_wiring_safety_thermostats_before_first_use' "
        "so the audit listing is honest that the safety interlocks "
        "(frost warning, over-temp warning, low-voltage lockout, "
        "mode-aware lockouts) are operator-wired per the recipe §8 "
        "and not RoamCore-enforced at tier-b"
    )
    # The frost + over-temp warnings depend on the temperature sensor
    # wiring being correct (outdoor sensor for frost; cabin sensor for
    # over-temp). The audit listing must be honest about this
    # dependency so operators know the warnings can be silent if the
    # sensors are mis-wired or disconnected.
    assert "frost_warning_and_over_temp_warning_depend_on_temperature_sensors" in tier_warnings, (
        "tier_warnings must declare 'frost_warning_and_over_temp_warning_depend_on_temperature_sensors' "
        "so the audit listing is honest that the safety warnings "
        "(frost_warning + over_temp_warning) require the operator's "
        "outdoor + cabin temperature sensors to be wired correctly"
    )


def test_safety_interlocks_are_documented(manifest: dict) -> None:
    """Defensive guard for the future tier-a promotion.

    HVAC safety is multi-dimensional in van life: the cabin MUST not
    drop below 5 °C (frozen pipes / condensation / battery damage
    below 0 °C); the cabin MUST not exceed 35 °C (the operator + pets
    + electronics must not cook); the diesel heater + rooftop AC MUST
    not run below 30 % SOC unless shore power is connected (battery
    brown-out); the mode-aware lockouts (Stealth / Sleep / Boost) MUST
    not wake the campground / waste battery / block service work.

    The recipe §8 walks through the four MANDATORY safety interlocks:
      - §8.1 Frost warning via `sensor.rc_hvac_outdoor_temperature` +
        `sensor.rc_hvac_cabin_temperature` (cross-reference to the
        heated-floors Wave 3 #44 connection's frost pattern)
      - §8.2 Over-temp warning via
        `sensor.rc_hvac_cabin_temperature` + cross-reference to the
        bluetooth-wifi-presence Wave 3 #42 connection's
        `binary_sensor.rc_presence_anyone_home` for the "pets left in
        van" escalation
      - §8.3 Low-voltage lockout via `sensor.rc_power_battery_soc` +
        `binary_sensor.rc_power_shore_connected` cross-reference to
        the Victron connection (diesel heater + AC pull 10–30 A
        sustained)
      - §8.4 Mode-aware lockouts (Stealth auto-lower fan + Sleep
        eco-mode + Boost disable-mode-aware-lockouts) via
        `select.rc_mode` cross-reference to the mode/automation-
        builder connection

    The test asserts all four are documented in the recipe so that
    when this connection promotes to tier-a (with a real HVAC bench
    on CI + the four safety interlock asserts hard-enforced in
    RoamCore code rather than only documented in the recipe), the
    audit has a clean assertion to flip.
    """
    text = RECIPE_PATH.read_text(encoding="utf-8")
    # §8 header MUST be present (with the "Safety interlocks" wording).
    assert "## §8 Safety interlocks" in text, (
        "recipe.md must have a '## §8 Safety interlocks' section "
        "(the four MANDATORY safety interlocks documentation block)"
    )
    # §8 must cover each of the four interlocking areas.
    safety_coverage = (
        # §8.1 frost warning via
        # `sensor.rc_hvac_outdoor_temperature` + cabin thermostat
        # maintaining > 5 °C
        "frost warning",
        # §8.2 over-temp warning via
        # `sensor.rc_hvac_cabin_temperature` > 35 °C + AC auto-on +
        # cabin fan auto-open + push notification
        "over-temp warning",
        # §8.3 low-voltage lockout via
        # `sensor.rc_power_battery_soc` < 30 % + shore-connected
        # check (cross-reference to the Victron connection)
        "low-voltage lockout",
        # §8.4 mode-aware lockouts via `select.rc_mode`
        # (Stealth auto-lower fan + Sleep eco-mode + Boost disable)
        "mode-aware lockouts",
    )
    for phrase in safety_coverage:
        assert phrase in text.lower(), (
            f"recipe.md §8 must cover {phrase!r}; the four safety "
            f"interlocks are MANDATORY before first use, and the "
            f"recipe is the only documentation operator + future-"
            f"tier-a integration code have at this tier"
        )
    # The contract tiles must include the three tiles that gate the
    # safety interlocks:
    #   binary_sensor.rc_hvac_frost_warning
    #     (frost warning aggregate)
    #   binary_sensor.rc_hvac_over_temp_warning
    #     (over-temp warning aggregate)
    #   binary_sensor.rc_hvac_heater_active
    #     (heater active feedback for the §7 safety interlocks)
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    safety_tiles = (
        "binary_sensor.rc_hvac_frost_warning",
        "binary_sensor.rc_hvac_over_temp_warning",
        "binary_sensor.rc_hvac_heater_active",
    )
    for safety_tile in safety_tiles:
        assert safety_tile in tiles, (
            f"dashboard.tiles must include {safety_tile!r}; the safety "
            f"interlock aggregate tiles are part of the contract layer "
            f"that the recipe §8 documents"
        )
    # The recipe must cross-reference the Victron connection via
    # `sensor.rc_power_battery_soc` + `binary_sensor.rc_power_shore_
    # connected` so the §8.3 low-voltage lockout cross-reference is
    # discoverable.
    assert "sensor.rc_power_battery_soc" in text, (
        "recipe.md must reference `sensor.rc_power_battery_soc` for "
        "the §8.3 low-voltage lockout cross-reference to the Victron "
        "`connections/victron/` recipe"
    )
    assert "binary_sensor.rc_power_shore_connected" in text, (
        "recipe.md must reference `binary_sensor.rc_power_shore_connected` "
        "for the §8.3 low-voltage lockout cross-reference to the "
        "Victron `connections/victron/` recipe"
    )
    # The recipe must cross-reference the bluetooth-wifi-presence
    # Wave 3 #42 connection via `binary_sensor.rc_presence_anyone_home`
    # so the §8.2 over-temp warning's "pets left in van" escalation
    # is discoverable.
    assert "binary_sensor.rc_presence_anyone_home" in text, (
        "recipe.md must reference `binary_sensor.rc_presence_anyone_home` "
        "for the §8.2 over-temp warning 'pets left in van' "
        "escalation cross-reference to the bluetooth-wifi-presence "
        "`connections/bluetooth-wifi-presence/` recipe"
    )
    # The recipe must cross-reference the mode/automation-builder
    # connection via `select.rc_mode` so the §8.4 mode-aware
    # lockouts are discoverable.
    assert "select.rc_mode" in text, (
        "recipe.md must reference `select.rc_mode` for the §8.4 "
        "mode-aware lockouts cross-reference to the mode/"
        "automation-builder `connections/mode-automation-builder/` "
        "recipe"
    )
    # The recipe must reference the heated-floors Wave 3 #44
    # companion (the floor heat + engine pre-heat connection) so
    # the umbrella HVAC basics + the specific heated-floors
    # relationship is discoverable.
    assert "heated-floors" in text.lower() or "heated floors" in text.lower(), (
        "recipe.md must reference the heated-floors Wave 3 #44 "
        "companion connection (`connections/heated-floors/`) so the "
        "umbrella + specific relationship between HVAC basics and "
        "heated floors is discoverable"
    )
    # The recipe's defensive guard for future tier-a promotion —
    # assert the §8 section has the "MANDATORY before first use"
    # emphasis that the recipe uses to remind operators to wire
    # each interlock.
    assert "mandatory before first use" in text.lower(), (
        "recipe.md §8 must use the 'MANDATORY before first use' "
        "emphasis on the four safety interlocks; this is the "
        "operator-side reminder that keeps the safety interlocks "
        "top-of-mind during install"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
