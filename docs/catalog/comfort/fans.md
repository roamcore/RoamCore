---
id: fans
title: Fans
support_tier: B
category: comfort
install_method: one_line
tags:
  - fan
  - ventilation
  - rooftop-vent
  - circulation
  - bathroom-exhaust
  - climate-aware
---

# Fans

## What you get

Fans are a simple upgrade that massively improves comfort: airflow, condensation control, cooking smells, and keeping the van livable in warm weather.

## Prerequisites

- A working RoamCore install (Home Assistant + the RoamCore integration).
- A van — or anything with 12 V / shore power that you'd like to monitor.

## Hardware you may want

- MaxxAir / Fan-Tastic rooftop vent fan ($250–$450)
- Generic 12 V circulation fan + Shelly 1 relay ($30–$80)

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature fans`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What the dashboard shows

- The Fans tile appears under **Comfort** in the RoamCore dashboard.
- Tiles update automatically from your upstream entities — no extra wiring required.

## Troubleshooting

- If the tile doesn't appear, restart Home Assistant and reload the RoamCore integration.
- If the upstream sensors are missing, the tile stays in its **unknown** state — that's expected.

## Links

- Source manifest: `connections/fans/connection.yml`
- Status: `beta` · Support tier: **B**
