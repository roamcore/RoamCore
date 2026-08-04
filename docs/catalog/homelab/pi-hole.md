# Pi-hole (network-wide ad blocking)

**Support tier:** B (Home Assistant supported)

> ⚠️ SUPERSEDED: This legacy tier-c spec has been promoted to a tier-b connection at [`connections/dns-blocker/`](../../../connections/dns-blocker/). This page is retained for historical context only. The current recipe (Pi-hole Path A + AdGuard Home Path B + DNS contract wiring + automations + troubleshooting + tier-a promotion outline) lives at [`connections/dns-blocker/docs/recipe.md`](../../../connections/dns-blocker/docs/recipe.md).

## What this is
Pi-hole blocks ads and trackers for every device on your network by acting as DNS.

## Why it’s useful in a van
- Less bandwidth wasted (important on LTE/Starlink)
- Faster browsing on weak connections
- Simple “is DNS healthy?” monitoring

## Extra hardware required
- A device to run Pi-hole (mini PC, Raspberry Pi, VM, etc.)

## Install / best next step
- Install Pi-hole on your LAN
- Add the HA integration for status + stats

## Links
- Pi-hole: https://pi-hole.net/
- Home Assistant Pi-hole: https://www.home-assistant.io/integrations/pi_hole/
