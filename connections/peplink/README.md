# Peplink (multi-WAN router for van internet)

**Tier:** B (recipe)
**Category:** Networking
**Status:** beta

## What this connection is

Peplink Balance / MAX / EP-series routers (Balance One, Balance 20, Balance 30, MAX 700, EP 5, etc.) are rugged, configurable multi-WAN gateways very popular in van life and remote installations. They handle LTE/5G + Starlink + campground Wi-Fi with automatic failover and load balancing, giving a single stable "van Wi-Fi" network. RoamCore uses them as the **multi-WAN glue** between Teltonika (single cellular WAN) and Starlink (long-range WAN): RoamCore recipes the **telemetry + failover** story — WAN state per WAN, active WAN, WAN failover count, load-balance health, uptime, public IP — and a one-tap "force failover" affordance for when one WAN goes sideways and the operator (or the mode-aware automation) wants to test the failover path.

- **Telemetry** comes from HA's core `snmp` integration (Path A, recommended for single-router operators with SNMP-enabled Peplink firmware — most Peplink units ship SNMP enabled-or-enableable, exposing MIB-II + Peplink-private OIDs for WAN state, signal strength per WAN, WAN priority, load-balance health, uptime, throughput, and public IP per WAN), OR from the Peplink InControl 2 REST API via the community HACS `hass-incontrol2` integration (Path B — recommended for fleet operators managing >1 Peplink device, pulled via `https://api.ic.peplink.com/...` with an API key).
- **Force-failover** is wired to either the Peplink REST/SNMP-triggered WAN-swap endpoint (Path A's native option) OR the InControl 2 fleet-action endpoint (Path B). The recipe walks through both.
- **Mode-aware behavior** is built into the recipe: treat Peplink as the multi-WAN glue between Starlink + Teltonika; in Travel / Boost mode prefer cellular (Teltonika) first; in Home / Shore mode prefer Starlink first; Stealth silent hours suppress the force-failover trigger + any WAN-restart automations; alert when WAN failover count exceeds 3 in 24h.

RoamCore does **not** ship a Peplink router or a RoamCore-owned native integration. Telemetry + force-failover are sourced from operator-side SNMP/InControl 2 and the operator's chosen failover path. RoamCore layers a contract on top: the `rc_net_peplink_*` dashboard tiles + the OpenClaw queries ("is peplink online?", "what's peplink's active WAN?", "how many peplink failovers in the last 24h?", "what's peplink's load-balance health?", "what's peplink's public IP?", "force a peplink failover", "refresh peplink telemetry") that bind to those contract entities.

## Setup recipe (one-paragraph)

1. Pick a path: **Path A** (HA core `snmp` integration — recommended for single-router operators on any SNMP-enabled Peplink firmware) OR **Path B** (HACS `hass-incontrol2` + InControl 2 API key — recommended for fleet operators managing >1 Peplink device).
2. Enable the chosen path on the Peplink router:
   - **Path A (SNMP):** System → SNMP → Enable; set a community string (v2c) or v3 credentials. Note the community string + the router's LAN IP.
   - **Path B (InControl 2):** install the HACS `hass-incontrol2` integration, generate an InControl 2 API key at <https://ic.peplink.com/>, and register your Peplink fleet.
3. Wire the router into HA via your chosen integration:
   - **Path A (SNMP):** HA → **Settings → Devices & Services → Add Integration → SNMP**. Add the router by IP + community string.
   - **Path B (InControl 2):** the HACS `hass-incontrol2` integration walks you through the API key + fleet registration.
4. Create the `rc_net_peplink_*` contract tiles (or import the recipe's `input_*` + `template` + `button` + `select` helpers from the recipe §4 snippet block).
5. (Optional) Wire a force-failover affordance — either the Peplink REST/SNMP-triggered WAN-swap endpoint (Path A's native option) OR the InControl 2 fleet-action endpoint (Path B). The recipe §5.2 automation handles either path.
6. Enable the recipe §5 automations (mode-aware multi-WAN preference: cellular-first in Travel/Boost, Starlink-first in Home/Shore; suppress-force-failover in Stealth; daily failover-count counter reset; alert when WAN failover count > 3 in 24h).
7. Reload the RoamCore dashboard; the `rc_net_peplink_*` contract tiles appear on the Networking section.

Full howto with copy-pasteable YAML for the helpers, automations, SNMP wiring, InControl 2 wiring, mode-aware exceptions, and the tier-a promotion outline: see [`docs/recipe.md`](docs/recipe.md).

## Why tier-b, not tier-a

Tier-a requires a working RoamCore-owned `config_flow.py`, integration tests against a real Peplink router on CI, and `wizard.one_tap: true`. We have no Peplink router on the CI bench to integration-test against, the operator's exact Peplink model + firmware combo varies (Balance One, Balance 20, Balance 30, MAX 700, EP 5 — same core MIB-II surface but firmware-specific Peplink-private OIDs shift), the SNMP-vs-InControl2 choice is model + firmware + fleet-size driven, and there's no canonical RoamCore-owned upstream HA integration that does what this connection recipes. So this connection is honestly beta-tier: the recipe is sound but we cannot claim one-tap automation. The [`tests/test_connection_yml.py`](tests/test_connection_yml.py) file asserts the manifest is honest about its tier — that's the only test we can ship today.

When a real Peplink router lands on the bench (likely via `testcontainers/snmp-sim` with a synthetic MIB-II + Peplink-private-OID fixture, or a recorded SNMP capture from a Balance 20), this connection is the candidate to promote to tier-a: add a native `config_flow.py` that wraps the RoamCore-specific multi-WAN contract (with per-firmware OID pinning so the MIB drift across the Peplink line is handled), add an integration test that asserts the `rc_net_peplink_*` contract entities appear after a synthetic SNMP-poll, and flip `tier_requirements` to include `working_config_flow` + `integration_test_passes` + `no_manual_yaml_required`.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "peplink"` marker for the audit.
- `docs/recipe.md` — the full howto (SNMP wiring, InControl 2 wiring, HA helpers, force-failover affordance via Path A or Path B, mode-aware multi-WAN automations that prefer cellular in Travel/Boost and Starlink in Home/Shore, troubleshooting, tier-a promotion outline).
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded by the connection manifest):
  [`docs/catalog/networking/peplink.md`](../../docs/catalog/networking/peplink.md)
- Catalog category index: `docs/catalog/networking/index.md`
- Teltonika connection (companion mobile-internet slice — single cellular WAN that Peplink fails over to/from):
  `connections/teltonika/`
- Starlink connection (companion mobile-internet slice — long-range WAN that Peplink fails over to/from):
  `connections/starlink/`
- MQTT broker (cross-reference — Peplink events could ride MQTT if a community exporter is installed):
  `connections/mqtt/`
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`