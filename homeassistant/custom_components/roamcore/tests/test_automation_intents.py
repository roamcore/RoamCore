"""Unit tests for the RoamCore automation intents module (slice #24).

Run from `homeassistant/` with:
    python -m unittest custom_components.roamcore.tests.test_automation_intents -v

These tests are pure-Python (no HA hass fixture) so they can run anywhere
PyYAML is available. The integration's `actions.py` module is imported
lazily inside the helper to keep the dependency surface tight.
"""

from __future__ import annotations

import os
import sys
import unittest

HERE = os.path.dirname(__file__)
PKG_PARENT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if PKG_PARENT not in sys.path:
    sys.path.insert(0, PKG_PARENT)

from custom_components.roamcore.automation_intents import (  # noqa: E402
    INTENT_CONTRACT,
    SUPPORTED_INTENTS,
    apply_intent,
    validate_intent,
)


# A minimal allowlist that covers every intent type the apply helper maps to.
ALLOWLIST = {
    "version": 1,
    "actions": [
        {
            "id": "set_helper:input_select.rc_mode",
            "kind": "set_helper",
            "target": {"entity_id": "input_select.rc_mode"},
            "constraints": {"enum": ["auto", "travel", "camp", "stealth", "off"]},
        },
        {
            "id": "set_helper:input_boolean.rc_mode_stealth",
            "kind": "set_helper",
            "target": {"entity_id": "input_boolean.rc_mode_stealth"},
        },
        {
            "id": "set_helper:input_number.rc_temp_target",
            "kind": "set_helper",
            "target": {"entity_id": "input_number.rc_temp_target"},
        },
        {
            "id": "run_script:script.rc_mode_apply",
            "kind": "run_script",
            "target": {"entity_id": "script.rc_mode_apply"},
        },
        {
            "id": "run_script:script.rc_trip_wrapped_run",
            "kind": "run_script",
            "target": {"entity_id": "script.rc_trip_wrapped_run"},
        },
    ],
}


class TestSchema(unittest.TestCase):
    """The schema must be discoverable and stable."""

    def test_contract_shape(self):
        self.assertIn("name", INTENT_CONTRACT)
        self.assertIn("version", INTENT_CONTRACT)
        self.assertEqual(INTENT_CONTRACT["name"], "roamcore_automation_intents")

    def test_supported_intents_keys(self):
        # All four intent types must be discoverable via the schema.
        for t in ("set_mode", "apply_mode", "set_helper", "run_script"):
            self.assertIn(t, SUPPORTED_INTENTS, f"missing intent type: {t}")
            meta = SUPPORTED_INTENTS[t]
            self.assertIn("description", meta)
            self.assertIn("params", meta)

    def test_set_helper_params_shape(self):
        p = SUPPORTED_INTENTS["set_helper"]["params"]
        self.assertIn("entity_id", p)
        self.assertIn("value", p)

    def test_run_script_params_shape(self):
        p = SUPPORTED_INTENTS["run_script"]["params"]
        self.assertIn("entity_id", p)


class TestValidateSetMode(unittest.TestCase):
    def test_happy(self):
        r = validate_intent({"type": "set_mode", "params": {"mode": "camp"}})
        self.assertTrue(r.ok)
        self.assertEqual(r.normalized, {"type": "set_mode", "params": {"mode": "camp"}})

    def test_invalid_mode(self):
        r = validate_intent({"type": "set_mode", "params": {"mode": "nope"}})
        self.assertFalse(r.ok)
        self.assertEqual(r.error, "invalid_mode")

    def test_missing_mode(self):
        r = validate_intent({"type": "set_mode", "params": {}})
        self.assertFalse(r.ok)
        self.assertEqual(r.error, "missing_mode")

    def test_mode_not_string(self):
        r = validate_intent({"type": "set_mode", "params": {"mode": 7}})
        self.assertFalse(r.ok)
        self.assertEqual(r.error, "missing_mode")


class TestValidateApplyMode(unittest.TestCase):
    def test_happy(self):
        r = validate_intent({"type": "apply_mode", "params": {}})
        self.assertTrue(r.ok)
        self.assertEqual(r.normalized, {"type": "apply_mode", "params": {}})

    def test_extras_warn(self):
        r = validate_intent({"type": "apply_mode", "params": {"foo": "bar"}})
        self.assertTrue(r.ok)
        self.assertIn("params_ignored", r.warnings or [])

    def test_missing_type(self):
        r = validate_intent({})
        self.assertFalse(r.ok)
        self.assertEqual(r.error, "missing_type")

    def test_unsupported_type(self):
        r = validate_intent({"type": "nope", "params": {}})
        self.assertFalse(r.ok)
        self.assertEqual(r.error, "unsupported_type")


class TestValidateSetHelper(unittest.TestCase):
    def test_happy_text(self):
        r = validate_intent(
            {"type": "set_helper", "params": {"entity_id": "input_text.rc_map_style_url", "value": "https://x"}}
        )
        self.assertTrue(r.ok)
        self.assertEqual(r.normalized["params"]["entity_id"], "input_text.rc_map_style_url")

    def test_happy_number(self):
        r = validate_intent(
            {"type": "set_helper", "params": {"entity_id": "input_number.rc_temp_target", "value": 22}}
        )
        self.assertTrue(r.ok)

    def test_happy_boolean(self):
        r = validate_intent(
            {"type": "set_helper", "params": {"entity_id": "input_boolean.rc_mode_stealth", "value": True}}
        )
        self.assertTrue(r.ok)

    def test_missing_entity_id(self):
        r = validate_intent({"type": "set_helper", "params": {"value": "x"}})
        self.assertFalse(r.ok)
        self.assertEqual(r.error, "missing_entity_id")

    def test_not_input_helper(self):
        r = validate_intent({"type": "set_helper", "params": {"entity_id": "script.rc_foo", "value": "x"}})
        self.assertFalse(r.ok)
        self.assertEqual(r.error, "entity_id_not_input_helper")

    def test_unsupported_domain(self):
        r = validate_intent({"type": "set_helper", "params": {"entity_id": "input_datetime.rc_x", "value": "x"}})
        self.assertFalse(r.ok)
        self.assertEqual(r.error, "unsupported_helper_domain")

    def test_bad_value_type_number_for_text(self):
        r = validate_intent(
            {"type": "set_helper", "params": {"entity_id": "input_text.rc_x", "value": 7}}
        )
        self.assertFalse(r.ok)
        self.assertEqual(r.error, "invalid_value_type")

    def test_bad_value_type_string_for_number(self):
        r = validate_intent(
            {"type": "set_helper", "params": {"entity_id": "input_number.rc_x", "value": "abc"}}
        )
        self.assertFalse(r.ok)
        self.assertEqual(r.error, "invalid_value_type")

    def test_bad_value_type_string_for_bool(self):
        r = validate_intent(
            {"type": "set_helper", "params": {"entity_id": "input_boolean.rc_x", "value": "on"}}
        )
        self.assertFalse(r.ok)
        self.assertEqual(r.error, "invalid_value_type")


class TestValidateRunScript(unittest.TestCase):
    def test_happy(self):
        r = validate_intent({"type": "run_script", "params": {"entity_id": "script.rc_trip_wrapped_run"}})
        self.assertTrue(r.ok)
        self.assertEqual(r.normalized["params"]["entity_id"], "script.rc_trip_wrapped_run")

    def test_missing_entity_id(self):
        r = validate_intent({"type": "run_script", "params": {}})
        self.assertFalse(r.ok)
        self.assertEqual(r.error, "missing_entity_id")

    def test_wrong_domain(self):
        r = validate_intent({"type": "run_script", "params": {"entity_id": "input_boolean.rc_x"}})
        self.assertFalse(r.ok)
        self.assertEqual(r.error, "entity_id_not_script")

    def test_wrong_prefix(self):
        r = validate_intent({"type": "run_script", "params": {"entity_id": "script.foo"}})
        self.assertFalse(r.ok)
        self.assertEqual(r.error, "script_not_rc_prefixed")


class TestApplyIntentAllowlist(unittest.TestCase):
    """apply_intent must enforce the allowlist end-to-end."""

    def _executor_calls(self):
        calls: list[tuple[str, dict, str]] = []

        def _exec(action_id, args, reason):
            calls.append((action_id, args, reason))

        return calls, _exec

    def test_set_mode_allowlisted_passes_and_calls_executor(self):
        calls, exec_ = self._executor_calls()
        plan = apply_intent(
            {"type": "set_mode", "params": {"mode": "camp"}},
            allowlist=ALLOWLIST,
            executor=exec_,
        )
        self.assertTrue(plan["ok"], msg=str(plan))
        self.assertEqual(plan["action_id"], "set_helper:input_select.rc_mode")
        self.assertEqual(plan["args"], {"value": "camp"})
        self.assertEqual(plan["reason"], "openclaw_automation_apply")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "set_helper:input_select.rc_mode")

    def test_set_helper_allowlisted_passes_and_calls_executor(self):
        calls, exec_ = self._executor_calls()
        plan = apply_intent(
            {"type": "set_helper", "params": {"entity_id": "input_number.rc_temp_target", "value": 21}},
            allowlist=ALLOWLIST,
            executor=exec_,
        )
        self.assertTrue(plan["ok"], msg=str(plan))
        self.assertEqual(plan["action_id"], "set_helper:input_number.rc_temp_target")
        self.assertEqual(len(calls), 1)

    def test_run_script_allowlisted_passes_and_calls_executor(self):
        calls, exec_ = self._executor_calls()
        plan = apply_intent(
            {"type": "run_script", "params": {"entity_id": "script.rc_trip_wrapped_run"}},
            allowlist=ALLOWLIST,
            executor=exec_,
        )
        self.assertTrue(plan["ok"], msg=str(plan))
        self.assertEqual(plan["action_id"], "run_script:script.rc_trip_wrapped_run")
        self.assertEqual(plan["args"], {})
        self.assertEqual(len(calls), 1)

    def test_non_allowlisted_set_helper_rejected(self):
        calls, exec_ = self._executor_calls()
        plan = apply_intent(
            {"type": "set_helper", "params": {"entity_id": "input_text.rc_unknown", "value": "x"}},
            allowlist=ALLOWLIST,
            executor=exec_,
        )
        self.assertFalse(plan["ok"])
        self.assertEqual(plan["error"], "action_not_allowlisted")
        # Executor must NOT have been invoked.
        self.assertEqual(len(calls), 0)

    def test_non_allowlisted_run_script_rejected(self):
        calls, exec_ = self._executor_calls()
        plan = apply_intent(
            {"type": "run_script", "params": {"entity_id": "script.rc_unknown"}},
            allowlist=ALLOWLIST,
            executor=exec_,
        )
        self.assertFalse(plan["ok"])
        self.assertEqual(plan["error"], "action_not_allowlisted")
        self.assertEqual(len(calls), 0)

    def test_missing_entity_rejected_via_validator(self):
        calls, exec_ = self._executor_calls()
        plan = apply_intent(
            {"type": "set_helper", "params": {"entity_id": "", "value": "x"}},
            allowlist=ALLOWLIST,
            executor=exec_,
        )
        self.assertFalse(plan["ok"])
        self.assertEqual(plan["error"], "missing_entity_id")
        self.assertEqual(len(calls), 0)

    def test_bad_value_rejected_via_validator(self):
        calls, exec_ = self._executor_calls()
        plan = apply_intent(
            {"type": "set_helper", "params": {"entity_id": "input_boolean.rc_mode_stealth", "value": "on"}},
            allowlist=ALLOWLIST,
            executor=exec_,
        )
        self.assertFalse(plan["ok"])
        self.assertEqual(plan["error"], "invalid_value_type")
        self.assertEqual(len(calls), 0)

    def test_empty_allowlist_blocks_everything(self):
        calls, exec_ = self._executor_calls()
        for intent, expected_action in (
            ({"type": "set_mode", "params": {"mode": "auto"}}, "set_helper:input_select.rc_mode"),
            ({"type": "set_helper", "params": {"entity_id": "input_text.rc_x", "value": "x"}}, "set_helper:input_text.rc_x"),
            ({"type": "run_script", "params": {"entity_id": "script.rc_mode_apply"}}, "run_script:script.rc_mode_apply"),
        ):
            plan = apply_intent(intent, allowlist={"actions": []}, executor=exec_)
            self.assertFalse(plan["ok"], msg=f"intent {intent} unexpectedly passed: {plan}")
            self.assertEqual(plan["error"], "action_not_allowlisted")
        self.assertEqual(len(calls), 0)

    def test_apply_mode_falls_through_to_run_script_when_allowlisted(self):
        calls, exec_ = self._executor_calls()
        plan = apply_intent(
            {"type": "apply_mode", "params": {}},
            allowlist=ALLOWLIST,
            executor=exec_,
        )
        self.assertTrue(plan["ok"], msg=str(plan))
        self.assertEqual(plan["action_id"], "run_script:script.rc_mode_apply")
        self.assertEqual(len(calls), 1)

    def test_executor_exception_surfaces_as_error(self):
        def _exec(action_id, args, reason):
            raise RuntimeError("boom")

        plan = apply_intent(
            {"type": "set_mode", "params": {"mode": "auto"}},
            allowlist=ALLOWLIST,
            executor=_exec,
        )
        self.assertFalse(plan["ok"])
        self.assertTrue(str(plan["error"]).startswith("executor_error"))


if __name__ == "__main__":
    unittest.main()