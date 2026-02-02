# Backup Vault (VanCore)

This runbook describes how VanCore backups are stored and synchronised.

## Goals

- GitHub remains the **source of truth** for configuration, runbooks, and recovery procedures.
- Large binary backups (VM/LXC disks, HA full backups, OpenWrt exports) are stored **outside GitHub**.
- Backups are copied off-host where practical.

## Current approach (Google Drive via rclone)

We use `rclone` with a Google Drive remote named `gdrive`.

### Required remotes

- `gdrive:` — Google Drive (configured via `rclone config`)
- (recommended) `gdrive-crypt:` — encrypted wrapper around `gdrive:`

## One-time setup checklist

Run on the machine that produces backups (e.g., Proxmox host or backup VM).

1) Verify the remote exists:

```bash
rclone listremotes
rclone lsd gdrive:
```

2) Create destination folder:

```bash
rclone mkdir gdrive:VanCore-Backups
```

3) Create encrypted remote (recommended):

```bash
rclone config
# n) New remote
# name: gdrive-crypt
# storage: crypt
# remote: gdrive:VanCore-Backups
# password + salt: set strong values and store them safely (not in GitHub)
```

4) Verify:

```bash
rclone lsd gdrive-crypt:
```

## Backup layout (suggested)

Inside `gdrive-crypt:`, keep:

- `proxmox/` (any exported backups if used)
- `ha/` (Home Assistant full backups)
- `openwrt/` (sanitised exports; raw archives only if needed)

## Sync command

Example (local → Drive):

```bash
rclone sync /srv/vancore-backups gdrive-crypt: --create-empty-src-dirs --fast-list
```

## Retention

Retention should be enforced **at the source** (local) and/or on the destination.

Recommended baseline:
- Keep last 14 daily
- Keep last 8 weekly
- Keep last 12 monthly

(Implementation depends on where backups are created; document the exact commands used when configured.)
