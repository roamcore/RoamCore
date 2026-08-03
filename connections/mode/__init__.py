"""Mode (AI mode) — vendor-neutral mode state (Off / Auto /
Travel / Camp / Stealth) + opt-in AI inference summary +
auto-revert on manual override — tier-b recipe connection.

Note on upstream wiring: tier-b connections don't ship a
RoamCore-owned operator-wired setup flow (a RoamCore
operator-wired wizard); instead, each path uses the upstream
integration's GUI flow (the HA core `input_select` +
`input_boolean` + `input_text` + `input_button` +
`input_number` helpers + the HA core `template:` sensor +
`template:` binary_sensor wrappers + the HA core
Conversation agent + the optional operator-selected LLM
add-ons all expose their own operator-wired setup flow +
GUI flow).

This module is a marker-only stub. Tier-b connections don't
ship native HA integration code; they publish a recipe
(docs/recipe.md) that walks the operator through installing
the upstream helpers + wiring the FIVE operator-pickable
modes:

  - Off — explicitly off. No auto-mode inference, no
    automations triggered by mode. Used when the operator
    wants to be fully manual (rare — most operators prefer
    Auto).

  - Auto — RoamCore infers the current mode from the
    upstream sensors (motion, location, plug-state, time-
    of-day, presence). This is the default for most
    operators. The §9.1 auto-mode inference automation
    reads GPS speed + ignition-on input + presence
    detection + plug-state + time-of-day primitives and
    writes `select.rc_mode_state` every 30 seconds.

  - Travel — the van is moving. Inferred from GPS speed >
    5 km/h OR the ignition-on input. Manual override is
    "I'm parked but I want travel-mode anyway" (e.g.,
    pulling a trailer).

  - Camp — the van is parked + occupied + utilities are
    available. Inferred from GPS speed = 0 + presence
    detected + time-of-day in daylight OR plug connected.
    Manual override is "I'm parked but not camping" (e.g.,
    quick grocery stop).

  - Stealth — the van is parked + occupied + utilities are
    restricted (no plug, no shore power). Used for
    overnight stealth camping in urban areas. Inferred
    from GPS speed = 0 + presence detected + time-of-day
    in night + no plug. Manual override is "I'm stealth
    camping during the day" (rare).

The umbrella publishes the resulting data via the upstream
HA core `input_select` + `input_boolean` + `input_text` +
`input_button` + `input_number` helper entities (since
2022.x — have exposed the standard `input_select.select_
option` + `input_boolean.toggle` + `input_text.set_value` +
`input_button.press` services + the `select` / `binary_
sensor` / `sensor` / `text` / `button` domain entities)
+ the HA core `template:` sensor wrapper (since 2022.x —
wraps any upstream sensor state into a derived `sensor.*`
entity) + the HA core `template:` binary_sensor wrapper
(since 2022.x — wraps any upstream sensor threshold into
a derived `binary_sensor.*` entity) + the HA core
Conversation agent (since 2022.x — the canonical upstream
opt-in AI path; handles natural-language queries + the
opt-in AI inference path) + the optional operator-
selected LLM add-ons (since 2023.x — handle the natural-
language AI summary for `text.rc_mode_ai_summary`), then
publishes the RoamCore mode contract tiles on top (the 10
contract entities documented in connection.yml — 1 select
mode_state + 1 select mode_state_previous + 1 binary_
sensor is_auto_inferred + 1 binary_sensor is_manual_
override + 1 sensor changed_at + 1 sensor inference_
confidence + 1 text ai_summary + 1 button revert_to_auto
+ 1 button force_stealth + 1 button force_travel = 10
contract entities).

The audit + boundary CI can detect a `mode/` folder that
claims to be a connection via the `DOMAIN` constant
exported here. The wizard reads the manifest + recipe at
runtime.

The real per-operator mode affordance path is:

    Operator-side choice of one of the FIVE modes (Off /
        Auto / Travel / Camp / Stealth)
        -> upstream entities (the HA core
           `input_select.rc_mode_state` for the mode
           storage; the HA core `input_boolean.rc_mode_is_
           manual_override` for the manual-override flag;
           the HA core `input_text.rc_mode_changed_at` for
           the changed-at timestamp; the HA core
           `input_select.rc_mode_state_previous` for the
           previous-mode storage; the HA core `sensor.rc_
           mode_inference_confidence` `template:` sensor
           for the inference confidence; the HA core
           `text.rc_mode_ai_summary` for the AI summary)
        -> upstream signals (the operator's chosen GPS
           source — Traccar for vehicle GPS OR the HA
           Companion app for phone GPS; the ignition-on
           input from the vehicle; the presence detection
           from the HA Companion app or Bluetooth/Wi-Fi
           presence; the plug-state from the shore-power
           integration; the time-of-day primitives from the
           time-atomic Wave 3 #55 connection)
        -> RoamCore contract layer (HA core `template:`
           sensor + binary_sensor + select + the
           operator's `input_select` / `input_boolean` /
           `input_text` / `input_button` / `input_number`
           for the contract tiles + the `command_line`
           integration for the upstream reachability probe)
        -> dashboard tiles + OpenClaw queries
            ("what mode are we in?",
             "what was the previous mode?",
             "was the mode auto-inferred?",
             "is the manual override active?",
             "when did the mode last change?",
             "what is the inference confidence?",
             "why are we in travel mode?",
             "revert to auto",
             "force stealth mode",
             "force travel mode")

    Safety interlocks (the recipe is the contract layer;
    the automation wrappers are documented in §9):
        -> The RoamCore auto-mode-inference automation is
           the §9.1 automation that reads the upstream
           GPS speed + ignition-on input + presence
           detection + plug-state + time-of-day primitives
           + writes `select.rc_mode_state` based on the
           inferred state + updates
           `sensor.rc_mode_inference_confidence` with the
           inference confidence. The automation fires every
           30 seconds.
        -> The RoamCore manual-override + auto-revert
           automation is the §9.2 automation that fires
           when the operator picks a mode directly via the
           dashboard OR presses one of the force_*
           buttons. The automation sets
           `binary_sensor.rc_mode_is_manual_override` to
           TRUE + starts a 30-minute timer; after 30
           minutes, the automation clears the manual
           override + reverts to the auto-inferred mode.
        -> The RoamCore confirm-before-power-changing-
           action automation is the §9.3 automation that
           fires when the §9.1 auto-mode inference
           suggests Travel mode AND the §9.2 manual
           override is active. The automation fires a
           confirmation notification before any power-
           changing action fires (e.g., turning off the
           fridge compressor when entering Travel mode —
           the operator must confirm).
        -> The RoamCore stealth-mode-audit-log automation
           is the §9.4 automation that fires when the
           mode transitions to Stealth. The automation
           writes an audit-log entry + fires a notification
           warning the operator to check the cabin-light
           state.
        -> The RoamCore mode-change-notification
           automation is the §9.5 automation that fires
           when `select.rc_mode_state` changes. The
           automation updates `select.rc_mode_state_
           previous` + writes `sensor.rc_mode_changed_at`
           + (if the AI path is opted-in) asks the
           upstream Conversation agent for a short
           natural-language summary that gets written to
           `text.rc_mode_ai_summary`.

    Cross-references:
        -> The HA core `input_select` + `input_boolean`
           + `input_text` + `input_button` + `input_number`
           helper entities are the canonical umbrella
           (since 2022.x — expose the standard contract).
        -> The HA core `template:` sensor wrapper is the
           canonical inference-confidence + AI-summary
           derivation (since 2022.x).
        -> The HA core `template:` binary_sensor wrapper is
           the canonical is-auto-inferred + is-manual-
           override derivation (since 2022.x).
        -> The HA core Conversation agent is the canonical
           upstream opt-in AI path (since 2022.x — exposes
           a GUI flow for the operator to enable the agent
           from the HA UI).
        -> The optional operator-selected LLM add-ons are
           the canonical upstream natural-language AI
           summary (since 2023.x — expose a GUI flow for
           the operator to add their API key + provider).
        -> The time-atomic Wave 3 #55 connection cross-
           references the time-of-day primitives used by
           the §9.1 auto-mode inference.
        -> The motion-based-lighting Wave 3 #53 connection
           cross-references the presence-detection
           primitive used by the §9.1 auto-mode inference.
        -> The approach lights Wave 3 #52 connection cross-
           references the cabin-lighting scene modified by
           the §9.4 stealth-mode audit-log entry.
        -> The remote-access Wave 3 #58 connection cross-
           references the VPN primitive used by the §9.5
           mode-change notification's optional Telegram
           delivery.
        -> The fans Wave 3 #59 connection cross-references
           the §9.3 confirm-before-power-changing-action
           guard's fan-off-on-mode-change behavior.
        -> The leveling Wave 3 #60 connection cross-
           references the §9.5 mode-change notification's
           level-cross-reference (the §9.5 mode-change
           notification cross-references the leveling
           mode's fridge-safe state).
        -> The NFC tags Wave 3 #57 connection cross-
           references the optional NFC-tag-triggered mode-
           change affordance (e.g., tapping an NFC tag at
           the bed to switch to Sleep mode).
        -> The mode/automation-builder Wave 2 #23 recipe
           cross-references the legacy `select.rc_mode`
           tile (the §9.1 auto-mode inference writes to
           `select.rc_mode_state`, NOT `select.rc_mode` —
           the two tiles are intentionally distinct: the
           legacy `select.rc_mode` is the Wave 2 #23
           recipe's "what is the van doing right now?"
           high-level selector; `select.rc_mode_state` is
           the Wave 3 #61 recipe's "what is the mode the
           automations + UI should branch on?" low-level
           state tile).

See docs/recipe.md for the full howto (HA core
`input_select` + `input_boolean` + `input_text` +
`input_button` + `input_number` helper install + HA core
`template:` sensor wrapper install + HA core
`template:` binary_sensor wrapper install + HA core
Conversation agent install + optional operator-selected
LLM add-on install + the FIVE operator-pickable modes +
the 10 `rc_mode_*` contract tiles + the FIVE §9
MANDATORY automations + the 6 §10 troubleshooting
entries + privacy + tier-a promotion outline).
"""

DOMAIN = "mode"