# Smart Automations

Smart automations are the day-to-day convenience layer of a RoamCore van: 17 prebuilt Home Assistant automations that handle mode-aware transitions (Night Mode Stealth/Auto), power-aware responses (Low Battery Mode → Camp, Battery Full Alert, Battery Critical Alert, Solar is Crushing It), safety alerts (Inverter…

## What you need

- Nothing extra — uses what's already in the van.

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature smart-automations`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What it shows on your dashboard

- Automations enabled count
- Automations total count
- Automations missing count
- Automations all ready
- Automations view
- Automations enable all ready
- Automations disable all
- Automation night mode
- Automation auto internet failover
- Automation low battery mode
- Automation freeze protection
- Automation daily trip log
- Automation battery full alert
- Automation inverter overheat alert
- Automation router overheat alert
- Automation shore power connected
- Automation shore power disconnected
- Automation internet recovery
- Automation arrive at camp
- Automation depart travel mode
- Automation solar crushing it
- Automation battery critical alert
- Automation bedtime level check
- Automation quiet hours reminder
