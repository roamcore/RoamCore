# RoamCore — Claude Code Instructions

## Purpose
RoamCore is Bernard’s home-lab “golden image” + operating runbooks for:
- Proxmox host (PVE) and VM/LXC lifecycle
- Home Assistant (HA) configuration and operations
- Backups, rollback discipline, and documentation

Your job: make the system **boringly reliable**. Prefer small, reversible changes.

## Critical safety rules (hard)
1) **No secrets**
   - Never add tokens/keys/passwords to git.
   - Don’t print secrets into logs.
   - If you suspect a secret is needed, ask Bernard where it is stored.

2) **High-risk changes require recoverability first**
   Before any change affecting **Home Assistant config/add-ons/network/storage/updates** or **Proxmox config/storage/network**:
   - Ensure there is a Proxmox snapshot of the HA VM (or relevant VM)
   - Ensure a Home Assistant **Full Backup** exists
   - Ensure current repo state is committed to git
   If you can’t verify those, **stop and ask**.

3) **Be explicit about impact**
   - Separate “plan” from “execution”.
   - State what you will change, where, and why.
   - Prefer incremental commits.

4) **No destructive operations by default**
   - Don’t delete data/backups.
   - Don’t run package upgrades, storage/network changes, or migrations without confirmation.

## Workflow (default)
1) **Assess**: what’s the goal, target machine, and blast radius?
2) **Plan**: propose steps + files/commands.
3) **Implement**: make the smallest change set that works.
4) **Verify**: include concrete verification commands and expected outcomes.
5) **Document**: update runbooks/docs alongside code.

## Repo landmarks
- Proxmox → Google Drive backup sync script:
  - `scripts/backups/roamcore-rclone-sync.sh`
- Proxmox backup policy:
  - `infra/proxmox/backup-policy.md`
- Docs live under:
  - `docs/`

## Home Assistant config editing (Bernard preference)
- Treat the **live Home Assistant config** as the primary editing surface.
- Work directly on the HA host over SSH (`roamcore-ha`) under `/config` (symlink to `/homeassistant`).
- After making safe, verified changes in HA, mirror the relevant files back into this repo under `ha/` for long-term versioning.

## Remote access (from this machine)
SSH aliases (via `~/.ssh/config`):
- `roamcore-proxmox` → `root@192.168.1.10`
- `roamcore-ha` → Home Assistant host (see ssh config)

If you need to inspect live state, prefer read-only commands first.

## Git discipline
- Direct-to-main is allowed.
- **No force-push.**
- Commit messages should include: Context / Changes / Verification / Rollback.

## When unsure
Stop and ask Bernard before:
- any destructive action (deletes, wipes, overwrites without backups)
- any external action (posting, emailing, publishing)
- any Proxmox/HA upgrade, network/storage change, or service restart that could cause downtime

## Output style
- Be concise, operational, and concrete.
- Prefer commands + file paths + acceptance criteria over long prose.
