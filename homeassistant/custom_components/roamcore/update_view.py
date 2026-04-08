from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

import aiohttp

from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_PROVISION_REF, DEFAULT_PROVISION_REF


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_text(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


def _parse_kv(text: Optional[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    if not text:
        return out
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        if "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        k = k.strip()
        v = v.strip()
        if k:
            out[k] = v
    return out


def _manifest_version_local() -> Optional[str]:
    try:
        here = os.path.dirname(__file__)
        p = os.path.join(here, "manifest.json")
        raw = _read_text(p)
        if not raw:
            return None
        obj = json.loads(raw)
        v = obj.get("version")
        return str(v) if v else None
    except Exception:
        return None


def _slug_from_repo(repo: str) -> str:
    s = (repo or "").strip()
    s = s.replace("https://github.com/", "").strip("/")
    if s.endswith(".git"):
        s = s[:-4]
    return s


async def fetch_latest_release_tag(repo: str) -> str:
    slug = _slug_from_repo(repo)
    if not slug:
        raise RuntimeError("invalid_repo")

    url = f"https://api.github.com/repos/{slug}/releases/latest"
    headers = {
        "User-Agent": "RoamCore/backup-update",
        "Accept": "application/vnd.github+json",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=12)) as resp:
            resp.raise_for_status()
            obj = await resp.json()

    tag = str(obj.get("tag_name") or "").strip()
    if not tag:
        raise RuntimeError("no_tag")
    return tag


async def _fetch_latest_release(repo: str) -> dict[str, Any]:
    slug = _slug_from_repo(repo)
    if not slug:
        return {"ok": False, "error": "invalid_repo"}

    url = f"https://api.github.com/repos/{slug}/releases/latest"
    headers = {
        "User-Agent": "RoamCore/backup-update",
        "Accept": "application/vnd.github+json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=12)) as resp:
                resp.raise_for_status()
                obj = await resp.json()
        return {
            "ok": True,
            "tag": str(obj.get("tag_name") or "").strip() or None,
            "name": obj.get("name"),
            "published_at": obj.get("published_at"),
            "html_url": obj.get("html_url"),
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


async def _fetch_manifest_version_remote(repo: str, ref: str) -> dict[str, Any]:
    slug = _slug_from_repo(repo)
    if not slug or not ref:
        return {"ok": False, "error": "invalid_args"}

    url = f"https://raw.githubusercontent.com/{slug}/{ref}/homeassistant/custom_components/roamcore/manifest.json"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=12)) as resp:
                resp.raise_for_status()
                raw = await resp.text()
        obj = json.loads(raw)
        v = obj.get("version")
        return {"ok": True, "version": str(v) if v else None, "url": url}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "url": url}


class RoamcoreUpdateView(HomeAssistantView):
    url = "/api/roamcore/update"
    name = "api:roamcore_update"

    def __init__(self, hass: HomeAssistant, entry_id: str):
        self._hass = hass
        self._entry_id = entry_id
        self._cache: dict[str, Any] = {}
        self._cache_ts: float = 0

    async def get(self, request):
        hass = self._hass
        now = datetime.now(timezone.utc).timestamp()

        if self._cache and (now - (self._cache_ts or 0)) < 60:
            return self.json(self._cache)

        entry: Optional[ConfigEntry] = hass.config_entries.async_get_entry(self._entry_id)
        options = dict(entry.options) if entry else {}

        repo = str(request.query.get("repo") or "https://github.com/roamcore/RoamCore").strip()
        configured_ref = str(options.get(CONF_PROVISION_REF, DEFAULT_PROVISION_REF) or DEFAULT_PROVISION_REF)

        install_info_path = hass.config.path(".roamcore", "install-info.txt")
        install_raw = await hass.async_add_executor_job(lambda: _read_text(install_info_path))
        install = _parse_kv(install_raw)

        latest = await _fetch_latest_release(repo)
        latest_manifest = None
        if latest.get("ok") and latest.get("tag"):
            latest_manifest = await _fetch_manifest_version_remote(repo, latest.get("tag"))

        payload: dict[str, Any] = {
            "contract": {"name": "roamcore_update", "version": 1},
            "generated_at": _iso_now(),
            "repo": repo,
            "configured": {"provision_ref": configured_ref},
            "installed": {
                "component_version": _manifest_version_local(),
                "repo": install.get("repo") or None,
                "ref": install.get("ref") or None,
                "installed_at": install.get("installed_at") or None,
                "backup_dir": install.get("backup_dir") or None,
                "install_info_path": "/config/.roamcore/install-info.txt",
            },
            "latest": {"release": latest, "manifest": latest_manifest},
            "backup_support": {
                "backup_create": hass.services.has_service("backup", "create"),
                "hassio_backup_full": hass.services.has_service("hassio", "backup_full"),
            },
        }

        self._cache = payload
        self._cache_ts = now
        return self.json(payload)
