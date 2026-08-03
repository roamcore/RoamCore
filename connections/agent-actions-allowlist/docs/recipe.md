# Agent actions allowlist — full howto (RoamCore vendor-neutral kill-switch + per-action allowlist + audit-log gateway for safe agent-driven RoamCore actions)

This recipe is the canonical howto for the
`connections/agent-actions-allowlist/` tier-b recipe
connection (Wave 3 #65). It walks the operator through
setting up the kill switch (already shipped in
`homeassistant/packages/roamcore_agent_actions.yaml`)
+ the policy file (operator-editable YAML; format
documented in
`connections/agent-actions-allowlist/docs/policy.example.yaml`)
+ the action types (set_helper + run_script; explicit
non-support list — `homeassistant.turn_on/off`, direct
`switch.*` / `climate.*` / `cover.*`, networking + users
+ add-ons) + the audit log (HA core `logbook`
integration + 3 `rc_agent_actions_last_*` template
sensors) + the 11 `rc_agent_actions_*` contract tiles +
the FIVE §8 MANDATORY automations + the operator-side
policy file format + the audit-log schema + the privacy
guarantees.

The recipe assumes the operator has at least the upstream
helpers installed (HA core `input_boolean` + `input_text` +
`input_number` + `input_select` + `input_datetime` +
`input_button` + `script` since 2022.x — auto-installed
in every HA install) + the existing kill switch
`input_boolean.rc_agent_actions_enabled` confirmed OFF
(already shipped in
`homeassistant/packages/roamcore_agent_actions.yaml` and
preserved verbatim by this slice). If the operator has
the upstream helpers + the existing kill switch + a
mounted policy file, the recipe starts at §4 The policy
file + walks through the action types + the audit log
before the §7 contract layer.

## §1 What is Agent actions allowlist in RoamCore?

Agent actions allowlist — vendor-neutral kill-switch +
per-action allowlist + audit-log gateway for safe agent-
driven RoamCore actions — the umbrella for "Agent
actions allowlist (safety gateway): A safety layer that
defaults to deny and only permits explicitly-allowed
agent actions, with a kill switch. Lets you use
automation/agents without fear of unexpected device
control; Clear boundary between read-only and can change
things" — is the ai-category complement to the broader
RoamCore "talk to your van" affordances. The single
`input_boolean.rc_agent_actions_enabled` kill switch is
the operator's master enable (OFF by default; this tile is
ALREADY shipped in `homeassistant/packages/roamcore_
agent_actions.yaml` and is preserved verbatim — the
package is not redefined by this slice); the
`input_text.rc_agent_actions_policy_path` is the operator-
configurable policy file path (default
`/config/.roamcore/agent_allowlist.yaml`); the
`input_boolean.rc_agent_actions_require_confirmation` is
the "every action needs an explicit confirmation" toggle
(default ON); the `select.rc_agent_actions_default_
duration` is the operator-pickable session-duration
picker (Off / 1h / 6h / 24h / 7d / Never; default 24h);
the `input_datetime.rc_agent_actions_session_expires_at`
is the session expiry timestamp (set to "now + selected
duration" when the kill switch flips ON); the
`sensor.rc_agent_actions_seconds_until_expiry` is the
resolved countdown to the session expiry; the
`sensor.rc_agent_actions_last_action_id` is the
`action_id` of the last agent action invocation (mirrors
the §8.3 audit-log entry); the
`sensor.rc_agent_actions_last_action_at` is the timestamp
of the last agent action invocation; the
`sensor.rc_agent_actions_last_action_result` is the
resolved result of the last agent action (`ok` / `error` /
`blocked` / `denied` / `pending-confirmation`); the
`binary_sensor.rc_agent_actions_is_blocked_by_kill_switch`
is the safety chip (TRUE when the kill switch is OFF or
the session has expired; should NEVER be FALSE
unexpectedly); the `button.rc_agent_actions_disable_now`
is the operator-triggered one-tap emergency off (also
turns the master kill switch OFF + clears the session
expiry timestamp).

The kill switch tile (`input_boolean.rc_agent_actions_
enabled`) is the operator's master switch — the recipe
defaults to OFF because agent actions are never permitted
unless the operator explicitly enables them (the §8.1
kill-switch-blocks-everything guard fires whenever a
`roamcore.action_execute` invocation arrives while the
kill switch is OFF, so forgetting to enable is mitigated
by default-deny).

The policy path tile (`input_text.rc_agent_actions_
policy_path`) is the operator's policy file location —
the recipe defaults to `/config/.roamcore/agent_allowlist.
yaml` because that's the canonical RoamCore-side policy
file location; the operator may override the path if they
prefer a different filesystem layout.

The require-confirmation tile (`input_boolean.rc_agent_
actions_require_confirmation`) is the operator's safety
mode toggle — the recipe defaults to ON because every
agent action that modifies state should require an
explicit confirmation step (the §8.4 require-confirmation
guard fires whenever a `roamcore.action_execute`
invocation arrives without a prior `roamcore.action_
confirm` call when this tile is ON; the second call
without confirmation short-circuits to
`pending-confirmation`).

The default-duration tile (`select.rc_agent_actions_
default_duration`) is the operator's session-duration
picker — the recipe defaults to 24h because that's the
canonical "session window" for an overnight trip; the
operator may pick 1h / 6h / 24h / 7d / Never depending on
their use case (Never means the kill switch stays ON
until the operator manually disables it via
`button.rc_agent_actions_disable_now`).

The session-expiry tile (`input_datetime.rc_agent_actions_
session_expires_at`) is the operator's session-expiry
timestamp — set to "now + selected duration" when the
kill switch flips ON; cleared when the kill switch
flips OFF or when the §8.2 session-timeout guard fires.

The seconds-until-expiry tile (`sensor.rc_agent_actions_
seconds_until_expiry`) is the resolved countdown timer —
surfaces as "expires in 23h 14m" in the dashboard;
factors in the kill switch state (always 0 when the kill
switch is OFF or when the session has expired).

The last-action-id tile (`sensor.rc_agent_actions_last_
action_id`) is the resolved `action_id` of the last
agent action invocation — surfaces as
"set_trip_wrapped_range" in the dashboard; mirrors the
§8.3 audit-log entry.

The last-action-at tile (`sensor.rc_agent_actions_last_
action_at`) is the resolved timestamp of the last agent
action invocation — surfaces as "last: 14m ago" in the
dashboard; mirrors the §8.3 audit-log entry.

The last-action-result tile (`sensor.rc_agent_actions_
last_action_result`) is the resolved result of the last
agent action invocation — surfaces as "ok" / "error" /
"blocked" / "denied" / "pending-confirmation" in the
dashboard; mirrors the §8.3 audit-log entry.

The is-blocked-by-kill-switch tile
(`binary_sensor.rc_agent_actions_is_blocked_by_kill_
switch`) is the §8 MANDATORY safety gate — should ALWAYS
be TRUE when the kill switch is OFF or the session has
expired; turns red if a misconfiguration would let an
agent action slip through while the kill switch is OFF
(this is the single most important safety affordance in
the agent-actions umbrella: forgetting to populate
`input_text.rc_agent_actions_policy_path` with a valid
policy file can leave the operator with a misconfigured
kill switch that surfaces a green "safe" chip while
agent actions are actually being denied by the §8.1
kill-switch-blocks-everything guard).

The disable-now tile (`button.rc_agent_actions_disable_
now`) is the operator's emergency off — clears the kill
switch + clears the session_expires_at timestamp +
surfaces an "agent actions disabled" toast.

The audit-log entry (the §8.3 audit-log-entry automation)
is the operator-facing "when did agent actions last
fire?" affordance — the §8.3 audit-log-entry automation
writes an entry to `sensor.rc_agent_actions_last_action_
id` + `sensor.rc_agent_actions_last_action_at` +
`sensor.rc_agent_actions_last_action_result` +
additionally tags the HA core `logbook` entry with the
`agent_actions` tag for sortability (the HA core `logbook`
integration is the canonical audit-log destination since
2022.x).

The recipe covers the FIVE-step operator flow (Confirm +
Mount + Decide + Enable + Audit + revert) + the FIVE
§8 MANDATORY automations + the 11 `rc_agent_actions_*`
contract tiles + the §9 troubleshooting entries + the
§10 privacy section + the §11 tier-a promotion outline +
the §12 files + the §13 cross-references.

## §2 Prerequisites

### §2.1 Universal prerequisites

The operator must have:

- A running Home Assistant installation (HA Core
  2022.6+; the helpers + `template:` + `logbook` + the
  `script:` integration are all upstream since 2022.x).
- The upstream HA core `input_boolean` + `input_text` +
  `input_number` + `input_select` + `input_datetime` +
  `input_button` + `script` helpers auto-installed
  (every HA install has these).
- The HA core `template:` integration auto-installed
  (every HA install has this).
- The HA core `logbook` integration auto-installed
  (every HA install has this).
- The HA core `script:` integration auto-installed
  (every HA install has this).
- The existing kill switch
  `input_boolean.rc_agent_actions_enabled` confirmed OFF
  (already shipped in
  `homeassistant/packages/roamcore_agent_actions.yaml`).
- Read access to the operator's policy file at
  `input_text.rc_agent_actions_policy_path` (default
  `/config/.roamcore/agent_allowlist.yaml`).

### §2.2 Upstream signal prerequisites

The operator must wire:

- `input_boolean.rc_agent_actions_enabled` (the existing
  kill switch — already shipped in
  `homeassistant/packages/roamcore_agent_actions.yaml`).
- `input_text.rc_agent_actions_policy_path` (the operator-
  configurable policy file path; default
  `/config/.roamcore/agent_allowlist.yaml`).
- `input_boolean.rc_agent_actions_require_confirmation`
  (default ON for the recommended safety mode).
- `select.rc_agent_actions_default_duration` (Off / 1h /
  6h / 24h / 7d / Never; default 24h).
- `input_datetime.rc_agent_actions_session_expires_at`
  (the session expiry timestamp).
- `sensor.rc_agent_actions_seconds_until_expiry` (the
  resolved countdown to expiry).
- `sensor.rc_agent_actions_last_action_id` (the last
  action_id).
- `sensor.rc_agent_actions_last_action_at` (the last
  action timestamp).
- `sensor.rc_agent_actions_last_action_result` (the
  last action result).
- `binary_sensor.rc_agent_actions_is_blocked_by_kill_
  switch` (the safety chip).
- `button.rc_agent_actions_disable_now` (the operator-
  triggered one-tap emergency off).

### §2.3 Optional cross-references (recommended)

The operator may also wire:

- The time-atomic Wave 3 #55 connection's time-of-day
  primitives for the §8.2 session-timeout guard's
  expiry timestamp.
- The remote-access Wave 3 #58 connection's VPN
  primitive for the §8.4 require-confirmation guard's
  owner-identity check.
- The approach lights Wave 3 #52 connection's dashboard
  banner pattern for the §8.3 audit-log entry.
- The fans Wave 3 #59 connection's fan-protection cross-
  reference for the §8.1 kill-switch-blocks-everything
  guard's fan protection.
- The leveling Wave 3 #60 connection's levelling-jack
  protection cross-reference for the §8.1 kill-switch-
  blocks-everything guard's levelling-jack protection.
- The mode Wave 3 #61 connection's mode-change cross-
  reference for the §8.3 audit-log entry.
- The demo-mode Wave 3 #62 connection's safety-chip
  pattern for the §8.5 outside-allowlist deny-by-
  default guard.
- The advanced-mode Wave 3 #63 connection's confirm-flag
  pattern for the §8.4 require-confirmation guard.
- The openclaw-api Wave 3 #64 connection's JSON payload
  cross-reference for the §8.3 audit-log entry.

## §3 The kill switch (already shipped)

The single `input_boolean.rc_agent_actions_enabled` kill
switch is the operator's master enable (OFF by default).
This tile is ALREADY shipped in
`homeassistant/packages/roamcore_agent_actions.yaml` and
is preserved verbatim by this slice — the operator must
NOT redefine the package.

### §3.1 Confirm the kill switch defaults

The §3 flow walks the operator through confirming the
kill switch defaults are correct:

1. Navigate to Home Assistant → Settings → Devices &
   services → Helpers.
2. Confirm `input_boolean.rc_agent_actions_enabled`
   exists with `initial: false`.
3. Confirm the tile surfaces a shield-lock icon in the
   dashboard (the canonical `mdi:shield-lock` icon for
   the kill switch).
4. Confirm the tile reads "RoamCore Agent Actions
   Enabled" + shows the OFF state.

### §3.2 What the kill switch does

The kill switch is the §8.1 kill-switch-blocks-everything
guard's master enable. When the kill switch is OFF:

- ANY `script.*` / `automation.*` action that tries to
  invoke `roamcore.action_execute` short-circuits to the
  `denied` result.
- `binary_sensor.rc_agent_actions_is_blocked_by_kill_
  switch` reads TRUE.
- `sensor.rc_agent_actions_seconds_until_expiry` reads 0.
- `input_datetime.rc_agent_actions_session_expires_at`
  is cleared.
- The §8.2 session-timeout guard does NOT fire (no
  session expiry timestamp to monitor).

### §3.3 Wiring the kill switch

The kill switch is wired by
`homeassistant/packages/roamcore_agent_actions.yaml`:

```yaml
input_boolean:
  rc_agent_actions_enabled:
    name: "RoamCore Agent Actions Enabled"
    icon: mdi:shield-lock
    initial: false
```

The operator must NOT add additional tiles to this
package — the slice preserves the package verbatim and
only references the existing kill switch tile.

## §4 The policy file (operator-editable YAML)

The policy file is the operator-side allowlist that
governs which `action_id` entries the agent is permitted
to invoke. The policy file is mounted at
`input_text.rc_agent_actions_policy_path` (default
`/config/.roamcore/agent_allowlist.yaml`).

### §4.1 Copy the EXAMPLE policy file

The operator copies
`connections/agent-actions-allowlist/docs/policy.example.yaml`
to the path declared in
`input_text.rc_agent_actions_policy_path` (default
`/config/.roamcore/agent_allowlist.yaml`).

### §4.2 Policy file format

The policy file is a YAML document with a `version: 1`
header + a `defaults:` block (e.g.
`require_confirmation: true`) + an `actions:` list with
per-action entries. Each entry has:

- `id` — the `action_id` the agent must reference when
  invoking `roamcore.action_execute` (must be unique
  across the `actions:` list).
- `description` — a human-readable description of the
  action (for the operator's review at setup time +
  for the audit-log entry).
- `kind` — either `set_helper` (the agent sets the
  value of an `input_text` / `input_number` /
  `input_select` / `input_boolean` helper entity) or
  `run_script` (the agent invokes a `script.rc_*` prefix
  script).
- `target` — the entity being targeted (single entity_id
  for `run_script`; one or more entity_ids for
  `set_helper`).
- `constraints` — optional per-action constraints:
  - For `set_helper` on `input_text`: a regex `pattern`.
  - For `set_helper` on `input_number`: `min` + `max`
    + optional `unit_of_measurement`.
  - For `set_helper` on `input_select`: an `enum`
    allowlist of the allowed option values.
  - For `set_helper` on `input_boolean`: a `value`
    (`true` or `false`).
- `require_confirmation` — optional per-action
  override for the `defaults.require_confirmation`
  value (e.g. an idempotent `run_script` may set
  `require_confirmation: false`).

### §4.3 Edit the policy file

The operator edits the policy file for their setup. The
EXAMPLE file ships with three example actions:

1. `set_trip_wrapped_range` — `set_helper` on
   `input_text.rc_trip_wrapped_from` +
   `input_text.rc_trip_wrapped_to` with an ISO8601 Zulu
   regex pattern constraint. This is the canonical
   "agent sets a date range" affordance.
2. `generate_trip_wrapped` — `run_script` on
   `script.rc_trip_wrapped_run` with
   `require_confirmation: false`. This is the canonical
   "agent triggers an idempotent script" affordance.
3. `set_target_soc_percent` — `set_helper` on
   `input_number.rc_target_soc_percent` with min=20 +
   max=90 + unit_of_measurement="%". This is the
   canonical "agent sets a numeric setting with safe
   bounds" affordance.

### §4.4 Wire the policy path

The operator configures
`input_text.rc_agent_actions_policy_path` to point at the
policy file:

```yaml
input_text:
  rc_agent_actions_policy_path:
    name: RC Agent Actions Policy Path
    initial: "/config/.roamcore/agent_allowlist.yaml"
    icon: mdi:file-document-outline
```

The operator may override the path if they prefer a
different filesystem layout (e.g. `/config/agent_allowlist.yaml`
or `/share/roamcore/agent_allowlist.yaml`).

## §5 The action types (set_helper + run_script)

The v1 action type set is intentionally conservative. We
support TWO action kinds: `set_helper` + `run_script`.
We explicitly do NOT support direct device control,
networking, or user/add-on modification.

### §5.1 Supported: `set_helper`

The `set_helper` action kind allows the agent to set
the value of an `input_text` / `input_number` /
`input_select` / `input_boolean` helper entity. The
agent must specify the target `entity_id` (one or more)
+ the value (which must satisfy the per-action
`constraints` block).

Example: set `input_text.rc_trip_wrapped_from` to a
valid ISO8601 Zulu timestamp.

```yaml
actions:
  - id: set_trip_wrapped_range
    description: "Set Trip Wrapped from/to ISO timestamps"
    kind: set_helper
    target:
      entity_id:
        - input_text.rc_trip_wrapped_from
        - input_text.rc_trip_wrapped_to
    constraints:
      pattern: "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.?\\d*Z$"
```

### §5.2 Supported: `run_script`

The `run_script` action kind allows the agent to invoke
a `script.rc_*` prefix script. The agent must specify the
target `entity_id` (single script entity). The script
itself is the canonical Trip Wrapped runner or any other
operator-side automation.

Example: invoke `script.rc_trip_wrapped_run`.

```yaml
actions:
  - id: generate_trip_wrapped
    description: "Generate Trip Wrapped latest report"
    kind: run_script
    target:
      entity_id: script.rc_trip_wrapped_run
    require_confirmation: false
```

### §5.3 Explicitly NOT supported (v1)

The following service families are EXPLICITLY NOT
supported at v1:

- `homeassistant.turn_on` / `homeassistant.turn_off` —
  the global HA core service that toggles any entity.
  Use `set_helper` (for `input_*` helpers) or `run_script`
  (for `script.rc_*` scripts) instead.
- Direct `switch.*` services — `switch.turn_on`,
  `switch.turn_off`, `switch.toggle`. Use `run_script` +
  a `script.rc_*` wrapper script that the operator has
  explicitly wired.
- Direct `climate.*` services — `climate.set_temperature`,
  `climate.set_hvac_mode`, `climate.turn_on`,
  `climate.turn_off`. Use `run_script` + a `script.rc_*`
  wrapper script that the operator has explicitly wired.
- Direct `cover.*` services — `cover.open_cover`,
  `cover.close_cover`, `cover.stop_cover`, `cover.toggle`.
  Use `run_script` + a `script.rc_*` wrapper script that
  the operator has explicitly wired.
- Networking services — anything that modifies network
  configuration (firewall rules, DNS, VPN, Wi-Fi).
  Use `run_script` + a `script.rc_*` wrapper script that
  the operator has explicitly wired.
- User / add-on services — `auth.create_user`,
  `auth.delete_user`, `auth.update_user`,
  `hassio.addon_install`, `hassio.addon_uninstall`,
  `hassio.addon_start`, `hassio.addon_stop`. NOT supported
  at v1; the agent cannot create / modify / delete users
  or add-ons.

### §5.4 Why this is conservative

The v1 action set is intentionally conservative because:

1. Default-deny is the foundational safety philosophy
   (`docs/design/agent-actions-allowlist.md` §Principles).
2. The first rollout should focus on safe primitives
   (`set_helper` on `input_*` helpers + `run_script` on
   `script.rc_*` scripts).
3. Avoiding direct device power switching early
   prevents the "agent turns on the heater while
   unattended" scenario.
4. Networking + user + add-on services are too dangerous
   to expose at v1 — they have no "safe subset" that
   can be allowlisted.

Future versions (v2 + v3) may add limited device control
via safe wrappers + per-action rate limits + better
confirmation flows. The recipe + the policy file format
+ the §8 automations are designed to evolve gracefully
when those features land.

## §6 The audit log (HA core `logbook` integration)

The audit log is the operator-facing "when did agent
actions last fire?" affordance. The audit log is stored
in the HA core `logbook` integration (since 2022.x — the
canonical audit-log destination for Home Assistant
automations) + 3 `rc_agent_actions_last_*` template
sensors (the last-action-id + last-action-at +
last-action-result tiles).

### §6.1 HA core `logbook` integration

The HA core `logbook` integration is the canonical
audit-log destination for Home Assistant automations.
The §8.3 audit-log-entry automation writes entries to
the logbook whenever an agent action fires.

The operator wires the §8.3 automation's `logbook.log`
service call to tag the entry with the `agent_actions`
domain + the `agent_actions` name + the agent's
`action_id` + the result + the timestamp.

### §6.2 Last-action-id tile

The `sensor.rc_agent_actions_last_action_id` tile is
the resolved `action_id` of the last agent action
invocation (mirrors the §8.3 audit-log entry). The tile
is a `template:` sensor (since 2022.x) that reads from
the most recent logbook entry's `action_id` attribute.

### §6.3 Last-action-at tile

The `sensor.rc_agent_actions_last_action_at` tile is
the resolved timestamp of the last agent action
invocation (mirrors the §8.3 audit-log entry). The tile
is a `template:` sensor (since 2022.x) that reads from
the most recent logbook entry's `when` attribute.

### §6.4 Last-action-result tile

The `sensor.rc_agent_actions_last_action_result` tile
is the resolved result of the last agent action
invocation (mirrors the §8.3 audit-log entry). The
tile is a `template:` sensor (since 2022.x) that reads
from the most recent logbook entry's `result` attribute.
The result is one of `ok` / `error` / `blocked` /
`denied` / `pending-confirmation`.

### §6.5 Audit-log schema

The audit-log schema is intentionally simple + flat:

```yaml
- when: "2026-08-03T07:34:00Z"  # ISO 8601 Zulu timestamp
  action_id: "set_trip_wrapped_range"  # the agent's proposed action_id
  result: "ok"  # ok | error | blocked | denied | pending-confirmation
  agent_identity: "openclaw-roamcore-skill-v1"  # best-effort agent identity
  reason: ""  # optional; populated for blocked / denied / pending-confirmation
```

The schema is documented in
`docs/design/agent-actions-allowlist.md` §Execution flow
+ §Audit log. The operator owns the audit log; RoamCore
does NOT maintain any agent-action telemetry.

## §7 RoamCore contract entities

The 11 `rc_agent_actions_*` contract tiles are the
canonical RoamCore surface for the agent-actions
umbrella. The tiles are vendor-neutral — no Victron /
SeeLevel / Garnet / Mopeka / Renogy / Starlink / Peplink
/ Teltonika / Unifi / Ubiquiti / OpenAI / Anthropic /
Claude / GPT / ChatGPT / LLM / conversation / MQTT /
webhook / REST / API / HTTP / HTTPS / Companion / ESPHome
/ phone / GPS / accelerometer / iPhone / iOS / Android /
Samsung / Pixel / OnePlus / Xiaomi / Huawei / input_boolean
/ input_text / input_number / input_select / input_datetime
/ input_button / script / template / logbook / Z-Wave /
Zigbee / ZHA / Deconz / Tasmota / Shelly / Sonoff /
ESP32 / ESP8266 / Wi-Fi / BLE / Bluetooth names leak into
the tile ids.

### §7.1 The 11 `rc_agent_actions_*` contract tiles

- `input_boolean.rc_agent_actions_enabled` — master kill
  switch (OFF by default; already shipped in
  `homeassistant/packages/roamcore_agent_actions.yaml`).
  The tile is an `input_boolean:` domain entity (since
  2022.x) that the operator's chosen kill-switch UI
  flips.
  ```yaml
  input_boolean:
    rc_agent_actions_enabled:
      name: "RoamCore Agent Actions Enabled"
      icon: mdi:shield-lock
      initial: false
  ```

- `input_text.rc_agent_actions_policy_path` — operator-
  configurable policy file path (default
  `/config/.roamcore/agent_allowlist.yaml`). The tile is
  an `input_text:` domain entity (since 2022.x) that the
  operator's chosen policy-path UI sets.
  ```yaml
  input_text:
    rc_agent_actions_policy_path:
      name: RC Agent Actions Policy Path
      initial: "/config/.roamcore/agent_allowlist.yaml"
      icon: mdi:file-document-outline
  ```

- `input_boolean.rc_agent_actions_require_confirmation`
  — whether new actions require explicit confirmation
  (default ON). The tile is an `input_boolean:` domain
  entity (since 2022.x) that the operator's chosen
  require-confirmation UI flips.
  ```yaml
  input_boolean:
    rc_agent_actions_require_confirmation:
      name: RC Agent Actions Require Confirmation
      icon: mdi:comment-question-outline
      initial: true
  ```

- `select.rc_agent_actions_default_duration` — Off / 1h
  / 6h / 24h / 7d / Never (default 24h). The tile is a
  `select:` domain entity (since 2022.x — `input_select`
  is the umbrella; since 2024.x the modern `select:`
  domain entity is exposed via the HA UI under Settings
  → Helpers) that the operator's chosen duration UI
  picks.
  ```yaml
  select:
    rc_agent_actions_default_duration:
      name: RC Agent Actions Default Duration
      options:
        - "Off"
        - "1h"
        - "6h"
        - "24h"
        - "7d"
        - "Never"
      initial: "24h"
      icon: mdi:timer-outline
  ```

- `input_datetime.rc_agent_actions_session_expires_at`
  — session expiry timestamp ("now + selected duration").
  The tile is an `input_datetime:` domain entity (since
  2022.x) that the §8.2 session-timeout guard writes to.
  ```yaml
  input_datetime:
    rc_agent_actions_session_expires_at:
      name: RC Agent Actions Session Expires At
      has_date: true
      has_time: true
      icon: mdi:timer-sand
  ```

- `sensor.rc_agent_actions_seconds_until_expiry` —
  resolved countdown to session expiry (factors in the
  kill switch state + the expiry timestamp). The tile is
  a `template:` sensor (since 2022.x).
  ```yaml
  template:
    - sensor:
        - name: "RC Agent Actions Seconds Until Expiry"
          unique_id: rc_agent_actions_seconds_until_expiry
          icon: mdi:timer-sand
          state: >
            {% set expires_at = states('input_datetime.rc_agent_actions_session_expires_at') %}
            {% if is_state('input_boolean.rc_agent_actions_enabled', 'on')
                  and expires_at not in ['unknown', 'unavailable', 'none', ''] %}
              {{ max(0, ((as_timestamp(expires_at) - now()) | int)) }}
            {% else %}
              0
            {% endif %}
          unit_of_measurement: "s"
  ```

- `sensor.rc_agent_actions_last_action_id` — last agent
  action `action_id` (mirrors the §8.3 audit-log entry).
  The tile is a `template:` sensor (since 2022.x).
  ```yaml
  template:
    - sensor:
        - name: "RC Agent Actions Last Action ID"
          unique_id: rc_agent_actions_last_action_id
          icon: mdi:tag-outline
          state: >
            {{ state_attr('sensor.rc_agent_actions_last_action_logbook_entry', 'action_id')
                | default('none') }}
  ```

- `sensor.rc_agent_actions_last_action_at` — last agent
  action timestamp (mirrors the §8.3 audit-log entry).
  The tile is a `template:` sensor (since 2022.x).
  ```yaml
  template:
    - sensor:
        - name: "RC Agent Actions Last Action At"
          unique_id: rc_agent_actions_last_action_at
          icon: mdi:clock-outline
          state: >
            {{ state_attr('sensor.rc_agent_actions_last_action_logbook_entry', 'when')
                | default('none') }}
  ```

- `sensor.rc_agent_actions_last_action_result` — last
  agent action result (`ok` / `error` / `blocked` /
  `denied` / `pending-confirmation`). The tile is a
  `template:` sensor (since 2022.x).
  ```yaml
  template:
    - sensor:
        - name: "RC Agent Actions Last Action Result"
          unique_id: rc_agent_actions_last_action_result
          icon: mdi:check-circle-outline
          state: >
            {{ state_attr('sensor.rc_agent_actions_last_action_logbook_entry', 'result')
                | default('none') }}
  ```

- `binary_sensor.rc_agent_actions_is_blocked_by_kill_
  switch` — TRUE when the kill switch is OFF or the
  session has expired. The tile is a `template:`
  binary_sensor (since 2022.x) that the §8.1 kill-switch-
  blocks-everything guard writes to.
  ```yaml
  template:
    - binary_sensor:
        - name: "RC Agent Actions Is Blocked By Kill Switch"
          unique_id: rc_agent_actions_is_blocked_by_kill_switch
          device_class: safety
          icon: mdi:shield-off-outline
          state: >
            {% if is_state('input_boolean.rc_agent_actions_enabled', 'on')
                  and states('input_datetime.rc_agent_actions_session_expires_at')
                  not in ['unknown', 'unavailable', 'none', ''] %}
              {{ false }}
            {% else %}
              {{ true }}
            {% endif %}
  ```

- `button.rc_agent_actions_disable_now` — operator-
  triggered one-tap emergency off (also turns the master
  kill switch OFF + clears the session expiry timestamp).
  The button is an `input_button:` domain entity (since
  2022.x) that fires an automation flipping
  `input_boolean.rc_agent_actions_enabled` OFF +
  clearing `input_datetime.rc_agent_actions_session_
  expires_at`.
  ```yaml
  input_button:
    rc_agent_actions_disable_now:
      name: RC Agent Actions Disable Now
      icon: mdi:shield-off-outline
  ```

### §7.2 Script-runner wrappers

The `roamcore.action_confirm` + `roamcore.action_execute`
wrappers are upstream `script:` integration script-runner
wrappers that the operator wires in
`homeassistant/scripts.yaml` (or in a dedicated
RoamCore-side `homeassistant/packages/roamcore_agent_actions_scripts.yaml`
file).

```yaml
script:
  roamcore_action_confirm:
    alias: "RoamCore: Action Confirm"
    description: >-
      Confirm an agent action invocation. Must be called
      BEFORE roamcore.action_execute when
      input_boolean.rc_agent_actions_require_confirmation
      is ON.
    sequence:
      - service: logbook.log
        data:
          name: "RoamCore Agent Actions"
          message: >-
            Agent confirmed action
            {{ action_id | default('unknown') }}.
          entity_id: input_boolean.rc_agent_actions_enabled
  roamcore_action_execute:
    alias: "RoamCore: Action Execute"
    description: >-
      Execute an agent action. Requires a prior
      roamcore.action_confirm call when
      input_boolean.rc_agent_actions_require_confirmation
      is ON.
    sequence:
      - choose:
          - conditions:
              - condition: state
                entity_id: input_boolean.rc_agent_actions_enabled
                state: "off"
            sequence:
              - service: logbook.log
                data:
                  name: "RoamCore Agent Actions"
                  message: >-
                    Agent action {{ action_id | default('unknown') }}
                    DENIED: kill switch is OFF.
                  entity_id: input_boolean.rc_agent_actions_enabled
              - stop: "Kill switch is OFF"
```

## §8 Automations (MANDATORY before first use)

### §8.1 Kill-switch blocks everything

The automation fires when ANY `script.*` / `automation.*`
action tries to invoke the `roamcore.action_execute`
service while `input_boolean.rc_agent_actions_enabled` is
OFF. The automation BLOCKS the invocation + short-circuits
to the `denied` result + flips
`binary_sensor.rc_agent_actions_is_blocked_by_kill_switch`
to TRUE + writes an audit-log entry + fires a critical
notification warning the operator that the kill switch
is OFF.

```yaml
automation:
  - alias: "RoamCore: Agent actions — kill-switch blocks everything"
    description: >-
      Fires when any script.* / automation.* action tries to
      invoke roamcore.action_execute while the kill switch is
      OFF. Blocks the invocation + writes an audit-log entry.
    trigger:
      - platform: event
        event_type: roamcore_action_execute_attempted
    condition:
      - condition: state
        entity_id: input_boolean.rc_agent_actions_enabled
        state: "off"
    action:
      - service: logbook.log
        data:
          name: "RoamCore Agent Actions"
          message: >-
            Agent action {{ trigger.event.data.action_id }}
            DENIED: kill switch is OFF.
          entity_id: input_boolean.rc_agent_actions_enabled
      - event: roamcore_action_execute_blocked
        event_data:
          action_id: "{{ trigger.event.data.action_id }}"
          result: denied
          reason: kill_switch_off
```

### §8.2 Session-timeout guard

The automation fires when
`sensor.rc_agent_actions_seconds_until_expiry` reaches 0
(i.e. the `input_datetime.rc_agent_actions_session_
expires_at` timestamp is reached). The automation clears
the kill switch + clears the session_expires_at +
writes a `session_expired` audit-log entry + fires a
notification warning the operator that agent actions have
been auto-disabled.

```yaml
automation:
  - alias: "RoamCore: Agent actions — session-timeout guard"
    description: >-
      Fires when the session-expiry timestamp is reached.
      Clears the kill switch + clears the expiry timestamp.
    trigger:
      - platform: state
        entity_id: input_datetime.rc_agent_actions_session_expires_at
        to: "0"
    condition:
      - condition: state
        entity_id: input_boolean.rc_agent_actions_enabled
        state: "on"
    action:
      - service: input_boolean.turn_off
        target:
          entity_id: input_boolean.rc_agent_actions_enabled
      - service: input_datetime.set_datetime
        target:
          entity_id: input_datetime.rc_agent_actions_session_expires_at
        data:
          datetime: "{{ now().strftime('%Y-%m-%dT%H:%M:%S') }}"
      - service: logbook.log
        data:
          name: "RoamCore Agent Actions"
          message: >-
            Agent actions auto-disabled: session expired.
          entity_id: input_boolean.rc_agent_actions_enabled
      - service: persistent_notification.create
        data:
          title: "RoamCore Agent Actions: session expired"
          message: >-
            Agent actions have been auto-disabled because
            the session expired. Flip the kill switch ON
            again to re-enable.
```

### §8.3 Audit-log entry

The automation fires on every agent action invocation.
The automation writes an entry to
`sensor.rc_agent_actions_last_action_id` +
`sensor.rc_agent_actions_last_action_at` +
`sensor.rc_agent_actions_last_action_result` +
additionally tags the HA core `logbook` entry with the
`agent_actions` tag for sortability.

```yaml
automation:
  - alias: "RoamCore: Agent actions — audit-log entry"
    description: >-
      Fires on every agent action invocation. Writes an
      entry to the last-action-* tiles + tags the HA
      core logbook entry.
    trigger:
      - platform: event
        event_type: roamcore_action_executed
      - platform: event
        event_type: roamcore_action_execute_blocked
      - platform: event
        event_type: roamcore_action_execute_denied
    action:
      - service: logbook.log
        data:
          name: "RoamCore Agent Actions"
          message: >-
            Agent action {{ trigger.event.data.action_id }}
            result: {{ trigger.event.data.result }}.
          entity_id: input_boolean.rc_agent_actions_enabled
          domain: agent_actions
```

### §8.4 Require-confirmation guard

The automation fires when
`input_boolean.rc_agent_actions_require_confirmation` is
ON AND `roamcore.action_execute` is invoked WITHOUT a
prior `roamcore.action_confirm` call from the same agent
identity. The automation BLOCKS the invocation +
short-circuits to `pending-confirmation` + writes an
audit-log entry + fires a notification warning the
operator that the agent must confirm the action first.

```yaml
automation:
  - alias: "RoamCore: Agent actions — require-confirmation guard"
    description: >-
      Fires when roamcore.action_execute is invoked WITHOUT
      a prior roamcore.action_confirm call while the
      require-confirmation toggle is ON. Blocks the
      invocation + short-circuits to pending-confirmation.
    trigger:
      - platform: event
        event_type: roamcore_action_execute_attempted
    condition:
      - condition: state
        entity_id: input_boolean.rc_agent_actions_require_confirmation
        state: "on"
      - condition: template
        value_template: >-
          {{ not trigger.event.data.confirmed }}
    action:
      - service: logbook.log
        data:
          name: "RoamCore Agent Actions"
          message: >-
            Agent action {{ trigger.event.data.action_id }}
            PENDING: requires confirmation.
          entity_id: input_boolean.rc_agent_actions_enabled
      - event: roamcore_action_execute_blocked
        event_data:
          action_id: "{{ trigger.event.data.action_id }}"
          result: pending-confirmation
          reason: requires_confirmation
```

### §8.5 Outside-allowlist deny-by-default

The automation fires when ANY `script.*` / `automation.*`
action tries to invoke `roamcore.action_execute` with an
`action_id` that is NOT in the operator's policy file at
`input_text.rc_agent_actions_policy_path`. The automation
BLOCKS the invocation + short-circuits to `denied` +
writes a `denied` audit-log entry + fires a critical
notification warning the operator that the agent
attempted an action outside the allowlist.

```yaml
automation:
  - alias: "RoamCore: Agent actions — outside-allowlist deny-by-default"
    description: >-
      Fires when roamcore.action_execute is invoked with an
      action_id that is NOT in the operator's policy file.
      Blocks the invocation + short-circuits to denied.
    trigger:
      - platform: event
        event_type: roamcore_action_execute_attempted
    condition:
      - condition: template
        value_template: >-
          {{ not (trigger.event.data.action_id in policy_action_ids) }}
    action:
      - service: logbook.log
        data:
          name: "RoamCore Agent Actions"
          message: >-
            Agent action {{ trigger.event.data.action_id }}
            DENIED: outside allowlist.
          entity_id: input_boolean.rc_agent_actions_enabled
      - event: roamcore_action_execute_blocked
        event_data:
          action_id: "{{ trigger.event.data.action_id }}"
          result: denied
          reason: outside_allowlist
```

## §9 Troubleshooting

### §9.1 Kill-switch not blocking

Symptom: agent actions still succeed even when
`input_boolean.rc_agent_actions_enabled` is OFF.

Cause: the §8.1 kill-switch-blocks-everything guard is
not wired; OR the `roamcore.action_execute` wrapper is
not using the upstream `script:` integration; OR the
kill switch tile is not surfaced correctly.

Fix: confirm the §8.1 automation is wired + the kill
switch tile reads OFF in the dashboard + the
`roamcore.action_execute` wrapper checks the kill switch
state at the top of the script's `choose:` chain.

### §9.2 Session not expiring

Symptom: agent actions stay ON past the
`select.rc_agent_actions_default_duration` selection.

Cause: the §8.2 session-timeout guard is not wired; OR
the `input_datetime.rc_agent_actions_session_expires_at`
tile is not populated; OR the
`sensor.rc_agent_actions_seconds_until_expiry` template
sensor has a stale state.

Fix: confirm the §8.2 automation is wired + the session
expiry timestamp is populated when the kill switch flips
ON + the countdown sensor reads a positive value before
expiry.

### §9.3 Audit-log entries missing

Symptom: the
`sensor.rc_agent_actions_last_action_id` +
`sensor.rc_agent_actions_last_action_at` +
`sensor.rc_agent_actions_last_action_result` tiles do not
update when an agent action fires.

Cause: the §8.3 audit-log entry guard is not wired; OR
the HA core `logbook` integration is not enabled; OR the
template sensors are not reading from the logbook entry
attributes.

Fix: confirm the §8.3 automation is wired + the HA core
`logbook` integration is enabled (Settings → Devices &
services → Integrations → Logbook) + the template
sensors reference the correct `logbook_entry` attribute
names.

### §9.4 Require-confirmation bypass

Symptom: agent actions succeed without a prior
`roamcore.action_confirm` call even when
`input_boolean.rc_agent_actions_require_confirmation` is
ON.

Cause: the §8.4 require-confirmation guard is not wired;
OR the `roamcore.action_execute` wrapper is not firing
the `roamcore_action_execute_attempted` event with the
correct `confirmed` flag.

Fix: confirm the §8.4 automation is wired + the
`roamcore.action_execute` wrapper fires
`roamcore_action_execute_attempted` with `confirmed:
true` after a prior `roamcore.action_confirm` call from
the same agent identity.

### §9.5 Policy file parse errors

Symptom: the `input_text.rc_agent_actions_policy_path`
tile references a policy file that fails to parse (e.g.
invalid YAML syntax).

Cause: the policy file has invalid YAML syntax; OR the
`version: 1` header is missing; OR the `actions:` list
is malformed.

Fix: validate the policy file's YAML syntax via
`python3 -c "import yaml; yaml.safe_load(open('/config/.roamcore/agent_allowlist.yaml'))"`
+ confirm the `version: 1` header is present + confirm
the `actions:` list is a valid YAML list of objects with
the required fields (`id` + `description` + `kind` +
`target`).

### §9.6 Action_id collision

Symptom: two actions in the `actions:` list have the same
`id` field.

Cause: the operator copy-pasted an entry without
updating the `id`.

Fix: ensure every entry in the `actions:` list has a
unique `id` field. The §8.5 outside-allowlist deny-by-
default guard will short-circuit any ambiguous `id`
matches to `denied` + write a `denied` audit-log entry.

## §10 Privacy

Agent actions allowlist is HA local-only by design:

- The kill switch + the policy file + the audit log +
  the require-confirmation toggle + the session-expiry
  timestamp + the last-action-id + last-action-at +
  last-action-result + the is-blocked-by-kill-switch +
  the disable-now button are ALL stored locally on the
  operator's HA box (no cloud round-trip).
- The policy file is owned by the operator (the
  recipe does NOT include any vendor-specific defaults;
  the operator copies the EXAMPLE policy file +
  customises it for their setup).
- The audit log is stored in the HA core `logbook` +
  the `sensor.rc_agent_actions_last_action_*` template
  sensors (no third-party audit-log destination; no
  cloud round-trip).
- The §8.1 + §8.2 + §8.3 + §8.4 + §8.5 automations are
  wired locally on the operator's HA box (no cloud
  round-trip).
- The `roamcore.action_execute` + `roamcore.action_
  confirm` wrappers are upstream `script:` integration
  script-runner wrappers that the operator wires locally
  on their HA box (no cloud round-trip).

RoamCore does NOT maintain any agent-action telemetry;
the policy file + the audit log + the kill switch are
100% operator-owned. If the operator wants to share the
policy file + the audit log + the kill switch state
across multiple HA instances, they can use the HA core
`input_*` helper entity replication (or the upstream
`sync` integration) — but the recipe does NOT require
any cross-instance sharing.

## §11 Promoting to tier-a

Tier-a would require a RoamCore-owned agent-actions
engine + integration code + integration tests against a
real agent-actions engine bench. The bench would need
the following canned fixture responses wired together
in a controlled environment:

1. Canned `roamcore_action_execute_attempted` event with
   `action_id: "set_trip_wrapped_range"` + `confirmed:
   true` — the §8.1 kill-switch-blocks-everything guard
   should fire (kill switch is OFF in the fixture).
2. Canned `roamcore_action_execute_attempted` event with
   `action_id: "set_trip_wrapped_range"` + `confirmed:
   true` — the §8.4 require-confirmation guard should
   NOT fire (require-confirmation toggle is OFF in the
   fixture).
3. Canned `roamcore_action_execute_attempted` event with
   `action_id: "set_unknown_action"` + `confirmed: true`
   — the §8.5 outside-allowlist deny-by-default guard
   should fire (action_id is NOT in the policy file).
4. Canned `roamcore_action_execute_attempted` event with
   `action_id: "set_trip_wrapped_range"` + `confirmed:
   false` — the §8.4 require-confirmation guard should
   fire (require-confirmation toggle is ON in the
   fixture).
5. Canned `input_datetime.rc_agent_actions_session_
   expires_at` state transition to "0" — the §8.2
   session-timeout guard should fire.
6. Canned policy file with two `actions:` entries having
   the same `id` field — the §8.5 outside-allowlist
   deny-by-default guard should fire (the audit
   scenario for the §9.6 action_id collision case).
7. Canned `roamcore.action_confirm` call + subsequent
   `roamcore.action_execute` call — the §8.4 require-
   confirmation guard should NOT fire (the audit
   scenario for the happy-path confirmation flow).
8. Canned `roamcore.action_execute` call with kill
   switch ON + require-confirmation OFF + action_id in
   allowlist — the §8.1 + §8.4 + §8.5 guards should NOT
   fire (the happy-path success scenario).

The bench would also need a RoamCore-owned operator-
wired setup flow walking the operator through Confirm
+ Mount the policy file + Decide the default duration +
Enable with optional confirmation + Audit + the §8
automations.

## §12 Files

- `connection.yml` — the source-of-truth tier-b
  manifest.
- `__init__.py` — `DOMAIN = "agent_actions"` marker for
  the audit.
- `README.md` — the folder overview + the 11-tile table
  + the 5-§8-automation summary + the supersession
  pointer + the cross-references.
- `docs/recipe.md` — this file.
- `docs/policy.example.yaml` — the EXAMPLE policy file
  format (operator copies to
  `input_text.rc_agent_actions_policy_path` and edits
  for their setup).
- `tests/test_connection_yml.py` — the 7 manifest-
  honesty checks.

External references:

- Legacy catalog page (now superseded by this slice):
  [the legacy spec](../../../catalog/ai/agent-actions-allowlist.md)
- Design doc (philosophy + threat model + policy file
  format + execution flow + UI/UX proposal):
  [`docs/design/agent-actions-allowlist.md`](../../../design/agent-actions-allowlist.md)
  (171 lines — the canonical source of truth for the
  safety philosophy)
- Existing kill-switch helper package (preserved
  verbatim):
  [`homeassistant/packages/roamcore_agent_actions.yaml`](../../../homeassistant/packages/roamcore_agent_actions.yaml)
  (declares the
  `input_boolean.rc_agent_actions_enabled` helper)

## §13 Cross-references

External HA core integrations:

- HA core `input_boolean` integration: https://www.home-assistant.io/integrations/input_boolean/
- HA core `input_text` integration: https://www.home-assistant.io/integrations/input_text/
- HA core `input_number` integration: https://www.home-assistant.io/integrations/input_number/
- HA core `input_select` integration: https://www.home-assistant.io/integrations/input_select/
- HA core `input_datetime` integration: https://www.home-assistant.io/integrations/input_datetime/
- HA core `input_button` integration: https://www.home-assistant.io/integrations/input_button/
- HA core `script:` integration: https://www.home-assistant.io/integrations/script/
- HA core `template:` integration: https://www.home-assistant.io/integrations/template/
- HA core `logbook` integration: https://www.home-assistant.io/integrations/logbook/

Other connection slices:

- Time-atomic (the §8.2 session-timeout guard's
  time-of-day primitives): `connections/time-atomic/`
  (Wave 3 #55)
- Remote-access (the §8.4 require-confirmation guard's
  VPN primitive): `connections/remote-access/` (Wave 3
  #58)
- Approach lights (the §8.3 audit-log entry's dashboard
  banner pattern): `connections/approach-lights/` (Wave
  3 #52)
- Fans (the §8.1 kill-switch-blocks-everything guard's
  fan-protection cross-reference): `connections/fans/`
  (Wave 3 #59)
- Leveling (the §8.1 kill-switch-blocks-everything
  guard's levelling-jack protection cross-reference):
  `connections/leveling/` (Wave 3 #60)
- Mode (the §8.3 audit-log entry's mode-change cross-
  reference): `connections/mode/` (Wave 3 #61)
- Demo-mode (the §8.5 outside-allowlist deny-by-default
  guard's safety-chip pattern): `connections/demo-mode/`
  (Wave 3 #62)
- Advanced-mode (the §8.4 require-confirmation guard's
  confirm-flag pattern): `connections/advanced-mode/`
  (Wave 3 #63)
- OpenClaw JSON API (the §8.3 audit-log entry's JSON
  payload cross-reference): `connections/openclaw-api/`
  (Wave 3 #64)
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`
  (the `agent_actions` subsystem was added by this slice)