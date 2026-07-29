# RoamCore OTA — Architecture

This document captures the design contract for the RoamCore OTA add-on: how image identity is established, how snapshots are stored, how channels map to GitHub releases, and how rollback is gated.

The slice that ships this doc is Wave 2 #30 (commit on `feat/wave2-ota-updates`). The slice is **only** the OTA primitive — apply paths, image-build pipelines, and signed-manifest verification are follow-ups tracked elsewhere.

## Image-id invariant

The running image is identified by a single deterministic string at `/config/.roamcore_image_id`. The string is opaque: it can be a content-addressable SHA-256, a tag, or a build uuid. It is the only identity the add-on compares against release metadata.

**Invariant:** `image_id == sha256(target_commitish)` of the running release. The add-on computes this SHA-256 from the GitHub `target_commitish` of the latest release on the selected channel and compares against `image_id`. On a mismatch, `binary_sensor.rc_ota_update_available` flips ON.

**First boot:** the add-on writes `dev-unknown` to `/config/.roamcore_image_id` if the file is missing. `dev-unknown` is treated as "no image known" and never matches any release — so the very first poll always reports `update_available=ON` until the running image is recorded.

**Recording:** when the apply path succeeds it writes the new `image_id` to `/config/.roamcore_image_id` *and* updates `/config/.roamcore_image_meta.json` with `{image_id, version, sha256, applied_at}`. The contract package's `input_text.rc_ota_running_version` is the user-facing label derived from the meta JSON.

## Snapshot semantics

Snapshots are **metadata records**, not image payloads. The add-on writes one JSON sidecar per "update available" check to `/share/roamcore/snapshots/`:

```json
{
  "version": "0.2.9",
  "tag": "v0.2.9",
  "sha256": "…",
  "published_at": "2026-07-29T18:00:00Z",
  "url": "https://github.com/roamcore/RoamCore/releases/tag/v0.2.9",
  "prerelease": false,
  "draft": false,
  "recorded_at": "2026-07-29T18:16:00Z",
  "applied_at": null
}
```

**Storage limit:** `snapshot_keep` (default 3, range 2–10). Older records are pruned oldest-first on every check that writes a new one. Records are pure JSON — no binary blobs, no database.

**Why metadata-only:** the actual image payload is owned by an external apply path (future slice) that downloads + verifies + writes a known-good image at a known location. This keeps the add-on's blast radius tiny: a malformed metadata record cannot brick a device, only a failed apply can.

**Where the running payload lives:** outside the add-on's scope in this slice. Future work will integrate with a dedicated apply primitive (e.g. a Mender client or a RoamCore-specific image writer). Until then, the `shell_command.rc_ota_apply_*` commands log + no-op; the slice ships the *detection* and *snapshot history* paths, not the apply path.

## Channel → release-tag mapping

The add-on reads `input_select.rc_ota_channel` and applies a filter to the GitHub releases list (`GET /repos/roamcore/RoamCore/releases?per_page=30`):

| Channel   | Filter                                                                                  |
|-----------|-----------------------------------------------------------------------------------------|
| `stable`  | `prerelease == false AND draft == false` (first match wins)                             |
| `beta`    | `prerelease == true  AND draft == false`                                                |
| `nightly` | `tag_name.startswith("nightly-") AND draft == false`                                    |

GitHub returns releases newest-first; the add-on picks the first match. If no release matches, `sensor.rc_ota_latest_version` reports `none` and the add-on logs `no release matched channel=<channel>`.

**Channel switching is hot.** The next poll (≤ `poll_minutes`) re-fetches and re-filters. The operator can force a check via `script.rc_ota_check`.

**No "all releases" channel.** Operators who want to pin a specific tag can use `input_text.rc_ota_running_version` (the user-facing label) and force-apply via `script.rc_ota_apply` — but the add-on itself does not honour a pinned version. Pinning is a follow-up.

## Rollback policy

Rollback is **manual only** in Wave 2 #30. There is no automatic rollback on first-boot failure (deferred; see *Failure modes* below).

When the operator triggers `script.rc_ota_rollback`:

1. The shell command reads `/share/roamcore/snapshots/` and picks the **most recent** snapshot whose `tag` is not the running version.
2. It verifies the SHA-256 of the rolled-back payload (TBD — for now this is a stub that logs).
3. It restores the image and re-writes `/config/.roamcore_image_id` to the rolled-back ID.
4. `binary_sensor.rc_ota_rollback_pending` returns to OFF.

If no snapshot exists (e.g. fresh install, never had an update), `script.rc_ota_rollback` is a no-op and logs `no rollback target`.

## Failure modes

| Failure                                        | Detection                             | Behavior                                                            |
|-----------------------------------------------|---------------------------------------|---------------------------------------------------------------------|
| `api.github.com` unreachable                  | `urllib.error.URLError` in poller      | Log warning; state retains last known values; `update_available` is whatever it was before. |
| `api.github.com` returns 4xx (rate limit)     | `urllib.error.HTTPError`              | Same as above + extra log line with the HTTP code.                  |
| `api.github.com` returns 5xx                  | `urllib.error.HTTPError`              | Same as above.                                                      |
| Channel filter has zero matches               | `pick_latest` returns `None`           | `latest_version` falls back to `none`; no snapshot written.        |
| Snapshot directory not writable               | `OSError` in `write_snapshot`         | Logged + exception in loop; the add-on keeps trying.               |
| `/config/.roamcore_image_id` missing           | `get_running_image_id`                | Writes `dev-unknown` on first call; this never matches anything.    |
| Apply path failed (future slice)              | TBD                                   | Will set `binary_sensor.rc_ota_rollback_pending=ON` + retain image. |
| Auto-apply fires but no update is available    | `binary_sensor.rc_ota_update_available=OFF` | Automation's condition blocks — no apply.                       |
| Disk full                                      | `OSError` writing state.json / log    | Logged; loop continues with degraded behaviour.                     |

The add-on never crashes on input. The outer loop catches every exception and logs at `ERROR`; the next iteration retries.

## Privacy

The add-on only talks to `api.github.com`. See `docs/setup/ota.md#privacy` for the full statement. No listening sockets, no telemetry, no upstream other than GitHub Releases.

## Constraints honoured by this slice

- **No new HA dependencies.** Stdlib only (`urllib.request`, `json`, `hashlib`, `logging`, `pathlib`).
- **No telemetry.** Outbound traffic limited to `api.github.com`.
- **Schema strict.** `config.yaml` validates against the current HA add-on schema (`slug`, `arch`, `map`, `options`, `schema` all present).
- **No docker required in CI.** Smoke checks assert structure + skip the docker build with a clear SKIP log.

## Follow-ups (not in this slice)

- Real apply path (download → verify → write image).
- Signed-manifest verification on apply.
- Auto-rollback on first-boot failure.
- Pinned-version channel (`input_text.rc_ota_pin_version`).
- Delta updates (currently every snapshot stores full metadata, not a delta).
- Tailscale-aware polling (poll more often when on a known-good LAN tailnet).