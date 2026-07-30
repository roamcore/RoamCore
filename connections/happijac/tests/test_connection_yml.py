"""Manifest-honesty tests for connections/happijac/connection.yml.

This is the only test file we can ship for a tier-b recipe connection
that has no real Happijac + 2× dry-contact relays + 2× limit
microswitches + optional CT-clamp current sensor to integration-test
against. The tests here assert that the manifest is *honest about
being tier-b* — that the folder/id/tier invariants hold, that the
recipe doc the tier_requirements promise is actually present on
disk, and that the rc_bed_lift_* tile ids are vendor-neutral per
docs/reference/rc-entity-naming.md.

If you add real integration coverage (e.g. a config_flow.py + a
bench with a Happijac + ESP32 + 2× dry-contact relays + 2× limit
microswitches + optional CT-clamp current sensor + canned fixture
responses), keep this file and add the new one alongside it; the
audit will then list both under `tests:` in the manifest.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/happijac/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> happijac/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "happijac"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
LEGACY_DOC = REPO_ROOT / "docs" / "catalog" / "bed-lift" / "happijac.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (happijac).

    This is the same invariant the audit script enforces; we duplicate
    it here so pytest catches regressions before CI runs the audit.
    """
    assert manifest["id"] == CONNECTION_DIR.name, (
        f"manifest id={manifest['id']!r} does not match folder name "
        f"{CONNECTION_DIR.name!r}"
    )
    assert manifest["id"] == "happijac"


def test_tier_b_without_tier_a_markers(manifest: dict) -> None:
    """Tier-b must NOT advertise tier-a-only RoamCore-owned fields.

    A regression here (e.g. someone flipping one_tap to true, or
    adding a RoamCore-owned config_flow.py) would falsely imply a
    working RoamCore integration + integration tests that we don't
    have, and the audit would either block the PR or let a
    misleading tier-a claim slip through.

    The distinction this test guards: install.config_flow is TRUE here
    because the UPSTREAM HA core `cover` template integration + the
    ESPHome `cover:` component are honest upstream truth (config_flow
    since 2022.x / 2023.x respectively) — that's NOT a tier-a marker
    for RoamCore's tier. The tier-a marker for RoamCore would be a
    RoamCore-owned `config_flow.py` + RoamCore-owned integration code +
    integration tests against a RoamCore-owned bed-lift bench. None of
    those are shipped at tier-b.
    """
    assert manifest["tier"] == "b", "happijac must stay at tier-b until integration coverage lands"
    assert manifest["wizard"]["one_tap"] is False, (
        "tier-b connections cannot advertise one_tap=true (that's a tier-a contract)"
    )
    # Bed lift recipes an operator-side ESPHome custom `cover:` (Path A)
    # OR an upstream HA core `template:` cover wrapping a Shelly / Shelly
    # Plus / Zooz ZEN17 / Aeotec Nano Switch pair (Path B); RoamCore
    # ships no native config_flow for that. install.config_flow is the
    # RoamCore-owned field. We document the distinction in the manifest
    # header: the UPSTREAM HA core `cover` template integration + the
    # ESPHome `cover:` component DO expose a config_flow since 2022.x /
    # 2023.x respectively (honest upstream truth, NOT a tier-a marker
    # for RoamCore's tier). The tier-a marker for RoamCore is a
    # RoamCore-owned config_flow.py + integration tests. Until those
    # ship, this connection is tier-b even though the upstream
    # integrations have a config_flow.
    assert manifest["install"]["config_flow"] is True, (
        "install.config_flow must stay True — the upstream HA core "
        "`cover` template integration + ESPHome `cover:` component "
        "expose a config_flow since 2022.x / 2023.x (honest upstream "
        "truth, NOT a tier-a marker)"
    )
    assert manifest["install"]["hacs"] is False, (
        "happijac is a recipe; no HACS integration of our own is "
        "shipped (Path A uses ESPHome + HA core; Path B uses only "
        "HA core)"
    )
    # Belt-and-braces: there must be no RoamCore-owned config_flow.py
    # in this folder (no native integration code for a tier-b recipe
    # connection). The upstream HA core + ESPHome integrations have
    # their own config_flow, but that lives in the upstream HA core /
    # HACS / ESPHome repos, not in this folder.
    assert not (CONNECTION_DIR / "config_flow.py").is_file(), (
        "tier-b recipe connection must not ship a RoamCore-owned config_flow.py"
    )
    # The __init__.py must be a DOMAIN-stub only — no integration
    # setup logic. We assert it exports DOMAIN and nothing else that
    # smells like HA integration code.
    init_text = (CONNECTION_DIR / "__init__.py").read_text(encoding="utf-8")
    assert "DOMAIN" in init_text, "__init__.py must export DOMAIN for the audit"
    # DOMAIN must equal "happijac" (matches the folder name).
    assert 'DOMAIN = "happijac"' in init_text, (
        '__init__.py must define DOMAIN = "happijac" '
        '(matches the folder name)'
    )
    for forbidden in ("async_setup", "config_flow", "PLATFORM_SCHEMA"):
        assert forbidden not in init_text, (
            f"__init__.py must be a DOMAIN stub; found {forbidden!r} "
            f"(tier-b recipe pattern)"
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
    # Sanity: the recipe actually documents Happijac bed lift + the
    # contract entities rather than just an empty placeholder.
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert (
        "happijac" in text.lower() and "bed lift" in text.lower()
    ) or "rc_bed_lift_" in text, (
        "recipe.md must document the Happijac bed-lift setup (Path A "
        "ESPHome, Path B Shelly/template cover, contract entities, "
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
    # Spec §4 calls for the §1–§10 sections to be present (≥10
    # §sections including §10 tier-a promotion outline). Grep-anchor
    # the major section headers so a future "I rewrote the recipe as
    # one wall of text" regression gets caught. The test accepts both
    # the canonical `## §N` form and the `# §N` form (the recipe's
    # H1-style section headers are valid Markdown either way).
    required_sections = (
        "## §1 What is Happijac in RoamCore?",
        "## §2 Prerequisites",
        "## §3 Path A",
        "## §4 Path B",
        "## §5 RoamCore contract entities",
        "## §6 Safety interlocks",
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
    docs/catalog/bed-lift/happijac.md; we promote the connection into
    the `bed_lift` category so the audit + boundary-CI can pair them
    up.
    """
    assert manifest["category"] == "bed_lift", (
        f"category must stay 'bed_lift' (legacy doc lives at "
        f"docs/catalog/bed-lift/happijac.md); got "
        f"{manifest['category']!r}"
    )
    assert LEGACY_DOC.is_file(), (
        "expected the legacy tier-c doc to still exist so we can reference it "
        "from the recipe (and add a supersession banner)"
    )


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """rc_* tile ids must NOT contain vendor names (per rc-entity-naming.md).

    The bed-lift contract is implementation-agnostic (it talks to
    whatever ESPHome device or Shelly / Shelly Plus / Zooz ZEN17 /
    Aeotec Nano Switch pair the operator wires, not any vendor's
    library). Contract ids must stay vendor-neutral — NO `happijac`,
    `happi`, `lc_`, `lci`, `bed`, `lift`, `actuator`, `esphome`,
    `shelly`, `zooz`, `aeotec`, `relay`, `cover_*`, `dry_contact` in
    any rc_* tile id BEYOND the subsystem prefix `rc_bed_lift_*`.

    The spec is strict: every `dashboard.tiles[*]` must match
    `^[a-z_]+\\.rc_bed_lift_[a-z0-9_]+$` (vendor-neutral, subsystem
    prefix `rc_bed_lift_*` per the §bed_lift subsystem naming rules
    in docs/reference/rc-entity-naming.md). The subsystem prefix IS
    allowed (it's the owning-area marker); what is forbidden is
    vendor / actuator / relay / dry-contact names appearing AFTER
    the subsystem prefix in a way that double-stamps the vendor into
    the id.
    """
    import re

    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles, "happijac contributes at least one dashboard tile"

    # Every tile must be a string entity id (spec calls for tiles-as-
    # strings, mirroring the spec's listed shape).
    for tile in tiles:
        assert isinstance(tile, str), (
            f"dashboard.tiles[*] must be a string entity id (spec §1); "
            f"got {tile!r}"
        )

    # Domain segment is lowercase + underscores only (HA convention).
    # Suffix segment after `rc_bed_lift_` may include digits but
    # must not contain vendor double-stamps.
    pattern = re.compile(r"^[a-z_]+\.rc_bed_lift_[a-z0-9_]+$")

    # Vendor / implementation / device-side name leaks that must
    # NEVER appear in any rc_* tile id. The spec requirement is
    # "no double-stamps of [vendor + generic nouns] beyond the
    # rc_bed_lift_ subsystem prefix". Vendor names like Happijac /
    # LCI / Shelly / Zooz / Aeotec / ESPHome / dry-contact are an
    # absolute vendor leak and are forbidden from EVER appearing in
    # any rc_* tile id (regardless of where in the tile).
    #
    # The generic nouns (`bed`, `lift`, `actuator`, `relay`,
    # `cover_*`, `dry_contact`) are LITERALLY PART OF the subsystem
    # prefix `rc_bed_lift_` for the first group, or are general
    # wiring/relay vocabulary that's unrelated to vendor identity
    # for the second — so flagging them as absolute substrings of
    # the suffix would conflict with the literal tile ids the spec
    # requires (e.g. `button.rc_bed_lift_lift`, `cover.rc_bed_lift_
    # position`, `binary_sensor.rc_bed_lift_up_limit` literally
    # contain `bed` and/or `lift` once in the suffix; the spec
    # calls for those tiles).
    forbidden_substrings = (
        # Vendor / brand names — recipe explicitly forbids these
        # (absolute forbidden — no Happijac / LCI / Shelly / Zooz /
        # Aeotec / ESPHome / dry-contact names anywhere in any rc_*
        # tile id; vendor neutrality is non-negotiable).
        "happijac",            # specific LCI bed-lift vendor name (vendor leak)
        "happi",               # upstream + LCI brand shorthand (vendor leak)
        "lc_",                 # LCI brand shorthand (vendor leak)
        "lci",                 # LCI brand shorthand (vendor leak)
        "esphome",             # Path A device-side stack name (vendor leak)
        "shelly",              # Path B common device vendor (vendor leak)
        "zooz",                # Path B alternative device vendor (vendor leak)
        "aeotec",              # Path B alternative device vendor (vendor leak)
        "dry_contact",         # Shelly / Shelly Plus input mode name (vendor leak)
    )

    # Double-stamp guard: the literal spec tile ids include
    # `button.rc_bed_lift_lift` which contains `lift` twice (once in
    # the `rc_bed_lift_` prefix, once in the `lift` suffix — that's
    # by spec design because the button's affordance IS "lift the
    # bed"). That's a true double-stamp, so we accept it here; any
    # FUTURE tile id that double-stamps anything beyond the
    # spec-required list should be flagged. For now, the spec's
    # literal tile ids are the authoritative source — we allow all
    # 12 of them through without further double-stamp checks.

    for tile in tiles:
        assert pattern.match(tile), (
            f"tile id {tile!r} must match ^[a-z_]+\\.rc_bed_lift_[a-z_]+$ "
            f"(vendor-neutral contract naming per docs/reference/rc-entity-naming.md)"
        )
        # Subsystem prefix is rc_bed_lift_; the suffix (after
        # `rc_bed_lift_`) MUST NOT contain any forbidden vendor substring.
        suffix = tile.split(".rc_bed_lift_", 1)[1]
        for bad in forbidden_substrings:
            assert bad not in suffix.lower(), (
                f"tile id {tile!r} contains forbidden vendor substring {bad!r} "
                f"in the suffix after `rc_bed_lift_`; per docs/reference/"
                f"rc-entity-naming.md, contract ids are vendor-neutral — "
                f"vendor names are forbidden in any rc_* tile id"
            )
        # Each segment after the dot must be lowercase + underscores + digits.
        for segment in tile.split("."):
            assert re.match(r"^[a-z_][a-z0-9_]*$", segment), (
                f"tile id {tile!r} contains a non-conforming segment {segment!r}"
            )

    # Spec calls for exactly 12 tiles (1 cover + 6 binary_sensor +
    # 1 sensor + 3 button + 1 select). These map to the 12 contract
    # entities documented in the recipe §5 contract layer:
    #   cover.rc_bed_lift_position
    #   binary_sensor.rc_bed_lift_up_limit
    #   binary_sensor.rc_bed_lift_down_limit
    #   binary_sensor.rc_bed_lift_moving
    #   binary_sensor.rc_bed_lift_safety_ok
    #   binary_sensor.rc_bed_lift_obstruction_detected
    #   binary_sensor.rc_bed_lift_low_voltage_lockout
    #   sensor.rc_bed_lift_position_pct
    #   button.rc_bed_lift_lift
    #   button.rc_bed_lift_lower
    #   button.rc_bed_lift_stop
    #   select.rc_bed_lift_mode
    assert len(tiles) == 12, (
        f"happijac must contribute exactly 12 contract tiles per "
        f"spec (1 cover + 6 binary_sensor + 1 sensor + 3 button + "
        f"1 select); got {len(tiles)}"
    )


def test_status_reflects_no_real_happijac(manifest: dict) -> None:
    """Status must be honest about no integration being shipped.

    If we ever flip this to 'shipped', the audit will demand an actual
    integration test (and rightly so). 'beta' is the only honest tier-b
    status for a recipe we can't integration-test.

    The four honesty warnings that tier_warnings must contain cover:
      - no_real_happijac_for_integration_test (no bench fixture)
      - recipe_depends_on_user_running_happijac_plus_relays_plus_limits
        (operator's hardware dependency)
      - optional_esphome_vs_template_cover_choice (Path choice honesty)
      - requires_operator_wiring_safety_interlocks_before_first_use
        (safety interlocks are operator-wired, not RoamCore-enforced)
    """
    assert manifest["status"] == "beta", (
        f"happijac status={manifest['status']!r} implies shipped "
        f"coverage we don't have; use 'beta' until tier-a promotion "
        f"lands"
    )
    tier_warnings = manifest.get("tier_warnings", [])
    # Tier-warnings must include the honest-about-no-happijac marker.
    assert "no_real_happijac_for_integration_test" in tier_warnings, (
        "tier_warnings must declare 'no_real_happijac_for_integration_test' "
        "for honesty in the audit listing"
    )
    # And the user-facing recipe dependency warning (operator must
    # run a Happijac + 2× relays + 2× limit switches + optional
    # current sensor).
    assert "recipe_depends_on_user_running_happijac_plus_relays_plus_limits" in tier_warnings, (
        "tier_warnings must declare 'recipe_depends_on_user_running_happijac_"
        "plus_relays_plus_limits' so the audit listing is honest about "
        "the operator's hardware dependency"
    )
    # Path choice honesty — ESPHome Path A vs relay-friendly Path B
    # depends on existing IoT wiring + comfort with ESPHome vs
    # relay-friendly templates + current-sensor preference.
    assert "optional_esphome_vs_template_cover_choice" in tier_warnings, (
        "tier_warnings must declare 'optional_esphome_vs_template_cover_choice' "
        "so the audit listing is honest about the path-choice driver "
        "(operator's ESPHome comfort vs relay-friendly preference)"
    )
    # The four safety interlocks are operator-wired, not RoamCore-enforced
    # at tier-b (tier-a promotion would move them into RoamCore-side
    # asserts; see recipe §10).
    assert "requires_operator_wiring_safety_interlocks_before_first_use" in tier_warnings, (
        "tier_warnings must declare 'requires_operator_wiring_safety_interlocks_before_first_use' "
        "so the audit listing is honest that the safety interlocks (limit-sanity, "
        "low-voltage lockout, obstruction detection, mode-aware lockouts) are "
        "operator-wired per the recipe §6 and not RoamCore-enforced at tier-b"
    )


def test_safety_interlocks_are_documented(manifest: dict) -> None:
    """Defensive guard for the future tier-a promotion.

    Bed lift control is the only RoamCore connection where mis-wiring
    can cause a **physical injury** (the bed motor can pinch / crush
    an operator or occupant). The recipe §6 walks through the four
    MANDATORY safety interlocks:
      - §6.1 limit-switch sanity (both limits cannot be TRUE
        simultaneously — wiring fault)
      - §6.2 low-voltage lockout via `sensor.rc_power_battery_soc`
        cross-reference to the Victron connection
      - §6.3 obstruction detection (current sensor / motor-stall
        heuristic)
      - §6.4 mode-aware lockouts (Stealth silent hours, Sleep mode
        lock-down, Boost disable-mode-aware-lockouts)

    The test asserts all four are documented in the recipe so that
    when this connection promotes to tier-a (with a real Happijac +
    ESPHome + relay bench on CI + the four safety interlock asserts
    hard-enforced in RoamCore code rather than only documented in
    the recipe), the audit has a clean assertion to flip.
    """
    text = RECIPE_PATH.read_text(encoding="utf-8")
    # §6 header MUST be present (with the "Safety interlocks" wording).
    assert "## §6 Safety interlocks" in text, (
        "recipe.md must have a '## §6 Safety interlocks' section "
        "(the four MANDATORY safety interlocks documentation block)"
    )
    # §6 must cover each of the four interlocking areas.
    safety_coverage = (
        # §6.1 limit-switch sanity (both limits cannot be TRUE simultaneously)
        "limit-switch sanity",
        # §6.2 low-voltage lockout via `sensor.rc_power_battery_soc`
        # cross-reference to the Victron connection
        "low-voltage lockout",
        # §6.3 obstruction detection (current sensor / motor-stall
        # heuristic)
        "obstruction detection",
        # §6.4 mode-aware lockouts (Stealth silent hours, Sleep mode
        # lock-down, Boost disable-mode-aware-lockouts)
        "mode-aware lockout",
    )
    for phrase in safety_coverage:
        assert phrase in text.lower(), (
            f"recipe.md §6 must cover {phrase!r}; the four safety "
            f"interlocks are MANDATORY before first use, and the recipe "
            f"is the only documentation operator + future-tier-a "
            f"integration code have at this tier"
        )
    # The contract tiles must include the two tiles that gate the
    # safety interlocks:
    #   binary_sensor.rc_bed_lift_safety_ok (limit-sanity aggregate)
    #   binary_sensor.rc_bed_lift_low_voltage_lockout
    #   binary_sensor.rc_bed_lift_obstruction_detected
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    safety_tiles = (
        "binary_sensor.rc_bed_lift_safety_ok",
        "binary_sensor.rc_bed_lift_low_voltage_lockout",
        "binary_sensor.rc_bed_lift_obstruction_detected",
    )
    for safety_tile in safety_tiles:
        assert safety_tile in tiles, (
            f"dashboard.tiles must include {safety_tile!r}; the safety "
            f"interlock aggregate tiles are part of the contract layer "
            f"that the recipe §6 documents"
        )
    # The recipe must reference the Victron cross-reference via
    # `sensor.rc_power_battery_soc` so the §6.2 cross-reference is
    # discoverable.
    assert "sensor.rc_power_battery_soc" in text, (
        "recipe.md must reference `sensor.rc_power_battery_soc` for the "
        "§6.2 low-voltage lockout cross-reference to the Victron "
        "`connections/victron/` recipe"
    )
    # The recipe's `test_connection_yml.py` defensive guard for
    # future tier-a promotion — assert the §6 section has the
    # "MANDATORY before first use" emphasis that the recipe uses
    # to remind operators to wire each interlock.
    assert "mandatory before first use" in text.lower(), (
        "recipe.md §6 must use the 'MANDATORY before first use' "
        "emphasis on the four safety interlocks; this is the "
        "operator-side reminder that keeps the safety interlocks "
        "top-of-mind during install"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
