# Mode (AI mode) — vendor-neutral mode state (Off / Auto / Travel / Camp / Stealth) + opt-in AI inference summary + auto-revert on manual override

**Tier:** B (recipe)
**Category:** ai
**Status:** beta

## What this connection is

Mode (AI mode) — vendor-neutral mode state (Off / Auto / Travel / Camp / Stealth) + opt-in AI inference summary + auto-revert on manual override — the umbrella for "Quickly switch the van between common states (driving, parked, quiet night). A clean way to group automations later without building everything at once" — is the ai-category complement to the broader RoamCore automation affordances. The single "current mode" tile collapses a pile of inferred state (motion, location, plug-state, time-of-day, presence) into one dashboard indicator; the "previous mode" tile surfaces the mode before the last change (useful for "auto-revert in 30 minutes" automations); the "is auto inferred" tile is the TRUE / FALSE indicator of whether the mode was auto-inferred or manually overridden; the "is manual override" tile is the TRUE / FALSE indicator of whether the operator has overridden the auto-inference (auto-clears after 30 minutes unless re-poked); the "changed at" tile surfaces the ISO timestamp of the last mode change; the "inference confidence" tile surfaces the upstream inference's confidence in the current mode (0.0–1.0); the "AI summary" tile is the short natural-language summary of WHY the mode is what it is (populated by the opt-in AI path via the upstream HA core Conversation agent + optional operator-selected LLM add-ons); the "revert to auto" button is the operator-triggered manual-override drop; the "force stealth" button is the operator-triggered Stealth-mode force; the "force travel" button is the operator-triggered Travel-mode force.

RoamCore ships **no** native mode engine. We RECIPE the well-understood upstream HA core `input_select` + `input_boolean` + `input_text` + `input_button` + `input_number` helper entities (since 2022.x — expose a GUI flow for the operator to add the helper entities from the HA UI under Settings → Helpers) + the HA core `template:` sensor + `template:` binary_sensor wrappers (since 2022.x — expose a GUI flow for the operator to add a derived entity from the upstream sensors) + the HA core Conversation agent (since 2022.x — the canonical upstream opt-in AI path; exposes a GUI flow for the operator to enable the agent from the HA UI) + the optional operator-selected LLM add-ons (since 2023.x — expose a GUI flow for the operator to add their API key + provider). The 10 `rc_mode_*` contract tiles are the vendor-neutral layer the dashboard + OpenClaw queries use; the actual mode logic is provided by the upstream HA core `input_select` + `input_boolean` + `input_text` + `input_button` + `input_number` helper entities + the HA core `template:` sensor + `template:` binary_sensor wrappers + the HA core Conversation agent + the optional operator-selected LLM add-ons (RoamCore does NOT fork any of these).

## The 5 operator-pickable modes

- **Off** — explicitly off. No auto-mode inference, no automations triggered by mode. Used when the operator wants to be fully manual (rare — most operators prefer Auto).

- **Auto** — RoamCore infers the current mode from the upstream sensors (motion, location, plug-state, time-of-day, presence). This is the default for most operators.

- **Travel** — the van is moving. Inferred from GPS speed > 5 km/h OR the ignition-on input. Manual override is "I'm parked but I want travel-mode anyway" (e.g., pulling a trailer).

- **Camp** — the van is parked + occupied + utilities are available. Inferred from GPS speed = 0 + presence detected + time-of-day in daylight OR plug connected. Manual override is "I'm parked but not camping" (e.g., quick grocery stop).

- **Stealth** — the van is parked + occupied + utilities are restricted (no plug, no shore power). Used for overnight stealth camping in urban areas. Inferred from GPS speed = 0 + presence detected + time-of-day in night + no plug. Manual override is "I'm stealth camping during the day" (rare).

## Setup recipe (one-paragraph)

1. Pick a default mode (most operators: Auto).
2. Set up the upstream helpers:
   - **HA core `input_select` + `input_boolean` + `input_text` + `input_button` + `input_number` helpers** — auto-installed in every HA install + exposed via the HA UI under Settings → Helpers. The operator creates the helper entities via the HA UI (or via `input_select:` / `input_boolean:` / `input_text:` / `input_button:` YAML blocks).
3. Wire the upstream signals (GPS speed + ignition-on input + presence detection + plug-state + time-of-day primitives):
   - **GPS speed** — Traccar for vehicle GPS OR the HA Companion app for phone GPS (since 2022.x).
   - **Ignition-on input** — the operator's chosen vehicle integration (varies by van; documented separately).
   - **Presence detection** — the HA Companion app (since 2022.x) OR Bluetooth/Wi-Fi presence.
   - **Plug-state** — the operator's shore-power integration (varies by van; documented separately).
   - **Time-of-day** — the time-atomic Wave 3 #55 connection's sunrise/sunset primitives.
4. Configure the operator-facing `select.rc_mode_state` + `select.rc_mode_state_previous` + `binary_sensor.rc_mode_is_auto_inferred` + `binary_sensor.rc_mode_is_manual_override` + `sensor.rc_mode_changed_at` + `sensor.rc_mode_inference_confidence` + `text.rc_mode_ai_summary` contract tiles to point at the upstream entities.
5. Wire the FIVE §9 MANDATORY automations (auto-mode inference from GPS + motion + plug + time-of-day + manual override + auto-revert + confirm-before-power-changing-action guard + stealth-mode audit-log entry + mode-change notification).
6. Optionally enable the Conversation agent (HA core since 2022.x — Settings → Voice assistants → Conversation agent) + add the optional operator-selected LLM add-ons (since 2023.x — Settings → Integrations → add the LLM provider) for the opt-in AI inference summary.
7. Verify: check `select.rc_mode_state` reflects the auto-inferred mode + pick a mode manually via the dashboard + verify `binary_sensor.rc_mode_is_manual_override` flips to TRUE + wait 30 minutes + verify the auto-revert fires.

Full howto: see [`docs/recipe.md`](docs/recipe.md).

## Why tier-b, not tier-a

Tier-a would require a RoamCore-owned mode engine + integration code + integration tests against a real mode engine bench (a controlled environment with canned fixture responses for GPS / motion / plug-state / time-of-day events + canned fixture responses for the Conversation agent's natural-language mode queries — all wired together in a controlled environment). We have no operator-side mode engine bench on the CI to integration-test against (the bench requires the operator's chosen GPS + ignition-on input + presence detection + plug-state + Conversation agent + canned fixture responses for GPS / motion / plug-state / time-of-day events — all wired together in a controlled environment). Tier-b is the honest tier: HA core `input_select` + `input_boolean` + `input_text` + `input_button` + `input_number` + HA core `template:` + HA core Conversation agent + optional operator-selected LLM add-ons are all upstream / vendor / HACS / hardware code (not RoamCore-owned); the RoamCore wrapper is a thin upstream-entity-aggregation layer + the contract layer + the §9 MANDATORY automations. The recipe is sound but we cannot claim one-tap automation.

The legacy catalog page (the legacy spec — 18-line tier-a claim stub, originally listed "RoamCore defines a simple 'Mode' entity and convenience scripts (Auto/Travel/Camp/Stealth/Off). This shows up as a user-facing control in the dashboard and is a foundation for future 'one tap' behavior changes. Quickly switch the van between common states (driving, parked, quiet night). A clean way to group automations later without building everything at once. None. HA package: homeassistant/packages/roamcore_mode.yaml" with no recipe + no contract + no automations + no install path — just a placeholder with an aspirational tier-a claim) is now superseded by this tier-b recipe connection. The legacy tier-a claim was aspirational (no native RoamCore mode engine in the repo today); the picker is honest and ships the contract layer + the recipe + the §9 automations as tier-b.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "mode"` marker for the audit.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded by this slice): [the legacy spec](../../the legacy spec)
- HA core `input_select` integration (the canonical mode-state helper umbrella): https://www.home-assistant.io/integrations/input_select/
- HA core `input_boolean` integration (the canonical manual-override flag helper): https://www.home-assistant.io/integrations/input_boolean/
- HA core `input_text` integration (the canonical changed-at timestamp helper): https://www.home-assistant.io/integrations/input_text/
- HA core `input_button` integration (the canonical force-* + revert-to-auto button helper): https://www.home-assistant.io/integrations/input_button/
- HA core `template:` integration (the canonical inference-confidence + AI-summary derivation): https://www.home-assistant.io/integrations/template/
- HA core Conversation agent (the canonical upstream opt-in AI path): https://www.home-assistant.io/integrations/conversation/
- Time-atomic (the time-of-day primitives used by the §9.1 auto-mode inference): `connections/time-atomic/` (Wave 3 #55)
- Motion-based-lighting (the presence-detection primitive used by the §9.1 auto-mode inference): `connections/motion-based-lighting/` (Wave 3 #53)
- Approach lights (the cabin-lighting scene modified by the §9.4 stealth-mode audit-log entry): `connections/approach-lights/` (Wave 3 #52)
- Remote-access (the VPN primitive used by the §9.5 mode-change notification's optional Telegram delivery): `connections/remote-access/` (Wave 3 #58)
- Fans (the §9.3 confirm-before-power-changing-action guard's fan-off-on-mode-change behavior): `connections/fans/` (Wave 3 #59)
- Leveling (the §9.5 mode-change notification's level-cross-reference): `connections/leveling/` (Wave 3 #60)
- NFC tags (the optional NFC-tag-triggered mode-change affordance): `connections/nfc-tags/` (Wave 3 #57)
- Mode/automation-builder (the legacy `select.rc_mode` tile source of truth — the Wave 3 #61 recipe's `select.rc_mode_state` is intentionally distinct from this legacy tile): `connections/smart-automations/` (Wave 2 #23)
- RoamCore entity naming: `docs/reference/rc-entity-naming.md` (the `mode` subsystem was added by this slice)