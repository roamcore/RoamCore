#!/usr/bin/env python3
"""Pack an XYZ tile directory (z/x/y.png) into an MBTiles file.

Useful for generating offline tiles locally (e.g. with GDAL), then packaging
into a single SQLite MBTiles for RoamCore's /rc-tiles server.

Example:
  python3 scripts/tiles/pack_xyz_dir_to_mbtiles.py --in /tmp/tiles --out tiles.mbtiles
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path


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


def set_meta(conn: sqlite3.Connection, name: str, value: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO metadata(name,value) VALUES (?,?)",
        (name, value),
    )


def xyz_to_tms_y(z: int, y: int) -> int:
    return (1 << z) - 1 - y


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="indir", required=True, help="XYZ tile root dir")
    ap.add_argument("--out", dest="out", required=True, help="Output MBTiles")
    ap.add_argument("--name", default="RoamCore Offline Tiles")
    ap.add_argument("--format", default="png")
    args = ap.parse_args()

    root = Path(args.indir)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(out))
    try:
        ensure_schema(conn)
        set_meta(conn, "name", args.name)
        set_meta(conn, "format", args.format)
        set_meta(conn, "type", "baselayer")
        set_meta(conn, "version", "1")
        conn.commit()

        cur = conn.cursor()
        count = 0

        for zdir in sorted([p for p in root.iterdir() if p.is_dir() and p.name.isdigit()], key=lambda p: int(p.name)):
            z = int(zdir.name)
            for xdir in [p for p in zdir.iterdir() if p.is_dir() and p.name.isdigit()]:
                x = int(xdir.name)
                for yfile in xdir.iterdir():
                    if not yfile.is_file():
                        continue
                    name = yfile.name
                    if not name.endswith(".png") and not name.endswith(".jpg") and not name.endswith(".jpeg"):
                        continue
                    y = int(name.split(".")[0])
                    data = yfile.read_bytes()
                    tms_y = xyz_to_tms_y(z, y)
                    cur.execute(
                        "INSERT OR REPLACE INTO tiles(zoom_level,tile_column,tile_row,tile_data) VALUES (?,?,?,?)",
                        (z, x, tms_y, sqlite3.Binary(data)),
                    )
                    count += 1
                    if count % 5000 == 0:
                        conn.commit()
                        print(f"packed {count} tiles...")

            conn.commit()
            print(f"z={z} done (total {count})")

        conn.commit()
        print(f"DONE. packed {count} tiles into {out}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

