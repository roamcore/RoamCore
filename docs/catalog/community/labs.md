# Labs (share setups/dashboards)

**Support tier:** B (RoamCore native)

## What this is
RoamCore Labs lets an owner package their active setup (dashboard YAML + selected packages + a manifest) as a local tar.gz and share it out-of-band — email, USB, SMB, git, forum. The importer stages the bundle on the target install and applies it on the next HA reload. Privacy-by-default: no remote upload, no telemetry, no third-party HTTP. The owner is in control of every byte.

## Why it's useful in a van
- Share a "my RC setup" recipe with a friend without exposing it to a third-party service
- Bootstrap a second RoamCore install (e.g. backup van) from the same setup
- Snapshot your working setup before a major change so you can roll back
- Carry a setup across a migration (e.g. M.2 swap, new mini PC)

## Extra hardware required
- None. The bundle is a local file; the owner chooses how to share it.

## Install / best next step
- See: `docs/setup/labs.md`

## Bundle schema

The bundle is a flat tar.gz with the following top-level entries:

- `manifest.json` — schema + version + creator + UTC timestamp + the list of packages the operator opted in to.
- `dashboard.yaml` — the active dashboard YAML (best-effort).
- `packages/...` — a snapshot of the `homeassistant/packages/` tree at bundle time.

### `manifest.json` schema

```json
{
  "schema": "roamcore.labs/bundle",
  "schema_version": 1,
  "created_at": "2026-07-29T21:12:14Z",
  "creator": "roamcore.labs_export_setup",
  "dashboard_file": "/config/lovelace/roamcore-dashboard.yaml",
  "packages": [
    "roamcore_labs.yaml",
    "roamcore_setup_wizard_labs.yaml"
  ]
}
```

| Field | Type | Description |
| --- | --- | --- |
| `schema` | string | Always `"roamcore.labs/bundle"`. Importers use this to gate on the schema family. |
| `schema_version` | int | Schema version. Bumped on breaking changes. |
| `created_at` | string | UTC ISO 8601 timestamp of the bundle creation. |
| `creator` | string | Always `"roamcore.labs_export_setup"`. Future variants may add other creators (e.g. `roamcore.labs_export_setup_partial`). |
| `dashboard_file` | string | Absolute path to the dashboard YAML that was included in the bundle. |
| `packages` | list of strings | The list of packages the operator opted in to, relative to the packages dir. |

Importer behaviour:

1. Reads `manifest.json` and validates `schema == "roamcore.labs/bundle"` plus `schema_version == 1` (or a known-compatible version).
2. Extracts every file under the staging dir, refusing any path that would escape the staging root (path-traversal guard).
3. Updates `input_text.rc_labs_pending_import` with the bundle path so the wizard can render the pending-import pill.
4. Bumps `sensor.rc_labs_import_count` in the state file.

## Privacy

- Local-only stdlib (`tarfile`, `json`, `pathlib`). No HTTP, no DNS, no third-party imports.
- No signature / verification. The owner is in control of "is this bundle trustworthy?".
- Privacy invariant enforced in CI by `scripts/checks/labs-smoke.sh`.

## RoamCore Labs
- Built-in: `docs/setup/labs.md`
- Contract package: `homeassistant/packages/roamcore_labs.yaml`
- Wizard snippet: `homeassistant/packages/roamcore_setup_wizard_labs.yaml`
- Services: `roamcore.labs_export_setup`, `roamcore.labs_import_setup` (registered in `homeassistant/custom_components/roamcore/services.yaml`)
- CLI mirrors: `homeassistant/tools/labs/export_setup.py`, `homeassistant/tools/labs/import_setup.py` (stdlib-only)
- Smoke check: `scripts/checks/labs-smoke.sh` (privacy invariant + N assertions)

## Links
- (Add videos/quickstart)
