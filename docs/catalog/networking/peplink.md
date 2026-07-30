# Peplink (multi-WAN router for van internet)

> **Superseded by:** `connections/peplink/` (Wave 3 #40, tier-b connection, shipped 2026-07-30).
> This legacy tier-c spec is kept for context only. Use the connection folder + recipe for current install paths.

**Support tier:** C (custom/manual)

## What this is
Peplink routers are popular in van life because they handle multi‑WAN setups (LTE/5G + Starlink + campground Wi‑Fi) and can do load‑balancing/failover.

## Why it’s useful in a van
- Automatic failover when one connection drops
- Single stable “van Wi‑Fi” network for all devices
- Better uptime for remote access and camera feeds

## Extra hardware required
- A Peplink router (model varies)

## Install / best next step
RoamCore doesn’t ship a native Peplink integration yet. The usual HA approach is:
- **SNMP** polling (signal strength, WAN status) if your Peplink exposes SNMP
- Or **HTTP/API** if available on your model

## Links
- Peplink: https://www.peplink.com/
- Home Assistant SNMP: https://www.home-assistant.io/integrations/snmp/
- Peplink InControl 2 API docs (cloud): https://www.peplink.com/ic2-api-doc/
- hass-incontrol2 (community integration): https://github.com/sneelco/hass-incontrol2
