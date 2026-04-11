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

## Editing

Use **Edit** in the UI (or open HA → Settings → Automations) to change the behavior.

Once edited, RoamCore will not overwrite your changes.
