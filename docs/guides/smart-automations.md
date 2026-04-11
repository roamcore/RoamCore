# RoamCore Smart Automations (v0.1)

RoamCore includes a small set of **prebuilt Home Assistant automations** designed to be:

- **1‑click enable/disable**
- **safe and predictable**
- **fully native Home Assistant automations** (editable in HA)
- **transparent** (no hidden automation engine)

You can manage these from:

**RoamCore → Settings → Smart Automations**

## How it works

- When you click **Enable**, RoamCore creates (if missing) a standard HA automation via the HA config API.
- RoamCore sets a managed marker in the automation **description**:

  - `Managed by RoamCore Smart Automations v0.1`
  - `key=<name>`
  - `hash=<template hash>`

- If you later edit the automation in Home Assistant (changing triggers/actions), RoamCore will **stop updating** its logic.
  - It will still allow **Enable/Disable**.

## Included automations

### 1) RoamCore - Night Mode

**What it does:**

- At **23:00** → sets RoamCore Mode to **Stealth**
- At **07:00** → sets RoamCore Mode back to **Auto**

**Dependencies:**

- `script.rc_mode_set_stealth`
- `script.rc_mode_set_auto`

### 2) RoamCore - Auto Internet Failover

**What it does:**

- If `sensor.rc_net_wan_status` becomes `bad` for 2 minutes → calls `script.rc_openwrt_prefer_auto`

**Dependencies:**

- `sensor.rc_net_wan_status`
- `script.rc_openwrt_prefer_auto`

### 3) RoamCore - Low Battery Mode

**What it does:**

- If `sensor.rc_power_battery_soc` stays below **20%** for 10 minutes and shore power is **disconnected** → calls `script.rc_mode_set_camp`

**Dependencies:**

- `sensor.rc_power_battery_soc`
- `binary_sensor.rc_power_shore_connected`
- `script.rc_mode_set_camp`

### 4) RoamCore - Freeze Protection

**What it does:**

- If outside temperature stays below **2°C** for 10 minutes → creates a persistent notification + logbook entry.

**Dependencies:**

- `sensor.rc_weather_temp_c`

### 5) RoamCore - Daily Trip Log

**What it does:**

- At **23:59** → writes a simple daily trip summary to HA Logbook.

**Dependencies:**

- `sensor.rc_trip_distance_today_mi`
- `sensor.rc_trip_time_today`

### 6) RoamCore - Battery Full Alert

**What it does:**

- If battery SOC stays above **95%** for 15 minutes → creates a notification + logbook entry.

**Dependencies:**

- `sensor.rc_power_battery_soc`

### 7) RoamCore - Inverter Overheat Alert

**What it does:**

- If inverter temperature stays above **75°C** for 5 minutes → creates a notification + logbook entry.

**Dependencies:**

- `sensor.rc_power_inverter_temperature`

### 8) RoamCore - Router Overheat Alert

**What it does:**

- If router temperature stays above **70°C** for 10 minutes → creates a notification + logbook entry.

**Dependencies:**

- `sensor.rc_router_temperature`

### 9) RoamCore - Shore Power Connected

**What it does:**

- When shore power connects → notification + logbook entry.

**Dependencies:**

- `binary_sensor.rc_power_shore_connected`

### 10) RoamCore - Shore Power Disconnected

**What it does:**

- When shore power disconnects for 1 minute → notification + logbook entry.

**Dependencies:**

- `binary_sensor.rc_power_shore_connected`

### 11) RoamCore - Internet Recovery

**What it does:**

- If internet is unreachable for 2 minutes → triggers a router network restart script.

**Dependencies:**

- `binary_sensor.rc_net_internet_reachable`
- `script.rc_openwrt_restart_network`

### 12) RoamCore - Arrive at Camp

**What it does:**

- If speed stays below **1** for 15 minutes between **18:00–23:59** → sets Mode to **Camp**.

**Dependencies:**

- `sensor.rc_location_speed`
- `script.rc_mode_set_camp`

### 13) RoamCore - Depart (Travel Mode)

**What it does:**

- If speed stays above **10** for 2 minutes → sets Mode to **Travel**.

**Dependencies:**

- `sensor.rc_location_speed`
- `script.rc_mode_set_travel`

### 14) RoamCore - Solar is Crushing It

**What it does:**

- If solar stays above **600W** for 5 minutes → notification + logbook entry.

**Dependencies:**

- `sensor.rc_power_solar_power`

### 15) RoamCore - Battery Critical Alert

**What it does:**

- If battery SOC stays below **10%** for 5 minutes → notification + logbook entry.

**Dependencies:**

- `sensor.rc_power_battery_soc`

### 16) RoamCore - Bedtime Level Check

**What it does:**

- At **22:00**, if you are not level → reminder notification + logbook entry.

**Dependencies:**

- `binary_sensor.rc_level`
- `sensor.rc_level_status`

### 17) RoamCore - Quiet Hours Reminder

**What it does:**

- At **21:30**, if Mode is not Stealth → reminder notification.

**Dependencies:**

- `input_select.rc_mode`
- `script.rc_mode_set_stealth`

## Editing

Use **Edit** in the UI (or open HA → Settings → Automations) to change the behavior.

Once edited, RoamCore will not overwrite your changes.
