# Power

Batteries, solar, alternator charging, inverter idle, and the whole
Victron stack.

<div class="rc-card-grid">
  <a class="rc-card" href="victron.md">
    <div class="rc-card__title">🔋 Victron (GX + MQTT)</div>
    <div class="rc-card__body">Victron GX device over MQTT — battery, solar, shunt, inverter.</div>
  </a>
  <a class="rc-card" href="victron-auto-addon.md">
    <div class="rc-card__title">🔌 Victron Auto add-on</div>
    <div class="rc-card__body">Backend connector add-on that bridges Victron GX → Home Assistant.</div>
  </a>
  <a class="rc-card" href="victron-mock-addon.md">
    <div class="rc-card__title">🎭 Victron Mock add-on</div>
    <div class="rc-card__body">Demo power data so the dashboard works without real Victron hardware.</div>
  </a>
  <a class="rc-card" href="alternator-charge-control-wakespeed.md">
    <div class="rc-card__title">⚡ Alternator charge (Wakespeed)</div>
    <div class="rc-card__body">Wakespeed / smart regulator control while the engine is running.</div>
  </a>
  <a class="rc-card" href="inverter-idle-shutdown.md">
    <div class="rc-card__title">🔌 Inverter idle shutdown</div>
    <div class="rc-card__body">Auto-shut the inverter when no load is detected — save battery.</div>
  </a>
</div>

## Pick the path that matches your stack

- **Real Victron hardware?** Install `victron` + `victron-auto-addon`.
- **Demo-ing the dashboard?** Install `victron-mock-addon` for safe demo values.
- **Non-Victron (Renogy, Battle Born, etc.)?** Use the MQTT/Modbus recipes in the `connections/power-monitor/` folder.