# Proxmox layout

Date: 2026-02-02

## Host

- Hostname: `pve`
- IP: `192.168.1.10`
- Version: Proxmox VE 9.1 (pve-manager 9.1.4)

## VMs

- **100** `openwrt` (stopped)
- **101** `homeassistant` (running)

## Networking (interfaces/bridges)

Observed bridges:
- `vmbr0` — LAN bridge, static `192.168.1.10/24`, gateway `192.168.1.1`, attached to `nic4`
- `vmbrWAN` — WAN bridge, attached to `nic0`
- `vmbrUSER` — internal/user bridge, attached to `nic1 nic3`

> Detailed VLAN design and OpenWrt responsibilities should live in `docs/architecture/networking.md`.

