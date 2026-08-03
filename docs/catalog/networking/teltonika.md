# Teltonika (LTE/5G router for vans)

> ⚠️ SUPERSEDED: This legacy tier-c spec has been promoted to a tier-b connection at [`connections/teltonika/`](../../connections/teltonika/) (Wave 3 #39, tier-b recipe). This page is retained for historical context only. The current recipe (SNMP wiring, REST/RMS wiring, HA helpers, reboot affordance via plug or REST, mode-aware automations, troubleshooting, tier-a promotion outline) lives at [`connections/teltonika/docs/recipe.md`](../../connections/teltonika/docs/recipe.md).

**Support tier:** C (custom/manual)

## What this is
Teltonika routers are widely used for mobile internet. They’re rugged, configurable, and often support features like VPN, SMS control, and monitoring.

## Why it’s useful in a van
- Reliable LTE/5G connectivity
- Easy to keep a consistent in‑van network
- Better remote access reliability than tethering

## Extra hardware required
- A Teltonika router (RUT series, etc.)

## Install / best next step
RoamCore doesn’t ship a native Teltonika integration yet. Common HA approaches:
- **SNMP** sensors (WAN status, signal)
- **REST** sensors / scraping if your model exposes a status endpoint

## Links
- Teltonika Networks: https://teltonika-networks.com/
- Home Assistant SNMP: https://www.home-assistant.io/integrations/snmp/
- Teltonika SNMP wiki: https://wiki.teltonika-networks.com/view/SNMP
- Teltonika developers portal (RMS/Web API): https://developers.teltonika-networks.com/
