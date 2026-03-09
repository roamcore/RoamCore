/**
 * RoamCore Victron Connect Card
 * 
 * A Lovelace custom card that discovers Victron devices on the network
 * and allows the user to select one to connect.
 * 
 * Usage in lovelace:
 *   type: custom:roamcore-victron-connect
 *   title: Connect Victron Device
 */

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
  }

  setConfig(config) {
    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    // Auto-discover on first hass set if we have no candidates yet
    if (this._candidates.length === 0 && !this._loading) {
      this._discover();
    }
  }

  _getApiBase() {
    // Add-on ingress URL pattern: /api/hassio_ingress/<ingress_token>/
    // For now, assume the add-on is accessible via its ingress path.
    // In production, this would be derived from the add-on's ingress_url.
    // Fallback: try localhost for development.
    return this._config.api_base || '/api/hassio_ingress/roamcore_victron_auto_dev';
  }

  async _discover() {
    this._loading = true;
    this._error = null;
    this._render();

    try {
      const base = this._getApiBase();
      const resp = await fetch(`${base}/api/v1/victron/discover`, {
        credentials: 'same-origin',
      });
      
      if (!resp.ok) {
        throw new Error(`Discovery failed: ${resp.status} ${resp.statusText}`);
      }
      
      const data = await resp.json();
      this._candidates = data.candidates || [];
      
      if (this._candidates.length === 0) {
        this._error = 'No Victron devices found on the network. Make sure your GX device is powered on and connected.';
      }
    } catch (err) {
      this._error = `Discovery error: ${err.message}`;
      this._candidates = [];
    } finally {
      this._loading = false;
      this._render();
    }
  }

  async _connect(candidate) {
    this._connecting = true;
    this._error = null;
    this._success = null;
    this._render();

    try {
      const base = this._getApiBase();
      const resp = await fetch(`${base}/api/v1/victron/connect`, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host: candidate.host || candidate.ip,
          port: candidate.port || 1883,
          use_tls: candidate.use_tls || false,
          portal_id: candidate.portal_id || null,
        }),
      });

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.error || `Connect failed: ${resp.status}`);
      }

      const data = await resp.json();
      this._success = data.message || 'Connected! The add-on is restarting to apply the configuration.';
      
      // Clear candidates after successful connect
      this._candidates = [];
    } catch (err) {
      this._error = `Connection error: ${err.message}`;
    } finally {
      this._connecting = false;
      this._render();
    }
  }

  _render() {
    const title = this._config.title || 'Connect Victron Device';

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
        .candidate:hover {
          background: var(--primary-color);
          color: var(--text-primary-color, white);
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
      </style>

      <ha-card>
        <div class="header">
          <span class="title">${title}</span>
          <button class="refresh-btn" ${this._loading || this._connecting ? 'disabled' : ''}>
            <ha-icon icon="mdi:refresh"></ha-icon>
          </button>
        </div>

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
              <div class="candidate" data-index="${i}">
                <div class="candidate-info">
                  <div class="candidate-name">${this._escapeHtml(c.name || 'Victron Device')}</div>
                  <div class="candidate-host">${this._escapeHtml(c.host || c.ip)}:${c.port || 1883}</div>
                  <div class="candidate-source">${this._escapeHtml(c.source || 'unknown')}</div>
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
      </ha-card>
    `;

    // Bind events
    const refreshBtn = this.shadowRoot.querySelector('.refresh-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this._discover());
    }

    const candidateEls = this.shadowRoot.querySelectorAll('.candidate');
    candidateEls.forEach(el => {
      el.addEventListener('click', () => {
        const idx = parseInt(el.dataset.index, 10);
        if (this._candidates[idx]) {
          this._connect(this._candidates[idx]);
        }
      });
    });
  }

  _escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
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
