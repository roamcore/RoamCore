# OpenClaw JSON API (local agent contract)

**Support tier:** A (RoamCore native)

## What this is
RoamCore exposes stable JSON endpoints for local agents (system summary + skill execution) so assistants can read state and (optionally) take safe actions.

## Why it’s useful in a van
- Ask “what’s the system status?” in plain English
- Build safe, auditable automations through an agent interface

## Extra hardware required
- None (runs inside Home Assistant)

## Install / best next step
- See: `docs/reference/openclaw-json-api.md`
- See: `docs/howto/openclaw-roamcore-skill.md`
- Custom component: `homeassistant/custom_components/roamcore_openclaw_api`
- HA package toggles/controls: `homeassistant/packages/roamcore_openclaw_api_controls.yaml`

## Links
- (Add OpenClaw resources here later)

---

## SUPERSEDED (2026-08-03)

The tier-a claim above is **HONEST** — the integration at
`homeassistant/custom_components/roamcore_openclaw_api/`
(233 lines, real code, real endpoints, real smoketest at
`homeassistant/tools/openclaw_api_smoketest.sh`) IS
RoamCore-owned + maintained + the canonical spec lives
at `docs/reference/openclaw-json-api.md` (230 lines).

This catalog page is now superseded by the connection
manifest at
[`connections/openclaw-api/connection.yml`](../../../connections/openclaw-api/connection.yml).

The connection wraps the existing custom component as
a tier-a connection (real RoamCore-owned integration
code + operator-wired setup flow via the HACS-installed
RoamCore integration's options flow) but flags the
bench-fixture gap (no pytest integration tests; the
smoketest is curl-based) so the audit doesn't false-
positive on tier-a promotion. The 12
`rc_openclaw_api_*` contract tiles + the FIVE §8
MANDATORY automations are documented in
[`connections/openclaw-api/docs/recipe.md`](../../../connections/openclaw-api/docs/recipe.md).

Migration:
- HACS-installed RoamCore: no action needed — the
  connection is bundled.
- Legacy `roamcore_openclaw_api` install (via
  `configuration.yaml:`): the connection manifest
  applies; the legacy integration is the canonical
  implementation; no migration required.

See PR #68 for the slice commit.
