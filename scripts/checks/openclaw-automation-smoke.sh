#!/usr/bin/env bash
# OpenClaw automation apply: smoke check (slice #24).
#
# Validates that the Wave 2 #24 slice ("Automations via text/LLM/MCP — OpenClaw
# API v2 apply bridge") is wired end-to-end on disk:
#
#   1) homeassistant/custom_components/roamcore/automation_intents.py exports
#      SUPPORTED_INTENTS containing the four intent types: set_mode,
#      apply_mode, set_helper, run_script.
#
#   2) homeassistant/custom_components/roamcore/openclaw_view.py defines the
#      OpenClawAutomationApplyView class AND it is registered in
#      homeassistant/custom_components/roamcore/__init__.py via
#      hass.http.register_view(OpenClawAutomationApplyView(...).
#
#   3) The new unittest file runs and all tests pass.
#
#   4) scripts/check.sh invokes this smoke check via
#      openclaw-automation-smoke.
#
# This check does NOT touch a live HA instance; it only inspects files and
# runs the pure-Python test suite.
# Wired into scripts/check.sh --core-only after the mode-builder smoke.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
FAIL=0

fail() { echo "ERROR: $*" >&2; FAIL=1; }
ok()   { echo "  ✓ $*"; }

# --- 1) automation_intents.py exports SUPPORTED_INTENTS with all 4 types ---
INTENTS_PY="homeassistant/custom_components/roamcore/automation_intents.py"
if [ ! -f "$INTENTS_PY" ]; then
  fail "missing $INTENTS_PY"
else
  ok "found $INTENTS_PY"
  if "$PYTHON_BIN" - "$INTENTS_PY" <<'PY' >/dev/null 2>&1
import importlib.util, sys, os
spec = importlib.util.spec_from_file_location("automation_intents_under_test", sys.argv[1])
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)
required = {"set_mode", "apply_mode", "set_helper", "run_script"}
missing = required - set(m.SUPPORTED_INTENTS.keys())
if missing:
    raise SystemExit(f"missing intents: {sorted(missing)}")
for t in ("set_helper", "run_script"):
    meta = m.SUPPORTED_INTENTS[t]
    if "params" not in meta or "description" not in meta:
        raise SystemExit(f"intent {t} missing params/description")
PY
  then
    ok "SUPPORTED_INTENTS contains set_mode, apply_mode, set_helper, run_script"
  else
    fail "SUPPORTED_INTENTS does NOT contain all 4 intent types"
  fi
fi

# --- 2) openclaw_view.py defines + registers OpenClawAutomationApplyView ---
VIEW_PY="homeassistant/custom_components/roamcore/openclaw_view.py"
INIT_PY="homeassistant/custom_components/roamcore/__init__.py"
if [ ! -f "$VIEW_PY" ]; then
  fail "missing $VIEW_PY"
else
  ok "found $VIEW_PY"
  if grep -q "class OpenClawAutomationApplyView" "$VIEW_PY"; then
    ok "OpenClawAutomationApplyView class declared in $VIEW_PY"
  else
    fail "OpenClawAutomationApplyView class NOT declared in $VIEW_PY"
  fi
  if grep -q 'url = "/api/roamcore/openclaw/automation/apply"' "$VIEW_PY"; then
    ok "apply view URL is /api/roamcore/openclaw/automation/apply"
  else
    fail "apply view URL NOT /api/roamcore/openclaw/automation/apply"
  fi
  if grep -q 'name = "api:roamcore_openclaw_automation_apply"' "$VIEW_PY"; then
    ok "apply view name is api:roamcore_openclaw_automation_apply"
  else
    fail "apply view name NOT api:roamcore_openclaw_automation_apply"
  fi
fi

if [ ! -f "$INIT_PY" ]; then
  fail "missing $INIT_PY"
else
  ok "found $INIT_PY"
  if grep -q "hass.http.register_view(OpenClawAutomationApplyView" "$INIT_PY"; then
    ok "OpenClawAutomationApplyView registered in $INIT_PY"
  else
    fail "OpenClawAutomationApplyView NOT registered in $INIT_PY"
  fi
fi

# --- 3) Run the new unittest file ---
TEST_FILE="homeassistant/custom_components/roamcore/tests/test_automation_intents.py"
if [ ! -f "$TEST_FILE" ]; then
  fail "missing $TEST_FILE"
else
  ok "found $TEST_FILE"
  # Prefer the project's existing venv if present; else fall back to python3.
  # We resolve the venv path before cd'ing into homeassistant so the relative
  # ".venv/bin/python" path still works.
  if [ -x "$ROOT_DIR/.venv/bin/python" ]; then
    PY_FOR_TEST="$ROOT_DIR/.venv/bin/python"
  else
    PY_FOR_TEST="$PYTHON_BIN"
  fi
  ok "running: (cd homeassistant && $PY_FOR_TEST -m unittest custom_components.roamcore.tests.test_automation_intents -v)"
  if (cd homeassistant && "$PY_FOR_TEST" -m unittest custom_components.roamcore.tests.test_automation_intents -v) >/tmp/openclaw_automation_smoke.log 2>&1; then
    last=$(tail -n 1 /tmp/openclaw_automation_smoke.log)
    if echo "$last" | grep -q "^OK"; then
      ok "unit tests passed: $last"
    else
      # unittest may print "Ran N tests in ...s" + "OK" on the same/different line
      if grep -q "^OK$" /tmp/openclaw_automation_smoke.log; then
        ok "unit tests passed"
      else
        fail "unit tests did not finish with OK; see /tmp/openclaw_automation_smoke.log"
        tail -n 20 /tmp/openclaw_automation_smoke.log >&2 || true
      fi
    fi
  else
    fail "unit tests FAILED; see /tmp/openclaw_automation_smoke.log"
    tail -n 40 /tmp/openclaw_automation_smoke.log >&2 || true
  fi
fi

# --- 4) scripts/check.sh invokes this smoke check ---
CHECK_SH="scripts/check.sh"
if [ ! -f "$CHECK_SH" ]; then
  fail "missing $CHECK_SH"
else
  ok "found $CHECK_SH"
  if grep -q "openclaw-automation-smoke" "$CHECK_SH"; then
    ok "scripts/check.sh invokes openclaw-automation-smoke"
  else
    fail "scripts/check.sh does NOT invoke openclaw-automation-smoke"
  fi
fi

echo
if [ "$FAIL" -eq 0 ]; then
  echo "✓ OpenClaw automation apply smoke check passed (slice #24)"
  exit 0
else
  echo "✗ OpenClaw automation apply smoke check FAILED" >&2
  exit 1
fi