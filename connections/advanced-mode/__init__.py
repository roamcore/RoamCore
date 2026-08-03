"""Advanced mode — vendor-neutral power-user toggle +
session-timeout guard + destructive-calls block — tier-b
recipe connection.

Note on upstream wiring: tier-b connections don't ship a
RoamCore-owned operator-wired setup flow (a RoamCore
operator-wired wizard); instead, each path uses the
upstream integration's GUI flow (the HA core `input_boolean`
+ `input_text` + `input_datetime` + `input_button` + `select`
helpers + the HA core `template:` sensor wrapper + the HA
core `template:` binary_sensor wrapper all expose their own
operator-wired setup flow + GUI flow).

This module is a marker-only stub. Tier-b connections don't
ship native HA integration code; they publish a recipe
(docs/recipe.md) that walks the operator through installing
the upstream helpers + wiring the FOUR-step operator flow:

  - Step 1 — Confirm — the operator explicitly confirms
    "I understand advanced mode exposes destructive
    irreversible service calls" by flipping
    `input_boolean.rc_advanced_mode_confirmed` helper ON
    (default OFF). Without this confirm, advanced controls
    stay hidden even if the master toggle is ON.

  - Step 2 — Enable — the operator flips
    `input_boolean.rc_advanced_mode_enabled` ON. The
    dashboard now shows the "advanced" badge + reveals the
    hidden diagnostics tiles + unlocks the operator-only
    controls. The §3 confirm-before-toggle-on guard
    documents the recipe's "if confirm-flag is OFF, the
    enable toggle refuses to stay ON" enforcement.

  - Step 3 — Session window — once enabled, advanced mode
    stays ON until either the operator disables it OR the
    `input_datetime.rc_advanced_mode_session_expires_at`
    timestamp is reached (default: 24 hours from when the
    toggle was flipped ON, controlled by the
    `select.rc_advanced_mode_session_duration` selector 1
    hour / 6 hours / 24 hours / 7 days / Never). After
    timeout, the toggle auto-reverts to OFF. The §4 auto-
    disable after session timeout guard fires when the
    expiry timestamp is reached.

  - Step 4 — Audit + revert — every advanced-mode toggle
    flip + every destructive irreversible service call that
    the operator initiates while advanced mode is ON is
    logged to `sensor.rc_advanced_mode_last_action_at` +
    counted in `sensor.rc_advanced_mode_session_action_count`.
    The operator can revert at any time via
    `button.rc_advanced_mode_disable_now`. The §5 audit-log
    entry guard fires on every destructive irreversible
    service call the operator initiates while advanced mode
    is ON.

The umbrella publishes the resulting data via the upstream
HA core `input_boolean` + `input_text` + `input_datetime` +
`input_button` + `select` helper entities (since 2022.x —
have exposed the standard `input_boolean.toggle` +
`input_text.set_value` + `input_datetime.set_datetime` +
`input_button.press` + `select.select_option` services + the
`input_boolean` / `select` / `sensor` / `binary_sensor` /
`button` domain entities) + the HA core `template:` sensor
wrapper (since 2022.x — wraps any upstream sensor state into
a derived `sensor.*` entity) + the HA core `template:`
binary_sensor wrapper (since 2022.x — wraps any upstream
sensor threshold into a derived `binary_sensor.*` entity),
then publishes the RoamCore advanced-mode contract tiles on
top (the 11 contract entities documented in connection.yml
— 1 input_boolean advanced_mode_confirmed + 1 input_boolean
advanced_mode_enabled + 1 input_datetime
advanced_mode_session_expires_at + 1 sensor
advanced_mode_seconds_until_expiry + 1 sensor
advanced_mode_session_action_count + 1 sensor
advanced_mode_last_action_at + 1 binary_sensor
advanced_mode_is_active + 1 binary_sensor
advanced_mode_is_blocking_destructive_calls + 1 select
advanced_mode_session_duration + 1 button
advanced_mode_enable + 1 button advanced_mode_disable_now
= 11 contract entities).

The audit + boundary CI can detect an `advanced-mode/`
folder that claims to be a connection via the `DOMAIN`
constant exported here. The wizard reads the manifest +
recipe at runtime.

The real per-operator advanced-mode affordance path is:

    Operator-side choice of the FOUR-step flow (Confirm ->
        Enable -> Session window -> Audit + revert)
        -> upstream entities (the HA core
           `input_boolean.rc_advanced_mode_confirmed` for
           the confirm-flag; the HA core
           `input_boolean.rc_advanced_mode_enabled` for the
           master enable; the HA core
           `input_datetime.rc_advanced_mode_session_expires_
           at` for the session expiry timestamp; the HA core
           `sensor.rc_advanced_mode_seconds_until_expiry`
           `template:` sensor for the resolved countdown;
           the HA core `sensor.rc_advanced_mode_session_
           action_count` `template:` sensor for the
           destructive-call counter; the HA core
           `sensor.rc_advanced_mode_last_action_at`
           `template:` sensor for the last destructive-call
           timestamp; the HA core `binary_sensor.rc_advanced_
           mode_is_active` `template:` binary_sensor for the
           resolved active chip; the HA core
           `binary_sensor.rc_advanced_mode_is_blocking_
           destructive_calls` `template:` binary_sensor for
           the safety chip; the HA core `select.rc_advanced_
           mode_session_duration` for the auto-revert
           duration picker; the HA core `button.rc_advanced_
           mode_enable` + `button.rc_advanced_mode_disable_
           now` for the operator-triggered one-tap enable /
           disable affordances)
        -> upstream signals (the operator's chosen
           destructive irreversible service call targets —
           the operator populates
           `input_text.rc_advanced_mode_destructive_call_
           targets` with the comma-separated list of
           service names the §8.5 destructive-calls block
           should protect)
        -> RoamCore contract layer (HA core `template:`
           sensor + binary_sensor + select + the operator's
           `input_boolean` / `input_text` / `input_datetime` /
           `input_button` for the contract tiles + the
           `command_line` integration for any upstream
           reachability probe)
        -> dashboard tiles + OpenClaw queries
            ("is advanced mode active?",
             "is advanced mode blocking destructive calls?",
             "how many destructive calls this session?",
             "when was the last destructive call?",
             "when does advanced mode expire?",
             "enable advanced mode",
             "disable advanced mode now")

    Safety interlocks (the recipe is the contract layer;
    the automation wrappers are documented in §8):
        -> The RoamCore confirm-before-toggle-on guard is
           the §8.1 automation that fires when a non-
           operator source tries to flip
           `input_boolean.rc_advanced_mode_enabled` ON
           without first flipping
           `input_boolean.rc_advanced_mode_confirmed` ON.
           The automation BLOCKS the enable flip + writes
           an audit-log entry + fires a notification warning
           the operator that the confirm-flag must be flipped
           ON first.
        -> The RoamCore auto-disable after session timeout
           guard is the §8.2 automation that fires when
           `input_datetime.rc_advanced_mode_session_expires_
           at` timestamp is reached. The automation clears
           the enable toggle + clears the session_expires_at
           + writes an audit-log entry + fires a notification
           warning the operator that advanced mode has been
           auto-disabled.
        -> The RoamCore hides-for-non-owners guard is the
           §8.3 automation that fires when a non-owner
           dashboard session attempts to view the advanced-
           mode dashboard page while
           `input_boolean.rc_advanced_mode_enabled` is ON.
           The automation hides the advanced-mode tiles +
           surfaces an "advanced mode hidden for non-owners"
           banner + writes an audit-log entry.
        -> The RoamCore audit-log-entry guard is the §8.4
           automation that fires on every destructive
           irreversible service call the operator initiates
           while `input_boolean.rc_advanced_mode_enabled` is
           ON. The automation writes an audit-log entry with
           the service name + the target entity + the
           operator identity (if the remote-access session
           tracks it) + the timestamp + the reason.
        -> The RoamCore blocks-destructive-irreversible-
           service-calls guard is the §8.5 automation that
           fires when ANY `script.*` / `automation.*` action
           tries to call a destructive irreversible service
           (the operator has flagged in
           `input_text.rc_advanced_mode_destructive_call_
           targets`) while
           `input_boolean.rc_advanced_mode_enabled` is OFF.
           The automation BLOCKS the service call + logs a
           security-style audit entry + flips
           `binary_sensor.rc_advanced_mode_is_blocking_
           destructive_calls` to FALSE + fires a critical
           notification.

    Cross-references:
        -> The HA core `input_boolean` + `input_text` +
           `input_datetime` + `input_button` + `select`
           helper entities are the canonical umbrella (since
           2022.x — expose the standard contract).
        -> The HA core `template:` sensor wrapper is the
           canonical seconds-until-expiry + session-action-
           count + last-action-at derivation (since 2022.x).
        -> The HA core `template:` binary_sensor wrapper is
           the canonical is-active + is-blocking-destructive-
           calls derivation (since 2022.x).
        -> The time-atomic Wave 3 #55 connection cross-
           references the time-of-day primitives used by the
           §8.2 auto-disable after session timeout guard's
           expiry timestamp.
        -> The remote-access Wave 3 #58 connection cross-
           references the VPN primitive used by the §8.3
           hides-for-non-owners guard's owner-identity check.
        -> The mode Wave 3 #61 connection cross-references
           the §8.4 audit-log entry's mode-change cross-
           reference (the guard surfaces advanced-mode
           transitions on the mode-change notification
           timeline).
        -> The demo-mode Wave 3 #62 connection cross-
           references the §8.1 confirm-before-toggle-on
           guard's confirm-flag pattern (mirrors the demo-
           mode §8.5 operator-only guard's confirm-flag
           pattern).
        -> The leveling Wave 3 #60 connection cross-
           references the §8.5 blocks-destructive-
           irreversible-service-calls guard's levelling-jack
           protection cross-reference (the guard protects
           real levelling jacks from being lowered by a
           stray destructive service call).
        -> The fans Wave 3 #59 connection cross-references
           the §8.5 blocks-destructive-irreversible-service-
           calls guard's fan-protection cross-reference (the
           guard protects real fans from being turned off by
           a stray destructive service call).

See docs/recipe.md for the full howto (HA core
`input_boolean` + `input_text` + `input_datetime` +
`input_button` + `select` helper install + HA core
`template:` sensor wrapper install + HA core `template:`
binary_sensor wrapper install + the FOUR-step operator-
pickable advanced-mode flow + the 11 `rc_advanced_mode_*`
contract tiles + the FIVE §8 MANDATORY automations + the
6 §9 troubleshooting entries + privacy + tier-a promotion
outline).
"""

DOMAIN = "advanced_mode"
