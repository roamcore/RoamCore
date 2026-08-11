#!/usr/bin/env bash
# Capability mapping (Phase 2 mapping layer — Wave 9 #119b): smoke check
#
# Verifies the vendor-entity → canonical-capability mapping layer:
#   - the module file parses (Python AST check)
#   - the optional mapping-rules JSON file parses + validates shape
#   - the pytest rig passes (real Python test, not a stub)
#   - the produced canonical map contains no vendor tokens (rc-naming
#     compliance)
#   - the IKEA-style user doc exists + has the 5-step shape
#
# Mirrors the convention in scripts/checks/<name>.sh:
#   - bash strict mode (set -euo pipefail)
#   - repo-local only (no live HA / Proxmox / vendor calls)
#   - plain-English summary at exit 0 / non-zero exit
#   - runs the validator pytest + a handful of cheap inline assertions
#
# Exit codes:
#   0  mapping module is healthy, pytest passes, rc-naming holds,
#      user doc has the 5 IKEA steps, no vendor tokens leak
#   1  anything failed (JSON parse, pytest, naming, doc shape)
#
# Wired into scripts/check.sh as a `run_if_present` step.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

MODULE="homeassistant/custom_components/roamcore/capability_mapping.py"
PYTEST_TARGET="homeassistant/custom_components/roamcore/tests/test_capability_mapping.py"
RULES="connections/_schema/capability_mapping_rules.json"
SCHEMA="connections/_schema/canonical_capabilities.json"
DOC="docs/reference/rc-capability-mapping.md"

fail() { echo "ERROR: $*" >&2; exit 1; }

[ -f "$MODULE" ] || fail "missing mapping module: $MODULE"
[ -f "$PYTEST_TARGET" ] || fail "missing pytest target: $PYTEST_TARGET"
[ -f "$SCHEMA" ] || fail "missing canonical schema: $SCHEMA"
[ -f "$DOC" ] || fail "missing IKEA user doc: $DOC"

# --- Module parses as valid Python (AST compile) ---
python3 -c "
import ast, sys
with open('$MODULE', 'r', encoding='utf-8') as fp:
    ast.parse(fp.read(), filename='$MODULE')
" || fail "mapping module does not parse as Python: $MODULE"
echo "OK: mapping module parses as Python"

# --- Rules JSON parses + validates ---
python3 -c "
import json, sys
with open('$RULES', 'r', encoding='utf-8') as fp:
    d = json.load(fp)
assert isinstance(d, dict), 'rules file top-level must be a JSON object'
assert isinstance(d.get('rules'), list), 'rules file must contain a rules list'
assert d['rules'], 'rules list must be non-empty'
for idx, rule in enumerate(d['rules']):
    assert isinstance(rule, dict), f'rules[{idx}] must be a JSON object'
    assert rule.get('vendor_entity_id_pattern'), f'rules[{idx}] missing vendor_entity_id_pattern'
    assert rule.get('canonical_id'), f'rules[{idx}] missing canonical_id'
print(f'OK: rules file parses with {len(d[\"rules\"])} rules')
"

# --- Pytest rig (real Python tests) ---
set +e
python3 -m pytest "$PYTEST_TARGET" -q --tb=short
PYTEST_EXIT=$?
set -e
if [ "$PYTEST_EXIT" -ne 0 ]; then
  fail "mapping pytest failed (see output above)"
fi
echo "OK: mapping pytest passed"

# --- Inline rc-naming + vendor-token sweep ---
# Replays the cross-cutting guard from the pytest rig but against the
# RULES file on disk (so the smoke fails fast with a clear message if
# the rules file ever drifts out of compliance, even between pytest
# runs). Same forbidden-vendor-token list as vehicle_model.py +
# capability_mapping.py — kept in sync via the test suite.
python3 - <<'PYEOF'
import json, re

RULES = "connections/_schema/capability_mapping_rules.json"
SCHEMA = "connections/_schema/canonical_capabilities.json"

with open(RULES, "r", encoding="utf-8") as fp:
    rules_doc = json.load(fp)
with open(SCHEMA, "r", encoding="utf-8") as fp:
    caps_doc = json.load(fp)

VENDOR_TOKENS = (
    "victron", "vt_", "unifi", "ubnt", "starlink", "peplink",
    "teltonika", "frigate", "mqtt", "esphome", "homeassistant", "hass",
)
ID_PATTERN = re.compile(r"^rc_[a-z][a-z0-9]*(_[a-z][a-z0-9]*){1,}$")

# Every rule canonical_id must follow rc-naming + have no vendor token.
errors = []
for idx, rule in enumerate(rules_doc["rules"]):
    cid = rule["canonical_id"]
    if not cid.startswith("rc_"):
        errors.append(f"rules[{idx}].canonical_id {cid!r} must start with rc_")
    if not ID_PATTERN.match(cid):
        errors.append(f"rules[{idx}].canonical_id {cid!r} does not match rc-naming")
    lower = cid.lower()
    for vendor in VENDOR_TOKENS:
        if vendor in lower:
            errors.append(
                f"rules[{idx}].canonical_id {cid!r} contains forbidden "
                f"vendor token {vendor!r}"
            )

# Every rule's canonical_id must be a real capability in the schema.
known_caps = {c["id"] for c in caps_doc["capabilities"]}
for idx, rule in enumerate(rules_doc["rules"]):
    cid = rule["canonical_id"]
    if cid not in known_caps:
        errors.append(
            f"rules[{idx}].canonical_id {cid!r} not declared in "
            "canonical_capabilities.json"
        )

# Cross-cutting: every category in the canonical schema has at least
# one explicit rule OR at least one example_source.
categories_with_any_signal: set[str] = set()
for rule in rules_doc["rules"]:
    cap = next((c for c in caps_doc["capabilities"] if c["id"] == rule["canonical_id"]), None)
    if cap:
        categories_with_any_signal.add(cap["category"])
for cap in caps_doc["capabilities"]:
    if cap.get("example_sources"):
        categories_with_any_signal.add(cap["category"])

expected_categories = {"power", "lighting", "climate", "water", "position", "network"}
missing = expected_categories - categories_with_any_signal
if missing:
    errors.append(
        f"categories with NO explicit rule AND NO example_source: "
        f"{sorted(missing)} (every default category must be reachable)"
    )

if errors:
    print("FAIL: rc-naming / vendor-token / category-coverage errors:")
    for e in errors:
        print(f"  - {e}")
    raise SystemExit(1)

print("OK: all mapping rules pass rc-naming + no vendor tokens + canonical IDs exist")
print(f"OK: every default category is reachable (rule or example_source)")
PYEOF

# --- End-to-end rc-naming sweep: import the module and run the canonical
#     map against the shipped schema + rules; assert every produced key
#     follows rc-naming. ---
python3 - <<'PYEOF'
import importlib.util, json, os, sys

REPO_ROOT = os.environ.get("REPO_ROOT") or os.getcwd()
MODULE = os.path.join(
    REPO_ROOT,
    "homeassistant", "custom_components", "roamcore",
    "capability_mapping.py",
)
spec = importlib.util.spec_from_file_location("cm", MODULE)
assert spec and spec.loader
cm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cm)

with open(os.path.join(REPO_ROOT, "connections/_schema/canonical_capabilities.json"), "r", encoding="utf-8") as fp:
    caps_doc = json.load(fp)
with open(os.path.join(REPO_ROOT, "connections/_schema/capability_mapping_rules.json"), "r", encoding="utf-8") as fp:
    rules_doc = json.load(fp)

# A typical van setup.
entities = {
    "sensor.vt_battery_soc_percent": {},
    "sensor.vt_battery_voltage_v": {},
    "sensor.vt_battery_current_a": {},
    "sensor.vt_solar_power_w": {},
    "binary_sensor.vt_shore_connected": {},
    "sensor.dish_signal_quality": {},
    "sensor.pep_wan_ip": {},
    "sensor.rut_signal_strength": {},
    "switch.cabin_main": {},
    "switch.porch_light": {},
    "sensor.indoor_temp": {},
    "switch.hvac_main": {},
    "sensor.fresh_water_tank_level": {},
    "switch.water_pump": {},
    "sensor.battery_state": {},  # example_sources
}
canonical_map = cm.build_capability_map(entities, rules_doc, caps_doc)
assert canonical_map, "expected non-empty canonical map for typical van setup"

VENDOR_TOKENS = cm.FORBIDDEN_VENDOR_TOKENS
import re
ID_PATTERN = re.compile(r"^rc_[a-z][a-z0-9]*(_[a-z][a-z0-9]*){1,}$")
for cid in canonical_map.keys():
    assert cid.startswith("rc_"), f"key {cid!r} does not start with rc_"
    assert ID_PATTERN.match(cid), f"key {cid!r} does not match rc-naming"
    lower = cid.lower()
    for vendor in VENDOR_TOKENS:
        assert vendor not in lower, f"key {cid!r} leaks vendor token {vendor!r}"

print(f"OK: end-to-end canonical map has {len(canonical_map)} keys, all rc_-prefixed + no vendor tokens")
PYEOF

# --- IKEA 5-step shape on the user doc ---
python3 - <<'PYEOF'
with open("docs/reference/rc-capability-mapping.md", "r", encoding="utf-8") as fp:
    doc = fp.read()

required_steps = [
    "§1 What it does",
    "§2 What you see",
    "§3 What you do",
    "§4 What to do if it goes wrong",
    "§5 Useful links",
]
for step in required_steps:
    assert step in doc, f"IKEA doc missing required step: {step!r}"
print("OK: IKEA doc has all 5 required steps")
PYEOF

echo "OK: capability-mapping-smoke.sh passed"