#!/usr/bin/env bash
set -euo pipefail

# RoamCore HA-only installer
#
# This installer is intended to be run on a machine that has direct filesystem
# access to your Home Assistant config directory (usually /config).
#
# Usage (typical inside HAOS via the SSH & Web Terminal add-on):
#   curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/scripts/install/ha/install.sh | bash
#
# Overrides:
#   TARGET_CONFIG_DIR=/path/to/config bash install.sh
#   ROAMCORE_OVERWRITE=0 bash install.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

TARGET_CONFIG_DIR="${TARGET_CONFIG_DIR:-/config}"
ROAMCORE_OVERWRITE="${ROAMCORE_OVERWRITE:-1}"

fail() { echo "ERROR: $*" >&2; exit 1; }
info() { echo "[roamcore] $*"; }

[ -d "$ROOT_DIR/homeassistant/packages" ] || fail "missing $ROOT_DIR/homeassistant/packages"
[ -d "$ROOT_DIR/homeassistant/www" ] || fail "missing $ROOT_DIR/homeassistant/www"
[ -f "$ROOT_DIR/homeassistant/lovelace/roamcore-dashboard.yaml" ] || fail "missing $ROOT_DIR/homeassistant/lovelace/roamcore-dashboard.yaml"

[ -d "$TARGET_CONFIG_DIR" ] || fail "TARGET_CONFIG_DIR does not exist: $TARGET_CONFIG_DIR"

PKG_DST="$TARGET_CONFIG_DIR/packages"
WWW_DST="$TARGET_CONFIG_DIR/www"
LOVE_DST="$TARGET_CONFIG_DIR/lovelace"

mkdir -p "$PKG_DST" "$WWW_DST" "$LOVE_DST"

copy_file() {
  local src="$1" dst="$2"
  if [ -e "$dst" ] && [ "$ROAMCORE_OVERWRITE" != "1" ]; then
    info "skip existing (ROAMCORE_OVERWRITE=0): $dst"
    return 0
  fi
  mkdir -p "$(dirname "$dst")"
  cp -f "$src" "$dst"
}

copy_dir() {
  local src="$1" dst="$2"
  if [ -e "$dst" ] && [ "$ROAMCORE_OVERWRITE" != "1" ]; then
    info "skip existing dir (ROAMCORE_OVERWRITE=0): $dst"
    return 0
  fi
  rm -rf "$dst"
  mkdir -p "$(dirname "$dst")"
  cp -a "$src" "$dst"
}

info "Installing RoamCore HA packages → $PKG_DST"
shopt -s nullglob
for f in "$ROOT_DIR"/homeassistant/packages/roamcore_*.yaml; do
  copy_file "$f" "$PKG_DST/$(basename "$f")"
done

info "Installing RoamCore web assets → $WWW_DST/roamcore"
copy_dir "$ROOT_DIR/homeassistant/www/roamcore" "$WWW_DST/roamcore"

info "Installing RoamCore dashboard YAML → $LOVE_DST/roamcore-dashboard.yaml"
copy_file "$ROOT_DIR/homeassistant/lovelace/roamcore-dashboard.yaml" "$LOVE_DST/roamcore-dashboard.yaml"

cat <<EOF

RoamCore HA-only install complete.

Next steps (Home Assistant):
1) Settings → System → Restart (or restart Home Assistant Core).
2) Settings → Dashboards → Add Dashboard → "From YAML" (or "From file"):
   - file: /config/lovelace/roamcore-dashboard.yaml
3) Verify entities exist (Developer Tools → States):
   - sensor.rc_power_battery_soc

Notes:
- Packages were installed into: $PKG_DST
- Web assets installed into: $WWW_DST/roamcore (served as /local/roamcore/..)

Uninstall:
  curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/scripts/install/ha/uninstall.sh | bash
EOF

