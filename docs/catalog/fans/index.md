# Fans

> **SUPERSEDED — Wave 3 (2026-08-02).** This legacy tier-c placeholder spec has been promoted to a tier-b recipe connection at [`connections/fans/`](../../../connections/fans/). The new connection ships a vendor-neutral fan controller recipe covering MaxxAir / Fan-Tastic / Hella / generic MQTT / generic template wrapper + the upstream HA core `fan` integration + the HA core `template:` fan wrapper + the HA core `zwave_js` integration + the HA core `mqtt` integration + the rain-sensor safety block. The legacy tier-c content below is preserved for historical context only — do NOT wire a new install from this doc; use the recipe in the connection folder.

**Replaced by:** [`connections/fans/`](../../../connections/fans/)

**Recipe:** [`connections/fans/docs/recipe.md`](../../../connections/fans/docs/recipe.md)

---

Roof and cabin fans with temperature-based automation.

<div class="rc-card-grid">
  <a class="rc-card" href="fans.md">
    <div class="rc-card__title">💨 Fans</div>
    <div class="rc-card__body">Roof + cabin fans with temperature/humidity automations and a dashboard tile.</div>
  </a>
</div>

## What the dashboard shows

- Current fan state (on/off/speed)
- Cabin temperature + humidity
- Auto mode toggle for "vent when hot + sleeping"