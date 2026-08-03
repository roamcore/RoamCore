# Pi-hole or AdGuard Home

Pi-hole and AdGuard Home are self-hosted DNS-level ad/tracker blockers (DNS sinkhole + blocklist + per-client query stats).

## What you need

- Z-Wave smart deadbolt (Yale / Schlage) ($120–$250)

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature dns-blocker`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What it shows on your dashboard

- Dns blocked today
- Dns blocked pct
- Dns blocker reachable
- Dns queries total
- Dns blocker enabled
- Dns resolver status
- Dns gravity updated
