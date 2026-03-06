// RoamCore Tiles (v0) - per-tile custom Lovelace cards
// Goal: allow Lovelace grid/layout to manage responsive placement + reliable navigation.
// Naming convention reference: RoamCore/docs/reference/rc-entity-naming.md

function rcStatusToColor(status) {
  if (status === 'good') return 'var(--rc-good)';
  if (status === 'ok') return 'var(--rc-ok)';
  if (status === 'bad') return 'var(--rc-bad)';
  return 'var(--rc-muted)';
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

class RoamcoreBaseTile extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
    if (!this._root) {
      this.attachShadow({ mode: 'open' });
      this._root = document.createElement('div');
      this.shadowRoot.appendChild(this._root);
      const style = document.createElement('style');
      style.textContent = this._css();
      this.shadowRoot.appendChild(style);

      // delegated click handler (bind once)
      this._rcClickBound = true;
      this._root.addEventListener(click, (ev) => {
        const path = ev.composedPath ? ev.composedPath() : [];
        const candidates = path.length ? path : [ev.target];
        for (const node of candidates) {
          if (node && node.getAttribute) {
            const nav = node.getAttribute(data-nav);
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

  _tileWrap(innerHtml, navPath) {
    const clickable = navPath ? ' rc-click' : '';
    const dataNav = navPath ? ` data-nav="${navPath}"` : '';
    return `<div class="rc-tile${clickable}"${dataNav}>${innerHtml}</div>`;
  }

  _batterySvg(percent, fillColor) {
    const p = Math.max(0, Math.min(100, Number(percent) || 0));
    const fillW = (p / 100) * 34;
    return `
      <svg viewBox="0 0 48 24" class="rc-batt-svg">
        <rect x="1" y="4" width="40" height="16" rx="2" fill="none" stroke="rgba(255,255,255,0.35)" stroke-width="2"/>
        <rect x="41" y="8" width="4" height="8" rx="1" fill="rgba(255,255,255,0.25)"/>
        <rect x="3" y="6" width="${fillW}" height="12" rx="1" fill="${fillColor}"/>
        <path d="M24 6 L20 12 L23 12 L21 18 L28 11 L24 11 L26 6 Z" fill="rgba(0,0,0,0.75)"/>
      </svg>
    `;
  }

  _bars(color) {
    return [1, 2, 3, 4]
      .map((i) => {
        const h = i * 7 + 6;
        const bg = color !== 'var(--rc-muted)' ? color : 'rgba(255,255,255,0.12)';
        return `<div class="rc-bar" style="height:${h}px;background:${bg}"></div>`;
      })
      .join('');
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
      .rc-click { cursor: pointer; }
      .rc-click:hover { filter: brightness(1.05); }
      .rc-tile {
        background: linear-gradient(180deg, var(--rc-card), var(--rc-card2));
        border: 1px solid var(--rc-border);
        border-radius: 14px;
        padding: 14px;
        min-height: 170px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.35);
        color: var(--rc-text);
      }
      .rc-tile-head { display:flex; justify-content:space-between; align-items:center; margin-bottom: 10px; }
      .rc-tile-title { font-size:13px; color:var(--rc-muted); font-weight:700; }
      .rc-tile-sub { font-size:12px; color:var(--rc-muted); font-weight:600; }
      .rc-muted { color: var(--rc-muted); }
      .rc-strong { color: var(--rc-text); font-weight:700; }
      .rc-batt-svg { width:64px; height:32px; }
      .rc-bar { width:8px; border-radius:3px; }
      .rc-van-svg { width:110px; height:52px; }
      .rc-map-svg { width:100%; height:100%; }
      .rc-power-main { display:flex; gap:12px; align-items:center; }
      .rc-power-soc { font-size:44px; font-weight:900; letter-spacing:0.5px; }
      .rc-power-time { margin-top: 10px; font-size: 13px; }
      .rc-pillrow { display:grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 16px; }
      .rc-pill { display:flex; justify-content:space-between; align-items:center; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 10px 12px; font-size: 12px; min-width:0; gap:10px; }
      .rc-net-main { display:flex; flex-direction:column; align-items:center; justify-content:center; gap:6px; min-height:92px; }
      .rc-bars { display:flex; gap:4px; align-items:flex-end; margin-top: 4px; }
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
      .rc-deg { font-size:20px; font-weight:900; }
      .rc-map-main { display:flex; flex-direction:column; align-items:center; justify-content:center; gap:10px; height: 120px; }
      .rc-map-box { width: 140px; height: 86px; border-radius: 12px; overflow:hidden; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); }
      .rc-map-loc { display:flex; gap:6px; align-items:center; font-size:13px; max-width:180px; }
      .rc-trunc { max-width:150px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
      .rc-map-stats { display:grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 6px; }
    `;
  }
}

class RoamcorePowerTile extends RoamcoreBaseTile {
  _render() {
    if (!this._root || !this._hass) return;
    const soc = this._num('sensor.rc_power_battery_soc', null);
    const solarW = this._num('sensor.rc_power_solar_power', null);
    const shore = this._getState('binary_sensor.rc_power_shore_connected');
    const invStatus = this._getState('sensor.rc_power_inverter_status');

    const pStatus = rcPowerStatusFromSoc(soc);
    const pColor = rcStatusToColor(pStatus);

    const socTxt = soc == null ? '—' : `${Math.round(soc)}%`;
    const chargingSource = (solarW != null && solarW > 50) ? 'Solar' : '';
    const shoreTxt = shore === 'on' ? 'Connected' : (shore === 'off' ? 'Off' : '—');
    const invTxtRaw = (invStatus && invStatus !== 'unknown' && invStatus !== 'unavailable') ? String(invStatus) : '—';
    const invTxt = (invTxtRaw === 'on' ? 'On' : invTxtRaw === 'off' ? 'Off' : invTxtRaw);

    const inner = `
      <div class="rc-tile-head">
        <div class="rc-tile-title">Power</div>
        <div class="rc-tile-sub">${chargingSource ? `☼ ${chargingSource}` : ''}</div>
      </div>
      <div class="rc-power-main">
        <div class="rc-batt">${this._batterySvg(soc ?? 0, pColor)}</div>
        <div class="rc-power-soc" style="color:${pColor}">${socTxt}</div>
      </div>
      <div class="rc-power-time"><span class="rc-muted">Time to full:</span> <span class="rc-strong">—</span></div>
      <div class="rc-pillrow">
        <div class="rc-pill"><span class="rc-muted">Inverter</span><span class="rc-strong">${invTxt}</span></div>
        <div class="rc-pill"><span class="rc-muted">Shore</span><span class="rc-strong">${shoreTxt}</span></div>
      </div>
    `;

    this._root.innerHTML = this._tileWrap(inner, '/lovelace/roamcore/power');
  }
}

class RoamcoreNetworkTile extends RoamcoreBaseTile {
  _render() {
    if (!this._root || !this._hass) return;
    const netStatus = this._getState('sensor.rc_net_wan_status');
    const netSource = this._getState('sensor.rc_net_wan_source');
    const down = this._num('sensor.rc_net_download', null);
    const up = this._num('sensor.rc_net_upload', null);
    const ping = this._num('sensor.rc_net_ping', null);

    const netLabel = (netStatus && netStatus !== 'unknown' && netStatus !== 'unavailable') ? (netStatus === 'good' ? 'Good' : netStatus === 'ok' ? 'OK' : netStatus === 'bad' ? 'Poor' : netStatus) : '—';
    const netColor = rcStatusToColor(netStatus);
    const src = (netSource && netSource !== 'unknown' && netSource !== 'unavailable') ? netSource : '—';

    const inner = `
      <div class="rc-tile-head"><div class="rc-tile-title">Network</div><div class="rc-tile-sub">⌁</div></div>
      <div class="rc-net-main">
        <div class="rc-bars">${this._bars(netColor)}</div>
        <div class="rc-net-status"><span class="rc-dot" style="background:${netColor}"></span><span class="rc-net-label" style="color:${netColor}">${netLabel}</span></div>
        <div class="rc-net-src">⌬ <span class="rc-muted">${rcCap(src)}</span></div>
      </div>
      <div class="rc-net-stats">
        <div class="rc-stat"><div class="rc-stat-val">${down == null ? '—' : Math.round(down)}</div><div class="rc-muted">Mbps ↓</div></div>
        <div class="rc-stat"><div class="rc-stat-val">${up == null ? '—' : Math.round(up)}</div><div class="rc-muted">Mbps ↑</div></div>
        <div class="rc-stat"><div class="rc-stat-val">${ping == null ? '—' : Math.round(ping)}</div><div class="rc-muted">ms</div></div>
      </div>
    `;

    this._root.innerHTML = this._tileWrap(inner, '/lovelace/roamcore/network');
  }
}

class RoamcoreLevelTile extends RoamcoreBaseTile {
  _levelStatus(pitch, roll) {
    const v = Math.max(Math.abs(pitch ?? 0), Math.abs(roll ?? 0));
    if (!Number.isFinite(v)) return { label: '—', color: 'var(--rc-muted)' };
    if (v < 2) return { label: 'Level', color: 'var(--rc-good)' };
    if (v < 6) return { label: 'Slight Tilt', color: 'var(--rc-ok)' };
    return { label: 'Not Level', color: 'var(--rc-bad)' };
  }

  _render() {
    if (!this._root || !this._hass) return;
    const pitch = this._num('sensor.rc_system_level_pitch_deg', null);
    const roll = this._num('sensor.rc_system_level_roll_deg', null);
    const pitchAbs = pitch == null ? '—' : Math.abs(pitch).toFixed(1);
    const rollAbs = roll == null ? '—' : Math.abs(roll).toFixed(1);
    const status = this._levelStatus(pitch, roll);

    const inner = `
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
    `;

    this._root.innerHTML = this._tileWrap(inner, '/lovelace/roamcore/level');
  }
}

class RoamcoreMapTile extends RoamcoreBaseTile {
  _render() {
    if (!this._root || !this._hass) return;
    const loc = 'Lake District, UK';
    const today = '42';
    const total = '1847';

    const inner = `
      <div class="rc-tile-head"><div class="rc-tile-title">Map</div><div class="rc-tile-sub">↗</div></div>
      <div class="rc-map-main">
        <div class="rc-map-box">${this._mapSvg()}</div>
        <div class="rc-map-loc"><span class="rc-pin" style="color:var(--rc-good)">⌖</span><span class="rc-strong rc-trunc">${loc}</span></div>
      </div>
      <div class="rc-map-stats">
        <div class="rc-stat"><div class="rc-stat-val">${today} mi</div><div class="rc-muted">Today</div></div>
        <div class="rc-stat"><div class="rc-stat-val">${total} mi</div><div class="rc-muted">Total</div></div>
      </div>
    `;

    this._root.innerHTML = this._tileWrap(inner, '/lovelace/roamcore/map');
  }
}

customElements.define('roamcore-power-tile', RoamcorePowerTile);
customElements.define('roamcore-network-tile', RoamcoreNetworkTile);
customElements.define('roamcore-level-tile', RoamcoreLevelTile);
customElements.define('roamcore-map-tile', RoamcoreMapTile);
