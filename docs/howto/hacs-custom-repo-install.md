# HACS install (beta) — Custom Repository

This is the **beta** HACS path for RoamCore.

It makes RoamCore discoverable *inside your Home Assistant UI* via HACS, without requiring RoamCore to be listed in the default HACS store yet.

> **Wave 2 #19 note:** the HACS package is now polished for default-store
> review. The repo root `hacs.json` declares all three RoamCore
> integrations (`roamcore`, `roamcore_tileserver`, `roamcore_traccar_proxy`),
> the primary integration ships an HACS `info.md` + `branding/` icon and
> logo, and each sub-integration ships its own `hacs.json`. A new
> `scripts/checks/hacs-packaging-smoke.sh` runs as part of
> `scripts/check.sh --core-only` to keep the package honest.

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

HACS will now see **three** RoamCore integrations under one repository:

- **RoamCore** — the primary integration (config flow, auto-provision,
  OpenClaw JSON API, support bundle, dashboard wiring).
- **RoamCore Tile Server** — optional add-on integration that bridges the
  HAOS tileserver into the dashboard.
- **RoamCore Traccar Proxy** — optional add-on integration that proxies
  Traccar device data into RoamCore contract sensors.

Only **RoamCore** is required to be installed. Install the other two
only if you intend to use the tile server and/or the Traccar proxy in
your setup.

## Install

1) In HACS → Integrations, search for **RoamCore**.
2) Install it.
3) Restart Home Assistant.
4) Add the integration:
   - Settings → Devices & services → Add integration → **RoamCore**

## HACS metadata surfaced to users

When HACS shows the RoamCore integration in the UI, it reads:

- `homeassistant/custom_components/roamcore/info.md` — the integration
  description / install / usage page (this is the polished Wave 2 #19
  metadata).
- `homeassistant/custom_components/roamcore/branding/icon.png` — the
  integration icon (≥256×256 PNG).
- `homeassistant/custom_components/roamcore/branding/logo.png` — the
  integration logo (≥256×256 PNG).
- `homeassistant/custom_components/roamcore/manifest.json` — `domain`,
  `name`, `version`, `codeowners`, `iot_class`, etc.

The repo-root `hacs.json` declares the repository as a HACS custom-repo
with `content_in_root: false`, `country: "ALL"`, and all three
`domains`.

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
- Confirm HACS sees all three integrations:
  - HACS → Integrations → search for "RoamCore" — should list
    RoamCore, RoamCore Tile Server, and RoamCore Traccar Proxy.

## Notes

- This repo also supports a one-line installer if you prefer not to use HACS:
  - `docs/howto/homeassistant-installer.md`
- The HACS package is validated on every push by
  `scripts/checks/hacs-packaging-smoke.sh` (wired into
  `scripts/check.sh --core-only`).
