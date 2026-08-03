# Water tanks (fresh/grey) monitoring

> **SUPERSEDED — Wave 3 #50 (2026-07-30).** This legacy tier-c
> placeholder spec has been promoted to a tier-b recipe connection at
> [`connections/water-tanks/`](../../connections/water-tanks/) (PR
> #51). The new connection ships a 17-tile vendor-neutral
> `rc_water_*` contract, a full howto recipe covering Path A
> (ESPHome tank sensor node), Path B (Shelly UNI + ADC probe), and
> Path C (cloud-bridged level sensor — SeeLevel / Garnet / Mopeka /
> Lippert), five MANDATORY safety interlocks (leak detected / freeze
> risk / fresh empty / pump running too long / mode-aware lockouts),
> six automations, eight troubleshooting entries, and the privacy +
> tier-a promotion outline. The legacy content below is preserved
> for historical context only — do NOT wire a new install from this
> doc; use the recipe + contract layer in the connection folder.

**Replaced by:** [`connections/water-tanks/`](../../connections/water-tanks/)

**Recipe:** [`connections/water-tanks/docs/recipe.md`](../../connections/water-tanks/docs/recipe.md)

---

**Support tier:** C (manual / varies)

## What this is
A placeholder for common water monitoring approaches (fresh/grey tank levels, pump runtime, leak sensors). RoamCore doesn't ship a single mandated hardware solution here yet.

## Why it's useful in a van
- Avoid running out of water unexpectedly
- Plan refill/dump stops
- Get alerts for leaks or pump running too long

## Extra hardware required
Varies by setup (tank level sensors, flow sensor, leak sensors).

## Install / best next step
- Add your preferred sensors/integration, then wire the resulting entities into your dashboard.

## Links
- (Add recommended hardware + HA guides/videos here later)