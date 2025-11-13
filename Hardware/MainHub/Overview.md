# VanCore Main Hub — Single-Box Architecture (VP2430)

> **Status:** Draft V1 (implementation-ready)  
> **Owner:** VanCore Hardware  
> **Last updated:** 2025-11-13

---

## TL;DR

The **VanCore Main Hub** is a single, serviceable enclosure built around the **Protectli VP2430**. It runs:

- A **router VM** (OpenWrt or OPNsense) for WAN/LAN, failover, and VPN.
- **Home Assistant** for UI, automations, and telemetry.
- **M.2 Wi-Fi** (single SSID) and **M.2 4G** by default, with a **drop-in 5G upgrade** path.
- A small **internal USB sensor node** (IMU for van level + BME680 for environment).

**Ports:** Starlink on **WAN** (Port 1), three **LAN** ports (Ports 2–4) to the **Electrical / Water / Safety** boxes.  
**Power:** 12 V screw terminal with automotive protections.  
**RF:** The chassis provides **six SMA upshot knockouts**—enough for **4× Cellular** and **2× Wi-Fi** external antennas.  
**No external switch shipped**; customers can add one later if they need extra ports/PoE.

---

## Why a Single Box ([VP2430](https://kb.protectli.com/kb/vp2430-hardware-overview/)) vs. Multiple Smaller Boxes

- **Simpler UX & support:** One SSID, one web UI, one power input, clear labels → fewer “which network am I on?” tickets.
- **Higher reliability:** Fewer inter-box cables, fewer failure points; cleaner grounding/EMI and thermal management.
- **Lower footprint & BOM:** No duplicate enclosures/PSUs/mounts; easier installation.
- **Future-proof:** Field-swappable M.2 cellular module (4G → 5G) without rewiring the van.

---

## System Architecture

ETH ports:
- Starlink Dish → Starlink Router/PSU (Ethernet LAN) → VP2430 Port 1 (WAN)
- Port 2 (LAN) → Electrical Box
- Port 3 (LAN) → Water Box
- Port 4 (LAN) → Safety/Security Box

Inside VP2430:
- Router VM (OpenWrt/OPNsense)
- WAN1: Port 1 (Starlink, DHCP client; Bypass mode recommended)
- LAN: Bridge over Ports 2–4
- Multi-WAN (failover/policy), WireGuard server, DHCP/DNS
- Home Assistant VM
- Dashboard: WAN toggle, signal, data usage, WAN IP, latency, sensor tiles
- M.2 Wi-Fi AP (single SSID for van)
- M.2 Cellular modem (4G default; 5G upgrade path)
- Internal USB Sensor Node (IMU + BME680 → MQTT → HA)

---

## Hardware Bill of Materials (BOM)

**Base chassis**
- **Protectli VP2430** (4× 2.5 GbE, internal M.2 slots, SIM support, six SMA upshot knockouts)

**Core compute**
- **RAM:** 1× 16 GB SO-DIMM (match VP2430 spec; planned: DDR5-4800)
- **Storage:** 256–512 GB NVMe (M-key 2280)

**Networking & radios**
- **Wi-Fi:** M.2 **E-key** Wi-Fi 6 card + **2× RP-SMA** pigtails + **2× Wi-Fi antennas**  
  _Note: Validate AP mode (hostapd), WPA3, multi-SSID/VLANs._
- **Cellular (default):** M.2 **B-key 3042/3052** LTE Cat-6 (e.g., EM06-E class) + **2× MHF4→SMA** pigtails + **2× cellular antennas**
- **Cellular (upgrade):** M.2 **5G** (e.g., RM520N-GL class) + **2 additional** MHF4→SMA pigtails + **2 additional** cellular antennas (for **4×4 MIMO** total)
- **SIM:** Nano-SIM in VP2430 slot

**Sensors (internal)**
- **USB sensor node:** ESP32/RP2040 + **BNO085/086** (IMU) + **BME680** (environment)  
  → Publishes via MQTT to HA

**RF panel (six SMA knockouts available)**
- **CELL 1–4:** **SMA** bulkheads (populate 1–2 for 4G; leave 3–4 capped for 5G upgrade)
- **WIFI 1–2:** **RP-SMA** bulkheads (populate)

**Power (automotive-grade)**
- 12 V screw terminal input (from ElectricalBox or other 12v source)

**Mechanicals & labeling**
- Anti-vibration mounts; thread-locker on RF bulkheads
- **Thermal pad** from cellular M.2 to chassis lid/heatsink (spec for 5G heat), included in RP2430 box
- **Silkscreen/labels**: WAN, LAN1–3, CELL1–4, WIFI1–2, 12 V PWR + QR to quick-start (custom sticker/silkscreen for labels/branding/etc)

---

## RF Plan (using the six knockouts)

- **Ship with 4 populated:**  
  - **CELL 1–2 (SMA)** → LTE 2×2 MIMO now  
  - **WIFI 1–2 (RP-SMA)** → Wi-Fi AP  
- **Leave CELL 3–4 capped** for the **5G upgrade** kit (achieves 4×4 MIMO)  
- Optionally support a **6-in-1/7-in-1 roof puck** (4× CELL + 2× Wi-Fi [+ GNSS]) via a cable gland if customers prefer roof-mounted antennas.

> **No RF splitters.** MIMO requires distinct elements; splitters add loss and can damage TX paths.

---

## Port Roles & Topology

- **Port 1 = WAN (Starlink)**  
  - Use Starlink **Ethernet Adapter** (or HP PSU LAN) → RJ45 to Port 1  
  - Enable **Bypass Mode** in the Starlink app to avoid double-NAT
- **Ports 2–4 = LAN**  
  - Bridge these ports in Proxmox (`vmbr0`)
  - Attach Router VM (LAN vNIC) + HA VM to `vmbr0`
  - Feed Electrical / Water / Safety boxes directly (no switch required for V1)

> Customers who need more wired ports or PoE can add a small switch to any LAN jack later.

---

## Software Stack

**Router VM (OpenWrt or OPNsense)**
- **Multi-WAN:** Starlink (WAN1) + Cellular with failover/policy
- **WireGuard** server for remote access (support + user)
- **DHCP/DNS**, mDNS reflector across VLANs if used
- **Watchdogs:** modem & WAN health checks with auto-recovery
- **Backups:** nightly config export off-box (cloud/USB); golden image/snapshot for rollback

**Home Assistant**
- **Dashboard tiles:**  
  - **Starlink ↔ Cellular** toggle (Auto / Starlink-only / Cellular-only)  
  - Cellular **RSRP/RSRQ/SINR**, band/cell ID  
  - **Data usage** (vnStat/nlbwmon/interface counters)  
  - **WAN IP**, **latency**, optional conservative speed test  
  - **Sensor node**: van level, temp, humidity, pressure, VOC  
- **Remote access:** **Nabu Casa** or **WireGuard** (QR provisioning)
- **Support bundle:** one-click log/config collector (router + HA) to zip

---

## 4G → 5G Field Upgrade Procedure (User)

1. Power down the hub.  
2. Remove LTE M.2; insert **VanCore-approved 5G M.2** module.  
3. Connect **four labeled MHF4 pigtails** (MAIN1/AUX1/MAIN2/AUX2).  
4. Uncap **CELL 3–4** bulkheads (or attach the extra two leads from a roof puck).  
5. Power on; router VM auto-selects 5G profile; HA shows 5G metrics.  
6. Keep spare MHF4 pigtails in the kit (they’re delicate).

---

## Assembly Notes

- Keep RF pigtails short, strain-relieved, and away from DC harnesses.  
- Verify Wi-Fi card AP mode (multi-SSID/VLAN) on the chosen distro.  
- Label **Port 1 = WAN (Starlink)**; **Ports 2–4 = LAN**; **CELL 1–4**; **WIFI 1–2**; **PWR 12 V**.  
- Include the 12 V power lead and anti-vibration mount kit.  
- Ship a laminated quick-start: Starlink Bypass, default SSID/pass, HA URL, support QR.

---

## Testing & Acceptance (V1)

- **Power:** cold-crank/brown-out; LVC cut & resume; load-dump protection.  
- **Thermals:** sustained cellular load; M.2 pad keeps modem < vendor limit.  
- **WAN:** Bypass mode; failover to LTE; manual toggle works from HA.  
- **Wi-Fi:** AP stability; WPA3; (optional) multi-SSID/VLANs.  
- **Sensors:** IMU zeroing & stability; BME680 readings; MQTT to HA.  
- **Watchdogs:** simulate modem/WAN hang → recover within target time.  
- **Backups/rollback:** golden image restore path verified end-to-end.

---

## Roadmap / Optional Extras

- GNSS puck (time sync + geo automations)  
- PoE injector/splitter options for cameras/desk AP **(part of SafetyBox)**
- VLAN presets per box (Electrical/Water/Safety/IoT)  
- ntopng/Influx/Grafana pack (requires CPU headroom)  
- NVR/Frigate pack (N305-class CPU recommended)**KEY CONSIDERATION BEFORE ORDERING**

---

## Versioning

- **v1.0** — Initial single-box design (VP2430; six SMA knockouts; 4G default; 5G upgrade path; no external switch shipped)

---
