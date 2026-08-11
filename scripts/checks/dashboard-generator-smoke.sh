#!/usr/bin/env bash
# Canonical vehicle model: dashboard generator smoke check
#
# Wave 9 #119c — Phase 2 auto-generated dashboard. The schema-as-data
# primitive (#119a) + mapping layer (#119b) feed this slice, which
# emits Lovelace YAML from a {canonical_capability_id: vendor_entity_id}
# map. The module is pure stdlib + json so it tests in isolation; the
# pytest rig mirrors test_vehicle_model.py's import-by-file-path
# pattern.
#
# Mirrors the convention in scripts/checks/<name>.sh:
#   - bash strict mode (set -euo pipefail)
#   - repo-local only (no live HA / Proxmox / vendor calls)
#   - plain-English summary at exit 0 / non-zero exit
#   - runs the dashboard-generator pytest + a handful of cheap inline
#     assertions (vendor-neutrality, IKEA doc shape, ≥30 tests)
#
# Exit codes:
#   0  generator is importable, pytest ≥30 tests pass, YAML is valid
#      and vendor-neutral, user-facing doc is IKEA-shaped
#   1  module fails to import, pytest fails, vendor tokens leaked
#      into card names / titles, doc is missing a numbered section,
#      or doc still has forbidden vendor tokens in plain-English copy

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

DG="homeassistant/custom_components/roamcore/dashboard_generator.py"
PYTEST_TARGET="homeassistant/custom_components/roamcore/tests/test_dashboard_generator.py"
DOC="docs/reference/rc-dashboard-generator.md"

fail() { echo "ERROR: $*" >&2; exit 1; }

[ -f "$DG" ] || fail "missing dashboard generator module: $DG"
[ -f "$PYTEST_TARGET" ] || fail "missing pytest target: $PYTEST_TARGET"

# --- Module is importable (pure stdlib + json, no HA imports) ---
python3 -c "
import importlib.util, sys
spec = importlib.util.spec_from_file_location('rc_dg', '$DG')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
# Public surface must be importable.
assert hasattr(mod, 'generate_dashboard_yaml'), 'missing generate_dashboard_yaml'
assert hasattr(mod, 'card_for_capability'), 'missing card_for_capability'
assert hasattr(mod, 'CARD_STYLES'), 'missing CARD_STYLES'
assert hasattr(mod, 'FORBIDDEN_VENDOR_TOKENS'), 'missing FORBIDDEN_VENDOR_TOKENS'
assert hasattr(mod, 'CATEGORY_TO_HEADING'), 'missing CATEGORY_TO_HEADING'
print('OK: dashboard_generator module imports cleanly + public surface present')
"

# --- Pytest (real Python, not a smoke assertion) ---
set +e
python3 -m pytest "$PYTEST_TARGET" -q --tb=short
PYTEST_EXIT=$?
set -e
if [ "$PYTEST_EXIT" -ne 0 ]; then
  fail "dashboard generator pytest failed (see output above)"
fi

# Cheap belt-and-braces guard: pytest must report ≥30 tests.
TEST_COUNT=$(python3 -m pytest "$PYTEST_TARGET" --collect-only -q 2>/dev/null \
  | grep -cE '^homeassistant/custom_components/roamcore/tests/test_dashboard_generator\.py::')
if [ "${TEST_COUNT:-0}" -lt 30 ]; then
  fail "expected ≥30 dashboard-generator tests; found ${TEST_COUNT}"
fi
echo "OK: dashboard generator pytest passed ($TEST_COUNT tests)"

# --- Inline rule sweeps ---
python3 - <<'PYEOF'
import json, sys
sys.path.insert(0, "homeassistant/custom_components/roamcore")

# Import the module by file path so the HA runtime isn't pulled in.
import importlib.util
spec = importlib.util.spec_from_file_location(
    "rc_dg", "homeassistant/custom_components/roamcore/dashboard_generator.py"
)
dg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dg)

SCHEMA = "connections/_schema/canonical_capabilities.json"
with open(SCHEMA, "r", encoding="utf-8") as fp:
    schema = json.load(fp)

# Build a non-trivial capability_map that exercises all 6 categories
# + all four card_style branches.
cap_map = {}
for cap in schema["capabilities"]:
    if cap["type"] != "button":
        cap_map[cap["id"]] = cap["example_sources"][0]
assert len(cap_map) >= 6, "expected ≥6 non-button capabilities"

# --- 1) Determinism: same inputs → byte-identical output ---
out_a = dg.generate_dashboard_yaml(cap_map, schema, card_style="compact")
out_b = dg.generate_dashboard_yaml(cap_map, schema, card_style="compact")
assert out_a == out_b, "generator output is not deterministic"
print("OK: deterministic output (byte-identical for same inputs)")

# --- 2) YAML parses (only when PyYAML is available) ---
try:
    import yaml as _yaml
except ImportError:
    _yaml = None
if _yaml is not None:
    parsed = _yaml.safe_load(out_a)
    assert "vertical-stack" in parsed, "missing vertical-stack root"
    assert isinstance(parsed["vertical-stack"]["cards"], list), "cards must be a list"
    assert len(parsed["vertical-stack"]["cards"]) >= 1, "expected ≥1 populated section"
    print("OK: rendered YAML parses cleanly + has ≥1 populated section")

# --- 3) Vendor-neutral surface (compact + full) ---
# Vendor tokens are banned from card names / titles / icons. They are
# allowed ONLY inside ``entity:`` lines (where the vendor entity id
# identifies the source). The diagnostic style is intentionally NOT
# vendor-neutral — it surfaces the ids for the Advanced mode.
forbidden = (
    "victron", "vt_", "unifi", "ubnt", "starlink", "dish_",
    "peplink", "teltonika", "rut_", "frigate", "mqtt", "esphome",
    "homeassistant", "hass",
)
for style in ("compact", "full"):
    out = dg.generate_dashboard_yaml(cap_map, schema, card_style=style)
    for line in out.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith("- entity:") or stripped.startswith("entity:"):
            continue  # vendor entity ids are allowed here
        low = line.lower()
        for tok in forbidden:
            assert tok not in low, (
                f"[{style}] forbidden vendor token {tok!r} leaked into "
                f"non-entity line: {line!r}"
            )
print("OK: vendor-neutral surface (compact + full)")

# --- 4) Empty capability_map → placeholder, not crash ---
out_empty = dg.generate_dashboard_yaml({}, schema)
assert isinstance(out_empty, str) and out_empty, "empty map returned empty string"
assert "vertical-stack" in out_empty, "empty map output missing vertical-stack"
print("OK: empty capability_map returns valid placeholder")

# --- 5) Buttons are NOT surfaced on the auto-generated dashboard ---
doc_with_button = {
    "capability_categories": ["power"],
    "capabilities": [{
        "id": "rc_power_button_test", "category": "power", "kind": "control",
        "type": "button", "description": "test button",
    }],
}
out_btn = dg.generate_dashboard_yaml(
    {"rc_power_button_test": "button.foo"}, doc_with_button
)
# The button card must be filtered out → only the placeholder.
assert "no capabilities mapped yet" in out_btn, (
    "button was rendered on the auto-generated dashboard (must be hidden)"
)
print("OK: buttons are HIDDEN from the auto-generated dashboard")

# --- 6) Card name derives from description, NOT from the canonical id ---
doc_one = {
    "capability_categories": ["power"],
    "capabilities": [{
        "id": "rc_power_internal_id_must_not_leak",
        "category": "power", "kind": "telemetry", "type": "sensor",
        "device_class": "battery", "description": "Friendly user-facing label",
    }],
}
out_one = dg.generate_dashboard_yaml(
    {"rc_power_internal_id_must_not_leak": "sensor.foo"}, doc_one,
    card_style="compact",
)
for line in out_one.split("\n"):
    stripped = line.lstrip()
    if stripped.startswith("- entity:") or stripped.startswith("entity:"):
        continue
    assert "rc_power_internal_id_must_not_leak" not in line, (
        f"canonical id leaked into non-entity line: {line!r}"
    )
assert "Friendly user-facing label" in out_one
print("OK: card names derived from descriptions (vanlifer language)")

# --- 7) rc-entity-naming honoured: icons all mdi:-prefixed ---
import re
icon_lines = [
    line for line in out_a.split("\n")
    if re.match(r"\s*icon:\s", line)
]
assert icon_lines, "expected at least one icon: line"
for line in icon_lines:
    icon = line.split(":", 1)[1].strip()
    assert icon.startswith("mdi:"), f"icon is not mdi:-prefixed: {line!r}"
print(f"OK: rc-entity-naming honoured — {len(icon_lines)} icons all mdi:-prefixed")
PYEOF

# --- User-facing doc must be IKEA-shaped + jargon-free ---
if [ ! -f "$DOC" ]; then
  fail "missing user-facing doc: $DOC"
fi
DOC_SECTIONS=$(grep -cE '^## §[1-5] ' "$DOC" || true)
if [ "${DOC_SECTIONS:-0}" -lt 5 ]; then
  fail "user-facing doc $DOC has fewer than 5 numbered sections (IKEA shape): found ${DOC_SECTIONS:-0}"
fi
echo "OK: $DOC has 5 numbered sections (IKEA shape)"

# Jargon check: the user-facing copy must not contain forbidden
# operator tokens in §1-§4 (the vanlifer-facing body). §5 may carry
# a translation table that mentions these tokens by name (that's
# the explicit job of the translation table — to map operator terms
# to vanlifer terms). The translation table at the bottom of the
# doc is the explicit carve-out.
#
# We extract the §1-§4 body with awk so the check is exact (the
# line-based grep -A 200 overcounts).
BODY_1_TO_4=$(awk '
  /^## §1 / { in_body = 1; next }
  /^## §5 / { in_body = 0 }
  in_body { print }
' "$DOC")

JARGON_TOKENS=(
  "entity_id"
  "Lovelace"
  "yaml"
  "tap_action"
  "binary_sensor"
)
for tok in "${JARGON_TOKENS[@]}"; do
  if echo "$BODY_1_TO_4" | grep -q -- "$tok"; then
    case "$tok" in
      "yaml")
        # Tolerated in the prose ("never touch a YAML file") — the
        # translation table explicitly maps yaml → "settings file".
        ;;
      *)
        fail "user-facing doc body (§1-§4) contains jargon token: $tok"
        ;;
    esac
  fi
done
echo "OK: user-facing doc body (§1-§4) is jargon-free"

# Forbidden vendor tokens must not appear in the user-facing copy at
# all (vanlifer-language doc never mentions brands).
for tok in victron starlink peplink teltonika frigate vt_ unifi; do
  if grep -qi -- "$tok" "$DOC"; then
    fail "user-facing doc mentions forbidden vendor token: $tok"
  fi
done
echo "OK: user-facing doc is vendor-neutral"

# PR numbers, branch names, "Wave N" labels, "tier-X", "the cron" /
# "the sub-agent" jargon must not appear in the user-facing doc.
for jargon in "Wave " "tier-" "PR #" "PRs" "the cron" "the sub-agent" "lint-pass" "Apple-grade"; do
  if grep -q -- "$jargon" "$DOC"; then
    fail "user-facing doc contains jargon: $jargon"
  fi
done
echo "OK: user-facing doc has no jargon (Wave / tier-X / PR / cron / sub-agent)"

echo "OK: dashboard-generator-smoke.sh passed"
