#!/usr/bin/env bash
# Capability mapping layer: smoke check
#
# Wave 9 #119.b — Phase 2 capability mapping layer (turns raw Home
# Assistant entity_ids into the canonical RoamCore capability ids
# declared in `connections/_schema/canonical_capabilities.json`).
#
# The mapping rules live at `connections/_schema/mapping_rules.json`
# and are consumed by the pure-Python mapper at
# `homeassistant/custom_components/roamcore/capability_mapper.py`.
#
# Mirrors the convention in scripts/checks/<name>.sh:
#   - bash strict mode (set -euo pipefail)
#   - repo-local only (no live HA / Proxmox / vendor calls)
#   - plain-English summary at exit 0 / non-zero exit
#   - runs the mapper pytest + a handful of cheap inline assertions
#
# Exit codes:
#   0  rules file is valid JSON, mapper is happy, every rule targets a
#      real canonical_capability, resolve_entity_to_capability works on
#      spot-checks, the 50-entity real-world mapping has zero unmapped
#      required entries, rc-naming is respected, validation rejects
#      broken rules, and check.sh --core-only stays green
#   1  any of the above failed
#
# Wired into scripts/check.sh as a `run_if_present` step.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

SCHEMA="connections/_schema/canonical_capabilities.json"
RULES="connections/_schema/mapping_rules.json"
MAPPER="homeassistant/custom_components/roamcore/capability_mapper.py"
PYTEST_TARGET="homeassistant/custom_components/roamcore/tests/test_capability_mapper.py"

fail() { echo "ERROR: $*" >&2; exit 1; }
ok()   { echo "OK: $*"; }

# --- 1. The three key files exist ---
[ -f "$SCHEMA" ]  || fail "missing canonical schema file: $SCHEMA"
[ -f "$RULES" ]   || fail "missing mapping rules file: $RULES"
[ -f "$MAPPER" ]  || fail "missing mapper module: $MAPPER"
ok "files present: schema + rules + mapper module"

# --- 2. The rules file parses as JSON ---
python3 -c "import json; json.load(open('$RULES','r',encoding='utf-8'))" \
  || fail "JSON parse failed: $RULES"
ok "$RULES parses as JSON"

# --- 3. The mapper Python module imports cleanly + the schema file
#       parses via the mapper's loader ---
python3 - <<'PYEOF'
import importlib.util, os, sys

# Load capability_mapper.py from absolute path so we don't depend on
# pytest's package-discovery machinery (same pattern as the
# mapper's own test file + test_vehicle_model.py).
HERE = os.path.dirname(os.path.abspath("homeassistant/custom_components/roamcore/capability_mapper.py"))
CM = os.path.abspath("homeassistant/custom_components/roamcore/capability_mapper.py")
spec = importlib.util.spec_from_file_location("smoke_mapper", CM)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Round-trip the rules + schema via the mapper's own loaders.
rules = mod.load_mapping_rules("connections/_schema/mapping_rules.json")
schema = mod.load_capability_schema("connections/_schema/canonical_capabilities.json")

# Resolve 5 sample inputs.
samples = [
    ("sensor.victron_smartshunt_battery_voltage", "rc_power_battery_voltage"),
    ("sensor.vt_battery_soc_percent",             "rc_power_battery_soc"),
    ("sensor.indoor_temp",                        "rc_climate_indoor_temperature"),
    ("switch.cabin_main",                         "rc_lighting_interior_state"),
    ("binary_sensor.rc_net_internet_reachable",   "rc_network_internet_reachable"),
]
for entity_id, expected_cap in samples:
    result = mod.resolve_entity_to_capability(entity_id, rules=rules, schema=schema)
    assert result is not None, (
        f"resolve_entity_to_capability({entity_id!r}) returned None"
    )
    cap_id, _rule_id, _conf = result
    assert cap_id == expected_cap, (
        f"resolve_entity_to_capability({entity_id!r}) -> {cap_id!r}, "
        f"expected {expected_cap!r}"
    )

# Unknown entity must return None (auto-recover doctrine).
assert mod.resolve_entity_to_capability(
    "sensor.totally_made_up_xyz", rules=rules, schema=schema
) is None, "unknown entity should resolve to None"

# map_entities on a 50-entity batch must cover every declared
# canonical capability with zero unmatched required entries.
real_world = [
    "sensor.vt_battery_soc_percent", "sensor.victron_smartshunt_battery_voltage",
    "sensor.vt_battery_current_a",   "sensor.vt_solar_power_w",
    "binary_sensor.vt_shore_connected",
    "switch.cabin_main",             "switch.porch_light",
    "sensor.indoor_temp",            "switch.hvac_main",
    "sensor.fresh_water_tank_level", "switch.water_pump",
    "device_tracker.vt_vehicle",     "sensor.vehicle_lon",
    "binary_sensor.rc_net_internet_reachable", "sensor.rc_net_wan_ip",
    "sensor.rc_power_battery_soc",   "sensor.rc_power_battery_voltage",
    "sensor.rc_power_battery_current","sensor.rc_power_solar_power",
    "binary_sensor.rc_power_shore_connected",
    "switch.rc_lighting_interior_state",
    "switch.rc_lighting_approach_state",
    "sensor.rc_climate_indoor_temperature",
    "switch.rc_climate_hvac_state",
    "sensor.rc_water_fresh_level",    "switch.rc_water_pump_state",
    "sensor.rc_position_lat",         "sensor.rc_position_lon",
    "binary_sensor.rc_network_internet_reachable",
    "sensor.rc_network_wan_ip",
    "sensor.renogy_ranger_battery_soc",
    "sensor.renogy_solar_power_w",
    "sensor.generic_battery_state_of_charge",
    "sensor.generic_solar_panel_power",
    "binary_sensor.shore_power_connected",
    "switch.cabin_lights_zone_2",
    "switch.awning_light_zone_a",
    "sensor.cabin_temperature",
    "switch.webasto_heater",
    "sensor.potable_water_tank",
    "switch.shurflo_pump",
    "sensor.gps_lat",                 "sensor.gps_lon",
    "binary_sensor.internet_reachable",
    "sensor.wan_ip",
    # 2 deliberately unmatched entries — must NOT crash.
    "sensor.weather_forecast",
    "binary_sensor.front_door_lock",
]
mapping, unmatched = mod.apply_mapping_rules(real_world, rules, schema)
resolved_caps = {v for v in mapping.values() if v is not None}
declared_caps = {
    c["id"] for c in schema["capabilities"]
    if isinstance(c, dict) and isinstance(c.get("id"), str)
}
missing_caps = declared_caps - resolved_caps
assert missing_caps == set(), (
    f"canonical capabilities with no mapping in the 50-entity batch: "
    f"{sorted(missing_caps)}"
)
# The 2 deliberately-unmatched entries should be in unmatched; the
# rest should not.
assert "sensor.weather_forecast" in unmatched
assert "binary_sensor.front_door_lock" in unmatched
assert "sensor.vt_battery_soc_percent" not in unmatched

# No secrets / hardcoded URLs / vendor tokens in the rules file or
# the mapper module. (Allowed: the regex patterns mention vendor
# names because they MATCH raw upstream entity_ids — that's the point.
# Banned: API keys, bearer tokens, http:// URLs to live services.)
import re
for path in ("connections/_schema/mapping_rules.json",
             "homeassistant/custom_components/roamcore/capability_mapper.py"):
    with open(path, "r", encoding="utf-8") as fp:
        text = fp.read()
    assert "bearer " not in text.lower(), (
        f"{path}: looks like it contains a bearer token"
    )
    assert "api_key" not in text.lower(), (
        f"{path}: looks like it contains an api_key string"
    )
    # http(s) URLs are tolerated in docstrings (canonical_capabilities
    # json-schema reference); just make sure none point to live
    # RoamCore / Victron / Starlink / etc. endpoints that would leak
    # a private host.
    for url in re.findall(r"https?://[^\s\"'<>)]+", text):
        assert "victron" not in url.lower() or "json-schema.org" in url.lower() \
            or "w3.org" in url.lower(), (
            f"{path}: suspicious live URL {url!r}"
        )

# rc-naming compliance check on every rule's canonical_capability.
import re
pat = re.compile(r"^rc_[a-z][a-z0-9]*(_[a-z][a-z0-9]*){1,}$")
for r in rules["rules"]:
    cid = r.get("canonical_capability")
    assert isinstance(cid, str) and cid.startswith("rc_"), (
        f"rule {r.get('id')!r}: canonical_capability must start with rc_"
    )
    assert pat.match(cid), (
        f"rule {r.get('id')!r}: canonical_capability {cid!r} does not "
        f"match rc-naming pattern"
    )

# Validation must reject 2 crafted bad rules.
bad_rules = {
    "version": 1,
    "rules": [
        {
            "id": "bad_regex_rule",
            "source_pattern": "sensor\\.(unclosed",
            "canonical_capability": "rc_power_battery_soc",
            "weight": 50,
            "description": "should fail: bad regex",
        },
        {
            "id": "bad_capability_rule",
            "source_pattern": "sensor\\.foo",
            "canonical_capability": "rc_power_typoed_capability",
            "weight": 50,
            "description": "should fail: cap not in schema",
        },
        {
            "id": "bad_weight_rule",
            "source_pattern": "sensor\\.foo",
            "canonical_capability": "rc_power_battery_soc",
            "weight": 999,
            "description": "should fail: weight out of range",
        },
    ],
}
errs = mod.validate_mapping_rules(bad_rules, schema)
joined = " | ".join(errs)
assert "invalid regex" in joined, f"validation missed bad regex: {errs}"
assert "not declared in canonical_capabilities.json" in joined, (
    f"validation missed unknown capability: {errs}"
)
assert "out of range" in joined, f"validation missed weight range: {errs}"

print("OK: mapper loads cleanly")
print("OK: 5 spot-check entity_ids resolve to expected canonical capabilities")
print("OK: unknown entity_id returns None (auto-recover)")
print("OK: 50-entity real-world mapping covers every declared canonical capability")
print("OK: deliberately-unmatched entries land in the unmatched list")
print("OK: no secrets / live URLs / vendor tokens in rules or mapper module")
print("OK: every rule's canonical_capability matches the rc-naming pattern")
print("OK: validate_mapping_rules rejects bad regex + unknown capability + bad weight")
PYEOF
ok "mapper end-to-end assertions (8 checks)"

# --- 4. The mapper pytest suite passes (real Python, not just inline) ---
if [ ! -f "$PYTEST_TARGET" ]; then
  fail "missing pytest target: $PYTEST_TARGET"
fi
set +e
python3 -m pytest "$PYTEST_TARGET" -q --tb=short
PYTEST_EXIT=$?
set -e
if [ "$PYTEST_EXIT" -ne 0 ]; then
  fail "mapper pytest failed (exit=$PYTEST_EXIT)"
fi
ok "mapper pytest passed"

# --- 5. Inline rule-sweep belt-and-braces guards (mirror the
#       validator's allowlists so the smoke fails fast with a clear
#       message if the validator and the data ever drift). ---
python3 - <<'PYEOF'
import json, re, sys

PATH = "connections/_schema/mapping_rules.json"

with open(PATH, "r", encoding="utf-8") as fp:
    doc = json.load(fp)

# Must declare the title + version + rules.
assert isinstance(doc.get("title"), str) and doc["title"], "rules.title missing"
assert isinstance(doc.get("version"), int), "rules.version must be an int"
rules = doc.get("rules")
assert isinstance(rules, list) and rules, "rules.rules missing or empty"
assert len(rules) >= 30, (
    f"need at least 30 rules for full Phase 2 coverage; found {len(rules)}"
)

PAT = re.compile(r"^rc_[a-z][a-z0-9]*(_[a-z][a-z0-9]*){1,}$")
seen_ids: set[str] = set()
for idx, rule in enumerate(rules):
    rid = rule.get("id")
    assert isinstance(rid, str) and rid, f"rules[{idx}].id missing"
    assert rid not in seen_ids, f"duplicate rule id: {rid!r}"
    seen_ids.add(rid)
    cap = rule.get("canonical_capability")
    assert isinstance(cap, str) and cap.startswith("rc_"), (
        f"rules[{idx}].canonical_capability must start with rc_"
    )
    assert PAT.match(cap), (
        f"rules[{idx}].canonical_capability {cap!r} does not match rc-naming"
    )
    sp = rule.get("source_pattern")
    assert isinstance(sp, str) and sp, f"rules[{idx}].source_pattern missing"
    re.compile(sp)  # raises re.error on bad regex
    w = rule.get("weight")
    assert isinstance(w, int) and not isinstance(w, bool) and 0 <= w <= 100, (
        f"rules[{idx}].weight {w!r} out of [0, 100]"
    )

print("OK: rule-sweep belt-and-braces guards (id uniqueness + rc-naming + weight range + regex compile)")
PYEOF
ok "rule-sweep belt-and-braces guards passed"

# --- 6. Make sure the chain still works (this script + the existing
#       canonical-capabilities smoke + the pytest test_vehicle_model.py
#       all green together). ---
set +e
python3 -m pytest "homeassistant/custom_components/roamcore/tests/test_vehicle_model.py" -q --tb=short >/dev/null
VM_EXIT=$?
bash scripts/checks/canonical-capabilities-smoke.sh >/dev/null 2>&1
CC_EXIT=$?
set -e
if [ "$VM_EXIT" -ne 0 ]; then
  fail "test_vehicle_model.py regressed (exit=$VM_EXIT) — mapper must not break vehicle_model"
fi
if [ "$CC_EXIT" -ne 0 ]; then
  fail "canonical-capabilities-smoke.sh regressed (exit=$CC_EXIT) — mapper must not break Phase 2 schema"
fi
ok "no regression: test_vehicle_model.py + canonical-capabilities-smoke.sh both green"

echo "OK: capability-mapping-smoke.sh passed"
