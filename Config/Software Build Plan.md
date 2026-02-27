# RoamCore MVP Software Scope & Task Breakdown

This document outlines all software-related components required to deliver the **RoamCore MVP**, including backend services, UI, integrations, onboarding, and reliability layers. It is written for internal use and project planning.

---

# 1. VanOS Base Image & Platform

## 1.1 VanOS Image (HA-based) — P0  
Create a reproducible image for:
- Raspberry Pi (Hub Lite)
- x86 mini PC (Hub Pro)

Must include:
- Home Assistant OS
- RoamCore add-ons (Victron integration, ESPHome, etc.)
- Default HA configuration

### Tasks
- [ ] Build ARM and x86 HA OS images
- [ ] Pre-install custom RoamCore repository + add-ons
- [ ] Pre-configure HA basics (timezone, language, admin)

---

## 1.2 Onboarding Flow — P0  
A simple first-boot wizard:
- Network confirmation
- Optional RoamCore account creation
- System readiness checks

### Tasks
- [ ] Build onboarding UI
- [ ] Integrate with HA’s onboarding pipeline
- [ ] Display high-level “System Status” page

---

# 2. Device Discovery & Capabilities Layer

## 2.1 Discovery Orchestrator Service — P0  
Detects presence of:
- Victron GX
- Water Hub v1
- ESPHome devices
- Router integrations (future)

### Tasks
- [ ] Implement continuous device discovery
- [ ] Build capability JSON model
- [ ] Store and update capability state

---

# 3. Backend Integration (“RoamCore Model”)

## 3.1 Unified RoamCore Data Model — P0  
A logical schema on top of HA entities:
- battery.soc, battery.voltage
- water.tank_level
- network.online
- modes: drive, camp, storage

### Tasks
- [ ] Define schema
- [ ] Map HA entities into schema
- [ ] Expose via internal API

---

## 3.2 Hide/Show UI Elements Based on Capabilities — P0  
Dynamically hides unavailable features (e.g., no solar → no solar tile).

### Tasks
- [ ] Connect capability model to frontend
- [ ] Implement conditional rendering

---

# 4. Frontend / UI Layer

## 4.1 Core Dashboards — P0  
MVP screens:
- Overview
- Power (Victron)
- Water (Water Hub)

### Tasks
- [ ] Overview UI (battery, water, network)
- [ ] Power detail screen
- [ ] Water detail screen
- [ ] Responsive mobile UI

---

## 4.2 Dashboard Builder (Tiles) — P1  
MVP version: add/remove/reorder tiles.

### Tasks
- [ ] Define tile types
- [ ] Implement grid layout
- [ ] Implement edit mode

---

# 5. Automation System

## 5.1 Automation Templates — P0  
Examples:
- Battery protect below threshold
- Leak detected → shut pump + alert
- Drive Mode logic
- Water tank alerts

### Tasks
- [ ] Build HA blueprints
- [ ] Settings UI for thresholds
- [ ] Mode-based logic

---

## 5.2 Visual Automation Builder — P1  
Optional later feature.

---

# 6. Update System

## 6.1 RoamCore Update Mechanism — P0  
Manage:
- HA OS updates  
- RoamCore add-on updates  
- RoamCore frontend updates  

### Tasks
- [ ] Build update check system
- [ ] Build simple version card
- [ ] Add update policies

---

# 7. Remote Access

## 7.1 User Remote Access — P0  
Nabu Casa recommended for MVP.

### Tasks
- [ ] Integrate Nabu Casa during onboarding
- [ ] Show remote access status

---

## 7.2 Admin/Support Remote Access — P1  
Optional support tunnel for later versions.

---

# 8. Settings, Modes & Profiles

## 8.1 Global Modes — P0  
Modes:
- Drive
- Camp
- Storage

Affects power/water automations.

### Tasks
- [ ] Mode selector UI
- [ ] Mode backend entity
- [ ] Tie modes into automation templates

---

## 8.2 System Settings UI — P0  
Includes:
- Battery SoC thresholds
- Tank capacity
- Pump/valve config

### Tasks
- [ ] Settings storage
- [ ] Validation
- [ ] Settings UI

---

# 9. Diagnostics & Logging

## 9.1 Local Diagnostics — P0  
“System Health” page.

### Tasks
- [ ] Integration status indicators
- [ ] Error/warning display
- [ ] Link to HA logs

---

## 9.2 Telemetry (optional) — P1  
Opt-in anonymised metrics.

---

# 10. Documentation & Help

## 10.1 In-App Help — P0  
Tooltips, explanations, basic troubleshooting.

### Tasks
- [ ] Create help overlays/tooltips
- [ ] Add quick troubleshooting text

---

## 10.2 External User Docs — P0  
Quick-start, installation, and troubleshooting page.

---

# 11. Final MVP Checklist (Condensed)

**Must Have Before Launch**
- [ ] VanOS image builds  
- [ ] Always-on Victron add-on completed  
- [ ] Water Hub integration  
- [ ] Capability detection system  
- [ ] RoamCore backend model  
- [ ] Overview + Power + Water dashboards  
- [ ] Basic tile system  
- [ ] Core automations  
- [ ] Update mechanism  
- [ ] Remote access  
- [ ] Modes implemented  
- [ ] Health/diagnostics view  
- [ ] Basic documentation & onboarding  

---

# 12. Post-MVP (v1.1+) Ideas
- Dashboard builder v2  
- Visual rule builder  
- Router integrations (Teltonika, Peplink)  
- Admin remote support mode  
- Telemetry  
- Safety/Electrical hub integrations  

---

This document represents the **complete software scope for the RoamCore MVP**.
