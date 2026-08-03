# Advanced mode — vendor-neutral power-user toggle + session-timeout guard + destructive-calls block

**Tier:** B (recipe)
**Category:** ai
**Status:** beta

## What this connection is

Advanced mode — vendor-neutral power-user toggle + session-timeout guard + destructive-calls block — the umbrella for "RoamCore includes an Advanced Mode toggle that can reveal extra controls and diagnostics without cluttering the default UI. Keeps the dashboard clean for daily use. Still gives power users access to deeper controls when needed" — is the ai-category complement to the broader RoamCore "show me everything" affordances. The "confirmed" toggle is the operator's confirm-flag (an "I understand advanced mode exposes destructive irreversible service calls" acknowledgement; OFF by default); the master "enabled" toggle is the operator's master enable (OFF by default; must be operator-confirmed ON before advanced controls surface in the dashboard); the "session expires at" timestamp is the auto-revert deadline (set to "now + selected duration" when the toggle is flipped ON; default 24 hours); the "seconds until expiry" tile is the resolved countdown timer; the "session action count" tile is the number of destructive irreversible service calls the operator has initiated while advanced mode is ON in the current session; the "last action at" tile is the timestamp of the last destructive irreversible service call; the "is active" binary_sensor is the resolved active chip (true when advanced mode is ON AND the confirm-flag is ON AND the session has not expired); the "is blocking destructive calls" binary_sensor is the safety chip (should ALWAYS be true when the toggle is OFF; turns red if a misconfiguration would let a destructive service call slip through); the "session duration" select is the operator-pickable auto-revert duration (1 hour / 6 hours / 24 hours / 7 days / Never); the "enable" button is the operator-triggered one-tap enable; the "disable now" button is the operator-triggered one-tap disable.

RoamCore ships **no** native advanced-mode engine. We RECIPE the well-understood upstream HA core `input_boolean` + `input_text` + `input_datetime` + `input_button` + `select` helper entities (since 2022.x — expose a GUI flow for the operator to add the helper entities from the HA UI under Settings → Helpers) + the HA core `template:` sensor wrapper (since 2022.x — expose a GUI flow for the operator to add a derived `sensor.*` entity from the upstream sensors) + the HA core `template:` binary_sensor wrapper (since 2022.x — expose a GUI flow for the operator to add a derived `binary_sensor.*` entity from the upstream sensors). The 11 `rc_advanced_mode_*` contract tiles are the vendor-neutral layer the dashboard + OpenClaw queries use; the actual advanced-mode logic is provided by the upstream HA core `input_boolean` + `input_text` + `input_datetime` + `input_button` + `select` helper entities + the HA core `template:` sensor wrapper + the HA core `template:` binary_sensor wrapper (RoamCore does NOT fork any of these).

## The 4-step operator flow

- **Step 1 — Confirm** — the operator flips `input_boolean.rc_advanced_mode_confirmed` ON, acknowledging "I understand advanced mode exposes destructive irreversible service calls". Without this confirm, advanced controls stay hidden even if the master toggle is ON.

- **Step 2 — Enable** — the operator flips `input_boolean.rc_advanced_mode_enabled` ON (or presses `button.rc_advanced_mode_enable`). The dashboard now shows the "advanced" badge + reveals the hidden diagnostics tiles + unlocks the operator-only controls.

- **Step 3 — Session window** — once enabled, advanced mode stays ON until either the operator disables it OR the `input_datetime.rc_advanced_mode_session_expires_at` timestamp is reached (default: 24 hours, controlled by the `select.rc_advanced_mode_session_duration` selector 1h / 6h / 24h / 7d / Never). After timeout, the toggle auto-reverts to OFF.

- **Step 4 — Audit + revert** — every destructive irreversible service call the operator initiates while advanced mode is ON is logged to `sensor.rc_advanced_mode_last_action_at` + counted in `sensor.rc_advanced_mode_session_action_count`. The operator can revert at any time via `button.rc_advanced_mode_disable_now`.

## Setup recipe (one-paragraph)

1. Decide if you want advanced mode (most operators: leave OFF).
2. Set up the upstream helpers:
   - **HA core `input_boolean` + `input_text` + `input_datetime` + `input_button` + `select` helpers** — auto-installed in every HA install + exposed via the HA UI under Settings → Helpers. The operator creates the helper entities via the HA UI (or via `input_boolean:` / `input_text:` / `input_datetime:` / `input_button:` / `select:` YAML blocks).
3. Wire the upstream destructive irreversible service call targets:
   - Populate `input_text.rc_advanced_mode_destructive_call_targets` with the comma-separated list of destructive irreversible service names the §8.5 destructive-calls block should protect (e.g. `switch.turn_off, climate.turn_off, script.rc_factory_reset`).
4. Configure the operator-facing `input_boolean.rc_advanced_mode_confirmed` + `input_boolean.rc_advanced_mode_enabled` + `input_datetime.rc_advanced_mode_session_expires_at` + `sensor.rc_advanced_mode_seconds_until_expiry` + `sensor.rc_advanced_mode_session_action_count` + `sensor.rc_advanced_mode_last_action_at` + `binary_sensor.rc_advanced_mode_is_active` + `binary_sensor.rc_advanced_mode_is_blocking_destructive_calls` + `select.rc_advanced_mode_session_duration` + `button.rc_advanced_mode_enable` + `button.rc_advanced_mode_disable_now` contract tiles to point at the upstream helpers + the `template:` wrappers.
5. Wire the FIVE §8 MANDATORY automations (confirm-before-toggle-on guard + auto-disable after session timeout + hides-for-non-owners guard + audit-log entry + blocks-destructive-irreversible-service-calls guard).
6. Verify: flip the confirm-flag ON → flip the master enable toggle ON → check the dashboard surfaces the "advanced active" badge → check the countdown timer ticks down → trigger a destructive irreversible service call → check the audit-log entry fires → wait for the expiry timestamp → check the §8.2 auto-disable guard fires + clears the enable toggle.

Full howto: see [`docs/recipe.md`](docs/recipe.md).

## The 11 `rc_advanced_mode_*` contract tiles

| Domain | Tile id | Purpose |
|---|---|---|
| `input_boolean` | `rc_advanced_mode_confirmed` | Confirm-flag — operator must flip ON to acknowledge destructive calls. |
| `input_boolean` | `rc_advanced_mode_enabled` | Master enable toggle (OFF by default). |
| `input_datetime` | `rc_advanced_mode_session_expires_at` | Session expiry timestamp ("now + selected duration"). |
| `sensor` | `rc_advanced_mode_seconds_until_expiry` | Resolved countdown timer. |
| `sensor` | `rc_advanced_mode_session_action_count` | Destructive-call counter (resets on session change). |
| `sensor` | `rc_advanced_mode_last_action_at` | Last destructive-call timestamp. |
| `binary_sensor` | `rc_advanced_mode_is_active` | Resolved active chip (confirm + enable + not expired). |
| `binary_sensor` | `rc_advanced_mode_is_blocking_destructive_calls` | Safety chip — should ALWAYS be true when toggle is OFF. |
| `select` | `rc_advanced_mode_session_duration` | 1h / 6h / 24h / 7d / Never (default 24h). |
| `button` | `rc_advanced_mode_enable` | One-tap enable advanced mode. |
| `button` | `rc_advanced_mode_disable_now` | One-tap disable advanced mode. |

## The 5 §8 MANDATORY automations

- **§8.1 Confirm-before-toggle-on guard** — fires when a non-operator source tries to flip `input_boolean.rc_advanced_mode_enabled` ON without first flipping `input_boolean.rc_advanced_mode_confirmed` ON. BLOCKS the enable flip + writes an audit-log entry + fires a notification.
- **§8.2 Auto-disable after session timeout** — fires when `input_datetime.rc_advanced_mode_session_expires_at` timestamp is reached. Clears the enable toggle + clears the session_expires_at + writes an audit-log entry + fires a notification.
- **§8.3 Hides-for-non-owners guard** — fires when a non-owner dashboard session attempts to view the advanced-mode dashboard page while the enable toggle is ON. Hides the advanced-mode tiles + surfaces an "advanced mode hidden for non-owners" banner + writes an audit-log entry.
- **§8.4 Audit-log entry on destructive call** — fires on every destructive irreversible service call the operator initiates while the enable toggle is ON. Writes an audit-log entry with the service name + the target entity + the operator identity + the timestamp.
- **§8.5 Blocks-destructive-irreversible-service-calls guard** — fires when ANY `script.*` / `automation.*` action tries to call a destructive irreversible service (the operator has flagged in `input_text.rc_advanced_mode_destructive_call_targets`) while the enable toggle is OFF. BLOCKS the service call + flips the safety chip + fires a critical notification.

## Why tier-b, not tier-a

Tier-a would require a RoamCore-owned advanced-mode engine + integration code + integration tests against a real advanced-mode engine bench (a controlled environment with canned fixture responses for session-expired events + canned fixture responses for destructive-service-call blocking events + canned fixture responses for non-owner dashboard session events — all wired together in a controlled environment). We have no operator-side advanced-mode engine bench on the CI to integration-test against (the bench requires the operator's chosen destructive irreversible service call targets + canned fixture responses for session-expired events — all wired together in a controlled environment). Tier-b is the honest tier: HA core `input_boolean` + `input_text` + `input_datetime` + `input_button` + `select` + HA core `template:` are all upstream / vendor / HACS / hardware code (not RoamCore-owned); the RoamCore wrapper is a thin upstream-entity-aggregation layer + the contract layer + the FIVE §8 MANDATORY automations. The recipe is sound but we cannot claim one-tap automation.

The legacy catalog page (the legacy spec — 13-line tier-a claim stub, originally listed "RoamCore includes an Advanced Mode toggle that can reveal extra controls and diagnostics without cluttering the default UI. Keeps the dashboard clean for daily use. Still gives power users access to deeper controls when needed. None. HA package: homeassistant/packages/roamcore_advanced_mode.yaml" with no recipe + no contract + no automations + no install path — just a placeholder with an aspirational tier-a claim) is now superseded by this tier-b recipe connection. The legacy tier-a claim was aspirational (no native RoamCore advanced-mode engine in the repo today); the picker is honest and ships the contract layer + the recipe + the §8 automations as tier-b.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "advanced_mode"` marker for the audit.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded by this slice): [the legacy spec](../../the legacy spec)
- HA core `input_boolean` integration (the canonical confirm-flag + enable-toggle helper umbrella): https://www.home-assistant.io/integrations/input_boolean/
- HA core `input_text` integration (the canonical destructive-call-targets helper): https://www.home-assistant.io/integrations/input_text/
- HA core `input_datetime` integration (the canonical session-expiry-timestamp helper): https://www.home-assistant.io/integrations/input_datetime/
- HA core `input_button` integration (the canonical enable / disable button helper): https://www.home-assistant.io/integrations/input_button/
- HA core `select` integration (the canonical session-duration picker helper): https://www.home-assistant.io/integrations/select/
- HA core `template:` integration (the canonical seconds-until-expiry + is-active + is-blocking-destructive-calls derivation): https://www.home-assistant.io/integrations/template/
- Time-atomic (the time-of-day primitives used by the §8.2 auto-disable-after-session-timeout guard's expiry timestamp): `connections/time-atomic/` (Wave 3 #55)
- Remote-access (the VPN primitive used by the §8.3 hides-for-non-owners guard's owner-identity check): `connections/remote-access/` (Wave 3 #58)
- Mode (the §8.4 audit-log entry's mode-change cross-reference): `connections/mode/` (Wave 3 #61)
- Demo-mode (the §8.1 confirm-before-toggle-on guard's confirm-flag pattern): `connections/demo-mode/` (Wave 3 #62)
- Leveling (the §8.5 blocks-destructive-irreversible-service-calls guard's levelling-jack protection cross-reference): `connections/leveling/` (Wave 3 #60)
- Fans (the §8.5 blocks-destructive-irreversible-service-calls guard's fan-protection cross-reference): `connections/fans/` (Wave 3 #59)
- RoamCore entity naming: `docs/reference/rc-entity-naming.md` (the `advanced_mode` subsystem was added by this slice)
