# Timezone geolocator

Keep HA's system timezone correct as the van travels across regions so that time-based automations (sun events + `now` + `today_at`) keep working.

## What you need

- Nothing extra — uses what's already in the van.

## Install

- Add this repo as a **HACS custom repository** (Category: *Integration*), then install **timezone-geolocator**.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What it shows on your dashboard

- A Timezone geolocator tile that updates automatically.
