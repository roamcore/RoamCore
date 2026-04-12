# Teltonika (LTE/5G router for vans)

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
