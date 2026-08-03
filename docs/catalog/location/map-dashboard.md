# Map dashboard

Map dashboard — vendor-neutral map tile + device_tracker aggregation + trip overlay + offline-tile cache.

## What you need

- Teltonika or other GPS tracker (often already in the LTE router)

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature map-dashboard`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What it shows on your dashboard

- Device tracker
- Latitude
- Longitude
- Accuracy meters
- Speed kph
- Bearing degrees
- Has fix
- Internet reachable for tiles
- Basemap mode
- Trip overlay
