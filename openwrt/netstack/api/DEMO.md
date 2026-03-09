# RoamCore OpenWrt API — Demo / Quickstart

This is the fastest path to see the OpenWrt Networking API working end-to-end.

## 0) Prereqs
- An OpenWrt host reachable over SSH from your dev machine.
- You have an SSH key allowed for `root` on the OpenWrt box.

## 1) Deploy the API to OpenWrt
From the RoamCore repo root:

```bash
cd openwrt/netstack/api
OPENWRT_HOST=192.168.1.250 \
OPENWRT_USER=root \
OPENWRT_SSH_KEY=~/.ssh/vancore_clawdbot \
./deploy_to_openwrt.sh
```

Notes:
- Uses `scp -O` (legacy scp protocol), because many OpenWrt images do **not** ship `sftp-server`.
- Attempts to add a firewall allow rule via UCI; if firewall restart fails on a given build, it falls back to a persistent `/etc/firewall.user` iptables rule.

## 2) Verify endpoints
From your dev machine:

```bash
curl -s http://192.168.1.250:8080/api/v1/status
curl -s http://192.168.1.250:8080/api/v1/system
curl -s http://192.168.1.250:8080/api/v1/wan
curl -s http://192.168.1.250:8080/api/v1/wifi
curl -s http://192.168.1.250:8080/api/v1/data_usage
```

## 3) Home Assistant wiring (package)
File:
- `homeassistant/packages/roamcore_openwrt_api.yaml`

What you should see in HA after loading packages + restarting:
- `sensor.rc_openwrt_internet`
- `sensor.rc_openwrt_active_wan`
- `sensor.rc_openwrt_preferred_wan`
- `sensor.rc_openwrt_wifi_clients`
- usage sensors like `sensor.rc_openwrt_starlink_today_rx_mb`

The `rc_net_*` contract sensors then prefer these OpenWrt sensors (with mock fallback).

## 4) Controls
HA `rest_command` entries (from the same package) allow:
- set Wi-Fi SSID/key
- set WAN preference (starlink vs lte)
- restart network stack
