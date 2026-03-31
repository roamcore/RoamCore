#!/bin/sh
set -eu

# RoamCore → Home Assistant (HAOS) uninstaller.
#
# Usage (on HA host):
#   curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/homeassistant/uninstall.sh | sh
#
# Optional env vars:
#   CONFIG_DIR=/config
#

CONFIG_DIR="${CONFIG_DIR:-/config}"
STATE_DIR="$CONFIG_DIR/.roamcore"
MANIFEST="$STATE_DIR/manifest.txt"
INFO="$STATE_DIR/install-info.txt"

echo "== RoamCore HA uninstall =="
echo "Dest: $CONFIG_DIR"

if [ ! -f "$MANIFEST" ]; then
  echo "Nothing to uninstall: manifest not found at $MANIFEST" >&2
  exit 0
fi

echo "Reading manifest…"

# Remove installed files.
missing=0
count=0

while IFS= read -r rel; do
  [ -n "$rel" ] || continue
  path="$CONFIG_DIR/$rel"
  if [ -e "$path" ]; then
    rm -f "$path"
    count=$((count + 1))
  else
    missing=1
  fi
done <"$MANIFEST"

# Best-effort cleanup of empty RoamCore dirs.
rmdir "$CONFIG_DIR/www/roamcore" 2>/dev/null || true

echo
echo "OK: removed $count files."
if [ "$missing" -eq 1 ]; then
  echo "Note: some files listed in the manifest were already missing." >&2
fi

echo
echo "State kept at: $STATE_DIR"
echo "- manifest: $MANIFEST"
echo "- info:     $INFO"
echo
echo "If you want to fully remove state/backups:"
echo "  rm -rf $STATE_DIR"

