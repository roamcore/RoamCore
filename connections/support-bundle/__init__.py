"""RoamCore connection: Support bundle — vendor-neutral
diagnostic snapshot exporter for RoamCore-installed HA
instances — tier-a connection.

This is a TIER-A connection that wraps the existing
RoamCore-owned support-bundle exporter at
`homeassistant/custom_components/roamcore/support_bundle.py`
(286 LOC, real `async def export_support_bundle(hass, *,
include_zip=True) -> dict` + 8 private helpers: `_ts`,
`_iso_now`, `_ensure_dir`, `_read_text`, `_copy_file`,
`_write_json`, `_zip_dir`, `_snapshot_entity`) + the
service registration in the matching
`homeassistant/custom_components/roamcore/...`
services.yaml file (registers the `export_support_bundle`
service with optional `zip: true`) + the handler wiring
in `homeassistant/custom_components/roamcore/__init__.py`
(registers the `_svc_export_support_bundle` handler via
`async_register_service`) + the operator howto at
`docs/howto/support-bundle.md` (44 lines, the canonical
operator-walk through the service-call flow + the 3
sections of bundle contents + the 6 files included + the
privacy guidance).

The exporter walks the canonical 3 sections of bundle
contents: installer/provisioning state (copies
`install-info.txt` + `manifest.txt` + `provisioned.marker`
from the HA installer at `/config/.roamcore/`),
OpenClaw snapshots (synthesizes `openclaw-summary.json`
from `rc_*` contract entities + `openclaw-timeseries-
catalog.json` from the canonical TIMESERIES_CATALOG),
setup-wizard states (snapshots `input_select.rc_setup_
stage` + `sensor.rc_setup_progress` + 3 binary_sensor
flags into `setup-wizard-states.json`). Writes the
bundle directory at `/config/.roamcore/support/<timestamp>/`
+ (when `include_zip=True`) the matching zip at
`/config/.roamcore/support/<timestamp>.zip`. Returns
`{"dir": <dir>, "zip": <zip_or_none>}` so the §8.4
export-success bookkeeping automation can populate the
3 `input_text` last_export_path + last_export_at +
last_export_zip contract tiles.

This file is just the connection manifest marker
(`DOMAIN = "support_bundle"`) used by the audit script
to detect the connection. The actual exporter lives in
the existing RoamCore custom component at
`homeassistant/custom_components/roamcore/support_bundle.py`
+ the matching `homeassistant/custom_components/roamcore/...`
services.yaml file + the handler wiring in
`homeassistant/custom_components/roamcore/__init__.py`.

The connection's recipe + contract tiles + FIVE §8
MANDATORY automations are documented in
`connections/support-bundle/docs/recipe.md`.

The operator-wired export flow is the canonical
service-call walkthrough documented in
`docs/howto/support-bundle.md` (the operator opens
Settings → Developer Tools → Services → selects
`roamcore.export_support_bundle` → optionally passes
`zip: true` in the service data → clicks Call service
→ reads the persistent notification with the output
directory). The `input_button.rc_support_bundle_export` +
`input_button.rc_support_bundle_export_no_zip` dashboard
tiles are the dashboard-side companion to the service-
call flow — they fire the
`roamcore.export_support_bundle` service via the HA
core `input_button:` integration, no shell wrapper
required.

The bundle is best-effort and intentionally avoids
obvious secrets (the canonical implementation does
best-effort filtering of `secrets.yaml`); the
`binary_sensor.rc_support_bundle_secrets_safe` chip is
the operator-facing privacy guard — if false, the
operator investigates which file leaked (the §8.5
privacy audit scans the output directory for filenames
matching `secrets.yaml` / `secrets*.yaml` / `*.env` /
`*token*` case-insensitive).

The umbrella publishes the resulting data via the
existing RoamCore-owned support-bundle exporter at
`homeassistant/custom_components/roamcore/support_bundle.py`
+ the matching `homeassistant/custom_components/roamcore/...`
services.yaml file + the handler wiring in
`homeassistant/custom_components/roamcore/__init__.py`,
then publishes the RoamCore support-bundle contract
tiles on top (the 8 contract entities documented in the
manifest's `dashboard.tiles` list — 2 `input_button`
helpers (export + export_no_zip) + 3 `input_text`
helpers (last_export_path + last_export_at +
last_export_zip) + 1 `sensor` derivation (status) + 1
`input_text` helper (last_error) + 1 `binary_sensor`
derivation (secrets_safe) = 8 contract entities).

The audit + boundary CI can detect a `support-bundle/`
folder that claims to be a connection via the `DOMAIN`
constant exported here. The wizard reads the manifest +
recipe at runtime.

The real per-operator support-bundle affordance path is:

    Operator-side choice of the FOUR-step flow (Export
        -> Locate -> Inspect -> Share)
        -> existing exporter
           (`homeassistant/custom_components/roamcore/
            support_bundle.py` — 286 LOC, real
            `async def export_support_bundle(hass, *,
            include_zip=True) -> dict` + 8 private
            helpers)
        -> existing service registration (the
           matching `homeassistant/custom_components/
           roamcore/...` services.yaml file registers
           `export_support_bundle` with optional
           `zip: true`)
        -> existing handler wiring (the
           `homeassistant/custom_components/roamcore/
           __init__.py` registers the
           `_svc_export_support_bundle` handler)
        -> existing operator howto (`docs/howto/
           support-bundle.md`, 44 lines, the canonical
           operator-walk through the service-call flow
           + the 3 sections of bundle contents + the 6
           files included + the privacy guidance)
        -> the RoamCore contract layer (the 8
           `rc_support_bundle_*` tiles documented in
           the manifest's `dashboard.tiles` list —
           `input_button` export + `input_button`
           export_no_zip + 3 `input_text`
           last_export_path + last_export_at +
           last_export_zip + 1 `sensor` status + 1
           `input_text` last_error + 1 `binary_sensor`
           secrets_safe = 8 contract entities)
        -> dashboard tiles + operator queries
            ("export a bundle now",
             "export a bundle without zipping",
             "where is the last bundle?",
             "when was the last export?",
             "where is the last zip?",
             "what's the export status?",
             "what was the last error?",
             "is the bundle secrets-safe?")

    Safety interlocks (the recipe is the contract layer;
    the automation wrappers are documented in §8):
        -> The RoamCore export-button guard is the §8.1
           automation that fires when
           `input_button.rc_support_bundle_export` is
           pressed. The button press marks `sensor.
           rc_support_bundle_status = Export-Running`
           and clears any stale `input_text.
           rc_support_bundle_last_error`. The actual
           export work happens via the canonical
           `roamcore.export_support_bundle` service
           (with `zip: true` passed via the service
           data).
        -> The RoamCore export-no-zip guard is the §8.2
           automation that fires when
           `input_button.rc_support_bundle_export_no_zip`
           is pressed. The button press marks `sensor.
           rc_support_bundle_status = Export-Running`,
           clears stale errors, and passes `zip: false`
           to the service call. Useful when `/config/`
           is space-constrained.
        -> The RoamCore export-failure capture guard is
           the §8.3 automation that fires when the
           service call returns `status != 'ok'` OR
           raises an exception. The automation captures
           the error into `input_text.rc_support_bundle_
           last_error` and marks `sensor.rc_support_
           bundle_status = Failed`.
        -> The RoamCore export-success bookkeeping guard
           is the §8.4 automation that fires when the
           service call returns `status == 'ok'`. The
           automation populates `input_text.rc_support_
           bundle_last_export_path` + `input_text.
           rc_support_bundle_last_export_at` +
           `input_text.rc_support_bundle_last_export_zip`
           (the last one is empty when `zip: false`)
           from the service response payload.
        -> The RoamCore privacy audit is the §8.5
           automation that fires when the bundle is
           written. The automation scans the output
           directory for filenames matching
           `secrets.yaml` / `secrets*.yaml` / `*.env` /
           `*token*` (case-insensitive). If any match,
           the automation marks `binary_sensor.
           rc_support_bundle_secrets_safe = false` and
           surfaces a "Bundle may contain secrets —
           review before sharing" notification. The
           canonical implementation marks these
           filenames as forbidden but does NOT delete
           them (the operator decides).

    Cross-references:
        -> The RoamCore-owned support-bundle exporter
           at `homeassistant/custom_components/roamcore/
           support_bundle.py` is the canonical umbrella
           (writes the bundle directory + optional zip;
           reads from existing `rc_*` contract entities
           + the canonical `/config/.roamcore/`
           installer state).
        -> The matching `homeassistant/custom_components/
           roamcore/...` services.yaml file is the
           canonical service registration surface
           (registers `export_support_bundle` with
           optional `zip: true`).
        -> The `homeassistant/custom_components/roamcore/
           __init__.py` is the canonical handler wiring
           (registers `_svc_export_support_bundle` via
           `async_register_service`).
        -> The operator howto at `docs/howto/support-
           bundle.md` (44 lines) is the canonical
           operator-walk through the service-call flow
           + the 3 sections of bundle contents + the 6
           files included + the privacy guidance.
        -> The openclaw-api Wave 3 #64 connection cross-
           references the exporter because the bundle
           includes `openclaw-summary.json` +
           `openclaw-timeseries-catalog.json` from
           the OpenClaw JSON API custom component.
        -> The ha-installer Wave 3 #71 connection cross-
           references the exporter because the bundle
           includes `install-info.txt` + `manifest.txt`
           + `provisioned.marker` from the HA installer
           (the files written by `homeassistant/
           install.sh` to `/config/.roamcore/`).
        -> The trip-local Wave 3 #68 connection cross-
           references the exporter because the bundle
           may include the `rc_trip_local_*` entity
           snapshots in the `openclaw-summary.json`
           payload (the trip-local package's sensors +
           binary sensors).

See docs/recipe.md for the full howto (the existing
exporter + service registration + the FOUR-step operator
flow + the 8 `rc_support_bundle_*` contract tiles + the
FIVE §8 MANDATORY automations + the 6 §9 troubleshooting
entries + privacy + tier-a promotion outline).
"""

DOMAIN = "support_bundle"