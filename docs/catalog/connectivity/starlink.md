# Starlink

Starlink is a self-hosted mobile-internet terminal (Gen-2/Gen-3 dish + router).

## 5-step IKEA howto

### 1. Pick your setup

The setup wizard asks ONE question: **how do you want to use Starlink in the van?** Three answers:

- **Starlink Mini as my only router** — use the built-in Starlink Wi-Fi router, nothing else. Simplest setup (~10 min, nothing to plug in besides power).
- **I have a separate router** — you own a third-party router + a controllable smart plug behind the Starlink PSU (~25 min).
- **VM router inside the VP2430** — you run an OpenWrt VM as the LAN router, with Starlink as the WAN upstream (~30 min).

Not sure? The wizard asks the question; you pick the answer; RoamCore does the rest.

### 2. Answer 2-3 questions

The wizard asks only what it needs:

- **Path A (Mini only):** no questions. RoamCore auto-detects your Starlink router at `192.168.100.1` and verifies it's reachable.
- **Path B (separate router):** the wizard asks for the HA `switch.*` entity ID of your smart plug. RoamCore validates the plug is exposed + controllable before wiring anything.
- **Path C (VM router):** the wizard asks for the OpenWrt API URL (e.g. `http://192.168.1.250/cgi-bin/luci`) + bearer token. RoamCore verifies the API is reachable before writing helpers.

### 3. RoamCore does the rest

The wizard writes the right helpers, REST sensors, and template sensors for your chosen path. **It verifies everything works before it touches your config** — if it can't reach your Starlink router (3 retries with backoff), it surfaces a plain-English error and writes nothing.

### 4. Tiles appear

Within ~30 seconds, the `rc_net_starlink_*` contract tiles show up on your dashboard:

- **Reachability** — is your Starlink online right now?
- **Signal %** — what's the signal strength? (Gen-2/Gen-3 only; Gen-1 shows `unknown`)
- **Sleep state** — `awake | asleep | waking` based on your plug state (Path B) or OpenWrt WAN state (Path C). Always `awake` on Path A.
- **Wake for 30 min** — one-tap button to power-cycle the dish back on.
- **Quiet hours** — set when Starlink is allowed to sleep.

### 5. Done

OpenClaw now answers "is Starlink on?", "what's the signal %?", and "wake Starlink for 30 minutes" automatically. The sleep / wake / mode-aware automations are wired up; remote access keeps working even when the rest of your internet goes down.

## What you need

- **Starlink Gen-2 or Gen-3 terminal** (Gen-1 works for reachability + Path B/C, but the signal tile is grayed out).
- **A controllable smart plug** (Path B only) — TP-Link Kasa / Shelly / Sonoff / Zigbee / Modbus / etc.
- **An OpenWrt VM on the VP2430** (Path C only) — see `connections/openwrt-controls`.

## Install

- Open **Settings -> Devices & Services -> RoamCore -> Configure -> Starlink**.
- Pick your setup path.
- Answer the 2-3 questions the wizard asks.
- Hit Submit.
- The tiles appear on the dashboard within ~30 seconds.

## What it shows on your dashboard

- A Starlink tile that updates automatically (reachability + signal + sleep state + wake button + quiet hours).

## Common questions

**Q: Which path should I pick?**
A: If this is your first time setting up Starlink in a van and you don't already own a separate router or a Proxmox box — pick **Path A (Starlink Mini as my only router)**. It's the simplest, fastest, and has the fewest things to plug in.

**Q: Can I switch paths later?**
A: Yes. Re-run the wizard step anytime. RoamCore re-detects, re-confirms, and writes the right helpers for the new path (no duplicate entities).

**Q: What if the wizard says "We can't reach your Starlink router"?**
A: The wizard retried 3 times with backoff. Make sure the ethernet adapter is plugged into the dish, the dish is powered on (solid white status light), and your computer can reach `192.168.100.1` on the Starlink LAN. On Gen-1 (round "Dishy") there's no local API — Path A still works for reachability, but the signal tile shows `unknown`.

**Q: Does RoamCore need my Starlink account credentials?**
A: No. RoamCore talks to Starlink's local HTTP API at `192.168.100.1:80` (LAN only, no cloud, no account). Your credentials never leave your computer.

**Q: Does the wizard break anything if I cancel mid-setup?**
A: No. The wizard only writes helpers + REST sensors AFTER it's verified everything works. If you cancel, nothing was written yet. If the verification fails (unreachable router, bad plug entity, bad OpenWrt token), the wizard surfaces a plain-English error and writes nothing.

## See also

- `connections/starlink/docs/recipe.md` — the full howto (smart-plug wiring, signal-stats wiring, automations, troubleshooting, privacy).
- `connections/openwrt-controls` — the upstream OpenWrt API integration Path C depends on.