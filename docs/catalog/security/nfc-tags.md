---
id: nfc-tags
title: NFC tags
support_tier: C
category: security
install_method: hacs
tags:
  - nfc
  - tag
  - scene
  - automation
  - access-control
  - phone
---

# NFC tags

## What you get

Cheap + simple NFC tags make the van feel magical: tap your phone to run a scene (Lights off, Bedtime, Leave camp).

## Prerequisites

- A working RoamCore install (Home Assistant + the RoamCore integration).
- A van — or anything with 12 V / shore power that you'd like to monitor.

## Hardware you may want

- None — uses what you already have.

## Install

- Add this repo as a **HACS custom repository** (Category: *Integration*), then install **nfc-tags**.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What the dashboard shows

- The NFC tags tile appears under **Security** in the RoamCore dashboard.
- Tiles update automatically from your upstream entities — no extra wiring required.

## Troubleshooting

- If the tile doesn't appear, restart Home Assistant and reload the RoamCore integration.
- If the upstream sensors are missing, the tile stays in its **unknown** state — that's expected.

## Links

- Source manifest: `connections/nfc-tags/connection.yml`
- Status: `recipe_published` · Support tier: **C**
