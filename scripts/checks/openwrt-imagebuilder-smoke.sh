#!/usr/bin/env bash
# RoamCore — OpenWrt Image Builder (Wave 9 #106) smoke check.
#
# Validates:
#   1. The imagebuilder directory tree exists and is non-empty.
#   2. Per-target manifests are well-formed (one package per non-blank
#      non-comment line).
#   3. The bake/files overlay includes the API service, firewall, the
#      first-boot wizard, and the LuCI landing-page files.
#   4. The build script is syntactically valid bash.
#   5. The first-boot wizard is syntactically valid POSIX shell.
#
# This is a REPO-LOCAL smoke check (no Image Builder, no Docker). It
# is safe to run on any host. The actual sysupgrade.itb is built via
# `openwrt/imagebuilder/build.sh` inside the pinned container.
#
# Usage:
#   bash scripts/checks/openwrt-imagebuilder-smoke.sh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IB_DIR="${ROOT_DIR}/openwrt/imagebuilder"

fail() { printf '\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }
pass() { printf '\033[1;32m✓ %s\033[0m\n' "$*"; }

# ----- 1. Tree exists ---------------------------------------------------

[ -d "${IB_DIR}" ] || fail "openwrt/imagebuilder directory missing"
[ -d "${IB_DIR}/manifests" ] || fail "openwrt/imagebuilder/manifests missing"
[ -d "${IB_DIR}/bake/files" ] || fail "openwrt/imagebuilder/bake/files missing"
[ -f "${IB_DIR}/build.sh" ] || fail "openwrt/imagebuilder/build.sh missing"
[ -f "${IB_DIR}/Dockerfile" ] || fail "openwrt/imagebuilder/Dockerfile missing"
pass "imagebuilder tree present"

# ----- 2. Manifests are well-formed ------------------------------------

required_manifests=(x86_64-generic gl-mt3000 bananapi-bpi-r3 ath79-generic)
for m in "${required_manifests[@]}"; do
  f="${IB_DIR}/manifests/${m}.manifest"
  [ -f "${f}" ] || fail "manifest missing: ${m}.manifest"
  # Each non-blank, non-comment line must be a bare package token.
  bad="$(grep -v '^[[:space:]]*#' "${f}" \
         | grep -v '^[[:space:]]*$' \
         | grep -v '^[[:space:]]*[A-Za-z0-9_.+-]\+[[:space:]]*$' || true)"
  if [ -n "${bad}" ]; then
    printf '%s\n' "${bad}" >&2
    fail "manifest ${m} has malformed package lines"
  fi
done
pass "all 4 manifests well-formed (${#required_manifests[@]} targets)"

# ----- 3. Bake-in files present ----------------------------------------

required_files=(
  "etc/init.d/roamcore-api"
  "etc/init.d/roamcore-fw"
  "etc/uci-defaults/99-roamcore-firstboot"
  "opt/roamcore/api.py"
  "opt/roamcore/iptables_mvp.sh"
  "www/luci-static/resources/view/roamcore_status.js"
  "www/luci-static/resources/view/roamcore_menu.js"
)
for rf in "${required_files[@]}"; do
  [ -f "${IB_DIR}/bake/files/${rf}" ] || fail "bake-in file missing: ${rf}"
done
pass "all 7 bake-in files present"

# api.py must still parse as Python (the smoke catches an accidental
# bad merge of the upstream netstack code).
python3 -c "import ast,sys; ast.parse(open('${IB_DIR}/bake/files/opt/roamcore/api.py').read())" \
  || fail "baked api.py does not parse as Python"
pass "baked api.py parses"

# ----- 4. build.sh is syntactically valid bash --------------------------

bash -n "${IB_DIR}/build.sh" || fail "build.sh has bash syntax errors"
pass "build.sh syntax OK"

# ----- 5. first-boot wizard is valid POSIX/sh ---------------------------

sh -n "${IB_DIR}/bake/files/etc/uci-defaults/99-roamcore-firstboot" \
  || fail "first-boot wizard has sh syntax errors"
pass "first-boot wizard syntax OK"

# ----- 6. build.sh references all 4 targets ----------------------------

missing="$(grep -oE '\b(x86_64-generic|gl-mt3000|bananapi-bpi-r3|ath79-generic)\b' \
  "${IB_DIR}/build.sh" | sort -u)"
for t in "${required_manifests[@]}"; do
  echo "${missing}" | grep -q "${t}" || fail "build.sh does not reference target ${t}"
done
pass "build.sh references all 4 supported targets"

# ----- 7. README + flash instructions ---------------------------------

[ -f "${ROOT_DIR}/openwrt/README.md" ] || fail "openwrt/README.md missing"
grep -qi "Flash instructions" "${ROOT_DIR}/openwrt/README.md" \
  || fail "openwrt/README.md missing 'Flash instructions' section"
grep -qi "192.168.1.250:8080" "${ROOT_DIR}/openwrt/README.md" \
  || fail "openwrt/README.md missing the verify curl one-liner"
pass "openwrt/README.md has Flash instructions section"

[ -f "${IB_DIR}/README.md" ] || fail "openwrt/imagebuilder/README.md missing"
pass "imagebuilder README present"

# ----- 8. No secrets baked in ------------------------------------------

# RC_API_TOKEN must NEVER appear as a literal value in the bake tree.
if grep -RInE 'RC_API_TOKEN=[A-Za-z0-9]{16,}' "${IB_DIR}/bake/" 2>/dev/null; then
  fail "bake tree contains a literal RC_API_TOKEN (must be generated at runtime)"
fi
pass "no RC_API_TOKEN literal in bake tree"

# HA tokens look like ~64 chars; we must not see any.
if grep -RInE '(RC_HA_TOKEN|RC_HOMEASSISTANT_TOKEN)=[A-Za-z0-9._-]{16,}' \
     "${IB_DIR}/bake/" 2>/dev/null; then
  fail "bake tree contains a literal HA token"
fi
pass "no HA token literal in bake tree"

# ----- 9. .gitignore covers the artifacts -------------------------------

git_root="${ROOT_DIR}"
if [ -f "${git_root}/.gitignore" ]; then
  if ! grep -qE '^openwrt/flash/' "${git_root}/.gitignore"; then
    printf '\n# OpenWrt image builder artifacts\nopenwrt/flash/\n' >> "${git_root}/.gitignore"
    pass "added openwrt/flash/ to .gitignore (artifacts dir excluded)"
  else
    pass "openwrt/flash/ already in .gitignore"
  fi
fi

printf '\n\033[1;32m▶ OpenWrt imagebuilder smoke check: PASS\033[0m\n'