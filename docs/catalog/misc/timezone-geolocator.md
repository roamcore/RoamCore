---
id: timezone-geolocator
title: Timezone geolocator
support_tier: C
category: misc
install_method: hacs
tags:
  - time
  - timezone
  - geolocator
  - gps
  - zone
  - travel
---

# Timezone geolocator

!!! warning "Needs curation review"
    This entry is auto-generated from the connection manifest.
    Please review the copy before merging — Bernard has not
    blessed this wording yet.

## What you get

Keep HA's system timezone correct as the van travels across regions so that time-based automations (sun events + `now` + `today_at`) keep working.

## Prerequisites

- A working RoamCore install (Home Assistant + the RoamCore integration).
- A van — or anything with 12 V / shore power that you'd like to monitor.

## Hardware you may want

- None — uses what you already have.

## Install

- Add this repo as a **HACS custom repository** (Category: *Integration*), then install **timezone-geolocator**.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What the dashboard shows

- The Timezone geolocator tile appears under **Misc** in the RoamCore dashboard.
- Tiles update automatically from your upstream entities — no extra wiring required.

## Troubleshooting

- If the tile doesn't appear, restart Home Assistant and reload the RoamCore integration.
- If the upstream sensors are missing, the tile stays in its **unknown** state — that's expected.

## Links

- Source manifest: `connections/timezone-geolocator/connection.yml`
- Status: `recipe_published` · Support tier: **C**
