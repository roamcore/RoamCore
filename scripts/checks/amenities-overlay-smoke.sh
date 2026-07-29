#!/usr/bin/env bash
# Amenities overlay smoke check (slice #22).
#
# Validates that the RoamCore amenities overlay slice (#22) is wired
# end-to-end on disk:
#
#   1) The Python helper ``homeassistant/tools/amenities/overpass_query.py``
#      exists, parses cleanly (stdlib-only — AST parse, not import),
#      and ``--dry-run`` produces a JSON file with the 6 contract fields.
#      The JSON must contain at least one POI per default category
#      (water, dump_station, laundry, campground, supermarket, gym).
#
#   2) ``homeassistant/packages/roamcore_amenities.yaml`` declares the
#      four contract inputs + at least one automation.
#
#   3) ``homeassistant/www/roamcore/roamcore-pages.js`` references the
#      ``RcAmenitiesLayer`` class and the toggle wiring
#      (``input_boolean.rc_amenities_overlay_enabled``).
#
# This check does NOT touch the live HA instance; it only inspects files.
# Wired into ``scripts/check.sh --core-only`` after the privacy smoke.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
FAIL=0

fail() { echo "ERROR: $*" >&2; FAIL=1; }
ok()   { echo "  ✓ $*"; }

# --- 1) Python helper exists + AST parse + dry-run ---
HELPER="homeassistant/tools/amenities/overpass_query.py"
if [ ! -f "$HELPER" ]; then
  fail "missing $HELPER"
else
  ok "found $HELPER"
  if "$PYTHON_BIN" -c "import ast; ast.parse(open('$HELPER').read())" >/dev/null 2>&1; then
    ok "overpass_query.py parses cleanly (ast.parse)"
  else
    fail "overpass_query.py failed to parse"
  fi

  TMP_OUT="/tmp/rc_amenities_overlay_smoke.json"
  rm -f "$TMP_OUT"
  if "$PYTHON_BIN" "$HELPER" --dry-run --lat 36.0 --lon -111.0 --radius-km 5 --out "$TMP_OUT" >/dev/null 2>&1; then
    ok "overpass_query.py --dry-run exited 0"
  else
    fail "overpass_query.py --dry-run exited non-zero"
  fi

  if [ ! -f "$TMP_OUT" ]; then
    fail "overpass_query.py did not write $TMP_OUT"
  else
    ok "overpass_query.py wrote $TMP_OUT"
    if "$PYTHON_BIN" - "$TMP_OUT" <<'PY' 2>/dev/null
import json, sys
p = sys.argv[1]
obj = json.load(open(p, "r", encoding="utf-8"))
required = ["generatedAt", "lat", "lon", "radiusKm", "categories", "pois"]
missing = [k for k in required if k not in obj]
if missing:
    print("missing top-level fields:", missing, file=sys.stderr); sys.exit(2)
if not isinstance(obj["pois"], list) or len(obj["pois"]) == 0:
    print("pois must be a non-empty list", file=sys.stderr); sys.exit(3)
for p in obj["pois"]:
    for k in ("id", "category", "name", "lat", "lon", "tags", "distanceKm"):
        if k not in p:
            print(f"poi missing field: {k}", file=sys.stderr); sys.exit(4)
sys.exit(0)
PY
    then
      ok "JSON has all 6 contract fields (generatedAt, lat, lon, radiusKm, categories, pois)"
    else
      fail "JSON missing one or more required contract fields"
    fi

    # 1 POI per default category.
    if "$PYTHON_BIN" - "$TMP_OUT" <<'PY' 2>/dev/null
import json, sys
obj = json.load(open(sys.argv[1], "r", encoding="utf-8"))
expected = {"water", "dump_station", "laundry", "campground", "supermarket", "gym"}
seen = {p.get("category") for p in obj.get("pois") or []}
missing = sorted(expected - seen)
if missing:
    print("missing categories:", missing, file=sys.stderr); sys.exit(2)
sys.exit(0)
PY
    then
      ok "fixture contains at least one POI per default category (6/6)"
    else
      fail "fixture is missing POIs for one or more default categories"
    fi
  fi
fi

# --- 2) YAML declares 4 inputs + at least 1 automation ---
YAML="homeassistant/packages/roamcore_amenities.yaml"
if [ ! -f "$YAML" ]; then
  fail "missing $YAML"
else
  ok "found $YAML"
  if "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import yaml
d = yaml.safe_load(open("homeassistant/packages/roamcore_amenities.yaml"))
need_ib = ["rc_amenities_overlay_enabled"]
need_is = ["rc_amenities_categories"]
need_in = ["rc_amenities_radius_km"]
need_it = ["rc_amenities_overpass_url"]
ib = (d.get("input_boolean") or {})
is_ = (d.get("input_select") or {})
inn = (d.get("input_number") or {})
it = (d.get("input_text") or {})
missing = []
for n in need_ib:
    if n not in ib: missing.append(f"input_boolean.{n}")
for n in need_is:
    if n not in is_: missing.append(f"input_select.{n}")
for n in need_in:
    if n not in inn: missing.append(f"input_number.{n}")
for n in need_it:
    if n not in it: missing.append(f"input_text.{n}")
if missing:
    raise SystemExit("missing inputs: " + ", ".join(missing))
auto = d.get("automation") or []
if not auto:
    raise SystemExit("no automations declared")
PY
  then
    ok "input_boolean.rc_amenities_overlay_enabled + input_select.rc_amenities_categories + input_number.rc_amenities_radius_km + input_text.rc_amenities_overpass_url + 1+ automation declared"
  else
    fail "YAML missing one of the 4 contract inputs (or no automations)"
  fi
fi

# --- 3) Pages.js has the layer + toggle wiring ---
PAGES_JS="homeassistant/www/roamcore/roamcore-pages.js"
if [ ! -f "$PAGES_JS" ]; then
  fail "missing $PAGES_JS"
else
  ok "found $PAGES_JS"
  if grep -q "RcAmenitiesLayer" "$PAGES_JS"; then
    ok "RcAmenitiesLayer referenced in pages.js"
  else
    fail "RcAmenitiesLayer NOT referenced in pages.js"
  fi
  if grep -q "rc_amenities_overlay_enabled" "$PAGES_JS"; then
    ok "input_boolean.rc_amenities_overlay_enabled wired in pages.js"
  else
    fail "input_boolean.rc_amenities_overlay_enabled NOT wired in pages.js"
  fi
fi

echo
if [ "$FAIL" -eq 0 ]; then
  echo "✓ Amenities overlay smoke check passed (slice #22)"
  exit 0
else
  echo "✗ Amenities overlay smoke check FAILED" >&2
  exit 1
fi
