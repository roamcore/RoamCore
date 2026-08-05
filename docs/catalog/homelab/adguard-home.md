# AdGuard Home (network-wide ad blocking)

>  SUPERSEDED: This legacy tier-c spec has been promoted to a tier-b connection at [`connections/dns-blocker/`](../../connections/dns-blocker/). This page is retained for historical context only. The current recipe (Pi-hole Path A + AdGuard Home Path B + DNS contract wiring + automations + troubleshooting + tier-a promotion outline) lives at [`connections/dns-blocker/docs/recipe.md`](../../connections/dns-blocker/docs/recipe.md).

## What it does
AdGuard Home is an alternative to Pi-hole: DNS-based ad/tracker blocking with a nice UI.

## Why it’s useful in a van
- Saves bandwidth
- Reduces junk traffic on constrained connections
- Easy to monitor + manage from one place

## How to install
- A device to run AdGuard Home

- Install AdGuard Home on your LAN
- Add the HA integration for monitoring/control

## Useful links
- AdGuard Home: https://github.com/AdguardTeam/AdGuardHome
- Home Assistant AdGuard Home: https://www.home-assistant.io/integrations/adguard/
- AdGuard Home overview: https://adguard.com/adguard-home/overview.html

## How it works

What RoamCore does behind the scenes.
