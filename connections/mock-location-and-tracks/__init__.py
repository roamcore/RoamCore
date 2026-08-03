"""Mock location + track replay (dev/demo polyline generator for the map page) — tier-a native connection.

This module is a marker-only stub for a tier-a **native** connection.
Unlike tier-b connections (which RECIPE upstream HA Core domains —
see `connections/smart-automations/`, `connections/heated-floors/`,
`connections/smoke-co-gas-sensors/`), tier-a connections ship all of
their integration code as RoamCore-owned YAML packages under
`homeassistant/packages/` (no upstream vendor integration is being
wrapped; no operator-walked GUI flow is required; the operator-side
enable/disable is the upstream `input_boolean` toggle).

The audit + boundary CI can detect a `mock-location-and-tracks/`
folder that claims to be a tier-a native connection via the `DOMAIN`
constant exported here. The wizard reads the manifest + recipe at
runtime.

Why tier-a (not tier-b):

    Tier-a requires that RoamCore owns ALL of the integration code
    natively (the YAML packages + the Python generator) and that
    there is NO external broker / device / vendor dependency. The
    mock polyline generator satisfies both:

      1. `homeassistant/packages/roamcore_mock_track.yaml` — defines
         the `shell_command.rc_mock_track_generate` (which calls the
         Python generator with the operator-selected preset + per-leg
         point density + per-point jitter), the
         `script.rc_mock_track_generate` wrapper (callable as a button
         press), and the `automation.rc_mock_track_generate_on_startup`
         auto-run-on-boot trigger.

      2. `homeassistant/packages/roamcore_mock_location_trail.yaml` —
         defines the `input_text.rc_map_mock_location_trail` helper
         (semicolon-separated lat,lon pairs) that the map tile reads.

      3. `homeassistant/packages/roamcore_dev_mocks.yaml` — the
         umbrella dev helpers package (input_* helpers used by other
         recipes for power / net / level / trip / map).

      4. `homeassistant/tools/mock_track/generate.py` — the
         dependency-free (stdlib only) Python polyline generator
         with six built-in presets (`uk_roadtrip`, `us_west_coast`,
         `alps_loop`, `desert_southwest`, `scandinavia_north`,
         `custom`) + per-leg point density + per-point jitter
         (meters). Writes a GeoJSON LineString feature to
         `/config/www/roamcore/mock/track.geojson`.

The operator-side enable/disable affordance path is:

    Operator enables the mock by toggling
        `input_boolean.rc_map_mock_enabled` (default FALSE → OFF)
        -> HA Core's `input_boolean:` domain (the upstream integration
           is part of HA Core since 2023.x; the recipe does NOT add
           a tier-a wrapper around it)
        -> Map page (`connections/map-dashboard/`, Wave 3 #66) reads
           the boolean and renders the synthetic polyline via the
           `<MapMockPolyline />` tile instead of (or alongside) the
           real Traccar track
        -> Trip Wrapped (`connections/trip-wrapped/`, Wave 3 #69)
           treats the mock as Traccar data when generating the
           dev/demo HTML report (if the operator hasn't enabled a
           real Traccar source)
        -> 9 `rc_map_mock_*` dashboard tiles
        -> 8 OpenClaw queries (`is mock active?`, `current preset?`,
           `point count?`, `track length km?`, `regenerate mock`,
           `set preset uk_roadtrip`, `set jitter 25`, `disable mock`)

The 9 `rc_map_mock_*` contract tiles (per
`docs/reference/rc-entity-naming.md` §map subsystem; the `map`
subsystem was added to the allowed subsystems list alongside this
slice — see the Cron-handoff doc for the rationale):

    1. `input_boolean.rc_map_mock_enabled` — master toggle (default
       FALSE). The map page reads this to decide mock-vs-real.
    2. `input_text.rc_map_mock_location_trail` — semicolon-separated
       lat,lon pairs that the `<MapMockPolyline />` tile renders as
       a polyline on the map.
    3. `input_select.rc_map_mock_preset` — the preset selector
       (`uk_roadtrip`, `us_west_coast`, `alps_loop`,
       `desert_southwest`, `scandinavia_north`, `custom`).
    4. `input_number.rc_map_mock_points_per_leg` — per-leg point
       density (10–500, default 80).
    5. `input_number.rc_map_mock_jitter_m` — per-point jitter in
       meters (0–100, default 10).
    6. `button.rc_map_mock_generate_now` — calls
       `script.rc_mock_track_generate` (which runs the Python
       generator with the current preset / points-per-leg / jitter
       values and writes the GeoJSON).
    7. `sensor.rc_map_mock_track_length_km` — template sensor over
       `input_text.rc_map_mock_location_trail`; computes the total
       polyline length in km (haversine sum over the lat,lon pairs).
    8. `sensor.rc_map_mock_track_point_count` — template sensor over
       `input_text.rc_map_mock_location_trail`; counts the number of
       lat,lon pairs.
    9. `binary_sensor.rc_map_mock_track_fresh` — TRUE when the
       polyline was generated < 1 hour ago (the operator can use
       this to detect stale mocks after a long HA downtime).

Why `wizard.connection_kind: native` + `install.kind: ha_package` +
`install.<gui-walk-through-flag>: false`:

    The mock has no upstream vendor integration to wrap — it IS the
    integration. There is no HA Core `mock_location` domain (the
    upstream integrations are `input_boolean` + `input_text` +
    `input_select` + `input_number` + `button` + `template:` + the
    `shell_command` for the Python generator). The operator enables
    the mock by toggling `input_boolean.rc_map_mock_enabled` (the
    upstream `input_boolean` integration's own GUI flow handles the
    toggle). No RoamCore-owned GUI-walk-through module is required
    because there is no upstream vendor to walk through (preset,
    points-per-leg, jitter, custom polyline — all live as `input_*`
    helpers that the operator tweaks from the RoamCore Settings →
    Map → Mock panel). The integration code is the package — the
    audit verifies that `__init__.py` does NOT contain any
    GUI-walk-through marker substring (see
    `tests/test_connection_yml.py` `test_tier_a_with_native_markers`).

Promotion path to a real GPS source (recipe §11):

    When `connections/traccar/` is enabled AND
    `input_boolean.rc_map_mock_enabled` is FALSE, the map page uses
    the real Traccar track. The mock is the fallback / dev / demo
    path — useful for offline development (no GPS), for trip demos
    (deterministic synthetic routes), and for the Trip Wrapped
    dev/demo HTML report generation when no real trip data is
    available.

See `docs/recipe.md` for the full howto.
"""

DOMAIN = "mock_location"