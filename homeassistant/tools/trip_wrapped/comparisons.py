"""Deterministic local comparisons for Trip Wrapped.

All logic is:
- privacy-first (uses only persisted local summaries)
- deterministic (no randomness, stable thresholds)
- resilient (works when history is empty or partial)

The history store lives in :mod:`trip_wrapped.history`.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .history import TripSummary, summarize_wrapped


def _mean(nums: list[float]) -> float | None:
    try:
        xs = [float(x) for x in nums if x is not None]
        xs = [x for x in xs if x == x]  # drop NaN
        if not xs:
            return None
        return sum(xs) / float(len(xs))
    except Exception:
        return None


def _days_from_ms(ms: int) -> int:
    try:
        ms = int(ms or 0)
        if ms <= 0:
            return 1
        # Keep consistent with build_wrapped's rough rounding.
        return max(1, round(ms / (1000 * 60 * 60 * 24)))
    except Exception:
        return 1


def _pct(v: float | None) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def classify_traveller(s: TripSummary) -> dict[str, Any]:
    """Return a simple deterministic traveller-type classification."""

    days = _days_from_ms(s.total_duration_ms)
    km = (float(s.total_distance_m or 0.0) / 1000.0) if s.total_distance_m else 0.0
    km_per_day = km / float(days) if days else km
    pct_stationary = _pct(s.percent_stationary)

    stops = int(s.number_of_stops or 0)
    stops_per_day = stops / float(days) if days else float(stops)

    # Thresholds are intentionally simple and story-friendly.
    # Ordering matters: first match wins.
    if km_per_day >= 250.0 or float(s.longest_drive_hours or 0.0) >= 6.0:
        t = {
            "type": "road_warrior",
            "label": "Road Warrior",
            "blurb": "Long driving days and big mileage — you cover ground.",
        }
    elif pct_stationary is not None and pct_stationary >= 75.0 and stops_per_day <= 0.6:
        t = {
            "type": "basecamper",
            "label": "Basecamper",
            "blurb": "You like to settle in — fewer moves, longer stays.",
        }
    elif stops_per_day >= 2.0 or (s.avg_stop_hours and s.avg_stop_hours > 0 and s.avg_stop_hours <= 8.0):
        t = {
            "type": "hopper",
            "label": "Stop Hopper",
            "blurb": "You keep things moving with lots of short stops.",
        }
    elif pct_stationary is not None and pct_stationary <= 40.0 and stops >= 4:
        t = {
            "type": "nomad",
            "label": "Nomad Mode",
            "blurb": "More time moving than parked — classic roaming energy.",
        }
    else:
        t = {
            "type": "balanced",
            "label": "Balanced Traveller",
            "blurb": "A healthy mix of driving and downtime.",
        }

    # Include computed features for potential UI use (kept small).
    t["features"] = {
        "days": days,
        "km": km,
        "kmPerDay": km_per_day,
        "stopsPerDay": stops_per_day,
        "percentStationary": pct_stationary,
    }
    return t


def compute_comparisons(
    wrapped: dict[str, Any],
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute 4–5 local comparison insights against persisted history.

    Returns a JSON-serializable dict suitable for embedding in `wrapped["comparisons"]`.
    """

    cur = summarize_wrapped(wrapped)
    past = [t for t in (history or []) if str(t.get("trip_id")) != cur.trip_id]

    # Materialize past summaries (best-effort; skip bad entries).
    past_summaries: list[TripSummary] = []
    for t in past:
        try:
            past_summaries.append(TripSummary(**t))
        except Exception:
            continue

    out: dict[str, Any] = {
        "historyCount": max(0, len(past_summaries)),
        "travellerType": classify_traveller(cur),
        "insights": [],
    }

    # Graceful for brand new users.
    if not past_summaries:
        out["insights"].append(
            {
                "kind": "getting_started",
                "title": "First Trip Wrapped",
                "body": "This is your first Trip Wrapped on this device. Future wraps will include comparisons and personal records.",
            }
        )
        return out

    # ---------- Record-based insights ----------
    def _record(metric: str, cur_v: float, higher_is_better: bool = True) -> dict[str, Any] | None:
        vals = []
        for ps in past_summaries:
            try:
                v = float(getattr(ps, metric) or 0.0)
                vals.append(v)
            except Exception:
                continue
        if not vals:
            return None
        best = max(vals) if higher_is_better else min(vals)
        is_record = (cur_v > best) if higher_is_better else (cur_v < best)
        if not is_record:
            return None
        return {
            "kind": "record",
            "metric": metric,
            "title": "Personal record",
            "body": "New best for this metric compared to your previous Trip Wrapped history.",
            "value": cur_v,
            "previousBest": best,
        }

    # Try a couple of record candidates; keep output bounded.
    r1 = _record("total_distance_m", float(cur.total_distance_m or 0.0), higher_is_better=True)
    if r1:
        r1["title"] = "Longest trip yet"
        r1["body"] = "This Trip Wrapped covers more distance than any of your previous wraps."
        out["insights"].append(r1)

    r2 = _record("longest_drive_hours", float(cur.longest_drive_hours or 0.0), higher_is_better=True)
    if r2 and len(out["insights"]) < 2:
        r2["title"] = "Longest single drive yet"
        r2["body"] = "Your longest drive on this wrap is a new personal best."
        out["insights"].append(r2)

    # ---------- Versus-average insight ----------
    avg_dist = _mean([ps.total_distance_m for ps in past_summaries])
    if avg_dist and avg_dist > 0:
        ratio = float(cur.total_distance_m or 0.0) / float(avg_dist)
        if ratio >= 1.25:
            out["insights"].append(
                {
                    "kind": "vs_average",
                    "metric": "total_distance_m",
                    "title": "Above your average distance",
                    "body": "This wrap covered significantly more distance than your historical average.",
                    "ratio": ratio,
                    "average": avg_dist,
                    "value": float(cur.total_distance_m or 0.0),
                }
            )
        elif ratio <= 0.75:
            out["insights"].append(
                {
                    "kind": "vs_average",
                    "metric": "total_distance_m",
                    "title": "Below your average distance",
                    "body": "This wrap was a lighter mileage period than your historical average.",
                    "ratio": ratio,
                    "average": avg_dist,
                    "value": float(cur.total_distance_m or 0.0),
                }
            )

    # ---------- Behaviour shift insight ----------
    # Compare stationary % where available; otherwise use avg stop hours.
    past_pct = [
        float(ps.percent_stationary)
        for ps in past_summaries
        if ps.percent_stationary is not None
    ]
    cur_pct = _pct(cur.percent_stationary)
    if cur_pct is not None and past_pct:
        avg_pct = _mean(past_pct)
        if avg_pct is not None:
            delta = float(cur_pct) - float(avg_pct)
            if abs(delta) >= 15.0:
                out["insights"].append(
                    {
                        "kind": "behaviour_shift",
                        "metric": "percent_stationary",
                        "title": "More downtime" if delta > 0 else "More time on the move",
                        "body": (
                            "You spent a bigger share of time parked than usual."
                            if delta > 0
                            else "You spent a bigger share of time moving than usual."
                        ),
                        "deltaPoints": delta,
                        "average": avg_pct,
                        "value": cur_pct,
                    }
                )
    else:
        avg_stop = _mean([float(ps.avg_stop_hours or 0.0) for ps in past_summaries if ps.avg_stop_hours])
        cur_stop = float(cur.avg_stop_hours or 0.0)
        if avg_stop and avg_stop > 0 and cur_stop > 0:
            ratio = cur_stop / avg_stop
            if ratio >= 1.35 or ratio <= 0.65:
                out["insights"].append(
                    {
                        "kind": "behaviour_shift",
                        "metric": "avg_stop_hours",
                        "title": "Longer stops" if ratio >= 1.35 else "Shorter stops",
                        "body": (
                            "Your average stop was longer than usual."
                            if ratio >= 1.35
                            else "Your average stop was shorter than usual."
                        ),
                        "ratio": ratio,
                        "average": avg_stop,
                        "value": cur_stop,
                    }
                )

    # Keep insights bounded (4–5). Prefer record + average + behaviour.
    # If we still have <4, add a stable "rank" insight for distance.
    if len(out["insights"]) < 4:
        try:
            d_cur = float(cur.total_distance_m or 0.0)
            ds = [float(ps.total_distance_m or 0.0) for ps in past_summaries] + [d_cur]
            ds_sorted = sorted(ds, reverse=True)
            rank = ds_sorted.index(d_cur) + 1
            out["insights"].append(
                {
                    "kind": "rank",
                    "metric": "total_distance_m",
                    "title": "Distance rank",
                    "body": f"This wrap ranks #{rank} by distance in your local Trip Wrapped history.",
                    "rank": rank,
                    "count": len(ds_sorted),
                }
            )
        except Exception:
            pass

    out["insights"] = out["insights"][:5]
    out["currentSummary"] = asdict(cur)
    return out
