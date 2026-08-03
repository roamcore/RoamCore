> **SUPERSEDED** by `connections/timezone-geolocator/` (Wave 3 #54, shipped 2026-08-02).
> This page is kept for historical context only. The canonical spec now lives in
> `connections/timezone-geolocator/connection.yml` + `connections/timezone-geolocator/docs/recipe.md`.

# Time zone auto-detection (GeoLocator)

**Support tier:** C (custom/manual)

## What this is
RoamCore includes notes for using GeoLocator to keep time zone correct based on location.

## Why it’s useful in a van
- Automations that depend on “local time” keep working as you travel

## Extra hardware required
- None

## Install / best next step
- See: `docs/howto/geolocator-timezone.md`
- RoamCore time helpers package: `homeassistant/packages/roamcore_weather_time.yaml`

## Links
- GeoLocator project: https://github.com/SmartyVan/hass-geolocator
