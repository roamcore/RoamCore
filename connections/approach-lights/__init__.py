"""Approach lights (welcome-home exterior + underbody lighting) — tier-b recipe connection.

This module is a marker-only stub. Tier-b connections don't ship native
HA integration code; they publish a recipe (docs/recipe.md) that walks
the user through setting up welcome-home exterior + underbody +
entry + soft-interior lighting on the van (Path A — smart switches /
smart bulbs the operator already owns — Shelly 1 / Shelly Plus 1 / Zooz
ZEN17 / Aeotec Nano Switch wired switches; Philips Hue / LIFX / IKEA
TRÅDFRI smart bulbs; generic-Zigbee / generic-Z-Wave / Tuya
vendor-neutral; the vendor integration exposes `light.*` or `switch.*`
entities; Path B — generic relay + HA template light — Shelly / Zooz /
Aeotec relay wired into a 12 V / 24 V LED driver for the underbody
strip + the entry porch light, with HA `template:` light wrapping the
relay state into virtual `light.entry` + `light.underbody` +
`light.soft_interior`; Path C — all-in-one smart scene controller —
Hue Bridge / Lutron Caséta / IKEA TRÅDFRI / Bond Home hub with all
approach lights grouped into a `light.approach_scene` group entity
(HA `light:` group domain since 2022.x)), and exposes the resulting
data via the upstream `light` / `switch` / `template` / `light:`
group / `input_boolean` / `input_select` / `input_number` /
`binary_sensor` / `button` integrations, then publishes the
RoamCore lighting contract tiles on top (`rc_lighting_*` tiles: the
12 contract entities documented in connection.yml — 4 binary_sensor
active/available/state tiles (approach_active / approach_available /
underbody_state / entry_state / soft_interior_state — 5 binary_sensor
in the §6 contract layer, but the contract list collapses the three
per-zone state binary_sensors into a single family + the camera-
override binary_sensor + the dark_outside binary_sensor) + 2 sensor
tiles (approach_minutes_remaining / last_approach_trigger_minutes_
ago) + 1 select tile (approach_mode: auto / dark_only / stealth_only
/ disabled) + 1 number configuration tile (approach_duration_min) +
1 button tile (run_approach_now) + the camera_override binary_sensor
+ the dark_outside binary_sensor).

The audit + boundary CI can detect a `approach-lights/` folder that
claims to be a connection via the `DOMAIN` constant exported here.
The wizard reads the manifest + recipe at runtime.

The real per-operator approach light affordance path is:

    Operator-side approach light source (Path A — smart switches /
        smart bulbs the operator already owns — Shelly 1 / Shelly
        Plus 1 / Zooz ZEN17 / Aeotec Nano Switch wired switches;
        Philips Hue / LIFX / IKEA TRÅDFRI smart bulbs; generic-
        Zigbee / generic-Z-Wave / Tuya vendor-neutral; the vendor
        integration exposes `light.*` or `switch.*` entities since
        2022.x via the vendor's GUI flow; OR Path B — generic relay
        + HA template light — Shelly 1 / Shelly Plus 1 / Zooz ZEN17
        / Aeotec Nano Switch wired into a 12 V / 24 V LED driver
        for the underbody strip + the entry porch light, with the
        Shelly / Z-Wave integration exposing a GUI flow since
        2022.x + the HA `template:` integration translating the
        relay state into virtual `light.entry` + `light.underbody`
        + `light.soft_interior` template lights; OR Path C — all-
        in-one smart scene controller — Hue Bridge / Lutron
        Caséta / IKEA TRÅDFRI / Bond Home hub with all approach
        lights grouped into a `light.approach_scene` group entity
        (HA `light:` group domain since 2022.x))
        -> upstream entity (light.<zone>_<role> for the operator's
           approach light entity; switch.<zone>_<role> for the
           operator's relay-driven light (Path B); light.approach_
           scene for the grouped scene controller (Path C))
        -> RoamCore contract layer (HA core `template:`
           binary_sensor / sensor / select / number / button that
           maps the upstream entities into the 12 `rc_lighting_*`
           contract tiles — rc_lighting_approach_active +
           rc_lighting_approach_available +
           rc_lighting_underbody_state + rc_lighting_entry_state +
           rc_lighting_soft_interior_state +
           rc_lighting_approach_minutes_remaining +
           rc_lighting_last_approach_trigger_minutes_ago +
           rc_lighting_dark_outside +
           rc_lighting_approach_mode +
           rc_lighting_approach_duration_min +
           rc_lighting_run_approach_now +
           rc_lighting_camera_override)
        -> dashboard tiles + OpenClaw queries
            ("is_approach_lighting_on",
             "approach_lighting_minutes_remaining",
             "last_approach_trigger_minutes_ago",
             "is_dark_outside", "is_underbody_light_on",
             "is_entry_light_on", "is_soft_interior_light_on",
             "run_approach_now", "set_approach_mode",
             "set_approach_duration_min",
             "is_camera_override_active")

    The five §7 automations (MANDATORY before first use — operator
    must wire each one per the recipe §7):
        -> First-arrival-after-dark: trigger when
           `binary_sensor.rc_presence_all_away` (from the bluetooth-
           wifi-presence Wave 3 #42 connection) transitions TRUE →
           FALSE AND `binary_sensor.rc_lighting_dark_outside` is
           TRUE AND `select.rc_lighting_approach_mode` != `disabled`
           AND `select.rc_mode` (from the mode/automation-builder
           connection) != `stealth`. Fire
           `binary_sensor.rc_lighting_approach_active` TRUE + start
           the N-minute countdown via HA `timer:` integration.
        -> Run-on-demand: trigger on
           `button.rc_lighting_run_approach_now` press. Fire the
           same approach-active transition + start the same
           N-minute countdown (useful for showing a friend where
           the van is + for testing the wiring without waiting for
           first arrival).
        -> Auto-stop-after-N-min: trigger on the HA `timer:` N-
           minute countdown fire (the countdown was started by the
           first-arrival-after-dark automation OR the run-on-demand
           button press). Fire
           `binary_sensor.rc_lighting_approach_active` FALSE +
           `light.turn_off` for each of the approach lights (cross-
           references the operator's upstream light entities).
        -> Camera-override-on-frigate-person: trigger on a Frigate
           `person` detection in the entry zone (cross-references
           Frigate Wave 3 #35). Fire
           `binary_sensor.rc_lighting_camera_override` TRUE for 30
           seconds (with auto-reset via HA `timer:` integration) +
           set the underbody lights to full brightness via
           `light.turn_on` (the operator wants a brighter "someone's
           at the door" cue than the gentle approach scene; the
           brighter cue is also a soft deterrent). Cross-reference
           the Frigate `connections/frigate/` connection's
           `binary_sensor.<camera>_<zone>_person_detected` entity
           (the operator wires this via HA `template:` binary_sensor
           if Frigate is installed; the camera-override contract
           tile stays FALSE if Frigate is not installed).
        -> Stealth-mode-suppression: when
           `select.rc_mode` (from the mode/automation-builder
           connection) == `stealth`, suppress ALL approach lighting
           (don't fire the first-arrival-after-dark automation). At
           a quiet campground after dark, the gentle approach
           lights can be enough to make neighbors think someone is
           up + wanting to chat — Stealth mode mutes the approach
           scene entirely so the operator can come home late without
           waking the campground. The camera-override cross-
           reference still fires (the camera-override is a
           safety-relevant deterrent; Stealth mode does NOT mute
           safety-relevant cues).

See docs/recipe.md for the full howto (Path A smart switches / smart
bulbs — Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano Switch
wired switches + Philips Hue / LIFX / IKEA TRÅDFRI smart bulbs +
generic-Zigbee / generic-Z-Wave / Tuya vendor-neutral — the
`light.turn_on` service call + a `template:` binary_sensor that
aggregates the vendor `light.*` entities into the `rc_lighting_*`
contract tiles; Path B generic relay + HA template light — Shelly /
Zooz / Aeotec wiring (12 V / 24 V supply + relay contacts into the
LED driver) + HA Shelly/Z-Wave integration auto-discovery +
`template:` light wrapping the relay state into virtual
`light.entry` + `light.underbody` + `light.soft_interior`; Path C
all-in-one smart scene controller — Hue Bridge / Lutron Caséta /
IKEA TRÅDFRI / Bond Home hub + the recipe walks through creating a
`light.approach_scene` group entity (HA `light:` group domain since
2022.x) + binding the approach scene to the contract tiles; the 12
§6 contract tiles + how the upstream light/switch template exposes
them + translation helpers needed for the derived metrics like
`approach_minutes_remaining` + `last_approach_trigger_minutes_ago` +
`dark_outside` + `camera_override`; the five §7 automations (first-
arrival-after-dark + run-on-demand + auto-stop-after-N-min +
camera-override-on-frigate-person + stealth-mode-suppression); the
six §8 troubleshooting entries (approach scene never fires / approach
scene stays on forever / only some lights come on / camera override
always firing / Stealth mode doesn't suppress / underbody light
flickers); §9 privacy (the lights produce no telemetry beyond local
on/off state; the camera-override cross-references Frigate which has
its own privacy controls; no cloud call home — Path A Hue/LIFX
require their own cloud auth but only for the operator's first-time
setup; subsequent runs are local); §10 Promoting to tier-a (real
Shelly 1 + LED strip + Hue Bridge + Frigate entry zone on CI bench +
RoamCore-owned operator-wired setup flow that walks the operator through
choosing Path A / B / C + declaring the upstream entities + the
camera-override Frigate zone + integration tests asserting a presence-
detected event triggers the approach scene + a Frigate `person`
event triggers the camera override + a Stealth mode change
suppresses the scene)).
"""

DOMAIN = "approach_lights"