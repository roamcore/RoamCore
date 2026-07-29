#!/usr/bin/env python3
"""RoamCore Gamification — stdlib-only snapshot helper.

This is the headless CLI mirror of the
``roamcore.gamification_acknowledge_trophy`` service surface. It is
used by ``scripts/checks/gamification-smoke.sh`` to validate the
trophy-state model without a running HA instance.

Privacy: stdlib-only. No HTTP. No third-party imports. No telemetry.

The script reads a JSON snapshot from stdin describing the 7 relevant
RoamCore entities (kill-switch + 7 trigger sensors + 7 seen flags +
last-award-at + last-award-trophy + trophy-count) and emits a JSON
report:

  {
    "enabled": bool,
    "count": int,
    "last_award_at": "...",
    "last_award_trophy": "...",
    "trophies": [
      {
        "id": "...",
        "title": "...",
        "triggered": bool,
        "seen": bool
      },
      ...
    ]
  }

Usage:
  python3 homeassistant/tools/gamification/trophy_state.py --help
  python3 homeassistant/tools/gamification/trophy_state.py --dry-run
  echo '{"enabled": true, ...}' | python3 homeassistant/tools/gamification/trophy_state.py

Exit code: 0 on success, 2 on argument error, 3 on a SnapshotError.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Trophy taxonomy — single source of truth for the gamification slice.
# Mirrors docs/setup/gamification.md and the contract package.
TROPHIES: list[dict] = [
    {
        "id": "first_trip_wrapped",
        "title": "First Trip Wrapped",
        "trigger_entity": "binary_sensor.rc_gamification_trophy_triggered_first_trip_wrapped",
        "seen_entity": "input_boolean.rc_gamification_trophy_seen_first_trip_wrapped",
    },
    {
        "id": "first_power_session",
        "title": "First Power Session",
        "trigger_entity": "binary_sensor.rc_gamification_trophy_triggered_first_power_session",
        "seen_entity": "input_boolean.rc_gamification_trophy_seen_first_power_session",
    },
    {
        "id": "first_automation",
        "title": "First Automation",
        "trigger_entity": "binary_sensor.rc_gamification_trophy_triggered_first_automation",
        "seen_entity": "input_boolean.rc_gamification_trophy_seen_first_automation",
    },
    {
        "id": "first_share_exported",
        "title": "First Share Exported",
        "trigger_entity": "binary_sensor.rc_gamification_trophy_triggered_first_share_exported",
        "seen_entity": "input_boolean.rc_gamification_trophy_seen_first_share_exported",
    },
    {
        "id": "first_offline_driving_day",
        "title": "First Offline Driving Day",
        "trigger_entity": "binary_sensor.rc_gamification_trophy_triggered_first_offline_driving_day",
        "seen_entity": "input_boolean.rc_gamification_trophy_seen_first_offline_driving_day",
    },
    {
        "id": "first_setup_complete",
        "title": "First Setup Complete",
        "trigger_entity": "binary_sensor.rc_gamification_trophy_triggered_first_setup_complete",
        "seen_entity": "input_boolean.rc_gamification_trophy_seen_first_setup_complete",
    },
    {
        "id": "first_twilight_handling",
        "title": "First Twilight Handling",
        "trigger_entity": "binary_sensor.rc_gamification_trophy_triggered_first_twilight_handling",
        "seen_entity": "input_boolean.rc_gamification_trophy_seen_first_twilight_handling",
    },
]


class SnapshotError(Exception):
    """Raised on any error path. All CLI helpers exit non-zero on this."""


def _bool(v) -> bool:
    """Coerce an HA-style state string ('on'/'off') into a strict bool."""
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    s = str(v).strip().lower()
    return s in ("on", "true", "1", "yes")


def _str(v, default: str = "unknown") -> str:
    """Coerce an HA-style state into a string, returning the default for unknown/unavailable/None."""
    if v is None:
        return default
    s = str(v).strip()
    if s in ("", "unknown", "unavailable", "none"):
        return default
    return s


def render_snapshot(snapshot: dict) -> dict:
    """Render a snapshot dict into the trophy-state report.

    The snapshot dict can be:

    - ``{"enabled": bool, "trophies": {trophy_id: {"triggered": bool, "seen": bool}, ...},
        "last_award_at": "...", "last_award_trophy": "..."}``

    - or a flat dict keyed by entity_id (as the smoke check feeds in).

    When ``enabled`` is missing, we assume ``False`` (kill-switch OFF is
    the default — the privacy-by-default posture).
    """
    enabled = _bool(snapshot.get("enabled", False))

    # Determine per-trophy state. We accept either a nested
    # ``trophies`` dict or a flat ``entity_id -> state`` dict.
    trophies_raw: dict = snapshot.get("trophies") or {}
    flat: dict = snapshot.get("states") or {}
    # Flat dict keys may be entity_id strings; map them back.
    if not trophies_raw and flat:
        for t in TROPHIES:
            trophies_raw[t["id"]] = {
                "triggered": _bool(flat.get(t["trigger_entity"], "off")),
                "seen": _bool(flat.get(t["seen_entity"], "off")),
            }

    out_trophies: list[dict] = []
    count = 0
    for t in TROPHIES:
        triggered = _bool((trophies_raw.get(t["id"]) or {}).get("triggered", False))
        seen = _bool((trophies_raw.get(t["id"]) or {}).get("seen", False))
        if triggered:
            count += 1
        out_trophies.append({
            "id": t["id"],
            "title": t["title"],
            "triggered": triggered,
            "seen": seen,
        })

    last_award_at = _str(snapshot.get("last_award_at"), default="unknown")
    last_award_trophy = _str(snapshot.get("last_award_trophy"), default="unknown")

    return {
        "enabled": enabled,
        "count": count,
        "last_award_at": last_award_at,
        "last_award_trophy": last_award_trophy,
        "trophies": out_trophies,
    }


def _die(msg: str, code: int = 2) -> None:
    """Print an error to stderr and exit non-zero."""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="roamcore_gamification_trophy_state",
        description=(
            "Render a RoamCore gamification trophy-state snapshot. "
            "Privacy-by-default: no remote upload, no telemetry, no third-party HTTP. "
            "Trophies compose over RoamCore's existing signals."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Emit a snapshot where the kill-switch is OFF and every "
            "trophy is untriggered + unseen. Used by the smoke check "
            "to validate the script runs end-to-end without stdin."
        ),
    )
    parser.add_argument(
        "--input",
        dest="input_path",
        default=None,
        help=(
            "Optional path to a JSON snapshot file. If omitted, the "
            "script reads JSON from stdin (set --dry-run to skip)."
        ),
    )
    args = parser.parse_args()

    snapshot: dict = {}
    if args.dry_run:
        # Default snapshot: OFF, no trophies triggered, no seen flags.
        snapshot = {
            "enabled": False,
            "last_award_at": "unknown",
            "last_award_trophy": "unknown",
            "trophies": {
                t["id"]: {"triggered": False, "seen": False} for t in TROPHIES
            },
        }
    elif args.input_path:
        try:
            with open(args.input_path, "r", encoding="utf-8") as f:
                snapshot = json.load(f)
        except FileNotFoundError as exc:
            _die(f"input file not found: {exc}", code=3)
        except json.JSONDecodeError as exc:
            _die(f"invalid JSON in input file: {exc}", code=3)
    else:
        # Read from stdin.
        raw = sys.stdin.read() or "{}"
        try:
            snapshot = json.loads(raw)
        except json.JSONDecodeError as exc:
            _die(f"invalid JSON on stdin: {exc}", code=3)

    try:
        report = render_snapshot(snapshot)
    except (KeyError, TypeError, ValueError) as exc:
        _die(f"snapshot render failed: {exc}", code=3)

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())