#!/usr/bin/env python3
"""Catalog robot for the RoamCore connections pipeline.

Reads connections/<id>/connection.yml + connections/registry.json
and generates per-connection docs pages under docs/connections/<id>.md.

This is the other half of the catalog contract: the audit script
emits the registry, this script emits the docs. Both are derived from
the same source-of-truth manifests, so they cannot drift.

Generates:
  docs/connections/<id>.md     — one page per connection
  docs/connections/index.md    — master index grouped by tier + category
  docs/catalog/_generated.md   — pointer for the legacy docs/catalog/
                                  nav, in case any page references a connection
                                  that doesn't have a legacy md yet.

The legacy docs/catalog/ tree is kept as-is (73 pages); new connection
docs go under docs/connections/. Day 4 wizard UI will read
connections/registry.json directly, but a user who lands on the docs
site via roamcore.co.uk sees docs/connections/<id>.md.

Idempotent. Run as part of `.github/workflows/catalog.yml` on every
push to main.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("ERROR: PyYAML required. pip install pyyaml", file=sys.stderr)
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parents[1]
CONNECTIONS_DIR = REPO_ROOT / "connections"
REGISTRY_PATH = CONNECTIONS_DIR / "registry.json"
DOCS_OUT = REPO_ROOT / "docs" / "connections"

STATUS_BADGE = {
    "shipped": "✅ shipped",
    "beta": "🧪 beta",
    "wip": "🚧 in progress",
    "planned": "📋 planned",
    "deprecated": "⛔ deprecated",
}

TIER_LABEL = {
    "a": "A — Native, one-tap, fully tested",
    "b": "B — Recipe / howto",
    "c": "C — External link only",
}


def load_registry() -> dict:
    if not REGISTRY_PATH.is_file():
        print(f"ERROR: registry not found at {REGISTRY_PATH}", file=sys.stderr)
        print("       run scripts/audit_connections.py first.", file=sys.stderr)
        sys.exit(2)
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def discover_manifests() -> dict[str, dict]:
    """Load every connections/<id>/connection.yml."""
    if not CONNECTIONS_DIR.is_dir():
        return {}
    out = {}
    for p in sorted(CONNECTIONS_DIR.iterdir()):
        if not p.is_dir() or p.name.startswith("_") or p.name.startswith("."):
            continue
        mf = p / "connection.yml"
        if not mf.is_file():
            continue
        try:
            data = yaml.safe_load(mf.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            print(f"WARN: skipping {mf}: yaml error: {e}", file=sys.stderr)
            continue
        if isinstance(data, dict) and data.get("id") == p.name:
            out[p.name] = data
    return out


def render_connection_page(manifest: dict) -> str:
    """Render one connection's markdown page."""
    cid = manifest["id"]
    name = manifest["name"]
    tier = manifest["tier"]
    status = manifest["status"]
    badge = STATUS_BADGE.get(status, status)
    tier_label = TIER_LABEL.get(tier, tier)

    lines: list[str] = []
    lines.append(f"# {name}")
    lines.append("")
    lines.append(f"**ID:** `{cid}`  ")
    lines.append(f"**Category:** {manifest['category']}  ")
    lines.append(f"**Tier:** {tier_label}  ")
    lines.append(f"**Status:** {badge}  ")
    if manifest.get("version"):
        lines.append(f"**Version:** {manifest['version']}  ")
    if manifest.get("codeowners"):
        lines.append(f"**Owners:** {', '.join(manifest['codeowners'])}  ")
    lines.append("")

    if manifest.get("description"):
        lines.append(manifest["description"].strip())
        lines.append("")

    # Wizard config
    wizard = manifest.get("wizard", {})
    if wizard:
        lines.append("## Setup wizard")
        lines.append("")
        lines.append(f"- **Connection kind:** `{wizard.get('connection_kind', '?')}`")
        if wizard.get("one_tap"):
            lines.append("- **One-tap:** yes")
        if wizard.get("auto_discover"):
            lines.append("- **Auto-discovery:** yes (LAN scan)")
        if wizard.get("estimated_time"):
            lines.append(f"- **Estimated time:** {wizard['estimated_time']}")
        if wizard.get("requires_reboot"):
            lines.append("- ⚠️ Requires Home Assistant restart after install")
        if wizard.get("setup_notes"):
            lines.append("")
            lines.append(f"> {wizard['setup_notes']}")
        lines.append("")

    # Install
    install = manifest.get("install", {})
    if install:
        lines.append("## Install")
        lines.append("")
        lines.append(f"- **HA integration domain:** `{install.get('ha_integration_domain', '?')}`")
        lines.append(f"- **Config flow:** {'yes' if install.get('config_flow') else 'no'}")
        if install.get("hacs"):
            lines.append("- **HACS:** available")
        if install.get("ha_addon"):
            lines.append(f"- **HA add-on:** `{install['ha_addon']}`")
        if install.get("min_ha_version"):
            lines.append(f"- **Min HA version:** {install['min_ha_version']}")
        if install.get("python_requirements"):
            lines.append("- **Python requirements:**")
            for req in install["python_requirements"]:
                lines.append(f"  - `{req}`")
        if install.get("side_effects"):
            lines.append("- **Side effects:**")
            for eff in install["side_effects"]:
                lines.append(f"  - `{eff}`")
        lines.append("")

    # Dashboard tiles
    dashboard = manifest.get("dashboard", {})
    tiles = dashboard.get("tiles", [])
    if tiles:
        lines.append("## Dashboard tiles")
        lines.append("")
        lines.append("| Tile | Source | Unit |")
        lines.append("|------|--------|------|")
        for t in tiles:
            label = t.get("label", t.get("id", "?"))
            src = t.get("source", "?")
            unit = t.get("unit", "")
            lines.append(f"| {label} | `{src}` | {unit} |")
        lines.append("")

    # OpenClaw
    openclaw = manifest.get("openclaw", {})
    if openclaw.get("queries") or openclaw.get("summary_keys"):
        lines.append("## OpenClaw")
        lines.append("")
        if openclaw.get("summary_keys"):
            lines.append("**Summary keys:** " + ", ".join(f"`{k}`" for k in openclaw["summary_keys"]))
            lines.append("")
        if openclaw.get("queries"):
            lines.append("**Example queries:**")
            lines.append("")
            for q in openclaw["queries"]:
                lines.append(f'- _{q}_')
            lines.append("")

    # Tests
    tests = manifest.get("tests", [])
    if tests:
        lines.append("## Tests")
        lines.append("")
        for t in tests:
            lines.append(f"- `{t}`")
        lines.append("")

    # Tier requirements
    tier_req = manifest.get("tier_requirements", [])
    if tier_req:
        lines.append("## Tier requirements")
        lines.append("")
        for req in tier_req:
            lines.append(f"- [x] `{req}`")
        lines.append("")

    # Tier warnings
    warnings = manifest.get("tier_warnings", [])
    if warnings:
        lines.append("## Known limitations")
        lines.append("")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    # Links
    links = manifest.get("links", {})
    if any(links.values()):
        lines.append("## Links")
        lines.append("")
        for key in ("official", "docs", "repo", "buy"):
            for url in links.get(key, []):
                lines.append(f"- **{key.capitalize()}:** <{url}>")
        lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append(
        f"_Source: [`connections/{cid}/connection.yml`](https://github.com/roamcore/RoamCore/blob/main/connections/{cid}/connection.yml). "
        f"Auto-generated by `scripts/build_catalog.py`._"
    )
    lines.append("")

    return "\n".join(lines)


def render_index(registry: dict) -> str:
    """Render the master index page, grouped by tier then category."""
    lines: list[str] = []
    lines.append("# Connections catalog")
    lines.append("")
    lines.append(
        f"This page is auto-generated from "
        f"[`connections/*/connection.yml`](https://github.com/roamcore/RoamCore/tree/main/connections). "
        f"Do not edit by hand — edit the manifest and the catalog robot "
        f"regenerates this page on the next push to `main`."
    )
    lines.append("")
    lines.append(
        f"**{registry['count']} connections registered.** "
        f"Last regenerated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    )
    lines.append("")

    by_tier: dict[str, list[dict]] = {"a": [], "b": [], "c": []}
    for c in registry["connections"]:
        by_tier.setdefault(c["tier"], []).append(c)

    for tier_letter, label in [
        ("a", "Tier A — Native, one-tap, fully tested"),
        ("b", "Tier B — Recipe / howto"),
        ("c", "Tier C — External link only"),
    ]:
        conns = by_tier.get(tier_letter, [])
        if not conns:
            continue
        lines.append(f"## {label}")
        lines.append("")
        by_cat: dict[str, list[dict]] = {}
        for c in conns:
            by_cat.setdefault(c["category"], []).append(c)
        for cat in sorted(by_cat.keys()):
            lines.append(f"### {cat.replace('-', ' ').title()}")
            lines.append("")
            for c in by_cat[cat]:
                status_emoji = {
                    "shipped": "✅",
                    "beta": "🧪",
                    "wip": "🚧",
                    "planned": "📋",
                    "deprecated": "⛔",
                }.get(c["status"], "❓")
                one_tap = c.get("wizard", {}).get("one_tap", False)
                lines.append(
                    f"- {status_emoji} **[{c['name']}]({c['id']}.md)** "
                    f"(`{c['id']}`) — {c['status']}"
                    + (" — one-tap" if one_tap else "")
                )
            lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    registry = load_registry()
    manifests = discover_manifests()

    DOCS_OUT.mkdir(parents=True, exist_ok=True)

    # Render one page per registered connection (driven by registry)
    written = 0
    for conn in registry["connections"]:
        cid = conn["id"]
        if cid not in manifests:
            print(f"WARN: registry has '{cid}' but no manifest found on disk — skipping.", file=sys.stderr)
            continue
        page = render_connection_page(manifests[cid])
        (DOCS_OUT / f"{cid}.md").write_text(page, encoding="utf-8")
        written += 1

    # Render master index
    index = render_index(registry)
    (DOCS_OUT / "index.md").write_text(index, encoding="utf-8")

    # Remove stale per-connection pages whose id is no longer in the registry
    active_ids = {c["id"] for c in registry["connections"]}
    removed = 0
    for p in DOCS_OUT.glob("*.md"):
        if p.name in ("index.md", "audit-report.md"):
            continue
        cid = p.stem
        if cid not in active_ids:
            p.unlink()
            removed += 1

    if not args.quiet:
        print(f"  Wrote {written} connection pages + index.md under docs/connections/")
        if removed:
            print(f"  Removed {removed} stale pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
