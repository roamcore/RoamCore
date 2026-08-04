"""Trip Wrapped (local-first route-recap HTML/JSON report) — tier-a recipe connection.

Marker-only stub. The actual surface lives in the RoamCore-owned
package at `homeassistant/packages/roamcore_trip_wrapped.yaml` (224
LOC — the `roamcore_traccar_proxy:` custom component + the 5+
`input_text.rc_traccar_*` / `input_text.rc_trip_wrapped_*` helpers
+ the 1 `input_number.rc_traccar_device_id` for the device id +
the 2 `binary_sensor.rc_trip_wrapped_latest_ready` +
`binary_sensor.rc_traccar_ui_reachable` readiness tiles + the 1
`sensor.rc_trip_wrapped_latest_status` status tile + the 1
`shell_command.rc_trip_wrapped_export` exporter) AND the
RoamCore-owned report-renderer tooling under
`homeassistant/tools/trip_wrapped/` (Python; `export.py` +
`build_wrapped.py` + `comparisons.py` + `history.py` +
`render_html.py` + `traccar_client.py` + `assets/` + `tests/`) —
referenced verbatim via `install.packages:` in the connection
manifest. There is no Python-side runtime code in this folder;
the HA `command_line:` / `shell_command:` / `input_text:` /
`input_number:` / `script:` / `binary_sensor:` / `sensor:`
integrations + the RoamCore-shipped Python exporter are the
actual surface.
"""

DOMAIN = "trip_wrapped"