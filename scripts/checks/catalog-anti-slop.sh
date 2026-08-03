#!/usr/bin/env bash
# RoamCore catalog: anti-slop smoke check.
#
# Asserts that the user-facing catalog has no AI slop / placeholder
# text that snuck into the rendered pages. Failure here = a non-technical
# visitor would see lorem-ipsum-style boilerplate.
#
# User-facing pages = the 27 entries linked from docs/catalog/index.md.
# Legacy SUPERSEDED stubs (e.g. docs/catalog/ai/mode.md) are NOT checked
# here because they are internal-tier cruft, not part of the user
# catalog.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

CATALOG_INDEX="docs/catalog/index.md"

if [ ! -f "$CATALOG_INDEX" ]; then
  echo "FAIL: $CATALOG_INDEX missing — cannot define user-facing page set" >&2
  exit 1
fi

# Pull the linked .md paths from the catalog index. One per line.
linked_paths=$(grep -oE '\([^)]+\.md\)' "$CATALOG_INDEX" | tr -d '()' | sort -u)

if [ -z "$linked_paths" ]; then
  echo "FAIL: no .md links found in $CATALOG_INDEX" >&2
  exit 1
fi

# Patterns that should NEVER appear in a user-facing catalog page.
# Each pattern is a whole-line match (anchored) so we don't false-positive
# on legitimate uses inside code fences.
slop_patterns=(
  "A .* tile that updates automatically\\."     # the placeholder line
  "RoamCore catalog entry"                       # humanize_summary fallback
  "Placeholder for common"                       # old stub copy
  "## Install / best next step"                  # old stub heading
  "needs_curation_review"                        # internal flag should never leak
  "legacy tier-c spec"                           # slop sentinel
  "legacy tier-b spec"                           # slop sentinel
  "## What this is"                              # old stub heading
  "Why it's useful in a van"                     # old stub heading
  "Support tier:"                                # tier-letter jargon
  "Backend: Wave"
)

fail=0
echo "Checking $(echo "$linked_paths" | wc -l) user-facing catalog pages for slop..."
for rel in $linked_paths; do
  page="docs/catalog/$rel"
  if [ ! -f "$page" ]; then
    echo "  FAIL: $page is linked from index.md but does not exist" >&2
    fail=1
    continue
  fi
  for pat in "${slop_patterns[@]}"; do
    if grep -nE "$pat" "$page" >/dev/null 2>&1; then
      echo "  FAIL: $page contains slop pattern: $pat" >&2
      grep -nE "$pat" "$page" | head -2 | sed 's/^/        /' >&2
      fail=1
    fi
  done
done

# Also check no MkDocs nav target points to a file that doesn't exist.
for nav_path in $(grep -oE 'catalog/[^:]+: ?catalog/[^ ]+\.md' mkdocs.yml 2>/dev/null | awk '{print $2}'); do
  if [ ! -f "docs/$nav_path" ]; then
    echo "  FAIL: mkdocs nav target docs/$nav_path does not exist" >&2
    fail=1
  fi
done

# And assert no broken links inside the docs/ tree (intra-docs).
# Uses a small Python helper since grep can't validate .md targets.
broken=$(python3 - <<'PY' 2>/dev/null || true
import re, pathlib
ROOT = pathlib.Path('docs')
bad = []
for f in ROOT.rglob('*.md'):
    if '_templates' in f.parts: continue
    text = f.read_text()
    for m in re.finditer(r'\[[^\]]*\]\(([^)]+)\)', text):
        link = m.group(1).strip().split('#')[0].split(' ')[0]
        if not link or link.startswith('http') or link.startswith('mailto:'):
            continue
        target = (f.parent / link).resolve()
        try:
            target.relative_to(ROOT.resolve())
        except ValueError:
            continue
        if not target.is_file() and not (target.is_dir() and (target/'index.md').exists()):
            bad.append(f"{f.relative_to(ROOT)} -> {link}")
for b in bad:
    print(b)
PY
)
if [ -n "$broken" ]; then
  echo "  FAIL: broken intra-docs links:" >&2
  echo "$broken" | sed 's/^/        /' >&2
  fail=1
fi

if [ "$fail" -ne 0 ]; then
  echo "FAIL: catalog slop check failed" >&2
  exit 1
fi

echo "OK: $(echo "$linked_paths" | wc -l) pages clean, no slop patterns, no broken links."
