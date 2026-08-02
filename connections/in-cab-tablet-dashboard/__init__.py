"""In-cab tablet dashboard (driving / arrival / lock-screen Lovelace views
with ignition-aware auto-switch) — tier-c recipe connection.

This module is a marker-only stub. Tier-c connections don't ship native
HA integration code; they publish a recipe (docs/recipe.md) that walks
the user through installing the upstream HA Lovelace view system (a
`view` config block in `ui-lovelace.yaml` / a panel view via the
dashboard UI's "Add view" button / the `lovelace:` config block under
`dashboard:` HA core UI configuration) + wiring ONE OR MORE operator-
pickable paths (Path A "Driving" view + Path B "Arrival / Welcome"
view + Path C "Lock screen / Always-on-display" view) + adding a thin
RoamCore automation wrapper that runs the THREE §7 automations
(ignition-on auto-switch to `arrival` view + ignition-off auto-switch
to `lock_screen` view + manual override via the
`select.rc_in_cab_tablet_view_mode` select or the
`button.rc_in_cab_tablet_set_view_now` button). The recipe exposes
the resulting data via the upstream HA Lovelace view system + the
`input_select` + `input_button` + `device_tracker` integrations, then
publishes the RoamCore in-cab-tablet-dashboard contract tiles on top
(the 8 contract entities documented in connection.yml — 4 sensor
active-view + ignition-state + last-view-switch-minutes-ago + refresh-
cadence-seconds + 2 binary_sensor driving-mode-active + lock-screen-
active + 1 select view-mode + 1 button switch-view-now).

The audit + boundary CI can detect an `in-cab-tablet-dashboard/`
folder that claims to be a connection via the `DOMAIN` constant
exported here. The wizard reads the manifest + recipe at runtime.

The real per-operator in-cab-tablet-dashboard affordance path is:

    Operator-side tablet (a 7-10" Android tablet mounted in the
        cab is the canonical RoamCore pick — battery-friendly +
        always-on-display capable + the HA Companion app is
        available on Android) running the HA Companion app
        -> upstream entity (the HA Lovelace view system
           rendering the active view; the
           `select.rc_in_cab_tablet_view_mode` from the upstream
           `input_select` integration; the
           `button.rc_in_cab_tablet_set_view_now` from the
           upstream `input_button` integration)
        -> RoamCore contract layer (HA core `template:` sensor
           + binary_sensor + select + button that mirror the
           upstream Lovelace view state + the THREE §7
           automations into the 8 `rc_in_cab_tablet_*` contract
           tiles)
        -> dashboard tiles + OpenClaw queries
            ("what view is the in-cab tablet showing?", "is the
             in-cab tablet in driving mode?", "is the in-cab
             tablet in lock screen mode?", "when was the in-cab
             tablet view last switched?", "what is the in-cab
             tablet refresh cadence?", "what is the ignition
             state on the van?", "switch the in-cab tablet to
             the driving view", "switch the in-cab tablet to
             the arrival view", "switch the in-cab tablet to
             the lock screen view")

    Safety interlocks (the recipe is the contract layer; the
    automation wrappers are documented in §7):
        -> The RoamCore ignition-on auto-switch to `arrival` view
           automation is the §7.1 automation that triggers when
           the Wican Pro Wave 3 #6 `binary_sensor.rc_vehicle_
           ignition` turns on OR a generic `binary_sensor.*`
           ignition source triggers OR a `device_tracker.rc_
           location_van` state change to home zone. The arrival
           view surfaces exterior lighting + compressor + house
           status.
        -> The RoamCore ignition-off auto-switch to `lock_screen`
           view automation is the §7.2 automation that triggers
           when the Wican Pro `binary_sensor.rc_vehicle_ignition`
           turns off. The lock screen view is battery-friendly +
           shows critical house status + key vehicle stats. The
           view refreshes every 60s + uses dimmed colors +
           minimal true/false states to preserve the tablet's
           battery.
        -> The RoamCore manual override automation is the §7.3
           automation that triggers when the operator changes
           the `select.rc_in_cab_tablet_view_mode` select OR
           presses the `button.rc_in_cab_tablet_set_view_now`
           button. The manual override sets the view mode to
           `manual` so the next ignition event reverts to the
           auto-switched view (a graceful opt-out for the
           operator who wants to override the auto-switch logic
           on a one-off basis).

    Cross-references:
        -> The canonical ignition source cross-references the
           Wican Pro Wave 3 #6 connection (the canonical
           `binary_sensor.rc_vehicle_ignition` source).
        -> The fallback ignition source cross-references the
           Traccar Wave 3 #36 server (the
           `device_tracker.rc_location_van` state change to
           home zone is a reliable proxy for "we're home + the
           engine is off").
        -> The HA Companion app cross-references the upstream
           `device_tracker.<phone_name>` entity (the operator-
           phone-based ignition proxy).
        -> The arrival view's exterior lighting controls
           cross-reference the Approach lights Wave 3 #52
           connection.
        -> The arrival view's heating/cooling toggles
           cross-reference the HVAC basics Wave 3 #49
           connection.
        -> The always-on LTE backhaul cross-references the
           Teltonika Wave 3 #39 connection (the LTE router
           that keeps the tablet online).
        -> The existing Wican Pro Wave 3 #6 connection
           cross-references this slice via the
           `binary_sensor.rc_vehicle_ignition` tile (which
           the §7.1 ignition-on auto-switch to `arrival` view
           automation uses as the primary trigger).

See docs/recipe.md for the full howto (HA Lovelace view install +
Path A "Driving" view wiring + Path B "Arrival / Welcome" view
wiring + Path C "Lock screen / Always-on-display" view wiring +
the THREE §7 automations + the 8 `rc_in_cab_tablet_*` contract
tiles + the 6 §8 troubleshooting entries + privacy + tier-b
promotion outline + cross-references).
"""

DOMAIN = "in_cab_tablet"
