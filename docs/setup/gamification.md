# Setup — RoamCore Gamification (opt-in streak + trophy subsystem)

**Tier:** c (community-curated, best-effort). Optional — operator must opt in.

## What this is

A delightful, opt-in streak + trophy subsystem that counts *real,
observable, on-prem RoamCore activities*. Every trophy composes over
an already-shipping RoamCore signal — no new sensors, no MQTT topics,
no telemetry, no third-party HTTP. The count is a local counter.

The 7 starter trophies are intentionally boring. No "streaks for the
sake of streaks". Each one maps to a real RoamCore user action.

## Trophy taxonomy

| Trophy ID                | Bucket         | Trigger                                                                                                       |
|--------------------------|----------------|---------------------------------------------------------------------------------------------------------------|
| `first_trip_wrapped`     | Map / Trip     | First Trip Wrapped export (`sensor.rc_trip_wrapped_latest_generated_at`)                                       |
| `first_power_session`    | Power          | First Victron telemetry tick (`sensor.rc_power_battery_soc`)                                                  |
| `first_automation`       | Automations    | First automation fired post RoamCore install (any `automation` whose id prefix is `rc_` and `last_triggered` is set) |
| `first_share_exported`   | Community      | First Labs bundle exported (`text.rc_labs_last_export_path`)                                                  |
| `first_offline_driving_day` | Map / Trip  | First 24h window with Traccar-derived movement AND zero telemetry leaked off-device (`sensor.rc_trip_local_today_distance_mi > 3.1 mi`, verified by the trip-tracking privacy smoke) |
| `first_setup_complete`   | System UX      | First time the setup wizard reaches "Done" (all 6 `binary_sensor.rc_setup_*_ready` are ON)                     |
| `first_twilight_handling`| Lighting       | First successful day→twilight boundary detection (sun below horizon + location known)                          |

## 1. Enable the Gamification subsystem

Open **RoamCore → Setup Wizard → Gamification (optional)** and flip the
"On" toggle, or flip `input_boolean.rc_gamification_enabled` ON
manually. The default state is **OFF** — the operator must opt in.

## 2. Confirm the 7 trophy cards appear

Visit the Gamification card. You should see 7 trophy cards with "Not
triggered" status, each with its own Acknowledge button. The trophy
count chip should read **0 of 7**.

## 3. Trigger at least one RoamCore action

Do anything that produces a real RoamCore signal, for example:

- Export a Labs bundle (Settings → RoamCore Labs → Export Setup)
- Run a setup wizard stage
- Fire an automation
- Drive somewhere (Trip Wrapped will pick it up)
- Wait for the wizard to reach "Done"

## 4. Confirm the trophy card flips to "Triggered"

The relevant trophy card flips to "Triggered" within ~30 seconds
(template sensors refresh on entity-change). When you're ready to
clear the "new" chip, tap the Acknowledge button on that card.

## 5. Privacy

Gamification is a **local counter only**. There is no telemetry, no
third-party HTTP, no external CDN, no off-device sync. Every trophy
composes over RoamCore's existing signals. You can disable the
subsystem at any time by flipping `input_boolean.rc_gamification_enabled`
back to OFF — when OFF, every derived sensor reports `unavailable`
(not `unknown`/`0`).

The privacy invariant is enforced in CI by
`scripts/checks/gamification-smoke.sh`.

## 6. Troubleshooting

- **Trophies not triggering.** Verify the entity each trophy references
  is alive (`Settings → Devices & Services → Entities`). Each trophy
  composes over an already-shipping RoamCore signal; if the source
  entity is `unknown`/`unavailable`, the trophy stays untriggered.
- **Count stuck at 0.** The kill-switch is OFF. Flip
  `input_boolean.rc_gamification_enabled` ON.
- **Trophy fires but the counter doesn't bump.** Template cache.
  Restart Home Assistant (`Settings → System → Restart`). The
  template sensors recompute on the next refresh.
- **Acknowledge button does nothing.** The `trophy_id` is rejected by
  the service (a persistent notification will surface the error).
  Verify the trophy id matches one of the 7 known IDs.

## Files

- `homeassistant/packages/roamcore_gamification.yaml` — contract layer (19 entities).
- `homeassistant/packages/roamcore_setup_wizard_gamification.yaml` — wizard snippet.
- `homeassistant/tools/gamification/trophy_state.py` — stdlib-only snapshot helper.
- `scripts/checks/gamification-smoke.sh` — privacy + assertions smoke check.

## Cross-references

- `docs/catalog/community/gamification.md` — tier-c community catalog entry.
- `docs/feature-checklist.md` line 80 — feature checklist (ticked `[x]`).
- `docs/mvp/features-build-status.md` — Wave 2 #33 slice shipped entry.