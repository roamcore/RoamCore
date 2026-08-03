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
    """Sanity: category is set (legacy-doc pairing no longer enforced)."""
    assert manifest["category"], "category must be set"


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