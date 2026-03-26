#!/usr/bin/env python3
"""Check for drift between Victron vt_* entities published by roamcore-victron-auto
and the documented list in docs/reference/victron-rc-mapping-plan.md.

Goal: keep the mapping plan as the human-readable source of truth, and fail fast
if code changes add/remove vt_* keys without updating docs.

Usage:
  python3 tools/check_victron_vt_mapping_drift.py

Exit codes:
  0: OK
  1: Drift detected
  2: Unexpected parse error
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
AUTO_MAIN = REPO / "homeassistant" / "addons" / "roamcore-victron-auto" / "src" / "main.py"
PLAN = REPO / "docs" / "reference" / "victron-rc-mapping-plan.md"


def _extract_vt_from_main_py(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")

    # We look for the `_path_to_vt: dict[...] = { ... }` dict literal and then
    # AST-parse just that substring.
    m = re.search(r"\n\s*self\._path_to_vt\s*:[^=]*=\s*(\{.*?\n\s*\})\s*\n\s*\n", text, re.S)
    if not m:
        raise ValueError("Could not locate self._path_to_vt dict literal")

    dict_src = m.group(1)
    node = ast.parse(dict_src, mode="eval")
    if not isinstance(node.body, ast.Dict):
        raise ValueError("_path_to_vt is not a dict literal")

    out: set[str] = set()
    for v in node.body.values:
        if not isinstance(v, ast.Dict):
            continue
        for k_node, val_node in zip(v.keys, v.values):
            if isinstance(k_node, ast.Constant) and k_node.value == "vt_key":
                if isinstance(val_node, ast.Constant) and isinstance(val_node.value, str):
                    out.add(val_node.value)
    return out


def _extract_vt_from_mapping_plan(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")

    # Extract the "Current vt_* signals (MVP)" section bullets.
    m = re.search(
        r"## Current vt_\* signals \(MVP\)(?P<section>.*?)(?:\n## |\Z)",
        text,
        re.S,
    )
    if not m:
        raise ValueError("Could not locate 'Current vt_* signals (MVP)' section")

    section = m.group("section")

    # Bullets look like: - `sensor.vt_battery_voltage_v`
    vt_keys: set[str] = set()
    for mm in re.finditer(r"-\s+`(?:sensor|binary_sensor)\.(vt_[a-zA-Z0-9_]+)`", section):
        vt_keys.add(mm.group(1))

    if not vt_keys:
        raise ValueError("Found section but no vt_* bullets")

    return vt_keys


def main() -> int:
    try:
        vt_code = _extract_vt_from_main_py(AUTO_MAIN)
        vt_plan = _extract_vt_from_mapping_plan(PLAN)
    except Exception as e:
        print(f"ERROR: {e}")
        return 2

    missing_in_plan = sorted(vt_code - vt_plan)
    missing_in_code = sorted(vt_plan - vt_code)

    if missing_in_plan or missing_in_code:
        print("Victron vt_* mapping drift detected:\n")
        if missing_in_plan:
            print("  Present in code but missing in mapping plan:")
            for k in missing_in_plan:
                print(f"    - {k}")
            print("")
        if missing_in_code:
            print("  Present in mapping plan but missing in code:")
            for k in missing_in_code:
                print(f"    - {k}")
            print("")
        print("Fix: update docs/reference/victron-rc-mapping-plan.md and/or main.py so they match.")
        return 1

    print(f"OK: vt_* list matches mapping plan ({len(vt_code)} keys).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
