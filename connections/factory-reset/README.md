# Factory Reset — one-tap recover to a known-good state, never silent

**Tier:** A (native integration; real RoamCore-owned Python service handler at `homeassistant/custom_components/roamcore/factory_reset.py` + >=25 pytest tests at `homeassistant/packages/tests/test_factory_reset.py` + 12 bash assertions at `scripts/checks/factory-reset-smoke.sh`)

**Category:** system
**Status:** needs_information (tier-a, but the rollback path is still being wired — the chain-corruption recovery automation is dormant until the openclaw-api audit chain binary_sensor lands on main)

## What this connection is

Factory Reset gives you a panic button for your Hub — it always restores from your latest verified Hub Backup first, so you can recover from a bad config in one tap without losing any of your van data. The 5-step IKEA flow is the operator-facing affordance surface (Glance at the tile -> Click Dry-run -> Read the plan -> Click Confirm -> Check the post-flight tile). The full howto lives at [`docs/recipe.md`](docs/recipe.md).

This is the **third true tier-a connection** in the RoamCore connection pipeline. Like `connections/hub-backup/` (Wave 9 #123.a) and `connections/openclaw-api/` (Wave 3 #64), this slice SHIPS a new RoamCore-owned service handler at `homeassistant/custom_components/roamcore/factory_reset.py` (~340 LOC) + a helper package at `homeassistant/packages/roamcore_factory_reset.yaml` + the >=25 pytest tests + the bash smoke check.

The reset is **panic-button safe** — it always restores from the latest Hub Backup (from the hub-backup connection) and never silently destroys user data. The wizard enforces a 2-step confirmation flow with an explicit token ("type RESET to confirm") AND it runs a dry-run first that lists the current state + the last backup + the post-reset state. If no recent backup exists, the reset refuses to run and offers to take a backup first.

## The 5-step operator flow

- **Step 1 — Glance at the tile.** Open the dashboard and look at `sensor.rc_factory_reset_status` (plain-English "Ready" / "Dry-run shown" / "Confirm pending" / "Resetting…" / "Last reset: 3 days ago") and `binary_sensor.rc_factory_reset_safe_to_run` (green = safe to run, red = please back up first).
- **Step 2 — Click Dry-run.** Tap `input_button.rc_factory_reset_dry_run` to see the planned post-reset state + the last backup + the services that will restart. The 8-char token is generated and stored in `input_text.rc_factory_reset_token`.
- **Step 3 — Read the plan.** The dry-run report surfaces via `input_text.rc_factory_reset_dry_run_report` (plain English). The section 8.1 dry-run automation auto-clears the token after 5 minutes (operator walked away / changed their mind).
- **Step 4 — Click Confirm.** Tap `input_button.rc_factory_reset_confirm`. The section 8.2 confirm automation reads the token from the helper and calls `roamcore.factory_reset_confirm` with the value. The HA core `backup.restore` service runs against the latest verified-restorable backup. The Hub restarts.
- **Step 5 — Check the post-flight tile.** The section 8.4 postflight automation calls `roamcore.factory_reset_postflight_check` on HA start + writes the result to `sensor.rc_factory_reset_postflight_status`. A green tile means the reset worked + the Hub is healthy.

## What this depends on

- **Hub Backup** (`connections/hub-backup/`, MERGED on main as commit bfaa73d). The reset refuses to run without a recent Hub Backup (< 24h old). If no recent backup exists, the reset refuses to run and surfaces a plain-English message.
- **OpenClaw audit chain** (when the `binary_sensor.rc_openclaw_api_chain_valid` lands on main from the openclaw-api connection). The section 8.5 recovery automation references the binary_sensor by name + fires the chain-corruption recovery flow when it flips off (wipe audit log + restore from latest backup). The automation is dormant until the binary_sensor lands.

## Files

- `connection.yml` — the source-of-truth tier-a manifest.
- `__init__.py` — `DOMAIN = "factory_reset"` marker + tile-name + service-name constants for the audit.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- RoamCore-owned service handler: `homeassistant/custom_components/roamcore/factory_reset.py` (~340 LOC — registers 4 RoamCore services + a `HomeAssistantView` at `/api/roamcore/factory_reset/{action}` + the 2-step confirm flow + the chain-corruption recovery path).
- Helper package: `homeassistant/packages/roamcore_factory_reset.yaml` (declares the 11 contract entities + the 5 section 8 MANDATORY automations).
- Pytest rig: `homeassistant/packages/tests/test_factory_reset.py` (>=25 tests).
- Bash smoke check: `scripts/checks/factory-reset-smoke.sh` (12 assertions).
- User-facing IKEA-style runbook: `docs/runbooks/factory-reset.md` (5 steps + 3-line troubleshooting + useful links).
- Upstream Hub Backup connection: `connections/hub-backup/` (the MANDATORY `requires: hub-backup` dependency).
- RoamCore entity naming: `docs/reference/rc-entity-naming.md` (the `factory_reset` subsystem was added by this slice).
