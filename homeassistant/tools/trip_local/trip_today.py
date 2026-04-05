#!/usr/bin/env python3

"""Local-first trip metrics from Home Assistant recorder DB.

Goal (beta): provide basic trip distance/time/stops without depending on Traccar.

Reads `/config/home-assistant_v2.db` (SQLite) and extracts device_tracker latitude/longitude
from the `states.attributes` JSON recorded by Home Assistant.

This is privacy-first and works fully offline.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import sqlite3
from typing import Any


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="/config/home-assistant_v2.db")
    p.add_argument("--entity-id", required=True)
    p.add_argument(
        "--day",
        default="today",
        help="today|yesterday|ISO date YYYY-MM-DD (interpreted as local time)",
    )
    p.add_argument("--out-json", default="")
    p.add_argument("--min-move-m", type=float, default=25.0)
    p.add_argument("--min-stop-min", type=float, default=10.0)
    p.add_argument("--max-points", type=int, default=5000)
    return p.parse_args()


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p = math.pi / 180.0
    a1 = lat1 * p
    a2 = lat2 * p
    dlat = (lat2 - lat1) * p
    dlon = (lon2 - lon1) * p
    s = math.sin(dlat / 2) ** 2 + math.cos(a1) * math.cos(a2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(s), math.sqrt(1 - s))
    return r * c


def _local_midnight_range(day: str) -> tuple[dt.datetime, dt.datetime]:
    now = dt.datetime.now().astimezone()
    if day == "today":
        d = now.date()
    elif day == "yesterday":
        d = (now - dt.timedelta(days=1)).date()
    else:
        d = dt.date.fromisoformat(day)
    start = dt.datetime(d.year, d.month, d.day, 0, 0, 0).astimezone()
    end = start + dt.timedelta(days=1)
    return start, end


def _load_points(db_path: str, entity_id: str, start: dt.datetime, end: dt.datetime, max_points: int) -> list[dict[str, Any]]:
    if not os.path.exists(db_path):
        return []

    start_ts = start.timestamp()
    end_ts = end.timestamp()

    con = sqlite3.connect(db_path)
    try:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        # Join states_meta to get metadata_id for entity_id.
        cur.execute("SELECT metadata_id FROM states_meta WHERE entity_id = ?", (entity_id,))
        row = cur.fetchone()
        if not row:
            return []
        mid = int(row[0])

        # states.last_updated_ts is float seconds.
        cur.execute(
            """
            SELECT last_updated_ts, attributes
            FROM states
            WHERE metadata_id = ?
              AND last_updated_ts >= ?
              AND last_updated_ts < ?
            ORDER BY last_updated_ts ASC
            LIMIT ?
            """,
            (mid, float(start_ts), float(end_ts), int(max_points)),
        )
        out = []
        for r in cur.fetchall():
            try:
                attrs = json.loads(r["attributes"] or "{}")
            except Exception:
                attrs = {}
            lat = attrs.get("latitude")
            lon = attrs.get("longitude")
            if lat is None or lon is None:
                continue
            try:
                lat = float(lat)
                lon = float(lon)
            except Exception:
                continue
            out.append({"t": float(r["last_updated_ts"]), "lat": lat, "lon": lon})
        return out
    finally:
        con.close()


def compute(points: list[dict[str, Any]], min_move_m: float, min_stop_s: float) -> dict[str, Any]:
    if len(points) < 2:
        return {
            "distance_m": 0.0,
            "drive_time_s": 0,
            "stops": 0,
            "segments": 0,
            "points": len(points),
        }

    dist = 0.0
    drive_s = 0
    stops = 0
    segments = 0

    # Simple state machine: moving vs stopped.
    moving = False
    stop_start = None

    for prev, cur in zip(points, points[1:]):
        d = _haversine_m(prev["lat"], prev["lon"], cur["lat"], cur["lon"])
        dt_s = max(0, int(cur["t"] - prev["t"]))
        dist += max(0.0, d)

        if d >= min_move_m:
            drive_s += dt_s
            if not moving:
                segments += 1
                moving = True
            stop_start = None
        else:
            # candidate stop
            if moving:
                moving = False
                stop_start = prev["t"]
            if stop_start is not None:
                if (cur["t"] - stop_start) >= min_stop_s:
                    # Count once, then reset to avoid recount until movement resumes.
                    stops += 1
                    stop_start = None

    return {
        "distance_m": float(dist),
        "drive_time_s": int(drive_s),
        "stops": int(stops),
        "segments": int(segments),
        "points": len(points),
    }


def main():
    a = parse_args()
    start, end = _local_midnight_range(a.day)
    pts = _load_points(a.db, a.entity_id, start=start, end=end, max_points=a.max_points)
    stats = compute(pts, min_move_m=float(a.min_move_m), min_stop_s=float(a.min_stop_min) * 60.0)
    payload = {
        "meta": {
            "entity_id": a.entity_id,
            "day": a.day,
            "from": start.isoformat(),
            "to": end.isoformat(),
            "generated_at": dt.datetime.now().astimezone().isoformat(),
        },
        "stats": stats,
    }
    if a.out_json:
        os.makedirs(os.path.dirname(a.out_json), exist_ok=True)
        tmp = a.out_json + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, a.out_json)
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()

