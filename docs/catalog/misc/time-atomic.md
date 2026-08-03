# Time

Keep HA's clock accurate even when offline (in a van with intermittent connectivity).

## What you need

- Nothing extra — uses what's already in the van.

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature time-atomic`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What it shows on your dashboard

- Current
- Ntp source
- Last sync minutes ago
- Drift seconds
- Synced
- Stale
- Ntp reachable
- Rtc present
