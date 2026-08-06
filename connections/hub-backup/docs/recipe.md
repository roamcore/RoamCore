# Hub Backup — recipe

This is the operator-facing recipe for the **Hub Backup** connection. It walks you through the FIVE-step IKEA flow + the "How to restore" section + the "How to factory reset" section.

For the broader vanlifer-facing howto (no file paths, no internal jargon, no "Wave N" labels), see the IKEA-style runbook at the project docs site.

## §1 What this is

Hub Backup gives you a nightly automatic snapshot of your Hub that is verified-restorable — if anything ever goes wrong, recovery is one button and one flash away. RoamCore runs the backup at 02:00 every night, then immediately tests that the backup can actually be restored (not just that it was made), and surfaces a plain-English status on a single dashboard tile.

## §2 Prerequisites

- RoamCore is installed (HACS or one-line command — RoamCore bundles the service handler at `homeassistant/custom_components/roamcore/backup.py` as part of the standard install).
- The Hub is plugged in + on Wi-Fi (the backup runs against the Hub's local state).
- The destination drive has at least 5 GB of free space (each backup is ~1-2 GB; the default `30 daily only` policy needs ~30-60 GB).

## §3 Step 1 — Enable

1. Open the RoamCore dashboard.
2. Find the **Hub Backup** tile.
3. Confirm `input_boolean.rc_hub_backup_enabled` is ON (the helper package ships with `initial: true` — backups start running automatically as soon as the helper package loads).

## §4 Step 2 — Set destination

1. Tap the **destination** tile under Hub Backup.
2. Confirm `input_text.rc_hub_backup_destination` is set to the desired path (default `/config/.roamcore/backups/`).
3. The input_text is mode password so the value is obscured in the dashboard — only the operator can read it back.

## §5 Step 3 — Set retention

1. Tap the **retention policy** selector under Hub Backup.
2. Pick ONE of the three options:
   - `7 daily + 4 weekly + 12 monthly` — default for operators who travel frequently + want a year of history.
   - `30 daily only` (default) — best for most operators; 30 days × ~1.5 GB ≈ 45 GB of destination space.
   - `90 daily only` — for operators with abundant storage + who want 3 months of history.
3. The §8.3 cleanup-old automation enforces the policy at 03:30 daily.

## §6 Step 4 — Wait for first run

1. The §8.1 nightly-create automation fires at **02:00 daily** (the cron expression is `0 2 * * *`).
2. The automation calls the RoamCore `roamcore.create_backup` service with `retention_days: 30` (the default; the operator-chosen retention policy is enforced by the §8.3 cleanup-old automation, not by the nightly-create).
3. The automation writes the result to `input_text.rc_hub_backup_status` as plain English.
4. The §8.1 automation has a `mode: single` guard so re-firing the cron while a backup is running returns gracefully (no double-creation).

## §7 Step 5 — Check the tile

1. After 02:00 the next morning, open the dashboard.
2. Confirm `sensor.rc_hub_backup_last_status` shows a plain-English message like "Your last backup ran 2 hours ago and checked out."
3. Confirm `sensor.rc_hub_backup_age_minutes` shows a number under 1500 (≈ 25h, since backups run every 24h).
4. Confirm `binary_sensor.rc_hub_backup_healthy` is ON (true when age_minutes < 1500 AND the last verify-integrity automation passed).

## §8 The 3 §8 MANDATORY automations

### §8.1 Nightly-create-backup

- **Trigger.** Cron at 02:00 daily (`0 2 * * *`).
- **Condition.** `input_boolean.rc_hub_backup_enabled` is ON.
- **Action.** Calls the RoamCore `roamcore.create_backup` service with `retention_days: 30`. Writes the result (`backup_id` + `path` + `size_bytes`) to `input_text.rc_hub_backup_status` as plain English.
- **Idempotency.** `mode: single` — re-firing the cron while a backup is running returns gracefully.

### §8.2 Verify-integrity

- **Trigger.** `roamcore.test_restore` completes after the nightly-create.
- **Action.** Calls `roamcore.test_restore` against the newly-created backup. Writes the result (`restorable: bool` + `tested_at`) to `input_text.rc_hub_backup_status` as plain English.
- **Outcome.** Surfaces "Your last backup ran and the restore-test passed." OR "Your last backup ran but the restore-test failed — check the Hub is plugged in."

### §8.3 Cleanup-old

- **Trigger.** Cron at 03:30 daily (`30 3 * * *`).
- **Action.** Calls `roamcore.list_backups` to enumerate existing backups, then calls `roamcore.delete_backup` for any backup older than the operator-chosen retention policy (`input_select.rc_hub_backup_retention_policy`).
- **Outcome.** The destination stays within the policy's storage budget.

## §9 How to restore

1. Open the RoamCore dashboard.
2. Tap **Settings → Backup + Update → Restore from backup**.
3. Pick the desired backup from the list (the dashboard shows `created_at` + plain-English `status` for each).
4. Tap **Restore**. RoamCore restarts the Hub with the backup's state.

> ⚠️ This is the operator-facing one-tap restore flow. The `roamcore.test_restore` service runs a sandbox restore-test (verifies the backup can be restored, doesn't actually restore) — the production restore is the dashboard flow above.

## §10 How to factory reset

1. If you want to wipe the Hub + start fresh (e.g., before selling the van), the flow is documented in the #123.b follow-up slice (factory reset). For now, the canonical flow is:
   - Tap **Settings → Backup + Update → Create fresh backup** (one-tap full backup).
   - Tap **Settings → Backup + Update → Restore from backup → pick the pre-factory-reset backup** (this is your last-known-good state).
   - Manually delete all `rc_hub_backup_*` helpers via Developer Tools → Services → `input_boolean.turn_off` etc.
   - Delete `/config/.roamcore/backups/` manually.

> ⚠️ The factory-reset flow is intentionally NOT automated in this slice (the recipe's "How to factory reset" section cross-references the #123.b follow-up slice for the canonical flow).

## §11 The 10 `rc_hub_backup_*` contract entities

| Domain | Tile id | Purpose |
|---|---|---|
| `input_boolean` | `rc_hub_backup_enabled` | Master enable toggle (pauses nightly backups when OFF). |
| `input_datetime` | `rc_hub_backup_next_run` | Date_time helper tracking the next scheduled run (default tomorrow 02:00). |
| `input_select` | `rc_hub_backup_retention_policy` | Operator-chosen retention policy (3 options). |
| `input_text` | `rc_hub_backup_destination` | Operator-owned destination path (mode password; default `/config/.roamcore/backups/`). |
| `input_text` | `rc_hub_backup_status` | Operator-visible plain-English status. |
| `sensor` | `rc_hub_backup_last_status` | Mirrors `input_text.rc_hub_backup_status` + adds a plain-English banner. |
| `sensor` | `rc_hub_backup_age_minutes` | Minutes since last successful backup (99999 if never). |
| `binary_sensor` | `rc_hub_backup_healthy` | Resolved healthiness chip (true when age < 25h AND verify-integrity passed). |
| `button` | `rc_hub_backup_backup_now` | Operator-triggered one-tap "back up now". |
| `button` | `rc_hub_backup_verify_now` | Operator-triggered one-tap "verify restore now". |

## §12 Troubleshooting (3 entries)

- **"Your last backup failed — check the Hub is plugged in."** The Hub lost power or Wi-Fi during the nightly backup. Confirm the Hub is plugged in + on Wi-Fi, then tap the **verify now** button to re-test.
- **"Your last backup ran but the restore-test failed."** The backup ran but the sandbox restore-test failed. RoamCore will retry tomorrow; if it keeps failing, restore from the last-known-good backup via Settings → Backup + Update → Restore from backup.
- **"Your destination path is full."** The destination drive ran out of space. Either increase the retention policy (e.g., from `30 daily only` to `7 daily + 4 weekly + 12 monthly`) or move older backups to another drive.

## §13 Files in this connection + cross-references

- `connections/hub-backup/connection.yml` — the source-of-truth tier-a manifest.
- `connections/hub-backup/__init__.py` — `DOMAIN = "hub_backup"` marker + tile-name constants for the audit.
- `connections/hub-backup/docs/recipe.md` — this recipe.
- `connections/hub-backup/tests/test_connection_yml.py` — manifest honesty checks.
- `homeassistant/custom_components/roamcore/backup.py` — RoamCore-owned service handler (~240 LOC).
- `homeassistant/custom_components/roamcore/services.yaml` — service definitions (4 services).
- `homeassistant/custom_components/roamcore/__init__.py` — `register_backup_services(hass)` wired into `async_setup_entry`.
- `homeassistant/packages/roamcore_hub_backup.yaml` — helper package + 3 §8 automations.
- `homeassistant/packages/tests/test_hub_backup.py` — 22 pytest tests.
- `scripts/checks/hub-backup-smoke.sh` — 10 bash assertions.
- `docs/runbooks/hub-backup.md` — IKEA-style user-facing runbook.
- `scripts/check.sh` — wired with the new smoke check.
