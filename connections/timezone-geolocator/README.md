# Timezone geolocator (location-aware HA timezone)

**Tier:** C (recipe)
**Category:** time
**Status:** recipe_published

## What this connection is

Timezone geolocator (location-aware HA timezone) — the umbrella for "keep HA's system timezone correct as the van travels across regions so that time-based automations (sun events + `now()` + `today_at()`) keep working" — is the time-category complement to the existing RoamCore time helpers (`homeassistant/packages/roamcore_weather_time.yaml` + `sensor.rc_time_zone` override contract). The single "is the timezone synced?" tile aggregates GeoLocator's last-update state into one dashboard indicator; the "is the timezone stale?" tile is the freshness gate (TRUE when `sensor.rc_time_zone_last_update_minutes_ago` > 60); the GPS-source sensor surfaces which upstream tracker is feeding `zone.home`; the operator-tunable update-cadence (event_driven / 15_min / 60_min / manual) select covers the day-1 cadence choice; the update-now button covers the on-demand affordance (force a `geolocator.update_location` call without waiting for the next cadence tick).

RoamCore ships **no** native timezone engine. We RECIPE the GeoLocator HACS integration by SmartyVan (`https://github.com/SmartyVan/hass-geolocator`) and a thin RoamCore automation wrapper. The 8 `rc_time_zone_*` contract tiles are the vendor-neutral layer the dashboard + OpenClaw queries use; the actual timezone lookup is done by GeoLocator's offline table (RoamCore does NOT fork GeoLocator).

## Setup recipe (one-paragraph)

1. Install GeoLocator via HACS → Repositories → Custom repositories (URL: `https://github.com/SmartyVan/hass-geolocator`, Category: Integration).
2. Restart Home Assistant (GeoLocator loads at startup).
3. Wire a GPS source to `zone.home`. Options: **Traccar** (Wave 3 #36) for the canonical server-side GPS feed; **HA Companion app** for the operator's phone GPS; **Wican Pro** (Wave 3 #6) for the OBD-II reader's GPS feed (always-on even when phone is asleep); or any `device_tracker.*` entity that calls `homeassistant.set_location` on update.
4. Pick the update cadence: **15-min default** (conservative; recommended for most vans) OR **event-driven** (triggers on `zone.home` changes only; lower latency but requires a reliable change-trigger) OR **manual** (operator-driven via the `button.rc_time_zone_update_now` button).
5. Wire the §5 automation (RoamCore Update timezone via GeoLocator) — the recipe §5 walks through both cadence options.
6. Verify: call `geolocator.update_location` manually once + check that `sensor.rc_time_zone_current` reflects the correct timezone.

Full howto: see [`docs/recipe.md`](docs/recipe.md).

## Why tier-c, not tier-b

Tier-b would require a RoamCore-owned timezone engine + integration code + integration tests against a real timezone-update bench (a Traccar server + a mock GPS feed + canned fixture responses). We have no operator-side timezone bench on the CI to integration-test against (the bench requires GeoLocator itself, which is upstream HACS code, plus a Traccar server, which is a separate service). Tier-c is the honest tier: GeoLocator is upstream HACS code (not RoamCore-owned); the RoamCore wrapper is a thin automation + a contract layer. The recipe is sound but we cannot claim one-tap automation.

The original legacy catalog page (`docs/catalog/time/timezone-geolocator.md`) listed "Support tier: C" with no recipe + no contract + no automations — that placeholder is now superseded by this tier-c recipe connection.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "timezone_geolocator"` marker for the audit.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded): [`docs/catalog/time/timezone-geolocator.md`](../../docs/catalog/time/timezone-geolocator.md)
- GeoLocator upstream (HACS): https://github.com/SmartyVan/hass-geolocator
- Traccar connection (the canonical GPS source; Wave 3 #36): `connections/traccar/`
- Wican Pro OBD-II connection (the optional GPS source; Wave 3 #6): `connections/wican-pro/`
- HA Companion app (the operator-side GPS source): upstream integration
- Time / weather contract (the existing time helpers; Wave 2 #14 + Wave 2 #15 + Wave 3 #55): `homeassistant/packages/roamcore_weather_time.yaml`
- Teltonika (the optional LTE/5G router for vans; Wave 3 #39): `connections/teltonika/`
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`