"""RoamCore action allowlist + Gate D confirmation helpers.

This module owns the agent-action allowlist logic and the confirmation
flow that protects destructive operations. The chain-of-custody
audit log itself lives in :mod:`.audit` (lifted out of this file in
Wave 9 #113 so multiple call sites can share it).

Public surface:
- :func:`allowlist_path` / :func:`auditlog_path` — disk paths
- :func:`load_allowlist_yaml` / :func:`find_action` — allowlist lookups
- :func:`validate_constraints` — per-action param validation
- :func:`append_audit_record` — re-exported from :mod:`.audit` (kept
  here so older imports keep working).
- :func:`request_confirmation` / :func:`confirm_action` /
  :func:`reject_confirmation` — the Gate D confirmation flow.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import re
import secrets
import threading
from typing import Any


# ---------------------------------------------------------------------------
# ActionResult
# ---------------------------------------------------------------------------


@dataclass
class ActionResult:
    ok: bool
    error: str | None = None
    details: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Time + paths
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def allowlist_path(config_dir: str) -> str:
    return os.path.join(config_dir, ".roamcore", "agent_allowlist.yaml")


def auditlog_path(config_dir: str) -> str:
    """Best-effort human-readable action log (not tamper-evident).

    The tamper-evident chain lives at :func:`audit.audit_chain_path`.
    This file remains for human eyeballing + grep-friendly export.
    """
    return os.path.join(config_dir, ".roamcore", "agent_action_log.jsonl")


def pending_confirmations_path(config_dir: str) -> str:
    """JSONL file holding in-flight confirmation challenges.

    Each line is one confirmation object. We use JSONL (append-only
    + truncate on confirm/reject) so HA restarts don't drop pending
    codes. The file is local-only — never committed.
    """
    return os.path.join(config_dir, ".roamcore", "agent_pending_confirmations.jsonl")


# ---------------------------------------------------------------------------
# Allowlist
# ---------------------------------------------------------------------------


def load_allowlist_yaml(path: str) -> dict[str, Any]:
    # Local import: Home Assistant environments usually ship PyYAML.
    import yaml  # type: ignore

    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def find_action(policy: dict[str, Any], action_id: str) -> dict[str, Any] | None:
    actions = policy.get("actions") or []
    for a in actions:
        if isinstance(a, dict) and str(a.get("id") or "") == action_id:
            return a
    return None


def action_requires_confirmation(action: dict[str, Any]) -> bool:
    """Return True if this action must be confirmed by the user.

    The flag is opt-in on the allowlist record:
        actions:
          - id: network.change
            requires_confirmation: true
            ...
    Destructive / irreversible actions should set this. Reads + non-
    destructive toggles should leave it false (default).
    """
    try:
        return bool(action.get("requires_confirmation"))
    except Exception:
        return False


def validate_constraints(constraints: dict[str, Any] | None, value: Any) -> tuple[bool, str | None]:
    if not constraints:
        return True, None

    if "pattern" in constraints:
        pat = str(constraints.get("pattern") or "")
        try:
            if re.match(pat, str(value)) is None:
                return False, "value does not match pattern"
        except re.error:
            return False, "invalid allowlist pattern"

    if "enum" in constraints:
        allowed = constraints.get("enum") or []
        if str(value) not in [str(x) for x in allowed]:
            return False, "value not in enum allowlist"

    if "min" in constraints or "max" in constraints:
        try:
            n = float(value)
        except Exception:
            return False, "value is not numeric"
        if "min" in constraints and n < float(constraints.get("min")):
            return False, "value below min"
        if "max" in constraints and n > float(constraints.get("max")):
            return False, "value above max"

    return True, None


# ---------------------------------------------------------------------------
# Audit record (re-exported from audit.py for backward compat)
# ---------------------------------------------------------------------------


def append_audit_record(path: str, record: dict[str, Any]) -> None:
    """Deprecated shim.

    The chained audit log lives in :mod:`.audit` now. This function
    preserves the old surface (write one JSONL line) for any external
    caller that hasn't migrated yet. New callers should use
    :func:`audit.append_audit_record` directly — it signs + validates
    + has the persistent_notification fallback.
    """

    # Lazy import so this module stays importable in test environments
    # where audit.py's full deps aren't resolvable.
    from .audit import append_audit_record as _chained  # type: ignore

    return _chained(path, record)


# ---------------------------------------------------------------------------
# Confirmation flow (Gate D)
# ---------------------------------------------------------------------------


#: Default validity window for a confirmation code.
DEFAULT_CONFIRMATION_TTL_SEC = 5 * 60

#: Max failed code attempts before auto-rejection.
DEFAULT_CONFIRMATION_MAX_ATTEMPTS = 5

#: In-process lock guarding the pending-confirmations file.
_confirm_lock = threading.Lock()


@dataclass
class ConfirmationChallenge:
    confirmation_id: str
    code_hash: str
    code_plaintext: str  # only kept for return-to-caller; not persisted
    action_id: str
    params: dict[str, Any]
    actor: dict[str, Any]
    expires_at: str
    issued_at: str
    attempts_remaining: int
    status: str  # pending | confirmed | rejected | expired | blocked


def _hash_code(code: str) -> str:
    """Return a SHA-256 hex digest of ``code`` for at-rest storage."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _generate_code(length: int = 6) -> str:
    """Return a random numeric confirmation code (default 6 digits)."""
    if length < 4:
        length = 4
    if length > 12:
        length = 12
    upper = 10 ** length
    return f"{secrets.randbelow(upper):0{length}d}"


def _read_pending(path: str) -> list[dict[str, Any]]:
    """Return all pending confirmations from disk (most recent last)."""

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


def _write_pending(path: str, items: list[dict[str, Any]]) -> None:
    """Rewrite the pending-confirmations file with ``items`` (best-effort)."""

    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            for obj in items:
                f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")
        os.replace(tmp, path)
    except Exception:
        # Pending confirmations are best-effort persistence. The in-
        # memory copy + audit log keep the flow correct; if we can't
        # persist we'll just expire faster.
        pass


def _is_expired(challenge: dict[str, Any], now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    try:
        exp = datetime.fromisoformat(str(challenge.get("expires_at") or ""))
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return now >= exp
    except Exception:
        # Unparseable expiry → treat as expired (fail safe).
        return True


def request_confirmation(
    *,
    config_dir: str,
    action_id: str,
    params: dict[str, Any],
    actor: dict[str, Any],
    ttl_sec: int = DEFAULT_CONFIRMATION_TTL_SEC,
    max_attempts: int = DEFAULT_CONFIRMATION_MAX_ATTEMPTS,
) -> tuple[bool, str | None, dict[str, Any] | None]:
    """Issue a confirmation challenge for ``action_id``.

    Returns ``(True, None, challenge_dict)`` on success. The challenge
    dict contains the user-visible code, the confirmation_id, the
    expiry, and the echoed action body. The code's plaintext is also
    returned in ``challenge_dict["code"]`` — callers MUST surface it to
    the user (e.g. via ``persistent_notification``) and never log it
    unmasked.
    """

    code = _generate_code(6)
    challenge_id = secrets.token_urlsafe(16)
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(seconds=int(ttl_sec))).isoformat()

    challenge = {
        "confirmation_id": challenge_id,
        "code_hash": _hash_code(code),
        "action_id": str(action_id),
        "params": dict(params or {}),
        "actor": dict(actor),
        "issued_at": now.isoformat(),
        "expires_at": expires_at,
        "attempts_remaining": int(max_attempts),
        "status": "pending",
    }

    with _confirm_lock:
        path = pending_confirmations_path(config_dir)
        items = _read_pending(path)
        # Garbage-collect any expired/rejected items while we're here.
        now_dt = datetime.now(timezone.utc)
        items = [c for c in items if c.get("status") == "pending" and not _is_expired(c, now_dt)]
        items.append(challenge)
        _write_pending(path, items)

    out = dict(challenge)
    out["code"] = code  # plaintext only for the caller — not persisted
    out["expires_in_sec"] = int(ttl_sec)
    return True, None, out


def _find_challenge(items: list[dict[str, Any]], confirmation_id: str) -> dict[str, Any] | None:
    for c in items:
        if str(c.get("confirmation_id") or "") == str(confirmation_id):
            return c
    return None


def _settle_challenge(
    *,
    config_dir: str,
    confirmation_id: str,
    new_status: str,
    reason_suffix: str | None = None,
) -> tuple[bool, str | None]:
    """Update a pending challenge to a terminal state and persist."""

    with _confirm_lock:
        path = pending_confirmations_path(config_dir)
        items = _read_pending(path)
        target = _find_challenge(items, confirmation_id)
        if not target:
            return False, "unknown_confirmation_id"
        target["status"] = str(new_status)
        if reason_suffix:
            target["reason"] = str(reason_suffix)
        # Filter to terminal states only — we don't keep settled
        # confirmations around in the pending file.
        items = [
            c for c in items
            if c.get("status") == "pending" and not _is_expired(c)
        ]
        _write_pending(path, items)
        return True, None


def confirm_action(
    *,
    config_dir: str,
    confirmation_id: str,
    code: str,
) -> tuple[bool, str, dict[str, Any] | None]:
    """Attempt to confirm a previously-issued challenge.

    Returns ``(True, status, challenge_dict)`` on a state transition
    (``status`` in ``allowed|rejected|expired|blocked``) or
    ``(False, "<error>", None)`` on input errors (unknown id, wrong
    code, etc.). The caller is responsible for translating the status
    to the appropriate HTTP response and writing the audit record.
    """

    now_dt = datetime.now(timezone.utc)

    with _confirm_lock:
        path = pending_confirmations_path(config_dir)
        items = _read_pending(path)
        target = _find_challenge(items, confirmation_id)
        if not target:
            return False, "unknown_confirmation_id", None

        if target.get("status") != "pending":
            return False, f"already_{target.get('status')}", None

        if _is_expired(target, now_dt):
            target["status"] = "expired"
            items = [c for c in items if c.get("status") == "pending" and not _is_expired(c)]
            _write_pending(path, items)
            return True, "expired", target

        remaining = int(target.get("attempts_remaining") or 0)
        if remaining <= 0:
            target["status"] = "blocked"
            items = [c for c in items if c.get("status") == "pending" and not _is_expired(c)]
            _write_pending(path, items)
            return True, "blocked", target

        if _hash_code(str(code)) != str(target.get("code_hash") or ""):
            target["attempts_remaining"] = max(0, remaining - 1)
            # If we just used the last attempt, transition to blocked.
            if target["attempts_remaining"] <= 0:
                target["status"] = "blocked"
                items = [c for c in items if c.get("status") == "pending" and not _is_expired(c)]
                _write_pending(path, items)
                return True, "blocked", target
            # Wrong code but still have attempts → leave pending, signal reject.
            _write_pending(path, items)
            return True, "rejected", target

        # Correct code → allowed.
        target["status"] = "confirmed"
        items = [c for c in items if c.get("status") == "pending" and not _is_expired(c)]
        _write_pending(path, items)
        return True, "allowed", target


def get_pending_confirmation(config_dir: str, confirmation_id: str) -> dict[str, Any] | None:
    """Return the (current) pending challenge for ``confirmation_id`` or None."""

    items = _read_pending(pending_confirmations_path(config_dir))
    target = _find_challenge(items, confirmation_id)
    if target and target.get("status") == "pending" and not _is_expired(target):
        return target
    return None


def reject_confirmation(*, config_dir: str, confirmation_id: str) -> tuple[bool, str]:
    """Mark a pending challenge as user-rejected (no audit-record side effects here).

    The caller (HTTP view) is responsible for writing the audit record
    after this returns.
    """

    ok, _err = _settle_challenge(
        config_dir=config_dir,
        confirmation_id=confirmation_id,
        new_status="rejected",
        reason_suffix="user_rejected",
    )
    return (True, "rejected") if ok else (False, "unknown_confirmation_id")


def expire_overdue_confirmations(config_dir: str, now: datetime | None = None) -> int:
    """Transition every overdue pending challenge to ``expired``. Returns the count."""

    now = now or datetime.now(timezone.utc)
    changed = 0
    with _confirm_lock:
        path = pending_confirmations_path(config_dir)
        items = _read_pending(path)
        for c in items:
            if c.get("status") == "pending" and _is_expired(c, now):
                c["status"] = "expired"
                changed += 1
        items = [c for c in items if c.get("status") == "pending" and not _is_expired(c)]
        _write_pending(path, items)
    return changed


__all__ = [
    "ActionResult",
    "DEFAULT_CONFIRMATION_TTL_SEC",
    "DEFAULT_CONFIRMATION_MAX_ATTEMPTS",
    "allowlist_path",
    "auditlog_path",
    "pending_confirmations_path",
    "load_allowlist_yaml",
    "find_action",
    "action_requires_confirmation",
    "validate_constraints",
    "append_audit_record",
    "request_confirmation",
    "confirm_action",
    "get_pending_confirmation",
    "reject_confirmation",
    "expire_overdue_confirmations",
    "ConfirmationChallenge",
]