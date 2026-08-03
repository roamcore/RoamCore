# Smoke / CO / Gas sensors

> **Replaced by:** `connections/smoke-co-gas-sensors/` (Wave 3 #45,
> tier-b recipe connection, 2026-07-30). This catalog page is the
> legacy tier-c spec; the connection folder is the source of truth
> for the install + recipe + vendor-neutral contract tiles.
> See `connections/smoke-co-gas-sensors/` for the canonical `rc_safety_*`
> contract tiles (12 vendor-neutral tiles: `binary_sensor.rc_safety_smoke_detected`
> / `_co_detected` / `_gas_detected` / `_any_alarm_active` / `_siren_active`
> / `_alarm_in_test_mode` / `_low_battery_warning` / `_sensor_offline`
> + `sensor.rc_safety_lowest_battery_pct` + `button.rc_safety_silence_alarm`
> + `button.rc_safety_test_alarm` + `select.rc_safety_alarm_mode`) +
> the full howto at
> `connections/smoke-co-gas-sensors/docs/recipe.md`.

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
- ESPHome ADC sensor (for MQ-series analog sensors): https://esphome.io/components/sensor/adc.html
