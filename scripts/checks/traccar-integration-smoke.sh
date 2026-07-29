#!/usr/bin/env bash
set -euo pipefail

# Wave 2 #17 \u2014 Traccar install + integration smoke check.
#
# Static, regex-driven checks proving that the slice landed coherently:
#   1. The location package declares input_text.rc_location_tracker_entity
#      with a sensible (non-blank) default.
#   2. The location package ships an automation that auto-fills
#      input_text.rc_location_tracker_entity on homeassistant_started
#      and on every new device_tracker.traccar_* entity registration.
#   3. scripts/install/ha/install.sh exposes the traccar integration setup
#      function/flag (--with-traccar).
#   4. homeassistant/configuration_addon.yaml includes the commented-out
#      device_tracker -> traccar YAML pre-stage block.
#   5. docs/setup/traccar.md has the "Step 1: Configure the Home
#      Assistant Traccar integration" section.
#
# All assertions are regex / line-based; no build step, fail-softly.
# Exit 0 on success, non-zero on the first failing assertion.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PKG_FILE="$ROOT_DIR/homeassistant/packages/roamcore_location.yaml"
INSTALL_SH="$ROOT_DIR/scripts/install/ha/install.sh"
ADDON_FILE="$ROOT_DIR/homeassistant/configuration_addon.yaml"
DOC_FILE="$ROOT_DIR/docs/setup/traccar.md"

fail() {
    echo "FAIL: $*" >&2
    exit 1
}
have() {
    [[ -f "$1" ]] || fail "missing file: $1"
}

have "$PKG_FILE"
have "$INSTALL_SH"
have "$ADDON_FILE"
have "$DOC_FILE"

echo "== Traccar install + integration smoke =="
echo "Package:  $PKG_FILE"
echo "Install:  $INSTALL_SH"
echo "Add-on:   $ADDON_FILE"
echo "Docs:     $DOC_FILE"
echo

# --- 1. input_text.rc_location_tracker_entity with a default ------------
if ! grep -Eq '^[[:space:]]*rc_location_tracker_entity:' "$PKG_FILE"; then
    fail "no rc_location_tracker_entity declaration in $PKG_FILE"
fi
echo "OK: input_text.rc_location_tracker_entity declared"

# The bootstrap initial must NOT be blank (the auto-fill needs a seed
# hint that the user's eventual device is probably `device_tracker.traccar_van`).
if grep -Eq '^[[:space:]]*initial:[[:space:]]*"?"[[:space:]]*"?[[:space:]]*$' "$PKG_FILE" \
   || ! grep -Eq '^[[:space:]]*initial:[[:space:]]*"[^"]*"' "$PKG_FILE"; then
    fail "rc_location_tracker_entity has a missing or blank 'initial:' (the auto-fill needs a non-blank seed)"
fi
if ! grep -q 'device_tracker.traccar_van' "$PKG_FILE"; then
    fail "rc_location_tracker_entity initial default is not device_tracker.traccar_van (gives first-install users a sane seed)"
fi
echo "OK: input_text.rc_location_tracker_entity has a non-blank bootstrap default (device_tracker.traccar_van)"

# --- 2. Auto-fill automation present and well-shaped --------------------
if ! grep -Eq '^[[:space:]]*-[[:space:]]*id:[[:space:]]*rc_location_autofill_tracker_entity' "$PKG_FILE"; then
    fail "missing automation id rc_location_autofill_tracker_entity in $PKG_FILE"
fi
echo "OK: automation.rc_location_autofill_tracker_entity declared"

if ! grep -Eq 'event:[[:space:]]*start' "$PKG_FILE"; then
    fail "auto-fill automation does not listen on homeassistant_started (event: start)"
fi
echo "OK: auto-fill automation triggers on homeassistant_started"

if ! grep -Eq 'entity_registry_updated' "$PKG_FILE"; then
    fail "auto-fill automation does not listen on entity_registry_updated (needed for mid-session additions)"
fi
echo "OK: auto-fill automation also triggers on entity_registry_updated"

if ! grep -Eq 'device_tracker\.traccar_' "$PKG_FILE"; then
    fail "auto-fill automation does not regex-match device_tracker.traccar_*"
fi
echo "OK: auto-fill automation matches device_tracker.traccar_*"

if ! grep -Eq 'input_text\.set_value' "$PKG_FILE"; then
    fail "auto-fill automation does not call input_text.set_value"
fi
if ! grep -Eq 'input_text\.rc_location_tracker_entity' "$PKG_FILE"; then
    fail "auto-fill automation does not target input_text.rc_location_tracker_entity"
fi
echo "OK: auto-fill automation writes back to input_text.rc_location_tracker_entity"

# --- 3. install.sh references the traccar integration setup -------------
if ! grep -Eq -- '--with-traccar' "$INSTALL_SH"; then
    fail "--with-traccar flag missing from $INSTALL_SH"
fi
echo "OK: install.sh exposes --with-traccar"

if ! grep -Eq 'install_traccar_integration|Traccar Server' "$INSTALL_SH"; then
    fail "install.sh has no Traccar Server integration setup reference"
fi
echo "OK: install.sh references the Traccar Server integration setup"

# --- 4. configuration_addon.yaml has the commented YAML pre-stage -------
if ! grep -Eq '^[[:space:]]*#.*device_tracker:' "$ADDON_FILE"; then
    fail "configuration_addon.yaml is missing the commented device_tracker: block"
fi
echo "OK: configuration_addon.yaml includes a commented device_tracker: pre-stage"

if ! grep -Eq '^[[:space:]]*#.*platform:[[:space:]]*traccar' "$ADDON_FILE"; then
    fail "commented device_tracker block is missing 'platform: traccar' line"
fi
echo "OK: commented device_tracker block includes 'platform: traccar'"

# Default-OFF invariant: the block must remain commented out so RoamCore
# stays HACS-first / UI-first per GOLDEN.md.
if grep -Eq '^[[:space:]]*platform:[[:space:]]*traccar' "$ADDON_FILE"; then
    fail "traccar device_tracker block is uncommented in configuration_addon.yaml (RoamCore ships HACS-first / UI-first by default)"
fi
echo "OK: traccar block stays commented (HACS-first / UI-first default preserved)"

# --- 5. docs/setup/traccar.md has Step 1 -------------------------------
DOC_CONTENT="$(cat "$DOC_FILE")"
if ! grep -q 'Step 1: Configure the Home Assistant Traccar integration' <<<"$DOC_CONTENT"; then
    fail "docs/setup/traccar.md is missing the 'Step 1: Configure the Home Assistant Traccar integration' section"
fi
echo "OK: docs/setup/traccar.md has 'Step 1: Configure the Home Assistant Traccar integration' section"

# The doc must mention both:
#  - the auto-fill automation (so users know Path A is hands-off), and
#  - the manual input_text.set_value path (Path B).
if ! grep -q 'rc_location_autofill_tracker_entity' <<<"$DOC_CONTENT"; then
    fail "docs/setup/traccar.md does not mention the auto-fill automation (rc_location_autofill_tracker_entity)"
fi
echo "OK: docs/setup/traccar.md references the auto-fill automation"
if ! grep -q 'input_text.set_value' <<<"$DOC_CONTENT"; then
    fail "docs/setup/traccar.md does not document the manual input_text.set_value path"
fi
echo "OK: docs/setup/traccar.md documents the manual input_text.set_value path"

# The doc must mention the traccar_server domain (built-in, not HACS).
if ! grep -q 'traccar_server' <<<"$DOC_CONTENT"; then
    fail "docs/setup/traccar.md does not mention the traccar_server domain (HA core integration, not HACS)"
fi
echo "OK: docs/setup/traccar.md mentions traccar_server (HA core, not HACS)"

echo
echo "All traccar-integration smoke checks passed."
