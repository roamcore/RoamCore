/**
 * RoamCore System Summary Card
 *
 * Vanilla-JS custom-element Lovelace card (and reusable <roamcore-system-summary>
 * embed for the in-app pages) that displays the deterministic
 * /api/roamcore/system/summary contract.
 *
 * Design goals (per slice #26):
 *  - Boring + consistent + trustworthy
 *  - Stable visual treatment regardless of which entities are missing
 *  - Best-effort: never crashes; degrades to "Status unknown" offline
 *  - Small (~5 KB), no external dependencies
 *
 * Usage in Lovelace YAML:
 *   type: custom:roamcore-system-summary
 *
 * Usage in pages.js (RoamCoreBasePage subclasses):
 *   const el = document.createElement('roamcore-system-summary');
 *   if (typeof el.setConfig === 'function') el.setConfig({ title: 'System' });
 *   el.hass = this._hass;
 *
 * The component never reaches the network itself — it always reads from the
 * cached `this._hass.callApi('GET', 'roamcore_system_summary', ...)` path.
 * Polling is done via `connectedCallback` (every 30s) and is canceled on
 * disconnect.
 */

(function () {
  'use strict';

  // ----- Constants (kept in sync with system_summary_view.py) -----
  var ENDPOINT = '/api/roamcore/system/summary';
  var POLL_MS = 30000;

  // ----- Tiny helpers (no external deps) -----
  function rcEscapeHtml(s) {
    if (s === null || s === undefined) return '—';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function rcDash(v) {
    if (v === null || v === undefined) return '—';
    var s = String(v);
    if (!s) return '—';
    var t = s.toLowerCase();
    if (t === 'unknown' || t === 'unavailable' || t === 'none') return '—';
    return s;
  }

  function rcStatusColor(overall) {
    // Mirrors rcStatusToColor() in roamcore-pages.js.
    if (overall === 'ok') return 'var(--rc-good, #43d17a)';
    if (overall === 'warn') return 'var(--rc-ok, #f4c542)';
    if (overall === 'error') return 'var(--rc-bad, #ff5d5d)';
    return 'var(--rc-muted, rgba(255,255,255,0.55))';
  }

  function rcStatusLabel(overall) {
    if (overall === 'ok') return 'All systems OK';
    if (overall === 'warn') return 'Some signals unknown';
    if (overall === 'error') return 'Setup incomplete';
    return 'Status unknown';
  }

  function rcYesNo(b) {
    if (b === true) return 'Yes';
    if (b === false) return 'No';
    return '—';
  }

  function rcFormatTimestamp(iso) {
    if (!iso) return '';
    try {
      // Render as compact HH:MM UTC for the "last refreshed" line.
      // We avoid locale-dependent rendering so the timestamp stays boring
      // across machines and timezones.
      var d = new Date(iso);
      if (isNaN(d.getTime())) return '';
      var hh = String(d.getUTCHours()).padStart(2, '0');
      var mm = String(d.getUTCMinutes()).padStart(2, '0');
      return hh + ':' + mm + ' UTC';
    } catch (e) {
      return '';
    }
  }

  // ----- Component -----
  class RoamcoreSystemSummaryCard extends HTMLElement {
    constructor() {
      super();
      this._config = {};
      this._hass = null;
      this._data = null;
      this._error = null;
      this._pollTimer = null;
      this._lastFetchedAt = null;
    }

    // Lovelace card API
    setConfig(config) {
      this._config = config || {};
      if (!this._root) {
        this.attachShadow({ mode: 'open' });
        this._root = document.createElement('div');
        this._root.className = 'rc-summary-root';
        this.shadowRoot.appendChild(this._root);
        var style = document.createElement('style');
        style.textContent = this._css();
        this.shadowRoot.appendChild(style);
      }
      this._render();
    }

    set hass(hass) {
      this._hass = hass;
      // Kick off (or refresh) the first fetch on every hass assignment so
      // the card stays in sync with the underlying entities.
      try { this._fetch(); } catch (e) { /* silent */ }
      if (!this._pollTimer) this._pollTimer = setInterval(() => {
        try { this._fetch(); } catch (e) { /* silent */ }
      }, POLL_MS);
    }

    getCardSize() {
      // Rough estimate; Lovelace uses this for the dashboard grid.
      return 4;
    }

    static getStubConfig() {
      return { title: 'System summary' };
    }

    connectedCallback() {
      // First paint only — the rest is driven by set hass + the poll loop.
      if (this._root) this._render();
    }

    disconnectedCallback() {
      if (this._pollTimer) {
        clearInterval(this._pollTimer);
        this._pollTimer = null;
      }
    }

    // ----- Data fetching -----
    _fetch() {
      var hass = this._hass;
      if (!hass) {
        this._data = null;
        this._error = 'no_hass';
        this._render();
        return;
      }
      // Prefer HA's authenticated callApi (sends the right token) — but
      // fall back to fetch() so the component also works when embedded
      // outside a Lovelace card (e.g. inside roamcore-pages.js).
      try {
        if (typeof hass.callApi === 'function') {
          var p = hass.callApi('GET', 'roamcore_system_summary');
          if (p && typeof p.then === 'function') {
            p.then((d) => { this._onData(d); }).catch((e) => { this._onError(e); });
            return;
          }
        }
      } catch (e) {
        // fall through to fetch
      }

      try {
        var headers = {};
        try {
          if (hass.auth && hass.auth.data && hass.auth.data.access_token) {
            headers['Authorization'] = 'Bearer ' + hass.auth.data.access_token;
          }
        } catch (e2) { /* ignore */ }
        fetch(ENDPOINT, { credentials: 'same-origin', headers: headers })
          .then(function (r) {
            if (!r.ok) throw new Error('http_' + r.status);
            return r.json();
          })
          .then((d) => { this._onData(d); })
          .catch((e) => { this._onError(e); });
      } catch (e) {
        this._onError(e);
      }
    }

    _onData(data) {
      this._data = data || null;
      this._error = null;
      this._lastFetchedAt = new Date();
      this._render();
    }

    _onError(err) {
      // Distinguish auth errors so the UI can show a "Sign in" hint.
      var msg = (err && err.message) ? String(err.message) : String(err || 'error');
      if (msg.indexOf('http_401') !== -1 || msg.toLowerCase().indexOf('unauthor') !== -1) {
        this._error = 'auth';
      } else {
        this._error = 'offline';
      }
      this._render();
    }

    // ----- Rendering -----
    _render() {
      if (!this._root) return;
      var title = (this._config && this._config.title) ? this._config.title : 'System summary';

      var body;
      if (this._error === 'auth') {
        body = '<div class="rc-empty">Sign in to Home Assistant to view the system summary.</div>';
      } else if (this._error === 'offline' || this._error === 'no_hass' || !this._data) {
        body = '<div class="rc-empty">Status unknown — connect to Home Assistant.</div>';
      } else {
        body = this._renderBody(this._data);
      }

      var ts = this._lastFetchedAt ? rcFormatTimestamp(this._lastFetchedAt.toISOString()) : '';

      this._root.innerHTML =
        '<ha-card>' +
          '<div class="rc-card">' +
            '<div class="rc-head">' +
              '<span class="rc-title">' + rcEscapeHtml(title) + '</span>' +
              '<span class="rc-ts">' + (ts ? ('Refreshed ' + rcEscapeHtml(ts)) : '') + '</span>' +
            '</div>' +
            body +
          '</div>' +
        '</ha-card>';
    }

    _renderBody(data) {
      var overall = data && data.overall ? String(data.overall) : 'unknown';
      var color = rcStatusColor(overall);
      var label = rcStatusLabel(overall);

      var diag = (data && data.diagnostics) || {};
      var ok = (typeof diag.signals_ok === 'number') ? diag.signals_ok : null;
      var total = (typeof diag.signals_total === 'number') ? diag.signals_total : null;
      var trust = (ok !== null && total !== null && total > 0)
        ? (ok + '/' + total + ' signals OK')
        : '—';

      var setup = (data && data.setup) || {};
      var power = (data && data.power_backend) || {};
      var net = (data && data.network) || {};
      var contract = (data && data.contract) || {};

      return '' +
        '<div class="rc-pill" style="background:' + color + '">' +
          '<span class="rc-pill-dot"></span>' +
          '<span class="rc-pill-label">' + rcEscapeHtml(label) + '</span>' +
        '</div>' +

        '<div class="rc-meta">' +
          '<span class="rc-chip" title="Trust indicator">' +
            '<span class="rc-chip-icon">✓</span> ' + rcEscapeHtml(trust) +
          '</span>' +
          (contract && contract.version
            ? '<span class="rc-chip rc-chip-muted">contract v' + rcEscapeHtml(contract.version) + '</span>'
            : '') +
        '</div>' +

        '<details class="rc-row" open>' +
          '<summary>Setup</summary>' +
          '<div class="rc-row-body">' +
            this._row('Stage', rcDash(setup.stage)) +
            this._row('Owner ready', rcYesNo(setup.owner_ready)) +
            this._row('Map ready', rcYesNo(setup.map_ready)) +
            this._row('Trip wrapped ready', rcYesNo(setup.trip_wrapped_ready)) +
            this._row('Victron ready', rcYesNo(setup.victron_ready)) +
            this._row('Overall ready', rcYesNo(setup.ready)) +
          '</div>' +
        '</details>' +

        '<details class="rc-row">' +
          '<summary>Power backend</summary>' +
          '<div class="rc-row-body">' +
            this._row('Connected', rcYesNo(power.connected)) +
            this._row('Status', rcDash(power.status)) +
          '</div>' +
        '</details>' +

        '<details class="rc-row">' +
          '<summary>Network</summary>' +
          '<div class="rc-row-body">' +
            this._row('WAN status', rcDash(net.wan_status)) +
            this._row('WAN source', rcDash(net.wan_source)) +
          '</div>' +
        '</details>';
    }

    _row(label, value) {
      return '<div class="rc-kv">' +
        '<span class="rc-k">' + rcEscapeHtml(label) + '</span>' +
        '<span class="rc-v">' + rcEscapeHtml(value) + '</span>' +
      '</div>';
    }

    _css() {
      // Self-contained styling: pull from HA theme vars where possible, fall
      // back to RoamCore's --rc-* palette. Stays inside a shadow root so we
      // never leak rules to the rest of the dashboard.
      return [
        ':host { display: block; }',
        '.rc-summary-root { font-family: inherit; }',
        '.rc-card { padding: 14px 16px 16px 16px; }',
        '.rc-head { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom: 10px; }',
        '.rc-title { font-weight: 800; font-size: 15px; letter-spacing: 0.2px; color: var(--primary-text-color, #f5f5f5); }',
        '.rc-ts { font-size: 11px; opacity: 0.6; color: var(--secondary-text-color, rgba(255,255,255,0.7)); }',
        '.rc-pill { display:inline-flex; align-items:center; gap:8px; padding: 6px 12px; border-radius: 999px; color: #0b0b0b; font-weight: 800; font-size: 13px; margin-bottom: 10px; }',
        '.rc-pill-dot { width: 8px; height: 8px; border-radius: 50%; background: rgba(0,0,0,0.55); }',
        '.rc-pill-label { white-space: nowrap; }',
        '.rc-meta { display:flex; flex-wrap:wrap; gap: 6px; margin-bottom: 10px; }',
        '.rc-chip { display:inline-flex; align-items:center; gap:4px; padding: 4px 10px; border-radius: 999px; border: 1px solid var(--divider-color, rgba(255,255,255,0.12)); background: var(--secondary-background-color, rgba(255,255,255,0.04)); font-weight: 700; font-size: 12px; color: var(--primary-text-color, #f5f5f5); }',
        '.rc-chip-muted { opacity: 0.7; font-weight: 600; }',
        '.rc-chip-icon { font-weight: 800; }',
        '.rc-row { border-top: 1px solid var(--divider-color, rgba(255,255,255,0.08)); padding: 6px 0; }',
        '.rc-row > summary { cursor: pointer; font-weight: 700; padding: 4px 0; color: var(--primary-text-color, #f5f5f5); }',
        '.rc-row-body { padding: 6px 0 4px 6px; display: grid; grid-template-columns: 1fr; gap: 4px; }',
        '.rc-kv { display:flex; justify-content:space-between; gap: 12px; font-size: 13px; }',
        '.rc-k { color: var(--secondary-text-color, rgba(255,255,255,0.7)); }',
        '.rc-v { font-weight: 700; color: var(--primary-text-color, #f5f5f5); }',
        '.rc-empty { padding: 14px 0; font-size: 13px; color: var(--secondary-text-color, rgba(255,255,255,0.7)); }',
        '@media (max-width: 700px) {',
        '  .rc-card { padding: 10px 12px 12px 12px; }',
        '  .rc-title { font-size: 14px; }',
        '}',
      ].join('\n');
    }
  }

  customElements.define('roamcore-system-summary', RoamcoreSystemSummaryCard);

  // Register the card for the Lovelace card picker.
  if (typeof window !== 'undefined') {
    window.customCards = window.customCards || [];
    window.customCards.push({
      type: 'roamcore-system-summary',
      name: 'RoamCore System Summary',
      description: 'Deterministic, boring, consistent system summary (slice #26).',
      preview: true,
    });
  }
})();