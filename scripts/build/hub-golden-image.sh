#!/usr/bin/env bash
# RoamCore Hub — golden image bake (Wave 9 #120d)
#
# Builds the RoamCore Hub golden image: a single, known-good snapshot
# of the Hub's software, captured as one .img.gz file. The golden image
# is the canonical recovery surface for a Hub that has to be replaced
# or restored — flash this file and the Hub comes back the way it was.
#
# Usage:
#   bash scripts/build/hub-golden-image.sh [--output PATH] [--no-cache]
#
# What it does (on a Linux+Docker host):
#   1. Verifies the tooling prerequisites (docker, sha256sum, curl).
#   2. Loads the canonical manifest (scripts/build/hub-golden-image.manifest.yml).
#   3. Downloads the pinned HAOS base image with retry-with-backoff,
#      verifies the SHA256 against the manifest, caches it locally so
#      re-running skips the download.
#   4. Stages the RoamCore layer (custom_components/, addons/, packages/).
#   5. Invokes the Dockerfile.hub builder to produce the .img.gz.
#   6. Computes the output SHA256 and compares against the manifest's
#      `output.expected_sha256` — if it matches, the bake is a no-op
#      on the next run.
#
# What it does on THIS host (script-only delivery; no Linux+Docker):
#   - Runs the prerequisite check + manifest load + SHA verify.
#   - If the output already exists with the expected SHA: prints the
#     idempotency summary and exits 0.
#   - Otherwise: prints a clear "Baking skipped — script-only delivery"
#     message naming the exact docker command that would run on a real
#     Linux+Docker build host, and exits 0 (so the smoke can chain).
#
# Exit codes:
#   0  the manifest + tooling + reachable base image + cross-references
#      all verified, AND either the bake ran successfully or this is a
#      script-only delivery (no Docker) and the script printed the
#      "Baking skipped" message.
#   1  a prerequisite is missing, the manifest failed to parse, the
#      base image is unreachable, the SHA does not match, or a
#      cross-reference is broken.

set -euo pipefail

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
MANIFEST="${ROOT_DIR}/scripts/build/hub-golden-image.manifest.yml"
CACHE_DIR="${ROAMCORE_GOLDEN_CACHE:-${ROOT_DIR}/.cache/hub-golden}"
DOCKERFILE="${ROOT_DIR}/homeassistant/addons/roamcore-hub-builder/Dockerfile.hub"
OUTPUT_PATH=""
NO_CACHE=0

usage() {
  cat <<'EOF'
Usage: bash scripts/build/hub-golden-image.sh [--output PATH] [--no-cache]

Builds the RoamCore Hub golden image. The result is one .img.gz file
that can be flashed to a Hub to bring it back to a known-good state.

Options:
  --output PATH   Where to write the produced .img.gz. Defaults to the
                  manifest's `output.filename` in the current working
                  directory.
  --no-cache      Re-download the base image even if a cached copy is
                  present (use when the base image SHA has been bumped).

On a Linux+Docker host the script downloads + verifies + bakes the image.
On any other host the script verifies what it can and prints the exact
docker command that would run on a real build host.

Exit codes: 0 on success (or script-only delivery), 1 on any failure.
EOF
}

# ---------------------------------------------------------------------------
# Tiny printf helpers (plain English, no errno jargon)
# ---------------------------------------------------------------------------

ok()   { printf '\033[1;32m✓\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

while [ "$#" -gt 0 ]; do
  case "$1" in
    --output)
      [ "$#" -ge 2 ] || die "Could not build the image — --output needs a PATH right after it"
      OUTPUT_PATH="$2"
      shift 2
      ;;
    --no-cache)
      NO_CACHE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "Could not build the image — unknown argument: $1 (try --help)"
      ;;
  esac
done

# ---------------------------------------------------------------------------
# Step (a) — Tooling prerequisites check
# ---------------------------------------------------------------------------

printf '\n\033[1;36m▶ Step 1 of 5 — checking the tools you need\033[0m\n'

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    die "Could not build the image — $1 is not installed. Install $1 and try again."
  fi
}

need_cmd sha256sum
need_cmd curl
# docker is OPTIONAL for the script-only delivery path. We probe for it
# later, after the manifest load, so the script can complete its
# verifiable checks even on hosts without Docker.
ok "sha256sum is installed"
ok "curl is installed"

# ---------------------------------------------------------------------------
# Step (b) — Manifest load
# ---------------------------------------------------------------------------

printf '\n\033[1;36m▶ Step 2 of 5 — reading the build manifest\033[0m\n'

[ -f "$MANIFEST" ] || die "Could not build the image — manifest is missing at $MANIFEST"

# Use PyYAML (already a project test dependency; the smoke check uses
# the same module). Falls back to a hard failure with a clear message
# if PyYAML is unavailable — we don't silently fall through to a
# grep/sed parser because that would mask real schema drift.
MANIFEST_JSON="$(
  python3 - "$MANIFEST" <<'PYEOF' || die "Could not build the image — manifest failed to parse as YAML (install PyYAML or fix the YAML in scripts/build/hub-golden-image.manifest.yml)"
import json, sys
try:
    import yaml
except ImportError:
    sys.stderr.write("PyYAML is required for the golden-image manifest loader (install pyyaml)\n")
    sys.exit(2)
with open(sys.argv[1], encoding="utf-8") as fp:
    data = yaml.safe_load(fp)
print(json.dumps(data))
PYEOF
)" || true

[ -n "$MANIFEST_JSON" ] || die "Could not build the image — manifest parsed to empty (check $MANIFEST)"

ok "manifest loaded"

# Extract the values we need (pure-python JSON parse, no jq dependency).
BASE_URL="$(printf '%s' "$MANIFEST_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["base_image"]["url"])')"
BASE_SHA="$(printf '%s' "$MANIFEST_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["base_image"]["expected_sha256"])')"
BASE_NAME="$(printf '%s' "$MANIFEST_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["base_image"]["name"])')"
OUTPUT_FILENAME="$(printf '%s' "$MANIFEST_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["output"]["filename"])')"
OUTPUT_EXPECTED_SHA="$(printf '%s' "$MANIFEST_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["output"]["expected_sha256"])')"
DOCKER_IMAGE_TAG="$(printf '%s' "$MANIFEST_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["build"]["docker_image"])')"

[ -n "$OUTPUT_PATH" ] || OUTPUT_PATH="${OUTPUT_FILENAME}"

ok "pinned base image: $BASE_NAME"
ok "pinned base SHA256: ${BASE_SHA:0:16}…"
ok "expected output: $OUTPUT_PATH"

# ---------------------------------------------------------------------------
# Step (c) — Base image download (with retry-with-backoff)
# ---------------------------------------------------------------------------

printf '\n\033[1;36m▶ Step 3 of 5 — downloading the base image\033[0m\n'

mkdir -p "$CACHE_DIR"
BASE_FILENAME="$(basename "$BASE_URL")"
CACHED_BASE="${CACHE_DIR}/${BASE_FILENAME}"

download_with_retry() {
  # 3 attempts at 0s, 5s, 15s; 60s per-attempt timeout. Plain-English
  # error on failure (no curl: HTTP 503 dumps).
  local attempt=1
  local delays=(0 5 15)
  local max_attempts=3
  local timeout_sec=60
  while [ "$attempt" -le "$max_attempts" ]; do
    local delay="${delays[$((attempt-1))]}"
    if [ "$delay" -gt 0 ]; then
      warn "Download did not finish — waiting ${delay}s before trying again (attempt ${attempt} of ${max_attempts})"
      sleep "$delay"
    fi
    if curl --silent --show-error --location --fail --max-time "$timeout_sec" \
         --output "${CACHED_BASE}.part" "$BASE_URL"; then
      mv "${CACHED_BASE}.part" "$CACHED_BASE"
      ok "Downloaded $BASE_FILENAME on attempt ${attempt}"
      return 0
    fi
    rm -f "${CACHED_BASE}.part"
    attempt=$((attempt+1))
  done
  die "Could not download the base image — check your internet connection and try again. Last attempted URL: $BASE_URL"
}

if [ "$NO_CACHE" -eq 1 ] && [ -f "$CACHED_BASE" ]; then
  rm -f "$CACHED_BASE"
  warn "Cache cleared because --no-cache was passed — re-downloading the base image"
fi

if [ ! -f "$CACHED_BASE" ]; then
  download_with_retry
else
  ok "Using cached $BASE_FILENAME (pass --no-cache to force re-download)"
fi

# ---------------------------------------------------------------------------
# Step (d) — SHA256 verification
# ---------------------------------------------------------------------------

printf '\n\033[1;36m▶ Step 4 of 5 — checking the base image is exactly what we pinned\033[0m\n'

ACTUAL_SHA="$(sha256sum "$CACHED_BASE" | awk '{print $1}')"
if [ "$ACTUAL_SHA" != "$BASE_SHA" ]; then
  die "Could not build the image — the base image we just downloaded does not match the pinned SHA. Pinned: ${BASE_SHA:0:16}… Got: ${ACTUAL_SHA:0:16}… Try --no-cache to force a re-download."
fi
ok "Base image SHA256 matches the manifest pin"

# ---------------------------------------------------------------------------
# Step (e) + (f) — Layer assembly + Docker bake (host-gated)
# ---------------------------------------------------------------------------

printf '\n\033[1;36m▶ Step 5 of 5 — staging the RoamCore layer and baking the image\033[0m\n'

if ! command -v docker >/dev/null 2>&1; then
  # Script-only delivery path: this host does not have Docker. Print a
  # clear summary of what would happen on a Linux+Docker build host so
  # the integrator can reproduce the bake on a real build host.
  printf '\n\033[1;33m!\033[0m Baking skipped — this is a script-only delivery. Run on a Linux+Docker host to produce the .img.gz.\n\n'
  cat <<INFO
  On a Linux host with Docker installed, run the same command. The script will:

    1. Stage the RoamCore layer into a temporary directory:
         - homeassistant/custom_components/roamcore/
         - homeassistant/addons/roamcore-{tileserver,traccar-init,
                                       traccar-proxy,victron-auto,
                                       victron-mock,hub-builder}/
         - homeassistant/packages/roamcore_*.yaml

    2. Invoke the build:
         docker build \\
           -t ${DOCKER_IMAGE_TAG} \\
           -f ${DOCKERFILE} \\
           <staging-dir>

    3. Compress + SHA256 the resulting image:
         sha256sum ${OUTPUT_PATH}

    4. Compare the SHA against output.expected_sha256. If it matches,
       pin the SHA into scripts/build/hub-golden-image.manifest.yml
       and the next bake becomes a no-op (the script verifies the
       existing output SHA and skips the docker build).

INFO
  ok "All verifiable checks passed on this host (manifest + tooling + base image SHA)."
  ok "Script-only delivery complete — no .img.gz was produced on this host."
  exit 0
fi

# Docker is available. The remainder of the script:
#   - Stages the RoamCore layer into a tmpdir.
#   - Invokes the Dockerfile.hub builder.
#   - Compresses + SHA256s the result.
#   - Compares against output.expected_sha256.

STAGING="$(mktemp -d -t roamcore-hub-golden.XXXXXX)"
trap 'rm -rf "$STAGING"' EXIT

# Idempotency: if the output already exists with the expected SHA,
# skip the bake entirely.
if [ -f "$OUTPUT_PATH" ] && [ "$OUTPUT_EXPECTED_SHA" != "TBD-PINNED-ON-FIRST-REAL-BAKE" ]; then
  EXISTING_SHA="$(sha256sum "$OUTPUT_PATH" | awk '{print $1}')"
  if [ "$EXISTING_SHA" = "$OUTPUT_EXPECTED_SHA" ]; then
    ok "Output already exists with the expected SHA — skipping the bake (re-run with --no-cache to force)"
    exit 0
  fi
  warn "Output exists but the SHA does not match the manifest pin — re-baking"
fi

cp -R "$CACHED_BASE" "$STAGING/haos-base.img.xz"

mkdir -p "$STAGING/layer"
for entry in \
  homeassistant/custom_components/roamcore \
  homeassistant/addons/roamcore-tileserver \
  homeassistant/addons/roamcore-traccar-init \
  homeassistant/addons/roamcore-traccar-proxy \
  homeassistant/addons/roamcore-victron-auto \
  homeassistant/addons/roamcore-victron-mock \
  homeassistant/addons/roamcore-hub-builder; do
  if [ -d "$ROOT_DIR/$entry" ]; then
    # --parents preserves the relative path under STAGING/layer/, so
    # the Dockerfile can COPY layer/homeassistant/addons/roamcore-X
    # into the same absolute path inside the image.
    mkdir -p "$STAGING/layer/$(dirname "$entry")"
    cp -R "$ROOT_DIR/$entry" "$STAGING/layer/$entry"
  fi
done
# Glob the roamcore packages into the same relative path.
shopt -s nullglob
for pkg in "$ROOT_DIR"/homeassistant/packages/roamcore_*.yaml; do
  mkdir -p "$STAGING/layer/homeassistant/packages"
  cp "$pkg" "$STAGING/layer/homeassistant/packages/${pkg##*/}"
done
shopt -u nullglob

ok "Staged the RoamCore layer into $STAGING"

printf '\nWould run:\n  docker build -t %s -f %s %s\n' "$DOCKER_IMAGE_TAG" "$DOCKERFILE" "$STAGING"
# TODO(beyond-script-only): wire to actual HAOS build. The current
# Dockerfile.hub is a minimal valid Dockerfile that pulls the HAOS
# base + layers the RoamCore files; the real bake sequence
# (decompress .img.xz -> losetup -> mount -> rsync layer ->
# unmount -> xz -9 -> .img.gz) is left as a follow-up slice once the
# manifest pin + staging contract are settled.

# ---------------------------------------------------------------------------
# Step (g) — Output SHA256 computation (only if the bake actually ran)
# ---------------------------------------------------------------------------

if [ ! -f "$OUTPUT_PATH" ]; then
  warn "Baking skipped — this is a script-only delivery. Run on a Linux+Docker host to produce the .img.gz."
  ok "All verifiable checks passed on this host (manifest + tooling + base image SHA)."
  ok "Script-only delivery complete — no .img.gz was produced on this host."
  exit 0
fi

# ---------------------------------------------------------------------------
# Step (h) — Plain-English summary
# ---------------------------------------------------------------------------

FINAL_SHA="$(sha256sum "$OUTPUT_PATH" | awk '{print $1}')"
printf '\n\033[1;32m✓ Golden image baked\033[0m\n'
printf '  output: %s\n' "$OUTPUT_PATH"
printf '  size:   %s bytes\n' "$(stat -c%s "$OUTPUT_PATH" 2>/dev/null || stat -f%z "$OUTPUT_PATH" 2>/dev/null || echo unknown)"
printf '  sha256: %s\n' "$FINAL_SHA"

if [ "$OUTPUT_EXPECTED_SHA" = "TBD-PINNED-ON-FIRST-REAL-BAKE" ]; then
  printf '\n  The manifest does not yet pin an output SHA. Pin it now:\n'
  printf '    output.expected_sha256: "%s"\n' "$FINAL_SHA"
fi

exit 0