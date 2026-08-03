# Approach lights

Approach lights (welcome-home exterior + underbody lighting) — the universal small-comfort van automation: open the door after dark, the underbody + entry + soft-interior lights come on for a configurable duration (default 2 min) so you can see where you're stepping and feel like the van is welcoming you home.

## What you need

- Zigbee / Z-Wave exterior light or relay ($20–$60)
- Shelly 1 / Shelly Plus 1 ($15–$25)

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature approach-lights`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What it shows on your dashboard

- A Approach lights tile that updates automatically.
