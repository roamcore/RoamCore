# NAS (Synology / QNAP / generic SMB) — tier-b recipe connection

**Tier:** B (recipe)
**Audience:** A RoamCore user who wants reliable local storage on
the van's LAN for media, CCTV archival, backups, and logs. Pick
ONE path (Path A = Synology DSM, Path B = QNAP, Path C = generic
SMB/NFS), stand up the NAS with a static IP on the LAN, expose
its shares, wire the upstream HA integration (config_flow for
Synology/QNAP, `homeassistant` network-storage block + backup
integration for SMB), and import the `rc_homelab_nas_*` contract
helpers from the recipe §6 snippet block.

This howto is mirrored into `docs/connections/nas.md` by the
catalog cron (`scripts/build_catalog.py`) so it shows up under
the public docs site's "Connections" section. Keep this recipe as
the source of truth.

## What is a NAS in RoamCore?

A NAS (Network Attached Storage) is a dedicated file-storage
appliance on the LAN. It exposes one or more volumes as SMB
shares (and optionally NFS), runs a management web UI, and
usually has its own storage health monitoring (S.M.A.R.T.,
RAID status, volume health).

In a van that's frequently off-grid, a NAS is the single biggest
"don't worry about cloud storage bills or LTE bandwidth"
win you can ship:

- **Local backups (even offline).** RoamCore's HA backups,
  Frigate's CCTV clip archive, and Trip Wrapped's HTML exports
  all have a place to land without depending on cloud storage.
  On a metered LTE plan this is the difference between "I keep
  backups for 90 days" and "I keep backups for a year without
  thinking about it".
- **Central media library.** Movies, music, reference docs,
  maps, offline OpenStreetMap tiles, vehicle manuals — all on
  one share reachable from any LAN device. A 2 TB USB drive on
  a Raspberry Pi masquerading as a NAS counts; you don't need a
  $500 DiskStation to get 80% of the value.
- **CCTV archival.** Frigate's event clips + continuous
  recordings can be offloaded from the RoamCore box's SD/NVMe
  (which is small + flash-wearing) to the NAS's larger-volume
  pool.
- **Logs + crash dumps.** Long-running log files that would
  fill the RoamCore box's local storage can land on the NAS.

**Why it's useful in a van** (the legacy spec's bullets, expanded):

- **Local backups even offline.** Pull into a campground with
  no LTE? Doesn't matter — the backup still lands on the NAS
  over LAN, which doesn't need internet.
- **Store CCTV recordings and Trip Wrapped exports.** Frigate
  generates event clips + continuous recordings; Trip Wrapped
  generates an HTML export at the end of each trip. Both want
  a stable home that's not the RoamCore box's SD card.
- **Central place for media libraries.** Movies for the kids,
  music for the road, vehicle manuals for the rare "how do I
  bleed the brakes" emergency — one share, every device.

RoamCore does **not** ship a NAS of its own. There is no
RoamCore-owned NAS image, no `config_flow.py` wrapping the
upstream Synology DSM / QNAP / SMB integrations, and no NAS on
the CI bench to integration-test against. So we publish a recipe
that walks you through deploying whichever NAS (your choice) on
your own LAN hardware, then layer a small contract on top:
`rc_homelab_nas_*` dashboard tiles + OpenClaw queries ("how much
storage is used on the NAS?", "is the NAS reachable?", "is the
latest backup running?", "when was the last backup?", "is the
NAS drive healthy?", "is the NAS CPU high?", "is the NAS memory
high?") that bind to those contract entities.

**Why tier-b:** RoamCore has no NAS on the bench to
integration-test against, no RoamCore-owned config_flow to ship
(the upstream Synology DSM / QNAP integrations have their own
config_flows in HA core, but those are UPSTREAM truth, not
RoamCore's). The recipe is sound (it leans on the upstream
config_flow + the operator's own NAS deployment), but we cannot
claim one-tap automation. The promotion outline at the bottom of
this recipe describes exactly what needs to happen to flip this
to tier-a.

**Three install paths:**

- **Path A — Synology DSM** (richest integration surface, ~30
  sensors including storage, S.M.A.R.T., CPU, memory, active
  users, volume health, UPS status). Best when you're already
  running DiskStation Manager and want the deepest contract
  coverage.
- **Path B — QNAP** (alternative NAS vendor, similarly rich
  integration surface). Best when you have QNAP hardware.
- **Path C — Generic SMB/NFS** (any NAS that exposes shares —
  TrueNAS, Unraid, a Raspberry Pi with an external drive, an old
  mini-PC with a big disk, etc.). Best when you already have
  generic SMB/NFS storage and don't need Synology/QNAP-specific
  telemetry.

## Prerequisites

Before starting the recipe, make sure you have:

- **A NAS to point the connection at.** Either:
  - A Synology DiskStation (any model from the last ~10 years
    supports the DSM integration; DSM 6.2+ recommended for the
    current config_flow). `https://www.synology.com/`
  - A QNAP NAS (any model from the last ~10 years supports the
    QNAP integration; QTS / QuTS hero). `https://www.qnap.com/`
  - Any NAS / mini-PC / Raspberry Pi + USB drive that can
    expose an SMB share (or NFS export). TrueNAS, Unraid,
    OpenMediaVault, or a hand-rolled Samba install all count.
- **A static IP for the NAS.** Either via DHCP reservation on
  your OpenWrt router (recommended) or a manually-configured
  static IP on the NAS itself. Example: `192.168.1.20` (or
  whatever fits your addressing scheme).
- **A low-privilege account on the NAS.** Path A + Path B
  integrations want a dedicated read-only (or scoped) account
  with API access enabled — don't reuse your admin account.
  Path C needs an SMB user that owns the share you'll back up
  to.
- **The NAS reachable from the RoamCore box on the LAN.** Verify
  with `ping 192.168.1.20` from the RoamCore box (or any LAN
  device) before starting the integration setup.
- **(Path A) Synology DSM ≥ 6.2** running on the DiskStation,
  with **API access enabled** in **Control Panel → External
  Access → Advanced**.
- **(Path B) QNAP QTS / QuTS hero** with **myQNAPcloud
  link disabled** if you don't want cloud round-trips, and the
  **QNAP service** enabled on the management port.
- **(Path C) An SMB share** mounted and writable from a LAN
  client. Verify with `mount -t cifs //192.168.1.20/share
  /mnt -o username=ha-backup,password=...` from any LAN box.

## Path A — Synology DSM (recommended for the richest integration surface)

The richest path. ~30 sensors, including storage %, S.M.A.R.T.
health, CPU %, memory %, active users, volume health, UPS status,
and external devices.

### A.1 — Verify DSM + enable the API

1. Log into DSM on the DiskStation (`http://192.168.1.20:5000/`).
2. **Control Panel → External Access → Advanced → Confirm DSM
   version** (≥ 6.2 recommended).
3. **Control Panel → External Access → Advanced → API**:
   ensure the API is enabled (it is by default on modern DSM).
4. **Control Panel → User & Group → Create** a dedicated
   `ha-roamcore` account (or any name you prefer). Membership:
   `users`. Permissions: read-only on the volumes you want HA to
   monitor, plus API access.
5. Note the account name + password for the config_flow in A.4.

### A.2 — Assign a static IP

- **DHCP reservation (recommended):** In OpenWrt → **Network →
  DHCP and DNS → Static Leases**, add the NAS's MAC address with
  IP `192.168.1.20` (or whatever you choose). The NAS will get
  `192.168.1.20` reliably on every boot.
- **Manual static IP:** On the NAS itself, set `192.168.1.20/24`,
  gateway `192.168.1.1` (your OpenWrt), DNS `192.168.1.1`
  (OpenWrt) + `1.1.1.1` (Cloudflare, fallback).

### A.3 — Verify the API is reachable

From the RoamCore box (or any LAN client), verify the DSM API:

```bash
curl -k https://192.168.1.20:5001/webapi/entry.cgi?api=SYNO.API.Info&version=1&method=query
```

You should get back JSON listing the available API versions. If
you get a connection error, the API isn't enabled or the
firewall's blocking port 5001.

### A.4 — Add the HA integration

In Home Assistant → **Settings → Devices & Services → Add
Integration → Synology DSM**
(`https://www.home-assistant.io/integrations/synology_dsm/`):

- **Host:** `192.168.1.20`
- **Port:** `5001` (HTTPS) or `5000` (HTTP)
- **Username:** `ha-roamcore` (the low-privilege account from
  A.1)
- **Password:** the password you set

After the config_flow completes you'll have entities like:

- `sensor.synology_dsm_storage_<volume>_used` (and `_total`,
  `_percent_used`, `_free`)
- `binary_sensor.synology_dsm_<volume>_status` (volume health)
- `binary_sensor.synology_dsm_smart_status` (S.M.A.R.T. health)
- `sensor.synology_dsm_cpu_load` (CPU %)
- `sensor.synology_dsm_memory` (memory %)
- `sensor.synology_dsm_active_users`
- `binary_sensor.synology_dsm_update_available`
- `sensor.synology_dsm_uptime`
- `binary_sensor.synology_dsm_<ups>_status` (if you have a UPS)

These are UPSTREAM entity ids. The recipe §6 contract templates
wrap them into vendor-neutral `rc_homelab_nas_*` ids.

## Path B — QNAP (alternative NAS vendor)

Alternative NAS vendor with a similarly rich integration surface.

### B.1 — Verify QTS / QuTS hero + enable the API

1. Log into QTS on the QNAP (`http://192.168.1.20:8080/`).
2. **Control Panel → Network Services → QTS Service** (or
   **myQNAPcloud Service** depending on firmware): ensure the
   QNAP service is enabled.
3. **Privilege Settings → Users → Create** a dedicated
   `ha-roamcore` account with administration rights (the QNAP
   integration needs admin-level API access — there's no
   read-only role).
4. Note the account name + password for the config_flow in B.4.

### B.2 — Assign a static IP

Same as A.2: DHCP reservation in OpenWrt or manual static IP on
the NAS itself. Use the same `192.168.1.20` if you want
consistency with Path A.

### B.3 — Verify the API is reachable

From the RoamCore box (or any LAN client), verify the QNAP API:

```bash
curl -k http://192.168.1.20:8080/cgi-bin/login_sid.cgi
```

You should get back XML containing a `<authSid>` element (or a
similar session-id response). If you get a connection error, the
QNAP service isn't enabled or the firewall's blocking port 8080.

### B.4 — Add the HA integration

In Home Assistant → **Settings → Devices & Services → Add
Integration → QNAP**
(`https://www.home-assistant.io/integrations/qnap/`):

- **Host:** `192.168.1.20`
- **Port:** `8080` (HTTP) or `443` (HTTPS)
- **Username:** `ha-roamcore` (the account from B.1)
- **Password:** the password you set

After the config_flow completes you'll have entities like:

- `sensor.qnap_<volume>_space_used` (and `_free`, `_total`,
  `_percent_used`)
- `sensor.qnap_system_cpu` (CPU %)
- `sensor.qnap_system_memory` (memory %)
- `sensor.qnap_system_uptime`
- `sensor.qnap_system_temperature`
- `binary_sensor.qnap_<volume>_status` (volume health)
- `binary_sensor.qnap_smart_status` (S.M.A.R.T. health)

These are UPSTREAM entity ids. The recipe §6 contract templates
wrap them into vendor-neutral `rc_homelab_nas_*` ids.

## Path C — Generic SMB/NFS (any NAS that exposes shares)

For operators running TrueNAS, Unraid, OpenMediaVault, a
Raspberry Pi with an external drive, or any box that exposes an
SMB (or NFS) share.

### C.1 — Create an SMB share

On the NAS, create a share (e.g. `roamcore-backups`):

- **TrueNAS:** **Sharing → SMB → Add** → name the share, set
  the path, enable, save.
- **Unraid:** **Shares → Add Share** → name, set the path,
  enable SMB export, save.
- **OpenMediaVault:** **Services → SMB/CIFS → Shares → Add** →
  name, set the path, enable, save.
- **Raspberry Pi + Samba:** edit `/etc/samba/smb.conf`:
  ```
  [roamcore-backups]
  path = /mnt/usb/backups
  browseable = yes
  read only = no
  guest ok = no
  valid users = ha-backup
  ```
  Then `sudo smbpasswd -a ha-backup` and `sudo systemctl
  restart smbd`.

### C.2 — Assign a static IP

Same as A.2 / B.2: DHCP reservation in OpenWrt or manual static
IP on the NAS itself.

### C.3 — Verify the share is reachable

From the RoamCore box (or any LAN client), verify the SMB share:

```bash
# Using smbclient (install if missing: apt install smbclient)
smbclient //192.168.1.20/roamcore-backups -U ha-backup
# Or mount to test full read/write:
sudo mount -t cifs //192.168.1.20/roamcore-backups /mnt/test \
  -o username=ha-backup,password=YOUR_PASSWORD_HERE,vers=3.0
ls /mnt/test/
sudo umount /mnt/test
```

### C.4 — Add the SMB share to Home Assistant

Edit `configuration.yaml`:

```yaml
homeassistant:
  # Generic SMB/NFS share wired into HA for backup target use.
  # See https://www.home-assistant.io/common-tasks/os/#network-storage
  # RoamCore does NOT ship a config_flow for this — Path C uses
  # configuration.yaml as the UPSTREAM pattern (the HA SMB
  # share is added via the `homeassistant` network-storage block,
  # not via a config_flow integration).
  custom_mounts:
    share_for_backups:
      host: 192.168.1.20
      share: roamcore-backups
      username: ha-backup
      password: !secret smb_backup_password
      mount_type: cifs
      # Read-only is false; the operator may want backups to
      # land on this share.
      read_only: false
```

Then in `secrets.yaml`:

```yaml
smb_backup_password: YOUR_PASSWORD_HERE
```

Reload HA (Developer Tools → YAML → Reload all YAML
configuration, or restart HA if the share isn't picked up via
reload). The share should now appear at `/mnt/` inside the HA
container (or wherever HA mounts network-storage).

### C.5 — Point HA's backup integration at the share

In Home Assistant → **Settings → System → Backups → Configure
automatic backups → Network storage location**, select the
`share_for_backups` share you just added (Path C) — or the
Synology/QNAP share if Path A/B. Backups will now land on the
NAS instead of the RoamCore box's local SD/NVMe.

After this you'll have:

- A mounted SMB share at `/mnt/` inside HA
- HA's `backup` integration reporting backup state (last backup
  timestamp, backup running, backup successful)
- (RoamCore contract layer from recipe §6.3 wraps these into
  `rc_homelab_nas_*` ids)

## RoamCore contract entities

The full listing the wizard + dashboard + OpenClaw rely on:

| Entity | Type | States | Source |
|---|---|---|---|
| `sensor.rc_homelab_nas_storage_used_pct` | sensor | 0–100 (%) | template over upstream `*_percent_used` |
| `sensor.rc_homelab_nas_storage_total_gb` | sensor | count (GB) | template over upstream `*_total` |
| `sensor.rc_homelab_nas_storage_free_gb` | sensor | count (GB) | template over upstream `*_free` |
| `binary_sensor.rc_homelab_nas_reachable` | binary_sensor | ON / OFF | template over upstream reachability |
| `binary_sensor.rc_homelab_nas_smart_status_ok` | binary_sensor | ON / OFF | template over upstream `*_smart_status` |
| `sensor.rc_homelab_nas_last_backup_at` | sensor | timestamp | template over HA backup integration |
| `binary_sensor.rc_homelab_nas_backup_running` | binary_sensor | ON / OFF | template over HA backup integration |
| `sensor.rc_homelab_nas_cpu_pct` | sensor | 0–100 (%) | template over upstream `*_cpu_load` / `*_cpu` |
| `sensor.rc_homelab_nas_memory_pct` | sensor | 0–100 (%) | template over upstream `*_memory` |

All grayed-out / `unknown` fallback when the upstream integration
is in error state (or no NAS is configured).

### §6.1 — Copy-pasteable helper YAML (Path A — Synology DSM)

Drop into `homeassistant/packages/roamcore_nas.yaml`:

```yaml
# RoamCore NAS contract helpers (recipe §6.1, Synology DSM / Path A).
# All entities are vendor-neutral per docs/reference/rc-entity-naming.md.
# Wraps upstream `sensor.synology_dsm_*` entities from the Synology DSM
# integration (ha_integration_domain: synology_dsm) into
# rc_homelab_nas_* ids.

template:
  - sensor:
      - name: NAS storage used pct (contract)
        unique_id: rc_homelab_nas_storage_used_pct
        unit_of_measurement: "%"
        state: >
          {{ max(states('sensor.synology_dsm_storage_volume_1_used_pct') | float(0),
                 states('sensor.synology_dsm_storage_volume_2_used_pct') | float(0)) }}
        icon: mdi:database
      - name: NAS storage total (contract)
        unique_id: rc_homelab_nas_storage_total_gb
        unit_of_measurement: "GB"
        state: >
          {{ (states('sensor.synology_dsm_storage_volume_1_total') | float(0)
            + states('sensor.synology_dsm_storage_volume_2_total') | float(0)) | round(1) }}
        icon: mdi:database
      - name: NAS storage free (contract)
        unique_id: rc_homelab_nas_storage_free_gb
        unit_of_measurement: "GB"
        state: >
          {{ (states('sensor.synology_dsm_storage_volume_1_free') | float(0)
            + states('sensor.synology_dsm_storage_volume_2_free') | float(0)) | round(1) }}
        icon: mdi:database
      - name: NAS CPU pct (contract)
        unique_id: rc_homelab_nas_cpu_pct
        unit_of_measurement: "%"
        state: "{{ states('sensor.synology_dsm_cpu_load') | float(0) }}"
        icon: mdi:chip
      - name: NAS memory pct (contract)
        unique_id: rc_homelab_nas_memory_pct
        unit_of_measurement: "%"
        state: "{{ states('sensor.synology_dsm_memory') | float(0) }}"
        icon: mdi:memory
  - binary_sensor:
      - name: NAS reachable (contract)
        unique_id: rc_homelab_nas_reachable
        device_class: connectivity
        state: >
          {% set v1 = states('binary_sensor.synology_dsm_storage_volume_1_status') %}
          {% set v2 = states('binary_sensor.synology_dsm_storage_volume_2_status') %}
          {% if v1 == 'normal' or v2 == 'normal' %}on
          {% elif v1 == 'unknown' and v2 == 'unknown' %}off
          {% else %}on
          {% endif %}
        icon: mdi:server-network
      - name: NAS SMART status ok (contract)
        unique_id: rc_homelab_nas_smart_status_ok
        device_class: problem
        state: "{{ is_state('binary_sensor.synology_dsm_smart_status', 'normal') }}"
        icon: mdi:harddisk
      - name: NAS backup running (contract)
        unique_id: rc_homelab_nas_backup_running
        device_class: running
        state: >
          {% set s = states('sensor.ha_backup_last_backup') | default('unknown', true) %}
          {{ 'on' if 'in_progress' in s.lower() or 'running' in s.lower() else 'off' }}
        icon: mdi:backup-restore
  - sensor:
      - name: NAS last backup at (contract)
        unique_id: rc_homelab_nas_last_backup_at
        state: "{{ states('sensor.ha_backup_last_backup') | default('never', true) }}"
        icon: mdi:clock-outline
```

### §6.2 — Copy-pasteable helper YAML (Path B — QNAP)

Drop alongside §6.1 in the same package (or replace §6.1 — pick
the path you deployed):

```yaml
# RoamCore NAS contract helpers (recipe §6.2, QNAP / Path B).
# All entities are vendor-neutral per docs/reference/rc-entity-naming.md.
# Wraps upstream `sensor.qnap_*` entities from the QNAP integration
# (ha_integration_domain: qnap) into rc_homelab_nas_* ids.

template:
  - sensor:
      - name: NAS storage used pct (contract)
        unique_id: rc_homelab_nas_storage_used_pct
        unit_of_measurement: "%"
        state: >
          {{ max(states('sensor.qnap_volume_1_used_percent') | float(0),
                 states('sensor.qnap_volume_2_used_percent') | float(0)) }}
        icon: mdi:database
      - name: NAS storage total (contract)
        unique_id: rc_homelab_nas_storage_total_gb
        unit_of_measurement: "GB"
        state: >
          {{ (states('sensor.qnap_volume_1_size') | float(0)
            + states('sensor.qnap_volume_2_size') | float(0)) | round(1) }}
        icon: mdi:database
      - name: NAS storage free (contract)
        unique_id: rc_homelab_nas_storage_free_gb
        unit_of_measurement: "GB"
        state: >
          {{ ((states('sensor.qnap_volume_1_size') | float(0)
            - states('sensor.qnap_volume_1_used') | float(0))
            + (states('sensor.qnap_volume_2_size') | float(0)
            - states('sensor.qnap_volume_2_used') | float(0))) | round(1) }}
        icon: mdi:database
      - name: NAS CPU pct (contract)
        unique_id: rc_homelab_nas_cpu_pct
        unit_of_measurement: "%"
        state: "{{ states('sensor.qnap_system_cpu_usage') | float(0) }}"
        icon: mdi:chip
      - name: NAS memory pct (contract)
        unique_id: rc_homelab_nas_memory_pct
        unit_of_measurement: "%"
        state: "{{ states('sensor.qnap_system_memory_usage') | float(0) }}"
        icon: mdi:memory
  - binary_sensor:
      - name: NAS reachable (contract)
        unique_id: rc_homelab_nas_reachable
        device_class: connectivity
        state: >
          {% set v1 = states('binary_sensor.qnap_volume_1_status') %}
          {% set v2 = states('binary_sensor.qnap_volume_2_status') %}
          {% if v1 == 'ready' or v2 == 'ready' %}on
          {% elif v1 == 'unknown' and v2 == 'unknown' %}off
          {% else %}on
          {% endif %}
        icon: mdi:server-network
      - name: NAS SMART status ok (contract)
        unique_id: rc_homelab_nas_smart_status_ok
        device_class: problem
        state: "{{ is_state('binary_sensor.qnap_smart_status', 'normal') }}"
        icon: mdi:harddisk
      - name: NAS backup running (contract)
        unique_id: rc_homelab_nas_backup_running
        device_class: running
        state: >
          {% set s = states('sensor.ha_backup_last_backup') | default('unknown', true) %}
          {{ 'on' if 'in_progress' in s.lower() or 'running' in s.lower() else 'off' }}
        icon: mdi:backup-restore
  - sensor:
      - name: NAS last backup at (contract)
        unique_id: rc_homelab_nas_last_backup_at
        state: "{{ states('sensor.ha_backup_last_backup') | default('never', true) }}"
        icon: mdi:clock-outline
```

### §6.3 — Copy-pasteable helper YAML (Path C — Generic SMB)

For Path C, the upstream is the HA backup integration (which
reports last-backup state from the SMB-mounted share) plus the
NAS's own LAN ping (for reachability):

```yaml
# RoamCore NAS contract helpers (recipe §6.3, Generic SMB / Path C).
# All entities are vendor-neutral per docs/reference/rc-entity-naming.md.
# Path C uses HA's `homeassistant` network-storage block + the HA
# backup integration. Storage % / total / free come from a `shell_command`
# (or `command_line` sensor) that runs `df -h` on the mount point;
# reachability comes from `binary_sensor.ping` (HA's device_tracker
# `ping` integration); SMART comes from a `command_line` sensor running
# `smartctl` (if the operator runs the RoamCore box on the NAS directly,
# or has the NAS expose smartctl over SSH).

shell_command:
  nas_storage_used_pct: df -h /mnt/share_for_backups | tail -1 | awk '{print $5}' | tr -d '%'
  nas_storage_total_gb: df -BG /mnt/share_for_backups | tail -1 | awk '{print $2}' | tr -d 'G'
  nas_storage_free_gb: df -BG /mnt/share_for_backups | tail -1 | awk '{print $4}' | tr -d 'G'

template:
  - sensor:
      - name: NAS storage used pct (contract)
        unique_id: rc_homelab_nas_storage_used_pct
        unit_of_measurement: "%"
        state: "{{ states('sensor.nas_storage_used_pct_raw') | float(0) }}"
        icon: mdi:database
      - name: NAS storage total (contract)
        unique_id: rc_homelab_nas_storage_total_gb
        unit_of_measurement: "GB"
        state: "{{ states('sensor.nas_storage_total_gb_raw') | float(0) }}"
        icon: mdi:database
      - name: NAS storage free (contract)
        unique_id: rc_homelab_nas_storage_free_gb
        unit_of_measurement: "GB"
        state: "{{ states('sensor.nas_storage_free_gb_raw') | float(0) }}"
        icon: mdi:database
      # Path C doesn't expose CPU / memory from the NAS itself (no
      # upstream integration that talks to it) — these stay `unknown`.
      - name: NAS CPU pct (contract)
        unique_id: rc_homelab_nas_cpu_pct
        unit_of_measurement: "%"
        state: "unknown"
        icon: mdi:chip
      - name: NAS memory pct (contract)
        unique_id: rc_homelab_nas_memory_pct
        unit_of_measurement: "%"
        state: "unknown"
        icon: mdi:memory
  - binary_sensor:
      - name: NAS reachable (contract)
        unique_id: rc_homelab_nas_reachable
        device_class: connectivity
        state: "{{ is_state('binary_sensor.ping_192_168_1_20', 'on') }}"
        icon: mdi:server-network
      # Path C doesn't have an upstream S.M.A.R.T. integration unless
      # the operator installs `smartctl` + a `command_line` sensor —
      # leave `unknown` for honesty.
      - name: NAS SMART status ok (contract)
        unique_id: rc_homelab_nas_smart_status_ok
        device_class: problem
        state: "unknown"
        icon: mdi:harddisk
      - name: NAS backup running (contract)
        unique_id: rc_homelab_nas_backup_running
        device_class: running
        state: >
          {% set s = states('sensor.ha_backup_last_backup') | default('unknown', true) %}
          {{ 'on' if 'in_progress' in s.lower() or 'running' in s.lower() else 'off' }}
        icon: mdi:backup-restore
  - sensor:
      - name: NAS last backup at (contract)
        unique_id: rc_homelab_nas_last_backup_at
        state: "{{ states('sensor.ha_backup_last_backup') | default('never', true) }}"
        icon: mdi:clock-outline

command_line:
  - sensor:
      - name: NAS storage used pct (raw)
        unique_id: nas_storage_used_pct_raw
        command: "df -h /mnt/share_for_backups | tail -1 | awk '{print $5}' | tr -d '%'"
        unit_of_measurement: "%"
        scan_interval: 300
      - name: NAS storage total (raw)
        unique_id: nas_storage_total_gb_raw
        command: "df -BG /mnt/share_for_backups | tail -1 | awk '{print $2}' | tr -d 'G'"
        unit_of_measurement: "GB"
        scan_interval: 300
      - name: NAS storage free (raw)
        unique_id: nas_storage_free_gb_raw
        command: "df -BG /mnt/share_for_backups | tail -1 | awk '{print $4}' | tr -d 'G'"
        unit_of_measurement: "GB"
        scan_interval: 300
```

## Automations

Four sample automations, copy-pasteable into
`homeassistant/automations/roamcore_nas_*.yaml`:

### §7.1 — Alert when storage crosses 90% used

```yaml
alias: NAS — storage >= 90% used
mode: single
trigger:
  - platform: numeric_state
    entity_id: sensor.rc_homelab_nas_storage_used_pct
    above: 90
    for: "01:00:00"
condition:
  - condition: state
    entity_id: binary_sensor.rc_homelab_nas_reachable
    state: "on"
action:
  - service: persistent_notification.create
    data:
      title: RoamCore — NAS storage >= 90% used
      message: >-
        Storage on the NAS is at
        {{ states('sensor.rc_homelab_nas_storage_used_pct') }}% used
        ({{ states('sensor.rc_homelab_nas_storage_free_gb') }} GB free
        of {{ states('sensor.rc_homelab_nas_storage_total_gb') }} GB).
        Prune old Frigate clips, Trip Wrapped exports, or HA backups
        before new ones fail to write.
  - service: notify.mobile_app
    data:
      title: NAS storage >= 90%
      message: >-
        {{ states('sensor.rc_homelab_nas_storage_used_pct') }}% used;
        {{ states('sensor.rc_homelab_nas_storage_free_gb') }} GB free.
```

### §7.2 — Alert when S.M.A.R.T. health flips OFF

```yaml
alias: NAS — S.M.A.R.T. health flipped OFF
mode: single
trigger:
  - platform: state
    entity_id: binary_sensor.rc_homelab_nas_smart_status_ok
    from: "on"
    to: "off"
    for: "00:05:00"
action:
  - service: persistent_notification.create
    data:
      title: RoamCore — NAS S.M.A.R.T. health degraded
      message: >-
        S.M.A.R.T. health on the NAS has flipped OFF. One or more
        drives are reporting pre-failure attributes. Schedule
        drive replacement soon — DO NOT wait for the drive to
        fully fail.
  - service: notify.mobile_app
    data:
      title: NAS S.M.A.R.T. health degraded
      message: "Replace the failing drive soon — don't wait for total failure."
```

### §7.3 — Pause Trip Wrapped exports when NAS is unreachable

```yaml
alias: NAS — pause Trip Wrapped exports when unreachable
mode: single
trigger:
  - platform: state
    entity_id: binary_sensor.rc_homelab_nas_reachable
    from: "on"
    to: "off"
    for: "00:10:00"
action:
  - service: persistent_notification.create
    data:
      title: RoamCore — NAS unreachable (Trip Wrapped exports paused)
      message: >-
        NAS unreachable for 10 minutes; Trip Wrapped exports
        have been paused so they don't fail mid-write. Exports
        will resume automatically once the NAS is reachable
        again.
  - service: automation.turn_off
    target:
      entity_id: automation.trip_wrapped_export
trigger:
  - platform: state
    entity_id: binary_sensor.rc_homelab_nas_reachable
    from: "off"
    to: "on"
    for: "00:01:00"
action:
  - service: automation.turn_on
    target:
      entity_id: automation.trip_wrapped_export
  - service: persistent_notification.create
    data:
      title: RoamCore — NAS reachable (Trip Wrapped exports resumed)
      message: >-
        NAS is reachable again; Trip Wrapped exports resumed.
```

### §7.4 — Auto-trigger a backup before departure (Mode-based hook)

```yaml
alias: NAS — auto-trigger backup before departure (Travel mode)
mode: single
trigger:
  - platform: state
    entity_id: input_select.rc_mode
    to: "travel"
condition:
  - condition: state
    entity_id: binary_sensor.rc_homelab_nas_reachable
    state: "on"
  - condition: state
    entity_id: binary_sensor.rc_homelab_nas_backup_running
    state: "off"
action:
  - service: hassio.backup_full
    data:
      name: "pre-departure-auto-{{ now().strftime('%Y%m%d-%H%M') }}"
      include_database: true
  - service: persistent_notification.create
    data:
      title: RoamCore — backup started (pre-departure)
      message: >-
        Travel mode engaged and NAS reachable; started an
        automatic HA backup to the NAS. The backup will land in
        `share_for_backups` (or your Synology/QNAP share) and
        will appear on the dashboard's NAS tile once complete.
```

(Some operators prefer to NOT auto-backup on every mode flip —
this is opt-in. Disable the automation if you want backups to
stay manual.)

## Troubleshooting

- **HA shows stale storage % — DSM/QNAP polling interval too
  long.** The upstream `sensor.synology_dsm_*` entities default
  to a 5-minute scan interval, but Frigate clip offloads can
  change storage % faster than that. If the storage tile looks
  stuck, force a refresh in HA → **Developer Tools → States** by
  calling `synology_dsm.refresh`, or bump the template sensor's
  `scan_interval` in the contract helpers to 60 seconds.

- **NAS went to sleep — wake-on-LAN not configured.** Some
  DiskStations / QNAPs sleep their disks after a period of
  inactivity, and the HA integration reports `unknown` for
  storage % while the disks are spinning up. Fix: **Control
  Panel → Hardware & Power → Disk Sleep Timer** (DSM) or
  **Control Panel → System → Power Recovery → Disk Standby
  Timer** (QNAP): disable, or extend to a much longer interval.
  Wake-on-LAN can be configured from OpenWrt if you want
  scheduled wake-ups.

- **Slow CIFS share discovery — `vers=` mismatch.** If Path C's
  SMB mount is slow to come up (HA shows the share as
  `unavailable` for a minute after boot), the SMB protocol
  version is probably mismatched. Modern NASes default to
  SMB3; old clients fall back to SMB1 which is slow + disabled
  on most modern NASes. Fix: in the `homeassistant.custom_mounts`
  block, set `vers=3.0` (or `vers=3.1.1` for SMB multichannel).

- **DSM SSO/auth expiry — session token TTL too short.** The
  Synology DSM integration can lose authentication after a DSM
  firmware update or after the account's password rotates.
  Symptom: `binary_sensor.rc_homelab_nas_reachable` flips OFF,
  DSM logs show `WebAPI session expired`. Fix: re-run the
  Synology DSM integration's config_flow (Settings → Devices &
  Services → Synology DSM → ⋯ → Reconfigure), provide the
  updated password, and the integration re-authenticates.

- **QNAP firmware-blocked API — admin role required.** The
  QNAP integration needs admin-level API access; non-admin
  users can't see CPU/memory/volume stats even if they have
  share access. Symptom: HA integration loads but most
  sensors stay `unknown`. Fix: **Privilege Settings → Users →
  ha-roamcore → Edit → Role**: change to **Administration** (the
  QNAP integration has no read-only API mode in current
  firmware).

- **SMB1 disabled on the NAS — old clients can't connect.**
  Modern NASes disable SMB1 by default (good — SMB1 is
  insecure), but old HA add-ons + some automation scripts
  still try SMB1 first. Symptom: mount fails with `CIFS VFS:
  cifs_mount failed w/return code = -6`. Fix: ensure all
  clients specify `vers=3.0` (or newer) in the mount options.
  Don't re-enable SMB1 on the NAS — it's a security regression.

- **Backup folder permission errors — share ACL wrong.** When
  pointing HA's backup integration at an SMB share, the
  share's ACL must allow the `ha-backup` user to write. Symptom:
  HA logs show `Permission denied` when starting a backup.
  Fix: on the NAS, grant `ha-backup` write access to the share
  root (TrueNAS: **Permissions → ACL → Add Item**; Unraid:
  **Shares → Share Settings → Share access → Custom**;
  OpenMediaVault: **Access Rights Management → User → Edit →
  Privileges**).

- **`binary_sensor.rc_homelab_nas_reachable` is OFF but the NAS
  pings fine — DSM/QNAP API is down but the box is alive.**
  Path A / B's reachability tile is sourced from the upstream
  volume-status entity, not from a ping. If DSM/QNAP's
  management API is wedged but the box is otherwise alive
  (responds to ping, responds to SSH), the upstream volume-
  status entity stays `unknown` and the contract tile reports
  OFF. Fix: log into DSM/QNAP and restart the management
  service (DSM: **Control Panel → Restart DSM** — this is a
  soft restart of the management UI, not the box itself;
  QNAP: **Control Panel → System → Hardware → Restart
  Management Service**).

## §9 Privacy

- **Local only.** RoamCore does not phone home to Synology or
  QNAP; the contract tiles are 100% local. No telemetry to
  RoamCore. No NAS hostname, IP, MAC, share name, account name,
  volume name, or storage path in any contract entity beyond
  the aggregate counts and percentages the user explicitly asks
  for via OpenClaw.
- **NAS stats** come from the NAS's own management API (DSM's
  `/webapi/entry.cgi` endpoint, QNAP's `/cgi-bin/` endpoint,
  or `df -h` on the SMB mount), which serves the LAN only — no
  internet round-trip unless you've enabled myQNAPcloud / DSM's
  QuickConnect (which is the operator's choice, not RoamCore's).
- **No NAS hostname, IP, MAC, share name, account name, volume
  name, or storage path** is captured in any `rc_homelab_nas_*`
  entity, OpenClaw summary key, or dashboard tile. The
  contract is intentionally vendor-neutral — the OpenClaw
  queries are "how much storage is used?", "is the NAS
  reachable?", etc., not "what's the IP of my Synology?".

## §10 Promoting to tier-a (outline)

When a real NAS lands on the CI bench (likely via
`testcontainers/synology-dsm` with a synthetic webapi fixture,
or `testcontainers/qnap` with a synthetic CGI fixture — both
upstream integrations already have testcontainer-style fixtures
in their own CI), this connection is the candidate to promote to
tier-a:

1. Add a native `config_flow.py` that wraps the upstream
   Synology DSM / QNAP config_flow (or ships its own wizard
   steps) and walks the operator through choosing Path A vs
   Path B vs Path C + providing the LAN URL + credentials (or
   the SMB share details for Path C).
2. Add a RoamCore-side `__init__.py` that listens for the
   upstream config_flow completing and auto-creates the
   `rc_homelab_nas_*` contract helpers (today those are manual
   YAML from §6.1 / §6.2 / §6.3).
3. Add an integration test that asserts the
   `rc_homelab_nas_*` contract entities appear after a
   synthetic DSM/QNAP/SMB admin-API fixture returns a known
   payload.
4. Flip `tier_requirements` to include `working_config_flow` +
   `integration_test_passes` + `no_manual_yaml_required`.
5. Drop `tier_warnings` entries that mention no-real-NAS /
   recipe-depends-on-user.
6. Flip `status` from `beta` to `shipped`.
7. Flip `wizard.one_tap` to `true`.

Until then, this stays at tier-b (beta, recipe) — the recipe is
sound, the contract is honest, and we don't claim one-tap
coverage we don't have.