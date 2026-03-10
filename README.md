# RoamCore

**The open-source operating system for life on the road.**

You chose vanlife for the freedom. The freedom to go anywhere, live on your own terms, and not answer to anyone. The software that runs your van should reflect that — not tie you to a subscription, a cloud service, or a vendor that decides what you can and can't do with your own vehicle.

You spent months building the van. The electrical is dialled. The plumbing works. The insulation is perfect. But when it comes to actually *managing* all of it — checking your batteries, staying connected, tracking where you've been — you're juggling five apps, three dashboards, and a spreadsheet. Each one owned by a different company, each one another dependency.

RoamCore fixes that.

One system. One dashboard. Everything in your van — power, connectivity, navigation, climate, water — visible and controllable from a single interface on your phone. It runs locally on your hardware, it works offline, and it belongs to you. No subscriptions. No cloud lock-in. No one else's terms and conditions.

We're building the operating system that van conversions have been missing — one that's as free as the lifestyle itself.

---

## What You Get

RoamCore gives you a clean, mobile-first dashboard that makes your van's systems feel as polished as the build itself:

- **Power** — battery state of charge, solar input, load consumption, charging status. See your energy situation at a glance and stop doing mental maths.
- **Navigation** — automatic GPS trip logging, route history, distance and stop tracking. Generate shareable trip summaries of where you've been.
- **Connectivity** — LTE, Starlink, Wi-Fi — managed and monitored from one place, with automatic failover so you stay connected.
- **Level** — a visual spirit level on your dashboard. Park, tap calibrate, done.
- **Weather & Time** — conditions, forecasts, and automatic timezone updates as you travel. Useful on its own, powerful when tied to automations.
- **Automations** — schedule routines, create modes, and let the system handle the repetitive stuff.

Simple enough for anyone. But underneath, it's the full Home Assistant stack — if you want to go deep, there's no ceiling.

## Why Open Source

You didn't build a van to be dependent on someone else's platform. The software that runs your home — even a home on wheels — should be transparent, extensible, and entirely in your control. That's why every layer of RoamCore is open source, built on foundations the community has already proven at scale:

- **[Home Assistant](https://www.home-assistant.io/)** — the world's largest open-source home automation platform
- **[OpenWrt](https://openwrt.org/)** — battle-tested networking used in millions of routers worldwide
- **[Proxmox VE](https://www.proxmox.com/)** — enterprise-grade virtualisation that keeps everything modular and updateable

No proprietary protocols. No locked-down firmware. No features held hostage behind a monthly fee. Every layer is open, documented, and replaceable. If RoamCore ever disappears, your system still works. That's the point.

---

## Getting Started

There are two ways to use RoamCore:

### RoamCore Dashboard

If you already run Home Assistant in your van, you can install the RoamCore dashboard and configuration onto your existing setup. This gives you the pre-built dashboard, integrations, and automations without replacing your current infrastructure.

The `homeassistant/` directory contains everything you need.

### RoamCore OS

The full experience. A pre-configured Proxmox image running Home Assistant OS and OpenWrt as VMs on supported hardware (Protectli VP2430). Integrated cellular connectivity, WAN failover, modem GPS — all pre-configured.

See [`docs/`](docs/) for setup instructions.

---

## Current Status

**RoamCore is in beta.** The core features are being built and tested. The software is usable but expect rough edges, breaking changes, and gaps in documentation.

We're releasing early because we believe in building in the open. The long-term goal is a polished, novice-friendly product — but right now, this is best suited for technical users who are comfortable with Home Assistant and happy to provide feedback.

See the [roadmap](ROADMAP.md) for what's being built and where the project is heading.

---

## Repo Structure

```
roamcore/
├── dashboard/       # Dashboard UI prototypes and design assets
├── docs/            # Documentation and guides
├── hardware/        # Hardware specifications and reference configs
├── homeassistant/   # Home Assistant configuration, dashboards, automations
├── openwrt/         # OpenWrt networking configuration
├── proxmox/         # Proxmox VM setup and provisioning
├── scripts/         # Utility and setup scripts
├── ROADMAP.md       # Project direction and feature roadmap
├── CONTRIBUTING.md  # How to contribute
└── LICENSE          # MIT License
```

---

## Extensible By Design

Start with the essentials, then grow into a complete control system:

- **Power** — solar, batteries, charging sources, inverters
- **Water** — tank levels, pumps, flow monitoring
- **Climate** — heaters, fans, AC, temperature sensors
- **Safety & Security** — cameras, gas and smoke detection, motion sensors
- **Navigation** — GPS tracking, trip history, levelling
- **Vehicle** — OBD-II diagnostics, fuel monitoring
- **Remote Access** — secure access from anywhere

This is one of the strengths of building on open source — the community can keep expanding what's possible.

---

## Who It's For

**Everyday users** who want a reliable system that just works.

**Builders and integrators** who want full control without starting from scratch.

**Home Assistant enthusiasts** who want a mobile-first, cohesive platform that saves weeks of configuration.

---

## Contributing

RoamCore is fully open source under the [MIT License](LICENSE). If you care about independence, clarity, and building systems that last, you're in the right place.

Read [CONTRIBUTING.md](CONTRIBUTING.md) to get started.

---

<p align="center">
  Built for the road. Built in the open.
</p>
