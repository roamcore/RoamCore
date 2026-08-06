#!/usr/bin/env bash
# Hub restart-stability: smoke check
#
# Wave 9 #120b — Phase 3 Hub restart-stability smoke test rig.
#
# Mirrors the convention in scripts/checks/<name>.sh:
#   - bash strict mode (set -euo pipefail)
#   - repo-local only (no live HA / Proxmox calls)
#   - runs the pytest rig + does a fast YAML pre-check on the canonical
#     manifest so a malformed manifest fails with a clear error before
#     pytest is invoked
#   - plain-English summary at exit 0 / non-zero exit
#
# Usage:
#   bash scripts/checks/hub-restart-stability-smoke.sh
#
# Exit codes:
#   0  the Hub restart-stability rig is GREEN (manifest + every
#      addon config.yaml parse; pytest rig passed; no port collisions;
#      depends_on graph is acyclic; simulated reboot test passed)
#   1  one or more checks failed (see pytest output above for the
#      offending file:line + the manifest pre-check output for any
#      YAML errors)
#
# Wired into scripts/check.sh as a run_if_present step.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

MANIFEST="$ROOT_DIR/scripts/build/hub-services.yml"
PYTEST_TARGET="homeassistant/addons/tests/test_hub_restart_stability.py"

# --- Pre-check: the canonical manifest must parse as YAML ---------------
# If the manifest is broken, fail fast with a clear message instead of
# letting pytest fail with a less helpful traceback.
python3 - "$MANIFEST" <<'PYEOF'
import sys
import yaml

path = sys.argv[1]
try:
    with open(path, encoding="utf-8") as fp:
        data = yaml.safe_load(fp)
except yaml.YAMLError as exc:
    print(f"FAIL: hub-services.yml did not parse as YAML: {exc}", file=sys.stderr)
    sys.exit(1)

if not isinstance(data, dict) or "services" not in data:
    print(f"FAIL: hub-services.yml is missing the top-level 'services:' key", file=sys.stderr)
    sys.exit(1)

if not isinstance(data["services"], list) or not data["services"]:
    print(f"FAIL: hub-services.yml 'services' must be a non-empty list", file=sys.stderr)
    sys.exit(1)

print(f"OK: hub-services.yml parses cleanly ({len(data['services'])} services declared)")
PYEOF

# --- Pre-check: every addon folder has a config.yaml --------------------
# Defends against a future slice accidentally deleting an addon folder
# without updating hub-services.yml. Cheap, repo-local.
MISSING=0
for folder in \
  homeassistant/addons/roamcore-victron-auto \
  homeassistant/addons/roamcore-victron-mock \
  homeassistant/addons/roamcore-traccar-init \
  homeassistant/addons/roamcore-traccar-proxy \
  homeassistant/addons/roamcore-tileserver; do
  if [ ! -f "$folder/config.yaml" ]; then
    echo "FAIL: missing addon config.yaml: $folder/config.yaml" >&2
    MISSING=1
  fi
done
if [ "$MISSING" -ne 0 ]; then
  echo "FAIL: one or more Hub addon config.yaml files are missing" >&2
  exit 1
fi

# --- Run the pytest rig --------------------------------------------------
# Temporarily disable `set -e` so we can capture pytest's exit code
# instead of the script aborting on the first failure. The pytest
# output is still streamed to the operator's terminal.
set +e
python3 -m pytest "$PYTEST_TARGET" --tb=short
PYTEST_EXIT=$?
set -e

if [ "$PYTEST_EXIT" -eq 0 ]; then
  echo "OK: Hub restart-stability rig is GREEN"
  exit 0
fi

# --- Pytest failed — translate to a plain-English summary ----------------
echo "FAIL: Hub restart-stability rig reported one or more failures (see pytest output above)" >&2
exit 1
