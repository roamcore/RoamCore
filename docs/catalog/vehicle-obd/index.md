# Vehicle OBD

OBD2 readers and the in-cab driving tablet dashboard.

<div class="rc-card-grid">
  <a class="rc-card" href="wican-pro.md">
    <div class="rc-card__title">🚗 WiCAN Pro (OBD2)</div>
    <div class="rc-card__body">MeatPi WiCAN Pro OBD2 reader → CAN bus → Home Assistant sensors.</div>
  </a>
  <a class="rc-card" href="in-cab-tablet-dashboard.md">
    <div class="rc-card__title">📱 In-cab tablet dashboard</div>
    <div class="rc-card__body">Driving-focused tablet dashboard for the cab — speed, temp, gear, fuel.</div>
  </a>
</div>

## How it works

WiCAN Pro plugs into the OBD2 port, talks to the CAN bus, and publishes
sensor data over MQTT. RoamCore's recipe layer turns those sensors
into driving dashboard tiles.