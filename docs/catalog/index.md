# Catalog

Stuff you can add to your van. Pick what you want and install it.

## Automation

- **[Mode](automation/mode.md)** — Quickly switch the van between common states (driving, parked, quiet night). A clean way to group automations later without building everything at once.

## Comfort

- **[Approach lights](comfort/approach-lights.md)** — Approach lights (welcome-home exterior + underbody lighting) — the universal small-comfort van automation: open the door after dark, the underbody + entry + soft-interior lights come on for a configurable duration (default 2 min) so you can see where you're stepping and feel like the van is welcoming you home.
- **[Fans](comfort/fans.md)** — Fans are a simple upgrade that massively improves comfort: airflow, condensation control, cooking smells, and keeping the van livable in warm weather.
- **[HVAC basics](comfort/hvac-basics.md)** — HVAC basics — RoamCore catalog entry.
- **[Happijac bed lift](comfort/happijac.md)** — Bed lift control — van bed up / down — is the foundation of every sleep-cycle automation in a van with a Happijac (or any 2-relay + 2-limit-switch bed lift: LCI Happijac, DIY linear actuators, winch + strap, etc.
- **[Heated floors + engine pre-heat](comfort/heated-floors.md)** — Heated floors + engine pre-heat — cold-weather comfort controls for vans — are the foundation of every "Warm up" automation in winter van life.
- **[Motion-based lighting](comfort/motion-based-lighting.md)** — Motion-based lighting — RoamCore catalog entry.
- **[Music Assistant](comfort/music-assistant.md)** — Music Assistant is a provider- agnostic multi-room audio orchestrator very popular in HA installs — it unifies Spotify, Apple Music, TuneIn/radio, local files, and Chromecast/AirPlay/Sonos receivers behind a single "play everywhere" surface with per-zone controls.

## Connectivity

- **[Peplink](connectivity/peplink.md)** — Peplink Balance / MAX / EP-series routers are rugged, configurable multi-WAN gateways very popular in van life — they handle LTE/5G + Starlink + campground Wi-Fi with automatic failover and load balancing, giving a single stable "van Wi-Fi" network.
- **[Pi-hole or AdGuard Home](connectivity/dns-blocker.md)** — Pi-hole and AdGuard Home are self-hosted DNS-level ad/tracker blockers (DNS sinkhole + blocklist + per-client query stats).
- **[Remote access](connectivity/remote-access.md)** — Check the van from anywhere: see sensor status, view cameras, get alerts, or (optionally) control systems.
- **[Starlink](connectivity/starlink.md)** — Starlink is a self-hosted mobile-internet terminal (Gen-2/Gen-3 dish + router).
- **[Teltonika](connectivity/teltonika.md)** — Teltonika RUT-series LTE/5G routers are rugged, configurable mobile-internet gateways widely used in van life.
- **[WiCAN Pro](connectivity/wican-pro.md)** — RoamCore auto-discovers it on the same network, polls it for engine RPM, speed, coolant temperature, throttle position, fuel level, battery voltage and a dozen other generic OBD2 readings, and saves them to a local time-series database. The dashboard populates automatically the moment the device is discovered — no…

## Location

- **[Amenities overlay](location/amenities-overlay.md)** — Amenities overlay (nearby places) — See nearby things you actually care about when living on the road — water taps, laundrettes, gyms, dump points, campsites, supermarkets, and more — directly on the RoamCore map.
- **[Bluetooth / Wi-Fi presence](location/bluetooth-wifi-presence.md)** — Presence detection — who is currently home in the van — is the foundation of every occupied/away automation in RoamCore: shut down inverter + pump when nobody is home, turn on approach lighting when the first person returns after dark, suppress Stealth-silent-hours actions when only the driver is present, alert…
- **[Map dashboard](location/map-dashboard.md)** — RoamCore provides a map experience inside Home Assistant, including current location and route/trip context. Quick 'where are we / where did we park?' view. Nice context for trips and daily travel. Extra hardware required: None if you already have a `device_tracker` or location source. Install / best next step:…

## Maintenance

- **[In-cab tablet dashboard](maintenance/in-cab-tablet-dashboard.md)** — Mount a small tablet in the cab that shows the handful of controls and readouts you care about while driving + a richer control surface on arrival + a battery-friendly lock screen while parked.
- **[Leveling](maintenance/leveling.md)** — Better sleep and cooking. Quick 'good enough' check without guessing.

## Misc

- **[Network Attached Storage](misc/nas.md)** — A NAS gives RoamCore a reliable local-storage target for media, camera footage, backups, and logs — especially valuable when you don't want to depend on cloud services.
- **[Time](misc/time-atomic.md)** — Keep HA's clock accurate even when offline (in a van with intermittent connectivity).
- **[Timezone geolocator](misc/timezone-geolocator.md)** — Keep HA's system timezone correct as the van travels across regions so that time-based automations (sun events + `now` + `today_at`) keep working.

## Safety

- **[Deadbolts](safety/deadbolts.md)** — Smart deadbolts — van door lock control for vans — are the "did I forget to lock the van?" answer.
- **[Smart Automations](safety/smart-automations.md)** — Smart automations are the day-to-day convenience layer of a RoamCore van: 17 prebuilt Home Assistant automations that handle mode-aware transitions (Night Mode Stealth/Auto), power-aware responses (Low Battery Mode → Camp, Battery Full Alert, Battery Critical Alert, Solar is Crushing It), safety alerts (Inverter…
- **[Smoke / CO / gas safety sensors](safety/smoke-co-gas-sensors.md)** — Smoke / CO / gas safety sensors — van life safety monitoring — are the foundation of every "is it safe to sleep in the van?" question.

## Security

- **[NFC tags](security/nfc-tags.md)** — Cheap + simple NFC tags make the van feel magical: tap your phone to run a scene (Lights off, Bedtime, Leave camp).

## Water

- **[Electronic valves + auto tank switching](water/electronic-valves.md)** — Electronic valves + auto tank switching — fresh / aux tank routing, grey drain valve auto-close, freeze-risk / leak-detected / low- voltage lockout safety interlocks — is the vendor-neutral surface that turns "which tank am I drawing from right now?" + "is the grey valve about to overflow?" + "can I safely open a…
- **[Water tanks](water/water-tanks.md)** — Water tanks — fresh + grey water telemetry + pump runtime + leak detection + freeze-risk monitoring for vans — is the vendor-neutral surface that turns "is the fresh tank still full enough to last the night?" into a dashboard tile + a push notification + a mode-aware automation.

