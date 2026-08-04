# HA installer (one-line)

**Connection:** [HA installer](./connection.yml) — vendor-neutral one-line installer + uninstaller + idempotent guard + RC_API_TOKEN-aware wiring for Home Assistant installs — tier-a connection.

**Recipe:** [`docs/recipe.md`](./docs/recipe.md) — full operator-facing howto.
**Manifest-honesty smoke:** [`tests/test_connection_yml.py`](./tests/test_connection_yml.py) — 8/8 PASS.

## What this connection does

RoamCore ships a vendor-neutral installer surface for Home Assistant: a one-line `curl ... | sh` install that copies the 5 RoamCore HA directories (`packages/` + `custom_components/` + `www/` + `lovelace/` + `tools/`) into the HA host's `/config/` + writes a state manifest + install-info + per-overwrite backups + an uninstall one-liner that reverses the install.

This connection is **tier-a** because RoamCore ALREADY OWNS + SHIPS + MAINTAINS the canonical installer scripts — this is not aspirational tier-a. The installer is fully idempotent (re-running install doesn't lose operator customizations — backups go to `/config/.roamcore/backups/<timestamp>/`) + RC_API_TOKEN-aware (operator can set `RC_API_TOKEN` in the env before the install, and the wiring forwards it to downstream curl probes — currently no probes consume it, but the wiring is in place for future operator-facing automation hooks).

## Operator flow (5 steps)

1. **Run install** — operator taps `input_button.rc_ha_installer_run_install` (or runs the `curl ... | sh` one-liner from `docs/howto/homeassistant-installer.md`). The installer copies the 5 directories into HA `/config/` + writes the manifest + install-info + backups. `sensor.rc_ha_installer_status` flips from `Not-Installed` → `Install-Running` → `Installed`.
2. **Verify** — operator restarts HA + confirms the 5 directories are populated under `/config/` + confirms `sensor.rc_ha_installer_status` shows `Installed`. The §8.4 installed-assets-match-repo guard validates the install.
3. **Pin version (optional)** — operator sets `input_text.rc_ha_installer_installed_ref` to a specific tag/sha and reruns install. The §8.3 stale-version detector compares the installed ref against `ROAMCORE_REF` — if they differ for > 7 days, `sensor.rc_ha_installer_status` flips to `Stale-Version`.
4. **Run uninstall** — operator taps `input_button.rc_ha_installer_run_uninstall` (or runs the `curl ... | sh` uninstall one-liner). The uninstaller removes the 5 directories + the `/config/.roamcore/` state.
5. **Reinstall** — operator reruns install. The installer detects the prior state + creates backups of any overwritten files + writes a new manifest.

## Contract tiles (10 `rc_ha_installer_*`)

| Tile | Type | Purpose |
|------|------|---------|
| `input_text.rc_ha_installer_installed_ref` | input_text | The installed `ROAMCORE_REF` tag/sha |
| `input_text.rc_ha_installer_installed_at` | input_text | ISO 8601 timestamp of last install |
| `input_text.rc_ha_installer_installed_repo` | input_text | The `ROAMCORE_REPO` URL |
| `input_button.rc_ha_installer_run_install` | input_button | One-tap install (fires `shell_command:` wrapper) |
| `input_button.rc_ha_installer_run_uninstall` | input_button | One-tap uninstall (fires `shell_command:` wrapper) |
| `input_text.rc_ha_installer_last_error` | input_text | Last install/uninstall error |
| `input_boolean.rc_ha_installer_backups_enabled` | input_boolean | Whether the installer makes backups |
| `sensor.rc_ha_installer_status` | sensor | Idle/Install-Running/Uninstall-Running/Installed/Stale-Version/Failed/Not-Installed |
| `sensor.rc_ha_installer_files_installed_count` | sensor | Count of files in `/config/.roamcore/manifest.txt` |
| `binary_sensor.rc_ha_installer_installed_assets_match_repo` | binary_sensor | true if installed files match repo inventory |

## FIVE §8 MANDATORY automations

1. **§8.1 install-button guard** — when `input_button.rc_ha_installer_run_install` is pressed, mark `sensor.rc_ha_installer_status = Install-Running` + clear stale `last_error`. The `shell_command:` wrapper runs the canonical installer.
2. **§8.2 uninstall-button guard** — when `input_button.rc_ha_installer_run_uninstall` is pressed, mark `sensor.rc_ha_installer_status = Uninstall-Running` + clear manifest + install-info state.
3. **§8.3 stale-version detector** — when `installed_ref != ROAMCORE_REF` for > 7 days, mark `sensor.rc_ha_installer_status = Stale-Version` + surface "RoamCore is outdated" notification.
4. **§8.4 installed-assets-match-repo guard** — when `files_installed_count != <repo file count>`, mark `binary_sensor.rc_ha_installer_installed_assets_match_repo = false` + surface "RoamCore install is incomplete" notification.
5. **§8.5 install-failure capture** — when the `shell_command:` wrapper exits non-zero, capture stderr into `input_text.rc_ha_installer_last_error` + mark `sensor.rc_ha_installer_status = Failed`.

## Supersession

The legacy catalog page [`docs/catalog/homelab/ha-installer.md`](../docs/catalog/homelab/ha-installer.md) (13 lines, tier-a "RoamCore native" claim) has been SUPERSEDED by this connection folder. The legacy claim is honest-upstream-truth: RoamCore ships + maintains + audits the canonical installer scripts and the operator howto — this connection wraps them as a tier-a recipe connection manifest.

## Cross-references

- RoamCore-owned installer scripts: [`install.sh`](../../install.sh) + [`uninstall.sh`](../../uninstall.sh) (root wrappers)
- RoamCore-owned canonical HA installer: [`homeassistant/install.sh`](../../homeassistant/install.sh) + [`homeassistant/uninstall.sh`](../../homeassistant/uninstall.sh)
- Operator howto: [`docs/howto/homeassistant-installer.md`](../../docs/howto/homeassistant-installer.md) (108 lines)
- HA smoke check: [`scripts/checks/ha-beta-smoke.sh`](../../scripts/checks/ha-beta-smoke.sh)
- Trip Local Wave 3 #68 connection: `../trip-local/` (the installer copies the trip-local package)
- Trip Wrapped Wave 3 #69 connection: `../trip-wrapped/` (the installer copies the trip-wrapped package + tools)
- OpenClaw JSON API Wave 3 #64 connection: `../openclaw-api/` (the installer copies the roamcore_openclaw_api custom component)
- Bed Lift DIY Wave 3 #70 connection: `../bed-lift-diy/` (the installer copies the bed-lift-diy package)
