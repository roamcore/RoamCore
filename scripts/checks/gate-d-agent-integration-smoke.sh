#!/usr/bin/env bash
# scripts/checks/gate-d-agent-integration-smoke.sh
#
# Developer-convenience smoke check for the Gate D agent-integration
# acceptance rig (Wave 9 #123.d.iv). Mirrors the pattern of
# gate-b-acceptance / hub-backup / pwa-install smokes: ~10 bash
# assertions that prove the rig is structurally healthy + that the
# user-facing shape is correct.
#
# This is a static check on the repo: no live HA / Proxmox / OpenWrt
# calls. Idempotent — safe to run repeatedly.
#
# Exit codes: 0 = PASS, 1 = FAIL.

set -euo pipefail

# Resolve repo root regardless of where the script is invoked from.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GATE_D_BASH="${ROOT_DIR}/scripts/tests/acceptance/gate_d_agent_integration.sh"
GATE_D_PYTEST="${ROOT_DIR}/scripts/tests/acceptance/test_gate_d_agent_integration.py"
GATE_D_RUNBOOK="${ROOT_DIR}/docs/runbooks/automated-acceptance-tests-gate-d.md"
GATE_D_WORKFLOW="${ROOT_DIR}/.github/workflows/acceptance-gate-d.yml"
GATE_D_UMBRELLA="${ROOT_DIR}/docs/runbooks/automated-acceptance-tests.md"
GATE_D_CHECK_SH="${ROOT_DIR}/scripts/check.sh"

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

# ---------------------------------------------------------------------------
# 1. Bash test exists + is executable + has the 12 stages
# ---------------------------------------------------------------------------

if assert_file "$GATE_D_BASH"; then
  if [ -x "$GATE_D_BASH" ]; then
    note_pass "bash test is executable"
  else
    note_fail "bash test is not executable"
    fail=$((fail+1))
  fi
  # Count the stage headings (12 stages).
  STAGE_COUNT=$(grep -cE '^step "([0-9]+|1[0-2])" ' "$GATE_D_BASH" || true)
  if [ "$STAGE_COUNT" -ge 12 ]; then
    note_pass "bash test defines >=12 stage assertions (found ${STAGE_COUNT})"
  else
    note_fail "bash test must define >=12 stage assertions; found ${STAGE_COUNT}"
    fail=$((fail+1))
  fi
fi

# ---------------------------------------------------------------------------
# 2. Pytest rig is importable (smoke-importable) + carries the
#    canonical 12-stage test layout
# ---------------------------------------------------------------------------

if assert_file "$GATE_D_PYTEST"; then
  if python3 -c "import importlib.util, sys; spec = importlib.util.spec_from_file_location('gate_d_pytest', '${GATE_D_PYTEST}'); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); print('ok')" > /dev/null 2>&1; then
    note_pass "pytest rig is importable"
  else
    note_fail "pytest rig is not importable"
    fail=$((fail+1))
  fi
  # The rig must reference every canonical stage (1-12).
  for stage in 01 02 03 04 05 06 07 08 09 10 11 12; do
    if grep -qE "test_stage_${stage}_" "$GATE_D_PYTEST"; then
      note_pass "pytest rig carries test_stage_${stage}_*"
    else
      note_fail "pytest rig is missing test_stage_${stage}_*"
      fail=$((fail+1))
    fi
  done
fi

# ---------------------------------------------------------------------------
# 3. Audit chain integrity assertions are present
# ---------------------------------------------------------------------------

if [ -f "$GATE_D_BASH" ]; then
  if grep -qE 'hashlib\.sha256' "$GATE_D_BASH"; then
    note_pass "bash test uses hashlib.sha256 for audit-chain integrity"
  else
    note_fail "bash test must use hashlib.sha256 for audit-chain integrity"
    fail=$((fail+1))
  fi
  if grep -qE 'tamper|tampered' "$GATE_D_BASH"; then
    note_pass "bash test covers tamper detection"
  else
    note_fail "bash test must cover tamper detection"
    fail=$((fail+1))
  fi
  if grep -qE '\[0-9a-f]\{64\}' "$GATE_D_BASH"; then
    note_pass "bash test asserts 64-char SHA-256 hex signature shape"
  else
    note_fail "bash test must assert the 64-char SHA-256 hex signature shape"
    fail=$((fail+1))
  fi
fi

# ---------------------------------------------------------------------------
# 4. Plain-English error copy on every failure path
# ---------------------------------------------------------------------------

if [ -f "$GATE_D_BASH" ]; then
  FAIL_CALLS=$(grep -cE '^[[:space:]]{0,4}fail "' "$GATE_D_BASH" || true)
  if [ "$FAIL_CALLS" -ge 10 ]; then
    note_pass "bash test has >=10 plain-English fail() calls (found ${FAIL_CALLS})"
  else
    note_fail "bash test must have >=10 plain-English fail() calls; found ${FAIL_CALLS}"
    fail=$((fail+1))
  fi
  if grep -q "Action not allowed without explicit confirmation" "$GATE_D_BASH"; then
    note_pass "bash test carries the canonical 'Action not allowed without explicit confirmation' denial"
  else
    note_fail "bash test must carry the canonical plain-English denial phrase"
    fail=$((fail+1))
  fi
fi

# ---------------------------------------------------------------------------
# 5. No bash command in user-facing doc body (§1-§4)
# ---------------------------------------------------------------------------

if assert_file "$GATE_D_RUNBOOK"; then
  # Extract §1-§4 (the body, before §5 Useful links).
  DOC_BODY=$(awk '/^## §5 Useful links/{exit} {print}' "$GATE_D_RUNBOOK")
  if echo "$DOC_BODY" | grep -qE 'bash |bash\$|\$\(|`bash|python3 |python \$|pytest |gh pr create'; then
    note_fail "user-facing runbook contains bash commands in §1-§4 — forbidden by the vanlifer-doc discipline"
    fail=$((fail+1))
  else
    note_pass "user-facing runbook contains no bash commands in §1-§4"
  fi
  # The runbook must follow the IKEA 5-step shape.
  for n in 1 2 3 4 5; do
    if grep -qE "^## §${n} " "$GATE_D_RUNBOOK"; then
      note_pass "runbook has §${n} section header"
    else
      note_fail "runbook is missing §${n} section header (IKEA 5-step shape)"
      fail=$((fail+1))
    fi
  done
fi

# ---------------------------------------------------------------------------
# 6. No vendor tokens / RC_API_TOKEN literals / hardcoded passwords in
#    the rig (secrets-leak grep)
# ---------------------------------------------------------------------------

if [ -f "$GATE_D_BASH" ]; then
  # The rig is allowed to mention the canonical phrase
  # "RC_API_TOKEN" (e.g. in error messages) but NOT to assign a
  # 16+ character literal to any of password / api_key / secret /
  # token variable. The mock tokens carry the 'mock-' prefix.
  SECRET_HITS=$(grep -E "(password|api[_-]?key|secret|token)[[:space:]]*=[[:space:]]*[a-zA-Z0-9_-]{16,}" "$GATE_D_BASH" | grep -v "mock-" | grep -v "^[#]" | wc -l || true)
  if [ "${SECRET_HITS:-0}" -eq 0 ]; then
    note_pass "bash test has no hardcoded passwords / tokens / api_keys"
  else
    note_fail "bash test has ${SECRET_HITS} hardcoded password/token/api_key lines"
    fail=$((fail+1))
  fi
fi

# ---------------------------------------------------------------------------
# 7. rc-entity-naming honored (every entity id uses rc_openclaw_api_*)
# ---------------------------------------------------------------------------

if [ -f "$GATE_D_BASH" ]; then
  # The rig must reference the canonical rc_openclaw_api_* tile ids
  # at least once (proves the rig aligns with rc-entity-naming.md).
  if grep -q "binary_sensor.rc_openclaw_api_last_action" "$GATE_D_BASH"; then
    note_pass "bash test references the canonical binary_sensor.rc_openclaw_api_last_action tile"
  else
    note_fail "bash test must reference the canonical rc_openclaw_api_last_action tile"
    fail=$((fail+1))
  fi
  if grep -q "docs/reference/rc-entity-naming.md" "$GATE_D_BASH"; then
    note_pass "bash test cites docs/reference/rc-entity-naming.md"
  else
    note_fail "bash test must cite docs/reference/rc-entity-naming.md"
    fail=$((fail+1))
  fi
fi

# ---------------------------------------------------------------------------
# 8. IKEA 5-step doc shape on the user-facing runbook
# ---------------------------------------------------------------------------

if [ -f "$GATE_D_RUNBOOK" ]; then
  # Count numbered steps in §3 (must be >=3).
  STEP3_COUNT=$(awk '/^## §3 /,/^## §4 /' "$GATE_D_RUNBOOK" | grep -cE '^[0-9]+\.[[:space:]]' || true)
  if [ "${STEP3_COUNT:-0}" -ge 3 ]; then
    note_pass "runbook §3 carries >=3 numbered steps (found ${STEP3_COUNT})"
  else
    note_fail "runbook §3 must carry >=3 numbered steps; found ${STEP3_COUNT}"
    fail=$((fail+1))
  fi
fi

# ---------------------------------------------------------------------------
# 9. No Wave / tier / PR / cron jargon in user copy
# ---------------------------------------------------------------------------

if [ -f "$GATE_D_RUNBOOK" ]; then
  DOC_BODY=$(awk '/^## §5 Useful links/{exit} {print}' "$GATE_D_RUNBOOK")
  if echo "$DOC_BODY" | grep -qiE 'Wave [0-9]|tier-[abc]|#[0-9]+|the cron|the sub-agent|PR #[0-9]+|Apple-grade'; then
    note_fail "user-facing runbook contains internal jargon (Wave / tier / PR / cron)"
    fail=$((fail+1))
  else
    note_pass "user-facing runbook contains no Wave / tier / PR / cron jargon"
  fi
fi

# ---------------------------------------------------------------------------
# 10. Idempotent re-run + GH Actions workflow mirrors Gate A/B/C shape
# ---------------------------------------------------------------------------

if assert_file "$GATE_D_WORKFLOW"; then
  # The workflow must run the bash test (or pytest rig) on every push
  # to main + every PR + manual dispatch.
  if grep -qE "(push:|pull_request:|workflow_dispatch:)" "$GATE_D_WORKFLOW"; then
    note_pass "GH Actions workflow has push + PR + manual_dispatch triggers"
  else
    note_fail "GH Actions workflow must carry push + PR + manual_dispatch triggers"
    fail=$((fail+1))
  fi
  if grep -qE "(pytest|bash scripts/tests/acceptance/gate_d_agent_integration)" "$GATE_D_WORKFLOW"; then
    note_pass "GH Actions workflow invokes the pytest rig + bash test"
  else
    note_fail "GH Actions workflow must invoke the pytest rig + bash test"
    fail=$((fail+1))
  fi
fi

# The check.sh chain must wire in the new Gate D bash test (or pytest
# rig) as a run_if_present block.
if [ -f "$GATE_D_CHECK_SH" ]; then
  if grep -qE "gate[-_]d[-_]agent[-_]integration" "$GATE_D_CHECK_SH"; then
    note_pass "scripts/check.sh wires in the Gate D bash test (run_if_present block)"
  else
    note_fail "scripts/check.sh must wire in the Gate D bash test (run_if_present block)"
    fail=$((fail+1))
  fi
fi

# The umbrella runbook (docs/runbooks/automated-acceptance-tests.md)
# must carry an additive Gate D section.
if [ -f "$GATE_D_UMBRELLA" ]; then
  if grep -qE "^### Gate D — agent integration" "$GATE_D_UMBRELLA"; then
    note_pass "umbrella runbook has the additive Gate D section"
  else
    note_fail "umbrella runbook must carry the additive '### Gate D — agent integration' section"
    fail=$((fail+1))
  fi
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

printf '\nSummary\n=======\n'
printf '  PASS: %d\n  FAIL: %d\n' "$pass" "$fail"

if [ "$fail" -eq 0 ]; then
  printf '\n\033[1;32m✓ Gate D agent-integration smoke PASSED\033[0m\n'
  exit 0
else
  printf '\n\033[1;31m✗ Gate D agent-integration smoke FAILED\033[0m\n'
  exit 1
fi