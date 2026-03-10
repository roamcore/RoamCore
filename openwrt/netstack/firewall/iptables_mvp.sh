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

set -eu

WAN_IF="${RC_WAN_IF:-eth3}"
LAN_IF="${RC_LAN_IF:-br-lan}"
USER_IF="${RC_USER_IF:-eth2}"

# Best-effort cleanup (ignore failures)
iptables -t nat -D POSTROUTING -o "$WAN_IF" -j MASQUERADE 2>/dev/null || true
iptables -D FORWARD -i "$LAN_IF" -o "$WAN_IF" -j ACCEPT 2>/dev/null || true
iptables -D FORWARD -i "$USER_IF" -o "$WAN_IF" -j ACCEPT 2>/dev/null || true
iptables -D FORWARD -i "$WAN_IF" -o "$LAN_IF" -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true
iptables -D FORWARD -i "$WAN_IF" -o "$USER_IF" -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true

# NAT
iptables -t nat -A POSTROUTING -o "$WAN_IF" -j MASQUERADE

# Forwarding
iptables -A FORWARD -i "$LAN_IF" -o "$WAN_IF" -j ACCEPT
iptables -A FORWARD -i "$USER_IF" -o "$WAN_IF" -j ACCEPT
iptables -A FORWARD -i "$WAN_IF" -o "$LAN_IF" -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i "$WAN_IF" -o "$USER_IF" -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT

echo "[roamcore-fw] applied iptables MVP NAT+forwarding: $LAN_IF,$USER_IF -> $WAN_IF"

