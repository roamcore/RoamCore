---
id: heated-floors
title: Heated floors + engine pre-heat
support_tier: B
category: comfort
install_method: one_line
tags:
  - hvac
  - heated-floor
  - engine-preheat
  - comfort
  - winter
  - thermostat
---

# Heated floors + engine pre-heat

!!! warning "Needs curation review"
    This entry is auto-generated from the connection manifest.
    Please review the copy before merging — Bernard has not
    blessed this wording yet.

## What you get

Heated floors + engine pre-heat — cold-weather comfort controls for vans — are the foundation of every "Warm up" automation in winter van life.

## Prerequisites

- A working RoamCore install (Home Assistant + the RoamCore integration).
- A van — or anything with 12 V / shore power that you'd like to monitor.

## Hardware you may want

- None — uses what you already have.

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature heated-floors`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What the dashboard shows

- The Heated floors + engine pre-heat tile appears under **Comfort** in the RoamCore dashboard.
- Tiles update automatically from your upstream entities — no extra wiring required.

## Troubleshooting

- If the tile doesn't appear, restart Home Assistant and reload the RoamCore integration.
- If the upstream sensors are missing, the tile stays in its **unknown** state — that's expected.

## Links

- Source manifest: `connections/heated-floors/connection.yml`
- Status: `beta` · Support tier: **B**
