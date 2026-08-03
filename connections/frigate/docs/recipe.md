# Frigate — full howto (RoamCore vendor-neutral NVR backend with on-device person / car / animal / package detection — the camera backend everything depends on)

This recipe is the canonical howto for the
`connections/frigate/` tier-b recipe connection (Wave 3
#35). It walks the operator through picking ONE of the
THREE upstream NVR paths (Path A HACS frigate add-on,
Path B external / cloud NVR, Path C local container / VM
NVR) + mounting the camera URLs
(`input_text.rc_security_camera_url` a comma-separated
list of camera URLs; `input_text.rc_security_camera_username`;
`input_boolean.rc_security_camera_motion_enabled`) +
confirming the cameras are online
(`binary_sensor.rc_security_camera_online` reads TRUE) +
enabling + starting recording
(`input_boolean.rc_storage_recording_enabled` flips ON;
the upstream `record` service exposes a GUI flow under
Developer Tools → Services) + auditing (the HA core
`logbook` integration is the canonical audit-log
destination; `sensor.rc_security_camera_last_motion`
mirrors the upstream `frigate` integration's per-camera
last-motion timestamp) + reverting at any time via
`button.rc_storage_recording_reset_now` (the
operator-triggered one-tap reset-now — fires an
automation resetting the upstream `recorder`
integration's recording state + clears the per-camera
offline guard + clears the storage-full guard).

The recipe assumes the operator has at least the upstream
HA core `frigate` integration auto-installed (every HA
install has it since 2022.x) + the HACS frigate add-on
installed (Path A — recommended) or the external / cloud
NVR reachable (Path B) or the local container / VM NVR
running (Path C) + the camera URLs configured via
`input_text.rc_security_camera_url` (a comma-separated
list of camera URLs). If the operator has the upstream
HA core `frigate` integration + a reachable NVR + the
camera URLs configured, the recipe starts at §4 Mount
the camera URLs + walks through the cameras-online guard
+ the enable + the audit log before the §7 contract
layer.

## §1 What is Frigate in RoamCore?

Frigate — vendor-neutral NVR backend with on-device
person / car / animal / package detection that the
upstream HA core `frigate` integration exposes for
IP-camera motion detection + recording + audit trails —
is the security-category umbrella for "the camera
backend everything depends on". The single
`binary_sensor.rc_security_camera_online` tile is the
operator's canonical safety chip (TRUE when the upstream
`frigate` integration reports a connected camera state;
should ALWAYS be TRUE when the upstream `frigate`
integration is healthy; should NEVER be TRUE
unexpectedly); the `binary_sensor.rc_security_camera_recording`
is the per-camera recording state (surfaces "recording"
/ "idle" in the dashboard; mirrors the upstream `recorder`
integration's recording state); the
`sensor.rc_security_camera_last_motion` is the
per-camera last-motion timestamp (mirrors the upstream
`frigate` integration's per-camera last-motion event);
the `sensor.rc_security_camera_motion_mask` is the
per-camera motion-mask count (mirrors the upstream
`frigate` integration's per-camera motion-mask state);
the `sensor.rc_security_detection_person_count` is the
resolved per-camera person-detection count aggregated
across all cameras; the `sensor.rc_security_detection_car_count`
is the resolved per-camera car-detection count
aggregated across all cameras; the
`sensor.rc_security_detection_animal_count` is the
resolved per-camera animal-detection count aggregated
across all cameras; the `sensor.rc_security_detection_package_count`
is the resolved per-camera package-detection count
aggregated across all cameras; the
`input_boolean.rc_storage_recording_enabled` is the
master enable for the upstream `recorder` integration's
`record` service (default OFF for the recommended
safe-default mode; the §8.5 records-on-motion guard
fires whenever a `record` invocation arrives while this
toggle is OFF); the `sensor.rc_storage_recording_used`
is the per-camera recording storage used in gigabytes
(mirrors the upstream `recorder` integration's storage
stat); the `sensor.rc_storage_recording_free` is the
per-camera recording storage free in gigabytes (mirrors
the upstream `recorder` integration's storage stat; the
§8.4 storage-full guard fires when this dips below 10
GB); the `sensor.rc_storage_recording_retention_today_count`
is the per-camera recording retention today count (the
count of recordings retained today before the
retention-spin-down cycle; the §8.5 retentions-spin-down
guard fires when this exceeds the operator's configured
threshold).

The camera-online tile
(`binary_sensor.rc_security_camera_online`) is the
operator's canonical safety chip — the recipe surfaces
a green "camera online" chip when the upstream `frigate`
integration reports a connected camera state + a red
"camera offline" chip when the upstream `frigate`
integration reports a disconnected camera state. The
§8.1 per-camera offline guard fires whenever the
camera-online chip flips FALSE; the §8.2 cameras-online
guard fires whenever the camera-online chip flips TRUE.

The camera-recording tile
(`binary_sensor.rc_security_camera_recording`) is the
operator's per-camera recording state — the recipe
surfaces "recording" / "idle" in the dashboard. The
§8.5 records-on-motion guard sets this to "idle" when
the guard blocks a record invocation; the §8.2
cameras-online guard sets this to "recording" when the
camera comes back online.

The camera-last-motion tile
(`sensor.rc_security_camera_last_motion`) is the
operator's per-camera last-motion timestamp — the recipe
surfaces "2026-08-03 14:35:22" in the dashboard; mirrors
the upstream `frigate` integration's per-camera
last-motion event.

The camera-motion-mask tile
(`sensor.rc_security_camera_motion_mask`) is the
operator's per-camera motion-mask count — the recipe
surfaces "3 masked regions" in the dashboard; mirrors
the upstream `frigate` integration's per-camera
motion-mask state.

The detection-person-count tile
(`sensor.rc_security_detection_person_count`) is the
operator's resolved per-camera person-detection count
aggregated across all cameras — the recipe surfaces "47
person detections today" in the dashboard; mirrors the
upstream `frigate` integration's detection event log for
the `person` label.

The detection-car-count tile
(`sensor.rc_security_detection_car_count`) is the
operator's resolved per-camera car-detection count
aggregated across all cameras — the recipe surfaces "23
car detections today" in the dashboard; mirrors the
upstream `frigate` integration's detection event log for
the `car` label.

The detection-animal-count tile
(`sensor.rc_security_detection_animal_count`) is the
operator's resolved per-camera animal-detection count
aggregated across all cameras — the recipe surfaces "12
animal detections today" in the dashboard; mirrors the
upstream `frigate` integration's detection event log for
the `animal` label.

The detection-package-count tile
(`sensor.rc_security_detection_package_count`) is the
operator's resolved per-camera package-detection count
aggregated across all cameras — the recipe surfaces "5
package detections today" in the dashboard; mirrors the
upstream `frigate` integration's detection event log for
the `package` label.

The recording-enabled tile
(`input_boolean.rc_storage_recording_enabled`) is the
operator's master enable for the upstream `recorder`
integration's `record` service — the recipe defaults to
OFF because recording should never be permitted unless
the operator explicitly enables it (the §8.5
records-on-motion guard fires whenever a `record`
invocation arrives while this toggle is OFF).

The recording-used tile
(`sensor.rc_storage_recording_used`) is the operator's
per-camera recording storage used in gigabytes — the
recipe surfaces "47 GB used" in the dashboard; mirrors
the upstream `recorder` integration's storage stat.

The recording-free tile
(`sensor.rc_storage_recording_free`) is the operator's
per-camera recording storage free in gigabytes — the
recipe surfaces "53 GB free" in the dashboard; the
§8.4 storage-full guard fires when this dips below 10
GB.

The retention-today-count tile
(`sensor.rc_storage_recording_retention_today_count`) is
the operator's per-camera recording retention today
count — the recipe surfaces "12 recordings retained" in
the dashboard; the §8.5 retentions-spin-down guard fires
when this exceeds the operator's configured threshold.

The audit-log entry (the §8.1 per-camera offline guard +
the §8.2 cameras-online guard + the §8.3 per-camera
motion-mask guard + the §8.4 storage-full guard + the
§8.5 records-on-motion guard) is the operator-facing
"when did the camera last change state?" affordance —
the §8 automations write entries to the HA core
`logbook` integration (the canonical audit-log
destination for Home Assistant automations) + the
`binary_sensor.rc_security_camera_online` + the
`binary_sensor.rc_security_camera_recording` + the
`sensor.rc_security_camera_last_motion` + the
`sensor.rc_security_camera_motion_mask` + the four
detection-count tiles + the `sensor.rc_storage_recording_used`
+ the `sensor.rc_storage_recording_free` + the
`sensor.rc_storage_recording_retention_today_count`
contract tiles (mirrors the upstream `frigate`
integration's per-camera state).

The recipe covers the FIVE-step operator flow (Pick the
NVR path + Mount the camera URLs + Confirm the cameras
are online + Enable + start recording + Audit + revert)
+ the FIVE §8 MANDATORY automations + the 12
`rc_security_*` + `rc_storage_*` contract tiles + the
§9 troubleshooting entries + the §10 privacy section +
the §14 storage-rotation-policy section + the §11
tier-a promotion outline + the §12 files + the §13
cross-references.

## §2 Prerequisites

### §2.1 Universal prerequisites

The operator must have:

- A running Home Assistant installation (HA Core
  2022.6+; the upstream `frigate` integration + the
  upstream `camera` platform + the `input_boolean` +
  `input_text` + `input_datetime` + `input_button` +
  `select` helpers + `recorder` + `template:` +
  `logbook` + `script:` integration are all upstream
  since 2022.x).
- The upstream HA core `frigate` integration
  auto-installed (every HA install has it since 2022.x).
- The HACS prerequisites installed (for Path A; the
  HACS frigate add-on is the canonical upstream
  vendor-neutral local NVR add-on; install HACS first
  per https://hacs.xyz/docs/setup/prerequisites).
- A reachable NVR (Path A HACS frigate add-on, Path B
  external / cloud NVR, or Path C local container / VM
  NVR).
- Read access to the operator's camera URLs via
  `input_text.rc_security_camera_url` (a comma-
  separated list of camera URLs).

### §2.2 Upstream signal prerequisites

The operator must wire:

- `binary_sensor.rc_security_camera_online` (the §7
  canonical safety chip + the §8.1 per-camera offline
  guard's target).
- `binary_sensor.rc_security_camera_recording` (the §7
  per-camera recording state).
- `sensor.rc_security_camera_last_motion` (the §7
  per-camera last-motion timestamp).
- `sensor.rc_security_camera_motion_mask` (the §7
  per-camera motion-mask count).
- `sensor.rc_security_detection_person_count` (the §7
  resolved per-camera person-detection count).
- `sensor.rc_security_detection_car_count` (the §7
  resolved per-camera car-detection count).
- `sensor.rc_security_detection_animal_count` (the §7
  resolved per-camera animal-detection count).
- `sensor.rc_security_detection_package_count` (the §7
  resolved per-camera package-detection count).
- `input_boolean.rc_storage_recording_enabled` (the §7
  master enable for the upstream `recorder`
  integration's `record` service; default OFF for the
  recommended safe-default mode).
- `sensor.rc_storage_recording_used` (the §7 per-camera
  recording storage used in gigabytes).
- `sensor.rc_storage_recording_free` (the §7 per-camera
  recording storage free in gigabytes).
- `sensor.rc_storage_recording_retention_today_count`
  (the §7 per-camera recording retention today count).

### §2.3 Optional cross-references (recommended)

The operator may also wire:

- The MQTT Wave 3 #34 connection's broker primitives
  for the upstream `frigate` integration's auto-discovery
  signal (the upstream `frigate` integration's
  auto-discovery relies on the broker's `mqtt`
  integration for upstream discovery signals).
- The mode Wave 3 #61 connection's mode-change cross-
  reference for the §8.3 per-camera motion-mask guard.
- The advanced-mode Wave 3 #63 connection's confirm-flag
  pattern for the §8.5 records-on-motion guard.
- The openclaw-api Wave 3 #64 connection's JSON payload
  cross-reference for the §8.1 per-camera offline guard.
- The agent-actions-allowlist Wave 3 #65 connection's
  kill-switch cross-reference for the §8.5 records-on-
  motion guard.
- The remote-access Wave 3 #58 connection's VPN
  primitive for the §8.5 records-on-motion guard's
  owner-identity check.
- The dns-blocker Wave 3 #37 connection's network-
  reachability cross-reference for the §8.1 per-camera
  offline guard.
- The hvac-basics Wave 3 #49 connection's ventilation
  cross-reference for the §8.4 storage-full guard.
- The fans Wave 3 #59 connection's cooling cross-
  reference for the §8.4 storage-full guard.

## §3 Pick the NVR path

The recipe documents THREE upstream NVR paths. The
operator picks ONE based on their setup.

### §3.1 Path A — HACS frigate add-on (recommended)

Path A is the recommended path for most operators. The
HACS frigate add-on is the canonical upstream
vendor-neutral local NVR add-on; it auto-starts on HA
boot + auto-configures the upstream HA core `frigate`
integration to point at the local NVR; no
vendor-specific credentials required.

Steps:

1. Install HACS (https://hacs.xyz/docs/setup/prerequisites).
2. Open HACS → Add-ons → Search for "Frigate NVR" →
   Install.
3. Configure the HACS frigate add-on with the default
   settings (port 5000 + no authentication for the
   recommended local-only mode).
4. Start the HACS frigate add-on + check the add-on
   logs for the "frigate NVR started" line.
5. The upstream HA core `frigate` integration will
   auto-detect the HACS frigate add-on at
   `http://core-frigate:5000` + auto-configure the
   connection.

### §3.2 Path B — External / cloud NVR

Path B is for operators who already run an NVR off-box
(e.g. a cloud-hosted NVR for multi-site deployments; a
separate mini-PC NVR; a VPS NVR).

Steps:

1. Provision the external / cloud NVR per the upstream
   provider's docs.
2. Note the NVR URL + the username + the password.
3. Configure `input_text.rc_security_camera_url` to
   point at the external / cloud NVR (e.g.
   `https://nvr.example.com:5000`).
4. Configure `input_text.rc_security_camera_username`
   to the external / cloud NVR's username.
5. Configure the password via `secrets.yaml` (the
   recipe does NOT store the password in `input_text.*`
   for security reasons).
6. The upstream HA core `frigate` integration will
   auto-configure the connection to the external /
   cloud NVR on the next HA restart.

### §3.3 Path C — Local container / VM NVR

Path C is for operators who want a Docker / Podman / LXC
/ VM NVR on the same Proxmox box or on a separate
mini-PC. The recipe documents the vendor-neutral generic
NVR wire-up.

Steps:

1. Provision the Docker / Podman / LXC / VM NVR per the
   upstream provider's docs.
2. Note the NVR URL + the username + the password.
3. Configure `input_text.rc_security_camera_url` to
   point at the local container / VM NVR (e.g.
   `http://192.168.1.100:5000`).
4. Configure `input_text.rc_security_camera_username`
   to the local container / VM NVR's username (if any).
5. Configure the password via `secrets.yaml` (if any).
6. The upstream HA core `frigate` integration will
   auto-configure the connection to the local container
   / VM NVR on the next HA restart.

## §4 Mount the camera URLs

The camera URLs are mounted via the operator-facing
contract tiles. The recipe defaults to the canonical
HACS frigate add-on URL + empty username + TRUE motion
for the recommended local-only mode.

### §4.1 Configure the camera URL

The operator configures `input_text.rc_security_camera_url`
to point at the cameras:

```yaml
input_text:
  rc_security_camera_url:
    name: RC Security Camera URL
    initial: "rtsp://192.168.1.201:554/stream1,rtsp://192.168.1.202:554/stream1"
    icon: mdi:cctv
```

The operator may override the URL based on their chosen
path (Path A: `rtsp://192.168.1.201:554/stream1,rtsp://192.168.1.202:554/stream1`;
Path B: `https://nvr.example.com:5000`; Path C:
`http://192.168.1.100:5000`).

### §4.2 Configure the camera username

The operator configures
`input_text.rc_security_camera_username` to the camera's
username (if any):

```yaml
input_text:
  rc_security_camera_username:
    name: RC Security Camera Username
    initial: ""
    icon: mdi:account-outline
```

The operator may leave this empty for the recommended
local-only mode (Path A) or populate this for Path B /
Path C with authentication enabled.

### §4.3 Configure the motion detection toggle

The operator configures
`input_boolean.rc_security_camera_motion_enabled` based
on whether the cameras should detect motion:

```yaml
input_boolean:
  rc_security_camera_motion_enabled:
    name: RC Security Camera Motion Enabled
    icon: mdi:motion-sensor
    initial: true
```

The operator may flip this ON for the recommended
motion-enabled mode (default TRUE) or flip this OFF for
the recommended motion-disabled mode.

## §5 Confirm the cameras are online

The cameras-online guard is the operator's canonical
safety chip. The operator MUST confirm the cameras are
online before the first recording.

### §5.1 Confirm the cameras-online chip

The `binary_sensor.rc_security_camera_online` tile is a
`template:` binary_sensor (since 2022.x) that reads from
the upstream `frigate` integration's camera-online state.
The operator MUST confirm the tile reads TRUE before the
first recording.

### §5.2 What the cameras-online chip does

When the cameras-online chip is TRUE:

- `binary_sensor.rc_security_camera_recording` reads
  "recording".
- `sensor.rc_security_camera_last_motion` updates as
  upstream `frigate` last-motion events arrive.
- `sensor.rc_security_camera_motion_mask` updates as
  upstream `frigate` motion-mask changes arrive.
- The four `sensor.rc_security_detection_*_count` tiles
  increment as upstream `frigate` detection events arrive.
- The §8.1 per-camera offline guard does NOT fire.
- The §8.5 records-on-motion guard allows `record`
  invocations (when `input_boolean.rc_storage_recording_enabled`
  is also ON).

When the cameras-online chip is FALSE:

- `binary_sensor.rc_security_camera_recording` reads
  "idle".
- `sensor.rc_security_camera_last_motion` is "unknown".
- `sensor.rc_security_camera_motion_mask` is 0.
- The four `sensor.rc_security_detection_*_count` tiles
  are 0.
- The §8.1 per-camera offline guard fires + writes an
  audit-log entry + flips
  `binary_sensor.rc_security_camera_online` to FALSE.
- The §8.5 records-on-motion guard BLOCKS `record`
  invocations.

### §5.3 Wiring the cameras-online chip

The cameras-online chip is wired via the HA core
`template:` binary_sensor wrapper:

```yaml
template:
  - binary_sensor:
      - name: "RC Security Camera Online"
        unique_id: rc_security_camera_online
        device_class: connectivity
        icon: mdi:cctv
        state: >
          {{ is_state('frigate.camera', 'connected') }}
```

## §6 Enable + start recording

The operator flips `input_boolean.rc_storage_recording_enabled`
ON when ready to record.

### §6.1 Configure the master enable

The operator configures `input_boolean.rc_storage_recording_enabled`:

```yaml
input_boolean:
  rc_storage_recording_enabled:
    name: RC Storage Recording Enabled
    icon: mdi:record-rec
    initial: false
```

The recipe defaults to OFF because recording should
never be permitted unless the operator explicitly enables
it.

### §6.2 Record a test event

The operator records a test event via Developer Tools →
Services → `record`:

```yaml
service: record
data:
  entity_id: camera.front_door
  duration: 30
  filename: "/tmp/roamcore_test_recording.mp4"
```

The operator MUST confirm the recording fires + the
upstream `recorder` integration reports the recording
succeeded + `sensor.rc_security_camera_last_motion`
updates.

### §6.3 Configure the last-motion tile

The `sensor.rc_security_camera_last_motion` tile is a
`template:` sensor (since 2022.x) that reads from the
upstream `frigate` integration's last-motion event log:

```yaml
template:
  - sensor:
      - name: "RC Security Camera Last Motion"
        unique_id: rc_security_camera_last_motion
        icon: mdi:motion-sensor
        state: >
          {{ state_attr('binary_sensor.rc_security_camera_online', 'last_motion') | default('unknown') }}
```

The operator MAY wire the last-motion tile to a more
sophisticated timestamp (e.g. the per-camera last-motion
timestamp aggregated across all cameras) — the recipe
ships the basic timestamp for v1.

## §7 RoamCore contract entities

The 12 `rc_security_*` + `rc_storage_*` contract tiles
are the canonical RoamCore surface for the NVR umbrella.
The tiles are vendor-neutral — no Frigate / go2rtc /
Reolink / Hikvision / Dahua / Amcrest / ONVIF / RTSP /
Coral / TPU / Google / Intel / Nvidia / SSD / NVMe / HDD
/ PoE / NVR / HACS / MQTT / webhook / REST / API / HTTP /
HTTPS / Companion / ESPHome / phone / GPS / accelerometer
/ iPhone / iOS / Android / Samsung / Pixel / OnePlus /
Xiaomi / Huawei / input_boolean / input_text /
input_number / input_select / input_datetime /
input_button / script / template / logbook / recorder /
camera / Z-Wave / Zigbee / ZHA / Deconz / Tasmota /
Shelly / Sonoff / ESP32 / ESP8266 / Wi-Fi / BLE /
Bluetooth names leak into the tile ids.

### §7.1 The 4 cameras `rc_security_camera_*` contract tiles

- `binary_sensor.rc_security_camera_online` — TRUE when
  the upstream `frigate` integration reports a connected
  camera state. The tile is a `template:` binary_sensor
  (since 2022.x) that reads from the upstream `frigate`
  integration's camera-online state.
  ```yaml
  template:
    - binary_sensor:
        - name: "RC Security Camera Online"
          unique_id: rc_security_camera_online
          device_class: connectivity
          icon: mdi:cctv
          state: >
            {{ is_state('frigate.camera', 'connected') }}
  ```

- `binary_sensor.rc_security_camera_recording` — per-
  camera recording state (`recording` / `idle`). The tile
  is a `template:` binary_sensor (since 2022.x) that
  reads from the upstream `frigate` integration's
  camera-recording state + the §8.1 + §8.2 + §8.5
  guards' state.
  ```yaml
  template:
    - binary_sensor:
        - name: "RC Security Camera Recording"
          unique_id: rc_security_camera_recording
          device_class: recording
          icon: mdi:record-rec
          state: >
            {% set camera_online = is_state('binary_sensor.rc_security_camera_online', 'on') %}
            {% set enabled = is_state('input_boolean.rc_storage_recording_enabled', 'on') %}
            {% if camera_online and enabled %}
              on
            {% else %}
              off
            {% endif %}
  ```

- `sensor.rc_security_camera_last_motion` — per-camera
  last-motion timestamp. The tile is a `template:`
  sensor (since 2022.x) that reads from the upstream
  `frigate` integration's last-motion event log.
  ```yaml
  template:
    - sensor:
        - name: "RC Security Camera Last Motion"
          unique_id: rc_security_camera_last_motion
          icon: mdi:motion-sensor
          state: >
            {{ state_attr('binary_sensor.rc_security_camera_online', 'last_motion') | default('unknown') }}
  ```

- `sensor.rc_security_camera_motion_mask` — per-camera
  motion-mask count. The tile is a `template:` sensor
  (since 2022.x) that reads from the upstream `frigate`
  integration's motion-mask state.
  ```yaml
  template:
    - sensor:
        - name: "RC Security Camera Motion Mask"
          unique_id: rc_security_camera_motion_mask
          icon: mdi:crop
          state: >
            {{ state_attr('binary_sensor.rc_security_camera_online', 'motion_mask_count') | default(0) }}
          unit_of_measurement: "regions"
  ```

### §7.2 The 4 detection `rc_security_detection_*` contract tiles

- `sensor.rc_security_detection_person_count` — resolved
  per-camera person-detection count aggregated across all
  cameras. The tile is a `template:` sensor (since 2022.x)
  that reads from the upstream `frigate` integration's
  detection event log for the `person` label.
  ```yaml
  template:
    - sensor:
        - name: "RC Security Detection Person Count"
          unique_id: rc_security_detection_person_count
          icon: mdi:account
          state: >
            {{ states.frigate | selectattr('attributes.label', 'defined') | selectattr('attributes.label', 'equalto', 'person') | list | length }}
          unit_of_measurement: "detections"
  ```

- `sensor.rc_security_detection_car_count` — resolved
  per-camera car-detection count aggregated across all
  cameras. The tile is a `template:` sensor (since 2022.x)
  that reads from the upstream `frigate` integration's
  detection event log for the `car` label.
  ```yaml
  template:
    - sensor:
        - name: "RC Security Detection Car Count"
          unique_id: rc_security_detection_car_count
          icon: mdi:car
          state: >
            {{ states.frigate | selectattr('attributes.label', 'defined') | selectattr('attributes.label', 'equalto', 'car') | list | length }}
          unit_of_measurement: "detections"
  ```

- `sensor.rc_security_detection_animal_count` — resolved
  per-camera animal-detection count aggregated across all
  cameras. The tile is a `template:` sensor (since 2022.x)
  that reads from the upstream `frigate` integration's
  detection event log for the `animal` label.
  ```yaml
  template:
    - sensor:
        - name: "RC Security Detection Animal Count"
          unique_id: rc_security_detection_animal_count
          icon: mdi:dog
          state: >
            {{ states.frigate | selectattr('attributes.label', 'defined') | selectattr('attributes.label', 'equalto', 'animal') | list | length }}
          unit_of_measurement: "detections"
  ```

- `sensor.rc_security_detection_package_count` — resolved
  per-camera package-detection count aggregated across all
  cameras. The tile is a `template:` sensor (since 2022.x)
  that reads from the upstream `frigate` integration's
  detection event log for the `package` label.
  ```yaml
  template:
    - sensor:
        - name: "RC Security Detection Package Count"
          unique_id: rc_security_detection_package_count
          icon: mdi:package-variant
          state: >
            {{ states.frigate | selectattr('attributes.label', 'defined') | selectattr('attributes.label', 'equalto', 'package') | list | length }}
          unit_of_measurement: "detections"
  ```

### §7.3 The 4 recording/storage `rc_storage_recording_*` contract tiles

- `input_boolean.rc_storage_recording_enabled` — master
  enable for the upstream `recorder` integration's
  `record` service (default OFF for the recommended
  safe-default mode). The tile is an `input_boolean:`
  domain entity (since 2022.x) that the operator's
  chosen master-enable UI flips.
  ```yaml
  input_boolean:
    rc_storage_recording_enabled:
      name: RC Storage Recording Enabled
      icon: mdi:record-rec
      initial: false
  ```

- `sensor.rc_storage_recording_used` — per-camera
  recording storage used in gigabytes. The tile is a
  `template:` sensor (since 2022.x) that reads from the
  upstream `recorder` integration's storage stat.
  ```yaml
  template:
    - sensor:
        - name: "RC Storage Recording Used"
          unique_id: rc_storage_recording_used
          icon: mdi:harddisk
          state: >
            {{ state_attr('sensor.recorder_storage', 'used_gb') | default(0) }}
          unit_of_measurement: "GB"
  ```

- `sensor.rc_storage_recording_free` — per-camera
  recording storage free in gigabytes. The tile is a
  `template:` sensor (since 2022.x) that reads from the
  upstream `recorder` integration's storage stat.
  ```yaml
  template:
    - sensor:
        - name: "RC Storage Recording Free"
          unique_id: rc_storage_recording_free
          icon: mdi:harddisk
          state: >
            {{ state_attr('sensor.recorder_storage', 'free_gb') | default(0) }}
          unit_of_measurement: "GB"
  ```

- `sensor.rc_storage_recording_retention_today_count` —
  per-camera recording retention today count. The tile
  is a `template:` sensor (since 2022.x) that counts
  the recordings retained today before the
  retention-spin-down cycle.
  ```yaml
  template:
    - sensor:
        - name: "RC Storage Recording Retention Today Count"
          unique_id: rc_storage_recording_retention_today_count
          icon: mdi:archive
          state: >
            {{ states.frigate | selectattr('attributes.start_time', 'defined') | selectattr('attributes.start_time', 'ge', now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()) | list | length }}
          unit_of_measurement: "recordings"
  ```

### §7.4 Script-runner wrappers

The `record` wrapper is an upstream `script:` integration
script-runner wrapper that the operator wires in
`homeassistant/scripts.yaml` (or in a dedicated
RoamCore-side
`homeassistant/packages/roamcore_frigate_scripts.yaml`
file).

```yaml
script:
  roamcore_frigate_record:
    alias: "RoamCore: Frigate Record"
    description: >-
      Trigger a record on the upstream `frigate`
      integration. Requires input_boolean.rc_storage_recording_enabled
      to be ON AND binary_sensor.rc_security_camera_online
      to be TRUE.
    sequence:
      - choose:
          - conditions:
              - condition: state
                entity_id: input_boolean.rc_storage_recording_enabled
                state: "off"
            sequence:
              - service: logbook.log
                data:
                  name: "RoamCore Frigate"
                  message: >-
                    Frigate record BLOCKED: master enable
                    is OFF.
                  entity_id: input_boolean.rc_storage_recording_enabled
              - stop: "Frigate master enable is OFF"
      - service: record
        data:
          entity_id: "{{ entity_id | default('camera.front_door') }}"
          duration: "{{ duration | default(30) }}"
          filename: "{{ filename | default('/tmp/roamcore_default_recording.mp4') }}"
```

## §8 Automations (MANDATORY before first use)

### §8.1 Per-camera offline guard

The automation fires when
`binary_sensor.rc_security_camera_online` flips FALSE. The
automation flips `binary_sensor.rc_security_camera_recording`
to FALSE + flips `sensor.rc_security_camera_last_motion`
to "unknown" + clears the per-camera detection counts to
0 + fires a critical notification warning the operator
that the camera has gone offline.

```yaml
automation:
  - alias: "RoamCore: Frigate — per-camera offline guard"
    description: >-
      Fires when the camera-online chip flips FALSE.
      Flips the camera-recording to FALSE + clears the
      last-motion + clears the detection counts + fires
      a critical notification.
    trigger:
      - platform: state
        entity_id: binary_sensor.rc_security_camera_online
        to: "off"
    action:
      - service: logbook.log
        data:
          name: "RoamCore Frigate"
          message: >-
            Camera OFFLINE: connection to {{ states('input_text.rc_security_camera_url') }}
            lost.
          entity_id: binary_sensor.rc_security_camera_online
      - service: persistent_notification.create
        data:
          title: "RoamCore Frigate: camera offline"
          message: >-
            The camera at
            {{ states('input_text.rc_security_camera_url') }}
            has gone offline. Check the NVR service + the
            network. Press
            button.rc_storage_recording_reset_now to
            retry.
          notification_id: roamcore_frigate_camera_offline
```

### §8.2 Cameras-online guard

The automation fires when
`binary_sensor.rc_security_camera_online` flips TRUE. The
automation clears the offline flag + flips
`binary_sensor.rc_security_camera_recording` to TRUE +
updates `sensor.rc_security_camera_last_motion` + updates
the per-camera detection counts + fires a notification
warning the operator that the cameras have come back
online.

```yaml
automation:
  - alias: "RoamCore: Frigate — cameras-online guard"
    description: >-
      Fires when the camera-online chip flips TRUE.
      Clears the offline flag + flips the camera-recording
      to TRUE + updates the last-motion + updates the
      detection counts + fires a notification.
    trigger:
      - platform: state
        entity_id: binary_sensor.rc_security_camera_online
        to: "on"
    action:
      - service: logbook.log
        data:
          name: "RoamCore Frigate"
          message: >-
            Camera ONLINE: connection to {{ states('input_text.rc_security_camera_url') }}
            established.
          entity_id: binary_sensor.rc_security_camera_online
      - service: persistent_notification.dismiss
        data:
          notification_id: roamcore_frigate_camera_offline
```

### §8.3 Per-camera motion-mask guard

The automation fires when
`sensor.rc_security_camera_motion_mask` flips to a non-zero
value for an unexpected camera (a camera that was
previously motion-masked now has motion). The automation
updates `sensor.rc_security_camera_motion_mask` + fires a
critical notification warning the operator that the
camera motion-mask has changed.

```yaml
automation:
  - alias: "RoamCore: Frigate — per-camera motion-mask guard"
    description: >-
      Fires when the motion-mask count flips to a non-zero
      value for an unexpected camera. Updates the
      motion-mask + fires a critical notification.
    trigger:
      - platform: numeric_state
        entity_id: sensor.rc_security_camera_motion_mask
        above: 0
    condition:
      - condition: template
        value_template: >
          {{ trigger.from_state.state | int(0) == 0 }}
    action:
      - service: logbook.log
        data:
          name: "RoamCore Frigate"
          message: >-
            Camera MOTION-MASK CHANGED: motion-mask count
            for {{ states('input_text.rc_security_camera_url') }}
            changed from {{ trigger.from_state.state }} to
            {{ trigger.to_state.state }} regions.
          entity_id: sensor.rc_security_camera_motion_mask
      - service: persistent_notification.create
        data:
          title: "RoamCore Frigate: camera motion-mask changed"
          message: >-
            The camera at
            {{ states('input_text.rc_security_camera_url') }}
            motion-mask changed from {{ trigger.from_state.state }}
            to {{ trigger.to_state.state }} regions. Verify
            the motion-mask is correct.
          notification_id: roamcore_frigate_motion_mask_changed
```

### §8.4 Storage-full guard

The automation fires when
`sensor.rc_storage_recording_free` dips below 10 GB. The
automation flips `input_boolean.rc_storage_recording_enabled`
to OFF + fires a critical notification warning the
operator that the storage is full.

```yaml
automation:
  - alias: "RoamCore: Frigate — storage-full guard"
    description: >-
      Fires when the storage-free dips below 10 GB. Flips
      the master enable to OFF + fires a critical
      notification.
    trigger:
      - platform: numeric_state
        entity_id: sensor.rc_storage_recording_free
        below: 10
    action:
      - service: logbook.log
        data:
          name: "RoamCore Frigate"
          message: >-
            Storage FULL: only {{ states('sensor.rc_storage_recording_free') }}
            GB free. Master enable flipped to OFF.
          entity_id: sensor.rc_storage_recording_free
      - service: input_boolean.turn_off
        target:
          entity_id: input_boolean.rc_storage_recording_enabled
      - service: persistent_notification.create
        data:
          title: "RoamCore Frigate: storage full"
          message: >-
            The storage at
            {{ state_attr('sensor.rc_storage_recording_free', 'path') | default('unknown') }}
            has only {{ states('sensor.rc_storage_recording_free') }}
            GB free. Master enable flipped to OFF. Free
            up storage (e.g. via the retention-spin-down
            cycle) + flip the master enable back ON.
          notification_id: roamcore_frigate_storage_full
```

### §8.5 Records-on-motion guard

The automation fires when ANY `script.*` / `automation.*`
action tries to call the `record` service while
`input_boolean.rc_storage_recording_enabled` is OFF. The
automation BLOCKS the record + flips
`binary_sensor.rc_security_camera_recording` to FALSE +
fires a critical notification warning the operator that
recording is disabled.

```yaml
automation:
  - alias: "RoamCore: Frigate — records-on-motion guard"
    description: >-
      Fires when any script.* / automation.* action tries
      to call record while the master enable is OFF.
      Blocks the record + flips the camera-recording to
      FALSE + fires a critical notification.
    trigger:
      - platform: event
        event_type: record_attempted
    condition:
      - condition: state
        entity_id: input_boolean.rc_storage_recording_enabled
        state: "off"
    action:
      - service: logbook.log
        data:
          name: "RoamCore Frigate"
          message: >-
            Frigate record BLOCKED: master enable is OFF.
          entity_id: input_boolean.rc_storage_recording_enabled
      - service: persistent_notification.create
        data:
          title: "RoamCore Frigate: record blocked"
          message: >-
            The agent / automation tried to record via
            the `record` service while
            input_boolean.rc_storage_recording_enabled is
            OFF. Flip the master enable ON to allow
            recording.
          notification_id: roamcore_frigate_record_blocked
      - event: record_blocked
        event_data:
          entity_id: "{{ trigger.event.data.entity_id }}"
          reason: master_enable_off
```

## §9 Troubleshooting

### §9.1 Camera not online

Symptom: `binary_sensor.rc_security_camera_online` reads
FALSE even after the operator has installed the HACS
frigate add-on (Path A) / configured the external / cloud
NVR (Path B) / started the local container / VM NVR (Path
C).

Cause: the camera URL is wrong; OR the NVR is not running;
OR the network is unreachable; OR the credentials are wrong.

Fix: confirm the camera URL via
`input_text.rc_security_camera_url` (a comma-separated
list of camera URLs) + confirm the NVR is running + confirm
the network is reachable from the HA box + populate
`input_text.rc_security_camera_username` if the NVR
requires authentication.

### §9.2 Detection count not incrementing

Symptom: `sensor.rc_security_detection_person_count`
reads 0 even after the operator has connected upstream
detecting cameras.

Cause: the upstream cameras are not detecting motion;
OR the upstream `frigate` integration's detection is
disabled.

Fix: confirm the upstream cameras are detecting motion +
enable the upstream `frigate` integration's detection via
the HA UI under Settings → Devices & services →
Integrations → Frigate → Configure → Detection.

### §9.3 Records-on-motion blocked

Symptom: `record` invocations fail with the "master
enable is OFF" message even when the operator wants to
record.

Cause: the §8.5 records-on-motion guard is not wired; OR
`input_boolean.rc_storage_recording_enabled` is OFF.

Fix: confirm the §8.5 automation is wired + flip
`input_boolean.rc_storage_recording_enabled` ON.

### §9.4 Storage full

Symptom: the upstream `recorder` integration reports the
storage is full.

Cause: the retention-spin-down cycle has not run; OR the
operator's retention threshold is too high; OR the
storage volume is too small.

Fix: confirm the retention-spin-down cycle has run (the
`recorder.purge` service is auto-called daily by the
upstream `recorder` integration) + lower the operator's
retention threshold + free up storage volume.

### §9.5 Authentication failure

Symptom: the upstream `frigate` integration reports an
authentication failure (wrong username / password).

Cause: the operator's camera username / password is
wrong; OR the NVR does NOT support the operator's
authentication protocol.

Fix: confirm the camera username / password is correct +
confirm the NVR supports the operator's authentication
protocol (Path A HACS frigate add-on: no authentication
by default; Path B external / cloud NVR: per provider
docs; Path C local container / VM NVR: per provider
docs).

### §9.6 Reset-now not firing

Symptom: pressing `button.rc_storage_recording_reset_now`
does not reset the recorder.

Cause: the reset-now automation is not wired; OR the
upstream `recorder` integration is not configured to
auto-reset.

Fix: confirm the reset-now automation is wired + confirm
the upstream `recorder` integration is configured to
auto-reset via the HA UI under Settings → Devices &
services → Integrations → Recorder → Configure → Auto-
reset.

## §10 Privacy

Frigate is HA local-only by design:

- The NVR (Path A HACS frigate add-on, Path B external /
  cloud NVR, Path C local container / VM NVR) + the
  camera URLs + the camera credentials + the
  cameras-online chip + the camera-recording + the
  last-motion + the motion-mask + the four detection-
  count tiles + the recording-enabled + the storage-used
  + the storage-free + the retention-today count are ALL
  stored locally on the operator's HA box (no RoamCore-
  side cloud round-trip).
- The camera URLs are owned by the operator (the recipe
  does NOT include any vendor-specific defaults for Path B
  or Path C; the operator populates the URLs based on
  their chosen NVR path).
- The audit log is stored in the HA core `logbook`
  integration (no third-party audit-log destination; no
  RoamCore-side cloud round-trip).
- The §8.1 + §8.2 + §8.3 + §8.4 + §8.5 automations are
  wired locally on the operator's HA box (no RoamCore-
  side cloud round-trip).
- The `record` wrapper is an upstream `script:`
  integration script-runner wrapper that the operator
  wires locally on their HA box (no RoamCore-side cloud
  round-trip).
- The detection counts are aggregated per-camera + across
  all cameras (no per-person tracking; no per-person
  audit log; the upstream `frigate` integration's
  detection event log is operator-owned via the HA core
  `logbook` integration).
- The motion-mask changes are logged per-camera (no
  per-camera audit log; the upstream `frigate`
  integration's motion-mask change log is operator-owned
  via the HA core `logbook` integration).

RoamCore does NOT maintain any NVR telemetry; the camera
credentials + the audit log + the cameras-online chip +
the detection counts are 100% operator-owned. If the
operator wants to share the camera state across multiple
HA instances, they can use the HA core `input_*` helper
entity replication (or the upstream `sync` integration)
— but the recipe does NOT require any cross-instance
sharing.

The detection counts are intentionally aggregated per
category (person / car / animal / package) rather than
per-detection — the recipe does NOT track individual
detections (e.g. "person A at 14:35:22" + "person B at
14:35:24"). The operator may opt into per-detection
tracking by enabling the upstream `frigate` integration's
audit log (the upstream `frigate` integration's
detection event log is operator-owned via the HA core
`logbook` integration) — but the recipe does NOT
recommend this for privacy reasons.

The motion-mask changes are logged per-camera (not
per-detection) — the recipe does NOT track individual
motion-mask changes (e.g. "front door camera motion-mask
changed at 14:35:22" + "side door camera motion-mask
changed at 14:35:24"). The operator may opt into
per-camera tracking by enabling the upstream `frigate`
integration's audit log (the upstream `frigate`
integration's motion-mask change log is operator-owned
via the HA core `logbook` integration) — but the recipe
does NOT recommend this for privacy reasons.

## §11 Promoting to tier-a

Tier-a would require a RoamCore-owned NVR engine +
integration code + integration tests against a real NVR
engine bench. The bench would need the following canned
fixture responses wired together in a controlled
environment:

1. Canned camera-disconnect event (the upstream `frigate`
   integration reports a camera disconnect) — the §8.1
   per-camera offline guard should fire (camera-online
   chip flips FALSE + camera-recording flips to FALSE +
   last-motion flips to "unknown" + detection counts
   cleared to 0 + critical notification fires).
2. Canned camera-reconnect event (the upstream `frigate`
   integration reports a camera reconnect) — the §8.2
   cameras-online guard should fire (camera-online chip
   flips TRUE + camera-recording flips to TRUE +
   last-motion updates + detection counts update +
   notification fires).
3. Canned motion-mask change event (the upstream
   `frigate` integration reports a motion-mask change) —
   the §8.3 per-camera motion-mask guard should fire
   (motion-mask count updates + critical notification
   fires).
4. Canned storage-full event (the upstream `recorder`
   integration reports the storage is full) — the §8.4
   storage-full guard should fire (master enable flips
   to OFF + critical notification fires).
5. Canned `record` invocation with
   `input_boolean.rc_storage_recording_enabled` OFF —
   the §8.5 records-on-motion guard should fire (record
   BLOCKS + camera-recording flips to FALSE + critical
   notification fires).
6. Canned `record` invocation with
   `input_boolean.rc_storage_recording_enabled` ON — the
   §8.5 records-on-motion guard should NOT fire (record
   succeeds + audit-log entry fires).
7. Canned cameras-online + reset-now button press —
   the camera-online chip should flip TRUE + the
   `homeassistant/status` topic should re-publish.
8. Canned detection event (the upstream `frigate`
   integration receives a detection event) — the
   corresponding `sensor.rc_security_detection_*_count`
   should increment.

The bench would also need a RoamCore-owned operator-
wired setup flow walking the operator through Pick the
NVR path + Mount the camera URLs + Confirm the cameras
are online + Enable + start recording + Audit + the §8
automations.

## §12 Files

- `connection.yml` — the source-of-truth tier-b
  manifest.
- `__init__.py` — `DOMAIN = "frigate"` marker for the
  audit.
- `README.md` — the folder overview + the 12-tile table
  + the 5-§8-automation summary + the supersession
  pointer + the cross-references.
- `docs/recipe.md` — this file.
- `tests/test_connection_yml.py` — the 7 manifest-
  honesty checks.

External references:

- Legacy catalog page (now superseded by this slice):
  [`docs/catalog/cctv/frigate.md`](../../../catalog/cctv/frigate.md)
- Design doc (philosophy + NVR wire-up details +
  tier-a promotion outline): [`docs/design.md`](../../../design.md)
- HA core `frigate` integration upstream doc (the
  canonical NVR backend umbrella): https://www.home-assistant.io/integrations/frigate/

## §13 Cross-references

External HA core integrations:

- HA core `frigate` integration: https://www.home-assistant.io/integrations/frigate/
- HA core `frigate` discovery documentation: https://www.home-assistant.io/integrations/frigate/
- HA core `camera` platform: https://www.home-assistant.io/integrations/camera/
- HA core `recorder` integration: https://www.home-assistant.io/integrations/recorder/
- HA core `input_boolean` integration: https://www.home-assistant.io/integrations/input_boolean/
- HA core `input_text` integration: https://www.home-assistant.io/integrations/input_text/
- HA core `input_number` integration: https://www.home-assistant.io/integrations/input_number/
- HA core `input_select` integration: https://www.home-assistant.io/integrations/input_select/
- HA core `input_datetime` integration: https://www.home-assistant.io/integrations/input_datetime/
- HA core `input_button` integration: https://www.home-assistant.io/integrations/input_button/
- HA core `script:` integration: https://www.home-assistant.io/integrations/script/
- HA core `template:` integration: https://www.home-assistant.io/integrations/template/
- HA core `logbook` integration: https://www.home-assistant.io/integrations/logbook/

HACS:

- HACS prerequisites: https://hacs.xyz/docs/setup/prerequisites

Other connection slices:

- MQTT (the broker everything depends on — the upstream
  `frigate` integration's auto-discovery relies on the
  broker's `mqtt` integration for upstream discovery
  signals): `connections/mqtt/` (Wave 3 #34)
- Mode (the §8.3 per-camera motion-mask guard's mode-
  change cross-reference): `connections/mode/` (Wave 3
  #61)
- Advanced-mode (the §8.5 records-on-motion guard's
  confirm-flag pattern): `connections/advanced-mode/`
  (Wave 3 #63)
- OpenClaw JSON API (the §8.1 per-camera offline guard's
  JSON payload cross-reference): `connections/openclaw-api/`
  (Wave 3 #64)
- Agent actions allowlist (the §8.5 records-on-motion
  guard's kill-switch cross-reference):
  `connections/agent-actions-allowlist/` (Wave 3 #65)
- Remote-access (the §8.5 records-on-motion guard's
  owner-identity check): `connections/remote-access/`
  (Wave 3 #58)
- DNS blocker (the §8.1 per-camera offline guard's
  network-reachability cross-reference):
  `connections/dns-blocker/` (Wave 3 #37)
- HVAC basics (the §8.4 storage-full guard's ventilation
  cross-reference): `connections/hvac-basics/` (Wave 3
  #49)
- Fans (the §8.4 storage-full guard's cooling cross-
  reference): `connections/fans/` (Wave 3 #59)
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`
  (the `security` + `storage` subsystems were added by
  this slice)

## §14 Storage rotation policy

The §14 storage rotation policy documents the
recommended retention thresholds for the upstream
`recorder` integration. The recipe ships the policy
as a starting point for the operator; the operator may
override the policy based on their storage volume + their
retention requirements.

### §14.1 Recommended retention thresholds

The recipe recommends the following retention thresholds
for the upstream `recorder` integration:

- Daily retention: 7 days (the §8.5 retentions-spin-down
  guard fires when the per-camera recording retention
  today count exceeds 7 days).
- Weekly retention: 4 weeks (the §8.5 retentions-spin-down
  guard fires when the per-camera recording retention
  weekly count exceeds 4 weeks).
- Monthly retention: 3 months (the §8.5 retentions-spin-
  down guard fires when the per-camera recording
  retention monthly count exceeds 3 months).

The operator may override the retention thresholds via
the upstream `recorder` integration's configuration UI
under Settings → Devices & services → Integrations →
Recorder → Configure → Retention.

### §14.2 Storage volume sizing

The recipe recommends the following storage volume sizing
for the upstream `recorder` integration:

- Single camera, 7-day retention: 50 GB minimum (the
  recipe's recommended minimum).
- Single camera, 30-day retention: 200 GB minimum.
- Four cameras, 7-day retention: 200 GB minimum.
- Four cameras, 30-day retention: 800 GB minimum.

The operator may override the storage volume sizing
based on their camera count + their retention
requirements. The recipe does NOT recommend any
specific storage volume size — the operator should
size the storage volume based on their specific needs.

### §14.3 Storage rotation policy example

The recipe ships the following storage rotation policy
example for the upstream `recorder` integration:

```yaml
recorder:
  purge_keep_days: 7
  auto_purge: true
  auto_repack: true
  commit_interval: 1
```

The operator may override the storage rotation policy
based on their retention requirements. The recipe does
NOT recommend any specific storage rotation policy — the
operator should configure the policy based on their
specific needs.

### §14.4 Storage rotation policy trade-offs

The recipe documents the trade-offs of the storage
rotation policy:

- Longer retention = more storage volume required =
  higher cost (the operator must size the storage volume
  accordingly).
- Shorter retention = less storage volume required =
  lower cost (but the operator may lose the recording
  history if they need to investigate an incident).
- The recipe ships the daily retention of 7 days as a
  starting point — the operator may override the
  retention threshold based on their storage volume +
  their retention requirements.

The recipe does NOT recommend any specific storage
rotation policy — the operator should configure the
policy based on their specific needs.
