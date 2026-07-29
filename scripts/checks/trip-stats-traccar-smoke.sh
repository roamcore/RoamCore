#!/usr/bin/env bash
set -euo pipefail

# Wave 2 #18 — Trip stats (rc_trip_*) from real Traccar data smoke check.
#
# Static, regex-driven checks proving that the slice landed coherently:
#   1. The Python helper `homeassistant/tools/trip_wrapped/traccar_trip_stats.py`
#      exists, parses, and `--dry-run` exits 0 with a non-empty JSON output.
#   2. The trip local package (`homeassistant/packages/roamcore_trip_local.yaml`)
#      declares the new `shell_command.rc_trip_stats_poll` shell command.
#   3. The trip local package declares the new `automation.rc_trip_stats_poll`
#      automation with the expected triggers (homeassistant_started + a
#      periodic time pattern + entity_registry_updated).
#   4. The trip local package ships six new `command_line` sensors
#      matching the fallthrough pattern: rc_trip_stats_today_distance,
#      rc_trip_stats_total_distance, rc_trip_stats_today_drive_time,
#      rc_trip_stats_total_drive_time, rc_trip_stats_today_segments,
#      rc_trip_stats_today_stops.
#   5. The location package (`homeassistant/packages/roamcore_location.yaml`)
#      has been updated to prefer `sensor.rc_trip_stats_*` ahead of the
#      existing `rc_trip_wrapped_*` / `rc_trip_local_*` / mock fallthrough.
#   6. The "Trip stats (rc_trip_*) from real Traccar data" row has been
#      moved out of `docs/mvp/features-build-status.md` "Next steps" —
#      i.e. it must NOT appear in the Next steps section anymore.
#
# All assertions are regex / line-based; no build step, fail-softly.
# Exit 0 on success, non-zero on the first failing assertion.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY_HELPER="$ROOT_DIR/homeassistant/tools/trip_wrapped/traccar_trip_stats.py"
TRIP_LOCAL_PKG="$ROOT_DIR/homeassistant/packages/roamcore_trip_local.yaml"
LOCATION_PKG="$ROOT_DIR/homeassistant/packages/roamcore_location.yaml"
FEATURES_DOC="$ROOT_DIR/docs/mvp/features-build-status.md"

fail() {
    echo "FAIL: $*" >&2
    exit 1
}
have() {
    [[ -f "$1" ]] || fail "missing file: $1"
}

have "$PY_HELPER"
have "$TRIP_LOCAL_PKG"
have "$LOCATION_PKG"
have "$FEATURES_DOC"

echo "== Trip stats from real Traccar smoke =="
echo "Helper:   $PY_HELPER"
echo "Pkg:      $TRIP_LOCAL_PKG"
echo "Pkg:      $LOCATION_PKG"
echo "Docs:     $FEATURES_DOC"
echo

# --- 1. Python helper --dry-run works ------------------------------------
if ! python3 -c 'import ast; ast.parse(open("'"$PY_HELPER"'", "r", encoding="utf-8").read())'; then
    fail "traccar_trip_stats.py has a Python syntax error"
fi
echo "OK: traccar_trip_stats.py parses as valid Python"

DRY_RUN_OUT="$(python3 "$PY_HELPER" --dry-run 2>&1)" || fail "traccar_trip_stats.py --dry-run exited non-zero"
if [[ -z "$DRY_RUN_OUT" ]]; then
    fail "traccar_trip_stats.py --dry-run produced empty output"
fi
# The dry-run output should be valid JSON containing the expected keys.
DRY_RUN_JSON="$(python3 "$PY_HELPER" --dry-run 2>/dev/null || true)"
if ! echo "$DRY_RUN_JSON" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert "tracker_available" in d; assert "today" in d; assert "total_distance_mi" in d; assert "today_drive_time_hms" in d' 2>/dev/null; then
    fail "traccar_trip_stats.py --dry-run did not produce the expected JSON shape (need tracker_available, today, total_distance_mi, today_drive_time_hms)"
fi
echo "OK: traccar_trip_stats.py --dry-run produces expected JSON shape"

# Also exercise the test path: --tracker + --latitude/--longitude
LIVE_OUT="$(python3 "$PY_HELPER" --dry-run --tracker device_tracker.traccar_test --latitude 51.5 --longitude -0.1 --speed-mps 5.0 2>/dev/null || true)"
if ! echo "$LIVE_OUT" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d.get("tracker_available") is True; assert d.get("tracker_entity_id") == "device_tracker.traccar_test"; assert d.get("last_lat") == 51.5' 2>/dev/null; then
    fail "traccar_trip_stats.py --dry-run --tracker/--latitude/--longitude did not echo the override inputs"
fi
echo "OK: traccar_trip_stats.py honours --tracker / --latitude / --longitude overrides"

# --- 2. shell_command.rc_trip_stats_poll present ------------------------
if ! grep -Eq '^[[:space:]]*rc_trip_stats_poll:' "$TRIP_LOCAL_PKG"; then
    fail "missing shell_command.rc_trip_stats_poll in $TRIP_LOCAL_PKG"
fi
echo "OK: shell_command.rc_trip_stats_poll declared in trip_local package"

if ! grep -Eq 'traccar_trip_stats\.py' "$TRIP_LOCAL_PKG"; then
    fail "rc_trip_stats_poll does not invoke traccar_trip_stats.py"
fi
echo "OK: rc_trip_stats_poll invokes traccar_trip_stats.py"

# --- 3. automation.rc_trip_stats_poll present ----------------------------
if ! grep -Eq '^[[:space:]]*-[[:space:]]*id:[[:space:]]*rc_trip_stats_poll' "$TRIP_LOCAL_PKG"; then
    fail "missing automation id rc_trip_stats_poll in $TRIP_LOCAL_PKG"
fi
echo "OK: automation.rc_trip_stats_poll declared"

if ! grep -Eq 'event:[[:space:]]*start' "$TRIP_LOCAL_PKG"; then
    fail "rc_trip_stats_poll does not trigger on homeassistant_started"
fi
echo "OK: rc_trip_stats_poll triggers on homeassistant_started"

if ! grep -Eq 'time_pattern' "$TRIP_LOCAL_PKG"; then
    fail "rc_trip_stats_poll does not have a periodic time_pattern trigger"
fi
echo "OK: rc_trip_stats_poll has a periodic trigger"

if ! grep -Eq 'entity_registry_updated' "$TRIP_LOCAL_PKG"; then
    fail "rc_trip_stats_poll does not listen on entity_registry_updated (needed for mid-session tracker additions)"
fi
echo "OK: rc_trip_stats_poll also triggers on entity_registry_updated"

if ! grep -Eq 'shell_command\.rc_trip_stats_poll' "$TRIP_LOCAL_PKG"; then
    fail "rc_trip_stats_poll automation does not call shell_command.rc_trip_stats_poll"
fi
echo "OK: rc_trip_stats_poll calls shell_command.rc_trip_stats_poll"

# --- 4. Six new command_line sensors ------------------------------------
for unique_id in \
    rc_trip_stats_today_distance_mi \
    rc_trip_stats_total_distance_mi \
    rc_trip_stats_today_drive_time \
    rc_trip_stats_total_drive_time \
    rc_trip_stats_today_segments \
    rc_trip_stats_today_stops ; do
    if ! grep -Eq "unique_id:[[:space:]]*$unique_id" "$TRIP_LOCAL_PKG"; then
        fail "missing command_line sensor with unique_id $unique_id in $TRIP_LOCAL_PKG"
    fi
done
echo "OK: all six rc_trip_stats_* command_line sensors declared"

# Each sensor must reference the rolling JSON file path so the
# fallthrough pattern is consistent.
if ! grep -Eq 'roamcore_trip_stats\.json' "$TRIP_LOCAL_PKG"; then
    fail "rc_trip_stats_* sensors do not reference the rolling JSON file path"
fi
echo "OK: rc_trip_stats_* sensors reference the rolling JSON file path"

# --- 5. location package fallthrough prefers rc_trip_stats_* -----------
if ! grep -Eq "rc_trip_stats_today_distance" "$LOCATION_PKG"; then
    fail "roamcore_location.yaml does not prefer sensor.rc_trip_stats_today_distance for rc_trip_distance_today_mi"
fi
if ! grep -Eq "rc_trip_stats_total_distance" "$LOCATION_PKG"; then
    fail "roamcore_location.yaml does not prefer sensor.rc_trip_stats_total_distance for rc_trip_distance_total_mi"
fi
if ! grep -Eq "rc_trip_stats_today_drive_time" "$LOCATION_PKG"; then
    fail "roamcore_location.yaml does not prefer sensor.rc_trip_stats_today_drive_time for rc_trip_time_today"
fi
if ! grep -Eq "rc_trip_stats_total_drive_time" "$LOCATION_PKG"; then
    fail "roamcore_location.yaml does not prefer sensor.rc_trip_stats_total_drive_time for rc_trip_time_total"
fi
if ! grep -Eq "rc_trip_stats_today_segments" "$LOCATION_PKG"; then
    fail "roamcore_location.yaml does not prefer sensor.rc_trip_stats_today_segments for rc_trip_segments"
fi
if ! grep -Eq "rc_trip_stats_today_stops" "$LOCATION_PKG"; then
    fail "roamcore_location.yaml does not prefer sensor.rc_trip_stats_today_stops for rc_trip_stops"
fi
echo "OK: rc_trip_distance_* / rc_trip_time_* / rc_trip_segments / rc_trip_stops prefer rc_trip_stats_* ahead of mocks"

# Ensure rc_trip_distance_total_mi is no longer ONLY reading the mock —
# i.e. the template must mention rc_trip_stats_total_distance, not just
# the mock input_number.
if ! awk '/unique_id:[[:space:]]*rc_trip_distance_total_mi/,/^[[:space:]]*-[[:space:]]*name:/' "$LOCATION_PKG" \
        | grep -q 'rc_trip_stats_total_distance'; then
    fail "rc_trip_distance_total_mi template does not fall through to rc_trip_stats_total_distance"
fi
echo "OK: rc_trip_distance_total_mi falls through to rc_trip_stats_total_distance (not just mock)"

# --- 6. docs: row moved out of "Next steps" ------------------------------
# The "Next steps" section in features-build-status.md must no longer
# mention the trip-stats title text. Capture the section between the
# "## Next steps" header and the next "## " header and assert the title
# is absent.
NEXT_STEPS="$(awk '/^## Next steps/{flag=1; next} /^## /{flag=0} flag' "$FEATURES_DOC")"
if grep -Eqi 'Trip stats \(rc_trip_\*\) from real Traccar data' <<<"$NEXT_STEPS"; then
    fail "docs/mvp/features-build-status.md still lists 'Trip stats (rc_trip_*) from real Traccar data' in the Next steps section (must be moved to Shipped)"
fi
echo "OK: 'Trip stats' row removed from 'Next steps' in features-build-status.md"

# And it must now appear under "Shipped (repo)".
if ! grep -Eqi 'Trip stats \(rc_trip_\*\) from real Traccar data' "$FEATURES_DOC"; then
    fail "docs/mvp/features-build-status.md no longer mentions 'Trip stats' at all (should be moved to Shipped, not deleted)"
fi
# Verify the moved row sits under the Shipped heading (i.e. between the
# "## Shipped" header and the "## Next steps" header).
SHIPPED="$(awk '/^## Shipped/{flag=1; next} /^## /{flag=0} flag' "$FEATURES_DOC")"
if ! grep -Eqi 'Trip stats \(rc_trip_\*\) from real Traccar data' <<<"$SHIPPED"; then
    fail "docs/mvp/features-build-status.md does not list 'Trip stats' under the 'Shipped (repo)' section"
fi
echo "OK: 'Trip stats' row is now under 'Shipped (repo)' in features-build-status.md"

echo
echo "All trip-stats-traccar smoke checks passed."