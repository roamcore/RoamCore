# RoamCore OpenWrt Networking Stack (MVP)

This folder contains the **OpenWrt-side** configuration and scripts for the RoamCore MVP networking stack.

## Principles

- **Parameterised**: we keep the “product spec” defaults (e.g. `10.0.0.0/24`) but allow overrides for dev/lab environments.
- **Idempotent**: scripts should be safe to re-run.
- **No secrets in git**: no SIM PINs, Wi‑Fi passwords (beyond default placeholders), tokens, or API credentials.

## Files

- `vars.example.env` — example variables you can copy to `vars.env` (not committed) to override defaults.
- `install_packages.sh` — installs required OpenWrt packages (mwan3, vnstat, python3, etc.).
- `apply_config.sh` — applies the UCI config (network/dhcp/firewall/wireless/mwan3) using variables.
- `api/` — RoamCore Networking API (OpenWrt local HTTP API on port 8080).
- `verify.sh` — smoke tests to confirm stack health.

## Usage (dev)

```sh
cd /opt/roamcore/netstack
cp vars.example.env vars.env
vi vars.env

./install_packages.sh
./apply_config.sh
./verify.sh
```

## Adding auth later

The API is LAN-only for MVP. The implementation is designed so we can add an optional header token later (e.g. `X-RoamCore-Token`) without breaking existing HA configs.

