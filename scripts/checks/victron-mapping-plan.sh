#!/usr/bin/env bash
set -euo pipefail

# Check that docs/reference/victron-rc-mapping-plan.md matches the vt_* keys
# currently published by the roamcore-victron-auto add-on.
#
# This is a lightweight drift detector (not a linter).

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AUTO_MAIN_PY="$ROOT_DIR/homeassistant/addons/roamcore-victron-auto/src/main.py"
PLAN_MD="$ROOT_DIR/docs/reference/victron-rc-mapping-plan.md"

if [[ ! -f "$AUTO_MAIN_PY" ]]; then
  echo "Missing: $AUTO_MAIN_PY" >&2
  exit 2
fi
if [[ ! -f "$PLAN_MD" ]]; then
  echo "Missing: $PLAN_MD" >&2
  exit 2
fi

# Extract vt keys from code.
code_keys="$(
  grep -oE '"vt_key"\s*:\s*"vt_[a-zA-Z0-9_]+"' "$AUTO_MAIN_PY" \
    | sed -E 's/.*"(vt_[a-zA-Z0-9_]+)".*/\1/' \
    | sort -u
)"

# Extract vt keys from mapping plan doc.
# Accept both sensor.* and binary_sensor.* forms.
doc_keys="$(
  grep -oE '(sensor|binary_sensor)\.vt_[a-zA-Z0-9_]+' "$PLAN_MD" \
    | sed -E 's/^(sensor|binary_sensor)\.//' \
    | sort -u
)"

echo "== Victron mapping drift check =="
echo "Code: $(echo "$code_keys" | wc -l | tr -d ' ') keys"
echo "Docs: $(echo "$doc_keys" | wc -l | tr -d ' ') keys"
echo

# Compare.
missing_in_docs="$({ comm -23 <(echo "$code_keys") <(echo "$doc_keys") || true; } | sed '/^$/d')"
missing_in_code="$({ comm -13 <(echo "$code_keys") <(echo "$doc_keys") || true; } | sed '/^$/d')"

ok=1
if [[ -n "$missing_in_docs" ]]; then
  ok=0
  echo "-- Present in code but missing in docs/reference/victron-rc-mapping-plan.md:"
  echo "$missing_in_docs" | sed 's/^/  - /'
  echo
fi

if [[ -n "$missing_in_code" ]]; then
  ok=0
  echo "-- Present in docs but missing in code (roamcore-victron-auto):"
  echo "$missing_in_code" | sed 's/^/  - /'
  echo
fi

if [[ "$ok" -eq 1 ]]; then
  echo "OK: docs and code vt_* lists match"
  exit 0
fi

echo "FAIL: mapping plan drift detected" >&2
exit 1
