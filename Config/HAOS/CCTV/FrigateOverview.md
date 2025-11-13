
# VanCore CCTV System Setup — Single-Page Spec

**Status:** Implementation-ready  
**Owner:** VanCore Hardware/Software  
**Last updated:** 2025-11-13

This document defines how the VanCore system records and serves CCTV video from **four cameras** with **low CPU load**, **predictable storage**, and **user-configurable retention & quality**. It is designed to be dropped into your GitHub repo as-is.

---

## TL;DR

- Use **IP cameras (RTSP/ONVIF)** or an **analog→IP encoder (XVR/ADC)** that outputs **H.264/H.265**.  
- Record **native camera streams** with **no server-side transcoding** ("copy-to-disk").  
- Implement **tiered retention** by recording multiple camera streams (e.g., Main 1080p / Sub1 720p / Sub2 480p) with **different keep-times**.  
- Expose **Home Assistant (HA)** controls to let users choose **days / bitrate / resolution / fps** and show a **live storage estimate**.  
- Live view is **decoded only when opened** in the dashboard (lazy-load).  
- Users can **swap SSDs** for more capacity and optionally **archive to cloud** via `rclone`.

---

## Requirements

- **Cameras:** 4× PoE IP cameras preferred. If using analog cameras, the encoder/XVR **must** output RTSP in **H.264/H.265** so the server does not encode.  
- **Network:** Cameras connect to a **PoE switch** uplinked to any **LAN** port of the main system.  
- **Recorder:** **Frigate** + **go2rtc** (Docker/LXC) on the main system; set to **no transcode** (copy-to-disk).  
- **Live View:** HA Lovelace (Frigate card + go2rtc); **lazy-load** views.  
- **Storage:** Mounted at **`/mnt/video`** on the NVMe SSD. Optional **cloud archive** via `rclone`.

---

## Storage Sizing

**Rule:** **1 Mb/s ≈ 10.8 GB/day per camera** (decimal GB). For **4 cameras**:

| Per-cam bitrate | Weekly total (4 cams) |
| --- | --- |
| 0.8 Mb/s | ~242 GB |
| 0.9 Mb/s | ~272 GB |
| **1.0 Mb/s** | **~302 GB** |
| 1.2 Mb/s | ~363 GB |

Prefer **H.265** where available (often 10–30% less bitrate vs H.264 for similar quality).

---

## Tiered Retention (Example to Target ≲300 GB/week)

Record multiple *native* streams per camera with different retention windows (no downconvert jobs). For each camera:

- **Tier 1 (recent 2 days):** **1080p30 @ 2.0 Mb/s** → ~43.2 GB  
- **Tier 2 (next 2 days):** **720p30 @ 0.9 Mb/s** → ~19.4 GB  
- **Tier 3 (final 3 days):** **480p @ 0.35–0.4 Mb/s** → ~11–13 GB  

**Per camera ≈ 75.6 GB/week → 4 cams ≈ 302.4 GB/week.**  
To add buffer under 300 GB, drop 720p to **0.85 Mb/s** or 480p to **0.35 Mb/s**.

---

## Home Assistant Controls (Users choose retention/bitrate; live storage estimate)

Add **helpers** and a **storage estimate sensor**:

```yaml
# configuration.yaml (or add via UI Helpers)
input_number:
  cctv_days_tier1: { name: "Tier 1 Days (1080p)", min: 0, max: 7, step: 1, mode: box }
  cctv_days_tier2: { name: "Tier 2 Days (720p)",  min: 0, max: 7, step: 1, mode: box }
  cctv_days_tier3: { name: "Tier 3 Days (480p)",  min: 0, max: 7, step: 1, mode: box }
  cctv_bitrate_tier1: { name: "Tier 1 Mb/s", min: 0.2, max: 8, step: 0.1, mode: slider }
  cctv_bitrate_tier2: { name: "Tier 2 Mb/s", min: 0.2, max: 8, step: 0.1, mode: slider }
  cctv_bitrate_tier3: { name: "Tier 3 Mb/s", min: 0.2, max: 8, step: 0.1, mode: slider }

input_boolean:
  cctv_cloud_archive: { name: "Archive to Cloud (rclone)", icon: mdi:cloud-upload }

template:
  - sensor:
      - name: CCTV Weekly Storage Estimate
        unit_of_measurement: "GB"
        state: >
          {% set cams = 4 %}
          {% set d1 = states('input_number.cctv_days_tier1')|float(0) %}
          {% set d2 = states('input_number.cctv_days_tier2')|float(0) %}
          {% set d3 = states('input_number.cctv_days_tier3')|float(0) %}
          {% set b1 = states('input_number.cctv_bitrate_tier1')|float(0) %}
          {% set b2 = states('input_number.cctv_bitrate_tier2')|float(0) %}
          {% set b3 = states('input_number.cctv_bitrate_tier3')|float(0) %}
          {% set per_day_gb = (b1*d1 + b2*d2 + b3*d3) * 10.8 %}
          {{ (cams * per_day_gb * (7.0 / (d1+d2+d3 if (d1+d2+d3)>0 else 1)) * 1.1)|round(0) }}
        attributes:
          note: "1 Mb/s ≈ 10.8 GB/day/camera; +10% overhead applied"
```

**Default values** (ships ≲300 GB/week total for 4 cams):  
- Tier 1: **2 days @ 2.0 Mb/s**, Tier 2: **2 days @ 0.9 Mb/s**, Tier 3: **3 days @ 0.35–0.4 Mb/s**.

---

## Recorder Configuration (Frigate + go2rtc; no transcoding)

Define **three “virtual cameras” per physical camera**, each bound to a different input stream and **retention**. Your HA automation renders a templated `frigate.yml` from user controls and triggers a quick restart.

```yaml
# frigate.yml (conceptual — repeat the triad per physical camera)
record:
  enabled: true

cameras:
  drive_cam_1080:
    ffmpeg:
      inputs:
        - path: rtsp://cam1/stream_main      # 1080p (H.264/H.265) from camera
          roles: [record]
    record:
      enabled: {{ (states('input_number.cctv_days_tier1')|int) > 0 }}
      retain:
        days: {{ states('input_number.cctv_days_tier1')|int }}

  drive_cam_720:
    ffmpeg:
      inputs:
        - path: rtsp://cam1/stream_sub1      # 720p
          roles: [record]
    record:
      enabled: {{ (states('input_number.cctv_days_tier2')|int) > 0 }}
      retain:
        days: {{ states('input_number.cctv_days_tier2')|int }}

  drive_cam_480:
    ffmpeg:
      inputs:
        - path: rtsp://cam1/stream_sub2      # 480p
          roles: [record]
    record:
      enabled: {{ (states('input_number.cctv_days_tier3')|int) > 0 }}
      retain:
        days: {{ states('input_number.cctv_days_tier3')|int }}
```

**Restart hook** (expose as HA `shell_command` or automation):  
```bash
# If Frigate runs in Docker:
docker restart frigate

# If managed via systemd:
systemctl restart frigate
```

**Live view:** Use **go2rtc** + Frigate card in HA; views load only when the user opens the CCTV page.

---

## Disk Path, SSD Swaps & Endurance

- Mount the video volume at **`/mnt/video`**; set Frigate `record -> path: /mnt/video`.  
- Provide a one-click **Prepare Disk** script so users can install larger SSDs safely:

```bash
# DANGER: Adjust device path before running; this wipes the target device.
umount /mnt/video || true
wipefs -a /dev/nvme1n1
parted -s /dev/nvme1n1 mklabel gpt mkpart video ext4 0% 100%
mkfs.ext4 -F -L VIDEO /dev/nvme1n1p1
mkdir -p /mnt/video
echo 'LABEL=VIDEO /mnt/video ext4 noatime,nodiratime,defaults 0 2' >> /etc/fstab
mount -a
chown -R frigate:frigate /mnt/video
```

- **Write endurance:** ~300 GB/week ≈ **43 GB/day** ≈ **~16 TB/year**; choose NVMe with **≥600 TBW**. Ensure **NVMe cooling**.

---

## Optional Cloud Archive (rclone)

```bash
# Example nightly job: move files older than 7 days to Backblaze B2
rclone move /mnt/video b2:vancore-archive   --min-age 7d --transfers 4 --checkers 8   --fast-list --delete-empty-src-dirs --bwlimit 4M
```

- Support B2/S3/Wasabi/Drive; offer **encrypted** remotes via `rclone crypt`.  
- Warn users about uplink bandwidth and egress costs. Toggle in HA via `input_boolean.cctv_cloud_archive`.

---

## Security & Networking Notes

- Place cameras on an **IoT/CCTV VLAN** (optional); restrict outbound traffic to required services (NTP/DNS/RTSP).  
- **Strong camera passwords**; disable P2P/UPnP on cameras.  
- Avoid Internet exposure; use **WireGuard** or **Nabu Casa** for remote access.

---

## Defaults (VanCore V1)

- **Streams:** 1080p30 (Main), 720p30 (Sub1), 480p (Sub2), **H.265** preferred.  
- **Tiering:** 2 days 1080p @ 2.0 Mb/s; 2 days 720p @ 0.9 Mb/s; 3 days 480p @ 0.35–0.4 Mb/s.  
- **Weekly target:** ≲ **300 GB** total for 4 cams.  
- **Recording path:** `/mnt/video`.  
- **Cloud archive:** **Off** by default (user toggle).  
- **Analytics/transcoding:** **Off** by default (optional Coral/CPU upgrade later).

---

## Acceptance Checklist

- 4× cameras discovered; RTSP Main/Sub1/Sub2 verified.  
- Continuous recording active; **no transcode**.  
- HA dashboard shows live estimate; weekly usage aligns ±10%.  
- Live view loads on demand; idle CPU remains low.  
- SSD prep & mount verified; endurance within spec.  
- Optional rclone archive runs successfully (if enabled).

---

## Versioning

- **v1.0** — Initial CCTV setup spec (four cams; tiered retention; HA controls; copy-to-disk).

