# Live OpenWrt VM (VP2430) — current state notes (2026-03-10)

This file is **notes** (not an apply script) capturing the live VM wiring and the temporary "WAN via vmbr0" mode.

## Proxmox wiring (VM100)
- net0 -> vmbrWAN (nic0)  [NO-CARRIER right now]
- net1 -> vmbrCORE
- net2 -> vmbrUSER
- net3 -> vmbr0 (nic4)    [has carrier]

## OpenWrt interface mapping (inside VM100)
- eth3 = vmbr0 (mgmt LAN uplink) → used as `network.wan` (static 192.168.1.250/24, gw 192.168.1.1)
- eth1 = vmbrCORE → used as `br-lan` port for `network.lan` (192.168.50.1/24)
- eth2 = vmbrUSER → used as `network.user` (192.168.60.1/24)
- eth0 = vmbrWAN → currently has no carrier; `network.wan6` points here but is effectively unused.

## mwan3
- `mwan3.wan.interface` is set to `wan` (canonical), tracking active.
- LTE interface (`wanb`) is disabled until SIM is present.

## fw4/nftables
- fw4 fails on this image/kernel with:
  - "Chain of type \"filter\" is not supported"
- We use an iptables-legacy MVP workaround for NAT+forwarding.
