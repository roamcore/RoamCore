# Trip Wrapped (local-first route-recap HTML/JSON report)

**Tier:** A (recipe)
**Category:** map
**Status:** beta

## What this connection is

Trip Wrapped — vendor-neutral local-first route-recap HTML/JSON report — the umbrella for "Trip Wrapped generates a shareable, beautiful HTML report of a trip/route… A fun end-of-trip recap… Easy to share with friends/family… Extra hardware required: Typically none beyond your location history source (often Traccar)… See existing notes in `homeassistant/tools/trip_wrapped/`… RoamCore also exposes `/local/roamcore/trip_wrapped/latest.html` when configured… HA package: `homeassistant/packages/roamcore_trip_wrapped.yaml`" — is the map-category surface that turns your Traccar trip history into a shareable HTML report (latest summary, trips in range, comparisons, story-style writeup, in-browser PNG export).

RoamCore ships **no** custom trip-wrapped integration. The RoamCore-owned package at `homeassistant/packages/roamcore_trip_wrapped.yaml` (224 LOC — the `roamcore_traccar_proxy:` custom component that proxies `/api/roamcore/traccar/*` requests to the upstream Traccar instance + the 5+ `input_text.rc_traccar_*` / `input_text.rc_trip_wrapped_*` helpers for credentials + date range + UI URL + ingress path + the 1 `input_number.rc_traccar_device_id` for the device id + the 2 `binary_sensor.rc_trip_wrapped_latest_ready` + `binary_sensor.rc_traccar_ui_reachable` readiness tiles + the 1 `sensor.rc_trip_wrapped_latest_status` status tile + the 1 `shell_command.rc_trip_wrapped_export` exporter) is the actual surface. The RoamCore-owned report-renderer tooling under `homeassistant/tools/trip_wrapped/` (Python; `export.py` + `build_wrapped.py` + `comparisons.py` + `history.py` + `render_html.py` + `traccar_client.py` + `assets/` + `tests/`) is the actual report-renderer surface — it reads Traccar's `/api/.../reports` + `/api/devices/{id}` endpoints, builds per-trip + trip-list summaries, renders the shareable HTML, and writes the optional PNG export via in-browser canvas. The HA core `shell_command:` integration (since 2022.x — exposes a GUI flow for the operator to add a `shell_command:` that runs an external command from an automation or script) is the actual shell-command surface. The HA core `input_text` / `input_number` integrations (since 2022.x — expose GUI flows for the operator to add helpers) are the actual credentials-pointer surface. The HA core `binary_sensor:` template platform (since 2022.x — exposes a GUI flow for the operator to add a `binary_sensor:` template) is the actual readiness-tile surface. The HA core `sensor:` template platform (since 2022.x — exposes a GUI flow for the operator to add a `sensor:` template) is the actual status-tile surface. The HA core `script:` integration (since 2022.x — exposes a GUI flow for the operator to add a `script:` that runs a sequence of actions) is the umbrella for the §9.1 dashboard-button automation. The 3 `rc_trip_wrapped_*` + `rc_traccar_ui_*` contract tiles are the vendor-neutral layer the dashboard + OpenClaw queries use.

## The 5-step operator flow

- **Step 1 — Configure Traccar credentials** — the operator sets `input_text.rc_traccar_username` + `input_text.rc_traccar_password` (or configures `roamcore_traccar_user_token` + `roamcore_traccar_base_url` in `secrets.yaml` — see the [Traccar (Wave 3 #12)](../traccar/) connection for the upstream setup). The §9.2 credentials-missing guard sets the status tile to `needs_setup` if neither is configured — don't fail silent.

- **Step 2 — Set date range** — the operator sets `input_text.rc_trip_wrapped_from` + `input_text.rc_trip_wrapped_to` to the desired range. The exporter passes these to Traccar's `/api/.../reports` endpoint as the `from` + `to` query params.

- **Step 3 — Set device id** — the operator sets `input_number.rc_traccar_device_id` to the Traccar device id (visible at the Traccar UI under Devices). The exporter reads the device metadata from `/api/devices/{id}` to surface the device name + model in the rendered recap.

- **Step 4 — Trigger export** — the operator triggers `shell_command.rc_trip_wrapped_export` from Developer Tools → Services, or via the dashboard "Generate" button (the §9.1 dashboard-button automation wires the button to `script.rc_trip_wrapped_run` → `shell_command.rc_trip_wrapped_export`). The exporter reads the Traccar data + writes `/local/roamcore/trip_wrapped/latest.html` + `/local/roamcore/trip_wrapped/latest.json` + `/local/roamcore/trip_wrapped/assets/...`. The §9.3 no-trip-data guard sets the status tile to `no_data` if Traccar is reachable but `/api/.../reports` returns 0 trips in the configured range for the configured device — don't fail silent.

- **Step 5 — View the recap** — the operator opens `/local/roamcore/trip_wrapped/latest.html` in their browser. The §9.5 html-cache-buster-param appends `?ts=<rfc3339-nano>` to the dashboard "View report" link so HA Core's static-file cache doesn't serve a stale version. The in-browser "Download summary" PNG export works fully offline via in-browser canvas — the §9.4 png-export-offline-first guard falls back to a no-tile version if the optional map-tile background is unreachable (the exporter requires CORS-enabled tile-layer config).

## Setup recipe (one-paragraph)

1. Confirm the RoamCore-owned package is loaded via the standard HA `packages:` mechanism (the package at `homeassistant/packages/roamcore_trip_wrapped.yaml` is already shipped + RoamCore-owned + preserved verbatim by this slice — the package contents are NOT redefined).
2. Confirm the `roamcore_traccar_proxy:` custom component (shipped by the package) is loaded (verify `/api/roamcore/traccar` returns a 200 from the HA backend).
3. Configure the upstream Traccar user/email + a Traccar user token via the `roamcore_secrets.yaml` keys (`roamcore_traccar_user_token` + `roamcore_traccar_base_url`) or via the legacy `input_text.rc_traccar_*` inputs.
4. Set `input_text.rc_trip_wrapped_from` + `input_text.rc_trip_wrapped_to` to the date range.
5. Set `input_number.rc_traccar_device_id` to the Traccar device id.
6. Verify the 3 contract tiles populate (`binary_sensor.rc_trip_wrapped_latest_ready` + `sensor.rc_trip_wrapped_latest_status` + `binary_sensor.rc_traccar_ui_reachable`).
7. Wire the FIVE §9 MANDATORY automations (§9.1 trip_wrapped_dashboard_button (already wired in the package) + §9.2 traccar_credentials_missing_needs_setup_notice + §9.3 traccar_reachable_no_trip_data_no_data_notice + §9.4 png_export_offline_first_guard + §9.5 html_cache_buster_param).
8. Verify: confirm credentials → set date range → set device id → trigger export → confirm `sensor.rc_trip_wrapped_latest_status` flips to `ok` + `binary_sensor.rc_trip_wrapped_latest_ready` flips to `true` → open the recap in your browser.

Full howto: see [`docs/recipe.md`](docs/recipe.md).

## The 3 contract tiles

| Domain | Tile id | Purpose |
|---|---|---|
| `binary_sensor` | `rc_trip_wrapped_latest_ready` | `true` when `sensor.rc_trip_wrapped_latest_status == 'ok'` (the report is generated + readable at `/local/roamcore/trip_wrapped/latest.html`). |
| `sensor` | `rc_trip_wrapped_latest_status` | One of `ok` / `needs_setup` / `no_data` / `unavailable` / `unknown` (the status of the latest export). |
| `binary_sensor` | `rc_traccar_ui_reachable` | `true` when the Traccar UI (`/api/roamcore/traccar`) responds within 5 s (the upstream data-source reachability tile). |

## The 5 §9 MANDATORY automations

- **§9.1 Trip_wrapped_dashboard_button** — the dashboard "Generate" button → `script.rc_trip_wrapped_run` → `shell_command.rc_trip_wrapped_export` chain (already wired in the package). The automation fires when the dashboard button is pressed + calls the shell command + waits for the export to complete + flips `sensor.rc_trip_wrapped_latest_status` to `ok` + `binary_sensor.rc_trip_wrapped_latest_ready` to `true`. The automation is the entry-point for the operator's "Generate a new wrapped report" workflow.

- **§9.2 Traccar_credentials_missing_needs_setup_notice** — fires when `input_text.rc_traccar_username` AND `input_text.rc_traccar_password` are empty (and no `roamcore_traccar_user_token` is in `secrets.yaml`). The automation sets `sensor.rc_trip_wrapped_latest_status` to `needs_setup` + logs a warning audit entry + fires a notification warning the operator that no Traccar credentials are configured. Without this guard, an unconfigured Traccar would silently emit `unavailable` for the status tile, which would mislead the operator into thinking the upstream is down.

- **§9.3 Traccar_reachable_no_trip_data_no_data_notice** — fires when Traccar is reachable (binary_sensor.rc_traccar_ui_reachable == true) but `/api/.../reports` returns 0 trips in `[rc_trip_wrapped_from, rc_trip_wrapped_to]` for `input_number.rc_traccar_device_id`. The automation sets `sensor.rc_trip_wrapped_latest_status` to `no_data` + logs a warning audit entry + fires a notification warning the operator that no trip data exists for the configured range. Without this guard, the exporter would silently write an empty `latest.html`, which would mislead the operator into thinking the upstream returned data.

- **§9.4 Png_export_offline_first_guard** — fires when the user opens `/local/roamcore/trip_wrapped/latest.html`. The in-browser "Download summary" PNG exporter MUST work fully offline via in-browser canvas; only the optional map-tile background requires network; if no network, fall back to a no-tile version. The automation logs an audit entry on each PNG export event confirming the surface is offline-first (the PNG generation happens in the operator's browser; the HTML lives on the operator's HA box; no cloud round-trip). The exporter requires CORS-enabled tile-layer config — the recipe documents this as the `png_export_requires_cors_enabled_tile_layer` tier-warning.

- **§9.5 Html_cache_buster_param** — fires when Traccar exports a newer trip. The automation appends `?ts=<rfc3339-nano>` to the dashboard "View report" link so HA Core's static-file cache doesn't serve a stale `latest.html`. The automation reads the Traccar trip-list modification timestamp + generates the `?ts=<rfc3339-nano>` query param + updates the dashboard link entity. Without this guard, the operator's browser would cache a stale `latest.html` for hours and miss new trips.

## Why tier-a, but beta

Tier-a is the right tier because the legacy catalog page's "Support tier: A (RoamCore native)" is correct: RoamCore DOES own + ship + maintain both the package at `homeassistant/packages/roamcore_trip_wrapped.yaml` AND the report-renderer tooling under `homeassistant/tools/trip_wrapped/`. No upstream HA integration covers the route-recap HTML/PNG-rendering surface (Traccar's web UI shows a trip list, not a Spotify-Wrapped-style recap). This slice ADDS the recipe layer (manifest + recipe.md + manifest-honesty smoke + 3 contract tiles + FIVE §9 MANDATORY automations + legacy SUPERSEDED banner + docs cross-references) WITHOUT modifying the existing package contents + WITHOUT modifying the existing tooling code.

Status is `beta` because there are no pytest integration tests for the trip-wrapped package (HA core `command_line:` sensor + `shell_command:` + `input_text:` + `input_number:` + `script:` + `binary_sensor:` + `sensor:` integrations are the actual surface; the audit script asserts the manifest is honest about being tier-a + the recipe layer is documented + the contract tiles are vendor-neutral + the FIVE §9 MANDATORY automations are documented). The eight honesty warnings (`no_pytest_bench_fixtures_for_trip_wrapped_package` + `recipe_depends_on_user_configuring_traccar_credentials` + `recipe_depends_on_user_configuring_trip_date_range` + `recipe_depends_on_user_configuring_traccar_device_id` + `requires_operator_wiring_traccar_input_texts_before_first_export` + `png_export_requires_cors_enabled_tile_layer` + `local_html_persists_offline_first_guard` + `traccar_unreachable_keeps_status_unavailable_guard`) document the bench-fixture gap + the operator-side wiring dependencies + the §9.2 needs-setup guard + the §9.3 no-data guard + the §9.4 PNG-export offline-first guard + the §9.5 cache-buster guard.

## Files

- `connection.yml` — the source-of-truth tier-a manifest.
- `__init__.py` — `DOMAIN = "trip_wrapped"` marker for the audit.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded by this slice): [`docs/catalog/map/trip-wrapped.md`](../../docs/catalog/map/trip-wrapped.md)
- Existing RoamCore-owned trip-wrapped package (preserved verbatim): [`homeassistant/packages/roamcore_trip_wrapped.yaml`](../../homeassistant/packages/roamcore_trip_wrapped.yaml) (224 LOC — declares the `roamcore_traccar_proxy:` custom component + the 5+ input_text + the 1 input_number + the 2 binary_sensor + the 1 sensor + the 1 shell_command)
- Existing RoamCore-owned report-renderer tooling (preserved verbatim): [`homeassistant/tools/trip_wrapped/`](../../homeassistant/tools/trip_wrapped/) (Python; `export.py` + `build_wrapped.py` + `comparisons.py` + `history.py` + `render_html.py` + `traccar_client.py` + `assets/` + `tests/` + `README.md`)
- HA core `shell_command:` integration (the canonical shell-command surface): https://www.home-assistant.io/integrations/shell_command/
- HA core `input_text` integration (the canonical credentials-pointer helper surface): https://www.home-assistant.io/integrations/input_text/
- HA core `input_number` integration (the canonical device-id helper surface): https://www.home-assistant.io/integrations/input_number/
- HA core `command_line:` sensor platform (the canonical sensor surface): https://www.home-assistant.io/integrations/command_line/
- HA core `script:` integration (the canonical §9.1 dashboard-button umbrella): https://www.home-assistant.io/integrations/script/
- Traccar `/api/.../reports` endpoint (the canonical upstream trip-history source): https://www.traccar.org/reports/
- Trip Local (the sibling trip-metric connection; today's distance/drive_time/stops feed the wrapped comparisons): `connections/trip-local/` (Wave 3 #68)
- Map dashboard (the map overlay surface; the §9.4 PNG export reuses the map tile layer): `connections/map-dashboard/` (Wave 3 #66)
- Traccar (the upstream Traccar data-source connection; the `roamcore_traccar_proxy` custom component bridges it): `connections/traccar/` (Wave 3 #12)
- Mode (the §9.4 PNG-export offline-first guard's mode-state cross-reference): `connections/mode/` (Wave 3 #61)
- Remote-access (the §9.5 html-cache-buster-param's remote-access cross-reference): `connections/remote-access/` (Wave 3 #58)
- Advanced-mode (the §9.2 needs-setup guard's confirm-flag pattern): `connections/advanced-mode/` (Wave 3 #63)
- OpenClaw JSON API (the JSON API surfaces the `rc_trip_wrapped_*` + `rc_traccar_ui_*` tiles): `connections/openclaw-api/` (Wave 3 #64)
- Leveling (the §9.4 wrapped-report's "Vehicle posture" section's leveling-jack cross-reference): `connections/leveling/` (Wave 3 #60)
- RoamCore entity naming: [`docs/reference/rc-entity-naming.md`](../../docs/reference/rc-entity-naming.md) (the `trip` subsystem was added by the trip-local Wave 3 #68 sibling slice; the `rc_trip_wrapped_*` + `rc_traccar_ui_*` tiles follow the same `trip` subsystem convention)