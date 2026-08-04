# HVAC basics

> **SUPERSEDED — Wave 3 #49 (2026-08-02).** This legacy tier-c page has been promoted to a tier-b recipe connection at [`connections/hvac-basics/`](../../../connections/hvac-basics/) (PR #52). The new connection ships a 12-tile vendor-neutral `rc_climate_*` contract, a full howto recipe covering diesel heater Path A + AC inverter Path B + generic thermostat Path C, seven automations (mode-aware scheduling + freeze-risk lockouts + inverter-idle guard + presence-aware temperature + battery-aware pre-heat + source-failover + safety interlocks), and the privacy + tier-a promotion outline. The legacy tier-c content below is preserved for historical context only — do NOT wire a new install from this doc; use the recipe + contract layer in the connection folder.

**Replaced by:** [`connections/hvac-basics/`](../../../connections/hvac-basics/)

**Recipe:** [`connections/hvac-basics/docs/recipe.md`](../../../connections/hvac-basics/docs/recipe.md)

---

HVAC basics — RoamCore catalog entry.

## What you need

- Nothing extra — uses what's already in the van.

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature hvac-basics`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What it shows on your dashboard

- A HVAC basics tile that updates automatically.