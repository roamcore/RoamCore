# Agent Actions Allowlist (Roadmap)

Status: **Roadmap + tier-b connection shipped** (Wave 3 #65; PR #69)

Goal: unlock the “talk to your van” wow-moment by allowing an agent to safely perform *some* actions, while keeping the system transparent, auditable, and default-deny.

Non-goal (beta): do **not** give an agent arbitrary Home Assistant service access.

---

## Principles

1) **Default deny**
   - If an action is not explicitly allowed, it cannot execute.

2) **User owns the policy**
   - Allowlist is a plain file on the RoamCore/Home Assistant box.
   - Human-readable.

3) **Transparency**
   - UI shows exactly what is permitted.
   - Every action has a stable `action_id` and description.

4) **Auditability**
   - Append-only action log (JSONL).
   - Includes who/what/why/inputs/result.

5) **Kill switch**
   - One toggle disables all agent actions.

6) **Constrained writes first**
   - Start with safe primitives:
     - set `input_*` helpers
     - run `script.rc_*`
   - Avoid direct device power switching early.

---

## Threat model (what we are preventing)

- agent calls dangerous HA services (heaters, fuel appliances, power switching)
- agent writes secrets / exfiltrates tokens
- agent toggles critical networking or breaks remote access
- “prompt injection” via entity names / attributes leading to unsafe tool use

Allowlist gateway limits blast radius: the agent can only do what the user explicitly allowed.

---

## Proposed architecture

### Components

1) **RoamCore action gateway** (single execution surface)
   - A Home Assistant service exposed by RoamCore, e.g.:
     - `roamcore.action_execute`
   - Agent calls *this* only.

2) **Allowlist policy file** (user-controlled)
   - Location (proposal):
     - `/config/.roamcore/agent_allowlist.yaml`

3) **Audit log** (append-only)
   - Location (proposal):
     - `/config/.roamcore/agent_action_log.jsonl`

4) **Global kill switch**
   - Stored as HA state (easy UI), e.g.:
     - `input_boolean.rc_agent_actions_enabled`

---

## Policy file format (proposal)

YAML for readability. Example:

```yaml
version: 1

defaults:
  require_confirmation: true

actions:
  - id: set_trip_wrapped_range
    description: "Set Trip Wrapped from/to ISO timestamps"
    kind: set_helper
    target:
      entity_id:
        - input_text.rc_trip_wrapped_from
        - input_text.rc_trip_wrapped_to
    constraints:
      # Only allow ISO8601 Zulu strings
      pattern: "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.?\\d*Z$"

  - id: generate_trip_wrapped
    description: "Generate Trip Wrapped latest report"
    kind: run_script
    target:
      entity_id: script.rc_trip_wrapped_run
    require_confirmation: false
```

### Supported kinds (v1)

- `set_helper`
  - only for `input_text`, `input_number`, `input_select`, `input_boolean`
  - constraints allowed:
    - numeric min/max
    - enum allowlist
    - regex pattern for strings

- `run_script`
  - only for scripts with `script.rc_*` prefix (recommended constraint)

Explicitly not supported initially:
- `homeassistant.turn_on/off`
- direct `switch.*` / `climate.*` / `cover.*`
- any service that can modify networking, users, add-ons

---

## Execution flow (proposal)

1) Agent proposes an action:
   - includes `action_id`, arguments, and a human explanation (“why”)

2) RoamCore validates:
   - global enabled toggle is ON
   - allowlist file present + parses
   - `action_id` exists
   - args satisfy constraints

3) If `require_confirmation=true`:
   - RoamCore should require an explicit confirmation step (UI or a second call)

4) RoamCore executes via HA service call

5) RoamCore writes an audit record:
   - timestamp
   - action_id
   - args
   - agent-reported reason
   - result (ok/error)

---

## UI/UX (proposal)

RoamCore Settings page should show:
- “Agent Actions: Disabled/Enabled” toggle (kill switch)
- “Allowed actions” list (id + description)
- recent action log (last N entries)
- big warning banner in beta if enabled

---

## Roadmap milestones

1) v1 (safe + boring)
   - set helpers + run scripts
   - audit log
   - kill switch

2) v2 (expanded)
   - limited device control via safe wrappers
   - per-action rate limits
   - better confirmation flows

3) v3 (community packs)
   - shareable allowlist “packs” with tests and recommended constraints

---

## Tier-b connection shipped (Wave 3 #65)

This design doc was promoted into a tier-b recipe connection on **2026-08-03** (Wave 3 #65, PR #69). The connection is at [`connections/agent-actions-allowlist/`](../../connections/agent-actions-allowlist/) and ships:

- The 11 `rc_agent_actions_*` contract tiles (the canonical RoamCore-side surface for the agent-actions umbrella: the single `input_boolean.rc_agent_actions_enabled` kill switch — already shipped in [`homeassistant/packages/roamcore_agent_actions.yaml`](../../homeassistant/packages/roamcore_agent_actions.yaml) and preserved verbatim — plus the `input_text.rc_agent_actions_policy_path` + `input_boolean.rc_agent_actions_require_confirmation` + `select.rc_agent_actions_default_duration` + `input_datetime.rc_agent_actions_session_expires_at` + `sensor.rc_agent_actions_seconds_until_expiry` + `sensor.rc_agent_actions_last_action_id` + `sensor.rc_agent_actions_last_action_at` + `sensor.rc_agent_actions_last_action_result` + `binary_sensor.rc_agent_actions_is_blocked_by_kill_switch` + `button.rc_agent_actions_disable_now` tiles).
- The full howto at [`connections/agent-actions-allowlist/docs/recipe.md`](../../connections/agent-actions-allowlist/docs/recipe.md) (1296 lines, 13 §sections — §1 What is Agent actions allowlist in RoamCore? + §2 Prerequisites + §3 The kill switch (already shipped) + §4 The policy file (operator-editable YAML) + §5 The action types (set_helper + run_script) + §6 The audit log (HA core `logbook` integration) + §7 RoamCore contract entities + §8 Automations (the FIVE MANDATORY ones — §8.1 kill-switch blocks everything + §8.2 session-timeout guard + §8.3 audit-log entry + §8.4 require-confirmation guard + §8.5 outside-allowlist deny-by-default) + §9 Troubleshooting (6 entries) + §10 Privacy + §11 Promoting to tier-a + §12 Files + §13 Cross-references).
- The 7 manifest-honesty tests at [`connections/agent-actions-allowlist/tests/test_connection_yml.py`](../../connections/agent-actions-allowlist/tests/test_connection_yml.py).
- The EXAMPLE policy file at [`connections/agent-actions-allowlist/docs/policy.example.yaml`](../../connections/agent-actions-allowlist/docs/policy.example.yaml) (operator-side documentation; the slice does NOT ship a custom YAML loader).
- The legacy catalog doc at [`docs/catalog/ai/agent-actions-allowlist.md`](../catalog/ai/agent-actions-allowlist.md) is now superseded by this connection (the SUPERSEDED banner is appended at the end of the doc).

The tier-b strategy is reuse-first over the upstream HA core `input_boolean` + `input_text` + `input_number` + `input_select` + `input_datetime` + `input_button` + `script` helpers (since 2022.x — auto-installed in every HA install) + the HA core `template:` sensor wrapper (since 2022.x) + the HA core `logbook` integration (since 2022.x — the canonical audit-log destination) + the upstream `script:` integration (since 2022.x — exposes the script-runner operator-wired setup flow for the §8.4 require-confirmation guard's `roamcore.action_confirm` wrapper + the §8.5 outside-allowlist deny-by-default guard's `roamcore.action_execute` wrapper). RoamCore does NOT fork any of these; the contract layer is a thin upstream-entity-aggregation wrapper + the vendor-neutral tile surface + the FIVE §8 MANDATORY automations.

The design philosophy above (default-deny + user owns the policy + transparency + auditability + kill switch + constrained writes first) is preserved verbatim by the connection. The roadmap milestones (v1 safe + boring / v2 expanded / v3 community packs) are also preserved verbatim; the tier-a promotion outline at recipe §11 documents the 8 canned-fixture bench artifacts that would be needed for a future RoamCore-owned agent-actions engine + integration code + integration tests against a real agent-actions engine bench.

