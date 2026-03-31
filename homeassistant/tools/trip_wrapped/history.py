"""Local, privacy-first Trip Wrapped history store.

Stores small summaries for completed wrapped exports so we can compute:
- record-based insights ("your longest trip yet")
- vs-average comparisons
- behaviour shifts
- a simple traveller type classification

All deterministic and local-only.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any


def _parse_iso(s: str | None) -> float | None:
    if not s:
        return None
    ss = str(s).strip()
    if ss.endswith("Z"):
        ss = ss[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(ss).timestamp()
    except Exception:
        return None


def _ms(v: Any) -> int:
    try:
        return int(float(v))
    except Exception:
        return 0


def _f(v: Any) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0


@dataclass
class TripSummary:
    trip_id: str
    device_id: int | None
    from_ts: str | None
    to_ts: str | None
    generated_at: str | None

    total_distance_m: float
    total_duration_ms: int
    number_of_stops: int

    longest_drive_m: float
    longest_drive_hours: float
    longest_stop_duration_ms: int

    avg_stop_hours: float
    percent_stationary: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def history_path(config_dir: str) -> str:
    # keep inside RoamCore state dir to avoid clutter
    return os.path.join(config_dir, ".roamcore", "trip_wrapped_history.json")


def load_history(config_dir: str) -> list[dict[str, Any]]:
    p = history_path(config_dir)
    try:
        if not os.path.exists(p):
            return []
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("trips"), list):
            return data["trips"]
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def save_history(config_dir: str, trips: list[dict[str, Any]]) -> None:
    p = history_path(config_dir)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    payload = {"trips": trips}
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp, p)


def summarize_wrapped(wrapped: dict[str, Any]) -> TripSummary:
    meta = wrapped.get("meta") or {}
    stats = wrapped.get("stats") or {}

    device_id = meta.get("deviceId")
    try:
        device_id = int(device_id) if device_id is not None else None
    except Exception:
        device_id = None

    from_ts = meta.get("from")
    to_ts = meta.get("to")
    trip_id = f"{device_id or 'dev'}:{from_ts or ''}:{to_ts or ''}"

    return TripSummary(
        trip_id=trip_id,
        device_id=device_id,
        from_ts=str(from_ts) if from_ts else None,
        to_ts=str(to_ts) if to_ts else None,
        generated_at=str(meta.get("generatedAt") or "") or None,
        total_distance_m=_f(stats.get("totalDistanceM")),
        total_duration_ms=_ms(stats.get("totalDurationMs")),
        number_of_stops=int(_f(stats.get("numberOfStops")) or 0),
        longest_drive_m=_f(stats.get("longestDriveM")),
        longest_drive_hours=_f(stats.get("longestDriveHours")),
        longest_stop_duration_ms=_ms(stats.get("longestStopDurationMs")),
        avg_stop_hours=_f(stats.get("avgStopHours")),
        percent_stationary=(
            float(stats.get("percentStationary"))
            if stats.get("percentStationary") is not None
            else None
        ),
    )


def upsert_history(config_dir: str, wrapped: dict[str, Any], max_trips: int = 200) -> list[dict[str, Any]]:
    """Insert/update current trip summary and return full history list."""
    trips = load_history(config_dir)
    s = summarize_wrapped(wrapped)

    # Remove existing matching id
    out: list[dict[str, Any]] = [t for t in trips if str(t.get("trip_id")) != s.trip_id]
    out.append(s.to_dict())

    # Sort oldest->newest by from_ts if possible
    out.sort(key=lambda t: (_parse_iso(t.get("from_ts") or "") or 0.0))

    if max_trips > 0 and len(out) > max_trips:
        out = out[-max_trips:]

    save_history(config_dir, out)
    return out


