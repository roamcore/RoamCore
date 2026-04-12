# Deadbolts (smart locks)

**Support tier:** B (Home Assistant supported)

## What this is
Smart deadbolts let you monitor lock state (locked/unlocked) and (optionally) control it from Home Assistant.

## Why it’s useful in a van
- Quick “is the van locked?” check from bed
- Get alerts if it unlocks unexpectedly
- Can tie into “Away mode” / night routines

## Extra hardware required
Varies by lock:
- **Z‑Wave lock** → Z‑Wave controller + Z‑Wave JS
- **Zigbee lock** → Zigbee coordinator + ZHA/Zigbee2MQTT
- **Thread/Matter** locks → Thread border router

## Install / best next step
- Decide your ecosystem (Z‑Wave is common for locks)
- Add the lock to Home Assistant, then expose a simple lock tile on your dashboard

## Links
- Home Assistant Z‑Wave JS: https://www.home-assistant.io/integrations/zwave_js/
- Home Assistant ZHA (Zigbee): https://www.home-assistant.io/integrations/zha/
