#!/usr/bin/env bash
set -euo pipefail

HA_BASE_URL="${HA_BASE_URL:-http://homeassistant.local:8123}"
ENDPOINT="${HA_BASE_URL%/}/api/roamcore/openclaw/summary"

echo "GET ${ENDPOINT}"
curl -fsS "${ENDPOINT}" | python3 -m json.tool > /dev/null
echo "OK: valid JSON"

