#!/usr/bin/env python3
"""Append/refresh a feature list on each catalog category index page.

For every docs/catalog/<category>/index.md, we:
- Keep the existing intro/overview text
- Replace the block between markers with a generated list of feature pages in that folder

This makes category pages the primary navigation surface: overview + clear list.
"""

from __future__ import annotations

from pathlib import Path
import re

DOCS = Path(__file__).resolve().parents[1] / "docs"
CAT = DOCS / "catalog"

START = "<!-- RC_FEATURE_LIST_START -->"
END = "<!-- RC_FEATURE_LIST_END -->"


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")


def first_h1(txt: str, fallback: str) -> str:
    m = re.search(r"^#\s+(.+)$", txt, re.M)
    return (m.group(1).strip() if m else fallback)


def parse_tier(txt: str) -> str:
    m = re.search(r"\*\*Support tier:\*\*\s*([ABC])", txt)
    return (m.group(1).lower() if m else "c")


def first_summary(txt: str) -> str:
    lines = [l.rstrip() for l in txt.splitlines()]
    try:
        i = next(i for i, l in enumerate(lines) if l.startswith("# "))
    except StopIteration:
        return ""
    j = i + 1
    while j < len(lines) and not lines[j].strip():
        j += 1
    if j < len(lines) and "Support tier" in lines[j]:
        j += 1
        while j < len(lines) and not lines[j].strip():
            j += 1
    return lines[j].strip() if j < len(lines) else ""


def render_list(items: list[dict]) -> str:
    out = []
    out.append("\n## Features\n\n")
    out.append("<div class=\"rc-feature-list\">\n")
    for it in items:
        tier = it["tier"]
        title = it["title"].replace('"', "&quot;")
        summary = it["summary"]
        out.append(
            f'  <a class="rc-feature" href="{it["href"]}" data-tier="{tier}">'
            f'<div class="rc-feature-left">'
            f'<div class="rc-feature-title">{title}</div>'
            f'<div class="rc-feature-sub">{summary}</div>'
            f'</div>'
            f'<div class="rc-feature-right"><span class="rc-tier {tier}">{tier.upper()}</span></div>'
            f'</a>\n'
        )
    out.append("</div>\n")
    return "".join(out)


def upsert_block(txt: str, block: str) -> str:
    if START in txt and END in txt:
        pre = txt.split(START)[0]
        post = txt.split(END)[1]
        return pre + START + "\n" + block + "\n" + END + post
    # Append markers at end
    return txt.rstrip() + "\n\n" + START + "\n" + block + "\n" + END + "\n"


def main() -> int:
    for catdir in sorted(CAT.iterdir()):
        if not catdir.is_dir():
            continue
        if catdir.name.startswith('_'):
            continue
        idx = catdir / "index.md"
        if not idx.exists():
            continue

        # Collect feature pages in this folder (direct children)
        items = []
        for p in sorted(catdir.glob('*.md')):
            if p.name.lower() == 'index.md':
                continue
            txt = read(p)
            title = first_h1(txt, p.stem)
            tier = parse_tier(txt)
            summary = first_summary(txt)[:160]
            rel = p.relative_to(DOCS)
            items.append({
                'title': title,
                'tier': tier,
                'summary': summary,
                'href': str(rel).replace('\\','/'),
            })

        # Keep index content but refresh feature list block
        txt = read(idx)
        block = render_list(items) if items else "\n## Features\n\nNothing listed here yet.\n"
        out = upsert_block(txt, block)
        idx.write_text(out, encoding='utf-8')

    print('Updated category index pages')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
