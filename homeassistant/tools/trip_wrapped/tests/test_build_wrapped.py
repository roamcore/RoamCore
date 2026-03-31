import unittest

import os
import sys

HERE = os.path.dirname(__file__)
PKG_PARENT = os.path.abspath(os.path.join(HERE, "..", ".."))
if PKG_PARENT not in sys.path:
    sys.path.insert(0, PKG_PARENT)

from trip_wrapped.build_wrapped import build_wrapped


class TestBuildWrapped(unittest.TestCase):
    def test_build_wrapped_empty(self):
        w = build_wrapped(
            title="Trip Wrapped",
            device_id=1,
            from_ts="2026-03-01T00:00:00Z",
            to_ts="2026-03-02T00:00:00Z",
            trips=[],
            generated_at="2026-03-03T00:00:00Z",
        )
        self.assertIn("meta", w)
        self.assertIn("stats", w)
        self.assertIn("trips", w)
        self.assertEqual(w["meta"]["tripCount"], 0)
        self.assertEqual(w["stats"]["totalDistanceM"], 0)

    def test_build_wrapped_journey_downsample(self):
        # 1000 points should be downsampled to <= 900
        route = [{"latitude": 1.0, "longitude": float(i)} for i in range(1000)]
        w = build_wrapped(
            title="Trip Wrapped",
            device_id=1,
            from_ts="2026-03-01T00:00:00Z",
            to_ts="2026-03-02T00:00:00Z",
            trips=[{"distance": 1000, "duration": 1000}],
            generated_at="2026-03-03T00:00:00Z",
            journey_route=route,
        )
        jr = w["stats"]["journeyRoute"]
        self.assertLessEqual(len(jr), 900)
        self.assertGreaterEqual(len(jr), 2)

    def test_build_wrapped_elevation_profile(self):
        route = [
            {"latitude": 0.0, "longitude": 0.0, "altitude": 10, "deviceTime": "2026-03-01T00:00:00Z"},
            {"latitude": 0.0, "longitude": 0.1, "altitude": 20, "deviceTime": "2026-03-01T00:10:00Z"},
            {"latitude": 0.0, "longitude": 0.2, "altitude": 15, "deviceTime": "2026-03-01T00:20:00Z"},
            {"latitude": 0.0, "longitude": 0.3, "altitude": 25, "deviceTime": "2026-03-01T00:30:00Z"},
        ]
        w = build_wrapped(
            title="Trip Wrapped",
            device_id=1,
            from_ts="2026-03-01T00:00:00Z",
            to_ts="2026-03-02T00:00:00Z",
            trips=[{"distance": 1000, "duration": 1000}],
            generated_at="2026-03-03T00:00:00Z",
            journey_route=route,
        )
        stats = w["stats"]
        # Back-compat field used by HTML asset
        self.assertIn("totalElevationGainM", stats)
        self.assertGreater(stats["totalElevationGainM"], 0)

        prof = stats.get("elevationProfile")
        self.assertIsNotNone(prof)
        self.assertEqual(prof.get("by"), "distanceKm")
        pts = prof.get("points")
        self.assertTrue(isinstance(pts, list) and len(pts) >= 2)
        self.assertTrue(all("dKm" in p and "alt" in p for p in pts))


if __name__ == "__main__":
    unittest.main()
