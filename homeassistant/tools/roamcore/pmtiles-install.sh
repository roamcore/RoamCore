#!/bin/sh
set -eu

# RoamCore PMTiles provisioner (HAOS-safe)
#
# Downloads required PMTiles archives into:
#   /config/www/roamcore/pmtiles/
# so MapLibre styles referencing /local/roamcore/pmtiles/*.pmtiles work.
#
# Usage:
#   sh /config/tools/roamcore/pmtiles-install.sh
# Optional env vars:
#   CONFIG_DIR=/config
#   ROAMCORE_PMTILES_PACK=pmtiles-v1
#   ROAMCORE_PMTILES_MANIFEST=/config/tools/roamcore/pmtiles-v1.manifest (overrides)

CONFIG_DIR="${CONFIG_DIR:-/config}"
PACK="${ROAMCORE_PMTILES_PACK:-pmtiles-v1}"

WORK_BASE="${WORK_BASE:-}"
if [ -z "${WORK_BASE}" ]; then
  if [ -d /mnt/data ] && [ -w /mnt/data ]; then
    WORK_BASE="/mnt/data/tmp"
  else
    WORK_BASE="/tmp"
  fi
fi

WORK="$WORK_BASE/roamcore-pmtiles.$$"
mkdir -p "$WORK"
trap 'rm -rf "$WORK" 2>/dev/null || true' EXIT

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: missing required command: $1" >&2
    exit 1
  fi
}

fetch() {
  url="$1"
  out="$2"
  if command -v curl >/dev/null 2>&1; then
    # -C - resumes if supported
    curl -fL --retry 3 --retry-delay 2 -C - "$url" -o "$out"
  elif command -v wget >/dev/null 2>&1; then
    # -c resumes if supported (busybox wget supports it)
    wget -q -c -O "$out" "$url"
  else
    echo "ERROR: need curl or wget" >&2
    exit 1
  fi
}

sha256_file() {
  f="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$f" | awk '{print $1}'
    return 0
  fi
  if command -v openssl >/dev/null 2>&1; then
    # Output: SHA2-256(file)= <hash>
    openssl dgst -sha256 "$f" | awk '{print $NF}'
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    python3 - <<'PY' "$f"
import hashlib,sys
p=sys.argv[1]
h=hashlib.sha256()
with open(p,'rb') as fp:
  for b in iter(lambda: fp.read(1024*1024), b''):
    h.update(b)
print(h.hexdigest())
PY
    return 0
  fi
  return 1
}

MANIFEST_SRC="${ROAMCORE_PMTILES_MANIFEST:-}"
if [ -z "${MANIFEST_SRC}" ]; then
  # When installed via homeassistant/install.sh, we copy the manifest into tools.
  MANIFEST_SRC="$CONFIG_DIR/tools/roamcore/${PACK}.manifest"
fi

if [ ! -f "$MANIFEST_SRC" ]; then
  echo "ERROR: PMTiles manifest not found: $MANIFEST_SRC" >&2
  exit 1
fi

DEST_DIR="$CONFIG_DIR/www/roamcore/pmtiles"
mkdir -p "$DEST_DIR"

echo "== RoamCore PMTiles provision =="
echo "Pack: $PACK"
echo "Manifest: $MANIFEST_SRC"
echo "Dest: $DEST_DIR"

# Read manifest lines: filename|sha256|url
# Ignore comments/blank lines.
while IFS= read -r line; do
  case "$line" in
    ''|'#'*) continue ;;
  esac
  file=$(echo "$line" | awk -F'|' '{print $1}')
  want=$(echo "$line" | awk -F'|' '{print $2}')
  url=$(echo "$line" | awk -F'|' '{print $3}')

  [ -n "${file}" ] || continue
  [ -n "${url}" ] || { echo "ERROR: missing url for $file" >&2; exit 1; }

  dest="$DEST_DIR/$file"

  if [ -s "$dest" ] && got=$(sha256_file "$dest" 2>/dev/null || true) && [ -n "${got:-}" ] && [ "$got" = "$want" ]; then
    echo "OK (cached): $file"
    continue
  fi

  tmp="$WORK/$file.partial"
  echo "Downloading: $file"
  fetch "$url" "$tmp"

  if got=$(sha256_file "$tmp" 2>/dev/null || true) && [ -n "${got:-}" ]; then
    if [ "$got" != "$want" ]; then
      echo "ERROR: sha256 mismatch for $file" >&2
      echo "  want: $want" >&2
      echo "  got:  $got" >&2
      exit 1
    fi
  else
    echo "WARN: no sha256 tool available; skipping verification for $file" >&2
  fi

  mv -f "$tmp" "$dest"
  echo "OK: $file"

done <"$MANIFEST_SRC"

echo "Done."
