# WiCAN Pro — Recipe (tier-a native integration)

This is the install + troubleshooting howto for the RoamCore WiCAN Pro
connection. It complements `../README.md` (the user-facing IKEA page)
with the operator-facing details.

## What this slice ships

This is the FIRST tier-a native connection in the RoamCore connection
pipeline. The recipe covers everything below:

1. **Custom HA component** (`homeassistant/custom_components/roamcore_wican/`)
   — a full Home Assistant integration with:
   - `config_flow.py` — auto-discover via mDNS + MQTT, manual IP fallback
   - `coordinator.py` — a polling DataUpdateCoordinator against the WiCAN Pro's REST API
   - `db.py` — a SQLite time-series store at `<config>/.storage/roamcore_wican.db`
   - `sensor.py` — one `sensor.rc_obd_*` per generic Mode-01 PID
   - `binary_sensor.py` — `rc_obd_connected` + `rc_obd_dtc_active`
   - `timeseries_view.py` — HTTP read-only views for ML tools
   - `pids.py` — the generic Mode-01 PID table + decoders
   - `discovery.py` — mDNS + MQTT topic helpers

2. **Connection manifest** (`connections/wican-pro/connection.yml`)
3. **Tests** (172 pytest cases — see `tests/`)
4. **User-facing IKEA page** (`docs/catalog/connectivity/wican-pro.md`)
5. **This recipe**

## Install

### Path A — Auto-discover (recommended)

1. Plug the WiCAN Pro into the OBD2 port.
2. Power on the vehicle (key to accessory is enough).
3. Wait ~10 seconds for the WiCAN Pro to join Wi-Fi.
4. Open HA on your phone. You'll see "Discovered a WiCAN Pro" — tap "Set up".

The config_flow will:
- Show the device name + host + firmware version
- Offer a one-tap confirm button
- Save the entry
- Start the polling coordinator immediately

### Path B — Manual IP

If auto-discovery doesn't fire (some Wi-Fi routers block mDNS), use the manual flow:

1. Settings → Devices & Services → + Add Integration → "RoamCore WiCAN Pro"
2. Enter the WiCAN Pro's IP address (find it in your router's DHCP leases)
3. Confirm poll interval (default 5s)
4. Confirm retention days (default 90)
5. Submit

### Path C — MQTT discovery

If the WiCAN Pro is already publishing to an MQTT broker (the WiCAN's
own MQTT bridge feature), HA's MQTT integration will pick up the
discovery messages. The config_flow will offer a "Discovered via MQTT"
confirm step.

## Operator-pickable settings

All of these live in Settings → Devices & Services → RoamCore WiCAN Pro → Configure:

- **Poll interval** (1-60s, default 5) — how often we ask the WiCAN Pro for fresh readings
- **Retention days** (1-365, default 90) — how long PID readings are kept in the SQLite store

## What the dashboard shows

Once set up, you get 17 generic Mode-01 PID sensors + 1 session
counter + 2 binary sensors. All named `sensor.rc_obd_*` or
`binary_sensor.rc_obd_*` per the RoamCore entity naming convention.

The dashboard auto-populates the moment the integration starts polling.

## Querying the time-series

Three HTTP endpoints:

```
GET /api/roamcore/wican/timeseries/catalog
  -> {"pids": [{"pid": 12, "name": "rpm", "label": "Engine RPM",
                 "unit": "rpm", "reading_count": 1234, "latest_ts": ...}, ...]}

GET /api/roamcore/wican/timeseries?pid=12&from=1234560000&to=1234570000&limit=1000
  -> {"pid": 12, "name": "rpm", "unit": "rpm",
      "count": 1000, "points": [{"ts": 1234567890, "value": 840.0}, ...]}

GET /api/roamcore/wican/timeseries/stats
  -> {"devices": {"WiCAN-A1B2C3": {"total_readings": 12345, ...}}}
```

These are read-only. No auth (assume local LAN; HA's http component is
the security boundary).

## Troubleshooting

### The WiCAN Pro isn't auto-discovered

- Make sure it's joined the same Wi-Fi network as HA.
- Check the WiCAN Pro's web UI (browse to its IP in a normal browser) — it should show its current network + IP.
- Some routers block mDNS. If your router is one of those, use the manual IP flow.

### `binary_sensor.rc_obd_connected` is OFF

- The integration is failing to reach the WiCAN Pro. Check Settings → Devices & Services → RoamCore WiCAN Pro → Logs for the error.
- Common causes: WiCAN Pro went to sleep, the vehicle is off, the Wi-Fi dropped.

### Sensor values are all "Unknown"

- The vehicle is off. The OBD2 bus is unpowered when the ignition is off.
- The WiCAN Pro is reaching HA but the vehicle's ECU isn't responding. Check the WiCAN Pro's web UI for a "BUS error" or similar.

### The DB is growing too fast

- Reduce retention_days (Settings → Devices & Services → RoamCore WiCAN Pro → Configure).
- Increase poll interval to fewer readings per day.

## Tier-a disclosure

Tier-a is honest here:

- RoamCore ships its own custom_components/roamcore_wican/ — we own the config_flow, coordinator, DB, sensor entities, and HTTP views.
- We do NOT claim the upstream HA `obd` integration works for the WiCAN Pro (it doesn't — it expects a wired ELM327 over serial).
- We do NOT claim integration test coverage against a real WiCAN Pro (the CI bench has no OBD2 port).
- 172 unit tests cover the PID decoder, the DB schema, the discovery layer, and the manifest honesty. They run on any CI bench.

## Rollback

- Delete the integration from Settings → Devices & Services.
- Delete `<config>/.storage/roamcore_wican.db` to wipe the time-series.

The integration does not touch anything outside `<config>/.storage/`.
