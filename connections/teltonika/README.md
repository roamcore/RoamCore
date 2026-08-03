# Teltonika (LTE/5G router for vans)

**Tier:** B (recipe)
**Category:** Networking
**Status:** beta

## What this connection is

Teltonika RUT-series routers (RUT950, RUT951, RUTX11, RUTX12, RUTM50, etc.) are rugged, configurable LTE/5G mobile-internet gateways widely used in van life and remote installations. RoamCore uses them as the LTE/5G WAN slice for vans that already have a Teltonika router on board: RoamCore recipes the **telemetry + reboot** story — signal stats, WAN state, carrier, monthly data, uptime, public IP — and a one-tap "reboot teltonika" affordance for when the SIM or the cellular connection goes sideways.

- **Telemetry** comes from HA's core `snmp` integration (Path A, recommended — every Teltonika RUT firmware ships SNMP enabled-or-enableable, exposing MIB-II + Teltonika-private OIDs for WAN state, signal strength, SIM state, LTE/5G mode, carrier, data counters, uptime, and public IP), OR from the Teltonika REST / RMS / Web UI API on newer firmware (Path B — `http://<router>/cgi-bin/api/...` or the Teltonika RMS cloud API, pulled via HA's `rest` integration or `command_line` / shell_command).
- **Reboot** is either a controllable smart plug behind the router (Path A's optional plug affordance, same pattern as the Starlink `switch.rc_net_starlink_plug`) OR the Teltonika REST/RMS `reboot` API endpoint wired into a `button` helper. The recipe walks through both.
- **Mode-aware behavior** is built into the recipe: treat Teltonika as a fallback WAN for Travel; fail over to Starlink or share with Peplink where relevant; suppress reboot during Stealth silent hours.

RoamCore does **not** ship a Teltonika router or a RoamCore-owned native integration. Telemetry + reboot are sourced from operator-side SNMP/REST/RMS and the operator's chosen reboot path. RoamCore layers a contract on top: the `rc_net_teltonika_*` dashboard tiles + the OpenClaw queries ("is teltonika online?", "what's the signal?", "how much data this month?", "reboot teltonika") that bind to those contract entities.

## Setup recipe (one-paragraph)

1. Enable SNMP on the Teltonika router (System → SNMP → Enable, set a community string) for **Path A**, OR enable the REST/RMS API on the router's firmware for **Path B**. Pick the path that matches your firmware.
2. Wire the router into HA via your preferred integration:
   - **Path A (SNMP):** HA → **Settings → Devices & Services → Add Integration → SNMP**. Add the router by IP + community string.
   - **Path B (REST):** HA → **Settings → Devices & Services → Add Integration → REST** (or use a `command_line` / `shell_command` sensor for shell-driven polling).
3. Create the `rc_net_teltonika_*` contract tiles (or import the recipe's `input_*` + `template` + `button` helpers from the recipe §4 snippet block).
4. (Optional) Wire a reboot affordance — either a controllable smart plug behind the router (Path A's plug option) OR the Teltonika REST/RMS `reboot` API endpoint. The recipe §5.2 automation handles either path.
5. Enable the recipe §5 automations (mode-aware fallback-to-Starlink + reboot-on-no-internet + suppress-reboot-in-Stealth + monthly-data-counter reset).
6. Reload the RoamCore dashboard; the `rc_net_teltonika_*` contract tiles appear on the Networking section.

Full howto with copy-pasteable YAML for the helpers, automations, SNMP wiring, REST/RMS wiring, mode-aware exceptions, and the tier-a promotion outline: see [`docs/recipe.md`](docs/recipe.md).

## Why tier-b, not tier-a

Tier-a requires a working RoamCore-owned `config_flow.py`, integration tests against a real Teltonika router on CI, and `wizard.one_tap: true`. We have no Teltonika router on the CI bench to integration-test against, the operator's exact Teltonika model + firmware combo varies (RUT950, RUT951, RUTX11, RUTX12, RUTM50 — same core MIB-II surface but firmware-specific OIDs shift), and there's no canonical RoamCore-owned upstream HA integration that does what this connection recipes (the operator's SNMP-vs-REST choice is firmware-driven). So this connection is honestly beta-tier: the recipe is sound but we cannot claim one-tap automation. The [`tests/test_connection_yml.py`](tests/test_connection_yml.py) file asserts the manifest is honest about its tier — that's the only test we can ship today.

When a real Teltonika router lands on the bench (likely via `testcontainers/snmp-sim` with a synthetic MIB-II + Teltonika-private-OID fixture, or a recorded SNMP capture), this connection is the candidate to promote to tier-a: add a native `config_flow.py` that wraps the RoamCore-specific mobile-internet contract, add an integration test that asserts the `rc_net_teltonika_*` contract entities appear after a synthetic SNMP-poll, and flip `tier_requirements` to include `working_config_flow` + `integration_test_passes` + `no_manual_yaml_required`.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "teltonika"` marker for the audit.
- `docs/recipe.md` — the full howto (SNMP wiring, REST/RMS wiring, HA helpers, reboot affordance via plug or REST, mode-aware automations, troubleshooting, tier-a promotion outline).
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded by the connection manifest):
  [the legacy spec](../../the legacy spec)
- Catalog category index: the legacy spec
- Starlink connection (companion mobile-internet slice — long-range WAN):
  `connections/starlink/`
- Peplink (multi-WAN router companion — shares the multi-WAN failover story):
  the legacy spec
- MQTT broker (cross-reference — Teltonika events could ride MQTT if a community exporter is installed):
  `connections/mqtt/`
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`