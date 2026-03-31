import unittest


import os
import sys


HERE = os.path.dirname(__file__)
PKG_PARENT = os.path.abspath(os.path.join(HERE, "..", ".."))
if PKG_PARENT not in sys.path:
    sys.path.insert(0, PKG_PARENT)


from trip_wrapped.comparisons import compute_comparisons
from trip_wrapped.history import upsert_history


def _wrapped(
    *,
    device_id=1,
    from_ts="2026-03-01T00:00:00Z",
    to_ts="2026-03-02T00:00:00Z",
    total_distance_m=100_000.0,
    total_duration_ms=24 * 60 * 60 * 1000,
    number_of_stops=2,
    longest_drive_hours=2.0,
    avg_stop_hours=10.0,
    percent_stationary=70.0,
):
    return {
        "meta": {
            "deviceId": device_id,
            "from": from_ts,
            "to": to_ts,
            "generatedAt": "2026-03-03T00:00:00Z",
        },
        "stats": {
            "totalDistanceM": total_distance_m,
            "totalDurationMs": total_duration_ms,
            "numberOfStops": number_of_stops,
            "longestDriveM": total_distance_m / 2.0,
            "longestDriveHours": longest_drive_hours,
            "longestStopDurationMs": int(avg_stop_hours * 60 * 60 * 1000),
            "avgStopHours": avg_stop_hours,
            "percentStationary": percent_stationary,
        },
        "trips": [],
        "comparisons": {},
    }


class TestComparisons(unittest.TestCase):
    def test_new_user_graceful(self):
        # No past trips: should include a getting-started insight and traveller type.
        w = _wrapped(total_distance_m=50_000.0)
        comps = compute_comparisons(wrapped=w, history=[])
        self.assertIn("travellerType", comps)
        self.assertGreaterEqual(len(comps.get("insights") or []), 1)
        self.assertEqual(comps["insights"][0]["kind"], "getting_started")

    def test_record_vs_average_and_shift(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            # Persist two past wraps, then compute comparisons for a new one.
            past1 = _wrapped(
                from_ts="2026-01-01T00:00:00Z",
                to_ts="2026-01-02T00:00:00Z",
                total_distance_m=100_000.0,
                percent_stationary=85.0,
                longest_drive_hours=2.0,
            )
            past2 = _wrapped(
                from_ts="2026-02-01T00:00:00Z",
                to_ts="2026-02-02T00:00:00Z",
                total_distance_m=200_000.0,
                percent_stationary=80.0,
                longest_drive_hours=3.0,
            )
            upsert_history(config_dir=d, wrapped=past1)
            hist = upsert_history(config_dir=d, wrapped=past2)

            cur = _wrapped(
                from_ts="2026-03-01T00:00:00Z",
                to_ts="2026-03-02T00:00:00Z",
                total_distance_m=320_000.0,
                percent_stationary=30.0,
                longest_drive_hours=7.0,
                number_of_stops=5,
                avg_stop_hours=4.0,
            )
            hist2 = upsert_history(config_dir=d, wrapped=cur)
            comps = compute_comparisons(wrapped=cur, history=hist2)

            kinds = {i.get("kind") for i in comps.get("insights") or []}
            self.assertIn("record", kinds)
            self.assertIn("vs_average", kinds)
            self.assertIn("behaviour_shift", kinds)

            # Traveller type should be stable and match the high-mileage / long drive.
            self.assertEqual(comps["travellerType"]["type"], "road_warrior")


if __name__ == "__main__":
    unittest.main()

