# scripts/

Operational scripts and build helpers (repo-local tooling).

Top folders:
- `install/` — installer wrappers and provisioning helpers
- `ha/` — Home Assistant-facing helper scripts
- `tiles/` — PMTiles/tiles build & extraction tooling
- `traccar/` — Trip/Traccar utilities
- `checks/` — smoke tests / sanity checks
- `backups/` — backup helpers
- `proxmox/` — Proxmox/VM utilities
- `provisioning/` — bring-up/provisioning helpers
- `tools/` — small one-off utilities (moved from top-level `tools/`)

Rule of thumb:
- anything user-facing and deployed to the HA box lives under `homeassistant/`
- anything developer/operator-facing lives here.
