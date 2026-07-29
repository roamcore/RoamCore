#!/usr/bin/env bash
# RoamCore unified smoke-check entrypoint.
#
# Mirrors the convention in scripts/checks/<name>.sh and chains the
# repository's standalone smoke checks in a stable order. Each step is
# idempotent and only inspects repo files (no live HA/Proxmox calls).
#
# Usage:
#   bash scripts/check.sh                # full suite
#   bash scripts/check.sh --core-only    # repo-local checks (HA beta + AI chat smoke)
#
# Slices wired in:
#   ▶ HA-only beta: smoke check
#   ▶ AI chat: smoke check              (slice #27 — this commit)
#
# Note: main does not yet have a broader check.sh; we ship a minimal chain
# here. Each slice's PR is expected to add its own smoke + wire it into this
# script (or merge the broader check.sh PR). The chain is intentionally
# additive: missing smoke scripts are skipped, never failed.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

CORE_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --core-only) CORE_ONLY=1 ;;
    -h|--help)
      sed -n '2,18p' "$0"
      exit 0
      ;;
    *) ;;
  esac
done

# Pretty banner for each step.
banner() {
  printf '\n\033[1;36m▶ %s\033[0m\n' "$1"
}

# Helper: run a named smoke check if its script exists; otherwise skip with
# a clear message. Lets stacked branches add their own checks without
# breaking the chain on origin/main.
run_if_present() {
  local script="$1"
  local label="$2"
  if [ -f "$script" ]; then
    banner "$label"
    bash "$script"
  else
    printf '\n\033[1;33m⊘ SKIP\033[0m — %s (script %s not present on this branch)\n' "$label" "$script"
  fi
}

banner "HA-only beta: smoke check"
bash scripts/checks/ha-beta-smoke.sh

banner "AI chat: smoke check"
bash scripts/checks/ai-chat-smoke.sh

# Slice #25 lives on a stacked branch (feat/wave2-advanced-mode-recovery-safe).
# Slice #26 lives on a stacked branch (feat/wave2-system-summary-deterministic).
# We probe for both so the chain stays portable; the files are added on top.
run_if_present "scripts/checks/advanced-mode-smoke.sh" "Advanced mode: smoke check"
run_if_present "scripts/checks/system-summary-smoke.sh" "System summary: smoke check"

if [ "$CORE_ONLY" -eq 0 ]; then
  banner "RoamCore: repo inventory"
  bash scripts/checks/roamcore-inventory.sh || true
  banner "Rclone drive health: smoke check"
  bash scripts/checks/rclone-drive-health.sh || true
  banner "Victron: smoke check"
  bash scripts/checks/victron-checks.sh || true
  banner "Victron: mapping plan"
  bash scripts/checks/victron-mapping-plan.sh || true
  banner "Victron: RC contract"
  bash scripts/checks/victron-rc-contract.sh || true
fi

printf '\n\033[1;32m✓ All checks passed\033[0m\n'