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

  _tileUrl() {
    // Prefer a configurable tile URL so we can support offline/local tiles.
    // Set via HA Helper: input_text.rc_map_tile_url
    // Example local/offline tile server:
    //   http://homeassistant.local:8123/local/tiles/{z}/{x}/{y}.png
    const v = this._getState('input_text.rc_map_tile_url');
    if (v && v !== 'unknown' && v !== 'unavailable' && String(v).trim()) {
      return String(v).trim();
    }
    // Default: RoamCore local offline tile endpoint.
    return '/rc-tiles/{z}/{x}/{y}.png';
  }

  _mapStyleUrl() {
    // Optional MapLibre style URL (vector). If set, we use MapLibre GL instead of Leaflet raster.
    // Set via HA Helper: input_text.rc_map_style_url
    // Example (LocationIQ streets): https://tiles.locationiq.com/v3/streets/vector.json?key=YOUR_KEY
    const v = this._getState('input_text.rc_map_style_url');
    if (v && v !== 'unknown' && v !== 'unavailable' && String(v).trim()) {
      return String(v).trim();
    }
    // Default: offline/local protomaps basemap (z0–8) served by Home Assistant.
    // Style JSON is patched at runtime to replace __ORIGIN__ with window.location.origin.
    return '/local/roamcore/styles/rc-offline-protomaps-light.json';
  }

  _mapMode() {
    // Prefer MapLibre if a style URL is provided; otherwise fall back to Leaflet raster tiles.
    const styleUrl = this._mapStyleUrl();
    if (styleUrl) return { mode: 'maplibre', styleUrl };
    return { mode: 'leaflet', tileUrl: this._tileUrl() };
  }

  _onlineTileUrl() {
    // Optional online tile URL for detailed view when internet is available.
    // Set via HA Helper: input_text.rc_map_tile_url_online
    // Default OFF (empty) to keep the map fully offline unless explicitly enabled.
    const v = this._getState('input_text.rc_map_tile_url_online');
    if (v && v !== 'unknown' && v !== 'unavailable' && String(v).trim()) {
      return String(v).trim();
    }
    return '';
  }

  _offlineMaxZoom() {
    // Max zoom level with offline tile coverage. Above this, online tiles are used.
    // Adjust based on how much you've preloaded.
    const v = this._getState('input_number.rc_map_offline_max_zoom');
    const n = Number(v);
    return Number.isFinite(n) ? n : 6;
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

      /* Modal (Trip Wrapped options) */
      .rc-modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.55); display:flex; align-items:center; justify-content:center; padding: 14px; z-index: 9999; }
      .rc-modal { width: min(720px, calc(100vw - 28px)); max-height: min(80vh, 760px); overflow:auto; background: linear-gradient(180deg, rgba(26,26,26,0.96), rgba(18,18,18,0.96)); border: 1px solid rgba(255,255,255,0.10); border-radius: 16px; padding: 14px; box-shadow: 0 20px 60px rgba(0,0,0,0.55); }
      .rc-modal-head { display:flex; align-items:center; justify-content:space-between; gap: 10px; }
      .rc-input { width: 100%; padding: 10px 10px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.10); background: rgba(255,255,255,0.04); color: var(--rc-text); font-weight: 700; box-sizing: border-box; }
      .rc-input:focus { outline: none; border-color: rgba(67,209,122,0.55); }
      .rc-modal a { color: rgba(255,255,255,0.92); }

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

      // IMPORTANT: Leaflet CSS must be available inside this component's shadow root
      // (global document styles don't pierce shadow DOM).
      if (!this.shadowRoot?.getElementById?.(cssId)) {
        const link = document.createElement('link');
        link.id = cssId;
        link.rel = 'stylesheet';
        link.href = '/local/roamcore/vendor/leaflet/leaflet.css?v=' + Date.now();
        const p = new Promise((resolve) => {
          link.onload = () => resolve(true);
          link.onerror = () => resolve(false);
        });
        (this.shadowRoot || document.head).appendChild(link);
        // Best-effort: wait a bit so tile positioning CSS is present before map init.
        try { await Promise.race([p, new Promise(r => setTimeout(r, 800))]); } catch (e) {}
      } else {
        // If CSS tag exists but stylesheet hasn't applied yet, give it a moment.
        try { await new Promise(r => setTimeout(r, 100)); } catch (e) {}
      }

      if (!document.getElementById(jsId)) {
        const src = '/local/roamcore/vendor/leaflet/leaflet.js';
        let lastErr = null;
        for (let i = 0; i < 4; i++) {
          try {
            await new Promise((resolve, reject) => {
              const s = document.createElement('script');
              s.id = jsId;
              s.src = src + (i ? `?v=${Date.now()}` : '');
              s.async = true;
              s.onload = resolve;
              s.onerror = reject;
              document.head.appendChild(s);
            });
            break;
          } catch (e) {
            lastErr = e;
            try { await new Promise(r => setTimeout(r, 400)); } catch (e2) {}
          }
        }
        if (lastErr && !(window.L && window.L.map)) {
          throw lastErr;
        }
      }

      return !!(window.L && window.L.map);
    } catch (e) {
      console.warn('leaflet load failed', e);
      return false;
    }
  }

  async _ensureMapLibre() {
    try {
      if (window.maplibregl && window.maplibregl.Map) return true;

      const jsId = 'rc-maplibre-js';
      const cssId = 'rc-maplibre-css';
      const pmtilesId = 'rc-pmtiles-js';
      const jsUrl = '/local/roamcore/vendor/maplibre-gl/maplibre-gl.js';
      const cssUrl = '/local/roamcore/vendor/maplibre-gl/maplibre-gl.css';
      const pmtilesUrl = '/local/roamcore/vendor/pmtiles/pmtiles.js';

      // IMPORTANT: MapLibre CSS must be available inside this component's shadow root.
      if (!this.shadowRoot?.getElementById?.(cssId)) {
        // Use <link> so the browser handles relative URLs inside CSS correctly.
        const link = document.createElement('link');
        link.id = cssId;
        link.rel = 'stylesheet';
        link.href = cssUrl + '?v=' + Date.now();
        const p = new Promise((resolve) => {
          link.onload = () => resolve(true);
          link.onerror = () => resolve(false);
        });
        (this.shadowRoot || document.head).appendChild(link);
        try { await Promise.race([p, new Promise(r => setTimeout(r, 800))]); } catch (e) {}
      } else {
        try { await new Promise(r => setTimeout(r, 100)); } catch (e) {}
      }

      if (!document.getElementById(jsId)) {
        await new Promise((resolve, reject) => {
          const s = document.createElement('script');
          s.id = jsId;
          s.src = jsUrl;
          s.async = true;
          s.onload = resolve;
          s.onerror = reject;
          document.head.appendChild(s);
        });
      }

      if (!document.getElementById(pmtilesId)) {
        await new Promise((resolve, reject) => {
          const s = document.createElement('script');
          s.id = pmtilesId;
          s.src = pmtilesUrl;
          s.async = true;
          s.onload = resolve;
          s.onerror = reject;
          document.head.appendChild(s);
        });
      }

      return !!(window.maplibregl && window.maplibregl.Map && window.pmtiles);
    } catch (e) {
      console.warn('maplibre load failed', e);
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

  _loadSavedMapView() {
    try {
      const raw = localStorage.getItem('rc_map_view_v1');
      if (!raw) return null;
      const o = JSON.parse(raw);
      const lat = Number(o?.lat);
      const lon = Number(o?.lon);
      const zoom = Number(o?.zoom);
      if (!Number.isFinite(lat) || !Number.isFinite(lon) || !Number.isFinite(zoom)) return null;
      return { lat, lon, zoom };
    } catch (e) {
      return null;
    }
  }

  _loadSavedMapViewMapLibre() {
    try {
      const raw = localStorage.getItem('rc_map_view_maplibre_v1');
      if (!raw) return null;
      const o = JSON.parse(raw);
      const lat = Number(o?.lat);
      const lon = Number(o?.lon);
      const zoom = Number(o?.zoom);
      if (!Number.isFinite(lat) || !Number.isFinite(lon) || !Number.isFinite(zoom)) return null;
      return { lat, lon, zoom };
    } catch (e) {
      return null;
    }
  }

  _saveMapViewMapLibre(map) {
    try {
      if (!map) return;
      const c = map.getCenter?.();
      const z = map.getZoom?.();
      if (!c || !Number.isFinite(c.lat) || !Number.isFinite(c.lng) || !Number.isFinite(z)) return;
      localStorage.setItem('rc_map_view_maplibre_v1', JSON.stringify({ lat: c.lat, lon: c.lng, zoom: z }));
    } catch (e) {}
  }

  _saveMapView(map) {
    try {
      if (!map) return;
      const c = map.getCenter?.();
      const z = map.getZoom?.();
      if (!c || !Number.isFinite(c.lat) || !Number.isFinite(c.lng) || !Number.isFinite(z)) return;
      localStorage.setItem('rc_map_view_v1', JSON.stringify({ lat: c.lat, lon: c.lng, zoom: z }));
    } catch (e) {}
  }

  async _getTraccarRoutePositions({ deviceId = null, hours = 6 } = {}) {
    try {
      if (!this._hass) return [];

      let did = deviceId;
      if (!did) {
        // Prefer dedicated route device (allows demo device without affecting other features).
        const routeDid = Number(this._getState('input_number.rc_map_route_device_id'));
        if (Number.isFinite(routeDid) && routeDid > 0) did = routeDid;
      }
      if (!did) {
        const configured = Number(this._getState('input_number.rc_traccar_device_id'));
        if (Number.isFinite(configured) && configured > 0) did = configured;
      }
      if (!did) {
        const devices = await this._hass.callApi('get', 'roamcore/traccar_api/devices').catch(() => []);
        did = Array.isArray(devices) && devices[0]?.id ? devices[0].id : null;
      }
      if (!did) return [];

      const to = new Date();
      const from = new Date(to.getTime() - (hours * 3600_000));
      const q = new URLSearchParams({
        deviceId: String(did),
        from: from.toISOString(),
        to: to.toISOString(),
      });
      const positions = await this._hass
        .callApi('get', `roamcore/traccar_api/reports/route?${q.toString()}`)
        .catch(() => []);
      if (!Array.isArray(positions)) return [];
      return positions;
    } catch (e) {
      return [];
    }
  }

  _positionsToGeojsonLine(positions) {
    try {
      // Convert to [lon,lat] and aggressively de-noise/decimate so rendering stays stable on mobile.
      // Traccar can return a lot of points (30s cadence), and MapLibre line triangulation can glitch.
      const sorted = [...(positions || [])].sort((a, b) => {
        const ta = new Date(a?.fixTime || a?.deviceTime || a?.serverTime || 0).getTime();
        const tb = new Date(b?.fixTime || b?.deviceTime || b?.serverTime || 0).getTime();
        return ta - tb;
      });

      const raw = sorted
        .map(p => {
          const lat = Number(p?.latitude);
          const lon = Number(p?.longitude);
          return (Number.isFinite(lat) && Number.isFinite(lon)) ? [lon, lat] : null;
        })
        .filter(Boolean);

      if (raw.length < 2) return null;

      const coords = [];
      let last = null;
      const minMeters = 25; // keep points only if moved at least this far
      const toRad = (x) => (x * Math.PI) / 180;
      const distM = (a, b) => {
        // Haversine
        const R = 6371000;
        const dLat = toRad(b[1] - a[1]);
        const dLon = toRad(b[0] - a[0]);
        const lat1 = toRad(a[1]);
        const lat2 = toRad(b[1]);
        const s = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
        return 2 * R * Math.asin(Math.sqrt(s));
      };

      for (const c of raw) {
        if (!last) {
          coords.push(c);
          last = c;
          continue;
        }
        if (distM(last, c) >= minMeters) {
          coords.push(c);
          last = c;
        }
      }

      // Always include final point.
      const final = raw[raw.length - 1];
      if (coords.length && (coords[coords.length - 1][0] != final[0] || coords[coords.length - 1][1] != final[1])) {
        coords.push(final);
      }
      if (coords.length < 2) return null;

      // Split into segments if there are big jumps (prevents huge "wedge" joins rendering as triangles).
      const jumpMeters = 2500;
      const segments = [];
      let seg = [coords[0]];
      for (let i = 1; i < coords.length; i++) {
        const a = coords[i - 1];
        const b = coords[i];
        if (distM(a, b) > jumpMeters) {
          if (seg.length >= 2) segments.push(seg);
          seg = [b];
        } else {
          seg.push(b);
        }
      }
      if (seg.length >= 2) segments.push(seg);
      if (!segments.length) return null;

      const geom = segments.length === 1
        ? { type: 'LineString', coordinates: segments[0] }
        : { type: 'MultiLineString', coordinates: segments };

      return {
        type: 'Feature',
        properties: { pointCount: coords.length, segmentCount: segments.length },
        geometry: geom,
      };
    } catch (e) {
      return null;
    }
  }

  _lineToBreadcrumbPoints(lineFeature, { everyN = 12 } = {}) {
    try {
      const geom = lineFeature?.geometry;
      if (!geom) return null;
      let coords = null;
      if (geom.type === 'LineString') coords = geom.coordinates;
      else if (geom.type === 'MultiLineString') coords = (geom.coordinates || []).flat();
      if (!Array.isArray(coords) || coords.length < 2) return null;
      const features = [];
      for (let i = 0; i < coords.length; i += Math.max(2, everyN)) {
        const c = coords[i];
        if (!Array.isArray(c) || c.length < 2) continue;
        features.push({
          type: 'Feature',
          properties: { i },
          geometry: { type: 'Point', coordinates: c },
        });
      }
      // Always add end point.
      const last = coords[coords.length - 1];
      features.push({ type: 'Feature', properties: { i: coords.length - 1, end: true }, geometry: { type: 'Point', coordinates: last } });
      return { type: 'FeatureCollection', features };
    } catch (e) {
      return null;
    }
  }

  _lineToEndpoints(lineFeature) {
    try {
      const geom = lineFeature?.geometry;
      if (!geom) return null;
      const getFirstLast = (coords) => ({ first: coords?.[0], last: coords?.[coords.length - 1] });
      let first = null;
      let last = null;
      if (geom.type === 'LineString') {
        ({ first, last } = getFirstLast(geom.coordinates));
      } else if (geom.type === 'MultiLineString') {
        const segs = geom.coordinates || [];
        if (segs.length) {
          first = segs[0]?.[0];
          const tail = segs[segs.length - 1];
          last = tail?.[tail.length - 1];
        }
      }
      if (!first || !last) return null;
      return {
        type: 'FeatureCollection',
        features: [
          { type: 'Feature', properties: { kind: 'start' }, geometry: { type: 'Point', coordinates: first } },
          { type: 'Feature', properties: { kind: 'end' }, geometry: { type: 'Point', coordinates: last } },
        ],
      };
    } catch (e) {
      return null;
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

      // If we don't have an HA GPS fix yet, try Traccar last known position
      // so the map still renders during early bring-up / mock-data testing.
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
        try {
          const fix = await this._getTraccarLastFix();
          if (fix && Number.isFinite(fix.lat) && Number.isFinite(fix.lon)) {
            lat = fix.lat;
            lon = fix.lon;
          }
        } catch (e) {}
      }
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
        el.innerHTML = '<div class="rc-label">No GPS fix yet.</div>';
        return;
      }

      const L = window.L;
      const m = L.map(el, { zoomControl: false, attributionControl: false });
      el._rcMap = m;

      // Hybrid tile setup: local offline tiles + online fallback for higher zooms.
      // Local tiles serve z0–offlineMaxZoom (default 6); online tiles fill in above that.
      const offlineMaxZ = this._offlineMaxZoom();
      const localUrl = this._tileUrl();
      const onlineUrl = this._onlineTileUrl();

      // Base layer: local offline tiles (always available, even without internet)
      const localLayer = L.tileLayer(localUrl, {
        maxZoom: offlineMaxZ,
        crossOrigin: true,
        updateWhenIdle: true,
        keepBuffer: 4,
      });
      localLayer.addTo(m);

      // Detail layer: online tiles for higher zoom levels (only loads when zoomed past offline coverage)
      if (onlineUrl) {
        const onlineLayer = L.tileLayer(onlineUrl, {
          minZoom: offlineMaxZ + 1,
          maxZoom: 19,
          crossOrigin: true,
          updateWhenIdle: true,
          keepBuffer: 2,
        });
        onlineLayer.addTo(m);
      }

      const trail = await this._loadTrail(trackerId, 6);
      const pts = (trail && trail.length ? trail : [[lat, lon]]);

      const saved = this._loadSavedMapView();
      if (saved) {
        m.setView([saved.lat, saved.lon], saved.zoom);
      } else if (pts.length >= 2) {
        const line = L.polyline(pts, { color: '#22c55e', weight: 4, opacity: 0.85 });
        line.addTo(m);
        m.fitBounds(line.getBounds(), { padding: [18, 18] });
      } else {
        m.setView([lat, lon], 14);
      }

      L.circleMarker([lat, lon], { radius: 8, color: '#0ea5e9', weight: 3, fillColor: '#0ea5e9', fillOpacity: 0.9 }).addTo(m);
      L.control.zoom({ position: 'bottomright' }).addTo(m);

      // Leaflet often needs an explicit resize once the container is visible / laid out.
      try {
        setTimeout(() => { try { m.invalidateSize(true); } catch (e) {} }, 50);
        setTimeout(() => { try { m.invalidateSize(true); } catch (e) {} }, 300);
        setTimeout(() => { try { m.invalidateSize(true); } catch (e) {} }, 1200);
      } catch (e) {}

      // Persist view so refresh doesn't snap back every time.
      try {
        m.on('moveend', () => this._saveMapView(m));
        m.on('zoomend', () => this._saveMapView(m));
      } catch (e) {}

      return m;
    } catch (e) {
      console.warn('leaflet mount failed', e);
      try { el.innerHTML = '<div class="rc-label">Map failed to render.</div>'; } catch (e2) {}
    }
  }

  async _mountMapLibreMap(el, { lat, lon } = {}) {
    try {
      if (!el) return;
      const ok = await this._ensureMapLibre();
      if (!ok) {
        el.innerHTML = '<div class="rc-label">Map failed to load (MapLibre missing).</div>';
        return;
      }
      if (el._rcMapLibre) {
        // Idempotent: don't recreate the map on HA re-renders.
        try { el._rcMapLibre.resize(); } catch (e) {}
        return el._rcMapLibre;
      }

      // If we don't have a GPS fix yet, fall back to Traccar last fix.
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
        try {
          const fix = await this._getTraccarLastFix();
          if (fix && Number.isFinite(fix.lat) && Number.isFinite(fix.lon)) {
            lat = fix.lat;
            lon = fix.lon;
          }
        } catch (e) {}
      }
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
        el.innerHTML = '<div class="rc-label">No GPS fix yet.</div>';
        return;
      }

      const styleUrl = this._mapStyleUrl();
      if (!styleUrl) {
        el.innerHTML = '<div class="rc-label">No vector map style URL configured.</div>';
        return;
      }

      // Register PMTiles protocol (once) so styles can reference pmtiles:// URLs.
      this._ensurePmtilesProtocol();

      // MapLibre wants a dedicated container node.
      el.innerHTML = '';
      const container = document.createElement('div');
      container.style.width = '100%';
      container.style.height = '100%';
      el.appendChild(container);

      const saved = this._loadSavedMapViewMapLibre();
      const centerLon = saved ? Number(saved.lon) : Number(lon);
      const centerLat = saved ? Number(saved.lat) : Number(lat);
      const zoom = saved ? Number(saved.zoom) : 10;

      const origin = (() => {
        try { return window.location.origin; } catch (e) { return ''; }
      })();

      const minimalRasterStyle = () => ({
        version: 8,
        glyphs: `${origin}/local/roamcore/fonts/{fontstack}/{range}.pbf`,
        sprite: `${origin}/local/roamcore/sprites/rc-sprite`,
        sources: {
          rc_raster: {
            type: 'raster',
            tiles: ['/rc-tiles/{z}/{x}/{y}.png'],
            tileSize: 256,
            maxzoom: 18,
          },
        },
        layers: [
          { id: 'background', type: 'background', paint: { 'background-color': '#0b1220' } },
          { id: 'rc_raster', type: 'raster', source: 'rc_raster', paint: { 'raster-opacity': 1.0 } },
        ],
      });

      // Allow using a local JSON style and patching in the current origin.
      let style = styleUrl;
      try {
        if (typeof styleUrl === 'string' && styleUrl.startsWith('/local/roamcore/styles/') && styleUrl.endsWith('.json')) {
          const obj = await this._loadJson(styleUrl);
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
        console.warn('failed to load/patch style json; falling back to raster-only style', e);
        style = minimalRasterStyle();
      }

      // If a remote style URL is configured and fails later, MapLibre will emit an error.
      // We still always add a raster base layer so the user never sees a flat grey background.

      const m = new maplibregl.Map({
        container,
        style,
        center: [centerLon, centerLat],
        zoom,
        // Prevent zooming into empty PMTiles ranges (avoids grey gaps).
        maxZoom: 11,
        attributionControl: false,
      });
      m.addControl(new maplibregl.NavigationControl({ showCompass: true, showZoom: true }), 'top-right');
      el._rcMapLibre = m;

      // Raster basemap fallback: ensures we never show a flat grey background if the vector
      // style fails to load tiles (offline / missing sources). Always available via /rc-tiles.
      const ensureRasterFallback = () => {
        try {
          if (m.getSource('rc_raster_fallback')) return;
          const maxZ = Number(this._getState('input_number.rc_map_offline_max_zoom'));
          const offlineMaxZ = Number.isFinite(maxZ) ? maxZ : 6;
          m.addSource('rc_raster_fallback', {
            type: 'raster',
            tiles: ['/rc-tiles/{z}/{x}/{y}.png'],
            tileSize: 256,
            // Allow zooming beyond offline coverage; the tile endpoint can decide what to return.
            // Keeping this high avoids MapLibre clamping/blanking.
            maxzoom: Math.max(offlineMaxZ, 18),
          });
          // Insert just above the style background (background is often opaque grey).
          const style = m.getStyle?.();
          const beforeId = (style?.layers || []).find(l => l && l.type !== 'background')?.id;
          m.addLayer({
            id: 'rc_raster_fallback',
            type: 'raster',
            source: 'rc_raster_fallback',
            paint: { 'raster-opacity': 1.0 },
            minzoom: 0,
          }, beforeId);
        } catch (e) {}
      };
      try {
        m.on('load', ensureRasterFallback);
        // Some style/source failures can happen before the user ever sees a tile.
        // Ensure the fallback is applied even if the vector sources error.
        m.on('error', ensureRasterFallback);
        setTimeout(ensureRasterFallback, 250);
      } catch (e) {}

      // Ensure marker exists and is updated on every render tick.
      const ensureMarker = () => {
        try {
          if (!Number.isFinite(lon) || !Number.isFinite(lat)) return;
          if (!el._rcMapLibreMarker) {
            el._rcMapLibreMarker = new maplibregl.Marker({ color: '#0ea5e9' })
              .setLngLat([Number(lon), Number(lat)])
              .addTo(m);
          } else {
            el._rcMapLibreMarker.setLngLat([Number(lon), Number(lat)]);
          }
        } catch (e) {}
      };

      // Route polyline: production path is Traccar reports/route. Fall back to mock GeoJSON.
      try {
        const mockUrl = '/local/roamcore/mock/track.geojson';

        const upsertRoute = async () => {
          try {
            // 1) Source-of-truth: Traccar route
            const positions = await this._getTraccarRoutePositions({ hours: 6 });
            let gj = this._positionsToGeojsonLine(positions);

            // 2) Fallback: mock demo route
            if (!gj) {
              const r = await fetch(mockUrl, { cache: 'no-cache' }).catch(() => null);
              if (r && r.ok) {
                const j = await r.json().catch(() => null);
                if (j && j.geometry) gj = j;
              }
            }
            if (!gj) return;

            const crumbs = this._lineToBreadcrumbPoints(gj, { everyN: 10 });
            const ends = this._lineToEndpoints(gj);

            if (!m.getSource('rc_route')) {
              m.addSource('rc_route', { type: 'geojson', data: gj });

              if (crumbs) m.addSource('rc_route_points', { type: 'geojson', data: crumbs });
              if (ends) m.addSource('rc_route_ends', { type: 'geojson', data: ends });

              // Google-ish route styling: casing + inner stroke.
              m.addLayer({
                id: 'rc_route_casing',
                type: 'line',
                source: 'rc_route',
                layout: { 'line-join': 'round', 'line-cap': 'round' },
                paint: {
                  'line-color': 'rgba(0,0,0,0.35)',
                  // Keep widths modest to avoid GPU triangulation artifacts.
                  'line-width': ['interpolate', ['linear'], ['zoom'], 4, 3, 8, 5, 12, 7, 16, 10],
                  'line-opacity': 0.9,
                },
              });
              m.addLayer({
                id: 'rc_route_line',
                type: 'line',
                source: 'rc_route',
                layout: { 'line-join': 'round', 'line-cap': 'round' },
                paint: {
                  'line-color': '#1a73e8',
                  'line-width': ['interpolate', ['linear'], ['zoom'], 4, 2, 8, 3.5, 12, 5.5, 16, 8],
                  'line-opacity': 0.95,
                },
              });

              // Breadcrumb dots along the route.
              if (crumbs) {
                m.addLayer({
                  id: 'rc_route_dots_outline',
                  type: 'circle',
                  source: 'rc_route_points',
                  paint: {
                    'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 2, 8, 3, 12, 4, 16, 5],
                    'circle-color': '#1a73e8',
                    'circle-opacity': 0.95,
                  },
                });
                m.addLayer({
                  id: 'rc_route_dots',
                  type: 'circle',
                  source: 'rc_route_points',
                  paint: {
                    'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 1.2, 8, 2, 12, 2.6, 16, 3.2],
                    'circle-color': '#ffffff',
                    'circle-opacity': 0.9,
                  },
                });
              }

              // Start/end markers.
              if (ends) {
                m.addLayer({
                  id: 'rc_route_ends',
                  type: 'circle',
                  source: 'rc_route_ends',
                  paint: {
                    'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 4, 8, 6, 12, 8, 16, 10],
                    'circle-color': [
                      'match',
                      ['get', 'kind'],
                      'start', '#34a853',
                      'end', '#ea4335',
                      '#1a73e8',
                    ],
                    'circle-stroke-color': '#ffffff',
                    'circle-stroke-width': 2,
                    'circle-opacity': 0.95,
                  },
                });
              }

              // Auto-fit to the route once, so the demo immediately looks like a trip.
              try {
                if (!this._rcRouteFitDone) {
                  const bounds = new maplibregl.LngLatBounds();
                  const addCoord = (c) => { if (c && c.length >= 2) bounds.extend([c[0], c[1]]); };
                  if (gj.geometry.type === 'LineString') {
                    for (const c of gj.geometry.coordinates) addCoord(c);
                  } else if (gj.geometry.type === 'MultiLineString') {
                    for (const seg of gj.geometry.coordinates) for (const c of seg) addCoord(c);
                  }
                  if (!bounds.isEmpty()) {
                    m.fitBounds(bounds, { padding: 40, duration: 0, maxZoom: 8 });
                    this._rcRouteFitDone = true;
                  }
                }
              } catch (e) {}
            } else {
              m.getSource('rc_route').setData(gj);
              try {
                if (crumbs && m.getSource('rc_route_points')) m.getSource('rc_route_points').setData(crumbs);
              } catch (e) {}
              try {
                if (ends && m.getSource('rc_route_ends')) m.getSource('rc_route_ends').setData(ends);
              } catch (e) {}
            }
          } catch (e) {}
        };

        m.on('load', async () => {
          try { ensureMarker(); } catch (e) {}
          await upsertRoute();
          // Refresh once after initial render; navigation sometimes races style load.
          try { setTimeout(() => { upsertRoute(); }, 1200); } catch (e) {}
        });
      } catch (e) {}

      // Keep marker in sync even if the map was mounted before we had a fix.
      try {
        ensureMarker();
        m.on('styledata', ensureMarker);
      } catch (e) {}

      // Persist view so refresh doesn't snap back.
      try {
        m.on('moveend', () => this._saveMapViewMapLibre(m));
        m.on('zoomend', () => this._saveMapViewMapLibre(m));
      } catch (e) {}

      // Resize after layout.
      try {
        setTimeout(() => { try { m.resize(); } catch (e) {} }, 50);
        setTimeout(() => { try { m.resize(); } catch (e) {} }, 300);
      } catch (e) {}

      return m;
    } catch (e) {
      console.warn('maplibre mount failed', e);
      try { el.innerHTML = '<div class="rc-label">Map failed to render.</div>'; } catch (e2) {}
    }
  }

  async _getTraccarLastFix() {
    try {
      if (!this._hass) return null;

      // Pick the first device and follow its positionId.
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

    const trackerId = this._pickTrackerEntity();
    const tracker = trackerId ? (this._hass?.states?.[trackerId] || null) : null;
    const lastUpdated = tracker?.last_updated || tracker?.last_changed || null;
    const lastUpdatedTxt = lastUpdated ? new Date(lastUpdated).toLocaleString() : '—';

    const spdTxt = spd == null ? '—' : `${round1(spd)} mph`;
    const elevTxt = elev == null ? '—' : `${round1(elev)} m`;
    const distTodayTxt = distToday == null ? '—' : `${round1(distToday)} mi`;
    const distTotalTxt = distTotal == null ? '—' : `${round1(distTotal)} mi`;
    const timeTodayTxt = (timeToday && timeToday !== 'unknown' && timeToday !== 'unavailable') ? timeToday : '—';
    const timeTotalTxt = (timeTotal && timeTotal !== 'unknown' && timeTotal !== 'unavailable') ? timeTotal : '—';
    const stopsTodayTxt = stops == null ? '—' : `${Math.round(stops)}`;

    const mode = this._mapMode();

    // Below-map data tiles (do not touch the map itself when iterating on this section).
    const tripWrappedTile = `
      <div style="margin-top: 14px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 14px; padding: 14px;">
        <div style="display:flex; justify-content:space-between; align-items:center; gap:10px;">
          <div>
            <div style="font-weight: 900; font-size: 14px;">Trip Wrapped</div>
          <div class="rc-label" style="margin-top:4px;">Generate a shareable recap (distance, drive time, top trip, etc.). Source-of-truth comes from Traccar reports.</div>
          </div>
          <div style="display:flex; gap:10px; flex-wrap:wrap; justify-content:flex-end;">
            <button class="rc-btn" id="rc-tripwrapped-open">Options</button>
            <a class="rc-btn" href="/local/roamcore/trip_wrapped/latest.html" target="_blank" rel="noreferrer">Open latest</a>
          </div>
        </div>
        <div id="rc-tripwrapped-preview" class="rc-label" style="margin-top:12px;">No summary loaded yet.</div>
      </div>
    `;

    const mapDataTiles = `
      <div style="margin-top: 14px; display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px;">
        <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 12px; min-width:0;">
          <div class="rc-label" style="font-weight:900; color: var(--rc-text);">Today’s trip</div>
          <div style="height:8px"></div>
          ${this._row('Distance', distTodayTxt)}
          ${this._row('Drive time', timeTodayTxt)}
          ${this._row('Stops', stopsTodayTxt)}
        </div>

        <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 12px; min-width:0;">
          <div class="rc-label" style="font-weight:900; color: var(--rc-text);">Live position</div>
          <div style="height:8px"></div>
          ${this._row('Location', (loc && loc !== 'unknown' && loc !== 'unavailable') ? loc : '—')}
          ${this._row('Speed', spdTxt)}
          ${this._row('Elevation', elevTxt)}
          ${this._row('Last updated', lastUpdatedTxt)}
        </div>

        <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 12px; min-width:0;">
          <div class="rc-label" style="font-weight:900; color: var(--rc-text);">Trip summary</div>
          <div style="height:8px"></div>
          ${this._row('Total distance', distTotalTxt)}
          ${this._row('Total drive time', timeTotalTxt)}
          ${this._row('Segments', segments == null ? '—' : `${Math.round(segments)}`)}
        </div>
      </div>
    `;

    const mapTile = `
      <div style="border-radius: 12px; overflow:hidden; border: 1px solid rgba(255,255,255,0.06); background: rgba(255,255,255,0.03); padding: 10px;">
        <div id="rc-map-inner" style="height: calc(100vh - 250px); min-height: 420px; max-height: 760px;">
          <div class="rc-label">Loading map…</div>
        </div>
      </div>
      <div style="display:flex; gap:8px; align-items:center; margin-top: 10px;">
        <div style="color: var(--rc-good); font-weight:900">⌖</div>
        <div style="font-weight:800; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${(loc && loc!=='unknown' && loc!=='unavailable') ? loc : '—'}</div>
      </div>
      <div class="rc-label" style="margin-top: 6px;">RoamCore map (${mode.mode === 'maplibre' ? 'MapLibre GL (vector)' : 'Leaflet (raster)'})${mode.mode === 'leaflet' ? ' with Traccar route overlay (last 6h)' : ''}.</div>
      <div style="margin-top: 10px; display:flex; gap:10px; flex-wrap:wrap;">
        <a class="rc-btn" href="http://192.168.1.66:8082/" target="_blank" rel="noreferrer">Open Traccar (fullscreen)</a>
      </div>
      ${mapDataTiles}
      ${tripWrappedTile}
    `;

    this._root.innerHTML = `
      <div class="rc-page">
        ${this._header('Map')}
        <div class="rc-grid">
          ${this._tile({title:'Map', icon:'↗', content: mapTile, className:'span-2'})}
        </div>
      </div>
    `;

    // Mount map into placeholder.
    try {
      const inner = this._root.querySelector('#rc-map-inner');
      if (inner) {
        // Don't nuke the DOM on every HA re-render (causes a visible flash).
        // Create the container once, then keep it stable.
        let el = this._root.querySelector('#rc-map');
        if (!el) {
          inner.innerHTML = `<div id="rc-map" style="height:100%; width:100%; border-radius:12px; overflow:hidden;"></div>`;
          el = this._root.querySelector('#rc-map');
        }
        const lat = this._num('sensor.rc_location_lat', null);
        const lon = this._num('sensor.rc_location_lon', null);
        if (mode.mode === 'maplibre') {
          // NOTE: _render is not async; keep this promise-based.
          this._mountMapLibreMap(el, { lat, lon })
            .then((m) => {
              try {
                // Update marker to current location without moving the camera.
                const marker = el?._rcMapLibreMarker;
                if (marker && Number.isFinite(lon) && Number.isFinite(lat)) {
                  marker.setLngLat([Number(lon), Number(lat)]);
                }
              } catch (e) {}
            })
            .catch(() => {});
        } else {
          const mapP = this._mountLeafletMap(el, { lat, lon, trackerId });
          // Best-effort: overlay last 6h track from Traccar (if available).
          Promise.resolve(mapP).then((map) => this._overlayTraccarTrack(map)).catch(() => {});
        }
      }
    } catch (e) {}

    // Trip Wrapped: async preview + modal.
    try {
      const btn = this._root.querySelector('#rc-tripwrapped-open');
      if (btn) btn.addEventListener('click', () => this._openTripWrappedModal());
      const prev = this._root.querySelector('#rc-tripwrapped-preview');
      if (prev) this._loadTripWrappedPreview(prev);
    } catch (e) {}
  }

  async _loadTripWrappedPreview(el) {
    try {
      if (!el) return;
      // Prefer today's auto summary if available, otherwise latest.
      const tryUrls = [
        '/local/roamcore/trip_wrapped/today.json',
        '/local/roamcore/trip_wrapped/latest.json',
      ];
      let obj = null;
      for (const u of tryUrls) {
        try {
          const r = await fetch(u, { cache: 'no-cache' });
          if (!r.ok) continue;
          obj = await r.json();
          break;
        } catch (e) {}
      }
      if (!obj) {
        el.textContent = 'No Trip Wrapped data found yet. Tap Options → Generate.';
        return;
      }

      const stats = obj.stats || {};
      const meta = obj.meta || {};
      const distM = Number(stats.totalDistanceM || 0);
      const durS = Number(stats.totalDurationS || 0);
      const distMi = (Number.isFinite(distM) ? distM / 1609.344 : 0);
      const h = Number.isFinite(durS) ? Math.floor(durS / 3600) : 0;
      const m = Number.isFinite(durS) ? Math.floor((durS % 3600) / 60) : 0;
      const trips = Number(meta.tripCount || 0);
      const gen = meta.generatedAt ? new Date(meta.generatedAt).toLocaleString() : '—';
      el.innerHTML = `Last generated: <b>${gen}</b> · Trips: <b>${trips}</b> · Distance: <b>${distMi.toFixed(1)} mi</b> · Drive time: <b>${h}:${String(m).padStart(2,'0')}</b>`;
    } catch (e) {
      try { el.textContent = 'Trip Wrapped preview failed to load.'; } catch (e2) {}
    }
  }

  _tripWrappedModalHtml() {
    // NOTE: keep this self-contained; do not touch the map container.
    return `
      <div class="rc-modal-backdrop" id="rc-tripwrapped-backdrop">
        <div class="rc-modal" role="dialog" aria-modal="true">
          <div class="rc-modal-head">
            <div style="font-weight:900; font-size: 16px;">Trip Wrapped</div>
            <button class="rc-btn" id="rc-tripwrapped-close">Close</button>
          </div>

          <div class="rc-label" style="margin-top:8px;">Pick a time range, then generate a shareable recap.</div>

          <div style="margin-top:12px; display:flex; gap:10px; flex-wrap:wrap;">
            <button class="rc-btn" id="rc-tripwrapped-preset-today">Today</button>
            <button class="rc-btn" id="rc-tripwrapped-preset-7d">Last 7 days</button>
            <button class="rc-btn" id="rc-tripwrapped-preset-30d">Last 30 days</button>
          </div>

          <div style="margin-top:14px; display:grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <div>
              <div class="rc-label" style="margin-bottom:6px;">From</div>
              <input id="rc-tripwrapped-from" type="datetime-local" class="rc-input" />
            </div>
            <div>
              <div class="rc-label" style="margin-bottom:6px;">To</div>
              <input id="rc-tripwrapped-to" type="datetime-local" class="rc-input" />
            </div>
          </div>

          <div style="margin-top:14px; display:grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <div>
              <div class="rc-label" style="margin-bottom:6px;">Export</div>
              <select id="rc-tripwrapped-export" class="rc-input">
                <option value="html_json" selected>HTML + JSON (recommended)</option>
                <option value="json">JSON only</option>
                <option value="html">HTML only</option>
              </select>
            </div>
            <div>
              <div class="rc-label" style="margin-bottom:6px;">After generate</div>
              <select id="rc-tripwrapped-after" class="rc-input">
                <option value="none" selected>Do nothing</option>
                <option value="open_latest">Open latest report</option>
              </select>
            </div>
          </div>

          <div style="margin-top:14px; display:grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <div>
              <div class="rc-label" style="margin-bottom:6px;">Map theme</div>
              <select id="rc-tripwrapped-theme" class="rc-input">
                <option value="light" selected>Light</option>
                <option value="dark">Dark</option>
              </select>
            </div>
            <div>
              <div class="rc-label" style="margin-bottom:6px;">Open</div>
              <div style="display:flex; gap:10px; flex-wrap:wrap;">
                <a class="rc-btn" href="/local/roamcore/trip_wrapped/latest.html" target="_blank" rel="noreferrer">Latest (light)</a>
                <a class="rc-btn" href="/local/roamcore/trip_wrapped/latest.html?theme=dark" target="_blank" rel="noreferrer">Latest (dark)</a>
              </div>
            </div>
          </div>

          <div class="rc-label" style="margin-top:12px;">Metrics come from Traccar (reports/trips/route/etc). RoamCore only renders the results.</div>

          <div style="margin-top:14px; display:flex; gap:10px; flex-wrap:wrap; justify-content:flex-end;">
            <button class="rc-btn" id="rc-tripwrapped-generate">Generate</button>
            <a class="rc-btn" href="/local/roamcore/trip_wrapped/latest.html" target="_blank" rel="noreferrer">Open latest</a>
          </div>

          <div id="rc-tripwrapped-status" class="rc-label" style="margin-top:10px;"></div>
        </div>
      </div>
    `;
  }

  _openTripWrappedModal() {
    try {
      if (!this._root) return;
      // Remove any existing modal.
      try { this._root.querySelector('#rc-tripwrapped-backdrop')?.remove?.(); } catch (e) {}

      const host = document.createElement('div');
      host.innerHTML = this._tripWrappedModalHtml();
      const backdrop = host.firstElementChild;
      if (!backdrop) return;
      this._root.appendChild(backdrop);

      const close = () => { try { backdrop.remove(); } catch (e) {} };
      backdrop.addEventListener('click', (e) => { if (e.target === backdrop) close(); });
      const closeBtn = backdrop.querySelector('#rc-tripwrapped-close');
      if (closeBtn) closeBtn.addEventListener('click', close);

      const fromEl = backdrop.querySelector('#rc-tripwrapped-from');
      const toEl = backdrop.querySelector('#rc-tripwrapped-to');
      const statusEl = backdrop.querySelector('#rc-tripwrapped-status');

      const setRange = (fromDate, toDate) => {
        try {
          const pad = (n) => String(n).padStart(2, '0');
          const fmt = (d) => `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
          if (fromEl) fromEl.value = fmt(fromDate);
          if (toEl) toEl.value = fmt(toDate);
        } catch (e) {}
      };

      const now = new Date();
      setRange(new Date(now.getTime() - 7*24*3600*1000), now);

      const todayBtn = backdrop.querySelector('#rc-tripwrapped-preset-today');
      if (todayBtn) todayBtn.addEventListener('click', () => {
        const d = new Date();
        const from = new Date(d);
        from.setHours(0,0,0,0);
        setRange(from, d);
      });
      const d7Btn = backdrop.querySelector('#rc-tripwrapped-preset-7d');
      if (d7Btn) d7Btn.addEventListener('click', () => setRange(new Date(Date.now()-7*24*3600*1000), new Date()));
      const d30Btn = backdrop.querySelector('#rc-tripwrapped-preset-30d');
      if (d30Btn) d30Btn.addEventListener('click', () => setRange(new Date(Date.now()-30*24*3600*1000), new Date()));

      const genBtn = backdrop.querySelector('#rc-tripwrapped-generate');
      if (genBtn) genBtn.addEventListener('click', async () => {
        try {
          genBtn.disabled = true;
          if (statusEl) statusEl.textContent = 'Generating…';

          const fromVal = fromEl?.value;
          const toVal = toEl?.value;
          const fromIso = fromVal ? new Date(fromVal).toISOString() : null;
          const toIso = toVal ? new Date(toVal).toISOString() : null;
          if (!fromIso || !toIso) {
            if (statusEl) statusEl.textContent = 'Pick valid From/To dates.';
            return;
          }

          // Persist selected dates into HA helpers so the export command uses them.
          await this._hass.callService('input_text', 'set_value', { entity_id: 'input_text.rc_trip_wrapped_from', value: fromIso });
          await this._hass.callService('input_text', 'set_value', { entity_id: 'input_text.rc_trip_wrapped_to', value: toIso });

          // For now, export always generates both HTML+JSON (shell_command does both).
          // We keep the UI option for future, but do not branch yet.
          await this._hass.callService('script', 'turn_on', { entity_id: 'script.rc_trip_wrapped_run' });

          const theme = backdrop.querySelector('#rc-tripwrapped-theme')?.value || 'light';
          const url = theme === 'dark'
            ? '/local/roamcore/trip_wrapped/latest.html?theme=dark'
            : '/local/roamcore/trip_wrapped/latest.html';

          if (statusEl) statusEl.innerHTML = `Done. Open: <a href="${url}" target="_blank" rel="noreferrer">latest.html</a>`;

          // Refresh preview (best effort)
          try {
            const prev = this._root.querySelector('#rc-tripwrapped-preview');
            if (prev) this._loadTripWrappedPreview(prev);
          } catch (e) {}

          const after = backdrop.querySelector('#rc-tripwrapped-after')?.value;
          if (after === 'open_latest') {
            try { window.open(url, '_blank'); } catch (e) {}
          }
        } catch (e) {
          console.warn('trip wrapped generate failed', e);
          if (statusEl) statusEl.textContent = 'Generate failed (check Traccar credentials/config).';
        } finally {
          try { genBtn.disabled = false; } catch (e) {}
        }
      });
    } catch (e) {
      console.warn('open trip wrapped modal failed', e);
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
