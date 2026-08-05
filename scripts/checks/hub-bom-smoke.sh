#!/usr/bin/env bash
# RoamCore Hub BOM — smoke check.
#
# Mirrors the convention in scripts/checks/<name>.sh:
#   - bash strict mode (set -euo pipefail)
#   - repo-local only (no live HA / Proxmox / vendor calls)
#   - thin wrapper around the pure-Python validator with a few
#     inline assertions on top
#   - plain-English summary at exit 0 / non-zero exit
#
# Usage:
#   bash scripts/checks/hub-bom-smoke.sh
#
# Exit codes:
#   0  manifest is present, valid YAML, passes every validator rule,
#      and the component count is non-zero
#   1  one or more of the above failed (a plain-English message names
#      the failure)
#
# Wired into scripts/check.sh as a `run_if_present` step.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

BOM_FILE="hardware/roamcore-hub-bom.yml"
VALIDATOR="scripts/build/hub-bom-validate.py"

fail() { echo "FAIL: $*" >&2; exit 1; }

# --- Pre-flight: required files actually exist on disk -----------------
[ -f "$BOM_FILE" ] || fail "RoamCore Hub BOM: missing manifest at $BOM_FILE"
[ -f "$VALIDATOR" ] || fail "RoamCore Hub BOM: missing validator at $VALIDATOR"

# --- Pre-flight: PyYAML is importable (the validator's only dep) -------
python3 -c "import yaml" 2>/dev/null \
  || fail "RoamCore Hub BOM: PyYAML is required (pip install pyyaml)"

# --- Run the validator; capture output + exit code --------------------
set +e
VALIDATOR_OUTPUT="$(python3 "$VALIDATOR" "$BOM_FILE" 2>&1)"
VALIDATOR_EXIT=$?
set -e

if [ "$VALIDATOR_EXIT" -ne 0 ]; then
    echo "RoamCore Hub BOM: validator failed" >&2
    echo "$VALIDATOR_OUTPUT" >&2
    exit 1
fi

# --- Inline assertions on top of the validator's verdict --------------
# The validator already enforces every rule; these checks are
# belt-and-braces (e.g. ensure the summary line actually parses so
# CI doesn't silently pass on a future validator regression).

# 1) The summary line starts with "OK: RoamCore Hub BOM validates".
echo "$VALIDATOR_OUTPUT" | grep -q "^OK: RoamCore Hub BOM validates" \
  || fail "RoamCore Hub BOM: validator did not produce the expected OK summary"

# 2) The component count is a positive integer.
COMPONENT_COUNT="$(echo "$VALIDATOR_OUTPUT" \
  | sed -nE 's/.*OK: RoamCore Hub BOM validates — ([0-9]+) components.*/\1/p')"
if [ -z "$COMPONENT_COUNT" ] || [ "$COMPONENT_COUNT" -lt 1 ]; then
    fail "RoamCore Hub BOM: could not parse a positive component count"
fi

# 3) Idempotent: running the validator a second time yields the same
#    summary line. Catches any future "non-readonly" regression.
set +e
SECOND_OUTPUT="$(python3 "$VALIDATOR" "$BOM_FILE" 2>&1)"
SECOND_EXIT=$?
set -e
if [ "$SECOND_EXIT" -ne 0 ] || [ "$SECOND_OUTPUT" != "$VALIDATOR_OUTPUT" ]; then
    fail "RoamCore Hub BOM: validator is not idempotent (second run diverged)"
fi

# --- All checks passed --------------------------------------------------
echo "OK: $COMPONENT_COUNT components validated; total within sanity band; validator is idempotent."
exit 0
