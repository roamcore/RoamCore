# OpenClaw JSON API (local agent contract)

**Support tier:** A (RoamCore native)

## What this is
RoamCore exposes stable JSON endpoints for local agents (system summary + skill execution + action confirmation + tamper-evident audit log) so assistants can read state and (only with your approval) take safe actions.

## Why it's useful in a van
- Ask "what's the system status?" in plain English
- Build safe, auditable automations through an agent interface
- Destructive changes (network settings, mode switches that affect hardware) ask for a confirmation code before they happen

## Extra hardware required
- None (runs inside Home Assistant)

## Install / best next step
- See: `docs/reference/openclaw-json-api.md`
- See: `docs/howto/openclaw-roamcore-skill.md`
- Custom component: `homeassistant/custom_components/roamcore_openclaw_api`
- HA package toggles/controls: `homeassistant/packages/roamcore_openclaw_api_controls.yaml`

## How agent confirmations work

When a local agent (Claude, GPT, your custom script) tries to make a
change to your RoamCore, RoamCore follows this rule:

**Anything that affects the van — power, network, mode, locks — stops
and asks you first.**

### The flow

1. **The agent asks.** Your agent POSTs the proposed change to
   `/api/roamcore/openclaw/actions`. Example: changing the network
   mode from "travel" to "camp" so the router hands out a different
   DHCP range.

2. **RoamCore decides.** RoamCore looks the action up in its
   allowlist (`.roamcore/agent_allowlist.yaml`). If the action is
   flagged `requires_confirmation: true` (destructive / irreversible /
   affects hardware), RoamCore holds it. If it's a non-destructive
   toggle, it runs immediately and writes an audit record.

3. **You get a code.** For destructive actions, RoamCore generates a
   6-digit code + sends a Home Assistant persistent notification to
   your phone. The notification says, in plain English:

   > An agent wants to change your network settings on your RoamCore.
   > Code: **427319**. To approve, POST
   > `/api/roamcore/openclaw/actions/abc123/confirm` with
   > `{"code": "427319"}`. To reject, just ignore — the code expires
   > in 5 minutes.

4. **You approve (or ignore).** If you approve within 5 minutes, the
   change goes through. If you ignore it, the code expires and nothing
   changes. If you (or someone else) types the wrong code 5 times,
   RoamCore locks that request out.

5. **It's recorded.** Every action — allowed, blocked, expired,
   rejected — gets a signed audit record in
   `.roamcore/roamcore_audit_chain.jsonl`. Each record hashes the
   previous one, so the chain is tamper-evident: if anyone edits a
   record after the fact, every record after it shows the break.

### Why it's safe

- **5-minute timer.** Codes expire. A leaked code is only useful for
  5 minutes.
- **5-attempt cap.** Wrong code 5 times → blocked. Brute-forcing a
  6-digit code (1M possibilities) is hopeless inside the window.
- **No silent changes.** RoamCore will not change your network, power,
  mode, or locks without a fresh, in-window code.
- **Full audit trail.** Every code generation, every confirmation
  attempt, every allow/deny decision is logged with a SHA-256
  signature chain.
- **Per-action allowlist.** Even non-destructive actions are gated by
  the allowlist. An agent cannot just call any HA service — only the
  ones you explicitly listed.

### Plain-English errors

When something goes wrong, RoamCore tries to tell you what's actually
broken in words, not codes. Examples:

| What happened | What the API returns | What the user sees |
|---|---|---|
| Agent tries to call an action not on the allowlist | `{"ok": false, "error": "unknown_action", "hint": "Action 'foo.bar' is not on the agent allowlist. Add it to .roamcore/agent_allowlist.yaml or call a different endpoint."}` | The agent reads this back to the user |
| Agent sends a parameter that violates a constraint | `{"ok": false, "error": "constraint_violation", "field": "mode", "hint": "Parameter 'mode' violates the allowlist (value not in enum allowlist)."}` | The agent reads this back to the user |
| Agent tries to change the network without confirming | `{"ok": true, "status": "confirmation_required", "code": "427319", "hint": "We need your confirmation before making this change. ..."}` | User sees the persistent notification |
| User types the wrong code | `{"ok": false, "status": "rejected", "attempts_remaining": 4, "hint": "That code didn't match. You have 4 attempt(s) left before we block the request."}` | The user retries or gives up |
| Code has expired | `{"ok": false, "status": "expired", "hint": "That confirmation code expired. Ask the agent to try again if you still want the change."}` | User asks the agent to re-request |
| 5 wrong attempts | `{"ok": false, "status": "blocked", "hint": "Too many wrong codes — we blocked that request. Ask the agent to try again if you still want the change."}` | User asks the agent to re-request |

### Where to look

- **Settings UI:** Connectivity → OpenClaw → "Last action" tile
  (`binary_sensor.rc_openclaw_api_last_action`) lights up for 60s after
  any confirmed or blocked action.
- **Audit log (raw):** `<config_dir>/.roamcore/roamcore_audit_chain.jsonl`
  on the Home Assistant host. Inspect with `cat`, `less`, `grep`.
- **Audit log (verify):** `python3 -c "from homeassistant.custom_components.roamcore.audit import verify_chain, audit_chain_path; print(verify_chain(audit_chain_path('/config')))"`
- **Notification feed:** the HA mobile app's notifications panel —
  every destructive-agent request lives there until you act on it.

### Operator backup note

The audit chain is sensitive. **Include
`<config_dir>/.roamcore/roamcore_audit_chain.jsonl` in every Home
Assistant Full Backup.** Without that snapshot, historical chain
verification becomes impossible after a restore.

## Links
- `docs/reference/openclaw-json-api.md` — canonical contract spec
- `docs/howto/openclaw-roamcore-skill.md` — how to wire up an agent
- `connections/openclaw-api/connection.yml` — connection manifest
- `homeassistant/custom_components/roamcore/audit.py` — audit chain source

---

## SUPERSEDED (2026-08-03)

The tier-a claim above is **HONEST** — the integration at
`homeassistant/custom_components/roamcore_openclaw_api/`
IS RoamCore-owned + maintained + the canonical spec lives
at `docs/reference/openclaw-json-api.md`.

This catalog page is now superseded by the connection
manifest at
[`connections/openclaw-api/connection.yml`](../../connections/openclaw-api/connection.yml).

The connection wraps the existing custom component as
a tier-a connection (real RoamCore-owned integration
code + operator-wired setup flow via the HACS-installed
RoamCore integration's options flow) but flags the
bench-fixture gap (no pytest integration tests; the
smoketest is curl-based) so the audit doesn't false-
positive on tier-a promotion. The 12
`rc_openclaw_api_*` contract tiles + the FIVE §8
MANDATORY automations are documented in
[`connections/openclaw-api/docs/recipe.md`](../../connections/openclaw-api/docs/recipe.md).

The Gate D confirmation flow (Wave 9 #113) is documented
above; it is implemented in
`homeassistant/custom_components/roamcore/audit.py` +
`actions.py` + `openclaw_view.py` and tested by
`homeassistant/custom_components/roamcore/tests/test_audit.py` +
`test_confirmation.py`.

See PR #113 for the confirmation + audit slice.
See PR #68 for the original tier-a connection slice.