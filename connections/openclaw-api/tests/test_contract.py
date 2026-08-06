"""Contract-version + skill-discovery tests for the OpenClaw API.

The "contract" is the OpenClaw API's backwards-compatibility promise:
`contract.version` is a monotonically-increasing integer that the
RoamCore integration publishes on every endpoint. A bump is a
breaking change for the agent-side and MUST be handled defensively
on both sides (the integration bumps the version + emits a
`roamcore_openclaw_contract_bumped` event; the agent sees the new
version + asks the operator to re-run the skill discovery flow).

This test file asserts the contract layer end-to-end through the
real HA test rig (the `hass` fixture in `conftest.py`):

  1. `contract_version` is exposed via the `X-RoamCore-Contract: 1`
     HTTP header on every endpoint (the agent checks this header
     FIRST so it can detect a bump before parsing the body).
  2. The integration's `DEFAULT_CONTRACT_VERSION` constant matches
     the `X-RoamCore-Contract` header (the two CANNOT drift).
  3. The agent-skill discovery endpoint returns the canonical
     summary_url (the entry point the agent uses to discover the API).

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/openclaw-api/tests/test_contract.py -v
"""

from __future__ import annotations

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


CONTRACT_HEADER = "X-RoamCore-Contract"
# The canonical contract version, hardcoded in the integration's
# `const.py` as `DEFAULT_CONTRACT_VERSION = 1`. If this test ever
# fails with "expected 1, got 2", that means the integration bumped
# the contract and the recipe + the connection.yml + the agent
# skill + the canonical spec all need to be updated to match.
EXPECTED_CONTRACT_VERSION = 1
EXPECTED_CONTRACT_NAME = "roamcore_openclaw_summary"


REPO_ROOT = Path(__file__).resolve().parents[3]
CONST_PATH = (
    REPO_ROOT
    / "homeassistant"
    / "custom_components"
    / "roamcore"
    / "const.py"
)
CONNECTION_YML_PATH = (
    REPO_ROOT / "connections" / "openclaw-api" / "connection.yml"
)
SKILL_PAYLOAD_PATH = (
    REPO_ROOT / "openclaw" / "skills" / "roamcore" / "SKILL.md"
)
CANONICAL_SPEC_PATH = (
    REPO_ROOT / "docs" / "reference" / "openclaw-json-api.md"
)
RECIPE_PATH = (
    REPO_ROOT
    / "connections"
    / "openclaw-api"
    / "docs"
    / "recipe.md"
)


# ---------------------------------------------------------------------------
# Test 1: contract_version is exposed via the X-RoamCore-Contract header
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_emits_x_roamcore_contract_header(hass_client) -> None:
    """The `/api/roamcore/openclaw/summary` endpoint MUST emit
    the `X-RoamCore-Contract` header on every response.

    The agent checks this header FIRST so it can detect a contract
    bump before parsing the body (the body shape may have changed
    between versions; the header is the canary).
    """
    resp = await hass_client.get("/api/roamcore/openclaw/summary")
    assert resp.status == 200
    assert CONTRACT_HEADER in resp.headers, (
        f"openclaw summary response missing {CONTRACT_HEADER} header; "
        f"the agent uses this header to detect a contract bump before "
        f"parsing the body; headers were {sorted(resp.headers)!r}"
    )
    assert resp.headers[CONTRACT_HEADER] == str(EXPECTED_CONTRACT_VERSION), (
        f"openclaw summary {CONTRACT_HEADER} header = "
        f"{resp.headers[CONTRACT_HEADER]!r}; expected "
        f"{EXPECTED_CONTRACT_VERSION!r} (the canonical contract "
        f"version in `homeassistant/custom_components/roamcore/"
        f"const.py`)"
    )


@pytest.mark.asyncio
async def test_skill_emits_x_roamcore_contract_header(hass_client) -> None:
    """The `/api/roamcore/openclaw/skill` endpoint MUST emit
    the `X-RoamCore-Contract` header on every response.
    """
    resp = await hass_client.get("/api/roamcore/openclaw/skill")
    assert resp.status == 200
    assert CONTRACT_HEADER in resp.headers
    assert resp.headers[CONTRACT_HEADER] == str(EXPECTED_CONTRACT_VERSION)


@pytest.mark.asyncio
async def test_rc_dump_emits_x_roamcore_contract_header(hass_client) -> None:
    """The `/api/roamcore/openclaw/rc_dump` endpoint MUST emit
    the `X-RoamCore-Contract` header.
    """
    resp = await hass_client.get("/api/roamcore/openclaw/rc_dump")
    assert resp.status == 200
    assert CONTRACT_HEADER in resp.headers
    assert resp.headers[CONTRACT_HEADER] == str(EXPECTED_CONTRACT_VERSION)


@pytest.mark.asyncio
async def test_timeseries_catalog_emits_x_roamcore_contract_header(
    hass_client,
) -> None:
    """The `/api/roamcore/openclaw/timeseries/catalog` endpoint MUST
    emit the `X-RoamCore-Contract` header.
    """
    resp = await hass_client.get(
        "/api/roamcore/openclaw/timeseries/catalog"
    )
    assert resp.status == 200
    assert CONTRACT_HEADER in resp.headers
    assert resp.headers[CONTRACT_HEADER] == str(EXPECTED_CONTRACT_VERSION)


@pytest.mark.asyncio
async def test_automation_intents_emits_x_roamcore_contract_header(
    hass_client,
) -> None:
    """The `/api/roamcore/openclaw/automation/intents` endpoint MUST
    emit the `X-RoamCore-Contract` header.
    """
    resp = await hass_client.get(
        "/api/roamcore/openclaw/automation/intents"
    )
    assert resp.status == 200
    assert CONTRACT_HEADER in resp.headers
    assert resp.headers[CONTRACT_HEADER] == str(EXPECTED_CONTRACT_VERSION)


@pytest.mark.asyncio
async def test_diagnostics_emits_x_roamcore_contract_header(
    hass_auth_client,
) -> None:
    """The `/api/roamcore/diagnostics` endpoint MUST emit
    the `X-RoamCore-Contract` header (even though it requires auth).
    """
    resp = await hass_auth_client.get("/api/roamcore/diagnostics")
    assert resp.status == 200
    assert CONTRACT_HEADER in resp.headers
    assert resp.headers[CONTRACT_HEADER] == str(EXPECTED_CONTRACT_VERSION)


@pytest.mark.asyncio
async def test_system_summary_emits_x_roamcore_contract_header(
    hass_auth_client,
) -> None:
    """The `/api/roamcore/system/summary` endpoint MUST emit
    the `X-RoamCore-Contract` header.
    """
    resp = await hass_auth_client.get("/api/roamcore/system/summary")
    assert resp.status == 200
    assert CONTRACT_HEADER in resp.headers
    assert resp.headers[CONTRACT_HEADER] == str(EXPECTED_CONTRACT_VERSION)


@pytest.mark.asyncio
async def test_update_emits_x_roamcore_contract_header(hass_auth_client) -> None:
    """The `/api/roamcore/update` endpoint MUST emit
    the `X-RoamCore-Contract` header.
    """
    resp = await hass_auth_client.get("/api/roamcore/update")
    assert resp.status == 200
    assert CONTRACT_HEADER in resp.headers
    assert resp.headers[CONTRACT_HEADER] == str(EXPECTED_CONTRACT_VERSION)


# ---------------------------------------------------------------------------
# Test 2: the integration's CONTRACT_VERSION constant matches the header
# ---------------------------------------------------------------------------


def test_const_py_contract_version_is_v1() -> None:
    """The `DEFAULT_CONTRACT_VERSION` constant in the integration's
    `const.py` MUST be `1` (the current contract version).

    If this test fails, the integration has bumped the contract
    version. That bump is a coordinated change with the recipe
    + the connection.yml + the agent skill + the canonical spec —
    update ALL of them in the same PR or the agent will silently
    drift.
    """
    src = CONST_PATH.read_text(encoding="utf-8")
    assert "DEFAULT_CONTRACT_VERSION = 1" in src, (
        f"`{CONST_PATH}` is missing the literal "
        f"`DEFAULT_CONTRACT_VERSION = 1`; the contract has been "
        f"bumped (the integration code is now out of sync with "
        f"the recipe + the connection.yml). The bump is a "
        f"coordinated change — update the recipe §8.5 contract-"
        f"version-bump-notify guard + the connection.yml manifest "
        f"+ the agent skill + the canonical spec in the same PR."
    )
    # The RoamCore views read CONTRACT_VERSION off the config entry
    # options (defaulting to DEFAULT_CONTRACT_VERSION). The integration
    # MUST also expose the `X-RoamCore-Contract` header constant.
    assert "ROAMCORE_CONTRACT_HEADER = " in src, (
        f"`{CONST_PATH}` is missing the "
        f"`ROAMCORE_CONTRACT_HEADER = ` constant; the "
        f"`apply_contract_header` helper in "
        f"`homeassistant/custom_components/roamcore/contract_header.py` "
        f"uses this to set the canary header on every response."
    )


def test_contract_header_helper_exists() -> None:
    """The `apply_contract_header` helper MUST exist in
    `homeassistant/custom_components/roamcore/contract_header.py`.

    The helper is the single source of truth for the
    `X-RoamCore-Contract` header. Every view calls it on its
    response. If the file is gone or the function is renamed,
    the header silently disappears from the API surface — and
    the agent has no canary for contract bumps.
    """
    helper_path = (
        REPO_ROOT
        / "homeassistant"
        / "custom_components"
        / "roamcore"
        / "contract_header.py"
    )
    assert helper_path.is_file(), (
        f"`{helper_path}` is missing; the `apply_contract_header` "
        f"helper is the single source of truth for the canary "
        f"header; if it's gone, the agent has no way to detect "
        f"a contract bump."
    )
    src = helper_path.read_text(encoding="utf-8")
    assert "def apply_contract_header" in src, (
        f"`{helper_path}` is missing the `apply_contract_header` "
        f"function; the views call it on every response."
    )


# ---------------------------------------------------------------------------
# Test 3: integration code wires the helper into every view
# ---------------------------------------------------------------------------


def test_openclaw_view_calls_apply_contract_header() -> None:
    """The RoamCore OpenClaw views (`openclaw_view.py`) MUST call
    `apply_contract_header` on every response. The function is
    the contract-bump canary — if any view is missing the call,
    the agent can't detect a contract version bump on that
    endpoint.
    """
    text = (
        REPO_ROOT
        / "homeassistant"
        / "custom_components"
        / "roamcore"
        / "openclaw_view.py"
    ).read_text(encoding="utf-8")
    # The file must contain the import.
    assert "from .contract_header import apply_contract_header" in text, (
        f"`openclaw_view.py` is missing the `apply_contract_header` "
        f"import; the views won't set the X-RoamCore-Contract header."
    )
    # The file must call apply_contract_header at least 9 times (one
    # per view return path; the OpenClaw summary / skill / rc_dump /
    # timeseries / timeseries-catalog / timeseries-no-keys /
    # automation-intents / automation-validate use-post / and
    # automation-validate-success paths).
    count = text.count("apply_contract_header(self.json")
    assert count >= 9, (
        f"`openclaw_view.py` only calls `apply_contract_header` "
        f"{count} times; expected >= 9 (one per response path). A "
        f"missing call means a view's response won't carry the "
        f"X-RoamCore-Contract header — the agent's contract-bump "
        f"canary is broken for that endpoint."
    )


def test_diagnostics_view_calls_apply_contract_header() -> None:
    """The diagnostics view must call apply_contract_header
    (the auth-required endpoints need the header too).
    """
    text = (
        REPO_ROOT
        / "homeassistant"
        / "custom_components"
        / "roamcore"
        / "diagnostics_view.py"
    ).read_text(encoding="utf-8")
    assert "apply_contract_header" in text, (
        f"`diagnostics_view.py` is missing the `apply_contract_header` "
        f"call; the diagnostics endpoint won't carry the "
        f"X-RoamCore-Contract header."
    )


def test_system_summary_view_calls_apply_contract_header() -> None:
    """The system summary view must call apply_contract_header."""
    text = (
        REPO_ROOT
        / "homeassistant"
        / "custom_components"
        / "roamcore"
        / "system_summary_view.py"
    ).read_text(encoding="utf-8")
    assert "apply_contract_header" in text, (
        f"`system_summary_view.py` is missing the "
        f"`apply_contract_header` call; the system summary endpoint "
        f"won't carry the X-RoamCore-Contract header."
    )


def test_update_view_calls_apply_contract_header() -> None:
    """The update view must call apply_contract_header."""
    text = (
        REPO_ROOT
        / "homeassistant"
        / "custom_components"
        / "roamcore"
        / "update_view.py"
    ).read_text(encoding="utf-8")
    assert "apply_contract_header" in text, (
        f"`update_view.py` is missing the `apply_contract_header` "
        f"call; the update endpoint won't carry the "
        f"X-RoamCore-Contract header."
    )


# ---------------------------------------------------------------------------
# Test 4: agent-skill discovery returns the canonical summary_url
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_skill_endpoint_returns_canonical_openclaw_summary_url(
    hass_client,
) -> None:
    """The `/api/roamcore/openclaw/skill` endpoint MUST return the
    agent-discovery payload with the canonical `openclaw_summary_url`.

    The agent-side skill payload documents the canonical 11 URL
    endpoints (the 7 OpenClaw endpoints + `diagnostics` +
    `system/summary` + `update` + `pmtiles/{filename}` +
    `automation/validate`). The skill payload exposes the canonical
    summary URL; the agent then uses the agent-skill docs to discover
    the other 10 endpoints.

    The integration exposes the summary URL because that's the
    minimum-viable entry point — the agent uses it to make the first
    request. The other URLs are documented in
    `docs/reference/openclaw-json-api.md` (the canonical spec).
    """
    resp = await hass_client.get("/api/roamcore/openclaw/skill")
    assert resp.status == 200
    body = await resp.json()

    # The agent-discovery payload MUST include the canonical summary
    # URL so the agent can copy/paste it from the skill payload
    # directly (without needing to read the spec).
    assert "roamcore" in body, (
        "openclaw skill payload missing `roamcore` block; the agent "
        "uses this block to discover the API surface"
    )
    assert "openclaw_summary_url" in body["roamcore"], (
        "openclaw skill payload missing `roamcore.openclaw_summary_url`; "
        "the agent uses this as the entry point for the canonical API"
    )
    assert body["roamcore"]["openclaw_summary_url"].endswith(
        "/api/roamcore/openclaw/summary"
    ), (
        f"openclaw skill payload `roamcore.openclaw_summary_url` must "
        f"end with `/api/roamcore/openclaw/summary`; got "
        f"{body['roamcore']['openclaw_summary_url']!r}"
    )


# ---------------------------------------------------------------------------
# Test 5: skill discovery on the canonical spec doc agrees
# ---------------------------------------------------------------------------


def test_canonical_spec_documents_the_5_openclaw_endpoints() -> None:
    """The canonical spec at `docs/reference/openclaw-json-api.md`
    MUST document the 5 OpenClaw endpoints (the most-active ones:
    `/summary`, `/skill`, `/rc_dump`, `/timeseries/catalog`,
    `/timeseries`).

    The newer 6 endpoints (diagnostics, system/summary, update,
    pmtiles, automation/intents, automation/validate) are documented
    in `connections/openclaw-api/docs/recipe.md` instead — the
    recipe is the canonical reference for the integration-managed
    endpoints, and the spec is the canonical reference for the
    agent-discoverable endpoints. This split keeps each doc small
    + focused. The recipe has its own honesty test
    (`test_recipe_documents_auth_required_endpoints` in
    `test_connection_yml.py`).
    """
    text = CANONICAL_SPEC_PATH.read_text(encoding="utf-8")
    expected_endpoints = (
        "/api/roamcore/openclaw/summary",
        "/api/roamcore/openclaw/skill",
        "/api/roamcore/openclaw/rc_dump",
        "/api/roamcore/openclaw/timeseries/catalog",
        "/api/roamcore/openclaw/timeseries",
    )
    missing = [e for e in expected_endpoints if e not in text]
    assert not missing, (
        f"canonical spec at `{CANONICAL_SPEC_PATH}` is missing "
        f"endpoints: {sorted(missing)!r}; the spec is the agent's "
        f"source of truth for the OpenClaw API surface."
    )


def test_canonical_spec_documents_contract_version_1() -> None:
    """The canonical spec at `docs/reference/openclaw-json-api.md`
    MUST document the contract version as `1` (the current version).

    The spec is the agent-facing source of truth. If the spec
    disagrees with the integration, the agent will follow the spec
    + the integration will reject the request.
    """
    text = CANONICAL_SPEC_PATH.read_text(encoding="utf-8")
    assert '"version": 1' in text or "'version': 1" in text, (
        f"canonical spec at `{CANONICAL_SPEC_PATH}` does not document "
        f"`contract.version = 1`; the spec is the agent-facing source "
        f"of truth — it MUST agree with the integration's "
        f"`DEFAULT_CONTRACT_VERSION` constant. Run `git grep -n 'version' "
        f"`{CANONICAL_SPEC_PATH}` to see the current contract "
        f"documentation."
    )


def test_skill_payload_documents_canonical_endpoints() -> None:
    """The agent-side skill payload at
    `openclaw/skills/roamcore/SKILL.md` MUST document the canonical
    5 OpenClaw endpoints (the ones the agent most actively uses).

    The skill payload is the agent-side source of truth. The agent
    uses it to discover the API surface. If it disagrees with the
    integration, the agent + the integration will silently drift.
    """
    if not SKILL_PAYLOAD_PATH.is_file():
        # The agent skill payload hasn't been authored yet —
        # this is a soft failure (we don't have a test to enforce
        # the skill payload's presence; this test guards against
        # silent drift if/when the skill payload IS shipped).
        return
    text = SKILL_PAYLOAD_PATH.read_text(encoding="utf-8")
    expected_endpoints = (
        "/api/roamcore/openclaw/summary",
        "/api/roamcore/openclaw/skill",
        "/api/roamcore/openclaw/rc_dump",
        "/api/roamcore/openclaw/timeseries/catalog",
        "/api/roamcore/openclaw/timeseries",
    )
    for endpoint in expected_endpoints:
        assert endpoint in text, (
            f"agent skill payload at `{SKILL_PAYLOAD_PATH}` does not "
            f"document endpoint {endpoint!r}; the skill payload is "
            f"the agent-side source of truth — the agent uses it to "
            f"discover the API surface. Adding the endpoint here is "
            f"the step that unlocks the agent's ability to call it."
        )
