"""RoamCore audit-log helpers — Gate D (chain-of-custody for agent actions).

This module is the single source of truth for the append-only audit log
that records every agent action through the OpenClaw JSON API. It exposes:

- :func:`append_audit_record` — append a record to the JSONL audit log
  (idempotent across HA restarts; safe to call when the file already exists).
- :func:`compute_signature` — SHA-256 hash over the canonical JSON of a
  record with its ``signature`` field stripped.
- :func:`build_record` — build a fully-formed audit record (including
  prev + current signature) for a given action context.
- :func:`verify_chain` — re-walk the audit chain and confirm every record
  hashes to its declared ``signature`` and references the previous
  record's ``signature`` correctly. This is the tamper-evidence
  primitive Gate D relies on.
- :func:`audit_chain_path` — canonical path to the JSONL chain
  (``<config_dir>/.roamcore/roamcore_audit_chain.jsonl``).
- :data:`AUDIT_RECORD_V1` — the JSON Schema (draft 2020-12 lite subset
  we actually validate against) for a single record.

Design notes:
- The chain lives in ``.roamcore/roamcore_audit_chain.jsonl`` (sibling
  to the existing ``.roamcore/agent_action_log.jsonl`` from
  ``actions.py``). It is the canonical tamper-evident chain; the
  non-chained log remains a best-effort human-readable mirror.
- The chain is purely additive — no rewriting, no deleting, no rotation
  inside the integration. Operators who need to rotate should follow
  the doc: snapshot HA first, then rename + re-verify.
- Failures here MUST NOT crash the API: writes fall back to
  ``homeassistant.components.persistent_notification`` and to a
  best-effort log line. See :func:`append_audit_record`.

Backup warning (operator note):
    The audit chain is sensitive. Before any Home Assistant Full Backup
    or filesystem snapshot, include
    ``<config_dir>/.roamcore/roamcore_audit_chain.jsonl`` in the backup.
    Without that snapshot, historical chain verification becomes
    impossible.

Tier discipline:
    This is tier-a code — Gate D is the audit + confirmation gate that
    the directive mandates for any agent interface. Keep it minimal,
    dependency-free, and reviewable.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Canonical path to the chained audit log (JSONL).
#: Resolved via :func:`audit_chain_path` against the HA ``config_dir``.
AUDIT_CHAIN_FILENAME = "roamcore_audit_chain.jsonl"

#: Number of hex zeros used to represent the "no predecessor" sentinel.
#: 64 hex digits = SHA-256 width.
ZERO_SIG_LEN = 64

#: Sentinel signature used for the first record in an empty chain.
ZERO_SIG = "0" * ZERO_SIG_LEN

#: Max number of bytes we are willing to read from a single audit record
#: on read-back. Defensive cap — a sane record is < 4 KB.
MAX_RECORD_BYTES = 32 * 1024


# ---------------------------------------------------------------------------
# JSON Schema (audit_record_v1)
# ---------------------------------------------------------------------------

#: Minimal JSON Schema for ``audit_record_v1``. We deliberately keep the
#: schema small enough to validate with stdlib alone (no jsonschema
#: dependency required) — pytest + prod code share this dict.
AUDIT_RECORD_V1: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://roamcore.dev/schemas/audit_record_v1.json",
    "title": "audit_record_v1",
    "type": "object",
    "required": [
        "schema_version",
        "ts",
        "actor",
        "action_id",
        "result",
        "reason",
        "params",
        "prev_signature",
        "signature",
        "ha_version",
    ],
    "properties": {
        "schema_version": {"const": 1},
        "ts": {"type": "string", "minLength": 10},
        "actor": {
            "type": "object",
            "required": ["kind", "id", "display"],
            "properties": {
                "kind": {"type": "string", "enum": ["agent", "user", "system"]},
                "id": {"type": "string", "minLength": 1},
                "display": {"type": "string"},
            },
        },
        "action_id": {"type": "string", "minLength": 1},
        "confirmation_id": {
            "oneOf": [
                {"type": "string", "minLength": 1},
                {"type": "null"},
            ]
        },
        "result": {
            "type": "string",
            "enum": ["allowed", "blocked", "expired", "rejected"],
        },
        "reason": {"type": "string"},
        "params": {"type": "object"},
        "prev_signature": {
            "type": "string",
            "pattern": "^[0-9a-f]{64}$",
        },
        "signature": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "ha_version": {"type": "string", "minLength": 1},
    },
    "additionalProperties": True,
}


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def audit_chain_path(config_dir: str) -> str:
    """Return the canonical audit-chain path for ``config_dir``."""
    return os.path.join(config_dir, ".roamcore", AUDIT_CHAIN_FILENAME)


def audit_chain_dir(config_dir: str) -> str:
    """Return the directory that should contain the audit chain."""
    return os.path.join(config_dir, ".roamcore")


# ---------------------------------------------------------------------------
# Time + canonical JSON helpers
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(obj: Any) -> str:
    """Return a deterministic JSON encoding for ``obj``.

    - Sorts keys so two semantically equal objects hash the same.
    - Uses ``ensure_ascii=False`` so non-ASCII reasons survive intact.
    - Separators are compact (``", "`` and ``": "``) to make the bytes
      stable across Python versions.
    """

    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ": "),
    )


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


def validate_record(record: dict[str, Any]) -> tuple[bool, str | None]:
    """Validate ``record`` against :data:`AUDIT_RECORD_V1`.

    Returns ``(True, None)`` on success or ``(False, "<reason>")`` on
    failure. The validator is intentionally hand-written and
    dependency-free so this module can be imported in any HA core
    environment without a third-party ``jsonschema`` package.
    """

    if not isinstance(record, dict):
        return False, "record must be an object"

    for key in AUDIT_RECORD_V1["required"]:
        if key not in record:
            return False, f"missing required field: {key}"

    if record.get("schema_version") != 1:
        return False, "schema_version must be 1"

    if not isinstance(record.get("ts"), str) or len(str(record["ts"])) < 10:
        return False, "ts must be an ISO-8601 string"

    actor = record.get("actor")
    if not isinstance(actor, dict):
        return False, "actor must be an object"
    for k in ("kind", "id", "display"):
        if k not in actor:
            return False, f"actor missing field: {k}"
    if actor.get("kind") not in ("agent", "user", "system"):
        return False, "actor.kind must be agent|user|system"
    if not isinstance(actor.get("id"), str) or not actor["id"]:
        return False, "actor.id must be a non-empty string"

    if not isinstance(record.get("action_id"), str) or not record["action_id"]:
        return False, "action_id must be a non-empty string"

    if "confirmation_id" in record and record["confirmation_id"] is not None:
        if not isinstance(record["confirmation_id"], str) or not record["confirmation_id"]:
            return False, "confirmation_id must be a non-empty string when present"

    if record.get("result") not in ("allowed", "blocked", "expired", "rejected"):
        return False, "result must be allowed|blocked|expired|rejected"

    if not isinstance(record.get("reason"), str):
        return False, "reason must be a string"

    if not isinstance(record.get("params"), dict):
        return False, "params must be an object"

    for sig_field in ("prev_signature", "signature"):
        v = record.get(sig_field)
        if not isinstance(v, str) or len(v) != ZERO_SIG_LEN:
            return False, f"{sig_field} must be a {ZERO_SIG_LEN}-char hex string"
        try:
            int(v, 16)
        except ValueError:
            return False, f"{sig_field} must be hex"

    if not isinstance(record.get("ha_version"), str) or not record["ha_version"]:
        return False, "ha_version must be a non-empty string"

    return True, None


# ---------------------------------------------------------------------------
# Signatures + chain reading
# ---------------------------------------------------------------------------


def compute_signature(record: dict[str, Any]) -> str:
    """Return the SHA-256 signature of ``record`` (sans its own signature).

    The signature is ``SHA-256(canonical_json({k:v for k,v in record.items()
    if k != 'signature'}))``. ``prev_signature`` IS part of the input
    — that is what binds the chain together.
    """

    body = {k: v for k, v in record.items() if k != "signature"}
    encoded = _canonical_json(body).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_record(
    *,
    ts: str | None,
    actor: dict[str, Any],
    action_id: str,
    confirmation_id: str | None,
    result: str,
    reason: str,
    params: dict[str, Any],
    prev_signature: str,
    ha_version: str,
    schema_version: int = 1,
) -> dict[str, Any]:
    """Build a complete audit record (including signatures).

    The returned dict is suitable for :func:`append_audit_record` and
    has its ``signature`` pre-computed.
    """

    record: dict[str, Any] = {
        "schema_version": int(schema_version),
        "ts": ts or _utc_now_iso(),
        "actor": dict(actor),
        "action_id": str(action_id),
        "confirmation_id": (str(confirmation_id) if confirmation_id else None),
        "result": str(result),
        "reason": str(reason),
        "params": dict(params or {}),
        "prev_signature": str(prev_signature),
        "signature": "",  # filled in below
        "ha_version": str(ha_version),
    }
    record["signature"] = compute_signature(record)
    return record


def _last_signature(path: str) -> str:
    """Return the signature of the last record in ``path`` (or ZERO_SIG)."""

    if not os.path.exists(path):
        return ZERO_SIG

    sig = ZERO_SIG
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    # Skip unparseable trailing line — verify_chain() will
                    # still flag it on a full walk. We just need the last
                    # good signature here.
                    continue
                if isinstance(obj, dict) and isinstance(obj.get("signature"), str):
                    sig = obj["signature"]
    except Exception:
        return ZERO_SIG
    return sig


# ---------------------------------------------------------------------------
# Public: append + verify
# ---------------------------------------------------------------------------


def append_audit_record(
    path: str,
    record: dict[str, Any],
    *,
    fallback_notify: callable = None,  # type: ignore[valid-type]
    fallback_logger: Any = None,
) -> bool:
    """Append ``record`` to the JSONL audit chain at ``path``.

    The function is idempotent across HA restarts: an existing file is
    appended to (its tail is read for the previous signature). Returns
    ``True`` if the record was written, ``False`` if a fallback path
    was used. Callers should never propagate failures from here
    upstream — Gate D is "never crash the API".

    Prev-signature resolution contract:
        If the caller passes ``prev_signature=""`` (or ``None``) we
        auto-resolve it from the last signature on disk. This is the
        canonical "restart-safe append" path. If the caller passes an
        explicit non-empty hex string we trust it (e.g. a freshly-built
        record that already knows its place in the chain).
    """

    prev = record.get("prev_signature")
    if prev is None or prev == "" or prev == ZERO_SIG and not os.path.exists(path):
        record["prev_signature"] = _last_signature(path)
    elif prev == ZERO_SIG and os.path.exists(path):
        # Caller passed ZERO_SIG on a non-empty chain → trust them
        # only if the chain is actually empty. Otherwise auto-resolve.
        last = _last_signature(path)
        if last != ZERO_SIG:
            record["prev_signature"] = last

    # Ensure signature is current (idempotent for repeated calls).
    record["signature"] = compute_signature(record)

    ok, err = validate_record(record)
    if not ok:
        _fallback(f"audit record failed schema validation: {err}", record, fallback_notify, fallback_logger)
        return False

    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        line = json.dumps(record, ensure_ascii=False, sort_keys=False)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        return True
    except Exception as e:
        _fallback(f"audit record write failed: {e}", record, fallback_notify, fallback_logger)
        return False


def _fallback(msg: str, record: dict[str, Any], notify: callable, logger: Any) -> None:
    """Best-effort fallback: try the ``persistent_notification`` bus, else log."""

    payload = {
        "title": "RoamCore audit fallback",
        "message": f"{msg}. Record was NOT written to the audit chain. "
                   f"action_id={record.get('action_id')!r} result={record.get('result')!r}.",
        "notification_id": f"roamcore_audit_fallback_{record.get('action_id')}",
    }

    if callable(notify):
        try:
            notify(payload)
            return
        except Exception:
            pass

    if logger is not None:
        try:
            logger.warning("%s | record=%s", msg, _canonical_json(record))
            return
        except Exception:
            pass

    # Last resort: stderr. The HA core logbook integration will pick it up.
    try:
        import sys
        print(f"[roamcore-audit-fallback] {msg} | record={_canonical_json(record)}", file=sys.stderr)
    except Exception:
        pass


def read_chain(path: str) -> list[dict[str, Any]]:
    """Read all records from the chain at ``path``.

    Lines that fail to parse are skipped (with the line number returned
    via the optional ``on_bad_line`` contract — see :func:`verify_chain`).
    """

    if not os.path.exists(path):
        return []

    out: list[dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if isinstance(obj, dict):
                    out.append(obj)
    except Exception:
        return out
    return out


def verify_chain(path: str) -> tuple[bool, str | None]:
    """Walk the chain at ``path`` and verify every record.

    Returns ``(True, None)`` if the chain is intact. Otherwise returns
    ``(False, "<reason>")`` with the failing line number / field.

    Tamper-evidence property:
        Because each record's signature is computed over its body
        (including ``prev_signature``), any tampering with a record's
        fields — even the ``reason`` field — invalidates the signature
        AND every subsequent record's ``prev_signature`` link. There is
        no way to silently rewrite history without re-signing every
        record from the tampered point forward, which is detectable by
        comparing the trailing signature against a separately-anchored
        checkpoint.
    """

    if not os.path.exists(path):
        return True, None  # Empty chain is trivially valid.

    prev_sig = ZERO_SIG
    line_no = 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line_no += 1
                line = raw.strip()
                if not line:
                    continue

                try:
                    obj = json.loads(line)
                except Exception as e:
                    return False, f"line {line_no}: not valid JSON ({e})"

                if not isinstance(obj, dict):
                    return False, f"line {line_no}: not a JSON object"

                ok, err = validate_record(obj)
                if not ok:
                    return False, f"line {line_no}: schema invalid ({err})"

                if obj["prev_signature"] != prev_sig:
                    return False, (
                        f"line {line_no}: prev_signature mismatch "
                        f"(expected {prev_sig[:12]}…, got {str(obj['prev_signature'])[:12]}…)"
                    )

                expected = compute_signature(obj)
                if obj["signature"] != expected:
                    return False, (
                        f"line {line_no}: signature mismatch "
                        f"(expected {expected[:12]}…, got {str(obj['signature'])[:12]}…)"
                    )

                prev_sig = obj["signature"]
    except Exception as e:
        return False, f"chain read failed at line {line_no}: {e}"

    return True, None


__all__ = [
    "AUDIT_CHAIN_FILENAME",
    "AUDIT_RECORD_V1",
    "ZERO_SIG",
    "audit_chain_dir",
    "audit_chain_path",
    "append_audit_record",
    "build_record",
    "compute_signature",
    "read_chain",
    "validate_record",
    "verify_chain",
]