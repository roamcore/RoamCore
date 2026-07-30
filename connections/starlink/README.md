# Starlink (sleep timer + bring-back-up controls)

**Tier:** B (recipe)
**Category:** Networking
**Status:** beta

## What this connection is

Starlink is a self-hosted mobile-internet terminal (Gen-2/Gen-3 dish +
router + PSU). RoamCore uses it as the long-range WAN in vans that go
off-grid: when campground Wi-Fi is weak and LTE/5G is congested, the
Starlink dish is what keeps remote access + streaming working. RoamCore
recipes the **sleep timer + bring-back-up** story — automatically
power down Starlink during quiet hours to save battery, and a one-tap
"wake for 30 minutes" affordance when you need it back.

- **Sleep + wake** go through an operator-side controllable smart plug
  / relay / DC switch behind the Starlink PSU (or behind the router
  only, if you want the dish powered but the router off). Any plug
  HA can switch works — TP-Link / Shelly / Sonoff / Zigbee / Modbus /
  a Sonoff POW with a tail / etc.
- **Reachability + signal stats** use Starlink's local HTTP API
  (`http://192.168.100.1/api/console/dish-status.json` on Gen-2/Gen-3
  routers). Gen-1 routers have no local API and the signal tile is
  grayed out.
- **Mode-aware behavior** is built into the recipe: skip sleep while
  Travel mode unless alternator charging; respect Stealth silent hours;
  break sleep if nobody else has internet so remote access keeps
  working.

RoamCore does **not** ship a Starlink terminal or phone Starlink's
cloud API. Sleep + wake + signal telemetry are sourced from operator-
side smart-plug state and Starlink's local HTTP API only.

## Setup recipe (one-paragraph)

1. Put a controllable smart plug / relay / DC switch behind the
   Starlink PSU (or behind the router only — see recipe §3 for the
   trade-off).
2. Wire the plug into HA via your preferred integration (TP-Link /
   Shelly / Sonoff / Zigbee / Modbus / ...). Create a helper
   `switch.rc_net_starlink_plug` pointing at the plug's HA switch
   entity.
3. Create the `rc_net_starlink_*` contract tiles (or import the recipe's
   `input_datetime` + `input_boolean` + `template` helpers from the
   recipe §4 snippet block).
4. (Optional, Gen-2/Gen-3 only) Pull signal stats from
   `http://192.168.100.1/api/console/dish-status.json` via a REST sensor
   or shell_command and feed `sensor.rc_net_starlink_signal_pct`.
5. Enable the recipe §5 automations (sleep-during-quiet-hours + wake-
   for-30-min-on-demand + mode-aware exceptions).
6. Reload the RoamCore dashboard; the `rc_net_starlink_*` contract
   tiles appear on the Networking section.

Full howto with copy-pasteable YAML for the helpers, automations,
REST-sensor wiring, mode-aware exceptions, and the tier-a promotion
outline: see [`docs/recipe.md`](docs/recipe.md).

## Why tier-b, not tier-a

Tier-a requires a working RoamCore-owned `config_flow.py`, integration
tests against a real Starlink terminal on CI, and `wizard.one_tap:
true`. We have no Starlink dish on the CI bench to integration-test
against, and there's no canonical upstream HA integration that does
what this connection recipes (the operator's smart-plug integration
varies; Starlink's own local API is undocumented and shifts between
firmware versions). So this connection is honestly beta-tier: the
recipe is sound but we cannot claim one-tap automation. The
[`tests/test_connection_yml.py`](tests/test_connection_yml.py) file
asserts the manifest is honest about its tier — that's the only test
we can ship today.

When a real Starlink terminal lands on the bench (likely via
`testcontainers/grpc-starlink-dish` with a synthetic `dish-status.json`
fixture, or a recorded capture), this connection is the candidate to
promote to tier-a: add a native `config_flow.py` that wraps the
RoamCore-specific mobile-internet contract, add an integration test
that asserts the `rc_net_starlink_*` contract entities appear after a
synthetic plug-toggle, and flip `tier_requirements` to include
`working_config_flow` + `integration_test_passes` +
`no_manual_yaml_required`.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "starlink"` marker for the audit.
- `docs/recipe.md` — the full howto (smart-plug wiring, HA helpers,
  optional signal-stats wiring, sleep + wake + mode-aware automations,
  troubleshooting, tier-a promotion outline).
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded by the connection manifest):
  [`docs/catalog/networking/starlink-sleep-timer.md`](../../docs/catalog/networking/starlink-sleep-timer.md)
- Catalog category index: `docs/catalog/networking/index.md`
- MQTT broker (cross-reference — future Starlink telemetry could ride
  MQTT if a community exporter is installed): `connections/mqtt/`
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`
- OpenWrt router controls (Starlink plugs into the LAN behind the
  OpenWrt WAN): `connections/openwrt-controls/`
  (see `docs/catalog/networking/openwrt-controls.md`)