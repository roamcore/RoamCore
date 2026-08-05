# Peplink (multi-WAN router for van internet)

## What it does
Peplink routers are popular in van life because they handle multi‑WAN setups (LTE/5G + Starlink + campground Wi‑Fi) and can do load‑balancing/failover.

## Why it’s useful in a van
- Automatic failover when one connection drops
- Single stable “van Wi‑Fi” network for all devices
- Better uptime for remote access and camera feeds

## How to install
- A Peplink router (model varies)

RoamCore doesn’t ship a native Peplink integration yet. The usual HA approach is:
- **SNMP** polling (signal strength, WAN status) if your Peplink exposes SNMP
- Or **HTTP/API** if available on your model

## Useful links
- Peplink: https://www.peplink.com/
- Home Assistant SNMP: https://www.home-assistant.io/integrations/snmp/
- Peplink InControl 2 API docs (cloud): https://www.peplink.com/ic2-api-doc/
- hass-incontrol2 (community integration): https://github.com/sneelco/hass-incontrol2

## How it works

What RoamCore does behind the scenes.
