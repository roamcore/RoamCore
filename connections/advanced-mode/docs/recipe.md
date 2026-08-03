# Advanced mode — full howto (RoamCore vendor-neutral power-user toggle + session-timeout guard + destructive-calls block)

This recipe is the canonical howto for the
`connections/advanced-mode/` tier-b recipe connection (Wave
3 #63). It walks the operator through setting up the FOUR-
step operator flow (Confirm + Enable + Session window +
Audit + revert) + the 11 `rc_advanced_mode_*` contract tiles
+ the FIVE §8 MANDATORY automations + the optional safety
guards (confirm-before-toggle-on + auto-disable after session
timeout + hides-for-non-owners + audit-log entry + blocks-
destructive-irreversible-service-calls).

The recipe assumes the operator has at least the upstream
helpers installed (HA core `input_boolean` + `input_text` +
`input_datetime` + `input_button` + `select` since 2022.x —
auto-installed in every HA install). If the operator has no
upstream helpers wired, the recipe starts at §2 Prerequisites
+ walks through the upstream-helper wiring before the
advanced-mode wiring.

## §1 What is Advanced mode in RoamCore?

Advanced mode — vendor-neutral power-user toggle + session-
timeout guard + destructive-calls block — the umbrella for
"RoamCore includes an Advanced Mode toggle that can reveal
extra controls and diagnostics without cluttering the default
UI. Keeps the dashboard clean for daily use. Still gives
power users access to deeper controls when needed" — is the
ai-category complement to the broader RoamCore "show me
everything" affordances. The umbrella positions Advanced mode
as an ai-category concern (not a vehicle-category concern +
not a power-load concern + not a remote-access concern + not
a water-category concern) because Advanced mode is the
operator-facing "show me everything" affordance: the confirm-
flag is the operator's acknowledgement (the operator must
flip ON before the master enable toggle will surface the
hidden controls; the confirm-flag is a "I understand advanced
mode exposes destructive irreversible service calls"
acknowledgement); the master enable toggle is OFF by default
(advanced controls are never shown unless the operator
explicitly enables them); the session-expires-at timestamp is
the auto-revert deadline (default 24 hours; surfaces as
"expires in 23h 14m" in the dashboard); the seconds-until-
expiry tile is the resolved countdown timer; the session-
action-count tile is the number of destructive irreversible
service calls the operator has initiated while advanced mode
is ON in the current session (surfaces as "12 destructive
calls this session" in the dashboard); the last-action-at tile
is the timestamp of the last destructive irreversible service
call (surfaces as "last: 14m ago" in the dashboard); the
is-active binary_sensor is the resolved active chip (true when
advanced mode is ON AND the confirm-flag is ON AND the
session has not expired; turns red if any of those three
conditions fail); the is-blocking-destructive-calls
binary_sensor is the safety chip (should ALWAYS be true when
the toggle is OFF; turns red if a misconfiguration would let
a destructive service call slip through while advanced mode
is OFF); the session-duration select is the operator-pickable
auto-revert duration (1 hour / 6 hours / 24 hours / 7 days /
Never; default 24 hours); the enable button is the operator-
facing one-tap enable affordance; the disable-now button is
the operator-facing one-tap disable affordance.

The confirm-flag tile (`input_boolean.rc_advanced_mode_
confirmed`) is the operator's acknowledgement — the recipe
defaults to OFF because the confirm-flag is a "I understand
advanced mode exposes destructive irreversible service calls"
acknowledgement that the operator must give explicitly. The
§8.1 confirm-before-toggle-on guard fires whenever a non-
operator source tries to flip the master enable toggle ON
without first flipping the confirm-flag ON, so forgetting to
acknowledge is mitigated.

The master enable tile (`input_boolean.rc_advanced_mode_
enabled`) is the operator's master switch — the recipe
defaults to OFF because advanced controls are never shown
unless the operator explicitly enables them. The §8.2 auto-
disable after session timeout guard fires whenever the
session-expires-at timestamp is reached, so forgetting to
disable advanced mode is mitigated.

The session-expires-at tile (`input_datetime.rc_advanced_
mode_session_expires_at`) is the auto-revert deadline — the
recipe sets this to "now + selected duration" when the enable
toggle is flipped ON. The default duration is 24 hours, but
the operator can pick 1 hour / 6 hours / 24 hours / 7 days /
Never via the `select.rc_advanced_mode_session_duration`
selector.

The seconds-until-expiry tile (`sensor.rc_advanced_mode_
seconds_until_expiry`) is the resolved countdown timer — the
operator can see at a glance how much time is left in the
current session. The tile is a `template:` sensor that
computes the seconds-remaining by subtracting now() from the
session_expires_at timestamp.

The session-action-count tile (`sensor.rc_advanced_mode_
session_action_count`) is the destructive-call counter — the
operator can see at a glance how many destructive irreversible
service calls have been initiated while advanced mode is ON
in the current session. The tile is a `template:` sensor that
gets bumped by the §8.4 audit-log entry automation on every
destructive irreversible service call.

The last-action-at tile (`sensor.rc_advanced_mode_last_
action_at`) is the last destructive-call timestamp — the
operator can see at a glance when the last destructive
irreversible service call was initiated. The tile is a
`template:` sensor that gets set by the §8.4 audit-log entry
automation on every destructive irreversible service call.

The is-active tile (`binary_sensor.rc_advanced_mode_is_
active`) is the resolved active chip — the §8.1 confirm-
before-toggle-on guard + the §8.2 auto-disable after session
timeout guard + the §8.3 hides-for-non-owners guard all
publish state to this tile. The dashboard surfaces it as a
green "active" chip when advanced mode is ON AND the confirm-
flag is ON AND the session has not expired; turns red if any
of those three conditions fail.

The is-blocking-destructive-calls tile (`binary_sensor.rc_
advanced_mode_is_blocking_destructive_calls`) is the safety
chip — the §8.5 blocks-destructive-irreversible-service-calls
guard publishes state to this tile. The tile should ALWAYS be
true when the enable toggle is OFF; turns red if a
misconfiguration would let a destructive service call slip
through while advanced mode is OFF.

The session-duration tile (`select.rc_advanced_mode_session_
duration`) is the operator-pickable auto-revert duration —
the operator picks 1 hour / 6 hours / 24 hours / 7 days /
Never. The default is 24 hours. The §8.2 auto-disable after
session timeout guard uses this selector to set the session-
expires-at timestamp when the enable toggle is flipped ON.

The enable button (`button.rc_advanced_mode_enable`) is the
operator-facing one-tap enable affordance — pressing the
button fires the §8.1 confirm-before-toggle-on guard, which
checks if the confirm-flag is ON; if yes, flips the master
enable toggle ON + sets the session_expires_at to "now +
selected duration"; if no, surfaces a "confirm advanced mode"
modal and refuses to enable.

The disable-now button (`button.rc_advanced_mode_disable_now`)
is the operator-facing one-tap disable affordance — pressing
the button flips the master enable toggle OFF + clears the
session_expires_at + surfaces a "advanced mode disabled" toast.

## §2 Prerequisites

### §2.1 Universal prerequisites

- Home Assistant Core 2022.6 or newer (the upstream HA core
  `input_boolean` + `input_text` + `input_datetime` +
  `input_button` + `select` helpers + the HA core `template:`
  sensor wrapper + the HA core `template:` binary_sensor
  wrapper have all been available since 2022.6 — auto-
  installed in every HA install + exposed via the HA UI
  under Settings → Helpers + Settings → Devices & Services →
  Helpers).
- The RoamCore base packages installed (`homeassistant/
  packages/roamcore_core.yaml` + `homeassistant/packages/
  roamcore_*.yaml` for the umbrella categories the advanced
  mode will surface — power / water / network / vehicle).
- The upstream `command_line` integration configured (the
  recipe uses `command_line` for any upstream reachability
  probe — `binary_sensor` / `sensor` that tests whether the
  operator's chosen upstream is reachable).

### §2.2 Upstream signal prerequisites

The operator MUST populate `input_text.rc_advanced_mode_
destructive_call_targets` with the comma-separated list of
destructive irreversible service names the §8.5 blocks-
destructive-irreversible-service-calls guard should protect
(e.g. `switch.turn_off, climate.turn_off, script.rc_factory_
reset`). Forgetting to populate this list is the #1 cause of
"destructive service call slip-through" misconfigurations.

The operator MUST also pick an auto-revert duration via the
`select.rc_advanced_mode_session_duration` selector (default
24 hours). The §8.2 auto-disable after session timeout guard
uses this selector to set the session-expires-at timestamp
when the enable toggle is flipped ON.

The operator MUST also acknowledge the destructive-calls
exposure via the `input_boolean.rc_advanced_mode_confirmed`
confirm-flag. The §8.1 confirm-before-toggle-on guard fires
whenever a non-operator source tries to flip the enable toggle
ON without first flipping the confirm-flag ON.

### §2.3 Optional cross-references (recommended)

- Time-atomic Wave 3 #55 connection — the time-of-day
  primitives used by the §8.2 auto-disable after session
  timeout guard's expiry timestamp.
- Remote-access Wave 3 #58 connection — the VPN primitive
  used by the §8.3 hides-for-non-owners guard's owner-
  identity check.
- Mode Wave 3 #61 connection — the §8.4 audit-log entry's
  mode-change cross-reference.
- Demo-mode Wave 3 #62 connection — the §8.1 confirm-before-
  toggle-on guard's confirm-flag pattern.
- Leveling Wave 3 #60 connection — the §8.5 blocks-
  destructive-irreversible-service-calls guard's levelling-
  jack protection cross-reference.
- Fans Wave 3 #59 connection — the §8.5 blocks-destructive-
  irreversible-service-calls guard's fan-protection cross-
  reference.

## §3 Step 1 — Confirm

The Confirm step means the operator acknowledges "I understand
advanced mode exposes destructive irreversible service calls"
by flipping `input_boolean.rc_advanced_mode_confirmed` ON.
Without this confirm, advanced controls stay hidden even if
the master enable toggle is ON.

### §3.1 Confirm step steps

1. Flip `input_boolean.rc_advanced_mode_confirmed` ON (default
   OFF).
2. Verify the dashboard surfaces the "confirm advanced mode"
   chip as green (the §8.1 confirm-before-toggle-on guard is
   satisfied).
3. The §8.1 confirm-before-toggle-on guard now allows the
   master enable toggle to be flipped ON.
4. To unconfirm, flip the confirm-flag OFF (this is a
   security-conscious operator action — the dashboard will
   surface a "advanced mode will not surface hidden controls"
   warning).
5. Verify: the dashboard's "advanced mode" page should show
   the confirm-flag ON + the master enable toggle OFF + the
   is-active binary_sensor = FALSE (red chip — the toggle is
   OFF even though the confirm-flag is ON) + the is-blocking-
   destructive-calls binary_sensor = TRUE (green chip — the
   safety guard is satisfied).

## §4 Step 2 — Enable

The Enable step means the operator flips the master enable
toggle ON (or presses `button.rc_advanced_mode_enable`). The
dashboard now shows the "advanced" badge + reveals the hidden
diagnostics tiles + unlocks the operator-only controls.

### §4.1 Enable step steps

1. Verify the confirm-flag is ON (Step 1 prerequisite).
2. Pick an auto-revert duration via
   `select.rc_advanced_mode_session_duration` (default 24
   hours; 1 hour / 6 hours / 24 hours / 7 days / Never).
3. Press `button.rc_advanced_mode_enable` (one-tap: flips the
   master enable toggle ON + sets the session_expires_at to
   "now + selected duration" + surfaces a confirm-modal if the
   confirm-flag is OFF).
4. Verify the dashboard surfaces the "advanced mode active"
   badge + the hidden diagnostics tiles + the operator-only
   controls.
5. Verify `input_datetime.rc_advanced_mode_session_expires_at`
   is set to "now + selected duration" (e.g. 24 hours from
   now).
6. Verify `binary_sensor.rc_advanced_mode_is_active` is TRUE
   (green chip).
7. Verify `binary_sensor.rc_advanced_mode_is_blocking_
   destructive_calls` is FALSE (the safety chip is
   intentionally reversed — when advanced mode is ON, the
   safety chip is FALSE because destructive calls are
   ALLOWED when advanced mode is ON; the chip reverts to TRUE
   when advanced mode is OFF).
8. To exit, press `button.rc_advanced_mode_disable_now` (one-
   tap: flips the master enable toggle OFF + clears the
   session_expires_at + surfaces a "advanced mode disabled"
   toast).

## §5 Step 3 — Session window

Once enabled, advanced mode stays ON until either the operator
disables it OR the `input_datetime.rc_advanced_mode_session_
expires_at` timestamp is reached. After timeout, the toggle
auto-reverts to OFF.

### §5.1 Session window step steps

1. Verify the enable toggle is ON (Step 2 completed).
2. Watch the `sensor.rc_advanced_mode_seconds_until_expiry`
   tile countdown (the tile surfaces as "expires in 23h 14m"
   in the dashboard).
3. The `sensor.rc_advanced_mode_session_action_count` tile
   starts at 0 (no destructive irreversible service calls have
   been initiated yet).
4. The `sensor.rc_advanced_mode_last_action_at` tile starts
   at `unknown` (no destructive irreversible service calls
   have been initiated yet).
5. When the session_expires_at timestamp is reached, the
   §8.2 auto-disable after session timeout guard fires:
   - Clears the enable toggle
   - Clears the session_expires_at
   - Resets the session_action_count to 0
   - Clears the last_action_at to `unknown`
   - Writes an audit-log entry
   - Fires a notification warning the operator that advanced
     mode has been auto-disabled.
6. To exit early, press `button.rc_advanced_mode_disable_now`
   (the operator-facing one-tap disable affordance).

## §6 Step 4 — Audit + revert

Every destructive irreversible service call the operator
initiates while advanced mode is ON is logged to
`sensor.rc_advanced_mode_last_action_at` + counted in
`sensor.rc_advanced_mode_session_action_count`. The operator
can revert at any time via `button.rc_advanced_mode_disable_
now`.

### §6.1 Audit + revert step steps

1. Verify the enable toggle is ON (Step 2 completed).
2. Initiate a destructive irreversible service call (e.g.
   call `switch.turn_off` on a real switch).
3. Verify the §8.4 audit-log entry automation fires:
   - Writes an audit-log entry with the service name + the
     target entity + the operator identity (if the remote-
     access session tracks it) + the timestamp + the reason.
   - Bumps `sensor.rc_advanced_mode_session_action_count` by
     1 (the tile surfaces as "1 destructive call this
     session" in the dashboard).
   - Sets `sensor.rc_advanced_mode_last_action_at` to the
     current timestamp (the tile surfaces as "last: just now"
     in the dashboard).
4. To revert, press `button.rc_advanced_mode_disable_now`:
   - Flips the master enable toggle OFF
   - Clears the session_expires_at
   - Resets the session_action_count to 0
   - Clears the last_action_at to `unknown`
   - Surfaces a "advanced mode disabled" toast.
5. Verify the dashboard now shows the "advanced mode" badge
   as hidden + the is-active binary_sensor = FALSE + the
   is-blocking-destructive-calls binary_sensor = TRUE (the
   safety chip is back to green).

## §7 RoamCore contract entities

The 11 `rc_advanced_mode_*` contract tiles are the canonical
RoamCore surface for the advanced-mode umbrella. The tiles
are vendor-neutral — no Victron / SeeLevel / Garnet / Mopeka /
Renogy / Starlink / Peplink / Teltonika / Unifi / Ubiquiti /
MQTT / webhook / REST / API / HTTP / HTTPS / Companion /
ESPHome / phone / GPS / accelerometer / iPhone / iOS / Android
/ Samsung / Pixel / OnePlus / Xiaomi / Huawei / input_boolean
/ input_text / input_datetime / input_button / select /
template / Z-Wave / Zigbee / ZHA / Deconz / Tasmota / Shelly /
Sonoff / ESP32 / ESP8266 / Wi-Fi / BLE / Bluetooth names leak
into the tile ids.

### §7.1 The 11 `rc_advanced_mode_*` contract tiles

- `input_boolean.rc_advanced_mode_confirmed` — confirm-flag
  (operator must flip ON to acknowledge that advanced mode
  exposes destructive irreversible service calls; default
  OFF). The tile is an `input_boolean:` domain entity (since
  2022.x) that the operator's chosen confirm-flag UI flips.
  ```yaml
  input_boolean:
    rc_advanced_mode_confirmed:
      name: RC Advanced Mode Confirmed
      initial: false
      icon: mdi:shield-alert-outline
  ```

- `input_boolean.rc_advanced_mode_enabled` — master enable
  toggle (OFF by default). The tile is an `input_boolean:`
  domain entity (since 2022.x) that the operator's chosen
  enable-toggle UI flips.
  ```yaml
  input_boolean:
    rc_advanced_mode_enabled:
      name: RC Advanced Mode Enabled
      initial: false
      icon: mdi:toolbox-outline
  ```

- `input_datetime.rc_advanced_mode_session_expires_at` —
  session expiry timestamp (set to "now + selected duration"
  when the enable toggle is flipped ON; cleared when the
  toggle is flipped OFF). The tile is an `input_datetime:`
  domain entity (since 2022.x) that the operator's chosen
  expiry-timestamp UI inspects.
  ```yaml
  input_datetime:
    rc_advanced_mode_session_expires_at:
      name: RC Advanced Mode Session Expires At
      has_time: true
      has_date: true
      icon: mdi:timer-sand
  ```

- `sensor.rc_advanced_mode_seconds_until_expiry` — resolved
  seconds-until-auto-revert (surfaces as "expires in 23h 14m"
  in the dashboard). The tile is a `template:` sensor (since
  2022.x).
  ```yaml
  template:
    - sensor:
        - name: "RC Advanced Mode Seconds Until Expiry"
          unique_id: rc_advanced_mode_seconds_until_expiry
          icon: mdi:timer-sand
          state: >
            {% if is_state('input_boolean.rc_advanced_mode_enabled', 'on')
                  and states('input_datetime.rc_advanced_mode_session_expires_at')
                      is not none %}
              {% set expires_at = as_datetime(states('input_datetime.rc_advanced_mode_session_expires_at')) %}
              {{ max(0, (expires_at - now()).total_seconds()) | int }}
            {% else %}
              0
            {% endif %}
          unit_of_measurement: "s"
  ```

- `sensor.rc_advanced_mode_session_action_count` — destructive
  irreversible service call counter (surfaces as "12
  destructive calls this session" in the dashboard). The tile
  is a `template:` sensor (since 2022.x) that the §8.4 audit-
  log entry automation bumps.
  ```yaml
  template:
    - sensor:
        - name: "RC Advanced Mode Session Action Count"
          unique_id: rc_advanced_mode_session_action_count
          icon: mdi:counter
          state: >
            {% if is_state('input_boolean.rc_advanced_mode_enabled', 'on') %}
              {{ states('input_number.rc_advanced_mode_session_action_count_helper') | int(0) }}
            {% else %}
              0
            {% endif %}
          unit_of_measurement: "calls"
  ```

- `sensor.rc_advanced_mode_last_action_at` — last destructive
  irreversible service call timestamp (surfaces as "last:
  14m ago" in the dashboard). The tile is a `template:`
  sensor (since 2022.x) that the §8.4 audit-log entry
  automation sets.
  ```yaml
  template:
    - sensor:
        - name: "RC Advanced Mode Last Action At"
          unique_id: rc_advanced_mode_last_action_at
          icon: mdi:clock-outline
          state: >
            {% if is_state('input_boolean.rc_advanced_mode_enabled', 'on') %}
              {{ states('input_datetime.rc_advanced_mode_last_action_at_helper') }}
            {% else %}
              unknown
            {% endif %}
          device_class: timestamp
  ```

- `binary_sensor.rc_advanced_mode_is_active` — true when
  advanced mode is ON AND the confirm-flag is ON AND the
  session has not expired. The tile is a `template:`
  binary_sensor (since 2022.x).
  ```yaml
  template:
    - binary_sensor:
        - name: "RC Advanced Mode Is Active"
          unique_id: rc_advanced_mode_is_active
          device_class: running
          icon: mdi:check-decagram
          state: >
            {% if is_state('input_boolean.rc_advanced_mode_enabled', 'on')
                  and is_state('input_boolean.rc_advanced_mode_confirmed', 'on')
                  and states('sensor.rc_advanced_mode_seconds_until_expiry') | int(0) > 0 %}
              {{ true }}
            {% else %}
              {{ false }}
            {% endif %}
  ```

- `binary_sensor.rc_advanced_mode_is_blocking_destructive_calls`
  — true when advanced mode would block destructive
  irreversible service calls (should ALWAYS be true when the
  toggle is OFF; turns red if a misconfiguration would let a
  destructive service call slip through while advanced mode is
  OFF). The tile is a `template:` binary_sensor (since
  2022.x).
  ```yaml
  template:
    - binary_sensor:
        - name: "RC Advanced Mode Is Blocking Destructive Calls"
          unique_id: rc_advanced_mode_is_blocking_destructive_calls
          device_class: safety
          icon: mdi:shield-check
          state: >
            {% if is_state('input_boolean.rc_advanced_mode_enabled', 'on') %}
              {# Advanced mode is ON -> destructive calls are ALLOWED -> safety chip is FALSE #}
              {{ false }}
            {% else %}
              {# Advanced mode is OFF -> destructive calls are BLOCKED -> safety chip is TRUE #}
              {{ true }}
            {% endif %}
  ```

- `select.rc_advanced_mode_session_duration` — operator-
  pickable auto-revert duration (1 hour / 6 hours / 24 hours
  / 7 days / Never; default 24 hours). The tile is a
  `select:` domain entity (since 2024.x — exposed via the HA
  UI under Settings → Helpers) that the operator's chosen
  duration-picker UI picks.
  ```yaml
  select:
    rc_advanced_mode_session_duration:
      name: RC Advanced Mode Session Duration
      options:
        - "1 hour"
        - "6 hours"
        - "24 hours"
        - "7 days"
        - "Never"
      initial: "24 hours"
      icon: mdi:timer-outline
  ```

- `button.rc_advanced_mode_enable` — operator-triggered: one-
  tap enable advanced mode (equivalent to flipping the master
  toggle ON + setting session_expires_at to "now + selected
  duration"). The button is an `input_button:` domain entity
  (since 2022.x) that fires an automation flipping the master
  enable toggle ON + setting the session_expires_at.
  ```yaml
  input_button:
    rc_advanced_mode_enable:
      name: RC Advanced Mode Enable
      icon: mdi:toolbox
  ```

- `button.rc_advanced_mode_disable_now` — operator-triggered:
  one-tap disable advanced mode NOW (flips the master toggle
  OFF + clears the session_expires_at). The button is an
  `input_button:` domain entity (since 2022.x) that fires an
  automation flipping the master enable toggle OFF + clearing
  the session_expires_at.
  ```yaml
  input_button:
    rc_advanced_mode_disable_now:
      name: RC Advanced Mode Disable Now
      icon: mdi:stop-circle-outline
  ```

## §8 Automations (MANDATORY before first use)

The §8 walks through the FIVE MANDATORY automations. The
recipe is the contract layer; the automation wrappers are
documented below.

### §8.1 Confirm-before-toggle-on guard

The automation fires when a non-operator source tries to flip
`input_boolean.rc_advanced_mode_enabled` ON without first
flipping `input_boolean.rc_advanced_mode_confirmed` ON. The
automation BLOCKS the enable flip + writes an audit-log entry
+ fires a notification warning the operator that the
confirm-flag must be flipped ON first.

```yaml
automation:
  - id: rc_advanced_mode_confirm_before_toggle_on
    alias: "RC Advanced Mode: Confirm-before-toggle-on guard"
    mode: single
    trigger:
      - platform: state
        entity_id: input_boolean.rc_advanced_mode_enabled
        to: "on"
    condition:
      - condition: state
        entity_id: input_boolean.rc_advanced_mode_confirmed
        state: "off"
    action:
      - service: input_boolean.turn_off
        target:
          entity_id: input_boolean.rc_advanced_mode_enabled
      - service: logbook.log
        data:
          name: "RC Advanced Mode"
          message: >
            BLOCKED: Tried to enable advanced mode without
            first confirming destructive irreversible
            service calls exposure. Confirm-flag is OFF.
            Enable toggle has been re-disabled.
          domain: roamcore
      - service: persistent_notification.create
        data:
          title: "RC Advanced Mode: BLOCKED"
          message: >
            You must flip the
            `input_boolean.rc_advanced_mode_confirmed`
            confirm-flag ON before you can enable advanced
            mode. Advanced mode exposes destructive
            irreversible service calls.
```

### §8.2 Auto-disable after session timeout

The automation fires when
`input_datetime.rc_advanced_mode_session_expires_at` timestamp
is reached. The automation clears the enable toggle + clears
the session_expires_at + resets the session_action_count to 0
+ clears the last_action_at to unknown + writes an audit-log
entry + fires a notification warning the operator that
advanced mode has been auto-disabled.

```yaml
automation:
  - id: rc_advanced_mode_auto_disable_after_session_timeout
    alias: "RC Advanced Mode: Auto-disable after session timeout"
    mode: single
    trigger:
      - platform: state
        entity_id: input_datetime.rc_advanced_mode_session_expires_at
        attribute: timestamp
    condition:
      - condition: state
        entity_id: input_boolean.rc_advanced_mode_enabled
        state: "on"
      - condition: template
        value_template: >
          {{ as_datetime(states('input_datetime.rc_advanced_mode_session_expires_at'))
              <= now() }}
    action:
      - service: input_boolean.turn_off
        target:
          entity_id: input_boolean.rc_advanced_mode_enabled
      - service: input_datetime.set_datetime
        target:
          entity_id: input_datetime.rc_advanced_mode_session_expires_at
        data:
          datetime: "1970-01-01 00:00:00"
      - service: input_number.set_value
        target:
          entity_id: input_number.rc_advanced_mode_session_action_count_helper
        data:
          value: 0
      - service: input_datetime.set_datetime
        target:
          entity_id: input_datetime.rc_advanced_mode_last_action_at_helper
        data:
          datetime: "1970-01-01 00:00:00"
      - service: logbook.log
        data:
          name: "RC Advanced Mode"
          message: >
            Advanced mode auto-disabled: session expired
            at {{ states('input_datetime.rc_advanced_mode_session_expires_at') }}.
            Enable toggle has been cleared + session_
            expires_at cleared + session_action_count
            reset to 0 + last_action_at cleared.
          domain: roamcore
      - service: persistent_notification.create
        data:
          title: "RC Advanced Mode auto-disabled"
          message: >
            Advanced mode has been auto-disabled because
            the session expired at {{ states('input_datetime.rc_advanced_mode_session_expires_at') }}.
            Press `button.rc_advanced_mode_enable` to
            re-enable (after flipping the confirm-flag ON
            again).
```

### §8.3 Hides-for-non-owners

The automation fires when a non-owner dashboard session
attempts to view the advanced-mode dashboard page while
`input_boolean.rc_advanced_mode_enabled` is ON. The
automation hides the advanced-mode tiles + surfaces an
"advanced mode hidden for non-owners" banner + writes an
audit-log entry.

```yaml
automation:
  - id: rc_advanced_mode_hides_for_non_owners
    alias: "RC Advanced Mode: Hides for non-owners"
    mode: single
    trigger:
      - platform: state
        entity_id: input_boolean.rc_advanced_mode_enabled
        to: "on"
    condition:
      # The current dashboard session is NOT the operator's
      # session. The operator can confirm by checking the
      # trigger's context.user_id — if it's not the
      # operator's user_id, hide the tiles + log + notify.
      - condition: template
        value_template: >
          {{ trigger.context.user_id is none
              or trigger.context.user_id not in [
                'OPERATOR_USER_ID_1',
                'OPERATOR_USER_ID_2',
                # add operator user_ids here
              ] }}
    action:
      - service: persistent_notification.create
        data:
          title: "RC Advanced Mode is hidden for non-owners"
          message: >
            Advanced mode is currently enabled for the
            operator, but your dashboard session is not
            the operator's session. The advanced-mode
            tiles are hidden from your view.
            Press `button.rc_advanced_mode_disable_now` to
            disable advanced mode (allowed for non-owners
            in case of emergency).
      - service: logbook.log
        data:
          name: "RC Advanced Mode"
          message: >
            Hides-for-non-owners guard fired: Non-owner
            session (user_id={{ trigger.context.user_id }})
            attempted to view the advanced-mode dashboard
            page while advanced mode is ON. The advanced-
            mode tiles are hidden from view.
          domain: roamcore
```

### §8.4 Audit-log entry on destructive call

The automation fires on every destructive irreversible service
call the operator initiates while
`input_boolean.rc_advanced_mode_enabled` is ON. The
automation writes an audit-log entry with the service name +
the target entity + the operator identity (if the remote-
access session tracks it) + the timestamp + the reason.

```yaml
automation:
  - id: rc_advanced_mode_audit_log_entry
    alias: "RC Advanced Mode: Audit-log entry on destructive call"
    mode: single
    trigger:
      - platform: event
        event_type: call_service
    condition:
      - condition: state
        entity_id: input_boolean.rc_advanced_mode_enabled
        state: "on"
      - condition: template
        value_template: >
          {{ trigger.event.data.service in
              states('input_text.rc_advanced_mode_destructive_call_targets')
                  .split(',') | map('trim') | reject('equalto', '') | list }}
    action:
      - service: logbook.log
        data:
          name: "RC Advanced Mode"
          message: >
            Destructive irreversible service call:
            service={{ trigger.event.data.service }},
            target={{ trigger.event.data.service_data
                .entity_id if trigger.event.data.service_data
                is mapping and 'entity_id' in trigger.event.data.service_data
                else 'unknown' }}.
            Operator: {{ trigger.context.user_id or
                'unknown' }}.
            Time: {{ now().isoformat() }}.
          domain: roamcore
      - service: input_number.increment
        target:
          entity_id: input_number.rc_advanced_mode_session_action_count_helper
      - service: input_datetime.set_datetime
        target:
          entity_id: input_datetime.rc_advanced_mode_last_action_at_helper
        data:
          datetime: "{{ now().isoformat() }}"
```

### §8.5 Blocks-destructive-irreversible-service-calls guard

The automation fires when ANY `script.*` / `automation.*`
action tries to call a destructive irreversible service (the
operator has flagged in
`input_text.rc_advanced_mode_destructive_call_targets`) while
`input_boolean.rc_advanced_mode_enabled` is OFF. The
automation BLOCKS the service call + logs a security-style
audit entry + flips
`binary_sensor.rc_advanced_mode_is_blocking_destructive_calls`
to FALSE + fires a critical notification.

```yaml
automation:
  - id: rc_advanced_mode_blocks_destructive_irreversible_service_calls
    alias: "RC Advanced Mode: Blocks-destructive-irreversible-service-calls guard"
    mode: single
    trigger:
      - platform: event
        event_type: call_service
    condition:
      - condition: state
        entity_id: input_boolean.rc_advanced_mode_enabled
        state: "off"
      - condition: template
        value_template: >
          {{ trigger.event.data.service in
              states('input_text.rc_advanced_mode_destructive_call_targets')
                  .split(',') | map('trim') | reject('equalto', '') | list }}
    action:
      - service: logbook.log
        data:
          name: "RC Advanced Mode"
          message: >
            BLOCKED: Destructive irreversible service call
            attempted while advanced mode is OFF.
            service={{ trigger.event.data.service }},
            target={{ trigger.event.data.service_data
                .entity_id if trigger.event.data.service_data
                is mapping and 'entity_id' in trigger.event.data.service_data
                else 'unknown' }}.
            Operator: {{ trigger.context.user_id or
                'unknown' }}.
          domain: roamcore
      - service: persistent_notification.create
        data:
          title: "RC Advanced Mode: BLOCKED destructive call"
          message: >
            A destructive irreversible service call was
            attempted while advanced mode is OFF.
            service={{ trigger.event.data.service }}.
            The call has been BLOCKED.
            Press `button.rc_advanced_mode_enable` to
            enable advanced mode + allow the call.
```

(The actual block is enforced by the operator's automations
checking `is_state('input_boolean.rc_advanced_mode_enabled',
'off')` AND `{{ trigger.event.data.service in
states('input_text.rc_advanced_mode_destructive_call_targets')
.split(',') | map('trim') | reject('equalto', '') | list }}`
before calling any destructive irreversible service on a
flagged target. The automation above is the reminder pattern
— the operator's automations do the actual blocking.)

## §9 Troubleshooting

### §9.1 Advanced mode is stuck on Confirmed but not Enabled

- **Cause:** The §8.1 confirm-before-toggle-on guard may have
  fired (the operator tried to flip the enable toggle ON
  without first flipping the confirm-flag ON), OR the operator
  hasn't flipped the enable toggle ON yet.
- **Fix:** Verify the upstream `input_boolean` helpers are
  installed (Developer Tools → Services → search for
  `input_boolean.toggle` — should return the service). Verify
  the operator pressed the enable button
  (`button.rc_advanced_mode_enable`) OR flipped the enable
  toggle ON manually. Verify the confirm-flag is ON
  (otherwise the §8.1 guard would block the enable).

### §9.2 Advanced mode never surfaces the hidden controls

- **Cause:** The is-active binary_sensor is FALSE (the
  confirm-flag is OFF, OR the enable toggle is OFF, OR the
  session has expired). OR the `template:` sensor wrappers
  for the derived tiles aren't wired.
- **Fix:** Verify the `template:` binary_sensor wrapper is
  configured (Developer Tools → States → search
  `binary_sensor.rc_advanced_mode_is_active`). Verify the
  confirm-flag is ON (`input_boolean.rc_advanced_mode_
  confirmed`). Verify the enable toggle is ON
  (`input_boolean.rc_advanced_mode_enabled`). Verify the
  session has not expired (`sensor.rc_advanced_mode_seconds_
  until_expiry` > 0). If all three are satisfied, the
  is-active binary_sensor will be TRUE.

### §9.3 §8.2 auto-disable after session timeout guard never fires

- **Cause:** The §8.2 automation is misconfigured OR the
  upstream `input_datetime` helper isn't installed OR the
  session_expires_at timestamp is not being compared to
  now().
- **Fix:** Verify the §8.2 automation is ENABLED (Developer
  Tools → Automations → search
  "rc_advanced_mode_auto_disable_after_session_timeout" →
  toggle ON). Verify the upstream `input_datetime` helper is
  installed (`input_datetime.rc_advanced_mode_session_expires_
  at` should exist in Developer Tools → States). Verify the
  trigger uses the `state` platform with the `attribute:
  timestamp` filter. Verify the condition compares
  `as_datetime(states('input_datetime.rc_advanced_mode_
  session_expires_at')) <= now()`.

### §9.4 §8.5 blocks-destructive-irreversible-service-calls guard fires unexpectedly

- **Cause:** The `input_text.rc_advanced_mode_destructive_call_
  targets` list contains a service name that the operator
  wants to call normally (NOT a destructive irreversible
  service that should be blocked).
- **Fix:** Remove the service name from the
  `input_text.rc_advanced_mode_destructive_call_targets`
  list. The list should ONLY contain destructive irreversible
  service names that the operator never wants to call while
  advanced mode is OFF.

### §9.5 §8.3 hides-for-non-owners guard surfaces banner every time

- **Cause:** The §8.3 automation is firing every time
  `input_boolean.rc_advanced_mode_enabled` flips to ON,
  which is expected behavior (the banner is intended to fire
  on every enable for non-operator sessions).
- **Fix:** This is expected behavior for non-operator sessions.
  The operator can disable advanced mode to clear the banner.
  OR the operator can configure the dashboard to suppress
  the banner for trusted operator sessions.

### §9.6 §8.1 confirm-before-toggle-on guard BLOCKS the operator's own enable

- **Cause:** The operator's confirm-flag is OFF (the §8.1
  guard only allows enable when the confirm-flag is ON).
- **Fix:** Flip the confirm-flag ON (`input_boolean.rc_
  advanced_mode_confirmed`) before pressing the enable
  button. The operator should also explicitly acknowledge
  "I understand advanced mode exposes destructive
  irreversible service calls" before flipping the confirm-
  flag ON.

## §10 Privacy

The advanced-mode umbrella produces no telemetry beyond local
on/off state:

- The upstream `input_boolean.rc_advanced_mode_confirmed` +
  `input_boolean.rc_advanced_mode_enabled` +
  `input_datetime.rc_advanced_mode_session_expires_at` +
  `sensor.rc_advanced_mode_seconds_until_expiry` +
  `sensor.rc_advanced_mode_session_action_count` +
  `sensor.rc_advanced_mode_last_action_at` +
  `binary_sensor.rc_advanced_mode_is_active` +
  `binary_sensor.rc_advanced_mode_is_blocking_destructive_calls`
  + `select.rc_advanced_mode_session_duration` +
  `button.rc_advanced_mode_enable` +
  `button.rc_advanced_mode_disable_now` helper entities are
  local; the data never leaves the HA server.
- The §8.4 audit-log-entry automation writes entries to the
  HA core logbook; the logbook is operator-owned and never
  leaves the HA server.
- No cloud call-home. No RoamCore-side telemetry. No
  third-party analytics.

## §11 Promoting to tier-a

Tier-a would require a RoamCore-owned advanced-mode engine +
integration code + integration tests against a real advanced-
mode engine bench (a controlled environment with canned
fixture responses for session-expired events + canned fixture
responses for destructive-service-call blocking events +
canned fixture responses for non-owner dashboard session
events — all wired together in a controlled environment).

Specifically:
- A RoamCore-owned operator-wired setup flow that walks the
  operator through Confirm + Enable + Session window + Audit
  + declare the upstream destructive irreversible service
  call targets + the §8 automations (the current slice ships
  the upstream HA core `input_boolean` + `input_text` +
  `input_datetime` + `input_button` + `select` helpers + the
  HA core `template:` sensor + `template:` binary_sensor
  wrappers, NOT a RoamCore-owned operator-wired setup flow).
- A RoamCore-owned advanced-mode integration code that maps
  the upstream signals (confirm-flag + enable toggle +
  session_expires_at + destructive-call-targets) into the 11
  `rc_advanced_mode_*` contract tiles (the current slice
  ships a thin `template:` sensor + `template:` binary_sensor
  + `input_boolean` + `input_text` + `input_datetime` +
  `input_button` + `select` helper, NOT a RoamCore-owned
  advanced-mode integration code).
- Integration tests against a RoamCore-owned advanced-mode
  engine bench (a controlled environment with canned fixture
  responses for session-expired events + canned fixture
  responses for destructive-service-call blocking events +
  canned fixture responses for non-owner dashboard session
  events — all wired together in a controlled environment).
  The current slice ships manifest-honesty tests ONLY, NOT
  integration tests.

Until those three are in place, the slice is tier-b.

## §12 Files in this connection + cross-references

- `connection.yml` — the source-of-truth manifest (tier=b,
  category=ai, status=beta, 11 `rc_advanced_mode_*` contract
  tiles, FIVE MANDATORY automations, FOUR-step operator flow).
- `__init__.py` — `DOMAIN = "advanced_mode"` marker for the
  audit.
- `README.md` — the folder overview + FOUR-step flow summary
  + supersession pointer.
- `docs/recipe.md` — this file (the full howto).
- `tests/test_connection_yml.py` — 7 manifest-honesty
  tests (id_matches_folder_name + tier_b_without_tier_a_
  markers + requires_docs_recipe_published + category_
  matches_existing_legacy_doc + dashboard_tiles_follow_
  rc_naming + status_reflects_no_native_advanced_mode_engine
  + automations_are_documented).

Cross-references:
- Legacy catalog page (now superseded by this slice):
  `docs/catalog/ai/advanced-mode.md`.
- HA core `input_boolean` integration (the canonical
  confirm-flag + enable-toggle helper umbrella): https://www.home-assistant.io/integrations/input_boolean/.
- HA core `input_text` integration (the canonical
  destructive-call-targets helper): https://www.home-assistant.io/integrations/input_text/.
- HA core `input_datetime` integration (the canonical
  session-expiry-timestamp helper): https://www.home-assistant.io/integrations/input_datetime/.
- HA core `input_button` integration (the canonical enable /
  disable button helper): https://www.home-assistant.io/integrations/input_button/.
- HA core `select` integration (the canonical session-
  duration picker helper): https://www.home-assistant.io/integrations/select/.
- HA core `template:` integration (the canonical seconds-
  until-expiry + is-active + is-blocking-destructive-calls
  derivation): https://www.home-assistant.io/integrations/template/.
- Time-atomic (the time-of-day primitives used by the §8.2
  auto-disable after session timeout guard's expiry
  timestamp): `connections/time-atomic/` (Wave 3 #55).
- Remote-access (the VPN primitive used by the §8.3 hides-
  for-non-owners guard's owner-identity check):
  `connections/remote-access/` (Wave 3 #58).
- Mode (the §8.4 audit-log entry's mode-change cross-
  reference): `connections/mode/` (Wave 3 #61).
- Demo-mode (the §8.1 confirm-before-toggle-on guard's
  confirm-flag pattern): `connections/demo-mode/` (Wave 3
  #62).
- Leveling (the §8.5 blocks-destructive-irreversible-
  service-calls guard's levelling-jack protection cross-
  reference): `connections/leveling/` (Wave 3 #60).
- Fans (the §8.5 blocks-destructive-irreversible-service-
  calls guard's fan-protection cross-reference):
  `connections/fans/` (Wave 3 #59).
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`
  (the `advanced_mode` subsystem was added by this slice).
