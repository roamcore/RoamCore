#!/usr/bin/env bash
# RoamCore smoke check: ensure no giant SUPERSEDED banner leaks into the
# user-facing docs tree.
#
# Wave 9 #124b (follow-up to Wave 9 #124 docs cleanup). Per the directive
# repo-hygiene § "user-facing repo", end users should never see the
# legacy multi-line SUPERSEDED block — promoted stubs should be clean
# 2-line redirect pages pointing at the canonical connection recipe.
#
# Scans docs/**/*.md for the giant supersession banner pattern:
#   - a blockquote block (lines starting with ">") whose first non-blank
#     line contains the word "SUPERSEDED" AND whose total block length
#     exceeds 5 lines (the "giant banner" — a short 1-line mention is OK).
#   - OR a paragraph containing the literal phrase "**Replaced by**"
#     used as a banner header.
#
# Excludes:
#   - connections/*/docs/   (developer plumbing, owned by connection tests)
#   - docs-internal/        (internal docs, not user-facing)
#   - GRANDFATHERED_FILES   (explicitly accepted by prior slices; tracked
#     here so future cleanup can remove them from this list)
#
# Exit codes:
#   0 — clean (no giant banners in user tree)
#   1 — one or more banners found
#   2 — usage / scan error

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() { echo "ERROR: $*" >&2; exit 1; }

# --- Args ---
SHOW_OK=0
for arg in "$@"; do
  case "$arg" in
    -v|--verbose) SHOW_OK=1 ;;
    -h|--help)
      sed -n '2,32p' "$0"
      exit 0
      ;;
    *) ;;
  esac
done

# Grandfathered legacy stubs (explicitly accepted by Wave 9 #124 — see
# commit f0241e1 verification: "only historical banners (acceptable)").
# Wave 9 #124c cleaned up ALL remaining SUPERSEDED stubs in the user
# tree (20 connection-specific + category-index stubs → 2-line
# "Moved to" redirect pages pointing at the canonical connection
# recipe). The GRANDFATHERED_FILES list is now empty.
GRANDFATHERED_FILES=()

# --- Pre-flight ---
[ -d docs ] || fail "missing docs/ — run from repo root"

# --- Find candidate files ---
# User tree = docs/**/*.md minus connections/*/docs/ minus docs-internal/
mapfile -t CANDIDATES < <(
  find docs -type f -name '*.md' \
    -not -path 'docs-internal/*' \
    -not -path 'docs/connections/*' \
    | sort
)

if [ "${#CANDIDATES[@]}" -eq 0 ]; then
  echo "OK: no user-tree markdown files found"
  exit 0
fi

violations=0
checked=0
grandfathered=0

for f in "${CANDIDATES[@]}"; do
  # Skip explicitly grandfathered files (see GRANDFATHERED_FILES above).
  skip=0
  for gf in "${GRANDFATHERED_FILES[@]}"; do
    if [ "$f" = "$gf" ]; then
      skip=1
      grandfathered=$((grandfathered + 1))
      break
    fi
  done
  if [ "$skip" -eq 1 ]; then
    continue
  fi
  checked=$((checked + 1))

  # Use Python for reliable multi-line blockquote detection. Awk is fine
  # but the block-length tracking is cleaner in Python.
  if ! python3 - "$f" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    text = path.read_text(encoding="utf-8")
except Exception as e:
    print(f"READ_ERROR: {e}", file=sys.stderr)
    sys.exit(2)

lines = text.splitlines()

# Pattern A: giant SUPERSEDED blockquote (> 5 lines, first non-blank line
# contains the literal word SUPERSEDED).
i = 0
while i < len(lines):
    line = lines[i].rstrip()
    if line.lstrip().startswith(">"):
        # Start of a blockquote run.
        start = i
        while i < len(lines) and lines[i].lstrip().startswith(">"):
            i += 1
        block = lines[start:i]
        # Strip leading '>' and whitespace.
        clean = [ln.lstrip().lstrip(">").strip() for ln in block]
        # Find first non-blank line.
        first = next((c for c in clean if c), "")
        if "SUPERSEDED" in first.upper() and len(block) > 5:
            print(
                f"BANNER: {path}:{start + 1}: giant SUPERSEDED "
                f"blockquote ({len(block)} lines) — first line: "
                f"{first[:80]!r}",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        i += 1

# Pattern B: paragraph with literal "**Replaced by**" phrase used as a
# banner header (markdown bold).
for n, line in enumerate(lines, 1):
    if "**Replaced by" in line:
        print(
            f"BANNER: {path}:{n}: '**Replaced by**' banner found — "
            f"line: {line.strip()[:80]!r}",
            file=sys.stderr,
        )
        sys.exit(1)

sys.exit(0)
PY
  then
    violations=$((violations + 1))
  fi
done

if [ "$violations" -gt 0 ]; then
  echo "" >&2
  echo "FAIL: $violations file(s) in user tree still carry giant SUPERSEDED banners." >&2
  echo "      Convert to 2-line 'Moved to /catalog/X/' redirect pages," >&2
  echo "      OR delete + add mkdocs.yml redirect_maps entry." >&2
  echo "      See directive repo-hygiene § 'user-facing repo'." >&2
  exit 1
fi

if [ "$SHOW_OK" -eq 1 ]; then
  echo "OK: scanned $checked user-tree markdown files; no giant SUPERSEDED banners"
  if [ "$grandfathered" -gt 0 ]; then
    echo "    ($grandfathered grandfathered files skipped — see GRANDFATHERED_FILES in script)"
  fi
fi
exit 0
