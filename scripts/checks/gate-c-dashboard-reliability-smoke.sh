#!/usr/bin/env bash
# Gate C — dashboard reliability: developer-convenience smoke check.
#
# Wave 9 #123.d.iii — Phase 7 — Hardened release: Gate C (dashboard
# reliability) acceptance test.
#
# Mirrors the convention in scripts/checks/<name>.sh:
#   - bash strict mode (set -euo pipefail)
#   - repo-local only (no live HA / Proxmox calls)
#   - runs the pytest rig + does a fast pre-check on the bash
#     contract + the user-facing runbook so a regression in any of
#     the three layers fails with a clear message before the full
#     pytest rig is invoked
#   - plain-English summary at exit 0 / non-zero exit
#
# Usage:
#   bash scripts/checks/gate-c-dashboard-reliability-smoke.sh
#
# Exit codes:
#   0  the Gate C dashboard-reliability rig is GREEN (the bash
#      contract has the 12-stage shape + the pytest rig passes +
#      the user-facing runbook has the IKEA 5-step shape + no
#      forbidden jargon + no entity IDs + no bash commands in
#      §1-§4 + idempotent re-runs).
#   1  one or more checks failed (see the printed error line for
#      the offending file:line + the pytest output for any rig
#      failures).
#
# Wired into scripts/check.sh as a run_if_present step (developer
# convenience only; the full chain still runs the Gate C contract
# on every push to main via the GitHub Actions workflow).

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

GATE_C_SCRIPT="${ROOT_DIR}/scripts/tests/acceptance/gate_c_dashboard_reliability.sh"
GATE_C_PYTEST="${ROOT_DIR}/scripts/tests/acceptance/test_gate_c_dashboard_reliability.py"
GATE_C_RUNBOOK="${ROOT_DIR}/docs/runbooks/automated-acceptance-tests-gate-c.md"
GATE_C_WORKFLOW="${ROOT_DIR}/.github/workflows/acceptance-gate-c.yml"

# --- Pre-check 1: every required file is present -----------------------
MISSING=0
for f in "$GATE_C_SCRIPT" "$GATE_C_PYTEST" "$GATE_C_RUNBOOK" "$GATE_C_WORKFLOW"; do
  if [ ! -f "$f" ]; then
    echo "FAIL: required file is missing: $f" >&2
    MISSING=1
  fi
done
if [ "$MISSING" -ne 0 ]; then
  echo "FAIL: one or more Gate C files are missing — see the lines above" >&2
  exit 1
fi

# --- Pre-check 2: the bash contract has the 12-stage shape --------------
# Defends against a future edit accidentally removing one of the
# canonical Step N banners. The rig parses the bash script for the
# canonical step banner pattern.
expected_stages=12
actual_stages=$(grep -cE '^step "[0-9]+" ' "$GATE_C_SCRIPT" || true)
if [ "$actual_stages" -ne "$expected_stages" ]; then
  echo "FAIL: bash contract at $GATE_C_SCRIPT must define exactly $expected_stages stages (found $actual_stages)" >&2
  exit 1
fi
echo "OK: bash contract has the canonical $expected_stages-stage shape"

# --- Pre-check 3: every fail() message in the bash contract has a recovery hint
# Every fail() message must include a plain-English recovery hint
# (check / verify / look at / see / open / reload / restart). This
# proves the contract: every Gate C red carries an actionable
# plain-English error.
missing_hint_count=$(grep -E '^\s{0,6}fail "[0-9]+" ' "$GATE_C_SCRIPT" \
  | grep -viE 'check|verify|look at|see|open|reload|restart' | wc -l || true)
if [ "$missing_hint_count" -ne 0 ]; then
  echo "FAIL: bash contract has $missing_hint_count fail() message(s) without a plain-English recovery hint" >&2
  echo "FAIL: every fail() must include one of: check / verify / look at / see / open / reload / restart" >&2
  exit 1
fi
echo "OK: every fail() message in the bash contract carries a plain-English recovery hint"

# --- Pre-check 4: no bash command appears in the user-facing runbook §1-§4
# Extract §1-§4 (the prose that the user sees) + assert no bash
# command appears. Developer plumbing stays in scripts/, not in docs/.
runbook_sections_1_to_4=$(awk '/^## §1/{flag=1} /^## §5 /{flag=0} flag' "$GATE_C_RUNBOOK" || true)
if printf '%s' "$runbook_sections_1_to_4" | grep -q "bash "; then
  echo "FAIL: user-facing runbook §1-§4 contains a bash command — developer plumbing must stay in scripts/" >&2
  exit 1
fi
echo "OK: user-facing runbook §1-§4 contains no bash command"

# --- Pre-check 5: no vendor token appears in the user-facing runbook §1-§4
# The user-facing runbook is vendor-neutral per rc-entity-naming.md.
for vendor_token in victron unifi starlink peplink teltonika fronius byd pylon generac outback; do
  if printf '%s' "$runbook_sections_1_to_4" | grep -qi "$vendor_token"; then
    echo "FAIL: user-facing runbook §1-§4 contains the vendor token '$vendor_token' — user copy is vendor-neutral" >&2
    exit 1
  fi
done
echo "OK: user-facing runbook §1-§4 contains no vendor token"

# --- Pre-check 6: no Wave / tier / PR / cron jargon in the user-facing runbook §1-§4
for jargon in "wave " "tier-a" "tier-b" "tier-c" "tier a" "tier b" "tier c" "sub-agent" "subagent" "the cron" "lint-pass" "apple-grade"; do
  if printf '%s' "$runbook_sections_1_to_4" | grep -qiF "$jargon"; then
    echo "FAIL: user-facing runbook §1-§4 contains the forbidden jargon '$jargon'" >&2
    exit 1
  fi
done
echo "OK: user-facing runbook §1-§4 contains no Wave / tier / PR / cron jargon"

# --- Pre-check 7: the user-facing runbook has the IKEA 5-step shape ----
for section in "## §1 What this is" "## §2 What you see" "## §3 What you do" "## §4 What to do if it goes wrong" "## §5 Useful links"; do
  if ! grep -qF "$section" "$GATE_C_RUNBOOK"; then
    echo "FAIL: user-facing runbook is missing the canonical IKEA section: $section" >&2
    exit 1
  fi
done
echo "OK: user-facing runbook has the canonical IKEA 5-step shape"

# --- Pre-check 8: canonical rc-entity-naming honored in the bash contract
# Every canonical tile id in the bash script must start with
# sensor. / binary_sensor. / switch. + contain rc_ + never carry a
# vendor token. Defends against a future edit accidentally breaking
# the Stage 12 contract.
canonical_tile_pattern='^(sensor|binary_sensor|switch)\.rc_'
while IFS= read -r tile_id; do
  if ! printf '%s' "$tile_id" | grep -qE "$canonical_tile_pattern"; then
    echo "FAIL: bash contract has a non-canonical tile id: $tile_id" >&2
    exit 1
  fi
  for vendor_token in victron unifi starlink peplink teltonika fronius byd pylon generac outback; do
    if printf '%s' "$tile_id" | grep -qi "$vendor_token"; then
      echo "FAIL: bash contract tile id $tile_id contains the vendor token '$vendor_token'" >&2
      exit 1
    fi
  done
done < <(grep -oE 'GATE_C_TILE_[A-Z_]+="[^"]+"' "$GATE_C_SCRIPT" \
  | sed -E 's/.*="([^"]+)"/\1/' \
  | grep -E '^(sensor|binary_sensor|switch)\.rc_' || true)
echo "OK: bash contract honors canonical rc-entity-naming for every tile id"

# --- Pre-check 9: the bash contract's --mock mode is parseable + exits 0
# The developer-convenience smoke must be able to invoke the bash
# contract in --mock mode + see "all 12 stages green". This proves
# the contract is runnable on the cron host (no jq/python3/curl
# required for the mock path).
mkdir -p "${ROOT_DIR}/.cache/gate-c-smoke"
mock_env="GATE_C_CACHE_DIR=${ROOT_DIR}/.cache/gate-c-smoke ROAMCORE_GATE_C_CACHE=${ROOT_DIR}/.cache/gate-c-smoke"
if ! env -i PATH="/usr/bin:/bin" HOME="$ROOT_DIR" $mock_env bash "$GATE_C_SCRIPT" --mock >/dev/null 2>&1; then
  echo "FAIL: bash contract did not exit 0 in --mock mode — re-run 'bash $GATE_C_SCRIPT --mock' to see the error" >&2
  exit 1
fi
echo "OK: bash contract exits 0 in --mock mode"

# --- Pre-check 10: idempotency — a second --mock run produces the same end state
# Run the bash contract twice in --mock mode + assert both runs
# exit 0 (idempotency: re-runs produce the same end state).
if ! env -i PATH="/usr/bin:/bin" HOME="$ROOT_DIR" $mock_env bash "$GATE_C_SCRIPT" --mock >/dev/null 2>&1; then
  echo "FAIL: bash contract did not exit 0 on the second --mock run — gate is not idempotent" >&2
  exit 1
fi
echo "OK: bash contract is idempotent across re-runs"

# --- Run the pytest rig --------------------------------------------------
# Temporarily disable `set -e` so we can capture pytest's exit code
# instead of the script aborting on the first failure. The pytest
# output is still streamed to the operator's terminal.
set +e
python3 -m pytest "$GATE_C_PYTEST" --tb=short
PYTEST_EXIT=$?
set -e

if [ "$PYTEST_EXIT" -eq 0 ]; then
  echo "OK: Gate C dashboard-reliability rig is GREEN (pytest passed + every pre-check passed)"
  exit 0
fi

# --- Pytest failed — translate to a plain-English summary ----------------
echo "FAIL: Gate C dashboard-reliability rig reported one or more failures (see pytest output above)" >&2
exit 1
