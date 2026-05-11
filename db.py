import logging
import os
from contextlib import contextmanager

from psycopg2 import pool
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

_pool: pool.ThreadedConnectionPool | None = None


def init_pool(min_conn: int = 2, max_conn: int = 10) -> None:
    """
    Initialize the connection pool.
    Called once at app startup — if DATABASE_URL is wrong, you find out immediately
    instead of on the first request.
    """
    global _pool
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")
    _pool = pool.ThreadedConnectionPool(
        minconn=min_conn,
        maxconn=max_conn,
        dsn=database_url,
        cursor_factory=RealDictCursor,
    )
    logger.info("DB pool ready  (min=%d  max=%d)", min_conn, max_conn)


def _get_pool() -> pool.ThreadedConnectionPool:
    """Return the pool, initialising it lazily if necessary."""
    global _pool
    if _pool is None:
        init_pool()
    return _pool


@contextmanager
def get_db():
    """
    Yield a pooled connection, return it when done.

    Usage (unchanged from before — models.py needs no edits):
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(...)
    """
    p = _get_pool()
    conn = p.getconn()
    try:
        yield conn
    except Exception:
        # Roll back any partial work so the connection is clean when returned.
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            p.putconn(conn)
        except Exception as exc:
            logger.warning("Could not return connection to pool: %s", exc)