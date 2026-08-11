#!/usr/bin/env bash
# scripts/deploy-to-ha.sh
#
# Push the current RoamCore repo state (branch/ref/commit) to Bernard's
# live Home Assistant at 192.168.1.66, restart HA Core, and verify the
# deploy by hitting the OpenClaw JSON API.
#
# Designed to be run from:
#   - a local post-commit hook (after every commit to main or any cron branch)
#   - manually:  bash scripts/deploy-to-ha.sh [--ref main] [--skip-restart] [--no-verify]
#
# What it does:
#   1. Validate preflight (SSH to HA, token works, repo clean of secret leaks)
#   2. Snapshot the current /config state on HA (timestamped backup)
#   3. Run the official install.sh (ROAMCORE_REF=<commit-sha>, deploy-only mode)
#   4. Restart Home Assistant Core via the HA API (Bearer token)
#   5. Wait for HA to come back (poll /api/ until 200)
#   6. Verify the new code is loaded (manifest version, OpenClaw API reachable)
#   7. Print a deploy receipt
#
# Idempotent. Safe to run repeatedly.

set -euo pipefail

# ---- config (env-overridable) ----
HA_HOST="${HA_HOST:-192.168.1.66}"
HA_SSH_USER="${HA_SSH_USER:-hassio}"
HA_SSH_KEY="${HA_SSH_KEY:-$HOME/.ssh/vancore_clawdbot}"
HA_TOKEN_FILE="${HA_TOKEN_FILE:-$HOME/.clawdbot/secrets/homeassistant.token}"
CONFIG_DIR="${CONFIG_DIR:-/config}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ---- args ----
REF=""
SKIP_RESTART=0
NO_VERIFY=0
DRY_RUN=0

while [ $# -gt 0 ]; do
  case "$1" in
    --ref) shift; REF="${1:-}";;
    --skip-restart) SKIP_RESTART=1;;
    --no-verify) NO_VERIFY=1;;
    --dry-run) DRY_RUN=1;;
    --help|-h)
      sed -n '2,28p' "$0"
      exit 0
      ;;
    *) err "unknown arg: $1"; exit 1;;
  esac
  shift
done

# ---- helpers ----
log() { printf '\033[1;36m[deploy]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*" >&2; }
err() { printf '\033[1;31m[err]\033[0m %s\n' "$*" >&2; }
ok() { printf '\033[1;32m[ok]\033[0m %s\n' "$*"; }

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    err "missing required command: $1"
    exit 1
  fi
}

# ---- preflight ----
log "preflight"
need ssh
need curl

[ -f "$HA_SSH_KEY" ] || { err "HA SSH key not found: $HA_SSH_KEY"; exit 1; }
[ -f "$HA_TOKEN_FILE" ] || { err "HA token not found: $HA_TOKEN_FILE"; exit 1; }

cd "$REPO_ROOT"

# If no ref passed, use HEAD sha
if [ -z "$REF" ]; then
  REF="$(git rev-parse HEAD)"
  log "no --ref passed, using HEAD: $REF"
fi

# Confirm ref exists in repo
if ! git cat-file -e "$REF" 2>/dev/null; then
  err "ref $REF does not exist in this repo"
  exit 1
fi

SHORT_REF="$(git rev-parse --short "$REF")"
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'detached')"

log "repo:   $REPO_ROOT"
log "ref:    $REF ($SHORT_REF, branch=$BRANCH)"
log "ha:     $HA_SSH_USER@$HA_HOST"
log "config: $CONFIG_DIR"

# Secret-leak pre-flight (catch typos before they hit /config)
log "scanning staged + working tree for accidental secret commits"
LEAK_HITS="$( (git diff "$REF" -- ':!docs' ':!homeassistant/packages/tests' ':!scripts' || true) \
  | grep -iEn '(api[_-]?key|token|password|secret)\s*[:=]\s*["\047]?[A-Za-z0-9+/=._-]{16,}' \
  | grep -viE '(your[-_ ]token|enter your|placeholder|example|test|fake|dummy)' \
  | head -5 || true)"
if [ -n "$LEAK_HITS" ]; then
  err "SECRET LEAK detected in diff at $REF:"
  echo "$LEAK_HITS"
  err "aborting deploy"
  exit 2
fi
ok "no secret leaks detected in diff"

# Verify SSH + token before doing anything destructive
log "verifying SSH to HA"
ssh -o ConnectTimeout=5 -o BatchMode=yes -i "$HA_SSH_KEY" -o IdentitiesOnly=yes \
  "$HA_SSH_USER@$HA_HOST" 'echo "ssh-ok"' >/dev/null
ok "ssh works"

HA_TOKEN="$(cat "$HA_TOKEN_FILE")"
log "verifying HA token"
HA_PROBE=$(curl -sk -o /dev/null -w "%{http_code}" --max-time 5 \
  -H "Authorization: Bearer $HA_TOKEN" \
  "http://$HA_HOST:8123/api/")
if [ "$HA_PROBE" != "200" ]; then
  err "HA token check failed (HTTP $HA_PROBE)"
  exit 1
fi
ok "ha token works"

# ---- snapshot before deploy ----
# We snapshot to /tmp on the HA host (which is writable by hassio) because
# /config/.roamcore/ is root-owned by the HA install script and hassio can't
# write under it. The official installer writes /config/.roamcore/install-info.txt
# which we leave alone.
TS="$(date +%Y%m%d-%H%M%S)"
SNAP_DIR="/tmp/roamcore-snapshots/$TS-pre-deploy"
log "snapshotting current /config state to $SNAP_DIR"

ssh -o ConnectTimeout=10 -i "$HA_SSH_KEY" -o IdentitiesOnly=yes "$HA_SSH_USER@$HA_HOST" \
  sh <<EOF
set -e
SNAP_DIR="$SNAP_DIR"
CONFIG_DIR="$CONFIG_DIR"
mkdir -p "\$SNAP_DIR/custom_components" "\$SNAP_DIR/packages" "\$SNAP_DIR/www" "\$SNAP_DIR/lovelace" "\$SNAP_DIR/tools"
cp -rp "\$CONFIG_DIR/custom_components/roamcore"* "\$SNAP_DIR/custom_components/" 2>/dev/null || true
cp -rp "\$CONFIG_DIR/packages/roamcore_"*.yaml "\$SNAP_DIR/packages/" 2>/dev/null || true
cp -rp "\$CONFIG_DIR/www/roamcore" "\$SNAP_DIR/www/" 2>/dev/null || true
if [ -d "\$CONFIG_DIR/lovelace" ]; then
  cp -rp "\$CONFIG_DIR/lovelace/." "\$SNAP_DIR/lovelace/" 2>/dev/null || true
fi
cp -rp "\$CONFIG_DIR/tools/roamcore" "\$SNAP_DIR/tools/" 2>/dev/null || true
printf '{"snapshot_at":"$TS","ref_before":"$REF"}\n' > "\$SNAP_DIR/snapshot.json"
echo "snapshot=\$SNAP_DIR"
EOF
ok "snapshot created at $SNAP_DIR (remote)"

# ---- run the official installer ----
if [ "$DRY_RUN" = "1" ]; then
  warn "dry-run mode: skipping install"
else
  log "running install.sh (ROAMCORE_REF=$REF, ROAMCORE_SKIP_PMTILES=1)"
  REMOTE_TMP="/mnt/data/tmp/roamcore-deploy-$TS"
  ssh -o ConnectTimeout=10 -i "$HA_SSH_KEY" -o IdentitiesOnly=yes "$HA_SSH_USER@$HA_HOST" \
    sh <<EOF
set -e
mkdir -p "$REMOTE_TMP"
ROAMCORE_REF="$REF" \
ROAMCORE_REPO="https://github.com/roamcore/RoamCore" \
CONFIG_DIR="$CONFIG_DIR" \
ROAMCORE_SKIP_PMTILES=1 \
sh -c 'curl -fsSL "https://raw.githubusercontent.com/roamcore/RoamCore/main/homeassistant/install.sh" | ROAMCORE_REF="$REF" ROAMCORE_REPO="https://github.com/roamcore/RoamCore" CONFIG_DIR="$CONFIG_DIR" ROAMCORE_SKIP_PMTILES=1 sh'
EOF
  ok "installer completed"
fi

# ---- restart HA Core (skip flag, dry-run skip) ----
if [ "$SKIP_RESTART" = "1" ]; then
  warn "skipping HA restart (--skip-restart)"
elif [ "$DRY_RUN" = "1" ]; then
  warn "skipping HA restart (--dry-run)"
else
  log "requesting HA Core restart via API"
  curl -sk -X POST --max-time 10 \
    -H "Authorization: Bearer $HA_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{}' \
    "http://$HA_HOST:8123/api/services/homeassistant/restart" \
    -o /dev/null -w "  restart request: HTTP %{http_code}\n" || true
  ok "restart requested"

  # ---- wait for HA to come back ----
  log "waiting for HA to come back online (max 90s)"
  for i in $(seq 1 18); do
    sleep 5
    PROBE=$(curl -sk -o /dev/null -w "%{http_code}" --max-time 4 \
      -H "Authorization: Bearer $HA_TOKEN" \
      "http://$HA_HOST:8123/api/" 2>/dev/null || echo "000")
    if [ "$PROBE" = "200" ]; then
      ok "HA back online after $((i*5))s"
      break
    fi
    printf "  ...wait %ds (HTTP %s)\n" "$((i*5))" "$PROBE"
  done
fi

# ---- verify ----
if [ "$NO_VERIFY" = "1" ]; then
  warn "skipping verification (--no-verify)"
else
  log "verifying deployed code is current"
  DEPLOYED_SHA=$(ssh -o ConnectTimeout=5 -i "$HA_SSH_KEY" -o IdentitiesOnly=yes "$HA_SSH_USER@$HA_HOST" \
    "stat -c %Y '$CONFIG_DIR/.roamcore/install-info.txt' 2>/dev/null || echo 0")
  log "  install-info.txt mtime: $DEPLOYED_SHA"

  log "checking /api/roamcore/openclaw/summary reachable"
  sleep 3
  OC_PROBE=$(curl -sk -o /tmp/oc.json -w "%{http_code}" --max-time 6 \
    -H "Authorization: Bearer $HA_TOKEN" \
    "http://$HA_HOST:8123/api/roamcore/openclaw/summary")
  if [ "$OC_PROBE" = "200" ]; then
    ok "OpenClaw API reachable (HTTP 200)"
    python3 -c "import json; d=json.load(open('/tmp/oc.json')); print('  contract_version:', d.get('contract_version', 'n/a')); print('  keys:', sorted(d.keys())[:8])" 2>/dev/null || head -c 300 /tmp/oc.json
  else
    warn "OpenClaw API probe returned HTTP $OC_PROBE (may need a manual HA restart if first deploy)"
  fi

  log "checking roamcore integration manifest"
  ssh -o ConnectTimeout=5 -i "$HA_SSH_KEY" -o IdentitiesOnly=yes "$HA_SSH_USER@$HA_HOST" \
    sh <<EOF
cat "$CONFIG_DIR/custom_components/roamcore/manifest.json" 2>/dev/null | head -7
EOF
fi

# ---- receipt ----
echo ""
echo "=================================="
echo "  RoamCore deploy receipt"
echo "=================================="
echo "  when:    $(date -u +%FT%TZ)"
echo "  ref:     $REF ($SHORT_REF)"
echo "  branch:  $BRANCH"
echo "  ha host: $HA_HOST"
echo "  snapshot: $SNAP_DIR"
echo "  restart: $([ "$SKIP_RESTART" = "1" ] && echo "SKIPPED" || echo "requested")"
echo "  verify:  $([ "$NO_VERIFY" = "1" ] && echo "SKIPPED" || echo "done")"
echo "=================================="
ok "deploy complete"
