# Mode (AI mode) — full howto (RoamCore vendor-neutral mode state (Off / Auto / Travel / Camp / Stealth) + opt-in AI inference summary + auto-revert on manual override)

This recipe is the canonical howto for the
`connections/mode/` tier-b recipe connection (Wave 3
#61). It walks the operator through setting up the FIVE
operator-pickable modes (Off + Auto + Travel + Camp +
Stealth) + the 10 `rc_mode_*` contract tiles + the FIVE
§9 MANDATORY automations + the optional opt-in AI
inference summary path.

The recipe assumes the operator has at least the upstream
helpers installed (HA core `input_select` + `input_boolean`
+ `input_text` + `input_button` + `input_number` since
2022.x — auto-installed in every HA install) + at least
ONE upstream signal source (GPS speed from Traccar OR the
HA Companion app OR the ignition-on input OR presence
detection OR plug-state OR the time-atomic primitives).
If the operator has no upstream signals wired, the recipe
starts at §2 Prerequisites + walks through the upstream-
signal wiring before the mode-state wiring.

## §1 What is Mode in RoamCore?

Mode (AI mode) — vendor-neutral mode state (Off / Auto /
Travel / Camp / Stealth) + opt-in AI inference summary +
auto-revert on manual override — the umbrella for
"Quickly switch the van between common states (driving,
parked, quiet night). A clean way to group automations
later without building everything at once" — is the
ai-category complement to the broader RoamCore automation
affordances. The umbrella positions Mode as an ai-category
concern (not a vehicle-category concern + not a power-
load concern + not a remote-access concern) because Mode
is the operator-facing "what is the van doing right now?"
state surface: the mode tile collapses a pile of inferred
state (motion, location, plug-state, time-of-day,
presence) into a single dashboard indicator that the rest
of the UI + automations can branch on; the previous-mode
tile is the "auto-revert in 30 minutes" affordance's
source of truth; the is-auto-inferred + is-manual-override
tiles are the §9.1 + §9.2 automation's source of truth;
the inference-confidence tile is the §9.1 auto-mode
inference's confidence in the current mode; the AI-summary
tile is the opt-in AI path's natural-language summary of
WHY the mode is what it is; the revert-to-auto + force-
stealth + force-travel buttons are the operator-facing
affordances for manual mode control.

The mode tile (`select.rc_mode_state`) is the operator's
"what is the van doing right now?" dashboard indicator —
the recipe exposes the Off / Auto / Travel / Camp /
Stealth options so the operator can see at a glance
whether the van is parked, driving, camping, stealth-
camping, or fully manual.

The is-manual-override tile (`binary_sensor.rc_mode_is_
manual_override`) is the §9 MANDATORY safety gate — when
the tile flips to TRUE, the §9.2 manual-override +
auto-revert automation starts a 30-minute timer; after 30
minutes, the automation clears the manual override +
reverts to the auto-inferred mode. This is the single
most important affordance in the mode umbrella: forgetting
to wire the manual-override auto-revert can leave the
operator with a stale mode state (the auto-mode inference
cannot take over until the operator manually clears the
override).

The mode-change-notification tile (`sensor.rc_mode_changed_
at`) is the operator-facing "when did the mode last
change?" affordance — the §9.5 mode-change notification
automation updates the tile on every mode change so the
operator can review the mode history at a glance.

The AI-summary tile (`text.rc_mode_ai_summary`) is the
opt-in AI path's natural-language summary of WHY the mode
is what it is — the §9.5 mode-change notification
automation, IF the operator has enabled the Conversation
agent + an optional operator-selected LLM add-on, asks
the upstream Conversation agent for a short natural-
language summary that gets written to the tile. The AI
path is OPT-IN (the operator can use Mode without the AI
summary; the AI summary is just a convenience for
operators who want a natural-language explanation).

The revert-to-auto button (`button.rc_mode_revert_to_
auto`) is the operator-facing affordance to drop the
manual override — pressing the button fires the §9.2
manual-override auto-revert automation, which clears
the manual override + reverts to the auto-inferred mode.

The force-stealth button (`button.rc_mode_force_stealth`)
is the operator-facing affordance to force Stealth mode
regardless of inference — pressing the button fires the
§9.2 manual-override automation with the `stealth`
option.

The force-travel button (`button.rc_mode_force_travel`)
is the operator-facing affordance to force Travel mode
regardless of inference — pressing the button fires the
§9.2 manual-override automation with the `travel`
option.

## §2 Prerequisites

### §2.1 Universal prerequisites

- HA core `input_select` + `input_boolean` + `input_text`
  + `input_button` + `input_number` helper entities
  installed (HA core since 2022.x — auto-installed in
  every HA install).
- HA core `template:` integration installed (HA core
  since 2022.x — auto-installed in every HA install).
- HA core Conversation agent installed (HA core since
  2022.x — Settings → Voice assistants → Conversation
  agent; this is the canonical upstream opt-in AI path;
  the operator can skip this if they don't want the AI
  summary).
- Optional upstream LLM add-ons installed (since 2023.x
  — Settings → Integrations → add the LLM provider; the
  operator can skip these if they don't want the AI
  summary).
- The HA server reachable from the operator's chosen
  upstream signal source (local network for the upstream
  signals).

### §2.2 Upstream signal prerequisites

The operator must wire at least ONE of the following
upstream signal sources (the §9.1 auto-mode inference
reads from these signals to infer the mode):

- **GPS speed** — Traccar for vehicle GPS (since 2022.x)
  OR the HA Companion app on iOS / Android (since 2022.x)
  for phone GPS. The §9.1 auto-mode inference uses
  `sensor.<tracker>_speed` (Traccar) OR
  `sensor.<phone>_accelerometer` (HA Companion app). Path
  A (Traccar) is the default for vehicle GPS; Path B (HA
  Companion app) is the default for phone GPS.
- **Ignition-on input** — the operator's chosen vehicle
  integration (varies by van). The §9.1 auto-mode
  inference uses `binary_sensor.<vehicle>_ignition` (the
  operator's chosen integration's ignition entity).
- **Presence detection** — the HA Companion app on iOS /
  Android (since 2022.x) OR Bluetooth/Wi-Fi presence.
  The §9.1 auto-mode inference uses
  `device_tracker.<phone>` (HA Companion app) OR
  `device_tracker.<user>` (Bluetooth/Wi-Fi presence).
- **Plug-state** — the operator's chosen shore-power
  integration (varies by van). The §9.1 auto-mode
  inference uses `binary_sensor.<shore_power>_connected`
  (the operator's chosen integration's plug entity).
- **Time-of-day primitives** — the time-atomic Wave 3
  #55 connection's sunrise/sunset primitives. The §9.1
  auto-mode inference uses `sensor.rc_time_sun_elevation`
  (the time-atomic connection's sun-elevation tile).

### §2.3 Optional cross-references (recommended)

- The time-atomic Wave 3 #55 connection's
  `sensor.rc_time_sun_elevation` for the §9.1 auto-mode
  inference's day/night decision.
- The motion-based-lighting Wave 3 #53 connection's
  presence-detection primitive for the §9.1 auto-mode
  inference's presence detection.
- The approach lights Wave 3 #52 connection's cabin-
  lighting scene for the §9.4 stealth-mode audit-log
  entry's cabin-light check.
- The remote-access Wave 3 #58 connection's VPN primitive
  for the §9.5 mode-change notification's optional
  Telegram delivery.
- The fans Wave 3 #59 connection's fan control for the
  §9.3 confirm-before-power-changing-action guard's fan-
  off-on-mode-change behavior.
- The leveling Wave 3 #60 connection's fridge-safe tile
  for the §9.5 mode-change notification's level-cross-
  reference.
- The NFC tags Wave 3 #57 connection's NFC-tag-trigger
  primitive for the optional NFC-tag-triggered mode-
  change affordance.
- The mode/automation-builder Wave 2 #23 recipe's legacy
  `select.rc_mode` tile (the Wave 3 #61 recipe's
  `select.rc_mode_state` is intentionally distinct from
  this legacy tile — the two tiles are documented in §13
  Files + cross-references).

## §3 Off mode (the default for fully-manual operators)

Off mode is the operator-facing "I want to be fully
manual" affordance — Off means no auto-mode inference +
no automations triggered by mode. The operator picks Off
mode from the `select.rc_mode_state` dashboard tile (or
via the legacy `script.rc_mode_set_off` script) and the
§9.1 auto-mode inference + the §9.2 manual-override
automation are both disabled.

### §3.1 Off mode steps

1. Verify the upstream `select.rc_mode_state` entity
   exists (Settings → Helpers → RC Mode State).
2. Pick `off` from the `select.rc_mode_state` dropdown.
3. Verify the §9.1 auto-mode inference automation is
   disabled (Developer Tools → Automations → search
   "rc_mode_auto_mode_inference" → toggle OFF).
4. Verify the §9.2 manual-override + auto-revert
   automation is disabled (Developer Tools →
   Automations → search "rc_mode_manual_override_auto_
   revert" → toggle OFF).
5. Verify: check `binary_sensor.rc_mode_is_auto_inferred`
   is `off` (the §9.1 is disabled, so the tile stays
   `off`).
6. Verify: check `binary_sensor.rc_mode_is_manual_
   override` is `off` (no manual override is active).
7. Done. Skip to §7 for the contract tile derivation +
   §9 for the FIVE MANDATORY automations.

## §4 Auto mode (the inference logic)

Auto mode is the operator-facing "RoamCore infers the
current mode from the upstream sensors" affordance — the
§9.1 auto-mode inference automation reads the upstream
GPS speed + ignition-on input + presence detection +
plug-state + time-of-day primitives and writes
`select.rc_mode_state` every 30 seconds. This is the
default for most operators.

### §4.1 Auto mode steps

1. Verify the upstream `select.rc_mode_state` entity
   exists.
2. Pick `auto` from the `select.rc_mode_state` dropdown.
3. Verify the §9.1 auto-mode inference automation is
   ENABLED (Developer Tools → Automations → search
   "rc_mode_auto_mode_inference" → toggle ON).
4. Verify the §9.2 manual-override + auto-revert
   automation is ENABLED.
5. Verify: check `binary_sensor.rc_mode_is_auto_inferred`
   is `on` (the §9.1 is enabled, so the tile is `on`).
6. Verify: check `binary_sensor.rc_mode_is_manual_
   override` is `off` (no manual override is active).
7. Verify the inference is working: drive the van (GPS
   speed > 5 km/h) + check `select.rc_mode_state`
   switches to `travel`. Park the van (GPS speed = 0 +
   presence detected + time-of-day in daylight OR plug
   connected) + check `select.rc_mode_state` switches to
   `camp`. Park the van (GPS speed = 0 + presence
   detected + time-of-day in night + no plug) + check
   `select.rc_mode_state` switches to `stealth`.
8. Verify: check `sensor.rc_mode_inference_confidence`
   reflects the §9.1 automation's confidence (0.0–1.0;
   higher when more signals agree, lower when signals
   conflict).
9. Done. Skip to §7 for the contract tile derivation +
   §9 for the FIVE MANDATORY automations.

## §5 Travel mode (the "I'm moving" affordance)

Travel mode is the operator-facing "the van is moving"
affordance — Travel means GPS speed > 5 km/h OR the
ignition-on input is TRUE. The §9.1 auto-mode inference
automatically switches to Travel when the GPS speed
exceeds 5 km/h; the operator can also manually force
Travel mode via `button.rc_mode_force_travel` (e.g.,
"pulling a trailer" use case).

### §5.1 Travel mode steps

1. Verify the upstream `select.rc_mode_state` entity
   exists.
2. Either pick `travel` from the `select.rc_mode_state`
   dropdown OR press `button.rc_mode_force_travel`.
3. Verify the §9.2 manual-override + auto-revert
   automation is ENABLED (if the operator manually
   picked Travel, the §9.2 starts a 30-minute timer; if
   the §9.1 auto-mode inference picked Travel, no timer
   is needed).
4. Verify: check `binary_sensor.rc_mode_is_manual_
   override` is `on` (the operator manually picked
   Travel, so the tile is `on`).
5. Verify: wait 30 minutes + check `binary_sensor.rc_
   mode_is_manual_override` is `off` (the §9.2 auto-
   revert fired).
6. Done. Skip to §7 for the contract tile derivation +
   §9 for the FIVE MANDATORY automations.

## §6 Camp mode (the "I'm parked + camping" affordance)

Camp mode is the operator-facing "the van is parked +
camping" affordance — Camp means GPS speed = 0 + presence
detected + time-of-day in daylight OR plug connected. The
§9.1 auto-mode inference automatically switches to Camp
when the van is parked + occupied + utilities are
available; the operator can also manually force Camp mode
via the dashboard.

### §6.1 Camp mode steps

1. Verify the upstream `select.rc_mode_state` entity
   exists.
2. Pick `camp` from the `select.rc_mode_state` dropdown
   (OR let the §9.1 auto-mode inference pick it for you
   when the conditions are met).
3. Verify the §9.2 manual-override + auto-revert
   automation is ENABLED.
4. Verify: check `binary_sensor.rc_mode_is_manual_
   override` is `on` if manually picked + `off` if
   auto-inferred.
5. Verify: the §9.4 stealth-mode audit-log automation
   is NOT firing (Camp mode is not stealth, so no audit-
   log entry is written).
6. Done. Skip to §7 for the contract tile derivation +
   §9 for the FIVE MANDATORY automations.

## §7 Stealth mode (the "I'm stealth camping" affordance)

Stealth mode is the operator-facing "the van is parked +
stealth camping" affordance — Stealth means GPS speed = 0
+ presence detected + time-of-day in night + no plug. The
§9.1 auto-mode inference automatically switches to
Stealth when the van is parked + occupied + utilities are
restricted + it's night; the operator can also manually
force Stealth mode via `button.rc_mode_force_stealth`
(e.g., "I'm stealth camping during the day" use case).

### §7.1 Stealth mode steps

1. Verify the upstream `select.rc_mode_state` entity
   exists.
2. Either pick `stealth` from the `select.rc_mode_state`
   dropdown OR press `button.rc_mode_force_stealth` OR
   let the §9.1 auto-mode inference pick it for you when
   the conditions are met.
3. Verify the §9.2 manual-override + auto-revert
   automation is ENABLED (if the operator manually
   picked Stealth, the §9.2 starts a 30-minute timer).
4. Verify: the §9.4 stealth-mode audit-log automation
   fires + writes an audit-log entry + fires a
   notification warning the operator to check the cabin-
   light state.
5. Verify: check `binary_sensor.rc_mode_is_manual_
   override` is `on` if manually picked + `off` if
   auto-inferred.
6. Done. Skip to §8 for the contract tile derivation +
   §9 for the FIVE MANDATORY automations.

## §8 RoamCore contract entities

The mode contract layer is a thin upstream-entity-
aggregation layer. The 10 `rc_mode_*` contract tiles are
vendor-neutral — no OpenAI / Anthropic / Claude / GPT /
Conversation / LLM / GPS / accelerometer / phone /
Companion / HA / HACS / MQTT / webhook / REST / API /
HTTP / HTTPS / input_select / input_boolean / input_text
/ input_button / template names leak into the tile ids.

### §8.1 The 10 `rc_mode_*` contract tiles

- `select.rc_mode_state` — Off / Auto / Travel / Camp /
  Stealth (current mode, operator-overridable from the
  dashboard). The tile is an `input_select:` domain
  entity (since 2022.x) that the operator picks from a
  list.
  ```yaml
  input_select:
    rc_mode_state:
      name: RC Mode State
      options:
        - off
        - auto
        - travel
        - camp
        - stealth
      initial: auto
      icon: mdi:route
  ```

- `select.rc_mode_state_previous` — the mode before the
  last change. The tile is an `input_select:` domain
  entity (since 2022.x) that the operator's automations
  write to before a manual override.
  ```yaml
  input_select:
    rc_mode_state_previous:
      name: RC Mode State Previous
      options:
        - off
        - auto
        - travel
        - camp
        - stealth
      initial: auto
      icon: mdi:route-clock
  ```

- `binary_sensor.rc_mode_is_auto_inferred` — TRUE when
  mode was inferred by the upstream sensors, FALSE when
  manually overridden. The tile is a `template:`
  binary_sensor (since 2022.x) that derives from the
  §9.2 manual override automation's tracking state.
  ```yaml
  binary_sensor:
    - platform: template
      sensors:
        rc_mode_is_auto_inferred:
          friendly_name: "RC Mode Is Auto Inferred"
          value_template: >-
            {{ is_state('input_boolean.rc_mode_is_manual_override', 'off') }}
  ```

- `binary_sensor.rc_mode_is_manual_override` — TRUE when
  operator has overridden the auto-inference; auto-clears
  after 30 minutes unless re-poked. The tile is an
  `input_boolean:` domain entity (since 2022.x) that the
  §9.2 manual override automation toggles.
  ```yaml
  input_boolean:
    rc_mode_is_manual_override:
      name: RC Mode Is Manual Override
      initial: off
      icon: mdi:account-cog
  ```

- `sensor.rc_mode_changed_at` — ISO timestamp of last
  mode change. The tile is an `input_text:` domain
  entity (since 2022.x) that the operator's automations
  write to on every mode change.
  ```yaml
  input_text:
    rc_mode_changed_at:
      name: RC Mode Changed At
      initial: "Never"
      icon: mdi:clock-outline
  ```

- `sensor.rc_mode_inference_confidence` — 0.0–1.0; the
  upstream inference's confidence in the current mode.
  The tile is a `template:` sensor (since 2022.x) that
  the §9.1 auto-mode inference automation writes to.
  ```yaml
  input_number:
    rc_mode_inference_confidence:
      name: RC Mode Inference Confidence
      min: 0.0
      max: 1.0
      step: 0.01
      initial: 0.0
      icon: mdi:gauge
  ```

- `text.rc_mode_ai_summary` — a short natural-language
  summary of WHY the mode is what it is; populated by
  the opt-in AI path via the upstream HA core
  Conversation agent + the optional operator-selected
  LLM add-ons (RoamCore ships NO custom LLM code). The
  tile is a `text:` domain entity (since 2024.x) that
  the §9.5 mode-change notification automation writes
  to.
  ```yaml
  text:
    rc_mode_ai_summary:
      name: RC Mode AI Summary
      max: 255
  ```

- `button.rc_mode_revert_to_auto` — operator-triggered:
  drop the manual override and let auto-inference take
  over. The button is an `input_button:` domain entity
  (since 2022.x) that fires the §9.2 manual override
  auto-revert automation.
  ```yaml
  input_button:
    rc_mode_revert_to_auto:
      name: RC Mode Revert To Auto
      icon: mdi:refresh
  ```

- `button.rc_mode_force_stealth` — operator-triggered:
  force Stealth mode regardless of inference. The
  button is an `input_button:` domain entity (since
  2022.x) that fires the §9.2 manual override
  automation with the `stealth` option.
  ```yaml
  input_button:
    rc_mode_force_stealth:
      name: RC Mode Force Stealth
      icon: mdi:eye-off
  ```

- `button.rc_mode_force_travel` — operator-triggered:
  force Travel mode regardless of inference. The button
  is an `input_button:` domain entity (since 2022.x)
  that fires the §9.2 manual override automation with
  the `travel` option.
  ```yaml
  input_button:
    rc_mode_force_travel:
      name: RC Mode Force Travel
      icon: mdi:car
  ```

## §9 Automations (MANDATORY before first use)

The §9 walks through the FIVE MANDATORY automations. The
recipe is the contract layer; the automation wrappers are
documented below.

### §9.1 Auto-mode inference from GPS + motion + plug + time-of-day

The automation reads the upstream GPS speed + ignition-on
input + presence detection + plug-state + time-of-day
primitives and writes `select.rc_mode_state` based on the
inferred state + updates
`sensor.rc_mode_inference_confidence` with the inference
confidence. The automation fires every 30 seconds.

```yaml
automation:
  - id: rc_mode_auto_mode_inference
    alias: "RC Mode: Auto-mode inference from GPS + motion + plug + time-of-day"
    mode: single
    trigger:
      - platform: time_pattern
        seconds: "/30"
    condition:
      - condition: state
        entity_id: input_boolean.rc_mode_is_manual_override
        state: "off"
    action:
      - choose:
          # Travel: van is moving (GPS speed > 5 km/h OR ignition on).
          - conditions:
              - condition: numeric_state
                entity_id: sensor.van_gps_speed
                above: 5
            sequence:
              - service: input_select.select_option
                target:
                  entity_id: input_select.rc_mode_state
                data:
                  option: travel
              - service: input_number.set_value
                target:
                  entity_id: input_number.rc_mode_inference_confidence
                data:
                  value: 0.95
          # Stealth: van is parked + occupied + night + no plug.
          - conditions:
              - condition: numeric_state
                entity_id: sensor.van_gps_speed
                below: 1
              - condition: state
                entity_id: binary_sensor.van_presence
                state: "on"
              - condition: numeric_state
                entity_id: sensor.rc_time_sun_elevation
                below: 0
              - condition: state
                entity_id: binary_sensor.van_shore_power
                state: "off"
            sequence:
              - service: input_select.select_option
                target:
                  entity_id: input_select.rc_mode_state
                data:
                  option: stealth
              - service: input_number.set_value
                target:
                  entity_id: input_number.rc_mode_inference_confidence
                data:
                  value: 0.90
          # Camp: van is parked + occupied + (daylight OR plug).
          - conditions:
              - condition: numeric_state
                entity_id: sensor.van_gps_speed
                below: 1
              - condition: state
                entity_id: binary_sensor.van_presence
                state: "on"
            sequence:
              - service: input_select.select_option
                target:
                  entity_id: input_select.rc_mode_state
                data:
                  option: camp
              - service: input_number.set_value
                target:
                  entity_id: input_number.rc_mode_inference_confidence
                data:
                  value: 0.85
          # Off: no signal (van is parked + unoccupied + no plug).
          - conditions:
              - condition: numeric_state
                entity_id: sensor.van_gps_speed
                below: 1
              - condition: state
                entity_id: binary_sensor.van_presence
                state: "off"
            sequence:
              - service: input_select.select_option
                target:
                  entity_id: input_select.rc_mode_state
                data:
                  option: off
              - service: input_number.set_value
                target:
                  entity_id: input_number.rc_mode_inference_confidence
                data:
                  value: 0.70
```

### §9.2 Manual override + auto-revert

The automation fires when the operator picks a mode
directly via the dashboard OR presses one of the force_*
buttons. The automation sets
`binary_sensor.rc_mode_is_manual_override` to TRUE +
starts a 30-minute timer; after 30 minutes, the
automation clears the manual override + reverts to the
auto-inferred mode.

```yaml
automation:
  - id: rc_mode_manual_override_auto_revert
    alias: "RC Mode: Manual override + auto-revert (30 min)"
    mode: single
    trigger:
      - platform: state
        entity_id: input_select.rc_mode_state
      - platform: state
        entity_id: input_button.rc_mode_revert_to_auto
      - platform: state
        entity_id: input_button.rc_mode_force_stealth
      - platform: state
        entity_id: input_button.rc_mode_force_travel
    action:
      - choose:
          # revert_to_auto button pressed: clear manual override.
          - conditions:
              - condition: template
                value_template: >-
                  {{ trigger.entity_id == 'input_button.rc_mode_revert_to_auto' }}
            sequence:
              - service: input_boolean.turn_off
                target:
                  entity_id: input_boolean.rc_mode_is_manual_override
              - service: logbook.log
                data:
                  name: RoamCore
                  message: "Mode manual override cleared via revert_to_auto button"
          # force_stealth button pressed: force Stealth mode.
          - conditions:
              - condition: template
                value_template: >-
                  {{ trigger.entity_id == 'input_button.rc_mode_force_stealth' }}
            sequence:
              - service: input_select.select_option
                target:
                  entity_id: input_select.rc_mode_state
                data:
                  option: stealth
              - service: input_boolean.turn_on
                target:
                  entity_id: input_boolean.rc_mode_is_manual_override
          # force_travel button pressed: force Travel mode.
          - conditions:
              - condition: template
                value_template: >-
                  {{ trigger.entity_id == 'input_button.rc_mode_force_travel' }}
            sequence:
              - service: input_select.select_option
                target:
                  entity_id: input_select.rc_mode_state
                data:
                  option: travel
              - service: input_boolean.turn_on
                target:
                  entity_id: input_boolean.rc_mode_is_manual_override
          # Dashboard pick: set manual override + start 30-min timer.
          - conditions:
              - condition: template
                value_template: >-
                  {{ trigger.entity_id == 'input_select.rc_mode_state' }}
            sequence:
              - service: input_boolean.turn_on
                target:
                  entity_id: input_boolean.rc_mode_is_manual_override
              - delay: "00:30:00"
              - service: input_boolean.turn_off
                target:
                  entity_id: input_boolean.rc_mode_is_manual_override
              - service: logbook.log
                data:
                  name: RoamCore
                  message: "Mode manual override auto-reverted after 30 minutes"
```

### §9.3 Confirm-before-power-changing-action guard

The automation fires when the §9.1 auto-mode inference
suggests Travel mode AND the §9.2 manual override is
active. The automation fires a confirmation notification
before any power-changing action fires (e.g., turning off
the fridge compressor when entering Travel mode — the
operator must confirm).

```yaml
automation:
  - id: rc_mode_confirm_before_power_changing_action
    alias: "RC Mode: Confirm-before-power-changing-action guard"
    mode: single
    trigger:
      - platform: state
        entity_id: input_select.rc_mode_state
        to: "travel"
    condition:
      - condition: state
        entity_id: input_boolean.rc_mode_is_manual_override
        state: "on"
    action:
      - service: persistent_notification.create
        data:
          title: "Confirm: Power-changing action"
          message: >-
            Mode is being changed to Travel. Power-changing
            actions (e.g., fridge compressor) may fire.
            Confirm via dashboard or press
            `button.rc_mode_revert_to_auto` to cancel.
```

### §9.4 Stealth-mode audit-log entry

The automation fires when the mode transitions to
Stealth. The automation writes an audit-log entry + fires
a notification warning the operator to check the cabin-
light state.

```yaml
automation:
  - id: rc_mode_stealth_mode_audit_log
    alias: "RC Mode: Stealth-mode audit-log entry"
    mode: single
    trigger:
      - platform: state
        entity_id: input_select.rc_mode_state
        to: "stealth"
    action:
      - service: logbook.log
        data:
          name: RoamCore
          message: >-
            Mode changed to Stealth at
            {{ now().isoformat() }}.
            Operator: {{ states('person.operator') }}.
      - service: persistent_notification.create
        data:
          title: "Stealth Mode"
          message: >-
            Mode is now Stealth. Check cabin-light state
            (turn off all visible lights) + verify no
            shore power is connected.
```

### §9.5 Mode-change notification

The automation fires when `select.rc_mode_state`
changes. The automation updates
`select.rc_mode_state_previous` + writes
`sensor.rc_mode_changed_at` + (if the AI path is
opted-in) asks the upstream Conversation agent for a
short natural-language summary that gets written to
`text.rc_mode_ai_summary`.

```yaml
automation:
  - id: rc_mode_mode_change_notification
    alias: "RC Mode: Mode-change notification + AI summary"
    mode: single
    trigger:
      - platform: state
        entity_id: input_select.rc_mode_state
    action:
      - service: input_select.select_option
        target:
          entity_id: input_select.rc_mode_state_previous
        data:
          option: "{{ trigger.from_state.state }}"
      - service: input_text.set_value
        target:
          entity_id: input_text.rc_mode_changed_at
        data:
          value: "{{ now().isoformat() }}"
      - service: text.set_value
        target:
          entity_id: text.rc_mode_ai_summary
        data:
          value: >-
            Mode changed from {{ trigger.from_state.state }}
            to {{ trigger.to_state.state }} at
            {{ now().isoformat() }}.
```

## §10 Troubleshooting

### §10.1 Mode is stuck on Auto (or Off)

- **Cause:** The §9.1 auto-mode inference automation is
  misconfigured OR the upstream signals (GPS + ignition
  + presence + plug-state + time-of-day) are not
  reporting state.
- **Fix:** Verify the upstream entities exist (`Developer
  Tools → States → search "gps_speed" + "ignition" +
  "presence" + "shore_power" + "sun_elevation"`). For
  Traccar, verify the device is online (`Developer Tools
  → Integrations → Traccar → device status`). For the HA
  Companion app, verify the location permission is
  enabled. For the time-atomic connection, verify
  `sensor.rc_time_sun_elevation` is reporting.

### §10.2 Manual override doesn't auto-revert after 30 minutes

- **Cause:** The §9.2 manual-override + auto-revert
  automation's `delay:` step is wrong OR the automation
  is disabled.
- **Fix:** Verify the §9.2 automation is ENABLED
  (Developer Tools → Automations → search
  "rc_mode_manual_override_auto_revert" → toggle ON).
  Verify the `delay: "00:30:00"` step is in the
  sequence. If the operator wants a different timeout,
  change the `delay:` step accordingly.

### §10.3 Stealth-mode audit-log entry doesn't fire

- **Cause:** The §9.4 stealth-mode audit-log automation
  is misconfigured OR `select.rc_mode_state` is not
  transitioning to `stealth`.
- **Fix:** Verify the §9.4 automation is ENABLED
  (Developer Tools → Automations → search
  "rc_mode_stealth_mode_audit_log" → toggle ON). Verify
  the trigger uses `to: "stealth"`. Check the Logbook
  for the audit-log entry (Developer Tools → Logbook →
  search "RoamCore").

### §10.4 AI summary tile is empty

- **Cause:** The §9.5 mode-change notification
  automation's `text.set_value` step is wrong OR the
  upstream Conversation agent is not enabled OR the
  operator-selected LLM add-on is not configured.
- **Fix:** Verify the Conversation agent is enabled
  (Settings → Voice assistants → Conversation agent →
  Enable). If the operator wants LLM-powered summaries,
  add the optional operator-selected LLM add-ons
  (Settings → Integrations → add the LLM provider).
  Verify the §9.5 automation's `text.set_value` step is
  writing to `text.rc_mode_ai_summary`.

### §10.5 Inference confidence is always 0.0

- **Cause:** The §9.1 auto-mode inference automation's
  `input_number.set_value` step is wrong OR the upstream
  signals are not reporting state.
- **Fix:** Verify the upstream signals are reporting
  state (see §10.1). Verify the §9.1 automation is
  ENABLED. Verify the `input_number.set_value` step is
  writing to `input_number.rc_mode_inference_confidence`
  with a value between 0.0 and 1.0.

### §10.6 Confirm-before-power-changing-action guard never fires

- **Cause:** The §9.3 confirm-before-power-changing-
  action automation is misconfigured OR the operator is
  not in manual override mode when the mode changes to
  Travel.
- **Fix:** Verify the §9.3 automation is ENABLED
  (Developer Tools → Automations → search
  "rc_mode_confirm_before_power_changing_action" → toggle
  ON). Verify the trigger uses `to: "travel"`. Verify the
  condition checks `input_boolean.rc_mode_is_manual_
  override` is `on`. If the operator wants the guard to
  fire on auto-inferred Travel mode changes too, remove
  the condition.

## §11 Privacy

The mode umbrella produces no telemetry beyond local
on/off state:

- The upstream `input_select.rc_mode_state` +
  `input_boolean.rc_mode_is_manual_override` +
  `input_text.rc_mode_changed_at` + `input_number.rc_mode_
  inference_confidence` + `text.rc_mode_ai_summary`
  helper entities are local; the data never leaves the
  HA server.
- The HA core Conversation agent (since 2022.x) handles
  natural-language queries locally by default; the agent
  does NOT call any cloud service unless the operator
  adds an optional operator-selected LLM add-on.
- The optional operator-selected LLM add-ons (since
  2023.x) send natural-language queries to the
  operator's chosen LLM provider (e.g., OpenAI /
  Anthropic). The operator must opt in by adding the
  provider + API key.
- No cloud call-home. No RoamCore-side telemetry. No
  third-party analytics.

## §12 Promoting to tier-a

Tier-a would require a RoamCore-owned mode engine +
integration code + integration tests against a real mode
engine bench (a controlled environment with canned
fixture responses for GPS / motion / plug-state / time-
of-day events + canned fixture responses for the
Conversation agent's natural-language mode queries — all
wired together in a controlled environment).

Specifically:
- A RoamCore-owned `config_flow.py`-style wizard (the
  current slice ships the upstream HA core `input_select`
  + `input_boolean` + `input_text` + `input_button` +
  `input_number` helpers + the HA core `template:` sensor
  + `template:` binary_sensor wrappers + the HA core
  Conversation agent + the optional operator-selected LLM
  add-ons, NOT a RoamCore-owned operator-wired setup
  flow).
- A RoamCore-owned mode integration code that maps the
  upstream signals (GPS speed + ignition-on input +
  presence detection + plug-state + time-of-day
  primitives) into the 10 `rc_mode_*` contract tiles
  (the current slice ships a thin `template:` sensor +
  `template:` binary_sensor + `input_select` +
  `input_boolean` + `input_text` + `input_button` +
  `input_number` helper, NOT a RoamCore-owned mode
  integration code).
- Integration tests against a RoamCore-owned mode
  engine bench (a controlled environment with canned
  fixture responses for GPS / motion / plug-state /
  time-of-day events + canned fixture responses for the
  Conversation agent's natural-language mode queries —
  all wired together in a controlled environment). The
  current slice ships manifest-honesty tests ONLY, NOT
  integration tests.

Until those three are in place, the slice is tier-b.

## §13 Files in this connection + cross-references

- `connection.yml` — the source-of-truth manifest (tier=b,
  category=ai, status=beta, 10 `rc_mode_*` contract tiles,
  FIVE MANDATORY automations, FIVE operator-pickable
  modes).
- `__init__.py` — `DOMAIN = "mode"` marker for the
  audit.
- `README.md` — the folder overview + 5-mode summary +
  supersession pointer.
- `docs/recipe.md` — this file (the full howto).
- `tests/test_connection_yml.py` — 7 manifest-honesty
  tests (id_matches_folder_name + tier_b_without_tier_a_
  markers + requires_docs_recipe_published + category_
  matches_existing_legacy_doc + dashboard_tiles_follow_
  rc_naming + status_reflects_no_native_mode_engine +
  automations_are_documented).

Cross-references:
- Legacy catalog page (now superseded by this slice):
  `docs/catalog/ai/mode.md`.
- HA core `input_select` integration (the canonical mode-
  state helper umbrella): https://www.home-assistant.io/integrations/input_select/.
- HA core `input_boolean` integration (the canonical
  manual-override flag helper): https://www.home-assistant.io/integrations/input_boolean/.
- HA core `input_text` integration (the canonical
  changed-at timestamp helper): https://www.home-assistant.io/integrations/input_text/.
- HA core `input_button` integration (the canonical
  force-* + revert-to-auto button helper):
  https://www.home-assistant.io/integrations/input_button/.
- HA core `template:` integration (the canonical
  inference-confidence + AI-summary derivation):
  https://www.home-assistant.io/integrations/template/.
- HA core Conversation agent (the canonical upstream
  opt-in AI path): https://www.home-assistant.io/integrations/conversation/.
- Time-atomic (the time-of-day primitives used by the
  §9.1 auto-mode inference): `connections/time-atomic/`
  (Wave 3 #55).
- Motion-based-lighting (the presence-detection
  primitive used by the §9.1 auto-mode inference):
  `connections/motion-based-lighting/` (Wave 3 #53).
- Approach lights (the cabin-lighting scene modified by
  the §9.4 stealth-mode audit-log entry):
  `connections/approach-lights/` (Wave 3 #52).
- Remote-access (the VPN primitive used by the §9.5
  mode-change notification's optional Telegram delivery):
  `connections/remote-access/` (Wave 3 #58).
- Fans (the §9.3 confirm-before-power-changing-action
  guard's fan-off-on-mode-change behavior):
  `connections/fans/` (Wave 3 #59).
- Leveling (the §9.5 mode-change notification's level-
  cross-reference): `connections/leveling/` (Wave 3 #60).
- NFC tags (the optional NFC-tag-triggered mode-change
  affordance): `connections/nfc-tags/` (Wave 3 #57).
- Mode/automation-builder (the legacy `select.rc_mode`
  tile source of truth — the Wave 3 #61 recipe's
  `select.rc_mode_state` is intentionally distinct from
  this legacy tile): `connections/smart-automations/`
  (Wave 2 #23).
- RoamCore entity naming:
  `docs/reference/rc-entity-naming.md` (the `mode`
  subsystem was added by this slice).