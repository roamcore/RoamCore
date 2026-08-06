#!/usr/bin/env bash
# scripts/checks/tailscale-qr-smoke.sh
#
# Wave 9 #122.d.ii — Phase 6 Tailscale wizard QR code for mobile
# pairing (sub-slice d.ii). Repo-local verification of:
#   - the new package YAML (roamcore_tailscale_qr.yaml)
#   - the stdlib QR generator (scripts/qr_generator.py)
#   - the pytest rig (test_tailscale_qr.py)
#   - the IKEA user doc (docs/setup/tailscale-qr.md)
#
# Mirrors the convention in scripts/checks/<name>.sh:
#   - bash strict mode (set -euo pipefail)
#   - repo-local only (no live HA / Proxmox / OpenWrt calls)
#   - asserts file presence + YAML parse + rc-naming + secrets-leak
#     + pytest wrapper + IKEA doc shape + QR generator self-test.
#   - plain-English summary at exit 0 / non-zero.
#
# Usage:
#   bash scripts/checks/tailscale-qr-smoke.sh
#
# Exit codes:
#   0  all wizard helpers + automations + generator + doc are present +
#      named right + pytest rig is green + no secrets leaked (PASS)
#   1  one or more checks failed (FAIL — see summary above)
#
# Wired into scripts/check.sh as a `run_if_present` step.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PACKAGE="$ROOT_DIR/homeassistant/packages/roamcore_tailscale_qr.yaml"
PYTEST="$ROOT_DIR/homeassistant/packages/tests/test_tailscale_qr.py"
GENERATOR="$ROOT_DIR/homeassistant/packages/scripts/qr_generator.py"
DOC="$ROOT_DIR/docs/setup/tailscale-qr.md"

fail=0
pass=0

note_pass() { printf '  \033[1;32m✓\033[0m %s\n' "$1"; pass=$((pass+1)); }
note_fail() { printf '  \033[1;31m✗\033[0m %s\n' "$1"; fail=$((fail+1)); }

echo
echo "▶ Tailscale QR (mobile pairing): file presence"

for f in \
    "$PACKAGE" \
    "$PYTEST" \
    "$GENERATOR" \
    "$DOC"; do
    rel="${f#$ROOT_DIR/}"
    if [ -f "$f" ]; then
        note_pass "exists: $rel"
    else
        note_fail "missing: $rel"
    fi
done

echo
echo "▶ Tailscale QR: YAML pre-check (PyYAML parse)"

if python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" "$PACKAGE" 2>/dev/null; then
    note_pass "package YAML parses"
else
    note_fail "package YAML parse error — see python3 output above"
fi

echo
echo "▶ Tailscale QR: rc-entity-naming pre-check"

naming_violations=$(python3 - "$PACKAGE" <<'PYEOF'
import sys, yaml
data = yaml.safe_load(open(sys.argv[1]))
allowed_prefix = "rc_tailscale_qr_"
violations = []
for kind in ("input_text", "input_button", "input_boolean", "input_number",
             "input_datetime", "input_select"):
    for eid in (data.get(kind) or {}).keys():
        if not eid.startswith(allowed_prefix):
            violations.append((kind, eid))
for a in (data.get("automation") or []):
    aid = a.get("id") or ""
    if aid and not aid.startswith(allowed_prefix):
        violations.append(("automation", aid))
tpl = data.get("template") or []
for entry in tpl:
    for s in (entry.get("sensor") or []):
        uid = s.get("unique_id") or ""
        if uid and not uid.startswith(allowed_prefix):
            violations.append(("template sensor", uid))
    for bs in (entry.get("binary_sensor") or []):
        uid = bs.get("unique_id") or ""
        if uid and not uid.startswith(allowed_prefix):
            violations.append(("template binary_sensor", uid))
if violations:
    for k, eid in violations:
        print(f"  VIOLATION: {k}.{eid}")
    sys.exit(1)
PYEOF
) || true
if [ -z "$naming_violations" ]; then
    note_pass "all entity_ids comply with docs/reference/rc-entity-naming.md (rc_tailscale_qr_*)"
else
    note_fail "rc-naming violations found"
    echo "$naming_violations"
fi

echo
echo "▶ Tailscale QR: required helpers + automations + shell_command contract"

helper_check=$(python3 - "$PACKAGE" <<'PYEOF'
import sys, yaml
data = yaml.safe_load(open(sys.argv[1]))
required_helpers = {
    "input_text": [
        "rc_tailscale_qr_device_key",
        "rc_tailscale_qr_login_url",
        "rc_tailscale_qr_svg_path",
        "rc_tailscale_qr_nonce",
    ],
    "input_button": ["rc_tailscale_qr_regenerate"],
}
missing = []
for kind, ids in required_helpers.items():
    have = set((data.get(kind) or {}).keys())
    for eid in ids:
        if eid not in have:
            missing.append((kind, eid))
required_automations = {
    "rc_tailscale_qr_compute_login_url",
    "rc_tailscale_qr_regenerate_on_request",
}
have_aids = {a.get("id") for a in (data.get("automation") or [])}
for aid in required_automations:
    if aid not in have_aids:
        missing.append(("automation", aid))
shell = (data.get("shell_command") or {})
if "rc_tailscale_qr_render" not in shell:
    missing.append(("shell_command", "rc_tailscale_qr_render"))
if missing:
    for k, eid in missing:
        print(f"  MISSING: {k}.{eid}")
    sys.exit(1)
helper = (data.get("input_text") or {}).get("rc_tailscale_qr_device_key") or {}
if (helper.get("mode") or "").lower() != "password":
    print(f"  rc_tailscale_qr_device_key MUST be mode: password (got {helper.get('mode')!r})")
    sys.exit(1)
PYEOF
) || true
if [ -z "$helper_check" ]; then
    note_pass "all required helpers + automations + shell_command present + device_key is mode: password"
else
    note_fail "helper/automation contract gap"
    echo "$helper_check"
fi

echo
echo "▶ Tailscale QR: secrets-leak check"

SECRETS=$(grep -E '(tskey-[A-Za-z0-9_-]{10,}|ts-auth-[A-Za-z0-9_-]{10,})' "$PACKAGE" || true)
if [ -z "$SECRETS" ]; then
    note_pass "no secrets (tskey- / ts-auth-) leaked in YAML"
else
    note_fail "SECRET PATTERN FOUND in YAML — operator auth keys MUST NOT be committed"
    echo "$SECRETS"
fi

echo
echo "▶ Tailscale QR: idempotency probe (PyYAML twice → same dict)"

if python3 - "$PACKAGE" <<'PYEOF'
import sys, yaml
text = open(sys.argv[1]).read()
d1 = yaml.safe_load(text); d2 = yaml.safe_load(text)
if yaml.safe_dump(d1, sort_keys=True) != yaml.safe_dump(d2, sort_keys=True):
    print("NOT IDEMPOTENT — re-parsing diverges")
    sys.exit(1)
PYEOF
then
    note_pass "YAML is idempotent (re-parse produces identical dict)"
else
    note_fail "YAML is NOT idempotent — random IDs / timestamps / non-deterministic ordering"
fi

echo
echo "▶ Tailscale QR: QR generator stdlib-only + self-test"

GENERATOR_CHECK=$(python3 - "$GENERATOR" <<'PYEOF'
import ast, sys
src = open(sys.argv[1]).read()
tree = ast.parse(src)
allowed_modules = {
    "argparse", "math", "sys", "xml.etree.ElementTree",
    "itertools", "typing", "__future__",
}
bad = []
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        for alias in node.names:
            if alias.name not in allowed_modules:
                bad.append(("import", alias.name))
    elif isinstance(node, ast.ImportFrom):
        module = node.module or ""
        if module not in allowed_modules:
            bad.append(("from", module))
if bad:
    for kind, mod in bad:
        print(f"  NON-STDLIB: {kind} {mod}")
    sys.exit(1)
PYEOF
) || true
if [ -z "$GENERATOR_CHECK" ]; then
    note_pass "QR generator is stdlib-only (no qrcode / segno / qrencode)"
else
    note_fail "QR generator pulls in non-stdlib modules"
    echo "$GENERATOR_CHECK"
fi

if python3 "$GENERATOR" --self-test 2>&1 | grep -q "self-test OK"; then
    note_pass "QR generator self-test exits 0"
else
    note_fail "QR generator self-test FAILED — see python3 output above"
fi

TMP_SVG="$(mktemp /tmp/qr-smoke-XXXXXX.svg)"
if python3 "$GENERATOR" "https://login.tailscale.com/a/test-abc123" 256 "$TMP_SVG" 2>&1 \
        | grep -q "^OK:" \
        && [ -f "$TMP_SVG" ] \
        && grep -q 'viewBox="0 0 256 256"' "$TMP_SVG" \
        && python3 -c "
import xml.etree.ElementTree as ET
svg = open('$TMP_SVG').read()
root = ET.fromstring(svg)
rects = root.findall('{http://www.w3.org/2000/svg}rect')
dark = [r for r in rects if (r.get('fill') or '').lower() == 'black']
assert len(dark) >= 1, 'no dark modules'
"; then
    note_pass "QR renderer produces valid SVG with correct viewBox + ≥1 dark module"
else
    note_fail "QR renderer did NOT produce valid SVG for canonical Tailscale URL"
fi
rm -f "$TMP_SVG"

echo
echo "▶ Tailscale QR: IKEA doc shape (5 numbered sections, no jargon)"

if [ -f "$DOC" ]; then
    if grep -q '§1' "$DOC" && grep -q '§2' "$DOC" && grep -q '§3' "$DOC" \
            && grep -q '§4' "$DOC" && grep -q '§5' "$DOC"; then
        note_pass "doc has 5 numbered sections (§1..§5)"
    else
        note_fail "doc missing one or more of §1..§5"
    fi
    BODY=$(awk '/§5/{exit} {print}' "$DOC")
    JARGON_FOUND=$(echo "$BODY" | grep -E -i "(integration|entity|shell_command|automation|input_text|binary_sensor|template sensor)" || true)
    if [ -z "$JARGON_FOUND" ]; then
        note_pass "doc §1..§4 contains no operator jargon"
    else
        note_fail "doc §1..§4 contains operator jargon"
        echo "$JARGON_FOUND"
    fi
    CRON_FOUND=$(grep -i -E "(cron |sub-agent|wave [0-9])" "$DOC" || true)
    if [ -z "$CRON_FOUND" ]; then
        note_pass "doc has no cron / sub-agent / Wave references"
    else
        note_fail "doc contains internal-speak: cron / sub-agent / Wave"
        echo "$CRON_FOUND"
    fi
else
    note_fail "IKEA doc missing at $DOC"
fi

echo
echo "▶ Tailscale QR: pytest rig (test_tailscale_qr.py)"

set +e
python3 -m pytest "$PYTEST" --tb=short -q 2>&1 | tail -20
PYTEST_EXIT=${PIPESTATUS[0]}
set -e

if [ "$PYTEST_EXIT" -eq 0 ]; then
    note_pass "pytest rig green (test_tailscale_qr.py)"
else
    note_fail "pytest rig FAILED (exit=$PYTEST_EXIT) — see output above"
fi

echo
echo "Summary"
echo "======="
printf '  PASS: %d\n' "$pass"
printf '  FAIL: %d\n' "$fail"

if [ "$fail" -gt 0 ]; then
    printf '\n\033[1;31m✗ tailscale qr smoke FAILED\033[0m\n'
    exit 1
fi

printf '\n\033[1;32m✓ tailscale qr smoke PASSED\033[0m\n'
exit 0
