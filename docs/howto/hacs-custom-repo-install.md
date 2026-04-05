# HACS install (beta) — Custom Repository

This is the **beta** HACS path for RoamCore.

It makes RoamCore discoverable *inside your Home Assistant UI* via HACS, without requiring RoamCore to be listed in the default HACS store yet.

## Prerequisites

- Home Assistant installed and running.
- HACS installed: https://hacs.xyz/

## Add RoamCore as a Custom Repository

1) Open **HACS** in Home Assistant.
2) Go to **Integrations**.
3) Open the menu (⋮) → **Custom repositories**.
4) Add:
   - Repository: `https://github.com/roamcore/RoamCore`
   - Category: **Integration**

## Install

1) In HACS → Integrations, search for **RoamCore**.
2) Install it.
3) Restart Home Assistant.
4) Add the integration:
   - Settings → Devices & services → Add integration → **RoamCore**

## Provision RoamCore assets (packages, dashboards, tools)

HACS installs the RoamCore **integration** (`custom_components/roamcore`).

### Automatic provisioning (recommended)

By default, when you add the RoamCore integration, it will **auto-provision** the rest of the RoamCore assets into `/config` on first run.

After it completes, RoamCore will show a persistent notification asking you to restart Home Assistant.

This is controlled by the integration option:

- `auto_provision_assets` (default: true)

### Manual provisioning (fallback)

RoamCore also includes additional assets (packages, Lovelace YAML, `/www/roamcore/*`, tools). To install those automatically, run the RoamCore provisioning service once:

Developer Tools → Services → call:

```yaml
service: roamcore.provision_assets
data:
  repo: https://github.com/roamcore/RoamCore
  ref: main
```

This downloads the repo archive and installs:

- `homeassistant/packages/*` → `/config/packages/*`
- `homeassistant/custom_components/*` → `/config/custom_components/*`
- `homeassistant/www/*` → `/config/www/*`
- `homeassistant/lovelace/*` → `/config/lovelace/*`
- `homeassistant/tools/*` → `/config/tools/*`

It also writes state/backups under:

- `/config/.roamcore/manifest.txt`
- `/config/.roamcore/backups/<timestamp>/...`

After provisioning, restart HA again so packages/components are loaded.

## Verify

- OpenClaw summary endpoint (optional):
  - `http://<ha>:8123/api/roamcore/openclaw/summary`
- Confirm RoamCore contract entities exist (Developer Tools → States):
  - `sensor.rc_power_battery_soc`
  - `sensor.rc_level_pitch_deg`

## Notes

- This repo also supports a one-line installer if you prefer not to use HACS:
  - `docs/howto/homeassistant-installer.md`
