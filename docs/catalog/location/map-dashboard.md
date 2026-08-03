---
id: map
title: Map dashboard
support_tier: A
category: location
install_method: one_line
tags:
  - map
  - map-dashboard
  - device_tracker
  - gps
  - tiles
  - basemap
---

# Map dashboard

!!! warning "Needs curation review"
    This entry is auto-generated from the connection manifest.
    Please review the copy before merging — Bernard has not
    blessed this wording yet.

## What you get

RoamCore provides a map experience inside Home Assistant, including current location and route/trip context. Quick 'where are we / where did we park?' view. Nice context for trips and daily travel. Extra hardware required: None if you already have a `device_tracker` or location source. Install / best next step:…

## Prerequisites

- A working RoamCore install (Home Assistant + the RoamCore integration).
- A van — or anything with 12 V / shore power that you'd like to monitor.

## Hardware you may want

- Teltonika or other GPS tracker (often already in the LTE router)

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature map-dashboard`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What the dashboard shows

- The Map dashboard tile appears under **Location** in the RoamCore dashboard.
- Tiles update automatically from your upstream entities — no extra wiring required.

## Troubleshooting

- If the tile doesn't appear, restart Home Assistant and reload the RoamCore integration.
- If the upstream sensors are missing, the tile stays in its **unknown** state — that's expected.

## Links

- Source manifest: `connections/map-dashboard/connection.yml`
- Status: `beta` · Support tier: **A**
