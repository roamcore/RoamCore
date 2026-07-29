# Advanced Mode — operator setup (Wave 2 #25)

RoamCore's **Advanced Mode** is the deliberate, reversible toggle
between the clean daily-driver UI and the deeper power-user surfaces.
This page is the operator runbook: how to **engage** it, how to
**disengage** it, and how to **recover** if you want to roll back any
changes you made while it was ON.

> Catalog page (overview): `docs/catalog/ai/advanced-mode.md`
> Access model (architecture): `homeassistant/HAOS/NormalVsAdminMode.md`

## Entities (the contract)

| Entity | Purpose |
| --- | --- |
| `input_boolean.rc_advanced_mode_enabled` | The toggle. Default: **off**. |
| `binary_sensor.rc_advanced_mode` | Mirror of the boolean. |
| `input_text.rc_advanced_mode_last_engaged_state` | JSON snapshot of state at engage time. |
| `script.rc_advanced_mode_engage` | The only safe way to flip ON. |
| `script.rc_advanced_mode_disengage` | The only safe way to flip OFF. |
| `automation.rc_advanced_mode_engaged_audit` | Logs the engagement edge transition. |
| `automation.rc_advanced_mode_disengaged_audit` | Logs the disengagement edge transition. |
| `homeassistant/.roamcore/advanced_mode_snapshot.json` | On-disk snapshot (written on engage). |
| `homeassistant/.roamcore/advanced_mode_audit.log` | Append-only audit trail. |

## How to engage

**Path A — UI card (recommended):**

1. Open the RoamCore dashboard.
2. Tap ⚙ → **Settings**.
3. Scroll to the **Advanced** tile.
4. Tap **Engage advanced mode**.

What happens:

- The boolean flips to `on`.
- The card shows a yellow "advanced controls unlocked" banner.
- A snapshot lands in `input_text.rc_advanced_mode_last_engaged_state`.
- A `persistent_notification` titled "Advanced mode ENGAGED" appears.
- An `engaged at <iso8601>` line is appended to the audit log.

**Path B — call the script directly:**

```yaml
action: script.rc_advanced_mode_engage
```

This is the same code path as the UI card. Prefer this over flipping the
boolean directly so the snapshot + audit are written.

## How to disengage

**Path A — UI card (recommended):**

On the same Settings → Advanced tile, tap **Lock again**. The boolean
flips back to `off`, the banner disappears, and a `persistent_notification`
titled "Advanced mode LOCKED" appears.

**Path B — call the script directly:**

```yaml
action: script.rc_advanced_mode_disengage
```

## How to recover

Disengaging only flips the boolean. If you changed settings while
Advanced Mode was ON and want to undo those changes, follow these
steps:

1. **Read the snapshot.** Either:
   - In-HA: open Developer Tools → States → search
     `input_text.rc_advanced_mode_last_engaged_state`. The value is a
     JSON blob with `engaged_at`, `mode`, `demo_mode`,
     `amenities_overlay`, `offline_only`.
   - On-disk (via SSH): `cat homeassistant/.roamcore/advanced_mode_snapshot.json`
2. **Read the audit log** for the full timeline:
   `cat homeassistant/.roamcore/advanced_mode_audit.log`
   (or browse it in HA via Developer Tools → Files → `.roamcore`).
3. **Identify changes.** Compare the snapshot values to the current
   states. Anything that flipped while Advanced Mode was ON is a
   candidate for rollback.
4. **Revert** the changes you made (e.g. flip an
   `input_boolean.*` back, restore an `input_select.*` value, etc.).
5. **Re-engage** to take a fresh snapshot (or leave Advanced Mode
   off — the boolean is the source of truth).

## Safety guarantees

- The default state is **off** (`input_boolean.rc_advanced_mode_enabled.initial: false`).
- Engagement is only done via `script.rc_advanced_mode_engage`, which
  is the single path that writes the snapshot + audit log.
- The `persistent_notification`s give you a visible in-HA breadcrumb of
  every edge transition.
- The audit log is append-only (`tee -a`), so a rollback never erases
  history.

## Files (this slice)

- `homeassistant/packages/roamcore_advanced_mode.yaml` — input_boolean,
  input_text, template binary_sensor, both scripts, all
  `shell_command` audit/snapshot writers, and both audit automations.
- `homeassistant/www/roamcore/roamcore-advanced-mode.js` — the
  `custom:roamcore-advanced-mode` UI card (vanilla JS, no build step).
- `homeassistant/www/roamcore/roamcore-pages.js` — mounts the card on
  the Settings page (Advanced tile).
- `docs/catalog/ai/advanced-mode.md` — catalog overview (What / How /
  Recovery / Safety).
- `docs/feature-checklist.md` — §System UX row flipped to `[x]` for
  slice #25.
- `scripts/checks/advanced-mode-smoke.sh` — repo-local smoke check
  wired into `scripts/check.sh --core-only`.