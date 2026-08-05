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
run_if_present "scripts/checks/map-offline-smoke.sh"          "Map graceful offline degradation (Wave 9 #111): smoke check"
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
run_if_present "connections/dns-blocker/tests/test_connection_yml.py" \
  "Connection: DNS blocker (Pi-hole / AdGuard) (tier-b) — manifest honesty smoke check"
run_if_present "connections/nas/tests/test_connection_yml.py" \
  "Connection: NAS (Synology / QNAP / SMB) (tier-b) — manifest honesty smoke check"
run_if_present "connections/teltonika/tests/test_connection_yml.py" \
  "Connection: Teltonika (tier-b) — LTE/5G router for vans: manifest honesty smoke check"
run_if_present "connections/peplink/tests/test_connection_yml.py" \
  "Connection: Peplink (tier-b) — multi-WAN router for vans: manifest honesty smoke check"
run_if_present "connections/music-assistant/tests/test_connection_yml.py" \
  "Connection: Music Assistant (tier-b) — manifest honesty smoke check"
run_if_present "connections/bluetooth-wifi-presence/tests/test_connection_yml.py" \
  "Connection: Bluetooth/Wi-Fi presence (tier-b) — manifest honesty smoke check"
run_if_present "connections/happijac/tests/test_connection_yml.py" \
  "Connection: Happijac bed lift (tier-b) — manifest honesty smoke check"
run_if_present "connections/heated-floors/tests/test_connection_yml.py" \
  "Connection: Heated floors + engine pre-heat (tier-b) — manifest honesty smoke check"
run_if_present "connections/smoke-co-gas-sensors/tests/test_connection_yml.py" \
  "Connection: Smoke / CO / gas sensors (tier-b) — manifest honesty smoke check"
run_if_present "connections/smart-automations/tests/test_connection_yml.py" \
  "Connection: Smart automations (tier-b) — manifest honesty smoke check"
run_if_present "connections/mock-location-and-tracks/tests/test_connection_yml.py" \
  "Connection: Mock location + track replay (tier-a) — manifest honesty smoke check"
run_if_present "connections/deadbolts/tests/test_connection_yml.py" \
  "Connection: Deadbolts (smart lock control) (tier-b) — manifest honesty smoke check"
run_if_present "connections/hvac-basics/tests/test_connection_yml.py" \
  "Connection: HVAC basics (heating/cooling foundations) (tier-b) — manifest honesty smoke check"
run_if_present "connections/motion-based-lighting/tests/test_connection_yml.py" \
  "Connection: Motion-based lighting (driving + arrival) (tier-b) — manifest honesty smoke check"
run_if_present "connections/timezone-geolocator/tests/test_connection_yml.py" \
  "Connection: Timezone geolocator (tier-c) — manifest honesty smoke check"
run_if_present "connections/time-atomic/tests/test_connection_yml.py" \
  "Connection: Time (atomic) (tier-c) — manifest honesty smoke check"
run_if_present "connections/in-cab-tablet-dashboard/tests/test_connection_yml.py" \
  "Connection: In-cab tablet dashboard (tier-c) — manifest honesty smoke check"
run_if_present "connections/nfc-tags/tests/test_connection_yml.py" \
  "Connection: NFC tags (tier-c) — manifest honesty smoke check"
run_if_present "connections/remote-access/tests/test_connection_yml.py" \
  "Connection: Remote access (Tailscale + Cloudflare Tunnel + Nabu Casa + Wireguard, tier-b) — manifest honesty smoke check"
run_if_present "connections/fans/tests/test_connection_yml.py" \
  "Connection: Fans (rooftop + circulation) (tier-b) — vendor-neutral fan controller + rain-sensor safety block: manifest honesty smoke check"
run_if_present "connections/leveling/tests/test_connection_yml.py" \
  "Connection: Leveling (IMU) (tier-b) — vendor-neutral pitch/roll + auto-jack + fridge-safe gate: manifest honesty smoke check"
run_if_present "connections/mode/tests/test_connection_yml.py" \
  "Connection: Mode (AI mode) (tier-b) — vendor-neutral mode state (Off/Auto/Travel/Camp/Stealth) + opt-in AI inference + auto-revert: manifest honesty smoke check"
run_if_present "connections/demo-mode/tests/test_connection_yml.py" \
  "Connection: Demo mode (tier-b) — vendor-neutral demo values for missing sensors + auto-disable on real sensor reconnect + never-controls-hardware guard: manifest honesty smoke check"
run_if_present "connections/advanced-mode/tests/test_connection_yml.py" \
  "Connection: Advanced mode (tier-b) — vendor-neutral power-user toggle + session-timeout guard + destructive-calls block: manifest honesty smoke check"
run_if_present "connections/openclaw-api/tests/test_connection_yml.py" \
  "Connection: OpenClaw JSON API (tier-a) — vendor-neutral machine-readable summary + skill + rc_dump + timeseries endpoints for local agents: manifest honesty smoke check"
run_if_present "connections/agent-actions-allowlist/tests/test_connection_yml.py" \
  "Connection: Agent actions allowlist (tier-b) — vendor-neutral kill-switch + per-action allowlist + audit-log gateway for safe agent-driven RoamCore actions: manifest honesty smoke check"

# RoamCore custom-component unit tests (Wave 9 #113 — Gate D).
# Audit chain + confirmation flow tests live under the roamcore custom
# component and run against the in-repo `roamcore` package (no live
# HA required).
if [ -d "homeassistant/custom_components/roamcore/tests" ]; then
  banner "RoamCore custom component (Gate D): audit chain + confirmation flow"
  if [ -f "homeassistant/custom_components/roamcore/tests/pytest.ini" ]; then
    (cd homeassistant/custom_components/roamcore/tests && python3 -m pytest)
  else
    python3 -m pytest homeassistant/custom_components/roamcore/tests/
  fi
fi
run_if_present "connections/openwrt/tests/test_connection_yml.py" \
  "Connection: OpenWrt auto-pair (LAN-probe daemon + auto-add + token push) (tier-a) — manifest honesty smoke check"
run_if_present "connections/openwrt/tests/test_pair.py" \
  "Connection: OpenWrt auto-pair (LAN-probe daemon + auto-add + token push) (tier-a) — discovery + pair pytest HTTP probe (fake-bind mock + aiohttp skip-when-missing)"

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