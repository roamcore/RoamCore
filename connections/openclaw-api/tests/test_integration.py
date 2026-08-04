"""Real pytest integration tests for the 13 RoamCore OpenClaw API endpoints.

These tests are the "tier-a-is-honest" proof: they hit a real Home
Assistant instance with the RoamCore custom component loaded (the
canonical HACS-path integration at
`homeassistant/custom_components/roamcore/`, NOT the legacy
`homeassistant/custom_components/roamcore_openclaw_api/`) and send
real HTTP requests through the registered `HomeAssistantView`s.

Why this exists (the tier-a-but-flagged honesty note in
`connections/openclaw-api/connection.yml`):

  - The slice was originally tagged `tier-a-but-flagged` because the
    only "integration test" we had was a curl smoketest at
    `homeassistant/tools/openclaw_api_smoketest.sh`. That smoketest
    only checks that the endpoint returns 200 + JSON; it doesn't
    exercise the actual view code, the option-gating, the
    upgrade paths, the auth-required path, or the dispatcher logic
    in the diagnostics/system_summary/update views.

  - These tests are the real test rig: a real `HomeAssistant` instance
    (the `hass` fixture in `conftest.py`), a real `aiohttp.test_utils.
    TestClient` (the `hass_client` fixture), and real HTTP requests
    through the registered views. There is no mocking layer between
    the test and the production code.

The 13 endpoints break down into 11 unique URL routes + 2 service/direct
function surfaces:

  OpenClaw namespace (the 7 endpoints spec'd by the slice):
    1. GET  /api/roamcore/openclaw/summary
    2. GET  /api/roamcore/openclaw/skill
    3. GET  /api/roamcore/openclaw/rc_dump
    4. GET  /api/roamcore/openclaw/timeseries/catalog
    5. GET  /api/roamcore/openclaw/timeseries
    6. GET  /api/roamcore/openclaw/automation/intents
    7. POST /api/roamcore/openclaw/automation/validate
       (POST on a separate route, /automation/validate, which is the
       same view as /automation/intents — the dispatcher dispatches
       on the HTTP method)

  Diagnostics + system surfaces (the 3 endpoints spec'd by the slice):
    8. GET  /api/roamcore/diagnostics
    9. GET  /api/roamcore/system/summary
   10. GET  /api/roamcore/update

  Static / service surfaces (the 3 endpoints spec'd by the slice):
   11. GET  /api/roamcore/pmtiles/{filename}
   12. POST serve {action_id, args, reason} via roamcore.action_execute
       (the agent actions gateway — exercised via direct service call,
       not a URL route)
   13. POST export_support_bundle(...) — called directly, not via a URL
       route (the recipe's support-bundle export path).

The tests are organized by group (OpenClaw / diagnostics / static /
services) so a failure immediately tells the operator which group
regressed. Every test asserts the contract version explicitly (the
contract is the whole point of the API) and surfaces the actual
entity state on failure (plain-English errors, per doctrine).

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/openclaw-api/tests/test_integration.py -v
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict

import pytest

# Lazy skip-marker: applied to every test below so the suite degrades
# gracefully on hosts without aiohttp + homeassistant (the picker /
# CI runners that only run the manifest-honesty chain). Same gate as
# conftest.py uses for the fixtures.
try:
    import aiohttp  # noqa: F401
    _AIOHTTP_AVAILABLE = True
except ModuleNotFoundError:
    _AIOHTTP_AVAILABLE = False

requires_aiohttp = pytest.mark.skipif(
    not _AIOHTTP_AVAILABLE,
    reason="aiohttp + homeassistant not installed; run on a dev box with "
           "`pip install -r connections/openclaw-api/tests/requirements.txt` "
           "and the first-party homeassistant package",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_json(client, path: str) -> Dict[str, Any]:
    """GET `path` and return the parsed JSON body, with plain-English
    failure messages that surface the actual state for diagnostic."""
    resp = await client.get(path)
    assert resp.status == 200, (
        f"GET {path} returned {resp.status} (expected 200); "
        f"body={await resp.text()!r}"
    )
    body = await resp.json()
    assert isinstance(body, dict), (
        f"GET {path} body is not a dict (got {type(body).__name__}); "
        f"the OpenClaw API contract requires a top-level JSON object"
    )
    return body


async def _post_json(client, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """POST `payload` (JSON) to `path` and return the parsed JSON body."""
    resp = await client.post(path, json=payload)
    assert resp.status == 200, (
        f"POST {path} returned {resp.status} (expected 200); "
        f"body={await resp.text()!r}"
    )
    body = await resp.json()
    assert isinstance(body, dict), (
        f"POST {path} body is not a dict (got {type(body).__name__})"
    )
    return body


# ---------------------------------------------------------------------------
# The 7 OpenClaw endpoints
# ---------------------------------------------------------------------------


@requires_aiohttp
@pytest.mark.asyncio
async def test_openclaw_summary_returns_contract_v1_and_graceful_nulls(
    hass_client,
) -> None:
    """Endpoint #1: GET /api/roamcore/openclaw/summary.

    Contract assertion: `contract.version == 1` + the four contract
    groups (`power`, `map`, `level`, `mode`) are present as top-level
    keys + `debug.entities` is present. We do NOT assert specific
    scalar values here because the test rig has no rc_* entities —
    the contract is "all fields are null when entities are missing",
    which is the whole point of the rc_* contract layer + the
    graceful-degradation design.
    """
    body = await _get_json(hass_client, "/api/roamcore/openclaw/summary")

    # Contract version MUST be exposed + must be the canonical "1".
    assert body["contract"] == {
        "name": "roamcore_openclaw_summary",
        "version": 1,
    }, (
        "openclaw summary contract version mismatch; the canonical "
        "spec at `docs/reference/openclaw-json-api.md` documents "
        "contract.name='roamcore_openclaw_summary' + version=1. "
        "A bump here requires bumping the snapshot in `__init__.py` "
        "+ updating the §8.5 contract-version-bump-notify guard "
        "automation in `connections/openclaw-api/docs/recipe.md`."
    )

    # The four contract groups must be present.
    for group in ("power", "map", "level", "mode"):
        assert group in body, (
            f"openclaw summary missing required contract group {group!r}; "
            f"the full top-level keys were {sorted(body.keys())!r}"
        )

    # The debug block is the operator-facing affordance for "what rc_*
    # entities exist right now"; must be present even when the rig has
    # zero rc_* entities.
    assert "debug" in body, "openclaw summary missing the `debug` block"
    assert "entities" in body["debug"], "openclaw summary debug block missing `entities`"

    # Every numeric / boolean field MUST be null when the source entity
    # is missing — that's the graceful-degradation contract. If any
    # of these are non-null, the rc_* entities are leaking and the test
    # rig is wrong (entities from a previous test leaked).
    power = body["power"]
    for field in ("battery_soc_pct", "solar_power_w", "load_power_w",
                  "ac_in_power_w", "ac_out_power_w"):
        assert power[field] is None, (
            f"openclaw summary power.{field} should be null when "
            f"source entity is missing; got {power[field]!r} "
            f"(the test rig has no rc_* entities — this is a leak "
            f"from a previous test or a regression in the view's "
            f"`_state_float` helper)"
        )
    assert power["shore_connected"] is None, (
        f"openclaw summary power.shore_connected should be null when "
        f"source entity is missing; got {power[field]!r}"
    )
    assert power["inverter_status"] is None, (
        f"openclaw summary power.inverter_status should be null when "
        f"source entity is missing; got {power['inverter_status']!r}"
    )


@requires_aiohttp
@pytest.mark.asyncio
async def test_openclaw_skill_returns_agent_discovery_payload(hass_client) -> None:
    """Endpoint #2: GET /api/roamcore/openclaw/skill.

    Contract assertion: `contract.version == 1` + the
    agent-discovery payload includes the absolute summary URL +
    `requires_auth` (a boolean) + the summary contract metadata.
    """
    body = await _get_json(hass_client, "/api/roamcore/openclaw/skill")

    assert body["contract"] == {
        "name": "roamcore_openclaw_skill",
        "version": 1,
    }, (
        "openclaw skill contract version mismatch; the canonical "
        "spec at `docs/reference/openclaw-json-api.md` and the "
        "agent install guide at `docs/howto/openclaw-roamcore-skill.md` "
        "both pin the contract at version 1."
    )

    # The agent-discovery payload includes the absolute summary URL
    # so the agent can copy/paste it.
    assert "roamcore" in body, "openclaw skill payload missing `roamcore` block"
    assert (
        body["roamcore"]["openclaw_summary_url"].endswith(
            "/api/roamcore/openclaw/summary"
        )
    ), (
        "openclaw skill payload `roamcore.openclaw_summary_url` must "
        "end with `/api/roamcore/openclaw/summary`; got "
        f"{body['roamcore']['openclaw_summary_url']!r}"
    )

    # The auth-required flag MUST be present (the agent config flow
    # reads it to decide whether to send a Bearer token).
    assert "requires_auth" in body["roamcore"], (
        "openclaw skill payload missing `roamcore.requires_auth`; "
        "the agent needs this to know whether to send a Bearer token"
    )
    assert isinstance(body["roamcore"]["requires_auth"], bool), (
        f"`roamcore.requires_auth` must be a bool; got "
        f"{type(body['roamcore']['requires_auth']).__name__}"
    )

    # The summary contract metadata is mirrored so the agent can
    # assert the contract version without making a separate call.
    assert body["roamcore"]["summary_contract"] == {
        "name": "roamcore_openclaw_summary",
        "version": 1,
    }, (
        "openclaw skill payload must mirror the summary contract "
        "metadata; the canonical spec is "
        "{name: 'roamcore_openclaw_summary', version: 1}"
    )

    # The user_instructions list is the operator-facing copy.
    assert "user_instructions" in body, (
        "openclaw skill payload missing `user_instructions`; this is "
        "the operator-facing copy that walks the agent through the "
        "config flow"
    )


@requires_aiohttp
@pytest.mark.asyncio
async def test_openclaw_rc_dump_returns_rc_prefix_filter(hass_client) -> None:
    """Endpoint #3: GET /api/roamcore/openclaw/rc_dump.

    Contract assertion: only `rc_*` entities are returned (the
    contract layer guarantees the API is vendor-neutral; the rc_dump
    endpoint is the agent-side introspection that proves it). The
    test rig has no rc_* entities, so the dump is empty — but the
    `count` + `entities` keys must be present.
    """
    body = await _get_json(hass_client, "/api/roamcore/openclaw/rc_dump")

    assert body["contract"] == {
        "name": "roamcore_openclaw_rc_dump",
        "version": 1,
    }, (
        "openclaw rc_dump contract version mismatch; the canonical "
        "spec at `docs/reference/openclaw-json-api.md` documents "
        "contract.name='roamcore_openclaw_rc_dump' + version=1."
    )
    assert "count" in body, "openclaw rc_dump missing `count` field"
    assert isinstance(body["count"], int), (
        f"openclaw rc_dump `count` must be an int; "
        f"got {type(body['count']).__name__}"
    )
    assert "entities" in body, "openclaw rc_dump missing `entities` field"
    assert isinstance(body["entities"], dict), (
        f"openclaw rc_dump `entities` must be a dict; "
        f"got {type(body['entities']).__name__}"
    )

    # Belt-and-braces: EVERY entity in the dump must match the `.rc_*`
    # pattern. The spec is `rc_*` — no vendor prefixes, no other
    # domains. This is the trust-but-verify check that keeps the
    # rc_dump endpoint from leaking vendor entity IDs into the
    # agent's working memory (the §8.3 rc-dump-only-includes-rc-prefix
    # guard in the recipe).
    for entity_id in body["entities"]:
        assert ".rc_" in entity_id, (
            f"openclaw rc_dump leaked non-rc_ entity id {entity_id!r}; "
            f"the rc_* prefix filter is the single hardest contract "
            f"guarantee of the endpoint (per "
            f"docs/reference/openclaw-json-api.md + the §8.3 "
            f"rc-dump-only-includes-rc-prefix guard in "
            f"connections/openclaw-api/docs/recipe.md)"
        )


@requires_aiohttp
@pytest.mark.asyncio
async def test_openclaw_timeseries_catalog_returns_discovery_keys(hass_client) -> None:
    """Endpoint #4: GET /api/roamcore/openclaw/timeseries/catalog.

    Contract assertion: `keys` is a dict of catalog entries. Each
    entry has `entity_id` + `kind` (the agent uses this to know
    which keys to request from the timeseries endpoint). The test
    rig has no rc_* entities, so each `state` will be null — but
    the catalog metadata must still be present.
    """
    body = await _get_json(hass_client, "/api/roamcore/openclaw/timeseries/catalog")

    assert body["contract"] == {
        "name": "roamcore_openclaw_timeseries_catalog",
        "version": 1,
    }, (
        "openclaw timeseries/catalog contract version mismatch; the "
        "canonical spec at `docs/reference/openclaw-json-api.md` "
        "documents contract.name='roamcore_openclaw_timeseries_catalog' + "
        "version=1."
    )
    assert "keys" in body, (
        "openclaw timeseries/catalog missing `keys` field; the agent "
        "uses this to discover which keys it can request from /timeseries"
    )
    assert "count" in body, (
        "openclaw timeseries/catalog missing `count` field; the agent "
        "uses this to know how many keys are available"
    )

    # The TIMESERIES_CATALOG constant in the integration has a curated
    # set of keys. The catalog endpoint MUST expose at least the
    # 13 base keys (power.battery_soc_pct + power.solar_power_w + ...
    # + map.accuracy_m) — the canonical agent contract. We don't
    # assert == 13 because future versions may add keys; we assert
    # >= 13 because pruning them would break agents.
    expected_keys = {
        "power.battery_soc_pct",
        "power.solar_power_w",
        "power.load_power_w",
        "power.ac_in_power_w",
        "power.ac_out_power_w",
        "power.shore_connected",
        "level.pitch_deg",
        "level.roll_deg",
        "level.is_level",
        "map.lat",
        "map.lon",
        "map.accuracy_m",
    }
    assert expected_keys <= set(body["keys"].keys()), (
        "openclaw timeseries/catalog missing required keys; the "
        "agent contract documents at least the 13 base keys "
        f"({sorted(expected_keys)!r}); got "
        f"{sorted(body['keys'].keys())!r}"
    )

    # Each catalog entry must have `entity_id` + `kind` (the agent
    # uses these to validate the request).
    for key, meta in body["keys"].items():
        assert "entity_id" in meta, (
            f"openclaw timeseries/catalog entry {key!r} missing "
            f"`entity_id` field"
        )
        assert "kind" in meta, (
            f"openclaw timeseries/catalog entry {key!r} missing "
            f"`kind` field"
        )
        assert meta["kind"] in ("number", "bool"), (
            f"openclaw timeseries/catalog entry {key!r} has unknown "
            f"`kind` {meta['kind']!r}; expected 'number' or 'bool'"
        )


@requires_aiohttp
@pytest.mark.asyncio
async def test_openclaw_timeseries_returns_series_and_events(hass_client) -> None:
    """Endpoint #5: GET /api/roamcore/openclaw/timeseries.

    Contract assertion: `keys` is a comma-separated list of catalog
    keys; the response is `{series: {key: [[t, value], ...]}, events:
    {key: [[t, 0|1], ...]}}` — both numeric series (for `number` kind)
    and boolean events (for `bool` kind). The test rig has no rc_*
    entities, so the series values are null but the shape is correct.
    """
    body = await _get_json(
        hass_client,
        "/api/roamcore/openclaw/timeseries?keys="
        "power.battery_soc_pct,power.solar_power_w",
    )

    # The contract is the same family as the catalog endpoint.
    assert body["contract"]["name"] == "roamcore_openclaw_timeseries"
    assert body["contract"]["version"] == 1

    # The response MUST include `series` + `events` as separate dicts
    # (the agent uses `series` for numeric keys + `events` for boolean
    # keys — the separation is the cleanest way to handle the
    # type-fork without losing precision).
    assert "series" in body, (
        "openclaw timeseries missing `series` field; the agent "
        "expects numeric series as `series[key] = [[t_epoch, value], ...]`"
    )
    assert "events" in body, (
        "openclaw timeseries missing `events` field; the agent "
        "expects boolean events as `events[key] = [[t_epoch, 0|1], ...]`"
    )

    # Window + resolution must be echoed back (the agent uses these
    # to verify the request was honored).
    assert "window_sec" in body
    assert "resolution_sec" in body
    assert isinstance(body["window_sec"], int)
    assert isinstance(body["resolution_sec"], int)

    # The requested keys MUST be in the response (even when their
    # source entities are missing — the agent relies on the key
    # being present so it can iterate without missing-field checks).
    for key in ("power.battery_soc_pct", "power.solar_power_w"):
        assert key in body["series"], (
            f"openclaw timeseries response missing requested key "
            f"{key!r} in `series`; the agent skips silently when "
            f"keys disappear from the response, which is a common "
            f"downstream bug"
        )

    # The series for numeric keys must be lists of [t_epoch, value]
    # pairs — the agent's chart code expects this exact shape.
    for key, points in body["series"].items():
        assert isinstance(points, list), (
            f"openclaw timeseries series[{key!r}] must be a list; "
            f"got {type(points).__name__}"
        )
        for point in points:
            assert isinstance(point, list) and len(point) == 2, (
                f"openclaw timeseries series point for {key!r} "
                f"malformed: expected [t, value], got {point!r}"
            )
            assert isinstance(point[0], (int, float)), (
                f"openclaw timeseries series point t-value for "
                f"{key!r} must be numeric; got {type(point[0]).__name__}"
            )

    # Events must be lists of [t_epoch, 0|1] transitions.
    for key, points in body["events"].items():
        for point in points:
            assert isinstance(point, list) and len(point) == 2, (
                f"openclaw timeseries events point for {key!r} "
                f"malformed: expected [t, 0|1], got {point!r}"
            )
            assert point[1] in (0, 1), (
                f"openclaw timeseries events value for {key!r} "
                f"must be 0 or 1; got {point[1]!r}"
            )


@requires_aiohttp
@pytest.mark.asyncio
async def test_openclaw_automation_intents_get_returns_schema(hass_client) -> None:
    """Endpoint #6: GET /api/roamcore/openclaw/automation/intents.

    Contract assertion: `supported_intents` is a dict of intent types
    + their params schema + the `validate` block points at the
    /automation/validate endpoint with the right payload shape.
    """
    body = await _get_json(
        hass_client, "/api/roamcore/openclaw/automation/intents"
    )

    # The contract is owned by the `automation_intents` module.
    assert body["contract"]["name"] == "roamcore_automation_intents"
    assert body["contract"]["version"] == 1

    assert "supported_intents" in body, (
        "openclaw automation/intents missing `supported_intents` "
        "field; the agent reads this to discover which intents "
        "it can construct"
    )
    assert "set_mode" in body["supported_intents"], (
        "openclaw automation/intents missing `set_mode` intent — "
        "this is the canonical intent (the only one the LLM-side "
        "agent constructs today)"
    )
    assert "apply_mode" in body["supported_intents"], (
        "openclaw automation/intents missing `apply_mode` intent"
    )

    # The validator hint block points at the /validate endpoint.
    assert "validate" in body
    assert body["validate"]["method"] == "POST"
    assert body["validate"]["url"] == "/api/roamcore/openclaw/automation/validate"
    assert body["validate"]["payload_shape"] == {"type": "<intent_type>", "params": {}}


@requires_aiohttp
@pytest.mark.asyncio
async def test_openclaw_automation_validate_post_accepts_valid_intent(
    hass_client,
) -> None:
    """Endpoint #7: POST /api/roamcore/openclaw/automation/validate.

    Contract assertion: valid intents return `{ok: true, normalized: ...}`.
    Invalid intents return `{ok: false, error: ...}` with a stable
    machine-readable error string. The `error` field is the operator-
    facing surface for "what was wrong with the intent you sent?".
    """
    # Valid intent (set_mode to 'travel')
    body = await _post_json(
        hass_client,
        "/api/roamcore/openclaw/automation/validate",
        {"type": "set_mode", "params": {"mode": "travel"}},
    )
    assert body["ok"] is True, (
        f"openclaw automation/validate should accept set_mode "
        f"'travel' as valid; got {body!r}"
    )
    assert body["normalized"] == {
        "type": "set_mode",
        "params": {"mode": "travel"},
    }, (
        f"openclaw automation/validate normalized the 'travel' "
        f"mode incorrectly; expected lowercase normalization; "
        f"got {body.get('normalized')!r}"
    )

    # Case-insensitive (the agent might write "Travel" not "travel")
    body = await _post_json(
        hass_client,
        "/api/roamcore/openclaw/automation/validate",
        {"type": "set_mode", "params": {"mode": "CAMP"}},
    )
    assert body["ok"] is True
    assert body["normalized"]["params"]["mode"] == "camp", (
        f"openclaw automation/validate should normalize mode "
        f"to lowercase; got {body['normalized']['params']['mode']!r}"
    )

    # Invalid intent (unsupported mode)
    body = await _post_json(
        hass_client,
        "/api/roamcore/openclaw/automation/validate",
        {"type": "set_mode", "params": {"mode": "invalid_mode"}},
    )
    assert body["ok"] is False
    assert body["error"] == "invalid_mode", (
        f"openclaw automation/validate should return 'invalid_mode' "
        f"for an unsupported mode; got {body['error']!r} "
        f"(the agent uses this string to surface the error to the user)"
    )

    # Invalid intent (unsupported type)
    body = await _post_json(
        hass_client,
        "/api/roamcore/openclaw/automation/validate",
        {"type": "do_something_unsupported", "params": {}},
    )
    assert body["ok"] is False
    assert body["error"] == "unsupported_type", (
        f"openclaw automation/validate should return "
        f"'unsupported_type' for an unknown intent type; got "
        f"{body['error']!r}"
    )

    # Malformed payload (not even a dict)
    body = await _post_json(
        hass_client,
        "/api/roamcore/openclaw/automation/validate",
        {"type": "", "params": None},
    )
    assert body["ok"] is False
    assert body["error"] == "missing_type", (
        f"openclaw automation/validate should return 'missing_type' "
        f"for an empty type; got {body['error']!r}"
    )


@requires_aiohttp
@pytest.mark.asyncio
async def test_openclaw_automation_validate_get_returns_use_post_hint(
    hass_client,
) -> None:
    """Endpoint #7b: GET /api/roamcore/openclaw/automation/validate.

    The /validate endpoint is POST-only; a GET returns a clear
    `use_post` error + a hint pointing at /intents. This is the
    "Plain-English errors" doctrine in action.
    """
    body = await _get_json(
        hass_client, "/api/roamcore/openclaw/automation/validate"
    )
    assert body["ok"] is False
    assert body["error"] == "use_post", (
        f"openclaw automation/validate GET should return 'use_post' "
        f"error; got {body['error']!r}"
    )
    assert "POST" in body["hint"], (
        f"openclaw automation/validate GET hint should mention "
        f"POST; got {body['hint']!r}"
    )
    assert "/intents" in body["hint"], (
        f"openclaw automation/validate GET hint should point at "
        f"/automation/intents; got {body['hint']!r}"
    )


# ---------------------------------------------------------------------------
# The 3 diagnostics + system endpoints
# ---------------------------------------------------------------------------


@requires_aiohttp
@pytest.mark.asyncio
async def test_diagnostics_returns_contract_v1_and_key_entity_snapshots(
    hass_auth_client,
) -> None:
    """Endpoint #8: GET /api/roamcore/diagnostics (requires auth).

    Contract assertion: `contract.version == 1` + the response
    includes the HA `hass` block + the RoamCore component manifest
    version + the canonical endpoint URLs the recipe cross-references.

    The diagnostics endpoint hardcodes `requires_auth = True` (it
    leaks HA version + key-entity state which could guide an attacker
    to a known-vulnerable surface; the OpenClaw endpoints don't
    require auth because the spec is intentionally public-on-LAN).
    """
    body = await _get_json(hass_auth_client, "/api/roamcore/diagnostics")

    assert body["contract"] == {
        "name": "roamcore_diagnostics",
        "version": 1,
    }
    assert "hass" in body
    assert "version" in body["hass"]
    assert "roamcore" in body
    assert "domain" in body["roamcore"]
    assert body["roamcore"]["domain"] == "roamcore"
    assert "entities" in body
    assert "key" in body["entities"]

    # The endpoint URLs the recipe cross-references must be present
    # so the operator can copy/paste them from the diagnostics view.
    assert "endpoints" in body
    assert (
        body["endpoints"]["openclaw_summary"].endswith(
            "/api/roamcore/openclaw/summary"
        )
    )
    assert (
        body["endpoints"]["openclaw_skill"].endswith(
            "/api/roamcore/openclaw/skill"
        )
    )
    assert (
        body["endpoints"]["openclaw_rc_dump"].endswith(
            "/api/roamcore/openclaw/rc_dump"
        )
    )


@requires_aiohttp
@pytest.mark.asyncio
async def test_system_summary_returns_overall_status(hass_auth_client) -> None:
    """Endpoint #9: GET /api/roamcore/system/summary (requires auth).

    Contract assertion: `contract.version == 1` + the response
    includes `overall` (the deterministic status: ok/warn/error) +
    `setup` (the four-readiness chip block) + `power_backend` +
    `network` + `roamcore.component_version` (mirrored from the
    integration manifest).
    """
    body = await _get_json(hass_auth_client, "/api/roamcore/system/summary")

    assert body["contract"] == {
        "name": "roamcore_system_summary",
        "version": 1,
    }
    assert body["overall"] in ("ok", "warn", "error"), (
        f"system/summary overall must be one of ok/warn/error; got "
        f"{body['overall']!r}"
    )
    assert "setup" in body
    assert "ready" in body["setup"]
    assert "power_backend" in body
    assert "network" in body
    assert "roamcore" in body
    assert "component_version" in body["roamcore"]


@requires_aiohttp
@pytest.mark.asyncio
async def test_update_returns_graceful_payload(hass_auth_client) -> None:
    """Endpoint #10: GET /api/roamcore/update (requires auth).

    Contract assertion: `contract.version == 1` + the response
    includes the cached release info (the endpoint is rate-limited
    via a 60s in-memory cache, so the first call may make a real
    HTTPS request to api.github.com — if that fails due to network,
    the endpoint MUST still return a 200 with `latest.ok = false`
    and a descriptive `error` field, NOT crash or 5xx).

    This test is network-resilient: it accepts either `latest.ok=true`
    (release fetched successfully) or `latest.ok=false` (network down
    in the test rig). The point is the contract — the endpoint never
    crashes.
    """
    resp = await hass_auth_client.get("/api/roamcore/update")
    assert resp.status == 200, (
        f"GET /api/roamcore/update returned {resp.status}; "
        f"body={await resp.text()!r}"
    )
    body = await resp.json()
    assert body["contract"] == {
        "name": "roamcore_update",
        "version": 1,
    }
    assert "installed" in body, (
        "update endpoint missing `installed` block; the dashboard "
        "uses this to compare installed vs latest"
    )
    assert "latest" in body, (
        "update endpoint missing `latest` block; the dashboard "
        "uses this to show the operator what version is available"
    )
    assert "backup_support" in body, (
        "update endpoint missing `backup_support` block; the "
        "dashboard uses this to know whether `backup.create` + "
        "`hassio.backup_full` are available before offering an update"
    )


# ---------------------------------------------------------------------------
# The 3 static / service endpoints
# ---------------------------------------------------------------------------


@requires_aiohttp
@pytest.mark.asyncio
async def test_pmtiles_returns_404_for_missing_file(hass_auth_client) -> None:
    """Endpoint #11: GET /api/roamcore/pmtiles/{filename} (requires auth).

    The pmtiles endpoint serves `.pmtiles` files from
    `<config>/www/roamcore/pmtiles/` with HTTP Range support. A
    request for a non-existent file should return 404 (the standard
    HTTP semantics for a missing file). The endpoint also has
    defensive guards against path traversal (`/`, `\\`, `..` in
    the filename) — but those are security guards, not contract
    behavior, so we don't test them here.
    """
    resp = await hass_auth_client.get("/api/roamcore/pmtiles/missing.pmtiles")
    assert resp.status == 404, (
        f"GET /api/roamcore/pmtiles/missing.pmtiles should return 404 "
        f"for a non-existent file; got {resp.status} "
        f"(the agent uses this endpoint to fetch offline map tiles; "
        f"a 404 is the correct failure mode for a missing tile)"
    )


@requires_aiohttp
@pytest.mark.asyncio
async def test_pmtiles_rejects_non_pmtiles_extension(hass_auth_client) -> None:
    """Endpoint #11b: GET /api/roamcore/pmtiles/{filename} rejects
    non-`.pmtiles` extensions — the defensive guard against an
    agent probing for arbitrary files under the config dir.
    """
    resp = await hass_auth_client.get("/api/roamcore/pmtiles/secret.txt")
    assert resp.status == 404, (
        f"GET /api/roamcore/pmtiles/secret.txt should return 404 "
        f"(the .pmtiles extension guard); got {resp.status}"
    )


@requires_aiohttp
@pytest.mark.asyncio
async def test_action_execute_service_is_registered_and_default_denies(
    hass, hass_client
) -> None:
    """Endpoint #12: the agent actions gateway.

    The agent actions gateway is exposed via the `roamcore.action_execute`
    HA service (NOT a URL route — services are dispatched via the
    HA websocket + REST API; the agent integration uses the REST
    path). We test the service contract directly.

    Default-deny: the `input_boolean.rc_agent_actions_enabled` helper
    must be ON for any action to execute. The test rig has no helpers
    + no entity means the default is `off`, so the service MUST
    produce an audit-log record with `result.ok=false` and an error
    mentioning the kill switch.
    """
    # The service must be registered (if it's not, the test rig
    # couldn't talk to the agent actions gateway at all).
    assert hass.services.has_service("roamcore", "action_execute"), (
        "roamcore.action_execute service not registered; the agent "
        "actions gateway is wired in `homeassistant/custom_components/"
        "roamcore/__init__.py` via `hass.services.async_register(...)` "
        "— the call is missing or the test rig didn't fully set up "
        "the integration (the `hass` fixture in conftest.py asserts "
        "setup_ok=True before yielding)"
    )

    # Call the service. NOTE: we do NOT pass `return_response=True`
    # because the service is registered without `supports_response`
    # (the gateway is fire-and-forget for the agent — the audit log
    # is the source of truth, not a return value).
    await hass.services.async_call(
        "roamcore",
        "action_execute",
        {
            "action_id": "echo_mode",
            "args": {"value": "travel"},
            "reason": "test default-deny",
        },
        blocking=True,
    )

    # The service handler writes a record to the audit log + it's
    # the contract surface for "what just happened?". We assert the
    # audit log was created + it contains an entry with the expected
    # fail status.
    import json
    from pathlib import Path as _Path

    audit_log_path = _Path(hass.config.path(".roamcore", "agent_action_log.jsonl"))
    assert audit_log_path.is_file(), (
        f"agent actions gateway did not write the audit log at "
        f"{audit_log_path}; the service handler must always write "
        f"a record (even on denial) so the operator has a complete "
        f"trace of who-tried-what"
    )

    # Read the audit log (line-delimited JSON).
    lines = audit_log_path.read_text(encoding="utf-8").splitlines()
    matching = [
        json.loads(line)
        for line in lines
        if line.strip()
        and json.loads(line).get("action_id") == "echo_mode"
    ]
    assert matching, (
        f"agent actions gateway audit log does not contain an entry "
        f"for action_id='echo_mode'; the service must log every "
        f"call (the operator's audit log is the only proof the "
        f"service ran)"
    )
    last_record = matching[-1]
    assert last_record["result"]["ok"] is False, (
        f"agent actions gateway should default-deny when the kill "
        f"switch is off; got {last_record['result']!r}"
    )
    assert "disabled" in last_record["result"].get("error", "").lower(), (
        f"agent actions gateway audit log error should mention the "
        f"kill switch ('disabled'); got "
        f"{last_record['result'].get('error')!r}"
    )


@requires_aiohttp
@pytest.mark.asyncio
async def test_support_bundle_export_succeeds(hass) -> None:
    """Endpoint #13: the support bundle export.

    The support bundle export is exposed via
    `homeassistant/custom_components/roamcore/support_bundle.py`'s
    `export_support_bundle(hass, ...)` function (NOT a URL route —
    the operator triggers it via the dashboard button, which calls
    the function directly). We test it headlessly.

    The bundle MUST be created under `<config>/.roamcore/support/<ts>/`
    and contain the expected JSON files.
    """
    # Lazy import — the function is in the integration package.
    # The support_bundle module has a relative import
    # `from .openclaw_view import TIMESERIES_CATALOG`, so we need to
    # load the parent package (`roamcore`) first. The conftest's
    # `hass` fixture adds the test shim's custom_components dir to
    # sys.path, so `roamcore` is importable as a top-level package.
    import sys
    if "roamcore" not in sys.modules:
        import roamcore  # noqa: F401
    from roamcore.support_bundle import (  # type: ignore[import-not-found]
        export_support_bundle,
    )

    # The support bundle export is best-effort: it tries to read
    # install-info + the rc_* entity snapshots, but it's resilient
    # to missing data (the test rig has no rc_* entities, so the
    # snapshot block is empty).
    result = await export_support_bundle(hass, include_zip=False)
    assert "dir" in result, (
        f"export_support_bundle must return the bundle dir; got {result!r}"
    )

    bundle_dir = Path(result["dir"])
    assert bundle_dir.is_dir(), (
        f"support bundle dir was not created at {bundle_dir}; "
        f"the export_support_bundle function failed silently"
    )

    # The bundle MUST include the openclaw-summary.json snapshot —
    # that's the whole point of the export (the agent + the RoamCore
    # support team read this to diagnose issues).
    assert (bundle_dir / "openclaw-summary.json").is_file(), (
        "support bundle missing openclaw-summary.json; the "
        "RoamCore support team + the agent use this to diagnose "
        "issues without needing an interactive shell"
    )

    # The bundle MUST include the timeseries catalog snapshot.
    assert (bundle_dir / "openclaw-timeseries-catalog.json").is_file(), (
        "support bundle missing openclaw-timeseries-catalog.json"
    )

    # The bundle MUST include the setup-wizard-states snapshot.
    assert (bundle_dir / "setup-wizard-states.json").is_file(), (
        "support bundle missing setup-wizard-states.json"
    )

    # The bundle MUST include the bundle metadata (so the support
    # team knows which bundle they're looking at).
    assert (bundle_dir / "bundle-meta.json").is_file(), (
        "support bundle missing bundle-meta.json"
    )


# ---------------------------------------------------------------------------
# Cross-cutting: the API-disabled 404 guard
# ---------------------------------------------------------------------------


@requires_aiohttp
@pytest.mark.asyncio
async def test_openclaw_api_disabled_returns_404(hass, hass_client) -> None:
    """The §8.1 API-disabled-returns-404 guard.

    When `input_boolean.rc_openclaw_api_enabled` is OFF (per the
    helper package), the OpenClaw endpoints MUST return 404 — they
    MUST NOT leak whether the RoamCore integration is even installed.
    This is the "safe to leave this integration installed but keep
    the API off by default" guarantee in
    `homeassistant/custom_components/roamcore/openclaw_view.py`.
    """
    # Flip the toggle OFF via the config entry options.
    entry = hass.config_entries.async_entries("roamcore")[0]
    hass.config_entries.async_update_entry(
        entry,
        options={"openclaw_api_enabled": False},
    )

    try:
        resp = await hass_client.get("/api/roamcore/openclaw/summary")
        assert resp.status == 404, (
            f"openclaw summary should return 404 when the API is "
            f"disabled; got {resp.status} (the §8.1 404 guard is "
            f"the contract that makes the integration safe to leave "
            f"installed but disabled)"
        )
    finally:
        # Restore the toggle so subsequent tests see the enabled state.
        hass.config_entries.async_update_entry(
            entry,
            options={"openclaw_api_enabled": True},
        )
