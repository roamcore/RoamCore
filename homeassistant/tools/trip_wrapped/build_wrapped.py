def build_wrapped(title, device_id, from_ts, to_ts, trips, generated_at):
    total_distance_m = sum((t.get("distance") or 0) for t in (trips or []))
    total_duration_s = sum((t.get("duration") or 0) for t in (trips or []))

    def best_trip_key(t):
        return (t.get("distance") or 0, t.get("duration") or 0)

    top_trip = max(trips, key=best_trip_key) if trips else None

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
        },
        # Keep raw trips for MVP (HTML renders these directly)
        "trips": trips or [],
    }

