---
id: starlink
title: Starlink
support_tier: B
category: connectivity
install_method: manual
tags:
  - starlink
  - networking
  - sleep-timer
  - mobile-internet
  - recipe
---

# Starlink

## What you get

Starlink is a self-hosted mobile-internet terminal (Gen-2/Gen-3 dish + router).

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

- The Starlink tile appears under **Connectivity** in the RoamCore dashboard.
- Tiles update automatically from your upstream entities — no extra wiring required.

## Troubleshooting

- If the tile doesn't appear, restart Home Assistant and reload the RoamCore integration.
- If the upstream sensors are missing, the tile stays in its **unknown** state — that's expected.

## Links

- Source manifest: `connections/starlink/connection.yml`
- Status: `beta` · Support tier: **B**
