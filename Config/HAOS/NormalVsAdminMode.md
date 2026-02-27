# RoamCore Access Model — Normal vs Advanced Mode (Local-First, HA-Backed)

> Purpose: lock down a **clean, app-like UI** for everyday users while preserving **full control** for power users—without cloud logins. This doc defines the architecture, protections, and exact touch points you’ll implement on the VP2430 (Proxmox + OpenWrt + HAOS).

---

## Goals

- **Make `van.local` feel like a separate app.** Users never see Home Assistant (HA) menus, device lists, logs, etc.  
- **Provide a deliberate “Advanced Mode.”** Power users reach full HA, Proxmox, OpenWrt, Frigate via `admin.van.local`.  
- **Local-first.** No external account system required; each backend keeps its own local login/2FA.  
- **Robust & repeatable.** Protections live in saved configs (proxy, HA, router). No dynamic toggles required.

---

## High-Level Architecture

- **Proxmox** (host) with VMs/CTs:  
  - **OpenWrt (VM):** routing, firewall.  
  - **HAOS (VM):** Home Assistant + **RoamCore add-on (Ingress)**.  
  - **Proxy LXC (Nginx/Caddy):** serves two hostnames:
    - `van.local` → **only** the add-on’s Ingress UI (Normal Mode).
    - `admin.van.local` → admin portal page with tiles/links to HA/Proxmox/OpenWrt/Frigate (Advanced Mode).

```
[User device] ──▶ van.local ──▶ Proxy LXC ──▶ HA: /api/hassio_ingress/<addon_slug>     (ONLY)
[User device] ──▶ admin.van.local ──▶ Proxy LXC ──▶ HA root / Proxmox / OpenWrt / Frigate (Admin)
```

---

## Three Layers of Protection (Plain English)

1) **Doorman (Reverse Proxy rules)**  
   - `van.local` **only** fetches the RoamCore add-on’s **Ingress path**.  
   - Any request for core HA pages (e.g., `/lovelace`, `/config`, `/api`, `/hassio`) is **denied (403)** on this hostname.  
   - **Outcome:** the browser never receives HA chrome (header/sidebar), so **no HA links exist** to click.

2) **HA Auto-trust (for van.local only)**  
   - HA trusts only the **proxy LXC IP** (Trusted Networks) and maps it to a **non-admin** user.  
   - **Outcome:** no HA login redirect from Ingress; the add-on loads cleanly as **your app**.

3) **(Optional) Router Firewall Guard**  
   - OpenWrt blocks direct access to HA:8123 and Proxmox:8006 from general LAN.  
   - Only the **proxy LXC**, **Tailscale**, and (optionally) the **owner device** can reach those ports.  
   - **Outcome:** even if someone guesses an IP/port, direct access is refused.

> With these in place, there is **no way** to reach HA by “clicking around” on `van.local`. Users would have to deliberately browse to the hidden admin door or guess IP/ports (which the firewall can also block).

---

## Hostnames & Roles

- **`van.local` (Normal Mode):**  
  App-like, shows **only** the RoamCore UI (your add-on’s Ingress). No links or chrome from HA.

- **`admin.van.local` (Advanced Mode):**  
  A branded landing page with **tiles** to:
  - **Home Assistant** (full UI)
  - **Proxmox VE**
  - **OpenWrt (LuCI)**
  - **Frigate** (full UI)
  - **Docs/Help** (“What can I do?”)  
  Users log into each tool with their **own local credentials** (enable 2FA where supported). Include a big **“Exit Admin Mode”** button back to `https://van.local`.

---

## Variables (replace in configs)

- `HA_IP` — IP of HAOS VM (e.g., `192.168.7.10`)  
- `PVE_IP` — IP of Proxmox host (e.g., `192.168.7.2`)  
- `OPENWRT_IP` — IP of OpenWrt VM (e.g., `192.168.7.1`)  
- `PROXY_IP` — IP of Proxy LXC (e.g., `192.168.7.20`)  
- `<ADDON_SLUG>` — Ingress slug of RoamCore add-on  
- `<FRIGATE_INGRESS>` — Ingress slug of Frigate add-on  
- `<USER_ID_NON_ADMIN>` — HA user_id of non-admin “RoamCore User”

---

## Reverse Proxy (Nginx) — Minimal, Safe Configs

> Serve both vhosts from the Proxy LXC (or OpenWrt). Add TLS (self-signed or local CA).

### `van.local` → Ingress-only (block all HA routes)

```nginx
server {
  listen 443 ssl;
  server_name van.local;

  # Only serve the add-on's Ingress app (your UI)
  location / {
    proxy_pass http://HA_IP:8123/api/hassio_ingress/<ADDON_SLUG>/;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto https;
  }

  # Hard block any HA routes on this host
  location ^~ /api/            { return 403; }
  location ^~ /hassio          { return 403; }
  location ^~ /lovelace        { return 403; }
  location ^~ /config          { return 403; }
  location ^~ /developer-tools { return 403; }
}
```

### `admin.van.local` → Tiles + full backends (logins required)

```nginx
server {
  listen 443 ssl;
  server_name admin.van.local;

  # Static admin portal (tiles page)
  location = / {
    root /opt/roamcore/admin;
    index index.html;
  }

  # Pass-through to full backends (real logins)
  location /ha/      { proxy_pass http://HA_IP:8123/; }
  location /proxmox/ { proxy_pass https://PVE_IP:8006/; }
  location /router/  { proxy_pass http://OPENWRT_IP/; }
  location /frigate/ { proxy_pass http://HA_IP:8123/api/hassio_ingress/<FRIGATE_INGRESS>/; }

  proxy_set_header Host $host;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto https;
}
```

---

## Home Assistant — Trust the Proxy (for `van.local` only)

```yaml
# configuration.yaml
http:
  use_x_forwarded_for: true
  trusted_proxies:
    - PROXY_IP        # Proxy LXC IP for van.local

homeassistant:
  auth_providers:
    - type: trusted_networks
      trusted_networks:
        - PROXY_IP    # Only the proxy can auto-login
      allow_bypass_login: true
      trusted_users:
        PROXY_IP: <USER_ID_NON_ADMIN>   # non-admin "RoamCore User"
    - type: homeassistant                # Normal username/password elsewhere (admin portal)
```

- Create a **non-admin** user (e.g., `RoamCore User`) for `van.local`.  
- Keep **admin** user(s) separate; enable **2FA**.

---

## OpenWrt — (Optional) Firewall Guardrails

> Ensures HA/Proxmox aren’t reachable directly from the LAN (only via the proxy, Tailscale, or your admin device).

```sh
# Allow HA from proxy LXC
uci add firewall rule
uci set firewall.@rule[-1].name='Allow HA from Proxy'
uci set firewall.@rule[-1].src='lan'
uci set firewall.@rule[-1].src_ip='PROXY_IP'
uci set firewall.@rule[-1].dest_ip='HA_IP'
uci set firewall.@rule[-1].dest_port='8123'
uci set firewall.@rule[-1].proto='tcp'
uci set firewall.@rule[-1].target='ACCEPT'

# Block HA from the rest of the LAN
uci add firewall rule
uci set firewall.@rule[-1].name='Block HA from LAN'
uci set firewall.@rule[-1].src='lan'
uci set firewall.@rule[-1].dest_ip='HA_IP'
uci set firewall.@rule[-1].dest_port='8123'
uci set firewall.@rule[-1].proto='tcp'
uci set firewall.@rule[-1].target='REJECT'

# (Repeat similarly for Proxmox:8006 as needed)
uci commit firewall && /etc/init.d/firewall reload
```

---

## Admin Portal (What Users See in Advanced Mode)

- **Landing page** (static HTML) with tiles:
  - Home Assistant (full UI)
  - Proxmox VE
  - OpenWrt (LuCI)
  - Frigate (full)
  - Docs / “What can I do?” / Backups & Restore
- **Warning modal:** “Advanced area—changes here can break your system.”  
- **Exit Admin Mode** button → returns to `https://van.local`.

> Host this static page at `/opt/roamcore/admin/index.html` on the Proxy LXC. No credentials stored by you—owners use each backend’s local login (with 2FA).

## Advanced Mode Dashboard Implementation (Heimdall)

For the initial implementation of **Advanced Mode**, RoamCore will use a self-hosted application dashboard called **Heimdall** as the primary “launchpad” for advanced tools and services.

### What Heimdall Provides

Heimdall is an open-source, MIT-licensed dashboard designed to present a grid of applications and links. It gives us, out of the box:

- A clean, tile-based UI listing all advanced tools (Home Assistant, Portainer, logs, diagnostics, etc.).
- Click-through access to each service running on the hub (or reachable remotely).
- Basic status indicators and descriptions for each tile.
- Self-hosted operation that fits our offline-first design.

Heimdall will run as a **Docker container on the VP2430** and be reachable both:

- **Locally** when the user is on the RoamCore Wi-Fi.
- **Remotely** via the same cloud proxy/tunnel used for the main RoamCore UI.

From the user’s perspective, “Advanced Mode” in the RoamCore app will simply open the Heimdall dashboard in a webview or new tab.

### RoamCore Customisation & Reskinning

Heimdall will be customised to appear as a native part of the RoamCore experience:

- **Branding**
  - RoamCore logo and colour palette applied to the Heimdall theme.
  - Custom background image consistent with the main RoamCore UI.
- **Preconfigured Tiles**
  - Home Assistant (advanced config/UI)
  - Portainer (container management, for internal/support use)
  - System logs and metrics
  - Network / tunnel diagnostics
  - Firmware / update status page
  - “RoamCore Docs”, “Advanced Mode Guide”, and “Support” tiles linking to documentation and tutorials.
- **Documentation & Help**
  - Dedicated tiles linking to:
    - User manual (normal + advanced mode)
    - Wiring diagrams / hardware docs
    - Troubleshooting guides
    - Example automations / recipes

Because Heimdall is open source and uses simple Blade/Laravel templates, we can further reskin or fork it later if needed (e.g. tighter integration with RoamCore APIs, custom info panels, or different layout), while keeping the MVP implementation fast and low-risk.

In summary, Heimdall gives us a production-ready advanced dashboard with minimal engineering effort, while still allowing full RoamCore branding and deep customisation over time.

---

## UX Guarantees (Why Users Cannot “Click Into HA”)

- **No HA chrome delivered:** `van.local` proxies **only** the add-on’s Ingress app; HA header/sidebar never load.  
- **Blocked routes:** Any HA core paths on `van.local` return **403**.  
- **No links added:** Your UI contains **no link** to HA.  
- **(Optional) LAN blocks:** Even if someone guesses HA’s IP/port, the router refuses connections (except from proxy/Tailscale/admin).

**Result:** There is **zero chance** to reach the HA dashboard by clicking around your app.

---

## Security & Ownership

- **Local-first:** No cloud account system required for MVP.  
- **Accounts remain per backend:**
  - HA: admin + non-admin (2FA for admin).  
  - Proxmox: `owner@pve` (2FA).  
  - OpenWrt: `root` (SSH keys preferred).  
- **No admin credentials embedded** in your UI.  
- **Backups:** Include proxy configs, HA configs, and OpenWrt UCI files in your weekly backup bundle to eMMC/external.

---

## Implementation Checklist

- [ ] Create **Proxy LXC** with two vhosts (`van.local`, `admin.van.local`).  
- [ ] Configure **HA Trusted Networks** for the proxy IP (non-admin user).  
- [ ] (Optional) Add **OpenWrt firewall** allow/deny rules for HA/Proxmox.  
- [ ] Package **RoamCore UI** as a HA add-on with **Ingress**.  
- [ ] Build a **static admin portal** (tiles page) for `admin.van.local`.  
- [ ] Enable **2FA** for admin accounts (HA, Proxmox).  
- [ ] Document **owner credentials** and recovery steps (local).

---

## Future Enhancements (Optional)

- **Local SSO** (Authelia) in front of `admin.van.local` for a single admin gate (still local-only).  
- **Per-device DNS responses**: don’t advertise `admin.van.local` to non-admin clients.  
- **Support Mode**: a button that temporarily whitelists a device/IP for HA access (auto-expires).

---

## TL;DR

- `van.local` → **only** your add-on UI via Ingress; **blocks** all HA paths; HA auto-trusts proxy → app feels standalone.  
- `admin.van.local` → deliberate admin door with tiles to HA/Proxmox/OpenWrt/Frigate (logins required).  
- Optional firewall rules can **physically block** direct admin access from the LAN.  
- No cloud accounts, no secret credential storage—**simple, local, reliable**.
