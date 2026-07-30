# Mock location + tracks (dev/demo)

**Support tier:** A (RoamCore native)

> **Replaced by:** `connections/mock-location-and-tracks/` (Wave 3 #47, tier-a native connection, 2026-07-30)
>
> This catalog page is kept for historical context only. The canonical
> source of truth for mock location + track replay is now the
> `connections/mock-location-and-tracks/` folder, which ships:
> - `connection.yml` (tier-a native manifest)
> - `__init__.py` (`DOMAIN = "mock_location"` marker)
> - `docs/recipe.md` (~497-line howto, 11 §sections)
> - `tests/test_connection_yml.py` (7/7 manifest-honesty smoke)
>
> See the new connection folder for the full feature spec, the 9
> `rc_map_mock_*` contract tiles, the 6 built-in presets, the
> integration with Trip Wrapped + the map page, and the §11 promotion
> path to a real GPS source via `connections/traccar/`.

## What this is
RoamCore includes developer/demo mocks for location trails and tracks, useful for testing map and Trip Wrapped flows without real driving data.

## Why it’s useful in a van
Mostly for development and demos—lets you test before relying on real tracking.

## Extra hardware required
- None

## Install / best next step
- See: `docs/guides/roamcore-dev-mocks.md`
- HA packages: `homeassistant/packages/roamcore_mock_track.yaml`, `roamcore_mock_location_trail.yaml`
- Dev helpers package: `homeassistant/packages/roamcore_dev_mocks.yaml`

## Links
- (Add notes later)
