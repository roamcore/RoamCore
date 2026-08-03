---
id: mock-location-and-tracks
title: Mock location + track replay
support_tier: A
category: location
install_method: manual
tags:
  - map
  - mock
  - dev
  - demo
  - polyline
  - trip
---

# Mock location + track replay

!!! warning "Needs curation review"
    This entry is auto-generated from the connection manifest.
    Please review the copy before merging — Bernard has not
    blessed this wording yet.

## What you get

Mock location + track replay is the dev/demo polyline generator for the RoamCore map page.

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

- The Mock location + track replay tile appears under **Location** in the RoamCore dashboard.
- Tiles update automatically from your upstream entities — no extra wiring required.

## Troubleshooting

- If the tile doesn't appear, restart Home Assistant and reload the RoamCore integration.
- If the upstream sensors are missing, the tile stays in its **unknown** state — that's expected.

## Links

- Source manifest: `connections/mock-location-and-tracks/connection.yml`
- Status: `beta` · Support tier: **A**
