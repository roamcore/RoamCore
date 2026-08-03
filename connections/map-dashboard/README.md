# Map dashboard — vendor-neutral map tile + device_tracker aggregation + trip overlay + offline-tile cache

**Tier:** A (recipe)
**Category:** map
**Status:** beta

## What this connection is

Map dashboard — vendor-neutral map tile + device_tracker aggregation + trip overlay + offline-tile cache — the umbrella for "RoamCore provides a map experience inside Home Assistant, including current location and route/trip context. Quick 'where are we / where did we park?' view. Nice context for trips and daily travel. Extra hardware required: None if you already have a `device_tracker` or location source. Install / best next step: Core packages: homeassistant/packages/roamcore_map.yaml + homeassistant/packages/roamcore_map_route.yaml + homeassistant/packages/roamcore_location.yaml" — is the map-category umbrella for the RoamCore dashboard's map view. The three RoamCore-owned packages at `homeassistant/packages/roamcore_map.yaml` (31 LOC — the `input_text.rc_map_tile_url` + `rc_map_tile_url_online` + `rc_map_style_url` + `input_number.rc_map_offline_max_zoom` helpers) + `homeassistant/packages/roamcore_map_route.yaml` (10 LOC — the `input_number.rc_map_route_device_id` helper) + `homeassistant/packages/roamcore_location.yaml` (123 LOC — the `input_text.rc_location_tracker_entity` + the 11 `template:` sensors that map a configurable `device_tracker.*` → `rc_location_lat` + `rc_location_lon` + `rc_location_accuracy_m` + `rc_location_source` + `rc_location_speed` + `rc_location_heading_deg` + the 6 trip-summary `rc_trip_*` template sensors) are the RoamCore-owned packages this slice WRAPS (referenced verbatim via `install.packages:` in the manifest — the package contents are NOT redefined by this slice). The slice publishes the 10 `rc_map_*` contract tiles documented below (vendor-neutral — no OSM / Mapbox / HERE / TomTom / Google / Apple Maps names leak into the tile ids; the upstream tile URL stays the operator's choice via the existing `input_text.rc_map_tile_url` helper) + the FIVE-step operator-pickable map flow + the FIVE §9 MANDATORY automations + the legacy SUPERSEDED banner on the catalog page + the docs cross-references.

RoamCore ships **no** custom map-dashboard integration. The three RoamCore-owned packages are the existing umbrella (already shipped + already RoamCore-owned + already loaded via the standard HA `packages:` mechanism). The HA core `map:` card (since 2022.x — exposes the Lovelace map card surface) is the actual map surface. The HA core `device_tracker` integration (since 2022.x — exposes the canonical `device_tracker.*` umbrella for GPS sources) is the upstream GPS source. The HA core `template:` sensor + binary_sensor wrappers (since 2022.x — expose a GUI flow for the operator to add a derived `sensor.*` / `binary_sensor.*` entity from upstream sensors) are the upstream-entity-aggregation layer for the `rc_map_*` contract tiles. The HA core `automation:` integration (since 2022.x — exposes the canonical automation runner) is the umbrella for the FIVE §9 MANDATORY automations. The 10 `rc_map_*` contract tiles are the vendor-neutral layer the dashboard + OpenClaw queries use.

## The 5-step operator flow

- **Step 1 — Configure the device_tracker** — the operator sets `input_text.rc_location_tracker_entity` to their chosen `device_tracker.*` (typically `device_tracker.traccar_van` if Traccar is the upstream source, or a phone-derived device_tracker if the HA Companion app is the upstream source). The §9.4 has-fix-blocks-tile-flicker guard ensures the map does not flicker between stale + fresh fixes.

- **Step 2 — Pick a basemap mode** — the operator picks the basemap mode via `select.rc_map_basemap_mode_user_pick` (Off / Online / Cached / Offline; default Online). The §9.3 basemap-mode-fallback automation auto-falls-back to Offline when the upstream tile servers are unreachable.

- **Step 3 — Pick a trip overlay** — the operator picks the trip overlay via `select.rc_map_trip_overlay` (Off / Active / Recent-7d / All-Time; default Off). The §9.5 trip-overlay-active-only-when-vehicle-moving guard keeps the trip overlay from rendering when the vehicle is parked.

- **Step 4 — Verify the map renders** — the operator opens the Lovelace map card + confirms the current location + the trip overlay + the basemap-mode chip render. The §9.4 has-fix-blocks-tile-flicker guard debounces the tile-recenter signal so the map doesn't flicker between stale + fresh fixes.

- **Step 5 — Toggle between Online / Cached / Offline** — the operator toggles the basemap mode to test the §9.3 fallback automation. The §9.1 basemap-mode-online-requires-internet-reachability guard + §9.2 basemap-mode-cached-prefers-local-tile-archive guard surface warning audit entries + notifications when the chosen basemap mode requires infrastructure that isn't available.

## Setup recipe (one-paragraph)

1. Confirm the three RoamCore-owned packages are loaded via the standard HA `packages:` mechanism (the packages at `homeassistant/packages/roamcore_map.yaml` + `homeassistant/packages/roamcore_map_route.yaml` + `homeassistant/packages/roamcore_location.yaml` are already shipped + RoamCore-owned + preserved verbatim by this slice — the package contents are NOT redefined).
2. Confirm the HA core `map:` card + `device_tracker` + `template:` + `input_text` + `input_number` + `input_select` + `select:` + `automation:` integrations are installed (auto-installed in every HA install + exposed via the HA UI under Settings → Devices & services).
3. Set up the upstream entity pointers:
   - **`input_text.rc_location_tracker_entity`** — operator-configurable upstream tracker entity_id (default `device_tracker.traccar_van`).
   - **`input_text.rc_map_tile_url`** — operator-configurable upstream tile URL (default `https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png` — the existing default in the package; the operator can change to their chosen upstream tile server).
   - **`input_text.rc_map_tile_url_online`** — operator-configurable online-fallback tile URL (default empty — operator populates with their chosen fallback tile server).
   - **`input_text.rc_map_style_url`** — operator-configurable MapLibre style URL (default `/local/roamcore/styles/rc-online-carto-light.json` — the existing default in the package).
   - **`input_number.rc_map_offline_max_zoom`** — offline-tile-archive max zoom (default 19).
   - **`input_number.rc_map_route_device_id`** — route-device id (default 3).
4. Configure the 10 `rc_map_*` contract tiles (`device_tracker.rc_map_device_tracker` + `sensor.rc_map_latitude` + `sensor.rc_map_longitude` + `sensor.rc_map_accuracy_meters` + `sensor.rc_map_speed_kph` + `sensor.rc_map_bearing_degrees` + `binary_sensor.rc_map_has_fix` + `binary_sensor.rc_map_internet_reachable_for_tiles` + `sensor.rc_map_basemap_mode` + `select.rc_map_trip_overlay`) to mirror the upstream state via the HA core `template:` sensor + binary_sensor + select wrappers.
5. Wire the FIVE §9 MANDATORY automations (§9.1 basemap-mode-online-requires-internet-reachability guard + §9.2 basemap-mode-cached-prefers-local-tile-archive guard + §9.3 basemap-mode-fallback to offline when tile servers unreachable + §9.4 has-fix-blocks-tile-flicker guard + §9.5 trip-overlay-active-only-when-vehicle-moving guard).
6. Verify: confirm the device_tracker → confirm the basemap mode → confirm the trip overlay → open the Lovelace map card → confirm the current location renders → confirm the trip overlay renders → toggle the basemap mode to test the §9.3 fallback automation.

Full howto: see [`docs/recipe.md`](docs/recipe.md).

## The 10 `rc_map_*` contract tiles

| Domain | Tile id | Purpose |
|---|---|---|
| `device_tracker` | `rc_map_device_tracker` | Resolved current device_tracker — mirrors `input_text.rc_location_tracker_entity`. |
| `sensor` | `rc_map_latitude` | Current latitude — `template:` sensor derived from `device_tracker.*`'s `latitude` attribute. |
| `sensor` | `rc_map_longitude` | Current longitude — `template:` sensor derived from `device_tracker.*`'s `longitude` attribute. |
| `sensor` | `rc_map_accuracy_meters` | Current accuracy in meters — `template:` sensor derived from `device_tracker.*`'s `gps_accuracy` / `accuracy` attribute. |
| `sensor` | `rc_map_speed_kph` | Current speed in kph — `template:` sensor derived from `device_tracker.*`'s `speed` attribute. |
| `sensor` | `rc_map_bearing_degrees` | Current bearing / heading in degrees — `template:` sensor derived from `device_tracker.*`'s `course` / `heading` attribute. |
| `binary_sensor` | `rc_map_has_fix` | TRUE if lat/lng present + accuracy < 1000m — `template:` binary_sensor. |
| `binary_sensor` | `rc_map_internet_reachable_for_tiles` | TRUE if the upstream tile servers are reachable — `template:` binary_sensor (the §9.3 fallback target). |
| `sensor` | `rc_map_basemap_mode` | Current resolved basemap mode — `template:` sensor (Off / Online / Cached / Offline). |
| `select` | `rc_map_trip_overlay` | Trip overlay mode — Off / Active / Recent-7d / All-Time. |

## The 5 §9 MANDATORY automations

- **§9.1 Basemap-mode-online-requires-internet-reachability guard** — fires when `binary_sensor.rc_map_internet_reachable_for_tiles` is FALSE AND `sensor.rc_map_basemap_mode` resolves to `Online`. Logs a critical audit entry + fires a notification warning the operator that the basemap mode requires internet reachability + flips `sensor.rc_map_basemap_mode` to `Offline` (the §9.3 fallback).
- **§9.2 Basemap-mode-cached-prefers-local-tile-archive guard** — fires when `sensor.rc_map_basemap_mode` resolves to `Cached` AND the operator-configured tile archive path is empty. Logs a warning audit entry + fires a notification warning the operator that the cached mode requires a populated tile archive + flips `sensor.rc_map_basemap_mode` to `Offline` (the §9.3 fallback).
- **§9.3 Basemap-mode-fallback to offline when tile servers unreachable** — fires when `binary_sensor.rc_map_internet_reachable_for_tiles` is FALSE. Flips `sensor.rc_map_basemap_mode` to `Offline` + fires a notification warning the operator that the map has fallen back to offline.
- **§9.4 Has-fix-blocks-tile-flicker guard** — fires when `binary_sensor.rc_map_has_fix` toggles FALSE→TRUE or TRUE→FALSE. Debounces the tile-recenter signal + logs an audit entry + keeps the map from flickering between stale + fresh fixes.
- **§9.5 Trip-overlay-active-only-when-vehicle-moving guard** — fires when `sensor.rc_map_speed_kph` is below 1 kph (vehicle is parked) AND `select.rc_map_trip_overlay` is set to `Active`. Flips `select.rc_map_trip_overlay` to `Off` + logs an audit entry + fires a notification warning the operator that the trip overlay is suppressed because the vehicle is parked.

## Why tier-a, but beta

Tier-a is the right tier because the legacy catalog page's "Support tier: A (RoamCore native)" is correct: RoamCore DOES own + ship + maintain the three packages at `homeassistant/packages/roamcore_map.yaml` + `homeassistant/packages/roamcore_map_route.yaml` + `homeassistant/packages/roamcore_location.yaml`. This slice ADDS the recipe layer (manifest + recipe.md + smoke + cross-references + legacy SUPERSEDED banner) WITHOUT modifying the existing package contents.

Status is `beta` because there are no pytest integration tests for the map packages (HA core `map:` card is the actual surface; the audit script asserts the manifest is honest about being tier-a + the recipe layer is documented + the contract tiles are vendor-neutral + the FIVE §9 MANDATORY automations are documented). The five honesty warnings (`no_pytest_bench_fixtures_for_map_packages` + `recipe_depends_on_user_configuring_device_tracker` + `recipe_depends_on_user_configuring_tile_url` + `requires_operator_wiring_basemap_mode_picker_before_first_use` + `has_fix_guard_must_be_wired`) document the bench-fixture gap + the operator-side wiring dependencies + the operator-side picker wiring + the §9.4 guard wiring.

## Files

- `connection.yml` — the source-of-truth tier-a manifest.
- `__init__.py` — `DOMAIN = "map"` marker for the audit.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded by this slice): [`docs/catalog/map/map-dashboard.md`](../../docs/catalog/map/map-dashboard.md)
- Existing RoamCore-owned map package (preserved verbatim): [`homeassistant/packages/roamcore_map.yaml`](../../homeassistant/packages/roamcore_map.yaml) (31 LOC — declares the `input_text.rc_map_tile_url` + `rc_map_tile_url_online` + `rc_map_style_url` + `input_number.rc_map_offline_max_zoom` helpers)
- Existing RoamCore-owned map route package (preserved verbatim): [`homeassistant/packages/roamcore_map_route.yaml`](../../homeassistant/packages/roamcore_map_route.yaml) (10 LOC — declares the `input_number.rc_map_route_device_id` helper)
- Existing RoamCore-owned location package (preserved verbatim): [`homeassistant/packages/roamcore_location.yaml`](../../homeassistant/packages/roamcore_location.yaml) (123 LOC — declares the `input_text.rc_location_tracker_entity` helper + the 11 `template:` sensors that map a configurable `device_tracker.*` → `rc_location_*`)
- HA core `map:` integration (the canonical map card surface): https://www.home-assistant.io/integrations/map/
- HA core `device_tracker` integration (the canonical GPS-source umbrella): https://www.home-assistant.io/integrations/device_tracker/
- HA core `template:` integration (the canonical upstream-entity-aggregation layer for the 6 `rc_map_*` `template:` sensor tiles + the 2 `rc_map_*` `template:` binary_sensor tiles): https://www.home-assistant.io/integrations/template/
- HA core `input_text` integration (the canonical `input_text.rc_location_tracker_entity` + `rc_map_tile_url` + `rc_map_tile_url_online` + `rc_map_style_url` helpers): https://www.home-assistant.io/integrations/input_text/
- HA core `input_number` integration (the canonical `input_number.rc_map_offline_max_zoom` + `rc_map_route_device_id` helpers): https://www.home-assistant.io/integrations/input_number/
- HA core `input_select` integration (the canonical basemap-mode + trip-overlay pickers): https://www.home-assistant.io/integrations/input_select/
- HA core `automation:` integration (the canonical umbrella for the FIVE §9 MANDATORY automations): https://www.home-assistant.io/integrations/automation/
- Time-atomic (the time-of-day primitives used by the §9.5 trip-overlay-active-only-when-vehicle-moving guard's "vehicle just started moving" edge detection): `connections/time-atomic/` (Wave 3 #55)
- Remote-access (the VPN primitive used by the §9.1 basemap-mode-online-requires-internet-reachability guard's internet-reachability check): `connections/remote-access/` (Wave 3 #58)
- Mode (the §9.5 trip-overlay-active-only-when-vehicle-moving guard's mode-change cross-reference): `connections/mode/` (Wave 3 #61)
- Demo-mode (the §9.1 basemap-mode-online-requires-internet-reachability guard's safety-chip pattern): `connections/demo-mode/` (Wave 3 #62)
- Advanced-mode (the §9.4 has-fix-blocks-tile-flicker guard's confirm-flag pattern): `connections/advanced-mode/` (Wave 3 #63)
- OpenClaw JSON API (the §9.1 basemap-mode-online-requires-internet-reachability guard's JSON payload cross-reference): `connections/openclaw-api/` (Wave 3 #64)
- Leveling (the §9.5 trip-overlay-active-only-when-vehicle-moving guard's leveling-jack cross-reference): `connections/leveling/` (Wave 3 #60)
- Fans (the §9.1 basemap-mode-online-requires-internet-reachability guard's fan-protection cross-reference): `connections/fans/` (Wave 3 #59)
- Approach lights (the dashboard banner pattern used by the §9.3 basemap-mode-fallback to offline automation): `connections/approach-lights/` (Wave 3 #52)
- Agent actions allowlist (the §9.3 basemap-mode-fallback to offline automation's kill-switch integration): `connections/agent-actions-allowlist/` (Wave 3 #65)
- RoamCore entity naming: [`docs/reference/rc-entity-naming.md`](../../docs/reference/rc-entity-naming.md) (the `map` subsystem was added by this slice)
