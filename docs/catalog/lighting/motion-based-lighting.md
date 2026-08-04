# Motion-based lighting

> **SUPERSEDED — Wave 3 (2026-08-02).** This legacy tier-c placeholder spec has been promoted to a tier-b recipe connection at [`connections/motion-based-lighting/`](../../../connections/motion-based-lighting/). The new connection ships a 12-tile vendor-neutral `rc_lighting_*` contract, a full howto recipe covering motion sensor integration (Aqara / Hue / generic MQTT / ESPHome), five automations (motion-on-arrival + motion-night-mode + motion-mode-aware + motion-battery-aware + motion-safety-interlock), and the privacy + tier-a promotion outline. The legacy tier-c content below is preserved for historical context only — do NOT wire a new install from this doc; use the recipe + contract layer in the connection folder.

**Replaced by:** [`connections/motion-based-lighting/`](../../../connections/motion-based-lighting/)

**Recipe:** [`connections/motion-based-lighting/docs/recipe.md`](../../../connections/motion-based-lighting/docs/recipe.md)

---

Motion-based lighting — RoamCore catalog entry.

## What you need

- Zigbee / Z-Wave exterior light or relay ($20–$60)
- Shelly 1 / Shelly Plus 1 ($15–$25)

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature motion-based-lighting`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What it shows on your dashboard

- A Motion-based lighting tile that updates automatically.
