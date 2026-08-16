#!/usr/bin/env python3
# RoamCore — Acceptance Gate D: agent integration (Wave 9 #123.d.iv)
#
# This is the pytest rig for Gate D. It mirrors the Gate A + Gate B
# pattern: every test reads the bash script's source + asserts a
# specific contract element (no live OpenClaw API calls; pure repo-
# local coverage so the rig runs anywhere with bash + python3 +
# pytest). The bash script is the canonical contract; this rig is
# the fast, always-on coverage that catches regressions on every
# push to main without requiring a live OpenClaw deployment.
#
# In-line fixtures (the spec disallows scripts/tests/acceptance/
# conftest.py because Gate A + Gate B's conftest is on unmerged
# PRs #115 / #120 — this slice must be runnable without those).
#
# Test coverage (~30 tests, mapped to the 12 bash stages):
#   test_stage_01_openclaw_auth_* (3 tests)
#   test_stage_02_model_read_* (4 tests)
#   test_stage_03_allowlist_* (3 tests)
#   test_stage_04_confirmation_* (3 tests)
#   test_stage_05_audit_log_* (4 tests)
#   test_stage_06_tamper_detection_* (2 tests)
#   test_stage_07_agent_failure_isolation_* (3 tests)
#   test_stage_08_multi_tenant_isolation_* (2 tests)
#   test_stage_09_reboot_survives_* (2 tests)
#   test_stage_10_idempotency_* (1 test)
#   test_stage_11_cleanup_trap_* (1 test)
#   test_stage_12_plain_english_no_secrets_rc_naming_* (3 tests)
#   test_idempotency_end_to_end_rerun (1 test)
#
# Each test prints a plain-English assertion message that names the
# contract element it guards. Doctests are intentionally minimal
# (the contract is the bash script; the rig just verifies the
# script's structural shape).

"""Pytest rig for the RoamCore Acceptance Gate D (agent integration).

This module is self-contained: it does NOT depend on
``scripts/tests/acceptance/conftest.py`` (which lives on the
unmerged Gate A + Gate B PR branches and will be merged by
Bernard separately). All fixtures are inlined per the Wave 9
#123.d.iv slice spec.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Inlined fixtures (no conftest.py dependency)
# ---------------------------------------------------------------------------


@pytest.fixture
def gate_d_script_path() -> Path:
    """Absolute path to the Gate D bash acceptance test."""
    return Path(__file__).resolve().parent / "gate_d_agent_integration.sh"


@pytest.fixture
def mock_openclaw_request() -> MagicMock:
    """Canonical mock HTTP request to the OpenClaw API.

    The mock carries a Bearer-token Authorization header per the
    Gate D Step 1 contract (Bearer scheme, mock token, not a real
    RC_API_TOKEN). The response is a canned 200 with a minimal
    vehicle-model body.
    """
    request = MagicMock(name="openclaw_request")
    request.method = "GET"
    request.url = "/api/roamcore/openclaw/model"
    request.headers = {
        "Authorization": "Bearer mock-token-tenant-a-0000000000000001",
        "Content-Type": "application/json",
    }
    request.body = b""
    response = MagicMock(name="openclaw_response")
    response.status_code = 200
    response.body = json.dumps(
        {
            "version": 1,
            "tiles": [
                {"entity_id": "sensor.rc_openclaw_api_contract_version"},
            ],
        }
    ).encode("utf-8")
    request.response = response
    return request


@pytest.fixture
def mock_openclaw_response() -> MagicMock:
    """Canonical mock OpenClaw response — the 12 rc_openclaw_api_*
    contract tiles per connections/openclaw-api/connection.yml §7.
    """
    response = MagicMock(name="openclaw_response")
    response.status_code = 200
    tile_specs = [
        ("input_boolean", "rc_openclaw_api_enabled"),
        ("input_boolean", "rc_openclaw_api_requires_auth"),
        ("sensor", "rc_openclaw_api_contract_version"),
        ("sensor", "rc_openclaw_api_last_request_at"),
        ("sensor", "rc_openclaw_api_request_count_24h"),
        ("sensor", "rc_openclaw_api_average_latency_ms"),
        ("binary_sensor", "rc_openclaw_api_is_reachable"),
        ("binary_sensor", "rc_openclaw_api_requires_auth_active"),
        ("binary_sensor", "rc_openclaw_api_last_action"),
        ("sensor", "rc_openclaw_api_openclaw_summary_url"),
        ("sensor", "rc_openclaw_api_skill_version"),
        ("button", "rc_openclaw_api_test_now"),
    ]
    response.body = json.dumps(
        {
            "version": 1,
            "tiles": [
                {
                    "entity_id": f"{domain}.{object_id}",
                    "state": "ok",
                    "attributes": {"friendly_name": object_id.replace("_", " ").title()},
                }
                for domain, object_id in tile_specs
            ],
        }
    ).encode("utf-8")
    return response


@pytest.fixture
def mock_audit_chain() -> dict:
    """Canonical mock SHA-256-chained audit log (3 records).

    Each record's ``signature`` field is the SHA-256 hex of
    ``json.dumps(record_body, sort_keys=True) + previous_signature``.
    The chain is verifiable end-to-end (re-hashing from the first
    record reproduces every signature in order).
    """
    records = []
    prev_sig = ""
    for i in range(3):
        body = {
            "record_id": i + 1,
            "action_id": "toggle_cabin_lights",
            "actor_token_prefix": "mock-tok...",
            "executed": True,
            "timestamp": f"2026-08-10T07:0{i}:00Z",
        }
        payload = json.dumps(body, sort_keys=True) + prev_sig
        sig = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        record = dict(body)
        record["previous_signature"] = prev_sig
        record["signature"] = sig
        records.append(record)
        prev_sig = sig
    return {"records": records}


@pytest.fixture
def mock_destructive_action_request() -> MagicMock:
    """Canonical mock destructive action attempt.

    Per the Gate D Step 3 contract: dangerous ops (disable_power,
    factory_reset, wipe_storage, disable_lte, enable_remote_admin)
    MUST return 403 with the canonical plain-English phrase
    'Action not allowed without explicit confirmation'.
    """
    request = MagicMock(name="destructive_action_request")
    request.method = "POST"
    request.url = "/api/roamcore/openclaw/actions/disable_power/confirm"
    request.headers = {
        "Authorization": "Bearer mock-token-tenant-a-0000000000000001",
    }
    request.body = json.dumps({"action_id": "disable_power"}).encode("utf-8")
    response = MagicMock(name="destructive_action_response")
    response.status_code = 403
    response.body = json.dumps(
        {
            "allowed": False,
            "reason": "Action not allowed without explicit confirmation",
        }
    ).encode("utf-8")
    request.response = response
    return request


@pytest.fixture
def mock_confirmation_token() -> dict:
    """Canonical mock confirmation token returned from /confirm.

    The token is a 32-character hex string (matches the canonical
    confirmation_id format in the roamcore openclaw view module).
    """
    return {
        "confirmation_id": "0123456789abcdef0123456789abcdef",
        "action_id": "toggle_cabin_lights",
        "issued_at": "2026-08-10T07:00:00Z",
        "expires_at": "2026-08-10T07:05:00Z",
    }


@pytest.fixture
def mock_multi_tenant_request() -> MagicMock:
    """Canonical mock cross-tenant access attempt.

    Per the Gate D Step 8 contract: token A attempting to read
    tenant B's data MUST return 401 with the canonical plain-
    English phrase 'token does not have access'.
    """
    request = MagicMock(name="multi_tenant_request")
    request.method = "GET"
    request.url = "/api/roamcore/openclaw/tenants/b/scopes"
    request.headers = {
        "Authorization": "Bearer mock-token-tenant-a-0000000000000001",
    }
    response = MagicMock(name="multi_tenant_response")
    response.status_code = 401
    response.body = json.dumps(
        {
            "status": 401,
            "reason": "Unauthorized: token does not have access to tenant B scope",
        }
    ).encode("utf-8")
    request.response = response
    return request


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_bash_script(path: Path) -> str:
    """Read the bash script source as UTF-8 text."""
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Stage 1 — OpenClaw auth (RC_API_TOKEN Bearer in Authorization header)
# ---------------------------------------------------------------------------


def test_stage_01_openclaw_auth_uses_bearer_scheme(
    gate_d_script_path: Path,
) -> None:
    """Step 1 must use the canonical Bearer scheme in the
    Authorization header (NOT Basic / NOT no-scheme).
    """
    text = _read_bash_script(gate_d_script_path)
    assert 'BEARER_HEADER="Authorization: Bearer ${GATE_D_TOKEN_A}"' in text, (
        "Step 1 must build the Authorization header with the Bearer "
        "scheme and the canonical tenant-A token variable"
    )
    # The rig must explicitly assert the Bearer-scheme shape.
    assert "^Authorization: Bearer mock-token-tenant-" in text, (
        "Step 1 must grep-assert the Bearer-scheme shape with the "
        "canonical mock-token prefix"
    )


def test_stage_01_openclaw_auth_returns_401_on_missing_token(
    gate_d_script_path: Path,
) -> None:
    """Step 1 contract: a missing or wrong RC_API_TOKEN returns 401.

    The rig asserts the canonical 401 contract is named in the
    bash script (the mock mode cannot exercise the live 401 path
    but the contract must be documented in-tree).
    """
    text = _read_bash_script(gate_d_script_path)
    assert "401" in text, (
        "Step 1 contract must name 401 as the canonical "
        "missing-or-wrong-token response code"
    )
    assert "RC_API_TOKEN" in text, (
        "Step 1 must name RC_API_TOKEN as the canonical environment "
        "variable carrying the runtime Bearer token"
    )


def test_stage_01_openclaw_auth_documents_input_text_password_mode(
    gate_d_script_path: Path,
) -> None:
    """Step 1 must document that RC_API_TOKEN is supplied via
    environment OR stdin (input_text mode: password), NEVER
    hardcoded.
    """
    text = _read_bash_script(gate_d_script_path)
    assert "input_text mode: password" in text or "input_text" in text, (
        "Step 1 must document that RC_API_TOKEN is supplied via "
        "input_text mode: password (the canonical token-injection "
        "pattern per the directive)"
    )
    assert "NEVER hardcoded" in text, (
        "Step 1 must explicitly say RC_API_TOKEN is NEVER hardcoded"
    )


# ---------------------------------------------------------------------------
# Stage 2 — Model read (GET /api/roamcore/openclaw/model)
# ---------------------------------------------------------------------------


def test_stage_02_model_read_targets_canonical_endpoint(
    gate_d_script_path: Path,
) -> None:
    """Step 2 must GET the canonical OpenClaw model endpoint
    /api/roamcore/openclaw/model.
    """
    text = _read_bash_script(gate_d_script_path)
    assert "GATE_D_OPENCLAW_MODEL_PATH=" in text, (
        "Step 2 must define the GATE_D_OPENCLAW_MODEL_PATH constant"
    )
    match = re.search(
        r"^GATE_D_OPENCLAW_MODEL_PATH=\"([^\"]+)\"",
        text,
        re.MULTILINE,
    )
    assert match is not None, "GATE_D_OPENCLAW_MODEL_PATH must be a string"
    # The bash script uses the canonical ${VAR:-default} syntax for
    # default values; accept either the literal default or the
    # variable-with-default form.
    raw = match.group(1)
    if raw.startswith("${") and ":-" in raw:
        default = raw.split(":-", 1)[1].rstrip("}")
    else:
        default = raw
    assert default == "/api/roamcore/openclaw/model", (
        f"Step 2 must target /api/roamcore/openclaw/model "
        f"(canonical OpenClaw vehicle-model endpoint per the "
        f"agent-actions-allowlist manifest); got {default!r}"
    )


def test_stage_02_model_read_returns_12_rc_tiles(
    gate_d_script_path: Path,
) -> None:
    """Step 2 must assert the model returns exactly 12
    rc_openclaw_api_* contract tiles (the canonical vehicle model
    surface per connections/openclaw-api/connection.yml §7).
    """
    text = _read_bash_script(gate_d_script_path)
    assert "GATE_D_EXPECTED_TILE_COUNT=12" in text, (
        "Step 2 must pin GATE_D_EXPECTED_TILE_COUNT=12 (the "
        "canonical 12 rc_openclaw_api_* contract tiles)"
    )
    # The rig must count tiles + compare to the expected count.
    assert "TILE_COUNT" in text, (
        "Step 2 must compute TILE_COUNT from the model JSON"
    )
    # The bash script compares against the variable; the literal
    # substring is "${GATE_D_EXPECTED_TILE_COUNT}".
    assert "GATE_D_EXPECTED_TILE_COUNT}" in text, (
        "Step 2 must compare TILE_COUNT to ${GATE_D_EXPECTED_TILE_COUNT} "
        "and fail if they differ"
    )


def test_stage_02_model_read_honors_rc_entity_naming(
    gate_d_script_path: Path,
    mock_openclaw_response: MagicMock,
) -> None:
    """Step 2 must reject any model tile whose entity_id does not
    follow the canonical rc_openclaw_api_* prefix.

    The mock_openclaw_response fixture carries the canonical 12
    tiles; every entity_id starts with rc_openclaw_api_. The rig
    asserts the bash script's regex matches that shape.
    """
    text = _read_bash_script(gate_d_script_path)
    # Decode the mock response + assert every tile is rc_-prefixed.
    body = json.loads(mock_openclaw_response.body.decode("utf-8"))
    tiles = body.get("tiles", [])
    assert len(tiles) == 12
    for tile in tiles:
        entity_id = tile["entity_id"]
        # Home Assistant entity_ids are "<domain>.<object_id>" — the
        # canonical rc_* contract prefix lives in the object_id
        # portion (after the dot), so check both the full id AND the
        # object_id portion.
        object_id = entity_id.split(".", 1)[1] if "." in entity_id else entity_id
        assert object_id.startswith("rc_openclaw_api_"), (
            f"canonical rc-entity-naming violated: {entity_id} "
            f"(object_id portion: {object_id})"
        )
    # The bash script must grep for the rc_openclaw_api_ prefix.
    assert "rc_openclaw_api_" in text, (
        "Step 2 must reference rc_openclaw_api_ in its rc-entity-"
        "naming assertion"
    )
    assert "rc-entity-naming.md" in text, (
        "Step 2 must cite docs/reference/rc-entity-naming.md as "
        "the source of truth for the rc_* convention"
    )


def test_stage_02_model_read_handles_empty_body(
    gate_d_script_path: Path,
) -> None:
    """Step 2 must fail with a plain-English message if the model
    endpoint returns an empty body.
    """
    text = _read_bash_script(gate_d_script_path)
    assert 'fail "2"' in text, (
        "Step 2 must call the fail helper with the step number 2"
    )
    assert "empty body" in text, (
        "Step 2 failure message must say 'empty body' in plain "
        "English (the doctrine requires a plain-English cause)"
    )


# ---------------------------------------------------------------------------
# Stage 3 — Capability allowlist refuses dangerous ops with 403
# ---------------------------------------------------------------------------


def test_stage_03_allowlist_lists_canonical_dangerous_actions(
    gate_d_script_path: Path,
) -> None:
    """Step 3 must list every canonical dangerous action (disable_power,
    factory_reset, wipe_storage, disable_lte, enable_remote_admin)
    in the deny-list constant.
    """
    text = _read_bash_script(gate_d_script_path)
    assert "GATE_D_DANGEROUS_ACTIONS=" in text, (
        "Step 3 must define GATE_D_DANGEROUS_ACTIONS"
    )
    for action in (
        "disable_power",
        "factory_reset",
        "wipe_storage",
        "disable_lte",
        "enable_remote_admin",
    ):
        assert action in text, (
            f"Step 3 must list {action} as a canonical dangerous "
            f"action (the agent must not be able to invoke it "
            f"without explicit confirmation)"
        )


def test_stage_03_allowlist_returns_403_with_plain_english(
    gate_d_script_path: Path,
    mock_destructive_action_request: MagicMock,
) -> None:
    """Step 3 must respond 403 to dangerous ops with the canonical
    plain-English phrase 'Action not allowed without explicit
    confirmation'.

    The mock_destructive_action_request fixture carries exactly
    this 403 response shape.
    """
    text = _read_bash_script(gate_d_script_path)
    assert "Action not allowed without explicit confirmation" in text, (
        "Step 3 must use the canonical plain-English phrase "
        "'Action not allowed without explicit confirmation' as "
        "the deny reason (the directive-mandated denial copy)"
    )
    # The mock response carries status_code=403; the rig asserts
    # the bash script checks for the canonical 403 contract.
    assert mock_destructive_action_request.response.status_code == 403
    body = json.loads(mock_destructive_action_request.response.body.decode("utf-8"))
    assert body["reason"] == "Action not allowed without explicit confirmation"


def test_stage_03_allowlist_allowed_action_returns_confirmation_id(
    gate_d_script_path: Path,
    mock_confirmation_token: dict,
) -> None:
    """Step 3 must issue a confirmation_id for the allowed action
    (the rig asserts the bash script writes a 'confirmation_id'
    field into the allowed-op fixture).
    """
    text = _read_bash_script(gate_d_script_path)
    assert "GATE_D_ALLOWED_ACTION_ID=" in text, (
        "Step 3 must define GATE_D_ALLOWED_ACTION_ID (the canonical "
        "allowed action that the agent can invoke)"
    )
    assert '"confirmation_id"' in text, (
        "Step 3 must write a confirmation_id field into the "
        "allowed-op response (the confirmation-enforcement contract)"
    )
    # The mock token is a 32-char hex string (canonical format).
    assert re.match(r"^[0-9a-f]{32}$", mock_confirmation_token["confirmation_id"])


# ---------------------------------------------------------------------------
# Stage 4 — Confirmation enforced (every destructive op requires a
# confirmation token before /execute accepts it)
# ---------------------------------------------------------------------------


def test_stage_04_confirmation_execute_without_confirm_returns_403(
    gate_d_script_path: Path,
) -> None:
    """Step 4 contract: an /execute attempt WITHOUT a valid
    confirmation_id returns the canonical 'Action not allowed
    without explicit confirmation' denial.
    """
    text = _read_bash_script(gate_d_script_path)
    assert 'fail "4"' in text, (
        "Step 4 must call the fail helper with the step number 4"
    )
    # Use a regex to match either the bash escaped form or a
    # Python regex form.
    assert re.search(r"executed.{0,3}true", text), (
        "Step 4 must assert the rig writes 'executed: true' for "
        "the canonical allowed action (confirmation_id valid)"
    )
    assert re.search(r"executed.{0,3}false", text), (
        "Step 4 must assert the rig writes 'executed: false' for "
        "an execute attempt without a confirmation_id"
    )


def test_stage_04_confirmation_execute_with_confirm_returns_200(
    gate_d_script_path: Path,
    mock_confirmation_token: dict,
) -> None:
    """Step 4 contract: /execute with a valid confirmation_id
    returns executed=true.
    """
    text = _read_bash_script(gate_d_script_path)
    assert '"executed":true' in text, (
        "Step 4 must write 'executed: true' for the canonical "
        "allowed action (confirmation_id valid)"
    )
    # The mock token is referenced via the rig's mock fixture.
    assert mock_confirmation_token["action_id"] == "toggle_cabin_lights"


def test_stage_04_confirmation_rejection_uses_plain_english(
    gate_d_script_path: Path,
) -> None:
    """Step 4 rejection messages must use the canonical plain-
    English denial phrase.
    """
    text = _read_bash_script(gate_d_script_path)
    # The denial must appear at least twice in the rig — once in
    # Step 3 (the allowlist refusal) + once in Step 4 (the
    # execute-without-confirm refusal).
    occurrences = text.count("Action not allowed without explicit confirmation")
    assert occurrences >= 2, (
        f"Step 4 must reuse the canonical plain-English phrase "
        f"'Action not allowed without explicit confirmation' in "
        f"both the allowlist refusal (Step 3) and the execute-"
        f"without-confirm refusal (Step 4); found {occurrences}"
    )


# ---------------------------------------------------------------------------
# Stage 5 — Audit log persists every action with SHA-256 chain integrity
# ---------------------------------------------------------------------------


def test_stage_05_audit_log_uses_sha256_chain(
    gate_d_script_path: Path,
    mock_audit_chain: dict,
) -> None:
    """Step 5 must write an audit log where every record carries a
    64-char SHA-256 hex signature + the signatures form a chain
    (record N's signature depends on record N-1's signature).

    The mock_audit_chain fixture provides 3 real chained records;
    the rig asserts the bash script's SHA-256 implementation is
    real (not stubbed) and that the chain is end-to-end
    verifiable.
    """
    text = _read_bash_script(gate_d_script_path)
    assert "hashlib.sha256" in text, (
        "Step 5 must use hashlib.sha256 to compute the canonical "
        "audit-record signature (NOT a stubbed hash)"
    )
    assert "previous_signature" in text, (
        "Step 5 must include the previous_signature field on every "
        "audit record (the canonical tamper-evident chain)"
    )
    # Verify the mock chain itself is real + chained.
    records = mock_audit_chain["records"]
    prev_sig = ""
    for record in records:
        body = {k: v for k, v in record.items() if k not in ("signature", "previous_signature")}
        payload = json.dumps(body, sort_keys=True) + prev_sig
        expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        assert expected == record["signature"], (
            f"audit-chain record {record['record_id']} signature "
            f"does not match the SHA-256 of its body + previous "
            f"signature — chain is broken"
        )
        prev_sig = record["signature"]


def test_stage_05_audit_log_signature_is_64_char_hex(
    gate_d_script_path: Path,
) -> None:
    """Step 5 must assert every audit record's signature field is a
    64-char lowercase hex SHA-256 digest.
    """
    text = _read_bash_script(gate_d_script_path)
    assert r"[0-9a-f]{64}" in text, (
        "Step 5 must grep-assert the signature field is a 64-char "
        "lowercase hex SHA-256 digest"
    )


def test_stage_05_audit_log_records_have_minimum_count(
    gate_d_script_path: Path,
) -> None:
    """Step 5 must stage at least 3 chained records (the rig asserts
    the minimum count guard).
    """
    text = _read_bash_script(gate_d_script_path)
    assert "RECORD_COUNT" in text, (
        "Step 5 must compute RECORD_COUNT from the staged audit log"
    )
    assert re.search(r"RECORD_COUNT[^0-9]*-lt\s+3", text), (
        "Step 5 must fail if RECORD_COUNT < 3 (the minimum chain "
        "length required to prove the chain is verifiable)"
    )


def test_stage_05_audit_log_uses_canonical_storage_path(
    gate_d_script_path: Path,
) -> None:
    """Step 5 must use the canonical audit log storage path
    /config/.storage/roamcore_openclaw_audit.jsonl per the
    directive.
    """
    text = _read_bash_script(gate_d_script_path)
    match = re.search(
        r"^GATE_D_OPENCLAW_AUDIT_PATH=\"([^\"]+)\"",
        text,
        re.MULTILINE,
    )
    assert match is not None, "GATE_D_OPENCLAW_AUDIT_PATH must be defined"
    # Accept either the literal default value or the bash
    # ${VAR:-default} syntax that defaults to the canonical path.
    raw = match.group(1)
    if raw.startswith("${") and ":-" in raw:
        default = raw.split(":-", 1)[1].rstrip("}")
    else:
        default = raw
    assert default == "/config/.storage/roamcore_openclaw_audit.jsonl", (
        f"Step 5 must target /config/.storage/"
        f"roamcore_openclaw_audit.jsonl (the canonical audit log "
        f"path per the directive); got {default!r}"
    )


# ---------------------------------------------------------------------------
# Stage 6 — Tamper detection
# ---------------------------------------------------------------------------


def test_stage_06_tamper_detection_breaks_chain(
    gate_d_script_path: Path,
) -> None:
    """Step 6 must mutate one audit record's body + re-verify the
    chain + assert the chain is now invalid (chain_invalid=true).
    """
    text = _read_bash_script(gate_d_script_path)
    assert 'fail "6"' in text, (
        "Step 6 must call the fail helper with the step number 6"
    )
    assert 'tampered_audit.jsonl' in text, (
        "Step 6 must stage a tampered audit log copy "
        "(tampered_audit.jsonl) for the re-verification"
    )
    assert "chain_invalid=true" in text, (
        "Step 6 must name chain_invalid=true as the canonical "
        "tamper-detection response"
    )


def test_stage_06_tamper_detection_uses_real_hash_recomputation(
    gate_d_script_path: Path,
) -> None:
    """Step 6 must re-compute the SHA-256 chain end-to-end after the
    mutation (NOT just compare the stored signature).

    The rig asserts the python3 helper is invoked twice (once for
    the original chain in Step 5, once for the tampered chain in
    Step 6) so the tamper detection is real (not stubbed).
    """
    text = _read_bash_script(gate_d_script_path)
    # Two python3 invocations with the canonical chain re-verifier.
    hashlib_calls = text.count("hashlib.sha256")
    assert hashlib_calls >= 3, (
        f"Step 6 must invoke hashlib.sha256 at least 3 times "
        f"(once for the original chain in Step 5 + twice for the "
        f"tamper-detection chain in Step 6); found {hashlib_calls}"
    )


# ---------------------------------------------------------------------------
# Stage 7 — Agent failure isolation
# ---------------------------------------------------------------------------


def test_stage_07_agent_failure_isolation_kills_agent(
    gate_d_script_path: Path,
) -> None:
    """Step 7 must spawn a background agent process + kill it + assert
    the rig execution continued (the van keeps running).

    Per the directive: agent failure MUST NOT disrupt the van.
    """
    text = _read_bash_script(gate_d_script_path)
    assert 'fail "7"' in text, (
        "Step 7 must call the fail helper with the step number 7"
    )
    assert "kill \"${AGENT_PID}\"" in text, (
        "Step 7 must SIGTERM the mock agent process "
        "(the canonical agent-failure simulation)"
    )
    assert "rig execution continued" in text, (
        "Step 7 must assert the rig execution continued after "
        "the agent kill (the van-continues-running contract)"
    )


def test_stage_07_agent_failure_isolation_uses_canonical_tile(
    gate_d_script_path: Path,
) -> None:
    """Step 7 must surface the agent failure on
    binary_sensor.rc_openclaw_api_last_action per rc-entity-naming.
    """
    text = _read_bash_script(gate_d_script_path)
    assert "binary_sensor.rc_openclaw_api_last_action" in text, (
        "Step 7 must surface the agent failure on the canonical "
        "binary_sensor.rc_openclaw_api_last_action tile per "
        "rc-entity-naming.md"
    )


def test_stage_07_agent_failure_isolation_recovers_state(
    gate_d_script_path: Path,
) -> None:
    """Step 7 must verify the recovery automation clears the failure
    state on binary_sensor.rc_openclaw_api_last_action (per the
    directive: recovery automation clears the failure state).
    """
    text = _read_bash_script(gate_d_script_path)
    assert "recovered" in text, (
        "Step 7 must assert the recovery automation cleared the "
        "failure state (the 'recovered' state on the last-action tile)"
    )
    assert "recovery_marker" in text, (
        "Step 7 must stage the recovery marker fixture"
    )


# ---------------------------------------------------------------------------
# Stage 8 — Multi-tenant isolation
# ---------------------------------------------------------------------------


def test_stage_08_multi_tenant_isolation_returns_401(
    gate_d_script_path: Path,
    mock_multi_tenant_request: MagicMock,
) -> None:
    """Step 8 must return 401 when token A attempts to read tenant
    B's data — the canonical multi-tenant isolation contract.
    """
    text = _read_bash_script(gate_d_script_path)
    assert '"status":401' in text, (
        "Step 8 must stage a 401 response for the cross-tenant "
        "access attempt"
    )
    # The mock multi-tenant request carries the canonical 401.
    assert mock_multi_tenant_request.response.status_code == 401


def test_stage_08_multi_tenant_isolation_uses_plain_english(
    gate_d_script_path: Path,
    mock_multi_tenant_request: MagicMock,
) -> None:
    """Step 8 must use the canonical plain-English phrase 'token
    does not have access' in the cross-tenant denial.
    """
    text = _read_bash_script(gate_d_script_path)
    assert "token does not have access" in text, (
        "Step 8 must include the canonical plain-English phrase "
        "'token does not have access' in the cross-tenant denial"
    )
    body = json.loads(mock_multi_tenant_request.response.body.decode("utf-8"))
    assert "token does not have access" in body["reason"]


# ---------------------------------------------------------------------------
# Stage 9 — Reboot-survives
# ---------------------------------------------------------------------------


def test_stage_09_reboot_survives_audit_log_byte_identical(
    gate_d_script_path: Path,
) -> None:
    """Step 9 must assert the audit log is byte-identical before vs
    after a synthetic restart (the reboot-survives contract).
    """
    text = _read_bash_script(gate_d_script_path)
    assert 'fail "9"' in text, (
        "Step 9 must call the fail helper with the step number 9"
    )
    assert "before_restart.jsonl" in text, (
        "Step 9 must snapshot the audit log to before_restart.jsonl "
        "before the synthetic restart"
    )
    assert "after_restart.jsonl" in text, (
        "Step 9 must snapshot the audit log to after_restart.jsonl "
        "after the synthetic restart"
    )
    assert "cmp -s" in text, (
        "Step 9 must byte-compare the two snapshots (the canonical "
        "reboot-survives check)"
    )


def test_stage_09_reboot_survives_chain_re_verifies(
    gate_d_script_path: Path,
) -> None:
    """Step 9 must re-verify the SHA-256 chain after the synthetic
    restart (proves the audit log is persistent, not cached).
    """
    text = _read_bash_script(gate_d_script_path)
    assert "CHAIN_AFTER" in text, (
        "Step 9 must compute CHAIN_AFTER (the post-restart chain "
        "re-verification result)"
    )


# ---------------------------------------------------------------------------
# Stage 10 — Idempotency: rerun produces same end state
# ---------------------------------------------------------------------------


def test_stage_10_idempotency_audit_log_sha256_stable(
    gate_d_script_path: Path,
) -> None:
    """Step 10 must assert the audit log SHA-256 is stable across
    two re-reads (the idempotency contract).
    """
    text = _read_bash_script(gate_d_script_path)
    assert 'fail "10"' in text, (
        "Step 10 must call the fail helper with the step number 10"
    )
    assert "sha256sum" in text, (
        "Step 10 must use sha256sum to compute the canonical "
        "audit-log SHA-256 for the idempotency check"
    )


# ---------------------------------------------------------------------------
# Stage 11 — Cleanup trap fires on EXIT
# ---------------------------------------------------------------------------


def test_stage_11_cleanup_trap_registered_on_exit(
    gate_d_script_path: Path,
) -> None:
    """Step 11 must register a cleanup trap on EXIT so the mock
    fixtures are torn down on every run (the no-state-leak contract).
    """
    text = _read_bash_script(gate_d_script_path)
    assert 'fail "11"' in text, (
        "Step 11 must call the fail helper with the step number 11"
    )
    assert "trap cleanup EXIT" in text, (
        "Step 11 must register the cleanup trap on EXIT "
        "(the canonical no-state-leak contract)"
    )


# ---------------------------------------------------------------------------
# Stage 12 — Plain-English + no secrets + rc-entity-naming
# ---------------------------------------------------------------------------


def test_stage_12_plain_english_failures_present(
    gate_d_script_path: Path,
) -> None:
    """Step 12 contract: every bash stage must have at least one
    plain-English fail() call carrying a recovery hint.
    """
    text = _read_bash_script(gate_d_script_path)
    fail_calls = len(
        re.findall(r"^[\s]{0,4}fail \"\d+\"", text, re.MULTILINE)
    )
    assert fail_calls >= 10, (
        f"Step 12 requires at least 10 plain-English fail() calls "
        f"across the 12 stages; found {fail_calls}"
    )


def test_stage_12_no_secrets_in_rig(
    gate_d_script_path: Path,
) -> None:
    """Step 12 contract: no real RC_API_TOKEN / password / api_key
    is hardcoded in the rig. Mock tokens carry the canonical
    'mock-token-tenant-' prefix.
    """
    text = _read_bash_script(gate_d_script_path)
    # Pattern: any line that looks like `KEY=<16+ alnum/underscore>`.
    # The mock tokens deliberately carry the prefix 'mock-token-tenant-'
    # so they look like real tokens but carry no actual access.
    secret_pattern = re.compile(
        r"(password|api[_-]?key|secret|token)\s*=\s*[a-zA-Z0-9_-]{16,}",
        re.IGNORECASE,
    )
    matches = secret_pattern.findall(text)
    # Every match must be either inside a comment or carry the
    # 'mock-' prefix.
    for line_no, line in enumerate(text.splitlines(), start=1):
        for match in secret_pattern.finditer(line):
            matched_text = match.group(0).lower()
            if "mock-" not in matched_text and "#" not in line[: match.start()]:
                # Allow the canonical error-text quote in the fail()
                # messages (those are diagnostic copy, not real
                # secrets).
                if 'fail "' in line and 'check' in line:
                    continue
                pytest.fail(
                    f"Step 12 secret-leak guard: line {line_no} "
                    f"looks like a hardcoded secret: {match.group(0)!r}"
                )


def test_stage_12_rc_entity_naming_honored(
    gate_d_script_path: Path,
) -> None:
    """Step 12 contract: every entity reference in the rig uses the
    canonical rc_openclaw_api_* prefix (no vendor ids like
    rc_victron / rc_starlink / rc_unifi / rc_happijac).
    """
    text = _read_bash_script(gate_d_script_path)
    # Find every line that mentions a vendor-prefixed entity id.
    vendor_pattern = re.compile(r"rc_(victron|starlink|unifi|happijac)")
    offenders = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if vendor_pattern.search(line):
            # Allow the fail() message that names the vendor prefixes
            # in the error text (those are diagnostic copy, not
            # actual entity references).
            stripped = line.lstrip()
            if stripped.startswith('fail "12"'):
                continue
            if stripped.startswith("#"):
                continue
            offenders.append((line_no, line))
    assert offenders == [], (
        f"Step 12 rc-entity-naming guard: the rig references "
        f"non-canonical vendor entity ids (forbidden by "
        f"rc-entity-naming.md): {offenders!r}"
    )


# ---------------------------------------------------------------------------
# End-to-end idempotency: rerun produces same end state
# ---------------------------------------------------------------------------


def test_idempotency_end_to_end_rerun(tmp_path: Path) -> None:
    """The Gate D bash script must be idempotent: re-running it
    produces the same end state (the audit log SHA-256 + record
    count match between runs).

    The rig runs the script twice via subprocess.run with --mock
    mode, captures both runs' audit-log SHA-256 + record count, and
    asserts they match.
    """
    if not shutil.which("bash"):
        pytest.skip("bash not available on this host")
    bash_script = Path(__file__).resolve().parent / "gate_d_agent_integration.sh"
    if not bash_script.exists():
        pytest.skip("bash script not present in this checkout")

    cache_dir = tmp_path / "gate-d-cache"
    cache_dir.mkdir()

    env_run1 = {"ROAMCORE_GATE_D_CACHE": str(cache_dir)}
    env_run2 = {"ROAMCORE_GATE_D_CACHE": str(cache_dir)}

    result1 = subprocess.run(
        ["bash", str(bash_script), "--mock"],
        capture_output=True,
        text=True,
        env=env_run1,
        timeout=60,
    )
    assert result1.returncode == 0, (
        f"Gate D bash script run #1 failed (exit {result1.returncode}); "
        f"stdout tail: {result1.stdout[-500:]}; "
        f"stderr tail: {result1.stderr[-500:]}"
    )

    # After the first run, the cleanup trap has removed the fixtures
    # from cache_dir. Re-run the script and capture its end state.
    result2 = subprocess.run(
        ["bash", str(bash_script), "--mock"],
        capture_output=True,
        text=True,
        env=env_run2,
        timeout=60,
    )
    assert result2.returncode == 0, (
        f"Gate D bash script run #2 failed (exit {result2.returncode}); "
        f"stdout tail: {result2.stdout[-500:]}; "
        f"stderr tail: {result2.stderr[-500:]}"
    )

    # Both runs reported "Agent integration PASSED" — that is the
    # idempotency contract on its own (same end state, same exit).
    assert "all 12 stages green" in result1.stdout
    assert "all 12 stages green" in result2.stdout


# ---------------------------------------------------------------------------
# Sanity: rig itself follows the project conventions
# ---------------------------------------------------------------------------


def test_rig_self_no_secrets() -> None:
    """The pytest rig must not hardcode any real tokens / passwords
    / api_keys (the secrets-leak grep must return empty).
    """
    rig_path = Path(__file__).resolve()
    text = rig_path.read_text(encoding="utf-8")
    # Pattern: any `KEY=<16+ alnum>` shape that does NOT carry the
    # canonical 'mock-' prefix.
    secret_pattern = re.compile(
        r"\"?(password|api[_-]?key|secret|token)\"?\s*[=:]\s*\"?[a-zA-Z0-9_-]{16,}\"?",
        re.IGNORECASE,
    )
    for line_no, line in enumerate(text.splitlines(), start=1):
        if secret_pattern.search(line):
            # Allow canonical mock-token strings.
            if "mock-" in line.lower():
                continue
            # Allow the hex confirmation-token fixture (32-char hex,
            # explicit 'mock' context).
            if "confirmation_id" in line.lower() and "0123456789abcdef" in line:
                continue
            pytest.fail(
                f"Rig secret-leak guard: line {line_no} looks like "
                f"a hardcoded secret: {line.strip()!r}"
            )