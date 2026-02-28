# RoamCore Software Stack Overview — VP2430 (Protectli)

**Status:** Overview (implementation-aligned)  
**Owner:** RoamCore Platform  
**Last updated:** 2025-11-13

This document explains the **software layers** that make up the RoamCore platform on the **Protectli VP2430**. It focuses on responsibilities, boundaries, and how layers interact for reliability, security, and remote support. Use this as the top-level map for engineers and partners.

---

## 1) Stack at a Glance (Layers & Roles)

```
Hardware (VP2430: N100/N150, 4×2.5GbE, M.2 Wi‑Fi + LTE/5G)
│
├─ Proxmox VE (hypervisor)  ← always-on
│   ├─ Tailscale (host)      ← admin plane (JIT SSH via Support Mode)
│   ├─ PCIe/IOMMU passthrough for WAN NIC to Router VM
│   └─ Watchdog/snapshots/backup targets
│
├─ Router VM (OPNsense/OpenWrt)  ← network control-plane
│   ├─ Multi-WAN: Starlink (WAN1) + Cellular (WAN2)
│   ├─ DHCP/DNS (Unbound), VLANs, mDNS reflector
│   ├─ WireGuard (end-user remote) + optional WG to VPS (break-glass)
│   └─ Modem management (QMI/MBIM) + health watchdog
│
├─ Home Assistant OS VM (HAOS)    ← user experience
│   ├─ Home Assistant Core + Add-ons (Mosquitto, go2rtc, Frigate, etc.)
│   ├─ Nabu Casa (default) or Cloudflare Tunnel for remote UI
│   └─ Backups (nightly) + “Support Mode” toggle UI
│
└─ RoamCore App CT (LXC, Debian 12) ← orchestration & glue
    ├─ RoamCore API (pairing, settings, health, storage estimator)
    ├─ Config templating (e.g., write frigate.yml, trigger reload)
    ├─ Support controller (calls host `support-mode on/off`)
    └─ Optional: cloudflared, rclone jobs, Prometheus exporter
```

---

## 2) Responsibilities & Interfaces (Who does what)

- **Proxmox (host)**: lifecycle of VMs/CTs, PCI passthrough, snapshots, backups, watchdogs, and **Tailscale (admin plane)**. Exposes **no user web ports**.  
- **Router VM**: sole owner of WAN/LAN, firewall, VLANs, DHCP/DNS, and tunnels for end-user remote access (WireGuard). Publishes telemetry (usage, latency, signal) via MQTT/REST to HA.  
- **HAOS VM**: canonical **user dashboard** and automations. Provides pairing/onboarding flow, Starlink↔Cell controls, Support Mode switch (consent), and integrations.  
- **RoamCore App CT**: light control-plane that talks to HA/Router/Host via APIs or SSH to coordinate tasks (template config, archive jobs, tunnel policy, support).

**APIs between layers**
- **App CT → HA**: HA WebSocket/REST (read/write helpers, render config, trigger reloads).  
- **App CT → Host**: SSH to run `support-mode on/off`; optional Proxmox API token for snapshots.  
- **App CT → Router**: OPNsense/OpenWrt API for WAN status, policy changes, counters.  
- **MQTT**: shared bus (Mosquitto add-on in HAOS) for telemetry and simple commands.

---

## 3) Remote Access Plan (Two Planes)

**Admin plane (for RoamCore support):**
- **Tailscale on the Proxmox host** (always connected), **Tailscale SSH disabled by default**.
- User enables **Support Mode** in HA → host runs `tailscale set --ssh=true` with auto-off timer (e.g., 24h).  
- Support connects with **root** to host via Tailscale SSH; uses SSH port-forwarding for Proxmox/HA/Router UIs.  
- Benefits: CGNAT-safe, host-level rescue path, explicit user consent, audit trail.

**User plane (for owners):**
- **Default:** **Nabu Casa** for remote HA URL, push, voice.  
- **Alt (white-label):** **Cloudflare Tunnel + Access** (SSO) from HA/App CT. Pairing flow grants the owner access to their subdomain.  
- Avoid inbound port-forwarding; rely on outbound tunnels only.

---

## 4) Networking & Identity (High Level)

- **WAN:** Starlink on Port 1 (Ethernet Adapter; Bypass Mode recommended). Cellular is failover/policy WAN2.  
- **LAN:** vmbr0 bridges Ports 2–4 to the Router VM and HAOS/App CT. Optional VLANs for Core/HA, Electrical, Water, Security, IoT.  
- **Discovery:** mDNS reflector lets HA discover devices across VLANs.  
- **Identity & Auth:**  
  - Admin: Tailscale ACLs (e.g., `tag:roamcore-hub` accessible only by `group:support`), MFA via SSO.  
  - Users: Nabu Casa or Cloudflare Access (SSO, 2FA).  
  - “Support Mode” provides JIT consent + banner and countdown in HA.

---

## 5) Storage & Paths

- **/mnt/video** → CCTV recordings (Frigate/go2rtc, copy-to-disk, no transcode).  
- **/mnt/backup** → HA snapshots, router exports, support bundles.  
- **NVMe**: high-endurance SSD with heatsink; smartd monitoring. Optional rclone job to archive old clips to B2/S3/Drive (off by default).

---

## 6) Reliability, Safety & Watchdogs

- **Proxmox watchdog** (iTCO) for host health; VM **scheduled snapshots** for quick rollback.  
- **Router WAN/modem watchdog** to bounce interfaces if health checks fail.  
- **HA health sensor**; “Support Bundle” button to zip logs/configs for tickets.  
- **Power semantics**: ignition-sense → graceful shutdown; low‑voltage cutoff prevents battery drain.

---

## 7) Provisioning & Pairing (First Boot)

1. First boot presents **Pair Van** (QR/claim code) in HA.  
2. Owner authenticates to RoamCore Cloud (or Nabu Casa) and claims the device.  
3. App CT finalizes remote URL (Nabu Casa or Cloudflare), sets device name, timezone, LTE APN.  
4. Optional: create WireGuard profile for the owner; show QR in HA.  
5. Show the **Support Mode** toggle and a short quick-start.

---

## 8) Minimal Specs (for planning)

- **Router VM**: 2 vCPU, 1–2 GB RAM, 8–16 GB disk.  
- **HAOS VM**: 2–4 vCPU, 4–8 GB RAM, 32–64 GB disk (configs/add-ons).  
- **App CT**: 2 vCPU, 2–4 GB RAM, 8–16 GB disk.  
- **CCTV storage**: 1 TB NVMe recommended for tiered retention (~≤300 GB/week @ 4 cams).  
- **CPU guidance**: N100/N150 fine for copy-to-disk + on-demand viewing; i3‑N305 SKU if adding heavy analytics/transcoding or more cameras.

---

## 9) Security Posture (Defaults)

- No public ports; all remote access via **outbound tunnels**.  
- **JIT admin access**: Tailscale SSH disabled by default; enabled only by user consent.  
- **Separation of planes**: Admin (Tailscale) vs User (Nabu Casa/Cloudflare).  
- **Principle of least privilege**: narrow ACLs, short-lived sessions, audit logs retained.  
- **Hardening**: host firewall accepts SSH only on `tailscale0`; strong passwords/keys; disable P2P/UPnP on cameras; IoT VLAN egress limited.

---

## 10) Operations (Day‑2)

- **Backups**: nightly HA snapshots to /mnt/backup (+ cloud), router config export, optional PBS/rsync for VMs.  
- **Updates**: Proxmox kernel window, Router/HA add-on cadence, App CT container rollouts (tagged releases).  
- **Monitoring**: Prometheus (light) + Grafana (optional) for temps, NVMe wear, WAN uptime, modem RSSI/RSRP/SINR.  
- **Support**: HA “Support Mode (24h)” toggle; ticket ID displayed; tailscale admin logs + host journal for audit.

---

## 11) Roadmap (Nice-to-haves)

- GNSS for time/geo automations.  
- App marketplace (apps run in CT/VM sandboxes).  
- Fleet dashboard (online/offline, update status).  
- Alternative admin path via WireGuard hub on VPS (already documented as break-glass).

---

## 12) Glossary (quick)

- **Admin plane**: secure path for RoamCore support (Tailscale on host).  
- **User plane**: owner’s remote access to HA (Nabu Casa/Cloudflare Access).  
- **Support Mode**: user-consented, time-limited enabling of Tailscale SSH on the host.  
- **Pairing**: associating a device with an owner account and provisioning remote URL/keys.

