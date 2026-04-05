#!/bin/sh
set -eu

# RoamCore uninstaller (HA-only beta).
#
# Thin wrapper that delegates to:
#   homeassistant/uninstall.sh
#
# Usage (on a Home Assistant host with /bin/sh):
#   curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/uninstall.sh | sh
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

need sh

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

repo_slug() {
  echo "$ROAMCORE_REPO" \
    | sed -e 's#^https\?://github.com/##' -e 's#\.git$##' -e 's#/*$##'
}

SLUG="$(repo_slug)"
RAW_URL="https://raw.githubusercontent.com/${SLUG}/${ROAMCORE_REF}/homeassistant/uninstall.sh"

WORK_BASE="${WORK_BASE:-}"
if [ -z "${WORK_BASE}" ]; then
  if [ -d /mnt/data ] && [ -w /mnt/data ]; then
    WORK_BASE="/mnt/data/tmp"
  else
    WORK_BASE="/tmp"
  fi
fi

WORK="$WORK_BASE/roamcore-uninstaller.$$"
mkdir -p "$WORK"
SCRIPT="$WORK/uninstall-ha.sh"

cleanup() {
  rm -rf "$WORK" 2>/dev/null || true
}
trap cleanup EXIT

echo "== RoamCore uninstaller (wrapper) =="
echo "Delegating to: $RAW_URL"

fetch "$RAW_URL" "$SCRIPT"

ROAMCORE_REPO="$ROAMCORE_REPO" \
ROAMCORE_REF="$ROAMCORE_REF" \
CONFIG_DIR="$CONFIG_DIR" \
sh "$SCRIPT"

