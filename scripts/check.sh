#!/usr/bin/env bash
# RoamCore unified smoke-check entrypoint.
#
# Mirrors the convention in scripts/checks/<name>.sh and chains the
# repository's standalone smoke checks in a stable order. Each step is
# idempotent and only inspects repo files (no live HA/Proxmox calls).
#
# Usage:
#   bash scripts/check.sh                # full suite
#   bash scripts/check.sh --core-only    # repo-local checks (HA beta + repo inventory)
#
# Note: this branch was forked from main before the Wave 2 #23-#33 stack
# landed upstream; we ship a minimal chain here. Each slice's PR is expected
# to add its own smoke + wire it into this script (or merge the broader
# check.sh PR from another slice). The chain is intentionally additive:
# missing smoke scripts are skipped, never failed.

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
    case "$script" in
      *.py)
        python3 "$script"
        ;;
      *)
        bash "$script"
        ;;
    esac
  else
    printf '\n\033[1;33m⊘ SKIP\033[0m — %s (script %s not present on this branch)\n' "$label" "$script"
  fi
}

banner "HA-only beta: smoke check"
bash scripts/checks/ha-beta-smoke.sh

# Wave 2 #23-#33 smokes live on their own stacked branches. We probe for
# the well-known names so the chain stays portable; once those PRs land
# on main, they will chain automatically here.
run_if_present "scripts/checks/openwrt-controls-smoke.sh"      "Networking controls (OpenWrt API): smoke check"
run_if_present "scripts/checks/remote-access-tailscale-smoke.sh" "Remote access (Tailscale contract): smoke check"
run_if_present "scripts/checks/ota-smoke.sh"                   "OTA updates: smoke check"
run_if_present "scripts/checks/labs-smoke.sh"                  "RoamCore Labs: smoke check"
run_if_present "scripts/checks/hardware-auto-discovery-smoke.sh" "Hardware auto-discovery + setup flows: smoke check"
run_if_present "scripts/checks/ai-chat-smoke.sh"               "AI chat: smoke check"
run_if_present "scripts/checks/system-summary-smoke.sh"        "System summary: smoke check"
run_if_present "scripts/checks/advanced-mode-smoke.sh"         "Advanced mode: smoke check"
run_if_present "scripts/checks/automation-apply-smoke.sh"      "Automation apply: smoke check"
run_if_present "scripts/checks/mode-builder-smoke.sh"          "Mode builder: smoke check"

# Connection manifest smokes live under connections/<id>/tests/. We probe
# for the well-known names so the chain picks them up automatically once
# the slice lands.
run_if_present "connections/mqtt/tests/test_connection_yml.py" \
  "Connection: MQTT (tier-b) — manifest honesty smoke check"
run_if_present "connections/frigate/tests/test_connection_yml.py" \
  "Connection: Frigate (tier-b) — CCTV with on-device object detection: manifest honesty smoke check"
run_if_present "connections/starlink/tests/test_connection_yml.py" \
  "Connection: Starlink (tier-b) — sleep timer + bring-back-up controls: manifest honesty smoke check"

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

printf '\n\033[1;32m✓ all requested smoke checks passed.\033[0m\n'