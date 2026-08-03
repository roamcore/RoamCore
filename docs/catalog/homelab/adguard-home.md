# AdGuard Home (network-wide ad blocking)

**Support tier:** B (Home Assistant supported)

> ⚠️ SUPERSEDED: This legacy tier-c spec has been promoted to a tier-b connection at [`connections/dns-blocker/`](../../../connections/dns-blocker/). This page is retained for historical context only. The current recipe (Pi-hole Path A + AdGuard Home Path B + DNS contract wiring + automations + troubleshooting + tier-a promotion outline) lives at [`connections/dns-blocker/docs/recipe.md`](../../../connections/dns-blocker/docs/recipe.md).

## What this is
AdGuard Home is an alternative to Pi-hole: DNS-based ad/tracker blocking with a nice UI.

## Why it’s useful in a van
- Saves bandwidth
- Reduces junk traffic on constrained connections
- Easy to monitor + manage from one place

## Extra hardware required
- A device to run AdGuard Home

## Install / best next step
- Install AdGuard Home on your LAN
- Add the HA integration for monitoring/control

## Links
- AdGuard Home: https://github.com/AdguardTeam/AdGuardHome
- Home Assistant AdGuard Home: https://www.home-assistant.io/integrations/adguard/
- AdGuard Home overview: https://adguard.com/adguard-home/overview.html
