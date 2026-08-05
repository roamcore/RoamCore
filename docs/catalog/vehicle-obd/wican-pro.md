# MeatPi WiCAN Pro (OBD2 reader)

## What it does
MeatPi WiCAN Pro is an OBD2 + CAN adapter (ESP32-based) that can bring vehicle telemetry into Home Assistant: voltage, coolant temp, fault codes, trip metrics, and more (depending on vehicle support).

## Why it’s useful in a van
- Catch issues early (overheating, low voltage)
- See driving/engine data alongside house systems
- Build alerts before you end up stranded

## How to install
- An OBD2 reader (WiCAN Pro)
- A compatible vehicle (OBD2)

Two common HA approaches:
- **HACS integration (HTTP)** (recommended by the WiCAN docs): add the device by hostname/IP and pull telemetry over HTTP.
- **MQTT**: publish telemetry to your broker and optionally enable Home Assistant MQTT discovery.

## Useful links
- Product page: https://www.meatpi.com/products/wican-pro
- WiCAN docs — Home Assistant: https://meatpihq.github.io/wican-fw/home-assistant/
- ha-wican (HACS integration): https://github.com/jay-oswald/ha-wican
- WiCAN MQTT guide: https://meatpihq.github.io/wican-fw/home-assistant/mqtt/
- Home Assistant MQTT: https://www.home-assistant.io/integrations/mqtt/

## How it works

What RoamCore does behind the scenes.
