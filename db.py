import os
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor


def connect_db():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)


@contextmanager
def get_db():
    """Yield a DB connection and always close it.

    Usage:
        with get_db() as conn:
            with conn.cursor() as cur:
                ...
    """
    conn = connect_db()
    try:
        yield conn
    finally:
        conn.close()
