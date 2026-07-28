#!/usr/bin/env python3
"""Generate docs/catalog/index.md from the feature pages under docs/catalog/**.

Goal: keep the catalog page as a clean, filterable grid without hand-maintaining
lists. This makes the docs site the central source of truth for features.

Heuristics (v0):
- Include all feature pages under docs/catalog/** excluding README.md, index.md, _templates
- Title: first H1
- Tier: parse a line like '**Support tier:** A|B|C'
- Tags: category folder + a few keyword guesses from filename/title
- Summary: first non-empty paragraph after title (skipping Support tier line)

Later we can move to explicit frontmatter metadata.
"""

from __future__ import annotations

from pathlib import Path
import re
from collections import defaultdict

DOCS = Path(__file__).resolve().parents[1] / "docs"
CATALOG = DOCS / "catalog"


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")


def first_h1(txt: str, fallback: str) -> str:
    m = re.search(r"^#\s+(.+)$", txt, re.M)
    return (m.group(1).strip() if m else fallback)


def parse_tier(txt: str) -> str:
    m = re.search(r"\*\*Support tier:\*\*\s*([ABC])", txt)
    return (m.group(1).lower() if m else "c")


def first_summary(txt: str) -> str:
    lines = [l.rstrip() for l in txt.splitlines()]
    # find title line
    try:
        i = next(i for i, l in enumerate(lines) if l.startswith("# "))
    except StopIteration:
        return ""

    j = i + 1
    while j < len(lines) and not lines[j].strip():
        j += 1

    # skip support tier line
    if j < len(lines) and "Support tier" in lines[j]:
        j += 1
        while j < len(lines) and not lines[j].strip():
            j += 1

    if j < len(lines):
        # Skip sub-headings like "## What this is"; we want a human sentence.
        while j < len(lines) and lines[j].strip().startswith('##'):
            j += 1
            while j < len(lines) and not lines[j].strip():
                j += 1
        if j < len(lines):
            return lines[j].strip()
    return ""


def guess_tags(rel: Path, title: str) -> str:
    tags = []
    # category folder (docs/catalog/<cat>/file.md)
    parts = rel.parts
    if len(parts) >= 3:
        tags.append(parts[1])

    # keyword guesses
    s = f"{title} {rel.stem}".lower()
    for k in [
        "victron",
        "traccar",
        "tailscale",
        "openwrt",
        "mqtt",
        "tileserver",
        "pmtiles",
        "frigate",
        "wican",
        "pihole",
        "adguard",
        "music",
        "nas",
        "bed",
        "level",
    ]:
        if k in s:
            tags.append(k)

    # unique + stable order
    out = []
    for t in tags:
        t = t.replace("_", "-").strip()
        if t and t not in out:
            out.append(t)
    return ",".join(out)


def main() -> int:
    items = []

    for p in sorted(CATALOG.rglob("*.md")):
        rel = p.relative_to(DOCS)
        # Exclude category indexes and the catalog index.
        if rel.name.lower() in ("readme.md", "index.md"):
            continue
        if "_templates" in rel.parts:
            continue

        txt = read_text(p)
        title = first_h1(txt, p.stem)
        tier = parse_tier(txt)
        summary = first_summary(txt)[:140]
        tags = guess_tags(rel, title)

        items.append(
            {
                "title": title,
                "tier": tier,
                "tags": tags,
                # Two URL forms:
                # - `href`: MkDocs HTML URL (with trailing slash). Used by the HTML catalog.
                # - `href_md`: Markdown link form (relative .md path). MkDocs strict mode
                #   accepts this and avoids "unrecognized relative link" warnings.
                "href": str(rel.with_suffix("")).replace("\\", "/") + "/",
                "href_md": str(rel).replace("\\", "/"),
                "summary": summary,
                "category": (rel.parts[1] if len(rel.parts) >= 3 else ""),
            }
        )

    out = [
        "# Catalog\n\n",
        "Use the filters to quickly find what’s supported, and what’s possible.\n\n",
        '<div data-rc-filter-root>\n'
        '  <div class="rc-filter">\n'
        '    <div class="rc-chips">\n'
        '      <a class="rc-chip active" href="#" data-rc-tier="all">All</a>\n'
        '      <a class="rc-chip a" href="#" data-rc-tier="a">Tier A</a>\n'
        '      <a class="rc-chip b" href="#" data-rc-tier="b">Tier B</a>\n'
        '      <a class="rc-chip c" href="#" data-rc-tier="c">Tier C</a>\n'
        "    </div>\n"
        '    <input type="text" placeholder="Search… (e.g. victron, tailscale, traccar)" data-rc-filter-q />\n'
        '    <a class="rc-chip" href="#" data-rc-filter-clear>Clear</a>\n'
        '    <div class="rc-filter-meta">Showing <b data-rc-filter-counter>0</b> items</div>\n'
        "  </div>\n\n"
        '  <div class="rc-grid">\n',
    ]

    for it in items:
        title = it["title"].replace('"', "&quot;")
        out.append(
            f'    <a class="rc-card" data-tier="{it["tier"]}" data-tags="{it["tags"]}" '
            f'data-title="{title}" href="{it["href"]}">'
            f'<div class="rc-card-title">{it["title"]}</div>'
            f'<div class="rc-card-sub">{it["summary"]}</div>'
            "</a>\n"
        )

    out.append("  </div>\n</div>\n")

    (CATALOG / "index.md").write_text("".join(out), encoding="utf-8")
    print(f"Generated catalog/index.md with {len(items)} items")

    # Also generate tier rollup pages (one long scroll per tier)
    def pretty_category(slug: str) -> str:
        return slug.replace("-", " ").replace("_", " ").title()

    by_tier_cat: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for it in items:
        by_tier_cat[it["tier"]][it["category"]].append(it)

    for tier in ["a", "b", "c"]:
        md = []
        md.append(f"# Support tier {tier.upper()}\n\n")
        md.append(
            "One long page listing every feature currently tagged with this tier, grouped by category.\n\n"
        )
        md.append(
            "Tip: use your browser’s find (Ctrl/Cmd+F) to jump quickly (e.g. ‘victron’, ‘tailscale’).\n\n"
        )

        cats = sorted(by_tier_cat.get(tier, {}).keys())
        for cat in cats:
            items2 = sorted(by_tier_cat[tier][cat], key=lambda x: x["title"].lower())
            if not items2:
                continue
            md.append(f"## {pretty_category(cat)}\n\n")
            for it in items2:
                # Use the .md-relative form (href_md) so MkDocs strict mode accepts it
                # without "unrecognized relative link" warnings. Strip the leading
                # 'catalog/' prefix because tier-{a,b,c}.md lives inside docs/catalog/.
                href = it["href_md"].replace("catalog/", "", 1)
                md.append(f"- [{it['title']}]({href}) — {it['summary']}\n")
            md.append("\n")

        (CATALOG / f"tier-{tier}.md").write_text("".join(md), encoding="utf-8")
        print(f"Generated catalog/tier-{tier}.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
