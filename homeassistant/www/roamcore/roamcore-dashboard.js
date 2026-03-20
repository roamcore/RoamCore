// RoamCore Dashboard (v0) - custom Lovelace card
// Goal: match RoamCore TSX v0 design as closely as possible using a single custom card.
// Naming convention reference: RoamCore/docs/reference/rc-entity-naming.md
//
// This is intentionally self-contained (no external deps) for HAOS reliability.

class RoamcoreDashboardCard extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
    if (!this._root) {
      this.attachShadow({ mode: "open" });
      this._root = document.createElement("div");
      this.shadowRoot.appendChild(this._root);
      const style = document.createElement('style');
      style.textContent = this._css();
      this.shadowRoot.appendChild(style);
    }
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
    // Mount the embedded Leaflet overview map (idempotent).
    try { this._mountOverviewMap(); } catch (e) {}
  }

  getCardSize() {
    return 6;
  }

  _navigate(path) {
    try {
      if (!path) return;
      // Preferred: use Home Assistant navigation helper when available
      if (this._hass && typeof this._hass.navigate === 'function') {
        this._hass.navigate(path);
        return;
      }
      // Fallback: pushState + HA router event
      history.pushState(null, '', path);
      window.dispatchEvent(new Event('location-changed'));
    } catch (e) {
      console.warn('roamcore navigate failed', e);
    }
  }

  _goSettings() {
    this._navigate(`${this._basePath()}/settings`);
  }

  _basePath() {
    // Force canonical RoamCore dashboard path.
    // HA storage dashboards are typically accessible at /<url_path>/...
    // We standardize on /roamcore to avoid drift across devices.
    return '/roamcore';
  }

  _getState(entityId) {
    return this._hass?.states?.[entityId]?.state;
  }

  _traccarEmbedUrl() {
    // Prefer Supervisor ingress panel so it works on mobile/remote.
    try {
      const panels = this._hass?.panels || {};
      for (const key of Object.keys(panels)) {
        const p = panels[key];
        const title = String(p?.title || p?.config?.title || '').toLowerCase();
        const urlPath = p?.url_path || '';
        if (title.includes('traccar') || urlPath.includes('traccar')) {
          return `/${urlPath}`;
        }
      }
    } catch (e) {}
    // Fallback: same-origin HA proxy (frontend route; works in iframes)
    return '/api/roamcore/traccar_public/';
  }

  _num(entityId, fallback = null) {
    const s = this._getState(entityId);
    const n = Number(s);
    return Number.isFinite(n) ? n : fallback;
  }

  _statusToColor(status) {
    if (status === 'good') return 'var(--rc-good)';
    if (status === 'ok') return 'var(--rc-ok)';
    if (status === 'bad') return 'var(--rc-bad)';
    return 'var(--rc-muted)';
  }

  _powerStatusFromSoc(soc) {
    if (soc == null) return 'ok';
    if (soc >= 60) return 'good';
    if (soc >= 30) return 'ok';
    return 'bad';
  }

  _render() {
    if (!this._root || !this._hass) return;

    // Avoid iframe flashing: do a full DOM build only once, then update text/values.
    const alreadyBuilt = !!this._root.querySelector('.rc-wrap');

    const soc = this._num('sensor.rc_power_battery_soc', null);
    const solarW = this._num('sensor.rc_power_solar_power', null);
    const shore = this._getState('binary_sensor.rc_power_shore_connected');
    const invStatus = this._getState('sensor.rc_power_inverter_status');

    const netStatus = this._getState('sensor.rc_net_wan_status');
    const netSource = this._getState('sensor.rc_net_wan_source');
    const down = this._num('sensor.rc_net_download', null);
    const up = this._num('sensor.rc_net_upload', null);
    const ping = this._num('sensor.rc_net_ping', null);

    const pitch = this._num('sensor.rc_system_level_pitch_deg', null) ?? this._num('sensor.rc_system_level_pitch', null);
    const roll = this._num('sensor.rc_system_level_roll_deg', null) ?? this._num('sensor.rc_system_level_roll', null);

    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const dateStr = now.toLocaleDateString([], { weekday: 'short', day: 'numeric', month: 'short' });

    const pStatus = this._powerStatusFromSoc(soc);
    const pColor = this._statusToColor(pStatus);

    // Network label + color
    const netRaw = (netStatus && netStatus !== 'unknown' && netStatus !== 'unavailable') ? String(netStatus) : '';
    const netLabel = netRaw ? this._cap(netRaw) : '—';
    let netColor = 'var(--rc-muted)';
    if (netRaw === 'good') netColor = 'var(--rc-good)';
    else if (netRaw === 'ok') netColor = 'var(--rc-ok)';
    else if (netRaw === 'bad') netColor = 'var(--rc-bad)';

    const shoreTxt = shore === 'on' ? 'Connected' : (shore === 'off' ? 'Off' : '—');
    const invTxtRaw = (invStatus && invStatus !== "unknown" && invStatus !== "unavailable") ? String(invStatus) : "—";
    const invTxt = (invTxtRaw === "on" ? "On" : invTxtRaw === "off" ? "Off" : invTxtRaw);

    const pitchAbs = pitch == null ? '—' : Math.abs(pitch).toFixed(1);
    const rollAbs = roll == null ? '—' : Math.abs(roll).toFixed(1);

    if (!alreadyBuilt) {
      this._root.innerHTML = `
        <div class="rc-wrap">
          <div class="rc-header">
            <div class="rc-header-left">
              <div class="rc-time" data-bind="time"></div>
              <div class="rc-date" data-bind="date"></div>
            </div>
            <div class="rc-header-right">
              <button class="rc-gear" title="Settings">⚙</button>
            </div>
          </div>

          <div class="rc-grid">
            ${this._tilePower({ soc, pColor, solarW, invTxt, shoreTxt })}
            ${this._tileNetwork({ netLabel, netColor, netSource, down, up, ping })}
            ${this._tileLevel({ pitchAbs, rollAbs, status: this._levelStatus(pitch, roll) })}
            ${this._tileMap()}
          </div>
        </div>
      `;

      // bind navigation clicks (once)
      this._root.querySelectorAll('.rc-click').forEach((el) => {
        el.addEventListener('click', () => this._navigate(el.getAttribute('data-nav')));
      });

      const gear = this._root.querySelector('.rc-gear');
      if (gear) gear.addEventListener('click', (e) => { e.stopPropagation(); this._goSettings(); });
    }

    // Update header time/date every render.
    const t = this._root.querySelector('[data-bind="time"]');
    if (t) t.textContent = timeStr;
    const d = this._root.querySelector('[data-bind="date"]');
    if (d) d.textContent = dateStr;
  }

  _levelStatus(pitch, roll) {
    const v = Math.max(Math.abs(pitch ?? 0), Math.abs(roll ?? 0));
    if (!Number.isFinite(v)) return { label: '—', color: 'var(--rc-muted)' };
    if (v < 2) return { label: 'Level', color: 'var(--rc-good)' };
    if (v < 6) return { label: 'Slight Tilt', color: 'var(--rc-ok)' };
    return { label: 'Not Level', color: 'var(--rc-bad)' };
  }

  _tilePower({ soc, pColor, solarW, invTxt, shoreTxt }) {
    const socTxt = soc == null ? '—' : `${Math.round(soc)}%`;
    const chargingSource = (solarW != null && solarW > 50) ? 'Solar' : '';
    const timeRemaining = '—';

    return `
      <div class="rc-tile rc-click" data-nav="${this._basePath()}/power">
        <div class="rc-tile-head">
          <div class="rc-tile-title">Power</div>
          <div class="rc-tile-sub">${chargingSource ? `☼ ${chargingSource}` : ''}</div>
        </div>

        <div class="rc-power-main">
          <div class="rc-batt">${this._batterySvg(soc ?? 0, pColor)}</div>
          <div class="rc-power-soc" style="color:${pColor}">${socTxt}</div>
        </div>

        <div class="rc-power-time"><span class="rc-muted">Time to full:</span> <span class="rc-strong">${timeRemaining}</span></div>

        <div class="rc-pillrow">
          <div class="rc-pill"><span class="rc-muted">Inverter</span><span class="rc-strong">${invTxt}</span></div>
          <div class="rc-pill"><span class="rc-muted">Shore</span><span class="rc-strong">${shoreTxt}</span></div>
        </div>
      </div>
    `;
  }

  _tileNetwork({ netLabel, netColor, netSource, down, up, ping }) {
    const downTxt = down == null ? '—' : `${Math.round(down)}`;
    const upTxt = up == null ? '—' : `${Math.round(up)}`;
    const pingTxt = ping == null ? '—' : `${Math.round(ping)}`;
    const src = (netSource && netSource !== 'unknown' && netSource !== 'unavailable') ? netSource : '—';

    return `
      <div class="rc-tile rc-click" data-nav="${this._basePath()}/network">
        <div class="rc-tile-head"><div class="rc-tile-title">Network</div><div class="rc-tile-sub">⌁</div></div>

        <div class="rc-net-main">
          <div class="rc-bars">${this._bars(netColor)}</div>
          <div class="rc-net-status"><span class="rc-dot" style="background:${netColor}"></span><span class="rc-net-label" style="color:${netColor}">${netLabel}</span></div>
          <div class="rc-net-src">⌬ <span class="rc-muted">${this._cap(src)}</span></div>
        </div>

        <div class="rc-net-stats">
          <div class="rc-stat"><div class="rc-stat-val">${downTxt}</div><div class="rc-muted">Mbps ↓</div></div>
          <div class="rc-stat"><div class="rc-stat-val">${upTxt}</div><div class="rc-muted">Mbps ↑</div></div>
          <div class="rc-stat"><div class="rc-stat-val">${pingTxt}</div><div class="rc-muted">ms</div></div>
        </div>
      </div>
    `;
  }

  _tileLevel({ pitchAbs, rollAbs, status }) {
    return `
      <div class="rc-tile rc-click" data-nav="${this._basePath()}/level">
        <div class="rc-tile-head"><div class="rc-tile-title">Level</div><div class="rc-tile-sub" style="color:${status.color}">${status.label}</div></div>

        <div class="rc-level-main">
          <div class="rc-level-col">
            <div class="rc-van">${this._vanSideSvg()}</div>
            <div class="rc-deg">${pitchAbs}°</div>
            <div class="rc-muted">Pitch</div>
          </div>
          <div class="rc-divider"></div>
          <div class="rc-level-col">
            <div class="rc-van">${this._vanBackSvg()}</div>
            <div class="rc-deg">${rollAbs}°</div>
            <div class="rc-muted">Roll</div>
          </div>
        </div>
      </div>
    `;
  }

  _tileMap() {
    const locRaw = this._getState('sensor.rc_map_location');
    const loc = (locRaw && locRaw !== 'unknown' && locRaw !== 'unavailable') ? String(locRaw) : '—';

    const todayN = this._num('sensor.rc_trip_distance_today_mi', null);
    const totalN = this._num('sensor.rc_trip_distance_total_mi', null);
    const today = todayN == null ? '—' : `${Math.round(todayN)}`;
    const total = totalN == null ? '—' : `${Math.round(totalN)}`;

    return `
      <div class="rc-tile rc-click" data-nav="${this._basePath()}/map">
        <div class="rc-tile-head"><div class="rc-tile-title">Map</div><div class="rc-tile-sub">↗</div></div>

        <div class="rc-map-main">
          <div class="rc-map-box">
            <div class="rc-map-leaflet" id="rc-overview-leaflet"></div>
          </div>
          <div class="rc-map-loc"><span class="rc-pin" style="color:var(--rc-good)">⌖</span><span class="rc-strong rc-trunc">${loc}</span></div>
        </div>

        <div class="rc-map-stats">
          <div class="rc-stat"><div class="rc-stat-val">${today} mi</div><div class="rc-muted">Today</div></div>
          <div class="rc-stat"><div class="rc-stat-val">${total} mi</div><div class="rc-muted">Total</div></div>
        </div>
      </div>
    `;
  }

  _cap(s) {
    if (!s) return '—';
    return String(s).charAt(0).toUpperCase() + String(s).slice(1);
  }

  _bars(color) {
    return [1,2,3,4].map(i => {
      const h = i*7 + 6;
      const on = (color !== 'var(--rc-muted)') && (i <= 4);
      const bg = on ? color : 'rgba(255,255,255,0.12)';
      return `<div class="rc-bar" style="height:${h}px;background:${bg}"></div>`;
    }).join('');
  }

  _batterySvg(percent, fillColor) {
    const p = Math.max(0, Math.min(100, Number(percent)||0));
    const fillW = (p/100)*34;
    return `
      <svg viewBox="0 0 48 24" class="rc-batt-svg">
        <rect x="1" y="4" width="40" height="16" rx="2" fill="none" stroke="rgba(255,255,255,0.35)" stroke-width="2"/>
        <rect x="41" y="8" width="4" height="8" rx="1" fill="rgba(255,255,255,0.25)"/>
        <rect x="3" y="6" width="${fillW}" height="12" rx="1" fill="${fillColor}"/>
        <path d="M24 6 L20 12 L23 12 L21 18 L28 11 L24 11 L26 6 Z" fill="rgba(0,0,0,0.75)"/>
      </svg>
    `;
  }

  _vanSideSvg() {
    return `
      <svg viewBox="0 0 80 40" class="rc-van-svg">
        <g fill="none" stroke="rgba(255,255,255,0.35)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
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

  _vanBackSvg() {
    return `
      <svg viewBox="0 0 50 45" class="rc-van-svg">
        <g fill="none" stroke="rgba(255,255,255,0.35)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
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

  _mapSvg() {
    return `
      <svg viewBox="0 0 100 60" class="rc-map-svg" preserveAspectRatio="none">
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

  _tileUrl() {
    const v = this._getState('input_text.rc_map_tile_url');
    if (v && v !== 'unknown' && v !== 'unavailable' && String(v).trim()) return String(v).trim();
    return '/rc-tiles/{z}/{x}/{y}.png';
  }

  _mapStyleUrl() {
    const v = this._getState('input_text.rc_map_style_url');
    if (v && v !== 'unknown' && v !== 'unavailable' && String(v).trim()) return String(v).trim();
    // Default: offline/local protomaps basemap style.
    return '/local/roamcore/styles/rc-offline-protomaps-light.json';
  }

  _mapMode() {
    const styleUrl = this._mapStyleUrl();
    if (styleUrl) return { mode: 'maplibre', styleUrl };
    return { mode: 'leaflet', tileUrl: this._tileUrl() };
  }

  _offlineMaxZoom() {
    const v = this._getState('input_number.rc_map_offline_max_zoom');
    const n = Number(v);
    return Number.isFinite(n) ? n : 6;
  }

  async _ensureLeaflet() {
    try {
      if (window.L && window.L.map) return true;
      const cssId = 'rc-leaflet-css';
      const jsId = 'rc-leaflet-js';

      if (!document.getElementById(cssId)) {
        const link = document.createElement('link');
        link.id = cssId;
        link.rel = 'stylesheet';
        link.href = '/local/roamcore/vendor/leaflet/leaflet.css?v=' + Date.now();
        document.head.appendChild(link);
      }

      if (!document.getElementById(jsId)) {
        const s = document.createElement('script');
        s.id = jsId;
        s.src = '/local/roamcore/vendor/leaflet/leaflet.js';
        s.async = true;
        document.head.appendChild(s);
      }

      const start = Date.now();
      while (Date.now() - start < 4000) {
        if (window.L && window.L.map) return true;
        await new Promise(r => setTimeout(r, 50));
      }
      return !!(window.L && window.L.map);
    } catch (e) {
      return false;
    }
  }

  async _ensureMapLibre() {
    try {
      if (window.maplibregl && window.maplibregl.Map) return true;
      const cssId = 'rc-maplibre-css';
      const jsId = 'rc-maplibre-js';
      const pmtilesId = 'rc-pmtiles-js';
      // IMPORTANT: this card uses shadow DOM; ensure CSS is available inside shadow root.
      if (!this.shadowRoot?.getElementById?.(cssId)) {
        const link = document.createElement('link');
        link.id = cssId;
        link.rel = 'stylesheet';
        link.href = '/local/roamcore/vendor/maplibre-gl/maplibre-gl.css?v=' + Date.now();
        (this.shadowRoot || document.head).appendChild(link);
        try { await new Promise(r => setTimeout(r, 100)); } catch (e) {}
      }
      if (!document.getElementById(jsId)) {
        const s = document.createElement('script');
        s.id = jsId;
        s.src = '/local/roamcore/vendor/maplibre-gl/maplibre-gl.js';
        s.async = true;
        document.head.appendChild(s);
      }
      if (!document.getElementById(pmtilesId)) {
        const s = document.createElement('script');
        s.id = pmtilesId;
        s.src = '/local/roamcore/vendor/pmtiles/pmtiles.js';
        s.async = true;
        document.head.appendChild(s);
      }
      const start = Date.now();
      while (Date.now() - start < 4000) {
        if (window.maplibregl && window.maplibregl.Map && window.pmtiles) return true;
        await new Promise(r => setTimeout(r, 50));
      }
      return !!(window.maplibregl && window.maplibregl.Map && window.pmtiles);
    } catch (e) {
      return false;
    }
  }

  _ensurePmtilesProtocol() {
    try {
      if (!window.maplibregl || !window.pmtiles) return false;
      if (window.__rcPmtilesProtocol) return true;
      const protocol = new window.pmtiles.Protocol();
      window.maplibregl.addProtocol('pmtiles', protocol.tile);
      window.__rcPmtilesProtocol = protocol;
      return true;
    } catch (e) {
      console.warn('pmtiles protocol init failed', e);
      return false;
    }
  }

  async _loadJson(url) {
    const res = await fetch(url, { cache: 'no-cache' });
    if (!res.ok) throw new Error(`fetch failed ${res.status} for ${url}`);
    return await res.json();
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

  async _getTraccarLastFix() {
    try {
      if (!this._hass) return null;
      // Pick first device and follow its positionId.
      const devs = await this._hass.callApi('GET', 'roamcore/traccar_api/devices').catch(() => []);
      if (!Array.isArray(devs) || devs.length === 0) return null;
      const d = devs[0] || {};
      const posId = d.positionId;
      if (!posId) return null;

      const positions = await this._hass.callApi('GET', `roamcore/traccar_api/positions?id=${encodeURIComponent(posId)}`).catch(() => []);
      const p = Array.isArray(positions) && positions.length ? positions[0] : null;
      if (!p) return null;
      const lat = Number(p.latitude);
      const lon = Number(p.longitude);
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;
      return { lat, lon, fixTime: p.fixTime || null };
    } catch (e) {
      return null;
    }
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
      return [];
    }
  }

  async _mountOverviewMap() {
    try {
      const el = this.shadowRoot?.querySelector('#rc-overview-leaflet');
      if (!el) return;

      // If nothing is mounted yet, show a lightweight placeholder so it isn't an empty box.
      if (!el._rcMap && !el._rcMapLibre && !el._rcMapPlaceholder) {
        try {
          el._rcMapPlaceholder = true;
          el.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:rgba(255,255,255,0.45);font-size:12px;">Loading map…</div>';
        } catch (e) {}
      }

      const mode = this._mapMode();
      if (mode.mode === 'maplibre') {
        if (el._rcMapLibre) return;
        // If Leaflet map was mounted earlier (before style URL was set), remove it and switch.
        if (el._rcMap) {
          try { el._rcMap.remove?.(); } catch (e) {}
          try { delete el._rcMap; } catch (e) { el._rcMap = null; }
        }
        const ok = await this._ensureMapLibre();
        if (!ok) return;
      } else {
        if (el._rcMap) return;
        // If MapLibre map was mounted earlier, remove it and switch.
        if (el._rcMapLibre) {
          try { el._rcMapLibre.remove?.(); } catch (e) {}
          try { delete el._rcMapLibre; } catch (e) { el._rcMapLibre = null; }
        }
        const ok = await this._ensureLeaflet();
        if (!ok) return;
      }

      const trackerId = this._pickTrackerEntity();
      let lat = this._num('sensor.rc_location_lat', null);
      let lon = this._num('sensor.rc_location_lon', null);
      try {
        const a = trackerId ? (this._hass?.states?.[trackerId]?.attributes || {}) : {};
        if (!Number.isFinite(lat)) lat = Number(a.latitude);
        if (!Number.isFinite(lon)) lon = Number(a.longitude);
      } catch (e) {}

      // If we still don't have a fix, fall back to Traccar last known position.
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
        try {
          const fix = await this._getTraccarLastFix();
          if (fix && Number.isFinite(fix.lat) && Number.isFinite(fix.lon)) {
            lat = fix.lat;
            lon = fix.lon;
          }
        } catch (e) {}
      }

      // As a last resort, pick a reasonable UK-ish default so the preview renders.
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
        lat = 54.5;
        lon = -3.0;
      }

      if (mode.mode === 'maplibre') {
        // Ensure PMTiles protocol is registered.
        this._ensurePmtilesProtocol();

        // MapLibre overview (simple marker).
        el.innerHTML = '';
        const container = document.createElement('div');
        container.style.width = '100%';
        container.style.height = '100%';
        el.appendChild(container);

        let style = mode.styleUrl;
        try {
          if (typeof style === 'string' && style.startsWith('/local/roamcore/styles/') && style.endsWith('.json')) {
            const obj = await this._loadJson(style);
            const origin = window.location.origin;
            const replaceOrigin = (v) => (typeof v === 'string' ? v.replaceAll('__ORIGIN__', origin) : v);
            if (obj && obj.sources) {
              for (const k of Object.keys(obj.sources)) {
                if (obj.sources[k] && obj.sources[k].url) obj.sources[k].url = replaceOrigin(obj.sources[k].url);
                if (obj.sources[k] && obj.sources[k].tiles) obj.sources[k].tiles = (obj.sources[k].tiles || []).map(replaceOrigin);
              }
            }
            if (obj && obj.sprite) obj.sprite = replaceOrigin(obj.sprite);
            if (obj && obj.glyphs) obj.glyphs = replaceOrigin(obj.glyphs);
            style = obj;
          }
        } catch (e) {
          console.warn('failed to load/patch style json (overview)', e);
        }

        const m = new maplibregl.Map({
          container,
          style,
          center: [Number(lon), Number(lat)],
          zoom: 6,
          interactive: false,
          attributionControl: false,
        });
        el._rcMapLibre = m;
        try {
          m.on('error', (ev) => {
            try {
              console.warn('roamcore overview maplibre error', ev?.error || ev);
            } catch (e) {}
          });
          m.on('load', () => { try { m.resize(); } catch (e) {} });
        } catch (e) {}
        try {
          new maplibregl.Marker({ color: '#0ea5e9' })
            .setLngLat([Number(lon), Number(lat)])
            .addTo(m);
        } catch (e) {}
        try {
          setTimeout(() => { try { m.resize(); } catch (e) {} }, 50);
          setTimeout(() => { try { m.resize(); } catch (e) {} }, 500);
        } catch (e) {}
      } else {
        const L = window.L;
        const m = L.map(el, {
          zoomControl: false,
          attributionControl: false,
          dragging: false,
          scrollWheelZoom: false,
          doubleClickZoom: false,
          boxZoom: false,
          keyboard: false,
          tap: false,
        });
        el._rcMap = m;

        const offlineMaxZ = this._offlineMaxZoom();
        L.tileLayer(this._tileUrl(), {
          maxZoom: offlineMaxZ,
          crossOrigin: true,
          updateWhenIdle: true,
          keepBuffer: 2,
        }).addTo(m);

        const trail = await this._loadTrail(trackerId, 6);
        const pts = (trail && trail.length ? trail : [[lat, lon]]);
        if (pts.length >= 2) {
          const line = L.polyline(pts, { color: '#22c55e', weight: 3, opacity: 0.85 });
          line.addTo(m);
          m.fitBounds(line.getBounds(), { padding: [10, 10] });
        } else {
          m.setView([lat, lon], Math.min(offlineMaxZ, 7));
        }
        L.circleMarker([lat, lon], { radius: 6, color: '#0ea5e9', weight: 2, fillColor: '#0ea5e9', fillOpacity: 0.9 }).addTo(m);

        try { setTimeout(() => { try { m.invalidateSize(true); } catch (e) {} }, 50); } catch (e) {}
      }
    } catch (e) {
      // best-effort
    }
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
        font-family: var(--primary-font-family, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif);
      }

      .rc-wrap { padding: 10px; color: var(--rc-text); }

      .rc-header { display:flex; justify-content:space-between; align-items:center; margin: 4px 2px 10px; }
      .rc-header-left { display:flex; gap:10px; align-items:baseline; }
      .rc-time { font-size:28px; font-weight:800; letter-spacing:0.5px; }
      .rc-date { font-size:13px; color:var(--rc-muted); font-weight:600; }
      .rc-header-right { display:flex; gap:10px; align-items:center; }
      .rc-gear { width: 34px; height: 34px; border-radius: 10px; border: 1px solid var(--rc-border); background: rgba(255,255,255,0.04); color: var(--rc-muted); font-size: 16px; cursor:pointer; }
      .rc-gear:hover { filter: brightness(1.08); }

      .rc-grid { display:grid; grid-template-columns: 1fr 1fr; gap: 10px; }

      .rc-click { cursor: pointer; }
      .rc-click:hover { filter: brightness(1.05); }

      .rc-tile {
        background: linear-gradient(180deg, var(--rc-card), var(--rc-card2));
        border: 1px solid var(--rc-border);
        border-radius: 14px;
        padding: 14px;
        /* Slightly taller overall so the overview doesn't feel squashed */
        min-height: 190px;
        /* Prevent grid items from expanding the column due to min-content sizing */
        min-width: 0;
        box-shadow: 0 6px 18px rgba(0,0,0,0.35);
      }

      .rc-tile-head { display:flex; justify-content:space-between; align-items:center; margin-bottom: 10px; }
      .rc-tile-title { font-size:13px; color:var(--rc-muted); font-weight:700; }
      .rc-tile-sub { font-size:12px; color:var(--rc-muted); font-weight:600; }

      .rc-power-main { display:flex; gap:12px; align-items:center; }
      .rc-batt-svg { width:64px; height:32px; }
      .rc-power-soc { font-size:44px; font-weight:900; letter-spacing:0.5px; }
      .rc-muted { color: var(--rc-muted); }
      .rc-strong { color: var(--rc-text); font-weight:700; }
      .rc-power-time { margin-top: 10px; font-size: 13px; }

      .rc-pillrow { display:grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 16px; }
      .rc-pill {padding: 10px 12px; font-size: 12px; min-width: 0; gap: 10px; }

      .rc-net-main { display:flex; flex-direction:column; align-items:center; justify-content:center; gap:6px; min-height:92px; }
      .rc-bars { display:flex; gap:4px; align-items:flex-end; margin-top: 4px; }
      .rc-bar { width:8px; border-radius:3px; }
      .rc-dot { width:8px; height:8px; border-radius:999px; display:inline-block; }
      .rc-net-status { display:flex; gap:8px; align-items:center; }
      .rc-net-label { font-size:18px; font-weight:800; }
      .rc-net-src { font-size:13px; }
      .rc-net-stats { display:grid; grid-template-columns: repeat(3, 1fr); gap:6px; margin-top: 8px; }
      .rc-stat { text-align:center; }
      .rc-stat-val { font-weight: 800; color: var(--rc-text); }

      .rc-level-main { display:flex; gap:14px; align-items:center; justify-content:center; height: 120px; }
      .rc-level-col { flex:1; display:flex; flex-direction:column; align-items:center; gap:4px; }
      .rc-divider { width:1px; height:80px; background: rgba(255,255,255,0.10); }
      .rc-van-svg { width:110px; height:52px; }
      .rc-deg { font-size:20px; font-weight:900; }

      /* Make the map preview dominate the tile (~70-80% of tile body). */
      .rc-map-main { display:flex; flex-direction:column; align-items:stretch; justify-content:flex-start; gap:10px; height: 150px; }
      .rc-map-box { width: 100%; height: 125px; border-radius: 12px; overflow:hidden; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); min-width: 0; }
      .rc-map-iframe { width: 100%; height: 100%; border: 0; pointer-events: none; }
      .rc-map-leaflet { width: 100%; height: 100%; }
      /* MapLibre sometimes sets an explicit canvas width that can force grid columns to grow. */
      .rc-map-box canvas { max-width: 100% !important; }
      .rc-map-box .maplibregl-canvas { max-width: 100% !important; }
      .rc-map-svg { width:100%; height:100%; }
      .rc-map-loc { display:flex; gap:6px; align-items:center; font-size:13px; max-width:100%; }
      .rc-trunc { max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
      .rc-map-stats { display:grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 6px; }

      @media (min-width: 1280px) {
        .rc-grid { grid-template-columns: repeat(4, 1fr); }
        .rc-tile { min-height: 210px; }
      }

      /* Mobile portrait: stack tiles and give them breathing room */
      @media (max-width: 700px) {
        .rc-wrap { padding: 8px; }
        .rc-grid { grid-template-columns: 1fr; }
        .rc-tile { min-height: 220px; }
        .rc-level-main { height: 140px; }
        .rc-map-main { height: 190px; }
        .rc-map-box { height: 160px; }
      }
    `;
  }
}

customElements.define('roamcore-dashboard-card', RoamcoreDashboardCard);
