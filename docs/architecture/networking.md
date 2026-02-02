# Networking architecture

Date: 2026-02-02

## Current state (known)

- Proxmox host `pve` is reachable on LAN at `192.168.1.10/24` via `vmbr0`.
- Default gateway for Proxmox is `192.168.1.1`.
- There is an OpenWrt VM (VMID 100) intended to become the network edge/router.

## Target state (intent)

- OpenWrt provides:
  - WAN uplink
  - firewall rules
  - DHCP/DNS
  - VLAN segmentation (as needed)
- Proxmox bridges map cleanly to OpenWrt interfaces (WAN/LAN/USER/management as appropriate).

## Work items

- Document VLAN plan and port mapping.
- Decide whether OpenWrt is the sole router or if an upstream router remains.
- Add `infra/networking/openwrt/` exports + restore steps.

