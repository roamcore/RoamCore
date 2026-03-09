#!/bin/sh
set -eu

RC_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

mkdir -p /opt/roamcore
cp -f "$RC_DIR/api.py" /opt/roamcore/api.py
chmod +x /opt/roamcore/api.py

cp -f "$RC_DIR/roamcore-api.init" /etc/init.d/roamcore-api
chmod +x /etc/init.d/roamcore-api

/etc/init.d/roamcore-api enable || true
/etc/init.d/roamcore-api restart || /etc/init.d/roamcore-api start

echo "installed"

