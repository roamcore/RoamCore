# Leveling

> **SUPERSEDED — Wave 3 (2026-08-02).** This legacy tier-a claim stub has been promoted to a tier-b recipe connection at [`connections/leveling/`](../../../connections/leveling/). The new connection ships a vendor-neutral pitch/roll + auto-jack + fridge-safe gate recipe over the upstream HA Companion IMU + dedicated MPU-6050 / BNO085 IMU modules + ESPHome IMU nodes + the upstream HA core `template:` sensor wrapper. The legacy tier-a claim stub is preserved for historical context only — the original "RoamCore defines a levelling contract" claim was aspirational and is hereby retracted; the active spec lives in the connection folder.

**Replaced by:** [`connections/leveling/`](../../../connections/leveling/)

**Recipe:** [`connections/leveling/docs/recipe.md`](../../../connections/leveling/docs/recipe.md)

---

Better sleep and cooking. Quick 'good enough' check without guessing.

## What you need

- Phone IMU (no cost — uses the HA Companion app)
- Dedicated MPU-6050 / BNO085 IMU module ($10–$40)

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature leveling`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What it shows on your dashboard

- A Leveling tile that updates automatically.
