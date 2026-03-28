#!/usr/bin/env bash
set -euo pipefail

# Convenience wrapper: run all Victron-related drift checks.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

"$ROOT_DIR/scripts/checks/victron-mapping-plan.sh"

echo

"$ROOT_DIR/scripts/checks/victron-rc-contract.sh"
