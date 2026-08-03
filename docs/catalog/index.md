# Catalog

Stuff you can add to your van. Pick what you want and install it.

## Automation

- **[Mode](automation/mode.md)** — Quickly switch the van between common states (driving, parked, quiet night). A clean way to group automations later without building everything at once.

## Comfort

- **[Approach lights](comfort/approach-lights.md)** — Approach lights (welcome-home exterior + underbody lighting) — the universal small-comfort van automation: open the door after dark, the underbody + entry + soft-interior lights come on for a configurable duration (default 2 min) so you can see where you're stepping and feel like the van is welcoming you home.
- **[Fans](comfort/fans.md)** — Fans (vendor-neutral fan-controller umbrella for HA, covering rooftop vent fans + circulation fans + bathroom exhaust fans — rooftop + circulation fans cover the climate-aware airflow + the rain-sensor safety block; bathroom exhaust fans wire as a separate downstream `fan.
- **[HVAC basics](comfort/hvac-basics.md)** — HVAC basics — cabin heating/cooling foundations for vans.
- **[Happijac bed lift](comfort/happijac.md)** — Bed lift control — van bed up / down.
- **[Heated floors + engine pre-heat](comfort/heated-floors.md)** — Heated floors + engine pre-heat — cold-weather comfort controls for vans — are the foundation of every "Warm up" automation in winter van life.
- **[Motion-based lighting](comfort/motion-based-lighting.md)** — Motion-based lighting (driving + arrival).
- **[Music Assistant](comfort/music-assistant.md)** — Music Assistant is a provider- agnostic multi-room audio orchestrator very popular in HA installs — it unifies Spotify, Apple Music, TuneIn/radio, local files, and Chromecast/AirPlay/Sonos receivers behind a single "play everywhere" surface with per-zone controls.

## Connectivity

- **[Peplink](connectivity/peplink.md)** — Peplink Balance / MAX / EP-series routers are rugged, configurable multi-WAN gateways very popular in van life — they handle LTE/5G + Starlink + campground Wi-Fi with automatic failover and load balancing, giving a single stable "van Wi-Fi" network.
- **[Pi-hole or AdGuard Home](connectivity/dns-blocker.md)** — Pi-hole and AdGuard Home are self-hosted DNS-level ad/tracker blockers (DNS sinkhole + blocklist + per-client query stats).
- **[Remote access](connectivity/remote-access.md)** — Remote access (vendor-neutral remote-access umbrella for HA, covering Tailscale + Cloudflare Tunnel + Nabu Casa HA Cloud + Wireguard — operator picks ONE path).
- **[Starlink](connectivity/starlink.md)** — Starlink is a self-hosted mobile-internet terminal (Gen-2/Gen-3 dish + router).
- **[Teltonika](connectivity/teltonika.md)** — Teltonika RUT-series LTE/5G routers are rugged, configurable mobile-internet gateways widely used in van life.

## Location

- **[Amenities overlay](location/amenities-overlay.md)** — Amenities overlay (nearby places) — See nearby things you actually care about when living on the road — water taps, laundrettes, gyms, dump points, campsites, supermarkets, and more — directly on the RoamCore map.
- **[Bluetooth / Wi-Fi presence](location/bluetooth-wifi-presence.md)** — Presence detection — who is currently home in the van.
- **[Map dashboard](location/map-dashboard.md)** — Map dashboard — vendor-neutral map tile + device_tracker aggregation + trip overlay + offline-tile cache.

## Maintenance

- **[In-cab tablet dashboard](maintenance/in-cab-tablet-dashboard.md)** — In-cab tablet dashboard (driving / arrival / lock-screen Lovelace views with ignition-aware auto-switch).
- **[Leveling](maintenance/leveling.md)** — Better sleep and cooking. Quick 'good enough' check without guessing.

## Misc

- **[Network Attached Storage](misc/nas.md)** — A NAS gives RoamCore a reliable local-storage target for media, camera footage, backups, and logs — especially valuable when you don't want to depend on cloud services.
- **[Time](misc/time-atomic.md)** — Keep HA's clock accurate even when offline (in a van with intermittent connectivity).
- **[Timezone geolocator](misc/timezone-geolocator.md)** — Timezone geolocator (location-aware HA timezone).

## Safety

- **[Deadbolts](safety/deadbolts.md)** — Smart deadbolts — van door lock control for vans — are the "did I forget to lock the van?" answer.
- **[Smart Automations](safety/smart-automations.md)** — Smart automations are the day-to-day convenience layer of a RoamCore van: 17 prebuilt Home Assistant automations that handle mode-aware transitions (Night Mode Stealth/Auto), power-aware responses (Low Battery Mode → Camp, Battery Full Alert, Battery Critical Alert, Solar is Crushing It), safety alerts (Inverter…
- **[Smoke / CO / gas safety sensors](safety/smoke-co-gas-sensors.md)** — Smoke / CO / gas safety sensors — van life safety monitoring — are the foundation of every "is it safe to sleep in the van?" question.

## Security

- **[NFC tags](security/nfc-tags.md)** — NFC tags (vendor-neutral NFC-triggered scenes mapped via `tag_id → scene` mapping).

## Water

- **[Electronic valves + auto tank switching](water/electronic-valves.md)** — Electronic valves + auto tank switching — fresh / aux tank routing, grey drain valve auto-close, freeze-risk / leak-detected / low- voltage lockout safety interlocks.
- **[Water tanks](water/water-tanks.md)** — Water tanks — fresh + grey water telemetry + pump runtime + leak detection + freeze-risk monitoring for vans.

