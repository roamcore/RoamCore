"""Map dashboard — vendor-neutral map tile + device_tracker
aggregation + trip overlay + offline-tile cache — tier-a
recipe connection.

Note on upstream wiring: tier-a connections for the
RoamCore map dashboard don't ship a RoamCore-owned
operator-wired setup flow (a RoamCore operator-wired
wizard); instead, each path uses the upstream
integration's GUI flow (the HA core `map:` card (since
2022.x — exposes a GUI flow for the operator to add a
map card to a Lovelace view) + the HA core
`device_tracker` integration (since 2022.x — exposes the
canonical `device_tracker.*` umbrella for GPS sources) +
the HA core `template:` sensor wrapper (since 2022.x —
exposes a GUI flow for the operator to add a derived
`sensor.*` entity from upstream sensors) + the HA core
`template:` binary_sensor wrapper (since 2022.x —
exposes a GUI flow for the operator to add a derived
`binary_sensor.*` entity from upstream sensors) + the
HA core `input_text` helper (since 2022.x — exposes a
GUI flow for the operator to add an `input_text.*`
helper) + the HA core `input_number` helper (since
2022.x — exposes a GUI flow for the operator to add an
`input_number.*` helper) + the HA core `input_select`
helper (since 2022.x — exposes a GUI flow for the
operator to add an `input_select.*` helper) + the HA
core `select:` domain (since 2022.x — exposes a GUI flow
for the operator to add a `select.*` entity) + the HA
core `automation:` integration (since 2022.x — exposes
the canonical automation runner) all expose their own
operator-wired setup flow + GUI flow).

This module is a marker-only stub. The map-dashboard
connection is a tier-a recipe connection that WRAPS the
existing RoamCore-owned packages at
`homeassistant/packages/roamcore_map.yaml` (31 LOC —
the `input_text.rc_map_tile_url` + `rc_map_tile_url_
online` + `rc_map_style_url` +
`input_number.rc_map_offline_max_zoom` helpers) +
`homeassistant/packages/roamcore_map_route.yaml` (10
LOC — the `input_number.rc_map_route_device_id` helper)
+ `homeassistant/packages/roamcore_location.yaml` (123
LOC — the `input_text.rc_location_tracker_entity` + the
11 `template:` sensors that map a configurable
`device_tracker.*` → `rc_location_lat` + `rc_location_
lon` + `rc_location_accuracy_m` + `rc_location_source`
+ `rc_location_speed` + `rc_location_heading_deg` + the
6 trip-summary `rc_trip_*` template sensors). The three
packages are ALREADY SHIPPED + RoamCore-owned + loaded
via the standard HA `packages:` mechanism — the tier-a
claim IS honest: the legacy catalog page's "Support
tier: A (RoamCore native)" is correct because RoamCore
DOES own + ship + maintain those packages. This slice
preserves the package contents verbatim (the recipes an
upstream-entity-aggregation wrapper on top + the
contract layer + the FIVE §9 MANDATORY automations + the
operator-side basemap-mode + trip-overlay picker +
the docs cross-references).

The audit + boundary CI can detect a `map-dashboard/`
folder that claims to be a connection via the `DOMAIN`
constant exported here. The wizard reads the manifest +
recipe at runtime.

The real per-operator map-dashboard affordance path is:

    Operator-side choice of the FIVE-step flow
    (Configure the device_tracker + Pick a basemap mode
    + Pick a trip overlay + Verify the map renders +
    Toggle between Online / Cached / Offline)
    -> upstream entities (the HA core
       `device_tracker.*` for the resolved current
       device_tracker — typically
       `device_tracker.traccar_van` if Traccar is the
       upstream source, or a phone-derived
       device_tracker if the HA Companion app is the
       upstream source; the HA core
       `input_text.rc_location_tracker_entity` for the
       operator-configurable upstream tracker entity_id;
       the HA core
       `input_text.rc_map_tile_url` for the operator-
       configurable upstream tile URL; the HA core
       `input_text.rc_map_tile_url_online` for the
       online-fallback tile URL; the HA core
       `input_text.rc_map_style_url` for the operator-
       configurable MapLibre style URL; the HA core
       `input_number.rc_map_offline_max_zoom` for the
       offline-tile-archive max zoom; the HA core
       `input_number.rc_map_route_device_id` for the
       route-device id)
    -> upstream signals (the operator-configured
       `device_tracker.*`'s `latitude` + `longitude` +
       `gps_accuracy` + `speed` + `course` attributes;
       the operator-configured upstream tile URL's
       HTTP-reachability signal; the operator's tile
       cache; the operator's trip-wrapped + trip-local
       databases)
    -> RoamCore contract layer (the three existing
       RoamCore-owned packages + the HA core
       `template:` sensor + binary_sensor + select
       wrappers for the 10 `rc_map_*` contract tiles
       + the HA core `automation:` integration for
       the FIVE §9 MANDATORY automations)
    -> dashboard tiles + OpenClaw queries
        ("where is the van right now?",
         "what is the current latitude?",
         "what is the current longitude?",
         "what is the current GPS accuracy?",
         "what is the current speed?",
         "what is the current bearing?",
         "is there a GPS fix right now?",
         "are the tile servers reachable?",
         "what is the current basemap mode?",
         "what trip overlay is on the map?")

    Safety interlocks (the recipe is the contract
    layer; the automation wrappers are documented in
    §9):
        -> The RoamCore basemap-mode-online-requires-
           internet-reachability guard is the §9.1
           automation that fires when
           `binary_sensor.rc_map_internet_reachable_for_
           tiles` is FALSE AND
           `sensor.rc_map_basemap_mode` resolves to
           `Online`. The automation logs a critical
           audit entry + fires a notification warning
           the operator that the basemap mode requires
           internet reachability for the upstream tile
           servers + flips
           `sensor.rc_map_basemap_mode` to `Offline`
           (the §9.3 basemap-mode-fallback automation).
        -> The RoamCore basemap-mode-cached-prefers-
           local-tile-archive guard is the §9.2
           automation that fires when
           `sensor.rc_map_basemap_mode` resolves to
           `Cached` AND the operator-configured tile
           archive path is empty. The automation logs
           a warning audit entry + fires a notification
           warning the operator that the cached mode
           requires a populated tile archive + flips
           `sensor.rc_map_basemap_mode` to `Offline`
           (the §9.3 basemap-mode-fallback automation).
        -> The RoamCore basemap-mode-fallback to
           offline when tile servers unreachable is
           the §9.3 automation that fires when
           `binary_sensor.rc_map_internet_reachable_for_
           tiles` is FALSE. The automation flips
           `sensor.rc_map_basemap_mode` to `Offline` +
           fires a notification warning the operator
           that the map has fallen back to offline.
        -> The RoamCore has-fix-blocks-tile-flicker
           guard is the §9.4 automation that fires
           when `binary_sensor.rc_map_has_fix` toggles
           FALSE→TRUE or TRUE→FALSE. The automation
           debounces the tile-recenter signal + logs
           an audit entry + keeps the map from
           flickering between stale + fresh fixes.
        -> The RoamCore trip-overlay-active-only-when-
           vehicle-moving guard is the §9.5 automation
           that fires when
           `sensor.rc_map_speed_kph` is below 1 kph
           (vehicle is parked) AND
           `select.rc_map_trip_overlay` is set to
           `Active`. The automation flips
           `select.rc_map_trip_overlay` to `Off` +
           logs an audit entry + fires a notification
           warning the operator that the trip overlay
           is suppressed because the vehicle is parked.

    Cross-references:
        -> The three RoamCore-owned packages at
           `homeassistant/packages/roamcore_map.yaml`
           + `homeassistant/packages/roamcore_map_
           route.yaml` + `homeassistant/packages/
           roamcore_location.yaml` are the canonical
           umbrella for the map-dashboard contract
           (already shipped + already RoamCore-owned
           + already loaded via the standard HA
           `packages:` mechanism; preserved verbatim by
           this slice).
        -> The HA core `device_tracker` integration is
           the canonical umbrella for GPS sources
           (since 2022.x).
        -> The HA core `template:` sensor wrapper is
           the canonical upstream-entity-aggregation
           layer for the 6 `rc_map_*` `template:`
           sensor tiles (since 2022.x).
        -> The HA core `template:` binary_sensor
           wrapper is the canonical upstream-entity-
           aggregation layer for the 2 `rc_map_*`
           `template:` binary_sensor tiles (since
           2022.x).
        -> The HA core `input_text` + `input_number`
           + `input_select` helpers are the canonical
           umbrella for the operator-configurable
           upstream-entity pointers (since 2022.x).
        -> The HA core `select:` domain is the
           canonical umbrella for the
           `select.rc_map_trip_overlay` tile (since
           2022.x).
        -> The HA core `automation:` integration is
           the canonical umbrella for the FIVE §9
           MANDATORY automations (since 2022.x).
        -> The time-atomic Wave 3 #55 connection
           cross-references the time-of-day primitives
           used by the §9.5 trip-overlay-active-only-
           when-vehicle-moving guard's "vehicle just
           started moving" edge detection.
        -> The remote-access Wave 3 #58 connection
           cross-references the VPN primitive used by
           the §9.1 basemap-mode-online-requires-
           internet-reachability guard's
           internet-reachability check.
        -> The mode Wave 3 #61 connection cross-
           references the §9.5 trip-overlay-active-
           only-when-vehicle-moving guard's mode-
           change cross-reference (the guard surfaces
           trip-overlay transitions on the mode-change
           notification timeline).
        -> The demo-mode Wave 3 #62 connection cross-
           references the §9.1 basemap-mode-online-
           requires-internet-reachability guard's
           safety-chip pattern (mirrors the demo-mode
           §8.2 never-controls-actual-hardware
           guard's safety-chip pattern).
        -> The advanced-mode Wave 3 #63 connection
           cross-references the §9.4 has-fix-blocks-
           tile-flicker guard's confirm-flag pattern
           (mirrors the advanced-mode §8.1 confirm-
           before-toggle-on guard's confirm-flag
           pattern).
        -> The openclaw-api Wave 3 #64 connection
           cross-references the §9.1 basemap-mode-
           online-requires-internet-reachability
           guard's JSON payload cross-reference (the
           openclaw-api contract version surfaces map
           events via the JSON API).
        -> The leveling Wave 3 #60 connection cross-
           references the §9.5 trip-overlay-active-
           only-when-vehicle-moving guard's leveling-
           jack cross-reference (the guard prevents
           trip overlay rendering while the vehicle
           is being leveled).
        -> The fans Wave 3 #59 connection cross-
           references the §9.1 basemap-mode-online-
           requires-internet-reachability guard's
           fan-protection cross-reference (the guard
           protects real fans from being toggled by
           map-dashboard events).
        -> The approach lights Wave 3 #52 connection
           cross-references the dashboard banner
           pattern used by the §9.3 basemap-mode-
           fallback to offline automation.
        -> The agent-actions-allowlist Wave 3 #65
           connection cross-references the §9.3
           basemap-mode-fallback to offline
           automation's kill-switch integration (the
           kill switch disables agent-driven basemap-
           mode changes when the operator has the
           agent kill switch OFF).

See docs/recipe.md for the full howto (the three
RoamCore-owned packages install via the standard HA
`packages:` mechanism + the HA core `map:` card install
+ the HA core `device_tracker` integration install +
the HA core `template:` sensor wrapper install + the
HA core `template:` binary_sensor wrapper install +
the HA core `input_text` + `input_number` +
`input_select` helpers install + the HA core `select:`
domain install + the HA core `automation:` integration
install + the FIVE-step operator-pickable map-dashboard
flow + the 10 `rc_map_*` contract tiles + the FIVE §9
MANDATORY automations + the 6 §10 troubleshooting
entries + privacy + tier-a promotion outline).
"""

DOMAIN = "map"
