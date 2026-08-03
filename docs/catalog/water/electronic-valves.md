---
id: electronic-valves
title: Electronic valves + auto tank switching
support_tier: B
category: water
install_method: one_line
tags:
  - valve
  - water
  - fresh
  - grey
  - tank
  - switch
---

# Electronic valves + auto tank switching

!!! warning "Needs curation review"
    This entry is auto-generated from the connection manifest.
    Please review the copy before merging — Bernard has not
    blessed this wording yet.

## What you get

Electronic valves + auto tank switching — fresh / aux tank routing, grey drain valve auto-close, freeze-risk / leak-detected / low- voltage lockout safety interlocks — is the vendor-neutral surface that turns "which tank am I drawing from right now?" + "is the grey valve about to overflow?" + "can I safely open a…

## Prerequisites

- A working RoamCore install (Home Assistant + the RoamCore integration).
- A van — or anything with 12 V / shore power that you'd like to monitor.

## Hardware you may want

- None — uses what you already have.

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature electronic-valves`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What the dashboard shows

- The Electronic valves + auto tank switching tile appears under **Water** in the RoamCore dashboard.
- Tiles update automatically from your upstream entities — no extra wiring required.

## Troubleshooting

- If the tile doesn't appear, restart Home Assistant and reload the RoamCore integration.
- If the upstream sensors are missing, the tile stays in its **unknown** state — that's expected.

## Links

- Source manifest: `connections/electronic-valves/connection.yml`
- Status: `beta` · Support tier: **B**
