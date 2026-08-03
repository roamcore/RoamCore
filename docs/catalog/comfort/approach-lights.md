---
id: approach-lights
title: Approach lights
support_tier: B
category: comfort
install_method: one_line
tags:
  - lighting
  - light
  - switch
  - approach
  - welcome-home
  - exterior
---

# Approach lights

## What you get

Approach lights (welcome-home exterior + underbody lighting) — the universal small-comfort van automation: open the door after dark, the underbody + entry + soft-interior lights come on for a configurable duration (default 2 min) so you can see where you're stepping and feel like the van is welcoming you home.

## Prerequisites

- A working RoamCore install (Home Assistant + the RoamCore integration).
- A van — or anything with 12 V / shore power that you'd like to monitor.

## Hardware you may want

- Zigbee / Z-Wave exterior light or relay ($20–$60)
- Shelly 1 / Shelly Plus 1 ($15–$25)

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature approach-lights`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What the dashboard shows

- The Approach lights tile appears under **Comfort** in the RoamCore dashboard.
- Tiles update automatically from your upstream entities — no extra wiring required.

## Troubleshooting

- If the tile doesn't appear, restart Home Assistant and reload the RoamCore integration.
- If the upstream sensors are missing, the tile stays in its **unknown** state — that's expected.

## Links

- Source manifest: `connections/approach-lights/connection.yml`
- Status: `beta` · Support tier: **B**
