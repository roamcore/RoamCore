# Amenities overlay (nearby places)

See nearby things you actually care about when living on the road — water taps, laundrettes, gyms, dump points, campsites, supermarkets, and more — directly on the RoamCore map.

## What it does

An **optional map overlay** layer that adds “points of interest” (POIs) around your current location.

The goal is practical: when you’re parked somewhere new, you can answer:
- Where’s the nearest **water fill**?
- Is there a **laundrette** nearby?
- Where can I find a **quiet overnight spot** or a **campsite**?

## How to install

- A working RoamCore Map page (any basemap mode).
- Internet access (at least when fetching POIs).

Optional (future): offline/“cached” POI packs for areas you travel often.

## How it works (planned)

RoamCore will fetch POIs from one or more data sources (e.g. OpenStreetMap-based APIs) and render them as an overlay layer on the map.

Design constraints:
- Must **fail safe** (no blank map if the overlay fails)
- Must be **rate-limited** and cache results (to avoid hammering APIs)
- Must be user-configurable (categories on/off)

## Setup

Not shipped yet.

## Troubleshooting

- If the map works but POIs don’t show up, first check if the selected categories are enabled.
- If you see “rate limit” errors, reduce refresh frequency or use cached results.

## Useful links

Upstream docs and related references.
