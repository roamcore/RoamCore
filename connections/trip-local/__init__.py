"""Trip Local (local-first trip metrics from the HA recorder) — tier-a recipe connection.

Marker-only stub. The actual surface lives in the RoamCore-owned
package at `homeassistant/packages/roamcore_trip_local.yaml` —
referenced verbatim via `install.packages:` in the connection
manifest. There is no Python-side runtime code in this folder;
the HA `command_line:` sensor + `shell_command:` integrations +
the HA `recorder:` integration are the actual surface.
"""

DOMAIN = "trip_local"