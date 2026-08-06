# Hub Backup — nightly automatic snapshot of your Hub that is verified-restorable

**Tier:** A (native integration; real RoamCore-owned Python service handler at `homeassistant/custom_components/roamcore/backup.py` + 22 pytest tests at `homeassistant/packages/tests/test_hub_backup.py` + 10 bash assertions at `scripts/checks/hub-backup-smoke.sh`)

**Category:** backup
**Status:** beta

## What this connection is

Hub Backup gives you a nightly automatic snapshot of your Hub that is verified-restorable — if anything goes wrong, recovery is one button and one flash away. RoamCore runs the backup at 02:00 every night, then immediately tests that the backup can actually be restored (not just that it was made), and surfaces a plain-English status ("Your last backup ran 2 hours ago and checked out.") on a single dashboard tile. The 5-step IKEA flow is the operator-facing affordance surface (Enable → Set destination → Set retention → Wait for first run → Check the tile). The full howto lives at [`docs/recipe.md`](docs/recipe.md).

This is the **second true tier-a connection** in the RoamCore connection pipeline. Unlike the first tier-a (`connections/openclaw-api/`, Wave 3 #64) which wraps an existing custom component, this slice SHIPS a new RoamCore-owned service handler at `homeassistant/custom_components/roamcore/backup.py` (~240 LOC) + a nightly cron package at `homeassistant/packages/roamcore_hub_backup.yaml` + the 22 pytest tests + the bash smoke check. The tier-a claim is provable via `pytest homeassistant/packages/tests/test_hub_backup.py` (22/22 PASS) + `bash scripts/checks/hub-backup-smoke.sh` (10/10 PASS).

## The 5-step operator flow

- **Step 1 — Enable.** The `input_boolean.rc_hub_backup_enabled` toggle ships ON by default; flip OFF only to pause nightly backups.
- **Step 2 — Set destination.** The `input_text.rc_hub_backup_destination` defaults to `/config/.roamcore/backups/` (mode password so the value is obscured in the dashboard).
- **Step 3 — Set retention.** Pick one of three options via `input_select.rc_hub_backup_retention_policy` — `7 daily + 4 weekly + 12 monthly`, `30 daily only` (default), or `90 daily only`.
- **Step 4 — Wait for first run.** The §8.1 nightly-create automation fires at 02:00 daily; the first run surfaces a plain-English status in `input_text.rc_hub_backup_status`.
- **Step 5 — Check the tile.** Glance at `sensor.rc_hub_backup_last_status` + `sensor.rc_hub_backup_age_minutes` + `binary_sensor.rc_hub_backup_healthy` to confirm the backup ran + the restore-test passed.

## Files

- `connection.yml` — the source-of-truth tier-a manifest.
- `__init__.py` — `DOMAIN = "hub_backup"` marker + tile-name constants for the audit.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- RoamCore-owned service handler: `homeassistant/custom_components/roamcore/backup.py` (~240 LOC — wraps HA core `backup.create` / `backup.list` / `backup.delete` + the RoamCore `roamcore.create_backup` / `roamcore.list_backups` / `roamcore.delete_backup` / `roamcore.test_restore` services).
- Helper package: `homeassistant/packages/roamcore_hub_backup.yaml` (declares the 10 contract entities + the 3 §8 MANDATORY automations).
- Pytest rig: `homeassistant/packages/tests/test_hub_backup.py` (22 tests).
- Bash smoke check: `scripts/checks/hub-backup-smoke.sh` (10 assertions).
- User-facing IKEA-style runbook: `docs/runbooks/hub-backup.md` (5 steps + 3-line troubleshooting + useful links).
- RoamCore entity naming: `docs/reference/rc-entity-naming.md` (the `hub_backup` subsystem was added by this slice).
