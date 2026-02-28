# Freelancer Brief: Auto-Discovery Victron GX → RoamCore Integration Add-on (Production-Grade)

## 1. Project Context

I am building **RoamCore**, a modular operating system for vanlife based on **Home Assistant OS**.

RoamCore is pre-installed on dedicated hardware (Raspberry Pi / x86) and aims to provide:

- Beautiful dashboards  
- Whole-van automation (power, water, safety, climate, etc.)  
- Brand-agnostic integrations  
- A reliable, simple way to manage complex van systems  

One of the most critical integrations is **Victron Cerbo GX / Venus OS**, which forms the power backbone of many campervan systems.

This integration must be:

- **Zero configuration**  
- **Automatic**  
- **Extremely robust**  
- **Invisible to the end user**

The user should only need to:

> **Plug their Cerbo GX into their router (same LAN as the RoamCore Hub).**

The system must auto-detect it, configure itself, and expose clean entities into Home Assistant.

---

## 2. Technical Resources

### A. MQTT / D-Bus / Venus OS Official Documentation

- Victron MQTT Topics & VRM API:  
  https://github.com/victronenergy/dbus-mqtt  
- Venus OS / D-Bus documentation:  
  https://github.com/victronenergy/venus/wiki/dbus  
- D-Bus service structure (battery, solarcharger, tanks, etc.):  
  https://github.com/victronenergy/venus/wiki/dbus/services  
- MQTT service example:  
  https://github.com/victronenergy/dbus-mqtt/blob/master/README.md

### B. Community Reference

**SmartyVan YouTube: “Victron & Home Assistant Integration”**  
https://www.youtube.com/watch?v=lvTGsOFsy8o

Useful for understanding real-world MQTT topic behaviour.

---

## 3. Key Objective

Build a **Home Assistant add-on** (Docker container) that:

1. **Runs automatically** on RoamCore  
2. **Auto-discovers** Victron GX / Venus OS on the LAN  
3. **Connects** to its MQTT broker  
4. **Ingests** required Victron MQTT topics  
5. **Normalises** data into canonical RoamCore entities  
6. **Publishes** them to Home Assistant via MQTT Discovery  
7. Is **bulletproof reliable**  

The integration must survive network drops, reboots, and system interruptions, since many van systems depend on these values for automation.

---

## 4. Requirements

### 4.1 Platform

- Implement as a **Home Assistant add-on** (Docker + `config.json`)  
- Must run on **HA OS / HA Supervised**  
- Must run on x86_64  (mini pc)
- Will be **pre-installed & pre-enabled** in VanOS  
- Should run as a continuously-active background service  

---

### 4.2 Auto-Discovery of Victron GX / Venus OS

Periodic (lightweight) scanning for devices using:

- **mDNS** (`venus.local`, `_mqtt._tcp`)  
- **ARP scanning**  
- **Port probing** (MQTT 1883 & 8883, Modbus TCP 502, Venus HTTP pages)

State machine:

- No device → wait & retry  
- Device discovered → validate & connect  
- Device goes offline → mark sensors unavailable & retry  

Multi-device support not required for v1, but code should be extensible.

---

### 4.3 MQTT Enablement & Connection

- Detect if Victron MQTT broker is reachable  
- Attempt connection with default LAN MQTT settings  
- If broker unreachable:
  - Log diagnostic messages  
  - Continue retry loop  
  - DO NOT crash  

**Important:**  
Victron does **not** expose a safe remote API for enabling MQTT → auto-enabling is **not required**.
Make sure to include the setup step in the user.md deliverable file. 

---

### 4.4 Data Ingestion & Mapping (Canonised Entity Model)

Subscribe to relevant Victron MQTT topics and map them to clean RoamCore entities such as:

```
sensor.vt_battery_soc
sensor.vt_battery_voltage
sensor.vt_battery_current
sensor.vt_battery_power
sensor.vt_solar_power
sensor.vt_ac_in_power
sensor.vt_ac_out_power
sensor.vt_dc_load_power
binary_sensor.vt_shore_connected
```
Please add '.vt' to every entity to show which entities have come from this victron integration when integrating into the larger system later on. 

Requirements:

- Correct units and device classes  
- Missing components → entities marked unavailable  
- Internal **capabilities model** (e.g. `has_pv`, `has_ac_in`, etc.)  
- Throttle updates to sensible rates considering compute and power constraints
- No entity duplication  

---

### 4.5 Entity Exposure in Home Assistant

Use **MQTT Discovery** to create entities automatically:

- Stable entity IDs  
- Grouped under a device named **“RoamCore Victron System”**  
- Entities persist across disconnects, marked `unavailable`  

Must not require YAML editing or user action.

---

## 5. Reliability Requirements

This integration must:

- Recover from Cerbo, router, or HA reboots  
- Handle intermittent MQTT drops  
- Maintain stable entity IDs  
- Use minimal CPU/RAM  
- Avoid logging spam  
- Never crash, freeze, or duplicate data  

This is a **mission-critical** component in a van’s automation system.

---

## 6. Handling Lack of Hardware Access

The developer must:

- Use Victron sample payloads  
- Use `dbus-mqtt` documentation  
- Use mock MQTT brokers to simulate Cerbo  
- Reproduce topic structure using test files  


The expectation is that you can complete this with mocks and official documentation. But please let me know if this is very difficult/not possible. 

---

## 7. Deliverables

1. Full Home Assistant add-on repository  
   - Source code  
   - Dockerfile  
   - `config.json`  
   - README + DEV_NOTES  

2. Functionality:  
   - Auto-discovery  
   - MQTT connection  
   - MQTT topic ingestion  
   - Canonical mapping  
   - MQTT Discovery publishing  
   - Capabilities model  
   - Reliable reconnection logic  

3. Optional: **Mock Victron MQTT payload generator**  
   - For testing without hardware  

4. Documentation  
   - INSTALLATION notes (internal)  
   - Developer instructions
   - System overview notes (how the app works)

5. Demo  
   - Screenshots or video demonstrating:  
     - Discovery  
     - Correct entity creation  
     - Reconnect behaviour  

---

## 8. Acceptance Criteria

- Add-on autostarts with HA OS  
- Auto-discovers a Victron GX (real or mock)  
- Maps and exposes complete entity set  
- Survives:  
  - Cerbo reboot  
  - Router reboot  
  - RoamCore reboot  
- Proper throttling and debouncing  
- Clean logs  
- No duplicate entities  
- Low CPU/RAM usage  

---

## 9. Optional Enhancements

(Not required for v1)

- Diagnostics UI via Ingress  
- Modbus-TCP ingestion  
- Multi-device support  
- Advanced device class mapping  

---

## 10. Summary

You are building the **official Victron → RoamCore integration**, which must:

- Discover automatically  
- Configure itself  
- Expose stable Home Assistant entities  
- Be reliable under all conditions  
- Never require user action  

This is a **production component** that will ship inside a commercial product.  
It cannot be the weak link in the system.

I am able to provide ssh into a Home Assistant testbed if you require it - although I hope you would be able to spin up your own development environment. 
