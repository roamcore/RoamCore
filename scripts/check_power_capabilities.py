#!/usr/bin/env python3
"""Smoke check for the RoamCore capability-driven Power page manifest.

Validates that power-capabilities.json parses, that every tile has the
required {id, title, required[], optional[]} shape, and warns when a
required prefix has no matching entity in the backend. Wired into
scripts/check.sh --core-only. Exit 0 on success, 1 on hard failure.
"""
from __future__ import annotations
import json, pathlib, re, sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / "homeassistant" / "www" / "roamcore" / "power-capabilities.json"


def _scan_files() -> list[pathlib.Path]:
    paths: list[pathlib.Path] = []
    pkgs = REPO_ROOT / "homeassistant" / "packages"
    if pkgs.is_dir():
        paths.extend(sorted(pkgs.rglob("*.yaml")))
        paths.extend(sorted(pkgs.rglob("*.yml")))
    addon = REPO_ROOT / "homeassistant" / "addons" / "roamcore-victron-auto"
    if addon.is_dir():
        paths.extend(sorted(addon.rglob("*.py")))
    return paths


def _prefix_patterns(prefix: str) -> list[re.Pattern[str]]:
    forms = {prefix}
    if "." in prefix:
        forms.add(prefix.partition(".")[2])
    return [re.compile(rf"\b{re.escape(f)}\b") for f in forms]


def _validate_manifest(manifest: dict) -> list[str]:
    errs: list[str] = []
    if not isinstance(manifest, dict):
        return [f"manifest must be a JSON object, got {type(manifest).__name__}"]
    if not isinstance(manifest.get("version"), int):
        errs.append("manifest.version must be an integer")
    tiles = manifest.get("tiles")
    if not isinstance(tiles, list) or not tiles:
        errs.append("manifest.tiles must be a non-empty array")
        return errs
    seen: set[str] = set()
    for i, tile in enumerate(tiles):
        if not isinstance(tile, dict):
            errs.append(f"tiles[{i}] must be an object"); continue
        tid = tile.get("id"); title = tile.get("title")
        req = tile.get("required"); opt = tile.get("optional")
        if not isinstance(tid, str) or not tid:
            errs.append(f"tiles[{i}].id must be a non-empty string")
        elif tid in seen:
            errs.append(f"tiles[{i}].id duplicate: {tid!r}")
        else:
            seen.add(tid)
        if not isinstance(title, str) or not title:
            errs.append(f"tiles[{i}].title must be a non-empty string")
        if not isinstance(req, list) or not req:
            errs.append(f"tiles[{i}].required must be a non-empty array of strings")
        else:
            for j, p in enumerate(req):
                if not isinstance(p, str) or not p:
                    errs.append(f"tiles[{i}].required[{j}] must be a string")
        if opt is not None:
            if not isinstance(opt, list):
                errs.append(f"tiles[{i}].optional must be an array (or omitted)")
            else:
                for j, p in enumerate(opt):
                    if not isinstance(p, str) or not p:
                        errs.append(f"tiles[{i}].optional[{j}] must be a string")
    return errs


def main() -> int:
    if not MANIFEST.is_file():
        print(f"FAIL: manifest not found at {MANIFEST}", file=sys.stderr); return 1
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"FAIL: {MANIFEST.name} is not valid JSON: {e}", file=sys.stderr); return 1

    errs = _validate_manifest(manifest)
    if errs:
        print("FAIL: capability manifest schema errors:", file=sys.stderr)
        for e in errs: print(f"  - {e}", file=sys.stderr)
        return 1

    files = _scan_files()
    if not files:
        print(f"WARN: no YAML/Python source files found under {REPO_ROOT}")
    tiles = manifest["tiles"]
    print(f"OK: capability manifest parsed ({len(tiles)} tiles, "
          f"{sum(len(t.get('required', [])) for t in tiles)} required, "
          f"{sum(len(t.get('optional', [])) for t in tiles)} optional refs)")

    files_text = {p: p.read_text(encoding="utf-8", errors="ignore") for p in files if p.is_file()}

    missing: list[str] = []
    for tile in tiles:
        for prefix in tile.get("required", []) or []:
            patterns = _prefix_patterns(prefix)
            hits = [p for p, txt in files_text.items() if any(rx.search(txt) for rx in patterns)]
            if not hits:
                missing.append(f"{tile['id']}: required prefix {prefix!r} has zero backend matches")
            else:
                rels = ", ".join(h.relative_to(REPO_ROOT).as_posix() for h in hits[:2])
                if len(hits) > 2: rels += f", …(+{len(hits) - 2} more)"
                print(f"  - {tile['id']:<10} required {prefix:<46} -> {rels}")

    if missing:
        print()
        print("WARN: required prefixes with zero backend matches:", file=sys.stderr)
        for m in missing: print(f"  - {m}", file=sys.stderr)

    print("\n✓ PASS — Power: capability-driven page smoke")
    return 0


if __name__ == "__main__":
    sys.exit(main())