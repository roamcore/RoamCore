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

## Verify

- OpenClaw summary endpoint (optional):
  - `http://<ha>:8123/api/roamcore/openclaw/summary`
- Confirm RoamCore contract entities exist (Developer Tools → States):
  - `sensor.rc_power_battery_soc`
  - `sensor.rc_level_pitch_deg`

## Notes

- This repo also supports a one-line installer if you prefer not to use HACS:
  - `docs/howto/homeassistant-installer.md`

