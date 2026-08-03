---
id: bluetooth-wifi-presence
title: Bluetooth / Wi-Fi presence
support_tier: B
category: location
install_method: one_line
tags:
  - presence
  - bluetooth
  - wifi
  - device-tracker
  - person
  - recipe
---

# Bluetooth / Wi-Fi presence

!!! warning "Needs curation review"
    This entry is auto-generated from the connection manifest.
    Please review the copy before merging — Bernard has not
    blessed this wording yet.

## What you get

Presence detection — who is currently home in the van — is the foundation of every occupied/away automation in RoamCore: shut down inverter + pump when nobody is home, turn on approach lighting when the first person returns after dark, suppress Stealth-silent-hours actions when only the driver is present, alert…

## Prerequisites

- A working RoamCore install (Home Assistant + the RoamCore integration).
- A van — or anything with 12 V / shore power that you'd like to monitor.

## Hardware you may want

- None — uses what you already have.

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature bluetooth-wifi-presence`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What the dashboard shows

- The Bluetooth / Wi-Fi presence tile appears under **Location** in the RoamCore dashboard.
- Tiles update automatically from your upstream entities — no extra wiring required.

## Troubleshooting

- If the tile doesn't appear, restart Home Assistant and reload the RoamCore integration.
- If the upstream sensors are missing, the tile stays in its **unknown** state — that's expected.

## Links

- Source manifest: `connections/bluetooth-wifi-presence/connection.yml`
- Status: `beta` · Support tier: **B**
