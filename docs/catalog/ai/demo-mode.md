# Demo Mode (safe demo values)

**Support tier:** A (RoamCore native) — *aspirational claim; the picker is honest: see SUPERSEDED banner at the end of this doc.*

## What this is
Demo Mode lets RoamCore show example values when critical sensors are missing, so the UI still looks and feels complete during setup or demos.

## Why it’s useful in a van
- Helps you configure slowly without a broken-looking dashboard
- Great for showcasing RoamCore without full hardware installed

## Extra hardware required
- None

## Install / best next step
- HA package: `homeassistant/packages/roamcore_demo_mode.yaml`

## Links
- (Add how-to and screenshots later)

---

> **SUPERSEDED — 2026-08-03.** The 14-line tier-a claim stub at this path has been promoted into a tier-b recipe connection at [`connections/demo-mode/`](../../../../connections/demo-mode/). The legacy tier-a "RoamCore native" claim is **honest-upstream-truth**: RoamCore ships **no** native demo-mode engine today; the contract layer + the recipe + the §8 MANDATORY automations are the canonical RoamCore contribution; the upstream engines are HA core `input_boolean` + `input_select` + `input_text` + `input_number` helpers (since 2022.x) + the HA core `template:` sensor + `template:` binary_sensor wrappers (since 2022.x). Replaced by the tier-b recipe connection; see [`connections/demo-mode/` README](../../../../connections/demo-mode/README.md) + [`connections/demo-mode/docs/recipe.md`](../../../../connections/demo-mode/docs/recipe.md). Wave 3 #62, PR #66.
