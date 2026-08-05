"""Manifest-honesty tests for connections/dns-blocker/connection.yml.

This is the only test file we can ship for a tier-b recipe connection
that has no real DNS blocker on the bench to integration-test against.
The tests here assert that the manifest is *honest about being tier-b* —
that the folder/id/tier invariants hold, that the recipe doc the
tier_requirements promise is actually present on disk, that the
rc_net_dns_* tile ids are vendor-neutral per
docs/reference/rc-entity-naming.md, and that both legacy tier-c specs
(Pi-hole + AdGuard Home) still exist so the supersession banners can
point at them.

NUANCE — config_flow=true is allowed here, unlike Starlink:

  Starlink recipes an operator-side plug (TP-Link / Shelly / Sonoff /
  Zigbee / Modbus / ...). There is no canonical upstream HA
  integration that does the operator-side power-cycle path Starlink
  recipes, so `install.config_flow: true` would falsely imply a
  RoamCore-owned native config_flow we don't have. Hence the Starlink
  manifest asserts config_flow=false at tier-b.

  DNS blocker recipes both Pi-hole AND AdGuard Home. Both upstream
  integrations have had working config_flows in HA core for years:
    - Pi-hole (ha_integration_domain: pi_hole): config_flow since
      2021.8.
    - AdGuard Home (ha_integration_domain: adguard): config_flow
      since 2022.11.
  The `install.config_flow: true` here is UPSTREAM truth (the
  operator adds the integration via HA's own config_flow), NOT a
  RoamCore-owned config_flow. The `__init__.py` is a DOMAIN stub
  and there is no RoamCore-owned config_flow.py in this folder. If
  a future RoamCore release ships a native wrapper around the
  upstream config_flow (e.g. a wizard-side helper that auto-creates
  the rc_net_dns_* tiles post-config_flow), this test would be
  updated to also assert a config_flow.py is present.

If you add real integration coverage (e.g. a config_flow.py + an
integration test against testcontainers/pihole or testcontainers/
adguardhome with a synthetic admin-API fixture), keep this file and
add the new one alongside it; the audit will then list both under
`tests:` in the manifest.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/dns-blocker/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> dns-blocker/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "dns-blocker"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
LEGACY_PIHOLE_DOC = REPO_ROOT / "docs" / "catalog" / "homelab" / "pi-hole.md"
LEGACY_ADGUARD_DOC = REPO_ROOT / "docs" / "catalog" / "homelab" / "adguard-home.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (dns-blocker).

    This is the same invariant the audit script enforces; we duplicate
    it here so pytest catches regressions before CI runs the audit.
    """
    assert manifest["id"] == CONNECTION_DIR.name, (
        f"manifest id={manifest['id']!r} does not match folder name "
        f"{CONNECTION_DIR.name!r}"
    )
    assert manifest["id"] == "dns-blocker"


def test_tier_b_without_tier_a_markers(manifest: dict) -> None:
    """Tier-b must NOT advertise tier-a-only fields — except for config_flow.

    NUANCE (see module docstring): unlike Starlink, the DNS-blocker
    manifest DOES set install.config_flow=true because both upstream
    integrations (Pi-hole and AdGuard Home) have had config_flow in
    HA core since 2021.8 / 2022.11 respectively. The config_flow=true
    field is UPSTREAM truth, NOT a RoamCore-owned config_flow. To
    catch a future regression where someone mistakes the upstream
    config_flow truth for a RoamCore-owned one, we assert:

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
    assert manifest["tier"] == "b", "dns-blocker must stay at tier-b until integration coverage lands"
    assert manifest["wizard"]["one_tap"] is False, (
        "tier-b connections cannot advertise one_tap=true (that's a tier-a contract)"
    )
    # install.config_flow: true is UPSTREAM truth for DNS blocker
    # (Pi-hole + AdGuard Home both have config_flow in HA core).
    # We assert it IS true (matches upstream reality), but we ALSO
    # assert there is no RoamCore-owned config_flow.py / no
    # async_setup code in __init__.py — so the truth is honest.
    assert manifest["install"]["config_flow"] is True, (
        "dns-blocker must advertise install.config_flow=true (UPSTREAM truth: "
        "both Pi-hole and AdGuard Home have config_flow in HA core)"
    )
    assert manifest["install"]["hacs"] is False, (
        "dns-blocker is a recipe; no HACS integration of our own is shipped"
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
    # Sanity: the recipe actually documents a DNS blocker setup
    # (Pi-hole / AdGuard Home) rather than just an empty placeholder.
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert len(text) > 500, "recipe.md looks like a placeholder — should be a real howto"
    assert ("DNS blocker" in text or "Pi-hole" in text or "AdGuard" in text), (
        "recipe.md must document the DNS-blocker setup "
        "(Path A Pi-hole install + Path B AdGuard Home install + contract wiring)"
    )
    # The spec requires ≥100 lines; we ship a substantive howto well
    # over both; this catches a regression where someone leaves a
    # 30-line placeholder.
    line_count = len(text.splitlines())
    assert line_count > 100, (
        f"recipe.md must be a substantive howto (>100 lines); got {line_count}"
    )
    # Spec §4 calls for the §1–§7 sections to be present. Grep-anchor
    # the major section headers so a future "I rewrote the recipe as
    # one wall of text" regression gets caught.
    required_sections = (
        "## What is a DNS blocker in RoamCore?",
        "## Prerequisites",
        "## Path A",
        "## Path B",
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
    """Promoted from tier-c legacy docs — category must match.

    Both legacy tier-c specs (Pi-hole + AdGuard Home) live at
    docs/catalog/homelab/pi-hole.md and docs/catalog/homelab/adguard-home.md.
    We set category=networking (the §net subsystem) because the
    rc_net_dns_* contract ids belong under `net` per
    docs/reference/rc-entity-naming.md — but the legacy docs live
    under docs/catalog/homelab/, so the natural alternative is
    category=homelab. We pick networking here for the §net
    subsystem fit; the legacy docs are still present with
    supersession banners so the homelab catalog tag has something
    to discover.

    CRITICAL: BOTH legacy docs must still exist (this connection
    covers BOTH Pi-hole and AdGuard Home, not just one). The
    supersession banners reference both.
    """
    assert manifest["category"] == "networking", (
        f"category must stay 'networking' (§net subsystem per docs/reference/rc-entity-naming.md "
        f"for rc_net_dns_* contract ids); got {manifest['category']!r}"
    )
    assert LEGACY_PIHOLE_DOC.is_file(), (
        f"expected the legacy Pi-hole tier-c doc to still exist at {LEGACY_PIHOLE_DOC} "
        f"so old links resolve to the redirect page"
    )
    assert LEGACY_ADGUARD_DOC.is_file(), (
        f"expected the legacy AdGuard Home tier-c doc to still exist at {LEGACY_ADGUARD_DOC} "
        f"so old links resolve to the redirect page "
        f"(this connection covers BOTH blockers, not just one)"
    )
    # Wave 9 #124c: BOTH legacy stubs converted to 2-line clean
    # redirect pages (per directive repo-hygiene § "user-facing repo").
    # The files must still exist (so old links resolve) and must now
    # be thin redirects pointing at the canonical recipe — NOT carry
    # the giant supersession banner anymore.
    pihole_text = LEGACY_PIHOLE_DOC.read_text(encoding="utf-8")
    assert "Moved" in pihole_text and "connections/dns-blocker/docs/recipe.md" in pihole_text, (
        "legacy docs/catalog/homelab/pi-hole.md must be a 2-line 'Moved to ...' "
        "redirect page pointing at connections/dns-blocker/docs/recipe.md "
        "(Wave 9 #124c); got:\n" + pihole_text[:200]
    )
    assert "SUPERSEDED" not in pihole_text, (
        "legacy docs/catalog/homelab/pi-hole.md must not carry the 'SUPERSEDED' "
        "banner (Wave 9 #124c — user-facing repo hygiene)"
    )
    adguard_text = LEGACY_ADGUARD_DOC.read_text(encoding="utf-8")
    assert "Moved" in adguard_text and "connections/dns-blocker/docs/recipe.md" in adguard_text, (
        "legacy docs/catalog/homelab/adguard-home.md must be a 2-line "
        "'Moved to ...' redirect page pointing at "
        "connections/dns-blocker/docs/recipe.md (Wave 9 #124c); got:\n"
        + adguard_text[:200]
    )
    assert "SUPERSEDED" not in adguard_text, (
        "legacy docs/catalog/homelab/adguard-home.md must not carry the "
        "'SUPERSEDED' banner (Wave 9 #124c — user-facing repo hygiene)"
    )


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """rc_* tile ids must NOT contain vendor names (per rc-entity-naming.md).

    The §net DNS contract is implementation-agnostic (it talks to
    whichever blocker the operator runs — Pi-hole or AdGuard Home —
    via the upstream HA integration). Contract ids must stay vendor-
    neutral — no `pi-hole`, `pi_hole`, `adguard`, `adblock`,
    `unbound`, `dnsmasq`, `blocklist`, `cloudflare`, `quad9`,
    upstream DNS vendor names, or double-stamps of "dns_blocker"
    into the suffix.

    The spec is strict: every `dashboard.tiles[*]` must match
    `^[a-z_]+\\.rc_net_dns_[a-z0-9_]+$` (vendor-neutral, subsystem
    prefix `rc_net_dns_*` per the §net subsystem naming rules in
    docs/reference/rc-entity-naming.md). The subsystem prefix IS
    allowed (it's the owning-area marker); what is forbidden is
    vendor names appearing AFTER the subsystem prefix in a way
    that double-stamps the vendor into the id beyond the
    subsystem token.
    """
    import re

    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles, "dns-blocker contributes at least one dashboard tile"

    # Every tile must be a string entity id (spec calls for tiles-as-
    # strings, mirroring the spec's listed shape).
    for tile in tiles:
        assert isinstance(tile, str), (
            f"dashboard.tiles[*] must be a string entity id (spec §1); "
            f"got {tile!r}"
        )

    # Domain segment is lowercase + underscores only (HA convention).
    # Suffix segment after `rc_net_dns_` may include digits (e.g.
    # `_pct`) but must not contain vendor double-stamps.
    pattern = re.compile(r"^[a-z_]+\.rc_net_dns_[a-z0-9_]+$")

    # Vendor / implementation names that must NEVER appear in any
    # rc_* tile id (beyond the subsystem prefix). Includes author /
    # host name of the upstream project AND common upstream DNS
    # resolver names — the contract is implementation-agnostic AND
    # resolver-agnostic.
    forbidden = {
        # Blocker vendors
        "pi-hole", "pi_hole", "adguard", "adguard_home", "adguardhome",
        "adblock",
        # DNS server / resolver implementations
        "unbound", "dnsmasq", "bind", "named", "powerdns",
        # Upstream DNS resolver vendors (the contract must be resolver-agnostic)
        "cloudflare", "quad9", "quad_9", "google_dns", "opendns",
        # Generic DNS terminology that must not double-stamp into the suffix
        "blocklist", "gravity_list", "upstream_",
        # The subsystem prefix `dns_blocker` is the ONLY place
        # "dns_blocker" appears — double-stamping "dns_blocker_"
        # into the suffix (e.g. _dns_blocker_query) is forbidden.
        "dns_blocker_",
        # Cross-connection vendor leaks
        "mqtt", "frigate", "starlink", "victron", "wican", "meatpi",
    }

    for tile in tiles:
        assert pattern.match(tile), (
            f"tile id {tile!r} must match ^[a-z_]+\\.rc_net_dns_[a-z0-9_]+$ "
            f"(vendor-neutral contract naming per docs/reference/rc-entity-naming.md)"
        )
        # Subsystem prefix is rc_net_dns_; the suffix (after
        # `rc_net_dns_`) MUST be a single identifier segment
        # — no double-stamping of vendor names into the suffix.
        suffix = tile.split(".rc_net_dns_", 1)[1]
        # Belt-and-braces: subsystem token `dns_blocker` MUST NOT
        # appear in the suffix (the subsystem prefix is the only
        # place that token lives).
        assert "dns_blocker" not in suffix.lower().split("_"), (
            f"tile id {tile!r} double-stamps 'dns_blocker' into the suffix "
            f"(only the subsystem prefix `rc_net_dns_` may carry the token)"
        )
        # Each segment after the dot must be lowercase + underscores + digits.
        for segment in tile.split("."):
            assert re.match(r"^[a-z_][a-z0-9_]*$", segment), (
                f"tile id {tile!r} contains a non-conforming segment {segment!r}"
            )
        for bad in forbidden:
            # We explicitly allow the single 'dns_blocker' token inside
            # the subsystem prefix by checking after rc_net_dns_.
            tail = tile.split(".rc_net_dns_", 1)[-1] if ".rc_net_dns_" in tile else tile
            assert bad not in tail.lower(), (
                f"tile id {tile!r} contains forbidden name {bad!r}; "
                f"per docs/reference/rc-entity-naming.md, contract ids are vendor-neutral"
            )


def test_status_reflects_no_real_dns_blocker(manifest: dict) -> None:
    """Status must be honest about no integration being shipped.

    If we ever flip this to 'shipped', the audit will demand an
    actual integration test (and rightly so). 'beta' is the only
    honest tier-b status for a recipe we can't integration-test.
    """
    assert manifest["status"] in {"beta", "wip"}, (
        f"dns-blocker status={manifest['status']!r} implies shipped coverage we don't have; "
        f"use 'beta' or 'wip' until tier-a promotion lands"
    )
    # tier_warnings must include the honest-about-no-blocker marker.
    assert "no_real_dns_blocker_for_integration_test" in manifest["tier_warnings"], (
        "tier_warnings must declare 'no_real_dns_blocker_for_integration_test' "
        "for honesty in the audit listing"
    )
    # And the user-facing recipe dependency warning.
    assert "recipe_depends_on_user_running_pi_hole_or_adguard" in manifest["tier_warnings"], (
        "tier_warnings must declare 'recipe_depends_on_user_running_pi_hole_or_adguard' "
        "so the audit listing is honest about the user-bringing-the-blocker contract"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))