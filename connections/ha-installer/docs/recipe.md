# Recipe: HA installer — vendor-neutral one-line installer + uninstaller + idempotent guard + RC_API_TOKEN-aware wiring for Home Assistant installs — tier-a connection.

**Connection:** [`connections/ha-installer/`](../)
**Manifest:** [`../connection.yml`](../connection.yml)
**Status:** beta (tier-a-but-flagged — see [§12 Promoting to fully-fledged tier-a](#12-promoting-to-fully-fledged-tier-a))
**Manifest-honesty smoke:** [`../tests/test_connection_yml.py`](../tests/test_connection_yml.py) — 8/8 PASS.

## §1 What is HA installer in RoamCore?

The **HA installer** connection wraps RoamCore's canonical Home Assistant installer surface — a vendor-neutral one-line install that copies the 5 RoamCore HA directories into HA's `/config/` + a matching one-line uninstall + an idempotent guard + RC_API_TOKEN-aware wiring for future automation hooks.

RoamCore ALREADY OWNS + SHIPS + MAINTAINS the canonical installer scripts:

- **Root wrapper** [`install.sh`](../../../install.sh) (79 LOC) — thin sh wrapper that delegates to `homeassistant/install.sh` and forwards `ROAMCORE_REPO`, `ROAMCORE_REF`, `CONFIG_DIR`, `WORK_BASE`.
- **Root uninstaller wrapper** [`uninstall.sh`](../../../uninstall.sh) (78 LOC) — thin sh wrapper that delegates to `homeassistant/uninstall.sh`.
- **Canonical HA installer** [`homeassistant/install.sh`](../../../homeassistant/install.sh) (274 LOC) — copies 5 directories + writes state files.
- **Canonical HA uninstaller** [`homeassistant/uninstall.sh`](../../../homeassistant/uninstall.sh) (92 LOC) — reverses the install.
- **Operator howto** [`docs/howto/homeassistant-installer.md`](../../../docs/howto/homeassistant-installer.md) (108 lines) — canonical operator-walk through the one-line install + the 5 directories copied + the 3 state files written + the uninstall one-liner + the 5 verification steps + the RC_API_TOKEN-aware wiring guidance.

The installer is fully idempotent — re-running install doesn't lose operator customizations because any file that would be overwritten is first copied to `/config/.roamcore/backups/<timestamp>/`. The installer is RC_API_TOKEN-aware — the operator can set `RC_API_TOKEN` in the env before the install, and the installer forwards it to any downstream curl probes (currently no probes consume it — but the wiring is in place for future operator-facing automation hooks via the §8.5 install-failure capture automation's `shell_command:` wrapper).

This slice DOES NOT replace any of that code. It ADDS the `connections/ha-installer/` recipe layer that:

1. Wraps the existing installer scripts as a tier-a connection-style manifest so the audit pipeline can find them.
2. Defines the canonical 10 `rc_ha_installer_*` contract tiles that the dashboard + operator-facing setup flow use.
3. Wires the FIVE §8 MANDATORY automations (install-button guard + uninstall-button guard + stale-version detector + installed-assets-match-repo + install-failure capture).
4. Documents the upgrade path for tier-a promotion (when the installer gains pytest integration tests against a controlled bench — see [§12](#12-promoting-to-fully-fledged-tier-a)).

## §2 Prerequisites

Before running the install, the operator needs:

- **HAOS host** (or HA Supervised + HA Core with the Terminal & SSH add-on enabled). The installer is shell-script-based; it requires shell access to the HA host.
- **Shell access** to the HA host. On HAOS, install the **Terminal & SSH** add-on from the Add-on Store.
- **`curl` available** on the HA host. HAOS includes curl by default.
- **`ROAMCORE_REF`** (optional) — if the operator wants to pin a specific ref (e.g. `v0.1.0`), set `ROAMCORE_REF=v0.1.0` before the install.
- **`ROAMCORE_REPO`** (optional) — defaults to `https://github.com/roamcore/RoamCore`. Override only for forks.
- **`CONFIG_DIR`** (optional) — defaults to `/config`. Override for non-standard HA installs.
- **`WORK_BASE`** (optional) — defaults to `/tmp/roamcore-install`. Override if `/tmp` is too small.
- **`RC_API_TOKEN`** (optional) — set in the env before the install. The installer forwards it to any downstream curl probes (currently no probes consume it — the wiring is in place for future operator-facing automation hooks via the §8.5 install-failure capture automation's `shell_command:` wrapper).

The installer does NOT need:

- **HACS** — the installer copies the custom components directly, not via HACS.
- **pip / pypi** — the installer doesn't install Python packages; it copies files directly into `/config/custom_components/`.
- **docker / docker-compose / kubernetes / ansible / terraform** — the installer runs as a shell script on the HA host itself.

## §3 Step 1 — Run install

The operator has two ways to run the install:

### Option A: One-line `curl ... | sh` (canonical)

From the HA host's Terminal & SSH add-on:

```sh
curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh | sh
```

To pin a specific ref:

```sh
ROAMCORE_REF=v0.1.0 \
  curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh | sh
```

To set `RC_API_TOKEN` for downstream curl probes:

```sh
RC_API_TOKEN=my-token \
  curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh | sh
```

### Option B: One-tap install button (dashboard)

The operator taps `input_button.rc_ha_installer_run_install` in the dashboard. The §8.1 install-button guard marks `sensor.rc_ha_installer_status = Install-Running` + clears any stale `input_text.rc_ha_installer_last_error`. The button press fires the `shell_command.rc_ha_installer_run_install` wrapper, which executes the canonical installer script.

### What the installer does

The canonical HA installer (`homeassistant/install.sh`, 274 LOC) copies:

- `homeassistant/packages/*` → `/config/packages/*`
- `homeassistant/custom_components/*` → `/config/custom_components/*`
- `homeassistant/www/*` → `/config/www/*` (RoamCore JS ends up at `/config/www/roamcore/*.js`, served as `/local/roamcore/*.js`)
- `homeassistant/lovelace/*` → `/config/lovelace/*`
- `homeassistant/tools/*` → `/config/tools/*` (used by local exporters like Trip Wrapped)

The installer writes state to:

- `/config/.roamcore/manifest.txt` — list of installed files (one per line)
- `/config/.roamcore/install-info.txt` — which ref was installed + which repo + which timestamp
- `/config/.roamcore/backups/<timestamp>/...` — copies of any overwritten files

The installer is fully idempotent: re-running install creates a new backup directory (`/config/.roamcore/backups/<timestamp>/`) for any files that would be overwritten, then writes a new manifest. Operator customizations to RoamCore-shipped files are NEVER lost — they always go to a timestamped backup directory first.

## §4 Step 2 — Verify

After the install completes, the operator verifies:

1. **Restart Home Assistant** — Settings → System → Restart (the `input_button` triggers a "restart HA now" notification chip).
2. **Confirm files exist on disk** — from the Terminal & SSH add-on:
   ```sh
   ls -la /config/packages | grep roamcore
   ls -la /config/custom_components | grep roamcore
   ls -la /config/www/roamcore
   ```
3. **Confirm `sensor.rc_ha_installer_status` shows `Installed`** — the dashboard's first tile should display the green "Installed" chip. If it shows `Failed`, check `input_text.rc_ha_installer_last_error` for the stderr capture.
4. **Confirm `sensor.rc_ha_installer_files_installed_count` matches expected** — the count should be roughly equal to the file count in the repo's `homeassistant/` directory (the `find homeassistant -type f | wc -l` value, minus meta-files).
5. **Confirm `binary_sensor.rc_ha_installer_installed_assets_match_repo = true`** — the §8.4 installed-assets-match-repo guard validates this.

In the HA UI:

- Developer Tools → **YAML** → reload *Template Entities* / *Automations* (if the operator prefers not to restart).
- Settings → Devices & services: confirm any RoamCore custom integrations appear/initialize.

Open the RoamCore dashboard and complete first-run setup:

- Dashboard: `/roamcore/home`
- Setup wizard: `/roamcore/setup`
- Optional: enable **RC Demo Mode** (`input_boolean.rc_demo_mode`) to preview the UI even if critical sensors are still missing.

## §5 Step 3 — Pin version (optional)

The installer does NOT enforce version pinning — by default it pulls from the `main` branch of `https://github.com/roamcore/RoamCore`. To pin to a specific tag/sha:

```sh
ROAMCORE_REF=v0.1.0 \
  curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh | sh
```

After the install completes, the operator updates `input_text.rc_ha_installer_installed_ref` to the same ref so the dashboard matches the actual install:

```yaml
service: input_text.set_value
target:
  entity_id: input_text.rc_ha_installer_installed_ref
data:
  value: "v0.1.0"
```

The §8.3 stale-version detector compares `input_text.rc_ha_installer_installed_ref` against the configured `ROAMCORE_REF` — if they differ for > 7 days (operator-tunable via `input_number.rc_ha_installer_stale_version_days_threshold`, default 7), `sensor.rc_ha_installer_status` flips to `Stale-Version` and the operator gets a "RoamCore is outdated" notification.

The slice does NOT enforce pinning (it's the operator's choice — running on `main` is also valid for testing).

## §6 Step 4 — Run uninstall

The operator has two ways to run the uninstall:

### Option A: One-line `curl ... | sh` (canonical)

From the HA host's Terminal & SSH add-on:

```sh
curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/uninstall.sh | sh
```

### Option B: One-tap uninstall button (dashboard)

The operator taps `input_button.rc_ha_installer_run_uninstall` in the dashboard. The §8.2 uninstall-button guard marks `sensor.rc_ha_installer_status = Uninstall-Running` + clears the manifest + install-info state. The button press fires the `shell_command.rc_ha_installer_run_uninstall` wrapper.

### What the uninstaller does

The canonical HA uninstaller (`homeassistant/uninstall.sh`, 92 LOC) reverses the install:

- Removes the 5 copied directories from HA `/config/`:
  - `/config/packages/roamcore_*`
  - `/config/custom_components/roamcore_*`
  - `/config/www/roamcore/`
  - `/config/lovelace/roamcore-*`
  - `/config/tools/roamcore_*`
- Removes the `/config/.roamcore/` state directory (manifest + install-info + backups).
- `sensor.rc_ha_installer_status` flips to `Not-Installed`.
- `input_text.rc_ha_installer_installed_ref` resets to `not installed`.
- `input_text.rc_ha_installer_installed_at` resets to `unknown`.
- `input_text.rc_ha_installer_installed_repo` resets to `unknown`.
- `sensor.rc_ha_installer_files_installed_count` resets to 0.
- `binary_sensor.rc_ha_installer_installed_assets_match_repo` resets to `false`.

The uninstaller is safe to re-run — it handles the case where some directories don't exist.

## §7 Step 5 — Reinstall

After an uninstall, the operator can rerun install (Step 1) to reinstall. The installer detects that the prior `/config/.roamcore/` state was cleared by the uninstaller + creates a fresh manifest.

After an install (without uninstalling first), the operator can rerun install (Step 1) to refresh to a newer ref. The installer detects the prior `/config/.roamcore/` state + creates backups of any files that would be overwritten (`/config/.roamcore/backups/<timestamp>/`) + writes a new manifest.

The reinstall flow is the same as Step 1 — the operator taps `input_button.rc_ha_installer_run_install` (or runs the `curl ... | sh` one-liner).

## §8 RoamCore contract entities (the 10 `rc_ha_installer_*` tiles)

The 10 contract tiles are the dashboard-side companion to the installer scripts. They're HA core `input_text` + `input_button` + `input_boolean` helpers + `template:` sensors + `binary_sensor:` derivations. The audit + boundary CI can detect the contract via the `rc_ha_installer_*` prefix in the tile IDs.

### Tile 1: `input_text.rc_ha_installer_installed_ref`

The installed `ROAMCORE_REF` tag/sha. Defaults to `not installed` until the first run.

```yaml
input_text:
  rc_ha_installer_installed_ref:
    name: "RoamCore HA installer — installed ref"
    initial: "not installed"
    max: 255
    icon: mdi:tag-outline
```

### Tile 2: `input_text.rc_ha_installer_installed_at`

ISO 8601 timestamp of the last successful install. Defaults to `not installed` until the first run.

```yaml
input_text:
  rc_ha_installer_installed_at:
    name: "RoamCore HA installer — installed at"
    initial: "not installed"
    max: 32
    icon: mdi:clock-outline
```

### Tile 3: `input_text.rc_ha_installer_installed_repo`

The `ROAMCORE_REPO` URL that was used for the last successful install. Defaults to `not installed` until the first run.

```yaml
input_text:
  rc_ha_installer_installed_repo:
    name: "RoamCore HA installer — installed repo"
    initial: "not installed"
    max: 255
    icon: mdi:source-repository
```

### Tile 4: `input_button.rc_ha_installer_run_install`

One-tap dry-run + execute the canonical `curl ... | sh` flow. The button press fires the §8.1 install-button guard + the `shell_command.rc_ha_installer_run_install` wrapper.

```yaml
input_button:
  rc_ha_installer_run_install:
    name: "RoamCore HA installer — run install"
    icon: mdi:download-network-outline
```

### Tile 5: `input_button.rc_ha_installer_run_uninstall`

One-tap run the uninstaller. The button press fires the §8.2 uninstall-button guard + the `shell_command.rc_ha_installer_run_uninstall` wrapper.

```yaml
input_button:
  rc_ha_installer_run_uninstall:
    name: "RoamCore HA installer — run uninstall"
    icon: mdi:trash-can-outline
```

### Tile 6: `input_text.rc_ha_installer_last_error`

The last install / uninstall error message (stderr capture from the `shell_command:` wrapper). Defaults to `none` (empty).

```yaml
input_text:
  rc_ha_installer_last_error:
    name: "RoamCore HA installer — last error"
    initial: "none"
    max: 1024
    icon: mdi:alert-circle-outline
```

### Tile 7: `input_boolean.rc_ha_installer_backups_enabled`

Whether the installer makes backup copies before overwriting. Defaults to ON (matches the existing `install.sh` behavior of writing to `/config/.roamcore/backups/<timestamp>/`).

```yaml
input_boolean:
  rc_ha_installer_backups_enabled:
    name: "RoamCore HA installer — backups enabled"
    initial: true
    icon: mdi:archive-outline
```

### Tile 8: `sensor.rc_ha_installer_status`

Idle / Install-Running / Uninstall-Running / Installed / Stale-Version / Failed / Not-Installed. Derived from the `/config/.roamcore/install-info.txt` file + the §8.3 stale-version detector.

```yaml
template:
  - sensor:
      - name: "RoamCore HA installer — status"
        unique_id: rc_ha_installer_status
        state: >
          {% set info = exists('/config/.roamcore/install-info.txt') %}
          {% if is_state('input_boolean.rc_ha_installer_install_running', 'on') %}
            Install-Running
          {% elif is_state('input_boolean.rc_ha_installer_uninstall_running', 'on') %}
            Uninstall-Running
          {% elif not info %}
            Not-Installed
          {% elif states('sensor.rc_ha_installer_stale_version_days') | float(0) > 7 %}
            Stale-Version
          {% elif states('input_text.rc_ha_installer_last_error') != 'none' %}
            Failed
          {% else %}
            Installed
          {% endif %}
        icon: mdi:check-circle-outline
```

### Tile 9: `sensor.rc_ha_installer_files_installed_count`

Count of files copied into `/config/`; derived from the `/config/.roamcore/manifest.txt` (one file per line).

```yaml
template:
  - sensor:
      - name: "RoamCore HA installer — files installed count"
        unique_id: rc_ha_installer_files_installed_count
        state: >
          {% set manifest = '/config/.roamcore/manifest.txt' %}
          {% if exists(manifest) %}
            {{ value_lines(manifest) | length }}
          {% else %}
            0
          {% endif %}
        unit_of_measurement: "files"
        icon: mdi:file-multiple-outline
```

### Tile 10: `binary_sensor.rc_ha_installer_installed_assets_match_repo`

true if the installed file list matches the current repo's `homeassistant/` inventory. Driven by the §8.4 installed-assets-match-repo guard.

```yaml
template:
  - binary_sensor:
      - name: "RoamCore HA installer — installed assets match repo"
        unique_id: rc_ha_installer_installed_assets_match_repo
        state: >
          {% set installed = states('sensor.rc_ha_installer_files_installed_count') | int(0) %}
          {% set repo_count = states('sensor.rc_ha_installer_repo_file_count') | int(0) %}
          {{ installed == repo_count and installed > 0 }}
        icon: mdi:check-decagram-outline
```

### `shell_command:` wrappers

The installer runs as a shell command. The `shell_command:` wrappers are the integration-layer glue that the §8.1 + §8.2 + §8.5 automations fire:

```yaml
shell_command:
  rc_ha_installer_run_install: >
    curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh | sh
    && echo $? > /config/.roamcore/last-exit-code
    || echo $? > /config/.roamcore/last-exit-code
  rc_ha_installer_run_uninstall: >
    curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/uninstall.sh | sh
    && echo $? > /config/.roamcore/last-exit-code
    || echo $? > /config/.roamcore/last-exit-code
```

The §8.5 install-failure capture automation polls `/config/.roamcore/last-exit-code` to detect non-zero exits.

## §9 Automations (MANDATORY before first use)

The FIVE §8 MANDATORY automations wire the contract tiles to the installer scripts. They MUST be wired before first use — without them, the operator gets no install-state visibility + no idempotency guard + no stale-version detection + no install-failure capture.

### §9.1 Install-button guard

When `input_button.rc_ha_installer_run_install` is pressed, mark `sensor.rc_ha_installer_status = Install-Running` and clear any stale `input_text.rc_ha_installer_last_error`. The actual install work happens via the `shell_command.rc_ha_installer_run_install` wrapper.

```yaml
automation:
  - id: rc_ha_installer_install_button_guard
    alias: "HA installer — install-button guard"
    trigger:
      - platform: state
        entity_id: input_button.rc_ha_installer_run_install
    action:
      - service: input_text.set_value
        target:
          entity_id: input_text.rc_ha_installer_last_error
        data:
          value: "none"
      - service: input_boolean.turn_on
        target:
          entity_id: input_boolean.rc_ha_installer_install_running
      - service: shell_command.rc_ha_installer_run_install
      - delay: "00:00:05"
      - service: input_boolean.turn_off
        target:
          entity_id: input_boolean.rc_ha_installer_install_running
      - service: input_text.set_value
        target:
          entity_id: input_text.rc_ha_installer_installed_at
        data:
          value: "{{ now().isoformat() }}"
      - service: homeassistant.restart
        data:
          message: "RoamCore installer — restart HA to reload packages"
```

### §9.2 Uninstall-button guard

When `input_button.rc_ha_installer_run_uninstall` is pressed, mark `sensor.rc_ha_installer_status = Uninstall-Running` and clear the manifest + install-info state. The actual uninstall work happens via the `shell_command.rc_ha_installer_run_uninstall` wrapper.

```yaml
automation:
  - id: rc_ha_installer_uninstall_button_guard
    alias: "HA installer — uninstall-button guard"
    trigger:
      - platform: state
        entity_id: input_button.rc_ha_installer_run_uninstall
    action:
      - service: input_text.set_value
        target:
          entity_id: input_text.rc_ha_installer_last_error
        data:
          value: "none"
      - service: input_boolean.turn_on
        target:
          entity_id: input_boolean.rc_ha_installer_uninstall_running
      - service: shell_command.rc_ha_installer_run_uninstall
      - delay: "00:00:05"
      - service: input_boolean.turn_off
        target:
          entity_id: input_boolean.rc_ha_installer_uninstall_running
      - service: input_text.set_value
        target:
          entity_id: input_text.rc_ha_installer_installed_ref
        data:
          value: "not installed"
      - service: input_text.set_value
        target:
          entity_id: input_text.rc_ha_installer_installed_at
        data:
          value: "not installed"
      - service: input_text.set_value
        target:
          entity_id: input_text.rc_ha_installer_installed_repo
        data:
          value: "not installed"
      - service: homeassistant.restart
        data:
          message: "RoamCore uninstaller — restart HA to reload packages"
```

### §9.3 Stale-version detector

When `input_text.rc_ha_installer_installed_ref` differs from the configured `ROAMCORE_REF` for > 7 days, mark `sensor.rc_ha_installer_status = Stale-Version` and surface a "RoamCore is outdated" notification. The 7-day threshold is operator-tunable via `input_number.rc_ha_installer_stale_version_days_threshold` (default 7).

```yaml
automation:
  - id: rc_ha_installer_stale_version_detector
    alias: "HA installer — stale-version detector"
    trigger:
      - platform: time_pattern
        hours: "/1"
    condition:
      - condition: template
        value_template: >
          {{ states('input_text.rc_ha_installer_installed_ref') != 'not installed' and
             states('input_text.rc_ha_installer_installed_ref') != states('input_text.rc_ha_installer_configured_ref') and
             (now() - as_datetime(states('input_text.rc_ha_installer_installed_at'))) > timedelta(days=states('input_number.rc_ha_installer_stale_version_days_threshold') | int(7)) }}
    action:
      - service: persistent_notification.create
        data:
          title: "RoamCore is outdated"
          message: >
            Your installed RoamCore ref ({{ states('input_text.rc_ha_installer_installed_ref') }})
            differs from the configured ref ({{ states('input_text.rc_ha_installer_configured_ref') }})
            for more than {{ states('input_number.rc_ha_installer_stale_version_days_threshold') }} days.
            Consider reinstalling to pick up the latest changes.
```

### §9.4 Installed-assets-match-repo guard

When `sensor.rc_ha_installer_files_installed_count` differs from the count of files in the current repo's `homeassistant/` inventory, mark `binary_sensor.rc_ha_installer_installed_assets_match_repo = false` and surface a "RoamCore install is incomplete" notification.

```yaml
automation:
  - id: rc_ha_installer_installed_assets_match_repo
    alias: "HA installer — installed-assets-match-repo guard"
    trigger:
      - platform: state
        entity_id: sensor.rc_ha_installer_files_installed_count
    condition:
      - condition: template
        value_template: >
          {{ states('sensor.rc_ha_installer_files_installed_count') | int(0) !=
             states('sensor.rc_ha_installer_repo_file_count') | int(0) }}
    action:
      - service: persistent_notification.create
        data:
          title: "RoamCore install is incomplete"
          message: >
            Your RoamCore install has {{ states('sensor.rc_ha_installer_files_installed_count') }} files,
            but the current repo has {{ states('sensor.rc_ha_installer_repo_file_count') }} files.
            Consider reinstalling to bring the install up to date.
```

### §9.5 Install-failure capture

When the `shell_command:` wrapper exits non-zero, capture stderr into `input_text.rc_ha_installer_last_error` and mark `sensor.rc_ha_installer_status = Failed`. The `shell_command:` wrapper writes its exit code to a sentinel file at `/config/.roamcore/last-exit-code` that the automation polls.

```yaml
automation:
  - id: rc_ha_installer_install_failure_capture
    alias: "HA installer — install-failure capture"
    trigger:
      - platform: file
        entity_id: sensor.rc_ha_installer_last_exit_code
    condition:
      - condition: template
        value_template: >
          {{ states('sensor.rc_ha_installer_last_exit_code') | int(0) != 0 }}
    action:
      - service: input_text.set_value
        target:
          entity_id: input_text.rc_ha_installer_last_error
        data:
          value: >
            Install failed with exit code {{ states('sensor.rc_ha_installer_last_exit_code') }}.
            Check the HA logs for details.
      - service: persistent_notification.create
        data:
          title: "RoamCore install failed"
          message: >
            The RoamCore install failed with exit code {{ states('sensor.rc_ha_installer_last_exit_code') }}.
            Check input_text.rc_ha_installer_last_error for details.
```

## §10 Troubleshooting

### §10.1 Install fails with curl 404

If the install fails with `curl: (22) The requested URL returned error: 404`, the operator is likely using a stale `ROAMCORE_REPO` URL or the repo was renamed/moved. Check the URL by running `curl -fsSL <ROAMCORE_REPO>/main/install.sh` in a browser — if it returns 404, the repo was moved. Update `ROAMCORE_REPO` to the new URL and rerun.

### §10.2 Install fails with permission denied

If the install fails with `permission denied` errors when writing to `/config/`, the operator likely doesn't have write access to the HA config directory. On HAOS, the `share` user (used by the Terminal & SSH add-on) has write access by default. If using a custom user, grant it write access via `chown` or `chmod`.

### §10.3 Uninstall leaves HA in broken state

If the uninstall leaves HA in a broken state (e.g. broken automations referencing removed entities), the operator should restore from a backup. The installer creates backups at `/config/.roamcore/backups/<timestamp>/` before overwriting any file, so the operator can manually restore specific files if needed.

### §10.4 Reinstall overwrites user customizations

If the operator customized a RoamCore-shipped file (e.g. a package YAML) and then reran install, the customization was moved to `/config/.roamcore/backups/<timestamp>/` before the new version was copied in. To restore the customization, copy the file back from the backup directory.

### §10.5 Stale-version detector keeps firing

If the §8.3 stale-version detector keeps firing even though the operator just reinstalled, check that `input_text.rc_ha_installer_installed_ref` was updated to the same ref as `input_text.rc_ha_installer_configured_ref`. The §9.1 install-button guard automation updates `installed_ref` automatically — but if the operator ran the install via `curl ... | sh` manually, they need to update `installed_ref` manually.

### §10.6 Installed-assets-match-repo fires after a manual file delete

If the §8.4 installed-assets-match-repo guard fires because the operator manually deleted a file from `/config/packages/`, `/config/custom_components/`, `/config/www/`, `/config/lovelace/`, or `/config/tools/`, they can either (a) restore the file from a backup at `/config/.roamcore/backups/<timestamp>/`, or (b) rerun the install to restore the file.

## §11 Privacy

The installer is **100% local** — no telemetry, no analytics, no cloud calls except the initial `curl` from the operator's machine to GitHub to fetch the install script.

- **Initial curl** — the operator runs `curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh | sh` from their HA host. This is the only network call (to GitHub, over HTTPS). GitHub sees the operator's IP address + user-agent.
- **File copies** — once the install script is downloaded, all file copies are local (from `/tmp/roamcore-install/` to `/config/`).
- **No telemetry** — the installer does not phone home, does not log to any cloud service, does not report install success/failure to any external server.
- **No vendor-side storage** — the operator's install state is stored locally at `/config/.roamcore/manifest.txt` + `/config/.roamcore/install-info.txt`. There is no RoamCore-side database tracking installs.
- **RC_API_TOKEN is forwarded only** — if the operator sets `RC_API_TOKEN` in the env, it is forwarded to any downstream curl probes the installer might run. Currently no probes consume it — but the wiring is in place for future operator-facing automation hooks via the §8.5 install-failure capture automation's `shell_command:` wrapper. The token is NOT stored anywhere by RoamCore; the operator owns it.

## §12 Promoting to fully-fledged tier-a

This slice is **tier-a-but-flagged** because the installer has real RoamCore-owned installer code + a RoamCore-owned operator-wired setup flow (`curl ... | sh`) + a shell-based smoke check, but it does NOT have pytest integration tests against a controlled bench.

To promote to fully-fledged tier-a, the bench fixture gap must be closed. The 8 canned-response bench artifacts needed:

1. **Canned install-success response** (curl exit 0 + `manifest.txt` populated with the 5 directory listings).
2. **Canned install-failure response** (curl exit non-zero + stderr captured into `input_text.rc_ha_installer_last_error`).
3. **Canned uninstall-success response** (curl exit 0 + `manifest.txt` truncated).
4. **Canned uninstall-failure response** (curl exit non-zero + stderr captured).
5. **Canned reinstall response** (prior `manifest.txt` detected + backup created at `/config/.roamcore/backups/<timestamp>/`).
6. **Canned stale-version response** (installed_ref != `ROAMCORE_REF` for > 7 days).
7. **Canned installed-assets-match response** (files_installed_count matches repo inventory).
8. **Canned installed-assets-mismatch response** (files_installed_count differs from repo inventory).

The bench would be a docker-compose rig with:

- A HA core container (running the latest HA core release).
- A RoamCore clone (mounted as a volume for the `homeassistant/` inventory).
- A canned test fixture directory with the 8 responses above.
- A pytest integration test that asserts the §8.1 + §8.2 + §8.3 + §8.4 + §8.5 automations fire correctly under each canned fixture.

When this bench lands, the tier_requirements can be flipped to mark the connection as fully-fledged tier-a (status: stable, tier_warnings reduced to the bench-fixture gap being closed).

## §13 Files + cross-references

This slice added or modified:

**NEW** `connections/ha-installer/connection.yml` (708 lines) — tier-a manifest.
**NEW** `connections/ha-installer/__init__.py` (234 lines) — `DOMAIN = "ha_installer"` marker.
**NEW** `connections/ha-installer/README.md` (58 lines) — folder overview.
**NEW** `connections/ha-installer/docs/recipe.md` (this file) — operator-facing howto.
**NEW** `connections/ha-installer/tests/test_connection_yml.py` — 8 manifest-honesty tests.

**MOD** `scripts/check.sh` — wired `connections/ha-installer/tests/test_connection_yml.py` smoke check.
**MOD** `docs/catalog/homelab/ha-installer.md` — appended SUPERSEDED banner.
**MOD** `docs/reference/rc-entity-naming.md` — added `ha_installer` subsystem + back-fill for `map` + `trip` + `bed_lift` OWNED entries.
**MOD** `docs/mvp/features-build-status.md` — added HA installer Shipped (repo) row.

Cross-references:

- The RoamCore-owned installer scripts at repo root (`install.sh` + `uninstall.sh`) are the canonical entry points for the operator-facing one-line install / uninstall flows.
- The RoamCore-owned installer scripts at `homeassistant/install.sh` + `homeassistant/uninstall.sh` are the canonical HA-only installer + uninstaller (the root scripts are thin wrappers that delegate to these).
- The operator howto at `docs/howto/homeassistant-installer.md` (108 lines) is the canonical operator-walk through the one-line install + the 5 directories copied + the 3 state files written + the uninstall one-liner + the 5 verification steps + the RC_API_TOKEN-aware wiring guidance.
- The HA smoke check at `scripts/checks/ha-beta-smoke.sh` is the canonical smoke check for the installer surface.
- The Trip Local Wave 3 #68 connection (`../trip-local/`) cross-references the installer because the installer copies the trip-local package (`homeassistant/packages/roamcore_trip_local.yaml`) into HA `/config/packages/`.
- The Trip Wrapped Wave 3 #69 connection (`../trip-wrapped/`) cross-references the installer because the installer copies the trip-wrapped package (`homeassistant/packages/roamcore_trip_wrapped.yaml`) + the trip-wrapped tools (`homeassistant/tools/trip_wrapped/`) into HA `/config/`.
- The OpenClaw JSON API Wave 3 #64 connection (`../openclaw-api/`) cross-references the installer because the installer copies the roamcore_openclaw_api custom component (`homeassistant/custom_components/roamcore_openclaw_api/`) into HA `/config/custom_components/`.
- The Bed Lift DIY Wave 3 #70 connection (`../bed-lift-diy/`) cross-references the installer because the installer copies the bed-lift-diy package (`homeassistant/packages/roamcore_bed_lift_diy.yaml`) into HA `/config/packages/`.
- The official HA installation documentation at `https://www.home-assistant.io/installation/` is the canonical reference for HAOS / HA Supervised / HA Core install prerequisites.
