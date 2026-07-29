# Hardware auto-discovery (local LAN)

**Support tier:** B (RoamCore native)

## What this is
RoamCore ships a stdlib-Python helper that surveys the local LAN for each add-on RoamCore already has a connection for (OpenWrt, tileserver, Traccar, Victron, OTA) and exposes a `binary_sensor.rc_hardware_<addon>_available` per add-on. The Setup Wizard renders a "Hardware" card with a one-tap "Set up" CTA per discovered row.

## Why it's useful in a van
- See at a glance what's already reachable without opening five tabs
- One-tap "Set up" instead of remembering which helper or URL to flip
- All probing is local — nothing leaves the device

## Extra hardware required
- None (the helper works against any RFC1918 / loopback target RoamCore already knows about)

## Install / best next step
- See: `docs/setup/hardware-auto-discovery.md`

## RoamCore Hardware auto-discovery
- Built-in: `docs/setup/hardware-auto-discovery.md`
- Contract package: `homeassistant/packages/roamcore_hardware_discovery.yaml`
- Wizard snippet: `homeassistant/packages/roamcore_setup_wizard_hardware_discovery.yaml`
- Probe helper: `homeassistant/tools/hardware_discovery/probe.py` (stdlib-only)
- Smoke check: `scripts/checks/hardware-auto-discovery-smoke.sh` (privacy invariant + 39 assertions)

## Links
- (Add videos/quickstart)