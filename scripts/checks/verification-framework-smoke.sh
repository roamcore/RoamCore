#!/usr/bin/env bash
# Post-install verification framework: smoke check
#
# Wave 9 #119d — Phase 2 canonical vehicle model VERIFICATION
# FRAMEWORK (sibling slice to #119b mapping layer + #119c dashboard
# generator, all three consuming the #119a schema primitive).
#
# The framework is a pure-Python module (`verification.py`) + pytest
# rig (`test_verification.py`) that turns "the tile is on the screen"
# into "the tile is showing REAL DATA that we just verified" — per
# Directive Rule 4 ("Don't mark successful if automated action can't
# be verified"). This smoke asserts:
#
#   * verification.py + test_verification.py exist on disk
#   * the module is pure stdlib + json (no HA imports — the
#     canonical pattern)
#   * the pytest rig reports >= 30 tests, all PASS
#   * the IKEA-shaped user-facing doc exists with the 5-step shape
#   * the user-facing doc contains NO forbidden operator-speak
#   * the rc-entity-naming rule is honoured (every rc_* id in the
#     module + tests starts with rc_ and contains no vendor tokens)
#   * every reason/recovery_hint string the framework emits passes
#     the operator->vanlifer translation table
#
# Mirrors the convention in scripts/checks/<name>.sh:
#   - bash strict mode (set -euo pipefail)
#   - repo-local only (no live HA / Proxmox / vendor calls)
#   - plain-English summary at exit 0 / non-zero exit
#   - chained as a run_if_present step from scripts/check.sh
#
# Exit codes:
#   0  verification framework is healthy
#   1  module missing / fails to import / pytest failed / doc missing
#      / rc-naming violated / operator jargon leaked into user copy

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

MODULE="homeassistant/custom_components/roamcore/verification.py"
PYTEST_TARGET="homeassistant/custom_components/roamcore/tests/test_verification.py"
USER_DOC="docs/reference/rc-verification.md"

fail() { echo "ERROR: $*" >&2; exit 1; }

[ -f "$MODULE" ] || fail "missing verification module: $MODULE"
[ -f "$PYTEST_TARGET" ] || fail "missing pytest rig: $PYTEST_TARGET"
[ -f "$USER_DOC" ] || fail "missing user-facing doc: $USER_DOC"

# --- Module parses as Python + is pure-stdlib ---
python3 -c "
import ast
with open('$MODULE', 'r', encoding='utf-8') as fp:
    tree = ast.parse(fp.read(), filename='$MODULE')
print('OK: $MODULE parses as valid Python')
"

# --- Module is pure stdlib + json (no HA imports) ---
python3 - <<PYEOF
import ast, sys
with open('$MODULE', 'r', encoding='utf-8') as fp:
    tree = ast.parse(fp.read(), filename='$MODULE')

ALLOWED_MODULES = {
    '__future__', 'annotations',
    'ast', 'dataclasses', 'importlib', 'json', 'os',
    're', 'sys', 'time', 'typing',
}

bad_imports: list[str] = []
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        for alias in node.names:
            top = alias.name.split('.')[0]
            if top not in ALLOWED_MODULES:
                bad_imports.append(alias.name)
    elif isinstance(node, ast.ImportFrom):
        if node.module is None or node.level > 0:
            # Relative imports (level > 0) are forbidden in pure-stdlib.
            bad_imports.append(f"relative import: {node.module}")
        else:
            top = node.module.split('.')[0]
            if top not in ALLOWED_MODULES:
                bad_imports.append(node.module)

if bad_imports:
    print(f"ERROR: $MODULE has non-stdlib imports: {bad_imports}", file=sys.stderr)
    sys.exit(1)
print("OK: $MODULE uses only stdlib + json (no HA imports)")
PYEOF

# --- Pytest rig: >= 30 tests, all PASS ---
set +e
python3 -m pytest "$PYTEST_TARGET" -q --tb=short
PYTEST_EXIT=$?
set -e
if [ "$PYTEST_EXIT" -ne 0 ]; then
  fail "verification pytest failed (see output above)"
fi

TEST_COUNT=$(python3 -m pytest "$PYTEST_TARGET" --collect-only -q 2>/dev/null | tail -1 | awk '{print $1}')
if [ -z "$TEST_COUNT" ] || [ "$TEST_COUNT" -lt 30 ]; then
  fail "verification pytest collected $TEST_COUNT tests; spec requires >= 30"
fi
echo "OK: verification pytest passed ($TEST_COUNT tests)"

# --- rc-entity-naming rule honoured in source ---
# Two checks:
#   1. Every canonical id in the SHIPPED schema (`canonical_capabilities.json`)
#      is well-formed + free of vendor tokens. This is the ground truth
#      for what canonical ids exist.
#   2. Every canonical id that flows through the framework at runtime
#      (i.e. as a string-literal argument in `test_verification.py`,
#      OUTSIDE the test fixtures that intentionally use bad ids) is
#      well-formed + free of vendor tokens.
python3 - <<'PYEOF'
import json, re, sys

VENDOR_TOKENS = (
    "victron", "vt_", "unifi", "ubnt", "starlink", "peplink",
    "teltonika", "frigate", "mqtt", "esphome", "homeassistant", "hass",
)
PAT = re.compile(r"^rc_[a-z][a-z0-9]*(_[a-z][a-z0-9]*){1,}$")

def check(cid: str, where: str) -> None:
    if not PAT.match(cid):
        print(f"ERROR: {where} {cid!r} does not match rc-naming pattern", file=sys.stderr)
        sys.exit(1)
    lower = cid.lower()
    for vendor in VENDOR_TOKENS:
        if vendor in lower:
            print(f"ERROR: {where} {cid!r} contains forbidden vendor token {vendor!r}", file=sys.stderr)
            sys.exit(1)

# --- 1. Shipped schema is the ground truth ---
with open("connections/_schema/canonical_capabilities.json", "r", encoding="utf-8") as fp:
    schema = json.load(fp)
schema_ids = [c["id"] for c in schema["capabilities"]]
for cid in schema_ids:
    check(cid, "schema")
print(f"OK: rc-naming + no-vendor-tokens held for {len(schema_ids)} schema canonical ids")

# --- 2. Test rig: any string-literal `capability_id="rc_..."` is well-formed.
# We deliberately skip fixture strings inside the `for bad in (...)` tuples
# in `test_assert_no_vendor_tokens_rejects_known_vendors` — those are
# crafted to be bad (it's a rejection test).
with open("homeassistant/custom_components/roamcore/tests/test_verification.py", "r", encoding="utf-8") as fp:
    test_src = fp.read()

# Find every `capability_id="rc_..."` or `capability_id='rc_...'` occurrence.
# These are the ids that flow through verify_connection at runtime.
runtime_ids = re.findall(r'capability_id\s*=\s*["\'](rc_[a-z][a-z0-9_]+)["\']', test_src)
runtime_ids = list(set(runtime_ids))

for cid in runtime_ids:
    check(cid, "test rig runtime id")

print(f"OK: rc-naming + no-vendor-tokens held for {len(runtime_ids)} runtime test rig ids")
PYEOF

# --- User-facing IKEA doc: 5-step shape + no forbidden operator-speak ---
python3 - <<'PYEOF'
import re, sys

PATH = "docs/reference/rc-verification.md"
with open(PATH, "r", encoding="utf-8") as fp:
    text = fp.read()

# §1..§5 must be present (numbered or named). IKEA convention in
# this repo uses "## §1" / "## 1." / "## 1)" style.
section_pattern = re.compile(
    r"^##\s+(?:§\s*)?\d+",
    re.MULTILINE,
)
sections = section_pattern.findall(text)
if len(sections) < 5:
    print(
        f"ERROR: IKEA doc needs at least 5 numbered sections, found {len(sections)}",
        file=sys.stderr,
    )
    sys.exit(1)
print(f"OK: IKEA doc has {len(sections)} numbered sections (>= 5 required)")

# Forbidden operator-speak (per the operator->vanlifer table).
# We scan everything EXCEPT the translation table at the bottom of
# the doc (which is the canonical place where operator-speak words
# appear verbatim in order to translate them — that's the table's
# whole purpose, per the discipline block).
FORBIDDEN = [
    "entity id", "entity_id", "integration",
    "hacs", "lovelace", "automation", "script",
    "service call", "mdns", "zeroconf", "mqtt",
    "tailscale", "failover", "api key", "access code",
    "dashboard tile",
    "wave 9", "wave9", "sub-agent", "subagent",
    "the cron", "apple-grade", "lint-pass",
    "tier-a", "tier-b", "tier-c",
    "roamcore native",
]

# Find the start of the translation table (the section that
# starts with "## §5 Useful links" or contains "Operator" header).
# Everything from that marker onward is excluded from the jargon sweep.
TABLE_MARKERS = (
    "## §5 Useful links",
    "## Useful links",
    "Operator → vanlifer",
    "Operator -> vanlifer",
)

scan_text = text
for marker in TABLE_MARKERS:
    idx = scan_text.find(marker)
    if idx != -1:
        scan_text = scan_text[:idx]
        break

found: list[tuple[str, str]] = []
for line in scan_text.splitlines():
    low = line.lower()
    for tok in FORBIDDEN:
        if tok in low:
            if line.strip().startswith("```"):
                continue
            found.append((tok, line.strip()))

if found:
    print("ERROR: user-facing doc contains forbidden operator-speak:", file=sys.stderr)
    for tok, line in found[:10]:
        print(f"  {tok!r} in: {line}", file=sys.stderr)
    sys.exit(1)
print("OK: user-facing doc is jargon-free (operator->vanlifer table honored)")
PYEOF

# --- reason / recovery_hint strings pass anti-slop guard ---
python3 - <<'PYEOF'
import importlib.util, sys

MODULE_PATH = "homeassistant/custom_components/roamcore/verification.py"

# Load verification.py by file path so we don't pull in HA imports.
spec = importlib.util.spec_from_file_location("roamcore_verification_smoke", MODULE_PATH)
assert spec is not None and spec.loader is not None
m = importlib.util.module_from_spec(spec)
sys.modules["roamcore_verification_smoke"] = m
spec.loader.exec_module(m)

import json
with open("connections/_schema/canonical_capabilities.json", "r", encoding="utf-8") as fp:
    doc = json.load(fp)

import time
now = time.time()

# Trigger every failure mode and capture its strings.
scenarios = [
    # (label, target)
    ("range", m.VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=[(now - 5, 150.0)],
    )),
    ("stale", m.VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=[(now - 600, 80.0)],
    )),
    ("no_data", m.VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=[],
    )),
    ("jump", m.VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=[(now, 0.0), (now + 1, 100.0)],
    )),
    ("restart_fail", m.VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.vt_battery_soc_percent",
        sample_history=[(now - 30, 80.0)],
        connection_metadata={"restart_count": 1, "last_disconnect_at": now - 1},
    )),
    ("vendor_fail", m.VerificationTarget(
        capability_id="rc_power_battery_soc",
        entity_id="sensor.unifi_random_thing",
        sample_history=[(now - 5, 80.0)],
    )),
]

FORBIDDEN = (
    "entity", "integration", "hacs", "lovelace",
    "automation", "script", "service call",
    "mdns", "zeroconf", "mqtt", "tailscale",
    "failover", "api key", "access code",
)

bad: list[str] = []
for label, target in scenarios:
    res = m.verify_connection(target, doc)
    for field_name, val in (("reason", res.reason), ("recovery_hint", res.recovery_hint)):
        if val is None:
            continue
        low = val.lower()
        for tok in FORBIDDEN:
            if tok in low:
                bad.append(f"{label}.{field_name} contains {tok!r}: {val!r}")

if bad:
    print("ERROR: framework strings fail operator->vanlifer translation:", file=sys.stderr)
    for b in bad:
        print(f"  {b}", file=sys.stderr)
    sys.exit(1)
print(f"OK: all {len(scenarios)} failure-mode strings pass the anti-slop guard")
PYEOF

echo "OK: verification-framework-smoke.sh passed"
