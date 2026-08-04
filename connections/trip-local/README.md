# Trip Local (local-first trip metrics from the HA recorder)

**Tier:** A (recipe)
**Category:** map
**Status:** beta

## What this connection is

Trip Local — vendor-neutral local-first trip metrics from the HA recorder — the umbrella for "RoamCore includes a 'Trip Local' path for working with local trip data/tools inside Home Assistant… Useful when you don't want to depend on a cloud service… Helps keep trip history and exports under your control… Extra hardware required: None… Install / best next step: HA package: homeassistant/packages/roamcore_trip_local.yaml" — is the map-category surface that surfaces today's distance / drive time / stops computed from the operator's HA recorder DB.

RoamCore ships **no** custom trip-local integration. The RoamCore-owned package at `homeassistant/packages/roamcore_trip_local.yaml` (73 LOC — the `shell_command.rc_trip_local_today_export` that runs the recorder-DB Python script + the 15-minute `automation.rc_trip_local_today_exporter` that triggers the shell command + the 3 `command_line:` sensors that read the resulting JSON: `sensor.rc_trip_local_today_distance_mi` + `sensor.rc_trip_local_today_drive_time` + `sensor.rc_trip_local_today_stops`) is the actual surface. The HA core `recorder:` integration (since 2022.x — exposes the canonical recorder DB that records `device_tracker.*` history) is the canonical source of `device_tracker.*` history. The HA core `command_line:` sensor platform (since 2022.x — exposes a GUI flow for the operator to add a `command_line:` sensor that runs an external command + parses the stdout) is the actual sensor surface. The HA core `shell_command:` integration (since 2022.x — exposes a GUI flow for the operator to add a `shell_command:` that runs an external command from an automation or script) is the actual shell-command surface. The HA core `automation:` integration (since 2022.x — exposes the canonical automation runner) is the umbrella for the FIVE §9 MANDATORY automations. The 3 `rc_trip_local_today_*` contract tiles are the vendor-neutral layer the dashboard + OpenClaw queries use.

## The 4-step operator flow

- **Step 1 — Configure the device_tracker** — the operator sets `input_text.rc_location_tracker_entity` to their chosen `device_tracker.*` (typically `device_tracker.traccar_van` if Traccar is the upstream source, or a phone-derived device_tracker if the HA Companion app is the upstream source — the RoamCore location subsystem already wires this for Traccar / OwnTracks / HA companion app / etc.). The §9.2 device_tracker_unconfigured_keeps_tiles_unknown guard ensures the 3 tiles stay `unknown` rather than silently emitting 0 when no device_tracker is configured.

- **Step 2 — Wait 15 minutes for the first export** — the `automation.rc_trip_local_today_exporter` (the §9.1 local-trip-metrics-export automation) triggers every 15 minutes via `time_pattern: minutes: "/15"`. The `shell_command.rc_trip_local_today_export` runs `python3 /config/tools/trip_local/trip_today.py --entity-id {{ states('input_text.rc_location_tracker_entity') }} --day today --out-json /config/www/roamcore/trip_local/today.json`. Alternatively, the operator can trigger the shell command manually via Developer Tools → Services → `shell_command.rc_trip_local_today_export`.

- **Step 3 — Verify the 3 contract tiles populate** — the operator opens Developer Tools → States and confirms:
  - `sensor.rc_trip_local_today_distance_mi` → today's distance in miles (e.g. `12.34`)
  - `sensor.rc_trip_local_today_drive_time` → today's drive time in `H:MM` format (e.g. `1:23`)
  - `sensor.rc_trip_local_today_stops` → today's stop count (e.g. `3`)

  The §9.4 drive_time_format_human_readable_guard enforces the `H:MM` format on the drive-time tile + the §9.3 recorder_purge_resets_local_trip_metrics guard resets the tiles to 0 when the recorder purges history older than N days.

- **Step 4 — Optional — install the Map dashboard** — the operator installs the [Map dashboard (Wave 3 #66)](../map-dashboard/) connection to overlay today's route on the map. The map dashboard's `select.rc_map_trip_overlay` mode picker can be set to `Active` to render today's route polyline alongside the current location.

## Setup recipe (one-paragraph)

1. Confirm the RoamCore-owned package is loaded via the standard HA `packages:` mechanism (the package at `homeassistant/packages/roamcore_trip_local.yaml` is already shipped + RoamCore-owned + preserved verbatim by this slice — the package contents are NOT redefined).
2. Confirm the HA core `command_line:` sensor + `shell_command:` + `recorder:` + `automation:` integrations are installed (auto-installed in every HA install + exposed via the HA UI under Settings → Devices & services).
3. Confirm the upstream `device_tracker.*` entity is configured via `input_text.rc_location_tracker_entity` (the RoamCore location subsystem already wires this — see the [map-dashboard (Wave 3 #66)](../map-dashboard/) connection for the device_tracker picker).
4. Confirm the HA recorder is enabled (default ON in every HA install; the recorder DB is the canonical source of `device_tracker.*` history).
5. Verify the 3 `rc_trip_local_today_*` contract tiles (`sensor.rc_trip_local_today_distance_mi` + `sensor.rc_trip_local_today_drive_time` + `sensor.rc_trip_local_today_stops`) populate via the existing `command_line:` sensors in the package.
6. Wire the FIVE §9 MANDATORY automations (§9.1 local-trip-metrics-export (already wired in the package) + §9.2 device_tracker_unconfigured_keeps_tiles_unknown + §9.3 recorder_purge_resets_local_trip_metrics + §9.4 drive_time_format_human_readable_guard + §9.5 no_traccar_required_offline_first_guard).
7. Verify: confirm the device_tracker → wait 15 minutes for the first export → confirm the 3 tiles populate → optionally install the Map dashboard to overlay today's route.

Full howto: see [`docs/recipe.md`](docs/recipe.md).

## The 3 `rc_trip_local_today_*` contract tiles

| Domain | Tile id | Purpose |
|---|---|---|
| `sensor` | `rc_trip_local_today_distance_mi` | Today's distance in miles — `command_line:` sensor that reads `/config/www/roamcore/trip_local/today.json` and emits the `distance_m` field converted to miles. |
| `sensor` | `rc_trip_local_today_drive_time` | Today's drive time in `H:MM` format — `command_line:` sensor that reads `/config/www/roamcore/trip_local/today.json` and emits the `drive_time_s` field formatted as `H:MM`. |
| `sensor` | `rc_trip_local_today_stops` | Today's stop count — `command_line:` sensor that reads `/config/www/roamcore/trip_local/today.json` and emits the `stops` field. |

## The 5 §9 MANDATORY automations

- **§9.1 Local-trip-metrics-export** — the 15-minute trigger that's already wired in the package as `automation.rc_trip_local_today_exporter` (`time_pattern: minutes: "/15"` → `shell_command.rc_trip_local_today_export` → `python3 /config/tools/trip_local/trip_today.py --entity-id {{ states('input_text.rc_location_tracker_entity') }} --day today --out-json /config/www/roamcore/trip_local/today.json`). The automation runs the recorder-DB-reading Python script + emits a JSON to `/config/www/roamcore/trip_local/today.json` every 15 minutes.

- **§9.2 Device_tracker_unconfigured_keeps_tiles_unknown** — fires when `input_text.rc_location_tracker_entity` is `unknown` / `unavailable` / empty. The automation resets all 3 tiles to `unknown` rather than silently emitting 0 + logs a warning audit entry + fires a notification warning the operator that no device_tracker is configured. Without this guard, an unconfigured device_tracker would silently emit `0.0` for distance + `0:00` for drive_time + `0` for stops, which would mislead the operator into thinking they've driven nothing today.

- **§9.3 Recorder_purge_resets_local_trip_metrics** — fires when the recorder purges history older than N days (the recorder's `purge_keep_days` integration option). The automation resets the 3 trip-today tiles to 0 (don't carry over stale values) + logs an audit entry. Without this guard, the tiles would carry over stale values from the purged history.

- **§9.4 Drive_time_format_human_readable_guard** — fires when the `rc_trip_local_today_drive_time` tile is set. The automation enforces the `H:MM` format on the tile value (e.g. `1:23` for 1 hour 23 minutes) + rejects raw seconds (e.g. `4980`) + logs an audit entry if the format is wrong. Without this guard, the tile could leak raw seconds into the dashboard, which would be unreadable.

- **§9.5 No_traccar_required_offline_first_guard** — explicitly documents that no Traccar / no cloud is required for this connection to work; the surface works fully offline from the recorder DB alone. The automation logs an audit entry on each tile update confirming the surface is local-first (the recorder DB is on the operator's HA box; the JSON export is on the operator's HA box; no cloud round-trip).

## Why tier-a, but beta

Tier-a is the right tier because the legacy catalog page's "Support tier: A (RoamCore native)" is correct: RoamCore DOES own + ship + maintain the package at `homeassistant/packages/roamcore_trip_local.yaml`. This slice ADDS the recipe layer (manifest + recipe.md + manifest-honesty smoke + 3 `rc_trip_local_today_*` contract tiles + FIVE §9 MANDATORY automations + legacy SUPERSEDED banner + docs cross-references) WITHOUT modifying the existing package contents.

Status is `beta` because there are no pytest integration tests for the trip-local package (HA core `command_line:` sensor + `shell_command:` + `recorder:` integrations are the actual surface; the audit script asserts the manifest is honest about being tier-a + the recipe layer is documented + the contract tiles are vendor-neutral + the FIVE §9 MANDATORY automations are documented). The five honesty warnings (`no_pytest_bench_fixtures_for_trip_local_package` + `recipe_depends_on_user_configuring_device_tracker` + `recipe_depends_on_recorder_db_having_enough_history` + `requires_operator_wiring_device_tracker_entity_before_first_use` + `recorder_unavailable_keeps_tiles_unknown_guard`) document the bench-fixture gap + the operator-side wiring dependencies + the §9.2 device_tracker_unconfigured guard.

## Files

- `connection.yml` — the source-of-truth tier-a manifest.
- `__init__.py` — `DOMAIN = "trip_local"` marker for the audit.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded by this slice): [`docs/catalog/map/trip-local.md`](../../docs/catalog/map/trip-local.md)
- Existing RoamCore-owned trip-local package (preserved verbatim): [`homeassistant/packages/roamcore_trip_local.yaml`](../../homeassistant/packages/roamcore_trip_local.yaml) (73 LOC — declares the `shell_command.rc_trip_local_today_export` + the `automation.rc_trip_local_today_exporter` + the 3 `command_line:` sensors that read the resulting JSON)
- HA core `recorder:` integration (the canonical source of `device_tracker.*` history): https://www.home-assistant.io/integrations/recorder/
- HA core `command_line:` sensor platform (the canonical sensor surface): https://www.home-assistant.io/integrations/command_line/
- HA core `shell_command:` integration (the canonical shell-command surface): https://www.home-assistant.io/integrations/shell_command/
- HA core `input_text` integration (the canonical `input_text.rc_location_tracker_entity` helper): https://www.home-assistant.io/integrations/input_text/
- HA core `automation:` integration (the canonical umbrella for the FIVE §9 MANDATORY automations): https://www.home-assistant.io/integrations/automation/
- Map dashboard (the optional route-overlay sibling): `connections/map-dashboard/` (Wave 3 #66)
- Trip Wrapped (the forward-referenced weekly-summary sibling; Wave 3 #69 — will land in a follow-up slice): `connections/trip-wrapped/` (planned)
- Mode (the §9.5 offline-first guard's mode-state cross-reference): `connections/mode/` (Wave 3 #61)
- Remote-access (the §9.5 offline-first guard's offline-first cross-reference): `connections/remote-access/` (Wave 3 #58)
- Advanced-mode (the §9.4 drive-time-format guard's confirm-flag pattern): `connections/advanced-mode/` (Wave 3 #63)
- OpenClaw JSON API (the JSON API surfaces the `rc_trip_local_today_*` tiles): `connections/openclaw-api/` (Wave 3 #64)
- Leveling (the §9.5 offline-first guard's leveling-jack cross-reference): `connections/leveling/` (Wave 3 #60)
- RoamCore entity naming: [`docs/reference/rc-entity-naming.md`](../../docs/reference/rc-entity-naming.md) (the `trip` subsystem was added by this slice)