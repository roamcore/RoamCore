#!/bin/sh
set -eu

. "$(dirname "$0")/lib.sh"
rc_load_vars

rc_log "Installing OpenWrt packages for RoamCore netstack"

opkg update

# Core networking
opkg install mwan3 luci-app-mwan3 vnstat2 || true

# LTE modem (QMI) + diagnostics
opkg install kmod-usb-net-qmi-wwan uqmi luci-proto-qmi \
  kmod-usb-serial-option kmod-usb-serial kmod-usb-net \
  chat comgt picocom curl wget || true

# Wi‑Fi (AX210)
opkg install kmod-iwlwifi iwlwifi-firmware-ax210 hostapd-openssl || true

# API layer
opkg install python3-light || true

rc_log "Done"

