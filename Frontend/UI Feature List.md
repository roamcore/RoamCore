# VanCore Demo Dashboard – Frontend Functionality Breakdown
This document lists all UI elements and potential UI elements for the VanCore dashboard/app.
It is designed as an exhaustive checklist – you can remove anything you don’t need, but you shouldn’t need to add new items.
Sections (matching the current dashboard):
*	Global (header, time, weather)
*	Power System
*	Lighting Control
*	Climate Control
*	Water System
*	Van Level
*	GPS & Travel
*	Network
*	Media
*	Automation
*	Security System

## 1. Global / App Shell
These elements sit at the top or are “global context”.
### 1.1 Header Bar
*	Title – "Van Control Dashboard"
*	Dark Mode toggle – text: "Dark Mode" + on/off control
*	Settings button – "Settings"

**Global / App Shell – possible data points and controls (edit down as needed):**
*	App logo / VanCore logo
*	Van name or profile (e.g. "Sprinter 4x4", "Family Van")
*	User profile / avatar (for multi-user setups)
*	Quick navigation tabs (e.g. Overview, Power, Climate, Water, Security)
*	Global search bar (search devices, automations, camera names, etc.)
*	Global notifications icon (alerts, warnings, reminders)
*	System health indicator (e.g. "All systems OK", or warning badge)
*	Global connection state (online/offline cloud access)
*	Global edit / layout mode toggle (switch between control mode and layout edit mode)
*	Quick actions menu (e.g. "All lights off", "Night mode", "Leaving van")
*	Profile switcher (for multiple vans or installations)
*	Language selector (if needed)

### 1.2 Time & Date
*	Section label – "Current Time"
*	Time display – current local time (digital clock)
*	Date display – current day and calendar date

**Time & Date – possible data points and controls (edit down as needed):**
*	Current local time (digital clock)
*	Current day and date
*	12-hour vs 24-hour time format toggle
*	Local timezone / location source display (e.g. "Auto via GPS" or manual)
*	Sunrise time today
*	Sunset time today
*	Indication of whether it is currently day or night
*	Quiet hours indicator (show if within user-defined quiet period)
*	Quiet hours configuration (start/end times)
*	Next calendar event (if calendar is connected)
*	List of today’s events (simple, next few only)
*	Reminder banner (e.g. "Check out by 11:00", "Service due soon")

### 1.3 Weather Summary
*	Section label – "Weather"
*	Outside temperature
*	Weather condition text (e.g. sunny, cloudy, rain)
*	Humidity
*	Wind speed

**Weather – possible data points, forecasts and controls (edit down as needed):**
*	Current outside temperature
*	Feels-like temperature
*	Short condition text plus icon (sun, cloud, rain, etc.)
*	Today high and low temperatures
*	Chance of rain in the next few hours
*	Expected precipitation in the next hour
*	Rain rate (if currently raining)
*	Wind speed and direction
*	Gust speed (if above a useful threshold)
*	Humidity
*	UV index (daytime only)
*	Cloud cover percentage
*	Air pressure and pressure trend (rising / steady / falling)
*	Dew point
*	Hourly temperature trend for the next 6–12 hours
*	Hourly rain probability for the next 6–12 hours
*	Simple "good driving window" indicator (time window with dry conditions and low wind)
*	Simple "good solar window" indicator (time window with clear or mostly clear skies)
*	Next 3–5 days forecast (day name, high/low, condition icon)
*	Weather alerts / warnings indicator (e.g. wind, storms, extreme heat/cold)
*	Link or button to open detailed weather page
*	Units controls (°C/°F, km/h or mph, mm or inches)
*	Location mode (GPS-based vs fixed location)
*	Toggle to show/hide advanced weather metrics
*	Notification options (e.g. freeze warning, high wind warning, "notify before sunset")

## 2. Power System Section – "Power System"
*	Section label – "Power System"

### 2.1 Battery Card
*	Battery label – "Battery Level"
*	Battery charging state (charging / discharging / idle)
*	Battery percentage (state of charge)
*	Battery voltage
*	Battery current (amps)
*	Battery power (watts in/out)
*	Estimated time remaining at current usage
*	Estimated time to full when charging
*	Battery temperature
*	Battery health status (good / warning / critical)
*	Battery chemistry / profile (e.g. LiFePO4, AGM)
*	Number of battery banks / modules
*	Per-battery-bank state of charge
*	Per-battery-bank voltage and current
*	Battery error or warning indicator
*	Tap/click area to open detailed battery view

### 2.2 Input Power Card
*	Input power label – "Input Power"
*	Total input power (watts)
*	Per-source input power for:
	◦	Solar
	◦	Alternator / DC-DC charger
	◦	Shore power
	◦	Generator
*	Input source description (e.g. "Solar + Shore")
*	Solar status (producing / not producing)
*	Solar array voltage and current
*	Shore connection state (connected / disconnected)
*	Shore current limit setting (amps)
*	Generator status (on / off / auto)
*	Alternator charging state (active / inactive)
*	Policy/mode selector for input priority (e.g. "Solar first", "Shore priority")
*	Tap/click area to open detailed input sources view

### 2.3 Output Power Card
*	Output power label – "Output Power"
*	Total output power (watts)
*	Output destination description (e.g. "To Inverter")
*	Per-bus output (DC bus, AC bus)
*	Per-subsystem power use (e.g. "House loads", "Heating", "Appliances")
*	Inverter state (on / off / standby)
*	Inverter load percentage
*	Inverter output voltage and frequency
*	Critical vs non-critical loads breakdown
*	Tap/click area to open detailed loads view

### 2.4 Total Power Draw Card
*	Power draw label – "Power Draw"
*	Power draw value – total live usage (watts)
*	Sub-label – "Current Usage"
*	Average power over last X minutes
*	Peak power today
*	Daily energy used (kWh) today
*	Daily energy used (kWh) yesterday
*	Rolling 7-day or 30-day energy usage
*	Simple usage graph preview
*	Tap/click area to open full history/graph view

**Power System – possible extra data points and controls (edit down as needed):**
*	System nominal voltage (12 V / 24 V / 48 V)
*	DC bus voltage and current
*	AC bus voltage, current and frequency
*	Per-circuit fuse/breaker status
*	Per-circuit on/off switches (soft switching)
*	Error flags for overcurrent, overvoltage, undervoltage
*	Temperature of key components (inverter, DC-DC, MPPT, etc.)
*	"Eco mode" toggle (limit inverter, dim non-critical loads)
*	"Shore priority" vs "Battery priority" vs "Balanced" mode toggle
*	"Generator auto-start" toggle and configuration
*	Charge/discharge current limit sliders
*	SOC minimum/maximum limits for charge controller
*	Battery equalization / maintenance controls (for non-LFP chemistries)
*	Maintenance reminders (e.g. "Check battery terminals")
*	Export button for power logs or CSV
*	Quick actions such as "Turn off non-critical loads" or "Force bulk charge"

## 3. Lighting Section – "Lighting Control"
*	Section label – "Lighting Control"

### 3.1 Master Lighting
*	Master lighting control – global lights on/off toggle
*	Overall lights status – text state (e.g. "Lights On")
*	Active lights count (number of zones or fixtures currently on)

### 3.2 Global Brightness
*	Global brightness label – "Brightness"
*	Global brightness slider / control (0–100%)

### 3.3 Individual Zones
*	Kitchen lights switch – on/off
*	Bedroom lights switch – on/off
*	Shower lights switch – on/off
*	Exterior lights switch – on/off

**Lighting – possible extra data points and controls (edit down as needed):**
*	Per-zone brightness sliders (e.g. kitchen, bedroom, shower, exterior)
*	Per-zone colour temperature controls (warm → cool white)
*	Per-zone RGB colour controls (for strips/accent lighting)
*	Lighting scenes (presets) such as:
	◦	Day mode
	◦	Night mode
	◦	Movie mode
	◦	Cooking mode
	◦	Reading mode
*	Scene selection buttons / chips
*	"All interior off" quick action
*	"All exterior off" quick action
*	Occupancy-based lighting (auto on/off using motion sensors)
*	Ambient light sensor integration (auto-dimming based on light level)
*	Per-zone schedule (e.g. "Exterior lights on at sunset, off at 23:00")
*	Sunrise/sunset-based automations
*	"Red night mode" toggle (soft red lights to preserve night vision)
*	Child lock / accidental touch lock for key lighting controls
*	Temporary timer (e.g. "Turn all lights off in 10 minutes")
*	Per-zone energy usage display
*	Per-zone rename/edit feature (e.g. rename "Kitchen Lights" to "Galley")
*	Indicator for lights left on when van is locked/armed

## 4. Climate Section – "Climate Control"
*	Section label – "Climate Control"

### 4.1 Roof Fan / Vent
*	Vent display – e.g. "Maxxair Fan 45% open"
*	Vent position slider (0–100% open)
*	Vent open/close buttons (fully open / fully close)
*	Vent direction (intake / exhaust) selector

### 4.2 Fan Speed
*	Fan speed label – "Fan Speed"
*	Fan speed control (step-based or slider)
*	Fan on/off toggle

### 4.3 Interior Temperature & Comfort
*	Inside temperature display
*	Target temperature setpoint (for heater/AC)
*	Climate mode selector (Off / Heat / Cool / Fan only / Auto)
*	Inside humidity display
*	CO₂ level display (if sensor available)
*	VOC / air quality indicator (if sensor available)

**Climate – possible extra data points and controls (edit down as needed):**
*	Diesel heater control (on/off, power level)
*	Electric heater control (on/off, power level)
*	Air conditioning control (on/off, fan speed, swing)
*	"Silent night" mode (reduced fan/heater noise)
*	"Boost" mode (max power for quick heating/cooling)
*	Thermostat schedule (time-based temperature setpoints)
*	"Frost protection" mode (keep above a minimum temperature)
*	Window/door open detection and energy-saving logic
*	Automatic venting based on temperature/humidity
*	Condensation protection mode (manage humidity and temperature)
*	Integration with bed occupancy (reduce heating when not in bed)
*	Graph of inside temperature over last X hours
*	Graph of inside humidity over last X hours
*	Alerts for high CO₂ or poor air quality
*	Alerts for too cold / too hot conditions

## 5. Water Section – "Water System"
*	Section label – "Water System"

### 5.1 Tank & Flow
*	Fresh water tank percentage
*	Flow rate display (e.g. L/min)

### 5.2 Pump
*	Pump status label – e.g. "Pump Status"
*	Pump on/off control

**Water – possible extra data points and controls (edit down as needed):**
*	Fresh water tank absolute volume (litres or gallons)
*	Grey water tank level
*	Black water tank level (if applicable)
*	Individual tank status (OK / nearly full / full)
*	Tank temperature (for freeze risk)
*	Leak detection sensor state
*	Water pressure display
*	Water pump auto-mode (on demand vs manual)
*	Pump speed / intensity control (if variable-speed pump)
*	Pump run-time statistics and history
*	City water connection state
*	City water pressure indicator
*	Water heater on/off control
*	Water heater temperature setpoint
*	Water heater mode (gas / electric / boost / eco)
*	Recirculation loop control (e.g. instant hot water)
*	“Winterize” mode (drain tanks, blow out lines)
*	“Tank fill” mode (with automatic stop at X%)
*	Filter status / change filter reminder
*	Water quality reading (TDS or similar if supported)
*	Alerts for low fresh water
*	Alerts for full grey/black tanks
*	Alerts for detected leaks or freeze risk

---

## 6. Van Level Section – “Van Level”
*	Section label – “Van Level”
*	Pitch value (degrees, front-to-back)
*	Roll value (degrees, side-to-side)
*	Simple level indicator graphic

**Van Level – possible extra data points and controls (edit down as needed):**
*	Option to “Set current as level” (recalibration)
*	Recommended adjustment hints (e.g. “Raise front left by 2 cm”)
*	Numeric thresholds for “Good enough” (sleeping vs cooking)
*	Graph/log of van angle over time (optional)
*	Different presets for “Sleeping level” vs “Cooking level”
*	Integration with auto-levelling jacks (if present)
*	Warning if van is parked at unsafe angle

---

## 7. GPS & Travel Section – “GPS & Travel”
*	Section label – “GPS & Travel”
*	Current location name (e.g. town/area)

**GPS & Travel – possible data points and controls (edit down as needed):**
*	Latitude and longitude
*	Altitude
*	Current speed
*	Current heading (N/E/S/W)
*	Time since last movement
*	Distance travelled today
*	Total trip distance
*	Total odometer (if integrated)
*	Time driving today
*	Time parked today
*	Next destination name (if navigation linked)
*	Estimated arrival time (ETA)
*	Distance to next destination
*	Simple route summary (major roads ahead)
*	Button to open navigation app (Google Maps, Apple Maps, etc.)
*	Button to “Save this spot” (favourite location)
*	List of saved/favourite spots
*	Parking mode indicator (e.g. “Overnight”, “Day parking”)
*	Geofencing options (e.g. alerts when leaving/entering area)
*	Offline map data status (downloaded/not downloaded)

---

## 8. Network Section – “Network”
*	Section label – “Network”
*	Connection status (e.g. “Status Connected”)
*	Signal strength value (percentage or bars)

**Network – possible data points and controls (edit down as needed):**
*	Active internet source (e.g. Starlink, LTE, Campground Wi-Fi)
*	Backup source (fallback connection)
*	Data usage today
*	Data usage this month
*	Data cap and remaining quota
*	Simple data usage graph
*	Ping/latency reading
*	Simple speed test (down/up)
*	Router status (online/offline, uptime)
*	LAN IP address of router
*	WAN IP address
*	List of connected devices
*	Per-device data usage
*	Per-device block/allow controls
*	Guest Wi-Fi SSID and password display
*	QR code to join Wi-Fi
*	SSID name and password editor
*	Wi-Fi channel and band info
*	VPN status (connected/disconnected)
*	Remote access status (VanCore cloud / HA Remote / Nabu Casa)
*	Auto-failover toggle (switch to backup when main fails)
*	Priority rules for sources (e.g. “Use Wi-Fi if available, else LTE”)
*	Simple firewall profile selector (e.g. Strict / Normal / Open)

---

## 9. Media Section – “Media”
*	Section label – “Media”
*	“Now Playing” label
*	Track name / current media title

**Media – possible data points and controls (edit down as needed):**
*	Play / Pause button
*	Next track button
*	Previous track button
*	Seek / scrub bar (track position)
*	Elapsed time and remaining time for track
*	Volume slider (global)
*	Mute button
*	Per-zone volume sliders (cab, living area, bedroom, exterior)
*	Output zone selector (which speakers are active)
*	Media source selector (Spotify, Bluetooth, Radio, Local files, etc.)
*	Playlist / queue view
*	Shuffle toggle
*	Repeat toggle (off / one / all)
*	Equaliser presets (e.g. Flat, Bass boost, Voice)
*	Sleep timer (stop playback after X minutes)
*	“Chill” / “Focus” / “Party” quick playlists
*	Integration with phone as remote control
*	Indicator for offline/online media availability

---

## 10. Automation Section – “Automation”
*	Section label – “Automation”
*	Active rules label – “Active Rules”
*	Active rules count

**Automation – possible data points and controls (edit down as needed):**
*	List of all automations/rules
*	Per-automation on/off toggle
*	Per-automation tags (e.g. Power, Security, Comfort)
*	Short description of each rule (natural language)
*	Indication of which automations are currently active (conditions met)
*	Button to add new automation
*	Natural-language rule builder (“When X, do Y”)
*	Template gallery (e.g. “Turn on exterior lights at sunset”)
*	Rule details view (triggers, conditions, actions)
*	Schedule view of time-based automations
*	Conflict warnings (e.g. two rules fighting over same device)
*	Log of last runs (when each automation last fired)
*	Error indicators for failed automations
*	Import/export automations (backup/restore)
*	Bulk enable/disable (e.g. “Disable all climate automations”)

---

## 11. Security Section – “Security System”
*	Section label – “Security System”
*	System status line (e.g. “System Status Armed”)
*	Cameras active label
*	Camera count (e.g. “0/4”)
*	Motion label
*	Motion state (e.g. “Yes” / “No”)

**Security & CCTV – possible data points and controls (edit down as needed):**
*	Arm / Disarm button
*	Multiple arm modes (Away / Home / Night)
*	Entry/exit delay timers
*	Door sensor states (open/closed for each door)
*	Window sensor states
*	Lock status of each door
*	Lock/unlock controls for each door or all doors
*	Deadbolt status and control (if fitted)
*	Panic button (trigger alarm immediately)
*	Siren status and manual trigger
*	Alarm countdown display when arming
*	Alarm event history (timeline of triggers)
*	List of recent security events (doors opened, motion detected, alarm triggered)
*	Per-sensor bypass/ignore toggle
*	Camera grid with live thumbnails
*	Tap-to-open full-screen camera view
*	Camera PTZ controls (if supported: pan/tilt/zoom)
*	Snapshot/record controls per camera
*	Spotlight or IR illuminator control (if camera supports)
*	Privacy mode for cameras (disable or mask certain views)
*	Geofenced arming (auto arm when phone leaves area)
*	Presence simulation (fake occupancy mode – lights/music)
*	Notification settings (push/email for motion, door, alarm, etc.)
*	Integration with other systems (e.g. flash lights on alarm, record clip)

---

## 12. Section → Page Mapping (for Backend Planning)

These sections naturally map to pages/modules in the final product:
*	Global / Shell
Title, dark mode toggle, settings, navigation, time/date, weather, notifications.
*	Power System
Battery status, inputs, outputs, power history, protection modes, logs.
*	Lighting
Master lighting, zones, brightness, scenes, schedules, occupancy.
*	Climate
Vent and fan control, heating, cooling, comfort sensors, schedules.
*	Water
Fresh/grey/black tanks, pump, heater, leaks, winterization.
*	Van Level
Pitch/roll, levelling aids, safety.
*	GPS & Travel
Location, trips, saved spots, navigation.
*	Network
Internet source, data usage, connected devices, remote access.
*	Media
Now playing, control, zones, sources.
*	Automation
Rules, templates, logs, conflict handling.
*	Security System
Arming, sensors, cameras, history, notifications.
