# Demo mode — vendor-neutral demo values for missing sensors + auto-disable on real sensor reconnect + never-controls-real-hardware guard

**Tier:** B (recipe)
**Category:** ai
**Status:** beta

## What this connection is

Demo mode — vendor-neutral demo values for missing sensors + auto-disable on real sensor reconnect + hard-block from controlling real hardware — the umbrella for "Demo Mode lets RoamCore show example values when critical sensors are missing, so the UI still looks and feels complete during setup or demos" — is the ai-category complement to the broader RoamCore "show me what it looks like" affordances. The single "demo enabled" toggle is the operator's master enable (OFF by default); the "scenario" selector picks which demo scenario the dashboard should show (Off / Battery / Water / Connectivity); the "active scenario" tile surfaces the resolved active scenario (factoring in the enable toggle — always "Off" when the toggle is OFF); the "blocking real hardware" tile is the TRUE / FALSE safety chip that should ALWAYS be FALSE (turns red if a misconfiguration would let demo values drive a real `switch.*` / `light.*` / `climate.*` service call); the "demo battery SoC" tile surfaces a demo battery state-of-charge percentage (around 80% ± 10% on a slow cycle); the "demo fresh-water %" tile surfaces a demo fresh-water tank percentage (60% → 90% on a slow timer); the "demo LTE up" tile surfaces a demo LTE upstream boolean (TRUE / FALSE on a slow timer to simulate intermittent LTE); the "enable battery / water / connectivity" buttons are the operator-triggered one-tap enable + scenario pick; the "disable" button is the operator-triggered one-tap disable.

RoamCore ships **no** native demo-mode engine. We RECIPE the well-understood upstream HA core `input_boolean` + `input_select` + `input_text` + `input_number` helper entities (since 2022.x — expose a GUI flow for the operator to add the helper entities from the HA UI under Settings → Helpers) + the HA core `template:` sensor wrapper (since 2022.x — expose a GUI flow for the operator to add a derived `sensor.*` entity from the upstream sensors) + the HA core `template:` binary_sensor wrapper (since 2022.x — expose a GUI flow for the operator to add a derived `binary_sensor.*` entity from the upstream sensors). The 11 `rc_demo_mode_*` contract tiles are the vendor-neutral layer the dashboard + OpenClaw queries use; the actual demo-mode logic is provided by the upstream HA core `input_boolean` + `input_select` + `input_text` + `input_number` helper entities + the HA core `template:` sensor wrapper + the HA core `template:` binary_sensor wrapper (RoamCore does NOT fork any of these).

## The 4 operator-pickable demo scenarios

- **Off** — demo mode is disabled. Real sensor values (or "unknown" if sensors aren't wired) are shown. Default for operators with all hardware installed.

- **Battery demo** — shows example battery / solar / inverter values as if a Victron GX were installed + reporting. Useful when the operator is wiring RoamCore without a real power system.

- **Water tank demo** — shows example fresh / grey / black tank levels as if the SeeLevel / Victron / generic resistive tank sensors were installed. Useful for showcasing the water UI without a real tank sensor.

- **Connectivity demo** — shows example Wi-Fi / LTE / Starlink state as if multiple upstream network integrations were installed. Useful for showcasing the network UI without real radios.

## Setup recipe (one-paragraph)

1. Decide if you want demo mode (most operators with all hardware installed: leave OFF).
2. Set up the upstream helpers:
   - **HA core `input_boolean` + `input_select` + `input_text` + `input_number` helpers** — auto-installed in every HA install + exposed via the HA UI under Settings → Helpers. The operator creates the helper entities via the HA UI (or via `input_boolean:` / `input_select:` / `input_text:` / `input_number:` YAML blocks).
3. Wire the upstream real-sensor availability signals:
   - **Battery sensor availability** — the operator's chosen battery integration (Victron / Renogy / generic shunt) — the recipe uses the sensor's `unavailable` / `unknown` → real-value transition to trigger the §9.1 auto-disable guard.
   - **Tank sensor availability** — the operator's chosen tank integration (SeeLevel / Garnet / Mopeka / generic resistive) — same pattern.
   - **LTE-up binary sensor availability** — the operator's chosen network integration (Peplink / Teltonika / Starlink / generic router) — same pattern.
4. Populate `input_text.rc_demo_mode_real_hardware_targets` with the comma-separated list of real-hardware entity ids the §9.2 never-controls-hardware guard should protect (e.g. `switch.rc_fan_main, switch.rc_heated_floor_main, light.rc_approach_lights_main`).
5. Configure the operator-facing `input_boolean.rc_demo_mode_enabled` + `select.rc_demo_mode_scenario` + `sensor.rc_demo_mode_active_scenario` + `binary_sensor.rc_demo_mode_is_blocking_real_hardware` + `sensor.rc_demo_mode_demo_value_battery_soc_percent` + `sensor.rc_demo_mode_demo_value_water_fresh_percent` + `binary_sensor.rc_demo_mode_demo_value_connectivity_lte_up` contract tiles to point at the upstream helpers + the `template:` wrappers.
6. Wire the FIVE §9 MANDATORY automations (auto-disable on real sensor reconnect + never-controls-actual-hardware guard + blocks-remote-access guard + audit-log entry + operator-only guard).
7. Verify: enable demo mode via one of the `button.rc_demo_mode_enable_*` buttons → check the dashboard surfaces the demo values → check `binary_sensor.rc_demo_mode_is_blocking_real_hardware` stays FALSE → reconnect a real sensor → confirm the §9.1 auto-disable guard fires + clears the enable toggle.

Full howto: see [`docs/recipe.md`](docs/recipe.md).

## The 11 `rc_demo_mode_*` contract tiles

| Domain | Tile id | Purpose |
|---|---|---|
| `input_boolean` | `rc_demo_mode_enabled` | Master enable toggle (OFF by default). |
| `select` | `rc_demo_mode_scenario` | Off / Battery / Water / Connectivity. |
| `sensor` | `rc_demo_mode_active_scenario` | Resolved active scenario (factors in the enable toggle). |
| `binary_sensor` | `rc_demo_mode_is_blocking_real_hardware` | Safety chip — should ALWAYS be FALSE. |
| `sensor` | `rc_demo_mode_demo_value_battery_soc_percent` | Demo battery SoC (80% ± 10% slow cycle). |
| `sensor` | `rc_demo_mode_demo_value_water_fresh_percent` | Demo fresh-water % (60% → 90% slow timer). |
| `binary_sensor` | `rc_demo_mode_demo_value_connectivity_lte_up` | Demo LTE upstream boolean (slow TRUE/FALSE timer). |
| `button` | `rc_demo_mode_enable_battery` | One-tap enable + Battery scenario. |
| `button` | `rc_demo_mode_enable_water` | One-tap enable + Water scenario. |
| `button` | `rc_demo_mode_enable_connectivity` | One-tap enable + Connectivity scenario. |
| `button` | `rc_demo_mode_disable` | One-tap disable. |

## The 5 §9 MANDATORY automations

- **§9.1 Demo-mode auto-disable on real sensor reconnect** — fires when `input_boolean.rc_demo_mode_enabled` is ON AND any of the upstream real sensors (battery + tank + LTE-up, whichever matches the picked scenario) transitions from `unavailable` / `unknown` to a real value. Clears the enable toggle + resets the scenario to Off + writes an audit-log entry.
- **§9.2 Demo-mode never-controls-actual-hardware guard** — fires when any `script.*` / `automation.*` tries to call a `switch.turn_on` / `switch.turn_off` / `light.turn_on` / `light.turn_off` / `climate.set_*` service on a real-hardware target while demo mode is ON. BLOCKS the service call + flips the safety chip + fires a critical notification.
- **§9.3 Demo-mode blocks-remote-access guard** — fires when a remote-access session interacts with the dashboard while demo mode is ON. Surfaces a "demo mode is ON — values are not real" banner + adds the flag to session metadata + (if supported) refuses write-capable actions.
- **§9.4 Demo-mode audit-log entry** — fires when `input_boolean.rc_demo_mode_enabled` flips OFF→ON or ON→OFF. Writes an audit-log entry with the scenario + operator identity + timestamp + reason.
- **§9.5 Demo-mode operator-only guard** — fires when a non-operator source tries to flip the enable toggle. BLOCKS the change + writes an audit-log entry + fires a critical notification.

## Why tier-b, not tier-a

Tier-a would require a RoamCore-owned demo-mode engine + integration code + integration tests against a real demo-mode engine bench (a controlled environment with canned fixture responses for sensor availability events + canned fixture responses for remote-access session events + canned fixture responses for service-call blocking events — all wired together in a controlled environment). We have no operator-side demo-mode engine bench on the CI to integration-test against (the bench requires the operator's chosen battery + tank + LTE sensors + the operator's real-hardware target list + canned fixture responses for sensor availability events — all wired together in a controlled environment). Tier-b is the honest tier: HA core `input_boolean` + `input_select` + `input_text` + `input_number` + HA core `template:` are all upstream / vendor / HACS / hardware code (not RoamCore-owned); the RoamCore wrapper is a thin upstream-entity-aggregation layer + the contract layer + the §9 MANDATORY automations. The recipe is sound but we cannot claim one-tap automation.

The legacy catalog page (the legacy spec — 14-line tier-a claim stub, originally listed "Demo Mode lets RoamCore show example values when critical sensors are missing, so the UI still looks and feels complete during setup or demos. Helps you configure slowly without a broken-looking dashboard. Great for showcasing RoamCore without full hardware installed. None. HA package: homeassistant/packages/roamcore_demo_mode.yaml" with no recipe + no contract + no automations + no install path — just a placeholder with an aspirational tier-a claim) is now superseded by this tier-b recipe connection. The legacy tier-a claim was aspirational (no native RoamCore demo-mode engine in the repo today); the picker is honest and ships the contract layer + the recipe + the §9 automations as tier-b.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "demo_mode"` marker for the audit.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded by this slice): [the legacy spec](../../the legacy spec)
- HA core `input_boolean` integration (the canonical demo-enabled helper umbrella): https://www.home-assistant.io/integrations/input_boolean/
- HA core `input_select` integration (the canonical scenario selector helper): https://www.home-assistant.io/integrations/input_select/
- HA core `input_text` integration (the canonical real-hardware target list helper): https://www.home-assistant.io/integrations/input_text/
- HA core `input_number` integration (the canonical demo-value helper): https://www.home-assistant.io/integrations/input_number/
- HA core `template:` integration (the canonical active-scenario + demo-value derivation): https://www.home-assistant.io/integrations/template/
- Time-atomic (the time-of-day primitives used by the §9.4 audit-log entry's timestamp): `connections/time-atomic/` (Wave 3 #55)
- Remote-access (the VPN primitive used by the §9.3 blocks-remote-access guard): `connections/remote-access/` (Wave 3 #58)
- Approach lights (the §9.3 blocks-remote-access guard's dashboard banner pattern): `connections/approach-lights/` (Wave 3 #52)
- Fans (the §9.2 never-controls-actual-hardware guard's fan-protection cross-reference): `connections/fans/` (Wave 3 #59)
- Leveling (the §9.5 operator-only-guard's levelling-jack protection cross-reference): `connections/leveling/` (Wave 3 #60)
- Mode (the §9.4 audit-log entry's mode-change cross-reference): `connections/mode/` (Wave 3 #61)
- RoamCore entity naming: `docs/reference/rc-entity-naming.md` (the `demo_mode` subsystem was added by this slice)