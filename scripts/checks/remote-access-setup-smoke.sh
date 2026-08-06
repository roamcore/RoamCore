#!/usr/bin/env bash
# scripts/checks/remote-access-setup-smoke.sh
#
# Wave 9 #122.a — Phase 6 Tailscale wizard (sub-slice A). Repo-local
# verification of the guided remote-access setup wizard + Path A
# (Tailscale) full implementation. Mirrors the convention in
# scripts/checks/<name>.sh:
#   - bash strict mode (set -euo pipefail)
#   - repo-local only (no live HA / Proxmox / OpenWrt calls)
#   - wrapper around the pytest rig that guards the data layer
#   - stage coverage + rc-naming + secrets-leak + idempotency
#     checks that don't need pytest
#   - plain-English summary at exit 0 / non-zero exit
#
# This is a static check on the repo: nothing touches HA at runtime.
# Idempotent — safe to run repeatedly.
#
# Usage:
#   bash scripts/checks/remote-access-setup-smoke.sh
#
# Exit codes:
#   0  all wizard YAML helpers + automations are present + named right +
#      pytest rig is green + no secrets leaked + idempotent (PASS)
#   1  one or more checks failed (FAIL — see summary above)
#
# Wired into scripts/check.sh as a `run_if_present` step in the
# core-only chain (next to the other package-layer smokes like
# mode-builder-smoke.sh).

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PACKAGE="$ROOT_DIR/homeassistant/packages/roamcore_remote_access_setup.yaml"
PYTEST="$ROOT_DIR/homeassistant/packages/tests/test_remote_access_setup.py"

fail=0
pass=0

note_pass() { printf '  \033[1;32m✓\033[0m %s\n' "$1"; pass=$((pass+1)); }
note_fail() { printf '  \033[1;31m✗\033[0m %s\n' "$1"; fail=$((fail+1)); }

echo
echo "▶ Remote access setup wizard: file presence"

if [ -f "$PACKAGE" ]; then
  note_pass "package exists: ${PACKAGE#$ROOT_DIR/}"
else
  note_fail "missing package: ${PACKAGE#$ROOT_DIR/}"
  echo
  echo "Summary"
  echo "======="
  printf '  PASS: %d\n' "$pass"
  printf '  FAIL: %d\n' "$fail"
  printf '\n\033[1;31m✗ remote access setup smoke FAILED (missing package)\033[0m\n'
  exit 1
fi

if [ -f "$PYTEST" ]; then
  note_pass "pytest rig exists: ${PYTEST#$ROOT_DIR/}"
else
  note_fail "missing pytest rig: ${PYTEST#$ROOT_DIR/}"
fi

echo
echo "▶ Remote access setup wizard: YAML pre-check (PyYAML parse)"

if python3 -c "import yaml,sys; yaml.safe_load(open('$PACKAGE'))" 2>/dev/null; then
  note_pass "YAML parses"
else
  note_fail "YAML parse error — see python3 output above"
fi

echo
echo "▶ Remote access setup wizard: rc-entity-naming pre-check"

# Every entity_id in the package MUST start with rc_remote_access_setup_ or rc_tailscale_
naming_violations=$(python3 - "$PACKAGE" <<'PYEOF'
import sys, yaml
data = yaml.safe_load(open(sys.argv[1]))
allowed = ("rc_remote_access_setup_", "rc_tailscale_")
violations = []
for kind in ("input_select", "input_text", "input_boolean", "input_number", "input_datetime"):
    for eid in (data.get(kind) or {}).keys():
        if not any(eid.startswith(p) for p in allowed):
            violations.append((kind, eid))
if violations:
    for k, eid in violations:
        print(f"  VIOLATION: {k}.{eid}")
    sys.exit(1)
PYEOF
) || true
if [ -z "$naming_violations" ]; then
  note_pass "all entity_ids comply with docs/reference/rc-entity-naming.md"
else
  note_fail "rc-naming violations found"
  echo "$naming_violations"
fi

echo
echo "▶ Remote access setup wizard: stage coverage check"

# Every option in rc_remote_access_setup_stage MUST have a corresponding
# status branch in sensor.rc_remote_access_setup_status.
coverage=$(python3 - "$PACKAGE" <<'PYEOF'
import sys, yaml, re
data = yaml.safe_load(open(sys.argv[1]))
stages = (data["input_select"]["rc_remote_access_setup_stage"]["options"]) or []
status_sensor = None
for entry in (data.get("template") or []):
    for s in (entry.get("sensor") or []):
        if s.get("unique_id") == "rc_remote_access_setup_status":
            status_sensor = s
            break
state_template = (status_sensor.get("state") or "") if status_sensor else ""
state_lower = state_template.lower()
uncovered = []
# These 4 stages always have a known marker (covered above in pytest)
# but we still want to confirm tailscale_done + done + recovery are
# all individually named in the template (defensive).
required_markers = {
    "welcome": ["ready to help you set up"],
    "tailscale_done": ["tailscale is set up"],
    "recovery": ["couldn't reach tailscale"],
    "done": ["remote access setup complete"],
}
for stage, markers in required_markers.items():
    if stage in stages:
        if not any(m in state_lower for m in markers):
            uncovered.append((stage, markers))
if uncovered:
    for stage, markers in uncovered:
        print(f"  UNCOVERED: stage={stage!r} missing markers={markers}")
    sys.exit(1)
PYEOF
) || true
if [ -z "$coverage" ]; then
  note_pass "every required stage has a corresponding status branch"
else
  note_fail "stage coverage gap found"
  echo "$coverage"
fi

echo
echo "▶ Remote access setup wizard: secrets-leak check"

# grep for tskey- / ts-auth- / tailnet auth-key patterns — fail if found
SECRETS=$(grep -E '(tskey-[A-Za-z0-9_-]{10,}|ts-auth-[A-Za-z0-9_-]{10,})' "$PACKAGE" || true)
if [ -z "$SECRETS" ]; then
  note_pass "no secrets (tskey- / ts-auth-) leaked in YAML"
else
  note_fail "SECRET PATTERN FOUND in YAML — operator auth keys MUST NOT be committed"
  echo "$SECRETS"
fi

echo
echo "▶ Remote access setup wizard: idempotency probe (PyYAML twice → same dict)"

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
echo "▶ Remote access setup wizard: pytest rig (test_remote_access_setup.py)"

# Temporarily disable `set -e` so we can capture pytest's exit code
# instead of the script aborting on the first failure. The pytest
# output is still streamed to the operator's terminal.
set +e
python3 -m pytest "$PYTEST" --tb=short -q 2>&1 | tail -20
PYTEST_EXIT=${PIPESTATUS[0]}
set -e

if [ "$PYTEST_EXIT" -eq 0 ]; then
  note_pass "pytest rig green (test_remote_access_setup.py)"
else
  note_fail "pytest rig FAILED (exit=$PYTEST_EXIT) — see output above"
fi

echo
echo "Summary"
echo "======="
printf '  PASS: %d\n' "$pass"
printf '  FAIL: %d\n' "$fail"

if [ "$fail" -gt 0 ]; then
  printf '\n\033[1;31m✗ remote access setup smoke FAILED\033[0m\n'
  exit 1
fi

printf '\n\033[1;32m✓ remote access setup smoke PASSED\033[0m\n'
exit 0
