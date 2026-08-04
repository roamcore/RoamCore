# Trip Wrapped — Recipe (tier-a recipe connection)

This is the install + troubleshooting howto for the RoamCore Trip Wrapped connection. It complements `../README.md` (the user-facing IKEA page) with the operator-facing details.

## What this slice ships

This is a tier-a recipe connection — the recipe wraps the existing RoamCore-owned package at `homeassistant/packages/roamcore_trip_wrapped.yaml` (224 LOC) AND the existing RoamCore-owned report-renderer tooling under `homeassistant/tools/trip_wrapped/` (Python; `export.py` + `build_wrapped.py` + `comparisons.py` + `history.py` + `render_html.py` + `traccar_client.py` + `assets/` + `tests/`) and publishes the recipe layer (manifest + recipe.md + manifest-honesty smoke + cross-references). The package contents are PRESERVED VERBATIM by this slice. The tooling code is PRESERVED VERBATIM by this slice.

The recipe covers everything below:

1. **Connection manifest** (`connections/trip-wrapped/connection.yml`)
2. **Recipe howto** (`connections/trip-wrapped/docs/recipe.md`) — this file
3. **User-facing IKEA page** (`connections/trip-wrapped/README.md`)
4. **Tests** (`connections/trip-wrapped/tests/test_connection_yml.py`) — manifest honesty smoke
5. **Existing RoamCore-owned package** (`homeassistant/packages/roamcore_trip_wrapped.yaml`) — the surface this slice WRAPS (referenced verbatim via `install.packages:` in the manifest — the package contents are NOT redefined)
6. **Existing RoamCore-owned report-renderer tooling** (`homeassistant/tools/trip_wrapped/`) — the report-renderer this slice WRAPS (referenced from `recipe.md` — the tooling code is NOT modified by this slice)

## What this is

RoamCore's local-first route-recap report renderer. Turn your Traccar trip history into a shareable HTML report — latest summary, trips in range, comparisons, story-style writeup, in-browser PNG export. The HTML lives at `/local/roamcore/trip_wrapped/latest.html` and updates via the `shell_command.rc_trip_wrapped_export` script.

## Why it's useful in a van

- **No cloud dependency for the recap** — the rendered HTML lives at `/local/roamcore/trip_wrapped/latest.html` on the operator's HA box; the in-browser PNG export happens in the operator's browser via in-browser canvas; no cloud round-trip.
- **Vendor-neutral `rc_*` contract surface** — the 3 contract tiles (`binary_sensor.rc_trip_wrapped_latest_ready` + `sensor.rc_trip_wrapped_latest_status` + `binary_sensor.rc_traccar_ui_reachable`) are vendor-neutral (no Spotify / Apple Music / route-engine / cloud-recap names leak into the tile ids; Traccar IS the canonical source for the upstream trip-history data, so `rc_traccar_ui_reachable` is the explicit exception per Hard Rule #1: the vendor name IS the canonical product name; the data-source-prefix is allowed).
- **Traccar is OPTIONAL** — the exporter gracefully degrades to a `needs_setup` notice when Traccar credentials / devices aren't configured (the §9.2 credentials-missing guard).
- **No-data is a first-class state** — the exporter sets the status tile to `no_data` when Traccar is reachable but `/api/.../reports` returns 0 trips in the configured range for the configured device (the §9.3 no-trip-data guard) — don't fail silent.
- **Works offline for the recap** — the rendered HTML is fully static once generated; the in-browser PNG export works fully offline via in-browser canvas; only the optional map-tile background requires network (the §9.4 png-export-offline-first guard falls back to a no-tile version if no network).
- **Easy to share** — the operator can email the rendered HTML + the PNG export to friends/family without exposing any live data; the HTML is a snapshot of the operator's trip history at the moment of export.

## Extra hardware required

**Typically none.** Traccar is OPTIONAL — the exporter gracefully degrades to a `needs_setup` notice when Traccar credentials / devices aren't configured. The package + the tooling are RoamCore-owned + RoamCore-shipped; the Python report-renderer is RoamCore-owned + RoamCore-shipped.

If the operator wants the optional map-tile background in the recap, they need CORS-enabled tile-layer config (the `png_export_requires_cors_enabled_tile_layer` tier-warning documents this dependency).

## Install / best next step

The 5-step operator flow:

1. **Configure Traccar credentials** — operator sets `input_text.rc_traccar_username` + `input_text.rc_traccar_password` OR configures `roamcore_traccar_user_token` + `roamcore_traccar_base_url` in `secrets.yaml` (see the [Traccar (Wave 3 #12)](../traccar/) connection for the upstream setup). The §9.2 credentials-missing guard sets the status tile to `needs_setup` if neither is configured — don't fail silent.

2. **Set date range** — operator sets `input_text.rc_trip_wrapped_from` + `input_text.rc_trip_wrapped_to` to the desired range. The exporter passes these to Traccar's `/api/.../reports` endpoint as the `from` + `to` query params.

3. **Set device id** — operator sets `input_number.rc_traccar_device_id` to the Traccar device id (visible at the Traccar UI under Devices). The exporter reads the device metadata from `/api/devices/{id}` to surface the device name + model in the rendered recap.

4. **Trigger export** — operator triggers `shell_command.rc_trip_wrapped_export` from Developer Tools → Services, or via the dashboard "Generate" button (the §9.1 dashboard-button automation wires the button to `script.rc_trip_wrapped_run` → `shell_command.rc_trip_wrapped_export`). The exporter reads the Traccar data + writes `/local/roamcore/trip_wrapped/latest.html` + `/local/roamcore/trip_wrapped/latest.json` + `/local/roamcore/trip_wrapped/assets/...`. The §9.3 no-trip-data guard sets the status tile to `no_data` if Traccar is reachable but `/api/.../reports` returns 0 trips in the configured range — don't fail silent.

5. **View the recap** — operator opens `/local/roamcore/trip_wrapped/latest.html` in their browser. The §9.5 html-cache-buster-param appends `?ts=<rfc3339-nano>` to the dashboard "View report" link so HA Core's static-file cache doesn't serve a stale version. The in-browser "Download summary" PNG export works fully offline via in-browser canvas — the §9.4 png-export-offline-first guard falls back to a no-tile version if the optional map-tile background is unreachable (the exporter requires CORS-enabled tile-layer config).

## What it produces

- **`/local/roamcore/trip_wrapped/latest.html`** — the shareable recap HTML (the "Trip Wrapped" report; per-trip cards + trip-list table + comparisons + story-style writeup + the in-browser "Download summary" PNG export button).
- **`/local/roamcore/trip_wrapped/latest.json`** — the raw stats + trip list (the JSON that the HTML reads on load to populate the trip cards + the trip-list table + the comparisons).
- **`/local/roamcore/trip_wrapped/assets/...`** — the static assets the HTML loads (CSS + JS + sample images + map-tile layer config).

## The 3 contract tiles

The surface publishes 3 contract tiles:

- **`binary_sensor.rc_trip_wrapped_latest_ready`** — `true` when `sensor.rc_trip_wrapped_latest_status == 'ok'` (the report is generated + readable at `/local/roamcore/trip_wrapped/latest.html`). The tile is the dashboard's "ready to view" indicator.
- **`sensor.rc_trip_wrapped_latest_status`** — one of `ok` / `needs_setup` / `no_data` / `unavailable` / `unknown` (the status of the latest export). The tile is the dashboard's "what state is the export in" indicator.
- **`binary_sensor.rc_traccar_ui_reachable`** — `true` when the Traccar UI (`/api/roamcore/traccar`) responds within 5 s (the upstream data-source reachability tile). The `roamcore_traccar_proxy:` custom component polls the Traccar `/api/server` endpoint and exposes this.

The 3 tiles refresh:
- `binary_sensor.rc_trip_wrapped_latest_ready` → on each export completion (via the §9.1 dashboard-button automation OR the §9.5 html-cache-buster-param trigger).
- `sensor.rc_trip_wrapped_latest_status` → on each export attempt (via the §9.2 needs-setup guard OR the §9.3 no-data guard OR the §9.1 dashboard-button completion).
- `binary_sensor.rc_traccar_ui_reachable` → every 30 s via the `roamcore_traccar_proxy:` custom component's poll loop.

## §9 MANDATORY automations

The FIVE cross-cutting automations:

1. **§9.1 Trip_wrapped_dashboard_button** — the dashboard "Generate" button → `script.rc_trip_wrapped_run` → `shell_command.rc_trip_wrapped_export` chain (already wired in the package). The automation fires when the dashboard button is pressed + calls the shell command + waits for the export to complete + flips `sensor.rc_trip_wrapped_latest_status` to `ok` + `binary_sensor.rc_trip_wrapped_latest_ready` to `true`. **The §9.1 automation is the entry-point for the operator's "Generate a new wrapped report" workflow — without it, the dashboard button doesn't trigger the exporter.**

2. **§9.2 Traccar_credentials_missing_needs_setup_notice** — fires when `input_text.rc_traccar_username` AND `input_text.rc_traccar_password` are empty (and no `roamcore_traccar_user_token` is in `secrets.yaml`). The automation sets `sensor.rc_trip_wrapped_latest_status` to `needs_setup` + logs a warning audit entry + fires a notification warning the operator that no Traccar credentials are configured. **Without this guard, an unconfigured Traccar would silently emit `unavailable` for the status tile, which would mislead the operator into thinking the upstream is down.**

3. **§9.3 Traccar_reachable_no_trip_data_no_data_notice** — fires when Traccar is reachable (`binary_sensor.rc_traccar_ui_reachable == true`) but `/api/.../reports` returns 0 trips in `[rc_trip_wrapped_from, rc_trip_wrapped_to]` for `input_number.rc_traccar_device_id`. The automation sets `sensor.rc_trip_wrapped_latest_status` to `no_data` + logs a warning audit entry + fires a notification warning the operator that no trip data exists for the configured range. **Without this guard, the exporter would silently write an empty `latest.html`, which would mislead the operator into thinking the upstream returned data.**

4. **§9.4 Png_export_offline_first_guard** — fires when the user opens `/local/roamcore/trip_wrapped/latest.html`. The in-browser "Download summary" PNG exporter MUST work fully offline via in-browser canvas; only the optional map-tile background requires network; if no network, fall back to a no-tile version. The automation logs an audit entry on each PNG export event confirming the surface is offline-first (the PNG generation happens in the operator's browser; the HTML lives on the operator's HA box; no cloud round-trip). **This guard is the contract-tier promise — it's the §9.4 proof that the route-recap report surface is vendor-neutral + offline-first.** The exporter requires CORS-enabled tile-layer config — the recipe documents this as the `png_export_requires_cors_enabled_tile_layer` tier-warning.

5. **§9.5 Html_cache_buster_param** — fires when Traccar exports a newer trip. The automation appends `?ts=<rfc3339-nano>` to the dashboard "View report" link so HA Core's static-file cache doesn't serve a stale `latest.html`. The automation reads the Traccar trip-list modification timestamp + generates the `?ts=<rfc3339-nano>` query param + updates the dashboard link entity. **Without this guard, the operator's browser would cache a stale `latest.html` for hours and miss new trips.**

## Troubleshooting

### The status tile stays `needs_setup` forever

- `input_text.rc_traccar_username` AND `input_text.rc_traccar_password` are empty (and no `roamcore_traccar_user_token` is in `secrets.yaml`). The §9.2 credentials-missing guard is firing correctly.
- Set `input_text.rc_traccar_username` + `input_text.rc_traccar_password` to the operator's Traccar credentials.
- Alternatively, configure `roamcore_traccar_user_token` + `roamcore_traccar_base_url` in `secrets.yaml`.
- Verify the Traccar credentials work by curling the Traccar UI directly with the same credentials.

### The status tile stays `no_data` even after the operator has driven the configured range

- Traccar is reachable (good), but `/api/.../reports` returns 0 trips. The §9.3 no-trip-data guard is firing correctly.
- Verify the date range is correct (`input_text.rc_trip_wrapped_from` + `input_text.rc_trip_wrapped_to`).
- Verify the device id is correct (`input_number.rc_traccar_device_id`).
- Verify the device has recorded trips in the configured range by curling the Traccar `/api/.../reports` endpoint directly with the same credentials + date range + device id.

### The status tile stays `unavailable` after configuring Traccar

- The Traccar UI is unreachable. The §9.5 traccar_unreachable_keeps_status_unavailable_guard is firing correctly.
- Verify Traccar is running (`binary_sensor.rc_traccar_ui_reachable` should be `true`).
- Verify `input_text.rc_traccar_base_url` points to the correct Traccar instance URL.
- Verify the `roamcore_traccar_proxy:` custom component is loaded (check Settings → Devices & services → Integration: RoamCore Traccar Proxy).

### The latest.html is missing or stale

- The `shell_command.rc_trip_wrapped_export` hasn't run yet. Trigger it from Developer Tools → Services or via the dashboard "Generate" button.
- The §9.1 dashboard-button automation might not be wired. Verify the automation exists in Settings → Automations.
- The `/config/www/roamcore/trip_wrapped/` directory might not be writable. Verify the directory exists + is writable by the HA process.

### The PNG export is broken / throws a CORS error

- The optional map-tile background requires CORS-enabled tile-layer config. Verify the tile-layer config in the recipe allows CORS.
- The §9.4 png-export-offline-first guard falls back to a no-tile version if the map-tile background is unreachable. The PNG export should still succeed with a no-tile background.
- If the PNG export fails entirely, verify the operator's browser supports in-browser canvas + the `html2canvas` library (or whatever the exporter uses).

### The dashboard "View report" link serves a stale `latest.html`

- The §9.5 html-cache-buster-param appends `?ts=<rfc3339-nano>` to the dashboard link. Verify the automation is wired in Settings → Automations.
- Alternatively, hard-refresh the browser (Cmd+Shift+R / Ctrl+Shift+R) to bypass the browser cache.

## Privacy

- No RoamCore-side telemetry — the rendered HTML lives at `/local/roamcore/trip_wrapped/latest.html` on the operator's HA box; the in-browser PNG export happens in the operator's browser via in-browser canvas; no cloud round-trip.
- The operator owns the rendered HTML + the PNG export + the JSON.
- The upstream Traccar instance is the operator's choice — Traccar / OwnTracks / HA companion app / etc. (Traccar is the typical choice because it stores trip history; see the [Traccar (Wave 3 #12)](../traccar/) connection for the upstream setup).

## Tier-a promotion outline

Tier-a is honest because:

- RoamCore ships its own package at `homeassistant/packages/roamcore_trip_wrapped.yaml` (224 LOC) — the package IS the tier-a surface.
- RoamCore ships the report-renderer tooling under `homeassistant/tools/trip_wrapped/` (Python; `export.py` + `build_wrapped.py` + `comparisons.py` + `history.py` + `render_html.py` + `traccar_client.py` + `assets/` + `tests/`) — the tooling IS the tier-a renderer surface.
- No upstream HA integration covers the route-recap HTML/PNG-rendering surface (Traccar's web UI shows a trip list, not a Spotify-Wrapped-style recap) — RoamCore ships the report-renderer as part of its tier-a surface.
- The 3 `rc_trip_wrapped_*` + `rc_traccar_ui_*` contract tiles are vendor-neutral + offline-first.
- The FIVE §9 MANDATORY automations document the cross-cutting guarantees (dashboard-button entry-point + credentials-missing needs-setup guard + no-trip-data no-data guard + PNG-export offline-first guard + HTML-cache-buster-param guard).

## Files

- `connections/trip-wrapped/connection.yml` — tier-a manifest.
- `connections/trip-wrapped/__init__.py` — `DOMAIN = "trip_wrapped"` marker.
- `connections/trip-wrapped/README.md` — user-facing IKEA page.
- `connections/trip-wrapped/docs/recipe.md` — this file.
- `connections/trip-wrapped/tests/test_connection_yml.py` — manifest honesty smoke.
- `homeassistant/packages/roamcore_trip_wrapped.yaml` (224 LOC, preserved verbatim) — the existing RoamCore-owned package that this slice WRAPS.
- `homeassistant/tools/trip_wrapped/` (Python; preserved verbatim) — the existing RoamCore-owned report-renderer tooling that this slice WRAPS.

## Cross-references

- Trip Local (the sibling trip-metric connection; today's distance/drive_time/stops feed the wrapped comparisons): `connections/trip-local/` (Wave 3 #68)
- Map dashboard (the map overlay surface; the §9.4 PNG export reuses the map tile layer): `connections/map-dashboard/` (Wave 3 #66)
- Traccar (the upstream Traccar data-source connection; the `roamcore_traccar_proxy` custom component bridges it): `connections/traccar/` (Wave 3 #12)
- Mode (the §9.4 PNG-export offline-first guard's mode-state cross-reference): `connections/mode/` (Wave 3 #61)
- Remote-access (the §9.5 html-cache-buster-param's remote-access cross-reference): `connections/remote-access/` (Wave 3 #58)
- Advanced-mode (the §9.2 needs-setup guard's confirm-flag pattern): `connections/advanced-mode/` (Wave 3 #63)
- OpenClaw JSON API (the JSON API surfaces the `rc_trip_wrapped_*` + `rc_traccar_ui_*` tiles): `connections/openclaw-api/` (Wave 3 #64)
- Leveling (the §9.4 wrapped-report's "Vehicle posture" section's leveling-jack cross-reference): `connections/leveling/` (Wave 3 #60)
- RoamCore entity naming: `docs/reference/rc-entity-naming.md` (the `trip` subsystem was added by the trip-local Wave 3 #68 sibling slice; the `rc_trip_wrapped_*` + `rc_traccar_ui_*` tiles follow the same `trip` subsystem convention)