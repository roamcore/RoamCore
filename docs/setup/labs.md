# RoamCore — Labs setup

> **Tier: b** (community-supported) — first-slice contract layer; opt-in.

This guide covers the RoamCore Labs subsystem (Wave 2 #32): how to bundle the active setup as a local tar.gz, share it out-of-band, and import a bundle on another RoamCore install. The whole subsystem is **local and privacy-by-default** — RoamCore never phones home, never uploads a bundle, never opens a third-party HTTP connection.

The slice ships:

- Contract package: `homeassistant/packages/roamcore_labs.yaml` (8 contract entities + wizard helpers).
- Wizard snippet: `homeassistant/packages/roamcore_setup_wizard_labs.yaml` (4 wizard scripts + status refresh).
- Custom-component services: `roamcore.labs_export_setup` and `roamcore.labs_import_setup` (registered in `homeassistant/custom_components/roamcore/services.yaml`).
- Headless CLI mirrors: `homeassistant/tools/labs/export_setup.py` and `homeassistant/tools/labs/import_setup.py` (stdlib-only).
- Catalog entry: `docs/catalog/community/labs.md` (tier-b).
- Smoke check: `scripts/checks/labs-smoke.sh` (wired into `scripts/check.sh --core-only`).

## 1. Enable the Labs subsystem

The Labs subsystem is **off by default**. Operators must opt in.

**Setup Wizard:** open the wizard, advance to the **Labs** stage, and tap the *Enable* button. The wizard flips `input_boolean.rc_labs_enabled` ON.

**Manual:** from Developer Tools → Services, call `input_boolean.turn_on` with `entity_id: input_boolean.rc_labs_enabled`.

When the subsystem is OFF, the contract sensors (`sensor.rc_labs_export_count`, `sensor.rc_labs_import_count`) report `unavailable` (never `unknown`). The wizard card renders a clear "Off" chip.

## 2. Export the active setup

There are two equivalent paths.

**Setup Wizard:** tap the *Export* button. The wizard calls `roamcore.labs_export_setup` with no arguments. The bundle is written under `/config/.storage/roamcore_labs/exports/<UTC-timestamp>/roamcore_setup.tar.gz`.

**Manual / headless CLI:**

```bash
python3 homeassistant/tools/labs/export_setup.py --help
python3 homeassistant/tools/labs/export_setup.py --dry-run
python3 homeassistant/tools/labs/export_setup.py \
    --target /config/.storage/roamcore_labs/exports/manual/roamcore_setup.tar.gz
```

The bundle is a flat tar.gz with three top-level entries:

- `manifest.json` — schema + version + creator + UTC timestamp + the list of packages the operator opted in to.
- `dashboard.yaml` — the active dashboard YAML (best-effort).
- `packages/...` — a snapshot of the `homeassistant/packages/` tree at bundle time.

The CLI exits non-zero on any error path. The `--dry-run` flag resolves the output path + manifest without writing the bundle.

## 3. Share the bundle out-of-band

**RoamCore does not transmit the bundle anywhere.** The owner chooses how to share it. Common options:

- **USB stick** — copy the tar.gz to a USB drive, ship it to the second site, import there.
- **SMB / NFS / Synology** — copy the tar.gz to a shared folder on your local network.
- **Email / chat / forum** — attach the tar.gz to a private message. The bundle is plain text (YAML + JSON) so any channel works.
- **Git gist or repo** — many owners publish a "my RC setup" gist on git. The bundle is small enough to commit.

The bundle contains **your** active setup (your dashboard, your selected packages, your package list). Treat it the same way you'd treat any other backup of your HA config.

## 4. Import a bundle on another RoamCore install

**Setup Wizard:** open the wizard, advance to the **Labs** stage, paste the bundle path into the *Pending import* field, tap *Import*. The wizard calls `roamcore.labs_import_setup` with `dry_run=false` (or `true` for a preview).

**Manual / headless CLI:**

```bash
python3 homeassistant/tools/labs/import_setup.py --help
python3 homeassistant/tools/labs/import_setup.py \
    --bundle /config/.storage/roamcore_labs/exports/20260729T211214Z/roamcore_setup.tar.gz \
    --dry-run
python3 homeassistant/tools/labs/import_setup.py \
    --bundle /config/.storage/roamcore_labs/exports/20260729T211214Z/roamcore_setup.tar.gz \
    --apply
```

The CLI is split into two phases:

1. **stage** — the bundle is unpacked into `/config/.storage/roamcore_labs/imports/<stem>_<timestamp>/` and the path is written to `input_text.rc_labs_pending_import`. The wizard shows the pending-import pill.
2. **apply on next reload** (`--apply` flag) — the staged bundle is marked as *apply-on-next-reload*. The next HA reload copies the staged files into `/config/packages/` and stages the dashboard YAML for review. The actual apply is gated on operator consent.

The import is **idempotent**. Staging the same bundle twice creates two staging directories (with different UTC timestamps); the second does not overwrite the first. The path in `input_text.rc_labs_pending_import` always points at the most recent stage.

The service **defaults to `dry_run=true`** so a slip-up never extracts a bundle. The operator has to opt in explicitly (`dry_run=false`, or `--apply` in the CLI) to write anything outside the staging root.

## 5. Privacy

**RoamCore does not phone home. Bundles are local files. The owner chooses how to share.**

What the Labs subsystem does:

- Local-only stdlib (`tarfile`, `json`, `pathlib`) — no third-party imports, no HTTP clients.
- Writes bundles to `/config/.storage/roamcore_labs/exports/<UTC-timestamp>/` (inside the HA config dir; the operator can browse it via the standard file editor).
- Reads bundles from any path the operator chose to copy one to.
- Updates `/config/.storage/roamcore_labs/state.json` with the export / import counters so the wizard chip can show a "X exports, Y imports" pill.
- Emits a `logbook.log` entry on each successful export / import so the operator has an audit trail.

What the Labs subsystem does **not** do:

- **No remote upload.** RoamCore never opens an outbound connection to a third-party host. The bundle is a local file; the owner chooses where to share it.
- **No telemetry.** No "anonymous usage stats", no "crash reports", no "diagnostic uploads".
- **No DNS resolution.** The export / import paths are literal filesystem paths the operator chose.
- **No third-party HTTP library.** The contract and the smoke both reject any `import requests` / `urllib.request` / `urllib3` / `httpx` / `aiohttp` in the slice code.
- **No signature / verification.** RoamCore does not sign or verify bundles. The owner is in control of "is this bundle trustworthy?" — the same way the owner is in control of "is this tar.gz trustworthy?".

The privacy invariant is enforced in CI by `scripts/checks/labs-smoke.sh`. The smoke greps the contract package, the wizard snippet, the custom-component code, and the CLI helpers; any forbidden import would fail the build.

## 6. Troubleshooting

### "binary_sensor.rc_labs_enabled is unknown"

The contract binary sensor mirrors the `input_boolean.rc_labs_enabled` helper. Verify the helper exists:

```bash
# Either via the UI:
# Settings → Devices & Services → Entities → filter rc_labs_enabled
# Or via the CLI:
ha core entities | grep rc_labs_enabled
```

If the helper is missing, the contract package didn't load. Restart Home Assistant or check `/config/packages/roamcore_labs.yaml` for a YAML error.

### "Export count stays at 0"

The counter is a `command_line` sensor that reads `/config/.storage/roamcore_labs/state.json`. The service writes the state on each successful export. If the count is stuck at 0:

1. Check the file exists: `ls /config/.storage/roamcore_labs/`.
2. Read the JSON: `cat /config/.storage/roamcore_labs/state.json`.
3. Force a refresh: **Developer Tools → Actions → `script.rc_labs_wizard_export_now`** (or call `roamcore.labs_export_setup` from the services dashboard).

### "Pending import is sticky"

`input_text.rc_labs_pending_import` always points at the most recent bundle you staged. To clear it, set the field to `""` from Developer Tools → Actions.

### "Apply on next reload didn't apply"

The `apply` flag marks the bundle as *apply-on-next-reload*. The actual apply happens on the next HA config reload. Some operators report the dashboard not refreshing — that's a separate dashboard asset issue, not a Labs issue. Try **Developer Tools → Reload → YAML** or restart Home Assistant.

### "Bundle SHA doesn't match"

RoamCore does not verify bundle integrity (no signature, no SHA). If you share signed bundles, you can layer a `sha256sum` workflow on top. The Labs subsystem itself is intentionally agnostic about integrity.

## 7. What this slice does NOT do

This is the **first-slice** of the Labs subsystem. Future slices will add:

- A signed bundle variant (e.g. minisign / age), so the operator can verify the source of a bundle.
- A "package graph" validator that warns when an exported bundle references helpers that don't exist on the target install.
- A bundle preview that renders the manifest + the diff of the dashboard YAML before the operator commits to staging.
- A per-package prompt in the wizard so the operator can pick which packages to include in the export (today the export includes everything under `homeassistant/packages/`).

The slice ships with the privacy invariant **strictly enforced** in CI so future additions can't regress the local-only guarantee.

## See also

- `docs/catalog/community/labs.md` — tier-b catalog entry.
- `docs/reference/rc-entity-naming.md` — `rc_labs_*` naming follows the same convention.
- `scripts/checks/labs-smoke.sh` — the static smoke that runs in CI.
- `homeassistant/tools/labs/common.py` — shared bundle helpers (manifest schema, tar.gz layout, state file).
- `homeassistant/tools/labs/export_setup.py` — headless CLI mirror of `roamcore.labs_export_setup`.
- `homeassistant/tools/labs/import_setup.py` — headless CLI mirror of `roamcore.labs_import_setup`.
