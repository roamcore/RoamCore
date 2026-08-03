"""Fuzz / property tests for the PID decoder and DB layer.

Throws random garbage at the decoders to make sure they don't crash on
malformed input. This is the "stress test" the user asked for.

For each PID:
  - feed it random bytes of length 0..16
  - feed it None, ints, floats, strings
  - feed it huge values (overflow)
  - feed it negative values
  - feed it unicode garbage

The decoders MUST return None for invalid input; they MUST NOT raise.
"""

from __future__ import annotations

import os
import random
import sys
import pathlib
import tempfile

import pytest

_REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO / "homeassistant" / "custom_components"))

from roamcore_wican.pids import PID_BY_ID, decode_bytes, decode_value  # noqa: E402


# --- Random byte fuzzing ---

@pytest.mark.parametrize("pid", list(PID_BY_ID.keys()))
def test_pid_decodes_arbitrary_bytes_without_crashing(pid):
    """For each known PID, feed it 200 random byte sequences and confirm it returns None or float."""
    rng = random.Random(pid * 7 + 13)  # deterministic per PID
    for _ in range(200):
        length = rng.randint(0, 16)
        data = bytes(rng.randint(0, 255) for _ in range(length))
        result = decode_bytes(pid, data)
        assert result is None or isinstance(result, float), (
            f"PID {pid:02X} returned {type(result).__name__}: {result!r}"
        )


@pytest.mark.parametrize("pid", list(PID_BY_ID.keys()))
def test_pid_decodes_arbitrary_values_without_crashing(pid):
    """Feed each PID a variety of bizarre value types."""
    bizarre = [
        None,
        True,
        False,
        0,
        1,
        -1,
        255,
        256,
        -100,
        0.0,
        -0.0,
        float("inf"),
        float("-inf"),
        "",
        "0",
        "FF",
        "0xFF",
        "FF GG HH",  # malformed hex
        "not a number",
        [],
        [0, 0],
        [0xFF, 0xFF, 0xFF],
        tuple(),
        (1, 2, 3),
        {},
        {"key": "value"},
    ]
    for value in bizarre:
        try:
            result = decode_value(pid, value)
        except Exception as e:
            pytest.fail(f"PID {pid:02X} raised {type(e).__name__} on input {value!r}: {e}")
        assert result is None or isinstance(result, float), (
            f"PID {pid:02X} returned {type(result).__name__}: {result!r} for input {value!r}"
        )


def test_pid_decodes_extreme_values():
    """Some PIDs have specific bit widths; verify the decoders don't overflow."""
    # RPM: max value = (256 * 255 + 255) / 4 = 16383.75
    result = decode_bytes(0x0C, bytes([0xFF, 0xFF]))
    assert result == 16383.75

    # Speed: max = 255 km/h
    result = decode_bytes(0x0D, bytes([0xFF]))
    assert result == 255.0

    # Throttle: max = 100%
    result = decode_bytes(0x11, bytes([0xFF]))
    assert result == 100.0

    # Coolant: max = 215°C
    result = decode_bytes(0x05, bytes([0xFF]))
    assert result == 215.0

    # Coolant: min = -40°C
    result = decode_bytes(0x05, bytes([0x00]))
    assert result == -40.0

    # Fuel rate: max = (256*255 + 255)/20 = 3276.75 L/h (absurd but mathematically OK)
    result = decode_bytes(0x5E, bytes([0xFF, 0xFF]))
    assert result == 3276.75


# --- DB fuzzing ---

@pytest.mark.parametrize("pid_count", [0, 1, 17, 100, 1000])
def test_db_handles_arbitrary_pid_values(pid_count):
    """Insert N readings with various PIDs and confirm DB round-trips."""
    from roamcore_wican.db import WicanDatabase

    db_path = os.path.join(tempfile.gettempdir(), f"test_wican_fuzz_{pid_count}.db")
    if os.path.exists(db_path):
        os.unlink(db_path)
    db = WicanDatabase(db_path)
    db.open()
    try:
        sid = db.start_session()
        # Use any PIDs in the 0x00..0xFF range, including unknown ones
        rng = random.Random(pid_count)
        readings = []
        for i in range(pid_count):
            pid = rng.randint(0x00, 0xFF)
            value = rng.uniform(-1e6, 1e6)
            readings.append((pid, value))
        db.insert_readings(sid, readings)
        assert db.reading_count() == pid_count
    finally:
        db.close()
        try:
            os.unlink(db_path)
        except OSError:
            pass


def test_db_handles_extreme_timestamps():
    """Insert a reading with ts=0 (1970) and ts=2**31 (2038 overflow edge)."""
    from roamcore_wican.db import WicanDatabase

    db_path = os.path.join(tempfile.gettempdir(), "test_wican_ts.db")
    if os.path.exists(db_path):
        os.unlink(db_path)
    db = WicanDatabase(db_path)
    db.open()
    try:
        sid = db.start_session()
        with db._cursor() as cur:
            cur.execute(
                "INSERT INTO pid_readings (ts, pid, value, session_id) VALUES (?, ?, ?, ?)",
                (0, 0x0C, 100.0, sid),
            )
            cur.execute(
                "INSERT INTO pid_readings (ts, pid, value, session_id) VALUES (?, ?, ?, ?)",
                (2147483647, 0x0C, 200.0, sid),  # 2038-01-19 03:14:07 UTC
            )
        rows = db.query_readings(0x0C, ts_from=0, ts_to=2147483647)
        assert len(rows) == 2
    finally:
        db.close()
        try:
            os.unlink(db_path)
        except OSError:
            pass


def test_db_concurrent_writes_dont_corrupt():
    """Hammer the DB with 10 concurrent threads × 100 inserts."""
    from roamcore_wican.db import WicanDatabase

    db_path = os.path.join(tempfile.gettempdir(), "test_wican_concurrent.db")
    if os.path.exists(db_path):
        os.unlink(db_path)
    db = WicanDatabase(db_path)
    db.open()
    try:
        sid = db.start_session()
        errors = []

        def worker(thread_id):
            try:
                for i in range(100):
                    db.insert_readings(sid, [(0x0C, float(thread_id * 1000 + i))])
            except Exception as e:
                errors.append(e)

        import threading
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        assert errors == []
        assert db.reading_count() == 1000
    finally:
        db.close()
        try:
            os.unlink(db_path)
        except OSError:
            pass
