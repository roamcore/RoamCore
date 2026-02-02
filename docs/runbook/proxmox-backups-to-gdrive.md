# Proxmox backups → Google Drive (rclone)

This runbook defines the baseline, low-ceremony backup approach for VanCore on the Proxmox host.

## Summary

- Proxmox creates local VM/LXC backups (vzdump) to a local storage path.
- `rclone` syncs those backups to Google Drive (`gdrive:VanCore-Backups`).
- Google Drive is treated as an off-host copy, **not** as a stateful backup system.

> This assumes you have already configured `rclone` and created a remote named `gdrive`.

## Prerequisites

On the Proxmox host:

```bash
rclone listremotes
rclone lsd gdrive:
```

Create destination folder (once):

```bash
rclone mkdir gdrive:VanCore-Backups
```

## Local source of truth (Proxmox vzdump)

Default local backup directory on Proxmox is typically:

- `/var/lib/vz/dump`

Confirm:

```bash
ls -la /var/lib/vz/dump | head
```

If you use a different Proxmox storage for backups, set `SRC_DIR` accordingly.

## Sync to Drive

Recommended destination layout:

- `gdrive:VanCore-Backups/proxmox-vzdump/`

Run a one-off sync:

```bash
SRC_DIR=/var/lib/vz/dump
DST=gdrive:VanCore-Backups/proxmox-vzdump

rclone sync "$SRC_DIR" "$DST" \
  --create-empty-src-dirs \
  --fast-list \
  --transfers 4 \
  --checkers 8 \
  --log-level INFO
```

### Notes

- `rclone sync` will remove files from Drive that no longer exist locally.
- This is intentional if local retention is configured correctly.

## Retention policy (recommended)

Enforce retention in **Proxmox** (local) so Drive mirrors the policy.

Recommended baseline:
- Keep **14** daily
- Keep **8** weekly
- Keep **12** monthly

Implement retention using Proxmox scheduled backup jobs (preferred), or prune scripts.

## Scheduling

### Option A: cron (simple)

Create `/etc/cron.d/vancore-rclone-backup`:

```cron
# Sync Proxmox vzdump backups to Google Drive daily at 02:30
30 2 * * * root /usr/local/sbin/vancore-rclone-sync.sh
```

### Option B: systemd timer (cleaner)

Use a `vancore-rclone-sync.service` + `.timer` pair.

(See `scripts/backups/` in this repo for templates.)

## Troubleshooting

- If `rclone lsd gdrive:` fails, re-check that you typed the remote with a colon.
  - `gdrive` ≠ `gdrive:`
- If Proxmox is writing backups elsewhere, update `SRC_DIR`.
- Use verbose logs:

```bash
rclone -vv sync /var/lib/vz/dump gdrive:VanCore-Backups/proxmox-vzdump
```
