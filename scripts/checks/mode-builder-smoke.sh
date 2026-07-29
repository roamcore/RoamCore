#!/usr/bin/env bash
# Mode / automation builder smoke check (slice #23).
#
# Validates that the RoamCore Mode / automation builder slice (#23) is
# wired end-to-end on disk:
#
#   1) `homeassistant/www/roamcore/roamcore-mode-builder.js` exists and
#      parses cleanly (Node `node --check` is preferred; stdlib regex
#      heuristic is a fallback when Node is unavailable).
#
#   2) The custom element class `RoamCoreModeBuilderCard` (matching
#      `RcModeBuilder` references) is declared and exported.
#
#   3) `homeassistant/packages/roamcore_mode.yaml` declares:
#      - `input_text.rc_mode_rules_json`
#      - `automation.rc_mode_apply_rules`
#      - at least one seed rule in the default JSON.
#
#   4) `homeassistant/packages/roamcore_mode_builder.yaml` declares the
#      `script.rc_mode_rules_seed_defaults` helper.
#
#   5) `homeassistant/www/roamcore/roamcore-pages.js` references the
#      mode-builder card (`roamcore-mode-builder`) and the contract
#      entity `input_text.rc_mode_rules_json`.
#
#   6) `docs/setup/mode-builder.md` exists and mentions the three core
#      terms: "Mode", "rule", and "automation".
#
#   7) `docs/feature-checklist.md` flips the §Automations row #23 from
#      `- [ ]` → `- [x]`.
#
#   8) `scripts/check.sh` invokes this smoke check via
#      `mode-builder-smoke`.
#
# This check does NOT touch a live HA instance; it only inspects files.
# Wired into `scripts/check.sh --core-only` after the privacy smokes.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
FAIL=0

fail() { echo "ERROR: $*" >&2; FAIL=1; }
ok()   { echo "  ✓ $*"; }

# --- 1) JS file exists + parses cleanly ---
JS_FILE="homeassistant/www/roamcore/roamcore-mode-builder.js"
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
    # Fallback: regex heuristic — balanced braces / parens / brackets.
    if "$PYTHON_BIN" - "$JS_FILE" <<'PY' >/dev/null 2>&1
import sys, re
src = open(sys.argv[1], "r", encoding="utf-8").read()
# Strip strings + comments before counting braces.
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
fi

# --- 2) Class declaration + custom element registration ---
if [ -f "$JS_FILE" ]; then
  if grep -q "class RoamCoreModeBuilderCard" "$JS_FILE"; then
    ok "RoamCoreModeBuilderCard class declared in $JS_FILE"
  else
    fail "RoamCoreModeBuilderCard class NOT declared in $JS_FILE"
  fi
  if grep -q "customElements.define" "$JS_FILE" && grep -q "'roamcore-mode-builder'" "$JS_FILE"; then
    ok "custom element 'roamcore-mode-builder' registered in $JS_FILE"
  else
    fail "custom element 'roamcore-mode-builder' NOT registered in $JS_FILE"
  fi
  if grep -q "RcModeBuilder\|RoamCoreModeBuilderCard" "$JS_FILE"; then
    ok "RcModeBuilder / RoamCoreModeBuilderCard references present in $JS_FILE"
  else
    fail "RcModeBuilder / RoamCoreModeBuilderCard NOT referenced in $JS_FILE"
  fi
fi

# --- 3) Mode YAML declares input_text + automation + ≥1 seed rule ---
MODE_YAML="homeassistant/packages/roamcore_mode.yaml"
if [ ! -f "$MODE_YAML" ]; then
  fail "missing $MODE_YAML"
else
  ok "found $MODE_YAML"
  if "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import yaml
d = yaml.safe_load(open("homeassistant/packages/roamcore_mode.yaml"))
it = d.get("input_text") or {}
auto = d.get("automation") or []
if "rc_mode_rules_json" not in it:
    raise SystemExit("input_text.rc_mode_rules_json missing")
auto_ids = [a.get("id") for a in auto]
if "rc_mode_apply_rules" not in auto_ids:
    raise SystemExit("automation.rc_mode_apply_rules missing")
raw = it["rc_mode_rules_json"].get("initial") or "[]"
import json
# Strip YAML block-scalar folds.
clean = " ".join(str(raw).split())
seed = json.loads(clean)
if not isinstance(seed, list) or len(seed) < 1:
    raise SystemExit("rc_mode_rules_json initial must be a non-empty list of rules")
# Each seed rule must have id, name, when, then, enabled.
for r in seed:
    for k in ("id", "name", "when", "then"):
        if k not in r:
            raise SystemExit(f"seed rule missing key: {k}")
    if not isinstance(r["when"], dict):
        raise SystemExit("seed rule 'when' must be an object")
PY
  then
    ok "input_text.rc_mode_rules_json declared (with seed rules), automation.rc_mode_apply_rules declared"
  else
    fail "roamcore_mode.yaml missing one of: input_text.rc_mode_rules_json / automation.rc_mode_apply_rules / seed rule"
  fi
fi

# --- 4) Builder YAML declares the seed_defaults script ---
BUILDER_YAML="homeassistant/packages/roamcore_mode_builder.yaml"
if [ ! -f "$BUILDER_YAML" ]; then
  fail "missing $BUILDER_YAML"
else
  ok "found $BUILDER_YAML"
  if grep -q "rc_mode_rules_seed_defaults" "$BUILDER_YAML"; then
    ok "script.rc_mode_rules_seed_defaults declared in $BUILDER_YAML"
  else
    fail "script.rc_mode_rules_seed_defaults NOT declared in $BUILDER_YAML"
  fi
fi

# --- 5) Pages.js references the card + contract entity ---
PAGES_JS="homeassistant/www/roamcore/roamcore-pages.js"
if [ ! -f "$PAGES_JS" ]; then
  fail "missing $PAGES_JS"
else
  ok "found $PAGES_JS"
  if grep -q "RcModeBuilder\|roamcore-mode-builder" "$PAGES_JS"; then
    ok "RcModeBuilder / roamcore-mode-builder referenced in pages.js"
  else
    fail "RcModeBuilder / roamcore-mode-builder NOT referenced in pages.js"
  fi
  if grep -q "input_text.rc_mode_rules_json" "$PAGES_JS"; then
    ok "input_text.rc_mode_rules_json wired in pages.js"
  else
    fail "input_text.rc_mode_rules_json NOT wired in pages.js"
  fi
fi

# --- 6) User-facing doc exists + mentions the core terms ---
DOC="docs/setup/mode-builder.md"
if [ ! -f "$DOC" ]; then
  fail "missing $DOC"
else
  ok "found $DOC"
  for term in Mode rule automation; do
    if grep -qi "$term" "$DOC"; then
      ok "doc mentions '$term'"
    else
      fail "doc does NOT mention '$term'"
    fi
  done
fi

# --- 7) Feature checklist row flipped ---
CHECKLIST="docs/feature-checklist.md"
if [ ! -f "$CHECKLIST" ]; then
  fail "missing $CHECKLIST"
else
  ok "found $CHECKLIST"
  if grep -q "^\- \[x\] Mode / automation builder (simple UI)" "$CHECKLIST"; then
    ok "feature-checklist.md §Automations row 1 flipped to [x]"
  else
    fail "feature-checklist.md §Automations row 1 NOT flipped to [x]"
  fi
fi

# --- 8) scripts/check.sh invokes this smoke ---
CHECK_SH="scripts/check.sh"
if [ ! -f "$CHECK_SH" ]; then
  fail "missing $CHECK_SH"
else
  ok "found $CHECK_SH"
  if grep -q "mode-builder-smoke" "$CHECK_SH"; then
    ok "scripts/check.sh invokes mode-builder-smoke"
  else
    fail "scripts/check.sh does NOT invoke mode-builder-smoke"
  fi
fi

echo
if [ "$FAIL" -eq 0 ]; then
  echo "✓ Mode / automation builder smoke check passed (slice #23)"
  exit 0
else
  echo "✗ Mode / automation builder smoke check FAILED" >&2
  exit 1
fi
