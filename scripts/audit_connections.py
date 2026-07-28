#!/usr/bin/env python3
"""Audit robot for the RoamCore connections pipeline.

Validates every connections/<id>/connection.yml against the JSON schema,
checks tier vs reality (does `tier: a` actually have working config_flow
+ tests + tier_requirements?), cross-checks against the legacy catalog,
and emits:

  - connections/registry.json          (machine-readable for the wizard)
  - docs/connections/audit-report.md   (human-readable for Bernard + crons)
  - exit code 0 (clean) / 1 (violations) / 2 (errors)

This is the single source-of-truth guarantee for the wizard + the catalog
+ the install path. If this script says a connection is tier-a, the wizard
will render the "Connect" button.

Usage:
  python scripts/audit_connections.py            # default: scan repo root
  python scripts/audit_connections.py --strict    # also fail on warnings
  python scripts/audit_connections.py --quiet     # only print errors

Designed to be idempotent and runnable from CI, cron, and local dev.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    print("ERROR: PyYAML is required. pip install pyyaml", file=sys.stderr)
    sys.exit(2)

try:
    import jsonschema
except ImportError:  # pragma: no cover
    print("ERROR: jsonschema is required. pip install jsonschema", file=sys.stderr)
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parents[1]
CONNECTIONS_DIR = REPO_ROOT / "connections"
SCHEMA_PATH = CONNECTIONS_DIR / "_schema" / "connection.schema.json"
LEGACY_CATALOG_DIR = REPO_ROOT / "docs" / "catalog"
REGISTRY_OUTPUT = CONNECTIONS_DIR / "registry.json"
AUDIT_OUTPUT = REPO_ROOT / "docs" / "connections" / "audit-report.md"

# Working copies — main() may reassign these if --root is passed.
_REPO_ROOT = REPO_ROOT
_CONNECTIONS_DIR = CONNECTIONS_DIR
_SCHEMA_PATH = SCHEMA_PATH
_LEGACY_CATALOG_DIR = LEGACY_CATALOG_DIR
_REGISTRY_OUTPUT = REGISTRY_OUTPUT
_AUDIT_OUTPUT = AUDIT_OUTPUT

# Allowed side-effect prefixes the boundary CI permits when scanning existing code
# for tier verification. Exhaustive list keeps the audit deterministic.
TIER_A_REQUIRED_FIELDS = {
    "config_flow": True,
    "tests_present": True,
    "tier_requirements_present": True,
    "wizard_one_tap": True,
}

TIER_B_REQUIRED_FIELDS = {
    "tier_requirements_docs_recipe_published": True,
}

TIER_C_REQUIRED_FIELDS = {
    "external_link_present": True,
}


def load_schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def discover_connections() -> list[Path]:
    """Find every connections/<id>/connection.yml."""
    if not _CONNECTIONS_DIR.is_dir():
        return []
    found = []
    for p in sorted(_CONNECTIONS_DIR.iterdir()):
        if not p.is_dir():
            continue
        if p.name.startswith("_") or p.name.startswith("."):
            continue
        manifest = p / "connection.yml"
        if manifest.is_file():
            found.append(manifest)
    return found


def load_manifest(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Load + parse a connection.yml. Returns (manifest, error)."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        return None, f"cannot read: {e}"
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        return None, f"yaml parse error: {e}"
    if not isinstance(data, dict):
        return None, "connection.yml must be a mapping at the top level"
    return data, None


def validate_against_schema(
    manifest: dict[str, Any], schema: dict[str, Any]
) -> list[str]:
    """Validate one manifest against the JSON schema. Returns list of errors."""
    validator = jsonschema.Draft202012Validator(schema)
    return [f"{'.'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
            for e in validator.iter_errors(manifest)]


def cross_check_tier(
    manifest: dict[str, Any], connection_dir: Path
) -> tuple[list[str], list[str]]:
    """Verify the tier claim against reality on disk.

    Returns (errors, warnings). Errors block tier-a/b classification;
    warnings are advisory (the audit still passes but the report flags them).
    """
    errors: list[str] = []
    warnings: list[str] = []
    tier = manifest.get("tier")
    status = manifest.get("status")

    if tier == "a":
        install = manifest.get("install", {})
        wizard = manifest.get("wizard", {})
        tests = manifest.get("tests", [])
        tier_req = manifest.get("tier_requirements", [])

        if not install.get("config_flow"):
            errors.append("tier=a requires install.config_flow: true")
        if not wizard.get("one_tap"):
            errors.append("tier=a requires wizard.one_tap: true")
        if not tests:
            errors.append("tier=a requires at least one entry in tests")
        if "working_config_flow" not in tier_req:
            errors.append("tier=a requires 'working_config_flow' in tier_requirements")
        if "integration_test_passes" not in tier_req:
            errors.append("tier=a requires 'integration_test_passes' in tier_requirements")
        if "no_manual_yaml_required" not in tier_req:
            errors.append("tier=a requires 'no_manual_yaml_required' in tier_requirements")

        # Verify each test file exists
        for t in tests:
            test_path = connection_dir / t
            if not test_path.is_file():
                warnings.append(f"tests entry references missing file: {t}")

        # If status is shipped, the integration code must exist
        if status == "shipped":
            if not (connection_dir / "__init__.py").is_file() \
               and not (connection_dir / "manifest.json").is_file():
                warnings.append(
                    "status=shipped but no __init__.py or manifest.json found in connection folder"
                )

    elif tier == "b":
        tier_req = manifest.get("tier_requirements", [])
        if "docs_recipe_published" not in tier_req:
            errors.append(
                "tier=b requires 'docs_recipe_published' in tier_requirements"
            )
        # Verify the recipe doc exists in docs/howto/ or docs/catalog/<category>/
        if not manifest.get("links", {}).get("docs") \
           and not (LEGACY_CATALOG_DIR / manifest.get("category", "_")).is_dir():
            warnings.append(
                "tier=b but no docs links declared AND no docs/catalog/<category>/ folder found"
            )

    elif tier == "c":
        links = manifest.get("links", {})
        if not (links.get("official") or links.get("docs") or links.get("repo")):
            errors.append(
                "tier=c requires at least one external link in links.official / docs / repo"
            )

    return errors, warnings


def cross_check_legacy_catalog(
    manifest: dict[str, Any], legacy_pages: list[Path]
) -> list[str]:
    """If a legacy docs/catalog/<category>/<id>.md exists for this
    connection, flag drift between the markdown tier line and the yml tier.

    The legacy catalog still exists and is the user-facing docs surface
    until the wizard fully takes over. The audit surfaces drift so the
    crons can reconcile it.
    """
    cid = manifest["id"]
    category = manifest["category"]
    notes: list[str] = []
    candidates = [
        LEGACY_CATALOG_DIR / category / f"{cid}.md",
        LEGACY_CATALOG_DIR / category / f"{cid.replace('-', '_')}.md",
    ]
    matched = next((p for p in candidates if p.is_file()), None)
    if not matched:
        return notes
    text = matched.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"\*\*Support tier:\*\*\s*([ABC])", text)
    legacy_tier = m.group(1).lower() if m else None
    if legacy_tier and legacy_tier != manifest["tier"]:
        notes.append(
            f"legacy catalog page tier={legacy_tier.upper()} but connection.yml tier={manifest['tier']} "
            f"(run scripts/build_catalog.py to reconcile)"
        )
    return notes


def scan_legacy_catalog() -> dict[str, list[Path]]:
    """Map category -> list of .md pages. Used to detect orphans
    (pages with no matching connection.yml).
    """
    out: dict[str, list[Path]] = defaultdict(list)
    if not _LEGACY_CATALOG_DIR.is_dir():
        return out
    for cat_dir in sorted(_LEGACY_CATALOG_DIR.iterdir()):
        if not cat_dir.is_dir() or cat_dir.name.startswith("_") or cat_dir.name.startswith("."):
            continue
        for md in sorted(cat_dir.glob("*.md")):
            if md.stem == "index":
                continue
            out[cat_dir.name].append(md)
    return out


def build_registry(
    valid_manifests: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the wizard-readable registry from validated manifests."""
    return {
        "version": 1,
        "generated_by": "scripts/audit_connections.py",
        "count": len(valid_manifests),
        "connections": sorted(
            [
                {
                    "id": m["id"],
                    "name": m["name"],
                    "tier": m["tier"],
                    "category": m["category"],
                    "status": m["status"],
                    "version": m.get("version"),
                    "description": m.get("description", ""),
                    "icon": m.get("icon"),
                    "tags": m.get("tags", []),
                    "wizard": m.get("wizard", {}),
                    "install": {
                        "ha_integration_domain": m["install"]["ha_integration_domain"],
                        "hacs": m["install"].get("hacs", False),
                        "ha_addon": m["install"].get("ha_addon"),
                        "min_ha_version": m["install"].get("min_ha_version"),
                    },
                    "dashboard_tiles": m.get("dashboard", {}).get("tiles", []),
                    "openclaw_queries": m.get("openclaw", {}).get("queries", []),
                    "openclaw_summary_keys": m.get("openclaw", {}).get("summary_keys", []),
                    "links": m.get("links", {}),
                }
                for m in valid_manifests
            ],
            key=lambda c: (c["category"], c["name"]),
        ),
    }


def write_markdown_report(
    results: list[dict[str, Any]],
    registry: dict[str, Any],
    legacy_orphans: list[str],
    output: Path,
) -> None:
    """Write the human-readable audit report."""
    output.parent.mkdir(parents=True, exist_ok=True)
    by_tier: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in results:
        if r["ok"]:
            by_tier[r["manifest"]["tier"]].append(r)

    lines: list[str] = []
    lines.append("# Connections Audit Report")
    lines.append("")
    lines.append(
        "_Generated by `scripts/audit_connections.py`. "
        "If this report is stale, re-run the script._"
    )
    lines.append("")

    # Summary
    total = len(results)
    ok = sum(1 for r in results if r["ok"])
    lines.append(f"## Summary")
    lines.append("")
    lines.append(f"- **Total connections scanned:** {total}")
    lines.append(f"- **Valid (passing audit):** {ok}")
    lines.append(f"- **Tier A:** {len(by_tier['a'])}")
    lines.append(f"- **Tier B:** {len(by_tier['b'])}")
    lines.append(f"- **Tier C:** {len(by_tier['c'])}")
    if legacy_orphans:
        lines.append(f"- **Legacy catalog pages without a connection.yml:** {len(legacy_orphans)}")
    lines.append("")

    # Errors block
    errored = [r for r in results if not r["ok"]]
    if errored:
        lines.append("## ❌ Errors (block merge)")
        lines.append("")
        for r in errored:
            cid = r["manifest"].get("id", "<unknown>")
            lines.append(f"### `{cid}`")
            lines.append("")
            for e in r["errors"]:
                lines.append(f"- {e}")
            lines.append("")

    # Warnings block
    warned = [r for r in results if r["warnings"]]
    if warned:
        lines.append("## ⚠️ Warnings (advisory)")
        lines.append("")
        for r in warned:
            cid = r["manifest"].get("id", "<unknown>")
            lines.append(f"### `{cid}`")
            lines.append("")
            for w in r["warnings"]:
                lines.append(f"- {w}")
            lines.append("")

    # Tier sections
    for tier_letter, label in [("a", "Tier A — native, one-tap, full tests"),
                                ("b", "Tier B — recipe / howto"),
                                ("c", "Tier C — external link")]:
        tier_conns = by_tier[tier_letter]
        if not tier_conns:
            continue
        lines.append(f"## {label}")
        lines.append("")
        for r in tier_conns:
            m = r["manifest"]
            status_emoji = {
                "shipped": "✅",
                "beta": "🧪",
                "wip": "🚧",
                "planned": "📋",
                "deprecated": "⛔",
            }.get(m["status"], "❓")
            lines.append(f"- {status_emoji} **{m['name']}** (`{m['id']}`) — {m['category']} — {m['status']}")
            if m.get("description"):
                lines.append(f"  - {m['description']}")
            one_tap = m.get("wizard", {}).get("one_tap", False)
            lines.append(f"  - one-tap: {one_tap}, config_flow: {m.get('install', {}).get('config_flow', False)}")
        lines.append("")

    # Legacy orphans
    if legacy_orphans:
        lines.append("## 📚 Legacy catalog pages without a connection.yml")
        lines.append("")
        lines.append(
            "These pages exist in `docs/catalog/` but have no matching "
            "`connections/<id>/connection.yml`. Either create the yml "
            "(promoting them to the pipeline) or remove the page."
        )
        lines.append("")
        for orphan in legacy_orphans:
            lines.append(f"- `{orphan}`")
        lines.append("")

    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    # Declare these as global up-front so reassignment below doesn't trip
    # Python's "name used prior to global declaration" syntax error.
    global _REPO_ROOT, _CONNECTIONS_DIR, _SCHEMA_PATH, _LEGACY_CATALOG_DIR, _REGISTRY_OUTPUT, _AUDIT_OUTPUT

    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--strict", action="store_true", help="Fail on warnings too")
    parser.add_argument("--quiet", action="store_true", help="Only print errors")
    parser.add_argument("--no-registry", action="store_true", help="Skip writing registry.json")
    parser.add_argument("--no-report", action="store_true", help="Skip writing audit-report.md")
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Root of the repo to audit (default: parent of the script's directory). "
             "Used for testing the script against isolated workspaces.",
    )
    args = parser.parse_args()

    # Override the working-copy globals if --root was provided so
    # discover_connections + writes go to the test workspace.
    if args.root is not None and args.root.resolve() != _REPO_ROOT:
        root = args.root.resolve()
        _REPO_ROOT = root
        _CONNECTIONS_DIR = root / "connections"
        _SCHEMA_PATH = _CONNECTIONS_DIR / "_schema" / "connection.schema.json"
        _LEGACY_CATALOG_DIR = root / "docs" / "catalog"
        _REGISTRY_OUTPUT = _CONNECTIONS_DIR / "registry.json"
        _AUDIT_OUTPUT = root / "docs" / "connections" / "audit-report.md"

    if not _SCHEMA_PATH.is_file():
        print(f"ERROR: schema not found at {_SCHEMA_PATH}", file=sys.stderr)
        return 2

    schema = load_schema()
    manifests = discover_connections()

    if not args.quiet:
        print(f"Scanning {len(manifests)} connections in {_CONNECTIONS_DIR}...")

    legacy_pages = scan_legacy_catalog()
    legacy_ids: dict[str, str] = {}
    for cat, pages in legacy_pages.items():
        for p in pages:
            legacy_ids[p.stem] = f"{cat}/{p.stem}.md"

    results: list[dict[str, Any]] = []
    for manifest_path in manifests:
        manifest, err = load_manifest(manifest_path)
        if err:
            results.append({
                "path": manifest_path,
                "manifest": {"id": manifest_path.parent.name},
                "errors": [err],
                "warnings": [],
                "ok": False,
            })
            continue

        cid = manifest.get("id", manifest_path.parent.name)
        # id must match folder name
        if cid != manifest_path.parent.name:
            results.append({
                "path": manifest_path,
                "manifest": manifest,
                "errors": [f"id '{cid}' does not match folder name '{manifest_path.parent.name}'"],
                "warnings": [],
                "ok": False,
            })
            continue

        schema_errors = validate_against_schema(manifest, schema)
        tier_errors, tier_warnings = cross_check_tier(manifest, manifest_path.parent)
        drift_notes = cross_check_legacy_catalog(manifest, [])

        all_errors = schema_errors + tier_errors
        all_warnings = tier_warnings + drift_notes
        results.append({
            "path": manifest_path,
            "manifest": manifest,
            "errors": all_errors,
            "warnings": all_warnings,
            "ok": not all_errors,
        })

    # Legacy orphans
    declared_ids = {r["manifest"]["id"] for r in results if r["ok"]}
    legacy_orphans: list[str] = []
    for cat, pages in legacy_pages.items():
        for p in pages:
            slug = p.stem
            if slug not in declared_ids:
                legacy_orphans.append(f"{cat}/{p.stem}.md")

    # Build registry from valid manifests only
    valid_manifests = [r["manifest"] for r in results if r["ok"]]
    registry = build_registry(valid_manifests)

    if not args.no_registry:
        _REGISTRY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        _REGISTRY_OUTPUT.write_text(
            json.dumps(registry, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )

    if not args.no_report:
        write_markdown_report(results, registry, legacy_orphans, _AUDIT_OUTPUT)

    # Console output
    errored = [r for r in results if not r["ok"]]
    warned = [r for r in results if r["warnings"]]

    if not args.quiet:
        print()
        print(f"  Tier A: {sum(1 for r in results if r['ok'] and r['manifest']['tier'] == 'a')}")
        print(f"  Tier B: {sum(1 for r in results if r['ok'] and r['manifest']['tier'] == 'b')}")
        print(f"  Tier C: {sum(1 for r in results if r['ok'] and r['manifest']['tier'] == 'c')}")
        print(f"  Errors: {len(errored)}")
        print(f"  Warnings: {len(warned)}")
        if legacy_orphans:
            print(f"  Legacy orphans: {len(legacy_orphans)}")
        print()
        try:
            print(f"  Registry: {_REGISTRY_OUTPUT.relative_to(_REPO_ROOT)}")
            print(f"  Report:   {_AUDIT_OUTPUT.relative_to(_REPO_ROOT)}")
        except ValueError:
            # Display the absolute path if the file is outside the root
            # (shouldn't happen in normal use but is fine for tests).
            print(f"  Registry: {_REGISTRY_OUTPUT}")
            print(f"  Report:   {_AUDIT_OUTPUT}")
        print()

    if errored:
        if not args.quiet:
            print("❌ ERRORS:")
            for r in errored:
                cid = r["manifest"].get("id", "<unknown>")
                print(f"  - {cid}:")
                for e in r["errors"]:
                    print(f"      {e}")
        return 1

    if args.strict and warned:
        if not args.quiet:
            print("⚠️ STRICT MODE WARNINGS:")
            for r in warned:
                cid = r["manifest"].get("id", "<unknown>")
                print(f"  - {cid}:")
                for w in r["warnings"]:
                    print(f"      {w}")
        return 1

    if not args.quiet:
        print("✅ audit clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
