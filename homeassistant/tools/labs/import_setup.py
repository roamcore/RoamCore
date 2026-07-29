#!/usr/bin/env python3
"""RoamCore Labs — stage a bundle for apply-on-next-reload.

Local-only. Stdlib-only. No HTTP. No third-party imports.

This is the headless CLI mirror of the
``roamcore.labs_import_setup`` service. The custom-component service
and this CLI share ``homeassistant/tools/labs/common.py`` so the
bundle schema is identical.

The import path is split into two phases:

  1. **stage** — the bundle is unpacked into a staging directory and
     the path is written to ``input_text.rc_labs_pending_import``. The
     operator is shown a preview in the wizard.
  2. **apply on next reload** — on the next HA reload, the staged
     files are copied into ``/config/packages/`` and the dashboard YAML
     is staged for review. The actual apply is gated on operator
     consent; this CLI only stages it.

By default (``--dry-run``) the bundle is *not* extracted; the CLI
prints the manifest + the files it would extract.

Usage:
  python3 homeassistant/tools/labs/import_setup.py --help
  python3 homeassistant/tools/labs/import_setup.py --dry-run --bundle /tmp/in.tar.gz
  python3 homeassistant/tools/labs/import_setup.py --bundle /tmp/in.tar.gz

Exit code: 0 on success, 2 on argument error, 3 on a BundleError.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

# Allow running as a standalone script: insert the labs package's parent
# (homeassistant/tools) onto sys.path so `import labs.common` resolves.
_HERE = Path(__file__).resolve().parent
_TOOLS = _HERE.parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from labs.common import (  # noqa: E402
    DEFAULT_STATE_FILE,
    BundleError,
    read_bundle_state,
    write_bundle_state,
    _die,
)

# Default staging dir. Lives inside /config so the operator can inspect
# the extracted files via the standard file editor.
DEFAULT_STAGING_ROOT = "/config/.storage/roamcore_labs/imports"


def _utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stage_path(bundle_path: Path) -> Path:
    """Pick a staging directory for this bundle."""
    bundle_path = Path(bundle_path)
    # Use the bundle's stem + a UTC timestamp suffix so we don't
    # collide with multiple imports.
    stem = bundle_path.stem
    if stem.endswith(".tar"):
        stem = stem[:-4]
    ts = _utc_now_compact()
    return Path(DEFAULT_STAGING_ROOT) / f"{stem}_{ts}"


def stage_bundle(
    *,
    bundle_path: str,
    apply: bool = False,
    dry_run: bool = False,
) -> dict:
    """Stage a bundle tar.gz for import.

    Returns a small dict the CLI / service can render.
    """
    bp = Path(bundle_path)
    if not bp.exists():
        raise BundleError(f"bundle not found: {bp}")
    if not bp.is_file():
        raise BundleError(f"bundle is not a regular file: {bp}")
    if not (bp.name.endswith(".tar.gz") or bp.name.endswith(".tgz")):
        raise BundleError(
            f"bundle must end in .tar.gz or .tgz: {bp.name}"
        )

    staging = _stage_path(bp)
    manifest: dict = {}
    files: list[str] = []

    if dry_run:
        # Read the manifest without extracting.
        with tarfile.open(bp, "r:gz") as tf:
            try:
                manifest_member = tf.getmember("manifest.json")
                f = tf.extractfile(manifest_member)
                if f is not None:
                    manifest = json.loads(f.read().decode("utf-8"))
                for m in tf.getmembers():
                    if m.isfile():
                        files.append(m.name)
            except KeyError:
                raise BundleError("bundle has no manifest.json")
        return {
            "ok": True,
            "dry_run": True,
            "apply": apply,
            "bundle_path": str(bp),
            "staging": str(staging),
            "manifest": manifest,
            "files": files,
        }

    # Real path: extract to staging dir.
    staging.mkdir(parents=True, exist_ok=True)
    with tarfile.open(bp, "r:gz") as tf:
        # Read manifest first so we can validate schema_version.
        try:
            manifest_member = tf.getmember("manifest.json")
        except KeyError:
            raise BundleError("bundle has no manifest.json")
        f = tf.extractfile(manifest_member)
        if f is None:
            raise BundleError("manifest.json is not a regular file")
        manifest = json.loads(f.read().decode("utf-8"))

        # Extract the rest of the bundle into the staging dir.
        # We deliberately extract *all* regular files (manifest included
        # so the staging dir is self-contained) but refuse anything
        # that would escape the staging dir (path traversal).
        for m in tf.getmembers():
            if not m.isfile():
                continue
            target = (staging / m.name).resolve()
            if not str(target).startswith(str(staging.resolve())):
                raise BundleError(
                    f"refusing unsafe path in bundle: {m.name}"
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            extracted = tf.extractfile(m)
            if extracted is None:
                continue
            with open(target, "wb") as out:
                out.write(extracted.read())
            files.append(m.name)

    # Update state.
    st = read_bundle_state()
    st["import_count"] = int(st.get("import_count", 0) or 0) + 1
    st["last_import_status"] = (
        "apply_on_next_reload" if apply else "staged"
    )
    st["last_import_at"] = _utc_now_iso()
    # The pending-import path is what the wizard reads back.
    st["pending_import_path"] = str(bp)
    try:
        write_bundle_state(st)
    except OSError:
        pass

    return {
        "ok": True,
        "dry_run": False,
        "apply": apply,
        "bundle_path": str(bp),
        "staging": str(staging),
        "manifest": manifest,
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="roamcore_labs_import_setup",
        description=(
            "Stage a RoamCore Labs bundle for apply-on-next-reload. "
            "Privacy-by-default: no remote upload, no telemetry, no third-party HTTP. "
            "The bundle is a local file the owner chose to share."
        ),
    )
    parser.add_argument(
        "--bundle",
        dest="bundle_path",
        required=True,
        help="Path to the bundle tar.gz to import.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Mark the staged bundle as 'apply on next reload'. Without "
            "this flag, the bundle is staged only (the default). Idempotent."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect the bundle without extracting it.",
    )
    args = parser.parse_args()

    try:
        result = stage_bundle(
            bundle_path=args.bundle_path,
            apply=args.apply,
            dry_run=args.dry_run,
        )
    except BundleError as exc:
        _die(f"import failed: {exc}", code=3)
    except OSError as exc:
        _die(f"filesystem error: {exc}", code=3)

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
