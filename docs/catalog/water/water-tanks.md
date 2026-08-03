# Water tanks

Water tanks — fresh + grey water telemetry + pump runtime + leak detection + freeze-risk monitoring for vans.

## What you need

- SeeLevel / Garnet tank sensor ($80–$200)
- 12 V solenoid valve ($25–$60)

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature water-tanks`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What it shows on your dashboard

- Fresh level pct
- Fresh level l
- Fresh days remaining
- Grey level pct
- Grey level l
- Grey full warning
- Fresh low warning
- Fresh empty warning
- Pump running
- Pump runtime min last 24h
- Pump running too long
- Leak detected
- Freeze risk
- Fresh temperature c
- Fresh tank size l
- Grey tank size l
- Mode
