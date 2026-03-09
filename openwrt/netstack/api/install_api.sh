#!/bin/sh
set -eu

RC_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

mkdir -p /opt/roamcore
cp -f "$RC_DIR/api.py" /opt/roamcore/api.py
chmod +x /opt/roamcore/api.py

# Provide a simple defaults file (not required). Admins can override via /etc/init.d env.
if [ ! -f /etc/roamcore-api.env ]; then
  cat > /etc/roamcore-api.env <<'EOF'
# Optional environment overrides for the RoamCore OpenWrt API.
# RC_API_TOKEN=change-me
# RC_DEV_WAN_STARLINK=eth1
# RC_DEV_WAN_LTE_WWAN=wwan0
# RC_DEV_LTE_QMI=/dev/cdc-wdm0
# RC_DEV_LAN=eth0
EOF
fi

cp -f "$RC_DIR/roamcore-api.init" /etc/init.d/roamcore-api
chmod +x /etc/init.d/roamcore-api

/etc/init.d/roamcore-api enable || true
/etc/init.d/roamcore-api restart || /etc/init.d/roamcore-api start

echo "installed"
