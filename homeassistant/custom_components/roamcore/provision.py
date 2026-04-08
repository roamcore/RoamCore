from __future__ import annotations

import io
import os
import shutil
import tarfile
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

import aiohttp


@dataclass
class ProvisionResult:
    installed: list[str]
    backup_dir: str
    manifest_path: str
    info_path: str


def _ts() -> str:
    # Seconds resolution is not enough for back-to-back provisioning calls.
    # Include a short random suffix to avoid collisions.
    return datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]


def _ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)


def _atomic_write(path: str, text: str) -> None:
    d = os.path.dirname(path)
    _ensure_dir(d)
    fd, tmp = tempfile.mkstemp(prefix=os.path.basename(path) + ".", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.unlink(tmp)
        except Exception:
            pass


def _safe_extract(tf: tarfile.TarFile, dest_dir: str) -> None:
    """Extract tarball defensively (avoid path traversal / special members)."""

    dest_real = os.path.realpath(dest_dir)
    members: list[tarfile.TarInfo] = []
    for m in tf.getmembers():
        # Only allow regular files and directories.
        if not (m.isreg() or m.isdir()):
            continue
        target = os.path.realpath(os.path.join(dest_dir, m.name))
        if not (target == dest_real or target.startswith(dest_real + os.sep)):
            raise RuntimeError(f"unsafe tar member path: {m.name}")
        members.append(m)
    tf.extractall(dest_dir, members=members)


def _files_equal(a: str, b: str) -> bool:
    try:
        sa = os.stat(a)
        sb = os.stat(b)
        if sa.st_size != sb.st_size:
            return False
        # Chunked compare
        with open(a, "rb") as fa, open(b, "rb") as fb:
            while True:
                ca = fa.read(1024 * 256)
                cb = fb.read(1024 * 256)
                if ca != cb:
                    return False
                if not ca:
                    return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def _copy_file(src: str, dest: str, backup_root: str, config_dir: str, installed: list[str]) -> None:
    _ensure_dir(os.path.dirname(dest))
    # Idempotent re-run: avoid rewriting/backup churn if unchanged.
    if os.path.exists(dest) and _files_equal(src, dest):
        installed.append(os.path.relpath(dest, config_dir))
        return
    # backup if exists
    if os.path.exists(dest):
        rel = os.path.relpath(dest, config_dir)
        bpath = os.path.join(backup_root, rel)
        _ensure_dir(os.path.dirname(bpath))
        try:
            with open(dest, "rb") as rf, open(bpath, "wb") as wf:
                wf.write(rf.read())
        except Exception:
            pass
    try:
        shutil.copy2(src, dest)
    except Exception:
        with open(src, "rb") as rf, open(dest, "wb") as wf:
            wf.write(rf.read())
    installed.append(os.path.relpath(dest, config_dir))


def _iter_files(root: str) -> Iterable[str]:
    for base, _, files in os.walk(root):
        for fn in files:
            if fn == ".gitkeep":
                continue
            yield os.path.join(base, fn)


async def provision_from_github(
    *,
    session: aiohttp.ClientSession,
    repo: str,
    ref: str,
    config_dir: str,
    state_dir: str,
) -> ProvisionResult:
    """Download repo tarball and install homeassistant/ assets into /config.

    This mirrors the shell installer logic but is callable from HA (HACS-first UX).
    """

    slug = repo.replace("https://github.com/", "").strip("/")
    if slug.endswith(".git"):
        slug = slug[:-4]
    archive_url = f"https://github.com/{slug}/archive/{ref}.tar.gz"

    work = tempfile.mkdtemp(prefix="roamcore-provision-")
    try:
        tgz_path = os.path.join(work, "src.tar.gz")
        async with session.get(archive_url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
            resp.raise_for_status()
            with open(tgz_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(1024 * 256):
                    f.write(chunk)

        src_root = os.path.join(work, "src")
        _ensure_dir(src_root)
        with tarfile.open(tgz_path, "r:gz") as tf:
            _safe_extract(tf, src_root)

        # locate top dir
        top_dirs = [d for d in os.listdir(src_root) if os.path.isdir(os.path.join(src_root, d))]
        if not top_dirs:
            raise RuntimeError("archive extract failed")
        top = os.path.join(src_root, top_dirs[0])
        ha_src = os.path.join(top, "homeassistant")
        if not os.path.isdir(ha_src):
            raise RuntimeError("archive missing homeassistant/")

        state = os.path.join(config_dir, state_dir)
        manifest_path = os.path.join(state, "manifest.txt")
        info_path = os.path.join(state, "install-info.txt")
        backup_dir = os.path.join(state, "backups", _ts())
        _ensure_dir(state)
        _ensure_dir(backup_dir)

        installed: list[str] = []

        def install_dir_children(src_dir: str, dest_dir: str) -> None:
            if not os.path.isdir(src_dir):
                return
            for f in _iter_files(src_dir):
                rel = os.path.relpath(f, src_dir)
                _copy_file(f, os.path.join(dest_dir, rel), backup_root=backup_dir, config_dir=config_dir, installed=installed)

        install_dir_children(os.path.join(ha_src, "packages"), os.path.join(config_dir, "packages"))
        install_dir_children(os.path.join(ha_src, "custom_components"), os.path.join(config_dir, "custom_components"))
        install_dir_children(os.path.join(ha_src, "www"), os.path.join(config_dir, "www"))
        install_dir_children(os.path.join(ha_src, "lovelace"), os.path.join(config_dir, "lovelace"))
        install_dir_children(os.path.join(ha_src, "tools"), os.path.join(config_dir, "tools"))

        installed_sorted = sorted(set(installed))
        _atomic_write(manifest_path, "\n".join(installed_sorted) + "\n")
        _atomic_write(
            info_path,
            "\n".join(
                [
                    f"installed_at={datetime.now().isoformat()}",
                    f"repo={repo}",
                    f"ref={ref}",
                    f"archive_url={archive_url}",
                    f"backup_dir={backup_dir}",
                ]
            )
            + "\n",
        )

        return ProvisionResult(
            installed=installed_sorted,
            backup_dir=backup_dir,
            manifest_path=manifest_path,
            info_path=info_path,
        )
    finally:
        try:
            # best-effort cleanup
            for base, dirs, files in os.walk(work, topdown=False):
                for fn in files:
                    try:
                        os.unlink(os.path.join(base, fn))
                    except Exception:
                        pass
                for dn in dirs:
                    try:
                        os.rmdir(os.path.join(base, dn))
                    except Exception:
                        pass
            os.rmdir(work)
        except Exception:
            pass
