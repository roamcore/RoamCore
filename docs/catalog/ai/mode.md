# Mode (Auto / Travel / Camp / Stealth)

**Support tier:** A (RoamCore native) — *aspirational claim; the picker is honest: see SUPERSEDED banner at the end of this doc.*

## What this is
RoamCore defines a simple “Mode” entity and convenience scripts (Auto/Travel/Camp/Stealth/Off). This shows up as a user-facing control in the dashboard and is a foundation for future “one tap” behavior changes.

## Why it’s useful in a van
- Quickly switch the van between common states (driving, parked, quiet night)
- A clean way to group automations later without building everything at once

## Extra hardware required
- None

## Install / best next step
- HA package: `homeassistant/packages/roamcore_mode.yaml`

## Links
- (Add examples later)

---

> **SUPERSEDED — 2026-08-03.** The 18-line tier-a claim stub at this path has been promoted into a tier-b recipe connection at [`connections/mode/`](../../../../connections/mode/). The legacy tier-a "RoamCore native" claim is **honest-upstream-truth**: RoamCore ships **no** native mode engine today; the contract layer + the recipe + the §9 MANDATORY automations are the canonical RoamCore contribution; the upstream engines are HA core `input_select` + `input_boolean` + `input_text` + `input_button` + `input_number` helpers (since 2022.x) + the HA core `template:` sensor + `template:` binary_sensor wrappers + the HA core Conversation agent (since 2022.x — the canonical upstream opt-in AI path) + the optional operator-selected LLM add-ons (since 2023.x). Replaced by the tier-b recipe connection; see [`connections/mode/` README](../../../../connections/mode/README.md) + [`connections/mode/docs/recipe.md`](../../../../connections/mode/docs/recipe.md). Wave 3 #61, PR #65.
