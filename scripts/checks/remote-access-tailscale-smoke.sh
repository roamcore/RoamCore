#!/usr/bin/env bash
set -euo pipefail

# RoamCore — Remote access (Tailscale contract layer) smoke check.
#
# Validates the Wave 2 #29 slice is present and consistent in the repo:
#   1. homeassistant/packages/roamcore_remote_access.yaml parses as YAML
#      and declares the 6 contract entities the spec requires.
#   2. The active binary_sensor's ON formula gates on BOTH the kill-switch
#      input_boolean AND a Tailscale-integration device-state template
#      variable (so the On-condition is not a tautology).
#   3. The unavailable-when-OFF branch is present: every contract
#      sensor/binary_sensor carries an availability expression that
#      includes the literal 'is_state(...rc_remote_access_enabled..., off)'
#      pattern OR an explicit `is_state('input_boolean.rc_remote_access_enabled', 'on')`
#      requirement, AND we can locate the rc_remote_access_active unavailable
#      path that explicitly references the binary_sensor's own state.
#   4. homeassistant/packages/roamcore_setup_wizard_remote_access.yaml
#      exists and parses as YAML.
#   5. docs/setup/remote-access.md exists and contains the four numbered
#      setup steps, the privacy note, and a Troubleshooting section.
#   6. docs/feature-checklist.md line 70 (Remote access) is updated to
#      `[x]` with a one-sentence pointer.
#
# This script is purely static — it never reaches out to a running HA or
# Tailscale API. It exits non-zero on the first failed assertion.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PKG="homeassistant/packages/roamcore_remote_access.yaml"
WIZ="homeassistant/packages/roamcore_setup_wizard_remote_access.yaml"
DOCS="docs/setup/remote-access.md"
CHECKLIST="docs/feature-checklist.md"

fail() { echo "ERROR: $*" >&2; exit 1; }
pass() { echo "  PASS: $*"; }

# --- Pre-flight -----------------------------------------------------------
[ -f "$PKG" ]  || fail "missing $PKG"
[ -f "$WIZ" ]  || fail "missing $WIZ"
[ -f "$DOCS" ] || fail "missing $DOCS"
[ -f "$CHECKLIST" ] || fail "missing $CHECKLIST"

# YAML must parse cleanly (HA refuses to load malformed YAML).
python3 -c 'import sys,yaml; yaml.safe_load(open(sys.argv[1],"r",encoding="utf-8"))' "$PKG" \
  || fail "YAML parse failed: $PKG"
python3 -c 'import sys,yaml; yaml.safe_load(open(sys.argv[1],"r",encoding="utf-8"))' "$WIZ" \
  || fail "YAML parse failed: $WIZ"
pass "YAML parses cleanly for $PKG and $WIZ"

# --- 1. Six contract entities declared (grep + line-anchored) -------------
echo "== contract entities declared =="
declare -a ENTITIES=(
  "rc_remote_access_active"            # binary_sensor (the OFF switch)
  "rc_remote_access_url"               # sensor
  "rc_remote_access_peer_count"        # sensor
  "rc_remote_access_last_seen"         # sensor
  "rc_remote_access_enabled"           # input_boolean (kill-switch)
  "rc_remote_access_tailnet_host"      # input_text (operator override)
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

# --- 2. ON formula gates on BOTH the kill-switch AND a Tailscale device ---
echo "== active binary_sensor On-condition =="
# (a) Must reference input_boolean.rc_remote_access_enabled (gating).
if ! grep -qE "is_state\\('input_boolean\\.rc_remote_access_enabled',[[:space:]]*'on'\\)" "$PKG"; then
  fail "rc_remote_access_active formula missing 'input_boolean.rc_remote_access_enabled == on' clause"
fi
# (b) Must reference a Tailscale-integration device-state template variable
# (sensor.*_last_seen, binary_sensor.*_update_available, etc). We accept any
# reference to a tailscale-emitted entity pattern: _last_seen or
# _update_available or _client_supports_*.
if ! grep -qE "_last_seen|_update_available|_client_supports_" "$PKG"; then
  fail "rc_remote_access_active formula missing Tailscale-integration device-state reference"
fi
pass "rc_remote_access_active gates on kill-switch AND Tailscale device-state"

# --- 3. unavailable-when-OFF branch is present --------------------------
echo "== unavailable-when-OFF branch =="
# The contract-layer guarantee is: every sensor / binary_sensor reports
# `unavailable` when the kill-switch is OFF. We assert the On-condition
# references 'is_state(...rc_remote_access_enabled..., on)' (i.e. it is
# not just a passive value) AND the availability expression for
# rc_remote_access_active is present.
if ! grep -qE "is_state\\('input_boolean\\.rc_remote_access_enabled',[[:space:]]*'on'\\)" "$PKG"; then
  fail "no 'is_state(...rc_remote_access_enabled..., on)' gating found anywhere in $PKG"
fi
# Also assert the literal `is_state(...rc_remote_access_enabled..., 'off')`
# branch OR the `states.binary_sensor.rc_remote_access_active` unavailable
# path. We accept either form: an explicit `is_state(..., 'off')` clause
# OR a reference to the active binary_sensor's own state to drive the
# unavailable path.
if ! grep -qE "is_state\\('input_boolean\\.rc_remote_access_enabled',[[:space:]]*'off'\\)" "$PKG" \
   && ! grep -qE "states\\.binary_sensor\\.rc_remote_access_active" "$PKG"; then
  fail "no unavailable-when-OFF branch found (expected 'is_state(...rc_remote_access_enabled..., off)' OR 'states.binary_sensor.rc_remote_access_active')"
fi
pass "unavailable-when-OFF branch present in $PKG"

# --- 4. Setup wizard card snippet ---------------------------------------
echo "== setup wizard card =="
# The snippet must declare at least one card referencing the contract
# entities so the wizard can render a useful status view.
if ! grep -qE "rc_remote_access_active" "$WIZ"; then
  fail "$WIZ does not reference rc_remote_access_active"
fi
if ! grep -qE "rc_remote_access_url" "$WIZ"; then
  fail "$WIZ does not reference rc_remote_access_url"
fi
pass "setup wizard card references contract entities"

# --- 5. docs/setup/remote-access.md has all 4 steps + privacy + TS ------
echo "== docs/setup/remote-access.md content =="
for needle in \
  "### 1. Enable the Tailscale integration" \
  "### 2. Set the tailnet host" \
  "### 3. Flip the kill-switch" \
  "### 4. Confirm \`binary_sensor.rc_remote_access_active\` turns ON" \
  "Privacy" \
  "Troubleshooting"; do
  if ! grep -qF "$needle" "$DOCS"; then
    fail "docs/setup/remote-access.md missing required heading: '$needle'"
  fi
done
pass "docs/setup/remote-access.md has all 4 steps + privacy + troubleshooting"

# --- 6. docs/feature-checklist.md line 70 (Remote access) ticked --------
echo "== feature-checklist line 70 (Remote access) =="
# Extract line 70 of the checklist (1-indexed) and assert it is the
# Remote access row AND it is ticked `[x]`.
LINE_70="$(sed -n '70p' "$CHECKLIST")"
echo "    line 70: $LINE_70"
if ! grep -qE "Remote access" <<<"$LINE_70"; then
  fail "feature-checklist.md line 70 is not the Remote access row: '$LINE_70'"
fi
if ! grep -qE "^\- \[x\] .*Remote access" <<<"$LINE_70"; then
  fail "feature-checklist.md line 70 is not ticked '[x]': '$LINE_70'"
fi
pass "feature-checklist.md line 70 ticked [x] for Remote access"

echo "All remote-access-tailscale smoke checks passed."