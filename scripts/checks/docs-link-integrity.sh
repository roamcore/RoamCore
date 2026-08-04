#!/usr/bin/env bash
set -euo pipefail

# RoamCore — docs link-integrity check.
#
# Walks every .md file under docs/ and asserts that every relative-link
# target (those starting with ./) or ../../ or ../../.. etc.) resolves
# to a file that exists on disk. Catches both:
#   - Markdown links: ](path)
#   - HTML hrefs:     href="path"
#
# Wired into scripts/check.sh so this fails the build the moment a
# future slice breaks a link.

cd "$(dirname "$0")/../.."  # repo root

fail=0
checked=0
broken_lines=()

is_external() {
  case "$1" in
    "" | "#"*) return 0 ;;
    http://* | https://* | mailto:* | tel:*) return 0 ;;
  esac
  return 1
}

check_target() {
  local md="$1"
  local target="$2"
  is_external "$target" && return 0
  local md_dir
  md_dir="$(dirname "$md")"
  local abs
  abs="$(cd "$md_dir" && realpath -m -- "$target" 2>/dev/null || true)"
  checked=$((checked + 1))
  if [ -z "$abs" ] || [ ! -e "$abs" ]; then
    echo "✗ $md: BROKEN LINK -> $target" >&2
    fail=$((fail + 1))
  fi
}

while IFS= read -r -d '' md; do
  # Markdown links: ](path)
  while IFS= read -r link; do
    target="${link#*(}"
    target="${target%)*}"
    check_target "$md" "$target"
  done < <(grep -oE '\]\([^)]+\)' "$md" || true)

  # HTML hrefs: href="path"
  while IFS= read -r href; do
    target="${href#href=\"}"
    target="${target%\"}"
    check_target "$md" "$target"
  done < <(grep -oE 'href="[^"]+"' "$md" || true)
done < <(find docs -name '*.md' -type f -print0)

if [ "$fail" -gt 0 ]; then
  echo "" >&2
  echo "✗ docs-link-integrity: $fail broken link(s) out of $checked checked." >&2
  exit 1
fi
echo "✓ docs-link-integrity: $checked links checked, all resolve."