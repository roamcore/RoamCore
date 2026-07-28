#!/bin/sh
set -eu

# RoamCore one-line installer (HA-only beta).
#
# This is a thin wrapper that delegates to the Home Assistant installer at:
#   homeassistant/install.sh
#
# Usage (on a Home Assistant host with /bin/sh):
#   curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh | sh
#
# Optional env vars (forwarded):
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
  # https://github.com/owner/repo(.git) -> owner/repo
  echo "$ROAMCORE_REPO" \
    | sed -e 's#^https\?://github.com/##' -e 's#\.git$##' -e 's#/*$##'
}

SLUG="$(repo_slug)"

# ROAMCORE_REPO may point at a local checkout via file:// (used for testing
# and for offline/air-gapped installs). In that case, source the inner
# installer directly from the local path instead of going through GitHub.
case "$ROAMCORE_REPO" in
  file://*)
    LOCAL_REPO_PATH="${ROAMCORE_REPO#file://}"
    RAW_URL="file://${LOCAL_REPO_PATH}/homeassistant/install.sh"
    ;;
  *)
    RAW_URL="https://raw.githubusercontent.com/${SLUG}/${ROAMCORE_REF}/homeassistant/install.sh"
    ;;
esac

WORK_BASE="${WORK_BASE:-}"
if [ -z "${WORK_BASE}" ]; then
  if [ -d /mnt/data ] && [ -w /mnt/data ]; then
    WORK_BASE="/mnt/data/tmp"
  else
    WORK_BASE="/tmp"
  fi
fi

WORK="$WORK_BASE/roamcore-installer.$$"
mkdir -p "$WORK"
SCRIPT="$WORK/install-ha.sh"

cleanup() {
  rm -rf "$WORK" 2>/dev/null || true
}
trap cleanup EXIT

echo "== RoamCore installer (wrapper) =="
echo "Delegating to: $RAW_URL"

fetch "$RAW_URL" "$SCRIPT"

ROAMCORE_REPO="$ROAMCORE_REPO" \
ROAMCORE_REF="$ROAMCORE_REF" \
CONFIG_DIR="$CONFIG_DIR" \
sh "$SCRIPT"

