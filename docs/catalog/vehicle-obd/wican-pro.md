# MeatPi WiCAN Pro (OBD2 reader)

**Support tier:** C (custom/manual)

## What this is
An OBD2 reader can bring vehicle telemetry into Home Assistant (where supported): voltage, coolant temp, fault codes, trip metrics, etc. The exact integration path depends on how the device exposes data (Bluetooth/Wi‑Fi/MQTT/API).

## Why it’s useful in a van
- Catch issues early (overheating, low voltage)
- See driving/engine data alongside house systems
- Build alerts before you end up stranded

## Extra hardware required
- An OBD2 reader (WiCAN Pro)
- A compatible vehicle (OBD2)

## Install / best next step
If you can get the device to output via a standard method, HA can ingest it:
- MQTT (ideal)
- REST sensors
- Or a supported OBD integration if you run it locally

## Links
- Home Assistant OBD-II: https://www.home-assistant.io/integrations/obd2/
- Home Assistant MQTT: https://www.home-assistant.io/integrations/mqtt/
