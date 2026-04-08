from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
import re
from typing import Any


@dataclass
class ActionResult:
    ok: bool
    error: str | None = None
    details: dict[str, Any] | None = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def allowlist_path(config_dir: str) -> str:
    return os.path.join(config_dir, ".roamcore", "agent_allowlist.yaml")


def auditlog_path(config_dir: str) -> str:
    return os.path.join(config_dir, ".roamcore", "agent_action_log.jsonl")


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


def append_audit_record(path: str, record: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, sort_keys=False)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

