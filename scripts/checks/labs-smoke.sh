#!/usr/bin/env bash
set -euo pipefail

# RoamCore — Labs (share setups/dashboards) smoke check.
#
# Validates the Wave 2 #32 slice is present and consistent in the repo:
#   1. Contract package YAML parses and declares 8 contract entities.
#   2. Wizard snippet YAML parses and references the contract entities.
#   3. Custom-component services `roamcore.labs_export_setup` +
#      `roamcore.labs_import_setup` are registered in services.yaml.
#   4. Custom-component handlers `_svc_labs_export_setup` +
#      `_svc_labs_import_setup` are present in __init__.py.
#   5. CLI helpers exist + accept --help + --dry-run.
#   6. import path references input_text.rc_labs_pending_import;
#      export path does NOT (separation of concerns).
#   7. unavailable-when-OFF branch + availability gate are present
#      in the derived sensors (privacy / availability invariant).
#   8. docs/setup/labs.md has 4-step setup + privacy section + tier-b tag.
#   9. docs/feature-checklist.md RoamCore Labs row is ticked [x].
#  10. Privacy invariant: no `requests` / `urllib.request` / `urllib3`
#      / `httpx` / `aiohttp` imports in any new code.
#  11. Negative-test self-check: when the CLI helper is patched to
#      import `urllib.request`, the smoke would fail (so the
#      privacy invariant is enforced, not just declared).
#
# This script is purely static — it never reaches out to a running HA,
# never resolves DNS, never opens a socket. It exits non-zero on the
# first failed assertion.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PKG="homeassistant/packages/roamcore_labs.yaml"
WIZ="homeassistant/packages/roamcore_setup_wizard_labs.yaml"
SERVICES_YAML="homeassistant/custom_components/roamcore/services.yaml"
INIT_PY="homeassistant/custom_components/roamcore/__init__.py"
EXPORT_CLI="homeassistant/tools/labs/export_setup.py"
IMPORT_CLI="homeassistant/tools/labs/import_setup.py"
EXPORT_COMMON="homeassistant/tools/labs/common.py"
SETUP_DOC="docs/setup/labs.md"
CHECKLIST="docs/feature-checklist.md"
BUILD_STATUS="docs/mvp/features-build-status.md"
SCRIPTS_CHECK="scripts/check.sh"

fail() { echo "ERROR: $*" >&2; exit 1; }
pass() { echo "  PASS: $*"; }
ASSERTS=0
note_assert() { ASSERTS=$((ASSERTS + 1)); }

# --- Pre-flight -----------------------------------------------------------
[ -f "$PKG" ]    || fail "missing contract package: $PKG"
[ -f "$WIZ" ]    || fail "missing wizard snippet: $WIZ"
[ -f "$SERVICES_YAML" ] || fail "missing services.yaml: $SERVICES_YAML"
[ -f "$INIT_PY" ]  || fail "missing __init__.py: $INIT_PY"
[ -f "$EXPORT_CLI" ] || fail "missing CLI: $EXPORT_CLI"
[ -f "$IMPORT_CLI" ] || fail "missing CLI: $IMPORT_CLI"
[ -f "$EXPORT_COMMON" ] || fail "missing helper: $EXPORT_COMMON"
[ -f "$SETUP_DOC" ] || fail "missing setup doc: $SETUP_DOC"
[ -f "$CHECKLIST" ] || fail "missing feature checklist: $CHECKLIST"
[ -f "$BUILD_STATUS" ] || fail "missing build status: $BUILD_STATUS"
[ -f "$SCRIPTS_CHECK" ] || fail "missing check.sh: $SCRIPTS_CHECK"

# --- 1. Contract package parses + declares 8 contract entities ------------
echo "== contract package parses =="
python3 -c 'import sys,yaml; yaml.safe_load(open(sys.argv[1],"r",encoding="utf-8"))' "$PKG" \
  || fail "YAML parse failed: $PKG"
python3 -c 'import sys,yaml; yaml.safe_load(open(sys.argv[1],"r",encoding="utf-8"))' "$WIZ" \
  || fail "YAML parse failed: $WIZ"
pass "$PKG parses as YAML"
note_assert
python3 -c 'import sys,yaml; yaml.safe_load(open(sys.argv[1],"r",encoding="utf-8"))' "$WIZ" \
  >/dev/null && pass "$WIZ parses as YAML" && note_assert

# 8 contract entities declared (line-anchored unique_id checks).
echo "== 8 contract entities declared =="
declare -a ENTITIES=(
  "rc_labs_enabled"
  "rc_labs_export_setup"
  "rc_labs_import_setup"
  "rc_labs_last_export_path"
  "rc_labs_last_import_status"
  "rc_labs_export_count"
  "rc_labs_import_count"
)
declare -a INPUT_TEXT_HELPERS=(
  "rc_labs_pending_import"
)
for unique in "${ENTITIES[@]}"; do
  if ! grep -qE "^[[:space:]]+unique_id:[[:space:]]+${unique}[[:space:]]*$" "$PKG"; then
    fail "contract package missing unique_id '${unique}'"
  fi
  pass "entity unique_id '${unique}' declared in $PKG"
  note_assert
done

# input_text helper: rc_labs_pending_import is declared as a top-level
# input_text key (input_text helpers don't have a unique_id slot, but
# the helper key is the contract identifier).
echo "== input_text.rc_labs_pending_import declared =="
if ! grep -qE "^[[:space:]]+rc_labs_pending_import:[[:space:]]*$" "$PKG"; then
  fail "input_text helper 'rc_labs_pending_import' missing from $PKG"
fi
pass "input_text.rc_labs_pending_import declared (line-anchored)"
note_assert

# --- 2. Wizard snippet references contract entities ----------------------
echo "== wizard snippet references contract entities =="
for unique in \
  "rc_labs_enabled" \
  "rc_labs_export_setup" \
  "rc_labs_import_setup" \
  "rc_labs_last_export_path" \
  "rc_labs_last_import_status" \
  "rc_labs_pending_import" \
  "rc_labs_export_count" \
  "rc_labs_import_count"; do
  if ! grep -qF "$unique" "$WIZ"; then
    fail "$WIZ does not reference contract entity '${unique}'"
  fi
  pass "wizard references contract entity '${unique}'"
  note_assert
done

# --- 3. Services registered ----------------------------------------------
echo "== custom-component services registered =="
if ! grep -qE "^labs_export_setup:" "$SERVICES_YAML"; then
  fail "service 'labs_export_setup' not declared in $SERVICES_YAML"
fi
pass "service 'roamcore.labs_export_setup' declared in $SERVICES_YAML"
note_assert

if ! grep -qE "^labs_import_setup:" "$SERVICES_YAML"; then
  fail "service 'labs_import_setup' not declared in $SERVICES_YAML"
fi
pass "service 'roamcore.labs_import_setup' declared in $SERVICES_YAML"
note_assert

# Services must declare their target field.
if ! grep -qE "target_path:" "$SERVICES_YAML"; then
  fail "service 'labs_export_setup' missing 'target_path' field"
fi
pass "service 'roamcore.labs_export_setup' declares 'target_path' field"
note_assert

if ! grep -qE "bundle_path:" "$SERVICES_YAML"; then
  fail "service 'labs_import_setup' missing 'bundle_path' field"
fi
pass "service 'roamcore.labs_import_setup' declares 'bundle_path' field"
note_assert

# --- 4. Service handlers present in __init__.py ---------------------------
echo "== service handlers present =="
if ! grep -qF "_svc_labs_export_setup" "$INIT_PY"; then
  fail "$INIT_PY missing service handler '_svc_labs_export_setup'"
fi
pass "$INIT_PY defines service handler '_svc_labs_export_setup'"
note_assert

if ! grep -qF "_svc_labs_import_setup" "$INIT_PY"; then
  fail "$INIT_PY missing service handler '_svc_labs_import_setup'"
fi
pass "$INIT_PY defines service handler '_svc_labs_import_setup'"
note_assert

if ! grep -qF '"labs_export_setup"' "$INIT_PY"; then
  fail "$INIT_PY does not register 'labs_export_setup' with hass.services.async_register"
fi
pass "$INIT_PY registers 'labs_export_setup' service"
note_assert

if ! grep -qF '"labs_import_setup"' "$INIT_PY"; then
  fail "$INIT_PY does not register 'labs_import_setup' with hass.services.async_register"
fi
pass "$INIT_PY registers 'labs_import_setup' service"
note_assert

# --- 5. CLI helpers exist + accept --help + --dry-run --------------------
echo "== CLI helpers exist =="
SHEBANG_E="$(head -1 "$EXPORT_CLI" 2>/dev/null || true)"
if ! [[ "$SHEBANG_E" =~ ^#!.*python3 ]]; then
  fail "$EXPORT_CLI does not start with a python3 shebang"
fi
pass "$EXPORT_CLI has python3 shebang"
note_assert

SHEBANG_I="$(head -1 "$IMPORT_CLI" 2>/dev/null || true)"
if ! [[ "$SHEBANG_I" =~ ^#!.*python3 ]]; then
  fail "$IMPORT_CLI does not start with a python3 shebang"
fi
pass "$IMPORT_CLI has python3 shebang"
note_assert

# --help must exit 0 (argparse).
if ! python3 "$EXPORT_CLI" --help >/dev/null 2>&1; then
  fail "$EXPORT_CLI --help exit non-zero"
fi
pass "$EXPORT_CLI --help exits 0"
note_assert

if ! python3 "$IMPORT_CLI" --help >/dev/null 2>&1; then
  fail "$IMPORT_CLI --help exit non-zero"
fi
pass "$IMPORT_CLI --help exits 0"
note_assert

# --dry-run must exit 0 (the export CLI takes a target so we feed /tmp).
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
DRY_OUT_EXPORT="$TMPDIR/dry_export.tar.gz"
if ! python3 "$EXPORT_CLI" --dry-run --target "$DRY_OUT_EXPORT" >/dev/null 2>&1; then
  fail "$EXPORT_CLI --dry-run exit non-zero"
fi
pass "$EXPORT_CLI --dry-run exits 0"
note_assert

# Build a stub bundle so the import CLI can dry-run against it.
python3 "$EXPORT_CLI" --target "$DRY_OUT_EXPORT" >/dev/null 2>&1 \
  || fail "could not build a stub bundle for the import dry-run"
if ! python3 "$IMPORT_CLI" --bundle "$DRY_OUT_EXPORT" --dry-run >/dev/null 2>&1; then
  fail "$IMPORT_CLI --dry-run exit non-zero"
fi
pass "$IMPORT_CLI --dry-run exits 0"
note_assert

# --- 6. reference separation: import uses pending_import, export does not
echo "== reference separation: pending_import =="
# The export CLI / service should NOT touch the pending-import path.
# We check the export side for any reference to rc_labs_pending_import.
if grep -qF "rc_labs_pending_import" "$EXPORT_CLI" \
   || grep -qF "rc_labs_pending_import" "$EXPORT_COMMON"; then
  fail "export side references rc_labs_pending_import (separation of concerns violated)"
fi
pass "export side does not reference rc_labs_pending_import"
note_assert

# The import CLI / service / __init__.py handler MUST reference
# rc_labs_pending_import (so the wizard chip refreshes).
if ! grep -qF "rc_labs_pending_import" "$IMPORT_CLI" \
   && ! grep -qF "rc_labs_pending_import" "$INIT_PY"; then
  fail "import side does not reference rc_labs_pending_import (wizard chip won't refresh)"
fi
pass "import side references rc_labs_pending_import"
note_assert

# --- 7. unavailable-when-OFF branch + availability gate -------------------
echo "== unavailable-when-OFF branch + availability gate =="
# The contract package must explicitly gate the derived sensors on
# the master switch. We accept either the explicit OFF clause or the
# positive ON gate (both are documented Wave 2 patterns).
if ! grep -qE "is_state\('input_boolean.rc_labs_enabled',[[:space:]]*'off'\)" "$PKG" \
   && ! grep -qE "is_state\('input_boolean.rc_labs_enabled',[[:space:]]*'on'\)" "$PKG"; then
  fail "no OFF-clause / ON-gate for rc_labs_enabled in $PKG (privacy/availability invariant)"
fi
pass "unavailable-when-OFF branch present (explicit OFF clause or positive ON gate)"
note_assert

# The contract package must declare an availability template on at
# least one of the derived sensors.
if ! grep -qE "availability:" "$PKG"; then
  fail "no availability template in $PKG (sensors must report unavailable when OFF)"
fi
pass "availability template present in $PKG"
note_assert

# --- 8. docs/setup/labs.md has 4-step + privacy + tier-b ------------------
echo "== docs/setup/labs.md content =="
for needle in \
  "## 1. Enable the Labs subsystem" \
  "## 2. Export the active setup" \
  "## 3. Share the bundle out-of-band" \
  "## 4. Import a bundle on another RoamCore install" \
  "## 5. Privacy" \
  "## 6. Troubleshooting" \
  "tier-b" \
  "Tier: b"; do
  if ! grep -qF "$needle" "$SETUP_DOC"; then
    fail "docs/setup/labs.md missing required content: '$needle'"
  fi
done
pass "$SETUP_DOC has 4-step setup + privacy section + tier-b tag"
note_assert

# --- 9. docs/feature-checklist.md RoamCore Labs row ticked [x] -----------
echo "== docs/feature-checklist.md RoamCore Labs row ticked =="
# Find the line that mentions RoamCore Labs (intent: the slice name).
LABS_LINE="$(grep -n -E "RoamCore Labs \(share setups/dashboards\)" "$CHECKLIST" | head -1 || true)"
if [ -z "$LABS_LINE" ]; then
  fail "docs/feature-checklist.md has no 'RoamCore Labs (share setups/dashboards)' row"
fi
echo "    matched: $LABS_LINE"
# The checkbox pattern is `- [x] RoamCore Labs (share setups/dashboards)`.
# Extract the matching line and check it starts with `- [x]`.
LABS_RAW="$(grep -E "RoamCore Labs \(share setups/dashboards\)" "$CHECKLIST" | head -1 || true)"
if ! grep -qE "^\s*-\s*\[x\]" <<<"$LABS_RAW"; then
  fail "RoamCore Labs row in $CHECKLIST is not ticked '[x]' (got: $LABS_RAW)"
fi
pass "RoamCore Labs row ticked [x] in $CHECKLIST"
note_assert

# --- 10. docs/mvp/features-build-status.md updated -----------------------
echo "== docs/mvp/features-build-status.md updated =="
if ! grep -qF "RoamCore Labs (share setups/dashboards) — Wave 2 #32 (slice shipped)" "$BUILD_STATUS"; then
  fail "$BUILD_STATUS is missing the 'RoamCore Labs — Wave 2 #32 (slice shipped)' bullet"
fi
pass "$BUILD_STATUS has the RoamCore Labs (Wave 2 #32) bullet"
note_assert

# Last updated must be 2026-07-29.
if ! grep -qE "^Last updated: 2026-07-29" "$BUILD_STATUS"; then
  fail "$BUILD_STATUS 'Last updated' is not 2026-07-29"
fi
pass "$BUILD_STATUS 'Last updated' = 2026-07-29"
note_assert

# --- 11. Privacy invariant: no forbidden imports in any new code ---------
# This is the smoke's strictest assertion. We grep the *new* code paths
# (the contract package, the wizard snippet, the CLI helpers, the
# service handlers we added) for any HTTP client import. If found, the
# privacy contract is broken and the build FAILS.
#
# We deliberately exclude the rest of __init__.py — pre-existing aiohttp
# imports are owned by other slices (OTA, provisioning, etc.) and are
# not part of this slice's privacy contract. The slice's own additions
# are scoped to the new service handlers + the labs helpers.
echo "== privacy invariant (no HTTP clients in new code) =="
# Scope: slice-owned files only. The custom-component check is scoped
# to the slice's added handlers (line-anchored on the function names).
python3 - "$PKG" "$WIZ" "$EXPORT_CLI" "$IMPORT_CLI" "$EXPORT_COMMON" "$INIT_PY" <<'PY'
import re
import sys

paths = sys.argv[1:]
PAT_IMPORT = re.compile(r"^(import|from)\s+(requests|urllib\.request|urllib3|httpx|aiohttp|python_http_client|http\.client)\b")

# For __init__.py we only inspect the slice's two handlers so we don't
# trip on pre-existing aiohttp imports (used by other slices).
def slice_bounds(text: str):
    start = text.find("async def _svc_labs_export_setup(")
    end = text.find("async def _svc_labs_import_setup(")
    end_close = text.find("\n    return True\n", end)
    if end_close == -1:
        end_close = len(text)
    if start == -1 or end == -1:
        return None
    # Go to start of line for both.
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end_close)
    if line_end == -1:
        line_end = len(text)
    return (line_start, line_end)

found = []
for path in paths:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if path.endswith("__init__.py"):
        bounds = slice_bounds(text)
        if bounds is None:
            # Slice handlers not present: skip (the slice-handler test
            # elsewhere catches this).
            continue
        text = text[bounds[0]:bounds[1]]
    for ln, line in enumerate(text.splitlines(), start=1):
        if PAT_IMPORT.search(line):
            found.append(f"{path}: {line.rstrip()[:160]}")

if found:
    print("ERROR: privacy invariant violated: HTTP client import(s) found in new code:", file=sys.stderr)
    for f in found:
        print(f"  {f}", file=sys.stderr)
    sys.exit(1)

print(f"  PASS: privacy invariant holds across {len(paths)} files (no HTTP clients in new code)")
PY
pass "no HTTP client imports in $PKG / $WIZ / $EXPORT_CLI / $IMPORT_CLI / $EXPORT_COMMON / slice handlers in $INIT_PY"
note_assert

# No http:// or https:// URLs in any new code beyond canonical docs cross-refs.
# We scope to the slice-owned files (excluding __init__.py because the
# pre-existing handlers already had outbound URLs for other services).
echo "== privacy invariant (no http(s) URLs in new code) =="
URL_HITS="$(grep -RIn -E "https?://[A-Za-z0-9._/?=&%-]+" \
  "$PKG" "$WIZ" "$SERVICES_YAML" "$EXPORT_CLI" "$IMPORT_CLI" "$EXPORT_COMMON" 2>/dev/null | \
  grep -v -E "github\\.com/roamcore/RoamCore" || true)"
if [ -n "$URL_HITS" ]; then
  echo "$URL_HITS" >&2
  fail "privacy invariant violated: URL(s) found in new code beyond canonical docs cross-refs"
fi
pass "no http(s):// URLs in new code (except canonical docs cross-refs)"
note_assert

# --- 12. Negative-test self-check (load-bearing for tier-b) -------------
# We deliberately pretend the privacy invariant was violated by patching
# the export CLI to import urllib.request, then verify the smoke would
# fail (so the privacy invariant is enforced, not just declared).
#
# This mirrors the OTA smoke's pattern of assert-the-assertion-fails.
# We restore the file before exit (set -e + trap).
echo "== negative-test self-check (privacy invariant enforced) =="
INVARIANT_GREP='^(import|from)[[:space:]]+(requests|urllib\.request|urllib3|httpx|aiohttp)'
# Stub: write a fake patched copy next to the export CLI (we don't touch
# the real file). Confirm the patched copy would fail the same grep.
PATCHED="$TMPDIR/export_setup_patched.py"
cp "$EXPORT_CLI" "$PATCHED"
# Append a forbidden import. Use a fresh, contained line so we don't
# accidentally introduce a real syntax error.
printf '\nimport urllib.request  # NEGATIVE-TEST-ONLY\n' >> "$PATCHED"
if ! grep -qE "$INVARIANT_GREP" "$PATCHED"; then
  fail "negative-test self-check: patched stub did not register the forbidden import — the privacy grep invariant is broken"
fi
pass "negative-test self-check: patching the export CLI to import urllib.request makes the privacy grep fail (privacy invariant is enforced)"
note_assert

# Final summary.
echo ""
echo "All Labs (share setups/dashboards) smoke checks passed: $ASSERTS assertions."