"""Pure-function helpers for the RoamCore time + timezone contract.

These helpers are intentionally **HA-free** (no HomeAssistantView, no
ConfigEntry, no global state) so they can be unit-tested without a live
HA install.

Reference: docs/reference/rc-entity-naming.md
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

try:
    # Python 3.9+ stdlib.
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    _HAS_ZONEINFO = True
except Exception:  # pragma: no cover - Python <3.9
    ZoneInfo = None  # type: ignore
    ZoneInfoNotFoundError = Exception  # type: ignore
    _HAS_ZONEINFO = False


# Canonical enum for which source the active timezone came from.
# Order matters for documentation — keep this tuple unchanged unless
# the doc and dashboards are updated together.
RC_TIMEZONE_SOURCES: tuple[str, ...] = (
    "override",
    "ha_config",
    "browser",
    "unknown",
)

# Canonical sync status enum for the rc_time_status sensor.
# Order matters for documentation — keep this tuple unchanged unless
# the doc and dashboards are updated together.
RC_TIME_STATUSES: tuple[str, ...] = (
    "ok",
    "no_override",
    "invalid_override",
    "ha_unconfigured",
    "unknown",
)


def _strip(v: Any) -> str:
    """Safely coerce any input to a stripped string. Returns "" for None."""
    if v is None:
        return ""
    return str(v).strip()


def is_valid_iana_name(name: Any) -> bool:
    """Return True iff `name` is a valid IANA tz database key.

    Uses stdlib `zoneinfo` (Python 3.9+). Never raises.

    Notes on case: the IANA database is **case-sensitive** (`zoneinfo`
    itself is case-sensitive). Examples:

      - ``"Europe/London"``     → valid
      - ``"EUROPE/LONDON"``     → **invalid** (must match exactly)
      - ``"America/New_York"``  → valid
      - ``"UTC"``               → valid

    We intentionally reject mismatched case here so the "override" path
    in `resolve_timezone` only succeeds when the user wrote a valid
    canonical name (no silent case-folding surprises).
    """
    s = _strip(name)
    if not s:
        return False
    if not _HAS_ZONEINFO:
        # Without zoneinfo we fall back to a tiny hardcoded allowlist.
        return s in ("UTC", "Etc/UTC", "GMT")
    try:
        ZoneInfo(s)  # type: ignore[arg-type]
    except Exception:
        return False
    return True


def resolve_timezone(
    override: Any, ha_configured_tz: Any
) -> tuple[Optional[str], str]:
    """Resolve the canonical timezone name + source.

    Returns ``(canonical_tz_name, source)``. ``canonical_tz_name`` is
    ``None`` when neither source is usable; ``source`` is one of
    ``RC_TIMEZONE_SOURCES``.

    Canonical rules (in order):

      1. ``override`` is non-empty and a valid IANA name →
         return ``(override, "override")``.
      2. ``override`` is non-empty but **invalid** →
         fall through to HA config and source ``"invalid_override"``.
      3. ``ha_configured_tz`` is non-empty → return ``(it, "ha_config")``.
      4. else → return ``(None, "unknown")``.

    This function **never crashes** — any unparseable input is treated
    as "not provided". Callers can map ``(None, "unknown")`` to
    ``sensor.rc_time_status = "unknown"`` (or similar) without risk.
    """
    ovr = _strip(override)
    ha = _strip(ha_configured_tz)

    # 1. override valid?
    if ovr and is_valid_iana_name(ovr):
        return (ovr, "override")

    # 2. override set but invalid → still record "invalid_override",
    #    but try to fall back to ha_config for the actual timezone.
    if ovr and not is_valid_iana_name(ovr):
        if ha and is_valid_iana_name(ha):
            return (ha, "invalid_override")
        return (None, "invalid_override")

    # 3. ha_config (only if we didn't have an override attempt).
    if ha and is_valid_iana_name(ha):
        return (ha, "ha_config")

    # 4. nothing usable.
    return (None, "unknown")


def safe_isoformat(dt: Any) -> Optional[str]:
    """Best-effort ISO 8601 string for a datetime. Returns None on any failure.

    Behaviour:
      - ``None`` → ``None``
      - aware datetime → ``dt.isoformat()`` (preserves offset)
      - naive datetime → treated as UTC and emitted with ``+00:00`` suffix
      - any other type → ``None``
    """
    if dt is None:
        return None
    if not isinstance(dt, datetime):
        return None
    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        return None


def _coerce_enum(value: Any, allowed: tuple[str, ...]) -> str:
    """Coerce an enum-like string into one of `allowed` (or "unknown").

    Used by ``normalize_time_payload`` so we never emit values outside
    the documented contract enum.
    """
    s = _strip(value).lower()
    if s in allowed:
        return s
    return "unknown"


def normalize_time_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize a time payload dict for JSON exposure.

    Coerces nullable values to a stable shape:

      - ``now_iso`` becomes ISO-8601 string or None.
      - ``timezone`` becomes string or None.
      - ``source`` becomes one of ``RC_TIMEZONE_SOURCES`` (default "unknown").
      - ``utc_offset_minutes`` becomes int|None.
      - ``is_dst`` becomes bool|None.
      - ``status`` becomes one of ``RC_TIME_STATUSES`` (default "unknown").
      - ``reason`` becomes string (default "unknown").

    Unknown keys are preserved as-is so callers can layer on extra
    metadata without breaking the contract.
    """
    out: dict[str, Any] = {}

    if "now_iso" in payload:
        v = payload.get("now_iso")
        if isinstance(v, datetime):
            out["now_iso"] = safe_isoformat(v)
        elif isinstance(v, str):
            s = v.strip()
            out["now_iso"] = s if s else None
        else:
            # Any other type (object, list, int, dict, …) is unusable.
            out["now_iso"] = None

    if "timezone" in payload:
        tz_raw = payload.get("timezone")
        tz_s = _strip(tz_raw)
        if tz_s and is_valid_iana_name(tz_s):
            out["timezone"] = tz_s
        else:
            out["timezone"] = None

    if "source" in payload:
        out["source"] = _coerce_enum(payload.get("source"), RC_TIMEZONE_SOURCES)

    if "utc_offset_minutes" in payload:
        v = payload.get("utc_offset_minutes")
        if v is None or _strip(v) == "":
            out["utc_offset_minutes"] = None
        else:
            try:
                out["utc_offset_minutes"] = int(float(v))
            except (TypeError, ValueError):
                out["utc_offset_minutes"] = None

    if "is_dst" in payload:
        v = payload.get("is_dst")
        if isinstance(v, bool):
            out["is_dst"] = v
        elif v is None:
            out["is_dst"] = None
        else:
            s = _strip(v).lower()
            if s in ("on", "true", "1", "yes"):
                out["is_dst"] = True
            elif s in ("off", "false", "0", "no"):
                out["is_dst"] = False
            else:
                out["is_dst"] = None

    if "status" in payload:
        out["status"] = _coerce_enum(payload.get("status"), RC_TIME_STATUSES)

    if "reason" in payload:
        out["reason"] = _strip(payload.get("reason")) or "unknown"

    # Preserve any extra keys (forward-compat).
    for k, v in payload.items():
        if k not in out:
            out[k] = v

    return out
