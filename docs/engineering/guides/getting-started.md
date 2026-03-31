# Getting started

This guide is a practical “where do I start?” for RoamCore **HA-only beta**.

## What RoamCore is

RoamCore is a mobile-first Home Assistant experience for vans and off-grid rigs.
It provides a cohesive dashboard (power, map, levelling, weather, exports) while keeping everything **local-first** and **extensible**.

## Supported environments (beta)

- **Home Assistant OS (HAOS)** on any supported hardware (recommended).
- Home Assistant Supervised / Container installs can work if you have filesystem access to the HA config directory.

## Install

Follow the HA-only one-line installer:

- `docs/howto/homeassistant-installer.md`

## First setup checklist (beta)

1) **Install RoamCore assets** into `/config` (packages, web assets, dashboard YAML).
2) **Restart Home Assistant**.
3) Open the RoamCore dashboard and confirm:
   - Power cards show (mock values are fine initially).
   - Map renders a basemap (should never be a grey canvas).
   - Levelling entities exist (`sensor.rc_level_pitch_deg`, `sensor.rc_level_roll_deg`).
4) Connect real sources as desired:
   - Victron: install/configure the Victron path you’re using; RoamCore maps those into stable `rc_*` entities.
   - GPS / trip tracking: configure Traccar (see `docs/setup/traccar.md`).

## How it stays stable

RoamCore’s UI is built on stable **contract entities** (`rc_*`).
That means:
- you can swap underlying vendors/hardware,
- without breaking dashboards/automations,
- and without changing OpenClaw’s JSON API.
