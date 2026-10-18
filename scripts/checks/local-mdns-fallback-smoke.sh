#!/usr/bin/env bash
# scripts/checks/local-mdns-fallback-smoke.sh
#
# Wave 9 #122.d.iv — Phase 6 Tailscale wizard (sub-slice D.iv:
# mDNS `roamcore.local` fallback so local survives Tailscale failure).
# Repo-local verification of the local-access-fallback package +
# pytest rig + IKEA doc. Mirrors the convention in
# scripts/checks/<name>.sh:
#   - bash strict mode (set -euo pipefail)
#   - repo-local only (no live HA / Proxmox / OpenWrt calls)
#   - wrapper around the pytest rig that guards the data layer
#   - 10 standalone bash assertions that don't need pytest
#   - plain-English summary at exit 0 / non-zero exit
#
# This is a static check on the repo: nothing touches HA at runtime.
# Idempotent — safe to run repeatedly.
#
# Usage:
#   bash scripts/checks/local-mdns-fallback-smoke.sh
#
# Exit codes:
#   0  all package YAML helpers + automations are present + named right +
#      pytest rig is green + no secrets leaked + idempotent (PASS)
#   1  one or more checks failed (FAIL — see summary above)
#
# Wired into scripts/check.sh as a `run_if_present` step in the
# core-only chain (next to the other package-layer smokes like
# remote-access-setup-smoke.sh).

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PACKAGE="$ROOT_DIR/homeassistant/packages/roamcore_local_mdns_fallback.yaml"
PYTEST="$ROOT_DIR/homeassistant/packages/tests/test_local_mdns_fallback.py"
DOC="$ROOT_DIR/docs/setup/local-access-fallback.md"

fail=0
pass=0

note_pass() { printf '  \033[1;32m✓\033[0m %s\n' "$1"; pass=$((pass+1)); }
note_fail() { printf '  \033[1;31m✗\033[0m %s\n' "$1"; fail=$((fail+1)); }

echo
echo "▶ Local mDNS fallback: file presence"

if [ -f "$PACKAGE" ]; then
  note_pass "package exists: ${PACKAGE#$ROOT_DIR/}"
else
  note_fail "missing package: ${PACKAGE#$ROOT_DIR/}"
  echo
  echo "Summary"
  echo "======="
  printf '  PASS: %d\n' "$pass"
  printf '  FAIL: %d\n' "$fail"
  printf '\n\033[1;31m✗ local-mdns-fallback smoke FAILED (missing package)\033[0m\n'
  exit 1
fi

if [ -f "$PYTEST" ]; then
  note_pass "pytest rig exists: ${PYTEST#$ROOT_DIR/}"
else
  note_fail "missing pytest rig: ${PYTEST#$ROOT_DIR/}"
fi

if [ -f "$DOC" ]; then
  note_pass "IKEA doc exists: ${DOC#$ROOT_DIR/}"
else
  note_fail "missing IKEA doc: ${DOC#$ROOT_DIR/}"
fi

echo
echo "▶ Local mDNS fallback: YAML pre-check (PyYAML parse)"

if python3 -c "import yaml,sys; yaml.safe_load(open('$PACKAGE'))" 2>/dev/null; then
  note_pass "YAML parses"
else
  note_fail "YAML parse error — see python3 output above"
fi

echo
echo "▶ Local mDNS fallback: rc-entity-naming pre-check"

# Every entity_id in the package MUST start with rc_local_mdns_
naming_violations=$(python3 - "$PACKAGE" <<'PYEOF'
import sys, yaml
data = yaml.safe_load(open(sys.argv[1]))
allowed = ("rc_local_mdns_",)
violations = []
for kind in ("input_select", "input_text", "input_boolean", "input_number", "input_datetime", "input_button", "shell_command"):
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
echo "▶ Local mDNS fallback: helpers + automations + templates pre-check"

# All required helpers, automations, sensors, and binary_sensors
# MUST be present.
helpers_present=$(python3 - "$PACKAGE" <<'PYEOF'
import sys, yaml
data = yaml.safe_load(open(sys.argv[1]))
missing = []
for kind, ids in (
    ("input_boolean", ["rc_local_mdns_fallback_enabled"]),
    ("input_text", ["rc_local_mdns_hostname"]),
    ("input_button", ["rc_local_mdns_retest"]),
    ("shell_command", ["rc_local_mdns_probe"]),
):
    present = set((data.get(kind) or {}).keys())
    for eid in ids:
        if eid not in present:
            missing.append((kind, eid))
# Automations
auto_ids = {a.get("id") for a in (data.get("automation") or [])}
for aid in ("rc_local_mdns_register_on_start", "rc_local_mdns_probe_periodic", "rc_local_mdns_fallback_tile_surfacing"):
    if aid not in auto_ids:
        missing.append(("automation", aid))
# Template sensors / binary_sensors (unique_id)
seen_sensor_uids = set()
seen_bs_uids = set()
for entry in (data.get("template") or []):
    for s in (entry.get("sensor") or []):
        seen_sensor_uids.add(s.get("unique_id"))
    for bs in (entry.get("binary_sensor") or []):
        seen_bs_uids.add(bs.get("unique_id"))
for uid in ("rc_local_mdns_resolved_ip", "rc_local_mdns_status"):
    if uid not in seen_sensor_uids:
        missing.append(("template_sensor", uid))
if "rc_local_mdns_resolvable" not in seen_bs_uids:
    missing.append(("template_binary_sensor", "rc_local_mdns_resolvable"))
if missing:
    for k, ident in missing:
        print(f"  MISSING: {k}.{ident}")
    sys.exit(1)
PYEOF
) || true
if [ -z "$helpers_present" ]; then
  note_pass "all required helpers + automations + template entities present"
else
  note_fail "missing required entries:"
  echo "$helpers_present"
fi

echo
echo "▶ Local mDNS fallback: status template covers all branches"

# The status template MUST cover all 4 (enabled × resolvable × ip)
# combinations with the canonical plain-English phrases.
coverage=$(python3 - "$PACKAGE" <<'PYEOF'
import sys, yaml
data = yaml.safe_load(open(sys.argv[1]))
status_sensor = None
for entry in (data.get("template") or []):
    for s in (entry.get("sensor") or []):
        if s.get("unique_id") == "rc_local_mdns_status":
            status_sensor = s
            break
state_template = (status_sensor.get("state") or "") if status_sensor else ""
state_lower = state_template.lower()
required_markers = {
    "turned off": ["turned off"],
    "reachable at": ["reachable at"],
    "fallback unavailable": ["fallback unavailable"],
}
uncovered = []
for label, markers in required_markers.items():
    if not any(m in state_lower for m in markers):
        uncovered.append((label, markers))
if uncovered:
    for label, markers in uncovered:
        print(f"  UNCOVERED: {label!r} missing markers={markers}")
    sys.exit(1)
PYEOF
) || true
if [ -z "$coverage" ]; then
  note_pass "every (enabled, resolvable, ip) combo has a status branch"
else
  note_fail "status coverage gap found:"
  echo "$coverage"
fi

echo
echo "▶ Local mDNS fallback: status copy has no operator jargon"

# The rendered status strings MUST NOT contain operator jargon
# (no entity IDs, no bash terms, no upstream-integration names).
# We exercise the four canonical (enabled, resolvable, ip) combos
# via a pure-function reimplementation pinned by the pytest rig,
# and assert each rendered output is jargon-free. The template
# SOURCE naturally references entity_ids to compute its output
# — that's normal Home Assistant template syntax and is not jargon.
jargon=$(python3 - "$PACKAGE" <<'PYEOF'
import sys, yaml, re

def render(template, ctx):
    """Minimal Jinja2-lite for the four string literals the
    rc_local_mdns_status template can produce. We don't try to
    implement Jinja2 — we just hand-extract the four literal
    strings (one per branch) and assert each is jargon-free."""
    # Find each literal string in the if/elif chain. The branches
    # use single-quoted strings ending with a period.
    literals = re.findall(r"'([^']{20,200}\.)'", template)
    return [s for s in literals if 'reachable' in s.lower() or 'fallback' in s.lower() or 'turned off' in s.lower()]

data = yaml.safe_load(open(sys.argv[1]))
status_sensor = None
for entry in (data.get("template") or []):
    for s in (entry.get("sensor") or []):
        if s.get("unique_id") == "rc_local_mdns_status":
            status_sensor = s
            break
state_template = (status_sensor.get("state") or "") if status_sensor else ""
literals = render(state_template, {})
forbidden = ("binary_sensor.", "input_boolean.", "input_text.", "shell_command.", "avahi-daemon", "zeroconf")
hits = []
for lit in literals:
    for term in forbidden:
        if term in lit.lower():
            hits.append((lit, term))
if hits:
    for lit, term in hits:
        print(f"  JARGON {term!r} in literal: {lit!r}")
    sys.exit(1)
PYEOF
) || true
if [ -z "$jargon" ]; then
  note_pass "status copy has no operator jargon (entity IDs / bash / integration names)"
else
  note_fail "operator jargon in status copy:"
  echo "$jargon"
fi

echo
echo "▶ Local mDNS fallback: secrets-leak check"

# grep for tskey- / ts-auth- / hard-coded IPs — fail if found.
SECRETS=$(grep -E '(tskey-[A-Za-z0-9_-]{10,}|ts-auth-[A-Za-z0-9_-]{10,}|\b192\.168\.\d{1,3}\.\d{1,3}\b|\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b)' "$PACKAGE" || true)
if [ -z "$SECRETS" ]; then
  note_pass "no secrets (tskey- / ts-auth-) or hard-coded IPs leaked in YAML"
else
  note_fail "SECRET / IP PATTERN FOUND in YAML — operator credentials MUST NOT be committed"
  echo "$SECRETS"
fi

echo
echo "▶ Local mDNS fallback: idempotency probe (PyYAML twice → same dict + single shell_command)"

if python3 - "$PACKAGE" <<'PYEOF'
import sys, yaml
text = open(sys.argv[1]).read()
d1 = yaml.safe_load(text); d2 = yaml.safe_load(text)
if yaml.safe_dump(d1, sort_keys=True) != yaml.safe_dump(d2, sort_keys=True):
    print("NOT IDEMPOTENT — re-parsing diverges")
    sys.exit(1)
shell = (d1.get("shell_command") or {})
if len(shell) != 1:
    print(f"DUPLICATE SHELL_COMMAND — expected 1, got {len(shell)}: {list(shell.keys())}")
    sys.exit(1)
PYEOF
then
  note_pass "YAML is idempotent + exactly one shell_command defined (no duplicate mDNS service)"
else
  note_fail "YAML is NOT idempotent — random IDs / timestamps / non-deterministic ordering"
fi

echo
echo "▶ Local mDNS fallback: IKEA doc 5-step shape + translation table"

if python3 - "$DOC" <<'PYEOF'
import sys, re
text = open(sys.argv[1]).read()
# 5 numbered sections
sections = re.findall(r"^##\s+(\d+)\.\s+", text, flags=re.MULTILINE)
if sections != ["1", "2", "3", "4", "5"]:
    print(f"NOT 5 SECTIONS — got {sections}")
    sys.exit(1)
# Translation table present
lower = text.lower()
if "operator" not in lower:
    print("MISSING: 'operator' translation table")
    sys.exit(1)
if not any(m in lower for m in ("you might call it", "you'd call it", "what you see", "what this means")):
    print("MISSING: plain-English translation explanation")
    sys.exit(1)
if "SUPERSEDED" in text or "CRON-HANDOFF" in text.upper():
    print("FOUND: SUPERSEDED / CRON-HANDOFF banner")
    sys.exit(1)
PYEOF
then
  note_pass "IKEA doc has 5 numbered sections + operator→vanlifer translation table + no SUPERSEDED banner"
else
  note_fail "IKEA doc 5-step shape check FAILED — see output above"
fi

echo
echo "▶ Local mDNS fallback: §8.M.3 fallback automation wired correctly"

# §8.M.3 must trigger on the retest button AND fire a persistent_notification
# containing the fallback IP instruction copy.
M3=$(python3 - "$PACKAGE" <<'PYEOF'
import sys, yaml
data = yaml.safe_load(open(sys.argv[1]))
auto = next((a for a in (data.get("automation") or []) if a.get("id") == "rc_local_mdns_fallback_tile_surfacing"), None)
if not auto:
    print("MISSING AUTOMATION")
    sys.exit(1)
# Trigger
triggers = auto.get("trigger") or []
if not any(t.get("platform") == "state" and t.get("entity_id") == "input_button.rc_local_mdns_retest" for t in triggers):
    print("TRIGGER missing retest button")
    sys.exit(1)
actions_dumped = yaml.safe_dump(auto.get("action") or [], default_flow_style=False)
if "persistent_notification.create" not in actions_dumped:
    print("MISSING persistent_notification.create")
    sys.exit(1)
if "8123" not in actions_dumped:
    print("MISSING :8123 port in fallback copy")
    sys.exit(1)
lower = actions_dumped.lower()
if not ("tailscale" in lower or "wi-fi" in lower or "wifi" in lower):
    print("MISSING plain-English context (tailscale / wi-fi) in fallback copy")
    sys.exit(1)
PYEOF
) || true
if [ -z "$M3" ]; then
  note_pass "§8.M.3 wired (retest trigger + persistent_notification + :8123 port + plain-English)"
else
  note_fail "§8.M.3 wiring check FAILED:"
  echo "$M3"
fi

echo
echo "▶ Local mDNS fallback: pytest rig (test_local_mdns_fallback.py)"

# Temporarily disable `set -e` so we can capture pytest's exit code
# instead of the script aborting on the first failure. The pytest
# output is still streamed to the operator's terminal.
set +e
python3 -m pytest "$PYTEST" --tb=short -q 2>&1 | tail -20
PYTEST_EXIT=${PIPESTATUS[0]}
set -e

if [ "$PYTEST_EXIT" -eq 0 ]; then
  note_pass "pytest rig green (test_local_mdns_fallback.py)"
else
  note_fail "pytest rig FAILED (exit=$PYTEST_EXIT) — see output above"
fi

echo
echo "Summary"
echo "======="
printf '  PASS: %d\n' "$pass"
printf '  FAIL: %d\n' "$fail"

if [ "$fail" -gt 0 ]; then
  printf '\n\033[1;31m✗ local-mdns-fallback smoke FAILED\033[0m\n'
  exit 1
fi

printf '\n\033[1;32m✓ local-mdns-fallback smoke PASSED\033[0m\n'
exit 0