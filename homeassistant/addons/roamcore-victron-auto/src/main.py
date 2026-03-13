import asyncio
import json
import logging
import os
import socket
import ssl
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Optional
from urllib.parse import urlparse

import paho.mqtt.client as mqtt
from zeroconf import ServiceBrowser, ServiceStateChange, Zeroconf

LOG = logging.getLogger("roamcore_victron_auto")


def load_options() -> dict[str, Any]:
    # Home Assistant add-ons mount options at /data/options.json
    p = "/data/options.json"
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


@dataclass
class VictronTarget:
    host: str
    port: int
    source: str


class MdnsMqttListener:
    def __init__(self):
        # Many networks have multiple `_mqtt._tcp` advertisers (eg. Home Assistant,
        # printers, dev brokers). Keep a small candidate set and let higher-level
        # logic pick/validate.
        # Key: (host, port)
        self.candidates: dict[tuple[str, int], VictronTarget] = {}

    def best(self) -> Optional[VictronTarget]:
        if not self.candidates:
            return None

        def score(t: VictronTarget) -> tuple[int, float]:
            # Prefer likely-Victron names and standard ports.
            s = 0
            name = (t.source or "").lower()
            if any(k in name for k in ("venus", "victron", "gx", "cerbo", "color")):
                s += 2
            if any(k in name for k in ("homeassistant", "ha", "mosquitto")):
                s -= 2
            if t.port in (1883, 8883):
                s += 1
            # Tie-breaker: most recently seen (we store it in source timestamp suffix)
            # If parsing fails, treat as old.
            ts = 0.0
            try:
                if "@" in t.source:
                    ts = float(t.source.split("@")[-1])
            except Exception:
                ts = 0.0
            return (s, ts)

        # max by score then timestamp
        return max(self.candidates.values(), key=score)

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        return

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        try:
            info = zc.get_service_info(type_, name)
            if not info:
                return
            addrs = info.parsed_addresses()
            if not addrs:
                return
            host = addrs[0]
            port = int(info.port)
            tgt = VictronTarget(host=host, port=port, source=f"mdns:{name}@{time.time():.0f}")
            self.candidates[(host, port)] = tgt
            LOG.info("mDNS discovered MQTT: %s:%s (%s)", host, port, name)
        except Exception:
            LOG.exception("mDNS add_service failed")


class VictronAuto:
    def __init__(self, opts: dict[str, Any]):
        self.opts = opts
        self.scan_interval = int(opts.get("scan_interval_sec", 15))
        self.timeout = int(opts.get("mqtt_connect_timeout_sec", 10))
        self.prefer_mdns = bool(opts.get("prefer_mdns", True))
        self.prefer_venus_local = bool(opts.get("prefer_venus_local", True))
        self.victron_host = opts.get("victron_host")
        self.victron_port = int(opts.get("victron_mqtt_port", 1883))
        self.victron_port_tls = int(opts.get("victron_mqtt_port_tls", 8883))

        # Victron LAN MQTT security is configurable on the GX (Venus OS).
        # Official dbus-flashmq doc: broker on 1883 and/or 8883 depending on security settings.
        self.victron_use_tls = bool(opts.get("victron_use_tls", False))
        # Optional manual override. Without this, we must learn the portal id from any incoming
        # notification topic (N/<portal id>/...). But if the GX is idle and nothing changes,
        # we won't receive a first notification and can't send keepalives (catch-22).
        # So: allow a user-supplied portal id to trigger keepalive immediately.
        self.victron_portal_id = opts.get("victron_portal_id")
        self.victron_username = opts.get("victron_username")
        self.victron_password = opts.get("victron_password")
        self.victron_tls_ca_file = opts.get("victron_tls_ca_file")
        self.victron_tls_insecure = bool(opts.get("victron_tls_insecure", True))

        # Keepalive behavior (dbus-flashmq / Venus OS)
        # Official docs: empty payload triggers a full republish; optional keepalive-options can
        # request echo payload on Venus >= 3.50.
        self.keepalive_use_echo = bool(opts.get("keepalive_use_echo", True))

        # Optional periodic *full* snapshot refresh (empty keepalive payload) even after we
        # switch to suppress-republish keepalives. This is useful as a guard against missed
        # startup data (eg. add-on restarts while GX is idle) and aligns with the official
        # docs suggestion: send suppress-republish keepalives on a timer, and send empty
        # keepalives when your program requires a full refresh.
        self.full_snapshot_interval_sec = int(opts.get("full_snapshot_interval_sec", 0))

        # Optional extra read requests to fetch values that don't change often
        # (notably settings under com.victronenergy.settings). Format is a list of
        # topic suffixes after the portal id, eg:
        #   ["settings/0/Settings", "system/0/Dc"]
        # These are sent as read requests: R/<portal id>/<suffix>
        self.startup_read_requests: list[str] = list(opts.get("startup_read_requests", []) or [])

        # HA MQTT credentials fallback (when Supervisor MQTT service is not enabled)
        self.ha_mqtt_username = opts.get("ha_mqtt_username")
        self.ha_mqtt_password = opts.get("ha_mqtt_password")

        self.publish_discovery = bool(opts.get("publish_discovery", True))
        self.publish_devices_sensor = bool(opts.get("publish_devices_sensor", True))
        self.discovery_prefix = str(opts.get("discovery_prefix", "homeassistant"))
        self.device_name = str(opts.get("device_name", "RoamCore Victron System"))
        self.device_id = str(opts.get("device_id", "roamcore-victron"))

        self._zc: Optional[Zeroconf] = None
        self._mdns_listener = MdnsMqttListener()

        self._victron: Optional[VictronTarget] = None
        self._victron_client: Optional[mqtt.Client] = None
        self._portal_id: Optional[str] = None
        self._did_keepalive = False
        self._keepalive_echo: Optional[str] = None
        self._did_full_publish = False
        self._last_full_snapshot_request = 0.0
        self._last_keepalive_sent = 0.0
        self._keepalive_pending_since: Optional[float] = None
        self._keepalive_attempts = 0

        self._ha_client: Optional[mqtt.Client] = None

        self._last_discovery_publish = 0.0
        self._last_seen_victron_msg = 0.0

        # Static config validation summary (surfaced via status endpoint + summary logs).
        # We keep this intentionally simple and non-fatal: most misconfigurations should
        # result in a clear status surface, not a crash-loop.
        self._config_errors: list[str] = []
        self._config_warnings: list[str] = []
        self._validate_config()

        self._victron_connected_at: Optional[float] = None
        # Cache bad targets to avoid sticky failure when multiple MQTT brokers are
        # present on the LAN.
        # Key: (host, port) -> unix timestamp when it may be retried.
        self._bad_targets: dict[tuple[str, int], float] = {}

        self._last_devices_snapshot_publish = 0.0

        # Discovered device instances (from official dbus-flashmq doc suggestion:
        # subscribe to N/<portal>/+/+/ProductId)
        # Keyed by (service_type, device_instance)
        self._devices: dict[tuple[str, str], dict[str, Any]] = {}

        # Topic inventory (audit mode): track which Victron topics we've observed.
        # Keyed by (service_type, device_instance, dbus_path)
        self._topics: dict[tuple[str, str, str], dict[str, Any]] = {}
        self._last_topics_snapshot_publish = 0.0
        self.topics_sensor_max = int(opts.get("topics_sensor_max", 200))

        # Optional: publish a Home Assistant MQTT Discovery entity per observed Victron topic.
        # This can create hundreds/thousands of entities, so it is guarded by an option + cap.
        # Default OFF for production sanity; enable explicitly when needed.
        self.publish_raw_topics = bool(opts.get("publish_raw_topics", False))
        self.raw_topics_max = int(opts.get("raw_topics_max", 500))
        if self.publish_raw_topics:
            LOG.info("Raw topic sensors enabled (raw_topics_max=%s)", self.raw_topics_max)
        else:
            LOG.info("Raw topic sensors disabled")
        self._published_raw_topics: set[str] = set()

        # Track which HA MQTT Discovery entities we've already published.
        self._published_discovery_entities: set[str] = set()

        # Notifications look like: N/<portal ID>/<service_type>/<device instance>/<D-Bus path>
        # Payload JSON usually includes {"value": ...}.
        #
        # We keep the mapping intentionally small and stable.
        # Some values (VE.Bus and solar chargers) can have multiple instances; we aggregate
        # those and publish a single vt_* sensor/binary_sensor.
        self._path_to_vt: dict[tuple[str, str], dict[str, Any]] = {
            ("system", "Dc/Battery/Voltage"): {
                "vt_key": "vt_battery_voltage_v",
                "name": "Victron battery voltage",
                "device_class": "voltage",
                "unit": "V",
                "icon": "mdi:car-battery",
            },
            ("system", "Dc/Battery/Current"): {
                "vt_key": "vt_battery_current_a",
                "name": "Victron battery current",
                "device_class": "current",
                "unit": "A",
                "icon": "mdi:current-dc",
            },
            ("system", "Dc/Battery/Power"): {
                "vt_key": "vt_battery_power_w",
                "name": "Victron battery power",
                "device_class": "power",
                "unit": "W",
                "icon": "mdi:battery-charging",
            },
            ("system", "Soc"): {
                "vt_key": "vt_battery_soc_percent",
                "name": "Victron battery state of charge",
                "device_class": "battery",
                "unit": "%",
                "icon": "mdi:battery",
            },

            # Total solar power (best-effort). Many GX systems publish this under
            # com.victronenergy.system.
            ("system", "Dc/Pv/Power"): {
                "vt_key": "vt_solar_power_w",
                "name": "Victron solar power",
                "device_class": "power",
                "unit": "W",
                "icon": "mdi:solar-power",
            },

            # Total DC load power (best-effort).
            ("system", "Dc/System/Power"): {
                "vt_key": "vt_dc_load_power_w",
                "name": "Victron DC load power",
                "device_class": "power",
                "unit": "W",
                "icon": "mdi:flash",
            },

            # Aggregated multi-instance values (computed from other topics).
            ("__agg__", "ac_in_power"): {
                "vt_key": "vt_ac_in_power_w",
                "name": "Victron AC in power",
                "device_class": "power",
                "unit": "W",
                "icon": "mdi:transmission-tower",
            },
            ("__agg__", "ac_out_power"): {
                "vt_key": "vt_ac_out_power_w",
                "name": "Victron AC out power",
                "device_class": "power",
                "unit": "W",
                "icon": "mdi:transmission-tower",
            },
            ("__agg__", "solar_power"): {
                "vt_key": "vt_solar_power_w",
                "name": "Victron solar power",
                "device_class": "power",
                "unit": "W",
                "icon": "mdi:solar-power",
            },
            ("__agg__", "shore_connected"): {
                "domain": "binary_sensor",
                "vt_key": "vt_shore_connected",
                "name": "Victron shore power connected",
                "device_class": "plug",
                "icon": "mdi:power-plug",
            },
        }

        # Aggregation caches for multi-instance services.
        self._vebus_ac_in_w: dict[str, float] = {}
        self._vebus_ac_out_w: dict[str, float] = {}
        self._vebus_shore_connected: dict[str, bool] = {}
        self._solarcharger_yield_w: dict[str, float] = {}

        # Devices sensor sizing guardrail (MQTT payload limits vary by broker/client).
        self.devices_sensor_max = int(opts.get("devices_sensor_max", 50))

        # Periodic one-line status summary for boring debugging.
        self._started_at = time.time()
        self._tick_count = 0
        self._last_tick_duration_ms: Optional[float] = None
        self._last_summary_log = 0.0
        self._summary_log_interval_sec = int(opts.get("summary_log_interval_sec", 60))

    async def run(self):
        # Start lightweight local HTTP API for the UI "Connect Victron" flow.
        # Intended to be exposed via add-on ingress.
        try:
            self._start_http_api()
        except Exception:
            LOG.exception("Failed to start HTTP API")

        # Start mDNS browse
        if self.prefer_mdns:
            self._zc = Zeroconf()
            ServiceBrowser(self._zc, "_mqtt._tcp.local.", handlers=[self._on_mdns])

        # Connect to HA MQTT broker (typically Mosquitto add-on)
        await self._connect_ha_mqtt()

        # Publish basic discovery immediately so users see entities without waiting
        # for the periodic discovery tick.
        if self.publish_discovery and self._ha_client:
            LOG.info("Publishing initial MQTT discovery configs")
            self._publish_discovery_skeleton()
            self._last_discovery_publish = time.time()

        while True:
            try:
                await self._tick()
            except Exception:
                LOG.exception("tick failed")
            await asyncio.sleep(self.scan_interval)

    def _start_http_api(self) -> None:
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def _json(self, code: int, obj: dict[str, Any]):
                raw = json.dumps(obj).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def _norm_path(self) -> str:
                """Normalize ingress-prefixed paths.

                HA ingress may forward requests as:
                  /api/hassio_ingress/<token>/<path>
                while the add-on server expects <path>.
                """

                p = urlparse(self.path)
                path = p.path or "/"

                # Strip hassio ingress prefix if present.
                if path.startswith("/api/hassio_ingress/"):
                    parts = path.split("/")
                    # ['', 'api', 'hassio_ingress', '<token>', ...rest]
                    rest = parts[4:]
                    path = "/" + "/".join(rest) if rest else "/"

                # Some HA versions use /api/ingress/<token>/...
                if path.startswith("/api/ingress/"):
                    parts = path.split("/")
                    # ['', 'api', 'ingress', '<token>', ...rest]
                    rest = parts[4:]
                    path = "/" + "/".join(rest) if rest else "/"

                return path

            def do_POST(self):
                path = self._norm_path()
                try:
                    LOG.info("HTTP POST %s (norm=%s)", self.path, path)
                except Exception:
                    pass

                if path in ("/api/v1/victron/connect", "/api/v1/connect"):
                    # Read JSON body
                    try:
                        length = int(self.headers.get("Content-Length", 0))
                        body = self.rfile.read(length).decode("utf-8") if length else "{}"
                        data = json.loads(body) if body else {}
                    except Exception as e:
                        return self._json(400, {"error": "invalid_json", "detail": str(e)})

                    host = data.get("host")
                    port = int(data.get("port", 1883))
                    use_tls = bool(data.get("use_tls", False))
                    portal_id = data.get("portal_id")

                    if not host:
                        return self._json(400, {"error": "missing_host"})

                    # Persist selection via Supervisor API (PATCH add-on options)
                    result = parent._persist_victron_selection(host, port, use_tls, portal_id)
                    if result.get("error"):
                        return self._json(500, result)

                    return self._json(200, {
                        "ok": True,
                        "message": "Victron device configured. Add-on will restart to apply.",
                        "host": host,
                        "port": port,
                        "use_tls": use_tls,
                        "portal_id": portal_id,
                    })

                if path in ("/api/v1/victron/clear", "/api/v1/clear"):
                    result = parent._persist_victron_clear()
                    if result.get("error"):
                        return self._json(500, result)
                    return self._json(200, {"ok": True, "message": "Cleared Victron config. Add-on will restart."})

                return self._json(404, {"error": "not_found"})

            def do_GET(self):
                path = self._norm_path()
                try:
                    LOG.info("HTTP GET %s (norm=%s)", self.path, path)
                except Exception:
                    pass

                # Simple built-in UI (best-effort) served via add-on ingress.
                # This avoids the complexity of custom cards needing an ingress token.
                #
                # If the ingress forwards a prefixed path, _norm_path() strips it.
                # We then treat *any* non-API path as the UI root.
                if (
                    path in ("/", "/index.html")
                    or (not path.startswith("/api/") and path not in ("/health", "/api/v1/health"))
                ): 
                    html = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>RoamCore — Connect Victron</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 0; background: #0b0f14; color: #e6edf3; }
    .wrap { max-width: 720px; margin: 0 auto; padding: 20px; }
    .card { background: #111826; border: 1px solid #243044; border-radius: 12px; padding: 16px; }
    h1 { font-size: 18px; margin: 0 0 12px; }
    button { background: #238636; border: none; color: white; padding: 10px 12px; border-radius: 10px; cursor: pointer; }
    button.secondary { background: #334155; }
    button:disabled { opacity: .6; cursor: not-allowed; }
    .row { display: flex; gap: 10px; align-items: center; }
    .muted { color: #9fb0c2; font-size: 13px; }
    .err { background: #7f1d1d; padding: 10px 12px; border-radius: 10px; margin-top: 12px; }
    .ok { background: #064e3b; padding: 10px 12px; border-radius: 10px; margin-top: 12px; }
    ul { list-style: none; padding: 0; margin: 12px 0 0; }
    li { border: 1px solid #243044; border-radius: 10px; padding: 12px; margin-bottom: 10px; }
    .name { font-weight: 600; }
    code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; color: #d1e7ff; }
  </style>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"card\">
      <div class=\"row\" style=\"justify-content: space-between;\">
        <h1>Connect Victron</h1>
        <div class=\"row\">
          <button id=\"refresh\" class=\"secondary\">Refresh</button>
          <button id=\"clear\" class=\"secondary\">Clear</button>
        </div>
      </div>
      <div class=\"muted\">This page is served by the add-on (Ingress). It can configure the Victron target and restart the add-on.</div>

      <div id=\"msg\"></div>

      <div style=\"margin-top: 14px;\" class=\"row\">
        <input id=\"manualHost\" placeholder=\"Victron host (IP or hostname)\" style=\"flex:1; padding:10px 12px; border-radius:10px; border:1px solid #243044; background:#0b1220; color:#e6edf3;\" />
        <input id=\"manualPort\" placeholder=\"1883\" value=\"1883\" style=\"width:90px; padding:10px 12px; border-radius:10px; border:1px solid #243044; background:#0b1220; color:#e6edf3;\" />
        <button id=\"manualConnect\">Connect</button>
      </div>
      <div class=\"muted\" style=\"margin-top:6px;\">Tip: If discovery finds nothing, enter your GX IP here (eg. <code>192.168.1.123</code>) and click Connect.</div>

      <ul id=\"list\"></ul>
    </div>
  </div>

<script>
const msg = (kind, text) => {
  const el = document.getElementById('msg');
  el.innerHTML = text ? `<div class=\"${kind}\">${text}</div>` : '';
};

async function connectHost(host, port) {
  const resp = await fetch('api/v1/victron/connect', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({host, port}),
  });
  const out = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(out.error || resp.statusText);
  msg('ok', out.message || 'Configured. Restarting add-on...');
}

async function discover() {
  msg('', '');
  const list = document.getElementById('list');
  list.innerHTML = '<li class="muted">Discovering...</li>';
  // Use relative URLs so this works under HA ingress (which prefixes the path)
  const r = await fetch('api/v1/victron/discover');
  const j = await r.json();
  const c = (j.candidates || []);
  if (!c.length) {
    list.innerHTML = '<li class="muted">No candidates found. Use manual connect above or ensure your GX advertises MQTT on the LAN.</li>';
    return;
  }
  list.innerHTML = '';
  for (const cand of c) {
    const host = cand.host || cand.ip;
    const port = cand.port || 1883;
    const li = document.createElement('li');
    li.innerHTML = `
      <div class="row" style="justify-content: space-between;">
        <div>
          <div class="name">${(cand.name || 'Victron candidate')}</div>
          <div class="muted"><code>${host}:${port}</code> · ${cand.source || 'unknown'}</div>
        </div>
        <button>Connect</button>
      </div>
    `;
    li.querySelector('button').onclick = async () => {
      msg('', '');
      li.querySelector('button').disabled = true;
      try {
        await connectHost(host, port);
      } catch (e) {
        msg('err', `Connect failed: ${e.message}`);
      } finally {
        li.querySelector('button').disabled = false;
      }
    };
    list.appendChild(li);
  }
}

async function clearConfig() {
  msg('', '');
  const ok = confirm('Clear the saved Victron host/portal_id and restart the add-on?');
  if (!ok) return;
  const resp = await fetch('api/v1/victron/clear', { method: 'POST' });
  const out = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(out.error || resp.statusText);
  msg('ok', out.message || 'Cleared. Restarting add-on...');
}

document.getElementById('refresh').onclick = discover;
document.getElementById('clear').onclick = async () => {
  const btn = document.getElementById('clear');
  btn.disabled = true;
  try {
    await clearConfig();
  } catch (e) {
    msg('err', `Clear failed: ${e.message}`);
  } finally {
    btn.disabled = false;
  }
};
document.getElementById('manualConnect').onclick = async () => {
  msg('', '');
  const host = (document.getElementById('manualHost').value || '').trim();
  const port = parseInt(document.getElementById('manualPort').value || '1883', 10) || 1883;
  if (!host) { msg('err', 'Please enter a host (IP or hostname).'); return; }
  const btn = document.getElementById('manualConnect');
  btn.disabled = true;
  try {
    await connectHost(host, port);
  } catch (e) {
    msg('err', `Connect failed: ${e.message}`);
  } finally {
    btn.disabled = false;
  }
};

discover();
</script>
</body>
</html>"""
                    raw = html.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)
                    return

                if path in ("/health", "/api/v1/health"):
                    return self._json(200, {"ok": True})

                if path in ("/api/v1/victron/status", "/api/v1/status"):
                    try:
                        return self._json(200, {"ok": True, "status": parent.status_dict()})
                    except Exception as e:
                        return self._json(500, {"ok": False, "error": "status_failed", "detail": str(e)})

                if path in ("/api/v1/victron/discover", "/api/v1/discover"):
                    # MVP stub: return current best-known candidates from mdns + venus.local probe.
                    candidates: list[dict[str, Any]] = []

                    # 0) If a victron_host override is set (common for mock/dev), always show it as a candidate.
                    try:
                        if getattr(parent, "victron_host", None):
                            host = str(getattr(parent, "victron_host"))
                            use_tls = bool(getattr(parent, "victron_use_tls", False))
                            port = int(getattr(parent, "victron_port_tls", 8883) if use_tls else getattr(parent, "victron_port", 1883))
                            candidates.append(
                                {
                                    "name": "Configured host",
                                    "host": host,
                                    "port": port,
                                    "source": "config:victron_host",
                                }
                            )
                    except Exception:
                        pass

                    # 1) mDNS _mqtt candidates
                    try:
                        for tgt in list(getattr(parent._mdns_listener, "candidates", {}).values()):
                            candidates.append(
                                {
                                    "name": tgt.source,
                                    "host": tgt.host,
                                    "port": tgt.port,
                                    "source": tgt.source,
                                }
                            )
                    except Exception:
                        pass

                    if getattr(parent, "prefer_venus_local", False):
                        try:
                            # Avoid awaiting async helpers inside this sync HTTP handler.
                            # Also guard against long mDNS/DNS timeouts by using a short default timeout.
                            old_timeout = socket.getdefaulttimeout()
                            socket.setdefaulttimeout(0.3)
                            try:
                                ip = socket.gethostbyname("venus.local")
                            finally:
                                socket.setdefaulttimeout(old_timeout)

                            if ip:
                                candidates.append(
                                    {
                                        "name": "venus.local",
                                        "host": "venus.local",
                                        "ip": ip,
                                        "port": 1883,
                                        "source": "dns:venus.local",
                                    }
                                )
                        except Exception:
                            pass

                    # De-dupe
                    uniq: dict[tuple[str, int], dict[str, Any]] = {}
                    for c in candidates:
                        host = str(c.get("host") or c.get("ip") or "")
                        port = int(c.get("port") or 1883)
                        if host:
                            uniq[(host, port)] = c
                    return self._json(200, {"candidates": list(uniq.values())})

                return self._json(404, {"error": "not_found"})

            def log_message(self, fmt: str, *args):
                return

        server = HTTPServer(("0.0.0.0", 8099), Handler)
        t = threading.Thread(target=server.serve_forever, name="http-api", daemon=True)
        t.start()
        LOG.info("HTTP API listening on :8099")

    def _persist_victron_selection(
        self, host: str, port: int, use_tls: bool, portal_id: Optional[str]
    ) -> dict[str, Any]:
        """Persist Victron selection via Supervisor add-on options API.

        Updates the add-on options and triggers a restart to apply.
        """
        sup_token = os.environ.get("SUPERVISOR_TOKEN")
        if not sup_token:
            return {"error": "no_supervisor_token", "detail": "Not running as HA add-on"}

        try:
            import urllib.request

            # Build the options patch
            new_opts: dict[str, Any] = {
                "victron_host": host,
                "victron_mqtt_port": port,
                "victron_use_tls": use_tls,
            }
            if portal_id:
                new_opts["victron_portal_id"] = portal_id

            # Supervisor API notes:
            # - /addons/self/options is POST-only
            # - validation requires a full options payload (not just a partial patch)
            # So: fetch current options from /addons/self/info, merge, then POST full options.

            # Get current options from /info
            info_req = urllib.request.Request(
                "http://supervisor/addons/self/info",
                headers={"Authorization": f"Bearer {sup_token}"},
            )
            raw = urllib.request.urlopen(info_req, timeout=10).read().decode("utf-8")
            info = json.loads(raw) if raw else {}
            current = ((info.get("data") or {}).get("options") or {})
            if not isinstance(current, dict):
                current = {}

            merged = {**current, **new_opts}

            patch_body = json.dumps({"options": merged}).encode("utf-8")
            patch_req = urllib.request.Request(
                "http://supervisor/addons/self/options",
                data=patch_body,
                headers={
                    "Authorization": f"Bearer {sup_token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            urllib.request.urlopen(patch_req, timeout=10)
            LOG.info("Updated add-on options: %s", new_opts)

            # Trigger restart (async, non-blocking)
            def restart_addon():
                try:
                    import time as t_mod
                    t_mod.sleep(1)  # Brief delay to let the HTTP response complete
                    restart_req = urllib.request.Request(
                        "http://supervisor/addons/self/restart",
                        headers={"Authorization": f"Bearer {sup_token}"},
                        method="POST",
                    )
                    urllib.request.urlopen(restart_req, timeout=30)
                except Exception:
                    LOG.exception("Add-on restart failed")

            import threading
            threading.Thread(target=restart_addon, daemon=True).start()

            return {"ok": True}

        except Exception as e:
            LOG.exception("Failed to persist Victron selection")
            return {"error": "persist_failed", "detail": str(e)}

    def _persist_victron_clear(self) -> dict[str, Any]:
        """Clear Victron selection via Supervisor add-on options API.

        Removes victron_host and victron_portal_id from add-on options and triggers a restart.
        """

        sup_token = os.environ.get("SUPERVISOR_TOKEN")
        if not sup_token:
            return {"error": "no_supervisor_token", "detail": "Not running as HA add-on"}

        try:
            import urllib.request

            info_req = urllib.request.Request(
                "http://supervisor/addons/self/info",
                headers={"Authorization": f"Bearer {sup_token}"},
            )
            raw = urllib.request.urlopen(info_req, timeout=10).read().decode("utf-8")
            info = json.loads(raw) if raw else {}
            current = ((info.get("data") or {}).get("options") or {})
            if not isinstance(current, dict):
                current = {}

            merged = dict(current)
            # Remove selection keys; leave other configuration intact.
            for k in ("victron_host", "victron_portal_id"):
                if k in merged:
                    merged.pop(k, None)

            patch_body = json.dumps({"options": merged}).encode("utf-8")
            patch_req = urllib.request.Request(
                "http://supervisor/addons/self/options",
                data=patch_body,
                headers={
                    "Authorization": f"Bearer {sup_token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            urllib.request.urlopen(patch_req, timeout=10)
            LOG.info("Cleared Victron selection (victron_host, victron_portal_id)")

            def restart_addon():
                try:
                    import time as t_mod

                    t_mod.sleep(1)
                    restart_req = urllib.request.Request(
                        "http://supervisor/addons/self/restart",
                        headers={"Authorization": f"Bearer {sup_token}"},
                        method="POST",
                    )
                    urllib.request.urlopen(restart_req, timeout=30)
                except Exception:
                    LOG.exception("Add-on restart failed")

            import threading

            threading.Thread(target=restart_addon, daemon=True).start()

            return {"ok": True}
        except Exception as e:
            LOG.exception("Failed to clear Victron selection")
            return {"error": "persist_failed", "detail": str(e)}

    def _resolve(self, name: str) -> Optional[str]:
        """Synchronous DNS resolution helper for HTTP handler."""
        try:
            return socket.gethostbyname(name)
        except Exception:
            return None

    def _on_mdns(self, zc: Zeroconf, type_: str, name: str, state_change: ServiceStateChange):
        if state_change is ServiceStateChange.Added:
            self._mdns_listener.add_service(zc, type_, name)

    async def _tick(self):
        t0 = time.time()
        self._tick_count += 1
        # Choose Victron target
        target = await self._discover_target()
        if target and (
            self._victron is None or (target.host, target.port) != (self._victron.host, self._victron.port)
        ):
            LOG.info("Selected Victron target: %s:%s (%s)", target.host, target.port, target.source)
            self._victron = target
            await self._connect_victron()

        # Validate target: if we connected but haven't seen *any* Victron-style traffic
        # within a grace period, assume we latched onto a non-Victron broker (common
        # in HA labs) and rotate.
        self._maybe_rotate_bad_target()

        # Periodically publish discovery configs (idempotent)
        if self.publish_discovery and self._ha_client and time.time() - self._last_discovery_publish > 120:
            self._publish_discovery_skeleton()
            self._last_discovery_publish = time.time()

        # If we haven't seen messages in a while, mark offline by publishing availability
        if self._ha_client and time.time() - self._last_seen_victron_msg > 30:
            self._ha_client.publish(
                f"roamcore/victron/{self.device_id}/availability", payload="offline", retain=True
            )

        # Keep-alive maintenance (official dbus-flashmq behavior)
        # - After initial keepalive + full republish, keep the stream alive with suppress-republish.
        # - If we have not yet completed a full publish, avoid suppressing: we want the full snapshot.
        if self._victron_client and self._portal_id:
            # If full snapshot didn't complete after a keepalive-with-options payload,
            # retry with an empty keepalive payload as shown in official examples.
            self._maybe_retry_keepalive()

            # If configured, periodically request a *full* snapshot refresh even after
            # we've entered suppress-republish keepalive mode.
            self._maybe_request_periodic_full_snapshot()

            now = time.time()
            # Keepalive timeout is 60s in official docs.
            #
            # Practical note: during startup we want to quickly reach the first
            # `full_publish_completed` checkpoint; otherwise downstream apps will
            # appear idle (no retained messages). So we keep retry cadence tighter
            # until we've observed the first full publish.
            cadence = 30 if self._did_full_publish else 5
            if now - self._last_keepalive_sent > cadence:
                self._send_keepalive(suppress_republish=self._did_full_publish)
                self._last_keepalive_sent = now

        self._last_tick_duration_ms = (time.time() - t0) * 1000.0
        self._log_summary_if_due()

    def status_dict(self) -> dict[str, Any]:
        """Current runtime status snapshot (safe to call from sync HTTP handler)."""

        now = time.time()
        tgt = None
        if self._victron:
            tgt = {
                "host": self._victron.host,
                "port": self._victron.port,
                "source": self._victron.source,
            }
        return {
            "config": {
                "valid": len(self._config_errors) == 0,
                "errors": list(self._config_errors),
                "warnings": list(self._config_warnings),
                "prefer_mdns": bool(self.prefer_mdns),
                "prefer_venus_local": bool(self.prefer_venus_local),
                "victron_use_tls": bool(self.victron_use_tls),
                "victron_host_configured": bool(self.victron_host),
                "victron_portal_id_configured": bool(self.victron_portal_id),
                "publish_raw_topics": bool(self.publish_raw_topics),
            },
            "uptime_sec": int(now - (self._started_at or now)),
            "scan_interval_sec": self.scan_interval,
            "tick_count": self._tick_count,
            "last_tick_ms": round(self._last_tick_duration_ms or 0.0, 1),
            "ha_mqtt": {
                "connected": bool(self._ha_client),
                "host": getattr(self, "_ha_mqtt_host", None),
                "port": getattr(self, "_ha_mqtt_port", None),
                "has_user": bool(getattr(self, "_ha_mqtt_user", None)),
            },
            "victron": {
                "target": tgt,
                "connected": bool(self._victron_client),
                "portal_id": self._portal_id,
                "did_full_publish": bool(self._did_full_publish),
                "last_seen_msg_age_sec": int(now - self._last_seen_victron_msg)
                if self._last_seen_victron_msg
                else None,
                "keepalive_age_sec": int(now - self._last_keepalive_sent)
                if self._last_keepalive_sent
                else None,
            },
            "inventory": {
                "devices_count": len(self._devices),
                "topics_count": len(self._topics),
                "raw_topics_published": len(self._published_raw_topics),
                "raw_topics_max": int(self.raw_topics_max),
            },
        }

    def _validate_config(self) -> None:
        """Best-effort options validation.

        This should never throw. It is used to surface configuration problems
        via /api/v1/victron/status and periodic STATUS logs.
        """

        errs: list[str] = []
        warns: list[str] = []
        try:
            if int(self.scan_interval) <= 0:
                errs.append("scan_interval_sec must be > 0")
        except Exception:
            errs.append("scan_interval_sec must be an integer")

        try:
            if int(self.timeout) <= 0:
                errs.append("mqtt_connect_timeout_sec must be > 0")
        except Exception:
            errs.append("mqtt_connect_timeout_sec must be an integer")

        # Raw topic publishing can explode entity count; keep guardrails.
        try:
            if bool(self.publish_raw_topics) and int(self.raw_topics_max) <= 0:
                errs.append("raw_topics_max must be > 0 when publish_raw_topics is enabled")
            if bool(self.publish_raw_topics) and int(self.raw_topics_max) > 5000:
                warns.append("raw_topics_max is very high (>5000); Home Assistant may slow down")
        except Exception:
            errs.append("raw_topics_max must be an integer")

        # TLS configuration sanity.
        try:
            if bool(self.victron_use_tls):
                if not self.victron_tls_insecure and not self.victron_tls_ca_file:
                    warns.append("victron_use_tls is on but no CA file is set (and insecure=false); TLS may fail")
        except Exception:
            pass

        # Credentials are commonly needed; warn if missing.
        if not (self.victron_username and self.victron_password):
            warns.append("victron_username/victron_password not set; connection may fail if GX requires auth")

        # Host override sanity.
        if self.victron_host is not None:
            try:
                if not str(self.victron_host).strip():
                    errs.append("victron_host is set but empty")
            except Exception:
                errs.append("victron_host must be a string")

        self._config_errors = errs
        self._config_warnings = warns

    def _log_summary_if_due(self) -> None:
        """Emit a structured, grep-friendly status summary line periodically."""

        try:
            now = time.time()
            if self._summary_log_interval_sec <= 0:
                return
            if now - self._last_summary_log < self._summary_log_interval_sec:
                return
            self._last_summary_log = now

            summary = {"event": "status_summary", **self.status_dict()}
            LOG.info("STATUS %s", json.dumps(summary, sort_keys=True))
        except Exception:
            # Never let summary logging break the main loop.
            return

    async def _discover_target(self) -> Optional[VictronTarget]:
        # 0) Manual override
        if self.victron_host:
            host = str(self.victron_host)
            probe_port = self.victron_port_tls if self.victron_use_tls else self.victron_port
            if await self._tcp_probe(host, probe_port, timeout=0.5):
                return VictronTarget(host=host, port=probe_port, source="config:victron_host")

        # 1) mDNS _mqtt
        mdns = self._mdns_listener.best()
        if mdns and not self._is_bad_target(mdns):
            return mdns

        # 2) Try venus.local
        if self.prefer_venus_local:
            host = await self._resolve("venus.local")
            if host:
                probe_port = self.victron_port_tls if self.victron_use_tls else self.victron_port
                if await self._tcp_probe(host, probe_port, timeout=0.5):
                    return VictronTarget(host=host, port=probe_port, source="dns:venus.local")

        # TODO: ARP scan / port sweep (later)
        return None

    def _is_bad_target(self, t: VictronTarget) -> bool:
        until = self._bad_targets.get((t.host, t.port))
        return bool(until and time.time() < until)

    def _mark_bad_target(self, t: VictronTarget, cooldown_sec: int = 300) -> None:
        self._bad_targets[(t.host, t.port)] = time.time() + cooldown_sec
        LOG.warning(
            "Marking target as bad for %ss: %s:%s (%s)", cooldown_sec, t.host, t.port, t.source
        )

    def _maybe_rotate_bad_target(self) -> None:
        if not self._victron_client or not self._victron:
            return
        if not self._victron_connected_at:
            return

        # If we've seen any Victron message, the target is good.
        if self._last_seen_victron_msg and self._last_seen_victron_msg >= self._victron_connected_at:
            return

        # If portal id is explicitly configured, we expect full_publish_completed
        # relatively quickly after the first keepalive.
        grace = 12
        if time.time() - self._victron_connected_at < grace:
            return

        # No messages at all -> likely wrong broker.
        self._mark_bad_target(self._victron)
        try:
            self._victron_client.loop_stop()
            self._victron_client.disconnect()
        except Exception:
            pass
        self._victron_client = None
        self._victron = None
        self._portal_id = None
        self._did_keepalive = False
        self._did_full_publish = False
        self._victron_connected_at = None

    async def _resolve(self, name: str) -> Optional[str]:
        try:
            return socket.gethostbyname(name)
        except Exception:
            return None

    async def _tcp_probe(self, host: str, port: int, timeout: float) -> bool:
        try:
            fut = asyncio.open_connection(host, port)
            r, w = await asyncio.wait_for(fut, timeout=timeout)
            w.close()
            return True
        except Exception:
            return False

    async def _connect_ha_mqtt(self):
        # Preferred: ask Supervisor for the configured MQTT service (host/port/user/pass).
        # Endpoint: http://supervisor/services/mqtt (requires SUPERVISOR_TOKEN)
        host = None
        port = None
        user = None
        pw = None
        try:
            # Debug: list relevant env vars
            sup_vars = {k: v[:20]+"..." if len(v) > 20 else v for k, v in os.environ.items() if "SUPER" in k.upper() or "HASSIO" in k.upper() or "MQTT" in k.upper()}
            LOG.info("Supervisor/MQTT env vars: %s", sup_vars)
            sup_token = os.environ.get("SUPERVISOR_TOKEN")
            LOG.info("SUPERVISOR_TOKEN present: %s", bool(sup_token))
            if sup_token:
                import urllib.request

                req = urllib.request.Request(
                    "http://supervisor/services/mqtt",
                    headers={"Authorization": f"Bearer {sup_token}"},
                )
                raw = urllib.request.urlopen(req, timeout=5).read().decode("utf-8")
                obj = json.loads(raw)
                data = obj.get("data") or {}
                host = data.get("host")
                port = int(data.get("port")) if data.get("port") else None
                user = data.get("username")
                pw = data.get("password")
                LOG.info("Supervisor MQTT service: host=%s port=%s user=%s", host, port, bool(user))
        except Exception:
            LOG.exception("Failed to query Supervisor MQTT service; falling back")

        # Fallbacks (some environments export these)
        host = host or os.environ.get("MQTT_HOST") or os.environ.get("SUPERVISOR_MQTT_HOST") or "core-mosquitto"
        port = port or int(os.environ.get("MQTT_PORT") or os.environ.get("SUPERVISOR_MQTT_PORT") or "1883")
        user = user or os.environ.get("MQTT_USERNAME") or os.environ.get("SUPERVISOR_MQTT_USERNAME")
        pw = pw or os.environ.get("MQTT_PASSWORD") or os.environ.get("SUPERVISOR_MQTT_PASSWORD")

        # Explicit add-on option fallback (useful when Supervisor MQTT service is not enabled)
        user = user or (str(self.ha_mqtt_username) if self.ha_mqtt_username else None)
        pw = pw or (str(self.ha_mqtt_password) if self.ha_mqtt_password else None)

        # paho-mqtt 2.x: pin callback API version to avoid future-breaking defaults.
        client = mqtt.Client(
            client_id=f"roamcore-ha-{self.device_id}",
            protocol=mqtt.MQTTv311,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        if user:
            client.username_pw_set(user, pw or "")

        # Callback API v2 signatures:
        #   on_connect(client, userdata, flags, reason_code, properties)
        #   on_disconnect(client, userdata, disconnect_flags, reason_code, properties)
        client.on_connect = lambda c, u, f, rc, p: LOG.info("Connected to HA MQTT rc=%s", rc)
        client.on_disconnect = lambda c, u, df, rc, p: LOG.warning("HA MQTT disconnected rc=%s", rc)
        client.reconnect_delay_set(min_delay=1, max_delay=30)

        # Start loop thread
        client.connect_async(host, port, keepalive=30)
        client.loop_start()
        # Best-effort wait for connection
        await asyncio.sleep(1)
        self._ha_client = client
        # Save HA MQTT connection info (useful for dev mocks / fallback auth)
        self._ha_mqtt_host = host
        self._ha_mqtt_port = port
        self._ha_mqtt_user = user
        self._ha_mqtt_pw = pw

        # publish availability online
        self._ha_client.publish(f"roamcore/victron/{self.device_id}/availability", payload="online", retain=True)

    async def _connect_victron(self):
        if not self._victron:
            return
        if self._victron_client:
            try:
                self._victron_client.loop_stop()
                self._victron_client.disconnect()
            except Exception:
                pass

        # paho-mqtt 2.x: pin callback API version to avoid future-breaking defaults.
        client = mqtt.Client(
            client_id=f"roamcore-victron-{self.device_id}",
            protocol=mqtt.MQTTv311,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        if self.victron_username:
            client.username_pw_set(str(self.victron_username), str(self.victron_password or ""))
        else:
            # Dev-friendly fallback: if the Victron target is the same broker as HA MQTT
            # (e.g. when using a mock publisher on core-mosquitto), reuse the HA MQTT
            # service credentials so we can subscribe.
            try:
                if (
                    getattr(self, "_ha_mqtt_host", None)
                    and getattr(self, "_ha_mqtt_port", None)
                    and self._victron.host == self._ha_mqtt_host
                    and self._victron.port == self._ha_mqtt_port
                    and getattr(self, "_ha_mqtt_user", None)
                ):
                    client.username_pw_set(str(self._ha_mqtt_user), str(getattr(self, "_ha_mqtt_pw", "") or ""))
                    LOG.info("Using HA MQTT service credentials for Victron MQTT connection")
            except Exception:
                LOG.exception("Failed to apply HA MQTT credential fallback for Victron MQTT")

        if self.victron_use_tls:
            ctx = ssl.create_default_context()
            if self.victron_tls_ca_file:
                try:
                    ctx.load_verify_locations(cafile=str(self.victron_tls_ca_file))
                except Exception:
                    LOG.exception("Failed to load victron_tls_ca_file=%s", self.victron_tls_ca_file)
            if self.victron_tls_insecure:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            client.tls_set_context(ctx)
        client.on_connect = self._on_victron_connect
        client.on_message = self._on_victron_message
        client.on_disconnect = lambda c, u, df, rc, p: LOG.warning("Victron MQTT disconnected rc=%s", rc)
        client.reconnect_delay_set(min_delay=1, max_delay=30)

        # reset state for this connection
        self._portal_id = str(self.victron_portal_id) if self.victron_portal_id else None
        self._did_keepalive = False
        self._keepalive_echo = None
        self._did_full_publish = False
        self._last_keepalive_sent = 0.0
        self._keepalive_pending_since = None
        self._keepalive_attempts = 0

        # Set before connecting so callbacks (on_connect) can publish keepalives immediately.
        self._victron_client = client
        self._victron_connected_at = time.time()
        self._last_seen_victron_msg = 0.0

        client.connect_async(self._victron.host, self._victron.port, keepalive=30)
        client.loop_start()
        await asyncio.sleep(1)

    def _on_victron_connect(self, client: mqtt.Client, userdata, flags, rc, properties=None):
        LOG.info("Connected to Victron MQTT rc=%s", rc)
        # Local broker: subscribe to notifications.
        # If portal id is known, scope the subscription; otherwise subscribe broadly and learn it.
        if self._portal_id:
            client.subscribe(f"N/{self._portal_id}/#")
            # Trigger keepalive immediately (see keep-alive chapter in dbus-flashmq README).
            self._did_keepalive = True
            self._send_keepalive(suppress_republish=False)
            self._last_keepalive_sent = time.time()
            self._keepalive_pending_since = self._last_keepalive_sent
            self._keepalive_attempts = 1

            # Optional startup read requests for rarely-changing values.
            self._send_startup_read_requests()
        else:
            client.subscribe("N/+/#")

    def _on_victron_message(self, client: mqtt.Client, userdata, msg):
        self._last_seen_victron_msg = time.time()

        topic = (msg.topic or "").lstrip("/")
        parts = topic.split("/")
        if len(parts) < 2:
            return

        # Learn portal id from any notification
        if parts[0] == "N" and self._portal_id is None:
            self._portal_id = parts[1]
            LOG.info("Detected portal id: %s", self._portal_id)
            # Now that we know it, narrow subscription and request a snapshot.
            try:
                client.subscribe(f"N/{self._portal_id}/#")
                # Best-effort unsubscribe from broad wildcard; reduces traffic on busy brokers.
                client.unsubscribe("N/+/#")
            except Exception:
                pass

        # Kick keepalive once after we know portal id.
        # Official docs (dbus-flashmq): publish to R/<portal ID>/keepalive to trigger full republish.
        if self._portal_id and not self._did_keepalive:
            self._did_keepalive = True
            self._send_keepalive(suppress_republish=False)
            self._last_keepalive_sent = time.time()
            self._keepalive_pending_since = self._last_keepalive_sent
            self._keepalive_attempts = 1

            # Optional startup read requests for rarely-changing values.
            self._send_startup_read_requests()

        # Publish availability online
        if self._ha_client:
            self._ha_client.publish(f"roamcore/victron/{self.device_id}/availability", payload="online", retain=True)

        # Observe full_publish_completed (useful end-to-end checkpoint for snapshot completeness)
        if (
            parts[0] == "N"
            and self._portal_id
            and len(parts) == 3
            and parts[1] == self._portal_id
            and parts[2] == "full_publish_completed"
        ):
            try:
                payload = msg.payload.decode("utf-8") if msg.payload else ""
                data = json.loads(payload) if payload else {}
                if not isinstance(data, dict):
                    data = {}
                echo = data.get("full-publish-completed-echo")
                if self._keepalive_echo and echo == self._keepalive_echo:
                    self._did_full_publish = True
                    LOG.info("Full publish completed (echo matched)")
                else:
                    # Still useful to know _someone_ triggered it.
                    self._did_full_publish = True
                    LOG.info("Full publish completed")
            except Exception:
                self._did_full_publish = True
                LOG.info("Full publish completed (payload parse failed)")

            # keepalive satisfied
            self._keepalive_pending_since = None
            return

        # Map select topics to vt_* sensors.
        if len(parts) < 5 or parts[0] != "N":
            return
        if self._portal_id and parts[1] != self._portal_id:
            return

        # parts: N/<portal>/<service_type>/<device instance>/<dbus path...>
        service_type = parts[2]
        device_instance = parts[3]
        dbus_path = "/".join(parts[4:])

        # Audit/inventory: record all observed topics (best-effort, bounded).
        try:
            key = (service_type, device_instance, dbus_path)
            rec = self._topics.get(key) or {
                "service_type": service_type,
                "device_instance": device_instance,
                "dbus_path": dbus_path,
                "first_seen": int(time.time()),
            }
            rec["last_seen"] = int(time.time())
            # Store a small sample of value for debugging (stringified, size-bounded)
            v_sample = self._extract_value(msg.payload)
            if v_sample is None:
                rec["sample"] = None
            else:
                s = str(v_sample)
                rec["sample"] = s[:120]
            self._topics[key] = rec

            # Periodically publish the snapshot sensor
            if self._ha_client:
                self._publish_topics_snapshot()

                # Optionally publish per-topic discovery entities (raw mirroring)
                if self.publish_raw_topics:
                    self._ensure_raw_topic_entity(service_type, device_instance, dbus_path)
        except Exception:
            pass

        # Lightweight device discovery: capture ProductId topics for an instance map.
        # Official docs recommend: mosquitto_sub -t 'N/<portal ID>/+/+/ProductId'
        if dbus_path == "ProductId":
            try:
                payload = msg.payload.decode("utf-8") if msg.payload else ""
                data = json.loads(payload) if payload else {}
                if not isinstance(data, dict):
                    data = {}
                v = data.get("value")
                self._devices[(service_type, device_instance)] = {
                    "service_type": service_type,
                    "device_instance": device_instance,
                    "product_id": v,
                    "last_seen": int(time.time()),
                }
                if self._ha_client:
                    self._publish_devices_snapshot()
            except Exception:
                # Don't let discovery parsing break the main ingest.
                pass

        # Update rolling aggregates (VE.Bus + solarcharger). This also publishes the
        # aggregate vt_* sensors/binary_sensor.
        self._update_aggregates_from_instance(service_type, device_instance, dbus_path, msg.payload)

        meta = self._path_to_vt.get((service_type, dbus_path))
        if not meta:
            return

        v = self._extract_value(msg.payload)
        vt_key = str(meta["vt_key"])

        if self._ha_client:
            self._ensure_discovery_for_meta(meta, vt_key, device_instance=device_instance)
            self._publish_state_for_meta(meta, vt_key, v)

    def _extract_value(self, payload_bytes: Optional[bytes]) -> Any:
        """Extract {"value": ...} from dbus-flashmq notifications.

        Handles edge-cases:
        - empty payload (b"")
        - explicit null payload (b"null")
        - malformed JSON
        """

        if not payload_bytes:
            return None

        try:
            txt = payload_bytes.decode("utf-8")
        except Exception:
            return None

        s = (txt or "").strip()
        if not s or s == "null":
            return None

        try:
            data = json.loads(s)
        except Exception:
            return None

        if not isinstance(data, dict):
            return None

        return data.get("value")

    def _coerce_bool(self, v: Any) -> bool:
        if v is None:
            return False
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return bool(v)
        s = str(v).strip().lower()
        return s in ("1", "true", "on", "yes", "y", "connected")

    def _publish_state_for_meta(self, meta: dict[str, Any], vt_key: str, v: Any) -> None:
        if not self._ha_client:
            return

        domain = str(meta.get("domain") or "sensor")
        state_topic = f"roamcore/victron/{self.device_id}/{vt_key}/state"

        if domain == "binary_sensor":
            payload = "ON" if self._coerce_bool(v) else "OFF"
        else:
            payload = "" if v is None else str(v)

        self._ha_client.publish(state_topic, payload=payload, retain=True)

        # Dev-friendly: log the first publish per vt_key to confirm mapping is alive.
        try:
            if not hasattr(self, "_logged_vt_keys"):
                self._logged_vt_keys = set()
            if vt_key not in self._logged_vt_keys:
                self._logged_vt_keys.add(vt_key)
                LOG.info("Published %s=%s", vt_key, payload)
        except Exception:
            pass

    def _ensure_discovery_for_meta(self, meta: dict[str, Any], vt_key: str, device_instance: str) -> None:
        if not self._ha_client:
            return
        # Stable id to prevent repeated discovery floods.
        uniq = f"{self.device_id}_{vt_key}"
        if uniq in self._published_discovery_entities:
            return

        name = meta.get("name") or vt_key

        domain = str(meta.get("domain") or "sensor")
        cfg_topic = f"{self.discovery_prefix}/{domain}/{self.device_id}/{uniq}/config"
        state = f"roamcore/victron/{self.device_id}/{vt_key}/state"

        cfg: dict[str, Any] = {
            "name": name,
            "unique_id": uniq,
            # Force entity_id style to match requested vt namespace.
            # Home Assistant will create e.g. sensor.vt_battery_voltage_v
            "object_id": vt_key,
            "state_topic": state,
            "availability_topic": f"roamcore/victron/{self.device_id}/availability",
            "device": {
                "identifiers": [self.device_id],
                "name": self.device_name,
                "model": "Victron GX (dbus-flashmq)",
                "manufacturer": "Victron Energy",
            },
        }
        if meta.get("unit"):
            cfg["unit_of_measurement"] = meta["unit"]
        if meta.get("device_class"):
            cfg["device_class"] = meta["device_class"]
        if meta.get("icon"):
            cfg["icon"] = meta["icon"]

        if domain == "binary_sensor":
            cfg["payload_on"] = "ON"
            cfg["payload_off"] = "OFF"

        self._ha_client.publish(cfg_topic, payload=json.dumps(cfg), retain=True)
        self._published_discovery_entities.add(uniq)

    def _update_aggregates_from_instance(
        self,
        service_type: str,
        device_instance: str,
        dbus_path: str,
        payload_bytes: Optional[bytes],
    ) -> None:
        """Maintain aggregated vt_* metrics across multi-instance services."""

        if not self._ha_client:
            return

        v = self._extract_value(payload_bytes)

        # VE.Bus: AC in/out power and shore connected
        if service_type == "vebus":
            if dbus_path == "Ac/ActiveIn/P":
                if isinstance(v, (int, float)):
                    self._vebus_ac_in_w[device_instance] = float(v)
            elif dbus_path == "Ac/Out/P":
                if isinstance(v, (int, float)):
                    self._vebus_ac_out_w[device_instance] = float(v)
            elif dbus_path == "Ac/ActiveIn/Connected":
                self._vebus_shore_connected[device_instance] = self._coerce_bool(v)

            if dbus_path in ("Ac/ActiveIn/P", "Ac/Out/P", "Ac/ActiveIn/Connected"):
                ac_in_total = sum(self._vebus_ac_in_w.values()) if self._vebus_ac_in_w else None
                ac_out_total = sum(self._vebus_ac_out_w.values()) if self._vebus_ac_out_w else None
                shore_any = any(self._vebus_shore_connected.values()) if self._vebus_shore_connected else None

                # Only publish aggregates once we have a value; avoid publishing empty/false
                # placeholders during startup ordering differences.
                if ac_in_total is not None:
                    self._publish_aggregate("ac_in_power", ac_in_total)
                if ac_out_total is not None:
                    self._publish_aggregate("ac_out_power", ac_out_total)
                if shore_any is not None:
                    self._publish_aggregate("shore_connected", shore_any)

        # Solar chargers: sum Yield/Power
        if service_type == "solarcharger" and dbus_path == "Yield/Power":
            if isinstance(v, (int, float)):
                self._solarcharger_yield_w[device_instance] = float(v)
                self._publish_aggregate("solar_power", sum(self._solarcharger_yield_w.values()))

    def _publish_aggregate(self, agg_key: str, value: Any) -> None:
        meta = self._path_to_vt.get(("__agg__", agg_key))
        if not meta:
            return

        vt_key = str(meta["vt_key"])
        self._ensure_discovery_for_meta(meta, vt_key, device_instance="0")
        self._publish_state_for_meta(meta, vt_key, value)

    def _send_keepalive(self, suppress_republish: bool):
        """Send a keepalive request according to official dbus-flashmq semantics.

        - Empty payload triggers full republish.
        - After initial full republish, use keepalive-options suppress-republish to reduce traffic.
        - Venus OS >= 3.50 supports full-publish-completed-echo for correlation.
        """

        if not self._victron_client or not self._portal_id:
            return

        try:
            # Official semantics (dbus-flashmq README):
            # - Empty payload triggers full republish.
            # - keepalive-options can request echo (Venus >= 3.50) and/or suppress-republish.
            payload: str = ""
            if suppress_republish:
                payload = json.dumps({"keepalive-options": ["suppress-republish"]})
            else:
                if self.keepalive_use_echo:
                    self._keepalive_echo = f"roamcore-{int(time.time())}"
                    payload = json.dumps(
                        {"keepalive-options": [{"full-publish-completed-echo": self._keepalive_echo}]}
                    )
                else:
                    payload = ""

            self._victron_client.publish(
                f"R/{self._portal_id}/keepalive", payload=payload, qos=0, retain=False
            )
            if not suppress_republish and payload == "":
                self._last_full_snapshot_request = time.time()
            LOG.info(
                "Sent keepalive (suppress_republish=%s, echo=%s)",
                suppress_republish,
                bool(self._keepalive_echo) if not suppress_republish else False,
            )
        except Exception:
            LOG.exception("Failed to publish keepalive")

    def _maybe_request_periodic_full_snapshot(self) -> None:
        if not self._victron_client or not self._portal_id:
            return
        if self.full_snapshot_interval_sec <= 0:
            return

        now = time.time()
        last = self._last_full_snapshot_request or 0.0
        # Don't spam: also require that we are already in steady-state (did at least one snapshot)
        # or that we've been running a bit.
        if last and (now - last) < self.full_snapshot_interval_sec:
            return

        # Request a full snapshot via empty keepalive payload.
        try:
            self._victron_client.publish(
                f"R/{self._portal_id}/keepalive",
                payload="",
                qos=0,
                retain=False,
            )
            self._last_full_snapshot_request = now
            LOG.info("Requested periodic full snapshot (empty keepalive)")
        except Exception:
            LOG.exception("Failed to request periodic full snapshot")

    def _send_startup_read_requests(self) -> None:
        """Send optional read requests for rarely-changing values.

        Official docs: values that don't change often (notably settings) may require explicit
        reads via `R/<portal id>/<service>/<instance>/<path>`.
        """

        if not self._victron_client or not self._portal_id:
            return
        if not self.startup_read_requests:
            return

        for suffix in self.startup_read_requests:
            s = str(suffix or "").strip().lstrip("/")
            if not s:
                continue
            try:
                self._victron_client.publish(f"R/{self._portal_id}/{s}", payload="", qos=0, retain=False)
                LOG.info("Sent startup read request: R/%s/%s", self._portal_id, s)
            except Exception:
                LOG.exception("Failed startup read request: %s", s)

    def _maybe_retry_keepalive(self):
        """Fallback behavior for older Venus versions / edge cases.

        If we don't observe `N/<portal>/full_publish_completed` within ~20s of the keepalive
        that included keepalive-options, retry with an empty payload, which is the canonical
        example in the dbus-flashmq docs.
        """

        if not self._victron_client or not self._portal_id:
            return
        if self._did_full_publish:
            return
        if not self._keepalive_pending_since:
            return
        if self._keepalive_attempts >= 2:
            return

        if time.time() - self._keepalive_pending_since < 20:
            return

        try:
            self._victron_client.publish(
                f"R/{self._portal_id}/keepalive",
                payload="",
                qos=0,
                retain=False,
            )
            self._keepalive_attempts += 1
            self._keepalive_pending_since = time.time()
            LOG.warning("Retrying keepalive with empty payload (attempt %s)", self._keepalive_attempts)
        except Exception:
            LOG.exception("Failed to retry keepalive")

    def _publish_discovery_skeleton(self):
        if not self._ha_client:
            return

        LOG.info("Publishing discovery skeleton")

        # Minimal placeholder entity to show add-on is alive
        uniq = f"{self.device_id}_status"
        base = f"{self.discovery_prefix}/sensor/{self.device_id}/{uniq}/config"
        state_topic = f"roamcore/victron/{self.device_id}/status"

        payload = {
            "name": "Victron Link Status",
            "unique_id": uniq,
            "state_topic": state_topic,
            "icon": "mdi:lan-connect",
            "availability_topic": f"roamcore/victron/{self.device_id}/availability",
            "device": {
                "identifiers": [self.device_id],
                "name": self.device_name,
                "model": "Victron GX (auto)",
                "manufacturer": "RoamCore",
            },
        }
        self._ha_client.publish(base, payload=json.dumps(payload), retain=True)
        # publish state
        st = "connected" if (time.time() - self._last_seen_victron_msg) < 30 else "searching"
        self._ha_client.publish(state_topic, payload=st, retain=True)

        # Expose whether we've received a full publish snapshot yet.
        snap_topic = f"roamcore/victron/{self.device_id}/snapshot_state"
        self._ha_client.publish(snap_topic, payload="ready" if self._did_full_publish else "pending", retain=True)

        snap_uniq = f"{self.device_id}_snapshot_state"
        snap_cfg_topic = f"{self.discovery_prefix}/sensor/{self.device_id}/{snap_uniq}/config"
        snap_cfg = {
            "name": "Victron Snapshot State",
            "unique_id": snap_uniq,
            "state_topic": snap_topic,
            "icon": "mdi:database-check",
            "availability_topic": f"roamcore/victron/{self.device_id}/availability",
            "device": {
                "identifiers": [self.device_id],
                "name": self.device_name,
                "model": "Victron GX (auto)",
                "manufacturer": "RoamCore",
            },
        }
        self._ha_client.publish(snap_cfg_topic, payload=json.dumps(snap_cfg), retain=True)

        # Publish discovery for all mapped entities (idempotent).
        for _, meta in self._path_to_vt.items():
            vt_key = str(meta["vt_key"])
            self._ensure_discovery_for_meta(meta, vt_key, device_instance="0")

        # Diagnostic devices sensor (count as state + full list in attributes).
        if self.publish_devices_sensor:
            self._publish_devices_discovery()
            self._publish_devices_snapshot()

        # Diagnostic topic inventory sensor (count + topic list in attributes).
        self._publish_topics_discovery()
        self._publish_topics_snapshot()

    def _publish_devices_discovery(self):
        if not self._ha_client:
            return

        uniq = f"{self.device_id}_devices"
        cfg_topic = f"{self.discovery_prefix}/sensor/{self.device_id}/{uniq}/config"
        state_topic = f"roamcore/victron/{self.device_id}/devices/count"
        attrs_topic = f"roamcore/victron/{self.device_id}/devices/attrs"

        cfg = {
            "name": "Victron Devices (discovered)",
            "unique_id": uniq,
            "state_topic": state_topic,
            "json_attributes_topic": attrs_topic,
            "icon": "mdi:devices",
            "availability_topic": f"roamcore/victron/{self.device_id}/availability",
            "device": {
                "identifiers": [self.device_id],
                "name": self.device_name,
                "model": "Victron GX (dbus-flashmq)",
                "manufacturer": "Victron Energy",
            },
        }
        self._ha_client.publish(cfg_topic, payload=json.dumps(cfg), retain=True)

    def _publish_devices_snapshot(self):
        if not self._ha_client:
            return

        # Avoid publishing huge attributes payload too often.
        now = time.time()
        if now - self._last_devices_snapshot_publish < 5:
            return
        self._last_devices_snapshot_publish = now

        # Keep attributes stable + JSON-friendly.
        devices = list(self._devices.values())
        devices.sort(key=lambda d: (str(d.get("service_type")), str(d.get("device_instance"))))
        truncated = False
        if self.devices_sensor_max > 0 and len(devices) > self.devices_sensor_max:
            devices = devices[: self.devices_sensor_max]
            truncated = True

        attrs = {"portal_id": self._portal_id, "devices": devices, "truncated": truncated}
        self._ha_client.publish(
            f"roamcore/victron/{self.device_id}/devices/count",
            payload=str(len(devices)),
            retain=True,
        )
        self._ha_client.publish(
            f"roamcore/victron/{self.device_id}/devices/attrs",
            payload=json.dumps(attrs),
            retain=True,
        )

    def _publish_topics_discovery(self) -> None:
        if not self._ha_client:
            return

        uniq = f"{self.device_id}_topics"
        cfg_topic = f"{self.discovery_prefix}/sensor/{self.device_id}/{uniq}/config"
        state_topic = f"roamcore/victron/{self.device_id}/topics/count"
        attrs_topic = f"roamcore/victron/{self.device_id}/topics/attrs"

        cfg = {
            "name": "Victron Topics (seen)",
            "unique_id": uniq,
            "state_topic": state_topic,
            "json_attributes_topic": attrs_topic,
            "icon": "mdi:format-list-bulleted",
            "availability_topic": f"roamcore/victron/{self.device_id}/availability",
            "device": {
                "identifiers": [self.device_id],
                "name": self.device_name,
                "model": "Victron GX (dbus-flashmq)",
                "manufacturer": "Victron Energy",
            },
        }
        self._ha_client.publish(cfg_topic, payload=json.dumps(cfg), retain=True)

    def _slugify(self, s: str) -> str:
        out = []
        for ch in (s or ""):
            if ch.isalnum():
                out.append(ch.lower())
            else:
                out.append("_")
        x = "".join(out)
        while "__" in x:
            x = x.replace("__", "_")
        return x.strip("_")

    def _ensure_raw_topic_entity(self, service_type: str, device_instance: str, dbus_path: str) -> None:
        """Publish a raw per-topic entity via HA MQTT Discovery (guarded by caps)."""

        if not self._ha_client:
            return
        if not self.publish_raw_topics:
            return

        key = f"{service_type}/{device_instance}/{dbus_path}".strip("/")

        # Cap entity creation to avoid blowing up HA.
        if len(self._published_raw_topics) >= self.raw_topics_max and key not in self._published_raw_topics:
            return

        # object_id must be short and stable. Use a hash of the full key to avoid huge entity_ids.
        import hashlib

        h = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
        obj = f"vt_raw_{h}"
        uniq = f"{self.device_id}_{obj}"

        if uniq in self._published_discovery_entities:
            return

        domain = "sensor"
        cfg_topic = f"{self.discovery_prefix}/{domain}/{self.device_id}/{uniq}/config"
        state_topic = f"roamcore/victron/{self.device_id}/raw/{obj}/state"
        attrs_topic = f"roamcore/victron/{self.device_id}/raw/{obj}/attrs"

        cfg: dict[str, Any] = {
            "name": f"Victron Raw {service_type}/{device_instance}/{dbus_path}",
            "unique_id": uniq,
            "object_id": obj,
            "json_attributes_topic": attrs_topic,
            "state_topic": state_topic,
            "availability_topic": f"roamcore/victron/{self.device_id}/availability",
            "icon": "mdi:code-tags",
            "device": {
                "identifiers": [self.device_id],
                "name": self.device_name,
                "model": "Victron GX (dbus-flashmq)",
                "manufacturer": "Victron Energy",
            },
        }

        self._ha_client.publish(cfg_topic, payload=json.dumps(cfg), retain=True)
        self._published_discovery_entities.add(uniq)
        self._published_raw_topics.add(key)

        # Publish metadata attributes (so we can reverse-map hash -> original topic).
        meta = {
            "service_type": service_type,
            "device_instance": device_instance,
            "dbus_path": dbus_path,
            "topic_key": key,
        }
        self._ha_client.publish(attrs_topic, payload=json.dumps(meta), retain=True)

        # Publish current state (best-effort) from our topic cache.
        rec = self._topics.get((service_type, device_instance, dbus_path))
        if rec is not None:
            sample = rec.get("sample")
            payload = "" if sample is None else str(sample)
            self._ha_client.publish(state_topic, payload=payload, retain=True)

    def _publish_topics_snapshot(self) -> None:
        if not self._ha_client:
            return

        now = time.time()
        if now - self._last_topics_snapshot_publish < 5:
            return
        self._last_topics_snapshot_publish = now

        topics = list(self._topics.values())
        topics.sort(key=lambda d: (str(d.get("service_type")), str(d.get("device_instance")), str(d.get("dbus_path"))))

        truncated = False
        if self.topics_sensor_max > 0 and len(topics) > self.topics_sensor_max:
            topics = topics[: self.topics_sensor_max]
            truncated = True

        attrs = {
            "portal_id": self._portal_id,
            "topics": topics,
            "truncated": truncated,
        }

        self._ha_client.publish(
            f"roamcore/victron/{self.device_id}/topics/count",
            payload=str(len(self._topics)),
            retain=True,
        )
        self._ha_client.publish(
            f"roamcore/victron/{self.device_id}/topics/attrs",
            payload=json.dumps(attrs),
            retain=True,
        )


def setup_logging(level: str):
    lv = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(level=lv, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


async def main():
    opts = load_options()
    setup_logging(str(opts.get("log_level", "info")))
    LOG.info("Starting RoamCore Victron Auto (DEV)")
    app = VictronAuto(opts)
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
