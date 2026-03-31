# Home Assistant (HAOS) one-line installer

This installs the **HA-only** RoamCore assets (YAML packages, custom components, and Lovelace/dashboard JS) into your Home Assistant `/config` directory.

It is intended for HAOS users with the **SSH add-on** enabled.

## Install (one line)

Run on the HA host (eg via *Terminal & SSH* add-on):

```sh
curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/homeassistant/install.sh | sh
```

Install a specific tag/commit:

```sh
ROAMCORE_REF=v0.1.0 \
  curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/homeassistant/install.sh | sh
```

### What it copies

From this repo’s `homeassistant/` folder into HA’s `/config`:

- `homeassistant/packages/*` → `/config/packages/*`
- `homeassistant/custom_components/*` → `/config/custom_components/*`
- `homeassistant/www/*` → `/config/www/*`  
  (RoamCore JS ends up at `/config/www/roamcore/*.js`, served as `/local/roamcore/*.js`)
- `homeassistant/lovelace/*` → `/config/lovelace/*`

The installer writes state to:

- `/config/.roamcore/manifest.txt` (list of installed files)
- `/config/.roamcore/install-info.txt` (what ref was installed)
- `/config/.roamcore/backups/<timestamp>/…` (copies of any overwritten files)

## Uninstall (one line)

```sh
curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/homeassistant/uninstall.sh | sh
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

