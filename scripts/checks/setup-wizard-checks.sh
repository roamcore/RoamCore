#!/usr/bin/env bash
set -euo pipefail

# Convenience wrapper: run all setup-wizard smoke checks.
# Mirrors scripts/checks/victron-checks.sh.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

"$ROOT_DIR/scripts/checks/setup-wizard-stage-aware-smoke.sh"