#!/usr/bin/env bash
# Canonical vehicle model: smoke check
#
# Wave 9 #119 — Phase 2 canonical vehicle model schema (the foundational
# abstraction that every Phase 2 piece builds on). The schema is
# `connections/_schema/canonical_capabilities.json` and is enforced by
# the validator in `homeassistant/custom_components/roamcore/vehicle_model.py`.
#
# Mirrors the convention in scripts/checks/<name>.sh:
#   - bash strict mode (set -euo pipefail)
#   - repo-local only (no live HA / Proxmox / vendor calls)
#   - plain-English summary at exit 0 / non-zero exit
#   - runs the validator pytest + a handful of cheap inline assertions
#
# Exit codes:
#   0  schema is valid, validator is happy, naming rules hold
#   1  JSON parse failed, validator returned errors, a naming rule failed,
#      the capability count dropped below the 12 floor, or a vendor name
#      leaked into a contract id
#
# Wired into scripts/check.sh as a `run_if_present` step.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

SCHEMA="connections/_schema/canonical_capabilities.json"
PYTEST_TARGET="homeassistant/custom_components/roamcore/tests/test_vehicle_model.py"

fail() { echo "ERROR: $*" >&2; exit 1; }

[ -f "$SCHEMA" ] || fail "missing canonical schema file: $SCHEMA"

# --- JSON parseable ---
python3 -c "import json,sys; json.load(open('$SCHEMA','r',encoding='utf-8'))" \
  || fail "JSON parse failed: $SCHEMA"
echo "OK: $SCHEMA parses as JSON"

# --- Validator pytest (real Python, not a smoke assertion) ---
if [ ! -f "$PYTEST_TARGET" ]; then
  fail "missing pytest target: $PYTEST_TARGET"
fi
set +e
python3 -m pytest "$PYTEST_TARGET" -q --tb=short
PYTEST_EXIT=$?
set -e
if [ "$PYTEST_EXIT" -ne 0 ]; then
  fail "validator pytest failed (see output above)"
fi
echo "OK: validator pytest passed"

# --- Inline rule sweeps (cheap belt-and-braces guards that mirror the
#     validator's allowlists so the smoke fails fast with a clear
#     message if the validator and the data ever drift). ---
python3 - <<'PYEOF'
import json, re, sys

PATH = "connections/_schema/canonical_capabilities.json"

with open(PATH, "r", encoding="utf-8") as fp:
    doc = json.load(fp)

# Must declare the title + capability_categories + capabilities.
title = doc.get("title")
assert title == "RoamCore Canonical Vehicle Model", (
    f"unexpected title: {title!r}"
)

cats = doc.get("capability_categories")
assert isinstance(cats, list) and cats, "capability_categories missing or empty"

caps = doc.get("capabilities")
assert isinstance(caps, list) and caps, "capabilities missing or empty"

# At least 12 capabilities (one per the 6 categories minimum).
assert len(caps) >= 12, (
    f"need at least 12 capabilities (one per the 6 minimum categories); "
    f"found {len(caps)}"
)

# Every capability id matches the rc-naming pattern AND has no vendor
# name. Pattern: rc_<subsystem>_<object>_<metric>, lowercase,
# underscore-separated, at least 2 tokens after rc_.
PAT = re.compile(r"^rc_[a-z][a-z0-9]*(_[a-z][a-z0-9]*){1,}$")
VENDOR_TOKENS = (
    "victron", "vt_", "unifi", "ubnt", "starlink", "peplink",
    "teltonika", "frigate", "mqtt", "esphome", "homeassistant", "hass",
)
seen = set()
for idx, cap in enumerate(caps):
    cid = cap.get("id")
    assert isinstance(cid, str), f"capabilities[{idx}].id missing"
    assert PAT.match(cid), (
        f"capabilities[{idx}].id {cid!r} does not match rc-naming pattern"
    )
    lower = cid.lower()
    for vendor in VENDOR_TOKENS:
        assert vendor not in lower, (
            f"capabilities[{idx}].id {cid!r} contains forbidden vendor "
            f"token {vendor!r}"
        )
    assert cid not in seen, f"duplicate capability id: {cid!r}"
    seen.add(cid)
    cat = cap.get("category")
    assert cat in cats, (
        f"capabilities[{idx}].category {cat!r} not in declared "
        f"capability_categories"
    )

# Cross-cutting: every default category is used by at least one
# capability.
seen_cats = {c.get("category") for c in caps}
expected = {"power", "lighting", "climate", "water", "position", "network"}
missing = expected - seen_cats
assert not missing, f"categories with no capabilities: {sorted(missing)}"

print("OK: all capability ids match rc-naming + no vendor tokens")
print("OK: every default category has at least one capability")
PYEOF

echo "OK: canonical-capabilities-smoke.sh passed"
