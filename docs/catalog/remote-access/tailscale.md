# Tailscale (secure remote access)

**Support tier:** B (Home Assistant supported)

## What this is
Tailscale is a simple, secure mesh VPN. It’s a great way to access Home Assistant remotely without opening ports or relying on complex networking.

## Why it’s useful in a van
- Check your van systems from anywhere
- More reliable than port-forwarding on mobile networks
- Useful for remote debugging/support

## Extra hardware required
- None

## Install / best next step
Two related options:
- HA **integration** (monitor your tailnet)
- HA **add-on/app** (actually puts HA on your tailnet for remote access)

## Links
- Home Assistant Tailscale integration: https://www.home-assistant.io/integrations/tailscale/
- Home Assistant Community Tailscale add-on: https://github.com/hassio-addons/app-tailscale

## Installed in RoamCore

RoamCore ships a contract layer that wraps the HA core Tailscale
integration — see `homeassistant/packages/roamcore_remote_access.yaml`:

- One boolean kill-switch: `input_boolean.rc_remote_access_enabled`
- One text field for the tailnet host: `input_text.rc_remote_access_tailnet_host`
- `binary_sensor.rc_remote_access_active`, `sensor.rc_remote_access_url`,
  `sensor.rc_remote_access_peer_count`, `sensor.rc_remote_access_last_seen`

RoamCore does **not** ship a separate Tailscale client. The HA core
integration is the only Tailscale client in the system.
