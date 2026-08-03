#!/usr/bin/env bash
# Smoketest for the RoamCore WiCAN Pro time-series HTTP views.
#
# Verifies that the /api/roamcore/wican/timeseries/* endpoints respond
# correctly when the integration has been set up + has at least one
# reading in the SQLite store.
#
# Usage: bash homeassistant/tools/wican_smoketest.sh [HA_URL] [TOKEN]
#   HA_URL defaults to http://localhost:8123
#   TOKEN defaults to $HA_TOKEN env var

set -euo pipefail

HA_URL="${1:-${HA_URL:-http://localhost:8123}}"
TOKEN="${2:-${HA_TOKEN:-}}"

if [[ -z "$TOKEN" ]]; then
    echo "ERROR: HA_TOKEN env var or second argument required" >&2
    exit 1
fi

echo "== smoketest: wican pro time-series HTTP views =="
echo "HA_URL=$HA_URL"

# 1. Catalog
echo
echo "-- /api/roamcore/wican/timeseries/catalog"
CATALOG=$(curl -fsSL -H "Authorization: Bearer $TOKEN" "$HA_URL/api/roamcore/wican/timeseries/catalog")
PID_COUNT=$(echo "$CATALOG" | python3 -c "import json, sys; print(len(json.load(sys.stdin)['pids']))")
echo "OK: catalog returned $PID_COUNT PID entries"
if [[ "$PID_COUNT" -lt 17 ]]; then
    echo "FAIL: catalog has fewer than 17 PIDs (expected generic Mode-01 coverage)" >&2
    exit 1
fi

# 2. Stats
echo
echo "-- /api/roamcore/wican/timeseries/stats"
STATS=$(curl -fsSL -H "Authorization: Bearer $TOKEN" "$HA_URL/api/roamcore/wican/timeseries/stats")
DEVICES=$(echo "$STATS" | python3 -c "import json, sys; print(len(json.load(sys.stdin)['devices']))")
echo "OK: stats returned $DEVICES device(s)"

# 3. Query PID 0x0C (RPM) — should always be present if the WiCAN is connected
echo
echo "-- /api/roamcore/wican/timeseries?pid=12"
QUERY=$(curl -fsSL -H "Authorization: Bearer $TOKEN" "$HA_URL/api/roamcore/wican/timeseries?pid=12&limit=10")
echo "OK: RPM query responded with $(echo "$QUERY" | python3 -c "import json, sys; print(json.load(sys.stdin)['count'])") readings"

# 4. Bad PID
echo
echo "-- /api/roamcore/wican/timeseries?pid=99999 (should 400)"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$HA_URL/api/roamcore/wican/timeseries?pid=99999")
if [[ "$HTTP_CODE" != "400" ]]; then
    echo "FAIL: bad PID returned $HTTP_CODE (expected 400)" >&2
    exit 1
fi
echo "OK: bad PID correctly returned 400"

# 5. Missing PID
echo
echo "-- /api/roamcore/wican/timeseries (no pid param, should 400)"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$HA_URL/api/roamcore/wican/timeseries")
if [[ "$HTTP_CODE" != "400" ]]; then
    echo "FAIL: missing pid returned $HTTP_CODE (expected 400)" >&2
    exit 1
fi
echo "OK: missing pid correctly returned 400"

echo
echo "ALL CHECKS PASSED"
