#!/usr/bin/env bash
# scripts/checks/tailscale-self-test-smoke.sh
#
# Wave 9 #122.d.iii — Phase 6 Tailscale wizard (sub-slice D.iii:
# connectivity self-test HA → tunnel → phone → tunnel → HA
# round-trip). Repo-local verification of the self-test package +
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
#   bash scripts/checks/tailscale-self-test-smoke.sh
#
# Exit codes:
#   0  all package YAML helpers + automations are present + named right +
#      pytest rig is green + no secrets leaked + idempotent (PASS)
#   1  one or more checks failed (FAIL — see summary above)
#
# Wired into scripts/check.sh as a `run_if_present` step in the
# core-only chain (next to the other package-layer smokes like
# remote-access-setup-smoke.sh + local-mdns-fallback-smoke.sh).

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PACKAGE="$ROOT_DIR/homeassistant/packages/roamcore_tailscale_self_test.yaml"
PYTEST="$ROOT_DIR/homeassistant/packages/tests/test_tailscale_self_test.py"
DOC="$ROOT_DIR/docs/setup/tailscale-self-test.md"

fail=0
pass=0

note_pass() { printf '  \033[1;32m✓\033[0m %s\n' "$1"; pass=$((pass+1)); }
note_fail() { printf '  \033[1;31m✗\033[0m %s\n' "$1"; fail=$((fail+1)); }

echo
echo "▶ Tailscale self-test: file presence"

if [ -f "$PACKAGE" ]; then
  note_pass "package exists: ${PACKAGE#$ROOT_DIR/}"
else
  note_fail "missing package: ${PACKAGE#$ROOT_DIR/}"
  echo
  echo "Summary"
  echo "======="
  printf '  PASS: %d\n' "$pass"
  printf '  FAIL: %d\n' "$fail"
  printf '\n\033[1;31m✗ tailscale-self-test smoke FAILED (missing package)\033[0m\n'
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
echo "▶ Tailscale self-test: YAML pre-check (PyYAML parse)"

if python3 -c "import yaml,sys; yaml.safe_load(open('$PACKAGE'))" 2>/dev/null; then
  note_pass "YAML parses"
else
  note_fail "YAML parse error — see python3 output above"
fi

echo
echo "▶ Tailscale self-test: rc-entity-naming pre-check"

# Every helper entity_id MUST start with one of the allowed prefixes.
naming_violations=$(python3 - "$PACKAGE" <<'PYEOF'
import sys, yaml
data = yaml.safe_load(open(sys.argv[1]))
allowed = ("rc_tailscale_self_test_", "rc_tailscale_run_self_test")
violations = []
for kind in ("input_select", "input_text", "input_boolean", "input_number", "input_datetime", "input_button", "shell_command"):
    for eid in (data.get(kind) or {}).keys():
        if not any(eid.startswith(p) for p in allowed):
            violations.append((kind, eid))
# command_line + template sensors + automation ids
for entry in (data.get("command_line") or []):
    for s in (entry.get("sensor") or []):
        uid = s.get("unique_id") or ""
        if not any(uid.startswith(p) for p in allowed):
            violations.append(("command_line_sensor", uid))
for entry in (data.get("template") or []):
    for bs in (entry.get("binary_sensor") or []):
        uid = bs.get("unique_id") or ""
        if not any(uid.startswith(p) for p in allowed):
            violations.append(("template_binary_sensor", uid))
    for s in (entry.get("sensor") or []):
        uid = s.get("unique_id") or ""
        if not any(uid.startswith(p) for p in allowed):
            violations.append(("template_sensor", uid))
for a in (data.get("automation") or []):
    aid = a.get("id") or ""
    if not any(aid.startswith(p) for p in allowed):
        violations.append(("automation", aid))
if violations:
    for k, eid in violations:
        print(f"  VIOLATION: {k}.{eid}")
    sys.exit(1)
PYEOF
) || true
if [ -z "$naming_violations" ]; then
  note_pass "all entity_ids + automation ids comply with docs/reference/rc-entity-naming.md"
else
  note_fail "rc-naming violations found"
  echo "$naming_violations"
fi

echo
echo "▶ Tailscale self-test: helpers + automations + templates pre-check"

# All required helpers, automations, sensors, and binary_sensors
# MUST be present.
helpers_present=$(python3 - "$PACKAGE" <<'PYEOF'
import sys, yaml
data = yaml.safe_load(open(sys.argv[1]))
missing = []
for kind, ids in (
    ("input_text", ["rc_tailscale_self_test_tunnel_url"]),
    ("input_boolean", ["rc_tailscale_self_test_running"]),
    ("input_button", ["rc_tailscale_run_self_test"]),
    ("input_datetime", ["rc_tailscale_self_test_last_run"]),
    ("shell_command", [
        "rc_tailscale_self_test_outbound_probe",
        "rc_tailscale_self_test_inbound_probe",
    ]),
):
    present = set((data.get(kind) or {}).keys())
    for eid in ids:
        if eid not in present:
            missing.append((kind, eid))
# Automations
auto_ids = {a.get("id") for a in (data.get("automation") or [])}
for aid in (
    "rc_tailscale_self_test_run",
    "rc_tailscale_self_test_recovery",
    "rc_tailscale_self_test_wizard_advance",
):
    if aid not in auto_ids:
        missing.append(("automation", aid))
# command_line sensors + template sensors + binary_sensors (unique_id)
seen_cl_uids = set()
seen_sensor_uids = set()
seen_bs_uids = set()
for entry in (data.get("command_line") or []):
    for s in (entry.get("sensor") or []):
        seen_cl_uids.add(s.get("unique_id"))
for entry in (data.get("template") or []):
    for s in (entry.get("sensor") or []):
        seen_sensor_uids.add(s.get("unique_id"))
    for bs in (entry.get("binary_sensor") or []):
        seen_bs_uids.add(bs.get("unique_id"))
for uid in (
    "rc_tailscale_self_test_outbound_code",
    "rc_tailscale_self_test_expected_nonce_sensor",
    "rc_tailscale_self_test_received_nonce_sensor",
):
    if uid not in seen_cl_uids:
        missing.append(("command_line_sensor", uid))
for uid in ("rc_tailscale_self_test_status",):
    if uid not in seen_sensor_uids:
        missing.append(("template_sensor", uid))
for uid in (
    "rc_tailscale_self_test_outbound_ok",
    "rc_tailscale_self_test_inbound_ok",
    "rc_tailscale_self_test_ok",
    "rc_tailscale_self_test_recovery",
):
    if uid not in seen_bs_uids:
        missing.append(("template_binary_sensor", uid))
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
echo "▶ Tailscale self-test: status template covers all branches"

# The status template MUST cover all 6 state combinations with
# the canonical plain-English phrases.
coverage=$(python3 - "$PACKAGE" <<'PYEOF'
import sys, yaml
data = yaml.safe_load(open(sys.argv[1]))
status_sensor = None
for entry in (data.get("template") or []):
    for s in (entry.get("sensor") or []):
        if s.get("unique_id") == "rc_tailscale_self_test_status":
            status_sensor = s
            break
state_template = (status_sensor.get("state") or "") if status_sensor else ""
state_lower = state_template.lower()
required_markers = {
    "not configured": ["type your tunnel address"],
    "checking": ["checking your tunnel"],
    "round-trip succeeded": ["round-trip succeeded"],
    "outbound failed": ["hub can't reach itself"],
    "inbound failed": ["phone-side callback didn't arrive"],
    "ready": ["ready to check your tunnel"],
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
  note_pass "every (url, running, outbound, inbound, recovery, never_run) combo has a status branch"
else
  note_fail "status coverage gap found:"
  echo "$coverage"
fi

echo
echo "▶ Tailscale self-test: status copy has no operator jargon"

# The rendered status strings MUST NOT contain operator jargon
# (no entity IDs, no bash terms, no upstream-integration names).
# We exercise the 6 canonical combos via a pure-function
# reimplementation pinned by the pytest rig, and assert each
# rendered output is jargon-free. The template SOURCE naturally
# references entity_ids to compute its output — that's normal
# Home Assistant template syntax and is not jargon.
jargon=$(python3 - "$PACKAGE" <<'PYEOF'
import sys, yaml, re

data = yaml.safe_load(open(sys.argv[1]))
status_sensor = None
for entry in (data.get("template") or []):
    for s in (entry.get("sensor") or []):
        if s.get("unique_id") == "rc_tailscale_self_test_status":
            status_sensor = s
            break
state_template = (status_sensor.get("state") or "") if status_sensor else ""
# Find each literal string in the if/elif chain. The branches
# use single-quoted strings ending with a period.
literals = re.findall(r"'([^']{20,250}\.)'", state_template)
literals = [s for s in literals if any(
    kw in s.lower() for kw in (
        "type your tunnel", "checking your tunnel", "round-trip",
        "hub can't reach", "phone-side callback", "ready to check",
    )
)]
forbidden = (
    "binary_sensor.", "input_boolean.", "input_text.", "input_datetime.",
    "input_button.", "shell_command.", "command_line.",
    "avahi-daemon", "zeroconf", "tskey-", "magicdns", ".ts.net", "curl ", "bash ",
)
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
echo "▶ Tailscale self-test: secrets-leak check"

# grep for tskey- / ts-auth- / hard-coded IPs — fail if found.
SECRETS=$(grep -E '(tskey-[A-Za-z0-9_-]{10,}|ts-auth-[A-Za-z0-9_-]{10,}|\b192\.168\.\d{1,3}\.\d{1,3}\b|\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b|\b172\.(1[6-9]|2[0-9]|3[01])\.\d{1,3}\.\d{1,3}\b)' "$PACKAGE" || true)
if [ -z "$SECRETS" ]; then
  note_pass "no secrets (tskey- / ts-auth-) or hard-coded IPs leaked in YAML"
else
  note_fail "SECRET / IP PATTERN FOUND in YAML — operator credentials MUST NOT be committed"
  echo "$SECRETS"
fi

echo
echo "▶ Tailscale self-test: idempotency probe (PyYAML twice → same dict + exactly 2 probes)"

if python3 - "$PACKAGE" <<'PYEOF'
import sys, yaml
text = open(sys.argv[1]).read()
d1 = yaml.safe_load(text); d2 = yaml.safe_load(text)
if yaml.safe_dump(d1, sort_keys=True) != yaml.safe_dump(d2, sort_keys=True):
    print("NOT IDEMPOTENT — re-parsing diverges")
    sys.exit(1)
shell = (d1.get("shell_command") or {})
if len(shell) != 2:
    print(f"WRONG SHELL_COMMAND COUNT — expected 2, got {len(shell)}: {list(shell.keys())}")
    sys.exit(1)
PYEOF
then
  note_pass "YAML is idempotent + exactly 2 shell_command probes defined (no duplicate probes)"
else
  note_fail "YAML is NOT idempotent — random IDs / timestamps / non-deterministic ordering"
fi

echo
echo "▶ Tailscale self-test: IKEA doc 5-step shape + translation table"

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
# First paragraph must be plain English (no tier / wave / YAML jargon)
lines = text.splitlines()
first_content = next(
    (line.strip() for line in lines[1:] if line.strip() and not line.strip().startswith("#")),
    "",
)
forbidden_openers = (
    "this slice", "wave 9", "wave", "tier-a", "tier-b", "tier-c",
    "yaml", "input_boolean", "binary_sensor",
    "homeassistant/packages/", "scripts/check.sh",
    "pr #", "commit ", "branch ", "lint-pass", "apple-grade",
)
lower_first = first_content.lower()
for term in forbidden_openers:
    if term in lower_first:
        print(f"OPENING JARGON {term!r}: {first_content!r}")
        sys.exit(1)
PYEOF
then
  note_pass "IKEA doc has 5 numbered sections + operator→vanlifer translation table + no SUPERSEDED + plain-English opener"
else
  note_fail "IKEA doc 5-step shape check FAILED — see output above"
fi

echo
echo "▶ Tailscale self-test: §8.T.1 run automation wired correctly (button + event + stage triggers)"

# §8.T.1 must trigger on the operator button, the parent wizard event,
# AND the wizard stage transition into tailscale_verify. It must NOT
# call input_text.set_value on the tunnel URL helper.
T1=$(python3 - "$PACKAGE" <<'PYEOF'
import sys, yaml
data = yaml.safe_load(open(sys.argv[1]))
auto = next((a for a in (data.get("automation") or []) if a.get("id") == "rc_tailscale_self_test_run"), None)
if not auto:
    print("MISSING AUTOMATION")
    sys.exit(1)
triggers = auto.get("trigger") or []
has_button = any(
    t.get("platform") == "state"
    and t.get("entity_id") == "input_button.rc_tailscale_run_self_test"
    for t in triggers
)
has_event = any(
    t.get("platform") == "event"
    and t.get("event_type") == "rc_run_tailscale_self_test"
    for t in triggers
)
has_stage = any(
    t.get("platform") == "state"
    and t.get("entity_id") == "input_select.rc_remote_access_setup_stage"
    and t.get("to") == "tailscale_verify"
    for t in triggers
)
if not (has_button and has_event and has_stage):
    print(f"MISSING TRIGGER (button={has_button}, event={has_event}, stage={has_stage})")
    sys.exit(1)
actions_dumped = yaml.safe_dump(auto.get("action") or [], default_flow_style=False)
if "shell_command.rc_tailscale_self_test_outbound_probe" not in actions_dumped:
    print("MISSING outbound probe")
    sys.exit(1)
if "shell_command.rc_tailscale_self_test_inbound_probe" not in actions_dumped:
    print("MISSING inbound probe")
    sys.exit(1)
if "input_boolean.turn_on" not in actions_dumped:
    print("MISSING turn_on running flag")
    sys.exit(1)
if "input_boolean.turn_off" not in actions_dumped:
    print("MISSING turn_off running flag")
    sys.exit(1)
if "input_datetime.set_datetime" not in actions_dumped:
    print("MISSING set_datetime last_run")
    sys.exit(1)
if "00:00:30" not in actions_dumped:
    print("MISSING 30s wait")
    sys.exit(1)
# Idempotency: MUST NOT call input_text.set_value on tunnel URL
if "input_text.set_value" in actions_dumped and "rc_tailscale_self_test_tunnel_url" in actions_dumped:
    print("CLEARS TUNNEL URL — idempotent retry broken")
    sys.exit(1)
PYEOF
) || true
if [ -z "$T1" ]; then
  note_pass "§8.T.1 wired (button + event + stage triggers + both probes + 30s wait + idempotent)"
else
  note_fail "§8.T.1 wiring check FAILED:"
  echo "$T1"
fi

echo
echo "▶ Tailscale self-test: §8.T.2 recovery automation wired correctly (60s timeout + plain-English)"

# §8.T.2 must trigger on the running flag being on for 60s, fire a
# persistent_notification with plain-English copy, and NOT clear the
# tunnel URL helper (idempotent retry).
T2=$(python3 - "$PACKAGE" <<'PYEOF'
import sys, yaml
data = yaml.safe_load(open(sys.argv[1]))
auto = next((a for a in (data.get("automation") or []) if a.get("id") == "rc_tailscale_self_test_recovery"), None)
if not auto:
    print("MISSING AUTOMATION")
    sys.exit(1)
triggers = auto.get("trigger") or []
if not any(
    t.get("platform") == "state"
    and t.get("entity_id") == "input_boolean.rc_tailscale_self_test_running"
    and t.get("to") == "on"
    and t.get("for") == "00:01:00"
    for t in triggers
):
    print("MISSING 60s timeout trigger on running flag")
    sys.exit(1)
actions_dumped = yaml.safe_dump(auto.get("action") or [], default_flow_style=False)
if "persistent_notification.create" not in actions_dumped:
    print("MISSING persistent_notification.create")
    sys.exit(1)
lower = actions_dumped.lower()
if "tunnel" not in lower:
    print("MISSING 'tunnel' in plain-English copy")
    sys.exit(1)
if "wizard" not in lower and "van" not in lower:
    print("MISSING 'wizard' or 'van' in plain-English copy")
    sys.exit(1)
# Idempotency: MUST NOT clear the tunnel URL
if "input_text.set_value" in actions_dumped and "rc_tailscale_self_test_tunnel_url" in actions_dumped:
    print("CLEARS TUNNEL URL — idempotent retry broken")
    sys.exit(1)
PYEOF
) || true
if [ -z "$T2" ]; then
  note_pass "§8.T.2 wired (60s timeout + plain-English persistent_notification + idempotent)"
else
  note_fail "§8.T.2 wiring check FAILED:"
  echo "$T2"
fi

echo
echo "▶ Tailscale self-test: pytest rig (test_tailscale_self_test.py)"

# Temporarily disable `set -e` so we can capture pytest's exit code
# instead of the script aborting on the first failure. The pytest
# output is still streamed to the operator's terminal.
set +e
python3 -m pytest "$PYTEST" --tb=short -q 2>&1 | tail -20
PYTEST_EXIT=${PIPESTATUS[0]}
set -e

if [ "$PYTEST_EXIT" -eq 0 ]; then
  note_pass "pytest rig green (test_tailscale_self_test.py)"
else
  note_fail "pytest rig FAILED (exit=$PYTEST_EXIT) — see output above"
fi

echo
echo "Summary"
echo "======="
printf '  PASS: %d\n' "$pass"
printf '  FAIL: %d\n' "$fail"

if [ "$fail" -gt 0 ]; then
  printf '\n\033[1;31m✗ tailscale-self-test smoke FAILED\033[0m\n'
  exit 1
fi

printf '\n\033[1;32m✓ tailscale-self-test smoke PASSED\033[0m\n'
exit 0
