# HVAC

Heating, cooling, and engine pre-heat recipes.

<div class="rc-card-grid">
  <a class="rc-card" href="hvac-basics.md">
    <div class="rc-card__title">🔥 HVAC basics</div>
    <div class="rc-card__body">Heating/cooling foundations — thermostats, switches, and automations.</div>
  </a>
  <a class="rc-card" href="heated-floors-and-engine-preheat.md">
    <div class="rc-card__title">🔥 Heated floors + engine pre-heat</div>
    <div class="rc-card__body">Schedule floor heat + warm the engine before cold starts.</div>
  </a>
</div>

## What RoamCore does

RoamCore provides the contract layer (`rc_climate_*`) + the recipes for
common van HVAC topologies (diesel heater + AC inverter + floor heat).
The actual hardware integrations stay vendor-neutral.