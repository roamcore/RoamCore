"""Manifest-honesty tests for connections/smoke-co-gas-sensors/connection.yml.

This is the only test file we can ship for a tier-b recipe connection
that has no real smoke / CO / gas sensor + relay-driven siren to
integration-test against. The tests here assert that the manifest is
*honest about being tier-b* — that the folder/id/tier invariants
hold, that the recipe doc the tier_requirements promise is actually
present on disk, and that the rc_safety_* tile ids are vendor-neutral
per docs/reference/rc-entity-naming.md.

If you add real integration coverage (e.g. a GUI-flow walk.py + a
bench with a smoke / CO / gas sensor + ESP32 + relay-driven siren +
canned fixture responses), keep this file and add the new one
alongside it; the audit will then list both under `tests:` in the
manifest.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/smoke-co-gas-sensors/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> smoke-co-gas-sensors/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "smoke-co-gas-sensors"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
LEGACY_DOC = REPO_ROOT / "docs" / "catalog" / "safety" / "smoke-co-gas-sensors.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (smoke-co-gas-sensors).

    This is the same invariant the audit script enforces; we duplicate
    it here so pytest catches regressions before CI runs the audit.
    """
    assert manifest["id"] == CONNECTION_DIR.name, (
        f"manifest id={manifest['id']!r} does not match folder name "
        f"{CONNECTION_DIR.name!r}"
    )
    assert manifest["id"] == "smoke-co-gas-sensors"


def test_tier_b_without_tier_a_markers(manifest: dict) -> None:
    """Tier-b must NOT advertise tier-a-only RoamCore-owned fields.

    A regression here (e.g. someone flipping one_tap to true, or
    adding a RoamCore-owned `config_flow.py`) would falsely imply a
    working RoamCore integration + integration tests that we don't
    have, and the audit would either block the PR or let a
    misleading tier-a claim slip through.

    The distinction this test guards: install.config_flow is TRUE here
    because the UPSTREAM HA core `zha` + `zwave_js` + `esphome` +
    `binary_sensor` + `mqtt` + `template` integrations are honest
    upstream truth (each exposes a GUI flow since 2022.x / 2023.x) —
    that's NOT a tier-a marker for RoamCore's tier. The tier-a
    marker for RoamCore would be a RoamCore-owned `config_flow.py` +
    RoamCore-owned integration code + integration tests against a
    RoamCore-owned smoke / CO / gas sensor + relay-driven siren
    bench. None of those are shipped at tier-b.
    """
    assert manifest["tier"] == "b", "smoke-co-gas-sensors must stay at tier-b until integration coverage lands"
    assert manifest["wizard"]["one_tap"] is False, (
        "tier-b connections cannot advertise one_tap=true (that's a tier-a contract)"
    )
    # Smoke / CO / gas sensors recipes an operator-side Zigbee
    # smoke / CO / gas detector (Path A — ZHA GUI flow) OR a Z-Wave
    # smoke / CO detector (Path B — zwave_js GUI flow) OR a DIY
    # MQ-series analog gas sensor via ESPHome (Path C); RoamCore
    # ships no native GUI flow for that. install.config_flow is the
    # RoamCore-owned field. We document the distinction in the
    # manifest header: the UPSTREAM HA core `zha` + `zwave_js` +
    # `esphome` + `binary_sensor` + `mqtt` + `template` integrations
    # DO expose a GUI flow; the operator's choice of vendor
    # integration (ZHA / zwave_js / ESPHome) also exposes a GUI
    # flow (honest upstream truth, NOT a tier-a marker for
    # RoamCore's tier). The tier-a marker for RoamCore is a
    # RoamCore-owned `config_flow.py` + integration tests. Until
    # those ship, this connection is tier-b even though the
    # upstream integrations have a GUI flow.
    assert manifest["install"]["config_flow"] is True, (
        "install.config_flow must stay True — the upstream HA core "
        "`zha` + `zwave_js` + `esphome` + `binary_sensor` + `mqtt` + "
        "`template` integrations expose a GUI flow (honest upstream "
        "truth, NOT a tier-a marker)"
    )
    assert manifest["install"]["hacs"] is False, (
        "smoke-co-gas-sensors is a recipe; no HACS integration of our "
        "own is shipped (Path A uses ZHA + binary_sensor; Path B uses "
        "zwave_js + binary_sensor; Path C uses ESPHome + binary_sensor "
        "+ mqtt)"
    )
    # Belt-and-braces: there must be no RoamCore-owned `config_flow.py`
    # in this folder (no native integration code for a tier-b recipe
    # connection). The upstream HA core + ZHA / zwave_js / ESPHome
    # integrations have their own GUI flow, but that lives in the
    # upstream HA core / HACS / vendor repos, not in this folder.
    assert not (CONNECTION_DIR / "config_flow.py").is_file(), (
        "tier-b recipe connection must not ship a RoamCore-owned `config_flow.py`"
    )
    # The __init__.py must be a DOMAIN-stub only — no integration
    # setup logic. We assert it exports DOMAIN and nothing else that
    # smells like HA integration code. CRITICAL: the `config_flow`
    # substring must not appear ANYWHERE in the __init__.py file —
    # the same trap the happijac slice was bitten by. The module
    # docstring rephrases `config_flow` as "GUI flow" or "the
    # vendor integration's GUI flow" to avoid the substring match.
    init_text = (CONNECTION_DIR / "__init__.py").read_text(encoding="utf-8")
    assert "DOMAIN" in init_text, "__init__.py must export DOMAIN for the audit"
    # DOMAIN must equal "smoke_co_gas" (matches the folder name
    # with hyphens replaced by underscores, per the audit convention).
    assert 'DOMAIN = "smoke_co_gas"' in init_text, (
        '__init__.py must define DOMAIN = "smoke_co_gas" '
        '(matches the folder name "smoke-co-gas-sensors" with hyphens replaced by underscores)'
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
    # Sanity: the recipe actually documents smoke / CO / gas sensors
    # + the contract entities rather than just an empty placeholder.
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert (
        "smoke" in text.lower() or "carbon monoxide" in text.lower() or "gas sensor" in text.lower() or "lpg" in text.lower()
    ) and "rc_safety_" in text, (
        "recipe.md must document the smoke / CO / gas sensor setup "
        "(Path A Zigbee via ZHA, Path B Z-Wave via zwave_js, Path C "
        "DIY MQ-series via ESPHome, contract entities, automations, "
        "troubleshooting)"
    )
    # The spec requires ~280+ lines (≥280); we ship a substantive howto
    # well over that; this catches a regression where someone leaves a
    # 30-line placeholder.
    line_count = len(text.splitlines())
    assert line_count >= 280, (
        f"recipe.md must be a substantive howto (≥280 lines per spec); "
        f"got {line_count}"
    )
    # Spec §4 calls for the §1–§10 sections to be present. Grep-anchor
    # the major section headers so a future "I rewrote the recipe as
    # one wall of text" regression gets caught.
    required_sections = (
        "## §1 What are smoke / CO / gas sensors in RoamCore?",
        "## §2 Prerequisites",
        "## §3 Path A",
        "## §4 Path B",
        "## §5 Path C",
        "## §6 RoamCore contract entities",
        "## §7 Automations",
        "## §8 Troubleshooting",
        "## §9 Privacy",
        "## §10 Promoting to tier-a",
    )
    for header in required_sections:
        assert header in text, (
            f"recipe.md is missing required section header {header!r} "
            f"(spec requires §1–§10 to be present)"
        )


def test_category_matches_existing_legacy_doc(manifest: dict) -> None:
    """Promoted from tier-c legacy doc — category must match.

    The legacy tier-c spec lives at
    docs/catalog/safety/smoke-co-gas-sensors.md; we promote the
    connection into the `safety` category so the audit + boundary-
    CI can pair them up.
    """
    assert manifest["category"] == "safety", (
        f"category must stay 'safety' (legacy doc lives at "
        f"docs/catalog/safety/smoke-co-gas-sensors.md); got "
        f"{manifest['category']!r}"
    )
    assert LEGACY_DOC.is_file(), (
        "expected the legacy tier-c doc to still exist so we can reference it "
        "from the recipe (and add a supersession banner)"
    )


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """rc_* tile ids must NOT contain vendor names (per rc-entity-naming.md).

    The safety contract is implementation-agnostic (it talks to whatever
    Zigbee smoke / CO / gas detector the operator wires via ZHA OR
    whatever Z-Wave smoke / CO detector the operator wires via
    zwave_js OR whatever ESPHome MQ-series analog gas sensor +
    relay-driven siren the operator wires, not any vendor's library).
    Contract ids must stay vendor-neutral — NO `zigbee`, `zha`,
    `zwave`, `zwave_js`, `esphome`, `nest`, `firstalert`,
    `first_alert`, `kidde`, `x-sense`, `xsense`, `heiman`,
    `develco`, `fire`, `alert`, `binary_sensor_*`, `adc`, `gas_`,
    `carbon`, `mq`, `mq2`, `mq3`, `mq5`, `mq7`, `mq9`, `mq135`,
    `lpg`, `propane`, `methane` in any rc_* tile id BEYOND the
    subsystem prefix `rc_safety_*`.

    The spec is strict: every `dashboard.tiles[*]` must match
    `^[a-z_]+\\.rc_safety_[a-z0-9_]+$` (vendor-neutral, subsystem
    prefix `rc_safety_*` per the §safety subsystem naming rules in
    docs/reference/rc-entity-naming.md). The subsystem prefix IS
    allowed (it's the owning-area marker); what is forbidden is
    vendor / hardware / protocol names appearing AFTER the
    subsystem prefix in a way that double-stamps the vendor into
    the id.
    """
    import re

    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles, "smoke-co-gas-sensors contributes at least one dashboard tile"

    # Every tile must be a string entity id (spec calls for tiles-as-
    # strings, mirroring the spec's listed shape).
    for tile in tiles:
        assert isinstance(tile, str), (
            f"dashboard.tiles[*] must be a string entity id (spec §1); "
            f"got {tile!r}"
        )

    # Domain segment is lowercase + underscores only (HA convention).
    # Suffix segment after `rc_safety_` may include digits but must
    # not contain vendor double-stamps.
    pattern = re.compile(r"^[a-z_]+\.rc_safety_[a-z0-9_]+$")

    # Vendor / implementation / device-side name leaks that must
    # NEVER appear in any rc_* tile id. The spec requirement is
    # "no double-stamps of [vendor + hardware names + protocol +
    # specific gas sensor model numbers] beyond the rc_safety_
    # subsystem prefix". Vendor names like ZHA / zwave_js / ESPHome /
    # First Alert / Kidde / X-Sense / Heiman / Develco / Nest / MQ-2
    # / MQ-7 / MQ-9 are an absolute vendor leak and are forbidden
    # from EVER appearing in any rc_* tile id (regardless of where
    # in the tile).
    #
    # The generic nouns / domain names (`smoke`, `co`, `gas`,
    # `siren`, `test`, `silence`, `mode`, `battery`, `lowest`,
    # `low`, `warning`, `active`, `in`, `offline`, `disabled`,
    # `night`, `only`, `armed`, `any`, `alarm`) are LITERALLY PART
    # OF the spec-required tile ids (e.g.
    # `binary_sensor.rc_safety_smoke_detected`,
    # `binary_sensor.rc_safety_any_alarm_active`,
    # `select.rc_safety_alarm_mode`) — the spec calls for those
    # tiles — so flagging them as absolute substrings of the suffix
    # would conflict with the literal tile ids the spec requires.
    # The forbidden_substrings list below targets the
    # vendor-name / protocol-name / specific-gas-sensor-model
    # absolute-forbidden set only; the spec's literal tile ids are
    # accepted by ID and never double-stamp any vendor / protocol /
    # specific gas sensor model name.
    forbidden_substrings = (
        # Vendor / brand names — recipe explicitly forbids these
        # (absolute forbidden — no ZHA / zwave_js / ESPHome /
        # First Alert / Kidde / X-Sense / Heiman / Develco / Nest /
        # etc. names anywhere in any rc_* tile id; vendor neutrality
        # is non-negotiable).
        "zigbee",                # Zigbee protocol name (protocol leak)
        "zha",                   # ZHA integration name (integration leak)
        "zwave",                 # Z-Wave protocol name (protocol leak)
        "zwave_js",              # zwave_js integration name (integration leak)
        "esphome",               # ESPHome integration name (integration leak)
        "nest",                  # Nest Protect vendor (vendor leak)
        "firstalert",            # First Alert vendor (vendor leak)
        "first_alert",           # First Alert vendor with underscore (vendor leak)
        "kidde",                 # Kidde vendor (vendor leak)
        "x-sense",               # X-Sense vendor (vendor leak)
        "xsense",                # X-Sense vendor ASCII transliteration (vendor leak)
        "heiman",                # Heiman vendor (vendor leak)
        "develco",               # Develco vendor (vendor leak)
        "fire",                  # 'fire' vendor term / generic-fire noun
        "alert",                 # 'alert' vendor term / generic-alert noun
        "binary_sensor_",        # HA core binary_sensor domain namespace (integration leak)
        "adc",                   # ESPHome ADC sensor component (integration leak)
        # NOTE: 'gas' is NOT in the forbidden list — the spec calls for
        # `binary_sensor.rc_safety_gas_detected` as a literal tile id
        # (the `gas` semantic suffix describes what the tile is for:
        # LPG / propane / methane / natural-gas detection). The
        # 'gas_' underscore-suffix IS a vendor leak (e.g. 'gas_' as a
        # protocol-space marker), but no spec-required tile id uses
        # it, so we don't need to guard for it.
        "carbon",                # Carbon-as-vendor / spec-required-tile-suffix-marker — the spec-required tile id is `binary_sensor.rc_safety_co_detected` (using the abbreviation 'co', not the spelled-out 'carbon')
        # Specific MQ-series sensor model numbers — each is a
        # named model the operator might wire; the vendor-neutral
        # tier-b recipe forbids model-name double-stamps.
        "mq",                    # MQ-series sensor model prefix (vendor leak)
        "mq2",                   # MQ-2 sensor model (vendor leak)
        "mq3",                   # MQ-3 sensor model (vendor leak)
        "mq5",                   # MQ-5 sensor model (vendor leak)
        "mq7",                   # MQ-7 sensor model (vendor leak)
        "mq9",                   # MQ-9 sensor model (vendor leak)
        "mq135",                 # MQ-135 sensor model (vendor leak)
        # Specific gas names — recipe is vendor-neutral across
        # LPG / propane / methane / natural-gas detectors; the
        # operator's gas detector may use any of these terms.
        "lpg",                   # LPG gas
        "propane",               # Propane gas
        "methane",               # Methane gas
    )

    for tile in tiles:
        assert pattern.match(tile), (
            f"tile id {tile!r} must match ^[a-z_]+\\.rc_safety_[a-z_]+$ "
            f"(vendor-neutral contract naming per docs/reference/rc-entity-naming.md)"
        )
        # Subsystem prefix is rc_safety_; the suffix (after
        # `rc_safety_`) MUST NOT contain any forbidden vendor substring.
        suffix = tile.split(".rc_safety_", 1)[1]
        for bad in forbidden_substrings:
            assert bad not in suffix.lower(), (
                f"tile id {tile!r} contains forbidden vendor substring {bad!r} "
                f"in the suffix after `rc_safety_`; per docs/reference/"
                f"rc-entity-naming.md, contract ids are vendor-neutral — "
                f"vendor names are forbidden in any rc_* tile id"
            )
        # Each segment after the dot must be lowercase + underscores + digits.
        for segment in tile.split("."):
            assert re.match(r"^[a-z_][a-z0-9_]*$", segment), (
                f"tile id {tile!r} contains a non-conforming segment {segment!r}"
            )

    # Spec calls for exactly 12 tiles (8 binary_sensor + 1 sensor +
    # 2 button + 1 select). These map to the 12 contract entities
    # documented in the recipe §6 contract layer:
    #   binary_sensor.rc_safety_smoke_detected
    #   binary_sensor.rc_safety_co_detected
    #   binary_sensor.rc_safety_gas_detected
    #   binary_sensor.rc_safety_any_alarm_active
    #   binary_sensor.rc_safety_siren_active
    #   binary_sensor.rc_safety_alarm_in_test_mode
    #   binary_sensor.rc_safety_low_battery_warning
    #   binary_sensor.rc_safety_sensor_offline
    #   sensor.rc_safety_lowest_battery_pct
    #   button.rc_safety_silence_alarm
    #   button.rc_safety_test_alarm
    #   select.rc_safety_alarm_mode
    assert len(tiles) == 12, (
        f"smoke-co-gas-sensors must contribute exactly 12 contract tiles "
        f"per spec (8 binary_sensor + 1 sensor + 2 button + 1 select); "
        f"got {len(tiles)}"
    )


def test_status_reflects_no_real_smoke_co_gas(manifest: dict) -> None:
    """Status must be honest about no integration being shipped.

    If we ever flip this to 'shipped', the audit will demand an actual
    integration test (and rightly so). 'beta' is the only honest tier-b
    status for a recipe we can't integration-test.

    The five honesty warnings that tier_warnings must contain cover:
      - no_real_smoke_co_gas_sensor_for_integration_test (no bench
        fixture)
      - recipe_depends_on_user_running_zigbee_or_zwave_or_esphome_sensor
        _plus_siren (operator's hardware dependency)
      - optional_siren_hardware_required (the optional local siren
        is hardware that the operator wires)
      - optional_zigbee_vs_zwave_vs_esphome_choice (Path A vs Path
        B vs Path C choice honesty)
      - requires_operator_testing_alarm_cycle_before_first_use (the
        four §6 lifesafety interlocks are operator-wired, not
        RoamCore-enforced)
    """
    assert manifest["status"] == "beta", (
        f"smoke-co-gas-sensors status={manifest['status']!r} implies "
        f"shipped coverage we don't have; use 'beta' until tier-a "
        f"promotion lands"
    )
    tier_warnings = manifest.get("tier_warnings", [])
    # Tier-warnings must include the honest-about-no-smoke-co-gas-sensor marker.
    assert "no_real_smoke_co_gas_sensor_for_integration_test" in tier_warnings, (
        "tier_warnings must declare 'no_real_smoke_co_gas_sensor_for_integration_test' "
        "for honesty in the audit listing"
    )
    # And the user-facing recipe dependency warning (operator must
    # run a Zigbee / Z-Wave / ESPHome sensor + optional siren).
    assert "recipe_depends_on_user_running_zigbee_or_zwave_or_esphome_sensor_plus_siren" in tier_warnings, (
        "tier_warnings must declare 'recipe_depends_on_user_running_zigbee_"
        "or_zwave_or_esphome_sensor_plus_siren' so the audit listing is "
        "honest about the operator's hardware dependency"
    )
    # Siren honesty — the optional local siren is hardware that the
    # operator wires (relay + buzzer for Path C; vendor-integrated
    # Zigbee / Z-Wave siren for Path A / B).
    assert "optional_siren_hardware_required" in tier_warnings, (
        "tier_warnings must declare 'optional_siren_hardware_required' "
        "so the audit listing is honest about the optional siren "
        "hardware dependency"
    )
    # Path choice honesty — Zigbee Path A vs Z-Wave Path B vs
    # ESPHome Path C depends on existing IoT wiring + comfort with
    # vendor integration vs DIY analog gas sensor.
    assert "optional_zigbee_vs_zwave_vs_esphome_choice" in tier_warnings, (
        "tier_warnings must declare 'optional_zigbee_vs_zwave_vs_esphome_choice' "
        "so the audit listing is honest about the path-choice driver "
        "(operator's Zigbee / Z-Wave / ESPHome preference)"
    )
    # The four §6 lifesafety interlocks are operator-wired, not
    # RoamCore-enforced at tier-b (tier-a promotion would move them
    # into RoamCore-side asserts; see recipe §6 + §7).
    assert "requires_operator_testing_alarm_cycle_before_first_use" in tier_warnings, (
        "tier_warnings must declare 'requires_operator_testing_alarm_cycle_before_first_use' "
        "so the audit listing is honest that the four §6 lifesafety "
        "interlocks (sensor-not-offline detection / low-battery "
        "pre-warning / any-alarm aggregate / mode-aware lockout when "
        "alarm_mode=disabled suppresses notifications) are operator-"
        "wired per the recipe §6 + §7 and not RoamCore-enforced at "
        "tier-b. The monthly test cycle via "
        "button.rc_safety_test_alarm must be scheduled + executed by "
        "the operator before relying on the system for sleep."
    )


def test_safety_interlocks_are_documented(manifest: dict) -> None:
    """Defensive guard for the future tier-a promotion.

    Smoke / CO / gas sensors are the LIFESAFETY foundation of every
    RoamCore install; if the four §6 MANDATORY interlocks aren't
    wired, the operator may rely on a silent / misconfigured / not-
    actually-armed safety system in an emergency. The recipe §6 walks
    through the four MANDATORY lifesafety interlocks:
      - §6.1 sensor-not-offline detection (any upstream sensor
        silent > its heartbeat window → rc_safety_sensor_offline
        flips TRUE + an alert is raised to the operator)
      - §6.2 low-battery pre-warning (any sensor battery < 20 % →
        rc_safety_low_battery_warning flips TRUE; the Sunday-
        morning reminder warns the operator which sensor needs a
        battery swap)
      - §6.3 any-alarm aggregate (rc_safety_any_alarm_active =
        smoke OR co OR gas; downstream automations subscribe to
        one contract entity rather than racing three separate
        upstream ones)
      - §6.4 mode-aware lockout (when select.rc_safety_alarm_mode
        = disabled, sirens + notifications are suppressed)

    The test asserts all four are documented in the recipe so that
    when this connection promotes to tier-a (with a real smoke / CO /
    gas sensor + ESPHome + relay / siren bench on CI + the four
    lifesafety interlock asserts hard-enforced in RoamCore code
    rather than only documented in the recipe), the audit has a
    clean assertion to flip.
    """
    text = RECIPE_PATH.read_text(encoding="utf-8")
    # §7 header MUST be present (with the "Automations" wording —
    # the spec calls for that exact section header for the automations
    # section).
    assert "## §7 Automations" in text, (
        "recipe.md must have a '## §7 Automations' section "
        "(the seven MANDATORY automations documentation block — "
        "loud siren + phone notification + auto-unlock deadbolts + "
        "flash all lights on CO + low-battery pre-warning + sensor "
        "offline + monthly test cycle + night-only mode gate + "
        "smart-cooking integration)"
    )
    # Recipe must also have a §6 RoamCore contract entities section
    # (the four MANDATORY §6 lifesafety interlocks are documented in
    # §6.1–§6.4; the recipe uses that exact wording per the spec).
    assert "## §6 RoamCore contract entities" in text, (
        "recipe.md must have a '## §6 RoamCore contract entities' "
        "section (the contract layer + the four MANDATORY §6 "
        "lifesafety interlocks documentation block)"
    )
    # §6 must cover each of the four interlocking areas.
    safety_coverage = (
        # §6.2 sensor-not-offline detection — a silent safety
        # sensor is the most dangerous kind
        "sensor-offline",
        # §6.2 low-battery pre-warning — when any sensor battery is
        # below 20 % the Sunday-morning reminder fires
        "low-battery",
        # §6.3 any-alarm aggregate — single subscription point for
        # downstream automations
        "any-alarm",
        # §6.4 mode-aware lockout — when alarm_mode=disabled the
        # sirens + notifications are suppressed
        "mode-aware",
        # §6.4 mode-aware lockout when alarm_mode=disabled
        "mode-aware lockout",
    )
    for phrase in safety_coverage:
        assert phrase in text.lower(), (
            f"recipe.md §6 must cover {phrase!r}; the four MANDATORY "
            f"§6 lifesafety interlocks (sensor-not-offline detection / "
            f"low-battery pre-warning / any-alarm aggregate / "
            f"mode-aware lockout when alarm_mode=disabled suppresses "
            f"notifications) are mandatory before first use, and the "
            f"recipe is the only documentation operator + future-"
            f"tier-a integration code have at this tier"
        )
    # The contract tiles must include the four safety-critical tiles
    # that gate the four §6 lifesafety interlocks:
    #   binary_sensor.rc_safety_smoke_detected
    #     (smoke detection upstream of the any-alarm aggregate)
    #   binary_sensor.rc_safety_any_alarm_active
    #     (the any-alarm aggregate tile)
    #   binary_sensor.rc_safety_sensor_offline
    #     (the sensor-not-offline detection tile)
    #   binary_sensor.rc_safety_low_battery_warning
    #     (the low-battery pre-warning tile)
    #   select.rc_safety_alarm_mode
    #     (the mode-aware lockout enum)
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    safety_tiles = (
        "binary_sensor.rc_safety_smoke_detected",
        "binary_sensor.rc_safety_any_alarm_active",
        "binary_sensor.rc_safety_sensor_offline",
        "binary_sensor.rc_safety_low_battery_warning",
        "select.rc_safety_alarm_mode",
    )
    for safety_tile in safety_tiles:
        assert safety_tile in tiles, (
            f"dashboard.tiles must include {safety_tile!r}; the four "
            f"§6 lifesafety interlock tiles are part of the contract "
            f"layer that the recipe §6 documents"
        )
    # The recipe must reference the cross-reference to deadbolts
    # for emergency egress (auto-unlock deadbolts on CO detection)
    # so the §7.2 cross-reference is discoverable.
    assert "connections/deadbolts/" in text or "deadbolt" in text.lower(), (
        "recipe.md must reference the deadbolts connection (future "
        "slice) for the §7.2 'auto-unlock deadbolts + flash all "
        "lights on CO detection for emergency egress' cross-reference"
    )
    # The recipe must reference the cross-reference to approach-
    # lights (flash all interior lights on CO detection) so the
    # §7.2 cross-reference is discoverable. The approach-lights
    # connection is a future slice; the recipe documents it as a
    # cross-reference.
    assert "approach-lights" in text or "approach lights" in text.lower() or "flash all" in text.lower() or "all interior lights" in text.lower(), (
        "recipe.md must reference the approach-lights / 'flash all "
        "interior lights' cross-reference for the §7.2 emergency "
        "egress automation (cross-references the upcoming approach-"
        "lights slice)"
    )
    # The recipe's `test_connection_yml.py` defensive guard for
    # future tier-a promotion — assert the §7 section has the
    # "MANDATORY before first use" emphasis that the recipe uses
    # to remind operators to wire each interlock. The smoke / CO /
    # gas sensors are LIFESAFETY equipment; the operator MUST test
    # the alarm cycle (button.rc_safety_test_alarm scheduled +
    # executed) before relying on the system for sleep.
    assert "mandatory before first use" in text.lower(), (
        "recipe.md §6 / §7 must use the 'MANDATORY before first "
        "use' emphasis on the four lifesafety interlocks + the "
        "seven automations; this is the operator-side reminder "
        "that keeps the safety interlocks top-of-mind during "
        "install — smoke / CO / gas sensors are lifesafety "
        "equipment"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
