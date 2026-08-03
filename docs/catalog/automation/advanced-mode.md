---
id: advanced_mode
title: Advanced mode
support_tier: B
category: automation
install_method: one_line
tags:
  - advanced-mode
  - ai
  - power-user
  - toggle
  - extra-controls
  - diagnostics
---

# Advanced mode

!!! warning "Needs curation review"
    This entry is auto-generated from the connection manifest.
    Please review the copy before merging — Bernard has not
    blessed this wording yet.

## What you get

RoamCore includes an Advanced Mode toggle that can reveal extra controls and diagnostics without cluttering the default UI. Keeps the dashboard clean for daily use. Still gives power users access to deeper controls when needed.

## Prerequisites

- A working RoamCore install (Home Assistant + the RoamCore integration).
- A van — or anything with 12 V / shore power that you'd like to monitor.

## Hardware you may want

- None — uses what you already have.

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature advanced-mode`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What the dashboard shows

- The Advanced mode tile appears under **Automation** in the RoamCore dashboard.
- Tiles update automatically from your upstream entities — no extra wiring required.

## Troubleshooting

- If the tile doesn't appear, restart Home Assistant and reload the RoamCore integration.
- If the upstream sensors are missing, the tile stays in its **unknown** state — that's expected.

## Links

- Source manifest: `connections/advanced-mode/connection.yml`
- Status: `beta` · Support tier: **B**
