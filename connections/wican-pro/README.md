# Wicann Pro (MeatPi WiCAN Pro)

**Tier:** B (recipe)
**Category:** Vehicle OBD
**Status:** beta

## What this connection is

MeatPi WiCAN Pro is an OBD2 + CAN-bus adapter (ESP32-based) that sits in
your vehicle's diagnostic port and streams telemetry over your local Wi-Fi
or LAN: battery voltage, coolant temperature, speed, RPM, fault codes,
trip metrics — depending on what your vehicle exposes.

In RoamCore this is a **tier-b recipe connection**: we publish a setup
guide, you wire it up, and your dashboard gains the `rc_vehicle_*`
contract tiles. There is no native RoamCore config-flow for the WiCAN
device itself — we lean on HA's core `mqtt` integration or the community
`ha-wican` HACS integration instead.

## Setup recipe (one-paragraph)

1. Plug the WiCAN Pro into the OBD2 port (USB power optional, draws from
   the bus when the ignition is on).
2. Configure its Wi-Fi + either enable the **MQTT bridge** in the device
   firmware, or install the **ha-wican** HACS integration on HA.
3. Point the WiCAN's MQTT output at your RoamCore broker, and let HA's
   MQTT auto-discovery pick up the published sensors.
4. Map any raw sensor ids into the RoamCore contract entities
   (`rc_vehicle_battery_voltage`, `rc_vehicle_coolant_temp`,
   `rc_vehicle_speed`) — either via the WiCAN's per-sensor `object_id`
   setting, or via a tiny HA template sensor if you used the HACS path.
5. Reload the dashboard; the `rc_vehicle_*` tiles appear.

Full howto with copy-pasteable config snippets: see
[`docs/recipe.md`](docs/recipe.md). The same doc is mirrored at
`docs/howto/wican-pro-setup.md` so it shows up under the public docs
site's "How-to" section.

## Why tier-b, not tier-a

Tier-a requires a working `config_flow`, integration tests against a real
device, and `wizard.one_tap: true`. We have no WiCAN Pro device on the
CI bench to integration-test against, so this connection is honestly
beta-tier: the recipe is sound (it leans on the well-tested core `mqtt`
integration) but we cannot claim one-tap automation. The
[`tests/test_connection_yml.py`](tests/test_connection_yml.py) file
asserts the manifest is honest about its tier — that's the only test we
can ship today.

When a real WiCAN device lands on the bench, this connection is the
candidate to promote to tier-a: add a native `config_flow.py`, an
integration test that talks to a mock WiCAN REST endpoint, and flip
`tier_requirements` to include `working_config_flow` +
`integration_test_passes` + `no_manual_yaml_required`.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "wican_pro"` marker for the audit.
- `docs/recipe.md` — the full howto with copy-pasteable MQTT discovery
  payloads and a `ha-wican` template-sensor mapping example.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded): `docs/catalog/vehicle-obd/wican-pro.md`
- WiCAN Pro product page: <https://www.meatpi.com/products/wican-pro>
- WiCAN Pro docs: <https://meatpihq.github.io/wican-fw/home-assistant/>
- `ha-wican` HACS integration: <https://github.com/jay-oswald/ha-wican>
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`