# Timezone geolocator

> **SUPERSEDED — Wave 3 (2026-08-02).** This legacy tier-c placeholder spec has been promoted to a tier-c recipe connection at [`connections/timezone-geolocator/`](../../../connections/timezone-geolocator/). The new connection ships a vendor-neutral GPS-driven timezone recipe over the upstream HA Companion + HA Traccar + browser geolocation + GPS-from-network-location. The legacy tier-c content below is preserved for historical context only — do NOT wire a new install from this doc; use the recipe in the connection folder.

**Replaced by:** [`connections/timezone-geolocator/`](../../../connections/timezone-geolocator/)

**Recipe:** [`connections/timezone-geolocator/docs/recipe.md`](../../../connections/timezone-geolocator/docs/recipe.md)

---

Keep HA's system timezone correct as the van travels across regions so that time-based automations (sun events + `now` + `today_at`) keep working.

## What you need

- Nothing extra — uses what's already in the van.

## Install

- Add this repo as a **HACS custom repository** (Category: *Integration*), then install **timezone-geolocator**.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What it shows on your dashboard

- A Timezone geolocator tile that updates automatically.
