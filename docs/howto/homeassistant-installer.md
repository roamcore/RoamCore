# Home Assistant (HAOS) one-line installer

This installs the **HA-only** RoamCore assets (YAML packages, custom components, and Lovelace/dashboard JS) into your Home Assistant `/config` directory.

It is intended for HAOS users with the **SSH add-on** enabled.

## Install (one line)

Run on the HA host (eg via *Terminal & SSH* add-on):

```sh
curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh | sh
```

Install a specific tag/commit:

```sh
ROAMCORE_REF=v0.1.0 \
  curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh | sh
```

### What it copies

From this repo’s `homeassistant/` folder into HA’s `/config`:

- `homeassistant/packages/*` → `/config/packages/*`
- `homeassistant/custom_components/*` → `/config/custom_components/*`
- `homeassistant/www/*` → `/config/www/*`  
  (RoamCore JS ends up at `/config/www/roamcore/*.js`, served as `/local/roamcore/*.js`)
- `homeassistant/lovelace/*` → `/config/lovelace/*`
- `homeassistant/tools/*` → `/config/tools/*`
  (used by local exporters like Trip Wrapped)

The installer writes state to:

- `/config/.roamcore/manifest.txt` (list of installed files)
- `/config/.roamcore/install-info.txt` (what ref was installed)
- `/config/.roamcore/backups/<timestamp>/…` (copies of any overwritten files)

## Uninstall (one line)

```sh
curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/uninstall.sh | sh
```

## Verification steps

1. **Restart Home Assistant** (Settings → System → Restart) so packages and custom components are reloaded.
2. Confirm files exist on disk:

   ```sh
   ls -la /config/packages | grep roamcore
   ls -la /config/custom_components | grep roamcore
   ls -la /config/www/roamcore
   ```

3. In HA UI:
   - Developer Tools → **YAML**: reload *Template Entities* / *Automations* (if you prefer not to restart).
   - Settings → Devices & services: confirm any RoamCore custom integrations appear/initialize.
4. Optional API probe (from a machine with an HA token) using the repo helper:
   - `scripts/ha/check-rc-entities.sh`

5. Open the RoamCore dashboard and complete first-run setup:
   - Dashboard: `/roamcore/home`
   - Setup wizard: `/roamcore/setup`
   - Optional: enable **RC Demo Mode** (`input_boolean.rc_demo_mode`) to preview the UI even if critical sensors are still missing.

## Optional: Native dashboard (no custom JS)

RoamCore ships two dashboards:

- **Custom dashboard** (recommended): `homeassistant/lovelace/roamcore-dashboard.yaml` (uses RoamCore JS cards)
- **Native dashboard** (easy to edit): `homeassistant/lovelace/roamcore-dashboard-native.yaml` (built-in cards only)

To use the native dashboard, create a new Lovelace dashboard in HA and point it at:

- `/config/lovelace/roamcore-dashboard-native.yaml`

This is additive; keep the custom dashboard too.

## Securely storing API keys / tokens (beta)

RoamCore avoids storing real secrets in Lovelace YAML.

For beta, RoamCore provides a Home Assistant service that can safely write a key/value into `/config/secrets.yaml` using an atomic update (so you don't need to SSH in and edit files manually).

### Save a Traccar user token

1) Open the RoamCore Setup Wizard view.
2) Paste the token.
3) Tap **Save token securely**.

Under the hood this calls:

```yaml
service: roamcore.secrets_set
data:
  key: roamcore_traccar_user_token
  value: "<TOKEN>"
```

This writes to:

```yaml
roamcore_traccar_user_token: "..."
```

Note: tokens are still stored as plaintext in `secrets.yaml` (like all HA secrets), but they are not committed to git, not embedded in dashboards, and RoamCore avoids logging them.
