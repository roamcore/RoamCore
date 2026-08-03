---
id: dns-blocker
title: Pi-hole or AdGuard Home
support_tier: B
category: connectivity
install_method: one_line
tags:
  - dns
  - ad-blocker
  - pi-hole
  - adguard-home
  - networking
  - recipe
---

# Pi-hole or AdGuard Home

## What you get

Pi-hole and AdGuard Home are self-hosted DNS-level ad/tracker blockers (DNS sinkhole + blocklist + per-client query stats).

## Prerequisites

- A working RoamCore install (Home Assistant + the RoamCore integration).
- A van — or anything with 12 V / shore power that you'd like to monitor.

## Hardware you may want

- Z-Wave smart deadbolt (Yale / Schlage) ($120–$250)

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature dns-blocker`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What the dashboard shows

- The Pi-hole or AdGuard Home tile appears under **Connectivity** in the RoamCore dashboard.
- Tiles update automatically from your upstream entities — no extra wiring required.

## Troubleshooting

- If the tile doesn't appear, restart Home Assistant and reload the RoamCore integration.
- If the upstream sensors are missing, the tile stays in its **unknown** state — that's expected.

## Links

- Source manifest: `connections/dns-blocker/connection.yml`
- Status: `beta` · Support tier: **B**
