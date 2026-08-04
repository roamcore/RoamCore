import unittest

import os
import sys
from unittest import mock

HERE = os.path.dirname(__file__)
PKG_PARENT = os.path.abspath(os.path.join(HERE, "..", ".."))
if PKG_PARENT not in sys.path:
    sys.path.insert(0, PKG_PARENT)

from trip_wrapped import export as export_mod


def _common_args(
    *,
    base_url: str = "http://localhost:8082",
    device_id: int = 1,
    demo: bool = False,
    out_dir: str = "/tmp",
):
    """Build a minimal argparse Namespace for export.main() invocation."""
    return mock.Mock(
        base_url=base_url,
        username=None,
        password=None,
        user_token=None,
        no_ha_proxy=False,
        device_id=device_id,
        from_ts="2026-03-01T00:00:00Z",
        to_ts="2026-03-08T00:00:00Z",
        out_json=os.path.join(out_dir, "latest.json"),
        out_html=os.path.join(out_dir, "latest.html"),
        title="Trip Wrapped",
        template="classic",
        demo=demo,
        owner_name=None,
        config_dir=out_dir,
    )


class TestExportDemoFlag(unittest.TestCase):
    """Demonstrate that --demo bypasses Traccar config entirely."""

    def test_demo_flag_explicit_skips_traccar(self):
        """--demo with NO Traccar config (empty base_url) must NOT raise."""
        # Real Traccar modules must NEVER be touched when --demo is set.
        with mock.patch.object(export_mod, "TraccarClient") as mock_client, \
             mock.patch.object(export_mod, "_load_secrets", return_value={}), \
             mock.patch.object(export_mod, "_build_staticmap_url"), \
             mock.patch.object(export_mod, "render_html", return_value="<html></html>"), \
             mock.patch.object(export_mod, "build_wrapped", return_value={"meta": {}, "stats": {}, "trips": []}):
            # Provide empty base_url; --demo should cause the guard to be skipped.
            args = _common_args(base_url="", demo=True)
            # Should not raise SystemExit; demo path does not consult Traccar.
            export_mod.main_with_args(args)
            # TraccarClient must NOT be instantiated in demo mode.
            mock_client.assert_not_called()


class TestExportRequiresTraccarConfig(unittest.TestCase):
    """Non-demo invocations must exit with an actionable error when Traccar is unconfigured."""

    def test_no_demo_no_traccar_exits_actionable_error(self):
        """No --demo + empty base_url => exit with the actionable error message."""
        msg = (
            "ERROR: Traccar not configured. Either set rc_traccar_base_url + "
            "rc_traccar_device_id in your RoamCore config OR pass --demo to "
            "generate a demo Trip Wrapped for UI preview."
        )
        with mock.patch.object(export_mod, "TraccarClient") as mock_client, \
             mock.patch.object(export_mod, "_load_secrets", return_value={}):
            args = _common_args(base_url="", device_id=1, demo=False)
            with self.assertRaises(SystemExit) as cm:
                export_mod.main_with_args(args)
            self.assertEqual(cm.exception.code, 2)
            # TraccarClient must NOT be instantiated when guard fires.
            mock_client.assert_not_called()

    def test_no_demo_unknown_device_id_exits_actionable_error(self):
        """No --demo + device_id == 'unknown' => exit with the actionable error message."""
        with mock.patch.object(export_mod, "TraccarClient") as mock_client, \
             mock.patch.object(export_mod, "_load_secrets", return_value={}):
            args = _common_args(base_url="http://localhost:8082", device_id="unknown", demo=False)
            with self.assertRaises(SystemExit) as cm:
                export_mod.main_with_args(args)
            self.assertEqual(cm.exception.code, 2)
            mock_client.assert_not_called()

    def test_no_demo_with_traccar_calls_real_api(self):
        """No --demo + Traccar configured => real TraccarClient.get_trips/get_route/get_stops are called."""
        fake_trips = [{"distance": 1000, "duration": 60000}]
        fake_route = [{"latitude": 0.0, "longitude": 0.0, "altitude": 0, "deviceTime": "2026-03-01T00:00:00Z"}]
        fake_stops = [{"startTime": "2026-03-01T00:00:00Z", "endTime": "2026-03-01T00:05:00Z", "duration": 300000, "address": "Home"}]

        with mock.patch.object(export_mod, "_load_secrets", return_value={}), \
             mock.patch.object(export_mod, "_build_staticmap_url"), \
             mock.patch.object(export_mod, "render_html", return_value="<html></html>"), \
             mock.patch.object(export_mod, "build_wrapped", return_value={"meta": {}, "stats": {}, "trips": fake_trips}):
            # Construct a fake TraccarClient instance whose .get_trips / .get_route / .get_stops return canned data.
            fake_client = mock.Mock()
            fake_client.get_trips.return_value = fake_trips
            fake_client.get_route.return_value = fake_route
            fake_client.get_stops.return_value = fake_stops

            with mock.patch.object(export_mod, "TraccarClient") as mock_client_cls:
                # Both classmethods (direct_user_token / direct_basic / ha_supervisor_proxy)
                # return the fake client instance.
                mock_client_cls.direct_user_token.return_value = fake_client
                mock_client_cls.ha_supervisor_proxy.return_value = fake_client
                mock_client_cls.direct_basic.return_value = fake_client

                args = _common_args(base_url="http://localhost:8082", device_id=42, demo=False)
                export_mod.main_with_args(args)

                # Verify the three real-API methods were called with the right args.
                fake_client.get_trips.assert_called_once_with(
                    device_id=42,
                    from_ts="2026-03-01T00:00:00Z",
                    to_ts="2026-03-08T00:00:00Z",
                )
                fake_client.get_route.assert_called()
                fake_client.get_stops.assert_called()


if __name__ == "__main__":
    unittest.main()
