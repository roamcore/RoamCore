# Advanced Mode (power-user toggle)

**Support tier:** A (RoamCore native) — *aspirational claim; the picker is honest: see SUPERSEDED banner at the end of this doc.*

## What this is
RoamCore includes an Advanced Mode toggle that can reveal extra controls and diagnostics without cluttering the default UI.

## Why it’s useful in a van
- Keeps the dashboard clean for daily use
- Still gives power users access to deeper controls when needed

## Extra hardware required
- None

## Install / best next step
- HA package: `homeassistant/packages/roamcore_advanced_mode.yaml`

## Links
- (Add screenshots / explanation later)

---

> **SUPERSEDED — 2026-08-03.** The 13-line tier-a claim stub at this path has been promoted into a tier-b recipe connection at [`connections/advanced-mode/`](../../../../connections/advanced-mode/). The legacy tier-a "RoamCore native" claim is **honest-upstream-truth**: RoamCore ships **no** native advanced-mode engine today; the contract layer + the recipe + the FIVE §8 MANDATORY automations are the canonical RoamCore contribution; the upstream engines are HA core `input_boolean` + `input_text` + `input_datetime` + `input_button` + `select` helpers (since 2022.x) + the HA core `template:` sensor + `template:` binary_sensor wrappers (since 2022.x). Replaced by the tier-b recipe connection; see [`connections/advanced-mode/` README](../../../../connections/advanced-mode/README.md) + [`connections/advanced-mode/docs/recipe.md`](../../../../connections/advanced-mode/docs/recipe.md). Wave 3 #63, PR #67.
