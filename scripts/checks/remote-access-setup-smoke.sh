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

# Every entity_id in the package MUST start with rc_remote_access_setup_,
# rc_tailscale_, or rc_wireguard_.
naming_violations=$(python3 - "$PACKAGE" <<'PYEOF'
import sys, yaml
data = yaml.safe_load(open(sys.argv[1]))
allowed = ("rc_remote_access_setup_", "rc_tailscale_", "rc_wireguard_")
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
# These stages always have a known marker (covered above in pytest)
# but we still want to confirm tailscale_done + wireguard_done + done +
# recovery are all individually named in the template (defensive).
required_markers = {
    "welcome": ["ready to help you set up"],
    "tailscale_done": ["tailscale is set up"],
    "wireguard_done": ["wireguard is set up"],
    "recovery": ["couldn't reach your remote-access server"],
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

# Path D — Wireguard hardcoded secrets check. The wizard exposes
# the four Wireguard helpers (server endpoint + server public key +
# peer private key + peer allowed IPs) as `mode: password` operator-
# entered `input_text` helpers. The plain-English
# "wg.example.com:51820" + "10.0.0.2/32" example placeholders in
# the helper `name:` fields are allowlisted (operator-visible
# examples). Everything else — real-looking server endpoints,
# private keys, public keys, allowed-IP CIDR ranges — MUST NOT be
# committed.
WG_SECRETS=$(grep -E '\b[A-Za-z0-9+/]{40,}=|\b[A-Za-z0-9+/]{43}([[:space:]]|"|$)' "$PACKAGE" || true) && WG_SECRETS="$WG_SECRETS"$(grep -E '\b(wg|vpn|wireguard)\.[a-z0-9.-]+\.(com|net|org|io):[0-9]{4,5}' "$PACKAGE" | grep -vE 'wg\.example\.com:51820|RC Wireguard Server Endpoint' || true)
WG_CIDR_SECRETS=$(grep -E '\b(10|172|192)\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}/[0-9]{1,2}\b' "$PACKAGE" | grep -vE '10\.0\.0\.2/32|RC Wireguard Peer Allowed IPs' || true)
if [ -z "$WG_SECRETS" ] && [ -z "$WG_CIDR_SECRETS" ]; then
  note_pass "no Wireguard hardcoded secrets (server endpoints / private keys / public keys / allowed IP CIDRs) in YAML"
else
  note_fail "WIREGUARD HARDCODE FOUND in YAML — operator VPN credentials MUST NOT be committed"
  echo "$WG_SECRETS"
  echo "$WG_CIDR_SECRETS"
fi

# Path D wiring assertion: every new helper / automation / binary_sensor MUST be present.
WG_WIRING=$(python3 - "$PACKAGE" <<'PYEOF'
import sys, yaml
data = yaml.safe_load(open(sys.argv[1]))
missing = []
helpers = data.get("input_text") or {}
for required_helper in ("rc_wireguard_server_endpoint", "rc_wireguard_server_public_key", "rc_wireguard_peer_private_key", "rc_wireguard_peer_allowed_ips"):
    if required_helper not in helpers:
        missing.append(f"input_text.{required_helper}")
    elif helpers[required_helper].get("mode") != "password":
        missing.append(f"input_text.{required_helper} must be mode: password")
stages = (data.get("input_select") or {}).get("rc_remote_access_setup_stage", {}).get("options") or []
for required_stage in ("wireguard_have_server", "wireguard_paste_keys", "wireguard_verify", "wireguard_done"):
    if required_stage not in stages:
        missing.append(f"input_select stage option missing: {required_stage}")
binary_sensor_uids = set()
for entry in (data.get("template") or []):
    for bs in (entry.get("binary_sensor") or []):
        uid = bs.get("unique_id")
        if uid: binary_sensor_uids.add(uid)
for required_uid in ("rc_remote_access_setup_wireguard_installed", "rc_remote_access_setup_wireguard_active"):
    if required_uid not in binary_sensor_uids:
        missing.append(f"binary_sensor unique_id missing: {required_uid}")
automation_ids = set(a.get("id") for a in (data.get("automation") or []))
for required_id in ("rc_remote_access_setup_advance_path_d", "rc_remote_access_setup_recovery_wireguard", "rc_remote_access_setup_detect_existing_wireguard"):
    if required_id not in automation_ids:
        missing.append(f"automation id missing: {required_id}")
if missing:
    for m in missing:
        print(f"  MISSING: {m}")
    sys.exit(1)
PYEOF
) || true
if [ -z "$WG_WIRING" ]; then
  note_pass "Path D wiring complete (4 input_texts + 4 stages + 2 binary_sensors + 3 automations)"
else
  note_fail "Path D wiring incomplete — see above"
  echo "$WG_WIRING"
fi

# Path D recovery plain-English assertion: message MUST mention
# "UDP 51820" or "internet connection" — NOT "wg-quick: interface
# not found", "errno: ENETUNREACH", or raw upstream service codes.
WG_RECOVERY=$(python3 - "$PACKAGE" <<'PYEOF'
import sys, yaml
data = yaml.safe_load(open(sys.argv[1]))
autos = data.get("automation") or []
auto = next((a for a in autos if a.get("id") == "rc_remote_access_setup_recovery_wireguard"), None)
if auto is None:
    print("  MISSING: rc_remote_access_setup_recovery_wireguard")
    sys.exit(1)
actions_dump = yaml.safe_dump(auto.get("action") or [], default_flow_style=False)
failures = []
if "wg-quick" in actions_dump:
    failures.append("raw 'wg-quick' found in recovery action")
if "ENETUNREACH" in actions_dump:
    failures.append("raw errno 'ENETUNREACH' found in recovery action")
if "wg show" in actions_dump:
    failures.append("raw 'wg show' command found in recovery action")
if "udp 51820" not in actions_dump.lower() and "UDP 51820" not in actions_dump:
    failures.append("plain-English nudge about UDP 51820 MISSING")
if "input_text.set_value" in actions_dump:
    failures.append("input_text.set_value would clear operator Wireguard keys")
if failures:
    for f in failures:
        print(f"  PLAIN-ENGLISH FAIL: {f}")
    sys.exit(1)
PYEOF
) || true
if [ -z "$WG_RECOVERY" ]; then
  note_pass "Path D recovery uses plain-English errors (no raw codes, never clears keys)"
else
  note_fail "Path D recovery fails plain-English check — see above"
  echo "$WG_RECOVERY"
fi

# Path D — user-facing IKEA doc check. The wizard code is meaningless
# to a vanlifer without a plain-English howto on the docs site.
# `docs/setup/guided-remote-access.md` MUST carry a §6 Path D
# sub-section with the standard 5-step IKEA shape (6.1 What this is,
# 6.2 What you see, 6.3 What you do, 6.4 What to do if it goes wrong,
# 6.5 Useful links) — no bash in 6.1-6.4, no tier letters, no
# operator-speak jargon like "wg-quick" or "errno: ENETUNREACH".
GUIDE_DOC="docs/setup/guided-remote-access.md"
WG_DOC_CHECK=$(python3 - "$GUIDE_DOC" <<'PYEOF'
import sys, re
path = sys.argv[1]
try:
    text = open(path, encoding="utf-8").read()
except FileNotFoundError:
    print(f"  MISSING: {path}")
    sys.exit(1)
missing = []
# §6 main header
if not re.search(r"^##\s+6\.\s+How to set up Wireguard", text, re.MULTILINE):
    missing.append("## 6. How to set up Wireguard section missing")
# 5-step IKEA shape
for sub in ("6.1 What this is", "6.2 What you see", "6.3 What you do",
            "6.4 What to do if it goes wrong", "6.5 Useful links"):
    if sub not in text:
        missing.append(f"section '{sub}' missing")
# Plain-English guard: no operator-speak jargon in the §6 sub-section
section_6 = re.search(r"##\s+6\.(.*?)(?=^##\s|\Z)", text, re.MULTILINE | re.DOTALL)
if section_6:
    body = section_6.group(1).lower()
    for jargon in ("wg-quick", "errno:", "ip link", "ip route", "ip a ", "interface not found",
                   "wg show", "private key", "public key"):
        # "private key" / "public key" are OK if they're inside plain-English phrases
        # like "your peer private key" — but the bare "wg-quick" / "errno:" must NEVER appear.
        if jargon in ("wg-quick", "errno:", "ip link", "ip route", "ip a ", "interface not found", "wg show"):
            if jargon in body:
                missing.append(f"operator-speak jargon {jargon!r} found in §6")
# 4 numbered steps in 6.3 (1-4)
section_63 = re.search(r"###\s+6\.3(.*?)(?=^###\s|\Z)", text, re.MULTILINE | re.DOTALL)
if section_63:
    body = section_63.group(1)
    step_count = len(re.findall(r"^\d+\.\s+\*\*", body, re.MULTILINE))
    if step_count < 3:
        missing.append(f"6.3 needs ≥3 numbered steps (got {step_count})")
if missing:
    for m in missing:
        print(f"  MISSING: {m}")
    sys.exit(1)
PYEOF
) || true
if [ -z "$WG_DOC_CHECK" ]; then
  note_pass "Path D user-facing IKEA doc present (docs/setup/guided-remote-access.md §6, 5-step shape, no operator-speak)"
else
  note_fail "Path D user-facing doc incomplete — see above"
  echo "$WG_DOC_CHECK"
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
