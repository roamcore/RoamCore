# OpenClaw JSON API — vendor-neutral machine-readable summary + skill + rc-dump + timeseries endpoints for local agents

**Tier:** A (native integration; tier-a-but-flagged — bench integration tests are still on the roadmap)
**Category:** ai
**Status:** beta

## What this connection is

OpenClaw JSON API — vendor-neutral machine-readable summary + skill + rc-dump + timeseries endpoints for local agents — the umbrella for "RoamCore exposes stable JSON endpoints for local agents (system summary + skill execution) so assistants can read state and (optionally) take safe actions" — is the ai-category complement to the broader RoamCore "show me everything" affordances. The umbrella wraps the existing RoamCore-owned custom component at `homeassistant/custom_components/roamcore_openclaw_api/` (233 lines of Python code: `__init__.py` + `view.py` + `const.py` + `manifest.json` — registers two `HomeAssistantView`s at `/api/roamcore/openclaw/summary` + `/api/roamcore/openclaw/skill` plus the diagnostic endpoint `/api/roamcore/openclaw/rc_dump` and the time-series endpoints `/api/roamcore/openclaw/timeseries/catalog` + `/api/roamcore/openclaw/timeseries`). The integration reads ONLY from `rc_*` contract entities (the 19 `rc_power_*` + `rc_location_*` + `rc_map_*` + `rc_level_*` upstream entities referenced by the integration's `view.py`), so the JSON payload stays vendor-neutral.

**This is the FIRST TRUE tier-a connection in the RoamCore connection pipeline.** All previous connection slices (fans / leveling / mode / demo-mode / advanced-mode) were tier-b recipes over UPSTREAM HA core helpers + `template:` wrappers + HACS add-ons. The OpenClaw JSON API is DIFFERENT: RoamCore ALREADY OWNS + SHIPS + MAINTAINS a real custom component (audited + smoketest-validated via `homeassistant/tools/openclaw_api_smoketest.sh`). The connection wraps the existing integration as a tier-a manifest so the audit pipeline can find it. The slice DOES NOT replace any of the existing code; it ADDS the `connections/openclaw-api/` recipe layer that:

1. Wraps the existing integration as a tier-a connection-style manifest so the audit pipeline can find it.
2. Defines the canonical 12 `rc_openclaw_api_*` contract tiles that the dashboard + OpenClaw queries use.
3. Wires the FIVE §8 MANDATORY automations (API-disabled → 404 guard + requires-auth-when-enabled guard + rc-dump-only-includes-rc_-prefix guard + agent-skill-discovery guard + contract-version-bump-notify guard).
4. Documents the upgrade path for tier-a promotion: when the existing custom component gains full pytest integration-test coverage (currently the smoketest is curl-based, not pytest), the connection can be promoted to a fully-fledged tier-a with bench fixtures.

## The 4-step operator flow

- **Step 1 — Enable** — the operator flips `input_boolean.rc_openclaw_api_enabled` ON (via the dashboard Settings → OpenClaw API → Connect / Setup toggle, or via the integration options flow, or via the `roamcore_openclaw_api.options_set` service, or directly via the legacy helper). The integration's `view.py` now serves the JSON endpoints (200 OK on `/summary` + `/skill` + `/rc_dump` + `/timeseries/*`).

- **Step 2 — Auth setup** — the operator flips `input_boolean.rc_openclaw_api_requires_auth` ON (recommended default; the helper package ships with `initial: false` for safety, but the spec recommends ON for any non-isolated LAN). If the operator wants auth, they must create a Home Assistant Long-Lived Access Token (LLAT) under Home Assistant → Profile → Long-Lived Access Tokens → Create Token, and provide that LLAT to their OpenClaw agent. If the operator wants no auth (only on isolated / trusted LANs), they leave `input_boolean.rc_openclaw_api_requires_auth` OFF. The §8.2 auth-required-when-enabled guard fires when the toggle is ON AND no LLAT is configured (red chip + critical notification).

- **Step 3 — Skill discovery** — the OpenClaw agent calls `/api/roamcore/openclaw/skill` to learn the summary URL + whether auth is required. The §8.4 agent-skill-discovery guard fires (logs the agent identity via user-agent header if present + writes an audit-log entry + surfaces a "new agent discovered" notification).

- **Step 4 — Live use** — the OpenClaw agent calls `/api/roamcore/openclaw/summary` periodically (and optionally `/rc_dump` + `/timeseries/*`). The §8.3 rc-dump-only-includes-rc_-prefix guard validates the response (filters to `rc_*` entity IDs; rejects vendor leaks). The §8.1 disabled-returns-404 guard handles disable events. The §8.2 auth-required-when-enabled guard surfaces misconfigurations. The §8.5 contract-version-bump-notify guard fires when the integration's `CONTRACT_VERSION` constant is bumped.

## Setup recipe (one-paragraph)

1. Install RoamCore via HACS (preferred) — the RoamCore HACS package bundles the `roamcore_openclaw_api` integration at `homeassistant/custom_components/roamcore_openclaw_api/`. Alternatively, copy `homeassistant/custom_components/roamcore_openclaw_api/` into your HA `/config/custom_components/` and add `roamcore_openclaw_api:` to `configuration.yaml` (the legacy path).
2. Ensure `homeassistant/packages/roamcore_openclaw_api_controls.yaml` is included in your HA packages — this declares the `input_boolean.rc_openclaw_api_enabled` + `input_boolean.rc_openclaw_api_requires_auth` helpers.
3. Add the integration: Settings → Devices & services → Add integration → **RoamCore**. Restart Home Assistant.
4. Configure the integration: Settings → Devices & services → **RoamCore** → Configure → Enable OpenClaw API. (One-tap install for the HACS path; the integration's options flow exposes the `enabled` + `requires_auth` toggles via the UI.)
5. Verify the curl smoketest passes:
   ```sh
   HA_BASE_URL=http://homeassistant.local:8123 bash homeassistant/tools/openclaw_api_smoketest.sh
   ```
6. (Recommended) Generate an LLAT under Home Assistant → Profile → Long-Lived Access Tokens → Create Token. Provide that LLAT to your OpenClaw agent.
7. Point your OpenClaw agent at `/api/roamcore/openclaw/skill` for discovery, then at `/api/roamcore/openclaw/summary` for live use. The agent-side skill is at `openclaw/skills/roamcore/SKILL.md`.

Full howto: see [`docs/recipe.md`](docs/recipe.md).

## The 12 `rc_openclaw_api_*` contract tiles

| Domain | Tile id | Purpose |
|---|---|---|
| `input_boolean` | `rc_openclaw_api_enabled` | Master enable toggle (404 when OFF, default OFF for safety). |
| `input_boolean` | `rc_openclaw_api_requires_auth` | Require Bearer-token auth (LLAT) when ON; recommended default ON. |
| `sensor` | `rc_openclaw_api_contract_version` | Mirrors the JSON endpoint's `contract.version` (currently `1`). |
| `sensor` | `rc_openclaw_api_last_request_at` | Timestamp of last `/summary` + `/skill` + `/rc_dump` request. |
| `sensor` | `rc_openclaw_api_request_count_24h` | Request counter rolling 24h. |
| `sensor` | `rc_openclaw_api_average_latency_ms` | p50 latency over the last 24h. |
| `binary_sensor` | `rc_openclaw_api_is_reachable` | Resolved reachability chip (true when `/summary` returns 200 in the last 5 min). |
| `binary_sensor` | `rc_openclaw_api_requires_auth_active` | Safety chip — true when auth is required AND no LLAT is configured. |
| `sensor` | `rc_openclaw_api_openclaw_summary_url` | Absolute URL of the summary endpoint (mirrors the `/skill` payload). |
| `sensor` | `rc_openclaw_api_skill_version` | Mirrors the skill payload's `contract.version` (currently `1`). |
| `button` | `rc_openclaw_api_test_now` | One-tap `/summary` GET to verify reachability. |
| `button` | `rc_openclaw_api_bust_cache` | One-tap cache invalidation for stale agents. |

## The 5 §8 MANDATORY automations

- **§8.1 API-disabled returns 404 guard** — fires when ANY dashboard query or OpenClaw agent call hits `/api/roamcore/openclaw/*` while `input_boolean.rc_openclaw_api_enabled` is OFF. Writes an audit-log entry + fires a warning notification so the operator knows the API is disabled (and is not, e.g., broken).
- **§8.2 Auth-required-when-enabled guard** — fires when `input_boolean.rc_openclaw_api_requires_auth` is ON AND no LLAT is configured. Surfaces a red "Auth required but no token configured" chip + writes an audit-log entry + fires a critical notification.
- **§8.3 RC-dump-only-includes-rc-prefix guard** — fires when an OpenClaw agent requests `/api/roamcore/openclaw/rc_dump` AND the response includes non-`rc_*` entity IDs. Double-checks the response payload + writes an audit-log entry if a non-`rc_*` entity leaked through.
- **§8.4 Agent-skill-discovery guard** — fires when an OpenClaw agent calls `/api/roamcore/openclaw/skill` for the first time in 24h. Logs the agent identity (best-effort, via the user-agent header if present) + writes an audit-log entry + surfaces a "new agent discovered" notification.
- **§8.5 Contract-version-bump-notify guard** — fires when the integration's `CONTRACT_VERSION` constant in `homeassistant/custom_components/roamcore_openclaw_api/const.py` is bumped. Surfaces a "OpenClaw API contract bumped to v{N+1}" critical notification + writes an audit-log entry + auto-bumps `sensor.rc_openclaw_api_contract_version`.

## Why tier-a-but-flagged (the bench-fixture gap)

Tier-a would require pytest integration tests against a controlled bench (a controlled environment with canned fixture responses for the `/summary` endpoint with all `rc_*` fields populated, the `/summary` endpoint with all `rc_*` fields null/unknown, the `/skill` endpoint with auth required + auth not required, the `/rc_dump` endpoint with a mix of `rc_*` + non-`rc_*` entities, the `/timeseries/catalog` + `/timeseries` endpoints, the 404 response when `input_boolean.rc_openclaw_api_enabled` is OFF, and the 401 response when auth is required but LLAT is missing — all wired together in a controlled environment). We have a curl-based smoketest (`homeassistant/tools/openclaw_api_smoketest.sh`) that exercises the JSON contract end-to-end, but no pytest bench fixtures for canned `/summary` + `/skill` + `/rc_dump` + `/timeseries` responses. Tier-a-but-flagged is the honest tier: the integration HAS real code (the 233-line custom component) + a curl smoketest + a canonical spec, but the bench fixture gap is documented in `tier_requirements.integration_tests` below (8 canned-response bench artifacts needed for full tier-a promotion).

The legacy catalog page (the legacy spec — 14-line tier-a claim stub) is preserved with a SUPERSEDED banner pointing at this connection (the legacy tier-a claim is HONEST — the integration IS real + RoamCore-owned + audited + smoketest-validated; this slice DOES NOT replace the existing code, only ADDS the connection-style manifest wrapper).

## Files

- `connection.yml` — the source-of-truth tier-a manifest.
- `__init__.py` — `DOMAIN = "openclaw_api"` marker for the audit.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (preserved with SUPERSEDED banner — the tier-a claim is HONEST): [the legacy spec](../../the legacy spec)
- Canonical contract spec: [`docs/reference/openclaw-json-api.md`](../../docs/reference/openclaw-json-api.md) (230 lines — the source of truth for the JSON payload shape + auth modes + endpoint catalog)
- Agent install guide: [`docs/howto/openclaw-roamcore-skill.md`](../../docs/howto/openclaw-roamcore-skill.md) (62 lines — the canonical operator-walk through for installing the RoamCore skill into an OpenClaw agent)
- Existing custom component: [`homeassistant/custom_components/roamcore_openclaw_api/`](../../homeassistant/custom_components/roamcore_openclaw_api/) (233 lines — the canonical implementation; registers the `HomeAssistantView`s at `/summary` + `/skill` + `/rc_dump` + `/timeseries/*`)
- Helper package: [`homeassistant/packages/roamcore_openclaw_api_controls.yaml`](../../homeassistant/packages/roamcore_openclaw_api_controls.yaml) (declares the `input_boolean.rc_openclaw_api_enabled` + `input_boolean.rc_openclaw_api_requires_auth` helpers)
- Curl smoketest: [`homeassistant/tools/openclaw_api_smoketest.sh`](../../homeassistant/tools/openclaw_api_smoketest.sh) (40 lines — validates the JSON contract stability)
- Agent-side skill: [`openclaw/skills/roamcore/SKILL.md`](../../openclaw/skills/roamcore/SKILL.md) (the canonical agent-side skill that consumes the JSON API)
- Mode (the §8.4 agent-skill-discovery guard's mode-aware notification): `connections/mode/` (Wave 3 #61)
- Advanced mode (the §8.5 contract-version-bump-notify guard's confirmation-required pattern): `connections/advanced-mode/` (Wave 3 #63)
- Demo mode (the §8.2 auth-required-when-enabled guard's safety-chip pattern): `connections/demo-mode/` (Wave 3 #62)
- Leveling (the §8.3 rc-dump-only-includes-rc-prefix guard's contract-layer filtering): `connections/leveling/` (Wave 3 #60)
- RoamCore entity naming: [`docs/reference/rc-entity-naming.md`](../../docs/reference/rc-entity-naming.md) (the `openclaw_api` subsystem was added by this slice)
