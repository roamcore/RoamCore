# Amenities overlay (nearby places)

**Support tier:** C

See nearby things you actually care about when living on the road — water taps, laundrettes, gyms, dump points, campsites, supermarkets, and more — directly on the RoamCore map.

## What this is

An **optional map overlay** layer that adds “points of interest” (POIs) around your current location.

The goal is practical: when you’re parked somewhere new, you can answer:
- Where’s the nearest **water fill**?
- Is there a **laundrette** nearby?
- Where can I find a **quiet overnight spot** or a **campsite**?

## What you need

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

Shipped in slice #22. Four HA helper inputs + a toggle control the
overlay; the overlay only renders when the toggle is ON. Defaults are
safe (off, no outbound calls until you enable it).

| Input                                          | Default                              | Purpose |
|------------------------------------------------|--------------------------------------|---------|
| `input_boolean.rc_amenities_overlay_enabled`   | `false` (off)                        | Master switch — must be ON for the map to draw amenities. |
| `input_select.rc_amenities_categories`         | `water,laundry,campground,supermarket` | Comma-separated categories to show. JS chips read this. |
| `input_number.rc_amenities_radius_km`          | `5` (range 0.5–50)                   | Search radius in km around your current location. |
| `input_text.rc_amenities_overpass_url`         | `https://overpass-api.de/api/interpreter` (annotated `# PRIVACY-OPTIN:`) | Overpass endpoint. Override to a self-hosted instance if you prefer. |

The toggle is exposed in the Map page (next to the “Open Traccar
(fullscreen)” button) as **Amenities overlay**. While the toggle is ON,
the file `/local/roamcore/amenities/latest.json` is rewritten every 30
minutes (and on toggle-on / location move >1 km) by the
`shell_command.rc_amenities_overpass_query` wired in
`homeassistant/packages/roamcore_amenities.yaml`.

The six category chips on the map (water / dump / laundry / camping /
shop / gym) are bound to the `input_select` and grey out when a
category is deselected.

## Privacy

- The overlay is **off by default** — nothing is fetched until you turn
  on `input_boolean.rc_amenities_overlay_enabled`.
- The default Overpass URL (`overpass-api.de`) is annotated
  `# PRIVACY-OPTIN:` in both the YAML package and the Python helper so
  the privacy smoke check accepts it. The smoke check
  (`scripts/checks/amenities-overlay-privacy-smoke.sh`) refuses to pass
  if a non-loopback, non-`# PRIVACY-OPTIN:` host is added to the
  amenities surface.
- The Python helper never opens a socket at import time (the
  `urllib.request` import is scoped to the `--query` path).
- The JS layer fails safe: a missing or malformed `latest.json` simply
  hides the overlay with one console warning; the basemap is
  unaffected.

## Troubleshooting

- If the map works but POIs don’t show up, first check if the selected categories are enabled.
- If you see “rate limit” errors, reduce refresh frequency or use cached results.
