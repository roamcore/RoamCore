# Map dashboard

RoamCore provides a map experience inside Home Assistant, including current location and route/trip context. Quick 'where are we / where did we park?' view. Nice context for trips and daily travel. Extra hardware required: None if you already have a `device_tracker` or location source. Install / best next step:…

## What you need

- Teltonika or other GPS tracker (often already in the LTE router)

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature map-dashboard`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What it shows on your dashboard

- A Map dashboard tile that updates automatically.
