# Mock location + track replay

**Tier:** A (RoamCore native)
**Category:** Map
**Status:** beta

## What this connection is

Mock location + track replay is the **dev/demo polyline generator**
for the RoamCore map page. It generates a deterministic synthetic GPS
track as a GeoJSON LineString and exposes it as a semicolon-separated
`input_text.rc_map_mock_location_trail` of lat,lon pairs that the
`<MapMockPolyline />` dashboard tile + the Trip Wrapped dev/demo HTML
report can render without any real Traccar GPS data.

## Why this matters in a van

For development and demos you don't always have a real GPS feed handy:

- **Offline development** — work on the map page / Trip Wrapped HTML
  report on a train / plane / café without needing a Traccar
  receiver attached.
- **Trip demos** — show off the map page's polyline rendering with a
  deterministic, scenic synthetic route (e.g. `uk_roadtrip` London →
  Cambridge → Manchester → Lake District → Edinburgh → Belfast →
  Dublin → Birmingham → London) instead of a `home → grocery store`
  breadcrumb.
- **Trip Wrapped dev/demo HTML report** — when no real trip data is
  available, the Trip Wrapped recipe treats the mock as Traccar data
  and generates the same beautiful HTML report from the synthetic
  polyline (useful for marketing screenshots + integration tests).

## Why tier-a, not tier-b

Tier-a requires that RoamCore owns ALL of the integration code
natively (the YAML packages + the Python generator) and that there is
**no external broker / device / vendor dependency**. The mock polyline
generator satisfies both:

- `homeassistant/packages/roamcore_mock_track.yaml` — shell_command +
  script + startup automation.
- `homeassistant/packages/roamcore_mock_location_trail.yaml` —
  input_text helper for the lat,lon trail.
- `homeassistant/packages/roamcore_dev_mocks.yaml` — umbrella dev
  helpers package (power / net / level / trip / map input_* helpers).
- `homeassistant/tools/mock_track/generate.py` — dependency-free
  (stdlib only) Python polyline generator with six built-in presets.

The mock is **opt-in** via `input_boolean.rc_map_mock_enabled`
(default FALSE → OFF). When the operator enables it, the map page
renders the synthetic polyline. When disabled, the map page falls
back to real Traccar (if `connections/traccar/` is enabled) or to an
empty map (if no real GPS source is wired).

This is honestly tier-a because there is no upstream vendor
integration to wrap — the integration code IS the package, and the
operator-side enable/disable is the upstream `input_boolean` toggle.

## Setup recipe (one-paragraph)

1. Confirm the three YAML packages are wired into your HA Core
   `configuration.yaml` (RoamCore's `homeassistant/configuration_addon.yaml`
   uses `!include_dir_named packages` which auto-includes everything
   under `homeassistant/packages/`).
2. Confirm `homeassistant/tools/mock_track/generate.py` is readable
   by the `shell_command` user (HAOS mounts the repo at `/config`;
   the `shell_command.rc_mock_track_generate` is hardcoded to
   `/config/tools/mock_track/generate.py` — adjust the path if your
   HAOS mount differs).
3. Toggle `input_boolean.rc_map_mock_enabled` to ON.
4. Pick a preset (`input_select.rc_map_mock_preset` → `uk_roadtrip`
   is the default for new installs).
5. Click `button.rc_map_mock_generate_now` (or wait for HA startup
   to fire `automation.rc_mock_track_generate_on_startup`).
6. Reload the RoamCore map page — the synthetic polyline should
   appear.

Full howto: see [`docs/recipe.md`](docs/recipe.md).

## Files

- `connection.yml` — the source-of-truth manifest (tier-a native;
  `wizard.connection_kind: native` + `install.kind: ha_package` +
  `install.config_flow: false`).
- `__init__.py` — `DOMAIN = "mock_location"` marker for the audit.
- `docs/recipe.md` — the full howto (~250+ lines, 11 §sections).
- `tests/test_connection_yml.py` — manifest honesty checks
  (7 assertions: tier-a audit + asset presence + recipe published +
  category + tile naming + status + package wiring).

## See also

- Legacy catalog page (now superseded):
  [the legacy spec](../../the legacy spec)
- Traccar (the real GPS source — `connections/traccar/` Wave 3 #48
  promotes the real GPS integration; when Traccar is enabled AND
  `input_boolean.rc_map_mock_enabled` is FALSE, the map page uses
  the real track).
- Trip Wrapped (`connections/trip-wrapped/` Wave 3 #69 — treats the
  mock as Traccar data when generating the dev/demo HTML report).
- Map Dashboard (`connections/map-dashboard/` Wave 3 #66 — reads
  `input_boolean.rc_map_mock_enabled` to decide mock-vs-real; the
  `<MapMockPolyline />` tile reads `sensor.rc_map_mock_track_length_km`
  + `sensor.rc_map_mock_track_point_count` for the legend readout).
- Dev mocks umbrella (`homeassistant/packages/roamcore_dev_mocks.yaml`
  — the input_* helpers used by other recipes).
- RoamCore entity naming:
  [`docs/reference/rc-entity-naming.md`](../../docs/reference/rc-entity-naming.md)
  (the `map` subsystem was added to the allowed subsystems list
  alongside this slice — see the Cron-handoff doc for the rationale).