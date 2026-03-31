import unittest

import os
import sys

# Allow running tests directly from repo root:
#   python -m unittest discover -s RoamCore/homeassistant/tools/trip_wrapped/tests
HERE = os.path.dirname(__file__)
PKG_PARENT = os.path.abspath(os.path.join(HERE, "..", ".."))
if PKG_PARENT not in sys.path:
    sys.path.insert(0, PKG_PARENT)

from trip_wrapped.traccar_client import TraccarClient


class TestTraccarClient(unittest.TestCase):
    def test_extract_jsessionid_single_header(self):
        js = TraccarClient._extract_jsessionid(["JSESSIONID=abc123; Path=/; HttpOnly"])
        self.assertEqual(js, "abc123")

    def test_extract_jsessionid_multiple_headers(self):
        js = TraccarClient._extract_jsessionid(
            [
                "other=zzz; Path=/",
                "JSESSIONID=def456; Path=/; Secure; HttpOnly",
            ]
        )
        self.assertEqual(js, "def456")

    def test_extract_jsessionid_missing(self):
        js = TraccarClient._extract_jsessionid(["foo=bar; Path=/"])
        self.assertIsNone(js)


if __name__ == "__main__":
    unittest.main()
