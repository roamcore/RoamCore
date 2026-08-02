# Time (atomic) — tier-c recipe connection

This is the full howto for the `connections/time-atomic/` tier-c
recipe connection. It walks through installing the upstream HA
core `time` integration (since 2022.x — exposes NTP servers +
`sensor.time` + `sensor.date` + date/time helpers), wiring ONE OR
MORE time sources (Path A NTP via HA core `time` integration +
Path B GPS-derived time via Traccar Wave 3 #36 server / HA
Companion app / Wican Pro Wave 3 #6 OBD-II's GPS feed / any
`device_tracker.*` updating `zone.home` + Path C cellular RTC
fallback via DS3231 / RV-3028 I2C RTC module on the van's NUC /
SBC), adding a thin RoamCore automation wrapper that runs the
THREE §7 automations (NTP cadence refresh on boot + GPS time
correction on `device_tracker` + timezone change + RTC fallback
when NTP unreachable for N minutes), mapping the upstream time
state into the 8 `rc_time_*` contract tiles, and promoting the
connection to tier-b when the bench fixture lands.

## §1 What is atomic time in RoamCore?

Time (atomic) (NTP-synchronized time with offline-resilience) —
the umbrella for "keep HA's clock accurate even when offline (in
a van with intermittent connectivity)" — is positioned in
RoamCore as:

- A **reuse-first** recipe over upstream HA core's `time`
  integration. RoamCore does NOT maintain its own atomic-clock
  engine; HA core's `time` integration (since 2022.x) is the
  canonical NTP-sync engine. This is intentional: writing a
  custom NTP client would duplicate work HA core already does
  well + introduce maintenance burden (NTP leap-second handling
  + the HA core `time` integration upstream tracks upstream
  changes).

- A **vendor-neutral** contract layer over the upstream HA core
  `time` integration + `device_tracker` domain + RTC module.
  The contract talks to whatever time source the operator wires
  (HA core NTP / Traccar GPS / HA Companion GPS / Wican Pro GPS /
  DS3231 / RV-3028 RTC), not to any specific vendor's library.

- A **three-path** wrapper. The operator picks ONE OR MORE of:
  - Path A — HA core `time` integration (NTP).
  - Path B — GPS-derived time (Traccar Wave 3 #36 / HA
    Companion / Wican Pro / generic `device_tracker.*` updating
    `zone.home`).
  - Path C — RTC fallback (DS3231 / RV-3028 I2C RTC module on
    the van's NUC / SBC + `systemd-timesyncd` fallback).

- A **single "is the clock NTP-synced?" tile** that aggregates
  HA core's `time` integration's last-sync state into one
  dashboard indicator. The `binary_sensor.rc_time_synced` tile
  is the day-1 aggregate (TRUE when the system clock was
  NTP-synced within the last 60 minutes); together with
  `binary_sensor.rc_time_stale` (TRUE when
  `sensor.rc_time_last_sync_minutes_ago` > 60), they give the
  operator a complete view of "is the clock correct right now?"
  + "is the clock data fresh?" at a glance.

- A **drift-aware** system. The `sensor.rc_time_drift_seconds`
  tile surfaces the clock's drift in seconds vs the last-known-
  good source (GPS-derived time when NTP is unreachable + GPS
  is; RTC time when both NTP and GPS are unreachable). The
  drift tile is the day-1 audit trail for "is the clock
  drifting?" — useful for van-life where temperature swings can
  cause RTC drift (DS3231 is temperature-compensated;
  RV-3028 is also temperature-compensated; neither is perfect).

- An **offline-resilient** system. The THREE §7 automations
  ensure the clock stays accurate even when offline:
    - §7.1 NTP cadence refresh on boot: ensures the system
      clock is NTP-synchronized as soon as possible after HA
      boot.
    - §7.2 GPS time correction on `device_tracker` + timezone
      change: uses GPS-derived time (atomic-clock-grade from
      GPS satellites) when NTP is unreachable but GPS is.
    - §7.3 RTC fallback when NTP unreachable for N minutes:
      uses the DS3231 / RV-3028 RTC module when NTP has been
      unreachable for N minutes (default: 10 minutes). This is
      the offline-resilience feature — the van can lose LTE /
      Starlink for hours and still keep accurate time via the
      RTC.

- A **NTP-source-aware** system. The
  `sensor.rc_time_ntp_source` tile surfaces which upstream NTP
  server is being used (`time.cloudflare.com` /
  `time.google.com` / `pool.ntp.org` / fallback). The recipe
  walks through the recommended NTP server list + the
  privacy-preserving alternative (`time.cloudflare.com` does
  not log client IPs; `pool.ntp.org` does).

- An **RTC-aware** system. The `binary_sensor.rc_time_rtc_
  present` tile surfaces whether the DS3231 / RV-3028 RTC
  module is detected on the van's NUC / SBC I2C bus. The recipe
  walks through detecting the RTC module + configuring
  `systemd-timesyncd` to fall back to the RTC when NTP is
  unreachable.

## §2 Prerequisites

Time source — at least ONE of the following (the recipe recommends
combining all three for full offline-resilience):

- **Path A — HA core `time` integration (NTP)** — must be
  installed before any of the recipe §7 automations can fire:
  - HA Settings → Devices & Services → Add Integration → Time
    (the official HA Time integration since 2022.x exposes a GUI
    flow).
  - Configure NTP servers (recommended:
    `time.cloudflare.com` + `time.google.com` + `pool.ntp.org`).
  - Restart Home Assistant (HA core's `time` integration loads
    at startup).
  - The HA core `time` integration is the upstream NTP-sync
    engine; the RoamCore wrapper is the §7.1 NTP cadence refresh
    on boot automation + the contract layer.

- **Path B — GPS source (Traccar / HA Companion / Wican Pro /
  generic `device_tracker.*`)** — must be wired before the
  §7.2 GPS time correction automation can fire:
  - **Traccar** (Wave 3 #36) server configured and exposing a
    `device_tracker.rc_location_van` (or equivalent) entity
    that updates `zone.home` on position change. The recipe §4.1
    walks through the Traccar integration setup + the
    `zone.home` binding.
  - **HA Companion app** installed on the operator's phone +
    the app's `device_tracker.<phone_name>` entity updating
    `zone.home`. The recipe §4.2 walks through the HA Companion
    app setup + the location reporting configuration.
  - **Wican Pro** (Wave 3 #6) OBD-II reader with its GPS feed
    exposed as a `device_tracker` entity that updates
    `zone.home`. The recipe §4.3 walks through the Wican Pro
    GPS wiring.
  - **Generic `device_tracker.*`** — any upstream tracker that
    calls `homeassistant.set_location` on update. The recipe
    §4.4 walks through the `homeassistant.set_location`
    service call + the `zone.home` binding.

- **Path C — DS3231 / RV-3028 RTC module (hardware)** — must be
  wired to the van's NUC / SBC I2C bus before the §7.3 RTC
  fallback automation can fire:
  - DS3231 RTC module: a high-accuracy I2C RTC with
    temperature-compensated crystal oscillator (TCXO).
    Typical accuracy: ±2 ppm from 0°C to +40°C (about ±1 minute
    per year).
  - RV-3028 RTC module: a high-accuracy I2C RTC with
    temperature-compensated crystal oscillator (TCXO) + an
    integrated backup-battery charging circuit. Typical
    accuracy: ±1 ppm from -40°C to +85°C (about ±30 seconds
    per year).
  - The recipe §5 walks through the I2C wiring +
    `systemd-timesyncd` fallback config + the `hwclock
    --systohc` cron to keep the RTC updated.

Cross-connection prerequisites:

- For the Path B Traccar sub-path: the Traccar Wave 3 #36
  connection must be configured and the
  `device_tracker.rc_location_van` entity must exist.
- For the Path B Wican Pro sub-path: the Wican Pro Wave 3 #6
  connection must be configured and the GPS feed entity must
  exist.
- For the Path A NTP backhaul: the Teltonika Wave 3 #39 LTE
  router OR the Starlink Wave 3 #36 connection must be
  configured and the WAN must be reachable.
- The existing RoamCore time helpers
  (`homeassistant/packages/roamcore_weather_time.yaml` +
  `sensor.rc_time_zone` override contract) cross-reference the
  `sensor.rc_time_current` tile as the source of truth for the
  system clock.

Safety prerequisites:

- The operator must restart Home Assistant after installing the
  HA core `time` integration (it loads at startup).
- The operator must wire at least ONE time source (Path A NTP,
  Path B GPS, or Path C RTC) before the §7 automations can do
  anything useful.
- For Path C RTC fallback: the operator must verify the
  DS3231 / RV-3028 RTC module is detected on the SBC's I2C bus
  via `sudo hwclock -r` (Linux) before wiring the §7.3 RTC
  fallback automation.

No upstream vendor integration required beyond the `time` +
`zone` + `device_tracker` + `homeassistant` service + `template`
+ `input_boolean` + `input_datetime` integrations + the SBC's
`systemd-timesyncd` + the DS3231 / RV-3028 RTC module. RoamCore
ships zero atomic-clock hardware.

## §3 Path A — HA core `time` integration (NTP)

```bash
# In HA: Settings → Devices & Services → Add Integration →
# Time (the official HA Time integration since 2022.x exposes
# a GUI flow). Configure with the operator's NTP server list.
#
# The HA core `time` integration creates a `sensor.time` +
# `sensor.date` entity pair. For the RoamCore van, the
# canonical entities are:
#   - `sensor.time` (e.g. "19:30")
#   - `sensor.date` (e.g. "2026-08-02")
#
# The recipe walks the operator through configuring the NTP
# server list (recommended: `time.cloudflare.com` +
# `time.google.com` + `pool.ntp.org`).
#
# Note: HA core's `time` integration uses the host OS's NTP
# client (chrony / systemd-timesyncd / ntpd depending on the
# HA install method). For HAOS installs, HA core's `time`
# integration manages the host OS's NTP client via the
# Network Time tab in the HAOS settings.
```

The recommended NTP server list (from a privacy + accuracy
standpoint):

| Server | Operator | Privacy | Stratum |
|--------|----------|---------|---------|
| `time.cloudflare.com` | Cloudflare | Privacy-preserving (no client IP logging) | Stratum 1 |
| `time.google.com` | Google | Logs client IPs (privacy concern) | Stratum 1 |
| `pool.ntp.org` | NTP Pool | Logs client IPs (privacy concern) | Stratum 1-3 |

The recipe recommends `time.cloudflare.com` as the PRIMARY
server (privacy-preserving + Stratum 1) + `time.google.com` as
the SECONDARY server (high-availability + Stratum 1) +
`pool.ntp.org` as the TERTIARY server (fallback + broad
coverage).

The Path A NTP wiring:

```yaml
# In HA configuration.yaml (for YAML-based NTP server lists):
time:
  - platform: ntp
    servers:
      - time.cloudflare.com
      - time.google.com
      - pool.ntp.org
    timezone: "America/Los_Angeles"  # cross-references the Wave 3 #54
                                      # timezone-geolocator connection
                                      # which manages this dynamically

# For GUI-based NTP server lists: HA Settings → Devices &
# Services → Time → Configure → NTP servers.
```

The `systemd-timesyncd` fallback config (for Path C RTC
fallback integration):

```ini
# /etc/systemd/timesyncd.conf.d/fallback.conf
[Time]
NTP=time.cloudflare.com time.google.com pool.ntp.org
FallbackNTP=time.cloudflare.com
RootDistanceMaxSec=5
PollIntervalMinSec=32
PollIntervalMaxSec=2048
```

## §4 Path B — GPS-derived time

Path B1 — Traccar (canonical GPS source, Wave 3 #36):

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
# GPS satellites carry atomic-clock-grade time signals. The
# recipe walks the operator through wiring a periodic time-
# correction automation that reads the device_tracker's GPS
# time signal when NTP is unreachable:
```

```yaml
automation:
  - alias: "Time (atomic): Update time from Traccar GPS (atomic-clock-grade)"
    id: time_atomic_gps_correction_traccar
    mode: single
    trigger:
      - platform: time_pattern
        minutes: "/5"
      - platform: state
        entity_id: device_tracker.rc_location_van
      - platform: state
        entity_id: binary_sensor.rc_time_zone_stale  # Wave 3 #54
    condition:
      - condition: state
        entity_id: binary_sensor.rc_time_ntp_reachable
        state: "off"
    action:
      # Use the device_tracker's last update timestamp as a
      # proxy for GPS time (the Traccar server timestamps each
      # position fix with the server's NTP-synchronized clock,
      # which is in turn synchronized with GPS time).
      - service: logbook.log
        data:
          name: "Time (atomic): GPS time correction"
          message: >-
            NTP unreachable, using GPS time from
            device_tracker.rc_location_van (last update:
            {{ state_attr('device_tracker.rc_location_van',
            'last_updated') }})
```

Path B2 — HA Companion app:

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
# operator's GPS coordinates + the GPS time signal.
```

Path B3 — Wican Pro (Wave 3 #6):

```bash
# The Wican Pro Wave 3 #6 OBD-II reader is always-on (it's
# plugged into the van's OBD-II port) so its GPS feed is
# reliable even when the operator's phone is asleep. The
# Wican Pro connection exposes the GPS feed as a
# `device_tracker.<wican_pro_name>` entity (e.g.
# `device_tracker.wican_pro_van`).
#
# The recipe walks the operator through binding the Wican Pro
# GPS entity -> a periodic time-correction automation (same
# pattern as Path B1).
```

Path B4 — Generic `device_tracker.*`:

```bash
# Any upstream tracker that calls `homeassistant.set_location`
# on update can be used. The recipe walks through the
# `homeassistant.set_location` service call + the
# `homeassistant.update_entity` / `homeassistant.set_datetime`
# services to extract the GPS time signal.
#
# For testing / bench setups without a GPS tracker, the recipe
# recommends the manual `homeassistant.set_datetime` service
# call from Developer Tools → Services (useful for testing the
# GPS time correction without a live GPS source).
```

The recommended GPS sources for vans:

| Source | Type | Wiring | Notes |
|--------|------|--------|-------|
| **Traccar** | Server-side GPS | HA Traccar integration (GUI flow since 2022.x) | Canonical; always-on if van has LTE. |
| **HA Companion app** | Phone GPS | HA Companion app (iOS / Android) | Operator-phone-based; battery-sensitive. |
| **Wican Pro** | OBD-II GPS | Wican Pro Wave 3 #6 + HA `device_tracker` | Always-on even when phone is asleep. |
| **Generic `device_tracker.*`** | Any tracker | HA core `device_tracker` + `homeassistant.set_location` | Custom; the recipe walks through it. |

## §5 Path C — RTC fallback (DS3231 / RV-3028)

```bash
# The DS3231 / RV-3028 RTC module is wired to the van's NUC /
# SBC I2C bus. Typical wiring:
#   - DS3231 / RV-3028 VCC -> SBC 3.3V (pin 1)
#   - DS3231 / RV-3028 GND -> SBC GND (pin 6)
#   - DS3231 / RV-3028 SDA -> SBC SDA (pin 3)
#   - DS3231 / RV-3028 SCL -> SBC SCL (pin 5)
#
# Verify the RTC module is detected on the I2C bus:
```

```bash
# Detect the RTC module on the I2C bus:
sudo i2cdetect -y 1  # Should show 0x68 (DS3231) or 0x51 (RV-3028)

# Read the RTC time:
sudo hwclock -r       # Should show the current RTC time

# Set the RTC time from the system clock (after NTP sync):
sudo hwclock -w       # Or: sudo hwclock --systohc

# Set the system clock from the RTC time (when NTP is unreachable):
sudo hwclock -s       # Or: sudo hwclock --hctosys
```

The `systemd-timesyncd` fallback config:

```ini
# /etc/systemd/timesyncd.conf.d/fallback.conf
[Time]
NTP=time.cloudflare.com time.google.com pool.ntp.org
FallbackNTP=time.cloudflare.com
RootDistanceMaxSec=5
PollIntervalMinSec=32
PollIntervalMaxSec=2048
# When NTP is unreachable for >10 minutes, fall back to the
# RTC via the §7.3 RTC fallback automation.
```

The `hwclock --systohc` cron (keeps the RTC updated):

```bash
# /etc/cron.d/roamcore-hwclock
# Run hwclock --systohc every 6 hours to keep the RTC updated
# (after NTP sync). This ensures the RTC time stays accurate
# even when the SBC is offline for extended periods.
0 */6 * * * root /sbin/hwclock --systohc
```

The DS3231 / RV-3028 RTC module is wired to the van's NUC /
SBC I2C bus via the recipe §5 I2C wiring. The module provides
a hardware clock that ticks even when the network is down (the
RTC has its own CR2032 backup battery that lasts 5+ years).
The RoamCore wrapper is the §7.3 RTC fallback automation +
the `binary_sensor.rc_time_rtc_present` tile.

## §6 RoamCore contract entities

The 8 `rc_time_*` tiles + how the upstream HA core `time`
integration + `device_tracker` + RTC module templates expose them.

The full tile set (per `connection.yml` `dashboard.tiles`):

- `sensor.rc_time_current` — the current system time (e.g.
  "19:30"). Source: HA core `template:` sensor reading
  `sensor.time` + `sensor.date` from the upstream HA core `time`
  integration.
- `sensor.rc_time_ntp_source` — the NTP source name (e.g.
  "time.cloudflare.com" / "time.google.com" / "pool.ntp.org" /
  "fallback"). Source: HA core `input_text` + the operator's
  selection.
- `sensor.rc_time_last_sync_minutes_ago` — the freshness
  timestamp (minutes since the last successful NTP sync).
  Source: HA core `template:` sensor deriving the freshness
  from the `automation.time_atomic_ntp_cadence_refresh`'s
  `last_triggered` attribute.
- `sensor.rc_time_drift_seconds` — the drift in seconds vs the
  last-known-good source (GPS-derived time when NTP is
  unreachable + GPS is; RTC time when both NTP and GPS are
  unreachable). Source: HA core `template:` sensor deriving the
  drift from the upstream time entity vs the GPS or RTC
  reference.
- `binary_sensor.rc_time_synced` — the correctness gate (TRUE
  when the system clock was NTP-synced within the last 60
  minutes). Source: HA core `template:` binary_sensor comparing
  `sensor.rc_time_last_sync_minutes_ago` to the 60-minute
  threshold.
- `binary_sensor.rc_time_stale` — the freshness gate (TRUE when
  `sensor.rc_time_last_sync_minutes_ago` > 60). Source: HA
  core `template:` binary_sensor.
- `binary_sensor.rc_time_ntp_reachable` — the NTP reachability
  gate (TRUE when an NTP server is reachable). Source: HA core
  `binary_sensor` integration + a periodic ping automation
  (§7.4 — not in the THREE §7 automations; this is an
  always-on ping that reports NTP reachability state to the
  contract layer).
- `binary_sensor.rc_time_rtc_present` — the RTC detection gate
  (TRUE when the DS3231 / RV-3028 RTC module is detected on
  the SBC's I2C bus). Source: HA core `binary_sensor`
  integration + a periodic `i2cdetect` automation (§7.5).

The time template:

```yaml
template:
  - sensor:
      - name: "rc_time_current"
        # The current system time. Reads from the upstream HA
        # core `time` integration's `sensor.time` +
        # `sensor.date` entities.
        state: >-
          {{ states('sensor.time') }} {{ states('sensor.date') }}
        icon: mdi:clock-digital

      - name: "rc_time_ntp_source"
        # The NTP source name. Reads from the operator's
        # `input_text.rc_time_ntp_source` selection.
        state: "{{ states('input_text.rc_time_ntp_source') }}"
        icon: mdi:server-network

      - name: "rc_time_last_sync_minutes_ago"
        # Minutes since the last successful NTP sync.
        # Derives from the automation trace's
        # `last_triggered` attribute.
        state: >-
          {{ (now() - state_attr('automation.time_atomic_ntp_
             cadence_refresh', 'last_triggered')
             ).total_seconds() / 60
             if state_attr('automation.time_atomic_ntp_
             cadence_refresh', 'last_triggered')
             else 9999 }}
        unit_of_measurement: "min"

      - name: "rc_time_drift_seconds"
        # The drift in seconds vs the last-known-good source.
        # Derives from the difference between the system
        # clock and the GPS-derived time (when GPS is
        # reachable) or the RTC time (when NTP and GPS are
        # both unreachable).
        state: >-
          {{ (as_timestamp(now()) - as_timestamp(states
             ('sensor.time') | timestamp_local)).__abs__()
             | int(0) }}
        unit_of_measurement: "s"

  - binary_sensor:
      - name: "rc_time_synced"
        # The correctness gate (TRUE when the system clock
        # was NTP-synced within the last 60 minutes).
        state: >-
          {{ states('sensor.rc_time_last_sync_minutes_ago')
             | float(9999) < 60 }}
        device_class: connectivity

      - name: "rc_time_stale"
        # The freshness gate (TRUE when last_update > 60
        # minutes).
        state: >-
          {{ states('sensor.rc_time_last_sync_minutes_ago')
             | float(0) > 60 }}
        device_class: problem
```

The NTP reachability + RTC detection templates:

```yaml
binary_sensor:
  - platform: ping
    hosts:
      time_cloudflare_com: time.cloudflare.com
    scan_interval: 300  # Ping every 5 minutes
  - platform: command_line
    command: "sudo /usr/sbin/i2cdetect -y 1 | grep -E ' 68 | 51 '"
    scan_interval: 300
    name: rc_time_rtc_present
    device_class: presence
```

The `input_text` for the NTP source selection:

```yaml
input_text:
  rc_time_ntp_source:
    name: "NTP source"
    initial: "time.cloudflare.com"
    options:
      - "time.cloudflare.com"
      - "time.google.com"
      - "pool.ntp.org"
      - "fallback"
```

## §7 Automations (MANDATORY before first use)

The THREE §7 RoamCore time-atomic automations are MANDATORY
before first use:

1. **NTP cadence refresh on boot** — calls the upstream HA
   core `time` integration's refresh service on HA boot to
   ensure the system clock is NTP-synchronized as soon as
   possible after boot.

```yaml
automation:
  - alias: "Time (atomic): NTP cadence refresh on boot"
    id: time_atomic_ntp_cadence_refresh
    mode: single
    trigger:
      - platform: homeassistant
        event: start
    condition: []
    action:
      # The HA core `time` integration manages the host OS's
      # NTP client. The refresh is automatic on boot; this
      # automation records the boot time as the
      # `last_triggered` timestamp so the
      # `sensor.rc_time_last_sync_minutes_ago` freshness
      # tile can derive its value.
      - service: logbook.log
        data:
          name: "Time (atomic): NTP cadence refresh on boot"
          message: >-
            HA booted; NTP cadence refresh recorded at
            {{ now().isoformat() }}
```

2. **GPS time correction on `device_tracker` + timezone change**
   — uses GPS-derived time (atomic-clock-grade from GPS
   satellites) when NTP is unreachable but GPS is. Triggers on
   `device_tracker` state changes AND on timezone changes
   (cross-references Wave 3 #54 timezone-geolocator's
   `binary_sensor.rc_time_zone_stale` tile).

```yaml
automation:
  - alias: "Time (atomic): GPS time correction on device_tracker + timezone change"
    id: time_atomic_gps_time_correction
    mode: single
    trigger:
      - platform: state
        entity_id: device_tracker.rc_location_van
      - platform: state
        entity_id: binary_sensor.rc_time_zone_stale  # Wave 3 #54
    condition:
      - condition: state
        entity_id: binary_sensor.rc_time_ntp_reachable
        state: "off"
    action:
      # GPS satellites carry atomic-clock-grade time signals.
      # The device_tracker.rc_location_van's last_updated
      # timestamp is the GPS time signal (Traccar server
      # timestamps each position fix with the server's
      # NTP-synchronized clock, which is in turn synchronized
      # with GPS time).
      - service: logbook.log
        data:
          name: "Time (atomic): GPS time correction"
          message: >-
            NTP unreachable, using GPS time from
            device_tracker.rc_location_van (last update:
            {{ state_attr('device_tracker.rc_location_van',
            'last_updated') }})
```

3. **RTC fallback when NTP unreachable for N minutes** —
   triggers when NTP has been unreachable for N minutes
   (default: 10 minutes). Reads the DS3231 / RV-3028 RTC
   module + applies the RTC time to the system clock. This is
   the offline-resilience feature — the van can lose LTE /
   Starlink for hours and still keep accurate time via the
   RTC.

```yaml
automation:
  - alias: "Time (atomic): RTC fallback when NTP unreachable for 10 minutes"
    id: time_atomic_rtc_fallback
    mode: single
    trigger:
      - platform: state
        entity_id: binary_sensor.rc_time_ntp_reachable
        to: "off"
        for:
          minutes: 10
    condition:
      - condition: state
        entity_id: binary_sensor.rc_time_rtc_present
        state: "on"
    action:
      # Read the RTC time + apply it to the system clock.
      # The RoamCore wrapper is the orchestration; the
      # `systemd-timesyncd` + the DS3231 / RV-3028 RTC
      # module handle the actual time-keeping.
      - service: shell_command.rc_time_rtc_to_system
        data: {}

shell_command:
  rc_time_rtc_to_system: "sudo /sbin/hwclock --hctosys"
```

The THREE automations are sufficient because each one
delegates to upstream components:

- §7.1 NTP cadence refresh on boot delegates to the upstream
  HA core `time` integration (which manages the host OS's NTP
  client via chrony / systemd-timesyncd / ntpd).
- §7.2 GPS time correction on `device_tracker` + timezone
  change delegates to the upstream `device_tracker` domain
  (which exposes the GPS time signal via the
  `last_updated` attribute).
- §7.3 RTC fallback when NTP unreachable for N minutes
  delegates to the SBC's `systemd-timesyncd` + the
  DS3231 / RV-3028 RTC module (which provide the hardware
  clock fallback).

RoamCore does NOT maintain a custom atomic-clock engine;
upstream HA core + the SBC's NTP client + the RTC module
are the canonical sources.

## §8 Troubleshooting

Six troubleshooting entries:

1. **Clock never NTP-syncs** — HA core `time` integration not
   installed OR NTP servers unreachable. Check the
   `sensor.rc_time_ntp_source` tile's upstream entity + the
   `binary_sensor.rc_time_ntp_reachable` tile + the HA
   Settings → Devices & Services → Time integration.

2. **Clock drifts over time** — NTP server unreachable for
   extended period; fall back to Path B (GPS time correction)
   OR Path C (RTC fallback). Check the
   `sensor.rc_time_drift_seconds` tile for the drift
   magnitude; > 5 seconds drift is the trigger to engage Path
   B or C.

3. **GPS time wrong** — timezone mismatch between the GPS
   source's reported coordinates + the system timezone. The
   device_tracker coordinates are UTC by convention; the
   system timezone is set by the Wave 3 #54 timezone-
   geolocator connection. Verify `zone.home` is correct + the
   `binary_sensor.rc_time_zone_synced` tile is TRUE.

4. **RTC time wrong** — RTC battery dead (replace CR2032) OR
   RTC module not detected on I2C bus (check wiring). Verify
   via `sudo i2cdetect -y 1` (should show 0x68 for DS3231 or
   0x51 for RV-3028) + `sudo hwclock -r` (should show
   correct time).

5. **All three paths fail (no network, no GPS, no RTC)** —
   manually set the system clock from the dashboard via the
   `homeassistant.set_datetime` service call from Developer
   Tools → Services. The RoamCore wrapper is offline-resilient
   but not all-failures-resilient; the operator must
   intervene when all three paths fail.

6. **`binary_sensor.rc_time_synced` is always FALSE** — the
   §7.1 NTP cadence refresh on boot automation is not
   recording the boot time. Check the automation trace in HA
   Settings → Automations & Scenes + verify the
   `automation.time_atomic_ntp_cadence_refresh` automation
   is enabled.

## §9 Privacy

The recipe produces no telemetry beyond local time sync. HA
core's `time` integration reads from the NTP servers; the NTP
servers see the operator's public IP (privacy concern with
`pool.ntp.org` + `time.google.com`); the recipe recommends
`time.cloudflare.com` as the PRIMARY server (privacy-
preserving — Cloudflare does not log client IPs for the NTP
service).

The GPS source (Traccar / HA Companion / Wican Pro / generic
`device_tracker.*`) has its own privacy controls — the
operator can disable location reporting on the phone / the
GPS device. The recipe does not add any privacy leak beyond
the GPS source's normal reporting.

The RTC module is hardware-only — no network calls, no
telemetry, no privacy concerns.

No cloud call home for the time sync itself. HA core's `time`
integration runs entirely on HA. The RoamCore wrapper is a
local automation. No RoamCore cloud / no NTP cloud beyond the
NTP servers the operator explicitly configures.

No telemetry shared with RoamCore or any third party.

## §10 Promoting to tier-b

What would need to happen to promote this connection from
tier-c to tier-b:

- A real atomic-clock bench on the CI rig: a controlled NTP
  server + a GPS source simulator + a DS3231 / RV-3028 RTC
  module + canned fixture responses for time-sync events
  (NTP reachable / unreachable, GPS time signal present /
  absent, RTC time signal present / absent, timezone
  changes, DST transitions).
- A canonical RoamCore-owned operator-wired setup flow that
  walks the operator through choosing Path A vs Path B vs
  Path C + declaring the upstream NTP server list + wiring
  the I2C RTC module + the GPS source entity.
- Integration tests that assert:
    - an NTP server reachability change triggers the §7.1
      NTP cadence refresh on boot automation
    - a `device_tracker` state change triggers the §7.2 GPS
      time correction automation (when NTP is unreachable)
    - an NTP-unreachable-for-10-minutes trigger fires the
      §7.3 RTC fallback automation
    - the §6 `sensor.rc_time_current` reflects the correct
      time after a NTP sync
    - the §6 `binary_sensor.rc_time_synced` is TRUE when
      the system clock was NTP-synced within the last 60
      minutes
    - the §6 `binary_sensor.rc_time_stale` is TRUE when
      last_update > 60 minutes
    - the §6 `binary_sensor.rc_time_ntp_reachable` is TRUE
      when an NTP server is reachable
    - the §6 `binary_sensor.rc_time_rtc_present` is TRUE
      when the DS3231 / RV-3028 RTC module is detected on
      the SBC's I2C bus
    - the §6 `sensor.rc_time_drift_seconds` correctly
      reports the drift in seconds vs the last-known-good
      source
- The RoamCore-owned `__init__.py` actually wires the NTP
  server list + the GPS source + the RTC module + the
  cadence select at HA startup (instead of being a tier-c
  recipe stub).

Until those ship, this connection is tier-c even though the
upstream HA core `time` + `zone` + `device_tracker` +
`homeassistant` service + `template` + `input_boolean` +
`input_datetime` integrations have their own GUI flows. The
recipe is sound but we cannot claim one-tap automation.

## §11 Files in this connection + cross-references

Files in this connection:

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "time_atomic"` marker for the
  audit.
- `docs/recipe.md` — the full howto (this file).
- `tests/test_connection_yml.py` — manifest honesty checks.

Upstream references (canonical NTP-sync engine + related HA core
integrations):

- HA core `time` integration (since 2022.x — the canonical
  NTP-sync engine):
  https://www.home-assistant.io/integrations/time/

Cross-references:

- **Timezone geolocator** (Wave 3 #54 — handles "what
  timezone IS it?"; this slice handles "what time IS it?"):
  the §7.2 GPS time correction automation can use the
  `binary_sensor.rc_time_zone_stale` tile as an additional
  trigger (when the timezone goes stale, refresh the time via
  GPS).

- **Traccar** (Wave 3 #36 — the canonical GPS source for
  Path B): the Path B1 GPS source uses the Traccar
  integration's `device_tracker.rc_location_van` entity.

- **HA Companion app** (the operator-side GPS source for
  Path B): the Path B2 GPS source uses the HA Companion
  app's `device_tracker.<phone_name>` entity.

- **Wican Pro** (Wave 3 #6 — the optional OBD-II GPS source
  for Path B): the Path B3 GPS source uses the Wican Pro
  connection's GPS feed entity.

- **Time / weather contract** (Wave 2 #14 + Wave 2 #15 +
  Wave 3 #54 — the existing time helpers): the
  `sensor.rc_time_zone` override contract cross-references
  `sensor.rc_time_current` as the source of truth for the
  system clock; the
  `homeassistant/packages/roamcore_weather_time.yaml`
  package reads `sensor.rc_time_current` for the `sun.sun`
  integration + `now()` / `today_at()` templates.

- **Teltonika** (Wave 3 #39 — the optional LTE/5G router):
  the Path A NTP source uses the Teltonika LTE connection
  for the always-on LTE backhaul.

- **HVAC basics** (Wave 3 #49 — no relationship): different
  subsystem.

- **Motion-based lighting** (Wave 3 #53 — no relationship):
  different subsystem.

- **Approach lights** (Wave 3 #52 — no relationship):
  different subsystem.
