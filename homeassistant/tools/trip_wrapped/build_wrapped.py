def _downsample(points, max_points=350):
    try:
        if not points:
            return []
        n = len(points)
        if n <= max_points:
            return points
        # Use a ceiling-ish step so we actually reduce when n is only slightly
        # above max_points (e.g. 1000 -> 900).
        step = max(1, int((n + max_points - 1) / max_points))
        out = points[::step]
        # Ensure last point is included.
        if out and points[-1] is not out[-1]:
            out.append(points[-1])
        return out
    except Exception:
        return points or []


def _parse_dt(s: str):
    # Accept: 2026-03-20T14:00:00Z, 2026-03-20T14:00:00+00:00, etc.
    from datetime import datetime, timezone

    if not s:
        return None
    ss = str(s).strip()
    if ss.endswith("Z"):
        ss = ss[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(ss)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _ms(v):
    try:
        return int(float(v))
    except Exception:
        return 0


def _m(v):
    try:
        return float(v)
    except Exception:
        return 0.0


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    import math

    try:
        r = 6371.0
        p1 = math.radians(float(lat1))
        p2 = math.radians(float(lat2))
        dlat = math.radians(float(lat2) - float(lat1))
        dlon = math.radians(float(lon2) - float(lon1))
        a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return r * c
    except Exception:
        return 0.0


def build_wrapped(
    title,
    device_id,
    from_ts,
    to_ts,
    trips,
    generated_at,
    journey_route=None,
    top_trip_route=None,
    stops=None,
    map_image_url=None,
):
    trips = trips or []
    total_distance_m = sum(_m(t.get("distance")) for t in trips)
    # Traccar report durations are in milliseconds.
    moving_duration_ms = sum(_ms(t.get("duration")) for t in trips)

    dt_from = _parse_dt(from_ts)
    dt_to = _parse_dt(to_ts)
    total_duration_ms = 0
    if dt_from and dt_to:
        total_duration_ms = max(0, int((dt_to - dt_from).total_seconds() * 1000))

    def best_trip_key(t):
        return (t.get("distance") or 0, t.get("duration") or 0)

    top_trip = max(trips, key=best_trip_key) if trips else None

    # --- Stops + longest stop ---
    stops = stops or []
    # Traccar stops report returns entries with startTime/endTime/duration(ms).
    number_of_stops = len(stops) if stops else len(trips)

    longest_stop_ms = 0
    longest_stop_name = None
    stationary_duration_ms = 0
    if stops:
        for s in stops:
            if not s:
                continue
            dur = _ms(s.get("duration"))
            stationary_duration_ms += max(0, dur)
            if dur > longest_stop_ms:
                longest_stop_ms = dur
                longest_stop_name = s.get("address") or None
    else:
        # Fallback: estimate stops from gaps between trips.
        if len(trips) >= 2:
            def _k(t):
                d = _parse_dt(t.get("startTime") or "")
                return d.timestamp() if d else 0
            ordered = sorted(trips, key=_k)
            for prev, nxt in zip(ordered, ordered[1:]):
                prev_end = _parse_dt(prev.get("endTime") or "")
                nxt_start = _parse_dt(nxt.get("startTime") or "")
                if not (prev_end and nxt_start):
                    continue
                gap_ms = int((nxt_start - prev_end).total_seconds() * 1000)
                if gap_ms > longest_stop_ms:
                    longest_stop_ms = gap_ms
                    longest_stop_name = prev.get("endAddress") or nxt.get("startAddress")

    # --- Behaviour metrics ---
    longest_drive_m = max((_m(t.get("distance")) for t in trips), default=0.0)
    longest_drive_ms = max((_ms(t.get("duration")) for t in trips), default=0)
    total_days = 0
    if total_duration_ms:
        total_days = max(1, round(total_duration_ms / (1000 * 60 * 60 * 24)))
    avg_days_per_stop = None
    if total_days and number_of_stops:
        try:
            avg_days_per_stop = float(total_days) / float(number_of_stops)
        except Exception:
            avg_days_per_stop = None

    moving_hours = moving_duration_ms / (1000 * 60 * 60) if moving_duration_ms else 0.0
    total_hours = total_duration_ms / (1000 * 60 * 60) if total_duration_ms else 0.0
    if stationary_duration_ms > 0:
        stationary_hours = stationary_duration_ms / (1000 * 60 * 60)
    else:
        stationary_hours = max(0.0, total_hours - moving_hours)
    percent_stationary = None
    if total_hours > 0:
        percent_stationary = (stationary_hours / total_hours) * 100.0

    total_distance_km = total_distance_m / 1000.0 if total_distance_m else 0.0
    avg_daily_distance_km = None
    if total_days and total_distance_km:
        try:
            avg_daily_distance_km = total_distance_km / float(total_days)
        except Exception:
            avg_daily_distance_km = None

    avg_speed_kph = None
    if moving_hours and moving_hours > 0 and total_distance_km > 0:
        avg_speed_kph = total_distance_km / moving_hours

    nights_parked = None
    if stationary_hours and stationary_hours > 0:
        try:
            nights_parked = int(round(stationary_hours / 24.0))
        except Exception:
            nights_parked = None

    avg_stop_hours = None
    if stops:
        try:
            avg_stop_hours = (stationary_duration_ms / (1000 * 60 * 60)) / float(len(stops))
        except Exception:
            avg_stop_hours = None

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

    journey = []
    if journey_route:
        try:
            journey = [
                {"lat": p.get("latitude"), "lon": p.get("longitude")}
                for p in (journey_route or [])
                if p and p.get("latitude") is not None and p.get("longitude") is not None
            ]
            journey = _downsample(journey, max_points=900)
        except Exception:
            journey = []

    # Start/end displacement + loopiness (story-friendly)
    displacement_km = None
    loopiness = None
    if journey and len(journey) >= 2:
        try:
            a = journey[0]
            b = journey[-1]
            displacement_km = _haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
            if displacement_km and displacement_km > 0:
                loopiness = (total_distance_km / displacement_km) if total_distance_km else None
        except Exception:
            displacement_km = None
            loopiness = None

    return {
        "meta": {
            "title": title,
            "deviceId": device_id,
            "from": from_ts,
            "to": to_ts,
            "generatedAt": generated_at,
            "tripCount": len(trips or []),
            "mapImageUrl": map_image_url,
        },
        "stats": {
            # Primary headline metrics
            "totalDistanceM": total_distance_m,
            "totalDays": total_days,
            "numberOfStops": number_of_stops,

            # Behaviour metrics
            "avgDaysPerStop": avg_days_per_stop,
            "longestDriveM": longest_drive_m,
            "longestDriveHours": (longest_drive_ms / (1000 * 60 * 60)) if longest_drive_ms else 0.0,
            "longestStopDurationMs": longest_stop_ms,
            "longestStopLocationName": longest_stop_name,

            # Fun / shareable
            "movingHours": moving_hours,
            "stationaryHours": stationary_hours,
            "totalHours": total_hours,
            "percentStationary": percent_stationary,

            "totalDistanceKm": total_distance_km,
            "avgDailyDistanceKm": avg_daily_distance_km,
            "avgSpeedKph": avg_speed_kph,
            "nightsParked": nights_parked,
            "avgStopHours": avg_stop_hours,

            "displacementKm": displacement_km,
            "loopiness": loopiness,

            # Route(s)
            "journeyRoute": journey,
            "topTrip": top_trip,
            "topTripRoute": route,
        },
        # Keep raw trips for MVP (HTML renders these directly)
        "trips": trips or [],
    }
