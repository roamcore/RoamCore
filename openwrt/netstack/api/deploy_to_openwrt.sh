#!/usr/bin/env bash
set -euo pipefail

# Deploy RoamCore OpenWrt Networking API to an OpenWrt host over SSH.
#
# This script is intentionally simple and conservative:
# - Uses legacy scp protocol (scp -O) because many OpenWrt images lack sftp-server.
# - Installs required packages via opkg.
# - Adds a persistent firewall allow rule via UCI.
# - Enables + restarts the procd service.
#
# Usage:
#   OPENWRT_HOST=192.168.1.250 OPENWRT_USER=root \
#     OPENWRT_SSH_KEY=~/.ssh/vancore_clawdbot \
#     ./deploy_to_openwrt.sh

OPENWRT_HOST="${OPENWRT_HOST:-}"
OPENWRT_USER="${OPENWRT_USER:-root}"
OPENWRT_SSH_KEY="${OPENWRT_SSH_KEY:-}"
OPENWRT_PORT="${OPENWRT_PORT:-22}"

API_PORT="${RC_API_PORT:-8080}"

# When true, we temporarily stop mwan3 during opkg operations. This helps on some
# multi-WAN setups where policy routing can break downloads.
STOP_MWAN3_DURING_OPKG="${STOP_MWAN3_DURING_OPKG:-1}"

# For MVP we bind on 0.0.0.0 (LAN firewall rule restricts reachability).
BIND_HOST="${RC_API_BIND_HOST:-0.0.0.0}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
API_PY_SRC="$SCRIPT_DIR/api.py"
INIT_SRC="$SCRIPT_DIR/roamcore-api.init"

if [[ -z "$OPENWRT_HOST" ]]; then
  echo "ERROR: OPENWRT_HOST is required (e.g. 192.168.1.250)" >&2
  exit 2
fi
if [[ -z "$OPENWRT_SSH_KEY" ]]; then
  echo "ERROR: OPENWRT_SSH_KEY is required (path to private key)" >&2
  exit 2
fi

SSH=(ssh -i "$OPENWRT_SSH_KEY" -o IdentitiesOnly=yes -p "$OPENWRT_PORT" "${OPENWRT_USER}@${OPENWRT_HOST}")
SCP=(scp -O -i "$OPENWRT_SSH_KEY" -o IdentitiesOnly=yes -P "$OPENWRT_PORT")

remote() {
  "${SSH[@]}" "$@"
}

step() {
  echo
  echo "==> $*"
}

step "Preflight"
[[ -f "$API_PY_SRC" ]] || { echo "Missing $API_PY_SRC" >&2; exit 2; }
[[ -f "$INIT_SRC" ]] || { echo "Missing $INIT_SRC" >&2; exit 2; }

remote 'uname -a; cat /etc/openwrt_release 2>/dev/null || true'

step "Ensure directories"
remote 'mkdir -p /opt/roamcore'

step "Best-effort: ensure DNS is usable during install"
# Some OpenWrt setups point resolv.conf at local dnsmasq (127.0.0.1) which may
# refuse external lookups depending on config. For installs, we point to public
# resolvers. (This is reversible; we do not persistently edit uci dhcp.)
remote 'printf "nameserver 1.1.1.1\nnameserver 8.8.8.8\n" > /tmp/resolv.conf.roamcore && ln -sf /tmp/resolv.conf.roamcore /etc/resolv.conf'

if [[ "$STOP_MWAN3_DURING_OPKG" == "1" ]]; then
  step "Temporarily stop mwan3 (best-effort)"
  remote '/etc/init.d/mwan3 stop 2>/dev/null || true'
fi

step "opkg update + install dependencies"
remote 'opkg update'

# Minimal deps for our stdlib-based Python API + helpers.
# NOTE: python3-light on OpenWrt may omit some stdlib modules; add python3-codecs/email/urllib/logging.
remote 'opkg install \
  python3-light python3-codecs python3-email python3-urllib python3-logging \
  curl wget-ssl ca-bundle \
  vnstat2 mwan3 iwinfo uqmi \
  || true'

if [[ "$STOP_MWAN3_DURING_OPKG" == "1" ]]; then
  step "Restart mwan3 (best-effort)"
  remote '/etc/init.d/mwan3 restart 2>/dev/null || true'
fi

step "Copy API payload"
"${SCP[@]}" "$API_PY_SRC" "${OPENWRT_USER}@${OPENWRT_HOST}:/opt/roamcore/api.py"
"${SCP[@]}" "$INIT_SRC" "${OPENWRT_USER}@${OPENWRT_HOST}:/etc/init.d/roamcore-api"

step "Write env file (if missing)"
remote 'test -f /etc/roamcore-api.env || cat > /etc/roamcore-api.env <<"EOF"
# Optional environment overrides for the RoamCore OpenWrt API.
#
# RC_API_TOKEN=change-me
# RC_API_HOST=0.0.0.0
# RC_API_PORT=8080
# RC_DEV_WAN_STARLINK=eth1
# RC_DEV_WAN_LTE_WWAN=wwan0
# RC_DEV_LTE_QMI=/dev/cdc-wdm0
# RC_DEV_LAN=eth0
EOF'

step "Permissions + enable service"
remote 'chmod +x /opt/roamcore/api.py /etc/init.d/roamcore-api; /etc/init.d/roamcore-api enable'

step "Persist firewall allow rule for API port (UCI)"
# Keep it open for LAN reachability; firewall rules should still restrict WAN.
remote "uci -q delete firewall.roamcore_api_allow || true; \
  uci set firewall.roamcore_api_allow=rule; \
  uci set firewall.roamcore_api_allow.name='Allow-RoamCore-API'; \
  uci set firewall.roamcore_api_allow.src='lan'; \
  uci set firewall.roamcore_api_allow.dest_port='${API_PORT}'; \
  uci set firewall.roamcore_api_allow.proto='tcp'; \
  uci set firewall.roamcore_api_allow.target='ACCEPT'; \
  uci commit firewall"

step "Apply firewall rule (restart if possible; fallback to iptables rule)"
# Some deployments may not have fw4/nftables fully supported; in that case we
# fall back to a persistent iptables rule in /etc/firewall.user.
remote "set -e; \
  /etc/init.d/firewall restart >/dev/null 2>&1 && echo 'firewall:restarted' && exit 0; \
  echo 'firewall:restart_failed_falling_back_to_iptables'; \
  RULE=\"iptables -I INPUT -p tcp --dport ${API_PORT} -j ACCEPT\"; \
  grep -qs \"--dport ${API_PORT}\" /etc/firewall.user 2>/dev/null || echo \"$RULE\" >> /etc/firewall.user; \
  sh -c \"$RULE\" 2>/dev/null || true"

step "Restart service"
remote "/etc/init.d/roamcore-api restart || /etc/init.d/roamcore-api start"

step "Verify local endpoints"
remote "wget -qO- -T 3 http://127.0.0.1:${API_PORT}/api/v1/status; echo"
remote "wget -qO- -T 3 http://127.0.0.1:${API_PORT}/api/v1/wan; echo"

step "Verify from deploy host"
if command -v curl >/dev/null 2>&1; then
  curl -s -m 3 "http://${OPENWRT_HOST}:${API_PORT}/api/v1/status" && echo
else
  echo "(curl not found locally; skipping external verify)"
fi

echo
echo "DONE: API should be reachable at http://${OPENWRT_HOST}:${API_PORT}/api/v1/status"
