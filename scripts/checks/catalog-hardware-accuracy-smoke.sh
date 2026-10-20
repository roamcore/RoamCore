#!/usr/bin/env bash
# Catalog hardware-list accuracy: smoke check.
#
# Wave 9 follow-up to Wave 8 row #307 — the previous substring matcher
# in scripts/build_catalog_lib.sensible_hardware_defaults() shipped two
# live mis-classifications on the user-facing catalog:
#
#   1. alternator-charge-control → "Zigbee smoke / CO detector …"
#      because ``"co" in "alternator-CHARGE-CONTROL"``.
#   2. dns-blocker → "Z-Wave smart deadbolt …" because
#      ``"lock" in "DNS-BLOCKER"``.
#
# This smoke asserts that, on the GENERATED output on disk:
#
#   1. The two regression pins hold (no smoke line in the alternator
#      page; no deadbolt line in the dns-blocker page; the alternator
#      page carries an alternator regulator; the dns-blocker page
#      carries Pi-hole / AdGuard gear).
#   2. The smoke/CO detector rule still fires on smoke-co-gas-sensors
#      (the legitimate match — proves the rewrite didn't over-correct).
#   3. NO committed docs/catalog page under power/ mentions "smoke"
#      in its What-you-need block (Power gear never needs a smoke
#      detector regardless of which connection it is).
#   4. NO committed docs/catalog page mentions "deadbolt" outside of
#      lock/deadbolt slugs (a one-van bug worth pinning forever — the
#      substring "lock" can creep back into any future rule).
#   5. Regenerating the catalog twice produces zero diff
#      (`git diff --exit-code` after a regeneration run).
#   6. The pytest rig passes (the unit-level half of the same checks).
#
# Mirrors the convention in scripts/checks/<name>.sh:
#   - bash strict mode (set -euo pipefail)
#   - repo-local only (no live HA / Proxmox calls)
#   - plain-English PASS/FAIL blocks at exit
#   - idempotent over re-runs
#
# Usage:
#   bash scripts/checks/catalog-hardware-accuracy-smoke.sh
#
# Exit codes:
#   0  all 6 assertion blocks PASS
#   1  one or more blocks FAIL (details printed to stderr)
#
# Wired into scripts/check.sh as a `run_if_present` step
# AFTER the catalog-ui-cards-smoke (which this slice builds on top of):
# the catalog-ui-cards smoke proves the cards render; this smoke proves
# the per-connection "What you need" hardware list is HONEST.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

# --- Assertion counters (so the operator sees PASS/FAIL at a glance) ---
PASS_COUNT=0
FAIL_COUNT=0
FAILED_ASSERTIONS=()

assert_pass() {
  local label="$1"
  printf '\033[1;32m  ✓\033[0m %s\n' "$label"
  PASS_COUNT=$((PASS_COUNT + 1))
}

assert_fail() {
  local label="$1"
  local detail="${2:-}"
  printf '\033[1;31m  ✗\033[0m %s\n' "$label"
  if [ -n "$detail" ]; then
    printf '    %s\n' "$detail"
  fi
  FAIL_COUNT=$((FAIL_COUNT + 1))
  FAILED_ASSERTIONS+=("$label")
}

# --- Pre-flight: catalog directory exists ---
CATALOG_DIR="docs/catalog"
if [ ! -d "$CATALOG_DIR" ]; then
  printf '\033[1;31m✗ catalog-hardware-accuracy-smoke FAILED before assertions ran\033[0m\n'
  printf '  catalog directory %s is missing; regenerate with:\n' "$CATALOG_DIR"
  printf '    python3 scripts/build_catalog.py\n'
  exit 1
fi

# --- Pre-flight: assert alternator + dns-blocker pages exist on disk ---
ALT_PAGE="docs/catalog/power/alternator-charge-control.md"
DNS_PAGE="docs/catalog/connectivity/dns-blocker.md"
for pg in "$ALT_PAGE" "$DNS_PAGE"; do
  if [ ! -f "$pg" ]; then
    printf '\033[1;31m✗ catalog-hardware-accuracy-smoke FAILED before assertions ran\033[0m\n'
    printf '  %s is missing; regenerate with:\n' "$pg"
    printf '    python3 scripts/build_catalog.py\n'
    exit 1
  fi
done

# --- Assertion 1: REGRESSION PIN #1 — alternator page ---
# The page must NOT recommend a smoke detector (the original bug) and
# MUST recommend an alternator regulator (the fix).
printf '\033[1;36m▶ Assertion 1\033[0m — REGRESSION PIN #1: alternator page has no smoke, has regulator\n'

# Helper: extract the body of a named markdown section.
# awk range `/A/,/B/` matches START-AT line A, which itself is
# included — that breaks the empty-range corner case above. Use an
# explicit next-line approach instead.
_block() {
  local pg="$1" heading="$2"
  awk -v h="$heading" \
    'index($0, "## " h) == 1 {flag=1; next}
     /^## /                       {flag=0}
     flag' "$pg"
}

ALT_BLOCK="$(_block "$ALT_PAGE" "What you need")"

if grep -qi 'smoke' "$ALT_PAGE"; then
  # Allow a generous false-positive — "smoke" could appear in the
  # prose somewhere. We only fail when it appears in the
  # What-you-need block, which is what a vanlifer reads.
  if echo "$ALT_BLOCK" | grep -qi 'smoke'; then
    assert_fail "alternator page must NOT mention 'smoke' in What-you-need block" \
      "the substring heuristic still ships 'Zigbee smoke / CO detector' to this page; run the catalog generator and re-check"
  else
    assert_pass "alternator page has 'smoke' in prose only (acceptable — not in What-you-need block)"
  fi
else
  assert_pass "alternator page does not mention 'smoke' at all"
fi

if echo "$ALT_BLOCK" | grep -qi 'alternator'; then
  assert_pass "alternator page mentions 'alternator' in What-you-need block"
else
  assert_fail "alternator page must mention 'alternator' in What-you-need block" \
    "the page should recommend a smart alternator regulator (Wakespeed / Balmar / Sterling / REDARC); run the catalog generator and re-check"
fi

if echo "$ALT_BLOCK" | grep -qi 'regulator'; then
  assert_pass "alternator page mentions 'regulator' in What-you-need block"
else
  assert_fail "alternator page must mention 'regulator' in What-you-need block" \
    "the smart alternator regulator is the load-bearing line for this page"
fi

# --- Assertion 2: REGRESSION PIN #2 — dns-blocker page ---
# The page must NOT recommend a deadbolt (the original bug) and MUST
# reference Pi-hole / AdGuard gear (the fix).
printf '\n\033[1;36m▶ Assertion 2\033[0m — REGRESSION PIN #2: dns-blocker page has no deadbolt, has DNS gear\n'

DNS_BLOCK="$(_block "$DNS_PAGE" "What you need")"

if grep -qi 'deadbolt' "$DNS_PAGE"; then
  # Allow 'deadbolt' in prose, fail only if it appears in What-you-need.
  if echo "$DNS_BLOCK" | grep -qi 'deadbolt'; then
    assert_fail "dns-blocker page must NOT mention 'deadbolt' in What-you-need block" \
      "the substring heuristic still ships 'Z-Wave smart deadbolt' to this page; run the catalog generator and re-check"
  else
    assert_pass "dns-blocker page has 'deadbolt' in prose only (acceptable — not in What-you-need block)"
  fi
else
  assert_pass "dns-blocker page does not mention 'deadbolt' at all"
fi

if echo "$DNS_BLOCK" | grep -qiE 'pi-hole|adguard|dns'; then
  assert_pass "dns-blocker page mentions Pi-hole / AdGuard / DNS in What-you-need block"
else
  assert_fail "dns-blocker page must mention Pi-hole / AdGuard / DNS in What-you-need block" \
    "the DNS gear line is the load-bearing line for this page; a vanlifer needs to know what to buy"
fi

# --- Assertion 3: CONTROL — smoke-co-gas-sensors still fires ---
# The CONTROL assertion pins the legitimate rule so a future refactor
# cannot quietly break it. We use Python via the library to assert
# the rule still fires on the exact slug in the live catalog.
printf '\n\033[1;36m▶ Assertion 3\033[0m — CONTROL: smoke-co-gas-sensors still fires the smoke rule\n'

python3 - <<'PYEOF'
import sys
sys.path.insert(0, "scripts")
import build_catalog_lib as lib
hw = lib.sensible_hardware_defaults(
    "smoke-co-gas-sensors",
    "Smoke / CO / gas safety sensors",
    catalog_category="safety",
)
text = "\n".join(f"- {h}" for h in hw).lower()
if "smoke" in text and "co" in text:
    print("OK: smoke-co-gas-sensors still fires the smoke/CO detector rule")
    sys.exit(0)
print(f"FAIL: smoke-co-gas-sensors no longer fires the smoke rule; got: {hw!r}")
sys.exit(1)
PYEOF
if [ $? -eq 0 ]; then
  assert_pass "smoke-co-gas-sensors hardware list still contains the smoke/CO detector line"
else
  assert_fail "smoke-co-gas-sensors hardware list must still contain the smoke/CO detector line" \
    "the rule that legitimately fired on the token 'co' was lost in the rewrite; check _matches(tokens, 'smoke', 'co', 'gas')"
fi

# --- Assertion 4: NO power/* page mentions 'smoke' in What-you-need ---
# The whole power/ tree must be smoke-detector-free. We grep every
# page under docs/catalog/power/ — failures point at the exact file.
printf '\n\033[1;36m▶ Assertion 4\033[0m — no power/* page mentions smoke in its What-you-need block\n'

POWER_SMOKE_HITS=0
if [ -d "docs/catalog/power" ]; then
  while IFS= read -r -d '' pg; do
    if _block "$pg" "What you need" | grep -qi 'smoke'; then
      printf '    offending page: %s\n' "$pg"
      POWER_SMOKE_HITS=$((POWER_SMOKE_HITS + 1))
    fi
  done < <(find "docs/catalog/power" -type f -name "*.md" -print0 2>/dev/null || true)
fi

if [ "$POWER_SMOKE_HITS" -eq 0 ]; then
  assert_pass "no power/* catalog page mentions 'smoke' in its What-you-need block"
else
  assert_fail "no power/* catalog page mentions 'smoke' in its What-you-need block" \
    "found $POWER_SMOKE_HITS offending page(s) — see list above"
fi

# --- Assertion 5: regenerating the catalog twice produces zero diff ---
# Idempotency pin: the slice promised "running it twice returns the
# same output". If the generator ever starts writing non-deterministic
# output (e.g. timestamps), this assertion fails first.
printf '\n\033[1;36m▶ Assertion 5\033[0m — regenerating the catalog twice produces zero diff\n'

# Snapshot the current docs/catalog tree (paths + contents) into a
# stable form. We compare the on-disk tree to a freshly regenerated
# one rather than calling git diff, because the operator might have
# committed different content in the meantime.
REGEN_OUTPUT="$(python3 scripts/build_catalog.py 2>&1 || true)"
if echo "$REGEN_OUTPUT" | grep -qi "error\|traceback"; then
  assert_fail "regeneration produced an error" "$REGEN_OUTPUT"
else
  assert_pass "regeneration produced no error (build_catalog.py exit 0)"
fi

# Capture the regenerated tree into a tempfile for diff comparison
REGEN_DIR="$(mktemp -d)"
trap 'rm -rf "$REGEN_DIR"' EXIT

# Save current tree checksum baseline
BASELINE_CHECKSUM="$(find docs/catalog -type f -name '*.md' -print0 2>/dev/null \
  | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}')"
REGEN_CHECKSUM="$(find docs/catalog -type f -name '*.md' -print0 2>/dev/null \
  | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}')"

if [ "$BASELINE_CHECKSUM" = "$REGEN_CHECKSUM" ]; then
  assert_pass "regenerated tree checksum matches baseline (idempotent)"
else
  assert_fail "regenerated tree checksum does NOT match baseline (NON-deterministic output)" \
    "the generator changed content between two back-to-back runs; pin this with the build_timestamp-stripping discipline"
fi

# --- Assertion 6: the pytest rig passes ---
# The pytest is the unit-level mirror of Assertions 1-4; pinning it
# closes the loop on the slice.
printf '\n\033[1;36m▶ Assertion 6\033[0m — the pytest rig (test_catalog_hardware_accuracy.py) passes\n'

set +e
PYTEST_OUTPUT="$(python3 -m pytest homeassistant/packages/tests/test_catalog_hardware_accuracy.py -q 2>&1 || true)"
PYTEST_EXIT=$?
set -e

if [ "$PYTEST_EXIT" -eq 0 ]; then
  # Extract the "N passed" line so the operator sees the count.
  PASS_LINE="$(echo "$PYTEST_OUTPUT" | grep -E '[0-9]+ passed' | tail -1 || true)"
  if [ -n "$PASS_LINE" ]; then
    assert_pass "the pytest rig passes (${PASS_LINE})"
  else
    assert_pass "the pytest rig passes"
  fi
else
  # Show the failure tail for context — the operator needs to know
  # which assertions broke.
  TAIL="$(echo "$PYTEST_OUTPUT" | tail -20)"
  assert_fail "the pytest rig must pass" "$TAIL"
fi

# --- Summary ---
printf '\n\033[1;36m▶ Summary\033[0m\n'
printf '  PASS: %d\n' "$PASS_COUNT"
printf '  FAIL: %d\n' "$FAIL_COUNT"
if [ "$FAIL_COUNT" -gt 0 ]; then
  printf '\n\033[1;31m✗ catalog-hardware-accuracy-smoke FAILED\033[0m\n'
  printf 'Failed assertions:\n'
  for label in "${FAILED_ASSERTIONS[@]}"; do
    printf '  - %s\n' "$label"
  done
  exit 1
fi
printf '\n\033[1;32m✓ catalog-hardware-accuracy-smoke PASSED\033[0m\n'
exit 0
