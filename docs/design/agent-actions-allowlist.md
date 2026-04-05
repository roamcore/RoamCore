# Agent Actions Allowlist (Roadmap)

Status: **Roadmap / design only** (no beta implementation yet)

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

