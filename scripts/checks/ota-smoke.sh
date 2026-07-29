#!/usr/bin/env bash
set -euo pipefail

# RoamCore — OTA updates (GitHub channel + rollback-aware) smoke check.
#
# Validates the Wave 2 #30 slice is present and consistent in the repo:
#   1. Add-on structure: config.yaml parses; Dockerfile exists; run.sh
#      equivalent (s6 service runner) exists; daemon script exists.
#   2. Contract package YAML parses and declares the 4 sensors + 3 helpers.
#   3. Wizard snippet YAML parses and references all 4 contract entities.
#   4. docs/setup/ota.md has the required sections.
#   5. docs/architecture/ota-channel.md has the design sections.
#   6. docs/feature-checklist.md line 71 is ticked `[x]` for OTA updates.
#   7. Docker build helper probe: skip with a clear log if not available.
#
# This script is purely static — it never reaches out to a running HA or
# GitHub API. It exits non-zero on the first failed assertion.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

ADDON="homeassistant/addons/roamcore_ota"
PKG="homeassistant/packages/roamcore_ota.yaml"
WIZ="homeassistant/packages/roamcore_setup_wizard_ota.yaml"
SETUP_DOC="docs/setup/ota.md"
ARCH_DOC="docs/architecture/ota-channel.md"
CHECKLIST="docs/feature-checklist.md"

fail() { echo "ERROR: $*" >&2; exit 1; }
pass() { echo "  PASS: $*"; }

# --- Pre-flight -----------------------------------------------------------
[ -d "$ADDON" ] || fail "missing add-on dir: $ADDON"
[ -f "$ADDON/config.yaml" ] || fail "missing $ADDON/config.yaml"
[ -f "$ADDON/Dockerfile" ] || fail "missing $ADDON/Dockerfile"
[ -f "$ADDON/rootfs/usr/bin/roamcore-otad" ] || fail "missing daemon script $ADDON/rootfs/usr/bin/roamcore-otad"
[ -f "$ADDON/rootfs/etc/services.d/roamcore_ota/run" ] || fail "missing s6 run script $ADDON/rootfs/etc/services.d/roamcore_ota/run"
[ -f "$ADDON/rootfs/etc/services.d/roamcore_ota/finish" ] || fail "missing s6 finish script"
[ -f "$PKG" ] || fail "missing $PKG"
[ -f "$WIZ" ] || fail "missing $WIZ"
[ -f "$SETUP_DOC" ] || fail "missing $SETUP_DOC"
[ -f "$ARCH_DOC" ] || fail "missing $ARCH_DOC"
[ -f "$CHECKLIST" ] || fail "missing $CHECKLIST"

# --- 1. config.yaml parses (basic YAML sanity) -----------------------------
echo "== add-on structure =="
python3 -c 'import sys,yaml; yaml.safe_load(open(sys.argv[1],"r",encoding="utf-8"))' "$ADDON/config.yaml" \
  || fail "YAML parse failed: $ADDON/config.yaml"
pass "$ADDON/config.yaml parses as YAML"

# Add-on config must declare slug + arch + map + options + schema
for needle in "slug:" "arch:" "map:" "options:" "schema:"; do
  grep -qF "$needle" "$ADDON/config.yaml" || fail "$ADDON/config.yaml missing '$needle'"
done
pass "$ADDON/config.yaml declares slug/arch/map/options/schema"

# Declared channels must include stable / beta / nightly.
if ! grep -qE "list\(stable\|beta\|nightly\)" "$ADDON/config.yaml"; then
  fail "$ADDON/config.yaml schema missing 'list(stable|beta|nightly)' for the channel option"
fi
pass "$ADDON/config.yaml declares channel option as list(stable|beta|nightly)"

# Daemon script must reference urllib.request (no requests lib).
if ! grep -qE "urllib\.request" "$ADDON/rootfs/usr/bin/roamcore-otad"; then
  fail "daemon script does not use urllib.request"
fi
if grep -qE "^import requests\b|^from requests\b" "$ADDON/rootfs/usr/bin/roamcore-otad"; then
  fail "daemon script imports the 'requests' library (not allowed)"
fi
pass "daemon script uses stdlib urllib.request only"

# --- 2. Contract package declares the 4 sensors + 3 helpers --------------
echo "== contract entities declared =="
python3 -c 'import sys,yaml; yaml.safe_load(open(sys.argv[1],"r",encoding="utf-8"))' "$PKG" \
  || fail "YAML parse failed: $PKG"
python3 -c 'import sys,yaml; yaml.safe_load(open(sys.argv[1],"r",encoding="utf-8"))' "$WIZ" \
  || fail "YAML parse failed: $WIZ"
pass "YAML parses cleanly for $PKG and $WIZ"

declare -a ENTITIES=(
  "rc_ota_latest_version"     # sensor
  "rc_ota_update_available"   # binary_sensor
  "rc_ota_last_check"         # sensor (timestamp)
  "rc_ota_rollback_pending"   # binary_sensor
  "rc_ota_channel"            # input_select
  "rc_ota_poll_minutes"       # input_number
  "rc_ota_auto_apply"         # input_boolean
)
for e in "${ENTITIES[@]}"; do
  # unique_id line anchors the declaration to the file.
  if grep -qE "^[[:space:]]*unique_id:[[:space:]]+${e}[[:space:]]*$" "$PKG" \
     || grep -qE "^[[:space:]]+${e}:[[:space:]]*$" "$PKG"; then
    pass "contract entity '${e}' declared in $PKG"
  else
    fail "contract entity '${e}' not declared in $PKG (no unique_id / top-level key match)"
  fi
done

# Contract package must reference the add-on's MQTT base topic.
if ! grep -qE "roamcore/ota/roamcore-ota" "$PKG"; then
  fail "$PKG does not reference the add-on MQTT base topic 'roamcore/ota/roamcore-ota'"
fi
pass "$PKG references add-on MQTT base topic"

# --- 3. Wizard snippet references contract entities ----------------------
echo "== wizard card references =="
# The wizard package must reference all 4 contract sensor entities so the
# Setup Wizard's OTA stage can render a useful card preview without
# breaking when the underlying vendors change.
for e in \
  "rc_ota_latest_version" \
  "rc_ota_update_available" \
  "rc_ota_rollback_pending" \
  "rc_ota_last_check"; do
  if ! grep -qE "${e}" "$WIZ"; then
    fail "$WIZ does not reference contract entity '${e}'"
  fi
  pass "wizard references contract entity '${e}'"
done
# Direct assertion: at least one rc_ota_* sensor unique_id appears in
# the wizard package itself (not just in comments).
if ! grep -qE "^[[:space:]]+unique_id:[[:space:]]+rc_ota_" "$WIZ"; then
  fail "$WIZ does not declare any rc_ota_* contract entities"
fi
pass "$WIZ declares contract entities"

# --- 4. docs/setup/ota.md has required sections --------------------------
echo "== docs/setup/ota.md content =="
for needle in \
  "## 1. Install the add-on" \
  "## 2. Flip the channel" \
  "## 3. Auto-apply" \
  "## 4. Rollback" \
  "## 5. Privacy" \
  "## 6. Troubleshooting"; do
  if ! grep -qF "$needle" "$SETUP_DOC"; then
    fail "docs/setup/ota.md missing required heading: '$needle'"
  fi
done
pass "docs/setup/ota.md has all required sections (install/flip-channel/auto-apply/rollback/privacy/troubleshooting)"

# --- 5. docs/architecture/ota-channel.md has design sections ------------
echo "== docs/architecture/ota-channel.md content =="
for needle in \
  "## Image-id invariant" \
  "## Snapshot semantics" \
  "## Channel → release-tag mapping" \
  "## Rollback policy" \
  "## Failure modes" \
  "## Privacy"; do
  if ! grep -qF "$needle" "$ARCH_DOC"; then
    fail "docs/architecture/ota-channel.md missing required heading: '$needle'"
  fi
done
pass "docs/architecture/ota-channel.md has all design sections"

# --- 6. docs/feature-checklist.md line 71 (OTA updates) ticked ---------
echo "== feature-checklist line 71 (OTA updates) =="
LINE_71="$(sed -n '71p' "$CHECKLIST")"
echo "    line 71: $LINE_71"
if ! grep -qE "OTA updates" <<<"$LINE_71"; then
  fail "feature-checklist.md line 71 is not the OTA updates row: '$LINE_71'"
fi
if ! grep -qE "^\- \[x\] .*OTA updates" <<<"$LINE_71"; then
  fail "feature-checklist.md line 71 is not ticked '[x]': '$LINE_71'"
fi
pass "feature-checklist.md line 71 ticked [x] for OTA updates"

# --- 7. Docker build helper probe (skip-with-log if unavailable) ---------
echo "== docker build probe =="
if command -v docker >/dev/null 2>&1; then
  # We don't actually pull/build the image (would require hassio-addons/build-helper).
  # We only assert the Dockerfile has a valid FROM line.
  if grep -qE "^FROM[[:space:]]+\\\$\{BUILD_FROM\}" "$ADDON/Dockerfile" \
     || grep -qE "^FROM[[:space:]]+[a-zA-Z0-9./:-]+" "$ADDON/Dockerfile"; then
    pass "Dockerfile has a valid FROM instruction"
  else
    fail "Dockerfile has no valid FROM instruction"
  fi
else
  printf '\033[1;33m⊘ SKIP\033[0m — docker not available in PATH; skipping build probe\n'
fi

echo "All OTA updates smoke checks passed."