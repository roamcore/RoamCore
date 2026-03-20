#!/usr/bin/env python3

"""Generate a mock GPS track as GeoJSON for UI demos.

Writes a LineString feature to be served by Home Assistant under /local/...
This is intentionally dependency-free (stdlib only) for HAOS.

NOTE: Production tracking source-of-truth is Traccar. This tool is for UI demos only.
"""

import argparse
import json
import math
import os
import random
from datetime import datetime, timezone


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def gen_points(waypoints: list[tuple[float, float]], points_per_leg: int, jitter_m: float) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    if len(waypoints) < 2:
        return out

    # Rough conversion: 1 deg lat ~ 111_000m, 1 deg lon scaled by cos(lat)
    for i in range(len(waypoints) - 1):
        lat1, lon1 = waypoints[i]
        lat2, lon2 = waypoints[i + 1]
        for j in range(points_per_leg):
            t = j / float(points_per_leg)
            lat = lerp(lat1, lat2, t)
            lon = lerp(lon1, lon2, t)

            # Jitter
            if jitter_m > 0:
                lat_m = 111_000.0
                lon_m = 111_000.0 * max(0.2, math.cos(math.radians(lat)))
                lat += (random.uniform(-jitter_m, jitter_m) / lat_m)
                lon += (random.uniform(-jitter_m, jitter_m) / lon_m)

            out.append((lat, lon))

    # Add final waypoint
    out.append(waypoints[-1])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--points-per-leg", type=int, default=60)
    ap.add_argument("--jitter-m", type=float, default=12.0)
    ap.add_argument(
        "--preset",
        default="lakes_loop",
        help="lakes_loop | uk_roadtrip",
    )
    args = ap.parse_args()

    # (lat, lon)
    if args.preset == "uk_roadtrip":
        waypoints = [
            (51.5074, -0.1278),  # London
            (52.2053, 0.1218),  # Cambridge
            (53.4808, -2.2426),  # Manchester
            (54.4609, -3.0886),  # Lake District
            (55.9533, -3.1883),  # Edinburgh
            (54.5973, -5.9301),  # Belfast
            (53.3498, -6.2603),  # Dublin
            (52.4862, -1.8904),  # Birmingham
            (51.5074, -0.1278),  # back to London
        ]
    else:
        # Lake District loop
        waypoints = [
            (54.3760, -3.0150),  # Windermere
            (54.4609, -3.0886),  # Keswick-ish
            (54.5770, -3.3310),  # Wasdale
            (54.5070, -3.2140),  # Ennerdale
            (54.4300, -3.0430),  # Ambleside
            (54.3760, -3.0150),
        ]

    pts = gen_points(waypoints, max(5, args.points_per_leg), max(0.0, args.jitter_m))
    coords = [[lon, lat] for (lat, lon) in pts]
    obj = {
        "type": "Feature",
        "properties": {
            "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "preset": args.preset,
            "pointCount": len(coords),
        },
        "geometry": {
            "type": "LineString",
            "coordinates": coords,
        },
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


if __name__ == "__main__":
    main()
