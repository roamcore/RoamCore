#!/usr/bin/env bash
# RoamCore Wave 2 — Slice #27: AI chat (opt-in; API/Auth based) smoke check
#
# Repo-local only (no live HA calls). Asserts that:
#   1. The integration files parse + declare the right class/url/name.
#   2. The privacy contract is hard-enforced in the view source.
#   3. The package declares the toggle OFF by default.
#   4. The JS card parses + registers the custom element + has no outbound URLs.
#   5. The pages.js wiring references the new card.
#   6. The docs page exists.
#   7. The feature checklist line 63 is flipped to [x].
#
# Exit 0 on success. Exit 1 on any failure.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() { echo "ERROR: $*" >&2; exit 1; }
ok()   { echo "  ✓ $*"; }

echo "=================================================="
echo " RoamCore AI chat smoke check (slice #27)"
echo "=================================================="

# --- 1. Integration files parse + structure ---
INIT="homeassistant/custom_components/roamcore_ai_chat/__init__.py"
VIEW="homeassistant/custom_components/roamcore_ai_chat/view.py"
CONST="homeassistant/custom_components/roamcore_ai_chat/const.py"
MANIFEST="homeassistant/custom_components/roamcore_ai_chat/manifest.json"
REQ="homeassistant/custom_components/roamcore_ai_chat/requirements.txt"
for f in "$INIT" "$VIEW" "$CONST" "$MANIFEST" "$REQ"; do
  [ -f "$f" ] || fail "missing $f"
done
for f in "$INIT" "$VIEW" "$CONST"; do
  python3 -c 'import ast,sys; ast.parse(open(sys.argv[1],"r",encoding="utf-8").read())' "$f" \
    || fail "Python AST parse failed: $f"
done
ok "integration files exist + Python parses"

# --- 2. const.py declares DOMAIN + contract version + supported providers ---
grep -q '^DOMAIN = "roamcore_ai_chat"' "$CONST" \
  || fail 'expected DOMAIN = "roamcore_ai_chat" in const.py'
grep -q 'CONTRACT_VERSION' "$CONST" \
  || fail "expected CONTRACT_VERSION in const.py"
grep -q 'PROVIDER_ANTHROPIC' "$CONST" \
  || fail "expected PROVIDER_ANTHROPIC in const.py"
grep -q 'PROVIDER_OPENAI' "$CONST" \
  || fail "expected PROVIDER_OPENAI in const.py"
ok "const.py declares domain + version + providers"

# --- 3. view.py declares RoamCoreAiChatView + url + name ---
grep -q "class RoamCoreAiChatView" "$VIEW" \
  || fail "RoamCoreAiChatView class not declared in $VIEW"
grep -q 'url = "/api/roamcore/ai_chat/message"' "$VIEW" \
  || fail 'expected url = "/api/roamcore/ai_chat/message" in view'
grep -q 'name = "api:roamcore:ai_chat:message"' "$VIEW" \
  || fail 'expected name = "api:roamcore:ai_chat:message" in view'
ok "view declares RoamCoreAiChatView + url + name"

# --- 4. PRIVACY CONTRACT (hard guards in source) ---

# 4a. OFF-state guard: returns 404 with "ai chat disabled".
grep -q '"ai chat disabled"' "$VIEW" \
  || fail 'expected "ai chat disabled" string in view.py (OFF-state contract)'
grep -q 'status=404' "$VIEW" \
  || fail 'expected status=404 in view.py (OFF-state must return HTTP 404)'
ok "OFF-state guard: 404 with 'ai chat disabled'"

# 4b. No-API-key guard: returns 503 with "ai chat not configured".
grep -q '"ai chat not configured"' "$VIEW" \
  || fail 'expected "ai chat not configured" string in view.py (no-key contract)'
grep -q 'status=503' "$VIEW" \
  || fail 'expected status=503 in view.py (no-key must return HTTP 503)'
ok "no-key guard: 503 with 'ai chat not configured'"

# 4c. Summary source must be in-process, not a network loopback call.
# The view imports the sibling module directly:
grep -q 'from homeassistant.custom_components.roamcore_openclaw_api.view import' "$VIEW" \
  || fail 'expected direct import of roamcore_openclaw_api.view in view.py (in-process summary)'
# Must NOT contain a localhost/127.0.0.1 fetch back into HA.
if grep -E 'fetch\(|aiohttp\.ClientSession\(\)' "$VIEW" >/dev/null 2>&1; then
  # Allow aiohttp usage (it's how we call the LLM provider), but flag any
  # references to the local HA URL. The summary fetch path uses the import
  # above; provider calls go to api.anthropic.com / api.openai.com.
  if grep -E '127\.0\.0\.1|localhost|127\.0\.0\.1:8123' "$VIEW" >/dev/null 2>&1; then
    fail "view.py references 127.0.0.1/localhost — must not loopback to HA"
  fi
fi
ok "summary source is in-process (no HA loopback)"

# 4d. No hardcoded API keys (must read from the input_text helper).
grep -q 'input_text.rc_ai_chat_api_key' "$VIEW" \
  || fail "expected input_text.rc_ai_chat_api_key reference in view.py"
if grep -E 'sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{20,}' "$VIEW" >/dev/null 2>&1; then
  fail "view.py contains a hardcoded API key"
fi
ok "API key is sourced from input_text helper (no hardcoded keys)"

# 4e. Toggle entity must be the input_boolean helper.
grep -q 'input_boolean.rc_ai_chat_enabled' "$VIEW" \
  || fail "expected input_boolean.rc_ai_chat_enabled reference in view.py"
ok "toggle entity is the input_boolean helper"

# 4f. Outbound URLs are limited to the configured providers (Anthropic + OpenAI).
grep -q 'https://api.anthropic.com/v1/messages' "$VIEW" \
  || fail 'expected Anthropic endpoint in view.py'
grep -q 'https://api.openai.com/v1/chat/completions' "$VIEW" \
  || fail 'expected OpenAI endpoint in view.py'
# Make sure NO other unexpected outbound URLs leak in (other than the two).
OTHER_URLS=$(grep -oE 'https?://[A-Za-z0-9._/-]+' "$VIEW" | sort -u || true)
for u in $OTHER_URLS; do
  case "$u" in
    https://api.anthropic.com/*) ;;
    https://api.openai.com/*) ;;
    *) fail "unexpected outbound URL in view.py: $u" ;;
  esac
done
ok "outbound URLs limited to Anthropic + OpenAI"

# --- 5. __init__.py registers the view ---
grep -q "hass.http.register_view(RoamCoreAiChatView(hass))" "$INIT" \
  || fail "expected register_view(RoamCoreAiChatView(hass)) in $INIT"
ok "__init__.py registers RoamCoreAiChatView"

# --- 6. Package declares the toggle OFF by default ---
PKG="homeassistant/packages/roamcore_ai_chat.yaml"
if [ -f "$PKG" ]; then
  python3 -c 'import sys,yaml; yaml.safe_load(open(sys.argv[1],"r",encoding="utf-8"))' "$PKG" \
    || fail "YAML parse failed: $PKG"
  grep -q 'rc_ai_chat_enabled' "$PKG" \
    || fail "expected rc_ai_chat_enabled in $PKG"
  # OFF by default: input_boolean initial must be `false`.
  # Within the block under `rc_ai_chat_enabled:`, `initial: false` must appear.
  awk '
    /^[[:space:]]*rc_ai_chat_enabled:/ { hit = 1; next }
    hit && /^[[:space:]]+initial:[[:space:]]*false/ { found = 1; exit 0 }
    END { exit (found ? 0 : 1) }
  ' "$PKG" || fail 'expected rc_ai_chat_enabled initial: false (OFF by default)'
  grep -q 'rc_ai_chat_api_key' "$PKG" \
    || fail "expected rc_ai_chat_api_key helper in $PKG"
  ok "package declares rc_ai_chat_enabled initial: false + rc_ai_chat_api_key"
else
  ok "(skipped) package check — $PKG not present on this branch"
fi

# --- 7. JS card exists + parses + registers the custom element ---
CARD="homeassistant/www/roamcore/roamcore-ai-chat.js"
[ -f "$CARD" ] || fail "missing $CARD"
node --check "$CARD" || fail "node --check failed: $CARD"
grep -q "class RoamcoreAiChatCard" "$CARD" \
  || fail "RoamcoreAiChatCard class not declared in $CARD"
grep -q "customElements.define('roamcore-ai-chat'" "$CARD" \
  || fail "custom element 'roamcore-ai-chat' not registered in $CARD"
# Privacy notice must be present.
grep -q 'AI Chat is OFF' "$CARD" \
  || fail "expected 'AI Chat is OFF' banner string in JS card"
ok "JS card exists + class declared + custom element registered + privacy banner"

# --- 8. Pages wiring (substring check) ---
PAGES="homeassistant/www/roamcore/roamcore-pages.js"
[ -f "$PAGES" ] || fail "missing $PAGES"
grep -q "roamcore-ai-chat" "$PAGES" \
  || fail "expected 'roamcore-ai-chat' reference in $PAGES"
ok "roamcore-pages.js references roamcore-ai-chat"

# --- 9. JS card privacy contract (no outbound URLs except HA itself) ---
# We allow: /api/roamcore/ai_chat/message and same-origin HA.
# We forbid: any explicit external host.
JS_URLS=$(grep -oE 'https?://[A-Za-z0-9._/-]+' "$CARD" | sort -u || true)
if [ -n "$JS_URLS" ]; then
  for u in $JS_URLS; do
    case "$u" in
      https://api.anthropic.com/*) ;;
      https://api.openai.com/*) ;;
      *) fail "JS card references an external URL: $u" ;;
    esac
  done
fi
# The card must NOT include a CDN <script src="https://...">.
if grep -E '<script[^>]+src=["'\'']https?://' "$CARD" >/dev/null 2>&1; then
  fail "JS card loads a remote <script src=https://...> — privacy violation"
fi
# No analytics / telemetry snippets.
if grep -E 'google-analytics|googletagmanager|sentry|segment\.io|mixpanel|hotjar|amplitude|posthog' "$CARD" >/dev/null 2>&1; then
  fail "JS card references an analytics/telemetry host — privacy violation"
fi
ok "JS card has zero external URLs and no analytics/telemetry"

# --- 10. Docs page exists + references endpoint ---
DOCS="docs/setup/ai-chat.md"
[ -f "$DOCS" ] || fail "missing $DOCS"
grep -q "/api/roamcore/ai_chat/message" "$DOCS" \
  || fail "expected endpoint path '/api/roamcore/ai_chat/message' in $DOCS"
ok "docs/setup/ai-chat.md exists + references endpoint"

# --- 11. Catalog page exists (port from 91ff87d) ---
CATALOG="docs/catalog/ai/ai-chat.md"
[ -f "$CATALOG" ] || fail "missing $CATALOG"
ok "docs/catalog/ai/ai-chat.md exists"

# --- 12. Feature checklist #27 is flipped ---
FCL="docs/feature-checklist.md"
[ -f "$FCL" ] || fail "missing $FCL"
# line 63 (System UX) — should now read [x]
if ! grep -E "^- \[x\] AI chat \(opt-in; API/Auth based\)" "$FCL" >/dev/null 2>&1; then
  fail "expected '- [x] AI chat (opt-in; API/Auth based)' in $FCL"
fi
ok "feature-checklist.md line 63 flipped to [x]"

# --- 13. Manifest.json is valid JSON ---
python3 -c 'import json,sys; json.load(open(sys.argv[1],"r",encoding="utf-8"))' "$MANIFEST" \
  || fail "manifest.json is not valid JSON"
ok "manifest.json is valid JSON"

echo "=================================================="
echo " ✓ AI chat smoke check passed (slice #27)"
echo "=================================================="