/**
 * RoamCore Mode Builder Card
 *
 * A Lovelace custom card that gives the user:
 *   1. A one-tap 5-segment mode picker (auto / travel / camp / stealth / off).
 *   2. A list of simple "when X, switch to mode Y" rules with per-rule
 *      enable/disable.
 *   3. An "Add rule" modal that lets the user create a new rule with a
 *      name, an HA entity, an op, a value, and a target mode.
 *   4. A "Reset to defaults" button that re-seeds the two example rules.
 *
 * Wiring contract (matches homeassistant/packages/roamcore_mode.yaml +
 * homeassistant/packages/roamcore_mode_builder.yaml):
 *
 *   input_select.rc_mode                  (current mode; 5 options)
 *   input_text.rc_mode_rules_json         (JSON array of rule objects)
 *
 *   Custom events (UI-side):
 *     roamcore_mode_rule_toggle  { id: string, enabled: bool }
 *       → automation on YAML side re-writes rc_mode_rules_json
 *
 *   Custom service calls (UI-side):
 *     input_select.select_option / option=<mode>
 *
 * The card hides itself cleanly if input_select.rc_mode is missing,
 * matching the existing RcAmenitiesLayer pattern for
 * input_boolean.rc_amenities_overlay_enabled.
 *
 * Usage in lovelace:
 *   type: custom:roamcore-mode-builder
 */

class RoamCoreModeBuilderCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._config = {};
    this._hass = null;
    this._rules = [];
    this._modalOpen = false;
    this._editingRule = null; // null = adding a new rule
  }

  static getStubConfig() {
    return { title: 'Mode builder' };
  }

  setConfig(config) {
    this._config = config || {};
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._loadRules();
    this._render();
  }

  connectedCallback() {
    this._render();
  }

  // ---------------------------------------------------------------------------
  // Data helpers
  // ---------------------------------------------------------------------------

  _modeEntity() {
    return this._hass?.states?.['input_select.rc_mode'] ? 'input_select.rc_mode' : null;
  }

  _rulesEntity() {
    return this._hass?.states?.['input_text.rc_mode_rules_json'] ? 'input_text.rc_mode_rules_json' : null;
  }

  _currentMode() {
    const ent = this._modeEntity();
    if (!ent) return null;
    const st = this._hass.states[ent];
    return st ? st.state : null;
  }

  _loadRules() {
    const ent = this._rulesEntity();
    if (!ent) {
      this._rules = [];
      return;
    }
    const raw = this._hass.states[ent]?.state ?? '[]';
    try {
      const parsed = JSON.parse(raw);
      this._rules = Array.isArray(parsed) ? parsed : [];
    } catch (e) {
      console.warn('RoamCore mode builder: invalid rules JSON', e);
      this._rules = [];
    }
  }

  async _setMode(mode) {
    if (!this._hass) return;
    if (!['auto', 'travel', 'camp', 'stealth', 'off'].includes(mode)) return;
    try {
      await this._hass.callService('input_select', 'select_option', {
        entity_id: 'input_select.rc_mode',
        option: mode,
      });
    } catch (e) {
      console.warn('RoamCore mode builder: failed to set mode', e);
    }
  }

  async _saveRules() {
    if (!this._hass) return;
    try {
      await this._hass.callService('input_text', 'set_value', {
        entity_id: 'input_text.rc_mode_rules_json',
        value: JSON.stringify(this._rules),
      });
    } catch (e) {
      console.warn('RoamCore mode builder: failed to save rules', e);
    }
  }

  async _toggleRule(id, enabled) {
    if (!this._hass) return;
    // Fire a custom event; the YAML automation listens and updates
    // rc_mode_rules_json. This is the documented dispatch path so that
    // the YAML side stays the source of truth for persistence.
    try {
      this._hass.callService('roamcore_mode', 'rule_toggle', {
        id,
        enabled,
      }).catch(() => {});
    } catch (e) {}
    // Best-effort optimistic update so the UI feels instant; the YAML
    // automation will overwrite rc_mode_rules_json in the background.
    const rule = this._rules.find((r) => r && r.id === id);
    if (rule) {
      rule.enabled = !!enabled;
      this._saveRules();
      this._render();
    }
  }

  async _resetDefaults() {
    if (!this._hass) return;
    try {
      await this._hass.callService('script', 'turn_on', {
        entity_id: 'script.rc_mode_rules_seed_defaults',
      });
    } catch (e) {
      console.warn('RoamCore mode builder: failed to reset defaults', e);
    }
  }

  // ---------------------------------------------------------------------------
  // Rendering
  // ---------------------------------------------------------------------------

  _render() {
    const root = this.shadowRoot;
    if (!root) return;

    const mode = this._currentMode();
    if (!mode) {
      // Hide cleanly if the mode contract entity is missing.
      root.innerHTML = '';
      return;
    }

    const modes = ['auto', 'travel', 'camp', 'stealth', 'off'];
    const pills = modes
      .map(
        (m) => `
        <button class="rc-pill ${m === mode ? 'active' : ''}" data-mode="${this._esc(m)}">
          ${this._esc(this._cap(m))}
        </button>`
      )
      .join('');

    const rulesHtml = this._rules.length
      ? this._rules.map((r) => this._renderRule(r)).join('')
      : `<div class="rc-empty">No rules yet. Tap + Add rule to create one.</div>`;

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
        .title {
          font-weight: 900;
          font-size: 14px;
          margin: 0 0 10px 0;
        }
        .sub {
          font-size: 12px;
          opacity: 0.7;
          margin: 0 0 10px 0;
        }
        .pills {
          display: flex;
          gap: 6px;
          flex-wrap: wrap;
          margin-bottom: 14px;
        }
        .rc-pill {
          flex: 1 1 auto;
          min-width: 56px;
          padding: 8px 6px;
          font-weight: 700;
          font-size: 12px;
          border-radius: 999px;
          border: 1px solid rgba(255,255,255,0.12);
          background: rgba(255,255,255,0.04);
          color: inherit;
          cursor: pointer;
          text-transform: capitalize;
        }
        .rc-pill.active {
          background: rgba(0, 200, 120, 0.18);
          border-color: rgba(0, 200, 120, 0.55);
          color: #fff;
        }
        .section-title {
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-weight: 800;
          font-size: 12px;
          opacity: 0.85;
          margin: 6px 0 8px 0;
        }
        .rule {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
          padding: 8px 10px;
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(255,255,255,0.06);
          border-radius: 10px;
          margin-bottom: 6px;
        }
        .rule-main {
          flex: 1 1 auto;
          min-width: 0;
        }
        .rule-name {
          font-weight: 700;
          font-size: 12px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .rule-when {
          font-size: 11px;
          opacity: 0.7;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .rule-when code {
          font-size: 10px;
          opacity: 0.85;
        }
        .rule-actions {
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .toggle {
          position: relative;
          width: 32px;
          height: 18px;
          border-radius: 999px;
          background: rgba(255,255,255,0.18);
          cursor: pointer;
          border: none;
          padding: 0;
        }
        .toggle.on {
          background: rgba(0, 200, 120, 0.65);
        }
        .toggle::after {
          content: '';
          position: absolute;
          top: 2px;
          left: 2px;
          width: 14px;
          height: 14px;
          background: #fff;
          border-radius: 50%;
          transition: left 0.15s ease-in-out;
        }
        .toggle.on::after {
          left: 16px;
        }
        .row-actions {
          display: flex;
          gap: 8px;
          margin-top: 10px;
          flex-wrap: wrap;
        }
        .rc-btn {
          padding: 6px 12px;
          border-radius: 8px;
          border: 1px solid rgba(255,255,255,0.18);
          background: rgba(255,255,255,0.05);
          color: inherit;
          font-size: 12px;
          font-weight: 700;
          cursor: pointer;
        }
        .rc-btn:hover {
          background: rgba(255,255,255,0.10);
        }
        .rc-empty {
          font-size: 12px;
          opacity: 0.7;
          padding: 8px 0;
        }
        .modal-bg {
          position: fixed;
          inset: 0;
          background: rgba(0,0,0,0.55);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 9999;
        }
        .modal {
          background: var(--card-background-color, #1c1c1c);
          color: inherit;
          border-radius: 12px;
          padding: 16px;
          width: min(92vw, 420px);
          border: 1px solid rgba(255,255,255,0.12);
        }
        .modal h3 {
          margin: 0 0 10px 0;
          font-size: 14px;
          font-weight: 900;
        }
        .modal label {
          display: block;
          font-size: 11px;
          opacity: 0.75;
          margin-top: 8px;
          margin-bottom: 4px;
        }
        .modal input,
        .modal select {
          width: 100%;
          padding: 6px 8px;
          border-radius: 6px;
          border: 1px solid rgba(255,255,255,0.18);
          background: rgba(255,255,255,0.04);
          color: inherit;
          font-size: 12px;
          box-sizing: border-box;
        }
        .modal-actions {
          display: flex;
          justify-content: flex-end;
          gap: 8px;
          margin-top: 14px;
        }
      </style>

      <div class="card">
        <div class="title">${this._esc(this._config.title || 'Mode builder')}</div>
        <div class="sub">Current mode: <b style="text-transform: capitalize;">${this._esc(mode)}</b></div>
        <div class="pills">${pills}</div>

        <div class="section-title">
          <span>Rules (${this._rules.length})</span>
        </div>
        <div>${rulesHtml}</div>

        <div class="row-actions">
          <button class="rc-btn" id="rc-mode-add">+ Add rule</button>
          <button class="rc-btn" id="rc-mode-reset">Reset to defaults</button>
        </div>
      </div>

      ${this._modalOpen ? this._renderModal() : ''}
    `;

    this._wireEvents();
  }

  _renderRule(rule) {
    if (!rule || !rule.when) return '';
    const enabled = rule.enabled !== false;
    const w = rule.when || {};
    const entityShort = String(w.entity || '').split('.')[1] || String(w.entity || '');
    const op = w.op || '==';
    const value = w.value;
    const thenMode = this._esc(rule.then || 'auto');
    return `
      <div class="rule" data-id="${this._esc(rule.id || '')}">
        <div class="rule-main">
          <div class="rule-name">${this._esc(rule.name || '(unnamed)')}</div>
          <div class="rule-when">when <code>${this._esc(entityShort)}</code> ${this._esc(op)} <code>${this._esc(String(value))}</code> → <b style="text-transform: capitalize;">${this._esc(thenMode)}</b></div>
        </div>
        <div class="rule-actions">
          <button class="toggle ${enabled ? 'on' : ''}" data-toggle="${this._esc(rule.id || '')}" aria-label="Toggle rule"></button>
        </div>
      </div>
    `;
  }

  _renderModal() {
    const r = this._editingRule || { when: { entity: '', op: '==', value: '' }, then: 'auto', name: '' };
    const modes = ['auto', 'travel', 'camp', 'stealth', 'off'];
    const modeOptions = modes
      .map((m) => `<option value="${m}" ${r.then === m ? 'selected' : ''}>${this._cap(m)}</option>`)
      .join('');
    const ops = ['<', '>', '<=', '>=', '==', '!='];
    const opOptions = ops
      .map((o) => `<option value="${o}" ${r.when.op === o ? 'selected' : ''}>${o}</option>`)
      .join('');
    return `
      <div class="modal-bg" id="rc-mode-modal-bg">
        <div class="modal" role="dialog" aria-label="Add rule">
          <h3>Add rule</h3>
          <label>Name</label>
          <input id="rc-mode-modal-name" type="text" value="${this._esc(r.name || '')}" placeholder="When battery is low, switch to stealth" />
          <label>When entity (HA entity_id)</label>
          <input id="rc-mode-modal-entity" type="text" value="${this._esc(r.when.entity || '')}" placeholder="sensor.rc_battery_soc" />
          <label>Op</label>
          <select id="rc-mode-modal-op">${opOptions}</select>
          <label>Value</label>
          <input id="rc-mode-modal-value" type="text" value="${this._esc(String(r.when.value ?? ''))}" placeholder="20" />
          <label>Then mode</label>
          <select id="rc-mode-modal-then">${modeOptions}</select>
          <div class="modal-actions">
            <button class="rc-btn" id="rc-mode-modal-cancel">Cancel</button>
            <button class="rc-btn" id="rc-mode-modal-save">Save</button>
          </div>
        </div>
      </div>
    `;
  }

  _wireEvents() {
    const root = this.shadowRoot;
    if (!root) return;

    // Mode pills
    root.querySelectorAll('.rc-pill').forEach((btn) => {
      btn.addEventListener('click', () => {
        const mode = btn.getAttribute('data-mode');
        if (mode) this._setMode(mode);
      });
    });

    // Rule toggles
    root.querySelectorAll('[data-toggle]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-toggle');
        const on = btn.classList.contains('on');
        this._toggleRule(id, !on);
      });
    });

    // Add rule button
    const addBtn = root.querySelector('#rc-mode-add');
    if (addBtn) {
      addBtn.addEventListener('click', () => {
        this._editingRule = null;
        this._modalOpen = true;
        this._render();
      });
    }

    // Reset defaults
    const resetBtn = root.querySelector('#rc-mode-reset');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => this._resetDefaults());
    }

    // Modal events
    if (this._modalOpen) {
      const bg = root.querySelector('#rc-mode-modal-bg');
      if (bg) {
        bg.addEventListener('click', (e) => {
          if (e.target === bg) {
            this._modalOpen = false;
            this._render();
          }
        });
      }
      const cancel = root.querySelector('#rc-mode-modal-cancel');
      if (cancel) {
        cancel.addEventListener('click', () => {
          this._modalOpen = false;
          this._render();
        });
      }
      const save = root.querySelector('#rc-mode-modal-save');
      if (save) {
        save.addEventListener('click', () => this._saveModalRule());
      }
    }
  }

  async _saveModalRule() {
    const root = this.shadowRoot;
    if (!root) return;
    const name = root.querySelector('#rc-mode-modal-name')?.value?.trim() || 'Untitled rule';
    const entity = root.querySelector('#rc-mode-modal-entity')?.value?.trim();
    const op = root.querySelector('#rc-mode-modal-op')?.value || '==';
    const valueRaw = root.querySelector('#rc-mode-modal-value')?.value ?? '';
    const then = root.querySelector('#rc-mode-modal-then')?.value || 'auto';
    if (!entity) {
      console.warn('RoamCore mode builder: rule entity is required');
      return;
    }
    // Coerce value to number when possible; otherwise pass as string.
    const value = valueRaw === '' ? '' : (Number.isFinite(Number(valueRaw)) && valueRaw.trim() !== '') ? Number(valueRaw) : valueRaw;
    const id = 'rule_' + (crypto?.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2, 10));
    const rule = {
      id,
      name,
      when: { entity, op, value },
      then,
      enabled: true,
      cooldownMin: 15,
    };
    this._rules = [...this._rules, rule];
    await this._saveRules();
    this._modalOpen = false;
    this._render();
  }

  getCardSize() {
    return 4;
  }

  // ---------------------------------------------------------------------------
  // Utils
  // ---------------------------------------------------------------------------

  _cap(s) {
    if (!s) return '';
    return String(s).charAt(0).toUpperCase() + String(s).slice(1);
  }

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

customElements.define('roamcore-mode-builder', RoamCoreModeBuilderCard);

// Register with HACS / custom card picker
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'roamcore-mode-builder',
  name: 'RoamCore Mode Builder',
  description: 'One-tap mode picker + simple "when X then switch to mode Y" rules',
  preview: true,
});

// Export for tooling (node --check passes ESM-style module.exports guard).
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { RoamCoreModeBuilderCard };
}

console.log('RoamCore Mode Builder card loaded');
