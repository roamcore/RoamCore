"""Shared pytest fixtures for the Victron Auto bench test suite.

This bench exists to *prove the integration works end-to-end on a dev box or in
CI*. We do NOT mock the assertion under test — the addon publishes real MQTT
messages on a real broker, and the tests subscribe to that broker and assert
what they actually see.

Broker strategy (in order of preference):
  1. `mosquitto` binary on PATH  (fastest, smallest)
  2. `amqtt` (pure-Python) broker embedded in-process  (used by CI / dev hosts)

The fixture transparently picks whichever is available and bails out with a
clear SKIP message if neither is installed (so the suite never silently passes
on a host that can't actually run it).
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Iterator, Optional

import pytest

# `asyncio` is referenced inside _AmqttBroker.start(); import here so the
# import is in scope at runtime even though we use `_asyncio` locally to avoid
# shadowing in nested scopes.
import asyncio

# Make the addon's src/ importable without installing it.
ADDON_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ADDON_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


# ---------------------------------------------------------------------------
# Broker fixture
# ---------------------------------------------------------------------------


class _AmqttBroker:
    """In-process amqtt broker (pure Python, no external binary)."""

    def __init__(self, port: int) -> None:
        self.port = port
        self._loop: Optional[asyncio.AbstractEventLoop] = None  # type: ignore[name-defined]
        self._thread: Optional[threading.Thread] = None
        self._stopped = threading.Event()
        self._ready = threading.Event()
        self._err: Optional[BaseException] = None

    def start(self) -> None:
        # amqtt is asyncio-only; we run it on a dedicated thread + loop.
        import asyncio as _asyncio  # local import keeps test collection fast

        def _runner() -> None:
            try:
                self._loop = _asyncio.new_event_loop()
                _asyncio.set_event_loop(self._loop)
                self._loop.run_until_complete(self._serve())
            except BaseException as e:  # noqa: BLE001
                self._err = e
                self._ready.set()

        self._thread = threading.Thread(target=_runner, name="amqtt-broker", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=10):
            raise RuntimeError("amqtt broker did not signal ready within 10s")
        if self._err is not None:
            raise RuntimeError(f"amqtt broker failed to start: {self._err}")
        # Tiny grace period so the listener is fully accepting connections.
        time.sleep(0.2)

    async def _serve(self) -> None:
        # Lazy import so missing amqtt only fails when this fixture is used.
        import asyncio as _asyncio
        import socket as _socket
        from amqtt.broker import Broker

        broker = Broker(
            {
                "listeners": {
                    "default": {"type": "tcp", "bind": f"127.0.0.1:{self.port}"},
                },
                "auth": {"allow-anonymous": True},
                # Disable the periodic sys plugin to avoid a known amqtt bug on 0.11
                # that raises TypeError when sys_interval is None.
                "sys_interval": 0,
            }
        )
        await broker.start()
        # Wait until the broker is actually accepting TCP connections. amqtt 0.11
        # sometimes returns from broker.start() before the listener is ready, and
        # in the recovery test we restart the broker in the same process — the
        # OS-level TIME_WAIT can cause a brief bind gap. Poll the socket until
        # we get a clean connect, then claim ready.
        for _ in range(100):
            try:
                with _socket.create_connection(("127.0.0.1", self.port), timeout=0.1):
                    break
            except OSError:
                await _asyncio.sleep(0.1)
        # Extra grace so the MQTT protocol layer is ready (amqtt sometimes
        # accepts the socket but rejects CONNACK for ~100ms).
        await _asyncio.sleep(0.3)
        self._ready.set()
        # Wait for stop signal
        while not self._stopped.is_set():
            await _asyncio.sleep(0.2)
        await broker.shutdown()

    def stop(self) -> None:
        self._stopped.set()
        if self._thread:
            self._thread.join(timeout=5)


class _MosquittoBroker:
    """External mosquitto subprocess wrapper."""

    def __init__(self, port: int) -> None:
        self.port = port
        self._proc: Optional[subprocess.Popen[bytes]] = None
        self._log = open("/tmp/roamcore-victron-bench-mosquitto.log", "wb")  # noqa: SIM115

    def start(self) -> None:
        assert shutil.which("mosquitto"), "mosquitto not on PATH"
        self._proc = subprocess.Popen(
            [
                "mosquitto",
                "-p",
                str(self.port),
                "-i",
                f"bench-{self.port}",
                # Anonymous + no encryption: this is the bench broker, not a public one.
            ],
            stdout=self._log,
            stderr=subprocess.STDOUT,
        )
        # Poll for accept()
        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.2):
                    return
            except OSError:
                if self._proc.poll() is not None:
                    raise RuntimeError("mosquitto exited before accepting connections")
                time.sleep(0.1)
        raise RuntimeError("mosquitto did not start listening within 5s")

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        try:
            self._log.close()
        except Exception:
            pass


@pytest.fixture(scope="session")
def mqtt_broker() -> Iterator[Any]:
    """Yield a live MQTT broker bound to 127.0.0.1:<random port>.

    Tries `mosquitto` first (smaller, faster). Falls back to amqtt. Skips with a
    clear message if neither is available.
    """
    port = _free_port()

    impl: Optional[Any] = None
    if shutil.which("mosquitto"):
        impl = _MosquittoBroker(port)
        impl.start()
        impl_type = "mosquitto"
    else:
        try:
            import amqtt  # noqa: F401
        except ImportError:
            pytest.skip(
                "SKIP — no MQTT broker available. Install `mosquitto` (binary) or "
                "`pip install amqtt` to run the bench suite. See "
                "homeassistant/addons/roamcore-victron-auto/tests/README.md."
            )
        impl = _AmqttBroker(port)
        impl.start()
        impl_type = "amqtt"

    info = {"port": port, "host": "127.0.0.1", "impl": impl_type}
    try:
        yield info
    finally:
        impl.stop()


# ---------------------------------------------------------------------------
# Discovery recorder
# ---------------------------------------------------------------------------


@pytest.fixture
def ha_discovery_recorder(mqtt_broker: Any) -> Iterator[Any]:
    """Subscribe to `homeassistant/+/+/config` and record every discovery payload.

    Yields a dict-like recorder. The bench test publishes to MQTT, the recorder
    collects whatever the addon publishes, and the assertion code reads it.
    """
    import paho.mqtt.client as mqtt

    seen: dict[str, dict[str, Any]] = {}
    state_seen: dict[str, str] = {}
    raw_messages: list[tuple[str, str]] = []

    client = mqtt.Client(
        client_id=f"bench-recorder-{os.getpid()}",
        protocol=mqtt.MQTTv311,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )

    def on_message(c, u, msg):
        topic = msg.topic
        try:
            payload = msg.payload.decode("utf-8") if msg.payload else ""
        except Exception:
            payload = ""
        raw_messages.append((topic, payload))
        if topic.startswith("homeassistant/") and topic.endswith("/config"):
            try:
                seen[topic] = __import__("json").loads(payload)
            except Exception:
                seen[topic] = {"_raw": payload}
        else:
            # Capture state topics for round-trip tests.
            if "/state" in topic:
                state_seen[topic] = payload

    client.on_message = on_message
    client.connect(mqtt_broker["host"], mqtt_broker["port"], keepalive=30)
    client.loop_start()
    client.subscribe("homeassistant/#", qos=0)
    client.subscribe("roamcore/victron/#", qos=0)
    # Brief settle so subscription is registered before any publishes.
    time.sleep(0.2)

    recorder = {
        "discovery": seen,
        "state": state_seen,
        "raw": raw_messages,
        "_client": client,
    }
    try:
        yield recorder
    finally:
        try:
            client.loop_stop()
            client.disconnect()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# VictronAuto instance
# ---------------------------------------------------------------------------


@pytest.fixture
def victron_auto_instance(mqtt_broker: Any) -> Iterator[Any]:
    """Construct a VictronAuto pointed at the local bench broker.

    The fixture also attaches an injected HA MQTT client and clears options that
    would try to reach out to the LAN (mdns, venus.local). Bench tests get a
    fully-formed app they can drive directly.
    """
    from main import VictronAuto  # type: ignore[import-not-found]

    opts: dict[str, Any] = {
        "bench": True,
        "victron_host": mqtt_broker["host"],
        "victron_mqtt_port": mqtt_broker["port"],
        "victron_use_tls": False,
        # In bench mode the HA MQTT broker IS the same broker as Victron
        # (both are local — the bench fixture runs one broker for everything).
        # Point the bench HA client at the same broker.
        "bench_ha_host": mqtt_broker["host"],
        "bench_ha_port": mqtt_broker["port"],
        # Short timings so the bench doesn't sleep for seconds.
        "scan_interval_sec": 1,
        "mqtt_connect_timeout_sec": 3,
        "publish_discovery": True,
        "publish_devices_sensor": True,
        "publish_raw_topics": False,
        "discovery_prefix": "homeassistant",
        "device_name": "Victron Bench",
        "device_id": "victron-bench",
        # Disable LAN discovery / probes — pure localhost test.
        "prefer_mdns": False,
        "prefer_venus_local": False,
        "summary_log_interval_sec": 0,
        "log_level": "warning",
        "raw_topics_max": 0,  # suppress the validation warning noise
    }
    app = VictronAuto(opts)
    yield app


# ---------------------------------------------------------------------------
# Convenience: connect both clients for tests that need a full ready state
# ---------------------------------------------------------------------------


@pytest.fixture
async def victron_connected(mqtt_broker: Any, victron_auto_instance: Any) -> Iterator[Any]:
    """Connect both VictronAuto HA + Victron MQTT clients to the bench broker.

    Yields the app once both clients are connected. Cleans up on teardown.
    """
    import asyncio

    app = victron_auto_instance

    # HA MQTT — bench path (skips Supervisor)
    await app._bench_connect_ha_mqtt_local()
    # Victron MQTT
    target = await app._discover_target()
    assert target is not None, "Bench broker should be discoverable as Victron target"
    app._victron = target
    await app._connect_victron()
    assert app._victron_client is not None, "Victron MQTT should be connected"

    # Publish discovery skeleton
    app._publish_discovery_skeleton()
    app._last_discovery_publish = time.time()
    app._publish_status_topics(force=True)

    yield app

    # Teardown
    try:
        if app._victron_client:
            app._victron_client.loop_stop()
            try:
                app._victron_client.disconnect()
            except Exception:
                pass
    except Exception:
        pass
    try:
        if app._ha_client:
            app._ha_client.loop_stop()
            try:
                app._ha_client.disconnect()
            except Exception:
                pass
    except Exception:
        pass
