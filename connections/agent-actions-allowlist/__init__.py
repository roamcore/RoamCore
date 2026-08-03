"""Agent actions allowlist — vendor-neutral kill-switch +
per-action allowlist + audit-log gateway for safe agent-
driven RoamCore actions — tier-b recipe connection.

Note on upstream wiring: tier-b connections don't ship a
RoamCore-owned operator-wired setup flow (a RoamCore
operator-wired wizard); instead, each path uses the
upstream integration's GUI flow (the HA core `input_boolean`
+ `input_text` + `input_number` + `input_select` +
`input_datetime` + `input_button` + `script` helpers + the
HA core `template:` sensor wrapper + the HA core `logbook`
integration + the upstream `script:` integration all expose
their own operator-wired setup flow + GUI flow).

This module is a marker-only stub. Tier-b connections don't
ship native HA integration code; they publish a recipe
(docs/recipe.md) that walks the operator through installing
the upstream helpers + wiring the FIVE-step operator-
pickable agent-actions flow:

  - Confirm — confirm the kill switch is OFF (the
    `input_boolean.rc_agent_actions_enabled` is OFF by
    default; this tile is ALREADY shipped in
    `homeassistant/packages/roamcore_agent_actions.yaml`
    and is preserved verbatim — the package is not redefined
    by this slice). The §3 operator flow walks the operator
    through confirming the kill switch defaults are correct.

  - Mount the policy file — the operator copies
    `connections/agent-actions-allowlist/docs/policy.example.yaml`
    to `input_text.rc_agent_actions_policy_path` (default
    `/config/.roamcore/agent_allowlist.yaml`) and edits the
    policy file for their setup. The §4 operator flow walks
    the operator through populating the policy file's
    `actions:` list with the comma-separated list of
    `action_id` entries the agent is permitted to invoke
    (with per-action constraints: `set_helper` on
    `input_text.*` / `input_number.*` / `input_select.*` /
    `input_boolean.*` with regex pattern / numeric min-max
    / enum allowlist constraints; `run_script` on
    `script.rc_*` prefix with optional
    `require_confirmation` toggle).

  - Decide the default duration — the operator picks the
    session duration via
    `select.rc_agent_actions_default_duration` (Off / 1h /
    6h / 24h / 7d / Never; default 24h). The §5 operator
    flow walks the operator through choosing the duration
    and explains the §8.2 session-timeout guard's auto-
    disable semantics.

  - Enable with optional confirmation — the operator flips
    `input_boolean.rc_agent_actions_enabled` ON (or presses
    a future `button.rc_agent_actions_enable` if the
    operator adds one). The operator may toggle
    `input_boolean.rc_agent_actions_require_confirmation`
    ON (default ON) so the agent must call
    `roamcore.action_confirm` BEFORE `roamcore.action_
    execute`; the second call without confirmation short-
    circuits to `pending-confirmation`.

  - Audit + revert — every agent action invocation writes
    an entry to `sensor.rc_agent_actions_last_action_id` +
    `sensor.rc_agent_actions_last_action_at` +
    `sensor.rc_agent_actions_last_action_result` (and
    additionally tags the HA core `logbook` entry with the
    `agent_actions` tag for sortability). The operator can
    revert at any time via
    `button.rc_agent_actions_disable_now` (also turns the
    master kill switch OFF + clears the session expiry
    timestamp).

The umbrella publishes the resulting data via the upstream
HA core `input_boolean` + `input_text` + `input_number` +
`input_select` + `input_datetime` + `input_button` + `script`
helper entities (since 2022.x — have exposed the standard
`input_boolean.toggle` + `input_text.set_value` +
`input_number.set_value` + `input_select.select_option` +
`input_datetime.set_datetime` + `input_button.press` +
`script.*` services + the `input_boolean` / `input_text` /
`input_number` / `select` / `input_datetime` / `sensor` /
`binary_sensor` / `button` domain entities) + the HA core
`template:` sensor wrapper (since 2022.x — wraps any
upstream sensor state into a derived `sensor.*` entity) +
the HA core `logbook` integration (since 2022.x — the
canonical audit-log destination for Home Assistant
automations), then publishes the RoamCore agent-actions
contract tiles on top (the 11 contract entities documented
in connection.yml — 1 input_boolean agent_actions_enabled +
1 input_text agent_actions_policy_path + 1 input_boolean
agent_actions_require_confirmation + 1 select
agent_actions_default_duration + 1 input_datetime
agent_actions_session_expires_at + 1 sensor
agent_actions_seconds_until_expiry + 1 sensor
agent_actions_last_action_id + 1 sensor
agent_actions_last_action_at + 1 sensor
agent_actions_last_action_result + 1 binary_sensor
agent_actions_is_blocked_by_kill_switch + 1 button
agent_actions_disable_now = 11 contract entities).

The audit + boundary CI can detect an
`agent-actions-allowlist/` folder that claims to be a
connection via the `DOMAIN` constant exported here. The
wizard reads the manifest + recipe at runtime.

The real per-operator agent-actions affordance path is:

    Operator-side choice of the FIVE-step flow (Confirm
        -> Mount the policy file -> Decide the default
        duration -> Enable with optional confirmation ->
        Audit + revert)
        -> upstream entities (the HA core
           `input_boolean.rc_agent_actions_enabled` for the
           kill switch — already shipped in
           `homeassistant/packages/roamcore_agent_actions.yaml`;
           the HA core
           `input_text.rc_agent_actions_policy_path` for the
           policy file path; the HA core
           `input_boolean.rc_agent_actions_require_confirmation`
           for the confirmation toggle; the HA core
           `select.rc_agent_actions_default_duration` for
           the session duration picker; the HA core
           `input_datetime.rc_agent_actions_session_expires_at`
           for the session expiry timestamp; the HA core
           `sensor.rc_agent_actions_seconds_until_expiry`
           `template:` sensor for the resolved countdown;
           the HA core
           `sensor.rc_agent_actions_last_action_id`
           `template:` sensor for the last action_id; the
           HA core
           `sensor.rc_agent_actions_last_action_at`
           `template:` sensor for the last action timestamp;
           the HA core
           `sensor.rc_agent_actions_last_action_result`
           `template:` sensor for the last action result;
           the HA core
           `binary_sensor.rc_agent_actions_is_blocked_by_kill_switch`
           for the safety chip; the HA core
           `button.rc_agent_actions_disable_now` for the
           operator-triggered one-tap emergency off)
        -> upstream signals (the operator's policy file at
           `input_text.rc_agent_actions_policy_path` —
           operator edits the policy file to populate the
           `actions:` list with the per-action entries the
           agent is permitted to invoke; the
           `roamcore.action_execute` and
           `roamcore.action_confirm` upstream script-runner
           wrappers surface the agent's proposed action_id
           to the policy file + the audit log)
        -> RoamCore contract layer (HA core `template:`
           sensor + binary_sensor + select + the operator's
           `input_boolean` / `input_text` / `input_number` /
           `input_select` / `input_datetime` / `input_button`
           for the contract tiles + the `script:` integration
           for the upstream `roamcore.action_execute` +
           `roamcore.action_confirm` wrappers + the `logbook`
           integration for the §8.3 audit-log entry)
        -> dashboard tiles + OpenClaw queries
            ("are agent actions enabled?",
             "what is the agent actions policy file path?",
             "does the agent actions require confirmation?",
             "what is the default agent actions duration?",
             "when does the agent actions session expire?",
             "what was the last agent action?",
             "what was the last agent action result?",
             "is the agent actions kill switch blocking?",
             "disable agent actions now")

    Safety interlocks (the recipe is the contract layer;
    the automation wrappers are documented in §8):
        -> The RoamCore kill-switch-blocks-everything guard
           is the §8.1 automation that fires when ANY
           `script.*` / `automation.*` action tries to
           invoke the `roamcore.action_execute` service
           while `input_boolean.rc_agent_actions_enabled`
           is OFF. The automation BLOCKS the invocation +
           short-circuits to the `denied` result + flips
           `binary_sensor.rc_agent_actions_is_blocked_by_
           kill_switch` to TRUE + writes an audit-log entry
           + fires a critical notification warning the
           operator that the kill switch is OFF.
        -> The RoamCore session-timeout guard is the §8.2
           automation that fires when
           `sensor.rc_agent_actions_seconds_until_expiry`
           reaches 0 (i.e. the
           `input_datetime.rc_agent_actions_session_expires_at`
           timestamp is reached). The automation clears the
           enable toggle + clears the session_expires_at +
           writes a `session_expired` audit-log entry +
           fires a notification warning the operator that
           agent actions have been auto-disabled.
        -> The RoamCore audit-log-entry guard is the §8.3
           automation that fires on every agent action
           invocation. The automation writes an entry to
           `sensor.rc_agent_actions_last_action_id` +
           `sensor.rc_agent_actions_last_action_at` +
           `sensor.rc_agent_actions_last_action_result` +
           additionally tags the HA core `logbook` entry
           with the `agent_actions` tag for sortability.
        -> The RoamCore require-confirmation guard is the
           §8.4 automation that fires when
           `input_boolean.rc_agent_actions_require_confirmation`
           is ON AND a `script.*` / `automation.*` action
           tries to invoke `roamcore.action_execute`
           WITHOUT a prior `roamcore.action_confirm` call
           from the same agent identity. The automation
           BLOCKS the invocation + short-circuits to
           `pending-confirmation` + writes an audit-log
           entry + fires a notification warning the
           operator that the agent must confirm the action
           first.
        -> The RoamCore outside-allowlist deny-by-default
           guard is the §8.5 automation that fires when
           ANY `script.*` / `automation.*` action tries to
           invoke `roamcore.action_execute` with an
           `action_id` that is NOT in the operator's policy
           file at
           `input_text.rc_agent_actions_policy_path`. The
           automation BLOCKS the invocation + short-circuits
           to `denied` + writes a `denied` audit-log entry
           + fires a critical notification warning the
           operator that the agent attempted an action
           outside the allowlist.

    Cross-references:
        -> The HA core `input_boolean` + `input_text` +
           `input_number` + `input_select` +
           `input_datetime` + `input_button` + `script`
           helper entities are the canonical umbrella
           (since 2022.x — expose the standard contract).
        -> The HA core `template:` sensor wrapper is the
           canonical seconds-until-expiry + last-action-id
           + last-action-at + last-action-result derivation
           (since 2022.x).
        -> The HA core `logbook` integration is the
           canonical audit-log destination for Home
           Assistant automations (since 2022.x).
        -> The upstream `script:` integration is the
           canonical wrapper for the §8.4 require-
           confirmation guard's `roamcore.action_confirm`
           wrapper + the §8.5 outside-allowlist deny-by-
           default guard's `roamcore.action_execute`
           wrapper.
        -> The time-atomic Wave 3 #55 connection cross-
           references the time-of-day primitives used by
           the §8.2 session-timeout guard's expiry
           timestamp.
        -> The remote-access Wave 3 #58 connection cross-
           references the VPN primitive used by the §8.4
           require-confirmation guard's owner-identity
           check.
        -> The approach lights Wave 3 #52 connection cross-
           references the dashboard banner pattern used by
           the §8.3 audit-log entry.
        -> The fans Wave 3 #59 connection cross-references
           the §8.1 kill-switch-blocks-everything guard's
           fan-protection cross-reference (the guard
           protects real fans from being toggled by agent
           actions).
        -> The leveling Wave 3 #60 connection cross-
           references the §8.1 kill-switch-blocks-
           everything guard's levelling-jack protection
           cross-reference (the guard prevents agent
           actions from moving levelling jacks while
           parking).
        -> The mode Wave 3 #61 connection cross-references
           the §8.3 audit-log entry's mode-change cross-
           reference (the guard surfaces agent-action
           transitions on the mode-change notification
           timeline).
        -> The demo-mode Wave 3 #62 connection cross-
           references the §8.5 outside-allowlist deny-by-
           default guard's safety-chip pattern (mirrors the
           demo-mode §8.2 never-controls-actual-hardware
           guard's safety-chip pattern).
        -> The advanced-mode Wave 3 #63 connection cross-
           references the §8.4 require-confirmation guard's
           confirm-flag pattern (mirrors the advanced-mode
           §8.1 confirm-before-toggle-on guard's confirm-
           flag pattern).
        -> The openclaw-api Wave 3 #64 connection cross-
           references the §8.3 audit-log entry's JSON
           payload cross-reference (the openclaw-api
           contract version surfaces agent-action events
           via the JSON API).

See docs/recipe.md for the full howto (HA core
`input_boolean` + `input_text` + `input_number` +
`input_select` + `input_datetime` + `input_button` +
`script` helper install + HA core `template:` sensor
wrapper install + HA core `logbook` integration install +
the FIVE-step operator-pickable agent-actions flow + the
11 `rc_agent_actions_*` contract tiles + the FIVE §8
MANDATORY automations + the 6 §9 troubleshooting entries +
privacy + tier-a promotion outline + the EXAMPLE policy
file format at `connections/agent-actions-allowlist/docs/
policy.example.yaml`).
"""

DOMAIN = "agent_actions"