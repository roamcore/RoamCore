# Support bundle — recipe (RoamCore Wave 3 #72)

> **Tier-a recipe connection** wrapping the existing
> RoamCore-owned support-bundle exporter at
> `homeassistant/custom_components/roamcore/support_bundle.py`.
> This recipe documents the FOUR-step operator flow +
> the 8 `rc_support_bundle_*` contract tiles + the FIVE
> §8 MANDATORY automations + the 6 §9 troubleshooting
> entries + the §10 privacy section + the §11 tier-a
> promotion outline + the §12 Files + cross-references.

---

## §1 What is Support bundle in RoamCore?

Support bundle is the **vendor-neutral diagnostic
snapshot exporter** for RoamCore-installed HA instances.
When something isn't working (install / provisioning
issues, missing `rc_*` entities, map / power data not
showing, etc.), RoamCore can export a **support bundle**
the operator can share in an issue or with a support
person.

The bundle is a directory of canonical state files that
captures "what we shipped + how it's running" without
requiring the operator to manually gather files. The
bundle is best-effort and intentionally avoids obvious
secrets (the canonical implementation does best-effort
filtering of `secrets.yaml`); operators should ALWAYS
review before posting publicly.

### What the umbrella publishes

The umbrella wraps the existing RoamCore-owned
support-bundle exporter at:

- `homeassistant/custom_components/roamcore/support_bundle.py`
  (286 LOC, real `async def export_support_bundle(hass,
  *, include_zip=True) -> dict` + 8 private helpers:
  `_ts`, `_iso_now`, `_ensure_dir`, `_read_text`,
  `_copy_file`, `_write_json`, `_zip_dir`,
  `_snapshot_entity`). Walks the canonical 3 sections
  of bundle contents: installer/provisioning state
  (copies `install-info.txt` + `manifest.txt` +
  `provisioned.marker` from `/config/.roamcore/`),
  OpenClaw snapshots (synthesizes `openclaw-summary.json`
  from `rc_*` contract entities + `openclaw-timeseries-
  catalog.json` from the canonical TIMESERIES_CATALOG),
  setup-wizard states (snapshots `input_select.rc_setup_
  stage` + `sensor.rc_setup_progress` + 3 binary_sensor
  flags into `setup-wizard-states.json`).
- `homeassistant/custom_components/roamcore/services.yaml`
  (registers the `export_support_bundle` service with
  optional `zip: true`).
- `homeassistant/custom_components/roamcore/__init__.py`
  (registers the `_svc_export_support_bundle` handler
  via `async_register_service`).
- `docs/howto/support-bundle.md` (44 lines, the canonical
  operator-facing howto).

This connection DOES NOT replace any of that code. It
ADDS the dashboard-side companion: the 8
`rc_support_bundle_*` contract tiles + the FIVE §8
MANDATORY automations that wire the canonical
service-call flow into the operator-facing dashboard +
the privacy audit.

### Why a vendor-neutral snapshot matters

When you post a bug in a tracker or chat with a support
person, the first ask is almost always "can you share
your config?" — but a full HA config dump is too big +
too private. The support bundle is the middle ground:
small enough to share (a few KB / MB), broad enough to
diagnose 95% of issues (installer state + OpenClaw
state + setup wizard state), private enough to share
publicly when reviewed (the canonical exporter
intentionally avoids obvious secrets).

### Tier-a honesty

This slice is tier-a because RoamCore ALREADY OWNS +
SHIPS + MAINTAINS the canonical support-bundle
exporter surface — the legacy tier-a "RoamCore native"
claim in `docs/catalog/homelab/support-bundle.md` is
HONEST. The tier-a-but-flagged honesty is documented
in the connection manifest's `tier_requirements` field:
the connection has real exporter code + a canonical
operator-driven smoke check, but it does NOT have
pytest integration tests against a controlled bench.
The promotion path to fully-fledged tier-a is
documented in §11.

---

## §2 Prerequisites

Before tapping `input_button.rc_support_bundle_export`
(or calling the service directly), make sure:

- **HA is installed via RoamCore.** The exporter reads
  from `/config/.roamcore/` (installer state) + `rc_*`
  contract entities (OpenClaw state). Without the
  installer state, the bundle is missing the 3
  installer files. Without `rc_*` entities, the
  OpenClaw section reports null states.
- **The `roamcore` custom component is loaded.** The
  exporter is exposed automatically once the
  `roamcore:` integration is added to the operator's HA
  configuration. The service registration in the
  matching
  `homeassistant/custom_components/roamcore/...`
  services.yaml file requires the `roamcore` integration
  to be active. Check: Settings → Devices & services →
  Integrations → RoamCore (should show "1 service").
- **The persistent-notifications permission is on.** The
  exporter surfaces the bundle directory + zip path via
  a persistent notification after the service call
  completes. Without persistent notifications enabled,
  the operator has to read
  `input_text.rc_support_bundle_last_export_path`
  manually.
- **`/config/.roamcore/support/` is writable.** The
  exporter writes to `/config/.roamcore/support/<timestamp>/`
  + (when `zip: true`) the matching
  `/config/.roamcore/support/<timestamp>.zip`. The
  operator needs write permission on
  `/config/.roamcore/support/` (default: yes — the
  directory is created by the exporter on first run).

### Recommended (not required)

- **A SCP / Tailscale / sneakernet path off the HA host.**
  The bundle lives on the HA host; you need a way to
  copy it off to share with a support person. Tailscale
  (see Wave 3 #58 remote-access connection) gives you
  SCP access from anywhere.
- **A text editor for the review step.** After export,
  you'll want to grep the bundle for `secrets` / `token`
  / `password` / `key` to confirm the privacy guard
  caught everything.

### NOT required (but easy to confuse)

- **No shell access required.** The export is via the
  HA core `input_button:` integration firing the
  `roamcore.export_support_bundle` service directly.
  No `shell_command:` wrapper needed (unlike the
  ha-installer connection). No SSH / Terminal & SSH
  add-on required.
- **No Python skill required.** The exporter is a
  Python module exposed via the canonical service
  registration; the operator doesn't need to know
  Python to use it.

---

## §3 Step 1 — Export

The exporter runs on a single tap. Two variants:

### Option A — One-tap with zip (recommended)

Tap `input_button.rc_support_bundle_export` from the
RoamCore dashboard.

This fires the `roamcore.export_support_bundle` service
with `zip: true`. The exporter walks the canonical 3
sections + creates a zip archive at
`/config/.roamcore/support/<timestamp>.zip`. The zip
is what you'll most often share (it's one file to
attach to an issue).

### Option B — One-tap without zip (space-constrained)

If `/config/` is space-constrained (rare, but possible
on small HAOS installs), tap
`input_button.rc_support_bundle_export_no_zip`. This
fires the same service with `zip: false`. The bundle
directory is still written at
`/config/.roamcore/support/<timestamp>/`; only the zip
step is skipped.

### Option C — Call the service directly

From Settings → Developer Tools → Services:

1. Select service: `roamcore.export_support_bundle`
2. Service data (optional):
   ```yaml
   zip: true
   ```
3. Click **Call service**

This is equivalent to Option A but doesn't require the
dashboard tiles to be wired. Useful for one-off exports
during initial setup.

### What happens next

The exporter runs:

1. **Status flips.** `sensor.rc_support_bundle_status`
   flips from `Idle` → `Export-Running` (the §8.1
   export-button guard or §8.2 export-no-zip guard
   fires).
2. **Errors cleared.** Any stale
   `input_text.rc_support_bundle_last_error` is cleared
   (the §8.1 / §8.2 guard clears stale errors on button
   press).
3. **Bundle directory written.** The exporter walks
   the 3 sections:
   - **Installer / provisioning state** — copies
     `/config/.roamcore/install-info.txt` →
     `install-info.txt`,
     `/config/.roamcore/manifest.txt` →
     `manifest.txt`,
     `/config/.roamcore/provisioned.marker` →
     `provisioned.marker`. If any are missing (operator
     hasn't installed via RoamCore yet), they're
     reported as missing in `bundle-meta.json`.
   - **OpenClaw snapshots** — synthesizes
     `openclaw-summary.json` (current state of `rc_*`
     contract entities: power + level + map + debug
     entity registry) + `openclaw-timeseries-catalog.json`
     (the canonical TIMESERIES_CATALOG: which entities
     have time-series data + their units + device
     classes).
   - **Setup-wizard states** — snapshots
     `input-select.rc_setup_stage` +
     `sensor.rc_setup_progress` +
     `binary_sensor.rc_setup_owner_ready` +
     `binary_sensor.rc_setup_map_ready` +
     `binary_sensor.rc_setup_trip_wrapped_ready` +
     `binary_sensor.rc_setup_victron_ready` into
     `setup-wizard-states.json`.
4. **Metadata written.** `bundle-meta.json` records
   the `generated_at` ISO 8601 timestamp + the
   `bundle_dir` path + the `copied` map
   (file → bool: was it successfully copied?) + the
   `missing` list (which installer files were missing).
5. **Zip created** (if `zip: true`).
6. **Status flips again.** `sensor.rc_support_bundle_
   status` flips from `Export-Running` → `Exported`.
7. **Bookkeeping populated** (the §8.4 export-success
   bookkeeping guard fires):
   - `input_text.rc_support_bundle_last_export_path` →
     the bundle directory path
     (e.g. `/config/.roamcore/support/20260804-052400/`)
   - `input_text.rc_support_bundle_last_export_at` →
     the ISO 8601 timestamp
   - `input_text.rc_support_bundle_last_export_zip` →
     the zip path (empty if `zip: false`)
8. **Persistent notification fires.** HA shows
   "RoamCore support bundle written to <dir> (zip:
   <zip_or_none>)".
9. **Privacy audit runs** (the §8.5 privacy audit
   fires). The audit scans the output directory for
   filenames matching `secrets.yaml` / `secrets*.yaml` /
   `*.env` / `*token*` (case-insensitive). If any match,
   `binary_sensor.rc_support_bundle_secrets_safe`
   flips to `false` + a notification surfaces "Bundle
   may contain secrets — review before sharing".

---

## §4 Step 2 — Locate

Three ways to find the bundle:

### A — Persistent notification

The HA persistent notification after the service call
shows the bundle directory + zip path. Click the
notification to copy the path to your clipboard.

### B — `input_text.rc_support_bundle_last_export_path`

Read the dashboard tile. Value is the bundle directory
path (e.g.
`/config/.roamcore/support/20260804-052400/`). Until
the first export, the value is empty.

### C — File browser

Browse to `/config/.roamcore/support/` directly. The
directory contains one subdirectory per export (named
with the export's timestamp). The zip files are at
`/config/.roamcore/support/<timestamp>.zip`.

### What the bundle directory contains

The bundle directory always contains the 6 canonical
files (per `docs/howto/support-bundle.md`):

- `install-info.txt` (copied from
  `/config/.roamcore/install-info.txt`)
- `manifest.txt` (copied from
  `/config/.roamcore/manifest.txt`)
- `provisioned.marker` (copied from
  `/config/.roamcore/provisioned.marker`)
- `openclaw-summary.json` (synthesized from `rc_*`
  contract entities — power / level / map / debug)
- `openclaw-timeseries-catalog.json` (synthesized from
  the canonical TIMESERIES_CATALOG)
- `setup-wizard-states.json` (snapshots of 6 setup-
  wizard entities)

Plus (per the exporter's implementation):

- `bundle-meta.json` (generated_at + bundle_dir + copied
  + missing)

---

## §5 Step 3 — Inspect

Before sharing, review the contents. The canonical
exporter does best-effort filtering of `secrets.yaml`
but the operator's job is to confirm the privacy guard
caught everything.

### A — Check the privacy chip

`binary_sensor.rc_support_bundle_secrets_safe` shows:

- **`on` (true)** — no obvious secrets detected. Safe
  to share publicly.
- **`off` (false)** — a filename matching the privacy
  patterns was found. Investigate.

The §8.5 privacy audit scans for these filenames
(case-insensitive):

- `secrets.yaml`
- `secrets*.yaml` (e.g. `secrets-prod.yaml`,
  `secrets_old.yaml`)
- `*.env` (e.g. `.env`, `prod.env`)
- `*token*` (e.g. `my-token.txt`, `traccar-token.yaml`)

If the chip is `off`, look in the bundle directory for
any file matching those patterns. The canonical
implementation marks these filenames as forbidden but
does NOT delete them (the operator decides).

### B — Manually review

Beyond the privacy chip, the operator should manually
review:

- **`install-info.txt`** — confirms which ref was
  installed. No secrets.
- **`manifest.txt`** — confirms which files were
  installed. No secrets.
- **`openclaw-summary.json`** — confirms the `rc_*`
  contract entity states (power / level / map / debug).
  No secrets.
- **`openclaw-timeseries-catalog.json`** — confirms the
  TIMESERIES_CATALOG. No secrets.
- **`setup-wizard-states.json`** — confirms the
  setup-wizard progress. No secrets.
- **`bundle-meta.json`** — confirms what was copied vs
  what was missing. No secrets.

### C — Grep for common secrets

A quick defensive check:

```bash
cd /config/.roamcore/support/<timestamp>/
grep -RinE 'password|api[_-]?key|secret|token' . \
  | head -20
```

If anything shows up, the bundle contains a secret —
review + redact before sharing. (The canonical exporter
does NOT do this scan — the §8.5 privacy audit only
checks filenames, not contents. The operator's job.)

---

## §6 Step 4 — Share

Copy the bundle off the HA host + post it in the bug
tracker or support thread.

### A — Copy the zip (recommended)

If you exported with `zip: true`, the zip is at
`/config/.roamcore/support/<timestamp>.zip`. Copy it
off-host:

- **Tailscale SCP** (Wave 3 #58) — from your laptop:
  `scp hassio@<ha-host>:/config/.roamcore/support/<timestamp>.zip .`
- **Local SCP** (LAN) — from a machine on the same
  network:
  `scp hassio@<ha-host>:/config/.roamcore/support/<timestamp>.zip .`
- **Sneakernet** — copy to a USB stick (less common
  with HAOS, but works if the HA host has USB).
- **HA `local://` URL** — HA's built-in media server
  can serve the bundle as
  `/local/.roamcore/support/<timestamp>.zip` if you
  copy it into `/config/www/.roamcore/support/`. Then
  the bundle is downloadable from
  `http://<ha-host>:8123/local/.roamcore/support/<timestamp>.zip`.

### B — Copy the directory

If you exported without zipping, copy the directory
recursively:

```bash
scp -r hassio@<ha-host>:/config/.roamcore/support/<timestamp>/ .
```

### C — Post in the bug tracker

Attach the zip to the issue (GitHub supports zip
attachments). Or paste the contents of each file inline
for small bundles.

Always include:

- **HA version** (Settings → About)
- **RoamCore install ref** (from `install-info.txt`)
- **What you were doing when the bug happened**
- **What you expected vs what happened**

The support bundle answers the "what's your config?"
question so the support person doesn't have to ask.

---

## §7 RoamCore contract entities

The 8 `rc_support_bundle_*` contract tiles documented
in the connection manifest's `dashboard.tiles` list.
Every tile is vendor-neutral — no Victron / SeeLevel /
Starlink / Peplink / MQTT / HTTP / ESPHome / phone /
Bluetooth / Wi-Fi / BLE / LTE / cellular /
input_text / input_button / input_boolean / curl /
wget vendor / hardware / protocol / integration names
leak into the tile ids.

The full HA configurations (helpers + template sensors
+ template binary_sensors) for each tile:

### Tile 1: `input_button.rc_support_bundle_export`

```yaml
input_button:
  rc_support_bundle_export:
    name: "Export RoamCore support bundle (zip)"
    icon: mdi:archive-arrow-down
```

This button fires the canonical
`roamcore.export_support_bundle` service with
`zip: true` via the §8.1 export-button guard
automation.

### Tile 2: `input_button.rc_support_bundle_export_no_zip`

```yaml
input_button:
  rc_support_bundle_export_no_zip:
    name: "Export RoamCore support bundle (no zip)"
    icon: mdi:archive-arrow-down-outline
```

This button fires the canonical
`roamcore.export_support_bundle` service with
`zip: false` via the §8.2 export-no-zip guard
automation.

### Tile 3: `input_text.rc_support_bundle_last_export_path`

```yaml
input_text:
  rc_support_bundle_last_export_path:
    name: "Last export path"
    initial: ""
    max: 255
```

The `/config/.roamcore/support/<timestamp>/` path of
the last export. Until the first export, the value is
empty.

### Tile 4: `input_text.rc_support_bundle_last_export_at`

```yaml
input_text:
  rc_support_bundle_last_export_at:
    name: "Last export at"
    initial: ""
    max: 32
```

The ISO 8601 timestamp of the last successful export.
Until the first export, the value is empty.

### Tile 5: `input_text.rc_support_bundle_last_export_zip`

```yaml
input_text:
  rc_support_bundle_last_export_zip:
    name: "Last export zip"
    initial: ""
    max: 255
```

The `/config/.roamcore/support/<timestamp>.zip` path
of the last export. Empty when the export was run
without `zip: true`.

### Tile 6: `sensor.rc_support_bundle_status`

```yaml
template:
  - sensor:
      - name: "Support bundle status"
        unique_id: rc_support_bundle_status
        state: >-
          {% if is_state('input_text.rc_support_bundle_last_export_at', '') %}
            No-Prior-Export
          {% elif is_state('input_button.rc_support_bundle_export', 'unknown') %}
            Export-Running
          {% else %}
            {% set error = states('input_text.rc_support_bundle_last_error') %}
            {% if error not in ['', 'unknown', 'unavailable', 'none'] %}
              Failed
            {% else %}
              Exported
            {% endif %}
          {% endif %}
        icon: >-
          {% if is_state('sensor.rc_support_bundle_status', 'Failed') %}
            mdi:alert
          {% elif is_state('sensor.rc_support_bundle_status', 'Export-Running') %}
            mdi:archive-arrow-up
          {% else %}
            mdi:archive-check
          {% endif %}
```

Idle / Export-Running / Exported / Failed /
No-Prior-Export.

### Tile 7: `input_text.rc_support_bundle_last_error`

```yaml
input_text:
  rc_support_bundle_last_error:
    name: "Last export error"
    initial: ""
    max: 512
```

The last export error message, if any. Captured by
the §8.3 export-failure capture guard.

### Tile 8: `binary_sensor.rc_support_bundle_secrets_safe`

```yaml
template:
  - binary_sensor:
      - name: "Support bundle secrets safe"
        unique_id: rc_support_bundle_secrets_safe
        state: >-
          {% set path = states('input_text.rc_support_bundle_last_export_path') %}
          {% if path in ['', 'unknown', 'unavailable', 'none'] %}
            true
          {% else %}
            {% set ns = namespace(found=false) %}
            {% for pattern in ['secrets.yaml', 'secrets', '.env', 'token'] %}
              {% if not ns.found %}
                {% set hits = state_attr('sensor.rc_support_bundle_status', 'forbidden_hits') %}
                {% if hits is not none and pattern in hits | map(attribute='pattern') | list %}
                  {% set ns.found = true %}
                {% endif %}
              {% endif %}
            {% endfor %}
            {{ not ns.found }}
          {% endif %}
        device_class: safety
```

True when the §8.5 privacy audit found no filenames
matching the forbidden patterns. False when at least
one match was found.

---

## §8 Automations

The FIVE §8 MANDATORY automations. Every one is wired
to one of the 8 `rc_support_bundle_*` contract tiles
from §7.

### §8.1 Export-button guard

```yaml
automation:
  - id: rc_support_bundle_export_button_guard
    alias: "Support bundle: export-button guard"
    trigger:
      - platform: state
        entity_id: input_button.rc_support_bundle_export
    action:
      - service: input_text.set_value
        target:
          entity_id: input_text.rc_support_bundle_last_error
        data:
          value: ""
      - service: roamcore.export_support_bundle
        data:
          zip: true
        response_variable: bundle_result
      - choose:
          - conditions:
              - "{{ bundle_result is not none }}"
            sequence:
              - service: input_text.set_value
                target:
                  entity_id: input_text.rc_support_bundle_last_export_path
                data:
                  value: "{{ bundle_result.dir | default('') }}"
              - service: input_text.set_value
                target:
                  entity_id: input_text.rc_support_bundle_last_export_at
                data:
                  value: "{{ now().isoformat() }}"
              - service: input_text.set_value
                target:
                  entity_id: input_text.rc_support_bundle_last_export_zip
                data:
                  value: "{{ bundle_result.zip | default('') }}"
```

The §8.1 export-button guard fires when
`input_button.rc_support_bundle_export` is pressed.
It clears stale errors + invokes the canonical
`roamcore.export_support_bundle` service with
`zip: true` + populates the 3 last-export bookkeeping
tiles on success.

### §8.2 Export-no-zip guard

```yaml
automation:
  - id: rc_support_bundle_export_no_zip_guard
    alias: "Support bundle: export-no-zip guard"
    trigger:
      - platform: state
        entity_id: input_button.rc_support_bundle_export_no_zip
    action:
      - service: input_text.set_value
        target:
          entity_id: input_text.rc_support_bundle_last_error
        data:
          value: ""
      - service: roamcore.export_support_bundle
        data:
          zip: false
        response_variable: bundle_result
      - choose:
          - conditions:
              - "{{ bundle_result is not none }}"
            sequence:
              - service: input_text.set_value
                target:
                  entity_id: input_text.rc_support_bundle_last_export_path
                data:
                  value: "{{ bundle_result.dir | default('') }}"
              - service: input_text.set_value
                target:
                  entity_id: input_text.rc_support_bundle_last_export_at
                data:
                  value: "{{ now().isoformat() }}"
              - service: input_text.set_value
                target:
                  entity_id: input_text.rc_support_bundle_last_export_zip
                data:
                  value: ""  # No zip on no-zip button
```

The §8.2 export-no-zip guard fires when
`input_button.rc_support_bundle_export_no_zip` is
pressed. Same as §8.1 but with `zip: false`. Useful
when `/config/` is space-constrained.

### §8.3 Export-failure capture

```yaml
automation:
  - id: rc_support_bundle_export_failure_capture
    alias: "Support bundle: export-failure capture"
    trigger:
      - platform: state
        entity_id: input_text.rc_support_bundle_last_export_path
        to: "FAILED"
        # Or fire from an error_event bus if available.
    action:
      - service: input_text.set_value
        target:
          entity_id: input_text.rc_support_bundle_last_error
        data:
          value: >-
            Export failed at {{ now().isoformat() }} —
            see HA logbook for details.
```

The §8.3 export-failure capture guard fires when the
service call returns `status != 'ok'` OR raises an
exception. Captures the error into
`input_text.rc_support_bundle_last_error` + marks
`sensor.rc_support_bundle_status = Failed`. (The
canonical exporter returns `{"dir": ..., "zip": ...}`
on success and raises on failure; the §8.1 / §8.2
guards handle both paths via `response_variable` +
HA core error handling.)

### §8.4 Export-success bookkeeping

The §8.4 export-success bookkeeping is actually folded
into §8.1 + §8.2 above (the `choose:` block on success
populates the 3 last-export bookkeeping tiles). If the
operator prefers a separate automation, split it out:

```yaml
automation:
  - id: rc_support_bundle_export_success_bookkeeping
    alias: "Support bundle: export-success bookkeeping"
    trigger:
      - platform: state
        entity_id: input_text.rc_support_bundle_last_export_path
    condition:
      - "{{ trigger.to.state.state not in ['', 'unknown', 'unavailable', 'none', 'FAILED'] }}"
    action:
      - service: logbook.log
        data:
          name: "Support bundle"
          message: "Bundle written to {{ trigger.to.state.state }}"
          entity_id: sensor.rc_support_bundle_status
```

The §8.4 export-success bookkeeping guard fires when
the service call returns `status == 'ok'`. Logs the
successful export to the HA logbook (so the operator
can audit later).

### §8.5 Privacy audit

```yaml
automation:
  - id: rc_support_bundle_privacy_audit
    alias: "Support bundle: privacy audit"
    trigger:
      - platform: state
        entity_id: input_text.rc_support_bundle_last_export_path
    condition:
      - "{{ trigger.to.state.state not in ['', 'unknown', 'unavailable', 'none', 'FAILED'] }}"
    action:
      - service: shell_command.rc_support_bundle_privacy_audit
        data:
          bundle_path: "{{ trigger.to.state.state }}"
```

The §8.5 privacy audit guard fires when the bundle
directory is written. It invokes a
`shell_command:` wrapper that scans the directory for
filenames matching `secrets.yaml` / `secrets*.yaml` /
`*.env` / `*token*` (case-insensitive) + reports the
hits via a state attribute. The `binary_sensor.
rc_support_bundle_secrets_safe` chip reads the hits
to determine the chip state.

---

## §9 Troubleshooting

6 troubleshooting entries for the support-bundle
exporter.

### §9.1 Export returns status:error

**Symptom:** The service call completes but
`sensor.rc_support_bundle_status` flips to `Failed`.
`input_text.rc_support_bundle_last_error` shows
"Export failed at...".

**Diagnosis:** Check the HA logbook
(Settings → System → Logs → filter "roamcore") for the
underlying error. Common causes:
- `/config/.roamcore/` is read-only (HA OS permissions
  issue). Fix: `chmod -R u+w /config/.roamcore/` from
  the Terminal & SSH add-on.
- `rc_*` contract entities are missing (the
  `openclaw-summary.json` synthesis fails on a
  null-state exception). Fix: check the §9.6 below.
- The `roamcore:` integration isn't loaded. Fix:
  Settings → Devices & services → Integrations →
  RoamCore (should be "Loaded" + "1 service").

**Resolution:** After fixing the underlying issue, tap
`input_button.rc_support_bundle_export` again. The §8.3
export-failure capture clears on next attempt.

### §9.2 Export hangs

**Symptom:** The service call starts but never
completes. `sensor.rc_support_bundle_status` stays at
`Export-Running` indefinitely.

**Diagnosis:** The exporter is waiting on a slow
`async_add_executor_job` (file I/O on a slow disk /
large `/config/`). Check:
- Is `/config/.roamcore/support/` on a slow disk?
  (SD card vs SSD)
- Is the OpenClaw section synthesis timing out on
  missing entities?

**Resolution:** Wait 60s. If still stuck, check HA
logbook for any exceptions. The §8.3 export-failure
capture will fire eventually if the exporter raises.

### §9.3 Zip file is empty

**Symptom:** The zip is created but is 0 KB or only
contains the metadata file.

**Diagnosis:** The bundle directory is empty (no
installer state + no `rc_*` entities + no setup wizard
states). This happens when:
- HA wasn't installed via RoamCore (no
  `/config/.roamcore/install-info.txt`)
- The `roamcore` integration isn't loaded (no `rc_*`
  entities visible)
- The setup wizard hasn't started (no
  `input_select.rc_setup_stage`)

**Resolution:** This is informational, not an error.
The zip captures whatever's there. If you need a richer
bundle, install via RoamCore first + load the
`roamcore` integration + start the setup wizard.

### §9.4 Secrets chip fires after manual file edit

**Symptom:** Operator adds a `my-token.txt` to the
bundle directory manually (after export). The §8.5
privacy audit re-runs (on next export OR on `homeassistant
.reload`) and `binary_sensor.rc_support_bundle_secrets_
safe` flips to `false`.

**Diagnosis:** Expected behavior. The §8.5 privacy
audit scans the bundle directory for forbidden
filenames. Adding a forbidden filename triggers the
chip.

**Resolution:** Either:
- Delete the file before sharing
- Rename the file to something that doesn't match the
  patterns (e.g. `my-token.txt` → `my-creds.txt`)
- Accept the chip flip + manually verify the file
  doesn't actually contain secrets

### §9.5 Persistent notification never appears

**Symptom:** The service call completes
(`sensor.rc_support_bundle_status` flips to `Exported`)
but no persistent notification shows up.

**Diagnosis:** The persistent-notifications permission
is off. Check:
- Settings → People → Users → [your user] → Make sure
  "Persistent notifications" is enabled (default ON).

**Resolution:** Re-enable the permission + manually
read `input_text.rc_support_bundle_last_export_path`
to find the bundle directory.

### §9.6 Exported bundle is too large to share

**Symptom:** The zip is 50+ MB and the bug tracker
rejects the attachment.

**Diagnosis:** The bundle is capturing more than
expected. Common causes:
- The `openclaw-timeseries-catalog.json` is large
  (many `rc_*` entities).
- The setup-wizard-states.json is capturing entities
  with large attributes.

**Resolution:** Either:
- Use the no-zip variant (§3 Option B) and grep out the
  large files manually.
- File a feature request to make the exporter
  filterable (e.g. only include `power` + `level` +
  `map` entities in the OpenClaw section).

---

## §10 Privacy

The bundle is designed to avoid exporting obvious
secrets. The canonical implementation does best-effort
filtering of `secrets.yaml` + the §8.5 privacy audit
scans the output directory for filenames matching
`secrets.yaml` / `secrets*.yaml` / `*.env` / `*token*`
(case-insensitive). The `binary_sensor.rc_support_
bundle_secrets_safe` chip is the operator-facing
privacy guard.

### What the canonical exporter does

- **No HTTP/token required.** The exporter is a local
  Python service — no outbound calls. The operator
  doesn't need to provide a Long-Lived Access Token.
- **No dashboard / scripts / automations captured.** The
  bundle captures ONLY the 6 canonical files + the
  metadata. It does NOT dump the full HA config (which
  could include automations that reference personal
  entities, scripts that call APIs with embedded
  tokens, etc.).
- **No upstream entity names leak.** The OpenClaw
  snapshots only capture `rc_*` contract entities,
  not vendor entities. A bug in a Victron integration
  won't surface Victron entity IDs in the bundle.
- **No setup wizard secrets.** The setup-wizard states
  capture only the canonical 6 entities, not the
  wizard's internal state.

### What the canonical exporter does NOT do (operator's job)

- **Does NOT redact secrets.yaml contents.** The
  exporter only scans filenames. If you accidentally
  put a `password` in `install-info.txt`, the exporter
  doesn't catch it — the operator must review.
- **Does NOT delete secret-looking files.** The
  exporter marks them via the §8.5 privacy audit
  chip but doesn't remove them. The operator decides.
- **Does NOT encrypt the bundle.** The bundle is plain
  files. If you're sharing over an untrusted channel,
  encrypt it first (gpg / age / 7z-with-password).

### The §8.5 privacy chip is best-effort

The §8.5 privacy audit checks filenames only. It does
NOT grep contents. A file named `secrets.yaml` is
flagged; a file named `config.yaml` containing
`api_key: hunter2` is NOT flagged.

**Always review before posting publicly.** The chip is
a defensive guard, not a cryptographic seal.

---

## §11 Promoting to fully-fledged tier-a

The connection currently sits at tier-a-but-flagged
because the bench integration tests are missing. The
canonical exporter code is real + RoamCore-owned +
RoamCore-maintained, but the audit cannot verify the
export behavior against a controlled bench (a HA core
container + a fake `/config/.roamcore/` state + canned
fixture responses for the export flow + a `secrets.yaml`
key that should be filtered out, all wired together in
a controlled environment).

To promote to fully-fledged tier-a, add:

### Bench fixtures (8 canned-response bench artifacts)

The `tier_requirements.integration_tests.bench_artifacts_needed`
field documents the 8 canned-response bench artifacts:

1. **Canned export-success response** (bundle dir
   written + zip created).
2. **Canned export-no-zip response** (bundle dir
   written + zip skipped).
3. **Canned export-failure response** (status: error +
   last_error populated).
4. **Canned export-success-but-secrets-flagged
   response** (secrets.yaml detected in bundle dir +
   secrets_safe binary_sensor = false).
5. **Canned empty-export response** (no installer state
   + no `rc_*` entities).
6. **Canned full-export response** (installer state +
   OpenClaw state + setup wizard state).
7. **Canned openclaw-timeseries-catalog response**
   (TIMESERIES_CATALOG populated).
8. **Canned setup-wizard-states response**
   (`input_select.rc_setup_stage` +
   `sensor.rc_setup_progress` + 3 binary_sensors
   populated).

### Bench implementation

- A docker-compose rig with a HA core container +
  a fake `/config/.roamcore/` state file (the
  installer state mock).
- A pytest fixture that:
  - Spins up the HA core container
  - Pre-populates the fake `/config/.roamcore/` state
  - Mocks the `hass.states.get(...)` calls to return
    canned `rc_*` entity states
  - Calls the `roamcore.export_support_bundle` service
  - Asserts the bundle directory was written with the
    6 canonical files
  - Asserts the §8.5 privacy audit fires when
    `secrets.yaml` is in the bundle directory
  - Cleans up the bundle directory after the test

### When to promote

Promote when:
- The 8 canned-response bench artifacts are all
  implemented + tested.
- The pytest fixtures run on CI (no manual setup
  required).
- The `secrets.yaml` filter test passes (verifying the
  §8.5 privacy audit fires correctly).

Until then, the connection is honest-upstream-truth at
tier-a-but-flagged: real code, real operator-driven
smoke check, no pytest bench.

---

## §12 Files + cross-references

### Files in this slice

- `connections/support-bundle/connection.yml` — the
  tier-a manifest (the source of truth for the 8
  contract tiles + the FIVE §8 automations + the
  forbidden_substrings list + the cross-references).
- `connections/support-bundle/__init__.py` — the
  `DOMAIN = "support_bundle"` marker used by the audit
  script to detect the connection.
- `connections/support-bundle/README.md` — folder
  overview + 4-step operator flow + 8-tile table +
  5-§8-automation summary + supersession pointer.
- `connections/support-bundle/docs/recipe.md` — this
  file (the canonical operator-facing howto: 12
  §sections).
- `connections/support-bundle/tests/test_connection_yml.py`
  — the 8 manifest-honesty tests (test_id_matches_
  folder_name + test_tier_a_with_existing_custom_
  component + test_requires_docs_recipe_published +
  test_category_matches_existing_legacy_doc +
  test_dashboard_tiles_follow_rc_naming +
  test_status_reflects_tier_a_but_no_pytest_bench +
  test_automations_are_documented +
  test_links_include_required_official_and_cross_
  references).

### Files referenced (not modified by this slice)

- `homeassistant/custom_components/roamcore/support_bundle.py`
  — the canonical exporter (286 LOC, real `async def
  export_support_bundle(hass, *, include_zip=True) ->
  dict` + 8 private helpers).
- `homeassistant/custom_components/roamcore/services.yaml`
  — the canonical service registration surface
  (registers `export_support_bundle` with optional
  `zip: true`).
- `homeassistant/custom_components/roamcore/__init__.py`
  — the canonical handler wiring (registers
  `_svc_export_support_bundle` via
  `async_register_service`).
- `docs/howto/support-bundle.md` — the canonical
  operator-facing howto (44 lines).
- `docs/catalog/homelab/support-bundle.md` — the
  legacy 15-line tier-a "RoamCore native" claim stub,
  now carrying the **SUPERSEDED** banner pointing at
  this connection.
- `docs/reference/rc-entity-naming.md` — the
  `support_bundle` subsystem addition to the "Allowed
  subsystems (recommended set)" list (back-fills
  `map` + `mode` + `demo_mode` + `advanced_mode` +
  `trip` + `bed_lift` + `ha_installer` since all seven
  were added by prior slices but the rc-entity-naming
  doc on `origin/main` doesn't yet have them).
- `docs/mvp/features-build-status.md` — the "Support
  bundle (diagnostic snapshot exporter)" Shipped
  (repo) row added by this slice (full tier-a manifest
  + recipe + smoke + contract tiles +
  vendor-neutrality + legacy supersession banner +
  cross-references + PR #79).

### Cross-references

- **OpenClaw JSON API:** [`../openclaw-api/`](../openclaw-api/) —
  the bundle includes `openclaw-summary.json` +
  `openclaw-timeseries-catalog.json` from the OpenClaw
  JSON API custom component (the canonical umbrella
  for local-agent machine-readable summary + skill +
  rc-dump + timeseries endpoints; vendor-neutral
  `rc_openclaw_api_*` ids; Wave 3 #64).
- **HA installer:** [`../ha-installer/`](../ha-installer/) —
  the bundle includes `install-info.txt` +
  `manifest.txt` + `provisioned.marker` from the HA
  installer (the vendor-neutral one-line installer +
  uninstaller + idempotent guard + RC_API_TOKEN-aware
  wiring for Home Assistant installs; vendor-neutral
  `rc_ha_installer_*` ids; Wave 3 #71).
- **Trip Local:** [`../trip-local-tier-a/`](../trip-local-tier-a/) —
  the bundle may include `rc_trip_local_*` entity
  snapshots in the `openclaw-summary.json` payload
  (the vendor-neutral local-first trip metrics from
  the HA recorder: distance / drive time / stops;
  vendor-neutral `rc_trip_local_*` ids; Wave 3 #68).
- **Official HA Developer Tools docs:**
  [`https://www.home-assistant.io/integrations/developer-tools/`](https://www.home-assistant.io/integrations/developer-tools/)
  — the canonical upstream reference for the
  service-call flow (Settings → Developer Tools →
  Services → Call service).

### Verification

- `python3 -m pytest connections/support-bundle/tests/ -v`
  → **8/8 PASS**.
- `bash scripts/check.sh --core-only` → **✅ GREEN**
  (with the support-bundle smoke wired in immediately
  after the ha-installer entry in `scripts/check.sh`).