#!/bin/sh
# RoamCore OpenWrt networking MVP firewall (iptables-legacy)
#
# Why this exists:
# - On some OpenWrt x86/64 images (observed 24.10.0 and 24.10.4 in VP2430 VM),
#   fw4 fails to load due to missing kernel support for nftables filter hooks:
#     "Chain of type \"filter\" is not supported"
# - This script provides a minimal, carrier-agnostic NAT + forwarding setup so
#   mwan3, the RoamCore API, and HA polling can function while we investigate a
#   proper fw4/nft fix.
#
# IMPORTANT:
# - This is an MVP workaround, not a security-hardened policy.
# - It assumes interface roles:
#     LAN  = br-lan
#     USER = eth2
#     UPLINK/WAN = eth3

# Optional:
# - If RC_API_PORT is set, also allow inbound TCP to that port on LAN/USER.
#   (This is helpful when fw4 is broken and HA needs to reach the API.)

set -eu

WAN_IF="${RC_WAN_IF:-eth3}"
LAN_IF="${RC_LAN_IF:-br-lan}"
USER_IF="${RC_USER_IF:-eth2}"

API_PORT="${RC_API_PORT:-}"

# Best-effort cleanup (ignore failures)

delete_all() {
  # Delete a rule repeatedly until it no longer exists.
  # Usage: delete_all <table_or_empty> <rule...>
  tbl="$1"; shift
  while true; do
    if [ -n "$tbl" ]; then
      iptables -t "$tbl" -D "$@" 2>/dev/null || break
    else
      iptables -D "$@" 2>/dev/null || break
    fi
  done
}

delete_all nat POSTROUTING -o "$WAN_IF" -j MASQUERADE
delete_all "" FORWARD -i "$LAN_IF" -o "$WAN_IF" -j ACCEPT
delete_all "" FORWARD -i "$USER_IF" -o "$WAN_IF" -j ACCEPT
delete_all "" FORWARD -i "$WAN_IF" -o "$LAN_IF" -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
delete_all "" FORWARD -i "$WAN_IF" -o "$USER_IF" -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT

# Optional allow rules cleanup
if [ -n "${API_PORT}" ]; then
  delete_all "" INPUT -i "$LAN_IF" -p tcp --dport "$API_PORT" -j ACCEPT
  delete_all "" INPUT -i "$USER_IF" -p tcp --dport "$API_PORT" -j ACCEPT
  # Also remove any older generic allow rules without interface match.
  delete_all "" INPUT -p tcp --dport "$API_PORT" -j ACCEPT
  delete_all "" INPUT -p tcp -m tcp --dport "$API_PORT" -j ACCEPT
fi

# NAT (idempotent)
iptables -t nat -C POSTROUTING -o "$WAN_IF" -j MASQUERADE 2>/dev/null || \
  iptables -t nat -A POSTROUTING -o "$WAN_IF" -j MASQUERADE

# Forwarding (idempotent)
iptables -C FORWARD -i "$LAN_IF" -o "$WAN_IF" -j ACCEPT 2>/dev/null || \
  iptables -A FORWARD -i "$LAN_IF" -o "$WAN_IF" -j ACCEPT
iptables -C FORWARD -i "$USER_IF" -o "$WAN_IF" -j ACCEPT 2>/dev/null || \
  iptables -A FORWARD -i "$USER_IF" -o "$WAN_IF" -j ACCEPT
iptables -C FORWARD -i "$WAN_IF" -o "$LAN_IF" -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || \
  iptables -A FORWARD -i "$WAN_IF" -o "$LAN_IF" -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
iptables -C FORWARD -i "$WAN_IF" -o "$USER_IF" -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || \
  iptables -A FORWARD -i "$WAN_IF" -o "$USER_IF" -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT

# Optional allow rules
if [ -n "${API_PORT}" ]; then
  iptables -C INPUT -i "$LAN_IF" -p tcp -m tcp --dport "$API_PORT" -j ACCEPT 2>/dev/null || \
    iptables -A INPUT -i "$LAN_IF" -p tcp --dport "$API_PORT" -j ACCEPT
  iptables -C INPUT -i "$USER_IF" -p tcp -m tcp --dport "$API_PORT" -j ACCEPT 2>/dev/null || \
    iptables -A INPUT -i "$USER_IF" -p tcp --dport "$API_PORT" -j ACCEPT
fi

echo "[roamcore-fw] applied iptables MVP NAT+forwarding: $LAN_IF,$USER_IF -> $WAN_IF"
