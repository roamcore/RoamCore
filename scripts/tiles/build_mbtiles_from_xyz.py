#!/usr/bin/env python3
"""Build a small offline MBTiles file by downloading XYZ raster tiles.

DEV/BETA helper to bootstrap offline maps. Once the MBTiles exists on HAOS at:
  /config/roamcore/tiles.mbtiles
the RoamCore map can run fully offline (served via /rc-tiles/).

Example:
  python3 scripts/tiles/build_mbtiles_from_xyz.py \
    --out tiles.mbtiles \
    --lat 54.6034 --lon -3.1354 --radius-km 35 \
    --min-z 9 --max-z 14

Notes:
- Downloads from a remote provider (default OSM). Run once during provisioning,
  then operate offline.
- Respects a small delay between requests.
"""

from __future__ import annotations

import argparse
import math
import os
import random
import sqlite3
import time
import urllib.request


def latlon_to_tile(lat: float, lon: float, z: int) -> tuple[int, int]:
    lat_rad = math.radians(lat)
    n = 2.0**z
    xtile = int((lon + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile


def clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS metadata (name TEXT PRIMARY KEY, value TEXT)"
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tiles (
          zoom_level INTEGER,
          tile_column INTEGER,
          tile_row INTEGER,
          tile_data BLOB,
          PRIMARY KEY (zoom_level, tile_column, tile_row)
        )
        """
    )
    conn.commit()


def set_metadata(conn: sqlite3.Connection, name: str, value: str) -> None:
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO metadata(name,value) VALUES (?,?)",
        (name, value),
    )
    conn.commit()


def xyz_to_tms_y(z: int, y: int) -> int:
    return (1 << z) - 1 - y


def fetch(url: str, ua: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--tile-url", default="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png")
    ap.add_argument("--lat", type=float)
    ap.add_argument("--lon", type=float)
    ap.add_argument("--radius-km", type=float, default=35.0)
    ap.add_argument("--global", dest="is_global", action="store_true", help="Download full world tile range for each zoom")
    ap.add_argument("--min-z", type=int, default=9)
    ap.add_argument("--max-z", type=int, default=14)
    ap.add_argument("--x-min", type=int, help="optional: limit tile x range")
    ap.add_argument("--x-max", type=int, help="optional: limit tile x range")
    ap.add_argument("--y-min", type=int, help="optional: limit tile y range")
    ap.add_argument("--y-max", type=int, help="optional: limit tile y range")
    ap.add_argument("--delay", type=float, default=0.05)
    ap.add_argument("--max-tiles", type=int, default=5000)
    args = ap.parse_args()

    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)

    if not args.is_global:
        if args.lat is None or args.lon is None:
            raise SystemExit("--lat/--lon required unless --global")
        # crude bbox degrees; OK for small radius
        dlat = args.radius_km / 111.0
        dlon = args.radius_km / (111.0 * max(0.2, math.cos(math.radians(args.lat))))
        lat_min = args.lat - dlat
        lat_max = args.lat + dlat
        lon_min = args.lon - dlon
        lon_max = args.lon + dlon

    conn = sqlite3.connect(out)
    ensure_schema(conn)
    set_metadata(conn, "name", "RoamCore Offline Tiles")
    set_metadata(conn, "format", "png")
    set_metadata(conn, "type", "baselayer")
    set_metadata(conn, "version", "1")

    subs = ["a", "b", "c"]
    ua = "RoamCoreTileBootstrap/0.1 (offline mbtiles generator)"

    total = 0
    cur = conn.cursor()

    for z in range(args.min_z, args.max_z + 1):
        n = 2**z
        if args.is_global:
            x_min, x_max = 0, n - 1
            y_min, y_max = 0, n - 1
        else:
            x1, y1 = latlon_to_tile(lat_max, lon_min, z)
            x2, y2 = latlon_to_tile(lat_min, lon_max, z)
            x_min, x_max = sorted((x1, x2))
            y_min, y_max = sorted((y1, y2))
            x_min = clamp(x_min, 0, n - 1)
            x_max = clamp(x_max, 0, n - 1)
            y_min = clamp(y_min, 0, n - 1)
            y_max = clamp(y_max, 0, n - 1)

        # Optional range limiting (useful for chunking large zooms)
        if args.x_min is not None:
            x_min = clamp(int(args.x_min), 0, n - 1)
        if args.x_max is not None:
            x_max = clamp(int(args.x_max), 0, n - 1)
        if args.y_min is not None:
            y_min = clamp(int(args.y_min), 0, n - 1)
        if args.y_max is not None:
            y_max = clamp(int(args.y_max), 0, n - 1)

        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                if total >= args.max_tiles:
                    break
                s = random.choice(subs)
                url = args.tile_url.format(s=s, z=z, x=x, y=y)
                try:
                    data = fetch(url, ua)
                except Exception:
                    continue

                tms_y = xyz_to_tms_y(z, y)
                cur.execute(
                    "INSERT OR REPLACE INTO tiles(zoom_level,tile_column,tile_row,tile_data) VALUES (?,?,?,?)",
                    (z, x, tms_y, sqlite3.Binary(data)),
                )
                total += 1
                if args.delay:
                    time.sleep(args.delay)
            if total >= args.max_tiles:
                break

        conn.commit()
        print(f"z={z} tiles={total}")

    conn.close()
    print(f"Wrote {total} tiles to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
