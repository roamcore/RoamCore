"""RoamCore: automation intents (read-only, validated).

This module is the first building block of the planned "Automations builder via
text/LLM/MCP" project item.

Principles:
- Validation first: accept an intent payload and return a deterministic,
  structured result.
- No execution: this module does *not* call Home Assistant services.
- Small surface area: keep the schema intentionally tiny and stable.

Later, an allowlisted executor can map validated intents to a small set of
predefined HA scripts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


INTENT_CONTRACT = {"name": "roamcore_automation_intents", "version": 1}


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

    # Should never happen due to SUPPORTED_INTENTS check.
    return ValidationResult(ok=False, error="internal_error")

