<!-- SUPERSEDED: This legacy stub is superseded by the tier-b recipe connection at `connections/remote-access/`. The legacy 23-line Tailscale stub listed ONLY Tailscale at "Support tier: B" with no recipe + no contract + no broader vendor-neutral coverage — just a placeholder about "Tailscale is a simple, secure mesh VPN. It's a great way to access Home Assistant remotely without opening ports or relying on complex networking". The tier-b recipe connection promotes Tailscale as Path A of FOUR operator-pickable paths (Path A Tailscale mesh VPN + Path B Cloudflare Tunnel no-inbound-ports + Path C Nabu Casa HA Cloud official cloud relay + Path D Wireguard self-hosted VPN) + lifts the Wave 2 #29 Tailscale contract (`feat/wave2-remote-access-tailscale` @ `0caa9c2`) into the `connections/` pipeline + adds the broader vendor-neutral contract layer. See `connections/remote-access/README.md` for the new connection overview + `connections/remote-access/docs/recipe.md` for the full howto. See `Cron-handoff/2026-08-02-remote-access-connection.md` for the slice handoff. -->

# Tailscale (secure remote access)

**Support tier:** B (Home Assistant supported)

## What this is
Tailscale is a simple, secure mesh VPN. It's a great way to access Home Assistant remotely without opening ports or relying on complex networking.

## Why it's useful in a van
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
- Wave 3 #58 vendor-neutral remote-access umbrella (this slice): `connections/remote-access/`
- Wave 2 #29 Tailscale contract (`feat/wave2-remote-access-tailscale` @ `0caa9c2`): `homeassistant/packages/roamcore_remote_access.yaml`