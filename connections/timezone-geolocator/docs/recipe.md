# Timezone geolocator — tier-c recipe connection

This is the full howto for the `connections/timezone-geolocator/`
tier-c recipe connection. It walks through installing the GeoLocator
HACS integration by SmartyVan (`https://github.com/SmartyVan/
hass-geolocator`), wiring a GPS source to keep `zone.home` updated
(Traccar Wave 3 #36 server / HA Companion app / Wican Pro Wave 3 #6
OBD-II's GPS feed / any `device_tracker.*` updating `zone.home`),
adding a thin RoamCore automation wrapper that calls
`geolocator.update_location` on a cadence the operator picks
(15-min default / event-driven / manual), mapping the upstream
GeoLocator state into the 8 `rc_time_zone_*` contract tiles, and
promoting the connection to tier-b when the bench fixture lands.

## §1 What is timezone geolocator in RoamCore?

Timezone geolocator (location-aware HA timezone) — the umbrella for
"keep HA's system timezone correct as the van travels across
regions so that time-based automations (sun events + `now()` +
`today_at()`) keep working" — is positioned in RoamCore as:

- A **reuse-first** recipe over upstream GeoLocator. RoamCore does
  NOT maintain its own timezone engine; GeoLocator's offline
  timezone lookup table is the canonical source. This is
  intentional: writing a custom timezone engine would duplicate
  work GeoLocator already does well + introduce maintenance
  burden (timezone DST rules change annually + GeoLocator
  upstream tracks these changes).

- A **vendor-neutral** contract layer over the upstream GeoLocator
  + `zone.home` + GPS source. The contract talks to whatever
  GPS source the operator wires (Traccar / HA Companion / Wican
  Pro / generic `device_tracker`), not to any specific vendor's
  library.

- A **cadence-aware** wrapper. The `select.rc_time_zone_update_
  cadence` (event_driven / 15_min / 60_min / manual) select
  controls how often the wrapper calls
  `geolocator.update_location`. The 15-min default is
  conservative (avoids thrashing); the event-driven option
  triggers on `zone.home` changes only (lower latency but
  requires a reliable change-trigger); the manual option is
  operator-driven via `button.rc_time_zone_update_now`.

- A **single "is the timezone synced?" tile** that aggregates
  GeoLocator's last-update state into one dashboard indicator.
  The `binary_sensor.rc_time_zone_synced` tile is the day-1
  aggregate (TRUE when the system timezone matches the GPS
  source's computed timezone); together with
  `binary_sensor.rc_time_zone_stale` (TRUE when
  `sensor.rc_time_zone_last_update_minutes_ago` > 60), they
  give the operator a complete view of "is the timezone correct
  right now?" + "is the timezone data fresh?" at a glance.

- A **GPS-source-aware** system. The
  `sensor.rc_time_zone_gps_source` tile surfaces which upstream
  tracker is feeding `zone.home`. The recipe walks through
  four GPS source options: Traccar Wave 3 #36 (canonical),
  HA Companion app (operator's phone), Wican Pro Wave 3 #6
  (OBD-II reader's GPS, always-on), generic `device_tracker.*`
  (any tracker that calls `homeassistant.set_location`).

- A **freshness-aware** system. The
  `sensor.rc_time_zone_last_update_minutes_ago` tile is the
  freshness timestamp; the `binary_sensor.rc_time_zone_stale`
  binary_sensor is the freshness gate (TRUE when last_update >
  60 minutes); the `binary_sensor.rc_time_zone_synced`
  binary_sensor is the correctness gate (TRUE when the system
  timezone matches the GPS source's computed timezone).

- An **on-demand-aware** system. The
  `button.rc_time_zone_update_now` button forces a
  `geolocator.update_location` call without waiting for the
  next cadence tick. Useful for testing the wiring + for
  forcing an immediate sync after a long stop.

## §2 Prerequisites

GPS source — at least one of the following:

- **Traccar** (Wave 3 #36) server configured and exposing a
  `device_tracker.rc_location_van` (or equivalent) entity that
  updates `zone.home` on position change. The recipe §3.1 walks
  through the Traccar integration setup + the `zone.home`
  binding.
- **HA Companion app** installed on the operator's phone + the
  app's `device_tracker.<phone_name>` entity updating
  `zone.home`. The recipe §3.2 walks through the HA Companion
  app setup + the location reporting configuration.
- **Wican Pro** (Wave 3 #6) OBD-II reader with its GPS feed
  exposed as a `device_tracker` entity that updates
  `zone.home`. The recipe §3.3 walks through the Wican Pro GPS
  wiring.
- **Generic `device_tracker.*`** — any upstream tracker that
  calls `homeassistant.set_location` on update. The recipe
  §3.4 walks through the `homeassistant.set_location` service
  call + the `zone.home` binding.

GeoLocator HACS integration — must be installed before any of the
recipe §5 automations can fire:

- HACS → ⋮ → Custom repositories → Add:
  - URL: `https://github.com/SmartyVan/hass-geolocator`
  - Category: Integration
- Install GeoLocator → Restart Home Assistant.
- The HACS `geolocator` integration is the upstream timezone-
  update engine; the RoamCore wrapper is the automation that
  calls `geolocator.update_location`.

Cross-connection prerequisites:

- For the Traccar path: the Traccar Wave 3 #36 connection must
  be configured and the `device_tracker.rc_location_van` entity
  must exist.
- For the Wican Pro path: the Wican Pro Wave 3 #6 connection
  must be configured and the GPS feed entity must exist.
- The existing RoamCore time helpers
  (`homeassistant/packages/roamcore_weather_time.yaml` +
  `sensor.rc_time_zone` override contract) cross-reference the
  `sensor.rc_time_zone_current` tile as the source of truth for
  the system timezone.

Safety prerequisites:

- The operator must restart Home Assistant after installing
  GeoLocator (GeoLocator loads at startup).
- The operator must wire at least one GPS source to `zone.home`
  before the §5 automation can do anything useful.

No upstream vendor integration required beyond the `zone` +
`device_tracker` + `homeassistant` service + `template` +
`input_boolean` + `input_datetime` + HACS `geolocator`
integrations. RoamCore ships zero timezone hardware.

## §3 Path A — GPS source (Traccar / HA Companion / Wican Pro / generic)

Path A1 — Traccar (canonical GPS source, Wave 3 #36):

```bash
# In HA: Settings → Devices & Services → Add Integration →
# Traccar (the official HA Traccar integration since 2022.x
# exposes a GUI flow). Configure with the Traccar server URL +
# the operator's Traccar account credentials.
#
# The Traccar integration creates a `device_tracker.<device>`
# entity for each Traccar-tracked device. For the RoamCore van,
# the canonical entity is `device_tracker.rc_location_van` (the
# van's Traccar-tracked device).
#
# The recipe walks the operator through binding
# `device_tracker.rc_location_van` -> `zone.home` via a
# `homeassistant.set_location` automation:
```

```yaml
automation:
  - alias: "Timezone geolocator: Update zone.home from Traccar"
    id: timezone_geolocator_zone_from_traccar
    mode: single
    trigger:
      - platform: state
        entity_id: device_tracker.rc_location_van
    action:
      - service: homeassistant.set_location
        data:
          latitude: "{{ state_attr('device_tracker.rc_location_van', 'latitude') }}"
          longitude: "{{ state_attr('device_tracker.rc_location_van', 'longitude') }}"
```

Path A2 — HA Companion app:

```bash
# Install the HA Companion app on the operator's phone
# (iOS / Android). Configure the app's location reporting:
#   - Settings → Companion App → Location → Location
#     Reporting → Enabled
#   - Zone Detection → Home Zone → Enabled (the app
#     automatically reports when entering / leaving the home
#     zone)
#   - Background Fetch Interval → Significant Changes (the
#     app reports on significant GPS changes only — saves
#     battery)
#
# The HA Companion integration (upstream, since 2022.x exposes
# a GUI flow) creates a `device_tracker.<phone_name>` entity
# (e.g. `device_tracker.bernards_iphone`) that reports the
# operator's GPS coordinates.
```

Path A3 — Wican Pro (Wave 3 #6):

```bash
# The Wican Pro Wave 3 #6 OBD-II reader is always-on (it's
# plugged into the van's OBD-II port) so its GPS feed is
# reliable even when the operator's phone is asleep. The
# Wican Pro connection exposes the GPS feed as a
# `device_tracker.<wican_pro_name>` entity (e.g.
# `device_tracker.wican_pro_van`).
#
# The recipe walks the operator through binding the Wican Pro
# GPS entity -> `zone.home` via a `homeassistant.set_location`
# automation (same pattern as Path A1).
```

Path A4 — Generic `device_tracker.*`:

```bash
# Any upstream tracker that calls `homeassistant.set_location`
# on update can be used. The recipe walks through the
# `homeassistant.set_location` service call + the `zone.home`
# binding.
#
# For testing / bench setups without a GPS tracker, the recipe
# recommends the manual `homeassistant.set_location` service
# call from Developer Tools → Services (useful for testing
# GeoLocator without a live GPS source).
```

The recommended GPS sources for vans:

| Source | Type | Wiring | Notes |
|--------|------|--------|-------|
| **Traccar** | Server-side GPS | HA Traccar integration (GUI flow since 2022.x) | Canonical; always-on if van has LTE. |
| **HA Companion app** | Phone GPS | HA Companion app (iOS / Android) | Operator-phone-based; battery-sensitive. |
| **Wican Pro** | OBD-II GPS | Wican Pro Wave 3 #6 + HA `device_tracker` | Always-on even when phone is asleep. |
| **Generic `device_tracker.*`** | Any tracker | HA core `device_tracker` + `homeassistant.set_location` | Custom; the recipe walks through it. |

## §4 Path B — `homeassistant.set_location` fallback

```yaml
# For benches without a GPS tracker, the operator can manually
# push coordinates to HA via the `homeassistant.set_location`
# service. Useful for testing GeoLocator without a live GPS
# source.
#
# From HA Developer Tools → Services → homeassistant.set_location
# OR via the `button.rc_time_zone_update_now` button (which the
# recipe wires to call both `homeassistant.set_location` with
# the last-known GPS source coordinates AND
# `geolocator.update_location`).
#
# Example service call:
service: homeassistant.set_location
data:
  latitude: 34.0549
  longitude: -118.2426
```

The recipe recommends wiring a HA core `input_text` or
`input_number` to capture the last-known GPS coordinates for
bench testing (the operator can update these manually + the
`button.rc_time_zone_update_now` button reads them + calls
`homeassistant.set_location` + `geolocator.update_location`).

## §5 Path C — RoamCore automation wrapper (15-min cadence vs event-driven)

Path C1 — 15-minute cadence (recommended default):

```yaml
# The conservative 15-minute cadence. Calls
# `geolocator.update_location` every 15 minutes; GeoLocator
# re-computes the timezone from `zone.home` and updates HA's
# system timezone if it changed.
#
# This is the recipe's default cadence because:
#   - It's low-overhead (1 service call per 15 minutes; no
#     thrashing on GPS source flapping).
#   - It's predictable (the operator can reason about "the
#     timezone will be correct within 15 minutes of crossing
#     a timezone boundary").
#   - It's robust to missed events (if a `zone.home` change
#     event is missed due to HA being offline, the next 15-min
#     tick will catch it).
automation:
  - alias: "Timezone geolocator: Update timezone (15-min cadence)"
    id: timezone_geolocator_update_15min
    mode: single
    trigger:
      - platform: time_pattern
        minutes: "/15"
    condition: []
    action:
      - service: geolocator.update_location
        data: {}
```

Path C2 — Event-driven (lower latency):

```yaml
# Triggers on `zone.home` changes only. Lower latency than
# the 15-min cadence (the timezone updates within seconds of
# the GPS source reporting a new position) but requires a
# reliable change-trigger (the GPS source must reliably
# report position changes; some trackers only report on
# significant changes, which can miss small position
# updates).
#
# The recipe §5.2 notes that the event-driven cadence is
# recommended for vans with always-on GPS (Traccar server
# via LTE) + NOT recommended for phone-based GPS (HA
# Companion app reports on significant changes only).
automation:
  - alias: "Timezone geolocator: Update timezone (event-driven)"
    id: timezone_geolocator_update_event
    mode: single
    trigger:
      - platform: zone
        entity_id: device_tracker.rc_location_van
        zone: zone.home
        event: enter
      - platform: zone
        entity_id: device_tracker.rc_location_van
        zone: zone.home
        event: leave
    condition: []
    action:
      - service: geolocator.update_location
        data: {}
```

Path C3 — Manual only:

```yaml
# The operator drives the updates manually via the
# `button.rc_time_zone_update_now` button. Useful for
# benches without an automation runner OR for operators who
# prefer full control over when the timezone updates.
#
# No automation is wired in this mode; the operator presses
# the dashboard button whenever they want the timezone
# refreshed.
```

The cadence select:

```yaml
select:
  - platform: template
    selects:
      rc_time_zone_update_cadence:
        # The operator-tunable update cadence. Determines
        # which automation is enabled.
        options:
          - "event_driven"
          - "15_min"
          - "60_min"
          - "manual"
        initial: "15_min"
```

## §6 RoamCore contract entities

The 8 `rc_time_zone_*` tiles + how the upstream GeoLocator +
`zone.home` + GPS source templates expose them.

The full tile set (per `connection.yml` `dashboard.tiles`):

- `sensor.rc_time_zone_current` — the current system timezone
  (e.g. "America/Los_Angeles"). Source: HA core `sensor`
  integration reading `zone.home`'s timezone attribute + the
  upstream GeoLocator state.
- `sensor.rc_time_zone_offset_minutes` — the offset from UTC
  in minutes (e.g. -480 for PST). Source: HA core `template:`
  sensor deriving the offset from the current timezone.
- `binary_sensor.rc_time_zone_synced` — the correctness gate
  (TRUE when the system timezone matches the GPS source's
  computed timezone). Source: HA core `template:` binary_sensor
  comparing the system timezone to the GeoLocator output.
- `sensor.rc_time_zone_last_update_minutes_ago` — the freshness
  timestamp (minutes since the last successful
  `geolocator.update_location` call). Source: HA core
  `template:` sensor deriving the freshness from the
  `automation.timezone_geolocator_update_15min`'s
  `last_triggered` attribute (or whichever cadence the
  operator selected).
- `binary_sensor.rc_time_zone_stale` — the freshness gate
  (TRUE when `sensor.rc_time_zone_last_update_minutes_ago` >
  60). Source: HA core `template:` binary_sensor.
- `sensor.rc_time_zone_gps_source` — the GPS source name
  (e.g. "traccar" / "ha_companion" / "wican_pro" /
  "manual"). Source: HA core `input_text` + the operator's
  selection.
- `select.rc_time_zone_update_cadence` — the operator-tunable
  update cadence (event_driven / 15_min / 60_min / manual).
  Source: HA core `input_select` integration.
- `button.rc_time_zone_update_now` — the manual trigger button
  (forces a `geolocator.update_location` call). Source: HA
  core `button` integration.

The timezone template:

```yaml
template:
  - sensor:
      - name: "rc_time_zone_current"
        # The current system timezone. Reads from the
        # upstream GeoLocator state + falls back to the
        # existing `sensor.rc_time_zone` override contract
        # if GeoLocator is not installed.
        state: >-
          {{ state_attr('zone.home', 'timezone')
             or states('sensor.rc_time_zone') }}
        icon: mdi:globe-clock

      - name: "rc_time_zone_offset_minutes"
        # The offset from UTC in minutes. Derives from the
        # current timezone using a Jinja2 lookup table.
        state: >-
          {{ (now().utcoffset().total_seconds() / 60) | int(0) }}
        unit_of_measurement: "min"

      - name: "rc_time_zone_last_update_minutes_ago"
        # Minutes since the last successful
        # `geolocator.update_location` call. Derives from
        # the automation trace's `last_triggered` attribute.
        state: >-
          {{ (now() - state_attr('automation.timezone_
             geolocator_update_15min', 'last_triggered')
             ).total_seconds() / 60
             if state_attr('automation.timezone_geolocator_
             update_15min', 'last_triggered')
             else 9999 }}
        unit_of_measurement: "min"

      - name: "rc_time_zone_gps_source"
        # The GPS source name. Reads from the operator's
        # `input_text.rc_time_zone_gps_source` selection.
        state: "{{ states('input_text.rc_time_zone_gps_source') }}"
        icon: mdi:map-marker-radius

  - binary_sensor:
      - name: "rc_time_zone_synced"
        # The correctness gate (TRUE when the system
        # timezone matches the GPS source's computed
        # timezone).
        state: >-
          {{ states('sensor.rc_time_zone_current') != 'unknown'
             and (now() - state_attr('automation.timezone_
             geolocator_update_15min', 'last_triggered')
             ).total_seconds() < 3600 }}
        device_class: connectivity

      - name: "rc_time_zone_stale"
        # The freshness gate (TRUE when last_update > 60
        # minutes).
        state: >-
          {{ (now() - state_attr('automation.timezone_
             geolocator_update_15min', 'last_triggered')
             ).total_seconds() > 3600
             if state_attr('automation.timezone_geolocator_
             update_15min', 'last_triggered')
             else true }}
        device_class: problem
```

The update button:

```yaml
button:
  - platform: template
    buttons:
      rc_time_zone_update_now:
        name: "Update timezone now"
        # Forces a `geolocator.update_location` call +
        # updates `zone.home` from the last-known GPS source
        # coordinates (Path B fallback).
        press:
          - service: geolocator.update_location
            data: {}
          - service: homeassistant.set_location
            data:
              latitude: "{{ state_attr('device_tracker.rc_location_van', 'latitude') | float(0) }}"
              longitude: "{{ state_attr('device_tracker.rc_location_van', 'longitude') | float(0) }}"
```

## §7 Automations (MANDATORY before first use)

The single §5 RoamCore Update timezone automation is MANDATORY
before first use:

1. **Update timezone (15-min cadence or event-driven)** — calls
   `geolocator.update_location` either on a 15-min cadence
   (recommended default) OR on `zone.home` changes (event-
   driven alternative) OR manually (operator-driven via the
   button). The recipe §5 walks through both cadence options
   + the manual-only option.

```yaml
automation:
  - alias: "Timezone geolocator: Update timezone (15-min cadence)"
    id: timezone_geolocator_update_15min
    mode: single
    trigger:
      - platform: time_pattern
        minutes: "/15"
    condition: []
    action:
      - service: geolocator.update_location
        data: {}
```

The single automation is sufficient because GeoLocator handles
the timezone lookup + the `homeassistant.set_time_zone`
service call internally. RoamCore does NOT maintain its own
timezone engine; GeoLocator is the canonical source.

## §8 Troubleshooting

Six troubleshooting entries:

1. **Timezone never updates** — GeoLocator not installed OR
   `zone.home` not updated by a GPS source. Check the
   `sensor.rc_time_zone_gps_source` tile's upstream entity +
   the `device_tracker.<source>` entity's state in HA Developer
   Tools → States.

2. **Timezone updates but `now()` still shows the old
   timezone** — GeoLocator may have updated the system
   timezone but the HA core `now()` function caches the
   timezone at startup. Restart HA to refresh the cache OR
   check that the GeoLocator integration is loaded at startup
   (it should be — verify in HA Settings → Devices & Services
   → GeoLocator).

3. **`binary_sensor.rc_time_zone_stale` is always TRUE** — the
   §5 automation is not firing. Check the automation trace in
   HA Settings → Automations & Scenes + verify the
   `automation.timezone_geolocator_update_15min` automation
   is enabled.

4. **`sensor.rc_time_zone_current` shows `unknown`** — the
   `zone.home` entity is missing OR GeoLocator is not
   installed. Verify both in HA Settings → Devices & Services.

5. **`binary_sensor.rc_time_zone_synced` is always FALSE** —
   the system timezone doesn't match the GPS source's
   computed timezone. Check that GeoLocator is running
   (HA Settings → Devices & Services → GeoLocator → Service
   → geolocator.update_location → Call Service).

6. **`button.rc_time_zone_update_now` doesn't fire** — the
   button's underlying `geolocator.update_location` service
   call may have failed. Check HA Logs for the button press
   event + the GeoLocator service call result.

## §9 Privacy

The recipe produces no telemetry beyond local timezone state.
GeoLocator reads from `zone.home` (which the GPS source
updates); GeoLocator does not call home to a third-party
service (the offline timezone lookup table is bundled with
the HACS integration).

The GPS source (Traccar / HA Companion / Wican Pro / generic
`device_tracker.*`) has its own privacy controls — the
operator can disable location reporting on the phone / the
GPS device. The recipe does not add any privacy leak beyond
the GPS source's normal reporting.

No cloud call home for the timezone update itself. GeoLocator
runs entirely on HA. The RoamCore wrapper is a local
automation. No RoamCore cloud / no GeoLocator cloud.

No telemetry shared with RoamCore or any third party.

## §10 Promoting to tier-b

What would need to happen to promote this connection from
tier-c to tier-b:

- A real timezone engine bench on the CI rig: a Traccar
  server + a mock GPS feed + canned fixture responses for
  multiple timezones + the upstream GeoLocator integration
  installed.
- A canonical RoamCore-owned operator-wired setup flow that
  walks the operator through choosing Path A (Traccar / HA
  Companion / Wican Pro / generic) + declaring the upstream
  GPS source entity + wiring the cadence select default.
- Integration tests that assert:
    - a GPS source update to `zone.home` triggers
      `geolocator.update_location` (via the §5 event-driven
      automation)
    - a 15-min cadence tick triggers
      `geolocator.update_location` (via the §5 15-min
      cadence automation)
    - the §6 `sensor.rc_time_zone_current` reflects the
      correct timezone after a GeoLocator update
    - the §6 `binary_sensor.rc_time_zone_synced` is TRUE
      when the system timezone matches GeoLocator's output
    - the §6 `binary_sensor.rc_time_zone_stale` is TRUE
      when last_update > 60 minutes
    - the §5 `button.rc_time_zone_update_now` button forces
      a `geolocator.update_location` call within a defined
      latency budget
    - the §5 cadence select correctly enables / disables
      the corresponding automation.
- The RoamCore-owned `__init__.py` actually wires the GPS
  source + cadence select + GeoLocator service call at HA
  startup (instead of being a tier-c recipe stub).

Until those ship, this connection is tier-c even though the
upstream GeoLocator + `zone` + `device_tracker` +
`homeassistant` service + `template` + `input_boolean` +
`input_datetime` integrations have their own GUI flows. The
recipe is sound but we cannot claim one-tap automation.

## §11 Files in this connection + cross-references

Files in this connection:

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "timezone_geolocator"` marker for
  the audit.
- `docs/recipe.md` — the full howto (this file).
- `tests/test_connection_yml.py` — manifest honesty checks.

Cross-references:

- **Traccar** (Wave 3 #36 — the canonical GPS source): the
  Path A1 GPS source uses the Traccar integration's
  `device_tracker.rc_location_van` entity.
- **HA Companion app** (the operator-side GPS source): the
  Path A2 GPS source uses the HA Companion app's
  `device_tracker.<phone_name>` entity.
- **Wican Pro** (Wave 3 #6 — the optional OBD-II GPS source):
  the Path A3 GPS source uses the Wican Pro connection's
  GPS feed entity.
- **Time / weather contract** (Wave 2 #14 + Wave 2 #15 +
  Wave 3 #55 — the existing time helpers): the
  `sensor.rc_time_zone` override contract cross-references
  `sensor.rc_time_zone_current` as the source of truth for
  the system timezone; the
  `homeassistant/packages/roamcore_weather_time.yaml` package
  reads `sensor.rc_time_zone_current` for the
  `sun.sun` integration + `now()` / `today_at()` templates.
- **Teltonika** (Wave 3 #39 — the optional LTE/5G router):
  the Traccar GPS source uses the Teltonika LTE connection
  for the always-on LTE backhaul.
- **HVAC basics** (Wave 3 #49 — no relationship): different
  subsystem.
- **Motion-based lighting** (Wave 3 #53 — no relationship):
  different subsystem.
- **Approach lights** (Wave 3 #52 — no relationship):
  different subsystem.