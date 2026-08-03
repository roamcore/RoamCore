"""Unit tests for the WiCAN Pro SQLite time-series store.

Covers:
  - Schema migration on a fresh DB
  - Insert + query round-trip
  - Bulk insert performance (10k readings)
  - Latest reading lookup
  - Retention pruning
  - DTC upsert + clear
  - Stats endpoint
  - Concurrent access from multiple threads
  - DB corruption recovery (open the same DB twice — must work)
  - WAL mode is actually enabled
"""

from __future__ import annotations

import os
import sys
import pathlib
import tempfile
import threading
import time

import pytest

# Make the custom_components dir importable
_COMP = pathlib.Path(__file__).resolve().parents[3] / "homeassistant" / "custom_components" / "roamcore_wican"
sys.path.insert(0, str(_COMP))

from db import WicanDatabase  # noqa: E402


@pytest.fixture
def tmp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = WicanDatabase(path, retention_days=90)
    db.open()
    yield db, path
    db.close()
    try:
        os.unlink(path)
    except OSError:
        pass


# --- Schema + migration ---

def test_fresh_db_creates_schema(tmp_db):
    db, _ = tmp_db
    stats = db.stats()
    assert stats["total_readings"] == 0
    assert stats["session_count"] == 0
    assert stats["active_dtcs"] == 0


def test_wal_mode_enabled(tmp_db):
    db, _ = tmp_db
    # Open a separate connection to inspect journal mode
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    conn.close()
    assert mode.lower() == "wal"


def test_schema_version_set(tmp_db):
    db, _ = tmp_db
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    conn.close()
    assert version == 1


def test_pid_readings_index_exists(tmp_db):
    db, path = tmp_db
    import sqlite3
    conn = sqlite3.connect(path)
    idxs = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='pid_readings'"
    ).fetchall()
    names = {r[0] for r in idxs}
    conn.close()
    assert "idx_pid_ts" in names
    assert "idx_ts" in names


# --- Sessions ---

def test_start_and_end_session(tmp_db):
    db, _ = tmp_db
    sid = db.start_session()
    assert sid is not None
    assert db.get_session(sid)["id"] == sid
    assert db.get_session(sid)["ended_at"] is None

    db.end_session(sid)
    assert db.get_session(sid)["ended_at"] is not None


def test_list_sessions_orders_newest_first(tmp_db):
    db, _ = tmp_db
    s1 = db.start_session()
    time.sleep(1.05)  # ensure distinct started_at (seconds resolution)
    s2 = db.start_session()
    sessions = db.list_sessions()
    assert [s["id"] for s in sessions] == [s2, s1]


def test_session_not_found(tmp_db):
    db, _ = tmp_db
    assert db.get_session("nonexistent") is None


# --- Insert + query ---

def test_insert_and_query_round_trip(tmp_db):
    db, _ = tmp_db
    sid = db.start_session()
    db.insert_readings(sid, [(0x0C, 840.0), (0x0D, 65.0)])
    rows = db.query_readings(0x0C)
    assert len(rows) == 1
    assert rows[0]["value"] == 840.0
    assert rows[0]["session_id"] == sid


def test_insert_increments_session_counts(tmp_db):
    db, _ = tmp_db
    sid = db.start_session()
    db.insert_readings(sid, [(0x0C, 840.0), (0x0D, 65.0)])
    db.insert_readings(sid, [(0x0C, 850.0)])
    s = db.get_session(sid)
    assert s["reading_count"] == 3
    assert s["pid_count"] == 2  # 0x0C + 0x0D


def test_empty_inserts_are_no_op(tmp_db):
    db, _ = tmp_db
    sid = db.start_session()
    assert db.insert_readings(sid, []) == 0
    assert db.get_session(sid)["reading_count"] == 0


def test_latest_reading(tmp_db):
    db, _ = tmp_db
    sid = db.start_session()
    db.insert_readings(sid, [(0x0C, 840.0)])
    time.sleep(1)
    db.insert_readings(sid, [(0x0C, 1500.0)])
    latest = db.latest_reading(0x0C)
    assert latest is not None
    assert latest["value"] == 1500.0


def test_latest_reading_none_for_unknown_pid(tmp_db):
    db, _ = tmp_db
    assert db.latest_reading(0xFF) is None


def test_reading_count(tmp_db):
    db, _ = tmp_db
    sid = db.start_session()
    db.insert_readings(sid, [(0x0C, 840.0), (0x0D, 65.0), (0x0C, 850.0)])
    assert db.reading_count() == 3
    assert db.reading_count(0x0C) == 2
    assert db.reading_count(0x0D) == 1
    assert db.reading_count(0xFF) == 0


# --- Time range queries ---

def test_query_with_time_range(tmp_db):
    db, _ = tmp_db
    sid = db.start_session()
    now = int(time.time())
    db.insert_readings(sid, [(0x0C, 840.0)])  # ts = now
    rows = db.query_readings(0x0C, ts_from=now - 100, ts_to=now + 100)
    assert len(rows) == 1

    rows = db.query_readings(0x0C, ts_from=now + 100, ts_to=now + 200)
    assert len(rows) == 0


def test_query_limit(tmp_db):
    db, _ = tmp_db
    sid = db.start_session()
    for i in range(100):
        db.insert_readings(sid, [(0x0C, float(i))])
    rows = db.query_readings(0x0C, limit=10)
    assert len(rows) == 10


def test_query_returns_in_chronological_order(tmp_db):
    db, _ = tmp_db
    sid = db.start_session()
    for v in [10.0, 20.0, 30.0]:
        db.insert_readings(sid, [(0x0C, v)])
        time.sleep(1.05)  # ensure distinct ts (seconds resolution)
    rows = db.query_readings(0x0C)
    values = [r["value"] for r in rows]
    assert values == sorted(values)


# --- DTCs ---

def test_upsert_dtcs_new_codes(tmp_db):
    db, _ = tmp_db
    sid = db.start_session()
    added = db.upsert_dtcs(sid, ["P0420", "P0171"])
    assert added == 2
    active = db.list_active_dtcs()
    assert {d["code"] for d in active} == {"P0420", "P0171"}


def test_upsert_dtcs_idempotent(tmp_db):
    db, _ = tmp_db
    sid = db.start_session()
    db.upsert_dtcs(sid, ["P0420"])
    added = db.upsert_dtcs(sid, ["P0420", "P0171"])
    assert added == 1  # only P0171 is new
    active = db.list_active_dtcs()
    assert len(active) == 2


def test_clear_specific_dtcs(tmp_db):
    db, _ = tmp_db
    sid = db.start_session()
    db.upsert_dtcs(sid, ["P0420", "P0171"])
    cleared = db.clear_dtcs(["P0420"])
    assert cleared == 1
    active = db.list_active_dtcs()
    assert len(active) == 1
    assert active[0]["code"] == "P0171"


def test_clear_all_dtcs(tmp_db):
    db, _ = tmp_db
    sid = db.start_session()
    db.upsert_dtcs(sid, ["P0420", "P0171"])
    cleared = db.clear_dtcs()
    assert cleared == 2
    assert db.list_active_dtcs() == []


def test_reactivated_dtcs_get_new_timestamp(tmp_db):
    """If a code is cleared then re-appears, it should have a new ts."""
    db, _ = tmp_db
    sid = db.start_session()
    db.upsert_dtcs(sid, ["P0420"])
    first_ts = db.list_active_dtcs()[0]["ts"]
    db.clear_dtcs(["P0420"])
    time.sleep(1)
    db.upsert_dtcs(sid, ["P0420"])
    new_ts = db.list_active_dtcs()[0]["ts"]
    assert new_ts > first_ts


# --- Retention ---

def test_prune_old_readings():
    # Use a fresh DB with a 1-day retention for the test (can't change post-construction)
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = WicanDatabase(path, retention_days=1)
    db.open()
    try:
        sid = db.start_session()
        now = int(time.time())
        with db._cursor() as cur:
            cur.execute(
                "INSERT INTO pid_readings (ts, pid, value, session_id) VALUES (?, ?, ?, ?)",
                (now, 0x0C, 840.0, sid),
            )
            cur.execute(
                "INSERT INTO pid_readings (ts, pid, value, session_id) VALUES (?, ?, ?, ?)",
                (now - (86400 * 10), 0x0C, 1.0, sid),  # 10 days old
            )
        deleted = db.prune_old_readings()
        assert deleted == 1
        assert db.reading_count() == 1
    finally:
        db.close()
        try:
            os.unlink(path)
        except OSError:
            pass


def test_stats(tmp_db):
    db, _ = tmp_db
    sid = db.start_session()
    db.insert_readings(sid, [(0x0C, 840.0), (0x0D, 65.0)])
    db.upsert_dtcs(sid, ["P0420"])
    stats = db.stats()
    assert stats["total_readings"] == 2
    assert stats["session_count"] == 1
    assert stats["active_dtcs"] == 1
    assert stats["last_session"] is not None
    assert stats["retention_days"] == 90


# --- Concurrency ---

def test_concurrent_writes(tmp_db):
    """Multiple threads writing to the DB simultaneously must not corrupt."""
    db, _ = tmp_db
    sid = db.start_session()
    errors = []

    def worker(pid_base: int):
        try:
            for i in range(50):
                db.insert_readings(sid, [(pid_base, float(i))])
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(p,)) for p in [0x0C, 0x0D, 0x0E, 0x0F]]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert errors == []
    # 4 threads * 50 readings = 200 total
    assert db.reading_count() == 200
    # Each PID should have exactly 50 readings
    for pid in [0x0C, 0x0D, 0x0E, 0x0F]:
        assert db.reading_count(pid) == 50


def test_concurrent_writes_and_reads(tmp_db):
    """Writes shouldn't block reads (WAL mode)."""
    db, _ = tmp_db
    sid = db.start_session()
    db.insert_readings(sid, [(0x0C, 840.0)])

    errors = []

    def writer():
        try:
            for i in range(20):
                db.insert_readings(sid, [(0x0C, float(i))])
        except Exception as e:
            errors.append(("writer", e))

    def reader():
        try:
            for _ in range(20):
                db.latest_reading(0x0C)
        except Exception as e:
            errors.append(("reader", e))

    threads = [threading.Thread(target=writer), threading.Thread(target=reader)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert errors == []


# --- Idempotent open / close ---

def test_double_open_is_safe(tmp_db):
    db, _ = tmp_db
    db.open()  # second open should be a no-op
    db.insert_readings(db.start_session(), [(0x0C, 840.0)])


def test_close_then_reopen_preserves_data():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        db = WicanDatabase(path)
        db.open()
        sid = db.start_session()
        db.insert_readings(sid, [(0x0C, 840.0)])
        db.close()

        # Reopen and verify data is still there
        db2 = WicanDatabase(path)
        db2.open()
        rows = db2.query_readings(0x0C)
        assert len(rows) == 1
        assert rows[0]["value"] == 840.0
        db2.close()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


# --- Bulk insert performance ---

def test_bulk_insert_10k_readings(tmp_db):
    """Inserting 10k readings should be fast (sub-5s target)."""
    db, _ = tmp_db
    sid = db.start_session()
    batch = [(0x0C, float(i)) for i in range(1000)]
    start = time.monotonic()
    for _ in range(10):
        db.insert_readings(sid, batch)
    elapsed = time.monotonic() - start
    assert elapsed < 5.0, f"bulk insert too slow: {elapsed:.2f}s"
    assert db.reading_count() == 10000


# --- Disk size sanity ---

def test_disk_bytes_grows(tmp_db):
    db, _ = tmp_db
    initial = db.disk_bytes()
    assert initial > 0  # at least the header
    sid = db.start_session()
    db.insert_readings(sid, [(0x0C, float(i)) for i in range(1000)])
    grown = db.disk_bytes()
    # Hard to assert exact size; just make sure it's not implausibly small
    assert grown > 1000  # at least 1KB for 1000 readings
