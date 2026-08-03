# RoamCore Map (dashboard + route)

**Support tier:** A (RoamCore native)

## What this is
RoamCore provides a map experience inside Home Assistant, including current location and route/trip context.

## Why it’s useful in a van
- Quick “where are we / where did we park?” view
- Nice context for trips and daily travel

## Extra hardware required
- None if you already have a `device_tracker` or location source

## Install / best next step
- Core packages:
  - `homeassistant/packages/roamcore_map.yaml`
  - `homeassistant/packages/roamcore_map_route.yaml`
  - `homeassistant/packages/roamcore_location.yaml`
- If using Traccar, see the Traccar pages in this catalog

## Links
- (Add map card resources, offline map notes, videos)

---

> **SUPERSEDED — Wave 3 #66 (2026-08-03).** The tier-a claim above is now wrapped by the `connections/map-dashboard/` recipe connection (the manifest + the `connections/map-dashboard/docs/recipe.md` howto + the `connections/map-dashboard/tests/test_connection_yml.py` smoke + the 10 vendor-neutral `rc_map_*` contract tiles + the FIVE §9 MANDATORY automations + the legacy SUPERSEDED banner + the docs cross-references). The three RoamCore-owned packages at `homeassistant/packages/roamcore_map.yaml` + `homeassistant/packages/roamcore_map_route.yaml` + `homeassistant/packages/roamcore_location.yaml` are preserved verbatim by the slice. See `connections/map-dashboard/` for the canonical contract layer + the recipe + the test + the §14 cross-references.
