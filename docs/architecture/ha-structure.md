# Home Assistant structure

Date: 2026-02-02

## Environment

- Host: HA VM (VMID 101)
- UI: `http://192.168.1.67:8123`
- `/config` → `/homeassistant` (symlink)

## Recommended config layout (repo)

GitHub canonical structure:

- `ha/config/`
  - `packages/`
  - `automations/`
  - `scripts/`

Runtime HA config lives inside the VM under `/config`.

## Sync philosophy

- Prefer YAML/config over UI-only state where possible.
- UI-only changes must be documented (and mirrored back into YAML when feasible).

