"""RoamCore: automation intents (read-only, validated).

This module is the building block of the planned "Automations builder via
text/LLM/MCP" project item.

Principles:
- Validation first: accept an intent payload and return a deterministic,
  structured result.
- No execution: this module does *not* call Home Assistant services.
- Small surface area: keep the schema intentionally tiny and stable.

Slice #24 adds the apply_intent() helper that maps validated intents to the
allowlisted executor (`roamcore.action_execute`). The helper is intentionally
pure-Python (no hass dependency) so the module stays unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


INTENT_CONTRACT = {"name": "roamcore_automation_intents", "version": 2}


SUPPORTED_INTENTS: Dict[str, Dict[str, Any]] = {
    "set_mode": {
        "description": "Set the current RoamCore mode (does not apply it).",
        "params": {
            "mode": {
                "type": "string",
                "enum": ["auto", "travel", "camp", "stealth", "off"],
            }
        },
    },
    "apply_mode": {
        "description": "Apply the currently selected RoamCore mode (scaffold).",
        "params": {},
    },
    "set_helper": {
        "description": "Set an allowlisted input_* helper value.",
        "params": {
            "entity_id": {
                "type": "string",
                "description": "Helper entity id (must start with 'input_').",
            },
            "value": {
                "type": "string|number|boolean",
                "description": "Value to set (type depends on helper domain).",
            },
        },
    },
    "run_script": {
        "description": "Run an allowlisted script.rc_* script.",
        "params": {
            "entity_id": {
                "type": "string",
                "description": "Script entity id (must start with 'script.rc_').",
            },
        },
    },
}


@dataclass
class ValidationResult:
    ok: bool
    error: Optional[str] = None
    normalized: Optional[Dict[str, Any]] = None
    warnings: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": bool(self.ok),
            "error": self.error,
            "normalized": self.normalized,
            "warnings": self.warnings or [],
        }


def validate_intent(payload: Any) -> ValidationResult:
    """Validate a proposed automation intent.

    Expected payload shape:
      {"type": "set_mode", "params": { ... }}
    """

    if not isinstance(payload, dict):
        return ValidationResult(ok=False, error="invalid_payload")

    intent_type = payload.get("type")
    params = payload.get("params")

    if not isinstance(intent_type, str) or not intent_type:
        return ValidationResult(ok=False, error="missing_type")

    meta = SUPPORTED_INTENTS.get(intent_type)
    if meta is None:
        return ValidationResult(ok=False, error="unsupported_type")

    if params is None:
        params = {}
    if not isinstance(params, dict):
        return ValidationResult(ok=False, error="invalid_params")

    # Intent-specific validation
    if intent_type == "set_mode":
        mode = params.get("mode")
        if not isinstance(mode, str) or not mode:
            return ValidationResult(ok=False, error="missing_mode")
        mode = mode.strip().lower()
        allowed = set(meta["params"]["mode"]["enum"])
        if mode not in allowed:
            return ValidationResult(ok=False, error="invalid_mode")
        return ValidationResult(ok=True, normalized={"type": "set_mode", "params": {"mode": mode}})

    if intent_type == "apply_mode":
        # No params; ignore any extras but warn.
        warnings: List[str] = []
        if params:
            warnings.append("params_ignored")
        return ValidationResult(ok=True, normalized={"type": "apply_mode", "params": {}}, warnings=warnings)

    if intent_type == "set_helper":
        entity_id = params.get("entity_id")
        value = params.get("value")

        if not isinstance(entity_id, str) or not entity_id:
            return ValidationResult(ok=False, error="missing_entity_id")
        if "." not in entity_id:
            return ValidationResult(ok=False, error="invalid_entity_id")
        domain = entity_id.split(".", 1)[0]
        if not domain.startswith("input_"):
            return ValidationResult(ok=False, error="entity_id_not_input_helper")
        # Restrict to the four HA helper domains the executor supports.
        if domain not in ("input_text", "input_number", "input_select", "input_boolean"):
            return ValidationResult(ok=False, error="unsupported_helper_domain")

        if "value" not in params:
            return ValidationResult(ok=False, error="missing_value")

        # Value type depends on the helper domain. We do not check the allowlist
        # here; apply_intent does that (it needs the loaded allowlist).
        if domain in ("input_text", "input_select"):
            if not isinstance(value, str):
                return ValidationResult(ok=False, error="invalid_value_type")
        elif domain == "input_number":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return ValidationResult(ok=False, error="invalid_value_type")
        elif domain == "input_boolean":
            if not isinstance(value, bool):
                return ValidationResult(ok=False, error="invalid_value_type")

        return ValidationResult(
            ok=True,
            normalized={"type": "set_helper", "params": {"entity_id": entity_id, "value": value}},
        )

    if intent_type == "run_script":
        entity_id = params.get("entity_id")
        if not isinstance(entity_id, str) or not entity_id:
            return ValidationResult(ok=False, error="missing_entity_id")
        if "." not in entity_id:
            return ValidationResult(ok=False, error="invalid_entity_id")
        domain, _, object_id = entity_id.partition(".")
        if domain != "script":
            return ValidationResult(ok=False, error="entity_id_not_script")
        if not object_id.startswith("rc_"):
            return ValidationResult(ok=False, error="script_not_rc_prefixed")

        return ValidationResult(
            ok=True,
            normalized={"type": "run_script", "params": {"entity_id": entity_id}},
        )

    # Should never happen due to SUPPORTED_INTENTS check.
    return ValidationResult(ok=False, error="internal_error")


# ---------------------------------------------------------------------------
# Apply-intent helper (slice #24)
#
# apply_intent() is intentionally pure-Python:
#   - It validates the intent with validate_intent() (cheap, no I/O).
#   - It cross-checks the (entity_id, kind) tuple against the loaded
#     allowlist policy (the same one the roamcore.action_execute service
#     reads).
#   - It returns a plan describing which action_execute call the caller
#     should make. We do *not* invoke any Home Assistant service from
#     here so the module stays unit-testable with no hass fixture.
# ---------------------------------------------------------------------------


def _entity_id_in_allowlist(policy: Any, entity_id: str, kind: str) -> bool:
    """Return True if any allowlisted action of `kind` targets `entity_id`."""

    if not isinstance(policy, dict):
        return False
    actions = policy.get("actions") or []
    if not isinstance(actions, list):
        return False
    for a in actions:
        if not isinstance(a, dict):
            continue
        if str(a.get("kind") or "") != kind:
            continue
        target = a.get("target") or {}
        teid = target.get("entity_id")
        if isinstance(teid, str) and teid == entity_id:
            return True
        if isinstance(teid, list) and entity_id in [str(x) for x in teid]:
            return True
    return False


def apply_intent(
    payload: Any,
    *,
    allowlist: Any,
    executor: Optional[Any] = None,
) -> Dict[str, Any]:
    """Validate an intent + return an action_execute plan.

    Args:
        payload: the intent payload (same shape validate_intent accepts).
        allowlist: the parsed allowlist policy dict (from actions.load_allowlist_yaml).
        executor: optional callable (action_id, args, reason) -> None. If provided
                  AND validation passes, it is invoked with the derived plan.
                  The executor is wired only at the HTTP layer; this module
                  keeps it optional so unit tests can stay pure.

    Returns:
        A dict with:
          - ok (bool)
          - error (str|None)
          - contract (dict)
          - intent (dict|None) — the normalized intent
          - action_id (str|None) — the action_id to pass to action_execute
          - args (dict|None) — the args to pass to action_execute
          - reason (str) — fixed string "openclaw_automation_apply"
          - executor_result (Any|None) — the executor() return value, when invoked
    """

    base = {
        "ok": False,
        "error": None,
        "contract": INTENT_CONTRACT,
        "intent": None,
        "action_id": None,
        "args": None,
        "reason": "openclaw_automation_apply",
        "executor_result": None,
    }

    res = validate_intent(payload)
    if not res.ok:
        base["error"] = res.error
        return base

    intent = res.normalized or {}
    intent_type = intent.get("type")
    params = intent.get("params") or {}

    # Map intent → (action_id, args) via the allowlist.
    if intent_type == "set_mode":
        # Keep the existing convention: a virtual action_id the OpenClaw
        # view resolves to a real set_helper call. The view layer handles
        # the actual mapping; here we just emit the canonical id.
        entity_id = "input_select.rc_mode"
        action_id = f"set_helper:{entity_id}"
        if not _entity_id_in_allowlist(allowlist, entity_id, "set_helper"):
            base["error"] = "action_not_allowlisted"
            return base
        args = {"value": params.get("mode")}

    elif intent_type == "set_helper":
        entity_id = str(params.get("entity_id") or "")
        action_id = f"set_helper:{entity_id}"
        if not _entity_id_in_allowlist(allowlist, entity_id, "set_helper"):
            base["error"] = "action_not_allowlisted"
            return base
        args = {"value": params.get("value")}

    elif intent_type == "run_script":
        entity_id = str(params.get("entity_id") or "")
        action_id = f"run_script:{entity_id}"
        if not _entity_id_in_allowlist(allowlist, entity_id, "run_script"):
            base["error"] = "action_not_allowlisted"
            return base
        args = {}

    elif intent_type == "apply_mode":
        # Scaffold: we don't ship an apply_mode action by default. Map it to
        # a known run_script entry if the user has allowlisted one; else fail.
        entity_id = "script.rc_mode_apply"
        action_id = f"run_script:{entity_id}"
        if not _entity_id_in_allowlist(allowlist, entity_id, "run_script"):
            base["error"] = "action_not_allowlisted"
            return base
        args = {}

    else:
        base["error"] = "unsupported_type"
        return base

    if executor is not None:
        try:
            base["executor_result"] = executor(action_id, args, base["reason"])
        except Exception as e:  # pragma: no cover - executor failures are surfaced as plan errors
            base["error"] = f"executor_error: {type(e).__name__}: {e}"
            return base

    base["ok"] = True
    base["intent"] = intent
    base["action_id"] = action_id
    base["args"] = args
    return base