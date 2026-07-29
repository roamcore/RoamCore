#!/usr/bin/env bash
# RoamCore unified smoke-check entrypoint.
#
# Mirrors the convention in scripts/checks/<name>.sh and chains the
# repository's standalone smoke checks in a stable order. Each step is
# idempotent and only inspects repo files (no live HA/Proxmox calls).
#
# Usage:
#   bash scripts/check.sh                # full suite
#   bash scripts/check.sh --core-only    # repo-local checks (HA beta + advanced mode + system summary)
#
# Slices wired in:
#   ▶ HA-only beta: smoke check
#   ▶ Advanced mode: smoke check          (slice #25 — added on stacked branch)
#   ▶ System summary: smoke check         (slice #26 — this commit)
#   ▶ RoamCore: repo inventory
#   ▶ Rclone drive health: smoke check
#   ▶ Victron: smoke check
#   ▶ Victron: mapping plan
#   ▶ Victron: RC contract

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

CORE_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --core-only) CORE_ONLY=1 ;;
    -h|--help)
      sed -n '2,14p' "$0"
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

# Slice #25 lives on a stacked branch (feat/wave2-advanced-mode-recovery-safe).
# We probe for it here so the chain stays portable; the file is added on top.
run_if_present "scripts/checks/advanced-mode-smoke.sh" "Advanced mode: smoke check"

banner "System summary: smoke check"
bash scripts/checks/system-summary-smoke.sh

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