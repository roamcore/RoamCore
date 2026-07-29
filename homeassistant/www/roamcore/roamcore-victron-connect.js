/**
 * RoamCore Victron Pairing Wizard (polished, foolproof)
 *
 * Multi-step wizard that turns "discover + connect" into a guided onboarding
 * flow for a non-technical user.
 *
 *  Step 1 — Intro:           "what you'll need" + start CTA
 *  Step 2 — Discover/Manual: scan LAN for GX, or enter IP manually
 *  Step 3 — Connecting:      live status messages while the add-on applies
 *  Step 4 — Success:         "what changed" + one-click jump to Power page
 *
 * Each step has a working "Back" affordance that preserves user input.
 * All failure paths offer plain-English next actions.
 *
 * Usage in lovelace (backwards compatible with the existing card slot):
 *   type: custom:roamcore-victron-connect
 *   title: Pair Victron
 *
 * HACS-friendly: shipped as a single file, no build step.
 */

const RoamCoreVictronWizard_STEPS = ['intro', 'discover', 'connecting', 'success'];

const RoamCoreVictronWizard_COPY = {
  intro: {
    eyebrow: 'Power · Pair Victron',
    title: "Let's connect your Victron system",
    lead:
      "If you have a Victron Cerbo or GX on the same network as RoamCore, " +
      'this wizard finds it and gets the data flowing to your Power page. ' +
      'Takes about a minute.',
    needHeader: "What you'll need",
    needs: [
      'Your GX device powered on and on the same Wi-Fi as RoamCore.',
      "About 60 seconds — RoamCore will do the rest.",
      'If discovery cannot find it, you can also type the IP address by hand.',
    ],
    startLabel: 'Get started',
    skipLabel: 'Not now — take me to Power',
  },
  discover: {
    eyebrow: 'Step 2 of 4 · Find your GX',
    title: 'Looking for your Victron GX…',
    lead:
      'RoamCore is scanning your network for Victron devices. ' +
      'If nothing shows up in a few seconds, you can re-scan or type an IP address.',
    scanningLabel: 'Scanning…',
    noneFoundTitle: "Couldn't find a Victron device",
    noneFoundLead:
      "That doesn't always mean something is wrong. Try one of these:",
    recoveryOptions: [
      {
        id: 'rescan',
        label: 'Scan again',
        detail: 'Sometimes devices show up after a second scan.',
      },
      {
        id: 'manual',
        label: 'Type the IP address',
        detail:
          'Look in your GX Remote Console (Settings → General → "IP address"). ' +
          'It usually starts with 192.168.',
      },
      {
        id: 'help',
        label: 'Check the basics',
        detail:
          'Is the GX powered on and connected to the same Wi-Fi network as ' +
          'RoamCore? On most home setups, both devices share the same router.',
      },
    ],
    manualLabel: 'Type the IP address',
    manualHostPlaceholder: 'GX IP address (e.g. 192.168.1.50 or venus.local)',
    manualHelp:
      "Don't know the IP? Open the GX's Remote Console on a phone or laptop " +
      'and look under Settings → General → IP address.',
    backLabel: 'Back',
    manualConnectLabel: 'Connect',
  },
  connecting: {
    eyebrow: 'Step 3 of 4 · Connecting',
    title: 'Setting up Victron…',
    lead: 'RoamCore is talking to your GX and applying the configuration.',
    steps: [
      { id: 'save', label: 'Saving your selection' },
      { id: 'restart', label: 'Restarting the Victron add-on' },
      { id: 'verify', label: 'Verifying the data is flowing' },
    ],
    slowHelp:
      'Taking longer than usual? You can safely close this card and come back — ' +
      'the add-on is still working in the background.',
  },
  success: {
    eyebrow: 'Step 4 of 4 · Done',
    title: "You're connected",
    lead: 'Victron is now feeding live data into your Power page.',
    summaryHeader: "Here's what changed",
    nextSteps: [
      'Your battery, solar, shore, and AC readings are live on the Power page.',
      'If you ever change your GX IP, run this wizard again to point at the new one.',
    ],
    powerCta: 'Go to Power',
    powerCtaHint: 'See your live Victron numbers',
    doneCta: 'Done',
  },
};

const RoamCoreVictronWizard_ERRORS = {
  discovery_timeout: {
    title: 'The scan timed out',
    body:
      'RoamCore could not finish scanning before the network stopped responding. ' +
      'This usually clears up with a second try, or by typing the IP by hand.',
    next: 'Tap Scan again, or type the IP address.',
  },
  discovery_empty: {
    title: "Couldn't find a Victron device",
    body:
      'Nothing on your network is currently advertising itself as a Victron GX. ' +
      'Most of the time this is one of three things: the GX is off, it is on a ' +
      'different Wi-Fi network, or its MQTT-over-LAN setting is disabled.',
    next: 'Check the GX is on, on the same Wi-Fi, then tap Scan again.',
  },
  discovery_network: {
    title: 'We could not reach the add-on',
    body:
      "RoamCore's Victron add-on did not answer. It may be restarting after " +
      'a previous step, or the add-on is not installed.',
    next: 'Wait 10 seconds, then tap Scan again.',
  },
  connect_timeout: {
    title: 'The connection timed out',
    body:
      'RoamCore sent the configuration but did not hear back in time. ' +
      'The add-on is usually still applying it in the background.',
    next: 'Wait 15 seconds, then check Status. If still empty, tap Back and try again.',
  },
  connect_invalid_host: {
    title: 'That address does not look right',
    body:
      'RoamCore expects an IP address (something like 192.168.1.50) or a ' +
      'hostname (like venus.local). The one you typed does not parse.',
    next: 'Check the address and try again.',
  },
  connect_unreachable: {
    title: "We can't reach that device",
    body:
      'RoamCore saved the address but cannot open an MQTT connection to it. ' +
      'It is usually one of: the IP is wrong, the GX MQTT-over-LAN is disabled, ' +
      'or the device is on a different network than RoamCore.',
    next: 'Double-check the IP and the GX is on the same Wi-Fi, then try again.',
  },
  connect_persist: {
    title: 'Could not save the configuration',
    body:
      'RoamCore could not write the new GX address into the add-on. ' +
      'It may not have permission to update its own settings right now.',
    next: 'Wait a moment and try again. If it keeps happening, restart the add-on.',
  },
  connect_unknown: {
    title: 'Something went sideways',
    body: 'RoamCore got an unexpected response from the add-on.',
    next: 'Try again. If the problem keeps happening, check the add-on logs.',
  },
  generic: {
    title: 'Something did not work',
    body: 'RoamCore hit an unexpected error.',
    next: 'Try the step again. If it keeps happening, restart the add-on.',
  },
};

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
    this._errorKey = null;
    this._errorNext = null;
    this._success = null;
    this._status = null;
    this._statusPollTimer = null;
    this._statusPollInFlight = false;
    this._manualHost = '';
    this._manualPort = 1883;
    this._manualTls = false;
    this._manualPortTouched = false;

    // Wizard state machine.
    // 'intro' | 'discover' | 'connecting' | 'success'
    this._step = 'intro';

    // We keep a small history so "Back" goes to the right step.
    this._history = [];

    // What we remember across steps (never lose user input on back).
    this._saved = {
      manualHost: '',
      manualPort: 1883,
      manualTls: false,
      candidates: [],
      selectedCandidate: null,
      successSnapshot: null,
    };

    // Connecting-step sub-state.
    this._connectingSteps = {
      save: 'pending',
      restart: 'pending',
      verify: 'pending',
    };
    this._connectingPollTimer = null;
  }

  connectedCallback() {
    // Keep status reasonably fresh without requiring manual clicks.
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
    if (this._connectingPollTimer) {
      clearInterval(this._connectingPollTimer);
      this._connectingPollTimer = null;
    }
  }

  setConfig(config) {
    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    // Trigger a status refresh so the wizard can show a "you're already paired"
    // success path on first paint for users who completed the wizard before.
    try {
      if (!this._didInitialStatus) {
        this._didInitialStatus = true;
        this._fetchStatus().then(() => {
          if (this._step === 'intro' && this._isAlreadyPaired()) {
            // Keep the user on intro but pre-populate the saved snapshot so
            // the success card is one tap away.
          }
        });
      }
    } catch (e) {}
  }

  // ---------------------------------------------------------------------------
  // Status detection: "are we already paired?"
  // ---------------------------------------------------------------------------
  _isAlreadyPaired() {
    if (!this._status) return false;
    const vic = this._status && this._status.victron ? this._status.victron : null;
    if (!vic) return false;
    if (vic.connected === true && vic.did_full_publish === true) return true;
    return false;
  }

  // ---------------------------------------------------------------------------
  // Step navigation
  // ---------------------------------------------------------------------------
  _goto(step, options) {
    options = options || {};
    if (step === this._step) return;
    if (options.record !== false) {
      this._history.push(this._step);
    }
    this._step = step;
    this._error = null;
    this._errorKey = null;
    this._errorNext = null;
    this._render();

    // Side-effects per step entry.
    if (step === 'discover' && this._saved.candidates.length === 0 && !this._loading) {
      this._discover();
    }
    if (step === 'success' && this._saved.successSnapshot) {
      // We may already have a snapshot — start light status polling for the
      // "live numbers" line.
      try { this._fetchStatus(); } catch (e) {}
    }
  }

  _back() {
    const prev = this._history.pop();
    if (!prev) {
      // Nowhere to go; stay where we are.
      return;
    }
    this._step = prev;
    this._error = null;
    this._errorKey = null;
    this._errorNext = null;
    this._render();
  }

  _reset() {
    this._step = 'intro';
    this._history = [];
    this._error = null;
    this._errorKey = null;
    this._errorNext = null;
    this._connecting = false;
    this._loading = false;
    this._candidates = (this._saved.candidates || []).slice();
    this._connectingSteps = { save: 'pending', restart: 'pending', verify: 'pending' };
    if (this._connectingPollTimer) {
      clearInterval(this._connectingPollTimer);
      this._connectingPollTimer = null;
    }
    this._render();
  }

  // ---------------------------------------------------------------------------
  // HTTP plumbing (unchanged from base card)
  // ---------------------------------------------------------------------------
  _getApiBase() {
    if (this._config.api_base) return this._config.api_base;

    try {
      const panels = this._hass && this._hass.panels ? this._hass.panels : {};
      for (const key of Object.keys(panels)) {
        const p = panels[key];
        const title = String((p && p.title) || (p && p.config && p.config.title) || '').toLowerCase();
        const urlPath = String((p && p.url_path) || '').toLowerCase();
        const ingress = p && p.config && p.config.ingress;
        const isVictron = title.includes('victron') || title.includes('venus') || urlPath.includes('victron');
        if (isVictron && ingress) {
          return `/api/hassio_ingress/${ingress}`;
        }
      }
    } catch (e) {
      // ignore
    }

    return '/api/hassio_ingress/roamcore_victron_auto_dev';
  }

  async _fetchStatus() {
    if (this._statusPollInFlight) return;
    try {
      this._statusPollInFlight = true;
      const base = this._getApiBase();
      const ctl = new AbortController();
      const t = setTimeout(() => ctl.abort(), 4000);
      const resp = await fetch(`${base}/api/v1/victron/status`, {
        credentials: 'same-origin',
        signal: ctl.signal,
      }).finally(() => clearTimeout(t));
      if (!resp.ok) throw new Error(`status ${resp.status}`);
      const data = await resp.json().catch(() => ({}));
      this._status = data && data.status ? data.status : data;
      this._render();
    } catch (e) {
      // ignore — status is best-effort
    } finally {
      this._statusPollInFlight = false;
    }
  }

  // ---------------------------------------------------------------------------
  // Discovery
  // ---------------------------------------------------------------------------
  async _discover() {
    this._loading = true;
    this._error = null;
    this._errorKey = null;
    this._errorNext = null;
    this._render();

    try {
      const base = this._getApiBase();
      const ctl = new AbortController();
      const t = setTimeout(() => ctl.abort(), 8000);
      const resp = await fetch(`${base}/api/v1/victron/discover`, {
        credentials: 'same-origin',
        signal: ctl.signal,
      }).finally(() => clearTimeout(t));

      if (!resp.ok) {
        if (resp.status === 404 || resp.status === 502 || resp.status === 503) {
          throw this._wizError('discovery_network');
        }
        throw new Error(`HTTP ${resp.status}`);
      }

      const data = await resp.json();
      let candidates = (data && data.candidates) || [];

      try {
        candidates = candidates.slice().sort((a, b) => {
          const ar = a && a.reachable === true;
          const br = b && b.reachable === true;
          if (ar !== br) return ar ? -1 : 1;
          const ab = a && a.bad === true;
          const bb = b && b.bad === true;
          if (ab !== bb) return ab ? 1 : -1;
          return 0;
        });
      } catch (e) {}

      this._candidates = candidates;
      this._saved.candidates = candidates.slice();
      // No error here — empty list is its own friendly state.
    } catch (err) {
      if (err && err.__wiz) {
        this._applyWizError(err);
      } else if (err && (err.name === 'AbortError' || String(err.message || '').includes('aborted'))) {
        this._applyWizError(this._wizError('discovery_timeout'));
      } else {
        this._applyWizError(this._wizError('generic', err.message));
      }
      this._candidates = [];
    } finally {
      this._loading = false;
      this._render();
    }
  }

  // ---------------------------------------------------------------------------
  // Connect
  // ---------------------------------------------------------------------------
  _wizError(key, detail) {
    const e = new Error(key);
    e.__wiz = true;
    e.__wizKey = key;
    e.__wizDetail = detail || '';
    return e;
  }

  _applyWizError(err) {
    const meta = RoamCoreVictronWizard_ERRORS[err.__wizKey || 'generic'] || RoamCoreVictronWizard_ERRORS.generic;
    this._error = meta.body + (err.__wizDetail ? ` (${err.__wizDetail})` : '');
    this._errorKey = err.__wizKey || 'generic';
    this._errorNext = meta.next;
  }

  async _connect(candidate) {
    if (!candidate) return;
    this._saved.selectedCandidate = candidate;
    this._goto('connecting');
    this._connectingSteps = {
      save: 'active',
      restart: 'pending',
      verify: 'pending',
    };
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
        const apiErr = (errData && (errData.error || errData.detail)) || `HTTP ${resp.status}`;
        let key = 'connect_unknown';
        const detail = String(apiErr).toLowerCase();
        if (detail.includes('invalid') || detail.includes('host') || detail.includes('hostname')) key = 'connect_invalid_host';
        else if (detail.includes('timeout') || detail.includes('timed out')) key = 'connect_timeout';
        else if (detail.includes('unreachable') || detail.includes('refused') || detail.includes('reset')) key = 'connect_unreachable';
        else if (detail.includes('persist') || detail.includes('save') || detail.includes('supervisor')) key = 'connect_persist';
        throw this._wizError(key, String(apiErr));
      }

      const data = await resp.json().catch(() => ({}));
      this._connectingSteps = {
        save: 'done',
        restart: 'active',
        verify: 'pending',
      };
      this._render();

      // Poll the status endpoint so we can move save→restart→verify.
      // The add-on restarts asynchronously after the HTTP response.
      this._beginConnectingWatch();
    } catch (err) {
      if (err && err.__wiz) {
        this._applyWizError(err);
      } else if (err && (err.name === 'AbortError' || String(err.message || '').includes('aborted'))) {
        this._applyWizError(this._wizError('connect_timeout'));
      } else {
        this._applyWizError(this._wizError('generic', err.message));
      }
      // Land back on the discover step with the error visible.
      this._step = 'discover';
      this._render();
    }
  }

  _beginConnectingWatch() {
    if (this._connectingPollTimer) clearInterval(this._connectingPollTimer);
    let ticks = 0;
    const maxTicks = 30; // ~60s @ 2s
    const tick = async () => {
      ticks++;
      try {
        await this._fetchStatus();
      } catch (e) {}
      const st = this._status || null;
      const vic = st && st.victron ? st.victron : null;
      const cfg = st && st.config ? st.config : null;
      const inv = st && st.inventory ? st.inventory : null;

      if (cfg && cfg.valid === false) {
        // Config is invalid — bail out with a clear error.
        this._applyWizError(this._wizError('connect_persist', 'add-on reported invalid config'));
        this._step = 'discover';
        if (this._connectingPollTimer) {
          clearInterval(this._connectingPollTimer);
          this._connectingPollTimer = null;
        }
        this._render();
        return;
      }

      if (vic && vic.connected === true) {
        this._connectingSteps = {
          save: 'done',
          restart: 'done',
          verify: 'active',
        };
        this._render();
        // Move on once we see either a full snapshot or live device data.
        // Using `did_full_publish` first because it's the canonical "snapshot
        // ready" signal — `devices_count` can stay at 0 for an idle GX.
        const snapshotReady = vic.did_full_publish === true;
        const devicesPresent = inv && (inv.devices_count || 0) > 0;
        if (snapshotReady || devicesPresent) {
          this._finishSuccess();
          return;
        }
      }

      if (ticks >= maxTicks) {
        // We didn't observe a connection in time. Don't strand the user —
        // move them to a success-with-caveats state that explains what to do next.
        this._applyWizError(this._wizError('connect_timeout'));
        // Stay on connecting but show a "still working in background" message.
        this._render();
        if (this._connectingPollTimer) {
          clearInterval(this._connectingPollTimer);
          this._connectingPollTimer = null;
        }
      }
    };
    this._connectingPollTimer = setInterval(tick, 2000);
    // First tick fires immediately.
    try { tick(); } catch (e) {}
  }

  _finishSuccess() {
    if (this._connectingPollTimer) {
      clearInterval(this._connectingPollTimer);
      this._connectingPollTimer = null;
    }
    const inv = (this._status && this._status.inventory) || {};
    this._saved.successSnapshot = {
      devices: inv.devices_count || 0,
      topics: inv.topics_count || 0,
      connectedAt: Date.now(),
    };
    this._connectingSteps = { save: 'done', restart: 'done', verify: 'done' };
    this._goto('success');
  }

  async _connectManual() {
    const host = String(this._manualHost || '').trim();
    const port = parseInt(String(this._manualPort || '1883'), 10) || 1883;
    const use_tls = !!this._manualTls;
    if (!host) {
      this._applyWizError(this._wizError('connect_invalid_host', 'no host'));
      this._render();
      return;
    }
    this._saved.manualHost = host;
    this._saved.manualPort = port;
    this._saved.manualTls = use_tls;
    return this._connect({ host, port, use_tls, source: 'manual' });
  }

  // ---------------------------------------------------------------------------
  // Clear (advanced; from the discover step)
  // ---------------------------------------------------------------------------
  async _clear() {
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
        throw new Error(`HTTP ${resp.status}`);
      }
      // Reset wizard and re-fetch status.
      this._saved.candidates = [];
      this._saved.selectedCandidate = null;
      this._saved.successSnapshot = null;
      this._candidates = [];
      this._status = null;
      try { this._fetchStatus(); } catch (e) {}
      this._reset();
    } catch (e) {
      this._applyWizError(this._wizError('generic', e.message || 'clear failed'));
      this._render();
    }
  }

  // ---------------------------------------------------------------------------
  // Navigation helpers
  // ---------------------------------------------------------------------------
  _goToPower() {
    // Try the standard RoamCore internal page first; fall back to a custom
    // event that dashboards can hook into.
    try {
      const ev = new CustomEvent('roamcore-nav', {
        bubbles: true,
        composed: true,
        detail: { path: '/power', source: 'victron-wizard' },
      });
      this.dispatchEvent(ev);
    } catch (e) {}
    try {
      window.history && window.history.pushState({}, '', '/power');
      window.dispatchEvent(new PopStateEvent('popstate'));
    } catch (e) {}
  }

  // ---------------------------------------------------------------------------
  // Rendering
  // ---------------------------------------------------------------------------
  _render() {
    const title = this._config.title || 'Pair Victron';

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        ha-card { padding: 18px; }

        .stepper {
          display: flex;
          gap: 6px;
          margin-bottom: 14px;
        }
        .stepper-dot {
          flex: 1;
          height: 4px;
          border-radius: 2px;
          background: var(--divider-color);
          transition: background 0.25s ease;
        }
        .stepper-dot.active {
          background: var(--primary-color);
        }
        .stepper-dot.done {
          background: color-mix(in srgb, var(--primary-color) 65%, var(--divider-color));
        }

        .eyebrow {
          font-size: 12px;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          opacity: 0.7;
          margin-bottom: 6px;
        }
        h1 {
          font-size: 22px;
          line-height: 1.25;
          margin: 0 0 8px;
          color: var(--primary-text-color);
        }
        .lead {
          font-size: 14px;
          opacity: 0.85;
          margin: 0 0 18px;
          line-height: 1.5;
        }

        .card-section {
          margin-top: 10px;
          padding: 14px;
          border: 1px solid var(--divider-color);
          border-radius: 12px;
          background: var(--secondary-background-color, rgba(255,255,255,0.04));
        }
        .card-section h2 {
          font-size: 14px;
          margin: 0 0 8px;
          color: var(--primary-text-color);
        }
        .card-section ul {
          margin: 0;
          padding-left: 18px;
          color: var(--primary-text-color);
        }
        .card-section li {
          margin-bottom: 6px;
          font-size: 14px;
          line-height: 1.45;
        }

        .actions {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
          margin-top: 18px;
        }
        .btn {
          border: 1px solid var(--divider-color);
          background: var(--primary-color);
          color: var(--text-primary-color, #fff);
          padding: 10px 16px;
          border-radius: 10px;
          cursor: pointer;
          font-weight: 600;
          font-size: 14px;
        }
        .btn.secondary {
          background: var(--secondary-background-color);
          color: var(--primary-text-color);
        }
        .btn.ghost {
          background: transparent;
          color: var(--primary-text-color);
          border-color: transparent;
        }
        .btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .error {
          background: var(--error-color, #b00020);
          color: white;
          padding: 12px 14px;
          border-radius: 10px;
          margin: 12px 0 4px;
        }
        .error-title {
          font-weight: 700;
          margin-bottom: 4px;
        }
        .error-next {
          margin-top: 6px;
          font-size: 13px;
          opacity: 0.95;
        }
        .error-help {
          display: inline-block;
          margin-top: 8px;
          font-size: 13px;
          opacity: 0.95;
        }

        .success-banner {
          background: color-mix(in srgb, var(--success-color, #4caf50) 22%, transparent);
          border: 1px solid color-mix(in srgb, var(--success-color, #4caf50) 60%, var(--divider-color));
          padding: 14px;
          border-radius: 10px;
          margin: 12px 0;
        }
        .success-banner h2 {
          margin: 0 0 4px;
          font-size: 16px;
          color: var(--primary-text-color);
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
          padding: 12px 14px;
          background: var(--secondary-background-color);
          border-radius: 10px;
          cursor: pointer;
          transition: background 0.2s;
          border: 1px solid var(--divider-color);
        }
        .candidate.bad {
          opacity: 0.55;
          cursor: not-allowed;
        }
        .candidate:hover {
          border-color: var(--primary-color);
        }
        .candidate-info {
          flex: 1;
          min-width: 0;
        }
        .candidate-name {
          font-weight: 600;
          color: var(--primary-text-color);
        }
        .candidate-host {
          font-family: monospace;
          font-size: 12px;
          opacity: 0.85;
        }
        .candidate-source {
          font-size: 12px;
          color: var(--secondary-text-color);
          margin-top: 2px;
        }
        .candidate-action {
          margin-left: 12px;
        }

        .recovery-row {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
          margin-top: 10px;
        }

        .manual-row {
          display: flex;
          gap: 8px;
          align-items: center;
          flex-wrap: wrap;
          margin-top: 8px;
        }
        .manual-row input[type="text"] {
          flex: 1;
          min-width: 180px;
          padding: 9px 12px;
          border-radius: 10px;
          border: 1px solid var(--divider-color);
          background: var(--secondary-background-color);
          color: var(--primary-text-color);
          font-size: 14px;
        }
        .manual-row input[type="number"] {
          width: 92px;
          padding: 9px 12px;
          border-radius: 10px;
          border: 1px solid var(--divider-color);
          background: var(--secondary-background-color);
          color: var(--primary-text-color);
          font-size: 14px;
        }
        .manual-row label {
          display: inline-flex;
          gap: 6px;
          align-items: center;
          font-size: 13px;
          opacity: 0.9;
        }

        .progress-list {
          list-style: none;
          padding: 0;
          margin: 8px 0 0;
        }
        .progress-list li {
          display: flex;
          gap: 10px;
          align-items: center;
          padding: 8px 0;
          border-bottom: 1px solid var(--divider-color);
        }
        .progress-list li:last-child { border-bottom: none; }
        .progress-dot {
          width: 18px;
          height: 18px;
          border-radius: 50%;
          background: var(--divider-color);
          display: inline-flex;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          color: var(--text-primary-color, #fff);
        }
        .progress-dot.active {
          background: var(--primary-color);
          animation: pulse 1.4s ease-in-out infinite;
        }
        .progress-dot.done {
          background: var(--success-color, #4caf50);
        }
        @keyframes pulse {
          0%, 100% { opacity: 0.6; }
          50% { opacity: 1; }
        }
        .progress-label { flex: 1; }
        .progress-meta { font-size: 12px; opacity: 0.7; }

        .spinner {
          display: inline-block;
          width: 18px;
          height: 18px;
          border: 3px solid var(--divider-color);
          border-top-color: var(--primary-color);
          border-radius: 50%;
          animation: spin 1s linear infinite;
          vertical-align: middle;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        .meta-line {
          font-size: 12px;
          opacity: 0.75;
          margin-top: 14px;
        }

        .divider {
          height: 1px;
          background: var(--divider-color);
          margin: 16px 0;
        }

        .empty-state {
          padding: 14px;
          border: 1px dashed var(--divider-color);
          border-radius: 10px;
          margin-top: 8px;
        }
        .empty-state h3 {
          font-size: 15px;
          margin: 0 0 6px;
          color: var(--primary-text-color);
        }
        .empty-state p {
          margin: 0 0 8px;
          font-size: 13px;
          opacity: 0.85;
        }

        .help-toggle {
          background: none;
          border: none;
          color: var(--primary-color);
          cursor: pointer;
          padding: 4px 0;
          font-size: 13px;
        }
      </style>

      <ha-card>
        ${this._renderStepper()}

        ${this._renderStep(title)}
      </ha-card>
    `;

    this._bind();
  }

  _renderStepper() {
    const idx = RoamCoreVictronWizard_STEPS.indexOf(this._step);
    return `
      <div class="stepper" aria-label="Pair Victron progress">
        ${RoamCoreVictronWizard_STEPS.map((s, i) => {
          let cls = 'stepper-dot';
          if (i < idx) cls += ' done';
          else if (i === idx) cls += ' active';
          return `<div class="${cls}" title="${s}"></div>`;
        }).join('')}
      </div>
    `;
  }

  _renderStep(title) {
    const copy = RoamCoreVictronWizard_COPY[this._step] || RoamCoreVictronWizard_COPY.intro;
    const eyebrow = copy.eyebrow || '';

    let body = '';
    if (this._step === 'intro') body = this._renderIntro(copy);
    else if (this._step === 'discover') body = this._renderDiscover(copy);
    else if (this._step === 'connecting') body = this._renderConnecting(copy);
    else if (this._step === 'success') body = this._renderSuccess(copy);

    const errorBlock = this._renderError();

    return `
      <div class="eyebrow">${this._escapeHtml(eyy(eyebrow, title))}</div>
      <h1>${this._escapeHtml(copy.title)}</h1>
      <p class="lead">${this._escapeHtml(copy.lead || '')}</p>
      ${errorBlock}
      ${body}
    `;
  }

  _renderIntro(copy) {
    const paired = this._isAlreadyPaired();
    return `
      <div class="card-section">
        <h2>${this._escapeHtml(copy.needHeader)}</h2>
        <ul>
          ${copy.needs.map((n) => `<li>${this._escapeHtml(n)}</li>`).join('')}
        </ul>
      </div>

      ${paired ? `
        <div class="success-banner" style="margin-top: 14px;">
          <h2>Victron is already paired</h2>
          <div class="meta-line">You can re-run the wizard any time to point at a different device.</div>
        </div>
      ` : ''}

      <div class="actions">
        <button class="btn" id="startBtn">${this._escapeHtml(copy.startLabel)}</button>
        <button class="btn ghost" id="skipBtn">${this._escapeHtml(copy.skipLabel)}</button>
      </div>
    `;
  }

  _renderDiscover(copy) {
    const loading = this._loading;
    const cands = this._candidates || [];
    return `
      <div class="actions" style="margin-top: 0; margin-bottom: 10px;">
        <button class="btn secondary" id="backBtn">${this._escapeHtml(copy.backLabel)}</button>
        <button class="btn" id="rescanBtn" ${loading ? 'disabled' : ''}>
          ${loading ? '<span class="spinner"></span> ' : ''}${this._escapeHtml(copy.scanningLabel)}
        </button>
      </div>

      ${cands.length > 0 ? `
        <div class="card-section">
          <h2>Found ${cands.length} device${cands.length === 1 ? '' : 's'}</h2>
          <div class="candidates">
            ${cands.map((c, i) => `
              <div class="candidate ${c.bad ? 'bad' : ''}" data-index="${i}">
                <div class="candidate-info">
                  <div class="candidate-name">${this._escapeHtml(c.name || 'Victron device')}</div>
                  <div class="candidate-host">${this._escapeHtml(c.host || c.ip)}:${c.port || 1883}</div>
                  <div class="candidate-source">${this._escapeHtml(c.source || 'network')}
                    ${c.reachable === true ? ' · reachable' : c.reachable === false ? ' · not reachable yet' : ''}
                    ${c.bad ? ' · not working' : ''}
                  </div>
                </div>
                <div class="candidate-action">
                  <ha-icon icon="mdi:chevron-right"></ha-icon>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      ` : !loading ? `
        <div class="empty-state">
          <h3>${this._escapeHtml(copy.noneFoundTitle)}</h3>
          <p>${this._escapeHtml(copy.noneFoundLead)}</p>
          <div class="recovery-row">
            <button class="btn secondary" id="recoveryRescanBtn">${this._escapeHtml(copy.recoveryOptions[0].label)}</button>
            <button class="btn secondary" id="recoveryManualBtn">${this._escapeHtml(copy.recoveryOptions[1].label)}</button>
            <button class="btn ghost" id="recoveryHelpBtn">${this._escapeHtml(copy.recoveryOptions[2].label)}</button>
          </div>
          <div id="recoveryHelpDetail" class="meta-line" style="display:none; margin-top: 8px;">
            ${this._escapeHtml(copy.recoveryOptions[2].detail)}
          </div>
        </div>
      ` : `
        <div class="card-section" style="text-align: center; opacity: 0.85;">
          <span class="spinner"></span>
          <div style="margin-top: 8px;">${this._escapeHtml(copy.scanningLabel)}</div>
        </div>
      `}

      <div class="divider"></div>

      <div class="card-section">
        <h2>${this._escapeHtml(copy.manualLabel)}</h2>
        <div class="manual-row">
          <input id="manualHost" type="text"
            placeholder="${this._escapeHtml(copy.manualHostPlaceholder)}"
            value="${this._escapeHtml(this._manualHost || '')}" />
          <input id="manualPort" type="number" min="1" max="65535"
            value="${Number(this._manualPort || 1883)}" />
          <label><input id="manualTls" type="checkbox" ${this._manualTls ? 'checked' : ''}/> TLS</label>
          <button class="btn" id="manualConnectBtn">${this._escapeHtml(copy.manualConnectLabel)}</button>
        </div>
        <div class="meta-line">${this._escapeHtml(copy.manualHelp)}</div>
      </div>
    `;
  }

  _renderConnecting(copy) {
    return `
      <div class="card-section">
        <ul class="progress-list" aria-live="polite">
          ${copy.steps.map((s) => {
            const state = this._connectingSteps[s.id] || 'pending';
            const glyph = state === 'done' ? '✓' : state === 'active' ? '' : '';
            const cls = state === 'done' ? 'done' : state === 'active' ? 'active' : '';
            return `
              <li>
                <span class="progress-dot ${cls}">${glyph}</span>
                <span class="progress-label">${this._escapeHtml(s.label)}</span>
                <span class="progress-meta">${this._escapeHtml(state)}</span>
              </li>
            `;
          }).join('')}
        </ul>
        <div class="meta-line">${this._escapeHtml(copy.slowHelp)}</div>
      </div>

      <div class="actions">
        <button class="btn ghost" id="cancelBtn">Cancel</button>
      </div>
    `;
  }

  _renderSuccess(copy) {
    const snap = this._saved.successSnapshot || {};
    const devices = snap.devices || 0;
    const topics = snap.topics || 0;
    return `
      <div class="success-banner">
        <h2>${this._escapeHtml(copy.title)}</h2>
        <div>${this._escapeHtml(copy.lead)}</div>
      </div>

      <div class="card-section">
        <h2>${this._escapeHtml(copy.summaryHeader)}</h2>
        <ul>
          ${devices > 0
            ? `<li>${this._escapeHtml(`Found ${devices} Victron device${devices === 1 ? '' : 's'}`)}.</li>`
            : '<li>Victron is connected — initial data is arriving.</li>'}
          ${topics > 0
            ? `<li>${this._escapeHtml(`${topics} live sensor${topics === 1 ? '' : 's'} flowing to the Power page`)}.</li>`
            : ''}
          ${copy.nextSteps.map((n) => `<li>${this._escapeHtml(n)}</li>`).join('')}
        </ul>
      </div>

      <div class="actions">
        <button class="btn" id="powerCta">${this._escapeHtml(copy.powerCta)}</button>
        <button class="btn secondary" id="doneBtn">${this._escapeHtml(copy.doneCta)}</button>
      </div>
    `;
  }

  _renderError() {
    if (!this._error) return '';
    const meta = RoamCoreVictronWizard_ERRORS[this._errorKey] || RoamCoreVictronWizard_ERRORS.generic;
    const next = this._errorNext || meta.next;
    return `
      <div class="error" role="alert">
        <div class="error-title">${this._escapeHtml(meta.title)}</div>
        <div>${this._escapeHtml(this._error)}</div>
        <div class="error-next"><strong>What to try:</strong> ${this._escapeHtml(next)}</div>
      </div>
    `;
  }

  // ---------------------------------------------------------------------------
  // Event binding
  // ---------------------------------------------------------------------------
  _bind() {
    const root = this.shadowRoot;
    if (!root) return;

    const click = (id, fn) => {
      const el = root.querySelector('#' + id);
      if (el) el.addEventListener('click', fn);
    };

    if (this._step === 'intro') {
      click('startBtn', () => this._goto('discover'));
      click('skipBtn', () => this._goToPower());
    } else if (this._step === 'discover') {
      click('backBtn', () => this._back());
      click('rescanBtn', () => this._discover());
      click('recoveryRescanBtn', () => this._discover());
      click('recoveryManualBtn', () => {
        const el = root.querySelector('#manualHost');
        if (el) el.focus();
      });
      click('recoveryHelpBtn', () => {
        const el = root.querySelector('#recoveryHelpDetail');
        if (el) el.style.display = el.style.display === 'none' ? 'block' : 'none';
      });

      root.querySelectorAll('.candidate').forEach((el) => {
        el.addEventListener('click', () => {
          const idx = parseInt(el.dataset.index, 10);
          const c = this._candidates[idx];
          if (c && !c.bad) this._connect(c);
        });
      });

      const hostEl = root.querySelector('#manualHost');
      if (hostEl) {
        hostEl.addEventListener('input', () => {
          this._manualHost = hostEl.value;
        });
        hostEl.addEventListener('keydown', (ev) => {
          if (ev.key === 'Enter') this._connectManual();
        });
      }
      const portEl = root.querySelector('#manualPort');
      if (portEl) {
        portEl.addEventListener('input', () => {
          this._manualPort = portEl.value;
          this._manualPortTouched = true;
        });
        portEl.addEventListener('keydown', (ev) => {
          if (ev.key === 'Enter') this._connectManual();
        });
      }
      const tlsEl = root.querySelector('#manualTls');
      if (tlsEl) {
        tlsEl.addEventListener('change', () => {
          this._manualTls = !!tlsEl.checked;
          if (!this._manualPortTouched) {
            this._manualPort = this._manualTls ? 8883 : 1883;
            try {
              const portEl2 = root.querySelector('#manualPort');
              if (portEl2) portEl2.value = String(this._manualPort);
            } catch (e) {}
          }
        });
      }
      click('manualConnectBtn', () => this._connectManual());
    } else if (this._step === 'connecting') {
      click('cancelBtn', () => {
        if (this._connectingPollTimer) {
          clearInterval(this._connectingPollTimer);
          this._connectingPollTimer = null;
        }
        this._back();
      });
    } else if (this._step === 'success') {
      click('powerCta', () => this._goToPower());
      click('doneBtn', () => this._reset());
    }
  }

  _escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str == null ? '' : String(str);
    return div.innerHTML;
  }

  getCardSize() {
    return 4;
  }

  static getStubConfig() {
    return {
      title: 'Pair Victron',
    };
  }
}

// Local helper that prefers an explicit eyebrow but falls back to a card title.
function eyy(eyebrow, fallback) {
  return eyebrow || fallback || '';
}

customElements.define('roamcore-victron-connect', RoamCoreVictronConnectCard);

// Register with HACS / custom card picker
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'roamcore-victron-connect',
  name: 'RoamCore Victron Pairing Wizard',
  description:
    'A guided wizard to pair a Victron Cerbo/GX with RoamCore — discover, ' +
    'connect, and verify, with plain-English recovery at every step.',
  preview: true,
});

console.log('RoamCore Victron Pairing Wizard loaded');