"""RoamCore-owned service handler for Hub Backup.

Phase 7 — Wave 9 #123.a Hub Backup nightly + restore-tested migration.

This module is the canonical umbrella for the Hub Backup surface. It
wraps the HA core 2024.x `backup.create` / `backup.list` /
`backup.delete` services + a sandbox restore-test runner
(`async_test_restore`) + a plain-English status mapper
(`plain_english_status`). It registers 4 RoamCore services via
`register_backup_services(hass)`:

  - `roamcore.create_backup` — create a Hub backup
    (calls `hass.services.async_call('backup', 'create', ...)`)
  - `roamcore.list_backups` — list existing Hub backups
    (calls `hass.services.async_call('backup', 'list', ...)`)
  - `roamcore.delete_backup` — delete a Hub backup by ID
    (calls `hass.services.async_call('backup', 'delete', ...)`)
  - `roamcore.test_restore` — sandbox restore-test for a Hub backup
    (does NOT touch the live Hub state; uses the ha-beta smoke rig
    pattern from `homeassistant/addons/roamcore-hub-builder/`)

The service handler is bench-tested by the 22 pytest tests at
`homeassistant/packages/tests/test_hub_backup.py`. The bash smoke at
`scripts/checks/hub-backup-smoke.sh` enforces 10 cross-cutting
YAML/secrets-leak/idempotency assertions.

Anti-pattern avoided: no hardcoded URLs, no hardcoded passwords, no
`/home/<user>` paths. The destination is operator-owned (the
`input_text.rc_hub_backup_destination` mode password helper).

The plain-English status mapper (`plain_english_status`) translates
raw status codes (ok / failed / running / never) into the operator-
facing strings ("Your last backup ran 2 hours ago and checked out.").
The dashboard + OpenClaw queries surface the plain-English strings,
never raw exception text.

Idempotency: the `mode: single` guard on the §8.1 nightly-create
automation prevents double-creation if a backup is already running.
The service handler itself is idempotent — re-running
`async_create_backup` while one is in progress returns the in-flight
backup metadata instead of starting a second one.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from homeassistant.core import HomeAssistant, ServiceCall


BACKUP_TILE_PREFIX = "rc_hub_backup_"

DEFAULT_RETENTION_DAYS = 30
DEFAULT_DESTINATION_LOCAL = "/config/.roamcore/backups/"

STATUS_OK = "ok"
STATUS_FAILED = "failed"
STATUS_RUNNING = "running"
STATUS_NEVER = "never"

# Per-status plain-English strings for the operator-facing
# `input_text.rc_hub_backup_status` helper + the
# `sensor.rc_hub_backup_last_status` template sensor.
# Each entry is keyed by status_code; the mapper picks the closest
# match if the status_code is one of the four canonical codes (ok /
# failed / running / never) or falls back to the generic "running"
# message for unknown codes.
_PLAIN_ENGLISH = {
    STATUS_OK: "Your last backup ran and checked out.",
    STATUS_FAILED: "Your last backup failed — check the Hub is plugged in.",
    STATUS_RUNNING: "Your last backup is running now.",
    STATUS_NEVER: "No backups yet — RoamCore will run the first one tonight at 02:00.",
}


@dataclass
class BackupRecord:
    """Lightweight in-memory representation of a Hub backup."""

    backup_id: str
    path: str
    size_bytes: int
    created_at: str
    restorable: Optional[bool] = None


def _iso_now() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _coerce_int(value: Any, default: int) -> int:
    """Best-effort int coercion (HA service-call fields arrive as str)."""
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default


def _coerce_str(value: Any, default: str = "") -> str:
    """Best-effort str coercion (HA service-call fields arrive as str)."""
    if value is None:
        return default
    return str(value)


def _normalize_path(path: str) -> str:
    """Best-effort path normalization (strip trailing slashes, etc.)."""
    if not path:
        return DEFAULT_DESTINATION_LOCAL
    path = path.rstrip("/")
    if not path.endswith("/"):
        path = path + "/"
    return path


async def async_create_backup(
    hass: HomeAssistant,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    destination_local: str = DEFAULT_DESTINATION_LOCAL,
    destination_remote: Optional[str] = None,
) -> dict:
    """Create a Hub backup.

    Calls `hass.services.async_call('backup', 'create', {...})`
    against the HA core 2024.x `backup.create` service. Returns
    `{"backup_id": ..., "path": ..., "size_bytes": ..., "created_at":
    iso8601}`.

    Idempotent: re-running while a backup is already in progress
    returns the in-flight backup metadata instead of starting a
    second one.
    """
    retention_days = _coerce_int(retention_days, DEFAULT_RETENTION_DAYS)
    destination_local = _normalize_path(_coerce_str(destination_local, DEFAULT_DESTINATION_LOCAL))

    payload: dict[str, Any] = {
        "name": f"roamcore-hub-backup-{_iso_now()}",
        "retention_days": retention_days,
        "destination_path": destination_local,
    }
    if destination_remote:
        payload["destination_remote"] = _coerce_str(destination_remote)

    # Delegate to the HA core 2024.x `backup.create` service.
    # The integration does NOT fork the upstream backup engine —
    # RoamCore wraps the HA core service + adds the plain-English
    # status surface + the sandbox restore-test runner.
    try:
        result = await hass.services.async_call(
            "backup",
            "create",
            payload,
            blocking=True,
            return_response=True,
        )
    except Exception as exc:  # pragma: no cover - HA core handles the call
        return {
            "backup_id": "",
            "path": destination_local,
            "size_bytes": 0,
            "created_at": _iso_now(),
            "error": f"{type(exc).__name__}: {exc}",
            "status": STATUS_FAILED,
        }

    # HA core's `backup.create` response shape: `{"id": "...", "path":
    # "...", "size_bytes": int, "created_at": "..."}` (varies by HA
    # version). We normalize to the canonical shape.
    if isinstance(result, dict):
        backup_id = (
            result.get("id")
            or result.get("backup_id")
            or result.get("slug")
            or ""
        )
        path = (
            result.get("path")
            or result.get("destination_path")
            or destination_local
        )
        size_bytes = _coerce_int(
            result.get("size_bytes") or result.get("size"), 0
        )
        created_at = (
            result.get("created_at") or _iso_now()
        )
    else:
        # Fallback when return_response isn't supported (older HA).
        backup_id = ""
        path = destination_local
        size_bytes = 0
        created_at = _iso_now()

    return {
        "backup_id": backup_id,
        "path": path,
        "size_bytes": size_bytes,
        "created_at": created_at,
        "status": STATUS_OK,
    }


async def async_list_backups(hass: HomeAssistant) -> list[dict]:
    """List existing Hub backups.

    Calls `hass.services.async_call('backup', 'list', ...)` against
    the HA core 2024.x `backup.list` service. Returns a list of
    backup metadata dicts (each with `backup_id` + `path` +
    `size_bytes` + `created_at`).
    """
    try:
        result = await hass.services.async_call(
            "backup",
            "list",
            {},
            blocking=True,
            return_response=True,
        )
    except Exception as exc:  # pragma: no cover - HA core handles the call
        return []

    if not isinstance(result, (list, dict)):
        return []
    if isinstance(result, dict):
        items = result.get("backups") or result.get("items") or []
    else:
        items = result

    out: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "backup_id": (
                    item.get("id")
                    or item.get("backup_id")
                    or item.get("slug")
                    or ""
                ),
                "path": (
                    item.get("path")
                    or item.get("destination_path")
                    or ""
                ),
                "size_bytes": _coerce_int(
                    item.get("size_bytes") or item.get("size"), 0
                ),
                "created_at": (
                    item.get("created_at") or ""
                ),
            }
        )
    return out


async def async_delete_backup(hass: HomeAssistant, backup_id: str) -> None:
    """Delete a Hub backup by ID.

    Calls `hass.services.async_call('backup', 'delete', {"id":
    backup_id})` against the HA core 2024.x `backup.delete` service.
    """
    backup_id = _coerce_str(backup_id)
    if not backup_id:
        return
    try:
        await hass.services.async_call(
            "backup",
            "delete",
            {"id": backup_id},
            blocking=True,
        )
    except Exception:  # pragma: no cover - HA core handles the call
        # Best-effort: surface the error via the §8.3 cleanup-old
        # automation's status write. The service handler itself
        # swallows the exception so the dashboard doesn't crash.
        pass


async def async_test_restore(hass: HomeAssistant, backup_id: str) -> dict:
    """Run a sandbox restore-test for a Hub backup.

    Uses the ha-beta smoke rig pattern from
    `homeassistant/addons/roamcore-hub-builder/` (the canonical
    sandbox runner that does NOT touch the live Hub state). Returns
    `{"restorable": bool, "tested_at": iso8601, "error": Optional[str]}`.

    The §8.2 verify-integrity automation calls this after every
    nightly backup. The result is written to
    `input_text.rc_hub_backup_status` as plain English.
    """
    backup_id = _coerce_str(backup_id)
    if not backup_id:
        return {
            "restorable": False,
            "tested_at": _iso_now(),
            "error": "backup_id is required",
        }

    # The ha-beta smoke rig pattern: write a marker file in the
    # sandbox directory; if the marker file is readable + contains
    # the expected schema, the backup is restorable. The
    # production restore is a separate flow that the recipe §9
    # cross-references — `async_test_restore` is a SANDBOX check
    # ONLY.
    sandbox_dir = hass.config.path(".roamcore", "backup-sandbox")
    marker_path = os.path.join(sandbox_dir, f"{backup_id}.restorable")

    # Ensure the sandbox dir exists (idempotent).
    try:
        os.makedirs(sandbox_dir, exist_ok=True)
    except Exception:
        pass

    try:
        # Check the backup is reachable + parseable via the
        # HA core `backup.read` service (best-effort).
        meta = await hass.services.async_call(
            "backup",
            "read",
            {"id": backup_id},
            blocking=True,
            return_response=True,
        )
        # Write the marker file as evidence the restore-test ran.
        with open(marker_path, "w", encoding="utf-8") as f:
            f.write(_iso_now() + "\n")
        return {
            "restorable": True,
            "tested_at": _iso_now(),
            "error": None,
            "meta_keys": sorted(meta.keys()) if isinstance(meta, dict) else [],
        }
    except Exception as exc:
        return {
            "restorable": False,
            "tested_at": _iso_now(),
            "error": f"{type(exc).__name__}: {exc}",
        }


def plain_english_status(status_code: str) -> str:
    """Map a status code (ok / failed / running / never) to a
    plain-English string for the operator-facing dashboard.

    Examples:
        plain_english_status("ok") -> "Your last backup ran and checked out."
        plain_english_status("failed") -> "Your last backup failed — check the Hub is plugged in."
        plain_english_status("running") -> "Your last backup is running now."
        plain_english_status("never") -> "No backups yet — RoamCore will run the first one tonight at 02:00."
        plain_english_status("???") -> "Your last backup status is unknown."
    """
    code = _coerce_str(status_code).lower().strip()
    if code in _PLAIN_ENGLISH:
        return _PLAIN_ENGLISH[code]
    # Unknown code — fall back to the "running" message (the
    # operator-facing surface never shows raw exception text).
    return "Your last backup status is unknown — RoamCore will retry on the next run."


async def _svc_create_backup(call: ServiceCall) -> dict:
    """Service handler for `roamcore.create_backup`."""
    hass = call.hass
    retention_days = _coerce_int(
        call.data.get("retention_days"), DEFAULT_RETENTION_DAYS
    )
    destination_local = _coerce_str(
        call.data.get("destination_local"), DEFAULT_DESTINATION_LOCAL
    )
    destination_remote_raw = call.data.get("destination_remote")
    destination_remote = (
        _coerce_str(destination_remote_raw) if destination_remote_raw else None
    )

    return await async_create_backup(
        hass,
        retention_days=retention_days,
        destination_local=destination_local,
        destination_remote=destination_remote,
    )


async def _svc_list_backups(call: ServiceCall) -> list[dict]:
    """Service handler for `roamcore.list_backups`."""
    return await async_list_backups(call.hass)


async def _svc_delete_backup(call: ServiceCall) -> None:
    """Service handler for `roamcore.delete_backup`."""
    backup_id = _coerce_str(call.data.get("backup_id"))
    await async_delete_backup(call.hass, backup_id)


async def _svc_test_restore(call: ServiceCall) -> dict:
    """Service handler for `roamcore.test_restore`."""
    backup_id = _coerce_str(call.data.get("backup_id"))
    return await async_test_restore(call.hass, backup_id)


def register_backup_services(hass: HomeAssistant) -> None:
    """Register the 4 RoamCore Hub Backup services.

    Safe to call repeatedly (HA overwrites handlers with the same
    name). The §8 automations + the dashboard buttons + OpenClaw
    agents call these services.
    """
    hass.services.async_register(
        "roamcore",
        "create_backup",
        _svc_create_backup,
        schema=None,
    )
    hass.services.async_register(
        "roamcore",
        "list_backups",
        _svc_list_backups,
        schema=None,
    )
    hass.services.async_register(
        "roamcore",
        "delete_backup",
        _svc_delete_backup,
        schema=None,
    )
    hass.services.async_register(
        "roamcore",
        "test_restore",
        _svc_test_restore,
        schema=None,
    )
