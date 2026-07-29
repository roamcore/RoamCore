#!/usr/bin/env python3
"""RoamCore Labs — bundle the active setup as a local tar.gz.

Local-only. Stdlib-only. No HTTP. No third-party imports.

This is the headless CLI mirror of the
``roamcore.labs_export_setup`` service. The custom-component service
and this CLI share ``homeassistant/tools/labs/common.py`` so the
bundle schema is identical.

Usage:
  python3 homeassistant/tools/labs/export_setup.py --help
  python3 homeassistant/tools/labs/export_setup.py --dry-run
  python3 homeassistant/tools/labs/export_setup.py --target /tmp/out.tar.gz
  python3 homeassistant/tools/labs/export_setup.py --target /tmp/out.tar.gz --dry-run

Exit code: 0 on success, 2 on argument error, 3 on a BundleError.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running as a standalone script: insert the labs package's parent
# (homeassistant/tools) onto sys.path so `import labs.common` resolves.
_HERE = Path(__file__).resolve().parent
_TOOLS = _HERE.parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from labs.common import (  # noqa: E402
    DEFAULT_DASHBOARD_FILE,
    DEFAULT_PACKAGES_DIR,
    BundleError,
    build_export,
    _die,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="roamcore_labs_export_setup",
        description=(
            "Bundle the active RoamCore setup as a local tar.gz. "
            "Privacy-by-default: no remote upload, no telemetry, no third-party HTTP. "
            "The output is a local file the owner shares by whatever channel they trust."
        ),
    )
    parser.add_argument(
        "--target",
        dest="target_path",
        default=None,
        help=(
            "Output path for the bundle (must end in .tar.gz). "
            "Default: /config/.storage/roamcore_labs/exports/<UTC-timestamp>/roamcore_setup.tar.gz"
        ),
    )
    parser.add_argument(
        "--dashboard",
        dest="dashboard_file",
        default=DEFAULT_DASHBOARD_FILE,
        help=(
            "Path to the dashboard YAML to include. "
            f"Default: {DEFAULT_DASHBOARD_FILE}"
        ),
    )
    parser.add_argument(
        "--packages",
        dest="packages_dir",
        default=DEFAULT_PACKAGES_DIR,
        help=(
            "Path to the packages dir to include. "
            f"Default: {DEFAULT_PACKAGES_DIR}"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve the output path + manifest but do not write the bundle.",
    )
    args = parser.parse_args()

    try:
        result = build_export(
            target_path=args.target_path,
            dashboard_file=args.dashboard_file,
            packages_dir=args.packages_dir,
            dry_run=args.dry_run,
        )
    except BundleError as exc:
        _die(f"bundle failed: {exc}", code=3)
    except OSError as exc:
        _die(f"filesystem error: {exc}", code=3)

    print(json.dumps({
        "ok": True,
        "dry_run": result["dry_run"],
        "path": result["path"],
        "manifest": result["manifest"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
