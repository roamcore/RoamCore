#!/usr/bin/env bash
set -euo pipefail

# Default source: Proxmox vzdump directory
SRC_DIR="${SRC_DIR:-/var/lib/vz/dump}"

# Default destination: Google Drive remote + folder
DST="${DST:-gdrive:VanCore-Backups/proxmox-vzdump}"

LOG_DIR="${LOG_DIR:-/var/log}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/vancore-rclone-sync.log}"

mkdir -p "$LOG_DIR"

echo "[$(date -Is)] Starting rclone sync: $SRC_DIR -> $DST" | tee -a "$LOG_FILE"

rclone sync "$SRC_DIR" "$DST" \
  --create-empty-src-dirs \
  --fast-list \
  --transfers 4 \
  --checkers 8 \
  --log-level INFO \
  --log-file "$LOG_FILE"

echo "[$(date -Is)] Completed rclone sync" | tee -a "$LOG_FILE"
