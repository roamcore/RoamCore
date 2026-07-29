/**
 * RoamCore Advanced Mode Card
 *
 * A Lovelace custom card that gives the user a clean, clearly-separated
 * toggle surface for the RoamCore Advanced Mode slice (#25):
 *
 *   - Shows the current state (ON / OFF badge) for
 *     `input_boolean.rc_advanced_mode_enabled` (mirrored by
 *     `binary_sensor.rc_advanced_mode`).
 *   - Surfaces a one-tap "Engage advanced mode" / "Lock again" button.
 *     Engage calls `script.rc_advanced_mode_engage`; Lock calls
 *     `script.rc_advanced_mode_disengage`. Both scripts are the only
 *     safe way to flip the boolean — they snapshot state and write an
 *     audit line on toggle.
 *   - Provides a deeplink to the operator-facing
 *     `docs/setup/advanced-mode.md` so the user always sees recovery
 *     steps in one tap.
 *
 * The card hides itself cleanly if the boolean is missing, mirroring the
 * pattern used by `roamcore-mode-builder.js`.
 *
 * Wiring contract (matches homeassistant/packages/roamcore_advanced_mode.yaml):
 *
 *   input_boolean.rc_advanced_mode_enabled   (state; ON / OFF)
 *   binary_sensor.rc_advanced_mode           (mirrors the boolean)
 *   input_text.rc_advanced_mode_last_engaged_state  (snapshot, JSON)
 *   script.rc_advanced_mode_engage           (turn on + snapshot)
 *   script.rc_advanced_mode_disengage        (turn off + audit)
 *
 * Usage in lovelace:
 *   type: custom:roamcore-advanced-mode
 */

class RoamCoreAdvancedModeCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._config = {};
    this._hass = null;
  }

  static getStubConfig() {
    return { title: 'Advanced mode' };
  }

  setConfig(config) {
    this._config = config || {};
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  connectedCallback() {
    this._render();
  }

  // ---------------------------------------------------------------------------
  // Contract helpers
  // ---------------------------------------------------------------------------

  _booleanEntity() {
    return 'input_boolean.rc_advanced_mode_enabled';
  }

  _mirrorEntity() {
    return 'binary_sensor.rc_advanced_mode';
  }

  _snapshotEntity() {
    return 'input_text.rc_advanced_mode_last_engaged_state';
  }

  _engageScript() {
    return 'script.rc_advanced_mode_engage';
  }

  _disengageScript() {
    return 'script.rc_advanced_mode_disengage';
  }

  _isOn() {
    try {
      const v = this._hass?.states?.[this._booleanEntity()]?.state;
      return String(v || '').toLowerCase() === 'on';
    } catch (e) {
      return false;
    }
  }

  _snapshotLine() {
    try {
      const raw = this._hass?.states?.[this._snapshotEntity()]?.state || '{}';
      const obj = JSON.parse(raw);
      return obj && obj.engaged_at ? String(obj.engaged_at) : '';
    } catch (e) {
      return '';
    }
  }

  async _engage() {
    if (!this._hass) return;
    try {
      await this._hass.callService('script', 'turn_on', {
        entity_id: this._engageScript(),
      });
    } catch (e) {
      console.warn('RoamCore advanced mode: failed to engage', e);
    }
  }

  async _disengage() {
    if (!this._hass) return;
    try {
      await this._hass.callService('script', 'turn_on', {
        entity_id: this._disengageScript(),
      });
    } catch (e) {
      console.warn('RoamCore advanced mode: failed to disengage', e);
    }
  }

  // ---------------------------------------------------------------------------
  // Rendering
  // ---------------------------------------------------------------------------

  _render() {
    const root = this.shadowRoot;
    if (!root) return;

    // Hide cleanly if the contract entity is missing — same pattern as
    // the mode-builder card.
    if (!this._hass?.states?.[this._booleanEntity()]) {
      root.innerHTML = '';
      return;
    }

    const on = this._isOn();
    const snapAt = this._snapshotLine();
    const snapBlock = on && snapAt
      ? `<div class="rc-sub" style="margin-top:6px;">Snapshot taken: <b>${this._esc(snapAt)}</b></div>`
      : '';
    const mainAction = on
      ? `<button class="rc-btn rc-btn-danger" id="rc-am-disengage">Lock again</button>`
      : `<button class="rc-btn rc-btn-primary" id="rc-am-engage">Engage advanced mode</button>`;
    const badge = on
      ? `<span class="rc-badge rc-badge-on"><span class="rc-dot"></span>ON</span>`
      : `<span class="rc-badge rc-badge-off"><span class="rc-dot"></span>OFF</span>`;
    const docsHref = (this._config && this._config.docs_href) || '/local/roamcore/docs/setup/advanced-mode.html';

    root.innerHTML = `
      <style>
        :host {
          display: block;
          font-family: var(--rc-font, system-ui, -apple-system, Segoe UI, Roboto, sans-serif);
          color: var(--primary-text-color, #fff);
        }
        .card {
          background: var(--card-background-color, rgba(255,255,255,0.04));
          border: 1px solid rgba(255,255,255,0.08);
          border-radius: 14px;
          padding: 14px;
        }
        .row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
        }
        .title {
          font-weight: 900;
          font-size: 14px;
          margin: 0;
        }
        .sub {
          font-size: 12px;
          opacity: 0.7;
          margin: 4px 0 0 0;
        }
        .badge {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 4px 10px;
          border-radius: 999px;
          font-weight: 900;
          font-size: 12px;
          border: 1px solid;
        }
        .badge .rc-dot {
          width: 8px;
          height: 8px;
          border-radius: 999px;
          display: inline-block;
        }
        .rc-badge-on {
          color: var(--rc-good, #43d17a);
          border-color: rgba(67,209,122,0.45);
          background: rgba(67,209,122,0.10);
        }
        .rc-badge-on .rc-dot { background: var(--rc-good, #43d17a); }
        .rc-badge-off {
          color: rgba(255,255,255,0.65);
          border-color: rgba(255,255,255,0.18);
          background: rgba(255,255,255,0.04);
        }
        .rc-badge-off .rc-dot { background: rgba(255,255,255,0.45); }

        .desc {
          margin-top: 10px;
          font-size: 12px;
          opacity: 0.78;
          line-height: 1.45;
        }
        .actions {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
          margin-top: 12px;
        }
        .rc-btn {
          padding: 10px 14px;
          border-radius: 10px;
          border: 1px solid rgba(255,255,255,0.18);
          background: rgba(255,255,255,0.05);
          color: inherit;
          font-size: 13px;
          font-weight: 800;
          cursor: pointer;
          text-decoration: none;
          display: inline-flex;
          align-items: center;
          justify-content: center;
        }
        .rc-btn:hover { filter: brightness(1.08); }
        .rc-btn-primary {
          background: rgba(244,197,66,0.18);
          border-color: rgba(244,197,66,0.55);
          color: #fff;
        }
        .rc-btn-danger {
          background: rgba(255,93,93,0.18);
          border-color: rgba(255,93,93,0.55);
          color: #fff;
        }
        .rc-link {
          font-size: 12px;
          color: rgba(255,255,255,0.78);
          text-decoration: underline;
          padding: 10px 6px;
        }

        .advanced-on {
          margin-top: 12px;
          padding: 10px 12px;
          border-radius: 10px;
          border: 1px solid rgba(244,197,66,0.45);
          background: rgba(244,197,66,0.10);
          font-size: 12px;
          line-height: 1.4;
        }
        .advanced-on b { color: #f4c542; }
      </style>

      <div class="card">
        <div class="row">
          <div>
            <p class="title">${this._esc(this._config.title || 'Advanced mode')}</p>
            <p class="sub">Power-user toggle. Off by default.</p>
          </div>
          ${badge}
        </div>

        <div class="desc">
          RoamCore Advanced Mode unlocks extra controls and diagnostics.
          Engaging writes a state snapshot to
          <code>input_text.rc_advanced_mode_last_engaged_state</code> and
          appends an audit line, so you can recover in one tap.
        </div>

        ${on ? `
          <div class="advanced-on">
            <b>Advanced controls unlocked.</b> Changes you make here are
            recorded. Tap <b>Lock again</b> when you're done.
          </div>
        ` : ''}

        ${snapBlock}

        <div class="actions">
          ${mainAction}
          <a class="rc-link" href="${this._esc(docsHref)}" target="_blank" rel="noreferrer">Recovery docs ↗</a>
        </div>
      </div>
    `;

    this._wireEvents();
  }

  _wireEvents() {
    const root = this.shadowRoot;
    if (!root) return;

    const engage = root.querySelector('#rc-am-engage');
    if (engage) {
      engage.addEventListener('click', () => this._engage());
    }
    const disengage = root.querySelector('#rc-am-disengage');
    if (disengage) {
      disengage.addEventListener('click', () => this._disengage());
    }
  }

  getCardSize() {
    return 3;
  }

  // ---------------------------------------------------------------------------
  // Utils
  // ---------------------------------------------------------------------------

  _esc(s) {
    if (s === undefined || s === null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }
}

customElements.define('roamcore-advanced-mode', RoamCoreAdvancedModeCard);

// Register with HACS / custom card picker
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'roamcore-advanced-mode',
  name: 'RoamCore Advanced Mode',
  description: 'One-tap Advanced Mode toggle with safe recovery (snapshot + audit)',
  preview: true,
});

// Export for tooling (node --check passes ESM-style module.exports guard).
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { RoamCoreAdvancedModeCard };
}

console.log('RoamCore Advanced Mode card loaded');