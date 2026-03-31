# Installation (HA-only beta)

This guide documents the **HA-only** install path for RoamCore.

RoamCore installs as:
- Home Assistant **packages** (YAML) → `/config/packages/roamcore_*.yaml`
- Web assets (Map / UI helpers) → `/config/www/roamcore/…` (served as `/local/roamcore/…`)
- A reference Lovelace dashboard YAML → `/config/lovelace/roamcore-dashboard.yaml`

## Prerequisites

- Home Assistant with access to the `/config` filesystem (HAOS recommended).
- The `packages:` feature enabled in your Home Assistant configuration.

> Note: These instructions assume you are running the command inside Home Assistant
> (e.g. via the **SSH & Web Terminal** add-on) so `/config` is available.

## One-line install

```bash
curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/scripts/install/ha/install.sh | bash
```

## Post-install steps

1) Restart Home Assistant.
2) Add the RoamCore dashboard:
   - Settings → Dashboards → Add Dashboard → From YAML / From file
   - File: `/config/lovelace/roamcore-dashboard.yaml`
3) Verify a few core entities exist (Developer Tools → States):
   - `sensor.rc_power_battery_soc`

## Uninstall

```bash
curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/scripts/install/ha/uninstall.sh | bash
```
