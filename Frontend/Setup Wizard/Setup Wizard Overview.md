# RoamCore Setup Flow v1
*Comprehensive Onboarding & Provisioning Specification*  
_Last updated: 2025-11-18_

---

## Overview

This document defines the complete **first-time setup flow** for a RoamCore system, starting from unboxing through to a fully configured, internet-connected, personalised dashboard.

Design priorities:

- Ultra-simple onboarding for non-technical users  
- A **single QR code** entry point  
- Zero reliance on external networking hardware  
- Seamless **local + remote access using the same app / URL**  
- Robust identity binding between **user ↔ device (RoamCoreID)**  
- Modular configuration (Main Hub, Electrical, Water, Safety)  
- Future-proofed for additional modules and ecosystem components  

The VP2430 acts as:

- The **Wi-Fi access point (AP)**  
- The **router**  
- The **compute unit**  
- The **local web server**

This enables a self-contained experience that works even **without internet connectivity** when the user is connected to the RoamCore Wi-Fi.

---

# 1. QR Code Entry Point

Each RoamCore unit ships with a printed QR code linking to:

```text
https://setup.roamcore.app/?van_id=<VANCORE_ID>
```

Example:

```text
https://setup.roamcore.app/?van_id=VC-UK-00381
```

> `VANCORE_ID` is a globally unique identifier for the physical system, also printed on the product label and burned into the hub configuration.

### Key Behaviour

When the user scans the QR code:

1. It opens a **cloud-hosted PWA** (the Setup Wizard) in their mobile browser.
2. The app:
   - Reads `van_id` from the query string.
   - Stores it in local storage for the session.
   - Sends `setup_started(van_id, user_agent, timestamp)` to the backend.
3. This step does **not** require the hub to be powered on yet.
4. It works from anywhere: home, workshop, or inside the van.

**Crucial:** The QR code must remain usable for the entire lifetime of the product (for re-setup, ownership transfer, additional devices).

---

# 2. Initial Welcome Screen

### Content

- RoamCore logo + branding.
- Display of detected `VANCORE_ID` (from the URL).
- Short description of what the setup will do:
  - Hardware install guidance
  - Network configuration (internet + Wi-Fi)
  - App install to Home Screen
  - System configuration (electrical, water, safety)
- Buttons:
  - **Begin Installation**
  - **View Safety Information / Docs**

### Critical Considerations

- Tone should be reassuring:  
  > “You only need your phone. We’ll walk you through everything step by step.”
- No technical jargon (e.g. “router”, “DHCP”) on this first screen; keep it simple.

---

# 3. Hardware Installation Wizard

This stage is **instruction-only** and does not require the hub to be online.

The user should be able to follow this section even if they are completely offline.

### 3.1 Select Installed Modules

The wizard asks what is being installed:

- Main Hub (mandatory)  
- Electrical Box  
- Water Box  
- Safety & Security Box  
- (Future modules placeholder)

This allows later screens to be tailored to only the relevant modules.

### 3.2 Mounting Instructions

For each selected module:

- Show diagrams/images of recommended mounting locations.
- Show mechanical mounting details:
  - Hole patterns
  - Clearance requirements
  - Vibration/isolation notes
- Call out environmental constraints:
  - Avoiding high heat, direct water ingress, etc.

### 3.3 Cable / Harness Setup

Guide the user through:

- Connecting 12 V power input to the Main Hub.
- Connecting harnesses between Main Hub ↔ Electrical Box / Water Box / Safety Box.
- Connecting antennas (Wi‑Fi, LTE, GNSS) to the Main Hub.
- Connecting any necessary sense wires (e.g. ignition signal, shore power detection) according to diagrams.

### 3.4 Safety Checks

A quick safety checklist:

- “Confirm all connections are secure and correct.”  
- “Ensure no exposed copper or stray strands.”  
- “Install / confirm fuses in accordance with the wiring diagram.”  
- “Ensure main battery is fused correctly and appropriately sized.”

### 3.5 Power-On Step

The wizard then instructs:

> “Now switch on your RoamCore system.”

Behind the scenes:

- The VP2430 boots.
- RoamCore core services start.
- Network services start (Wi‑Fi AP + outbound connectivity).

The Setup Wizard moves to a **“Detecting Hub”** state.

---

# 4. Detecting the Hub Online

When the hub boots, it attempts an outbound registration call to:

```text
POST https://api.roamcore.app/hub/register
```

With payload such as:

```json
{
  "van_id": "VC-UK-00381",
  "firmware_version": "0.9.0",
  "hardware_model": "VP2430",
  "lan_ip": "192.168.50.2",
  "wifi_mac": "AA:BB:CC:DD:EE:FF",
  "modules": ["main_hub", "electrical", "water"],
  "timestamp": "2025-11-18T20:45:00Z"
}
```

The Setup Wizard periodically polls:

```text
GET https://api.roamcore.app/hub-status?van_id=VC-UK-00381
```

When the backend reports the hub as online:

- Display:  
  **“Your RoamCore hub is online 🎉”**

**Crucial:** This status check should be robust to reboots and flaky connections; use idempotent registration and last-seen timestamps in the backend.

---

# 5. Hub WAN (Internet) Setup

This step configures the hub’s ability to reach the internet for:

- Cloud proxy/tunnel (user remote access)
- Firmware and software updates
- Remote support (admin-only)

> The system must still be functional locally without internet, but cloud features will be unavailable.

### 5.1 WAN Connection Options

The wizard presents options in simple language:

#### Option A — Ethernet (Recommended)

Text:  
> “If you have Starlink, a van LTE router, or a campsite router, connect the RoamCore ‘Internet’ port to it using the supplied network cable.”

Behind the scenes:

- WAN interface uses DHCP.
- Hub tests connectivity to `https://api.roamcore.app/ping`.

If successful:

- “✅ Internet connection established.”

If failed:

- Offer basic troubleshooting tips (e.g. “Check the cable, router is on, etc.”).

#### Option B — Built-In LTE (If Fitted)

If the hardware includes a cellular modem:

- Request:
  - SIM provider (optional)
  - APN
  - PIN (if required)
- Apply configuration and test connection identical to Option A.

#### Option C — Skip Internet For Now

User can select:

> “Skip internet setup for now. I only want to use RoamCore locally.”

Show clear warnings:

- No remote control outside the van.
- No remote updates.
- Support may be limited until internet is configured.

---

# 6. RoamCore Wi‑Fi Setup (Hub as Access Point)

The VP2430 acts as the **primary Wi‑Fi router/AP** for the van.

This Wi‑Fi network is how:

- The user’s phone accesses the dashboard locally (even offline).
- Local devices (e.g. a tablet or control panel) access RoamCore.

### 6.1 Configure SSID and Password

Wizard pre-fills:

- SSID: `RoamCore-<LAST4_OF_VANCORE_ID>` (e.g. `RoamCore-0381`)
- Strong random password by default.

User can:

- Accept defaults.
- Change SSID.
- Change password.

### 6.2 Generate Wi‑Fi QR Code

After saving the settings, the wizard displays:

- SSID
- Password
- A **Wi‑Fi QR code** that encodes these credentials.

User instruction:

> “Open your camera and scan this code to join your RoamCore Wi‑Fi network.”

### 6.3 Apply AP Settings

The hub:

- Writes Wi‑Fi config.
- Restarts AP if necessary.

The wizard warns:

> “We will briefly restart the RoamCore Wi‑Fi. If you are already connected, you may be disconnected for a moment.”

### 6.4 User Connects to RoamCore Wi‑Fi

The wizard now shows a screen:

- “Connect to `RoamCore-XXXX` Wi‑Fi.”
- It periodically checks network status and local connectivity.

---

# 7. Local Connection Check

Once the phone joins the RoamCore Wi‑Fi, the Setup Wizard should aim for **local-first connectivity**.

### 7.1 Local Health Probe

The PWA attempts to reach local endpoints, e.g.:

```text
https://roamcore.local/status
https://192.168.50.2/status
```

(using a short timeout, e.g. 200–300 ms).

If successful:

- Mark connection mode as `local`.
- Display: **“Connected locally to your RoamCore system.”**

If not successful but cloud is available:

- Remain in `remote` mode but show a warning that local access could not yet be confirmed.

**Crucial:**

- Local endpoints must present valid HTTPS (can be self-signed or local CA) and the PWA must be prepared to trust this via appropriate UX / platform constraints.
- Local path is what allows full functionality **without internet**.

---

# 8. PWA Install (Add to Home Screen)

Goal: make RoamCore feel like a native app with a single tap.

### 8.1 PWA Requirements

The RoamCore frontend must:

- Provide a valid `manifest.json`:
  - `name`: “RoamCore”
  - `short_name`: “RoamCore”
  - `start_url`: `/`
  - `display`: `standalone`
  - Icons in required sizes for iOS/Android.
- Register a **service worker**:
  - Cache core assets for offline start.
  - Optionally cache basic UI shells.

### 8.2 Platform-Specific UX

The Setup Wizard detects the platform:

- **iOS Safari**
  - Show overlay instructions:
    - “Tap the share icon”
    - “Scroll down and tap ‘Add to Home Screen’”
- **Android Chrome / other PWA-friendly browsers**
  - Use the `beforeinstallprompt` event to show:
    - “Install RoamCore” button.
  - Fall back to manual “Add to Home Screen” instructions if necessary.

### 8.3 After Install

Once installed:

- Store a device-level token that links this app install to:
  - `user_id`
  - `van_id`
- Backend records:
  - `pwa_installed: true`
  - Device fingerprint (limited & privacy-respecting).

Display:

> **“RoamCore has been added to your Home Screen. From now on, just tap the icon to open your van dashboard.”**

---

# 9. User Account Creation & Binding

We must attach a **human identity** to the RoamCore system for:

- Ownership records
- Support
- Remote access rights
- Multi-device access in future

### 9.1 Minimal Account Flow (Recommended)

Steps:

1. Ask for:
   - Name
   - Email address
2. Present terms & privacy agreement.
3. Use **magic link** authentication:
   - Send an email with a “Sign in to RoamCore” button.
   - When tapped, it opens the PWA and completes the login.
4. On successful login:
   - Create `user_id`.
   - Bind `user_id ↔ van_id` as **owner**.
   - Store a secure auth token in local storage / secure storage.

### 9.2 Why Magic Links?

- No password management required.
- Much lower support burden.
- Works well with multi-device scenarios.
- Offline functionality preserved after initial sign-in (token cached locally).

---

# 10. System Configuration Wizard

After network & identity, the system runs a configuration wizard to map **physical wiring** and **hardware configuration** into software.

## 10.1 Module Detection & Confirmation

The hub reports:

- Which modules and boards it detects.
- Basic sensor presence.

The wizard displays:

- “We detected: Main Hub, Electrical Box, Water Box.”
- User can confirm or adjust (if something is physically present but not yet wired, they can mark it as “installed but not configured”).

---

## 10.2 Electrical Box Setup

### 10.2.1 Circuit Configuration

For each DC circuit / channel:

- Show:
  - Internal ID (e.g. `dc_output_1`)
  - Suggested name (can be blank)
- Ask user to configure:
  - Human-friendly name (e.g. “Fridge”, “Ceiling Lights – Rear”).
  - Fuse rating (amps).
  - Category:
    - Lights
    - Sockets
    - Pumps
    - Heating
    - Other

**Crucial:**  
You should enforce entry of a plausible fuse rating; use ranges or presets to reduce user error.

### 10.2.2 Battery & Power Setup

Ask for:

- Battery chemistry (AGM, LiFePO₄, etc.).
- Battery capacity (Ah).
- Nominal system voltage.
- Any special thresholds:
  - “Low battery warning at X% / Y volts”
  - “Critical battery cutoff at Z% / V volts”

Use this to:

- Configure monitoring.
- Enable default automations (battery protection, etc.).

### 10.2.3 Inverter & Charger Mapping

If these are integrated:

- Map relevant relays/sensors to:
  - Inverter on/off control.
  - Shore power detection.
  - Charger status.

---

## 10.3 Water Box Setup

### 10.3.1 Tank Configuration

Ask:

- Number of fresh water tanks.
- Number of grey/black tanks.
- For each tank:
  - Name (e.g. “Fresh 1”, “Grey”, “Black”).
  - Capacity (litres or gallons).

### 10.3.2 Pump & Heater Configuration

Map outputs:

- Main water pump relay.
- Hot water heater control relay.
- Any additional valves (e.g. tank-to-tank transfer, drain valves).

### 10.3.3 Sensor Calibration

Guide user through calibration:

- For each water level sensor:
  - “Empty the tank, then tap ‘Record empty’.”
  - “Fill the tank completely, then tap ‘Record full’.”
- For flow sensors:
  - “Run water for X seconds into a measured container and enter the volume.”

All calibration values are stored on the hub and optionally mirrored in the cloud.

---

## 10.4 Safety & Security Box Setup

### 10.4.1 Door / Lock Mapping

For each door/lock:

- Choose which input/relay maps to:
  - “Side door”
  - “Rear door”
  - “Cab doors”
- Allow naming for custom setups.

### 10.4.2 Cameras

If cameras are connected:

- Detect channels / streams.
- Ask user to name them:
  - “Rear view”
  - “Side view”
  - “Inside – living area”

### 10.4.3 Alarms & Alerts

Configure:

- Siren relay mapping.
- Trigger conditions:
  - Door open while “armed”
  - Motion detection
  - Shock sensor
- Sensitivity tiers (low / medium / high).

---

# 11. Recommended Automations (Optional)

At the end of configuration, offer a set of predefined automations (built via your internal form-based automation builder):

Examples:

- **Pump Safety:** Turn off water pump when no taps are active and pressure has dropped for X seconds.
- **Low Battery Protection:** Disable non-critical loads when battery SoC < threshold.
- **Tank Protection:** Alert when grey/black tank above N%; optionally flash lights or show warning on dashboard.
- **Night Mode Lighting:** Dim interior lights automatically after a chosen time.

User can:

- Enable all recommended automations.
- Select specific ones.
- Skip and set them up later.

---

# 12. Remote Access Setup (Cloud Proxy, User-Facing)

Purpose: allow the user to control their van **from anywhere** using the **same PWA** they use locally.

### 12.1 Behaviour Summary

- PWA always talks to `https://my.roamcore.app` as its API entry point.
- The backend decides, per request:
  - If user device is on RoamCore Wi‑Fi and local endpoint reachable:
    - Use **local mode** (direct call to hub).
  - Otherwise:
    - Use **remote mode** (cloud proxy → hub tunnel).

### 12.2 Hub Tunnel

The VP2430 maintains a persistent outbound encrypted tunnel to a cloud endpoint, e.g.:

```text
wss://cloud-tunnel.roamcore.app
```

The tunnel:

- Is initiated from the hub (no inbound ports needed).
- Is authenticated with hub credentials (bound to `van_id`).
- Handles:
  - Remote API requests
  - Reverse proxy for the dashboard UI if needed

### 12.3 Local vs Remote Detection (App-Side)

At PWA startup:

1. Try local health endpoint with a short timeout.
2. If success:
   - Mark connection as `local`.
   - Use local base URL for API.
3. If fail:
   - Use cloud base URL (which then routes via the tunnel).

**User experience:**  
They always tap the same icon. The routing is invisible.

---

# 13. Remote Support Consent (Admin-Only Access)

Remote support is separate from user remote access.

### 13.1 User-Facing Explanation

A dedicated screen explains:

- RoamCore support may need temporary access to:
  - Diagnose issues
  - Apply fixes
  - Help with configuration
- Access is:
  - Controlled by a “Remote Support” toggle.
  - Logged (who accessed, when).
  - Only possible while the hub has internet.

### 13.2 Toggle

User chooses:

- **Enable remote support**
- **Disable remote support**

The chosen state:

- Is stored on the hub.
- Is mirrored in the cloud.
- Is enforced in your admin networking layer (e.g. Headscale ACLs + firewall):

  - When OFF:
    - Support cannot reach the hub over the admin mesh.
  - When ON:
    - Support devices (tagged `support`) can access admin ports on the hub (HA, SSH, etc.).

**Crucial:** The user cannot see or interact with admin VPN details; they only control the high-level consent toggle.

---

# 14. Final Summary & Dashboard Walkthrough

### 14.1 Summary Screen

Show the result of the wizard:

- Installed modules:
  - Main Hub, Electrical, Water, Safety
- Wi‑Fi SSID (and reminder not to share password recklessly)
- Internet: Connected / Not Connected
- Remote Access: Enabled / Disabled (if internet exists)
- Remote Support: Enabled / Disabled
- Firmware version
- PWA installed: Yes/No

Provide buttons:

- **Open my RoamCore dashboard**
- **View quick-start guide**
- **Contact support**

### 14.2 First Dashboard Visit

Optionally, a short guided tour:

- “This is your power overview”
- “Here you can see water levels”
- “This area shows alerts and notifications”
- “Advanced settings live under ‘Settings’”

Keep it skippable with a “Skip tour” button.

---

# 15. Essential Edge Cases

### 15.1 No Internet During Setup

If internet setup fails or is skipped:

- Wizard should still allow:
  - Local Wi‑Fi setup
  - PWA install
  - System configuration
- Remote access and cloud features are marked as “Not available (internet not configured).”

Later, once internet exists, the user should be able to re-run a simplified **Connectivity Setup** flow from inside the app.

### 15.2 Hub Not Detected

If the hub does not appear as online:

- Show troubleshooting steps:
  - Confirm power and LEDs.
  - Check wiring.
  - Reboot hub.
- Provide a “Manual local mode”:
  - If the user is already on RoamCore Wi‑Fi, attempt direct local access even if cloud registration isn’t seen yet.

### 15.3 User Never Joins RoamCore Wi‑Fi

If the user doesn’t join the Wi‑Fi or struggles:

- Keep showing the Wi‑Fi QR code.
- Provide platform-specific help (“How to join Wi‑Fi on iOS/Android”).
- Allow them to skip and return later, but clearly state that **local control requires connecting to the RoamCore Wi‑Fi**.

### 15.4 Multiple Devices / Family Members

Same QR code and/or invitation link can be used later:

- Partner scans QR.
- Signs in or accepts invite.
- Gains access to the same `van_id`.
- Is prompted to add RoamCore to their Home Screen as well.

---

# 16. Security Requirements (High-Level)

- **TLS everywhere**:
  - Cloud endpoints must use valid public certificates.
  - Local endpoints should use HTTPS; consider:
    - Local CA
    - Device-pinned certs
- **Per-device tokens**:
  - Each PWA install should have its own token tied to `user_id` and `van_id`.
- **No user control over firewall / admin VPN**:
  - Users only see high-level consent (remote support toggle).
- **Least privilege**:
  - App roles (owner vs future guest accounts).
  - Admin support mesh strictly separated from user remote access path.
- **Logging**:
  - Remote support sessions logged (who/when/which `van_id`).

---

# 17. Data Model Summary (Conceptual)

### 17.1 Hub Identity

```text
van_id
serial_number
hardware_revision
firmware_version
modules_installed[]
last_seen_timestamp
```

### 17.2 User Identity

```text
user_id
email
name
auth_tokens[]
owns_van_ids[]
invited_van_ids[]
```

### 17.3 Configuration Snapshot

```text
van_id
electrical_config {
  circuits: [
    {
      id,
      name,
      fuse_rating,
      category
    }
  ],
  battery: { chemistry, capacity, thresholds... },
  inverter: { ... },
  chargers: [ ... ]
}
water_config {
  tanks: [
    { id, name, capacity }
  ],
  pumps: [ ... ],
  heaters: [ ... ],
  calibration_data: { ... }
}
safety_config {
  locks: [ ... ],
  cameras: [ ... ],
  alarms: [ ... ]
}
automations: [ ... ]
wifi_config {
  ssid,
  password_hash,
  last_changed
}
remote_support_enabled: boolean
```

---

# 18. State Diagram (Mermaid)

```mermaid
flowchart TD
    A[Scan QR] --> B[Setup Wizard Opens]
    B --> C[Hardware Installation Guide]
    C --> D[Hub Powered On]
    D --> E{Hub Detected via Cloud?}
    E -->|Yes| F[WAN / Internet Setup]
    E -->|No| D
    F --> G[Configure RoamCore Wi‑Fi (AP)]
    G --> H[User Joins RoamCore SSID]
    H --> I{Local Endpoint Reachable?}
    I -->|Yes| J[Local Mode Established]
    I -->|No| F
    J --> K[PWA Install (Add to Home Screen)]
    K --> L[Create/Verify Account]
    L --> M[Bind user ↔ van_id]
    M --> N[Module Detection]
    N --> O[Electrical/Water/Safety Config]
    O --> P[Recommended Automations]
    P --> Q[Remote Access Setup (Cloud Proxy)]
    Q --> R[Remote Support Consent]
    R --> S[Summary & Finish → Dashboard]
```

---

# 19. Summary

This setup flow ensures that:

- **Non-technical users** can get from box-opening to a working dashboard with minimal friction.
- There is a **single QR code** and a **single app icon** that works both **locally and remotely**.
- The system is usable **offline** when on the RoamCore Wi‑Fi.
- Identity and configuration are robustly tied to `van_id` for support and future features.
- Remote access and remote support are clearly separated, with strong security and user consent.
- The solution is **appliance-grade**, not a DIY/hobbyist experience, aligning with RoamCore’s product and brand goals.
