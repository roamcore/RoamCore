"""Frigate — vendor-neutral NVR backend with on-device
person / car / animal / package detection that the
upstream HA core `frigate` integration exposes for
IP-camera motion detection + recording + audit trails
— tier-b recipe connection.

Note on upstream wiring: tier-b connections don't ship a
RoamCore-owned operator-wired setup flow (a RoamCore
operator-wired wizard); instead, each path uses the
upstream integration's GUI flow (the HA core `frigate`
integration exposes an operator-wired setup flow + GUI
flow for adding the upstream NVR engine to the HA core;
the upstream `camera` platform exposes an operator-wired
setup flow + GUI flow for adding the upstream cameras;
the HA core `input_boolean` + `input_text` +
`input_number` + `input_select` + `input_datetime` +
`input_button` + `script` helpers + the HA core
`recorder` integration + the HA core `logbook`
integration + the HA core `template:` sensor wrapper +
the HA core `template:` binary_sensor wrapper + the HA
core `button:` domain helper + the upstream `script:`
integration all expose their own operator-wired setup
flow + GUI flow).

This module is a marker-only stub. Tier-b connections
don't ship native HA integration code; they publish a
recipe (docs/recipe.md) that walks the operator through
installing the HACS frigate add-on + the upstream HA
core `frigate` integration + wiring the FIVE-step
operator-pickable NVR flow:

  - Pick the NVR path — the operator chooses ONE of
    the THREE upstream NVR paths documented in the
    recipe: Path A — HACS frigate add-on (recommended
    for most operators; local-only + auto-starts on HA
    boot + auto-configures the HA core `frigate`
    integration to point at the local NVR; no
    vendor-specific credentials required); Path B —
    external / cloud NVR (for operators who already run
    an NVR off-box; the recipe documents how to wire
    the upstream HA core `frigate` integration to point
    at the external NVR + how to secure the connection
    with username / password); Path C — local container
    / VM NVR (for operators who want a Docker / Podman
    / LXC / VM NVR on the same Proxmox box or on a
    separate mini-PC; the recipe documents the
    vendor-neutral generic NVR wire-up).

  - Mount the camera URLs — the operator configures
    `input_text.rc_security_camera_url` (a comma-
    separated list of camera URLs) + the optional
    camera username + password + motion detection
    toggle. The §4 operator flow walks the operator
    through populating the camera URLs + confirming the
    camera URLs are reachable.

  - Confirm the cameras are online — the operator
    confirms `binary_sensor.rc_security_camera_online`
    reads TRUE (the §8.1 per-camera offline guard's
    canonical safety chip). The §5 operator flow walks
    the operator through confirming the cameras are
    online before the first recording.

  - Enable + start recording — the operator flips
    `input_boolean.rc_storage_recording_enabled` ON
    (the upstream HA core `recorder` integration's
    master enable; the upstream `record` service
    exposes a GUI flow for the operator to record from
    the HA UI under Developer Tools → Services). The
    `binary_sensor.rc_security_camera_recording`
    surfaces "recording" / "idle" in the dashboard.

  - Audit + revert — every camera state change + every
    `record` service call + every `record` event
    received writes an entry to
    `sensor.rc_security_camera_last_motion` (the
    resolved per-camera last-motion timestamp) + the
    `sensor.rc_security_camera_motion_mask` (the
    resolved per-camera motion-mask count) + the
    `sensor.rc_security_detection_person_count` + the
    `sensor.rc_security_detection_car_count` + the
    `sensor.rc_security_detection_animal_count` + the
    `sensor.rc_security_detection_package_count` (the
    resolved per-camera detection counts) + the HA
    core `logbook` (the canonical audit-log
    destination for Home Assistant automations). The
    operator can revert at any time via
    `button.rc_storage_recording_reset_now` (the
    operator-triggered one-tap reset-now — fires an
    automation resetting the upstream `recorder`
    integration's recording state + clears the
    per-camera offline guard + clears the storage-full
    guard).

The umbrella publishes the resulting data via the
upstream HA core `frigate` integration (since 2022.x —
exposes the canonical NVR backend for Home Assistant
automations) + the upstream `camera` platform (since
2022.x — exposes a GUI flow for the operator to add the
upstream cameras via the HA UI under Settings → Devices
& services → Integrations → Add Integration → Camera) +
the HA core `input_boolean` + `input_text` +
`input_number` + `input_select` + `input_datetime` +
`input_button` + `script` helper entities (since 2022.x
— have exposed the standard `input_boolean.toggle` +
`input_text.set_value` + `input_number.set_value` +
`input_select.select_option` + `input_datetime.set_datetime`
+ `input_button.press` + `script.*` services + the
`input_boolean` / `input_text` / `input_number` /
`select` / `input_datetime` / `sensor` / `binary_sensor`
/ `button` domain entities) + the HA core `recorder`
integration (since 2022.x — the canonical recording
service for Home Assistant automations) + the HA core
`template:` sensor wrapper (since 2022.x — wraps any
upstream sensor state into a derived `sensor.*` entity)
+ the HA core `template:` binary_sensor wrapper (since
2022.x — wraps any upstream binary_sensor state into a
derived `binary_sensor.*` entity) + the HA core
`logbook` integration (since 2022.x — the canonical
audit-log destination for Home Assistant automations) +
the HACS frigate add-on (the canonical upstream
vendor-neutral local NVR), then publishes the RoamCore
NVR contract tiles on top (the 12 contract entities
documented in connection.yml — 4 cameras
`rc_security_camera_*` + 4 detection
`rc_security_detection_*` + 4 recording/storage
`rc_storage_recording_*` = 12 contract entities).

The audit + boundary CI can detect a `frigate/` folder
that claims to be a connection via the `DOMAIN`
constant exported here. The wizard reads the manifest +
recipe at runtime.

The real per-operator NVR affordance path is:

    Operator-side choice of the FIVE-step flow (Pick the
        NVR path -> Mount the camera URLs -> Confirm the
        cameras are online -> Enable + start recording
        -> Audit + revert)
        -> upstream entities (the HA core
           `binary_sensor.rc_security_camera_online` for
           the upstream `frigate` integration's camera-
           online state — derived via the HA core
           `template:` binary_sensor wrapper since
           2022.x; the HA core
           `binary_sensor.rc_security_camera_recording`
           for the upstream `frigate` integration's
           camera-recording state — derived via the HA
           core `template:` binary_sensor wrapper since
           2022.x; the HA core
           `sensor.rc_security_camera_last_motion` for
           the upstream `frigate` integration's per-
           camera last-motion timestamp — derived via the
           HA core `template:` sensor wrapper since
           2022.x; the HA core
           `sensor.rc_security_camera_motion_mask` for
           the upstream `frigate` integration's per-
           camera motion-mask count — derived via the HA
           core `template:` sensor wrapper since 2022.x;
           the HA core
           `sensor.rc_security_detection_person_count`
           for the resolved per-camera person-detection
           count — derived via the HA core `template:`
           sensor wrapper since 2022.x; the HA core
           `sensor.rc_security_detection_car_count` for
           the resolved per-camera car-detection count —
           derived via the HA core `template:` sensor
           wrapper since 2022.x; the HA core
           `sensor.rc_security_detection_animal_count`
           for the resolved per-camera animal-detection
           count — derived via the HA core `template:`
           sensor wrapper since 2022.x; the HA core
           `sensor.rc_security_detection_package_count`
           for the resolved per-camera package-detection
           count — derived via the HA core `template:`
           sensor wrapper since 2022.x; the HA core
           `input_boolean.rc_storage_recording_enabled`
           for the master enable — operator flips via
           the HA UI under Settings → Helpers; the HA
           core `sensor.rc_storage_recording_used` for
           the resolved per-camera storage used in
           gigabytes — derived via the HA core `template:`
           sensor wrapper since 2022.x; the HA core
           `sensor.rc_storage_recording_free` for the
           resolved per-camera storage free in gigabytes
           — derived via the HA core `template:` sensor
           wrapper since 2022.x; the HA core
           `sensor.rc_storage_recording_retention_today_count`
           for the resolved per-camera retention today
           count — derived via the HA core `template:`
           sensor wrapper since 2022.x)
        -> upstream signals (the operator's chosen NVR
           path — Path A HACS frigate add-on, Path B
           external / cloud NVR, or Path C local
           container / VM NVR; the operator's chosen
           camera credentials — username + password +
           motion detection toggle; the upstream
           `frigate` integration's auto-discovery of
           upstream cameras via the canonical upstream
           `frigate` discovery protocol since 2022.x)
        -> RoamCore contract layer (HA core `template:`
           sensor + binary_sensor + the operator's
           `input_boolean` / `input_text` / `input_number`
           / `input_select` / `input_datetime` /
           `input_button` for the contract tiles + the
           upstream `frigate` integration for the
           auto-discovery signal + the `script:`
           integration for the upstream `record` wrapper
           + the `recorder` integration for the
           recording service + the `logbook` integration
           for the §8 audit-log entry)
        -> dashboard tiles + OpenClaw queries
            ("is the camera online?",
             "is the camera recording?",
             "what was the camera last motion?",
             "what is the camera motion mask count?",
             "how many person detections today?",
             "how many car detections today?",
             "how many animal detections today?",
             "how many package detections today?",
             "is recording enabled?",
             "how much storage is used?",
             "how much storage is free?",
             "how many recordings retained today?")

    Safety interlocks (the recipe is the contract layer;
    the automation wrappers are documented in §8):
        -> The RoamCore per-camera offline guard is the
           §8.1 automation that fires when
           `binary_sensor.rc_security_camera_online`
           flips FALSE; the automation flips
           `binary_sensor.rc_security_camera_recording`
           to FALSE + flips
           `sensor.rc_security_camera_last_motion` to
           "unknown" + clears the per-camera detection
           counts to 0 + fires a critical notification
           warning the operator that the camera has gone
           offline.
        -> The RoamCore cameras-online guard is the §8.2
           automation that fires when
           `binary_sensor.rc_security_camera_online`
           flips TRUE; the automation clears the offline
           flag + flips
           `binary_sensor.rc_security_camera_recording`
           to TRUE + updates
           `sensor.rc_security_camera_last_motion` +
           updates the per-camera detection counts +
           fires a notification warning the operator
           that the cameras have come back online.
        -> The RoamCore per-camera motion-mask guard is
           the §8.3 automation that fires when
           `sensor.rc_security_camera_motion_mask` flips
           to a non-zero value for an unexpected camera
           (a camera that was previously motion-masked
           now has motion); the automation updates
           `sensor.rc_security_camera_motion_mask` +
           fires a critical notification warning the
           operator that the camera motion-mask has
           changed.
        -> The RoamCore storage-full guard is the §8.4
           automation that fires when
           `sensor.rc_storage_recording_free` dips
           below 10 GB; the automation flips
           `input_boolean.rc_storage_recording_enabled`
           to OFF + fires a critical notification warning
           the operator that the storage is full.
        -> The RoamCore records-on-motion guard is the
           §8.5 automation that fires when ANY
           `script.*` / `automation.*` action tries to
           call the `record` service while
           `input_boolean.rc_storage_recording_enabled`
           is OFF; the automation BLOCKS the record +
           flips
           `binary_sensor.rc_security_camera_recording`
           to FALSE + fires a critical notification
           warning the operator that recording is
           disabled.

The audit + boundary CI can detect this module via the
`DOMAIN = "frigate"` constant; the wizard reads the
manifest + recipe at runtime.

The umbrella ships no RoamCore-owned NVR engine; the
recipe is the contract layer + the §8 MANDATORY
automations + the operator-facing affordance surfaces.

The legacy catalog page (now superseded by this slice)
lives at `docs/catalog/cctv/frigate.md` — a 669-byte
tier-c claim stub, originally listed "CCTV with Frigate
(spec + setup ideas): A single-page spec for a low-CPU
CCTV system using Frigate + go2rtc, designed for
predictable storage and practical van use" with no
recipe + no contract + no automations + no install path
— just a placeholder with an aspirational tier-c claim.
The picker is honest and ships the contract layer + the
recipe + the §8 automations + the operator-side NVR
wire-up as tier-b. The legacy doc now carries a
SUPERSEDED banner pointing at this connection.
"""

from __future__ import annotations

DOMAIN = "frigate"
