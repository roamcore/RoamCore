# Advanced Mode (power-user toggle)

**Support tier:** A (RoamCore native)

RoamCore's Advanced Mode is the single, deliberate gate between the
clean "van.local" daily-driver UI and the deeper power-user controls.
It is a clearly-separated toggle — not a hidden setting — and it ships
with a safe-recovery guarantee so an accidental slide into advanced mode
can be unwound in one tap.

## 1. What it is

Advanced Mode is a single boolean — `input_boolean.rc_advanced_mode_enabled`
(mirrored by `binary_sensor.rc_advanced_mode`) — that gates optional
power-user surfaces across RoamCore:

- The Settings page surfaces a one-tap **Engage / Lock again** card
  (`custom:roamcore-advanced-mode`).
- When the toggle is **ON**, downstream RoamCore surfaces can reveal
  deeper controls, diagnostics, and admin shortcuts.
- When the toggle is **OFF**, RoamCore stays in its default clean state.
  No HA chrome is ever exposed on `van.local`; Advanced Mode is just the
  RoamCore-level acknowledgement that power-user actions are allowed.

The boolean defaults to **off**. Toggling it ON runs the
`script.rc_advanced_mode_engage` script, which:

1. Flips `input_boolean.rc_advanced_mode_enabled` to `on`.
2. Records a timestamped JSON snapshot of current RoamCore state into
   `input_text.rc_advanced_mode_last_engaged_state`.
3. Writes a recovery marker to
   `homeassistant/.roamcore/advanced_mode_snapshot.json`.
4. Appends an `engaged at <iso8601>` line to
   `homeassistant/.roamcore/advanced_mode_audit.log`.
5. Fires a `persistent_notification` for the operator.

Toggling it OFF runs `script.rc_advanced_mode_disengage`, which:

1. Flips `input_boolean.rc_advanced_mode_enabled` to `off`.
2. Appends a `disengaged at <iso8601>` line to
   `homeassistant/.roamcore/advanced_mode_audit.log`.
3. Fires a `persistent_notification` for the operator.

## 2. How to engage

The simplest path is the UI card on the Settings page:

1. Open the RoamCore dashboard.
2. Tap the gear icon (⚙) to open **Settings**.
3. Scroll to the **Advanced** tile — the Advanced Mode card sits at
   the bottom of that tile.
4. Tap **Engage advanced mode**.

The card immediately flips to a yellow "advanced controls unlocked"
banner and exposes a red **Lock again** button.

You can also engage from anywhere in HA:

```yaml
action: script.rc_advanced_mode_engage
```

Or via the entity directly (less safe — bypasses the snapshot):

```yaml
action: input_boolean.turn_on
target:
  entity_id: input_boolean.rc_advanced_mode_enabled
```

## 3. Recovery (one-tap unwind)

Because every engagement writes a snapshot, recovering is mechanical:

1. Tap **Lock again** on the Advanced Mode card (calls
   `script.rc_advanced_mode_disengage`).
2. Read the snapshot:
   - On-disk: `homeassistant/.roamcore/advanced_mode_snapshot.json`
   - In-HA: `input_text.rc_advanced_mode_last_engaged_state` (JSON
     payload, includes `engaged_at`, current `mode`, `demo_mode`,
     `amenities_overlay`, `offline_only`).
3. Read the audit trail:
   `homeassistant/.roamcore/advanced_mode_audit.log`
4. If the user changed settings while in Advanced Mode, manually
   reverse the changes that you find surprising, then re-engage to
   take a fresh snapshot (or leave it off).

In short: the boolean is the source of truth, the snapshot is the
"what changed while we were in here", and the audit log is the
"who/when".

## 4. Safety guarantees

- **Clearly separated.** Advanced Mode is a first-class UI card with
  its own badge (ON / OFF) and a dedicated `binary_sensor` mirror. The
  default state is **off**.
- **Single path to flip.** The boolean is meant to be flipped only by
  `script.rc_advanced_mode_engage` / `script.rc_advanced_mode_disengage`,
  both of which write to the snapshot and audit log.
- **Auditable.** Every engagement / disengagement writes to
  `homeassistant/.roamcore/advanced_mode_audit.log` and surfaces a
  `persistent_notification` in HA.
- **Recoverable.** A snapshot of pre-engage state lives in
  `input_text.rc_advanced_mode_last_engaged_state` (in-HA) and in
  `homeassistant/.roamcore/advanced_mode_snapshot.json` (on-disk). One
  tap on **Lock again** clears the toggle.
- **No new dependencies.** Snapshot + audit writes are `shell_command`
  helpers that call `tee -a`. No Python deps were added in this slice.
- **Local-first.** No cloud round-trip, no telemetry. Advanced Mode is
  a plain HA boolean with a UI card.

## 5. Why this slice exists

The RoamCore access model (see `homeassistant/HAOS/NormalVsAdminMode.md`)
already isolates `van.local` from HA chrome at the reverse-proxy layer.
Advanced Mode is the in-app counterpart of that model — it makes the
"yes I am a power user" intent explicit and reversible, instead of
leaving operators to discover (or miss) the deep controls by accident.

## Extra hardware required
- None. It's a software toggle + UI card.

## Install / best next step
- HA package: `homeassistant/packages/roamcore_advanced_mode.yaml`
- UI card: `homeassistant/www/roamcore/roamcore-advanced-mode.js`
- Operator docs: `docs/setup/advanced-mode.md`
- Wired into: Settings page → Advanced tile (slice #25)

## Links
- `docs/setup/advanced-mode.md` — operator-facing recovery steps
- `homeassistant/HAOS/NormalVsAdminMode.md` — full RoamCore access model
- `docs/feature-checklist.md` §System UX — the row flipped to `[x]` in
  slice #25