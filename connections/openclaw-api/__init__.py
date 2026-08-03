"""RoamCore connection: OpenClaw JSON API — vendor-neutral
machine-readable summary + skill + rc-dump + timeseries
endpoints for local agents — tier-a connection.

This is a TIER-A connection that wraps the existing
RoamCore-owned custom component at
`homeassistant/custom_components/roamcore_openclaw_api/`.

The custom component registers two `HomeAssistantView`s
at `/api/roamcore/openclaw/summary` and
`/api/roamcore/openclaw/skill`, plus the diagnostic
endpoint `/api/roamcore/openclaw/rc_dump` and the
time-series endpoints
`/api/roamcore/openclaw/timeseries/catalog` and
`/api/roamcore/openclaw/timeseries`. The integration
reads ONLY from `rc_*` contract entities (the 19
`rc_power_*` + `rc_location_*` + `rc_map_*` + `rc_level_*`
upstream entities), so the JSON payload stays vendor-
neutral. The canonical contract spec lives at
`docs/reference/openclaw-json-api.md` (230 lines); the
canonical agent install guide lives at
`docs/howto/openclaw-roamcore-skill.md` (62 lines); the
canonical curl smoketest lives at
`homeassistant/tools/openclaw_api_smoketest.sh` (40
lines, validates `contract.version == 1` + the top-
level keys `power`, `map`, `level`, `debug` are
present in `/summary` + `contract.version == 1` +
`openclaw_summary_url` + `requires_auth` +
`summary_contract` are present in `/skill`).

This file is just the connection manifest marker
(`DOMAIN = "openclaw_api"`) used by the audit script
to detect the connection. The actual integration
lives in `homeassistant/custom_components/roamcore_openclaw_api/`.

The connection's recipe + contract tiles + FIVE §8
MANDATORY automations are documented in
`connections/openclaw-api/docs/recipe.md`.

The integration's GUI flow (Settings → Devices &
services → Add integration → RoamCore → Configure →
Enable OpenClaw API) is the canonical operator-wired
setup flow for the HACS-installed RoamCore
integration. The legacy `roamcore_openclaw_api`
package toggle at
`homeassistant/packages/roamcore_openclaw_api_controls.yaml`
is the legacy alternative (operator flips the
`input_boolean.rc_openclaw_api_enabled` helper ON
directly via the helper, or via the integration's
`roamcore_openclaw_api.options_set` service, or via
the dashboard Settings → OpenClaw API → Connect /
Setup toggle).

The umbrella publishes the resulting data via the
existing RoamCore-owned custom component at
`homeassistant/custom_components/roamcore_openclaw_api/`
(registers two `HomeAssistantView`s at
`/api/roamcore/openclaw/summary` +
`/api/roamcore/openclaw/skill` + the diagnostic
endpoint `/api/roamcore/openclaw/rc_dump` + the time-
series endpoints `/api/roamcore/openclaw/timeseries/
catalog` + `/api/roamcore/openclaw/timeseries`), then
publishes the RoamCore openclaw-api contract tiles on
top (the 12 contract entities documented in the
manifest's `dashboard.tiles` list — 2 input_boolean
helpers (enabled + requires_auth) + 6 sensors
(contract_version + last_request_at + request_count_24h
+ average_latency_ms + openclaw_summary_url +
skill_version) + 2 binary_sensors (is_reachable +
requires_auth_active) + 2 buttons (test_now +
bust_cache) = 12 contract entities).

The audit + boundary CI can detect an `openclaw-api/`
folder that claims to be a connection via the `DOMAIN`
constant exported here. The wizard reads the manifest
+ recipe at runtime.

The real per-operator openclaw-api affordance path is:

    Operator-side choice of the FOUR-step flow (Enable ->
        Auth setup -> Skill discovery -> Live use)
        -> existing custom component
           (`homeassistant/custom_components/roamcore_openclaw_api/`)
           -> the integration's `view.py` registers the
              `HomeAssistantView`s at
              `/api/roamcore/openclaw/summary` +
              `/api/roamcore/openclaw/skill` +
              `/api/roamcore/openclaw/rc_dump` +
              `/api/roamcore/openclaw/timeseries/*`
        -> existing helper entities (the HA core
           `input_boolean.rc_openclaw_api_enabled` +
           `input_boolean.rc_openclaw_api_requires_auth`
           from `homeassistant/packages/roamcore_openclaw_api_controls.yaml`)
        -> existing upstream contract entities (the 19
           `rc_power_*` + `rc_location_*` + `rc_map_*` +
           `rc_level_*` entities referenced by the
           integration's `view.py`)
        -> the RoamCore contract layer (the 12
           `rc_openclaw_api_*` tiles documented in the
           manifest's `dashboard.tiles` list — mostly
           `template:` sensors + `binary_sensor:`
           derivations + `input_boolean` helpers +
           `input_button` helpers derived from the
           integration's audit-log entries + the
           upstream contract entities)
        -> dashboard tiles + OpenClaw queries
            ("is the OpenClaw API reachable?",
             "what's the average latency?",
             "when was the last request?",
             "how many requests in the last 24h?",
             "is auth required and no LLAT configured?",
             "what's the contract version?",
             "what's the summary URL?",
             "test reachability now",
             "bust cache")

    Safety interlocks (the recipe is the contract layer;
    the automation wrappers are documented in §8):
        -> The RoamCore API-disabled returns 404 guard is
           the §8.1 automation that fires when ANY
           dashboard query or OpenClaw agent call hits
           `/api/roamcore/openclaw/*` while
           `input_boolean.rc_openclaw_api_enabled` is
           OFF. The integration's `view.py` already
           handles this (returns HTTP 404 with
           `{"ok": false, "error": "disabled"}`), but the
           §8.1 automation fires an audit-log entry + a
           warning notification so the operator knows
           the API is disabled (and is not, e.g.,
           broken).
        -> The RoamCore auth-required-when-enabled
           guard is the §8.2 automation that fires when
           `input_boolean.rc_openclaw_api_requires_auth`
           is ON AND no LLAT is configured in the
           operator's Home Assistant user profile. The
           automation surfaces a red "Auth required but
           no token configured" chip + writes an audit-
           log entry + fires a critical notification.
           Without this guard, a misconfigured deployment
           could expose the API without auth.
        -> The RoamCore rc-dump-only-includes-rc-
           prefix guard is the §8.3 automation that
           fires when an OpenClaw agent requests
           `/api/roamcore/openclaw/rc_dump` AND the
           response includes non-`rc_*` entity IDs (which
           would leak vendor entity IDs into the agent's
           working memory — defeating the entire point of
           the `rc_*` contract layer). The integration's
           `view.py` already filters to `.rc_`-prefixed
           entities, but the §8.3 automation double-
           checks the response payload + writes an
           audit-log entry if a non-`rc_*` entity leaked
           through.
        -> The RoamCore agent-skill-discovery guard is
           the §8.4 automation that fires when an
           OpenClaw agent calls
           `/api/roamcore/openclaw/skill` for the first
           time in 24h. The automation logs the agent
           identity (best-effort, via the user-agent
           header if present) + writes an audit-log
           entry + surfaces a "new agent discovered"
           notification. This is the trust-but-verify
           layer: the operator can see who has connected
           to the API.
        -> The RoamCore contract-version-bump-notify
           guard is the §8.5 automation that fires when
           the integration's `CONTRACT_VERSION` constant
           in `homeassistant/custom_components/
           roamcore_openclaw_api/const.py` is bumped.
           The automation surfaces a "OpenClaw API
           contract bumped to v{N+1}" critical
           notification + writes an audit-log entry +
           auto-bumps
           `sensor.rc_openclaw_api_contract_version`.
           This is the dashboard-side companion to the
           integration's bump; the operator knows
           immediately when the contract changes.

    Cross-references:
        -> The RoamCore-owned custom component at
           `homeassistant/custom_components/roamcore_openclaw_api/`
           is the canonical umbrella (registers the JSON
           endpoints; reads from `rc_*` upstream
           entities).
        -> The HA core `input_boolean` helper at
           `homeassistant/packages/roamcore_openclaw_api_controls.yaml`
           is the canonical enable / requires-auth toggle
           storage.
        -> The curl smoketest at
           `homeassistant/tools/openclaw_api_smoketest.sh`
           is the canonical smoke check for the JSON
           contract stability (validates `contract.
           version == 1` + the top-level keys `power`,
           `map`, `level`, `debug` are present in
           `/summary` + `contract.version == 1` +
           `openclaw_summary_url` + `requires_auth` +
           `summary_contract` are present in `/skill`).
        -> The canonical contract spec at
           `docs/reference/openclaw-json-api.md`
           (230 lines) is the source of truth for the
           JSON payload shape + auth modes + endpoint
           catalog.
        -> The agent install guide at
           `docs/howto/openclaw-roamcore-skill.md`
           (62 lines) is the canonical operator-walk
           through for installing the RoamCore skill
           into an OpenClaw agent.
        -> The agent-side skill at
           `openclaw/skills/roamcore/SKILL.md` is the
           canonical agent-side skill that consumes the
           JSON API.
        -> The mode Wave 3 #61 connection cross-
           references the §8.4 agent-skill-discovery
           guard's mode-aware notification (the guard
           surfaces new-agent-discovery notifications on
           the mode-change notification timeline).
        -> The advanced-mode Wave 3 #63 connection
           cross-references the §8.5 contract-version-
           bump-notify guard's confirmation-required
           pattern (mirrors the advanced-mode §8.1
           confirm-before-toggle-on guard's confirm-flag
           pattern — both require operator-side
           confirmation before exposing new
           functionality).
        -> The demo-mode Wave 3 #62 connection cross-
           references the §8.2 auth-required-when-
           enabled guard's safety-chip pattern (mirrors
           the demo-mode §8.5 operator-only guard's
           safety-chip pattern).
        -> The leveling Wave 3 #60 connection cross-
           references the §8.3 rc-dump-only-includes-
           rc-prefix guard's contract-layer filtering
           (mirrors the leveling §8.5 fridge-safe gate's
           contract-layer filtering).

See docs/recipe.md for the full howto (the existing
custom component install + the HA core `input_boolean`
helpers install + the FOUR-step operator flow + the 12
`rc_openclaw_api_*` contract tiles + the FIVE §8
MANDATORY automations + the 6 §9 troubleshooting
entries + privacy + tier-a promotion outline).
"""

DOMAIN = "openclaw_api"
