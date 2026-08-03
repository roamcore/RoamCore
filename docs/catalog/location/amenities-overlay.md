---
id: amenities_overlay
title: Amenities overlay
support_tier: B
category: location
install_method: one_line
tags:
  - amenities-overlay
  - map
  - poi
  - nearby-places
  - overpass
  - openstreetmap
---

# Amenities overlay

## What you get

Amenities overlay (nearby places) — See nearby things you actually care about when living on the road — water taps, laundrettes, gyms, dump points, campsites, supermarkets, and more — directly on the RoamCore map.

## Prerequisites

- A working RoamCore install (Home Assistant + the RoamCore integration).
- A van — or anything with 12 V / shore power that you'd like to monitor.

## Hardware you may want

- None — uses what you already have.

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature amenities-overlay`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What the dashboard shows

- The Amenities overlay tile appears under **Location** in the RoamCore dashboard.
- Tiles update automatically from your upstream entities — no extra wiring required.

## Troubleshooting

- If the tile doesn't appear, restart Home Assistant and reload the RoamCore integration.
- If the upstream sensors are missing, the tile stays in its **unknown** state — that's expected.

## Links

- Source manifest: `connections/amenities-overlay/connection.yml`
- Status: `beta` · Support tier: **B**
