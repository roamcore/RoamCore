# Gamification (opt-in streak + trophy subsystem)

**Support tier:** C (RoamCore native, community-curated, best-effort)

## What this is
RoamCore Gamification is a delightful, opt-in streak + trophy subsystem that counts *real, observable, on-prem RoamCore activities*. The 7 starter trophies are intentionally boring — each one maps to a real RoamCore user action (Trip Wrapped, Victron telemetry, automation fired, Labs bundle exported, on-device trip privacy, setup wizard complete, twilight handling). Privacy-by-default: local counter only, no telemetry, no third-party HTTP, no external CDN. The operator is in control of every byte.

## Why it's useful in a van
- Track small wins as you build out your RoamCore install
- Discover subsystems you haven't tried yet (each trophy is a one-tap CTA to the related slice)
- Share your progress with a friend without exposing any telemetry — trophy state is purely local

## Extra hardware required
- None. Gamification composes over RoamCore's existing signals.

## Install / best next step
- See: `docs/setup/gamification.md`

## Trophy taxonomy

The 7 starter trophies, all tier-c, all bucketed, all opt-in:

| Trophy ID | Bucket | Trigger |
| --- | --- | --- |
| `first_trip_wrapped` | Map / Trip | First Trip Wrapped export (`sensor.rc_trip_wrapped_latest_generated_at`) |
| `first_power_session` | Power | First Victron telemetry tick (`sensor.rc_power_battery_soc`) |
| `first_automation` | Automations | First `rc_*` automation fired post install |
| `first_share_exported` | Community | First Labs bundle exported (`text.rc_labs_last_export_path`) |
| `first_offline_driving_day` | Map / Trip | First 24h window with Traccar-derived movement AND zero telemetry leaked off-device (`sensor.rc_trip_local_today_distance_mi > 3.1 mi`, verified by the trip-tracking privacy smoke) |
| `first_setup_complete` | System UX | First time the setup wizard reaches "Done" (all 6 `binary_sensor.rc_setup_*_ready` are ON) |
| `first_twilight_handling` | Lighting | First day→twilight boundary detection (sun below horizon + location known) |

## Enable flow

1. Settings → Developer Tools → Services → `input_boolean.turn_on` on `input_boolean.rc_gamification_enabled` (default OFF).
2. Wait for the trophy cards to render (template sensors refresh on entity-change, ~30s).
3. Do anything that produces a real RoamCore signal — the relevant trophy card flips to "Triggered".
4. Tap the Acknowledge button on the card to clear the "new" chip.

## Uninstall

Flip `input_boolean.rc_gamification_enabled` back to OFF. The package's
contract entities stay registered (so dashboard history is preserved)
but every derived sensor reports `unavailable`. To fully remove the
slice, delete the contract package + wizard snippet + custom-component
handler.

## Privacy

- Local-only. No HTTP, no DNS, no third-party imports.
- No telemetry. No external CDN.
- Operator kill-switch on `binary_sensor.rc_gamification_enabled` (default OFF).
- Privacy invariant enforced in CI by `scripts/checks/gamification-smoke.sh`.

## RoamCore Gamification
- Built-in: `docs/setup/gamification.md`
- Contract package: `homeassistant/packages/roamcore_gamification.yaml`
- Wizard snippet: `homeassistant/packages/roamcore_setup_wizard_gamification.yaml`
- Service: `roamcore.gamification_acknowledge_trophy` (registered in `homeassistant/custom_components/roamcore/services.yaml`)
- CLI mirror: `homeassistant/tools/gamification/trophy_state.py` (stdlib-only)
- Smoke check: `scripts/checks/gamification-smoke.sh` (privacy invariant + N assertions)

## Links
- (Add videos/quickstart)