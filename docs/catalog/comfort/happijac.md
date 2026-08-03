---
id: happijac
title: Happijac bed lift
support_tier: B
category: comfort
install_method: one_line
tags:
  - bed-lift
  - happijac
  - safety
  - cover
  - relay
  - esphome
---

# Happijac bed lift

!!! warning "Needs curation review"
    This entry is auto-generated from the connection manifest.
    Please review the copy before merging — Bernard has not
    blessed this wording yet.

## What you get

Bed lift control — van bed up / down — is the foundation of every sleep-cycle automation in a van with a Happijac (or any 2-relay + 2-limit-switch bed lift: LCI Happijac, DIY linear actuators, winch + strap, etc.

## Prerequisites

- A working RoamCore install (Home Assistant + the RoamCore integration).
- A van — or anything with 12 V / shore power that you'd like to monitor.

## Hardware you may want

- None — uses what you already have.

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature happijac`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What the dashboard shows

- The Happijac bed lift tile appears under **Comfort** in the RoamCore dashboard.
- Tiles update automatically from your upstream entities — no extra wiring required.

## Troubleshooting

- If the tile doesn't appear, restart Home Assistant and reload the RoamCore integration.
- If the upstream sensors are missing, the tile stays in its **unknown** state — that's expected.

## Links

- Source manifest: `connections/happijac/connection.yml`
- Status: `beta` · Support tier: **B**
