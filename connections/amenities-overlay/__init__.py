"""Amenities overlay — vendor-neutral iOverlander-style
POI overlay on the RoamCore Map page + offline cache
fallback + 8 POI categories + 5 §8 MANDATORY
automations — tier-b recipe connection.

Note on upstream wiring: tier-b connections don't ship a
RoamCore-owned operator-wired setup flow (a RoamCore
operator-wired wizard); instead, each path uses the
upstream integration's GUI flow (the HA core `rest:`
integration + the HA core `input_boolean` +
`input_select` + `input_number` helpers + the HA core
`template:` sensor wrapper + the HA core `template:`
binary_sensor wrapper all expose their own operator-
wired setup flow + GUI flow).

This module is a marker-only stub. Tier-b connections
don't ship native HA integration code; they publish a
recipe (docs/recipe.md) that walks the operator through
installing the upstream Overpass API + the upstream
HA core `rest:` integration + the upstream HA core
`input_boolean` + `input_select` + `input_number`
helpers + the upstream HA core `template:` sensor +
`template:` binary_sensor wrappers + the optional
RoamCore TileServer add-on (Wave 2 catalog #21) for
offline POI cache, then wiring the EIGHT operator-
pickable POI categories:

  - water — `amenity=drinking_water` (drinking-water
    fountains + water-bottle refill stations). The
    §3 POI category walks the operator through wiring
    the upstream `rest:` sensor pointing at the
    Overpass endpoint with the
    `amenity=drinking_water` query string.

  - laundry — `shop=laundry` (laundrettes +
    laundromats). The §4 POI category walks the
    operator through wiring the upstream `rest:` sensor
    pointing at the Overpass endpoint with the
    `shop=laundry` query string.

  - gym — `leisure=fitness_centre` (gyms + fitness
    centres). The §5 POI category walks the operator
    through wiring the upstream `rest:` sensor pointing
    at the Overpass endpoint with the
    `leisure=fitness_centre` query string.

  - dump_point — `amenity=sanitary_dump_station` (RV
    / motorhome dump stations for grey + black tanks).
    The §6 POI category walks the operator through
    wiring the upstream `rest:` sensor pointing at the
    Overpass endpoint with the
    `amenity=sanitary_dump_station` query string.

  - campsite — `tourism=camp_site` (established
    campgrounds with facilities). The §7 POI category
    walks the operator through wiring the upstream
    `rest:` sensor pointing at the Overpass endpoint
    with the `tourism=camp_site` query string.

  - wild_camping — `tourism=wild_camping` (legal /
    tolerated overnight parking spots). The §8 POI
    category walks the operator through wiring the
    upstream `rest:` sensor pointing at the Overpass
    endpoint with the `tourism=wild_camping` query
    string.

  - supermarket — `shop=supermarket` (full-size
    grocery stores). The §9 POI category walks the
    operator through wiring the upstream `rest:` sensor
    pointing at the Overpass endpoint with the
    `shop=supermarket` query string.

  - fuel — `amenity=fuel` (petrol / diesel stations).
    The §10 POI category walks the operator through
    wiring the upstream `rest:` sensor pointing at the
    Overpass endpoint with the `amenity=fuel` query
    string.

The umbrella publishes the resulting data via the
upstream Overpass API (`https://overpass-api.de/api/
interpreter` — an OpenStreetMap project, fully open +
free + community-run since 2013) + the upstream HA
core `rest:` integration (since 2017 — wraps any
upstream HTTP endpoint into a derived `sensor.*`
entity) + the upstream HA core `input_boolean` +
`input_select` + `input_number` helpers (since 2022.x
— have exposed the standard `input_boolean.toggle` +
`input_select.select_option` + `input_number.set_value`
services + the `input_boolean` / `select` / `number` /
`sensor` / `binary_sensor` / `button` domain entities)
+ the upstream HA core `template:` sensor wrapper
(since 2022.x — wraps any upstream sensor state into a
derived `sensor.*` entity) + the upstream HA core
`template:` binary_sensor wrapper (since 2022.x —
wraps any upstream sensor threshold into a derived
`binary_sensor.*` entity) + the optional RoamCore
TileServer add-on (Wave 2 catalog #21 — serves pre-
cached POI mbtiles for offline use), then publishes
the RoamCore amenities-overlay contract tiles on top
(the 31 contract entities documented in connection.yml
— 1 input_boolean amenities_overlay_enabled + 1
input_boolean amenities_overlay_fail_safe + 1 select
amenities_overlay_radius_km + 1 select
amenities_overlay_data_source + 1 number
amenities_overlay_cache_ttl_min + 1 number
amenities_overlay_rate_limit_per_hour + 1 binary_sensor
amenities_overlay_is_loaded + 1 binary_sensor
amenities_overlay_is_rate_limited + 1 binary_sensor
amenities_overlay_is_offline_cache_active + 1 sensor
amenities_overlay_poi_count_total + 1 sensor
amenities_overlay_poi_count_water + 1 sensor
amenities_overlay_poi_count_laundry + 1 sensor
amenities_overlay_poi_count_gym + 1 sensor
amenities_overlay_poi_count_dump_point + 1 sensor
amenities_overlay_poi_count_campsite + 1 sensor
amenities_overlay_poi_count_wild_camping + 1 sensor
amenities_overlay_poi_count_supermarket + 1 sensor
amenities_overlay_poi_count_fuel + 1 sensor
amenities_overlay_last_refresh_minutes_ago + 1 sensor
amenities_overlay_nearest_water_km + 1 sensor
amenities_overlay_nearest_campsite_km + 1 button
amenities_overlay_refresh_now + 1 button
amenities_overlay_clear_cache + 1 button
amenities_overlay_enable_water + 1 button
amenities_overlay_enable_laundry + 1 button
amenities_overlay_enable_gym + 1 button
amenities_overlay_enable_dump_point + 1 button
amenities_overlay_enable_campsite + 1 button
amenities_overlay_enable_wild_camping + 1 button
amenities_overlay_enable_supermarket + 1 button
amenities_overlay_enable_fuel = 31 contract entities).

The audit + boundary CI can detect an `amenities-overlay/`
folder that claims to be a connection via the `DOMAIN`
constant exported here. The wizard reads the manifest +
recipe at runtime.

The real per-operator amenities-overlay affordance
path is:

    Operator-side choice of one of the EIGHT POI
        categories (water / laundry / gym / dump_point /
        campsite / wild_camping / supermarket / fuel)
        -> upstream entities (the HA core
           `input_boolean.rc_amenities_overlay_enabled`
           for the master enable; the HA core
           `input_boolean.rc_amenities_overlay_fail_
           safe` for the safety interlock; the HA core
           `select.rc_amenities_overlay_radius_km` for
           the radius selector; the HA core
           `select.rc_amenities_overlay_data_source`
           for the Overpass / Offline cache / Auto
           picker; the HA core
           `number.rc_amenities_overlay_cache_ttl_min`
           for the cache-TTL picker; the HA core
           `number.rc_amenities_overlay_rate_limit_per_
           hour` for the rate-limit picker; the HA core
           `binary_sensor.rc_amenities_overlay_is_
           loaded` for the is-loaded chip; the HA core
           `binary_sensor.rc_amenities_overlay_is_rate_
           limited` for the rate-limited chip; the HA
           core `binary_sensor.rc_amenities_overlay_is_
           offline_cache_active` for the offline-cache
           chip; the HA core `sensor.rc_amenities_
           overlay_poi_count_*` for the per-category
           counts; the HA core `sensor.rc_amenities_
           overlay_nearest_water_km` + `sensor.rc_
           amenities_overlay_nearest_campsite_km` for
           the nearest-POI distances; the HA core
           `button.rc_amenities_overlay_refresh_now` +
           `button.rc_amenities_overlay_clear_cache` +
           `button.rc_amenities_overlay_enable_*` for
           the operator-triggered affordances)
        -> upstream signals (the operator's chosen
           Overpass `rest:` sensors — one per POI
           category — pointing at
           `https://overpass-api.de/api/interpreter`
           with the category-specific query string;
           the operator's chosen `device_tracker.rc_
           location_current` for the §8.5 vehicle-
           moving guard; the optional RoamCore
           TileServer add-on for the offline POI cache)
        -> RoamCore contract layer (HA core `rest:`
           integration + HA core `template:` sensor +
           binary_sensor + select + the operator's
           `input_boolean` / `input_select` /
           `input_number` for the contract tiles)
        -> dashboard tiles + OpenClaw queries
            ("is amenities overlay enabled?",
             "is the overlay fail-safe guard on?",
             "what is the overlay search radius?",
             "what data source is the overlay using?",
             "what is the cache TTL?",
             "what is the rate limit?",
             "is the overlay loaded?",
             "is the overlay rate-limited?",
             "is the offline cache active?",
             "how many POIs are in view?",
             "how many water POIs are in view?",
             "how far is the nearest water POI?",
             "refresh the overlay now",
             "clear the overlay cache",
             "enable water POIs",
             "enable campsite POIs")

    Safety interlocks (the recipe is the contract layer;
    the automation wrappers are documented in §8):
        -> The RoamCore amenities-overlay fail-safe
           automation is the §8.1 automation that fires
           when `input_boolean.rc_amenities_overlay_
           fail_safe` is OFF OR when `binary_sensor.rc_
           amenities_overlay_is_loaded` has been FALSE
           for > 5 minutes AND the upstream Overpass
           query has returned an error. The automation
           flips the fail-safe toggle back to ON +
           clears the enable toggle (so the overlay
           goes back to the safe OFF state) + writes
           an audit-log entry + fires a critical
           notification warning the operator that the
           overlay has auto-disabled.
        -> The RoamCore amenities-overlay rate-limit
           automation is the §8.2 automation that fires
           when `number.rc_amenities_overlay_rate_
           limit_per_hour` Overpass requests have been
           made in the last hour OR when `sensor.rc_
           amenities_overlay_last_refresh_minutes_ago`
           < `number.rc_amenities_overlay_cache_ttl_
           min`. The automation surfaces a "rate-
           limited / using cached data" banner in the
           map page + flips `binary_sensor.rc_
           amenities_overlay_is_rate_limited` to TRUE +
           switches the data source to the offline
           cache.
        -> The RoamCore amenities-overlay user-
           configurable automation is the §8.3
           automation that fires when ANY of the per-
           category visibility toggles (the per-category
           buttons in the recipe) flip OFF AND
           `input_boolean.rc_amenities_overlay_enabled`
           is ON. The automation re-fetches the POI
           list from Overpass (or the offline cache if
           rate-limited) with only the enabled
           categories + writes an audit-log entry
           showing the new enabled-category list.
        -> The RoamCore amenities-overlay internet-or-
           cache automation is the §8.4 automation that
           fires when `binary_sensor.rc_amenities_
           overlay_is_loaded` is FALSE AND the offline
           cache has never been populated (the operator
           has never wired the optional RoamCore
           TileServer add-on). The automation surfaces
           a "no internet + no offline cache — overlay
           disabled" banner in the map page + disables
           the overlay + writes an audit-log entry.
        -> The RoamCore amenities-overlay vehicle-
           moving automation is the §8.5 automation that
           fires when `device_tracker.rc_location_
           current` reports a speed > 10 km/h AND
           `input_boolean.rc_amenities_overlay_enabled`
           is ON. The automation clears the enable
           toggle (so the overlay goes back to the safe
           OFF state while the vehicle is moving — POIs
           don't make sense at highway speeds) + writes
           an audit-log entry + fires a notification.
           The automation re-enables the overlay once
           the vehicle speed drops below 5 km/h for >
           2 minutes (so the overlay auto-resumes when
           parked).

    Cross-references:
        -> The upstream Overpass API (`https://overpass-
           api.de/api/interpreter`) is the canonical
           POI query engine (an OpenStreetMap project,
           fully open + free + community-run since 2013;
           stable query language; widely used by
           trucker / camper / van apps worldwide —
           iOverlander itself uses Overpass for its
           amenity queries).
        -> The HA core `rest:` integration is the
           canonical HTTP query primitive (since 2017 —
           wraps any upstream HTTP endpoint into a
           derived `sensor.*` entity).
        -> The HA core `input_boolean` + `input_select`
           + `input_number` helpers are the canonical
           per-category + radius + cache-TTL + rate-
           limit + data-source state primitives (since
           2022.x).
        -> The HA core `template:` sensor wrapper is
           the canonical per-category count + nearest-
           POI derivation (since 2022.x).
        -> The HA core `template:` binary_sensor
           wrapper is the canonical is-loaded + is-
           rate-limited + is-offline-cache-active
           derivation (since 2022.x).
        -> The optional RoamCore TileServer add-on
           (Wave 2 catalog #21) is the canonical
           offline POI cache (serves pre-cached POI
           mbtiles for offline use).
        -> The map-dashboard Wave 3 #66 connection
           cross-references the basemap mode for the
           map page where the overlay is rendered.
        -> The time-atomic Wave 3 #55 connection
           cross-references the time-of-day primitive
           used by the §8.5 vehicle-moving guard's
           2-minute parked timer.
        -> The bluetooth-wifi-presence Wave 3 #42
           connection cross-references the `device_
           tracker.rc_location_current` speed attribute
           used by the §8.5 vehicle-moving guard.
        -> The mode Wave 3 #61 connection cross-
           references the mode-state context for the
           §8.3 user-configurable guard's audit-log
           entry (the audit entry includes the current
           mode).
        -> The demo-mode Wave 3 #62 connection cross-
           references the demo-mode umbrella for the
           §8.4 internet-or-cache guard's "demo mode
           is ON — values are not real" banner pattern.
        -> The advanced-mode Wave 3 #63 connection
           cross-references the advanced-mode umbrella
           for the §8.5 vehicle-moving guard's "operator
           can override the auto-disable" affordance.

See docs/recipe.md for the full howto (Overpass API
reachability verification + HA core `rest:`
integration install + HA core `input_boolean` +
`input_select` + `input_number` helpers install + HA
core `template:` sensor wrapper install + HA core
`template:` binary_sensor wrapper install + the EIGHT
operator-pickable POI categories + the 31
`rc_amenities_overlay_*` contract tiles + the FIVE §8
MANDATORY automations + the 6 §9 troubleshooting
entries + privacy + tier-a promotion outline).
"""

DOMAIN = "amenities_overlay"