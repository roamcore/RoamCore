---
id: demo_mode
title: Demo mode
support_tier: B
category: automation
install_method: one_line
tags:
  - demo-mode
  - ai
  - demo
  - show-example-values
  - missing-sensors
  - setup-flow
---

# Demo mode

!!! warning "Needs curation review"
    This entry is auto-generated from the connection manifest.
    Please review the copy before merging — Bernard has not
    blessed this wording yet.

## What you get

Demo Mode lets RoamCore show example values when critical sensors are missing, so the UI still looks and feels complete during setup or demos.

## Prerequisites

- A working RoamCore install (Home Assistant + the RoamCore integration).
- A van — or anything with 12 V / shore power that you'd like to monitor.

## Hardware you may want

- None — uses what you already have.

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature demo-mode`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What the dashboard shows

- The Demo mode tile appears under **Automation** in the RoamCore dashboard.
- Tiles update automatically from your upstream entities — no extra wiring required.

## Troubleshooting

- If the tile doesn't appear, restart Home Assistant and reload the RoamCore integration.
- If the upstream sensors are missing, the tile stays in its **unknown** state — that's expected.

## Links

- Source manifest: `connections/demo-mode/connection.yml`
- Status: `beta` · Support tier: **B**
