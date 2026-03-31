#!/usr/bin/env bash
set -euo pipefail

HA_BASE_URL="${HA_BASE_URL:-http://homeassistant.local:8123}"
SUMMARY_ENDPOINT="${HA_BASE_URL%/}/api/roamcore/openclaw/summary"
SKILL_ENDPOINT="${HA_BASE_URL%/}/api/roamcore/openclaw/skill"

echo "GET ${SUMMARY_ENDPOINT}"
SUMMARY_JSON="$(curl -fsS "${SUMMARY_ENDPOINT}")"
echo "$SUMMARY_JSON" | python3 -m json.tool >/dev/null

python3 - <<'PY'
import json,sys
o=json.loads(sys.stdin.read())
assert o.get('contract',{}).get('name')=='roamcore_openclaw_summary'
assert o.get('contract',{}).get('version')==1
for k in ('power','map','level','debug'):
  assert k in o
print('OK: summary contract valid')
PY

echo "GET ${SKILL_ENDPOINT}"
SKILL_JSON="$(curl -fsS "${SKILL_ENDPOINT}")"
echo "$SKILL_JSON" | python3 -m json.tool >/dev/null

python3 - <<'PY'
import json,sys
o=json.loads(sys.stdin.read())
assert o.get('contract',{}).get('name')=='roamcore_openclaw_skill'
assert o.get('contract',{}).get('version')==1
rc=o.get('roamcore') or {}
assert 'openclaw_summary_url' in rc
assert 'requires_auth' in rc
sc=rc.get('summary_contract') or {}
assert sc.get('name')=='roamcore_openclaw_summary'
assert sc.get('version')==1
print('OK: skill payload valid')
PY

echo "OK: valid JSON + contract checks passed"
