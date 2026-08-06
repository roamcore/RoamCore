#!/usr/bin/env bash
# Hub-level Support Bundle export wiring: smoke check (Wave 9 #120c)
#
# Mirrors the convention in scripts/checks/<name>.sh:
#   - bash strict mode (set -euo pipefail)
#   - repo-local only (no live HA / Proxmox calls)
#   - pytest wrapper with exit-code propagation
#   - YAML pre-check (file exists + parses cleanly)
#   - rc-naming check (every entity id matches the rc_support_bundle_hub_ prefix)
#   - plain-English summary at exit 0 / non-zero exit
#
# Usage:
#   bash scripts/checks/support-bundle-hub-smoke.sh
#
# Exit codes:
#   0  Hub support-bundle package exists, parses, and passes all 11 pytest assertions
#   1  package file missing
#   1  package fails to parse as YAML
#   1  one or more entity ids violate rc_support_bundle_hub_ naming
#   1  pytest failed for some other reason
#
# Wired into scripts/check.sh as a `run_if_present` step.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

HUB_PACKAGE="homeassistant/packages/roamcore_support_bundle_hub.yaml"

# --- YAML pre-check: file exists + parses cleanly ---
if [ ! -f "$HUB_PACKAGE" ]; then
  echo "FAIL: missing Hub support-bundle package at $HUB_PACKAGE"
  echo "      Wave 9 #120c requires this file to exist for the Hub-level"
  echo "      one-tap 'Send support bundle' button wiring."
  exit 1
fi

# Use Python + PyYAML (already a pytest dependency, so it's available)
# to do a quick parse + rc-naming check before running the full pytest.
python3 - <<'PYEOF'
import sys, yaml

PATH = "homeassistant/packages/roamcore_support_bundle_hub.yaml"
try:
    with open(PATH, encoding="utf-8") as fp:
        data = yaml.safe_load(fp)
except yaml.YAMLError as e:
    print(f"FAIL: {PATH} does not parse as YAML: {e}")
    sys.exit(1)

if not isinstance(data, dict):
    print(f"FAIL: {PATH} must parse to a mapping; got {type(data).__name__}")
    sys.exit(1)

bad: list[str] = []

# Every rc-named entity id in the Hub package must start with the
# Hub-level prefix `rc_support_bundle_hub_`. The recipe-level contract
# (`connections/support-bundle/connection.yml`) uses the legacy
# `rc_support_bundle_` prefix — that surface lives in a different YAML
# and is not in scope here.
for bid in (data.get("input_button") or {}).keys():
    if not bid.startswith("rc_support_bundle_hub_"):
        bad.append(f"input_button.{bid}")
for tid in (data.get("input_text") or {}).keys():
    if not tid.startswith("rc_support_bundle_hub_"):
        bad.append(f"input_text.{tid}")
for sid in (data.get("input_select") or {}).keys():
    if not sid.startswith("rc_support_bundle_hub_"):
        bad.append(f"input_select.{sid}")
for block in (data.get("template") or []):
    if not isinstance(block, dict):
        continue
    for sensor in (block.get("sensor") or []):
        if not isinstance(sensor, dict):
            continue
        uid = sensor.get("unique_id") or ""
        if not uid.startswith("rc_support_bundle_hub_"):
            bad.append(f"sensor.unique_id={uid}")
for auto in (data.get("automation") or []):
    if not isinstance(auto, dict):
        continue
    aid = auto.get("id") or ""
    if not aid.startswith("rc_support_bundle_hub_"):
        bad.append(f"automation.id={aid}")

if bad:
    print("FAIL: rc-entity-naming violations in Hub support-bundle package:")
    for b in bad:
        print(f"      - {b}")
    print("      Every entity id must start with rc_support_bundle_hub_")
    print("      (see docs/reference/rc-entity-naming.md).")
    sys.exit(1)

print(f"OK: {PATH} parses cleanly and every entity id is rc_support_bundle_hub_-prefixed")
PYEOF

PARSER_EXIT=$?
if [ "$PARSER_EXIT" -ne 0 ]; then
  exit "$PARSER_EXIT"
fi

# --- Run the pytest (the source of truth for the data-layer checks) ---
# Use --tb=short so the failure output is bounded; the test file
# prints clear messages for the offending entity on failure.
set +e
python3 -m pytest homeassistant/packages/tests/test_support_bundle_hub.py --tb=short
PYTEST_EXIT=$?
set -e

if [ "$PYTEST_EXIT" -eq 0 ]; then
  echo "OK: Hub support-bundle export wiring — all 11 pytest assertions pass"
  exit 0
fi

echo "FAIL: Hub support-bundle export wiring — see pytest output above"
exit 1
