# RoamCore — landing page copy

**Author:** Slice 7 (marketing-readiness) · **Date:** 2026-07-28

This is a draft of the public marketing landing page. Plain English. No jargon. Three hero lines so Bernard can pick the one that fits the brand.

The copy is deliberately short. Each section is one paragraph or less. Empty marketing copy has killed more products than bad code has.

---

## Hero line — pick one

### Option A — the ownership line

> **Your van. Your software. Your rules.**
> One open-source system that runs your power, water, connectivity, and map — locally, on your hardware, no subscription. Built on Home Assistant, OpenWrt, and Proxmox.

### Option B — the "tired of five apps" line

> **Stop juggling five apps in your van.**
> RoamCore pulls your power, water, 5G, Starlink, lighting, and GPS into one dashboard that lives on your hardware and works offline. No subscriptions. No cloud lock-in. No one else's terms and conditions.

### Option C — the "we already did the hard part" line

> **The open-source operating system for life on the road.**
> RoamCore bundles Home Assistant, OpenWrt, and Proxmox into a single, opinionated van rig — one install, one dashboard, one community. Read the code, change it, run it forever.

> **Bernard:** if you can only pick one, the writer's pick is **A** — it's the shortest, owns the differentiation (open-source + local + no subscription), and it's the seal on every back-of-the-van-window sticker you'd want to put on it.

---

## Who this is for

Read this section top to bottom. If none of the three personas below sounds like you, you're probably not the target customer yet — and that's okay.

### 1. The vanlifer

You spent months building the van. The electrics are dialled. The plumbing works. The insulation is perfect. But every time you want to check the battery you open one app, every time you want to see where you parked you open another, every time the starlink drops you open a third. You don't want to learn a router config — you want to know "is the kettle safe to run?" in two seconds.

RoamCore gives you a single dashboard on your phone with the things you actually care about: battery, water, GPS, internet, lights. It works offline. It works on a headless box you never have to touch. And it never asks you to log in.

### 2. The integrator

You have a Victron Cerbo, a Starlink, a LTE router, three tank sensors, and a habit of saying "I can just script this in Home Assistant". You probably already do. You don't need RoamCore to talk to your devices — you need it to not get in the way.

RoamCore is a thin layer on top of Home Assistant. The integrations you already use (MQTT, ESPHome, Modbus, the Modbus-TCP Victron) work untouched. RoamCore adds a stable `rc_*` entity contract, a single dashboard, a setup wizard, and a JSON API you can hit from any local agent. If you want to keep using HA's native UI, you can. RoamCore will not lock you in.

### 3. The Home Assistant enthusiast

You run HA on a Raspberry Pi (or a NUC, or a VM, or all of the above). You have 200 entities. You have an automation for everything. You may or may not have a van — that's fine.

RoamCore is HA with a curated coat of paint and a documented install path. It ships an opinionated dashboard, a setup wizard, an `rc_*` entity contract you can rely on, and a JSON API for local agents. It is not a fork. It will not fight your existing setup. Install it as a HACS custom repo and you'll have one more dashboard, one more API, and zero surprises.

---

## The four things RoamCore does

### 1. **One-button install**

If you already have Home Assistant, install is one line:

```sh
curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh | sh
```

Or add `https://github.com/roamcore/RoamCore` as a HACS custom repository (category: Integration) and click Install. The integration auto-provisions the rest: dashboards, packages, the JSON API. Restart Home Assistant and you're done.

### 2. **One dashboard**

The RoamCore dashboard lives at `/roamcore/home` inside your existing Home Assistant. Battery SOC, solar input, water tanks, GPS, internet status, lighting, mode (Auto / Travel / Camp / Stealth) — all on one page, on your phone, works offline. The dashboard is a thin wrapper over Home Assistant's own UI, which means everything you already know about HA still works.

### 3. **Honest connections**

Every connection in the catalog is labelled with a tier:

- **Tier A** — we own it, one-tap connect, integration tests pass.
- **Tier B** — a recipe, documented, you can follow it.
- **Tier C** — an external link only, community-maintained.

The audit script (`scripts/audit_connections.py`) checks every claim. If a connection says tier-A, it has a working config_flow, tests, and a one-tap wizard. If it doesn't, the audit blocks the PR. No marketing-degree gradient.

### 4. **Open hardware references**

The canonical RoamCore OS target is the **Protectli VP2430** (N100/N150, 4×2.5GbE, M.2 Wi-Fi + LTE/5G), running Proxmox with OpenWrt, Home Assistant OS, and a small control-plane LXC. The full stack is documented in `docs/engineering/plans/SoftwareOverview.md`. You can build it yourself. You can fork it. You can run it on a different box — we don't lock the software to the hardware.

---

## The punchline

**No subscriptions. No cloud lock-in. No telemetry. No "your trial has ended".**

RoamCore runs on your hardware. It talks to your devices. It does not phone home. It does not require an account. The code is on GitHub. The license is open-source. You can read every line, change every line, and run it forever.

You chose vanlife for the freedom. The software that runs your van should reflect that.
