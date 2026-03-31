#!/usr/bin/env bash
set -euo pipefail

# Back-compat wrapper.
#
# The canonical HAOS installer lives at:
#   https://raw.githubusercontent.com/roamcore/RoamCore/main/homeassistant/install.sh
#
# This wrapper keeps older docs/links working.

set -euo pipefail

if command -v curl >/dev/null 2>&1; then
  curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/homeassistant/install.sh | sh
elif command -v wget >/dev/null 2>&1; then
  wget -qO- https://raw.githubusercontent.com/roamcore/RoamCore/main/homeassistant/install.sh | sh
else
  echo "ERROR: need curl or wget" >&2
  exit 1
fi
