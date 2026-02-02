# VanCore operating model

## GitHub

- GitHub is the **single source of truth** for:
  - documentation
  - configuration
  - operational knowledge
- Push directly to `main`.
- No force pushes or history rewriting.

See: `docs/runbook/github-discipline.md`

## Safe change discipline

Before risky changes (HA/Proxmox/networking):
1) Proxmox snapshot
2) HA backup
3) Git commit

See: `docs/runbook/backups-and-snapshots.md`

