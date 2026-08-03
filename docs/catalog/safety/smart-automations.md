# Smart Automations (one-click enable)

> **Replaced by:** `connections/smart-automations/` (Wave 3 #46,
> tier-b recipe connection, 2026-07-30). This catalog page is the
> legacy tier-c spec (which claimed tier-A "RoamCore native" but
> RoamCore ships NO native automation engine — the connection is
> honestly tier-b). The connection folder is the source of truth
> for the install + recipe + vendor-neutral contract tiles.
> See `connections/smart-automations/` for the canonical 24
> `rc_safety_automation_*` + `rc_safety_automations_*` contract
> tiles (7 summary: enabled count / total count / missing count /
> all-ready / view select / enable-all-ready button / disable-all
> button + 17 per-automation mirror binary_sensors for Night Mode,
> Auto Internet Failover, Low Battery Mode, Freeze Protection,
> Daily Trip Log, Battery Full Alert, Inverter Overheat Alert,
> Router Overheat Alert, Shore Power Connected, Shore Power
> Disconnected, Internet Recovery, Arrive at Camp, Depart Travel
> Mode, Solar is Crushing It, Battery Critical Alert, Bedtime
> Level Check, Quiet Hours Reminder) + the full howto at
> `connections/smart-automations/docs/recipe.md`.

**Support tier:** A (RoamCore native)

## What this is
A small set of prebuilt automations you can enable/disable from the RoamCore UI (implemented as native HA automations under the hood).

## Why it’s useful in a van
- Safety/comfort reminders without building YAML
- Easy to tweak later in Home Assistant

## Extra hardware required
- None (depends on which sensors each automation uses)

## Install / best next step
- See: `docs/guides/smart-automations.md`

## Links
- (Add videos/examples)
