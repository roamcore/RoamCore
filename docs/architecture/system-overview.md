# VanCore system overview

Date: 2026-02-02

VanCore runs as a small homelab stack with Proxmox as the infrastructure host, a Home Assistant VM for automation/UI, and (planned) additional services (OpenWrt, VanCore LXC, etc.).

## Components (current)

### Proxmox host (VP2430)
- Role: Hypervisor for VanCore VMs/LXCs
- Hostname: `pve`
- Management IP: `192.168.1.10`
- Proxmox version: `pve-manager 9.1.4` (kernel `6.17.4-2-pve`)

VM inventory (from `qm list`):
- VM **100**: `openwrt` (currently stopped)
- VM **101**: `homeassistant` (running)

### Home Assistant VM
- VMID: **101**
- Name: `homeassistant`
- IP: `192.168.1.67`
- UI: `http://192.168.1.67:8123`
- OS inside VM: `Alpine Linux v3.23.3` (HAOS kernel `6.12.63-haos`)
- Config path: `/config` (symlink to `/homeassistant`)

### OpenWrt VM
- VMID: **100**
- Name: `openwrt`
- Status: stopped (as of 2026-02-02)
- Purpose: network edge/router/firewall (planned to become the authoritative network controller for VanCore)

### Clawdbot host
- Hostname: `clawdbot-bernard`
- Role: automation agent + documentation + GitHub integration
- Chrome (automation browser): `Google Chrome 144.0.7559.109`

- IP: `192.168.1.191`


## Data flows

- GitHub is the **source of truth** for docs/config/scripts.
- Proxmox generates VM backups (vzdump) which are synced to Google Drive.
- Home Assistant is operated via UI + API token + SSH where appropriate.

## Next planned components

- `services/vancore-lxc/` — a dedicated LXC for custom VanCore services.
- `infra/networking/openwrt/` — OpenWrt configuration exports + runbooks.

