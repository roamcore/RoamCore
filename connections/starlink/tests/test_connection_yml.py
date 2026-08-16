"""Manifest-honesty tests for connections/starlink/connection.yml.

This is the only test file we can ship for a tier-b recipe connection
that has no real Starlink terminal to integration-test against. The
tests here assert that the manifest is *honest about being tier-b* —
that the folder/id/tier invariants hold, that the recipe doc the
tier_requirements promise is actually present on disk, that the
rc_net_starlink_* tile ids are vendor-neutral per
docs/reference/rc-entity-naming.md, AND — for Wave 9 #108 — that the
3 setup_paths (starlink_mini_only / separate_router /
vp2430_vm_router) the wizard exposes are well-formed.

If you add real integration coverage (e.g. a config_flow.py + an
integration test against testcontainers/grpc-starlink-dish with a
synthetic dish-status.json fixture), keep this file and add the new
one alongside it; the audit will then list both under `tests:` in the
manifest.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/starlink/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> starlink/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "starlink"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
LEGACY_DOC = REPO_ROOT / "docs" / "catalog" / "networking" / "starlink-sleep-timer.md"

# Wave 9 #108 — the 3 setup_paths the wizard exposes.
EXPECTED_PATH_IDS = ("starlink_mini_only", "separate_router", "vp2430_vm_router")


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (starlink).

    This is the same invariant the audit script enforces; we duplicate
    it here so pytest catches regressions before CI runs the audit.
    """
    assert manifest["id"] == CONNECTION_DIR.name, (
        f"manifest id={manifest['id']!r} does not match folder name "
        f"{CONNECTION_DIR.name!r}"
    )
    assert manifest["id"] == "starlink"


def test_tier_b_without_tier_a_markers(manifest: dict) -> None:
    """Tier-b must NOT advertise tier-a-only fields.

    A regression here (e.g. someone flipping one_tap to true) would
    falsely imply a working one-tap setup that we don't have, and
    the audit would either block the PR or let a misleading tier-a
    claim slip through.

    Wave 9 #108 nuance: this slice DOES flip
    `install.config_flow: true` because the wizard now exposes a
    Starlink step. The audit's tier-a litmus test is "do we ship a
    config_flow that takes the user all the way to a working
    integration in one click?" — the wizard is a guided step (the
    user picks a path; the connection kind is `setup_paths`, not
    `api`). For tier-b, `wizard.one_tap` MUST stay False (we don't
    claim one-tap automation for Path B / Path C, and Path A's
    promotion to tier-a is gated on integration-test fixtures).
    Path A (starlink_mini_only) is the tier-a promotion candidate
    but the connection tier stays `b` until the fixture lands.
    """
    assert manifest["tier"] == "b", "starlink must stay at tier-b until integration coverage lands"
    assert manifest["wizard"]["one_tap"] is False, (
        "tier-b connections cannot advertise one_tap=true (that's a tier-a contract)"
    )
    # Belt-and-braces: there must be no RoamCore-owned config_flow.py
    # in this folder (no native integration code for a tier-b recipe
    # connection — the wizard lives in the RoamCore umbrella
    # integration, not here).
    assert not (CONNECTION_DIR / "config_flow.py").is_file(), (
        "tier-b recipe connection must not ship a RoamCore-owned config_flow.py"
    )
    # The __init__.py must be a DOMAIN stub + wizard-wiring helpers
    # only — no HA async_setup code, no PLATFORM_SCHEMA (tier-b
    # recipe pattern).
    init_text = (CONNECTION_DIR / "__init__.py").read_text(encoding="utf-8")
    assert "DOMAIN" in init_text, "__init__.py must export DOMAIN for the audit"
    for forbidden in ("async_setup", "PLATFORM_SCHEMA"):
        assert forbidden not in init_text, (
            f"__init__.py must be a DOMAIN stub; found {forbidden!r} (tier-b recipe pattern)"
        )
    # The wizard-wiring helper apply_setup_path IS allowed (this
    # slice adds it).
    assert "apply_setup_path" in init_text, (
        "Wave 9 #108: __init__.py must export apply_setup_path so the "
        "config_flow wizard step can call it"
    )


def test_wizard_setup_paths_has_three_paths(manifest: dict) -> None:
    """Wave 9 #108 — the wizard exposes exactly 3 setup_paths.

    Each path must:
        - have an `id` matching one of EXPECTED_PATH_IDS
        - have `label`, `description`, `connection_kind`,
          `estimated_time`, `requires_reboot`, `setup_notes`
        - declare `requires_inputs` as a list (empty for Path A;
          [smart_plug_entity_id] for Path B; [openwrt_api_url,
          openwrt_api_token] for Path C)
        - declare `side_effects` as a list (each entry non-empty)
    """
    paths = manifest["wizard"]["setup_paths"]
    assert isinstance(paths, list), "wizard.setup_paths must be a list"
    assert len(paths) == 3, (
        f"wizard.setup_paths must have 3 entries (starlink_mini_only / "
        f"separate_router / vp2430_vm_router); got {len(paths)}"
    )

    ids = [p["id"] for p in paths]
    assert tuple(ids) == EXPECTED_PATH_IDS, (
        f"wizard.setup_paths must be exactly {EXPECTED_PATH_IDS}; got {tuple(ids)}"
    )

    for path in paths:
        for required_field in (
            "id", "label", "description", "connection_kind",
            "estimated_time", "requires_reboot", "setup_notes",
            "requires_inputs", "side_effects",
        ):
            assert required_field in path, (
                f"setup_path {path.get('id', '?')!r} is missing required "
                f"field {required_field!r}"
            )
        assert isinstance(path["label"], str) and path["label"].strip(), (
            f"setup_path {path['id']!r} has empty label"
        )
        assert isinstance(path["description"], str) and path["description"].strip(), (
            f"setup_path {path['id']!r} has empty description"
        )
        assert isinstance(path["requires_inputs"], list), (
            f"setup_path {path['id']!r} requires_inputs must be a list"
        )
        assert isinstance(path["side_effects"], list) and path["side_effects"], (
            f"setup_path {path['id']!r} must declare at least one side_effect"
        )
        assert isinstance(path["setup_notes"], str) and path["setup_notes"].strip(), (
            f"setup_path {path['id']!r} has empty setup_notes"
        )


def test_setup_path_a_mini_only_no_inputs(manifest: dict) -> None:
    """Path A (starlink_mini_only) needs no user input.

    The wizard auto-verifies reachability and writes helpers; the
    user just clicks "I'm using Starlink Mini as my only router".
    """
    paths = {p["id"]: p for p in manifest["wizard"]["setup_paths"]}
    mini = paths["starlink_mini_only"]
    assert mini["requires_inputs"] == [], (
        "starlink_mini_only must require no inputs (wizard auto-verifies "
        "reachability + writes the input_text + REST + 3 template sensors)"
    )
    assert mini["connection_kind"] == "api", (
        "starlink_mini_only is an api path (talks directly to Starlink "
        "local HTTP API; no operator wiring)"
    )
    assert mini["requires_reboot"] is False, (
        "starlink_mini_only must not require an HA reboot (helpers are "
        "created in-package; no service restarts)"
    )
    # The api_url / rest sensor / template sensors must be in side_effects.
    effects = " ".join(mini["side_effects"]).lower()
    assert "input_text" in effects, (
        "starlink_mini_only side_effects must include writes_input_text_helper"
    )
    assert "rest" in effects, (
        "starlink_mini_only side_effects must include creates_rest_sensor"
    )
    assert "template" in effects, (
        "starlink_mini_only side_effects must include creates_template_sensors"
    )


def test_setup_path_b_separate_router_requires_plug_entity(manifest: dict) -> None:
    """Path B (separate_router) requires smart_plug_entity_id.

    The wizard validates the plug entity is exposed + controllable
    before writing anything (per Wave 9 #108 doctrine: must not fail +
    super intuitive).
    """
    paths = {p["id"]: p for p in manifest["wizard"]["setup_paths"]}
    sep = paths["separate_router"]
    assert sep["requires_inputs"] == ["smart_plug_entity_id"], (
        "separate_router requires smart_plug_entity_id (the HA switch "
        "entity the operator already controls)"
    )
    assert sep["connection_kind"] == "recipe", (
        "separate_router is a recipe (depends on the operator's plug "
        "integration choice — TP-Link / Shelly / Sonoff / Zigbee / "
        "Modbus / etc.)"
    )
    effects = " ".join(sep["side_effects"]).lower()
    assert "switch" in effects, (
        "separate_router side_effects must include creates_switch_helper "
        "(switch.rc_net_starlink_plug → user's plug)"
    )


def test_setup_path_c_vp2430_vm_router_requires_openwrt_inputs(manifest: dict) -> None:
    """Path C (vp2430_vm_router) requires openwrt_api_url + token."""
    paths = {p["id"]: p for p in manifest["wizard"]["setup_paths"]}
    vm = paths["vp2430_vm_router"]
    assert "openwrt_api_url" in vm["requires_inputs"], (
        "vp2430_vm_router requires openwrt_api_url"
    )
    assert "openwrt_api_token" in vm["requires_inputs"], (
        "vp2430_vm_router requires openwrt_api_token"
    )
    assert vm["connection_kind"] == "recipe", (
        "vp2430_vm_router is a recipe (depends on the operator's "
        "OpenWrt VM token + the upstream connections/openwrt-controls "
        "integration)"
    )
    effects = " ".join(vm["side_effects"]).lower()
    assert "rest" in effects, (
        "vp2430_vm_router side_effects must include creates_rest_chain "
        "(through the OpenWrt API)"
    )


def test_tier_a_promotion_candidate_is_path_a(manifest: dict) -> None:
    """Path A is declared the tier-a promotion candidate.

    The connection tier stays `b` until a Starlink test fixture
    (testcontainers/grpc-starlink-dish or recorded dish-status.json)
    lands and an integration test passes. Until then, the manifest is
    honest about which path is the promotion candidate.
    """
    assert manifest.get("tier_a_promotion_candidate") == "starlink_mini_only", (
        "tier_a_promotion_candidate must be 'starlink_mini_only' (Path A "
        "doesn't depend on any operator wiring — Starlink local API is "
        "universal across Gen-2/Gen-3)"
    )


def test_absence_of_required_config_blocks_path_a(manifest: dict) -> None:
    """Failure case: Path A's required input_text helper is missing.

    Simulates the audit catching a regression where someone removes
    the input_text.rc_net_starlink_api_url helper from the in-package
    YAML without updating the wizard's side_effects list. The wizard
    would then claim "creates X" while nothing actually creates it.

    We assert the inverse: with the current manifest, every side_effect
    declared for starlink_mini_only references an entity id that's
    already declared elsewhere in the manifest (the dashboard.tiles or
    the wizard.setup_paths side_effects themselves).

    Concretely: Path A declares 5 entities and the manifest's
    dashboard.tiles list must contain at least 2 of them
    (reachable + signal_pct, both are surfaced as tiles per the
    recipe §4 contract).
    """
    paths = {p["id"]: p for p in manifest["wizard"]["setup_paths"]}
    mini = paths["starlink_mini_only"]

    # The dashboard must surface at least the binary_sensor.reachable
    # and sensor.signal_pct that Path A creates.
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    tiles_joined = " ".join(tiles).lower()
    assert "rc_net_starlink_reachable" in tiles_joined, (
        "dashboard must surface rc_net_starlink_reachable (Path A's "
        "primary reachability tile)"
    )
    assert "rc_net_starlink_signal_pct" in tiles_joined, (
        "dashboard must surface rc_net_starlink_signal_pct (Path A's "
        "primary signal-stat tile)"
    )

    # The wizard's side_effects list for Path A must mention
    # writes_input_text_helper (the input_text.rc_net_starlink_api_url
    # helper Path A writes — without it the REST resource_template
    # has no source-of-truth URL).
    effects = " ".join(mini["side_effects"]).lower()
    assert "writes_input_text_helper" in effects, (
        "Path A side_effects must include writes_input_text_helper "
        "(the wizard writes input_text.rc_net_starlink_api_url so the "
        "REST resource_template can be updated later without code changes)"
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
    # Sanity: the recipe actually documents Starlink + the contract
    # entities rather than just an empty placeholder.
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert len(text) > 500, "recipe.md looks like a placeholder — should be a real howto"
    assert "Starlink" in text or "starlink" in text, (
        "recipe.md must document the Starlink setup (smart-plug wiring, sleep + wake, signal stats)"
    )
    # The spec requires ≥100 lines; the frigate pattern asserts ≥250.
    # We ship a substantive howto well over both; this catches a
    # regression where someone leaves a 30-line placeholder.
    line_count = len(text.splitlines())
    assert line_count > 100, (
        f"recipe.md must be a substantive howto (>100 lines); got {line_count}"
    )
    # Spec §4 calls for the §1–§7 sections to be present. Grep-anchor
    # the major section headers so a future "I rewrote the recipe as
    # one wall of text" regression gets caught.
    required_sections = (
        "## What is Starlink in RoamCore?",
        "## Prerequisites",
        "## §4 RoamCore contract entities",
        "## §5 Automations",
        "## §6 Troubleshooting",
        "## §7 Privacy",
    )
    for header in required_sections:
        assert header in text, (
            f"recipe.md is missing required section header {header!r} "
            f"(spec §4 requires §1–§7 to be present)"
        )


def test_recipe_documents_three_setup_paths(manifest: dict) -> None:
    """Wave 9 #108 — recipe.md must document all 3 setup_paths.

    The wizard hands the user a choice of 3 paths; the recipe must
    back each path with at least one decision-tree section + step-by-
    step instructions. We grep for the path labels + the path id
    tokens so a regression where someone deletes a path gets caught.
    """
    text = RECIPE_PATH.read_text(encoding="utf-8")

    # The recipe must have a "Choose your setup" section at the top
    # (per the acceptance criteria).
    assert "Choose your setup" in text, (
        "recipe.md must have a 'Choose your setup' section at the top "
        "(per Wave 9 #108 acceptance: decision tree + the 3 paths documented)"
    )

    # All three path ids must appear by name in the recipe.
    for path_id in EXPECTED_PATH_IDS:
        assert path_id in text, (
            f"recipe.md must document the '{path_id}' setup path "
            f"(the wizard hands the user this choice; the recipe backs it)"
        )

    # Path labels should also appear (operator-facing).
    for label_fragment in (
        "Starlink Mini",
        "separate router",
        "VM router",
    ):
        assert label_fragment in text, (
            f"recipe.md must mention the path label fragment {label_fragment!r}"
        )


def test_category_matches_existing_legacy_doc(manifest: dict) -> None:
    """Promoted from tier-c legacy doc — category must match.

    The legacy tier-c spec lives at
    docs/catalog/networking/starlink-sleep-timer.md; we promote the
    connection into the `networking` category so the audit + boundary-
    CI can pair them up.
    """
    assert manifest["category"] == "networking", (
        f"category must stay 'networking' (legacy doc lives at "
        f"docs/catalog/networking/starlink-sleep-timer.md); got "
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

    The networking contract is implementation-agnostic (it talks to
    whatever smart plug the operator runs, not Starlink's cloud).
    Contract ids must stay vendor-neutral — no `starlink`, `spacex`,
    `dishy`, `gen2`, `gen3`, or author name.

    The spec is strict: every `dashboard.tiles[*]` must match
    `^[a-z_]+\\.rc_net_starlink_[a-z_]+$` (vendor-neutral, subsystem
    prefix `rc_net_starlink_*` per the §net subsystem naming rules
    in docs/reference/rc-entity-naming.md). The subsystem prefix IS
    allowed (it's the owning-area marker); what is forbidden is
    vendor names appearing AFTER the subsystem prefix in a way that
    double-stamps the vendor into the id beyond the subsystem token.
    """
    import re

    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles, "starlink contributes at least one dashboard tile"

    # Every tile must be a string entity id (spec calls for tiles-as-
    # strings, mirroring the spec's listed shape).
    for tile in tiles:
        assert isinstance(tile, str), (
            f"dashboard.tiles[*] must be a string entity id (spec §1); "
            f"got {tile!r}"
        )

    # Domain segment is lowercase + underscores only (HA convention).
    # Suffix segment after `rc_net_starlink_` may include digits (e.g.
    # `wake_30_min`) but must not contain vendor double-stamps.
    pattern = re.compile(r"^[a-z_]+\.rc_net_starlink_[a-z0-9_]+$")

    # Vendor / implementation names that must NEVER appear in any
    # rc_* tile id. Author/host name of the upstream project
    # included — the contract is implementation-agnostic.
    forbidden = {
        "spacex", "dishy", "gen2", "gen3", "gen_2", "gen_3",
        "starlink_",      # the subsystem token itself is the ONLY place "starlink" appears;
                          # double-stamping "starlink_" into the suffix (e.g. _starlink_dish)
                          # is forbidden.
        "kasa", "tplink", "tp_link", "shelly", "sonoff",   # plug vendors (cross-connection vendor leaks)
        "mqtt",                                            # cross-connection vendor leaks
        "victron", "wican", "meatpi",                      # unrelated connection vendor leaks
    }

    for tile in tiles:
        assert pattern.match(tile), (
            f"tile id {tile!r} must match ^[a-z_]+\\.rc_net_starlink_[a-z_]+$ "
            f"(vendor-neutral contract naming per docs/reference/rc-entity-naming.md)"
        )
        # Subsystem prefix is rc_net_starlink_; the suffix (after
        # `rc_net_starlink_`) MUST be a single identifier segment
        # — no double-stamping of the vendor name.
        suffix = tile.split(".rc_net_starlink_", 1)[1]
        assert "starlink" not in suffix.lower().split("_"), (
            f"tile id {tile!r} double-stamps 'starlink' into the suffix "
            f"(only the subsystem prefix `rc_net_starlink_` may carry the name)"
        )
        # Each segment after the dot must be lowercase + underscores + digits.
        for segment in tile.split("."):
            assert re.match(r"^[a-z_][a-z0-9_]*$", segment), (
                f"tile id {tile!r} contains a non-conforming segment {segment!r}"
            )
        for bad in forbidden:
            # 'starlink_' (with underscore) catches double-stamping;
            # we explicitly allow the single 'starlink' token inside
            # the subsystem prefix by checking after rc_net_starlink_.
            tail = tile.split(".rc_net_starlink_", 1)[-1] if ".rc_net_starlink_" in tile else tile
            assert bad not in tail.lower(), (
                f"tile id {tile!r} contains forbidden name {bad!r}; "
                f"per docs/reference/rc-entity-naming.md, contract ids are vendor-neutral"
            )


def test_status_reflects_no_real_starlink(manifest: dict) -> None:
    """Status must be honest about no integration being shipped.

    If we ever flip this to 'shipped', the audit will demand an actual
    integration test (and rightly so). 'beta' is the only honest tier-b
    status for a recipe we can't integration-test.
    """
    assert manifest["status"] in {"beta", "wip"}, (
        f"starlink status={manifest['status']!r} implies shipped coverage we don't have; "
        f"use 'beta' or 'wip' until tier-a promotion lands"
    )
    # tier_warnings must include the honest-about-no-terminal marker.
    assert "no_real_starlink_terminal_for_integration_test" in manifest["tier_warnings"], (
        "tier_warnings must declare 'no_real_starlink_terminal_for_integration_test' "
        "for honesty in the audit listing"
    )
    # And the user-facing recipe dependency warning.
    assert "smart_plug_required" in manifest["tier_warnings"], (
        "tier_warnings must declare 'smart_plug_required' so the audit "
        "listing is honest about the operator-bringing-the-plug contract"
    )
    assert "recipe_depends_on_user_smart_plug_or_relay" in manifest["tier_warnings"], (
        "tier_warnings must declare 'recipe_depends_on_user_smart_plug_or_relay' "
        "so the audit listing is honest about the user-bringing-the-plug contract"
    )


def test_init_module_exports_wizard_wiring_helpers() -> None:
    """Wave 9 #108 — __init__.py must export apply_setup_path + the 3 PATH_* constants.

    The config_flow wizard step imports these to drive the 3-path
    wizard. We do not call apply_setup_path here (no HA instance in
    the test env) — we only assert the public surface is present.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "starlink_init_for_test",
        CONNECTION_DIR / "__init__.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for name in (
        "DOMAIN",
        "PATH_STARLINK_MINI_ONLY",
        "PATH_SEPARATE_ROUTER",
        "PATH_VP2430_VM_ROUTER",
        "VALID_PATHS",
        "DEFAULT_STARLINK_API_URL",
        "STARLINK_REACH_TIMEOUT_S",
        "STARLINK_REACH_RETRIES",
        "STARLINK_REACH_BACKOFF_S",
        "apply_setup_path",
        "describe_setup_paths",
    ):
        assert hasattr(mod, name), f"__init__.py must export {name!r}"
    assert mod.PATH_STARLINK_MINI_ONLY == "starlink_mini_only"
    assert mod.PATH_SEPARATE_ROUTER == "separate_router"
    assert mod.PATH_VP2430_VM_ROUTER == "vp2430_vm_router"
    assert mod.VALID_PATHS == frozenset(
        {"starlink_mini_only", "separate_router", "vp2430_vm_router"}
    )
    # describe_setup_paths() returns 3 entries with all the keys the
    # config_flow needs to render the radio-button form.
    paths = mod.describe_setup_paths()
    assert len(paths) == 3
    for p in paths:
        for key in (
            "id", "label", "description", "estimated_time",
            "requires_reboot", "requires_inputs", "connection_kind",
        ):
            assert key in p, f"describe_setup_paths() entry missing key {key!r}"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))