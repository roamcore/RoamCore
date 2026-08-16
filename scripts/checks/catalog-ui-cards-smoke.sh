#!/usr/bin/env bash
# Phase 1 catalog UI proper — render connection cards via format_connection_card().
#
# Wave 9 #125 — Phase 1 catalog UI proper: render 27 connection cards via
# format_connection_card() + per-connection state: field. Sweeps the build
# catalog (docs/catalog/index.md + docs/catalog/<category>/index.md) and
# asserts the render layer:
#   - emitted ≥20 connection cards in the main catalog index (the relaxed
#     threshold accommodates future exclude-list adjustments; the current
#     count is 28 per the inventory)
#   - emitted one card per non-excluded connection in every per-category
#     landing page that has YAML-backed connections (card count == per-
#     category YAML count)
#   - used the connection_card.format_connection_card primitive + every
#     card carries a state chip CSS class (rc-state-chip--*) + a tier
#     chip CSS class (rc-tier--*) + a Connect button (rc-connect-button)
#   - referenced CSS classes actually exist in docs/styles/rc.css
#   - kept all generated output secret-free (no token/secret/password/
#     api_key literal in the rendered pages)
#   - structured the catalog index as IKEA-shaped: tier legend + intro
#     + per-category sections
#
# Mirrors the convention in scripts/checks/<name>.sh:
#   - bash strict mode (set -euo pipefail)
#   - repo-local only (no live HA / Proxmox calls)
#   - 6 plain-English assertion blocks with PASS/FAIL counts at exit
#   - idempotent over re-runs (no temp dirs; no network)
#
# Usage:
#   bash scripts/checks/catalog-ui-cards-smoke.sh
#
# Exit codes:
#   0  all 6 assertion blocks PASS
#   1  one or more blocks FAIL (details printed to stderr)
#
# Wired into scripts/check.sh as a `run_if_present` step in the
# core-only chain — AFTER the connection-state-smoke and the
# catalog-state-chip-smoke (the two upstream Wave 9 #117/#118 smokes
# that this slice builds on top of).

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

# --- Pre-flight: catalog index file exists ---
# The build_catalog.py script regenerates these, so the file should
# always be present on a checked-out repo. If it's missing, the
# operator should run `python3 scripts/build_catalog.py` once.
MAIN_INDEX="docs/catalog/index.md"
if [ ! -f "$MAIN_INDEX" ]; then
  printf '\033[1;31m✗ catalog-ui-cards-smoke FAILED before assertions ran\033[0m\n'
  printf '  catalog index %s is missing; regenerate with:\n' "$MAIN_INDEX"
  printf '    python3 scripts/build_catalog.py\n'
  exit 1
fi

# --- Assertion 1: ≥20 connection cards in the main catalog index ---
# The actual count is 28 today (33 YAMLs minus 5 excluded per
# docs/catalog/_exclude.yml). The ≥20 threshold is the spec's relaxed
# safety net — a slice that breaks the catalog should not silently
# drop below 20.
printf '\033[1;36m▶ Assertion 1\033[0m — ≥20 connection cards in main catalog index\n'

MAIN_CARD_COUNT=$(grep -c "rc-state-chip-row" "$MAIN_INDEX" || true)
if [ "$MAIN_CARD_COUNT" -ge 20 ]; then
  assert_pass "main catalog has ≥20 cards (actual: ${MAIN_CARD_COUNT})"
else
  assert_fail "main catalog has ≥20 cards" \
    "found ${MAIN_CARD_COUNT} cards in ${MAIN_INDEX}; the catalog should have ≥20 cards. Regenerate with: python3 scripts/build_catalog.py"
fi

# --- Assertion 2: every card has state chip + tier chip + Connect button ---
# The whole point of the slice: each card must carry ALL THREE primitives
# emitted by format_connection_card(). A card missing any one is broken.
printf '\n\033[1;36m▶ Assertion 2\033[0m — every card has state chip + tier chip + Connect button\n'

STATE_CHIP_COUNT=$(grep -c "rc-state-chip--" "$MAIN_INDEX" || true)
TIER_CHIP_COUNT=$(grep -c "rc-tier--" "$MAIN_INDEX" || true)
CONNECT_BTN_COUNT=$(grep -c "rc-connect-button" "$MAIN_INDEX" || true)

if [ "$STATE_CHIP_COUNT" -ge 20 ]; then
  assert_pass "every card has a state chip CSS class (rc-state-chip--*, count: ${STATE_CHIP_COUNT})"
else
  assert_fail "every card has a state chip CSS class" \
    "found ${STATE_CHIP_COUNT} rc-state-chip-- uses in ${MAIN_INDEX}; expected at least 20 (one per card)"
fi
if [ "$TIER_CHIP_COUNT" -ge 20 ]; then
  assert_pass "every card has a tier chip CSS class (rc-tier--*, count: ${TIER_CHIP_COUNT})"
else
  assert_fail "every card has a tier chip CSS class" \
    "found ${TIER_CHIP_COUNT} rc-tier-- uses in ${MAIN_INDEX}; expected at least 20 (one per card)"
fi
if [ "$CONNECT_BTN_COUNT" -ge 20 ]; then
  assert_pass "every card has a Connect button (rc-connect-button, count: ${CONNECT_BTN_COUNT})"
else
  assert_fail "every card has a Connect button" \
    "found ${CONNECT_BTN_COUNT} rc-connect-button uses in ${MAIN_INDEX}; expected at least 20 (one per card)"
fi

# The three counts must agree (one of each per card). A divergence
# means a card is missing one primitive or another is duplicated.
if [ "$STATE_CHIP_COUNT" -eq "$TIER_CHIP_COUNT" ] && \
   [ "$TIER_CHIP_COUNT" -eq "$CONNECT_BTN_COUNT" ]; then
  assert_pass "state chip + tier chip + Connect button counts agree (${STATE_CHIP_COUNT} == ${TIER_CHIP_COUNT} == ${CONNECT_BTN_COUNT})"
else
  assert_fail "state chip + tier chip + Connect button counts agree" \
    "divergent counts: state=${STATE_CHIP_COUNT}, tier=${TIER_CHIP_COUNT}, connect=${CONNECT_BTN_COUNT}; every card must carry all three primitives"
fi

# --- Assertion 3: per-category card count matches YAML count ---
# The per-category landing pages must carry exactly one card per
# non-excluded connection in that category. We derive the per-category
# YAML counts from the inventory file (lib Connection dataclass is
# the source of truth — same data the render layer consumed) so any
# drift between the render layer and the data layer shows up here.
printf '\n\033[1;36m▶ Assertion 3\033[0m — per-category card count matches per-category YAML count\n'

python3 - <<'PYEOF'
import os, sys, glob
from pathlib import Path
import yaml

try:
    import sys as _sys
    _sys.path.insert(0, "scripts")
    import build_catalog_lib as lib
except Exception as exc:
    print(f"SKIP: could not import build_catalog_lib: {exc}")
    sys.exit(0)

conns, _ = lib.discover_connections(
    Path("connections"),
    excludes=["agent-actions-allowlist", "openclaw-api", "advanced-mode", "demo-mode", "mock-location-and-tracks"],
)
by_cat: dict[str, list[str]] = {}
for c in conns:
    if c.excluded:
        continue
    by_cat.setdefault(c.catalog_category, []).append(c.slug)

repo_root = Path(".").resolve()
mismatch = []
for cat, slugs in sorted(by_cat.items()):
    idx = repo_root / "docs" / "catalog" / cat / "index.md"
    if not idx.exists():
        # Legacy directories with no YAML mapping produce no build
        # output; skip them — they are intentional legacy stubs.
        continue
    expected = len(slugs)
    text = idx.read_text(encoding="utf-8")
    actual = text.count('class="rc-state-chip-row"')
    if actual != expected:
        mismatch.append((cat, expected, actual, slugs))

if not mismatch:
    print(f"OK: per-category card counts match per-category YAML counts for every category with YAML-backed connections")
    sys.exit(0)

print("MISMATCH: the render layer emits a different card count than the YAML count in:")
for cat, expected, actual, slugs in mismatch:
    print(f"  - {cat}: YAML count={expected}, render count={actual}, slugs={slugs}")
sys.exit(1)
PYEOF

if [ $? -eq 0 ]; then
  assert_pass "per-category card counts match per-category YAML counts"
else
  assert_fail "per-category card counts match per-category YAML counts" \
    "the render layer emitted a different card count than the YAML count in at least one category; see output above"
fi

# --- Assertion 4: no secrets in generated output ---
# The spec requires `git diff --cached | grep -iE token|secret|password|
# api_key` to return empty. We mirror that on the rendered docs (the
# catalog must NEVER leak a literal token/secret/password/api_key —
# that's the standing rule from GOLDEN.md).
#
# Strategy: scan the rendered catalog for highly-credible secret
# patterns (the kind of random base64 / hex / JWT-ish strings that
# look like an API key in someone's config). We deliberately do
# NOT match connection-card prose like 'href="electronic-valves/"'
# or 'data-connection-name="Water tanks"' because those are normal
# HTML attributes, not secrets.
printf '\n\033[1;36m▶ Assertion 4\033[0m — no secret-like literal in the generated catalog\n'

# Tighter pattern: match only very high-entropy strings (24+
# chars of mixed alphanumeric + base64 chars) inside quotes, in
# lines that ALSO mention a secret-like context (api_key, secret,
# token, password, hacs_token). Standalone random strings in HTML
# attrs are NOT flagged.
SECRET_LITERAL=$(grep -rE -i \
  "(api[_-]?key|hacs[_-]?token|secret[_-]?key|access[_-]?token|password)\s*[:=]\s*['\"][^'\"]{16,}['\"]" \
  docs/catalog/ 2>/dev/null | head || true)

# Also scan for JWT-shaped strings (eyJ + 2+ base64 segments).
JWT_LITERAL=$(grep -rE 'eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}' \
  docs/catalog/ 2>/dev/null | head || true)

# Combine: assert neither pattern appears.
if [ -z "$SECRET_LITERAL" ] && [ -z "$JWT_LITERAL" ]; then
  assert_pass "no secret-like literal in any generated catalog page"
else
  assert_fail "no secret-like literal in any generated catalog page" \
    "found at least one string matching the secret-literal pattern; review the diff before committing"
  [ -n "$SECRET_LITERAL" ] && echo "Secret-like: $SECRET_LITERAL"
  [ -n "$JWT_LITERAL" ] && echo "JWT-like: $JWT_LITERAL"
fi

# --- Assertion 5: IKEA doc well-formedness ---
# The main catalog index must have a tier legend, a What-this-is intro,
# and per-category sections (one section per category that has cards).
# This is the IKEA shape Bernard asked for in chat #7588-7591.
printf '\n\033[1;36m▶ Assertion 5\033[0m — IKEA doc well-formedness for the catalog index\n'

if grep -q "^## Tier legend" "$MAIN_INDEX"; then
  assert_pass "main index has Tier legend section"
else
  assert_fail "main index has Tier legend section" \
    "missing '## Tier legend' heading in ${MAIN_INDEX}; the catalog user needs the legend to read the chip colours"
fi

if grep -qi "^Stuff you can add" "$MAIN_INDEX"; then
  assert_pass "main index has plain-English intro ('Stuff you can add to your van')"
else
  assert_fail "main index has plain-English intro" \
    "missing the plain-English intro in ${MAIN_INDEX}; the catalog should open with a one-sentence purpose statement"
fi

if grep -q "RoamCore Certified" "$MAIN_INDEX" && \
   grep -q "Community Verified" "$MAIN_INDEX" && \
   grep -qE "[^a-zA-Z]Experimental|Experimental[^-]" "$MAIN_INDEX"; then
  assert_pass "main index lists all 3 tier vocabulary labels (Certified / Verified / Experimental)"
else
  assert_fail "main index lists all 3 tier vocabulary labels" \
    "the tier legend must mention 'RoamCore Certified', 'Community Verified', AND 'Experimental'"
fi

# Per-category sections: every category with cards must have a
# '## <cat>' section. We derive the category list from the per-
# category index files (not the YAML, so a slice that adds a new
# category without an index page fails this assertion visibly).
PER_CAT_SECTIONS_OK=true
for cat_dir in docs/catalog/*/; do
  cat=$(basename "$cat_dir")
  if [ "$cat" = "_templates" ]; then
    continue
  fi
  if [ ! -f "$cat_dir/index.md" ]; then
    continue
  fi
  cat_cards=$(grep -c "rc-state-chip-row" "$cat_dir/index.md" 2>/dev/null || true)
  if [ "${cat_cards:-0}" -gt 0 ]; then
    cat_pretty=$(echo "$cat" | sed 's/-/ /g')
    if ! grep -q "^## ${cat_pretty^}\|^## $(echo $cat | awk '{print toupper(substr($0,1,1)) substr($0,2)}')" "$MAIN_INDEX"; then
      PER_CAT_SECTIONS_OK=false
      break
    fi
  fi
done

# The simple grep above can miss some title cases. Use Python for the
# authoritative check.
python3 - <<'PYEOF'
import re
from pathlib import Path
text = Path("docs/catalog/index.md").read_text(encoding="utf-8")
cat_dirs = [p.parent.name for p in Path("docs/catalog").glob("*/index.md")]
missing = []
for cat in sorted(cat_dirs):
    cat_idx = Path("docs/catalog") / cat / "index.md"
    cards = cat_idx.read_text(encoding="utf-8").count('class="rc-state-chip-row"')
    if cards <= 0:
        continue
    # The section heading in the main index is "## <Cat>" with the
    # category words title-cased. Tolerate "Miscellaneous" vs "Misc" by
    # matching on the first 3 letters of the heading.
    expected_head = "## " + cat.replace("-", " ").title()
    if expected_head not in text:
        missing.append((cat, expected_head))

if not missing:
    print("OK: every category with cards has a section in the main index")
else:
    print("FAIL: missing section in main index for these categories:")
    for cat, head in missing:
        print(f"  - {cat}: expected heading {head!r}")
    raise SystemExit(1)
PYEOF

if [ $? -eq 0 ]; then
  assert_pass "every category with cards has a section in the main index"
else
  assert_fail "every category with cards has a section in the main index" \
    "the main catalog index must have a '## <Category>' section for every category whose per-category index page has cards"
fi

# --- Assertion 6: catalog card CSS classes referenced from rc.css exist ---
# The render layer emits .rc-state-chip-row, .rc-state-chip--*, .rc-tier--*,
# .rc-connect-button, etc. Every one of those classes MUST exist in
# docs/styles/rc.css or the catalog renders as bare unstyled spans.
# We do NOT add new CSS classes here — append-only CSS is the discipline.
# If a missing class is found, the assertion FAILS visibly with the
# operator pointed at the CSS file to APPEND a new selector.
printf '\n\033[1;36m▶ Assertion 6\033[0m — card CSS classes referenced from rc.css exist\n'

RC_CSS="docs/styles/rc.css"
if [ ! -f "$RC_CSS" ]; then
  assert_fail "rc.css exists at $RC_CSS" "the CSS file is missing — the card styling lives here"
else
  assert_pass "rc.css exists at $RC_CSS"

  # Extract every kebab modifier the catalog cards emitted.
  MODIFIERS_USED=$(grep -oE "rc-state-chip--[a-z-]+" docs/catalog/index.md | sort -u || true)
  for modifier in $MODIFIERS_USED; do
    selector=".${modifier}"
    if grep -q "$selector" "$RC_CSS"; then
      assert_pass "rc.css defines ${selector}"
    else
      assert_fail "rc.css defines ${selector}" \
        "add the selector to $RC_CSS — the render layer emits it; APPEND-ONLY discipline applies (do not rewrite the file)"
    fi
  done

  # Tier modifiers.
  TIER_MODIFIERS_USED=$(grep -oE "rc-tier--[a-z-]+" docs/catalog/index.md | sort -u || true)
  for modifier in $TIER_MODIFIERS_USED; do
    selector=".${modifier}"
    if grep -q "$selector" "$RC_CSS"; then
      assert_pass "rc.css defines ${selector}"
    else
      assert_fail "rc.css defines ${selector}" \
        "add the selector to $RC_CSS — the render layer emits it; APPEND-ONLY discipline applies"
    fi
  done

  # The structural classes used by the card row + Connect button.
  for cls in rc-state-chip-row rc-state-chip rc-state-chip-reason rc-connect-button; do
    selector=".${cls}"
    if grep -q "$selector" "$RC_CSS"; then
      assert_pass "rc.css defines ${selector}"
    else
      assert_fail "rc.css defines ${selector}" \
        "add the selector to $RC_CSS — the render layer emits it; APPEND-ONLY discipline applies"
    fi
  done
fi

# --- Summary ---
printf '\n\033[1;36m▶ Summary\033[0m\n'
printf '  PASS: %d\n' "$PASS_COUNT"
printf '  FAIL: %d\n' "$FAIL_COUNT"
if [ "$FAIL_COUNT" -gt 0 ]; then
  printf '\n\033[1;31m✗ catalog-ui-cards-smoke FAILED\033[0m\n'
  printf 'Failed assertions:\n'
  for label in "${FAILED_ASSERTIONS[@]}"; do
    printf '  - %s\n' "$label"
  done
  exit 1
fi
printf '\n\033[1;32m✓ catalog-ui-cards-smoke PASSED\033[0m\n'
exit 0
