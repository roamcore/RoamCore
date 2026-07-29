# RoamCore — OTA updates setup

This guide covers the RoamCore OTA update channel: how to flip channels, when auto-apply fires, how rollback works, and how to verify the add-on is healthy.

The slice ships:

- Add-on: `homeassistant/addons/roamcore_ota/` (poller + snapshot history + state file).
- Contract package: `homeassistant/packages/roamcore_ota.yaml` (entities + helpers + automation).
- Wizard snippet: `homeassistant/packages/roamcore_setup_wizard_ota.yaml` (entities + paste-this-card).
- Design doc: `docs/architecture/ota-channel.md` (image-id invariant, channel → tag mapping, rollback policy).
- Smoke check: `scripts/checks/ota-smoke.sh` (wired into `scripts/check.sh --core-only`).

## 1. Install the add-on

1. In Home Assistant, open **Settings → Add-ons → Add-on store**.
2. Add the local repo (`/config/addons` for a side-loaded add-on or your RoamCore side-load entry).
3. Install **RoamCore OTA**.
4. Start it. First boot writes `/config/.roamcore_image_id = dev-unknown` and creates `/share/roamcore/{state.json,ota.log,snapshots/}`.

The contract package and wizard snippet ship via `homeassistant/install.sh` and are picked up on next HA restart (or the standard "reload packages" path).

## 2. Flip the channel

Set the channel via the helper (or the wizard → OTA card → dropdown):

```yaml
input_select.rc_ota_channel:
  options: [stable, beta, nightly]
  initial: stable
```

- **stable** — latest non-prerelease GitHub release of `roamcore/RoamCore`.
- **beta** — latest prerelease GitHub release of `roamcore/RoamCore`.
- **nightly** — latest release whose tag starts with `nightly-`.

Changing the helper flips the channel on the next poll (default 6 h). You can force a check via **Developer tools → Actions → `script.rc_ota_check`** which restarts the add-on.

## 3. Auto-apply (off by default)

`input_boolean.rc_ota_auto_apply` defaults to **OFF**. When flipped ON:

- The automation `RC OTA auto-apply scheduler (03:00 local)` watches `binary_sensor.rc_ota_update_available`.
- It fires only at the hour set by `input_number.rc_ota_apply_hour` (default 3 = 03:00 local).
- It calls `shell_command.rc_ota_apply_at_3am`, which logs and triggers the apply path.

The apply path is intentionally narrow: the add-on is the source of truth, and the apply path **only** swaps to a snapshot whose `tag` matches the latest release on the selected channel. It refuses to apply if the target image is missing or the SHA-256 mismatch fails.

## 4. Rollback

Rollback is **always manual** in Wave 2 #30. There is no automatic rollback on first-boot failure (that's a follow-up; see `docs/architecture/ota-channel.md#failure-modes`).

To roll back:

1. Open **Developer tools → Actions → `script.rc_ota_rollback`**.
2. The script calls `shell_command.rc_ota_rollback`, which:
   - Picks the **most recent** snapshot record from `/share/roamcore/snapshots/` that is not the running one.
   - Verifies the SHA-256 against the record.
   - Restores the image and re-writes `/config/.roamcore_image_id` to the rolled-back ID.
3. `binary_sensor.rc_ota_rollback_pending` returns to OFF once the running image matches the rolled-back snapshot.

Snapshots are kept at `/share/roamcore/snapshots/` (default `snapshot_keep=3`). To see what's there:

```bash
ls /share/roamcore/snapshots/
cat /share/roamcore/snapshots/snapshot-*.json | jq -s
```

You can also copy a snapshot off-device for safekeeping — each record is a self-contained JSON sidecar with `version`, `tag`, `sha256`, `published_at`, `recorded_at`, and (after a successful apply) `applied_at`.

## 5. Privacy

**RoamCore OTA only talks to `api.github.com` over HTTPS. No telemetry.**

What the add-on sends out:

- A `GET https://api.github.com/repos/roamcore/RoamCore/releases?per_page=30` request, on the configured poll interval.
- Optionally, an `Authorization: Bearer <token>` header if you supply a `github_token` (for private-repo previews; default empty → unauthenticated).

What the add-on does **not** send out:

- Your device ID, IP, location, telemetry, or anything else.
- Your running version (other than as part of the local file state).
- Anything to anywhere other than `api.github.com`.

The add-on never opens a listening port. State is written only to `/share/roamcore/` (which is local to the HA host).

## 6. Troubleshooting

### "binary_sensor.rc_ota_update_available is unknown"

The MQTT discovery payloads haven't been ingested yet. Wait ~60 s, or **Developer tools → Reload → MQTT**. Check the add-on log (`/share/roamcore/ota.log`) for `state published:` lines.

### "The add-on won't start"

Inspect the supervisor add-on log:

```bash
ha addons logs local_roamcore_ota
```

Common causes:

- `python3` missing from the base image → already declared in the `Dockerfile` (`apk add --no-cache python3 bash jq coreutils tzdata`).
- `/config/.roamcore_image_id` not writable → the add-on needs `map: config:rw`.

### "Channel is `beta` but the latest beta is too old / missing"

The channel filter requires **at least one matching release**. If you set `nightly` but no `nightly-*` tag exists, the daemon logs `no release matched channel=nightly` and `sensor.rc_ota_latest_version` falls back to `none`.

### "Auto-apply never fires"

Check the conditions:

- `input_boolean.rc_ota_auto_apply` is **ON**.
- `binary_sensor.rc_ota_update_available` is **ON**.
- `now().hour == input_number.rc_ota_apply_hour` (default `3`).

The automation runs in `mode: single`, so back-to-back triggers coalesce. Manual trigger: **Developer tools → Actions → `automation.trigger rc_ota_auto_apply_scheduler`**.

### "Snapshot count is 0 after first apply"

The add-on writes snapshots **per check** (not per apply). A check that finds an update writes one record; a check that finds nothing writes nothing. Snapshots only persist when an update is available on the selected channel — this keeps `/share/roamcore/snapshots/` from filling up with no-op records.

### "How do I uninstall?"

```bash
ha addons uninstall local_roamcore_ota
```

Then remove the contract package from your HA packages config. The snapshot directory is left in place at `/share/roamcore/snapshots/` so you can recover manually before deleting it.

## See also

- `docs/architecture/ota-channel.md` — design doc.
- `docs/reference/rc-entity-naming.md` — `rc_ota_*` naming follows the same convention.
- `scripts/checks/ota-smoke.sh` — the static smoke that runs in CI.