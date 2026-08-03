# WiCAN Pro (OBD2 telemetry)

**Tier:** A (native integration)
**Category:** Connectivity
**Status:** beta

## What this connection is

A small OBD2 reader that plugs into your vehicle's diagnostic port and
reports engine telemetry over Wi-Fi. RoamCore auto-discovers it,
connects to it, populates the dashboard, and records every reading
into a local time-series database.

This is a **plug-and-play** integration — once you've installed
RoamCore, you never have to touch the config flow again. Plug in the
WiCAN Pro, wait ~10 seconds for it to join Wi-Fi, and the dashboard
tiles appear by themselves.

## What it gives you

- **Live engine telemetry** — RPM, speed, coolant temperature,
  throttle position, mass air flow, fuel level, battery voltage,
  ambient air temperature, fuel rate, timing advance, fuel trim,
  engine load, run time, and more.
- **DTC tracking** — active Diagnostic Trouble Codes surface as a
  `binary_sensor.rc_obd_dtc_active` problem indicator; the active
  codes are in the attributes.
- **Reachability** — `binary_sensor.rc_obd_connected` flips off the
  moment the device stops responding.
- **Time-series history** — every reading lands in a SQLite store at
  `<config>/.storage/roamcore_wican.db`. Query the history via:

  ```
  curl http://homeassistant.local:8123/api/roamcore/wican/timeseries?pid=12
  ```

  Returns a JSON time-series suitable for ML analysis.

- **OpenClaw queries** — `what is engine RPM?`, `is the engine
  running?`, `are any DTCs active?` all work out of the box.

## What this slice does NOT cover (yet)

- **Vendor-proprietary PIDs** — Ford Mode-22, GM Mode-24, VAG
  Mode-1B, etc. are not decoded here. Generic Mode-01 only. Per-vehicle
  PID research is a follow-up slice.
- **ML / predictive maintenance** — the database is populated; ML
  on top is a separate slice.
- **DTC clearing** — we read DTCs but don't clear them via OBD2 (use
  a separate tool if you need to clear codes).
- **Vehicle-specific VIN decoding** — we don't pull the VIN or
  translate the ECU's specific protocol family.

## How it auto-discovers

The WiCAN Pro advertises itself on the LAN via mDNS
(`_wican._tcp.local.`) once it's joined your Wi-Fi. Home Assistant's
zeroconf integration picks that up and offers a one-tap "Set up"
button. Confirm, and the polling coordinator starts immediately.

If the WiCAN Pro is already configured to publish to your MQTT
broker, RoamCore picks it up via MQTT discovery too.

If neither path works (e.g. operator-supplied static IP), the config
flow has a manual entry form as a fallback.

## Storage

The time-series store is a single SQLite database at
`<config>/.storage/roamcore_wican.db`. Default retention is 90 days,
configurable in the integration options. Three tables:

- `pid_readings` — (ts, pid, value, session_id), indexed on (pid, ts)
- `sessions` — one row per connection session, with PID count + reading count
- `dtcs` — first-seen + cleared_at timestamps for every DTC

A background task prunes readings older than the retention window
every 24 hours.

## Verification

The slice ships with three test files (pytest, run on any CI bench):

- `tests/test_pid_decoder.py` — 50+ test cases derived directly from
  SAE J1979, validating every PID decoder against canonical
  responses (idle, cruise, hot, cold, etc.).
- `tests/test_db_schema.py` — schema migration, round-trip
  insert/query, retention pruning, DTC upsert/clear, concurrent
  writes from multiple threads.
- `tests/test_discovery.py` — mDNS service name parsing, MQTT topic
  helpers, host validation.

## Rollback

- Delete the integration from the device + Settings → Devices & Services.
- Delete `<config>/.storage/roamcore_wican.db` to clear the time-series.

## See also

- `docs/recipe.md` — full install howto, troubleshooting, and the
  OpenClaw contract surface.
- `homeassistant/custom_components/roamcore_wican/` — the runtime
  integration code (config_flow + coordinator + sensor + DB + views).
