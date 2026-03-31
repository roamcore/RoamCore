# RoamCore Roadmap

> The open-source operating system for life on the road.

RoamCore is a pre-configured, fully local, open-source platform that monitors, controls, and automates essential systems in campervans, overlanding rigs, and off-grid vehicles. It brings together Home Assistant, OpenWrt, and Proxmox into a single, opinionated stack that works out of the box — no cloud, no subscriptions, no lock-in.

This roadmap outlines where the project is today, what we're building next, and where we're heading. It's a living document and will evolve as the project matures and the community grows.

---

## Project Direction

RoamCore exists because there's no good middle ground for van tech. You either buy expensive proprietary boxes that do one thing and lock you into a subscription, or you spend weeks cobbling together a DIY Home Assistant setup. We're building the third option: a polished, integrated system that's simple enough for anyone to use, but fully open and extensible for those who want to go deeper.

**Our north star is the non-technical van owner.** Someone who wants to glance at their phone and know their battery level, see where they've been, check if they're parked level, and know their water situation — without learning what MQTT is. Every design decision we make works backwards from that person.

That said, we're building in the open from day one. The project is fully open source and the early releases are targeted at technical users who can contribute feedback, find bugs, and help shape the product before it reaches a wider audience.

---

## How to Use RoamCore Today

There are two ways to run RoamCore, depending on your setup:

### Path 1: RoamCore Dashboard (any Home Assistant install)

If you already have Home Assistant running in your van — on a Raspberry Pi, a mini-PC, or anything else — you can install the RoamCore dashboard and configuration package onto your existing setup. This gives you our pre-built dashboard, integrations, and automations without replacing your current infrastructure.

**What works on any HA install:**
- RoamCore dashboard (power, map, level, weather, trip wrapped export)
- Victron power integration
- GPS trip tracking (via HA companion app or any GPS source)
- Weather and time
- IMU levelling (with compatible hardware)

**What requires RoamCore OS (see Path 2):**
- Integrated LTE/Starlink networking with failover
- Modem-based GPS with cell tower fallback
- OpenWrt networking dashboard and controls
- Full setup wizard

See the install guide in the repo for setup instructions.

### Path 2: RoamCore OS (full stack)

The complete RoamCore experience. A pre-configured Proxmox image running Home Assistant OS and OpenWrt VMs on supported hardware (Protectli VP2430). This gives you everything — integrated cellular connectivity, automatic WAN failover, modem GPS, and the full networking stack, all pre-configured and ready to go.

This is the version that will ship on RoamCore hardware.

---

## Current Status: Beta

RoamCore is in active development. The core features are being built and tested. The software is usable but not yet stable — expect rough edges, breaking changes, and incomplete documentation. We're releasing early because we believe in building in the open and we want feedback from real users in real vans.

**What's working now:**
- Proxmox + HAOS + OpenWrt VM architecture
- Core networking (LTE, Starlink, failover)
- Basic dashboard structure
- Victron power integration (in progress)

---

## Near-Term: MVP Features

These are the features currently being built for the first beta release. They represent the minimum set of functionality needed to make RoamCore genuinely useful in a van.

### Power Monitoring
Integration with Victron Energy systems to display battery state of charge, solar input, load consumption, and charge/discharge status. Pairing via Bluetooth LE with support for VE.Direct and Cerbo GX as alternative connection methods.

### Trip Tracking & Map
Automatic GPS logging with route plotting on OpenStreetMap. Trip statistics including distance, duration, and stop detection. Built on Traccar (self-hosted, open source) running as a Home Assistant add-on. On RoamCore OS, GPS data comes from the integrated LTE modem with cell tower fallback for continuous coverage. On standalone HA installs, GPS data can come from the companion app or any device tracker.

### Trip Wrapped Export
A shareable, "Spotify Wrapped"-style image summarising a trip over a selected date range. Select your dates, hit generate, and get a downloadable PNG with your route map, total distance, stops, and key stats — branded and ready to share.

### Levelling
A visual spirit level on the dashboard using an onboard IMU sensor. One-tap calibration ("park level, tap zero"), with a clear directional indicator showing which way to adjust. Designed to be glanceable — green means level, done.

### Weather
Current conditions and multi-day forecast on the dashboard, powered by Open-Meteo (free, no API key required). Available for use in automations (e.g., close the vent if rain is forecast).

### Time & Location Sync
Automatic timezone detection based on the van's GPS position. The system stays accurate as you cross timezones without manual configuration.

### Dashboard
A clean, mobile-first, dark-mode dashboard with dedicated pages for power, map, level, and weather. Designed to be glanceable — the most important information (battery, connectivity, location) is visible within seconds. Built entirely in YAML for version control and reproducibility.

### Setup Wizard
A guided first-boot experience built as a dedicated dashboard. Walks the user through Wi-Fi configuration, internet source setup, Victron pairing, sensor calibration, and timezone — all from a phone browser, no terminal required.

---

## Medium-Term: Post-MVP

Once the core MVP is stable, these are the next priorities. Some of these are partially designed, others are in research. Timelines are not committed — we'll sequence based on user feedback and contributor interest.

### Networking Dashboard & Controls
A dedicated dashboard page for managing the van's connectivity. View active WAN sources, monitor data usage, switch between LTE and Starlink, configure Wi-Fi SSID and password — all from the HA dashboard, backed by the OpenWrt API.

### Automations Interface
A simplified automations page that makes it easy to create and manage common van automations without writing YAML. Pre-built templates for common scenarios (night mode, leaving mode, weather-reactive) with the ability to customise. Full Home Assistant automation access always available underneath.

### Remote Access
Secure remote access to your van's dashboard from anywhere, with no port forwarding, no dynamic DNS, and no subscriptions required for basic access. Architecture TBD. 

### Advanced Mode
A clearly separated "power user" area that gives full access to the underlying stack — Proxmox, Home Assistant's full UI, OpenWrt admin, terminal access. Entering advanced mode automatically creates a system snapshot so you can always roll back. Advanced mode is user-owned territory with clear documentation of what's safe to change and what isn't.

### Notifications System
Configurable alerts for critical events: low battery, loss of connectivity, GPS fence breach, temperature extremes, water levels. Push notifications via the HA companion app with per-alert enable/disable controls.

### OTA Updates
Secure, over-the-air software updates with automatic rollback on failure. Component-based updates (core, HA, OpenWrt updated independently), cryptographically signed, power-aware (never updates on low battery). Immutable system partition with persistent user data — updates never overwrite your configuration.

---

## Future Vision

These represent the longer-term direction of RoamCore. They're listed here to signal where we're heading, not to commit to timelines or specific implementations. Some of these will become concrete roadmap items as the project matures; others may evolve significantly based on user feedback and technical feasibility.

### Expanded System Integrations
- **Water system monitoring** — tank levels, pump control, flow monitoring
- **Electrical system monitoring** — fuse management, DC/AC load switching, alternator charging
- **Vehicle diagnostics** — OBD-II integration for engine data, fuel level, vehicle health
- **Climate control** — heating and cooling system integration and automation
- **Security** — camera support with local storage and motion detection

### Hardware Ecosystem
Modular, plug-and-play hardware components that extend the core hub. Each module is independently useful but integrates seamlessly with the RoamCore dashboard when connected. The goal is a system where you buy what you need and everything works together automatically.

### Intelligent System Assistance
Context-aware system summaries and recommendations built on top of deterministic sensor data. The system interprets your power usage, weather forecast, and driving patterns to provide clear, actionable information — not hype, not AI for the sake of AI. Designed to lower the barrier to understanding complex data, especially for users who don't want to learn what volts and amps mean. Trust and reliability are the absolute priorities here.

### RoamCore Labs
A community showcase for power user setups, custom dashboards, creative integrations, and advanced configurations. Designed to inspire novice users and recognise community contributions. Easy export and sharing of dashboard configurations.

### Mobile App
A dedicated mobile application (PWA initially, native later) for a streamlined on-the-go experience. Auto-discovery, adaptive layouts, and quick access to the most-used controls.

---

## Guiding Principles

These principles guide every decision on the roadmap:

**Local first.** Your data stays on your device. No cloud dependency for core functionality. The system works fully offline.

**No subscriptions for essentials.** Monitoring your battery, checking your location, and controlling your van will never require a monthly payment.

**Open source, genuinely.** The full stack is open source under permissive licenses. You own your hardware, you own your software, you own your data.

**Simple by default, powerful underneath.** The default experience is clean and approachable. The full Home Assistant, Proxmox, and OpenWrt stack is always accessible for those who want it.

**Built for the road.** Every feature is designed for the realities of mobile, off-grid life — intermittent connectivity, limited power, varying hardware, and users who have better things to do than debug their van's computer.

---

*This roadmap is updated as the project evolves. For the latest status, check the repo's issue tracker and discussion board.*
