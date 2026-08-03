---
id: remote-access
title: Remote access
support_tier: B
category: connectivity
install_method: hacs
tags:
  - remote-access
  - tailscale
  - cloudflare-tunnel
  - nabu-casa
  - wireguard
  - mesh-vpn
---

# Remote access

## What you get

Check the van from anywhere: see sensor status, view cameras, get alerts, or (optionally) control systems.

## Prerequisites

- A working RoamCore install (Home Assistant + the RoamCore integration).
- A van — or anything with 12 V / shore power that you'd like to monitor.

## Hardware you may want

- Tailscale account (free for personal use)
- Cloudflare account for Cloudflare Tunnel (free tier)

## Install

- Add this repo as a **HACS custom repository** (Category: *Integration*), then install **remote-access**.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What the dashboard shows

- The Remote access tile appears under **Connectivity** in the RoamCore dashboard.
- Tiles update automatically from your upstream entities — no extra wiring required.

## Troubleshooting

- If the tile doesn't appear, restart Home Assistant and reload the RoamCore integration.
- If the upstream sensors are missing, the tile stays in its **unknown** state — that's expected.

## Links

- Source manifest: `connections/remote-access/connection.yml`
- Status: `beta` · Support tier: **B**
