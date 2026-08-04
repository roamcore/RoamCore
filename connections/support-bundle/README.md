# connections/support-bundle/

> **Tier-a recipe connection** that wraps the existing
> RoamCore-owned support-bundle exporter at
> `homeassistant/custom_components/roamcore/support_bundle.py`
> as a connection-style manifest so the audit pipeline
> can find it. This slice DOES NOT replace any of the
> existing exporter code; it ADDS the recipe layer
> that defines the canonical 8 `rc_support_bundle_*`
> contract tiles + the FIVE §8 MANDATORY automations.

---

## What this is

A tier-a connection wrapping the canonical diagnostic
snapshot exporter in the existing RoamCore custom
component. The exporter is exposed as the
`roamcore.export_support_bundle` service (registered
in the matching
`homeassistant/custom_components/roamcore/...`
services.yaml file + wired by
`homeassistant/custom_components/roamcore/__init__.py`).
The connection ADDS the dashboard-side companion: the 8
`rc_support_bundle_*` contract tiles + the FIVE §8
MANDATORY automations that wire the canonical
service-call flow into the operator-facing dashboard +
the privacy audit.

**One-paragraph TL;DR for the operator:**
Tap `input_button.rc_support_bundle_export` from the
dashboard OR call `roamcore.export_support_bundle`
from Settings → Developer Tools → Services with
optional `zip: true` → the exporter writes
`/config/.roamcore/support/<timestamp>/` with the 6
canonical bundle files + an optional zip →
`binary_sensor.rc_support_bundle_secrets_safe` confirms
the privacy guard fired (true = no obvious secrets
detected; false = investigate the leak) → copy the
bundle off-host and post it in the bug tracker.

---

## Folder layout

```
connections/support-bundle/
├── connection.yml                              # the tier-a manifest (the source of truth)
├── __init__.py                                 # DOMAIN = "support_bundle" marker
├── README.md                                   # this file
├── docs/
│   └── recipe.md                               # the canonical operator-facing howto (~990 lines, 12 §sections)
└── tests/
    └── test_connection_yml.py                  # 8 manifest-honesty tests
```

---

## Operator flow (4 steps)

1. **Export** — operator taps
   `input_button.rc_support_bundle_export` (or calls
   the service directly from Settings → Developer Tools
   → Services → `roamcore.export_support_bundle` with
   `zip: true`). The exporter walks the canonical 3
   sections (installer/provisioning state, OpenClaw
   snapshots, setup-wizard states), writes
   `/config/.roamcore/support/<timestamp>/<file>` for
   each, and (when `zip: true`) creates a zip.
   `sensor.rc_support_bundle_status` flips from
   `Idle` → `Export-Running` → `Exported`.
2. **Locate** — operator reads the persistent
   notification (or
   `input_text.rc_support_bundle_last_export_path`) to
   get the bundle directory path. The optional zip path
   is in `input_text.rc_support_bundle_last_export_zip`.
3. **Inspect** — operator reviews the contents before
   sharing. The
   `binary_sensor.rc_support_bundle_secrets_safe` chip
   confirms the privacy guard fired (true = no obvious
   secrets detected; false = investigate). The §8.5
   privacy audit scans the output directory for
   filenames matching `secrets.yaml` / `secrets*.yaml` /
   `*.env` / `*token*` (case-insensitive).
4. **Share** — operator copies the bundle (or zip) off
   the HA host (scp / sneakernet / Tailscale share)
   and posts it in the bug tracker or support thread.

---

## Contract tiles (8)

The dashboard exposes 8 vendor-neutral
`rc_support_bundle_*` tiles (no Victron / SeeLevel /
Starlink / Peplink / MQTT / HTTP / ESPHome / phone /
Bluetooth / Wi-Fi / BLE / LTE / cellular / input_text
/ input_button / input_boolean / curl / wget vendor /
hardware / protocol / integration names leak into the
tile ids):

| Tile                                            | Domain                 | Purpose                                                                  |
| ----------------------------------------------- | ---------------------- | ------------------------------------------------------------------------ |
| `input_button.rc_support_bundle_export`         | one-tap export button  | Fires the `roamcore.export_support_bundle` service with `zip: true`      |
| `input_button.rc_support_bundle_export_no_zip`  | one-tap no-zip button  | Fires the same service with `zip: false` (space-constrained `/config/`)  |
| `input_text.rc_support_bundle_last_export_path` | last export dir        | The `/config/.roamcore/support/<timestamp>/` path (until first run: empty) |
| `input_text.rc_support_bundle_last_export_at`   | last export timestamp  | ISO 8601 timestamp of the last successful export                         |
| `input_text.rc_support_bundle_last_export_zip`  | last export zip        | The `/config/.roamcore/support/<timestamp>.zip` path (empty when no zip)  |
| `sensor.rc_support_bundle_status`               | status sensor          | Idle / Export-Running / Exported / Failed / No-Prior-Export              |
| `input_text.rc_support_bundle_last_error`       | last error             | The last export error message, if any                                    |
| `binary_sensor.rc_support_bundle_secrets_safe`  | privacy chip           | true = no secrets detected; false = investigate the leak                 |

---

## §8 Automations (5 mandatory)

| ID                                              | Title                       | Purpose                                                                  |
| ----------------------------------------------- | --------------------------- | ------------------------------------------------------------------------ |
| `rc_support_bundle_export_button_guard`         | Export-button guard         | Marks status=Export-Running + clears stale errors on button press        |
| `rc_support_bundle_export_no_zip_guard`         | Export-no-zip guard         | Marks status=Export-Running + clears stale errors + passes zip: false    |
| `rc_support_bundle_export_failure_capture`      | Export-failure capture      | Captures error into `last_error` + marks status=Failed on service failure |
| `rc_support_bundle_export_success_bookkeeping`  | Export-success bookkeeping  | Populates last_export_path + last_export_at + last_export_zip on success |
| `rc_support_bundle_privacy_audit`               | Privacy audit               | Scans output dir for `secrets.yaml` / `*.env` / `*token*` patterns       |

See [`docs/recipe.md`](./docs/recipe.md) §8 for the
full `automation:` YAML configurations.

---

## Supersession

The legacy catalog doc at
[`docs/catalog/homelab/support-bundle.md`](../../docs/catalog/homelab/support-bundle.md)
now carries the **SUPERSEDED** banner pointing at this
connection folder. The legacy tier-a "RoamCore native"
claim in that stub is honest-upstream-truth: RoamCore
ships + maintains + audits the canonical exporter code
at `homeassistant/custom_components/roamcore/support_bundle.py`
+ the service registration in the matching
`homeassistant/custom_components/roamcore/...`
services.yaml file + the handler wiring in
`homeassistant/custom_components/roamcore/__init__.py`
+ the operator howto at `docs/howto/support-bundle.md`.

---

## Cross-references

- **Exports the bundle from:**
  [`homeassistant/custom_components/roamcore/support_bundle.py`](../../homeassistant/custom_components/roamcore/support_bundle.py)
  (286 LOC, canonical exporter).
- **Service registered in:**
  `homeassistant/custom_components/roamcore/services.yaml`
  (registers `export_support_bundle` with optional
  `zip: true`).
- **Handler wired in:**
  `homeassistant/custom_components/roamcore/__init__.py`
  (registers `_svc_export_support_bundle` via
  `async_register_service`).
- **Operator howto:**
  [`docs/howto/support-bundle.md`](../../docs/howto/support-bundle.md)
  (44 lines, canonical operator-walk through the
  service-call flow).
- **OpenClaw JSON API:** [`../openclaw-api/`](../openclaw-api/) —
  the bundle includes `openclaw-summary.json` +
  `openclaw-timeseries-catalog.json` from the OpenClaw
  JSON API custom component.
- **HA installer:** [`../ha-installer/`](../ha-installer/) —
  the bundle includes `install-info.txt` + `manifest.txt`
  + `provisioned.marker` from the HA installer.
- **Trip Local:** [`../trip-local-tier-a/`](../trip-local-tier-a/) —
  the bundle may include `rc_trip_local_*` entity
  snapshots in the `openclaw-summary.json` payload.

---

## Verification

- `python3 -m pytest connections/support-bundle/tests/ -v` → **8/8 PASS**
- `bash scripts/check.sh --core-only` → **✅ GREEN** (with the support-bundle smoke wired in immediately after the ha-installer entry).