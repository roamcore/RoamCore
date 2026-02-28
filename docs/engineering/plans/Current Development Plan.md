# RoamCore: Product Strategy & Integration Roadmap

RoamCore is an open, modular **operating system for vanlife** — a unified software and hardware ecosystem that integrates power, water, safety, networking, climate, sensors, and automations into a single, reliable UI.

This document outlines:

- MVP scope  
- Hardware modules  
- Integration priorities  
- Expansion roadmap  
- Long-term platform philosophy

---

# 1. Vision

### RoamCore = The OS of Vanlife

RoamCore is designed to:

- Plug into **existing systems** (Victron, routers, ESPHome devices, sensors)  
- Provide **new hardware modules** that don’t currently exist (e.g., Water Hub)  
- Offer a beautiful, simplified UI for the whole van  
- Enable deep **automation**, **scenes**, and **custom behaviour**  
- Stay fully **extensible** using standard Home Assistant capabilities  
- Let advanced users create or extend integrations long before official support

> If we don’t officially support it yet, advanced users can still integrate it themselves.

This balances “easy for beginners” with “powerful for experts”.

---

# 2. MVP (v1.0) Scope

### Designed to be:  
- **Shippable fast**  
- **Affordable**  
- **Immediately useful**  
- **Expandable over time**

---

## 2.1 Core Deliverables

### A. RoamCore Main Hub (VanOS)

A pre-configured Home Assistant OS distribution, enhanced with:

- RoamCore onboarding  
- RoamCore dashboards  
- Victron integration pack  
- Water Hub integration  
- Automation templates  
- Dashboard builder  
  - Drag-and-drop tile system  
  - Custom cards  
  - Modes (Drive, Camp, Storage)  
  - Scenes and quick-actions

**Two SKUs:**

1. **Hub Lite** (no router)  
   - Raspberry Pi 5 / equivalent SBC  
   - Ethernet + Wi-Fi client  
   - For users with existing routers (Starlink, Teltonika, Pepwave, Maxview)

2. **Hub Pro** (router included)  
   - Wi-Fi AP + optional LTE module  
   - Optional external antenna support  
   - Network monitoring integrated into VanOS  
   - Adds network-based automations & WAN switching

> No standalone “Network Hub” hardware will be developed.

---

### B. Victron Integration (Essential MVP Feature)

- Automatic Cerbo GX / Venus OS discovery  
- Clean MQTT/Modbus ingestion  
- Normalised “RoamCore Power Model”  
- Battery/AC/PV dashboard  
- Automation templates  
  - Battery protect  
  - Drive/Camp/Storage modes  
  - Alerts

---

### C. Water Hub v1 (First Physical Module)

A pre-engineered, plug-and-play plumbing + electronics module:

- Pre-plumbed manifolds & valves  
- Tank in/out, heater in/out, fill, drain  
- Internal sensors: temperature, flow, leak detection  
- Pump & heater relay control  
- ESPHome firmware  
- Dedicated water dashboards  
- Scenes like Shower Mode / Winterise / Eco  
- Freeze protection automations

---

### D. ESPHome Sensor Support

- Temperature / humidity  
- Motion  
- Leak detectors  
- Door switches  
- Gas/fume sensors  
- Light sensors

---

# 3. Integrations Roadmap

### A. Available Now

- Victron  
- ESPHome devices  
- Water Hub v1  
- Basic router status

### B. In Development

- Renogy Modbus  
- Router APIs (Teltonika, Peplink, Maxview)  
- Water Hub v1.1  
- Safety Hub prototype  
- Dashboard Builder v2

### C. Under Evaluation

- Dometic  
- Redarc  
- Truma / Webasto  
- Starlink  
- CAN bus modules  
- OBD-II  
- Third-party RV automation systems

---

# 4. Hardware Roadmap

### Phase 1 Hardware  
- Water Hub v1  
- Sensors (ESPHome)

### Phase 2 Hardware  
- Safety & Security Hub

### Phase 3 Hardware  
- Electrical Hub (non-Victron users)

> Networking hardware is only included in Hub Pro — no standalone Network Hub.

---

# 5. Customisation Philosophy

### Simple for Beginners
- Onboarding wizard  
- Prebuilt dashboards  
- Scenes & modes  
- Dashboard builder

### Unlimited for Experts
- Full Home Assistant access  
- Custom automations  
- Third-party integrations  
- DIY ESPHome devices  
- Firmware customisation

---

# 6. Advanced Hardware Store

- CAN modules  
- Wiring harnesses  
- Leak sensors  
- Tank sensors  
- Motion detectors  
- Smart relays  
- Temperature/pressure sensors

---

# 7. Pricing Targets

- **RoamCore Hub Lite:** £179–£249  
- **RoamCore Hub Pro:** £349–£499  
- **Water Hub v1:** £299–£499  
- **Add-On Hardware:** 30–40% margin

---

# 8. Phased Release Plan

### Phase 1 – MVP  
- Hub Lite & Pro  
- Victron integration  
- Water Hub v1  
- ESPHome support  
- Dashboard builder v1  
- Public roadmap

### Phase 2 – Expansion  
- Renogy  
- Router APIs  
- Safety prototype  
- Dashboard builder v2  
- Additional scenes/modes

### Phase 3 – Platform Build-Out  
- Electrical Hub  
- Safety Hub v1  
- Add-on marketplace  
- Installer programme

### Phase 4 – Full VanOS Ecosystem  
- Multibrand automation  
- Integrated climate control  
- Vehicle OBD  
- Subscription add-ons  
- Builder kits

---

# 9. Summary

RoamCore is:

- A **brand-agnostic OS** for vanlife  
- Built on open standards  
- Modular through hardware hubs  
- Extensible with software updates  
- Beginner-friendly and expert-powerful  
- Designed to integrate *existing gear* and offer **new missing modules**

The MVP focuses on:

- Main Hub (Lite + Pro)  
- Victron integration  
- Water Hub v1  
- Dashboard builder  
- Clear integration roadmap

RoamCore aims to become the **definitive automation platform for mobile living**.
