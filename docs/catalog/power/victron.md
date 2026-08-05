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

## Bench testing

Want to verify the Victron integration works end-to-end on your dev box? The bench runs the real addon against a real MQTT broker, publishes fake Venus OS topics, and asserts that Home Assistant MQTT Discovery entities appear correctly.

### Install

```bash
pip3 install paho-mqtt pytest pytest-asyncio amqtt
```

(If you have the `mosquitto` binary on `$PATH` the bench uses it; otherwise it uses the pure-Python `amqtt` broker so no system install is required.)

### Run

```bash
bash scripts/checks/victron-bench-smoke.sh
```

### What the bench covers

End-to-end round-trip from `N/<portal>/system/0/Soc` → `sensor.vt_battery_soc_percent` discovery → retained state topic → the `sensor.rc_power_battery_soc` Jinja tile in `homeassistant/packages/roamcore_power.yaml`. It also verifies recovery after a broker restart and that errors are surfaced in plain English ("Victron GX not found on your network — check the cable and the IP"), not raw Python tracebacks.

### Run against a real Victron GX

Set `victron_host=<your-gx-ip>` and `victron_portal_id=<your-portal-id>` in the add-on options. The bench smoke script is still useful as a CI gate even when you run against real hardware.

### Troubleshooting

See `homeassistant/addons/roamcore-victron-auto/tests/README.md` for the full setup, troubleshooting, and developer documentation.
