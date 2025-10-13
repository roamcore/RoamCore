### VanCore
🔧 System Overview: Modular Automation Platform for Off-Grid and Mobile Living Spaces
 
## 🌍 Overview

This is an open-source, modular hardware and software platform designed to monitor, control, and automate all essential systems in a self-sufficient van conversion or off-grid living space. While the initial focus is campervans, the system is easily adaptable to boats, tiny houses, cabins, trailers, overlanding rigs, expedition vehicles, and mobile workstations or surveillance vehicles.

It uses Home Assistant as the core automation engine and aims to provide both:
●	A simple, intuitive interface for average users, enabling a "works-out-of-the-box" experience with modular plug-and-play components.
●	Full flexibility for technical users to customise, extend, and access the full Home Assistant stack underneath.
The goal is to provide a simple, powerful, and open-source control system for life off-grid.
 
## 🎯 Core Features and System Goals

People who live in vans or other mobile/off-grid environments often piece together partial monitoring solutions or use expensive proprietary systems that are hard to customise. This project aims to replace those with one unified platform that is:

✅ Modular Monitoring & Control
●	Every system (water, electrical, security, etc.) is built as a self-contained module.
●	Modules communicate via Wi-Fi, Zigbee, or serial, using open standards.
●	Designed to be installed independently, replaced, or upgraded easily.
●	All-in-one - combines electrical, water, safety, cameras, internet, GPS, and remote access in one system.
●	Simple for beginners, powerful for pros - Plug-and-play modules, with the full power of Home Assistant under the hood for advanced users.
✅ Unified Home Assistant Integration
●	All data and control is centralised in a Home Assistant instance running locally.
●	The system supports remote control and dashboard access via VPN or Nabu Casa.
●	OTA firmware updates and config management are supported via Git.
●	Beautiful, intuitive interface - custom UI layers over Home Assistant, designed for touchscreens and mobile use.
✅ Designed for Real-World, Off-Grid Use
●	Works fully offline with no reliance on internet/cloud.
●	Robust against power loss, mobile connectivity drops, and harsh conditions.
●	Power-efficient and designed around low-voltage 12V systems.
●	No dependency on third-party clouds or subscriptions.


 
## 👤 Target Users
●	Everyday vanlifers, boaters, and tiny home dwellers
who want reliable, powerful automation without having to learn code or deal with complex interfaces.

●	Installers and conversion shops
who want a white-label-ready, flexible automation platform to offer clients.

●	Home Assistant fans
who want a hardware/software system built around the ecosystem they love - but simplified and streamlined.

 
 
## 🧠 System Architecture
## 🧩 Core Components

## Component	Description
Main Hub	Mini PC (GMKtec Nucbox G5) running Home Assistant OS
Modules	ESP32-based sensor/actuator devices communicating via Wi-Fi (primary)
Comms	Wi-Fi preferred; Zigbee2MQTT where needed; MQTT supported
Update System	Git-based update repo, with OTA support for ESPHome devices
UI	Initial Lovelace dashboard (migratable to custom frontend later)

## ⚙️ Technical Standards & Practices
## 📡 Connectivity
●	Default: Wi-Fi

●	Zigbee or other protocols allowed when appropriate

●	Central server: runs Home Assistant, Frigate, and ESPHome

## ⚛️ Microcontrollers
●	ESP32 preferred for all modules

●	Use compact, power-efficient variants with low idle draw

## 🧑‍💻 Firmware
●	ESPHome is the required standard unless justified otherwise

●	All firmware must support OTA updating via Home Assistant

●	Code must be clean, modular, and commented

## 🗂️ Update & Version Control
●	All code/config must be easily updatable via a central Git repo

●	HA dashboard, ESPHome YAMLs, and configurations will be pulled automatically

 
## 🔐 Design & Safety Guidelines
●	Default to 12V DC systems (future 24V/48V flexibility is welcome)

●	Prefer MOSFETs over mechanical relays (mobile safety, vibration)

●	Space-constrained: All modules must be compact and mountable inside van electrical compartments

●	Enclosures must be safe for consumer use (no exposed wires/pins)

●	Fusing is centralised — modules do not require onboard fusing unless risk demands it

●	Fail-open or fail-closed logic depends on use-case — designers must justify based on scenario

 
## 🧠 Main Hub

## Goals:
●	Central brain of the system housing the Home Assistant core.
●	Reliable wireless + wired communication with modules.
●	Local automation and dashboard server.
## Functions:
●	Mini PC (e.g., Intel N100/N97, Nucbox G5) running Home Assistant.
●	Local storage for historical data and logs.
●	Integrated LTE router for internet access (UMR Ultra)
●	GPS module for geolocation and heading.
●	IMU (accelerometer, gyroscope) for detecting movement or tilt (van level).
●	Other environment sensors (cheap but massive value adds)
●	Local VPN server (or Nabu Casa) for secure remote access.

## 🧱 Subsystem Modules
Each module should be:
●	Standalone

●	OTA updateable

●	Documented with YAML, wiring, and entity structure

●	Delivered as a logical unit with a BOM

 
## 1. 🔋 Electrical Monitoring
Goals: 
●	Monitor all aspects of the van’s 12V DC electrical system.
●	Enable smart automation and fault alerts.
●	Support switching loads and tracking system performance over time.
Functions: 
●	Battery voltage, current, power, and energy monitoring.
●	Solar input tracking, inverter status, and charging states.
●	DC-DC charger status monitoring.
●	Inverter control (on/off via relay/mosfet).
●	Current sensing for major circuits (lights, fans, fridge, etc.).
●	Temperature sensing for batteries or compartments.
●	Provide alerts for low power or critical issues.
●	Monitor 230V AC if shore power/inverter is included.

## 2. ⚡ Smart Fuse Box
Goals: 
●	Combine traditional fuse panel with smart relay and monitoring features.
●	Enable remote on/off control per circuit and current draw monitoring.
Functions: 
●	Combined fuse & relay control
●	Monitor current per circuit (INA219 or similar)
●	Switch circuits on/off via HA (PWM dimmable)
ESP32 control via ESPHome

## 3. 💧 Water System
Goals:
●	Provide clear tank level information and allow smart pump/heater control, as well as fixture monitoring and control. 
Functions:
●	Monitor fresh, grey, and black tank levels (resistive or ultrasonic).
●	Water pump on/off switching (manual and automated).
●	Water heater control (tankless or immersion).
●	Flow rate tracking (via turbine sensor).
●	Leak alerts or dry-run protection for pump.
●	Trigger automatic shutoffs or reminders (e.g., low tank).
## 4. 🛡 Security & Safety
Goals:
●	Keep the van and its occupants safe from theft, gas leaks, fire, and intrusion.
Functions:
●	Door/window contact sensors (open/closed).
●	Motion sensors inside van.
●	Tilt/vibration sensors.
●	12V siren + strobe.
●	Central arming/disarming logic.
●	Gas leak detectors (LPG, CO, CO₂).
●	Smoke detector integration.
●	Central locking or deadbolt integration.

## 5. 📷 CCTV / Cameras
Goals:
●	Provide remote and local visual monitoring inside and outside the van.
Functions:
●	IP cameras (ONVIF/RTSP) for interior/exterior use.
●	Night vision support.
●	Motion-triggered recording.
●	Viewable via Home Assistant dashboard or app.
●	Alerts on motion when armed.
●	Optional: recording to local SSD or NAS.
●	PIR motion sensors? 

## 6. 🌐 Networking & Remote Access
Goals:
●	Allow full remote access to dashboards, alerts, and camera feeds.
●	Enable mobile data connectivity in areas without Wi-Fi.
Functions:
●	UMR Ultra LTE router (dual SIM, external roof-mounted antenna)
●	Wi-Fi signal monitoring.
●	VPN-based remote access (e.g., WireGuard, Tailscale) or Nabu Casa
●	OTA update system via Git or web panel.
●	Signal strength diagnostics.
●	Unifi HACS add on

 
 
## 🏗️ Development Standards
##📦 Deliverables (Per Module)
●	✅ Bill of Materials (with links and prices)

●	✅ Wiring diagram (hand-drawn, schematic; PCB design in KiCad or similar if appropriate aswell as necessary files inc. Gerber, BOM, Pick and place, etc)

●	✅ ESPHome YAML or MQTT config (unless discussed otherwise)

●	✅ Expected entity list (following naming convention)

●	✅ Screenshot or video of test in HA

●	✅ Estimated cost and power draw

●	✅ Documentation (README or Loom video preferred)

##🧪 Testing & Validation
●	I (the project owner) will test each module on a development bench

●	Prototypes must function reliably, without safety issues

●	Code must work in HA, and OTA firmware updates must succeed

●	Module must pass stress testing, restart without failure, and act safely

 
 
## 🧩 Naming Convention for Entity IDs
Standard format:
<domain>.<device>_<function>_<location>
Examples:
●	sensor.battery_voltage_main

●	switch.pump_water_kitchen

●	binary_sensor.door_rear_open

●	camera.interior_front_view

●	sensor.tank_level_fresh

 
## 👷‍♂️ Freelancer Guidelines
## 🚦 Creative Freedom & Responsibility
●	You are encouraged to propose better, cheaper, or more effective approaches

●	Consider the end user experience in your decisions

●	Think like a product designer - not just a coder, I want to help you develop your product design skillset and progress in your career, too. 

●	Suggest alternate parts or designs if they improve value or usability

📢 Communication Expectations
●	I’m available for questions within a few hours

●	Please check in a few times during your timeline, especially if blocked for any reason

●	I expect to receive partial progress updates before final delivery

 
## 🛠 BOM Strategy
●	Prioritize affordability and reliability - use your common sense to weigh up price, performance, size, power draw, etc

●	Prefer AliExpress, Banggood, or cheaper retailers, depending on value

●	Minimize complexity unless justified

 

## 🧭 Design Priorities
1.	Simplicity First: Users should be able to plug in and go with no setup required. Preloaded dashboards and OTA updates.
2.	Customisable for Power Users: Full access to Home Assistant configuration, editable automations, templates, and dashboards.
3.	Modular by Default: Easy to add/remove subsystems. No monolithic logic — each module works independently.
4.	Reliable & Offline-First: Fully functional without internet. Robust against power loss, mobile connectivity drops, and harsh conditions.
5.	Maintainable: One-click updates via Git. OTA updates for ESP modules. Documented and versioned configs.

## 🧑‍💻 Developer & Freelancer Philosophy

Every module should be:
●	Standalone and testable
●	Reproducible and clearly documented
●	Built from standard, affordable parts
●	Easy to wire and flash
●	OTA update-compatible
 
## 📁 File & Code Management
●	Delivery via Fiverr is acceptable, but reusable code should also be kept structured

●	GitHub folders will be organized by module or component

●	Ultimately, most parts of this system will be open-source (except sensitive IP)
●	I am very open to hear suggestions on how the code and update deployment should be managed. 

 
## 🔄 Software Integration
●	Home Assistant is the brain

●	ESPHome is the interface for all ESP32-based hardware

●	Zigbee2MQTT can be used for sensors (if ESPhome will not work, please discuss)

●	Dashboard is Lovelace for MVP; custom frontend is planned later

●	All modules must integrate smoothly into HA without breaking updates or naming conventions


