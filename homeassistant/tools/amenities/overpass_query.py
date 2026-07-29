#!/usr/bin/env python3
"""RoamCore Amenities overlay — Overpass query helper (slice #22).

Given a (lat, lon, radius_km) and a list of amenity categories, build an
Overpass QL query and write a JSON file describing nearby Points Of
Interest (POIs). This script is the data source for the
**iOverlander-style** amenities overlay on the RoamCore Map page.

This module is **stdlib-only** (no third-party imports) and is
intentionally safe to import without performing any network I/O. Real
Overpass calls are gated behind a ``--query`` flag; the default
``--dry-run`` mode emits a deterministic fixture so smoke checks can
validate the contract without ever touching the public Overpass API.

Privacy contract
----------------
- The helper is fully **off** by default — the YAML wiring that calls
  this script is also opt-in (``input_boolean.rc_amenities_overlay_enabled``).
- The default Overpass URL is the public ``overpass-api.de`` endpoint.
  It is annotated ``# PRIVACY-OPTIN:`` in the YAML so the privacy smoke
  check accepts it. Operators can switch to a self-hosted Overpass by
  editing ``input_text.rc_amenities_overpass_url``.
- This file contains a single outbound URL (``overpass-api.de``). It
  must remain annotated on the line that names it; the privacy smoke
  check enforces that.

Output shape
------------
A JSON object with these top-level keys (matching the acceptance
contract):

- ``generatedAt``  : ISO-8601 UTC timestamp.
- ``lat``          : float, the input latitude.
- ``lon``          : float, the input longitude.
- ``radiusKm``     : float, the input radius in km.
- ``categories``   : list[str], the categories actually queried.
- ``pois``         : list of objects, each with ``id`` (str), ``category``
                      (str), ``name`` (str), ``lat`` (float), ``lon`` (float),
                      ``tags`` (dict[str,str]), and ``distanceKm`` (float).

Usage
-----
::

    python3 overpass_query.py --dry-run --lat 36.0 --lon -111.0 --out /tmp/rc_amenities.json
    python3 overpass_query.py --query --lat 36.0 --lon -111.0 --radius-km 5 --out /config/www/roamcore/amenities/latest.json
    python3 overpass_query.py --print --dry-run

Design notes
------------
- Stdlib-only (matches the slice #21 ``demo_seed.py`` pattern).
- The fixture POIs are deterministic: one POI per default category,
  placed on a small ring around the input point so the slice always
  renders something for the smoke check.
- ``--query`` requires ``urllib.request`` at runtime; that import is
  scoped to ``main()`` so importing the module never opens a socket.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
from datetime import datetime, timezone


# --- Overpass endpoint (annotated; privacy smoke check requires it) ---
# PRIVACY-OPTIN: public Overpass instance (overpass-api.de) — the default
# but operator-overridable via input_text.rc_amenities_overpass_url. The
# privacy smoke check accepts this annotation.
DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter"  # PRIVACY-OPTIN


# --- Category → OSM tag mapping ---
# Mirrors the top-level buckets iOverlander uses. Kept intentionally
# small so the Overpass query stays simple and the JS legend has
# exactly 6 chips. Each entry is a list of ``key=value`` tag predicates
# that Overpass understands in a union statement.
CATEGORY_TAGS: dict[str, list[str]] = {
    "water": [
        "amenity=drinking_water",
        "man_made=water_tap",
        "amenity=water_point",
    ],
    "dump_station": [
        "amenity=sanitary_dump_station",
    ],
    "laundry": [
        "shop=laundry",
        "shop=laundrette",
    ],
    "campground": [
        "tourism=camp_site",
        "tourism=caravan_site",
        "leisure=park",  # permissive fallback for free overnight parking
    ],
    "supermarket": [
        "shop=supermarket",
        "shop=convenience",
    ],
    "gym": [
        "leisure=fitness_centre",
        "leisure=sports_centre",
    ],
}

DEFAULT_CATEGORIES: list[str] = list(CATEGORY_TAGS.keys())


# --- Color palette (kept in sync with the JS RcAmenitiesLayer) ---
CATEGORY_COLORS: dict[str, str] = {
    "water": "#1d6fe0",        # blue
    "dump_station": "#4b5563",  # dark-grey
    "laundry": "#0d9488",       # teal
    "campground": "#15803d",    # green
    "supermarket": "#ea580c",   # orange
    "gym": "#dc2626",           # red
}


# ---------------------------------------------------------------------------
# Geometry helpers (no third-party deps)
# ---------------------------------------------------------------------------

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two (lat, lon) points."""
    r = 6371.0088  # mean Earth radius (km)
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def _offset_point(lat: float, lon: float, d_km: float, bearing_deg: float) -> tuple[float, float]:
    """Return (lat, lon) ``d_km`` away from ``lat,lon`` along ``bearing_deg``."""
    r = 6371.0088
    br = math.radians(bearing_deg)
    phi1 = math.radians(lat)
    lam1 = math.radians(lon)
    dr = d_km / r
    phi2 = math.asin(
        math.sin(phi1) * math.cos(dr) + math.cos(phi1) * math.sin(dr) * math.cos(br)
    )
    lam2 = lam1 + math.atan2(
        math.sin(br) * math.sin(dr) * math.cos(phi1),
        math.cos(dr) - math.sin(phi1) * math.sin(phi2),
    )
    # Normalize lon to [-180, 180]
    lon2 = (math.degrees(lam2) + 540.0) % 360.0 - 180.0
    return math.degrees(phi2), lon2


# ---------------------------------------------------------------------------
# Overpass QL builder
# ---------------------------------------------------------------------------

def build_overpass_query(lat: float, lon: float, radius_km: float, categories: list[str]) -> str:
    """Return an Overpass QL string for the requested categories.

    Unknown categories are skipped (the smoke check asserts only default
    categories are used; this is also a graceful-degradation path if
    an operator types a typo into ``input_select.rc_amenities_categories``).
    """
    radius_m = max(50.0, radius_km * 1000.0)
    blocks: list[str] = []
    for cat in categories:
        preds = CATEGORY_TAGS.get(cat)
        if not preds:
            continue
        # OR-join the tag predicates; Overpass interprets them as a union.
        joined = " | ".join(f'["{p}"]' for p in preds)
        blocks.append(
            f'  node{joined}(around:{radius_m:.1f},{lat:.6f},{lon:.6f});'
        )
    if not blocks:
        return ""
    header = "[out:json][timeout:25];\n(\n"
    footer = "\n);\nout body;\n>;\nout skel qt;\n"
    return header + "\n".join(blocks) + footer


# ---------------------------------------------------------------------------
# Fixture (dry-run) POI generation — deterministic, no network
# ---------------------------------------------------------------------------

# Pretty display names per category for the dry-run fixture.
CATEGORY_FIXTURE_NAMES: dict[str, str] = {
    "water": "Demo Water Tap",
    "dump_station": "Demo Dump Station",
    "laundry": "Demo Laundrette",
    "campground": "Demo Campsite",
    "supermarket": "Demo Supermarket",
    "gym": "Demo Gym",
}


def build_fixture_payload(lat: float, lon: float, radius_km: float, categories: list[str]) -> dict:
    """Return a deterministic ``pois`` list with one POI per category.

    Used by ``--dry-run`` so the smoke check can validate the schema
    without hitting Overpass. Each POI sits on a 0.5 km ring around
    ``(lat, lon)`` at evenly spaced bearings so the fixture looks
    realistic in the slice screenshots.
    """
    cats = [c for c in categories if c in CATEGORY_TAGS]
    if not cats:
        cats = list(DEFAULT_CATEGORIES)
    n = len(cats)
    pois: list[dict] = []
    for i, cat in enumerate(cats):
        bearing = (360.0 / max(n, 1)) * i
        plat, plon = _offset_point(lat, lon, 0.5, bearing)
        name = CATEGORY_FIXTURE_NAMES.get(cat, f"Demo {cat}")
        pois.append({
            "id": f"fixture-{cat}",
            "category": cat,
            "name": name,
            "lat": round(plat, 6),
            "lon": round(plon, 6),
            "tags": {
                "fixture": "true",
                "category": cat,
                "color": CATEGORY_COLORS.get(cat, "#888888"),
            },
            "distanceKm": round(_haversine_km(lat, lon, plat, plon), 3),
        })
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "lat": float(lat),
        "lon": float(lon),
        "radiusKm": float(radius_km),
        "categories": cats,
        "pois": pois,
    }


# ---------------------------------------------------------------------------
# Live Overpass call (only when --query is requested)
# ---------------------------------------------------------------------------

def _run_overpass(query: str, endpoint: str) -> list[dict]:
    """POST ``query`` to ``endpoint`` and return the ``elements`` list.

    Imports ``urllib.request`` lazily so importing this module never
    opens a socket.
    """
    import urllib.request
    import urllib.parse

    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=data,
        headers={"User-Agent": "RoamCore-AmenitiesOverlay/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
    obj = json.loads(body)
    return obj.get("elements") or []


def _elements_to_pois(elements: list[dict], center_lat: float, center_lon: float) -> list[dict]:
    """Translate raw Overpass ``elements`` into our ``pois`` contract."""
    out: list[dict] = []
    for el in elements:
        if not isinstance(el, dict):
            continue
        if el.get("type") != "node":
            # Skip ways/relations for the MVP; iOverlander-style POIs
            # are mostly nodes anyway.
            continue
        lat = el.get("lat")
        lon = el.get("lon")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            continue
        tags = el.get("tags") or {}
        name = str(tags.get("name") or tags.get("operator") or "Unnamed")
        # Best-effort category derivation: first matching tag wins.
        category = "other"
        for cat, preds in CATEGORY_TAGS.items():
            for p in preds:
                k, _, v = p.partition("=")
                if tags.get(k) == v:
                    category = cat
                    break
            if category != "other":
                break
        out.append({
            "id": f"{el.get('type','node')}/{el.get('id','')}",
            "category": category,
            "name": name,
            "lat": float(lat),
            "lon": float(lon),
            "tags": {str(k): str(v) for k, v in tags.items()},
            "distanceKm": round(_haversine_km(center_lat, center_lon, float(lat), float(lon)), 3),
        })
    # Stable ordering: nearest first.
    out.sort(key=lambda p: p["distanceKm"])
    return out


# ---------------------------------------------------------------------------
# Payload assembly + atomic write
# ---------------------------------------------------------------------------

def build_payload(
    lat: float,
    lon: float,
    radius_km: float,
    categories: list[str],
    *,
    query: bool = False,
    overpass_url: str | None = None,
) -> dict:
    """Return the amenities JSON payload (no I/O).

    With ``query=False`` (default) this is a deterministic fixture.
    With ``query=True`` this performs a live Overpass call.
    """
    cats = [c for c in categories if c in CATEGORY_TAGS] or list(DEFAULT_CATEGORIES)
    if not query:
        return build_fixture_payload(lat, lon, radius_km, cats)

    ql = build_overpass_query(lat, lon, radius_km, cats)
    if not ql:
        return build_fixture_payload(lat, lon, radius_km, cats)
    endpoint = overpass_url or DEFAULT_OVERPASS_URL
    elements = _run_overpass(ql, endpoint)
    pois = _elements_to_pois(elements, lat, lon)
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "lat": float(lat),
        "lon": float(lon),
        "radiusKm": float(radius_km),
        "categories": cats,
        "pois": pois,
    }


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


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="overpass_query.py",
        description=(
            "RoamCore Amenities overlay helper. Stdlib-only by default; "
            "use --query to perform a live Overpass call."
        ),
    )
    p.add_argument("--lat", type=float, required=True, help="Latitude (decimal degrees).")
    p.add_argument("--lon", type=float, required=True, help="Longitude (decimal degrees).")
    p.add_argument("--radius-km", type=float, default=5.0, help="Search radius in km (default: 5).")
    p.add_argument(
        "--categories",
        default=",".join(DEFAULT_CATEGORIES),
        help="Comma-separated categories (default: all six).",
    )
    p.add_argument(
        "--out",
        default="/config/www/roamcore/amenities/latest.json",
        help="Output JSON path (default: /config/www/roamcore/amenities/latest.json).",
    )
    p.add_argument(
        "--overpass-url",
        default=DEFAULT_OVERPASS_URL,
        help=(
            "Overpass endpoint URL. "
            f"Default: {DEFAULT_OVERPASS_URL} (annotated # PRIVACY-OPTIN:)."
        ),
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Emit the deterministic fixture JSON (no network).",
    )
    p.add_argument(
        "--query",
        action="store_true",
        help="Perform a live Overpass call (default off; requires network).",
    )
    p.add_argument(
        "--print",
        action="store_true",
        help="Print the JSON payload to stdout instead of writing --out.",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if args.dry_run and args.out == "/config/www/roamcore/amenities/latest.json":
        args.out = "/tmp/rc_amenities_overlay.json"

    cats = [c.strip() for c in (args.categories or "").split(",") if c.strip()]

    payload = build_payload(
        lat=args.lat,
        lon=args.lon,
        radius_km=args.radius_km,
        categories=cats,
        query=args.query,
        overpass_url=args.overpass_url,
    )

    if args.print:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    _atomic_write_json(args.out, payload)
    # Print the resulting path so HA shell_command wrappers can surface it.
    print(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
