# Proxmox backup policy (VanCore)

## Goal

Maintain recoverability while keeping operations low-ceremony.

## Baseline

- Use Proxmox scheduled backups (vzdump) for VMs/LXCs that matter.
- Enforce retention **locally**.
- Sync local backups to Google Drive using `rclone sync`.

## Retention

Recommended baseline:
- Daily: 14
- Weekly: 8
- Monthly: 12

## Verification

- Confirm backups exist locally:
  - `ls -lh /var/lib/vz/dump | tail`
- Confirm Drive contains the same set:
  - `rclone lsf gdrive:VanCore-Backups/proxmox-vzdump --max-depth 1 | tail`

## Rollback

- Restore via Proxmox UI from the desired vzdump backup.
- If the host is unavailable, download the needed backup from Drive and restore manually.
