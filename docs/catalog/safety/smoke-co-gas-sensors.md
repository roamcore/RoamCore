# Smoke / CO / Gas sensors

**Support tier:** B (Home Assistant supported)

## What this is
Safety sensors that trigger clear alerts when something dangerous happens: smoke, carbon monoxide, propane/LPG, or other gases.

## Why it’s useful in a van
- Early warning while sleeping
- Peace of mind when leaving pets inside (heat/CO risk)
- Can trigger loud sirens + phone notifications

## Extra hardware required
Depends on sensor type:
- **Zigbee** smoke detectors / gas sensors (various brands)
- **Z‑Wave** smoke/CO detectors
- **DIY gas sensors** (MQ series) via ESPHome

## Install / best next step
- Prefer sensors that integrate locally (Zigbee/Z‑Wave)
- For DIY gas sensors, use ESPHome and expose readings as sensors/binary sensors

## Links
- Home Assistant ZHA (Zigbee): https://www.home-assistant.io/integrations/zha/
- ESPHome (DIY sensors): https://esphome.io/
