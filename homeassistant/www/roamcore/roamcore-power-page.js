// RoamCore Power detail page (v1) — capability-driven custom Lovelace card.
//
// Loads power-capabilities.json and renders only the tiles whose required
// rc_* contract entities exist in the live HA state. Extends the global
// RoamcoreBasePage shipped in roamcore-pages.js for shared helpers/CSS.

(function () {
  'use strict';
  if (typeof window === 'undefined' || !window.customElements) return;
  if (customElements.get('roamcore-power-page')) return;

  const CAPS_URLS = [
    '/local/roamcore/power-capabilities.json',
    './power-capabilities.json',
  ];

  function _isMissing(v) {
    const s = (v == null) ? '' : String(v);
    const t = s.toLowerCase();
    return !s || t === 'unknown' || t === 'unavailable' || t === 'none';
  }
  const _round1 = (n) => (n == null || !Number.isFinite(Number(n))) ? '—' : (Math.round(Number(n) * 10) / 10).toString();
  const _round0 = (n) => (n == null || !Number.isFinite(Number(n))) ? '—' : Math.round(Number(n)).toString();

  async function loadCapabilities() {
    let lastErr = null;
    for (const url of CAPS_URLS) {
      try {
        const res = await fetch(url, { credentials: 'same-origin', cache: 'no-cache' });
        if (res.ok) {
          const data = await res.json();
          if (data && Array.isArray(data.tiles)) return data;
          lastErr = new Error(`Invalid manifest at ${url}: missing tiles[]`);
        } else {
          lastErr = new Error(`HTTP ${res.status} on ${url}`);
        }
      } catch (e) { lastErr = e; }
    }
    throw lastErr || new Error('Could not load power-capabilities.json');
  }

  function makeCapHelpers(hass) {
    const states = (hass && hass.states) || {};
    function cap(entityId, fallback) {
      const v = states[entityId] && states[entityId].state;
      if (_isMissing(v)) return fallback == null ? '—' : fallback;
      return v;
    }
    function capNum(entityId, fallback) {
      const v = cap(entityId, null);
      if (v == null) return fallback == null ? null : fallback;
      const n = Number(v);
      return Number.isFinite(n) ? n : (fallback == null ? null : fallback);
    }
    return { cap, capNum, states };
  }

  // Tile renderers — each receives (page, helpers) where helpers = {cap, capNum}.
  const T = {
    battery(page, h) {
      const soc = h.capNum('sensor.rc_power_battery_soc', null);
      const socDisplay = soc == null ? null : Math.round(soc);
      const status = socDisplay == null ? 'inactive'
        : socDisplay >= 60 ? 'good'
        : socDisplay >= 30 ? 'ok' : 'bad';
      const c = status === 'good' ? 'var(--rc-good)'
        : status === 'ok' ? 'var(--rc-ok)'
        : status === 'bad' ? 'var(--rc-bad)'
        : status === 'inactive' ? 'var(--rc-inactive)' : 'var(--rc-muted)';
      const volt = h.capNum('sensor.rc_power_battery_voltage', null);
      const amp = h.capNum('sensor.rc_power_battery_current', null);
      const t1 = h.capNum('sensor.rc_power_battery_temperature', null);
      const t2 = h.capNum('sensor.rc_power_battery_temperature_2', null);
      const temp = t1 != null ? t1 : t2;
      const capAh = h.capNum('sensor.rc_power_battery_capacity', null);
      const cyc = h.capNum('sensor.rc_power_battery_cycle_count', null);
      const hlth = h.capNum('sensor.rc_power_battery_health', null);
      const ttf = h.cap('sensor.rc_power_battery_time_to_full', '—');
      const top = `
        <div style="display:flex; gap:14px; align-items:center; margin-bottom: 12px;">
          ${page._batterySvg(socDisplay == null ? 0 : socDisplay, c)}
          <div class="rc-value">
            <div class="rc-value-num rc-value-xl" style="color:${c}">${socDisplay == null ? '—' : socDisplay}</div>
            <div class="rc-value-unit">%</div>
          </div>
          ${page._badge(status === 'good' ? 'Healthy' : status === 'ok' ? 'OK' : status === 'bad' ? 'Low' : '—', status)}
        </div>
      `;
      return top
        + page._row('Voltage', volt == null ? '—' : _round1(volt), 'V', '', 'sensor.rc_power_battery_voltage')
        + page._row('Current', amp == null ? '—' : _round1(amp), 'A', '', 'sensor.rc_power_battery_current')
        + page._row('Temperature', temp == null ? '—' : _round1(temp), '°C', '', temp == null ? '' : 'sensor.rc_power_battery_temperature')
        + page._row('Time to Full', ttf, '', '', ttf === '—' ? '' : 'sensor.rc_power_battery_time_to_full')
        + (capAh == null ? '' : page._row('Capacity', _round1(capAh), 'Ah', '', 'sensor.rc_power_battery_capacity'))
        + (cyc == null ? '' : page._row('Cycles', _round0(cyc), '', '', 'sensor.rc_power_battery_cycle_count'))
        + (hlth == null ? '' : page._row('Health', _round0(hlth), '%', '', 'sensor.rc_power_battery_health'));
    },

    solar(page, h) {
      const w = h.capNum('sensor.rc_power_solar_power', null);
      const today = h.capNum('sensor.rc_power_solar_energy_today', null);
      const total = h.capNum('sensor.rc_power_solar_energy_total', null);
      const pv = h.capNum('sensor.rc_power_solar_panel_voltage', null);
      const pa = h.capNum('sensor.rc_power_solar_panel_current', null);
      const eff = h.capNum('sensor.rc_power_solar_efficiency', null);
      const pv2 = h.capNum('sensor.rc_power_solar_pv2_power', null);
      const top = `
        <div class="rc-value" style="margin-bottom:10px;">
          <div class="rc-value-num rc-value-lg" data-more="sensor.rc_power_solar_power" style="color:var(--rc-good)">${w == null ? '—' : _round0(w)}</div>
          <div class="rc-value-unit">W</div>
        </div>
      `;
      return top
        + (today == null ? '' : page._row('Today', _round1(today), 'kWh', '', 'sensor.rc_power_solar_energy_today'))
        + (total == null ? '' : page._row('Total', _round1(total), 'kWh', '', 'sensor.rc_power_solar_energy_total'))
        + (pv == null ? '' : page._row('Panel V', _round1(pv), 'V', '', 'sensor.rc_power_solar_panel_voltage'))
        + (pa == null ? '' : page._row('Panel A', _round1(pa), 'A', '', 'sensor.rc_power_solar_panel_current'))
        + (eff == null ? '' : page._row('Efficiency', _round0(eff), '%', '', 'sensor.rc_power_solar_efficiency'))
        + (pv2 == null ? '' : page._row('PV2', _round0(pv2), 'W', '', 'sensor.rc_power_solar_pv2_power'));
    },

    inverter(page, h) {
      const inv = h.cap('sensor.rc_power_inverter_status', null);
      const w = h.capNum('sensor.rc_power_inverter_output_power', null);
      const v = h.capNum('sensor.rc_power_inverter_output_voltage', null);
      const hz = h.capNum('sensor.rc_power_inverter_frequency', null);
      const t = h.capNum('sensor.rc_power_inverter_temperature', null);
      const lbl = (inv && inv !== 'unknown' && inv !== 'unavailable')
        ? inv.charAt(0).toUpperCase() + inv.slice(1) : '—';
      const status = (inv && inv !== 'off') ? 'good' : 'inactive';
      return `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 10px;">
          <div data-more="sensor.rc_power_inverter_status">${page._badge(lbl, status)}</div>
          <div class="rc-label" style="text-transform:uppercase; font-weight:700;">AC out</div>
        </div>
        ${page._row('Output', w == null ? '—' : _round0(w), 'W', '', 'sensor.rc_power_inverter_output_power')}
        ${page._row('Voltage', v == null ? '—' : _round1(v), 'V', '', 'sensor.rc_power_inverter_output_voltage')}
        ${page._row('Frequency', hz == null ? '—' : _round1(hz), 'Hz', '', 'sensor.rc_power_inverter_frequency')}
        ${page._row('Temperature', t == null ? '—' : _round1(t), '°C', '', 'sensor.rc_power_inverter_temperature')}
      `;
    },

    shore(page, h) {
      const s = h.cap('binary_sensor.rc_power_shore_connected', null);
      const v = h.capNum('sensor.rc_power_shore_voltage', null);
      const a = h.capNum('sensor.rc_power_shore_current', null);
      const w = h.capNum('sensor.rc_power_shore_power', null);
      const acIn = h.capNum('sensor.rc_power_ac_in_power', null);
      const lbl = s === 'on' ? 'Connected' : (s === 'off' ? 'Disconnected' : '—');
      const status = s === 'on' ? 'good' : 'inactive';
      return `
        <div style="margin-bottom: 10px;">
          <div data-more="binary_sensor.rc_power_shore_connected">${page._badge(lbl, status)}</div>
        </div>
        ${page._row('Voltage', v == null ? '—' : _round1(v), v == null ? '' : 'V', '', 'sensor.rc_power_shore_voltage')}
        ${page._row('Current', a == null ? '—' : _round1(a), a == null ? '' : 'A', '', 'sensor.rc_power_shore_current')}
        ${page._row('Power', w == null ? '—' : _round0(w), w == null ? '' : 'W', '', 'sensor.rc_power_shore_power')}
        ${acIn == null ? '' : page._row('AC In', _round0(acIn), 'W', '', 'sensor.rc_power_ac_in_power')}
      `;
    },

    alternator(page, h) {
      const v = h.capNum('sensor.rc_power_alternator_voltage', null);
      const a = h.capNum('sensor.rc_power_alternator_current', null);
      const w = h.capNum('sensor.rc_power_alternator_power', null);
      const charging = a != null && Math.abs(a) > 0.5;
      const status = charging ? 'good' : 'inactive';
      const lbl = charging ? 'Charging' : 'Idle';
      return `
        <div style="margin-bottom: 10px;">${page._badge(lbl, status)}</div>
        ${page._row('Voltage', v == null ? '—' : _round1(v), v == null ? '' : 'V', '', 'sensor.rc_power_alternator_voltage')}
        ${page._row('Current', a == null ? '—' : _round1(a), a == null ? '' : 'A', '', 'sensor.rc_power_alternator_current')}
        ${page._row('Power', w == null ? '—' : _round0(w), w == null ? '' : 'W', '', 'sensor.rc_power_alternator_power')}
      `;
    },

    'cell-bms'(page, h) {
      const cells = h.cap('sensor.rc_power_battery_cells_voltage', '—');
      const t1 = h.capNum('sensor.rc_power_battery_temperature', null);
      const t2 = h.capNum('sensor.rc_power_battery_temperature_2', null);
      const temp = t1 != null ? t1 : t2;
      const hlth = h.capNum('sensor.rc_power_battery_health', null);
      return `
        <div style="margin-bottom: 10px;">
          ${page._badge(cells === '—' ? '—' : 'Cells', cells === '—' ? 'inactive' : 'good')}
        </div>
        ${page._row('Cells', cells, '', '', cells === '—' ? '' : 'sensor.rc_power_battery_cells_voltage')}
        ${temp == null ? '' : page._row('Temperature', _round1(temp), '°C', '', 'sensor.rc_power_battery_temperature')}
        ${hlth == null ? '' : page._row('Health', _round0(hlth), '%', '', 'sensor.rc_power_battery_health')}
      `;
    },

    'dc-loads'(page, h) {
      const w = h.capNum('sensor.rc_power_load_power', null);
      const f = h.capNum('sensor.rc_power_load_fridge', null);
      const li = h.capNum('sensor.rc_power_load_lights', null);
      const ht = h.capNum('sensor.rc_power_load_heater', null);
      const p = h.capNum('sensor.rc_power_load_water_pump', null);
      const o = h.capNum('sensor.rc_power_load_other', null);
      const cur = h.capNum('sensor.rc_power_dc_load_current', null);
      const top = `
        <div class="rc-value" style="margin-bottom:10px;">
          <div class="rc-value-num rc-value-lg" data-more="sensor.rc_power_load_power">${w == null ? '—' : _round0(w)}</div>
          <div class="rc-value-unit">W</div>
        </div>
      `;
      return top
        + (cur == null ? '' : page._row('Current', _round1(cur), 'A', '', 'sensor.rc_power_dc_load_current'))
        + (f == null ? '' : page._row('Fridge', _round0(f), 'W', '', 'sensor.rc_power_load_fridge'))
        + (li == null ? '' : page._row('Lights', _round0(li), 'W', '', 'sensor.rc_power_load_lights'))
        + (ht == null ? '' : page._row('Heater', _round0(ht), 'W', (ht == 0 || ht == null) ? 'var(--rc-inactive)' : '', 'sensor.rc_power_load_heater'))
        + (p == null ? '' : page._row('Water Pump', _round0(p), 'W', '', 'sensor.rc_power_load_water_pump'))
        + (o == null ? '' : page._row('Other', _round0(o), 'W', '', 'sensor.rc_power_load_other'));
    },

    history(page, h) {
      const soc = h.capNum('sensor.rc_power_battery_soc', null);
      const solar = h.capNum('sensor.rc_power_solar_power', null);
      const load = h.capNum('sensor.rc_power_load_power', null);
      const todayGen = h.capNum('sensor.rc_power_solar_energy_today', null);
      const net = (solar != null && load != null) ? Math.round(solar - load) : null;
      return `
        <div class="rc-grid rc-grid-2">
          <div>
            <div class="rc-label" style="margin-bottom:4px;">Net Power</div>
            <div class="rc-value"><div class="rc-value-num rc-value-md" style="color:var(--rc-good)">${net == null ? '—' : (net >= 0 ? '+' : '') + net}</div><div class="rc-value-unit">W</div></div>
          </div>
          <div>
            <div class="rc-label" style="margin-bottom:4px;">Today Generation</div>
            <div class="rc-value"><div class="rc-value-num rc-value-md">${todayGen == null ? '—' : _round1(todayGen)}</div><div class="rc-value-unit">kWh</div></div>
          </div>
          <div>
            <div class="rc-label" style="margin-bottom:4px;">Battery SoC</div>
            <div class="rc-value"><div class="rc-value-num rc-value-md" data-more="sensor.rc_power_battery_soc">${soc == null ? '—' : _round0(soc)}</div><div class="rc-value-unit">%</div></div>
          </div>
          <div>
            <div class="rc-label" style="margin-bottom:4px;">DC Load</div>
            <div class="rc-value"><div class="rc-value-num rc-value-md" data-more="sensor.rc_power_load_power">${load == null ? '—' : _round0(load)}</div><div class="rc-value-unit">W</div></div>
          </div>
        </div>
      `;
    },
  };

  const BasePage = (typeof window !== 'undefined') ? window.RoamcoreBasePage : null;
  if (!BasePage) {
    console.warn('roamcore-power-page.js: RoamcoreBasePage is not defined yet. Ensure roamcore-pages.js loads before this file.');
    return;
  }

  class RoamcorePowerPageNew extends BasePage {
    constructor() {
      super();
      this._manifest = null;
      this._manifestError = null;
    }

    setConfig(config) {
      // Trigger initial render + kick off manifest load.
      super.setConfig(config);
      if (!this._manifest && !this._manifestLoading) this._loadManifest();
    }

    set hass(hass) {
      this._hass = hass;
      this._render();
    }

    async _loadManifest() {
      this._manifestLoading = true;
      try {
        this._manifest = await loadCapabilities();
        this._manifestError = null;
      } catch (e) {
        this._manifestError = e;
      } finally {
        this._manifestLoading = false;
      }
      this._render();
    }

    _hasAll(ids) {
      const states = (this._hass && this._hass.states) || {};
      for (const id of ids) {
        const s = states[id] && states[id].state;
        if (_isMissing(s)) return false;
      }
      return true;
    }

    _render() {
      if (!this._root || !this._hass) return;

      const manifest = this._manifest;
      if (!manifest) {
        const msg = this._manifestError
          ? `Capabilities manifest not loaded: ${this._escape(String(this._manifestError.message || this._manifestError))}`
          : 'Loading\u2026';
        this._root.innerHTML = `
          <div class="rc-page">
            <div class="rc-subheader"><div class="rc-subtitle">Power</div><div class="rc-subspacer"></div></div>
            <div class="rc-empty">${msg}</div>
          </div>
        `;
        return;
      }

      const visibleTiles = (manifest.tiles || []).filter((t) => this._hasAll(t.required || []));

      // Empty state.
      if (visibleTiles.length === 0) {
        const setupPath = `${this._basePath()}/setup`;
        this._root.innerHTML = `
          <div class="rc-page">
            <div class="rc-subheader"><div class="rc-subtitle">Power</div><div class="rc-subspacer"></div></div>
            <div class="rc-empty-card">
              <div class="rc-empty-title">Victron not connected</div>
              <div class="rc-empty-sub">No power entities are reporting yet. Open the setup wizard to discover and pair your Victron GX.</div>
              <button class="rc-btn rc-btn-primary" id="rc-empty-setup-btn">Open setup wizard</button>
            </div>
          </div>
        `;
        const btn = this._root.querySelector('#rc-empty-setup-btn');
        if (btn) btn.addEventListener('click', () => this._navigate(setupPath));
        return;
      }

      const helpers = makeCapHelpers(this._hass);
      const tileHtml = visibleTiles.map((tile) => {
        const renderer = T[tile.id];
        if (!renderer) return '';
        const body = renderer(this, helpers);
        const span = tile.span === 2 ? 'span-2' : '';
        const icon = tile.icon || '';
        return `
          <div class="rc-dtile ${span}">
            <div class="rc-dtile-head">
              <div class="rc-dtile-title">${tile.title}</div>
              <div class="rc-dtile-icon">${icon}</div>
            </div>
            <div class="rc-dtile-body">${body}</div>
          </div>
        `;
      }).join('\n');

      this._root.innerHTML = `
        <div class="rc-page">
          ${this._header('Power')}
          <div class="rc-grid rc-power-grid">
            ${tileHtml}
          </div>
        </div>
      `;
    }

    _css() {
      // Overlay: reuse the base page's CSS verbatim, then add the auto-fit
      // grid + empty-state card. We intentionally don't redefine the rest
      // of the styles so they stay consistent with other RoamCore pages.
      return super._css() + `
        .rc-power-grid {
          grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        }
        .rc-empty-card {
          background: linear-gradient(180deg, var(--rc-card), var(--rc-card2));
          border: 1px solid var(--rc-border);
          border-radius: 14px;
          padding: 22px;
          box-shadow: 0 6px 18px rgba(0,0,0,0.35);
          display: flex; flex-direction: column; gap: 10px; align-items: flex-start;
        }
        .rc-empty-title { font-size: 18px; font-weight: 800; }
        .rc-empty-sub { color: var(--rc-muted); font-size: 14px; line-height: 1.4; }
        .rc-empty { color: var(--rc-muted); padding: 10px 0; }
        .rc-btn {
          border: 1px solid var(--rc-border);
          background: rgba(255,255,255,0.06);
          color: var(--rc-text);
          padding: 10px 14px;
          border-radius: 10px;
          cursor: pointer;
          font-weight: 700;
        }
        .rc-btn-primary { background: var(--rc-good); color: #0b1d10; border-color: var(--rc-good); }
      `;
    }

    _escape(s) {
      return String(s == null ? '' : s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    }
  }

  customElements.define('roamcore-power-page', RoamcorePowerPageNew);
})();