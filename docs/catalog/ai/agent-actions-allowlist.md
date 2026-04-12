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
