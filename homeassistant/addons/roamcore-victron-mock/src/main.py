import json
import os
import time
import urllib.request

import paho.mqtt.client as mqtt


def supervisor_mqtt_service():
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        raise RuntimeError("SUPERVISOR_TOKEN not set (did you run under with-contenv?)")
    req = urllib.request.Request(
        "http://supervisor/services/mqtt",
        headers={"Authorization": f"Bearer {token}"},
    )
    raw = urllib.request.urlopen(req, timeout=10).read().decode("utf-8")
    obj = json.loads(raw)
    return obj.get("data") or {}


def main():
    """RoamCore Victron Mock — DEV mock publisher.

    Production: invoked by HA Supervisor (OPTIONS env var carries the add-on
    config). Publishes a steady stream of Venus-style notifications so the
    roamcore-victron-auto add-on has something to consume during dev.

    Bench mode: `--bench` makes the mock publish a deterministic, monotonic
    sequence of SoC values (10 → 20 → 30 → ... → 100 → repeat) on a short
    interval. The bench test asserts that the SoC discovery/state topics
    transition as expected.
    """
    import argparse

    parser = argparse.ArgumentParser(prog="roamcore-victron-mock")
    parser.add_argument(
        "--bench",
        action="store_true",
        help=(
            "Bench mode: publish a deterministic sequence of SoC values "
            "(10..100 step 10, repeated) every --bench-interval seconds. "
            "Used by tests/ and scripts/checks/victron-bench-smoke.sh."
        ),
    )
    parser.add_argument(
        "--bench-interval",
        type=float,
        default=0.5,
        help="Bench mode: seconds between publishes (default 0.5).",
    )
    parser.add_argument(
        "--bench-iterations",
        type=int,
        default=20,
        help="Bench mode: number of publishes before exiting (default 20).",
    )
    args = parser.parse_args()

    # Options passed by Supervisor
    opts = json.loads(os.environ.get("OPTIONS", "{}"))
    portal_id = str(opts.get("portal_id") or "mock-portal")
    interval = int(opts.get("publish_interval_sec") or 5)
    retain = bool(opts.get("retain", True))

    # Bench mode overrides the steady-state publish loop with a deterministic
    # SoC walk so the bench test can assert value transitions.
    bench_mode = args.bench or bool(opts.get("bench", False))
    if bench_mode:
        interval = float(args.bench_interval)
        # Don't reach out to Supervisor for MQTT credentials in bench mode —
        # allow the MQTT_HOST / MQTT_PORT env vars (or localhost) to win.
        host = os.environ.get("MQTT_HOST") or os.environ.get("SUPERVISOR_MQTT_HOST") or "127.0.0.1"
        port = int(os.environ.get("MQTT_PORT") or os.environ.get("SUPERVISOR_MQTT_PORT") or "1883")
        username = os.environ.get("MQTT_USERNAME") or ""
        password = os.environ.get("MQTT_PASSWORD") or ""

        client = mqtt.Client(
            client_id=f"roamcore-victron-mock-bench-{portal_id}",
            protocol=mqtt.MQTTv311,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        if username:
            client.username_pw_set(username, password)
        client.connect(host, port, keepalive=30)
        client.loop_start()
        print(f"[mock bench] connected to {host}:{port} portal={portal_id}")

        def j(v):
            return json.dumps({"value": v})

        # Deterministic SoC walk: 10..100 step 10, repeating.
        soc_values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        for i in range(args.bench_iterations):
            soc = soc_values[i % len(soc_values)]
            client.publish(
                f"N/{portal_id}/system/0/Soc",
                payload=j(soc),
                qos=0,
                retain=False,
            )
            print(f"[mock bench] publish SoC={soc}")
            time.sleep(interval)

        client.loop_stop()
        client.disconnect()
        print("[mock bench] done")
        return 0

    svc = supervisor_mqtt_service()
    host = svc.get("host") or "core-mosquitto"
    port = int(svc.get("port") or 1883)
    username = svc.get("username") or ""
    password = svc.get("password") or ""

    client = mqtt.Client(
        client_id=f"roamcore-victron-mock-{portal_id}",
        protocol=mqtt.MQTTv311,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )
    if username:
        client.username_pw_set(username, password)

    client.connect(host, port, keepalive=30)
    client.loop_start()

    def j(v):
        # Venus dbus-flashmq notifications are JSON objects (usually {"value": ...}).
        return json.dumps({"value": v})

    # Minimal subset of Venus-style topics used by roamcore-victron-auto mapping.
    # These are *mock* values for dev only.
    topics = {
        # Identity-ish
        f"N/{portal_id}/system/0/Serial": j("MOCKSERIAL"),
        f"N/{portal_id}/system/0/Model": j("Cerbo GX (mock)"),
        f"N/{portal_id}/system/0/FirmwareVersion": j("v3.40~mock"),
        f"N/{portal_id}/system/0/TimeZone": j("UTC"),
        f"N/{portal_id}/system/0/State": j(1),

        # system → vt_* direct mapping examples
        f"N/{portal_id}/system/0/Dc/Battery/Voltage": j(52.3),
        f"N/{portal_id}/system/0/Dc/Battery/Current": j(-12.4),
        f"N/{portal_id}/system/0/Dc/Battery/Power": j(-650.0),
        f"N/{portal_id}/system/0/Dc/Battery/Temperature": j(24.7),
        f"N/{portal_id}/system/0/Soc": j(78.0),
        f"N/{portal_id}/system/0/Dc/Pv/Power": j(1230.0),
        f"N/{portal_id}/system/0/Dc/System/Power": j(410.0),

        # Multi-instance aggregates (VE.Bus + solarcharger)
        # Publish multiple instances so roamcore-victron-auto aggregation paths are exercised.
        f"N/{portal_id}/vebus/0/Ac/ActiveIn/P": j(980.0),
        f"N/{portal_id}/vebus/0/Ac/Out/P": j(740.0),
        f"N/{portal_id}/vebus/0/Ac/ActiveIn/Connected": j(1),
        f"N/{portal_id}/vebus/0/State": j(8),

        f"N/{portal_id}/vebus/1/Ac/ActiveIn/P": j(120.0),
        f"N/{portal_id}/vebus/1/Ac/Out/P": j(80.0),
        f"N/{portal_id}/vebus/1/Ac/ActiveIn/Connected": j(0),
        f"N/{portal_id}/vebus/1/State": j(0),

        f"N/{portal_id}/solarcharger/0/Yield/Power": j(1200.0),
        f"N/{portal_id}/solarcharger/1/Yield/Power": j(200.0),

        # Example device instance discovery signals
        f"N/{portal_id}/vebus/0/ProductId": j("0xA381"),
        f"N/{portal_id}/vebus/1/ProductId": j("0xA381"),
        f"N/{portal_id}/solarcharger/0/ProductId": j("0xA042"),
        f"N/{portal_id}/solarcharger/1/ProductId": j("0xA042"),
    }

    # Subscribe to keepalive requests and respond with full_publish_completed
    # (mimics real Venus dbus-flashmq behavior)
    def on_message(c, userdata, msg):
        topic = msg.topic or ""
        if topic == f"R/{portal_id}/keepalive":
            print(f"[mock] Received keepalive request, publishing full_publish_completed")
            # Parse keepalive-options if present
            try:
                payload = json.loads(msg.payload.decode("utf-8")) if msg.payload else {}
                opts_list = payload.get("keepalive-options", [])
                echo = None
                for opt in opts_list:
                    if isinstance(opt, dict) and "full-publish-completed-echo" in opt:
                        echo = opt["full-publish-completed-echo"]
                        break
                # Publish full_publish_completed
                resp = {"full-publish-completed-echo": echo} if echo else {}
                client.publish(
                    f"N/{portal_id}/full_publish_completed",
                    payload=json.dumps(resp),
                    qos=0,
                    retain=False,
                )
            except Exception as e:
                print(f"[mock] Error handling keepalive: {e}")
                # Still publish completion even on parse error
                client.publish(
                    f"N/{portal_id}/full_publish_completed",
                    payload="{}",
                    qos=0,
                    retain=False,
                )

    client.on_message = on_message
    client.subscribe(f"R/{portal_id}/keepalive")
    print(f"[mock] Subscribed to R/{portal_id}/keepalive")

    while True:
        now = time.time()
        # Add a changing value so it's obvious the mock is alive.
        topics[f"N/{portal_id}/system/0/Uptime"] = j(int(now))

        for t, payload in topics.items():
            client.publish(t, payload=payload, qos=0, retain=retain)
        time.sleep(interval)


if __name__ == "__main__":
    main()
