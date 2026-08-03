---
id: time-atomic
title: Time
support_tier: C
category: misc
install_method: one_line
tags:
  - time
  - atomic
  - ntp
  - gps
  - rtc
  - offline-resilience
---

# Time

## What you get

Keep HA's clock accurate even when offline (in a van with intermittent connectivity).

## Prerequisites

- A working RoamCore install (Home Assistant + the RoamCore integration).
- A van — or anything with 12 V / shore power that you'd like to monitor.

## Hardware you may want

- None — uses what you already have.

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature time-atomic`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What the dashboard shows

- The Time tile appears under **Misc** in the RoamCore dashboard.
- Tiles update automatically from your upstream entities — no extra wiring required.

## Troubleshooting

- If the tile doesn't appear, restart Home Assistant and reload the RoamCore integration.
- If the upstream sensors are missing, the tile stays in its **unknown** state — that's expected.

## Links

- Source manifest: `connections/time-atomic/connection.yml`
- Status: `recipe_published` · Support tier: **C**
