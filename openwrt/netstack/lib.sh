#!/bin/sh
set -eu

RC_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

rc_load_vars() {
  # shellcheck disable=SC1091
  if [ -f "$RC_DIR/vars.env" ]; then
    . "$RC_DIR/vars.env"
  fi

  # Defaults (product spec)
  : "${RC_LAN_IP:=10.0.0.1}"
  : "${RC_LAN_NETMASK:=255.255.255.0}"
  : "${RC_LAN_DHCP_START:=100}"
  : "${RC_LAN_DHCP_LIMIT:=100}"
  : "${RC_LAN_DHCP_LEASETIME:=12h}"

  : "${RC_DOMAIN:=local}"
  : "${RC_DNS_ROAMCORE_NAME:=roamcore.local}"
  : "${RC_DNS_ROAMCORE_IP:=$RC_LAN_IP}"
  : "${RC_DNS_HA_NAME:=ha.roamcore.local}"
  : "${RC_DNS_HA_IP:=10.0.0.10}"

  : "${RC_HA_STATIC_MAC:=}"
  : "${RC_HA_STATIC_IP:=$RC_DNS_HA_IP}"

  : "${RC_WIFI_SSID:=RoamCore}"
  : "${RC_WIFI_KEY:=roamcore-default}"
  : "${RC_WIFI_COUNTRY:=GB}"
  : "${RC_WIFI_CHANNEL_2G:=6}"
  : "${RC_WIFI_CHANNEL_5G:=36}"

  : "${RC_DEV_LAN:=eth0}"
  : "${RC_DEV_WAN_STARLINK:=eth1}"
  : "${RC_DEV_WAN_LTE_WWAN:=wwan0}"
  : "${RC_DEV_LTE_QMI:=/dev/cdc-wdm0}"

  : "${RC_WAN_PREFERRED:=starlink}"
}

rc_log() {
  echo "[roamcore-netstack] $*" >&2
}

