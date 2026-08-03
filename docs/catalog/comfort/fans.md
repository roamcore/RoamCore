# Fans

Fans (vendor-neutral fan-controller umbrella for HA, covering rooftop vent fans + circulation fans + bathroom exhaust fans — rooftop + circulation fans cover the climate-aware airflow + the rain-sensor safety block; bathroom exhaust fans wire as a separate downstream `fan.

## What you need

- MaxxAir / Fan-Tastic rooftop vent fan ($250–$450)
- Generic 12 V circulation fan + Shelly 1 relay ($30–$80)

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature fans`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What it shows on your dashboard

- Main
- Speed percent
- Mode
- Active
- Runtime minutes today
- Last trigger reason
- Run now 15min
- Rain sensor active
