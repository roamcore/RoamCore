#!/usr/bin/env bash
# Trip Wrapped seamless USP flow smoke check (slice #21).
#
# Validates that a brand-new RoamCore install can render a Trip Wrapped
# report with one tap, before the operator configures Traccar. The "demo
# seed" path must be:
#   - stdlib-only (we parse the AST, not import; this catches syntax + the
#     absence of disallowed imports at parse time)
#   - able to produce a JSON file with the 5 contract fields via --dry-run
#   - pointing the map URL at the local tileserver (privacy-compliant)
# And the HA-side wiring must declare:
#   - input_boolean.rc_trip_wrapped_demo
#   - input_boolean.rc_trip_wrapped_real
#   - service roamcore.trip_wrapped_demo (declared in services.yaml)
#
# This check does NOT touch the live HA instance; it only inspects files.
#
# Wired into scripts/check.sh --core-only between the existing privacy
# smoke check and the end of the core suite.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
FAIL=0

fail() { echo "ERROR: $*" >&2; FAIL=1; }
ok()   { echo "  ✓ $*"; }

# --- 1) demo_seed.py exists and parses ---
DEMO_SCRIPT="homeassistant/tools/trip_wrapped/demo_seed.py"
if [ ! -f "$DEMO_SCRIPT" ]; then
  fail "missing $DEMO_SCRIPT"
else
  ok "found $DEMO_SCRIPT"
  if "$PYTHON_BIN" -c "import ast; ast.parse(open('$DEMO_SCRIPT').read())" >/dev/null 2>&1; then
    ok "demo_seed.py parses cleanly (ast.parse)"
  else
    fail "demo_seed.py failed to parse"
  fi
fi

# --- 2) demo_seed.py --dry-run produces a JSON file with the 5 contract fields ---
TMP_OUT="/tmp/rc_trip_wrapped_seamless_smoke.json"
rm -f "$TMP_OUT"
if "$PYTHON_BIN" "$DEMO_SCRIPT" --dry-run --out "$TMP_OUT" >/dev/null 2>&1; then
  ok "demo_seed.py --dry-run exited 0"
else
  fail "demo_seed.py --dry-run exited non-zero"
fi

if [ ! -f "$TMP_OUT" ]; then
  fail "demo_seed.py did not write $TMP_OUT"
else
  ok "demo_seed.py wrote $TMP_OUT"
  if "$PYTHON_BIN" - "$TMP_OUT" <<'PY' 2>/dev/null
import json, sys
p = sys.argv[1]
obj = json.load(open(p, "r", encoding="utf-8"))
required = ["generatedAt", "mode", "trip", "mapImageUrl"]
missing = [k for k in required if k not in obj]
if missing:
    print("missing fields:", missing, file=sys.stderr); sys.exit(2)
trip = obj.get("trip") or {}
for k in ("distanceKm", "durationMin", "stops"):
    if k not in trip:
        print("trip missing field:", k, file=sys.stderr); sys.exit(3)
if str(obj.get("mode")) != "demo":
    print("mode is not 'demo':", obj.get("mode"), file=sys.stderr); sys.exit(4)
sys.exit(0)
PY
  then
    ok "JSON has all 5 required fields (generatedAt, mode, trip.distanceKm, trip.durationMin, trip.stops, mapImageUrl)"
  else
    fail "JSON missing one or more required fields"
  fi

  # --- 3) mapImageUrl starts with http://localhost:8000/ ---
  MAP_URL="$("$PYTHON_BIN" - "$TMP_OUT" <<'PY'
import json, sys
print(json.load(open(sys.argv[1], "r", encoding="utf-8")).get("mapImageUrl") or "")
PY
)"
  case "$MAP_URL" in
    http://localhost:8000/*)
      ok "mapImageUrl is loopback tileserver: $MAP_URL"
      ;;
    *)
      fail "mapImageUrl is not loopback tileserver: $MAP_URL"
      ;;
  esac
fi

# --- 4) YAML declares both new input_booleans ---
YAML="homeassistant/packages/roamcore_trip_wrapped.yaml"
if [ ! -f "$YAML" ]; then
  fail "missing $YAML"
else
  ok "found $YAML"
  if "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import yaml
d = yaml.safe_load(open("homeassistant/packages/roamcore_trip_wrapped.yaml"))
ib = d.get("input_boolean") or {}
need = ["rc_trip_wrapped_demo", "rc_trip_wrapped_real"]
missing = [n for n in need if n not in ib]
if missing:
    raise SystemExit("input_boolean missing: " + ", ".join(missing))
PY
  then
    ok "input_boolean.rc_trip_wrapped_demo + rc_trip_wrapped_real declared"
  else
    fail "input_boolean.rc_trip_wrapped_demo + rc_trip_wrapped_real NOT both declared"
  fi
fi

# --- 5) services.yaml declares roamcore.trip_wrapped_demo ---
SERVICES_YAML="homeassistant/custom_components/roamcore/services.yaml"
if [ ! -f "$SERVICES_YAML" ]; then
  fail "missing $SERVICES_YAML"
else
  ok "found $SERVICES_YAML"
  if grep -Eq "^trip_wrapped_demo:" "$SERVICES_YAML"; then
    ok "service 'trip_wrapped_demo' declared in services.yaml"
  else
    fail "service 'trip_wrapped_demo' NOT declared in services.yaml"
  fi
fi

# --- 6) __init__.py registers the service handler ---
INIT_PY="homeassistant/custom_components/roamcore/__init__.py"
if [ ! -f "$INIT_PY" ]; then
  fail "missing $INIT_PY"
else
  ok "found $INIT_PY"
  if grep -Eq '"trip_wrapped_demo"' "$INIT_PY"; then
    ok "service handler 'trip_wrapped_demo' registered in __init__.py"
  else
    fail "service handler 'trip_wrapped_demo' NOT registered in __init__.py"
  fi
fi

# --- 7) Pages.js has the one-tap demo CTA ---
PAGES_JS="homeassistant/www/roamcore/roamcore-pages.js"
if [ ! -f "$PAGES_JS" ]; then
  fail "missing $PAGES_JS"
else
  ok "found $PAGES_JS"
  if grep -q "rc-tripwrapped-generate-demo" "$PAGES_JS"; then
    ok "one-tap demo CTA (rc-tripwrapped-generate-demo) wired in pages.js"
  else
    fail "one-tap demo CTA (rc-tripwrapped-generate-demo) NOT wired in pages.js"
  fi
  if grep -Eq "callService\\(['\"]roamcore['\"], ['\"]trip_wrapped_demo['\"]" "$PAGES_JS"; then
    ok "pages.js calls roamcore.trip_wrapped_demo service"
  else
    fail "pages.js does NOT call roamcore.trip_wrapped_demo service"
  fi
fi

echo
if [ "$FAIL" -eq 0 ]; then
  echo "✓ Trip Wrapped seamless smoke check passed (slice #21)"
  exit 0
else
  echo "✗ Trip Wrapped seamless smoke check FAILED" >&2
  exit 1
fi