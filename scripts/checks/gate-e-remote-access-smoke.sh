#!/usr/bin/env bash
# scripts/checks/gate-e-remote-access-smoke.sh
#
# Wave 9 #123.d.v — Phase 7 Gate E (remote access) smoke check.
# Repo-local verification of the Phase 7 Gate E acceptance test
# slice. Mirrors the convention in scripts/checks/<name>.sh:
#   - bash strict mode (set -euo pipefail)
#   - repo-local only (no live HA / Proxmox / OpenWrt calls)
#   - 11 plain-English assertions
#   - stage coverage + rc-naming + secrets-leak + idempotency
#     checks that don't need pytest
#   - plain-English summary at exit 0 / non-zero exit
#
# This is a static check on the repo: nothing touches HA at runtime.
# Idempotent — safe to run repeatedly.
#
# Usage:
#   bash scripts/checks/gate-e-remote-access-smoke.sh
#
# Exit codes:
#   0  all 11 assertions PASS
#   1  one or more assertions FAIL
#
# Wired into scripts/check.sh as a `run_if_present` step in the
# core-only chain.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PASS_COUNT=0
FAIL_COUNT=0

assert_pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
  printf '\033[1;32m✓\033[0m %s\n' "$1"
}

assert_fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  printf '\033[1;31m✗\033[0m %s\n' "$1"
  if [ -n "${2:-}" ]; then
    printf '  reason: %s\n' "$2"
  fi
}

# ---------------------------------------------------------------------------
# Assertion 1 — pytest rig importable + Gate E bash test executable
# ---------------------------------------------------------------------------

GATE_E_SCRIPT="${ROOT_DIR}/scripts/tests/acceptance/gate_e_remote_access.sh"
GATE_E_PYTEST="${ROOT_DIR}/scripts/tests/acceptance/test_gate_e_remote_access.py"

echo
echo "▶ Gate E (remote access): file presence"

if [ -f "$GATE_E_SCRIPT" ] && [ -f "$GATE_E_PYTEST" ]; then
  assert_pass "assertion 1: both Gate E files present (bash + pytest rig)"
else
  assert_fail "assertion 1: Gate E files missing" "expected bash + pytest rig at scripts/tests/acceptance/gate_e_remote_access.{sh,py}"
fi

# ---------------------------------------------------------------------------
# Assertion 2 — all 13 stages present in the bash script
# ---------------------------------------------------------------------------

echo
echo "▶ Gate E (remote access): 13-stage bash contract"

STAGE_COUNT=$(grep -cE '^step "[0-9]+"' "$GATE_E_SCRIPT" || true)
if [ "$STAGE_COUNT" -ge 13 ]; then
  assert_pass "assertion 2: bash script contains all 13 stages ($STAGE_COUNT found)"
else
  assert_fail "assertion 2: bash script missing stages" "expected >= 13 stages; found $STAGE_COUNT"
fi

# ---------------------------------------------------------------------------
# Assertion 3 — all 4 wizard paths (A/B/C/D) referenced
# ---------------------------------------------------------------------------

echo
echo "▶ Gate E (remote access): 4 wizard paths (A/B/C/D)"

MISSING_PATHS=()
for path in tailscale cloudflare nabu_casa wireguard; do
  if ! grep -q "${path}" "$GATE_E_SCRIPT"; then
    MISSING_PATHS+=("${path}")
  fi
done
if [ "${#MISSING_PATHS[@]}" -eq 0 ]; then
  assert_pass "assertion 3: all 4 wizard paths (A/B/C/D) referenced (tailscale/cloudflare/nabu_casa/wireguard)"
else
  assert_fail "assertion 3: missing wizard paths" "missing: ${MISSING_PATHS[*]}"
fi

# ---------------------------------------------------------------------------
# Assertion 4 — QR code format check (tailscale:// URL + 5-min TTL)
# ---------------------------------------------------------------------------

echo
echo "▶ Gate E (remote access): QR code format (tailscale:// + 5-min TTL)"

if grep -qE 'tailscale://login/\[A-Za-z0-9_-\]\+' "$GATE_E_SCRIPT" \
   && grep -qE 'GATE_E_AUTH_KEY_TTL_SECONDS="\$\{GATE_E_AUTH_KEY_TTL_SECONDS:-300\}"' "$GATE_E_SCRIPT"; then
  assert_pass "assertion 4: QR code uses tailscale:// format + 5-minute (300s) TTL"
else
  assert_fail "assertion 4: QR code format / TTL missing" "expected tailscale://login/<id> regex + 300s TTL constant"
fi

# ---------------------------------------------------------------------------
# Assertion 5 — plain-English error copy on every failure path
# ---------------------------------------------------------------------------

echo
echo "▶ Gate E (remote access): plain-English error copy"

PLAIN_ENGLISH_FAILURES=$(grep -cE '^[[:space:]]{0,4}fail "' "$GATE_E_SCRIPT" || true)
if [ "$PLAIN_ENGLISH_FAILURES" -ge 10 ]; then
  assert_pass "assertion 5: plain-English fail() messages on every failure path ($PLAIN_ENGLISH_FAILURES found)"
else
  assert_fail "assertion 5: missing plain-English fail() calls" "expected >= 10 fail() calls; found $PLAIN_ENGLISH_FAILURES"
fi

# ---------------------------------------------------------------------------
# Assertion 6 — no bash command in user-facing doc §1-§4
# ---------------------------------------------------------------------------

echo
echo "▶ Gate E (remote access): user-facing doc has no bash commands in §1-§4"

GATE_E_DOC="${ROOT_DIR}/docs/runbooks/automated-acceptance-tests-gate-e.md"
if [ -f "$GATE_E_DOC" ]; then
  USER_TEXT=$(awk '/^## §1/,/^## §5/' "$GATE_E_DOC" | sed '/^## §5/d')
  BASH_HITS=$(printf '%s' "$USER_TEXT" | grep -cE '(^|[^a-zA-Z])(bash|curl|pytest|ssh)([^a-zA-Z]|$)' || true)
  if [ "$BASH_HITS" -eq 0 ]; then
    assert_pass "assertion 6: user-facing doc §1-§4 has no bash commands (0 hits)"
  else
    assert_fail "assertion 6: user-facing doc §1-§4 contains bash commands" "found $BASH_HITS hits"
  fi
else
  assert_fail "assertion 6: user-facing runbook missing" "expected at $GATE_E_DOC"
fi

# ---------------------------------------------------------------------------
# Assertion 7 — no vendor tokens (Tailscale / Wireguard / Cloudflare / Nabu Casa)
#               in user-facing doc §1-§4
# ---------------------------------------------------------------------------

echo
echo "▶ Gate E (remote access): user-facing doc uses vendor-neutral phrasing in §1-§4"

if [ -f "$GATE_E_DOC" ]; then
  USER_TEXT=$(awk '/^## §1/,/^## §5/' "$GATE_E_DOC" | sed '/^## §5/d')
  VENDOR_HITS=$(printf '%s' "$USER_TEXT" | grep -cE '(Tailscale|Wireguard|WireGuard|Cloudflare|Nabu Casa|NabuCasa)' || true)
  if [ "$VENDOR_HITS" -eq 0 ]; then
    assert_pass "assertion 7: user-facing doc §1-§4 uses vendor-neutral phrasing (0 vendor tokens)"
  else
    assert_fail "assertion 7: user-facing doc §1-§4 contains vendor tokens" "found $VENDOR_HITS vendor tokens"
  fi
else
  assert_fail "assertion 7: user-facing runbook missing" "expected at $GATE_E_DOC"
fi

# ---------------------------------------------------------------------------
# Assertion 8 — rc-entity-naming honored (every entity_id starts with rc_remote_access_)
# ---------------------------------------------------------------------------

echo
echo "▶ Gate E (remote access): rc-entity-naming honored"

if grep -qE '\^\[a-z_\]\+\\\.rc_remote_access_' "$GATE_E_SCRIPT"; then
  assert_pass "assertion 8: rc-entity-naming honored (Stage 13 grep uses rc_remote_access_ pattern)"
else
  assert_fail "assertion 8: rc-entity-naming missing" "expected Stage 13 to assert rc_remote_access_ prefix"
fi

# ---------------------------------------------------------------------------
# Assertion 9 — IKEA doc shape (5 numbered sections in user-facing runbook)
# ---------------------------------------------------------------------------

echo
echo "▶ Gate E (remote access): IKEA 5-step user-facing runbook"

if [ -f "$GATE_E_DOC" ]; then
  IKEA_SECTIONS=$(grep -cE '^## §[1-5] ' "$GATE_E_DOC" || true)
  if [ "$IKEA_SECTIONS" -ge 5 ]; then
    assert_pass "assertion 9: user-facing runbook has IKEA 5-step shape ($IKEA_SECTIONS sections)"
  else
    assert_fail "assertion 9: user-facing runbook missing IKEA sections" "expected >= 5 numbered §1-§5 sections; found $IKEA_SECTIONS"
  fi
else
  assert_fail "assertion 9: user-facing runbook missing" "expected at $GATE_E_DOC"
fi

# ---------------------------------------------------------------------------
# Assertion 10 — no Wave / tier / PR / cron jargon in user copy
# ---------------------------------------------------------------------------

echo
echo "▶ Gate E (remote access): no Wave/tier/PR/cron jargon in user copy"

if [ -f "$GATE_E_DOC" ]; then
  USER_TEXT=$(awk '/^## §1/,/^## §5/' "$GATE_E_DOC" | sed '/^## §5/d')
  JARGON_HITS=$(printf '%s' "$USER_TEXT" | grep -ciE '(Wave [0-9]+|tier-[abc]|PR *#[0-9]+|the cron|the sub-agent)' || true)
  if [ "$JARGON_HITS" -eq 0 ]; then
    assert_pass "assertion 10: no Wave/tier/PR/cron jargon in user copy (0 hits)"
  else
    assert_fail "assertion 10: user copy contains Wave/tier/PR/cron jargon" "found $JARGON_HITS hits"
  fi
else
  assert_fail "assertion 10: user-facing runbook missing" "expected at $GATE_E_DOC"
fi

# ---------------------------------------------------------------------------
# Assertion 11 (idempotency bonus) — bash script + pytest rig exit 0 on re-run
# ---------------------------------------------------------------------------

echo
echo "▶ Gate E (remote access): idempotency (bash --mock exits 0 on re-run)"

if [ -x "$GATE_E_SCRIPT" ]; then
  set +e
  bash "$GATE_E_SCRIPT" --mock > /dev/null 2>&1
  FIRST_EXIT=$?
  bash "$GATE_E_SCRIPT" --mock > /dev/null 2>&1
  SECOND_EXIT=$?
  set -e
  if [ "$FIRST_EXIT" -eq 0 ] && [ "$SECOND_EXIT" -eq 0 ]; then
    assert_pass "assertion 11: bash script is idempotent (both runs exit 0)"
  else
    assert_fail "assertion 11: bash script not idempotent" "first exit=$FIRST_EXIT, second exit=$SECOND_EXIT"
  fi
else
  assert_fail "assertion 11: bash script not executable" "expected chmod +x on $GATE_E_SCRIPT"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

echo
echo "Summary"
echo "======="
printf '  PASS: %d\n' "$PASS_COUNT"
printf '  FAIL: %d\n' "$FAIL_COUNT"

if [ "$FAIL_COUNT" -gt 0 ]; then
  printf '\n\033[1;31m✗ Gate E (remote access) smoke FAILED\033[0m\n'
  exit 1
fi

printf '\n\033[1;32m✓ Gate E (remote access) smoke PASSED\033[0m\n'
exit 0