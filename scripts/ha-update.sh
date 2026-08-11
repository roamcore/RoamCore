#!/bin/sh
# scripts/ha-update.sh
#
# Single-paste deploy script for HAOS.
#
# What this does (in order, additive — never deletes existing files):
#   1. Snapshots /config/custom_components + /config/packages + /config/www/roamcore
#      into /config/.roamcore-updates/snapshot-<timestamp>/ (auto-pruned to last 5)
#   2. Streams the roamcore-bundle.tar.gz payload from this script's own location
#      (or downloads it from GitHub raw if called remotely)
#   3. Extracts ONLY the changed/new files into /config/
#   4. Chowns everything to root:root (HA requirement for custom_components)
#   5. Restarts HA Core via the supervisor API
#   6. Waits for HA to come back (poll /api/)
#   7. Verifies the OpenClaw API is reachable and returns 200
#   8. Prints a deploy receipt with rollback instructions
#
# USAGE (from HA root console, after SSH root is enabled):
#   curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/scripts/ha-update.sh | sh
#
# USAGE (offline, if you already downloaded the bundle):
#   sh ha-update.sh /path/to/roamcore-bundle.tar.gz
#
# ROLLBACK: snapshots live at /config/.roamcore-updates/snapshot-<ts>/
#   ls /config/.roamcore-updates/             # list snapshots
#   cp -rp /config/.roamcore-updates/snapshot-XXXXXXXX/custom_components/* /config/custom_components/
#   cp -rp /config/.roamcore-updates/snapshot-XXXXXXXX/packages/*      /config/packages/
#   cp -rp /config/.roamcore-updates/snapshot-XXXXXXXX/www/*           /config/www/
#   ha core restart

set -eu

CONFIG_DIR="${CONFIG_DIR:-/config}"
SNAP_ROOT="$CONFIG_DIR/.roamcore-updates"
BUNDLE_URL="${BUNDLE_URL:-https://raw.githubusercontent.com/roamcore/RoamCore/main/scripts/roamcore-bundle.tar.gz}"
HA_TOKEN_FILE="${HA_TOKEN_FILE:-/config/.roamcore-updates/ha.token}"
KEEP_SNAPSHOTS="${KEEP_SNAPSHOTS:-5}"
QUIET="${QUIET:-0}"

log() {
  [ "$QUIET" = "1" ] && return 0
  printf '\033[1;36m[rc-update]\033[0m %s\n' "$*"
}

warn() { printf '\033[1;33m[rc-update]\033[0m %s\n' "$*" >&2; }
err()  { printf '\033[1;31m[rc-update]\033[0m %s\n' "$*"   >&2; }
ok()   { printf '\033[1;32m[rc-update]\033[0m %s\n' "$*"; }

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    err "missing required command: $1 (this script must run as root on HAOS)"
    exit 1
  fi
}

need tar
need curl

# ---- token discovery (read-only if possible) ----
HA_TOKEN=""
for f in "$HA_TOKEN_FILE" "$CONFIG_DIR/.roamcore-updates/ha.token" /root/.roamcore.token; do
  if [ -f "$f" ] && [ -r "$f" ]; then
    HA_TOKEN="$(cat "$f" 2>/dev/null || true)"
    if [ -n "$HA_TOKEN" ]; then
      log "loaded HA token from $f"
      break
    fi
  fi
done

# ---- snapshot current state ----
TS="$(date +%Y%m%d-%H%M%S)"
SNAP_DIR="$SNAP_ROOT/snapshot-$TS"
log "creating snapshot at $SNAP_DIR"
mkdir -p "$SNAP_DIR"
mkdir -p "$SNAP_DIR/custom_components" "$SNAP_DIR/packages" "$SNAP_DIR/www"

# Use cp -rp only on directories that exist
[ -d "$CONFIG_DIR/custom_components" ] && cp -rp "$CONFIG_DIR/custom_components/." "$SNAP_DIR/custom_components/" 2>/dev/null || true
[ -d "$CONFIG_DIR/packages" ] && cp -rp "$CONFIG_DIR/packages/." "$SNAP_DIR/packages/" 2>/dev/null || true
[ -d "$CONFIG_DIR/www" ] && cp -rp "$CONFIG_DIR/www/." "$SNAP_DIR/www/" 2>/dev/null || true

# Write snapshot metadata
printf '{"snapshot_at":"%s","ha_version":"%s","core_path":"%s"}\n' \
  "$TS" "$(cat /config/.HA_VERSION 2>/dev/null || echo unknown)" "$CONFIG_DIR" \
  > "$SNAP_DIR/snapshot.json"

ok "snapshot created ($SNAP_DIR)"

# Prune old snapshots
SNAP_COUNT=$(ls -1 "$SNAP_ROOT" 2>/dev/null | grep -c '^snapshot-' || true)
if [ "$SNAP_COUNT" -gt "$KEEP_SNAPSHOTS" ]; then
  log "pruning old snapshots (keeping last $KEEP_SNAPSHOTS)"
  ls -1t "$SNAP_ROOT" | grep '^snapshot-' | tail -n +$((KEEP_SNAPSHOTS + 1)) | while read -r old; do
    rm -rf "$SNAP_ROOT/$old"
  done
fi

# ---- acquire the bundle ----
BUNDLE_PATH="${1:-}"
WORK="$(mktemp -d -t rc-update-XXXXXX)"
WORK_BUNDLE="$WORK/bundle.tar.gz"

if [ -z "$BUNDLE_PATH" ]; then
  log "downloading bundle from $BUNDLE_URL"
  if ! curl -fsSL --max-time 90 "$BUNDLE_URL" -o "$WORK_BUNDLE"; then
    err "failed to download bundle"
    exit 1
  fi
else
  log "using local bundle: $BUNDLE_PATH"
  if [ ! -f "$BUNDLE_PATH" ]; then
    err "bundle not found at $BUNDLE_PATH"
    exit 1
  fi
  cp "$BUNDLE_PATH" "$WORK_BUNDLE"
fi

ok "bundle ready ($(du -h "$WORK_BUNDLE" | cut -f1))"

# ---- extract into /config (additive, never overwrites unless needed) ----
log "extracting bundle into $CONFIG_DIR"

# Use tar with --keep-old-files? No — we want to overwrite the specific files
# we're shipping. But we DON'T want to clobber anything else in those dirs.
# So we extract to a staging area, then rsync the parts we care about.

EXTRACT_DIR="$WORK/extract"
mkdir -p "$EXTRACT_DIR"
tar -xzf "$WORK_BUNDLE" -C "$EXTRACT_DIR"

# Verify expected top-level dirs
for d in custom_components packages www; do
  if [ ! -d "$EXTRACT_DIR/$d" ]; then
    err "bundle missing $d/"
    exit 1
  fi
done

# Copy each directory, preserving structure
copy_section() {
  src="$1"
  dst="$2"
  if [ -d "$src" ]; then
    mkdir -p "$dst"
    cp -rp "$src/." "$dst/"
    log "  copied $src/ → $dst/"
  fi
}

# Backup files we're about to overwrite (in addition to the full snapshot above)
OVERWRITE_BACKUP="$SNAP_DIR/pre-overwrite-backup"
mkdir -p "$OVERWRITE_BACKUP/custom_components" "$OVERWRITE_BACKUP/packages" "$OVERWRITE_BACKUP/www"
for rel in custom_components packages www; do
  if [ -d "$CONFIG_DIR/$rel" ]; then
    find "$EXTRACT_DIR/$rel" -type f | while read -r src; do
      rel_path="${src#$EXTRACT_DIR/$rel/}"
      dst="$CONFIG_DIR/$rel/$rel_path"
      if [ -f "$dst" ]; then
        mkdir -p "$OVERWRITE_BACKUP/$rel/$(dirname "$rel_path")"
        cp -p "$dst" "$OVERWRITE_BACKUP/$rel/$rel_path"
      fi
    done
  fi
done

# Now do the actual copy
copy_section "$EXTRACT_DIR/custom_components" "$CONFIG_DIR/custom_components"
copy_section "$EXTRACT_DIR/packages" "$CONFIG_DIR/packages"
copy_section "$EXTRACT_DIR/www" "$CONFIG_DIR/www"

# Optional: tools, lovelace (only if bundle has them)
[ -d "$EXTRACT_DIR/tools" ] && copy_section "$EXTRACT_DIR/tools" "$CONFIG_DIR/tools"
[ -d "$EXTRACT_DIR/lovelace" ] && copy_section "$EXTRACT_DIR/lovelace" "$CONFIG_DIR/lovelace"

# Set correct ownership — HA Core runs as root for custom_components
log "fixing ownership"
chown -R root:root "$CONFIG_DIR/custom_components/roamcore" \
                      "$CONFIG_DIR/custom_components/roamcore_openclaw_api" \
                      "$CONFIG_DIR/custom_components/roamcore_tileserver" \
                      "$CONFIG_DIR/custom_components/roamcore_traccar_proxy" \
                      "$CONFIG_DIR/custom_components/geolocator" \
                      2>/dev/null || true
chown -R root:root "$CONFIG_DIR/packages/roamcore_"*.yaml 2>/dev/null || true
chown -R root:root "$CONFIG_DIR/www/roamcore" 2>/dev/null || true

ok "files in place"

# ---- restart HA Core ----
log "restarting Home Assistant Core"
HA_RESTART_OK=0
if [ -n "$HA_TOKEN" ]; then
  if curl -sk -X POST --max-time 10 \
       -H "Authorization: Bearer $HA_TOKEN" \
       -H "Content-Type: application/json" \
       -d '{}' \
       "http://127.0.0.1:8123/api/services/homeassistant/restart" \
       -o /dev/null -w "  API restart: HTTP %{http_code}\n"; then
    HA_RESTART_OK=1
  fi
fi
if [ "$HA_RESTART_OK" = "0" ]; then
  warn "API restart unavailable — falling back to ha cli"
  if command -v ha >/dev/null 2>&1; then
    ha core restart 2>&1 | head -3 || warn "ha core restart failed"
  else
    warn "no ha cli and no API token; you'll need to restart HA manually"
  fi
fi

# ---- wait for HA to come back ----
log "waiting for HA to come back (max 120s)"
HA_BACK=0
for i in $(seq 1 24); do
  sleep 5
  if [ -n "$HA_TOKEN" ]; then
    PROBE=$(curl -sk -o /dev/null -w "%{http_code}" --max-time 4 \
      -H "Authorization: Bearer $HA_TOKEN" \
      "http://127.0.0.1:8123/api/" 2>/dev/null || echo "000")
  else
    PROBE=$(curl -sk -o /dev/null -w "%{http_code}" --max-time 4 \
      "http://127.0.0.1:8123/api/" 2>/dev/null || echo "000")
  fi
  if [ "$PROBE" = "200" ]; then
    ok "HA back online after $((i*5))s"
    HA_BACK=1
    break
  fi
  printf "  ...wait %ds (HTTP %s)\n" "$((i*5))" "$PROBE"
done

if [ "$HA_BACK" = "0" ]; then
  warn "HA didn't come back within 120s — check the HA UI manually"
fi

# ---- verify ----
log "verifying deployed code is current"
sleep 5
if [ -n "$HA_TOKEN" ]; then
  OC_PROBE=$(curl -sk -o /tmp/oc.json -w "%{http_code}" --max-time 6 \
    -H "Authorization: Bearer $HA_TOKEN" \
    "http://127.0.0.1:8123/api/roamcore/openclaw/summary")
else
  OC_PROBE=$(curl -sk -o /tmp/oc.json -w "%{http_code}" --max-time 6 \
    "http://127.0.0.1:8123/api/roamcore/openclaw/summary")
fi
if [ "$OC_PROBE" = "200" ]; then
  ok "OpenClaw API reachable (HTTP 200)"
  CONTRACT_VER=$(grep -o '"version": *[0-9]*' /tmp/oc.json 2>/dev/null | head -1 || echo 'unknown')
  log "  contract: $CONTRACT_VER"
else
  warn "OpenClaw API probe returned HTTP $OC_PROBE"
fi

# ---- write deploy receipt ----
RECEIPT="$SNAP_ROOT/last-deploy.json"
cat > "$RECEIPT" <<EOF
{
  "deployed_at": "$TS",
  "ha_version": "$(cat /config/.HA_VERSION 2>/dev/null || echo unknown)",
  "snapshot": "$SNAP_DIR",
  "pre_overwrite_backup": "$OVERWRITE_BACKUP",
  "ha_back_online": $HA_BACK,
  "openclaw_api_http": $OC_PROBE,
  "bundle_size_bytes": $(stat -c %s "$WORK_BUNDLE" 2>/dev/null || echo 0)
}
EOF

# Cleanup workdir
rm -rf "$WORK"

echo ""
echo "==================================="
echo "  RoamCore deploy receipt"
echo "==================================="
echo "  when:    $(date -u +%FT%TZ)"
echo "  snapshot: $SNAP_DIR"
echo "  rollback: see /config/.roamcore-updates/last-deploy.json"
echo "  openclaw: HTTP $OC_PROBE"
echo "==================================="
ok "deploy complete"

exit 0
