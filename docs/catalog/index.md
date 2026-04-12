# Catalog

Scroll, pick a category, and explore what you can add to your van.

<div data-rc-filter-root>
  <div class="rc-filter">
    <div class="rc-chips">
      <a class="rc-chip active" href="#" data-rc-tier="all">All</a>
      <a class="rc-chip a" href="#" data-rc-tier="a">Tier A</a>
      <a class="rc-chip b" href="#" data-rc-tier="b">Tier B</a>
      <a class="rc-chip c" href="#" data-rc-tier="c">Tier C</a>
    </div>
    <input type="text" placeholder="Search… (e.g. victron, tailscale, traccar)" data-rc-filter-q />
    <a class="rc-chip" href="#" data-rc-filter-clear>Clear</a>
    <div class="rc-filter-meta">Showing <b data-rc-filter-counter>0</b> items</div>
  </div>

  <div class="rc-grid">
    <!-- Power -->
    <a class="rc-card" data-tier="a" data-tags="power,victron" data-title="Victron" href="power/victron.md"><div class="rc-card-title">Victron</div><div class="rc-card-sub">Battery SOC, solar watts, charging health.</div></a>
    <a class="rc-card" data-tier="a" data-tags="power,victron,addon" data-title="Victron Auto add-on" href="power/victron-auto-addon.md"><div class="rc-card-title">Victron Auto add-on</div><div class="rc-card-sub">Backend connector used by RoamCore.</div></a>

    <!-- Map -->
    <a class="rc-card" data-tier="a" data-tags="map,traccar" data-title="Traccar" href="map/traccar.md"><div class="rc-card-title">Traccar</div><div class="rc-card-sub">Reliable tracking + trip history.</div></a>
    <a class="rc-card" data-tier="a" data-tags="map,trip" data-title="Trip Wrapped" href="map/trip-wrapped.md"><div class="rc-card-title">Trip Wrapped</div><div class="rc-card-sub">Shareable trip recap report.</div></a>
    <a class="rc-card" data-tier="a" data-tags="map,offline,tiles" data-title="Offline tileserver" href="map/offline-tileserver.md"><div class="rc-card-title">Offline maps / tileserver</div><div class="rc-card-sub">Maps that still work without internet.</div></a>

    <!-- Networking / Remote -->
    <a class="rc-card" data-tier="a" data-tags="networking,openwrt" data-title="OpenWrt" href="networking/openwrt-controls.md"><div class="rc-card-title">OpenWrt</div><div class="rc-card-sub">WAN status + connectivity sensors.</div></a>
    <a class="rc-card" data-tier="c" data-tags="networking,peplink" data-title="Peplink" href="networking/peplink.md"><div class="rc-card-title">Peplink</div><div class="rc-card-sub">Multi‑WAN router monitoring ideas.</div></a>
    <a class="rc-card" data-tier="c" data-tags="networking,teltonika" data-title="Teltonika" href="networking/teltonika.md"><div class="rc-card-title">Teltonika</div><div class="rc-card-sub">LTE/5G router monitoring ideas.</div></a>
    <a class="rc-card" data-tier="b" data-tags="remote,tailscale" data-title="Tailscale" href="remote-access/tailscale.md"><div class="rc-card-title">Tailscale</div><div class="rc-card-sub">Secure remote access without port forwards.</div></a>

    <!-- Safety -->
    <a class="rc-card" data-tier="a" data-tags="safety,automations" data-title="Smart Automations" href="safety/smart-automations.md"><div class="rc-card-title">Smart Automations</div><div class="rc-card-sub">One-click safety/comfort automations.</div></a>
    <a class="rc-card" data-tier="b" data-tags="safety,co,smoke,gas" data-title="Smoke/CO/Gas sensors" href="safety/smoke-co-gas-sensors.md"><div class="rc-card-title">Smoke / CO / Gas</div><div class="rc-card-sub">Early warnings + notifications.</div></a>
    <a class="rc-card" data-tier="b" data-tags="safety,locks,deadbolt" data-title="Deadbolts" href="safety/deadbolts.md"><div class="rc-card-title">Deadbolts</div><div class="rc-card-sub">Lock state + alerts + routines.</div></a>

    <!-- Vehicle -->
    <a class="rc-card" data-tier="c" data-tags="vehicle,obd,wican" data-title="WiCAN Pro" href="vehicle-obd/wican-pro.md"><div class="rc-card-title">WiCAN Pro (OBD2)</div><div class="rc-card-sub">Vehicle telemetry + early warnings.</div></a>
  
    <!-- Audio / Homelab -->
    <a class="rc-card" data-tier="b" data-tags="audio,music" data-title="Music Assistant" href="audio-media/music-assistant.md"><div class="rc-card-title">Music Assistant</div><div class="rc-card-sub">Unified audio control.</div></a>
    <a class="rc-card" data-tier="b" data-tags="homelab,nas" data-title="NAS" href="homelab/nas.md"><div class="rc-card-title">NAS</div><div class="rc-card-sub">Local backups, media, CCTV storage.</div></a>
    <a class="rc-card" data-tier="b" data-tags="homelab,dns,pihole" data-title="Pi-hole" href="homelab/pi-hole.md"><div class="rc-card-title">Pi-hole</div><div class="rc-card-sub">Save bandwidth with DNS blocking.</div></a>
    <a class="rc-card" data-tier="b" data-tags="homelab,dns,adguard" data-title="AdGuard Home" href="homelab/adguard-home.md"><div class="rc-card-title">AdGuard Home</div><div class="rc-card-sub">DNS blocking alternative to Pi-hole.</div></a>

    <!-- Bed lift -->
    <a class="rc-card" data-tier="c" data-tags="bedlift,diy" data-title="DIY bed lift" href="bed-lift/diy-bedlift.md"><div class="rc-card-title">DIY bed lift</div><div class="rc-card-sub">Actuators/winch with safety interlocks.</div></a>
    <a class="rc-card" data-tier="c" data-tags="bedlift,happijac" data-title="HappiJac" href="bed-lift/happijac.md"><div class="rc-card-title">HappiJac bed lift</div><div class="rc-card-sub">OEM lift control ideas.</div></a>
  </div>
</div>

<div class="rc-grid">
  <a class="rc-card" href="power/README.md"><div class="rc-card-title">Power</div><div class="rc-card-sub">Batteries, solar, inverter/charger, and “can I run this?” confidence.</div></a>
  <a class="rc-card" href="water/README.md"><div class="rc-card-title">Water</div><div class="rc-card-sub">Fresh/grey levels, pump behavior, leaks, and usage trends.</div></a>
  <a class="rc-card" href="map/README.md"><div class="rc-card-title">Map</div><div class="rc-card-sub">Location, trips, tracking, offline maps, and route history.</div></a>
  <a class="rc-card" href="weather/README.md"><div class="rc-card-title">Weather</div><div class="rc-card-sub">Forecasts, alerts, and planning around conditions.</div></a>
  <a class="rc-card" href="time/README.md"><div class="rc-card-title">Time</div><div class="rc-card-sub">Schedules, quiet hours, bedtime routines, and time zones.</div></a>
  <a class="rc-card" href="safety/README.md"><div class="rc-card-title">Safety</div><div class="rc-card-sub">CO/smoke/gas, leaks, low battery, and critical alerts.</div></a>
  <a class="rc-card" href="networking/README.md"><div class="rc-card-title">Networking</div><div class="rc-card-sub">Starlink/LTE/Wi‑Fi, failover, and connection health.</div></a>
  <a class="rc-card" href="remote-access/README.md"><div class="rc-card-title">Remote Access</div><div class="rc-card-sub">Secure ways to reach your van from anywhere.</div></a>
  <a class="rc-card" href="cctv/README.md"><div class="rc-card-title">CCTV</div><div class="rc-card-sub">Cameras, recording, and quick “check outside” workflows.</div></a>
  <a class="rc-card" href="hvac/README.md"><div class="rc-card-title">HVAC</div><div class="rc-card-sub">Heating/cooling and comfort automation.</div></a>
  <a class="rc-card" href="fans/README.md"><div class="rc-card-title">Fans</div><div class="rc-card-sub">Airflow, condensation control, and simple triggers.</div></a>
  <a class="rc-card" href="lighting/README.md"><div class="rc-card-title">Lighting</div><div class="rc-card-sub">Scenes, dimming, and one‑tap “night mode”.</div></a>
  <a class="rc-card" href="audio-media/README.md"><div class="rc-card-title">Audio/Media</div><div class="rc-card-sub">Speakers, music systems, and media control.</div></a>
  <a class="rc-card" href="vehicle-obd/README.md"><div class="rc-card-title">Vehicle OBD</div><div class="rc-card-sub">Engine/vehicle telemetry and early-warning alerts.</div></a>
  <a class="rc-card" href="bed-lift/README.md"><div class="rc-card-title">Bed Lift</div><div class="rc-card-sub">DIY or OEM lifts with safety interlocks.</div></a>
  <a class="rc-card" href="nfc-tags/README.md"><div class="rc-card-title">NFC Tags</div><div class="rc-card-sub">Tap-to-run routines: bedtime, leave camp, lights off.</div></a>
  <a class="rc-card" href="level-sensor/README.md"><div class="rc-card-title">Level Sensor</div><div class="rc-card-sub">Pitch/roll and “are we level?” status.</div></a>
  <a class="rc-card" href="ai/README.md"><div class="rc-card-title">AI</div><div class="rc-card-sub">System summaries and safe agent-style control.</div></a>
  <a class="rc-card" href="homelab/README.md"><div class="rc-card-title">Homelab</div><div class="rc-card-sub">Local services: NAS, ad-blocking, backups, and more.</div></a>
</div>

## Tagging / design rules (Bernard)
- **Folder title = primary tag** (e.g. `power/`, `connectivity/`, `safety/`).
- **Support tier tag:**
  - **A** = RoamCore native (we own it; supported)
  - **B** = Home Assistant supported integration (we document setup)
  - **C** = Custom/manual (no support; shown for inspiration/potential)
- **Extra hardware required:** call out explicitly (assume user has HA only; no RoamCore hardware).
- **Install button:** clear, coloured, obvious CTA (either one-click install or best link).
- **Links section:** always at bottom (vanlife-specific where possible).

## Status
- Catalog content will be filled once the folder headers + item list are provided.
- MkDocs/Pages build will be added after the content + folder structure is stable.
