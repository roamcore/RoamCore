---
id: leveling
title: Leveling
support_tier: B
category: maintenance
install_method: one_line
tags:
  - leveling
  - level
  - pitch
  - roll
  - imu
  - accelerometer
---

# Leveling

## What you get

Better sleep and cooking. Quick 'good enough' check without guessing.

## Prerequisites

- A working RoamCore install (Home Assistant + the RoamCore integration).
- A van — or anything with 12 V / shore power that you'd like to monitor.

## Hardware you may want

- Phone IMU (no cost — uses the HA Companion app)
- Dedicated MPU-6050 / BNO085 IMU module ($10–$40)

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature leveling`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What the dashboard shows

- The Leveling tile appears under **Maintenance** in the RoamCore dashboard.
- Tiles update automatically from your upstream entities — no extra wiring required.

## Troubleshooting

- If the tile doesn't appear, restart Home Assistant and reload the RoamCore integration.
- If the upstream sensors are missing, the tile stays in its **unknown** state — that's expected.

## Links

- Source manifest: `connections/leveling/connection.yml`
- Status: `beta` · Support tier: **B**
