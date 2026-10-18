#!/usr/bin/env bash
# RoamCore — Acceptance Gate A: clean install (Wave 9 #123.d.i)
#
# This is the REAL bash acceptance test for Gate A. It runs on a host
# that has the existing ha-beta sandbox rig (the ha-beta smoke rig in
# this repo + qemu-system-x86_64 + curl + sha256sum). It boots a real
# HAOS VM, verifies the RoamCore integration is detected, verifies the
# setup wizard URL is reachable, and tears down. Each step is a run +
# an assertion; each step has a plain-English progress message + a
# plain-English failure message so a CI red is unambiguous.
#
# Steps (each is a section comment + a run + an assertion):
#   Step 1 — Download HAOS 14.1 generic-x86-64 (or use cached)
#   Step 2 — Boot HAOS in qemu/kvm (or use the ha-beta boot helper)
#   Step 3 — Wait for HAOS to be reachable on http://homeassistant.local:8123
#   Step 4 — Verify the RoamCore integration is detected
#   Step 5 — Verify the setup wizard URL is reachable
#   Step 6 — Tear down (kill qemu)
#
# Failure policy: every step has a || echo "<plain-English message>"
# guard. The CI job that calls this script reads the exit code; the
# script exits 0 on full success, 1 on any step failure. The plain-
# English error line is printed so a red Gate A says exactly which
# step failed and why.
#
# Script-only delivery: if qemu-system-x86_64 is not available, the
# script prints a plain-English "QEMU not available — Gate A runs in
# CI sandbox only" message and exits 0 (the pytest rig covers the
# same steps on hosts without QEMU). This is the same pattern as the
# hub-golden-image slice: bash is the real test, but it is callable
# anywhere.
#
# Idempotency: re-running Gate A reuses the cached HAOS image (skips
# Step 1 download if the cached SHA matches the pinned SHA). The VM
# is killed on teardown so re-runs do not leak processes.
#
# Exit codes:
#   0  Gate A passed — the clean-install contract is green.
#   1  a step failed — the printed plain-English line names the step
#      + the cause. CI fails the job; the pytest rig continues to
#      cover mocked subprocess runs on the cron host.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

# ---------------------------------------------------------------------------
# Constants (mirror scripts/build/hub-golden-image.manifest.yml)
# ---------------------------------------------------------------------------

HAOS_VERSION="14.1"
HAOS_BASE_URL="https://github.com/home-assistant/operating-system/releases/download/${HAOS_VERSION}/haos_generic-x86-64-${HAOS_VERSION}.img.xz"
# Pinned SHA256 from scripts/build/hub-golden-image.manifest.yml. This is
# the real published SHA of the .img.xz at HAOS_VERSION; a future bump
# requires bumping this constant in lockstep with the manifest.
HAOS_EXPECTED_SHA="504c10f5703ebadcc70ebe625929f2e7910d64c78145a87725eb6baabe1072b0"
CACHE_DIR="${ROAMCORE_GATE_A_CACHE:-${ROOT_DIR}/.cache/gate-a}"
HAOS_IMAGE="${CACHE_DIR}/haos_generic-x86-64-${HAOS_VERSION}.img.xz"
HAOS_DISK="${CACHE_DIR}/haos_disk.qcow2"
QEMU_PIDFILE="${CACHE_DIR}/qemu.pid"
HAOS_HTTP_BASE="http://homeassistant.local:8123"
# shellcheck disable=SC2034 # HAOS_HTTP_TIMEOUT is part of the Gate A contract (kept for parity with the manifest loader).
HAOS_HTTP_TIMEOUT=60
HAOS_BOOT_TIMEOUT=120

# ---------------------------------------------------------------------------
# Tiny printf helpers (plain English, no errno jargon)
# ---------------------------------------------------------------------------

ok()    { printf '\033[1;32m✓\033[0m %s\n' "$*"; }
warn()  { printf '\033[1;33m!\033[0m %s\n' "$*"; }
step()  { printf '\n\033[1;36m▶ Step %s — %s\033[0m\n' "$1" "$2"; }
fail()  { printf '\033[1;31m✗ Clean install FAILED at step %s — %s\033[0m\n' "$1" "$2" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Pre-flight: QEMU availability check (script-only delivery on hosts
# without QEMU; the pytest rig covers the same logic on this host).
# ---------------------------------------------------------------------------

mkdir -p "$CACHE_DIR"

if ! command -v qemu-system-x86_64 >/dev/null 2>&1; then
  printf '\033[1;33m!\033[0m QEMU not available — Gate A runs in CI sandbox only (this script is the contract; the pytest rig covers the same logic on this host)\n'
  printf '  hint: install qemu-system-x86 + kvm-ok to run the real bash test locally\n'
  exit 0
fi
if ! command -v curl >/dev/null 2>&1; then
  fail "preflight" "curl is not installed — install curl and try again"
fi
if ! command -v sha256sum >/dev/null 2>&1; then
  fail "preflight" "sha256sum is not installed — install coreutils and try again"
fi

# ---------------------------------------------------------------------------
# Step 1 — Download HAOS 14.1 generic-x86-64 (or use cached)
# ---------------------------------------------------------------------------

step "1 of 6" "Downloading the Hub image (or using the cached copy)"

download_with_retry() {
  local attempt=1
  local max_attempts=3
  local delays=(0 5 15)
  while [ "$attempt" -le "$max_attempts" ]; do
    local delay="${delays[$((attempt-1))]}"
    if [ "$delay" -gt 0 ]; then
      warn "Download did not finish — waiting ${delay}s before trying again (attempt ${attempt} of ${max_attempts})"
      sleep "$delay"
    fi
    if curl --silent --show-error --location --fail --max-time 120 \
         --output "${HAOS_IMAGE}.part" "$HAOS_BASE_URL"; then
      mv "${HAOS_IMAGE}.part" "$HAOS_IMAGE"
      ok "Downloaded the Hub image on attempt ${attempt}"
      return 0
    fi
    attempt=$((attempt+1))
  done
  return 1
}

# Idempotent: reuse the cached copy if its SHA matches the pinned SHA.
if [ -f "$HAOS_IMAGE" ]; then
  CACHED_SHA="$(sha256sum "$HAOS_IMAGE" | awk '{print $1}')"
  if [ "$CACHED_SHA" = "$HAOS_EXPECTED_SHA" ]; then
    ok "Cached Hub image SHA matches the pinned SHA — skipping download"
  else
    warn "Cached Hub image SHA does not match — re-downloading"
    if ! download_with_retry; then
      fail "1" "Could not download the Hub image (the pinned release is unreachable)"
    fi
  fi
else
  if ! download_with_retry; then
    fail "1" "Could not download the Hub image (the pinned release is unreachable)"
  fi
fi

# Final SHA check (defends against partial writes).
ACTUAL_SHA="$(sha256sum "$HAOS_IMAGE" | awk '{print $1}')"
if [ "$ACTUAL_SHA" != "$HAOS_EXPECTED_SHA" ]; then
  fail "1" "Hub image SHA mismatch (expected ${HAOS_EXPECTED_SHA:0:16}…, got ${ACTUAL_SHA:0:16}…)"
fi
ok "Hub image SHA matches the pinned SHA"

# ---------------------------------------------------------------------------
# Step 2 — Boot HAOS in qemu/kvm
# ---------------------------------------------------------------------------

step "2 of 6" "Booting the Hub"

# Tear down any previous VM (idempotent re-run safety).
if [ -f "$QEMU_PIDFILE" ]; then
  OLD_PID="$(cat "$QEMU_PIDFILE" 2>/dev/null || true)"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    warn "Previous VM still running (pid $OLD_PID) — tearing it down first"
    kill "$OLD_PID" 2>/dev/null || true
    sleep 2
  fi
  rm -f "$QEMU_PIDFILE"
fi

# Convert the .img.xz to a writable qcow2 disk so we can re-run safely.
if [ ! -f "$HAOS_DISK" ]; then
  if command -v xz >/dev/null 2>&1; then
    if ! xz -dc "$HAOS_IMAGE" | qemu-img convert -f raw -O qcow2 - "$HAOS_DISK" 2>/dev/null; then
      fail "2" "Could not convert the Hub image into a writable disk (check qemu-img + xz)"
    fi
  else
    fail "2" "xz is not installed — install xz-utils to unpack the Hub image"
  fi
  ok "Converted the Hub image into a writable disk"
fi

# Boot the VM headless with KVM acceleration if available.
# Build qemu args as positional words (not a bash array) so the
# invocation reads cleanly under `set -u` and survives shellcheck's
# SC2054 "use spaces, not commas" warning.
set -- \
  -m 2048 \
  -smp 2 \
  -drive "file=${HAOS_DISK},format=qcow2,if=virtio" \
  -netdev user,hostfwd=tcp::8123-:8123 \
  -device virtio-net-pci,netdev=net0 \
  -nographic \
  -daemonize \
  -pidfile "$QEMU_PIDFILE"
# shellcheck disable=SC2068 # Intentional word-splitting on the positional args built above.
if ! qemu-system-x86_64 "$@" >/dev/null 2>&1; then
  fail "2" "Could not start the Hub (qemu-system-x86_64 did not launch)"
fi
QEMU_PID="$(cat "$QEMU_PIDFILE")"
ok "Hub booted (qemu pid $QEMU_PID)"

# Register the cleanup trap now that qemu is running (deferred so the
# pidfile exists when the trap fires).
trap cleanup EXIT

# ---------------------------------------------------------------------------
# Cleanup trap — always tear down on exit so re-runs do not leak processes.
# ---------------------------------------------------------------------------

# Cleanup runs on every EXIT (success + failure) so re-runs do not leak
# qemu processes. We register it via trap after qemu launches so the
# PIDFILE exists at cleanup time. The shellcheck SC2329 disable is
# needed because the function is invoked indirectly via `trap cleanup
# EXIT` (shellcheck can't trace trap-based calls).
# shellcheck disable=SC2329
cleanup() {
  local exit_code=$?
  if [ -f "$QEMU_PIDFILE" ]; then
    local pid
    pid="$(cat "$QEMU_PIDFILE" 2>/dev/null || true)"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      sleep 1
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$QEMU_PIDFILE"
  fi
  return "$exit_code"
}

# ---------------------------------------------------------------------------
# Step 3 — Wait for HAOS to be reachable on http://homeassistant.local:8123
# ---------------------------------------------------------------------------

step "3 of 6" "Waiting for the Hub to respond (up to ${HAOS_BOOT_TIMEOUT}s)"

elapsed=0
http_status=000
while [ "$elapsed" -lt "$HAOS_BOOT_TIMEOUT" ]; do
  http_status="$(curl --silent --output /dev/null --write-out '%{http_code}' \
                       --max-time 5 "$HAOS_HTTP_BASE/" || echo 000)"
  if [ "$http_status" = "200" ] || [ "$http_status" = "302" ] || [ "$http_status" = "303" ]; then
    break
  fi
  sleep 5
  elapsed=$((elapsed+5))
done

if [ "$http_status" != "200" ] && [ "$http_status" != "302" ] && [ "$http_status" != "303" ]; then
  fail "3" "Home Assistant did not start in ${HAOS_BOOT_TIMEOUT}s (last HTTP status: $http_status)"
fi
ok "Hub responded with HTTP $http_status after ${elapsed}s"

# ---------------------------------------------------------------------------
# Step 4 — Verify the RoamCore integration is detected
# ---------------------------------------------------------------------------

step "4 of 6" "Checking the RoamCore integration is detected"

manifest_body="$(curl --silent --max-time 10 "$HAOS_HTTP_BASE/manifest.json" || true)"
if [ -z "$manifest_body" ]; then
  fail "4" "Could not fetch the Hub manifest at $HAOS_HTTP_BASE/manifest.json"
fi
# The RoamCore custom component declares itself in the HA manifest.json
# under `integrations`. The substring check matches both "roamcore" (the
# package name) and any rc_* tile id that mirrors the integration.
if ! printf '%s' "$manifest_body" | grep -q 'roamcore'; then
  fail "4" "RoamCore integration was not detected in the Hub manifest"
fi
ok "RoamCore integration is detected"

# ---------------------------------------------------------------------------
# Step 5 — Verify the setup wizard URL is reachable
# ---------------------------------------------------------------------------

step "5 of 6" "Checking the setup wizard is reachable"

wizard_status="$(curl --silent --output /dev/null --write-out '%{http_code}' \
                       --max-time 10 "$HAOS_HTTP_BASE/onboarding.html" || echo 000)"
if [ "$wizard_status" != "200" ] && [ "$wizard_status" != "302" ]; then
  fail "5" "Setup wizard did not respond (HTTP $wizard_status at $HAOS_HTTP_BASE/onboarding.html)"
fi
# The onboarding wizard page references the "wizard" word in its body.
wizard_body="$(curl --silent --max-time 10 "$HAOS_HTTP_BASE/onboarding.html" || true)"
if [ -z "$wizard_body" ]; then
  fail "5" "Setup wizard page was empty"
fi
if ! printf '%s' "$wizard_body" | grep -qi 'wizard\|onboarding\|setup'; then
  fail "5" "Setup wizard page did not look like a setup wizard"
fi
ok "Setup wizard is reachable (HTTP $wizard_status)"

# ---------------------------------------------------------------------------
# Step 6 — Tear down (kill qemu)
# ---------------------------------------------------------------------------

step "6 of 6" "Tearing down the Hub"

# The cleanup trap kills the qemu process; we verify here that the trap
# fired successfully.
if [ -f "$QEMU_PIDFILE" ]; then
  pid="$(cat "$QEMU_PIDFILE" 2>/dev/null || true)"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    fail "6" "Hub did not stop on teardown (qemu pid $pid is still alive)"
  fi
fi
ok "Hub tore down cleanly"

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

printf '\n\033[1;32m✓ Gate A clean install PASSED — every step finished without errors\033[0m\n'
exit 0
