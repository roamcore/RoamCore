#!/usr/bin/env bash
# Wave 9 #114 — Power mock-kill guard.
#
# The previous homeassistant/packages/roamcore_power.yaml silently fell back to
# input_number.<legacy-mock-prefix>.* when no real Victron source was present,
# which gave the user a plausible-but-fake tile on broken installs. Bernard's
# directive (chat #7562-7580, priority 1) was "power to be foolproof and work
# reliably" — a tile that fakes success is worse than a tile that says
# "unavailable" + directs the user to Setup.
#
# This smoke check fails CI if any literal legacy-mock-prefix reference sneaks
# back into the power package. Dav Mocks still live in
# homeassistant/packages/roamcore_dev_mocks.yaml for non-power demos; this
# guard only enforces the consumer (the power package) keeps using real
# sources — vt_* (RoamCore Victron Auto add-on) or the legacy victron_*
# integration — and surfaces "unavailable" otherwise.
#
# The matching binary_sensor.rc_power_no_real_source banner drives the
# dashboard "Power not connected — go to Setup" card.

set -euo pipefail

FILE=homeassistant/packages/roamcore_power.yaml

if [ ! -f "$FILE" ]; then
  echo "FAIL: $FILE not found at repo root."
  exit 1
fi

# Fail on any legacy-mock-prefix reference (entity-id or input_number/input_select/input_boolean
# prefix). The dev-mocks package is intentionally NOT scanned here — those
# helpers are still useful for non-power demos; this guard only enforces the
# power package's break from them.
if grep -q "rc_mock_power" "$FILE"; then
  echo "FAIL: $FILE still references rc_mock_power fallback chain."
  grep -n "rc_mock_power" "$FILE" || true
  exit 1
fi

if grep -q "input_number.rc_mock" "$FILE"; then
  echo "FAIL: $FILE still references input_number.rc_mock fallback."
  grep -n "input_number.rc_mock" "$FILE" || true
  exit 1
fi

if grep -q "input_select.rc_mock" "$FILE"; then
  echo "FAIL: $FILE still references input_select.rc_mock fallback."
  grep -n "input_select.rc_mock" "$FILE" || true
  exit 1
fi

if grep -q "input_boolean.rc_mock" "$FILE"; then
  echo "FAIL: $FILE still references input_boolean.rc_mock fallback."
  grep -n "input_boolean.rc_mock" "$FILE" || true
  exit 1
fi

echo "PASS: no rc_mock fallback references in $FILE"
