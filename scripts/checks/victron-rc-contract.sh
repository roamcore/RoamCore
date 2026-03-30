#!/usr/bin/env bash
set -euo pipefail

# Check that docs/reference/victron-rc-mapping-plan.md's rc_* contract entities
# exist as unique_id entries in Home Assistant packages.
#
# This helps keep the contract layer (rc_*) aligned with the mapping plan.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PLAN_MD="$ROOT_DIR/docs/reference/victron-rc-mapping-plan.md"
PKG_DIR="$ROOT_DIR/homeassistant/packages"
PKG_FILE="$PKG_DIR/roamcore_power.yaml"

if [[ ! -f "$PLAN_MD" ]]; then
  echo "Missing: $PLAN_MD" >&2
  exit 2
fi
if [[ ! -d "$PKG_DIR" ]]; then
  echo "Missing dir: $PKG_DIR" >&2
  exit 2
fi
if [[ ! -f "$PKG_FILE" ]]; then
  echo "Missing: $PKG_FILE" >&2
  exit 2
fi

# Extract rc ids from docs.
# Accept sensor.rc_* and binary_sensor.rc_*.
doc_rc="$(
  grep -oE '(sensor|binary_sensor)\.rc_[a-zA-Z0-9_]+' "$PLAN_MD" \
    | sed -E 's/^(sensor|binary_sensor)\.//' \
    | sort -u
)"

# Extract unique_id values from the RoamCore power package.
# This keeps the check scoped to the Victron → power contract layer.
# unique_id: rc_...
code_rc="$(
  grep -hoE '^\s*unique_id:\s*rc_[a-zA-Z0-9_]+' "$PKG_FILE" \
    | sed -E 's/^\s*unique_id:\s*//' \
    | sort -u
)"

echo "== Victron rc_* contract check =="
echo "Docs: $(echo "$doc_rc" | wc -l | tr -d ' ') rc_* ids"
echo "Code: $(echo "$code_rc" | wc -l | tr -d ' ') rc_* ids ($PKG_FILE)"
echo

missing_in_code="$({ comm -23 <(echo "$doc_rc") <(echo "$code_rc") || true; } | sed '/^$/d')"
extra_in_code="$({ comm -13 <(echo "$doc_rc") <(echo "$code_rc") || true; } | sed '/^$/d')"

if [[ -n "$missing_in_code" ]]; then
  echo "FAIL: rc_* ids present in docs but missing unique_id in homeassistant/packages:" >&2
  echo "$missing_in_code" | sed 's/^/  - /' >&2
  exit 1
fi

echo "OK: all docs rc_* ids exist in packages"

if [[ -n "$extra_in_code" ]]; then
  echo
  echo "WARN: rc_* ids present in packages but not listed in docs/reference/victron-rc-mapping-plan.md:"
  echo "$extra_in_code" | sed 's/^/  - /'
  echo
  echo "Tip: update the mapping plan doc (or intentionally ignore) to keep contract docs current."
fi
