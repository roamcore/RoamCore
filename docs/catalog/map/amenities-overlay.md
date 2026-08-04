# Amenities overlay (nearby places)

**Support tier:** C

> **Superseded by the tier-b connection:** this catalog page is retained for context. For the install + recipe + the 31 `rc_amenities_overlay_*` contract tiles + the FIVE §8 MANDATORY automations, see [connections/amenities-overlay/](../../../connections/amenities-overlay/) and [docs/recipe.md](../../../connections/amenities-overlay/docs/recipe.md).
>
> The tier-b connection contributes the 31 vendor-neutral `rc_amenities_overlay_*` contract tiles: `input_boolean.rc_amenities_overlay_enabled` + `input_boolean.rc_amenities_overlay_fail_safe` + `select.rc_amenities_overlay_radius_km` + `select.rc_amenities_overlay_data_source` + `number.rc_amenities_overlay_cache_ttl_min` + `number.rc_amenities_overlay_rate_limit_per_hour` + `binary_sensor.rc_amenities_overlay_is_loaded` + `binary_sensor.rc_amenities_overlay_is_rate_limited` + `binary_sensor.rc_amenities_overlay_is_offline_cache_active` + `sensor.rc_amenities_overlay_poi_count_total` + per-category `poi_count_water` + `poi_count_laundry` + `poi_count_gym` + `poi_count_dump_point` + `poi_count_campsite` + `poi_count_wild_camping` + `poi_count_supermarket` + `poi_count_fuel` + `sensor.rc_amenities_overlay_last_refresh_minutes_ago` + `sensor.rc_amenities_overlay_nearest_water_km` + `sensor.rc_amenities_overlay_nearest_campsite_km` + `button.rc_amenities_overlay_refresh_now` + `button.rc_amenities_overlay_clear_cache` + 8 per-category `enable_*` buttons (water + laundry + gym + dump_point + campsite + wild_camping + supermarket + fuel = 8 category buttons). The recipe at [docs/recipe.md](../../../connections/amenities-overlay/docs/recipe.md) walks the Overpass API (`https://overpass-api.de/api/interpreter`) + the HA core `rest:` integration + the HA core `input_boolean` + `input_select` + `input_number` helpers + the HA core `template:` sensor + `template:` binary_sensor wrappers + the optional RoamCore TileServer add-on (Wave 2 catalog #21) setup + the EIGHT operator-pickable POI categories + the FIVE §8 MANDATORY automations (fail-safe + rate-limited + user-configurable + offline-cache-or-internet + auto-disable-when-moving).

---

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

> For the install + the recipe + the 31 vendor-neutral `rc_amenities_overlay_*` contract tiles + the FIVE §8 MANDATORY automations + the 8 POI categories (water + laundry + gym + dump_point + campsite + wild_camping + supermarket + fuel), see the tier-b connection at [connections/amenities-overlay/](../../../connections/amenities-overlay/) (recipe: [docs/recipe.md](../../../connections/amenities-overlay/docs/recipe.md)).

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
