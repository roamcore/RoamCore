"""Manifest-honesty tests for connections/music-assistant/connection.yml.

This is the only test file we can ship for a tier-b recipe connection
that has no real Music Assistant server to integration-test against.
The tests here assert that the manifest is *honest about being tier-b* —
that the folder/id/tier invariants hold, that the recipe doc the
tier_requirements promise is actually present on disk, and that the
rc_media_* tile ids are vendor-neutral per
docs/reference/rc-entity-naming.md.

If you add real integration coverage (e.g. a config_flow.py + an
integration test against a RoamCore-owned MA container with a
default provider stub), keep this file and add the new one alongside
it; the audit will then list both under `tests:` in the manifest.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/music-assistant/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> music-assistant/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "music-assistant"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
LEGACY_DOC = REPO_ROOT / "docs" / "catalog" / "audio-media" / "music-assistant.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (music-assistant).

    This is the same invariant the audit script enforces; we duplicate
    it here so pytest catches regressions before CI runs the audit.
    """
    assert manifest["id"] == CONNECTION_DIR.name, (
        f"manifest id={manifest['id']!r} does not match folder name "
        f"{CONNECTION_DIR.name!r}"
    )
    assert manifest["id"] == "music-assistant"


def test_tier_b_without_tier_a_markers(manifest: dict) -> None:
    """Tier-b must NOT advertise tier-a-only RoamCore-owned fields.

    A regression here (e.g. someone flipping one_tap to true, or
    adding a RoamCore-owned config_flow.py) would falsely imply a
    working RoamCore integration + integration tests that we don't
    have, and the audit would either block the PR or let a
    misleading tier-a claim slip through.

    The distinction this test guards: install.config_flow + install.hacs
    are TRUE here because the UPSTREAM HACS `music_assistant` integration
    is honest upstream truth (config_flow since 2023; HACS-only because
    HA core does NOT include Music Assistant) — those are NOT tier-a
    markers for RoamCore's tier. The tier-a marker for RoamCore would
    be a RoamCore-owned `config_flow.py` + RoamCore-owned integration
    code + integration tests against a RoamCore-owned MA container.
    None of those are shipped at tier-b.
    """
    assert manifest["tier"] == "b", "music-assistant must stay at tier-b until integration coverage lands"
    assert manifest["wizard"]["one_tap"] is False, (
        "tier-b connections cannot advertise one_tap=true (that's a tier-a contract)"
    )
    # Music Assistant recipes an operator-side HACS `music_assistant`
    # integration; RoamCore ships no native config_flow for that.
    # install.config_flow is the RoamCore-owned field. We document the
    # distinction in the manifest header: the UPSTREAM HACS integration
    # has a config_flow since 2023 (honest upstream truth, NOT a
    # tier-a marker for RoamCore). The tier-a marker for RoamCore is a
    # RoamCore-owned config_flow.py + integration tests. Until those
    # ship, this connection is tier-b even though the upstream
    # integration has a config_flow.
    assert manifest["install"]["config_flow"] is True, (
        "install.config_flow must stay True — the upstream HACS `music_assistant` "
        "integration exposes a config_flow since 2023 (honest upstream truth, NOT "
        "a tier-a marker)"
    )
    assert manifest["install"]["hacs"] is True, (
        "music-assistant is HACS-only — HA core does NOT include Music Assistant; "
        "install.hacs must stay True (honest upstream truth, NOT a tier-a marker)"
    )
    # Belt-and-braces: there must be no RoamCore-owned config_flow.py
    # in this folder (no native integration code for a tier-b recipe
    # connection). The upstream HACS `music_assistant` integration has
    # its own config_flow, but that lives in the upstream HACS repo,
    # not in this folder.
    assert not (CONNECTION_DIR / "config_flow.py").is_file(), (
        "tier-b recipe connection must not ship a RoamCore-owned config_flow.py"
    )
    # The __init__.py must be a DOMAIN-stub only — no integration
    # setup logic. We assert it exports DOMAIN and nothing else that
    # smells like HA integration code.
    init_text = (CONNECTION_DIR / "__init__.py").read_text(encoding="utf-8")
    assert "DOMAIN" in init_text, "__init__.py must export DOMAIN for the audit"
    # DOMAIN must equal "music-assistant" (matches the folder name).
    assert 'DOMAIN = "music-assistant"' in init_text, (
        '__init__.py must define DOMAIN = "music-assistant" (matches the folder name)'
    )
    for forbidden in ("async_setup", "config_flow", "PLATFORM_SCHEMA"):
        assert forbidden not in init_text, (
            f"__init__.py must be a DOMAIN stub; found {forbidden!r} (tier-b recipe pattern)"
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
    # Sanity: the recipe actually documents Music Assistant + the
    # contract entities rather than just an empty placeholder.
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert "Music Assistant" in text or "music_assistant" in text, (
        "recipe.md must document the Music Assistant setup (HACS wiring, "
        "Path A HA add-on, Path B external MA server, provider setup, "
        "automations, troubleshooting)"
    )
    # The spec requires ≥250 lines; we ship a substantive howto well
    # over that; this catches a regression where someone leaves a
    # 30-line placeholder.
    line_count = len(text.splitlines())
    assert line_count >= 250, (
        f"recipe.md must be a substantive howto (≥250 lines per spec); got {line_count}"
    )
    # Spec §4 calls for the §1–§7 sections to be present. Grep-anchor
    # the major section headers so a future "I rewrote the recipe as
    # one wall of text" regression gets caught.
    required_sections = (
        "## What is Music Assistant in RoamCore?",
        "## Prerequisites",
        "## Path A",
        "## Path B",
        "## §5 RoamCore contract entities",
        "## §6 Automations",
        "## §7",
    )
    for header in required_sections:
        assert header in text, (
            f"recipe.md is missing required section header {header!r} "
            f"(spec requires §1–§7 to be present)"
        )


def test_category_matches_existing_legacy_doc(manifest: dict) -> None:
    """Promoted from tier-c legacy doc — category must match.

    The legacy tier-c spec lives at
    docs/catalog/audio-media/music-assistant.md; we promote the
    connection into the `media` category so the audit + boundary-CI
    can pair them up.
    """
    assert manifest["category"] == "media", (
        f"category must stay 'media' (legacy doc lives at "
        f"docs/catalog/audio-media/music-assistant.md); got "
        f"{manifest['category']!r}"
    )
    assert LEGACY_DOC.is_file(), (
        "expected the legacy tier-c doc to still exist so we can reference it "
        "from the recipe (and add a supersession banner)"
    )


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """rc_* tile ids must NOT contain vendor names (per rc-entity-naming.md).

    The media contract is implementation-agnostic (it talks to
    whatever MA server the operator runs, not any provider's
    library). Contract ids must stay vendor-neutral — no
    `music_assistant`, `mass`, `ma_`, `spotify`, `airplay`,
    `chromecast`, `sonos`, `squeezebox`, `dlna`, `upnp`, or any
    provider name.

    The spec is strict: every `dashboard.tiles[*]` must start with
    `rc_media_` (the new §media subsystem per
    docs/reference/rc-entity-naming.md).
    """
    import re

    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles, "music-assistant contributes at least one dashboard tile"

    # Every tile must be a string entity id (spec calls for tiles-as-
    # strings, mirroring the spec's listed shape).
    for tile in tiles:
        assert isinstance(tile, str), (
            f"dashboard.tiles[*] must be a string entity id (spec §1); "
            f"got {tile!r}"
        )

    # All tiles must use the `rc_media_` prefix (the new §media
    # subsystem). The spec lists exactly 14 tiles; mirror that.
    pattern = re.compile(r"^[a-z_]+\.rc_media_[a-z0-9_]+$")

    # Vendor / implementation names that must NEVER appear in any
    # rc_* tile id. MA server names + every provider name + every
    # player topology.
    forbidden_substrings = (
        "music_assistant",     # MA upstream integration name (vendor leak)
        "mass",                # MA upstream short name (vendor leak)
        "spotify",             # provider name
        "airplay",             # provider / player topology
        "chromecast",          # provider / player topology
        "sonos",               # provider / player topology
        "squeezebox",          # provider / player topology
        "dlna",                # provider / player topology
        "upnp",                # provider / player topology
    )

    for tile in tiles:
        assert pattern.match(tile), (
            f"tile id {tile!r} must match ^[a-z_]+\\.rc_media_[a-z_]+$ "
            f"(vendor-neutral contract naming per docs/reference/rc-entity-naming.md)"
        )
        for bad in forbidden_substrings:
            assert bad not in tile.lower(), (
                f"tile id {tile!r} contains forbidden substring {bad!r}; "
                f"per docs/reference/rc-entity-naming.md, contract ids are vendor-neutral"
            )

    # Spec calls for exactly 14 tiles (3 media_player zones + 1
    # binary_sensor + 6 sensors + 2 buttons + 1 select).
    assert len(tiles) == 14, (
        f"music-assistant must contribute exactly 14 contract tiles per spec "
        f"(3 media_player zones + 1 binary_sensor + 6 sensors + 2 buttons + 1 select); "
        f"got {len(tiles)}"
    )


def test_status_reflects_no_real_music_assistant(manifest: dict) -> None:
    """Status must be honest about no integration being shipped.

    If we ever flip this to 'shipped', the audit will demand an actual
    integration test (and rightly so). 'beta' is the only honest tier-b
    status for a recipe we can't integration-test.
    """
    assert manifest["status"] == "beta", (
        f"music-assistant status={manifest['status']!r} implies shipped coverage we don't have; "
        f"use 'beta' until tier-a promotion lands"
    )
    tier_warnings = manifest.get("tier_warnings", [])
    # tier_warnings must include the honest-about-no-MA-server marker.
    assert "no_real_music_assistant_for_integration_test" in tier_warnings, (
        "tier_warnings must declare 'no_real_music_assistant_for_integration_test' "
        "for honesty in the audit listing"
    )
    # And the user-facing recipe dependency warning.
    assert "recipe_depends_on_user_running_ma" in tier_warnings, (
        "tier_warnings must declare 'recipe_depends_on_user_running_ma' "
        "so the audit listing is honest about the user-bringing-the-server contract"
    )
    # Optional provider choice — Spotify / Apple Music / local files
    # / TuneIn / Chromecast / AirPlay / Sonos / DLNA / UPnP.
    assert "optional_provider_choice_spotify_apple_music_local_files" in tier_warnings, (
        "tier_warnings must declare 'optional_provider_choice_spotify_apple_music_local_files' "
        "so the audit listing is honest about the provider-mix choice"
    )
    # HACS required for the integration.
    assert "hacs_required_for_integration" in tier_warnings, (
        "tier_warnings must declare 'hacs_required_for_integration' "
        "so the audit listing is honest about MA being HACS-only"
    )


def test_agent_pause_all_action_is_allowlisted(manifest: dict) -> None:
    """The recipe names the pause-all button as a known OpenClaw agent action.

    The OpenClaw wiring passes the manifest honesty check only if the
    pause-all affordance is exposed via a `button` (not a free-form
    command). This test asserts the recipe names the pause-all button
    as `button.rc_media_pause_all` and that the openclaw queries list
    `pause_all_music` so the agent can drive it.
    """
    openclaw_queries = manifest.get("openclaw", {}).get("queries", [])
    assert "pause_all_music" in openclaw_queries, (
        "openclaw.queries must declare 'pause_all_music' so the agent can "
        "drive the pause-all affordance"
    )
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert "button.rc_media_pause_all" in tiles, (
        "dashboard.tiles must include 'button.rc_media_pause_all' so "
        "the OpenClaw wiring has a known-good button to call"
    )
    # And the recipe doc must reference the pause-all button + the
    # OpenClaw wiring so an operator reading the recipe can find the
    # wiring.
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert "button.rc_media_pause_all" in text, (
        "recipe.md must reference 'button.rc_media_pause_all' so "
        "operators can wire the OpenClaw agent-action allowlist correctly"
    )
    # Spec says §6 references "pause all" phrase (regex).
    import re

    # Find §6 Automations block and check it references "pause all".
    section_6_match = re.search(r"## §6 Automations(.*?)(?=## §7)", text, re.DOTALL)
    assert section_6_match is not None, (
        "recipe.md must have a §6 Automations section"
    )
    section_6_text = section_6_match.group(1)
    assert "pause all" in section_6_text.lower(), (
        "recipe.md §6 must reference the 'pause all' phrase so operators can find "
        "the pause-all automation"
    )
    # Also verify resume_last_playlist is referenced (paired affordance).
    assert "resume_last_playlist" in openclaw_queries, (
        "openclaw.queries must declare 'resume_last_playlist' so the agent can "
        "drive the resume-last affordance"
    )
    assert "button.rc_media_resume_last" in tiles, (
        "dashboard.tiles must include 'button.rc_media_resume_last' so "
        "the OpenClaw wiring has a known-good button to call"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
