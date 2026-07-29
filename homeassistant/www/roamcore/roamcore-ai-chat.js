/**
 * RoamCore AI Chat Card
 *
 * Vanilla-JS custom-element for the opt-in AI chat layer (slice #27).
 * Privacy contract (enforced by the view + smoke check):
 *   - The toggle input_boolean.rc_ai_chat_enabled is OFF by default.
 *   - When OFF, the card renders the "AI Chat is OFF" banner. No requests.
 *   - When ON but no API key, the card shows the setup instructions and
 *     surfaces the 503 error from the view if the user sends anyway.
 *   - When ON with an API key, the card POSTs to
 *     /api/roamcore/ai_chat/message and renders the chat-style log.
 *   - NO outbound URLs other than the in-tenant /api/roamcore/ai_chat/message.
 *     No CDN scripts. No telemetry. No analytics. No error reporters.
 *
 * Usage in Lovelace YAML:
 *   type: custom:roamcore-ai-chat
 *
 * Usage in pages.js:
 *   const el = document.createElement('roamcore-ai-chat');
 *   if (typeof el.setConfig === 'function') el.setConfig({});
 *   el.hass = this._hass;
 */

(function () {
  'use strict';

  // ----- Constants (kept in sync with view.py) -----
  var ENDPOINT = '/api/roamcore/ai_chat/message';
  var POLL_MS = 0; // chat does NOT poll by default

  var TOGGLE_ENTITY = 'input_boolean.rc_ai_chat_enabled';
  var API_KEY_ENTITY = 'input_text.rc_ai_chat_api_key';
  var PROVIDER_ENTITY = 'input_text.rc_ai_chat_provider';
  var MODEL_ENTITY = 'input_text.rc_ai_chat_model';
  var MAX_HISTORY_ENTITY = 'input_number.rc_ai_chat_max_history';

  // ----- Tiny helpers -----
  function rcEscapeHtml(s) {
    if (s === null || s === undefined) return '';
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

  function rcIsToggleOn(hass) {
    try {
      return hass && hass.states && hass.states[TOGGLE_ENTITY] && hass.states[TOGGLE_ENTITY].state === 'on';
    } catch (e) {
      return false;
    }
  }

  function rcHasApiKey(hass) {
    try {
      var st = hass && hass.states && hass.states[API_KEY_ENTITY];
      var v = st ? String(st.state || '') : '';
      return !!v && v.trim() !== '';
    } catch (e) {
      return false;
    }
  }

  function rcMaxHistory(hass) {
    try {
      var st = hass && hass.states && hass.states[MAX_HISTORY_ENTITY];
      var n = parseInt(st ? String(st.state || '10') : '10', 10);
      if (!isFinite(n) || n < 0) return 10;
      if (n > 50) return 50;
      return n;
    } catch (e) {
      return 10;
    }
  }

  // ----- Component -----
  class RoamcoreAiChatCard extends HTMLElement {
    constructor() {
      super();
      this._config = {};
      this._hass = null;
      this._history = []; // [{role: 'user'|'assistant', content: str}]
      this._busy = false;
      this._lastError = null;
      this._pollTimer = null;
    }

    setConfig(config) {
      this._config = config || {};
      if (!this._root) {
        this.attachShadow({ mode: 'open' });
        this._root = document.createElement('div');
        this._root.className = 'rc-aichat-root';
        this.shadowRoot.appendChild(this._root);
        var style = document.createElement('style');
        style.textContent = this._css();
        this.shadowRoot.appendChild(style);

        // Local handler for the form submit.
        this._root.addEventListener('submit', (ev) => {
          var t = ev.target;
          if (!t || !t.classList || !t.classList.contains('rc-aichat-form')) return;
          ev.preventDefault();
          var ta = this._root.querySelector('textarea');
          if (!ta) return;
          var v = String(ta.value || '').trim();
          if (!v) return;
          ta.value = '';
          this._send(v);
        });

        // Local handler for the "Clear" button.
        this._root.addEventListener('click', (ev) => {
          var t = ev.target;
          if (!t || !t.classList || !t.classList.contains('rc-aichat-clear')) {
            return;
          }
          this._history = [];
          this._lastError = null;
          this._render();
        });

        // Local handler for the enable-toggle button (when OFF).
        this._root.addEventListener('click', (ev) => {
          var t = ev.target;
          if (!t || !t.classList || !t.classList.contains('rc-aichat-enable')) {
            return;
          }
          if (!this._hass || typeof this._hass.callService !== 'function') return;
          this._hass.callService('input_boolean', 'turn_on', { entity_id: TOGGLE_ENTITY });
        });
      }
      this._render();
    }

    set hass(hass) {
      this._hass = hass;
      this._render();
    }

    getCardSize() {
      // Approximate; grows with chat history.
      return 5;
    }

    static getStubConfig() {
      return {};
    }

    connectedCallback() {
      if (this._root) this._render();
    }

    disconnectedCallback() {
      if (this._pollTimer) { clearInterval(this._pollTimer); this._pollTimer = null; }
    }

    // ----- Networking -----
    _send(message) {
      var hass = this._hass;
      if (!hass) return;
      if (!rcIsToggleOn(hass)) {
        this._lastError = 'AI Chat is OFF — turn on the toggle in Settings.';
        this._render();
        return;
      }
      if (!rcHasApiKey(hass)) {
        this._lastError = 'AI Chat is not configured — set the API key in Settings.';
        this._render();
        return;
      }
      if (this._busy) return;

      var cap = rcMaxHistory(hass);
      var trimmed = this._history.slice(-cap);
      this._history.push({ role: 'user', content: message });
      this._busy = true;
      this._lastError = null;
      this._render();

      var body = {
        message: message,
        history: trimmed,
      };

      var done = (data, err) => {
        this._busy = false;
        if (err) {
          this._lastError = String(err);
        } else if (data && data.ok === false) {
          this._lastError = String(data.error || 'AI chat error');
        } else if (data && typeof data.reply === 'string') {
          this._history.push({ role: 'assistant', content: data.reply });
        } else {
          this._lastError = 'Empty reply';
        }
        this._render();
      };

      // Prefer HA's authenticated callApi so the auth cookie/token is sent.
      try {
        if (typeof hass.callApi === 'function') {
          var p = hass.callApi('POST', 'roamcore_ai_chat_message', body);
          if (p && typeof p.then === 'function') {
            p.then(function (d) { done(d, null); }).catch(function (e) {
              done(null, String((e && e.message) || e || 'AI chat error'));
            });
            return;
          }
        }
      } catch (e) {
        // fall through to fetch
      }

      try {
        var headers = { 'content-type': 'application/json' };
        try {
          if (hass.auth && hass.auth.data && hass.auth.data.access_token) {
            headers['Authorization'] = 'Bearer ' + hass.auth.data.access_token;
          }
        } catch (e2) { /* ignore */ }
        fetch(ENDPOINT, {
          method: 'POST',
          credentials: 'same-origin',
          headers: headers,
          body: JSON.stringify(body),
        }).then(function (r) {
          if (!r.ok) {
            return r.json().catch(function () { return { error: 'http_' + r.status }; })
              .then(function (j) { done(null, String((j && j.error) || ('http_' + r.status))); });
          }
          return r.json();
        }).then(function (d) { done(d, null); })
          .catch(function (e) { done(null, String((e && e.message) || e || 'AI chat error')); });
      } catch (e) {
        done(null, String((e && e.message) || e || 'AI chat error'));
      }
    }

    // ----- Rendering -----
    _render() {
      if (!this._root) return;
      var hass = this._hass;

      // No hass -> "connect to HA".
      if (!hass) {
        this._root.innerHTML =
          '<ha-card><div class="rc-card">' +
            '<div class="rc-head">' +
              '<span class="rc-title">AI chat</span>' +
              '<span class="rc-pill rc-pill-off">OFF</span>' +
            '</div>' +
            '<div class="rc-empty">Connect to Home Assistant to use AI chat.</div>' +
          '</div></ha-card>';
        return;
      }

      var on = rcIsToggleOn(hass);
      var keyed = on && rcHasApiKey(hass);

      if (!on) {
        this._renderOff(hass);
        return;
      }
      if (!keyed) {
        this._renderUnconfigured(hass);
        return;
      }
      this._renderActive(hass);
    }

    _renderOff(hass) {
      this._root.innerHTML =
        '<ha-card><div class="rc-card">' +
          '<div class="rc-head">' +
            '<span class="rc-title">AI chat</span>' +
            '<span class="rc-pill rc-pill-off">OFF</span>' +
          '</div>' +
          '<div class="rc-banner rc-banner-off">' +
            '<div class="rc-banner-title">AI Chat is OFF</div>' +
            '<div class="rc-banner-sub">Opt-in only. Nothing is sent off-host until you turn this on.</div>' +
            '<div class="rc-banner-actions">' +
              '<button class="rc-btn rc-aichat-enable">Enable AI chat</button>' +
            '</div>' +
          '</div>' +
          '<div class="rc-privacy">' +
            '<div class="rc-privacy-title">Privacy</div>' +
            '<ul class="rc-privacy-list">' +
              '<li>OFF by default. No outbound calls. No telemetry.</li>' +
              '<li>When ON, the system summary is sent to your configured AI provider.</li>' +
              '<li>No other RoamCore data leaves the host.</li>' +
            '</ul>' +
          '</div>' +
        '</div></ha-card>';
    }

    _renderUnconfigured(hass) {
      this._root.innerHTML =
        '<ha-card><div class="rc-card">' +
          '<div class="rc-head">' +
            '<span class="rc-title">AI chat</span>' +
            '<span class="rc-pill rc-pill-warn">SETUP</span>' +
          '</div>' +
          '<div class="rc-banner rc-banner-warn">' +
            '<div class="rc-banner-title">AI chat is on but no API key is set</div>' +
            '<div class="rc-banner-sub">The endpoint will return 503 until <code>' + rcEscapeHtml(API_KEY_ENTITY) + '</code> has a value.</div>' +
            '<ol class="rc-steps">' +
              '<li>Open Home Assistant → Settings → Devices & Services → Helpers.</li>' +
              '<li>Set <code>' + rcEscapeHtml(API_KEY_ENTITY) + '</code> to your provider API key.</li>' +
              '<li>(Optional) Set <code>' + rcEscapeHtml(PROVIDER_ENTITY) + '</code> and <code>' + rcEscapeHtml(MODEL_ENTITY) + '</code>.</li>' +
              '<li>Refresh this page.</li>' +
            '</ol>' +
          '</div>' +
          '<div class="rc-privacy">' +
            '<div class="rc-privacy-title">Privacy</div>' +
            '<ul class="rc-privacy-list">' +
              '<li>OFF by default. No outbound calls. No telemetry.</li>' +
              '<li>When ON, the system summary is sent to your configured AI provider.</li>' +
              '<li>No other RoamCore data leaves the host.</li>' +
            '</ul>' +
          '</div>' +
        '</div></ha-card>';
    }

    _renderActive(hass) {
      var history = this._history;
      var busy = this._busy;
      var err = this._lastError;
      var log = history.map(function (t) {
        var role = t.role === 'assistant' ? 'assistant' : 'user';
        return '<div class="rc-msg rc-msg-' + role + '">' +
          '<div class="rc-msg-role">' + rcEscapeHtml(role) + '</div>' +
          '<div class="rc-msg-body">' + rcEscapeHtml(t.content) + '</div>' +
        '</div>';
      }).join('');
      if (!log) log = '<div class="rc-empty">Ask a question. Answers come from the local RoamCore system summary.</div>';

      var provider = rcDash(((hass.states || {})[PROVIDER_ENTITY] || {}).state);
      var model = rcDash(((hass.states || {})[MODEL_ENTITY] || {}).state);

      this._root.innerHTML =
        '<ha-card><div class="rc-card">' +
          '<div class="rc-head">' +
            '<span class="rc-title">AI chat</span>' +
            '<span class="rc-pill rc-pill-on">ON</span>' +
            '<span class="rc-meta">' + rcEscapeHtml(provider) + ' · ' + rcEscapeHtml(model) + '</span>' +
          '</div>' +
          '<div class="rc-log">' + log + '</div>' +
          (err ? '<div class="rc-error">' + rcEscapeHtml(err) + '</div>' : '') +
          '<form class="rc-aichat-form">' +
            '<textarea class="rc-aichat-input" rows="2" placeholder="' + (busy ? 'Working…' : 'Ask about your system…') + '" ' + (busy ? 'disabled' : '') + '></textarea>' +
            '<div class="rc-actions">' +
              '<button type="submit" class="rc-btn rc-btn-primary" ' + (busy ? 'disabled' : '') + '>' + (busy ? 'Sending…' : 'Send') + '</button>' +
              '<button type="button" class="rc-btn rc-aichat-clear" ' + (history.length === 0 || busy ? 'disabled' : '') + '>Clear</button>' +
            '</div>' +
          '</form>' +
          '<div class="rc-privacy">' +
            '<div class="rc-privacy-title">Privacy</div>' +
            '<ul class="rc-privacy-list">' +
              '<li>Messages and the system summary are sent to the configured AI provider.</li>' +
              '<li>Disabling the toggle stops all external calls within seconds.</li>' +
              '<li>No telemetry. No analytics. No CDN scripts that phone home.</li>' +
            '</ul>' +
          '</div>' +
        '</div></ha-card>';
    }

    _css() {
      return [
        ':host { display: block; }',
        '.rc-aichat-root { font-family: inherit; }',
        '.rc-card { padding: 14px 16px 16px 16px; }',
        '.rc-head { display:flex; align-items:center; gap:10px; margin-bottom: 10px; flex-wrap: wrap; }',
        '.rc-title { font-weight: 800; font-size: 15px; color: var(--primary-text-color, #f5f5f5); }',
        '.rc-meta { font-size: 11px; opacity: 0.6; color: var(--secondary-text-color, rgba(255,255,255,0.7)); margin-left: auto; }',
        '.rc-pill { display:inline-flex; align-items:center; padding: 2px 10px; border-radius: 999px; font-weight: 800; font-size: 11px; color: #0b0b0b; }',
        '.rc-pill-on { background: var(--rc-good, #43d17a); }',
        '.rc-pill-off { background: var(--rc-muted, rgba(255,255,255,0.55)); color: #0b0b0b; }',
        '.rc-pill-warn { background: var(--rc-ok, #f4c542); }',
        '.rc-banner { padding: 12px; border-radius: 10px; margin-bottom: 12px; }',
        '.rc-banner-off { background: rgba(255,255,255,0.04); border: 1px solid var(--divider-color, rgba(255,255,255,0.12)); }',
        '.rc-banner-warn { background: rgba(244,197,66,0.08); border: 1px solid rgba(244,197,66,0.35); }',
        '.rc-banner-title { font-weight: 800; margin-bottom: 4px; color: var(--primary-text-color, #f5f5f5); }',
        '.rc-banner-sub { font-size: 12px; opacity: 0.8; margin-bottom: 8px; color: var(--secondary-text-color, rgba(255,255,255,0.7)); }',
        '.rc-banner-actions { margin-top: 8px; }',
        '.rc-steps { margin: 8px 0 0 18px; padding: 0; font-size: 12px; color: var(--secondary-text-color, rgba(255,255,255,0.7)); }',
        '.rc-steps li { margin: 4px 0; }',
        '.rc-steps code { background: rgba(255,255,255,0.08); padding: 1px 5px; border-radius: 4px; font-size: 11px; }',
        '.rc-log { display: flex; flex-direction: column; gap: 8px; max-height: 360px; overflow-y: auto; margin-bottom: 12px; padding: 8px; background: rgba(255,255,255,0.03); border-radius: 8px; border: 1px solid var(--divider-color, rgba(255,255,255,0.08)); }',
        '.rc-msg { border-radius: 8px; padding: 8px 10px; }',
        '.rc-msg-user { background: rgba(67,209,122,0.12); border: 1px solid rgba(67,209,122,0.35); align-self: flex-end; max-width: 85%; }',
        '.rc-msg-assistant { background: rgba(255,255,255,0.06); border: 1px solid var(--divider-color, rgba(255,255,255,0.12)); align-self: flex-start; max-width: 90%; white-space: pre-wrap; }',
        '.rc-msg-role { font-size: 10px; opacity: 0.6; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; color: var(--secondary-text-color, rgba(255,255,255,0.7)); }',
        '.rc-msg-body { font-size: 13px; color: var(--primary-text-color, #f5f5f5); white-space: pre-wrap; word-wrap: break-word; }',
        '.rc-aichat-form { display: flex; flex-direction: column; gap: 8px; }',
        '.rc-aichat-input { width: 100%; resize: vertical; padding: 8px 10px; border-radius: 8px; border: 1px solid var(--divider-color, rgba(255,255,255,0.18)); background: var(--secondary-background-color, rgba(255,255,255,0.04)); color: var(--primary-text-color, #f5f5f5); font-family: inherit; font-size: 13px; box-sizing: border-box; }',
        '.rc-actions { display: flex; gap: 8px; }',
        '.rc-btn { padding: 6px 12px; border-radius: 8px; border: 1px solid var(--divider-color, rgba(255,255,255,0.18)); background: var(--secondary-background-color, rgba(255,255,255,0.06)); color: var(--primary-text-color, #f5f5f5); font-weight: 700; font-size: 13px; cursor: pointer; }',
        '.rc-btn-primary { background: var(--rc-good, #43d17a); color: #0b0b0b; border-color: transparent; }',
        '.rc-btn:disabled { opacity: 0.55; cursor: not-allowed; }',
        '.rc-error { margin: 8px 0; padding: 8px 10px; border-radius: 8px; background: rgba(255,93,93,0.10); border: 1px solid rgba(255,93,93,0.35); color: #ffb3b3; font-size: 12px; }',
        '.rc-empty { padding: 14px 0; font-size: 13px; color: var(--secondary-text-color, rgba(255,255,255,0.7)); }',
        '.rc-privacy { margin-top: 12px; padding: 10px 12px; border-radius: 8px; background: rgba(255,255,255,0.03); border: 1px solid var(--divider-color, rgba(255,255,255,0.10)); }',
        '.rc-privacy-title { font-weight: 800; font-size: 12px; letter-spacing: 0.4px; margin-bottom: 6px; opacity: 0.8; color: var(--primary-text-color, #f5f5f5); }',
        '.rc-privacy-list { margin: 0; padding-left: 18px; font-size: 12px; color: var(--secondary-text-color, rgba(255,255,255,0.7)); }',
        '.rc-privacy-list li { margin: 3px 0; }',
        '@media (max-width: 700px) {',
        '  .rc-card { padding: 10px 12px 12px 12px; }',
        '  .rc-title { font-size: 14px; }',
        '}',
      ].join('\n');
    }
  }

  customElements.define('roamcore-ai-chat', RoamcoreAiChatCard);

  // Register the card for the Lovelace card picker.
  if (typeof window !== 'undefined') {
    window.customCards = window.customCards || [];
    window.customCards.push({
      type: 'roamcore-ai-chat',
      name: 'RoamCore AI Chat',
      description: 'Opt-in AI chat layer that consumes the RoamCore system summary (slice #27).',
      preview: true,
    });
  }
})();