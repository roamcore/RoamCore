---
id: motion-based-lighting
title: Motion-based lighting
support_tier: B
category: comfort
install_method: one_line
tags:
  - lighting
  - motion
  - automation
  - ignition
  - presence
  - mode-aware
---

# Motion-based lighting

!!! warning "Needs curation review"
    This entry is auto-generated from the connection manifest.
    Please review the copy before merging — Bernard has not
    blessed this wording yet.

## What you get

Motion-based lighting (driving + arrival) — the umbrella for ignition-driven interior auto-off + ignition-driven soft-interior on stop + presence-driven arrival cue + motion-driven interior camping + mode-aware Stealth suppression — is the lighting- category complement to the approach-lights Wave 3 #52 welcome-…

## Prerequisites

- A working RoamCore install (Home Assistant + the RoamCore integration).
- A van — or anything with 12 V / shore power that you'd like to monitor.

## Hardware you may want

- Zigbee / Z-Wave exterior light or relay ($20–$60)
- Shelly 1 / Shelly Plus 1 ($15–$25)

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature motion-based-lighting`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What the dashboard shows

- The Motion-based lighting tile appears under **Comfort** in the RoamCore dashboard.
- Tiles update automatically from your upstream entities — no extra wiring required.

## Troubleshooting

- If the tile doesn't appear, restart Home Assistant and reload the RoamCore integration.
- If the upstream sensors are missing, the tile stays in its **unknown** state — that's expected.

## Links

- Source manifest: `connections/motion-based-lighting/connection.yml`
- Status: `beta` · Support tier: **B**
