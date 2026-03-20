#!/usr/bin/env bash
set -euo pipefail

# Minimal helper to verify that the RoamCore HA template packages are loaded
# and rc_* entities exist.
#
# Usage:
#   scripts/ha/check-rc-entities.sh
#   HA_URL=http://homeassistant.local:8123 scripts/ha/check-rc-entities.sh
#   HA_TOKEN_PATH=~/.clawdbot/secrets/homeassistant.token scripts/ha/check-rc-entities.sh

HA_URL="${HA_URL:-http://192.168.1.66:8123}"
HA_TOKEN_PATH="${HA_TOKEN_PATH:-$HOME/.clawdbot/secrets/homeassistant.token}"

if [[ ! -f "$HA_TOKEN_PATH" ]]; then
  echo "ERROR: HA token file not found at: $HA_TOKEN_PATH" >&2
  exit 1
fi

TOKEN="$(cat "$HA_TOKEN_PATH")"

echo "HA_URL=$HA_URL"

want=(
  "binary_sensor.rc_system_power_backend_connected"
  "sensor.rc_system_power_backend_status"
  "sensor.rc_system_power_backend_snapshot_state"
  "sensor.rc_system_power_backend_devices"
  "sensor.rc_system_power_backend_topics"
)

for ent in "${want[@]}"; do
  echo
  echo "--- $ent"
  if ! out="$(curl -fsS \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    "$HA_URL/api/states/$ent" 2>/dev/null)"; then
    echo "NOT FOUND (404): $ent"
    missing=1
    continue
  fi
  printf '%s' "$out" \
    | python3 -c 'import json,sys; s=json.load(sys.stdin); print(json.dumps({"state": s.get("state"), "attributes": s.get("attributes", {})}, indent=2, sort_keys=True))'
done

echo
if [[ "${missing:-0}" == "1" ]]; then
  echo "WARN: one or more rc_* entities were not found. Likely the Victron health package isn't loaded/deployed to HA (/config/packages/*) or entity ids differ."
  exit 2
fi

echo "OK: rc_* entity probe completed."
