#!/usr/bin/env bash
set -euo pipefail

# RoamCore HA-only beta smoke checks (repo-local)
# This script validates that the repository contains the expected assets
# for a HA-only install. It does NOT touch a running Home Assistant.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() { echo "ERROR: $*" >&2; exit 1; }

# --- Required directories ---
[ -d homeassistant ] || fail "missing homeassistant/"
[ -d homeassistant/packages ] || fail "missing homeassistant/packages/"
[ -d homeassistant/www ] || fail "missing homeassistant/www/"

# --- Core HA packages (contract layer) ---
req_pkgs=(
  "homeassistant/packages/roamcore_power.yaml"
  "homeassistant/packages/roamcore_victron_health.yaml"
)
for f in "${req_pkgs[@]}"; do
  [ -f "$f" ] || fail "missing $f"
  python3 -c 'import sys,yaml; yaml.safe_load(open(sys.argv[1],"r",encoding="utf-8"))' "$f" \
    || fail "YAML parse failed: $f"
done

echo "OK: required HA packages present + parseable"

# --- Map assets (best-effort: some files may be generated later) ---
# We at least require the RoamCore JS bundle that wires MapLibre.
MAP_JS="homeassistant/www/roamcore/roamcore-pages.js"
[ -f "$MAP_JS" ] || fail "missing $MAP_JS"

echo "OK: map JS bundle present"

# --- Trip wrapped assets (HTML template should exist) ---
TW_HTML_MIN="homeassistant/www/roamcore/trip_wrapped/trip_wrapped.min.html"
if [ -f "$TW_HTML_MIN" ]; then
  echo "OK: trip wrapped HTML present"
else
  echo "WARN: trip wrapped HTML not found at $TW_HTML_MIN (may be generated/deployed separately)" >&2
fi

# --- Victron add-on source should still compile ---
VIC_MAIN="homeassistant/addons/roamcore-victron-auto/src/main.py"
[ -f "$VIC_MAIN" ] || fail "missing $VIC_MAIN"
python3 -m py_compile "$VIC_MAIN" || fail "python compile failed: $VIC_MAIN"
echo "OK: victron auto add-on compiles"

echo "All HA-only beta smoke checks passed."
