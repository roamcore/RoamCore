# Mock location + track replay — tier-a native connection

This is the full howto for the `connections/mock-location-and-tracks/`
tier-a native connection. It walks through the dev/demo polyline
generator (the Python script + the YAML packages + the 6 built-in
presets + the 9 `rc_map_mock_*` contract tiles + the integration
with Trip Wrapped + the map page + the §11 promotion path to a real
GPS source via `connections/traccar/`), explains the tier-a audit
markers (`wizard.connection_kind: native` + `install.kind:
ha_package` + `install.config_flow: false` + no `config_flow.py` +
`__init__.py` exports `DOMAIN = "mock_location"`), and documents the
§9 troubleshooting flow (8 entries covering the most common operator
errors).

This is the **first tier-a connection slice in Wave 3** — all prior
Wave 3 slices were tier-b recipe-over-upstream. The tier-a audit
pattern this slice establishes is:

- `wizard.connection_kind: native` (NOT `recipe`).
- `install.kind: ha_package` (NOT `recipe-over-upstream`).
- `install.packages: [list of YAML files in
  homeassistant/packages/]`.
- `install.config_flow: false` (tier-a DOES NOT use config_flow.py
  because RoamCore owns the integration as a package — there is no
  upstream vendor integration to wrap).
- `__init__.py` exports `DOMAIN = "<audit_short_name>"` (the audit
  convention uses the singular short name; for the map category this
  is `mock_location`).
- The integration code IS the package — there is nothing for a
  `config_flow.py` to wrap.

## §1 What is mock location + track replay in RoamCore?

Mock location + track replay is the **dev/demo polyline generator**
for the RoamCore map page. It generates a deterministic synthetic GPS
track as a GeoJSON LineString and exposes it as a semicolon-separated
`input_text.rc_map_mock_location_trail` of lat,lon pairs that the
`<MapMockPolyline />` dashboard tile + the Trip Wrapped dev/demo
HTML report can render without any real Traccar GPS data.

The mock is **opt-in** via `input_boolean.rc_map_mock_enabled`
(default FALSE → OFF). When the operator enables it, the map page
renders the synthetic polyline. When disabled, the map page falls
back to real Traccar (if `connections/traccar/` is enabled) or to an
empty map (if no real GPS source is wired).

Key characteristics:

- **Deterministic** — the same preset + the same points-per-leg +
  the same jitter always produces the same polyline (modulo the
  random jitter applied per-point, which is seeded from the jitter
  value). Useful for integration tests + marketing screenshots.
- **Dependency-free** — the Python generator uses stdlib only
  (`argparse` + `json` + `math` + `random` + `os` + `datetime`). No
  `pip install` is required on HAOS.
- **No cloud call home** — the polyline is generated locally and
  written to `/config/www/roamcore/mock/track.geojson`. The map tile
  reads the file from the local HA `/local/` endpoint.
- **Auto-runs on HA startup** — the existing
  `automation.rc_mock_track_generate_on_startup` automation (in
  `homeassistant/packages/roamcore_mock_track.yaml`) fires on
  `homeassistant.start` event and regenerates the polyline.
- **Opt-in only** — `input_boolean.rc_map_mock_enabled` defaults to
  FALSE; the operator MUST toggle it ON to render the mock on the
  map page.

RoamCore owns all of the assets natively — there is NO external
broker / device / vendor dependency. This is the tier-a audit
marker.

## §2 Prerequisites

The operator MUST satisfy these prerequisites BEFORE the mock will
work end-to-end:

**HA Core:** 2023.8 or newer (the upstream `input_boolean` +
`input_text` + `input_select` + `input_number` + `button` + `template:`
+ `shell_command` + `script:` + `automation:` domains have all been
part of HA Core for years; 2023.8 is the RoamCore-wide minimum for
`template:` + `button:` + `select:` parity).

**RoamCore YAML packages:** confirm that the three mock YAML files
are wired into your HA Core `configuration.yaml`. RoamCore's
`homeassistant/configuration_addon.yaml` uses
`!include_dir_named packages` which auto-includes everything under
`homeassistant/packages/`. If you wire RoamCore manually, add these
three lines under `homeassistant.packages:`:

```yaml
homeassistant:
  packages:
    - roamcore_mock_track
    - roamcore_mock_location_trail
    - roamcore_dev_mocks
```

**Python generator path:** confirm that
`homeassistant/tools/mock_track/generate.py` is readable by the
`shell_command` user. HAOS mounts the repo at `/config`; the
`shell_command.rc_mock_track_generate` is hardcoded to
`/config/tools/mock_track/generate.py`. If your HAOS mount differs
(e.g. you symlinked RoamCore somewhere else), edit the path in
`homeassistant/packages/roamcore_mock_track.yaml`.

**Python 3.11+** for the generator (it uses PEP 604 union syntax
`list[tuple[float, float]]` — supported by Python 3.10+ but the rest
of the RoamCore HAOS image is Python 3.11+).

**No upstream vendor integration** — the mock has zero external
broker / device / vendor dependency. No Traccar receiver, no MQTT
broker, no Zigbee/Z-Wave stick required.

**Operator prerequisites:**

- The operator has decided whether to use the mock for dev/demo or
  enable a real Traccar source via `connections/traccar/` (Wave 3
  #48). The two are mutually exclusive on the map page — only one
  polyline source is rendered at a time.
- The operator has chosen a preset (`uk_roadtrip` is the default
  for new installs — see §4 for the full preset list).

## §3 Quick start

The mock auto-runs on HA startup via the existing
`automation.rc_mock_track_generate_on_startup` automation (in
`homeassistant/packages/roamcore_mock_track.yaml`) — no operator
action is required for the package to load. The operator opts in to
rendering the mock polyline on the map page by following these three
steps:

1. **Toggle the master switch.** From the RoamCore Settings → Map →
   Mock panel, toggle `input_boolean.rc_map_mock_enabled` from FALSE
   to ON. (Default FALSE; the mock is opt-in.)
2. **Pick a preset.** From the same panel, set
   `input_select.rc_map_mock_preset` to one of the 6 built-in presets
   (`uk_roadtrip` / `us_west_coast` / `alps_loop` /
   `desert_southwest` / `scandinavia_north` / `custom` — see §4 for
   the full preset list).
3. **Click Generate now.** Click `button.rc_map_mock_generate_now`
   (this fires `script.rc_mock_track_generate` which runs the Python
   generator with the current preset / points-per-leg / jitter values
   and writes the GeoJSON to `/config/www/roamcore/mock/track.geojson`).
   Alternatively, wait for the next HA restart (the startup
   automation will fire automatically).

Reload the RoamCore map page — the synthetic polyline should appear.
The legend readout (top-right of the `<MapMockPolyline />` tile)
shows the current `sensor.rc_map_mock_track_length_km` (total polyline
length in km, haversine sum) + the current
`sensor.rc_map_mock_track_point_count` (number of lat,lon pairs) +
the `binary_sensor.rc_map_mock_track_fresh` state (TRUE when
generated < 1 hour ago).

## §4 The 6 built-in presets

The Python generator ships 6 built-in presets. Each preset is a
hardcoded list of (lat, lon) waypoints that the generator interpolates
between with `points-per-leg` per segment + per-point Gaussian jitter
of `jitter-m` meters.

### §4.1 `uk_roadtrip` (the default)

A scenic 9-waypoint circular loop around the UK + Ireland: London →
Cambridge → Manchester → Lake District → Edinburgh → Belfast →
Dublin → Birmingham → back to London. ~1,500 km total. Curvature:
high (many waypoints, lots of segments). Scenery: English countryside
+ Scottish highlands + Irish coast.

### §4.2 `us_west_coast`

A long sweeping drive down the US Pacific Coast Highway: Seattle →
Portland → San Francisco → Los Angeles → San Diego. ~2,000 km total.
Curvature: medium (fewer waypoints, longer legs). Scenery: ocean
cliffs + redwoods + Big Sur.

### §4.3 `alps_loop`

A tight mountain loop through the Alps: Geneva → Chamonix → Turin →
Milan → Bern → back to Geneva. ~800 km total. Curvature: very high
(many sharp turns, mountain switchbacks). Scenery: glaciers + alpine
lakes + mountain passes.

### §4.4 `desert_southwest`

A sprawling desert drive through the US Southwest: Las Vegas → Grand
Canyon → Monument Valley → Moab → Zion → back to Las Vegas. ~1,200
km total. Curvature: low (long straight legs between landmarks).
Scenery: red rock + canyons + mesas.

### §4.5 `scandinavia_north`

A long Nordic sweep through Scandinavia: Stockholm → Oslo → Bergen →
Trondheim → Tromsø → back to Stockholm. ~3,000 km total. Curvature:
medium (fjord coastlines + long inland legs). Scenery: fjords +
northern lights (in season) + arctic tundra.

### §4.6 `custom`

If `input_select.rc_map_mock_preset = custom`, the generator reads a
custom polyline from a JSON file (see §6 for the authoring workflow).
If no custom polyline is found, the generator falls back to the
`uk_roadtrip` preset with a warning in the HA Core log.

## §5 The `rc_map_mock_*` contract tiles

The connection contributes 9 `rc_map_mock_*` contract tiles per
`docs/reference/rc-entity-naming.md` §map subsystem (the `map`
subsystem was added to the allowed subsystems list alongside this
slice — see the Cron-handoff doc for the rationale). The tiles:

| Tile                                              | Type           | Purpose                                                                                                                                                                                                  |
| ------------------------------------------------- | -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `input_boolean.rc_map_mock_enabled`               | input_boolean  | Master toggle (default FALSE). The map page reads this to decide mock-vs-real.                                                                                                                            |
| `input_text.rc_map_mock_location_trail`           | input_text     | Semicolon-separated lat,lon pairs. The `<MapMockPolyline />` tile renders this as a polyline on the map.                                                                                                  |
| `input_select.rc_map_mock_preset`                 | input_select   | Preset selector (`uk_roadtrip` / `us_west_coast` / `alps_loop` / `desert_southwest` / `scandinavia_north` / `custom`).                                                                                     |
| `input_number.rc_map_mock_points_per_leg`         | input_number   | Per-leg point density (10–500, default 80).                                                                                                                                                              |
| `input_number.rc_map_mock_jitter_m`               | input_number   | Per-point jitter in meters (0–100, default 10).                                                                                                                                                          |
| `button.rc_map_mock_generate_now`                 | button         | Calls `script.rc_mock_track_generate` (runs the Python generator with the current preset / points-per-leg / jitter values and writes the GeoJSON).                                                       |
| `sensor.rc_map_mock_track_length_km`              | sensor         | Template sensor over `input_text.rc_map_mock_location_trail`; computes the total polyline length in km (haversine sum over the lat,lon pairs).                                                            |
| `sensor.rc_map_mock_track_point_count`             | sensor         | Template sensor over `input_text.rc_map_mock_location_trail`; counts the number of lat,lon pairs.                                                                                                       |
| `binary_sensor.rc_map_mock_track_fresh`           | binary_sensor  | TRUE when the polyline was generated < 1 hour ago (the operator can use this to detect stale mocks after a long HA downtime).                                                                             |

How each upstream `input_*` / `button` / `template:` sensor exposes
them:

- `input_boolean.rc_map_mock_enabled` — directly from
  `homeassistant/packages/roamcore_mock_location_trail.yaml` (or a
  new `roamcore_mock_toggle.yaml` package added alongside this slice
  if you want to keep the toggle separate from the trail).
- `input_text.rc_map_mock_location_trail` — directly from
  `homeassistant/packages/roamcore_mock_location_trail.yaml`
  (already exists on disk).
- `input_select.rc_map_mock_preset` — from
  `homeassistant/packages/roamcore_mock_track.yaml` (added by this
  slice).
- `input_number.rc_map_mock_points_per_leg` + `input_number.rc_map_mock_jitter_m`
  — from `homeassistant/packages/roamcore_mock_track.yaml` (added by
  this slice).
- `button.rc_map_mock_generate_now` — from
  `homeassistant/packages/roamcore_mock_track.yaml` (added by this
  slice; calls `script.rc_mock_track_generate`).
- `sensor.rc_map_mock_track_length_km` +
  `sensor.rc_map_mock_track_point_count` +
  `binary_sensor.rc_map_mock_track_fresh` — `template:` sensors
  derived from `input_text.rc_map_mock_location_trail`. The
  `length_km` sensor uses a haversine sum; the `point_count` sensor
  counts the semicolon-separated pairs; the `fresh` binary_sensor
  uses a `as_timestamp(...)` check on the GeoJSON `properties.generatedAt`
  field.

## §6 Custom polyline authoring

If `input_select.rc_map_mock_preset = custom`, the generator reads a
custom polyline from `/config/www/roamcore/mock/custom_track.geojson`.
The operator authors this file using one of these workflows:

1. **geojson.io** — open <https://geojson.io>, draw a polyline on
   the map, export as GeoJSON, copy the `coordinates` array into a
   file with the schema below.
2. **Google Maps** — draw a route in Google Maps, export the
   waypoints (Google Maps doesn't have a direct export; use the
   "Add directions" + "Copy as KML" + convert to GeoJSON workflow).
3. **OpenStreetMap** — use the OSM "GPS traces" feature to draw a
   trace + export as GeoJSON.

The required GeoJSON schema:

```json
{
  "type": "Feature",
  "properties": {
    "name": "My custom trip"
  },
  "geometry": {
    "type": "LineString",
    "coordinates": [
      [lon1, lat1],
      [lon2, lat2],
      ...
    ]
  }
}
```

Note that GeoJSON uses `[lon, lat]` order (NOT `[lat, lon]`). The
generator validates this on load and rejects with a clear error if
the schema is malformed.

Validation: the operator can dry-run the custom polyline by clicking
`button.rc_map_mock_generate_now` and checking the HA Core log for
the generator's output (success: "Wrote 42 points to
/config/www/roamcore/mock/track.geojson"; failure: "GeoJSON schema
invalid: expected 'LineString', got 'Point'").

The generator also writes the converted `[lat, lon]` pairs into
`input_text.rc_map_mock_location_trail` (semicolon-separated) so the
map tile can render the polyline directly without parsing the
GeoJSON in the browser.

## §7 Integration with Trip Wrapped

`connections/trip-wrapped/` (Wave 3 #69) treats the mock as Traccar
data when generating the dev/demo HTML report. If the operator
hasn't enabled a real Traccar source, Trip Wrapped reads
`input_boolean.rc_map_mock_enabled` + `sensor.rc_map_mock_track_length_km`
+ `sensor.rc_map_mock_track_point_count` to populate the report's
"Total distance" + "Number of stops" + "Trip polyline" sections.

This is useful for:

- Marketing screenshots (deterministic synthetic routes, no need to
  wait for real trip data).
- Integration tests (assert the HTML report structure is correct
  without needing a real GPS feed).
- Dev demos (show off the report's visual design before the operator
  has any real trip data).

The mock polyline is rendered in the report with a distinct color +
a "Mock (dev/demo)" badge in the legend, so it's never confused
with real trip data.

## §8 Integration with the map page

`connections/map-dashboard/` (Wave 3 #66) reads
`input_boolean.rc_map_mock_enabled` to decide mock-vs-real. When the
boolean is TRUE, the map page renders the synthetic polyline via the
`<MapMockPolyline />` tile. When FALSE, the map page renders the
real Traccar track (if `connections/traccar/` is enabled) or an
empty map (if no real GPS source is wired).

The `<MapMockPolyline />` tile reads:

- `input_text.rc_map_mock_location_trail` for the polyline
  coordinates.
- `sensor.rc_map_mock_track_length_km` for the legend readout
  ("X km").
- `sensor.rc_map_mock_track_point_count` for the legend readout
  ("Y points").
- `binary_sensor.rc_map_mock_track_fresh` for the staleness badge
  (green checkmark when fresh, orange warning when stale).

The mock polyline is rendered with a distinct color (orange #FF6F00)
+ a "Mock (dev/demo)" badge in the tile header, so it's never
confused with real GPS data.

## §9 Troubleshooting

8 entries covering the most common operator errors:

### §9.1 Mock polyline not showing on the map page

**Symptom:** toggled `input_boolean.rc_map_mock_enabled` to ON,
clicked Generate, but the polyline doesn't appear on the map page.

**Cause:** the map page is reading from the real Traccar source
because `connections/traccar/` is enabled and the Traccar polyline
is being drawn on top of the mock.

**Fix:** the map page renders one polyline at a time. If you want to
see the mock, either disable Traccar (`connections/traccar/`) OR
temporarily rename `sensor.rc_trip_recent_polyline` to something
else so the map page falls back to the mock.

### §9.2 Preset change doesn't regenerate the polyline

**Symptom:** changed `input_select.rc_map_mock_preset` from
`uk_roadtrip` to `alps_loop`, but the polyline still shows the UK.

**Cause:** changing the preset only updates the `input_select` value;
the polyline is only regenerated when `script.rc_mock_track_generate`
fires (which reads the current preset / points-per-leg / jitter at
run-time).

**Fix:** click `button.rc_map_mock_generate_now` to manually
regenerate after any preset / points-per-leg / jitter change. OR
add a new automation that triggers `script.rc_mock_track_generate`
on `input_select.rc_map_mock_preset` changes.

### §9.3 Custom polyline rejected by generate.py

**Symptom:** clicked Generate with `input_select.rc_map_mock_preset = custom`,
but the HA Core log shows "GeoJSON schema invalid: ...".

**Cause:** the custom polyline at
`/config/www/roamcore/mock/custom_track.geojson` is malformed
(wrong geometry type, wrong coordinates order, missing `geometry`
key, etc.).

**Fix:** validate the GeoJSON at <https://geojsonlint.com/> or
<https://geojson.io/> before saving. The most common mistake is
using `[lat, lon]` order instead of `[lon, lat]` (GeoJSON convention
is `[lon, lat]`).

### §9.4 `shapely` import error in the Python generator

**Symptom:** clicking Generate fails with `ModuleNotFoundError: No
module named 'shapely'`.

**Cause:** an older version of `generate.py` required `shapely` for
great-circle distance computation. The current version is stdlib
only (`math.atan2` + `math.sin` + `math.cos` for haversine).

**Fix:** confirm you're running the current version of
`homeassistant/tools/mock_track/generate.py`. If you've vendored an
older version, replace it with the current version.

### §9.5 Polyline too dense (too many points)

**Symptom:** the polyline renders correctly but the map page is slow
because there are 500+ points.

**Cause:** `input_number.rc_map_mock_points_per_leg` is set to the
maximum (500) and the preset has 9 waypoints, giving 9 × 500 = 4,500
points.

**Fix:** reduce `input_number.rc_map_mock_points_per_leg` to 40–80
for most presets (the default is 80). The recipe §2 recommends 10–500;
for the map page's render performance, stay below 100.

### §9.6 Polyline too jittery (looks like noise)

**Symptom:** the polyline renders correctly but the points look
scattered / noisy.

**Cause:** `input_number.rc_map_mock_jitter_m` is set too high (50+
meters) for the map page's render scale.

**Fix:** reduce `input_number.rc_map_mock_jitter_m` to 5–15 meters
(the default is 10). Higher jitter is useful for simulating GPS
inaccuracy but makes the polyline look noisy at zoom levels < 10.

### §9.7 Mock toggle ignored by the map page

**Symptom:** toggled `input_boolean.rc_map_mock_enabled` to ON, but
the map page still renders the real Traccar polyline (or nothing).

**Cause:** the map page is reading a cached state of the input_boolean.
HA Core's `input_boolean` state changes are propagated to all
templates within 1 second, but some browsers cache the Lovelace tile
state longer.

**Fix:** reload the browser tab (Ctrl+Shift+R / Cmd+Shift+R) to
clear the Lovelace cache.

### §9.8 Polyline not on actual location

**Symptom:** the mock polyline renders in the wrong place (e.g. UK
preset renders in Australia).

**Cause:** the GeoJSON `coordinates` array uses `[lat, lon]` order
instead of `[lon, lat]` (GeoJSON convention is `[lon, lat]`).

**Fix:** swap the order of the coordinate pairs in the GeoJSON file.
The generator validates this on load and rejects with a clear error
if it detects `[lat, lon]` order (see §9.3).

## §10 Privacy

The mock polyline generator is fully local:

- **No telemetry** — the Python generator does not phone home, does
  not check for updates, does not send usage analytics.
- **No cloud call home** — the only network call the generator makes
  is reading / writing local files (`/config/tools/mock_track/generate.py`
  for the script, `/config/www/roamcore/mock/track.geojson` for the
  output).
- **Deterministic OR operator-entered** — the built-in presets are
  hardcoded waypoints; the custom preset is operator-authored GeoJSON.
  In neither case is there a cloud-source-of-truth that RoamCore is
  fetching.
- **No PII** — the synthetic polylines are not associated with any
  real person's location history. The `generatedAt` timestamp in
  the GeoJSON `properties` is the only metadata, and it stays
  local.
- **Runs entirely on the HAOS host** — the generator runs as a
  `shell_command` in HA Core, which executes on the HAOS host. No
  external process is spawned.

## §11 Promoting to a real GPS source

When the operator is done with dev/demo work, they can promote the
map page to a real GPS source by:

1. Enable `connections/traccar/` (Wave 3 #48) — the RoamCore Traccar
   connection that ships the proxy + init add-ons + the HA Core
   `device_tracker` integration.
2. Toggle `input_boolean.rc_map_mock_enabled` to OFF.
3. The map page automatically falls back to the real Traccar track
   (`sensor.rc_trip_recent_polyline` or the Traccar `device_tracker`
   entity).
4. The mock remains available for dev/demo — toggle
   `input_boolean.rc_map_mock_enabled` back to ON any time you want
   the synthetic polyline.

The mock is the **fallback / dev / demo path** — the real Traccar
source is the primary path. Both coexist; the
`input_boolean.rc_map_mock_enabled` toggle selects which one the map
page renders.