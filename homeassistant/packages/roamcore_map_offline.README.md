# RoamCore map offline degradation package

**Tier:** b (HA-core package recipe — no custom integration, no tier-a
claim, no RoamCore-owned engine).

**Source slice:** Wave 9 #111 — "Map graceful degradation when offline
(gray basemap + last-cached tile + last-known location + banner)".

**Companion packages:**

- `homeassistant/packages/roamcore_map.yaml` — the operator-configurable
  upstream tile URL (`input_text.rc_map_tile_url`) + style URL +
  offline max zoom helper.
- `homeassistant/packages/roamcore_location.yaml` — the operator-
  configurable upstream tracker (`input_text.rc_location_tracker_entity`)
  + the `rc_location_*` template sensors.

## What this package does

When the upstream tile server is unreachable (slow / blocked / no
internet / firewall rule / cellular down), the RoamCore map view
gracefully degrades to:

1. **Gray basemap** — the Lovelace map card with an empty `tile_url`
   renders a plain gray surface (no tile fetch attempted).
2. **Last-known location pin** — `sensor.rc_map_offline_last_location_lat`
   + `sensor.rc_map_offline_last_location_lon` mirror the operator's
   configured `device_tracker.*` and *hold the last non-unknown GPS
   coordinate* when the upstream goes away (HA template `this.state`
   reference preserves the previous value).
3. **Plain-English banner** — `input_text.rc_map_offline_banner`
   carries "Showing your last known location. We'll switch back when
   the map reconnects." (set by the offline-flip automation; cleared
   when the back-online flip fires).
4. **Persistent notification** — fires when the binary_sensor flips
   to `on` ("Map can't reach the internet right now. Showing your
   last known location."); dismissed + a "Map is back online." toast
   when it flips back to `off` (with a 5-minute cooldown so link
   flutters don't spam the operator).

The binary_sensor is wired up by:

- A 30-second `timer.rc_map_reachability_probe` that triggers
  `shell_command.rc_map_reachability_probe` (curl HEAD with a 3-second
  timeout against the operator-configured tile URL).
- The shell_command writes an ISO timestamp into
  `/config/.storage/rc_map_last_tile_fetch.txt` on success; leaves the
  file untouched on failure.
- A `command_line` sensor reads that file → `sensor.rc_map_last_tile_fetch_success`.
- The `binary_sensor.rc_map_offline` template flips to `on` when the
  last fetch is older than 60 seconds OR the operator has pressed
  *Force Offline*. It flips back to `off` after the next successful
  fetch OR when the operator presses *Force Online*.

## Entities exposed (all `rc_map_*` per docs/reference/rc-entity-naming.md)

| Domain | Entity id | Purpose |
|---|---|---|
| `binary_sensor` | `rc_map_offline` | True when the map can't reach the upstream tile server (or the operator has forced offline). |
| `sensor` | `rc_map_last_tile_fetch_success` | ISO timestamp of the last successful tile fetch (or `never`). |
| `sensor` | `rc_map_offline_state_changed` | ISO timestamp of the most recent offline flip (drives the 5-min back-online cooldown). |
| `sensor` | `rc_map_offline_last_location_lat` | Last known latitude (holds the previous value when the device_tracker goes away). |
| `sensor` | `rc_map_offline_last_location_lon` | Last known longitude (holds the previous value when the device_tracker goes away). |
| `input_select` | `rc_map_force_mode` | `auto` / `force_offline` / `force_online`. |
| `input_text` | `rc_map_offline_banner` | Plain-English banner text the dashboard renders when offline. |
| `input_button` | `rc_map_force_offline` | Operator shortcut to flip into force_offline. |
| `input_button` | `rc_map_force_online` | Operator shortcut to flip into force_online. |
| `input_button` | `rc_map_revert_force` | Operator shortcut to revert to auto. |
| `timer` | `rc_map_reachability_probe` | 30-second timer that drives the probe shell_command. |
| `shell_command` | `rc_map_reachability_probe` | curl HEAD probe with a 3-second timeout. |

## Operator wiring (Lovelace dashboard)

The actual Lovelace `conditional` card lives in
`homeassistant/lovelace/roamcore-dashboard-native.yaml` under the
`path: map` view. The package file
`homeassistant/packages/roamcore_map.yaml` documents the snippet as a
comment block so the operator can copy-paste without needing to read
this README. The snippet has two `conditional` cards:

- **Live** (when `binary_sensor.rc_map_offline == off`) — the regular
  `map:` card with the operator's `tile_url`.
- **Offline** (when `binary_sensor.rc_map_offline == on`) — a
  `vertical-stack` with the plain-English banner markdown card +
  the gray-basemap `map:` card with no `tile_url` + the
  last-known location pin.

Both cards are mutually exclusive — only one renders at a time.

## Force-mode behavior

| `input_select.rc_map_force_mode` | `binary_sensor.rc_map_offline` |
|---|---|
| `auto` (default) | Derives from probe (last fetch > 60s = on). |
| `force_offline` | Always on (operator overrides the probe). |
| `force_online` | Always off (operator overrides the probe — useful when the basemap URL works over Tailscale / VPN even though the probe can't reach it). |

## Tests

The bash smoke in `scripts/checks/map-offline-smoke.sh` validates:

1. `yaml.safe_load` parses both `homeassistant/packages/roamcore_map.yaml`
   and `homeassistant/packages/roamcore_map_offline.yaml`.
2. No duplicate `entity_id` across the two files.
3. Every entity exposed by the offline package matches the
   `^rc_map_` regex from `docs/reference/rc-entity-naming.md`.
4. The 60-second offline threshold logic (simulated with a mocked
   timestamp; no real network calls).
5. The 30-second-old-fetch case does NOT trigger offline.
6. The `force_offline` / `force_online` buttons flip the binary_sensor
   regardless of the probe.
7. The package does NOT hardcode the upstream tile URL — it reads
   whatever the operator has set in `input_text.rc_map_tile_url`.
   (This makes the slice independent of any future basemap default
   change; no upstream provider name is baked into the package.)
8. The mocked tile-server probe (3-second timeout) returns the right
   `offline` / `online` state for a synthetic broken-tile-server
   fixture.

The smoke does not require an HA runtime — it's pure repo-local
checks + a mocked bash function that simulates the curl HEAD response.

## See also

- `docs/reference/rc-entity-naming.md` — the canonical `rc_*` naming
  convention.
- `connections/map-dashboard/` — the tier-a wrap-around for the map
  domain (the contract tile surface + the FIVE §9 MANDATORY
  automations + the dashboard recipe).
- `homeassistant/packages/roamcore_map.yaml` — the upstream tile URL
  + style URL + offline max zoom helper.
- `homeassistant/packages/roamcore_location.yaml` — the operator-
  configurable upstream tracker + the `rc_location_*` template
  sensors.