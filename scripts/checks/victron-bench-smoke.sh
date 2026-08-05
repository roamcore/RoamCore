#!/usr/bin/env bash
# RoamCore Victron bench integration tests smoke check.
#
# Runs the pytest suite under homeassistant/addons/roamcore-victron-auto/tests/
# to verify end-to-end that the Victron Auto add-on publishes the right
# Home Assistant MQTT Discovery entities for every mapped vt_* key, that
# values propagate to retained state topics, that the addon recovers after a
# broker disconnect, and that errors are surfaced in plain English.
#
# This is the tier-a-is-honest evidence for the Victron integration
# (Bernard, 2026-08-04). Skip is allowed when paho-mqtt + amqtt are not
# available (CI hosts may lack them), but the script never silently passes.
#
# Exit codes:
#   0  all tests pass (or skipped with a clear SKIP message)
#   1  any test failed
#   2  deps missing in a way that prevents running the suite

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEST_DIR="$ROOT_DIR/homeassistant/addons/roamcore-victron-auto/tests"

if [[ ! -d "$TEST_DIR" ]]; then
  echo "ERROR: bench tests dir missing: $TEST_DIR" >&2
  exit 2
fi

# Use the repo .venv if present (preferred); otherwise fall back to python3.
PYTHON_BIN="$ROOT_DIR/.venv/bin/python3"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3 || true)"
fi
if [[ -z "${PYTHON_BIN:-}" ]]; then
  echo "SKIP — python3 not found on PATH"
  exit 0
fi

echo "== Victron bench: smoke check =="
echo "Bench dir:  $TEST_DIR"
echo "Python:     $PYTHON_BIN"

# Verify the bench can be collected (imports parse, fixtures load) even if
# the runtime deps are missing. This catches "bench file is broken" without
# requiring paho-mqtt on every dev host.
if ! "$PYTHON_BIN" -c "import ast, pathlib; ast.parse(pathlib.Path('$TEST_DIR/test_victron_auto_bench.py').read_text()); ast.parse(pathlib.Path('$TEST_DIR/conftest.py').read_text())" 2>/dev/null; then
  echo "FAIL: bench source files do not parse" >&2
  exit 1
fi

# Check for runtime deps; SKIP with a clear message if they're missing.
# We require: pytest (test runner), pytest-asyncio (async tests),
# paho-mqtt (client), and ONE of: mosquitto (binary) or amqtt (Python broker).
missing=()
"$PYTHON_BIN" -c "import pytest" 2>/dev/null || missing+=("pytest")
"$PYTHON_BIN" -c "import pytest_asyncio" 2>/dev/null || missing+=("pytest-asyncio")
"$PYTHON_BIN" -c "import paho.mqtt" 2>/dev/null || missing+=("paho-mqtt")

broker_available=0
if command -v mosquitto >/dev/null 2>&1; then
  broker_available=1
elif "$PYTHON_BIN" -c "import amqtt" 2>/dev/null; then
  broker_available=1
fi

if [[ ${#missing[@]} -gt 0 || $broker_available -eq 0 ]]; then
  echo
  echo "SKIP — install paho-mqtt to run"
  echo "  missing: ${missing[*]:-(none)}"
  if [[ $broker_available -eq 0 ]]; then
    echo "  broker:  none (install mosquitto OR pip install amqtt)"
  fi
  echo
  echo "  pip install paho-mqtt pytest pytest-asyncio amqtt"
  echo
  echo "  See $TEST_DIR/README.md for the full setup."
  # Per the spec: "bench tests SKIP gracefully on hosts without paho-mqtt;
  # the smoke script detects this and exits 0 with a clear SKIP message."
  exit 0
fi

echo "Deps:       OK (paho-mqtt + amqtt)"
echo

# Run pytest. Capture exit code separately so we can render a useful message.
# We cd into the addon dir (one level above tests/) so pytest picks up the
# pytest.ini in tests/ AND finds the src/ package on the implicit cwd path.
set +e
cd "$TEST_DIR/.."
"$PYTHON_BIN" -m pytest tests/ -v --tb=short
rc=$?
set -e

cd "$ROOT_DIR"

if [[ $rc -ne 0 ]]; then
  echo
  echo "FAIL: victron bench tests failed (exit $rc)" >&2
  echo "See $TEST_DIR/README.md for troubleshooting." >&2
  exit 1
fi

echo
echo "OK: victron bench integration tests passed."
