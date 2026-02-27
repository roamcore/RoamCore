# RoamCore MVP — **UI / UX Design Brief**

## Project Backstory & Context (For the Designer)

RoamCore is a **local‑first control system for van‑life**, designed to replace the fragmented setup most van owners live with today.

Typical vans rely on multiple disconnected systems:

- a Victron display for power
- a router or Maxview screen for internet
- physical spirit levels and light switches/misc screens
- separate apps, widgets, and guesswork

RoamCore’s goal is to **collapse all of this into a single, calm, trustworthy interface** that works out of the box for non‑technical users, while remaining open and extensible for advanced users.

This project is **not a smart‑home dashboard**. It is closer to a **vehicle instrument panel** or **marine control unit**:

- reliable
- simple
- confidence‑inspiring
- boring in the best possible way, but still modern and clean

The UI you are designing starts with the **main landing page** of this system — the page a user will see multiple times a day. It must prioritise clarity and reassurance over features or visual complexity.



Below are the key pages that must be included. Please consider the following **core design philosophies** while designing the UI/UX:

- **Reassurance first** – the UI should reduce anxiety before it provides information
- **One-glance clarity** – the user should understand system state in under 5 seconds - highly intuitive
- **Replace, don’t add** – this must feel simpler than the multiple systems it replaces
- **Status over data** – qualitative states are preferred over raw metrics (eg. colour coded status - good, ok, bad)
- **Familiar before clever** – reuse mental models from existing van systems, users should be able to intuitively use the new system since it is similar to legacy UI (dials, buttons, switches, etc)
- **Progressive disclosure** – hide complexity until the user asks for it
- **Appliance mindset** – the system should feel reliable, finished, and boring (in a good way)
- **Non-technical by default** – power users are supported, but never prioritised/assumed

---

# **Main Landing Page**

## 1. Purpose of the Main Page

The main landing page exists to answer **one question only**:

> **“Is my van OK right now?”**

This page is a **status surface**, not a control panel.

If the user looks at it for 3–5 seconds, they should feel either:

- reassured, or
- clearly alerted that something needs attention

Nothing else.

---

## 2. Target User

- Living or travelling in a van
- Non-technical
- Does not enjoy dashboards or data
- Currently relies on:
  - Victron screens
  - router / Maxview apps
  - phone widgets
  - guesswork

They want:

- simplicity
- confidence
- trust
- clarity

The page must **never feel overwhelming**.

---

## 3. Core Design Principles (Non‑Negotiable)

### 3.1 Extreme simplicity

- Fewer elements > more elements
- Fewer numbers > more numbers
- Fewer colours > more colours

If something is not essential, it does not belong on this page.

---

### 3.2 Recognition over interpretation

Users should **recognise states**, not interpret data.

Examples:

- “Battery OK” instead of voltage/current
- “Internet: Good” instead of signal metrics
- “Level: Steep/Mild/Flat” instead of raw angles

---

### 3.3 Familiar mental models

The UI should feel familiar to users coming from:

- Victron battery displays
- Maxview / router signal indicators
- Spirit levels
- Simple tank gauges

This should feel like a **clean unification of existing systems**, not a new technical tool.

---

### 3.4 Progressive disclosure

- Main page = summary only
- Tapping a tile = more detail
- Advanced views live elsewhere

The main page should never feel “busy”.

---

### 3.5 Appliance, not software

The experience should feel like:

- a car dashboard
- a boat instrument panel
- a premium control unit

Not:

- a smart home dashboard
- a data analytics UI
- a configuration interface

---

## 4. Page Structure (High Level)

The page has **three zones only**:

1. **Header (very light)**
2. **Primary status tiles (core of the page)**
3. **Secondary tiles (visually de‑emphasised)**

No sidebars.\
No complex navigation.\
Prefer no scrolling on tablet.

---

## 5. Header (Minimal)

### Purpose

- Orientation and context only

### Must include

- Current time
- Basic weather (icon + temperature)
- Small icons for:
  - notifications
  - settings
  - dark/light theme toggle (optional)

The header should feel **backgrounded**, not central.

---

## 6. Primary Status Tiles (Most Important)

These tiles are the **visual focus of the page**.\
They must be readable at a glance and from a distance.

Each tile:

- communicates state instantly
- uses colour sparingly, yet effectively to convey state
- is tappable for details

---

### 6.1 Power Tile (Required)

**Purpose:**\
Answer: *“Do I have enough power?”*

**Must show**

- Battery state of charge (single large value)
- Simple qualitative state:
  - Good / OK / Low
- Estimated time remaining (smaller subheading)

**Must NOT show**

- Voltage
- Current
- Solar breakdown
- Graphs
- Configuration

This tile replaces frequent checks of Victron screens.

---

### 6.2 Connectivity Tile (Required)

**Purpose:**\
Answer: *“Am I connected, and is it reliable?”*

**Must show**

- Connection quality:
  - Good / OK / Poor
- Active internet source:
  - Starlink
  - 4G / 5G
  - Hybrid / failover

**Must NOT show**

- Signal numbers
- SSIDs
- IP addresses
- Router complexity

This tile replaces router apps and Maxview displays.

---

### 6.3 Level Tile (Required)

**Purpose:**\
Answer: *“Am I level enough to sleep?”*

**Must show**

- Simple visual representation of van orientation
- Clear guidance:
  - Level
  - Slightly off
  - Not level

**Must NOT show**

- Raw IMU axes
- Calibration steps
- Graphs

This tile replaces physical spirit levels and phone apps.

---

## 6.4 Water Tile (REQUIRED)

**Purpose:**\
Answer: *“Do I have enough water, and is anything wrong?”*

**Should show:**

- Fresh water level (simple gauge or qualitative state: Full / OK / Low)
- Grey water level (OK / Nearly full)
- Optional pump state (On / Off)

Information should be:

- easy to understand at a glance
- qualitative by default
- focused on reassurance rather than precision

**Must NOT show**

- Raw percentages by default
- Flow rates
- Per‑fixture breakdowns
- Graphs or historical data

---

## 7. Secondary Tiles (De‑Emphasised)

These tiles should exist, but **must not compete** with the primary tiles.

---

### 7.2 Automations Tile

**Purpose:**\
Entry point only.

**Must show**

- A label/button to enter automations

**Must NOT show**

- Lists
- Counts
- Statuses
- Logic

Think “shortcut”, not “dashboard”.

---

### 7.3 Map / GPS Tile

**Purpose:**\
Context, not navigation.

Includes:

- Current location
- Very recent route (line on map)
- Small trip summary (today / total miles)

**Must NOT show**

- Full map UI
- Controls
- POI clutter
- Layers

This is awareness, not planning.

---

## 8. Colour & State System

Colour communicates **meaning**, not decoration.

### Allowed states

- Green → good / safe
- Amber → attention soon
- Red → action required
- Grey → not installed / unavailable

### Rules

- One state colour per tile
- No rainbow UI
- Text must still work without colour

---

## 9. Typography & Density

- Large text for reassurance
- Small text for context
- Generous spacing
- No dense clusters
- No tables

The page should feel calm and breathable.

---

## 10. Explicit Non‑Goals

This page is **not**:

- a configuration interface
- a Home Assistant showcase
- a metrics dashboard
- a developer or power‑user surface

Those belong elsewhere.

---

## 11. Deliverables Expected from Designer

- One main landing page (tablet‑first)
- Mobile version (secondary, just a much thought - everything must be visible on one screen without scrolling)
- Clear visual hierarchy
- Light and dark themes
- Short annotations explaining design decisions



This explains the main considerations, and the main landing page. Below is more detail for each sub page when you click on each of these tiles. 

