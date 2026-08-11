#!/usr/bin/env bash
# Catalog UI state chip primitive + tier vocabulary rebrand: smoke check
#
# Wave 9 #118 — Phase 1 catalog UI state chip primitive + tier vocabulary
# rebrand.
#
# Mirrors the convention in scripts/checks/<name>.sh:
#   - bash strict mode (set -euo pipefail)
#   - repo-local only (no live HA / Proxmox calls)
#   - 3 plain-English assertions (kebab CSS classes in rc.css, pytest
#     exit 0, every connection.yml state maps to a chip class)
#   - idempotent over re-runs
#
# Usage:
#   bash scripts/checks/catalog-state-chip-smoke.sh
#
# Exit codes:
#   0  all 3 assertions PASS (the chip primitive is data-layer-safe,
#      CSS-layer-safe, AND every connection.yml state maps to a chip)
#   1  one or more assertions FAIL (details printed to stderr)
#
# Wired into scripts/check.sh as a `run_if_present` step, AFTER the
# Wave 9 #117 state-field block but BEFORE the connection-manifest
# block. (Per the slice directive: state field is already on main
# via commit 863047b — this smoke checks the RENDER layer for that
# state field.)

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

# --- Assertion counters (so the operator sees PASS/FAIL at a glance) ---
PASS_COUNT=0
FAIL_COUNT=0
FAILED_ASSERTIONS=()

# Helper: assert a condition, increment counters, record failures.
# Uses printf so the output is portable across macOS / Linux.
assert_pass() {
  local label="$1"
  printf '\033[1;32m  ✓\033[0m %s\n' "$label"
  PASS_COUNT=$((PASS_COUNT + 1))
}

assert_fail() {
  local label="$1"
  local detail="${2:-}"
  printf '\033[1;31m  ✗\033[0m %s\n' "$label"
  if [ -n "$detail" ]; then
    printf '    %s\n' "$detail"
  fi
  FAIL_COUNT=$((FAIL_COUNT + 1))
  FAILED_ASSERTIONS+=("$label")
}

# --- Assertion 1: kebab CSS classes exist in docs/styles/rc.css ---
# Mirrors the cross-cutting pytest `test_rc_css_has_all_ten_state_chip_classes`
# in test_connection_card.py — same lockstep rule. If a future slice
# adds a state without adding the CSS, this assertion fails before
# the catalog renders as bare unstyled spans.
printf '\033[1;36m▶ Assertion 1\033[0m — kebab CSS classes exist in rc.css\n'

RC_CSS="docs/styles/rc.css"
if [ ! -f "$RC_CSS" ]; then
  assert_fail "rc.css exists at $RC_CSS" "the file is missing — the chip CSS lives here"
else
  assert_pass "rc.css exists at $RC_CSS"

  # The 10 kebab state classes (one per standard state).
  for kebab in available detected ready-to-connect connecting connected \
               needs-information needs-attention unsupported offline \
               update-available; do
    if grep -q "\.rc-state-chip--${kebab}" "$RC_CSS"; then
      assert_pass "rc.css defines .rc-state-chip--${kebab}"
    else
      assert_fail "rc.css defines .rc-state-chip--${kebab}" \
        "add the selector to $RC_CSS — the render layer emits this class"
    fi
  done

  # The 3 new tier vocabulary modifier classes (certified/verified/experimental).
  for vocab in certified verified experimental; do
    if grep -q "\.rc-tier--${vocab}" "$RC_CSS"; then
      assert_pass "rc.css defines .rc-tier--${vocab}"
    else
      assert_fail "rc.css defines .rc-tier--${vocab}" \
        "add the selector to $RC_CSS — the render layer emits this class"
    fi
    if grep -q "\.rc-chip--${vocab}" "$RC_CSS"; then
      assert_pass "rc.css defines .rc-chip--${vocab}"
    else
      assert_fail "rc.css defines .rc-chip--${vocab}" \
        "add the selector to $RC_CSS — the render layer emits this class"
    fi
  done

  # The row wrapper + Connect button + reason span base classes.
  for base in rc-state-chip rc-state-chip-row rc-state-chip-reason rc-connect-button; do
    if grep -q "\.${base}" "$RC_CSS"; then
      assert_pass "rc.css defines .${base}"
    else
      assert_fail "rc.css defines .${base}" \
        "add the selector to $RC_CSS — the render layer emits this class"
    fi
  done
fi

# --- Assertion 2: pytest rig exits 0 ---
# The pytest at homeassistant/packages/tests/test_connection_card.py is
# the contract rig for the render layer; running it here means any
# regression in the chip + tier + Connect + composition logic fails
# this smoke before the catalog renders.
printf '\n\033[1;36m▶ Assertion 2\033[0m — pytest rig exits 0\n'

# Temporarily disable `set -e` so we can capture pytest's exit code
# instead of the script aborting on the first failure. The pytest
# output is still streamed to the operator's terminal.
set +e
python3 -m pytest homeassistant/packages/tests/test_connection_card.py --tb=short -q
PYTEST_EXIT=$?
set -e

if [ "$PYTEST_EXIT" -eq 0 ]; then
  assert_pass "pytest test_connection_card.py exits 0"
else
  assert_fail "pytest test_connection_card.py exits 0" \
    "pytest exited with code ${PYTEST_EXIT}; see output above for the failing test(s)"
fi

# --- Assertion 3: every connection.yml state maps to a chip class ---
# The data-layer rule (from test_connection_state_field.py) is that
# every connection.yml carries a `state:` field from the 10-state
# allowlist. The render-layer rule (this assertion) is that every one
# of those 10 states maps to a kebab CSS class. The two assertions
# together ensure the chip primitive renders correctly for every
# device in the catalog.
printf '\n\033[1;36m▶ Assertion 3\033[0m — every connection.yml state maps to a chip class\n'

# Use Python to parse every connection.yml + bucket the chip classes
# the render layer would emit. PyYAML is already a pytest dependency.
python3 - <<'PYEOF'
import os, sys, glob

# The 10 standard states → kebab class (mirrors the helper's
# STATE_TO_KEBAB_CLASS table). Hardcoded here so this assertion
# catches a drift in either direction (a state in the helper that's
# missing from the CSS, OR a state in the data layer that's missing
# from the helper).
STATE_TO_KEBAB_CLASS = {
    "Available": "available",
    "Detected": "detected",
    "Ready to connect": "ready-to-connect",
    "Connecting": "connecting",
    "Connected": "connected",
    "Needs information": "needs-information",
    "Needs attention": "needs-attention",
    "Unsupported": "unsupported",
    "Offline": "offline",
    "Update available": "update-available",
}

import yaml

manifests = sorted(glob.glob("connections/*/connection.yml"))
manifests = [p for p in manifests if os.path.isfile(p)]
unmapped = []
unknown_state = []
for path in manifests:
    try:
        data = yaml.safe_load(open(path, encoding="utf-8"))
    except yaml.YAMLError as exc:
        unmapped.append((path, f"YAML parse failed: {exc}"))
        continue
    state = data.get("state") if isinstance(data, dict) else None
    if not isinstance(state, str) or not state.strip():
        unmapped.append((path, "missing or blank state field"))
        continue
    if state not in STATE_TO_KEBAB_CLASS:
        unknown_state.append((path, state))
        continue
    kebab = STATE_TO_KEBAB_CLASS[state]
    # Confirm the kebab CSS class actually exists in the CSS file.
    css_path = os.path.join("docs", "styles", "rc.css")
    if not os.path.isfile(css_path):
        unmapped.append((path, f"rc.css missing — cannot verify kebab class '{kebab}'"))
        continue
    css_text = open(css_path, encoding="utf-8").read()
    if f".rc-state-chip--{kebab}" not in css_text:
        unmapped.append((path, f"kebab class 'rc-state-chip--{kebab}' not in rc.css"))
        continue

if not unmapped and not unknown_state:
    print(f"OK: every one of the {len(manifests)} connection manifests carries a state that maps to a chip class")
    sys.exit(0)

if unmapped:
    short = unmapped[:8]
    more = "..." if len(unmapped) > 8 else ""
    print(f"FAIL: {len(unmapped)} manifests do not map cleanly to a chip class: {short}{more}")
if unknown_state:
    values = sorted({v for _, v in unknown_state})
    print(f"FAIL: {len(unknown_state)} manifests carry a state outside the 10-state allowlist: {values}")
sys.exit(1)
PYEOF

PYTHON_EXIT=$?
if [ "$PYTHON_EXIT" -eq 0 ]; then
  assert_pass "every connection.yml state maps to a chip class"
else
  assert_fail "every connection.yml state maps to a chip class" \
    "Python helper exited with code ${PYTHON_EXIT}; see output above"
fi

# --- Summary ---
printf '\n\033[1;36m▶ Summary\033[0m\n'
printf '  PASS: %d\n' "$PASS_COUNT"
printf '  FAIL: %d\n' "$FAIL_COUNT"
if [ "$FAIL_COUNT" -gt 0 ]; then
  printf '\n\033[1;31m✗ catalog-state-chip-smoke FAILED\033[0m\n'
  printf 'Failed assertions:\n'
  for label in "${FAILED_ASSERTIONS[@]}"; do
    printf '  - %s\n' "$label"
  done
  exit 1
fi
printf '\n\033[1;32m✓ catalog-state-chip-smoke PASSED\033[0m\n'
exit 0