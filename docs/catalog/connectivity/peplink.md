---
id: peplink
title: Peplink
support_tier: B
category: connectivity
install_method: manual
tags:
  - peplink
  - networking
  - multi-wan
  - failover
  - load-balance
  - router
---

# Peplink

## What you get

Peplink Balance / MAX / EP-series routers are rugged, configurable multi-WAN gateways very popular in van life — they handle LTE/5G + Starlink + campground Wi-Fi with automatic failover and load balancing, giving a single stable "van Wi-Fi" network.

## Prerequisites

- A working RoamCore install (Home Assistant + the RoamCore integration).
- A van — or anything with 12 V / shore power that you'd like to monitor.

## Hardware you may want

- None — uses what you already have.

## Install

- Follow the **Setup** steps in the recipe — this is a manual install that wires a few entities together.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What the dashboard shows

- The Peplink tile appears under **Connectivity** in the RoamCore dashboard.
- Tiles update automatically from your upstream entities — no extra wiring required.

## Troubleshooting

- If the tile doesn't appear, restart Home Assistant and reload the RoamCore integration.
- If the upstream sensors are missing, the tile stays in its **unknown** state — that's expected.

## Links

- Source manifest: `connections/peplink/connection.yml`
- Status: `beta` · Support tier: **B**
