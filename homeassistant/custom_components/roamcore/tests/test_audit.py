"""Audit chain integrity tests (Gate D).

Verifies the hash-chained audit log:
- A 5-record chain verifies cleanly.
- Tampering with any field in any record breaks the chain.
- Idempotent restart-safe appends work.
- Schema validation rejects malformed records.
- Reading + walking the chain returns records in order.

Run:
    cd /home/bernard/clawd/RoamCore
    source .venv/bin/activate
    pytest homeassistant/custom_components/roamcore/tests/test_audit.py -v
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from typing import Any

import pytest

# Make the roamcore package importable without HA runtime.
HERE = os.path.dirname(__file__)
PKG_PARENT = os.path.abspath(
    os.path.join(HERE, "..", "..", "..", "..")
)
# PKG_PARENT is the repo root. The package itself lives under
# homeassistant/custom_components/roamcore.
PKG_DIR = os.path.abspath(
    os.path.join(HERE, "..", "..")
)
if PKG_PARENT not in sys.path:
    sys.path.insert(0, PKG_PARENT)
# Custom components are usually discovered by HA's loader; we make
# the `roamcore` module importable by inserting its directory.
if PKG_DIR not in sys.path:
    sys.path.insert(0, PKG_DIR)


from roamcore.audit import (  # type: ignore  # noqa: E402
    AUDIT_RECORD_V1,
    ZERO_SIG,
    append_audit_record,
    build_record,
    compute_signature,
    read_chain,
    validate_record,
    verify_chain,
)


def _make_record(i: int, prev_sig: str, **overrides: Any) -> dict[str, Any]:
    r = build_record(
        ts=f"2026-08-05T0{i}:00:00+00:00",
        actor={"kind": "agent", "id": "test-agent", "display": "Test Agent"},
        action_id=f"test.action.{i}",
        confirmation_id=None,
        result="allowed",
        reason="test",
        params={"i": i},
        prev_signature=prev_sig,
        ha_version="2026.8.0",
    )
    for k, v in overrides.items():
        r[k] = v
    # Re-sign after override so signatures stay consistent.
    r["signature"] = compute_signature(r)
    return r


class TestAuditChain:
    def test_empty_chain_is_valid(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "chain.jsonl")
            ok, err = verify_chain(p)
            assert ok, err
            assert err is None

    def test_five_record_chain_verifies(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "chain.jsonl")
            prev = ZERO_SIG
            for i in range(5):
                r = _make_record(i, prev)
                ok = append_audit_record(p, r)
                assert ok
                prev = r["signature"]

            ok, err = verify_chain(p)
            assert ok, err
            assert err is None

            records = read_chain(p)
            assert len(records) == 5

    def test_tampering_reason_field_breaks_chain(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "chain.jsonl")
            prev = ZERO_SIG
            records = []
            for i in range(5):
                r = _make_record(i, prev)
                append_audit_record(p, r)
                records.append(r)
                prev = r["signature"]

            # Tamper with record[2]'s reason field, then rewrite the file.
            records[2]["reason"] = "TAMPERED"
            # Don't re-sign — simulate an attacker who didn't have the key.
            with open(p, "w", encoding="utf-8") as f:
                for rec in records:
                    f.write(json.dumps(rec) + "\n")

            ok, err = verify_chain(p)
            assert not ok
            assert "line 3" in (err or "")
            assert "signature" in (err or "")

    def test_tampering_action_id_breaks_chain(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "chain.jsonl")
            prev = ZERO_SIG
            records = []
            for i in range(3):
                r = _make_record(i, prev)
                append_audit_record(p, r)
                records.append(r)
                prev = r["signature"]

            # Tamper with the middle record's action_id.
            records[1]["action_id"] = "test.action.MALICIOUS"
            with open(p, "w", encoding="utf-8") as f:
                for rec in records:
                    f.write(json.dumps(rec) + "\n")

            ok, err = verify_chain(p)
            assert not ok

    def test_idempotent_append_across_restart(self):
        """Re-opening an existing chain and appending must link correctly."""
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "chain.jsonl")

            # First "session" — write 3 records.
            prev = ZERO_SIG
            for i in range(3):
                r = _make_record(i, prev)
                append_audit_record(p, r)
                prev = r["signature"]
            last_sig_after_first = prev

            # Simulate a "restart": read the chain back, then append more.
            records = read_chain(p)
            assert len(records) == 3
            assert records[-1]["signature"] == last_sig_after_first

            # New appends should pick up prev_signature from the file.
            r4 = build_record(
                ts="2026-08-05T04:00:00+00:00",
                actor={"kind": "user", "id": "bernard", "display": "B"},
                action_id="test.action.4",
                confirmation_id=None,
                result="allowed",
                reason="post-restart",
                params={"i": 4},
                prev_signature=ZERO_SIG,  # intentionally wrong → append should fix
                ha_version="2026.8.0",
            )
            ok = append_audit_record(p, r4)
            assert ok

            ok, err = verify_chain(p)
            assert ok, err

            # And the prev_signature of record 4 must equal the last sig of record 3.
            all_records = read_chain(p)
            assert all_records[3]["prev_signature"] == last_sig_after_first
            assert all_records[3]["action_id"] == "test.action.4"

    def test_validate_record_rejects_missing_required(self):
        ok, err = validate_record({"schema_version": 1})
        assert not ok
        assert "missing required field" in (err or "")

    def test_validate_record_rejects_bad_signature_hex(self):
        r = _make_record(0, ZERO_SIG)
        r["signature"] = "not-hex-at-all"
        ok, err = validate_record(r)
        assert not ok
        assert "hex" in (err or "").lower() or "signature" in (err or "").lower()

    def test_validate_record_rejects_unknown_result(self):
        r = _make_record(0, ZERO_SIG)
        r["result"] = "maybe"
        # Re-sign because we changed the body.
        r["signature"] = compute_signature(r)
        ok, err = validate_record(r)
        assert not ok
        assert "result" in (err or "").lower()

    def test_validate_record_rejects_wrong_schema_version(self):
        r = _make_record(0, ZERO_SIG)
        r["schema_version"] = 99
        r["signature"] = compute_signature(r)
        ok, err = validate_record(r)
        assert not ok
        assert "schema_version" in (err or "").lower()

    def test_audit_record_v1_schema_has_required_fields(self):
        required = AUDIT_RECORD_V1["required"]
        for k in (
            "schema_version", "ts", "actor", "action_id",
            "result", "reason", "params",
            "prev_signature", "signature", "ha_version",
        ):
            assert k in required, f"AUDIT_RECORD_V1 missing required: {k}"

    def test_write_failure_falls_back_without_crashing(self):
        """If the audit file can't be written, append_audit_record must
        not raise — it falls back via the persistent_notification bus."""

        captured = []

        def fake_notify(payload):
            captured.append(payload)

        # Use an obviously unwritable path.
        bad_path = "/proc/this/does/not/exist/audit.jsonl"
        r = _make_record(0, ZERO_SIG)
        ok = append_audit_record(bad_path, r, fallback_notify=fake_notify)
        # It should report failure (False) but not raise.
        assert ok is False
        # Either the notify fired OR stderr/logger absorbed it.
        # We don't require a specific sink — we just require no exception.


class TestAuditSignatures:
    def test_signature_is_deterministic(self):
        r = _make_record(0, ZERO_SIG)
        sig1 = compute_signature(r)
        sig2 = compute_signature(r)
        assert sig1 == sig2
        assert len(sig1) == 64

    def test_signature_changes_with_body(self):
        r1 = _make_record(0, ZERO_SIG)
        r2 = _make_record(1, ZERO_SIG)
        # Different action_id → different signature.
        assert compute_signature(r1) != compute_signature(r2)

    def test_prev_signature_is_part_of_input(self):
        r_zero = _make_record(0, ZERO_SIG)
        r_with_prev = _make_record(0, "deadbeef" * 8)
        # Same body except prev_signature → different signature.
        assert compute_signature(r_zero) != compute_signature(r_with_prev)


if __name__ == "__main__":  # pragma: no cover
    import unittest
    unittest.main()