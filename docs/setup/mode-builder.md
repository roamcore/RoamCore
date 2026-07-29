# Mode / automation builder (slice #23)

RoamCore's **Mode** is the single piece that downstream automation rules
(Wave 2 #24, #26) all depend on. The Mode subsystem lets you:

1. **Pick a mode** — one-tap, from a 5-segment pill (`auto`, `travel`,
   `camp`, `stealth`, `off`). The current mode drives the rest of
   RoamCore: power strategy, location reporting cadence, push
   notifications, etc.
2. **Define simple rules** — "when X happens, switch to mode Y". The
   builder UI lets you add, edit, and disable rules without writing
   YAML.

## Entities (contract)

| Entity | Purpose |
| --- | --- |
| `input_select.rc_mode` | Current mode (auto / travel / camp / stealth / off). |
| `input_text.rc_mode_rules_json` | JSON array of rule objects. |

Each rule in `rc_mode_rules_json` follows this shape:

```json
{
  "id": "rule_<uuid>",
  "name": "When battery is low, switch to stealth",
  "when": { "entity": "sensor.rc_battery_soc", "op": "<", "value": 20 },
  "then": "stealth",
  "enabled": true,
  "cooldownMin": 15
}
```

- `when.op` is one of `<`, `>`, `<=`, `>=`, `==`, `!=`.
- `when.value` may be numeric or string.
- `then` is one of the five rc_mode options.
- `cooldownMin` is the minimum minutes between two consecutive fires of
  this rule.

The first install ships with **two seed rules**:

1. "When battery is low, switch to stealth" — `sensor.rc_battery_soc < 20`
2. "When motion stays on for 5 min, switch to camp" —
   `binary_sensor.rc_motion_active == on`

Use the UI's **Reset to defaults** button to re-seed after wiping.

## How rules fire

The `automation.rc_mode_apply_rules` automation runs:

- on every state change of `input_select.rc_mode`
- on every state change of `input_text.rc_mode_rules_json`

For each rule it:

1. Skips rules whose `then` does not match the current mode.
2. Skips disabled rules (`enabled == false`).
3. Reads the state of `when.entity` and evaluates `(state op value)`.
4. Skips rules whose cooldown has not yet elapsed (per-rule
   `input_datetime.rc_mode_rule_<id>_last_fired`).
5. If the rule matches AND the cooldown has elapsed, fires the rule by
   re-selecting the current mode (idempotent) and writing
   `now()` to the per-rule cooldown entity.

The fire is intentionally idempotent: the action is `select_option` with
the current mode, so re-evaluating a rule in the same mode is a no-op.
The side effect you can rely on is the cooldown timestamp; downstream
integrations can read it.

### Known limits (intentional)

This slice is intentionally simple:

- **No AND/OR groups** — each rule has one when-clause.
- **No polling** — rules are evaluated on mode-change and rules-list
  change only. A future slice will add polling triggers so a rule can
  fire when its underlying entity changes while staying in the same
  mode.
- **No temporary disable** — toggling a rule off updates
  `enabled=false` in the JSON; the rule remains visible and editable.

## UI

A new Lovelace custom card `custom:roamcore-mode-builder` is shipped in
`homeassistant/www/roamcore/roamcore-mode-builder.js`. It is rendered on
the **Map / Dashboard** page (matching the placement of the existing
amenities overlay layer). The card:

- shows the current mode as a 5-segment pill (tap to switch);
- lists every rule with its when-clause, then-mode, and a toggle;
- has a `+ Add rule` button that opens a modal (name + entity + op +
  value + then-mode);
- has a `Reset to defaults` button that re-seeds the JSON;
- hides itself cleanly if `input_select.rc_mode` is missing.

## Files

- `homeassistant/packages/roamcore_mode.yaml` — declares
  `input_select.rc_mode`, `input_text.rc_mode_rules_json`, the 5
  quick-set scripts, the `rc_mode_apply` scaffold, and
  `automation.rc_mode_apply_rules`.
- `homeassistant/packages/roamcore_mode_builder.yaml` — declares the
  `script.rc_mode_rules_seed_defaults` "Reset to defaults" script.
- `homeassistant/www/roamcore/roamcore-mode-builder.js` — the custom
  card implementation (vanilla JS, no build step).
- `homeassistant/www/roamcore/roamcore-pages.js` — mounts the card on
  the Map / Dashboard page.
- `scripts/checks/mode-builder-smoke.sh` — repo-local smoke check
  (wired into `scripts/check.sh --core-only`).
