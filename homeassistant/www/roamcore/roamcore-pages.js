// RoamCore Pages (v0) - Power + Network subpages as custom Lovelace cards
// Goal: translate v0/lovable TSX pages into HAOS without depending on HA default card styling.
// Naming convention reference: RoamCore/docs/reference/rc-entity-naming.md

function rcStatusToColor(status) {
  if (status === 'good') return 'var(--rc-good)';
  if (status === 'ok') return 'var(--rc-ok)';
  if (status === 'bad') return 'var(--rc-bad)';
  if (status === 'inactive') return 'var(--rc-inactive)';
  return 'var(--rc-muted)';
}

function rcStatusLabel(status) {
  if (status === 'good') return 'Healthy';
  if (status === 'ok') return 'OK';
  if (status === 'bad') return 'Poor';
  if (status === 'inactive') return 'Inactive';
  return '—';
}

function rcCap(s) {
  if (!s) return '—';
  return String(s).charAt(0).toUpperCase() + String(s).slice(1);
}

function rcPowerStatusFromSoc(soc) {
  if (soc == null) return 'ok';
  if (soc >= 60) return 'good';
  if (soc >= 30) return 'ok';
  return 'bad';
}

function rcLevelStatusFromPitchRoll(pitch, roll) {
  const pv = (pitch==null||pitch!=pitch) ? 0 : Math.abs(Number(pitch));
  const rv = (roll==null||roll!=roll) ? 0 : Math.abs(Number(roll));
  const v = Math.max(pv, rv);
  if (!isFinite(v)) return { label: '—', status: 'inactive' };
  if (v < 2) return { label: 'Level', status: 'good' };
  if (v < 6) return { label: 'Slight Tilt', status: 'ok' };
  return { label: 'Not Level', status: 'bad' };
}

function rcVanSideSvg() {
  return `
    <svg viewBox="0 0 80 40" class="rc-van">
      <g fill="none" stroke="rgba(255,255,255,0.35)" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
        <path d="M8 30 L8 18 L20 18 L28 10 L68 10 L68 30" />
        <path d="M28 10 L28 18 L68 18" />
        <rect x="30" y="12" width="8" height="5" rx="0.5" />
        <rect x="42" y="12" width="8" height="5" rx="0.5" />
        <rect x="54" y="12" width="10" height="5" rx="0.5" />
        <line x1="40" y1="18" x2="40" y2="30" />
        <path d="M14 30 A6 6 0 0 1 26 30" />
        <path d="M54 30 A6 6 0 0 1 66 30" />
      </g>
      <circle cx="20" cy="32" r="4" fill="rgba(255,255,255,0.25)" />
      <circle cx="60" cy="32" r="4" fill="rgba(255,255,255,0.25)" />
    </svg>
  `;
}

function rcVanBackSvg() {
  return `
    <svg viewBox="0 0 50 45" class="rc-van">
      <g fill="none" stroke="rgba(255,255,255,0.35)" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
        <rect x="6" y="8" width="38" height="28" rx="2" />
        <line x1="25" y1="12" x2="25" y2="36" />
        <rect x="10" y="12" width="11" height="8" rx="0.5" />
        <rect x="29" y="12" width="11" height="8" rx="0.5" />
        <rect x="8" y="28" width="3" height="6" rx="0.5" />
        <rect x="39" y="28" width="3" height="6" rx="0.5" />
      </g>
      <circle cx="10" cy="39" r="3.5" fill="rgba(255,255,255,0.25)" />
      <circle cx="40" cy="39" r="3.5" fill="rgba(255,255,255,0.25)" />
    </svg>
  `;
}

function rcMiniMapSvg() {
  return `
    <svg viewBox="0 0 100 60" class="rc-map" preserveAspectRatio="none">
      <defs>
        <pattern id="grid" width="12" height="12" patternUnits="userSpaceOnUse">
          <path d="M 12 0 L 0 0 0 12" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="1" />
        </pattern>
      </defs>
      <rect width="100" height="60" fill="url(#grid)" />
      <path d="M10 50 Q 30 30, 50 35 T 90 15" fill="none" stroke="rgba(255,255,255,0.25)" stroke-width="2" stroke-dasharray="4 2" />
      <circle cx="90" cy="15" r="4" fill="var(--rc-good)" />
    </svg>
  `;
}

class RoamcoreBasePage extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
    if (!this._root) {
      this.attachShadow({ mode: 'open' });
      this._root = document.createElement('div');
      this.shadowRoot.appendChild(this._root);
      const style = document.createElement('style');
      style.textContent = this._css();
      this.shadowRoot.appendChild(style);

      // delegated nav handler (bind once)
      this._rcNavBound = true;
      this._root.addEventListener('click', (ev) => {
        const path = ev.composedPath ? ev.composedPath() : [];
        const candidates = path.length ? path : [ev.target];
        for (const node of candidates) {
          if (node && node.getAttribute) {
            const nav = node.getAttribute('data-nav');
            if (nav) {
              this._navigate(nav);
              return;
            }
          }
        }
      });
    }
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _getState(id) {
    return this._hass?.states?.[id]?.state;
  }

  _num(id, fallback = null) {
    const n = Number(this._getState(id));
    return Number.isFinite(n) ? n : fallback;
  }

  _navigate(path) {
    try {
      if (!path) return;
      if (this._hass && typeof this._hass.navigate === 'function') {
        this._hass.navigate(path);
        return;
      }
      history.pushState(null, '', path);
      window.dispatchEvent(new Event('location-changed'));
    } catch (e) {
      console.warn('roamcore navigate failed', e);
    }
  }

  _basePath() {
    // The RoamCore dashboard can be mounted at different base paths depending on
    // whether it's a YAML dashboard or a storage dashboard.
    // Common patterns we've used:
    //   - /roam-core/...   (YAML dashboard id must include a hyphen)
    //   - /roamcore/...    (legacy)
    //   - /lovelace/roamcore/... (storage dashboard)
    try {
      const p = String(window.location?.pathname || '');
      if (p.startsWith('/roam-core/')) return '/roam-core';
      if (p === '/roam-core') return '/roam-core';
      if (p.startsWith('/roamcore/')) return '/roamcore';
      if (p === '/roamcore') return '/roamcore';
      if (p.startsWith('/lovelace/roamcore/')) return '/lovelace/roamcore';
      if (p === '/lovelace/roamcore') return '/lovelace/roamcore';
    } catch (e) {}
    // Safe default: if we can't tell, fall back to the YAML dashboard id.
    return '/roam-core';
  }

  _header(title) {
    return `
      <div class="rc-subheader">
        <button class="rc-back" data-nav="${this._basePath()}/overview">←</button>
        <div class="rc-subtitle">${title}</div>
        <div class="rc-subspacer"></div>
        <button class="rc-gear" title="Settings" data-nav="${this._basePath()}/settings">⚙</button>
      </div>
    `;
  }

  _traccarEmbedUrl() {
    // Prefer HA Supervisor ingress panel so it works from mobile app / remote access.
    // Direct LAN URLs (e.g. :8082) can be blocked as "public page -> local network".
    try {
      const panels = this._hass?.panels || {};
      for (const key of Object.keys(panels)) {
        const p = panels[key];
        const title = String(p?.title || p?.config?.title || '').toLowerCase();
        const urlPath = p?.url_path || '';
        if (title.includes('traccar') || urlPath.includes('traccar')) {
          // url_path is already a frontend route.
          return `/${urlPath}`;
        }
      }
    } catch (e) {
      // ignore
    }
    // Fallback: same-origin HA proxy (frontend route; works in iframes)
    return '/api/roamcore/traccar_public/';
  }

  _tile({ title, icon, content, className = '' }) {
    return `
      <div class="rc-dtile ${className}">
        <div class="rc-dtile-head">
          <div class="rc-dtile-title">${title}</div>
          <div class="rc-dtile-icon">${icon || ''}</div>
        </div>
        <div class="rc-dtile-body">${content}</div>
      </div>
    `;
  }

  _row(label, value, unit = '', color = '') {
    const v = (value === null || value === undefined || value === '' || value === 'unknown' || value === 'unavailable') ? '—' : value;
    const style = color ? ` style="color:${color}"` : '';
    const unitHtml = unit ? `<span class="rc-unit">${unit}</span>` : '';
    return `
      <div class="rc-row">
        <div class="rc-label">${label}</div>
        <div class="rc-val"${style}>${v}${unitHtml}</div>
      </div>
    `;
  }

  _badge(label, status) {
    const c = rcStatusToColor(status);
    return `
      <div class="rc-badge" style="border-color:${c}; background: color-mix(in srgb, ${c} 18%, transparent)">
        <span class="rc-bdot" style="background:${c}"></span>
        <span class="rc-btxt" style="color:${c}">${label}</span>
      </div>
    `;
  }

  _batterySvg(percent, fillColor) {
    const p = Math.max(0, Math.min(100, Number(percent) || 0));
    const fillW = (p / 100) * 44;
    return `
      <svg viewBox="0 0 56 28" class="rc-batt2">
        <rect x="1" y="4" width="48" height="20" rx="2" fill="none" stroke="rgba(255,255,255,0.35)" stroke-width="2"/>
        <rect x="49" y="9" width="5" height="10" rx="1" fill="rgba(255,255,255,0.25)"/>
        <rect x="3" y="6" width="${fillW}" height="16" rx="1" fill="${fillColor}"/>
      </svg>
    `;
  }

  _css() {
    return `
      :host {
        --rc-card: rgba(32,32,32,0.72);
        --rc-card2: rgba(32,32,32,0.55);
        --rc-border: rgba(255,255,255,0.08);
        --rc-muted: rgba(255,255,255,0.55);
        --rc-text: rgba(255,255,255,0.92);
        --rc-good: #43d17a;
        --rc-ok: #f4c542;
        --rc-bad: #ff5d5d;
        --rc-inactive: rgba(255,255,255,0.35);
        font-family: var(--primary-font-family, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif);
      }
      .rc-page { padding: 10px 12px 14px; color: var(--rc-text); }
      .rc-subheader { display:flex; align-items:center; gap: 10px; margin: 6px 0 12px; }
      .rc-back { width: 34px; height: 34px; border-radius: 10px; border: 1px solid var(--rc-border); background: rgba(255,255,255,0.04); color: var(--rc-text); font-size: 16px; cursor:pointer; }
      .rc-gear { width: 34px; height: 34px; border-radius: 10px; border: 1px solid var(--rc-border); background: rgba(255,255,255,0.04); color: var(--rc-muted); font-size: 16px; cursor:pointer; }
      .rc-gear:hover { filter: brightness(1.08); }
      .rc-subtitle { font-size: 18px; font-weight: 800; letter-spacing: 0.2px; }
      .rc-subspacer { flex:1; }

      .rc-grid { display:grid; grid-template-columns: 1fr 1fr; gap: 10px; }
      .span-2 { grid-column: span 2; }

      .rc-dtile {
        background: linear-gradient(180deg, var(--rc-card), var(--rc-card2));
        border: 1px solid var(--rc-border);
        border-radius: 14px;
        padding: 14px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.35);
        min-height: 140px;
      }
      .rc-dtile-head { display:flex; justify-content:space-between; align-items:center; margin-bottom: 10px; }
      .rc-dtile-title { font-size: 13px; color: var(--rc-muted); font-weight: 700; }
      .rc-dtile-icon { color: var(--rc-muted); font-size: 14px; }

      .rc-row { display:flex; justify-content:space-between; align-items:center; padding: 6px 0; }
      .rc-label { color: var(--rc-muted); font-size: 13px; }
      .rc-val { font-weight: 700; font-size: 13px; }
      .rc-unit { margin-left: 4px; color: var(--rc-muted); font-weight: 600; }

      .rc-value { display:flex; align-items: baseline; gap: 6px; }
      .rc-value-num { font-weight: 900; letter-spacing: 0.2px; }
      .rc-value-xl { font-size: 42px; }
      .rc-value-lg { font-size: 30px; }
      .rc-value-md { font-size: 22px; }
      .rc-value-unit { font-size: 13px; color: var(--rc-muted); font-weight: 700; }

      .rc-badge { display:inline-flex; align-items:center; gap:8px; border-radius: 10px; padding: 6px 10px; border: 1px solid; }
      .rc-bdot { width: 8px; height: 8px; border-radius: 999px; display:inline-block; }
      .rc-btxt { font-weight: 800; font-size: 13px; }

      .rc-batt2 { width: 56px; height: 28px; }
      .rc-van { width: 140px; height: 64px; }
      .rc-vanwrap { display:inline-block; transition: transform 0.3s ease; }
      .rc-map { width: 100%; height: 100%; }
      .rc-mapbox { width: 100%; height: 220px; border-radius: 14px; overflow:hidden; border: 1px solid rgba(255,255,255,0.06); background: rgba(255,255,255,0.03); }
      .rc-btn { display:inline-flex; align-items:center; justify-content:center; width:100%; padding: 12px 12px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.10); background: rgba(255,255,255,0.05); color: var(--rc-text); font-weight: 800; cursor:pointer; }
      .rc-btn:hover { filter: brightness(1.05); }

      @media (min-width: 1280px) {
        .rc-page { max-width: 1100px; margin: 0 auto; }
      }
    `;
  }

  // -----------------
  // Map helpers (Leaflet + breadcrumb trail)
  // -----------------
  async _ensureLeaflet() {
    try {
      if (window.L && window.L.map) return true;

      const cssId = 'rc-leaflet-css';
      const jsId = 'rc-leaflet-js';

      if (!document.getElementById(cssId)) {
        const link = document.createElement('link');
        link.id = cssId;
        link.rel = 'stylesheet';
        link.href = '/local/roamcore/vendor/leaflet/leaflet.css';
        document.head.appendChild(link);
      }

      if (!document.getElementById(jsId)) {
        await new Promise((resolve, reject) => {
          const s = document.createElement('script');
          s.id = jsId;
          s.src = '/local/roamcore/vendor/leaflet/leaflet.js';
          s.async = true;
          s.onload = resolve;
          s.onerror = reject;
          document.head.appendChild(s);
        });
      }

      return !!(window.L && window.L.map);
    } catch (e) {
      console.warn('leaflet load failed', e);
      return false;
    }
  }

  _pickTrackerEntity() {
    const configured = this._getState('input_text.rc_location_tracker_entity');
    if (configured && configured !== 'unknown' && configured !== 'unavailable' && String(configured).trim()) {
      return String(configured).trim();
    }
    try {
      const st = this._hass?.states || {};
      for (const id of Object.keys(st)) {
        if (!id.startsWith('device_tracker.')) continue;
        const a = st[id]?.attributes || {};
        if (a.latitude != null && a.longitude != null) return id;
      }
    } catch (e) {}
    return null;
  }

  async _loadTrail(trackerId, hours = 6) {
    if (!this._hass || !trackerId) return [];
    try {
      const start = new Date(Date.now() - hours * 3600_000).toISOString();
      const url = `history/period/${encodeURIComponent(start)}?filter_entity_id=${encodeURIComponent(trackerId)}`;
      const rows = await this._hass.callApi('GET', url);
      const list = Array.isArray(rows) && rows.length ? rows[0] : [];
      const pts = [];
      for (const s of list) {
        const a = (s && s.attributes) || {};
        const lat = Number(a.latitude);
        const lon = Number(a.longitude);
        if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
        pts.push([lat, lon]);
      }
      const out = [];
      for (const p of pts) {
        const prev = out[out.length - 1];
        if (prev && Math.abs(prev[0] - p[0]) < 1e-6 && Math.abs(prev[1] - p[1]) < 1e-6) continue;
        out.push(p);
      }
      return out;
    } catch (e) {
      console.warn('trail load failed', e);
      return [];
    }
  }

  async _mountLeafletMap(el, { lat, lon, trackerId } = {}) {
    try {
      if (!el) return;
      const ok = await this._ensureLeaflet();
      if (!ok) {
        el.innerHTML = '<div class="rc-label">Map failed to load (Leaflet missing).</div>';
        return;
      }
      if (el._rcMap) return;

      if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
        el.innerHTML = '<div class="rc-label">No GPS fix yet.</div>';
        return;
      }

      const L = window.L;
      const m = L.map(el, { zoomControl: false, attributionControl: false });
      el._rcMap = m;

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(m);

      const trail = await this._loadTrail(trackerId, 6);
      const pts = (trail && trail.length ? trail : [[lat, lon]]);

      if (pts.length >= 2) {
        const line = L.polyline(pts, { color: '#22c55e', weight: 4, opacity: 0.85 });
        line.addTo(m);
        m.fitBounds(line.getBounds(), { padding: [18, 18] });
      } else {
        m.setView([lat, lon], 14);
      }

      L.circleMarker([lat, lon], { radius: 8, color: '#0ea5e9', weight: 3, fillColor: '#0ea5e9', fillOpacity: 0.9 }).addTo(m);
      L.control.zoom({ position: 'bottomright' }).addTo(m);
    } catch (e) {
      console.warn('leaflet mount failed', e);
      try { el.innerHTML = '<div class="rc-label">Map failed to render.</div>'; } catch (e2) {}
    }
  }
}

class RoamcorePowerPage extends RoamcoreBasePage {
  _render() {
    if (!this._root || !this._hass) return;

    // Contract entities currently available (MVP)
    const soc = this._num('sensor.rc_power_battery_soc', null);
    const battV = this._num('sensor.rc_power_battery_voltage', null);
    const battA = this._num('sensor.rc_power_battery_current', null);
    const battT = this._num('sensor.rc_power_battery_temperature', null) ?? this._num('sensor.rc_power_battery_temperature_2', null);
    const battCap = this._num('sensor.rc_power_battery_capacity', null);
    const battCycles = this._num('sensor.rc_power_battery_cycle_count', null);
    const battHealth = this._num('sensor.rc_power_battery_health', null);

    const solarW = this._num('sensor.rc_power_solar_power', null);
    const solarToday = this._num('sensor.rc_power_solar_energy_today', null);
    const solarTotal = this._num('sensor.rc_power_solar_energy_total', null);
    const solarPV = this._num('sensor.rc_power_solar_panel_voltage', null);
    const solarPA = this._num('sensor.rc_power_solar_panel_current', null);
    const solarEff = this._num('sensor.rc_power_solar_efficiency', null);

    const loadW = this._num('sensor.rc_power_load_power', null);
    const loadFridge = this._num('sensor.rc_power_load_fridge', null);
    const loadLights = this._num('sensor.rc_power_load_lights', null);
    const loadHeater = this._num('sensor.rc_power_load_heater', null);
    const loadPump = this._num('sensor.rc_power_load_water_pump', null);
    const loadOther = this._num('sensor.rc_power_load_other', null);

    const inv = this._getState('sensor.rc_power_inverter_status');
    const invOutW = this._num('sensor.rc_power_inverter_output_power', null);
    const invOutV = this._num('sensor.rc_power_inverter_output_voltage', null);
    const invHz = this._num('sensor.rc_power_inverter_frequency', null);
    const invTemp = this._num('sensor.rc_power_inverter_temperature', null);

    const shore = this._getState('binary_sensor.rc_power_shore_connected');
    const shoreV = this._num('sensor.rc_power_shore_voltage', null);
    const shoreA = this._num('sensor.rc_power_shore_current', null);
    const shoreW = this._num('sensor.rc_power_shore_power', null);

    const altV = this._num('sensor.rc_power_alternator_voltage', null);
    const altA = this._num('sensor.rc_power_alternator_current', null);
    const altW = this._num('sensor.rc_power_alternator_power', null);

    const status = rcPowerStatusFromSoc(soc);
    const c = rcStatusToColor(status);

    const batteryTop = `
      <div style="display:flex; gap:14px; align-items:center; margin-bottom: 12px;">
        ${this._batterySvg(soc ?? 0, c)}
        <div class="rc-value">
          <div class="rc-value-num rc-value-xl" style="color:${c}">${soc == null ? '—' : Math.round(soc)}</div>
          <div class="rc-value-unit">%</div>
        </div>
        ${this._badge(status === 'good' ? 'Healthy' : status === 'ok' ? 'OK' : 'Low', status)}
      </div>
    `;

    const batteryRows = `
      ${this._row('Voltage', battV == null ? '—' : round1(battV), 'V')}
      ${this._row('Current', battA == null ? '—' : round1(battA), 'A')}
      ${this._row('Temperature', battT == null ? '—' : round1(battT), '°C')}
      ${this._row('Capacity', battCap == null ? '—' : round1(battCap), 'Ah')}
      ${this._row('Cycles', battCycles == null ? '—' : Math.round(battCycles))}
      ${this._row('Health', battHealth == null ? '—' : Math.round(battHealth), '%')}
    `;

    const solar = `
      <div class="rc-value" style="margin-bottom:10px;">
        <div class="rc-value-num rc-value-lg" style="color:${rcStatusToColor('good')}">${solarW == null ? '—' : Math.round(solarW)}</div>
        <div class="rc-value-unit">W</div>
      </div>
      ${this._row('Today', solarToday == null ? '—' : round1(solarToday), 'kWh')}
      ${this._row('Total', solarTotal == null ? '—' : round1(solarTotal), 'kWh')}
      ${this._row('Panel V', solarPV == null ? '—' : round1(solarPV), 'V')}
      ${this._row('Panel A', solarPA == null ? '—' : round1(solarPA), 'A')}
      ${this._row('Efficiency', solarEff == null ? '—' : Math.round(solarEff), '%')}
    `;

    const loads = `
      <div class="rc-value" style="margin-bottom:10px;">
        <div class="rc-value-num rc-value-lg">${loadW == null ? '—' : Math.round(loadW)}</div>
        <div class="rc-value-unit">W</div>
      </div>
      ${this._row('Fridge', loadFridge == null ? '—' : Math.round(loadFridge), 'W')}
      ${this._row('Lights', loadLights == null ? '—' : Math.round(loadLights), 'W')}
      ${this._row('Heater', loadHeater == null ? '—' : Math.round(loadHeater), 'W', (loadHeater == null || loadHeater == 0) ? rcStatusToColor('inactive') : '')}
      ${this._row('Water Pump', loadPump == null ? '—' : Math.round(loadPump), 'W')}
      ${this._row('Other', loadOther == null ? '—' : Math.round(loadOther), 'W')}
    `;

    const inverter = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 10px;">
        ${this._badge((inv && inv !== 'unknown' && inv !== 'unavailable') ? rcCap(inv) : '—', (inv && inv !== 'off') ? 'good' : 'inactive')}
        <div class="rc-label" style="text-transform:uppercase; font-weight:700;">eco</div>
      </div>
      ${this._row('Output', invOutW == null ? '—' : Math.round(invOutW), 'W')}
      ${this._row('Voltage', invOutV == null ? '—' : round1(invOutV), 'V')}
      ${this._row('Frequency', invHz == null ? '—' : round1(invHz), 'Hz')}
      ${this._row('Temperature', invTemp == null ? '—' : round1(invTemp), '°C')}
    `;

    const shoreTile = `
      <div style="margin-bottom: 10px;">
        ${this._badge(shore === 'on' ? 'Connected' : 'Disconnected', shore === 'on' ? 'good' : 'inactive')}
      </div>
      ${this._row('Voltage', shoreV == null ? '—' : round1(shoreV), shoreV == null ? '' : 'V')}
      ${this._row('Current', shoreA == null ? '—' : round1(shoreA), shoreA == null ? '' : 'A')}
      ${this._row('Power', shoreW == null ? '—' : Math.round(shoreW), shoreW == null ? '' : 'W')}
    `;

    const alternatorTile = `
      <div style="margin-bottom: 10px;">
        ${this._badge('Idle', 'inactive')}
      </div>
      ${this._row('Voltage', altV == null ? '—' : round1(altV), altV == null ? '' : 'V')}
      ${this._row('Current', altA == null ? '—' : round1(altA), altA == null ? '' : 'A')}
      ${this._row('Power', altW == null ? '—' : Math.round(altW), altW == null ? '' : 'W')}
    `;

    const summary = `
      <div class="rc-grid" style="grid-template-columns: 1fr 1fr; gap: 12px;">
        <div>
          <div class="rc-label" style="margin-bottom:4px;">Net Power</div>
          <div class="rc-value"><div class="rc-value-num rc-value-md" style="color:var(--rc-good)">+${(solarW!=null && loadW!=null) ? Math.round(solarW-loadW) : '—'}</div><div class="rc-value-unit">W</div></div>
        </div>
        <div>
          <div class="rc-label" style="margin-bottom:4px;">Time to Full</div>
          <div class="rc-value"><div class="rc-value-num rc-value-md">—</div></div>
        </div>
        <div>
          <div class="rc-label" style="margin-bottom:4px;">Today Generation</div>
          <div class="rc-value"><div class="rc-value-num rc-value-md">—</div><div class="rc-value-unit">kWh</div></div>
        </div>
        <div>
          <div class="rc-label" style="margin-bottom:4px;">Today Consumption</div>
          <div class="rc-value"><div class="rc-value-num rc-value-md">—</div><div class="rc-value-unit">kWh</div></div>
        </div>
      </div>
    `;

    this._root.innerHTML = `
      <div class="rc-page">
        ${this._header('Power')}
        <div class="rc-grid">
          ${this._tile({title:'Battery', icon:'', content: batteryTop + batteryRows, className:'span-2'})}
          ${this._tile({title:'Solar', icon:'☼', content: solar})}
          ${this._tile({title:'Loads', icon:'⚡', content: loads})}
          ${this._tile({title:'Inverter', icon:'⎓', content: inverter})}
          ${this._tile({title:'Shore Power', icon:'⎍', content: shoreTile})}
          ${this._tile({title:'Alternator', icon:'⎈', content: alternatorTile})}
          ${this._tile({title:'Power Summary', icon:'', content: summary, className:'span-2'})}
        </div>
      </div>
    `;

  }
}

class RoamcoreNetworkPage extends RoamcoreBasePage {
  _render() {
    if (!this._root || !this._hass) return;

    const netStatus = this._getState('sensor.rc_net_wan_status');
    const netSource = this._getState('sensor.rc_net_wan_source');
    const down = this._num('sensor.rc_net_download', null);
    const up = this._num('sensor.rc_net_upload', null);
    const ping = this._num('sensor.rc_net_ping', null);

    const jitter = this._num('sensor.rc_net_jitter', null);
    const ploss = this._num('sensor.rc_net_packet_loss', null);
    const uptime = this._getState('sensor.rc_net_uptime');
    const lastDisc = this._getState('sensor.rc_net_last_disconnect');

    const dataTodayDown = this._num('sensor.rc_net_data_today_down', null);
    const dataTodayUp = this._num('sensor.rc_net_data_today_up', null);
    const dataMonthDown = this._num('sensor.rc_net_data_month_down', null);
    const dataMonthUp = this._num('sensor.rc_net_data_month_up', null);
    const dataMonthLimit = this._num('sensor.rc_net_data_month_limit', null);

    const slSig = this._num('sensor.rc_net_starlink_signal_quality', null);
    const cellProv = this._getState('sensor.rc_net_cellular_provider');
    const cellTech = this._getState('sensor.rc_net_cellular_technology');
    const cellSig = this._num('sensor.rc_net_cellular_signal', null);

    const lanDevs = this._num('sensor.rc_net_lan_devices', null);
    const lanWifi = this._num('sensor.rc_net_lan_wifi_clients', null);
    const lanEth = this._num('sensor.rc_net_lan_ethernet_clients', null);
    const ssid = this._getState('sensor.rc_net_ssid');
    const chan = this._getState('sensor.rc_net_channel');
    const freq = this._getState('sensor.rc_net_frequency');

    const rCpu = this._num('sensor.rc_router_cpu', null);
    const rMem = this._num('sensor.rc_router_memory', null);
    const rTemp = this._num('sensor.rc_router_temperature', null);
    const rUptime = this._getState('sensor.rc_router_uptime');
    const rFw = this._getState('sensor.rc_router_firmware');

    const status = (netStatus && netStatus !== 'unknown' && netStatus !== 'unavailable') ? netStatus : 'inactive';
    const c = rcStatusToColor(status);

    const connection = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 12px;">
        <div style="display:flex; gap:10px; align-items:center;">
          ${this._badge('Connected', status)}
        </div>
        <div style="text-align:right;">
          <div style="font-weight:800; text-transform:capitalize;">${rcCap(netSource)}</div>
          <div class="rc-label">Active Source</div>
        </div>
      </div>
      <div class="rc-grid" style="grid-template-columns: 1fr 1fr; gap: 10px;">
        <div>${this._row('Uptime', (uptime && uptime !== 'unknown' && uptime !== 'unavailable') ? uptime : '—')}</div>
        <div>${this._row('Last Disconnect', (lastDisc && lastDisc !== 'unknown' && lastDisc !== 'unavailable') ? lastDisc : '—')}</div>
      </div>
    `;

    const perf = `
      <div class="rc-grid" style="grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">
        <div>
          <div class="rc-label">Download</div>
          <div class="rc-value"><div class="rc-value-num rc-value-md" style="color:${c}">${down == null ? '—' : Math.round(down)}</div><div class="rc-value-unit">Mbps</div></div>
        </div>
        <div>
          <div class="rc-label">Upload</div>
          <div class="rc-value"><div class="rc-value-num rc-value-md">${up == null ? '—' : Math.round(up)}</div><div class="rc-value-unit">Mbps</div></div>
        </div>
      </div>
      ${this._row('Ping', ping == null ? '—' : Math.round(ping), 'ms')}
      ${this._row('Jitter', jitter == null ? '—' : Math.round(jitter), 'ms')}
      ${this._row('Packet Loss', ploss == null ? '—' : round1(ploss), '%')}
    `;

    const usagePct = (dataMonthDown != null && dataMonthLimit != null && dataMonthLimit > 0)
      ? Math.min(100, Math.max(0, (dataMonthDown / dataMonthLimit) * 100))
      : null;
    const usageColor = usagePct == null ? 'rgba(255,255,255,0.18)' : (usagePct > 90 ? 'var(--rc-bad)' : usagePct > 75 ? 'var(--rc-ok)' : 'var(--rc-good)');
    const dataUsage = `
      <div class="rc-label" style="margin-bottom:8px;">Monthly Usage</div>
      <div style="height: 10px; border-radius: 999px; background: rgba(255,255,255,0.08); overflow:hidden; margin-bottom: 8px;">
        <div style="height: 100%; width: ${usagePct == null ? 0 : Math.round(usagePct)}%; background: ${usageColor};"></div>
      </div>
      ${this._row('Today Down', dataTodayDown == null ? '—' : round1(dataTodayDown), 'GB')}
      ${this._row('Today Up', dataTodayUp == null ? '—' : round1(dataTodayUp), 'GB')}
      ${this._row('Month Down', dataMonthDown == null ? '—' : round1(dataMonthDown), 'GB')}
      ${this._row('Month Up', dataMonthUp == null ? '—' : round1(dataMonthUp), 'GB')}
    `;

    const starlink = `
      <div style="margin-bottom: 10px;">${this._badge('Connected', 'good')}</div>
      ${this._row('Signal', slSig == null ? '—' : Math.round(slSig), '%')}
      ${this._row('Obstructed', 'No')}
      ${this._row('Download', down == null ? '—' : Math.round(down), 'Mbps')}
      ${this._row('Upload', up == null ? '—' : Math.round(up), 'Mbps')}
      ${this._row('Latency', ping == null ? '—' : Math.round(ping), 'ms')}
    `;

    const cellular = `
      <div style="display:flex; gap:10px; align-items:center; margin-bottom: 10px;">
        ${this._badge(`${(cellProv && cellProv !== 'unknown' && cellProv !== 'unavailable') ? cellProv : '—'} • ${(cellTech && cellTech !== 'unknown' && cellTech !== 'unavailable') ? cellTech : '—'}`, 'ok')}
      </div>
      ${this._row('Signal', cellSig == null ? '—' : Math.round(cellSig), 'dBm')}
      ${this._row('Download', '—', 'Mbps')}
      ${this._row('Upload', '—', 'Mbps')}
      ${this._row('Latency', '—', 'ms')}
    `;

    const localNet = `
      <div class="rc-value" style="margin-bottom:10px;"><div class="rc-value-num rc-value-lg">${lanDevs == null ? '—' : Math.round(lanDevs)}</div><div class="rc-value-unit">devices</div></div>
      ${this._row('WiFi Clients', lanWifi == null ? '—' : Math.round(lanWifi))}
      ${this._row('Ethernet', lanEth == null ? '—' : Math.round(lanEth))}
      ${this._row('SSID', (ssid && ssid !== 'unknown' && ssid !== 'unavailable') ? ssid : '—')}
      ${this._row('Channel', (chan && chan !== 'unknown' && chan !== 'unavailable') ? `${chan} (${(freq && freq !== 'unknown' && freq !== 'unavailable') ? freq : '—'})` : '—')}
    `;

    const router = `
      <div style="margin-bottom: 10px;">${this._badge('Healthy', 'good')}</div>
      ${this._row('CPU', rCpu == null ? '—' : Math.round(rCpu), '%')}
      ${this._row('Memory', rMem == null ? '—' : Math.round(rMem), '%')}
      ${this._row('Temperature', rTemp == null ? '—' : Math.round(rTemp), '°C')}
      ${this._row('Uptime', (rUptime && rUptime !== 'unknown' && rUptime !== 'unavailable') ? rUptime : '—')}
      ${this._row('Firmware', (rFw && rFw !== 'unknown' && rFw !== 'unavailable') ? rFw : '—')}
    `;

    this._root.innerHTML = `
      <div class="rc-page">
        ${this._header('Network')}
        <div class="rc-grid">
          ${this._tile({title:'Connection Status', icon:'⌁', content: connection, className:'span-2'})}
          ${this._tile({title:'Performance', icon:'⟲', content: perf})}
          ${this._tile({title:'Data Usage', icon:'⛁', content: dataUsage})}
          ${this._tile({title:'Starlink', icon:'🛰', content: starlink})}
          ${this._tile({title:'Cellular', icon:'⋮', content: cellular})}
          ${this._tile({title:'Local Network', icon:'⌂', content: localNet})}
          ${this._tile({title:'Router Health', icon:'⎇', content: router})}
        </div>
      </div>
    `;

  }
}

customElements.define('roamcore-power-page', RoamcorePowerPage);


class RoamcoreLevelPage extends RoamcoreBasePage {
  _callCalibrate() {
    try {
      const ent = this._hass?.states?.['button.rc_system_level_calibrate'];
      if (ent && this._hass?.callService) {
        this._hass.callService('button', 'press', { entity_id: 'button.rc_system_level_calibrate' });
        return;
      }
      const sc = this._hass?.states?.['script.rc_system_level_calibrate'];
      if (sc && this._hass?.callService) {
        this._hass.callService('script', 'turn_on', { entity_id: 'script.rc_system_level_calibrate' });
        return;
      }
      alert('No calibrate entity found (expected button.rc_system_level_calibrate or script.rc_system_level_calibrate).');
    } catch (e) {
      console.warn('calibrate failed', e);
    }
  }

  _render() {
    if (!this._root || !this._hass) return;
    const pitch = this._num('sensor.rc_system_level_pitch_deg', null) ?? this._num('sensor.rc_system_level_pitch', null);
    const roll = this._num('sensor.rc_system_level_roll_deg', null) ?? this._num('sensor.rc_system_level_roll', null);
    const st = rcLevelStatusFromPitchRoll(pitch, roll);
    const c = rcStatusToColor(st.status);

    const pitchRot = (pitch == null ? 0 : Number(pitch));
    const rollRot = (roll == null ? 0 : Number(roll));

    const pitchTile = `
      <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; gap: 10px; height: 160px;">
        <div class="rc-vanwrap" style="transform: rotate(${(-pitchRot).toFixed(1)}deg)">${rcVanSideSvg()}</div>
        <div class="rc-value"><div class="rc-value-num rc-value-xl" style="color:${c}">${pitch == null ? '—' : Math.abs(pitch).toFixed(1)}</div><div class="rc-value-unit">°</div></div>
        <div class="rc-label">Pitch</div>
      </div>
    `;

    const rollTile = `
      <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; gap: 10px; height: 160px;">
        <div class="rc-vanwrap" style="transform: rotate(${(-rollRot).toFixed(1)}deg)">${rcVanBackSvg()}</div>
        <div class="rc-value"><div class="rc-value-num rc-value-xl" style="color:${c}">${roll == null ? '—' : Math.abs(roll).toFixed(1)}</div><div class="rc-value-unit">°</div></div>
        <div class="rc-label">Roll</div>
      </div>
    `;

    const statusTile = `
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
          <div class="rc-label" style="margin-bottom:6px;">Status</div>
          <div style="font-size: 22px; font-weight: 900; color:${c}">${st.label}</div>
        </div>
        ${this._badge(st.label, st.status)}
      </div>
      <div style="height: 10px"></div>
      <button class="rc-btn" id="rc-calibrate">Calibrate</button>
      <div class="rc-label" style="margin-top:10px;">Tip: Calibrate on level ground before fine parking.</div>
    `;

    this._root.innerHTML = `
      <div class="rc-page">
        ${this._header('Level')}
        <div class="rc-grid">
          ${this._tile({title:'Pitch', icon:'', content: pitchTile})}
          ${this._tile({title:'Roll', icon:'', content: rollTile})}
          ${this._tile({title:'Calibration', icon:'⦿', content: statusTile, className:'span-2'})}
        </div>
      </div>
    `;

    const btn = this._root.querySelector('#rc-calibrate');
    if (btn) btn.addEventListener('click', () => this._callCalibrate());
  }
}

class RoamcoreMapPage extends RoamcoreBasePage {
  _render() {
    if (!this._root || !this._hass) return;

    const loc = this._getState('sensor.rc_map_location');
    const lat = this._num('sensor.rc_location_lat', null);
    const lon = this._num('sensor.rc_location_lon', null);
    const acc = this._num('sensor.rc_location_accuracy_m', null);
    const spd = this._num('sensor.rc_location_speed', null);
    const head = this._num('sensor.rc_location_heading_deg', null);
    const elev = this._num('sensor.rc_map_elevation_m', null) ?? this._num('sensor.rc_map_elevation', null);
    const distToday = this._num('sensor.rc_trip_distance_today_mi', null) ?? this._num('sensor.rc_trip_distance_today', null);
    const distTotal = this._num('sensor.rc_trip_distance_total_mi', null) ?? this._num('sensor.rc_trip_distance_total', null);
    const timeToday = this._getState('sensor.rc_trip_time_today');
    const timeTotal = this._getState('sensor.rc_trip_time_total');
    const segments = this._num('sensor.rc_trip_segments', null);
    const stops = this._num('sensor.rc_trip_stops', null);

    const mapTile = `
      <div style="border-radius: 12px; overflow:hidden; border: 1px solid rgba(255,255,255,0.06); background: rgba(255,255,255,0.03); padding: 10px;">
        <div id="rc-map-inner" style="height:360px;">
          <div class="rc-label">Loading map…</div>
        </div>
      </div>
      <div style="display:flex; gap:8px; align-items:center; margin-top: 10px;">
        <div style="color: var(--rc-good); font-weight:900">⌖</div>
        <div style="font-weight:800; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${(loc && loc!=='unknown' && loc!=='unavailable') ? loc : '—'}</div>
      </div>
      <div class="rc-label" style="margin-top: 6px;">RoamCore map (Leaflet) + breadcrumb trail (last 6h).</div>
    `;

    const stats = `
      ${this._row('Latitude', lat == null ? '—' : lat.toFixed(5))}
      ${this._row('Longitude', lon == null ? '—' : lon.toFixed(5))}
      ${this._row('Accuracy', acc == null ? '—' : Math.round(acc), 'm')}
      ${this._row('Speed', spd == null ? '—' : round1(spd))}
      ${this._row('Heading', head == null ? '—' : Math.round(head), '°')}
      <div style="height: 10px"></div>
      ${this._row('Elevation', elev == null ? '—' : round1(elev), 'm')}
      ${this._row('Distance (Today)', distToday == null ? '—' : round1(distToday), 'mi')}
      ${this._row('Distance (Total)', distTotal == null ? '—' : round1(distTotal), 'mi')}
      ${this._row('Time (Today)', (timeToday && timeToday!=='unknown' && timeToday!=='unavailable') ? timeToday : '—')}
      ${this._row('Time (Total)', (timeTotal && timeTotal!=='unknown' && timeTotal!=='unavailable') ? timeTotal : '—')}
    `;

    const history = `
      <div class="rc-label" style="margin-bottom:8px;">Full trip history</div>
      <div class="rc-label" style="margin-top:4px;">Trip saving/history (MVP): use Trip Wrapped below. (We can add richer trip history next.)</div>
      <div style="height: 8px"></div>
      ${this._row('Segments', segments == null ? '—' : Math.round(segments))}
      ${this._row('Stops', stops == null ? '—' : Math.round(stops))}
      <div style="height: 12px"></div>
      <div class="rc-label" style="margin-bottom:8px;">Trip Wrapped (MVP)</div>
      <div style="display:flex; gap:10px; flex-wrap:wrap;">
        <button class="rc-btn" id="rc-tripwrapped-generate">Generate</button>
        <a class="rc-btn" href="/local/roamcore/trip_wrapped/latest.html" target="_blank" rel="noreferrer">Open latest</a>
      </div>
      <div class="rc-label" style="margin-top:10px;">Configure Traccar creds + device id in HA helpers, then tap Generate.</div>
    `;

    this._root.innerHTML = `
      <div class="rc-page">
        ${this._header('Map')}
        <div class="rc-grid">
          ${this._tile({title:'Map', icon:'↗', content: mapTile, className:'span-2'})}
          ${this._tile({title:'Stats', icon:'⟰', content: stats})}
          ${this._tile({title:'History', icon:'⟲', content: history})}
        </div>
      </div>
    `;

    // Mount Leaflet map into placeholder.
    try {
      const inner = this._root.querySelector('#rc-map-inner');
      if (inner) {
        inner.innerHTML = `<div id="rc-leaflet-map" style="height:360px; border-radius:12px; overflow:hidden;"></div>`;
        const trackerId = this._pickTrackerEntity();
        const lat = this._num('sensor.rc_location_lat', null);
        const lon = this._num('sensor.rc_location_lon', null);
        const el = this._root.querySelector('#rc-leaflet-map');
        const map = this._mountLeafletMap(el, { lat, lon, trackerId });

        // Best-effort: overlay last 6h track from Traccar (if available).
        // This avoids embedding the full Traccar UI and gives a native RoamCore map.
        this._overlayTraccarTrack(map).catch(() => {});
      }
    } catch (e) {}

    const genBtn = this._root.querySelector('#rc-tripwrapped-generate');
    if (genBtn) {
      genBtn.addEventListener('click', async () => {
        try {
          genBtn.disabled = true;
          await this._hass.callService('script', 'turn_on', { entity_id: 'script.rc_trip_wrapped_run' });
        } catch (e) {
          console.warn('trip wrapped generate failed', e);
        } finally {
          genBtn.disabled = false;
        }
      });
    }
  }

  async _overlayTraccarTrack(map) {
    try {
      if (!map || !this._hass) return;

      // 1) Choose a device
      const devices = await this._hass.callApi('get', 'roamcore/traccar_api/devices').catch(() => []);
      if (!Array.isArray(devices) || devices.length === 0) return;
      const deviceId = devices[0]?.id;
      if (!deviceId) return;

      // 2) Query route for last 6h
      const to = new Date();
      const from = new Date(to.getTime() - 6 * 3600 * 1000);
      const q = new URLSearchParams({
        deviceId: String(deviceId),
        from: from.toISOString(),
        to: to.toISOString(),
      });
      const positions = await this._hass.callApi('get', `roamcore/traccar_api/reports/route?${q.toString()}`).catch(() => []);
      if (!Array.isArray(positions) || positions.length < 2) return;

      // 3) Draw polyline
      const pts = positions
        .map(p => ({ lat: Number(p.latitude), lon: Number(p.longitude) }))
        .filter(p => Number.isFinite(p.lat) && Number.isFinite(p.lon));
      if (pts.length < 2) return;
      const latlngs = pts.map(p => [p.lat, p.lon]);

      // Leaflet is loaded by _mountLeafletMap.
      const L = window.L;
      if (!L) return;
      const line = L.polyline(latlngs, { color: '#43d17a', weight: 4, opacity: 0.9 });
      line.addTo(map);
    } catch (e) {
      return;
    }
  }
}

class RoamcoreLocationPage extends RoamcoreBasePage {
  _render() {
    if (!this._root || !this._hass) return;

    const lat = this._num('sensor.rc_location_lat', null);
    const lon = this._num('sensor.rc_location_lon', null);
    const acc = this._num('sensor.rc_location_accuracy_m', null) ?? this._num('sensor.rc_location_accuracy', null);
    const src = this._getState('sensor.rc_location_source');

    this._root.innerHTML = `
      <div class="rc-page">
        ${this._header('Location')}
        <div class="rc-grid" style="grid-template-columns: 1fr;">
          ${this._tile({
            title: 'Current Fix',
            icon: '📍',
            content: `
              ${this._row('Latitude', lat == null ? '—' : lat)}
              ${this._row('Longitude', lon == null ? '—' : lon)}
              ${this._row('Accuracy', acc == null ? '—' : Math.round(acc), acc == null ? '' : 'm')}
              ${this._row('Source', (src && src !== 'unknown' && src !== 'unavailable') ? src : '—')}
              <button class="rc-btn" data-nav="${this._basePath()}/location" style="margin-top:10px;">Refresh</button>
            `
          })}

          ${this._tile({
            title: 'Map',
            icon: '🗺',
            content: `
              <div id="rc-location-map" style="height:360px; border-radius:12px; overflow:hidden;"></div>
              <div class="rc-label" style="margin-top:8px;">Breadcrumb trail: last 6 hours (from HA history).</div>
            `
          })}
        </div>
      </div>
    `;
    this._wireNav();

    // Mount Leaflet map.
    try {
      const el = this._root.querySelector('#rc-location-map');
      const trackerId = this._pickTrackerEntity();
      const latN = Number(lat);
      const lonN = Number(lon);
      this._mountLeafletMap(el, { lat: latN, lon: lonN, trackerId });
    } catch (e) {}
  }
}

class RoamcoreSettingsPage extends RoamcoreBasePage {
  _render() {
    if (!this._root || !this._hass) return;

    const tracker = this._getState('input_text.rc_location_tracker_entity');
    const weather = this._getState('input_text.rc_weather_entity_id');
    const tz = this._getState('input_text.rc_time_zone_override');

    this._root.innerHTML = `
      <div class="rc-page">
        ${this._header('Settings')}
        <div class="rc-grid" style="grid-template-columns: 1fr;">
          ${this._tile({
            title: 'RoamCore Helpers',
            icon: '⚙',
            content: `
              <div class="rc-label" style="margin-bottom:8px;">Edit these in HA → Settings → Devices & services → Helpers.</div>
              ${this._row('Location tracker entity', (tracker && tracker !== 'unknown' && tracker !== 'unavailable') ? tracker : '—')}
              ${this._row('Weather entity', (weather && weather !== 'unknown' && weather !== 'unavailable') ? weather : '—')}
              ${this._row('Time zone override', (tz && tz.trim()) ? tz : '—')}
            `
          })}
          ${this._tile({
            title: 'Advanced',
            icon: '🧰',
            content: `
              <div class="rc-label">Open HA configuration for deeper setup.</div>
              <button class="rc-btn" data-nav="/config" style="margin-top:10px;">Open HA Settings</button>
            `
          })}
        </div>
      </div>
    `;
  }
}

function round1(n){
  try{ return (Math.round(Number(n)*10)/10).toFixed(1).replace(/\.0$/,''); }catch(e){return n}
}
customElements.define('roamcore-network-page', RoamcoreNetworkPage);
customElements.define('roamcore-level-page', RoamcoreLevelPage);
customElements.define('roamcore-map-page', RoamcoreMapPage);
customElements.define('roamcore-location-page', RoamcoreLocationPage);
customElements.define('roamcore-settings-page', RoamcoreSettingsPage);
