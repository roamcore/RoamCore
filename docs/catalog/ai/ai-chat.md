# AI Chat (opt-in)

## Why it’s useful in a van
When you’re in the field, you often want **answers and actions without digging through dashboards**.
AI Chat is an **optional** interface that lets you ask plain-English questions about your RoamCore system (and, later, trigger safe actions).

Examples:
- “Do I have enough battery to run the heater tonight?”
- “What changed in the last 24 hours?”
- “Is anything in an error state right now?”

**Privacy note:** This is opt-in by design. You choose whether any cloud AI is used.

**Support tier:** Proposed C (Experimental) — **pending Bernard sign-off**

## What this is
A user-facing chat layer that sits on top of RoamCore’s structured system summary.

Initial scope (Beta-friendly):
- opt-in toggle (default off)
- read-only answers from local/system data

## What you need
- RoamCore installed in Home Assistant
- (Optional) an AI provider account if you enable cloud AI

## How it works (high level)
1) RoamCore exposes a deterministic system summary.
2) Chat consumes that summary and produces a plain-language response.
3) (Later) safe actions can be enabled behind an allowlist + audit log.

## Setup (placeholder)
- Coming soon: a wizard step + an opt-in toggle.

## Troubleshooting
- If chat is not visible, confirm the opt-in toggle is enabled.

## Links
- See also: OpenClaw JSON API (local agent contract)
