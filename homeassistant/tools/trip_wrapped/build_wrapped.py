def _downsample(points, max_points=350):
    try:
        if not points:
            return []
        n = len(points)
        if n <= max_points:
            return points
        step = max(1, int(n / max_points))
        out = points[::step]
        # Ensure last point is included.
        if out and points[-1] is not out[-1]:
            out.append(points[-1])
        return out
    except Exception:
        return points or []


def build_wrapped(title, device_id, from_ts, to_ts, trips, generated_at, top_trip_route=None):
    total_distance_m = sum((t.get("distance") or 0) for t in (trips or []))
    total_duration_s = sum((t.get("duration") or 0) for t in (trips or []))

    def best_trip_key(t):
        return (t.get("distance") or 0, t.get("duration") or 0)

    top_trip = max(trips, key=best_trip_key) if trips else None

    # Optional: include a simplified route polyline for the top trip.
    # Keep payload bounded so the HTML remains lightweight and shareable.
    route = []
    if top_trip_route:
        try:
            route = [
                {
                    "lat": p.get("latitude"),
                    "lon": p.get("longitude"),
                }
                for p in (top_trip_route or [])
                if p and p.get("latitude") is not None and p.get("longitude") is not None
            ]
            route = _downsample(route, max_points=350)
        except Exception:
            route = []

    return {
        "meta": {
            "title": title,
            "deviceId": device_id,
            "from": from_ts,
            "to": to_ts,
            "generatedAt": generated_at,
            "tripCount": len(trips or []),
        },
        "stats": {
            "totalDistanceM": total_distance_m,
            "totalDurationS": total_duration_s,
            "topTrip": top_trip,
            "topTripRoute": route,
        },
        # Keep raw trips for MVP (HTML renders these directly)
        "trips": trips or [],
    }
