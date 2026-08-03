---
id: in-cab-tablet-dashboard
title: In-cab tablet dashboard
support_tier: C
category: maintenance
install_method: manual
tags:
  - vehicle
  - in-cab
  - tablet
  - dashboard
  - driving
  - arrival
---

# In-cab tablet dashboard

!!! warning "Needs curation review"
    This entry is auto-generated from the connection manifest.
    Please review the copy before merging — Bernard has not
    blessed this wording yet.

## What you get

Mount a small tablet in the cab that shows the handful of controls and readouts you care about while driving + a richer control surface on arrival + a battery-friendly lock screen while parked.

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

- The In-cab tablet dashboard tile appears under **Maintenance** in the RoamCore dashboard.
- Tiles update automatically from your upstream entities — no extra wiring required.

## Troubleshooting

- If the tile doesn't appear, restart Home Assistant and reload the RoamCore integration.
- If the upstream sensors are missing, the tile stays in its **unknown** state — that's expected.

## Links

- Source manifest: `connections/in-cab-tablet-dashboard/connection.yml`
- Status: `recipe_published` · Support tier: **C**
