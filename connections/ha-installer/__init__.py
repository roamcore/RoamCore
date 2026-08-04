"""RoamCore connection: HA installer — vendor-neutral one-line
installer + uninstaller + idempotent guard + RC_API_TOKEN-
aware wiring for Home Assistant installs — tier-a connection.

This is a TIER-A connection that wraps the existing
RoamCore-owned installer scripts at repo root (`install.sh`
+ `uninstall.sh`, both thin wrappers that delegate to the
canonical HA installer + uninstaller) + the canonical HA
installer at `homeassistant/install.sh` (274 LOC, copies
the 5 directories into HA `/config/`) + the canonical HA
uninstaller at `homeassistant/uninstall.sh` (92 LOC,
reverses the install) + the operator howto at
`docs/howto/homeassistant-installer.md` (108 lines, the
canonical operator-walk through the one-line install + the
5 directories copied + the 3 state files written + the
uninstall one-liner + the 5 verification steps + the
RC_API_TOKEN-aware wiring guidance).

The installer copies `homeassistant/packages/*` →
`/config/packages/*` + `homeassistant/custom_components/*`
→ `/config/custom_components/*` + `homeassistant/www/*` →
`/config/www/*` + `homeassistant/lovelace/*` →
`/config/lovelace/*` + `homeassistant/tools/*` →
`/config/tools/*`. It writes state to
`/config/.roamcore/manifest.txt` (list of installed files)
+ `/config/.roamcore/install-info.txt` (which ref was
installed) + `/config/.roamcore/backups/<timestamp>/`
(copies of any overwritten files).

This file is just the connection manifest marker
(`DOMAIN = "ha_installer"`) used by the audit script to
detect the connection. The actual installer lives in the
canonical shell scripts at repo root + `homeassistant/`.

The connection's recipe + contract tiles + FIVE §8
MANDATORY automations are documented in
`connections/ha-installer/docs/recipe.md`.

The operator-wired setup flow is the canonical `curl ...
| sh` one-liner documented in
`docs/howto/homeassistant-installer.md` (the operator runs
`curl -fsSL https://raw.githubusercontent.com/roamcore/
RoamCore/main/install.sh | sh` from the HA host's Terminal
& SSH add-on). The `input_button.rc_ha_installer_run_
install` + `input_button.rc_ha_installer_run_uninstall`
dashboard tiles are the dashboard-side companion to the
one-liner — they fire the `shell_command:` wrappers that
run the canonical installer + uninstaller.

The installer is RC_API_TOKEN-aware — the operator can set
`RC_API_TOKEN` in the env before the `curl ... | sh`
install, and the installer forwards it to any downstream
curl probes the installer might run (currently no probes
consume it — but the wiring is in place for future
operator-facing automation hooks via the §8.5 install-
failure capture automation's `shell_command:` wrapper).

The umbrella publishes the resulting data via the existing
RoamCore-owned installer scripts at repo root
(`install.sh` + `uninstall.sh`) + the canonical installer
at `homeassistant/install.sh` + the canonical uninstaller
at `homeassistant/uninstall.sh`, then publishes the
RoamCore ha-installer contract tiles on top (the 10
contract entities documented in the manifest's
`dashboard.tiles` list — 4 `input_text` helpers
(installed_ref + installed_at + installed_repo +
last_error) + 2 `input_button` helpers (run_install +
run_uninstall) + 1 `input_boolean` helper
(backups_enabled) + 2 `sensor` derivations (status +
files_installed_count) + 1 `binary_sensor` derivation
(installed_assets_match_repo) = 10 contract entities).

The audit + boundary CI can detect an `ha-installer/`
folder that claims to be a connection via the `DOMAIN`
constant exported here. The wizard reads the manifest +
recipe at runtime.

The real per-operator ha-installer affordance path is:

    Operator-side choice of the FIVE-step flow (Run
        install -> Verify -> Pin version (optional) ->
        Run uninstall -> Reinstall)
        -> existing installer scripts (root `install.sh`
           + root `uninstall.sh` + `homeassistant/
           install.sh` + `homeassistant/uninstall.sh`)
        -> existing operator howto (`docs/howto/
           homeassistant-installer.md`, 108 lines, the
           canonical operator-walk through the one-line
           install + the 5 directories copied + the 3
           state files written + the uninstall one-liner
           + the 5 verification steps + the RC_API_TOKEN-
           aware wiring guidance)
        -> existing state files (the manifest at
           `/config/.roamcore/manifest.txt` + the install-
           info at `/config/.roamcore/install-info.txt` +
           the backups at `/config/.roamcore/backups/
           <timestamp>/`)
        -> the RoamCore contract layer (the 10
           `rc_ha_installer_*` tiles documented in the
           manifest's `dashboard.tiles` list — `input_text`
           ref + `input_text` at + `input_text`
           installed_repo + 2 `input_button` run_install +
           run_uninstall + `input_text` last_error +
           `input_boolean` backups_enabled + `sensor`
           status + `sensor` files_installed_count +
           `binary_sensor` installed_assets_match_repo
           = 10 contract entities)
        -> dashboard tiles + operator queries
            ("is RoamCore installed?",
             "which ref is installed?",
             "when was it last installed?",
             "which repo was used?",
             "how many files are installed?",
             "do the installed assets match the repo?",
             "is the install stale?",
             "what was the last error?",
             "run install now",
             "run uninstall now")

    Safety interlocks (the recipe is the contract layer;
    the automation wrappers are documented in §8):
        -> The RoamCore install-button guard is the §8.1
           automation that fires when
           `input_button.rc_ha_installer_run_install` is
           pressed. The button press marks `sensor.
           rc_ha_installer_status = Install-Running` and
           clears any stale `input_text.rc_ha_installer_
           last_error`. The actual install work happens
           via the `shell_command.rc_ha_installer_run_
           install` wrapper that runs the canonical
           installer script (the integration layer can't
           run shell scripts from a button press in HA
           core without a `shell_command:` wrapper, which
           IS what this automation wires).
        -> The RoamCore uninstall-button guard is the §8.2
           automation that fires when
           `input_button.rc_ha_installer_run_uninstall`
           is pressed. The button press marks `sensor.
           rc_ha_installer_status = Uninstall-Running`
           and clears the manifest + install-info state
           (`/config/.roamcore/manifest.txt` is truncated
           + `/config/.roamcore/install-info.txt` is
           cleared). The actual uninstall work happens via
           the `shell_command.rc_ha_installer_run_
           uninstall` wrapper.
        -> The RoamCore stale-version detector is the §8.3
           automation that fires when `input_text.
           rc_ha_installer_installed_ref` differs from
           the configured `ROAMCORE_REF` for > 7 days. The
           automation marks `sensor.rc_ha_installer_status
           = Stale-Version` and surfaces a "RoamCore is
           outdated" notification chip. The 7-day
           threshold is operator-tunable via the
           `input_number.rc_ha_installer_stale_version_
           days_threshold` helper (default 7).
        -> The RoamCore installed-assets-match-repo
           guard is the §8.4 automation that fires when
           `sensor.rc_ha_installer_files_installed_count`
           differs from the count of files in the current
           repo's `homeassistant/` inventory. The
           automation marks `binary_sensor.
           rc_ha_installer_installed_assets_match_repo =
           false` and surfaces a "RoamCore install is
           incomplete" notification. The repo file count
           is derived from the operator's RoamCore clone
           (the RoamCore-side canonical inventory, NOT the
           HA `/config/` manifest).
        -> The RoamCore install-failure capture guard is
           the §8.5 automation that fires when the
           `shell_command:` wrapper exits non-zero. The
           automation captures stderr into `input_text.
           rc_ha_installer_last_error` and marks `sensor.
           rc_ha_installer_status = Failed`. The
           `shell_command:` wrapper writes its exit code
           to a sentinel file at `/config/.roamcore/
           last-exit-code` that the automation polls.

    Cross-references:
        -> The RoamCore-owned installer scripts at repo
           root (`install.sh` + `uninstall.sh`) are the
           canonical entry points for the operator-facing
           one-line install / uninstall flows.
        -> The RoamCore-owned installer scripts at
           `homeassistant/install.sh` + `homeassistant/
           uninstall.sh` are the canonical HA-only
           installer + uninstaller (the root scripts are
           thin wrappers that delegate to these).
        -> The operator howto at
           `docs/howto/homeassistant-installer.md`
           (108 lines) is the canonical operator-walk
           through the one-line install + the 5
           directories copied + the 3 state files
           written + the uninstall one-liner + the 5
           verification steps + the RC_API_TOKEN-aware
           wiring guidance.
        -> The HA smoke check at
           `scripts/checks/ha-beta-smoke.sh` is the
           canonical smoke check for the installer
           surface (validates the installer scripts
           exist + are syntactically correct + the
           operator howto exists + the 5 directories
           are present in the repo).
        -> The trip-local Wave 3 #68 connection cross-
           references the installer because the
           installer copies the trip-local package
           (`homeassistant/packages/roamcore_trip_
           local.yaml`) into HA `/config/packages/`.
        -> The trip-wrapped Wave 3 #69 connection cross-
           references the installer because the
           installer copies the trip-wrapped package
           (`homeassistant/packages/roamcore_trip_
           wrapped.yaml`) + the trip-wrapped tools
           (`homeassistant/tools/trip_wrapped/`) into
           HA `/config/`.
        -> The openclaw-api Wave 3 #64 connection cross-
           references the installer because the
           installer copies the roamcore_openclaw_api
           custom component (`homeassistant/custom_
           components/roamcore_openclaw_api/`) into
           HA `/config/custom_components/`.
        -> The bed-lift-diy Wave 3 #70 connection cross-
           references the installer because the
           installer copies the bed-lift-diy package
           (`homeassistant/packages/roamcore_bed_
           lift_diy.yaml`) into HA `/config/packages/`.

See docs/recipe.md for the full howto (the existing
installer scripts + the FIVE-step operator flow + the 10
`rc_ha_installer_*` contract tiles + the FIVE §8
MANDATORY automations + the 6 §10 troubleshooting entries
+ privacy + tier-a promotion outline).
"""

DOMAIN = "ha_installer"
