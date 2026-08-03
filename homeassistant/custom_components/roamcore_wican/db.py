"""Time-series SQLite store for the RoamCore WiCAN Pro integration.

Design notes:
  - We use a single SQLite database at `<config_dir>/.storage/roamcore_wican.db`.
  - WAL mode so writes don't block reads (HA's main thread reads the timeseries
    view while the coordinator writes new PID readings).
  - Indexed on (pid, ts DESC) so the timeseries view is fast.
  - All public methods are thread-safe — we serialize via a single-thread
    executor; the connection itself is opened with `check_same_thread=False`
    so HA's executor thread + the HTTP view thread can both use it.
  - Retention is rolling N days (default 90); a background task prunes on
    every write.

Schema:
  pid_readings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          INTEGER NOT NULL,         -- unix seconds (UTC)
    pid         INTEGER NOT NULL,         -- hex OBD2 PID (0x04, 0x0C, ...)
    value       REAL NOT NULL,            -- decoded scalar
    session_id  TEXT NOT NULL             -- ISO timestamp of the connection session
  );
  CREATE INDEX idx_pid_ts ON pid_readings (pid, ts DESC);

  sessions (
    id          TEXT PRIMARY KEY,         -- ISO timestamp
    started_at  INTEGER NOT NULL,
    ended_at    INTEGER,                  -- NULL while running
    pid_count   INTEGER NOT NULL,         -- distinct PIDs in this session
    reading_count INTEGER NOT NULL
  );

  dtcs (
    code        TEXT NOT NULL,            -- "P0420"
    ts          INTEGER NOT NULL,         -- first-seen timestamp
    cleared_at  INTEGER,                  -- NULL if still active
    session_id  TEXT
  );

This is intentionally simple — no compressed columns, no rollup tables,
no PostgreSQL. For a van running 1-4 PIDs/sec for a few hours a day, the
table grows ~1MB/day. 90-day retention = ~90MB. SQLite handles that
comfortably on any modern SD card.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterable, Optional

_LOGGER = logging.getLogger(__name__)

# Schema version. Bumped when migrations land; connection() runs
# PRAGMA user_version + on-the-fly migrations at startup.
SCHEMA_VERSION = 1

DEFAULT_RETENTION_DAYS = 90


class WicanDatabase:
    """Thread-safe SQLite time-series store for WiCAN Pro PID readings."""

    def __init__(self, db_path: str, retention_days: int = DEFAULT_RETENTION_DAYS) -> None:
        self._db_path = db_path
        self._retention_days = retention_days
        self._lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None

    @property
    def db_path(self) -> str:
        return self._db_path

    @property
    def retention_days(self) -> int:
        return self._retention_days

    def open(self) -> None:
        """Open the database, run migrations, and switch to WAL mode."""
        with self._lock:
            if self._conn is not None:
                return
            # `check_same_thread=False` is OK because we serialize via the
            # `self._lock` and the HA asyncio executor.
            self._conn = sqlite3.connect(
                self._db_path,
                check_same_thread=False,
                isolation_level=None,  # autocommit; we use explicit BEGIN
                timeout=10.0,
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._migrate()
            _LOGGER.info("wican db opened at %s (retention=%d days)", self._db_path, self._retention_days)

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None
                _LOGGER.info("wican db closed")

    @contextmanager
    def _cursor(self):
        """Yield a cursor inside a serialised transaction."""
        assert self._conn is not None, "db not opened"
        with self._lock:
            cur = self._conn.cursor()
            try:
                cur.execute("BEGIN")
                yield cur
                cur.execute("COMMIT")
            except Exception:
                cur.execute("ROLLBACK")
                raise
            finally:
                cur.close()

    def _migrate(self) -> None:
        """Run on-connect migrations keyed on PRAGMA user_version."""
        assert self._conn is not None
        cur = self._conn.execute("PRAGMA user_version")
        version = cur.fetchone()[0]
        if version < 1:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS pid_readings (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts          INTEGER NOT NULL,
                    pid         INTEGER NOT NULL,
                    value       REAL NOT NULL,
                    session_id  TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_pid_ts ON pid_readings (pid, ts DESC);
                CREATE INDEX IF NOT EXISTS idx_ts ON pid_readings (ts DESC);

                CREATE TABLE IF NOT EXISTS sessions (
                    id            TEXT PRIMARY KEY,
                    started_at    INTEGER NOT NULL,
                    ended_at      INTEGER,
                    pid_count     INTEGER NOT NULL DEFAULT 0,
                    reading_count INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS dtcs (
                    code        TEXT NOT NULL,
                    ts          INTEGER NOT NULL,
                    cleared_at  INTEGER,
                    session_id  TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_dtcs_code ON dtcs (code, cleared_at);

                CREATE TABLE IF NOT EXISTS migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at INTEGER NOT NULL
                );

                PRAGMA user_version = 1;
                INSERT OR REPLACE INTO migrations (version, applied_at)
                    VALUES (1, strftime('%s','now'));
                """
            )
            _LOGGER.info("wican db migration applied: v1 (initial schema)")

    # --- Sessions ---

    def start_session(self) -> str:
        """Record a new connection session. Returns the session_id."""
        sid = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO sessions (id, started_at, pid_count, reading_count) "
                "VALUES (?, ?, 0, 0)",
                (sid, int(time.time())),
            )
        return sid

    def end_session(self, sid: str) -> None:
        """Mark a session as ended + record the final stats."""
        with self._cursor() as cur:
            cur.execute(
                "UPDATE sessions SET ended_at = ? WHERE id = ?",
                (int(time.time()), sid),
            )

    def get_session(self, sid: str) -> Optional[dict]:
        """Return session row as a dict, or None if not found."""
        with self._cursor() as cur:
            row = cur.execute(
                "SELECT id, started_at, ended_at, pid_count, reading_count "
                "FROM sessions WHERE id = ?",
                (sid,),
            ).fetchone()
            return dict(row) if row else None

    def list_sessions(self, limit: int = 50) -> list[dict]:
        """Return the N most recent sessions."""
        with self._cursor() as cur:
            rows = cur.execute(
                "SELECT id, started_at, ended_at, pid_count, reading_count "
                "FROM sessions ORDER BY started_at DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
            return [dict(r) for r in rows]

    # --- PID readings ---

    def insert_readings(self, session_id: str, readings: Iterable[tuple[int, float]]) -> int:
        """Bulk-insert PID readings.

        `readings` is an iterable of (pid, value) pairs.
        Returns the number of rows inserted.
        """
        ts = int(time.time())
        rows = [(ts, pid, value, session_id) for pid, value in readings]
        if not rows:
            return 0
        with self._cursor() as cur:
            cur.executemany(
                "INSERT INTO pid_readings (ts, pid, value, session_id) VALUES (?, ?, ?, ?)",
                rows,
            )
            cur.execute(
                "UPDATE sessions SET reading_count = reading_count + ? WHERE id = ?",
                (len(rows), session_id),
            )
            cur.execute(
                "UPDATE sessions SET pid_count = ("
                "  SELECT COUNT(DISTINCT pid) FROM pid_readings WHERE session_id = ?"
                ") WHERE id = ?",
                (session_id, session_id),
            )
        return len(rows)

    def query_readings(
        self,
        pid: int,
        ts_from: Optional[int] = None,
        ts_to: Optional[int] = None,
        limit: int = 1000,
    ) -> list[dict]:
        """Query PID readings, ordered by timestamp ascending."""
        clauses = ["pid = ?"]
        params: list = [pid]
        if ts_from is not None:
            clauses.append("ts >= ?")
            params.append(int(ts_from))
        if ts_to is not None:
            clauses.append("ts <= ?")
            params.append(int(ts_to))
        sql = (
            "SELECT ts, pid, value, session_id FROM pid_readings "
            f"WHERE {' AND '.join(clauses)} "
            "ORDER BY ts ASC LIMIT ?"
        )
        params.append(int(limit))
        with self._cursor() as cur:
            rows = cur.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def latest_reading(self, pid: int) -> Optional[dict]:
        """Return the most recent reading for a PID, or None."""
        with self._cursor() as cur:
            row = cur.execute(
                "SELECT ts, pid, value, session_id FROM pid_readings "
                "WHERE pid = ? ORDER BY ts DESC LIMIT 1",
                (pid,),
            ).fetchone()
            return dict(row) if row else None

    def reading_count(self, pid: Optional[int] = None) -> int:
        """Count readings — for a specific PID if given, else total."""
        with self._cursor() as cur:
            if pid is None:
                row = cur.execute("SELECT COUNT(*) FROM pid_readings").fetchone()
            else:
                row = cur.execute(
                    "SELECT COUNT(*) FROM pid_readings WHERE pid = ?", (pid,)
                ).fetchone()
            return int(row[0]) if row else 0

    def disk_bytes(self) -> int:
        """Approximate on-disk size of the DB file."""
        import os

        try:
            return os.path.getsize(self._db_path)
        except OSError:
            return 0

    # --- DTCs ---

    def upsert_dtcs(self, session_id: str, codes: list[str]) -> int:
        """Insert any DTC codes that aren't already active. Returns new count."""
        if not codes:
            return 0
        ts = int(time.time())
        with self._cursor() as cur:
            # Find existing active (cleared_at IS NULL) DTCs
            existing = {
                row["code"]
                for row in cur.execute(
                    "SELECT DISTINCT code FROM dtcs WHERE cleared_at IS NULL"
                ).fetchall()
            }
            new_codes = [c for c in codes if c not in existing]
            if new_codes:
                cur.executemany(
                    "INSERT INTO dtcs (code, ts, session_id) VALUES (?, ?, ?)",
                    [(c, ts, session_id) for c in new_codes],
                )
            return len(new_codes)

    def list_active_dtcs(self) -> list[dict]:
        """Return all currently-active DTCs."""
        with self._cursor() as cur:
            rows = cur.execute(
                "SELECT code, ts, session_id FROM dtcs "
                "WHERE cleared_at IS NULL ORDER BY ts DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def clear_dtcs(self, codes: Optional[list[str]] = None) -> int:
        """Mark DTCs as cleared. If codes is None, clears all active."""
        ts = int(time.time())
        with self._cursor() as cur:
            if codes is None:
                cur.execute(
                    "UPDATE dtcs SET cleared_at = ? WHERE cleared_at IS NULL", (ts,)
                )
            else:
                placeholders = ",".join("?" for _ in codes)
                cur.execute(
                    f"UPDATE dtcs SET cleared_at = ? WHERE code IN ({placeholders}) AND cleared_at IS NULL",
                    (ts, *codes),
                )
            return cur.rowcount

    # --- Retention ---

    def prune_old_readings(self) -> int:
        """Delete readings older than `retention_days`. Returns deleted count."""
        cutoff = int(time.time()) - (self._retention_days * 86400)
        with self._cursor() as cur:
            cur.execute("DELETE FROM pid_readings WHERE ts < ?", (cutoff,))
            return cur.rowcount

    def vacuum(self) -> None:
        """Run VACUUM to reclaim disk space after large deletes."""
        with self._lock:
            assert self._conn is not None
            self._conn.execute("VACUUM")

    # --- Stats ---

    def stats(self) -> dict:
        """Return high-level stats for the OpenClaw /summary endpoint."""
        with self._cursor() as cur:
            total = cur.execute("SELECT COUNT(*) FROM pid_readings").fetchone()[0]
            session_count = cur.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            last_session = cur.execute(
                "SELECT started_at, ended_at, pid_count, reading_count "
                "FROM sessions ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
            active_dtcs = cur.execute(
                "SELECT COUNT(*) FROM dtcs WHERE cleared_at IS NULL"
            ).fetchone()[0]
            disk = self.disk_bytes()
        return {
            "total_readings": int(total),
            "session_count": int(session_count),
            "active_dtcs": int(active_dtcs),
            "disk_bytes": int(disk),
            "retention_days": self._retention_days,
            "last_session": dict(last_session) if last_session else None,
        }


async def async_prune_loop(db: WicanDatabase, interval_hours: int = 24) -> None:
    """Background coroutine that prunes old readings every `interval_hours`."""
    interval_seconds = interval_hours * 3600
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            deleted = await asyncio.get_running_loop().run_in_executor(
                None, db.prune_old_readings
            )
            if deleted:
                _LOGGER.info("pruned %d old wican readings", deleted)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("error during wican db prune")
