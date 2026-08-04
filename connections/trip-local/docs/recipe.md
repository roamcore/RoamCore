# Trip Local — Recipe (tier-a recipe connection)

This is the install + troubleshooting howto for the RoamCore Trip
Local connection. It complements `../README.md` (the user-facing
IKEA page) with the operator-facing details.

## What this slice ships

This is a tier-a recipe connection — the recipe wraps the
existing RoamCore-owned package at
`homeassistant/packages/roamcore_trip_local.yaml` (73 LOC) and
publishes the recipe layer (manifest + recipe.md + manifest-
honesty smoke + cross-references). The package contents are
PRESERVED VERBATIM by this slice.

The recipe covers everything below:

1. **Connection manifest** (`connections/trip-local/connection.yml`)
2. **Recipe howto** (`connections/trip-local/docs/recipe.md`) —
   this file
3. **User-facing IKEA page** (`connections/trip-local/README.md`)
4. **Tests** (`connections/trip-local/tests/test_connection_yml.py`)
   — manifest honesty smoke
5. **Existing RoamCore-owned package**
   (`homeassistant/packages/roamcore_trip_local.yaml`) — the
   surface this slice WRAPS (referenced verbatim via
   `install.packages:` in the manifest — the package contents
   are NOT redefined)

## What this is

RoamCore's local-first trip metrics path. Today's distance /
drive time / stops computed from the operator's HA recorder
DB — no Traccar, no cloud, no vendor lock-in.

## Why it's useful in a van

- **No cloud dependency** — the recorder DB lives on the
  operator's HA box; the JSON export lives at
  `/config/www/roamcore/trip_local/today.json` on the
  operator's HA box.
- **No vendor lock-in** — works with any upstream
  `device_tracker.*` (Traccar, OwnTracks, HA companion app,
  GPSd, etc.); the upstream device_tracker is just a
  pointer configured via
  `input_text.rc_location_tracker_entity`.
- **Works offline** — the recorder DB is on the operator's
  HA box; the Python script that reads the recorder DB
  runs on the operator's HA box; the JSON export lives on
  the operator's HA box. No cloud round-trip.
- **Vendor-neutral `rc_*` contract surface** — the 3
  `rc_trip_local_today_*` tiles are vendor-neutral (no
  Traccar / OwnTracks / GPX / cloud-route-engine names leak
  into the tile ids).

## Extra hardware required

**None.** The recorder is built into every HA install; the
`command_line:` sensor + `shell_command:` integrations are
built into every HA install; the package is RoamCore-owned
+ RoamCore-shipped; the Python script is RoamCore-owned +
RoamCore-shipped.

## Install / best next step

The 4-step operator flow:

1. **Configure the device_tracker** — operator sets
   `input_text.rc_location_tracker_entity` to their chosen
   `device_tracker.*`.
2. **Wait 15 minutes for the first export** — the
   `automation.rc_trip_local_today_exporter` triggers every
   15 minutes via `time_pattern: minutes: "/15"`. The
   shell command runs
   `python3 /config/tools/trip_local/trip_today.py --entity-id
   {{ states('input_text.rc_location_tracker_entity') }}
   --day today --out-json
   /config/www/roamcore/trip_local/today.json`.
3. **Verify the 3 contract tiles populate** —
   `sensor.rc_trip_local_today_distance_mi` +
   `sensor.rc_trip_local_today_drive_time` +
   `sensor.rc_trip_local_today_stops`.
4. **Optional — install the Map dashboard** — to overlay
   today's route on the map (see
   `connections/map-dashboard/` Wave 3 #66).

## What it does

The surface publishes 3 `rc_trip_local_today_*` contract
tiles:

- `sensor.rc_trip_local_today_distance_mi` — today's
  distance in miles (the recorder-DB-derived distance;
  the recorder's `states` table is the canonical source
  for the operator's `device_tracker.*` history; the
  `python3 /config/tools/trip_local/trip_today.py` script
  reads the recorder DB + emits a JSON to
  `/config/www/roamcore/trip_local/today.json`).
- `sensor.rc_trip_local_today_drive_time` — today's
  drive time in `H:MM` format (the recorder-DB-derived
  total moving-time; the §9.4 drive-time-format-human-
  readable-guard enforces the `H:MM` format and
  prevents the tile from leaking raw seconds into the
  dashboard).
- `sensor.rc_trip_local_today_stops` — today's stop
  count (the recorder-DB-derived count of distinct
  stationary clusters; stops are computed from the
  operator's `device_tracker.*` history; no cloud
  involvement).

The 3 tiles refresh every 15 minutes via the
`automation.rc_trip_local_today_exporter` (the §9.1
local-trip-metrics-export automation).

## §9 MANDATORY automations

The FIVE cross-cutting automations:

1. **§9.1 Local-trip-metrics-export** — the 15-minute
   trigger that's already wired in the package as
   `automation.rc_trip_local_today_exporter`. The
   automation triggers every 15 minutes via
   `time_pattern: minutes: "/15"` + calls
   `shell_command.rc_trip_local_today_export` +
   runs the recorder-DB Python script + emits a JSON
   to `/config/www/roamcore/trip_local/today.json`.
   **The §9.1 automation is the heartbeat of the
   connection — without it, the JSON export never
   refreshes and the 3 tiles stay stale.**

2. **§9.2 Device_tracker_unconfigured_keeps_tiles_unknown**
   — fires when `input_text.rc_location_tracker_entity`
   is `unknown` / `unavailable` / empty. The automation
   resets all 3 tiles to `unknown` rather than
   silently emitting 0 + logs a warning audit entry +
   fires a notification warning the operator that no
   device_tracker is configured. **Without this guard,
   an unconfigured device_tracker would silently emit
   `0.0` for distance + `0:00` for drive_time + `0`
   for stops, which would mislead the operator into
   thinking they've driven nothing today.**

3. **§9.3 Recorder_purge_resets_local_trip_metrics** —
   fires when the recorder purges history older than
   N days (the recorder's `purge_keep_days` integration
   option). The automation resets the 3 trip-today
   tiles to 0 (don't carry over stale values) + logs
   an audit entry. **Without this guard, the tiles
   would carry over stale values from the purged
   history.**

4. **§9.4 Drive_time_format_human_readable_guard** —
   fires when the `rc_trip_local_today_drive_time`
   tile is set. The automation enforces the `H:MM`
   format on the tile value (e.g. `1:23` for 1 hour
   23 minutes) + rejects raw seconds (e.g. `4980`)
   + logs an audit entry if the format is wrong.
   **Without this guard, the tile could leak raw
   seconds into the dashboard, which would be
   unreadable.**

5. **§9.5 No_traccar_required_offline_first_guard** —
   explicitly documents that no Traccar / no cloud is
   required for this connection to work; the surface
   works fully offline from the recorder DB alone.
   The automation logs an audit entry on each tile
   update confirming the surface is local-first (the
   recorder DB is on the operator's HA box; the JSON
   export is on the operator's HA box; no cloud
   round-trip). **This guard is the contract-tier
   promise — it's the §9.5 proof that the trip metric
   surface is vendor-neutral + offline-first.**

## Troubleshooting

### The 3 tiles stay `unknown` forever

- `input_text.rc_location_tracker_entity` is `unknown` /
  `unavailable` / empty. The §9.2 device_tracker
  unconfigured guard is firing correctly.
- Set `input_text.rc_location_tracker_entity` to the
  operator's chosen `device_tracker.*` (typically
  `device_tracker.traccar_van` or a phone-derived
  device_tracker).
- Verify the upstream `device_tracker.*` entity exists
  in Developer Tools → States.

### The distance tile is `0.0` even though the van has moved today

- The recorder DB might not have enough history. Verify
  the recorder is enabled (default ON; check
  Settings → System → Storage).
- The upstream `device_tracker.*` might not have
  emitted any states yet today. Check Developer Tools →
  States → `device_tracker.*` and verify the `latitude`
  + `longitude` attributes are present.
- The `/config/www/roamcore/trip_local/` directory
  might not be writable. Verify the directory exists +
  is writable by the HA process.

### The drive_time tile shows raw seconds instead of `H:MM`

- The §9.4 drive_time_format_human_readable_guard is
  firing. The Python script in the package is emitting
  raw seconds.
- Verify the script at
  `/config/tools/trip_local/trip_today.py` is the
  RoamCore-shipped version (it formats drive_time as
  `H:MM`).
- If the operator modified the script, restore the
  RoamCore-shipped version.

### The stops tile count is wrong

- The recorder DB might not have enough history. Verify
  the recorder is enabled (default ON; check
  Settings → System → Storage).
- The upstream `device_tracker.*` might emit too many
  state changes while parked (e.g. GPS jitter). The
  `trip_today.py` script uses a clustering algorithm to
  detect stationary clusters; GPS jitter can cause
  false-positive stops.

### The 3 tiles show stale data (no refresh in 15 minutes)

- The `automation.rc_trip_local_today_exporter` is not
  running. Verify the automation is enabled in
  Settings → Automations.
- The `/config/tools/trip_local/trip_today.py` script
  might be missing. Verify the file exists + is
  executable.
- The HA `recorder:` integration might be disabled.
  Enable the recorder (Settings → System → Storage).

### The §9.3 recorder_purge_resets_local_trip_metrics guard doesn't fire

- The recorder's `purge_keep_days` integration option
  might be set to `0` (never purge). Verify the option
  is set to a value > 0.
- The §9.3 automation might not be wired. Verify the
  automation exists in Settings → Automations.

## Privacy

- No RoamCore-side telemetry — the recorder DB lives
  on the operator's HA box; the JSON export lives at
  `/config/www/roamcore/trip_local/today.json` on the
  operator's HA box; no cloud round-trip.
- The operator owns the recorder DB + the device_tracker
  + the trip-today JSON.
- The upstream `device_tracker.*` is the operator's
  choice — Traccar / OwnTracks / HA companion app /
  GPSd / etc.

## Tier-a promotion outline

Tier-a is honest because:

- RoamCore ships its own package at
  `homeassistant/packages/roamcore_trip_local.yaml` (73
  LOC) — the package IS the tier-a surface.
- RoamCore ships the recorder-reading Python script at
  `/config/tools/trip_local/trip_today.py` — the script
  is RoamCore-owned + RoamCore-shipped.
- No upstream HA integration covers the recorder-DB-
  derived trip metric surface — RoamCore ships the
  recorder-reading script as part of its tier-a surface.
- The 3 `rc_trip_local_today_*` contract tiles are
  vendor-neutral + offline-first.
- The FIVE §9 MANDATORY automations document the
  cross-cutting guarantees (15-min refresh +
  device_tracker unconfigured guard + recorder purge
  guard + drive-time format guard + offline-first
  guard).

## Files

- `connections/trip-local/connection.yml` — tier-a
  manifest.
- `connections/trip-local/__init__.py` — `DOMAIN =
  "trip_local"` marker.
- `connections/trip-local/README.md` — user-facing
  IKEA page.
- `connections/trip-local/docs/recipe.md` — this file.
- `connections/trip-local/tests/test_connection_yml.py`
  — manifest honesty smoke.
- `homeassistant/packages/roamcore_trip_local.yaml` (73
  LOC, preserved verbatim) — the existing RoamCore-owned
  package that this slice WRAPS.

## Cross-references

- Map dashboard (the optional route-overlay sibling):
  `connections/map-dashboard/` (Wave 3 #66)
- Trip Wrapped (the forward-referenced weekly-summary
  sibling; Wave 3 #69 — will land in a follow-up slice):
  `connections/trip-wrapped/` (planned)
- Mode (the §9.5 offline-first guard's mode-state
  cross-reference): `connections/mode/` (Wave 3 #61)
- Remote-access (the §9.5 offline-first guard's
  offline-first cross-reference):
  `connections/remote-access/` (Wave 3 #58)
- Advanced-mode (the §9.4 drive-time-format guard's
  confirm-flag pattern):
  `connections/advanced-mode/` (Wave 3 #63)
- OpenClaw JSON API (the JSON API surfaces the
  `rc_trip_local_today_*` tiles):
  `connections/openclaw-api/` (Wave 3 #64)
- Leveling (the §9.5 offline-first guard's leveling-
  jack cross-reference): `connections/leveling/`
  (Wave 3 #60)
- RoamCore entity naming:
  `docs/reference/rc-entity-naming.md` (the `trip`
  subsystem was added by this slice)