<p align="center">
  <img src="https://raw.githubusercontent.com/roamcore/RoamCore/main/assets/banner.png" alt="RoamCore Banner" width="100%">
</p>

<p align="center">
  <a href="https://discord.gg/V689zUs4">
    <img src="https://img.shields.io/badge/Discord-Join-5865F2?style=for-the-badge&logo=discord&logoColor=white"/>
  </a>
  <a href="https://roamcore.co.uk/docs/">
    <img src="https://img.shields.io/badge/Docs-Read-2EA44F?style=for-the-badge&logo=readthedocs&logoColor=readthedocs"/>
  </a>
  <a href="https://buymeacoffee.com/bernardc">
    <img src="https://img.shields.io/badge/Donate-Support-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black"/>
  </a>
  <a href="https://www.youtube.com/@RoamCore">
    <img src="https://img.shields.io/badge/YouTube-Watch-FF0000?style=for-the-badge&logo=youtube&logoColor=white"/>
  </a>
</p>

<p align="center">
  <strong>The open-source operating system for life on the road.</strong><br>
  Built on Home Assistant, OpenWrt, and Proxmox.
</p>

---

## ⚡ One-line install

Already running Home Assistant? Install everything — packages, custom component, dashboard, JSON API — in one command:

```sh
curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh | sh
```

What this does: downloads the repo, copies `homeassistant/packages/*`, `custom_components/*`, `www/roamcore/*`, `lovelace/*`, and `tools/*` into your HA `/config`, writes a manifest to `/config/.roamcore/`, and backs up any files it overwrites. Restart Home Assistant when it's done. Uninstall with `uninstall.sh`.

**Prefer HACS?** Add `https://github.com/roamcore/RoamCore` as a **Custom Repository** (category: Integration) and the integration auto-provisions the rest. Details: [`docs/howto/hacs-custom-repo-install.md`](docs/howto/hacs-custom-repo-install.md).

---

## What you get

| Feature | What it does |
|---|---|
| **One mobile dashboard** | Battery, solar, water, GPS, connectivity, lighting, mode — one page, works offline, lives inside your existing Home Assistant. |
| **Honest integrations** | Tier A (one-tap, config_flow, tests), Tier B (recipe), Tier C (external link). The audit script enforces the badges — no marketing fluff. |
| **OpenClaw JSON API** | Stable, versioned `/api/roamcore/openclaw/summary` endpoint so local agents can read your van's state and answer questions in plain English. |
| **Trip Wrapped** | Self-hosted trip recap from local Traccar data — no cloud, no upload. |
| **Traccar + Wicann Pro recipes** | Step-by-step recipe installs for GPS tracking and OBD2 telemetry. No one-tap yet, but the docs work. |

---

## Status

**Beta — what's working, what's WIP.**

| Status | Feature |
|---|---|
| ✅ Shipped | One-line installer + uninstaller, HACS custom-repo install, RoamCore dashboard, native YAML dashboard, OpenClaw JSON API, Map page (with raster fallback), Trip Wrapped HTML export, Setup wizard (built-in Lovelace cards), support bundle exporter. |
| ✅ Honest tier-A | **Victron Energy (GX / Cerbo / MQTT)** — config_flow, one-tap, integration tests. |
| ✅ Honest tier-B | **Traccar** (GPS / trip tracking) and **MeatPi WiCAN Pro** (OBD2) — recipe installs, all blockers documented. |
| 🧪 In progress | Registry-driven setup wizard (today it's a hand-written YAML dashboard), VP2430 install E2E proof in CI, marketing-site install CTA, HACS default-store listing. |
| ❌ Not yet | A downloadable RoamCore OS image for the VP2430, a second tier-A connection. |

The full audit with blockers, go/no-go criteria, and what we'd need to ship a beta or a public launch is in [`docs/marketing/launch-checklist.md`](docs/marketing/launch-checklist.md).

---

## Why open source

You didn't build a van to be dependent on someone else's platform. The software that runs your home — even a home on wheels — should be transparent, extensible, and entirely in your control. That's why every layer of RoamCore is open source, built on foundations the community has already proven at scale:

- **[Home Assistant](https://www.home-assistant.io/)** — the world's largest open-source home automation platform
- **[OpenWrt](https://openwrt.org/)** — battle-tested networking used in millions of routers worldwide
- **[Proxmox VE](https://www.proxmox.com/)** — enterprise-grade virtualisation that keeps everything modular and updateable

No proprietary protocols. No locked-down firmware. No features held hostage behind a monthly fee. Every layer is open, documented, and replaceable. If RoamCore ever disappears, your system still works. That's the point.

You chose vanlife for the freedom. The software that runs your van should reflect that — not tie you to a subscription, a cloud service, or a vendor that decides what you can and can't do with your own vehicle.

You spent months building the van. The electrics are dialled. The plumbing works. The insulation is perfect. But when it comes to actually *managing* all of it — checking your batteries, staying connected, tracking where you've been — you're juggling five apps, three dashboards, and a spreadsheet. Each one owned by a different company, each one another dependency.

RoamCore fixes that.

One system. One dashboard. Everything in your van — power, connectivity, navigation, climate, water — visible and controllable from a single interface on your phone. It runs locally on your hardware, it works offline, and it belongs to you. No subscriptions. No cloud lock-in. No one else's terms and conditions.

---

## Getting started

### HA-only install (recommended)

If you already run Home Assistant, the one-line install above is the fastest path. Full walkthrough: [`docs/howto/homeassistant-installer.md`](docs/howto/homeassistant-installer.md).

### HACS install (beta)

Add `https://github.com/roamcore/RoamCore` as a HACS custom repository (category: Integration), install RoamCore, restart HA. Details: [`docs/howto/hacs-custom-repo-install.md`](docs/howto/hacs-custom-repo-install.md).

### First-run setup

- Open `/roamcore/setup` (or click **Open setup wizard** from the dashboard banner). A **"Setup not complete"** banner stays visible until the `rc_setup_*` readiness checks are green.
- Optional: toggle `input_boolean.rc_demo_mode` to preview the dashboard with safe demo values when sensors are missing.

### RoamCore OS (hardware: Protectli VP2430)

The full stack — Proxmox + OpenWrt + HAOS + App CT on a Protectli VP2430 — is documented in [`docs/engineering/plans/SoftwareOverview.md`](docs/engineering/plans/SoftwareOverview.md). A pre-built image is not yet shipped; today you build it yourself from the docs.

---

## OpenClaw JSON API

RoamCore ships an optional OpenClaw-oriented JSON API that exposes a stable, versioned snapshot of your van's state. Once you connect it to a local agent, you can ask your van questions in natural language and get context-heavy answers (power, location, levelling, trip context) without hunting through multiple apps.

- Docs: [`docs/reference/openclaw-json-api.md`](docs/reference/openclaw-json-api.md)
- Endpoint: `/api/roamcore/openclaw/summary`

**5 surprisingly useful things to ask your van:**

1. *"Can I make it through tonight on power if I work for 4 hours, cook once, and run the heater fan?"* — recent power drain + battery SOC → practical forecast.
2. *"Do I have enough water to last until tomorrow afternoon?"* — turns level sensors into "X days at your current use".
3. *"Find me a legal-ish place to sleep within 30 minutes that won't kill my internet."* — location + connectivity + (later) campsite overlays.
4. *"What's my internet situation right now — Starlink/LTE/Wi-Fi — and is it getting worse?"* — plain-English diagnosis, not an icon.
5. *"I'm in bed — show me what I'm parked near and tell me if anything looks wrong."* — cameras + sensors into a calm "night watch" summary.

---

## Repo structure

```
roamcore/
├── dashboard/       # Dashboard UI prototypes and design assets
├── docs/            # User docs (MkDocs) + engineering plans
├── homeassistant/   # HA packages, custom components, www, lovelace, tools
├── hardware/        # Hardware specifications and reference configs
├── openwrt/         # OpenWrt networking configuration
├── proxmox/         # Proxmox VM setup and provisioning
├── connections/     # Single source of truth for catalog connections
├── scripts/         # Audit, build, install, check scripts
├── ROADMAP.md       # Project direction
├── CONTRIBUTING.md  # How to contribute
└── LICENSE          # MIT License
```

---

## Contributing

RoamCore is fully open source under the [MIT License](LICENSE). Read [`CONTRIBUTING.md`](CONTRIBUTING.md) to get started.

If you want to add a new supported connection, the catalog pipeline (see [`connections/README.md`](connections/README.md)) is the entry point: one `connection.yml` per integration, validated by `scripts/audit_connections.py`, rendered onto the wizard and the docs site automatically.

---

<p align="center">
  Built for the road. Built in the open.
</p>
