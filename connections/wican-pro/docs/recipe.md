# Wicann Pro setup recipe

**Tier:** B (recipe)
**Audience:** A RoamCore user who already has a Home Assistant install
with the MQTT integration configured, and a MeatPi WiCAN Pro plugged
into their vehicle's OBD2 port.

This howto is mirrored at `docs/howto/wican-pro-setup.md` so it shows up
under the public docs site's "How-to" section. Keep them in sync — the
build_catalog script only regenerates `docs/connections/<id>.md`, not
this recipe.

## What you'll need

- A **MeatPi WiCAN Pro** (or compatible ESP32 OBD2 adapter running the
  upstream `wican-fw` firmware). Plugged into the vehicle.
- Your vehicle reachable from your HA host's network. The WiCAN
  defaults to joining your home Wi-Fi — if your vehicle parks out of
  range, you'll need a travel router or phone hotspot fallback.
- An MQTT broker reachable from the WiCAN. Mosquitto on the RoamCore
  broker, or HA's Mosquitto add-on.
- A `mqtt:` entry in `configuration.yaml` (or the MQTT integration
  configured via UI — both work).

## Path A: MQTT (recommended for RoamCore)

This is the path the RoamCore dashboard tiles expect. The WiCAN
firmware publishes OBD telemetry to your broker with HA's MQTT auto-
discovery format, and RoamCore's contract layer reads the resulting
sensors.

### A.1 — Configure the WiCAN firmware

Through the WiCAN's web UI (default `http://wican.local/` once it's
joined your Wi-Fi), enable MQTT and point it at your broker:

| Field | Value |
|-------|-------|
| MQTT broker host | your-roamcore-broker.lan (or IP) |
| MQTT broker port | 1883 (TLS: 8883) |
| Username / password | your MQTT creds |
| Client id | `wican-pro-<vehicle-slug>` |
| Home Assistant auto-discovery | **enabled** |
| Discovery prefix | `homeassistant` (the HA default) |
| State topic prefix | `wican/<vehicle-slug>/state` |

Use a short vehicle slug — e.g. `sprinter`, `transit`, `rigid`. The
slug appears in every entity id and in the published MQTT topic tree,
so keep it stable.

### A.2 — Map WiCAN sensors to RoamCore contract ids

The WiCAN publishes auto-discovery payloads with a configurable
`object_id`. The RoamCore contract expects these sensor ids (see
[`docs/reference/rc-entity-naming.md`](../../../reference/rc-entity-naming.md)):

| OBD PIDs / WiCAN signal | RoamCore contract entity |
|-------------------------|--------------------------|
| Battery voltage (PID 0x42) | `sensor.rc_vehicle_battery_voltage` |
| Coolant temperature (PID 0x05) | `sensor.rc_vehicle_coolant_temp` |
| Vehicle speed (PID 0x0D) | `sensor.rc_vehicle_speed` |

In the WiCAN web UI, under **Per-PID mapping**, override each of those
PIDs' `object_id` to the `rc_vehicle_*` form above. The WiCAN will
then publish HA discovery payloads like:

```yaml
# Topic: homeassistant/sensor/wican-pro/rc_vehicle_battery_voltage/config
# (published once at boot; HA picks it up automatically)
name: "Vehicle Battery"
state_topic: "wican/sprinter/state/rc_vehicle_battery_voltage"
unique_id: "wican-pro-sprinter-rc_vehicle_battery_voltage"
unit_of_measurement: "V"
device_class: voltage
state_class: measurement
device:
  identifiers: ["wican-pro-sprinter"]
  name: "WiCAN Pro (Sprinter)"
  manufacturer: "MeatPi"
  model: "WiCAN Pro"
  sw_version: "1.4.2"
```

After saving the WiCAN config and rebooting it, the three contract
sensors should appear in HA within ~30 seconds. Reload the RoamCore
dashboard — the `rc_vehicle_*` tiles start populating as soon as the
ignition is on and the OBD2 bus is awake.

### A.3 — Optional: alert on overheating or low voltage

Suggested automation starter (drop into `automations.yaml`):

```yaml
- id: rc_vehicle_engine_overheat_alert
  alias: "Vehicle: engine overheat warning"
  trigger:
    - platform: numeric_state
      entity_id: sensor.rc_vehicle_coolant_temp
      above: 105      # °C — adjust for your vehicle's normal range
      for: "00:00:30"
  action:
    - service: persistent_notification.create
      data:
        title: "Engine overheating"
        message: >-
          Coolant temperature is {{ states('sensor.rc_vehicle_coolant_temp') }} °C.
          Pull over and idle for 2-3 minutes before shutting off.
    - service: notify.all_admins
      data:
        title: "Engine overheat"
        message: "Coolant at {{ states('sensor.rc_vehicle_coolant_temp') }} °C"
```

## Path B: ha-wican (HACS HTTP integration)

If you'd rather not run an MQTT broker — for example, your WiCAN lives
on a different VLAN or your HA is brokerless — the community
[`ha-wican`](https://github.com/jay-oswald/ha-wican) HACS integration
talks to the WiCAN's built-in HTTP API.

### B.1 — Install ha-wican via HACS

1. HACS → Integrations → Custom repositories → add
   `https://github.com/jay-oswald/ha-wican` (category: Integration).
2. Install `ha-wican` and restart HA.
3. Settings → Devices & Services → Add Integration → "WiCAN" → enter
   your WiCAN's hostname or IP.

`ha-wican` will create entities like `sensor.wican_pro_battery_voltage`
(vehicle-specific).

### B.2 — Map to the RoamCore contract

The WiCAN entities won't match RoamCore's contract out of the box, so
add a `template:` block to `configuration.yaml` that aliases them:

```yaml
template:
  - sensor:
      - name: "rc_vehicle_battery_voltage"
        unique_id: rc_vehicle_battery_voltage_wican_pro
        unit_of_measurement: "V"
        device_class: voltage
        state_class: measurement
        state: "{{ states('sensor.wican_pro_battery_voltage') }}"
      - name: "rc_vehicle_coolant_temp"
        unique_id: rc_vehicle_coolant_temp_wican_pro
        unit_of_measurement: "°C"
        device_class: temperature
        state_class: measurement
        state: "{{ states('sensor.wican_pro_coolant_temp') }}"
      - name: "rc_vehicle_speed"
        unique_id: rc_vehicle_speed_wican_pro
        unit_of_measurement: "km/h"
        state_class: measurement
        state: "{{ states('sensor.wican_pro_speed') | float(0) }}"
```

Reload template entities, then reload the RoamCore dashboard.

> **Why the alias?** RoamCore tiles bind to the `rc_vehicle_*` contract
> ids (per [`docs/reference/rc-entity-naming.md`](../../../reference/rc-entity-naming.md)).
> If you ever swap the WiCAN for a different OBD2 adapter (OBDLink,
> Vgate iCar Pro, etc.) you only re-template; the dashboard stays put.

## Verifying it works

1. **HA → Developer Tools → States** — search for `rc_vehicle_`. You
   should see at least `battery_voltage`, `coolant_temp`, and `speed`
   once the ignition is on and OBD2 is responsive.
2. **RoamCore dashboard** — the Vehicle section gains three tiles
   showing live values within a few seconds of the vehicle waking up
   the OBD2 bus.
3. **OpenClaw** — ask your agent "is the engine overheating?" or
   "what's the vehicle battery voltage right now?". You should get a
   real answer from `sensor.rc_vehicle_*`.

## Troubleshooting

- **No entities appear** — check the WiCAN's MQTT logs (web UI →
  Logs) and your broker's connection logs. Most "missing sensor"
  reports trace back to a wrong username/password or a firewall
  blocking the WiCAN's outbound 1883/8883.
- **Entities appear but stay `unavailable`** — the WiCAN hasn't
  heard an OBD2 response in the configured timeout. Check the OBD2
  connector is fully seated and the ignition is on (some vehicles
  don't power the OBD2 bus in accessory mode).
- **Wrong unit / scale** — the WiCAN firmware lets you scale each
  PID; the RoamCore contract expects volts, °C, and km/h. If your
  vehicle publishes in mph or Fahrenheit, scale in the firmware or
  convert in a template sensor.
- **`object_id` collisions** — if you already have other HA
  integrations publishing `sensor.rc_vehicle_*` (e.g. a different
  vehicle's OBD2 reader), the entity_id allocator suffixes `_2`,
  `_3`, etc. Rename your non-WiCAN ones, or namespace the WiCAN with
  a vehicle slug in its `object_id` (e.g.
  `rc_vehicle_sprinter_battery_voltage`).

## What we *can't* help with (tier-b honesty)

- We don't have a real WiCAN device on the bench, so this recipe is
  not integration-tested end-to-end. The MQTT payload shape is the
  documented upstream default; if MeatPi changes the discovery
  payload format in a future firmware release, you'll need to
  re-validate it.
- The `ha-wican` mapping example assumes that integration's entity
  naming (`sensor.wican_pro_battery_voltage`). If jay-oswald renames
  his entities, update the template block.
- This recipe does not cover J1939 (heavy-duty trucks), only the
  OBD2 PID surface that the WiCAN exposes by default.

## Promoting to tier-a (future)

When a real WiCAN device lands on the bench:

1. Add `config_flow.py` that scans the LAN for `wican-*.local`
   mDNS entries and offers a one-tap wizard.
2. Add an integration test that points at a mock WiCAN REST
   endpoint (`pytest-homeassistant-custom` style).
3. Flip the manifest to `tier: a`, add `working_config_flow` +
   `integration_test_passes` + `no_manual_yaml_required` to
   `tier_requirements`, and add the missing tier-a fixture files.
4. Re-run `python3 scripts/audit_connections.py` — should go clean
   with zero warnings for `wican-pro`.

The recipe on this page stays useful as a fallback for users who
prefer MQTT or HACS over the one-tap path.