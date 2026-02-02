#!/usr/bin/env bash
set -euo pipefail

remote="${1:-gdrive}"

echo "== rclone remotes =="
rclone listremotes

echo

echo "== list top-level for ${remote}: =="
rclone lsd "${remote}:
" 2>/dev/null || rclone lsd "${remote}:" 
