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

    # Minimal subset of Venus-style topics used by roamcore-victron-auto mapping.
    # These are *mock* values for dev only.
    topics = {
        f"N/{portal_id}/system/0/Serial": "MOCKSERIAL",
        f"N/{portal_id}/system/0/Model": "Cerbo GX (mock)",
        f"N/{portal_id}/system/0/FirmwareVersion": "v3.40~mock",
        f"N/{portal_id}/system/0/TimeZone": "UTC",
        f"N/{portal_id}/system/0/State": "1",
        # Example device instance discovery signal
        f"N/{portal_id}/vebus/0/ProductId": "0xA381",
        f"N/{portal_id}/solarcharger/0/ProductId": "0xA042",
    }

    while True:
        now = time.time()
        # Add a changing value so it's obvious the mock is alive.
        topics[f"N/{portal_id}/system/0/Uptime"] = str(int(now))

        for t, v in topics.items():
            client.publish(t, payload=str(v), qos=0, retain=retain)
        time.sleep(interval)


if __name__ == "__main__":
    main()

