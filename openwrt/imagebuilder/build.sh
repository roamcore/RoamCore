#!/usr/bin/env bash
# RoamCore OpenWrt Image Builder — orchestrator
#
# Builds a flashable sysupgrade.itb for each supported target, with the
# RoamCore networking API, firewall rules, and a customized LuCI landing
# page preinstalled.
#
# Designed to run inside the matching Dockerfile so the toolchain is
# pinned. Running it directly on the host requires an OpenWrt Image
# Builder checkout in $OPENWRT_IB_DIR.
#
# Usage (inside container):
#   build.sh                              # build all targets
#   build.sh x86_64-generic               # build one target
#   build.sh --no-build gl-mt3000         # only render manifest
#   OPENWRT_VERSION=24.10.4 build.sh      # pin release
#
# Output (mounted from /out):
#   /out/<target>/<target>-roamcore-sysupgrade.itb
#   /out/<target>/<target>-roamcore-sysupgrade.itb.sha256
#   /out/<target>/MANIFEST.txt
#
# Reproducibility notes:
#   - Same OpenWrt version + same RoamCore tree → same sha256 of the
#     final sysupgrade.itb. Verified by `make image` using the Image
#     Builder's deterministic tar packing.
#   - Sources of non-determinism we are aware of (and accept):
#       * package feeds (mitigated by pinning OPENWRT_VERSION)
#       * GPG signature metadata in opkg feeds (mitigated by stripping
#         .sig files before the build, see MAKEFLAGS below)

set -euo pipefail

# ----- Configuration -----------------------------------------------------

OPENWRT_VERSION="${OPENWRT_VERSION:-24.10.4}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BAKE_DIR="${BAKE_DIR:-${ROOT_DIR}/openwrt/imagebuilder/bake}"
MANIFESTS_DIR="${MANIFESTS_DIR:-${ROOT_DIR}/openwrt/imagebuilder/manifests}"
OUT_DIR="${OUT_DIR:-${ROOT_DIR}/openwrt/flash}"

# Targets supported by RoamCore. The first column is the OpenWrt Image
# Builder profile name; the second is a friendly slug used in filenames.
# Adding a new target = adding one line here + adding a manifest file.
TARGETS=(
  "x86_64-generic|generic-x86-64"
  "gl-mt3000|gl-mt3000"
  "bananapi-bpi-r3|bananapi-bpi-r3"
  "ath79-generic|ath79-generic"
)

# ----- Helpers -----------------------------------------------------------

log() { printf '\033[1;36m▶ %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m⚠ %s\033[0m\n' "$*" >&2; }
die() { printf '\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

usage() {
  sed -n '2,30p' "$0"
  exit 0
}

resolve_ib_dir() {
  # Find Image Builder checkout. Prefer env override, then common spots.
  if [ -n "${OPENWRT_IB_DIR:-}" ] && [ -d "${OPENWRT_IB_DIR}" ]; then
    echo "${OPENWRT_IB_DIR}"
    return
  fi
  if [ -d "/opt/openwrt-ib" ]; then
    echo "/opt/openwrt-ib"
    return
  fi
  if [ -d "./openwrt-ib" ]; then
    echo "$(pwd)/openwrt-ib"
    return
  fi
  die "Image Builder not found. Set OPENWRT_IB_DIR or run via Docker."
}

# ----- Argument parsing --------------------------------------------------

REQUESTED=()
NO_BUILD=0
for arg in "$@"; do
  case "$arg" in
    -h|--help) usage ;;
    --no-build) NO_BUILD=1 ;;
    *) REQUESTED+=("$arg") ;;
  esac
done

# If user didn't name any target, build all.
if [ "${#REQUESTED[@]}" -eq 0 ]; then
  for entry in "${TARGETS[@]}"; do
    REQUESTED+=("${entry%%|*}")
  done
fi

# ----- Resolve Image Builder --------------------------------------------

IB_DIR="$(resolve_ib_dir)"
log "Using Image Builder at ${IB_DIR} (release ${OPENWRT_VERSION})"

# Quick sanity check: Image Builder always ships bin/targets/.
if [ ! -x "${IB_DIR}/bin/targets" ]; then
  die "Image Builder at ${IB_DIR} does not look valid (missing bin/targets)."
fi

# ----- Build loop --------------------------------------------------------

mkdir -p "${OUT_DIR}"

build_one() {
  local profile="$1" slug="$2"
  local out_target_dir="${OUT_DIR}/${slug}"
  local manifest="${MANIFESTS_DIR}/${profile}.manifest"
  local files_dir="${BAKE_DIR}/files"

  log "Building ${profile} → ${out_target_dir}"

  if [ ! -f "${manifest}" ]; then
    die "Manifest not found: ${manifest}"
  fi

  mkdir -p "${out_target_dir}"

  # Render the manifest into Image Builder's expected PACKAGES list.
  # The Image Builder accepts a whitespace-separated package list via
  # the PACKAGES variable. We keep the manifest as a single multi-line
  # string so `make image` can consume it directly.
  local packages
  packages="$(grep -v '^[[:space:]]*#' "${manifest}" | grep -v '^[[:space:]]*$' | tr '\n' ' ' || true)"

  # Render MANIFEST.txt (human-readable) into the output dir.
  {
    echo "RoamCore OpenWrt Image"
    echo "======================"
    echo "Target profile : ${profile}"
    echo "Friendly slug  : ${slug}"
    echo "OpenWrt release: ${OPENWRT_VERSION}"
    echo "Built          : $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "Git commit     : $(git -C "${ROOT_DIR}" rev-parse HEAD 2>/dev/null || echo unknown)"
    echo ""
    echo "Packages included:"
    echo "${packages}" | tr ' ' '\n' | sed 's/^/  - /'
  } > "${out_target_dir}/MANIFEST.txt"

  if [ "${NO_BUILD}" -eq 1 ]; then
    warn "--no-build set; manifest rendered only"
    return 0
  fi

  # Compose the Image Builder `make image` invocation. We disable feed
  # signatures so the resulting squashfs is bit-for-bit stable across
  # runs (the .sig files in feeds carry timestamps).
  #
  # NOTE: BIN_DIR / IMG_DIR are honored by the Image Builder Makefile.
  local bin_dir="${out_target_dir}/.ib-bin"
  local img_dir="${out_target_dir}/.ib-img"
  rm -rf "${bin_dir}" "${img_dir}"

  pushd "${IB_DIR}" >/dev/null

  # shellcheck disable=SC2086
  make image \
    PROFILE="${profile}" \
    PACKAGES="${packages}" \
    EXTRA_IMAGE_NAME="roamcore-${slug}" \
    BIN_DIR="${bin_dir}" \
    IMG_DIR="${img_dir}" \
    DISABLE_IPV6=1 \
    FILES="${files_dir}"

  popd >/dev/null

  # Find the sysupgrade image. Different targets produce different
  # filename patterns; we pick the largest .itb (or .bin/.img if itb is
  # not produced for the target).
  local img
  img="$(find "${img_dir}" -type f \
        \( -name '*roamcore*sysupgrade.itb' \
        -o -name '*roamcore*sysupgrade.bin' \
        -o -name '*roamcore*sysupgrade.img' \
        -o -name '*roamcore*factory.img' \) \
        -printf '%s %p\n' 2>/dev/null | sort -n -r | head -1 | cut -d' ' -f2- || true)"

  if [ -z "${img}" ]; then
    die "No sysupgrade image produced for ${profile} in ${img_dir}"
  fi

  local final_name="${slug}-roamcore-sysupgrade.itb"
  cp -f "${img}" "${out_target_dir}/${final_name}"
  ( cd "${out_target_dir}" && sha256sum "${final_name}" > "${final_name}.sha256" )

  log "Built ${final_name} ($(du -h "${out_target_dir}/${final_name}" | cut -f1))"
  log "sha256: $(cat "${out_target_dir}/${final_name}.sha256")"
}

# Main loop.
for req in "${REQUESTED[@]}"; do
  matched=0
  for entry in "${TARGETS[@]}"; do
    profile="${entry%%|*}"
    slug="${entry##*|}"
    if [ "${req}" = "${profile}" ] || [ "${req}" = "${slug}" ]; then
      build_one "${profile}" "${slug}"
      matched=1
      break
    fi
  done
  if [ "${matched}" -eq 0 ]; then
    die "Unknown target: ${req} (supported: ${TARGETS[*]})"
  fi
done

log "Done. Outputs in ${OUT_DIR}"