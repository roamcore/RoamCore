"""Wicann Pro (MeatPi WiCAN Pro OBD2 reader) — tier-b recipe connection.

This module is a marker-only stub. Tier-b connections don't ship native
HA integration code; they publish a recipe (docs/recipe.md) that walks the
user through the upstream MQTT or ha-wican HACS setup. The wizard reads
the manifest + recipe at runtime; the `DOMAIN` constant is the only thing
this stub needs to export so the audit + boundary CI can detect a wican-pro
folder that claims to be a connection.

The real telemetry path is:
    OBD2 port -> WiCAN Pro (ESP32) -> Wi-Fi/LAN ->
        either MQTT broker -> HA mqtt integration (rc_vehicle_* sensors)
        or     ha-wican HACS integration -> HA (wican_* sensors, mapped to rc_*)

See docs/recipe.md for the full howto.
"""

DOMAIN = "wican_pro"