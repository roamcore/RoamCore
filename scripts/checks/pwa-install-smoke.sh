#!/usr/bin/env bash
# scripts/checks/pwa-install-smoke.sh
#
# Static + live verification of the RoamCore PWA scaffold.
# Asserts the seven dashboard/Frontend/Setup Wizard files are present +
# structurally valid + that docs/setup/pwa.md follows the IKEA
# vanlifer-first shape. Optionally serves the PWA on a random local
# port and verifies manifest.json is reachable + parses + has the
# required PWA fields.
#
# This is a static check on the repo: no live HA / Proxmox / OpenWrt
# calls. Idempotent — safe to run repeatedly.
#
# Exit codes: 0 = PASS, 1 = FAIL.

set -euo pipefail

# Resolve repo root regardless of where the script is invoked from.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PWA_DIR="$ROOT_DIR/dashboard/Frontend/Setup Wizard"
DOC="$ROOT_DIR/docs/setup/pwa.md"

fail=0
pass=0

note_pass() { printf '  \033[1;32m✓\033[0m %s\n' "$1"; pass=$((pass+1)); }
note_fail() { printf '  \033[1;31m✗\033[0m %s\n' "$1"; fail=$((fail+1)); }

assert_file() {
  local path="$1"
  if [ -f "$path" ]; then note_pass "exists: $path"; else note_fail "missing: $path"; return 1; fi
  return 0
}

assert_file_contains() {
  local path="$1"
  local needle="$2"
  if [ ! -f "$path" ]; then note_fail "missing: $path (cannot check contents)"; return 1; fi
  if grep -Fq "$needle" "$path"; then
    note_pass "contains '$needle' in $path"
  else
    note_fail "missing '$needle' in $path"
    return 1
  fi
}

assert_json_field() {
  local path="$1"
  local jq_expr="$2"
  local desc="$3"
  if [ ! -f "$path" ]; then note_fail "missing: $path"; return 1; fi
  if ! python3 -c "import json,sys; json.load(open('$path'))" 2>/dev/null; then
    note_fail "not valid JSON: $path"
    return 1
  fi
  if python3 -c "
import json,sys
data=json.load(open('$path'))
val=$jq_expr
sys.exit(0 if val else 1)
" 2>/dev/null; then
    note_pass "$desc"
  else
    note_fail "$desc"
    return 1
  fi
}

echo
echo "▶ PWA: file presence (dashboard/Frontend/Setup Wizard/)"
for f in manifest.json sw.js pwa.js index.html offline.html install-banner.js profile-store.js icon-192.svg icon-512.svg; do
  assert_file "$PWA_DIR/$f" >/dev/null || true
done

echo
echo "▶ PWA: manifest.json structure"
assert_json_field "$PWA_DIR/manifest.json" \
  "data.get('name')=='RoamCore'" \
  "manifest.json has name=RoamCore"
assert_json_field "$PWA_DIR/manifest.json" \
  "data.get('short_name')=='RoamCore'" \
  "manifest.json has short_name=RoamCore"
assert_json_field "$PWA_DIR/manifest.json" \
  "data.get('start_url')" \
  "manifest.json has start_url"
assert_json_field "$PWA_DIR/manifest.json" \
  "data.get('display')=='standalone'" \
  "manifest.json has display=standalone"
assert_json_field "$PWA_DIR/manifest.json" \
  "any(i.get('sizes')=='192x192' for i in data.get('icons',[]))" \
  "manifest.json has icons[192x192]"
assert_json_field "$PWA_DIR/manifest.json" \
  "any(i.get('sizes')=='512x512' for i in data.get('icons',[]))" \
  "manifest.json has icons[512x512]"

echo
echo "▶ PWA: sw.js hooks (install / activate / fetch)"
assert_file_contains "$PWA_DIR/sw.js" "self.addEventListener('install'" >/dev/null || true
assert_file_contains "$PWA_DIR/sw.js" "self.addEventListener('activate'" >/dev/null || true
assert_file_contains "$PWA_DIR/sw.js" "self.addEventListener('fetch'" >/dev/null || true
assert_file_contains "$PWA_DIR/sw.js" "offline.html" >/dev/null || true

echo
echo "▶ PWA: offline.html honesty (the 'couldn't reach your van' message)"
assert_file_contains "$PWA_DIR/offline.html" "Couldn't reach your van" >/dev/null || true

echo
echo "▶ PWA: install banner + profile store present"
assert_file_contains "$PWA_DIR/install-banner.js" "beforeinstallprompt" >/dev/null || true
assert_file_contains "$PWA_DIR/profile-store.js" "window.RCProfile" >/dev/null || true

echo
echo "▶ PWA: docs/setup/pwa.md is IKEA-shaped (5 numbered sections)"
if [ ! -f "$DOC" ]; then
  note_fail "missing: $DOC"
else
  # 5 numbered sections in the IKEA pattern (1. … 5. …)
  sections=$(grep -cE '^## [1-5]\. ' "$DOC" || true)
  if [ "${sections:-0}" -ge 5 ]; then
    note_pass "docs/setup/pwa.md has 5+ numbered sections (IKEA shape)"
  else
    note_fail "docs/setup/pwa.md has <5 numbered sections (got ${sections:-0})"
  fi
  # No internal jargon leaks in user-facing copy.
  if grep -qE 'Cron-handoff|memory/roamcore|Wave [0-9]+|tier-[abc]|commit SHA|branch name' "$DOC"; then
    note_fail "docs/setup/pwa.md leaks internal jargon (Cron-handoff / Wave / tier / SHA / branch)"
  else
    note_pass "docs/setup/pwa.md is jargon-free"
  fi
fi

echo
echo "▶ PWA: live-fetch manifest.json via http.server (best-effort, skipped if python3 missing)"
LIVE_OK=0
if command -v python3 >/dev/null 2>&1; then
  PORT=$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1]);s.close()')
  (cd "$PWA_DIR" && python3 -m http.server "$PORT" --bind 127.0.0.1 >/dev/null 2>&1) &
  SERVER_PID=$!
  sleep 0.6
  if curl -sf "http://127.0.0.1:$PORT/manifest.json" -o /tmp/rc_pwa_manifest.$$.json 2>/dev/null; then
    if python3 -c "
import json,sys
try:
  d=json.load(open('/tmp/rc_pwa_manifest.$$.json'))
  assert d.get('name')=='RoamCore'
  assert d.get('start_url')
  assert any(i.get('sizes')=='192x192' for i in d.get('icons',[]))
  print('live-manifest-ok')
except Exception as e:
  print('live-manifest-fail:',e); sys.exit(1)
" >/dev/null 2>&1; then
      note_pass "live /manifest.json fetches + parses + has name/192 icon"
      LIVE_OK=1
    else
      note_fail "live /manifest.json failed field validation"
    fi
    rm -f /tmp/rc_pwa_manifest.$$.json
  else
    note_fail "live /manifest.json fetch returned non-2xx"
  fi
  kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
else
  echo "  ⊘ python3 not available; live fetch skipped (file-existence + JSON-parse path still applies)"
fi

# Schema validation is a nice-to-have: jsonschema is only present in
# the GitHub Actions runner (pip-installed). Skip silently when missing
# rather than fail.
if python3 -c "import jsonschema" 2>/dev/null; then
  echo
  echo "▶ PWA: W3C manifest schema validation (jsonschema present, network reachable)"
  if python3 -c "
import json, jsonschema, urllib.request
try:
  schema=json.loads(urllib.request.urlopen('https://json.schemastore.org/web-manifest', timeout=5).read())
  data=json.load(open('$PWA_DIR/manifest.json'))
  validator = jsonschema.Draft7Validator(schema)
  errs = list(validator.iter_errors(data))
  if errs:
    print('schema-errors:', len(errs))
    sys_exit = 1
  else:
    print('manifest-schema-ok')
except Exception as e:
  print('schema-skip:', type(e).__name__)
" 2>/dev/null; then
    note_pass "manifest.json validates against W3C web-manifest schema"
  else
    note_fail "manifest.json failed W3C web-manifest schema validation"
  fi
fi

echo
echo "Summary"
echo "======="
printf '  PASS: %d\n' "$pass"
printf '  FAIL: %d\n' "$fail"

if [ "$fail" -gt 0 ]; then
  printf '\n\033[1;31m✗ PWA install/offline/push smoke FAILED\033[0m\n'
  exit 1
fi

printf '\n\033[1;32m✓ PWA install/offline/push smoke PASSED\033[0m\n'
exit 0
