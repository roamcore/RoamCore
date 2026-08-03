# Smart Automations (one-click enable / disable)

**Tier:** B (recipe)
**Category:** Safety
**Status:** beta

## What this connection is

Smart Automations is the **day-to-day convenience layer** of a RoamCore van: **17 prebuilt Home Assistant automations** that handle mode-aware transitions (Night Mode Stealth/Auto), power-aware responses (Low Battery Mode, Battery Full Alert, Battery Critical Alert, Solar is Crushing It), safety alerts (Inverter Overheat Alert, Router Overheat Alert, Freeze Protection), trip accounting (Daily Trip Log, Arrive at Camp, Depart Travel Mode), connectivity resilience (Auto Internet Failover, Internet Recovery, Shore Power Connected / Disconnected), and bedtime reminders (Bedtime Level Check, Quiet Hours Reminder).

All 17 are **fully native Home Assistant automations** (editable in HA) — RoamCore does **not** ship a hidden automation engine. The 1-click enable/disable affordance lives in `RoamCore → Settings → Smart Automations` and is implemented as HA core `template:` + `button:` + `select:` entities that audit each managed automation's description for the `Managed by RoamCore Smart Automations v0.1` marker + the `key=<name>` + `hash=<template hash>` invariants, and expose 25 `rc_safety_*` contract tiles per docs/reference/rc-entity-naming.md §safety subsystem.

RoamCore ships **no** native automation engine. We RECIPE the well-understood combination of:

- **HA Core `automation:` domain** — the upstream `automation:` integration exposes its own GUI flow on first run since 2023.x; the recipe §3 walks the operator through enabling each of the 17 automations.
- **HA Core `script:` domain** — the upstream `script:` integration exposes its own GUI flow; the recipe §3 documents which scripts each automation depends on (Night Mode → `script.rc_mode_set_stealth` + `script.rc_mode_set_auto`, Low Battery Mode → `script.rc_mode_set_camp`, etc.).
- **HA Core `template:` + `button:` + `select:` domains** — the recipe §3 shows the templates that mirror each managed automation's enable/disable state into the `binary_sensor.rc_safety_automation_<name>` contract tiles + the `rc_safety_automations_*` summary tiles (enabled count + missing count + all-ready flag + view filter + enable-all-ready / disable-all buttons).

The 17 automations are listed in full at [`docs/guides/smart-automations.md`](../../docs/guides/smart-automations.md) — that file is the **canonical source of truth** for what each automation does; this recipe mirrors its structure with the wiring / audit / contract-tile layer on top.

## Setup recipe (one-paragraph)

1. Decide which of the 17 automations fit your van. Start with the **mode-aware** four (Night Mode / Arrive at Camp / Depart Travel Mode / Quiet Hours Reminder) — those ride the upcoming `connections/mode-automation-builder/` recipe's `input_select.rc_mode` + `script.rc_mode_set_*` scripts.
2. Wire the prerequisites FIRST (the recipe §2 walks through these). Each automation lists the prerequisite sensors / scripts it depends on; the operator MUST wire each one before the automation can fire.
3. From `RoamCore → Settings → Smart Automations`, click **Enable** for each automation you want. RoamCore creates a standard HA automation via the HA config API with the managed-marker (`Managed by RoamCore Smart Automations v0.1` + `key=<name>` + `hash=<template hash>`) in the description.
4. Verify the 17 `binary_sensor.rc_safety_automation_*` mirror tiles light up via the audit summary tile (`binary_sensor.rc_safety_automations_all_ready`).
5. Verify the mode-aware automations wire correctly (Night Mode Stealth/Auto transition, Arrive at Camp on GPS slowdown, etc.).
6. Reload the RoamCore dashboard.

Full howto: see [`docs/recipe.md`](docs/recipe.md).

## Why tier-b, not tier-a

Tier-a requires a working RoamCore-owned `config_flow.py`, integration tests against a real HA Core automation engine on CI, and `wizard.one_tap: true`. We have no RoamCore-owned automation engine — the 17 automations live in HA Core's automation engine and RoamCore only RECIPE-s them + audits the managed-marker + publishes the contract tiles. So this connection is honestly beta-tier: the recipe is sound but we cannot claim `wizard.one_tap: true` (each automation has per-automation prerequisites that the operator MUST wire first) and we cannot claim a RoamCore-owned `config_flow.py` (the upstream HA Core `automation:` integration already exposes a GUI flow).

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "smart_automations"` marker for the audit.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded): [the legacy spec](../../the legacy spec)
- Canonical automation list (the source of truth for what each of the 17 automations does): [`docs/guides/smart-automations.md`](../../docs/guides/smart-automations.md)
- Smoke / CO / gas safety sensors (companion for the §7 cooking-aware silencing automation): `connections/smoke-co-gas-sensors/`
- Heated floors + engine pre-heat (companion for the §16 Bedtime Level Check prerequisite): `connections/heated-floors/`
- Victron (companion for the §3 Low Battery Mode + §6 Battery Full Alert + §7 Inverter Overheat Alert + §14 Solar is Crushing It + §15 Battery Critical Alert + §9 Shore Power Connected + §10 Shore Power Disconnected prerequisites): `connections/victron/`
- Traccar (companion for the §5 Daily Trip Log + §12 Arrive at Camp + §13 Depart Travel Mode prerequisites): `connections/traccar/`
- Leveling (companion for the §16 Bedtime Level Check prerequisite): `connections/leveling/`
- OpenWrt controls (companion for the §2 Auto Internet Failover + §11 Internet Recovery script prerequisites): `connections/openwrt-controls/`
- Net (companion for the §2 Auto Internet Failover + §11 Internet Recovery sensor prerequisites): `connections/net/`
- Mode / automation-builder (companion for the §1 Night Mode + §12 Arrive at Camp + §13 Depart Travel Mode + §17 Quiet Hours Reminder mode scripts + `input_select.rc_mode` prerequisite): `connections/mode-automation-builder/`
- Bluetooth / Wi-Fi presence (companion for the operator-phone-home escalation that downstream alarms can use): `connections/bluetooth-wifi-presence/`
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`