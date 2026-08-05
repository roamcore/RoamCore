"""Manifest-honesty tests for connections/nas/connection.yml.

This is the only test file we can ship for a tier-b recipe connection
that has no real NAS on the bench to integration-test against. The
tests here assert that the manifest is *honest about being tier-b* —
that the folder/id/tier invariants hold, that the recipe doc the
tier_requirements promise is actually present on disk, that the
rc_homelab_nas_* tile ids are vendor-neutral per
docs/reference/rc-entity-naming.md, and that the legacy tier-b spec
still exists so the supersession banner can point at it.

NUANCE — config_flow=true is allowed here, unlike Starlink:

  Starlink recipes an operator-side plug (TP-Link / Shelly / Sonoff /
  Zigbee / Modbus / ...). There is no canonical upstream HA
  integration that does the operator-side power-cycle path Starlink
  recipes, so `install.config_flow: true` would falsely imply a
  RoamCore-owned native config_flow we don't have. Hence the Starlink
  manifest asserts config_flow=false at tier-b.

  NAS recipes Synology DSM (Path A), QNAP (Path B), and generic
  SMB/NFS (Path C). Two of those upstreams have had working
  config_flows in HA core for years:
    - Synology DSM (ha_integration_domain: synology_dsm):
      config_flow since 2020.12.
    - QNAP (ha_integration_domain: qnap): config_flow since 2017 /
      modernized 2022.4.
    - Generic SMB/NFS (ha_integration_domain: smb via the
      `homeassistant` network-storage block + HA backup integration):
      NOT a config_flow integration in the modern sense; the
      operator-driven BACKUP target selection uses HA's backup
      integration which DOES have a config_flow.
  The `install.config_flow: true` here is UPSTREAM truth (the
  operator adds the Synology/QNAP integration via HA's own
  config_flow, or wires the SMB share via configuration.yaml +
  the backup integration's config_flow), NOT a RoamCore-owned
  config_flow. The `__init__.py` is a DOMAIN stub and there is no
  RoamCore-owned config_flow.py in this folder. If a future
  RoamCore release ships a native wrapper around the upstream
  config_flow (e.g. a wizard-side helper that auto-creates the
  rc_homelab_nas_* tiles post-config_flow), this test would be
  updated to also assert a config_flow.py is present.

If you add real integration coverage (e.g. a config_flow.py + an
integration test against testcontainers/synology-dsm or
testcontainers/qnap with a synthetic webapi fixture, or a
testcontainers/samba with a synthetic SMB-share fixture), keep
this file and add the new one alongside it; the audit will then
list both under `tests:` in the manifest.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/nas/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> nas/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "nas"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
LEGACY_NAS_DOC = REPO_ROOT / "docs" / "catalog" / "homelab" / "nas.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (nas).

    This is the same invariant the audit script enforces; we duplicate
    it here so pytest catches regressions before CI runs the audit.
    """
    assert manifest["id"] == CONNECTION_DIR.name, (
        f"manifest id={manifest['id']!r} does not match folder name "
        f"{CONNECTION_DIR.name!r}"
    )
    assert manifest["id"] == "nas"


def test_tier_b_without_tier_a_markers(manifest: dict) -> None:
    """Tier-b must NOT advertise tier-a-only fields — except for config_flow.

    NUANCE (see module docstring): unlike Starlink, the NAS manifest
    DOES set install.config_flow=true because two of the three
    upstream integrations (Synology DSM and QNAP) have had
    config_flow in HA core for years (2020.12 and 2017 / 2022.4
    respectively). The third (generic SMB) uses configuration.yaml +
    the HA backup integration which DOES have a config_flow. The
    config_flow=true field is UPSTREAM truth, NOT a RoamCore-owned
    config_flow. To catch a future regression where someone mistakes
    the upstream config_flow truth for a RoamCore-owned one, we
    assert:

      - there is no config_flow.py file in this folder (no
        RoamCore-owned integration code),
      - the __init__.py is a DOMAIN stub (no async_setup /
        config_flow / PLATFORM_SCHEMA),
      - install.hacs is false (no HACS integration of our own).

    A regression here (e.g. someone flipping one_tap to true OR
    adding a RoamCore-owned config_flow.py without bumping the tier
    to tier-a) would falsely imply one-tap automation + native
    integration code we don't have.
    """
    assert manifest["tier"] == "b", "nas must stay at tier-b until integration coverage lands"
    assert manifest["wizard"]["one_tap"] is False, (
        "tier-b connections cannot advertise one_tap=true (that's a tier-a contract)"
    )
    # install.config_flow: true is UPSTREAM truth for NAS
    # (Synology DSM + QNAP both have config_flow in HA core).
    # We assert it IS true (matches upstream reality), but we ALSO
    # assert there is no RoamCore-owned config_flow.py / no
    # async_setup code in __init__.py — so the truth is honest.
    assert manifest["install"]["config_flow"] is True, (
        "nas must advertise install.config_flow=true (UPSTREAM truth: "
        "both Synology DSM and QNAP have config_flow in HA core)"
    )
    assert manifest["install"]["hacs"] is False, (
        "nas is a recipe; no HACS integration of our own is shipped"
    )
    # Belt-and-braces: there must be no RoamCore-owned config_flow.py
    # in this folder. config_flow=true is UPSTREAM truth, not a
    # RoamCore-owned flow.
    assert not (CONNECTION_DIR / "config_flow.py").is_file(), (
        "tier-b recipe connection must not ship a RoamCore-owned config_flow.py "
        "(install.config_flow=true reflects UPSTREAM truth, not RoamCore-owned code)"
    )
    # The __init__.py must be a DOMAIN-stub only — no integration
    # setup logic. We assert it exports DOMAIN and nothing else that
    # smells like HA integration code.
    init_text = (CONNECTION_DIR / "__init__.py").read_text(encoding="utf-8")
    assert "DOMAIN" in init_text, "__init__.py must export DOMAIN for the audit"
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
    # Sanity: the recipe actually documents a NAS setup
    # (Synology / QNAP / SMB) rather than just an empty placeholder.
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert len(text) > 500, "recipe.md looks like a placeholder — should be a real howto"
    assert ("NAS" in text or "Synology" in text or "QNAP" in text or "SMB" in text), (
        "recipe.md must document the NAS setup "
        "(Path A Synology install + Path B QNAP install + Path C SMB + contract wiring)"
    )
    # The spec requires ≥200 lines; we ship a substantive howto well
    # over both; this catches a regression where someone leaves a
    # 30-line placeholder.
    line_count = len(text.splitlines())
    assert line_count > 200, (
        f"recipe.md must be a substantive howto (>200 lines); got {line_count}"
    )
    # Spec §4 calls for the §1–§7 sections to be present. Grep-anchor
    # the major section headers so a future "I rewrote the recipe as
    # one wall of text" regression gets caught.
    required_sections = (
        "## What is a NAS in RoamCore?",
        "## Prerequisites",
        "## Path A",
        "## Path B",
        "## Path C",
        "## RoamCore contract entities",
        "## Automations",
        "## Troubleshooting",
    )
    for header in required_sections:
        assert header in text, (
            f"recipe.md is missing required section header {header!r} "
            f"(spec §4 requires §1–§7 to be present)"
        )


def test_category_matches_existing_legacy_doc(manifest: dict) -> None:
    """Promoted from the legacy tier-b doc — category must match.

    The legacy tier-b spec lives at
    docs/catalog/homelab/nas.md. The legacy page's category is the
    homelab bucket (the operator-facing way to discover "self-hosted
    storage you might want in the van"). The contract entities this
    connection publishes are `rc_homelab_nas_*` ids — the `homelab`
    subsystem is being introduced by this slice (it isn't yet
    enumerated in docs/reference/rc-entity-naming.md's §subsystem
    list, but the canonicalization pass will codify `homelab` for
    self-hosted appliances in a follow-up). So the connection
    manifest's `category` must be `homelab` (matching the legacy
    doc's bucket + matching the subsystem prefix the contract
    tiles use).

    NUANCE: the dns-blocker test (the closest peer slice) explicitly
    allows the bridging from `homelab` → `networking` because the
    dns-blocker contract ids are `rc_net_dns_*` (the §net subsystem).
    The NAS contract ids are `rc_homelab_nas_*` (the homelab bucket
    directly), so there is NO bridging here — `category=homelab`
    matches the legacy doc pairing AND matches the subsystem prefix
    the contract tiles use.

    CRITICAL: the legacy doc must still exist (this connection
    covers the same single legacy page, not multiple) so the
    supersession banner can point at it.
    """
    assert manifest["category"] == "homelab", (
        f"category must stay 'homelab' (matches legacy doc at "
        f"{LEGACY_NAS_DOC.relative_to(REPO_ROOT)} + matches the "
        f"`rc_homelab_nas_*` subsystem prefix used by the contract "
        f"tiles per docs/reference/rc-entity-naming.md); "
        f"got {manifest['category']!r}"
    )
    assert LEGACY_NAS_DOC.is_file(), (
        f"expected the legacy NAS tier-b doc to still exist at {LEGACY_NAS_DOC} "
        f"so the supersession banner can point at it"
    )
    # Wave 9 #124c: legacy stub converted to a 2-line clean redirect
    # page (per directive repo-hygiene § "user-facing repo"). The file
    # must still exist (so old links resolve) and must now be a thin
    # redirect pointing at the canonical recipe — NOT carry the giant
    # supersession banner anymore.
    legacy_text = LEGACY_NAS_DOC.read_text(encoding="utf-8")
    assert "Moved" in legacy_text and "connections/nas/docs/recipe.md" in legacy_text, (
        "legacy docs/catalog/homelab/nas.md must be a 2-line 'Moved to ...' "
        "redirect page pointing at connections/nas/docs/recipe.md "
        "(Wave 9 #124c); got:\n" + legacy_text[:200]
    )
    # Belt-and-braces: the user-facing legacy doc must NOT carry the
    # giant supersession banner anymore (directive repo-hygiene §).
    assert "SUPERSEDED" not in legacy_text, (
        "legacy docs/catalog/homelab/nas.md must not carry the 'SUPERSEDED' "
        "banner (Wave 9 #124c — user-facing repo hygiene)"
    )


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """rc_* tile ids must NOT contain vendor names (per rc-entity-naming.md).

    The §homelab NAS contract is implementation-agnostic (it talks
    to whichever NAS the operator runs — Synology, QNAP, or generic
    SMB/NFS — via the upstream HA integration or via configuration
    yaml + the backup integration). Contract ids must stay vendor-
    neutral — no `synology`, `qnap`, `diskstation`, `dsm`, `smb`,
    `cifs`, `nfs`, `freenas`, `unraid`, `openmediavault`, or vendor
    double-stamps of `nas` into the suffix.

    The spec is strict: every `dashboard.tiles[*]` must match
    `^[a-z_]+\\.rc_homelab_nas_[a-z0-9_]+$` (vendor-neutral,
    subsystem prefix `rc_homelab_nas_*` per the homelab bucket
    naming rules in docs/reference/rc-entity-naming.md). The
    subsystem prefix IS allowed (it's the owning-area marker);
    what is forbidden is vendor names appearing AFTER the
    subsystem prefix in a way that double-stamps the vendor
    into the id beyond the subsystem token.
    """
    import re

    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles, "nas contributes at least one dashboard tile"

    # Every tile must be a string entity id (spec calls for tiles-as-
    # strings, mirroring the spec's listed shape).
    for tile in tiles:
        assert isinstance(tile, str), (
            f"dashboard.tiles[*] must be a string entity id (spec §1); "
            f"got {tile!r}"
        )

    # Domain segment is lowercase + underscores only (HA convention).
    # Suffix segment after `rc_homelab_nas_` may include digits
    # (e.g. `_pct`) but must not contain vendor double-stamps.
    pattern = re.compile(r"^[a-z_]+\.rc_homelab_nas_[a-z0-9_]+$")

    # Vendor / implementation names that must NEVER appear in any
    # rc_* tile id (beyond the subsystem prefix). Includes author /
    # host name of the upstream project AND common NAS OS names —
    # the contract is implementation-agnostic.
    forbidden = {
        # NAS vendors
        "synology", "qnap", "diskstation", "dsm",
        # NAS OS / software platforms
        "freenas", "truenas", "unraid", "openmediavault", "omv",
        # File-share protocols / implementations
        "smb", "cifs", "nfs", "samba", "netatalk", "afp",
        # NAS-specific firmware / feature names
        "raid", "snapraid", "btrfs", "zfs", "mergerfs",
        # The subsystem prefix `nas` is the ONLY place that
        # token appears — double-stamping "nas_" into the suffix
        # (e.g. _nas_status) is forbidden.
        "nas_",
        # Cross-connection vendor leaks
        "mqtt", "frigate", "starlink", "victron", "wican", "meatpi",
        "pi_hole", "pi-hole", "adguard",
    }

    for tile in tiles:
        assert pattern.match(tile), (
            f"tile id {tile!r} must match ^[a-z_]+\\.rc_homelab_nas_[a-z0-9_]+$ "
            f"(vendor-neutral contract naming per docs/reference/rc-entity-naming.md)"
        )
        # Subsystem prefix is rc_homelab_nas_; the suffix (after
        # `rc_homelab_nas_`) MUST be a single identifier segment
        # — no double-stamping of vendor names into the suffix.
        suffix = tile.split(".rc_homelab_nas_", 1)[1]
        # Belt-and-braces: subsystem token `nas` MUST NOT appear
        # as a standalone word in the suffix (the subsystem prefix
        # is the only place that token lives).
        assert "nas" not in suffix.lower().split("_"), (
            f"tile id {tile!r} double-stamps 'nas' into the suffix "
            f"(only the subsystem prefix `rc_homelab_nas_` may carry the token)"
        )
        # Each segment after the dot must be lowercase + underscores + digits.
        for segment in tile.split("."):
            assert re.match(r"^[a-z_][a-z0-9_]*$", segment), (
                f"tile id {tile!r} contains a non-conforming segment {segment!r}"
            )
        for bad in forbidden:
            # We explicitly allow the single 'nas' token inside
            # the subsystem prefix by checking after rc_homelab_nas_.
            tail = tile.split(".rc_homelab_nas_", 1)[-1] if ".rc_homelab_nas_" in tile else tile
            assert bad not in tail.lower(), (
                f"tile id {tile!r} contains forbidden name {bad!r}; "
                f"per docs/reference/rc-entity-naming.md, contract ids are vendor-neutral"
            )


def test_status_reflects_no_real_nas(manifest: dict) -> None:
    """Status must be honest about no integration being shipped.

    If we ever flip this to 'shipped', the audit will demand an
    actual integration test (and rightly so). 'beta' is the only
    honest tier-b status for a recipe we can't integration-test.
    """
    assert manifest["status"] in {"beta", "wip"}, (
        f"nas status={manifest['status']!r} implies shipped coverage we don't have; "
        f"use 'beta' or 'wip' until tier-a promotion lands"
    )
    # tier_warnings must include the honest-about-no-NAS marker.
    assert "no_real_nas_for_integration_test" in manifest["tier_warnings"], (
        "tier_warnings must declare 'no_real_nas_for_integration_test' "
        "for honesty in the audit listing"
    )
    # And the user-facing recipe dependency warning.
    assert "recipe_depends_on_user_running_nas" in manifest["tier_warnings"], (
        "tier_warnings must declare 'recipe_depends_on_user_running_nas' "
        "so the audit listing is honest about the user-bringing-the-NAS contract"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))