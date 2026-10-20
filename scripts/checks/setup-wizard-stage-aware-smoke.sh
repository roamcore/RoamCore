#!/usr/bin/env bash
set -euo pipefail

# Wave 2 #16 — setup wizard stage-aware smoke check.
#
# Static checks for the stage-aware collapse slice:
#   1. The Lovelace YAML parses (yaml.safe_load).
#   2. Every stage referenced by a `conditional` card is a valid option in
#      `input_select.rc_setup_stage` (defined in the setup package).
#   3. Every `binary_sensor.rc_setup_*_ready` referenced in the YAML exists
#      as a `unique_id:` in the setup package.
#   4. Every `script.*` and `input_button.*` referenced in the YAML exists
#      as a top-level key in the setup package.
#   5. `input_select.rc_setup_stage` is referenced in the YAML at least twice
#      (gating + reset/jump-back).
#
# Exit 0 on success, non-zero on the first failing assertion.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOVELACE_FILE="$ROOT_DIR/homeassistant/lovelace/roamcore-setup-wizard.yaml"
PKG_FILE="$ROOT_DIR/homeassistant/packages/roamcore_setup_wizard.yaml"

if [[ ! -f "$LOVELACE_FILE" ]]; then
  echo "FAIL: missing $LOVELACE_FILE" >&2
  exit 2
fi
if [[ ! -f "$PKG_FILE" ]]; then
  echo "FAIL: missing $PKG_FILE" >&2
  exit 2
fi

echo "== Setup wizard stage-aware smoke =="
echo "Lovelace: $LOVELACE_FILE"
echo "Package:  $PKG_FILE"
echo

# --- 1) YAML parses ------------------------------------------------------
python3 - "$LOVELACE_FILE" <<'PY' || exit 1
import sys, yaml
with open(sys.argv[1]) as fh:
    d = yaml.safe_load(fh)
assert isinstance(d, dict), "top-level must be a mapping"
assert "views" in d and isinstance(d["views"], list) and d["views"], "views must be a non-empty list"
print("OK: Lovelace YAML parses (views={})".format(len(d["views"])))
PY

# --- 2) Package YAML parses ---------------------------------------------
PKG_KEYS="$(python3 -c "import yaml; d=yaml.safe_load(open('$PKG_FILE')); print(' '.join(d.keys()))")"
echo "Package top-level keys: $PKG_KEYS"

# Stages referenced in input_select.rc_setup_stage.options
STAGE_OPTIONS="$(
  python3 - "$PKG_FILE" <<'PY'
import sys, yaml
d = yaml.safe_load(open(sys.argv[1]))
opts = d.get('input_select', {}).get('rc_setup_stage', {}).get('options', [])
for o in opts:
    print(o)
PY
)"

# Unique IDs in the package
PKG_UNIQUE_IDS="$(
  grep -hoE '^\s*unique_id:\s*[a-zA-Z0-9_]+' "$PKG_FILE" \
    | sed -E 's/^\s*unique_id:\s*//' \
    | sort -u
)"

# Top-level keys that look like scripts (scanned across all packages
# because the wizard legitimately references scripts from sibling packages,
# e.g. roamcore_trip_wrapped).
ALL_PKG_FILES="$PKG_FILE $(ls "$ROOT_DIR/homeassistant/packages/"*.yaml 2>/dev/null | tr '\n' ' ')"
PKG_SCRIPTS="$(
  python3 - $ALL_PKG_FILES <<'PY'
import sys, yaml
out = []
for path in sys.argv[1:]:
    try:
        with open(path) as fh:
            d = yaml.safe_load(fh)
    except Exception:
        continue
    if not isinstance(d, dict):
        continue
    for k in (d.get('script', {}) or {}).keys():
        out.append(k)
for k in sorted(set(out)):
    print(k)
PY
)"

# Top-level input_button keys (across all packages — the wizard's own
# buttons live in the setup package, but we check the whole tree for
# future-proofing).
PKG_INPUT_BUTTONS="$(
  python3 - $ALL_PKG_FILES <<'PY'
import sys, yaml
out = []
for path in sys.argv[1:]:
    try:
        with open(path) as fh:
            d = yaml.safe_load(fh)
    except Exception:
        continue
    if not isinstance(d, dict):
        continue
    for k in (d.get('input_button', {}) or {}).keys():
        out.append(k)
for k in sorted(set(out)):
    print(k)
PY
)"

# --- 3) conditional stages in YAML must be valid stages ----------------
COND_STAGES="$(
  python3 - "$LOVELACE_FILE" <<'PY'
import sys, yaml
d = yaml.safe_load(open(sys.argv[1]))
out = []
def walk(node):
    if isinstance(node, dict):
        cond = node.get('conditions')
        if isinstance(cond, list):
            for c in cond:
                if isinstance(c, dict) and 'state' in c and 'entity' in c:
                    if str(c['entity']).endswith('input_select.rc_setup_stage'):
                        out.append(str(c['state']))
        for v in node.values():
            walk(v)
    elif isinstance(node, list):
        for v in node:
            walk(v)
walk(d)
for s in sorted(set(out)):
    print(s)
PY
)"

echo "Stages used in conditional cards: $(echo "$COND_STAGES" | tr '\n' ',' | sed 's/,$//')"
echo "Stages declared in input_select.rc_setup_stage: $(echo "$STAGE_OPTIONS" | tr '\n' ',' | sed 's/,$//')"

while read -r s; do
  [[ -z "$s" ]] && continue
  if ! grep -Fxq "$s" <<< "$STAGE_OPTIONS"; then
    echo "FAIL: conditional stage '$s' is not declared in input_select.rc_setup_stage.options" >&2
    exit 1
  fi
done <<< "$COND_STAGES"
echo "OK: all conditional stages are declared options"

# --- 4) binary_sensor.rc_setup_*_ready referenced must exist ------------
READY_REFS="$(
  python3 - "$LOVELACE_FILE" <<'PY'
import sys, yaml
d = yaml.safe_load(open(sys.argv[1]))
out = []
def walk(node):
    if isinstance(node, dict):
        ent = node.get('entity')
        if isinstance(ent, str) and ent.startswith('binary_sensor.rc_setup_') and ent.endswith('_ready'):
            out.append(ent.split('.', 1)[1])
        for v in node.values():
            walk(v)
    elif isinstance(node, list):
        for v in node:
            walk(v)
walk(d)
for s in sorted(set(out)):
    print(s)
PY
)"

if [[ -z "$READY_REFS" ]]; then
  echo "WARN: no binary_sensor.rc_setup_*_ready references found in Lovelace YAML"
else
  echo "Readiness refs in Lovelace YAML: $(echo "$READY_REFS" | tr '\n' ',' | sed 's/,$//')"
  while read -r ref; do
    [[ -z "$ref" ]] && continue
    if ! grep -Fxq "$ref" <<< "$PKG_UNIQUE_IDS"; then
      echo "FAIL: readiness sensor '$ref' has no unique_id in $PKG_FILE" >&2
      exit 1
    fi
  done <<< "$READY_REFS"
  echo "OK: all readiness references exist as unique_id in the setup package"
fi

# --- 5) script.* references must exist as top-level keys ----------------
SCRIPT_REFS="$(
  python3 - "$LOVELACE_FILE" <<'PY'
import sys, yaml
d = yaml.safe_load(open(sys.argv[1]))
out = []
def walk(node):
    if isinstance(node, dict):
        ent = node.get('entity')
        if isinstance(ent, str) and ent.startswith('script.'):
            out.append(ent.split('.', 1)[1])
        for v in node.values():
            walk(v)
    elif isinstance(node, list):
        for v in node:
            walk(v)
walk(d)
for s in sorted(set(out)):
    print(s)
PY
)"

if [[ -n "$SCRIPT_REFS" ]]; then
  echo "Script refs in Lovelace YAML: $(echo "$SCRIPT_REFS" | tr '\n' ',' | sed 's/,$//')  (scanned across all packages)"
  while read -r ref; do
    [[ -z "$ref" ]] && continue
    if ! grep -Fxq "$ref" <<< "$PKG_SCRIPTS"; then
      echo "FAIL: script '$ref' referenced in YAML is not defined in $PKG_FILE" >&2
      exit 1
    fi
  done <<< "$SCRIPT_REFS"
  echo "OK: all script.* references exist in the setup package"
fi

# --- 6) input_button.* references must exist as top-level keys ----------
IB_REFS="$(
  python3 - "$LOVELACE_FILE" <<'PY'
import sys, yaml
d = yaml.safe_load(open(sys.argv[1]))
out = []
def walk(node):
    if isinstance(node, dict):
        ent = node.get('entity')
        if isinstance(ent, str) and ent.startswith('input_button.'):
            out.append(ent.split('.', 1)[1])
        for v in node.values():
            walk(v)
    elif isinstance(node, list):
        for v in node:
            walk(v)
walk(d)
for s in sorted(set(out)):
    print(s)
PY
)"

if [[ -n "$IB_REFS" ]]; then
  echo "input_button refs in Lovelace YAML: $(echo "$IB_REFS" | tr '\n' ',' | sed 's/,$//')  (scanned across all packages)"
  while read -r ref; do
    [[ -z "$ref" ]] && continue
    if ! grep -Fxq "$ref" <<< "$PKG_INPUT_BUTTONS"; then
      echo "FAIL: input_button '$ref' referenced in YAML is not defined in $PKG_FILE" >&2
      exit 1
    fi
  done <<< "$IB_REFS"
  echo "OK: all input_button.* references exist in the setup package"
fi

# --- 7) input_select.rc_setup_stage must be referenced >= 2 times ------
SELECT_REFS="$(grep -c 'input_select.rc_setup_stage' "$LOVELACE_FILE" || true)"
echo "input_select.rc_setup_stage references: $SELECT_REFS"
if [[ "$SELECT_REFS" -lt 2 ]]; then
  echo "FAIL: input_select.rc_setup_stage must be referenced at least twice in the Lovelace YAML (got $SELECT_REFS)" >&2
  exit 1
fi
echo "OK: input_select.rc_setup_stage is referenced >= 2 times"

echo
echo "All setup-wizard stage-aware smoke checks passed."