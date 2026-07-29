#!/usr/bin/env bash
# RoamCore unified smoke-check entrypoint.
#
# Mirrors the convention in scripts/checks/<name>.sh and chains the
# repository's standalone smoke checks in a stable order. Each step is
# idempotent and only inspects repo files (no live HA/Proxmox calls).
#
# Usage:
#   bash scripts/check.sh                # full suite
#   bash scripts/check.sh --core-only    # repo-local checks (HA beta + advanced mode)
#
# Slice #25 wires these on top of main:
#   ▶ Advanced mode: smoke check

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

CORE_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --core-only) CORE_ONLY=1 ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *) ;;
  esac
done

# Pretty banner for each step.
banner() {
  printf '\n\033[1;36m▶ %s\033[0m\n' "$1"
}

banner "HA-only beta: smoke check"
bash scripts/checks/ha-beta-smoke.sh

banner "Advanced mode: smoke check"
bash scripts/checks/advanced-mode-smoke.sh

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