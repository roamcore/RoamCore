# Frigate — tier-b recipe connection

**Tier:** B (recipe)
**Audience:** A RoamCore user who has Home Assistant running, RTSP/
ONVIF-capable IP cameras on the LAN, an SSD/NVMe volume for recordings,
and wants the on-device ML object detection NVR that powers the
RoamCore `rc_security_*` contract tiles + OpenClaw security queries.

This howto is mirrored into `docs/connections/frigate.md` by the catalog
cron (`scripts/build_catalog.py`) so it shows up under the public docs
site's "Connections" section. Keep this recipe as the source of truth.

## What is Frigate in RoamCore?

Frigate (<https://frigate.video/>) is a self-hosted NVR with **on-device
ML object detection**. It runs as a Docker container (the recommended
path is the HA community add-on `core- frigate`, or external Docker)
and:

- pulls RTSP/ONVIF streams from your IP cameras,
- runs object detection (person, car, animal, package, license plate,
  etc.) locally on CPU, Intel GPU, or Google Coral,
- records to a local SSD/NVMe volume with per-event and per-alert
  retention policies,
- publishes `frigate/events` + `frigate/available` on MQTT,
- re-streams the live view via `go2rtc` (bundled) for the HA dashboard.

In RoamCore, Frigate is the CCTV backend. We do **not** ship a Frigate
container of our own. Instead we publish the documented setup for the
upstream HA core `frigate` integration
(<https://www.home-assistant.io/integrations/frigate/>, ships in HA
core, has had a config_flow since 2022.4) and layer a small contract on
top: the `rc_security_camera_*` and `rc_security_recording_*` dashboard
tiles + the OpenClaw queries ("is anyone at the door right now?",
"any cars in the driveway?", "show me motion events from the last
hour") that bind to those contract entities.

**Why tier-b:** RoamCore has no real Frigate container on the bench to
integration-test against (the CI bench is a container, not a video-
recording box with a Coral accelerator + RTSP cameras), so we honestly
stay at tier-b. The recipe is sound — it leans on the well-tested core
`frigate` integration — but we cannot claim one-tap automation. The
promotion outline at the bottom of this recipe describes exactly what
needs to happen to flip this to tier-a.

**Two install paths:**

- **Path A — Frigate HA add-on** (recommended for RoamCore users
  running HAOS / supervised): the `core- frigate` community add-on,
  managed from the HA UI, gets you up in ~15 minutes.
- **Path B — External Docker** (for power users who want full control
  over the Frigate version, Coral accelerator, or storage layout): run
  Frigate + go2rtc as standalone containers on the LAN and point HA at
  them.

## Prerequisites

Before starting the recipe, make sure you have:

- **Home Assistant 2024.8 or newer** (the upstream `frigate` integration
  has been core since 2022.4; we pin 2024.8 to match the rest of
  RoamCore's `min_ha_version` baseline).
- **IP cameras with RTSP or ONVIF.** Most modern PoE cameras (Hikvision,
  Dahua, Reolink, Amcrest, UniFi, etc.) speak RTSP out of the box. Get
  the RTSP URL from the camera's web UI or its app.
- **A PoE switch or reliable Wi-Fi.** Wired PoE is strongly preferred
  for CCTV — bandwidth + reliability. If you must use Wi-Fi, prefer
  5 GHz and cameras close to the AP.
- **SSD or NVMe storage.** 1 TB minimum for a single 1080p camera with
  14-day retention; 2–4 TB for a 4-camera system. USB spinning rust
  will choke on the write throughput. The Frigate add-on mounts this as
  `/media/frigate` inside the container; external Docker mounts it
  wherever you declare.
- **Docker** (Path B only) — Docker 20.10+ with compose v2.
- **MQTT broker** (recommended) — the Mosquitto broker from
  `connections/mqtt/` carries `frigate/events` to the RoamCore contract
  layer. Path A can install Mosquitto at the same time; Path B
  typically already has it.
- **(Optional) Google Coral USB accelerator or Intel Arc / iGPU.** Frigate
  runs object detection on CPU by default; a Coral USB stick gives you
  ~10 ms/inference and lets you run detection on 4+ cameras in parallel
  on modest hardware. Skip it for a 1-camera setup.

## Path A — Frigate HA add-on (recommended)

The default install for RoamCore users running HAOS or HA Supervised.

### A.1 — Add the community add-on repository (if not already)

1. HA → **Settings → Add-ons → Add-on Store** → ⋮ menu (top right) →
   **Repositories**.
2. Add `https://github.com/home-assistant/addons` (the official HA
   Community Add-ons). If you already have it, skip this step.

### A.2 — Install the Mosquitto broker add-on (if you don't have one yet)

Frigate publishes object-detection events on MQTT. You need a broker.

1. HA → **Settings → Add-ons → Add-on Store** → search for **Mosquitto
   broker** (the official add-on published by the HA team).
2. Click **Install**. Set a username + password in the **Configuration**
   tab. For local-only, leave `require_certificate: false`.
3. **Start** the add-on. Check the **Log** tab — you should see
   `mosquitto version X.Y.Z starting` with no errors.

If you already run a Mosquitto broker (Path B, or external), point
Frigate at it in A.4 below.

### A.3 — Install the Frigate add-on

1. HA → **Settings → Add-ons → Add-on Store** → search for **Frigate**
   (the community add-on, slug `core- frigate` or `a0d359d9-frigate`).
2. Click **Install**. Wait for it to finish — this pulls the Frigate
   Docker image + go2rtc.
3. Open the **Configuration** tab. Paste a minimal `config.yaml` (see
   A.4) and set the **Storage** section to mount your SSD/NVMe volume
   to `/media/frigate`.
4. Start the add-on. The **Log** tab will show go2rtc starting, Frigate
   loading the config, and (once you have cameras configured) the
   per-camera stream status.

### A.4 — A minimal `config.yaml` for Frigate

Drop this into the add-on's **Configuration** tab. It declares one
camera, points MQTT at the Mosquitto broker, and sets sensible
retention policies. Replace `front_door` with the name of your camera
and the RTSP URL with the URL your camera gives you (usually
`rtsp://user:pass@<ip>:554/h264Preview` or similar).

```yaml
mqtt:
  enabled: true
  host: core-mosquitto          # the Mosquitto add-on's slug
  port: 1883
  username: roamcore
  password: change-me-strong
  topic_prefix: frigate
  client_id: frigate
  stats_interval: 60

cameras:
  front_door:
    enabled: true
    ffmpeg:
      inputs:
        - path: rtsp://user:pass@192.168.1.201:554/h264Preview
          roles:
            - detect
            - rtmp           # so go2rtc can restream for HA
    detect:
      width: 1280
      height: 720
      fps: 5
    objects:
      track:
        - person
        - car
        - animal
        - package

record:
  enabled: true
  retain:
    days: 14
    mode: motion
  events:
    retain:
      default: 14
      mode: active_objects
  alerts:
    retain: 30                  # keep alert clips longer (30 days)

snapshots:
  enabled: true
  retain:
    default: 14

go2rtc:
  enabled: true
  streams:
    front_door:
      - rtsp://user:pass@192.168.1.201:554/h264Preview
```

Notes:

- `record.events.retain.mode: active_objects` is the recommended
  setting — it keeps the pre-buffer + post-buffer around an actual
  detected object, not around motion-only frames.
- `go2rtc.streams` mirrors the camera input so HA's live view pulls a
  low-latency restream (sub-200 ms) instead of the heavier RTSP
  stream.
- Bump `detect.fps` to 10 if you have a Coral accelerator; keep it at
  5 for CPU-only detection.

### A.5 — Restart and watch the logs

1. **Save** the config, then **Restart** the add-on.
2. Watch the **Log** tab. You should see:
   - `mqtt: connected to core-mosquitto:1883` (broker up).
   - `detector: loaded model...` (object-detection model loaded).
   - `camera front_door: started` (per-camera stream up).
3. Open the Frigate add-on's **Web UI** tab (or visit
   `http://<ha-host>:5000` for external Docker). You should see the
   live view of your camera with bounding boxes around detected
   objects.

### A.6 — Add the HA core `frigate` integration

1. HA → **Settings → Devices & Services → Add Integration → Frigate**.
2. Enter the Frigate URL:
   - For the add-on: `http://ccab4aaf-frigate:5000` (the slug is the
     add-on slug from A.3 — find it under **Add-ons → Frigate → Info**
     as "Slug").
   - For external Docker: `http://<frigate-host>:5000`.
3. If your MQTT credentials aren't auto-detected, paste them.
4. Save. HA tests the connection and creates one **device per camera**,
   each with `camera.<name>`, `binary_sensor.<name>_person`, etc.

### A.7 — Verify camera entities appear

In HA → **Developer Tools → States**, search for `camera.front_door`
(or whatever your camera is named). It should be **on** with a live
stream URL. If it's **unavailable**, see **Troubleshooting** below.

## Path B — External Frigate (Docker)

For power users who want full control over the Frigate version, Coral
accelerator, or storage layout, or for users running HA Container /
HA Core on a separate box from the Frigate NVR.

### B.1 — docker-compose.yml

Create a directory like `/opt/frigate` and drop this in:

```yaml
# /opt/frigate/docker-compose.yml
services:
  frigate:
    container_name: frigate
    restart: unless-stopped
    image: ghcr.io/blakeblackshear/frigate:stable
    shm_size: "64mb"           # bump if you see shmem errors
    devices:
      - /dev/bus/usb:/dev/bus/usb   # Coral USB accelerator
    ports:
      - "5000:5000"             # Frigate web UI + HA integration API
      - "8554:8554"             # go2rtc RTSP
      - "8555:8555/tcp"         # go2rtc WebRTC
      - "8555:8555/udp"         # go2rtc WebRTC/UDP
    volumes:
      - ./config.yml:/config/config.yml:ro
      - /mnt/ssd-nvme/frigate:/media/frigate   # recordings volume
      - /etc/localtime:/etc/localtime:ro       # TZ
    environment:
      - FRIGATE_RTSP_PASSWORD=change-me
    depends_on:
      - mosquitto

  go2rtc:
    container_name: frigate-go2rtc
    restart: unless-stopped
    image: ghcr.io/alexxit/go2rtc:latest
    ports:
      - "8554:8554"
      - "8555:8555/tcp"
      - "8555:8555/udp"
    volumes:
      - ./go2rtc.yml:/config/go2rtc.yml:ro

  mosquitto:
    container_name: frigate-mosquitto
    restart: unless-stopped
    image: eclipse-mosquitto:2.0
    ports:
      - "1883:1883"
    volumes:
      - ./mosquitto/config:/mosquitto/config
      - ./mosquitto/data:/mosquitto/data
      - ./mosquitto/log:/mosquitto/log
```

Notes:

- Replace `/mnt/ssd-nvme/frigate` with the mount point of your SSD.
- The `devices:` line is for the Coral USB accelerator — remove it if
  you're CPU-only.
- If you already run Mosquitto (the `connections/mqtt/` slice), drop
  the `mosquitto` service here and point Frigate at the existing
  broker's host/port.

### B.2 — External `config.yml`

Same shape as Path A.4 — drop it at `/opt/frigate/config.yml`. Set
`mqtt.host` to your Mosquitto broker's reachable address (the
Mosquitto container's hostname if it's on the same Docker network, or
the LAN IP if it's not).

### B.3 — Point HA at the external Frigate

Same as Path A.6, but use `http://<lan-ip-of-frigate-host>:5000` as
the Frigate URL. The integration will auto-detect MQTT credentials if
you've enabled the standard `homeassistant` discovery prefix; otherwise
paste them.

## HA MQTT discovery mapping

Frigate publishes object-detection events on MQTT under
`<topic_prefix>/events` and an availability heartbeat on
`<topic_prefix>/available`. The HA core `frigate` integration
subscribes to those topics and auto-creates:

- `camera.<camera_name>` — the live stream (via go2rtc).
- `binary_sensor.<camera_name>_person`, `<camera_name>_car`, etc. —
  one per object class per camera.
- `sensor.<camera_name>_fps`, `<camera_name>_detection_fps` —
  performance sensors.
- `binary_sensor.<camera_name>_motion` — motion detected (any object).

The RoamCore contract layer subscribes to those auto-created entities
and derives the vendor-neutral `rc_security_*` tiles that the dashboard
and OpenClaw bind to. The mapping:

| Frigate / HA auto-created entity            | RoamCore contract entity                            |
|---------------------------------------------|----------------------------------------------------|
| `sensor.frigate_camera_count`               | `sensor.rc_security_camera_count`                   |
| OR aggregate of `binary_sensor.<cam>_person` (any ON) | `binary_sensor.rc_security_camera_motion_active` |
| `binary_sensor.frigate_recording`           | `binary_sensor.rc_security_recording_active`        |
| latest timestamp across `<cam>_*_last_motion` | `sensor.rc_security_last_motion_at`               |
| aggregate label from `<cam>_*_person` etc.  | `sensor.rc_security_object_detection_summary`       |
| Frigate `stats: storage` gauge              | `sensor.rc_storage_frigate_usage`                   |

The aggregate sensors (motion / count / last-motion / summary) are
template sensors that iterate over the per-camera entities. Drop this
into `homeassistant/packages/roamcore_security_cameras.yaml`:

```yaml
# Aggregate template sensors for the Frigate RoamCore contract layer.
# Mounted from the connections/frigate/docs/recipe.md "Dashboard tile
# wiring" section.

template:
  - sensor:
      - name: "Security camera count"
        unique_id: rc_security_camera_count
        unit_of_measurement: "online"
        state: >
          {{ states.binary_sensor
              | selectattr('entity_id', 'search', 'person|motion|car')
              | selectattr('state', 'eq', 'on')
              | list | length }}

  - binary_sensor:
      - name: "Security camera motion active"
        unique_id: rc_security_camera_motion_active
        device_class: motion
        state: >
          {{ is_state('binary_sensor.front_door_motion', 'on')
             or is_state('binary_sensor.back_door_motion', 'on')
             or is_state('binary_sensor.driveway_motion', 'on') }}

  - sensor:
      - name: "Security last motion at"
        unique_id: rc_security_last_motion_at
        device_class: timestamp
        state: >
          {% set cams = ['front_door', 'back_door', 'driveway'] %}
          {% set ts = cams | map('regex_replace', '$', '_last_motion')
                          | map('as_timestamp') | list %}
          {{ max(ts) | timestamp_local }}

  - sensor:
      - name: "Security object detection summary (1h)"
        unique_id: rc_security_object_detection_summary
        state: >
          {% set counts = namespace(p=0, c=0, a=0) %}
          {% for cam in ['front_door', 'back_door', 'driveway'] %}
            {% set counts.p = counts.p +
                state_attr('binary_sensor.' ~ cam ~ '_person', 'detections_1h') | int(0) %}
            {% set counts.c = counts.c +
                state_attr('binary_sensor.' ~ cam ~ '_car', 'detections_1h') | int(0) %}
            {% set counts.a = counts.a +
                state_attr('binary_sensor.' ~ cam ~ '_animal', 'detections_1h') | int(0) %}
          {% endfor %}
          person: {{ counts.p }}, car: {{ counts.c }}, animal: {{ counts.a }}

  - sensor:
      - name: "Storage Frigate usage"
        unique_id: rc_storage_frigate_usage
        unit_of_measurement: "%"
        state: >
          {{ state_attr('sensor.frigate_storage', 'used_percent') | float(0) | round(1) }}
        device_class: battery                       # so the % unit renders as a battery-style gauge
```

The `detections_1h` attribute is exposed by the Frigate HA integration
on each per-class `binary_sensor` and counts how many detections of
that class happened on that camera in the last hour.

## Storage + retention

Frigate's storage footprint is dominated by:

- **Continuous recording** (if `record.enabled: true` with
  `retain.mode: motion`) — records 24/7 but only keeps segments that
  contain motion (i.e. detected pixel-delta, not objects). At 1080p /
  5 fps, expect ~30 GB / camera / day before retention.
- **Event clips** (`record.events`) — short clips around each detected
  object. Typically ~5–10 % of the continuous volume.
- **Alert clips** (`record.alerts`) — short clips around each object
  that crossed the configured alert threshold (e.g. person in a zone).
  Smaller again.
- **Snapshots** (`snapshots.enabled: true`) — one JPEG per object
  detection. Negligible.

Recommended sizing for a 4-camera / 1080p / 14-day retention system:

- **1 TB SSD/NVMe minimum** if you accept shorter retention.
- **2 TB** comfortable for 14 days.
- **4 TB** if you want to bump `record.alerts.retain` to 60 days.

Sizing rule of thumb: `~30 GB / camera / day` × `camera_count` ×
`retain_days` × `1.2` (snapshots + alerts overhead). Round up to the
nearest SSD size.

If you hit storage pressure:

1. Lower `detect.fps` from 5 to 2 — halves the frame rate and roughly
   halves the continuous-recording volume (motion segments are still
   recorded; the pre/post buffer is shorter).
2. Drop `record.retain.days` from 14 to 7.
3. Add a `record.events.retain.objects` filter so you only keep events
   for the object classes you actually care about (person + car,
   skipping animal for example).
4. Set up an external cleanup job (`find /media/frigate/clips -mtime
   +14 -delete`) as a belt-and-braces last line of defence.

## Troubleshooting

- **CPU saturation.** Detection is the heaviest load Frigate puts on
  the host. If `top` shows the Frigate container pegging 100 % CPU,
  drop `detect.fps` to 2–3, disable any non-essential `objects.track`
  classes, and add a Coral USB accelerator (~$60) for ~10 ms/inference
  on 4+ cameras.
- **go2rtc stream failures.** go2rtc needs to reach the camera's RTSP
  URL from inside the container. Errors like `go2rtc: rtsp: failed to
  connect` usually mean: (a) the URL is wrong, (b) the camera's RTSP
  auth requires URL-encoded credentials (special characters in the
  password — encode with `urllib.parse.quote`), (c) the camera and
  the Frigate host are on different VLANs / firewall. Check the go2rtc
  log tab and `ping <camera-lan-ip>` from the Frigate host.
- **MQTT discovery mismatch.** If HA doesn't auto-create the camera
  entities, the most common cause is `mqtt.topic_prefix` in Frigate's
  `config.yaml` not matching what the HA core `frigate` integration
  expects. Default is `frigate`; the integration reads
  `<topic_prefix>/available` and `<topic_prefix>/events`. If you've
  changed one, change both.
- **RTSP auth errors.** Special characters in the camera's RTSP
  password (`!`, `@`, `#`, `$`, `%`, `&`, `+`, `=`, `?`, `/`, `:`)
  need to be URL-encoded in the RTSP URL. Use `python3 -c "import
  urllib.parse, sys; print(urllib.parse.quote(sys.argv[1]))" 'p@ss!word'`
  to encode. Also, the username often lives in the camera's RTSP path
  rather than the URL userinfo — check the camera's web UI.
- **Storage filling up.** Three knobs in order: (1) `record.retain.days`
  — lower it. (2) `record.events.retain.objects` — only keep clips
  for the classes you care about. (3) Drop `record.alerts.retain`
  from 30 to 14 days. If all three are tight, add a one-line
  external cleanup cron (`find /media/frigate/clips -mtime +14
  -delete`).
- **Cameras not detected / streams dropped.** Check multicast / IGMP
  snooping on your PoE switch — if it's enabled, the RTSP multicast
  traffic from the cameras may be silently dropped, causing Frigate to
  fail to subscribe to the stream. Disable IGMP snooping on the CCTV
  VLAN, or pin the cameras to a non-snooped VLAN.
- **`binary_sensor.<cam>_motion` stays ON.** Motion sensors latch ON
  until a "no motion for X seconds" timer fires. Frigate's default is
  30 s. If you want a faster reset, add
  `motion: { threshold: 15 }` under each camera in `config.yaml`.
- **Web UI loads but live stream doesn't.** go2rtc isn't running, or
  the camera isn't in the `go2rtc.streams` section. Add the camera's
  RTSP URL under `go2rtc.streams.<camera_name>` in `config.yaml` and
  restart the add-on.

## Promoting to tier-a (future)

When a canonical reference Frigate container lands in CI (likely via
`testcontainers/frigate` with a synthetic RTSP source or a recorded
fixture):

1. Add `config_flow.py` that:
   - Discovers Frigate containers on the LAN via mDNS `_frigate._tcp`
     (or a manual host entry).
   - Tests the connection + authentication against the container's
     HTTP API.
   - Sets up the RoamCore-specific security contract
     (`rc_security_*` + `rc_storage_frigate_*`) on behalf of the user.
   - Wires the MQTT discovery prefix.
2. Add an integration test that:
   - Spins up `testcontainers/frigate` with a synthetic camera input.
   - Publishes a synthetic `frigate/events` payload.
   - Asserts the `rc_security_camera_motion_active`,
     `rc_security_recording_active`, `rc_security_last_motion_at`,
     and `rc_storage_frigate_usage` contract entities appear in HA
     with the right `unique_id` + `device_class`.
   - Asserts the `rc_security_object_detection_summary` rolls up the
     per-class `detections_1h` correctly.
3. Flip the manifest to `tier: a`, add `working_config_flow` +
   `integration_test_passes` + `no_manual_yaml_required` to
   `tier_requirements`, and remove `tier_warnings`.
4. Re-run `python3 scripts/audit_connections.py` — should go clean
   with zero warnings for `frigate`.

The recipe on this page stays useful as a fallback for users who prefer
manual setup over the one-tap path, and as a reference for the
external-Docker / Coral-accelerator configurations that won't fit in
the one-tap wizard.