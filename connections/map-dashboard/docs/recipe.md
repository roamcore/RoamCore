# Map dashboard recipe — vendor-neutral map tile + device_tracker aggregation + trip overlay + offline-tile cache

This recipe walks the operator through installing + configuring the **Map dashboard** connection — the map-category umbrella for "RoamCore provides a map experience inside Home Assistant, including current location and route/trip context. Quick 'where are we / where did we park?' view. Nice context for trips and daily travel. Extra hardware required: None if you already have a `device_tracker` or location source. Install / best next step: Core packages: homeassistant/packages/roamcore_map.yaml + homeassistant/packages/roamcore_map_route.yaml + homeassistant/packages/roamcore_location.yaml".

The slice wraps three existing RoamCore-owned packages:

- `homeassistant/packages/roamcore_map.yaml` (31 LOC — declares the `input_text.rc_map_tile_url` + `rc_map_tile_url_online` + `rc_map_style_url` + `input_number.rc_map_offline_max_zoom` helpers). **Preserved verbatim** by this slice.
- `homeassistant/packages/roamcore_map_route.yaml` (10 LOC — declares the `input_number.rc_map_route_device_id` helper). **Preserved verbatim** by this slice.
- `homeassistant/packages/roamcore_location.yaml` (123 LOC — declares the `input_text.rc_location_tracker_entity` helper + the 11 `template:` sensors that map a configurable `device_tracker.*` → `rc_location_lat` + `rc_location_lon` + `rc_location_accuracy_m` + `rc_location_source` + `rc_location_speed` + `rc_location_heading_deg` + the 6 trip-summary `rc_trip_*` template sensors). **Preserved verbatim** by this slice.

The legacy catalog page's "Support tier: A (RoamCore native)" is correct: RoamCore DOES own + ship + maintain those packages. This slice ADDS the recipe layer (manifest + recipe + smoke + cross-references + legacy SUPERSEDED banner) WITHOUT modifying the existing package contents.

This is a **tier-a recipe connection**. There is no native RoamCore-owned map-dashboard engine; the recipe is the contract layer. The FIVE §9 MANDATORY automations below are documented in this recipe and are the operator's responsibility to wire — they are the only safety + UX contracts this connection publishes.

**Time to read:** ~12 min.
**Time to install:** ~10 min.

---

## §1 What is Map dashboard in RoamCore?

**Map dashboard** is the RoamCore dashboard's map view. The dashboard's map card shows:

1. **Current location** — a marker on the map at the operator's current GPS coordinates, with accuracy radius + speed + bearing + tile-server reachability chips.
2. **Trip overlay** — an optional polyline overlay on the map showing today's trip (or the last 7 days of trips, or all-time trips, depending on the operator's choice).
3. **Basemap mode** — the underlying map tile surface (Off / Online / Cached / Offline). The Online mode fetches tiles from the operator's configured upstream tile server. The Cached mode prefers tiles from the operator's local tile archive (when populated). The Offline mode falls back to a placeholder when neither Online nor Cached is available.

**Who is it for:** every RoamCore operator who wants a "where are we right now?" view on the dashboard, and operators who want to overlay today's trip (or recent trips) on the map without depending on a third-party map service.

**What you need to start:**

- A working RoamCore install on a Home Assistant OS box (HAOS 2022.6 or later).
- A `device_tracker.*` entity (typically `device_tracker.traccar_van` if you're running Traccar, or a phone-derived device_tracker if you're using the HA Companion app).
- A choice of upstream tile server (the default in `homeassistant/packages/roamcore_map.yaml` is `https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png` — a vendor-neutral default; the operator can change to their chosen upstream tile server via `input_text.rc_map_tile_url`).
- Optional: a populated tile archive (for the Cached mode; RoamCore ships a default-empty archive path; the operator populates it via `input_text.rc_map_style_url` or a separate tile-fetch helper).
- Optional: trip data (for the Active / Recent-7d / All-Time trip overlays; the trip data comes from the operator's trip-wrapped + trip-local databases).

**What you DON'T need:**

- A native RoamCore map-dashboard integration (we don't ship one; the three RoamCore-owned packages + the HA core `map:` card + the HA core `template:` sensor wrappers handle 95%+ of operator-facing map-dashboard operations).
- A custom_components folder addition (this slice does NOT add a custom_component — the three packages are loaded via the standard HA `packages:` mechanism).
- A HACS installation (this slice does NOT depend on a HACS add-on as a required dependency).

**Honesty footnote:** the `install.config_flow: true` flag in the manifest refers to the UPSTREAM HA core `map:` card + `device_tracker` + `template:` + `input_text` + `input_number` + `input_select` + `select:` + `automation:` integrations, ALL of which expose a GUI flow since 2022.x. That's honest upstream truth, NOT a tier-a marker for RoamCore's tier. The tier-a marker for RoamCore is the three RoamCore-owned packages + the recipe layer + the contract layer + the FIVE §9 MANDATORY automations + the legacy SUPERSEDED banner + the docs cross-references.

---

## §2 Prerequisites

Before installing the Map dashboard connection, confirm the following:

### §2.1 Home Assistant

- HAOS 2022.6 or later (the `template:` sensor + binary_sensor + `select:` domain + `automation:` integrations all require 2022.6+).
- The `packages:` mechanism enabled in `configuration.yaml`:
  ```yaml
  homeassistant:
    packages:
      packs:
        - homeassistant/packages/roamcore_map.yaml
        - homeassistant/packages/roamcore_map_route.yaml
        - homeassistant/packages/roamcore_location.yaml
  ```
  (the three packages are already shipped + RoamCore-owned + preserved verbatim by this slice).

### §2.2 Upstream GPS source

You need at least one `device_tracker.*` entity. The most common sources:

- **Traccar** (operator of an RV / van with a Traccar server) → typically `device_tracker.traccar_van`.
- **HA Companion app** (operator with the HA Companion app installed on their phone) → typically a phone-derived `device_tracker.*` entity.
- **GPS hat / USB GPS** (operator with a hardware GPS receiver) → typically a `device_tracker.*` entity exposed via the upstream GPS integration.

The operator configures `input_text.rc_location_tracker_entity` to point at their chosen `device_tracker.*` (e.g. `device_tracker.traccar_van`).

### §2.3 Upstream tile server

The default upstream tile URL in `homeassistant/packages/roamcore_map.yaml` is `https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png` — a vendor-neutral default that does not depend on any specific upstream vendor. The operator can change to their chosen upstream tile server via `input_text.rc_map_tile_url` (e.g. a self-hosted tile server, a paid tile-provider URL, or the upstream OSM tile servers if the operator accepts the OSM volunteer-tile terms).

### §2.4 (Optional) Tile cache

For the Cached mode, the operator populates a local tile archive. RoamCore does NOT ship a tile-fetch helper; the operator can either (a) manually populate a tile archive, (b) use a third-party tile-fetcher like `tileserver-gl` + a download script, or (c) leave the tile archive empty and use the Offline mode (which falls back to a placeholder when no cached tiles are available).

### §2.5 (Optional) Trip data

For the Active / Recent-7d / All-Time trip overlays, the operator needs trip data. The trip data comes from the operator's trip-wrapped + trip-local databases (the `sensor.rc_trip_wrapped_today_distance` + `sensor.rc_trip_wrapped_today_duration` + `sensor.rc_trip_wrapped_today_stops` + `sensor.rc_trip_local_today_distance` + `sensor.rc_trip_local_today_drive_time` + `sensor.rc_trip_local_today_stops` upstream sensors; both are upstream / vendor code, not RoamCore-owned). The slice's `select.rc_map_trip_overlay` is OFF by default — the operator toggles it on when they want the trip overlay to render.

### §2.6 (Recommended) Lovelace view

The operator adds the Lovelace `map:` card to a dashboard view (typically the dashboard's main view or a dedicated `/lovelace/roamcore/map` view). The existing dashboard already includes `/lovelace/roamcore/map` per `docs/mvp/features-build-status.md` — the operator just needs to populate the view with the `rc_map_*` contract tiles.

---

## §3 Configure the device_tracker

The first step is to configure the operator's upstream device_tracker.

### §3.1 Set `input_text.rc_location_tracker_entity`

The operator opens Settings → Helpers in the HA UI, finds the `RC Location Tracker Entity` helper, and sets its value to their chosen `device_tracker.*` entity_id.

For most operators, this is `device_tracker.traccar_van` (Traccar) or a phone-derived `device_tracker.*` entity (HA Companion app).

```yaml
# Example: homeassistant/packages/roamcore_location.yaml (preserved verbatim)
input_text:
  rc_location_tracker_entity:
    name: "RC Location Tracker Entity"
    # Example: device_tracker.traccar_van
    initial: "device_tracker.traccar_van"
```

### §3.2 Verify the contract tiles resolve

After setting the helper, the operator should verify that the upstream-entity-aggregation wrappers resolve correctly:

- `sensor.rc_map_latitude` should resolve to the operator's current latitude (e.g. `37.7749`).
- `sensor.rc_map_longitude` should resolve to the operator's current longitude (e.g. `-122.4194`).
- `sensor.rc_map_accuracy_meters` should resolve to the GPS accuracy in meters (e.g. `5`).
- `sensor.rc_map_speed_kph` should resolve to the current speed in kph (e.g. `0` when parked).
- `sensor.rc_map_bearing_degrees` should resolve to the current bearing in degrees (e.g. `0`).
- `binary_sensor.rc_map_has_fix` should resolve to TRUE if the lat/lng is present + accuracy < 1000m.
- `device_tracker.rc_map_device_tracker` should mirror the upstream tracker entity.

If any tile is `unknown` / `unavailable`, the operator should:

1. Confirm the upstream `device_tracker.*` is reporting a fix (check `dev-info` on the device_tracker in the HA UI).
2. Confirm `input_text.rc_location_tracker_entity` matches the upstream entity_id exactly (case-sensitive).
3. Reload the HA location package: Settings → Developer tools → YAML → Reload location.

---

## §4 Pick a basemap mode

The second step is to pick a basemap mode. The basemap mode determines which underlying tile surface the map card renders.

### §4.1 The four basemap modes

- **Off** — the map card renders no basemap (just the marker + the trip overlay on a blank canvas). Use this when the operator wants to save bandwidth / battery + the trip overlay alone is enough.
- **Online** — the map card fetches tiles from the operator-configured upstream tile URL (`input_text.rc_map_tile_url`). Use this when internet reachability is good.
- **Cached** — the map card prefers tiles from the operator's local tile archive. Use this when the operator has populated a tile archive + wants to avoid tile-server round-trips.
- **Offline** — the map card renders a placeholder when neither Online nor Cached is available. Use this as the fallback when internet reachability is lost.

The default basemap mode is `Online`. The operator picks their preferred mode via `select.rc_map_basemap_mode_user_pick` (an `input_select` helper that the operator creates via Settings → Helpers; the `sensor.rc_map_basemap_mode` template sensor resolves the picker to a concrete mode based on the §9.3 fallback logic).

### §4.2 The `rc_map_basemap_mode` template sensor

The `sensor.rc_map_basemap_mode` template sensor resolves the operator's `select.rc_map_basemap_mode_user_pick` to a concrete basemap mode based on the following logic:

```yaml
# Example: connections/map-dashboard/docs/recipe.md §4.2
# (the operator wires this template sensor in their HA configuration.yaml
#  after copying the §4.2 snippet below).
template:
  - sensor:
      - name: "RC Map Basemap Mode"
        unique_id: rc_map_basemap_mode
        icon: mdi:map
        state: >-
          {% set pick = states('select.rc_map_basemap_mode_user_pick') %}
          {% set internet = is_state('binary_sensor.rc_map_internet_reachable_for_tiles', 'on') %}
          {% set has_fix = is_state('binary_sensor.rc_map_has_fix', 'on') %}
          {% if pick == 'off' %}
            off
          {% elif pick == 'online' and internet %}
            online
          {% elif pick == 'cached' %}
            cached
          {% elif pick == 'offline' %}
            offline
          {% elif not internet %}
            offline
          {% else %}
            {{ pick }}
          {% endif %}
        availability: >-
          {{ states('select.rc_map_basemap_mode_user_pick') not in ['unknown','unavailable',''] }}
```

The §9.3 basemap-mode-fallback automation auto-flips `sensor.rc_map_basemap_mode` to `offline` when `binary_sensor.rc_map_internet_reachable_for_tiles` is FALSE — the operator doesn't need to flip the picker manually.

### §4.3 The `rc_map_internet_reachable_for_tiles` binary_sensor

The `binary_sensor.rc_map_internet_reachable_for_tiles` template binary_sensor reports whether the upstream tile servers are reachable. The operator wires this via the `ping` integration or a custom URL probe:

```yaml
# Example: connections/map-dashboard/docs/recipe.md §4.3
# (the operator wires this template binary_sensor in their HA configuration.yaml
#  after copying the §4.3 snippet below).
template:
  - binary_sensor:
      - name: "RC Map Internet Reachable For Tiles"
        unique_id: rc_map_internet_reachable_for_tiles
        icon: mdi:earth
        state: >-
          {% set url = states('input_text.rc_map_tile_url') %}
          {% if url in ['unknown','unavailable',''] %}
            false
          {% else %}
            {{ states('binary_sensor.rc_map_tile_server_reachable') }}
          {% endif %}
        availability: >-
          {{ states('input_text.rc_map_tile_url') not in ['unknown','unavailable',''] }}
```

The `binary_sensor.rc_map_tile_server_reachable` upstream binary_sensor can be wired via the `binary_sensor.ping` integration (a manual ping to the operator's tile-server domain) or a custom URL probe.

---

## §5 Pick a trip overlay

The third step is to pick a trip overlay. The trip overlay is an optional polyline on the map showing the operator's trip data.

### §5.1 The four trip overlay modes

- **Off** — no trip overlay (the operator just sees the current location marker). Use this when the operator doesn't want a polyline on the map.
- **Active** — the map card renders today's trip polyline (from `sensor.rc_trip_wrapped_today_distance` + `sensor.rc_trip_wrapped_today_duration` + `sensor.rc_trip_wrapped_today_stops` upstream sensors, falling back to `sensor.rc_trip_local_today_distance` + `sensor.rc_trip_local_today_drive_time` + `sensor.rc_trip_local_today_stops`). Use this when the operator wants to see today's trip live-updating.
- **Recent-7d** — the map card renders the last 7 days of trip polylines (from the operator's trip-wrapped + trip-local databases). Use this when the operator wants to see the past week's trip history on the map.
- **All-Time** — the map card renders all-time trip polylines (from the operator's trip-wrapped + trip-local databases). Use this when the operator wants to see all accumulated trip history on the map.

The default trip overlay is `Off`. The operator picks their preferred mode via `select.rc_map_trip_overlay`.

### §5.2 The `rc_map_trip_overlay` select

The `select.rc_map_trip_overlay` select entity is wired as follows:

```yaml
# Example: connections/map-dashboard/docs/recipe.md §5.2
# (the operator wires this select entity in their HA configuration.yaml
#  after copying the §5.2 snippet below).
select:
  - platform: input_select
    name: "RC Map Trip Overlay"
    unique_id: rc_map_trip_overlay
    icon: mdi:map-marker-path
    options:
      - "off"
      - "active"
      - "recent-7d"
      - "all-time"
    initial: "off"
```

### §5.3 The trip-overlay data sources

The trip-overlay data comes from the operator's trip-wrapped + trip-local upstream sensors:

- `sensor.rc_trip_wrapped_today_distance` + `sensor.rc_trip_wrapped_today_duration` + `sensor.rc_trip_wrapped_today_stops` — the trip-wrapped upstream sensors (today's distance / duration / stops).
- `sensor.rc_trip_local_today_distance` + `sensor.rc_trip_local_today_drive_time` + `sensor.rc_trip_local_today_stops` — the trip-local upstream sensors (today's distance / drive-time / stops; used as a fallback when trip-wrapped is unavailable).

Both are upstream / vendor code (the trip-wrapped tool lives at `homeassistant/tools/trip_wrapped/`; the trip-local tool lives at `homeassistant/tools/trip_local/`). RoamCore does NOT own either tool — the slice just exposes the `select.rc_map_trip_overlay` contract tile.

---

## §6 Verify the map renders

The fourth step is to verify the map renders correctly.

### §6.1 Open the Lovelace map view

The operator opens the Lovelace view `/lovelace/roamcore/map` (already included in `dashboard/lovelace/storage/lovelace.roamcore.json` per `docs/mvp/features-build-status.md`).

### §6.2 Confirm the current location renders

The map card should show the operator's current location marker at the resolved lat/lng coordinates. If the marker is missing or in the wrong location, the operator should:

1. Confirm `binary_sensor.rc_map_has_fix` is TRUE.
2. Confirm `sensor.rc_map_latitude` + `sensor.rc_map_longitude` resolve to the operator's expected coordinates.
3. Confirm the upstream `device_tracker.*` is reporting a fix (check `dev-info` on the device_tracker in the HA UI).

### §6.3 Confirm the trip overlay renders

If the operator has selected `Active` / `Recent-7d` / `All-Time` for `select.rc_map_trip_overlay`, the map card should render the corresponding polyline. If the polyline is missing, the operator should:

1. Confirm the trip data is populated in the operator's trip-wrapped + trip-local databases.
2. Confirm the §9.5 trip-overlay-active-only-when-vehicle-moving guard has not suppressed the polyline (the guard flips `select.rc_map_trip_overlay` to `Off` when the vehicle is parked).
3. Reload the HA trip-wrapped + trip-local packages: Settings → Developer tools → YAML → Reload trip-wrapped + Reload trip-local.

### §6.4 Confirm the basemap mode chip renders

The map card should show the resolved basemap mode (Off / Online / Cached / Offline) as a chip. If the chip is missing or stuck on Offline, the operator should:

1. Confirm `binary_sensor.rc_map_internet_reachable_for_tiles` reflects the actual upstream tile-server reachability.
2. Confirm `input_text.rc_map_tile_url` points at a reachable upstream tile URL.
3. Confirm the §9.3 basemap-mode-fallback automation has not flipped the mode to Offline unexpectedly (the automation fires when `binary_sensor.rc_map_internet_reachable_for_tiles` is FALSE).

---

## §7 Toggle between Online / Cached / Offline

The fifth step is to toggle between Online / Cached / Offline to test the §9.3 fallback automation.

### §7.1 Toggle to Online

The operator sets `select.rc_map_basemap_mode_user_pick` to `Online`. The `sensor.rc_map_basemap_mode` template sensor should resolve to `online` (assuming `binary_sensor.rc_map_internet_reachable_for_tiles` is TRUE).

### §7.2 Toggle to Cached

The operator sets `select.rc_map_basemap_mode_user_pick` to `Cached`. The `sensor.rc_map_basemap_mode` template sensor should resolve to `cached` (regardless of internet reachability — the Cached mode prefers the local tile archive).

If the local tile archive is empty, the §9.2 basemap-mode-cached-prefers-local-tile-archive guard fires a warning audit entry + a notification + flips the mode to `Offline`.

### §7.3 Toggle to Offline

The operator sets `select.rc_map_basemap_mode_user_pick` to `Offline`. The `sensor.rc_map_basemap_mode` template sensor should resolve to `offline`.

### §7.4 Toggle to Off

The operator sets `select.rc_map_basemap_mode_user_pick` to `Off`. The `sensor.rc_map_basemap_mode` template sensor should resolve to `off`. The map card renders no basemap (just the marker + the trip overlay on a blank canvas).

### §7.5 Test the §9.3 fallback

The operator disconnects the upstream tile server (by blocking the upstream URL via firewall / DNS / unplugging the upstream router). The `binary_sensor.rc_map_internet_reachable_for_tiles` should flip to FALSE, the §9.3 basemap-mode-fallback automation should fire + flip `sensor.rc_map_basemap_mode` to `offline`, and the operator should see a notification warning them that the map has fallen back to offline.

---

## §8 RoamCore contract entities

The 10 `rc_map_*` contract tiles are the vendor-neutral map-dashboard contract surface.

### §8.1 The contract tile table

| Domain | Tile id | Purpose |
|---|---|---|
| `device_tracker` | `rc_map_device_tracker` | Resolved current device_tracker — mirrors `input_text.rc_location_tracker_entity`. |
| `sensor` | `rc_map_latitude` | Current latitude — `template:` sensor derived from `device_tracker.*`'s `latitude` attribute. |
| `sensor` | `rc_map_longitude` | Current longitude — `template:` sensor derived from `device_tracker.*`'s `longitude` attribute. |
| `sensor` | `rc_map_accuracy_meters` | Current accuracy in meters — `template:` sensor derived from `device_tracker.*`'s `gps_accuracy` / `accuracy` attribute. |
| `sensor` | `rc_map_speed_kph` | Current speed in kph — `template:` sensor derived from `device_tracker.*`'s `speed` attribute. |
| `sensor` | `rc_map_bearing_degrees` | Current bearing / heading in degrees — `template:` sensor derived from `device_tracker.*`'s `course` / `heading` attribute. |
| `binary_sensor` | `rc_map_has_fix` | TRUE if lat/lng present + accuracy < 1000m — `template:` binary_sensor. |
| `binary_sensor` | `rc_map_internet_reachable_for_tiles` | TRUE if the upstream tile servers are reachable — `template:` binary_sensor. |
| `sensor` | `rc_map_basemap_mode` | Current resolved basemap mode — `template:` sensor. |
| `select` | `rc_map_trip_overlay` | Trip overlay mode — Off / Active / Recent-7d / All-Time. |

### §8.2 The template sensor configurations

The 6 `template:` sensors (`rc_map_latitude` + `rc_map_longitude` + `rc_map_accuracy_meters` + `rc_map_speed_kph` + `rc_map_bearing_degrees` + `rc_map_basemap_mode`) are wired as follows:

```yaml
# Example: connections/map-dashboard/docs/recipe.md §8.2
# (the operator wires these template sensors in their HA configuration.yaml
#  after copying the §8.2 snippet below; the existing packages at
#  homeassistant/packages/roamcore_location.yaml + roamcore_map.yaml
#  already declare the upstream template sensors that map rc_location_*;
#  this slice adds the rc_map_* wrappers on top).
template:
  - sensor:
      - name: "RC Map Latitude"
        unique_id: rc_map_latitude
        icon: mdi:latitude
        state: "{{ state_attr('device_tracker.rc_map_device_tracker', 'latitude') | float(default=none) }}"
        availability: "{{ states('binary_sensor.rc_map_has_fix') == 'on' }}"

      - name: "RC Map Longitude"
        unique_id: rc_map_longitude
        icon: mdi:longitude
        state: "{{ state_attr('device_tracker.rc_map_device_tracker', 'longitude') | float(default=none) }}"
        availability: "{{ states('binary_sensor.rc_map_has_fix') == 'on' }}"

      - name: "RC Map Accuracy"
        unique_id: rc_map_accuracy_meters
        unit_of_measurement: "m"
        icon: mdi:target
        state: "{{ state_attr('device_tracker.rc_map_device_tracker', 'gps_accuracy') | default(state_attr('device_tracker.rc_map_device_tracker', 'accuracy'), true) | float(default=none) }}"
        availability: "{{ states('binary_sensor.rc_map_has_fix') == 'on' }}"

      - name: "RC Map Speed"
        unique_id: rc_map_speed_kph
        unit_of_measurement: "kph"
        icon: mdi:speedometer
        state: "{{ (state_attr('device_tracker.rc_map_device_tracker', 'speed') | float(default=none)) * 3.6 | round(2, default=none) }}"
        availability: "{{ states('device_tracker.rc_map_device_tracker') not in ['unknown','unavailable',''] }}"

      - name: "RC Map Bearing"
        unique_id: rc_map_bearing_degrees
        unit_of_measurement: "°"
        icon: mdi:compass
        state: "{{ state_attr('device_tracker.rc_map_device_tracker', 'course') | default(state_attr('device_tracker.rc_map_device_tracker', 'heading'), true) | float(default=none) }}"
        availability: "{{ states('device_tracker.rc_map_device_tracker') not in ['unknown','unavailable',''] }}"
```

### §8.3 The template binary_sensor configurations

The 2 `template:` binary_sensors (`rc_map_has_fix` + `rc_map_internet_reachable_for_tiles`) are wired as follows:

```yaml
# Example: connections/map-dashboard/docs/recipe.md §8.3
# (the operator wires these template binary_sensors in their HA configuration.yaml
#  after copying the §8.3 snippet below).
template:
  - binary_sensor:
      - name: "RC Map Has Fix"
        unique_id: rc_map_has_fix
        icon: mdi:crosshairs-gps
        state: >-
          {% set lat = state_attr('device_tracker.rc_map_device_tracker', 'latitude') %}
          {% set lon = state_attr('device_tracker.rc_map_device_tracker', 'longitude') %}
          {% set acc = state_attr('device_tracker.rc_map_device_tracker', 'gps_accuracy') | default(state_attr('device_tracker.rc_map_device_tracker', 'accuracy'), true) | float(9999) %}
          {{ lat is not none and lon is not none and acc < 1000 }}
        availability: "{{ states('device_tracker.rc_map_device_tracker') not in ['unknown','unavailable',''] }}"
```

The `binary_sensor.rc_map_internet_reachable_for_tiles` is wired via the §4.3 snippet above.

### §8.4 The select entity configuration

The `select.rc_map_trip_overlay` select entity is wired via the §5.2 snippet above.

---

## §9 Automations (MANDATORY before first use)

The FIVE §9 MANDATORY automations are the safety + UX contracts this connection publishes. The operator MUST wire all FIVE before first use.

### §9.1 Basemap-mode-online-requires-internet-reachability guard

The §9.1 automation fires when `binary_sensor.rc_map_internet_reachable_for_tiles` is FALSE AND `sensor.rc_map_basemap_mode` resolves to `online`. The automation logs a critical audit entry + fires a notification warning the operator that the basemap mode requires internet reachability for the upstream tile servers + flips `sensor.rc_map_basemap_mode` to `offline` (the §9.3 basemap-mode-fallback automation).

```yaml
# Example: connections/map-dashboard/docs/recipe.md §9.1
# (the operator wires this automation in their HA automations.yaml
#  after copying the §9.1 snippet below).
automation:
  - id: rc_map_basemap_mode_online_requires_internet_reachability_guard
    alias: "RC Map: basemap-mode-online requires internet reachability"
    description: >-
      Fires when the operator's chosen basemap mode is Online
      BUT the upstream tile servers are not reachable. Flips
      sensor.rc_map_basemap_mode to Offline + logs a critical
      audit entry + fires a notification warning the operator.
    mode: single
    trigger:
      - platform: state
        entity_id: binary_sensor.rc_map_internet_reachable_for_tiles
        to: "off"
    condition:
      - condition: state
        entity_id: sensor.rc_map_basemap_mode
        state: "online"
    action:
      - service: logbook.log
        data:
          name: "RC Map"
          message: "Basemap mode is Online but upstream tile servers are unreachable — falling back to Offline"
          entity_id: sensor.rc_map_basemap_mode
          domain: map
      - service: persistent_notification.create
        data:
          title: "RC Map: tile servers unreachable"
          message: >-
            The basemap mode is Online but the upstream tile servers are
            unreachable. Falling back to Offline. Check your internet
            connection + the input_text.rc_map_tile_url configuration.
          notification_id: rc_map_basemap_mode_online_unreachable
      - service: select.select_option
        target:
          entity_id: select.rc_map_basemap_mode_user_pick
        data:
          option: "offline"
```

### §9.2 Basemap-mode-cached-prefers-local-tile-archive guard

The §9.2 automation fires when `sensor.rc_map_basemap_mode` resolves to `cached` AND the operator-configured tile archive path is empty. The automation logs a warning audit entry + fires a notification warning the operator that the cached mode requires a populated tile archive + flips `sensor.rc_map_basemap_mode` to `offline` (the §9.3 basemap-mode-fallback automation).

```yaml
# Example: connections/map-dashboard/docs/recipe.md §9.2
# (the operator wires this automation in their HA automations.yaml
#  after copying the §9.2 snippet below).
automation:
  - id: rc_map_basemap_mode_cached_prefers_local_tile_archive_guard
    alias: "RC Map: basemap-mode-cached prefers local tile archive"
    description: >-
      Fires when the operator's chosen basemap mode is Cached
      BUT the local tile archive is empty. Flips
      sensor.rc_map_basemap_mode to Offline + logs a warning
      audit entry + fires a notification warning the operator.
    mode: single
    trigger:
      - platform: state
        entity_id: sensor.rc_map_basemap_mode
        to: "cached"
    condition:
      - condition: template
        value_template: "{{ states('input_text.rc_map_tile_archive_path') in ['unknown','unavailable',''] }}"
    action:
      - service: logbook.log
        data:
          name: "RC Map"
          message: "Basemap mode is Cached but the local tile archive is empty — falling back to Offline"
          entity_id: sensor.rc_map_basemap_mode
          domain: map
      - service: persistent_notification.create
        data:
          title: "RC Map: tile archive empty"
          message: >-
            The basemap mode is Cached but the local tile archive
            (configured via input_text.rc_map_tile_archive_path)
            is empty. Falling back to Offline. Populate the tile
            archive via tileserver-gl + a download script, or
            leave it empty and use the Offline mode.
          notification_id: rc_map_basemap_mode_cached_empty
      - service: select.select_option
        target:
          entity_id: select.rc_map_basemap_mode_user_pick
        data:
          option: "offline"
```

### §9.3 Basemap-mode-fallback to offline when tile servers unreachable

The §9.3 automation fires when `binary_sensor.rc_map_internet_reachable_for_tiles` is FALSE. The automation flips `sensor.rc_map_basemap_mode` to `offline` + fires a notification warning the operator that the map has fallen back to offline.

```yaml
# Example: connections/map-dashboard/docs/recipe.md §9.3
# (the operator wires this automation in their HA automations.yaml
#  after copying the §9.3 snippet below).
automation:
  - id: rc_map_basemap_mode_fallback_to_offline
    alias: "RC Map: basemap-mode-fallback to offline when tile servers unreachable"
    description: >-
      Fires when the upstream tile servers are not reachable.
      Flips sensor.rc_map_basemap_mode to Offline + fires a
      notification warning the operator that the map has
      fallen back to offline.
    mode: single
    trigger:
      - platform: state
        entity_id: binary_sensor.rc_map_internet_reachable_for_tiles
        to: "off"
        for: "00:00:30"
    action:
      - service: logbook.log
        data:
          name: "RC Map"
          message: "Tile servers unreachable — basemap mode falling back to Offline"
          entity_id: sensor.rc_map_basemap_mode
          domain: map
      - service: persistent_notification.create
        data:
          title: "RC Map: tile servers unreachable"
          message: >-
            The upstream tile servers are not reachable. The basemap
            mode has fallen back to Offline. Check your internet
            connection + the input_text.rc_map_tile_url configuration.
          notification_id: rc_map_tile_servers_unreachable
      - service: select.select_option
        target:
          entity_id: select.rc_map_basemap_mode_user_pick
        data:
          option: "offline"
```

### §9.4 Has-fix-blocks-tile-flicker guard

The §9.4 automation fires when `binary_sensor.rc_map_has_fix` toggles FALSE→TRUE or TRUE→FALSE. The automation debounces the tile-recenter signal + logs an audit entry + keeps the map from flickering between stale + fresh fixes.

```yaml
# Example: connections/map-dashboard/docs/recipe.md §9.4
# (the operator wires this automation in their HA automations.yaml
#  after copying the §9.4 snippet below).
automation:
  - id: rc_map_has_fix_blocks_tile_flicker_guard
    alias: "RC Map: has-fix-blocks-tile-flicker guard"
    description: >-
      Fires when binary_sensor.rc_map_has_fix toggles
      FALSE→TRUE or TRUE→FALSE. Debounces the tile-recenter
      signal + logs an audit entry + keeps the map from
      flickering between stale + fresh fixes.
    mode: single
    trigger:
      - platform: state
        entity_id: binary_sensor.rc_map_has_fix
    condition:
      - condition: template
        value_template: "{{ trigger.from_state.state != trigger.to_state.state }}"
    action:
      - delay: "00:00:05"
      - service: logbook.log
        data:
          name: "RC Map"
          message: "GPS fix state changed: {{ trigger.from_state.state }} → {{ trigger.to_state.state }}"
          entity_id: binary_sensor.rc_map_has_fix
          domain: map
```

### §9.5 Trip-overlay-active-only-when-vehicle-moving guard

The §9.5 automation fires when `sensor.rc_map_speed_kph` is below 1 kph (vehicle is parked) AND `select.rc_map_trip_overlay` is set to `active`. The automation flips `select.rc_map_trip_overlay` to `off` + logs an audit entry + fires a notification warning the operator that the trip overlay is suppressed because the vehicle is parked.

```yaml
# Example: connections/map-dashboard/docs/recipe.md §9.5
# (the operator wires this automation in their HA automations.yaml
#  after copying the §9.5 snippet below).
automation:
  - id: rc_map_trip_overlay_active_only_when_vehicle_moving_guard
    alias: "RC Map: trip-overlay-active-only-when-vehicle-moving guard"
    description: >-
      Fires when the vehicle is parked (sensor.rc_map_speed_kph
      below 1 kph) AND select.rc_map_trip_overlay is set to
      active. Flips select.rc_map_trip_overlay to off + logs
      an audit entry + fires a notification warning the
      operator that the trip overlay is suppressed because
      the vehicle is parked.
    mode: single
    trigger:
      - platform: numeric_state
        entity_id: sensor.rc_map_speed_kph
        below: 1
        for: "00:01:00"
    condition:
      - condition: state
        entity_id: select.rc_map_trip_overlay
        state: "active"
    action:
      - service: logbook.log
        data:
          name: "RC Map"
          message: "Trip overlay suppressed because vehicle is parked"
          entity_id: select.rc_map_trip_overlay
          domain: map
      - service: persistent_notification.create
        data:
          title: "RC Map: trip overlay suppressed"
          message: >-
            The trip overlay is suppressed because the vehicle
            is parked (sensor.rc_map_speed_kph below 1 kph).
            Trip overlay flipped to Off. Set select.rc_map_trip_overlay
            to Active when you start driving again.
          notification_id: rc_map_trip_overlay_vehicle_parked
      - service: select.select_option
        target:
          entity_id: select.rc_map_trip_overlay
        data:
          option: "off"
```

---

## §10 Troubleshooting

The FIVE §10 troubleshooting entries cover the most common operator-facing issues.

### §10.1 Tile server 403

**Symptom:** the map card renders a 403 / blank-tile error.

**Cause:** the operator-configured `input_text.rc_map_tile_url` points at a tile server that returns 403 (e.g. tile.openstreetmap.org's referer-block on the upstream URL).

**Fix:**

1. Confirm the operator-configured `input_text.rc_map_tile_url` is a vendor-neutral upstream (not the OSM volunteer tile server — the existing default in `homeassistant/packages/roamcore_map.yaml` is `https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png` to avoid this issue).
2. Confirm the operator-configured `input_text.rc_map_tile_url_online` (the online-fallback) is populated + reachable.
3. Toggle `select.rc_map_basemap_mode_user_pick` to `Offline` as a temporary workaround.

### §10.2 No GPS fix

**Symptom:** the map card does not render the current location marker (or renders it at 0,0).

**Cause:** the upstream `device_tracker.*` is not reporting a fix.

**Fix:**

1. Confirm the upstream `device_tracker.*` is reporting a fix (check `dev-info` on the device_tracker in the HA UI).
2. Confirm `input_text.rc_location_tracker_entity` matches the upstream entity_id exactly (case-sensitive).
3. Confirm `binary_sensor.rc_map_has_fix` is TRUE.
4. Reload the HA location package: Settings → Developer tools → YAML → Reload location.

### §10.3 Stale cached tiles

**Symptom:** the map card renders cached tiles that are out-of-date.

**Cause:** the operator's local tile archive has not been refreshed.

**Fix:**

1. Refresh the local tile archive via tileserver-gl + a download script (RoamCore does NOT ship a tile-fetcher — the operator uses a third-party tool).
2. Toggle `select.rc_map_basemap_mode_user_pick` to `Online` (the Online mode fetches fresh tiles from the upstream tile server).
3. Toggle `select.rc_map_basemap_mode_user_pick` to `Offline` (the Offline mode renders a placeholder).

### §10.4 Trip overlay shows no data

**Symptom:** the trip overlay polyline is empty / missing.

**Cause:** the operator's trip-wrapped + trip-local databases have no data for the selected time range (Active / Recent-7d / All-Time).

**Fix:**

1. Confirm the trip data is populated in the operator's trip-wrapped + trip-local databases.
2. Confirm the §9.5 trip-overlay-active-only-when-vehicle-moving guard has not suppressed the polyline (the guard flips `select.rc_map_trip_overlay` to `Off` when the vehicle is parked).
3. Reload the HA trip-wrapped + trip-local packages: Settings → Developer tools → YAML → Reload trip-wrapped + Reload trip-local.

### §10.5 Basemap mode keeps falling back to Offline

**Symptom:** the operator selects `Online` or `Cached` but the mode keeps flipping to `Offline`.

**Cause:** the §9.3 basemap-mode-fallback automation is firing repeatedly.

**Fix:**

1. Confirm `binary_sensor.rc_map_internet_reachable_for_tiles` reflects the actual upstream tile-server reachability.
2. Confirm `input_text.rc_map_tile_url` points at a reachable upstream tile URL.
3. Confirm the operator-configured tile archive (for `Cached` mode) is populated.
4. Toggle `select.rc_map_basemap_mode_user_pick` to `Online` or `Cached` again after confirming the upstream tile server is reachable.

### §10.6 Map card not loading

**Symptom:** the Lovelace map card does not render at all.

**Cause:** the Lovelace `map:` card is not configured correctly + the operator's browser does not support the upstream tile-server's HTTPS certificate.

**Fix:**

1. Confirm the Lovelace `map:` card is configured to use the 10 `rc_map_*` contract tiles (not the upstream `device_tracker.*` directly).
2. Confirm the operator's browser supports the upstream tile-server's HTTPS certificate.
3. Reload the Lovelace view: Settings → Developer tools → YAML → Reload lovelace.

---

## §11 Privacy

The Map dashboard connection is privacy-respecting by design.

### §11.1 No RoamCore-side telemetry

RoamCore does NOT collect telemetry on the operator's map usage. There is no analytics ping, no usage-reporting endpoint, no RoamCore cloud round-trip. The map tiles fetch from the operator-configured upstream URL (the operator owns the choice of tile server). The cached tiles live on the operator's HA box. The trip-overlay data lives in the operator's trip-wrapped + trip-local databases.

### §11.2 The operator owns the tile URL

The operator-configured `input_text.rc_map_tile_url` + `rc_map_tile_url_online` + `rc_map_style_url` are the operator's choice. RoamCore does NOT inject a default upstream URL that leaks to a RoamCore-controlled tile server. The default in `homeassistant/packages/roamcore_map.yaml` is `https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png` — a vendor-neutral CartoDB-hosted tile server (Carto is a third-party vendor that RoamCore does NOT control). The operator can change to their chosen upstream at any time.

### §11.3 The operator owns the tile cache

The operator's local tile cache lives on the operator's HA box. The tile cache is NOT shared with RoamCore or any third party. The tile cache is part of the operator's HA filesystem + is backed up with the operator's HA backup.

### §11.4 The operator owns the device_tracker

The operator-configured `input_text.rc_location_tracker_entity` is the operator's choice. RoamCore does NOT inject a default device_tracker that leaks the operator's location to a third party. The default in `homeassistant/packages/roamcore_location.yaml` is `device_tracker.traccar_van` — the operator must configure this helper to point at their chosen upstream device_tracker.

### §11.5 The operator owns the trip-overlay choice

The operator-configured `select.rc_map_trip_overlay` is the operator's choice. RoamCore does NOT inject a default trip-overlay mode that leaks the operator's trip history. The default is `Off` — the operator must explicitly select `Active` / `Recent-7d` / `All-Time` to render the trip overlay.

### §11.6 The operator owns the audit log

The FIVE §9 MANDATORY automations write audit entries to the HA core `logbook` integration (since 2022.x — the canonical audit-log destination for Home Assistant automations). The audit log stays local on the operator's HA box. The operator owns the audit log + can clear it at any time.

---

## §12 Promoting to tier-a

The Map dashboard connection is already tier-a — the legacy catalog page's "Support tier: A (RoamCore native)" is correct because RoamCore DOES own + ship + maintain the three packages. This slice ADDS the recipe layer (manifest + recipe + smoke + cross-references + legacy SUPERSEDED banner) WITHOUT modifying the existing package contents.

For full tier-a promotion (removing the `status: beta` flag + the five `tier_warnings`), the operator + the RoamCore team would need to ship:

### §12.1 Real tile-cache engine

A RoamCore-owned tile-cache engine (a background process that fetches tiles from the operator's chosen upstream + caches them in a local tile archive + serves cached tiles to the map card when the upstream is unreachable). The tile-cache engine would live at `homeassistant/tools/tile_cache/` (analogous to `homeassistant/tools/trip_wrapped/` + `homeassistant/tools/trip_local/`).

### §12.2 Canned fixture responses for tile-server-403 events

Canned fixture responses for tile-server-403 events (the §10.1 tile server 403 troubleshooting entry). The bench would emit a synthetic tile-server-403 event + verify that the §9.3 basemap-mode-fallback automation fires + flips `sensor.rc_map_basemap_mode` to `offline`.

### §12.3 Canned fixture responses for stale-cache fallback events

Canned fixture responses for stale-cache fallback events (the §10.3 stale cached tiles troubleshooting entry). The bench would emit a synthetic stale-cache event + verify that the §9.2 basemap-mode-cached-prefers-local-tile-archive guard fires + flips `sensor.rc_map_basemap_mode` to `offline`.

### §12.4 Canned fixture responses for trip-overlay-with-no-data events

Canned fixture responses for trip-overlay-with-no-data events (the §10.4 trip overlay shows no data troubleshooting entry). The bench would emit a synthetic trip-overlay-with-no-data event + verify that the map card renders a "no trip data" placeholder.

### §12.5 Canned fixture responses for basemap-mode-fallback-to-offline events

Canned fixture responses for basemap-mode-fallback-to-offline events (the §10.5 basemap mode keeps falling back to Offline troubleshooting entry). The bench would emit a synthetic upstream-tile-server-unreachable event + verify that the §9.3 basemap-mode-fallback automation fires + flips `sensor.rc_map_basemap_mode` to `offline`.

### §12.6 RoamCore-owned operator-wired setup flow

A RoamCore-owned operator-wired setup flow (a RoamCore operator-wired wizard) that walks the operator through Device-tracker + Basemap-mode + Trip-overlay + Cached + Offline + the §9 automations. The wizard would live at `connections/map-dashboard/wizard/` (analogous to the HACS-installed RoamCore integration wizard).

### §12.7 Integration tests asserting the FIVE §9 automations

Integration tests asserting that (a) a tile-server-403 event auto-falls-back to Cached + (b) a trip-overlay-with-no-data event shows a "no trip data" placeholder + (c) a basemap-mode fallback to Offline fires when the upstream tile servers are unreachable + (d) a has-fix toggle FALSE→TRUE does not cause the map to flicker + (e) a trip-overlay-active mode is auto-flipped to Off when the vehicle is parked.

---

## §13 Files

The files in this connection:

- `connection.yml` — the source-of-truth tier-a manifest.
- `__init__.py` — `DOMAIN = "map"` marker for the audit.
- `docs/recipe.md` — this file (the full howto).
- `tests/test_connection_yml.py` — manifest honesty checks.

The files referenced by this connection (preserved verbatim by this slice):

- `homeassistant/packages/roamcore_map.yaml` (31 LOC — the `input_text.rc_map_tile_url` + `rc_map_tile_url_online` + `rc_map_style_url` + `input_number.rc_map_offline_max_zoom` helpers). **Preserved verbatim** by this slice.
- `homeassistant/packages/roamcore_map_route.yaml` (10 LOC — the `input_number.rc_map_route_device_id` helper). **Preserved verbatim** by this slice.
- `homeassistant/packages/roamcore_location.yaml` (123 LOC — the `input_text.rc_location_tracker_entity` + the 11 `template:` sensors that map a configurable `device_tracker.*` → `rc_location_lat` + `rc_location_lon` + `rc_location_accuracy_m` + `rc_location_source` + `rc_location_speed` + `rc_location_heading_deg` + the 6 trip-summary `rc_trip_*` template sensors). **Preserved verbatim** by this slice.

The files modified by this connection:

- the legacy spec (legacy catalog page — appended SUPERSEDED banner; legacy tier-a claim preserved as aspirational with a footnote pointing at the new connection).
- `docs/reference/rc-entity-naming.md` (added `map` subsystem to the `Allowed subsystems` list; back-fills `ventilation` + `vehicle` + `mode` + `demo_mode` + `advanced_mode` + `openclaw_api` + `agent_actions` since all seven were missing from the list on the fresh-from-main branch cut).
- `docs/mvp/features-build-status.md` (added "Map dashboard" Shipped (repo) row with full tier-a manifest + recipe + smoke + contract tiles + vendor-neutrality + legacy supersession banner + cross-references + PR #70; Last updated: 2026-03-31 → 2026-08-03).

The new file created by this connection:

- `scripts/check.sh` (full chain + the map-dashboard smoke wired in immediately after the agent-actions-allowlist entry; created from scratch on this branch since `origin/main` doesn't have check.sh — mirrors the timezone-geolocator / time-atomic / in-cab-tablet-dashboard / nfc-tags / remote-access / fans / leveling / mode / demo-mode / advanced-mode / openclaw-api / agent-actions-allowlist pattern of fresh-from-main slices recreating the chain).

---

## §14 Cross-references

The Map dashboard connection cross-references:

- **Time-atomic (Wave 3 #55)** — the time-of-day primitives used by the §9.5 trip-overlay-active-only-when-vehicle-moving guard's "vehicle just started moving" edge detection. See `connections/time-atomic/` (PR #58).
- **Remote-access (Wave 3 #58)** — the VPN primitive used by the §9.1 basemap-mode-online-requires-internet-reachability guard's internet-reachability check. See `connections/remote-access/` (PR #62).
- **Mode (Wave 3 #61)** — the §9.5 trip-overlay-active-only-when-vehicle-moving guard's mode-change cross-reference (the guard surfaces trip-overlay transitions on the mode-change notification timeline). See `connections/mode/` (PR #65).
- **Demo-mode (Wave 3 #62)** — the §9.1 basemap-mode-online-requires-internet-reachability guard's safety-chip pattern (mirrors the demo-mode §8.2 never-controls-actual-hardware guard's safety-chip pattern). See `connections/demo-mode/` (PR #66).
- **Advanced-mode (Wave 3 #63)** — the §9.4 has-fix-blocks-tile-flicker guard's confirm-flag pattern (mirrors the advanced-mode §8.1 confirm-before-toggle-on guard's confirm-flag pattern). See `connections/advanced-mode/` (PR #67).
- **OpenClaw JSON API (Wave 3 #64)** — the §9.1 basemap-mode-online-requires-internet-reachability guard's JSON payload cross-reference (the openclaw-api contract version surfaces map events via the JSON API). See `connections/openclaw-api/` (PR #68).
- **Leveling (Wave 3 #60)** — the §9.5 trip-overlay-active-only-when-vehicle-moving guard's leveling-jack cross-reference (the guard prevents trip overlay rendering while the vehicle is being leveled). See `connections/leveling/` (PR #64).
- **Fans (Wave 3 #59)** — the §9.1 basemap-mode-online-requires-internet-reachability guard's fan-protection cross-reference (the guard protects real fans from being toggled by map-dashboard events). See `connections/fans/` (PR #63).
- **Approach lights (Wave 3 #52)** — the dashboard banner pattern used by the §9.3 basemap-mode-fallback to offline automation. See `connections/approach-lights/` (PR #55).
- **Agent actions allowlist (Wave 3 #65)** — the §9.3 basemap-mode-fallback to offline automation's kill-switch integration (the kill switch disables agent-driven basemap-mode changes when the operator has the agent kill switch OFF). See `connections/agent-actions-allowlist/` (PR #69).

The Map dashboard connection is referenced by:

- The legacy catalog page [the legacy spec](../../the legacy spec) (28 lines — the legacy tier-a claim stub, originally listed "RoamCore provides a map experience inside Home Assistant, including current location and route/trip context. Quick 'where are we / where did we park?' view. Nice context for trips and daily travel. Extra hardware required: None if you already have a `device_tracker` or location source. Install / best next step: Core packages: homeassistant/packages/roamcore_map.yaml + homeassistant/packages/roamcore_map_route.yaml + homeassistant/packages/roamcore_location.yaml. If using Traccar, see the Traccar pages in this catalog." with no recipe + no contract layer + no basemap-mode picker + no trip-overlay picker + no automated basemap-mode fallback + no offline-tile-cache integration — just a placeholder with an aspirational tier-a claim that pointed at the three existing RoamCore-owned packages without documenting how they compose; now superseded by this slice).
- The features build status doc [`docs/mvp/features-build-status.md`](../../docs/mvp/features-build-status.md) (the "Map dashboard" Shipped (repo) row added by this slice).
- The RoamCore entity naming convention doc [`docs/reference/rc-entity-naming.md`](../../docs/reference/rc-entity-naming.md) (the `map` subsystem added by this slice).
