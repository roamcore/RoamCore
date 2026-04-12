# OpenWrt router controls (WAN status + sensors)

**Support tier:** A (RoamCore native)

## What this is
RoamCore includes an OpenWrt API integration path to surface WAN/internet state into HA and enable safe control flows.

## Why it’s useful in a van
- Know which internet source is active
- Quickly spot “no internet” vs “Wi‑Fi connected but captive portal”

## Extra hardware required
- An OpenWrt router (or OpenWrt VM)

## Install / best next step
- HA package: `homeassistant/packages/roamcore_openwrt_api.yaml`
- Sensors: `homeassistant/packages/roamcore_net.yaml`

## Links
- OpenWrt: https://openwrt.org/
