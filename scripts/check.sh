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
run_if_present "scripts/checks/hub-bom-smoke.sh"               "RoamCore Hub BOM: manifest + validator smoke check"
run_if_present "scripts/checks/labs-smoke.sh"                  "RoamCore Labs: smoke check"
run_if_present "scripts/checks/hardware-auto-discovery-smoke.sh" "Hardware auto-discovery + setup flows: smoke check"
run_if_present "scripts/checks/ai-chat-smoke.sh"               "AI chat: smoke check"
run_if_present "scripts/checks/system-summary-smoke.sh"        "System summary: smoke check"
run_if_present "scripts/checks/advanced-mode-smoke.sh"         "Advanced mode: smoke check"
run_if_present "scripts/checks/automation-apply-smoke.sh"      "Automation apply: smoke check"
run_if_present "scripts/checks/mode-builder-smoke.sh"          "Mode builder: smoke check"
run_if_present "scripts/checks/remote-access-setup-smoke.sh"    "Remote access setup wizard (Tailscale Path A): smoke check"

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
run_if_present "connections/hub-backup/tests/test_connection_yml.py" \
  "Connection: Hub Backup (tier-a) — nightly automatic snapshot of your Hub that is verified-restorable: manifest honesty smoke check"
run_if_present "homeassistant/packages/tests/test_hub_backup.py" \
  "Hub Backup (Phase 7 — Wave 9 #123.a) — nightly + restore-tested migration: 22 pytest contract tests"
run_if_present "scripts/checks/hub-backup-smoke.sh" \
  "Hub Backup (Phase 7 — Wave 9 #123.a) — nightly + restore-tested migration: 10 bash smoke assertions"
run_if_present "connections/agent-actions-allowlist/tests/test_connection_yml.py" \
  "Connection: Agent actions allowlist (tier-b) — vendor-neutral kill-switch + per-action allowlist + audit-log gateway for safe agent-driven RoamCore actions: manifest honesty smoke check"
run_if_present "scripts/checks/connection-state-smoke.sh" \
  "Connection state field: cross-cutting state-field smoke check (every connection.yml carries a valid state from the 10-state allowlist)"
run_if_present "scripts/checks/catalog-state-chip-smoke.sh" \
  "Catalog UI state chip primitive: kebab CSS classes + pytest rig + every connection.yml state maps to a chip (Wave 9 #118)"
run_if_present "scripts/checks/canonical-capabilities-smoke.sh" \
  "Canonical vehicle model: schema-as-data + validator smoke check (Wave 9 #119)"

# Wave 9 #125 — Phase 1 catalog UI proper: render 27 (28 today)
# connection cards via format_connection_card() + per-connection state
# field. Builds on the Wave 9 #118 chip primitive + the Wave 9 #117
# cross-cutting state field; asserts the render layer emits the right
# card count, the right CSS classes, and the right per-category counts.
run_if_present "scripts/checks/catalog-ui-cards-smoke.sh" \
  "Catalog UI cards (Phase 1 proper): ≥20 cards + state chip + tier chip + Connect button + per-category counts + IKEA shape + CSS lockstep (Wave 9 #125)"

# Wave 9 #120b — Phase 3 Hub restart-stability smoke test rig.
# Reads scripts/build/hub-services.yml + the 5 addon config.yaml files
# + spawns a real port-bind regression to prove every Hub service comes
# back after a reboot. Repo-local only; no live HA / Proxmox calls.
run_if_present "scripts/checks/hub-restart-stability-smoke.sh" \
  "Hub restart-stability: Phase 3 Hub smoke test rig (5 addons + manifest + real port-bind reboot check)"

# Wave 9 #120d — Phase 3 Hub golden image build pipeline (foundation).
# Asserts scripts/build/hub-golden-image.sh + manifest + their cross-
# references are healthy, the manifest pins a reachable + verifiable
# base image, and the script's user-facing surface is plain English.
# Script-only delivery (similar to #106 OpenWrt Image Builder); the
# actual .img.gz bake happens on a Linux+Docker host.
run_if_present "scripts/checks/hub-golden-image-smoke.sh" \
  "Hub golden image: Phase 3 Hub golden-image build pipeline smoke (script + manifest + base-image reachability + SHA format + idempotent cache + retry pattern)"

# Wave 9 #121 — Phase 5 Installable PWA refresh. Static + live-fetch
# verification of the dashboard/Frontend/Setup Wizard scaffold + the
# IKEA-shaped docs/setup/pwa.md user guide. Idempotent + best-effort
# live http.server fetch (skips silently if python3 + curl unavailable).
run_if_present "scripts/checks/pwa-install-smoke.sh" \
  "PWA: install/offline/push smoke (manifest + sw.js hooks + offline.html honesty + install banner + profile store + IKEA doc + live http.server fetch)"

# Wave 9 #121 — Phase 5 Installable PWA refresh. Static + live-fetch
# verification of the dashboard/Frontend/Setup Wizard scaffold + the
# IKEA-shaped docs/setup/pwa.md user guide. Idempotent + best-effort
# live http.server fetch (skips silently if python3 + curl unavailable).
run_if_present "scripts/checks/pwa-install-smoke.sh" \
  "PWA: install/offline/push smoke (manifest + sw.js hooks + offline.html honesty + install banner + profile store + IKEA doc + live http.server fetch)"

# Wave 9 #123.d.iv — Phase 7 Hardened release — Gate D (agent integration).
# Developer-convenience smoke that runs the Gate D bash test in --mock
# mode + the Gate D pytest rig. Idempotent (re-runs produce the same
# end state) + safe on any host (mock mode skips live OpenClaw API
# calls; real API runs are CI-only via HAS_OPENCLAW_API=true).
# NOT part of core-only — developers can run `bash scripts/check.sh`
# (without --core-only) to exercise the Gate D acceptance rig locally
# before opening a PR.
run_if_present "scripts/checks/gate-d-agent-integration-smoke.sh" \
  "Acceptance Gate D (agent integration): 12-stage bash contract (auth + model read + allowlist + confirmation + audit chain + tamper detection + agent failure isolation + multi-tenant isolation + reboot-survives)"

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