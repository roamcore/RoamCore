# Electronic valves + auto tank switching

> **SUPERSEDED — Wave 3 #51 (2026-07-30).** This legacy tier-c
> placeholder spec has been promoted to a tier-b recipe connection at
> [`connections/electronic-valves/`](../../connections/electronic-valves/)
> (PR #54). The new connection ships an 18-tile vendor-neutral
> `rc_water_valve_*` contract, a full howto recipe covering Path A
> (ESPHome valve node) + Path B (generic relay + HA template valve),
> seven automations (auto-switch-to-aux-tank when fresh < 5 % + auto-
> switch-back-to-primary when aux < 5 % + auto-close-grey-after-N-
> min + leak-detected-close-fresh-open-grey + freeze-risk-close-all
> + low-voltage-lockout + mode-aware scheduling), six MANDATORY
> safety interlocks (leak detected / freeze risk / low-voltage
> lockout / auto-close grey / mode-aware lockouts / valve stuck-
> open detector), eight troubleshooting entries, and the privacy +
> tier-a promotion outline. The legacy content below is preserved
> for historical context only — do NOT wire a new install from this
> doc; use the recipe + contract layer in the connection folder.

**Replaced by:** [`connections/electronic-valves/`](../../connections/electronic-valves/)

**Recipe:** [`connections/electronic-valves/docs/recipe.md`](../../connections/electronic-valves/docs/recipe.md)

---

**Support tier:** C

Use electronically controlled valves to automate water routing: switching between primary/aux tanks, closing a grey valve if it’s left open, and protecting the system in freezing conditions.

## What you need
- Electrically actuated valves (12V/24V) + safe drivers (relays/IO modules)
- Tank level sensors (primary + auxiliary)
- Optional: temperature sensors (freeze protection)

## What RoamCore would do
- Expose a clear state model:
  - active tank (primary/aux)
  - grey valve open/closed
  - freeze risk (yes/no)
- Provide one-tap actions (switch tanks, close grey valve)

## Common automations (ideas)
- Switch to auxiliary tank when primary reaches 0%
- Close the grey valve if it’s left open for N minutes
- When freeze risk is detected: close valves / run safe drain / enable tank heater (build dependent)

