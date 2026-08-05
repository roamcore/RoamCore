"""Manifest-honesty tests for connections/water-tanks/connection.yml.

This is the only test file we can ship for a tier-b recipe connection
that has no real water tank bench (a fresh tank + a grey tank + a
12 V water pump + a leak sensor + a temperature probe + an ESP32 +
an ultrasonic probe + a CT clamp + optionally a Shelly UNI) on the
CI rig to integration-test against. The tests here assert that the
manifest is *honest about being tier-b* — that the folder/id/tier
invariants hold, that the recipe doc the tier_requirements promise
is actually present on disk, and that the rc_water_* tile ids are
vendor-neutral per docs/reference/rc-entity-naming.md.

If you add real integration coverage (e.g. a config_flow.py + a
bench with a fresh tank + a grey tank + a pump + a leak sensor +
a temperature probe + an ESP32 + canned fixture responses), keep
this file and add the new one alongside it; the audit will then
list both under `tests:` in the manifest.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/water-tanks/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> water-tanks/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "water-tanks"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
LEGACY_DOC = REPO_ROOT / "docs" / "catalog" / "water" / "water-tanks.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (water-tanks).

    This is the same invariant the audit script enforces; we duplicate
    it here so pytest catches regressions before CI runs the audit.
    """
    assert manifest["id"] == CONNECTION_DIR.name, (
        f"manifest id={manifest['id']!r} does not match folder name "
        f"{CONNECTION_DIR.name!r}"
    )
    assert manifest["id"] == "water-tanks"


def test_tier_b_without_tier_a_markers(manifest: dict) -> None:
    """Tier-b must NOT advertise tier-a-only RoamCore-owned fields.

    A regression here (e.g. someone flipping one_tap to true, or
    adding a RoamCore-owned config_flow.py) would falsely imply a
    working RoamCore integration + integration tests that we don't
    have, and the audit would either block the PR or let a
    misleading tier-a claim slip through.

    The distinction this test guards: install.config_flow is TRUE here
    because the UPSTREAM HA core sensor / esphome / shelly / template
    / binary_sensor integrations ALL expose a GUI flow (since 2022.x
    / 2023.x) — that's NOT a tier-a marker for RoamCore's tier. The
    tier-a marker for RoamCore would be a RoamCore-owned
    `config_flow.py` + RoamCore-owned integration code + integration
    tests against a RoamCore-owned water tank bench. None of those
    are shipped at tier-b.
    """
    assert manifest["tier"] == "b", "water-tanks must stay at tier-b until integration coverage lands"
    assert manifest["wizard"]["one_tap"] is False, (
        "tier-b connections cannot advertise one_tap=true (that's a tier-a contract)"
    )
    # Water tanks recipes an operator-side ESPHome tank sensor node
    # (Path A — ESPHome integration with 2× ultrasonic probes + CT
    # clamp + optional DS18B20 + optional leak sensor) OR a Shelly
    # UNI + ADC probe (Path B — Shelly integration with ADC input
    # + the HA `template:` integration translating voltage to
    # percentage via a per-tank calibration curve) OR a cloud-bridged
    # level sensor (Path C — SeeLevel / Garnet / Mopeka / Lippert
    # vendor integration); RoamCore ships no native config_flow for
    # that.
    # install.config_flow is the RoamCore-owned field. We document the
    # distinction in the manifest header: the UPSTREAM HA core
    # sensor / binary_sensor / template / input_number / input_select
    # domains + the ESPHome integration + the Shelly integration ALL
    # expose a GUI flow (since 2022.x / 2023.x) — honest upstream
    # truth, NOT a tier-a marker for RoamCore's tier. The tier-a
    # marker for RoamCore is a RoamCore-owned config_flow.py +
    # integration tests. Until those ship, this connection is tier-b
    # even though the upstream integrations have a GUI flow.
    assert manifest["install"]["config_flow"] is True, (
        "install.config_flow must stay True — the upstream HA core "
        "`sensor` domain (Path A ESPHome + Path B Shelly UNI + Path C "
        "vendor integration) + the `binary_sensor` domain (Path A "
        "pump_running + leak_detected + Path B/C derived binary_"
        "sensors) + the `template` integration (Path B voltage-to-"
        "percentage translation + the derived contract tiles) + the "
        "`input_number` integration (operator-tunable tank sizes) + "
        "the `input_select` integration (operator-tunable water mode) "
        "ALL expose a GUI flow since 2022.x / 2023.x; this is honest "
        "upstream truth, NOT a tier-a marker for RoamCore's tier. The "
        "tier-a marker for RoamCore would be a RoamCore-owned "
        "`config_flow.py` + RoamCore-owned integration code + "
        "integration tests against a RoamCore-owned water tank bench "
        "(a fresh tank + a grey tank + a 12 V water pump + a leak "
        "sensor + a temperature probe + an ESP32 + an ultrasonic "
        "probe + a CT clamp + optionally a Shelly UNI, all wired "
        "together in a controlled environment). None of those are "
        "shipped at tier-b."
    )
    assert manifest["install"]["hacs"] is False, (
        "water-tanks is a recipe; no HACS integration of our own is "
        "shipped (Path A uses HA core esphome; Path B uses HA core "
        "shelly + template; Path C uses vendor's own HA core or HACS "
        "integration — see_level / mopeka_pro_check / lippert_onecontrol "
        "are operator-installed via HACS, not RoamCore-shipped)"
    )
    # Belt-and-braces: there must be no RoamCore-owned config_flow.py
    # in this folder (no native integration code for a tier-b recipe
    # connection). The upstream HA core + sensor / esphome / shelly /
    # template / binary_sensor / input_number / input_select
    # integrations have their own GUI flows, but that lives in the
    # upstream HA core / HACS / vendor repos, not in this folder.
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
    # DOMAIN must equal "water_tanks" (matches the folder name
    # with hyphens replaced by underscores, per the audit convention).
    assert 'DOMAIN = "water_tanks"' in init_text, (
        '__init__.py must define DOMAIN = "water_tanks" '
        '(matches the folder name "water-tanks" with hyphens replaced by underscores)'
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
    # Sanity: the recipe actually documents water tanks + the contract
    # entities rather than just an empty placeholder. The recipe
    # mentions "water" / "tank" / "fresh" / "grey" — any one of these
    # is sufficient (a substantive howto would mention all of them,
    # but the assertion guards against the empty-placeholder
    # regression).
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert (
        "water" in text.lower()
        or "tank" in text.lower()
        or "fresh" in text.lower()
        or "grey" in text.lower()
    ) and "rc_water_" in text, (
        "recipe.md must document the water tanks setup (Path A "
        "ESPHome tank sensor node, Path B Shelly UNI + ADC probe, "
        "Path C cloud-bridged level sensor, contract entities, "
        "automations, troubleshooting) and reference at least one "
        "`rc_water_*` tile"
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
    # structured to mirror the hvac-basics §1–§11 shape with §1–§11
    # + §3 Path A + §4 Path B + §5 Path C + §7 Safety interlocks).
    # Grep-anchor the major section headers so a future "I rewrote
    # the recipe as one wall of text" regression gets caught.
    required_sections = (
        "## §1 What is Water tanks in RoamCore?",
        "## §2 Prerequisites",
        "## §3 Path A",
        "## §4 Path B",
        "## §5 Path C",
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
    docs/catalog/water/water-tanks.md; we promote the connection into
    the `water` category so the audit + boundary-CI can pair them up.
    The legacy doc MUST still exist (with the supersession banner) so
    that the recipe can reference it AND the audit can verify the
    supersession banner is in place.
    """
    assert manifest["category"] == "water", (
        f"category must stay 'water' (legacy doc lives at "
        f"docs/catalog/water/water-tanks.md); got {manifest['category']!r}"
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
        "legacy docs/catalog/water/water-tanks.md must carry the "
        "'SUPERSEDED' banner per spec"
    )
    assert "connections/water-tanks/" in legacy_text, (
        "legacy docs/catalog/water/water-tanks.md must point at "
        "`connections/water-tanks/` per spec"
    )


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """rc_* tile ids must NOT contain vendor names (per rc-entity-naming.md).

    The water contract is implementation-agnostic (it talks to whatever
    ESPHome tank sensor node / Shelly UNI + ADC probe / cloud-bridged
    level sensor the operator wires, not any vendor's library).
    Contract ids must stay vendor-neutral — NO `seelevel`, `mopeka`,
    `lippert`, `garnet`, `esphome`, `shelly`, `ads1115`, `current`,
    `adc`, `voltage`, `sensor_*` in any `rc_water_*` tile id BEYOND
    the subsystem prefix `rc_water_*`. The generic nouns `fresh`,
    `grey`, `level`, `pump`, `runtime`, `leak`, `freeze`,
    `temperature`, `tank`, `size`, `mode`, `warning`, `empty`, `low`,
    `full`, `days`, `remaining`, `too_long` are allowed (they
    describe what the tile is for, not which vendor).

    The spec is strict: every `dashboard.tiles[*]` must match
    `^[a-z_]+\\.rc_water_[a-z0-9_]+$` (vendor-neutral, subsystem
    prefix `rc_water_*` per the §water subsystem naming rules in
    docs/reference/rc-entity-naming.md). The subsystem prefix IS
    allowed (it's the owning-area marker); what is forbidden is
    vendor / hardware / sensor-model names appearing AFTER the
    subsystem prefix in a way that double-stamps the vendor into
    the id.
    """
    import re

    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles, "water-tanks contributes at least one dashboard tile"

    # Every tile must be a string entity id (spec calls for tiles-as-
    # strings, mirroring the spec's listed shape).
    for tile in tiles:
        assert isinstance(tile, str), (
            f"dashboard.tiles[*] must be a string entity id (spec §1); "
            f"got {tile!r}"
        )

    # Allowed HA core domain prefixes per docs/reference/rc-entity-
    # naming.md: sensor, binary_sensor, number, select.
    allowed_domains = {"sensor", "binary_sensor", "number", "select"}
    pattern = re.compile(r"^[a-z_]+\.rc_water_[a-z0-9_]+$")

    # Vendor / implementation / device-side name leaks that must
    # NEVER appear in any rc_* tile id. The spec requirement is
    # "no double-stamps of [vendor + hardware + sensor-model +
    # measurement-unit] names beyond the rc_water_ subsystem
    # prefix". Vendor names like SeeLevel / Mopeka / Lippert /
    # Garnet / ESPHome / Shelly / ADS1115 are an absolute vendor
    # leak and are forbidden from EVER appearing in any rc_* tile
    # id (regardless of where in the tile).
    #
    # The generic nouns (`fresh`, `grey`, `level`, `pump`, `leak`,
    # `freeze`, `temperature`, `tank`, `size`, `mode`, `warning`,
    # `empty`, `low`, `full`, `days`, `remaining`, `too_long`,
    # `runtime`, `min`, `24h`) are LITERALLY PART OF the spec-
    # required tile ids (e.g.
    # `binary_sensor.rc_water_fresh_low_warning`,
    # `binary_sensor.rc_water_leak_detected`,
    # `binary_sensor.rc_water_pump_running_too_long`) — the spec
    # calls for those tiles — so flagging them as absolute
    # substrings of the suffix would conflict with the literal
    # tile ids the spec requires. The forbidden_substrings list
    # below targets the vendor-name / hardware-name / sensor-model
    # / measurement-unit absolute-forbidden set only; the spec's
    # literal tile ids are accepted by ID and never double-stamp
    # any vendor name.
    forbidden_substrings = (
        # Vendor / brand names — recipe explicitly forbids these
        # (absolute forbidden — no SeeLevel / Mopeka / Lippert /
        # Garnet / ESPHome / Shelly / ADS1115 / JSNSR04T / HC-SR04
        # / DS18B20 / CT-013 / SCT-013 / vendor names anywhere in
        # any rc_* tile id; vendor neutrality is non-negotiable).
        "seelevel",             # SeeLevel vendor (vendor leak)
        "see_level",            # SeeLevel alternative spelling (vendor leak)
        "mopeka",               # Mopeka vendor (vendor leak)
        "lippert",              # Lippert vendor (vendor leak)
        "garnet",               # Garnet SeeLevel II vendor (vendor leak)
        "esphome",              # ESPHome integration name (integration leak)
        "shelly",               # Shelly vendor (vendor leak)
        "ads1115",              # ADS1115 ADC chip (hardware leak)
        "jsnsr04t",             # JSNSR04T ultrasonic probe (hardware leak)
        "hc_sr04",              # HC-SR04 ultrasonic probe (hardware leak)
        "ds18b20",              # DS18B20 temperature probe (hardware leak)
        "sct013",               # SCT-013 CT clamp (hardware leak)
        "sct_013",              # SCT-013 alternative spelling (hardware leak)
        # Measurement / hardware-side unit names that must not be
        # double-stamped into the rc_water_* tile id.
        "current",              # current (A) is a hardware-side unit; the
                                # contract tile is "pump_running" / "pump_
                                # running_too_long" not "pump_current"
        "adc",                  # ADC (analog-to-digital converter) is a
                                # hardware-side acronym; not a contract
                                # tile concept
        "voltage",              # voltage (V) is a hardware-side unit;
                                # the contract tile is "level_pct" /
                                # "level_l" not "voltage"
        "sensor_",              # HA core sensor domain namespace as a
                                # prefix (integration leak — the rc_*
                                # tile is itself a sensor.* but we
                                # never double-stamp the domain name)
        "binary_sensor_",       # HA core binary_sensor domain namespace
                                # as a prefix (integration leak)
    )

    for tile in tiles:
        assert pattern.match(tile), (
            f"tile id {tile!r} must match ^[a-z_]+\\.rc_water_[a-z_]+$ "
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
        # Subsystem prefix is rc_water_; the suffix (after
        # `rc_water_`) MUST NOT contain any forbidden vendor substring.
        suffix = tile.split(".rc_water_", 1)[1]
        for bad in forbidden_substrings:
            assert bad not in suffix.lower(), (
                f"tile id {tile!r} contains forbidden vendor substring "
                f"{bad!r} in the suffix after `rc_water_`; per "
                f"docs/reference/rc-entity-naming.md, contract ids are "
                f"vendor-neutral — vendor names are forbidden in any "
                f"rc_* tile id"
            )
        # Each segment after the dot must be lowercase + underscores + digits.
        for segment in tile.split("."):
            assert re.match(r"^[a-z_][a-z0-9_]*$", segment), (
                f"tile id {tile!r} contains a non-conforming segment {segment!r}"
            )

    # Spec calls for exactly 17 tiles (5 sensor telemetry +
    # 7 binary_sensor warnings + 1 temperature sensor +
    # 2 number configuration tiles + 1 mode select = 17 contract
    # entities documented in the recipe §6 contract layer):
    #   sensor.rc_water_fresh_level_pct
    #   sensor.rc_water_fresh_level_l
    #   sensor.rc_water_fresh_days_remaining
    #   sensor.rc_water_grey_level_pct
    #   sensor.rc_water_grey_level_l
    #   binary_sensor.rc_water_grey_full_warning
    #   binary_sensor.rc_water_fresh_low_warning
    #   binary_sensor.rc_water_fresh_empty_warning
    #   binary_sensor.rc_water_pump_running
    #   sensor.rc_water_pump_runtime_min_last_24h
    #   binary_sensor.rc_water_pump_running_too_long
    #   binary_sensor.rc_water_leak_detected
    #   binary_sensor.rc_water_freeze_risk
    #   sensor.rc_water_fresh_temperature_c
    #   number.rc_water_fresh_tank_size_l
    #   number.rc_water_grey_tank_size_l
    #   select.rc_water_mode
    assert len(tiles) == 17, (
        f"water-tanks must contribute exactly 17 contract tiles per "
        f"spec (5 sensor telemetry + 7 binary_sensor warnings + 1 "
        f"temperature sensor + 2 number configuration tiles + 1 mode "
        f"select); got {len(tiles)}"
    )


def test_status_reflects_no_real_water_tank(manifest: dict) -> None:
    """Status must be honest about no integration being shipped.

    If we ever flip this to 'shipped', the audit will demand an actual
    integration test (and rightly so). 'beta' is the only honest tier-b
    status for a recipe we can't integration-test.

    The four honesty warnings that tier_warnings must contain cover:
      - no_real_water_tank_for_integration_test (no bench fixture)
      - recipe_depends_on_user_running_tank_sensors_plus_pump_sense
        (operator's hardware dependency — at least one tank sensor +
        the pump-sense wire + (optional) the leak sensor must be
        wired)
      - optional_esphome_vs_shelly_uni_vs_vendor_choice (Path A vs
        Path B vs Path C is the operator's choice; RoamCore does not
        require any one specific path)
      - requires_operator_wiring_safety_freeze_leak_alerts_before_
        first_use (the safety interlocks are operator-wired, not
        RoamCore-enforced)
    """
    assert manifest["status"] == "beta", (
        f"water-tanks status={manifest['status']!r} implies shipped "
        f"coverage we don't have; use 'beta' until tier-a promotion "
        f"lands"
    )
    tier_warnings = manifest.get("tier_warnings", [])
    # Tier-warnings must include the honest-about-no-water-tank-bench marker.
    assert "no_real_water_tank_for_integration_test" in tier_warnings, (
        "tier_warnings must declare 'no_real_water_tank_for_integration_test' "
        "for honesty in the audit listing"
    )
    # And the user-facing recipe dependency warning (operator must
    # run tank sensors + pump sense + optional leak sensor + optional
    # temperature probe).
    assert "recipe_depends_on_user_running_tank_sensors_plus_pump_sense" in tier_warnings, (
        "tier_warnings must declare 'recipe_depends_on_user_running_tank_sensors_"
        "plus_pump_sense' so the audit listing is honest about the "
        "operator's hardware dependency"
    )
    # Path honesty — Path A vs Path B vs Path C is the operator's
    # choice; the recipe lists all three + the operator picks based
    # on hardware ownership + ESPHome familiarity + vendor preference.
    assert "optional_esphome_vs_shelly_uni_vs_vendor_choice" in tier_warnings, (
        "tier_warnings must declare 'optional_esphome_vs_shelly_uni_vs_vendor_choice' "
        "so the audit listing is honest about the optional Path A "
        "(ESPHome) vs Path B (Shelly UNI) vs Path C (vendor "
        "integration) hardware dependency"
    )
    # The five safety interlocks are operator-wired, not RoamCore-
    # enforced at tier-b (tier-a promotion would move them into
    # RoamCore-side asserts; see recipe §7).
    assert "requires_operator_wiring_safety_freeze_leak_alerts_before_first_use" in tier_warnings, (
        "tier_warnings must declare 'requires_operator_wiring_safety_freeze_leak_alerts_before_first_use' "
        "so the audit listing is honest that the safety interlocks "
        "(leak detected / freeze risk / fresh empty / pump running "
        "too long / mode-aware lockouts) are operator-wired per the "
        "recipe §7 and not RoamCore-enforced at tier-b"
    )


def test_safety_interlocks_are_documented(manifest: dict) -> None:
    """Defensive guard for the future tier-a promotion.

    Water safety is multi-dimensional in van life: a leak in a van
    ruins everything (water + electronics + cabinetry + insulation
    all die together); a frozen fresh water tank + frozen pipes =
    cracked tank + burst pipes + no drinking water + no shower water
    (the operator's whole water system is offline until the van
    thaws); a fresh tank that runs empty in the middle of the night
    means no shower / no dish wash / no toilet flush the next
    morning; a pump that's stuck running drains the fresh tank onto
    the floor + drains the battery bank (both are van-killers); the
    mode-aware lockouts (Stealth / Sleep / Boost) MUST not wake the
    campground / waste battery / block service work.

    The recipe §7 walks through the five MANDATORY safety
    interlocks:
      - §7.1 Leak detected via ANY leak sensor (under-sink /
        pump-area / under-van) — stops the pump + sends a HIGH-
        PRIORITY push notification
      - §7.2 Freeze risk via
        `sensor.rc_water_fresh_temperature_c` < 2 °C — cross-
        reference to the heated-floors + hvac-basics connections'
        frost-warning path
      - §7.3 Fresh empty warning via
        `sensor.rc_water_fresh_level_pct` < 5 % — surfaces
        prominently on the dashboard
      - §7.4 Pump running too long via
        `binary_sensor.rc_water_pump_running` continuously TRUE for
        > 10 min — auto-stops the pump
      - §7.5 Mode-aware lockouts (Stealth auto-mute warnings /
        Sleep silent / Boost disable-mode-aware-lockouts) via
        `select.rc_mode`

    The test asserts all five are documented in the recipe so that
    when this connection promotes to tier-a (with a real water tank
    bench on CI + the five safety interlock asserts hard-enforced in
    RoamCore code rather than only documented in the recipe), the
    audit has a clean assertion to flip.
    """
    text = RECIPE_PATH.read_text(encoding="utf-8")
    # §7 header MUST be present (with the "Safety interlocks" wording).
    assert "## §7 Safety interlocks" in text, (
        "recipe.md must have a '## §7 Safety interlocks' section "
        "(the five MANDATORY safety interlocks documentation block)"
    )
    # §7 must cover each of the five interlocking areas.
    safety_coverage = (
        # §7.1 leak detected via ANY leak sensor (under-sink /
        # pump-area / under-van) — stops the pump + sends a HIGH-
        # PRIORITY push notification
        "leak detected",
        # §7.2 freeze risk via
        # `sensor.rc_water_fresh_temperature_c` < 2 °C — cross-
        # reference to the heated-floors + hvac-basics connections'
        # frost-warning path
        "freeze risk",
        # §7.3 fresh empty warning via
        # `sensor.rc_water_fresh_level_pct` < 5 % — surfaces
        # prominently on the dashboard
        "fresh empty",
        # §7.4 pump running too long via
        # `binary_sensor.rc_water_pump_running` continuously TRUE for
        # > 10 min — auto-stops the pump
        "pump running too long",
        # §7.5 mode-aware lockouts via `select.rc_mode`
        # (Stealth auto-mute warnings / Sleep silent / Boost disable)
        "mode-aware lockouts",
    )
    for phrase in safety_coverage:
        assert phrase in text.lower(), (
            f"recipe.md §7 must cover {phrase!r}; the five safety "
            f"interlocks are MANDATORY before first use, and the "
            f"recipe is the only documentation operator + future-"
            f"tier-a integration code have at this tier"
        )
    # The contract tiles must include the four tiles that gate the
    # safety interlocks:
    #   binary_sensor.rc_water_leak_detected
    #     (leak detected aggregate)
    #   binary_sensor.rc_water_freeze_risk
    #     (freeze risk aggregate)
    #   binary_sensor.rc_water_fresh_empty_warning
    #     (fresh empty warning aggregate)
    #   binary_sensor.rc_water_pump_running_too_long
    #     (pump running too long aggregate)
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    safety_tiles = (
        "binary_sensor.rc_water_leak_detected",
        "binary_sensor.rc_water_freeze_risk",
        "binary_sensor.rc_water_fresh_empty_warning",
        "binary_sensor.rc_water_pump_running_too_long",
    )
    for safety_tile in safety_tiles:
        assert safety_tile in tiles, (
            f"dashboard.tiles must include {safety_tile!r}; the safety "
            f"interlock aggregate tiles are part of the contract layer "
            f"that the recipe §7 documents"
        )
    # The recipe must cross-reference the Victron connection via
    # `sensor.rc_power_battery_soc` + `binary_sensor.rc_power_shore_
    # connected` so the §7.4 pump running too long cross-reference
    # to the Victron `connections/victron/` recipe is discoverable
    # (the §7.4 auto-stop pattern uses the Victron SOC + shore-
    # connected state for the SOC > 50 % gate in §8.5).
    assert "sensor.rc_power_battery_soc" in text, (
        "recipe.md must reference `sensor.rc_power_battery_soc` for "
        "the §7.4 pump running too long / §8.5 freeze risk auto-"
        "engage heated-floors cross-reference to the Victron "
        "`connections/victron/` recipe"
    )
    assert "binary_sensor.rc_power_shore_connected" in text, (
        "recipe.md must reference `binary_sensor.rc_power_shore_connected` "
        "for the §7.4 pump running too long / §8.5 freeze risk auto-"
        "engage heated-floors cross-reference to the Victron "
        "`connections/victron/` recipe"
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
        "emphasis on the five safety interlocks; this is the "
        "operator-side reminder that keeps the safety interlocks "
        "top-of-mind during install"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))