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


if __name__ == "__main__":
    unittest.main()
