import asyncio
import json
import logging
import os
import socket
import time
from dataclasses import dataclass
from typing import Any, Optional

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
        self.latest: Optional[VictronTarget] = None

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
            self.latest = VictronTarget(host=host, port=port, source=f"mdns:{name}")
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
        self.victron_port = int(opts.get("victron_mqtt_port", 1883))
        self.victron_port_tls = int(opts.get("victron_mqtt_port_tls", 8883))

        self.publish_discovery = bool(opts.get("publish_discovery", True))
        self.discovery_prefix = str(opts.get("discovery_prefix", "homeassistant"))
        self.device_name = str(opts.get("device_name", "RoamCore Victron System"))
        self.device_id = str(opts.get("device_id", "roamcore-victron"))

        self._zc: Optional[Zeroconf] = None
        self._mdns_listener = MdnsMqttListener()

        self._victron: Optional[VictronTarget] = None
        self._victron_client: Optional[mqtt.Client] = None

        self._ha_client: Optional[mqtt.Client] = None

        self._last_discovery_publish = 0.0
        self._last_seen_victron_msg = 0.0

    async def run(self):
        # Start mDNS browse
        if self.prefer_mdns:
            self._zc = Zeroconf()
            ServiceBrowser(self._zc, "_mqtt._tcp.local.", handlers=[self._on_mdns])

        # Connect to HA MQTT broker (Supervisor add-on)
        await self._connect_ha_mqtt()

        while True:
            try:
                await self._tick()
            except Exception:
                LOG.exception("tick failed")
            await asyncio.sleep(self.scan_interval)

    def _on_mdns(self, zc: Zeroconf, type_: str, name: str, state_change: ServiceStateChange):
        if state_change is ServiceStateChange.Added:
            self._mdns_listener.add_service(zc, type_, name)

    async def _tick(self):
        # Choose Victron target
        target = await self._discover_target()
        if target and (self._victron is None or (target.host, target.port) != (self._victron.host, self._victron.port)):
            LOG.info("Selected Victron target: %s:%s (%s)", target.host, target.port, target.source)
            self._victron = target
            await self._connect_victron()

        # Periodically publish discovery configs (idempotent)
        if self.publish_discovery and self._ha_client and time.time() - self._last_discovery_publish > 120:
            self._publish_discovery_skeleton()
            self._last_discovery_publish = time.time()

        # If we haven't seen messages in a while, mark offline by publishing availability
        if self._ha_client and time.time() - self._last_seen_victron_msg > 30:
            self._ha_client.publish(f"roamcore/victron/{self.device_id}/availability", payload="offline", retain=True)

    async def _discover_target(self) -> Optional[VictronTarget]:
        # 1) mDNS _mqtt
        mdns = self._mdns_listener.latest
        if mdns:
            return mdns

        # 2) Try venus.local
        if self.prefer_venus_local:
            host = await self._resolve("venus.local")
            if host:
                # Probe 1883 quickly
                if await self._tcp_probe(host, self.victron_port, timeout=0.5):
                    return VictronTarget(host=host, port=self.victron_port, source="dns:venus.local")

        # TODO: ARP scan / port sweep (later)
        return None

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
        # Use Supervisor MQTT service env vars if present (Mosquitto add-on typically exposes these)
        host = os.environ.get("MQTT_HOST") or os.environ.get("SUPERVISOR_MQTT_HOST") or "core-mosquitto"
        port = int(os.environ.get("MQTT_PORT") or os.environ.get("SUPERVISOR_MQTT_PORT") or "1883")
        user = os.environ.get("MQTT_USERNAME") or os.environ.get("SUPERVISOR_MQTT_USERNAME")
        pw = os.environ.get("MQTT_PASSWORD") or os.environ.get("SUPERVISOR_MQTT_PASSWORD")

        client = mqtt.Client(client_id=f"roamcore-ha-{self.device_id}")
        if user:
            client.username_pw_set(user, pw or "")

        client.on_connect = lambda c, u, f, rc: LOG.info("Connected to HA MQTT rc=%s", rc)
        client.on_disconnect = lambda c, u, rc: LOG.warning("HA MQTT disconnected rc=%s", rc)

        # Start loop thread
        client.connect_async(host, port, keepalive=30)
        client.loop_start()
        # Best-effort wait for connection
        await asyncio.sleep(1)
        self._ha_client = client

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

        client = mqtt.Client(client_id=f"roamcore-victron-{self.device_id}")
        client.on_connect = self._on_victron_connect
        client.on_message = self._on_victron_message
        client.on_disconnect = lambda c, u, rc: LOG.warning("Victron MQTT disconnected rc=%s", rc)

        client.connect_async(self._victron.host, self._victron.port, keepalive=30)
        client.loop_start()
        await asyncio.sleep(1)
        self._victron_client = client

    def _on_victron_connect(self, client: mqtt.Client, userdata, flags, rc):
        LOG.info("Connected to Victron MQTT rc=%s", rc)
        # Subscribe broadly first; we'll tighten later
        client.subscribe("#")

    def _on_victron_message(self, client: mqtt.Client, userdata, msg):
        self._last_seen_victron_msg = time.time()
        # TODO: parse dbus-mqtt topics and map to vt_* entities
        # For now just set online
        if self._ha_client:
            self._ha_client.publish(f"roamcore/victron/{self.device_id}/availability", payload="online", retain=True)

    def _publish_discovery_skeleton(self):
        if not self._ha_client:
            return

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
