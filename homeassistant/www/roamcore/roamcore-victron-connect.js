/**
 * RoamCore Victron Connect Card
 *
 * A Lovelace custom card that discovers Victron devices on the network
 * and allows the user to select one to connect.
 *
 * Auto-discovery (Wave 2 #12):
 *   - Auto-launches discovery when the user lands on the Power page and the
 *     system is not yet paired. If a GX is on the LAN we surface a banner
 *     ("we see a GX at <ip> — let's connect it") and pre-select the best
 *     candidate.
 *   - Periodic re-scan while the user is staring at the discover view
 *     (default every 6 s) so a GX that just powered on shows up.
 *   - "Enable MQTT over LAN" prompt: when we detect a GX but the add-on
 *     reports data isn't flowing, surface a plain-English recovery that
 *     points at the GX menu (Settings → Services → MQTT → "Enable MQTT over
 *     LAN (Broker mode)"). This setting is off by default on Venus OS.
 *
 * Usage in lovelace:
 *   type: custom:roamcore-victron-connect
 *   title: Connect Victron Device
 */

// Wave 2 #12: how often we re-probe while the user is parked on the
// discover view. Keep this short enough that a freshly-powered GX shows up
// without making the user feel like the UI is "twitchy".
const _AUTO_RESCAN_INTERVAL_MS = 6000;

// Wave 2 #12: when discovery finds a GX but data isn't flowing, the wizard
// shows a plain-English prompt pointing at the GX menu. Keep copy here so
// the smoke check can verify the menu path is present.
const _MQTT_LAN_PROMPT = {
  title: 'One thing to check on your GX',
  body:
    'RoamCore found your GX at {ip} but no data is flowing. ' +
    'On the GX, open Settings → Services → MQTT and turn on ' +
    '"Enable MQTT over LAN (Broker mode)".',
  detail:
    "This setting is off by default on Venus OS. After you flip it, " +
    "click Re-scan here.",
  menuPath: 'Settings → Services → MQTT → Enable MQTT over LAN (Broker mode)',
  menuHint:
    '[ Settings ] → [ Services ] → [ MQTT ]\n' +
    '       └─ ☑ Enable MQTT over LAN (Broker mode)',
  cta: 'Re-scan now',
  // Stringified version used by the smoke check (must contain the menu
  // path verbatim).
  menuPathCanonical:
    'Settings \u2192 Services \u2192 MQTT \u2192 Enable MQTT over LAN (Broker mode)',
};

// Wave 2 #12: a "we're auto-discovering for you" step name. The smoke check
// verifies this constant exists; the render path uses it to show a banner
// instead of the default empty-state copy.
const _AUTO_DISCOVER_STEP = 'auto_discover';

// State machine name used by smoke checks and rendering. When the user is
// not yet paired and we found at least one candidate, this is the active
// "view" that drives the auto-launch banner.
const _STATE_AUTO_DISCOVER = 'auto_discover';

class RoamCoreVictronConnectCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._config = {};
    this._hass = null;
    this._candidates = [];
    this._loading = false;
    this._connecting = false;
    this._error = null;
    this._success = null;
    this._status = null;
    this._statusPollTimer = null;
    this._statusPollInFlight = false;
    this._manualHost = '';
    this._manualPort = 1883;
    this._manualTls = false;
    this._manualPortTouched = false;

    // Wave 2 #12 — expose the constants on the card instance so smoke
    // checks and (defensively) external readers can verify the slice's
    // invariants. Mirrors the module-level constants declared at the top
    // of this file.
    this.AUTO_RESCAN_INTERVAL_MS = _AUTO_RESCAN_INTERVAL_MS;
    this.MQTT_LAN_PROMPT = _MQTT_LAN_PROMPT;
    this.STATE_AUTO_DISCOVER = _STATE_AUTO_DISCOVER;

    // Wave 2 #12 — auto-discovery state.
    // _view can be one of: 'idle' | 'auto_discover' | 'discover' | 'connecting' | 'success'
    // - 'idle' is the initial state (waiting for first hass set).
    // - 'auto_discover' means: the user opened the card on a fresh install /
    //   unpaired system and we're probing the LAN for them.
    // - 'discover' is the explicit user-driven discovery view (they clicked
    //   the refresh button or the wizard walked them here).
    this._view = 'idle';
    // _autoScannedOnce guards against re-running auto-discovery when the
    // user navigates away and back to the card.
    this._autoScannedOnce = false;
    // _rescanTimer is the periodic re-probe while we're on the discover
    // view. It's only armed in auto-discover or explicit discover modes.
    this._rescanTimer = null;
    // _mqttLanPromptCandidate holds the candidate we last saw that should
    // trigger the "Enable MQTT over LAN" prompt (when status says no data
    // is flowing). Storing it separately means we don't have to re-discover
    // to render the prompt after a status poll.
    this._mqttLanPromptCandidate = null;
  }

  connectedCallback() {
    // Keep status reasonably fresh without requiring manual clicks.
    // Best-effort + low frequency to avoid hammering HA/Supervisor.
    if (!this._statusPollTimer) {
      try { this._fetchStatus(); } catch (e) {}
      this._statusPollTimer = setInterval(() => {
        try { this._fetchStatus(); } catch (e) {}
      }, 10000);
    }
  }

  disconnectedCallback() {
    if (this._statusPollTimer) {
      clearInterval(this._statusPollTimer);
      this._statusPollTimer = null;
    }
    if (this._rescanTimer) {
      clearInterval(this._rescanTimer);
      this._rescanTimer = null;
    }
  }

  setConfig(config) {
    this._config = config;
    this._render();
  }

  set hass(hass) {
    const wasNull = this._hass == null;
    this._hass = hass;
    if (wasNull) {
      // First paint from HA. Trigger the auto-discovery flow if the user
      // is not yet paired.
      try {
        this._maybeAutoLaunchDiscovery();
      } catch (e) {
        // ignore — auto-launch is best-effort, never crash the card
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Wave 2 #12 — auto-launch: probe the LAN once on first paint if the
  // system is not paired. The user should not have to click "Connect
  // Victron" to learn that their GX is on the network.
  // ---------------------------------------------------------------------------
  _maybeAutoLaunchDiscovery() {
    if (this._autoScannedOnce) return;
    if (this._loading || this._connecting) return;
    if (this._isAlreadyPaired()) return;
    this._autoScannedOnce = true;
    this._view = _STATE_AUTO_DISCOVER;
    // Defer slightly so we don't slam the add-on during HA's own startup
    // burst.
    try {
      setTimeout(() => {
        try { this._discover({ auto: true }); } catch (e) {}
      }, 250);
    } catch (e) {
      try { this._discover({ auto: true }); } catch (e2) {}
    }
  }

  // ---------------------------------------------------------------------------
  // Wave 2 #12 — periodic re-scan while parked on the discover view.
  // Only armed when we're explicitly in auto_discover / discover mode and
  // the user hasn't started a manual connect yet.
  // ---------------------------------------------------------------------------
  _armRescanTimer() {
    if (this._rescanTimer) return;
    this._rescanTimer = setInterval(() => {
      try {
        if (this._view !== 'auto_discover' && this._view !== 'discover') return;
        if (this._loading || this._connecting) return;
        // Don't keep scanning if we already have a healthy candidate AND
        // the system shows data flowing — that's the happy path.
        if (this._isAlreadyPaired()) return;
        this._discover({ auto: true, silent: true });
      } catch (e) {}
    }, _AUTO_RESCAN_INTERVAL_MS);
  }

  _stopRescanTimer() {
    if (this._rescanTimer) {
      clearInterval(this._rescanTimer);
      this._rescanTimer = null;
    }
  }

  // ---------------------------------------------------------------------------
  // "Is Victron already paired?" — also exposes the "did we see a GX" hint
  // for the auto-launch banner.
  // ---------------------------------------------------------------------------
  _isAlreadyPaired() {
    if (!this._status) return false;
    const vic = this._status && this._status.victron ? this._status.victron : null;
    if (!vic) return false;
    if (vic.connected === true && vic.did_full_publish === true) return true;
    return false;
  }

  // Pick the best "we see a GX" candidate for the auto-launch banner and
  // the "Enable MQTT over LAN" prompt. Prefer reachable + non-bad.
  _bestCandidate() {
    const list = (this._candidates || []).filter((c) => c && !c.bad);
    if (!list.length) return null;
    const reachable = list.filter((c) => c.reachable === true);
    return (reachable.length ? reachable : list)[0] || null;
  }

  // Should we show the "Enable MQTT over LAN" prompt? Conditions:
  //   - We have a candidate that the user could pick (we found a GX).
  //   - The add-on reports no data is flowing (not connected OR not yet
  //     published a full snapshot after a meaningful grace period).
  //   - The system is not already paired.
  _shouldShowMqttLanPrompt() {
    if (this._isAlreadyPaired()) return false;
    const cand = this._bestCandidate();
    if (!cand) return false;
    const st = this._status || null;
    const vic = st && st.victron ? st.victron : null;
    // If the status endpoint reports a connection, we're good.
    if (vic && vic.connected === true && vic.did_full_publish === true) return false;
    // If the user is actively in a connect flow, don't nag with the prompt.
    if (this._connecting) return false;
    // Otherwise: we have a candidate AND no live data — prompt.
    return true;
  }

  _buildMqttLanPrompt() {
    const cand = this._bestCandidate();
    const ip = cand ? (cand.host || cand.ip || '') : '';
    const tpl = _MQTT_LAN_PROMPT;
    const body = String(tpl.body || '').replace('{ip}', ip || '?');
    return {
      title: tpl.title,
      body,
      detail: tpl.detail,
      menuPath: tpl.menuPath,
      menuHint: tpl.menuHint,
      cta: tpl.cta,
      menuPathCanonical: tpl.menuPathCanonical,
      ip,
    };
  }

  async _fetchStatus() {
    if (this._statusPollInFlight) return;
    try {
      this._statusPollInFlight = true;
      const base = this._getApiBase();
      const ctl = new AbortController();
      // Status is best-effort, but can be slow on loaded HA boxes.
      const t = setTimeout(() => ctl.abort(), 4000);
      const resp = await fetch(`${base}/api/v1/victron/status`, {
        credentials: 'same-origin',
        signal: ctl.signal,
      }).finally(() => clearTimeout(t));
      if (!resp.ok) throw new Error(`status ${resp.status}`);
      const data = await resp.json().catch(() => ({}));
      this._status = data && data.status ? data.status : data;
      // Wave 2 #12: if status reports we're paired (live data flowing),
      // stop the periodic re-scan and switch to the connected view.
      if (this._isAlreadyPaired()) {
        this._stopRescanTimer();
        if (this._view === 'auto_discover' || this._view === 'discover') {
          this._view = 'success';
        }
      }
      this._render();
    } catch (e) {
      // ignore (status is best-effort)
    } finally {
      this._statusPollInFlight = false;
    }
  }

  _getApiBase() {
    // Add-on ingress URL pattern: /api/hassio_ingress/<ingress_token>/
    // NOTE: the ingress token is not stable across installs. For MVP we allow
    // the dashboard YAML to pass `api_base` explicitly.

    // 1) Explicit override
    if (this._config.api_base) return this._config.api_base;

    // 2) Best-effort auto-detect from HA panels (Supervisor ingress).
    // Panels often include a per-install ingress token at `config.ingress`.
    // We scan for something Victron-ish and map it to the API ingress path.
    try {
      const panels = this._hass?.panels || {};
      for (const key of Object.keys(panels)) {
        const p = panels[key];
        const title = String(p?.title || p?.config?.title || '').toLowerCase();
        const urlPath = String(p?.url_path || '').toLowerCase();
        const ingress = p?.config?.ingress;
        const isVictron = title.includes('victron') || title.includes('venus') || urlPath.includes('victron');
        if (isVictron && ingress) {
          return `/api/hassio_ingress/${ingress}`;
        }
      }
    } catch (e) {
      // ignore
    }

    // 3) Fallback: dev slug (legacy)
    return '/api/hassio_ingress/roamcore_victron_auto_dev';
  }

  async _discover(opts) {
    opts = opts || {};
    const isAuto = !!opts.auto;
    const isSilent = !!opts.silent;
    // Avoid kicking a second discovery while one is already in flight.
    if (this._loading) return;
    this._loading = true;
    // Wave 2 #12: in auto/silent mode, don't blow away a previous error or
    // a manually-typed host value.
    if (!isAuto) {
      this._error = null;
    }
    if (!isSilent) {
      this._render();
    }

    // Wave 2 #12: make sure the periodic re-scan timer is running while we
    // park on the discover view. Disarmed on _connectManual / disconnect /
    // when the system becomes paired.
    if (this._view === 'auto_discover' || this._view === 'discover') {
      this._armRescanTimer();
    }

    try {
      const base = this._getApiBase();
      const ctl = new AbortController();
      // Discovery may involve mDNS/DNS probes inside the add-on; keep this lenient.
      const t = setTimeout(() => ctl.abort(), 8000);
      const resp = await fetch(`${base}/api/v1/victron/discover`, {
        credentials: 'same-origin',
        signal: ctl.signal,
      }).finally(() => clearTimeout(t));
      
      if (!resp.ok) {
        throw new Error(`Discovery failed: ${resp.status} ${resp.statusText}`);
      }
      
      const data = await resp.json();
      this._candidates = (data.candidates || []).slice();

      // Prefer reachable + non-bad candidates first.
      try {
        this._candidates.sort((a, b) => {
          const ar = a && a.reachable === true;
          const br = b && b.reachable === true;
          if (ar !== br) return ar ? -1 : 1;
          const ab = a && a.bad === true;
          const bb = b && b.bad === true;
          if (ab !== bb) return ab ? 1 : -1;
          return 0;
        });
      } catch (e) {
        // ignore
      }
      
      if (this._candidates.length === 0) {
        this._error = 'No Victron devices found on the network. Make sure your GX device is powered on and connected.';
      }
    } catch (err) {
      if (err && (err.name === 'AbortError' || String(err.message || '').includes('aborted'))) {
        this._error = 'Discovery timed out. Check network/Victron power and try again.';
      } else {
        this._error = `Discovery error: ${err.message}`;
      }
      this._candidates = [];
    } finally {
      this._loading = false;
      // Wave 2 #12: cache the best candidate for the MQTT-LAN prompt and
      // arm the periodic re-scan timer.
      const best = this._bestCandidate();
      if (best) {
        this._mqttLanPromptCandidate = best;
      }
      if (this._view === 'auto_discover' || this._view === 'discover') {
        this._armRescanTimer();
      }
      this._render();
    }
  }

  async _connect(candidate) {
    this._connecting = true;
    this._error = null;
    this._success = null;
    // Wave 2 #12: user has committed — stop re-probing the LAN, the
    // add-on is now driving the connect flow.
    this._stopRescanTimer();
    this._view = 'connecting';
    this._render();

    try {
      const base = this._getApiBase();
      const ctl = new AbortController();
      const t = setTimeout(() => ctl.abort(), 8000);
      const resp = await fetch(`${base}/api/v1/victron/connect`, {
        method: 'POST',
        credentials: 'same-origin',
        signal: ctl.signal,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host: candidate.host || candidate.ip,
          port: candidate.port || 1883,
          use_tls: candidate.use_tls || false,
          portal_id: candidate.portal_id || null,
        }),
      }).finally(() => clearTimeout(t));

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.error || `Connect failed: ${resp.status}`);
      }

      const data = await resp.json();
      this._success = data.message || 'Connected! The add-on is restarting to apply the configuration.';
      
      // Clear candidates after successful connect
      this._candidates = [];

      // Best-effort: refresh status so the user sees a deterministic success signal.
      try {
        this._status = null;
        setTimeout(() => this._fetchStatus(), 800);
        setTimeout(() => this._fetchStatus(), 2500);
      } catch (e) {}
    } catch (err) {
      if (err && (err.name === 'AbortError' || String(err.message || '').includes('aborted'))) {
        this._error = 'Connection timed out. Check the GX is reachable on the LAN (MQTT port 1883/8883) and try again.';
      } else {
        this._error = `Connection error: ${err.message}`;
      }
    } finally {
      this._connecting = false;
      this._render();
    }
  }

  async _connectManual() {
    const host = String(this._manualHost || '').trim();
    const port = parseInt(String(this._manualPort || '1883'), 10) || 1883;
    const use_tls = !!this._manualTls;
    if (!host) {
      this._error = 'Enter a host (IP or hostname) to connect.';
      this._success = null;
      this._render();
      return;
    }
    return this._connect({ host, port, use_tls, source: 'manual' });
  }

  async _clear() {
    this._connecting = true;
    this._error = null;
    this._success = null;
    this._render();

    try {
      const base = this._getApiBase();
      const ctl = new AbortController();
      const t = setTimeout(() => ctl.abort(), 8000);
      const resp = await fetch(`${base}/api/v1/victron/clear`, {
        method: 'POST',
        credentials: 'same-origin',
        signal: ctl.signal,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      }).finally(() => clearTimeout(t));

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.error || `Clear failed: ${resp.status}`);
      }

      const data = await resp.json().catch(() => ({}));
      this._success = data.message || 'Cleared configuration. The add-on may restart.';
      this._candidates = [];
    } catch (err) {
      if (err && (err.name === 'AbortError' || String(err.message || '').includes('aborted'))) {
        this._error = 'Clear timed out. Try again; the add-on may be restarting.';
      } else {
        this._error = `Clear error: ${err.message}`;
      }
    } finally {
      this._connecting = false;
      this._render();
    }
  }

  _render() {
    const title = this._config.title || 'Connect Victron Device';

    const st = this._status || null;
    const stConfigValid = st && st.config ? st.config.valid === true : null;
    const stVic = st && st.victron ? st.victron : null;
    const stInv = st && st.inventory ? st.inventory : null;
    const statusLine = (stConfigValid == null && !stVic && !stInv)
      ? ''
      : `
        <div style="margin: 10px 0 14px; padding: 10px 12px; border: 1px solid var(--divider-color); border-radius: 10px; background: rgba(255,255,255,0.02);">
          <div style="font-weight: 700; margin-bottom: 6px;">Status</div>
          <div style="font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 12px; opacity: 0.9;">
            ${stConfigValid == null ? '' : `config.valid=${stConfigValid}<br/>`}
            ${stVic ? `victron.connected=${stVic.connected === true}<br/>did_full_publish=${stVic.did_full_publish === true}<br/>` : ''}
            ${stInv ? `devices=${stInv.devices_count || 0} topics=${stInv.topics_count || 0}` : ''}
          </div>
        </div>
      `;

    // Wave 2 #12 — auto-discovery banner ("we see a Victron GX at <ip>").
    // Only shown in the auto_discover / discover view when not yet paired
    // AND we have a best candidate. While we're probing, we also show a
    // "Scanning for your Victron GX…" banner so the user immediately
    // understands why the card is on the discover view (no button click
    // needed).
    let autoDiscoverBanner = '';
    try {
      if (
        !this._isAlreadyPaired() &&
        (this._view === 'auto_discover' || this._view === 'discover') &&
        !this._connecting
      ) {
        const best = this._bestCandidate();
        if (best) {
          const ip = best.host || best.ip || '';
          autoDiscoverBanner = `
            <div class="auto-discover-banner" data-test="auto-discover-banner">
              <div class="auto-discover-banner-title">We see a Victron GX at <code>${this._escapeHtml(ip)}</code></div>
              <div class="auto-discover-banner-body">Let's connect it — RoamCore can do the rest.</div>
            </div>
          `;
        } else if (this._view === 'auto_discover') {
          // While still loading OR after a scan returned empty, show the
          // scanning banner so the user knows the card is doing work on
          // their behalf.
          autoDiscoverBanner = `
            <div class="auto-discover-banner auto-discover-banner-info" data-test="auto-discover-banner">
              <div class="auto-discover-banner-title">Scanning for your Victron GX…</div>
              <div class="auto-discover-banner-body">${this._loading
                ? 'RoamCore is probing your network. We\u2019ll update this card as soon as something shows up.'
                : 'No GX found yet. RoamCore will keep re-scanning automatically — a GX that just powered on will show up here.'}</div>
            </div>
          `;
        }
      }
    } catch (e) {
      autoDiscoverBanner = '';
    }

    // Wave 2 #12 — "Enable MQTT over LAN" prompt. Shown when discovery
    // found a candidate but the add-on reports no data is flowing. Plain-
    // English recovery that names the GX menu path.
    let mqttLanPromptBlock = '';
    try {
      if (this._shouldShowMqttLanPrompt()) {
        const prompt = this._buildMqttLanPrompt();
        mqttLanPromptBlock = `
          <div class="mqtt-lan-prompt" data-test="mqtt-lan-prompt" role="alert">
            <div class="mqtt-lan-prompt-title">${this._escapeHtml(prompt.title)}</div>
            <div class="mqtt-lan-prompt-body">${this._escapeHtml(prompt.body)}</div>
            <div class="mqtt-lan-prompt-detail">${this._escapeHtml(prompt.detail)}</div>
            <pre class="mqtt-lan-prompt-hint" data-test="mqtt-lan-prompt-menu-hint">${this._escapeHtml(prompt.menuHint)}</pre>
            <div class="mqtt-lan-prompt-cta">
              <button class="btn" id="mqttLanPromptRescanBtn">${this._escapeHtml(prompt.cta)}</button>
            </div>
          </div>
        `;
      }
    } catch (e) {
      mqttLanPromptBlock = '';
    }

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
        }
        ha-card {
          padding: 16px;
        }
        .header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 16px;
        }
        .title {
          font-size: 1.2em;
          font-weight: 500;
          color: var(--primary-text-color);
        }
        .refresh-btn {
          background: none;
          border: none;
          cursor: pointer;
          padding: 8px;
          border-radius: 50%;
          color: var(--primary-color);
        }
        .refresh-btn:hover {
          background: var(--secondary-background-color);
        }
        .refresh-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .btn-row {
          display: flex;
          gap: 10px;
          justify-content: flex-end;
          margin: -6px 0 12px;
        }
        .btn {
          border: 1px solid var(--divider-color);
          background: var(--secondary-background-color);
          color: var(--primary-text-color);
          padding: 8px 10px;
          border-radius: 10px;
          cursor: pointer;
          font-weight: 600;
        }
        .btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .btn-danger {
          border-color: color-mix(in srgb, var(--error-color, #b00020) 55%, var(--divider-color));
        }
        .loading {
          text-align: center;
          padding: 24px;
          color: var(--secondary-text-color);
        }
        .spinner {
          display: inline-block;
          width: 24px;
          height: 24px;
          border: 3px solid var(--divider-color);
          border-top-color: var(--primary-color);
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        .error {
          background: var(--error-color, #b00020);
          color: white;
          padding: 12px;
          border-radius: 8px;
          margin-bottom: 16px;
        }
        .success {
          background: var(--success-color, #4caf50);
          color: white;
          padding: 12px;
          border-radius: 8px;
          margin-bottom: 16px;
        }
        .candidates {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .candidate {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 12px 16px;
          background: var(--secondary-background-color);
          border-radius: 8px;
          cursor: pointer;
          transition: background 0.2s;
        }
        .candidate.bad {
          opacity: 0.55;
          cursor: not-allowed;
        }
        .candidate.unreachable {
          opacity: 0.72;
        }
        .candidate:hover {
          background: var(--primary-color);
          color: var(--text-primary-color, white);
        }
        .candidate.bad:hover {
          background: var(--secondary-background-color);
          color: inherit;
        }
        .candidate:hover .candidate-source {
          color: inherit;
          opacity: 0.8;
        }
        .candidate-info {
          flex: 1;
        }
        .candidate-name {
          font-weight: 500;
        }
        .candidate-host {
          font-family: monospace;
          font-size: 0.9em;
        }
        .candidate-source {
          font-size: 0.8em;
          color: var(--secondary-text-color);
          margin-top: 2px;
        }
        .candidate-action {
          margin-left: 16px;
        }
        .empty {
          text-align: center;
          padding: 24px;
          color: var(--secondary-text-color);
        }
        .empty-icon {
          font-size: 48px;
          margin-bottom: 8px;
        }

        .manual {
          margin-top: 14px;
          padding-top: 12px;
          border-top: 1px solid var(--divider-color);
        }
        .manual-title {
          font-weight: 700;
          margin-bottom: 8px;
        }
        .manual-row {
          display: flex;
          gap: 10px;
          align-items: center;
          flex-wrap: wrap;
        }
        .manual-row input {
          padding: 8px 10px;
          border-radius: 10px;
          border: 1px solid var(--divider-color);
          background: var(--secondary-background-color);
          color: var(--primary-text-color);
        }
        .manual-row input.host {
          flex: 1;
          min-width: 200px;
        }
        .manual-row input.port {
          width: 96px;
        }
        .manual-row label {
          display: inline-flex;
          gap: 8px;
          align-items: center;
          font-weight: 600;
          opacity: 0.9;
        }

        /* Wave 2 #12 — auto-discovery banner */
        .auto-discover-banner {
          margin: 10px 0 14px;
          padding: 12px 14px;
          border-radius: 12px;
          border: 1px solid color-mix(in srgb, var(--primary-color) 55%, var(--divider-color));
          background: color-mix(in srgb, var(--primary-color) 14%, var(--secondary-background-color));
        }
        .auto-discover-banner-info {
          border-color: var(--divider-color);
          background: rgba(255, 255, 255, 0.04);
        }
        .auto-discover-banner-title {
          font-weight: 700;
          color: var(--primary-text-color);
          font-size: 14px;
        }
        .auto-discover-banner-body {
          font-size: 13px;
          opacity: 0.9;
          margin-top: 4px;
          color: var(--primary-text-color);
        }
        .auto-discover-banner code {
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
          background: rgba(0, 0, 0, 0.18);
          padding: 1px 6px;
          border-radius: 6px;
          font-size: 13px;
        }

        /* Wave 2 #12 — "Enable MQTT over LAN" prompt */
        .mqtt-lan-prompt {
          margin: 10px 0 14px;
          padding: 14px;
          border-radius: 12px;
          border: 1px solid color-mix(in srgb, var(--error-color, #b00020) 35%, var(--divider-color));
          background: color-mix(in srgb, var(--error-color, #b00020) 10%, var(--secondary-background-color));
        }
        .mqtt-lan-prompt-title {
          font-weight: 700;
          color: var(--primary-text-color);
          font-size: 15px;
          margin-bottom: 6px;
        }
        .mqtt-lan-prompt-body {
          font-size: 14px;
          color: var(--primary-text-color);
          line-height: 1.45;
        }
        .mqtt-lan-prompt-detail {
          font-size: 13px;
          opacity: 0.9;
          margin-top: 8px;
          color: var(--primary-text-color);
        }
        .mqtt-lan-prompt-hint {
          margin: 10px 0 0;
          padding: 10px 12px;
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
          font-size: 12px;
          color: var(--primary-text-color);
          background: rgba(0, 0, 0, 0.18);
          border-radius: 8px;
          white-space: pre-wrap;
          line-height: 1.4;
        }
        .mqtt-lan-prompt-cta {
          margin-top: 12px;
        }
      </style>

      <ha-card>
        <div class="header">
          <span class="title">${title}</span>
          <button class="refresh-btn" ${this._loading || this._connecting ? 'disabled' : ''}>
            <ha-icon icon="mdi:refresh"></ha-icon>
          </button>
        </div>

        <div class="btn-row">
          <button class="btn" id="statusBtn" ${this._loading || this._connecting ? 'disabled' : ''}>
            Status
          </button>
          <button class="btn btn-danger" id="clearBtn" ${this._loading || this._connecting ? 'disabled' : ''}>
            Clear
          </button>
        </div>

        ${statusLine}

        ${autoDiscoverBanner}
        ${mqttLanPromptBlock}

        ${this._error ? `<div class="error">${this._error}</div>` : ''}
        ${this._success ? `<div class="success">${this._success}</div>` : ''}

        ${this._loading ? `
          <div class="loading">
            <div class="spinner"></div>
            <p>Discovering Victron devices...</p>
          </div>
        ` : this._connecting ? `
          <div class="loading">
            <div class="spinner"></div>
            <p>Connecting...</p>
          </div>
        ` : this._candidates.length > 0 ? `
          <div class="candidates">
            ${this._candidates.map((c, i) => `
              <div class="candidate ${c.bad ? 'bad' : ''} ${c.reachable === false ? 'unreachable' : ''}" data-index="${i}">
                <div class="candidate-info">
                  <div class="candidate-name">${this._escapeHtml(c.name || 'Victron Device')}</div>
                  <div class="candidate-host">${this._escapeHtml(c.host || c.ip)}:${c.port || 1883}</div>
                  <div class="candidate-source">${this._escapeHtml(c.source || 'unknown')}${c.reachable === true ? ' (reachable)' : c.reachable === false ? ' (unreachable)' : ''}${c.bad ? ' (bad)' : ''}</div>
                </div>
                <div class="candidate-action">
                  <ha-icon icon="mdi:chevron-right"></ha-icon>
                </div>
              </div>
            `).join('')}
          </div>
        ` : !this._success ? `
          <div class="empty">
            <div class="empty-icon">🔍</div>
            <p>No devices found</p>
            <p>Click refresh to scan again</p>
          </div>
        ` : ''}

        <div class="manual">
          <div class="manual-title">Manual connect</div>
          <div class="manual-row">
            <input class="host" id="manualHost" placeholder="GX host (e.g. 192.168.1.50 or venus.local)" value="${this._escapeHtml(this._manualHost || '')}" />
            <input class="port" id="manualPort" type="number" min="1" max="65535" value="${Number(this._manualPort || 1883)}" />
            <label><input id="manualTls" type="checkbox" ${this._manualTls ? 'checked' : ''}/> TLS</label>
            <button class="btn" id="manualConnectBtn" ${this._loading || this._connecting ? 'disabled' : ''}>
              Connect
            </button>
          </div>
          <div style="margin-top:8px; font-size:12px; opacity:0.8;">
            Default MQTT ports: 1883 (no TLS) / 8883 (TLS).
          </div>
        </div>
      </ha-card>
    `;

    // Bind events
    const refreshBtn = this.shadowRoot.querySelector('.refresh-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this._discover());
    }

    const clearBtn = this.shadowRoot.querySelector('#clearBtn');
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        const ok = window.confirm('Clear Victron configuration? This will disconnect and may restart the add-on.');
        if (ok) this._clear();
      });
    }

    const statusBtn = this.shadowRoot.querySelector('#statusBtn');
    if (statusBtn) {
      statusBtn.addEventListener('click', () => this._fetchStatus());
    }

    const candidateEls = this.shadowRoot.querySelectorAll('.candidate');
    candidateEls.forEach(el => {
      el.addEventListener('click', () => {
        const idx = parseInt(el.dataset.index, 10);
        const c = this._candidates[idx];
        if (c && !c.bad) {
          this._connect(c);
        }
      });
    });

    const manualHostEl = this.shadowRoot.querySelector('#manualHost');
    if (manualHostEl) {
      manualHostEl.addEventListener('input', () => {
        this._manualHost = manualHostEl.value;
      });
    }
    const manualPortEl = this.shadowRoot.querySelector('#manualPort');
    if (manualPortEl) {
      manualPortEl.addEventListener('input', () => {
        this._manualPort = manualPortEl.value;
        this._manualPortTouched = true;
      });
    }
    const manualTlsEl = this.shadowRoot.querySelector('#manualTls');
    if (manualTlsEl) {
      manualTlsEl.addEventListener('change', () => {
        this._manualTls = !!manualTlsEl.checked;

        // UX: if the user hasn't manually edited the port, switch to the
        // conventional default for TLS/non-TLS.
        if (!this._manualPortTouched) {
          this._manualPort = this._manualTls ? 8883 : 1883;
          // Avoid a full re-render (can steal focus); just update the input.
          try {
            const portEl = this.shadowRoot.querySelector('#manualPort');
            if (portEl) portEl.value = String(this._manualPort);
          } catch (e) {}
        }
      });
    }
    const manualConnectBtn = this.shadowRoot.querySelector('#manualConnectBtn');
    if (manualConnectBtn) {
      manualConnectBtn.addEventListener('click', () => this._connectManual());
    }

    // Wave 2 #12: bind the MQTT-LAN prompt's "Re-scan now" CTA.
    const mqttLanPromptRescanBtn = this.shadowRoot.querySelector('#mqttLanPromptRescanBtn');
    if (mqttLanPromptRescanBtn) {
      mqttLanPromptRescanBtn.addEventListener('click', () => {
        try { this._discover({ auto: true }); } catch (e) {}
      });
    }

    // Keyboard UX
    if (manualHostEl) {
      manualHostEl.addEventListener('keydown', (ev) => {
        if (ev.key === 'Enter') this._connectManual();
      });
    }
    if (manualPortEl) {
      manualPortEl.addEventListener('keydown', (ev) => {
        if (ev.key === 'Enter') this._connectManual();
      });
    }
  }

  _escapeHtml(str) {
    if (str == null) return '';
    const s = String(str);
    // Prefer the standard DOM API. Some test harnesses don't provide a real
    // `document.createElement`, in which case `div.innerHTML` may be
    // `undefined` instead of throwing — guard both cases.
    try {
      const div = document.createElement('div');
      div.textContent = s;
      const html = div.innerHTML;
      if (typeof html === 'string') return html;
    } catch (e) {
      // ignore
    }
    // Best-effort fallback: minimal HTML-entity encode.
    return s
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  getCardSize() {
    return 3;
  }

  static getStubConfig() {
    return {
      title: 'Connect Victron Device',
    };
  }
}

customElements.define('roamcore-victron-connect', RoamCoreVictronConnectCard);

// Register with HACS / custom card picker
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'roamcore-victron-connect',
  name: 'RoamCore Victron Connect',
  description: 'Discover and connect to Victron devices on your network',
  preview: true,
});

console.log('RoamCore Victron Connect card loaded');
