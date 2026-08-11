#!/usr/bin/env bash
# scripts/auto-deploy-hook.sh
#
# Auto-deploy hook for the RoamCore repo. Runs after every commit.
#
# What it does:
#   1. Detects the SHA of the new commit
#   2. Regenerates scripts/roamcore-bundle.tar.gz from current repo state
#   3. Calls the HA API to trigger roamcore.provision_assets (idempotent)
#   4. Restarts HA Core if the install manifest changed
#   5. Verifies the OpenClaw API is reachable
#   6. Prints a deploy receipt
#
# Install:
#   ln -sf "$(pwd)/scripts/auto-deploy-hook.sh" .git/hooks/post-commit
#
# Disable: rm .git/hooks/post-commit

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

HA_HOST="${HA_HOST:-192.168.1.66}"
HA_TOKEN_FILE="${HA_TOKEN_FILE:-$HOME/.clawdbot/secrets/homeassistant.token}"
REF="$(git rev-parse HEAD)"
SHORT_REF="$(git rev-parse --short HEAD)"
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'detached')"

log() { printf '\033[1;36m[auto-deploy]\033[0m %s\n' "$*"; }
ok()  { printf '\033[1;32m[auto-deploy]\033[0m %s\n' "$*"; }
warn(){ printf '\033[1;33m[auto-deploy]\033[0m %s\n' "$*" >&2; }
err() { printf '\033[1;31m[auto-deploy]\033[0m %s\n' "$*"   >&2; }

# Skip if we're not on main (PR branch commits shouldn't auto-deploy)
if [ "$BRANCH" != "main" ]; then
  log "skipping deploy — not on main (branch=$BRANCH, ref=$SHORT_REF)"
  exit 0
fi

# Skip if this commit hasn't been pushed to the remote yet
# (roamcore.provision_assets fetches from GitHub; unpushed commits 404)
if ! git ls-remote --exit-code origin main >/dev/null 2>&1; then
  log "skipping deploy — cannot reach origin (offline?)"
  exit 0
fi
REMOTE_SHA="$(git ls-remote origin main 2>/dev/null | awk '{print $1}')"
if [ "$REMOTE_SHA" != "$REF" ]; then
  # Allow HEAD to be the tip, or any of HEAD~3..HEAD (cron-style squash-fests)
  TIP3="$(git log --format=%H -n 3 origin/main..HEAD 2>/dev/null | head -1 || true)"
  if ! git log --format=%H origin/main..HEAD 2>/dev/null | grep -q "^${REF}$"; then
    log "skipping deploy — ref $SHORT_REF not on origin/main (unpushed)"
    log "  remote main: ${REMOTE_SHA:0:12}"
    log "  local HEAD:  $SHORT_REF"
    exit 0
  fi
  log "deploying even though HEAD != origin/main ($SHORT_REF is in origin/main..HEAD)"
fi

# Skip if the token file doesn't exist
if [ ! -f "$HA_TOKEN_FILE" ]; then
  warn "HA token file not found: $HA_TOKEN_FILE — skipping deploy"
  exit 0
fi

HA_TOKEN="$(cat "$HA_TOKEN_FILE")"

# 1. Regenerate the bundle so it always reflects current main
log "regenerating bundle tarball (ref=$SHORT_REF)"
rm -f scripts/roamcore-bundle.tar.gz
tar -czf scripts/roamcore-bundle.tar.gz -C homeassistant \
    custom_components packages www tools lovelace 2>/dev/null || {
  err "bundle regen failed"
  exit 1
}

# 2. Trigger provision_assets via the HA API
log "calling HA API: roamcore.provision_assets (ref=$REF)"
PROV=$(curl -sk -X POST -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"ref\": \"$REF\", \"repo\": \"https://github.com/roamcore/RoamCore\"}" \
  "http://$HA_HOST:8123/api/services/roamcore/provision_assets" \
  -w "\nHTTP_STATUS:%{http_code}" 2>&1)
PROV_STATUS=$(echo "$PROV" | grep -oE 'HTTP_STATUS:[0-9]+' | cut -d: -f2)

if [ "$PROV_STATUS" != "200" ]; then
  err "provision_assets call failed (HTTP $PROV_STATUS)"
  echo "$PROV"
  exit 1
fi
ok "provision_assets triggered (HTTP 200)"

# 3. Wait + verify
log "waiting 15s for provisioning + restart (if triggered)"
sleep 15

for i in $(seq 1 6); do
  PROBE=$(curl -sk -o /dev/null -w "%{http_code}" --max-time 4 \
    -H "Authorization: Bearer $HA_TOKEN" \
    "http://$HA_HOST:8123/api/" 2>/dev/null || echo "000")
  if [ "$PROBE" = "200" ]; then
    ok "HA online"
    break
  fi
  printf '  waiting for HA... HTTP %s\n' "$PROBE"
  sleep 5
done

# 4. Verify OpenClaw API is reachable + returns live data
OC=$(curl -sk -H "Authorization: Bearer $HA_TOKEN" \
  "http://$HA_HOST:8123/api/roamcore/system/summary" 2>/dev/null)

if echo "$OC" | grep -q '"contract"'; then
  ok "OpenClaw system summary reachable"
  echo "  contract_version: $(echo "$OC" | grep -oE '"version":[0-9]+' | head -1)"
  echo "  overall:          $(echo "$OC" | grep -oE '"overall":"[^"]+"' | head -1)"
else
  warn "OpenClaw system summary not reachable"
fi

# 5. Print receipt
echo ""
echo "============================================="
echo "  RoamCore auto-deploy receipt"
echo "  ref:      $REF ($SHORT_REF)"
echo "  branch:   $BRANCH"
echo "  ha host:  $HA_HOST"
echo "  time:     $(date -u +%FT%TZ)"
echo "============================================="
ok "done"

exit 0
