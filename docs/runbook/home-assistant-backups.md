# Home Assistant backups (VanCore)

## What we back up

VanCore treats “Home Assistant backup” in two layers:

1) **Proxmox VM backup** (vzdump) — full-machine recovery, simplest to automate.
2) **Home Assistant Full Backup** (Supervisor) — more granular restore inside HA.

In early stages, we prioritise (1) because it is deterministic and does not depend on HA add-ons or tokens.

## Current baseline (recommended)

Use Proxmox `vzdump` backups of the HA VM and sync them to Google Drive.

- VM: `101` (`homeassistant`)
- Local dumps: `/var/lib/vz/dump`
- Drive destination: `gdrive:VanCore-Backups/ha-vm/`

See:
- `docs/runbook/proxmox-backups-to-gdrive.md`

## Verification

On Proxmox:

```bash
ls -lh /var/lib/vz/dump/vzdump-qemu-101-* | tail
rclone lsl gdrive:VanCore-Backups/ha-vm/ | tail
```

## Future improvement

When we confirm stable access to the Home Assistant Supervisor API, add a second job to also create **HA Full Backups** and sync `/backup` to Drive.
