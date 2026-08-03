---
id: nas
title: Network Attached Storage
support_tier: B
category: misc
install_method: one_line
tags:
  - nas
  - storage
  - synology
  - qnap
  - smb
  - nfs
---

# Network Attached Storage

## What you get

A NAS gives RoamCore a reliable local-storage target for media, camera footage, backups, and logs — especially valuable when you don't want to depend on cloud services.

## Prerequisites

- A working RoamCore install (Home Assistant + the RoamCore integration).
- A van — or anything with 12 V / shore power that you'd like to monitor.

## Hardware you may want

- None — uses what you already have.

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature nas`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What the dashboard shows

- The Network Attached Storage tile appears under **Misc** in the RoamCore dashboard.
- Tiles update automatically from your upstream entities — no extra wiring required.

## Troubleshooting

- If the tile doesn't appear, restart Home Assistant and reload the RoamCore integration.
- If the upstream sensors are missing, the tile stays in its **unknown** state — that's expected.

## Links

- Source manifest: `connections/nas/connection.yml`
- Status: `beta` · Support tier: **B**
