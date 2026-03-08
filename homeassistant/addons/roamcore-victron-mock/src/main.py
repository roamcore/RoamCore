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
    # Options passed by Supervisor
    opts = json.loads(os.environ.get("OPTIONS", "{}"))
    portal_id = str(opts.get("portal_id") or "mock-portal")
    interval = int(opts.get("publish_interval_sec") or 5)
    retain = bool(opts.get("retain", True))

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
        f"N/{portal_id}/system/0/Soc": j(78.0),
        f"N/{portal_id}/system/0/Dc/Pv/Power": j(1230.0),
        f"N/{portal_id}/system/0/Dc/System/Power": j(410.0),

        # Multi-instance aggregates (VE.Bus + solarcharger)
        f"N/{portal_id}/vebus/0/Ac/ActiveIn/P": j(980.0),
        f"N/{portal_id}/vebus/0/Ac/Out/P": j(740.0),
        f"N/{portal_id}/vebus/0/Ac/ActiveIn/Connected": j(1),
        f"N/{portal_id}/solarcharger/0/Yield/Power": j(1200.0),

        # Example device instance discovery signal
        f"N/{portal_id}/vebus/0/ProductId": j("0xA381"),
        f"N/{portal_id}/solarcharger/0/ProductId": j("0xA042"),
    }

    while True:
        now = time.time()
        # Add a changing value so it's obvious the mock is alive.
        topics[f"N/{portal_id}/system/0/Uptime"] = j(int(now))

        for t, payload in topics.items():
            client.publish(t, payload=payload, qos=0, retain=retain)
        time.sleep(interval)


if __name__ == "__main__":
    main()

