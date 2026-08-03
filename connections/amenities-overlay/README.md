# Amenities overlay — vendor-neutral iOverlander-style POI overlay on the RoamCore Map page + offline cache fallback + 8 POI categories + 5 §8 MANDATORY automations

**Tier:** B (recipe)
**Category:** map
**Status:** beta

## What this connection is

Amenities overlay — vendor-neutral iOverlander-style POI overlay on the RoamCore Map page + offline cache fallback + 8 POI categories + 5 §8 MANDATORY automations — the umbrella for "Amenities overlay (nearby places) — See nearby things you actually care about when living on the road — water taps, laundrettes, gyms, dump points, campsites, supermarkets, and more — directly on the RoamCore map" — is the map-category complement to the broader RoamCore "where am I + what's around me?" affordances. The master enable toggle is the operator's master switch (OFF by default; no POIs surface on the map unless the operator explicitly turns it ON); the fail-safe toggle is the safety interlock (must be ON; the §8.1 fail-safe guard is bypassed if OFF); the radius selector picks the max-distance radius (1 / 2 / 5 / 10 / 25 / 50 km from the current location; default 5 km); the data-source selector picks where to fetch POIs from (Overpass / Offline cache / Auto); the cache-TTL picker controls how long the in-memory POI cache survives (5–1440 minutes; default 60); the rate-limit picker controls how many Overpass requests per hour are allowed (1–100; default 30); the is-loaded binary sensor surfaces whether the overlay has at least one POI in view; the is-rate-limited binary sensor surfaces whether Overpass returned 429 in the last hour; the is-offline-cache-active binary sensor surfaces whether the offline cache is serving POIs; the count-total + count-water + count-laundry + count-gym + count-dump-point + count-campsite + count-wild-camping + count-supermarket + count-fuel sensors surface the per-category POI counts in view; the last-refresh-minutes-ago sensor surfaces how long ago the last successful Overpass refresh was; the nearest-water-km + nearest-campsite-km sensors surface the distance to the nearest POI in km (-1 when no POI in view); the refresh-now button is the operator-triggered one-tap force-refresh from Overpass, bypassing the cache; the clear-cache button is the operator-triggered one-tap clear the offline + in-memory POI cache; the enable-water + enable-laundry + enable-gym + enable-dump-point + enable-campsite + enable-wild-camping + enable-supermarket + enable-fuel buttons are the operator-triggered one-tap per-category visibility toggle.

RoamCore ships **no** native amenities-overlay engine. We RECIPE the well-understood upstream Overpass API (`https://overpass-api.de/api/interpreter` — an OpenStreetMap project, fully open + free + community-run since 2013; stable query language; widely used by trucker / camper / van apps worldwide — iOverlander itself uses Overpass for its amenity queries) + the HA core `rest:` integration (since 2017 — exposes a GUI flow for the operator to add a derived `sensor.*` entity from an HTTP endpoint) + the HA core `input_boolean` + `input_select` + `input_number` helpers (since 2022.x — expose a GUI flow for the operator to add the helper entities from the HA UI under Settings → Helpers) + the HA core `template:` sensor wrapper (since 2022.x — exposes a GUI flow for the operator to add a derived `sensor.*` entity from the upstream sensors) + the HA core `template:` binary_sensor wrapper (since 2022.x — exposes a GUI flow for the operator to add a derived `binary_sensor.*` entity from the upstream sensors) + the optional RoamCore TileServer add-on (Wave 2 catalog #21 — serves pre-cached POI mbtiles for offline use). The 31 `rc_amenities_overlay_*` contract tiles are the vendor-neutral layer the dashboard + OpenClaw queries use; the actual amenities-overlay logic is provided by the upstream Overpass API + the HA core `rest:` integration + the HA core `input_boolean` + `input_select` + `input_number` helpers + the HA core `template:` sensor + `template:` binary_sensor wrappers (RoamCore does NOT fork any of these).

## The 8 operator-pickable POI categories

- **water** — `amenity=drinking_water` (drinking-water fountains + water-bottle refill stations).
- **laundry** — `shop=laundry` (laundrettes + laundromats).
- **gym** — `leisure=fitness_centre` (gyms + fitness centres).
- **dump_point** — `amenity=sanitary_dump_station` (RV / motorhome dump stations for grey + black tanks).
- **campsite** — `tourism=camp_site` (established campgrounds with facilities).
- **wild_camping** — `tourism=wild_camping` (legal / tolerated overnight parking spots).
- **supermarket** — `shop=supermarket` (full-size grocery stores).
- **fuel** — `amenity=fuel` (petrol / diesel stations).

## Setup recipe (one-paragraph)

1. Decide if you want amenities overlay (most operators: leave OFF until you actually need it).
2. Verify the upstream Overpass API (`https://overpass-api.de/api/interpreter`) is reachable from the HA host: `curl --data 'data=[out:json];(node["amenity"="drinking_water"](around:5000,0,0););out;' https://overpass-api.de/api/interpreter` — expect a JSON response with `elements: []` or POI nodes.
3. Set up the upstream helpers:
   - **HA core `rest:` integration** — auto-installed in every HA install since 2017 + exposed via the HA UI under Settings → Devices & Services → Add Integration → REST.
   - **HA core `input_boolean` + `input_select` + `input_number` helpers** — auto-installed in every HA install + exposed via the HA UI under Settings → Helpers. The operator creates the helper entities via the HA UI (or via `input_boolean:` / `input_select:` / `input_number:` YAML blocks).
4. Wire the upstream Overpass `rest:` sensors (one per POI category — the operator configures the REST endpoint + the JSON path + the scan interval pointing at `https://overpass-api.de/api/interpreter` with the category-specific query string; the §3 water / §4 laundry / §5 gym / §6 dump_point / §7 campsite / §8 wild_camping / §9 supermarket / §10 fuel sections walk through each one).
5. Optionally install the RoamCore TileServer add-on (Wave 2 catalog #21) for the offline POI cache + populate the cache with POIs for the operator's most-travelled areas.
6. Configure the operator-facing `input_boolean.rc_amenities_overlay_enabled` + `input_boolean.rc_amenities_overlay_fail_safe` + `select.rc_amenities_overlay_radius_km` + `select.rc_amenities_overlay_data_source` + `number.rc_amenities_overlay_cache_ttl_min` + `number.rc_amenities_overlay_rate_limit_per_hour` contract tiles to point at the upstream helpers.
7. Wire the FIVE §8 MANDATORY automations (overlay must fail safe + overlay must be rate-limited + overlay must be user-configurable + overlay must require internet OR offline cache + overlay auto-disables when vehicle is moving > N km/h).
8. Verify: enable amenities overlay via `input_boolean.rc_amenities_overlay_enabled` → check the dashboard surfaces the POI counts → check `binary_sensor.rc_amenities_overlay_is_loaded` flips TRUE → start driving → check the §8.5 vehicle-moving guard auto-disables the overlay once speed > 10 km/h.

Full howto: see [`docs/recipe.md`](docs/recipe.md).

## The 31 `rc_amenities_overlay_*` contract tiles

| Domain | Tile id | Purpose |
|---|---|---|
| `input_boolean` | `rc_amenities_overlay_enabled` | Master enable toggle (OFF by default). |
| `input_boolean` | `rc_amenities_overlay_fail_safe` | Safety interlock (must be ON). |
| `select` | `rc_amenities_overlay_radius_km` | Radius selector (1 / 2 / 5 / 10 / 25 / 50 km). |
| `select` | `rc_amenities_overlay_data_source` | Overpass / Offline cache / Auto. |
| `number` | `rc_amenities_overlay_cache_ttl_min` | Cache TTL in minutes (5–1440, default 60). |
| `number` | `rc_amenities_overlay_rate_limit_per_hour` | Max Overpass requests / hour (1–100, default 30). |
| `binary_sensor` | `rc_amenities_overlay_is_loaded` | TRUE when overlay has ≥1 POI in view. |
| `binary_sensor` | `rc_amenities_overlay_is_rate_limited` | TRUE when Overpass returned 429 in the last hour. |
| `binary_sensor` | `rc_amenities_overlay_is_offline_cache_active` | TRUE when offline cache is serving POIs. |
| `sensor` | `rc_amenities_overlay_poi_count_total` | Total POIs in view (all 8 categories). |
| `sensor` | `rc_amenities_overlay_poi_count_water` | Count of `amenity=drinking_water` POIs in view. |
| `sensor` | `rc_amenities_overlay_poi_count_laundry` | Count of `shop=laundry` POIs in view. |
| `sensor` | `rc_amenities_overlay_poi_count_gym` | Count of `leisure=fitness_centre` POIs in view. |
| `sensor` | `rc_amenities_overlay_poi_count_dump_point` | Count of `amenity=sanitary_dump_station` POIs. |
| `sensor` | `rc_amenities_overlay_poi_count_campsite` | Count of `tourism=camp_site` POIs. |
| `sensor` | `rc_amenities_overlay_poi_count_wild_camping` | Count of `tourism=wild_camping` POIs. |
| `sensor` | `rc_amenities_overlay_poi_count_supermarket` | Count of `shop=supermarket` POIs. |
| `sensor` | `rc_amenities_overlay_poi_count_fuel` | Count of `amenity=fuel` POIs. |
| `sensor` | `rc_amenities_overlay_last_refresh_minutes_ago` | Minutes since last successful Overpass refresh. |
| `sensor` | `rc_amenities_overlay_nearest_water_km` | Distance to nearest `amenity=drinking_water` POI (km, -1 if none). |
| `sensor` | `rc_amenities_overlay_nearest_campsite_km` | Distance to nearest `tourism=camp_site` POI (km, -1 if none). |
| `button` | `rc_amenities_overlay_refresh_now` | One-tap force-refresh from Overpass, bypassing cache. |
| `button` | `rc_amenities_overlay_clear_cache` | One-tap clear the offline + in-memory POI cache. |
| `button` | `rc_amenities_overlay_enable_water` | One-tap enable the `water` category. |
| `button` | `rc_amenities_overlay_enable_laundry` | One-tap enable the `laundry` category. |
| `button` | `rc_amenities_overlay_enable_gym` | One-tap enable the `gym` category. |
| `button` | `rc_amenities_overlay_enable_dump_point` | One-tap enable the `dump_point` category. |
| `button` | `rc_amenities_overlay_enable_campsite` | One-tap enable the `campsite` category. |
| `button` | `rc_amenities_overlay_enable_wild_camping` | One-tap enable the `wild_camping` category. |
| `button` | `rc_amenities_overlay_enable_supermarket` | One-tap enable the `supermarket` category. |
| `button` | `rc_amenities_overlay_enable_fuel` | One-tap enable the `fuel` category. |

## The 5 §8 MANDATORY automations

- **§8.1 Amenities-overlay must fail safe (no blank map if overlay fails)** — fires when `input_boolean.rc_amenities_overlay_fail_safe` is OFF OR when `binary_sensor.rc_amenities_overlay_is_loaded` has been FALSE for > 5 minutes AND the upstream Overpass query has returned an error. Flips the fail-safe toggle back to ON + clears the enable toggle + writes an audit-log entry + fires a critical notification.
- **§8.2 Amenities-overlay must be rate-limited + cache results** — fires when `number.rc_amenities_overlay_rate_limit_per_hour` Overpass requests have been made in the last hour OR when `sensor.rc_amenities_overlay_last_refresh_minutes_ago` < `number.rc_amenities_overlay_cache_ttl_min`. Surfaces a "rate-limited / using cached data" banner + flips `binary_sensor.rc_amenities_overlay_is_rate_limited` to TRUE + switches the data source to the offline cache.
- **§8.3 Amenities-overlay must be user-configurable (categories on/off)** — fires when ANY of the per-category visibility toggles flips OFF AND `input_boolean.rc_amenities_overlay_enabled` is ON. Re-fetches the POI list with only the enabled categories + writes an audit-log entry showing the new enabled-category list.
- **§8.4 Amenities-overlay must require internet OR a populated offline cache** — fires when `binary_sensor.rc_amenities_overlay_is_loaded` is FALSE AND the offline cache has never been populated. Surfaces a "no internet + no offline cache — overlay disabled" banner + disables the overlay + writes an audit-log entry.
- **§8.5 Amenities-overlay auto-disables when vehicle is moving > N km/h** — fires when `device_tracker.rc_location_current` reports a speed > 10 km/h AND `input_boolean.rc_amenities_overlay_enabled` is ON. Clears the enable toggle (so the overlay goes back to the safe OFF state while the vehicle is moving — POIs don't make sense at highway speeds) + writes an audit-log entry + fires a notification. The automation re-enables the overlay once the vehicle speed drops below 5 km/h for > 2 minutes.

## Why tier-b, not tier-a

Tier-a would require a RoamCore-owned amenities-overlay engine + integration code + integration tests against a real amenities-overlay engine bench (a controlled environment with canned fixture responses for Overpass queries + canned fixture responses for rate-limit events + canned fixture responses for offline-cache fallbacks + canned fixture responses for vehicle-moving events — all wired together in a controlled environment). We have no operator-side amenities-overlay engine bench on the CI to integration-test against (the bench requires the operator's chosen Overpass `rest:` sensors + the operator's `device_tracker.rc_location_current` + canned fixture responses for rate-limit events — all wired together in a controlled environment). Tier-b is the honest tier: Overpass + HA core `rest:` + HA core `input_boolean` + HA core `input_select` + HA core `input_number` + HA core `template:` are all upstream / vendor / HACS / hardware code (not RoamCore-owned); the RoamCore wrapper is a thin upstream-entity-aggregation layer + the contract layer + the §8 MANDATORY automations. The recipe is sound but we cannot claim one-tap automation.

The legacy catalog page (the legacy spec — 39-line tier-c claim stub, originally listed "Amenities overlay (nearby places) — See nearby things you actually care about when living on the road — water taps, laundrettes, gyms, dump points, campsites, supermarkets, and more — directly on the RoamCore map. An optional map overlay layer that adds 'points of interest' (POIs) around your current location. The goal is practical: when you're parked somewhere new, you can answer: Where's the nearest water fill? Is there a laundrette nearby? Where can I find a quiet overnight spot or a campsite? RoamCore will fetch POIs from one or more data sources (e.g. OpenStreetMap-based APIs) and render them as an overlay layer on the map. Design constraints: Must fail safe (no blank map if the overlay fails) + Must be rate-limited and cache results (to avoid hammering APIs) + Must be user-configurable (categories on/off)" with no recipe + no contract + no automations + no install path — just a placeholder with an aspirational tier-c claim) is now superseded by this tier-b recipe connection. The legacy tier-c claim was honest about no recipe + no contract + no automations + no install path; the picker ships the contract layer + the recipe + the §8 automations as tier-b (the upstream engines are well-known stable APIs + the recipe is sound).

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "amenities_overlay"` marker for the audit.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded by this slice): [the legacy spec](../../the legacy spec)
- HA core `rest:` integration (the canonical HTTP query primitive): https://www.home-assistant.io/integrations/rest/
- HA core `input_boolean` integration (the canonical master enable toggle helper): https://www.home-assistant.io/integrations/input_boolean/
- HA core `input_select` integration (the canonical radius + data-source selector helper): https://www.home-assistant.io/integrations/input_select/
- HA core `input_number` integration (the canonical cache-TTL + rate-limit picker helper): https://www.home-assistant.io/integrations/input_number/
- HA core `template:` integration (the canonical per-category count + nearest-POI derivation): https://www.home-assistant.io/integrations/template/
- Overpass API (the canonical POI query engine — an OpenStreetMap project, fully open + free + community-run since 2013): https://wiki.openstreetmap.org/wiki/Overpass_API
- Map dashboard (the basemap mode for the map page where the overlay is rendered): `connections/map-dashboard/` (Wave 3 #66)
- Time-atomic (the §8.5 vehicle-moving guard's 2-minute parked timer): `connections/time-atomic/` (Wave 3 #55)
- Bluetooth/Wi-Fi presence (the §8.5 vehicle-moving guard's `device_tracker.rc_location_current` speed attribute): `connections/bluetooth-wifi-presence/` (Wave 3 #42)
- Mode (the §8.3 user-configurable guard's audit-log entry's mode-change context): `connections/mode/` (Wave 3 #61)
- Demo mode (the §8.4 internet-or-cache guard's "demo mode is ON — values are not real" banner pattern): `connections/demo-mode/` (Wave 3 #62)
- Advanced mode (the §8.5 vehicle-moving guard's "operator can override the auto-disable" affordance): `connections/advanced-mode/` (Wave 3 #63)
- RoamCore TileServer add-on (the optional offline POI cache — Wave 2 catalog #21): the legacy spec
- RoamCore entity naming: `docs/reference/rc-entity-naming.md` (the `map` + `amenities_overlay` subsystems were added by this slice)