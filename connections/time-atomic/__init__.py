"""Time (atomic) (NTP-synchronized time with offline-resilience) — tier-c
recipe connection.

This module is a marker-only stub. Tier-c connections don't ship native
HA integration code; they publish a recipe (docs/recipe.md) that walks
the user through installing the upstream HA core `time` integration
(since 2022.x — exposes NTP servers + `sensor.time` + `sensor.date` +
date/time helpers) + wiring ONE OR MORE time sources (Path A NTP via
HA core `time` integration + Path B GPS-derived time via Traccar
Wave 3 #36 server / HA Companion app / Wican Pro Wave 3 #6 OBD-II's
GPS feed / any `device_tracker.*` updating `zone.home` + Path C
cellular RTC fallback via DS3231 / RV-3028 I2C RTC module on the
van's NUC / SBC) + adding a thin RoamCore automation wrapper that
runs the THREE §7 automations (NTP cadence refresh on boot + GPS
time correction on `device_tracker` + timezone change + RTC
fallback when NTP unreachable for N minutes). The recipe exposes
the resulting data via the upstream `time` + `zone` +
`device_tracker` + `homeassistant` service + `template` +
`input_boolean` + `input_datetime` integrations, then publishes
the RoamCore time-atomic contract tiles on top (the 8 contract
entities documented in connection.yml — 1 sensor current-time + 1
sensor NTP-source + 1 sensor last-sync-minutes-ago + 1 sensor
drift-seconds + 1 binary_sensor synced + 1 binary_sensor stale +
1 binary_sensor NTP-reachable + 1 binary_sensor RTC-present).

The audit + boundary CI can detect a `time-atomic/` folder that
claims to be a connection via the `DOMAIN` constant exported here.
The wizard reads the manifest + recipe at runtime.

The real per-operator time-atomic affordance path is:

    Operator-side time source (Path A — HA core `time`
        integration's NTP server list (`time.cloudflare.com` +
        `time.google.com` + `pool.ntp.org`) reaching out over
        LTE / Starlink; OR Path B — `device_tracker.rc_location_
        van` (Traccar Wave 3 #36) OR `device_tracker.<phone>`
        (HA Companion) OR `device_tracker.<wican_pro_name>`
        (Wican Pro Wave 3 #6) GPS feed where GPS satellites
        carry atomic-clock-grade time signals; OR Path C —
        DS3231 / RV-3028 I2C RTC module on the van's NUC / SBC
        that ticks even when the network is down + the SBC's
        `systemd-timesyncd` fallback config)
        -> upstream entity (`sensor.time` + `sensor.date` from
           HA core `time` integration OR the GPS source's
           device_tracker attributes OR the SBC's `hwclock`
           output)
        -> RoamCore contract layer (HA core `template:` sensor +
           binary_sensor that mirrors the upstream time state +
           the THREE §7 automations into the 8 `rc_time_*`
           contract tiles)
        -> dashboard tiles + OpenClaw queries
            ("what time is it on the van?", "what NTP source
             is the van using?", "when was the clock last
             NTP-synced?", "what is the drift in seconds vs
             the last-known-good source?", "is the clock
             NTP-synced?", "is the clock stale?", "is NTP
             reachable from the van?", "is the RTC present?")

    Safety interlocks (the recipe is the contract layer; the
    automation wrappers are documented in §7):
        -> The RoamCore NTP cadence refresh on boot automation
           is the §7.1 automation that ensures the system clock
           is NTP-synchronized as soon as possible after HA
           boot.
        -> The RoamCore GPS time correction on `device_tracker`
           + timezone change automation is the §7.2 automation
           that uses GPS-derived time (atomic-clock-grade from
           GPS satellites) when NTP is unreachable but GPS is.
           Triggers on `device_tracker` state changes AND on
           timezone changes (cross-references Wave 3 #54
           timezone-geolocator's `binary_sensor.rc_time_zone_
           stale` tile).
        -> The RoamCore RTC fallback when NTP unreachable for
           N minutes automation is the §7.3 automation that
           reads the DS3231 / RV-3028 RTC module + applies the
           RTC time to the system clock when NTP has been
           unreachable for N minutes (default: 10 minutes).
           This is the offline-resilience feature — the van
           can lose LTE / Starlink for hours and still keep
           accurate time via the RTC.

    Cross-references:
        -> The NTP source optionally cross-references the
           Teltonika Wave 3 #39 LTE router (the LTE backhaul
           for vans that use LTE for NTP).
        -> The NTP source optionally cross-references Starlink
           Wave 3 #36 (the Starlink backhaul for vans that use
           Starlink for NTP).
        -> The GPS source cross-references the Traccar Wave 3
           #36 server (the canonical GPS source for the
           RoamCore map page; GPS satellites carry
           atomic-clock-grade time signals).
        -> The GPS source cross-references the HA Companion app
           (the operator's phone GPS feed).
        -> The GPS source cross-references the Wican Pro Wave
           3 #6 OBD-II reader's GPS feed (always-on even when
           the phone is asleep).
        -> The existing RoamCore time helpers
           (`homeassistant/packages/roamcore_weather_time.yaml`
           + `sensor.rc_time_zone` override contract)
           cross-reference the `sensor.rc_time_current` tile
           as the source of truth for the system clock.
        -> The Wave 3 #54 timezone-geolocator connection
           cross-references this slice via the `binary_sensor
           .rc_time_zone_stale` tile (which the §7.2 GPS time
           correction automation can use as an additional
           trigger — when the timezone goes stale, refresh the
           time via GPS).

See docs/recipe.md for the full howto (HA core `time`
integration install + NTP server list configuration + Path A NTP
wiring + Path B GPS time correction wiring + Path C RTC fallback
wiring + the THREE §7 automations + the 8 `rc_time_*` contract
tiles + the 6 §8 troubleshooting entries + privacy + tier-b
promotion outline).
"""

DOMAIN = "time_atomic"
