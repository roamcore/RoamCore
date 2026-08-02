# Approach + underbody lights (welcome home)

> **SUPERSEDED — Wave 3 #52 (2026-08-02).** This legacy tier-c
> placeholder spec has been promoted to a tier-b recipe connection at
> [`connections/approach-lights/`](../../connections/approach-lights/) (PR
> #N). The new connection ships a 12-tile vendor-neutral
> `rc_lighting_*` contract, a full howto recipe covering Path A
> (smart switches / smart bulbs — Shelly / Zooz / Aeotec / Hue / LIFX /
> IKEA TRÅDFRI / generic-Zigbee / generic-Z-Wave / Tuya), Path B
> (generic relay + HA template light), and Path C (Hue Bridge / Lutron
> Caséta / IKEA TRÅDFRI / Bond Home hub), five automations (first-
> arrival-after-dark / run-on-demand / auto-stop-after-N-min /
> camera-override-on-frigate-person / stealth-mode-suppression), and
> the privacy + tier-a promotion outline. The legacy content below is
> preserved for historical context only — do NOT wire a new install
> from this doc; use the recipe + contract layer in the connection
> folder.

**Replaced by:** [`connections/approach-lights/`](../../connections/approach-lights/)

**Recipe:** [`connections/approach-lights/docs/recipe.md`](../../connections/approach-lights/docs/recipe.md)

---

**Support tier:** C

Turn on exterior/underbody lights automatically when you approach the van after dark, so you can see where you’re stepping and feel like the van is “welcoming you home”.

## What you need
- Any controllable exterior/underbody lights (relay, smart switch, or lighting controller)
- A presence signal (see: Presence detection feature)
- Optional: an “after sunset” signal (time or light sensor)

## What RoamCore would do
- Detect a **first arrival** event (nobody → someone home)
- If it’s dark, run a short “approach” lighting scene:
  - Underbody ON for N minutes
  - Porch/entry light ON
  - Optional: soft interior entry lighting

## Common automations (ideas)
- Only trigger when arriving (not when already home)
- Disable in “Stealth” mode
- Flash/brighten only if a camera sees a person at night