# Deadbolts

Smart deadbolts — van door lock control for vans — are the "did I forget to lock the van?" answer.

## What you need

- Z-Wave smart deadbolt (Yale / Schlage) ($120–$250)

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature deadbolts`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What it shows on your dashboard

- Lock front door
- Lock side door
- Lock storage compartment
- Lock any unlocked
- Lock unlocked count
- Lock last action age min
- Lock unexpected unlock
- Lock co egress required
- Lock low voltage lockout
- Lock mode
- Lock lock all
- Lock unlock all
