# RoamCore Victron Mock (DEV add-on)

This is a **development-only** Home Assistant add-on that publishes **mock Victron Venus OS MQTT topics** into the Home Assistant Mosquitto broker.

Use it when you **do not have a real GX/Venus device on the LAN**, but want to validate:
- `roamcore-victron-auto` MQTT ingest
- vt_* entity publishing via MQTT Discovery
- UI wiring / dashboards

## Safety / removal

- It is designed to be **easy to remove**.
- To remove it, uninstall the add-on from Home Assistant.
- It only publishes to MQTT; it does not modify HA configuration.

## Install (local add-on)

1. Ensure Home Assistant has the local add-ons directory enabled (`/addons/local`).
2. Copy this folder to HA:
   - `RoamCore/homeassistant/addons/roamcore-victron-mock/` → `/addons/local/roamcore-victron-mock/`
3. Reload the Supervisor store.
4. Install **RoamCore Victron Mock (DEV)**.

## Configure

Options:
- `portal_id`: string identifier used in topic paths (default: `mock-portal`)
- `publish_interval_sec`: how often to publish the topic set (default: 5)
- `retain`: whether messages should be retained (default: true)

## What it publishes

It publishes a small subset of Venus-style topics, e.g.:

- `N/<portal_id>/system/0/Serial`
- `N/<portal_id>/system/0/Model`
- `N/<portal_id>/system/0/FirmwareVersion`
- `N/<portal_id>/vebus/0/ProductId`
- `N/<portal_id>/solarcharger/0/ProductId`

These are sufficient to exercise discovery + mapping logic in `roamcore-victron-auto`.

