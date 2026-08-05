# Time (atomic) — NTP-synchronized time with offline-resilience

> **SUPERSEDED** by `connections/time-atomic/` (Wave 3 #55, shipped 2026-08-02).

## What it does
RoamCore includes notes for keeping HA's clock accurate even when offline
(in a van with intermittent connectivity). The recipe recycles the
upstream HA core `time` integration (since 2022.x — exposes NTP
servers + `sensor.time` + `sensor.date` + date/time helpers) +
a thin RoamCore automation wrapper that runs the THREE §7
automations (NTP cadence refresh on boot + GPS time correction on
`device_tracker` + timezone change + RTC fallback when NTP
unreachable for N minutes).

## Why it's useful in a van
- The van can lose LTE / Starlink for hours — the recipe's Path C
  RTC fallback (DS3231 / RV-3028 I2C RTC module on the van's NUC /
  SBC + the SBC's `systemd-timesyncd` fallback config) keeps
  accurate time even when offline
- GPS satellites carry atomic-clock-grade time signals — the
  recipe's Path B GPS time correction (Traccar Wave 3 #36 / HA
  Companion app / Wican Pro Wave 3 #6 OBD-II's GPS feed) uses GPS
  time when NTP is unreachable but GPS is
- NTP is the canonical time-sync mechanism when the WAN is
  reachable — the recipe's Path A NTP uses HA core's `time`
  integration with the recommended NTP server list
  (`time.cloudflare.com` + `time.google.com` + `pool.ntp.org`)

## How to install
- Optional: DS3231 / RV-3028 I2C RTC module for Path C RTC
  fallback (otherwise the recipe relies on Path A NTP + Path B
  GPS only)
- Optional: Traccar Wave 3 #36 server OR HA Companion app OR
  Wican Pro Wave 3 #6 OBD-II reader for Path B GPS time
  correction (otherwise the recipe relies on Path A NTP + Path C
  RTC only)
- No extra hardware required for Path A NTP (just HA core's
  `time` integration + the WAN backhaul)

- See: `connections/time-atomic/docs/recipe.md`
- RoamCore time helpers package: `homeassistant/packages/roamcore_weather_time.yaml`

## Useful links
- HA core `time` integration: https://www.home-assistant.io/integrations/time/
- Cross-reference to Wave 3 #54 timezone-geolocator (the
  time-category complement — handles "what timezone IS it?"; this
  slice handles "what time IS it?"):
  `connections/timezone-geolocator/`
- Cross-reference to Traccar Wave 3 #36 (the canonical GPS source
  for Path B GPS time correction): `connections/traccar/`
- Cross-reference to Wican Pro Wave 3 #6 (the optional OBD-II
  GPS source for Path B GPS time correction):
  `connections/wican-pro/`

## How it works

What RoamCore does behind the scenes.
