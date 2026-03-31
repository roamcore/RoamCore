#!/bin/sh
set -eu

# RoamCore → Home Assistant (HAOS) one-line installer.
#
# Goal: copy RoamCore HA packages, custom components, and dashboard assets into
# Home Assistant's /config so it works on a stock HAOS system with the SSH add-on.
#
# One-line usage (on the HA host):
#   curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/homeassistant/install.sh | sh
#
# Optional env vars:
#   ROAMCORE_REF=main|<tag>|<sha>
#   ROAMCORE_REPO=https://github.com/roamcore/RoamCore
#   CONFIG_DIR=/config

ROAMCORE_REPO="${ROAMCORE_REPO:-https://github.com/roamcore/RoamCore}"
ROAMCORE_REF="${ROAMCORE_REF:-main}"
CONFIG_DIR="${CONFIG_DIR:-/config}"

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: missing required command: $1" >&2
    exit 1
  fi
}

need tar

fetch() {
  url="$1"
  out="$2"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$url" -o "$out"
  elif command -v wget >/dev/null 2>&1; then
    wget -qO "$out" "$url"
  else
    echo "ERROR: need curl or wget to download $url" >&2
    exit 1
  fi
}

ts() {
  # ISO-ish timestamp; busybox date may not support -Is.
  date "+%Y%m%d-%H%M%S"
}

repo_slug() {
  # https://github.com/owner/repo(.git) -> owner/repo
  echo "$ROAMCORE_REPO" \
    | sed -e 's#^https\?://github.com/##' -e 's#\.git$##' -e 's#/*$##'
}

SLUG="$(repo_slug)"
ARCHIVE_URL="https://github.com/${SLUG}/archive/${ROAMCORE_REF}.tar.gz"

# HAOS rootfs can be very small / full. Prefer a workdir on /mnt/data when present.
WORK_BASE="${WORK_BASE:-}"
if [ -z "${WORK_BASE}" ]; then
  if [ -d /mnt/data ] && [ -w /mnt/data ]; then
    WORK_BASE="/mnt/data/tmp"
  else
    WORK_BASE="/tmp"
  fi
fi

WORK="$WORK_BASE/roamcore-install.$$"
ARCHIVE="$WORK/src.tar.gz"
SRC_ROOT="$WORK/src"

STATE_DIR="$CONFIG_DIR/.roamcore"
MANIFEST="$STATE_DIR/manifest.txt"
INFO="$STATE_DIR/install-info.txt"

BACKUP_DIR="$STATE_DIR/backups/$(ts)"
BACKUP_INFO="$BACKUP_DIR/backup-info.txt"

mkdir -p "$WORK" "$SRC_ROOT" "$STATE_DIR" "$BACKUP_DIR"

cleanup() {
  rm -rf "$WORK" 2>/dev/null || true
}
trap cleanup EXIT

echo "== RoamCore HA install =="
echo "Repo: $ROAMCORE_REPO"
echo "Ref:  $ROAMCORE_REF"
echo "URL:  $ARCHIVE_URL"
echo "Dest: $CONFIG_DIR"

echo "Downloading…"
fetch "$ARCHIVE_URL" "$ARCHIVE"

echo "Extracting…"
tar -xzf "$ARCHIVE" -C "$SRC_ROOT"

TOP_DIR="$(find "$SRC_ROOT" -maxdepth 1 -mindepth 1 -type d | head -n 1)"
if [ -z "${TOP_DIR:-}" ] || [ ! -d "$TOP_DIR" ]; then
  echo "ERROR: failed to locate extracted archive directory" >&2
  exit 1
fi

HA_SRC="$TOP_DIR/homeassistant"
if [ ! -d "$HA_SRC" ]; then
  echo "ERROR: archive does not contain homeassistant/ directory" >&2
  exit 1
fi

write_manifest_line() {
  # Arg: absolute path under CONFIG_DIR.
  p="$1"
  # Store as /config-relative for portability.
  rel="${p#"$CONFIG_DIR"/}"
  echo "$rel" >>"$MANIFEST.tmp"
}

backup_if_exists() {
  dest="$1"
  if [ -e "$dest" ]; then
    rel="${dest#"$CONFIG_DIR"/}"
    mkdir -p "$BACKUP_DIR/$(dirname "$rel")"
    cp -f "$dest" "$BACKUP_DIR/$rel"
  fi
}

install_file() {
  src="$1"
  dest="$2"
  mkdir -p "$(dirname "$dest")"
  backup_if_exists "$dest"
  cp -f "$src" "$dest"
  write_manifest_line "$dest"
}

install_dir_children() {
  # Copy files from a source dir into a destination dir.
  # Args: src_dir dest_dir
  sdir="$1"
  ddir="$2"
  [ -d "$sdir" ] || return 0
  mkdir -p "$ddir"
  # Find regular files only (ignore .gitkeep).
  find "$sdir" -type f ! -name '.gitkeep' | while IFS= read -r f; do
    rel="${f#"$sdir"/}"
    install_file "$f" "$ddir/$rel"
  done
}

echo "Staging manifest…"
: >"$MANIFEST.tmp"

# 1) Packages → /config/packages/
install_dir_children "$HA_SRC/packages" "$CONFIG_DIR/packages"

# 2) Custom components → /config/custom_components/
install_dir_children "$HA_SRC/custom_components" "$CONFIG_DIR/custom_components"

# HACS note: if both legacy roamcore_openclaw_api and new roamcore are present,
# both will attempt to register the same endpoint. The RoamCore HACS integration
# supersedes the legacy component.

# 3) Dashboard JS → /config/www/roamcore/
install_dir_children "$HA_SRC/www" "$CONFIG_DIR/www"

# 4) Lovelace yaml → /config/lovelace/
install_dir_children "$HA_SRC/lovelace" "$CONFIG_DIR/lovelace"

# 5) Tools (exporters/helpers) → /config/tools/
# This is required for features like Trip Wrapped which execute local python.
install_dir_children "$HA_SRC/tools" "$CONFIG_DIR/tools"

# Write install metadata.
{
  echo "installed_at=$(date)"
  echo "repo=$ROAMCORE_REPO"
  echo "ref=$ROAMCORE_REF"
  echo "archive_url=$ARCHIVE_URL"
  echo "backup_dir=$BACKUP_DIR"
} >"$INFO.tmp"

# Atomically replace state files.
mv -f "$MANIFEST.tmp" "$MANIFEST"
mv -f "$INFO.tmp" "$INFO"

{
  echo "created_at=$(date)"
  echo "ref=$ROAMCORE_REF"
  echo "repo=$ROAMCORE_REPO"
  echo "note=Files that existed before install were copied here before overwrite."
} >"$BACKUP_INFO"

echo
echo "OK: RoamCore assets installed into $CONFIG_DIR"
echo "State:   $STATE_DIR"
echo "Manifest:$MANIFEST"
echo "Backup:  $BACKUP_DIR"
echo
echo "Next steps (in Home Assistant UI):"
echo "- Settings → System → Restart (or restart Core)"
echo "- Developer Tools → YAML → Reload Template Entities / Automations as needed"
echo "- Lovelace: add the dashboard yaml, and add /local/roamcore/*.js as resources if required"
