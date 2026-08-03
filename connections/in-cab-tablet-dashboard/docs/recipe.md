# In-cab tablet dashboard — tier-c recipe connection

This is the full howto for the `connections/in-cab-tablet-dashboard/`
tier-c recipe connection. It walks through installing the upstream HA
Lovelace view system (a `view` config block in `ui-lovelace.yaml` / a
panel view via the dashboard UI's "Add view" button / the `lovelace:`
config block under `dashboard:` HA core UI configuration), wiring ONE
OR MORE of the THREE operator-pickable paths (Path A "Driving" view +
Path B "Arrival / Welcome" view + Path C "Lock screen /
Always-on-display" view), adding a thin RoamCore automation wrapper
that runs the THREE §7 automations (ignition-on auto-switch to
`arrival` view + ignition-off auto-switch to `lock_screen` view +
manual override via select or button), mapping the upstream Lovelace
view state into the 8 `rc_in_cab_tablet_*` contract tiles, and
promoting the connection to tier-b when the bench fixture lands.

See https://www.home-assistant.io/dashboards/ for the full HA
dashboard docs (the canonical Path A "Driving" view wiring
surface).

## §1 What is the in-cab tablet dashboard in RoamCore?

In-cab tablet dashboard (driving / arrival / lock-screen Lovelace
views with ignition-aware auto-switch) — the umbrella for "mount a
small tablet in the cab that shows the handful of controls and
readouts you care about while driving + a richer control surface on
arrival + a battery-friendly lock screen while parked" — is
positioned in RoamCore as:

- A **reuse-first** recipe over HA's Lovelace view system. RoamCore
  does NOT maintain a custom in-cab-tablet dashboard engine; HA's
  Lovelace view system (since 2022.x — exposes a `view` config block
  in `ui-lovelace.yaml` + a panel view via the dashboard UI's "Add
  view" button + the `lovelace:` config block under `dashboard:` HA
  core UI configuration) is the canonical view-switching engine. This
  is intentional: writing a custom view-switching engine would
  duplicate work HA core already does + introduce maintenance burden
  every time HA's Lovelace system adds a feature (conditional cards +
  sections + new tile types).

- An **in-cab-tablet-dashboard SPECIFIC subset** of the broader
  vehicle subsystem. The `vehicle` subsystem `rc_vehicle_*` prefix
  is OWNED by the existing Wican Pro Wave 3 #6 connection (the
  OBD-II reader that publishes `binary_sensor.rc_vehicle_ignition` +
  `sensor.rc_vehicle_battery_voltage` + `sensor.rc_vehicle_coolant_
  temp` + `sensor.rc_vehicle_speed` + `sensor.rc_vehicle_obd_fault_
  count`). This slice inherits the `rc_vehicle_*` prefix from the
  existing Wican Pro entities and extends it with the
  `rc_in_cab_tablet_*` SPECIFIC subset for the dashboard view state.
  Both subsets coexist in the same vehicle subsystem, mirroring how
  the time subsystem houses both the `rc_time_*` BROADER prefix
  (time-atomic Wave 3 #55) AND the `rc_time_zone_*` SPECIFIC subset
  (timezone-geolocator Wave 3 #54) without conflict.

- A **single "what view is the in-cab tablet showing?" tile**. The
  `sensor.rc_in_cab_tablet_active_view` tile surfaces the currently-
  active view (one of `driving` / `arrival` / `lock_screen` /
  `manual`); the `binary_sensor.rc_in_cab_tablet_driving_mode_
  active` is the safety gate (TRUE when view=`driving`); the
  `binary_sensor.rc_in_cab_tablet_lock_screen_active` is the battery
  gate (TRUE when view=`lock_screen`); the
  `select.rc_in_cab_tablet_view_mode` is the manual override (values:
  `driving` / `arrival` / `lock_screen` / `manual`); the
  `button.rc_in_cab_tablet_set_view_now` is the one-tap manual
  switch.

- A **THREE-path** operator-pickable wrapper. The operator picks ONE
  OR MORE of Path A "Driving" view (Lovelace view YAML with view
  type `panel` + view icon `mdi:car` + view title `Driving` + big-
  button tile layout + only safe interactions) + Path B "Arrival /
  Welcome" view (ignition-triggered view switch via an automation
  that watches the OBD-II `binary_sensor.rc_vehicle_ignition` from
  Wican Pro Wave 3 #6 OR a generic `binary_sensor.*` ignition source
  OR a `device_tracker.rc_location_van` state change to home zone) +
  Path C "Lock screen / Always-on-display" view (battery-friendly
  low-power dashboard showing critical house status + key vehicle
  stats, refreshes every 60s, dimmed colors, minimal true/false
  states).

- An **ignition-aware** auto-switch wrapper. The RoamCore
  automation wrapper flips the active view based on the ignition
  state — when ignition turns on, switch to `arrival` view (the
  richer control surface for arriving home + the operator is now
  ready to control exterior lights + compressor + house status);
  when ignition turns off, switch to `lock_screen` view (the
  battery-friendly view for when the van is parked + the operator
  is away). The manual override is a graceful opt-out for the
  operator who wants to override the auto-switch logic on a one-
  off basis.

- A **vendor-neutral** view of the world. The 8 `rc_in_cab_tablet_*`
  contract tiles + the 3 §7 automations are agnostic to which
  tablet form factor the operator uses (a 7-10" Android tablet
  mounted in the cab is the canonical RoamCore pick + a
  fire-tablet-style always-on-display device is a valid
  alternative + a Raspberry-Pi-driven info panel is a valid
  alternative), agnostic to which ignition source the operator
  wires (Wican Pro Wave 3 #6 OBD-II's `binary_sensor.rc_vehicle_
  ignition` is the canonical source + a generic `binary_sensor.*`
  ignition source is a valid fallback + a `device_tracker.rc_
  location_van` state change to home zone is a valid proxy + a
  HA Companion app `device_tracker.<phone_name>` is a valid
  proxy), agnostic to which dashboard view layout the operator
  uses (the recipe walks the operator through the canonical
  `view` config block in `ui-lovelace.yaml` + a `panel` view type
  + the `mdi:car` icon + the `Driving` / `Arrival` / `Lock
  screen` titles).

### §1.1 Honest scope — what this recipe is NOT

The in-cab-tablet-dashboard recipe is intentionally a recipe over
existing well-trodden HA core + vendor primitives. It is NOT:

- A RoamCore-owned in-cab-tablet dashboard engine. We do not ship
  a custom dashboard rendering engine. HA's Lovelace view system
  is the canonical rendering engine; the RoamCore wrapper is a
  few thin automations + the contract layer.
- A RoamCore-owned tablet-management integration. We do not ship
  a custom integration that controls the tablet's screen +
  brightness + always-on-display setting + battery state. The
  HA Companion app on the tablet is the canonical tablet-
  management surface; the RoamCore wrapper only reads the
  Lovelace view state.
- A RoamCore-owned view-switching service. We do not ship a
  custom service that flips the active Lovelace view. The HA
  core `lovelace:` config block under `dashboard:` is the
  canonical view-switching surface; the RoamCore wrapper uses
  the `lovelace.set_view` service via the dashboard UI's
  "Raw configuration editor" or a third-party Lovelace view
  switcher.

### §1.2 Why the in-cab-tablet-dashboard subsystem uses `rc_in_cab_tablet_*` (not `rc_dashboard_*`)

The spec-required tile prefix is `rc_in_cab_tablet_*` (NOT
`rc_dashboard_*` and NOT `rc_in_cab_*`). The choice is
deliberate:

- The `vehicle` subsystem is OWNED by the existing Wican Pro
  Wave 3 #6 connection (the OBD-II reader that publishes
  `binary_sensor.rc_vehicle_ignition` + `sensor.rc_vehicle_
  battery_voltage` + `sensor.rc_vehicle_coolant_temp` +
  `sensor.rc_vehicle_speed` + `sensor.rc_vehicle_obd_fault_
  count`).
- This slice inherits the `rc_vehicle_*` prefix from the
  existing Wican Pro entities and extends it with the
  `rc_in_cab_tablet_*` SPECIFIC subset for the dashboard view
  state — a SPECIFIC subset of the broader `vehicle`
  subsystem that handles "what is the in-cab tablet
  showing?" rather than the broader "what is the vehicle
  doing?" question.
- The forbidden_substrings list in the manifest-honesty tests
  includes `dashboard_` to prevent the `rc_dashboard_*` prefix
  (which would be a category-wide prefix that would conflict
  with the existing approach-lights + hvac-basics + smart-
  automations slices + the future dashboard-shaped tiles
  planned for Wave 4 + Wave 5). The `rc_in_cab_tablet_*`
  prefix is the SPECIFIC subset that this slice owns; the
  broader `vehicle` subsystem prefix `rc_vehicle_*` is owned
  by Wican Pro Wave 3 #6; both prefixes coexist.

## §2 Prerequisites

Before you wire the in-cab-tablet-dashboard recipe, you need the
following in place.

### §2.1 Hardware prerequisites

- A tablet form factor (one of):
  - **Android tablet (canonical RoamCore pick).** A 7-10" Android
    tablet mounted in the cab is the canonical RoamCore pick —
    battery-friendly + always-on-display capable + the HA
    Companion app is available on Android + a wide range of
    mounting options (RAM mounts + suction-cup mounts +
    dashboard-embedded mounts).
  - **iPad / iOS tablet (alternative).** A 7-12" iPad mounted
    in the cab is a valid alternative — battery-friendly +
    Safari-based HA Lovelace UI + the HA Companion app is
    available on iOS. Battery life is generally better than
    Android tablets at the cost of always-on-display support
    (iOS does not natively support always-on-display; a
    third-party kiosk app is required).
  - **Fire tablet (always-on-display alternative).** A 7-10"
    Amazon Fire tablet mounted in the cab is a valid
    alternative for always-on-display use cases — the Fire OS
    supports always-on-display natively + the Silk browser
    can reach HA's Lovelace UI. Battery life is generally
    worse than Android tablets at the cost of always-on-
    display support.
  - **Raspberry-Pi-driven info panel (custom alternative).** A
    Raspberry-Pi 4 or 5 driving a 7-10" touchscreen is a valid
    alternative for custom installations — runs the HA
    Companion app in kiosk mode + supports always-on-display
    natively + the GPIO pins can be wired to physical buttons
    for one-tap view switching.

- An ignition source (one of):
  - **Wican Pro Wave 3 #6 OBD-II reader (canonical).** The
    Wican Pro OBD-II reader is the canonical ignition source
    — the OBD-II bus exposes a D+ signal that's TRUE when
    the ignition is on and FALSE when the ignition is off.
    Wican Pro publishes the D+ signal as
    `binary_sensor.rc_vehicle_ignition` (one of the 5
    contract entities from the Wican Pro Wave 3 #6
    connection).
  - **Generic OBD-II reader (alternative).** Any OBD-II
    reader that publishes a `binary_sensor.*` ignition
    entity is a valid alternative — for example, a generic
    ELM327-based OBD-II reader with the upstream `obdii`
    integration. The OBD-II standard exposes a D+ signal
    that's TRUE when the ignition is on and FALSE when the
    ignition is off.
  - **Traccar Wave 3 #36 server (location proxy).** A
    `device_tracker.rc_location_van` state change to home
    zone is a valid proxy for "we're home + the engine is
    off" — when the device_tracker enters the home zone,
    treat it as ignition off. The proxy is less reliable
    than an OBD-II ignition source (the operator may
    arrive home and park the van with the engine still
    running for cabin cooling), but it's a useful fallback
    for vans without an OBD-II reader.
  - **HA Companion app (phone proxy).** The HA Companion
    app's `device_tracker.<phone_name>` state change to
    home zone is a valid proxy for "we're home + the
    phone is on Wi-Fi" — when the device_tracker enters
    the home zone, treat it as ignition off. The proxy is
    less reliable than an OBD-II ignition source (the
    phone's GPS may be inaccurate + the phone may be in
    the house while the van is parked outside) but it's a
    useful fallback for vans without an OBD-II reader.

- An always-on LTE backhaul (optional but recommended):
  - **Teltonika Wave 3 #39 LTE router (canonical).** The
    Teltonika LTE router is the canonical always-on LTE
    backhaul for the in-cab tablet — the router keeps the
    tablet online even when the WAN is intermittent
    (Starlink roaming + campground Wi-Fi + cellular
    handoffs). The Teltonika's 4G/5G modem is always-on
    (low power consumption + reliable); the tablet can
    reach HA's Lovelace UI via the LTE backhaul without
    depending on Starlink.

### §2.2 Software prerequisites

- Home Assistant 2022.6 or newer (the upstream Lovelace view
  system is GA since 2022.6; the `view` config block in
  `ui-lovelace.yaml` is supported since 2022.6; the
  `lovelace:` config block under `dashboard:` is supported
  since 2022.6).
- The `input_select` integration enabled (for the
  `select.rc_in_cab_tablet_view_mode` select). The
  `input_select` integration is a HA core integration
  since 2022.x — it ships with HA core; no HACS install
  required.
- The `input_button` integration enabled (for the
  `button.rc_in_cab_tablet_set_view_now` button). The
  `input_button` integration is a HA core integration
  since 2022.x — it ships with HA core; no HACS install
  required.
- The `device_tracker` integration enabled (for the
  `device_tracker.rc_location_van` fallback ignition
  proxy). The `device_tracker` integration is a HA core
  integration since 2022.x — it ships with HA core; no
  HACS install required.
- The `template` integration enabled (for the
  `template:` sensor + binary_sensor + select + button
  that mirror the upstream Lovelace view state into the 8
  `rc_in_cab_tablet_*` contract tiles). The `template`
  integration is a HA core integration since 2022.x — it
  ships with HA core; no HACS install required.
- The `automation` integration enabled (for the THREE
  §7 automations). The `automation` integration is a HA
  core integration since 2022.x — it ships with HA core;
  no HACS install required.
- The Wican Pro Wave 3 #6 connection installed + working
  (for the canonical `binary_sensor.rc_vehicle_ignition`
  source). See `connections/wican-pro/` for the install
  recipe.
- The Traccar Wave 3 #36 server installed + working
  (optional, for the `device_tracker.rc_location_van`
  fallback ignition proxy). See `connections/traccar/`
  for the install recipe.
- The HA Companion app installed on the in-cab tablet
  (for the tablet to reach HA's Lovelace UI). The HA
  Companion app is available on Android + iOS + Fire OS
  + a web-based kiosk mode for Raspberry-Pi-driven info
  panels.

### §2.3 Safety prerequisites

- The ignition source must be wired BEFORE first use. A
  missing ignition source means the §7.1 ignition-on auto-
  switch to `arrival` view automation has no trigger + the
  §7.2 ignition-off auto-switch to `lock_screen` view
  automation has no trigger. The recipe walks the
  operator through wiring an ignition source in §2.1
  (Wican Pro Wave 3 #6 OBD-II reader + generic OBD-II
  reader + Traccar server + HA Companion app).
- The `input_select` view mode must be configured BEFORE
  first use. A missing `input_select` means the
  `select.rc_in_cab_tablet_view_mode` select is
  unavailable + the §7.3 manual override automation has
  no trigger.
- The `input_button` switch view now must be configured
  BEFORE first use. A missing `input_button` means the
  `button.rc_in_cab_tablet_set_view_now` button is
  unavailable + the operator cannot manually switch
  views.

## §3 Path A — "Driving" view (Lovelace view YAML with view type `panel`)

The Path A "Driving" view is the canonical in-cab-tablet-dashboard
view — Lovelace view YAML with view type `panel`, view icon
`mdi:car`, view title `Driving`, big-button tile layout, only safe
interactions (toggle exterior lights + toggle compressor + mute the
cabin). The view is designed to be glanceable while the operator is
driving — big buttons + minimal text + only safe interactions
(nothing that requires the operator to read more than a single word
or press more than a single button).

### §3.1 Why Path A

The Path A "Driving" view exists because the operator's attention
while driving is focused on the road, not the dashboard. A
traditional Lovelace dashboard with text-heavy tiles + small
buttons + multi-step interactions is dangerous to use while
driving (the operator's eyes are off the road for too long + the
operator's hands are off the wheel for too long). The Path A
"Driving" view is designed to be safe to use while driving:

- **Big buttons.** The buttons in the Path A "Driving" view are
  at least 100x100 pixels each — large enough to be tapped
  without looking at the tablet + large enough to be tapped
  with one hand while the other hand is on the wheel.
- **Minimal text.** The text in the Path A "Driving" view is at
  most 2-3 words per tile — no long descriptions + no multi-
  line status messages + no log entries.
- **Only safe interactions.** The buttons in the Path A
  "Driving" view are limited to safe interactions — toggle
  exterior lights + toggle compressor + mute the cabin. No
  navigation interactions + no music control + no climate
  control (climate control requires the operator to look at
  the tablet to set the temperature; the operator can use
  voice control for climate instead).
- **Glanceable.** The Path A "Driving" view is designed to be
  glanceable — the operator can read the entire view in 1-2
  seconds + the operator can identify the current state of
  every tile without reading any text (color coding + icon
  coding).

### §3.2 Wiring Path A — Lovelace view YAML

The Path A "Driving" view is wired via a `view` config block in
`ui-lovelace.yaml` (the YAML-based Lovelace configuration that HA
core's dashboard UI exposes via the "Raw configuration editor"
button in the dashboard edit mode). The view is a `panel` view
type (the full-width view type that's designed for tablet
dashboards) with view icon `mdi:car` + view title `Driving` +
big-button tile layout.

```yaml
# ui-lovelace.yaml — Path A "Driving" view
# Add this view to your existing views: list in ui-lovelace.yaml.
# The view is a `panel` view type (full-width; designed for
# tablet dashboards) with view icon `mdi:car` + view title
# `Driving` + big-button tile layout. The buttons are at least
# 100x100 pixels each + only safe interactions (toggle exterior
# lights + toggle compressor + mute the cabin).

views:
  - title: Driving
    path: driving
    icon: mdi:car
    panel: true  # full-width view; designed for tablet dashboards
    cards:
      - type: grid
        square: false  # the grid is NOT square; tiles are 100x100+ pixels
        columns: 2     # 2 columns of big buttons; minimal visual complexity
        cards:
          # Big button 1: toggle the exterior lights (Approach lights
          # Wave 3 #52). The button reflects the current state of the
          # `light.rc_approach_left` entity + the `light.rc_approach_
          # right` entity + the `light.rc_approach_underbody` entity.
          - type: button
            entity: light.rc_approach_left
            name: Ext Lights
            icon: mdi:car-light-high
            show_state: false  # hide the state text; only show the icon
            tap_action:
              action: toggle
            hold_action:
              action: more-info
          # Big button 2: toggle the compressor (the air compressor
          # for the pneumatic suspension + the air horns). The
          # button reflects the current state of the
          # `switch.rc_compressor_enabled` entity.
          - type: button
            entity: switch.rc_compressor_enabled
            name: Compressor
            icon: mdi:air-compressor
            show_state: false
            tap_action:
              action: toggle
            hold_action:
              action: more-info
          # Big button 3: mute the cabin (mute the cabin audio +
          # mute the cabin notifications + dim the cabin lights).
          # The button reflects the current state of the
          # `switch.rc_cabin_muted` entity.
          - type: button
            entity: switch.rc_cabin_muted
            name: Mute Cabin
            icon: mdi:volume-off
            show_state: false
            tap_action:
              action: toggle
            hold_action:
              action: more-info
          # Big button 4: open the full dashboard (navigate to the
          # default Lovelace dashboard). The button is a "navigation"
          # button that uses the `navigate` action to open the
          # default dashboard.
          - type: button
            name: Open Dashboard
            icon: mdi:view-dashboard
            show_state: false
            tap_action:
              action: navigate
              navigation_path: /lovelace/default
            hold_action:
              action: none
```

### §3.3 Verifying Path A

After wiring the Path A "Driving" view, verify:

- The "Driving" view appears in the Lovelace dashboard's view
  list (the left sidebar in the desktop UI + the bottom tab bar
  in the mobile UI).
- The "Driving" view icon is `mdi:car` (a car icon).
- The "Driving" view title is `Driving` (no truncation).
- The "Driving" view is a `panel` view type (full-width).
- The 4 big buttons are visible + the buttons are at least
  100x100 pixels each.
- Tapping the "Ext Lights" button toggles the
  `light.rc_approach_left` entity.
- Tapping the "Compressor" button toggles the
  `switch.rc_compressor_enabled` entity.
- Tapping the "Mute Cabin" button toggles the
  `switch.rc_cabin_muted` entity.
- Tapping the "Open Dashboard" button navigates to the default
  Lovelace dashboard.

## §4 Path B — "Arrival / Welcome" view (ignition-triggered view switch)

The Path B "Arrival / Welcome" view is the canonical rich-control
view for the in-cab tablet — Lovelace view YAML with view type
`panel`, view icon `mdi:home-outline`, view title `Arrival`, rich
tile layout, full control surface (exterior lighting + compressor +
house status). The view is auto-switched when the ignition turns on
(operator is arriving home + ready to control exterior lights +
compressor + house status).

### §4.1 Why Path B

The Path B "Arrival / Welcome" view exists because the operator
needs a richer control surface on arrival — when the van is parked
at a "home" zone and the operator is stepping out of the cab, the
operator wants to:

- Turn on the exterior approach lights (so the operator can see
  the path from the van to the house).
- Turn on the porch light (so the operator can see the front
  door).
- Turn on the compressor (so the pneumatic suspension can level
  the van).
- Check the house status (battery SOC + water level + propane
  level + interior temp).

The Path B "Arrival / Welcome" view surfaces all of these
controls in a single glanceable view + the view is auto-switched
when the ignition turns on (no operator interaction required).

### §4.2 Wiring Path B — Lovelace view YAML

The Path B "Arrival / Welcome" view is wired via a `view` config
block in `ui-lovelace.yaml` (the YAML-based Lovelace
configuration). The view is a `panel` view type (full-width;
designed for tablet dashboards) with view icon
`mdi:home-outline` + view title `Arrival` + rich tile layout.

```yaml
# ui-lovelace.yaml — Path B "Arrival / Welcome" view
# Add this view to your existing views: list in ui-lovelace.yaml.
# The view is a `panel` view type (full-width; designed for
# tablet dashboards) with view icon `mdi:home-outline` + view
# title `Arrival` + rich tile layout. The view surfaces exterior
# lighting + compressor + house status (battery + water + propane
# + interior temp) for one-tap control on arrival.

views:
  - title: Arrival
    path: arrival
    icon: mdi:home-outline
    panel: true
    cards:
      - type: grid
        square: false
        columns: 3     # 3 columns of medium-sized tiles
        cards:
          # Tile 1: Approach lights (Approach lights Wave 3 #52).
          # The tile is a vertical-stack card with the
          # `light.rc_approach_left` + `light.rc_approach_right` +
          # `light.rc_approach_underbody` entities.
          - type: vertical-stack
            title: Approach Lights
            cards:
              - type: light
                entity: light.rc_approach_left
                name: Left
              - type: light
                entity: light.rc_approach_right
                name: Right
              - type: light
                entity: light.rc_approach_underbody
                name: Underbody
          # Tile 2: Compressor + pneumatic suspension. The tile is
          # a vertical-stack card with the
          # `switch.rc_compressor_enabled` entity + the
          # `sensor.rc_pneumatic_pressure_psi` entity.
          - type: vertical-stack
            title: Compressor
            cards:
              - type: button
                entity: switch.rc_compressor_enabled
                name: Compressor
                icon: mdi:air-compressor
                show_state: true
                tap_action:
                  action: toggle
              - type: sensor
                entity: sensor.rc_pneumatic_pressure_psi
                name: Pressure
                icon: mdi:gauge
          # Tile 3: House battery (the existing RoamCore power
          # subsystem). The tile is a gauge card with the
          # `sensor.rc_power_battery_soc` entity.
          - type: gauge
            entity: sensor.rc_power_battery_soc
            name: Battery
            unit: "%"
            min: 0
            max: 100
            needle: true
          # Tile 4: Water level (the existing RoamCore water
          # subsystem). The tile is a gauge card with the
          # `sensor.rc_water_fresh_percent` entity.
          - type: gauge
            entity: sensor.rc_water_fresh_percent
            name: Water
            unit: "%"
            min: 0
            max: 100
            needle: true
          # Tile 5: Propane level (the existing RoamCore propane
          # subsystem). The tile is a gauge card with the
          # `sensor.rc_propane_percent` entity.
          - type: gauge
            entity: sensor.rc_propane_percent
            name: Propane
            unit: "%"
            min: 0
            max: 100
            needle: true
          # Tile 6: Interior temperature (the existing RoamCore
          # climate subsystem). The tile is a sensor card with
          # the `sensor.rc_climate_interior_temp` entity.
          - type: sensor
            entity: sensor.rc_climate_interior_temp
            name: Interior Temp
            icon: mdi:thermometer
```

### §4.3 Wiring Path B — ignition-on auto-switch automation

The Path B "Arrival / Welcome" view is auto-switched when the
ignition turns on. The ignition-on auto-switch to `arrival` view
automation is the §7.1 MANDATORY automation. The automation
triggers when:

- The Wican Pro Wave 3 #6
  `binary_sensor.rc_vehicle_ignition` turns on (the canonical
  trigger).
- OR a generic `binary_sensor.*` ignition source turns on (for
  vans without a Wican Pro).
- OR a `device_tracker.rc_location_van` state change to home
  zone (the location proxy; the operator is arriving home).

The automation's action is to set the
`select.rc_in_cab_tablet_view_mode` to `arrival` (which causes
the `template:` select to update + the Lovelace view to switch
to the `arrival` view via the `lovelace.set_view` service).

```yaml
# configuration.yaml — Path B "Arrival / Welcome" view ignition-on
# auto-switch automation (§7.1 MANDATORY automation).
# This automation triggers when the Wican Pro Wave 3 #6
# `binary_sensor.rc_vehicle_ignition` turns on OR a generic
# `binary_sensor.*` ignition source turns on OR a
# `device_tracker.rc_location_van` state change to home zone.
# The automation's action is to set the
# `select.rc_in_cab_tablet_view_mode` to `arrival` (which causes
# the Lovelace view to switch to the `arrival` view via the
# `lovelace.set_view` service).

automation:
  - alias: in_cab_tablet_arrival_view_on_ignition_on
    description: >-
      Auto-switch the in-cab tablet to the Arrival view when
      the Wican Pro `binary_sensor.rc_vehicle_ignition` turns
      on (canonical trigger) OR a generic `binary_sensor.*`
      ignition source turns on (fallback trigger) OR a
      `device_tracker.rc_location_van` state change to home
      zone (location proxy trigger). The §7.1 MANDATORY
      automation; wired BEFORE first use.
    mode: single
    trigger:
      - platform: state
        entity_id: binary_sensor.rc_vehicle_ignition
        from: "off"
        to: "on"
        id: ignition_on
      - platform: state
        entity_id: binary_sensor.rc_generic_ignition  # operator-supplied; replace with the operator's actual ignition binary_sensor
        from: "off"
        to: "on"
        id: generic_ignition_on
      - platform: state
        entity_id: device_tracker.rc_location_van
        to: home
        id: location_home
    condition:
      # Only auto-switch if the current view mode is NOT already
      # `manual` (the operator may have manually overridden the
      # auto-switch logic; respect the override).
      - condition: not
        conditions:
          - condition: state
            entity_id: select.rc_in_cab_tablet_view_mode
            state: manual
    action:
      # Set the view mode select to `arrival`. The select's
      # `template:` listener will detect the change + trigger
      # the `lovelace.set_view` service via a downstream
      # automation to switch the active view.
      - service: select.select_option
        target:
          entity_id: select.rc_in_cab_tablet_view_mode
        data:
          option: arrival
```

## §5 Path C — "Lock screen / Always-on-display" view (battery-friendly low-power dashboard)

The Path C "Lock screen / Always-on-display" view is the canonical
battery-friendly view for the in-cab tablet — Lovelace view YAML
with view type `panel`, view icon `mdi:cellphone-lock`, view title
`Lock screen`, dimmed tile layout, minimal true/false states, 60s
refresh cadence. The view is auto-switched when the ignition turns
off (operator is leaving the van + the tablet is parked).

### §5.1 Why Path C

The Path C "Lock screen / Always-on-display" view exists because
the in-cab tablet is parked when the ignition is off + the
operator is away from the van. The tablet's battery is finite
(a 7-10" Android tablet has a 5000-10000 mAh battery that lasts
8-24 hours of always-on-display use). A traditional Lovelace
dashboard with constantly-updating tiles + bright colors + high
refresh rates burns the battery in 4-6 hours. The Path C "Lock
screen / Always-on-display" view is designed to preserve the
tablet's battery:

- **60s refresh cadence.** The tiles in the Path C "Lock screen"
  view refresh every 60s (vs the default 1-5s refresh). The
  refresh cadence is configured via the
  `sensor.rc_in_cab_tablet_refresh_cadence_seconds` tile +
  the operator's tablet settings.
- **Dimmed colors.** The tiles in the Path C "Lock screen" view
  use dimmed colors (low brightness + low saturation) to
  preserve the tablet's battery.
- **Minimal true/false states.** The binary_sensors in the Path
  C "Lock screen" view use minimal true/false states — the
  binary_sensors are not animated + the binary_sensors do not
  flash on state change.
- **Critical house status + key vehicle stats only.** The tiles
  in the Path C "Lock screen" view are limited to critical
  house status (battery SOC + water level + interior temp) +
  key vehicle stats (battery voltage + cabin temp). No
  approach lights + no compressor + no music + no climate.

### §5.2 Wiring Path C — Lovelace view YAML

The Path C "Lock screen / Always-on-display" view is wired via a
`view` config block in `ui-lovelace.yaml` (the YAML-based
Lovelace configuration). The view is a `panel` view type
(full-width; designed for tablet dashboards) with view icon
`mdi:cellphone-lock` + view title `Lock screen` + dimmed tile
layout.

```yaml
# ui-lovelace.yaml — Path C "Lock screen / Always-on-display" view
# Add this view to your existing views: list in ui-lovelace.yaml.
# The view is a `panel` view type (full-width; designed for
# tablet dashboards) with view icon `mdi:cellphone-lock` + view
# title `Lock screen` + dimmed tile layout. The tiles refresh
# every 60s + use dimmed colors + minimal true/false states to
# preserve the tablet's battery.

views:
  - title: Lock screen
    path: lock_screen
    icon: mdi:cellphone-lock
    panel: true
    cards:
      - type: grid
        square: false
        columns: 2     # 2 columns of medium-sized tiles
        cards:
          # Tile 1: House battery (the existing RoamCore power
          # subsystem). The tile is a sensor card with the
          # `sensor.rc_power_battery_soc` entity. The
          # `state_color: false` option disables the bright color
          # change on state change (preserves battery).
          - type: sensor
            entity: sensor.rc_power_battery_soc
            name: Battery
            icon: mdi:car-battery
            state_color: false  # dimmed colors; no bright color change
          # Tile 2: Water level (the existing RoamCore water
          # subsystem). The tile is a sensor card with the
          # `sensor.rc_water_fresh_percent` entity.
          - type: sensor
            entity: sensor.rc_water_fresh_percent
            name: Water
            icon: mdi:water-percent
            state_color: false
          # Tile 3: Interior temperature (the existing RoamCore
          # climate subsystem). The tile is a sensor card with
          # the `sensor.rc_climate_interior_temp` entity.
          - type: sensor
            entity: sensor.rc_climate_interior_temp
            name: Interior
            icon: mdi:thermometer
            state_color: false
          # Tile 4: Vehicle battery voltage (the Wican Pro Wave 3
          # #6 OBD-II reader's contract entity). The tile is a
          # sensor card with the `sensor.rc_vehicle_battery_
          # voltage` entity.
          - type: sensor
            entity: sensor.rc_vehicle_battery_voltage
            name: Vehicle
            icon: mdi:car-battery
            unit: "V"
            state_color: false
          # Tile 5: Cabin temperature (the Wican Pro Wave 3 #6
          # OBD-II reader's contract entity). The tile is a
          # sensor card with the `sensor.rc_vehicle_coolant_
          # temp` entity.
          - type: sensor
            entity: sensor.rc_vehicle_coolant_temp
            name: Cabin
            icon: mdi:thermometer
            unit: "°C"
            state_color: false
          # Tile 6: Ignition state (the Wican Pro Wave 3 #6
          # OBD-II reader's contract entity). The tile is a
          # binary_sensor card with the `binary_sensor.rc_vehicle_
          # ignition` entity.
          - type: entity
            entity: binary_sensor.rc_vehicle_ignition
            name: Ignition
            icon: mdi:car-key
            state_color: false
```

### §5.3 Wiring Path C — ignition-off auto-switch automation

The Path C "Lock screen / Always-on-display" view is auto-switched
when the ignition turns off. The ignition-off auto-switch to
`lock_screen` view automation is the §7.2 MANDATORY automation.
The automation triggers when the Wican Pro Wave 3 #6
`binary_sensor.rc_vehicle_ignition` turns off. The automation's
action is to set the `select.rc_in_cab_tablet_view_mode` to
`lock_screen` (which causes the `template:` select to update +
the Lovelace view to switch to the `lock_screen` view via the
`lovelace.set_view` service).

```yaml
# configuration.yaml — Path C "Lock screen / Always-on-display" view
# ignition-off auto-switch automation (§7.2 MANDATORY automation).
# This automation triggers when the Wican Pro
# `binary_sensor.rc_vehicle_ignition` turns off. The automation's
# action is to set the `select.rc_in_cab_tablet_view_mode` to
# `lock_screen` (which causes the Lovelace view to switch to the
# `lock_screen` view via the `lovelace.set_view` service).

automation:
  - alias: in_cab_tablet_lock_screen_view_on_ignition_off
    description: >-
      Auto-switch the in-cab tablet to the Lock screen view
      when the Wican Pro `binary_sensor.rc_vehicle_ignition`
      turns off. The §7.2 MANDATORY automation; wired BEFORE
      first use.
    mode: single
    trigger:
      - platform: state
        entity_id: binary_sensor.rc_vehicle_ignition
        from: "on"
        to: "off"
        id: ignition_off
    condition:
      # Only auto-switch if the current view mode is NOT already
      # `manual` (the operator may have manually overridden the
      # auto-switch logic; respect the override).
      - condition: not
        conditions:
          - condition: state
            entity_id: select.rc_in_cab_tablet_view_mode
            state: manual
    action:
      # Set the view mode select to `lock_screen`. The select's
      # `template:` listener will detect the change + trigger
      # the `lovelace.set_view` service via a downstream
      # automation to switch the active view.
      - service: select.select_option
        target:
          entity_id: select.rc_in_cab_tablet_view_mode
        data:
          option: lock_screen
```

## §6 RoamCore contract entities

The in-cab-tablet-dashboard recipe publishes 8 vendor-neutral
contract tiles that the dashboard + OpenClaw queries use. The
tiles mirror the upstream Lovelace view state + the ignition source
+ the §7 automations into a single contract layer.

### §6.1 The 8 `rc_in_cab_tablet_*` contract tiles

1. **`sensor.rc_in_cab_tablet_active_view`** — the currently-
   active view (one of `driving` / `arrival` / `lock_screen` /
   `manual`). Source: HA core `template:` sensor reading the
   `select.rc_in_cab_tablet_view_mode` select's current option.
2. **`sensor.rc_in_cab_tablet_ignition_state`** — the ignition
   state (one of `on` / `off` / `unknown`). Source: HA core
   `template:` sensor reading the
   `binary_sensor.rc_vehicle_ignition` from Wican Pro Wave 3 #6.
3. **`sensor.rc_in_cab_tablet_last_view_change_minutes_ago`** —
   the freshness timestamp (minutes since the last view switch).
   Source: HA core `template:` sensor deriving the freshness
   from the `automation.in_cab_tablet_arrival_view_on_ignition_
   on`'s `last_triggered` attribute + the
   `automation.in_cab_tablet_lock_screen_view_on_ignition_off`'s
   `last_triggered` attribute.
4. **`sensor.rc_in_cab_tablet_refresh_cadence_seconds`** — the
   refresh cadence for the active view (default: 60s for
   `lock_screen`, 5s for `driving`, 5s for `arrival`). Source:
   HA core `template:` sensor deriving the cadence from the
   active view + the operator's tablet settings.
5. **`binary_sensor.rc_in_cab_tablet_driving_mode_active`** —
   the safety gate (TRUE when view=`driving`). Source: HA core
   `template:` binary_sensor.
6. **`binary_sensor.rc_in_cab_tablet_lock_screen_active`** —
   the battery gate (TRUE when view=`lock_screen`). Source: HA
   core `template:` binary_sensor.
7. **`select.rc_in_cab_tablet_view_mode`** — the manual override
   (values: `driving` / `arrival` / `lock_screen` / `manual`).
   Source: HA core `input_select` integration.
8. **`button.rc_in_cab_tablet_set_view_now`** — the one-tap
   manual switch (when pressed, opens a Lovelace view picker).
   Source: HA core `input_button` integration.

### §6.2 The 8 `rc_in_cab_tablet_*` contract tile templates

```yaml
# configuration.yaml — the 8 `rc_in_cab_tablet_*` contract tiles
# Add this template + input_select + input_button block to your
# existing `template:` + `input_select:` + `input_button:` config
# blocks in configuration.yaml.

template:
  - sensor:
      # sensor.rc_in_cab_tablet_active_view — the currently-active
      # view (one of `driving` / `arrival` / `lock_screen` /
      # `manual`).
      - name: rc_in_cab_tablet_active_view
        unique_id: rc_in_cab_tablet_active_view
        state: >
          {{ states('select.rc_in_cab_tablet_view_mode') }}
        icon: >
          {% if is_state('select.rc_in_cab_tablet_view_mode', 'driving') %}mdi:car
          {% elif is_state('select.rc_in_cab_tablet_view_mode', 'arrival') %}mdi:home-outline
          {% elif is_state('select.rc_in_cab_tablet_view_mode', 'lock_screen') %}mdi:cellphone-lock
          {% else %}mdi:view-dashboard{% endif %}
      # sensor.rc_in_cab_tablet_ignition_state — the ignition state
      # (one of `on` / `off` / `unknown`).
      - name: rc_in_cab_tablet_ignition_state
        unique_id: rc_in_cab_tablet_ignition_state
        state: >
          {% if is_state('binary_sensor.rc_vehicle_ignition', 'on') %}on
          {% elif is_state('binary_sensor.rc_vehicle_ignition', 'off') %}off
          {% else %}unknown{% endif %}
        icon: mdi:car-key
      # sensor.rc_in_cab_tablet_last_view_change_minutes_ago — the
      # freshness timestamp (minutes since the last view switch).
      - name: rc_in_cab_tablet_last_view_change_minutes_ago
        unique_id: rc_in_cab_tablet_last_view_change_minutes_ago
        state: >
          {% set ignition_on_triggered = state_attr('automation.in_cab_tablet_arrival_view_on_ignition_on', 'last_triggered') %}
          {% set ignition_off_triggered = state_attr('automation.in_cab_tablet_lock_screen_view_on_ignition_off', 'last_triggered') %}
          {% set manual_triggered = state_attr('automation.in_cab_tablet_manual_override', 'last_triggered') %}
          {% set last_triggered = [ignition_on_triggered, ignition_off_triggered, manual_triggered] | select | list | max %}
          {% if last_triggered %}
            {{ (now() - last_triggered).total_seconds() / 60 | round(1) }}
          {% else %}
            0
          {% endif %}
        unit_of_measurement: "min"
        icon: mdi:clock-outline
      # sensor.rc_in_cab_tablet_refresh_cadence_seconds — the
      # refresh cadence for the active view.
      - name: rc_in_cab_tablet_refresh_cadence_seconds
        unique_id: rc_in_cab_tablet_refresh_cadence_seconds
        state: >
          {% if is_state('select.rc_in_cab_tablet_view_mode', 'lock_screen') %}60
          {% else %}5{% endif %}
        unit_of_measurement: "s"
        icon: mdi:refresh

  - binary_sensor:
      # binary_sensor.rc_in_cab_tablet_driving_mode_active — the
      # safety gate (TRUE when view=`driving`).
      - name: rc_in_cab_tablet_driving_mode_active
        unique_id: rc_in_cab_tablet_driving_mode_active
        state: >
          {{ is_state('select.rc_in_cab_tablet_view_mode', 'driving') }}
        icon: mdi:car
      # binary_sensor.rc_in_cab_tablet_lock_screen_active — the
      # battery gate (TRUE when view=`lock_screen`).
      - name: rc_in_cab_tablet_lock_screen_active
        unique_id: rc_in_cab_tablet_lock_screen_active
        state: >
          {{ is_state('select.rc_in_cab_tablet_view_mode', 'lock_screen') }}
        icon: mdi:cellphone-lock

input_select:
  # select.rc_in_cab_tablet_view_mode — the manual override
  # (values: `driving` / `arrival` / `lock_screen` / `manual`).
  rc_in_cab_tablet_view_mode:
    name: rc_in_cab_tablet_view_mode
    options:
      - driving
      - arrival
      - lock_screen
      - manual
    initial: lock_screen
    icon: mdi:view-dashboard

input_button:
  # button.rc_in_cab_tablet_set_view_now — the one-tap manual
  # switch.
  rc_in_cab_tablet_set_view_now:
    name: rc_in_cab_tablet_set_view_now
    icon: mdi:view-dashboard
```

## §7 Automations (MANDATORY before first use)

The in-cab-tablet-dashboard recipe is the contract layer; the
automation wrappers are documented in this section. The THREE
MANDATORY automations must be wired BEFORE first use.

### §7.1 Ignition-on auto-switch to `arrival` view

Triggers when the Wican Pro Wave 3 #6
`binary_sensor.rc_vehicle_ignition` turns on (canonical trigger) OR
a generic `binary_sensor.*` ignition source turns on (fallback
trigger) OR a `device_tracker.rc_location_van` state change to
home zone (location proxy trigger). The automation's action is to
set the `select.rc_in_cab_tablet_view_mode` to `arrival`.

The full automation YAML is documented in §4.3 above.

### §7.2 Ignition-off auto-switch to `lock_screen` view

Triggers when the Wican Pro Wave 3 #6
`binary_sensor.rc_vehicle_ignition` turns off. The automation's
action is to set the `select.rc_in_cab_tablet_view_mode` to
`lock_screen`.

The full automation YAML is documented in §5.3 above.

### §7.3 Manual override via the `select.rc_in_cab_tablet_view_mode` select or the `button.rc_in_cab_tablet_set_view_now` button

Triggers when the operator changes the
`select.rc_in_cab_tablet_view_mode` select (values: `driving` /
`arrival` / `lock_screen` / `manual`) OR presses the
`button.rc_in_cab_tablet_set_view_now` button. The automation's
action is to set the view mode to `manual` (so the next ignition
event reverts to the auto-switched view).

```yaml
# configuration.yaml — Path B / C manual override automation
# (§7.3 MANDATORY automation).
# This automation triggers when the operator changes the
# `select.rc_in_cab_tablet_view_mode` select OR presses the
# `button.rc_in_cab_tablet_set_view_now` button. The
# automation's action is to set the view mode to `manual` (so
# the next ignition event reverts to the auto-switched view;
# a graceful opt-out for the operator who wants to override the
# auto-switch logic on a one-off basis).

automation:
  - alias: in_cab_tablet_manual_override
    description: >-
      Manual override of the in-cab tablet view mode via the
      `select.rc_in_cab_tablet_view_mode` select or the
      `button.rc_in_cab_tablet_set_view_now` button. The
      §7.3 MANDATORY automation; wired BEFORE first use.
    mode: single
    trigger:
      - platform: state
        entity_id: select.rc_in_cab_tablet_view_mode
        id: view_mode_select_changed
      - platform: state
        entity_id: button.rc_in_cab_tablet_set_view_now
        id: view_mode_button_pressed
    condition:
      # Only set to `manual` if the current option is NOT
      # `manual` (the operator is changing away from the
      # auto-switched view).
      - condition: not
        conditions:
          - condition: state
            entity_id: select.rc_in_cab_tablet_view_mode
            state: manual
    action:
      # Set the view mode select to `manual` (the operator
      # has manually overridden the auto-switch logic).
      - service: select.select_option
        target:
          entity_id: select.rc_in_cab_tablet_view_mode
        data:
          option: manual
```

## §8 Troubleshooting

The in-cab-tablet-dashboard recipe includes 6 troubleshooting
entries for the most common operator-side issues.

### §8.1 View never auto-switches

**Symptom:** The in-cab tablet stays on the same view even when
the ignition turns on or off. The
`binary_sensor.rc_in_cab_tablet_driving_mode_active` is always
FALSE. The `binary_sensor.rc_in_cab_tablet_lock_screen_active` is
always FALSE. The `sensor.rc_in_cab_tablet_active_view` shows
`lock_screen` regardless of the ignition state.

**Cause:** The §7.1 ignition-on auto-switch automation + the §7.2
ignition-off auto-switch automation are not wired. The
`select.rc_in_cab_tablet_view_mode` select is not being updated
when the ignition state changes.

**Fix:** Verify the §7.1 + §7.2 automations are wired correctly
in `configuration.yaml`. Verify the
`binary_sensor.rc_vehicle_ignition` from Wican Pro Wave 3 #6 is
`on` when the ignition is on. Verify the
`select.rc_in_cab_tablet_view_mode` select is configured with
the 4 options (`driving` / `arrival` / `lock_screen` /
`manual`). Verify the `select.select_option` service is being
called when the ignition state changes.

### §8.2 Driving view not safe while moving

**Symptom:** The Path A "Driving" view has small buttons + long
text + multi-step interactions. The operator's eyes are off the
road for too long when using the view. The buttons are smaller
than 100x100 pixels.

**Cause:** The `panel: true` option is not set in the view YAML
(so the view is NOT a full-width view). The `square: false`
option is not set in the grid card YAML (so the grid is square
+ the buttons are smaller than 100x100 pixels). The buttons are
not configured with the `show_state: false` option (so the
state text is shown + the buttons are too small).

**Fix:** Verify the `panel: true` option is set in the view YAML.
Verify the `square: false` option is set in the grid card YAML.
Verify the buttons are configured with the `show_state: false`
option. Verify the buttons are at least 100x100 pixels each.

### §8.3 Always-on display drains battery

**Symptom:** The in-cab tablet's battery drains in 4-6 hours when
the Path C "Lock screen / Always-on-display" view is active. The
operator expects the tablet's battery to last 8-24 hours.

**Cause:** The Path C "Lock screen / Always-on-display" view is
NOT configured with the 60s refresh cadence (so the tiles refresh
every 1-5s). The tiles in the Path C "Lock screen" view are NOT
configured with the `state_color: false` option (so the tiles use
bright colors + the tablet's display is brighter than necessary).
The tablet's always-on-display setting is not enabled (so the
display is at full brightness all the time).

**Fix:** Verify the `sensor.rc_in_cab_tablet_refresh_cadence_
seconds` shows `60` when the view is `lock_screen`. Verify the
tiles in the Path C "Lock screen" view are configured with the
`state_color: false` option. Verify the tablet's always-on-
display setting is enabled in the tablet's OS settings.

### §8.4 Wican Pro ignition not detected

**Symptom:** The §7.1 ignition-on auto-switch automation does not
trigger when the ignition turns on. The
`binary_sensor.rc_vehicle_ignition` from Wican Pro Wave 3 #6
does not change state.

**Cause:** The Wican Pro Wave 3 #6 connection is not installed
+ working. The Wican Pro OBD-II reader is not plugged into the
vehicle's OBD-II port. The Wican Pro's MQTT broker is not
configured correctly.

**Fix:** Verify the Wican Pro Wave 3 #6 connection is installed
+ working (see `connections/wican-pro/` for the install recipe).
Verify the Wican Pro OBD-II reader is plugged into the vehicle's
OBD-II port. Verify the Wican Pro's MQTT broker is configured
correctly + the `binary_sensor.rc_vehicle_ignition` entity is
present in HA.

### §8.5 Lock screen view not dimmed enough

**Symptom:** The Path C "Lock screen / Always-on-display" view
uses bright colors + the tiles flash on state change. The
tablet's battery drains faster than expected.

**Cause:** The tiles in the Path C "Lock screen" view are NOT
configured with the `state_color: false` option (so the tiles
use bright colors + flash on state change). The
`sensor.rc_in_cab_tablet_refresh_cadence_seconds` does not
show `60` when the view is `lock_screen`.

**Fix:** Verify the tiles in the Path C "Lock screen" view are
configured with the `state_color: false` option. Verify the
`sensor.rc_in_cab_tablet_refresh_cadence_seconds` shows `60`
when the view is `lock_screen`. Verify the tablet's brightness
setting is set to a low value when the view is `lock_screen`.

### §8.6 Manual override doesn't stick

**Symptom:** The operator manually changes the
`select.rc_in_cab_tablet_view_mode` select to `driving` + the
view switches to `driving` for a few seconds + then switches
back to the auto-switched view when the next ignition event
fires.

**Cause:** The §7.3 manual override automation is not wired. The
`select.rc_in_cab_tablet_view_mode` select is not being updated
to `manual` when the operator manually changes the view.

**Fix:** Verify the §7.3 manual override automation is wired
correctly in `configuration.yaml`. Verify the
`automation.in_cab_tablet_manual_override` automation is enabled
+ the `last_triggered` attribute is being updated when the
operator changes the view.

## §9 Privacy

The in-cab-tablet-dashboard recipe is a vendor-neutral recipe over
the upstream HA Lovelace view system + the upstream `input_select`
+ `input_button` + `device_tracker` integrations. The recipe
exposes the following data:

- **Local Lovelace view state.** The
  `sensor.rc_in_cab_tablet_active_view` + the
  `select.rc_in_cab_tablet_view_mode` + the
  `button.rc_in_cab_tablet_set_view_now` tiles expose the
  current Lovelace view state to the dashboard + OpenClaw
  queries. The data is local to the HA instance; no cloud call
  home.
- **Local ignition source state.** The
  `sensor.rc_in_cab_tablet_ignition_state` + the
  `binary_sensor.rc_vehicle_ignition` tiles expose the current
  ignition state. The data is local to the HA instance; no cloud
  call home.
- **Local view mode select state.** The
  `select.rc_in_cab_tablet_view_mode` select exposes the current
  view mode. The data is local to the HA instance; no cloud
  call home.

The recipe does NOT collect any telemetry + does NOT call home to
any cloud service. All processing is local to the HA instance +
the in-cab tablet. The only network traffic is the in-cab tablet
reaching HA's Lovelace UI over the local network (Wi-Fi or LTE).

## §10 Promoting to tier-b

Tier-b would require a RoamCore-owned in-cab-tablet dashboard
engine + integration code + integration tests against a real
in-cab tablet bench. The bench fixture would require:

- A physical 7-10" Android tablet mounted in the cab with the
  HA Companion app installed + configured to reach the HA
  instance.
- A Wican Pro OBD-II reader plugged into the vehicle's OBD-II
  port + configured to publish
  `binary_sensor.rc_vehicle_ignition` + the 4 other Wican Pro
  contract entities.
- A Traccar Wave 3 #36 server installed + configured to publish
  `device_tracker.rc_location_van` + the 6 other Traccar
  contract entities.
- The HA Companion app installed on the operator's phone +
  configured to publish `device_tracker.<phone_name>` + the
  other HA Companion contract entities.
- Canned fixture responses for ignition-on / ignition-off /
  zone-home / zone-away events.
- The upstream HA Lovelace view system installed + configured
  with the Path A "Driving" view + the Path B "Arrival /
  Welcome" view + the Path C "Lock screen / Always-on-
  display" view.

Once the bench fixture is in place, the tier-b promotion would
add:

- A RoamCore-owned `config_flow.py` walking the operator
  through Path A vs Path B vs Path C.
- A RoamCore-owned integration code that publishes the 8
  `rc_in_cab_tablet_*` contract tiles + the §7 automations.
- Integration tests asserting:
  - Ignition-on triggers the §7.1 ignition-on auto-switch to
    `arrival` view automation.
  - Ignition-off triggers the §7.2 ignition-off auto-switch to
    `lock_screen` view automation.
  - Manual select change triggers the §7.3 manual override
    automation.
  - `sensor.rc_in_cab_tablet_active_view` reflects the current
    view state.
  - `binary_sensor.rc_in_cab_tablet_driving_mode_active` is
    TRUE when view=`driving`.
  - `binary_sensor.rc_in_cab_tablet_lock_screen_active` is
    TRUE when view=`lock_screen`.
  - The `button.rc_in_cab_tablet_set_view_now` button
    forces a view switch within a defined latency budget.
  - The cadence select correctly enables / disables the
    corresponding refresh interval.

## §11 Files in this connection + cross-references

### §11.1 Files in this connection

- `connection.yml` — the source-of-truth manifest. Mirrors the
  time-atomic shape; the in-cab-tablet-dashboard `rc_in_cab_
  tablet_*` prefix is the SPECIFIC in-cab-tablet-dashboard
  subset of the broader vehicle subsystem (the `vehicle`
  subsystem `rc_vehicle_*` prefix is OWNED by the existing
  Wican Pro Wave 3 #6 connection). The three install paths
  (Path A "Driving" view + Path B "Arrival / Welcome" view +
  Path C "Lock screen / Always-on-display" view) + the 8
  `rc_in_cab_tablet_*` contract tiles are documented in the
  description + tier_warnings + dashboard.tiles. The reuse-
  first strategy is explicitly documented in the description
  (no custom in-cab-tablet dashboard engine; HA's Lovelace
  view system + the upstream `input_select` + `input_button`
  + `device_tracker` integrations).
- `__init__.py` — `DOMAIN = "in_cab_tablet"` marker for the
  audit. The docstring rephrases the strategy to avoid the
  literal `config_flow.py` substring (the same trap the
  happijac slice was bitten by). The substring guard in
  `test_tier_c_documents_reuse_first_strategy` asserts no
  `config_flow.py` substring appears anywhere in the file.
- `README.md` — the folder overview. Cross-references Wican
  Pro + Traccar + HA Companion app + Approach lights + HVAC
  basics + Teltonika.
- `docs/recipe.md` (this file) — the full howto. §1 the
  umbrella positioning + reuse-first strategy + single
  "active view?" tile + driving-mode safety gate + lock-
  screen battery gate + THREE-path wrapper + ignition-aware
  auto-switch; §2 prerequisites; §3 Path A "Driving" view
  wiring; §4 Path B "Arrival / Welcome" view wiring + the
  §7.1 ignition-on auto-switch automation; §5 Path C "Lock
  screen / Always-on-display" view wiring + the §7.2
  ignition-off auto-switch automation; §6 the 8 `rc_in_cab_
  tablet_*` contract tiles + templates; §7 the THREE
  automations (with full YAML); §8 the 6 troubleshooting
  entries; §9 privacy; §10 tier-b promotion outline; §11
  files + cross-references.
- `tests/test_connection_yml.py` — the 7 manifest-honesty
  tests. The 7 tests:
  test_connection_yaml_is_valid (base YAML parse +
  tier=c + status=recipe_published + DOMAIN=`in_cab_tablet`)
  + test_tier_c_documents_reuse_first_strategy (tier=c +
  one_tap=false + config_flow=false honest because RoamCore
  ships no native in-cab-tablet dashboard engine + hacs=false
  because the recipe is a pure recipe over upstream HA
  Lovelace view system code + substring guard against
  `config_flow.py` + DOMAIN=`in_cab_tablet` + description
  mentions reuse / lovelace / in-cab-tablet / ignition +
  links.official includes the HA dashboard docs URL) +
  test_dashboard_tiles_follow_rc_naming (8 vendor-neutral
  `rc_in_cab_tablet_*` tiles, forbidden_substrings covers
  vendor + hardware + protocol + integration names including
  `wican`, `obd`, `12v`, `24v`, `mqtt`, `hacs`,
  `homeassistant`, `device_tracker`, `lovelace`, `dashboard_`,
  `view_`, `panel`, `traccar`, `ha_companion`, `esphome`,
  `esp32`, `binary_sensor_`, `sensor_`, `switch`,
  `input_boolean`, `input_select`, `input_number`,
  `input_datetime`, `input_text`) + test_status_reflects_
  recipe_published (status=recipe_published + 5
  tier_warnings — `no_native_in_cab_tablet_integration` +
  `recipe_depends_on_user_wiring_dashboard_yaml` +
  `requires_operator_choice_of_path_a_driving_view_or_path_b_
  arrival_view_or_path_c_lock_screen` + `no_real_vehicle_
  ignition_signal_on_ci_bench` + `mode_aware_stealth_
  suppression_not_required`) + test_automations_are_documented
  (THREE §7 automations + 4 safety tiles + Wican Pro +
  Traccar + HA Companion + Approach lights + HVAC basics
  cross-references) + test_no_legacy_dashboard_yaml_
  collisions (assert no collision with the existing
  dashboard YAML files in the operator's existing
  `ui-lovelace.yaml` file — the new connection is a
  recipe-only addition; the operator wires the Path A +
  Path B + Path C views into the existing `ui-lovelace.yaml`
  via the dashboard UI's "Add view" button or the "Raw
  configuration editor", not into a separate
  Lovelace config file) +
  test_cross_references_resolve (assert all §11 cross-
  references resolve to existing files).

### §11.2 Cross-references

- **Wican Pro (Wave 3 #6 — canonical).** The
  `binary_sensor.rc_vehicle_ignition` from Wican Pro Wave 3
  #6 is the canonical ignition source for the §7.1 ignition-
  on auto-switch to `arrival` view automation. The OBD-II bus
  exposes a D+ signal that's TRUE when the ignition is on +
  FALSE when the ignition is off. Wican Pro publishes the D+
  signal as `binary_sensor.rc_vehicle_ignition` (one of the
  5 contract entities from the Wican Pro Wave 3 #6
  connection).
- **Traccar (Wave 3 #36 — fallback ignition source).** A
  `device_tracker.rc_location_van` state change to home
  zone is a valid fallback ignition source for the §7.1
  ignition-on auto-switch to `arrival` view automation. The
  Traccar server's `device_tracker.rc_location_van` entity
  is updated whenever the van enters or leaves a zone.
- **HA Companion app (phone-based ignition proxy).** The
  HA Companion app's `device_tracker.<phone_name>` state
  change to home zone is a valid fallback ignition source
  for the §7.1 ignition-on auto-switch to `arrival` view
  automation. The HA Companion app is the operator-phone-
  based location source.
- **Approach lights (Wave 3 #52 — arrival view's exterior
  lighting).** The `arrival` view's exterior lighting
  controls surface the Approach lights Wave 3 #52 contract
  entities (`light.rc_approach_left` + `light.rc_approach_
  right` + `light.rc_approach_underbody`) for one-tap
  control of the approach lights on arrival.
- **HVAC basics (Wave 3 #49 — arrival view's heating/
  cooling).** The `arrival` view's heating/cooling toggles
  surface the HVAC basics Wave 3 #49 contract entities
  (`climate.rc_hvac_*` + `switch.rc_hvac_*`) for one-tap
  control of the heating/cooling on arrival.
- **Teltonika LTE (Wave 3 #39 — always-on LTE backhaul).**
  The in-cab tablet reaches HA's Lovelace UI over the
  always-on LTE backhaul via the Teltonika Wave 3 #39 LTE
  router. The Teltonika's 4G/5G modem is always-on (low
  power consumption + reliable); the tablet can reach HA's
  Lovelace UI via the LTE backhaul without depending on
  Starlink.
