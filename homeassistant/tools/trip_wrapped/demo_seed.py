#!/usr/bin/env python3
"""RoamCore Trip Wrapped — demo seed generator (slice #21).

Generates a deterministic, **fully local** "Trip Wrapped" payload for the
first-run USP flow. No outbound HTTP, no Traccar required, no telemetry.

Why this exists
---------------
When a brand-new RoamCore user opens Map → Trip Wrapped, they should see a
fully rendered report with **one tap**, not a setup wizard. This script is
the "killer demo" entry point: it produces a realistic-looking Trip Wrapped
JSON purely from local data (a hard-coded 4-day road trip) and points the
map image at the local RoamCore tileserver add-on
(`http://localhost:8000/...`). The "use my real trips" CTA only appears once
the operator configures Traccar.

Privacy contract
----------------
This script is stdlib-only, contains **zero outbound HTTP calls**, and the
map image URL it emits always starts with ``http://localhost:8000/`` (the
local tileserver add-on). Smoke check:
``scripts/checks/trip-wrapped-seamless-smoke.sh``.

Output shape
------------
A JSON object with these top-level keys (matching the acceptance contract):

- ``generatedAt``        : ISO-8601 UTC timestamp.
- ``mode``               : always ``"demo"`` for this generator.
- ``trip``               : object with ``distanceKm`` (float, km),
                           ``durationMin`` (int, minutes),
                           ``stops`` (int).
- ``mapImageUrl``        : local tileserver URL, e.g.
                           ``http://localhost:8000/staticmap.php?...``.

Usage
-----
::

    python3 demo_seed.py --out /config/www/roamcore/trip_wrapped/latest.json
    python3 demo_seed.py --dry-run --out /tmp/rc_demo.json
    python3 demo_seed.py --print

The service ``roamcore.trip_wrapped_demo`` (in the custom component) wraps
this script and returns the resulting path.

Design notes
------------
- Deterministic: same numbers every run (modulo ``generatedAt``).
- No random + no clock reads except for ``generatedAt``.
- Side-effect-free apart from the requested ``--out`` file.
- Stays in the same shape as the real exporter so the HTML template renders
  the demo identically to a real report.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import urllib.parse
from datetime import datetime, timezone


# --- Demo trip data (deterministic) ---
# A 4-day southwestern US road trip that fits the "RoamCore Wrapped" demo.
# Numbers chosen to look impressive but plausible; locked at slice #21 so
# the demo screenshots stay consistent across releases.
DEMO_DISTANCE_KM = 1770.0  # ≈ 1100 mi total
DEMO_DURATION_MIN = 17 * 60 + 58  # 17 h 58 min behind the wheel
DEMO_STOPS = 4  # Palm Springs, Grand Canyon Village, Albuquerque, Denver
DEMO_DAYS = 4


def _build_staticmap_url(points: list[tuple[float, float]], w: int = 980, h: int = 420) -> str:
    """Return a local-tileserver static-map URL for the given polyline.

    Always uses ``http://localhost:8000/staticmap.php`` (the local RoamCore
    tileserver add-on). This is the only map backend the demo path is
    allowed to reference — see the privacy contract in
    ``docs/feature-checklist.md``.
    """
    base = "http://localhost:8000/staticmap.php"

    # Simple auto-zoom: derive a center + zoom based on bbox.
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    c_lat = (min(lats) + max(lats)) / 2.0
    c_lon = (min(lons) + max(lons)) / 2.0

    # Path: keep it short so the URL stays under common server limits.
    path = "color:0x6EE7FF|weight:4" + "".join(
        f"|{lat:.5f},{lon:.5f}" for (lat, lon) in points
    )
    qs = {
        "center": f"{c_lat:.5f},{c_lon:.5f}",
        "zoom": "5",
        "size": f"{w}x{h}",
        "maptype": "mapnik",
        "path": path,
    }
    return base + "?" + urllib.parse.urlencode(qs)


def build_demo_payload(generated_at: str | None = None) -> dict:
    """Return the demo Trip Wrapped JSON payload (no I/O)."""
    if not generated_at:
        generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Coarse polyline: LA → Palm Springs → Grand Canyon → Albuquerque → Denver.
    # Same waypoints as the existing ``--demo`` path in ``export.py``.
    points = [
        (34.0100, -118.4960),  # Santa Monica
        (33.8303, -116.5453),  # Palm Springs
        (36.0544, -112.1401),  # Grand Canyon Village
        (35.0844, -106.6504),  # Albuquerque
        (39.7392, -104.9903),  # Denver
    ]
    map_image_url = _build_staticmap_url(points)

    payload = {
        # Contract field 1: ISO-8601 generation timestamp.
        "generatedAt": generated_at,
        # Contract field 2: explicit demo mode marker.
        "mode": "demo",
        # Contract fields 3–5 (nested under ``trip``).
        "trip": {
            "distanceKm": float(DEMO_DISTANCE_KM),
            "durationMin": int(DEMO_DURATION_MIN),
            "stops": int(DEMO_STOPS),
            "days": int(DEMO_DAYS),
        },
        # Contract field 5: local-tileserver URL (privacy-compliant).
        "mapImageUrl": map_image_url,
        # Friendly metadata for the UI; not part of the strict contract but
        # harmless and useful for the dashboard CTA copy.
        "meta": {
            "dataStatus": "demo",
            "notice": (
                "Demo trip — generated locally. "
                "Configure Traccar to see your real trips here."
            ),
            "tripCount": int(DEMO_STOPS),
            "source": "demo_seed",
        },
    }
    return payload


def _atomic_write_json(path: str, obj: dict) -> None:
    """Write ``obj`` as JSON to ``path`` atomically (write-temp + rename)."""
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=os.path.basename(path) + ".", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.unlink(tmp)
        except Exception:
            pass


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="demo_seed.py",
        description=(
            "Generate a local-only demo Trip Wrapped JSON payload. "
            "No Traccar required, no outbound HTTP."
        ),
    )
    p.add_argument(
        "--out",
        default="/config/www/roamcore/trip_wrapped/latest.json",
        help="Output JSON path (default: /config/www/roamcore/trip_wrapped/latest.json).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Use a /tmp default for --out and exit before touching the real "
            "RoamCore output dir. Useful for tests and CI."
        ),
    )
    p.add_argument(
        "--print",
        action="store_true",
        help="Print the generated JSON to stdout instead of writing to --out.",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if args.dry_run and args.out == "/config/www/roamcore/trip_wrapped/latest.json":
        args.out = "/tmp/rc_demo_trip_wrapped.json"

    payload = build_demo_payload()

    if args.print:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    _atomic_write_json(args.out, payload)
    # Print the result path on stdout for callers (e.g. the custom-component
    # service handler) that want to surface it back to the user.
    print(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())