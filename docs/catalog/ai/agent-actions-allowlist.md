# Agent actions allowlist (safety gateway)

**Support tier:** A (RoamCore native)

## What this is
A safety layer that defaults to deny and only permits explicitly-allowed agent actions, with a kill switch.

## Why it’s useful in a van
- Lets you use automation/agents without fear of unexpected device control
- Clear boundary between “read-only” and “can change things”

## Extra hardware required
- None

## Install / best next step
- Design notes: `docs/design/agent-actions-allowlist.md`
- HA package: `homeassistant/packages/roamcore_agent_actions.yaml`

## Links
- (Add safety philosophy + examples)

---

> **SUPERSEDED — 2026-08-03.** The 12-line tier-a claim stub at this path has been promoted into a tier-b recipe connection at [`connections/agent-actions-allowlist/`](../../../../connections/agent-actions-allowlist/). The legacy tier-a "RoamCore native" claim is **honest-upstream-truth**: RoamCore ships **no** native agent-actions engine today; the contract layer + the recipe + the FIVE §8 MANDATORY automations are the canonical RoamCore contribution; the upstream engines are HA core `input_boolean` + `input_text` + `input_number` + `input_select` + `input_datetime` + `input_button` + `script` helpers (since 2022.x) + the HA core `template:` sensor wrapper (since 2022.x) + the HA core `logbook` integration (since 2022.x) + the upstream `script:` integration (since 2022.x). The single `input_boolean.rc_agent_actions_enabled` kill switch is **already shipped** in [`homeassistant/packages/roamcore_agent_actions.yaml`](../../../homeassistant/packages/roamcore_agent_actions.yaml) and is preserved verbatim by the slice; the slice ADDS the remaining 10 `rc_agent_actions_*` contract tiles + the recipe + the smoke + the FIVE §8 MANDATORY automations + the operator-side policy file format (with the EXAMPLE policy file at [`connections/agent-actions-allowlist/docs/policy.example.yaml`](../../../../connections/agent-actions-allowlist/docs/policy.example.yaml)). Replaced by the tier-b recipe connection; see [`connections/agent-actions-allowlist/` README](../../../../connections/agent-actions-allowlist/README.md) + [`connections/agent-actions-allowlist/docs/recipe.md`](../../../../connections/agent-actions-allowlist/docs/recipe.md). Wave 3 #65, PR #69.
