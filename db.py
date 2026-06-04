from __future__ import annotations

import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import psycopg2
from psycopg2 import pool as pg_pool
from psycopg2.extras import RealDictCursor


logger = logging.getLogger(__name__)

_pool: pg_pool.ThreadedConnectionPool | None = None
_lock = threading.Lock()

_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    company TEXT,
    email TEXT,
    phone TEXT,
    source TEXT NOT NULL DEFAULT 'Manual',
    status TEXT NOT NULL DEFAULT 'New' CHECK (status IN ('New','Contacted','Qualified','Proposal','Closed-Won','Closed-Lost')),
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low','medium','high')),
    value REAL,
    message TEXT,
    notes TEXT,
    next_followup TEXT,
    ai_score INTEGER,
    ai_summary TEXT,
    ai_category TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_leads_user_id ON leads(user_id);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(user_id, status);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_leads_followup ON leads(user_id, next_followup);

CREATE TRIGGER IF NOT EXISTS trg_leads_updated_at
AFTER UPDATE ON leads
FOR EACH ROW
BEGIN
    UPDATE leads SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;

CREATE TABLE IF NOT EXISTS password_resets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    used_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pw_resets_token ON password_resets(token_hash);
CREATE INDEX IF NOT EXISTS idx_pw_resets_user  ON password_resets(user_id);
"""


def _database_url() -> str:
    test_url = os.environ.get("TEST_DATABASE_URL")
    if test_url and (os.environ.get("FLASK_ENV") == "testing" or os.environ.get("PYTEST_CURRENT_TEST")):
        return test_url
    url = os.environ.get("DATABASE_URL") or test_url
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy .env.example to .env and configure it."
        )
    return url


def is_sqlite_url(url: str | None = None) -> bool:
    return (url or _database_url()).startswith("sqlite:///")


def _sqlite_path(url: str | None = None) -> Path:
    return Path((url or _database_url()).removeprefix("sqlite:///")).expanduser().resolve()


def _adapt_placeholders(query: str) -> str:
    return query.replace("%s", "?") if is_sqlite_url() else query


def _connect_sqlite():
    path = _sqlite_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_pool(min_conn: int | None = None, max_conn: int | None = None) -> None:
    global _pool
    if is_sqlite_url():
        return
    with _lock:
        if _pool is not None:
            return
        minimum = min_conn or int(os.environ.get("DB_POOL_MIN", 2))
        maximum = max_conn or int(os.environ.get("DB_POOL_MAX", 10))
        _pool = pg_pool.ThreadedConnectionPool(
            minconn=minimum,
            maxconn=maximum,
            dsn=_database_url(),
            cursor_factory=RealDictCursor,
        )
        logger.info("DB pool ready (min=%d max=%d dsn=***)", minimum, maximum)


def _get_pool() -> pg_pool.ThreadedConnectionPool:
    if _pool is None:
        init_pool()
    return _pool  # type: ignore[return-value]


def close_pool() -> None:
    global _pool
    with _lock:
        if _pool is not None:
            _pool.closeall()
            _pool = None


@contextmanager
def get_db() -> Iterator[Any]:
    if is_sqlite_url():
        conn = _connect_sqlite()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return

    pool = _get_pool()
    conn = pool.getconn()
    try:
        if conn.closed:
            raise psycopg2.OperationalError("Connection is closed")
    except Exception:
        try:
            pool.putconn(conn, close=True)
        except Exception:
            pass
        conn = psycopg2.connect(dsn=_database_url(), cursor_factory=RealDictCursor)

    try:
        yield conn
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            pool.putconn(conn)
        except Exception as exc:  # pragma: no cover - requires pool failure
            logger.warning("Could not return connection to pool: %s", exc)


def _row_to_dict(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    if isinstance(row, dict):
        return dict(row)
    if isinstance(row, sqlite3.Row):
        return {key: row[key] for key in row.keys()}
    return dict(row)


def fetch_one(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(_adapt_placeholders(query), params)
            return _row_to_dict(cursor.fetchone())
        finally:
            cursor.close()


def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(_adapt_placeholders(query), params)
            rows = cursor.fetchall()
            return [_row_to_dict(row) for row in rows if row is not None]
        finally:
            cursor.close()


def execute_write(query: str, params: tuple[Any, ...] = ()) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(_adapt_placeholders(query), params)
            return int(cursor.rowcount)
        finally:
            cursor.close()


def insert_returning_id(query: str, params: tuple[Any, ...] = ()) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            adapted = _adapt_placeholders(query)
            if is_sqlite_url():
                cursor.execute(adapted, params)
                return int(cursor.lastrowid)
            cursor.execute(f"{adapted} RETURNING id", params)
            row = cursor.fetchone()
            return int(row["id"])
        finally:
            cursor.close()


def execute_script(script: str) -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            if is_sqlite_url():
                cursor.executescript(script)
            else:
                cursor.execute(script)
        finally:
            cursor.close()


def init_schema() -> None:
    if is_sqlite_url():
        execute_script(_SQLITE_SCHEMA)
        return

    # Gunicorn starts multiple workers simultaneously — every worker calls
    # init_schema(), and concurrent DDL (CREATE OR REPLACE FUNCTION, DROP/CREATE
    # TRIGGER, ALTER TABLE) deadlocks on pg_proc catalog rows.
    #
    # Fix: acquire a transaction-level advisory lock before running any DDL.
    # pg_try_advisory_xact_lock() returns FALSE immediately if another process
    # already holds it, so competing workers skip cleanly instead of waiting
    # and creating a circular lock chain. The lock auto-releases on commit/rollback.
    schema_path = Path(__file__).with_name("schema.sql")
    script = schema_path.read_text()

    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute("SELECT pg_try_advisory_xact_lock(7482910) AS acquired")
            row = _row_to_dict(cur.fetchone())
            if not row or not row.get("acquired"):
                logger.info("Schema init: lock held by another worker — skipping")
                return
            logger.info("Schema init: running migrations")
            cur.execute(script)
            logger.info("Schema init: complete")
        finally:
            cur.close()
