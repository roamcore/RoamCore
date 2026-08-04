# Map

Live location, trip history, GPS tracking, and the on-van map tile.

<div class="rc-card-grid">
  <a class="rc-card" href="map-dashboard.md">
    <div class="rc-card__title">🗺 Map dashboard</div>
    <div class="rc-card__body">The main map tile on the dashboard — where the van is right now.</div>
  </a>
  <a class="rc-card" href="amenities-overlay.md">
    <div class="rc-card__title">📍 Amenities overlay</div>
    <div class="rc-card__body">See nearby water taps, laundrettes, dump points, campsites, gyms.</div>
  </a>
  <a class="rc-card" href="traccar.md">
    <div class="rc-card__title">📡 Traccar (GPS tracking)</div>
    <div class="rc-card__body">Self-hosted Traccar integration for van-to-cloud GPS tracking.</div>
  </a>
  <a class="rc-card" href="roamcore-tileserver-addon.md">
    <div class="rc-card__title">🗺 RoamCore TileServer add-on</div>
    <div class="rc-card__body">Self-hosted map tile server so the dashboard works offline.</div>
  </a>
  <a class="rc-card" href="traccar-init-addon.md">
    <div class="rc-card__title">🚀 Traccar Init add-on</div>
    <div class="rc-card__body">First-boot provisioning for the Traccar add-on stack.</div>
  </a>
  <a class="rc-card" href="traccar-proxy-addon.md">
    <div class="rc-card__title">🔌 Traccar Proxy add-on</div>
    <div class="rc-card__body">Reverse-proxy add-on that lets the dashboard talk to Traccar.</div>
  </a>
  <a class="rc-card" href="mock-location-and-tracks.md">
    <div class="rc-card__title">🎭 Mock location + tracks</div>
    <div class="rc-card__body">Dev/demo mode: fake location + tracks for showing off the dashboard.</div>
  </a>
  <a class="rc-card" href="trip-local.md">
    <div class="rc-card__title">📁 Trip Local</div>
    <div class="rc-card__body">Local GPX / local trip tools — keep trip data on the van.</div>
  </a>
  <a class="rc-card" href="trip-wrapped.md">
    <div class="rc-card__title">🎁 Trip Wrapped</div>
    <div class="rc-card__body">Route recap report — your year in trips, generated locally.</div>
  </a>
</div>

## What works offline

RoamCore's map dashboard is designed to work offline. The TileServer
add-on serves cached tiles locally; amenities overlay falls back to a
cached set; trip data stays on the van.