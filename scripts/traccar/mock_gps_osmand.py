#!/usr/bin/env python3
"""Send mock GPS points to Traccar using the OsmAnd HTTP protocol.

This is a DEV TOOL to help validate the RoamCore map UI and Traccar route history
without real hardware.

It sends positions to:
  http://<host>:5055/?id=<uniqueId>&lat=...&lon=...&timestamp=...

Usage:
  python3 scripts/traccar/mock_gps_osmand.py --host 192.168.1.66 --device roamcore

Notes:
- Traccar must have a device whose uniqueId matches --device.
- Port 5055 is the default OsmAnd protocol port in many Traccar installs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import time
from typing import Iterable, Tuple

import urllib.parse
import urllib.request


def _pts_lake_district() -> list[Tuple[float, float]]:
    # A short loop near Keswick / Derwentwater (roughly).
    return [
        (54.6034, -3.1354),
        (54.5995, -3.1409),
        (54.5954, -3.1455),
        (54.5909, -3.1453),
        (54.5868, -3.1426),
        (54.5826, -3.1392),
        (54.5790, -3.1348),
        (54.5762, -3.1298),
        (54.5740, -3.1240),
        (54.5730, -3.1182),
        (54.5736, -3.1122),
        (54.5760, -3.1070),
        (54.5793, -3.1042),
        (54.5832, -3.1053),
        (54.5881, -3.1102),
        (54.5927, -3.1172),
        (54.5970, -3.1243),
        (54.6007, -3.1300),
        (54.6034, -3.1354),
    ]


def send_points(
    host: str,
    port: int,
    device: str,
    points: Iterable[Tuple[float, float]],
    start: dt.datetime,
    step_sec: int,
    sleep_sec: float,
) -> None:
    base = f"http://{host}:{port}/"
    t = start
    for (lat, lon) in points:
        qs = {
            "id": device,
            "lat": f"{lat:.6f}",
            "lon": f"{lon:.6f}",
            "timestamp": t.replace(tzinfo=dt.timezone.utc).isoformat().replace("+00:00", "Z"),
            # Optional fields
            "speed": "8",
            "bearing": "0",
            "altitude": "120",
        }
        url = base + "?" + urllib.parse.urlencode(qs)
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            # OsmAnd protocol returns 200 with empty body on success.
            if resp.status != 200:
                raise RuntimeError(f"unexpected status {resp.status}")
        print(f"sent {qs['timestamp']} {lat:.6f},{lon:.6f}")
        t = t + dt.timedelta(seconds=step_sec)
        if sleep_sec > 0:
            time.sleep(sleep_sec)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="192.168.1.66")
    ap.add_argument("--port", type=int, default=5055)
    ap.add_argument("--device", default="roamcore")
    ap.add_argument("--step-sec", type=int, default=30)
    ap.add_argument("--sleep", type=float, default=0.0, help="sleep between points (sec)")
    args = ap.parse_args()

    pts = _pts_lake_district()
    start = dt.datetime.utcnow() - dt.timedelta(minutes=10)
    send_points(
        host=args.host,
        port=args.port,
        device=args.device,
        points=pts,
        start=start,
        step_sec=args.step_sec,
        sleep_sec=args.sleep,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

