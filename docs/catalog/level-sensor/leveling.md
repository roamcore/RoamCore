# Levelling sensor (pitch/roll + “are we level?”)

**Support tier:** A (RoamCore native) — *aspirational claim; the picker is honest: see SUPERSEDED banner at the end of this doc.*

## What this is
RoamCore defines a levelling contract (`rc_level_*`) and supports pitch/roll sensors so the dashboard can show an easy levelling status.

## Why it’s useful in a van
- Better sleep and cooking
- Quick “good enough” check without guessing

## Extra hardware required
- A pitch/roll sensor (often via ESPHome / accelerometer)

## Install / best next step
- Guide: `docs/guides/leveling-ha-esphome.md`
- HA package: `homeassistant/packages/roamcore_level.yaml`
- System-level helpers: `homeassistant/packages/roamcore_system_level.yaml`

## Links
- (Add recommended sensors + ESPHome boards)

---

> **SUPERSEDED — 2026-08-03.** The 18-line tier-a claim stub at this path has been promoted into a tier-b recipe connection at [`connections/leveling/`](../../../../connections/leveling/). The legacy tier-a "RoamCore native" claim is **honest-upstream-truth**: RoamCore ships **no** native levelling engine today; the contract layer + the recipe + the §8 MANDATORY automations are the canonical RoamCore contribution; the upstream engines are HA core + the HA Companion app's phone IMU + the ESPHome components + the HACS `mopeka` / `bno055` / `esp32_imu` integrations + the well-known pneumatic / hydraulic levelling jacks driven via relay. Replaced by the tier-b recipe connection; see [`connections/leveling/` README](../../../../connections/leveling/README.md) + [`connections/leveling/docs/recipe.md`](../../../../connections/leveling/docs/recipe.md). Wave 3 #60, PR #64.
