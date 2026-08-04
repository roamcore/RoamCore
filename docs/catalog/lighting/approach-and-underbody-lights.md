# Approach lights

> **SUPERSEDED — Wave 3 #52 (2026-08-02).** This legacy tier-c placeholder spec has been promoted to a tier-b recipe connection at [`connections/approach-lights/`](../../../connections/approach-lights/) (PR #N). The new connection ships a 12-tile vendor-neutral `rc_lighting_*` contract, a full howto recipe covering Path A (smart switches / smart bulbs — Shelly / Zooz / Aeotec / Hue / LIFX / generic MQTT) + Path B (12 V relay + HA template light), seven automations (sunset-triggered welcome + arrival-home + scene-aware + motion-tie-in + battery-aware + mode-aware + safety-interlock), and the privacy + tier-a promotion outline. The legacy tier-c content below is preserved for historical context only — do NOT wire a new install from this doc; use the recipe + contract layer in the connection folder.

**Replaced by:** [`connections/approach-lights/`](../../../connections/approach-lights/)

**Recipe:** [`connections/approach-lights/docs/recipe.md`](../../../connections/approach-lights/docs/recipe.md)

---

Approach lights (welcome-home exterior + underbody lighting) — the universal small-comfort van automation: open the door after dark, the underbody + entry + soft-interior lights come on for a configurable duration (default 2 min) so you can see where you're stepping and feel like the van is welcoming you home.

## What you need

- Zigbee / Z-Wave exterior light or relay ($20–$60)
- Shelly 1 / Shelly Plus 1 ($15–$25)

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature approach-lights`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What it shows on your dashboard

- A Approach lights tile that updates automatically.
