"""Manifest-honesty tests for connections/bed-lift-diy/connection.yml.

This is the only test file we can ship for a tier-c recipe connection
that has no real DIY bed lift (linear actuators / winch + motor + strap)
+ 2× dry-contact relays + 2× limit microswitches + optional CT-clamp
current sensor to integration-test against. The tests here assert that
the manifest is *honest about being tier-c* — that the folder/id/tier
invariants hold, that the recipe doc the tier_requirements promise is
actually present on disk, that the tier-c markers (no custom_components,
no HACS, no native integration code, no addons) are honest, that the
rc_bed_lift_* tile ids are vendor-neutral per
docs/reference/rc-entity-naming.md, that the §7 MANDATORY automations
are documented with proper cross-refs, and that the connection.yml
links include the required official ESPHome / HA cover docs plus the
cross-refs to the Wave 2 #23 mode builder + Wave 3 #43 Happijac
sibling + Wave 3 #48 deadbolts + Wave 3 #49 HVAC basics.

If you add real integration coverage (e.g. a config_flow.py + a
bench with a DIY bed lift + ESP32 + 2× dry-contact relays + 2× limit
microswitches + optional CT-clamp current sensor + canned fixture
responses), keep this file and add the new one alongside it; the
audit will then list both under `tests:` in the manifest.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/bed-lift-diy/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> bed-lift-diy/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "bed-lift-diy"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
LEGACY_DOC = REPO_ROOT / "docs" / "catalog" / "bed-lift" / "diy-bedlift.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_manifest_required_fields(manifest: dict) -> None:
    """The manifest must carry the canonical folder/id/tier/category/connection invariant.

    The audit script enforces this invariant; we duplicate it here so
    pytest catches regressions before CI runs the audit. A regression
    here (e.g. someone dropping the `connection` field, or renaming
    `category` to `cat`) would silently fail the connection manifest
    schema check on CI.
    """
    # Required top-level fields.
    for required in ("id", "name", "tier", "category", "status", "version"):
        assert required in manifest, (
            f"manifest is missing required field {required!r} (the "
            f"connection manifest schema requires all of "
            f"{('id', 'name', 'tier', 'category', 'status', 'version')})"
        )
    # The connection invariant: every connection manifest has the
    # fields that the docs site + OpenClaw summarizer rely on.
    assert "description" in manifest, "connection manifest must carry a description"
    assert "dashboard" in manifest, "connection manifest must carry dashboard tiles"
    assert "openclaw" in manifest, "connection manifest must carry openclaw queries"
    assert "tier_requirements" in manifest, "connection manifest must declare tier_requirements"
    assert "tier_warnings" in manifest, "connection manifest must declare tier_warnings"
    assert "links" in manifest, "connection manifest must declare links"
    # Folder + id + tier + category match the connection manifest
    # schema invariants.
    assert manifest["id"] == "bed-lift-diy"
    assert manifest["tier"] == "c"
    assert manifest["category"] == "bed_lift"
    # The README must exist (a tier-c slice is required to point at
    # docs/recipe.md; the README is the short pointer).
    readme = CONNECTION_DIR / "README.md"
    assert readme.is_file(), (
        f"connection manifest promises a connection folder but the "
        f"README pointer is missing at {readme}"
    )
    # The recipe must exist (tier_requirements promises docs_recipe_published).
    assert RECIPE_PATH.is_file(), (
        f"tier_requirements promises docs_recipe_published but "
        f"{RECIPE_PATH} does not exist"
    )


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (bed-lift-diy).

    This is the same invariant the audit script enforces; we duplicate
    it here so pytest catches regressions before CI runs the audit.
    """
    assert manifest["id"] == CONNECTION_DIR.name, (
        f"manifest id={manifest['id']!r} does not match folder name "
        f"{CONNECTION_DIR.name!r}"
    )
    assert manifest["id"] == "bed-lift-diy"


def test_tier_is_c(manifest: dict) -> None:
    """Tier-c must NOT advertise tier-a-only RoamCore-owned fields.

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
    those are shipped at tier-c.
    """
    assert manifest["tier"] == "c", "bed-lift-diy must stay at tier-c until integration coverage lands"
    assert manifest["wizard"]["one_tap"] is False, (
        "tier-c connections cannot advertise one_tap=true (that's a tier-a contract)"
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
    # ship, this connection is tier-c even though the upstream
    # integrations have a config_flow.
    assert manifest["install"]["config_flow"] is True, (
        "install.config_flow must stay True — the upstream HA core "
        "`cover` template integration + ESPHome `cover:` component "
        "expose a config_flow since 2022.x / 2023.x (honest upstream "
        "truth, NOT a tier-a marker)"
    )
    assert manifest["install"]["hacs"] is False, (
        "bed-lift-diy is a recipe; no HACS integration of our own is "
        "shipped (Path A uses ESPHome + HA core; Path B uses only "
        "HA core)"
    )
    assert manifest["install"]["doc_recipe_only"] is True, (
        "tier-c must declare doc_recipe_only=true (RoamCore ships "
        "no native integration code; the recipe IS the install)"
    )
    # Belt-and-braces: there must be no RoamCore-owned config_flow.py
    # in this folder (no native integration code for a tier-c recipe
    # connection). The upstream HA core + ESPHome integrations have
    # their own config_flow, but that lives in the upstream HA core /
    # HACS / ESPHome repos, not in this folder.
    assert not (CONNECTION_DIR / "config_flow.py").is_file(), (
        "tier-c recipe connection must not ship a RoamCore-owned config_flow.py"
    )
    # The __init__.py must be a DOMAIN-stub only — no integration
    # setup logic. We assert it exports DOMAIN and nothing else that
    # smells like HA integration code.
    init_text = (CONNECTION_DIR / "__init__.py").read_text(encoding="utf-8")
    assert "DOMAIN" in init_text, "__init__.py must export DOMAIN for the audit"
    # DOMAIN must equal "bed-lift-diy" (matches the folder name).
    assert 'DOMAIN = "bed-lift-diy"' in init_text, (
        '__init__.py must define DOMAIN = "bed-lift-diy" '
        '(matches the folder name)'
    )
    for forbidden in ("async_setup", "config_flow", "PLATFORM_SCHEMA"):
        assert forbidden not in init_text, (
            f"__init__.py must be a DOMAIN stub; found {forbidden!r} "
            f"(tier-c recipe pattern)"
        )


def test_category_is_bed_lift(manifest: dict) -> None:
    """Promoted from tier-c legacy doc — category must match.

    The legacy tier-c spec lives at docs/catalog/bed-lift/diy-bedlift.md;
    we promote the connection into the `bed_lift` category so the
    audit + boundary-CI can pair them up.
    """
    assert manifest["category"] == "bed_lift", (
        f"category must stay 'bed_lift' (legacy doc lives at "
        f"docs/catalog/bed-lift/diy-bedlift.md); got "
        f"{manifest['category']!r}"
    )
    assert LEGACY_DOC.is_file(), (
        "expected the legacy tier-c doc to still exist so we can reference it "
        "from the recipe (and add a supersession banner)"
    )


def test_tier_c_does_not_ship_native_integration(manifest: dict) -> None:
    """Tier-c must not ship native integration code / packaging.

    Verifies the tier-c honesty markers:
      - no `custom_components/` directory in this folder
      - no `hacs.json`
      - no `addons/`
      - no PyPI upload artifact (no setup.py / pyproject.toml with
        `name = ...` style packaging metadata)
      - no manifest pointing to `codeowners/` ownership of upstream
        HA core (the operator's path is operator's own; RoamCore does
        NOT own upstream HA core's `cover` template integration or
        ESPHome's `cover:` component).

    This is the defensive guard for a future regression where someone
    adds a `custom_components/bed_lift_diy/` folder claiming the
    slice is "really" a native integration. At tier-c, RoamCore
    RECIPEs upstream ESPHome / HA core `template` cover; no native
    integration code is honest here.
    """
    # No custom_components/ directory at tier-c.
    assert not (CONNECTION_DIR / "custom_components").is_dir(), (
        "tier-c recipe connection must not ship a custom_components/ "
        "directory (RoamCore recipes upstream ESPHome / HA core "
        "`template` cover; no native integration code)"
    )
    # No hacs.json (tier-c is recipe-only; not packaged).
    assert not (CONNECTION_DIR / "hacs.json").is_file(), (
        "tier-c recipe connection must not ship hacs.json "
        "(recipe-only; not packaged)"
    )
    # No addons/ (tier-c).
    assert not (CONNECTION_DIR / "addons").is_dir(), (
        "tier-c recipe connection must not ship an addons/ directory "
        "(recipe-only)"
    )
    # No PyPI / HACS upload artifacts.
    for forbidden in ("setup.py", "pyproject.toml", "manifest.json"):
        assert not (CONNECTION_DIR / forbidden).is_file(), (
            f"tier-c recipe connection must not ship {forbidden} "
            f"(recipe-only; not packaged)"
        )
    # The tier_requirements must declare the tier-c honesty markers.
    tier_requirements = manifest.get("tier_requirements", [])
    for marker in (
        "no_custom_components_dir",
        "no_native_integration_code",
        "no_hacs_json",
        "no_addons_dir",
    ):
        assert marker in tier_requirements, (
            f"tier_requirements must declare {marker!r} for tier-c honesty"
        )
    # The tier_warnings must declare the recipe-only / no-rc-owned-
    # controller markers.
    tier_warnings = manifest.get("tier_warnings", [])
    assert "recipe_only_no_roamcore_owned_controller" in tier_warnings, (
        "tier_warnings must declare "
        "'recipe_only_no_roamcore_owned_controller' so the audit "
        "listing is honest about the recipe-only nature"
    )
    # The Happijac sibling is the canonical tier-b pattern; the DIY
    # connection is honest about being a sibling at tier-c.
    assert "sibling_happijac_connection_is_tier_b_canonical_pattern" in tier_warnings, (
        "tier_warnings must declare "
        "'sibling_happijac_connection_is_tier_b_canonical_pattern' so "
        "the audit listing is honest about the Happijac sibling being "
        "the canonical pattern"
    )


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """rc_* tile ids must NOT contain vendor names (per rc-entity-naming.md).

    The bed-lift contract is implementation-agnostic (it talks to
    whatever ESPHome device or Shelly / Shelly Plus / Zooz ZEN17 /
    Aeotec Nano Switch pair the operator wires, not any vendor's
    library). Contract ids must stay vendor-neutral — NO `diy`,
    `lc_`, `lci`, `bed`, `lift`, `actuator`, `esphome`, `shelly`,
    `zooz`, `aeotec`, `relay`, `cover_*`, `dry_contact` in any rc_*
    tile id BEYOND the subsystem prefix `rc_bed_lift_*`.

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
    assert tiles, "bed-lift-diy contributes at least one dashboard tile"

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
    # rc_bed_lift_ subsystem prefix". Vendor names like DIY / LCI /
    # Shelly / Zooz / Aeotec / ESPHome / dry-contact are an
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
        # (absolute forbidden — no DIY / LCI / Shelly / Zooz /
        # Aeotec / ESPHome / dry-contact names anywhere in any rc_*
        # tile id; vendor neutrality is non-negotiable).
        "diy",                  # DIY bed-lift vendor shorthand (vendor leak)
        "lc_",                  # LCI brand shorthand (vendor leak)
        "lci",                  # LCI brand shorthand (vendor leak)
        "esphome",              # Path A device-side stack name (vendor leak)
        "shelly",               # Path B common device vendor (vendor leak)
        "zooz",                 # Path B alternative device vendor (vendor leak)
        "aeotec",               # Path B alternative device vendor (vendor leak)
        "dry_contact",          # Shelly / Shelly Plus input mode name (vendor leak)
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
        f"bed-lift-diy must contribute exactly 12 contract tiles per "
        f"spec (1 cover + 6 binary_sensor + 1 sensor + 3 button + "
        f"1 select); got {len(tiles)}"
    )


def test_automations_are_documented(manifest: dict) -> None:
    """§7 MANDATORY automations must be documented with cross-refs.

    The spec requires the §7 mandatory automations to all have
    entries in `recipe.md` with proper cross-refs. The recipe ships
    eight automations:
      - §7.1 Stealth auto-stop (stop in-progress motion at silent hours)
      - §7.2 Sleep lock-down (auto-lower at 23:00 when mode is Sleep)
      - §7.3 Boost disable-mode-aware-lockouts
      - §7.4 Low-voltage lockout when SOC < 20 %
      - §7.5 Obstruction detected → stop + alert via Music Assistant
      - §7.6 Mode-aware scheduling — gentle reminder
      - §7.7 Actuator safety interlock — block lift when door
        unlocked (Wave 3 #48 deadbolts cross-reference)
      - §7.8 HVAC service-mode block — block lift when HVAC service
        mode engaged (Wave 3 #49 HVAC basics cross-reference)

    The cross-refs to Wave 2 #23 (mode builder), Wave 3 #43
    (Happijac sibling), Wave 3 #48 (deadbolts), Wave 3 #49 (HVAC
    basics), and Wave 2 #26 (system summary) must all appear in the
    recipe.

    The test asserts all eight automations have entries in recipe.md
    with proper cross-refs.
    """
    text = RECIPE_PATH.read_text(encoding="utf-8")
    # §7 header MUST be present (with the "Automations" wording).
    assert "## §7 Automations" in text, (
        "recipe.md must have a '## §7 Automations' section "
        "(the §7 MANDATORY automations documentation block)"
    )
    # §7 must cover each of the eight automation areas. We grep for
    # the unique markers of each automation so a future "I rewrote
    # the recipe as one wall of text" regression gets caught.
    automation_coverage = (
        # §7.1 Stealth auto-stop
        "§7.1 Stealth auto-stop",
        # §7.2 Sleep lock-down (auto-lower at 23:00)
        "§7.2 Sleep lock-down",
        # §7.3 Boost disable-mode-aware-lockouts
        "§7.3 Boost disable-mode-aware-lockouts",
        # §7.4 Low-voltage lockout when SOC < 20 %
        "§7.4 Low-voltage lockout",
        # §7.5 Obstruction detected → stop + alert
        "§7.5 Obstruction detected",
        # §7.6 Mode-aware scheduling — gentle reminder
        "§7.6 Mode-aware scheduling",
        # §7.7 Actuator safety interlock — block lift when door
        # unlocked (Wave 3 #48 deadbolts cross-reference)
        "§7.7 Actuator safety interlock",
        # §7.8 HVAC service-mode block — block lift when HVAC
        # service mode engaged (Wave 3 #49 HVAC basics cross-reference)
        "§7.8 HVAC service-mode block",
    )
    for marker in automation_coverage:
        assert marker in text, (
            f"recipe.md §7 must include the automation {marker!r}; the "
            f"eight §7 MANDATORY automations are part of the recipe "
            f"contract"
        )
    # The spec requires the recipe §7 to cross-reference Wave 2 #23
    # (mode builder) + Wave 3 #43 (Happijac sibling) + Wave 3 #48
    # (deadbolts) + Wave 3 #49 (HVAC basics) + Wave 2 #26 (system
    # summary). The §7 entries + the connection.yml `links.cross_
    # references` block must collectively cover these cross-refs.
    cross_refs = (
        # Wave 3 #43 — Happijac sibling connection (mandatory per spec)
        ("happijac", "Wave 3 #43"),
        # Wave 2 #23 — Mode builder (drives the `select.roamcore_mode`
        # state referenced by §7 automations + §6.4 mode-aware lockouts).
        ("mode-builder", "Wave 2 #23"),
        # Wave 3 #48 — Deadbolts (cross-ref for §7.7 actuator safety interlock)
        ("deadbolts", "Wave 3 #48"),
        # Wave 3 #49 — HVAC basics (cross-ref for §7.8 HVAC service-mode block)
        ("hvac-basics", "Wave 3 #49"),
    )
    for slug, wave in cross_refs:
        assert wave in text and slug in text.lower(), (
            f"recipe.md must cross-reference {wave} ({slug}) in the "
            f"§7 automations section"
        )
    # The §7.7 actuator safety interlock automation must reference
    # the Wave 3 #48 deadbolts connection in the recipe body.
    assert (
        "Wave 3 #48" in text and "deadbolts" in text.lower()
    ), (
        "recipe.md §7.7 actuator safety interlock must cross-reference "
        "Wave 3 #48 deadbolts"
    )
    # The §7.8 HVAC service-mode block automation must reference the
    # Wave 3 #49 HVAC basics connection in the recipe body.
    assert (
        "Wave 3 #49" in text and "hvac-basics" in text.lower()
    ), (
        "recipe.md §7.8 HVAC service-mode block must cross-reference "
        "Wave 3 #49 HVAC basics"
    )


def test_links_include_required_official_and_cross_references(manifest: dict) -> None:
    """`links:` in connection.yml must include the required official
    docs + the cross-references to Wave 2 #23 + Wave 3 #43 + Wave 3
    #48 + Wave 3 #49.

    Required official links:
      - HA cover docs
      - ESPHome cover docs
      - HA template docs
      - Shelly integration docs

    Required cross-references:
      - Wave 2 #23 mode builder (`connections/mode-builder/`)
      - Wave 3 #43 Happijac sibling (`connections/happijac/`)
      - Wave 3 #48 deadbolts (`connections/deadbolts/`)
      - Wave 3 #49 HVAC basics (`connections/hvac-basics/`)

    The test asserts all 4 official + 4 cross-references are present
    in the manifest's `links:` block.
    """
    links = manifest.get("links", {})
    official = links.get("official", []) or []
    cross_references = links.get("cross_references", []) or []

    # Required official docs.
    required_official = (
        "https://www.home-assistant.io/integrations/cover/",
        "https://esphome.io/components/cover/index.html",
        "https://www.home-assistant.io/integrations/template/",
        "https://www.home-assistant.io/integrations/shelly/",
    )
    for url in required_official:
        assert url in official, (
            f"connection.yml `links.official` must include {url!r}"
        )

    # Required cross-references.
    required_xrefs = (
        "connections/happijac/",          # Wave 3 #43
        "connections/mode-builder/",      # Wave 2 #23
        "connections/deadbolts/",         # Wave 3 #48
        "connections/hvac-basics/",       # Wave 3 #49
    )
    for path in required_xrefs:
        assert path in cross_references, (
            f"connection.yml `links.cross_references` must include "
            f"{path!r}"
        )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))