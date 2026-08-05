# Zigbee2MQTT (Zigbee → MQTT bridge)

Use cheap Zigbee sensors and switches (Aqara, IKEA, Sonoff) with Home Assistant without buying a vendor hub.

## What it does

Zigbee2MQTT is a free bridge that lets you use cheap Zigbee devices (Aqara door sensors, IKEA bulbs, Sonoff temperature sensors, etc.) with Home Assistant without buying the vendor's proprietary hub. It runs as a Docker container with a USB Zigbee dongle and exposes every device as an MQTT topic.

## How to install

1. Buy a Zigbee USB dongle (the SONOFF Zigbee 3.0 USB Dongle Plus is the popular pick).
2. Run Zigbee2MQTT as a Docker container or HA add-on.
3. Pair devices by putting them in pairing mode; Z2M auto-discovers them and exposes them to HA via MQTT.

## How it works

Zigbee2MQTT talks to the Zigbee mesh via the USB dongle. Each paired device gets a friendly name and publishes its state to MQTT. HA's MQTT integration picks them up automatically.

## Useful links

- [Zigbee2MQTT homepage](https://www.zigbee2mqtt.io/) — official site
- [Supported devices list](https://www.zigbee2mqtt.io/supported-devices/) — what works
- [Zigbee2MQTT + HA guide](https://www.zigbee2mqtt.io/guide/usage/home-assistant.html) — setup
