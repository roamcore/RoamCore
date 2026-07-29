"""Shared bundle helpers for the RoamCore Labs subsystem.

Local-only. Stdlib-only. No HTTP. No third-party imports.

The bundle schema is a flat tar.gz with three top-level entries:

  manifest.json       — schema + version + creator + created_at
  dashboard.yaml      — the active dashboard YAML (best-effort)
  packages/...        — the selected packages (a snapshot of the
                         homeassistant/packages/ tree at bundle time)

The bundle is owner-controlled: the operator picks where to write it
(default: /config/.storage/roamcore_labs/exports/<UTC-timestamp>/roamcore_setup.tar.gz)
and picks how to share it out-of-band. RoamCore never phones home.
"""

from __future__ import annotations

import json
import os
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional


# Default export root. Lives inside HA's config dir so the operator can
# find it via the standard file editor / SMB share path.
DEFAULT_EXPORT_ROOT = "/config/.storage/roamcore_labs/exports"

# State file the smoke / dashboard reads from. Bumped by the services
# on each successful export / import (the CLI is a mirror; the services
# are the source of truth).
DEFAULT_STATE_FILE = "/config/.storage/roamcore_labs/state.json"

# Bundle schema version. Bump on breaking changes.
BUNDLE_SCHEMA_VERSION = 1

# Default packages sub-tree to include in the bundle. The operator can
# override via the --packages CLI flag / the service target_path arg.
DEFAULT_PACKAGES_DIR = "/config/packages"

# Default dashboard file. The operator can override the same way.
DEFAULT_DASHBOARD_FILE = "/config/lovelace/roamcore-dashboard.yaml"


class BundleError(Exception):
    """Raised on any error path. All CLI helpers exit non-zero on this."""


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in ISO 8601 form."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_now_compact() -> str:
    """Return the current UTC timestamp in compact form (for path segments)."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_export_path(target_path: Optional[str] = None) -> Path:
    """Resolve the export path.

    If ``target_path`` is given, use it as-is (must end in .tar.gz).
    Otherwise, build a default under DEFAULT_EXPORT_ROOT with a UTC
    timestamp prefix.
    """
    if target_path:
        p = Path(target_path)
        if p.suffix != ".gz" or p.name.endswith(".tar"):
            # Best-effort: if the user gave a directory, append a name.
            if p.is_dir() or str(p).endswith("/"):
                ts = _utc_now_compact()
                p = p / f"roamcore_setup_{ts}.tar.gz"
        return p

    ts = _utc_now_compact()
    return Path(DEFAULT_EXPORT_ROOT) / ts / "roamcore_setup.tar.gz"


def default_manifest(
    *,
    dashboard_file: Optional[str],
    packages: Iterable[str],
    extra: Optional[dict] = None,
) -> dict:
    """Build the manifest.json payload for a bundle.

    The manifest is intentionally minimal: it describes the bundle
    schema, the creator's stated package list, and the bundle timestamp.
    The owner is in control of "what's in here" — there is no remote
    verifier and no signature. The privacy invariant is that we never
    read a remote source.
    """
    payload = {
        "schema": "roamcore.labs/bundle",
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "created_at": _utc_now_iso(),
        "creator": "roamcore.labs_export_setup",
        "dashboard_file": dashboard_file or "",
        "packages": list(packages),
    }
    if extra:
        payload.update(extra)
    return payload


def write_bundle(
    out_path: Path,
    *,
    manifest: dict,
    dashboard_text: Optional[str],
    packages_dir: Optional[Path],
    dry_run: bool = False,
) -> Path:
    """Write the bundle tar.gz to ``out_path``.

    Returns the resolved output path. The output directory is created
    on demand. On ``dry_run``, do not write anything but still return
    the resolved path so the operator can preview.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if dry_run:
        # We still touch the manifest-only wiring so the dry-run is
        # meaningfully different from "do nothing".
        return out_path

    with tarfile.open(out_path, "w:gz") as tf:
        # 1. manifest.json
        manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
        from io import BytesIO
        info = tarfile.TarInfo(name="manifest.json")
        info.size = len(manifest_bytes)
        info.mtime = int(datetime.now(timezone.utc).timestamp())
        tf.addfile(info, BytesIO(manifest_bytes))

        # 2. dashboard.yaml (best-effort).
        if dashboard_text is not None:
            info = tarfile.TarInfo(name="dashboard.yaml")
            data = dashboard_text.encode("utf-8")
            info.size = len(data)
            info.mtime = int(datetime.now(timezone.utc).timestamp())
            tf.addfile(info, BytesIO(data))

        # 3. packages/ — include every file under the packages root.
        if packages_dir is not None and packages_dir.exists():
            for child in sorted(packages_dir.rglob("*")):
                if not child.is_file():
                    continue
                arc = "packages/" + str(child.relative_to(packages_dir))
                tf.add(str(child), arcname=arc, recursive=False)

    return out_path


def read_bundle_state(state_file: Path = Path(DEFAULT_STATE_FILE)) -> dict:
    """Read the latest state.json. Returns an empty dict if missing."""
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def write_bundle_state(state: dict, state_file: Path = Path(DEFAULT_STATE_FILE)) -> None:
    """Write the state.json atomically."""
    state_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_file.with_suffix(state_file.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
    os.replace(tmp, state_file)


def _read_text(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


def build_export(
    *,
    target_path: Optional[str] = None,
    dashboard_file: Optional[str] = DEFAULT_DASHBOARD_FILE,
    packages_dir: Optional[str] = DEFAULT_PACKAGES_DIR,
    dry_run: bool = False,
) -> dict:
    """Convenience wrapper that resolves the path, builds the manifest,
    and writes the bundle. Returns a small dict the CLI / service can
    render (path, manifest, dry_run)."""
    out_path = resolve_export_path(target_path)
    # Best-effort: read the dashboard if it exists.
    dashboard_text = _read_text(dashboard_file)
    # Best-effort: list the packages dir.
    packages: list[str] = []
    if packages_dir:
        pd = Path(packages_dir)
        if pd.exists():
            for child in sorted(pd.glob("*.yaml")):
                packages.append(child.name)

    manifest = default_manifest(
        dashboard_file=dashboard_file,
        packages=packages,
    )

    written = write_bundle(
        out_path,
        manifest=manifest,
        dashboard_text=dashboard_text,
        packages_dir=Path(packages_dir) if packages_dir else None,
        dry_run=dry_run,
    )

    if not dry_run:
        # Update the state file.
        state = read_bundle_state()
        state["export_count"] = int(state.get("export_count", 0) or 0) + 1
        state["last_export_path"] = str(written)
        state["last_export_at"] = _utc_now_iso()
        try:
            write_bundle_state(state)
        except OSError:
            # State file is best-effort; the bundle is the source of truth.
            pass

    return {
        "path": str(written),
        "manifest": manifest,
        "dry_run": dry_run,
    }


def _die(msg: str, code: int = 2) -> None:
    """Print an error to stderr and exit non-zero."""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)
