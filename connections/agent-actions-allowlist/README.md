# Agent actions allowlist — vendor-neutral kill-switch + per-action allowlist + audit-log gateway for safe agent-driven RoamCore actions

**Tier:** B (recipe)
**Category:** ai
**Status:** beta

## What this connection is

Agent actions allowlist — vendor-neutral kill-switch + per-action allowlist + audit-log gateway for safe agent-driven RoamCore actions — the umbrella for "Agent actions allowlist (safety gateway): A safety layer that defaults to deny and only permits explicitly-allowed agent actions, with a kill switch. Lets you use automation/agents without fear of unexpected device control; Clear boundary between read-only and can change things" — is the ai-category complement to the broader RoamCore "talk to your van" affordances. The single `input_boolean.rc_agent_actions_enabled` kill switch is the operator's master enable (OFF by default; this tile is ALREADY shipped in `homeassistant/packages/roamcore_agent_actions.yaml` and is preserved verbatim — the package is not redefined by this slice); the `input_text.rc_agent_actions_policy_path` is the operator-configurable policy file path (default `/config/.roamcore/agent_allowlist.yaml`); the `input_boolean.rc_agent_actions_require_confirmation` is the "every action needs an explicit confirmation" toggle (default ON); the `select.rc_agent_actions_default_duration` is the operator-pickable session-duration picker (Off / 1h / 6h / 24h / 7d / Never; default 24h); the `input_datetime.rc_agent_actions_session_expires_at` is the session expiry timestamp (set to "now + selected duration" when the kill switch flips ON); the `sensor.rc_agent_actions_seconds_until_expiry` is the resolved countdown to the session expiry; the `sensor.rc_agent_actions_last_action_id` is the `action_id` of the last agent action invocation; the `sensor.rc_agent_actions_last_action_at` is the timestamp of the last agent action invocation; the `sensor.rc_agent_actions_last_action_result` is the resolved result of the last agent action (`ok` / `error` / `blocked` / `denied` / `pending-confirmation`); the `binary_sensor.rc_agent_actions_is_blocked_by_kill_switch` is the safety chip (TRUE when the kill switch is OFF or the session has expired); the `button.rc_agent_actions_disable_now` is the operator-triggered one-tap emergency off.

RoamCore ships **no** native agent-actions engine. We RECIPE the well-understood upstream HA core `input_boolean` + `input_text` + `input_number` + `input_select` + `input_datetime` + `input_button` + `script` helper entities (since 2022.x — expose a GUI flow for the operator to add the helper entities from the HA UI under Settings → Helpers) + the HA core `template:` sensor wrapper (since 2022.x — expose a GUI flow for the operator to add a derived `sensor.*` entity from the upstream sensors) + the HA core `logbook` integration (since 2022.x — the canonical audit-log destination for Home Assistant automations). The 11 `rc_agent_actions_*` contract tiles are the vendor-neutral layer the dashboard + OpenClaw queries use; the actual agent-actions logic is provided by the upstream HA core helpers + the upstream `script:` integration (RoamCore does NOT fork any of these).

## The 5-step operator flow

- **Step 1 — Confirm** — the operator confirms the existing `input_boolean.rc_agent_actions_enabled` kill switch defaults to OFF (already shipped in `homeassistant/packages/roamcore_agent_actions.yaml`; preserved verbatim by this slice). Without this confirmation, agent actions stay blocked.

- **Step 2 — Mount the policy file** — the operator copies `connections/agent-actions-allowlist/docs/policy.example.yaml` to `input_text.rc_agent_actions_policy_path` (default `/config/.roamcore/agent_allowlist.yaml`) and edits the policy file for their setup. The policy file is a YAML document with a `version: 1` header + a `defaults:` block (e.g. `require_confirmation: true`) + an `actions:` list with per-action entries (each entry has `id` + `description` + `kind` (`set_helper` or `run_script`) + `target` + optional `constraints` + optional `require_confirmation`).

- **Step 3 — Decide the default duration** — the operator picks the session duration via `select.rc_agent_actions_default_duration` (Off / 1h / 6h / 24h / 7d / Never; default 24h). After timeout, the §8.2 session-timeout guard fires and auto-disables the kill switch.

- **Step 4 — Enable with optional confirmation** — the operator flips `input_boolean.rc_agent_actions_enabled` ON. The kill switch surfaces a green "agent actions enabled" chip + unlocks the agent-actions dashboard tiles + the §8.4 require-confirmation guard enforces that the agent must call `roamcore.action_confirm` BEFORE `roamcore.action_execute` when `input_boolean.rc_agent_actions_require_confirmation` is ON (default ON).

- **Step 5 — Audit + revert** — every agent action invocation writes an entry to `sensor.rc_agent_actions_last_action_id` + `sensor.rc_agent_actions_last_action_at` + `sensor.rc_agent_actions_last_action_result` + additionally tags the HA core `logbook` entry with the `agent_actions` tag. The operator can revert at any time via `button.rc_agent_actions_disable_now`.

## Setup recipe (one-paragraph)

1. Decide if you want agent actions (most operators: leave OFF; flip ON only when the agent is being used).
2. Confirm the existing `input_boolean.rc_agent_actions_enabled` kill switch (already shipped in `homeassistant/packages/roamcore_agent_actions.yaml`; preserved verbatim).
3. Set up the upstream helpers:
   - **HA core `input_boolean` + `input_text` + `input_number` + `input_select` + `input_datetime` + `input_button` + `script` helpers** — auto-installed in every HA install + exposed via the HA UI under Settings → Helpers. The operator creates the helper entities via the HA UI (or via `input_boolean:` / `input_text:` / `input_number:` / `input_select:` / `input_datetime:` / `input_button:` / `script:` YAML blocks).
4. Mount the policy file:
   - Copy `connections/agent-actions-allowlist/docs/policy.example.yaml` to `input_text.rc_agent_actions_policy_path` (default `/config/.roamcore/agent_allowlist.yaml`).
   - Populate the `actions:` list with the per-action entries the agent is permitted to invoke (each entry has `id` + `description` + `kind` (`set_helper` or `run_script`) + `target` + optional `constraints` + optional `require_confirmation`).
5. Wire the upstream require-confirmation toggle:
   - Populate `input_boolean.rc_agent_actions_require_confirmation` (default ON for the recommended safety mode).
6. Configure the operator-facing `input_text.rc_agent_actions_policy_path` + `input_boolean.rc_agent_actions_require_confirmation` + `select.rc_agent_actions_default_duration` + `input_datetime.rc_agent_actions_session_expires_at` + `sensor.rc_agent_actions_seconds_until_expiry` + `sensor.rc_agent_actions_last_action_id` + `sensor.rc_agent_actions_last_action_at` + `sensor.rc_agent_actions_last_action_result` + `binary_sensor.rc_agent_actions_is_blocked_by_kill_switch` + `button.rc_agent_actions_disable_now` contract tiles to point at the upstream helpers + the `template:` wrappers + the `logbook` integration.
7. Wire the FIVE §8 MANDATORY automations (kill-switch-blocks-everything guard + session-timeout guard + audit-log entry + require-confirmation guard + outside-allowlist deny-by-default guard).
8. Verify: confirm the kill switch is OFF → mount the policy file → set the require-confirmation toggle ON → flip the kill switch ON → invoke a known action via `roamcore.action_execute` → confirm the agent calls `roamcore.action_confirm` first → check the audit-log entry fires → invoke an unknown action → check the §8.5 outside-allowlist deny-by-default guard fires + short-circuits to denied → wait for the expiry timestamp → check the §8.2 session-timeout guard fires + clears the kill switch.

Full howto: see [`docs/recipe.md`](docs/recipe.md).

## The 11 `rc_agent_actions_*` contract tiles

| Domain | Tile id | Purpose |
|---|---|---|
| `input_boolean` | `rc_agent_actions_enabled` | Master kill switch (OFF by default; already shipped in `homeassistant/packages/roamcore_agent_actions.yaml`; preserved verbatim). |
| `input_text` | `rc_agent_actions_policy_path` | Operator-configurable policy file path (default `/config/.roamcore/agent_allowlist.yaml`). |
| `input_boolean` | `rc_agent_actions_require_confirmation` | Whether new actions require explicit confirmation (default ON). |
| `select` | `rc_agent_actions_default_duration` | Off / 1h / 6h / 24h / 7d / Never (default 24h). |
| `input_datetime` | `rc_agent_actions_session_expires_at` | Session expiry timestamp ("now + selected duration"). |
| `sensor` | `rc_agent_actions_seconds_until_expiry` | Resolved countdown to session expiry. |
| `sensor` | `rc_agent_actions_last_action_id` | Last agent action `action_id`. |
| `sensor` | `rc_agent_actions_last_action_at` | Last agent action timestamp. |
| `sensor` | `rc_agent_actions_last_action_result` | Last agent action result (`ok` / `error` / `blocked` / `denied` / `pending-confirmation`). |
| `binary_sensor` | `rc_agent_actions_is_blocked_by_kill_switch` | Safety chip — TRUE when kill switch is OFF or session has expired. |
| `button` | `rc_agent_actions_disable_now` | One-tap emergency off (also turns the master kill switch OFF). |

## The 5 §8 MANDATORY automations

- **§8.1 Kill-switch-blocks-everything guard** — fires when ANY `script.*` / `automation.*` action tries to invoke `roamcore.action_execute` while `input_boolean.rc_agent_actions_enabled` is OFF. BLOCKS the invocation + short-circuits to `denied` + flips `binary_sensor.rc_agent_actions_is_blocked_by_kill_switch` to TRUE + writes an audit-log entry + fires a critical notification.
- **§8.2 Session-timeout guard** — fires when `sensor.rc_agent_actions_seconds_until_expiry` reaches 0. Clears the kill switch + clears the session_expires_at + writes a `session_expired` audit-log entry + fires a notification.
- **§8.3 Audit-log entry** — fires on every agent action invocation. Writes an entry to `sensor.rc_agent_actions_last_action_id` + `sensor.rc_agent_actions_last_action_at` + `sensor.rc_agent_actions_last_action_result` + additionally tags the HA core `logbook` entry with the `agent_actions` tag for sortability.
- **§8.4 Require-confirmation guard** — fires when `input_boolean.rc_agent_actions_require_confirmation` is ON AND `roamcore.action_execute` is invoked WITHOUT a prior `roamcore.action_confirm` call. BLOCKS the invocation + short-circuits to `pending-confirmation` + writes an audit-log entry + fires a notification.
- **§8.5 Outside-allowlist deny-by-default guard** — fires when ANY `script.*` / `automation.*` action tries to invoke `roamcore.action_execute` with an `action_id` that is NOT in the operator's policy file at `input_text.rc_agent_actions_policy_path`. BLOCKS the invocation + short-circuits to `denied` + writes a `denied` audit-log entry + fires a critical notification.

## Why tier-b, not tier-a

Tier-a would require a RoamCore-owned agent-actions engine + integration code + integration tests against a real agent-actions engine bench (a controlled environment with canned fixture responses for kill-switch-blocks events + canned fixture responses for session-expired events + canned fixture responses for require-confirmation bypass attempts + canned fixture responses for outside-allowlist deny events + canned fixture responses for action_id collisions — all wired together in a controlled environment). We have no operator-side agent-actions engine bench on the CI to integration-test against (the bench requires the operator's chosen policy file + canned fixture responses for the FIVE §8 automations). Tier-b is the honest tier: HA core `input_boolean` + `input_text` + `input_number` + `input_select` + `input_datetime` + `input_button` + `script` + HA core `template:` + HA core `logbook` are all upstream / vendor / HACS code (not RoamCore-owned); the RoamCore wrapper is a thin upstream-entity-aggregation layer + the contract layer + the FIVE §8 MANDATORY automations + the operator-side policy file format documentation. The recipe is sound but we cannot claim one-tap automation.

The legacy catalog page (`docs/catalog/ai/agent-actions-allowlist.md` — 12-line tier-a claim stub, originally listed "Agent actions allowlist (safety gateway): A safety layer that defaults to deny and only permits explicitly-allowed agent actions, with a kill switch. Lets you use automation/agents without fear of unexpected device control; Clear boundary between read-only and can change things. None. Design notes: docs/design/agent-actions-allowlist.md; HA package: homeassistant/packages/roamcore_agent_actions.yaml. (Add safety philosophy + examples)" with no recipe + no contract + no automations + no install path — just a placeholder with an aspirational tier-a claim) is now superseded by this tier-b recipe connection. The legacy tier-a claim was aspirational (no native RoamCore agent-actions engine in the repo today); the picker is honest and ships the contract layer + the recipe + the §8 automations + the operator-side policy file format as tier-b. The kill-switch helper at `homeassistant/packages/roamcore_agent_actions.yaml` is preserved verbatim by this slice.

## Files

- `connection.yml` — the source-of-truth tier-b manifest.
- `__init__.py` — `DOMAIN = "agent_actions"` marker for the audit.
- `docs/recipe.md` — the full howto.
- `docs/policy.example.yaml` — the EXAMPLE policy file format (operator copies to `input_text.rc_agent_actions_policy_path` and edits for their setup).
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded by this slice): [`docs/catalog/ai/agent-actions-allowlist.md`](../../docs/catalog/ai/agent-actions-allowlist.md)
- Design doc (philosophy + threat model + policy file format + execution flow + UI/UX proposal): [`docs/design/agent-actions-allowlist.md`](../../docs/design/agent-actions-allowlist.md) (171 lines — the canonical source of truth for the safety philosophy)
- Existing kill-switch helper package (preserved verbatim): [`homeassistant/packages/roamcore_agent_actions.yaml`](../../homeassistant/packages/roamcore_agent_actions.yaml) (declares the `input_boolean.rc_agent_actions_enabled` helper; this slice ONLY references it as an existing tile — DO NOT redefine)
- HA core `input_boolean` integration (the canonical kill switch + require-confirmation toggle helper): https://www.home-assistant.io/integrations/input_boolean/
- HA core `input_text` integration (the canonical policy file path helper): https://www.home-assistant.io/integrations/input_text/
- HA core `input_number` integration (the canonical numeric helper for policy validation): https://www.home-assistant.io/integrations/input_number/
- HA core `input_select` integration (the canonical default-duration picker helper): https://www.home-assistant.io/integrations/input_select/
- HA core `input_datetime` integration (the canonical session-expiry-timestamp helper): https://www.home-assistant.io/integrations/input_datetime/
- HA core `input_button` integration (the canonical disable-now button helper): https://www.home-assistant.io/integrations/input_button/
- HA core `script:` integration (the canonical `roamcore.action_execute` + `roamcore.action_confirm` wrapper): https://www.home-assistant.io/integrations/script/
- HA core `template:` integration (the canonical seconds-until-expiry + last-action-id + last-action-at + last-action-result derivation): https://www.home-assistant.io/integrations/template/
- HA core `logbook` integration (the canonical audit-log destination for the §8.3 audit-log entry): https://www.home-assistant.io/integrations/logbook/
- Time-atomic (the time-of-day primitives used by the §8.2 session-timeout guard's expiry timestamp): `connections/time-atomic/` (Wave 3 #55)
- Remote-access (the VPN primitive used by the §8.4 require-confirmation guard's owner-identity check): `connections/remote-access/` (Wave 3 #58)
- Approach lights (the dashboard banner pattern used by the §8.3 audit-log entry): `connections/approach-lights/` (Wave 3 #52)
- Fans (the §8.1 kill-switch-blocks-everything guard's fan-protection cross-reference): `connections/fans/` (Wave 3 #59)
- Leveling (the §8.1 kill-switch-blocks-everything guard's levelling-jack protection cross-reference): `connections/leveling/` (Wave 3 #60)
- Mode (the §8.3 audit-log entry's mode-change cross-reference): `connections/mode/` (Wave 3 #61)
- Demo-mode (the §8.5 outside-allowlist deny-by-default guard's safety-chip pattern): `connections/demo-mode/` (Wave 3 #62)
- Advanced-mode (the §8.4 require-confirmation guard's confirm-flag pattern): `connections/advanced-mode/` (Wave 3 #63)
- OpenClaw JSON API (the §8.3 audit-log entry's JSON payload cross-reference): `connections/openclaw-api/` (Wave 3 #64)
- RoamCore entity naming: [`docs/reference/rc-entity-naming.md`](../../docs/reference/rc-entity-naming.md) (the `agent_actions` subsystem was added by this slice)