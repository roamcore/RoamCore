# Decision: Use Proxmox vzdump as primary HA backup

Date: 2026-02-02

Context:
- We need an automated, reliable way to back up Home Assistant off-host.
- HA Full Backups (Supervisor) are useful but can be blocked by access/token constraints depending on deployment.
- Proxmox has a deterministic VM-level backup mechanism (`vzdump`) that can be synced to Google Drive.

Decision:
- Use **Proxmox vzdump of VM 101 (homeassistant)** as the primary backup mechanism.
- Sync resulting `.vma.*` artifacts to Google Drive via `rclone`.

Rationale:
- VM-level backups are straightforward to automate and restore.
- Avoids coupling backup reliability to HA add-ons/tokens.

Alternatives Considered:
- HA Supervisor Full Backups as the sole mechanism.

Impact:
- Recovery can restore the full HA VM state from Proxmox/Drive.
- We may add HA-native Full Backups later as a second layer.
