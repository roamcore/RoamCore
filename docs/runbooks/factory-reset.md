# Factory Reset

Your Hub has a panic button that always restores from your latest backup, so you can recover from a bad config in one tap without losing any of your van data.

## What this is

Factory Reset is a one-tap recover-to-known-good for your Hub. It always restores from your latest verified Hub Backup, so you can recover from a bad config in one tap without losing any of your van data. The reset is "panic-button safe" — it never silently destroys your data. The wizard shows you a preview of the plan before anything happens, and you have to type the word RESET to confirm.

## What you see

- **A status tile.** It reads "Ready" when the Hub is ready to reset, "Dry-run shown" after you preview the plan, "Confirm pending" while you decide, "Resetting…" while the Hub restarts, or "Last reset: 3 days ago" after a successful reset.
- **A safe-to-run indicator.** Green means your last Hub Backup is recent and the restore-check passed. Red means the last backup is too old or didn't pass — please take a new backup first.
- **A pre-flight warnings tile.** Plain-English messages like "No backup yet — please take a new backup first" or "All clear — your Hub is ready for a factory reset."
- **Two buttons.** A blue **Dry-run** button to preview the plan, and a red **Confirm** button (only enabled after a dry-run) to actually reset.
- **A token field.** Shows the 8-character code you need to type in the confirm field. The token is only valid for 5 minutes.

## What you do

1. **Glance at the tile.** Open the dashboard and look at the Factory Reset tile. Confirm the status says "Ready" and the safe-to-run indicator is green. If the indicator is red, see "What to do if it goes wrong" below.
2. **Click Dry-run.** Tap the **Dry-run** button. The tile shows a plain-English preview: "Last backup: 2 hours ago. Will restart integrations: victron, mqtt, tailscale. After reset, your dashboards + automations + helpers will look exactly like they did 2 hours ago." A short code appears in the token field.
3. **Read the plan.** Look at the preview. Make sure the last backup timestamp is recent (less than 24 hours old). If the plan looks good, proceed to Step 4. If you change your mind, just walk away — the token auto-clears after 5 minutes.
4. **Click Confirm.** Within 5 minutes, tap the **Confirm** button. The Hub restarts and comes back exactly as it was at the last backup. The whole thing takes about 3-5 minutes.
5. **Check the post-flight tile.** When the Hub is back up, the post-flight tile reads "Your Hub restarted successfully and the post-reset state matches the dry-run plan." If the post-flight tile shows an error, see "What to do if it goes wrong" below.

## What to do if it goes wrong

- **"I can't reset without a recent backup — your last backup is 3 days old."** The Hub Backup is stale (more than 24 hours old). The reset refuses to run to protect your data. Tap the **Back up now** button on the Hub Backup tile to take a fresh backup, wait a few minutes for it to finish, then try the dry-run again.
- **"Token expired — please re-run dry-run and try again."** The 8-character code is more than 5 minutes old. The reset cancelled itself to protect you. Tap the **Dry-run** button again to get a new code, then tap **Confirm** within 5 minutes.
- **"OpenClaw audit chain is invalid — please run recovery before reset."** The OpenClaw audit log went invalid (this is rare). The Hub will self-recover automatically by wiping the audit log + restoring from the latest backup. If the auto-recovery doesn't fire (the Hub might need a restart), go to Settings -> System -> Restart to trigger the recovery.

## Useful links

- The full step-by-step recipe is in the **Factory Reset** section of the RoamCore catalog.
- The Hub Backup runbook: explains how the nightly backup works and how to take a backup on demand.
- The GitHub issue tracker: open an issue at <https://github.com/roamcore/RoamCore/issues> with the label `factory-reset`.
- For the broader RoamCore catalog, browse to <https://roamcore.github.io/RoamCore/>.
