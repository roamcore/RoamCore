#!/usr/bin/env python3
"""Wave 2 #18 — Trip stats (rc_trip_*) from real Traccar data.

This is the "real-data" source for `sensor.rc_trip_distance_today_mi`,
`sensor.rc_trip_distance_total_mi`, `sensor.rc_trip_time_today`,
`sensor.rc_trip_time_total`, `sensor.rc_trip_segments`, and
`sensor.rc_trip_stops` once a Traccar device_tracker is configured via
`input_text.rc_location_tracker_entity` (auto-filled by Wave 2 #17).

Design (MVP-friendly, stdlib-only):

  The Traccar `device_tracker.traccar_<device>` entity in Home Assistant
  carries a small set of attributes on every state change:
    - latitude, longitude (when known)
    - speed (m/s, instantaneous)
    - gps_accuracy / accuracy (m)
    - course / heading (deg)
    - battery_level / device_status / etc. (device-specific)

  We do NOT need to read raw positions — HA already records those into
  the recorder DB on every state change of the tracker. For the MVP we
  keep a small **rolling state file** on disk that this script reads/
  writes atomically on each poll. Each poll:

    1.  Resolves the configured `device_tracker.<entity_id>` (via a
        `--tracker` CLI flag, defaulting to whatever
        `input_text.rc_location_tracker_entity` resolves to in HA's REST
        API; or a literal `--tracker-entity-id` override for testing).
    2.  Reads the tracker's current attributes (lat, lon, speed, …).
    3.  If the tracker has moved >= 50 m from the last recorded position,
        adds the haversine delta to the running
        `total_distance_m`, and if `speed > 0` at that point, accumulates
        `drive_time_s` by the poll interval (default 300 s). Also bumps
        `segments_today`.
    4.  If the tracker is stationary for >= 5 minutes (>= 10 polls at
        the 30 s default `--min-interval-s`, or >= 1 poll at the 5 min
        HA cadence) we treat it as a stop and bump `stops_today`.
    5.  Writes the JSON output atomically (tmp + os.replace) to a
        well-known path that the matching `command_line` sensors in
        `homeassistant/packages/roamcore_trip_local.yaml` can read.

  The output JSON schema is stable (forward-compatible):

    {
      "version": 1,
      "schema_version": 1,
      "generated_at": "2026-07-29T05:05:00Z",
      "tracker_entity_id": "device_tracker.traccar_van",
      "tracker_available": true,
      "last_lat": 51.123,
      "last_lon": -0.456,
      "last_speed_mps": 0.0,
      "last_fix_at": "2026-07-29T05:00:00Z",
      "total_distance_m": 12345.6,
      "total_distance_mi": 7.67,
      "today": {
        "date": "2026-07-29",
        "distance_m": 4321.0,
        "distance_mi": 2.69,
        "drive_time_s": 3600,
        "segments": 4,
        "stops": 2
      }
    }

  Falls back to writing a `tracker_available: false` payload (and
  leaving the previous totals untouched) when the tracker is unknown/
  unavailable — the downstream HA templates in `roamcore_location.yaml`
  handle that case by falling back to `rc_trip_wrapped_*` →
  `rc_trip_local_*` → mocks.

CLI flags:
  --tracker-entity-id <id>   Bypass HA REST API; use this entity_id literally
                              (useful for `--dry-run` testing in CI).
  --tracker <entity_id>      Alias of --tracker-entity-id (preferred form).
  --latitude <deg>           Bypass HA REST API; provide current latitude.
  --longitude <deg>          Bypass HA REST API; provide current longitude.
  --speed-mps <m/s>          Bypass HA REST API; provide current speed m/s.
  --state-json <path>        Path to the persistent state JSON (default below).
  --out-json <path>          Path to the output JSON consumed by HA
                              (default below; mirrors --state-json).
  --ha-base-url <url>        HA base URL (default: http://supervisor/core).
  --ha-token-file <path>     File containing the bearer token (default:
                              /run/s6/container_environment/HASSIO_TOKEN).
  --min-interval-s <s>       Minimum seconds between polls (default: 30).
                              Drives the stop detector (>=10 consecutive
                              stationary polls == 5 min at 30 s).
  --move-threshold-m <m>     Minimum movement (m) to count toward distance
                              (default: 50).
  --move-threshold-m-max <m> Maximum sane single-hop distance (m). If the
                              gap exceeds this we assume a teleport /
                              lost-GPS event and do NOT add it to the
                              odometer (default: 50000).
  --dry-run                  Print what would be written to stdout instead
                              of writing files. Exit 0 on success.

Exit codes:
  0  success
  2  bad CLI args
  3  HA REST call failed (only relevant when reading live HA state)

This script intentionally avoids `import trip_wrapped.*` to keep
"import this module from anywhere in HA" cheap and safe. The downstream
`rc_trip_local.yaml` package invokes it via `shell_command:` and
`command_line:` sensors.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Paths (all overridable via CLI). The defaults mirror HA's `/config/.storage`
# convention so we don't pollute the repo; in dev / CI we write to a temp
# file instead.
# ---------------------------------------------------------------------------

# Default state file: HA's persistent storage dir. In HAOS this is
# /config/.storage. We use the HA-standard `.storage` dir.
DEFAULT_STATE_PATHS = (
    "/config/.storage/roamcore_trip_stats.json",  # HAOS default
    "/homeassistant/.storage/roamcore_trip_stats.json",  # alt HA layout
)


def _pick_default_state_path() -> str:
    """Pick the first existing/writable of DEFAULT_STATE_PATHS, else tmp."""
    for p in DEFAULT_STATE_PATHS:
        parent = os.path.dirname(p)
        try:
            os.makedirs(parent, exist_ok=True)
            # Probe write access with a tiny stat on the parent dir.
            if os.access(parent, os.W_OK):
                return p
        except Exception:
            continue
    # Last resort: /tmp file (still readable by command_line sensors
    # if HA mounts /tmp into the container, which it does by default).
    return "/tmp/roamcore_trip_stats.json"


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in meters between two WGS84 points."""
    R = 6371000.0  # mean Earth radius (m)
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today_local_date() -> str:
    # We use UTC date as the rollover key — Traccar positions are
    # recorded in UTC and the HA `utility_meter` rollover is timezone-
    # configurable. For MVP this matches the existing `rc_trip_*_today_*`
    # fallthrough behaviour well enough; an MVP upgrade can swap in a
    # timezone-aware rollover.
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# HA state retrieval. We support two paths:
#   1. Pull live state from the HA REST API (production path).
#   2. Use literal CLI-supplied lat/lon/speed (test path, --dry-run,
#      CI smoke).
# ---------------------------------------------------------------------------


def _read_ha_tracker_state(
    base_url: str, token: str, entity_id: str
) -> dict:
    """Fetch a tracker's state from HA's /api/states/<entity_id>.

    Returns a dict with keys: state (str), attributes (dict). Raises on
    HTTP / network failure with a structured error string.
    """
    url = base_url.rstrip("/") + "/api/states/" + entity_id
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = (e.read() or b"").decode("utf-8", errors="replace")
        except Exception:
            body = ""
        raise RuntimeError(
            f"HA REST GET {url} -> {e.code} {e.reason}. {body}".strip()
        )
    except Exception as e:
        raise RuntimeError(f"HA REST GET {url} failed: {e}")
    try:
        return json.loads(raw)
    except Exception as e:
        raise RuntimeError(f"HA REST returned invalid JSON: {e}")


def _attrs_to_point(attrs: dict) -> tuple:
    """Extract (lat, lon, speed_mps) from a HA device_tracker attribute dict.

    Returns (None, None, None) if lat/lon are not present.
    """
    lat = attrs.get("latitude")
    lon = attrs.get("longitude")
    if lat is None or lon is None:
        return (None, None, None)
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError):
        return (None, None, None)
    speed = attrs.get("speed")
    try:
        speed_f = float(speed) if speed is not None else 0.0
    except (TypeError, ValueError):
        speed_f = 0.0
    return (lat_f, lon_f, speed_f)


def _resolve_tracker_entity_id(
    base_url: str, token: str, override: str | None
) -> str:
    """Return the configured `input_text.rc_location_tracker_entity` value.

    If `override` is provided (non-empty), return it directly. Otherwise
    fetch `input_text.rc_location_tracker_entity` from the HA REST API.
    Returns "" if unavailable.
    """
    if override:
        return override.strip()
    try:
        body = _read_ha_tracker_state(
            base_url, token, "input_text.rc_location_tracker_entity"
        )
    except Exception:
        return ""
    val = (body.get("state") or "").strip()
    return val


# ---------------------------------------------------------------------------
# Persistent rolling state.
# ---------------------------------------------------------------------------


def _load_state(path: str) -> dict:
    """Load the rolling state JSON; return {} if missing/corrupt."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except FileNotFoundError:
        return {}
    except Exception:
        return {}
    return {}


def _atomic_write_json(path: str, payload: dict) -> None:
    """Write JSON atomically: tmp + os.replace, mode 0644."""
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".rc_trip_stats_", dir=parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
            f.write("\n")
        os.chmod(tmp_path, 0o644)
        os.replace(tmp_path, path)
    except Exception:
        # Best-effort cleanup of the tmp file.
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        raise


# ---------------------------------------------------------------------------
# Main update loop.
# ---------------------------------------------------------------------------


def _update(
    state: dict,
    tracker_entity_id: str,
    tracker_available: bool,
    lat: float | None,
    lon: float | None,
    speed_mps: float,
    min_interval_s: int,
    move_threshold_m: float,
    move_threshold_m_max: float,
) -> dict:
    """Compute the next rolling state. Pure function on `state` -> new state."""
    now = _now_utc_iso()
    today = _today_local_date()
    last = dict(state or {})

    # Preserve the previous `today` block if the date hasn't rolled over.
    today_prev = last.get("today") or {}
    if today_prev.get("date") != today:
        today_block = {
            "date": today,
            "distance_m": 0.0,
            "drive_time_s": 0,
            "segments": 0,
            "stops": 0,
        }
        # On day rollover, "stops" resets, but the running
        # `total_distance_m` / odometer is preserved (it's a true
        # cumulative counter, not a today counter).
        # Also reset stationary-polls accumulator and last_segment_stops.
        last["stationary_polls"] = 0
        last["last_segment_stops"] = 0
    else:
        today_block = {
            "date": today,
            "distance_m": float(today_prev.get("distance_m") or 0.0),
            "drive_time_s": int(today_prev.get("drive_time_s") or 0),
            "segments": int(today_prev.get("segments") or 0),
            "stops": int(today_prev.get("stops") or 0),
        }

    last_lat = last.get("last_lat")
    last_lon = last.get("last_lon")
    last_fix_at = last.get("last_fix_at")
    stationary_polls = int(last.get("stationary_polls") or 0)
    last_segment_stops = int(last.get("last_segment_stops") or 0)
    total_distance_m = float(last.get("total_distance_m") or 0.0)

    if tracker_available and lat is not None and lon is not None:
        if last_lat is not None and last_lon is not None:
            try:
                last_lat_f = float(last_lat)
                last_lon_f = float(last_lon)
                d_m = _haversine_m(last_lat_f, last_lon_f, lat, lon)
                # Sanity-cap single-hop distance: if the gap is larger
                # than move_threshold_m_max we assume a teleport /
                # lost-GPS event and skip adding it to the odometer.
                # We still update the "last position" so future polls
                # resume from the new fix.
                if d_m >= move_threshold_m and d_m <= move_threshold_m_max:
                    total_distance_m += d_m
                    today_block["distance_m"] += d_m
                    if speed_mps > 0.0:
                        # Attribute the elapsed poll time to drive_time.
                        today_block["drive_time_s"] += min_interval_s
                        # If we were stationary and now moved, that ends
                        # the current "stop". Increment stops once when
                        # we transition from stationary -> moving.
                        if stationary_polls > 0 and last_segment_stops == 0:
                            today_block["stops"] += 1
                            last_segment_stops = 1
                        stationary_polls = 0
                    else:
                        stationary_polls += 1
                    # New segment: any movement beyond threshold counts
                    # as a new segment if we were previously stationary
                    # for >=1 poll.
                    if d_m >= move_threshold_m and stationary_polls == 0 and (
                        last.get("last_movement_was_segment") is not True
                    ):
                        today_block["segments"] += 1
                        last["last_movement_was_segment"] = True
                elif d_m > move_threshold_m_max:
                    # Teleport / lost-GPS: keep last position but don't
                    # credit distance. We DO reset stationary_polls to 0
                    # because the user is clearly moving (just with a
                    # bad fix in between).
                    stationary_polls = 0
                else:
                    # Small jiggle: still counted as stationary.
                    stationary_polls += 1
                    last["last_movement_was_segment"] = False
            except (TypeError, ValueError):
                pass
        else:
            # First fix: start fresh.
            stationary_polls = 0
            last["last_movement_was_segment"] = False

        last["last_lat"] = lat
        last["last_lon"] = lon
        last["last_speed_mps"] = speed_mps
        last["last_fix_at"] = now
    else:
        # Tracker unavailable: leave totals alone, mark unavailable.
        last["last_speed_mps"] = None

    # Stop detector: if we've been stationary for >= 5 minutes
    # (>= 10 polls at 30 s, >= 1 poll at 5 min), bump stops once and
    # reset the per-segment latch.
    if stationary_polls * min_interval_s >= 300 and last_segment_stops == 0:
        today_block["stops"] += 1
        last_segment_stops = 1

    last["tracker_entity_id"] = tracker_entity_id
    last["tracker_available"] = bool(tracker_available)
    last["generated_at"] = now
    last["schema_version"] = 1
    last["version"] = last.get("version", 0) + 1
    last["total_distance_m"] = round(total_distance_m, 1)
    last["total_distance_mi"] = round(total_distance_m / 1609.344, 2)
    last["today"] = today_block
    last["today"]["distance_mi"] = round(today_block["distance_m"] / 1609.344, 2)
    last["stationary_polls"] = stationary_polls
    last["last_segment_stops"] = last_segment_stops
    return last


def _format_hms(seconds: int) -> str:
    """Format seconds as `Hh MMm` for HA `input_text` consumers.

    The template sensors in `roamcore_location.yaml` use string fallthrough,
    so producing a human-readable string here keeps the existing UX.
    """
    try:
        s = int(seconds)
    except (TypeError, ValueError):
        s = 0
    if s < 0:
        s = 0
    h = s // 3600
    m = (s % 3600) // 60
    return f"{h}h {m:02d}m"


def _build_cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="traccar_trip_stats.py",
        description="Wave 2 #18 — Trip stats from real Traccar data",
    )
    p.add_argument(
        "--tracker",
        "--tracker-entity-id",
        dest="tracker",
        default=None,
        help=(
            "Bypass HA REST API for the configured tracker; use this "
            "entity_id literally (useful for --dry-run / CI)."
        ),
    )
    p.add_argument("--latitude", type=float, default=None, help="Bypass HA REST: latitude")
    p.add_argument("--longitude", type=float, default=None, help="Bypass HA REST: longitude")
    p.add_argument("--speed-mps", type=float, default=0.0, help="Bypass HA REST: speed m/s")
    p.add_argument("--state-json", default=None, help="Path to rolling state JSON")
    p.add_argument("--out-json", default=None, help="Path to output JSON consumed by HA")
    p.add_argument("--ha-base-url", default="http://supervisor/core", help="HA REST base URL")
    p.add_argument(
        "--ha-token-file",
        default="/run/s6/container_environment/HASSIO_TOKEN",
        help="File containing HA bearer token",
    )
    p.add_argument("--min-interval-s", type=int, default=30, help="Seconds between polls")
    p.add_argument("--move-threshold-m", type=float, default=50.0, help="Min movement (m) to count")
    p.add_argument(
        "--move-threshold-m-max",
        type=float,
        default=50000.0,
        help="Max sane single-hop distance (m)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the output JSON to stdout instead of writing files",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_cli().parse_args(argv)

    if args.min_interval_s < 1:
        print("ERROR: --min-interval-s must be >= 1", file=sys.stderr)
        return 2

    state_path = args.state_json or _pick_default_state_path()
    out_path = args.out_json or state_path

    # --- Resolve tracker entity id ---------------------------------------
    tracker_entity_id = ""
    if args.tracker:
        tracker_entity_id = args.tracker.strip()
    else:
        # Try to read the configured input_text from HA. If we can't,
        # treat the tracker as unavailable so downstream sensors fall
        # back to wrapped/local/mocks.
        token = ""
        try:
            if args.ha_token_file and os.path.exists(args.ha_token_file):
                token = open(args.ha_token_file, "r", encoding="utf-8").read().strip()
        except Exception:
            token = ""
        if token:
            tracker_entity_id = _resolve_tracker_entity_id(
                args.ha_base_url, token, None
            )

    # --- Resolve current lat/lon/speed ------------------------------------
    lat: float | None = None
    lon: float | None = None
    speed_mps: float = float(args.speed_mps or 0.0)
    tracker_available = False

    if args.latitude is not None and args.longitude is not None:
        lat = float(args.latitude)
        lon = float(args.longitude)
        tracker_available = True
    elif tracker_entity_id and not args.tracker:
        # Pull live state from HA REST.
        try:
            token = open(args.ha_token_file, "r", encoding="utf-8").read().strip()
            body = _read_ha_tracker_state(
                args.ha_base_url, token, tracker_entity_id
            )
            st = (body.get("state") or "").strip()
            attrs = body.get("attributes") or {}
            if st not in ("", "unknown", "unavailable", "none"):
                lat, lon, speed_from_attrs = _attrs_to_point(attrs)
                if lat is not None and lon is not None:
                    tracker_available = True
                    if speed_from_attrs is not None:
                        speed_mps = speed_from_attrs
        except Exception as e:
            print(f"WARN: HA REST read failed: {e}", file=sys.stderr)
    elif tracker_entity_id and args.tracker:
        # --tracker override but no --latitude/--longitude: still
        # unavailable, but we record the entity_id for diagnostics.
        pass

    # --- Load + update + write -------------------------------------------
    prev = _load_state(state_path) if not args.dry_run else {}
    new_state = _update(
        prev,
        tracker_entity_id=tracker_entity_id,
        tracker_available=tracker_available,
        lat=lat,
        lon=lon,
        speed_mps=speed_mps,
        min_interval_s=int(args.min_interval_s),
        move_threshold_m=float(args.move_threshold_m),
        move_threshold_m_max=float(args.move_threshold_m_max),
    )

    # Add the human-readable today fields consumed by the fallthrough
    # template sensors in roamcore_location.yaml (string-form times).
    today_block = new_state.get("today") or {}
    new_state["today_drive_time_hms"] = _format_hms(
        today_block.get("drive_time_s") or 0
    )
    new_state["total_drive_time_s"] = int(today_block.get("drive_time_s") or 0)
    new_state["total_drive_time_hms"] = _format_hms(
        today_block.get("drive_time_s") or 0
    )

    if args.dry_run:
        print(json.dumps(new_state, indent=2, sort_keys=True))
        return 0

    try:
        _atomic_write_json(out_path, new_state)
    except Exception as e:
        print(f"ERROR: could not write {out_path}: {e}", file=sys.stderr)
        return 1

    print(
        f"OK: wrote {out_path} "
        f"(tracker={tracker_entity_id or 'none'}, "
        f"available={tracker_available}, "
        f"distance_today_mi={new_state['today'].get('distance_mi', 0)}, "
        f"total_mi={new_state.get('total_distance_mi', 0)})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())