# Hub Backup

Your Hub takes a copy of itself every night, then checks that the copy actually works, so that if anything ever goes wrong, recovery is one button and one flash away.

## What this is

Hub Backup makes sure your Hub can always be put back the way it was. Every night at 2 AM, your Hub saves a full copy of itself, then immediately tries restoring that copy in a safe sandbox to confirm it really works — not just that it was made. You see one tile that says "Your last backup ran 2 hours ago and checked out." in plain English.

## What you see

- **A single status tile.** It reads "Your last backup ran [time] ago and checked out." or "Your last backup failed — check the Hub is plugged in."
- **A "last backup" tile.** Shows the age in plain English ("2 hours ago" / "yesterday" / "no backup yet").
- **A green/red healthy indicator.** Green means a recent backup checked out; red means the last backup didn't run or didn't pass the restore check.

## What you do

1. **Turn on Hub Backup.** Open the Hub Backup screen. Confirm the master switch at the top is **ON** (it ships ON by default — you don't have to do anything).
2. **Pick where to keep the backups.** The destination defaults to the Hub's built-in backup folder. If you want to keep backups somewhere else (a USB drive, a network share), tap **Destination** and pick another folder.
3. **Pick how long to keep backups.** Tap **Retention** and choose one of:
   - **7 daily + 4 weekly + 12 monthly** — best if you travel a lot and want a year of history.
   - **30 daily only** (default) — best for most people; needs about 45 GB of free space.
   - **90 daily only** — best if you have lots of storage and want 3 months of history.
4. **Wait for the first run.** The Hub does its first backup at 2 AM the next morning. You don't need to do anything.
5. **Check the tile in the morning.** After 2 AM, open the dashboard. The status tile should read "Your last backup ran [time] ago and checked out." and the healthy indicator should be green.

## What to do if it goes wrong

- **"Your last backup didn't run tonight — check the Hub is plugged in and on Wi-Fi."** The Hub lost power or its connection during the night. Plug the Hub back in, confirm it's on Wi-Fi, then tap the **Verify now** button to re-test.
- **"Your last backup ran but the restore-check failed."** The backup saved fine, but the safety restore-check didn't pass. The Hub will try again tomorrow. If it keeps failing, restore from the last-known-good backup by going to **Settings → Backup + Update → Restore from backup**.
- **"Your destination is full."** The backup folder ran out of space. Either pick a smaller retention policy above (e.g. switch from "90 daily only" to "30 daily only") or move older backups to another drive and free up space.

## Useful links

- The full step-by-step recipe is in the **Hub Backup** section of the RoamCore catalog.
- The GitHub issue tracker: open an issue at <https://github.com/roamcore/RoamCore/issues> with the label `hub-backup`.
- For the broader RoamCore catalog, browse to <https://roamcore.github.io/RoamCore/>.
