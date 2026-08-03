---
id: hvac-basics
title: HVAC basics
support_tier: B
category: comfort
install_method: one_line
tags:
  - hvac
  - climate
  - thermostat
  - diesel-heater
  - webasto
  - eberspaecher
---

# HVAC basics

!!! warning "Needs curation review"
    This entry is auto-generated from the connection manifest.
    Please review the copy before merging — Bernard has not
    blessed this wording yet.

## What you get

HVAC basics — cabin heating/cooling foundations for vans — is the umbrella for thermostat + diesel heater + rooftop AC + cabin ventilation control.

## Prerequisites

- A working RoamCore install (Home Assistant + the RoamCore integration).
- A van — or anything with 12 V / shore power that you'd like to monitor.

## Hardware you may want

- None — uses what you already have.

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature hvac-basics`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What the dashboard shows

- The HVAC basics tile appears under **Comfort** in the RoamCore dashboard.
- Tiles update automatically from your upstream entities — no extra wiring required.

## Troubleshooting

- If the tile doesn't appear, restart Home Assistant and reload the RoamCore integration.
- If the upstream sensors are missing, the tile stays in its **unknown** state — that's expected.

## Links

- Source manifest: `connections/hvac-basics/connection.yml`
- Status: `beta` · Support tier: **B**
