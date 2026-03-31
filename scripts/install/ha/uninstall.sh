#!/usr/bin/env bash
set -euo pipefail

# RoamCore HA-only uninstaller
# Removes files previously installed by scripts/install/ha/install.sh

TARGET_CONFIG_DIR="${TARGET_CONFIG_DIR:-/config}"

info() { echo "[roamcore] $*"; }
fail() { echo "ERROR: $*" >&2; exit 1; }

[ -d "$TARGET_CONFIG_DIR" ] || fail "TARGET_CONFIG_DIR does not exist: $TARGET_CONFIG_DIR"

PKG_DST="$TARGET_CONFIG_DIR/packages"
WWW_DST="$TARGET_CONFIG_DIR/www/roamcore"
LOVE_DASH="$TARGET_CONFIG_DIR/lovelace/roamcore-dashboard.yaml"

info "Removing RoamCore packages from $PKG_DST"
if [ -d "$PKG_DST" ]; then
  rm -f "$PKG_DST"/roamcore_*.yaml
fi

info "Removing RoamCore web assets from $WWW_DST"
rm -rf "$WWW_DST"

info "Removing RoamCore dashboard YAML from $LOVE_DASH"
rm -f "$LOVE_DASH"

cat <<EOF

RoamCore HA-only uninstall complete.

Next steps (Home Assistant):
- Restart Home Assistant Core.
- Remove the RoamCore dashboard from Settings → Dashboards (if you added it).

EOF

