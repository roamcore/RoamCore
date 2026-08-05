# OpenWrt router controls (WAN status + sensors)

## What it does
RoamCore includes an OpenWrt API integration path to surface WAN/internet state into HA and enable safe control flows.

## Why it’s useful in a van
- Know which internet source is active
- Quickly spot “no internet” vs “Wi‑Fi connected but captive portal”

## How to install
- An OpenWrt router (or OpenWrt VM)

- HA package: `homeassistant/packages/roamcore_openwrt_api.yaml`
- Sensors: `homeassistant/packages/roamcore_net.yaml`

## Useful links
- OpenWrt: https://openwrt.org/

## How it works

What RoamCore does behind the scenes.
