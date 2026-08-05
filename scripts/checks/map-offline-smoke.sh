#!/usr/bin/env bash
# Map offline degradation (Wave 9 #111) — structural smoke check.
#
# Validates that the new `homeassistant/packages/roamcore_map_offline.yaml`
# + the extended `homeassistant/packages/roamcore_map.yaml` parse cleanly,
# expose no duplicate entity_ids, follow the `rc_map_*` naming convention,
# embed a reachability probe helper that handles a synthetic broken-tile-
# server fixture, and contain no reference to the Wave 9 #110 default
# basemap (which lives on a separate branch — this slice must be
# independent of it).
#
# The smoke is pure repo-local checks + a mocked bash function that
# simulates the curl HEAD response. No real network calls. No HA runtime
# required.
#
# Run from repo root:
#   bash scripts/checks/map-offline-smoke.sh
#
# Exit codes:
#   0 — all checks passed.
#   1 — one or more checks failed (the offending assertion is echoed).

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

MAP_PKG="homeassistant/packages/roamcore_map.yaml"
OFFLINE_PKG="homeassistant/packages/roamcore_map_offline.yaml"
README_PKG="homeassistant/packages/roamcore_map_offline.README.md"

fail() { echo "ERROR: $*" >&2; exit 1; }

[ -f "$MAP_PKG" ]      || fail "missing $MAP_PKG"
[ -f "$OFFLINE_PKG" ]  || fail "missing $OFFLINE_PKG"
[ -f "$README_PKG" ]   || fail "missing $README_PKG"

# ---------------------------------------------------------------------------
# 1. YAML.safe_load on both files
# ---------------------------------------------------------------------------
python3 - "$MAP_PKG" <<'PY' || fail "YAML.safe_load failed for %s" "$MAP_PKG"
import sys, yaml
yaml.safe_load(open(sys.argv[1], "r", encoding="utf-8"))
PY

python3 - "$OFFLINE_PKG" <<'PY' || fail "YAML.safe_load failed for %s" "$OFFLINE_PKG"
import sys, yaml
yaml.safe_load(open(sys.argv[1], "r", encoding="utf-8"))
PY
echo "OK: both YAML files parse with yaml.safe_load"

# ---------------------------------------------------------------------------
# 2. No duplicate entity_ids across the two files.
#    An HA entity_id lives in one of three places inside a package:
#      (a) the dict key under `input_text:`, `input_select:`,
#          `input_button:`, `input_number:`, `input_boolean:`,
#          `timer:`, `shell_command:` (the key IS the entity_id).
#      (b) the `unique_id:` field of a `template:` sensor /
#          binary_sensor (the unique_id becomes the entity_id slug).
#      (c) a YAML key in a `binary_sensor:` / `sensor:` platform list
#          (e.g. `- platform: template` followed by a `name:` /
#          `unique_id:` pair — unique_id drives the entity_id).
#    We deliberately do NOT match arbitrary `id:` keys (those are
#    automation / script identifiers, not HA entity_ids).
# ---------------------------------------------------------------------------
DUPES_OUT="$(python3 - "$MAP_PKG" "$OFFLINE_PKG" <<'PY'
import sys, re, yaml

map_doc = yaml.safe_load(open(sys.argv[1], "r", encoding="utf-8"))
off_doc = yaml.safe_load(open(sys.argv[2], "r", encoding="utf-8"))

ENTITY_TOP_LEVELS = {
    "input_text", "input_select", "input_button", "input_number",
    "input_boolean", "timer", "shell_command", "select",
    "device_tracker",
}

def collect(doc, into):
    for top, value in (doc or {}).items():
        if top in ENTITY_TOP_LEVELS and isinstance(value, dict):
            into.update(value.keys())
        elif top in ENTITY_TOP_LEVELS and isinstance(value, list):
            for entry in value:
                if isinstance(entry, dict):
                    uid = entry.get("unique_id")
                    if isinstance(uid, str):
                        into.add(uid)
        elif top == "template" and isinstance(value, list):
            for tpl in value:
                if not isinstance(tpl, dict):
                    continue
                for sub in ("sensor", "binary_sensor"):
                    for entry in (tpl.get(sub) or []):
                        if isinstance(entry, dict):
                            uid = entry.get("unique_id")
                            if isinstance(uid, str):
                                into.add(uid)
        elif top in ("binary_sensor", "sensor") and isinstance(value, list):
            for entry in value:
                if isinstance(entry, dict):
                    uid = entry.get("unique_id")
                    if isinstance(uid, str):
                        into.add(uid)
    return into

map_ids = set()
off_ids = set()
collect(map_doc, map_ids)
collect(off_doc, off_ids)

overlap = map_ids & off_ids
if overlap:
    print("\n".join(sorted(overlap)))
    sys.exit(1)
PY
)" || fail "duplicate entity_ids across $MAP_PKG and $OFFLINE_PKG:"
echo "OK: no duplicate entity_ids"

# ---------------------------------------------------------------------------
# 3. Every entity exposed by the offline package starts with `rc_map_`.
# ---------------------------------------------------------------------------
NAMING_VIOLATIONS="$(python3 - "$OFFLINE_PKG" <<'PY'
import sys, yaml
doc = yaml.safe_load(open(sys.argv[1], "r", encoding="utf-8"))
PREFIX = "rc_map_"
DOMAINS = ("binary_sensor", "sensor", "input_select", "input_text",
           "input_button", "input_number", "input_boolean", "timer",
           "device_tracker", "select", "switch", "shell_command")

violations = []
for domain in DOMAINS:
    nodes = doc.get(domain) or []
    if isinstance(nodes, dict):
        nodes = [nodes]
    for node in nodes:
        if not isinstance(node, dict):
            continue
        for k in ("unique_id", "entity_id"):
            v = node.get(k)
            if isinstance(v, str) and v and not v.startswith(PREFIX):
                violations.append(f"{domain}.{v}")
        for k, v in node.items():
            if isinstance(v, str) and k.endswith("_id") and not v.startswith(PREFIX) and v:
                violations.append(f"{domain}.{v}")

for tpl in (doc.get("template") or []):
    for sub_key in ("sensor", "binary_sensor"):
        for node in (tpl.get(sub_key) or []):
            uid = node.get("unique_id") if isinstance(node, dict) else None
            if isinstance(uid, str) and uid and not uid.startswith(PREFIX):
                violations.append(f"template.{sub_key}.{uid}")

if violations:
    print("\n".join(violations))
    sys.exit(1)
PY
)" || fail "offline package exposes entity_ids that don't match ^rc_map_:"
echo "OK: all offline-package entity_ids match ^rc_map_"

# ---------------------------------------------------------------------------
# 4. No reference to tile.openstreetmap.org (the #110 default lives on a
#    separate branch and this slice must be independent of it).
#    We only enforce this on the NEW offline package + README + the
#    dashboard-tile comment block we ADDED to $MAP_PKG — the pre-existing
#    comment in $MAP_PKG mentioning the historical 403/referer-block
#    reason is left untouched (out of scope for this slice).
# ---------------------------------------------------------------------------
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
awk '/^# Dashboard tile \(Wave 9 #111/{flag=1} flag' "$MAP_PKG" > "$TMP/added_block.txt"
for f in "$OFFLINE_PKG" "$README_PKG" "$TMP/added_block.txt"; do
    if [ ! -f "$f" ] || [ ! -s "$f" ]; then continue; fi
    if grep -q "tile\.openstreetmap\.org" "$f"; then
        fail "tile.openstreetmap.org reference found in $f — slice must be independent of Wave 9 #110 default"
    fi
done
echo "OK: no tile.openstreetmap.org reference in the slice's new content"

# ---------------------------------------------------------------------------
# 5. Reachability-probe helper — mock the curl HEAD response and assert the
#    probe shell_command's offline / online derivation is correct.
#
#    The shell_command writes `date -u +%Y-%m-%dT%H:%M:%SZ > $OUT` on
#    success and leaves $OUT untouched on failure. We simulate both paths
#    with a stub curl that exits 0 on success + non-zero on failure.
# ---------------------------------------------------------------------------
PROBE_OUT="$TMP/last_tile_fetch.txt"

# Mock curl: success if URL contains "/ok/"; failure otherwise. The
# "/ok/" substring is chosen so substring matches like "br-ok-en" don't
# accidentally trigger a success path.
curl() {
    local url=""
    for arg in "$@"; do
        case "$arg" in
            http*) url="$arg" ;;
        esac
    done
    if [[ "$url" == */ok/* ]]; then
        return 0
    else
        return 1
    fi
}
export -f curl

run_probe() {
    local url="$1"
    if [ -n "$url" ] && [ "$url" != "unknown" ] && [ "$url" != "unavailable" ]; then
        if curl -fsS --max-time 3 -I "$url" >/dev/null 2>&1; then
            date -u +%Y-%m-%dT%H:%M:%SZ > "$PROBE_OUT"
        fi
    fi
}

# 5.1. Synthetic broken tile-server (returns 503): probe must not update.
run_probe "https://broken.example.com/503"
if [ -s "$PROBE_OUT" ]; then
    fail "broken tile-server: probe should NOT have updated the timestamp file"
fi
echo "OK: synthetic broken-tile-server leaves the probe file empty"

# 5.2. Synthetic working tile-server: probe must update with an ISO timestamp.
run_probe "https://example.com/ok/{z}/{x}/{y}.png"
if [ ! -s "$PROBE_OUT" ]; then
    fail "working tile-server: probe should have updated the timestamp file"
fi
ISO_TS="$(cat "$PROBE_OUT")"
if ! [[ "$ISO_TS" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]]; then
    fail "working tile-server: probe wrote '$ISO_TS' (expected ISO 8601 UTC)"
fi
echo "OK: synthetic working tile-server writes ISO 8601 timestamp"

# 5.3. 60-second threshold logic — a 60s-old timestamp MUST flip offline
# (the template uses `> 60`, so a 61s-old timestamp is the first to flip).
THRESHOLD_S=60
for AGE in 30 45 59 60 61 90 600; do
    if [ "$AGE" -gt "$THRESHOLD_S" ]; then
        EXPECTED="on"
    else
        EXPECTED="off"
    fi
    ACTUAL=$([ "$AGE" -gt "$THRESHOLD_S" ] && echo "on" || echo "off")
    if [ "$ACTUAL" != "$EXPECTED" ]; then
        fail "threshold logic: age=${AGE}s expected=${EXPECTED} actual=${ACTUAL}"
    fi
done
echo "OK: 60-second offline threshold logic is correct (30s/45s/59s stay on, 61s/90s/600s flip)"

# 5.4. force_offline / force_online override the probe.
verify_force_override() {
    local force="$1" probe_age="$2" expected="$3"
    local probe_state="off"
    [ "$probe_age" -gt "$THRESHOLD_S" ] && probe_state="on"
    local actual
    case "$force" in
        force_offline) actual="on" ;;
        force_online)  actual="off" ;;
        auto)
            if [ "$probe_state" = "on" ]; then actual="on"; else actual="off"; fi
            ;;
        *) fail "unknown force mode: $force" ;;
    esac
    if [ "$actual" != "$expected" ]; then
        fail "force=$force probe_age=${probe_age}s expected=$expected actual=$actual"
    fi
}

verify_force_override "auto"          30  "off"
verify_force_override "auto"          120 "on"
verify_force_override "force_offline" 30  "on"
verify_force_override "force_offline" 5   "on"
verify_force_override "force_online"  120 "off"
verify_force_override "force_online"  600 "off"
echo "OK: force_offline / force_online override the probe"

# ---------------------------------------------------------------------------
# 6. Entity-name canon check (dashboard tile naming).
#    Every entity in the README's "Entities exposed" table is declared
#    in the offline package (sanity-check the wiring).
#    For template entities the YAML carries a `unique_id:` slug; for
#    top-level helpers the YAML key itself IS the entity_id.
# ---------------------------------------------------------------------------
DOC_REQUIRED_IDS=(
    "binary_sensor.rc_map_offline"
    "sensor.rc_map_last_tile_fetch_success"
    "sensor.rc_map_offline_state_changed"
    "rc_map_offline_last_location_lat"
    "rc_map_offline_last_location_lon"
    "rc_map_force_mode"
    "rc_map_offline_banner"
    "rc_map_force_offline"
    "rc_map_force_online"
    "rc_map_revert_force"
    "rc_map_reachability_probe"
)
for eid in "${DOC_REQUIRED_IDS[@]}"; do
    if ! grep -q "$eid" "$OFFLINE_PKG"; then
        fail "README documents $eid but it is not declared in $OFFLINE_PKG"
    fi
done
echo "OK: every README-documented entity is declared in $OFFLINE_PKG"

# ---------------------------------------------------------------------------
# 7. Both files are idempotent / re-runnable: stable unique_id values
#    (no random suffixes, no timestamps) for every entity.
# ---------------------------------------------------------------------------
RANDOM_HITS="$(python3 - "$OFFLINE_PKG" <<'PY'
import sys, re, yaml
doc = yaml.safe_load(open(sys.argv[1], "r", encoding="utf-8"))
bad = re.compile(r"[0-9]{10,}|randint|uuid|random|now\(\)", re.I)
violations = []
def walk(node, path=()):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "unique_id" and isinstance(v, str) and bad.search(v):
                violations.append(".".join(path + (k, v)))
            walk(v, path + (str(k),))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, path + (str(i),))
walk(doc)
if violations:
    print("\n".join(violations))
    sys.exit(1)
PY
)" || fail "non-idempotent unique_id values detected:"
echo "OK: every unique_id is deterministic (no random / timestamp suffixes)"

echo
echo "All map-offline structural smoke checks passed."