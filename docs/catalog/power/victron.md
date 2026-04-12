# Victron power monitoring (GX + MQTT)

**Support tier:** A (RoamCore native)

## What this is
RoamCore includes a Victron integration path that turns your Victron GX + battery/solar system into clean Home Assistant entities (SOC, solar watts, etc.) and dashboard tiles.

## Why it’s useful in a van
- See battery SOC and solar input at a glance
- Catch charging/inverter issues early
- Build simple automations like “low battery alert” without custom code

## Extra hardware required
- A Victron GX device (e.g. Cerbo GX) or equivalent that can publish telemetry
- Your existing Victron battery/solar hardware

## Install / best next step
- See: `docs/runbooks/victron-integration.md`
- See: `docs/guides/victron-connect-flow.md`
- HA packages:
  - `homeassistant/packages/roamcore_power.yaml`
  - `homeassistant/packages/roamcore_victron_health.yaml`

## Links
- (Add Victron docs / MQTT notes / videos here later)
