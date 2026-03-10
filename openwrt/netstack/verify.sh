#!/bin/sh
set -eu

. "$(dirname "$0")/lib.sh"
rc_load_vars

rc_log "Verifying OpenWrt netstack"

# API host: prefer explicit RC_API_HOST (or RC_OPENWRT_HOST) when verifying from
# a non-LAN context (e.g. temporary mgmt/WAN mode on vmbr0).
API_HOST="${RC_API_HOST:-${RC_OPENWRT_HOST:-${RC_LAN_IP}}}"
API_PORT="${RC_API_PORT:-8080}"

rc_log "Interfaces (ubus):"
ubus call network.interface.lan status | head -c 400 || true
echo

rc_log "Default route:"
ip route show default || true

rc_log "mwan3 status (if installed):"
if command -v mwan3 >/dev/null 2>&1; then
  mwan3 status || true
fi

rc_log "API status endpoint (if running):"
if command -v wget >/dev/null 2>&1; then
  wget -qO- "http://${API_HOST}:${API_PORT}/api/v1/status" || true
  echo
  wget -qO- "http://${API_HOST}:${API_PORT}/api/v1/wan" || true
  echo
  wget -qO- "http://${API_HOST}:${API_PORT}/api/v1/system" || true
  echo
  wget -qO- "http://${API_HOST}:${API_PORT}/api/v1/wifi" || true
  echo
  wget -qO- "http://${API_HOST}:${API_PORT}/api/v1/lte" || true
  echo
fi

rc_log "Done"
