# Catalog

Every RoamCore feature, grouped by what it does for you. Click into any feature to see the install steps and what it shows on the dashboard.

## Browse by category

- **[Automation](#automation)** — 3 features. Recipes, scenes, and the automations that make the van feel like it has a mind of its own.
- **[Comfort](#comfort)** — 7 features. Climate, fans, lights, beds, audio — the small things that make the van feel like home.
- **[Connectivity](#connectivity)** — 5 features. Internet, cellular, satellite, and the secure ways to reach the van from anywhere.
- **[Location](#location)** — 4 features. GPS, maps, presence, and knowing where the van is (and who's in it).
- **[Maintenance](#maintenance)** — 2 features. Diagnostics, leveling, OBD — keeping the van itself healthy.
- **[Misc](#misc)** — 3 features. Tools that don't fit a single bucket — DNS, NAS, time sync, and more.
- **[Safety](#safety)** — 3 features. Smoke, CO, gas, locks, and the alerts that keep you and the van out of trouble.
- **[Security](#security)** — 1 feature. Locks, CCTV, access control.
- **[Water](#water)** — 2 features. Tanks, pumps, valves, leaks.

---

## Automation

_Recipes, scenes, and the automations that make the van feel like it has a mind of its own._

| Feature | Tier | Install | What it does |
|---|---|---|---|
| [Advanced mode](automation/advanced-mode.md) ⚠️ | **B** | one line | RoamCore includes an Advanced Mode toggle that can reveal extra controls and diagnostics without cluttering the default UI. Keeps the dashboard clean for daily use. Still gives… |
| [Demo mode](automation/demo-mode.md) ⚠️ | **B** | one line | Demo Mode lets RoamCore show example values when critical sensors are missing, so the UI still looks and feels complete during setup or demos. |
| [Mode](automation/mode.md) ⚠️ | **B** | one line | Quickly switch the van between common states (driving, parked, quiet night). A clean way to group automations later without building everything at once. |

## Comfort

_Climate, fans, lights, beds, audio — the small things that make the van feel like home._

| Feature | Tier | Install | What it does |
|---|---|---|---|
| [Approach lights](comfort/approach-lights.md) | **B** | one line | Approach lights (welcome-home exterior + underbody lighting) — the universal small-comfort van automation: open the door after dark, the underbody + entry + soft-interior… |
| [Fans](comfort/fans.md) | **B** | one line | Fans are a simple upgrade that massively improves comfort: airflow, condensation control, cooking smells, and keeping the van livable in warm weather. |
| [HVAC basics](comfort/hvac-basics.md) ⚠️ | **B** | one line | HVAC basics — cabin heating/cooling foundations for vans — is the umbrella for thermostat + diesel heater + rooftop AC + cabin ventilation control. |
| [Happijac bed lift](comfort/happijac.md) ⚠️ | **B** | one line | Bed lift control — van bed up / down — is the foundation of every sleep-cycle automation in a van with a Happijac (or any 2-relay + 2-limit-switch bed lift: LCI Happijac, DIY… |
| [Heated floors + engine pre-heat](comfort/heated-floors.md) ⚠️ | **B** | one line | Heated floors + engine pre-heat — cold-weather comfort controls for vans — are the foundation of every "Warm up" automation in winter van life. |
| [Motion-based lighting](comfort/motion-based-lighting.md) ⚠️ | **B** | one line | Motion-based lighting (driving + arrival) — the umbrella for ignition-driven interior auto-off + ignition-driven soft-interior on stop + presence-driven arrival cue +… |
| [Music Assistant](comfort/music-assistant.md) ⚠️ | **B** | hacs | Music Assistant is a provider- agnostic multi-room audio orchestrator very popular in HA installs — it unifies Spotify, Apple Music, TuneIn/radio, local files, and… |

## Connectivity

_Internet, cellular, satellite, and the secure ways to reach the van from anywhere._

| Feature | Tier | Install | What it does |
|---|---|---|---|
| [Peplink](connectivity/peplink.md) | **B** | manual | Peplink Balance / MAX / EP-series routers are rugged, configurable multi-WAN gateways very popular in van life — they handle LTE/5G + Starlink + campground Wi-Fi with automatic… |
| [Pi-hole or AdGuard Home](connectivity/dns-blocker.md) | **B** | one line | Pi-hole and AdGuard Home are self-hosted DNS-level ad/tracker blockers (DNS sinkhole + blocklist + per-client query stats). |
| [Remote access](connectivity/remote-access.md) | **B** | hacs | Check the van from anywhere: see sensor status, view cameras, get alerts, or (optionally) control systems. |
| [Starlink](connectivity/starlink.md) | **B** | manual | Starlink is a self-hosted mobile-internet terminal (Gen-2/Gen-3 dish + router). |
| [Teltonika](connectivity/teltonika.md) | **B** | manual | Teltonika RUT-series LTE/5G routers are rugged, configurable mobile-internet gateways widely used in van life. |

## Location

_GPS, maps, presence, and knowing where the van is (and who's in it)._

| Feature | Tier | Install | What it does |
|---|---|---|---|
| [Amenities overlay](location/amenities-overlay.md) | **B** | one line | Amenities overlay (nearby places) — See nearby things you actually care about when living on the road — water taps, laundrettes, gyms, dump points, campsites, supermarkets, and… |
| [Bluetooth / Wi-Fi presence](location/bluetooth-wifi-presence.md) ⚠️ | **B** | one line | Presence detection — who is currently home in the van — is the foundation of every occupied/away automation in RoamCore: shut down inverter + pump when nobody is home, turn on… |
| [Map dashboard](location/map-dashboard.md) ⚠️ | **A** | one line | RoamCore provides a map experience inside Home Assistant, including current location and route/trip context. Quick 'where are we / where did we park?' view. Nice context for… |
| [Mock location + track replay](location/mock-location-and-tracks.md) ⚠️ | **A** | manual | Mock location + track replay is the dev/demo polyline generator for the RoamCore map page. |

## Maintenance

_Diagnostics, leveling, OBD — keeping the van itself healthy._

| Feature | Tier | Install | What it does |
|---|---|---|---|
| [In-cab tablet dashboard](maintenance/in-cab-tablet-dashboard.md) ⚠️ | **C** | manual | Mount a small tablet in the cab that shows the handful of controls and readouts you care about while driving + a richer control surface on arrival + a battery-friendly lock… |
| [Leveling](maintenance/leveling.md) | **B** | one line | Better sleep and cooking. Quick 'good enough' check without guessing. |

## Misc

_Tools that don't fit a single bucket — DNS, NAS, time sync, and more._

| Feature | Tier | Install | What it does |
|---|---|---|---|
| [Network Attached Storage](misc/nas.md) | **B** | one line | A NAS gives RoamCore a reliable local-storage target for media, camera footage, backups, and logs — especially valuable when you don't want to depend on cloud services. |
| [Time](misc/time-atomic.md) | **C** | one line | Keep HA's clock accurate even when offline (in a van with intermittent connectivity). |
| [Timezone geolocator](misc/timezone-geolocator.md) ⚠️ | **C** | hacs | Keep HA's system timezone correct as the van travels across regions so that time-based automations (sun events + `now` + `today_at`) keep working. |

## Safety

_Smoke, CO, gas, locks, and the alerts that keep you and the van out of trouble._

| Feature | Tier | Install | What it does |
|---|---|---|---|
| [Deadbolts](safety/deadbolts.md) | **B** | one line | Smart deadbolts — van door lock control for vans — are the "did I forget to lock the van?" answer. |
| [Smart Automations](safety/smart-automations.md) ⚠️ | **B** | one line | Smart automations are the day-to-day convenience layer of a RoamCore van: 17 prebuilt Home Assistant automations that handle mode-aware transitions (Night Mode Stealth/Auto),… |
| [Smoke / CO / gas safety sensors](safety/smoke-co-gas-sensors.md) | **B** | one line | Smoke / CO / gas safety sensors — van life safety monitoring — are the foundation of every "is it safe to sleep in the van?" question. |

## Security

_Locks, CCTV, access control._

| Feature | Tier | Install | What it does |
|---|---|---|---|
| [NFC tags](security/nfc-tags.md) | **C** | hacs | Cheap + simple NFC tags make the van feel magical: tap your phone to run a scene (Lights off, Bedtime, Leave camp). |

## Water

_Tanks, pumps, valves, leaks._

| Feature | Tier | Install | What it does |
|---|---|---|---|
| [Electronic valves + auto tank switching](water/electronic-valves.md) ⚠️ | **B** | one line | Electronic valves + auto tank switching — fresh / aux tank routing, grey drain valve auto-close, freeze-risk / leak-detected / low- voltage lockout safety interlocks — is the… |
| [Water tanks](water/water-tanks.md) ⚠️ | **B** | one line | Water tanks — fresh + grey water telemetry + pump runtime + leak detection + freeze-risk monitoring for vans — is the vendor-neutral surface that turns "is the fresh tank still… |

