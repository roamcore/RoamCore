# In-cab tablet dashboard (driving / arrival / lock-screen Lovelace views with ignition-aware auto-switch)

**Tier:** C (recipe)
**Category:** vehicle_obd
**Status:** recipe_published

## What this connection is

In-cab tablet dashboard — the umbrella for "mount a small tablet in the cab that shows the handful of controls and readouts you care about while driving + a richer control surface on arrival + a battery-friendly lock screen while parked" — is the in-cab-tablet-dashboard SPECIFIC subset of the broader vehicle subsystem (the `vehicle` subsystem `rc_vehicle_*` prefix is OWNED by the existing Wican Pro Wave 3 #6 connection — this slice inherits the `rc_vehicle_*` prefix from the existing Wican Pro entities and extends it with the `rc_in_cab_tablet_*` SPECIFIC subset for the dashboard view state, mirroring how time-atomic Wave 3 #55 inherits the `rc_time_*` prefix from the existing time helpers and how hvac-basics Wave 3 #49 inherits the `rc_hvac_*` prefix from heated-floors Wave 3 #44).

The single "what view is the in-cab tablet showing?" tile surfaces the currently-active view; the "is the in-cab tablet in driving mode?" binary_sensor is the safety gate (TRUE when view=`driving`); the "is the in-cab tablet in lock screen mode?" binary_sensor is the battery gate (TRUE when view=`lock_screen`); the view mode select is the manual override; the switch view now button is the one-tap manual switch.

RoamCore ships **no** native in-cab-tablet dashboard engine. We RECIPE the upstream HA Lovelace view system (a `view` config block in `ui-lovelace.yaml` / a panel view via the dashboard UI's "Add view" button / the `lovelace:` config block under `dashboard:` HA core UI configuration) + a thin RoamCore automation wrapper that runs the THREE §7 automations (ignition-on auto-switch to `arrival` view + ignition-off auto-switch to `lock_screen` view + manual override via select or button). The 8 `rc_in_cab_tablet_*` contract tiles are the vendor-neutral layer the dashboard + OpenClaw queries use; the actual view switching is done by HA's Lovelace view system + the upstream `input_select` + `input_button` + `device_tracker` integrations (RoamCore does NOT fork any of these).

## Setup recipe (one-paragraph)

1. Pick a tablet form factor (a 7-10" Android tablet mounted in the cab is the canonical RoamCore pick — battery-friendly + always-on-display capable + the HA Companion app is available on Android) and install the HA Companion app.
2. Wire the THREE operator-pickable paths (one or more of):
   - **Path A — "Driving" view.** Lovelace view YAML with view type `panel`, view icon `mdi:car`, view title `Driving`, big-button tile layout, only safe interactions (toggle exterior lights + toggle compressor + mute the cabin). Path A is the default for any van that has a tablet mounted in the cab while the operator is driving.
   - **Path B — "Arrival / Welcome" view.** Ignition-triggered view switch via an automation that watches the OBD-II `binary_sensor.rc_vehicle_ignition` from Wican Pro Wave 3 #6 OR a generic `binary_sensor.*` ignition source OR a `device_tracker.rc_location_van` state change to home zone. The arrival view shows exterior lighting + compressor + house status.
   - **Path C — "Lock screen / Always-on-display" view.** Battery-friendly low-power dashboard showing critical house status + key vehicle stats, refreshes every 60s, dimmed colors, minimal true/false states. Path C is the default for the in-cab tablet when the ignition is off and the operator is away from the van.
3. Wire the THREE §7 automations (ignition-on auto-switch to `arrival` view + ignition-off auto-switch to `lock_screen` view + manual override via the `select.rc_in_cab_tablet_view_mode` select or the `button.rc_in_cab_tablet_set_view_now` button) BEFORE first use.
4. Verify: check `sensor.rc_in_cab_tablet_active_view` reflects the current view + `binary_sensor.rc_in_cab_tablet_driving_mode_active` is TRUE when view=`driving`.

Full howto: see [`docs/recipe.md`](docs/recipe.md).

## Why tier-c, not tier-b

Tier-b would require a RoamCore-owned in-cab-tablet dashboard engine + integration code + integration tests against a real in-cab tablet bench (a 7-10" Android tablet mounted in the cab with the HA Companion app installed + a Wican Pro OBD-II reader for the ignition source + a Traccar server for the location proxy + canned fixture responses for ignition-on / ignition-off / zone-home / zone-away events). We have no operator-side in-cab-tablet bench on the CI to integration-test against (the bench requires a physical tablet in the cab + a Wican Pro device + a Traccar server + the HA Companion app). Tier-c is the honest tier: HA's Lovelace view system is upstream HA core code (not RoamCore-owned); the RoamCore wrapper is a few thin automations + a contract layer. The recipe is sound but we cannot claim one-tap automation.

The legacy catalog page (`docs/catalog/vehicle-obd/in-cab-tablet-dashboard.md`) listed "Support tier: C" with no recipe + no contract + no automations — that placeholder is now superseded by this tier-c recipe connection.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "in_cab_tablet"` marker for the audit.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded by this slice): [`docs/catalog/vehicle-obd/in-cab-tablet-dashboard.md`](../../docs/catalog/vehicle-obd/in-cab-tablet-dashboard.md)
- Wican Pro OBD-II connection (the canonical `binary_sensor.rc_vehicle_ignition` source; Wave 3 #6): `connections/wican-pro/`
- Traccar connection (the fallback `device_tracker.rc_location_van` ignition proxy; Wave 3 #36): `connections/traccar/`
- HA Companion app (the operator-phone-based `device_tracker.<phone_name>` ignition proxy): upstream integration
- Approach lights connection (the `arrival` view's exterior lighting controls; Wave 3 #52): `connections/approach-lights/`
- HVAC basics connection (the `arrival` view's heating/cooling toggles; Wave 3 #49): `connections/hvac-basics/`
- Teltonika (the always-on LTE backhaul to keep the tablet online; Wave 3 #39): `connections/teltonika/`
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`
