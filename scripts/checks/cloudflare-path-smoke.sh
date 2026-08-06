#!/usr/bin/env bash
# scripts/checks/cloudflare-path-smoke.sh
#
# Wave 9 #122.b — Phase 6 Cloudflare Tunnel (Path B). Repo-local
# verification of the Path B addition to the wizard: the new
# `cloudflare_tunnel` setup-path entry in
# connections/remote-access/connection.yml + the new
# `rc_remote_access_cloudflare_*` helpers in
# homeassistant/packages/roamcore_remote_access_setup.yaml +
# the new tests in tests/test_connection_yml.py +
# the user-facing IKEA doc at docs/catalog/remote-access/cloudflare.md.
#
# Mirrors the convention in scripts/checks/<name>.sh:
#   - bash strict mode (set -euo pipefail)
#   - repo-local only (no live HA / Proxmox / OpenWrt calls)
#   - 6+ plain-English assertions covering: YAML parses, both
#     Path A + Path B appear in path choices, secret: true marker
#     on the Cloudflare token, rc-entity-naming compliance,
#     pytest test count ≥4 for the new Cloudflare tests, secrets-
#     leak grep on the new YAML + Python files.
#   - plain-English summary at exit 0 / non-zero exit
#
# Doctrine (Bernard, 2026-08-04): must not fail + super intuitive +
# critical infrastructure. This script is a defensive guard that
# catches regressions before they land on main.
#
# Idempotent — safe to run repeatedly.
#
# Usage:
#   bash scripts/checks/cloudflare-path-smoke.sh
#
# Exit codes:
#   0  all 6+ assertions passed (PASS)
#   1  one or more assertions failed (FAIL — see summary above)
#
# Wired into scripts/check.sh as a `run_if_present` step in the
# core-only chain (next to the other connection smokes).

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

MANIFEST="$ROOT_DIR/connections/remote-access/connection.yml"
PACKAGE="$ROOT_DIR/homeassistant/packages/roamcore_remote_access_setup.yaml"
PYTEST_REMOTE="$ROOT_DIR/connections/remote-access/tests/test_connection_yml.py"
PYTEST_PACKAGE="$ROOT_DIR/homeassistant/packages/tests/test_remote_access_setup.py"
IKEA_DOC="$ROOT_DIR/docs/catalog/remote-access/cloudflare.md"

fail=0
pass=0

note_pass() { printf '  \033[1;32m✓\033[0m %s\n' "$1"; pass=$((pass+1)); }
note_fail() { printf '  \033[1;31m✗\033[0m %s\n' "$1"; fail=$((fail+1)); }

echo
echo "▶ Cloudflare Path B (Wave 9 #122.b): file presence"

for f in "$MANIFEST" "$PACKAGE" "$PYTEST_REMOTE" "$PYTEST_PACKAGE" "$IKEA_DOC"; do
  if [ -f "$f" ]; then
    note_pass "file exists: ${f#$ROOT_DIR/}"
  else
    note_fail "missing file: ${f#$ROOT_DIR/}"
  fi
done

# If any file is missing, abort early — the remaining assertions
# would all fail and produce noisy output.
if [ "$fail" -gt 0 ]; then
  echo
  echo "Summary"
  echo "======="
  printf '  PASS: %d\n' "$pass"
  printf '  FAIL: %d\n' "$fail"
  printf '\n\033[1;31m✗ cloudflare path smoke FAILED (missing file(s))\033[0m\n'
  exit 1
fi

echo
echo "▶ Cloudflare Path B: YAML parses (manifest + package)"

if python3 -c "import yaml; yaml.safe_load(open('$MANIFEST'))" 2>/dev/null; then
  note_pass "manifest YAML parses (connection.yml)"
else
  note_fail "manifest YAML parse error — see python3 output above"
fi

if python3 -c "import yaml; yaml.safe_load(open('$PACKAGE'))" 2>/dev/null; then
  note_pass "package YAML parses (roamcore_remote_access_setup.yaml)"
else
  note_fail "package YAML parse error — see python3 output above"
fi

echo
echo "▶ Cloudflare Path B: both Path A (tailscale) + Path B (cloudflare_tunnel) in path choices"

path_check=$(python3 - "$PACKAGE" <<'PYEOF'
import sys, yaml
data = yaml.safe_load(open(sys.argv[1]))
opts = (data["input_select"]["rc_remote_access_setup_path"]["options"]) or []
expected_paths = {"tailscale", "cloudflare_tunnel"}
missing = expected_paths - set(opts)
if missing:
    print(f"MISSING: {sorted(missing)}")
    sys.exit(1)
PYEOF
) || true
if [ -z "$path_check" ]; then
  note_pass "both Path A (tailscale) and Path B (cloudflare_tunnel) appear in input_select.rc_remote_access_setup_path options"
else
  note_fail "path-choice gap: $path_check"
fi

echo
echo "▶ Cloudflare Path B: secret: true marker on the Cloudflare tunnel token"

secret_check=$(python3 - "$MANIFEST" "$PACKAGE" <<'PYEOF'
import sys, yaml
manifest = yaml.safe_load(open(sys.argv[1]))
package = yaml.safe_load(open(sys.argv[2]))

# (1) Manifest setup_paths entry: requires_inputs cloudflare_tunnel_token.secret
cf_paths = [p for p in (manifest.get("wizard", {}).get("setup_paths") or [])
            if p.get("id") == "cloudflare_tunnel"]
if not cf_paths:
    print("MISSING_CF_PATH")
    sys.exit(1)
cf_path = cf_paths[0]
token_input = next((i for i in cf_path.get("requires_inputs", [])
                    if i.get("field") == "cloudflare_tunnel_token"), None)
if token_input is None:
    print("MISSING_TOKEN_INPUT")
    sys.exit(1)
if not token_input.get("secret") is True:
    print(f"MANIFEST_SECRET={token_input.get('secret')!r}")
    sys.exit(1)

# (2) Package helper: input_text.rc_remote_access_cloudflare_token.mode
helpers = package.get("input_text", {}) or {}
helper = helpers.get("rc_remote_access_cloudflare_token")
if helper is None:
    print("MISSING_HELPER")
    sys.exit(1)
if helper.get("mode") != "password":
    print(f"PKG_MODE={helper.get('mode')!r}")
    sys.exit(1)
PYEOF
) || true
if [ -z "$secret_check" ]; then
  note_pass "secret: true marker present on cloudflare_tunnel_token (manifest) + mode: password on rc_remote_access_cloudflare_token (package)"
else
  note_fail "secret marker missing: $secret_check"
fi

echo
echo "▶ Cloudflare Path B: rc-entity-naming compliance (every new entity starts with rc_remote_access_)"

naming_check=$(python3 - "$PACKAGE" <<'PYEOF'
import sys, yaml
package = yaml.safe_load(open(sys.argv[1]))

allowed_prefixes = ("rc_remote_access_", "rc_cloudflare_", "rc_tailscale_", "rc_setup_")
violations = []

# Check the package's helpers (input_select / input_text / input_boolean)
# — every entity_id MUST start with one of the allowed prefixes.
for kind in ("input_select", "input_text", "input_boolean", "input_number", "input_datetime"):
    for eid in (package.get(kind) or {}).keys():
        if not any(eid.startswith(p) for p in allowed_prefixes):
            violations.append(f"PKG:{kind}.{eid}")

if violations:
    for v in violations:
        print(f"  VIOLATION: {v}")
    sys.exit(1)
PYEOF
) || true
if [ -z "$naming_check" ]; then
  note_pass "every new entity_id complies with docs/reference/rc-entity-naming.md"
else
  note_fail "rc-naming violations found"
  echo "$naming_check"
fi

echo
echo "▶ Cloudflare Path B: pytest test count for the new Cloudflare tests ≥5"

test_count=$(grep -cE '^def test_cloudflare_path_in_setup_paths\(|^def test_cloudflare_path_has_token_secret_marker\(|^def test_cloudflare_path_does_not_require_reboot\(|^def test_cloudflare_path_idempotency\(|^def test_cloudflare_path_retry_with_backoff\(|^def test_describe_cloudflare_setup_path\(|^def test_cloudflare_appears_in_path_choice\(|^def test_cloudflare_password_field_uses_password_mode\(|^def test_path_a_inputs_preserved_bit_for_bit\(|^def test_cloudflare_setup_automation_idempotency\(' "$PYTEST_REMOTE" "$PYTEST_PACKAGE" 2>/dev/null | awk -F: '{sum += $2} END {print sum}')
if [ -n "$test_count" ] && [ "$test_count" -ge 5 ]; then
  note_pass "found $test_count new Cloudflare-related tests (≥5 required by the slice spec)"
else
  note_fail "found ${test_count:-0} new Cloudflare tests; need ≥5"
fi

echo
echo "▶ Cloudflare Path B: secrets-leak grep on the new YAML + Python files"

# Search for hardcoded Cloudflare tunnel tokens / real hostnames
# in the new files. The grep must NOT match the placeholder
# patterns (`<CLOUDFLARE_TUNNEL_TOKEN>`, `my-van.example.com`,
# `one.dash.cloudflare.com`).
SECRETS_LEAK=$(grep -E '(eyJhI[A-Za-z0-9+/=]{40,}|CF[A-Za-z0-9]{40,}==|tskey-[A-Za-z0-9_-]{10,})' "$MANIFEST" "$PACKAGE" "$PYTEST_REMOTE" "$PYTEST_PACKAGE" "$IKEA_DOC" 2>/dev/null | grep -v '^Binary' || true)
if [ -z "$SECRETS_LEAK" ]; then
  note_pass "no hardcoded tokens / secrets leaked in new files (placeholders allowed)"
else
  note_fail "SECRET PATTERN FOUND in new files — operator credentials MUST NOT be committed"
  echo "$SECRETS_LEAK"
fi

echo
echo "Summary"
echo "======="
printf '  PASS: %d\n' "$pass"
printf '  FAIL: %d\n' "$fail"

if [ "$fail" -gt 0 ]; then
  printf '\n\033[1;31m✗ cloudflare path smoke FAILED\033[0m\n'
  exit 1
fi

printf '\n\033[1;32m✓ cloudflare path smoke PASSED\033[0m\n'
exit 0