"""Timezone geolocator (location-aware HA timezone) — tier-c recipe connection.

This module is a marker-only stub. Tier-c connections don't ship native
HA integration code; they publish a recipe (docs/recipe.md) that walks
the user through installing the GeoLocator HACS integration by
SmartyVan (https://github.com/SmartyVan/hass-geolocator) + wiring a
GPS source to keep `zone.home` updated (Traccar Wave 3 #36 / HA
Companion app / Wican Pro Wave 3 #6 OBD-II's GPS feed / any
`device_tracker.*` updating `zone.home`) + adding a thin RoamCore
automation wrapper that calls `geolocator.update_location` on a
cadence the operator picks (15-min default; event-driven alternative).
The recipe exposes the resulting data via the upstream `zone` +
`device_tracker` + `homeassistant` service + `template` +
`input_boolean` + `input_datetime` + HACS `geolocator` integrations,
then publishes the RoamCore timezone-geolocator contract tiles on
top (the 8 contract entities documented in connection.yml — 1 sensor
timezone + 1 sensor offset-minutes + 1 binary_sensor synced +
1 sensor last-update-minutes-ago + 1 binary_sensor stale +
1 sensor GPS-source + 1 select update-cadence + 1 button
update-now).

The audit + boundary CI can detect a `timezone-geolocator/` folder
that claims to be a connection via the `DOMAIN` constant exported
here. The wizard reads the manifest + recipe at runtime.

The real per-operator timezone-geolocator affordance path is:

    Operator-side GPS source (Traccar Wave 3 #36 server exposing
        `device_tracker.rc_location_van` OR the HA Companion app's
        `device_tracker.<phone>` entity OR a Wican Pro Wave 3 #6
        OBD-II reader's GPS feed OR any other `device_tracker.*`
        entity that updates `zone.home` coordinates)
        -> upstream entity (`device_tracker.rc_location_van` OR
           `device_tracker.<phone>` OR the Wican Pro GPS entity)
        -> `zone.home` (HA core `zone` integration's home zone —
           the operator's home zone entity that GeoLocator reads
           from)
        -> GeoLocator HACS integration's offline timezone lookup
           (computes the correct timezone ID from `zone.home`
           coordinates; updates HA's system timezone via the
           upstream `homeassistant.set_time_zone` service)
        -> HA system timezone (the operator's `now()` + `today_at()`
           + `sun.sun` integration now reflect the correct
           timezone)
        -> RoamCore contract layer (HA core `template:` sensor +
           binary_sensor + select + button that mirrors the
           upstream GeoLocator state + the cadence-driven
           automation trigger into the 8 `rc_time_zone_*` contract
           tiles)
        -> dashboard tiles + OpenClaw queries
            ("what timezone is the van in?", "is the timezone
             synced?", "when was the timezone last updated?",
             "is the timezone stale?", "what is the GPS source
             for the timezone?", "set the timezone update cadence
             to event_driven / 15_min / 60_min / manual", "update
             the timezone now")

    Safety interlocks (the recipe is the contract layer; the
    automation wrappers are documented in §5):
        -> The RoamCore Update timezone automation (15-min cadence
           default OR event-driven on `zone.home` change) is the
           ONLY automation the recipe ships. GeoLocator handles
           the timezone lookup + the `homeassistant.set_time_zone`
           service call internally. The recipe §5.1 walks through
           the 15-min cadence option; §5.2 walks through the
           event-driven option.

    Cross-references:
        -> The GPS source optionally cross-references the Traccar
           Wave 3 #36 server (the canonical GPS source for the
           RoamCore map page).
        -> The GPS source optionally cross-references the HA
           Companion app (the operator's phone GPS feed).
        -> The GPS source optionally cross-references the Wican
           Pro Wave 3 #6 OBD-II reader's GPS feed (the OBD-II
           reader is in the van so its GPS is always-on even when
           the operator's phone is asleep).
        -> The existing RoamCore time helpers
           (`homeassistant/packages/roamcore_weather_time.yaml` +
           `sensor.rc_time_zone` override contract) cross-reference
           the `sensor.rc_time_zone_current` tile as the source
           of truth for the system timezone — this slice
           complements the existing time helpers by automating
           the timezone update; the existing time helpers remain
           the canonical place for the override-input
           (`input_text.rc_time_zone_override`).

See docs/recipe.md for the full howto (HACS install + the GPS
source wiring (Traccar / HA Companion / Wican Pro / generic
device_tracker) + `homeassistant.set_location` fallback + the
15-min cadence vs event-driven update choice + the 8 `rc_time_zone_*`
contract tiles + the single §5 automation + the 6 §6 troubleshooting
entries + privacy + tier-b promotion outline).
"""

DOMAIN = "timezone_geolocator"