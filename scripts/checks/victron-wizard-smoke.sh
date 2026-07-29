#!/usr/bin/env bash
set -euo pipefail

# Smoke check for the RoamCore Victron pairing wizard JS.
#
# Verifies:
#   - The wizard file parses with `node --check` (syntax).
#   - A minimal stub-DOM instantiation can render all 4 steps without
#     throwing. This catches regressions like a missing template variable
#     that would only surface when the user actually opens the wizard.
#
# The wizard code itself is HACS-friendly and has zero build step, so the
# only check we can realistically automate here is "it parses and the
# state machine + renderers don't throw on the happy paths".

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WIZARD="$ROOT_DIR/homeassistant/www/roamcore/roamcore-victron-connect.js"

if [[ ! -f "$WIZARD" ]]; then
  echo "Missing: $WIZARD" >&2
  exit 2
fi

# 1. Syntax check (catches typos / missing braces).
node --check "$WIZARD"

# 2. Lightweight DOM-stub render test.
TMP_DRIVER="$(mktemp -t victron-wizard-smoke-XXXXXX.js)"
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

// Verify the state machine walks all 4 steps without throwing.
const steps = ['intro', 'discover', 'connecting', 'success'];
for (const s of steps) {
  card._step = s;
  card._render();
}
// Verify error mapping helpers don't throw.
card._wizError('discovery_timeout');
card._wizError('connect_invalid_host', 'detail');
// Verify back navigation.
card._goto('discover');
card._back();
console.log('OK');
EOF

node "$TMP_DRIVER" "$WIZARD" >/dev/null

echo "OK: victron wizard smoke check passed"