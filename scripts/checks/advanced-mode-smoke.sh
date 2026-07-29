#!/usr/bin/env bash
# Advanced Mode smoke check (slice #25).
#
# Validates that the RoamCore Advanced Mode slice (#25) is wired
# end-to-end on disk:
#
#   1) `homeassistant/packages/roamcore_advanced_mode.yaml` declares:
#      - `input_boolean.rc_advanced_mode_enabled` (with initial: false)
#      - `binary_sensor.rc_advanced_mode`
#      - `script.rc_advanced_mode_engage` (writes the snapshot input_text)
#      - `script.rc_advanced_mode_disengage`
#      - `automation.rc_advanced_mode_engaged_audit`
#      - `automation.rc_advanced_mode_disengaged_audit`
#
#   2) `homeassistant/www/roamcore/roamcore-advanced-mode.js` exists,
#      parses cleanly (`node --check` preferred, stdlib regex fallback),
#      declares `class RoamCoreAdvancedModeCard` and registers
#      `customElements.define('roamcore-advanced-mode', ...)`.
#
#   3) `homeassistant/www/roamcore/roamcore-pages.js` references
#      `roamcore-advanced-mode`.
#
#   4) `docs/feature-checklist.md` §System UX row is flipped to `[x]`.
#
#   5) `docs/setup/advanced-mode.md` exists and mentions "engage",
#      "disengage", and "recover".
#
#   6) `scripts/check.sh` invokes this smoke check via
#      `advanced-mode-smoke`.
#
# This check does NOT touch a live HA instance; it only inspects files.
# Wired into `scripts/check.sh --core-only` immediately after the
# OpenClaw automation smoke check.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
FAIL=0

fail() { echo "ERROR: $*" >&2; FAIL=1; }
ok()   { echo "  ✓ $*"; }

# --- 1) Advanced mode YAML declarations ---
YAML_FILE="homeassistant/packages/roamcore_advanced_mode.yaml"
if [ ! -f "$YAML_FILE" ]; then
  fail "missing $YAML_FILE"
else
  ok "found $YAML_FILE"
  if "$PYTHON_BIN" - "$YAML_FILE" <<'PY' >/dev/null 2>&1
import sys, yaml
d = yaml.safe_load(open(sys.argv[1], "r", encoding="utf-8"))

# 1a. input_boolean.rc_advanced_mode_enabled with initial: false
ib = (d.get("input_boolean") or {}).get("rc_advanced_mode_enabled")
if not ib:
    raise SystemExit("input_boolean.rc_advanced_mode_enabled missing")
if not bool(ib.get("initial", False)) is False and ib.get("initial") is not False:
    # initial should be False (off)
    if ib.get("initial") not in (False, "false", "off"):
        raise SystemExit(f"input_boolean.rc_advanced_mode_enabled.initial must be false (got {ib.get('initial')!r})")

# 1b. template binary_sensor.rc_advanced_mode
template = d.get("template") or []
bs_found = False
for entry in template:
    for bs in (entry.get("binary_sensor") or []):
        if bs.get("unique_id") == "rc_advanced_mode":
            bs_found = True
            break
    if bs_found:
        break
if not bs_found:
    raise SystemExit("binary_sensor.rc_advanced_mode (template) missing")

# 1c. script.rc_advanced_mode_engage + script.rc_advanced_mode_disengage
scripts = d.get("script") or {}
if "rc_advanced_mode_engage" not in scripts:
    raise SystemExit("script.rc_advanced_mode_engage missing")
if "rc_advanced_mode_disengage" not in scripts:
    raise SystemExit("script.rc_advanced_mode_disengage missing")

# The engage script must write input_text.rc_advanced_mode_last_engaged_state.
engage_seq = scripts["rc_advanced_mode_engage"].get("sequence") or []
wrote_snapshot = False
for step in engage_seq:
    target = step.get("target") or {}
    if not isinstance(target, dict):
        continue
    ents = target.get("entity_id")
    if not ents:
        continue
    if isinstance(ents, str):
        ents = [ents]
    if any(e == "input_text.rc_advanced_mode_last_engaged_state" for e in ents):
        wrote_snapshot = True
        break
if not wrote_snapshot:
    raise SystemExit("script.rc_advanced_mode_engage must write input_text.rc_advanced_mode_last_engaged_state")

# 1d. automations: engaged + disengaged audit
auto = d.get("automation") or []
auto_ids = [a.get("id") for a in auto]
if "rc_advanced_mode_engaged_audit" not in auto_ids:
    raise SystemExit("automation.rc_advanced_mode_engaged_audit missing")
if "rc_advanced_mode_disengaged_audit" not in auto_ids:
    raise SystemExit("automation.rc_advanced_mode_disengaged_audit missing")
PY
  then
    ok "roamcore_advanced_mode.yaml declares boolean(initial=off), binary_sensor, both scripts (engage writes the snapshot input_text), both audit automations"
  else
    fail "roamcore_advanced_mode.yaml missing one or more required declarations"
  fi
fi

# --- 2) Advanced mode JS card exists + parses cleanly + class + registration ---
JS_FILE="homeassistant/www/roamcore/roamcore-advanced-mode.js"
if [ ! -f "$JS_FILE" ]; then
  fail "missing $JS_FILE"
else
  ok "found $JS_FILE"
  if command -v node >/dev/null 2>&1; then
    if node --check "$JS_FILE" >/dev/null 2>&1; then
      ok "node --check passed for $JS_FILE"
    else
      fail "node --check FAILED for $JS_FILE"
    fi
  else
    # Fallback: balanced braces / parens / brackets heuristic.
    if "$PYTHON_BIN" - "$JS_FILE" <<'PY' >/dev/null 2>&1
import sys, re
src = open(sys.argv[1], "r", encoding="utf-8").read()
no_strings = re.sub(r"'(?:\\.|[^'\\])*'", "''", src)
no_strings = re.sub(r'"(?:\\.|[^"\\])*"', '""', no_strings)
no_strings = re.sub(r"`(?:\\.|[^`\\])*`", "``", no_strings)
no_strings = re.sub(r"//[^\n]*", "", no_strings)
no_strings = re.sub(r"/\*.*?\*/", "", no_strings, flags=re.S)
def bal(s, op, cl):
    depth = 0
    for ch in s:
        if ch == op: depth += 1
        elif ch == cl: depth -= 1
        if depth < 0: return False
    return depth == 0
sys.exit(0 if (bal(no_strings, "{", "}") and bal(no_strings, "(", ")") and bal(no_strings, "[", "]")) else 1)
PY
    then
      ok "stdlib brace-balance heuristic passed for $JS_FILE"
    else
      fail "stdlib brace-balance heuristic FAILED for $JS_FILE"
    fi
  fi

  if grep -q "class RoamCoreAdvancedModeCard" "$JS_FILE"; then
    ok "RoamCoreAdvancedModeCard class declared in $JS_FILE"
  else
    fail "RoamCoreAdvancedModeCard class NOT declared in $JS_FILE"
  fi
  if grep -q "customElements.define" "$JS_FILE" && grep -q "'roamcore-advanced-mode'" "$JS_FILE"; then
    ok "custom element 'roamcore-advanced-mode' registered in $JS_FILE"
  else
    fail "custom element 'roamcore-advanced-mode' NOT registered in $JS_FILE"
  fi
fi

# --- 3) pages.js references the advanced-mode card ---
PAGES_JS="homeassistant/www/roamcore/roamcore-pages.js"
if [ ! -f "$PAGES_JS" ]; then
  fail "missing $PAGES_JS"
else
  ok "found $PAGES_JS"
  if grep -q "roamcore-advanced-mode" "$PAGES_JS"; then
    ok "roamcore-advanced-mode referenced in pages.js"
  else
    fail "roamcore-advanced-mode NOT referenced in pages.js"
  fi
fi

# --- 4) Feature checklist row flipped to [x] ---
CHECKLIST="docs/feature-checklist.md"
if [ ! -f "$CHECKLIST" ]; then
  fail "missing $CHECKLIST"
else
  ok "found $CHECKLIST"
  if grep -q "^- \[x\] Advanced mode (clearly separated + safe recovery)" "$CHECKLIST"; then
    ok "feature-checklist.md §System UX row flipped to [x]"
  else
    fail "feature-checklist.md §System UX row NOT flipped to [x]"
  fi
fi

# --- 5) Operator setup doc mentions engage + disengage + recover ---
DOC="docs/setup/advanced-mode.md"
if [ ! -f "$DOC" ]; then
  fail "missing $DOC"
else
  ok "found $DOC"
  for term in engage disengage recover; do
    if grep -qi "$term" "$DOC"; then
      ok "doc mentions '$term'"
    else
      fail "doc does NOT mention '$term'"
    fi
  done
fi

# --- 6) scripts/check.sh invokes this smoke ---
CHECK_SH="scripts/check.sh"
if [ ! -f "$CHECK_SH" ]; then
  fail "missing $CHECK_SH"
else
  ok "found $CHECK_SH"
  if grep -q "advanced-mode-smoke" "$CHECK_SH"; then
    ok "scripts/check.sh invokes advanced-mode-smoke"
  else
    fail "scripts/check.sh does NOT invoke advanced-mode-smoke"
  fi
fi

echo
if [ "$FAIL" -eq 0 ]; then
  echo "✓ Advanced mode smoke check passed (slice #25)"
  exit 0
else
  echo "✗ Advanced mode smoke check FAILED" >&2
  exit 1
fi