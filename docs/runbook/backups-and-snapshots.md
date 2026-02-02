# Backups and snapshots (VanCore)

## Goals

- Ensure we can recover from bad changes quickly.
- Keep the process low-ceremony but reliable.

## Layers

### 1) Proxmox snapshots (fast rollback)
- Use Proxmox snapshots before risky changes.
- Naming convention: `prechange-YYYYMMDD-HHMM-<shortdesc>`

### 2) Home Assistant backups
Two mechanisms:
- **Primary (baseline):** Proxmox `vzdump` backup of HA VM (VMID 101)
- **Secondary (future):** HA Supervisor Full Backups (when Supervisor token access is confirmed)

### 3) Off-host copy
- Sync Proxmox backups to Google Drive via rclone.

See:
- `docs/runbook/proxmox-backups-to-gdrive.md`
- `docs/runbook/home-assistant-backups.md`

## Verification

- Confirm HA UI reachable.
- Confirm latest backups exist locally and on Drive.

