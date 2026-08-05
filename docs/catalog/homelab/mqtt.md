# Mosquitto (MQTT broker)

Lightweight message bus for IoT — Shelly, Tasmota, ESPHome, Victron, and most "smart" devices speak MQTT.

## What it does

MQTT is a lightweight message bus that IoT devices use to publish their state and subscribe to commands. Most DIY van sensors (Shelly relays, Tasmota-flashed devices, ESPHome boards, Victron kits) talk MQTT. A broker (typically Mosquitto) runs on your network and relays messages between them. Home Assistant also speaks MQTT and can mirror every device into a clean entity.

## How to install

1. The official Mosquitto add-on installs in one click from the Home Assistant Add-on Store.
2. Default port is 1883. Devices on the same network can publish without extra config.
3. Set a username and password — MQTT has no security otherwise.

## How it works

Devices connect to the broker and either publish state (e.g. `shellies/living-room/light/state → ON`) or subscribe to commands (e.g. `shellies/living-room/light/command ← OFF`). Home Assistant subscribes to everything and shows each topic as an entity.

## Useful links

- [MQTT spec](https://mqtt.org/) — what MQTT actually is
- [Mosquitto add-on docs](https://github.com/home-assistant/addons/blob/master/mosquitto/DOCS.md) — official HA install
- [MQTT integration in HA](https://www.home-assistant.io/integrations/mqtt/) — auto-discovery explained
