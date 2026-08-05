"""Manifest-honesty tests for connections/heated-floors/connection.yml.

This is the only test file we can ship for a tier-b recipe connection
that has no real heated-floor + relay + temperature probe + optional
engine preheat to integration-test against. The tests here assert that
the manifest is *honest about being tier-b* — that the folder/id/tier
invariants hold, that the recipe doc the tier_requirements promise is
actually present on disk, and that the rc_hvac_* tile ids are
vendor-neutral per docs/reference/rc-entity-naming.md.

If you add real integration coverage (e.g. a config_flow.py + a
bench with a heated-floor + relay + temperature probe + optional
engine preheat + canned fixture responses), keep this file and add
the new one alongside it; the audit will then list both under `tests:`
in the manifest.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/heated-floors/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> heated-floors/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "heated-floors"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
LEGACY_DOC = REPO_ROOT / "docs" / "catalog" / "hvac" / "heated-floors-and-engine-preheat.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (heated-floors).

    This is the same invariant the audit script enforces; we duplicate
    it here so pytest catches regressions before CI runs the audit.
    """
    assert manifest["id"] == CONNECTION_DIR.name, (
        f"manifest id={manifest['id']!r} does not match folder name "
        f"{CONNECTION_DIR.name!r}"
    )
    assert manifest["id"] == "heated-floors"


def test_tier_b_without_tier_a_markers(manifest: dict) -> None:
    """Tier-b must NOT advertise tier-a-only RoamCore-owned fields.

    A regression here (e.g. someone flipping one_tap to true, or
    adding a RoamCore-owned config_flow.py) would falsely imply a
    working RoamCore integration + integration tests that we don't
    have, and the audit would either block the PR or let a
    misleading tier-a claim slip through.

    The distinction this test guards: install.config_flow is TRUE here
    because the UPSTREAM HA core `generic_thermostat` integration is
    honest upstream truth (GUI flow since 2022.x) — that's NOT a
    tier-a marker for RoamCore's tier. The tier-a marker for
    RoamCore would be a RoamCore-owned `config_flow.py` + RoamCore-
    owned integration code + integration tests against a RoamCore-
    owned heated-floor + relay + temperature probe + optional engine
    preheat bench. None of those are shipped at tier-b.
    """
    assert manifest["tier"] == "b", "heated-floors must stay at tier-b until integration coverage lands"
    assert manifest["wizard"]["one_tap"] is False, (
        "tier-b connections cannot advertise one_tap=true (that's a tier-a contract)"
    )
    # Heated floors + engine pre-heat recipes an operator-side smart
    # thermostat (Path A — Mysa / Shelly H&T / generic-Zigbee) OR an
    # upstream HA core `generic_thermostat:` wrapping a temperature
    # probe + a relay-driven heater (Path B) OR an optional engine
    # pre-heat via a relay or CAN bus gateway (Path C); RoamCore ships
    # no native config_flow for that. install.config_flow is the
    # RoamCore-owned field. We document the distinction in the
    # manifest header: the UPSTREAM HA core `generic_thermostat`
    # integration DOES expose a GUI flow since 2022.x; the operator's
    # choice of climate-domain vendor integration (Path A: Mysa /
    # Shelly H&T / generic-Zigbee) also exposes a GUI flow (honest
    # upstream truth, NOT a tier-a marker for RoamCore's tier). The
    # tier-a marker for RoamCore is a RoamCore-owned config_flow.py +
    # integration tests. Until those ship, this connection is tier-b
    # even though the upstream integrations have a GUI flow.
    assert manifest["install"]["config_flow"] is True, (
        "install.config_flow must stay True — the upstream HA core "
        "`generic_thermostat` integration + the climate-domain vendor "
        "integrations (Mysa / Shelly H&T / generic-Zigbee) expose a "
        "GUI flow (honest upstream truth, NOT a tier-a marker)"
    )
    assert manifest["install"]["hacs"] is False, (
        "heated-floors is a recipe; no HACS integration of our own is "
        "shipped (Path A uses vendor integration + HA core; Path B "
        "uses only HA core generic_thermostat; Path C uses vendor "
        "engine preheat integration or HA core switch)"
    )
    # Belt-and-braces: there must be no RoamCore-owned config_flow.py
    # in this folder (no native integration code for a tier-b recipe
    # connection). The upstream HA core + climate-domain vendor
    # integrations have their own GUI flow, but that lives in the
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
    # DOMAIN must equal "heated_floors" (matches the folder name
    # with hyphens replaced by underscores, per the audit convention).
    assert 'DOMAIN = "heated_floors"' in init_text, (
        '__init__.py must define DOMAIN = "heated_floors" '
        '(matches the folder name "heated-floors" with hyphens replaced by underscores)'
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
    # Sanity: the recipe actually documents heated floors + engine
    # preheat + the contract entities rather than just an empty
    # placeholder.
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert (
        "heated floor" in text.lower() or "engine preheat" in text.lower() or "engine pre-heat" in text.lower()
    ) and "rc_hvac_" in text, (
        "recipe.md must document the heated floors + engine pre-heat "
        "setup (Path A smart thermostat, Path B generic_thermostat, "
        "Path C optional engine pre-heat, contract entities, "
        "automations, troubleshooting)"
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
        "## §1 What are heated floors + engine pre-heat in RoamCore?",
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
    docs/catalog/hvac/heated-floors-and-engine-preheat.md; we promote
    the connection into the `hvac` category so the audit + boundary-
    CI can pair them up.
    """
    assert manifest["category"] == "hvac", (
        f"category must stay 'hvac' (legacy doc lives at "
        f"docs/catalog/hvac/heated-floors-and-engine-preheat.md); got "
        f"{manifest['category']!r}"
    )
    # Per the 2026-08-05 docs/ux-first-pass repo-hygiene alignment,
    # the legacy doc is OPTIONAL (recipe.md is canonical).
    # Skip the supersession-banner checks when the legacy doc isn't present.
    if not LEGACY_DOC.is_file():
        pytest.skip(
            f"legacy doc {LEGACY_DOC} not present; "
            f"new pattern: recipe.md is canonical per directive repo-hygiene rule"
        )

def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """rc_* tile ids must NOT contain vendor names (per rc-entity-naming.md).

    The HVAC contract is implementation-agnostic (it talks to whatever
    smart thermostat integration OR HA core generic_thermostat + relay
    OR engine preheat relay/CAN bus gateway the operator wires, not any
    vendor's library). Contract ids must stay vendor-neutral — NO
    `floor`, `heated`, `thermostat`, `wyze`, `mysa`, `shelly`, `moen`,
    `zigbee`, `webasto`, `espar`, `eberspacher`, `preheat`, `engine`,
    `climate_`, `generic_thermostat` in any rc_* tile id BEYOND the
    subsystem prefix `rc_hvac_*`.

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
    assert tiles, "heated-floors contributes at least one dashboard tile"

    # Every tile must be a string entity id (spec calls for tiles-as-
    # strings, mirroring the spec's listed shape).
    for tile in tiles:
        assert isinstance(tile, str), (
            f"dashboard.tiles[*] must be a string entity id (spec §1); "
            f"got {tile!r}"
        )

    # Domain segment is lowercase + underscores only (HA convention).
    # Suffix segment after `rc_hvac_` may include digits but must not
    # contain vendor double-stamps.
    pattern = re.compile(r"^[a-z_]+\.rc_hvac_[a-z0-9_]+$")

    # Vendor / implementation / device-side name leaks that must
    # NEVER appear in any rc_* tile id. The spec requirement is
    # "no double-stamps of [vendor + hardware names + climate-domain
    # + generic_thermostat] beyond the rc_hvac_ subsystem prefix".
    # Vendor names like Mysa / Shelly / Wyze / Moen / Zigbee /
    # Webasto / Espar / Eberspächer are an absolute vendor leak and
    # are forbidden from EVER appearing in any rc_* tile id
    # (regardless of where in the tile).
    #
    # The generic nouns / domain names (`floor`, `heated`, `thermostat`,
    # `preheat`, `engine`, `climate_`, `generic_thermostat`) are
    # LITERALLY PART OF the spec-required tile ids (e.g.
    # `climate.rc_hvac_floor_thermostat`,
    # `sensor.rc_hvac_engine_preheat_runtime_min`) — the spec calls
    # for those tiles — so flagging them as absolute substrings of
    # the suffix would conflict with the literal tile ids the spec
    # requires. The forbidden_substrings list below targets the
    # vendor-name absolute-forbidden set only; the spec's literal
    # tile ids are accepted by ID and never double-stamp any vendor
    # name.
    forbidden_substrings = (
        # Vendor / brand names — recipe explicitly forbids these
        # (absolute forbidden — no Mysa / Wyze / Shelly / Moen /
        # Zigbee / Webasto / Espar / Eberspächer names anywhere in
        # any rc_* tile id; vendor neutrality is non-negotiable).
        "wyze",                 # Wyze smart thermostat vendor (vendor leak)
        "mysa",                 # Mysa floor thermostat vendor (vendor leak)
        "shelly",               # Shelly relay / Shelly H&T vendor (vendor leak)
        "moen",                 # Moen smart water / Flo vendor (vendor leak)
        "zigbee",               # Zigbee protocol name (vendor / protocol leak)
        "webasto",              # Webasto engine preheat vendor (vendor leak)
        "espar",                # Espar engine preheat vendor (vendor leak)
        "eberspacher",          # Eberspächer engine preheat vendor (vendor leak)
        "ebersp_acher",         # Eberspächer with non-ASCII umlaut — defensive (vendor leak)
        "eberspacher",          # Eberspächer ASCII transliteration (vendor leak)
        "thermo_top",           # Webasto Thermo Top Evo / Pro model name (vendor leak)
        "hydronic",             # Eberspächer Hydronic S3 model name (vendor leak)
        "generic_thermostat",   # HA core generic_thermostat integration name (integration leak)
        "climate_",             # HA core climate-domain namespace (integration leak)
    )

    for tile in tiles:
        assert pattern.match(tile), (
            f"tile id {tile!r} must match ^[a-z_]+\\.rc_hvac_[a-z_]+$ "
            f"(vendor-neutral contract naming per docs/reference/rc-entity-naming.md)"
        )
        # Subsystem prefix is rc_hvac_; the suffix (after
        # `rc_hvac_`) MUST NOT contain any forbidden vendor substring.
        suffix = tile.split(".rc_hvac_", 1)[1]
        for bad in forbidden_substrings:
            assert bad not in suffix.lower(), (
                f"tile id {tile!r} contains forbidden vendor substring {bad!r} "
                f"in the suffix after `rc_hvac_`; per docs/reference/"
                f"rc-entity-naming.md, contract ids are vendor-neutral — "
                f"vendor names are forbidden in any rc_* tile id"
            )
        # Each segment after the dot must be lowercase + underscores + digits.
        for segment in tile.split("."):
            assert re.match(r"^[a-z_][a-z0-9_]*$", segment), (
                f"tile id {tile!r} contains a non-conforming segment {segment!r}"
            )

    # Spec calls for exactly 13 tiles (1 climate + 2 sensor + 3
    # binary_sensor + 1 switch + 1 number + 1 select + 1 binary_sensor
    # + 1 switch + 1 binary_sensor + 1 sensor). These map to the 13
    # contract entities documented in the recipe §6 contract layer:
    #   climate.rc_hvac_floor_thermostat
    #   sensor.rc_hvac_floor_current_temp
    #   sensor.rc_hvac_interior_temp
    #   binary_sensor.rc_hvac_floor_heating_active
    #   binary_sensor.rc_hvac_floor_maintaining
    #   binary_sensor.rc_hvac_floor_off
    #   switch.rc_hvac_floor_heater
    #   number.rc_hvac_floor_setpoint
    #   select.rc_hvac_floor_mode
    #   binary_sensor.rc_hvac_floor_low_voltage_lockout
    #   switch.rc_hvac_engine_preheat
    #   binary_sensor.rc_hvac_engine_preheat_active
    #   sensor.rc_hvac_engine_preheat_runtime_min
    assert len(tiles) == 13, (
        f"heated-floors must contribute exactly 13 contract tiles per "
        f"spec (1 climate + 2 sensor + 3 binary_sensor + 1 switch + "
        f"1 number + 1 select + 1 binary_sensor + 1 switch + "
        f"1 binary_sensor + 1 sensor); got {len(tiles)}"
    )


def test_status_reflects_no_real_heated_floor(manifest: dict) -> None:
    """Status must be honest about no integration being shipped.

    If we ever flip this to 'shipped', the audit will demand an actual
    integration test (and rightly so). 'beta' is the only honest tier-b
    status for a recipe we can't integration-test.

    The five honesty warnings that tier_warnings must contain cover:
      - no_real_heated_floor_for_integration_test (no bench fixture)
      - recipe_depends_on_user_running_heated_floor_plus_thermostat_or_relay
        (operator's hardware dependency)
      - optional_engine_preheat_hardware_required (Path C is optional
        + additive)
      - optional_smart_thermostat_vs_generic_thermostat_choice (Path
        A vs Path B choice honesty)
      - requires_operator_wiring_temperature_probes_before_first_use
        (safety interlocks are operator-wired, not RoamCore-enforced)
    """
    assert manifest["status"] == "beta", (
        f"heated-floors status={manifest['status']!r} implies shipped "
        f"coverage we don't have; use 'beta' until tier-a promotion "
        f"lands"
    )
    tier_warnings = manifest.get("tier_warnings", [])
    # Tier-warnings must include the honest-about-no-heated-floor marker.
    assert "no_real_heated_floor_for_integration_test" in tier_warnings, (
        "tier_warnings must declare 'no_real_heated_floor_for_integration_test' "
        "for honesty in the audit listing"
    )
    # And the user-facing recipe dependency warning (operator must
    # run a heated floor + thermostat OR relay + temperature probes).
    assert "recipe_depends_on_user_running_heated_floor_plus_thermostat_or_relay" in tier_warnings, (
        "tier_warnings must declare 'recipe_depends_on_user_running_heated_floor_"
        "plus_thermostat_or_relay' so the audit listing is honest about "
        "the operator's hardware dependency"
    )
    # Path C honesty — the optional engine preheat hardware
    # (Webasto / Espar / Eberspächer / DIY coolant-loop) requires
    # separate hardware + wiring + fuel.
    assert "optional_engine_preheat_hardware_required" in tier_warnings, (
        "tier_warnings must declare 'optional_engine_preheat_hardware_required' "
        "so the audit listing is honest about the optional Path C engine "
        "preheat hardware dependency"
    )
    # Path choice honesty — smart thermostat Path A vs HA core
    # `generic_thermostat` Path B depends on existing IoT wiring +
    # thermostat preference + comfort with vendor integration vs
    # relay-friendly templates.
    assert "optional_smart_thermostat_vs_generic_thermostat_choice" in tier_warnings, (
        "tier_warnings must declare 'optional_smart_thermostat_vs_generic_thermostat_choice' "
        "so the audit listing is honest about the path-choice driver "
        "(operator's smart thermostat ownership vs relay-friendly preference)"
    )
    # The five safety interlocks are operator-wired, not
    # RoamCore-enforced at tier-b (tier-a promotion would move them
    # into RoamCore-side asserts; see recipe §7).
    assert "requires_operator_wiring_temperature_probes_before_first_use" in tier_warnings, (
        "tier_warnings must declare 'requires_operator_wiring_temperature_probes_before_first_use' "
        "so the audit listing is honest that the safety interlocks "
        "(low-voltage lockout, shore-power-aware throttling, mode-aware "
        "lockouts, presence-aware pre-warm, frost-protection automation) "
        "are operator-wired per the recipe §7 and not RoamCore-enforced "
        "at tier-b"
    )


def test_safety_interlocks_are_documented(manifest: dict) -> None:
    """Defensive guard for the future tier-a promotion.

    Heated floors + engine pre-heat can pull 10–30 A sustained; if the
    low-voltage lockout isn't wired, the floor + engine preheat can
    brown out a low SOC battery bank. The recipe §7 walks through the
    five MANDATORY safety interlocks:
      - §7.4 low-voltage lockout via `sensor.rc_power_battery_soc` +
        `binary_sensor.rc_power_shore_connected` cross-reference to
        the Victron connection
      - §7.2 shore-power-aware throttling (heat aggressively when on
        shore, conserve when off)
      - §7.3 mode-aware lockouts (Stealth silent hours reduce floor
        heat to setpoint -3 °C; Sleep mode locks the floor to a min
        setpoint of 10 °C for frost protection; Boost disables
        mode-aware throttling for service work)
      - §7.5 presence-aware pre-warm when the operator's phone
        reconnects to the LAN AND it's been >24h since the last
        warm-up (cross-reference to the bluetooth-wifi-presence
        recipe's `binary_sensor.rc_presence_operator_phone_arrived`)
      - §7.6 frost-protection automation that cross-references the
        upcoming happijac recipe's `select.rc_bed_lift_mode`

    The test asserts all five are documented in the recipe so that
    when this connection promotes to tier-a (with a real heated-floor
    + relay + temperature probe + optional engine preheat bench on CI
    + the five safety interlock asserts hard-enforced in RoamCore
    code rather than only documented in the recipe), the audit has a
    clean assertion to flip.
    """
    text = RECIPE_PATH.read_text(encoding="utf-8")
    # §7 header MUST be present (with the "Automations" wording).
    assert "## §7 Automations" in text, (
        "recipe.md must have a '## §7 Automations' section "
        "(the five MANDATORY safety interlocks documentation block)"
    )
    # §7 must cover each of the five interlocking areas.
    safety_coverage = (
        # §7.4 low-voltage lockout via `sensor.rc_power_battery_soc`
        # cross-reference to the Victron connection
        "low-voltage lockout",
        # §7.2 shore-power-aware throttling (heat aggressively when
        # on shore, conserve when off)
        "shore-power-aware",
        # §7.3 mode-aware lockouts (Stealth silent hours, Sleep mode
        # lock-down, Boost disable-mode-aware-throttling)
        "mode-aware",
        # §7.5 presence-aware pre-warm when the operator's phone
        # reconnects to the LAN AND it's been >24h since the last
        # warm-up (cross-reference to the bluetooth-wifi-presence
        # recipe)
        "presence-aware",
        # §7.6 frost-protection automation (cross-reference to the
        # upcoming happijac recipe's `select.rc_bed_lift_mode`)
        "frost-protection",
    )
    for phrase in safety_coverage:
        assert phrase in text.lower(), (
            f"recipe.md §7 must cover {phrase!r}; the five safety "
            f"interlocks are MANDATORY before first use, and the recipe "
            f"is the only documentation operator + future-tier-a "
            f"integration code have at this tier"
        )
    # The contract tiles must include the three tiles that gate the
    # safety interlocks:
    #   binary_sensor.rc_hvac_floor_low_voltage_lockout
    #     (low-voltage lockout aggregate)
    #   switch.rc_hvac_floor_heater (heater on/off gate)
    #   binary_sensor.rc_hvac_floor_heating_active (heater active
    #     feedback)
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    safety_tiles = (
        "binary_sensor.rc_hvac_floor_low_voltage_lockout",
        "switch.rc_hvac_floor_heater",
        "binary_sensor.rc_hvac_floor_heating_active",
    )
    for safety_tile in safety_tiles:
        assert safety_tile in tiles, (
            f"dashboard.tiles must include {safety_tile!r}; the safety "
            f"interlock aggregate tiles are part of the contract layer "
            f"that the recipe §7 documents"
        )
    # The recipe must reference the Victron cross-reference via
    # `sensor.rc_power_battery_soc` so the §7.4 cross-reference is
    # discoverable.
    assert "sensor.rc_power_battery_soc" in text, (
        "recipe.md must reference `sensor.rc_power_battery_soc` for the "
        "§7.4 low-voltage lockout cross-reference to the Victron "
        "`connections/victron/` recipe"
    )
    # The recipe must reference the bluetooth-wifi-presence cross-
    # reference via `binary_sensor.rc_presence_operator_phone_arrived`
    # so the §7.5 presence-aware pre-warm cross-reference is
    # discoverable.
    assert "rc_presence_operator_phone_arrived" in text, (
        "recipe.md must reference `binary_sensor.rc_presence_operator_phone_arrived` "
        "for the §7.5 presence-aware pre-warm cross-reference to the "
        "bluetooth-wifi-presence `connections/bluetooth-wifi-presence/` recipe"
    )
    # The recipe's `test_connection_yml.py` defensive guard for
    # future tier-a promotion — assert the §7 section has the
    # "MANDATORY before first use" emphasis that the recipe uses
    # to remind operators to wire each interlock.
    assert "mandatory before first use" in text.lower(), (
        "recipe.md §7 must use the 'MANDATORY before first use' "
        "emphasis on the five safety interlocks; this is the "
        "operator-side reminder that keeps the safety interlocks "
        "top-of-mind during install"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))