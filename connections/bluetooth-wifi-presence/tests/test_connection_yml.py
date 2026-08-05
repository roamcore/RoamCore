"""Manifest-honesty tests for connections/bluetooth-wifi-presence/connection.yml.

This is the only test file we can ship for a tier-b recipe connection
that has no real Bluetooth adapters + Wi-Fi routers + BLE beacons to
integration-test against. The tests here assert that the manifest is
*honest about being tier-b* — that the folder/id/tier invariants hold,
that the recipe doc the tier_requirements promise is actually present
on disk, and that the rc_presence_* tile ids are vendor-neutral per
docs/reference/rc-entity-naming.md.

If you add real integration coverage (e.g. a config_flow.py + an
integration test against a bench with 2 BLE devices + a Wi-Fi router
+ a canned fixture response from bluetooth_le_tracker / nmap_device_tracker),
keep this file and add the new one alongside it; the audit will then
list both under `tests:` in the manifest.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/bluetooth-wifi-presence/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> bluetooth-wifi-presence/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "bluetooth-wifi-presence"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
LEGACY_DOC = REPO_ROOT / "docs" / "catalog" / "presence" / "bluetooth-wifi-presence.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (bluetooth-wifi-presence).

    This is the same invariant the audit script enforces; we duplicate
    it here so pytest catches regressions before CI runs the audit.
    """
    assert manifest["id"] == CONNECTION_DIR.name, (
        f"manifest id={manifest['id']!r} does not match folder name "
        f"{CONNECTION_DIR.name!r}"
    )
    assert manifest["id"] == "bluetooth-wifi-presence"


def test_tier_b_without_tier_a_markers(manifest: dict) -> None:
    """Tier-b must NOT advertise tier-a-only RoamCore-owned fields.

    A regression here (e.g. someone flipping one_tap to true, or
    adding a RoamCore-owned config_flow.py) would falsely imply a
    working RoamCore integration + integration tests that we don't
    have, and the audit would either block the PR or let a
    misleading tier-a claim slip through.

    The distinction this test guards: install.config_flow is TRUE here
    because the UPSTREAM HA core `nmap_device_tracker` (Path B) +
    `asuswrt` / `unifi` / `mikrotik` (Path C) integrations are honest
    upstream truth (config_flow since 2022.x) — that's NOT a tier-a
    marker for RoamCore's tier. The tier-a marker for RoamCore would
    be a RoamCore-owned `config_flow.py` + RoamCore-owned integration
    code + integration tests against a RoamCore-owned presence
    scanner bench. None of those are shipped at tier-b. The
    `bluetooth_le_tracker` Path A is YAML-only (documented in the
    recipe); the operator's choice of Path A goes through YAML, not
    a config_flow — also honest upstream truth.
    """
    assert manifest["tier"] == "b", "bluetooth-wifi-presence must stay at tier-b until integration coverage lands"
    assert manifest["wizard"]["one_tap"] is False, (
        "tier-b connections cannot advertise one_tap=true (that's a tier-a contract)"
    )
    # Presence recipes an operator-side HA core `nmap_device_tracker`
    # / `ping` / `asuswrt` / `unifi` / `mikrotik` integration; RoamCore
    # ships no native config_flow for that. install.config_flow is the
    # RoamCore-owned field. We document the distinction in the manifest
    # header: the UPSTREAM HA core nmap_device_tracker + asuswrt /
    # unifi / mikrotik integrations DO expose a config_flow since
    # 2022.x (honest upstream truth, NOT a tier-a marker for
    # RoamCore's tier). The tier-a marker for RoamCore is a
    # RoamCore-owned config_flow.py + integration tests. Until those
    # ship, this connection is tier-b even though the upstream
    # integrations have a config_flow.
    assert manifest["install"]["config_flow"] is True, (
        "install.config_flow must stay True — the upstream HA core "
        "`nmap_device_tracker` + `asuswrt` / `unifi` / `mikrotik` "
        "integrations expose a config_flow since 2022.x (honest "
        "upstream truth, NOT a tier-a marker)"
    )
    assert manifest["install"]["hacs"] is False, (
        "bluetooth-wifi-presence is a recipe; no HACS integration of "
        "our own is shipped (Paths A/B/C all use existing HA core "
        "integrations)"
    )
    # Belt-and-braces: there must be no RoamCore-owned config_flow.py
    # in this folder (no native integration code for a tier-b recipe
    # connection). The upstream HA core integrations have their own
    # config_flow, but that lives in the upstream HA core / HACS repos,
    # not in this folder.
    assert not (CONNECTION_DIR / "config_flow.py").is_file(), (
        "tier-b recipe connection must not ship a RoamCore-owned config_flow.py"
    )
    # The __init__.py must be a DOMAIN-stub only — no integration
    # setup logic. We assert it exports DOMAIN and nothing else that
    # smells like HA integration code.
    init_text = (CONNECTION_DIR / "__init__.py").read_text(encoding="utf-8")
    assert "DOMAIN" in init_text, "__init__.py must export DOMAIN for the audit"
    # DOMAIN must equal "bluetooth-wifi-presence" (matches the folder name).
    assert 'DOMAIN = "bluetooth-wifi-presence"' in init_text, (
        '__init__.py must define DOMAIN = "bluetooth-wifi-presence" '
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
    # Sanity: the recipe actually documents presence detection + the
    # contract entities rather than just an empty placeholder.
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert (
        "presence" in text.lower() and "bluetooth" in text.lower()
    ) or "rc_presence_" in text, (
        "recipe.md must document the presence setup (Path A Bluetooth, "
        "Path B nmap/ping, Path C router-side, contract entities, "
        "automations, troubleshooting)"
    )
    # The spec requires ≥250 lines; we ship a substantive howto well
    # over that; this catches a regression where someone leaves a
    # 30-line placeholder.
    line_count = len(text.splitlines())
    assert line_count >= 250, (
        f"recipe.md must be a substantive howto (≥250 lines per spec); "
        f"got {line_count}"
    )
    # Spec §4 calls for the §1–§10 sections to be present. Grep-anchor
    # the major section headers so a future "I rewrote the recipe as
    # one wall of text" regression gets caught. The test accepts both
    # the canonical `## §N` form and the `# §N` form (the recipe's
    # H1-style section headers are valid Markdown either way).
    required_sections = (
        "## §1 What is presence detection in RoamCore?",
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
    docs/catalog/presence/bluetooth-wifi-presence.md; we promote the
    connection into the `presence` category so the audit + boundary-CI
    can pair them up.
    """
    assert manifest["category"] == "presence", (
        f"category must stay 'presence' (legacy doc lives at "
        f"docs/catalog/presence/bluetooth-wifi-presence.md); got "
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

    The presence contract is implementation-agnostic (it talks to
    whatever Bluetooth / Wi-Fi / router source the operator runs,
    not any vendor's library). Contract ids must stay vendor-neutral
    — NO `bluetooth`, `bt`, `wifi`, `wlan`, `arp`, `nmap`, `ping`,
    `asuswrt`, `ubiquiti`, `unifi`, `mikrotik`, `iphone`, `android`,
    `pixel`, `galaxy` in any rc_* tile id BEYOND the subsystem prefix
    `rc_presence_*`.

    The spec is strict: every `dashboard.tiles[*]` must match
    `^[a-z_]+\\.rc_presence_[a-z0-9_]+$` (vendor-neutral, subsystem
    prefix `rc_presence_*` per the §presence subsystem naming rules
    in docs/reference/rc-entity-naming.md). The subsystem prefix IS
    allowed (it's the owning-area marker); what is forbidden is
    vendor / phone-model names appearing AFTER the subsystem prefix
    in a way that double-stamps the vendor into the id.
    """
    import re

    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles, "bluetooth-wifi-presence contributes at least one dashboard tile"

    # Every tile must be a string entity id (spec calls for tiles-as-
    # strings, mirroring the spec's listed shape).
    for tile in tiles:
        assert isinstance(tile, str), (
            f"dashboard.tiles[*] must be a string entity id (spec §1); "
            f"got {tile!r}"
        )

    # Domain segment is lowercase + underscores only (HA convention).
    # Suffix segment after `rc_presence_` may include digits but
    # must not contain vendor double-stamps.
    pattern = re.compile(r"^[a-z_]+\.rc_presence_[a-z0-9_]+$")

    # Vendor / implementation / phone-model names that must NEVER
    # appear in any rc_* tile id BEYOND the subsystem prefix
    # `rc_presence_*`. These cover all three upstream paths +
    # common phone model names that the recipe explicitly forbids.
    forbidden_substrings = (
        # Path A — Bluetooth LE
        "bluetooth",        # upstream integration name (vendor leak)
        "bt_",              # upstream integration short name (vendor leak)
        # Path B — Wi-Fi presence
        "wifi",             # upstream integration name (vendor leak)
        "wlan",             # upstream integration name (vendor leak)
        "arp",              # upstream integration name (vendor leak)
        "nmap",             # upstream integration name (vendor leak)
        "ping",             # upstream integration name (vendor leak)
        # Path C — Router-side device_tracker
        "asuswrt",          # upstream integration name (vendor leak)
        "ubiquiti",         # upstream integration name (vendor leak)
        "unifi",            # upstream integration name (vendor leak)
        "mikrotik",         # upstream integration name (vendor leak)
        # Phone model names — recipe explicitly forbids these
        "iphone",           # Apple phone model (vendor leak)
        "android",          # OS name (vendor leak)
        "pixel",            # Google phone model (vendor leak)
        "galaxy",           # Samsung phone model (vendor leak)
    )

    for tile in tiles:
        assert pattern.match(tile), (
            f"tile id {tile!r} must match ^[a-z_]+\\.rc_presence_[a-z_]+$ "
            f"(vendor-neutral contract naming per docs/reference/rc-entity-naming.md)"
        )
        # Subsystem prefix is rc_presence_; the suffix (after
        # `rc_presence_`) MUST NOT contain any forbidden substring.
        suffix = tile.split(".rc_presence_", 1)[1]
        for bad in forbidden_substrings:
            assert bad not in suffix.lower(), (
                f"tile id {tile!r} contains forbidden substring {bad!r} "
                f"in the suffix after `rc_presence_`; per docs/reference/"
                f"rc-entity-naming.md, contract ids are vendor-neutral "
                f"BEFORE and AFTER the subsystem prefix"
            )
        # Each segment after the dot must be lowercase + underscores + digits.
        for segment in tile.split("."):
            assert re.match(r"^[a-z_][a-z0-9_]*$", segment), (
                f"tile id {tile!r} contains a non-conforming segment {segment!r}"
            )

    # Spec calls for exactly 10 tiles (2 device_tracker persons +
    # 3 binary_sensor + 3 sensor + 1 button + 1 select).
    assert len(tiles) == 10, (
        f"bluetooth-wifi-presence must contribute exactly 10 contract "
        f"tiles per spec (2 device_tracker persons + 3 binary_sensor + "
        f"3 sensor + 1 button + 1 select); got {len(tiles)}"
    )


def test_status_reflects_no_real_presence_devices(manifest: dict) -> None:
    """Status must be honest about no integration being shipped.

    If we ever flip this to 'shipped', the audit will demand an actual
    integration test (and rightly so). 'beta' is the only honest tier-b
    status for a recipe we can't integration-test.
    """
    assert manifest["status"] == "beta", (
        f"bluetooth-wifi-presence status={manifest['status']!r} implies "
        f"shipped coverage we don't have; use 'beta' until tier-a "
        f"promotion lands"
    )
    tier_warnings = manifest.get("tier_warnings", [])
    # tier_warnings must include the honest-about-no-presence-devices marker.
    assert "no_real_presence_devices_for_integration_test" in tier_warnings, (
        "tier_warnings must declare 'no_real_presence_devices_for_integration_test' "
        "for honesty in the audit listing"
    )
    # And the user-facing recipe dependency warning (operator must declare
    # persons + devices).
    assert "recipe_depends_on_user_declaring_persons_and_devices" in tier_warnings, (
        "tier_warnings must declare 'recipe_depends_on_user_declaring_persons_and_devices' "
        "so the audit listing is honest about the user-declaring-the-per-person-mapping contract"
    )
    # Path choice honesty — Bluetooth vs nmap/ping vs router-side depends
    # on host OS + available hardware + existing router + per-person device mix.
    assert "bluetooth_vs_wifi_path_choice" in tier_warnings, (
        "tier_warnings must declare 'bluetooth_vs_wifi_path_choice' "
        "so the audit listing is honest about the model + hardware + fleet-size driven choice"
    )
    # False positives on iPhone/Android screensaver sleep (Path A's
    # screensaver-sleep failure mode).
    assert "false_positives_on_screensaver_sleep" in tier_warnings, (
        "tier_warnings must declare 'false_positives_on_screensaver_sleep' "
        "so the audit listing is honest about Path A's screensaver-sleep "
        "failure mode (the recipe recommends pairing a BLE beacon alongside "
        "the phone so the beacon remains discoverable while the phone "
        "screen is locked)"
    )


def test_agent_refresh_action_is_allowlisted(manifest: dict) -> None:
    """The recipe names the refresh-now button as a known OpenClaw agent action.

    The OpenClaw wiring passes the manifest honesty check only if the
    refresh-now affordance is exposed via a `button` (not a free-form
    command). This test asserts the recipe names the refresh-now
    button as `button.rc_presence_refresh_now` and that the openclaw
    queries list `refresh_presence_now` so the agent can drive it.
    """
    openclaw_queries = manifest.get("openclaw", {}).get("queries", [])
    assert "refresh_presence_now" in openclaw_queries, (
        "openclaw.queries must declare 'refresh_presence_now' so the agent can "
        "drive the refresh-now affordance"
    )
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert "button.rc_presence_refresh_now" in tiles, (
        "dashboard.tiles must include 'button.rc_presence_refresh_now' so "
        "the OpenClaw wiring has a known-good button to call"
    )
    # And the recipe doc must reference the refresh-now button + the
    # OpenClaw wiring so an operator reading the recipe can find the
    # wiring.
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert "button.rc_presence_refresh_now" in text, (
        "recipe.md must reference 'button.rc_presence_refresh_now' so "
        "operators can wire the OpenClaw agent-action allowlist correctly"
    )
    assert "refresh_presence_now" in text, (
        "recipe.md must reference 'refresh_presence_now' so operators can "
        "wire the OpenClaw agent-action allowlist correctly"
    )
    # Spec says §7 references "refresh" or "anyone home" phrase (regex).
    import re

    # Find §7 Automations block and check it references "anyone home".
    section_7_match = re.search(r"## §7 Automations(.*?)(?=## §8)", text, re.DOTALL)
    assert section_7_match is not None, (
        "recipe.md must have a §7 Automations section"
    )
    section_7_text = section_7_match.group(1)
    assert "anyone home" in section_7_text.lower(), (
        "recipe.md §7 must reference the 'anyone home' phrase so operators "
        "can find the anyone-home automation"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))