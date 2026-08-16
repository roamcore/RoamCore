# Factory Reset — recipe

This is the operator-facing recipe for the **Factory Reset** connection. It walks you through the FIVE-step IKEA flow + the "How the 2-step confirm works" section + the "How chain-corruption recovery works" section.

For the broader vanlifer-facing howto (no file paths, no internal jargon, no "Wave N" labels), see the IKEA-style runbook at the project docs site.

## §1 What this is

Factory Reset gives you a panic button for your Hub — it always restores from your latest verified Hub Backup first, so you can recover from a bad config in one tap without losing any of your van data. The reset is "panic-button safe": it ALWAYS restores from the latest Hub Backup and never silently destroys user data. The wizard enforces a 2-step confirmation flow with an explicit token AND it runs a dry-run first that lists the current state + the last backup + the post-reset state. If no recent backup exists, the reset refuses to run and offers to take a backup first.

## §2 Prerequisites

- RoamCore is installed (HACS or one-line command — RoamCore bundles the service handler at `homeassistant/custom_components/roamcore/factory_reset.py` as part of the standard install).
- The Hub Backup connection is installed (the reset refuses to run without a recent Hub Backup).
- A recent verified Hub Backup exists (< 24h old). If no recent backup exists, the reset refuses to run and surfaces a plain-English message ("I can't reset without a recent backup — your last backup is 3 days old. Please take a new backup first, then try again.").

## §3 Step 1 — Glance at the tile

1. Open the RoamCore dashboard.
2. Find the **Factory Reset** tile.
3. Confirm `sensor.rc_factory_reset_status` reads "Ready" (or "Last reset: X days ago" if you have reset before).
4. Confirm `binary_sensor.rc_factory_reset_safe_to_run` is ON (true when the last Hub Backup is < 24h old AND the last verify-integrity automation passed).

## §4 Step 2 — Click Dry-run

1. Tap the **Dry-run** button (`input_button.rc_factory_reset_dry_run`) on the Factory Reset tile.
2. The dry-run report surfaces in `input_text.rc_factory_reset_dry_run_report` (plain English: "Last backup: 2026-08-06 02:00. Will restart: homeassistant. Will restart integrations: victron, mqtt, tailscale. After reset, your dashboards + automations + helpers will look exactly like they did 2 hours ago.").
3. An 8-char token is generated and stored in `input_text.rc_factory_reset_token`. The token auto-clears after 5 minutes (the section 8.3 cancel automation).

## §5 Step 3 — Read the plan

1. Read the dry-run report in `input_text.rc_factory_reset_dry_run_report`. Verify the last backup timestamp + the integrations that will restart.
2. If something looks wrong, walk away — the section 8.3 cancel automation clears the token after 5 minutes.
3. If the plan looks good, proceed to Step 4.

## §6 Step 4 — Click Confirm

1. Tap the **Confirm** button (`input_button.rc_factory_reset_confirm`) on the Factory Reset tile.
2. The section 8.2 confirm automation reads the token from the helper and calls `roamcore.factory_reset_confirm` with the value. The service handler verifies the token matches the latest dry-run + checks the backup is still fresh + calls the HA core `backup.restore` service against the latest verified-restorable backup.
3. The Hub restarts. The section 8.2 confirm automation has a `mode: single` guard so re-firing the confirm button while a reset is in progress returns gracefully.

## §7 Step 5 — Check the post-flight tile

1. After the Hub restarts, open the dashboard.
2. Confirm `sensor.rc_factory_reset_postflight_status` reads "Your Hub restarted successfully and the post-reset state matches the dry-run plan." (or surfaces a plain-English error if the post-flight check failed).
3. Confirm `sensor.rc_factory_reset_status` reads "Last reset: 2 minutes ago" (or "Ready" if you want to reset again).

## §8 The 5 §8 MANDATORY automations

### §8.1 Dry-run-sets-token

- **Trigger.** `input_button.rc_factory_reset_dry_run` is pressed.
- **Action.** Calls the RoamCore `roamcore.factory_reset_dry_run` service. Writes the returned 8-char token to `input_text.rc_factory_reset_token`. Writes the dry-run report to `input_text.rc_factory_reset_dry_run_report`. Sets `input_boolean.rc_factory_reset_armed` to `true`. Sets `input_datetime.rc_factory_reset_last_dry_run` to the current time.
- **Idempotency.** `mode: single` — re-pressing the dry-run button while a reset is pending returns gracefully.

### §8.2 Confirm-requires-token-match

- **Trigger.** `input_button.rc_factory_reset_confirm` is pressed.
- **Condition.** `input_boolean.rc_factory_reset_armed` is `true` (a dry-run is pending).
- **Action.** Reads the token from `input_text.rc_factory_reset_token` + calls the RoamCore `roamcore.factory_reset_confirm` service with the value. Sets `sensor.rc_factory_reset_status` to "Resetting…". The Hub restarts when the confirm service returns.
- **Idempotency.** `mode: single` — re-pressing the confirm button while a reset is in progress returns gracefully.

### §8.3 Cancel-clears-token

- **Trigger.** Timer every 5 minutes.
- **Action.** Checks `input_datetime.rc_factory_reset_last_dry_run` for staleness. If the dry-run is >5 minutes old, the automation clears the token (sets `input_text.rc_factory_reset_token` to ""), sets `input_boolean.rc_factory_reset_armed` to `false`, and sets `sensor.rc_factory_reset_status` to "Ready".
- **Idempotency.** `mode: single` — re-firing the timer while a previous clear is in progress returns gracefully.

### §8.4 Postflight-check-on-boot

- **Trigger.** HA start (`homeassistant.start` event).
- **Action.** Calls the RoamCore `roamcore.factory_reset_postflight_check` service (idempotent). Writes the result to `sensor.rc_factory_reset_postflight_status`. The postflight check verifies the Hub is reachable, the latest backup is ingested, and the integrations are healthy.
- **Idempotency.** The service is idempotent — safe to re-run on every HA start.

### §8.5 Recovery-on-audit-chain-invalid

- **Trigger.** `binary_sensor.rc_openclaw_api_chain_valid` flips off (the openclaw-api audit chain went invalid).
- **Action.** Runs the chain-corruption recovery flow (wipe audit log + restore from latest backup). Surfaces a "your Hub self-recovered" tile via `sensor.rc_factory_reset_postflight_status`.
- **Idempotency.** The recovery is one-shot — once the chain is wiped + the backup is restored, the binary_sensor flips back on + the automation is dormant until the next chain corruption.

## §9 How the 2-step confirm works

The 2-step confirm flow is the core safety rail. The dry-run call (`roamcore.factory_reset_dry_run`) returns a short random 8-char token. The confirm call (`roamcore.factory_reset_confirm`) requires the token — if the token is wrong, missing, or stale, the confirm returns a 400 with a plain-English error message.

- **No dry-run, just confirm.** If the operator tries to confirm without a matching dry-run, the confirm returns 409 "No pending reset — please run dry-run first."
- **Wrong token.** If the operator types the wrong token, the confirm returns 400 "Wrong token — please re-run dry-run and copy the new token."
- **Stale token.** If the dry-run is >5 minutes old, the confirm returns 400 "Token expired — please re-run dry-run and try again."
- **Correct token.** If the operator types the correct token AND the backup is still fresh, the confirm returns 200 + the Hub restarts.

## §10 How chain-corruption recovery works

The section 8.5 recovery automation references `binary_sensor.rc_openclaw_api_chain_valid` by name. The binary_sensor is owned by the openclaw-api connection. When the binary_sensor flips off (the openclaw-api audit chain went invalid), the recovery automation fires:

1. Wipes the audit log file (sets the chain length to 0).
2. Restores from the latest Hub Backup.
3. Surfaces a "your Hub self-recovered" tile via `sensor.rc_factory_reset_postflight_status`.

The recovery is one-shot — once the chain is wiped + the backup is restored, the binary_sensor flips back on + the automation is dormant until the next chain corruption.

## §11 The 11 `rc_factory_reset_*` contract entities

| Domain | Tile id | Purpose |
|---|---|---|
| `input_button` | `rc_factory_reset_dry_run` | The "preview before reset" button. |
| `input_button` | `rc_factory_reset_confirm` | The actual panic button. |
| `input_text` | `rc_factory_reset_token` | The 8-char token returned by dry-run (auto-clears after 5 minutes). |
| `input_text` | `rc_factory_reset_dry_run_report` | The last dry-run report (plain English). |
| `input_boolean` | `rc_factory_reset_armed` | Internal flag that surfaces as a tile. |
| `input_datetime` | `rc_factory_reset_last_dry_run` | Timestamp for staleness (5-minute TTL). |
| `sensor` | `rc_factory_reset_status` | Plain-English surface ("Ready" / "Dry-run shown" / "Confirm pending" / "Resetting…" / "Last reset: 3 days ago"). |
| `sensor` | `rc_factory_reset_last_backup_age` | Human-readable age of the most recent Hub Backup. |
| `binary_sensor` | `rc_factory_reset_safe_to_run` | On iff last backup is < 24h old AND verify-integrity passed. |
| `sensor` | `rc_factory_reset_preflight_warnings` | Plain-English pre-flight warnings. |
| `sensor` | `rc_factory_reset_postflight_status` | The post-flight check result. |

## §12 Troubleshooting (3 entries)

- **"I can't reset without a recent backup — your last backup is 3 days old."** The Hub Backup is stale (> 24h). The reset refuses to run. Tap the **Back up now** button on the Hub Backup tile to take a fresh backup, then try the dry-run again.
- **"Token expired — please re-run dry-run and try again."** The 8-char token is > 5 minutes old. The section 8.3 cancel automation cleared the token. Tap the **Dry-run** button again to generate a new token, then tap **Confirm** within 5 minutes.
- **"OpenClaw audit chain is invalid — please run recovery before reset."** The openclaw-api audit chain went invalid. The section 8.5 recovery automation will fire automatically when `binary_sensor.rc_openclaw_api_chain_valid` flips off. If the automation is dormant (the binary_sensor is not yet wired), go to Settings -> System -> Restart to wipe the audit log manually.

## §13 Files in this connection + cross-references

- `connections/factory-reset/connection.yml` — the source-of-truth tier-a manifest.
- `connections/factory-reset/__init__.py` — `DOMAIN = "factory_reset"` marker + tile-name + service-name constants for the audit.
- `connections/factory-reset/docs/recipe.md` — this recipe.
- `connections/factory-reset/tests/test_connection_yml.py` — manifest honesty checks.
- `homeassistant/custom_components/roamcore/factory_reset.py` — RoamCore-owned service handler (~340 LOC).
- `homeassistant/custom_components/roamcore/services.yaml` — service definitions (4 services).
- `homeassistant/custom_components/roamcore/__init__.py` — `register_factory_reset_services(hass)` wired into `async_setup_entry`.
- `homeassistant/packages/roamcore_factory_reset.yaml` — helper package + 5 section 8 automations.
- `homeassistant/packages/tests/test_factory_reset.py` — >=25 pytest tests.
- `scripts/checks/factory-reset-smoke.sh` — 12 bash assertions.
- `docs/runbooks/factory-reset.md` — IKEA-style user-facing runbook.
- `scripts/check.sh` — wired with the new smoke check.
