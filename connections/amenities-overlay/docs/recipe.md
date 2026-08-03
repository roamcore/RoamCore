# Amenities overlay — full howto (RoamCore vendor-neutral iOverlander-style POI overlay on the RoamCore Map page + offline cache fallback + 8 POI categories + 5 §8 MANDATORY automations)

This recipe is the canonical howto for the
`connections/amenities-overlay/` tier-b recipe
connection (Wave 3 #67). It walks the operator through
setting up the EIGHT operator-pickable POI categories
(water + laundry + gym + dump_point + campsite +
wild_camping + supermarket + fuel) + the 31
`rc_amenities_overlay_*` contract tiles + the FIVE §8
MANDATORY automations + the optional offline POI cache
(the RoamCore TileServer add-on from Wave 2 catalog #21)
+ the per-category `rest:` sensor wiring for the upstream
Overpass API (`https://overpass-api.de/api/interpreter`).

The recipe assumes the operator has at least the
upstream HA core `rest:` integration installed (since
2017 — auto-installed in every HA install) + the
upstream HA core `input_boolean` + `input_select` +
`input_number` helpers installed (since 2022.x — auto-
installed in every HA install) + at least ONE upstream
device_tracker wired (the operator's chosen
`device_tracker.rc_location_current` — Traccar /
OwnTracks / HA Companion / generic NMEA — for the §8.5
vehicle-moving guard). If the operator has no upstream
device_tracker wired, the recipe starts at §2
Prerequisites + walks through the device_tracker wiring
before the amenities-overlay wiring.

## §1 What is Amenities overlay in RoamCore?

Amenities overlay — vendor-neutral iOverlander-style POI
overlay on the RoamCore Map page + offline cache fallback
+ 8 POI categories + 5 §8 MANDATORY automations — the
umbrella for "Amenities overlay (nearby places) — See
nearby things you actually care about when living on the
road — water taps, laundrettes, gyms, dump points,
campsites, supermarkets, and more — directly on the
RoamCore map" — is the map-category complement to the
broader RoamCore "where am I + what's around me?"
affordances. The umbrella positions Amenities overlay as
a map-category concern (not a power-category concern +
not a safety-category concern + not a connectivity-
category concern + not a vehicle-category concern)
because Amenities overlay is the operator-facing "what's
near me on the map?" affordance: the master enable
toggle is the operator's master switch (OFF by default;
no POIs surface on the map unless the operator
explicitly turns it ON); the fail-safe toggle is the
single most important safety interlock in the
amenities-overlay umbrella (must be ON; the §8.1
fail-safe guard is bypassed if OFF — forgetting to wire
the fail-safe guard can leave the operator with a blank
map when the upstream Overpass query fails); the radius
selector picks the max-distance radius (1 / 2 / 5 / 10 /
25 / 50 km from the current location; default 5 km);
the data-source selector picks where to fetch POIs from
(Overpass / Offline cache / Auto — "Auto" tries Overpass
first, falls back to the offline cache if Overpass fails
or rate-limits); the cache-TTL picker controls how long
the in-memory POI cache survives (5–1440 minutes;
default 60); the rate-limit picker controls how many
Overpass requests per hour are allowed (1–100; default
30); the is-loaded binary sensor surfaces whether the
overlay has at least one POI in view (drives the
dashboard chip); the is-rate-limited binary sensor
surfaces whether Overpass returned 429 in the last hour
(drives the §8.2 rate-limit guard); the is-offline-cache-
active binary sensor surfaces whether the offline cache
is serving POIs (drives the §8.4 internet-or-cache
guard); the count-total + count-water + count-laundry
+ count-gym + count-dump-point + count-campsite +
count-wild-camping + count-supermarket + count-fuel
sensors surface the per-category POI counts in view
(drives the map page's POI markers); the last-refresh-
minutes-ago sensor surfaces how long ago the last
successful Overpass refresh was (drives the §8.2 rate-
limit guard); the nearest-water-km + nearest-campsite-km
sensors surface the distance to the nearest POI in km
(drives the dashboard's "nearest water: 2.3 km" chip);
the refresh-now button is the operator-triggered one-
tap force-refresh from Overpass, bypassing the cache;
the clear-cache button is the operator-triggered one-
tap clear the offline + in-memory POI cache; the
enable-water + enable-laundry + enable-gym + enable-
dump-point + enable-campsite + enable-wild-camping +
enable-supermarket + enable-fuel buttons are the
operator-triggered one-tap per-category visibility
toggle.

The master enable tile
(`input_boolean.rc_amenities_overlay_enabled`) is the
operator's master switch — the recipe defaults to OFF
because POIs are never shown unless the operator
explicitly enables the overlay (the §8.5 vehicle-moving
guard fires whenever the vehicle is moving > 10 km/h,
so forgetting to disable the overlay is mitigated for
highway driving).

The fail-safe tile
(`input_boolean.rc_amenities_overlay_fail_safe`) is the
operator's safety interlock — the recipe defaults to ON
because the §8.1 fail-safe guard depends on it; if the
operator flips it OFF, the §8.1 fail-safe guard is
bypassed and a failed Overpass query can leave the
operator with a blank map.

The radius tile (`select.rc_amenities_overlay_radius_km`)
is the operator's max-distance selector — the recipe
exposes the 1 / 2 / 5 / 10 / 25 / 50 km options so the
operator can pick a radius based on how densely the
area is populated (1–2 km for dense urban areas, 10–50
km for rural areas).

The data-source tile
(`select.rc_amenities_overlay_data_source`) is the
operator's data-source selector — the recipe exposes the
Overpass / Offline cache / Auto options so the operator
can pick a data source based on the network availability
(Overpass when on Wi-Fi or unmetered LTE, Offline cache
when on metered LTE or no signal, Auto to let the §8.2
rate-limit guard pick automatically).

The cache-TTL tile
(`number.rc_amenities_overlay_cache_ttl_min`) is the
operator's cache-TTL selector — the recipe defaults to
60 minutes because most POIs don't change frequently;
operators who travel quickly between areas may want a
shorter TTL (5–15 minutes) so the POI list reflects
the new area promptly.

The rate-limit tile
(`number.rc_amenities_overlay_rate_limit_per_hour`) is the
operator's rate-limit selector — the recipe defaults
to 30 Overpass requests per hour because Overpass's
public instance has a soft rate limit around 10–60
requests per IP per minute; operators who hit the rate
limit can lower this number so the §8.2 rate-limit
guard switches to the offline cache earlier.

The is-loaded tile
(`binary_sensor.rc_amenities_overlay_is_loaded`) is the
single most important operator-facing chip in the
amenities-overlay umbrella — it surfaces whether the
overlay has at least one POI in view (turns green when
the overlay has POIs; turns grey when the overlay is
empty; turns red when the upstream Overpass query has
been failing for > 5 minutes — the §8.1 fail-safe
guard uses this signal).

The is-rate-limited tile
(`binary_sensor.rc_amenities_overlay_is_rate_limited`)
is the rate-limit chip — surfaces whether Overpass
returned 429 in the last hour; the §8.2 rate-limit
guard flips this to TRUE and switches the data source
to the offline cache.

The is-offline-cache-active tile
(`binary_sensor.rc_amenities_overlay_is_offline_cache_
active`) is the offline-cache chip — surfaces whether
the offline cache is serving POIs; the §8.4 internet-
or-cache guard uses this signal to detect "no internet
+ no offline cache" scenarios.

The count-total tile
(`sensor.rc_amenities_overlay_poi_count_total`) is the
total POI count — surfaces how many POIs are in view
across all 8 enabled categories; drives the map page's
"12 POIs in view" header.

The per-category count tiles (the 8 per-category
`sensor.rc_amenities_overlay_poi_count_*` tiles) are
the per-category POI counts — drive the map page's
per-category marker layers + the dashboard's per-
category counters.

The last-refresh-minutes-ago tile
(`sensor.rc_amenities_overlay_last_refresh_minutes_ago`)
is the freshness chip — surfaces how long ago the last
successful Overpass refresh was; drives the §8.2 rate-
limit guard.

The nearest-water-km + nearest-campsite-km tiles are
the nearest-POI distance chips — surface the distance
to the nearest POI in km (-1 when no POI in view);
drive the dashboard's "nearest water: 2.3 km" + "nearest
campsite: 8.7 km" chips.

The refresh-now button
(`button.rc_amenities_overlay_refresh_now`) is the
operator-triggered one-tap force-refresh from Overpass,
bypassing the cache — useful when the operator parks
in a new area and wants the POI list updated
immediately rather than waiting for the next cache TTL
expiry.

The clear-cache button
(`button.rc_amenities_overlay_clear_cache`) is the
operator-triggered one-tap clear the offline + in-memory
POI cache — useful when the operator has moved to a
completely new area and wants to force a full refresh
from Overpass.

The per-category enable buttons (the 8 per-category
`button.rc_amenities_overlay_enable_*` buttons) are the
operator-triggered one-tap per-category visibility
toggle — each flips the per-category visibility toggle
for the corresponding POI category + triggers the §8.3
user-configurable guard's re-fetch.

## §2 Prerequisites

Before installing the amenities-overlay recipe, the
operator MUST have:

1. **A working RoamCore Map page.** The operator has the
   upstream RoamCore Map page (`connections/map-dashboard/`
   — Wave 3 #66) installed + the basemap mode picker
   working + the trip-overlay picker working. The map
   page is where the amenities overlay renders its POI
   markers. (See `connections/map-dashboard/docs/recipe.md`
   for the basemap mode + trip-overlay picker install.)

2. **A working `device_tracker.rc_location_current`.**
   The operator has wired their chosen location source
   (Traccar / OwnTracks / HA Companion / generic NMEA)
   into a `device_tracker.rc_location_current` entity
   with a `speed` attribute (in km/h). This is the
   upstream signal for the §8.5 vehicle-moving guard.
   (See `connections/bluetooth-wifi-presence/` Wave 3
   #42 for the bluetooth-wifi-presence speed-attribute
   wiring pattern; the §8.5 vehicle-moving guard
   consumes `device_tracker.rc_location_current.attributes.speed`
   directly.)

3. **The upstream Overpass API reachable from the HA
   host.** The operator can curl the upstream Overpass
   endpoint (`https://overpass-api.de/api/interpreter`)
   with a minimal query:

   ```bash
   curl --data 'data=[out:json];(node["amenity"="drinking_water"](around:5000,0,0););out;' https://overpass-api.de/api/interpreter
   ```

   The expected response is a JSON object with an
   `elements: []` key (or POI nodes if there happen to
   be any water taps near (0,0) — the (0,0) coordinate
   is in the Atlantic Ocean off the coast of Africa so
   the expected response is usually an empty array).
   If the curl fails (connection refused / timeout /
   DNS resolution failure), the operator MUST resolve
   the connectivity issue before proceeding (check the
   HA host's outbound network configuration + check
   whether the HA host can reach `overpass-api.de`).

4. **The HA core `rest:` integration installed** (since
   2017 — auto-installed in every HA install + exposed
   via the HA UI under Settings → Devices & Services →
   Add Integration → REST). The operator creates the
   `rest:` resource via the HA UI (or via the
   `rest:` YAML configuration block).

5. **The HA core `input_boolean` + `input_select` +
   `input_number` helpers installed** (since 2022.x —
   auto-installed in every HA install + exposed via
   the HA UI under Settings → Helpers). The operator
   creates the helper entities via the HA UI (or via
   the `input_boolean:` / `input_select:` /
   `input_number:` YAML blocks).

6. **The HA core `template:` sensor + `template:`
   binary_sensor wrappers installed** (since 2022.x —
   auto-installed in every HA install + exposed via
   the HA UI under Settings → Devices & Services →
   Add Integration → Template). The operator creates
   the `template:` sensor + binary_sensor entities via
   the HA UI (or via the `template:` YAML configuration
   block).

Optionally, the operator MAY also have:

7. **The RoamCore TileServer add-on installed** (Wave 2
   catalog #21 — `docs/catalog/map/roamcore-tileserver-
   addon.md`). The TileServer add-on serves pre-cached
   POI mbtiles for offline use. The §8.4 internet-or-
   cache guard depends on the offline cache being
   populated; without the TileServer add-on, the §8.4
   guard will surface a "no internet + no offline cache
   — overlay disabled" banner whenever the upstream
   Overpass API is unreachable.

If the operator has all 6 required prerequisites, they
can proceed to §3 8 operator-pickable POI categories. If
the operator is missing any prerequisite, they should
follow the linked recipe in the prerequisite's bullet
point above before proceeding.

## §3 The 8 operator-pickable POI categories

The recipe walks the operator through the EIGHT POI
categories an operator picks when enabling amenities
overlay. Each category is mapped to an OpenStreetMap
amenity key + has a dedicated upstream `rest:` sensor
that queries Overpass for POIs of that category within
the operator's current radius + current location.

### §3.1 water — `amenity=drinking_water`

The water POI category surfaces drinking-water
fountains + water-bottle refill stations near the
operator's current location. This is one of the most
useful POI categories for vanlife — being able to
quickly find a free water refill is a daily concern.

**OpenStreetMap amenity key:** `amenity=drinking_water`

**Overpass QL query string:**

```
data=[out:json][timeout:25];(node["amenity"="drinking_water"](around:{{ radius_m }},{{ lat }},{{ lon }}););out;
```

**Example result** (when the operator is parked in a
dense urban area):

```json
{
  "version": 0.6,
  "generator": "Overpass API 0.7.61.5",
  "elements": [
    {"type": "node", "id": 1234567890, "lat": 47.6062, "lon": -122.3321, "tags": {"amenity": "drinking_water", "operator": "City of Seattle"}},
    {"type": "node", "id": 1234567891, "lat": 47.6063, "lon": -122.3322, "tags": {"amenity": "drinking_water", "bottle": "yes"}},
    {"type": "node", "id": 1234567892, "lat": 47.6064, "lon": -122.3323, "tags": {"amenity": "drinking_water"}}
  ]
}
```

### §3.2 laundry — `shop=laundry`

The laundry POI category surfaces laundrettes +
laundromats near the operator's current location.

**OpenStreetMap amenity key:** `shop=laundry`

**Overpass QL query string:**

```
data=[out:json][timeout:25];(node["shop"="laundry"](around:{{ radius_m }},{{ lat }},{{ lon }});way["shop"="laundry"](around:{{ radius_m }},{{ lat }},{{ lon }}););out;
```

**Example result:**

```json
{
  "version": 0.6,
  "generator": "Overpass API 0.7.61.5",
  "elements": [
    {"type": "way", "id": 2345678901, "lat": 47.6065, "lon": -122.3324, "tags": {"shop": "laundry", "name": "Sudz Laundromat"}},
    {"type": "node", "id": 2345678902, "lat": 47.6066, "lon": -122.3325, "tags": {"shop": "laundry"}}
  ]
}
```

### §3.3 gym — `leisure=fitness_centre`

The gym POI category surfaces gyms + fitness centres
near the operator's current location.

**OpenStreetMap amenity key:** `leisure=fitness_centre`

**Overpass QL query string:**

```
data=[out:json][timeout:25];(node["leisure"="fitness_centre"](around:{{ radius_m }},{{ lat }},{{ lon }});way["leisure"="fitness_centre"](around:{{ radius_m }},{{ lat }},{{ lon }});relation["leisure"="fitness_centre"](around:{{ radius_m }},{{ lat }},{{ lon }}););out;
```

**Example result:**

```json
{
  "version": 0.6,
  "generator": "Overpass API 0.7.61.5",
  "elements": [
    {"type": "way", "id": 3456789012, "lat": 47.6067, "lon": -122.3326, "tags": {"leisure": "fitness_centre", "name": "Anytime Fitness"}}
  ]
}
```

### §3.4 dump_point — `amenity=sanitary_dump_station`

The dump_point POI category surfaces RV / motorhome
dump stations for grey + black tanks near the
operator's current location. This is critical for
vanlife — being able to quickly find a dump point is
essential for grey + black tank maintenance.

**OpenStreetMap amenity key:** `amenity=sanitary_dump_station`

**Overpass QL query string:**

```
data=[out:json][timeout:25];(node["amenity"="sanitary_dump_station"](around:{{ radius_m }},{{ lat }},{{ lon }}););out;
```

**Example result:**

```json
{
  "version": 0.6,
  "generator": "Overpass API 0.7.61.5",
  "elements": [
    {"type": "node", "id": 4567890123, "lat": 47.6068, "lon": -122.3327, "tags": {"amenity": "sanitary_dump_station", "fee": "no"}}
  ]
}
```

### §3.5 campsite — `tourism=camp_site`

The campsite POI category surfaces established
campgrounds with facilities near the operator's
current location.

**OpenStreetMap amenity key:** `tourism=camp_site`

**Overpass QL query string:**

```
data=[out:json][timeout:25];(node["tourism"="camp_site"](around:{{ radius_m }},{{ lat }},{{ lon }});way["tourism"="camp_site"](around:{{ radius_m }},{{ lat }},{{ lon }});relation["tourism"="camp_site"](around:{{ radius_m }},{{ lat }},{{ lon }}););out;
```

**Example result:**

```json
{
  "version": 0.6,
  "generator": "Overpass API 0.7.61.5",
  "elements": [
    {"type": "way", "id": 5678901234, "lat": 47.6069, "lon": -122.3328, "tags": {"tourism": "camp_site", "name": "Cape Disappointment State Park"}}
  ]
}
```

### §3.6 wild_camping — `tourism=wild_camping`

The wild_camping POI category surfaces legal /
tolerated overnight parking spots near the operator's
current location.

**OpenStreetMap amenity key:** `tourism=wild_camping`

**Overpass QL query string:**

```
data=[out:json][timeout:25];(node["tourism"="wild_camping"](around:{{ radius_m }},{{ lat }},{{ lon }}););out;
```

**Example result:**

```json
{
  "version": 0.6,
  "generator": "Overpass API 0.7.61.5",
  "elements": [
    {"type": "node", "id": 6789012345, "lat": 47.6070, "lon": -122.3329, "tags": {"tourism": "wild_camping", "tolerance": "yes"}}
  ]
}
```

### §3.7 supermarket — `shop=supermarket`

The supermarket POI category surfaces full-size
grocery stores near the operator's current location.

**OpenStreetMap amenity key:** `shop=supermarket`

**Overpass QL query string:**

```
data=[out:json][timeout:25];(node["shop"="supermarket"](around:{{ radius_m }},{{ lat }},{{ lon }});way["shop"="supermarket"](around:{{ radius_m }},{{ lat }},{{ lon }});relation["shop"="supermarket"](around:{{ radius_m }},{{ lat }},{{ lon }}););out;
```

**Example result:**

```json
{
  "version": 0.6,
  "generator": "Overpass API 0.7.61.5",
  "elements": [
    {"type": "way", "id": 7890123456, "lat": 47.6071, "lon": -122.3330, "tags": {"shop": "supermarket", "name": "Safeway"}}
  ]
}
```

### §3.8 fuel — `amenity=fuel`

The fuel POI category surfaces petrol / diesel
stations near the operator's current location.

**OpenStreetMap amenity key:** `amenity=fuel`

**Overpass QL query string:**

```
data=[out:json][timeout:25];(node["amenity"="fuel"](around:{{ radius_m }},{{ lat }},{{ lon }});way["amenity"="fuel"](around:{{ radius_m }},{{ lat }},{{ lon }}););out;
```

**Example result:**

```json
{
  "version": 0.6,
  "generator": "Overpass API 0.7.61.5",
  "elements": [
    {"type": "node", "id": 8901234567, "lat": 47.6072, "lon": -122.3331, "tags": {"amenity": "fuel", "brand": "Shell"}}
  ]
}
```

## §4 Setting the radius (the `select.rc_amenities_overlay_radius_km` tile)

The radius tile (`select.rc_amenities_overlay_radius_km`)
picks the max-distance radius from the operator's
current location. The recipe exposes the 1 / 2 / 5 / 10
/ 25 / 50 km options so the operator can pick a radius
based on how densely the area is populated:

- **1 km** — dense urban areas (city centres) where the
  operator only cares about POIs within walking
  distance. Use this for short stops in dense cities.
- **2 km** — medium urban areas (suburbs) where the
  operator cares about POIs within biking distance.
  Use this for short stops in suburban areas.
- **5 km** — the default; balanced for most vanlife
  scenarios (covers a typical town + the immediate
  outskirts). Use this when in doubt.
- **10 km** — sparse suburban / rural areas where the
  operator cares about POIs within driving distance.
  Use this for longer stops in rural areas.
- **25 km** — sparse rural areas where the operator
  cares about POIs within short-driving distance. Use
  this for multi-day stops in remote areas.
- **50 km** — very remote areas where the operator
  cares about POIs within long-driving distance. Use
  this for multi-week stops in very remote areas.

The recipe walks the operator through the trade-offs
between radius and cache size: a larger radius means
the upstream Overpass query takes longer (Overpass has
a soft timeout around 25 seconds for the public
instance) + the response is larger (more POIs to parse
+ store in the in-memory cache). A smaller radius means
faster queries + smaller cache but the operator may
miss POIs that are slightly outside the radius.

The recipe also walks the operator through the
trade-off between radius and rate-limit: a larger
radius means more POIs in the response (more JSON to
parse) but the Overpass query itself counts as one
request regardless of result size — so the rate-limit
picker (`number.rc_amenities_overlay_rate_limit_per_hour`)
is independent of the radius picker.

The recipe recommends starting with 5 km (the default)
+ adjusting up or down based on the operator's
experience in their typical travel areas.

## §5 Wiring the Overpass `rest:` sensor (the 8 category-specific `rest:` sensors)

The recipe walks the operator through wiring the 8
upstream Overpass `rest:` sensors (one per POI category).
Each `rest:` sensor configures the REST endpoint + the
JSON path + the scan interval pointing at
`https://overpass-api.de/api/interpreter` with the
category-specific query string. The recipe walks through
the canonical configuration pattern:

### §5.1 Generic `rest:` resource template

Every per-category `rest:` resource follows the same
pattern: the `resource` is the upstream Overpass API +
the `method` is POST + the `payload` is the category-
specific query string (templated with the operator's
current radius + current location) + the `scan_interval`
is 3600 seconds (1 hour). The `value_template` extracts
the POI count from the JSON response.

```yaml
resource: https://overpass-api.de/api/interpreter
method: POST
payload: >-
  data=[out:json][timeout:25];(node["<amenity_key>"="<amenity_value>"](around:{{ states('select.rc_amenities_overlay_radius_km') | int * 1000 }},{{ state_attr('device_tracker.rc_location_current', 'latitude') }},{{ state_attr('device_tracker.rc_location_current', 'longitude') }}););out;
scan_interval: 3600
sensor:
  - name: "Overpass <category> POI count (amenities overlay)"
    unique_id: rc_amenities_overlay_overpass_<category>_count
    unit_of_measurement: "POIs"
    value_template: "{{ value_json.elements | length }}"
```

### §5.2 The 8 per-category `rest:` sensors

The recipe walks the operator through creating 8
per-category `rest:` resources (one for each POI
category documented in §3). Each resource follows the
generic template above with the category-specific
`<amenity_key>` + `<amenity_value>` + `<category>`
substituted:

| Category | amenity_key | amenity_value | Sensor name | unique_id |
|---|---|---|---|---|
| water | `amenity` | `drinking_water` | `sensor.overpass_water_poi_count_amenities_overlay` | `rc_amenities_overlay_overpass_water_count` |
| laundry | `shop` | `laundry` | `sensor.overpass_laundry_poi_count_amenities_overlay` | `rc_amenities_overlay_overpass_laundry_count` |
| gym | `leisure` | `fitness_centre` | `sensor.overpass_gym_poi_count_amenities_overlay` | `rc_amenities_overlay_overpass_gym_count` |
| dump_point | `amenity` | `sanitary_dump_station` | `sensor.overpass_dump_point_poi_count_amenities_overlay` | `rc_amenities_overlay_overpass_dump_point_count` |
| campsite | `tourism` | `camp_site` | `sensor.overpass_campsite_poi_count_amenities_overlay` | `rc_amenities_overlay_overpass_campsite_count` |
| wild_camping | `tourism` | `wild_camping` | `sensor.overpass_wild_camping_poi_count_amenities_overlay` | `rc_amenities_overlay_overpass_wild_camping_count` |
| supermarket | `shop` | `supermarket` | `sensor.overpass_supermarket_poi_count_amenities_overlay` | `rc_amenities_overlay_overpass_supermarket_count` |
| fuel | `amenity` | `fuel` | `sensor.overpass_fuel_poi_count_amenities_overlay` | `rc_amenities_overlay_overpass_fuel_count` |

The recipe walks the operator through the per-category
YAML configuration blocks for each of the 8 sensors.

## §6 Wiring the offline cache (the optional RoamCore TileServer add-on)

The recipe walks the operator through the optional
RoamCore TileServer add-on (Wave 2 catalog #21 —
the legacy spec). The
TileServer add-on serves pre-cached POI mbtiles for
offline use. The §8.4 internet-or-cache guard depends
on the offline cache being populated; without the
TileServer add-on, the §8.4 guard will surface a "no
internet + no offline cache — overlay disabled" banner
whenever the upstream Overpass API is unreachable.

### §6.1 Installing the TileServer add-on

The operator installs the TileServer add-on via the HA
Supervisor panel (Add-on Store → RoamCore TileServer →
Install). The add-on is a thin wrapper around the
upstream mbtiles-server (a well-known static mbtiles
server since 2018).

### §6.2 Configuring the cache TTL

The operator configures the
`number.rc_amenities_overlay_cache_ttl_min` tile to
control how long the in-memory POI cache survives
(5–1440 minutes; default 60). The TileServer add-on
respects this TTL by serving cached POIs from the
local mbtiles store for the configured TTL before
falling back to the upstream Overpass query.

### §6.3 Populating the cache for the operator's most-travelled areas

The operator pre-populates the TileServer add-on's
mbtiles store with POI data for their most-travelled
areas. The recipe walks the operator through the
process: pre-fetch POIs for the operator's home area +
the operator's typical weekend destinations + the
operator's seasonal migration routes + dump them into
the TileServer add-on's mbtiles store.

### §6.4 Verifying the offline cache is active

The operator verifies that the offline cache is active
by checking that `binary_sensor.rc_amenities_overlay_is_
offline_cache_active` flips TRUE when the upstream
Overpass API is unreachable (or when the operator
manually switches the data source to "Offline cache"
via `select.rc_amenities_overlay_data_source`).

## §7 RoamCore contract entities (the 31 `rc_amenities_overlay_*` tiles)

The recipe walks the operator through configuring the
31 vendor-neutral `rc_amenities_overlay_*` contract
tiles + the upstream Overpass `rest:` sensors + the
`template:` sensors that aggregate them. The full
contract surface is:

- `input_boolean.rc_amenities_overlay_enabled` — master
  enable toggle (OFF by default; the operator must
  explicitly turn it ON before any POIs surface on the
  map). HA `input_boolean` helper, named
  `rc_amenities_overlay_enabled`, initial state `off`.

- `input_boolean.rc_amenities_overlay_fail_safe` —
  safety interlock (must be ON; the §8.1 fail-safe
  guard depends on it). HA `input_boolean` helper,
  named `rc_amenities_overlay_fail_safe`, initial state
  `on`.

- `select.rc_amenities_overlay_radius_km` — radius
  selector (1 / 2 / 5 / 10 / 25 / 50 km; default 5).
  HA `input_select` helper, named
  `rc_amenities_overlay_radius_km`, options
  `["1", "2", "5", "10", "25", "50"]`, initial
  `"5"`.

- `select.rc_amenities_overlay_data_source` — data
  source selector (Overpass / Offline cache / Auto;
  default Auto). HA `input_select` helper, named
  `rc_amenities_overlay_data_source`, options
  `["Overpass", "Offline cache", "Auto"]`, initial
  `"Auto"`.

- `number.rc_amenities_overlay_cache_ttl_min` — cache
  TTL in minutes (5–1440; default 60). HA `input_number`
  helper, named `rc_amenities_overlay_cache_ttl_min`,
  min `5`, max `1440`, step `5`, initial `60`.

- `number.rc_amenities_overlay_rate_limit_per_hour` —
  max Overpass requests per hour (1–100; default 30).
  HA `input_number` helper, named
  `rc_amenities_overlay_rate_limit_per_hour`, min `1`,
  max `100`, step `1`, initial `30`.

- `binary_sensor.rc_amenities_overlay_is_loaded` — TRUE
  when the overlay has at least one POI in view. HA
  `template:` binary_sensor, named
  `rc_amenities_overlay_is_loaded`, state
  `{{ states('sensor.rc_amenities_overlay_poi_count_total') | int(0) > 0 }}`.

- `binary_sensor.rc_amenities_overlay_is_rate_limited` —
  TRUE when Overpass returned 429 in the last hour.
  HA `template:` binary_sensor, named
  `rc_amenities_overlay_is_rate_limited`, state
  `{{ state_attr('sensor.overpass_water_poi_count_amenities_overlay', 'last_rate_limited') | default(false) }}`.

- `binary_sensor.rc_amenities_overlay_is_offline_cache_active` —
  TRUE when serving POIs from the offline cache because
  Overpass is unavailable / rate-limited / disconnected.
  HA `template:` binary_sensor, named
  `rc_amenities_overlay_is_offline_cache_active`, state
  `{{ states('select.rc_amenities_overlay_data_source') == 'Offline cache' or states('binary_sensor.rc_amenities_overlay_is_rate_limited') }}`.

- `sensor.rc_amenities_overlay_poi_count_total` — total
  POIs in view (all 8 categories). HA `template:`
  sensor, named `rc_amenities_overlay_poi_count_total`,
  state `{{ (states('sensor.rc_amenities_overlay_poi_count_water') | int(0)) + (states('sensor.rc_amenities_overlay_poi_count_laundry') | int(0)) + (states('sensor.rc_amenities_overlay_poi_count_gym') | int(0)) + (states('sensor.rc_amenities_overlay_poi_count_dump_point') | int(0)) + (states('sensor.rc_amenities_overlay_poi_count_campsite') | int(0)) + (states('sensor.rc_amenities_overlay_poi_count_wild_camping') | int(0)) + (states('sensor.rc_amenities_overlay_poi_count_supermarket') | int(0)) + (states('sensor.rc_amenities_overlay_poi_count_fuel') | int(0)) }}`.

- `sensor.rc_amenities_overlay_poi_count_water` — count
  of `amenity=drinking_water` POIs in view. HA
  `template:` sensor, named
  `rc_amenities_overlay_poi_count_water`, state
  `{{ states('sensor.overpass_water_poi_count_amenities_overlay') | int(0) }}`.

- `sensor.rc_amenities_overlay_poi_count_laundry` —
  count of `shop=laundry` POIs in view. HA `template:`
  sensor, named `rc_amenities_overlay_poi_count_laundry`,
  state `{{ states('sensor.overpass_laundry_poi_count_amenities_overlay') | int(0) }}`.

- `sensor.rc_amenities_overlay_poi_count_gym` — count
  of `leisure=fitness_centre` POIs in view. HA
  `template:` sensor, named
  `rc_amenities_overlay_poi_count_gym`, state
  `{{ states('sensor.overpass_gym_poi_count_amenities_overlay') | int(0) }}`.

- `sensor.rc_amenities_overlay_poi_count_dump_point` —
  count of `amenity=sanitary_dump_station` POIs in view.
  HA `template:` sensor, named
  `rc_amenities_overlay_poi_count_dump_point`, state
  `{{ states('sensor.overpass_dump_point_poi_count_amenities_overlay') | int(0) }}`.

- `sensor.rc_amenities_overlay_poi_count_campsite` —
  count of `tourism=camp_site` POIs in view. HA
  `template:` sensor, named
  `rc_amenities_overlay_poi_count_campsite`, state
  `{{ states('sensor.overpass_campsite_poi_count_amenities_overlay') | int(0) }}`.

- `sensor.rc_amenities_overlay_poi_count_wild_camping` —
  count of `tourism=wild_camping` POIs in view. HA
  `template:` sensor, named
  `rc_amenities_overlay_poi_count_wild_camping`, state
  `{{ states('sensor.overpass_wild_camping_poi_count_amenities_overlay') | int(0) }}`.

- `sensor.rc_amenities_overlay_poi_count_supermarket` —
  count of `shop=supermarket` POIs in view. HA
  `template:` sensor, named
  `rc_amenities_overlay_poi_count_supermarket`, state
  `{{ states('sensor.overpass_supermarket_poi_count_amenities_overlay') | int(0) }}`.

- `sensor.rc_amenities_overlay_poi_count_fuel` — count
  of `amenity=fuel` POIs in view. HA `template:` sensor,
  named `rc_amenities_overlay_poi_count_fuel`, state
  `{{ states('sensor.overpass_fuel_poi_count_amenities_overlay') | int(0) }}`.

- `sensor.rc_amenities_overlay_last_refresh_minutes_ago`
  — minutes since the last successful Overpass refresh.
  HA `template:` sensor, named
  `rc_amenities_overlay_last_refresh_minutes_ago`,
  state `{{ (now() - state_attr('sensor.overpass_water_poi_count_amenities_overlay', 'last_refreshed') | default(now())).total_seconds() / 60 | round(1) }}`.

- `sensor.rc_amenities_overlay_nearest_water_km` —
  distance to the nearest `amenity=drinking_water` POI
  in km (-1 when no POI in view). HA `template:`
  sensor, named `rc_amenities_overlay_nearest_water_km`,
  state `{{ state_attr('sensor.overpass_water_poi_count_amenities_overlay', 'nearest_km') | default(-1) | float }}`.

- `sensor.rc_amenities_overlay_nearest_campsite_km` —
  distance to the nearest `tourism=camp_site` POI in km
  (-1 when no POI in view). HA `template:` sensor,
  named `rc_amenities_overlay_nearest_campsite_km`,
  state `{{ state_attr('sensor.overpass_campsite_poi_count_amenities_overlay', 'nearest_km') | default(-1) | float }}`.

- `button.rc_amenities_overlay_refresh_now` —
  operator-triggered one-tap force-refresh from
  Overpass, bypassing the cache. HA `input_button`
  helper, named `rc_amenities_overlay_refresh_now`, with
  a script that triggers the upstream `rest:` resource
  refresh on all 8 POI categories.

- `button.rc_amenities_overlay_clear_cache` —
  operator-triggered one-tap clear the offline + in-
  memory POI cache. HA `input_button` helper, named
  `rc_amenities_overlay_clear_cache`, with a script that
  calls `rest.delete` on the upstream `rest:` resource's
  cached responses + clears the optional RoamCore
  TileServer add-on's cache for the operator's current
  area.

- `button.rc_amenities_overlay_enable_water` —
  operator-triggered one-tap enable the `water`
  category. HA `input_button` helper, named
  `rc_amenities_overlay_enable_water`, with a script
  that flips the per-category visibility toggle for
  water to ON.

- `button.rc_amenities_overlay_enable_laundry` — same
  pattern, for the `laundry` category.

- `button.rc_amenities_overlay_enable_gym` — same
  pattern, for the `gym` category.

- `button.rc_amenities_overlay_enable_dump_point` —
  same pattern, for the `dump_point` category.

- `button.rc_amenities_overlay_enable_campsite` —
  same pattern, for the `campsite` category.

- `button.rc_amenities_overlay_enable_wild_camping` —
  same pattern, for the `wild_camping` category.

- `button.rc_amenities_overlay_enable_supermarket` —
  same pattern, for the `supermarket` category.

- `button.rc_amenities_overlay_enable_fuel` — same
  pattern, for the `fuel` category.

## §8 Automations (the FIVE MANDATORY ones)

The recipe walks the operator through wiring the FIVE
§8 MANDATORY automations. Each automation is documented
below with the trigger + the condition + the action + a
real-world example.

### §8.1 Amenities-overlay must fail safe (no blank map if overlay fails)

The §8.1 fail-safe automation fires when
`input_boolean.rc_amenities_overlay_fail_safe` is OFF
OR when `binary_sensor.rc_amenities_overlay_is_loaded`
has been FALSE for > 5 minutes AND the upstream
Overpass query has returned an error. The automation
flips the fail-safe toggle back to ON + clears the
enable toggle (so the overlay goes back to the safe
OFF state) + writes an audit-log entry + fires a
critical notification warning the operator that the
overlay has auto-disabled.

```yaml
- alias: "Amenities overlay fail-safe guard"
  description: "Auto-disables the overlay if the upstream Overpass query has been failing for > 5 minutes."
  mode: single
  trigger:
    - platform: state
      entity_id: binary_sensor.rc_amenities_overlay_is_loaded
      to: "off"
      for: "00:05:00"
  condition:
    - condition: state
      entity_id: binary_sensor.rc_amenities_overlay_is_rate_limited
      state: "off"
    - condition: template
      value_template: "{{ states('sensor.rc_amenities_overlay_poi_count_total') | int(0) == 0 }}"
  action:
    - service: input_boolean.turn_off
      target:
        entity_id: input_boolean.rc_amenities_overlay_enabled
    - service: input_boolean.turn_on
      target:
        entity_id: input_boolean.rc_amenities_overlay_fail_safe
    - service: logbook.log
      data:
        name: "Amenities overlay"
        message: "fail-safe guard auto-disabled the overlay (upstream Overpass query failing for > 5 minutes)"
        entity_id: input_boolean.rc_amenities_overlay_enabled
    - service: persistent_notification.create
      data:
        title: "Amenities overlay auto-disabled"
        message: "The amenities overlay has been auto-disabled because the upstream Overpass query has been failing for > 5 minutes. Check the HA logs for the upstream `rest:` sensor's error details. The overlay will resume once the upstream query succeeds."
        notification_id: "rc_amenities_overlay_fail_safe"
```

### §8.2 Amenities-overlay must be rate-limited + cache results

The §8.2 rate-limit automation fires when
`number.rc_amenities_overlay_rate_limit_per_hour`
Overpass requests have been made in the last hour OR
when `sensor.rc_amenities_overlay_last_refresh_minutes_
ago` < `number.rc_amenities_overlay_cache_ttl_min`. The
automation surfaces a "rate-limited / using cached data"
banner in the map page + flips
`binary_sensor.rc_amenities_overlay_is_rate_limited` to
TRUE + switches the data source to the offline cache.

```yaml
- alias: "Amenities overlay rate-limit guard"
  description: "Auto-switches to offline cache when Overpass returns 429."
  mode: single
  trigger:
    - platform: state
      entity_id: binary_sensor.rc_amenities_overlay_is_rate_limited
      to: "on"
  action:
    - service: select.select_option
      target:
        entity_id: select.rc_amenities_overlay_data_source
        option: "Offline cache"
    - service: persistent_notification.create
      data:
        title: "Amenities overlay rate-limited"
        message: "The amenities overlay has been rate-limited by the upstream Overpass API. Switching to the offline cache. The overlay will resume Overpass queries once the rate-limit window expires."
        notification_id: "rc_amenities_overlay_rate_limited"
    - service: logbook.log
      data:
        name: "Amenities overlay"
        message: "rate-limit guard auto-switched to offline cache (Overpass returned 429)"
        entity_id: select.rc_amenities_overlay_data_source
```

### §8.3 Amenities-overlay must be user-configurable (categories on/off)

The §8.3 user-configurable automation fires when ANY
of the per-category visibility toggles flips OFF AND
`input_boolean.rc_amenities_overlay_enabled` is ON.
The automation re-fetches the POI list from Overpass
(or the offline cache if rate-limited) with only the
enabled categories + writes an audit-log entry showing
the new enabled-category list.

```yaml
- alias: "Amenities overlay user-configurable guard"
  description: "Re-fetches the POI list when a per-category visibility toggle flips."
  mode: single
  trigger:
    - platform: state
      entity_id: button.rc_amenities_overlay_enable_water
    - platform: state
      entity_id: button.rc_amenities_overlay_enable_laundry
    - platform: state
      entity_id: button.rc_amenities_overlay_enable_gym
    - platform: state
      entity_id: button.rc_amenities_overlay_enable_dump_point
    - platform: state
      entity_id: button.rc_amenities_overlay_enable_campsite
    - platform: state
      entity_id: button.rc_amenities_overlay_enable_wild_camping
    - platform: state
      entity_id: button.rc_amenities_overlay_enable_supermarket
    - platform: state
      entity_id: button.rc_amenities_overlay_enable_fuel
  condition:
    - condition: state
      entity_id: input_boolean.rc_amenities_overlay_enabled
      state: "on"
  action:
    - service: button.press
      target:
        entity_id: button.rc_amenities_overlay_refresh_now
    - service: logbook.log
      data:
        name: "Amenities overlay"
        message: "user-configurable guard re-fetched the POI list (per-category visibility toggle changed)"
        entity_id: input_boolean.rc_amenities_overlay_enabled
```

### §8.4 Amenities-overlay must require internet OR a populated offline cache

The §8.4 internet-or-cache automation fires when
`binary_sensor.rc_amenities_overlay_is_loaded` is FALSE
AND the offline cache has never been populated (the
operator has never wired the optional RoamCore TileServer
add-on). The automation surfaces a "no internet + no
offline cache — overlay disabled" banner in the map page
+ disables the overlay + writes an audit-log entry.

```yaml
- alias: "Amenities overlay internet-or-cache guard"
  description: "Auto-disables the overlay when no internet AND no offline cache."
  mode: single
  trigger:
    - platform: state
      entity_id: binary_sensor.rc_amenities_overlay_is_loaded
      to: "off"
      for: "00:02:00"
  condition:
    - condition: state
      entity_id: binary_sensor.rc_amenities_overlay_is_offline_cache_active
      state: "off"
  action:
    - service: input_boolean.turn_off
      target:
        entity_id: input_boolean.rc_amenities_overlay_enabled
    - service: persistent_notification.create
      data:
        title: "Amenities overlay disabled (no internet + no offline cache)"
        message: "The amenities overlay has been auto-disabled because there is no internet connection AND no populated offline cache. Either restore internet connectivity or populate the offline cache (via the RoamCore TileServer add-on) to resume the overlay."
        notification_id: "rc_amenities_overlay_no_cache"
    - service: logbook.log
      data:
        name: "Amenities overlay"
        message: "internet-or-cache guard auto-disabled the overlay (no internet + no offline cache)"
        entity_id: input_boolean.rc_amenities_overlay_enabled
```

### §8.5 Amenities-overlay auto-disables when vehicle is moving > N km/h

The §8.5 vehicle-moving automation fires when
`device_tracker.rc_location_current` reports a speed >
10 km/h AND `input_boolean.rc_amenities_overlay_enabled`
is ON. The automation clears the enable toggle (so the
overlay goes back to the safe OFF state while the
vehicle is moving — POIs don't make sense at highway
speeds) + writes an audit-log entry + fires a
notification. The automation re-enables the overlay once
the vehicle speed drops below 5 km/h for > 2 minutes
(so the overlay auto-resumes when parked).

```yaml
- alias: "Amenities overlay vehicle-moving guard"
  description: "Auto-disables the overlay when the vehicle is moving > 10 km/h; auto-resumes when parked > 2 minutes."
  mode: single
  trigger:
    - platform: numeric_state
      entity_id: device_tracker.rc_location_current
      attribute: speed
      above: 10
      for: "00:00:30"
  condition:
    - condition: state
      entity_id: input_boolean.rc_amenities_overlay_enabled
      state: "on"
  action:
    - service: input_boolean.turn_off
      target:
        entity_id: input_boolean.rc_amenities_overlay_enabled
    - service: logbook.log
      data:
        name: "Amenities overlay"
        message: "vehicle-moving guard auto-disabled the overlay (speed > 10 km/h)"
        entity_id: input_boolean.rc_amenities_overlay_enabled

- alias: "Amenities overlay auto-resume on park"
  description: "Auto-resumes the overlay when the vehicle has been parked > 2 minutes (speed < 5 km/h)."
  mode: single
  trigger:
    - platform: numeric_state
      entity_id: device_tracker.rc_location_current
      attribute: speed
      below: 5
      for: "00:02:00"
  condition:
    - condition: state
      entity_id: input_boolean.rc_amenities_overlay_enabled
      state: "off"
  action:
    - service: input_boolean.turn_on
      target:
        entity_id: input_boolean.rc_amenities_overlay_enabled
    - service: logbook.log
      data:
        name: "Amenities overlay"
        message: "auto-resumed the overlay (vehicle parked > 2 minutes)"
        entity_id: input_boolean.rc_amenities_overlay_enabled
```

## §9 Troubleshooting (6 entries)

### §9.1 Overpass returns 429 rate-limited

If Overpass returns 429 (rate-limited), the §8.2
rate-limit automation should fire and switch the data
source to the offline cache. If the automation doesn't
fire, check:

1. **Is the §8.2 automation enabled?** Verify the
   automation is in the `automation:` list in the
   operator's `configuration.yaml` or `packages/
   roamcore_amenities_overlay.yaml`.
2. **Is the trigger entity correct?** Verify the trigger
   points at `binary_sensor.rc_amenities_overlay_is_rate_limited`.
3. **Is the upstream `rest:` sensor reporting rate-limit
   correctly?** Check the HA logbook for the upstream
   `rest:` sensor's rate-limit detection. The §8.2
   guard depends on the upstream `rest:` sensor's
   `last_rate_limited` attribute.

If the §8.2 automation fires but the data source
doesn't switch, check:

4. **Is the operator's HA user authorized to call
   `select.select_option`?** Verify the operator's HA
   user has the `select` permissions.

### §9.2 Overpass returns empty result

If Overpass returns an empty result (no POIs in the
query), the per-category count tile will show 0 + the
§8.1 fail-safe guard will eventually fire (after 5
minutes). If the operator is in an area where POIs
should exist, check:

1. **Is the operator's current location correct?**
   Verify `device_tracker.rc_location_current` is
   reporting the correct latitude + longitude.
2. **Is the radius large enough?** Try increasing the
   radius to 25 km or 50 km and re-fetch.
3. **Is the Overpass query string correct?** Verify
   the query string in the upstream `rest:` resource
   matches the expected Overpass QL syntax. Try the
   query manually with curl.

### §9.3 Offline cache never gets populated

If the operator has installed the RoamCore TileServer
add-on (Wave 2 catalog #21) but the offline cache is
never populated, check:

1. **Is the TileServer add-on running?** Verify the
   add-on is running in the HA Supervisor panel.
2. **Is the cache populated for the operator's current
   area?** The TileServer add-on pre-caches POIs for
   the operator's most-travelled areas; if the operator
   is in an area that wasn't pre-cached, the cache will
   be empty.
3. **Is the §8.4 internet-or-cache guard incorrectly
   firing?** Verify the §8.4 guard is wired correctly
   — if it fires when the offline cache IS populated,
   the operator may have the offline-cache-active
   detection logic wrong.

### §9.4 Per-category counts are 0 even with POIs visible on map

If the per-category count tiles show 0 even though the
operator can see POIs on the map, check:

1. **Are the per-category `rest:` sensors configured
   correctly?** Verify each per-category `rest:` sensor
   points at the correct Overpass endpoint + the correct
   query string for the category.
2. **Are the per-category `template:` sensors wired
   correctly?** Verify each per-category `template:`
   sensor points at the correct upstream `rest:` sensor
   (not a typo in the entity id).
3. **Are the per-category `rest:` sensors being
   rate-limited?** Verify the upstream `rest:` sensor's
   logbook for 429 responses.

### §9.5 `rest:` sensor shows `unknown`

If the upstream `rest:` sensor shows `unknown`, check:

1. **Is the upstream Overpass API reachable from the HA
   host?** Verify with curl from the HA host's shell.
2. **Is the `rest:` resource configured correctly?**
   Verify the resource URL + the method + the payload +
   the scan interval in the `rest:` configuration.
3. **Is the Overpass QL query string valid?** Verify
   the query string is valid Overpass QL syntax (use
   the Overpass QL validator at
   https://overpass-turbo.eu/).

### §9.6 Map page loads blank when overlay enabled

If the map page loads blank when the overlay is
enabled, check:

1. **Is the §8.1 fail-safe guard wired?** If the
   §8.1 guard isn't wired, a failed Overpass query can
   leave the operator with a blank map. Wire the §8.1
   guard immediately.
2. **Is the upstream Overpass query returning data?**
   Verify the upstream `rest:` sensor's value is not
   `unknown` / `unavailable`.
3. **Is the basemap mode selected?** If the basemap mode
   is set to "none" or "blank", the map page will load
   blank even without the overlay. Verify the basemap
   mode is set to a valid tile source (see the map-
   dashboard recipe for the basemap mode picker).

## §10 Privacy

The amenities-overlay recipe is privacy-respecting by
default:

1. **No RoamCore-side telemetry.** RoamCore does not
   collect any telemetry about which POIs the operator
   queries + how often they query + where they are
   located. The recipe is entirely local.

2. **Overpass API is queried from HA directly.** The
   HA host queries the upstream Overpass API directly
   (via the `rest:` integration) — no proxy + no
   RoamCore-controlled server sits between the HA host
   and Overpass.

3. **No telemetry goes to RoamCore.** The RoamCore
   wrapper does not log any POI data + the contract
   layer is entirely local. The OpenClaw queries on the
   31 contract tiles run locally; they do not call any
   RoamCore-controlled API.

4. **No telemetry goes to iOverlander / OSM / Wikimedia.**
   The recipe uses the upstream Overpass API (an
   OpenStreetMap project) but does NOT send any
   telemetry to iOverlander / OSM / Wikimedia. The
   Overpass API itself does not log client IPs (per
   the Overpass privacy policy at
   https://wiki.openstreetmap.org/wiki/Overpass_API/
   Privacy_Policy).

5. **The optional RoamCore TileServer add-on is
   entirely local.** The TileServer add-on serves pre-
   cached POI mbtiles from the operator's local network;
   no data leaves the operator's network when using the
   offline cache.

6. **POI counts + cache state are operator-owned.** The
   `sensor.rc_amenities_overlay_poi_count_*` tiles +
   the `binary_sensor.rc_amenities_overlay_is_*` tiles
   are operator-owned via the HA core logbook; the
   operator can inspect + export + delete them at any
   time.

7. **The §8 automations' audit-log entries are
   operator-owned.** The §8.1 + §8.2 + §8.3 + §8.4 +
   §8.5 automations write audit-log entries via the HA
   core logbook; the operator can inspect + export +
   delete them at any time.

## §11 Promoting to tier-a

Tier-a would require a RoamCore-owned amenities-overlay
engine + integration code + integration tests against a
real amenities-overlay engine bench. The bench would be
a controlled environment with canned fixture responses
for Overpass queries + canned fixture responses for
rate-limit events + canned fixture responses for
offline-cache fallbacks + canned fixture responses for
vehicle-moving events — all wired together in a
controlled environment.

The recipe ships the §11 tier-a promotion outline (the
recipe is sound but we cannot claim tier-a until the
bench exists). The §11 tier-a promotion outline
includes:

1. **Real Overpass bench.** A controlled environment
   with canned fixture responses for Overpass queries
   (a mock Overpass server that returns canned JSON
   responses for each of the 8 POI categories). The
   bench would be run on every PR + every merge to
   main.

2. **Populated offline cache on CI.** A populated
   RoamCore TileServer add-on instance on CI with POI
   mbtiles for a representative test area. The bench
   would verify that the §8.4 internet-or-cache guard
   correctly detects a populated offline cache.

3. **RoamCore-owned operator-wired setup flow walking
   the 8 categories.** A RoamCore-owned operator-wired
   setup flow that walks the operator through the 8
   POI categories (water / laundry / gym / dump_point /
   campsite / wild_camping / supermarket / fuel) +
   the per-category visibility toggles + the radius
   selector + the cache-TTL picker + the rate-limit
   picker + the data-source selector + the §8
   automations.

4. **Integration tests asserting a mock Overpass
   response with 5 POIs surfaces as `count_total = 5`.**
   An integration test that wires the upstream `rest:`
   sensor to a mock Overpass server that returns a
   canned JSON response with 5 POI nodes + verifies
   that `sensor.rc_amenities_overlay_poi_count_total`
   surfaces as `5` + verifies that the per-category
   counts add up.

5. **The 5 safety guards all flip when wired to canned
   fixture responses.** Integration tests that wire each
   of the 5 §8 MANDATORY automations to canned fixture
   responses for the trigger events (Overpass failure
   for §8.1; Overpass 429 for §8.2; per-category
   toggle flip for §8.3; no-internet + no-cache for
   §8.4; vehicle speed > 10 km/h for §8.5) + verify
   that the automation's action fires correctly.

None of those are shipped at tier-b; the picker ships
tier-b honestly.

## §12 Files in this connection + cross-references

This recipe is the canonical howto for the
`connections/amenities-overlay/` tier-b recipe
connection. The other files in this connection are:

- `connection.yml` — the source-of-truth manifest (the
  umbrella for the 31 `rc_amenities_overlay_*`
  contract tiles + the §8 FIVE MANDATORY automations).
- `__init__.py` — `DOMAIN = "amenities_overlay"`
  marker for the audit.
- `README.md` — folder overview + 8-category summary +
  31-tile table + 5-§8-automation summary +
  supersession pointer.
- `tests/test_connection_yml.py` — 7 manifest-honesty
  tests.

Cross-references to other RoamCore connections +
catalog pages:

- Map dashboard (the basemap mode + the map page where
  the overlay is rendered): `connections/map-dashboard/`
  (Wave 3 #66).
- Time-atomic (the §8.5 vehicle-moving guard's 2-minute
  parked timer): `connections/time-atomic/` (Wave 3 #55).
- Bluetooth/Wi-Fi presence (the §8.5 vehicle-moving
  guard's `device_tracker.rc_location_current` speed
  attribute): `connections/bluetooth-wifi-presence/`
  (Wave 3 #42).
- Mode (the §8.3 user-configurable guard's audit-log
  entry's mode-change context): `connections/mode/`
  (Wave 3 #61).
- Demo mode (the §8.4 internet-or-cache guard's "demo
  mode is ON — values are not real" banner pattern):
  `connections/demo-mode/` (Wave 3 #62).
- Advanced mode (the §8.5 vehicle-moving guard's
  "operator can override the auto-disable" affordance):
  `connections/advanced-mode/` (Wave 3 #63).
- RoamCore TileServer add-on (the optional offline POI
  cache — Wave 2 catalog #21): `docs/catalog/map/
  roamcore-tileserver-addon.md`.
- HA core `rest:` integration (the canonical HTTP
  query primitive): https://www.home-assistant.io/
  integrations/rest/.
- HA core `input_boolean` integration (the canonical
  master enable toggle helper): https://www.home-
  assistant.io/integrations/input_boolean/.
- HA core `input_select` integration (the canonical
  radius + data-source selector helper): https://www.
  home-assistant.io/integrations/input_select/.
- HA core `input_number` integration (the canonical
  cache-TTL + rate-limit picker helper): https://www.
  home-assistant.io/integrations/input_number/.
- HA core `template:` integration (the canonical per-
  category count + nearest-POI derivation): https://www.
  home-assistant.io/integrations/template/.
- Overpass API (the canonical POI query engine — an
  OpenStreetMap project, fully open + free +
  community-run since 2013): https://wiki.openstreetmap.
  org/wiki/Overpass_API.
- RoamCore entity naming (the `map` + `amenities_overlay`
  subsystems were added by this slice):
  `docs/reference/rc-entity-naming.md`.
- Legacy catalog page (now superseded by this slice):
  the legacy spec.