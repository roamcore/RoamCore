#!/usr/bin/env python3

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone

try:
    # When executed as a module/package.
    from .build_wrapped import build_wrapped
    from .comparisons import compute_comparisons
    from .history import upsert_history
    from .render_html import render_html
    from .traccar_client import TraccarClient, TraccarError
except Exception:  # pragma: no cover
    # When executed as a standalone script.
    from build_wrapped import build_wrapped
    from comparisons import compute_comparisons
    from history import upsert_history
    from render_html import render_html
    from traccar_client import TraccarClient, TraccarError


def _merc_x(lon: float) -> float:
    return (lon + 180.0) / 360.0


def _merc_y(lat: float) -> float:
    import math

    s = math.sin(lat * math.pi / 180.0)
    y = 0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)
    return y


def _choose_zoom(points, w: int, h: int, pad: int = 48) -> tuple[int, float, float]:
    """Choose OSM zoom + center lat/lon to fit points."""
    import math

    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    cx = (min_lon + max_lon) / 2.0
    cy = (min_lat + max_lat) / 2.0

    # Clamp zoom search.
    best = 12
    for z in range(16, 3, -1):
        scale = 256 * (2**z)
        x1 = _merc_x(min_lon) * scale
        x2 = _merc_x(max_lon) * scale
        y1 = _merc_y(min_lat) * scale
        y2 = _merc_y(max_lat) * scale
        bw = abs(x2 - x1)
        bh = abs(y2 - y1)
        if bw <= max(1, (w - pad * 2)) and bh <= max(1, (h - pad * 2)):
            best = z
            break
    return best, cy, cx


def _build_staticmap_url(points: list[tuple[float, float]], w: int, h: int) -> str:
    import urllib.parse

    # Use staticmap.openstreetmap.de (mapnik) for labels/city names.
    # Path format is "color:0xRRGGBB|weight:N|lat,lon|lat,lon|...".
    z, c_lat, c_lon = _choose_zoom(points, w=w, h=h)

    # Reduce path points for URL length.
    # Keep URL length reasonable for hosted static map servers.
    max_pts = 70
    if len(points) > max_pts:
        step = max(1, int(len(points) / max_pts))
        pts = points[::step]
        if pts[-1] != points[-1]:
            pts.append(points[-1])
    else:
        pts = points

    path = "color:0x6EE7FF|weight:4" + "".join([f"|{lat:.5f},{lon:.5f}" for (lat, lon) in pts])
    qs = {
        "center": f"{c_lat:.5f},{c_lon:.5f}",
        "zoom": str(z),
        "size": f"{w}x{h}",
        "maptype": "mapnik",
        "path": path,
    }
    # PRIVACY: default to the local RoamCore tileserver add-on (loopback).
    # The legacy `staticmap.openstreetmap.de` fallback is retained as an
    # opt-in path via `input_text.rc_trip_opt_in_domains` (smoke-checked).
    base = os.environ.get(
        "RC_TRIP_STATICMAP_BASE",
        "http://localhost:8000/staticmap.php",
    )
    return base + "?" + urllib.parse.urlencode(qs)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", required=True)
    # Optional: if omitted (or passed as unknown/unavailable from HA templates),
    # we will fall back to /config/secrets.yaml (keys: roamcore_traccar_admin_email/password)
    p.add_argument("--username")
    p.add_argument("--password")
    p.add_argument(
        "--user-token",
        help="Traccar user token. If omitted, will try /config/secrets.yaml key roamcore_traccar_user_token.",
    )
    p.add_argument(
        "--no-ha-proxy",
        action="store_true",
        help="Disable the Home Assistant supervisor proxy fallback (useful for local dev).",
    )
    p.add_argument("--device-id", type=int, required=True)
    p.add_argument("--from", dest="from_ts", required=True)
    p.add_argument("--to", dest="to_ts", required=True)
    p.add_argument("--out-json", required=True)
    p.add_argument("--out-html", required=True)
    p.add_argument("--title", default="Trip Wrapped")
    p.add_argument(
        "--template",
        default="classic",
        choices=["classic", "story"],
        help="HTML template to render (classic single-card or story swipe-deck).",
    )
    p.add_argument(
        "--demo",
        action="store_true",
        help="Generate a demo Trip Wrapped (no Traccar required). Useful for UI previews.",
    )
    p.add_argument("--owner-name", help="Optional owner name used for auto-title (e.g. Emily)")
    p.add_argument(
        "--config-dir",
        default="/config",
        help="Home Assistant config dir (used for local trip history persistence).",
    )
    return p.parse_args()


def _load_secrets() -> dict[str, str]:
    try:
        p = "/config/secrets.yaml"
        if not os.path.exists(p):
            return {}
        with open(p, "r", encoding="utf-8") as f:
            text = f.read()
        import re

        out: dict[str, str] = {}
        for key in (
            "roamcore_traccar_admin_email",
            "roamcore_traccar_admin_password",
            "roamcore_traccar_user_token",
        ):
            m = re.search(rf"^{key}:\s*\"?([^\"\n]+)\"?$", text, re.M)
            if m:
                out[key] = m.group(1).strip()
        return out
    except Exception:
        return {}


def _norm(v: str | None) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s or s in ("unknown", "unavailable", "None"):
        return None
    return s


def main():
    a = parse_args()

    def _demo_payload(from_ts: str, to_ts: str):
        """Return (trips, journey_route, stops, top_trip_route) demo payload in Traccar-like shape."""
        from datetime import timedelta

        # Anchor demo times to the requested range so the UI shows sane day counts.
        try:
            t0 = datetime.fromisoformat(str(from_ts).replace("Z", "+00:00"))
        except Exception:
            t0 = datetime.now(timezone.utc) - timedelta(days=3)
        trips = [
            {
                "distance": 220_000,
                "duration": 2 * 60 * 60 * 1000 + 18 * 60 * 1000,
                "startTime": (t0 + timedelta(hours=9)).isoformat(),
                "endTime": (t0 + timedelta(hours=11, minutes=18)).isoformat(),
                "startAddress": "Santa Monica",
                "endAddress": "Palm Springs",
            },
            {
                "distance": 410_000,
                "duration": 4 * 60 * 60 * 1000 + 5 * 60 * 1000,
                "startTime": (t0 + timedelta(days=1, hours=8)).isoformat(),
                "endTime": (t0 + timedelta(days=1, hours=12, minutes=5)).isoformat(),
                "startAddress": "Palm Springs",
                "endAddress": "Grand Canyon Village",
            },
            {
                "distance": 530_000,
                "duration": 5 * 60 * 60 * 1000 + 25 * 60 * 1000,
                "startTime": (t0 + timedelta(days=2, hours=7)).isoformat(),
                "endTime": (t0 + timedelta(days=2, hours=12, minutes=25)).isoformat(),
                "startAddress": "Grand Canyon Village",
                "endAddress": "Albuquerque",
            },
            {
                "distance": 610_000,
                "duration": 6 * 60 * 60 * 1000 + 10 * 60 * 1000,
                "startTime": (t0 + timedelta(days=3, hours=6)).isoformat(),
                "endTime": (t0 + timedelta(days=3, hours=12, minutes=10)).isoformat(),
                "startAddress": "Albuquerque",
                "endAddress": "Denver",
            },
        ]

        # Stops report-like entries (duration in ms + address).
        stops = [
            {
                "startTime": (t0 + timedelta(hours=12)).isoformat(),
                "endTime": (t0 + timedelta(days=1, hours=7, minutes=30)).isoformat(),
                "duration": int(19.5 * 60 * 60 * 1000),
                "address": "Palm Springs",
            },
            {
                "startTime": (t0 + timedelta(days=1, hours=12, minutes=30)).isoformat(),
                "endTime": (t0 + timedelta(days=2, hours=6, minutes=30)).isoformat(),
                "duration": int(18.0 * 60 * 60 * 1000),
                "address": "Grand Canyon Village",
            },
            {
                "startTime": (t0 + timedelta(days=2, hours=12, minutes=40)).isoformat(),
                "endTime": (t0 + timedelta(days=3, hours=5, minutes=40)).isoformat(),
                "duration": int(17.0 * 60 * 60 * 1000),
                "address": "Albuquerque",
            },
            {
                "startTime": (t0 + timedelta(days=3, hours=12, minutes=20)).isoformat(),
                "endTime": (t0 + timedelta(days=3, hours=20, minutes=20)).isoformat(),
                "duration": int(8.0 * 60 * 60 * 1000),
                "address": "Denver",
            },
        ]

        # Journey route points (positions report-like)
        # Rough line: LA -> Palm Springs -> Grand Canyon -> Albuquerque -> Denver
        pts = [
            (34.0100, -118.4960, 30),
            (33.8303, -116.5453, 140),
            (36.0544, -112.1401, 2090),
            (35.0844, -106.6504, 1610),
            (39.7392, -104.9903, 1609),
        ]
        def lerp(a: float, b: float, t: float) -> float:
            return a + (b - a) * t

        journey = []
        samples_per_leg = 24
        idx = 0
        for (a_lat, a_lon, a_alt), (b_lat, b_lon, b_alt) in zip(pts, pts[1:]):
            for j in range(samples_per_leg):
                t = j / float(samples_per_leg)
                journey.append(
                    {
                        "latitude": lerp(a_lat, b_lat, t),
                        "longitude": lerp(a_lon, b_lon, t),
                        "altitude": lerp(a_alt, b_alt, t),
                        "deviceTime": (t0 + timedelta(minutes=idx * 18)).isoformat(),
                    }
                )
                idx += 1

        # Ensure final point included.
        journey.append(
            {
                "latitude": pts[-1][0],
                "longitude": pts[-1][1],
                "altitude": pts[-1][2],
                "deviceTime": (t0 + timedelta(minutes=idx * 18)).isoformat(),
            }
        )

        top_trip_route = journey[-(samples_per_leg + 1) :]
        return trips, journey, stops, top_trip_route

    user = _norm(a.username)
    pw = _norm(a.password)

    # Preferred (for RoamCore): use a Traccar user token (works even when the
    # email/password login endpoint is unavailable) so we don't need to store creds.
    trips = None
    pref_err = None

    # Demo mode: skip Traccar entirely.
    if a.demo:
        demo_trips, demo_journey, demo_stops, demo_top_trip_route = _demo_payload(a.from_ts, a.to_ts)
        wrapped = build_wrapped(
            title=a.title,
            device_id=a.device_id,
            from_ts=a.from_ts,
            to_ts=a.to_ts,
            trips=demo_trips,
            generated_at=datetime.now(timezone.utc).isoformat(),
            journey_route=demo_journey,
            top_trip_route=demo_top_trip_route,
            stops=demo_stops,
            map_image_url=None,
            owner_name=_norm(a.owner_name) or "You",
            comparisons={},
        )
        wrapped.setdefault("meta", {})
        wrapped["meta"]["dataStatus"] = "demo"
        wrapped["meta"]["notice"] = "Showing demo data. Turn off Demo Mode to use your real trip."

        # Generate a static map PNG (demo too), so the map box never looks empty.
        try:
            pts = []
            for p in wrapped.get("stats", {}).get("journeyRoute") or []:
                lat = p.get("lat")
                lon = p.get("lon")
                if lat is None or lon is None:
                    continue
                pts.append((float(lat), float(lon)))
            if len(pts) >= 2:
                map_url = _build_staticmap_url(pts, w=980, h=420)
                out_png = os.path.join(os.path.dirname(a.out_html), "latest_map.png")
                import urllib.request

                req = urllib.request.Request(map_url, headers={"User-Agent": "RoamCore-TripWrapped/0.1"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = resp.read()
                with open(out_png, "wb") as f:
                    f.write(data)
                wrapped["meta"]["mapImageUrl"] = "/local/roamcore/trip_wrapped/latest_map.png"
        except Exception:
            pass

        os.makedirs(os.path.dirname(a.out_json), exist_ok=True)
        os.makedirs(os.path.dirname(a.out_html), exist_ok=True)
        def _atomic_write_text(path: str, text: str):
            d = os.path.dirname(path)
            fd, tmp = tempfile.mkstemp(prefix=os.path.basename(path) + ".", dir=d)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(text)
                os.replace(tmp, path)
            finally:
                try:
                    if os.path.exists(tmp):
                        os.unlink(tmp)
                except Exception:
                    pass
        def _atomic_write_json(path: str, obj):
            _atomic_write_text(path, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
        _atomic_write_json(a.out_json, wrapped)
        _atomic_write_text(a.out_html, render_html(wrapped, template=a.template))
        return
    try:
        sec = _load_secrets()
        tok = _norm(a.user_token) or sec.get("roamcore_traccar_user_token")
        if tok:
            tok_client = TraccarClient.direct_user_token(base_url=a.base_url, user_token=tok)
            trips = tok_client.get_trips(device_id=a.device_id, from_ts=a.from_ts, to_ts=a.to_ts)
    except Exception as e:
        pref_err = e

    # Secondary preference: HA proxy (no direct token required)
    ha_client = None
    if trips is None and not a.no_ha_proxy:
        try:
            ha_client = TraccarClient.ha_supervisor_proxy(base_url="http://supervisor/core")
            # PRIVACY: loopback / supervisor proxy — stays inside HA core.
            trips = ha_client.get_trips(device_id=a.device_id, from_ts=a.from_ts, to_ts=a.to_ts)
        except Exception as e:
            pref_err = e

    export_notice = None

    if trips is None:
        # Fallback: direct Traccar Basic Auth using args or secrets.yaml
        if not (user and pw):
            sec = _load_secrets()
            user = user or sec.get("roamcore_traccar_admin_email")
            pw = pw or sec.get("roamcore_traccar_admin_password")
        if user and pw:
            client = TraccarClient.direct_basic(base_url=a.base_url, username=user, password=pw)
            trips = client.get_trips(device_id=a.device_id, from_ts=a.from_ts, to_ts=a.to_ts)
        else:
            # IMPORTANT (beta UX): do not hard-fail the export.
            # We still generate a valid Trip Wrapped HTML/JSON with a clear call-to-action.
            trips = []
            export_notice = (
                "Trip Wrapped couldn't connect to Traccar yet. "
                "To unlock seamless trip summaries, set roamcore_traccar_user_token in /config/secrets.yaml "
                "(recommended), or set input_text.rc_traccar_username/password (basic auth)."
            )

    # Best-effort: pull a full-journey route polyline (hero map) + stops report
    # for story metrics, plus a top-trip route (optional secondary).
    journey_route = None
    top_trip_route = None
    stops = None
    try:
        # Prefer HA proxy client if available (no creds), otherwise fall back to direct.
        try:
            if "tok_client" in locals() and tok_client:
                journey_route = tok_client.get_route(device_id=a.device_id, from_ts=a.from_ts, to_ts=a.to_ts)
                stops = tok_client.get_stops(device_id=a.device_id, from_ts=a.from_ts, to_ts=a.to_ts)
            elif ha_client:
                journey_route = ha_client.get_route(device_id=a.device_id, from_ts=a.from_ts, to_ts=a.to_ts)
                stops = ha_client.get_stops(device_id=a.device_id, from_ts=a.from_ts, to_ts=a.to_ts)
            elif "client" in locals() and client:
                journey_route = client.get_route(device_id=a.device_id, from_ts=a.from_ts, to_ts=a.to_ts)
                stops = client.get_stops(device_id=a.device_id, from_ts=a.from_ts, to_ts=a.to_ts)
        except Exception:
            journey_route = None
            stops = None

        if trips:
            top_trip = max(trips, key=lambda t: (t.get("distance") or 0, t.get("duration") or 0))
            if top_trip and top_trip.get("startTime") and top_trip.get("endTime"):
                try:
                    if "tok_client" in locals() and tok_client:
                        top_trip_route = tok_client.get_route(device_id=a.device_id, from_ts=top_trip.get("startTime"), to_ts=top_trip.get("endTime"))
                    elif ha_client:
                        top_trip_route = ha_client.get_route(device_id=a.device_id, from_ts=top_trip.get("startTime"), to_ts=top_trip.get("endTime"))
                except Exception:
                    if "client" in locals() and client:
                        top_trip_route = client.get_route(
                            device_id=a.device_id,
                            from_ts=top_trip.get("startTime"),
                            to_ts=top_trip.get("endTime"),
                        )
    except Exception:
        journey_route = None
        top_trip_route = None
        stops = None

    wrapped = build_wrapped(
        title=a.title,
        owner_name=_norm(a.owner_name),
        device_id=a.device_id,
        from_ts=a.from_ts,
        to_ts=a.to_ts,
        trips=trips,
        generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        journey_route=journey_route,
        top_trip_route=top_trip_route,
        stops=stops,
        map_image_url=None,
        comparisons={},
    )

    # Meta notices for better UX (avoid blank/"—" screens with no explanation).
    try:
        wrapped.setdefault("meta", {})
        if export_notice:
            wrapped["meta"]["notice"] = export_notice
            wrapped["meta"]["dataStatus"] = "needs_setup"
        else:
            # If we connected but got no usable trip/route data, surface a helpful message.
            has_trips = bool(wrapped.get("trips"))
            jr = (wrapped.get("stats", {}) or {}).get("journeyRoute") or []
            has_route = bool(jr)
            if not has_trips and not has_route:
                wrapped["meta"].setdefault(
                    "notice",
                    "No trip data found for this range yet. Try expanding the date range, "
                    "confirm the device ID, and ensure Traccar is connected.",
                )
                wrapped["meta"].setdefault("dataStatus", "no_data")
    except Exception:
        pass

    # Local, privacy-first comparisons vs past trips.
    try:
        history = upsert_history(config_dir=a.config_dir, wrapped=wrapped)
        wrapped["comparisons"] = compute_comparisons(history=history, wrapped=wrapped)
    except Exception:
        wrapped["comparisons"] = {"historyCount": 0, "records": {}, "vsAverage": {}, "insights": []}

    # Generate a static map PNG (non-interactive) and reference it from HTML.
    map_url = None
    try:
        pts = []
        for p in wrapped.get("stats", {}).get("journeyRoute") or []:
            lat = p.get("lat")
            lon = p.get("lon")
            if lat is None or lon is None:
                continue
            pts.append((float(lat), float(lon)))
        if len(pts) >= 2:
            map_url = _build_staticmap_url(pts, w=980, h=420)
            out_png = os.path.join(os.path.dirname(a.out_html), "latest_map.png")
            import urllib.request

            req = urllib.request.Request(
                map_url,
                headers={"User-Agent": "RoamCore-TripWrapped/0.1"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            with open(out_png, "wb") as f:
                f.write(data)
            wrapped["meta"]["mapImageUrl"] = "/local/roamcore/trip_wrapped/latest_map.png"
    except Exception:
        map_url = None

    os.makedirs(os.path.dirname(a.out_json), exist_ok=True)
    os.makedirs(os.path.dirname(a.out_html), exist_ok=True)

    # Atomic writes so /local/latest.html doesn't intermittently serve partial files.
    def _atomic_write_text(path: str, text: str):
        d = os.path.dirname(path)
        fd, tmp = tempfile.mkstemp(prefix=os.path.basename(path) + ".", dir=d)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(tmp, path)
        finally:
            try:
                if os.path.exists(tmp):
                    os.unlink(tmp)
            except Exception:
                pass

    def _atomic_write_json(path: str, obj):
        _atomic_write_text(path, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")

    _atomic_write_json(a.out_json, wrapped)
    _atomic_write_text(a.out_html, render_html(wrapped, template=a.template))


if __name__ == "__main__":
    try:
        main()
    except TraccarError as e:
        # Best-effort safety net: if a Traccar call raises late in the process,
        # surface the error but don't crash the whole export command.
        print(f"Trip Wrapped export warning: {e}", file=sys.stderr)
        raise SystemExit(0)
