#!/usr/bin/env bash
set -euo pipefail

# Smoke check for the RoamCore Victron auto-discovery slice (Wave 2 #12).
#
# Verifies:
#   - The wizard file parses with `node --check` (syntax).
#   - The Wave 2 #12 constants exist:
#       _AUTO_RESCAN_INTERVAL_MS
#       _MQTT_LAN_PROMPT (with menu path string)
#       _STATE_AUTO_DISCOVER
#   - A DOM-stub instance can be constructed without throwing.
#   - When discovery returns a candidate, the auto-discover banner and the
#     "Enable MQTT over LAN" prompt both render.
#   - The docs/feature-checklist.md entry for auto-discovery is ticked.
#   - The docs/guides/victron-connect-flow.md has an "Auto-discovery on LAN"
#     section.
#
# Mirrors scripts/checks/victron-wizard-smoke.sh's pattern: no build step,
# single-file JS, regex-driven assertions on the source.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WIZARD="$ROOT_DIR/homeassistant/www/roamcore/roamcore-victron-connect.js"
CHECKLIST="$ROOT_DIR/docs/feature-checklist.md"
GUIDE="$ROOT_DIR/docs/guides/victron-connect-flow.md"

if [[ ! -f "$WIZARD" ]]; then
  echo "Missing: $WIZARD" >&2
  exit 2
fi

# ---------------------------------------------------------------------------
# 1. JS syntax check.
# ---------------------------------------------------------------------------
node --check "$WIZARD"

# ---------------------------------------------------------------------------
# 2. Required constants present.
# ---------------------------------------------------------------------------
for sym in _AUTO_RESCAN_INTERVAL_MS _MQTT_LAN_PROMPT _STATE_AUTO_DISCOVER _maybeAutoLaunchDiscovery _armRescanTimer _stopRescanTimer _bestCandidate _shouldShowMqttLanPrompt _buildMqttLanPrompt; do
  # Accept any of: const NAME =, function NAME, NAME[,=: ] (method/property).
  if ! grep -qE "(const |function |^[[:space:]]+|^)$sym\b" "$WIZARD"; then
    echo "Missing symbol in wizard JS: $sym" >&2
    exit 1
  fi
done

# The MQTT-LAN prompt copy block must contain the menu path verbatim.
if ! grep -q 'Enable MQTT over LAN (Broker mode)' "$WIZARD"; then
  echo "MQTT-LAN prompt is missing the 'Enable MQTT over LAN (Broker mode)' copy." >&2
  exit 1
fi
if ! grep -q 'Settings.*Services.*MQTT' "$WIZARD"; then
  echo "MQTT-LAN prompt is missing the Settings/Services/MQTT menu path." >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# 3. Lightweight DOM-stub render test.
#
# The driver instantiates the card, force-sets view=auto_discover, then
# pretends discovery returned a candidate and status reports no data flowing.
# We assert both the auto-discover banner and the MQTT-LAN prompt are in the
# rendered shadow HTML.
# ---------------------------------------------------------------------------
TMP_DRIVER="$(mktemp -t victron-auto-discovery-smoke-XXXXXX.js)"
trap 'rm -f "$TMP_DRIVER"' EXIT

cat > "$TMP_DRIVER" <<'EOF'
const fs = require('fs');
const vm = require('vm');

const code = fs.readFileSync(process.argv[2], 'utf8')
  + '\nglobalThis.__Card = RoamCoreVictronConnectCard;\n';

class ShadowRoot {
  constructor() { this._innerHTML = ''; }
  set innerHTML(v) { this._innerHTML = v; }
  get innerHTML() { return this._innerHTML; }
  querySelector() { return new Element(); }
  querySelectorAll() { return []; }
  appendChild(c) { return c; }
  addEventListener(ev, fn) { (this._listeners = this._listeners || {})[ev] = (this._listeners[ev] || []).concat([fn]); }
}
class Element {
  constructor() {
    this.shadowRoot = null;
    this._listeners = {};
  }
  attachShadow() { this.shadowRoot = new ShadowRoot(); return this.shadowRoot; }
  addEventListener(ev, fn) { (this._listeners[ev] = this._listeners[ev] || []).push(fn); }
  querySelector() { return new Element(); }
  querySelectorAll() { return []; }
  appendChild(c) { return c; }
}
class HTMLElementShim extends Element {}

const ctx = {
  document: { createElement: () => new Element() },
  window: { customCards: [], addEventListener: () => {}, dispatchEvent: () => {} },
  HTMLElement: HTMLElementShim,
  customElements: { define: () => {}, get: () => null },
  CustomEvent: class { constructor(n, i) { this.detail = i && i.detail; } },
  PopStateEvent: class {},
  history: { pushState: () => {} },
  fetch: () => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }),
  setInterval: () => 0, setTimeout: () => 0,
  clearInterval: () => {}, clearTimeout: () => {},
  AbortController: class { abort() {} constructor() { this.signal = {}; } },
  console,
};
ctx.globalThis = ctx;
vm.createContext(ctx);
vm.runInContext(code, ctx);

const card = new ctx.__Card();
card.setConfig({ title: 'Pair Victron' });

// Step 1: idle → auto_discover view, no candidates yet.
card._view = 'auto_discover';
card._candidates = [];
card._status = null;
card._render();

if (!String(card.shadowRoot.innerHTML).includes('data-test="auto-discover-banner"')) {
  console.error('Expected auto-discover banner in shadow DOM (scanning state).');
  console.error('--- shadow HTML (truncated) ---');
  console.error(String(card.shadowRoot.innerHTML).slice(0, 600));
  process.exit(1);
}

// Step 2: discovery returns a reachable candidate, status still empty.
card._candidates = [
  { name: 'venus.local', host: 'venus.local', ip: '192.168.1.50', port: 1883, source: 'dns:venus.local', reachable: true, bad: false },
];
card._status = { victron: { connected: false, did_full_publish: false }, config: { valid: true }, inventory: { devices_count: 0, topics_count: 0 } };
card._render();

const html = String(card.shadowRoot.innerHTML);
if (!html.includes('auto-discover-banner')) {
  console.error('Expected auto-discover banner with candidate.');
  console.error('--- shadow HTML (truncated) ---');
  console.error(html.slice(0, 800));
  process.exit(1);
}
if (!html.includes('192.168.1.50')) {
  console.error('Expected discovered IP in auto-discover banner.');
  process.exit(1);
}
if (!html.includes('mqtt-lan-prompt')) {
  console.error('Expected MQTT-LAN prompt when candidate found but no data flowing.');
  console.error('--- shadow HTML (truncated) ---');
  console.error(html.slice(0, 1200));
  process.exit(1);
}
if (!html.includes('Enable MQTT over LAN (Broker mode)')) {
  console.error('Expected MQTT-LAN prompt copy with menu path.');
  process.exit(1);
}

// Step 3: status reports connected → banner and prompt disappear.
card._status = { victron: { connected: true, did_full_publish: true }, config: { valid: true }, inventory: { devices_count: 3, topics_count: 42 } };
card._render();
const html2 = String(card.shadowRoot.innerHTML);
// Look for the actual prompt *block* (with the data-test attribute the
// runtime uses), not just the CSS class name in the style tag.
if (html2.includes('data-test="mqtt-lan-prompt"')) {
  console.error('MQTT-LAN prompt should be hidden when paired.');
  process.exit(1);
}
if (html2.includes('data-test="auto-discover-banner"')) {
  console.error('Auto-discover banner should be hidden when paired.');
  process.exit(1);
}

// Step 4: helper sanity.
const prompt = card._buildMqttLanPrompt();
if (!prompt || !prompt.menuPathCanonical || !prompt.menuPathCanonical.includes('Enable MQTT over LAN')) {
  console.error('_buildMqttLanPrompt() returned malformed data:', JSON.stringify(prompt));
  process.exit(1);
}
if (typeof card.AUTO_RESCAN_INTERVAL_MS !== 'number' || card.AUTO_RESCAN_INTERVAL_MS <= 0) {
  console.error('Auto rescan interval constant not exposed.');
  process.exit(1);
}
if (String(card.STATE_AUTO_DISCOVER).length === 0) {
  console.error('Auto discover state constant not exposed.');
  process.exit(1);
}

console.log('OK');
EOF

node "$TMP_DRIVER" "$WIZARD" >/dev/null

# ---------------------------------------------------------------------------
# 4. Docs.
# ---------------------------------------------------------------------------
if ! grep -qE '^- \[x\] Auto-discovery of Victron GX on LAN' "$CHECKLIST"; then
  echo "feature-checklist.md must have [x] Auto-discovery of Victron GX on LAN entry." >&2
  exit 1
fi

if ! grep -q 'Auto-discovery on LAN' "$GUIDE"; then
  echo "victron-connect-flow.md must contain an 'Auto-discovery on LAN' section." >&2
  exit 1
fi

if ! grep -q 'Enable MQTT over LAN (Broker mode)' "$GUIDE"; then
  echo "victron-connect-flow.md must document the 'Enable MQTT over LAN (Broker mode)' setting." >&2
  exit 1
fi

echo "OK: victron auto-discovery smoke check passed"