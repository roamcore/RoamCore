---
id: music-assistant
title: Music Assistant
support_tier: B
category: comfort
install_method: hacs
tags:
  - music-assistant
  - media
  - multi-room
  - audio
  - provider-agnostic
  - spotify
---

# Music Assistant

!!! warning "Needs curation review"
    This entry is auto-generated from the connection manifest.
    Please review the copy before merging — Bernard has not
    blessed this wording yet.

## What you get

Music Assistant is a provider- agnostic multi-room audio orchestrator very popular in HA installs — it unifies Spotify, Apple Music, TuneIn/radio, local files, and Chromecast/AirPlay/Sonos receivers behind a single "play everywhere" surface with per-zone controls.

## Prerequisites

- A working RoamCore install (Home Assistant + the RoamCore integration).
- A van — or anything with 12 V / shore power that you'd like to monitor.

## Hardware you may want

- Any AirPlay / Chromecast / Snapcast-capable speaker

## Install

- Add this repo as a **HACS custom repository** (Category: *Integration*), then install **music-assistant**.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What the dashboard shows

- The Music Assistant tile appears under **Comfort** in the RoamCore dashboard.
- Tiles update automatically from your upstream entities — no extra wiring required.

## Troubleshooting

- If the tile doesn't appear, restart Home Assistant and reload the RoamCore integration.
- If the upstream sensors are missing, the tile stays in its **unknown** state — that's expected.

## Links

- Source manifest: `connections/music-assistant/connection.yml`
- Status: `beta` · Support tier: **B**
