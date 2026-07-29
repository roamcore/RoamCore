#!/usr/bin/env bash
#
# RoamCore PWA install/offline/push smoke (Wave 2 #10).
#
# Purely static — no HA runtime. Greps files under
# dashboard/Frontend/Setup Wizard/ + the new docs to assert that the
# tier-b PWA scaffold shipped:
#
#   1. Manifest parses with start_url, display, icons, theme + bg colors.
#   2. sw.js bumps RC_CACHE_VERSION above rc-shell-v1, declares push +
#      notificationclick listeners.
#   3. Install button + iOS hint card are present in the DOM/JS.
#   4. Connectivity listeners + localStorage outbox are wired.
#   5. Docs (pwa.md setup, catalog entry, feature-checklist ticker,
#      features-build-status bullet) all reference the slice.
#
# Exits 0 if every assertion passes, 1 on the first failure.

set -uo pipefail
cd "$(dirname "$0")/../.."
REPO_ROOT="$(pwd)"

RED=''; GREEN=''; YELLOW=''; BLUE=''; NC=''
if [ -t 1 ]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;34m'; NC='\033[0m'
fi

PWA_DIR="dashboard/Frontend/Setup Wizard"
INDEX="$PWA_DIR/index.html"
SW="$PWA_DIR/sw.js"
MANIFEST="$PWA_DIR/manifest.json"
PWA_JS="$PWA_DIR/pwa.js"
PWA_DOC="docs/setup/pwa.md"
CATALOG_DOC="docs/catalog/homelab/pwa.md"
FEATURE_CHECKLIST="docs/feature-checklist.md"
BUILD_STATUS="docs/mvp/features-build-status.md"
BACKLOG="/home/bernard/.openclaw/workspace/memory/cross-project/unified-backlog.md"

PASS=0
FAIL=0
FAILED=()

assert() {
    local label="$1"; local cond="$2"
    if eval "$cond" >/dev/null 2>&1; then
        PASS=$((PASS + 1))
        echo -e "  ${GREEN}✓${NC} $label"
    else
        FAIL=$((FAIL + 1))
        FAILED+=("$label")
        echo -e "  ${RED}✗${NC} $label"
    fi
}

assert_grep() {
    local label="$1"; local pattern="$2"; local file="$3"
    if [ -f "$file" ] && grep -qE "$pattern" "$file"; then
        PASS=$((PASS + 1))
        echo -e "  ${GREEN}✓${NC} $label"
    else
        FAIL=$((FAIL + 1))
        FAILED+=("$label")
        echo -e "  ${RED}✗${NC} $label (file: $file, pattern: $pattern)"
    fi
}

echo -e "${BLUE}PWA install/offline/push smoke (Wave 2 #10)${NC}"
echo "Repo: $REPO_ROOT"
echo ""

# 1. Manifest checks
assert "manifest.json parses as JSON" "[ -f '$MANIFEST' ] && python3 -c 'import json; json.load(open(\"$MANIFEST\"))'"
assert "manifest has start_url=./" "python3 -c 'import json,sys; m=json.load(open(\"$MANIFEST\")); sys.exit(0 if m.get(\"start_url\")==\"./\" else 1)'"
assert "manifest display is standalone (or richer)" "python3 -c 'import json,sys; m=json.load(open(\"$MANIFEST\")); sys.exit(0 if m.get(\"display\") in (\"standalone\",\"fullscreen\",\"minimal-ui\") else 1)'"
assert "manifest icons[] is non-empty" "python3 -c 'import json,sys; m=json.load(open(\"$MANIFEST\")); sys.exit(0 if isinstance(m.get(\"icons\"),list) and m[\"icons\"] else 1)'"
assert "manifest theme_color + background_color present" "python3 -c 'import json,sys; m=json.load(open(\"$MANIFEST\")); sys.exit(0 if m.get(\"theme_color\") and m.get(\"background_color\") else 1)'"

# 2. sw.js checks
assert "sw.js defines RC_CACHE_VERSION above rc-shell-v1" \
    "grep -E \"RC_CACHE_VERSION\\s*=\\s*['\\\"]rc-shell-v[2-9]\" '$SW'"
assert_grep "sw.js has push event listener" "addEventListener\\(\\s*['\\\"]push['\\\"]" "$SW"
assert_grep "sw.js has notificationclick event listener" "addEventListener\\(\\s*['\\\"]notificationclick['\\\"]" "$SW"

# 3. Install + iOS hint UI
assert_grep "index.html references beforeinstallprompt (or pwa.js does)" "beforeinstallprompt" "$PWA_JS"
assert_grep "install button id rc-pwa-install-btn present" 'id="rc-pwa-install-btn"' "$INDEX"
assert_grep "iOS hint card mentions Add to Home Screen" "Add to Home Screen" "$INDEX"

# 4. Connectivity + outbox
assert_grep "online listener present in JS" "addEventListener\\(\\s*['\\\"]online['\\\"]" "$PWA_JS"
assert_grep "offline listener present in JS" "addEventListener\\(\\s*['\\\"]offline['\\\"]" "$PWA_JS"
assert_grep "localStorage outbox wrapper (rc_outbox) present" "rc_outbox" "$PWA_JS"
assert_grep "outbox cap defined (RC_OUTBOX_MAX)" "RC_OUTBOX_MAX" "$PWA_JS"

# 5. Push wiring
assert_grep "subscribe call references applicationServerKey" "applicationServerKey" "$PWA_JS"
assert_grep "showNotification is exercised" "showNotification" "$PWA_JS"

# 6. Docs
assert "[NEW] docs/setup/pwa.md exists" "[ -f '$PWA_DOC' ]"
if [ -f "$PWA_DOC" ]; then
    for section in "What this is" "Privacy" "Supported browsers" "Install" "Offline" "Push" "Troubleshooting" "What" ; do
        assert "pwa.md has section: $section" "grep -qiE \"^#+ .*$section\" '$PWA_DOC'"
    done
fi
assert "[NEW] docs/catalog/homelab/pwa.md exists" "[ -f '$CATALOG_DOC' ]"
assert_grep "catalog pwa.md points to Setup Wizard" "Setup Wizard" "$CATALOG_DOC"
assert_grep "feature-checklist has ticked PWA scaffold line" "\\[x\\].*[Pp][Ww][Aa] scaffold" "$FEATURE_CHECKLIST"
assert_grep "features-build-status mentions PWA scaffold" "[Pp][Ww][Aa] scaffold" "$BUILD_STATUS"

# 7. Backlog row #10 status
if [ -f "$BACKLOG" ]; then
    ROW=$(awk -F'|' '/^\| 10 \|/ {print; exit}' "$BACKLOG")
    assert "backlog Row #10 marked DONE (Row content: $ROW)" \
        "echo '$ROW' | grep -q '✅ DONE'"
else
    FAIL=$((FAIL + 1)); FAILED+=("backlog row file present")
    echo -e "  ${RED}✗${NC} backlog row file present ($BACKLOG)"
fi

echo ""
echo -e "${BLUE}Summary${NC}"
TOTAL=$((PASS + FAIL))
echo -e "  ${GREEN}PASS${NC}: $PASS"
if [ $FAIL -gt 0 ]; then
    echo -e "  ${RED}FAIL${NC}: $FAIL"
    for f in "${FAILED[@]}"; do echo -e "    - $f"; done
fi
echo -e "  Total: $TOTAL assertions"
echo ""

if [ $FAIL -gt 0 ]; then
    echo -e "${RED}❌ pwa-install-smoke FAILED${NC}"
    exit 1
fi
echo -e "${GREEN}✅ pwa-install-smoke PASSED ($PASS/$TOTAL)${NC}"
exit 0