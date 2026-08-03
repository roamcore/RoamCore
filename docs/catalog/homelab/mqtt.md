# MQTT (the broker everything depends on)

**Support tier:** B (Home Assistant supported)

> ⚠️ SUPERSEDED: This legacy tier-b spec has been promoted to a tier-b connection at [`connections/mqtt/`](../../connections/mqtt/). This page is retained for historical context only. The current recipe (Path A HACS mosquitto add-on + Path B external / cloud broker + Path C local container / VM broker + broker URL + broker username + TLS toggle + broker-online chip + broker-status + discovery-count + reconnect-now button + master enable + the FIVE §8 MANDATORY automations + 6 §9 troubleshooting entries + tier-a promotion outline) lives at [`connections/mqtt/docs/recipe.md`](../../connections/mqtt/docs/recipe.md).

## What this is
A lightweight pub/sub messaging layer that the upstream HA core `mqtt` integration uses for Victron GX + Teltonika + Wican Pro + Shelly + Tasmota + ESPHome + Traccar + 90%+ of IoT devices.

## Why it's useful in a van
- Vendor-neutral messaging layer — most IoT devices speak it
- Local-only broker option (HACS mosquitto add-on) keeps everything on-LAN
- Auto-discovery of upstream sensors + binary_sensors + switches + lights + covers via the canonical upstream `mqtt` discovery protocol

## Extra hardware required
- None if Path A (HACS mosquitto add-on); for Path B/C you may need a separate broker box

## Install / best next step
- Install the HACS mosquitto add-on (recommended Path A)
- Or set up an external / cloud broker (Path B) or a local container / VM broker (Path C)
- The upstream HA core `mqtt` integration will auto-detect the HACS mosquitto add-on

## Links
- Home Assistant MQTT: https://www.home-assistant.io/integrations/mqtt/
- Home Assistant MQTT discovery: https://www.home-assistant.io/docs/mqtt/discovery/
- HACS prerequisites: https://hacs.xyz/docs/setup/prerequisites