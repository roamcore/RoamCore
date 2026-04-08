# RoamCore “Backup + Update” (Internal Runbook)

This guide documents the RoamCore **Settings → Backup + Update** flow.

## What it does

When the user clicks **Backup + Update** in the RoamCore dashboard:

1. **Attempts a full Home Assistant backup** (Supervisor snapshot) using HA’s built-in services:
   - Prefers `backup.create` (newer HA)
   - Falls back to `hassio.backup_full` (older supervised installs)
   - If neither service exists (non-supervised HA Core installs), backup is **not available** and the flow proceeds **best-effort**.

2. **Provisions RoamCore assets into `/config`** by downloading the RoamCore GitHub archive for an explicit git ref and copying `homeassistant/*` into `/config`.

3. Writes install metadata:
   - `/config/.roamcore/install-info.txt` (written by provisioning)
   - `/config/.roamcore/provisioned.marker`

4. **Does not restart Home Assistant automatically.** The user must restart HA after the update.

## Determinism & safety

- **Deterministic by ref:** Prefer release tags or commit SHAs.
- **Reversible:**
  - Restore a **Supervisor backup** (preferred), or
  - Restore files from `/config/.roamcore/backups/<timestamp>/`.
- **Concurrency-safe:** only one update runs at a time (guarded by an `asyncio.Lock`).

## How the UI determines “installed” and “latest”

The Settings tile calls:

- `GET /api/roamcore/update`

It returns:
- installed ref + timestamp (from `/config/.roamcore/install-info.txt`)
- installed integration version (local `manifest.json`)
- latest GitHub release tag (best-effort)

## Services

### `roamcore.backup_update`

Creates a full backup (best-effort) then provisions assets.

Parameters:
- `repo` (optional)
- `ref` (optional): explicit tag/commit/branch
- `target` (optional): `latest_release` resolves the latest GitHub release tag
- `backup` (optional, default `true`)
- `backup_name` (optional)

## “Supervisor backup without token” note

- **Inside Home Assistant (custom component)**: you do **not** need a Supervisor token. Call HA’s built-in services (`backup.create` or `hassio.backup_full`).
- **Outside Home Assistant (external scripts)**: you generally need authentication (Supervisor token or HA Long-Lived Access Token).
