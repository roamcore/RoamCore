#!/usr/bin/env bash
# RoamCore Wave 2 — Slice #26: Deterministic system summary smoke check
#
# Repo-local only (no live HA calls). Asserts that the deterministic
# /api/roamcore/system/summary endpoint, the bundled UI card, the page
# wiring, and the docs page are all in place.
#
# Exit 0 on success. Exit 1 on any failure.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() { echo "ERROR: $*" >&2; exit 1; }
ok()   { echo "  \u2713 $*"; }

echo "=================================================="
echo " RoamCore system summary smoke check (slice #26)"
echo "=================================================="

# --- 1. View file exists + parses + exposes the expected class/url/name ---
VIEW="homeassistant/custom_components/roamcore/system_summary_view.py"
[ -f "$VIEW" ] || fail "missing $VIEW"
python3 -c 'import ast,sys; ast.parse(open(sys.argv[1],"r",encoding="utf-8").read())' "$VIEW" \
  || fail "Python AST parse failed: $VIEW"
ok "Python AST parse: $VIEW"

grep -q "class RoamcoreSystemSummaryView" "$VIEW" \
  || fail "RoamcoreSystemSummaryView class not declared in $VIEW"
grep -q 'url = "/api/roamcore/system/summary"' "$VIEW" \
  || fail 'expected url = "/api/roamcore/system/summary" in view'
grep -q 'name = "api:roamcore_system_summary"' "$VIEW" \
  || fail 'expected name = "api:roamcore_system_summary" in view'
grep -q '"roamcore_system_summary"' "$VIEW" \
  || fail 'expected contract name "roamcore_system_summary" in view'
ok "view declares RoamcoreSystemSummaryView + url + name"

# --- 2. Response builder references the required top-level keys ---
for k in contract generated_at overall roamcore setup power_backend network diagnostics; do
  grep -q "\"$k\"" "$VIEW" \
    || fail "expected key \"$k\" in view response builder"
done
ok "view references required top-level keys (incl. diagnostics)"

# --- 3. __init__.py imports + registers the view ---
INIT="homeassistant/custom_components/roamcore/__init__.py"
[ -f "$INIT" ] || fail "missing $INIT"
grep -q "from .system_summary_view import RoamcoreSystemSummaryView" "$INIT" \
  || fail "expected import of RoamcoreSystemSummaryView in $INIT"
grep -q "hass.http.register_view(RoamcoreSystemSummaryView(hass))" "$INIT" \
  || fail "expected register_view(RoamcoreSystemSummaryView(hass)) in $INIT"
ok "__init__.py imports + registers RoamcoreSystemSummaryView"

# --- 4. UI card file exists + parses + registers the custom element ---
CARD="homeassistant/www/roamcore/roamcore-system-summary.js"
[ -f "$CARD" ] || fail "missing $CARD"
node --check "$CARD" || fail "node --check failed: $CARD"
grep -q "class RoamcoreSystemSummaryCard" "$CARD" \
  || fail "RoamcoreSystemSummaryCard class not declared in $CARD"
grep -q "customElements.define('roamcore-system-summary'" "$CARD" \
  || fail "custom element 'roamcore-system-summary' not registered in $CARD"
ok "UI card exists + class declared + custom element registered"

# --- 5. Pages wiring (substring check) ---
PAGES="homeassistant/www/roamcore/roamcore-pages.js"
[ -f "$PAGES" ] || fail "missing $PAGES"
grep -q "roamcore-system-summary" "$PAGES" \
  || fail "expected 'roamcore-system-summary' reference in $PAGES"
ok "roamcore-pages.js references roamcore-system-summary"

# --- 6. Docs page exists + references the endpoint ---
DOCS="docs/setup/system-summary.md"
[ -f "$DOCS" ] || fail "missing $DOCS"
grep -q "/api/roamcore/system/summary" "$DOCS" \
  || fail "expected endpoint path '/api/roamcore/system/summary' in $DOCS"
ok "docs page exists + references endpoint"

# --- 7. Feature checklist #26 is flipped ---
FCL="docs/feature-checklist.md"
[ -f "$FCL" ] || fail "missing $FCL"
# line 62 (System UX) — should now read [x]
if ! grep -E "^- \[x\] Deterministic system summary" "$FCL" >/dev/null 2>&1; then
  fail "expected '- [x] Deterministic system summary' in $FCL"
fi
ok "feature-checklist.md #26 flipped to [x]"

echo "=================================================="
echo " \u2713 System summary smoke check passed (slice #26)"
echo "=================================================="