#!/usr/bin/env bash
# Connection state field: smoke check
#
# Wave 9 #117 — Repo hygiene: add state field to every connection.yml.
#
# Mirrors the convention in scripts/checks/<name>.sh:
#   - bash strict mode (set -euo pipefail)
#   - repo-local only (no live HA / Proxmox calls)
#   - wrapper around the cross-cutting pytest that guards the data
#     layer (every connection.yml carries a valid `state:` value)
#   - plain-English summary at exit 0 / non-zero exit
#
# Usage:
#   bash scripts/checks/connection-state-smoke.sh
#
# Exit codes:
#   0  all 32 connection manifests carry a valid `state:` value
#   1  one or more manifests are missing the `state:` field (FAIL)
#   1  one or more manifests carry a value outside the 10-state allowlist (FAIL)
#   1  pytest failed for some other reason (FAIL)
#
# Wired into scripts/check.sh as a `run_if_present` step.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

# --- Run the pytest (the source of truth for the data-layer checks) ---
# We use --tb=short so the failure output is bounded; the
# connection-state-field test prints a clear diff for the offending
# manifest(s) on failure.
#
# Temporarily disable `set -e` so we can capture pytest's exit code
# instead of the script aborting on the first failure. The pytest
# output is still streamed to the operator's terminal.
set +e
python3 -m pytest homeassistant/packages/tests/test_connection_state_field.py --tb=short
PYTEST_EXIT=$?
set -e

if [ "$PYTEST_EXIT" -eq 0 ]; then
  echo "OK: all 32 connections have a valid state"
  exit 0
fi

# --- Pytest failed — translate the failure into a plain-English summary ---
# The pytest output already names the offending manifest(s), but
# operators at the terminal want a short, plain-English line that names
# the count + the top reason. We re-derive the failure categories from
# the manifest files (cheap, repo-local) so the summary is accurate
# even if pytest's exact failure message drifts across versions.

STANDARD_STATES=(
  "Available"
  "Detected"
  "Ready to connect"
  "Connecting"
  "Connected"
  "Needs information"
  "Needs attention"
  "Unsupported"
  "Offline"
  "Update available"
)

# Use Python to parse the YAML quickly (PyYAML is already a pytest
# dependency, so it's available) and bucket the failure categories.
python3 - <<PYEOF
import os, sys, yaml, glob

STANDARD_STATES = {
    "Available",
    "Detected",
    "Ready to connect",
    "Connecting",
    "Connected",
    "Needs information",
    "Needs attention",
    "Unsupported",
    "Offline",
    "Update available",
}

missing = []
unknown = []
for path in sorted(glob.glob("connections/*/connection.yml")):
    if not os.path.isfile(path):
        continue
    with open(path, encoding="utf-8") as fp:
        data = yaml.safe_load(fp)
    state = data.get("state") if isinstance(data, dict) else None
    if not isinstance(state, str) or not state.strip():
        missing.append(path)
        continue
    if state not in STANDARD_STATES:
        unknown.append((path, state))

if missing:
    short = missing[:8]
    more = "..." if len(missing) > 8 else ""
    print(f"FAIL: {len(missing)} manifests missing 'state:' field: {short}{more}")
if unknown:
    values = sorted({v for _, v in unknown})
    print(f"FAIL: {len(unknown)} manifests have an unknown state: {values}")
if not missing and not unknown:
    # pytest failed for some other reason (e.g. import error, fixture
    # failure) — surface the bucket-free summary so the operator
    # knows to look at the pytest output above.
    print("FAIL: pytest failed; see output above for the offending manifest(s)")
PYEOF

exit 1
