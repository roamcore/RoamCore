# NFC tags — tier-c recipe connection

This is the full howto for the `connections/nfc-tags/` tier-c recipe
connection. It walks through installing the upstream HA core `tag`
integration (since 2022.x — exposes scanned NFC tag IDs as
`tag.last_scanned` + persistence via the core `tag` registry + a
`tag_scanned` event fired on every scan), wiring ONE OR MORE NFC
readers (Path A phone-as-NFC-reader via the HA Companion app + Path B
USB NFC reader via the HACS `nfcpy` integration + Path C HA Companion
app `tag` trigger as an implicit Path A), adding a thin RoamCore
automation wrapper that maintains the `tag_id → scene` mapping table
+ runs the THREE §7 automations (last-tag-triggered scene + tag-unknown
warning + Stealth-mode suppression), mapping the upstream NFC tag scan
events into the 8 `rc_nfc_*` contract tiles, and promoting the
connection to tier-b when the bench fixture lands.

## §1 What are NFC tags in RoamCore?

NFC tags (vendor-neutral NFC-triggered scenes mapped via
`tag_id → scene` mapping) — the umbrella for "cheap + simple NFC
tags make the van feel magical: tap your phone to run a scene (Lights
off, Bedtime, Leave camp)" — is positioned in RoamCore as:

- A **reuse-first** recipe over upstream HA core's `tag` integration.
  RoamCore does NOT maintain its own NFC integration; HA core's `tag`
  integration (since 2022.x) is the canonical NFC tag scan event
  source. This is intentional: writing a custom NFC tag reader would
  duplicate work HA core already does well + introduce maintenance
  burden (the HACS `nfcpy` integration upstream tracks upstream
  changes + writing a custom NFC reader would also require a custom
  USB NFC reader driver + a custom HA-Companion-app-NFC scan event
  forwarder).

- A **vendor-neutral** contract layer over the upstream HA core
  `tag` integration + the HA Companion app's `tag` trigger + the
  HACS `nfcpy` integration + the HA core `scene` integration. The
  contract talks to whatever NFC reader the operator wires (HA
  Companion app NFC / HACS `nfcpy` USB NFC reader / any combination
  thereof), not to any specific vendor's NFC reader hardware.

- A **three-path** wrapper. The operator picks ONE OR MORE of:
  - Path A — Phone-as-NFC-reader via the HA Companion app.
  - Path B — USB NFC reader via the HACS `nfcpy` integration.
  - Path C — Implicit Path A via the HA Companion app's `tag` trigger.

- A **single "what scene did the last NFC tag trigger?" tile** that
  aggregates the most recent `tag_scanned` event into one dashboard
  indicator. The `sensor.rc_nfc_last_triggered_scene` tile is the
  day-1 aggregate (reports the scene name mapped to the most recent
  scanned `tag_id`; useful for "what did the NFC tag just do?"); the
  `binary_sensor.rc_nfc_last_triggered_scene_active` is the
  scratchpad state (TRUE while the triggered scene is still in its
  active state).

- A **freshness-aware** system. The `sensor.rc_nfc_last_scan_minutes_
  ago` sensor is the freshness gate (helpful for "when did the
  operator last interact with the van?"). The
  `sensor.rc_nfc_last_scanned_tag_id` sensor surfaces the most recent
  scanned tag ID — useful for the operator's "what did I just scan?"
  debugging affordance.

- A **coverage-aware** system. The
  `sensor.rc_nfc_registered_tags_count` tile surfaces how many NFC
  tags are registered in HA's tag registry — useful for the
  operator's "did I add the new tag I bought?" debugging affordance.

- A **Stealth-mode-aware** system. The
  `binary_sensor.rc_nfc_stealth_mode_suppressed` tile surfaces
  whether the mode/automation-builder recipe's `select.rc_mode` tile
  is currently suppressing NFC-triggered scenes (campgrounds with
  quiet hours + overnight stays where running a scene would disturb
  other campers). The recipe §7.3 walks through the Stealth-mode
  suppression automation.

- A **tag-unknown-warning** system. The
  `binary_sensor.rc_nfc_tag_unknown_warning` tile surfaces whether
  the last scanned tag was unknown (the `tag_id` is NOT in the
  RoamCore `tag_id → scene` mapping table). The recipe §7.2 walks
  through the tag-unknown warning automation.

- A **manual-override** system. The `button.rc_nfc_trigger_scene_now`
  button surfaces the manual override (operator can trigger the last-
  tag-triggered scene without re-scanning the tag — useful for the
  "I just want the lights off" affordance, or for triggering the
  scene from the dashboard without walking to the NFC tag).

## §2 Prerequisites

NFC tag — at least ONE of the following (the recipe recommends starting
with one + adding more as the operator finds natural places to use
them):

- **NTAG215 / NTAG216 NFC sticker tags** — the cheapest + most widely
  available + the HA Companion app + the HACS `nfcpy` integration
  both support them out of the box. Recommended for the operator's
  first NFC tag set.
- **Mifare Classic 1K NFC sticker tags** — slightly more expensive
  but more durable; the HA Companion app + the HACS `nfcpy`
  integration both support them.
- **Mifare Ultralight NFC sticker tags** — the cheapest option; the
  HA Companion app + the HACS `nfcpy` integration both support them
  but the storage capacity is smaller (so the tag IDs are shorter).

NFC reader — at least ONE of the following (the recipe recommends
starting with Path A + adding Path B as the operator's second
choice):

- **Path A — Phone-as-NFC-reader via the HA Companion app.** The
  operator needs a modern Android phone with NFC built in (most
  Android phones since 2018 support NFC). The HA Companion app must
  be installed + the NFC sensor must be enabled in the app (Settings
  → Companion app → Sensors → NFC tag sensor).
- **Path B — USB NFC reader via the HACS `nfcpy` integration.** The
  operator needs a USB NFC reader (ACR122U / PN532 / SonMicro /
  Identiv — all commercially available + well-supported by the HACS
  `nfcpy` integration). The HACS `nfcpy` integration must be
  installed (Home Assistant Community Store — HACS).
- **Path C — Implicit Path A via the HA Companion app's `tag`
  trigger.** Functionally identical to Path A; the recipe treats Path
  C as the "implicit" Path A (the operator does NOT need to install
  a separate NFC reader; the phone IS the NFC reader).

Upstream HA core `tag` integration (since 2022.x) — installed by
default in Home Assistant since 2022.x. The `tag` integration is a
core integration that ships with Home Assistant; no separate install
is required. The integration exposes the `tag_scanned` event +
`tag.last_scanned` entity + `tag.list` service.

HA core `scene` integration (since 2022.x) — installed by default in
Home Assistant since 2022.x. The `scene` integration is a core
integration that ships with Home Assistant; no separate install is
required. The integration exposes the operator's `scene.*` entities.

HA core `automation` UI editor (since 2022.x) — built into Home
Assistant since 2022.x. The `automation` UI editor exposes a GUI flow
for the operator to create an automation with a `tag` trigger.

Mode/automation-builder recipe (Wave 2 #23) — the `select.rc_mode`
tile is the source of truth for the §7.3 Stealth-mode suppression.
The recipe assumes the operator has already wired the
mode/automation-builder recipe (the `select.rc_mode` tile with the
following options: `home` / `away` / `stealth` / `sleep`).

Optional: Approach lights (Wave 3 #52) — the canonical "Lights off"
/ "Welcome home" scene entities. The recipe §3.4 walks the operator
through wiring the `tag_id → scene` mapping table; the scene
entities from the approach-lights slice can be used as the
`tag_id → scene` mapping's scene targets.

Optional: HVAC basics (Wave 3 #49) — the canonical "Bedtime" /
"Climate" scene entities. The recipe §3.4 walks the operator
through wiring the `tag_id → scene` mapping table; the scene
entities from the hvac-basics slice can be used as the
`tag_id → scene` mapping's scene targets.

## §3 Path A — Phone-as-NFC-reader via the HA Companion app

Path A is the default for any van operator who has a modern Android
phone with NFC built in (most Android phones since 2018 support
NFC). The HA Companion app exposes a `tag_scanned` event in HA
core since 2022.x when the operator taps an NFC tag to the phone.

**Step A.1 — Install the HA Companion app on the operator's phone.**

The operator installs the HA Companion app from the Google Play store
on their Android phone. The app is free + open-source.

**Step A.2 — Connect the HA Companion app to the operator's HA
instance.**

The operator configures the HA Companion app to connect to their HA
instance (Settings → Companion app → Home Assistant URL). The app
authenticates with the operator's HA instance via a long-lived access
token (created in the HA profile page).

**Step A.3 — Enable NFC scans on the phone.**

The operator enables the NFC sensor in the HA Companion app
(Settings → Companion app → Sensors → NFC tag sensor). The app
exposes a `tag_scanned` event in HA core since 2022.x when the
operator taps an NFC tag to the phone.

**Step A.4 — Test the NFC scan.**

The operator taps an NFC tag to the phone. The HA Companion app
detects the NFC tag + fires a `tag_scanned` event in HA core.
The operator can verify the event by checking the HA logbook
(Developer tools → Events → Listen for `tag_scanned` events).

**Step A.5 — Register the NFC tag in HA's tag registry.**

The operator registers the NFC tag in HA's tag registry
(Settings → Devices & Services → Tags → Add tag — paste the tag's
unique ID + give it a friendly name). The tag's unique ID is the
NFC tag's serial number (a long hexadecimal string like
`04:a3:2b:8c:1d:9e:5f:6a:80`).

**Step A.6 — Create the operator's scenes in HA's scene registry.**

The operator creates the scenes in HA's scene registry
(Settings → Devices & Services → Scenes → Add scene). Each scene
is a collection of entity states (e.g. the "Lights off" scene turns
off all HASS `light.*` entities + the "Bedtime" scene lowers the
thermostat + turns off all HASS `light.*` entities except the
bedside reading lamp + the "Leave camp" scene turns off all HASS
`light.*` entities + locks the deadbolts + activates the Stealth
mode).

**Step A.7 — Wire the §7.1 last-tag-triggered scene automation.**

The §7.1 last-tag-triggered scene automation is the operator's
`tag_id → scene` mapping table. The automation fires when a
`tag_scanned` event is received AND matches a known `tag_id` in the
mapping table AND then calls `scene.turn_on` on the mapped scene.

```yaml
# homeassistant/automations/nfc_tag_to_scene.yaml
- alias: "NFC: tag_id → scene"
  description: >
    The §7.1 last-tag-triggered scene automation. When a
    `tag_scanned` event is received, the automation checks the
    known `tag_id → scene` mapping table + calls `scene.turn_on`
    on the mapped scene. The mapping table is the operator's
    single source of truth for which tag fires which scene.
  mode: single
  trigger:
    - platform: event
      event_type: tag_scanned
  condition: []
  action:
    - choose:
        # Lights off scene
        - conditions:
            - condition: template
              value_template: >
                {{ trigger.event.data.tag_id == 'tag_lights_off' }}
          sequence:
            - service: scene.turn_on
              target:
                entity_id: scene.lights_off
        # Bedtime scene
        - conditions:
            - condition: template
              value_template: >
                {{ trigger.event.data.tag_id == 'tag_bedtime' }}
          sequence:
            - service: scene.turn_on
              target:
                entity_id: scene.bedtime
        # Leave camp scene
        - conditions:
            - condition: template
              value_template: >
                {{ trigger.event.data.tag_id == 'tag_leave_camp' }}
          sequence:
            - service: scene.turn_on
              target:
                entity_id: scene.leave_camp
        # Welcome home scene
        - conditions:
            - condition: template
              value_template: >
                {{ trigger.event.data.tag_id == 'tag_welcome_home' }}
          sequence:
            - service: scene.turn_on
              target:
                entity_id: scene.welcome_home
```

## §4 Path B — USB NFC reader via the HACS `nfcpy` integration

Path B is the default for vans where the operator does NOT have an
Android phone with NFC (e.g. the operator uses an iPhone, which
does NOT expose an NFC scan event to HA directly) OR for vans where
the operator wants a SINGLE shared NFC reader that everyone in the
van can use (no per-phone pairing required).

**Step B.1 — Plug the USB NFC reader into the HA server.**

The operator plugs the USB NFC reader (ACR122U / PN532 / SonMicro
/ Identiv) into a USB port on the HA server (the HA VM running on
Proxmox). The USB device is auto-detected by the underlying Linux
kernel.

**Step B.2 — Install the HACS `nfcpy` integration.**

The operator installs the HACS `nfcpy` integration from the HACS
default repository (HACS → Integrations → Explore & Add Repositories
→ Search "nfcpy" → Install). The HACS `nfcpy` integration exposes a
GUI flow for the operator to wire the USB NFC reader into HA.

**Step B.3 — Configure the HACS `nfcpy` integration.**

The operator configures the HACS `nfcpy` integration (Settings →
Devices & Services → Integrations → nfcpy → Configure). The
integration detects the USB NFC reader + forwards the NFC tag ID to
HA as a `tag_scanned` event.

**Step B.4 — Test the NFC scan.**

The operator taps an NFC tag to the USB NFC reader. The HACS
`nfcpy` integration detects the NFC tag + fires a `tag_scanned`
event in HA core. The operator can verify the event by checking the
HA logbook (Developer tools → Events → Listen for `tag_scanned`
events).

**Step B.5 — Register the NFC tag in HA's tag registry.**

Same as Step A.5 above (the operator registers the NFC tag in HA's
tag registry).

**Step B.6 — Create the operator's scenes in HA's scene registry.**

Same as Step A.6 above (the operator creates the scenes in HA's
scene registry).

**Step B.7 — Wire the §7.1 last-tag-triggered scene automation.**

Same as Step A.7 above (the operator wires the `tag_id → scene`
mapping table).

## §5 Path C — Implicit Path A via the HA Companion app's `tag` trigger

Path C is functionally identical to Path A (the HA Companion app is
the phone-side NFC reader); the recipe treats Path C as the
"implicit" Path A (the operator does NOT need to install a separate
NFC reader; the phone IS the NFC reader).

**Step C.1 — Install the HA Companion app on the operator's phone.**

Same as Step A.1 above.

**Step C.2 — Connect the HA Companion app to the operator's HA
instance.**

Same as Step A.2 above.

**Step C.3 — Enable the HA Companion app's `tag` trigger.**

The operator enables the HA Companion app's `tag` trigger in HA
(Developer tools → Events → tag_scanned). The HA Companion app's
`tag` trigger fires a `tag_scanned` event in HA when the operator
scans an NFC tag with the phone.

**Step C.4 — Test the NFC scan.**

Same as Step A.4 above.

**Step C.5 — Register the NFC tag in HA's tag registry.**

Same as Step A.5 above.

**Step C.6 — Create the operator's scenes in HA's scene registry.**

Same as Step A.6 above.

**Step C.7 — Wire the §7.1 last-tag-triggered scene automation.**

Same as Step A.7 above.

## §6 RoamCore contract entities

The NFC tags contract layer exposes the 8 `rc_nfc_*` contract tiles
that the dashboard + OpenClaw queries use. The contract is
implementation-agnostic: it talks to whatever NFC reader the
operator wires (HA Companion app NFC / HACS `nfcpy` USB NFC reader
/ any combination thereof), not to any specific vendor's NFC reader
hardware.

- `sensor.rc_nfc_last_triggered_scene` — the scene name mapped to
  the most recent scanned `tag_id` (e.g. "Lights off" / "Bedtime" /
  "Leave camp" / "Welcome home" / "Unknown"). The
  `last_triggered_scene` is the canonical "what did the NFC tag
  just do?" affordance. Maps from the operator's `tag_id → scene`
  mapping table (the §7.1 automation's `choose:` block).
  Implementation: HA core `template:` sensor deriving the scene
  name from the most recent `tag_scanned` event's `tag_id` against
  the operator's `tag_id → scene` mapping table.

- `binary_sensor.rc_nfc_last_triggered_scene_active` — the scratchpad
  state (TRUE while the triggered scene is still in its active
  state). The `last_triggered_scene_active` is the canonical "is
  the triggered scene still doing its thing?" affordance. Maps from
  the `state` attribute of the `script.last_triggered_scene` script
  + the `last_triggered` attribute of the operator's `scene.*`
  entity. Implementation: HA core `template:` binary_sensor
  deriving the active state from the operator's `scene.*` entity's
  `last_triggered` attribute.

- `sensor.rc_nfc_registered_tags_count` — the number of NFC tags
  registered in HA's tag registry (e.g. "4" / "10" / "23"). The
  `registered_tags_count` is the canonical "how many tags do I
  have?" affordance. Maps from the `tag.list` service response
  (a list of all registered tags). Implementation: HA core
  `template:` sensor deriving the count from the `tag.list` service
  response.

- `sensor.rc_nfc_last_scanned_tag_id` — the most recent scanned
  NFC tag ID (e.g. "04:a3:2b:8c:1d:9e:5f:6a:80" / "tag_lights_off"
  / "tag_bedtime"). The `last_scanned_tag_id` is the canonical
  "what did I just scan?" debugging affordance. Maps from the
  most recent `tag_scanned` event's `tag_id` attribute. Source:
  HA core `event.tag_scanned` event + the upstream `tag.last_scanned`
  entity.

- `sensor.rc_nfc_last_scan_minutes_ago` — the freshness timestamp
  (minutes since the last successful `tag_scanned` event). The
  `last_scan_minutes_ago` is the canonical "when did the operator
  last interact with the van?" affordance. Maps from the
  `last_triggered` attribute of the operator's `automation.nfc_tag_
  to_scene` automation. Implementation: HA core `template:` sensor
  deriving the freshness from the automation trace's `last_triggered`
  attribute.

- `binary_sensor.rc_nfc_tag_unknown_warning` — the tag-unknown-warning
  gate (TRUE when the last scanned `tag_id` was unknown — the
  `tag_id` is NOT in the RoamCore `tag_id → scene` mapping table).
  The `tag_unknown_warning` is the canonical "the operator scanned
  an unregistered tag" affordance. Maps from the §7.2 tag-unknown
  warning automation. Implementation: HA core `template:` binary_sensor
  deriving the warning state from the §7.2 automation's
  `last_triggered` attribute.

- `binary_sensor.rc_nfc_stealth_mode_suppressed` — the Stealth-mode
  suppression gate (TRUE when the mode/automation-builder recipe's
  `select.rc_mode` tile is in `stealth` mode + the §7.3 Stealth-mode
  suppression automation is suppressing the §7.1 last-tag-triggered
  scene automation). The `stealth_mode_suppressed` is the canonical
  "are NFC-triggered scenes currently suppressed?" affordance.
  Maps from the `select.rc_mode` tile's current value from the
  mode/automation-builder recipe (Wave 2 #23). Implementation: HA
  core `template:` binary_sensor deriving the suppression state from
  the `select.rc_mode` tile's current value.

- `button.rc_nfc_trigger_scene_now` — the manual override button
  (triggers the last-tag-triggered scene without re-scanning the
  tag — useful for the "I just want the lights off" affordance, or
  for triggering the scene from the dashboard without walking to the
  NFC tag). The `trigger_scene_now` is the canonical "manually
  trigger the last-scanned-tag's scene" affordance. Source: HA core
  `input_button` integration + the operator's `script.last_triggered_
  scene` script.

Domain set (per docs/reference/rc-entity-naming.md §access_control
subsystem): binary_sensor, sensor, button.

## §7 Automations (MANDATORY before first use)

The THREE MANDATORY automations are the contract layer between the
operator's NFC tag scan events and the operator's scene registry.
The recipe is the documentation; the automations are the
implementation. The automations MUST be wired BEFORE the operator
starts using the NFC tags (otherwise the NFC scan events will be
fired but no scene will be triggered — the operator will be confused).

### §7.1 Last-tag-triggered scene (the `tag_id → scene` mapping)

The §7.1 last-tag-triggered scene automation is the operator's
`tag_id → scene` mapping table. The automation fires when a
`tag_scanned` event is received AND matches a known `tag_id` in the
mapping table AND then calls `scene.turn_on` on the mapped scene.

```yaml
# homeassistant/automations/nfc_tag_to_scene.yaml
- alias: "NFC: tag_id → scene"
  description: >
    The §7.1 last-tag-triggered scene automation. When a
    `tag_scanned` event is received, the automation checks the
    known `tag_id → scene` mapping table + calls `scene.turn_on`
    on the mapped scene.
  mode: single
  trigger:
    - platform: event
      event_type: tag_scanned
  condition: []
  action:
    - choose:
        # Lights off scene
        - conditions:
            - condition: template
              value_template: >
                {{ trigger.event.data.tag_id == 'tag_lights_off' }}
          sequence:
            - service: scene.turn_on
              target:
                entity_id: scene.lights_off
        # Bedtime scene
        - conditions:
            - condition: template
              value_template: >
                {{ trigger.event.data.tag_id == 'tag_bedtime' }}
          sequence:
            - service: scene.turn_on
              target:
                entity_id: scene.bedtime
        # Leave camp scene
        - conditions:
            - condition: template
              value_template: >
                {{ trigger.event.data.tag_id == 'tag_leave_camp' }}
          sequence:
            - service: scene.turn_on
              target:
                entity_id: scene.leave_camp
        # Welcome home scene
        - conditions:
            - condition: template
              value_template: >
                {{ trigger.event.data.tag_id == 'tag_welcome_home' }}
          sequence:
            - service: scene.turn_on
              target:
                entity_id: scene.welcome_home
```

### §7.2 Tag-unknown warning

The §7.2 tag-unknown warning automation fires when a `tag_scanned`
event is received AND the `tag_id` is NOT in the RoamCore
`tag_id → scene` mapping table. The automation sends a notification
to the operator's phone (via the HA Companion app) saying "Unknown
NFC tag scanned: <tag_id> — register it in the RoamCore tag_id →
scene mapping table".

```yaml
# homeassistant/automations/nfc_tag_unknown_warning.yaml
- alias: "NFC: tag-unknown warning"
  description: >
    The §7.2 tag-unknown warning automation. When a `tag_scanned`
    event is received AND the `tag_id` is NOT in the RoamCore
    `tag_id → scene` mapping table, the automation sends a
    notification to the operator's phone.
  mode: single
  trigger:
    - platform: event
      event_type: tag_scanned
  condition:
    - condition: template
      value_template: >
        {{ trigger.event.data.tag_id not in [
          'tag_lights_off', 'tag_bedtime',
          'tag_leave_camp', 'tag_welcome_home'
        ] }}
  action:
    - service: notify.mobile_app
      data:
        title: "NFC: unknown tag scanned"
        message: >
          Unknown NFC tag scanned: {{ trigger.event.data.tag_id }}
          — register it in the RoamCore tag_id → scene mapping
          table.
```

### §7.3 Stealth-mode suppression

The §7.3 Stealth-mode suppression automation SUPPRESSES the §7.1
last-tag-triggered scene automation when the `select.rc_mode` is in
`stealth` mode (campgrounds with quiet hours + overnight stays where
running a scene would disturb other campers).

```yaml
# homeassistant/automations/nfc_tag_stealth_mode_suppression.yaml
- alias: "NFC: stealth mode suppression"
  description: >
    The §7.3 Stealth-mode suppression automation. When the
    `select.rc_mode` is in `stealth` mode, this automation
    SUPPRESSES the §7.1 last-tag-triggered scene automation
    (by stopping the automation + sending a notification to the
    operator's phone saying "NFC tags are suppressed in stealth
    mode").
  mode: single
  trigger:
    - platform: state
      entity_id: select.rc_mode
      to: "stealth"
  action:
    - service: automation.turn_off
      target:
        entity_id: automation.nfc_tag_to_scene
    - service: notify.mobile_app
      data:
        title: "NFC: stealth mode suppression"
        message: >
          NFC tags suppressed in stealth mode (campground quiet
          hours). Re-enable via the mode/automation-builder
          recipe or scan the tag again after exiting stealth mode.
- alias: "NFC: stealth mode restore"
  description: >
    The §7.3 Stealth-mode suppression recovery automation. When
    the `select.rc_mode` leaves `stealth` mode, this automation
    RE-ENABLES the §7.1 last-tag-triggered scene automation.
  mode: single
  trigger:
    - platform: state
      entity_id: select.rc_mode
      from: "stealth"
  action:
    - service: automation.turn_on
      target:
        entity_id: automation.nfc_tag_to_scene
```

## §8 Troubleshooting

The following troubleshooting entries cover the most common issues
that operators encounter during the NFC tags setup. The recipe is
the documentation; the troubleshooting entries are the operator-side
diagnostic affordances.

### §8.1 NFC scan event fires but no scene is triggered

The most common cause is that the operator has NOT wired the §7.1
last-tag-triggered scene automation yet. The `tag_scanned` event
fires from HA core (Path A / Path B / Path C) but the §7.1
automation is the only thing that maps the `tag_id` to a scene.

Action: verify the §7.1 automation is configured (Settings →
Automations → NFC: tag_id → scene). The automation should be in
the "on" state. If the automation is "off", turn it on.

### §8.2 NFC scan event DOES NOT fire when I tap a tag

There are several possible causes:

- **Path A / Path C — the HA Companion app's NFC sensor is not
  enabled.** Open the HA Companion app on the phone → Settings →
  Companion app → Sensors → NFC tag sensor → enable. If the
  sensor is enabled but the event still does not fire, try
  re-installing the HA Companion app.
- **Path B — the USB NFC reader is not detected.** SSH into the HA
  server + run `lsusb` to verify the USB NFC reader is detected
  by the Linux kernel. If the reader is not detected, try a
  different USB port.
- **Path B — the HACS `nfcpy` integration is not configured.** Open
  HACS → Integrations → nfcpy → Configure. The integration should
  be in the "active" state. If the integration is not configured,
  configure it.
- **The NFC tag is not registered in HA's tag registry.** Open
  Settings → Devices & Services → Tags → verify the tag is
  registered. If the tag is not registered, register it.

### §8.3 Re-scanning the same tag fires the same scene repeatedly

The §7.1 automation runs in `mode: single` (only one
`tag_scanned` event is processed at a time). If the operator is
re-scanning the same tag rapidly (e.g. testing the NFC tag setup),
the automation may fire multiple times in quick succession.

Action: change the §7.1 automation's `mode` to `mode: queued` if
the operator wants every scan to fire (with a 5-second debounce).
Alternatively, the operator can add a `for: "00:00:05"` debounce
to the trigger to prevent duplicate fires.

### §8.4 Tag-unknown warning fires for a tag I just registered

The most common cause is that the operator registered the tag in
HA's tag registry but did NOT add the tag's `tag_id` to the §7.1
automation's `choose:` block. The §7.1 automation is the single
source of truth for which tag fires which scene.

Action: verify the tag's `tag_id` is in the §7.1 automation's
`choose:` block. The `tag_id` is the hexadecimal string
(e.g. `04:a3:2b:8c:1d:9e:5f:6a:80`) — NOT the tag's friendly name.

### §8.5 Stealth-mode suppression is always active

The most common cause is that the operator accidentally set the
`select.rc_mode` tile to `stealth` mode and did not exit stealth
mode. The mode/automation-builder recipe (Wave 2 #23) controls the
mode tile.

Action: verify the `select.rc_mode` tile's current value
(Developer tools → States → search `select.rc_mode`). If the value
is `stealth`, change it to `home` / `away` / `sleep` (whatever the
operator's preferred mode is).

### §8.6 Last-tag-triggered scene fires but the scene does NOT do anything

The most common cause is that the operator's `scene.*` entity does
not exist in HA's scene registry. The §7.1 automation calls
`scene.turn_on` on the mapped scene + the HA core `scene` integration
looks up the scene by its `entity_id`.

Action: verify the scene's `entity_id` is correct. The scene
entities are listed in Settings → Devices & Services → Scenes.
If the scene does not exist, create it.

## §9 Privacy

NFC tags produce no telemetry beyond local HA tag registry + scene
registry + scan event log. The recipe is the contract layer; the
upstream HA core `tag` integration + the HA Companion app + the HACS
`nfcpy` integration are the upstream sources. The privacy posture:

- **No telemetry beyond local HA tag registry + scene registry +
  scan event log.** The `tag_scanned` event is fired in HA core
  locally; the event is NOT forwarded to any cloud service.
- **No cloud call home.** Path A (HA Companion app) does NOT call
  home to the HA Cloud; Path B (HACS `nfcpy` integration) does NOT
  call home to HACS Cloud; Path C (HA Companion app's implicit
  Path A) does NOT call home to the HA Cloud. The recipe is
  fully local.
- **Path A / Path C — the HA Companion app's NFC sensor is
  enabled by the operator.** The operator must opt in to the NFC
  sensor in the HA Companion app (Settings → Companion app →
  Sensors → NFC tag sensor). This is an explicit opt-in.
- **Path B — the HACS `nfcpy` integration is operator-installed.**
  The HACS `nfcpy` integration is installed by the operator from
  HACS. The integration is a local USB driver + a local HA tag
  scanner; no cloud call home.
- **Operator's `tag_id → scene` mapping table is operator-owned.**
  The mapping table is the operator's single source of truth for
  which tag fires which scene. The mapping is stored in HA's
  automation YAML (local) and is NOT shared with any cloud
  service.

The recipe does NOT collect any personally identifiable information
(PII) about the operator's NFC tag scans. The recipe is fully
local; the operator's privacy is preserved.

## §10 Promoting to tier-b

To promote the NFC tags connection from tier-c to tier-b, the
following would need to happen:

1. **Real NFC bench on CI.** RoamCore would need a CI bench with a
   physical NFC reader (an ACR122U / PN532 USB NFC reader) +
   canned fixture responses for `tag_scanned` events (a list of
   pre-known `tag_id` values + their expected scene mappings) +
   the upstream HA core `tag` integration installed + the HACS
   `nfcpy` integration installed + the HA Companion app's `tag`
   trigger installed. The bench is the canonical "integration
   test" target for NFC tags.
2. **RoamCore-owned operator-wired setup flow.** RoamCore would
   need a `config_flow.py` for the NFC tags integration that
   walks the operator through registering each NFC tag in HA's
   tag registry + writing the `tag_id → scene` mapping into the
   RoamCore wrapper. The setup flow is the canonical
   "operator-wired" affordance that distinguishes tier-c from
   tier-b.
3. **Integration tests asserting:**
   - A `tag_scanned` event with a known `tag_id` triggers the
     mapped scene.
   - A `tag_scanned` event with an unknown `tag_id` fires the
     tag-unknown warning.
   - A `select.rc_mode` change to `stealth` suppresses the §7.1
     automation.
   - A `select.rc_mode` change from `stealth` re-enables the
     §7.1 automation.
   - The contract tiles reflect the current state of the NFC
     tag setup (last-triggered-scene + last-triggered-scene-
     active + registered-tags-count + last-scanned-tag-id +
     last-scan-minutes-ago + tag-unknown-warning + stealth-
     mode-suppressed + trigger-scene-now).

The tier-b promotion is BLOCKED on the real NFC bench; until the
bench fixture lands, the NFC tags connection is tier-c.

## §11 Files in this connection + cross-references

### Files

- `connections/nfc-tags/connection.yml` — the source-of-truth
  manifest.
- `connections/nfc-tags/__init__.py` — the `DOMAIN = "nfc_tags"`
  marker for the audit.
- `connections/nfc-tags/README.md` — the folder overview.
- `connections/nfc-tags/docs/recipe.md` — the full howto.
- `connections/nfc-tags/tests/test_connection_yml.py` — the
  manifest honesty checks.

### Cross-references

- **HA core `tag` integration** (the canonical NFC tag scan event
  source; since 2022.x) — https://www.home-assistant.io/integrations/tag/
- **HA core `scene` integration** (the canonical scene registry;
  since 2022.x) — https://www.home-assistant.io/integrations/scene/
- **HA core `automation` UI editor** (the canonical operator-wired
  setup flow; since 2022.x) — https://www.home-assistant.io/integrations/automation/
- **HA Companion app** (the phone-side NFC reader for Path A +
  Path C implicit Path A; since 2022.x) — https://companion.home-assistant.io/docs/core/sensors
- **HACS `nfcpy` integration** (the USB NFC reader for Path B;
  HACS) — https://hacs.xyz/docs/integrations/active
- **Mode/automation-builder recipe** (the `select.rc_mode` tile
  source of truth for the §7.3 Stealth-mode suppression; Wave 2
  #23) — `connections/smart-automations/`
- **Deadbolts** (the optional "tag-unlock-the-door" affordance
  that uses the same `tag_id → scene` mapping pattern; Wave 3
  #48) — `connections/deadbolts/`
- **Approach lights** (the canonical "Lights off" / "Welcome
  home" scene entities; Wave 3 #52) — `connections/approach-lights/`
- **HVAC basics** (the canonical "Bedtime" / "Climate" scene
  entities; Wave 3 #49) — `connections/hvac-basics/`
- **RoamCore entity naming** — `docs/reference/rc-entity-naming.md`
  (the `nfc` subsystem was added by this slice; the §access_control
  category is the canonical category for NFC tags + deadbolts)
