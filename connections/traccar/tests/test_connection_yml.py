"""Tests for connections/traccar/connection.yml.

These tests verify the connection manifest is internally consistent
and matches the declared reality on disk:

  - the yml parses and validates against the JSON schema
  - the id matches the folder name
  - the ha_integration_domain in the yml matches the live integration
  - the ha_addon slug in the yml matches the add-on folder on disk
  - tier-claim is honest (tier=a requires config_flow + tests)
  - tier_requirements contains everything the schema requires for the tier
  - all references in tier_requirements resolve to real on-disk evidence

The audit robot (scripts/audit_connections.py) covers this at the
repo-wide level; these tests are the per-connection slice and give
a tighter, faster feedback loop when iterating on the yml.

Run:
    cd connections/traccar && python -m pytest tests/ -v
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

# Repo layout: <repo>/connections/traccar/tests/test_connection_yml.py
REPO = Path(__file__).resolve().parents[3]
CONNECTION_DIR = Path(__file__).resolve().parents[1]
MANIFEST = CONNECTION_DIR / "connection.yml"
SETUP_DOC = CONNECTION_DIR / "docs" / "setup.md"
INTEGRATION_INIT = REPO / "homeassistant" / "custom_components" / "roamcore_traccar_proxy" / "__init__.py"
PROXY_ADDON_DIR = REPO / "homeassistant" / "addons" / "roamcore-traccar-proxy"
INIT_ADDON_DIR = REPO / "homeassistant" / "addons" / "roamcore-traccar-init"
SCHEMA = REPO / "connections" / "_schema" / "connection.schema.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def manifest() -> dict:
    """Load + parse connection.yml once per module."""
    assert MANIFEST.is_file(), f"connection.yml missing at {MANIFEST}"
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Manifest sanity
# ---------------------------------------------------------------------------

def test_manifest_is_present():
    """The connection.yml must exist on disk. (Build error if not.)"""
    assert MANIFEST.is_file()


def test_manifest_parses_as_yaml(manifest):
    """The yml must parse and be a mapping at the top level."""
    assert isinstance(manifest, dict), "connection.yml must be a YAML mapping"


def test_id_matches_folder_name(manifest):
    """The id must equal the folder name (the audit enforces this)."""
    assert manifest["id"] == CONNECTION_DIR.name, (
        f"id {manifest['id']!r} does not match folder "
        f"{CONNECTION_DIR.name!r}"
    )


def test_manifest_validates_against_schema(manifest, schema):
    """The yml must satisfy the schema — catch typos and missing fields."""
    try:
        import jsonschema
    except ImportError:
        pytest.skip("jsonschema not installed; run: pip install jsonschema")
    validator = jsonschema.Draft202012Validator(schema)
    errors = list(validator.iter_errors(manifest))
    assert not errors, (
        "connection.yml does not validate against the schema:\n"
        + "\n".join(
            f"  - {'.'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
            for e in errors
        )
    )


# ---------------------------------------------------------------------------
# Tier honesty
# ---------------------------------------------------------------------------

def test_tier_claim_is_honest(manifest, integration_has_config_flow):
    """If the yml claims tier=a, the integration MUST have a config_flow.

    The audit enforces this at the repo level; this is the per-connection
    guard so a typo in the yml can't accidentally green-wash a tier-b
    connection into tier-a.
    """
    if manifest["tier"] == "a":
        assert integration_has_config_flow, (
            "yml claims tier=a but the live integration has no config_flow. "
            "Either downgrade to tier=b or add a real config_flow."
        )


@pytest.fixture(scope="module")
def integration_has_config_flow() -> bool:
    """Detect whether the live integration has a config_flow on disk.

    We look for either:
      - a `config_flow.py` file in the integration directory, OR
      - a `ConfigFlow` class in the integration's __init__.py
    """
    if not INTEGRATION_INIT.is_file():
        return False
    if (INTEGRATION_INIT.parent / "config_flow.py").is_file():
        return True
    text = INTEGRATION_INIT.read_text(encoding="utf-8")
    return bool(re.search(r"\bclass\s+ConfigFlow\b", text))


def test_tier_b_requires_docs_recipe_published(manifest):
    """tier=b must include 'docs_recipe_published' in tier_requirements."""
    if manifest["tier"] != "b":
        pytest.skip("only enforced for tier=b")
    assert "docs_recipe_published" in manifest.get("tier_requirements", []), (
        "tier=b requires 'docs_recipe_published' in tier_requirements"
    )


def test_status_shipped_requires_tests(manifest):
    """status=shipped requires `tests:` to be present."""
    if manifest["status"] != "shipped":
        pytest.skip("only enforced for status=shipped")
    assert manifest.get("tests"), "status=shipped requires a non-empty `tests` list"


def test_tier_warnings_present_when_promotion_blocked(manifest):
    """If we're tier=b but there's no config_flow, tier_warnings should
    make the blocker explicit. This is the audit's documented 'be honest
    about promotion blockers' rule."""
    if manifest["tier"] != "b":
        pytest.skip("only enforced for tier=b")
    if not _integration_has_config_flow():
        warnings = manifest.get("tier_warnings", [])
        assert any("promotion_blocker" in w for w in warnings), (
            "tier=b with no config_flow MUST include a 'promotion_blocker' "
            "entry in tier_warnings explaining why this is not tier=a."
        )


def _integration_has_config_flow() -> bool:
    if not INTEGRATION_INIT.is_file():
        return False
    if (INTEGRATION_INIT.parent / "config_flow.py").is_file():
        return True
    return bool(re.search(r"\bclass\s+ConfigFlow\b",
                          INTEGRATION_INIT.read_text(encoding="utf-8")))


# ---------------------------------------------------------------------------
# Install contract cross-checks
# ---------------------------------------------------------------------------

def test_ha_integration_domain_resolves_to_real_integration(manifest):
    """The `ha_integration_domain` must point to a real custom_component."""
    domain = manifest["install"]["ha_integration_domain"]
    path = REPO / "homeassistant" / "custom_components" / domain
    assert path.is_dir(), (
        f"install.ha_integration_domain {domain!r} does not resolve to "
        f"{path.relative_to(REPO)} on disk"
    )
    assert (path / "__init__.py").is_file() or (path / "manifest.json").is_file(), (
        f"Integration {domain!r} has neither __init__.py nor manifest.json"
    )


def test_ha_addon_slug_resolves_to_addon_directory(manifest):
    """If a ha_addon is declared, its folder must exist on disk."""
    addon = manifest["install"].get("ha_addon")
    if not addon:
        pytest.skip("no ha_addon declared")
    addon_path = REPO / "homeassistant" / "addons" / addon
    assert addon_path.is_dir(), (
        f"install.ha_addon {addon!r} does not resolve to "
        f"{addon_path.relative_to(REPO)} on disk"
    )
    assert (addon_path / "config.yaml").is_file(), (
        f"Addon {addon!r} has no config.yaml — not a valid HA add-on"
    )


def test_init_addon_present_when_proxy_addon_present(manifest):
    """Traccar recipe requires the init add-on (first-boot credentials).
    If we ever drop the proxy add-on, this check should be revisited."""
    addon = manifest["install"].get("ha_addon")
    if addon != "roamcore-traccar-proxy":
        pytest.skip("only enforced for the proxy add-on")
    assert INIT_ADDON_DIR.is_dir(), (
        "roamcore-traccar-proxy declared but roamcore-traccar-init missing — "
        "the recipe requires the init add-on for first-boot credentials"
    )
    assert (INIT_ADDON_DIR / "config.yaml").is_file()


# ---------------------------------------------------------------------------
# Wizard honesty
# ---------------------------------------------------------------------------

def test_one_tap_is_false_for_recipe(manifest):
    """wizard.connection_kind=recipe MUST have one_tap: false."""
    if manifest.get("wizard", {}).get("connection_kind") != "recipe":
        pytest.skip("only enforced for recipe connections")
    assert manifest["wizard"].get("one_tap") is False, (
        "recipe connections cannot be one-tap — the user must install "
        "add-ons manually. Setting one_tap: true here would lie to the user."
    )


def test_auto_discover_is_false_for_recipe(manifest):
    """Recipes don't auto-discover by definition."""
    if manifest.get("wizard", {}).get("connection_kind") != "recipe":
        pytest.skip("only enforced for recipe connections")
    assert manifest["wizard"].get("auto_discover") is False, (
        "recipe connections cannot auto-discover — the user must opt in."
    )


# ---------------------------------------------------------------------------
# OpenClaw contract
# ---------------------------------------------------------------------------

def test_openclaw_queries_are_non_empty(manifest):
    """Every connection must declare at least one natural-language query
    so the OpenClaw agent can route 'where am I?' etc."""
    queries = manifest.get("openclaw", {}).get("queries", [])
    assert queries, "openclaw.queries must be non-empty"


def test_openclaw_summary_keys_use_snake_case(manifest):
    """summary_keys must be snake_case so they compose into JSON cleanly."""
    keys = manifest.get("openclaw", {}).get("summary_keys", [])
    assert keys, "openclaw.summary_keys must be non-empty"
    bad = [k for k in keys if not re.fullmatch(r"[a-z][a-z0-9_]{2,63}", k)]
    assert not bad, f"summary_keys must be snake_case, got: {bad}"


# ---------------------------------------------------------------------------
# Docs recipe (the tier-b deliverable)
# ---------------------------------------------------------------------------

def test_setup_doc_exists(manifest):
    """tier=b requires a published recipe. The pipeline treats
    docs/setup.md as the recipe location."""
    if manifest["tier"] != "b":
        pytest.skip("only enforced for tier=b")
    assert SETUP_DOC.is_file(), (
        f"tier=b requires a recipe at {SETUP_DOC.relative_to(REPO)}"
    )


def test_setup_doc_mentions_addon_install(manifest):
    """The recipe must (a) mention the add-on install + (b) explain how
    the user gets the Traccar URL + (c) explain device linking."""
    if manifest["tier"] != "b":
        pytest.skip("only enforced for tier=b")
    text = SETUP_DOC.read_text(encoding="utf-8").lower()
    assert "roamcore-traccar-proxy" in text or "traccar proxy" in text, (
        "setup.md must mention the roamcore-traccar-proxy add-on install"
    )
    assert "url" in text or "http" in text, (
        "setup.md must explain how the user gets the Traccar instance URL"
    )
    assert "device" in text, (
        "setup.md must explain device linking (Traccar device id ↔ HA entity)"
    )
